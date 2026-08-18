#!/usr/bin/env python
"""DG8-B: does the proposer's certified gap equal the ground truth's, item by item?

The manuscript currently compares the ORACLE rung (a perfectly attentive human
translator of the same instruction) with the flagship proposer through two
summary statistics of their certified-gap distributions: a median that agrees to
six decimal places and a coincident maximum
(manuscript/drafts/s6_results.tex:669-681, macros \\ladOracleVThreeGapMedian and
\\ladOpusVThreeGapMedian).  That comparison is estimator-fragile: the agreement
of the medians depends on the nearest-rank convention the pipeline uses
(code/scripts/suite_gate.py:578-585), and a linearly interpolated median does not
coincide.  A far stronger statement is available from the same files, because the
two systems are evaluated on the SAME items: join them per item and count how
often the certified gap is literally the same number.

This script performs that join, for the flagship and for every other arm, so the
manuscript can state the agreement as a measured range rather than as one arm's
coincidence.

Sources (read-only)
-------------------
* ``analysis/ladder/oracle_items.jsonl`` -- one row per suite item, carrying
  ``oracle_gap`` (the certified gap of the ground-truth translation, the value
  the ORACLE rung's profile aggregates: ladder_replay.py:1077-1090) and
  ``oracle_applied``.
* ``results/e1_eval_<arm>/verdicts_G_CERT.jsonl`` -- one row per (arm, mode,
  thinking, repeat, item_id) with ``certificate_gap``.
* ``analysis/ladder/ladder_anchors.json`` and
  ``analysis/T3_guard_value_curve.csv`` -- the published statistics the
  self-check reproduces.

Self-check (runs first; the script exits non-zero if it fails)
--------------------------------------------------------------
The published ORACLE V3 gap median and maximum
(``anchors.per_class.ORACLE.V3``) and the published per-arm V3 gap median, p90
and maximum (``analysis/T3_guard_value_curve.csv``) are recomputed from the two
raw files with the pipeline's own nearest-rank quantile and asserted equal.

Version: l1-dg8-gap-1
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import json
import math
import statistics
import sys
from collections import OrderedDict
from pathlib import Path

VERSION = "l1-dg8-gap-1"

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS = ROOT / "results"
ANALYSIS = ROOT / "analysis"

E1_DIRS = ["qwen14b", "qwen27b", "glm9b", "gpt54mini", "deepseek",
           "sonnet5", "opus5", "sol"]

#: The constrained-mode roster in table order (paper_macros.py CONSTRAINED_ROWS).
CONSTRAINED_ROWS = [
    ("qwen3-14b", "-"), ("qwen3.6-27b-fp8", "-"), ("glm-4-9b", "-"),
    ("openai", "-"), ("deepseek", "non_think"), ("deepseek", "think_high"),
    ("sonnet", "disabled"), ("opus", "default"), ("opus", "disabled"),
    ("sol", "none"),
]
CAPABILITY_ROWS = [r for r in CONSTRAINED_ROWS if r[0] != "deepseek"]
FLAGSHIP = ("opus", "default")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def nearest_rank(values, q):
    """The pipeline's own quantile (code/scripts/suite_gate.py:578-585)."""
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    idx = max(0, math.ceil(q * len(vals)) - 1)
    return vals[min(idx, len(vals) - 1)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-csv", default=str(ANALYSIS / "DG8_gap_agreement.csv"))
    ap.add_argument("--klass", default="V3")
    args = ap.parse_args()
    KLASS = args.klass

    hashes = OrderedDict()

    # ---------------- ORACLE side ----------------------------------------- #
    oracle_path = ANALYSIS / "ladder" / "oracle_items.jsonl"
    hashes[str(oracle_path.relative_to(ROOT))] = sha256(oracle_path)
    oracle = {}
    with oracle_path.open() as fh:
        for line in fh:
            r = json.loads(line)
            oracle[r["item_id"]] = r
    oracle_klass = [r for r in oracle.values() if r["primary_class"] == KLASS]
    oracle_gaps = [r["oracle_gap"] for r in oracle_klass
                   if r["oracle_applied"] and r["oracle_gap"] is not None]

    # ---------------- self-check against ladder_anchors.json --------------- #
    anchors_path = ANALYSIS / "ladder" / "ladder_anchors.json"
    hashes[str(anchors_path.relative_to(ROOT))] = sha256(anchors_path)
    anchors = json.loads(anchors_path.read_text())
    pub = anchors["anchors"]["per_class"]["ORACLE"][KLASS]
    sc = []
    sc.append(("ORACLE {} n".format(KLASS), pub["n"], len(oracle_klass)))
    sc.append(("ORACLE {} certified_gap_median".format(KLASS),
               pub["certified_gap_median"], nearest_rank(oracle_gaps, 0.5)))
    sc.append(("ORACLE {} certified_gap_p90".format(KLASS),
               pub["certified_gap_p90"], nearest_rank(oracle_gaps, 0.9)))
    sc.append(("ORACLE {} certified_gap_max".format(KLASS),
               pub["certified_gap_max"], max(oracle_gaps) if oracle_gaps else None))

    # ---------------- proposer side --------------------------------------- #
    arm_rows = OrderedDict()
    for d in E1_DIRS:
        p = RESULTS / ("e1_eval_" + d) / "verdicts_G_CERT.jsonl"
        hashes[str(p.relative_to(ROOT))] = sha256(p)
        with p.open() as fh:
            for line in fh:
                r = json.loads(line)
                if r["mode"] != "M_constrained":
                    continue
                if r["primary_class"] != KLASS:
                    continue
                key = (r["arm"], r.get("thinking") or "-")
                cert = r.get("certificate") or {}
                arm_rows.setdefault(key, []).append({
                    "item_id": r["item_id"], "repeat": r.get("repeat"),
                    "gap": r.get("certificate_gap"),
                    "obj_bh": cert.get("obj_bh"), "lb_bh": cert.get("lb_bh"),
                    "terminal": r["terminal"],
                })

    # ---------------- self-check against T3 -------------------------------- #
    t3_path = ANALYSIS / "T3_guard_value_curve.csv"
    hashes[str(t3_path.relative_to(ROOT))] = sha256(t3_path)
    with t3_path.open() as fh:
        body = [ln for ln in fh if not ln.startswith("#")]
    t3 = {}
    for rec in csv.DictReader(body):
        t3[(rec["arm"], rec["thinking"])] = rec
    for key in CONSTRAINED_ROWS:
        rec = t3.get(key)
        if rec is None:
            continue
        vals = [r["gap"] for r in arm_rows.get(key, []) if r["gap"] is not None]
        for col, mine in (("v3_gap_median", nearest_rank(vals, 0.5)),
                          ("v3_gap_p90", nearest_rank(vals, 0.9)),
                          ("v3_gap_max", max(vals) if vals else None)):
            want = rec.get(col, "")
            if want == "":
                continue
            sc.append(("T3 {} {} {}".format(key[0], key[1], col),
                       float(want), mine))

    failures = []
    for name, want, got in sc:
        if want is None or got is None:
            if want is not got:
                failures.append((name, want, got))
        elif abs(float(want) - float(got)) > 5e-7:
            failures.append((name, want, got))
    print("SELF-CHECK  {} published statistics recomputed from the raw files; "
          "mismatches = {}".format(len(sc), len(failures)), file=sys.stderr)
    if failures:
        for f in failures:
            print("  MISMATCH {}: published {} vs recomputed {}".format(*f),
                  file=sys.stderr)
        return 1

    # ---------------- the per-item join ------------------------------------ #
    results = OrderedDict()
    for key in CONSTRAINED_ROWS:
        rows = [r for r in arm_rows.get(key, []) if r["gap"] is not None]
        n = len(rows)
        joined = 0
        equal_exact = 0
        equal_1e12 = 0
        equal_obj = 0
        lower = 0
        higher = 0
        diffs = []
        detail = []
        for r in rows:
            o = oracle.get(r["item_id"])
            if o is None or not o["oracle_applied"] or o["oracle_gap"] is None:
                continue
            joined += 1
            og = o["oracle_gap"]
            # The stronger identity: the same executed objective, not merely the
            # same ratio.  ORACLE's executed objective on an applied item is
            # oracle_wwt_adjusted_bh (ladder_replay.py:1077-1090).
            if (r["obj_bh"] is not None
                    and o.get("oracle_wwt_adjusted_bh") is not None
                    and r["obj_bh"] == o["oracle_wwt_adjusted_bh"]):
                equal_obj += 1
            d = r["gap"] - og
            if r["gap"] == og:
                equal_exact += 1
            else:
                rel = abs(d) / max(abs(og), 1e-300)
                if rel <= 1e-12:
                    equal_1e12 += 1
                diffs.append(d)
                detail.append({"item_id": r["item_id"], "repeat": r["repeat"],
                               "arm_gap": r["gap"], "oracle_gap": og,
                               "difference": d})
                if d < 0:
                    lower += 1
                else:
                    higher += 1
        results[key] = {
            "certificates": n,
            "joined_to_an_oracle_gap": joined,
            "identical_to_float_precision": equal_exact,
            "share_identical": (equal_exact / joined) if joined else None,
            "identical_executed_objective": equal_obj,
            "differing": joined - equal_exact,
            "differing_but_within_1e-12_relative": equal_1e12,
            "arm_gap_lower": lower,
            "arm_gap_higher": higher,
            "all_differences_same_direction": (lower == 0 or higher == 0)
                                              if diffs else None,
            "max_abs_difference": max((abs(x) for x in diffs), default=0.0),
            "median_signed_difference_over_differing": (
                statistics.median(diffs) if diffs else None),
            "detail": detail,
        }

    # ---------------- estimator fragility of the published comparison ------ #
    # The manuscript's ORACLE-equals-flagship sentence rests on two summary
    # statistics.  Five standard median conventions are computed for each
    # distribution so it is on the record whether the agreement is an artifact
    # of the pipeline's nearest-rank quantile or survives the estimator.
    import numpy as _np

    flag = [r["gap"] for r in arm_rows.get(FLAGSHIP, []) if r["gap"] is not None]

    def medians(vals):
        arr = _np.asarray(sorted(vals), dtype=float)
        return OrderedDict([
            ("nearest_rank_pipeline", nearest_rank(vals, 0.5)),
            ("linear_numpy_default", float(_np.percentile(arr, 50, method="linear"))),
            ("lower", float(_np.percentile(arr, 50, method="lower"))),
            ("higher", float(_np.percentile(arr, 50, method="higher"))),
            ("midpoint", float(_np.percentile(arr, 50, method="midpoint"))),
            ("statistics_median", statistics.median(sorted(vals))),
        ])

    om, fm = medians(oracle_gaps), medians(flag)
    # Which item carries the coincident maximum on each side.
    o_argmax = max((r for r in oracle_klass
                    if r["oracle_applied"] and r["oracle_gap"] is not None),
                   key=lambda r: r["oracle_gap"])["item_id"]
    f_argmax = max((r for r in arm_rows[FLAGSHIP] if r["gap"] is not None),
                   key=lambda r: r["gap"])["item_id"]

    fragility = OrderedDict()
    fragility["oracle_n"] = len(oracle_gaps)
    fragility["flagship_n"] = len(flag)
    for name in om:
        fragility["oracle_median_" + name] = om[name]
        fragility["flagship_median_" + name] = fm[name]
        fragility["medians_agree_" + name] = (om[name] == fm[name])
    fragility["oracle_max"] = max(oracle_gaps)
    fragility["flagship_max"] = max(flag)
    fragility["max_on_same_item"] = (o_argmax == f_argmax)
    fragility["max_item_oracle"] = o_argmax
    fragility["max_item_flagship"] = f_argmax

    # Item-for-item at repeat 0 only: one flagship certificate per suite item,
    # so the two distributions have the same 220-item support.
    r0 = [r for r in arm_rows[FLAGSHIP] if r["gap"] is not None and r["repeat"] == 0]
    r0_gaps = [r["gap"] for r in r0]
    r0_identical = sum(1 for r in r0
                       if oracle.get(r["item_id"]) is not None
                       and r["gap"] == oracle[r["item_id"]]["oracle_gap"])
    fragility["flagship_repeat0_certificates"] = len(r0)
    fragility["flagship_repeat0_identical_to_oracle"] = r0_identical
    fragility["flagship_repeat0_median_linear"] = float(
        _np.percentile(_np.asarray(sorted(r0_gaps)), 50, method="linear"))

    # ---------------- write the CSV ---------------------------------------- #
    out = Path(args.out_csv)
    stamp = _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    with out.open("w", newline="") as fh:
        fh.write("# DG8-B. Per-item agreement between the ORACLE rung's certified "
                 "gap and each proposer's, class {}\n".format(KLASS))
        fh.write("# generated {} by code/scripts/dg8_gap_agreement.py ({})\n".format(
            stamp, VERSION))
        fh.write("# join key: item_id (the ORACLE rung and every proposer arm are "
                 "evaluated on the same suite items); constrained mode, repeats "
                 "kept separate so every logged certificate is one row\n")
        fh.write("# self-check: {} published statistics (ladder_anchors.json "
                 "per_class.ORACLE.{}, T3_guard_value_curve.csv v3_gap_*) "
                 "recomputed from the raw files, {} mismatches\n".format(
                     len(sc), KLASS, len(failures)))
        for path, h in hashes.items():
            fh.write("# {} sha256 {}\n".format(path, h))
        w = csv.writer(fh)
        w.writerow(["arm", "thinking", "certificates", "joined", "identical",
                    "share_identical", "identical_executed_objective",
                    "differing", "arm_gap_lower",
                    "arm_gap_higher", "same_direction", "max_abs_difference",
                    "in_capability_set"])
        for key, r in results.items():
            w.writerow([key[0], key[1], r["certificates"],
                        r["joined_to_an_oracle_gap"],
                        r["identical_to_float_precision"],
                        "" if r["share_identical"] is None
                        else "{:.6f}".format(r["share_identical"]),
                        r["identical_executed_objective"],
                        r["differing"], r["arm_gap_lower"], r["arm_gap_higher"],
                        r["all_differences_same_direction"],
                        "{:.6g}".format(r["max_abs_difference"]),
                        "yes" if key in CAPABILITY_ROWS else "no"])
        w.writerow([])
        w.writerow(["# estimator fragility of the published median comparison"])
        for k, v in fragility.items():
            w.writerow(["fragility", k, v])
        w.writerow([])
        w.writerow(["# every differing certificate of the flagship "
                    "({} / {})".format(*FLAGSHIP)])
        w.writerow(["item_id", "repeat", "arm_gap", "oracle_gap", "difference"])
        for d in sorted(results[FLAGSHIP]["detail"], key=lambda x: x["item_id"]):
            w.writerow([d["item_id"], d["repeat"], repr(d["arm_gap"]),
                        repr(d["oracle_gap"]), repr(d["difference"])])

    report = {
        "version": VERSION,
        "class": KLASS,
        "self_check": {"statistics_checked": len(sc), "mismatches": len(failures)},
        "oracle_items": len(oracle_klass),
        "per_arm": {"{}/{}".format(*k): {kk: vv for kk, vv in v.items()
                                         if kk != "detail"}
                    for k, v in results.items()},
        "fragility": fragility,
        "flagship_differing_detail": results[FLAGSHIP]["detail"],
    }
    print(json.dumps(report, indent=1, default=str))
    print("wrote {}".format(out), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
