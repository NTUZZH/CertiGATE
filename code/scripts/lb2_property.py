#!/usr/bin/env python
"""Property suite for the Tier 2 bound: it must never exceed what is achievable.

The certificate's soundness rests on one inequality: the bound is at or below
the optimum of the instance it is computed on.  The optimum is not known in
general, so the suite checks the two things that imply a violation of it:

1. ``lb2 <= WWT`` for every schedule any dispatching rule produces, on the base
   instance and on an adjusted one (a realized schedule is feasible, so its
   objective is at or above the optimum);
2. ``lb2 <= objective`` for every instance CP-SAT solves, and ``lb2 == 0``
   wherever CP-SAT proves a zero-tardiness optimum.

It also reports what the certificate needs to be *useful*: the wall time of the
bound, and how it compares with the solver's bound at a per-proposal budget.

Run (about seven minutes on 300 instances)::

    python scripts/lb2_property.py --per-cell 75 --cpsat-per-cell 10
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("MKL_NUM_THREADS", "4")

from l1adapter import apply, dispatch, evaluate, instances  # noqa: E402
from l1guard.lb2 import lb2_detail  # noqa: E402
from l1guard.tier1 import tier1_certificate  # noqa: E402

CELLS = [
    (9, "storm2", None),
    (10, "storm2", None),
    (10, "replay", "150"),
    (9, "replay", "400"),
]

TOL = 1e-6


def cell_name(campus, track, size):
    return "c{:02d}/{}{}".format(campus, track, "" if size is None else "/" + size)


def deterministic_proposal(inst):
    """A small, always-applicable proposal built from the instance itself."""
    orders = inst["work_orders"]
    ops = [{"op": "set_priority", "order_id": orders[0]["id"], "priority_class": 1}]
    if len(orders) > 1:
        ops.append(
            {"op": "reassign_window", "order_id": orders[1]["id"], "release_shift_bh": 8.0}
        )
    if len(orders) > 2:
        ops.append(
            {"op": "pin_next", "order_id": orders[2]["id"], "trade": orders[2]["trade"]}
        )
    return {"operations": ops}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-cell", type=int, default=75)
    ap.add_argument("--cpsat-per-cell", type=int, default=10)
    ap.add_argument("--cpsat-budget", type=float, default=5.0)
    ap.add_argument("--rules", default="atc,edd,wspt,pfifo,mor")
    args = ap.parse_args()
    rules = [r for r in args.rules.split(",") if r]

    violations = []
    n_instances = 0
    n_rule_checks = 0
    n_adjusted_checks = 0
    n_cpsat_checks = 0
    n_zero_optima = 0
    walls = []
    rows = []

    for campus, track, size in CELLS:
        paths = instances.list_instances(campus, track, size)[: args.per_cell]
        cell = cell_name(campus, track, size)
        cell_walls = []
        ratios = []
        tier_rows = []
        for k, path in enumerate(paths):
            inst = instances.load_instance(path)
            n_instances += 1
            detail = lb2_detail(inst)
            lb = detail["lb_bh"]
            walls.append(detail["wall_ms"])
            cell_walls.append(detail["wall_ms"])
            if lb < 0.0:
                violations.append((path.stem, "negative bound", lb))

            best = None
            for rule in rules:
                sched = dispatch.dispatch_baseline(inst, rule, seed=0)
                realized = evaluate.wwt(inst, sched)
                n_rule_checks += 1
                if lb > realized + TOL:
                    violations.append((path.stem, "lb2 > WWT[{}]".format(rule), lb, realized))
                best = realized if best is None else min(best, realized)
            if best is not None and best > 0:
                ratios.append(lb / best)

            adj = apply.apply_proposal(inst, deterministic_proposal(inst))
            sched = dispatch.dispatch_adjusted(adj, rule="atc", seed=0)
            adj_lb = lb2_detail(adj.instance)["lb_bh"]
            adj_wwt = evaluate.wwt(adj.instance, sched)
            n_adjusted_checks += 1
            if adj_lb > adj_wwt + TOL:
                violations.append((path.stem, "lb2(adjusted) > WWT(adjusted)", adj_lb, adj_wwt))

            if k < args.cpsat_per_cell:
                rec = tier1_certificate(inst, budget_s=args.cpsat_budget, workers=4)
                if rec["objective_bh"] is not None:
                    n_cpsat_checks += 1
                    if lb > rec["objective_bh"] + TOL:
                        violations.append(
                            (path.stem, "lb2 > cpsat objective", lb, rec["objective_bh"])
                        )
                    if rec["objective_bh"] == 0.0:
                        n_zero_optima += 1
                        if lb != 0.0:
                            violations.append((path.stem, "lb2 != 0 at a zero optimum", lb))
                tier_rows.append((lb, rec["lb_bh"], rec["status"], detail["wall_ms"],
                                  rec["wall_ms"]))
            print(
                "  {:<28s} lb2={:12.4f}  {:.3f} ms".format(path.stem, lb, detail["wall_ms"]),
                flush=True,
            )

        rows.append(
            {
                "cell": cell,
                "n": len(paths),
                "lb_wall_median_ms": median(cell_walls) if cell_walls else float("nan"),
                "lb_wall_max_ms": max(cell_walls) if cell_walls else float("nan"),
                "ratio_median": median(ratios) if ratios else float("nan"),
                "tier": tier_rows,
            }
        )

    print("\n" + "=" * 100)
    print("LB2 PROPERTY SUITE")
    print("=" * 100)
    print(
        "instances checked            : {}\n"
        "rule-schedule comparisons    : {} ({} rules per instance)\n"
        "adjusted-instance comparisons: {}\n"
        "cpsat comparisons            : {} (budget {:.0f} s, of which {} proved a zero "
        "optimum)\n"
        "VIOLATIONS                   : {}".format(
            n_instances,
            n_rule_checks,
            len(rules),
            n_adjusted_checks,
            n_cpsat_checks,
            args.cpsat_budget,
            n_zero_optima,
            len(violations),
        )
    )
    for v in violations[:20]:
        print("   !", v)

    print("\nper cell")
    print(
        "{:<18s} {:>5s} {:>14s} {:>12s} {:>14s}".format(
            "cell", "n", "lb2 med (ms)", "lb2 max ms", "lb2/best rule"
        )
    )
    for row in rows:
        print(
            "{:<18s} {:>5d} {:>14.3f} {:>12.3f} {:>14.3f}".format(
                row["cell"],
                row["n"],
                row["lb_wall_median_ms"],
                row["lb_wall_max_ms"],
                row["ratio_median"],
            )
        )

    print("\ntier preview (the {} solver-compared instances per cell)".format(
        args.cpsat_per_cell))
    print(
        "{:<18s} {:>10s} {:>14s} {:>16s} {:>14s}".format(
            "cell", "lb2>cpsat", "median ratio", "cpsat status", "cpsat wall ms"
        )
    )
    for row in rows:
        tier = row["tier"]
        if not tier:
            continue
        wins = sum(1 for lb2v, lb1v, _s, _w2, _w1 in tier if lb2v > lb1v + TOL)
        ratios = [
            lb2v / lb1v for lb2v, lb1v, _s, _w2, _w1 in tier if lb1v > TOL
        ]
        statuses = {}
        for _lb2v, _lb1v, s, _w2, _w1 in tier:
            statuses[s] = statuses.get(s, 0) + 1
        print(
            "{:<18s} {:>4d}/{:<5d} {:>14s} {:>16s} {:>14.0f}".format(
                row["cell"],
                wins,
                len(tier),
                "{:.3f}".format(median(ratios)) if ratios else "n/a (bound 0)",
                ",".join("{}:{}".format(k, v) for k, v in sorted(statuses.items())),
                median([w1 for *_x, w1 in tier]),
            )
        )

    if walls:
        ordered = sorted(walls)
        print(
            "\nlb2 wall time over {} calls: min {:.3f} ms, median {:.3f} ms, "
            "p95 {:.3f} ms, max {:.3f} ms".format(
                len(walls),
                ordered[0],
                median(ordered),
                ordered[int(0.95 * (len(ordered) - 1))],
                ordered[-1],
            )
        )
    print("\nGATE: {}".format("PASS" if not violations else "FAIL"))
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
