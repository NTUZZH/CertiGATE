"""The generator: planning, determinism, self-checks, and the written artifacts."""

from __future__ import annotations

import csv
import hashlib
import json

import pytest

from l1adapter import errors as adapter_errors
from l1suite import build_suite, load_suite
from l1suite.checks import SuiteBuildError, assert_raises, assert_schema_valid
from l1suite.config import SuiteConfig, smoke_config
from l1suite.generate import allocate, plan
from l1suite.stats import verify_balance
from l1suite import facts as facts_mod


# --------------------------------------------------------------------------- #
# Planning                                                                     #
# --------------------------------------------------------------------------- #
def test_allocation_conserves_the_count():
    for n in (1, 3, 7, 60, 220):
        alloc = allocate(n, {"a": 0.55, "b": 0.2, "c": 0.25})
        assert len(alloc) == n


def test_allocation_is_deterministic_and_weight_ordered():
    a = allocate(100, {"a": 0.55, "b": 0.2, "c": 0.25})
    b = allocate(100, {"a": 0.55, "b": 0.2, "c": 0.25})
    assert a == b
    assert a.count("a") == 55 and a.count("c") == 25 and a.count("b") == 20


def test_a_single_item_quota_lands_in_the_heaviest_stratum():
    assert allocate(1, {"a": 0.55, "b": 0.2, "c": 0.25}) == ["a"]


def test_the_plan_matches_the_configured_totals():
    config = SuiteConfig()
    specs = plan(config)
    n_pairs = sum(q.count for q in config.pairs)
    n_singles = sum(q.count for q in config.singles)
    assert len(specs) == n_pairs + n_singles
    assert sum(1 for s in specs if s.kind == "pair") == n_pairs


def test_the_configured_sizes_are_the_orchestrator_fixed_ones():
    config = SuiteConfig()
    per_class = {}
    from l1suite.templates import FAMILIES

    for q in config.pairs:
        per_class[FAMILIES[q.family_id].primary_class] = (
            per_class.get(FAMILIES[q.family_id].primary_class, 0) + q.count
        )
    for q in config.singles:
        per_class[FAMILIES[q.family_id].primary_class] = (
            per_class.get(FAMILIES[q.family_id].primary_class, 0) + q.count
        )
    assert per_class == {"V1": 160, "V2": 200, "V3": 220, "V4": 220, "V5": 200, "V6": 200}
    assert sum(q.count for q in config.pairs) == 800


def test_the_config_fingerprint_changes_with_the_seed():
    assert SuiteConfig().fingerprint() != SuiteConfig(global_seed=7).fingerprint()


# --------------------------------------------------------------------------- #
# A small end-to-end build                                                     #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def small_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("suite_a")
    summary = build_suite(smoke_config(), out_dir=out)
    return summary, out


def test_the_small_build_produces_the_four_artifacts(small_build):
    _, out = small_build
    for name in ("suite.jsonl", "manifest.json", "stats.md", "audit_sample.csv"):
        assert (out / name).is_file()


def test_rebuilding_the_same_config_is_byte_identical(small_build, tmp_path):
    summary, out = small_build
    again = build_suite(smoke_config(), out_dir=tmp_path / "again")
    assert again["suite_sha256"] == summary["suite_sha256"]
    first = (out / "suite.jsonl").read_bytes()
    second = (tmp_path / "again" / "suite.jsonl").read_bytes()
    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()


def test_a_different_seed_produces_a_different_suite(small_build, tmp_path):
    summary, _ = small_build
    other = build_suite(smoke_config(seed=99), out_dir=tmp_path / "other")
    assert other["suite_sha256"] != summary["suite_sha256"]
    assert other["items"] == summary["items"]


def test_the_manifest_records_the_frozen_schema_hash(small_build):
    _, out = small_build
    manifest = json.loads((out / "manifest.json").read_text())
    from l1adapter import ops as ops_mod

    assert manifest["schema"]["sha256"] == ops_mod.FROZEN_SCHEMA_SHA256
    assert manifest["schema"]["version"] == "l1-adjustments-1.0.0"


def test_the_manifest_carries_the_config_seed_and_the_artifact_hash(small_build):
    summary, out = small_build
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["config"]["global_seed"] == smoke_config().global_seed
    assert manifest["artifacts"]["suite.jsonl"]["sha256"] == summary["suite_sha256"]
    assert manifest["config_fingerprint"] == smoke_config().fingerprint()


def test_the_manifest_holds_no_timestamp_so_rebuilds_compare(small_build):
    import re

    _, out = small_build
    text = (out / "manifest.json").read_text().lower()
    for word in ("timestamp", "generated_at", "built_at", "hostname", "username"):
        assert word not in text
    assert re.search(r"\d{4}-\d{2}-\d{2}t?\d{0,2}", text) is None


def test_the_manifest_lists_the_open_items_for_the_guard_pass(small_build):
    _, out = small_build
    manifest = json.loads((out / "manifest.json").read_text())
    assert len(manifest["open_items_for_the_guard_pass"]) >= 3


def test_the_audit_sample_covers_every_stratum_of_the_suite(small_build):
    """At full scale this is a tenth; at smoke scale every group keeps one row."""
    summary, out = small_build
    with open(out / "audit_sample.csv") as fh:
        rows = list(csv.DictReader(fh))
    records = load_suite(out / "suite.jsonl")
    groups = {(r["set"], r["primary_class"], r["subclass"]) for r in records}
    sampled = {(r["set"], r["primary_class"], r["subclass"]) for r in rows}
    assert sampled == groups
    assert len(rows) <= summary["items"]
    assert all(r["instruction"] for r in rows)
    assert "author_verdict" in rows[0]


def test_the_audit_sample_renders_operations_in_words(small_build):
    _, out = small_build
    with open(out / "audit_sample.csv") as fh:
        rows = list(csv.DictReader(fh))
    benign = [r for r in rows if r["primary_class"] == "benign"]
    assert benign and all(r["gold_operations"] for r in benign)
    refusals = [r for r in rows if r["primary_class"] in ("V1", "V5")]
    assert all("no operation" in r["gold_operations"] for r in refusals)


def test_the_balance_checks_run_inside_the_build(small_build):
    summary, out = small_build
    records = load_suite(out / "suite.jsonl")
    verify_balance(records, smoke_config())
    assert summary["balance"]["pairs"] == sum(
        1 for r in records if r["primary_class"] in ("V1", "V2", "V3", "V4")
    )


def test_stats_md_reports_the_length_distribution(small_build):
    _, out = small_build
    text = (out / "stats.md").read_text()
    assert "Instruction length over the whole suite" in text
    assert "Coverage matrix" in text
    assert "badness" in text


# --------------------------------------------------------------------------- #
# The self-checks themselves                                                   #
# --------------------------------------------------------------------------- #
def test_schema_validation_rejects_an_operation_outside_the_contract():
    with pytest.raises(SuiteBuildError):
        assert_schema_valid("x", "gold_ops", [{"op": "delete_order", "order_id": "W1"}])


def test_schema_validation_rejects_an_enum_value_outside_the_vocabulary():
    with pytest.raises(SuiteBuildError):
        assert_schema_valid("x", "gold_ops", [{"op": "pin_next", "order_id": "W1", "trade": "C20"}])


def test_expected_error_assertion_fails_when_the_wrong_error_is_raised():
    f = facts_mod.facts_for("c09_storm2_w80", 0)
    ops = [{"op": "reassign_window", "order_id": "not-an-order", "release_shift_bh": 8.0}]
    assert_raises("x", f, ops, "DanglingOrderID")
    with pytest.raises(SuiteBuildError):
        assert_raises("x", f, ops, "NotFrozen")


def test_an_out_of_range_shift_is_a_guard_only_code_the_adapter_accepts():
    f = facts_mod.facts_for("c09_storm2_w80", 0)
    oid = f.instance["work_orders"][0]["id"]
    ops = [{"op": "reassign_window", "order_id": oid, "release_shift_bh": 480.0}]
    out = assert_raises("x", f, ops, "ArgumentOutOfRange")
    assert out["raised_by"] is None
    with pytest.raises(SuiteBuildError):
        assert_raises(
            "x", f,
            [{"op": "reassign_window", "order_id": oid, "release_shift_bh": 8.0}],
            "ArgumentOutOfRange",
        )


def test_a_cycle_is_reported_from_dispatch_not_from_apply():
    f = facts_mod.facts_for("c09_storm2_w80", 0)
    a, b = (w["id"] for w in f.instance["work_orders"][:2])
    ops = [
        {"op": "reorder", "order_id": a, "relation": "before", "ref_order_id": b},
        {"op": "reorder", "order_id": b, "relation": "before", "ref_order_id": a},
    ]
    out = assert_raises("x", f, ops, "CyclicPrecedence")
    assert out["raised_by"] == "dispatch"


def test_adapter_errors_used_by_the_suite_all_exist():
    for name in ("DanglingOrderID", "DanglingBuildingID", "UnknownTrade",
                 "TradeMismatch", "FrozenWindowConflict", "NotFrozen", "CyclicPrecedence"):
        assert issubclass(getattr(adapter_errors, name), adapter_errors.AdapterError)
