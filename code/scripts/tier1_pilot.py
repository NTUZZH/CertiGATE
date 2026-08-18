#!/usr/bin/env python
"""Solve-time pilot: what does a per-proposal CP-SAT budget actually buy?

The Tier 1 certificate is only as good as the bound CP-SAT can prove inside a
per-proposal time budget.  This script measures that, per cell and per budget,
and puts the Tier 2 bound next to it on the same instances so the tier-selection
rule can be decided from a table rather than from an assumption.

It does not choose the budget.  It prints the table.

Reported per cell x budget:
  coverage   share of instances with any incumbent (objective_bh is not None)
  bound>0    share with a non-vacuous lower bound
  optimal    share proved optimal
  med gap    median (obj - bound) / max(bound, 1) over instances with an incumbent
  med wall   median wall time of the solve call, including model construction
And, on the same instances:
  lb2>cpsat  share where the analytic bound is the tighter of the two
  med ratio  median lb2 / cpsat-bound where the cpsat bound is non-vacuous
  lb2 wall   median wall time of the analytic bound

Run::

    python scripts/tier1_pilot.py --per-cell 20 --budgets 1,2,5,10 --out results/
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("MKL_NUM_THREADS", "4")

from l1adapter import instances  # noqa: E402
from l1guard.lb2 import lb2_detail  # noqa: E402
from l1guard.tier1 import tier1_certificate  # noqa: E402

CELLS = [
    (9, "storm2", None),
    (10, "storm2", None),
    (10, "replay", "150"),
    (9, "replay", "400"),
]

LAUNCH_QUESTIONS = """\
Before the run (global CLAUDE.md experiment rules; answered in writing):

1. PURPOSE. Which per-proposal CP-SAT budget, if any, produces a Tier 1
   certificate worth having on each cell of the E1 grid?  The number lands in
   the certificate-protocol deliverable (D3, the Tier 1 vs Tier 2 comparison
   table) and fixes `GuardConfig.tier1_budget_s` for every later run.
2. EXPECTED RESULT. The replay cells (150 and 400 orders) should be solved to
   proven optimality inside 1 s, so Tier 1 is informative there.  The storm2
   cells (2.3k and 9.4k orders) are expected to return a vacuous bound of 0.0
   at every budget in this range, which would mean Tier 2 carries the
   certificate wherever the queue is deep.  If storm2 instead produces a useful
   bound at 5 or 10 s, Tier 1 becomes affordable on the primary campus and the
   tier-selection rule changes accordingly.
3. CONTAMINATION. No checkpoint, no model, no partially written result file is
   involved: every solve is a fresh CP-SAT call on an unmodified instance read
   from the Y1 corpus, and the output file is written once at the end.  The
   machine is shared, so wall-clock is reported as INDICATIVE and the load
   context is recorded below; the shares and gaps are contention-independent.
4. DATA ACCURACY. Instances come from `l1adapter.instances.list_instances`,
   sorted, taking the first n of each cell; the cell paths, the file counts and
   the order counts are printed for every row so the selection can be checked.
"""


def cell_name(campus, track, size):
    return "c{:02d}/{}{}".format(campus, track, "" if size is None else "/" + size)


def sh(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
    except Exception as exc:  # pragma: no cover
        return "<unavailable: {}>".format(exc)


def load_context() -> dict:
    return {
        "uptime": sh(["uptime"]),
        "nvidia_smi": sh(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader",
            ]
        ),
        "cores": sh(["nproc", "--all"]),  # --all: nproc alone honours OMP_NUM_THREADS
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-cell", type=int, default=20)
    ap.add_argument("--budgets", default="1,2,5,10")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    budgets = [float(b) for b in args.budgets.split(",") if b]

    print(LAUNCH_QUESTIONS)
    context = load_context()
    print("LOAD CONTEXT AT LAUNCH (timings below are INDICATIVE, not measurements)")
    for k, v in context.items():
        print("  {:<12s} {}".format(k, v))
    print()

    rows = []
    lb2_rows = []
    for campus, track, size in CELLS:
        cell = cell_name(campus, track, size)
        paths = instances.list_instances(campus, track, size)[: args.per_cell]
        print("== {}  ({} instances) ==".format(cell, len(paths)), flush=True)
        for path in paths:
            inst = instances.load_instance(path)
            detail = lb2_detail(inst)
            lb2_rows.append(
                {
                    "cell": cell,
                    "instance": path.stem,
                    "orders": len(inst["work_orders"]),
                    "technicians": len(inst["technicians"]),
                    "lb2_bh": detail["lb_bh"],
                    "lb2_wall_ms": detail["wall_ms"],
                }
            )
            for budget in budgets:
                rec = tier1_certificate(inst, budget_s=budget, workers=args.workers)
                rows.append(
                    {
                        "cell": cell,
                        "instance": path.stem,
                        "orders": len(inst["work_orders"]),
                        "budget_s": budget,
                        "status": rec["status"],
                        "bound_bh": rec["lb_bh"],
                        "objective_bh": rec["objective_bh"],
                        "wall_ms": rec["wall_ms"],
                        "lb2_bh": detail["lb_bh"],
                        "lb2_wall_ms": detail["wall_ms"],
                    }
                )
                print(
                    "  {:<28s} {:>5.0f}s  status={:<9s} bound={:>10.3f} obj={:>12s} "
                    "wall={:>7.0f} ms  lb2={:>10.3f}".format(
                        path.stem,
                        budget,
                        rec["status"],
                        rec["lb_bh"],
                        "None" if rec["objective_bh"] is None else
                        "{:.3f}".format(rec["objective_bh"]),
                        rec["wall_ms"],
                        detail["lb2_bh"] if "lb2_bh" in detail else detail["lb_bh"],
                    ),
                    flush=True,
                )

    # ---------------------------------------------------------------- table -- #
    print("\n" + "=" * 118)
    print("TIER 1 SOLVE-TIME PILOT  (n = {} per cell; wall times INDICATIVE, shared "
          "machine)".format(args.per_cell))
    print("=" * 118)
    header = (
        "{:<18s} {:>7s} {:>8s} {:>9s} {:>9s} {:>9s} {:>10s} {:>11s} {:>10s} {:>10s}".format(
            "cell", "budget", "coverage", "bound>0", "optimal", "med gap", "med wall",
            "lb2>cpsat", "med ratio", "lb2 wall"
        )
    )
    print(header)
    print("-" * len(header))
    summary = []
    for campus, track, size in CELLS:
        cell = cell_name(campus, track, size)
        for budget in budgets:
            sel = [r for r in rows if r["cell"] == cell and r["budget_s"] == budget]
            if not sel:
                continue
            n = len(sel)
            with_obj = [r for r in sel if r["objective_bh"] is not None]
            gaps = [
                (r["objective_bh"] - r["bound_bh"]) / max(r["bound_bh"], 1.0)
                for r in with_obj
            ]
            nonzero_bound = [r for r in sel if r["bound_bh"] > 0.0]
            optimal = [r for r in sel if r["status"] == "OPTIMAL"]
            lb2_wins = [r for r in sel if r["lb2_bh"] > r["bound_bh"] + 1e-9]
            ratios = [r["lb2_bh"] / r["bound_bh"] for r in sel if r["bound_bh"] > 1e-9]
            row = {
                "cell": cell,
                "budget_s": budget,
                "n": n,
                "coverage": len(with_obj) / n,
                "bound_gt_0": len(nonzero_bound) / n,
                "optimal": len(optimal) / n,
                "median_gap": median(gaps) if gaps else None,
                "median_wall_ms": median([r["wall_ms"] for r in sel]),
                "lb2_tighter": len(lb2_wins) / n,
                "median_lb2_over_cpsat": median(ratios) if ratios else None,
                "median_lb2_wall_ms": median([r["lb2_wall_ms"] for r in sel]),
            }
            summary.append(row)
            print(
                "{:<18s} {:>6.0f}s {:>7.0%} {:>9.0%} {:>9.0%} {:>9s} {:>9.0f}ms "
                "{:>11.0%} {:>10s} {:>8.3f}ms".format(
                    cell,
                    budget,
                    row["coverage"],
                    row["bound_gt_0"],
                    row["optimal"],
                    "n/a" if row["median_gap"] is None else "{:.4f}".format(row["median_gap"]),
                    row["median_wall_ms"],
                    row["lb2_tighter"],
                    "n/a" if row["median_lb2_over_cpsat"] is None
                    else "{:.3f}".format(row["median_lb2_over_cpsat"]),
                    row["median_lb2_wall_ms"],
                )
            )

    print("\nlb2 on the same instances (no solver involved)")
    print("{:<18s} {:>6s} {:>12s} {:>14s} {:>14s}".format(
        "cell", "n", "median bh", "median wall ms", "max wall ms"))
    for campus, track, size in CELLS:
        cell = cell_name(campus, track, size)
        sel = [r for r in lb2_rows if r["cell"] == cell]
        if not sel:
            continue
        print(
            "{:<18s} {:>6d} {:>12.3f} {:>14.3f} {:>14.3f}".format(
                cell,
                len(sel),
                median([r["lb2_bh"] for r in sel]),
                median([r["lb2_wall_ms"] for r in sel]),
                max(r["lb2_wall_ms"] for r in sel),
            )
        )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "context": context,
        "per_cell": args.per_cell,
        "budgets": budgets,
        "workers": args.workers,
        "rows": rows,
        "lb2_rows": lb2_rows,
        "summary": summary,
    }
    out_path = out_dir / "tier1_pilot.json"
    out_path.write_text(json.dumps(payload, indent=1, sort_keys=True))
    print("\nraw rows written to {}".format(out_path))
    print("Wall times are INDICATIVE: the machine was shared during this run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
