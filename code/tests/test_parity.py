"""Parity: a zero-operation adjustment must reproduce the Y1 dispatcher exactly.

This is the fast in-test check over a few real instances per cell.  The full
gate (>= 200 instances, both rules, printed counts) is
``code/scripts/run_parity.py``; its output is recorded in
``reports/adapter_build.md``.
"""

from __future__ import annotations

import pytest

from l1adapter import apply_operations, dispatch, evaluate, instances

CELLS = [
    (9, "storm2", None),
    (10, "storm2", None),
    (10, "replay", 150),
    (5, "replay", 150),
]
RULES = ["atc", "edd"]
PER_CELL = 3


def _paths():
    out = []
    for campus, track, size in CELLS:
        found = instances.list_instances(campus, track, size)
        assert found, "no instances for {}/{}/{}".format(campus, track, size)
        out.extend(found[:PER_CELL])
    return out


@pytest.mark.parametrize("path", _paths(), ids=lambda p: p.stem)
@pytest.mark.parametrize("rule", RULES)
def test_zero_op_adjusted_dispatch_matches_fmwos(path, rule):
    inst = instances.load_instance(path)
    base = dispatch.dispatch_baseline(inst, rule, 0)
    adj = apply_operations(inst, [])
    got = dispatch.dispatch_adjusted(adj, rule, 0)

    assert dispatch.canonical_schedule(got) == dispatch.canonical_schedule(base)
    assert evaluate.wwt(inst, got) == evaluate.wwt(inst, base)
    assert evaluate.validate(adj, got)["feasible"]


@pytest.mark.parametrize("rule", ["wspt", "pfifo", "mor", "random"])
def test_parity_holds_for_the_other_rules_too(rule):
    path = instances.list_instances(9, "storm2")[0]
    inst = instances.load_instance(path)
    base = dispatch.dispatch_baseline(inst, rule, 7)
    got = dispatch.dispatch_adjusted(apply_operations(inst, []), rule, 7)
    assert dispatch.canonical_schedule(got) == dispatch.canonical_schedule(base)


def test_field_only_operations_still_take_the_unconstrained_path():
    """set_priority / reassign_window change fields, never dispatch constraints."""
    from l1adapter import ops

    path = instances.list_instances(10, "replay", 150)[0]
    inst = instances.load_instance(path)
    first = inst["work_orders"][0]["id"]
    proposal = {
        "operations": [
            {"op": "set_priority", "order_id": first, "priority_class": 1},
            {"op": "reassign_window", "order_id": first, "release_shift_bh": 2.0},
        ]
    }
    adj = apply_operations(inst, ops.parse_operations(proposal))
    assert not adj.is_constrained
    got = dispatch.dispatch_adjusted(adj, "atc", 0)
    # identical to dispatching the adjusted instance through Y1 directly
    ref = dispatch.dispatch_baseline(adj.instance, "atc", 0)
    assert dispatch.canonical_schedule(got) == dispatch.canonical_schedule(ref)
    assert evaluate.validate(adj, got)["feasible"]
