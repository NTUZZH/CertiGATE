"""G_schema: one test per finding code, and one per structural sub-class."""

from __future__ import annotations

import pytest

from l1adapter import dispatch
from l1guard import G_CERT, evaluate_proposal
from l1guard.guard import _schema_subcode
from l1guard.verdict import APPLIED_WITH_CERTIFICATE, BLOCKED_SCHEMA
from micro import make_instance, order


@pytest.fixture()
def inst():
    return make_instance(
        [
            order("A", "B20", 1.0, building="BLD1"),
            order("B", "B20", 1.0, building="BLD1"),
            order("C", "C10", 1.0),
        ],
        [("T1", "B20"), ("T2", "C10")],
    )


def codes(verdict, stage="schema"):
    return [f.code for f in verdict.findings if f.stage == stage]


def subcodes(verdict):
    return [f.detail.get("subcode") for f in verdict.findings if f.code == "schema_invalid"]


def one(inst, proposal, config=G_CERT, **kw):
    return evaluate_proposal(inst, proposal, config, **kw)


# --------------------------------------------------------------------------- #
# (a) parse                                                                    #
# --------------------------------------------------------------------------- #
def test_malformed_json_is_a_schema_block(inst):
    v = one(inst, '{"operations": [ this is not json')
    assert v.terminal == BLOCKED_SCHEMA
    assert codes(v) == ["malformed_json"]
    assert v.parse["ok"] is False


def test_the_guard_never_repairs_silently(inst):
    """A fenced proposal is a schema violation under the guard, not a repair."""
    fenced = '```json\n{"operations": []}\n```'
    v = one(inst, fenced)
    assert v.terminal == BLOCKED_SCHEMA
    assert "malformed_json" in codes(v)
    assert v.parse["repair"] is None


def test_a_dict_proposal_is_accepted_without_a_parse_step(inst):
    v = one(inst, {"operations": []})
    assert v.parse["source"] == "object"
    assert v.terminal == APPLIED_WITH_CERTIFICATE


def test_a_json_text_proposal_is_accepted(inst):
    v = one(inst, '{"operations": []}')
    assert v.parse["source"] == "text"
    assert v.parse["ok"] is True
    assert v.terminal == APPLIED_WITH_CERTIFICATE


# --------------------------------------------------------------------------- #
# (b) the frozen schema                                                        #
# --------------------------------------------------------------------------- #
def test_subcode_not_object(inst):
    v = one(inst, "[1, 2, 3]")
    assert subcodes(v) == ["not_object"]
    assert v.terminal == BLOCKED_SCHEMA


def test_subcode_missing_operations(inst):
    v = one(inst, {"ops": []})
    assert "missing_operations" in subcodes(v)


def test_subcode_operations_not_array(inst):
    v = one(inst, {"operations": "freeze A"})
    assert subcodes(v) == ["operations_not_array"]


def test_subcode_operation_not_object(inst):
    v = one(inst, {"operations": [42]})
    assert subcodes(v) == ["operation_not_object"]


def test_subcode_unknown_operation(inst):
    v = one(inst, {"operations": [{"op": "cancel_order", "order_id": "A"}]})
    assert subcodes(v) == ["unknown_operation"]
    assert v.findings[0].op_index == 0


def test_subcode_missing_field(inst):
    v = one(inst, {"operations": [{"op": "set_priority", "order_id": "A"}]})
    assert subcodes(v) == ["missing_field"]


def test_subcode_extra_field(inst):
    v = one(inst, {"operations": [{"op": "freeze", "order_id": "A", "why": "urgent"}]})
    assert subcodes(v) == ["extra_field"]


def test_subcode_enum_violation_on_the_priority_class(inst):
    v = one(inst, {"operations": [{"op": "set_priority", "order_id": "A", "priority_class": 9}]})
    assert subcodes(v) == ["enum_violation"]


def test_subcode_enum_violation_on_the_trade_vocabulary(inst):
    v = one(inst, {"operations": [{"op": "pin_next", "order_id": "A", "trade": "PLUMBING"}]})
    assert subcodes(v) == ["enum_violation"]


def test_subcode_type_error(inst):
    v = one(inst, {"operations": [{"op": "freeze", "order_id": 17}]})
    assert subcodes(v) == ["type_error"]


def test_subcode_other_is_the_documented_fallback():
    assert _schema_subcode("something the parser has never said before") == "other"


def test_every_bad_operation_is_reported_not_just_the_first(inst):
    v = one(
        inst,
        {
            "operations": [
                {"op": "nope", "order_id": "A"},
                {"op": "set_priority", "order_id": "A", "priority_class": 7},
                {"op": "freeze", "order_id": "A"},
            ]
        },
    )
    assert subcodes(v) == ["unknown_operation", "enum_violation"]
    assert [f.op_index for f in v.findings if f.code == "schema_invalid"] == [0, 1]


def test_the_root_extra_field_is_reported(inst):
    v = one(inst, {"operations": [], "comment": "done"})
    assert "extra_field" in subcodes(v)


# --------------------------------------------------------------------------- #
# (c) instance-dependent legality                                              #
# --------------------------------------------------------------------------- #
def test_dangling_order_id(inst):
    v = one(inst, {"operations": [{"op": "freeze", "order_id": "W999"}]})
    assert codes(v) == ["dangling_order_id"]
    assert v.findings[0].detail["order_id"] == "W999"
    assert v.terminal == BLOCKED_SCHEMA


def test_dangling_order_id_on_the_reference_side_of_a_reorder(inst):
    v = one(
        inst,
        {"operations": [{"op": "reorder", "order_id": "A", "relation": "before",
                         "ref_order_id": "W999"}]},
    )
    assert codes(v) == ["dangling_order_id"]
    assert v.findings[0].detail["field"] == "ref_order_id"


def test_dangling_building_id(inst):
    v = one(inst, {"operations": [{"op": "batch", "building_id": "TOWER9", "trade": "B20"}]})
    assert codes(v) == ["dangling_building_id"]


def test_unknown_trade_for_this_instance(inst):
    v = one(inst, {"operations": [{"op": "batch", "building_id": "BLD1", "trade": "D90"}]})
    assert codes(v) == ["unknown_trade"]
    assert v.findings[0].detail["trade"] == "D90"


def test_release_shift_out_of_range_above(inst):
    v = one(
        inst,
        {"operations": [{"op": "reassign_window", "order_id": "A", "release_shift_bh": 401.0}]},
    )
    assert codes(v) == ["release_shift_out_of_range"]


def test_release_shift_out_of_range_below(inst):
    v = one(
        inst,
        {"operations": [{"op": "reassign_window", "order_id": "A", "release_shift_bh": -900.0}]},
    )
    assert codes(v) == ["release_shift_out_of_range"]


def test_a_release_shift_inside_the_range_is_legal(inst):
    v = one(
        inst,
        {"operations": [{"op": "reassign_window", "order_id": "A", "release_shift_bh": 40.0}]},
    )
    assert codes(v) == []


def test_the_range_is_configurable(inst):
    tight = G_CERT.with_(max_shift_bh=8.0)
    v = one(
        inst,
        {"operations": [{"op": "reassign_window", "order_id": "A", "release_shift_bh": 40.0}]},
        config=tight,
    )
    assert codes(v) == ["release_shift_out_of_range"]
    assert v.findings[0].detail["max_shift_bh"] == 8.0


def test_duplicate_operation_on_the_same_target(inst):
    v = one(
        inst,
        {
            "operations": [
                {"op": "set_priority", "order_id": "A", "priority_class": 1},
                {"op": "set_priority", "order_id": "A", "priority_class": 2},
            ]
        },
    )
    assert codes(v) == ["duplicate_operation"]
    assert v.findings[0].detail["first_op_index"] == 0


def test_duplicate_detection_normalises_the_two_reorder_relations(inst):
    v = one(
        inst,
        {
            "operations": [
                {"op": "reorder", "order_id": "A", "relation": "before", "ref_order_id": "B"},
                {"op": "reorder", "order_id": "B", "relation": "after", "ref_order_id": "A"},
            ]
        },
    )
    assert codes(v) == ["duplicate_operation"]


def test_the_same_operation_on_different_targets_is_not_a_duplicate(inst):
    v = one(
        inst,
        {
            "operations": [
                {"op": "set_priority", "order_id": "A", "priority_class": 1},
                {"op": "set_priority", "order_id": "B", "priority_class": 1},
            ]
        },
    )
    assert codes(v) == []


def test_freeze_then_unfreeze_is_not_a_duplicate(inst):
    base = dispatch.dispatch_baseline(inst, "atc", seed=0)
    v = one(
        inst,
        {"operations": [{"op": "freeze", "order_id": "A"}, {"op": "unfreeze", "order_id": "A"}]},
        baseline_schedule=base,
    )
    assert codes(v) == []


def test_an_empty_proposal_is_recorded_as_the_refusal_signal_and_never_blocks(inst):
    v = one(inst, {"operations": []})
    assert codes(v) == ["empty_proposal"]
    assert v.findings[0].severity == "info"
    assert v.terminal == APPLIED_WITH_CERTIFICATE


def test_the_schema_hash_travels_with_every_verdict(inst):
    from l1adapter.ops import FROZEN_SCHEMA_SHA256

    v = one(inst, {"operations": []})
    assert v.schema_hash == FROZEN_SCHEMA_SHA256
    assert v.schema_version == "l1-adjustments-1.0.0"
