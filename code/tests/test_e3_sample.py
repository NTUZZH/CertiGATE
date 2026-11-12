"""The frozen E3 slice: the same draw every time, twins closed, registers kept."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

CODE_DIR = Path(__file__).resolve().parent.parent
for _p in (str(CODE_DIR), str(CODE_DIR / "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import e3_sample  # noqa: E402
import suite_gate as sg  # noqa: E402


@pytest.fixture(scope="module")
def rows():
    if not sg.SUITE_PATH.exists():  # pragma: no cover - sibling deliverable
        pytest.skip("suite v0.2 not on disk")
    return sg.load_suite()


@pytest.fixture(scope="module")
def built(rows):
    return e3_sample.build_slices(rows)


@pytest.fixture(scope="module")
def by_id(rows):
    return {r["item_id"]: r for r in rows}


# --------------------------------------------------------------------------- #
# the largest-remainder split                                                  #
# --------------------------------------------------------------------------- #
def test_the_split_always_sums_to_the_total():
    for total in (0, 1, 7, 24, 30, 33, 96, 120, 300):
        for weights in ([160, 200, 220, 220], [64, 49, 47], [1, 1, 1], [5, 0, 0]):
            assert sum(e3_sample.largest_remainder(total, weights)) == total


def test_a_tie_on_the_remainder_goes_to_the_earlier_position():
    # Two equal weights, one seat to hand out: the first position takes it, so
    # the draw is a function of the inputs and not of dict ordering.
    assert e3_sample.largest_remainder(1, [1, 1]) == [1, 0]
    assert e3_sample.largest_remainder(3, [1, 1]) == [2, 1]


def test_a_zero_weight_never_receives_a_seat():
    assert e3_sample.largest_remainder(10, [1, 0, 1]) == [5, 0, 5]
    assert e3_sample.largest_remainder(10, [0, 0]) == [0, 0]


# --------------------------------------------------------------------------- #
# determinism                                                                  #
# --------------------------------------------------------------------------- #
def test_two_draws_of_the_same_suite_are_the_same_slice(rows, built):
    again = e3_sample.build_slices(rows)
    for name in e3_sample.SLICE_NAMES:
        assert again["slices"][name]["item_ids"] == built["slices"][name]["item_ids"]
        assert again["slices"][name]["sha256"] == built["slices"][name]["sha256"]


def test_the_cell_order_does_not_depend_on_the_order_the_suite_is_read_in(rows):
    shuffled = list(reversed(rows))
    assert (e3_sample.build_slices(shuffled)["slices"]["E3-300"]["item_ids"]
            == e3_sample.build_slices(rows)["slices"]["E3-300"]["item_ids"])


def test_the_draw_order_is_a_keyed_sort_of_the_ids_alone():
    ids = ["V1-0003", "V1-0001", "V1-0002"]
    first = e3_sample.draw_order(ids, "V1", "formal")
    assert first == e3_sample.draw_order(list(reversed(ids)), "V1", "formal")
    assert sorted(first) == sorted(ids)
    # A different cell is a different salt, so the orders are independent.
    assert first != e3_sample.draw_order(ids, "V1", "terse") or len(set(ids)) == 1


# --------------------------------------------------------------------------- #
# composition                                                                  #
# --------------------------------------------------------------------------- #
def test_e3_300_is_the_frozen_composition(built, by_id):
    ids = built["slices"]["E3-300"]["item_ids"]
    assert len(ids) == 300
    assert len(set(ids)) == 300
    counts = {}
    for item_id in ids:
        cls = by_id[item_id]["primary_class"]
        counts[cls] = counts.get(cls, 0) + 1
    assert counts == {"V1": 24, "V2": 30, "V3": 33, "V4": 33, "V5": 30, "V6": 30,
                      "benign": 120}


def test_every_drawn_violation_brings_its_matched_benign_twin(built, by_id):
    ids = built["slices"]["E3-300"]["item_ids"]
    drawn = set(ids)
    violations = [i for i in ids if by_id[i]["primary_class"] in e3_sample.V_CLASSES]
    twins = [i for i in ids if by_id[i]["primary_class"] == "benign"]
    assert len(violations) == 120
    assert len(twins) == 120
    for item_id in violations:
        twin = by_id[item_id]["twin_id"]
        assert twin in drawn, item_id
        assert by_id[twin]["twin_role"] == "benign"
        assert by_id[twin]["twin_id"] == item_id  # the pairing is a bijection
    assert {by_id[i]["twin_id"] for i in violations} == set(twins)


def test_the_refusal_classes_are_drawn_without_twins(built, by_id):
    ids = built["slices"]["E3-300"]["item_ids"]
    refusal = [i for i in ids if by_id[i]["primary_class"] in e3_sample.R_CLASSES]
    assert len(refusal) == 60
    assert all(by_id[i]["twin_id"] is None for i in refusal)


def test_registers_are_proportional_within_every_class(built, by_id):
    ids = built["slices"]["E3-300"]["item_ids"]
    for cls in e3_sample.V_CLASSES + e3_sample.R_CLASSES:
        drawn = [i for i in ids if by_id[i]["primary_class"] == cls]
        got = [sum(1 for i in drawn if by_id[i]["register"] == reg)
               for reg in e3_sample.REGISTERS]
        want = e3_sample.largest_remainder(
            len(drawn),
            [built["register_sizes"][cls][reg] for reg in e3_sample.REGISTERS],
        )
        assert got == want, (cls, got, want)
        assert sum(got) == e3_sample.FROZEN_300[cls]


def test_the_twins_inherit_the_registers_of_the_violations_they_match(built, by_id):
    ids = built["slices"]["E3-300"]["item_ids"]
    for item_id in ids:
        twin = by_id[item_id]["twin_id"]
        if twin:
            assert by_id[twin]["register"] == by_id[item_id]["register"]


# --------------------------------------------------------------------------- #
# the two smaller slices                                                       #
# --------------------------------------------------------------------------- #
def test_the_three_slices_nest(built):
    big = set(built["slices"]["E3-300"]["item_ids"])
    mid = set(built["slices"]["E3-240"]["item_ids"])
    small = set(built["slices"]["E3-CAL-60"]["item_ids"])
    assert small <= mid <= big


def test_the_fallback_and_the_calibration_have_the_frozen_sizes(built, by_id):
    fallback = built["slices"]["E3-240"]
    assert (fallback["n"], fallback["n_violations"], fallback["n_twins"],
            fallback["n_refusal"]) == (240, 96, 96, 48)
    cal = built["slices"]["E3-CAL-60"]
    assert (cal["n"], cal["n_violations"], cal["n_twins"], cal["n_refusal"]) == (
        60, 24, 24, 12)
    for name in ("E3-240", "E3-CAL-60"):
        ids = built["slices"][name]["item_ids"]
        for item_id in ids:
            twin = by_id[item_id]["twin_id"]
            if by_id[item_id]["primary_class"] in e3_sample.V_CLASSES:
                assert twin in set(ids)


# --------------------------------------------------------------------------- #
# the emitted file                                                             #
# --------------------------------------------------------------------------- #
def test_the_file_records_the_sha256_of_every_emitted_list(tmp_path, built, monkeypatch):
    path = tmp_path / "e3_slice.json"
    monkeypatch.setattr(sys, "argv", ["e3_sample.py", "--out", str(path)])
    assert e3_sample.main() == 0
    payload = json.loads(path.read_text())
    for name in e3_sample.SLICE_NAMES:
        ids = payload["slices"][name]["item_ids"]
        assert payload["slices"][name]["sha256"] == e3_sample.list_sha256(ids)
        assert payload["slices"][name]["sha256"] == built["slices"][name]["sha256"]
    assert payload["seed"] == 0
    assert all(payload["nesting"].values())


def test_load_slice_refuses_a_file_that_disagrees_with_the_suite(tmp_path, rows):
    path = tmp_path / "e3_slice.json"
    path.write_text(json.dumps({"slices": {"E3-300": {"sha256": "0" * 64,
                                                      "item_ids": []}}}))
    with pytest.raises(SystemExit):
        e3_sample.load_slice("E3-300", path=path, rows=rows)


def test_load_slice_returns_the_recomputed_ids_when_no_file_exists(tmp_path, rows, built):
    ids = e3_sample.load_slice("E3-300", path=tmp_path / "absent.json", rows=rows)
    assert ids == built["slices"]["E3-300"]["item_ids"]


def test_an_unknown_slice_name_is_a_key_error(rows):
    with pytest.raises(KeyError):
        e3_sample.load_slice("E3-999", rows=rows)
