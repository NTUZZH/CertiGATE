#!/usr/bin/env python
"""DG14: three deterministic delta baselines against the optimality certificate.

WHY THIS EXISTS
---------------
A reviewer asked for the simplest quality check a scheduler would actually
write: run the proposal, run a reference schedule, and refuse the proposal when
it makes the reference worse by more than a threshold.  If such a rule matched
the certificate on the direct benchmark, the certificate would be machinery
nobody needs.  This script builds three of those rules, sweeps each over its
own grid, and compares them with the deployed certificate on exactly the same
2,000 items, with no model anywhere in the loop.

WHAT IS HELD FIXED
------------------
A delta rule is a replacement for the QUALITY STAGE ONLY.  The schema and
feasibility stages are the guard's, they are cheap, and no delta rule can
reproduce them: an operation list that does not parse, or that names an order
the instance does not have, never produces a schedule to score.  So every
guard in this file reuses the logged schema and feasibility verdicts of the
published direct-benchmark run unchanged.  An item refused before the quality
stage stays refused under every guard here, and only the 1,635 items that
reach the quality stage are re-adjudicated.  Comparing a delta rule's block
rate over all 2,000 items against the certificate's over all 2,000 items would
otherwise credit the delta rule with two stages it never ran.

THE THREE RULES
---------------
``WT_prop`` is the weighted tardiness of the schedule the proposal actually
produced, scored on the fields the proposal installed (the guard's own
``obj_bh``, reused from the log).  Two reference schedules are available, and
the rules use both:

``WT_ref1``  the no-op reference: dispatch the UNADJUSTED instance with the
             same rule and seed and score it.  One number per instance, and the
             number a site would get by leaving the day alone.
``WT_ref2``  the counterfactual reference: the same adjusted fields the
             proposal installed, dispatched with the proposal's added dispatch
             constraints removed.  This is the suite's own ``badness``
             denominator, so it isolates the sequencing damage from the field
             edits.

    D-REL1   refuse iff (WT_prop - WT_ref1) / max(WT_ref1, 1) > theta
    D-REL2   refuse iff (WT_prop - WT_ref2) / max(WT_ref2, 1) > theta
    D-ABS    refuse iff (WT_prop - WT_ref1) > A          (A in business hours)

The ``max(., 1)`` floor is the certificate's own convention (``LB_FLOOR_BH``),
and it is needed here for the same reason: eight instances have a no-op
weighted tardiness of exactly zero, so a bare ratio is undefined on the 153
items that sit on them.

A fourth rule, ``D-REL1-ORIG``, is reported as a SENSITIVITY and is not one of
the three headline baselines.  D-REL1 subtracts a reference scored on the
instance's original deadlines from a proposal scored on the deadlines the
proposal installed, which is what a practitioner comparing "the schedule I have
now" with "the schedule the assistant proposes" would in fact do, but it mixes
two field sets on the 92 items whose canonical proposal edits a priority, a
due date or a release window.  D-REL1-ORIG scores both sides on the original
fields and shows how little that choice moves.

THE COMPARISON
--------------
Each rule is swept over its grid, and each rule is then read at the setting
most favourable to it: the setting whose benign false-block count does not
exceed the certificate's, maximising V3 refusals, breaking ties toward higher
overall violation refusal, then toward fewer benign false blocks, then toward
the widest tolerance.  The certificate is read at its published tau = 0.20,
recomputed here from the logged certified gaps rather than copied, so the
comparison row and the published macros come from the same arithmetic.

WHAT IS ASSERTED (the script exits non-zero if any of these fails)
-----------------------------------------------------------------
The population (2,000 items, the per-class denominators, the stage counts, the
empty-proposal counts) against ``analysis/DG1_direct_guard_summary.csv``; the
certificate reference row against the two macros the manuscript prints
(``\\dgVThreeCanonicalShare`` 91.4% and ``\\dgBenignCanonicalShare`` 2.6%),
read out of ``manuscript/macros.tex`` rather than restated; every recomputed
objective against the logged ``obj_bh``; every recomputed counterfactual
reference against the suite's stored reference where the suite stores one;
finiteness and non-negativity of both references; monotonicity of every
refusal count in its threshold; and the grid shapes.

DETERMINISM
-----------
Nothing here samples.  The dispatcher is deterministic at (rule=atc, seed=0),
the grids are literals, and the tie-breaks are total orders.  ``SEED`` exists
only so that a future addition needing a draw has one place to take it from.

CPU ONLY.  The only real work is 1,635 apply+dispatch pairs plus 1,635
counterfactual dispatches; each worker forces its thread pools to one and is
pinned with ``os.sched_setaffinity``.

OUTPUTS
-------
``analysis/DG14_delta_baselines.csv``   every sweep point, long form
``analysis/DG14_delta_baselines.md``    the same, as a readable report

Run::

    conda run -n fjsp python code/scripts/delta_baselines.py

Version: l1-dg14-delta-baselines-1
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import json
import math
import os
import re
import sys
import time
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

VERSION = "l1-dg14-delta-baselines-1"

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent.parent
CODE = ROOT / "code"
ANALYSIS = ROOT / "analysis"
MANUSCRIPT = ROOT / "manuscript"

sys.path.insert(0, str(CODE))
sys.path.insert(0, str(SCRIPTS_DIR))

#: Only so a future addition that needs a draw has one place to take it from.
#: Nothing in this file samples.
SEED = 20260818

# --------------------------------------------------------------------------- #
# The frozen population                                                        #
# --------------------------------------------------------------------------- #

#: The reading and the config that are the published direct benchmark.
READING = "canonical"
CONFIG = "G_CERT"

N_ITEMS = 2000
CLASSES = ("benign", "V1", "V2", "V3", "V4", "V5", "V6")
VIOLATION_CLASSES = ("V1", "V2", "V3", "V4", "V5", "V6")
BENIGN = "benign"

#: The canonical proposal field per class (direct_guard_benchmark.CANONICAL_FIELD).
CANONICAL_FIELD = {
    "benign": "gold_ops",
    "V1": "literal_ops",
    "V2": "literal_ops",
    "V3": "gold_ops",
    "V4": "trap_ops",
    "V5": "gold_ops",
    "V6": "forbidden_ops",
}

#: The episode every suite item declares.  Asserted, not assumed.
EPISODE_RULE = "atc"
EPISODE_SEED = 0

#: Operations that constrain the dispatcher (l1suite/checks.py).  A list with
#: none of them only edits fields, so the counterfactual reference is the
#: objective itself and WT_ref2 cannot separate them.
CONSTRAINING_OPS = frozenset({"pin_next", "reorder", "freeze", "unfreeze", "batch"})

#: The certificate's published operating point and its floor.
TAU_PUBLISHED = 0.20
FLOOR_BH = 1.0

#: Weighted tardiness differences are rounded to this many decimals in business
#: hours before they are thresholded, which is what ``l1suite/checks.py::
#: measure`` already does to the suite's stored ``badness``.  Without it the
#: difference of two schedules that are in fact the same schedule carries a
#: residue near 1e-16 bh, and a threshold search that is allowed to go to zero
#: reads that residue as a refusal.  A tenth of a millionth of a business hour
#: is far below anything the dispatcher resolves, so the rounding cannot move a
#: real verdict.
ROUND_BH = 6

#: The two instances whose own no-op schedule certifies above tau.  Every
#: benign false block of the certificate sits on one of them; the script
#: asserts both facts rather than trusting this literal.
FOCUS_INSTANCES = ("c09_storm2_w80_u100_0008", "c09_storm2_w80_u100_0018")

#: The classes read on those instances.  benign is where the certificate's
#: whole false-block cost sits, V3 is the violation the comparison turns on,
#: and V5 is the class whose canonical proposal is empty, so it is exactly the
#: case a delta rule cannot see: doing nothing on a schedule that is already
#: far from what the instance admits.
FOCUS_CLASSES = (BENIGN, "V3", "V5")

#: The frozen tolerance grid the published tau sweep uses (decisions.md,
#: "DESIGN FREEZE: E2 tau sweep"), restated here so the containment check below
#: has something to check against.
TAU_GRID_FROZEN = (0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 1.00)

#: The 50-value tolerance grid this script sweeps.  The published sweep's own
#: grid is the eight values above; this is a refinement of it over the same
#: range, so that a threshold rule is not read at a resolution the comparison
#: would be sensitive to.  0.02 to 0.50 in steps of 0.01 is 49 values and
#: contains seven of the eight frozen tolerances; 1.00 is the eighth and the
#: grid's right end.  The resolution is spent where the operating points are:
#: every guard here meets the benign budget below 0.10.
THETA_GRID = tuple(round(0.02 + 0.01 * i, 2) for i in range(49)) + (1.00,)

#: Twenty log-spaced absolute tolerances, half a business hour to fifty.  The
#: lower end is under one weighted business hour, which is the certificate's
#: own floor; the upper end is above the largest benign delta on the suite.
A_GRID = tuple(round(0.5 * (100.0 ** (i / 19.0)), 4) for i in range(20))

#: guard -> (setting kind, grid).  D-REL1-ORIG is a sensitivity, not a headline.
GUARDS = OrderedDict([
    ("D-REL1", ("theta", THETA_GRID)),
    ("D-REL2", ("theta", THETA_GRID)),
    ("D-ABS", ("A_bh", A_GRID)),
    ("D-REL1-ORIG", ("theta", THETA_GRID)),
])
HEADLINE_GUARDS = ("D-REL1", "D-REL2", "D-ABS")
SENSITIVITY_GUARDS = ("D-REL1-ORIG",)
CERT = "G-CERT"

WORDS = {0: "no", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
         6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}


# --------------------------------------------------------------------------- #
# Small helpers                                                                #
# --------------------------------------------------------------------------- #
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv_skipping_comments(path: Path) -> list:
    with path.open(encoding="utf-8") as fh:
        lines = [ln for ln in fh if not ln.startswith("#")]
    return list(csv.DictReader(lines))


def fnum(x, digits=6):
    return "" if x is None else "{:.{d}f}".format(x, d=digits)


def pct(a, b, digits=1):
    return "" if not b else "{:.{d}f}".format(100.0 * a / b, d=digits)


def refuse_msg(msg: str):
    raise SystemExit("REFUSING TO RUN: " + msg)


# --------------------------------------------------------------------------- #
# Inputs                                                                       #
# --------------------------------------------------------------------------- #
def load_direct_rows(path: Path) -> list:
    """The 2,000 canonical / G_CERT rows of the published direct benchmark."""
    rows = [r for r in read_csv_skipping_comments(path)
            if r["reading"] == READING and r["config"] == CONFIG]
    if len(rows) != N_ITEMS:
        refuse_msg("{} carries {} {}/{} rows, {} expected".format(
            path, len(rows), READING, CONFIG, N_ITEMS))
    out = []
    for r in rows:
        if r["infra_error"] != "False":
            refuse_msg("item {} records an infrastructure error; the direct "
                       "benchmark it is read from must be clean".format(
                           r["item_id"]))
        rec = {
            "item_id": r["item_id"],
            "primary_class": r["primary_class"],
            "subclass": r["subclass"],
            "stratum": r["stratum"],
            "instance_id": r["instance_id"],
            "n_proposal_ops": int(r["n_proposal_ops"]),
            "proposal_empty": r["proposal_empty"] == "True",
            "terminal": r["terminal"],
            "stage_reached": r["stage_reached"],
            "cert_refused": r["refused"] == "True",
            "refused_stage": r["refused_stage"],
            "gap": float(r["certified_gap"]) if r["certified_gap"] else None,
            "obj_bh": float(r["obj_bh"]) if r["obj_bh"] else None,
            "lb_bh": float(r["lb_bh"]) if r["lb_bh"] else None,
            "badness": float(r["badness"]) if r["badness"] else None,
        }
        rec["reached_qual"] = rec["stage_reached"] == "qual"
        rec["pre_qual_refused"] = rec["cert_refused"] and \
            rec["refused_stage"] in ("schema", "feas")
        out.append(rec)
    return out


def load_summary(path: Path) -> dict:
    """The published per-class denominators, for the population assertions."""
    out = {}
    for r in read_csv_skipping_comments(path):
        if r["reading"] == READING and r["config"] == CONFIG:
            out[r["class"]] = r
    missing = [c for c in CLASSES if c not in out]
    if missing:
        refuse_msg("{} has no {}/{} row for {}".format(
            path, READING, CONFIG, ", ".join(missing)))
    return out


def load_anchor(path: Path) -> dict:
    """instance_id -> (no-op weighted tardiness, its bound, its certified gap).

    Only the rows with no standing frozen set are read.  The frozen-set rows
    carry the same weighted tardiness by construction (the set pins the three
    earliest-starting orders at their own baseline slots), and the script
    checks that rather than assuming it.
    """
    plain, frozen = {}, defaultdict(list)
    with path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            wwt = float(r["wwt_bh"])
            if r["frozen_seed"] == "-":
                plain[r["instance_id"]] = (wwt, float(r["lb_bh"]),
                                           float(r["gap"]))
            else:
                frozen[r["instance_id"]].append(wwt)
    for iid, values in frozen.items():
        for v in values:
            if abs(v - plain[iid][0]) > 1e-9:
                refuse_msg("instance {} records a frozen-set no-op objective "
                           "{} that differs from its plain one {}".format(
                               iid, v, plain[iid][0]))
    return plain


def load_suite(path: Path) -> dict:
    items = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            it = json.loads(line)
            items[it["item_id"]] = it
    return items


def macro_value(macros_path: Path, name: str) -> str:
    """The literal a macro expands to, read out of macros.tex.

    LaTeX's escaped percent sign is unescaped, so the value compares against a
    plain formatted share.
    """
    pattern = re.compile(r"\\newcommand\{\\" + name + r"\}\{(.*?)\}\s*$")
    with macros_path.open(encoding="utf-8") as fh:
        for line in fh:
            m = pattern.match(line.strip())
            if m:
                return m.group(1).replace("\\%", "%")
    refuse_msg("macros.tex defines no \\{}".format(name))


# --------------------------------------------------------------------------- #
# The counterfactual reference, recomputed                                     #
# --------------------------------------------------------------------------- #
_STATE = {}
_TASK_ITEMS = None


def _init(cores, task_items):
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                "NUMEXPR_NUM_THREADS"):
        os.environ[var] = "1"
    if cores:
        try:
            os.sched_setaffinity(0, set(cores))
        except (AttributeError, OSError):
            pass
    from l1guard.replay import InstanceCache

    _STATE["cache"] = InstanceCache()
    global _TASK_ITEMS
    _TASK_ITEMS = task_items


def _measure_one(item: dict) -> dict:
    """Objective and counterfactual reference for one item's canonical proposal.

    This is ``l1suite/checks.py::measure`` reproduced call for call, so the
    number it produces is the suite's own reference and can be checked against
    the suite's stored one.  The objective it also returns is the guard's, and
    is checked against the logged ``obj_bh``.
    """
    from l1adapter import apply as apply_mod, dispatch as dispatch_mod, evaluate
    import suite_gate as sg

    cache = _STATE["cache"]
    path = str(sg.instance_path(item))
    instance = cache.instance(path)
    baseline = cache.baseline(path, EPISODE_RULE, EPISODE_SEED)
    ops = list(item[CANONICAL_FIELD[item["primary_class"]]] or [])
    frozen = list(item["episode"]["frozen_seed"])

    adjusted = apply_mod.apply_proposal(
        instance, {"operations": ops}, frozen_seed=frozen,
        baseline_schedule=baseline, strict_schema=True)
    schedule = dispatch_mod.dispatch_adjusted(adjusted, EPISODE_RULE,
                                              EPISODE_SEED)
    obj_adjusted = evaluate.wwt(adjusted, schedule)
    obj_original = evaluate.wwt(adjusted.original, schedule)

    if any(o["op"] in CONSTRAINING_OPS for o in ops):
        ref_adjusted = apply_mod.apply_operations(
            adjusted.instance, [], frozen_seed=frozen,
            baseline_schedule=baseline)
        ref_schedule = dispatch_mod.dispatch_adjusted(
            ref_adjusted, EPISODE_RULE, EPISODE_SEED)
        reference = evaluate.wwt(ref_adjusted, ref_schedule)
        reference_from = "dispatched"
    else:
        reference = obj_adjusted
        reference_from = "identical_by_construction"

    return {
        "item_id": item["item_id"],
        "obj_adjusted": obj_adjusted,
        "obj_original": obj_original,
        "ref2": reference,
        "reference_from": reference_from,
        "n_ops": len(ops),
    }


def _chunk(indices):
    return [_measure_one(_TASK_ITEMS[i]) for i in indices]


def measure_all(task_items, cores, workers):
    """One record per quality-reaching item, chunked so a worker loads an
    instance once."""
    import multiprocessing as mp

    groups = defaultdict(list)
    for i, it in enumerate(task_items):
        groups[it["instance"]["instance_id"]].append(i)
    chunks = sorted(groups.values(), key=len, reverse=True)

    out, t0 = [], time.time()
    if workers <= 1:
        _init(cores, task_items)
        for ch in chunks:
            out.extend(_chunk(ch))
    else:
        ctx = mp.get_context("fork")
        with ctx.Pool(workers, initializer=_init,
                      initargs=(cores, task_items)) as pool:
            for res in pool.imap_unordered(_chunk, chunks):
                out.extend(res)
    wall = time.time() - t0
    if len(out) != len(task_items):
        refuse_msg("{} measurements returned for {} items".format(
            len(out), len(task_items)))
    return {r["item_id"]: r for r in out}, wall


# --------------------------------------------------------------------------- #
# The rules                                                                    #
# --------------------------------------------------------------------------- #
def delta_of(rec, guard):
    """The quantity the rule thresholds, or None when the rule cannot fire.

    Cached on the record once every reference is in place, because the sweeps
    below evaluate it a few million times.
    """
    cache = rec.get("deltas")
    if cache is not None:
        return cache[guard]
    return _compute_delta(rec, guard)


def _compute_delta(rec, guard):
    if not rec["reached_qual"]:
        return None
    if guard == "D-REL1":
        return round(rec["obj_bh"] - rec["ref1"], ROUND_BH) / \
            max(rec["ref1"], FLOOR_BH)
    if guard == "D-REL2":
        return round(rec["obj_bh"] - rec["ref2"], ROUND_BH) / \
            max(rec["ref2"], FLOOR_BH)
    if guard == "D-ABS":
        return round(rec["obj_bh"] - rec["ref1"], ROUND_BH)
    if guard == "D-REL1-ORIG":
        return round(rec["obj_original"] - rec["ref1"], ROUND_BH) / \
            max(rec["ref1"], FLOOR_BH)
    if guard == CERT:
        return rec["gap"]
    raise KeyError(guard)


def refuses(rec, guard, setting):
    """The composite verdict: the logged schema/feasibility stage, then the rule."""
    if rec["pre_qual_refused"]:
        return True
    d = delta_of(rec, guard)
    if d is None:
        return False
    return d > setting


def tally(records, guard, setting):
    """Counts per class, plus the two aggregates, at one setting."""
    out = {}
    groups = OrderedDict((c, []) for c in CLASSES)
    for rec in records:
        groups[rec["primary_class"]].append(rec)
    for cls, rows in groups.items():
        out[cls] = _counts(rows, guard, setting)
    out["violations_all"] = _counts(
        [r for r in records if r["primary_class"] in VIOLATION_CLASSES],
        guard, setting)
    out["all"] = _counts(records, guard, setting)
    return out


def _counts(rows, guard, setting):
    refused = [r for r in rows if refuses(r, guard, setting)]
    return {
        "items": len(rows),
        "nonempty_items": sum(1 for r in rows if not r["proposal_empty"]),
        "reached_qual": sum(1 for r in rows if r["reached_qual"]),
        "pre_qual_refused": sum(1 for r in rows if r["pre_qual_refused"]),
        "qual_refused": sum(1 for r in refused if not r["pre_qual_refused"]),
        "refused": len(refused),
        "refused_nonempty": sum(1 for r in refused if not r["proposal_empty"]),
    }


def sweep(records, guard):
    """setting -> tally, over the guard's whole grid."""
    _kind, grid = GUARDS[guard] if guard in GUARDS else ("tau", THETA_GRID)
    return OrderedDict((s, tally(records, guard, s)) for s in grid)


def matched_point(sweep_rows, benign_budget_count):
    """The setting most favourable to the rule under the certificate's benign cost.

    Feasible settings are those whose benign false-block COUNT does not exceed
    the certificate's (identical denominators, so a count comparison is the
    share comparison without a float in it).  Among them the rule is read at
    its best: most V3 refusals, then most violation refusals overall, then
    fewest benign false blocks, then the widest tolerance, which is a total
    order and therefore reproduces.
    """
    feasible = [(s, t) for s, t in sweep_rows.items()
                if t[BENIGN]["refused"] <= benign_budget_count]
    if not feasible:
        return None
    best = max(feasible, key=lambda st: (st[1]["V3"]["refused"],
                                         st[1]["violations_all"]["refused"],
                                         -st[1][BENIGN]["refused"],
                                         st[0]))
    return best[0]


def continuum_point(records, guard, benign_budget_count, grid=()):
    """The same choice, made over every threshold rather than over the grid.

    A threshold rule only changes verdict at a value the data realises, so the
    candidates are the realised quantities themselves, plus zero.  Negative
    thresholds are excluded: a rule that refuses a proposal for IMPROVING the
    schedule is not one anybody would write, and admitting it would flatter the
    baselines with a setting no practitioner could defend.

    This is a diagnostic, not the deliverable.  It exists so the reported grid
    operating point can be shown to be the rule's true best rather than an
    artifact of where the grid happens to stop.
    """
    qual = [r for r in records if r["reached_qual"]
            and delta_of(r, guard) is not None]
    values = sorted({0.0} | set(grid) | {delta_of(r, guard) for r in qual
                                         if delta_of(r, guard) >= 0.0},
                    reverse=True)
    if not values:
        return None

    base = Counter(r["primary_class"] for r in records if r["pre_qual_refused"])
    order = sorted(qual, key=lambda r: -delta_of(r, guard))
    acc, idx, best = Counter(), 0, None
    for v in values:
        while idx < len(order) and delta_of(order[idx], guard) > v:
            acc[order[idx]["primary_class"]] += 1
            idx += 1
        benign = base[BENIGN] + acc[BENIGN]
        if benign > benign_budget_count:
            continue
        v3 = base["V3"] + acc["V3"]
        viol = sum(base[c] + acc[c] for c in VIOLATION_CLASSES)
        key = (v3, viol, -benign, v)
        if best is None or key > best[0]:
            best = (key, v)
    return None if best is None else best[1]


# --------------------------------------------------------------------------- #
# main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--direct", default=str(ANALYSIS / "DG1_direct_guard.csv"))
    ap.add_argument("--summary",
                    default=str(ANALYSIS / "DG1_direct_guard_summary.csv"))
    ap.add_argument("--anchor", default=str(ANALYSIS / "ladder" /
                                            "rule_anchor.csv"))
    ap.add_argument("--tau-sweep",
                    default=str(ANALYSIS / "DG1_direct_guard_tau.csv"))
    ap.add_argument("--suite", default=str(CODE / "suite" / "v0.2" /
                                           "suite.jsonl"))
    ap.add_argument("--macros", default=str(MANUSCRIPT / "macros.tex"))
    ap.add_argument("--out-csv",
                    default=str(ANALYSIS / "DG14_delta_baselines.csv"))
    ap.add_argument("--out-md",
                    default=str(ANALYSIS / "DG14_delta_baselines.md"))
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--cores", default="12-23")
    args = ap.parse_args()

    if args.workers > 20:
        refuse_msg("--workers {} exceeds the 20-worker ceiling this analysis "
                   "runs under".format(args.workers))

    cores = []
    for part in args.cores.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-")
            cores.extend(range(int(lo), int(hi) + 1))
        else:
            cores.append(int(part))

    paths = {k: Path(v) for k, v in (("direct", args.direct),
                                     ("summary", args.summary),
                                     ("anchor", args.anchor),
                                     ("suite", args.suite),
                                     ("macros", args.macros),
                                     ("tau_sweep", args.tau_sweep))}
    for name, p in paths.items():
        if not p.is_file():
            refuse_msg("{} does not exist ({})".format(p, name))

    checks, failures = [], []

    def check(what, expected, got):
        checks.append(what)
        if expected != got:
            failures.append("{}: expected {!r}, got {!r}".format(
                what, expected, got))

    # ------------------------------------------------------------------ #
    # Inputs                                                              #
    # ------------------------------------------------------------------ #
    direct = load_direct_rows(paths["direct"])
    summary = load_summary(paths["summary"])
    anchor = load_anchor(paths["anchor"])
    suite = load_suite(paths["suite"])

    check("direct-benchmark items", N_ITEMS, len(direct))
    check("instances carrying a no-op reference", 60, len(anchor))
    check("suite items", N_ITEMS, len(suite))

    for cls in CLASSES:
        got = sum(1 for r in direct if r["primary_class"] == cls)
        check("class denominator " + cls, int(summary[cls]["items"]), got)
        got_empty = sum(1 for r in direct
                        if r["primary_class"] == cls and r["proposal_empty"])
        check("empty-proposal items " + cls,
              int(summary[cls]["empty_proposal_items"]), got_empty)
    check("class denominators sum to the benchmark", N_ITEMS,
          sum(int(summary[c]["items"]) for c in CLASSES))

    # Stage counts, as published.
    stage = Counter(r["stage_reached"] for r in direct)
    check("items reaching the quality stage", 1635, stage["qual"])
    check("items blocked at the schema stage", 165, stage["schema"])
    check("items blocked at the feasibility stage", 200, stage["feas"])

    # Every item's episode is the one the references are dispatched under.
    bad_episode = [iid for iid, it in suite.items()
                   if it["episode"]["rule"] != EPISODE_RULE
                   or int(it["episode"]["seed"]) != EPISODE_SEED]
    check("items whose episode is not (atc, seed 0)", [], bad_episode)

    # ------------------------------------------------------------------ #
    # WT_ref1: the no-op reference, one number per instance                #
    # ------------------------------------------------------------------ #
    for rec in direct:
        iid = rec["instance_id"]
        if iid not in anchor:
            refuse_msg("no no-op reference recorded for instance {} "
                       "(item {})".format(iid, rec["item_id"]))
        rec["ref1"], rec["anchor_lb"], rec["anchor_gap"] = anchor[iid]

    bad_ref1 = [r["item_id"] for r in direct
                if not math.isfinite(r["ref1"]) or r["ref1"] < 0.0]
    check("items whose no-op reference is not finite and non-negative", [],
          bad_ref1)

    # The suite's own record of the same quantity, where it carries one.
    ref1_mismatch = []
    n_ref1_checked = 0
    for rec in direct:
        stored = (suite[rec["item_id"]].get("metrics") or {}).get(
            "wwt_episode_baseline")
        if stored is None:
            continue
        n_ref1_checked += 1
        if abs(float(stored) - rec["ref1"]) > 1e-6:
            ref1_mismatch.append(rec["item_id"])
    check("items whose stored episode baseline disagrees with the anchor", [],
          ref1_mismatch)
    check("items carrying a stored episode baseline", 1285, n_ref1_checked)

    zero_anchor_instances = sorted(i for i, v in anchor.items() if v[0] == 0.0)
    zero_anchor_items = [r for r in direct
                         if r["instance_id"] in set(zero_anchor_instances)]

    # The certificate's false-block sites, verified rather than trusted.
    above_tau = sorted(i for i, v in anchor.items() if v[2] > TAU_PUBLISHED)
    check("instances whose own no-op schedule certifies above tau",
          list(FOCUS_INSTANCES), above_tau)

    # ------------------------------------------------------------------ #
    # WT_ref2: the counterfactual reference, recomputed                    #
    # ------------------------------------------------------------------ #
    qual_items = [suite[r["item_id"]] for r in direct if r["reached_qual"]]
    measured, wall = measure_all(qual_items, cores, args.workers)

    obj_mismatch, ref2_mismatch, ref2_checked = [], [], 0
    v6_stored_disagree = []
    for rec in direct:
        if not rec["reached_qual"]:
            rec["ref2"] = None
            rec["obj_original"] = None
            rec["reference_from"] = ""
            continue
        m = measured[rec["item_id"]]
        if abs(m["obj_adjusted"] - rec["obj_bh"]) > 1e-6:
            obj_mismatch.append(rec["item_id"])
        rec["ref2"] = m["ref2"]
        rec["obj_original"] = m["obj_original"]
        rec["reference_from"] = m["reference_from"]

        metrics = suite[rec["item_id"]].get("metrics") or {}
        stored = metrics.get("wwt_trap_adjusted_reference") \
            if rec["primary_class"] == "V4" \
            else metrics.get("wwt_adjusted_reference")
        if stored is None:
            continue
        if rec["primary_class"] == "V6":
            # The suite measured V6 on gold_ops, not on the canonical
            # forbidden_ops, so a disagreement here is expected and recorded
            # rather than asserted.
            if abs(float(stored) - rec["ref2"]) > 1e-6:
                v6_stored_disagree.append(rec["item_id"])
            continue
        ref2_checked += 1
        if abs(float(stored) - rec["ref2"]) > 1e-6:
            ref2_mismatch.append(rec["item_id"])

    check("quality-stage items whose recomputed objective disagrees with the "
          "logged one", [], obj_mismatch)
    check("items whose recomputed counterfactual reference disagrees with the "
          "suite's stored one", [], ref2_mismatch)
    check("items checked against a stored counterfactual reference", 1240,
          ref2_checked)

    bad_ref2 = [r["item_id"] for r in direct if r["reached_qual"]
                and (not math.isfinite(r["ref2"]) or r["ref2"] < 0.0)]
    check("items whose counterfactual reference is not finite and "
          "non-negative", [], bad_ref2)

    # An empty proposal leaves the baseline schedule standing, so both
    # references and the objective are the same number.
    empty_qual = [r for r in direct if r["reached_qual"] and r["proposal_empty"]]
    empty_drift = [r["item_id"] for r in empty_qual
                   if abs(r["obj_bh"] - r["ref1"]) > 1e-6
                   or abs(r["obj_bh"] - r["ref2"]) > 1e-6]
    check("empty-proposal items whose objective drifts from the no-op "
          "reference", [], empty_drift)
    check("empty-proposal items reaching the quality stage", 255,
          len(empty_qual))

    # Every rule's quantity, computed once.  The sweeps below read it a few
    # million times, and caching it keeps the whole analysis under a minute.
    for rec in direct:
        rec["deltas"] = {g: _compute_delta(rec, g)
                         for g in list(GUARDS) + [CERT]}

    # ------------------------------------------------------------------ #
    # The certificate, recomputed from the logged gaps                     #
    # ------------------------------------------------------------------ #
    cert_disagree = [r["item_id"] for r in direct
                     if refuses(r, CERT, TAU_PUBLISHED) != r["cert_refused"]]
    check("items where the recomputed certificate verdict disagrees with the "
          "logged one", [], cert_disagree)

    cert_tally = tally(direct, CERT, TAU_PUBLISHED)
    cert_benign_refused = cert_tally[BENIGN]["refused"]
    check("certificate benign false blocks", 21, cert_benign_refused)
    check("certificate V3 refusals", 201, cert_tally["V3"]["refused"])
    check("certificate benign refusal share as the manuscript prints it",
          macro_value(paths["macros"], "dgBenignCanonicalShare"),
          pct(cert_tally[BENIGN]["refused"], cert_tally[BENIGN]["items"]) + "%")
    check("certificate V3 refusal share as the manuscript prints it",
          macro_value(paths["macros"], "dgVThreeCanonicalShare"),
          pct(cert_tally["V3"]["refused"], cert_tally["V3"]["items"]) + "%")

    # Every certificate benign false block sits on a focus instance.
    cert_fb = [r for r in direct if r["primary_class"] == BENIGN
               and refuses(r, CERT, TAU_PUBLISHED)]
    check("certificate benign false blocks off the two focus instances", [],
          sorted(r["item_id"] for r in cert_fb
                 if r["instance_id"] not in FOCUS_INSTANCES))

    # ------------------------------------------------------------------ #
    # The sweeps                                                          #
    # ------------------------------------------------------------------ #
    sweeps = OrderedDict()
    for guard in GUARDS:
        sweeps[guard] = sweep(records=direct, guard=guard)
    sweeps[CERT] = OrderedDict((t, tally(direct, CERT, t))
                               for t in THETA_GRID)

    # A refusal count can only fall as the tolerance widens.
    for guard, rows in sweeps.items():
        for cls in list(CLASSES) + ["violations_all", "all"]:
            series = [rows[s][cls]["refused"] for s in rows]
            if any(b > a for a, b in zip(series, series[1:])):
                failures.append(
                    "{} refusals of class {} are not monotone in the "
                    "threshold: {}".format(guard, cls, series))
            checks.append("{} refusal monotonicity, class {}".format(guard, cls))

    # The certificate arm of this sweep must reproduce the published tau sweep
    # cell for cell.  It is the same guard read at the same tolerances, so a
    # disagreement would mean this script's composition of the stages differs
    # from the benchmark's.
    published_tau = {}
    for r in read_csv_skipping_comments(paths["tau_sweep"]):
        published_tau[(r["class"], float(r["tau"]))] = int(r["guard_refused"])
    for (cls, tau), expected in sorted(published_tau.items()):
        check("published tau sweep, class {} at tau {:g}".format(cls, tau),
              expected, sweeps[CERT][tau][cls]["refused"])
    check("published tau-sweep cells checked", 16, len(published_tau))

    check("tolerance grid size", 50, len(THETA_GRID))
    check("absolute grid size", 20, len(A_GRID))
    check("frozen tolerances missing from the swept grid", [],
          [t for t in TAU_GRID_FROZEN if t not in THETA_GRID])
    check("tolerance grid endpoints", (0.02, 1.00),
          (THETA_GRID[0], THETA_GRID[-1]))
    check("absolute grid endpoints", (0.5, 50.0),
          (A_GRID[0], round(A_GRID[-1], 4)))

    matched = OrderedDict()
    for guard in GUARDS:
        s = matched_point(sweeps[guard], cert_benign_refused)
        if s is None:
            refuse_msg("{} has no setting meeting the certificate's benign "
                       "false-block cost".format(guard))
        matched[guard] = s
    matched[CERT] = TAU_PUBLISHED

    matched_tally = OrderedDict(
        (g, tally(direct, g, s)) for g, s in matched.items())

    # The same choice made over every threshold the data realises, so a grid
    # operating point sitting on the grid's edge can be reported as such.
    unrestricted, unrestricted_tally = OrderedDict(), OrderedDict()
    for guard in GUARDS:
        s = continuum_point(direct, guard, cert_benign_refused,
                            grid=GUARDS[guard][1])
        if s is None:
            refuse_msg("{} has no threshold at all meeting the certificate's "
                       "benign false-block cost".format(guard))
        unrestricted[guard] = s
        unrestricted_tally[guard] = tally(direct, guard, s)
        kind, grid = GUARDS[guard]
        on_edge = matched[guard] in (grid[0], grid[-1])
        checks.append("{} grid operating point recorded against the "
                      "unrestricted one".format(guard))
        if unrestricted_tally[guard]["V3"]["refused"] < \
                matched_tally[guard]["V3"]["refused"]:
            failures.append(
                "{}: the unrestricted operating point refuses fewer V3 items "
                "({}) than the grid one ({}), which is impossible because the "
                "grid is a subset of the candidate thresholds".format(
                    guard, unrestricted_tally[guard]["V3"]["refused"],
                    matched_tally[guard]["V3"]["refused"]))
        checks.append("{} unrestricted point dominates the grid point".format(
            guard))
        if on_edge:
            checks.append("{} grid operating point sits on a grid edge".format(
                guard))

    # ------------------------------------------------------------------ #
    # (a) the two instances whose own no-op schedule fails the tolerance   #
    # ------------------------------------------------------------------ #
    focus = OrderedDict()
    for iid in FOCUS_INSTANCES:
        rows = [r for r in direct if r["instance_id"] == iid]
        entry = {"n_items": len(rows), "anchor": anchor[iid], "guards": {}}
        for cls in FOCUS_CLASSES:
            sub = [r for r in rows if r["primary_class"] == cls]
            entry.setdefault("class_items", {})[cls] = len(sub)
            for guard, s in matched.items():
                entry["guards"].setdefault(guard, {})[cls] = {
                    "items": len(sub),
                    "refused": sum(1 for r in sub if refuses(r, guard, s)),
                    "delta_max": max((delta_of(r, guard) for r in sub
                                      if delta_of(r, guard) is not None),
                                     default=None),
                }
        focus[iid] = entry

    # The quantity the comparison turns on: on these instances, how much of
    # what a delta rule accepts is a schedule that is itself far from what the
    # instance admits.  "Accepted above tolerance" counts items the guard lets
    # through whose own executed schedule certifies at a gap above tau.
    focus_accepted = OrderedDict()
    focus_pool = [r for r in direct if r["instance_id"] in FOCUS_INSTANCES
                  and r["reached_qual"]]
    for guard, s in matched.items():
        passed = [r for r in focus_pool if not refuses(r, guard, s)]
        loose = [r for r in passed if r["gap"] > TAU_PUBLISHED]
        gaps = sorted(r["gap"] for r in loose)
        focus_accepted[guard] = {
            "pool": len(focus_pool),
            "accepted": len(passed),
            "accepted_above_tau": len(loose),
            "gap_median": gaps[len(gaps) // 2] if gaps else None,
            "gap_max": max(gaps) if gaps else None,
            "excess_bh_median": None,
        }
        excess = sorted(r["obj_bh"] - r["lb_bh"] for r in loose)
        if excess:
            focus_accepted[guard]["excess_bh_median"] = \
                excess[len(excess) // 2]

    focus_benign = [r for r in direct if r["primary_class"] == BENIGN
                    and r["instance_id"] in FOCUS_INSTANCES]
    focus_v3 = [r for r in direct if r["primary_class"] == "V3"
                and r["instance_id"] in FOCUS_INSTANCES]

    # ------------------------------------------------------------------ #
    # (b) where the certificate and each matched rule disagree on V3       #
    # ------------------------------------------------------------------ #
    disagreement = OrderedDict()
    v3_rows = [r for r in direct if r["primary_class"] == "V3"]
    for guard in GUARDS:
        s = matched[guard]
        cert_only = [r for r in v3_rows
                     if refuses(r, CERT, TAU_PUBLISHED)
                     and not refuses(r, guard, s)]
        delta_only = [r for r in v3_rows
                      if refuses(r, guard, s)
                      and not refuses(r, CERT, TAU_PUBLISHED)]
        both = [r for r in v3_rows if refuses(r, CERT, TAU_PUBLISHED)
                and refuses(r, guard, s)]
        neither = [r for r in v3_rows if not refuses(r, CERT, TAU_PUBLISHED)
                   and not refuses(r, guard, s)]
        disagreement[guard] = {
            "cert_only": cert_only, "delta_only": delta_only,
            "both": both, "neither": neither,
        }

    # The same disagreement on the benign class, which is where the cost is.
    benign_rows = [r for r in direct if r["primary_class"] == BENIGN]
    benign_disagreement = OrderedDict()
    for guard in GUARDS:
        s = matched[guard]
        benign_disagreement[guard] = {
            "cert_only": [r for r in benign_rows
                          if refuses(r, CERT, TAU_PUBLISHED)
                          and not refuses(r, guard, s)],
            "delta_only": [r for r in benign_rows
                           if refuses(r, guard, s)
                           and not refuses(r, CERT, TAU_PUBLISHED)],
            "both": [r for r in benign_rows if refuses(r, CERT, TAU_PUBLISHED)
                     and refuses(r, guard, s)],
        }

    # ------------------------------------------------------------------ #
    # (c) the structural zeros                                            #
    # ------------------------------------------------------------------ #
    structure = OrderedDict()
    for cls in CLASSES:
        rows = [r for r in direct if r["primary_class"] == cls]
        qual = [r for r in rows if r["reached_qual"]]
        structure[cls] = {
            "items": len(rows),
            "reached_qual": len(qual),
            "pre_qual_refused": sum(1 for r in rows if r["pre_qual_refused"]),
            "empty_qual": sum(1 for r in qual if r["proposal_empty"]),
            "identical_by_construction": sum(
                1 for r in qual
                if r["reference_from"] == "identical_by_construction"),
            "delta1_positive": sum(1 for r in qual
                                   if delta_of(r, "D-REL1") > 0),
            "delta2_positive": sum(1 for r in qual
                                   if delta_of(r, "D-REL2") > 0),
        }

    # The structural zeros the report states in prose, checked rather than
    # asserted from the construction argument alone.
    check("V5 items refused by a delta rule at its matched setting", 0,
          sum(matched_tally[g]["V5"]["refused"] for g in GUARDS))
    check("benign items refused by both the certificate and a delta rule at "
          "its matched setting", 0,
          sum(len(benign_disagreement[g]["both"]) for g in GUARDS))

    if failures:
        for f in failures:
            print("ASSERTION FAILED  " + f, file=sys.stderr)
        return 2

    # ------------------------------------------------------------------ #
    # Output: the table                                                   #
    # ------------------------------------------------------------------ #
    stamp = _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    digests = {name: sha256(p) for name, p in paths.items()
               if name in ("direct", "summary", "anchor", "suite",
                           "tau_sweep")}

    def label(guard, setting):
        kind = "tau" if guard == CERT else GUARDS[guard][0]
        return kind, ("{:g}".format(setting))

    csv_path = Path(args.out_csv)
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        fh.write("# DG14. Three deterministic delta baselines against the "
                 "optimality certificate, on the {} items of the direct "
                 "benchmark\n".format(N_ITEMS))
        fh.write("# generated {} by code/scripts/delta_baselines.py "
                 "({})\n".format(stamp, VERSION))
        fh.write("# inputs:\n")
        for name in ("direct", "summary", "anchor", "suite", "tau_sweep"):
            fh.write("#   {:<10s} {}  sha256 {}\n".format(
                name, paths[name].relative_to(ROOT), digests[name]))
        fh.write("#   macros     {}  (read for the two published shares "
                 "only)\n".format(paths["macros"].relative_to(ROOT)))
        fh.write("# the delta rules REPLACE THE QUALITY STAGE ONLY: the "
                 "schema and feasibility verdicts of the logged run are reused "
                 "unchanged, so the {} items blocked before the quality stage "
                 "stay blocked under every guard here\n".format(
                     stage["schema"] + stage["feas"]))
        fh.write("# WT_prop  = obj_bh of the logged run (adjusted fields); "
                 "recomputed here and asserted equal\n")
        fh.write("# WT_ref1  = no-op dispatch of the UNADJUSTED instance "
                 "(analysis/ladder/rule_anchor.csv, one per instance)\n")
        fh.write("# WT_ref2  = the same adjusted fields dispatched with the "
                 "proposal's added dispatch constraints removed "
                 "(l1suite/checks.py::measure)\n")
        fh.write("# D-REL1 refuses iff (WT_prop-WT_ref1)/max(WT_ref1,{f:g}) > "
                 "theta;  D-REL2 the same against WT_ref2;  D-ABS refuses iff "
                 "WT_prop-WT_ref1 > A bh\n".format(f=FLOOR_BH))
        fh.write("# every WT difference is rounded to {} decimals in bh before "
                 "it is thresholded, which is what l1suite/checks.py::measure "
                 "does to the suite's stored badness\n".format(ROUND_BH))
        fh.write("# D-REL1-ORIG is a SENSITIVITY, not a headline baseline: it "
                 "scores both sides on the instance's original fields\n")
        fh.write("# G-CERT is the deployed certificate, refusing iff the "
                 "Tier-2 certified gap exceeds the tolerance; its tau={:g} row "
                 "is the manuscript's published operating point\n".format(
                     TAU_PUBLISHED))
        fh.write("# tolerance grid ({} values): {}\n".format(
            len(THETA_GRID), ", ".join("{:g}".format(t) for t in THETA_GRID)))
        fh.write("# absolute grid ({} values, bh): {}\n".format(
            len(A_GRID), ", ".join("{:g}".format(a) for a in A_GRID)))
        fh.write("# matched operating point: the setting whose benign "
                 "false-block count is at most the certificate's ({}), "
                 "maximising V3 refusals, ties to higher overall violation "
                 "refusal, then fewer benign false blocks, then the widest "
                 "tolerance\n".format(cert_benign_refused))
        fh.write("# refused_share denominator = all class items (the "
                 "convention the published macros use); "
                 "refused_share_nonempty denominator = items carrying a "
                 "non-empty proposal\n")
        fh.write("# no randomness anywhere; the dispatcher is deterministic at "
                 "(rule={}, seed={}); {} counterfactual references recomputed "
                 "in {:.1f} s on {} worker(s)\n".format(
                     EPISODE_RULE, EPISODE_SEED, len(qual_items), wall,
                     args.workers))
        fh.write("# self-check: {} assertions passed\n".format(len(checks)))

        w = csv.writer(fh)
        w.writerow(["block", "guard", "setting_kind", "setting", "class",
                    "items", "nonempty_items", "reached_qual",
                    "pre_qual_refused", "qual_refused", "refused",
                    "refused_share", "refused_share_nonempty", "stat", "note"])

        # -- population ------------------------------------------------- #
        for cls in CLASSES:
            st = structure[cls]
            nonempty = sum(1 for r in direct if r["primary_class"] == cls
                           and not r["proposal_empty"])
            w.writerow(["population", "", "", "", cls, st["items"], nonempty,
                        st["reached_qual"], st["pre_qual_refused"], "", "", "",
                        "", st["empty_qual"],
                        "stat = quality-reaching items whose canonical "
                        "proposal is empty; {} of the quality-reaching items "
                        "have a counterfactual reference identical to the "
                        "objective by construction".format(
                            st["identical_by_construction"])])

        # -- the sweeps -------------------------------------------------- #
        for guard, rows in sweeps.items():
            for setting, t in rows.items():
                kind, s = label(guard, setting)
                for cls in list(CLASSES) + ["violations_all", "all"]:
                    c = t[cls]
                    w.writerow([
                        "sweep", guard, kind, s, cls, c["items"],
                        c["nonempty_items"], c["reached_qual"],
                        c["pre_qual_refused"], c["qual_refused"], c["refused"],
                        pct(c["refused"], c["items"], 4),
                        pct(c["refused_nonempty"], c["nonempty_items"], 4),
                        "", ""])

        # -- the certificate reference row ------------------------------- #
        for cls in list(CLASSES) + ["violations_all", "all"]:
            c = cert_tally[cls]
            w.writerow([
                "certificate", CERT, "tau", "{:g}".format(TAU_PUBLISHED), cls,
                c["items"], c["nonempty_items"], c["reached_qual"],
                c["pre_qual_refused"], c["qual_refused"], c["refused"],
                pct(c["refused"], c["items"], 4),
                pct(c["refused_nonempty"], c["nonempty_items"], 4), "",
                "the published operating point; benign {} and V3 {} are the "
                "two macros the manuscript prints".format(
                    macro_value(paths["macros"], "dgBenignCanonicalShare"),
                    macro_value(paths["macros"], "dgVThreeCanonicalShare"))])

        # -- the matched operating points -------------------------------- #
        for guard, setting in matched.items():
            kind, s = label(guard, setting)
            for cls in list(CLASSES) + ["violations_all", "all"]:
                c = matched_tally[guard][cls]
                w.writerow([
                    "matched", guard, kind, s, cls, c["items"],
                    c["nonempty_items"], c["reached_qual"],
                    c["pre_qual_refused"], c["qual_refused"], c["refused"],
                    pct(c["refused"], c["items"], 4),
                    pct(c["refused_nonempty"], c["nonempty_items"], 4), "",
                    "sensitivity, not a headline baseline"
                    if guard in SENSITIVITY_GUARDS else ""])

        # -- the same point chosen over every threshold ------------------ #
        for guard, setting in unrestricted.items():
            kind, _s = label(guard, setting)
            on_grid = "on the grid" if setting in GUARDS[guard][1] \
                else "off the grid"
            for cls in list(CLASSES) + ["violations_all", "all"]:
                c = unrestricted_tally[guard][cls]
                w.writerow([
                    "unrestricted", guard, kind, "{:.6g}".format(setting), cls,
                    c["items"], c["nonempty_items"], c["reached_qual"],
                    c["pre_qual_refused"], c["qual_refused"], c["refused"],
                    pct(c["refused"], c["items"], 4),
                    pct(c["refused_nonempty"], c["nonempty_items"], 4), "",
                    "diagnostic: the best threshold under the same benign "
                    "budget when the search is not restricted to the grid "
                    "({}); the grid point is {} = {:g}".format(
                        on_grid, kind, matched[guard])])

        # -- (a) the two focus instances --------------------------------- #
        for iid, entry in focus.items():
            wwt, lb, gap = entry["anchor"]
            for guard, setting in matched.items():
                kind, s = label(guard, setting)
                for cls in FOCUS_CLASSES:
                    g = entry["guards"][guard][cls]
                    w.writerow([
                        "focus_instance", guard, kind, s,
                        "{}@{}".format(cls, iid), g["items"], "", "", "",
                        g["refused"], g["refused"],
                        pct(g["refused"], g["items"], 4), "",
                        fnum(g["delta_max"], 4),
                        "stat = the largest value this rule thresholds on "
                        "these items; the instance's own no-op schedule "
                        "certifies at gap {:.4f}, above tau={:g}".format(
                            gap, TAU_PUBLISHED)])

        # -- what each guard accepts on those instances ------------------ #
        for guard, fa in focus_accepted.items():
            kind, s = label(guard, matched[guard])
            w.writerow([
                "focus_accepted", guard, kind, s, "accepted_above_tau",
                fa["pool"], "", fa["pool"], "", "", fa["accepted"], "", "",
                fa["accepted_above_tau"],
                "of the {} quality-reaching items on the two instances the "
                "guard accepts {}, and {} of those carry an executed schedule "
                "whose own certified gap exceeds tau={:g} (median {}, max {}, "
                "median absolute excess over the bound {} bh)".format(
                    fa["pool"], fa["accepted"], fa["accepted_above_tau"],
                    TAU_PUBLISHED, fnum(fa["gap_median"], 4),
                    fnum(fa["gap_max"], 4), fnum(fa["excess_bh_median"], 4))])

        # -- (b) the V3 and benign disagreements ------------------------- #
        for guard in GUARDS:
            kind, s = label(guard, matched[guard])
            d = disagreement[guard]
            for name, rows in (("cert_only", d["cert_only"]),
                               ("delta_only", d["delta_only"]),
                               ("both", d["both"]),
                               ("neither", d["neither"])):
                gaps = [r["gap"] for r in rows if r["gap"] is not None]
                dl = [delta_of(r, guard) for r in rows
                      if delta_of(r, guard) is not None]
                w.writerow([
                    "disagreement_V3", guard, kind, s, name, len(rows), "", "",
                    "", "", "", "", "",
                    fnum(sorted(gaps)[len(gaps) // 2], 4) if gaps else "",
                    "stat = median certified gap of these V3 items; median "
                    "rule quantity {}".format(
                        fnum(sorted(dl)[len(dl) // 2], 4) if dl else "n/a")])
            bd = benign_disagreement[guard]
            for name in ("cert_only", "delta_only", "both"):
                rows = bd[name]
                w.writerow([
                    "disagreement_benign", guard, kind, s, name, len(rows), "",
                    "", "", "", "", "", "", "",
                    "benign items refused by one side only"])

        # -- (c) the structural zeros ------------------------------------ #
        for cls in CLASSES:
            st = structure[cls]
            w.writerow([
                "structure", "", "", "", cls, st["items"], "",
                st["reached_qual"], st["pre_qual_refused"], "", "", "", "",
                st["identical_by_construction"],
                "stat = quality-reaching items whose counterfactual reference "
                "equals the objective by construction (a field-only proposal), "
                "so D-REL2 can never refuse them; {} have a strictly positive "
                "D-REL1 delta and {} a strictly positive D-REL2 delta".format(
                    st["delta1_positive"], st["delta2_positive"])])

        # -- the zero-reference instances -------------------------------- #
        w.writerow([
            "floor", "", "", "", "zero_reference_instances",
            len(zero_anchor_instances), "", "", "", "", "", "", "",
            len(zero_anchor_items),
            "instances whose no-op weighted tardiness is exactly zero, and the "
            "items sitting on them; the max(.,{:g}) floor is what makes a "
            "relative rule defined there: {}".format(
                FLOOR_BH, ", ".join(zero_anchor_instances))])

    # ------------------------------------------------------------------ #
    # Output: the report                                                  #
    # ------------------------------------------------------------------ #
    write_md(Path(args.out_md), csv_path, paths, digests, stamp, direct,
             anchor, structure, sweeps, matched, matched_tally, cert_tally,
             focus, disagreement, benign_disagreement, zero_anchor_instances,
             zero_anchor_items, v6_stored_disagree, focus_benign, focus_v3,
             wall, args, checks, stage, unrestricted, unrestricted_tally,
             focus_accepted)

    print("wrote {}".format(csv_path))
    print("wrote {}".format(args.out_md))
    print("{} assertions passed; {:.1f} s of dispatch on {} worker(s)".format(
        len(checks), wall, args.workers))
    for guard in GUARDS:
        t = matched_tally[guard]
        print("  {:<12s} matched at {:<6g}  benign {:>3d}/800  V3 {:>3d}/220  "
              "violations {:>4d}/1200".format(
                  guard, matched[guard], t[BENIGN]["refused"],
                  t["V3"]["refused"], t["violations_all"]["refused"]))
    t = cert_tally
    print("  {:<12s} at tau {:<6g}  benign {:>3d}/800  V3 {:>3d}/220  "
          "violations {:>4d}/1200".format(
              CERT, TAU_PUBLISHED, t[BENIGN]["refused"], t["V3"]["refused"],
              t["violations_all"]["refused"]))
    return 0


# --------------------------------------------------------------------------- #
# The report                                                                   #
# --------------------------------------------------------------------------- #
def write_md(path, csv_path, paths, digests, stamp, direct, anchor, structure,
             sweeps, matched, matched_tally, cert_tally, focus, disagreement,
             benign_disagreement, zero_anchor_instances, zero_anchor_items,
             v6_stored_disagree, focus_benign, focus_v3, wall, args, checks,
             stage, unrestricted, unrestricted_tally, focus_accepted):
    L = []
    A = L.append

    def row(cells):
        A("| " + " | ".join(str(c) for c in cells) + " |")

    def head(cells, align=None):
        row(cells)
        A("|" + "|".join(align or ["---"] * len(cells)) + "|")

    def share(t, cls):
        c = t[cls]
        return "{}/{} ({}%)".format(c["refused"], c["items"],
                                    pct(c["refused"], c["items"], 1))

    A("# DG14. Three deterministic delta baselines against the optimality "
      "certificate")
    A("")
    A("Generated {} by `code/scripts/delta_baselines.py` (`{}`). Companion "
      "table: `analysis/DG14_delta_baselines.csv`.".format(stamp, VERSION))
    A("")
    A("## The question")
    A("")
    A("A reviewer asked for the simplest quality check a scheduler would write "
      "by hand: run the proposal, run a reference schedule, and refuse the "
      "proposal when it makes the reference worse by more than a threshold. "
      "This note builds three such rules, sweeps each over its own grid, and "
      "reads each at the setting most favourable to it, on exactly the "
      "{} items of the direct benchmark with no model in the loop.".format(
          len(direct)))
    A("")
    A("## What is held fixed")
    A("")
    A("A delta rule replaces the **quality stage only**. The schema and "
      "feasibility stages are the guard's, and no delta rule can reproduce "
      "them: an operation list that does not parse, or that names an order the "
      "instance does not have, never produces a schedule to score. Every guard "
      "here therefore reuses the logged schema and feasibility verdicts "
      "unchanged. {} items are blocked before the quality stage ({} at schema, "
      "{} at feasibility) and stay blocked under every guard; the {} items that "
      "reach the quality stage are the ones re-adjudicated.".format(
          stage["schema"] + stage["feas"], stage["schema"], stage["feas"],
          stage["qual"]))
    A("")
    A("## The rules")
    A("")
    A("`WT_prop` is the weighted tardiness of the schedule the canonical "
      "proposal actually produced, scored on the fields the proposal installed. "
      "It is the logged `obj_bh`, recomputed here and asserted equal on all "
      "{} quality-reaching items.".format(stage["qual"]))
    A("")
    head(["rule", "reference", "refuses when", "grid"])
    row(["D-REL1", "`WT_ref1`, the no-op dispatch of the unadjusted instance",
         "`(WT_prop - WT_ref1) / max(WT_ref1, 1) > theta`",
         "{} tolerances, {:g} to {:g}".format(len(THETA_GRID), THETA_GRID[0],
                                              THETA_GRID[-1])])
    row(["D-REL2", "`WT_ref2`, the same adjusted fields with the proposal's "
         "added dispatch constraints removed",
         "`(WT_prop - WT_ref2) / max(WT_ref2, 1) > theta`",
         "the same {} tolerances".format(len(THETA_GRID))])
    row(["D-ABS", "`WT_ref1`", "`WT_prop - WT_ref1 > A`",
         "{} log-spaced values, {:g} to {:g} bh".format(
             len(A_GRID), A_GRID[0], A_GRID[-1])])
    row(["D-REL1-ORIG *(sensitivity)*",
         "`WT_ref1`, with the proposal scored on the original fields too",
         "`(WT_prop_orig - WT_ref1) / max(WT_ref1, 1) > theta`",
         "the same {} tolerances".format(len(THETA_GRID))])
    row(["G-CERT *(the deployed guard)*", "the Tier-2 lower bound",
         "`(WT_prop - LB) / max(LB, 1) > tau`",
         "published at tau = {:g}".format(TAU_PUBLISHED)])
    A("")
    A("Every weighted-tardiness difference is rounded to {} decimals in "
      "business hours before it is thresholded, which is what the suite "
      "already does to its stored `badness`. Without that rounding the "
      "difference between two schedules that are in fact the same schedule "
      "carries a residue near 1e-16 bh, and a threshold search allowed to run "
      "down to zero reads the residue as a refusal.".format(ROUND_BH))
    A("")
    A("The `max(., 1)` floor is the certificate's own convention "
      "(`LB_FLOOR_BH = {:g}`), and it is needed here for the same reason: {} "
      "instances have a no-op weighted tardiness of exactly zero, so a bare "
      "ratio is undefined on the {} items that sit on them ({}).".format(
          FLOOR_BH, len(zero_anchor_instances), len(zero_anchor_items),
          ", ".join(zero_anchor_instances)))
    A("")
    A("`D-REL1-ORIG` is reported as a sensitivity rather than as a fourth "
      "baseline. D-REL1 subtracts a reference scored on the instance's "
      "original deadlines from a proposal scored on the deadlines the proposal "
      "installed, which is what a practitioner comparing the schedule they "
      "have with the schedule the assistant proposes would in fact do, but it "
      "mixes two field sets on the items whose canonical proposal edits a "
      "priority, a due date or a release window. D-REL1-ORIG scores both sides "
      "on the original fields.")
    A("")
    A("## The grids")
    A("")
    A("Tolerance grid, {} values: {}.".format(
        len(THETA_GRID), ", ".join("{:g}".format(t) for t in THETA_GRID)))
    A("")
    A("The tolerance sweep the manuscript already publishes runs on a frozen "
      "grid of eight values ({}). This is a {}-value refinement of it: same "
      "range, every one of the eight frozen tolerances still in it, and the "
      "added resolution spent below 0.50, which is where every operating point "
      "in this note sits.".format(
          ", ".join("{:g}".format(t) for t in TAU_GRID_FROZEN),
          len(THETA_GRID)))
    A("")
    A("Absolute grid, {} values in weighted business hours: {}.".format(
        len(A_GRID), ", ".join("{:g}".format(a) for a in A_GRID)))
    A("")
    A("## The population")
    A("")
    head(["class", "items", "reach quality", "blocked before quality",
          "empty proposal at quality", "reference identical by construction"])
    for cls in CLASSES:
        st = structure[cls]
        row([cls, st["items"], st["reached_qual"], st["pre_qual_refused"],
             st["empty_qual"], st["identical_by_construction"]])
    A("")
    A("The last column is the structural limit of `WT_ref2`: a proposal that "
      "only edits fields imposes no dispatch constraint, so the counterfactual "
      "reference is the objective itself and the delta is exactly zero at every "
      "threshold. D-REL2 cannot refuse those items however the threshold is "
      "set.")
    A("")
    A("## The matched operating points")
    A("")
    A("Each rule is read at the setting most favourable to it: the setting "
      "whose benign false-block count does not exceed the certificate's "
      "({} of {}), maximising V3 refusals, breaking ties toward higher overall "
      "violation refusal, then toward fewer benign false blocks, then toward "
      "the widest tolerance.".format(cert_tally[BENIGN]["refused"],
                                     cert_tally[BENIGN]["items"]))
    A("")
    head(["guard", "setting", "benign false blocks", "V3 refused",
          "all violations refused"])
    for guard in list(GUARDS) + [CERT]:
        t = matched_tally[guard] if guard in matched_tally else cert_tally
        note = " *(sensitivity)*" if guard in SENSITIVITY_GUARDS else ""
        note = " *(the deployed guard)*" if guard == CERT else note
        kind = "tau" if guard == CERT else GUARDS[guard][0]
        row([guard + note, "{} = {:g}".format(kind, matched[guard]),
             share(t, BENIGN), share(t, "V3"), share(t, "violations_all")])
    A("")
    n_edge = sum(1 for g in GUARDS
                 if matched[g] in (GUARDS[g][1][0], GUARDS[g][1][-1]))
    A("{} of the {} rules take their grid operating point at an end of the "
      "grid, so the same choice was made again over every threshold the data "
      "realises, with negative thresholds excluded because a rule that refuses "
      "a proposal for improving the schedule is not one anybody would write. "
      "This is a diagnostic, not the deliverable: it exists so the reported "
      "operating point can be shown to be each rule's true best rather than an "
      "artifact of where the grid stops.".format(
          WORDS.get(n_edge, str(n_edge)).capitalize(),
          WORDS.get(len(GUARDS), str(len(GUARDS)))))
    A("")
    head(["guard", "grid setting", "unrestricted setting", "benign",
          "V3 refused", "all violations refused"])
    for guard in GUARDS:
        kind = GUARDS[guard][0]
        t = unrestricted_tally[guard]
        row([guard, "{} = {:g}".format(kind, matched[guard]),
             "{} = {:.6g}".format(kind, unrestricted[guard]),
             share(t, BENIGN), share(t, "V3"), share(t, "violations_all")])
    A("")
    A("## What the comparison shows")
    A("")
    best_v3 = max(matched_tally[g]["V3"]["refused"] for g in HEADLINE_GUARDS)
    best_viol = max(matched_tally[g]["violations_all"]["refused"]
                    for g in HEADLINE_GUARDS)
    A("**On this benchmark the delta rules are not weaker than the "
      "certificate on V3, and one of them is stronger.** At the certificate's "
      "own benign cost the three rules refuse {} to {} of the {} V3 items "
      "against the certificate's {}, and {} to {} of the {} violation items "
      "against its {}. Read over every threshold rather than over the grid, "
      "all three reach {} of {} V3 items. The comparison cannot be presented "
      "as the certificate detecting more damage than a hand-written "
      "rule.".format(
          min(matched_tally[g]["V3"]["refused"] for g in HEADLINE_GUARDS),
          best_v3, cert_tally["V3"]["items"], cert_tally["V3"]["refused"],
          min(matched_tally[g]["violations_all"]["refused"]
              for g in HEADLINE_GUARDS), best_viol,
          cert_tally["violations_all"]["items"],
          cert_tally["violations_all"]["refused"],
          max(unrestricted_tally[g]["V3"]["refused"] for g in HEADLINE_GUARDS),
          cert_tally["V3"]["items"]))
    A("")
    A("**Three things the delta rules do not do, and each is measured "
      "here.** They refuse none of the {} V5 items, where the instruction is "
      "ambiguous and the canonical proposal is empty, while the certificate "
      "refuses {}: an empty proposal cannot move a reference schedule, so no "
      "threshold on that movement can fire. They give a one-sided answer of a "
      "different kind: passing a delta rule means only that the proposal is no "
      "worse than a reference which may itself be far from what the instance "
      "admits, and on the two instances in section (a) that reference is "
      "measurably poor. And they need a reference schedule the site has to "
      "keep current, at one extra dispatch per proposal, which the certificate "
      "does not.".format(cert_tally["V5"]["items"],
                         cert_tally["V5"]["refused"]))
    A("")
    A("**The benign cost is the same number on different items.** The "
      "certificate's {} benign false blocks and the delta rules' {} to {} do "
      "not overlap at all, so a matched cost here means an equal count of "
      "interruptions, not the same day being queried twice.".format(
          cert_tally[BENIGN]["refused"],
          min(matched_tally[g][BENIGN]["refused"] for g in HEADLINE_GUARDS),
          max(matched_tally[g][BENIGN]["refused"] for g in HEADLINE_GUARDS)))
    A("")
    A("## Per-class refusal at the matched settings")
    A("")
    header = ["class"] + [g for g in GUARDS] + [CERT]
    head(header)
    for cls in list(CLASSES) + ["violations_all", "all"]:
        cells = [cls]
        for guard in list(GUARDS) + [CERT]:
            t = matched_tally[guard] if guard in matched_tally else cert_tally
            cells.append(share(t, cls))
        row(cells)
    A("")
    A("Denominators are all class items, the convention the published macros "
      "use. The certificate column reproduces the two numbers the manuscript "
      "prints, benign {} and V3 {}, and the script asserts that against "
      "`manuscript/macros.tex` rather than restating them.".format(
          pct(cert_tally[BENIGN]["refused"], cert_tally[BENIGN]["items"]) + "%",
          pct(cert_tally["V3"]["refused"], cert_tally["V3"]["items"]) + "%"))
    A("")
    A("## The sweeps at the frozen tolerances")
    A("")
    A("The full grids are in the CSV; this is the same sweep read at the eight "
      "frozen tau values, so the certificate column is the published tau "
      "sweep.")
    A("")
    for cls in (BENIGN, "V3"):
        A("**{}, refused of {}**".format(cls, structure[cls]["items"]))
        A("")
        head(["tolerance"] + [g for g in GUARDS if GUARDS[g][0] == "theta"]
             + [CERT])
        for t in TAU_GRID_FROZEN:
            cells = ["{:g}".format(t)]
            for guard in GUARDS:
                if GUARDS[guard][0] != "theta":
                    continue
                cells.append(sweeps[guard][t][cls]["refused"])
            cells.append(sweeps[CERT][t][cls]["refused"])
            row(cells)
        A("")
    A("**D-ABS, over its own grid**")
    A("")
    head(["A (bh)", "benign refused", "V3 refused", "V4 refused",
          "V6 refused", "all violations refused"])
    for a in A_GRID:
        t = sweeps["D-ABS"][a]
        row(["{:g}".format(a), t[BENIGN]["refused"], t["V3"]["refused"],
             t["V4"]["refused"], t["V6"]["refused"],
             t["violations_all"]["refused"]])
    A("")
    A("## (a) The two instances whose own no-op schedule fails the tolerance")
    A("")
    A("Every one of the certificate's {} benign false blocks sits on one of two "
      "instances, and the script asserts that rather than assuming it. On both, "
      "doing nothing is already uncertifiable: the no-op schedule certifies at "
      "a gap above tau = {:g}.".format(cert_tally[BENIGN]["refused"],
                                       TAU_PUBLISHED))
    A("")
    head(["instance", "no-op WT (bh)", "Tier-2 bound (bh)", "no-op gap",
          "benign items", "V3 items"])
    for iid, entry in focus.items():
        wwt, lb, gap = entry["anchor"]
        row([iid, "{:.4f}".format(wwt), "{:.4f}".format(lb),
             "{:.4f}".format(gap), entry["class_items"][BENIGN],
             entry["class_items"]["V3"]])
    A("")
    A("What each rule does with those items, at its matched setting:")
    A("")
    focus_n = {cls: sum(focus[i]["class_items"][cls] for i in focus)
               for cls in FOCUS_CLASSES}
    head(["guard"] + ["{} refused (of {})".format(c, focus_n[c])
                      for c in FOCUS_CLASSES]
         + ["largest benign quantity thresholded",
            "largest V5 quantity thresholded"])
    focus_counts = {}
    for guard in list(GUARDS) + [CERT]:
        counts = [sum(focus[i]["guards"][guard][c]["refused"] for i in focus)
                  for c in FOCUS_CLASSES]
        focus_counts[guard] = dict(zip(FOCUS_CLASSES, counts))
        mb = max((focus[i]["guards"][guard][BENIGN]["delta_max"]
                  for i in focus), default=None)
        m5 = max((focus[i]["guards"][guard]["V5"]["delta_max"]
                  for i in focus), default=None)
        row([guard] + counts + [fnum(mb, 4), fnum(m5, 4)])
    A("")
    A("Three things follow, and they are the substance of the comparison.")
    A("")
    A("First, the certificate's whole benign cost is here: it refuses {} of "
      "the {} benign items on these two instances and {} of the {} benign "
      "items everywhere else. Every delta rule refuses at most {} of the same "
      "{}, and the ones it refuses are items the certificate passes, so the "
      "two false-block sets are disjoint (the benign disagreement table below "
      "records {} benign item refused by both sides at any matched "
      "setting). The delta rules' own benign false blocks sit elsewhere: of "
      "D-REL1's {}, {} are on these two instances and {} are spread over the "
      "rest of the suite.".format(
          focus_counts[CERT][BENIGN], focus_n[BENIGN],
          cert_tally[BENIGN]["refused"] - focus_counts[CERT][BENIGN],
          cert_tally[BENIGN]["items"] - focus_n[BENIGN],
          max(focus_counts[g][BENIGN] for g in GUARDS), focus_n[BENIGN],
          WORDS[max(len(benign_disagreement[g]["both"]) for g in GUARDS)],
          matched_tally["D-REL1"][BENIGN]["refused"],
          focus_counts["D-REL1"][BENIGN],
          matched_tally["D-REL1"][BENIGN]["refused"]
          - focus_counts["D-REL1"][BENIGN]))
    A("")
    A("Second, this is where a delta rule is structurally blind, and V5 is the "
      "class that shows it. A V5 item has no representable proposal, so doing "
      "nothing leaves the reference schedule exactly where it was and every "
      "delta is zero: no delta rule refuses any of the {} V5 items on these "
      "instances at any threshold at or above zero, while the certificate "
      "refuses all {}. The delta rules ask whether the proposal made a "
      "schedule worse; the certificate asks whether the schedule that results "
      "is any good. On an instance whose own no-op schedule is already far "
      "from what the instance admits, only the second question has an "
      "answer.".format(focus_n["V5"], focus_counts[CERT]["V5"]))
    A("")
    A("The size of that blind spot is measurable. Of the {} quality-reaching "
      "items on these two instances, each rule accepts a schedule whose own "
      "certified gap exceeds tau:".format(
          focus_accepted[CERT]["pool"]))
    A("")
    head(["guard", "items accepted", "of those, certifying above tau",
          "median gap of those", "largest gap of those",
          "median excess over the bound (bh)"])
    for guard in list(GUARDS) + [CERT]:
        fa = focus_accepted[guard]
        row([guard, fa["accepted"], fa["accepted_above_tau"],
             fnum(fa["gap_median"], 4), fnum(fa["gap_max"], 4),
             fnum(fa["excess_bh_median"], 4)])
    A("")
    A("A delta rule accepting {} such items is the concrete form of \"the "
      "proposal did not make the day worse, so it passes\": the day was "
      "already bad, and the rule has no way to say so. The certificate accepts "
      "{}, because refusing them is what it is for, and its benign false "
      "blocks are the price of that.".format(
          max(focus_accepted[g]["accepted_above_tau"] for g in HEADLINE_GUARDS),
          focus_accepted[CERT]["accepted_above_tau"]))
    A("")
    A("Third, the V3 items on these instances are caught by both sides: the "
      "certificate refuses {} of {} and the delta rules {} to {}. The "
      "disagreement is not about the damaging proposals here; it is about "
      "what happens when nothing damaging was proposed.".format(
          focus_counts[CERT]["V3"], focus_n["V3"],
          min(focus_counts[g]["V3"] for g in GUARDS),
          max(focus_counts[g]["V3"] for g in GUARDS)))
    A("")
    A("## (b) Where the certificate and each matched rule disagree on V3")
    A("")
    head(["guard", "certificate only", "delta rule only", "both", "neither"])
    for guard in GUARDS:
        d = disagreement[guard]
        row([guard, len(d["cert_only"]), len(d["delta_only"]), len(d["both"]),
             len(d["neither"])])
    A("")
    for guard in GUARDS:
        d = disagreement[guard]
        co, do = d["cert_only"], d["delta_only"]

        def med(rows, key):
            vals = sorted(v for v in (key(r) for r in rows) if v is not None)
            return None if not vals else vals[len(vals) // 2]

        A("**{}.** ".format(guard) + _characterise(guard, co, do, med, matched))
        A("")
    A("The benign side of the same comparison:")
    A("")
    head(["guard", "certificate only", "delta rule only", "both"])
    for guard in GUARDS:
        bd = benign_disagreement[guard]
        row([guard, len(bd["cert_only"]), len(bd["delta_only"]),
             len(bd["both"])])
    A("")
    A("## (c) V4, V5 and V6, including the structural zeros")
    A("")
    head(["class", "guard", "refused at the matched setting", "why"])
    for cls in ("V4", "V5", "V6"):
        for guard in list(GUARDS) + [CERT]:
            t = matched_tally[guard] if guard in matched_tally else cert_tally
            row([cls, guard, share(t, cls), _why(cls, guard, structure)])
    A("")
    A("## Caveats")
    A("")
    A("1. **Field-set mixing.** `WT_prop` is scored on the fields the proposal "
      "installed and `WT_ref1` on the instance's original fields. On the items "
      "whose canonical proposal edits a priority, a due date or a release "
      "window the two sides of the D-REL1 and D-ABS subtraction use different "
      "deadlines. That is what a practitioner comparing the current schedule "
      "with the proposed one would do, and the D-REL1-ORIG sensitivity shows "
      "what changes when both sides are scored on the original fields.")
    A("2. **The suite's stored V6 references are not reusable.** The suite "
      "measured V6 on `gold_ops`, the legitimate carrier order, not on the "
      "`forbidden_ops` that is the canonical proposal for that class. {} of the "
      "stored V6 references disagree with the counterfactual of the proposal "
      "actually scored here, so every V6 reference in this note is recomputed "
      "and the stored ones are not asserted against.".format(
          len(v6_stored_disagree)))
    A("3. **A matched false-block cost compares different items, not a "
      "subset.** The certificate's benign false blocks and the delta rules' "
      "are disjoint sets, so equal cost here means equal count, not the same "
      "supervisor being interrupted about the same day.")
    A("4. **The delta rules need a reference schedule the certificate does "
      "not.** Each proposal costs one extra dispatch of a reference the site "
      "has to keep current; the certificate needs only the bound it already "
      "computes.")
    A("")
    A("## Provenance and reproduction")
    A("")
    head(["input", "sha256"])
    for name in ("direct", "summary", "anchor", "suite", "tau_sweep"):
        row(["`{}`".format(paths[name].relative_to(ROOT)), digests[name]])
    A("")
    A("`manuscript/macros.tex` is read for the two published shares the "
      "certificate row is asserted against, and is not written to.")
    A("")
    A("Nothing here samples. The dispatcher is deterministic at "
      "(rule = {}, seed = {}); the grids are literals; the matched-point "
      "tie-break is a total order. {} counterfactual references were "
      "recomputed in {:.1f} s on {} worker(s) pinned to cores {}, with the "
      "thread pools forced to one per worker. {} assertions passed.".format(
          EPISODE_RULE, EPISODE_SEED, stage["qual"], wall, args.workers,
          args.cores, len(checks)))
    A("")
    A("```")
    A("conda run -n fjsp python code/scripts/delta_baselines.py")
    A("```")
    A("")

    path.write_text("\n".join(L), encoding="utf-8")


def _characterise(guard, cert_only, delta_only, med, matched):
    """One sentence for each direction of the V3 disagreement."""
    parts = []
    if cert_only:
        g = med(cert_only, lambda r: r["gap"])
        d = med(cert_only, lambda r: delta_of(r, guard))
        one = len(cert_only) == 1
        parts.append(
            "The certificate refuses {} V3 item{} the rule passes; {} a median "
            "certified gap of {:.3f}, above tau, while the median quantity the "
            "rule thresholds is only {:.4f}, so the proposal leaves the "
            "reference schedule close to where it was but the schedule it "
            "leaves is still far from what the instance admits.".format(
                len(cert_only), "" if one else "s",
                "it carries" if one else "they carry", g, d))
    else:
        parts.append("The certificate refuses no V3 item the rule passes.")
    if delta_only:
        g = med(delta_only, lambda r: r["gap"])
        d = med(delta_only, lambda r: delta_of(r, guard))
        one = len(delta_only) == 1
        parts.append(
            "The rule refuses {} V3 item{} the certificate passes; {} median "
            "certified gap is {:.3f}, inside tau, and the median quantity the "
            "rule thresholds is {:.4f}, so the proposal degrades the reference "
            "measurably yet still lands within the tolerance of an admissible "
            "bound.".format(len(delta_only), "" if one else "s",
                            "its" if one else "their", g, d))
    else:
        parts.append("The rule refuses no V3 item the certificate passes.")
    return " ".join(parts)


def _why(cls, guard, structure):
    st = structure[cls]
    if cls == "V5":
        return ("all {} canonical proposals are empty, so every delta is "
                "exactly zero and no delta rule can fire at any threshold at "
                "or above zero".format(st["items"])) if guard != CERT else \
            ("the certificate refuses on the resulting schedule's own "
             "distance from the bound, which an empty proposal does not "
             "change but does not hide either")
    if cls == "V6":
        base = ("{} of the {} items are blocked at the schema stage and stay "
                "blocked under every guard; {} more carry an empty canonical "
                "proposal and are delta zero".format(
                    st["pre_qual_refused"], st["items"], st["empty_qual"]))
        return base if guard != CERT else base + \
            "; the certificate adds refusals on the quality stage"
    if cls == "V4":
        if guard == "D-REL2":
            return ("{} of the {} quality-reaching items carry a field-only "
                    "proposal whose counterfactual reference is the objective "
                    "itself, so D-REL2 is structurally blind to them".format(
                        st["identical_by_construction"], st["reached_qual"]))
        return ("all {} items reach the quality stage and carry a non-empty "
                "proposal".format(st["reached_qual"]))
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
