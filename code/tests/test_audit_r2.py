"""Practitioner audit under protocol v1.2: the pack and the scorer.

Builds the material pack twice into temporary folders (never into the
results tree), checks the balance of the draw, the byte-identity of the two
builds and the recorded dispositions, and runs the scorer on a synthetic set
of five filled workbooks per stage, written to a temporary folder.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

CODE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = CODE_DIR / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SNAPSHOT = Path(((os.environ.get("L1_Y1_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "PaperY-FMScheduling")) + "/data/processed/instances_v10"))
os.environ.setdefault("L1_INSTANCE_ROOT", str(SNAPSHOT))

if not SNAPSHOT.is_dir():  # pragma: no cover - machine without the instance snapshot
    pytest.skip("instances_v10 snapshot not on disk", allow_module_level=True)

import practitioner_audit_r2_pack as PK  # noqa: E402
import practitioner_audit_r2_score as SC  # noqa: E402

REGISTERS = ("formal", "terse", "conversational")
STRATA = ("c09_storm2_w80", "c10_storm2_w80", "c10_replay_400")


@pytest.fixture(scope="module")
def builds(tmp_path_factory):
    out = []
    for name in ("b1", "b2"):
        root = tmp_path_factory.mktemp(name)
        res = PK.build(root / "results", root / "panel", quiet=True)
        out.append((root, res))
    return out


def _draw(root: Path) -> list:
    with open(root / "results" / "draw.csv", newline="") as fh:
        return list(csv.DictReader(fh))


def _files(root: Path) -> dict:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*"))
            if p.is_file()}


# --------------------------------------------------------------------------- #
# The draw                                                                     #
# --------------------------------------------------------------------------- #
def test_draw_balance(builds):
    root, res = builds[0]
    rows = _draw(root)
    assert len(rows) == 30
    assert len({r["item_id"] for r in rows}) == 30
    by_class = Counter(r["class"] for r in rows)
    assert by_class == {"benign": 6, "V3": 6, "V4": 6, "V5": 6, "V6": 6}
    for cls in by_class:
        cc = [r for r in rows if r["class"] == cls]
        assert Counter(r["register"] for r in cc) == {k: 2 for k in REGISTERS}
        assert Counter(r["stratum"] for r in cc) == {k: 2 for k in STRATA}
        assert [(r["register"], r["stratum"]) for r in cc] == list(PK.PATTERN)
    v4 = [r for r in rows if r["class"] == "V4"]
    assert Counter(r["quality_visible"] for r in v4) == {"True": 3, "False": 3}
    for flag in ("True", "False"):
        sub = [r for r in v4 if r["quality_visible"] == flag]
        assert len({r["register"] for r in sub}) == 3
        assert len({r["stratum"] for r in sub}) == 3
    for r in rows:
        if r["class"] == "V3":
            assert float(r["certified_gap"]) > PK.TAU
    assert res["deviations"] == []
    with open(root / "results" / "label_map.csv", newline="") as fh:
        lm = list(csv.DictReader(fh))
    assert sorted(x["label"] for x in lm) == ["C{:02d}".format(i) for i in range(1, 31)]
    assert {x["case_id"] for x in lm} == {r["case_id"] for r in rows}
    # the presentation order is shuffled, not the class order
    assert [x["case_id"] for x in lm] != [r["case_id"] for r in rows]


def test_two_builds_are_byte_identical(builds):
    (r1, a), (r2, b) = builds
    f1, f2 = _files(r1), _files(r2)
    assert sorted(f1) == sorted(f2)
    for k in f1:
        assert f1[k] == f2[k], k
    assert a["n_checks"] == b["n_checks"] > 200


# --------------------------------------------------------------------------- #
# Dispositions                                                                 #
# --------------------------------------------------------------------------- #
def test_dispositions(builds):
    root, res = builds[0]
    rows = {r["case_id"]: r for r in _draw(root)}
    for cid, r in rows.items():
        cls = r["class"]
        if cls == "benign" or (cls == "V4" and r["quality_visible"] == "False"):
            assert r["suite_disposition_v12"] == "apply"
            assert r["guard_terminal_v12"] == "applied_with_certificate"
            assert float(r["certified_gap"]) <= PK.TAU
            assert r["matches_suite"] == "True"
        elif cls == "V3" or cls == "V4":
            assert r["suite_disposition_v12"] == "refer"
            assert r["guard_terminal_v12"] == "referred_with_price"
            assert float(r["certified_gap"]) > PK.TAU
            assert r["matches_suite"] == "True"
        else:
            assert r["suite_disposition_v12"] == "refer"
            assert r["suite_terminal_v12"] == "refuse_or_ask"
            assert r["matches_suite"] == str(r["guard_disposition"] == "refer")
    # every difference is flagged in the README
    readme = (root / "results" / "README.md").read_text()
    for cid, r in rows.items():
        if r["matches_suite"] == "False":
            assert "| {} | {} |".format(cid, r["class"]) in readme
    assert "Build assertions passed: {}.".format(res["n_checks"]) in readme
    # the v1.1 path with no acceptance equals v1.2 on every case (asserted in the build)
    v12 = [c for c in res["cases"]]
    assert all(c["guard"]["terminal_v11_noflag"] == c["guard"]["terminal_v12"] for c in v12)
    # Stage B referral records carry the price, the tolerance and the anchor gap
    with open(root / "results" / "stage_b.jsonl") as fh:
        sb = [json.loads(line) for line in fh]
    for rec in sb:
        if rec["terminal"] == "referred_with_price":
            assert rec["referral"]["tau"] == PK.TAU
            assert rec["referral"]["price"] > PK.TAU
            assert rec["referral"]["waits_for_approver"] is True
            assert "waits for the approver" in rec["record"]
        elif rec["terminal"] == "applied_with_certificate":
            assert rec["certificate"]["gap"] <= PK.TAU
        else:
            assert rec["findings"]


def test_stage_a_is_blind(builds):
    root, res = builds[0]
    text = (root / "results" / "stage_a.jsonl").read_text().lower()
    for w in ("benign", "referred", "certificate", "blocked", "trap", "gold", "guard",
              "\"v3", "\"v4", "\"v5", "\"v6"):
        assert w not in text, w
    for c in res["cases"]:
        assert c["item_id"].lower() not in text
    from openpyxl import load_workbook

    wb = load_workbook(root / "panel" / "Stage_A_Workbook.xlsx")
    assert wb.sheetnames == ["Instructions", "Cases"]
    ws = wb["Cases"]
    header = [c.value for c in ws[1]]
    assert header == ["Case", "Board", "Instruction", "Board context", "Candidate handling",
                      "Realism (1-4)", "Disposition", "Fidelity (1-4)", "Comment"]
    assert ws.max_row == 31
    assert ws.freeze_panes == "B2"
    kinds = sorted(dv.formula1 for dv in ws.data_validations.dataValidation)
    assert kinds == ['"1,2,3,4"', '"apply,reject,refer"']
    wb_b = load_workbook(root / "panel" / "Stage_B_Workbook.xlsx")
    assert [c.value for c in wb_b["Cases"]["A"]][1:] == [c.value for c in ws["A"]][1:]


# --------------------------------------------------------------------------- #
# Scorer                                                                       #
# --------------------------------------------------------------------------- #
def test_fleiss_kappa_known_values():
    # Fleiss (1971) style worked example: 10 subjects, 14 raters, 5 categories.
    table = np.array([
        [0, 0, 0, 0, 14], [0, 2, 6, 4, 2], [0, 0, 3, 5, 6], [0, 3, 9, 2, 0],
        [2, 2, 8, 1, 1], [7, 7, 0, 0, 0], [3, 2, 6, 3, 0], [2, 5, 3, 2, 2],
        [6, 5, 2, 1, 0], [0, 2, 2, 3, 7]])
    assert SC.fleiss_kappa(table) == pytest.approx(0.210, abs=5e-4)
    assert SC.fleiss_kappa(np.array([[5, 0, 0], [0, 5, 0], [0, 0, 5]])) == pytest.approx(1.0)
    assert np.isnan(SC.fleiss_kappa(np.array([[5, 0, 0], [5, 0, 0]])))


def test_scorer_on_synthetic_workbooks(builds, tmp_path):
    root, _ = builds[0]
    pack, panel = root / "results", root / "panel"
    syn = tmp_path / "synthetic_in"
    paths = SC.make_synthetic(syn, pack, panel, seed=7)
    assert len(paths) == 10
    out = tmp_path / "synthetic_out"
    res = SC.score(syn, out, pack, quiet=True)
    assert res["synthetic"] is True
    assert (out / "SYNTHETIC_TEST_DATA.txt").exists()
    assert "SYNTHETIC TEST DATA" in (out / "scores.md").read_text()
    with open(out / "cases.csv", newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == SC.CASES_HEADER
    assert len(rows) == 31
    for r in rows[1:]:
        assert int(r[5]) + int(r[6]) + int(r[7]) == 5
        for v in r[8:]:
            assert 0 <= int(v) <= 5
    m = res["measures"]
    p = m["pooled"]
    for k in ("realism", "fidelity", "clarity", "action", "agree_suite", "agree_guard"):
        s = p[k]
        assert s["lo"] <= s["value"] <= s["hi"]
    assert p["realism"]["den"] == 150
    assert set(m["by_class"]) == {"benign", "V3", "V4", "V5", "V6"}
    assert set(m["by_register"]) == {"formal", "terse", "conversational"}
    k = m["fleiss_kappa"]
    assert -1.0 <= k["value"] <= 1.0 and k["lo"] <= k["value"] <= k["hi"]
    # recompute the pooled realism share and kappa from cases.csv
    pos = sum(int(r[8]) for r in rows[1:])
    assert p["realism"]["value"] == pytest.approx(pos / 150)
    counts = np.array([[int(r[5]), int(r[6]), int(r[7])] for r in rows[1:]])
    assert k["value"] == pytest.approx(SC.fleiss_kappa(counts))
    # four-of-five counts agree with cases.csv
    assert p["four_of_five"]["realism"] == sum(1 for r in rows[1:] if int(r[8]) >= 4)
    # deterministic: a second scoring gives the same numbers
    res2 = SC.score(syn, tmp_path / "again", pack, quiet=True)
    assert json.dumps(res2["measures"]) == json.dumps(m)


def test_scorer_refuses_synthetic_into_the_real_folder(builds, tmp_path):
    root, _ = builds[0]
    pack, panel = root / "results", root / "panel"
    syn = tmp_path / "syn"
    SC.make_synthetic(syn, pack, panel, seed=3)
    real = SC.DEFAULT_OUT / "cases.csv"
    before = real.exists()
    with pytest.raises(SystemExit):
        SC.score(syn, SC.DEFAULT_OUT, pack, quiet=True)
    assert real.exists() == before


def test_scorer_rejects_blank_ratings(builds, tmp_path):
    from openpyxl import load_workbook

    root, _ = builds[0]
    pack, panel = root / "results", root / "panel"
    syn = tmp_path / "syn"
    SC.make_synthetic(syn, pack, panel, seed=5)
    p = syn / "Stage_A_Workbook_R2.xlsx"
    wb = load_workbook(p)
    wb["Cases"]["F5"] = None
    wb.save(p)
    with pytest.raises(SystemExit):
        SC.score(syn, tmp_path / "out", pack, quiet=True)
    res = SC.score(syn, tmp_path / "out2", pack, allow_missing=True, quiet=True)
    assert res["measures"]["pooled"]["realism"]["den"] == 149
