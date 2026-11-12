"""Acceptance gate: parity, determinism and runtime for the L1 adapter.

Parity
    On every instance of the listed cells, a zero-operation adjustment
    dispatched through ``l1adapter.dispatch.dispatch_adjusted`` must produce the
    same schedule (same assignments, same start/end times, same decision count)
    and the same WWT as ``fmwos.pdrs.dispatch``, rule for rule and seed for seed.

Determinism
    The same call twice must produce byte-identical schedule JSON (the measured
    ``wall_seconds`` excluded, since it is a timing measurement, not content).

Runtime
    Wall time of the wrapper against the Y1 baseline on the two storm2 scales.

Usage: python scripts/run_parity.py [--per-cell N] [--seeds 0,1]
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from l1adapter import apply_operations, dispatch, evaluate, instances, ops  # noqa: E402
from l1adapter.errors import CyclicPrecedence  # noqa: E402

CELLS = [
    (9, "storm2", None),
    (10, "storm2", None),
    (10, "replay", 150),
    (5, "replay", 150),
    (9, "replay", 400),
    (12, "storm", 150),
]
RULES = ("atc", "edd")


def parity(per_cell: int, seeds) -> int:
    print("PARITY  (zero-operation adjustment vs fmwos.pdrs.dispatch)")
    print(
        "%-22s %7s %8s %9s %9s %9s"
        % ("cell", "files", "orders", "checks", "identical", "wwt_eq")
    )
    total_checks = total_ok = total_wwt = total_files = 0
    mismatches = []
    for campus, track, size in CELLS:
        paths = instances.list_instances(campus, track, size)[:per_cell]
        n_checks = n_ok = n_wwt = 0
        n_orders = 0
        for path in paths:
            inst = instances.load_instance(path)
            n_orders += len(inst["work_orders"])
            adj = apply_operations(inst, [])
            for rule in RULES:
                for seed in seeds:
                    base = dispatch.dispatch_baseline(inst, rule, seed)
                    got = dispatch.dispatch_adjusted(adj, rule, seed)
                    n_checks += 1
                    if dispatch.canonical_schedule(got) == dispatch.canonical_schedule(base):
                        n_ok += 1
                    elif len(mismatches) < 3:
                        mismatches.append((path.name, rule, seed, base, got))
                    if evaluate.wwt(inst, got) == evaluate.wwt(inst, base):
                        n_wwt += 1
        label = "c%02d/%s%s" % (campus, track, "/%s" % size if size else "")
        print(
            "%-22s %7d %8d %9d %9d %9d"
            % (label, len(paths), n_orders, n_checks, n_ok, n_wwt)
        )
        total_files += len(paths)
        total_checks += n_checks
        total_ok += n_ok
        total_wwt += n_wwt
    print(
        "%-22s %7d %8s %9d %9d %9d"
        % ("TOTAL", total_files, "-", total_checks, total_ok, total_wwt)
    )
    for name, rule, seed, base, got in mismatches:
        print("MISMATCH", name, rule, seed)
        b = {a["wo"]: a for a in base["assignments"]}
        g = {a["wo"]: a for a in got["assignments"]}
        diff = [k for k in b if b[k] != g.get(k)][:5]
        print("  first differing orders:", [(k, b[k], g.get(k)) for k in diff])
    return 0 if (total_ok == total_checks == total_wwt) else 1


def determinism(n: int = 5) -> int:
    print("\nDETERMINISM  (same call twice -> byte-identical schedule JSON)")
    paths = (
        instances.list_instances(9, "storm2")[:n]
        + instances.list_instances(10, "replay", 150)[:n]
    )
    n_ok = 0
    for path in paths:
        inst = instances.load_instance(path)
        baseline = dispatch.dispatch_baseline(inst, "atc", 0)
        wo = inst["work_orders"]
        building = next((w["building"] for w in wo if w["building"] is not None), None)
        blocks = [
            {"op": "set_priority", "order_id": wo[0]["id"], "priority_class": 1},
            {"op": "pin_next", "order_id": wo[1]["id"], "trade": wo[1]["trade"]},
            {"op": "reorder", "order_id": wo[2]["id"], "relation": "before",
             "ref_order_id": wo[3]["id"]},
            {"op": "reassign_window", "order_id": wo[4]["id"], "release_shift_bh": 6.0},
            {"op": "freeze", "order_id": wo[5]["id"]},
        ]
        if building is not None:
            trade = next(w["trade"] for w in wo if w["building"] == building)
            blocks.append({"op": "batch", "building_id": building, "trade": trade})
        runs = []
        for _ in range(2):
            adj = apply_operations(
                inst, ops.parse_operations({"operations": blocks}, strict_schema=True),
                baseline_schedule=baseline,
            )
            runs.append(
                dispatch.canonical_schedule_json(dispatch.dispatch_adjusted(adj, "atc", 0))
            )
        n_ok += int(runs[0] == runs[1])
    print("  %d/%d instances byte-identical over two constrained runs (6 operations each)"
          % (n_ok, len(paths)))
    return 0 if n_ok == len(paths) else 1


def runtime(repeats: int = 5) -> int:
    print("\nRUNTIME  (best of %d, single process, wall seconds)" % repeats)
    print(
        "%-32s %7s %10s %10s %10s %7s"
        % ("instance", "orders", "fmwos", "wrapper0", "wrapper+ops", "ratio")
    )
    for campus in (9, 10):
        path = instances.list_instances(campus, "storm2")[0]
        inst = instances.load_instance(path)
        adj0 = apply_operations(inst, [])
        baseline = dispatch.dispatch_baseline(inst, "atc", 0)
        wo = inst["work_orders"]
        blocks = [
            {"op": "set_priority", "order_id": wo[0]["id"], "priority_class": 1},
            {"op": "pin_next", "order_id": wo[1]["id"], "trade": wo[1]["trade"]},
            {"op": "reorder", "order_id": wo[2]["id"], "relation": "before",
             "ref_order_id": wo[3]["id"]},
            {"op": "reassign_window", "order_id": wo[4]["id"], "release_shift_bh": 6.0},
            {"op": "freeze", "order_id": wo[5]["id"]},
        ]
        adj1 = apply_operations(
            inst, ops.parse_operations({"operations": blocks}), baseline_schedule=baseline
        )

        def timeit(fn):
            out = []
            for _ in range(repeats):
                t = time.perf_counter()
                fn()
                out.append(time.perf_counter() - t)
            return min(out), statistics.median(out)

        base_min, _ = timeit(lambda: dispatch.dispatch_baseline(inst, "atc", 0))
        w0_min, _ = timeit(lambda: dispatch.dispatch_adjusted(adj0, "atc", 0))
        w1_min, _ = timeit(lambda: dispatch.dispatch_adjusted(adj1, "atc", 0))
        print(
            "%-32s %7d %10.4f %10.4f %10.4f %6.2fx"
            % (path.stem, len(wo), base_min, w0_min, w1_min, w0_min / base_min)
        )
    return 0


def refusals() -> int:
    print("\nREFUSALS  (mechanically impossible proposals on a real instance)")
    path = instances.list_instances(10, "replay", 150)[0]
    inst = instances.load_instance(path)
    wo = inst["work_orders"]
    cyc = ops.parse_operations(
        {
            "operations": [
                {"op": "reorder", "order_id": wo[0]["id"], "relation": "before",
                 "ref_order_id": wo[1]["id"]},
                {"op": "reorder", "order_id": wo[1]["id"], "relation": "before",
                 "ref_order_id": wo[0]["id"]},
            ]
        }
    )
    adj = apply_operations(inst, cyc)
    print("  find_cycles() ->", adj.find_cycles())
    try:
        dispatch.dispatch_adjusted(adj, "atc", 0)
    except CyclicPrecedence as exc:
        print("  dispatch_adjusted raised CyclicPrecedence:", exc.cycles)
        return 0
    print("  ERROR: a cyclic proposal was dispatched")
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-cell", type=int, default=100)
    ap.add_argument("--seeds", default="0")
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",")]

    rc = parity(args.per_cell, seeds)
    rc |= determinism()
    rc |= runtime()
    rc |= refusals()
    print("\nGATE:", "PASS" if rc == 0 else "FAIL")
    return rc


if __name__ == "__main__":
    sys.exit(main())
