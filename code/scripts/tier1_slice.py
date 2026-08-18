#!/usr/bin/env python
"""The Tier 1 vs Tier 2 certificate comparison, and the single-stream latency.

One CPU-only replay over accepted, already-certified proposals answers the two
questions the manuscript still carries as open numbers.

**What the tier comparison asks.**  Every accepted certificate on record was
computed with the Tier 2 analytic bound (``tier1_budget_s = 0.0``).  Guidance
Section 3.4 promises a comparison against the Tier 1 solver-native bound: how
much tightness does the solver buy inside a per-proposal budget, what does it
cost in wall time, and how often does it return nothing at all?  This script
takes a stratified sample of rows whose accepted verdict is
``applied_with_certificate``, re-evaluates each one from its raw model output,
and reports both bounds on the same adjusted instance and the same realized
schedule.

**What the latency measurement asks.**  Every wall-clock figure on record was
measured with twelve workers in flight, which is a throughput number, not the
latency a proposal experiences.  The same run therefore measures the guard's
per-stage cost single-stream on one pinned core, which is what
``\\guardAddedLatencyMs`` means.

Three configurations of one guard, and why each exists
-----------------------------------------------------
``CFG_T2``
    ``G_CERT.with_(tier1_budget_s=0.0)`` -- byte-identical to the configuration
    the accepted E1 evaluations ran, same ``config_hash``.  Its verdict must
    reproduce the accepted one exactly (terminal and certified gap); a mismatch
    stops the run, because a comparison against an unreproducible record is not
    a comparison.
``CFG_BEST(B)``
    ``G_CERT.with_(lb_tier="best", tier1_budget_s=B)``.  The design freeze
    writes this as ``G_CERT.with_(tier1_budget_s=B)``; ``lb_tier`` has to move
    with it, because ``G_CERT.lb_tier`` is ``"tier2"`` and the solver is never
    called under it whatever the budget is.  ``"best"`` computes BOTH bounds on
    one adjusted instance and records them separately (``lb_tier2_bh``,
    ``lb_tier1_bh``), so the per-row comparison is exact and no row is dispatched
    twice to get it.  ``"best"`` is also the deployable rule: the maximum of two
    admissible bounds is admissible.
``CFG_T1_LAT``
    ``G_CERT.with_(lb_tier="tier1", tier1_budget_s=1.0, tier1_workers=1)``, used
    only in the latency phase, where the stage timing wanted is the solver's
    alone and the machine is one pinned core.

Sequencing, and why it is not negotiable
----------------------------------------
The latency phase runs FIRST, single-stream, on one pinned core, with every
numerical runtime capped at one thread.  Only when it has finished does the bulk
comparison start.  A latency measured while the bulk pass holds the solver is
not a measurement (global CLAUDE.md, "Running experiments").

The bulk pass is serial by default for the same reason on the other side: the
quantity it measures is the bound CP-SAT can PROVE inside the budget, and a
solver sharing its cores proves less.  ``--workers N`` is refused unless the
pinned core set holds ``N * tier1_workers`` cores.

Outputs, under ``--out`` (default ``results/tier1_slice``): ``rows.jsonl``
(one line per sampled row, written as the run goes so a stop leaves its
evidence), ``summary.json``, ``summary.md``.

Run::

    conda run -n fjsp python code/scripts/tier1_slice.py --cores 0-5
"""

from __future__ import annotations

import os

# Thread caps before any numeric import.  Every numerical runtime sizes its pool
# from the machine's core count, not from this process's share of it, so the cap
# has to be in the environment before OR-Tools and NumPy are imported anywhere
# (global CLAUDE.md, "Running experiments"; l1guard.tier1 re-caps per solve).
for _var in (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ[_var] = "1"

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import multiprocessing as mp  # noqa: E402
import random  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from collections import Counter, OrderedDict  # noqa: E402
from pathlib import Path  # noqa: E402
from types import SimpleNamespace  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent
CODE_DIR = SCRIPTS_DIR.parent
REPO_ROOT = CODE_DIR.parent
for _p in (str(CODE_DIR), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from l1guard.config import G_CERT  # noqa: E402
from l1guard.verdict import APPLIED_WITH_CERTIFICATE, certified_gap  # noqa: E402

SLICE_VERSION = "l1-tier1-slice-1"

#: The seven arms whose M_constrained mode is genuinely shape-enforced (xgrammar
#: locally, strict server-side json_schema).  DeepSeek is json_object only and is
#: outside the frozen sample by design.
SCHEMA_ENFORCED_ARMS = (
    "qwen14b",
    "qwen27b",
    "glm9b",
    "gpt54mini",
    "sonnet5",
    "opus5",
    "sol",
)

#: The opus core: the only (mode, thinking) cell the opus arm's accepted
#: evaluation covers end to end, both repeats.
OPUS_DIR = "e1_eval_opus5"
OPUS_CORE_MODE = "M_constrained"
OPUS_CORE_THINKING = "disabled"

#: Budgets, per the design freeze.
BUDGETS = (1.0, 5.0)

#: Sample sizes, per the design freeze.
BENIGN_V4_N = 400
LATENCY_N = 200
SEED = 0

#: The classes the 400-row slice is drawn from.
BENIGN_V4_CLASSES = ("benign", "V4")

CFG_T2 = G_CERT.with_(tier1_budget_s=0.0)
CFG_BEST = {b: G_CERT.with_(lb_tier="best", tier1_budget_s=b) for b in BUDGETS}
CFG_T1_LAT = G_CERT.with_(lb_tier="tier1", tier1_budget_s=1.0, tier1_workers=1)

#: Printed with every results table, per the design freeze.  Quoted from the
#: module docstring of ``l1guard.tier1``, which is the source of record.
CENTI_HOUR_CAVEAT = """\
CAVEAT ON THE TIER 1 BOUND (l1guard/tier1.py, fact 2 of the module docstring).
The Tier 1 bound lives on a centi-business-hour grid: the Y1 CP-SAT model scales
business hours by 100, rounding processing times and releases up and due dates to
nearest.  `best_bound_bh` is therefore a lower bound on the DISCRETIZED model's
optimum, and it differs from the continuous optimum by at most the
discretization.  Tier 2 has no such caveat.  Every tightness delta below is
computed against a Tier 1 bound that carries it, so a delta smaller than the
discretization is not evidence that the solver bound is sharper.
A second recorded fact (fact 1): the CP-SAT model carries the adjusted
instance's FIELDS only, not the proposal's dispatch constraints, so Tier 1
bounds a relaxation.  That is sound (a bound on the relaxation bounds the
constrained optimum) and it is why the certified gap never understates.
A third (fact 3): a budget that proves nothing still returns 0.0, which is valid
but vacuous; the vacuous share is reported per budget and never averaged away."""

LAUNCH_QUESTIONS = """\
================================================================================
FOUR LAUNCH QUESTIONS (global CLAUDE.md experiment rules), answered before the run
================================================================================
1. PURPOSE.  Two open numbers close with one CPU-only run.  (a) The Tier 1 vs
   Tier 2 certificate comparison promised by guidance Section 3.4 and listed as
   deliverable 3: per-row bound tightness, gap movement, solve wall time and
   timeout share at per-proposal budgets of 1 s and 5 s.  It lands in the
   certificate-protocol exhibit of the manuscript.  (b) The single-stream
   per-stage guard latency, which fills \\guardAddedLatencyMs (currently a TODO:
   every wall-clock figure on record was measured under concurrency and is a
   throughput number, not a latency).
2. EXPECTED RESULT.  From the accepted solve-time pilot (results/tier1_pilot.json,
   20 instances per cell): Tier 1 is expected to prove optimality inside 1 s on
   the 400-order replay cell and to return a vacuous 0.0 bound on both storm2
   cells at 1 s, becoming marginally informative on c09/storm2 at 5 s.  So the
   expected finding is that Tier 2 carries the certificate almost everywhere at
   a fraction of the cost, with Tier 1 adding tightness on a small, identified
   share.  If instead Tier 1 is materially tighter on the storm2 strata, the
   tier-selection rule in the paper changes from "Tier 2 with Tier 1 as an
   optional refinement" to "best of both, budgeted".  Either outcome is
   reportable; the two lead to different sentences, so the run is not
   redundant.  A row that fails to reproduce its accepted Tier 2 verdict is a
   defect in this instrument or in the record, not a finding, and stops the run.
3. CONTAMINATION.  No API, no GPU, no model call: every number is a
   deterministic replay of raw model output already on disk.  results/ is
   read-only except the --out directory, which must be empty unless --force.
   The two phases are SEQUENCED, never concurrent: the latency phase runs first,
   single-stream, on one pinned core with every numerical runtime capped at one
   thread, and the bulk pass starts only after it has finished, because a wall
   time measured under contention is not a measurement.  The bulk pass is serial
   by default and refuses --workers N unless the pinned core set holds
   N x tier1_workers cores, because the quantity it measures is the bound the
   solver can PROVE inside the budget and a contended solver proves less.  The
   machine's load context is recorded at the start of each phase.
4. DATA ACCURACY.  The sample is drawn from the accepted verdict files, and each
   sampled row is joined to its raw model output by the unique key
   (mode, thinking, repeat, item_id); a duplicate key stops the run.  Every
   input file is sha256'd into the output header.  Each row is then re-evaluated
   under the accepted Tier 2 configuration and asserted to reproduce the
   accepted terminal and the accepted certified gap exactly before its Tier 1
   numbers are used, which is what makes the two tiers a comparison on the same
   schedule rather than two independent readings.
================================================================================"""


# --------------------------------------------------------------------------- #
# Small helpers                                                               #
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sh(cmd) -> str:
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
    except Exception as exc:  # pragma: no cover - diagnostics only
        return "<unavailable: {}>".format(exc)


def load_context(label: str) -> dict:
    return {
        "phase": label,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "uptime": sh(["uptime"]),
        "cores_total": sh(["nproc", "--all"]),
    }


def quantile(values, q: float):
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    pos = q * (len(vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(vals) - 1)
    frac = pos - lo
    return vals[lo] * (1.0 - frac) + vals[hi] * frac


def stats(values) -> dict:
    vals = [v for v in values if v is not None]
    return {
        "n": len(vals),
        "median": quantile(vals, 0.5),
        "p90": quantile(vals, 0.9),
        "min": min(vals) if vals else None,
        "max": max(vals) if vals else None,
        "mean": (sum(vals) / len(vals)) if vals else None,
    }


def share(hits: int, n: int):
    return None if not n else hits / n


def _fmt(value, spec="{:.4f}"):
    return "-" if value is None else spec.format(value)


def _pct(value):
    return "-" if value is None else "{:.1%}".format(value)


def md_table(headers, rows) -> list:
    out = [
        "| " + " | ".join(str(h) for h in headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in rows:
        out.append("| " + " | ".join("" if c is None else str(c) for c in row) + " |")
    return out


def read_jsonl(path: Path) -> list:
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit("{} line {} is not JSON: {}".format(path, n, exc))
    return rows


def parse_cores(text):
    if not text:
        return None
    cores = set()
    for part in str(text).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            cores.update(range(int(lo), int(hi) + 1))
        else:
            cores.add(int(part))
    return sorted(cores) or None


# --------------------------------------------------------------------------- #
# Sampling: pure, deterministic, and testable on its own                      #
# --------------------------------------------------------------------------- #
def allocate(cells: list, total: int, sizes: dict) -> "OrderedDict[object, int]":
    """Spread ``total`` draws as evenly as possible over ``cells``.

    Largest-remainder on an equal share, then clipped at what each cell actually
    holds and the freed draws redistributed over the cells that still have room.
    ``cells`` is consumed in the order given, which the caller sorts, so the
    allocation is a function of the inputs and not of dictionary order.
    """
    out = OrderedDict((c, 0) for c in cells)
    room = {c: int(sizes.get(c, 0)) for c in cells}
    remaining = int(total)
    while remaining > 0:
        open_cells = [c for c in cells if room[c] > out[c]]
        if not open_cells:
            break
        base, extra = divmod(remaining, len(open_cells))
        # The remainder goes to the first `extra` open cells in the caller's
        # order: deterministic, and no cell is favoured by a hash.
        want = {c: base + (1 if i < extra else 0) for i, c in enumerate(open_cells)}
        moved = 0
        for c in open_cells:
            take = min(want[c], room[c] - out[c])
            out[c] += take
            moved += take
        remaining -= moved
        if moved == 0:  # pragma: no cover - defensive; open_cells implies room
            break
    return out


def draw_even(pool: dict, total: int, seed: int) -> list:
    """Draw ``total`` items evenly over the pool's cells, deterministically.

    ``pool`` maps a cell key to a list of candidate items.  Cells are visited in
    sorted key order and each cell's candidates are sorted by their own key
    before sampling, so the draw depends only on (pool contents, total, seed) and
    never on the order the caller happened to build the pool in.
    """
    cells = sorted(pool)
    sizes = {c: len(pool[c]) for c in cells}
    quota = allocate(cells, total, sizes)
    out = []
    for cell in cells:
        n = quota[cell]
        if not n:
            continue
        candidates = sorted(pool[cell], key=row_key)
        rng = random.Random("{}|{}".format(seed, cell))
        out.extend(rng.sample(candidates, n) if n < len(candidates) else list(candidates))
    return sorted(out, key=row_key)


def row_key(row: dict) -> tuple:
    """The unique, sortable identity of one evaluated proposal."""
    return (
        str(row.get("eval_dir", "")),
        str(row.get("mode", "")),
        "" if row.get("thinking") is None else str(row["thinking"]),
        -1 if row.get("repeat") is None else int(row["repeat"]),
        str(row.get("item_id", "")),
    )


# --------------------------------------------------------------------------- #
# The Tier 2 reproduction gate                                                #
# --------------------------------------------------------------------------- #
#: Relative tolerance on the certified gap.  The accepted value and the replayed
#: value are produced by the same code from the same numbers, so exact equality
#: is the expectation and this absorbs only the JSON round-trip.
REPRO_RTOL = 1e-12


def reproduction_mismatch(accepted: dict, replayed: dict, rtol: float = REPRO_RTOL):
    """Return ``None`` when the replay reproduces the accepted verdict.

    Otherwise return the fields that differ, with both values.  The checker is
    deliberately narrow: the terminal state and the certified gap are what the
    tier comparison stands on, and a change in either means the two tiers would
    be compared on different schedules.
    """
    diffs = {}
    if accepted.get("terminal") != replayed.get("terminal"):
        diffs["terminal"] = {
            "accepted": accepted.get("terminal"),
            "replayed": replayed.get("terminal"),
        }
    a_gap, r_gap = accepted.get("certificate_gap"), replayed.get("gap")
    if a_gap is None or r_gap is None:
        if a_gap is not r_gap:
            diffs["certificate_gap"] = {"accepted": a_gap, "replayed": r_gap}
    else:
        scale = max(abs(float(a_gap)), abs(float(r_gap)), 1.0)
        if abs(float(a_gap) - float(r_gap)) > rtol * scale:
            diffs["certificate_gap"] = {"accepted": a_gap, "replayed": r_gap}
    return diffs or None


# --------------------------------------------------------------------------- #
# Loading the accepted record                                                 #
# --------------------------------------------------------------------------- #
def load_arm(results_root: Path, arm_dir: str) -> list:
    """Join one accepted evaluation's verdicts to their raw model output.

    Returns one dict per row carrying everything a replay needs (instance path,
    raw output, frozen seed, rule, dispatch seed) plus the accepted verdict's
    terminal and certified gap, which the reproduction gate checks against.
    """
    base = results_root / arm_dir
    proposals = read_jsonl(base / "proposals.jsonl")
    verdicts = read_jsonl(base / "verdicts_G_CERT.jsonl")

    by_key = {}
    for rec in proposals:
        extra = rec.get("extra") or {}
        key = (extra["mode"], extra.get("thinking"), extra.get("repeat"), rec["instruction_id"])
        if key in by_key:
            raise SystemExit(
                "REFUSING TO RUN: {}/proposals.jsonl has two rows for {}; the join "
                "key (mode, thinking, repeat, item_id) must be unique.".format(arm_dir, key)
            )
        by_key[key] = rec

    out = []
    seen = set()
    for v in verdicts:
        key = (v["mode"], v.get("thinking"), v.get("repeat"), v["item_id"])
        if key in seen:
            raise SystemExit(
                "REFUSING TO RUN: {}/verdicts_G_CERT.jsonl has two rows for "
                "{}".format(arm_dir, key)
            )
        seen.add(key)
        rec = by_key.get(key)
        if rec is None:
            raise SystemExit(
                "REFUSING TO RUN: {} has a verdict for {} with no proposal row; the "
                "raw output it was computed from is not on disk.".format(arm_dir, key)
            )
        out.append(
            {
                "eval_dir": arm_dir,
                "arm": v["arm"],
                "item_id": v["item_id"],
                "mode": v["mode"],
                "thinking": v.get("thinking"),
                "repeat": v.get("repeat"),
                "primary_class": v["primary_class"],
                "subclass": v.get("subclass"),
                "stratum": v["stratum"],
                "instance_id": v["instance_id"],
                "instance_path": rec["instance_path"],
                "raw_output": rec.get("raw_output"),
                "frozen_seed": rec.get("frozen_seed") or [],
                "rule": rec.get("rule") or CFG_T2.rule,
                "dispatch_seed": (rec.get("seeds") or {}).get("dispatch", 0),
                "accepted_terminal": v["terminal"],
                "accepted_gap": v.get("certificate_gap"),
                "accepted_certificate": v.get("certificate"),
                "accepted_config_hash": v.get("config_hash"),
            }
        )
    return out


def build_sample(results_root: Path, seed: int, benign_v4_n: int) -> dict:
    """The frozen sample: the opus core's certified V3 rows, plus a 400-row slice.

    Part A is every certified V3 row of the opus core (M_constrained x
    thinking-disabled, both repeats) -- a census, not a draw.  Part B is
    ``benign_v4_n`` certified benign and V4 rows drawn evenly across the seven
    schema-enforced arms and, within each arm, evenly across the six
    (class, stratum) cells.  Draw order and cell order are both sorted, so the
    sample is a function of (record, seed, n) alone.
    """
    arms = {}
    for arm_dir in ("e1_eval_" + a for a in SCHEMA_ENFORCED_ARMS):
        arms[arm_dir] = load_arm(results_root, arm_dir)

    # -- part A: the census ------------------------------------------------- #
    part_a = [
        r
        for r in arms[OPUS_DIR]
        if r["mode"] == OPUS_CORE_MODE
        and r["thinking"] == OPUS_CORE_THINKING
        and r["primary_class"] == "V3"
        and r["accepted_terminal"] == APPLIED_WITH_CERTIFICATE
    ]
    part_a = sorted(part_a, key=row_key)
    for r in part_a:
        r["sample_part"] = "opus_core_v3"

    taken = {row_key(r) for r in part_a}

    # -- part B: the stratified draw ---------------------------------------- #
    pool = {}
    for arm_dir, rows in arms.items():
        for r in rows:
            if r["accepted_terminal"] != APPLIED_WITH_CERTIFICATE:
                continue
            if r["primary_class"] not in BENIGN_V4_CLASSES:
                continue
            if row_key(r) in taken:  # a row is never sampled twice
                continue
            pool.setdefault((arm_dir, r["primary_class"], r["stratum"]), []).append(r)

    # Even across arms first, then even across the (class, stratum) cells inside
    # each arm: "evenly across the seven schema-enforced arms" is the freeze's
    # wording, and the inner split is what makes the draw cover the gap
    # distribution rather than the biggest cell.
    arm_cells = sorted({k[0] for k in pool})
    arm_sizes = {a: sum(len(v) for k, v in pool.items() if k[0] == a) for a in arm_cells}
    per_arm = allocate(arm_cells, benign_v4_n, arm_sizes)
    part_b = []
    for arm_dir in arm_cells:
        sub = {k: v for k, v in pool.items() if k[0] == arm_dir}
        part_b.extend(draw_even(sub, per_arm[arm_dir], seed))
    part_b = sorted(part_b, key=row_key)
    for r in part_b:
        r["sample_part"] = "benign_v4_400"

    rows = part_a + part_b
    return {
        "rows": rows,
        "part_a": part_a,
        "part_b": part_b,
        "per_arm_quota": dict(per_arm),
        "pool_sizes": {"|".join(str(x) for x in k): len(v) for k, v in sorted(pool.items())},
        "arm_row_counts": {k: len(v) for k, v in sorted(arms.items())},
    }


def draw_latency_subsample(rows: list, n: int, seed: int) -> list:
    """A ``n``-row sub-sample of the drawn sample, stratified the same way."""
    pool = {}
    for r in rows:
        pool.setdefault((r["sample_part"], r["primary_class"], r["stratum"]), []).append(r)
    return draw_even(pool, n, seed + 1)


# --------------------------------------------------------------------------- #
# Worker side                                                                 #
# --------------------------------------------------------------------------- #
_STATE: dict = {}
_TASK_ROWS: list = []


def _init_worker(cores=None, threads: int = 1):
    for var in (
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ):
        os.environ[var] = str(int(threads))
    if cores:
        try:
            os.sched_setaffinity(0, set(cores))
        except (AttributeError, OSError):
            pass
    from l1guard.replay import InstanceCache

    _STATE["cache"] = InstanceCache()


def _evaluate(row: dict, config):
    """One logged proposal through one guard configuration."""
    from l1guard import evaluate_proposal
    from l1guard.replay import _needs_baseline

    cache = _STATE["cache"]
    instance = cache.instance(row["instance_path"])
    raw = row.get("raw_output") or ""
    cfg = config if row["rule"] == config.rule else config.with_(rule=row["rule"])
    probe = SimpleNamespace(frozen_seed=list(row.get("frozen_seed") or []), raw_output=raw)
    baseline = None
    if _needs_baseline(probe):
        baseline = cache.baseline(row["instance_path"], cfg.rule, cfg.seed)
    started = time.perf_counter()
    verdict = evaluate_proposal(
        instance,
        raw,
        cfg,
        baseline_schedule=baseline,
        frozen_seed=tuple(row.get("frozen_seed") or ()),
    )
    wall_s = time.perf_counter() - started
    return verdict, wall_s


def _verdict_summary(verdict, wall_s: float) -> dict:
    cert = verdict.certificate
    return {
        "terminal": verdict.terminal,
        "stage_reached": verdict.stage_reached,
        "infra": any(f.severity == "infra" for f in verdict.findings),
        "findings": sorted({f.code for f in verdict.findings}),
        "gap": None if cert is None else cert.gap,
        "obj_bh": None if cert is None else cert.obj_bh,
        "lb_bh": None if cert is None else cert.lb_bh,
        "lb_tier2_bh": None if cert is None else cert.lb_tier2_bh,
        "lb_tier1_bh": None if cert is None else cert.lb_tier1_bh,
        "tier": None if cert is None else cert.tier,
        "tier1_status": None if cert is None else cert.tier1_status,
        "tier1_incumbent_bh": None if cert is None else cert.tier1_incumbent_bh,
        "lb_wall_ms": None if cert is None else cert.lb_wall_ms,
        "solve_wall_ms": None if cert is None else cert.solve_wall_ms,
        "timings_ms": {k: v for k, v in (verdict.timings_ms or {}).items()},
        "schedule_digest": verdict.schedule_digest,
        "wall_s": wall_s,
    }


def _compare_chunk(indices) -> list:
    """Tier 2 reproduction plus both Tier 1 budgets, for one chunk of rows."""
    out = []
    for i in indices:
        row = _TASK_ROWS[i]
        v2, w2 = _evaluate(row, CFG_T2)
        entry = {"i": i, "t2": _verdict_summary(v2, w2), "budgets": {}}
        entry["repro_mismatch"] = reproduction_mismatch(
            {"terminal": row["accepted_terminal"], "certificate_gap": row["accepted_gap"]},
            entry["t2"],
        )
        if entry["repro_mismatch"] is None:
            for budget, cfg in sorted(CFG_BEST.items()):
                vb, wb = _evaluate(row, cfg)
                entry["budgets"]["{:g}".format(budget)] = _verdict_summary(vb, wb)
        out.append(entry)
    return out


def _latency_chunk(indices) -> list:
    """Per-stage single-stream timing for one chunk of rows."""
    out = []
    for i in indices:
        row = _TASK_ROWS[i]
        v2, w2 = _evaluate(row, CFG_T2)
        v1, w1 = _evaluate(row, CFG_T1_LAT)
        out.append(
            {
                "i": i,
                "t2": _verdict_summary(v2, w2),
                "t1": _verdict_summary(v1, w1),
            }
        )
    return out


def _imap(func, tasks, workers: int, cores=None, threads: int = 1):
    """Yield each chunk's result as it lands, in task order.

    A generator rather than a list on both paths, so the caller can write and
    check as the run goes: a stop leaves its evidence on disk, and the Tier 2
    reproduction gate fires on the first bad row instead of an hour later.
    """
    if workers <= 1 or len(tasks) <= 1:
        _init_worker(cores, threads)
        for task in tasks:
            yield func(task)
        return
    ctx = mp.get_context("fork")
    with ctx.Pool(
        processes=workers, initializer=_init_worker, initargs=(cores, threads)
    ) as pool:
        for out in pool.imap(func, tasks, chunksize=1):
            yield out


# --------------------------------------------------------------------------- #
# Row records                                                                 #
# --------------------------------------------------------------------------- #
def build_row_record(row: dict, entry: dict) -> dict:
    """Everything the analysis needs about one sampled row, and nothing live."""
    t2 = entry["t2"]
    rec = {
        "sample_part": row["sample_part"],
        "eval_dir": row["eval_dir"],
        "arm": row["arm"],
        "item_id": row["item_id"],
        "mode": row["mode"],
        "thinking": row["thinking"],
        "repeat": row["repeat"],
        "primary_class": row["primary_class"],
        "subclass": row["subclass"],
        "stratum": row["stratum"],
        "instance_id": row["instance_id"],
        "accepted_terminal": row["accepted_terminal"],
        "accepted_gap": row["accepted_gap"],
        "t2_terminal": t2["terminal"],
        "t2_gap": t2["gap"],
        "t2_obj_bh": t2["obj_bh"],
        "t2_lb_bh": t2["lb_bh"],
        "t2_lb_wall_ms": t2["lb_wall_ms"],
        "t2_timings_ms": t2["timings_ms"],
        "t2_schedule_digest": t2["schedule_digest"],
        "reproduced": entry["repro_mismatch"] is None,
        "repro_mismatch": entry["repro_mismatch"],
        "budgets": {},
    }
    tau, floor = CFG_T2.tau, CFG_T2.lb_floor_bh
    for label, b in sorted(entry["budgets"].items()):
        lb2 = b["lb_tier2_bh"]
        lb1 = b["lb_tier1_bh"]
        obj = b["obj_bh"]
        item = {
            "budget_s": float(label),
            "terminal_best": b["terminal"],
            "obj_bh": obj,
            "lb_tier2_bh": lb2,
            "lb_tier1_bh": lb1,
            "lb_best_bh": b["lb_bh"],
            "tier_chosen": b["tier"],
            "tier1_status": b["tier1_status"],
            "tier1_incumbent_bh": b["tier1_incumbent_bh"],
            "tier1_proved_optimal": b["tier1_status"] == "OPTIMAL",
            "tier1_vacuous": (lb1 is not None and lb1 <= 0.0),
            "solve_wall_s": None if b["solve_wall_ms"] is None else b["solve_wall_ms"] / 1000.0,
            "lb2_wall_ms": b["lb_wall_ms"],
            "qual_wall_ms": b["timings_ms"].get("qual"),
            "total_wall_s": b["wall_s"],
            "findings": b["findings"],
            "schedule_digest_matches_t2": b["schedule_digest"] == t2["schedule_digest"],
        }
        if lb1 is not None and lb2 is not None:
            item["delta_abs_bh"] = lb1 - lb2
            item["delta_rel"] = (lb1 - lb2) / max(lb2, floor)
            item["tier1_tighter"] = lb1 > lb2 + 1e-9
        if obj is not None:
            if lb2 is not None:
                item["gap_tier2"] = certified_gap(obj, lb2, floor)
            if lb1 is not None:
                item["gap_tier1"] = certified_gap(obj, lb1, floor)
                item["accepted_under_tier1_only"] = item["gap_tier1"] <= tau
            item["gap_best"] = b["gap"]
            if lb2 is not None:
                item["gap_movement"] = item["gap_tier2"] - b["gap"]
        rec["budgets"][label] = item
    return rec


# --------------------------------------------------------------------------- #
# Aggregation                                                                 #
# --------------------------------------------------------------------------- #
def budget_stats(records: list, label: str) -> dict:
    items = [r["budgets"][label] for r in records if label in r["budgets"]]
    n = len(items)
    tighter = [it for it in items if it.get("tier1_tighter")]
    return {
        "n": n,
        "tier1_vacuous": share(sum(1 for it in items if it.get("tier1_vacuous")), n),
        "tier1_vacuous_n": sum(1 for it in items if it.get("tier1_vacuous")),
        "tier1_proved_optimal": share(
            sum(1 for it in items if it.get("tier1_proved_optimal")), n
        ),
        "tier1_not_proved_optimal": share(
            sum(1 for it in items if not it.get("tier1_proved_optimal")), n
        ),
        "tier1_tighter": share(len(tighter), n),
        "tier1_tighter_n": len(tighter),
        "tier2_carries": share(
            sum(1 for it in items if str(it.get("tier_chosen", "")).endswith("tier2")), n
        ),
        "delta_rel_all": stats([it.get("delta_rel") for it in items]),
        "delta_rel_when_tighter": stats([it.get("delta_rel") for it in tighter]),
        "delta_abs_when_tighter": stats([it.get("delta_abs_bh") for it in tighter]),
        "gap_tier2": stats([it.get("gap_tier2") for it in items]),
        "gap_tier1": stats([it.get("gap_tier1") for it in items]),
        "gap_best": stats([it.get("gap_best") for it in items]),
        "gap_movement": stats([it.get("gap_movement") for it in items]),
        "blocked_under_tier1_only": share(
            sum(1 for it in items if it.get("accepted_under_tier1_only") is False), n
        ),
        "blocked_under_tier1_only_n": sum(
            1 for it in items if it.get("accepted_under_tier1_only") is False
        ),
        "accepted_under_best": share(
            sum(1 for it in items if it.get("terminal_best") == APPLIED_WITH_CERTIFICATE), n
        ),
        "solve_wall_s": stats([it.get("solve_wall_s") for it in items]),
        "solve_over_budget": share(
            sum(
                1
                for it in items
                if it.get("solve_wall_s") is not None
                and it["solve_wall_s"] > it["budget_s"] * 1.05
            ),
            n,
        ),
        "lb2_wall_ms": stats([it.get("lb2_wall_ms") for it in items]),
        "schedule_digest_matches_t2": share(
            sum(1 for it in items if it.get("schedule_digest_matches_t2")), n
        ),
    }


def group_stats(records: list) -> dict:
    return {
        "n": len(records),
        "budgets": {label: budget_stats(records, label) for label in
                    ("{:g}".format(b) for b in BUDGETS)},
    }


def latency_stats(records: list) -> dict:
    def stage(key):
        return stats([r["stages_ms"].get(key) for r in records])

    return {
        "n": len(records),
        "schema_ms": stage("schema"),
        "feas_ms": stage("feas"),
        "qual_tier2_ms": stage("qual_tier2"),
        "guard_total_tier2_ms": stage("total_tier2"),
        "qual_tier1_1s_ms": stage("qual_tier1_1s"),
        "guard_total_tier1_1s_ms": stage("total_tier1_1s"),
    }


# --------------------------------------------------------------------------- #
# Report                                                                      #
# --------------------------------------------------------------------------- #
def write_summary_md(path: Path, meta: dict, summary: dict) -> None:
    lines = []
    add = lines.append
    add("# Tier 1 vs Tier 2 certificate comparison, and the single-stream guard latency")
    add("")
    add("Generated {} by `{}` ({}).".format(meta["date"], "code/scripts/tier1_slice.py",
                                            meta["slice_version"]))
    add("")
    add("```")
    add(LAUNCH_QUESTIONS)
    add("```")
    add("")
    add("```")
    add(CENTI_HOUR_CAVEAT)
    add("```")
    add("")

    # -- run header ---------------------------------------------------------- #
    add("## Run")
    add("")
    lines.extend(
        md_table(
            ["field", "value"],
            [
                ["date", meta["date"]],
                ["sample seed", meta["seed"]],
                ["rows compared", meta["n_rows"]],
                ["  part A (opus core certified V3, census)", meta["n_part_a"]],
                ["  part B (certified benign + V4, stratified draw)", meta["n_part_b"]],
                ["latency sub-sample", meta["n_latency"]],
                ["budgets", ", ".join("{:g} s".format(b) for b in BUDGETS)],
                ["tau", "{} ({})".format(CFG_T2.tau,
                                         "provisional" if CFG_T2.tau_provisional else "published")],
                ["LB floor", "{:g} bh".format(CFG_T2.lb_floor_bh)],
                ["latency phase", "{} rows, 1 stream, cores {}, threads 1".format(
                    meta["n_latency"], meta["latency_cores"])],
                ["bulk phase", "{} rows, {} worker(s), cores {}, tier1_workers {}".format(
                    meta["n_rows"], meta["workers"], meta["bulk_cores"],
                    G_CERT.tier1_workers)],
                ["latency wall", "{:.1f} s".format(meta["latency_wall_s"])],
                ["bulk wall", "{:.1f} s".format(meta["bulk_wall_s"])],
                ["total wall", "{:.1f} s".format(meta["wall_s"])],
            ],
        )
    )
    add("")
    add("### Guard configurations")
    add("")
    lines.extend(
        md_table(
            ["configuration", "lb_tier", "tier1_budget_s", "tier1_workers", "config_hash"],
            [
                [name, cfg["lb_tier"], cfg["tier1_budget_s"], cfg["tier1_workers"],
                 "`{}`".format(cfg["config_hash"][:16])]
                for name, cfg in meta["configs"].items()
            ],
        )
    )
    add("")
    add("`CFG_T2` is byte-identical to the configuration the accepted E1 evaluations "
        "ran, so its `config_hash` is the one recorded in every `verdicts_G_CERT.jsonl` "
        "row. The design freeze writes the Tier 1 configuration as "
        "`G_CERT.with_(tier1_budget_s=B)`; `lb_tier` has to move with the budget, "
        "because `G_CERT.lb_tier` is `tier2` and the solver is never called under it "
        "whatever the budget is. `best` computes both bounds on one adjusted instance "
        "and records them separately, so the comparison is exact and the row is "
        "dispatched once per budget rather than twice.")
    add("")
    add("### Inputs")
    add("")
    lines.extend(
        md_table(
            ["file", "sha256"],
            [[ "`{}`".format(k), "`{}`".format(v)] for k, v in sorted(meta["inputs"].items())],
        )
    )
    add("")

    # -- the reproduction gate ------------------------------------------------ #
    add("## Gate: every sampled row reproduces its accepted Tier 2 verdict")
    add("")
    gate = summary["reproduction"]
    add("Each sampled row is re-evaluated from its raw model output under `CFG_T2` and "
        "its terminal state and certified gap are compared with the accepted verdict. "
        "The Tier 1 numbers of a row that fails are never used, and the run stops.")
    add("")
    lines.extend(
        md_table(
            ["checked", "reproduced", "mismatched", "verdict"],
            [[gate["n"], gate["reproduced"], gate["mismatched"],
              "PASS" if gate["mismatched"] == 0 else "**FAIL**"]],
        )
    )
    add("")
    if gate["mismatches"]:
        add("Mismatches:")
        add("")
        for m in gate["mismatches"][:20]:
            add("- `{}` / `{}`: {}".format(m["eval_dir"], m["item_id"], m["mismatch"]))
        add("")
    add("The executed schedule is also identical under every Tier 1 budget: "
        "`schedule_digest` matches the Tier 2 replay on {} of rows at 1 s and {} at 5 s, "
        "which is what makes the two bounds a comparison on the same schedule.".format(
            _pct(summary["overall"]["budgets"]["1"]["schedule_digest_matches_t2"]),
            _pct(summary["overall"]["budgets"]["5"]["schedule_digest_matches_t2"]),
        ))
    add("")

    # -- sample composition ---------------------------------------------------- #
    add("## Sample")
    add("")
    add("Part A is a census: every row of the opus core (M_constrained x "
        "thinking-disabled, both repeats) whose accepted verdict is "
        "`applied_with_certificate` and whose class is V3. Part B draws {} certified "
        "benign and V4 rows evenly across the seven schema-enforced arms and, within "
        "each arm, evenly across the six (class, stratum) cells; cells and candidates "
        "are both sorted before sampling, so the draw is a function of (record, seed, "
        "n) alone. Seed {}. A part-A row is never redrawn into part B.".format(
            meta["n_part_b"], meta["seed"]))
    add("")
    lines.extend(
        md_table(
            ["part", "arm", "class", "stratum", "rows"],
            [[c["sample_part"], c["arm"], c["primary_class"], c["stratum"], c["n"]]
             for c in summary["sample_composition"]],
        )
    )
    add("")

    # -- the headline ---------------------------------------------------------- #
    add("## The comparison")
    add("")
    add("`delta` is the Tier 1 bound minus the Tier 2 bound on the same adjusted "
        "instance, relative to `max(LB_tier2, {:g} bh)`. *Tier 1 tighter* counts rows "
        "where the solver bound strictly exceeds the analytic one. *Vacuous* counts "
        "rows where the solver proved nothing and returned 0.0. *Not proved optimal* "
        "is the timeout share: the solver used its whole budget without closing the "
        "instance.".format(CFG_T2.lb_floor_bh))
    add("")
    rows = []
    for label in ("1", "5"):
        b = summary["overall"]["budgets"][label]
        rows.append([
            "{} s".format(label), b["n"],
            "{} ({})".format(b["tier1_tighter_n"], _pct(b["tier1_tighter"])),
            "{} ({})".format(b["tier1_vacuous_n"], _pct(b["tier1_vacuous"])),
            _pct(b["tier1_not_proved_optimal"]),
            _fmt(b["delta_rel_when_tighter"]["median"], "{:+.2e}"),
            _fmt(b["delta_rel_when_tighter"]["max"], "{:+.2e}"),
            _fmt(b["gap_movement"]["median"], "{:.2e}"),
            _fmt(b["gap_movement"]["max"], "{:.2e}"),
            _fmt(b["solve_wall_s"]["median"], "{:.2f}"),
            _fmt(b["solve_wall_s"]["p90"], "{:.2f}"),
        ])
    lines.extend(
        md_table(
            ["budget", "rows", "Tier 1 tighter", "Tier 1 vacuous", "not proved optimal",
             "median delta (rel, tighter rows)", "max delta (rel)",
             "median gap movement", "max gap movement",
             "median solve wall s", "p90 solve wall s"],
            rows,
        )
    )
    add("")
    add("Gap movement is `gap(Tier 2) - gap(best of both)`: how much of the certified "
        "gap the solver bound removes when it is allowed to help. It is non-negative "
        "by construction, because the maximum of two admissible bounds is admissible.")
    add("")

    add("### What Tier 1 alone would do to the same accepted proposals")
    add("")
    rows = []
    for label in ("1", "5"):
        b = summary["overall"]["budgets"][label]
        rows.append([
            "{} s".format(label), b["n"],
            _fmt(b["gap_tier2"]["median"]), _fmt(b["gap_tier1"]["median"]),
            _fmt(b["gap_best"]["median"]),
            "{} ({})".format(b["blocked_under_tier1_only_n"],
                             _pct(b["blocked_under_tier1_only"])),
        ])
    lines.extend(
        md_table(
            ["budget", "rows", "median gap (Tier 2)", "median gap (Tier 1 only)",
             "median gap (best)", "would be refused under Tier 1 only"],
            rows,
        )
    )
    add("")
    add("Every sampled row is one the accepted Tier 2 certificate ACCEPTED. The last "
        "column is the share a Tier-1-only guard would refuse instead, at tau = {}: a "
        "vacuous solver bound inflates the certified gap above tolerance, so the "
        "proposal is blocked for want of evidence rather than for want of "
        "quality.".format(CFG_T2.tau))
    add("")
    add("The Tier-1-only median gap is large wherever the solver bound is vacuous, and "
        "that is arithmetic rather than a quality signal: with LB = 0 the gap "
        "convention `(obj - LB) / max(LB, {:g} bh)` returns the realized objective "
        "itself, in weighted business hours.".format(CFG_T2.lb_floor_bh))
    add("")

    # -- per stratum ------------------------------------------------------------ #
    add("### Per stratum")
    add("")
    rows = []
    for stratum in summary["by_stratum_order"]:
        for label in ("1", "5"):
            b = summary["by_stratum"][stratum]["budgets"][label]
            rows.append([
                stratum, "{} s".format(label), b["n"],
                _pct(b["tier1_tighter"]), _pct(b["tier1_vacuous"]),
                _pct(b["tier1_proved_optimal"]),
                _fmt(b["delta_rel_when_tighter"]["median"], "{:+.2e}"),
                _fmt(b["solve_wall_s"]["median"], "{:.2f}"),
                _fmt(b["lb2_wall_ms"]["median"], "{:.3f}"),
            ])
    lines.extend(
        md_table(
            ["stratum", "budget", "rows", "Tier 1 tighter", "Tier 1 vacuous",
             "proved optimal", "median delta (rel, tighter rows)",
             "median Tier 1 solve wall s", "median Tier 2 wall ms"],
            rows,
        )
    )
    add("")
    add("The Tier 2 column is milliseconds and the Tier 1 column is seconds; the two "
        "are not typos of each other.")
    add("")

    add("### Per sample part")
    add("")
    rows = []
    for part in summary["by_part_order"]:
        for label in ("1", "5"):
            b = summary["by_part"][part]["budgets"][label]
            rows.append([
                part, "{} s".format(label), b["n"], _pct(b["tier1_tighter"]),
                _pct(b["tier1_vacuous"]), _fmt(b["gap_tier2"]["median"]),
                _fmt(b["gap_best"]["median"]),
                _pct(b["blocked_under_tier1_only"]),
            ])
    lines.extend(
        md_table(
            ["sample part", "budget", "rows", "Tier 1 tighter", "Tier 1 vacuous",
             "median gap (Tier 2)", "median gap (best)",
             "refused under Tier 1 only"],
            rows,
        )
    )
    add("")

    # -- latency ---------------------------------------------------------------- #
    add("## Single-stream guard latency")
    add("")
    add("Measured on a {}-row sub-sample of the same sample, one proposal at a time, "
        "pinned to core(s) {}, with every numerical runtime capped at one thread. The "
        "bulk comparison had not started. The Tier 1 row is measured at "
        "`tier1_workers = 1` because one pinned core is one worker; the bulk pass "
        "above runs the frozen default of {}.".format(
            meta["n_latency"], meta["latency_cores"], G_CERT.tier1_workers))
    add("")
    lat = summary["latency"]
    rows = []
    for key, label in (
        ("schema_ms", "stage 1, schema"),
        ("feas_ms", "stage 2, feasibility"),
        ("qual_tier2_ms", "stage 3, quality (Tier 2)"),
        ("guard_total_tier2_ms", "**whole guard, Tier 2**"),
        ("qual_tier1_1s_ms", "stage 3, quality (Tier 1, 1 s budget)"),
        ("guard_total_tier1_1s_ms", "whole guard, Tier 1 at 1 s"),
    ):
        s = lat["overall"][key]
        rows.append([label, s["n"], _fmt(s["median"], "{:.2f}"), _fmt(s["p90"], "{:.2f}"),
                     _fmt(s["max"], "{:.1f}")])
    lines.extend(md_table(["stage", "rows", "median ms", "p90 ms", "max ms"], rows))
    add("")
    add("Per stratum, whole-guard Tier 2 latency (the deployed configuration):")
    add("")
    rows = []
    for stratum in summary["by_stratum_order"]:
        s = lat["by_stratum"].get(stratum)
        if not s:
            continue
        rows.append([
            stratum, s["guard_total_tier2_ms"]["n"],
            _fmt(s["schema_ms"]["median"], "{:.2f}"),
            _fmt(s["feas_ms"]["median"], "{:.2f}"),
            _fmt(s["qual_tier2_ms"]["median"], "{:.2f}"),
            _fmt(s["guard_total_tier2_ms"]["median"], "{:.2f}"),
            _fmt(s["guard_total_tier2_ms"]["p90"], "{:.2f}"),
            _fmt(s["qual_tier1_1s_ms"]["median"], "{:.0f}"),
        ])
    lines.extend(
        md_table(
            ["stratum", "rows", "schema ms", "feas ms", "qual Tier 2 ms",
             "whole guard ms (median)", "whole guard ms (p90)", "qual Tier 1 1 s ms"],
            rows,
        )
    )
    add("")
    add("Load context at each phase:")
    add("")
    lines.extend(
        md_table(
            ["phase", "timestamp", "uptime (load averages)", "cores"],
            [[c["phase"], c["timestamp"], "`{}`".format(c["uptime"]), c["cores_total"]]
             for c in meta["load_context"]],
        )
    )
    add("")
    add("Files: `rows.jsonl` (one line per sampled row, both budgets), `summary.json`, "
        "`summary.md`.")
    path.write_text("\n".join(lines) + "\n")


# --------------------------------------------------------------------------- #
# main                                                                        #
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    global _TASK_ROWS

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results-root", default=str(REPO_ROOT / "results"))
    ap.add_argument("--out", default=str(REPO_ROOT / "results" / "tier1_slice"))
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--benign-v4", type=int, default=BENIGN_V4_N)
    ap.add_argument("--latency-rows", type=int, default=LATENCY_N)
    ap.add_argument("--cores", default="0-5",
                    help="CPU affinity for the bulk pass, e.g. 0-5")
    ap.add_argument("--latency-core", type=int, default=None,
                    help="the single core the latency phase is pinned to "
                         "(default: the first core of --cores)")
    ap.add_argument("--workers", type=int, default=1,
                    help="bulk-pass worker processes; refused unless the pinned core "
                         "set holds workers x tier1_workers cores")
    ap.add_argument("--smoke", type=int, default=0,
                    help="cap both samples for a smoke run (spaced, deterministic)")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    print(LAUNCH_QUESTIONS, flush=True)
    started = time.time()

    results_root = Path(args.results_root).resolve()
    out_dir = Path(args.out)
    if out_dir.exists() and any(out_dir.iterdir()) and not args.force:
        raise SystemExit(
            "REFUSING TO RUN: {} already has results. Move it aside or pass "
            "--force.".format(out_dir)
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    bulk_cores = parse_cores(args.cores)
    latency_core = args.latency_core
    if latency_core is None:
        latency_core = bulk_cores[0] if bulk_cores else 0
    if args.workers > 1:
        need = args.workers * G_CERT.tier1_workers
        have = len(bulk_cores or [])
        if have < need:
            raise SystemExit(
                "REFUSING TO RUN: --workers {} needs {} cores ({} solver workers each) "
                "and --cores gives {}. A contended solve proves a weaker bound, and the "
                "bound is the quantity this run measures.".format(
                    args.workers, need, G_CERT.tier1_workers, have)
            )

    # -- the sample ---------------------------------------------------------- #
    print("\n[tier1-slice] building the sample from {} ...".format(results_root), flush=True)
    sample = build_sample(results_root, args.seed, args.benign_v4)
    rows = sample["rows"]
    if args.smoke:
        stride = max(1, len(rows) // args.smoke)
        rows = rows[::stride][: args.smoke]
    print("[tier1-slice] part A (opus core certified V3): {}".format(len(sample["part_a"])))
    print("[tier1-slice] part B (certified benign + V4):   {}".format(len(sample["part_b"])))
    print("[tier1-slice] per-arm quota: {}".format(dict(sample["per_arm_quota"])))
    print("[tier1-slice] rows to compare: {}".format(len(rows)), flush=True)

    latency_rows = draw_latency_subsample(rows, min(args.latency_rows, len(rows)), args.seed)
    latency_index = {row_key(r) for r in latency_rows}
    print("[tier1-slice] latency sub-sample: {} rows".format(len(latency_rows)), flush=True)

    inputs = {}
    for arm in SCHEMA_ENFORCED_ARMS:
        for name in ("proposals.jsonl", "verdicts_G_CERT.jsonl"):
            path = results_root / ("e1_eval_" + arm) / name
            inputs["results/e1_eval_{}/{}".format(arm, name)] = sha256_file(path)

    load_ctx = []

    # -- phase 1: latency, single stream, one pinned core --------------------- #
    print("\n[tier1-slice] PHASE 1 of 2: single-stream latency on core {} "
          "(threads=1, one proposal at a time)".format(latency_core), flush=True)
    ctx = load_context("latency (single stream, core {})".format(latency_core))
    load_ctx.append(ctx)
    print("  {}".format(ctx["uptime"]), flush=True)
    _TASK_ROWS = latency_rows
    t0 = time.time()
    latency_records = []
    for chunk in _imap(
        _latency_chunk,
        [list(range(i, min(i + 16, len(latency_rows)))) for i in range(0, len(latency_rows), 16)],
        1,
        [latency_core],
        1,
    ):
        for entry in chunk:
            row = latency_rows[entry["i"]]
            t2, t1 = entry["t2"], entry["t1"]
            latency_records.append(
                {
                    "sample_part": row["sample_part"],
                    "eval_dir": row["eval_dir"],
                    "item_id": row["item_id"],
                    "mode": row["mode"],
                    "thinking": row["thinking"],
                    "repeat": row["repeat"],
                    "primary_class": row["primary_class"],
                    "stratum": row["stratum"],
                    "instance_id": row["instance_id"],
                    "stages_ms": {
                        "schema": t2["timings_ms"].get("schema"),
                        "feas": t2["timings_ms"].get("feas"),
                        "qual_tier2": t2["timings_ms"].get("qual"),
                        "total_tier2": t2["timings_ms"].get("total"),
                        "qual_tier1_1s": t1["timings_ms"].get("qual"),
                        "total_tier1_1s": t1["timings_ms"].get("total"),
                    },
                    "t2_terminal": t2["terminal"],
                    "t1_terminal": t1["terminal"],
                }
            )
        print("    latency rows {}/{}".format(len(latency_records), len(latency_rows)),
              flush=True)
    latency_wall = time.time() - t0
    print("[tier1-slice] latency phase done in {:.1f} s".format(latency_wall), flush=True)

    # -- phase 2: the bulk comparison ---------------------------------------- #
    print("\n[tier1-slice] PHASE 2 of 2: tier comparison, {} row(s), {} worker(s), "
          "cores {}, tier1_workers {}".format(
              len(rows), args.workers, bulk_cores, G_CERT.tier1_workers), flush=True)
    ctx = load_context("bulk comparison (cores {})".format(bulk_cores))
    load_ctx.append(ctx)
    print("  {}".format(ctx["uptime"]), flush=True)
    _TASK_ROWS = rows
    t0 = time.time()
    rows_path = out_dir / "rows.jsonl"
    records = []
    mismatches = []
    chunks = [list(range(i, min(i + 8, len(rows)))) for i in range(0, len(rows), 8)]
    threads = G_CERT.tier1_workers
    with open(rows_path, "w", encoding="utf-8") as fh:
        for chunk in _imap(_compare_chunk, chunks, args.workers, bulk_cores, threads):
            for entry in chunk:
                row = rows[entry["i"]]
                rec = build_row_record(row, entry)
                rec["in_latency_subsample"] = row_key(row) in latency_index
                records.append(rec)
                fh.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
                if entry["repro_mismatch"] is not None:
                    mismatches.append(
                        {
                            "eval_dir": row["eval_dir"],
                            "item_id": row["item_id"],
                            "mode": row["mode"],
                            "thinking": row["thinking"],
                            "repeat": row["repeat"],
                            "mismatch": entry["repro_mismatch"],
                        }
                    )
            fh.flush()
            print("    compared {}/{} rows".format(len(records), len(rows)), flush=True)
            if mismatches:
                break
    bulk_wall = time.time() - t0

    if mismatches:
        print("\n[tier1-slice] TIER 2 REPRODUCTION GATE FAILED on {} row(s):".format(
            len(mismatches)))
        for m in mismatches[:10]:
            print("  {} / {} / {} / r{} : {}".format(
                m["eval_dir"], m["item_id"], m["mode"], m["repeat"], m["mismatch"]))
        print("\nSTOPPING. A tier comparison against a verdict that does not reproduce "
              "is not a comparison. Partial rows are in {}.".format(rows_path))
        return 3

    print("[tier1-slice] bulk phase done in {:.1f} s".format(bulk_wall), flush=True)

    # -- aggregate ----------------------------------------------------------- #
    strata = sorted({r["stratum"] for r in records})
    parts = sorted({r["sample_part"] for r in records})
    composition = [
        {
            "sample_part": part,
            "arm": arm,
            "primary_class": cls,
            "stratum": stratum,
            "n": n,
        }
        for (part, arm, cls, stratum), n in sorted(
            Counter(
                (r["sample_part"], r["arm"], r["primary_class"], r["stratum"])
                for r in records
            ).items()
        )
    ]
    summary = {
        "reproduction": {
            "n": len(records),
            "reproduced": sum(1 for r in records if r["reproduced"]),
            "mismatched": len(mismatches),
            "mismatches": mismatches,
        },
        "sample_composition": composition,
        "overall": group_stats(records),
        "by_stratum": {s: group_stats([r for r in records if r["stratum"] == s])
                       for s in strata},
        "by_stratum_order": strata,
        "by_part": {p: group_stats([r for r in records if r["sample_part"] == p])
                    for p in parts},
        "by_part_order": parts,
        "by_arm": {a: group_stats([r for r in records if r["arm"] == a])
                   for a in sorted({r["arm"] for r in records})},
        "latency": {
            "overall": latency_stats(latency_records),
            "by_stratum": {
                s: latency_stats([r for r in latency_records if r["stratum"] == s])
                for s in sorted({r["stratum"] for r in latency_records})
            },
            "by_part": {
                p: latency_stats([r for r in latency_records if r["sample_part"] == p])
                for p in sorted({r["sample_part"] for r in latency_records})
            },
            "rows": latency_records,
        },
    }

    meta = {
        "slice_version": SLICE_VERSION,
        "date": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "wall_s": time.time() - started,
        "latency_wall_s": latency_wall,
        "bulk_wall_s": bulk_wall,
        "seed": args.seed,
        "n_rows": len(records),
        "n_part_a": sum(1 for r in records if r["sample_part"] == "opus_core_v3"),
        "n_part_b": sum(1 for r in records if r["sample_part"] == "benign_v4_400"),
        "n_latency": len(latency_records),
        "budgets": list(BUDGETS),
        "workers": args.workers,
        "bulk_cores": bulk_cores,
        "latency_cores": [latency_core],
        "results_root": str(results_root),
        "out_dir": str(out_dir.resolve()),
        "schema_enforced_arms": list(SCHEMA_ENFORCED_ARMS),
        "opus_core": {"eval_dir": OPUS_DIR, "mode": OPUS_CORE_MODE,
                      "thinking": OPUS_CORE_THINKING},
        "per_arm_quota": {k: v for k, v in sample["per_arm_quota"].items()},
        "pool_sizes": sample["pool_sizes"],
        "arm_row_counts": sample["arm_row_counts"],
        "configs": {
            "CFG_T2": {**CFG_T2.to_dict(), "config_hash": CFG_T2.config_hash},
            **{
                "CFG_BEST_{:g}s".format(b): {**cfg.to_dict(), "config_hash": cfg.config_hash}
                for b, cfg in sorted(CFG_BEST.items())
            },
            "CFG_T1_LAT": {**CFG_T1_LAT.to_dict(), "config_hash": CFG_T1_LAT.config_hash},
        },
        "inputs": inputs,
        "load_context": load_ctx,
        "centi_hour_caveat": CENTI_HOUR_CAVEAT,
        "launch_questions": LAUNCH_QUESTIONS,
    }

    (out_dir / "summary.json").write_text(
        json.dumps({"run": meta, **summary}, indent=1, sort_keys=True, default=str) + "\n"
    )
    write_summary_md(out_dir / "summary.md", meta, summary)

    print("\n" + CENTI_HOUR_CAVEAT)
    print("\n[tier1-slice] Tier 2 reproduction: {}/{} rows".format(
        summary["reproduction"]["reproduced"], summary["reproduction"]["n"]))
    for label in ("1", "5"):
        b = summary["overall"]["budgets"][label]
        print("[tier1-slice] B={} s: tier1 tighter {} ({}), vacuous {} ({}), "
              "not proved optimal {}, median solve wall {}".format(
                  label, b["tier1_tighter_n"], _pct(b["tier1_tighter"]),
                  b["tier1_vacuous_n"], _pct(b["tier1_vacuous"]),
                  _pct(b["tier1_not_proved_optimal"]),
                  _fmt(b["solve_wall_s"]["median"], "{:.2f} s")))
    lat = summary["latency"]["overall"]
    print("[tier1-slice] single-stream guard latency (Tier 2, whole guard): "
          "median {} ms, p90 {} ms".format(
              _fmt(lat["guard_total_tier2_ms"]["median"], "{:.2f}"),
              _fmt(lat["guard_total_tier2_ms"]["p90"], "{:.2f}")))
    print("[tier1-slice] written to {} in {:.1f} s".format(out_dir, time.time() - started))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
