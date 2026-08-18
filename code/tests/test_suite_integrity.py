"""Properties of the shipped suite artifact (code/suite/v0.1/).

These read the released files rather than rebuilding them, so they check the
thing that will actually be used: the counts, the twin relation, the schema
validity of every operation list, the expected typed errors, and the absence of
any label wording in the instructions.
"""

from __future__ import annotations

import collections
import hashlib
import json
import random
from pathlib import Path

import pytest

from l1adapter import ops as ops_mod
from l1suite import facts as facts_mod
from l1suite import load_suite
from l1suite.checks import assert_raises, label_leaks
from l1suite.checks import CONSTRAINING_OPS
from l1suite.codes import ADAPTER_RAISED, STAGE_OF_CODE
from l1suite.config import MAX_ABS_RELEASE_SHIFT_BH, SUITE_VERSION, SuiteConfig
from l1suite.stats import OP_TYPES, verify_balance

SUITE_DIR = Path(__file__).resolve().parent.parent / "suite" / SUITE_VERSION

pytestmark = pytest.mark.skipif(
    not (SUITE_DIR / "suite.jsonl").is_file(),
    reason="suite v0.1 has not been built (run scripts/build_suite.py)",
)


@pytest.fixture(scope="module")
def suite():
    return load_suite(SUITE_DIR / "suite.jsonl")


@pytest.fixture(scope="module")
def manifest():
    return json.loads((SUITE_DIR / "manifest.json").read_text())


# --------------------------------------------------------------------------- #
# Shape                                                                        #
# --------------------------------------------------------------------------- #
def test_the_suite_holds_two_thousand_items(suite):
    assert len(suite) == 2000


def test_the_building_stratum_is_the_400_order_replay_cell(suite):
    strata = {r["instance"]["stratum"] for r in suite}
    assert strata == {"c09_storm2_w80", "c10_storm2_w80", "c10_replay_400"}
    for r in suite:
        if r["instance"]["stratum"] == "c10_replay_400":
            assert r["instance"]["size"] == "400"


def test_the_shipped_version_is_the_configured_one(suite):
    assert {r["suite_version"] for r in suite} == {SUITE_VERSION}
    assert (SUITE_DIR.parent / "v0.1" / "suite.jsonl").is_file(), "v0.1 kept for the record"


def test_per_class_counts_match_the_configured_sizes(suite):
    counts = collections.Counter(r["primary_class"] for r in suite)
    assert counts == {
        "benign": 800, "V1": 160, "V2": 200, "V3": 220, "V4": 220, "V5": 200, "V6": 200,
    }


def test_per_set_counts_match_the_corpus_design(suite):
    counts = collections.Counter(r["set"] for r in suite)
    assert counts == {"benign": 800, "violation": 800, "ambiguity": 200, "adversarial": 200}


def test_item_ids_are_unique_and_the_file_is_sorted(suite):
    ids = [r["item_id"] for r in suite]
    assert len(set(ids)) == len(ids)
    assert ids == sorted(ids)


def test_the_recorded_hash_matches_the_file(manifest):
    blob = (SUITE_DIR / "suite.jsonl").read_bytes()
    assert hashlib.sha256(blob).hexdigest() == manifest["artifacts"]["suite.jsonl"]["sha256"]


def test_all_balance_checks_pass_on_the_shipped_file(suite):
    verify_balance(suite, SuiteConfig())


# --------------------------------------------------------------------------- #
# Twins                                                                        #
# --------------------------------------------------------------------------- #
def test_every_violation_has_exactly_one_benign_twin(suite):
    by_id = {r["item_id"]: r for r in suite}
    twinned = [r for r in suite if r["primary_class"] in ("V1", "V2", "V3", "V4")]
    assert len(twinned) == 800
    partners = [r["twin_id"] for r in twinned]
    assert len(set(partners)) == 800
    for r in twinned:
        twin = by_id[r["twin_id"]]
        assert twin["primary_class"] == "benign"
        assert twin["twin_id"] == r["item_id"]


def test_twins_share_the_instance_episode_and_surface_form(suite):
    by_id = {r["item_id"]: r for r in suite}
    for r in suite:
        if r["primary_class"] not in ("V1", "V2", "V3", "V4"):
            continue
        twin = by_id[r["twin_id"]]
        assert twin["instance"] == r["instance"]
        assert twin["episode"] == r["episode"]
        assert twin["variant_id"] == r["variant_id"]
        assert twin["register"] == r["register"]
        assert twin["subclass"] == r["subclass"]


def test_a_twin_pair_never_carries_the_same_instruction(suite):
    by_id = {r["item_id"]: r for r in suite}
    for r in suite:
        if r["primary_class"] in ("V1", "V2", "V3", "V4"):
            assert by_id[r["twin_id"]]["instruction"] != r["instruction"], r["item_id"]


def test_every_mutation_records_a_real_change(suite):
    for r in suite:
        if r["primary_class"] in ("V1", "V2", "V3", "V4", "benign"):
            assert r["mutation"]["kind"]
            assert r["mutation"]["from"] != r["mutation"]["to"], r["item_id"]


def test_ambiguity_and_adversarial_items_have_no_twin(suite):
    for r in suite:
        if r["primary_class"] in ("V5", "V6"):
            assert r["twin_id"] is None


# --------------------------------------------------------------------------- #
# Operations                                                                   #
# --------------------------------------------------------------------------- #
def test_every_operation_list_validates_against_the_frozen_schema(suite):
    for r in suite:
        for field in ("gold_ops", "trap_ops", "literal_ops", "forbidden_ops"):
            proposal = {"operations": r[field]}
            ops_mod.validate_proposal(proposal)
            ops_mod.parse_operations(proposal)


def test_the_frozen_schema_is_the_one_the_manifest_records(manifest):
    assert ops_mod.schema_sha256() == manifest["schema"]["sha256"]
    assert ops_mod.FROZEN_SCHEMA_SHA256 == manifest["schema"]["sha256"]


def test_benign_items_propose_one_to_three_operations(suite):
    for r in suite:
        if r["primary_class"] == "benign":
            assert 1 <= len(r["gold_ops"]) <= 3, r["item_id"]


def test_the_benign_set_covers_all_seven_operations(suite):
    used = collections.Counter()
    for r in suite:
        if r["primary_class"] == "benign":
            used.update(o["op"] for o in r["gold_ops"])
    assert set(used) == set(OP_TYPES)
    assert min(used.values()) >= 20


def test_building_scoped_operations_appear_only_where_buildings_exist(suite):
    for r in suite:
        ops = r["gold_ops"] + r["trap_ops"] + r["literal_ops"] + r["forbidden_ops"]
        if any(o["op"] == "batch" for o in ops):
            assert r["instance"]["track"] == "replay", r["item_id"]


def test_v4_items_carry_a_gold_and_a_different_trap(suite):
    for r in suite:
        if r["primary_class"] == "V4":
            assert r["gold_ops"] and r["trap_ops"]
            assert r["gold_ops"] != r["trap_ops"], r["item_id"]
            assert isinstance(r["quality_visible_candidate"], bool)


def test_refusal_classes_propose_nothing(suite):
    for r in suite:
        if r["primary_class"] in ("V1", "V5"):
            assert r["gold_ops"] == [], r["item_id"]
        if r["primary_class"] == "V6" and r["subclass"] != "embedded_injection":
            assert r["gold_ops"] == [], r["item_id"]


def test_v2_items_ship_the_literal_translation_as_their_gold(suite):
    for r in suite:
        if r["primary_class"] == "V2":
            assert r["literal_ops"] == r["gold_ops"] != []


def test_adversarial_items_name_the_operations_they_try_to_force(suite):
    with_forbidden = [
        r for r in suite if r["primary_class"] == "V6" and r["forbidden_ops"]
    ]
    assert len(with_forbidden) >= 150


# --------------------------------------------------------------------------- #
# Labels                                                                       #
# --------------------------------------------------------------------------- #
def test_no_instruction_names_its_own_label(suite):
    leaks = [(r["item_id"], label_leaks(r["instruction"])) for r in suite]
    assert [x for x in leaks if x[1]] == []


def test_expected_codes_carry_the_guard_stage_they_belong_to(suite):
    for r in suite:
        if r["expected_violation"]:
            assert r["expected_stage"] == STAGE_OF_CODE[r["expected_violation"]]
        else:
            assert r["expected_stage"] is None


def test_v1_items_split_into_decoder_absorbable_and_guard_requiring(suite):
    split = collections.Counter(
        r["v1_decodability"] for r in suite if r["primary_class"] == "V1"
    )
    assert split["decoder_absorbable"] >= 20
    assert split["guard_requiring"] >= 100
    assert split["decoder_absorbable"] + split["guard_requiring"] == 160


def test_decoder_absorbable_items_ship_no_literal_operations(suite):
    for r in suite:
        if r["v1_decodability"] == "decoder_absorbable":
            assert r["literal_ops"] == []
            assert r["expected_violation"] == "SchemaViolation"
            assert r["notes"]


def test_out_of_range_items_really_exceed_the_declared_bound(suite):
    items = [r for r in suite if r["subclass"] == "out_of_range_shift" and r["primary_class"] == "V1"]
    assert items
    for r in items:
        shifts = [abs(o["release_shift_bh"]) for o in r["literal_ops"]]
        assert max(shifts) > MAX_ABS_RELEASE_SHIFT_BH


def test_v3_items_are_candidates_with_a_score_and_no_severity_yet(suite):
    v3 = [r for r in suite if r["primary_class"] == "V3"]
    assert all(r["v3_candidate"] for r in v3)
    assert all(r["severity"] is None for r in v3)
    assert all(isinstance(r["badness"], (int, float)) for r in v3)


def test_v3_candidates_degrade_the_schedule_and_their_twins_do_not(suite):
    v3 = [r for r in suite if r["primary_class"] == "V3"]
    benign = [r for r in suite if r["primary_class"] == "benign"]
    v3_hits = sum(1 for r in v3 if r["badness"] > 1e-9) / len(v3)
    benign_hits = sum(1 for r in benign if (r["badness"] or 0) > 1e-9) / len(benign)
    assert v3_hits >= 0.90, "V3 positive-badness share is {:.1%}".format(v3_hits)
    assert benign_hits < 0.05


def test_every_v3_item_imposes_a_dispatch_constraint(suite):
    """Ruling 1: an item that only edits fields cannot degrade a schedule."""
    for r in suite:
        if r["primary_class"] == "V3":
            assert any(o["op"] in CONSTRAINING_OPS for o in r["gold_ops"]), r["item_id"]


def test_field_only_operations_score_exactly_zero_degradation(suite):
    for r in suite:
        if r["badness"] is None or not r["gold_ops"]:
            continue
        if not any(o["op"] in CONSTRAINING_OPS for o in r["gold_ops"]):
            assert r["badness"] == 0.0, r["item_id"]
            if "reference_from" in r["metrics"]:
                assert r["metrics"]["reference_from"] == "identical_by_construction"


def test_the_quality_visible_share_of_v4_is_reported_and_non_trivial(suite):
    v4 = [r for r in suite if r["primary_class"] == "V4"]
    visible = [r for r in v4 if r["quality_visible_candidate"]]
    assert 0.1 <= len(visible) / len(v4) <= 0.9
    for r in visible:
        assert r["metrics"]["badness_trap_minus_gold"] > 0


def test_the_objective_shifting_trap_type_exists_and_is_field_only(suite):
    rows = [
        r for r in suite
        if r["subclass"] == "objective_shifting" and r["primary_class"] == "V4"
    ]
    assert len(rows) >= 30
    for r in rows:
        assert [o["op"] for o in r["trap_ops"]] == ["set_priority"]
        assert r["metrics"]["badness_trap"] == 0.0
    twins = [r for r in suite if r["subclass"] == "objective_shifting"
             and r["primary_class"] == "benign"]
    assert len(twins) == len(rows)


def test_no_item_pairs_a_freeze_with_a_precedence_edge_out_of_it(suite):
    """That combination can exhaust the adapter's event loop (see the report)."""
    for r in suite:
        for field in ("gold_ops", "trap_ops", "literal_ops"):
            ops = r[field]
            frozen = {o["order_id"] for o in ops if o["op"] == "freeze"}
            frozen |= set(r["episode"]["frozen_seed"])
            for o in ops:
                if o["op"] == "reorder":
                    pred = o["order_id"] if o["relation"] == "before" else o["ref_order_id"]
                    assert pred not in frozen, (r["item_id"], field)


# --------------------------------------------------------------------------- #
# Provenance and re-verification against the environment                       #
# --------------------------------------------------------------------------- #
def test_every_item_names_a_real_instance_of_a_declared_stratum(suite, manifest):
    pool = manifest["instance_pool"]
    for r in suite:
        assert r["instance"]["file"] in pool[r["instance"]["stratum"]]
        assert r["episode"]["rule"] == "atc" and r["episode"]["seed"] == 0


def test_referenced_orders_exist_on_the_items_own_instance(suite):
    rng = random.Random(4)
    for r in rng.sample(suite, 40):
        f = facts_mod.facts_for(
            r["instance"]["stratum"],
            [p.name for p in facts_mod.pool(r["instance"]["stratum"])].index(
                r["instance"]["file"]
            ),
        )
        for oid in r["referenced"]["order_ids"]:
            assert oid in f.by_id, (r["item_id"], oid)
        for b in r["referenced"]["buildings"]:
            assert b in set(f.buildings())


def test_the_standing_frozen_set_is_present_exactly_where_it_is_needed(suite):
    needing = {"frozen_order_edit", "not_frozen", "embedded_injection"}
    for r in suite:
        if r["subclass"] in needing:
            assert len(r["episode"]["frozen_seed"]) == 3, r["item_id"]
        elif r["primary_class"] != "benign" or r["subclass"] not in needing:
            pass


def test_v2_literal_operations_raise_the_expected_typed_error(suite):
    rng = random.Random(7)
    v2 = [r for r in suite if r["primary_class"] == "V2"]
    by_sub = {}
    for r in v2:
        by_sub.setdefault(r["subclass"], []).append(r)
    checked = 0
    for sub, rows in sorted(by_sub.items()):
        for r in rng.sample(rows, min(3, len(rows))):
            idx = [p.name for p in facts_mod.pool(r["instance"]["stratum"])].index(
                r["instance"]["file"]
            )
            f = facts_mod.facts_for(r["instance"]["stratum"], idx)
            out = assert_raises(
                r["item_id"], f, r["literal_ops"], r["expected_violation"],
                r["episode"]["frozen_seed"],
            )
            assert out["checked"] == r["expected_violation"]
            assert out["raised_by"] == ADAPTER_RAISED[r["expected_violation"]]
            checked += 1
    assert checked >= 12


def test_v1_guard_requiring_items_raise_their_code_too(suite):
    rng = random.Random(9)
    rows = [
        r for r in suite
        if r["primary_class"] == "V1" and r["v1_decodability"] == "guard_requiring"
        and r["expected_violation"] in ADAPTER_RAISED
    ]
    for r in rng.sample(rows, 8):
        idx = [p.name for p in facts_mod.pool(r["instance"]["stratum"])].index(
            r["instance"]["file"]
        )
        f = facts_mod.facts_for(r["instance"]["stratum"], idx)
        assert_raises(
            r["item_id"], f, r["literal_ops"], r["expected_violation"],
            r["episode"]["frozen_seed"],
        )


def test_instruction_lengths_are_within_a_supervisor_message_range(suite):
    for r in suite:
        assert 10 <= r["instruction_chars"] <= 400, r["item_id"]
        assert r["instruction_words"] >= 3
        assert r["instruction"] == r["instruction"].strip()


def test_all_three_registers_are_represented_in_every_class(suite):
    per_class = {}
    for r in suite:
        per_class.setdefault(r["primary_class"], set()).add(r["register"])
    for cls, regs in per_class.items():
        assert regs == {"formal", "terse", "conversational"}, cls


def test_almost_every_instruction_is_distinct(suite):
    texts = [r["instruction"] for r in suite]
    assert len(set(texts)) >= 0.95 * len(texts)


def test_the_shipped_audit_sample_is_a_tenth_of_the_suite(suite):
    import csv

    with open(SUITE_DIR / "audit_sample.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert 0.09 * len(suite) <= len(rows) <= 0.12 * len(suite)
    ids = {r["item_id"] for r in rows}
    assert ids <= {r["item_id"] for r in suite}
    groups = {(r["set"], r["primary_class"], r["subclass"]) for r in suite}
    assert {(r["set"], r["primary_class"], r["subclass"]) for r in rows} == groups
