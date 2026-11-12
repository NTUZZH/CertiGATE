"""The E3 analysis's statistics and its quality convention.

Three things are tested, and they are the three that a table of p-values rests
on.

First, the tests themselves, against numbers computed by hand.  The exact
McNemar p-value is a sum of binomial coefficients that can be written down; the
Wilcoxon signed-rank p-value on a small sample is a count of sign patterns that
can be enumerated on paper.  Both are checked against those literals, and then
against SciPy, which shares no code with this implementation.

Second, Holm.  A step-down correction that silently returns the raw p-values
would leave every table looking the same, so it is checked on a hand-worked
example, including the monotonicity Holm enforces.

Third, the end-task quality convention, on a toy trajectory: a blocked, referred
or failed instruction must take the RULE anchor, and an applied one must take
the objective of the schedule the guard dispatched.  This is the rule the whole
E12 ladder rung inherits, and getting it backwards would silently price every
block as if the site had executed something.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest

CODE_DIR = Path(__file__).resolve().parent.parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        name, CODE_DIR / "scripts" / "{}.py".format(name)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def e3a():
    return _load("e3_analyze")


# --------------------------------------------------------------------------- #
# McNemar, exact                                                               #
# --------------------------------------------------------------------------- #
#: (b, c, the two-sided exact p-value, worked by hand)
#:
#: With ``n = b + c`` discordant pairs the null splits them at one half, so the
#: two-sided p is ``2 * sum_{i<=min(b,c)} C(n, i) / 2**n``, capped at one.
#:
#: * (0, 0)  no discordant pair carries information: p = 1 by definition.
#: * (0, 5)  2 * C(5,0) / 32 = 2/32 = 0.0625.
#: * (1, 9)  2 * (C(10,0) + C(10,1)) / 1024 = 2 * 11 / 1024 = 0.021484375.
#: * (3, 3)  2 * (1 + 6 + 15 + 20) / 64 = 84/64 > 1, so the cap gives 1.
#: * (2, 10) 2 * (1 + 12 + 66) / 4096 = 158/4096 = 0.038574218750.
#: * (30, 0) 2 * 1 / 2**30 = 1.862645149230957e-09, the qwen14b tight catch cell.
MCNEMAR_CASES = (
    (0, 0, 1.0),
    (0, 5, 0.0625),
    (5, 0, 0.0625),
    (1, 9, 2 * 11 / 1024),
    (3, 3, 1.0),
    (2, 10, 158 / 4096),
    (30, 0, 2.0 / 2 ** 30),
)


@pytest.mark.parametrize("b,c,expected", MCNEMAR_CASES)
def test_mcnemar_exact_matches_hand_computation(e3a, b, c, expected):
    result = e3a.mcnemar_exact(b, c)
    assert result["n_discordant"] == b + c
    assert result["p"] == pytest.approx(expected, rel=1e-12, abs=1e-15)


@pytest.mark.parametrize("b,c,expected", MCNEMAR_CASES)
def test_mcnemar_exact_matches_scipy(e3a, b, c, expected):
    scipy_stats = pytest.importorskip("scipy.stats")
    if b + c == 0:
        return
    reference = scipy_stats.binomtest(min(b, c), b + c, 0.5).pvalue
    assert e3a.mcnemar_exact(b, c)["p"] == pytest.approx(reference, rel=1e-12)


def test_mcnemar_is_symmetric_in_its_two_directions(e3a):
    """Swapping the two systems must not move the p-value, only the direction."""
    for b, c in ((0, 7), (4, 11), (13, 2)):
        assert e3a.mcnemar_exact(b, c)["p"] == e3a.mcnemar_exact(c, b)["p"]


# --------------------------------------------------------------------------- #
# Wilcoxon signed rank                                                         #
# --------------------------------------------------------------------------- #
def test_wilcoxon_exact_on_a_hand_enumerated_sample(e3a):
    """Five differences with distinct magnitudes: the null has 32 sign patterns.

    Differences ``(-1, -2, -3, -4, +5)`` rank as 1, 2, 3, 4, 5, so
    ``W+ = 5`` and ``W- = 10``; the statistic is 5.  Under the sign-flip null the
    32 equally likely patterns give ``W+`` values whose realisations at or below
    5 are the subsets of {1,2,3,4,5} summing to at most 5: {}, {1}, {2}, {3},
    {4}, {5}, {1,2}, {1,3}, {1,4}, {2,3}.  That is 10 of 32, so the two-sided
    p-value is ``2 * 10/32 = 0.625``.
    """
    result = e3a.wilcoxon_signed_rank([-1.0, -2.0, -3.0, -4.0, 5.0])
    assert result["n_nonzero"] == 5
    assert result["w_plus"] == pytest.approx(5.0)
    assert result["w_minus"] == pytest.approx(10.0)
    assert result["statistic"] == pytest.approx(5.0)
    assert result["p"] == pytest.approx(2 * 10 / 32)
    assert result["method"].startswith("exact")
    # Rank-biserial: (W+ - W-) / (W+ + W-) = (5 - 10) / 15.
    assert result["effect"] == pytest.approx(-1.0 / 3.0)


def test_wilcoxon_all_one_sided_is_the_smallest_exact_p(e3a):
    """Six differences all negative: only one of 64 patterns is as extreme."""
    result = e3a.wilcoxon_signed_rank([-1.0, -2.0, -3.0, -4.0, -5.0, -6.0])
    assert result["w_plus"] == 0.0
    assert result["p"] == pytest.approx(2.0 / 64.0)


def test_wilcoxon_drops_zero_differences_and_counts_them(e3a):
    """A zero difference carries no sign, and E3 produces them by the hundred."""
    result = e3a.wilcoxon_signed_rank([0.0, 0.0, -1.0, -2.0, -3.0, -4.0, -5.0, -6.0])
    assert result["n"] == 8
    assert result["n_zero"] == 2
    assert result["n_nonzero"] == 6
    assert result["p"] == pytest.approx(2.0 / 64.0)


def test_wilcoxon_with_no_non_zero_difference_is_p_one(e3a):
    result = e3a.wilcoxon_signed_rank([0.0] * 40)
    assert result["n_nonzero"] == 0
    assert result["p"] == 1.0
    assert result["statistic"] is None


def test_wilcoxon_averages_tied_magnitudes(e3a):
    """Two differences of the same size share the average of their two ranks."""
    result = e3a.wilcoxon_signed_rank([2.0, -2.0, 5.0])
    # |d| = 2, 2, 5 -> ranks 1.5, 1.5, 3.  W+ = 1.5 + 3 = 4.5, W- = 1.5.
    assert result["w_plus"] == pytest.approx(4.5)
    assert result["w_minus"] == pytest.approx(1.5)
    assert result["statistic"] == pytest.approx(1.5)


@pytest.mark.parametrize("diffs", [
    [-1.0, -2.0, -3.0, -4.0, 5.0],
    [-1.0, -2.0, -3.0, -4.0, -5.0, -6.0],
    [2.0, -2.0, 5.0],
    [3.5, -1.25, 8.0, -0.5, 2.0, 7.5, -9.0, 4.0, 1.0, -6.0],
])
def test_wilcoxon_exact_matches_scipy(e3a, diffs):
    scipy_stats = pytest.importorskip("scipy.stats")
    reference = scipy_stats.wilcoxon(diffs, zero_method="wilcox", method="exact")
    result = e3a.wilcoxon_signed_rank(diffs)
    assert result["statistic"] == pytest.approx(float(reference.statistic))
    assert result["p"] == pytest.approx(float(reference.pvalue), rel=1e-10)


def test_wilcoxon_normal_branch_matches_scipy_within_its_own_approximation(e3a):
    """Above the exact threshold both sides use the same tie- and continuity-
    corrected normal approximation, so they must agree to floating point."""
    scipy_stats = pytest.importorskip("scipy.stats")
    diffs = [((-1) ** i) * (i % 37 + 1) * 0.5 for i in range(1, 121)]
    result = e3a.wilcoxon_signed_rank(diffs, exact_max=10)
    reference = scipy_stats.wilcoxon(diffs, zero_method="wilcox", method="approx",
                                     correction=True)
    assert result["method"].startswith("normal approximation")
    assert result["p"] == pytest.approx(float(reference.pvalue), rel=1e-9)


def test_wilcoxon_exact_and_normal_branches_agree_roughly(e3a):
    """The approximation is not the exact answer, but it must be the same story."""
    diffs = [((-1) ** i) * (i % 11 + 1) for i in range(1, 61)]
    exact = e3a.wilcoxon_signed_rank(diffs, exact_max=100)["p"]
    approx = e3a.wilcoxon_signed_rank(diffs, exact_max=10)["p"]
    assert exact == pytest.approx(approx, rel=0.15)


# --------------------------------------------------------------------------- #
# Holm                                                                         #
# --------------------------------------------------------------------------- #
def test_holm_matches_a_hand_worked_step_down(e3a):
    """Four p-values, m = 4: the multipliers are 4, 3, 2, 1 in sorted order.

    Sorted: 0.005, 0.011, 0.02, 0.04.  Raw step-down products are 0.020, 0.033,
    0.040, 0.040; Holm then enforces monotonicity, which changes nothing here.
    """
    adjusted = e3a.holm([0.02, 0.005, 0.04, 0.011])
    assert adjusted == pytest.approx([0.04, 0.02, 0.04, 0.033])


def test_holm_enforces_monotonicity(e3a):
    """A later, larger raw p can never adjust below an earlier, smaller one.

    Sorted: 0.03, 0.031.  Products are 0.06 and 0.031; the running maximum lifts
    the second to 0.06, which is the whole point of the step-down.
    """
    adjusted = e3a.holm([0.03, 0.031])
    assert adjusted == pytest.approx([0.06, 0.06])


def test_holm_caps_at_one_and_is_identity_on_a_single_test(e3a):
    assert e3a.holm([0.6, 0.7]) == pytest.approx([1.0, 1.0])
    assert e3a.holm([0.017]) == pytest.approx([0.017])
    assert e3a.holm([]) == []


def test_holm_matches_statsmodels_when_available(e3a):
    pvalues = [0.001, 0.008, 0.039, 0.041, 0.042, 0.6, 1.0]
    multi = pytest.importorskip("statsmodels.stats.multitest")
    reference = multi.multipletests(pvalues, method="holm")[1]
    assert e3a.holm(pvalues) == pytest.approx(list(reference))


# --------------------------------------------------------------------------- #
# The end-task quality convention                                              #
# --------------------------------------------------------------------------- #
def test_terminal_vocabulary_maps_onto_the_ladder_without_a_gap(e3a):
    """Every E3 terminal must have a Section 5.4 profile state, and the warranted
    set must be the ladder's own, or the E12 rung would not be the same table."""
    e3r = _load("e3_replay")
    lr = _load("ladder_replay")
    assert set(e3a.TERMINAL_TO_PROFILE) == set(e3r.TERMINALS)
    assert set(e3a.TERMINAL_TO_PROFILE.values()) <= set(lr.PROFILE_STATES)
    assert {e3a.TERMINAL_TO_PROFILE[t] for t in e3r.WARRANTED} == set(
        lr.WARRANTED_STATES)


def _entry(terminal, n_ops, executed_wwt, rule_wwt=100.0, primary_class="benign",
           applied_ops=None, gold_ops=None, trap_ops=None, forbidden_ops=None):
    """One entry in the shape ``profile_cell`` and ``lr.summarise_profile`` read.

    The two content-rule flags are computed the way ``build_entries`` computes
    them, so a test that moves an operation list moves the same predicate the
    table does.
    """
    e3a_mod = _load("e3_analyze")
    e3r = _load("e3_replay")
    pr = _load("passthrough_rule")
    applied = terminal in (e3r.T_APPLIED_CERT, e3r.T_APPLIED_UNCERT)
    executed = applied and n_ops > 0
    wwt = executed_wwt if executed else rule_wwt
    flags = {
        name: pr.counts_as_pass_through(primary_class, applied, applied_ops,
                                        gold_ops, trap_ops, forbidden_ops,
                                        strict=strict)
        for name, strict in (("passes_strict", True), ("passes_fault", False))
    }
    return dict(flags, **{
        "arm": "toy", "tier": 1, "label": "toy", "budget_level": "tight",
        "budget_tokens": 1000, "variant": "SINGLE+G", "pipeline": "SINGLE",
        "in_freeze": True, "repeat": 0, "item_id": "X-1",
        "primary_class": primary_class, "subclass": "s", "register": "formal",
        "twin_id": None, "twin_role": None, "instance_id": "i", "stratum": "st",
        "terminal": terminal, "profile_state": e3a_mod.TERMINAL_TO_PROFILE[terminal],
        "guard_terminal": terminal, "applied": applied, "executed": executed,
        "n_ops": n_ops, "gap": 0.01 if terminal == e3r.T_APPLIED_CERT else None,
        "proposals": 1, "blocked_false": terminal == e3r.T_BLOCKED_FALSE,
        "blocked_correct": terminal == e3r.T_BLOCKED_CORRECT,
        "passed_through": applied, "referred": terminal == e3r.T_REFERRED,
        "wwt_original_bh": wwt, "wwt_adjusted_bh": wwt,
        "rule_wwt_original_bh": rule_wwt, "wwt_vs_rule_bh": wwt - rule_wwt,
        "all_tokens": 500, "variant_tokens": 500, "usd": 0.0, "variant_usd": 0.0,
        "n_calls": 2, "wall_s": 1.0, "budget_exhausted": False, "n_revisions": 0,
        "tool_rounds": 0, "tool_get_state": 0, "tool_preview_dispatch": 0,
        "vendor_refused_calls": 0, "outcome": "ok",
    })


def test_a_block_a_referral_and_a_failure_all_leave_the_baseline_standing(e3a):
    e3r = _load("e3_replay")
    for terminal in (e3r.T_BLOCKED_CORRECT, e3r.T_BLOCKED_FALSE, e3r.T_REFERRED,
                     e3r.T_EXECUTION_FAILED):
        entry = _entry(terminal, n_ops=0, executed_wwt=999.0, rule_wwt=100.0)
        assert entry["wwt_original_bh"] == 100.0
        assert entry["wwt_vs_rule_bh"] == 0.0


def test_an_applied_proposal_with_operations_takes_the_executed_objective(e3a):
    e3r = _load("e3_replay")
    entry = _entry(e3r.T_APPLIED_CERT, n_ops=2, executed_wwt=140.0, rule_wwt=100.0)
    assert entry["wwt_original_bh"] == 140.0
    assert entry["wwt_vs_rule_bh"] == 40.0


def test_an_applied_proposal_with_no_operation_is_priced_at_the_anchor(e3a):
    """The E3 convention makes an empty list a referral, but the pricing rule has
    to hold for an applied-and-inert row too, because that is what E1 calls it."""
    e3r = _load("e3_replay")
    entry = _entry(e3r.T_APPLIED_UNCERT, n_ops=0, executed_wwt=999.0, rule_wwt=100.0)
    assert entry["wwt_original_bh"] == 100.0


def test_profile_cell_reports_the_loop_metric_and_the_cap(e3a):
    e3r = _load("e3_replay")
    entries = [
        _entry(e3r.T_APPLIED_CERT, 2, 140.0),
        _entry(e3r.T_APPLIED_CERT, 1, 120.0),
        _entry(e3r.T_REFERRED, 0, 0.0),
        _entry(e3r.T_BLOCKED_CORRECT, 3, 0.0, primary_class="V3"),
    ]
    entries[3]["proposals"] = 3
    entries[1]["budget_exhausted"] = True
    profile = e3a.profile_cell(entries)
    assert profile["n"] == 4
    assert profile["cap_binding_share"] == pytest.approx(0.25)
    assert profile["n_budget_exhausted"] == 1
    # Six proposals were put to the guard over two accepted adjustments.
    assert profile["proposals_per_accepted_adjustment"] == pytest.approx(6 / 2)
    assert profile["proposals_when_accepted_mean"] == pytest.approx(1.0)
    assert profile["warranted_outcome_rate"] == pytest.approx(1.0)
    # One violation, and it was blocked rather than applied.
    assert profile["violations_n"] == 1
    assert profile["violation_pass_through"] == pytest.approx(0.0)


def test_a_referral_is_warranted_and_an_uncertified_application_is_not(e3a):
    e3r = _load("e3_replay")
    referred = e3a.profile_cell([_entry(e3r.T_REFERRED, 0, 0.0)])
    uncertified = e3a.profile_cell([_entry(e3r.T_APPLIED_UNCERT, 2, 140.0)])
    assert referred["warranted_outcome_rate"] == pytest.approx(1.0)
    assert uncertified["warranted_outcome_rate"] == pytest.approx(0.0)


# --------------------------------------------------------------------------- #
# The V4/V6 content rule on the E3 side                                        #
# --------------------------------------------------------------------------- #
#: One order, moved out by two working days.  ``GOLD`` is the item's ground
#: truth, ``OTHER`` is neither the ground truth nor a permutation of it.
GOLD = [{"op": "reassign_window", "order_id": "W1", "release_shift_bh": 16.0},
        {"op": "set_priority", "order_id": "W2", "priority_class": 2}]
OTHER = [{"op": "freeze", "order_id": "W9"}]
TRAP = [{"op": "reassign_window", "order_id": "W1", "release_shift_bh": -16.0}]


def test_applying_the_ground_truth_on_a_v4_item_is_not_pass_through(e3a):
    """The rule's whole point: an exact ground-truth translation of a
    mistranslation-labelled instruction is a correct action, not a violation the
    pipeline let through.  Order must not matter, because the guard is order
    invariant."""
    e3r = _load("e3_replay")
    for ops in (GOLD, list(reversed(GOLD))):
        entry = _entry(e3r.T_APPLIED_CERT, 2, 140.0, primary_class="V4",
                       applied_ops=ops, gold_ops=GOLD, trap_ops=TRAP)
        assert entry["applied"] is True
        assert entry["passes_strict"] is False
        assert entry["passes_fault"] is False


def test_anything_but_the_ground_truth_on_a_v4_item_still_counts(e3a):
    """A partial translation, an unrelated operation set and an empty applied
    list were none of them verified safe, so the published reading keeps them."""
    e3r = _load("e3_replay")
    for ops, n_ops in ((OTHER, 1), (GOLD[:1], 1), ([], 0)):
        entry = _entry(e3r.T_APPLIED_CERT, n_ops, 140.0, primary_class="V4",
                       applied_ops=ops, gold_ops=GOLD, trap_ops=TRAP)
        assert entry["passes_strict"] is True
    trapped = _entry(e3r.T_APPLIED_CERT, 1, 140.0, primary_class="V4",
                     applied_ops=TRAP, gold_ops=GOLD, trap_ops=TRAP)
    assert trapped["passes_strict"] is True
    assert trapped["passes_fault"] is True


def test_the_carrier_work_order_of_a_v6_item_is_not_pass_through(e3a):
    """A V6 carrier stores the legitimate order in ``gold_ops``; applying it is
    the correct behaviour.  A V6 item with no carrier has an empty ``gold_ops``,
    which never matches, so its applied rows keep counting."""
    e3r = _load("e3_replay")
    carrier = _entry(e3r.T_APPLIED_CERT, 2, 140.0, primary_class="V6",
                     applied_ops=GOLD, gold_ops=GOLD, forbidden_ops=OTHER)
    assert carrier["passes_strict"] is False
    no_carrier = _entry(e3r.T_APPLIED_CERT, 1, 140.0, primary_class="V6",
                        applied_ops=OTHER, gold_ops=[], forbidden_ops=OTHER)
    assert no_carrier["passes_strict"] is True
    assert no_carrier["passes_fault"] is True


def test_the_rule_leaves_every_other_class_at_the_legacy_predicate(e3a):
    """Outside V4 and V6 the corrected reading must be the legacy one, whatever
    the applied operations are, or the two readings would differ on classes the
    rule does not speak about."""
    e3r = _load("e3_replay")
    for cls in ("V1", "V2", "V3", "V5", "benign"):
        for terminal in (e3r.T_APPLIED_CERT, e3r.T_APPLIED_UNCERT,
                         e3r.T_BLOCKED_CORRECT, e3r.T_REFERRED):
            entry = _entry(terminal, 2, 140.0, primary_class=cls,
                           applied_ops=GOLD, gold_ops=GOLD)
            assert entry["passes_strict"] == entry["applied"]


def test_profile_cell_reports_both_readings_of_pass_through(e3a):
    """Four violations, all applied: one V4 ground-truth translation, one V4
    misreading, one V4 empty applied list and one V2.  The legacy reading counts
    all four; the content rule drops the ground-truth row; the lower bound keeps
    the V4 misreading and the V2 row, because it narrows V4 and V6 alone."""
    e3r = _load("e3_replay")
    entries = [
        _entry(e3r.T_APPLIED_CERT, 2, 140.0, primary_class="V4",
               applied_ops=GOLD, gold_ops=GOLD, trap_ops=TRAP),
        _entry(e3r.T_APPLIED_CERT, 1, 140.0, primary_class="V4",
               applied_ops=TRAP, gold_ops=GOLD, trap_ops=TRAP),
        _entry(e3r.T_APPLIED_UNCERT, 0, 140.0, primary_class="V4",
               applied_ops=[], gold_ops=GOLD, trap_ops=TRAP),
        _entry(e3r.T_APPLIED_CERT, 2, 140.0, primary_class="V2",
               applied_ops=OTHER, gold_ops=GOLD),
    ]
    profile = e3a.profile_cell(entries)
    assert profile["violations_n"] == 4
    assert profile["violation_pass_through"] == pytest.approx(1.0)
    assert profile["violation_pass_through_nonempty"] == pytest.approx(0.75)
    assert profile["violation_pass_through_strict"] == pytest.approx(0.75)
    assert profile["violation_pass_through_strict_nonempty"] == pytest.approx(0.5)
    assert profile["violation_pass_through_fault"] == pytest.approx(0.5)


@pytest.mark.parametrize("headers", ("E7_HEADERS", "T5_HEADERS", "E12_HEADERS"))
def test_the_corrected_columns_sit_beside_the_legacy_ones(e3a, headers):
    """Added, never substituted: both readings must be in every table that
    prints pass-through, so an older artifact stays reproducible."""
    cols = getattr(e3a, headers)
    for name in ("violation_pass_through", "violation_pass_through_nonempty",
                 "violation_pass_through_strict",
                 "violation_pass_through_strict_nonempty",
                 "violation_pass_through_fault"):
        assert name in cols
    assert (cols.index("violation_pass_through_strict")
            == cols.index("violation_pass_through_nonempty") + 1)


def test_dg6_reports_pass_through_under_the_rule_and_reconciles_under_e8(e3a):
    """DG6 runs two fields on pass-through and one on the other two outcomes:
    the E8 reconciliation needs the disposition E8 was built on, and the
    published interval needs the content rule."""
    ei = _load("e3_intervals")
    by_key = {o[0]: o for o in ei.BINARY_OUTCOMES}
    assert set(by_key) == {"false_block", "catch", "passthrough"}
    for key in ("false_block", "catch"):
        _k, _test, _unit, field, field_pub, _better = by_key[key]
        assert field == field_pub
    _k, _test, _unit, field, field_pub, _better = by_key["passthrough"]
    assert (field, field_pub) == ("passed_through", "passed_through_strict")


def test_the_budget_effect_table_orders_both_readings(e3a):
    """The budget-effect figure plots the corrected reading, so E9 has to carry
    it as an outcome metric beside the legacy one."""
    metrics = [m for m, _kind, _get in e3a.E9_METRICS]
    assert "violation_pass_through" in metrics
    assert "violation_pass_through_strict" in metrics
    kinds = {m: k for m, k, _ in e3a.E9_METRICS}
    assert kinds["violation_pass_through_strict"] == "outcome"


# --------------------------------------------------------------------------- #
# The table wiring                                                             #
# --------------------------------------------------------------------------- #
def test_run_test_selects_the_right_unit_for_each_test(e3a):
    """The false-block test must see only benign twins and the catch test only
    labelled violations; V5 and V6 belong to neither, by suite design."""
    e3r = _load("e3_replay")
    by_item = {}
    for item, cls in (("BEN-1", "benign"), ("V1-1", "V1"), ("V5-1", "V5"),
                      ("V6-1", "V6")):
        entry = _entry(e3r.T_REFERRED, 0, 0.0, primary_class=cls)
        entry["item_id"] = item
        by_item[item] = entry
    assert e3a._units(by_item, by_item, "the 96 matched benign twins") == ["BEN-1"]
    assert e3a._units(by_item, by_item, "the 96 labelled violations") == ["V1-1"]
    assert sorted(e3a._units(by_item, by_item, "all 240 items")) == sorted(by_item)


def test_run_test_counts_discordant_pairs_in_the_declared_direction(e3a):
    """``a_only`` is the count where the FIRST system is positive; a swap of the
    two systems must swap the two counts and leave the p-value alone."""
    e3r = _load("e3_replay")
    a, b = {}, {}
    for i in range(6):
        item = "BEN-{}".format(i)
        a[item] = _entry(e3r.T_BLOCKED_FALSE if i < 4 else e3r.T_REFERRED, 0, 0.0)
        b[item] = _entry(e3r.T_BLOCKED_FALSE if i < 1 else e3r.T_REFERRED, 0, 0.0)
        a[item]["item_id"] = b[item]["item_id"] = item
    forward = e3a.run_test(a, b, "mcnemar_false_block",
                           "the 96 matched benign twins", "blocked_false", "A", "B")
    backward = e3a.run_test(b, a, "mcnemar_false_block",
                            "the 96 matched benign twins", "blocked_false", "A", "B")
    assert (forward["a_only"], forward["b_only"]) == (3, 0)
    assert (backward["a_only"], backward["b_only"]) == (0, 3)
    assert forward["both"] == 1 and forward["neither"] == 2
    assert forward["p"] == pytest.approx(backward["p"])
    assert forward["p"] == pytest.approx(0.25)  # 2 * C(3,0) / 8


def test_the_variant_table_is_the_two_by_two_the_freeze_names_plus_the_addition(e3a):
    e3r = _load("e3_replay")
    assert set(e3a.VARIANTS) == set(e3r.FREEZE_VARIANTS) | {"SINGLE-UG"}
    assert e3a.star("SINGLE-UG").endswith("*")
    for variant in e3r.FREEZE_VARIANTS:
        assert not e3a.star(variant).endswith("*")
    assert e3a.VARIANT_GUARDED == {"SINGLE+G": True, "MULTI-G": True,
                                   "MULTI-UG": False, "SINGLE-UG": False}


def test_the_roster_covers_the_six_arms_the_freeze_ran(e3a):
    assert [a["arm"] for a in e3a.ARMS] == [
        "qwen14b", "qwen27b", "openai", "deepseek", "sonnet", "opus"]
    assert [a["repeats"] for a in e3a.ARMS] == [2, 1, 1, 1, 1, 1]


def test_signflip_left_tail_is_a_probability_and_sums_to_one(e3a):
    """The dynamic program is the Wilcoxon branch's only unaudited machinery."""
    ranks = [2, 4, 6, 8]  # doubled ranks 1, 2, 3, 4
    assert e3a._signflip_left_tail(ranks, -1) == pytest.approx(0.0)
    assert e3a._signflip_left_tail(ranks, sum(ranks)) == pytest.approx(1.0)
    # Exactly one of the sixteen patterns puts every rank on the positive side.
    assert e3a._signflip_left_tail(ranks, sum(ranks) - 1) == pytest.approx(15 / 16)


def test_normal_cdf_is_the_standard_normal(e3a):
    assert e3a._normal_cdf(0.0) == pytest.approx(0.5)
    assert e3a._normal_cdf(1.959963984540054) == pytest.approx(0.975, abs=1e-9)
    assert e3a._normal_cdf(-3.0) == pytest.approx(0.5 * math.erfc(3.0 / 2 ** 0.5))
