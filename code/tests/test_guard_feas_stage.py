"""G_feas: the typed-error mapping, the frozen-order rule, and the referee."""

from __future__ import annotations

import pytest

from l1adapter import dispatch
from l1adapter.errors import AdapterError, DispatchDeadlock, FrozenSlotConflict
from l1guard import G_CERT, G_FEAS, UNGUARDED, evaluate_proposal, guard
from l1guard.verdict import APPLIED_UNCERTIFIED, BLOCKED_FEAS, EXECUTION_FAILED
from micro import make_instance, order


@pytest.fixture()
def inst():
    return make_instance(
        [
            order("A", "B20", 1.0, building="BLD1"),
            order("B", "B20", 1.0, priority=1, building="BLD1"),
            order("S", "B20", 1.0, building="SOLO"),
            order("C", "C10", 1.0),
        ],
        [("T1", "B20"), ("T2", "C10")],
    )


@pytest.fixture()
def base(inst):
    return dispatch.dispatch_baseline(inst, "atc", seed=0)


def codes(verdict, stage="feas"):
    return [f.code for f in verdict.findings if f.stage == stage]


def infos(verdict):
    return [f.code for f in verdict.findings if f.severity == "info"]


# --------------------------------------------------------------------------- #
# typed errors                                                                 #
# --------------------------------------------------------------------------- #
def test_trade_mismatch(inst):
    v = evaluate_proposal(
        inst, {"operations": [{"op": "pin_next", "order_id": "A", "trade": "C10"}]}, G_CERT
    )
    assert v.terminal == BLOCKED_FEAS
    assert codes(v) == ["trade_mismatch"]


def test_not_frozen(inst):
    v = evaluate_proposal(inst, {"operations": [{"op": "unfreeze", "order_id": "A"}]}, G_CERT)
    assert v.terminal == BLOCKED_FEAS
    assert codes(v) == ["not_frozen"]


def test_missing_baseline(inst):
    v = evaluate_proposal(inst, {"operations": [{"op": "freeze", "order_id": "A"}]}, G_CERT)
    assert v.terminal == BLOCKED_FEAS
    assert codes(v) == ["missing_baseline"]


def test_frozen_window_conflict(inst, base):
    # Shift first, then freeze: the frozen-order rule has nothing to say (the
    # order is not frozen when it is edited), so the only finding is the
    # mechanical contradiction between the pinned start and the new release.
    v = evaluate_proposal(
        inst,
        {
            "operations": [
                {"op": "reassign_window", "order_id": "A", "release_shift_bh": 10.0},
                {"op": "freeze", "order_id": "A"},
            ]
        },
        G_CERT,
        baseline_schedule=base,
    )
    assert v.terminal == BLOCKED_FEAS
    assert codes(v) == ["frozen_window_conflict"]


def test_precedence_cycle_between_two_orders(inst):
    v = evaluate_proposal(
        inst,
        {
            "operations": [
                {"op": "reorder", "order_id": "A", "relation": "before", "ref_order_id": "B"},
                {"op": "reorder", "order_id": "B", "relation": "before", "ref_order_id": "A"},
            ]
        },
        G_CERT,
    )
    assert v.terminal == BLOCKED_FEAS
    assert codes(v) == ["precedence_cycle"]


def test_precedence_self_loop(inst):
    v = evaluate_proposal(
        inst,
        {"operations": [{"op": "reorder", "order_id": "A", "relation": "before",
                         "ref_order_id": "A"}]},
        G_CERT,
    )
    assert codes(v) == ["precedence_cycle"]


def test_a_cyclic_proposal_has_no_execution_even_when_nothing_gates(inst):
    from l1guard import UNGUARDED

    v = evaluate_proposal(
        inst,
        {
            "operations": [
                {"op": "reorder", "order_id": "A", "relation": "before", "ref_order_id": "B"},
                {"op": "reorder", "order_id": "B", "relation": "before", "ref_order_id": "A"},
            ]
        },
        UNGUARDED,
    )
    assert v.terminal == EXECUTION_FAILED
    assert codes(v) == ["precedence_cycle"]


# --------------------------------------------------------------------------- #
# the frozen-order rule                                                        #
# --------------------------------------------------------------------------- #
def test_editing_a_standing_frozen_order_is_a_feasibility_violation(inst, base):
    v = evaluate_proposal(
        inst,
        {"operations": [{"op": "set_priority", "order_id": "A", "priority_class": 1}]},
        G_CERT,
        baseline_schedule=base,
        frozen_seed=("A",),
    )
    assert v.terminal == BLOCKED_FEAS
    assert "frozen_order_edit" in codes(v)


def test_unfreezing_first_makes_the_same_edit_legitimate(inst, base):
    v = evaluate_proposal(
        inst,
        {
            "operations": [
                {"op": "unfreeze", "order_id": "A"},
                {"op": "set_priority", "order_id": "A", "priority_class": 1},
            ]
        },
        G_CERT,
        baseline_schedule=base,
        frozen_seed=("A",),
    )
    assert "frozen_order_edit" not in codes(v)
    assert v.terminal != BLOCKED_FEAS


def test_freezing_an_already_frozen_order_is_not_an_edit(inst, base):
    v = evaluate_proposal(
        inst,
        {"operations": [{"op": "freeze", "order_id": "A"}]},
        G_CERT,
        baseline_schedule=base,
        frozen_seed=("A",),
    )
    assert "frozen_order_edit" not in codes(v)


def test_a_reorder_touching_a_frozen_order_is_an_edit(inst, base):
    v = evaluate_proposal(
        inst,
        {"operations": [{"op": "reorder", "order_id": "B", "relation": "before",
                         "ref_order_id": "A"}]},
        G_CERT,
        baseline_schedule=base,
        frozen_seed=("A",),
    )
    assert "frozen_order_edit" in codes(v)


def test_a_batch_group_containing_a_frozen_member_is_an_edit(inst, base):
    v = evaluate_proposal(
        inst,
        {"operations": [{"op": "batch", "building_id": "BLD1", "trade": "B20"}]},
        G_CERT,
        baseline_schedule=base,
        frozen_seed=("A",),
    )
    assert "frozen_order_edit" in codes(v)
    assert v.findings[0].detail["order_id"] == "A"


def test_a_proposals_own_freeze_does_not_block_its_other_operations(inst, base):
    """Guard v0.2: the proposal is one atomic adjustment, so its own freeze
    never poisons its other operations, in either listing order."""
    for ops in (
        [
            {"op": "freeze", "order_id": "A"},
            {"op": "set_priority", "order_id": "A", "priority_class": 1},
        ],
        [
            {"op": "set_priority", "order_id": "A", "priority_class": 1},
            {"op": "freeze", "order_id": "A"},
        ],
    ):
        v = evaluate_proposal(
            inst, {"operations": ops}, G_CERT, baseline_schedule=base
        )
        assert "frozen_order_edit" not in codes(v)


def test_an_edit_of_a_standing_frozen_order_is_still_flagged(inst, base):
    """The episode's standing frozen set stays protected; only an explicit
    unfreeze anywhere in the proposal releases the order."""
    v = evaluate_proposal(
        inst,
        {"operations": [{"op": "set_priority", "order_id": "A", "priority_class": 1}]},
        G_CERT,
        baseline_schedule=base,
        frozen_seed=("A",),
    )
    assert "frozen_order_edit" in codes(v)
    v2 = evaluate_proposal(
        inst,
        {
            "operations": [
                {"op": "set_priority", "order_id": "A", "priority_class": 1},
                {"op": "unfreeze", "order_id": "A"},
            ]
        },
        G_CERT,
        baseline_schedule=base,
        frozen_seed=("A",),
    )
    assert "frozen_order_edit" not in codes(v2)


# --------------------------------------------------------------------------- #
# the adapter's non-fatal notes become recorded, non-blocking findings          #
# --------------------------------------------------------------------------- #
def test_release_clipped_at_zero_is_recorded_and_does_not_block(inst):
    v = evaluate_proposal(
        inst,
        {"operations": [{"op": "reassign_window", "order_id": "A", "release_shift_bh": -5.0}]},
        G_CERT,
    )
    assert "release_clipped_at_zero" in infos(v)
    assert v.terminal != BLOCKED_FEAS


def test_batch_group_empty_and_members_frozen_are_recorded(inst, base):
    v = evaluate_proposal(
        inst,
        {"operations": [{"op": "batch", "building_id": "SOLO", "trade": "B20"}]},
        G_FEAS,
        baseline_schedule=base,
        frozen_seed=("S",),
    )
    assert "batch_members_frozen" in infos(v)
    assert "batch_group_empty" in infos(v)


def test_precedence_into_a_frozen_order_is_recorded(inst, base):
    v = evaluate_proposal(
        inst,
        {"operations": [{"op": "reorder", "order_id": "B", "relation": "before",
                         "ref_order_id": "A"}]},
        G_FEAS,
        baseline_schedule=base,
        frozen_seed=("A",),
    )
    assert "precedence_into_frozen_order" in infos(v)


def test_precedence_overriding_a_batch_groups_edd_order_is_recorded(inst):
    # BLD1/B20 groups A (due 80) and B (due 8); EDD puts B first, and the edge
    # asks for A before B.
    v = evaluate_proposal(
        inst,
        {
            "operations": [
                {"op": "batch", "building_id": "BLD1", "trade": "B20"},
                {"op": "reorder", "order_id": "A", "relation": "before", "ref_order_id": "B"},
            ]
        },
        G_FEAS,
    )
    assert "precedence_overrides_batch_edd" in infos(v)
    assert v.terminal == APPLIED_UNCERTIFIED


# --------------------------------------------------------------------------- #
# the referee and the defensive paths                                          #
# --------------------------------------------------------------------------- #
def test_a_referee_rejection_blocks_at_the_feasibility_stage(inst, monkeypatch):
    def fake_validate(instance, schedule):
        return {"feasible": False, "violations": ["invented for the test"], "metrics": {}}

    monkeypatch.setattr(guard.evaluate_mod, "validate", fake_validate)
    v = evaluate_proposal(inst, {"operations": []}, G_CERT)
    assert v.terminal == BLOCKED_FEAS
    assert codes(v) == ["validator_infeasible"]


def test_every_schedule_the_guard_accepts_has_passed_the_referee(inst):
    v = evaluate_proposal(
        inst, {"operations": [{"op": "pin_next", "order_id": "B", "trade": "B20"}]}, G_CERT
    )
    assert v.objective["feasible"] is True
    assert v.artifacts["validation"]["feasible"] is True


def test_frozen_precedence_conflict(inst, base):
    # Both ends frozen with pinned starts that contradict the edge: A and B are
    # the same trade, so the baseline runs them one after the other, and the
    # edge asks for the later one to start first.
    later = max(("A", "B"), key=lambda oid: {a["wo"]: a for a in base["assignments"]}[oid]
                ["start_bh"])
    earlier = "A" if later == "B" else "B"
    v = evaluate_proposal(
        inst,
        {
            "operations": [
                {"op": "reorder", "order_id": later, "relation": "before",
                 "ref_order_id": earlier},
            ]
        },
        G_CERT,
        baseline_schedule=base,
        frozen_seed=("A", "B"),
    )
    assert v.terminal == BLOCKED_FEAS
    assert "frozen_precedence_conflict" in codes(v)
    finding = [f for f in v.findings if f.code == "frozen_precedence_conflict"][0]
    assert finding.severity == "violation"
    assert finding.detail["error"] == "FrozenPrecedenceConflict"
    assert finding.detail["order_id"] == later
    assert finding.detail["ref_order_id"] == earlier
    assert finding.detail["start_bh"] > finding.detail["ref_start_bh"]


def test_an_edge_out_of_a_frozen_order_into_a_free_one_is_not_a_conflict(inst, base):
    v = evaluate_proposal(
        inst,
        {"operations": [{"op": "reorder", "order_id": "A", "relation": "before",
                         "ref_order_id": "C"}]},
        G_CERT,
        baseline_schedule=base,
        frozen_seed=("A",),
    )
    assert "frozen_precedence_conflict" not in codes(v)


def test_a_dispatch_deadlock_is_an_instrument_fault_not_a_guard_decision(inst, monkeypatch):
    def boom(adjusted, rule="atc", seed=0):
        raise DispatchDeadlock(["A"])

    monkeypatch.setattr(guard.dispatch_mod, "dispatch_adjusted", boom)
    v = evaluate_proposal(inst, {"operations": []}, G_CERT)
    assert v.terminal == EXECUTION_FAILED
    assert codes(v) == ["infra_error"]
    fault = [f for f in v.findings if f.code == "infra_error"][0]
    assert fault.severity == "infra" and not fault.blocking
    assert fault.detail["error"] == "DispatchDeadlock"
    assert fault.detail["unassigned"] == ["A"]
    assert "DispatchDeadlock raised while dispatching" in fault.message
    assert v.violations() == []  # never counted as a violation the guard caught


def test_an_unexpected_exception_in_dispatch_is_an_instrument_fault(inst, monkeypatch):
    def boom(adjusted, rule="atc", seed=0):
        raise RuntimeError("a defect in the instrument, not in the proposal")

    monkeypatch.setattr(guard.dispatch_mod, "dispatch_adjusted", boom)
    for cfg in (UNGUARDED, G_FEAS, G_CERT):
        v = evaluate_proposal(inst, {"operations": []}, cfg)
        assert v.terminal == EXECUTION_FAILED, cfg.name
        assert codes(v) == ["infra_error"]
        assert v.violations() == []
        fault = [f for f in v.findings if f.code == "infra_error"][0]
        assert fault.severity == "infra"
        assert "a defect in the instrument" in fault.message


def test_a_referee_that_raises_is_an_instrument_fault(inst, monkeypatch):
    def boom(instance, schedule):
        raise ValueError("the referee itself broke")

    monkeypatch.setattr(guard.evaluate_mod, "validate", boom)
    v = evaluate_proposal(inst, {"operations": []}, G_CERT)
    assert v.terminal == EXECUTION_FAILED
    assert codes(v) == ["infra_error"]
    assert v.violations() == []


def test_a_frozen_slot_conflict_is_mapped(inst, monkeypatch):
    def boom(adjusted, rule="atc", seed=0):
        raise FrozenSlotConflict("A", "T1", 0.0, "invented for the test")

    monkeypatch.setattr(guard.dispatch_mod, "dispatch_adjusted", boom)
    v = evaluate_proposal(inst, {"operations": []}, G_CERT)
    assert codes(v) == ["frozen_slot_conflict"]


def test_an_unclassified_adapter_error_falls_back_to_apply_error(inst, monkeypatch):
    def boom(*args, **kwargs):
        raise AdapterError("something the mapping does not know")

    monkeypatch.setattr(guard.apply_mod, "apply_operations", boom)
    v = evaluate_proposal(inst, {"operations": []}, G_CERT)
    assert codes(v) == ["apply_error"]


def test_the_feasibility_stage_reports_everything_it_found(inst, base):
    v = evaluate_proposal(
        inst,
        {
            "operations": [
                {"op": "set_priority", "order_id": "A", "priority_class": 1},
                {"op": "pin_next", "order_id": "A", "trade": "C10"},
            ]
        },
        G_CERT,
        baseline_schedule=base,
        frozen_seed=("A",),
    )
    # The frozen-order rule fires on both operations before the adapter raises
    # on the trade mismatch, and all three findings are reported.
    assert codes(v) == ["frozen_order_edit", "frozen_order_edit", "trade_mismatch"]
