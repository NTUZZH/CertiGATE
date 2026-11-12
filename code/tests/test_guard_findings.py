"""The finding vocabulary is closed, registered, and fully exercised."""

from __future__ import annotations

from pathlib import Path

import pytest

from l1guard import findings as F

TESTS_DIR = Path(__file__).resolve().parent


def test_every_registered_code_has_a_stage_and_a_severity():
    for code, spec in F.CODES.items():
        assert spec.stage in F.STAGES, code
        assert spec.severity in F.SEVERITIES, code
        assert spec.description


def test_a_finding_takes_its_stage_and_severity_from_the_registry():
    f = F.make("gap_above_tau", "over", gap=1.0)
    assert f.stage == F.STAGE_QUAL and f.severity == F.VIOLATION and f.blocking
    info = F.make("empty_proposal", "no operations")
    assert info.severity == F.INFO and not info.blocking


def test_only_violations_gate_and_instrument_faults_never_do():
    fault = F.make("infra_error", "the dispatcher raised", stage=F.STAGE_QUAL)
    assert fault.severity == F.INFRA
    assert not fault.blocking
    mixed = [fault, F.make("not_frozen", "y"), F.make("empty_proposal", "z")]
    assert [f.code for f in F.blocking(mixed)] == ["not_frozen"]
    assert [f.code for f in F.infra(mixed)] == ["infra_error"]


def test_the_stage_override_exists_for_instrument_faults_and_is_validated():
    assert F.make("infra_error", "x").stage == F.STAGE_FEAS  # registry default
    assert F.make("infra_error", "x", stage=F.STAGE_QUAL).stage == F.STAGE_QUAL
    with pytest.raises(KeyError):
        F.make("infra_error", "x", stage="certification")


def test_an_unregistered_code_cannot_be_created():
    with pytest.raises(KeyError):
        F.make("looks_wrong_to_me", "a typo invents a category")


def test_schema_invalid_needs_a_registered_subcode():
    with pytest.raises(KeyError):
        F.make("schema_invalid", "no subcode given")
    with pytest.raises(KeyError):
        F.make("schema_invalid", "bad subcode", subcode="weird")
    assert F.make("schema_invalid", "ok", subcode="type_error").detail["subcode"] == "type_error"


def test_a_finding_round_trips_through_its_dict_form():
    f = F.make("dangling_order_id", "no such order", op_index=2, order_id="W9")
    assert F.Finding.from_dict(f.to_dict()) == f


def test_the_helpers_select_by_stage_and_severity():
    assert "malformed_json" in F.codes_for_stage(F.STAGE_SCHEMA)
    assert "gap_above_tau" not in F.codes_for_stage(F.STAGE_FEAS)
    mixed = [F.make("empty_proposal", "x"), F.make("not_frozen", "y")]
    assert [f.code for f in F.blocking(mixed)] == ["not_frozen"]


def test_every_code_and_subcode_is_exercised_by_a_test():
    """The acceptance criterion, enforced: one test per finding code."""
    blob = "\n".join(p.read_text() for p in TESTS_DIR.glob("test_guard_*.py"))
    unexercised = sorted(c for c in F.CODES if c not in blob)
    assert unexercised == []
    missing_subcodes = sorted(s for s in F.SCHEMA_SUBCODES if s not in blob)
    assert missing_subcodes == []
