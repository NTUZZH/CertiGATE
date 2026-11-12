"""Dispatch-time semantics: pins, precedence, freezes, batch chains.

Every schedule built here is checked by the Y1 referee
(``fmwos.validator.validate``) against the adjusted instance.
"""

from __future__ import annotations

import pytest

from l1adapter import apply_operations, dispatch, evaluate, ops
from l1adapter.errors import CyclicPrecedence
from micro import assert_feasible, by_tech, by_wo, make_instance, order, order_ids


def op(**kw):
    return ops.parse_operations({"operations": [kw]})[0]


def three_orders_one_tech():
    """EDD order is B (due 1), C (due 3), A (due 5); all released at bh 0."""
    return make_instance(
        [
            order("A", "D20", 1.0, due_bh=5.0),
            order("B", "D20", 1.0, due_bh=1.0),
            order("C", "D20", 1.0, due_bh=3.0),
        ],
        [("T0", "D20")],
    )


# --------------------------------------------------------------------------- #
# baseline sanity                                                              #
# --------------------------------------------------------------------------- #
def test_zero_operation_adjustment_reproduces_the_baseline_on_a_micro_instance():
    inst = three_orders_one_tech()
    base = dispatch.dispatch_baseline(inst, "edd", 0)
    adj = apply_operations(inst, [])
    assert not adj.is_constrained
    got = dispatch.dispatch_adjusted(adj, "edd", 0)
    assert dispatch.schedules_equal(base, got)
    assert order_ids(base) == ["B", "C", "A"]
    assert_feasible(adj, got)


# --------------------------------------------------------------------------- #
# pin_next                                                                     #
# --------------------------------------------------------------------------- #
def test_pin_next_takes_the_trades_next_decision():
    inst = three_orders_one_tech()
    adj = apply_operations(inst, [op(op="pin_next", order_id="A", trade="D20")])
    sched, diag = dispatch.dispatch_adjusted_verbose(adj, "edd", 0)
    assert order_ids(sched) == ["A", "B", "C"]      # pinned first, then EDD
    assert by_wo(sched)["A"]["start_bh"] == 0.0
    assert diag["n_forced_picks"] == 1
    assert_feasible(adj, sched)


def test_two_pins_are_ordered_by_their_position_in_the_proposal():
    inst = three_orders_one_tech()
    adj = apply_operations(
        inst,
        [
            op(op="pin_next", order_id="C", trade="D20"),
            op(op="pin_next", order_id="A", trade="D20"),
        ],
    )
    sched = dispatch.dispatch_adjusted(adj, "edd", 0)
    assert order_ids(sched) == ["C", "A", "B"]
    assert_feasible(adj, sched)


def test_pin_fires_at_the_first_decision_at_which_the_order_is_queued():
    inst = make_instance(
        [
            order("A", "D20", 1.0, release_bh=2.0, due_bh=9.0),
            order("B", "D20", 3.0, release_bh=0.0, due_bh=1.0),
            order("C", "D20", 1.0, release_bh=0.0, due_bh=3.0),
        ],
        [("T0", "D20")],
    )
    assert order_ids(dispatch.dispatch_baseline(inst, "edd", 0)) == ["B", "C", "A"]
    adj = apply_operations(inst, [op(op="pin_next", order_id="A", trade="D20")])
    sched = dispatch.dispatch_adjusted(adj, "edd", 0)
    # B occupies the technician until bh 3; A is out by then, so the next
    # decision is the pinned one, and C follows.
    assert order_ids(sched) == ["B", "A", "C"]
    assert by_wo(sched)["A"]["start_bh"] == pytest.approx(3.0)
    assert_feasible(adj, sched)


# --------------------------------------------------------------------------- #
# reorder                                                                      #
# --------------------------------------------------------------------------- #
def test_reorder_before_holds_and_after_is_the_same_constraint():
    inst = make_instance(
        [order("A", "D20", 1.0, due_bh=5.0), order("B", "D20", 1.0, due_bh=1.0)],
        [("T0", "D20")],
    )
    assert order_ids(dispatch.dispatch_baseline(inst, "edd", 0)) == ["B", "A"]

    for proposal in (
        {"op": "reorder", "order_id": "A", "relation": "before", "ref_order_id": "B"},
        {"op": "reorder", "order_id": "B", "relation": "after", "ref_order_id": "A"},
    ):
        adj = apply_operations(inst, [op(**proposal)])
        sched = dispatch.dispatch_adjusted(adj, "edd", 0)
        rows = by_wo(sched)
        assert rows["A"]["start_bh"] <= rows["B"]["start_bh"]
        assert order_ids(sched) == ["A", "B"]
        assert_feasible(adj, sched)


def test_reorder_only_constrains_the_pair_it_names():
    inst = three_orders_one_tech()
    adj = apply_operations(
        inst, [op(op="reorder", order_id="A", relation="before", ref_order_id="B")]
    )
    sched = dispatch.dispatch_adjusted(adj, "edd", 0)
    rows = by_wo(sched)
    assert rows["A"]["start_bh"] <= rows["B"]["start_bh"]
    # C is unconstrained, so EDD still prefers it over A at bh 0
    assert order_ids(sched) == ["C", "A", "B"]
    assert_feasible(adj, sched)


def test_cross_trade_reorder_makes_the_successor_wait():
    inst = make_instance(
        [
            order("A", "D20", 1.0, release_bh=3.0, due_bh=9.0),
            order("B", "D30", 1.0, release_bh=0.0, due_bh=1.0),
        ],
        [("T0", "D20"), ("T1", "D30")],
    )
    assert by_wo(dispatch.dispatch_baseline(inst, "edd", 0))["B"]["start_bh"] == 0.0
    adj = apply_operations(
        inst, [op(op="reorder", order_id="A", relation="before", ref_order_id="B")]
    )
    sched = dispatch.dispatch_adjusted(adj, "edd", 0)
    rows = by_wo(sched)
    assert rows["A"]["start_bh"] == pytest.approx(3.0)
    # same instant is allowed by start_a <= start_b: the sweep repeats until
    # nothing more can move, so B starts as soon as A has started.
    assert rows["B"]["start_bh"] == pytest.approx(3.0)
    assert_feasible(adj, sched)


def test_a_precedence_cycle_cannot_be_dispatched():
    inst = three_orders_one_tech()
    adj = apply_operations(
        inst,
        [
            op(op="reorder", order_id="A", relation="before", ref_order_id="B"),
            op(op="reorder", order_id="B", relation="before", ref_order_id="A"),
        ],
    )
    with pytest.raises(CyclicPrecedence) as exc:
        dispatch.dispatch_adjusted(adj, "edd", 0)
    assert exc.value.cycles == [["A", "B"]]


# --------------------------------------------------------------------------- #
# freeze                                                                       #
# --------------------------------------------------------------------------- #
def freeze_instance():
    return make_instance(
        [
            order("A", "D20", 1.0, due_bh=2.0),
            order("B", "D20", 1.0, due_bh=4.0),
            order("C", "D20", 1.0, due_bh=6.0),
            order("D", "D20", 1.0, due_bh=8.0),
        ],
        [("T0", "D20"), ("T1", "D20")],
    )


def test_freeze_keeps_the_baseline_assignment_while_everything_else_moves():
    inst = freeze_instance()
    base = dispatch.dispatch_baseline(inst, "edd", 0)
    slot = by_wo(base)["D"]

    adj = apply_operations(
        inst,
        [
            op(op="freeze", order_id="D"),
            op(op="pin_next", order_id="C", trade="D20"),
            op(op="set_priority", order_id="B", priority_class=1),
        ],
        baseline_schedule=base,
    )
    sched, diag = dispatch.dispatch_adjusted_verbose(adj, "edd", 0)
    got = by_wo(sched)["D"]
    assert (got["tech"], got["start_bh"], got["end_bh"]) == (
        slot["tech"], slot["start_bh"], slot["end_bh"],
    )
    assert diag["n_frozen"] == 1
    assert order_ids(sched)[0] == "C"          # the pin still fired
    assert_feasible(adj, sched)


def test_a_frozen_slot_keeps_its_technician_free_until_the_pinned_start():
    # T0 must keep bh [2, 3) for the frozen order F, so at bh 0 it can only
    # take a job that finishes by bh 2: the long job L goes to T1.
    inst = make_instance(
        [
            order("F", "D20", 1.0, due_bh=3.0),
            order("L", "D20", 5.0, due_bh=1.0),
            order("S", "D20", 2.0, due_bh=2.0),
        ],
        [("T0", "D20"), ("T1", "D20")],
    )
    baseline = {
        "assignments": [
            {"wo": "F", "tech": "T0", "start_bh": 2.0, "end_bh": 3.0},
            {"wo": "L", "tech": "T1", "start_bh": 0.0, "end_bh": 5.0},
            {"wo": "S", "tech": "T0", "start_bh": 0.0, "end_bh": 2.0},
        ]
    }
    adj = apply_operations(inst, [], frozen_seed=["F"], baseline_schedule=baseline)
    sched = dispatch.dispatch_adjusted(adj, "edd", 0)
    rows = by_wo(sched)
    assert (rows["F"]["tech"], rows["F"]["start_bh"]) == ("T0", 2.0)
    assert rows["L"]["tech"] == "T1"           # 5 bh cannot fit before bh 2 on T0
    assert rows["S"]["tech"] == "T0" and rows["S"]["start_bh"] == 0.0
    assert_feasible(adj, sched)


def test_an_inconsistent_baseline_is_caught_not_laundered():
    """Two frozen slots that overlap on one technician cannot both be honoured."""
    from l1adapter.errors import FrozenSlotConflict

    inst = make_instance(
        [order("F1", "D20", 2.0, due_bh=9.0), order("F2", "D20", 2.0, due_bh=9.0)],
        [("T0", "D20")],
    )
    bad_baseline = {
        "assignments": [
            {"wo": "F1", "tech": "T0", "start_bh": 0.0, "end_bh": 2.0},
            {"wo": "F2", "tech": "T0", "start_bh": 1.0, "end_bh": 3.0},
        ]
    }
    adj = apply_operations(
        inst, [], frozen_seed=["F1", "F2"], baseline_schedule=bad_baseline
    )
    with pytest.raises(FrozenSlotConflict) as exc:
        dispatch.dispatch_adjusted(adj, "edd", 0)
    assert exc.value.order_id == "F2" and exc.value.tech_id == "T0"


def test_frozen_seed_can_be_lifted_by_unfreeze():
    inst = freeze_instance()
    base = dispatch.dispatch_baseline(inst, "edd", 0)
    adj = apply_operations(
        inst, [op(op="unfreeze", order_id="A")], frozen_seed=["A"], baseline_schedule=base
    )
    assert adj.frozen == {}
    sched = dispatch.dispatch_adjusted(adj, "edd", 0)
    assert dispatch.schedules_equal(base, sched)


# --------------------------------------------------------------------------- #
# batch                                                                        #
# --------------------------------------------------------------------------- #
def test_batch_chain_is_one_technician_consecutive_and_edd_ordered():
    inst = make_instance(
        [
            order("P", "D20", 1.0, due_bh=9.0, building="B1"),
            order("Q", "D20", 1.0, due_bh=7.0, building="B1"),
            order("R", "D20", 1.0, due_bh=8.0, building="B1"),
            order("X", "D20", 1.0, due_bh=2.0, building="B2"),
            order("Y", "D20", 1.0, due_bh=4.0, building="B2"),
            order("Z", "D20", 1.0, due_bh=6.0, building="B2"),
        ],
        [("T0", "D20"), ("T1", "D20")],
    )
    adj = apply_operations(inst, [op(op="batch", building_id="B1", trade="D20")])
    assert adj.batches[0].members == ("Q", "R", "P")
    sched = dispatch.dispatch_adjusted(adj, "edd", 0)
    rows = by_wo(sched)

    chain_tech = {rows[o]["tech"] for o in ("P", "Q", "R")}
    assert len(chain_tech) == 1, "the chain must run on one technician"
    tech = chain_tech.pop()

    seq = [a["wo"] for a in by_tech(sched)[tech]]
    first = seq.index("Q")
    assert seq[first:first + 3] == ["Q", "R", "P"], "EDD order, no other job between"
    assert rows["R"]["start_bh"] == pytest.approx(rows["Q"]["end_bh"])
    assert rows["P"]["start_bh"] == pytest.approx(rows["R"]["end_bh"])
    assert_feasible(adj, sched)


def test_batch_chain_waits_for_an_unreleased_member():
    inst = make_instance(
        [
            order("P", "D20", 1.0, release_bh=0.0, due_bh=1.0, building="B1"),
            order("Q", "D20", 1.0, release_bh=6.0, due_bh=7.0, building="B1"),
            order("X", "D20", 1.0, release_bh=0.0, due_bh=2.0, building="B2"),
        ],
        [("T0", "D20")],
    )
    adj = apply_operations(inst, [op(op="batch", building_id="B1", trade="D20")])
    sched, diag = dispatch.dispatch_adjusted_verbose(adj, "edd", 0)
    rows = by_wo(sched)
    assert rows["P"]["start_bh"] == 0.0
    assert rows["Q"]["tech"] == rows["P"]["tech"]
    assert rows["Q"]["start_bh"] == pytest.approx(6.0)   # the tech idled, waiting
    assert rows["X"]["start_bh"] >= 6.0 + 1.0            # X could not use the bound tech
    assert diag["n_group_waits"] > 0
    assert_feasible(adj, sched)


def test_batch_group_excludes_a_frozen_member_and_says_so():
    inst = make_instance(
        [
            order("P", "D20", 1.0, due_bh=9.0, building="B1"),
            order("Q", "D20", 1.0, due_bh=7.0, building="B1"),
        ],
        [("T0", "D20")],
    )
    baseline = dispatch.dispatch_baseline(inst, "edd", 0)
    adj = apply_operations(
        inst,
        [op(op="freeze", order_id="Q"), op(op="batch", building_id="B1", trade="D20")],
        baseline_schedule=baseline,
    )
    assert adj.batches[0].members == ("P",)
    assert "batch_members_frozen:B1/D20" in adj.notes
    assert_feasible(adj, dispatch.dispatch_adjusted(adj, "edd", 0))


# --------------------------------------------------------------------------- #
# evaluation surface                                                           #
# --------------------------------------------------------------------------- #
def test_wwt_scores_against_whichever_instance_it_is_given():
    # Every order is tardy, so a weight change is visible in the objective.
    inst = make_instance(
        [
            order("A", "D20", 4.0, due_bh=5.0),
            order("B", "D20", 4.0, due_bh=1.0),
            order("C", "D20", 4.0, due_bh=3.0),
        ],
        [("T0", "D20")],
    )
    base = dispatch.dispatch_baseline(inst, "edd", 0)
    adj = apply_operations(inst, [op(op="set_priority", order_id="A", priority_class=1)])
    sched = dispatch.dispatch_adjusted(adj, "edd", 0)
    assert dispatch.schedules_equal(base, sched)   # same plan, different scoring

    adjusted_wwt = evaluate.wwt(adj, sched)        # A: weight 8, due 8  -> 8*4
    original_wwt = evaluate.wwt(adj.original, sched)  # A: weight 2, due 5 -> 2*7
    assert original_wwt == pytest.approx(2 * 3 + 2 * 5 + 2 * 7)
    assert adjusted_wwt == pytest.approx(2 * 3 + 2 * 5 + 8 * 4)
    assert original_wwt == pytest.approx(evaluate.wwt(inst, base))
    # the validator computes WWT independently and must agree with ours
    assert evaluate.validate(adj, sched)["metrics"]["WWT"] == pytest.approx(adjusted_wwt)
    assert len(evaluate.tardiness_table(adj, sched)) == 3
