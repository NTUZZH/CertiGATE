"""The numbers pipeline: does macros.tex say what the analysis tables say?

The manuscript's rule is that every result-derived number is a macro generated
from ``analysis/``.  That rule only buys anything if the generator copies the
cell it claims to copy, so these tests re-read the source CSVs with their own
parser and compare the cells against the emitted macro bodies.  Nothing here
imports the generator's readers or formatters for the comparison values: the
expected strings are written down literally, the way a reader checking the
manuscript against the tables would write them down.

Four things are tested.

First, the spot-check: five macros from five different source tables, each
against the cell it names, computed independently from the raw CSV text.

Second, hygiene: names are letters only (a LaTeX control sequence cannot hold a
digit or an underscore), no name is defined twice, and every percentage macro
carries exactly one escaped per-cent sign, since the convention is that prose
never adds its own.

Third, idempotence: rendering twice with the same stamp is byte-identical, which
is what lets a re-run leave the file untouched.

Fourth, the range discipline: a macro whose name ends in Min or Max must not sit
outside the per-arm macros of its own family, which is the cheapest available
check that a range was taken over the set its comment names.
"""

from __future__ import annotations

import csv
import importlib.util
import re
from pathlib import Path

import pytest

CODE_DIR = Path(__file__).resolve().parent.parent
ROOT = CODE_DIR.parent
ANALYSIS = ROOT / "analysis"
MACROS_TEX = ROOT / "manuscript" / "macros.tex"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        name, CODE_DIR / "scripts" / "{}.py".format(name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def pm():
    return _load("paper_macros")


@pytest.fixture(scope="module")
def built(pm):
    if pm.missing_sources():
        pytest.skip("analysis artifacts are not on disk")
    return pm.build()


@pytest.fixture(scope="module")
def bodies(built):
    """macro name -> body, as the generator would emit it."""
    out = {}
    for _title, _note, items in built.groups:
        for name, body, _comment in items:
            out[name] = body
    return out


@pytest.fixture(scope="module")
def comments(built):
    out = {}
    for _title, _note, items in built.groups:
        for name, _body, comment in items:
            out[name] = comment
    return out


def rows(path: Path) -> list:
    """Read an analysis CSV the plain way, dropping the provenance header."""
    with path.open() as fh:
        return list(csv.DictReader(line for line in fh
                                   if not line.startswith("#")))


def cell(path: Path, column: str, **where) -> str:
    hits = [r for r in rows(path)
            if all(r[k] == v for k, v in where.items())]
    assert len(hits) == 1, "{}: {} rows matched {}".format(
        path.name, len(hits), where)
    return hits[0][column]


# ---------------------------------------------------------------------------
# 1. The spot-check: five macros against five source tables.
# ---------------------------------------------------------------------------

def test_spot_check_v3_separation_opus(bodies):
    """T3: the flagship's V3 separation, the paper's guard-value headline."""
    share = float(cell(ANALYSIS / "T3_guard_value_curve.csv",
                       "v3_separation_share",
                       arm="opus", mode="M_constrained", thinking="default"))
    assert bodies["eOneVThreeSepOpus"] == "{:.1f}\\%".format(share * 100)
    assert bodies["eOneVThreeSepOpus"] == "90.5\\%"


def test_spot_check_false_block_floor_sonnet(bodies):
    """T6: the schema-and-feasibility floor no value of tau can move."""
    floor = float(cell(ANALYSIS / "T6_tau_calibration.csv",
                       "schema_feas_false_block_floor",
                       arm="sonnet", mode="M_constrained", thinking="disabled",
                       tau="0.20"))
    assert bodies["eTwoFloorSonnet"] == "{:.1f}\\%".format(floor * 100)
    assert bodies["eTwoFloorSonnet"] == "1.2\\%"


def test_spot_check_guard_quality_delta_qwen27b(bodies):
    """E8: the guard's paired quality effect at a fixed architecture."""
    delta = float(cell(ANALYSIS / "E8_adjudication.csv", "median_diff_nonzero",
                       arm="qwen27b", budget_level="loose",
                       contrast="MULTI-G vs MULTI-UG",
                       test="wilcoxon_quality", repeat_scope="r0"))
    assert bodies["eThreeGuardQualityDeltaQwenTwentySevenB"] == \
        "{:+.2f}".format(delta)
    assert bodies["eThreeGuardQualityDeltaQwenTwentySevenB"] == "-404.16"


def test_spot_check_oracle_vs_rule(bodies):
    """T4: what perfect human translation costs against no-AI dispatch."""
    vs_rule = float(cell(ANALYSIS / "T4_trustworthiness.csv",
                         "wwt_original_vs_rule_bh",
                         system="ORACLE", scope="full_suite"))
    assert bodies["ladOracleVsRule"] == "{:+.2f}".format(vs_rule)
    assert bodies["ladOracleVsRule"] == "+37.22"


def test_spot_check_e3_total_cost(bodies):
    """E13: the measured E3 spend, the Section 6.7 disclosure's largest line."""
    total = float(cell(ANALYSIS / "E13_e3_costs.csv", "usd_recomputed",
                       arm="ALL", scope="grid + calibration"))
    assert bodies["costEThreeTotalUsd"] == "{:.2f}".format(total)
    assert bodies["costEThreeTotalUsd"] == "41.66"


def test_spot_check_suite_size(bodies):
    """The manifest: the suite size every other count is a share of."""
    import json
    man = json.loads((ROOT / "code" / "suite" / "v0.2" / "manifest.json")
                     .read_text())
    assert man["artifacts"]["suite.jsonl"]["items"] == 2000
    assert bodies["nSuiteItems"] == "2{,}000"


# ---------------------------------------------------------------------------
# 2. Hygiene
# ---------------------------------------------------------------------------

def test_names_are_valid_control_sequences(bodies):
    bad = [n for n in bodies if not re.fullmatch(r"[A-Za-z]+", n)]
    assert bad == []


def test_no_duplicate_names(built):
    seen = []
    for _t, _n, items in built.groups:
        seen.extend(name for name, _b, _c in items)
    assert len(seen) == len(set(seen))


def test_percent_macros_carry_exactly_one_escaped_sign(bodies):
    """The convention is that the macro owns its per-cent sign, not the prose."""
    offenders = []
    for name, body in bodies.items():
        signs = body.count("\\%")
        bare = re.search(r"(?<!\\)%", body)
        if signs > 1 or bare:
            offenders.append((name, body))
    assert offenders == []


def test_every_macro_names_a_source(comments, bodies):
    for name, comment in comments.items():
        assert comment.strip(), name
        if not bodies[name].startswith("\\TODOnum"):
            assert re.search(r"\.(csv|jsonl?|md|py)\b|decisions\.md", comment), \
                "{}: comment does not name a source file: {}".format(
                    name, comment)


def test_todo_bodies_are_declared(built):
    """A TODO body must be reported, so the drafting session cannot miss it."""
    declared = {name for name, _what, _c in built.todos}
    found = set()
    for _t, _n, items in built.groups:
        found.update(name for name, body, _c in items
                     if body.startswith("\\TODOnum"))
    assert declared == found


# ---------------------------------------------------------------------------
# 3. Idempotence
# ---------------------------------------------------------------------------

def test_render_is_deterministic(pm, built):
    a = pm.render(built, "2026-01-01 00:00:00 +0000")
    b = pm.render(built, "2026-01-01 00:00:00 +0000")
    assert a == b


def test_written_file_matches_the_generator(pm, built):
    """The committed macros.tex is the current generator's output."""
    if not MACROS_TEX.is_file():
        pytest.skip("macros.tex has not been generated")
    text = MACROS_TEX.read_text()
    stamp = next(ln[len(pm.HEADER_MARK):] for ln in text.splitlines()
                 if ln.startswith(pm.HEADER_MARK))
    head, body = pm.render(built, stamp)
    assert text == head + "\n" + body


# ---------------------------------------------------------------------------
# 4. Range discipline
# ---------------------------------------------------------------------------

#: Member sets are written down here rather than inferred from the macro names,
#: because that is exactly what the check is for: a range whose membership is
#: guessed cannot catch a range taken over the wrong set.  The capability set
#: excludes DeepSeek, whose constrained mode is JSON-object mode rather than
#: schema enforcement and therefore measures the wire, not the model
#: (analysis/consolidation_report.md, data-quality observation 4).
CAPABILITY = ["QwenFourteenB", "QwenTwentySevenB", "Glm", "Mini", "Sonnet",
              "Opus", "OpusDisabled", "Sol"]
E3_SIX = ["QwenFourteenB", "QwenTwentySevenB", "Mini", "Deepseek", "Sonnet",
          "Opus"]

FAMILIES = [
    ("eOneVThreeSep", CAPABILITY),          # T3 separation, capability set
    ("eTwoFloor", CAPABILITY),              # T6 false-block floor
    ("eOneFalseBlock", CAPABILITY),         # T3 benign false blocks
    ("eThreeCapBindSingleTight", E3_SIX),   # E7 cap binding, all six E3 arms
    ("eThreeTokensMultiLoose", E3_SIX),     # E7 median tokens, all six E3 arms
]


def _value(body: str) -> float:
    return float(body.replace("\\%", "").replace("{,}", "")
                 .replace("+", "").strip())


@pytest.mark.parametrize("stem,members", FAMILIES)
def test_range_macros_bracket_their_family(bodies, stem, members):
    vals = [_value(bodies[stem + arm]) for arm in members]
    assert vals
    lo, hi = _value(bodies[stem + "Min"]), _value(bodies[stem + "Max"])
    # The range endpoints must BE members of the set, not merely bound it: a
    # minimum that no row attains is a minimum taken over the wrong rows.
    assert lo == pytest.approx(min(vals), abs=5e-2)
    assert hi == pytest.approx(max(vals), abs=5e-2)


def test_capability_ranges_exclude_deepseek(bodies):
    """DeepSeek's constrained cells sit far outside every capability range."""
    ds = _value(bodies["eTwoFloorDeepseek"])
    assert ds > _value(bodies["eTwoFloorMax"])
