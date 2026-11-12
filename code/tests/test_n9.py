"""N9: the precedence-aware CP-SAT model and the held-out V3 builder.

The toy instance has two trades, three technicians and eight orders, all on
quarter-hour data, so the rounded-down grid is exact and the model's optimum
must equal the continuous optimum found by enumeration.
"""

from __future__ import annotations

import itertools
import os
import sys
from pathlib import Path

import pytest

from micro import make_instance, order

from l1oracle import cpsat_prec as cp

WORKERS = int(os.environ.get("N9_TEST_WORKERS", "4"))

TOY_ORDERS = (
    # id, trade, p, release, due, priority (weight from the class)
    ("A1", "D20", 3.0, 0.0, 3.0, 2),
    ("A2", "D20", 2.0, 0.0, 2.0, 1),
    ("A3", "D20", 4.0, 1.0, 5.0, 3),
    ("A4", "D20", 1.0, 2.0, 3.0, 1),
    ("A5", "D20", 2.0, 6.0, 8.0, 2),
    ("B1", "D30", 2.0, 0.0, 2.0, 1),
    ("B2", "D30", 3.0, 1.0, 4.0, 2),
    ("B3", "D30", 1.5, 4.0, 5.5, 1),
)


def toy():
    orders = [order(i, t, p, r, pr, due_bh=d) for i, t, p, r, d, pr in TOY_ORDERS]
    return make_instance(orders, [("t1", "D20"), ("t2", "D20"), ("t3", "D30")], "toy")


def _earliest(inst, seqs, edges):
    """Earliest starts for fixed technician sequences under start_a <= start_b."""
    by = {wo["id"]: wo for wo in inst["work_orders"]}
    prev = {}
    for seq in seqs.values():
        for a, b in zip(seq, seq[1:]):
            prev[b] = a
    s = {o: float(by[o]["release_bh"]) for o in by}
    for _ in range(4 * len(by) + 4):
        changed = False
        for o in by:
            lb = float(by[o]["release_bh"])
            if o in prev:
                lb = max(lb, s[prev[o]] + float(by[prev[o]]["p_bh"]))
            for a, b in edges:
                if b == o:
                    lb = max(lb, s[a])
            if lb > s[o] + 1e-12:
                s[o] = lb
                changed = True
        if not changed:
            return s
    return None  # a sequence contradicts a start relation


def enumerate_opt(inst, edges=()):
    """Minimum weighted tardiness over every assignment and sequence."""
    by = {wo["id"]: wo for wo in inst["work_orders"]}
    techs = {}
    for t in inst["technicians"]:
        techs.setdefault(t["trade"], []).append(t["id"])
    per_trade = []
    for trade, tids in sorted(techs.items()):
        oids = sorted(o for o in by if by[o]["trade"] == trade)
        options = []
        for assign in itertools.product(range(len(tids)), repeat=len(oids)):
            groups = [[o for o, k in zip(oids, assign) if k == u] for u in range(len(tids))]
            for perms in itertools.product(*[itertools.permutations(g) for g in groups]):
                options.append({tids[u]: list(perms[u]) for u in range(len(tids))})
        per_trade.append(options)
    best = None
    for combo in itertools.product(*per_trade):
        seqs = {}
        for c in combo:
            seqs.update(c)
        s = _earliest(inst, seqs, edges)
        if s is None:
            continue
        val = sum(float(by[o]["weight"]) * max(0.0, s[o] + float(by[o]["p_bh"]) - float(by[o]["due_bh"]))
                  for o in by)
        if best is None or val < best - 1e-12:
            best = val
    return best


EDGES = (("A5", "A2"), ("B3", "A4"))


def test_precedence_optimum_matches_enumeration():
    inst = toy()
    want = enumerate_opt(inst, EDGES)
    cons = cp.Constraints(precedence=EDGES)
    res = cp.solve(inst, cons, time_limit_s=20, workers=WORKERS)
    assert res["status"] == "OPTIMAL"
    assert res["bound_bh"] == pytest.approx(want, abs=1e-9)
    assert res["incumbent_obj_bh"] == pytest.approx(want, abs=1e-9)
    assert cp.check_constraints(inst, res["schedule"], cons) == []
    # The edges bind: the unconstrained optimum is strictly lower.
    assert enumerate_opt(inst) < want - 1e-9


def test_no_edge_bound_equals_y1_model():
    from l1guard import tier1

    inst = toy()
    mine = cp.solve(inst, cp.Constraints(), time_limit_s=20, workers=WORKERS)
    y1 = tier1._cpsat().solve(inst, time_limit_s=20, workers=WORKERS)
    assert mine["status"] == "OPTIMAL" and y1["status"] == "OPTIMAL"
    assert mine["bound_bh"] == pytest.approx(y1["best_bound_bh"], abs=1e-9)
    assert mine["grid_obj_bh"] == pytest.approx(y1["objective_bh"], abs=1e-9)
    assert mine["bound_bh"] == pytest.approx(enumerate_opt(inst), abs=1e-9)


def test_cross_trade_edge_couples_trades():
    inst = toy()
    cons = cp.Constraints(precedence=(("B3", "A4"),))
    comps = cp.trade_components(inst, cons)
    assert comps == [("D20", "D30")]
    joint = cp.solve(cp.sub_instance(inst, comps[0]), cons, time_limit_s=20, workers=WORKERS)
    assert joint["status"] == "OPTIMAL"
    want = enumerate_opt(inst, cons.precedence)
    assert joint["bound_bh"] == pytest.approx(want, abs=1e-9)
    # Splitting the coupled pair is refused, not silently relaxed.
    with pytest.raises(ValueError):
        cp.solve(cp.sub_instance(inst, ("D20",)), cons, time_limit_s=5, workers=WORKERS)
    # A same-trade edge leaves the other trade out of the component.
    assert cp.trade_components(inst, cp.Constraints(precedence=(("A5", "A2"),))) == [("D20",)]


def test_frozen_and_batch_semantics():
    inst = toy()
    cons = cp.Constraints(frozen=(("A2", "t2", 1.0),), batches=(("B2", "B3"),))
    res = cp.solve(inst, cons, time_limit_s=20, workers=WORKERS)
    assert res["status"] == "OPTIMAL"
    assert cp.check_constraints(inst, res["schedule"], cons) == []
    a2 = [a for a in res["schedule"]["assignments"] if a["wo"] == "A2"][0]
    assert a2["tech"] == "t2" and a2["start_bh"] == 1.0
    free = cp.solve(inst, cp.Constraints(), time_limit_s=20, workers=WORKERS)
    assert res["bound_bh"] >= free["bound_bh"] - 1e-9


def test_rounded_down_bound_is_valid_off_grid():
    """Off-grid data: the bound stays at or below a continuous feasible schedule."""
    orders = [order("X1", "D20", 1.237, 0.013, 1, due_bh=1.111),
              order("X2", "D20", 0.991, 0.0, 2, due_bh=0.5),
              order("X3", "D20", 2.003, 0.507, 1, due_bh=2.2)]
    inst = make_instance(orders, [("t1", "D20")], "offgrid")
    cons = cp.Constraints(precedence=(("X3", "X1"),))
    res = cp.solve(inst, cons, time_limit_s=10, workers=WORKERS)
    assert res["status"] == "OPTIMAL"
    assert res["bound_bh"] <= res["incumbent_obj_bh"] + 1e-9
    assert res["bound_bh"] <= enumerate_opt(inst, cons.precedence) + 1e-9


def test_heldout_builder_is_deterministic(tmp_path):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import build_suite_heldout as bh

    a = bh.build(scale=0.02, out_path=tmp_path / "a.jsonl")
    b = bh.build(scale=0.02, out_path=tmp_path / "b.jsonl")
    assert a["sha256"] == b["sha256"]
    assert a["n_items"] == b["n_items"] > 0
    assert (tmp_path / "a.jsonl").read_bytes() == (tmp_path / "b.jsonl").read_bytes()
