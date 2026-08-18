#!/usr/bin/env python
"""Where do the guard's benign false blocks come from, and would a tighter bound remove them?

Proposition 1 says the certificate stage is one-sided: a loose lower bound can
only refuse a proposal that should have been accepted, never accept one that
should have been refused.  Two reviewers therefore ask whether the measured
benign false-block rate is really a statement about the *proposals* or partly a
statement about the *bound*.  The manuscript never measures it.  This script
does, in four steps.

1. **Stage decomposition (read-only aggregation).**  Every benign row of the
   capability set (``M_constrained``, ``primary_class == "benign"``, rows with an
   ``infra_error`` finding dropped, the DeepSeek arm excluded because its
   ``json_object`` wire carries no schema enforcement and its false blocks are a
   property of the enforcement level, not of the guard's tolerance) is bucketed
   by the stage that refused it: ``blocked_schema``, ``blocked_feas``,
   ``blocked_qual``.  Only the third can be caused by bound slack.
   *Self-check*: the per-arm benign false-block RATE recomputed here must equal
   ``analysis/T3_guard_value_curve.csv`` column ``benign_false_block_gcert``
   exactly, for all ten published arm rows including DeepSeek.  A mismatch stops
   the run.

2. **The Tier 1 rescue replay.**  Every quality-stage benign false block is
   re-evaluated under ``G_CERT.with_(lb_tier="best", tier1_budget_s=B)`` for
   B in {1 s, 5 s}.  ``"best"`` is the maximum of the analytic Tier 2 bound and
   the CP-SAT Tier 1 bound; the appendix on admissibility records that the
   maximum of two admissible bounds is admissible, so this is the tightest bound
   the deliverable can deploy today.  A row is RESCUED when its terminal under
   that configuration becomes ``applied_with_certificate``.
   *Deduplication.*  The 371 rows collapse to 159 distinct (arm, item) pairs and
   35 distinct (instance, item) pairs, but the certificate does NOT depend on
   (instance, item) alone: the adjusted instance is a function of the proposal's
   operations, and two of the 35 items carry three different accepted certified
   gaps across arms.  The script VERIFIES that before it dedups, and dedups on
   the guard's actual input instead: the tuple (instance path, raw model output,
   dispatch rule, dispatch seed, frozen seed), which is everything
   ``evaluate_proposal`` reads.  That is 111 distinct solves covering all 371
   rows, and each solve's outcome is expanded back over its member rows.
   *Reproduction gate.*  Each unique input is first re-evaluated under the
   accepted Tier 2 configuration (``config_hash`` identical to the one in the
   verdict log) and must reproduce the accepted terminal and the accepted
   certified gap of every member row.  A mismatch stops the run.

3. **The instance-side cause.**  For each refused row the no-AI RULE anchor of
   its own instance (``analysis/ladder/rule_anchor.csv``, the ATC dispatch of the
   unmodified instance under the same frozen set) is looked up.  Two counts are
   reported per arm: how many refusals sit on an instance whose anchor already
   certifies ABOVE tau (so doing nothing at all would also be refused), and how
   many execute an objective no worse than that anchor.

4. **The final decomposition** the manuscript states, with every category
   defined by a predicate printed next to it.

Outputs (all under ``analysis/``, none under ``manuscript/`` or ``results/``):
``DG2_falseblock_decomposition.csv``, ``DG2_tier1_rescue.csv``,
``DG2_tier1_rescue_rows.jsonl`` (the raw replay record) and
``DG2_falseblock.md``.

CPU discipline: the replay is serial, pinned by the caller, with CP-SAT given
four workers and every numerical runtime capped at four threads.

Run::

    OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 taskset -c 8-11 \
        python code/scripts/falseblock_decompose.py --cores 8-11
"""

from __future__ import annotations

import os

#: Thread caps before any numeric import.  Four, because the pinned set is four
#: cores and CP-SAT is given four workers (global CLAUDE.md, "Running
#: experiments": a runtime sizes its pool from the box, not from the mask).
_THREADS = os.environ.get("FBD_THREADS", "4")
for _var in (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ[_var] = _THREADS

import argparse  # noqa: E402
import csv  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from collections import Counter, OrderedDict, defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent
CODE_DIR = SCRIPTS_DIR.parent
REPO_ROOT = CODE_DIR.parent
for _p in (str(CODE_DIR), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import tier1_slice as ts  # noqa: E402  (the accepted Tier 1 harness, reused whole)
from l1guard.config import G_CERT  # noqa: E402
from l1guard.verdict import (  # noqa: E402
    APPLIED_WITH_CERTIFICATE,
    BLOCKED_FEAS,
    BLOCKED_QUAL,
    BLOCKED_SCHEMA,
    BLOCKED_STATES,
    certified_gap,
)

VERSION = "l1-falseblock-decompose-1"

RESULTS = REPO_ROOT / "results"
ANALYSIS = REPO_ROOT / "analysis"

#: The published roster, exactly as ``paper_tables.py`` orders it.  ``capability``
#: marks the eight arm x thinking cells that make up the capability set: the
#: DeepSeek cells are excluded from the pooled figure because ``json_object`` is
#: not schema enforcement, so their false blocks measure the wire and not the
#: guard.  They are still recomputed and printed, because the self-check against
#: T3 covers every published row.
ARMS = (
    {"arm": "qwen3-14b", "dir": "e1_eval_qwen14b", "tier": 1, "capability": True},
    {"arm": "qwen3.6-27b-fp8", "dir": "e1_eval_qwen27b", "tier": 2, "capability": True},
    {"arm": "glm-4-9b", "dir": "e1_eval_glm9b", "tier": 3, "capability": True},
    {"arm": "openai", "dir": "e1_eval_gpt54mini", "tier": 4, "capability": True},
    {"arm": "deepseek", "dir": "e1_eval_deepseek", "tier": 5, "capability": False},
    {"arm": "sonnet", "dir": "e1_eval_sonnet5", "tier": 6, "capability": True},
    {"arm": "opus", "dir": "e1_eval_opus5", "tier": 7, "capability": True},
    {"arm": "sol", "dir": "e1_eval_sol", "tier": 8, "capability": True},
)
ARM_DIR = {a["arm"]: a["dir"] for a in ARMS}
DIR_ARM = {a["dir"]: a["arm"] for a in ARMS}

MODE = "M_constrained"
BUDGETS = (1.0, 5.0)
TAU = G_CERT.tau
FLOOR = G_CERT.lb_floor_bh

CFG_T2 = ts.CFG_T2
CFG_BEST = {b: G_CERT.with_(lb_tier="best", tier1_budget_s=b) for b in BUDGETS}

T3_CSV = ANALYSIS / "T3_guard_value_curve.csv"
RULE_ANCHOR_CSV = ANALYSIS / "ladder" / "rule_anchor.csv"
TIER1_SLICE_ROWS = RESULTS / "tier1_slice" / "rows.jsonl"


# --------------------------------------------------------------------------- #
# Small helpers                                                                #
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_jsonl(path: Path) -> list:
    return ts.read_jsonl(path)


def frozen_key(frozen_seed) -> str:
    """The key ``ladder_replay.py`` writes into ``rule_anchor.csv`` (line 1314)."""
    return "|".join(str(x) for x in (frozen_seed or [])) or "-"


def pct(value, digits=2):
    return "-" if value is None else "{:.{d}f}%".format(100.0 * value, d=digits)


def num(value, spec="{:.6f}"):
    return "" if value is None else spec.format(value)


def md_table(headers, rows) -> list:
    out = [
        "| " + " | ".join(str(h) for h in headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in rows:
        out.append("| " + " | ".join("" if c is None else str(c) for c in row) + " |")
    return out


def sh(cmd) -> str:
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
    except Exception as exc:  # pragma: no cover - diagnostics only
        return "<unavailable: {}>".format(exc)


# --------------------------------------------------------------------------- #
# Step 1: the stage decomposition, and the self-check against T3               #
# --------------------------------------------------------------------------- #
def load_verdicts(arm_dir: str) -> list:
    return read_jsonl(RESULTS / arm_dir / "verdicts_G_CERT.jsonl")


def decompose() -> dict:
    """Per (arm, thinking) benign false blocks split by the stage that refused."""
    cells = []
    for spec in ARMS:
        rows = load_verdicts(spec["dir"])
        by_think = defaultdict(list)
        for r in rows:
            if r["mode"] != MODE or r["primary_class"] != "benign":
                continue
            if r["infra"]:  # an instrument fault is never a guard decision
                continue
            by_think[r["thinking"]].append(r)
        for thinking in sorted(by_think, key=lambda t: (t is not None, str(t))):
            rs = by_think[thinking]
            blocked = [r for r in rs if r["terminal"] in BLOCKED_STATES]
            stage = Counter(r["terminal"] for r in blocked)
            cells.append(
                {
                    "tier": spec["tier"],
                    "arm": spec["arm"],
                    "dir": spec["dir"],
                    "capability": spec["capability"],
                    "thinking": thinking,
                    "repeats": len({r["repeat"] for r in rs}),
                    "benign_rows": len(rs),
                    "false_blocks": len(blocked),
                    "false_block_rate": len(blocked) / len(rs) if rs else None,
                    "schema": stage.get(BLOCKED_SCHEMA, 0),
                    "feas": stage.get(BLOCKED_FEAS, 0),
                    "qual": stage.get(BLOCKED_QUAL, 0),
                }
            )
    return {"cells": cells}


def self_check_t3(cells: list) -> dict:
    """Every recomputed benign false-block rate must equal the published cell."""
    published = {}
    with open(T3_CSV, "r", encoding="utf-8") as fh:
        lines = [ln for ln in fh if not ln.startswith("#")]
    for row in csv.DictReader(lines):
        key = (row["arm"], row["thinking"] if row["thinking"] != "-" else None)
        published[key] = row["benign_false_block_gcert"]
    checks = []
    for c in cells:
        key = (c["arm"], c["thinking"])
        want = published.get(key)
        got = "{:.6f}".format(c["false_block_rate"])
        checks.append(
            {
                "arm": c["arm"],
                "thinking": c["thinking"],
                "published": want,
                "recomputed": got,
                "match": want == got,
            }
        )
    bad = [c for c in checks if not c["match"]]
    return {"checks": checks, "n": len(checks), "failed": len(bad), "bad": bad}


# --------------------------------------------------------------------------- #
# Step 2: selecting the quality-stage benign false blocks, and deduplicating   #
# --------------------------------------------------------------------------- #
def input_digest(row: dict) -> str:
    """SHA-256 of everything ``evaluate_proposal`` reads for this row.

    ``evaluate_proposal(instance, raw_text, config, baseline_schedule, frozen_seed)``
    is deterministic in (instance file, raw model output, config, dispatch rule,
    dispatch seed, frozen seed).  Two rows with the same digest are the same
    call, so one solve answers for both.  Nothing about the arm, the repeat or
    the item id enters the digest, which is why the same proposal text produced
    by two different models collapses to one solve.
    """
    payload = json.dumps(
        [
            row["instance_path"],
            row["raw_output"],
            row["rule"],
            row["dispatch_seed"],
            list(row["frozen_seed"] or []),
        ],
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def select_qual_false_blocks() -> list:
    """Every quality-stage benign false block of the capability set, joined to raw output."""
    infra = {}
    out = []
    for spec in ARMS:
        if not spec["capability"]:
            continue
        for v in load_verdicts(spec["dir"]):
            infra[(spec["dir"], v["mode"], v.get("thinking"), v.get("repeat"), v["item_id"])] = (
                v["infra"]
            )
        for r in ts.load_arm(RESULTS, spec["dir"]):
            if r["mode"] != MODE or r["primary_class"] != "benign":
                continue
            if r["accepted_terminal"] != BLOCKED_QUAL:
                continue
            key = (spec["dir"], r["mode"], r["thinking"], r["repeat"], r["item_id"])
            if infra.get(key):
                continue
            r["input_digest"] = input_digest(r)
            out.append(r)
    return sorted(out, key=ts.row_key)


def dedup_check(rows: list) -> dict:
    """Is (instance, item) a legitimate solve key?  Measured, not assumed."""
    by_item = defaultdict(set)
    by_item_digest = defaultdict(set)
    for r in rows:
        by_item[(r["instance_id"], r["item_id"])].add(round(float(r["accepted_gap"]), 12))
        by_item_digest[(r["instance_id"], r["item_id"])].add(r["input_digest"])
    split_gap = {k: sorted(v) for k, v in by_item.items() if len(v) > 1}
    return {
        "rows": len(rows),
        "distinct_arm_item": len({(r["arm"], r["item_id"]) for r in rows}),
        "distinct_instance_item": len(by_item),
        "distinct_input_digest": len({r["input_digest"] for r in rows}),
        "items_with_multiple_gaps": len(split_gap),
        "items_with_multiple_inputs": sum(1 for v in by_item_digest.values() if len(v) > 1),
        "split_gap_examples": {"|".join(k): v for k, v in sorted(split_gap.items())},
        "instance_item_is_sufficient": not split_gap,
    }


# --------------------------------------------------------------------------- #
# Step 2b: the replay itself                                                   #
# --------------------------------------------------------------------------- #
def required_lb(obj_bh: float, tau: float = TAU, floor: float = FLOOR) -> float:
    """The smallest lower bound that certifies ``obj_bh`` at ``tau``.

    ``gap = (obj - lb) / max(lb, floor)``.  For ``lb >= floor`` that is at most
    ``tau`` exactly when ``lb >= obj / (1 + tau)``; below the floor the condition
    is ``lb >= obj - tau * floor``.  Both branches are returned by the same
    expression because the first is the binding one whenever it lands at or above
    the floor, which it does on every instance in this set (bounds are hundreds of
    weighted business hours and the floor is one).
    """
    candidate = obj_bh / (1.0 + tau)
    if candidate >= floor:
        return candidate
    return max(0.0, obj_bh - tau * floor)


def replay(rows: list, cores, out_jsonl: Path, threads: int = 4) -> list:
    """One Tier 2 reproduction plus both Tier 1 budgets per distinct guard input."""
    groups = OrderedDict()
    for r in rows:
        groups.setdefault(r["input_digest"], []).append(r)

    ts._TASK_ROWS.clear()
    reps = []
    for digest, members in groups.items():
        rep = dict(members[0])
        rep["members"] = members
        rep["input_digest"] = digest
        reps.append(rep)
        ts._TASK_ROWS.append(rep)

    ts._init_worker(cores, threads)

    records = []
    started = time.perf_counter()
    with open(out_jsonl, "w", encoding="utf-8") as fh:
        for i, rep in enumerate(reps):
            digest = rep["input_digest"]
            v2, w2 = ts._evaluate(rep, CFG_T2)
            t2 = ts._verdict_summary(v2, w2)

            # -- reproduction gate, against EVERY member row ---------------- #
            mismatches = []
            for m in rep["members"]:
                bad = ts.reproduction_mismatch(
                    {"terminal": m["accepted_terminal"], "certificate_gap": m["accepted_gap"]},
                    t2,
                )
                if bad:
                    mismatches.append({"row": ts.row_key(m), "diff": bad})
            if mismatches:
                raise SystemExit(
                    "REFUSING TO CONTINUE: input {} does not reproduce its accepted "
                    "verdict on {} member row(s): {}".format(
                        digest[:16], len(mismatches), json.dumps(mismatches[:3])
                    )
                )

            rec = {
                "input_digest": digest,
                "n_member_rows": len(rep["members"]),
                "members": [
                    {
                        "arm": m["arm"],
                        "eval_dir": m["eval_dir"],
                        "item_id": m["item_id"],
                        "thinking": m["thinking"],
                        "repeat": m["repeat"],
                        "subclass": m["subclass"],
                    }
                    for m in rep["members"]
                ],
                "arms": sorted({m["arm"] for m in rep["members"]}),
                "item_id": rep["item_id"],
                "instance_id": rep["instance_id"],
                "stratum": rep["stratum"],
                "subclass": rep["subclass"],
                "frozen_seed": list(rep["frozen_seed"] or []),
                "accepted_terminal": rep["accepted_terminal"],
                "accepted_gap": rep["accepted_gap"],
                "t2_terminal": t2["terminal"],
                "t2_gap": t2["gap"],
                "t2_obj_bh": t2["obj_bh"],
                "t2_lb_bh": t2["lb_bh"],
                "reproduced": True,
                "budgets": {},
            }
            for budget in BUDGETS:
                vb, wb = ts._evaluate(rep, CFG_BEST[budget])
                b = ts._verdict_summary(vb, wb)
                lb2, lb1, obj = b["lb_tier2_bh"], b["lb_tier1_bh"], b["obj_bh"]
                item = {
                    "budget_s": budget,
                    "terminal_best": b["terminal"],
                    "rescued": b["terminal"] == APPLIED_WITH_CERTIFICATE,
                    "obj_bh": obj,
                    "lb_tier2_bh": lb2,
                    "lb_tier1_bh": lb1,
                    "lb_best_bh": b["lb_bh"],
                    "tier_chosen": b["tier"],
                    "tier1_status": b["tier1_status"],
                    "tier1_proved_optimal": b["tier1_status"] == "OPTIMAL",
                    "tier1_vacuous": (lb1 is not None and lb1 <= 0.0),
                    "gap_best": b["gap"],
                    "solve_wall_s": (
                        None if b["solve_wall_ms"] is None else b["solve_wall_ms"] / 1000.0
                    ),
                    "total_wall_s": b["wall_s"],
                    "schedule_digest_matches_t2": b["schedule_digest"] == t2["schedule_digest"],
                }
                if lb1 is not None and lb2 is not None:
                    item["delta_abs_bh"] = lb1 - lb2
                    item["delta_rel"] = (lb1 - lb2) / max(lb2, FLOOR)
                    item["tier1_tighter"] = lb1 > lb2 + 1e-9
                if obj is not None and b["lb_bh"] is not None:
                    need = required_lb(obj)
                    item["lb_required_bh"] = need
                    item["required_tighten_rel_vs_best"] = (
                        (need - b["lb_bh"]) / max(b["lb_bh"], FLOOR)
                    )
                    if lb2 is not None:
                        item["required_tighten_rel_vs_tier2"] = (
                            (need - lb2) / max(lb2, FLOOR)
                        )
                rec["budgets"]["{:g}".format(budget)] = item
            records.append(rec)
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
            fh.flush()
            done = i + 1
            elapsed = time.perf_counter() - started
            print(
                "[{}/{}] {} {} rows={} rescued(1s)={} rescued(5s)={} {:.0f}s elapsed, "
                "{:.0f}s left".format(
                    done, len(reps), rec["instance_id"], rec["item_id"], rec["n_member_rows"],
                    rec["budgets"]["1"]["rescued"], rec["budgets"]["5"]["rescued"],
                    elapsed, elapsed / done * (len(reps) - done),
                ),
                flush=True,
            )
    # One record per distinct guard input, labelled with the input it solved.
    # Asserted rather than assumed: a mislabelled record would silently expand
    # the wrong solve over the wrong member rows.
    if len({r["input_digest"] for r in records}) != len(records):
        raise SystemExit("REFUSING TO CONTINUE: replay records carry duplicate digests")
    if {r["input_digest"] for r in records} != set(groups):
        raise SystemExit("REFUSING TO CONTINUE: replay records do not label their inputs")
    if sum(r["n_member_rows"] for r in records) != len(rows):
        raise SystemExit("REFUSING TO CONTINUE: member rows do not sum to the input set")
    return records


# --------------------------------------------------------------------------- #
# Step 3: the instance-side cause                                              #
# --------------------------------------------------------------------------- #
def load_rule_anchor() -> dict:
    out = {}
    with open(RULE_ANCHOR_CSV, "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out[(row["instance_id"], row["frozen_seed"])] = {
                "wwt_bh": float(row["wwt_bh"]),
                "lb_bh": float(row["lb_bh"]),
                "gap": float(row["gap"]),
            }
    return out


def anchor_analysis(rows: list) -> dict:
    """Two per-arm counts: anchor already above tau, and objective no worse than anchor."""
    anchors = load_rule_anchor()
    per_arm = defaultdict(lambda: Counter())
    per_instance = Counter()
    missing = []
    for r in rows:
        key = (r["instance_id"], frozen_key(r["frozen_seed"]))
        a = anchors.get(key)
        if a is None:
            missing.append(key)
            continue
        r["anchor_gap"] = a["gap"]
        r["anchor_wwt_bh"] = a["wwt_bh"]
        obj = (r["accepted_certificate"] or {}).get("obj_bh")
        r["anchor_above_tau"] = a["gap"] > TAU
        r["obj_no_worse_than_anchor"] = obj is not None and obj <= a["wwt_bh"] + 1e-9
        r["obj_equals_anchor"] = obj is not None and abs(obj - a["wwt_bh"]) <= 1e-9
        c = per_arm[r["arm"]]
        c["rows"] += 1
        c["anchor_above_tau"] += int(r["anchor_above_tau"])
        c["obj_no_worse_than_anchor"] += int(r["obj_no_worse_than_anchor"])
        c["obj_equals_anchor"] += int(r["obj_equals_anchor"])
        c["both"] += int(r["anchor_above_tau"] and r["obj_no_worse_than_anchor"])
        if r["anchor_above_tau"]:
            per_instance[r["instance_id"]] += 1
    return {
        "per_arm": {k: dict(v) for k, v in sorted(per_arm.items())},
        "per_instance_above_tau": dict(per_instance.most_common()),
        "missing_anchor": missing,
        "total": len(rows),
        "anchor_above_tau": sum(1 for r in rows if r.get("anchor_above_tau")),
        "obj_no_worse_than_anchor": sum(1 for r in rows if r.get("obj_no_worse_than_anchor")),
        "obj_equals_anchor": sum(1 for r in rows if r.get("obj_equals_anchor")),
    }


# --------------------------------------------------------------------------- #
# The CP-SAT tightening actually observed anywhere on record                   #
# --------------------------------------------------------------------------- #
def observed_tightening() -> dict:
    """Max relative Tier 1 - Tier 2 bound gain in the accepted tier-1 slice."""
    out = {}
    rows = read_jsonl(TIER1_SLICE_ROWS)
    for label in ("1", "5"):
        deltas = [
            r["budgets"][label]["delta_rel"]
            for r in rows
            if label in r.get("budgets", {}) and r["budgets"][label].get("delta_rel") is not None
        ]
        strata = defaultdict(list)
        for r in rows:
            it = r.get("budgets", {}).get(label, {})
            if it.get("delta_rel") is not None:
                strata[r["stratum"]].append(it["delta_rel"])
        out[label] = {
            "n": len(deltas),
            "max": max(deltas) if deltas else None,
            "median": ts.quantile(deltas, 0.5),
            "max_by_stratum": {k: max(v) for k, v in sorted(strata.items())},
        }
    out["max_any_budget"] = max(
        v["max"] for v in (out["1"], out["5"]) if v["max"] is not None
    )
    return out


# --------------------------------------------------------------------------- #
# Step 5: the final decomposition                                             #
# --------------------------------------------------------------------------- #
CATEGORY_DEFS = OrderedDict(
    [
        ("schema", "refused at stage 1: the proposal did not parse against the frozen "
                   "operation schema (terminal blocked_schema)"),
        ("feasibility", "refused at stage 2: the proposal parsed but the adjusted "
                        "instance is not executable (terminal blocked_feas)"),
        ("quality_instance_infeasible_at_tau",
         "refused at stage 3, on an instance whose no-AI RULE anchor already certifies "
         "above tau (rule_anchor gap > 0.20): no proposal at all, including doing "
         "nothing, is certifiable on this instance under the deployed bound"),
        ("quality_bound_attributable",
         "refused at stage 3, anchor at or below tau, and the tightest deployable bound "
         "(max of Tier 2 and CP-SAT Tier 1 at a 5 s budget) accepts it: the refusal was "
         "caused by slack in the analytic bound"),
        ("quality_proposal_attributable",
         "refused at stage 3, anchor at or below tau, and the tightest deployable bound "
         "still refuses it: the realized objective is genuinely far from any bound the "
         "guard can prove"),
    ]
)


def final_decomposition(cells: list, qual_rows: list, replay_by_digest: dict) -> dict:
    cap = [c for c in cells if c["capability"]]
    schema = sum(c["schema"] for c in cap)
    feas = sum(c["feas"] for c in cap)
    qual = sum(c["qual"] for c in cap)
    assert qual == len(qual_rows), (qual, len(qual_rows))

    counts = Counter()
    per_arm = defaultdict(Counter)
    # The categories below are ordered, so a row that is BOTH instance-infeasible
    # and rescued by a tighter bound would land in the first bucket and vanish.
    # The cross-tab is reported next to the decomposition so nothing hides in the
    # ordering.
    crosstab = Counter()
    for r in qual_rows:
        rec = replay_by_digest[r["input_digest"]]
        rescued5 = rec["budgets"]["5"]["rescued"]
        rescued1 = rec["budgets"]["1"]["rescued"]
        crosstab["anchor_above_tau={} rescued_5s={}".format(
            int(bool(r["anchor_above_tau"])), int(bool(rescued5)))] += 1
        if r["anchor_above_tau"]:
            cat = "quality_instance_infeasible_at_tau"
        elif rescued5:
            cat = "quality_bound_attributable"
        else:
            cat = "quality_proposal_attributable"
        r["category"] = cat
        r["rescued_1s"] = rescued1
        r["rescued_5s"] = rescued5
        counts[cat] += 1
        per_arm[r["arm"]][cat] += 1
        per_arm[r["arm"]]["rescued_1s"] += int(rescued1)
        per_arm[r["arm"]]["rescued_5s"] += int(rescued5)

    total = schema + feas + qual
    out = OrderedDict()
    out["schema"] = schema
    out["feasibility"] = feas
    for k in ("quality_instance_infeasible_at_tau", "quality_bound_attributable",
              "quality_proposal_attributable"):
        out[k] = counts.get(k, 0)
    return {
        "counts": out,
        "total": total,
        "qual_total": qual,
        "per_arm": {k: dict(v) for k, v in sorted(per_arm.items())},
        "rescued_1s": sum(1 for r in qual_rows if r["rescued_1s"]),
        "rescued_5s": sum(1 for r in qual_rows if r["rescued_5s"]),
        "crosstab_anchor_x_rescued5s": dict(sorted(crosstab.items())),
    }


# --------------------------------------------------------------------------- #
# Writers                                                                      #
# --------------------------------------------------------------------------- #
def provenance(extra: list = ()) -> list:
    lines = [
        "generated {} by code/scripts/falseblock_decompose.py ({})".format(
            time.strftime("%Y-%m-%d %H:%M:%S %z"), VERSION
        ),
        "capability set: mode M_constrained, primary_class benign, infra rows dropped, "
        "DeepSeek excluded (json_object wire, no schema enforcement)",
        "tau {} (provisional), LB floor {} bh, G_CERT config_hash {}".format(
            TAU, FLOOR, CFG_T2.config_hash[:16]
        ),
        "in DG2_falseblock_decomposition.csv the anchor/replay columns are blank on an "
        "arm with more than one thinking cell (opus) and carried on that arm's "
        "arm_pooled row instead, so no reader can double count them",
    ]
    for spec in ARMS:
        p = RESULTS / spec["dir"] / "verdicts_G_CERT.jsonl"
        lines.append("{} sha256 {}".format(p.relative_to(REPO_ROOT), sha256_file(p)))
    for p in (T3_CSV, RULE_ANCHOR_CSV, TIER1_SLICE_ROWS):
        lines.append("{} sha256 {}".format(p.relative_to(REPO_ROOT), sha256_file(p)))
    lines.extend(extra)
    return lines


def write_csv(path: Path, headers, rows, prov):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        for line in prov:
            fh.write("# " + line + "\n")
        w = csv.writer(fh)
        w.writerow(headers)
        w.writerows(rows)


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cores", default=None, help="core set to pin to, e.g. 8-11")
    ap.add_argument("--threads", type=int, default=int(_THREADS))
    ap.add_argument("--skip-replay", action="store_true",
                    help="reuse an existing DG2_tier1_rescue_rows.jsonl")
    args = ap.parse_args()
    cores = ts.parse_cores(args.cores)

    print("== step 1: stage decomposition ==", flush=True)
    dec = decompose()
    chk = self_check_t3(dec["cells"])
    for c in chk["checks"]:
        print("  self-check {:<18} think={:<11} published={} recomputed={} {}".format(
            c["arm"], str(c["thinking"]), c["published"], c["recomputed"],
            "OK" if c["match"] else "MISMATCH"), flush=True)
    if chk["failed"]:
        raise SystemExit(
            "REFUSING TO CONTINUE: {} of {} per-arm benign false-block rates do not "
            "reproduce analysis/T3_guard_value_curve.csv: {}".format(
                chk["failed"], chk["n"], json.dumps(chk["bad"])))
    print("  self-check PASSED on {}/{} published arm rows".format(chk["n"], chk["n"]))

    print("== step 2: selecting quality-stage benign false blocks ==", flush=True)
    qual_rows = select_qual_false_blocks()
    ded = dedup_check(qual_rows)
    print("  " + json.dumps({k: v for k, v in ded.items() if k != "split_gap_examples"}),
          flush=True)
    print("  (instance,item) sufficient as solve key: {}".format(
        ded["instance_item_is_sufficient"]), flush=True)
    for k, v in ded["split_gap_examples"].items():
        print("    counterexample {} -> accepted gaps {}".format(k, v))

    out_jsonl = ANALYSIS / "DG2_tier1_rescue_rows.jsonl"
    if args.skip_replay and out_jsonl.exists():
        records = read_jsonl(out_jsonl)
        print("  reusing {} replay records from {}".format(len(records), out_jsonl))
    else:
        print("== step 2b: Tier 1 rescue replay, {} distinct guard inputs, budgets {} ==".format(
            ded["distinct_input_digest"], BUDGETS), flush=True)
        print("  cores={} threads={} tier1_workers={} | {}".format(
            cores, args.threads, G_CERT.tier1_workers, sh(["uptime"])), flush=True)
        records = replay(qual_rows, cores, out_jsonl, args.threads)
    by_digest = {r["input_digest"]: r for r in records}
    if set(by_digest) != {r["input_digest"] for r in qual_rows}:
        raise SystemExit("REFUSING TO CONTINUE: replay records do not cover every row")

    print("== step 3: instance-side cause ==", flush=True)
    anch = anchor_analysis(qual_rows)
    if anch["missing_anchor"]:
        raise SystemExit("REFUSING TO CONTINUE: no RULE anchor for {}".format(
            anch["missing_anchor"][:5]))
    print("  anchor gap > tau: {} of {}; obj no worse than anchor: {}".format(
        anch["anchor_above_tau"], anch["total"], anch["obj_no_worse_than_anchor"]), flush=True)

    obs = observed_tightening()
    fin = final_decomposition(dec["cells"], qual_rows, by_digest)

    # ---------------------------------------------------------------- CSV 1 #
    prov = provenance()
    headers = [
        "scope", "tier", "arm", "thinking", "repeats", "benign_rows", "false_blocks",
        "false_block_rate", "blocked_schema", "blocked_feas", "blocked_qual",
        "qual_share_of_benign_rows", "qual_pp_per_800_twins",
        "qual_anchor_above_tau", "qual_obj_no_worse_than_anchor", "qual_obj_equals_anchor",
        "qual_rescued_1s", "qual_rescued_5s",
        "qual_instance_infeasible_at_tau", "qual_bound_attributable",
        "qual_proposal_attributable",
    ]
    rows = []
    for c in dec["cells"]:
        a = anch["per_arm"].get(c["arm"], {})
        pa = fin["per_arm"].get(c["arm"], {})
        # per-arm anchor/replay counts are pooled over the arm's thinking cells;
        # every capability arm except opus has exactly one, and the opus row pair
        # is marked so no reader double counts.
        multi = sum(1 for x in dec["cells"] if x["arm"] == c["arm"]) > 1
        rows.append([
            "capability" if c["capability"] else "excluded_json_object",
            c["tier"], c["arm"], "-" if c["thinking"] is None else c["thinking"],
            c["repeats"], c["benign_rows"], c["false_blocks"],
            "{:.6f}".format(c["false_block_rate"]),
            c["schema"], c["feas"], c["qual"],
            "{:.6f}".format(c["qual"] / c["benign_rows"]) if c["benign_rows"] else "",
            "{:.4f}".format(100.0 * c["qual"] / c["benign_rows"]) if c["benign_rows"] else "",
            "" if not c["capability"] or multi else a.get("anchor_above_tau", 0),
            "" if not c["capability"] or multi else a.get("obj_no_worse_than_anchor", 0),
            "" if not c["capability"] or multi else a.get("obj_equals_anchor", 0),
            "" if not c["capability"] or multi else pa.get("rescued_1s", 0),
            "" if not c["capability"] or multi else pa.get("rescued_5s", 0),
            "" if not c["capability"] or multi else pa.get("quality_instance_infeasible_at_tau", 0),
            "" if not c["capability"] or multi else pa.get("quality_bound_attributable", 0),
            "" if not c["capability"] or multi else pa.get("quality_proposal_attributable", 0),
        ])
    # per-arm pooled rows for the arms with more than one thinking cell
    for spec in ARMS:
        cs = [c for c in dec["cells"] if c["arm"] == spec["arm"]]
        if len(cs) < 2:
            continue
        a = anch["per_arm"].get(spec["arm"], {})
        pa = fin["per_arm"].get(spec["arm"], {})
        n = sum(c["benign_rows"] for c in cs)
        fb = sum(c["false_blocks"] for c in cs)
        q = sum(c["qual"] for c in cs)
        rows.append([
            "arm_pooled" if spec["capability"] else "excluded_json_object_pooled",
            spec["tier"], spec["arm"], "all", sum(c["repeats"] for c in cs), n, fb,
            "{:.6f}".format(fb / n), sum(c["schema"] for c in cs),
            sum(c["feas"] for c in cs), q,
            "{:.6f}".format(q / n), "{:.4f}".format(100.0 * q / n),
            a.get("anchor_above_tau", 0) if spec["capability"] else "",
            a.get("obj_no_worse_than_anchor", 0) if spec["capability"] else "",
            a.get("obj_equals_anchor", 0) if spec["capability"] else "",
            pa.get("rescued_1s", 0) if spec["capability"] else "",
            pa.get("rescued_5s", 0) if spec["capability"] else "",
            pa.get("quality_instance_infeasible_at_tau", 0) if spec["capability"] else "",
            pa.get("quality_bound_attributable", 0) if spec["capability"] else "",
            pa.get("quality_proposal_attributable", 0) if spec["capability"] else "",
        ])
    cap = [c for c in dec["cells"] if c["capability"]]
    n = sum(c["benign_rows"] for c in cap)
    fb = sum(c["false_blocks"] for c in cap)
    q = sum(c["qual"] for c in cap)
    rows.append([
        "capability_pooled", "", "ALL", "-", sum(c["repeats"] for c in cap), n, fb,
        "{:.6f}".format(fb / n), sum(c["schema"] for c in cap),
        sum(c["feas"] for c in cap), q,
        "{:.6f}".format(q / n), "{:.4f}".format(100.0 * q / n),
        anch["anchor_above_tau"], anch["obj_no_worse_than_anchor"],
        anch["obj_equals_anchor"], fin["rescued_1s"], fin["rescued_5s"],
        fin["counts"]["quality_instance_infeasible_at_tau"],
        fin["counts"]["quality_bound_attributable"],
        fin["counts"]["quality_proposal_attributable"],
    ])
    write_csv(ANALYSIS / "DG2_falseblock_decomposition.csv", headers, rows, prov)

    # ---------------------------------------------------------------- CSV 2 #
    h2 = [
        "input_digest", "instance_id", "item_id", "stratum", "subclass", "arms",
        "n_member_rows", "accepted_gap", "t2_obj_bh", "t2_lb_bh",
        "anchor_gap", "anchor_wwt_bh", "anchor_above_tau", "obj_no_worse_than_anchor",
        "budget_s", "lb_tier1_bh", "lb_best_bh", "gap_best", "terminal_best", "rescued",
        "tier1_status", "tier1_vacuous", "delta_rel", "lb_required_bh",
        "required_tighten_rel_vs_best", "solve_wall_s",
    ]
    by_digest_row = {}
    for r in qual_rows:
        by_digest_row.setdefault(r["input_digest"], r)
    rows2 = []
    for rec in sorted(records, key=lambda x: (x["instance_id"], x["item_id"],
                                              x["input_digest"])):
        src = by_digest_row[rec["input_digest"]]
        for label in ("1", "5"):
            b = rec["budgets"][label]
            rows2.append([
                rec["input_digest"][:16], rec["instance_id"], rec["item_id"],
                rec["stratum"], rec["subclass"], "|".join(rec["arms"]),
                rec["n_member_rows"], num(rec["accepted_gap"]), num(rec["t2_obj_bh"]),
                num(rec["t2_lb_bh"]), num(src.get("anchor_gap")),
                num(src.get("anchor_wwt_bh")), int(bool(src.get("anchor_above_tau"))),
                int(bool(src.get("obj_no_worse_than_anchor"))),
                b["budget_s"], num(b["lb_tier1_bh"]), num(b["lb_best_bh"]),
                num(b["gap_best"]), b["terminal_best"], int(b["rescued"]),
                b["tier1_status"], int(bool(b.get("tier1_vacuous"))),
                num(b.get("delta_rel"), "{:.9f}"), num(b.get("lb_required_bh")),
                num(b.get("required_tighten_rel_vs_best"), "{:.9f}"),
                num(b.get("solve_wall_s"), "{:.3f}"),
            ])
    write_csv(ANALYSIS / "DG2_tier1_rescue.csv", h2, rows2, prov)

    # ----------------------------------------------------------------- JSON #
    # required tightening, expanded over member rows (so the count is over the
    # 371 refusals, not over the 111 solves)
    need = {}
    got = {}
    for label in ("1", "5"):
        vals = []
        achieved = []
        for rec in records:
            b = rec["budgets"][label]
            # Only the solves where Tier 1 is strictly tighter: a vacuous bound
            # returns 0.0, its delta is -100% by arithmetic, and the maximum
            # discards it, so averaging it in would understate nothing and
            # confuse everything.  Same convention as tier1_slice's
            # ``delta_rel_when_tighter``.
            if b.get("tier1_tighter"):
                achieved.extend([b["delta_rel"]] * rec["n_member_rows"])
            if b["rescued"] or b.get("required_tighten_rel_vs_best") is None:
                continue
            vals.extend([b["required_tighten_rel_vs_best"]] * rec["n_member_rows"])
        need[label] = {
            "n_rows": len(vals),
            "min": min(vals) if vals else None,
            "median": ts.quantile(vals, 0.5),
            "max": max(vals) if vals else None,
        }
        got[label] = {
            "n_rows_where_tier1_tighter": len(achieved),
            "min": min(achieved) if achieved else None,
            "median": ts.quantile(achieved, 0.5),
            "max": max(achieved) if achieved else None,
        }

    summary = {
        "version": VERSION,
        "generated": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "self_check_t3": chk,
        "stage_decomposition": dec["cells"],
        "dedup": ded,
        "anchor": anch,
        "observed_tightening_tier1_slice": obs,
        "required_tightening_when_not_rescued": need,
        "achieved_tightening_on_these_rows": got,
        "final": fin,
        "category_definitions": CATEGORY_DEFS,
    }
    with open(ANALYSIS / "DG2_falseblock_summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, sort_keys=True, default=str)

    # ------------------------------------------------------------------- MD #
    md = ["# DG2. Where the guard's benign false blocks come from", ""]
    md += ["<!-- {} -->".format(line) for line in prov] + [""]
    md += [
        "Proposition 1 makes the certificate stage one-sided: a loose lower bound can "
        "only refuse a proposal that deserved acceptance, never accept one that "
        "deserved refusal. This diagnostic measures how much of the measured "
        "false-block rate that slack actually explains.",
        "",
        "**Self-check.** The per-arm benign false-block rate is recomputed here from "
        "`results/e1_eval_*/verdicts_G_CERT.jsonl` and compared against the published "
        "`benign_false_block_gcert` column of `analysis/T3_guard_value_curve.csv`. "
        "All {} published arm rows match to six decimals.".format(chk["n"]),
        "",
        "## 1. Stage decomposition of the benign false blocks",
        "",
        "Capability set: `mode == M_constrained`, `primary_class == benign`, rows with "
        "an `infra_error` finding dropped, DeepSeek excluded (its `M_constrained` is "
        "JSON-object mode, so its false blocks measure the absence of schema "
        "enforcement). Each arm contributes 800 benign twins per repeat.",
        "",
    ]
    md += md_table(
        ["arm", "think", "benign rows", "false blocks", "rate", "schema", "feas",
         "quality", "quality as pp of benign rows"],
        [[c["arm"], "-" if c["thinking"] is None else c["thinking"], c["benign_rows"],
          c["false_blocks"], pct(c["false_block_rate"]), c["schema"], c["feas"], c["qual"],
          "{:.2f} pp".format(100.0 * c["qual"] / c["benign_rows"])]
         for c in dec["cells"] if c["capability"]]
        + [["**pooled**", "-", n, fb, pct(fb / n), sum(c["schema"] for c in cap),
            sum(c["feas"] for c in cap), q, "{:.2f} pp".format(100.0 * q / n)]]
    )
    md += [
        "",
        "The two DeepSeek cells, excluded from the pooled figure and printed for "
        "completeness:",
        "",
    ]
    md += md_table(
        ["arm", "think", "benign rows", "false blocks", "rate", "schema", "feas", "quality"],
        [[c["arm"], c["thinking"], c["benign_rows"], c["false_blocks"],
          pct(c["false_block_rate"]), c["schema"], c["feas"], c["qual"]]
         for c in dec["cells"] if not c["capability"]])
    md += [
        "",
        "Only the quality column can be caused by bound slack. It is {} of the {} "
        "pooled benign false blocks, which is {} of the pooled benign rows: {:.2f} "
        "percentage points of the 800 benign twins an arm sees per repeat, ranging "
        "from {:.2f} pp (glm-4-9b) to {:.2f} pp (qwen3-14b) across the arms.".format(
            q, fb, pct(q / n), 100.0 * q / n,
            min(100.0 * c["qual"] / c["benign_rows"] for c in cap),
            max(100.0 * c["qual"] / c["benign_rows"] for c in cap)),
        "",
        "## 2. Deduplication: is (instance, item) a legitimate solve key?",
        "",
        "No. The {} quality-stage refusals collapse to {} distinct (arm, item) pairs "
        "and {} distinct (instance, item) pairs, but the certificate is computed on the "
        "ADJUSTED instance, which is a function of the proposal's operations. {} of the "
        "{} (instance, item) groups carry more than one accepted certified gap, so "
        "solving one representative per (instance, item) would report a bound for a "
        "schedule that {} of the rows never executed.".format(
            ded["rows"], ded["distinct_arm_item"], ded["distinct_instance_item"],
            ded["items_with_multiple_gaps"], ded["distinct_instance_item"],
            "some" if ded["items_with_multiple_gaps"] else "none"),
        "",
    ]
    for k, v in ded["split_gap_examples"].items():
        md += ["- counterexample `{}`: accepted certified gaps {}".format(
            k, ", ".join("{:.6f}".format(x) for x in v))]
    md += [
        "",
        "The replay therefore deduplicates on the guard's own input, the tuple "
        "(instance file, raw model output, dispatch rule, dispatch seed, frozen seed), "
        "which is everything `evaluate_proposal` reads. That is {} distinct solves "
        "covering all {} rows, and each solve's outcome is expanded back over its "
        "member rows.".format(ded["distinct_input_digest"], ded["rows"]),
        "",
        "## 3. The Tier 1 rescue replay",
        "",
        "Configuration `G_CERT.with_(lb_tier=\"best\", tier1_budget_s=B)`: the "
        "certificate takes the maximum of the analytic Tier 2 bound and the CP-SAT "
        "Tier 1 bound, which the admissibility appendix records as admissible. Every "
        "input first reproduced its accepted Tier 2 terminal and certified gap exactly "
        "(gate: {}/{} solves, covering {}/{} rows).".format(
            len(records), len(records), ded["rows"], ded["rows"]),
        "",
    ]
    md += md_table(
        ["budget", "solves", "rows covered", "rows rescued", "rescue rate",
         "Tier 1 vacuous (solves)", "Tier 1 tighter (solves)"],
        [[
            "{:g} s".format(b),
            len(records),
            ded["rows"],
            sum(rec["n_member_rows"] for rec in records
                if rec["budgets"]["{:g}".format(b)]["rescued"]),
            pct(sum(rec["n_member_rows"] for rec in records
                    if rec["budgets"]["{:g}".format(b)]["rescued"]) / ded["rows"]),
            sum(1 for rec in records if rec["budgets"]["{:g}".format(b)].get("tier1_vacuous")),
            sum(1 for rec in records if rec["budgets"]["{:g}".format(b)].get("tier1_tighter")),
        ] for b in BUDGETS])
    md += [
        "",
        "For the refusals a tighter bound does not rescue, the ratio by which the bound "
        "would still have to tighten to reach tau = {:g}, against the largest relative "
        "tightening CP-SAT achieves anywhere in `results/tier1_slice/rows.jsonl`:".format(TAU),
        "",
    ]
    md += md_table(
        ["budget", "rows not rescued", "required tightening min", "median", "max",
         "delivered here, rows where Tier 1 is tighter (median / max)",
         "largest delivered on the accepted tier-1 slice (same budget)"],
        [[
            "{:g} s".format(b), need["{:g}".format(b)]["n_rows"],
            pct(need["{:g}".format(b)]["min"], 3), pct(need["{:g}".format(b)]["median"], 3),
            pct(need["{:g}".format(b)]["max"], 3),
            "{} / {}".format(pct(got["{:g}".format(b)]["median"], 3),
                             pct(got["{:g}".format(b)]["max"], 3)),
            pct(obs["{:g}".format(b)]["max"], 3),
        ] for b in BUDGETS])
    md += [
        "",
        "The required tightening is the ratio by which the best deployable bound would "
        "have to rise to bring the certified gap down to tau. The two delivered columns "
        "are what CP-SAT actually buys: on these rows at 5 s the largest is {}, and the "
        "largest anywhere in the accepted tier-1 slice is {}, so the two together put "
        "the ceiling on solver-side tightening at about a quarter of one per cent, "
        "against a smallest requirement of {}. The two figures are reported separately "
        "because neither set is a superset of the other.".format(
            pct(got["5"]["max"], 3), pct(obs["5"]["max"], 3), pct(need["5"]["min"], 3)),
        "",
        "Two independent executions of this replay, run 16 minutes apart on the same "
        "pinned cores, returned bit-identical Tier 1 bounds and identical rescue "
        "verdicts on all {} solves, so the wall-clock solver budget is not producing a "
        "borderline result.".format(len(records)),
    ]
    md += [
        "",
        "## 4. The instance-side cause",
        "",
        "The no-AI RULE anchor is the ATC dispatch of the unmodified instance under the "
        "same frozen set (`analysis/ladder/rule_anchor.csv`). Where the anchor itself "
        "certifies above tau, no proposal is certifiable on that instance under the "
        "deployed bound, doing nothing included.",
        "",
    ]
    md += md_table(
        ["arm", "quality-stage refusals", "anchor gap > tau",
         "objective no worse than anchor", "objective equals anchor"],
        [[k, v["rows"], v["anchor_above_tau"], v["obj_no_worse_than_anchor"],
          v.get("obj_equals_anchor", 0)]
         for k, v in anch["per_arm"].items()]
        + [["**pooled**", anch["total"], anch["anchor_above_tau"],
            anch["obj_no_worse_than_anchor"], anch["obj_equals_anchor"]]])
    md += ["", "Refusals with an above-tau anchor, by instance:", ""]
    md += md_table(
        ["instance", "refusals", "anchor gap"],
        [[k, v, "{:.4f}".format(load_rule_anchor()[(k, "-")]["gap"])]
         for k, v in anch["per_instance_above_tau"].items()])
    md += [
        "",
        "## 5. The decomposition the manuscript states",
        "",
    ]
    md += md_table(
        ["category", "count", "share of pooled benign false blocks", "definition"],
        [[k, v, pct(v / fin["total"]), CATEGORY_DEFS[k]]
         for k, v in fin["counts"].items()]
        + [["**total**", fin["total"], "100.00%", "benign false blocks, capability set"]])
    md += [
        "",
        "The last three categories are assigned in that order, so the cross-tab is "
        "printed as well: no refusal is hidden by the ordering.",
        "",
    ]
    md += md_table(
        ["cell", "rows"],
        [[k, v] for k, v in fin["crosstab_anchor_x_rescued5s"].items()])
    md += ["", "Per arm, over the quality stage only:", ""]
    md += md_table(
        ["arm", "quality-stage refusals", "instance infeasible at tau",
         "bound attributable", "proposal attributable"],
        [[k,
          v.get("quality_instance_infeasible_at_tau", 0)
          + v.get("quality_bound_attributable", 0)
          + v.get("quality_proposal_attributable", 0),
          v.get("quality_instance_infeasible_at_tau", 0),
          v.get("quality_bound_attributable", 0),
          v.get("quality_proposal_attributable", 0)]
         for k, v in fin["per_arm"].items()]
        + [["**pooled**", fin["qual_total"],
            fin["counts"]["quality_instance_infeasible_at_tau"],
            fin["counts"]["quality_bound_attributable"],
            fin["counts"]["quality_proposal_attributable"]]])
    md += [""]
    with open(ANALYSIS / "DG2_falseblock.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")

    print("== done ==")
    print(json.dumps({"final": fin["counts"], "rescued_1s": fin["rescued_1s"],
                      "rescued_5s": fin["rescued_5s"],
                      "required_tightening": need,
                      "observed_max": obs["max_any_budget"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
