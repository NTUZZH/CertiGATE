"""Tier 2: the release-aware admissible bound.

Hand-computed cases first (every number in the assertions is derived in the
comment above it), then the two structural properties the certificate rests on:
the bound is never above a realized schedule's objective, and it is never above
a proven optimum.
"""

from __future__ import annotations

import pytest

from l1adapter import apply, dispatch, evaluate, instances
from l1guard.lb2 import LB2_VARIANT, lb2, lb2_detail
from micro import make_instance, order


def test_an_instance_with_no_possible_tardiness_has_a_zero_bound():
    # p = 1, d = r + SLA(3) = 80: the job cannot be late, so both components
    # are zero.
    inst = make_instance([order("A", "B20", 1.0)], [("T1", "B20")])
    assert lb2(inst) == 0.0


def test_component_i_is_the_earliest_completion_of_each_job():
    # One free technician at t = 0, one job p = 12 due at 8 (class 1), w = 8:
    # C >= 0 + 12, so w * (12 - 8) = 32.  Component (ii): D(8) = 12,
    # cap(8) = 8, O = 4, rho = 8/12, term = (8/12) * 16 / 2 = 5.33 < 32.
    inst = make_instance([order("A", "B20", 12.0, priority=1)], [("T1", "B20")])
    detail = lb2_detail(inst)
    assert detail["per_trade"]["B20"]["bound_i"] == pytest.approx(32.0)
    assert detail["lb_bh"] == pytest.approx(32.0)


def test_component_i_is_release_aware():
    # The extension: the job cannot start before its own release.  p = 2,
    # r = 10, an explicit due of 5, w = 4 (class 2), one free technician.
    # Release-aware: 4 * (max(0, 10) + 2 - 5) = 28.
    # Release-blind (the unextended form) would give 4 * (0 + 2 - 5)^+ = 0.
    inst = make_instance(
        [order("A", "B20", 2.0, release_bh=10.0, priority=2, due_bh=5.0)],
        [("T1", "B20")],
    )
    assert lb2_detail(inst)["per_trade"]["B20"]["bound_i"] == pytest.approx(28.0)


def test_a_busy_technician_raises_the_bound_through_tau_min():
    # Same job, but the only technician is busy until bh 6: C >= 6 + 2 = 8,
    # so w * (8 - 5) = 12 instead of 4 * (0 + 2 - 5)^+ = 0.
    inst = make_instance(
        [order("A", "B20", 2.0, priority=2, due_bh=5.0)], [("T1", "B20")]
    )
    assert lb2(inst) == 0.0
    assert lb2(inst, tau_by_trade={"B20": [6.0]}) == pytest.approx(12.0)


def test_component_ii_is_the_capacity_overflow_area():
    # Two jobs, p = 10 each, both due at 5, w = 1 (class 4), one technician
    # free at 0.  D(5) = 20, cap(5) = 5, O = 15, rho_min = 1/10 = 0.1, so
    # (ii) = 0.1 * 225 / 2 = 11.25.  Component (i) = 2 * 1 * (10 - 5) = 10.
    # The bound is the max, 11.25.
    jobs = [
        order("A", "B20", 10.0, priority=4, due_bh=5.0),
        order("B", "B20", 10.0, priority=4, due_bh=5.0),
    ]
    detail = lb2_detail(make_instance(jobs, [("T1", "B20")]))
    row = detail["per_trade"]["B20"]
    assert row["bound_i"] == pytest.approx(10.0)
    assert row["bound_ii"] == pytest.approx(11.25)
    assert row["bound"] == pytest.approx(11.25)
    assert row["argmax_due_bh"] == pytest.approx(5.0)


def test_unreleased_work_counts_towards_the_overflow():
    # The release-aware part of component (ii): an order released at bh 40 is
    # still due at 5 and still has to be done, so its 10 hours belong in D(5).
    # With it: D(5) = 20, cap(5) = 5, O = 15, rho_min = 0.1, (ii) = 11.25.
    # Counting only released work would give D(5) = 10, O = 5, (ii) = 1.25.
    jobs = [
        order("A", "B20", 10.0, priority=4, due_bh=5.0),
        order("B", "B20", 10.0, release_bh=40.0, priority=4, due_bh=5.0),
    ]
    row = lb2_detail(make_instance(jobs, [("T1", "B20")]))["per_trade"]["B20"]
    assert row["bound_ii"] == pytest.approx(11.25)


def test_two_technicians_halve_the_overflow_area():
    # Same two jobs on k = 2: cap(5) = 10, O = 10, (ii) = 0.1 * 100 / 4 = 2.5,
    # and component (i) still gives 10, so the max is 10.
    jobs = [
        order("A", "B20", 10.0, priority=4, due_bh=5.0),
        order("B", "B20", 10.0, priority=4, due_bh=5.0),
    ]
    row = lb2_detail(make_instance(jobs, [("T1", "B20"), ("T2", "B20")]))["per_trade"]["B20"]
    assert row["bound_ii"] == pytest.approx(2.5)
    assert row["bound"] == pytest.approx(10.0)


def test_trades_are_independent_and_summed():
    jobs = [
        order("A", "B20", 12.0, priority=1),
        order("C", "C10", 12.0, priority=1),
    ]
    inst = make_instance(jobs, [("T1", "B20"), ("T2", "C10")])
    detail = lb2_detail(inst)
    assert detail["per_trade"]["B20"]["bound"] == pytest.approx(32.0)
    assert detail["per_trade"]["C10"]["bound"] == pytest.approx(32.0)
    assert detail["lb_bh"] == pytest.approx(64.0)


def test_a_trade_with_no_technician_contributes_zero_and_says_so():
    inst = make_instance([order("A", "B20", 12.0, priority=1)], [("T1", "C10")])
    detail = lb2_detail(inst)
    assert detail["per_trade"]["B20"]["no_technician"] is True
    assert detail["lb_bh"] == 0.0


def test_jobs_sharing_a_due_date_are_all_counted_before_the_due_is_scored():
    # Three jobs of p = 4 sharing due 5 on one technician: D(5) = 12,
    # cap(5) = 5, O = 7, rho_min = 1/4, (ii) = 0.25 * 49 / 2 = 6.125.
    jobs = [order(i, "B20", 4.0, priority=4, due_bh=5.0) for i in ("A", "B", "C")]
    row = lb2_detail(make_instance(jobs, [("T1", "B20")]))["per_trade"]["B20"]
    assert row["bound_ii"] == pytest.approx(6.125)


def test_the_subset_argument_restricts_the_bound_to_a_queue():
    jobs = [
        order("A", "B20", 12.0, priority=1),
        order("B", "B20", 12.0, priority=1),
    ]
    inst = make_instance(jobs, [("T1", "B20"), ("T2", "B20")])
    assert lb2(inst, order_ids=["A"]) == pytest.approx(32.0)
    assert lb2(inst) == pytest.approx(64.0)


def test_the_bound_accepts_an_adjusted_bundle_and_uses_its_adjusted_fields():
    inst = make_instance([order("A", "B20", 12.0, priority=3)], [("T1", "B20")])
    assert lb2(inst) == 0.0  # class 3: due at 80, p = 12, nothing forced late
    adj = apply.apply_proposal(
        inst, {"operations": [{"op": "set_priority", "order_id": "A", "priority_class": 1}]}
    )
    # class 1: due at 8, w = 8, so 8 * (12 - 8) = 32 on the adjusted fields.
    assert lb2(adj) == pytest.approx(32.0)
    assert lb2(adj.original) == 0.0


def test_the_detail_record_carries_the_variant_and_a_wall_time():
    detail = lb2_detail(make_instance([order("A", "B20", 1.0)], [("T1", "B20")]))
    assert detail["variant"] == LB2_VARIANT
    assert detail["wall_ms"] >= 0.0
    assert detail["n_orders"] == 1


def test_the_bound_never_exceeds_a_realized_schedule_on_real_instances():
    paths = instances.list_instances(10, "replay", "150")[:4]
    paths += instances.list_instances(9, "storm2")[:2]
    for path in paths:
        inst = instances.load_instance(path)
        bound = lb2(inst)
        assert bound >= 0.0
        for rule in ("atc", "edd", "wspt"):
            sched = dispatch.dispatch_baseline(inst, rule, seed=0)
            realized = evaluate.wwt(inst, sched)
            assert bound <= realized + 1e-6, (path.stem, rule, bound, realized)


def test_the_bound_never_exceeds_a_proven_optimum():
    from l1guard.tier1 import tier1_certificate

    for path in instances.list_instances(10, "replay", "150")[:3]:
        inst = instances.load_instance(path)
        rec = tier1_certificate(inst, budget_s=10.0, workers=4)
        assert rec["status"] == "OPTIMAL", rec
        bound = lb2(inst)
        assert bound <= rec["objective_bh"] + 1e-6, (path.stem, bound, rec)
        if rec["objective_bh"] == 0.0:
            # A zero optimum forces a zero bound: the bound is non-negative and
            # cannot exceed the optimum.
            assert bound == 0.0


def test_the_bound_is_zero_when_no_schedule_can_be_late():
    inst = make_instance(
        [order("A", "B20", 1.0), order("B", "B20", 1.0)], [("T1", "B20"), ("T2", "B20")]
    )
    assert lb2(inst) == 0.0
