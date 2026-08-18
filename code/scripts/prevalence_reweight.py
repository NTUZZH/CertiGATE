#!/usr/bin/env python
"""Prevalence re-weighting of the as-is/to-be ladder (DG3).

Why
---
The benchmark suite is 60% non-benign by construction (1,200 of 2,000 items).
Every ladder quantity in T4/T5 is therefore an average over a *designed*
mixture, not over a field instruction stream.  A reviewer can read the ladder's
mean weighted tardiness as a descriptive claim about practice, which it is not.
This script restates the ladder at *declared* violation prevalences, so the
manuscript can say "at a declared prevalence of p, the certified rung sits X
business hours from the no-AI anchor" instead of relying on the suite's own
mixture.

The scheme
----------
Hold the composition *within* the benign set and *within* the violation set
fixed, and vary only the mixture weight.  For a declared violation prevalence
``p`` every suite row gets the weight

    w_benign    = (1 - p) / 0.40        (800 benign items are 40% of the suite)
    w_violation =       p / 0.60        (1,200 violation items are 60%)

Normalised, this makes the weighted mean of any per-row quantity ``x``

    mean(p) = (1 - p) * mean_benign(x) + p * mean_violation(x),

i.e. **linear in p**.  At ``p = 0.60`` the weights are both 1 and every
re-weighted quantity collapses to the published full-suite value exactly; that
identity is this script's self-check, asserted against ``ladder_anchors.json``.

Because both the rung and the RULE (no-AI) anchor are linear in p, so is their
difference, and the prevalence at which a rung crosses the no-AI anchor is
closed form:

    delta(p) = A + B p,   A = delta(0),   B = delta(1) - delta(0),   p* = -A / B.

The script computes p* in closed form and *verifies* linearity by comparing the
closed form against the directly re-weighted grid values.

What is invariant
-----------------
A rate whose denominator is the violation set (violation pass-through, and its
non-empty variant) is unchanged by the re-weighting for every p > 0, because
the weight cancels between numerator and denominator.  The script checks this
numerically rather than asserting it, so the manuscript does not print three
identical columns by accident.

Inputs (read-only)
------------------
analysis/ladder/oracle_items.jsonl          per-item RULE / ORACLE / ORACLE+G_CERT
analysis/ladder/rule_anchor.json            the no-AI anchor per (instance, frozen set)
analysis/ladder/unguarded_objective_patch.jsonl   priced UNGUARDED replays
analysis/ladder/ladder_anchors.json         the published profiles (self-check target)
results/e1_eval_*/proposals.jsonl           executed objectives
results/e1_eval_*/verdicts_{UNGUARDED,G_FEAS,G_CERT}.jsonl

Outputs
-------
analysis/DG3_prevalence.csv                 long format: one row per (rung, p)
analysis/DG3_prevalence.md                  the readable summary

Run::

    OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 taskset -c 0-3 \
        /home/ziheng/miniconda3/envs/fjsp/bin/python \
        code/scripts/prevalence_reweight.py

Exit code 0 only when every self-check passed; 2 when any failed.
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
    os.environ.setdefault(_var, "4")

import argparse  # noqa: E402
import csv  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
from collections import OrderedDict  # noqa: E402
from pathlib import Path  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ANALYSIS = REPO_ROOT / "analysis"
LADDER = ANALYSIS / "ladder"
RESULTS = REPO_ROOT / "results"

VERSION = "l1-dg3-prevalence-1"

# ---------------------------------------------------------------------------#
# Constants mirrored from code/scripts/ladder_replay.py (the accepted record)  #
# ---------------------------------------------------------------------------#
APPLIED_WITH_CERTIFICATE = "applied_with_certificate"
APPLIED_UNCERTIFIED = "applied_uncertified"
BLOCKED_SCHEMA = "blocked_schema"
BLOCKED_FEAS = "blocked_feas"
BLOCKED_QUAL = "blocked_qual"
EXECUTION_FAILED = "execution_failed"
MODEL_REFUSED = "model_refused"
REFERRED = "referred_to_human"
UNHANDLED = "unhandled"
BLOCKED_STATES = (BLOCKED_SCHEMA, BLOCKED_FEAS, BLOCKED_QUAL)
APPLIED_STATES = (APPLIED_WITH_CERTIFICATE, APPLIED_UNCERTIFIED)
WARRANTED_STATES = (APPLIED_WITH_CERTIFICATE, "blocked_correctly", REFERRED)
BENIGN = "benign"

#: The suite's designed mixture.  1,200 of 2,000 items carry a violation label.
SUITE_VIOLATION_SHARE = 0.60
SUITE_BENIGN_SHARE = 0.40

#: Declared prevalences the manuscript will quote.  0.60 is the suite's own
#: mixture and is the self-check point, not a claim about practice.
P_GRID = (0.01, 0.02, 0.05, 0.10, 0.15, 0.30, 0.60)

#: Float tolerance for the self-checks.  Both sides compute the same sum of the
#: same numbers, so this only absorbs the JSON round trip and the re-association
#: of the mean into a benign/violation split.
RTOL = 1e-9


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path):
    out = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def frozen_key(frozen_seed) -> str:
    return ",".join(str(x) for x in (frozen_seed or ()))


def profile_state(terminal: str, primary_class: str) -> str:
    """Section 5.4 profile state, exactly as ladder_replay.profile_state."""
    if terminal in (APPLIED_WITH_CERTIFICATE, APPLIED_UNCERTIFIED, REFERRED, UNHANDLED):
        return terminal
    if terminal in BLOCKED_STATES:
        return "blocked_correctly" if primary_class != BENIGN else "blocked_falsely"
    if terminal == EXECUTION_FAILED:
        return EXECUTION_FAILED
    if terminal == MODEL_REFUSED:
        return MODEL_REFUSED
    raise ValueError("unknown terminal {!r}".format(terminal))


# ---------------------------------------------------------------------------#
# The reconciler                                                              #
# ---------------------------------------------------------------------------#
class Checks:
    def __init__(self):
        self.rows = []
        self.max_rel_dev = 0.0

    def check(self, scope, label, expected, got, rtol=RTOL):
        if expected is None or got is None:
            ok = expected is got
        else:
            scale = max(abs(float(expected)), abs(float(got)), 1.0)
            dev = abs(float(expected) - float(got)) / scale
            self.max_rel_dev = max(self.max_rel_dev, dev)
            ok = dev <= rtol
        self.rows.append(
            {"scope": scope, "label": label, "expected": expected, "got": got, "ok": ok}
        )
        return ok

    @property
    def n(self):
        return len(self.rows)

    @property
    def failed(self):
        return [r for r in self.rows if not r["ok"]]

    def ok(self):
        return not self.failed


# ---------------------------------------------------------------------------#
# Per-row entries                                                             #
# ---------------------------------------------------------------------------#
def oracle_entry_lists(items):
    """RULE, ORACLE and ORACLE+G_CERT per-item entries from oracle_items.jsonl.

    The mapping is the one ladder_replay.py used to write ladder_anchors.json:
    a blocked, referred or failed instruction leaves the baseline standing, so
    its executed quality is the RULE anchor; an applied one takes the objective
    of the schedule that was dispatched.
    """
    rule, oracle, oracle_g = [], [], []
    for r in items:
        cls = r["primary_class"]
        base = {
            "item_id": r["item_id"],
            "primary_class": cls,
            "benign": cls == BENIGN,
        }
        rule.append(
            dict(
                base,
                profile_state=UNHANDLED,
                applied=False,
                n_ops=0,
                wwt=r["rule_wwt_original_bh"],
            )
        )
        oracle.append(
            dict(
                base,
                profile_state=r["oracle_profile_state"],
                applied=r["oracle_terminal"] in APPLIED_STATES,
                n_ops=r["oracle_n_ops"],
                wwt=r["oracle_wwt_original_bh"],
            )
        )
        g_applied = r["oracle_guarded_terminal"] in APPLIED_STATES
        oracle_g.append(
            dict(
                base,
                profile_state=r["oracle_guarded_profile_state"],
                applied=g_applied,
                n_ops=r["oracle_n_ops"] if g_applied else 0,
                wwt=(r["oracle_wwt_original_bh"] if g_applied
                     else r["rule_wwt_original_bh"]),
            )
        )
    return {"RULE": rule, "ORACLE": oracle, "ORACLE+G_CERT": oracle_g}


def arm_entry_lists(eval_dir: Path, anchors_by_id: dict, patch: dict):
    """Per-row entries for UNGUARDED / G_FEAS / G_CERT, plus the matched RULE rows.

    This reproduces ladder_replay.arm_entries without re-running the guard: the
    ~766 UNGUARDED rows the accepted log cannot price are taken from the
    persisted replay in analysis/ladder/unguarded_objective_patch.jsonl.
    """
    proposals = read_jsonl(eval_dir / "proposals.jsonl")
    rows = []
    for rec in proposals:
        extra = rec.get("extra") or {}
        rows.append(
            {
                "item_id": rec["instruction_id"],
                "instance_id": rec["instance_id"],
                "mode": rec["mode"],
                "arm": extra["arm"],
                "thinking": extra.get("thinking"),
                "repeat": extra.get("repeat"),
                "primary_class": extra["primary_class"],
                "frozen_seed": rec.get("frozen_seed") or [],
                "_objective": (rec.get("verdict") or {}).get("objective"),
            }
        )

    configs = ("UNGUARDED", "G_FEAS", "G_CERT")
    verdicts = {}
    for config in configs:
        by_key = {}
        for row in read_jsonl(eval_dir / "verdicts_{}.jsonl".format(config)):
            by_key[(row["mode"], row.get("thinking"), row.get("repeat"),
                    row["item_id"])] = row
        verdicts[config] = by_key

    out = {config: [] for config in configs}
    out["RULE"] = []
    for row in rows:
        akey = (row["instance_id"], frozen_key(row["frozen_seed"]))
        anchor = anchors_by_id[akey]
        vkey = (row["mode"], row.get("thinking"), row.get("repeat"), row["item_id"])
        pkey = (row["arm"], row["mode"], row.get("thinking"), row.get("repeat"),
                row["item_id"])
        base = {
            "item_id": row["item_id"],
            "primary_class": row["primary_class"],
            "benign": row["primary_class"] == BENIGN,
            "mode": row["mode"],
            "thinking": row.get("thinking"),
        }
        # The matched no-AI anchor: the same row multiset, every instruction
        # unhandled.  Built here rather than reused from the item-level RULE so
        # the arm's own repeat structure is carried exactly.
        out["RULE"].append(
            dict(base, profile_state=UNHANDLED, applied=False, n_ops=0,
                 wwt=anchor["wwt_original_bh"])
        )
        for config in configs:
            verdict = verdicts[config][vkey]
            terminal = verdict["terminal"]
            applied = terminal in APPLIED_STATES
            n_ops = verdict.get("n_ops") or 0
            wwt = anchor["wwt_original_bh"]
            if applied and n_ops != 0:
                patched = patch.get((config, pkey))
                if patched is not None:
                    wwt = patched["wwt_original_bh"]
                else:
                    objective = row["_objective"]
                    cert_gap = verdicts["G_CERT"][vkey].get("certificate_gap")
                    if objective is None or cert_gap is None:
                        wwt = None
                    else:
                        wwt = objective.get("wwt_original_bh")
            out[config].append(
                dict(base, profile_state=profile_state(terminal, row["primary_class"]),
                     applied=applied, n_ops=n_ops, wwt=wwt)
            )
    return out


# ---------------------------------------------------------------------------#
# Aggregation                                                                 #
# ---------------------------------------------------------------------------#
def split_stats(entries):
    """Within-benign and within-violation statistics; the whole re-weighting basis.

    Everything downstream is a convex combination of these two numbers, so this
    is the only place per-row data is touched.
    """
    ben = [e for e in entries if e["benign"]]
    vio = [e for e in entries if not e["benign"]]
    if not ben or not vio:
        raise SystemExit("REFUSING TO RUN: a rung with an empty benign or violation set")
    missing = [e for e in entries if e["wwt"] is None]
    if missing:
        raise SystemExit(
            "REFUSING TO RUN: {} rows carry no executed objective; the published "
            "profiles report quality_coverage 1.0, so a re-weighted mean over a "
            "shorter denominator would not be the same quantity.".format(len(missing))
        )

    def m(rows):
        return sum(r["wwt"] for r in rows) / len(rows)

    def warranted(rows):
        return sum(1 for r in rows if r["profile_state"] in WARRANTED_STATES) / len(rows)

    applied_vio = [e for e in vio if e["applied"]]
    return {
        "n": len(entries),
        "n_benign": len(ben),
        "n_violation": len(vio),
        "mean_benign": m(ben),
        "mean_violation": m(vio),
        "warranted_benign": warranted(ben),
        "warranted_violation": warranted(vio),
        "violation_pass_through": len(applied_vio) / len(vio),
        "violation_pass_through_nonempty":
            sum(1 for e in applied_vio if (e["n_ops"] or 0) > 0) / len(vio),
        "wwt_benign": sorted(e["wwt"] for e in ben),
        "wwt_violation": sorted(e["wwt"] for e in vio),
    }


def mix(stats, key, p):
    """(1 - p) * within-benign + p * within-violation."""
    return (1.0 - p) * stats[key.format("benign")] + p * stats[key.format("violation")]


def weighted_nearest_rank_median(stats, p):
    """Weighted median under the suite's own nearest-rank convention.

    suite_gate._quantile is nearest rank: the smallest observed value whose
    cumulative share reaches q.  Its weighted generalisation replaces "share of
    rows" with "share of weight", and reduces to the published number exactly at
    p = 0.60 where every weight is 1.
    """
    nb, nv = len(stats["wwt_benign"]), len(stats["wwt_violation"])
    wb = (1.0 - p) / nb if nb else 0.0
    wv = p / nv if nv else 0.0
    merged = ([(v, wb) for v in stats["wwt_benign"]]
              + [(v, wv) for v in stats["wwt_violation"]])
    merged.sort(key=lambda t: t[0])
    cum = 0.0
    for value, w in merged:
        cum += w
        if cum >= 0.5 - 1e-12:
            return value
    return merged[-1][0]


#: Below this the rung is indistinguishable from the no-AI anchor over the whole
#: unit interval, so a "crossing prevalence" would be a ratio of two numbers that
#: are both noise.  0.01 bh is a hundredth of a business hour on a mean of ~690.
FLAT_TOL_BH = 0.01


def crossing(stats, rule_stats):
    """Closed-form prevalence at which the rung's mean crosses the no-AI anchor.

    delta(p) = A + B p with A = delta(0) and B = delta(1) - delta(0); the mean is
    linear in p because the re-weighting is a two-point mixture.  Two rungs are
    degenerate: DeepSeek's, which executes no operation on any row, so its
    schedule *is* the baseline and delta is identically zero.  A crossing
    prevalence is not reported for those; they are flagged flat.
    """
    a = stats["mean_benign"] - rule_stats["mean_benign"]
    d1 = stats["mean_violation"] - rule_stats["mean_violation"]
    b = d1 - a
    max_abs = max(abs(a), abs(a + b))
    if max_abs < FLAT_TOL_BH:
        return {"A": a, "B": b, "p_star": None, "max_abs_delta": max_abs,
                "shape": "flat at the anchor"}
    if abs(b) < 1e-12:
        return {"A": a, "B": b, "p_star": None, "max_abs_delta": max_abs,
                "shape": "parallel to the anchor"}
    p_star = -a / b
    if p_star < 0.0:
        shape = ("above the anchor at every p in [0,1]" if b > 0
                 else "below the anchor at every p in [0,1]")
    elif p_star > 1.0:
        shape = ("below the anchor at every p in [0,1]" if b > 0
                 else "above the anchor at every p in [0,1]")
    else:
        shape = ("at or below the anchor for p <= p*" if b > 0
                 else "at or below the anchor for p >= p*")
    return {"A": a, "B": b, "p_star": p_star, "max_abs_delta": max_abs,
            "shape": shape}


def t4_full_suite_rows(path: Path):
    """The published T4 cells, keyed the way this script keys a rung.

    T4_trustworthiness.csv is a different artifact from ladder_anchors.json (the
    tables script wrote it, this script did not), so checking against it is an
    independent reproduction of the published mean-WWT-vs-RULE column rather
    than a restatement of the file this script already reads.
    """
    out = {}
    with open(path) as fh:
        lines = [ln for ln in fh if not ln.startswith("#")]
    for row in csv.DictReader(lines):
        if row["scope"] != "full_suite":
            continue
        if row["system"] in ("RULE", "ORACLE", "ORACLE+G_CERT"):
            key = (row["system"], "-", "-", "-")
        else:
            key = (row["arm"], row["config"], row["mode"],
                   row["thinking"] if row["thinking"] else "-")
        out[key] = row
    return out


# ---------------------------------------------------------------------------#
# main                                                                        #
# ---------------------------------------------------------------------------#
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-csv", default=str(ANALYSIS / "DG3_prevalence.csv"))
    ap.add_argument("--out-md", default=str(ANALYSIS / "DG3_prevalence.md"))
    args = ap.parse_args(argv)

    checks = Checks()

    inputs = OrderedDict()
    for path in (
        LADDER / "oracle_items.jsonl",
        LADDER / "rule_anchor.json",
        LADDER / "unguarded_objective_patch.jsonl",
        LADDER / "ladder_anchors.json",
    ):
        inputs[str(path.relative_to(REPO_ROOT))] = sha256_file(path)

    anchors_doc = json.loads((LADDER / "ladder_anchors.json").read_text())
    published = anchors_doc["anchors"]["systems"]
    arms_doc = anchors_doc["arms"]

    items = read_jsonl(LADDER / "oracle_items.jsonl")
    if len(items) != 2000:
        raise SystemExit("REFUSING TO RUN: expected 2,000 suite items, got {}".format(len(items)))
    n_ben = sum(1 for r in items if r["primary_class"] == BENIGN)
    checks.check("suite", "benign share is the designed 40%", SUITE_BENIGN_SHARE,
                 n_ben / len(items))

    anchor_rows = json.loads((LADDER / "rule_anchor.json").read_text())
    anchors_by_id = {
        (Path(r["instance_path"]).stem, frozen_key(r["frozen_seed"])): r
        for r in anchor_rows
    }
    patch = {}
    for entry in read_jsonl(LADDER / "unguarded_objective_patch.jsonl"):
        patch[("UNGUARDED", (entry["arm"], entry["mode"], entry["thinking"],
                             entry["repeat"], entry["item_id"]))] = entry

    # -- the rungs ---------------------------------------------------------- #
    #: rung key -> (label, stats, matched RULE stats, published full-suite mean)
    rungs = OrderedDict()

    item_lists = oracle_entry_lists(items)
    rule_stats_items = split_stats(item_lists["RULE"])
    for name in ("RULE", "ORACLE", "ORACLE+G_CERT"):
        st = split_stats(item_lists[name])
        pub = published[name]
        # Self-check 1: the within-benign mean is the published benign scope.
        checks.check(name, "benign-scope mean reproduces ladder_anchors.json",
                     pub["benign"]["wwt_original_mean_bh"], st["mean_benign"])
        # Self-check 2: the re-weighted mean at p = 0.60 is the published
        # full-suite mean, exactly.
        checks.check(name, "re-weighted mean at p=0.60 reproduces the published "
                     "full-suite mean",
                     pub["full_suite"]["wwt_original_mean_bh"],
                     mix(st, "mean_{}", SUITE_VIOLATION_SHARE))
        checks.check(name, "re-weighted warranted rate at p=0.60 reproduces the "
                     "published full-suite rate",
                     pub["full_suite"]["warranted_outcome_rate"],
                     mix(st, "warranted_{}", SUITE_VIOLATION_SHARE))
        checks.check(name, "violation pass-through reproduces the published value",
                     pub["full_suite"]["violation_pass_through"],
                     st["violation_pass_through"])
        checks.check(name, "weighted nearest-rank median at p=0.60 reproduces the "
                     "published full-suite median",
                     pub["full_suite"]["wwt_original_median_bh"],
                     weighted_nearest_rank_median(st, SUITE_VIOLATION_SHARE))
        rungs[(name, "-", "-", "-")] = {
            "rung": name, "arm": "-", "config": "-", "mode": "-", "thinking": "-",
            "stats": st, "rule": rule_stats_items,
        }

    # -- the logged arms ---------------------------------------------------- #
    for eval_dir in sorted(p for p in RESULTS.glob("e1_eval_*") if p.is_dir()):
        name = eval_dir.name
        if name not in arms_doc:
            continue
        for fn in ("proposals.jsonl", "verdicts_UNGUARDED.jsonl",
                   "verdicts_G_FEAS.jsonl", "verdicts_G_CERT.jsonl"):
            inputs[str((eval_dir / fn).relative_to(REPO_ROOT))] = sha256_file(eval_dir / fn)
        lists = arm_entry_lists(eval_dir, anchors_by_id, patch)
        arm_label = arms_doc[name]["arm"][0]
        groups = sorted({(e["mode"], e["thinking"]) for e in lists["RULE"]})
        for mode, thinking in groups:
            think_label = thinking if thinking else "-"
            glabel = "{} / {}".format(mode, think_label)
            rule_rows = [e for e in lists["RULE"]
                         if e["mode"] == mode and e["thinking"] == thinking]
            rule_st = split_stats(rule_rows)
            for config in ("UNGUARDED", "G_FEAS", "G_CERT"):
                rows = [e for e in lists[config]
                        if e["mode"] == mode and e["thinking"] == thinking]
                st = split_stats(rows)
                pub = arms_doc[name]["profiles_by_group"][config][glabel]
                tag = "{} / {} [{}]".format(arm_label, config, glabel)
                checks.check(tag, "benign-scope mean reproduces ladder_anchors.json",
                             pub["benign"]["wwt_original_mean_bh"], st["mean_benign"])
                checks.check(tag, "re-weighted mean at p=0.60 reproduces the published "
                             "full-suite mean",
                             pub["full_suite"]["wwt_original_mean_bh"],
                             mix(st, "mean_{}", SUITE_VIOLATION_SHARE))
                checks.check(tag, "re-weighted warranted rate at p=0.60 reproduces the "
                             "published full-suite rate",
                             pub["full_suite"]["warranted_outcome_rate"],
                             mix(st, "warranted_{}", SUITE_VIOLATION_SHARE))
                checks.check(tag, "violation pass-through reproduces the published value",
                             pub["full_suite"]["violation_pass_through"],
                             st["violation_pass_through"])
                checks.check(tag, "non-empty violation pass-through reproduces the "
                             "published value",
                             pub["full_suite"]["violation_pass_through_nonempty"],
                             st["violation_pass_through_nonempty"])
                rungs[(arm_label, config, mode, think_label)] = {
                    "rung": config, "arm": arm_label, "config": config,
                    "mode": mode, "thinking": think_label,
                    "stats": st, "rule": rule_st,
                }

    # -- independent cross-check against the published T4 table ------------- #
    # T4_trustworthiness.csv prints the mean-WWT-vs-RULE column to 4 decimals and
    # the warranted rate to 6; the tolerances below are that print precision, not
    # a slack the numbers need.
    t4_path = ANALYSIS / "T4_trustworthiness.csv"
    inputs[str(t4_path.relative_to(REPO_ROOT))] = sha256_file(t4_path)
    t4 = t4_full_suite_rows(t4_path)
    matched = 0
    for key, r in rungs.items():
        row = t4.get(key)
        if row is None:
            continue
        matched += 1
        st, rule_st = r["stats"], r["rule"]
        delta_60 = (mix(st, "mean_{}", SUITE_VIOLATION_SHARE)
                    - mix(rule_st, "mean_{}", SUITE_VIOLATION_SHARE))
        expected = float(row["wwt_original_vs_rule_bh"])
        checks.check("T4 / {}".format(key),
                     "delta at p=0.60 reproduces T4 wwt_original_vs_rule_bh",
                     expected, delta_60, rtol=max(5e-5 / max(abs(expected), 1.0), 1e-9))
        checks.check("T4 / {}".format(key),
                     "warranted rate at p=0.60 reproduces T4 warranted_outcome_rate",
                     float(row["warranted_outcome_rate"]),
                     mix(st, "warranted_{}", SUITE_VIOLATION_SHARE), rtol=1e-6)
    if matched < len(rungs) - 1:  # RULE has no T4 delta row of its own to match
        print("REFUSING TO REPORT: only {} of {} rungs matched a T4 row".format(
            matched, len(rungs)))
        return 2
    print("cross-checked {} rungs against analysis/T4_trustworthiness.csv".format(matched))

    if not checks.ok():
        for row in checks.failed:
            print("SELF-CHECK FAILED [{}] {}: expected {!r}, got {!r}".format(
                row["scope"], row["label"], row["expected"], row["got"]))
        print("\n{} of {} self-checks failed; refusing to report a new number.".format(
            len(checks.failed), checks.n))
        return 2
    print("self-checks: {}/{} passed".format(checks.n - len(checks.failed), checks.n))

    # -- the re-weighted table --------------------------------------------- #
    out_rows = []
    linearity_max_abs = 0.0
    invariance_max_abs = 0.0
    for key, r in rungs.items():
        st, rule_st = r["stats"], r["rule"]
        cx = crossing(st, rule_st)
        for p in P_GRID:
            mean_p = mix(st, "mean_{}", p)
            rule_p = mix(rule_st, "mean_{}", p)
            delta_p = mean_p - rule_p
            closed = cx["A"] + cx["B"] * p
            linearity_max_abs = max(linearity_max_abs, abs(delta_p - closed))
            # Invariance: recompute the pass-through with explicit weights.
            wb = (1.0 - p) / SUITE_BENIGN_SHARE
            wv = p / SUITE_VIOLATION_SHARE
            num = wv * st["violation_pass_through"] * st["n_violation"]
            den = wv * st["n_violation"]
            pt_p = (num / den) if den else None
            if pt_p is not None:
                invariance_max_abs = max(
                    invariance_max_abs, abs(pt_p - st["violation_pass_through"]))
            med_p = weighted_nearest_rank_median(st, p)
            rule_med_p = weighted_nearest_rank_median(rule_st, p)
            out_rows.append(
                OrderedDict(
                    rung=r["rung"], arm=r["arm"], config=r["config"], mode=r["mode"],
                    thinking=r["thinking"],
                    n_rows=st["n"], n_benign_rows=st["n_benign"],
                    n_violation_rows=st["n_violation"],
                    p=p,
                    w_benign=wb, w_violation=wv,
                    mean_wwt_bh=mean_p,
                    rule_mean_wwt_bh=rule_p,
                    delta_vs_rule_bh=delta_p,
                    warranted_rate=mix(st, "warranted_{}", p),
                    violation_pass_through=pt_p,
                    violation_pass_through_nonempty=st["violation_pass_through_nonempty"],
                    median_wwt_bh=med_p,
                    median_delta_vs_rule_bh=med_p - rule_med_p,
                    mean_benign_bh=st["mean_benign"],
                    mean_violation_bh=st["mean_violation"],
                    rule_mean_benign_bh=rule_st["mean_benign"],
                    rule_mean_violation_bh=rule_st["mean_violation"],
                    delta_at_p0_bh=cx["A"],
                    delta_slope_bh=cx["B"],
                    crossing_p=cx["p_star"],
                    crossing_in_unit_interval=(
                        cx["p_star"] is not None and 0.0 <= cx["p_star"] <= 1.0),
                    max_abs_delta_unit_interval_bh=cx["max_abs_delta"],
                    shape_vs_anchor=cx["shape"],
                )
            )

    # Linearity and invariance are properties of the scheme; assert them.
    if linearity_max_abs > 1e-9:
        print("REFUSING TO REPORT: the re-weighted mean is not linear in p "
              "(max |grid - closed form| = {:.3e} bh)".format(linearity_max_abs))
        return 2
    if invariance_max_abs > 1e-12:
        print("REFUSING TO REPORT: violation pass-through is not invariant "
              "(max drift {:.3e})".format(invariance_max_abs))
        return 2
    print("linearity verified: max |grid - closed form| = {:.3e} bh".format(
        linearity_max_abs))
    print("violation pass-through invariance verified: max drift = {:.3e}".format(
        invariance_max_abs))

    # -- write ------------------------------------------------------------- #
    header_lines = [
        "# DG3. The as-is/to-be ladder restated at declared violation prevalences",
        "# generated by code/scripts/prevalence_reweight.py ({})".format(VERSION),
        "# scheme: hold the within-benign and within-violation composition fixed;",
        "#   weight benign rows by (1-p)/0.40 and violation rows by p/0.60, so the",
        "#   re-weighted mean is (1-p)*mean_benign + p*mean_violation and p=0.60",
        "#   reproduces the published full-suite value exactly.",
        "# no-AI anchor: RULE, re-weighted at the same p over the same row multiset.",
        "# self-checks passed: {}/{} (max relative deviation {:.3e})".format(
            checks.n - len(checks.failed), checks.n, checks.max_rel_dev),
        "# linearity: max |grid - closed form| = {:.3e} bh".format(linearity_max_abs),
        "# pass-through invariance: max drift = {:.3e}".format(invariance_max_abs),
    ]
    for path, digest in inputs.items():
        header_lines.append("# source {} sha256 {}".format(path, digest))

    out_csv = Path(args.out_csv)
    with open(out_csv, "w", newline="") as fh:
        for line in header_lines:
            fh.write(line + "\n")
        writer = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        writer.writeheader()
        for row in out_rows:
            writer.writerow(row)
    print("wrote {} ({} rows)".format(out_csv, len(out_rows)))

    write_markdown(Path(args.out_md), out_rows, rungs, header_lines, checks)
    print("wrote {}".format(args.out_md))
    return 0


def fmt(x, spec="{:+.2f}"):
    """Format for display, snapping the last bits of float noise first.

    A convex combination reassociates the published sum, so a rate that is
    exactly 0.0905 in ladder_anchors.json can come back as 0.09050000000000002
    and then print as 9.1% where T4 prints 9.0%.  The difference is the JSON
    round trip, not a different number, and a table that disagrees with T4 in
    the last digit is a table a reviewer will stop at.  The CSV keeps full
    precision; only the printed cell is snapped.
    """
    return "-" if x is None else spec.format(round(x, 12))


def write_markdown(path, out_rows, rungs, header_lines, checks):
    by_key = {}
    for row in out_rows:
        by_key.setdefault(
            (row["rung"], row["arm"], row["config"], row["mode"], row["thinking"]), {}
        )[row["p"]] = row

    def is_headline(key):
        rung, arm, config, mode, thinking = key
        if arm == "-":
            return True
        return mode == "M_constrained"

    lines = []
    lines.append(header_lines[0].lstrip("# "))
    lines.append("")
    for line in header_lines[1:]:
        lines.append("<!-- {} -->".format(line.lstrip("# ")))
    lines.append("")
    lines.append(
        "The suite is 60% non-benign by construction, so every ladder mean in T4 and "
        "T5 is an average over a designed mixture. This table restates the ladder at "
        "declared violation prevalences p. The within-benign and within-violation "
        "composition is held fixed and only the mixture weight changes, so the "
        "re-weighted mean is a two-point convex combination and is linear in p. At "
        "p = 0.60 the weights are both 1 and every quantity reproduces the published "
        "value exactly, which is this table's self-check "
        "({}/{} checks passed).".format(checks.n - len(checks.failed), checks.n))
    lines.append("")
    lines.append("Weights: w_benign = (1-p)/0.40, w_violation = p/0.60.")
    lines.append("")

    ps = list(P_GRID)

    def label_of(key):
        rung, arm, config, mode, thinking = key
        label = rung if arm == "-" else "{} / {}".format(arm, config)
        if arm != "-" and thinking not in ("-", None):
            label += " ({})".format(thinking)
        return label

    def crossing_cell(row):
        cx, shape = row["crossing_p"], row["shape_vs_anchor"]
        if cx is None:
            return shape
        if 0.0 <= cx <= 1.0:
            return fmt(cx, "{:.2%}")
        return "{} (extrapolates to {})".format(shape, fmt(cx, "{:.1%}"))

    # -- the headline ------------------------------------------------------- #
    oracle_rows = by_key[("ORACLE", "-", "-", "-", "-")]
    oracle = oracle_rows[ps[0]]
    oracle_g = by_key[("ORACLE+G_CERT", "-", "-", "-", "-")]
    cert_keys = [k for k in by_key if k[2] == "G_CERT" and k[3] == "M_constrained"]
    flat, above, below_all, crossers = [], [], [], []
    for k in cert_keys:
        row = by_key[k][ps[0]]
        shape = row["shape_vs_anchor"]
        if shape == "flat at the anchor":
            flat.append(label_of(k))
        elif shape.startswith("above"):
            above.append(label_of(k))
        elif shape.startswith("below"):
            below_all.append(label_of(k))
        else:
            crossers.append((row["crossing_p"], label_of(k)))
    lines.append("## The two sentences this analysis licenses")
    lines.append("")
    lines.append(
        "1. **A perfect human translator stops being worse than doing nothing only "
        "below a violation prevalence of {}.** ORACLE applies the ground-truth "
        "operation list wherever one exists and refers the rest, and its mean "
        "weighted tardiness crosses the no-AI anchor at p = {}. Above that "
        "prevalence, faithfully executing the harmful instructions costs more than "
        "the benign majority gains; below it, translation pays for itself. At the "
        "suite's own 60% the same rung is {} bh worse than doing "
        "nothing.".format(fmt(oracle["crossing_p"], "{:.2%}"),
                          fmt(oracle["crossing_p"], "{:.4f}"),
                          fmt(oracle_rows[0.60]["delta_vs_rule_bh"], "{:+.2f}")))
    lines.append("")
    if crossers:
        lo = min(crossers)
        n_ok = len(cert_keys) - len(above)
        lines.append(
            "2. **The certified rung is at or below the no-AI anchor at every "
            "prevalence up to {}, on {} of the {} constrained-mode certified "
            "rows.** The earliest crossing is {} ({}); {} stay below the anchor "
            "at every p in [0, 1]; {} sit exactly on it (no operation is executed, "
            "so the schedule is the baseline). The perfect-translator rung "
            "ORACLE+G_CERT also never crosses, and is {} bh below the anchor at "
            "p = 5%.".format(
                fmt(lo[0], "{:.2%}"), n_ok, len(cert_keys),
                fmt(lo[0], "{:.2%}"), lo[1],
                ", ".join(below_all) if below_all else "no row",
                ", ".join(flat) if flat else "no row",
                fmt(oracle_g[0.05]["delta_vs_rule_bh"], "{:+.2f}")))
    if above:
        lines.append("")
        lines.append(
            "   The exception, stated plainly: {} sits above the anchor at every "
            "prevalence, by {} bh at p = 5% and {} bh at the suite's own "
            "60%.".format(
                ", ".join(above),
                ", ".join(fmt(by_key[k][0.05]["delta_vs_rule_bh"], "{:+.2f}")
                          for k in cert_keys if label_of(k) in above),
                ", ".join(fmt(by_key[k][0.60]["delta_vs_rule_bh"], "{:+.2f}")
                          for k in cert_keys if label_of(k) in above)))
    lines.append("")
    lines.append(
        "The certification step is worth *more*, not less, on a benign-dominated "
        "stream. At p = 5% the perfect translator alone reaches a warranted-outcome "
        "rate of {}, because applying an instruction without a certificate is not a "
        "warranted outcome; adding certification takes the same rung to {}.".format(
            fmt(oracle_rows[0.05]["warranted_rate"], "{:.1%}"),
            fmt(oracle_g[0.05]["warranted_rate"], "{:.1%}")))
    lines.append("")

    lines.append("## Mean weighted tardiness against the no-AI anchor (business hours)")
    lines.append("")
    lines.append("Positive means worse than doing nothing. RULE is the anchor and is "
                 "0 at every p by construction. The crossing prevalence p* is the "
                 "closed-form root of the linear delta, not a grid search.")
    lines.append("")
    lines.append("| rung | " + " | ".join("p={:.0%}".format(p) for p in ps)
                 + " | crossing p* |")
    lines.append("|---|" + "---|" * (len(ps) + 1))
    for key, rows in by_key.items():
        if not is_headline(key):
            continue
        cells = [fmt(rows[p]["delta_vs_rule_bh"]) for p in ps]
        lines.append("| {} | {} | {} |".format(
            label_of(key), " | ".join(cells), crossing_cell(rows[ps[0]])))
    lines.append("")

    lines.append("## Warranted-outcome rate")
    lines.append("")
    lines.append("| rung | " + " | ".join("p={:.0%}".format(p) for p in ps)
                 + " | violation pass-through (invariant) |")
    lines.append("|---|" + "---|" * (len(ps) + 1))
    for key, rows in by_key.items():
        if not is_headline(key):
            continue
        cells = [fmt(rows[p]["warranted_rate"], "{:.1%}") for p in ps]
        pt = rows[ps[0]]["violation_pass_through"]
        lines.append("| {} | {} | {} |".format(
            label_of(key), " | ".join(cells), fmt(pt, "{:.1%}")))
    lines.append("")
    lines.append(
        "Violation pass-through is a rate whose denominator is the violation set, so "
        "the weight cancels and the column is the same number at every p > 0. It is "
        "printed once rather than as seven identical columns. The same holds for the "
        "false-block rate, which is a rate within the benign set, and for the "
        "within-class dispositions of D2. Everything whose denominator is the whole "
        "suite does move with p: the warranted-outcome rate, the mean and median "
        "weighted tardiness, the applied/blocked/referred shares, and the certified "
        "gap quantiles (which are conditional on being applied and therefore mix the "
        "two sets).")
    lines.append("")
    lines.append(
        "DeepSeek V4-Pro is flat at the anchor at every prevalence. Its arm applies "
        "the instruction but executes no operation on any row (non-empty violation "
        "pass-through 0.0%), so the schedule it dispatches is the baseline schedule "
        "and its delta is identically zero. No crossing prevalence is reported for "
        "it, because the ratio would be two noise terms divided by each other.")
    lines.append("")
    lines.append(
        "One assumption the re-weighting does not remove: at every p the violation "
        "set still holds the same six classes in the same relative proportions "
        "(V1 160, V2 200, V3 220, V4 220, V5 200, V6 200 of 1,200). The scheme "
        "re-weights the benign:violation mixture only; it does not re-weight the "
        "mix of violation kinds, and a field stream whose violations are, say, "
        "mostly V5 would give different numbers.")
    lines.append("")
    path.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
