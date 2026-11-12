"""G_qual: the gap convention, the tier selection, and the certificate tuple."""

from __future__ import annotations

import pytest

from l1guard import G_CERT, evaluate_proposal, guard
from l1guard.tier1 import TIER1_VARIANT
from l1guard.lb2 import LB2_VARIANT
from l1guard.verdict import (
    APPLIED_WITH_CERTIFICATE,
    BLOCKED_QUAL,
    Certificate,
    certified_gap,
)
from micro import make_instance, order

#: One urgent short order and one long low-priority order on one technician.
#: Left alone, the urgent order runs first and nothing is late (obj = 0, and
#: the bound is 0 as well).  Forced to wait behind the long order, the urgent
#: order is 7 bh late at weight 8, so obj = 56 against a bound of 0: the
#: LB = 0 case of the gap convention, on a schedule that is perfectly feasible.
def poor_instance():
    return make_instance(
        [
            order("X", "B20", 1.0, priority=1, due_bh=2.0),
            order("Y", "B20", 8.0, priority=3),
        ],
        [("T1", "B20")],
    )


POOR = {
    "operations": [
        {"op": "reorder", "order_id": "X", "relation": "after", "ref_order_id": "Y"}
    ]
}


# --------------------------------------------------------------------------- #
# the gap convention, as arithmetic                                            #
# --------------------------------------------------------------------------- #
def test_gap_is_zero_when_both_objective_and_bound_are_zero():
    assert certified_gap(0.0, 0.0, 1.0) == 0.0


def test_gap_uses_the_declared_floor_when_the_bound_is_zero():
    assert certified_gap(5.0, 0.0, 1.0) == pytest.approx(5.0)


def test_gap_is_the_plain_ratio_once_the_bound_is_above_the_floor():
    assert certified_gap(12.0, 10.0, 1.0) == pytest.approx(0.2)


def test_the_floor_binds_for_a_bound_below_one_weighted_hour():
    assert certified_gap(1.5, 0.5, 1.0) == pytest.approx(1.0)


def test_gap_is_clamped_at_zero_against_floating_point_noise():
    assert certified_gap(10.0, 10.0 + 1e-12, 1.0) == 0.0


def test_the_floor_constant_is_configurable_and_recorded():
    cfg = G_CERT.with_(lb_floor_bh=10.0)
    assert cfg.lb_floor_bh == 10.0
    assert certified_gap(5.0, 0.0, cfg.lb_floor_bh) == pytest.approx(0.5)


# --------------------------------------------------------------------------- #
# end to end                                                                   #
# --------------------------------------------------------------------------- #
def test_a_clean_proposal_is_applied_with_a_certificate():
    v = evaluate_proposal(poor_instance(), {"operations": []}, G_CERT)
    assert v.terminal == APPLIED_WITH_CERTIFICATE
    cert = v.certificate
    assert cert.obj_bh == 0.0 and cert.lb_bh == 0.0 and cert.gap == 0.0
    assert cert.accepted is True
    assert cert.tier == "tier2" and cert.lb_variant == LB2_VARIANT
    assert cert.tau == 0.2 and cert.tau_provisional is True


def test_a_feasible_but_poor_proposal_is_blocked_at_the_quality_stage():
    v = evaluate_proposal(poor_instance(), POOR, G_CERT)
    assert v.terminal == BLOCKED_QUAL
    assert [f.code for f in v.findings if f.stage == "qual"] == ["gap_above_tau"]
    assert v.objective["feasible"] is True  # feasible, and still refused
    assert v.certificate.obj_bh == pytest.approx(56.0)
    assert v.certificate.lb_bh == 0.0
    assert v.certificate.gap == pytest.approx(56.0)


def test_a_blocked_proposal_still_carries_its_certificate_for_referral():
    v = evaluate_proposal(poor_instance(), POOR, G_CERT)
    assert v.certificate is not None
    assert v.certificate.accepted is False
    assert "obj=" in v.certificate.tuple_str()


def test_tau_is_an_inclusive_threshold():
    v = evaluate_proposal(poor_instance(), POOR, G_CERT)
    gap = v.certificate.gap
    at = evaluate_proposal(poor_instance(), POOR, G_CERT.with_(tau=gap))
    below = evaluate_proposal(poor_instance(), POOR, G_CERT.with_(tau=gap - 1e-9))
    assert at.terminal == APPLIED_WITH_CERTIFICATE
    assert below.terminal == BLOCKED_QUAL


def test_the_certificate_records_the_objective_under_both_field_sets():
    inst = make_instance([order("A", "B20", 12.0, priority=1)], [("T1", "B20")])
    # Relaxing the class moves the due date out, which is exactly the kind of
    # adjustment that flatters the adjusted-field objective; both are recorded.
    prop = {"operations": [{"op": "set_priority", "order_id": "A", "priority_class": 3}]}
    v = evaluate_proposal(inst, prop, G_CERT)
    assert v.certificate.obj_bh == 0.0  # adjusted fields: due 80, ends at 12
    assert v.certificate.obj_original_bh == pytest.approx(8.0 * (12.0 - 8.0))
    assert v.objective["wwt_adjusted_bh"] == 0.0


def test_scoring_against_the_original_fields_is_a_configuration():
    inst = make_instance([order("A", "B20", 12.0, priority=1)], [("T1", "B20")])
    prop = {"operations": [{"op": "set_priority", "order_id": "A", "priority_class": 3}]}
    v = evaluate_proposal(inst, prop, G_CERT.with_(objective_fields="original"))
    assert v.certificate.objective_fields == "original"
    assert v.certificate.obj_bh == pytest.approx(32.0)
    assert v.certificate.lb_bh == pytest.approx(32.0)  # the bound is on the same fields


# --------------------------------------------------------------------------- #
# tier selection                                                               #
# --------------------------------------------------------------------------- #
def test_tier1_certificates_come_from_the_solver():
    inst = poor_instance()
    v = evaluate_proposal(inst, POOR, G_CERT.with_(lb_tier="tier1", tier1_budget_s=5.0))
    cert = v.certificate
    assert cert.tier == "tier1" and cert.lb_variant == TIER1_VARIANT
    assert cert.budget_s == 5.0 and cert.solve_wall_ms > 0.0
    assert cert.tier1_status == "OPTIMAL"
    assert cert.lb_tier2_bh is None
    # The solver's bound is on the fields-only relaxation, which the proposal's
    # precedence edge is not part of: the optimum of the relaxation is 0.
    assert cert.lb_bh == 0.0


def test_the_best_tier_takes_the_larger_of_the_two_admissible_bounds():
    inst = make_instance(
        [
            order("A", "B20", 10.0, priority=4, due_bh=5.0),
            order("B", "B20", 10.0, priority=4, due_bh=5.0),
        ],
        [("T1", "B20")],
    )
    v = evaluate_proposal(inst, {"operations": []}, G_CERT.with_(lb_tier="best", tau=99.0))
    cert = v.certificate
    assert cert.lb_tier1_bh is not None and cert.lb_tier2_bh is not None
    assert cert.lb_bh == max(cert.lb_tier1_bh, cert.lb_tier2_bh)
    assert cert.tier.startswith("best:")


def test_the_solver_incumbent_is_recorded_next_to_the_bound():
    inst = poor_instance()
    v = evaluate_proposal(inst, {"operations": []}, G_CERT.with_(lb_tier="best"))
    assert v.certificate.tier1_incumbent_bh == 0.0
    assert v.certificate.tier1_relaxation == "fields_only"


# --------------------------------------------------------------------------- #
# defensive paths                                                              #
# --------------------------------------------------------------------------- #
def test_a_bound_above_the_objective_is_recorded_and_never_blocks(monkeypatch):
    def fake_lb2_detail(fields, *args, **kwargs):
        return {"lb_bh": 1e6, "wall_ms": 0.01, "variant": "fake", "per_trade": {}}

    monkeypatch.setattr(guard, "lb2_detail", fake_lb2_detail)
    v = evaluate_proposal(poor_instance(), {"operations": []}, G_CERT)
    assert "lb_exceeds_objective" in [f.code for f in v.findings]
    assert v.certificate.gap == 0.0
    assert v.terminal == APPLIED_WITH_CERTIFICATE


def test_no_bound_at_all_is_a_quality_block():
    cfg = G_CERT
    broken = G_CERT.with_(name="broken")
    object.__setattr__(broken, "lb_tier", "none")  # bypasses validation on purpose
    v = evaluate_proposal(poor_instance(), {"operations": []}, broken)
    assert v.terminal == BLOCKED_QUAL
    assert [f.code for f in v.findings if f.stage == "qual"] == ["lb_unavailable"]
    assert v.certificate is None
    assert cfg.lb_tier == "tier2"  # the preset is untouched


def test_a_failure_in_the_certification_path_is_an_instrument_fault(monkeypatch):
    def boom(fields, *args, **kwargs):
        raise ZeroDivisionError("the bound blew up")

    monkeypatch.setattr(guard, "lb2_detail", boom)
    v = evaluate_proposal(poor_instance(), POOR, G_CERT)
    assert v.terminal == "execution_failed"  # not a refusal, and not an acceptance
    fault = [f for f in v.findings if f.code == "infra_error"][0]
    assert fault.stage == "qual" and fault.severity == "infra" and not fault.blocking
    assert "ZeroDivisionError raised while computing the certificate" in fault.message
    assert v.violations() == []
    assert v.certificate is None
    # The schedule was still executed and is still reported: the instrument
    # failed at the certificate, not at the dispatch.
    assert v.objective["wwt_adjusted_bh"] == pytest.approx(56.0)


def test_a_shadow_certificate_that_fails_does_not_relabel_the_arm(monkeypatch):
    """G_FEAS applied the proposal; a failed *shadow* certificate cannot undo that."""
    from l1guard import G_FEAS

    def boom(fields, *args, **kwargs):
        raise ZeroDivisionError("the bound blew up")

    monkeypatch.setattr(guard, "lb2_detail", boom)
    v = evaluate_proposal(
        poor_instance(), POOR, G_FEAS.with_(certify_when_not_gating=True)
    )
    assert v.terminal == "applied_uncertified"  # the arm's own outcome stands
    assert [f.code for f in v.findings if f.stage == "qual"] == ["infra_error"]
    assert v.violations() == []
    assert v.certificate is None


def test_the_certificate_serialises_and_round_trips():
    v = evaluate_proposal(poor_instance(), POOR, G_CERT)
    d = v.certificate.to_dict()
    assert set(
        ["obj_bh", "lb_bh", "gap", "tier", "lb_wall_ms", "solve_wall_ms", "budget_s",
         "lb_variant"]
    ) <= set(d)
    assert Certificate.from_dict(d).to_dict() == d


def test_the_quality_stage_is_timed_separately():
    v = evaluate_proposal(poor_instance(), POOR, G_CERT)
    assert set(v.timings_ms) == {"schema", "feas", "qual", "total"}
    assert v.timings_ms["total"] >= v.timings_ms["qual"]
    assert v.certificate.lb_wall_ms > 0.0
    assert v.certificate.solve_wall_ms == 0.0  # no solver was called in tier2
