"""The frozen schema and the proposal parser."""

from __future__ import annotations

import pytest

from l1adapter import ops
from l1adapter.errors import SchemaViolation


def test_schema_file_matches_the_frozen_hash():
    assert ops.schema_sha256() == ops.FROZEN_SCHEMA_SHA256
    assert ops.verify_schema() == ops.FROZEN_SCHEMA_SHA256
    assert ops.SCHEMA_VERSION == "l1-adjustments-1.0.0"


def test_enums_come_from_the_schema_file():
    assert set(ops.OP_NAMES) == {
        "set_priority",
        "pin_next",
        "reorder",
        "reassign_window",
        "freeze",
        "unfreeze",
        "batch",
    }
    assert ops.PRIORITY_CLASSES == (1, 2, 3, 4)
    assert ops.RELATIONS == ("before", "after")
    assert len(ops.TRADE_VOCABULARY) == 14
    assert "D20" in ops.TRADE_VOCABULARY and "UNK" in ops.TRADE_VOCABULARY


def test_parse_all_seven_operations_round_trip():
    proposal = {
        "operations": [
            {"op": "set_priority", "order_id": "W1", "priority_class": 1},
            {"op": "pin_next", "order_id": "W2", "trade": "D20"},
            {"op": "reorder", "order_id": "W3", "relation": "before", "ref_order_id": "W4"},
            {"op": "reassign_window", "order_id": "W5", "release_shift_bh": -3.5},
            {"op": "freeze", "order_id": "W6"},
            {"op": "unfreeze", "order_id": "W7"},
            {"op": "batch", "building_id": "0500", "trade": "E10"},
        ]
    }
    parsed = ops.parse_operations(proposal, strict_schema=True)
    assert [o.op for o in parsed] == [
        "set_priority", "pin_next", "reorder", "reassign_window",
        "freeze", "unfreeze", "batch",
    ]
    assert parsed[0].priority_class == 1
    assert parsed[3].release_shift_bh == -3.5
    assert ops.to_proposal(parsed) == proposal


def test_empty_operations_is_the_refusal_signal_not_an_error():
    assert ops.parse_operations({"operations": []}, strict_schema=True) == []


def test_proposal_accepted_as_json_text():
    assert len(ops.parse_operations('{"operations": [{"op": "freeze", "order_id": "W1"}]}')) == 1


@pytest.mark.parametrize(
    "proposal",
    [
        {"operations": [{"op": "set_prio", "order_id": "W1", "priority_class": 1}]},
        {"operations": [{"op": "set_priority", "order_id": "W1", "priority_class": 5}]},
        {"operations": [{"op": "set_priority", "order_id": "W1"}]},
        {"operations": [{"op": "pin_next", "order_id": "W1", "trade": "Z99"}]},
        {"operations": [{"op": "reorder", "order_id": "W1", "relation": "during", "ref_order_id": "W2"}]},
        {"operations": [{"op": "freeze", "order_id": "W1", "extra": 1}]},
        {"operations": [{"op": "freeze", "order_id": 7}]},
        {"operations": [{"op": "reassign_window", "order_id": "W1", "release_shift_bh": "8"}]},
        {"ops": []},
        [{"op": "freeze", "order_id": "W1"}],
    ],
)
def test_structural_violations_are_rejected(proposal):
    with pytest.raises(SchemaViolation):
        ops.parse_operations(proposal)


@pytest.mark.parametrize(
    "proposal",
    [
        {"operations": [{"op": "set_priority", "order_id": "W1", "priority_class": 5}]},
        {"operations": [{"op": "pin_next", "order_id": "W1", "trade": "Z99"}]},
        {"operations": [{"op": "freeze", "order_id": "W1", "extra": 1}]},
        {"ops": []},
    ],
)
def test_jsonschema_agrees_with_the_structural_parser(proposal):
    with pytest.raises(SchemaViolation):
        ops.validate_proposal(proposal)


def test_malformed_json_is_a_schema_violation():
    with pytest.raises(SchemaViolation):
        ops.parse_operations('{"operations": [')
