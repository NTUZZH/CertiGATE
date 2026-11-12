"""Field-level operation semantics and the typed mechanical errors."""

from __future__ import annotations

import copy

import pytest

from l1adapter import SLA_BH, WEIGHT, apply_operations, ops
from l1adapter.errors import (
    DanglingBuildingID,
    DanglingOrderID,
    FrozenWindowConflict,
    MissingBaseline,
    NotFrozen,
    TradeMismatch,
    UnknownTrade,
)
from micro import make_instance, order


def base_instance():
    return make_instance(
        [
            order("A", "D20", 1.0, release_bh=0.0, priority=3, building="B1"),
            order("B", "D20", 2.0, release_bh=1.0, priority=4, building="B1"),
            order("C", "D30", 1.5, release_bh=0.0, priority=2, building="B2"),
        ],
        [("T0", "D20"), ("T1", "D30")],
    )


def op(**kw):
    return ops.parse_operations({"operations": [kw]})[0]


# --------------------------------------------------------------------------- #
# set_priority                                                                 #
# --------------------------------------------------------------------------- #
def test_set_priority_is_a_full_class_shift():
    inst = base_instance()
    adj = apply_operations(inst, [op(op="set_priority", order_id="B", priority_class=1)])
    wo = adj.order("B")
    assert wo["priority"] == 1
    assert wo["weight"] == WEIGHT[1] == 8.0
    assert wo["due_bh"] == pytest.approx(wo["release_bh"] + SLA_BH[1])
    # every other field, and every other order, is untouched
    assert wo["p_bh"] == 2.0 and wo["release_bh"] == 1.0
    assert adj.order("A") == adj.original["work_orders"][0]


def test_apply_never_mutates_the_input_instance():
    inst = base_instance()
    before = copy.deepcopy(inst)
    apply_operations(
        inst,
        [
            op(op="set_priority", order_id="A", priority_class=1),
            op(op="reassign_window", order_id="B", release_shift_bh=5.0),
        ],
    )
    assert inst == before


def test_meta_id_is_not_annotated_so_schedules_stay_comparable():
    inst = base_instance()
    adj = apply_operations(inst, [op(op="set_priority", order_id="A", priority_class=1)])
    assert adj.instance["meta"]["id"] == inst["meta"]["id"]


# --------------------------------------------------------------------------- #
# reassign_window                                                              #
# --------------------------------------------------------------------------- #
def test_reassign_window_moves_release_and_restarts_the_sla_clock():
    inst = base_instance()
    adj = apply_operations(inst, [op(op="reassign_window", order_id="B", release_shift_bh=40.0)])
    wo = adj.order("B")
    assert wo["release_bh"] == pytest.approx(41.0)
    assert wo["due_bh"] == pytest.approx(41.0 + SLA_BH[4])
    assert wo["priority"] == 4 and wo["weight"] == WEIGHT[4]


def test_reassign_window_clips_release_at_zero_and_records_it():
    inst = base_instance()
    adj = apply_operations(inst, [op(op="reassign_window", order_id="B", release_shift_bh=-99.0)])
    assert adj.order("B")["release_bh"] == 0.0
    assert adj.order("B")["due_bh"] == pytest.approx(SLA_BH[4])
    assert "release_clipped_at_zero:B" in adj.notes


def test_operations_apply_in_order_so_the_new_class_sla_is_used():
    inst = base_instance()
    adj = apply_operations(
        inst,
        [
            op(op="set_priority", order_id="B", priority_class=1),
            op(op="reassign_window", order_id="B", release_shift_bh=4.0),
        ],
    )
    wo = adj.order("B")
    assert wo["priority"] == 1
    assert wo["release_bh"] == pytest.approx(5.0)
    assert wo["due_bh"] == pytest.approx(5.0 + SLA_BH[1])


# --------------------------------------------------------------------------- #
# reorder / precedence graph                                                   #
# --------------------------------------------------------------------------- #
def test_before_and_after_produce_the_same_edge():
    inst = base_instance()
    a = apply_operations(inst, [op(op="reorder", order_id="A", relation="before", ref_order_id="C")])
    b = apply_operations(inst, [op(op="reorder", order_id="C", relation="after", ref_order_id="A")])
    assert a.precedence == b.precedence == (("A", "C"),)
    assert a.find_cycles() == []


def test_cycle_detection_catches_a_two_cycle_and_a_self_loop():
    inst = base_instance()
    two = apply_operations(
        inst,
        [
            op(op="reorder", order_id="A", relation="before", ref_order_id="B"),
            op(op="reorder", order_id="B", relation="before", ref_order_id="A"),
        ],
    )
    assert two.find_cycles() == [["A", "B"]]
    assert "precedence_cycle:A,B" in two.notes

    loop = apply_operations(
        inst, [op(op="reorder", order_id="A", relation="before", ref_order_id="A")]
    )
    assert loop.find_cycles() == [["A"]]


def test_long_acyclic_chain_has_no_cycles():
    inst = make_instance(
        [order("W%d" % i, "D20", 1.0) for i in range(6)], [("T0", "D20")]
    )
    chain = [
        op(op="reorder", order_id="W%d" % i, relation="before", ref_order_id="W%d" % (i + 1))
        for i in range(5)
    ]
    assert apply_operations(inst, chain).find_cycles() == []


# --------------------------------------------------------------------------- #
# freeze / unfreeze                                                            #
# --------------------------------------------------------------------------- #
def test_freeze_records_the_baseline_slot():
    inst = base_instance()
    baseline = {
        "assignments": [
            {"wo": "A", "tech": "T0", "start_bh": 0.0, "end_bh": 1.0},
            {"wo": "B", "tech": "T0", "start_bh": 1.0, "end_bh": 3.0},
            {"wo": "C", "tech": "T1", "start_bh": 0.0, "end_bh": 1.5},
        ]
    }
    adj = apply_operations(inst, [op(op="freeze", order_id="B")], baseline_schedule=baseline)
    assert adj.frozen == {"B": {"tech": "T0", "start_bh": 1.0}}


def test_unfreeze_removes_from_the_standing_frozen_set():
    inst = base_instance()
    baseline = {"assignments": [{"wo": "A", "tech": "T0", "start_bh": 0.0, "end_bh": 1.0}]}
    adj = apply_operations(
        inst, [op(op="unfreeze", order_id="A")], frozen_seed=["A"], baseline_schedule=baseline
    )
    assert adj.frozen == {}
    assert not adj.is_constrained


# --------------------------------------------------------------------------- #
# batch groups                                                                 #
# --------------------------------------------------------------------------- #
def test_batch_group_members_are_edd_ordered_after_the_field_edits():
    inst = make_instance(
        [
            order("A", "D20", 1.0, due_bh=9.0, building="B1"),
            order("B", "D20", 1.0, due_bh=7.0, building="B1"),
            order("C", "D20", 1.0, due_bh=8.0, building="B1"),
            order("D", "D30", 1.0, due_bh=1.0, building="B1"),  # other trade
            order("E", "D20", 1.0, due_bh=1.0, building="B2"),  # other building
        ],
        [("T0", "D20"), ("T1", "D30")],
    )
    adj = apply_operations(inst, [op(op="batch", building_id="B1", trade="D20")])
    assert len(adj.batches) == 1
    assert adj.batches[0].members == ("B", "C", "A")

    # a set_priority that moves a due date reorders the chain
    adj2 = apply_operations(
        inst,
        [
            op(op="set_priority", order_id="A", priority_class=1),  # due -> 8.0
            op(op="batch", building_id="B1", trade="D20"),
        ],
    )
    # A's due moves 9.0 -> 8.0, so it passes C (8.0, tie broken by id) but not B (7.0)
    assert adj2.order("A")["due_bh"] == pytest.approx(SLA_BH[1]) == 8.0
    assert adj2.batches[0].members == ("B", "A", "C")


def test_batch_group_with_no_matching_order_is_recorded_not_raised():
    inst = make_instance(
        [order("A", "D20", 1.0, building="B1"), order("C", "D30", 1.0, building="B2")],
        [("T0", "D20"), ("T1", "D30")],
    )
    adj = apply_operations(inst, [op(op="batch", building_id="B1", trade="D30")])
    assert adj.batches == ()
    assert "batch_group_empty:B1/D30" in adj.notes


# --------------------------------------------------------------------------- #
# typed errors                                                                 #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "block",
    [
        {"op": "set_priority", "order_id": "ZZ", "priority_class": 1},
        {"op": "pin_next", "order_id": "ZZ", "trade": "D20"},
        {"op": "reorder", "order_id": "ZZ", "relation": "before", "ref_order_id": "A"},
        {"op": "reorder", "order_id": "A", "relation": "before", "ref_order_id": "ZZ"},
        {"op": "reassign_window", "order_id": "ZZ", "release_shift_bh": 1.0},
        {"op": "freeze", "order_id": "ZZ"},
        {"op": "unfreeze", "order_id": "ZZ"},
    ],
)
def test_dangling_order_id(block):
    with pytest.raises(DanglingOrderID):
        apply_operations(base_instance(), [op(**block)], baseline_schedule={"assignments": []})


def test_dangling_building_id():
    with pytest.raises(DanglingBuildingID):
        apply_operations(base_instance(), [op(op="batch", building_id="NOPE", trade="D20")])


def test_unknown_trade_for_this_instance():
    with pytest.raises(UnknownTrade):
        apply_operations(base_instance(), [op(op="pin_next", order_id="A", trade="E20")])
    with pytest.raises(UnknownTrade):
        apply_operations(base_instance(), [op(op="batch", building_id="B1", trade="E20")])


def test_trade_mismatch_for_pin_next():
    with pytest.raises(TradeMismatch) as exc:
        apply_operations(base_instance(), [op(op="pin_next", order_id="A", trade="D30")])
    assert exc.value.order_trade == "D20" and exc.value.stated_trade == "D30"


def test_not_frozen():
    with pytest.raises(NotFrozen):
        apply_operations(base_instance(), [op(op="unfreeze", order_id="A")])


def test_freeze_plus_window_shift_past_the_pinned_start_is_impossible():
    """The eighth typed error: two operations that cannot both hold."""
    inst = base_instance()
    baseline = {
        "assignments": [
            {"wo": "A", "tech": "T0", "start_bh": 0.0, "end_bh": 1.0},
            {"wo": "B", "tech": "T0", "start_bh": 1.0, "end_bh": 3.0},
            {"wo": "C", "tech": "T1", "start_bh": 0.0, "end_bh": 1.5},
        ]
    }
    # shifting the release earlier keeps the pinned start feasible
    ok = apply_operations(
        inst,
        [op(op="freeze", order_id="B"), op(op="reassign_window", order_id="B", release_shift_bh=-1.0)],
        baseline_schedule=baseline,
    )
    assert ok.frozen["B"]["start_bh"] == 1.0

    with pytest.raises(FrozenWindowConflict) as exc:
        apply_operations(
            inst,
            [
                op(op="freeze", order_id="B"),
                op(op="reassign_window", order_id="B", release_shift_bh=10.0),
            ],
            baseline_schedule=baseline,
        )
    assert exc.value.order_id == "B" and exc.value.start_bh == 1.0
    # the order of the two operations does not matter
    with pytest.raises(FrozenWindowConflict):
        apply_operations(
            inst,
            [
                op(op="reassign_window", order_id="B", release_shift_bh=10.0),
                op(op="freeze", order_id="B"),
            ],
            baseline_schedule=baseline,
        )


def test_missing_baseline():
    with pytest.raises(MissingBaseline):
        apply_operations(base_instance(), [op(op="freeze", order_id="A")])
    with pytest.raises(MissingBaseline):
        apply_operations(
            base_instance(), [op(op="freeze", order_id="A")],
            baseline_schedule={"assignments": [{"wo": "B", "tech": "T0", "start_bh": 0.0, "end_bh": 2.0}]},
        )
    with pytest.raises(MissingBaseline):
        apply_operations(base_instance(), [], frozen_seed=["A"])
    # a baseline from another instance: the pinned technician cannot serve the trade
    with pytest.raises(MissingBaseline) as exc:
        apply_operations(
            base_instance(), [op(op="freeze", order_id="A")],
            baseline_schedule={"assignments": [
                {"wo": "A", "tech": "T1", "start_bh": 0.0, "end_bh": 1.0}]},
        )
    assert "not this instance's" in str(exc.value)
