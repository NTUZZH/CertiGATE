"""The three arms are one code path with different gates."""

from __future__ import annotations

import pytest

from l1adapter import dispatch
from l1guard import G_CERT, G_FEAS, UNGUARDED, GuardConfig, evaluate_proposal, preset
from l1guard.verdict import (
    APPLIED_UNCERTIFIED,
    APPLIED_WITH_CERTIFICATE,
    BLOCKED_FEAS,
    BLOCKED_SCHEMA,
    EXECUTION_FAILED,
    TERMINAL_STATES,
    Verdict,
)
from micro import make_instance, order

DANGLING = {"operations": [{"op": "freeze", "order_id": "W999"}]}
FENCED = '```json\n{"operations": [{"op": "set_priority", "order_id": "A", ' \
         '"priority_class": 1}]}\n```'


@pytest.fixture()
def inst():
    return make_instance(
        [order("A", "B20", 1.0), order("B", "B20", 1.0, priority=1)],
        [("T1", "B20")],
    )


# --------------------------------------------------------------------------- #
# the configurations themselves                                                #
# --------------------------------------------------------------------------- #
def test_the_three_arms_differ_only_in_which_stages_gate():
    assert UNGUARDED.gates == ()
    assert G_FEAS.gates == ("schema", "feas")
    assert G_CERT.gates == ("schema", "feas", "qual")
    ignore = {"name", "gate_schema", "gate_feas", "gate_qual", "lenient_repair"}
    a = {k: v for k, v in G_FEAS.to_dict().items() if k not in ignore}
    b = {k: v for k, v in G_CERT.to_dict().items() if k not in ignore}
    assert a == b


def test_the_config_hash_is_stable_and_distinguishes_the_arms():
    assert G_CERT.config_hash == GuardConfig(name="G_CERT").config_hash
    hashes = {c.config_hash for c in (UNGUARDED, G_FEAS, G_CERT)}
    assert len(hashes) == 3
    assert G_CERT.with_(tau=0.15).config_hash != G_CERT.config_hash


def test_presets_are_addressable_by_name():
    assert preset("G_CERT") is G_CERT
    with pytest.raises(KeyError):
        preset("G_MAYBE")


def test_a_config_refuses_an_unknown_tier_or_field_set():
    with pytest.raises(ValueError):
        GuardConfig(lb_tier="oracle")
    with pytest.raises(ValueError):
        GuardConfig(objective_fields="both")
    with pytest.raises(ValueError):
        GuardConfig(tau=-0.1)


# --------------------------------------------------------------------------- #
# UNGUARDED: repairs, applies, and records what would have been flagged        #
# --------------------------------------------------------------------------- #
def test_unguarded_repairs_a_fenced_proposal_and_says_which_repairs_fired(inst):
    v = evaluate_proposal(inst, FENCED, UNGUARDED)
    assert v.terminal == APPLIED_UNCERTIFIED
    assert v.parse["repair"] == ["strip_code_fence"]
    assert "malformed_json" in [f.code for f in v.findings]  # recorded, not gating
    assert v.ops == [{"op": "set_priority", "order_id": "A", "priority_class": 1}]


def test_the_same_fenced_proposal_is_blocked_by_the_guard(inst):
    assert evaluate_proposal(inst, FENCED, G_CERT).terminal == BLOCKED_SCHEMA
    assert evaluate_proposal(inst, FENCED, G_FEAS).terminal == BLOCKED_SCHEMA


def test_unguarded_records_the_violations_it_lets_through(inst):
    prop = {
        "operations": [
            {"op": "reassign_window", "order_id": "A", "release_shift_bh": 9000.0},
        ]
    }
    v = evaluate_proposal(inst, prop, UNGUARDED)
    assert v.terminal == APPLIED_UNCERTIFIED
    assert [f.code for f in v.findings] == ["release_shift_out_of_range"]
    assert evaluate_proposal(inst, prop, G_FEAS).terminal == BLOCKED_SCHEMA


def test_unguarded_applies_the_operations_that_parsed_and_reports_the_rest(inst):
    prop = {
        "operations": [
            {"op": "teleport", "order_id": "A"},
            {"op": "set_priority", "order_id": "A", "priority_class": 1},
        ]
    }
    v = evaluate_proposal(inst, prop, UNGUARDED)
    assert v.terminal == APPLIED_UNCERTIFIED
    assert [f.code for f in v.findings] == ["schema_invalid"]
    assert len(v.ops) == 1


def test_an_unexecutable_proposal_under_unguarded_is_an_execution_failure(inst):
    v = evaluate_proposal(inst, DANGLING, UNGUARDED)
    assert v.terminal == EXECUTION_FAILED
    assert [f.code for f in v.findings] == ["dangling_order_id", "dangling_order_id"]
    assert v.objective is None


def test_unrepairable_output_under_unguarded_is_an_execution_failure(inst):
    v = evaluate_proposal(inst, "I cannot help with that request.", UNGUARDED)
    assert v.terminal == EXECUTION_FAILED
    assert v.parse["ok"] is False
    assert v.parse["repair"] == []


def test_unguarded_carries_no_certificate_but_still_reports_the_objective(inst):
    v = evaluate_proposal(inst, {"operations": []}, UNGUARDED)
    assert v.certificate is None
    assert v.objective["wwt_adjusted_bh"] == 0.0
    assert v.objective["n_assignments"] == 2


# --------------------------------------------------------------------------- #
# G_FEAS                                                                       #
# --------------------------------------------------------------------------- #
def test_g_feas_applies_without_certifying(inst):
    v = evaluate_proposal(inst, {"operations": []}, G_FEAS)
    assert v.terminal == APPLIED_UNCERTIFIED
    assert v.certificate is None
    assert v.stage_reached == "feas"
    assert "qual" not in v.timings_ms


def test_g_feas_can_be_asked_to_record_a_shadow_certificate(inst):
    v = evaluate_proposal(inst, {"operations": []}, G_FEAS.with_(certify_when_not_gating=True))
    assert v.terminal == APPLIED_UNCERTIFIED  # the stage still does not gate
    assert v.certificate is not None
    assert v.certificate.accepted is True


def test_g_feas_blocks_the_same_feasibility_violations_as_g_cert(inst):
    prop = {"operations": [{"op": "unfreeze", "order_id": "A"}]}
    assert evaluate_proposal(inst, prop, G_FEAS).terminal == BLOCKED_FEAS
    assert evaluate_proposal(inst, prop, G_CERT).terminal == BLOCKED_FEAS


def test_the_schema_findings_are_identical_across_the_three_arms(inst):
    prop = {"operations": [{"op": "set_priority", "order_id": "W1", "priority_class": 9}]}
    sets = []
    for cfg in (UNGUARDED, G_FEAS, G_CERT):
        v = evaluate_proposal(inst, prop, cfg)
        sets.append([f.to_dict() for f in v.findings if f.stage == "schema"])
    assert sets[0] == sets[1] == sets[2]


# --------------------------------------------------------------------------- #
# the verdict object                                                           #
# --------------------------------------------------------------------------- #
def test_every_terminal_state_is_in_the_published_vocabulary(inst):
    base = dispatch.dispatch_baseline(inst, "atc", seed=0)
    seen = set()
    cases = [
        ({"operations": []}, G_CERT, None),
        (DANGLING, G_CERT, None),
        ({"operations": [{"op": "unfreeze", "order_id": "A"}]}, G_CERT, None),
        (DANGLING, UNGUARDED, None),
        ({"operations": []}, G_FEAS, base),
    ]
    for prop, cfg, bl in cases:
        seen.add(evaluate_proposal(inst, prop, cfg, baseline_schedule=bl).terminal)
    assert seen <= set(TERMINAL_STATES)
    assert {"applied_with_certificate", "blocked_schema", "blocked_feas",
            "execution_failed", "applied_uncertified"} == seen


def test_a_verdict_round_trips_through_its_dict_form(inst):
    v = evaluate_proposal(inst, {"operations": []}, G_CERT)
    again = Verdict.from_dict(v.to_dict())
    assert again.to_dict() == v.to_dict()
    assert again.fingerprint() == v.fingerprint()


def test_the_fingerprint_ignores_measured_wall_clock(inst):
    a = evaluate_proposal(inst, {"operations": []}, G_CERT)
    b = evaluate_proposal(inst, {"operations": []}, G_CERT)
    assert a.timings_ms != b.timings_ms  # two timers never agree
    assert a.fingerprint() == b.fingerprint()
    assert a.digest() == b.digest()


def test_the_verdict_reports_which_stage_it_reached(inst):
    assert evaluate_proposal(inst, "{", G_CERT).stage_reached == "schema"
    assert (
        evaluate_proposal(
            inst, {"operations": [{"op": "unfreeze", "order_id": "A"}]}, G_CERT
        ).stage_reached
        == "feas"
    )
    assert evaluate_proposal(inst, {"operations": []}, G_CERT).stage_reached == "qual"


def test_the_schedule_digest_identifies_the_executed_schedule(inst):
    a = evaluate_proposal(inst, {"operations": []}, G_CERT)
    b = evaluate_proposal(
        inst, {"operations": [{"op": "pin_next", "order_id": "A", "trade": "B20"}]}, G_CERT
    )
    assert a.schedule_digest is not None
    assert a.schedule_digest != b.schedule_digest
