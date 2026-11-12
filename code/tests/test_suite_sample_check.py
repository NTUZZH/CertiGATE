"""Tests for the second-checker workbook pack and scorer."""

from __future__ import annotations

import collections
import csv
import json
import sys
from pathlib import Path

import pytest
from openpyxl import load_workbook

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import suite_sample_check_pack as pack  # noqa: E402
import suite_sample_check_score as score  # noqa: E402

SUITE_DIR = Path(__file__).resolve().parents[1] / "suite" / "v0.2"
CLASS_COUNTS = {"benign": 77, "V1": 16, "V2": 19, "V3": 21, "V4": 21, "V5": 20, "V6": 20}


@pytest.fixture(scope="module")
def sample():
    return pack.load_sample(SUITE_DIR / "audit_sample.csv")


@pytest.fixture(scope="module")
def suite():
    return pack.load_suite(SUITE_DIR / "suite.jsonl")


@pytest.fixture(scope="module")
def workbook_path(tmp_path_factory):
    out = tmp_path_factory.mktemp("pack") / "Suite_Sample_Check.xlsx"
    import subprocess
    subprocess.run([sys.executable, str(SCRIPTS / "suite_sample_check_pack.py"), "--out", str(out)],
                   check=True, capture_output=True)
    return out


def test_row_count_and_classes(sample):
    assert len(sample) == 194
    assert dict(collections.Counter(r["primary_class"] for r in sample)) == CLASS_COUNTS


def test_every_item_and_twin_joins(sample, suite):
    for r in sample:
        assert r["item_id"] in suite
        if r["twin_id"]:
            assert r["twin_id"] in suite


def test_workbook_structure(workbook_path, sample):
    wb = load_workbook(workbook_path)
    assert wb.sheetnames == ["Instructions", "Sample"]
    ws = wb["Sample"]
    assert [c.value for c in ws[1]] == pack.HEADERS
    assert ws.max_row == 195
    assert ws.freeze_panes == "B2"
    assert [ws.cell(row=i, column=1).value for i in range(2, 196)] == [r["item_id"] for r in sample]
    # data validation on the five verdict columns
    ranges = " ".join(str(rng) for dv in ws.data_validations.dataValidation for rng in dv.sqref.ranges)
    for col in "LMNOP":
        assert f"{col}2:{col}195" in ranges
    # Instructions sheet mentions the sample size and the four questions
    text = " ".join(str(c.value) for row in wb["Instructions"].iter_rows() for c in row if c.value)
    for needle in ("194", "9.7%", "2,000", "Q1.", "Q2.", "Q3.", "Q4.", "defect", "n.a.", "alone"):
        assert needle in text


def test_na_rules_and_twin_text(workbook_path, sample, suite):
    ws = load_workbook(workbook_path)["Sample"]
    for i, s in enumerate(sample, start=2):
        row = [c.value for c in ws[i]]
        twin_txt, mut, trap, code = row[9], row[10], row[7], row[8]
        q1, q2, q3, q4 = row[11:15]
        assert row[5] == suite[s["item_id"]]["instruction"]
        if s["twin_id"]:
            assert twin_txt == suite[s["twin_id"]]["instruction"]
            assert mut != "n.a." and q3 is None
        else:
            assert s["primary_class"] in ("V5", "V6")
            assert twin_txt == mut == q3 == "n.a."
        if s["trap_operations"]:
            assert trap == s["trap_operations"] and q2 is None
        else:
            assert trap == q2 == "n.a."
        if s["expected_violation"]:
            assert code == s["expected_violation"] and q4 is None
        else:
            assert code == q4 == "n.a."
        assert q1 is None and row[15] is None and row[16] is None


def test_no_tool_or_path_traces(workbook_path):
    wb = load_workbook(workbook_path)
    text = " ".join(str(c.value) for ws in wb for row in ws.iter_rows() for c in row if c.value).lower()
    for bad in ("claude", "anthropic", "gpt", "gemini", "opus", "sonnet", "/home/", "/tmp/"):
        assert bad not in text, bad
    assert not wb.properties.creator


def _fill(path: Path, out: Path, defects: dict[str, list[str]]):
    """Fill every applicable cell with OK; mark the given items (id -> questions) as defect."""
    wb = load_workbook(path)
    ws = wb["Sample"]
    for i in range(2, ws.max_row + 1):
        iid = ws.cell(row=i, column=1).value
        bad = defects.get(iid, [])
        for k, q in enumerate(["Q1", "Q2", "Q3", "Q4"]):
            if ws.cell(row=i, column=12 + k).value is None:
                ws.cell(row=i, column=12 + k).value = "defect" if q in bad else "OK"
        ws.cell(row=i, column=16).value = "defect" if bad else "OK"
        if bad:
            ws.cell(row=i, column=17).value = f"synthetic note for {iid}"
    wb.save(out)


def test_scorer_on_synthetic_copy(workbook_path, sample, tmp_path):
    first = lambda c: next(r["item_id"] for r in sample if r["primary_class"] == c)
    v4 = [r["item_id"] for r in sample if r["primary_class"] == "V4"]
    defects = {
        first("benign"): ["Q1"],
        v4[0]: ["Q2"],
        v4[1]: ["Q1", "Q3"],
        first("V1"): ["Q4"],
        first("V6"): ["Q1"],
    }
    filled = tmp_path / "filled.xlsx"
    _fill(workbook_path, filled, defects)
    res = score.score(score.read_workbook(filled))

    assert res["n_rows"] == 194
    assert res["problems"] == []
    assert res["agreement"]["k"] == 189 and res["agreement"]["n"] == 194
    assert res["agreement"]["p"] == pytest.approx(189 / 194)
    assert res["agreement_by_class"]["V4"]["k"] == 19 and res["agreement_by_class"]["V4"]["n"] == 21
    assert res["agreement_by_class"]["benign"]["k"] == 76
    assert res["agreement_by_class"]["V3"]["k"] == 21
    assert res["per_class"]["V4"]["Q2_defect"] == 1 and res["per_class"]["V4"]["Q1_defect"] == 1
    assert res["per_class"]["V1"]["Q4_defect"] == 1
    # question applicability: Q2 applies to V4 only, Q3 to 154 rows, Q4 to 35 rows (V1 and V2)
    assert res["agreement_by_question"]["Q2"]["n"] == 21
    assert res["agreement_by_question"]["Q3"]["n"] == 154
    assert res["agreement_by_question"]["Q4"]["n"] == 35
    assert res["agreement_by_question"]["Q1"]["k"] == 194 - 3
    assert res["per_question"]["Q1"]["defect"] == 3
    assert {d["item_id"] for d in res["defects"]} == set(defects)
    assert all(d["note"] for d in res["defects"])
    assert res["kappa"] == pytest.approx(0.0)
    text = score.report(res)
    assert "189/194" in text and "synthetic note" in text


def test_scorer_all_ok_and_incomplete(workbook_path, tmp_path):
    filled = tmp_path / "ok.xlsx"
    _fill(workbook_path, filled, {})
    res = score.score(score.read_workbook(filled))
    assert res["agreement"]["k"] == res["agreement"]["n"] == 194
    assert res["kappa"] is None and res["defects"] == []
    # blank workbook: every applicable cell reported as a problem, nothing scored
    res0 = score.score(score.read_workbook(workbook_path))
    assert res0["agreement"]["n"] == 0 and len(res0["problems"]) > 194


def test_scorer_flags_defect_without_note(workbook_path, sample, tmp_path):
    iid = sample[0]["item_id"]
    filled = tmp_path / "nonote.xlsx"
    _fill(workbook_path, filled, {iid: ["Q1"]})
    wb = load_workbook(filled)
    wb["Sample"].cell(row=2, column=17).value = None
    wb.save(filled)
    res = score.score(score.read_workbook(filled))
    assert any("defect without a note" in p for p in res["problems"])
