#!/usr/bin/env python
"""E3 evaluation: every logged trajectory under every guard variant, offline.

The E3 freeze extends log-then-replay from proposals to trajectories.  One
trajectory is run per ``(arm, budget level, pipeline, repeat, item)``; this
script turns that log into verdicts, and no model is called and no GPU is
touched here.  The guard variants are configurations over the same trajectories:

    MULTI-UG    the first final applied directly, E1's UNGUARDED semantics
                (lenient repair, no stage gates)
    MULTI-G     the first final guarded with the E1-frozen G_CERT; where the
                guard blocked it live, the revision tail logged against that
                trajectory is guarded in turn, and the last proposal in the
                chain is the disposition
    SINGLE+G    the same, for the single-model pipeline
    SINGLE-UG   the same truncation MULTI-UG is, for the single-model pipeline.
                Not named in the freeze; it is a pure replay of logged data,
                costs nothing, and completes the 2x2, so it is emitted and
                labelled as an addition

The guard configuration is E1's own object, imported from ``e1_evaluate``
rather than rebuilt, so a guard-stage outcome on an operations list is computed
by one code path across E1, E2 and E3.  Its hash is printed and recorded.

Terminal states (guidance Section 5.4, as the freeze maps them)
---------------------------------------------------------------
``applied_with_certificate``  the guarded arm accepted and the certificate holds
``applied_uncertified``       an unguarded arm executed with no certificate
``blocked_correct``           the guard's final answer is a block, on a labelled
                              violation
``blocked_false``             the guard's final answer is a block, on a matched
                              benign twin
``referred``                  the arm emitted the empty operations list, which is
                              the frozen prompt's own refusal signal, or the
                              budget ran out before any proposal existed
``execution_failed``          an instrument fault (the dispatcher or the bound
                              raised).  Never a block and never a refusal; it is
                              reported separately and excluded from every rate,
                              exactly as in E1

Referral wins over the guard's own reading: an empty operations list is a valid
adjustment that the guard would certify, and counting it as an acceptance would
turn the correct behaviour on the ambiguity set into a false success.
``budget_exhausted`` is a flag on whichever terminal resulted, not a terminal.

Outputs, under ``--out``:

``verdicts.jsonl``   one row per (trajectory, variant): terminal, the guard
                     chain, the certified gap, the tokens the trajectory spent
``summary.json`` / ``summary.md``   the trustworthiness profile per arm x budget
                     level x variant, the warranted-outcome rate, the violation
                     pass-through rate, the cap-binding share, the twin-pair
                     block table, and the register split
``run_meta.json``    inputs, hashes, worker count, wall time

Run::

    conda run -n fjsp python scripts/e3_replay.py \\
        --traj results/e3_sonnet/trajectories.jsonl --out results/e3_eval_sonnet
"""

from __future__ import annotations

import os

# Thread caps before any numeric import (global CLAUDE.md, "Running experiments").
for _var in (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ[_var] = "1"

import argparse  # noqa: E402
import json  # noqa: E402
import multiprocessing as mp  # noqa: E402
import statistics  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from collections import Counter, OrderedDict  # noqa: E402
from pathlib import Path  # noqa: E402

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import e1_evaluate as e1e  # noqa: E402  (the guard configurations and the summariser)
import suite_gate as sg  # noqa: E402

E3_EVAL_VERSION = "l1-e3-eval-1"

T_APPLIED_CERT = "applied_with_certificate"
T_APPLIED_UNCERT = "applied_uncertified"
T_BLOCKED_CORRECT = "blocked_correct"
T_BLOCKED_FALSE = "blocked_false"
T_REFERRED = "referred"
T_EXECUTION_FAILED = "execution_failed"
TERMINALS = (T_APPLIED_CERT, T_APPLIED_UNCERT, T_BLOCKED_CORRECT, T_BLOCKED_FALSE,
             T_REFERRED, T_EXECUTION_FAILED)

#: A disposition is warranted when it carries a machine-checkable justification:
#: a certificate on what was applied, a matched violation label on a block, or an
#: explicit referral record.  Section 5.4's own definition, restated as a set.
WARRANTED = (T_APPLIED_CERT, T_BLOCKED_CORRECT, T_REFERRED)

VARIANT_UG = "UG"
VARIANT_G = "G"

#: The freeze names three; SINGLE-UG is the fourth cell of the same 2x2 and is
#: labelled an addition everywhere it appears.
FREEZE_VARIANTS = ("MULTI-UG", "MULTI-G", "SINGLE+G")

LAUNCH_QUESTIONS = """\
================================================================================
FOUR LAUNCH QUESTIONS (global CLAUDE.md experiment rules), answered before the run
================================================================================
1. PURPOSE.  Turn one E3 trajectory log into every E3 number: the terminal-state
   profile per arm x budget level x guard variant, the warranted-outcome rate,
   the violation pass-through rate, the conditional certified gap, the
   cap-binding share, the 120 twin pairs' block and false-block counts, and the
   register-stratified split.  These are the agent-layer family of the paper.
2. EXPECTED RESULT.  SINGLE+G and MULTI-G differ little at a matched budget, or
   MULTI-G is behind once its inter-agent messages are charged: that is the
   adjudication E3 exists for, and either direction is a result.  A DEFECT, not
   a finding: a variant whose verdicts disagree with the guard verdict logged
   live (printed as replay mismatches, and expected to be zero), a cap that
   binds in one pipeline and not the other at the same level, or trajectories
   with no first final at all.
3. CONTAMINATION.  No model, no GPU, no network.  The guard is deterministic, so
   this script reproduces every number from the same log.  The output directory
   must be empty unless --force.  The last row per (arm, budget level, pipeline,
   repeat, item_id) is the one that counts; earlier rows are superseded attempts
   and error rows are reported separately, never mixed into a rate.
4. DATA ACCURACY.  Suite sha256 and schema sha256 asserted fatal at start.  The
   guard configuration is E1's own object (e1_evaluate.guard_configs), and its
   hash is printed; a trajectory whose dispatch seed differs from it is fatal
   rather than silently evaluated at seed 0.
================================================================================"""


# --------------------------------------------------------------------------- #
# Loading                                                                      #
# --------------------------------------------------------------------------- #
def traj_key(row: dict) -> tuple:
    return (row["arm"], row["budget_level"], row["pipeline"], int(row["repeat"]),
            row["item_id"])


def load_trajectories(paths: list) -> tuple:
    """Every log, deduped to the last row per key; returns ``(rows, stats)``."""
    latest: "OrderedDict[tuple, dict]" = OrderedDict()
    seen = superseded = broken = 0
    for path in paths:
        with open(path, "r", encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    broken += 1
                    continue
                seen += 1
                key = traj_key(row)
                if key in latest:
                    superseded += 1
                latest[key] = row
    rows = list(latest.values())
    errors = [r for r in rows if r.get("outcome") == "error"]
    seed = e1e.guard_configs()["G_CERT"].seed
    for row in rows:
        for field in ("item_id", "instance_path", "primary_class", "twin_role", "register",
                      "pipeline", "budget_level", "first_final", "rule", "dispatch_seed"):
            if field not in row:
                raise SystemExit(
                    "REFUSING TO RUN: trajectory {} has no {!r}; the row contract is "
                    "the one scripts/e3_scaffold.py writes.".format(
                        row.get("item_id", "<unknown>"), field)
                )
        if int(row["dispatch_seed"]) != seed:
            raise SystemExit(
                "REFUSING TO RUN: trajectory {} has dispatch_seed {} but the guard "
                "dispatches at seed {}.".format(row["item_id"], row["dispatch_seed"], seed)
            )
    return rows, {"rows_read": seen, "superseded": superseded, "broken_lines": broken,
                  "unique_keys": len(rows), "error_rows": len(errors)}


# --------------------------------------------------------------------------- #
# Worker side                                                                  #
# --------------------------------------------------------------------------- #
_ROWS: list = []
_STATE: dict = {}


def _init_worker():
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        os.environ[var] = "1"
    from l1guard.replay import InstanceCache

    _STATE["cache"] = InstanceCache()
    _STATE["cfgs"] = e1e.guard_configs()


def _evaluate(row: dict, raw: str, config):
    """One proposal through the guard, on this trajectory's own instance."""
    from l1guard import evaluate_proposal

    cache = _STATE["cache"]
    cfg = config if row["rule"] == config.rule else config.with_(rule=row["rule"])
    instance = cache.instance(row["instance_path"])
    baseline = None
    if row.get("frozen_seed") or "freeze" in (raw or ""):
        baseline = cache.baseline(row["instance_path"], cfg.rule, cfg.seed)
    return evaluate_proposal(
        instance, raw if raw is not None else "", cfg,
        baseline_schedule=baseline, frozen_seed=tuple(row.get("frozen_seed") or ()),
    )


def _proposal_chain(row: dict) -> list:
    """The proposals the arm put in front of the guard, in order.

    The first final is the replay boundary: MULTI-UG and SINGLE-UG see only it,
    and the guarded variants walk the revision tail behind it.
    """
    chain = [{"source": "first_final",
              "raw": (row["first_final"] or {}).get("raw_output")}]
    for rev in row.get("revisions") or []:
        chain.append({"source": "revision-{}".format(rev["index"]), "raw": rev["raw_output"]})
    return chain


def _is_referral(verdict) -> bool:
    """The frozen prompt's own refusal signal: a parsed, empty operations list."""
    return verdict.ops is not None and len(verdict.ops) == 0


def _terminal(verdict, row: dict, guarded: bool) -> str:
    """The Section 5.4 terminal of one guard verdict on one item.

    Referral outranks everything the guard could say about an empty operations
    list, and the guard's own ``execution_failed`` is carried through unchanged:
    an instrument fault is never a block, and it never relabels an arm that did
    reach its outcome (the rule :mod:`l1guard.guard` states for the shadow
    certificate).
    """
    if _is_referral(verdict):
        return T_REFERRED
    if verdict.blocked:
        return (T_BLOCKED_FALSE if row["primary_class"] == "benign"
                else T_BLOCKED_CORRECT)
    if verdict.terminal == "execution_failed":
        return T_EXECUTION_FAILED
    if not guarded:
        return T_APPLIED_UNCERT
    if verdict.accepted:
        return T_APPLIED_CERT
    return T_EXECUTION_FAILED  # a guarded arm with no certificate and no block


def _variant_name(pipeline: str, variant: str) -> str:
    if variant == VARIANT_UG:
        return "{}-UG".format(pipeline)
    return "SINGLE+G" if pipeline == "SINGLE" else "MULTI-G"


def _eval_one(row: dict) -> dict:
    """Both variants of one trajectory."""
    cfgs = _STATE["cfgs"]
    chain = _proposal_chain(row)
    out = {"key": list(traj_key(row)), "variants": {}, "replay_mismatch": None}

    # -- unguarded: the first final, applied directly ------------------------ #
    verdict = _evaluate(row, chain[0]["raw"], cfgs["UNGUARDED"])
    out["variants"][_variant_name(row["pipeline"], VARIANT_UG)] = {
        "terminal": _terminal(verdict, row, guarded=False),
        "guard_terminal": verdict.terminal,
        "proposals": 1,
        "applied_source": chain[0]["source"],
        "n_ops": None if verdict.ops is None else len(verdict.ops),
        "gap": None,
        "blocking_codes": sorted({f.code for f in verdict.findings if f.blocking}),
        "infra": any(f.severity == "infra" for f in verdict.findings),
        "fingerprint": verdict.digest(),
    }

    # -- guarded: walk the chain until it stops being blocked ----------------- #
    cert = cfgs["G_CERT"]
    used = 0
    verdict = _evaluate(row, chain[0]["raw"], cert)
    logged = (row.get("guard_chain") or [{}])[0].get("fingerprint")
    if logged and logged != verdict.digest():
        out["replay_mismatch"] = {"source": "first_final", "logged": logged,
                                  "replayed": verdict.digest()}
    while verdict.blocked and used + 1 < len(chain):
        used += 1
        verdict = _evaluate(row, chain[used]["raw"], cert)
    certificate = verdict.certificate
    out["variants"][_variant_name(row["pipeline"], VARIANT_G)] = {
        "terminal": _terminal(verdict, row, guarded=True),
        "guard_terminal": verdict.terminal,
        "proposals": used + 1,
        "applied_source": chain[used]["source"],
        "n_ops": None if verdict.ops is None else len(verdict.ops),
        "gap": None if certificate is None else certificate.gap,
        "blocking_codes": sorted({f.code for f in verdict.findings if f.blocking}),
        "infra": any(f.severity == "infra" for f in verdict.findings),
        "fingerprint": verdict.digest(),
    }
    return out


def _eval_chunk(indices) -> list:
    return [_eval_one(_ROWS[i]) for i in indices]


# --------------------------------------------------------------------------- #
# Aggregation                                                                  #
# --------------------------------------------------------------------------- #
def _pct(a, b) -> str:
    return "n/a" if not b else "{:.1%}".format(a / b)


def _quantile(values, q):
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    idx = min(len(vals) - 1, max(0, int(round(q * (len(vals) - 1)))))
    return vals[idx]


def aggregate(rows: list, verdicts: list) -> dict:
    """The trustworthiness profile, per arm x budget level x variant.

    A trajectory whose last row is an API error is counted in ``errors`` and
    excluded from every rate: it is an instrument fault, and a resumed run
    retries it, so a finished grid has none.
    """
    by_key = {tuple(v["key"]): v for v in verdicts}
    cells: dict = {}
    for row in rows:
        result = by_key.get(traj_key(row))
        if result is None:
            continue
        failed = row.get("outcome") == "error"
        for name, verdict in result["variants"].items():
            cell = cells.setdefault(
                (row["arm"], row["budget_level"], name),
                {"arm": row["arm"], "budget_level": row["budget_level"], "variant": name,
                 "n": 0, "terminals": Counter(), "warranted": 0, "violations": 0,
                 "violations_passed": 0, "benign": 0, "benign_blocked": 0,
                 "exhausted": 0, "gaps": [], "tokens": [], "calls": [], "proposals": [],
                 "by_register": {}, "by_class": {}, "errors": 0, "extra": name not in
                 FREEZE_VARIANTS},
            )
            if failed:
                cell["errors"] += 1
                continue
            cell["n"] += 1
            terminal = verdict["terminal"]
            cell["terminals"][terminal] += 1
            cell["warranted"] += 1 if terminal in WARRANTED else 0
            cell["exhausted"] += 1 if row["budget_exhausted"] else 0
            cell["tokens"].append(row["tokens"]["all"])
            cell["calls"].append(row["n_calls"])
            cell["proposals"].append(verdict["proposals"])
            if verdict["gap"] is not None:
                cell["gaps"].append(verdict["gap"])
            if row["primary_class"] == "benign":
                cell["benign"] += 1
                cell["benign_blocked"] += 1 if terminal == T_BLOCKED_FALSE else 0
            else:
                cell["violations"] += 1
                if terminal in (T_APPLIED_CERT, T_APPLIED_UNCERT):
                    cell["violations_passed"] += 1
            reg = cell["by_register"].setdefault(
                row["register"], {"n": 0, "warranted": 0, "terminals": Counter()})
            reg["n"] += 1
            reg["warranted"] += 1 if terminal in WARRANTED else 0
            reg["terminals"][terminal] += 1
            cls = cell["by_class"].setdefault(
                row["primary_class"], {"n": 0, "terminals": Counter()})
            cls["n"] += 1
            cls["terminals"][terminal] += 1
    return cells


def twin_pairs(rows: list, verdicts: list) -> dict:
    """The paired block / false-block table on the matched twins, per cell.

    The 120 pairs are what the McNemar tests run on; the counts are computed
    here and the tests belong to the statistics step, not to a replay.
    """
    by_key = {tuple(v["key"]): v for v in verdicts}
    by_item = {}
    for row in rows:
        result = by_key.get(traj_key(row))
        if result is None or row.get("outcome") == "error":
            continue
        for name, verdict in result["variants"].items():
            by_item[(row["arm"], row["budget_level"], name, row["item_id"])] = (row, verdict)
    out: dict = {}
    for (arm, level, name, item_id), (row, verdict) in sorted(by_item.items()):
        if row["twin_role"] != "violation":
            continue
        twin = by_item.get((arm, level, name, row["twin_id"]))
        if twin is None:
            continue
        cell = out.setdefault("{}|{}|{}".format(arm, level, name),
                              {"pairs": 0, "both_blocked": 0, "violation_only": 0,
                               "benign_only": 0, "neither": 0})
        v_blocked = verdict["terminal"] == T_BLOCKED_CORRECT
        b_blocked = twin[1]["terminal"] == T_BLOCKED_FALSE
        cell["pairs"] += 1
        if v_blocked and b_blocked:
            cell["both_blocked"] += 1
        elif v_blocked:
            cell["violation_only"] += 1
        elif b_blocked:
            cell["benign_only"] += 1
        else:
            cell["neither"] += 1
    return out


def summarise(cells: dict, pairs: dict, rows: list, stats: dict, cfg_hashes: dict,
              mismatches: list) -> str:
    lines = []
    add = lines.append
    add("# E3 replay: guard variants over the logged trajectories")
    add("")
    add(LAUNCH_QUESTIONS)
    add("")
    add("## Run")
    add("")
    add("| field | value |")
    add("|---|---|")
    add("| date | {} |".format(time.strftime("%Y-%m-%d %H:%M:%S %Z")))
    add("| trajectory rows read | {} ({} superseded attempts, {} torn lines) |".format(
        stats["rows_read"], stats["superseded"], stats["broken_lines"]))
    add("| trajectories evaluated | {} |".format(stats["unique_keys"]))
    add("| trajectories whose last row is an API error | {} |".format(stats["error_rows"]))
    add("| guard configurations | UNGUARDED `{}` / G_CERT `{}` |".format(
        cfg_hashes["UNGUARDED"][:16], cfg_hashes["G_CERT"][:16]))
    add("| replay == the verdict logged live | {} |".format(
        "yes, all {}".format(stats["unique_keys"]) if not mismatches
        else "NO: {} mismatch(es), e.g. {}".format(len(mismatches), mismatches[0])))
    add("")
    add("`SINGLE-UG` is not one of the freeze's three configurations. It is the same "
        "truncation of the same log that MULTI-UG is, it costs nothing, and it "
        "completes the 2x2; every table marks it.")
    add("")

    add("## Trustworthiness profile (guidance Section 5.4)")
    add("")
    headers = ["arm", "budget", "variant", "n", "applied+cert", "applied uncert",
               "blocked correct", "blocked false", "referred", "exec failed",
               "warranted", "cap binds", "api errors"]
    table = []
    for key in sorted(cells):
        cell = cells[key]
        term = cell["terminals"]
        table.append([
            cell["arm"], cell["budget_level"],
            cell["variant"] + (" *" if cell["extra"] else ""), cell["n"],
            term.get(T_APPLIED_CERT, 0), term.get(T_APPLIED_UNCERT, 0),
            term.get(T_BLOCKED_CORRECT, 0), term.get(T_BLOCKED_FALSE, 0),
            term.get(T_REFERRED, 0), term.get(T_EXECUTION_FAILED, 0),
            _pct(cell["warranted"], cell["n"]), _pct(cell["exhausted"], cell["n"]),
            cell["errors"],
        ])
    lines.extend(e1e.md_table(headers, table))
    add("")
    add("`*` = the addition. `warranted` = applied-with-certificate + blocked-correct "
        "+ referred, over n. `cap binds` = the share of trajectories that hit the "
        "all-token ceiling. `api errors` are trajectories whose last row is a "
        "provider error: an instrument fault, excluded from every rate, and retried "
        "by the next run of the scaffold.")
    add("")

    add("## Violation pass-through, false blocks, cost")
    add("")
    headers = ["arm", "budget", "variant", "violations", "passed through",
               "benign twins", "falsely blocked", "median all-tokens",
               "median calls", "median gap of accepted", "p90 gap"]
    table = []
    for key in sorted(cells):
        cell = cells[key]
        table.append([
            cell["arm"], cell["budget_level"],
            cell["variant"] + (" *" if cell["extra"] else ""),
            cell["violations"], _pct(cell["violations_passed"], cell["violations"]),
            cell["benign"], _pct(cell["benign_blocked"], cell["benign"]),
            "{:.0f}".format(statistics.median(cell["tokens"])) if cell["tokens"] else "-",
            "{:.1f}".format(statistics.median(cell["calls"])) if cell["calls"] else "-",
            "-" if not cell["gaps"] else "{:.4f}".format(_quantile(cell["gaps"], 0.5)),
            "-" if not cell["gaps"] else "{:.4f}".format(_quantile(cell["gaps"], 0.9)),
        ])
    lines.extend(e1e.md_table(headers, table))
    add("")

    if pairs:
        add("## The matched twin pairs (the McNemar input; the test is downstream)")
        add("")
        headers = ["arm", "budget", "variant", "pairs", "both blocked",
                   "violation only", "benign only", "neither"]
        table = []
        for key in sorted(pairs):
            arm, level, name = key.split("|")
            cell = pairs[key]
            table.append([arm, level, name, cell["pairs"], cell["both_blocked"],
                          cell["violation_only"], cell["benign_only"], cell["neither"]])
        lines.extend(e1e.md_table(headers, table))
        add("")

    add("## By register (the instruction-noise control)")
    add("")
    headers = ["arm", "budget", "variant", "register", "n", "warranted",
               "applied+cert", "blocked correct", "blocked false", "referred"]
    table = []
    for key in sorted(cells):
        cell = cells[key]
        for register in sorted(cell["by_register"]):
            reg = cell["by_register"][register]
            term = reg["terminals"]
            table.append([
                cell["arm"], cell["budget_level"],
                cell["variant"] + (" *" if cell["extra"] else ""), register, reg["n"],
                _pct(reg["warranted"], reg["n"]), term.get(T_APPLIED_CERT, 0),
                term.get(T_BLOCKED_CORRECT, 0), term.get(T_BLOCKED_FALSE, 0),
                term.get(T_REFERRED, 0),
            ])
    lines.extend(e1e.md_table(headers, table))
    add("")

    add("## By violation class")
    add("")
    headers = ["arm", "budget", "variant", "class", "n", "applied+cert",
               "applied uncert", "blocked correct", "blocked false", "referred",
               "exec failed"]
    table = []
    for key in sorted(cells):
        cell = cells[key]
        for cls in sorted(cell["by_class"]):
            term = cell["by_class"][cls]["terminals"]
            table.append([
                cell["arm"], cell["budget_level"],
                cell["variant"] + (" *" if cell["extra"] else ""), cls,
                cell["by_class"][cls]["n"], term.get(T_APPLIED_CERT, 0),
                term.get(T_APPLIED_UNCERT, 0), term.get(T_BLOCKED_CORRECT, 0),
                term.get(T_BLOCKED_FALSE, 0), term.get(T_REFERRED, 0),
                term.get(T_EXECUTION_FAILED, 0),
            ])
    lines.extend(e1e.md_table(headers, table))
    return "\n".join(lines)


def to_json(cells: dict) -> list:
    """The cells as plain JSON, counters expanded."""
    out = []
    for key in sorted(cells):
        cell = dict(cells[key])
        cell["terminals"] = dict(cell["terminals"])
        cell["by_register"] = {
            r: {"n": v["n"], "warranted": v["warranted"], "terminals": dict(v["terminals"])}
            for r, v in cell["by_register"].items()
        }
        cell["by_class"] = {
            c: {"n": v["n"], "terminals": dict(v["terminals"])}
            for c, v in cell["by_class"].items()
        }
        cell["warranted_rate"] = (cell["warranted"] / cell["n"]) if cell["n"] else None
        cell["violation_pass_through_rate"] = (
            cell["violations_passed"] / cell["violations"]) if cell["violations"] else None
        cell["false_block_rate"] = (
            cell["benign_blocked"] / cell["benign"]) if cell["benign"] else None
        cell["cap_binding_share"] = (cell["exhausted"] / cell["n"]) if cell["n"] else None
        cell["median_all_tokens"] = (
            statistics.median(cell["tokens"]) if cell["tokens"] else None)
        cell["median_gap_accepted"] = _quantile(cell["gaps"], 0.5)
        cell["p90_gap_accepted"] = _quantile(cell["gaps"], 0.9)
        cell.pop("gaps", None)
        cell.pop("tokens", None)
        cell.pop("calls", None)
        cell.pop("proposals", None)
        out.append(cell)
    return out


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def evaluate_rows(rows: list, workers: int = 1) -> list:
    """Every trajectory under every variant; ``workers <= 1`` runs in process."""
    global _ROWS
    _ROWS = rows
    chunks = e1e.chunk_by_instance(rows)
    if workers <= 1:
        _init_worker()
        out = []
        for chunk in chunks:
            out.extend(_eval_chunk(chunk))
        return out
    ctx = mp.get_context("fork")
    with ctx.Pool(processes=workers, initializer=_init_worker) as pool:
        results = pool.map(_eval_chunk, chunks)
    return [r for chunk in results for r in chunk]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--traj", nargs="+", required=True,
                    help="one or more trajectories.jsonl written by e3_scaffold.py")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0, help="cap the trajectories (smoke)")
    ap.add_argument("--force", action="store_true", help="allow writing into a used dir")
    args = ap.parse_args()

    print(LAUNCH_QUESTIONS)
    inputs = sg.assert_inputs()
    print("\n[e3r] suite sha256  {} OK".format(inputs["suite_sha256"]))
    print("[e3r] schema sha256 {} OK".format(inputs["schema_sha256"]))

    out_dir = Path(args.out)
    if out_dir.exists() and any(out_dir.iterdir()) and not args.force:
        raise SystemExit(
            "REFUSING TO RUN: {} already has results. Move it aside or pass "
            "--force.".format(out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)

    rows, stats = load_trajectories([Path(p) for p in args.traj])
    if args.limit:
        rows = rows[: args.limit]
        stats["unique_keys"] = len(rows)
    cfgs = e1e.guard_configs()
    print("[e3r] guard configurations: {}".format(", ".join(
        "{} {}".format(name, cfg.config_hash[:16]) for name, cfg in cfgs.items())))
    print("[e3r] {} trajectory rows, {} unique keys, {} superseded, {} error rows".format(
        stats["rows_read"], stats["unique_keys"], stats["superseded"], stats["error_rows"]))

    started = time.perf_counter()
    verdicts = evaluate_rows(rows, args.workers)
    wall = time.perf_counter() - started
    print("[e3r] {} trajectories x {} variants evaluated in {:.1f}s".format(
        len(verdicts), 2, wall))

    mismatches = [v["replay_mismatch"] for v in verdicts if v["replay_mismatch"]]
    if mismatches:
        print("[e3r] WARNING: {} trajectory(ies) replay to a different verdict than the "
              "one logged live; the guard is deterministic, so this is a defect."
              .format(len(mismatches)))
    else:
        print("[e3r] every replayed first-final verdict equals the one logged live")

    with open(out_dir / "verdicts.jsonl", "w", encoding="utf-8") as fh:
        by_key = {tuple(v["key"]): v for v in verdicts}
        for row in rows:
            result = by_key.get(traj_key(row))
            if result is None:
                continue
            for name, verdict in sorted(result["variants"].items()):
                fh.write(json.dumps({
                    "arm": row["arm"], "model": row["model"],
                    "budget_level": row["budget_level"],
                    "budget_tokens": row["budget_tokens"],
                    "pipeline": row["pipeline"], "variant": name,
                    "in_freeze": name in FREEZE_VARIANTS,
                    "repeat": row["repeat"], "item_id": row["item_id"],
                    "primary_class": row["primary_class"], "subclass": row["subclass"],
                    "register": row["register"], "twin_id": row["twin_id"],
                    "twin_role": row["twin_role"],
                    "quality_visible_candidate": row.get("quality_visible_candidate"),
                    "instance_id": row["instance_id"], "stratum": row["stratum"],
                    "terminal": verdict["terminal"],
                    "guard_terminal": verdict["guard_terminal"],
                    "applied_source": verdict["applied_source"],
                    "proposals_guarded": verdict["proposals"],
                    "n_ops": verdict["n_ops"], "gap": verdict["gap"],
                    "blocking_codes": verdict["blocking_codes"],
                    "infra": verdict["infra"], "fingerprint": verdict["fingerprint"],
                    "budget_exhausted": row["budget_exhausted"],
                    "all_tokens": row["tokens"]["all"], "n_calls": row["n_calls"],
                    "stages": row["stages"], "outcome": row.get("outcome"),
                }, sort_keys=True) + "\n")

    cells = aggregate(rows, verdicts)
    pairs = twin_pairs(rows, verdicts)
    text = summarise(cells, pairs, rows, stats,
                     {n: c.config_hash for n, c in cfgs.items()}, mismatches)
    (out_dir / "summary.md").write_text(text)
    (out_dir / "summary.json").write_text(json.dumps(
        {"version": E3_EVAL_VERSION, "cells": to_json(cells), "twin_pairs": pairs,
         "stats": stats, "replay_mismatches": mismatches}, indent=1, default=str))
    (out_dir / "run_meta.json").write_text(json.dumps({
        "version": E3_EVAL_VERSION,
        "date": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "trajectory_logs": [str(p) for p in args.traj],
        "workers": args.workers, "wall_s": wall,
        "guard_config_hashes": {n: c.config_hash for n, c in cfgs.items()},
        "suite_sha256": inputs["suite_sha256"],
        "schema_sha256": inputs["schema_sha256"],
        "stats": stats,
        "terminal_mapping": "guidance Section 5.4; an empty operations list is a "
                            "referral and outranks the guard's own reading of it, and "
                            "an instrument fault is execution_failed, never a block",
    }, indent=1, default=str))
    print("\n" + text)
    print("\n[e3r] written to {}".format(out_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
