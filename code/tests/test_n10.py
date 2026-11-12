"""N10: field-changing proposals, certified gap against original-field damage.

Covers the helper classifications on hand-written operation lists, and on the
real logs: the per-row damage reproduces published aggregates (T5_ladder.csv
and DG17_e2e_delta.csv), the split matches column 15 of N2_rows_e2e.csv on
every row, the written outputs are reproduced byte for byte, and the macros
file parses with a value for every macro.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import e1_delta_guard_replay as e1dg  # noqa: E402
import n10_field_change as N  # noqa: E402

ANALYSIS = N.ANALYSIS


def read_commented_csv(path):
    with open(path, "r", encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


# --------------------------------------------------------------------------- #
# Helpers, on hand-written inputs                                              #
# --------------------------------------------------------------------------- #
def test_field_kind_on_toy_lists():
    assert N.field_kind([]) is None
    assert N.field_kind([{"op": "pin_next", "order_id": "W1", "trade": "D30"}]) is None
    assert N.field_kind([{"op": "set_priority", "order_id": "W1", "priority_class": 2}]) \
        == "set_priority_only"
    assert N.field_kind([{"op": "reassign_window", "order_id": "W1",
                          "release_shift_bh": 4.0},
                         {"op": "freeze", "order_id": "W2"}]) == "reassign_window_only"
    assert N.field_kind([{"op": "set_priority", "order_id": "W1", "priority_class": 2},
                         {"op": "reassign_window", "order_id": "W1",
                          "release_shift_bh": 4.0}]) == "both"


def test_bins_are_closed_on_the_right():
    assert N.gap_bin(0.0) == "0-0.05"
    assert N.gap_bin(0.05) == "0-0.05"
    assert N.gap_bin(0.0500001) == "0.05-0.10"
    assert N.gap_bin(0.20) == "0.10-0.20"
    with pytest.raises(ValueError):
        N.gap_bin(0.2000001)
    assert N.dmg_bin(-3.0) == "<=0"
    assert N.dmg_bin(0.0) == "<=0"
    assert N.dmg_bin(2.0) == "0-2"
    assert N.dmg_bin(10.0) == "2-10"
    assert N.dmg_bin(10.000001) == ">10"


def test_class_groups():
    assert [N.class_group(c) for c in ("benign", "V1", "V2", "V3", "V4", "V5", "V6")] == \
        ["benign", "other", "other", "V3", "V4", "other", "other"]


def test_number_formats():
    assert N.fmt_bh(999827.2595) == "999{,}827.26"
    assert N.fmt_bh(0.0) == "0.00"
    assert N.fmt_bh(-1234.5) == "-1{,}234.50"
    assert N.fmt_pct(1, 3) == "33.3\\%"
    assert N.fmt_pct(0, 0) == "--"


# --------------------------------------------------------------------------- #
# The real logs                                                                #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def computed():
    check = e1dg.Checker()
    res = N.compute(check)
    return res, check


def test_every_assertion_passes(computed):
    res, check = computed
    assert check.failures == []
    assert check.n > 100_000
    assert res["n_rows"] == 40_000
    assert res["n_qual"] == 29_980


def test_per_row_damage_reproduces_published_aggregates(computed):
    """Mean excess under G-CERT, rebuilt from the per-row damage, for one arm and all."""
    res, _check = computed
    cells = res["cells"]
    t5 = {}
    for row in read_commented_csv(ANALYSIS / "T5_ladder.csv"):
        if row["scope"] == "full_suite" and row["step"].startswith("5. G-CERT"):
            mode, thinking = [p.strip() for p in row["mode"].split("/")]
            if mode == N.MODE:
                t5[(row["arm"], thinking)] = float(row["wwt_original_vs_rule_bh"])
    assert ("qwen3-14b", "-") in t5
    for cell, crow in cells.items():
        total = sum(r["damage_if_applied"] if r["applied"] else 0.0 for r in crow)
        mean = total / len(crow)
        assert round(mean, 4) == pytest.approx(t5[cell], abs=1e-9), cell
    dg17 = {(r["arm"], r["thinking"]): float(r["mean_excess_bh"])
            for r in read_commented_csv(ANALYSIS / "DG17_e2e_delta.csv")
            if r["block"] == "headline" and r["config"] == "G-CERT"}
    crow = cells[("qwen3-14b", "-")]
    mean = sum(r["damage_if_applied"] if r["applied"] else 0.0 for r in crow) / len(crow)
    assert mean == pytest.approx(dg17[("qwen3-14b", "-")], abs=1e-6)


def test_split_matches_n2_on_every_row(computed):
    res, _check = computed
    n2 = {}
    for r in read_commented_csv(ANALYSIS / "N2_rows_e2e.csv"):
        if r["dataset"] == "e2e" and r["mode"] == N.MODE:
            n2[r["row_id"]] = r["split"]
    qual = [r for r in res["rows"] if r["reached_qual"]]
    assert len(n2) == len(qual) == 29_980
    mismatched = [N.row_id(r) for r in qual if n2.get(N.row_id(r)) != r["split"]]
    assert mismatched == []


def test_written_outputs_are_reproduced(computed, tmp_path):
    res, check = computed
    N.write_all(res, check.n, tmp_path)
    for name in N.OUTPUT_NAMES:
        assert (tmp_path / name).read_bytes() == (ANALYSIS / name).read_bytes(), name


def test_rows_file_matches_the_headline(computed):
    res, _check = computed
    rows = read_commented_csv(ANALYSIS / "N10_rows.csv")
    s = res["table"][("all", "all", "field_changing")]
    assert len(rows) == s["n_applied"]
    assert sum(1 for r in rows if float(r["damage_bh"]) > 10.0) == s["n_dmg_gt10"]
    assert all(float(r["gap_cert"]) <= N.TAU for r in rows)


# --------------------------------------------------------------------------- #
# The macros file                                                              #
# --------------------------------------------------------------------------- #
MACRO_RE = re.compile(r"^\\newcommand\{\\(nTen[A-Za-z]+)\}\{(.*)\}$")


def parse_macros():
    out = {}
    for ln in (ANALYSIS / "N10_macros.tex").read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.startswith("%"):
            continue
        m = MACRO_RE.match(ln)
        assert m is not None, ln
        name, value = m.group(1), m.group(2)
        assert name not in out, name
        out[name] = value
    return out


def test_macros_parse_and_every_macro_has_a_value():
    macros = parse_macros()
    assert len(macros) > 100
    for name, value in macros.items():
        assert value.strip() != "", name
        assert value.count("{") == value.count("}"), name
        assert "%" not in value.replace("\\%", ""), name
    text = (ANALYSIS / "N10_macros.tex").read_text(encoding="utf-8")
    assert text.startswith("% N10 macros, generated by code/scripts/n10_field_change.py")
    assert "sha256" in text
    assert "/home/" not in text


def test_macros_agree_with_the_csv():
    macros = parse_macros()
    rows = {(r["scope"], r["class"], r["split"]): r
            for r in read_commented_csv(ANALYSIS / "N10_field_change.csv")}
    fa = rows[("all", "all", "field_changing")]
    assert macros["nTenAllFieldApplied"] == N.group_int(int(fa["n_applied"]))
    assert macros["nTenAllFieldDmgTenCount"] == N.group_int(int(fa["n_dmg_gt10"]))
    assert macros["nTenAllFieldDmgTwoCount"] == N.group_int(int(fa["n_dmg_gt2"]))
    assert macros["nTenRows"] == "40{,}000"
    assert macros["nTenTau"] == "0.20"
