"""The suite acceptance gate runner: selection, refusals, and the criterion."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

CODE_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def gate():
    spec = importlib.util.spec_from_file_location(
        "suite_gate", CODE_DIR / "scripts" / "suite_gate.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def rows(gate):
    if not gate.SUITE_PATH.exists():  # pragma: no cover - sibling deliverable
        pytest.skip("suite v0.2 not on disk")
    return gate.load_suite()


def V(terminal):
    return SimpleNamespace(terminal=terminal)


# --------------------------------------------------------------------------- #
# the three refusals                                                           #
# --------------------------------------------------------------------------- #
def test_the_runner_refuses_a_suite_whose_hash_does_not_match(gate, monkeypatch):
    monkeypatch.setattr(gate, "SUITE_SHA256", "0" * 64)
    with pytest.raises(SystemExit, match="REFUSING TO RUN: suite"):
        gate.assert_inputs()


def test_the_runner_refuses_a_schema_whose_hash_does_not_match(gate, monkeypatch):
    monkeypatch.setattr(gate, "SCHEMA_SHA256", "0" * 64)
    with pytest.raises(SystemExit, match="REFUSING TO RUN: schema"):
        gate.assert_inputs()


def test_the_expected_hashes_are_the_published_ones(gate):
    from l1adapter.ops import FROZEN_SCHEMA_SHA256

    assert gate.SCHEMA_SHA256 == FROZEN_SCHEMA_SHA256
    inputs = gate.assert_inputs()
    assert inputs["suite_sha256"] == gate.SUITE_SHA256
    assert inputs["schema_sha256"] == FROZEN_SCHEMA_SHA256


def test_the_pinned_model_snapshot_is_the_one_in_decisions(gate):
    assert gate.MODEL_PATH.endswith("40c069824f4251a91eefaf281ebe4c544efd3e18")
    assert "models--Qwen--Qwen3-14B" in gate.MODEL_PATH


# --------------------------------------------------------------------------- #
# item selection                                                               #
# --------------------------------------------------------------------------- #
def test_the_selection_is_every_v3_every_v4_and_their_twins(gate, rows):
    items = gate.select_items(rows)
    assert len(items) == 880
    assert len({r["item_id"] for r in items}) == 880
    counts = {}
    for r in items:
        counts[r["primary_class"]] = counts.get(r["primary_class"], 0) + 1
    assert counts == {"V3": 220, "V4": 220, "benign": 440}


def test_each_target_is_followed_by_its_own_twin(gate, rows):
    items = gate.select_items(rows)
    for target, twin in zip(items[::2], items[1::2]):
        assert target["primary_class"] in ("V3", "V4")
        assert twin["item_id"] == target["twin_id"]
        assert twin["primary_class"] == "benign"
        assert twin["instance"]["file"] == target["instance"]["file"]


def test_the_mock_sample_covers_all_three_strata(gate, rows):
    sample = gate.sample_items(gate.select_items(rows), 10)
    assert len(sample) == 10
    classes = {r["primary_class"] for r in sample}
    assert classes == {"V3", "V4", "benign"}
    visible = [r for r in sample if r["primary_class"] == "V4"
               and r["quality_visible_candidate"]]
    invisible = [r for r in sample if r["primary_class"] == "V4"
                 and not r["quality_visible_candidate"]]
    assert visible and invisible  # both sides of the V4 split are exercised


def test_the_sample_is_deterministic(gate, rows):
    items = gate.select_items(rows)
    a = [r["item_id"] for r in gate.sample_items(items, 10)]
    b = [r["item_id"] for r in gate.sample_items(items, 10)]
    assert a == b


def test_instances_resolve_from_the_items_own_stratum(gate, rows):
    seen = set()
    for item in gate.select_items(rows):
        stratum = item["instance"]["stratum"]
        if stratum in seen:
            continue
        seen.add(stratum)
        assert gate.instance_path(item).exists()
    assert seen == {"c09_storm2_w80", "c10_storm2_w80", "c10_replay_400"}


# --------------------------------------------------------------------------- #
# the gate criterion, on synthetic verdicts                                    #
# --------------------------------------------------------------------------- #
def test_the_criterion_counts_pass_under_feas_and_block_under_cert(gate):
    targets = ["a", "b", "c", "d", "e"]
    feas = {
        "a": V("applied_uncertified"),   # passed, then blocked on quality  -> counts
        "b": V("applied_uncertified"),   # passed both                      -> no
        "c": V("blocked_feas"),          # already blocked before quality   -> no
        "d": V("execution_failed"),      # never applied                    -> no
        "e": V("applied_uncertified"),   # blocked on schema under cert     -> counts
    }
    cert = {
        "a": V("blocked_qual"),
        "b": V("applied_with_certificate"),
        "c": V("blocked_feas"),
        "d": V("execution_failed"),
        "e": V("blocked_schema"),
    }
    assert gate.separated_ids(targets, feas, cert) == ["a", "e"]


def test_an_instrument_fault_never_counts_as_separation(gate):
    feas = {"x": V("execution_failed")}
    cert = {"x": V("execution_failed")}
    assert gate.separated_ids(["x"], feas, cert) == []


def test_the_terminal_vocabulary_matches_the_guard(gate):
    from l1guard.verdict import APPLIED_STATES, BLOCKED_STATES

    assert set(gate.APPLIED_TERMINALS) == set(APPLIED_STATES)
    assert set(gate.BLOCKED_TERMINALS) == set(BLOCKED_STATES)


# --------------------------------------------------------------------------- #
# translation matching                                                         #
# --------------------------------------------------------------------------- #
def test_exact_match_needs_the_same_operations_in_the_same_order(gate):
    gold = [
        {"op": "set_priority", "order_id": "A", "priority_class": 1},
        {"op": "pin_next", "order_id": "A", "trade": "D30"},
    ]
    assert gate.match_kind(list(gold), gold) == "exact"
    assert gate.match_kind(list(reversed(gold)), gold) == "semantic"
    assert gate.match_kind([gold[0]], gold) == "none"
    assert gate.match_kind(None, gold) == "none"


def test_the_two_relations_of_one_edge_are_semantically_equal(gate):
    gold = [{"op": "reorder", "order_id": "A", "relation": "before", "ref_order_id": "B"}]
    same = [{"op": "reorder", "order_id": "B", "relation": "after", "ref_order_id": "A"}]
    flipped = [{"op": "reorder", "order_id": "B", "relation": "before", "ref_order_id": "A"}]
    assert gate.match_kind(same, gold) == "semantic"
    assert gate.match_kind(flipped, gold) == "none"  # the V4 trap must not score


def test_an_empty_proposal_matches_an_empty_gold(gate):
    assert gate.match_kind([], []) == "exact"
    assert gate.match_kind([], [{"op": "freeze", "order_id": "A"}]) == "none"


# --------------------------------------------------------------------------- #
# the mock                                                                     #
# --------------------------------------------------------------------------- #
def test_the_mock_emits_gold_for_benign_and_v3_and_the_trap_for_v4(gate, rows):
    items = gate.sample_items(gate.select_items(rows), 10)
    outputs = gate.mock_outputs(items)
    for item, text in zip(items, outputs):
        ops = json.loads(text)["operations"]
        expected = item["trap_ops"] if item["primary_class"] == "V4" else item["gold_ops"]
        assert ops == expected


def test_the_mock_can_emit_an_unparseable_output_to_exercise_that_path(gate, rows):
    items = gate.sample_items(gate.select_items(rows), 4)
    outputs = gate.mock_outputs(items, noise=2)
    assert outputs[0].startswith("```json") and outputs[1].startswith("```json")
    assert not outputs[2].startswith("```")


# --------------------------------------------------------------------------- #
# GPU discipline                                                               #
# --------------------------------------------------------------------------- #
def test_the_gpu_condition_is_the_published_one(gate):
    assert gate.MIN_FREE_GIB == 34.0
    assert gate.MAX_FOREIGN_UTIL == 20
    assert gate.GPU_MEM_UTIL <= 0.85


def test_the_gpu_state_reader_reports_a_verdict(gate):
    state = gate.gpu_state()
    assert set(("ok", "condition", "free_gib", "util")) <= set(state)
    assert isinstance(state["ok"], bool)
    if state["free_gib"] is not None:
        expected = state["free_gib"] >= 34.0 and state["util"] < 20
        assert state["ok"] == expected
