"""Template families, surface forms, and the instance facts they select from."""

from __future__ import annotations

import random

import pytest

from l1adapter import ops as ops_mod
from l1suite import facts as facts_mod
from l1suite import phrasing
from l1suite.checks import BANNED_TERMS, label_leaks
from l1suite.config import STRATA_BY_KEY, SuiteConfig
from l1suite.templates import FAMILIES, render

PAIR_FAMILIES = [f for f in FAMILIES.values() if f.kind == "pair"]
SINGLE_FAMILIES = [f for f in FAMILIES.values() if f.kind == "single"]


# --------------------------------------------------------------------------- #
# Family metadata                                                              #
# --------------------------------------------------------------------------- #
def test_every_family_in_the_config_exists_in_the_registry():
    config = SuiteConfig()
    for q in list(config.pair_quotas) + list(config.single_quotas):
        assert q.family_id in FAMILIES


def test_every_family_carries_at_least_three_surface_variants():
    for fam in FAMILIES.values():
        assert len(fam.variants) >= 3, fam.family_id


def test_every_family_covers_all_three_registers():
    for fam in FAMILIES.values():
        registers = {v.register for v in fam.variants}
        assert registers == {"formal", "terse", "conversational"}, fam.family_id


def test_variants_are_interleaved_so_a_small_quota_spans_registers():
    for fam in FAMILIES.values():
        first_three = [v.register for v in fam.variants[:3]]
        assert sorted(first_three) == ["conversational", "formal", "terse"], fam.family_id


def test_variant_ids_are_unique_within_a_family():
    for fam in FAMILIES.values():
        vids = [v.vid for v in fam.variants]
        assert len(vids) == len(set(vids)), fam.family_id


def test_every_family_declares_operations_from_the_frozen_vocabulary():
    for fam in FAMILIES.values():
        for op in tuple(fam.op_types) + tuple(fam.benign_op_types):
            assert op in ops_mod.OP_NAMES, (fam.family_id, op)


def test_building_families_are_the_only_ones_using_batch():
    for fam in FAMILIES.values():
        if "batch" in fam.op_types:
            assert fam.needs_buildings, fam.family_id


def test_pair_families_cover_all_seven_operations_in_their_benign_side():
    covered = set()
    for fam in PAIR_FAMILIES:
        covered.update(fam.benign_op_types or fam.op_types)
    assert covered == set(ops_mod.OP_NAMES)


# --------------------------------------------------------------------------- #
# Drawing on a real instance                                                   #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def storm2_facts():
    return facts_mod.facts_for("c09_storm2_w80", 0)


@pytest.fixture(scope="module")
def replay_facts():
    return facts_mod.facts_for("c10_replay_400", 0)


def _draw(fam, f, seed=1, register="formal"):
    return fam.draw(f, random.Random(seed), register)


def test_every_family_draws_on_a_suitable_instance(storm2_facts, replay_facts):
    for fam in FAMILIES.values():
        f = replay_facts if fam.needs_buildings else storm2_facts
        if fam.family_id.startswith("v1_unstaffed"):
            f = replay_facts if fam.needs_buildings else facts_mod.facts_for("c10_storm2_w80", 0)
        assert _draw(fam, f) is not None, fam.family_id


def test_a_draw_renders_in_every_variant_without_a_missing_slot(storm2_facts, replay_facts):
    for fam in FAMILIES.values():
        f = replay_facts if fam.needs_buildings else storm2_facts
        if fam.family_id.startswith("v1_unstaffed"):
            f = replay_facts if fam.needs_buildings else facts_mod.facts_for("c10_storm2_w80", 0)
        for variant in fam.variants:
            drawn = fam.draw(f, random.Random(3), variant.register)
            assert drawn is not None, fam.family_id
            text = render(variant, drawn.violation.slots)
            # A message may open with a building number or a bracketed console
            # tag, but never with a lower-case word.
            assert text and (text[0].isupper() or text[0].isdigit() or text[0] == "["), (
                fam.family_id, variant.vid, text
            )
            if drawn.benign is not None:
                assert render(variant, drawn.benign.slots)


def test_a_pair_draw_differs_in_exactly_one_recorded_way(storm2_facts, replay_facts):
    for fam in PAIR_FAMILIES:
        f = replay_facts if fam.needs_buildings else storm2_facts
        if fam.family_id.startswith("v1_unstaffed"):
            f = replay_facts if fam.needs_buildings else facts_mod.facts_for("c10_storm2_w80", 0)
        drawn = _draw(fam, f)
        assert drawn.benign is not None, fam.family_id
        assert drawn.mutation.get("kind"), fam.family_id
        assert drawn.mutation.get("from") != drawn.mutation.get("to"), fam.family_id


def test_drawing_twice_with_the_same_seed_gives_the_same_slots(storm2_facts):
    fam = FAMILIES["v3_reorder_block_tight"]
    a = _draw(fam, storm2_facts, seed=11)
    b = _draw(fam, storm2_facts, seed=11)
    assert a.violation.slots == b.violation.slots
    assert a.violation.gold_ops == b.violation.gold_ops


def test_single_families_never_carry_a_benign_twin(storm2_facts):
    for fam in SINGLE_FAMILIES:
        drawn = _draw(fam, storm2_facts)
        assert drawn is not None and drawn.benign is None, fam.family_id


def test_ambiguity_and_injection_items_propose_nothing_except_a_carrier(storm2_facts):
    for fam in SINGLE_FAMILIES:
        drawn = _draw(fam, storm2_facts)
        if fam.family_id == "v6_embedded_injection":
            assert drawn.violation.gold_ops  # the legitimate part of the message
        else:
            assert drawn.violation.gold_ops == ()


# --------------------------------------------------------------------------- #
# Instance facts                                                               #
# --------------------------------------------------------------------------- #
def test_pools_have_the_configured_size():
    for key, stratum in STRATA_BY_KEY.items():
        assert len(facts_mod.pool(key)) == stratum.n_instances


def test_storm2_instances_have_no_buildings_and_replay_does(storm2_facts, replay_facts):
    assert all(w["building"] is None for w in storm2_facts.instance["work_orders"])
    assert all(w["building"] for w in replay_facts.instance["work_orders"])
    assert replay_facts.building_groups(min_members=2)


def test_dangling_order_ids_are_really_absent(storm2_facts, replay_facts):
    for f in (storm2_facts, replay_facts):
        for w in f.instance["work_orders"][:40]:
            bad = f.dangling_order_id(w["id"])
            assert bad not in f.by_id
            assert bad != w["id"]


def test_dangling_building_ids_are_really_absent(replay_facts):
    for b in replay_facts.buildings()[:20]:
        bad = replay_facts.dangling_building_id(b)
        assert bad not in set(replay_facts.buildings())


def test_the_standing_frozen_set_is_the_earliest_work_and_is_stable(storm2_facts):
    frozen = storm2_facts.frozen_seed
    assert len(frozen) == 3
    starts = [storm2_facts.assign[o]["start_bh"] for o in frozen]
    others = [
        a["start_bh"]
        for a in storm2_facts.baseline["assignments"]
        if a["wo"] not in frozen
    ]
    assert max(starts) <= min(others)


def test_queue_state_separates_the_contention_strata(storm2_facts, replay_facts):
    deep = storm2_facts.deep_trades()[0]
    assert storm2_facts.queue_state(deep) == "deep"
    shallow = replay_facts.deep_trades()[0]
    assert replay_facts.queue_state(shallow) in ("shallow", "moderate")


def test_absent_nameable_trades_are_absent_from_the_instance():
    f = facts_mod.facts_for("c10_storm2_w80", 0)
    for trade in f.absent_nameable_trades():
        assert trade not in f.trades
        assert trade in ops_mod.TRADE_VOCABULARY


# --------------------------------------------------------------------------- #
# Surface helpers                                                              #
# --------------------------------------------------------------------------- #
def test_registers_produce_different_surface_forms():
    forms = {phrasing.order_ref("W12", s) for s in ("formal", "terse", "conversational")}
    assert len(forms) == 3


def test_trade_reference_names_a_crew_even_without_a_craft_name():
    assert "electrical" in phrasing.trade_ref("D50", "formal")
    assert phrasing.trade_ref("MISC", "formal") == "the MISC crew"
    assert phrasing.trade_ref("D50", "terse") == "D50"


def test_magnitudes_state_business_hours_in_the_formal_register():
    assert "40 business hours" in phrasing.magnitude(40.0, "formal")
    assert phrasing.magnitude(40.0, "terse") == "40 bh"
    assert phrasing.duration(40.0, "formal") == "40 business hours"


def test_snap_shift_returns_a_natural_amount_above_the_bound():
    assert phrasing.snap_shift(0.0) == 4.0
    assert phrasing.snap_shift(30.0) == 40.0
    assert phrasing.snap_shift(200.0) > 200.0


def test_the_label_leak_detector_catches_its_own_vocabulary():
    assert label_leaks("this is a violation of the schema") == ["violation"]
    assert label_leaks("Please expedite work order W12.") == []
    assert "invalid" in BANNED_TERMS
