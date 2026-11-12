"""Same inputs and seed twice -> byte-identical schedule JSON."""

from __future__ import annotations

import json

from l1adapter import apply_operations, dispatch, instances, ops, state
from micro import make_instance, order


def _constrained(inst, baseline):
    proposal = {
        "operations": [
            {"op": "batch", "building_id": "B1", "trade": "D20"},
            {"op": "pin_next", "order_id": "X", "trade": "D20"},
            {"op": "reorder", "order_id": "Y", "relation": "before", "ref_order_id": "Z"},
            {"op": "set_priority", "order_id": "Z", "priority_class": 1},
            {"op": "reassign_window", "order_id": "Y", "release_shift_bh": 1.0},
            {"op": "freeze", "order_id": "F"},
        ]
    }
    return apply_operations(
        inst, ops.parse_operations(proposal), baseline_schedule=baseline
    )


def build():
    inst = make_instance(
        [
            order("P", "D20", 1.0, due_bh=9.0, building="B1"),
            order("Q", "D20", 1.5, due_bh=7.0, building="B1"),
            order("R", "D20", 0.5, due_bh=8.0, building="B1"),
            order("X", "D20", 2.0, due_bh=6.0, building="B2"),
            order("Y", "D20", 1.0, due_bh=4.0, building="B2"),
            order("Z", "D20", 1.0, due_bh=2.0, building="B3"),
            order("F", "D20", 1.0, due_bh=3.0, building="B3"),
        ],
        [("T0", "D20"), ("T1", "D20")],
    )
    return inst, dispatch.dispatch_baseline(inst, "atc", 0)


def test_repeated_baseline_dispatch_is_byte_identical():
    path = instances.list_instances(9, "storm2")[0]
    inst = instances.load_instance(path)
    a = dispatch.canonical_schedule_json(dispatch.dispatch_baseline(inst, "atc", 0))
    b = dispatch.canonical_schedule_json(dispatch.dispatch_baseline(inst, "atc", 0))
    assert a == b


def test_repeated_adjusted_dispatch_is_byte_identical():
    inst, baseline = build()
    adj1 = _constrained(inst, baseline)
    adj2 = _constrained(inst, baseline)
    a = dispatch.canonical_schedule_json(dispatch.dispatch_adjusted(adj1, "atc", 0))
    b = dispatch.canonical_schedule_json(dispatch.dispatch_adjusted(adj2, "atc", 0))
    assert a == b
    assert json.loads(a)["decisions"] == len(inst["work_orders"])


def test_repeated_adjusted_dispatch_is_byte_identical_on_a_real_instance():
    path = instances.list_instances(10, "replay", 150)[0]
    inst = instances.load_instance(path)
    baseline = dispatch.dispatch_baseline(inst, "atc", 0)
    wo = inst["work_orders"]
    building = next(w["building"] for w in wo if w["building"] is not None)
    trade = next(w["trade"] for w in wo if w["building"] == building)
    proposal = {
        "operations": [
            {"op": "set_priority", "order_id": wo[0]["id"], "priority_class": 1},
            {"op": "pin_next", "order_id": wo[1]["id"], "trade": wo[1]["trade"]},
            {"op": "reorder", "order_id": wo[2]["id"], "relation": "before",
             "ref_order_id": wo[3]["id"]},
            {"op": "reassign_window", "order_id": wo[4]["id"], "release_shift_bh": 8.0},
            {"op": "freeze", "order_id": wo[5]["id"]},
            {"op": "batch", "building_id": building, "trade": trade},
        ]
    }
    runs = []
    for _ in range(2):
        adj = apply_operations(
            inst, ops.parse_operations(proposal), baseline_schedule=baseline
        )
        runs.append(dispatch.canonical_schedule_json(dispatch.dispatch_adjusted(adj, "atc", 0)))
    assert runs[0] == runs[1]

    slices = [json.dumps(state.state_slice(inst, top_k=5), sort_keys=True) for _ in range(2)]
    assert slices[0] == slices[1]


def test_the_random_rule_is_seed_deterministic():
    inst, _ = build()
    adj = apply_operations(inst, [])
    a = dispatch.canonical_schedule_json(dispatch.dispatch_adjusted(adj, "random", 3))
    b = dispatch.canonical_schedule_json(dispatch.dispatch_adjusted(adj, "random", 3))
    c = dispatch.canonical_schedule_json(dispatch.dispatch_adjusted(adj, "random", 4))
    assert a == b and a != c


def test_state_slice_shape():
    inst, _ = build()
    sl = state.state_slice(inst, top_k=3)
    assert sl["n_work_orders"] == 7 and sl["n_technicians"] == 2
    assert [r["trade"] for r in sl["trades"]] == ["D20"]
    assert sl["trades"][0]["n_technicians"] == 2
    assert [o["id"] for o in sl["top_orders"]] == ["Z", "F", "Y"]
    assert set(sl["top_orders"][0]) == {
        "id", "trade", "p_bh", "release_bh", "due_bh", "priority", "building"
    }
