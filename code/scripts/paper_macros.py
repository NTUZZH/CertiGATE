#!/usr/bin/env python
"""Generate ``manuscript/macros.tex``: one LaTeX macro per result-derived number.

The manuscript rule (``manuscript/main.tex`` header, decisions.md 2026-08-13) is
that every number a sentence cites is a macro, and every macro body comes from an
accepted analysis artifact.  This script is the only writer of that file.

Design, in the order it matters:

* **Sources are the accepted artifacts, never the raw logs.**  ``analysis/``
  (T1-T6, D1-D3, E7-E13, ``tables_meta.json``, ``e3_analysis_meta.json``,
  ``ladder/``), the frozen suite manifest, and the two summary files the tables
  do not cover (``results/e2_tau_sweep/summary.json`` for the tau grid,
  ``results/tier1_slice/summary.json`` for the tier comparison and the
  single-stream guard latency, the eight ``results/e1_eval_*/summary.json``
  for per-arm grid sizes).  Nothing is read
  from a proposals/verdicts log, and nothing is re-derived from one.
* **A value that is not in an accepted artifact becomes ``\\TODOnum{...}``.**  It
  is never guessed, and never computed here from raw data.  The TODO list is
  printed at the end of a run so the drafting session sees it.
* **Derivations are restricted to arithmetic over sourced cells**: a share times
  100, a difference of two table cells, a minimum or maximum over a named set of
  rows.  Every such macro's comment names the rows the set contains, because a
  range whose membership is implicit is a range nobody can check.
* **Idempotent.**  Re-running with unchanged sources rewrites nothing: the
  generation timestamp is preserved when the macro body is byte-identical.
* **Fails loudly.**  A missing source file, or a lookup that finds no row, exits
  non-zero rather than emitting a plausible-looking number.

Usage::

    python code/scripts/paper_macros.py            # write manuscript/macros.tex
    python code/scripts/paper_macros.py --check    # exit 1 if it would change
    python code/scripts/paper_macros.py --out FILE

Changelog::

    2026-08-17  Added the DG13 practitioner-audit group, reading
                ``analysis/DG13_practitioner_audit.csv`` (five practitioners,
                thirty cases, 150 judgements per measure). Appended after the
                guard-fix audit and before the count words, so the regenerated
                file is a pure addition and no earlier group moves.
    2026-08-17  Added the spelled-out companions of the small counts
                (``build_count_words``, the "Spelled-out small counts" group).
                Prose writes a count below ten as a word when it is a count
                noun, so ``\\nEOneArmsWord`` renders "eight" beside
                ``\\nEOneArms``'s "8". Each word is spelled from the body its
                numeric parent already emitted, so the two cannot drift, and a
                parent whose value reaches ten raises rather than emitting a
                digit. The builder runs last in build(), so the regenerated
                file is a pure addition.
    2026-08-17  Corrected the E9 ordering-flip counts and added the review
                response groups. The flip counts now run over DISTINCT
                orderings of the architecture comparison only, dropping three
                metrics that restate another metric's arithmetic, so
                \\eThreeOrderingFlipsOutcome goes 18 -> 14 and
                \\eThreeOrderingFlipsCost 16 -> 11; the two denominators
                \\eThreeOrderingCellsOutcome and \\eThreeOrderingCellsCost are
                new. Added, as pure additions: the E8 differing-item and
                mean-difference range, the DG5 interval-width factor, and five
                new groups (DG10 direct-guard intervals, DG9 stratum split,
                D1 V3 build subclasses, R2 evidence-rate decomposition, PH1
                accepted tail). The five new builders run last in build(), so
                every earlier group keeps its position in macros.tex.

Version: l1-paper-macros-1.
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path

VERSION = "l1-paper-macros-1"

ROOT = Path(__file__).resolve().parent.parent.parent      # /home/ziheng/PaperL1
ANALYSIS = ROOT / "analysis"
RESULTS = ROOT / "results"
SUITE = ROOT / "code" / "suite" / "v0.2"
DEFAULT_OUT = ROOT / "manuscript" / "macros.tex"

# --------------------------------------------------------------------------
# Sources.  Every one of these must exist; a missing file is a hard error.
# --------------------------------------------------------------------------

SOURCES: dict = {
    "T1": ANALYSIS / "T1_e1_main.csv",
    "T2": ANALYSIS / "T2_enforcement_ladder.csv",
    "T3": ANALYSIS / "T3_guard_value_curve.csv",
    "T4": ANALYSIS / "T4_trustworthiness.csv",
    "T5": ANALYSIS / "T5_ladder.csv",
    "T6": ANALYSIS / "T6_tau_calibration.csv",
    "D1": ANALYSIS / "D1_v3_separation_breakdown.csv",
    "D2": ANALYSIS / "D2_class_disposition.csv",
    "D3": ANALYSIS / "D3_translation_equivalence.csv",
    "E7": ANALYSIS / "E7_e3_profiles.csv",
    "E8": ANALYSIS / "E8_adjudication.csv",
    "E9": ANALYSIS / "E9_budget_effect.csv",
    "E11": ANALYSIS / "E11_refusal_and_v56.csv",
    "E12": ANALYSIS / "E12_ladder_e3_rungs.csv",
    "E13": ANALYSIS / "E13_e3_costs.csv",
    "tables_meta": ANALYSIS / "tables_meta.json",
    "e3_meta": ANALYSIS / "e3_analysis_meta.json",
    "ladder_anchors": ANALYSIS / "ladder" / "ladder_anchors.json",
    # One RULE anchor per (instance, standing frozen set).  Section 6.3 cites
    # how many of them already carry a certified gap above the tolerance, and
    # this file is the only authority on that count.
    "rule_anchor": ANALYSIS / "ladder" / "rule_anchor.csv",
    "consolidation": ANALYSIS / "consolidation_report.md",
    "suite_manifest": SUITE / "manifest.json",
    "suite_stats": SUITE / "stats.md",
    # The frozen suite itself.  Four counts have no summary line in the
    # manifest and are read from the item records: the prompt-cache split, the
    # standing frozen set, the V4 quality-visible split, and the benign twins
    # that degrade their own schedule.  It is registered here so its sha256
    # reaches the macros.tex header like every other source.
    "suite_jsonl": SUITE / "suite.jsonl",
    # The guard's own finding vocabulary.  Section 4.2 cites its size, and the
    # only authority for that size is the registry the guard validates against.
    "findings": ROOT / "code" / "l1guard" / "findings.py",
    "e2_summary": RESULTS / "e2_tau_sweep" / "summary.json",
    "tier1_slice": RESULTS / "tier1_slice" / "summary.json",
    # The eight direct-guard / review-response analyses (DG1, DG3-DG8).  Each
    # one is an accepted artifact with its own provenance header; the per-row
    # dumps beside them (DG1_direct_guard.csv, DG7_passthrough_perclass.csv)
    # are not read here, because every number the manuscript quotes is in a
    # summary table.
    "DG1": ANALYSIS / "DG1_direct_guard_summary.csv",
    "DG1_tau": ANALYSIS / "DG1_direct_guard_tau.csv",
    "DG1_fb": ANALYSIS / "DG1_direct_guard_benign_false_blocks.csv",
    "DG2": ANALYSIS / "DG2_falseblock_decomposition.csv",
    "DG2_summary": ANALYSIS / "DG2_falseblock_summary.json",
    "DG2_rescue": ANALYSIS / "DG2_tier1_rescue.csv",
    "DG3": ANALYSIS / "DG3_prevalence.csv",
    "DG4": ANALYSIS / "DG4_tau_cost_rule.csv",
    "DG5": ANALYSIS / "DG5_e1_intervals.csv",
    "DG5_conc": ANALYSIS / "DG5_falseblock_concentration.csv",
    "DG6": ANALYSIS / "DG6_e3_intervals.csv",
    # The two secondary equivalence margins are declared in the note, not in
    # the table, so the note is a source.
    "DG6_note": ANALYSIS / "DG6_e3_intervals.md",
    "DG7": ANALYSIS / "DG7_passthrough.csv",
    "DG7_class": ANALYSIS / "DG7_passthrough_decomp.csv",
    "DG8_floor": ANALYSIS / "DG8_floor.csv",
    "DG8_gap": ANALYSIS / "DG8_gap_agreement.csv",
    "DG8_refusals": ANALYSIS / "DG8_refusals.csv",
    # The five review-response analyses added for the 2026-08-17 revision.
    # DG9 splits the E1 rates by stratum and characterises the three strata;
    # DG10 puts cluster-bootstrap intervals on the direct-guard rates of DG1
    # and locates the benign refusals by instance; R2 decomposes the rise in
    # the evidence-bearing disposition rate; PH1 measures the accepted tail
    # the certificate stage removes from what the feasibility guard accepts.
    "DG9": ANALYSIS / "DG9_stratum_split.csv",
    "DG9_anchor": ANALYSIS / "DG9_stratum_anchor.csv",
    "DG9_char": ANALYSIS / "DG9_stratum_characterisation.csv",
    "DG10": ANALYSIS / "DG10_direct_guard_intervals.csv",
    "DG10_conc": ANALYSIS / "DG10_benign_concentration.csv",
    # DG11 and DG12 audit the guard fix itself: DG12 puts both guard versions
    # on every recorded E3 proposal and counts what the correction withdrew,
    # DG11 measures how far the retired rule reached into the 240-instruction
    # slice.  The per-proposal dump DG12 writes beside its summary is not read
    # here; every number the manuscript quotes is in the summary.
    "DG11": ANALYSIS / "DG11_e3_exposure.csv",
    "DG12": ANALYSIS / "DG12_guard_relaxation.csv",
    # DG13 is the one human-subject artifact in the set: five practitioners
    # rated thirty cases against the suite's own dispositions.  The recorded
    # ratings live in results/practitioner_audit/cases.csv and are read only by
    # code/scripts/practitioner_audit.py, which asserts every headline it
    # prints; the summary table below is what the manuscript quotes.
    "DG13": ANALYSIS / "DG13_practitioner_audit.csv",
    # DG14 answers the external review of 2026-08-18: what does the
    # certificate add over a hand-written threshold rule?  Generated by
    # code/scripts/delta_baselines.py on the direct benchmark.
    "DG14": ANALYSIS / "DG14_delta_baselines.csv",
    "R2": ANALYSIS / "R2_circularity_decomposition.csv",
    "R2_class": ANALYSIS / "R2_circularity_perclass.csv",
    "R2_read": ANALYSIS / "R2_circularity_readings.csv",
    # The two PH1 files carry no provenance header of their own; they are
    # written by scratchpad/phase1/appa/cert_tail.py and cert_tail_detail.py
    # over the same G_FEAS and G_CERT verdict logs the ladder reads, and the
    # detail file is used here only to check the summary's own totals.
    "PH1_tail": ANALYSIS / "PH1_cert_accepted_tail.csv",
    "PH1_tail_detail": ANALYSIS / "PH1_cert_accepted_tail_detail.csv",
    # ---------------------------------------------------------------- v0.1 #
    # The pre-fix copies the guard-v0.2 rerun preserved.  They are read for one
    # purpose only: the short passage that reports the defect the direct
    # benchmark located, which needs the numbers the defective rule produced.
    # No live quantity is ever taken from them, and every macro built here
    # carries "PreFix" in its name so a value from the retired guard cannot be
    # mistaken for a current one.
    "DG1_v01": ANALYSIS / "DG1_direct_guard_summary_guardv01.csv",
    "DG1_fb_v01": ANALYSIS / "DG1_direct_guard_benign_false_blocks_guardv01.csv",
    "DG2_v01": ANALYSIS / "DG2_falseblock_decomposition_guardv01.csv",
    # The guard package's own version string, the only authority on which
    # implementation produced the live numbers.
    "guard_init": ROOT / "code" / "l1guard" / "__init__.py",
}
for _arm_dir in ("qwen14b", "qwen27b", "glm9b", "gpt54mini",
                 "deepseek", "sonnet5", "opus5", "sol"):
    SOURCES["e1_" + _arm_dir] = RESULTS / ("e1_eval_" + _arm_dir) / "summary.json"

#: Every pass that held the workstation GPU, with the meta field carrying its
#: wall-clock.  The E1 generation metas report one wall per (mode, repeat)
#: under ``walls_s``; the E3 metas report one ``tally.wall_s`` per pass.  The
#: hosted arms never touched the GPU, so this list is the whole of it.
LOCAL_WALL_META = [
    ("localEOneQwenFourteenB", RESULTS / "grid_e1_local" / "run_meta.json",
     "walls_s"),
    ("localEOneQwenTwentySevenB", RESULTS / "grid_e1_local_27b" / "run_meta.json",
     "walls_s"),
    ("localEOneGlm", RESULTS / "grid_e1_local_glm9b" / "run_meta.json",
     "walls_s"),
    ("localEThreeQwenFourteenBCal",
     RESULTS / "e3_qwen14b_calibration" / "run_meta_20260812T085454Z.json",
     "tally"),
    ("localEThreeQwenFourteenB",
     RESULTS / "e3_qwen14b" / "run_meta_20260812T092845Z.json", "tally"),
    ("localEThreeQwenTwentySevenBCal",
     RESULTS / "e3_qwen27b_calibration" / "run_meta_20260812T101853Z.json",
     "tally"),
    ("localEThreeQwenTwentySevenB",
     RESULTS / "e3_qwen27b" / "run_meta_20260812T104756Z.json", "tally"),
]
for _key, _path, _field in LOCAL_WALL_META:
    SOURCES[_key] = _path

# --------------------------------------------------------------------------
# Arm vocabulary.  LaTeX control sequences are letters only, so every arm id
# becomes a spelled-out CamelCase token.
# --------------------------------------------------------------------------

#: analysis-table arm id -> macro token
ARM_TOKEN = {
    "qwen3-14b": "QwenFourteenB",
    "qwen3.6-27b-fp8": "QwenTwentySevenB",
    "glm-4-9b": "Glm",
    "openai": "Mini",
    "mini": "Mini",
    "deepseek": "Deepseek",
    "sonnet": "Sonnet",
    "opus": "Opus",
    "sol": "Sol",
    # E3/E13 use short ids for the two local arms.
    "qwen14b": "QwenFourteenB",
    "qwen27b": "QwenTwentySevenB",
}

#: injected class -> macro token, the vocabulary every per-class macro uses.
CLASS_TOKEN = {"V1": "VOne", "V2": "VTwo", "V3": "VThree", "V4": "VFour",
               "V5": "VFive", "V6": "VSix"}

#: The thinking setting that carries each arm's headline row.  Opus's "default"
#: is the flagship at deployed strength; DeepSeek's "non_think" is its cheaper
#: half.  The other configuration of each pair gets its own suffixed macros.
PRIMARY_THINKING = {
    "qwen3-14b": "-", "qwen3.6-27b-fp8": "-", "glm-4-9b": "-", "openai": "-",
    "deepseek": "non_think", "sonnet": "disabled", "opus": "default",
    "sol": "none",
}

#: Constrained-mode rows in table order.  Every (arm, thinking) pair T1/T3/T6
#: publish, so a range's membership can be written down exactly.
CONSTRAINED_ROWS = [
    ("qwen3-14b", "-"), ("qwen3.6-27b-fp8", "-"), ("glm-4-9b", "-"),
    ("openai", "-"), ("deepseek", "non_think"), ("deepseek", "think_high"),
    ("sonnet", "disabled"), ("opus", "default"), ("opus", "disabled"),
    ("sol", "none"),
]

#: The capability-curve set: the constrained rows minus DeepSeek's two.  T3's
#: own note says DeepSeek's JSON-object mode "measures the wire, not the model"
#: and that the capability reading must exclude it (analysis/consolidation
#: _report.md, observation 4; decisions.md 2026-08-13 ruling 2).
CAPABILITY_ROWS = [r for r in CONSTRAINED_ROWS if r[0] != "deepseek"]

#: E3 arms, in the capability order the adjudication uses.
E3_ARMS = ["qwen14b", "qwen27b", "openai", "deepseek", "sonnet", "opus"]
#: E3 arms minus DeepSeek, whose unguarded cells are the lenient-repair /
#: empty-list artifact (decisions.md 2026-08-13, E3 ruling 2).
E3_ARMS_NO_DS = [a for a in E3_ARMS if a != "deepseek"]

#: The capability set at one thinking setting per arm: the seven arms, each in
#: the configuration PRIMARY_THINKING names.  DG9 and D1 publish Opus twice, so
#: a pooled share over "the seven arms" has to say which of the two Opus rows it
#: pools; this list is that statement.
PRIMARY_ROWS = [r for r in CAPABILITY_ROWS
                if r[1] == PRIMARY_THINKING[r[0]]]

#: Instance stratum id -> macro token.  The two storm strata are constructed
#: (a Poisson arrival stream per trade, scaled to an offered load of one); the
#: replay stratum is a recorded window of 400 consecutive work orders
#: (analysis/DG9_stratum_split.md, provenance column C / R).
STRATUM_TOKEN = {
    "c09_storm2_w80": "CNine",
    "c10_storm2_w80": "CTenStorm",
    "c10_replay_400": "Replay",
}

#: V3 build subclass -> macro token.  The suite carries 70 / 45 / 45 / 45 / 15
#: items in this order (code/suite/v0.2/suite.jsonl, subclass field).
VTHREE_SUBCLASS_TOKEN = {
    "reorder_block_tight": "BlockTight",
    "reorder_two_successors": "TwoSuccessors",
    "reorder_cross_trade": "CrossTrade",
    "window_blocked_predecessor": "Window",
    "reorder_behind_batch_member": "BehindBatch",
}

#: E1 evaluation directory -> analysis-table arm id.
E1_DIR_ARM = {
    "qwen14b": "qwen3-14b", "qwen27b": "qwen3.6-27b-fp8", "glm9b": "glm-4-9b",
    "gpt54mini": "openai", "deepseek": "deepseek", "sonnet5": "sonnet",
    "opus5": "opus", "sol": "sol",
}

#: The content rule the published pass-through columns apply
#: (code/scripts/passthrough_rule.py).  Every macro reading a ``*_strict``
#: column appends this clause to its provenance line, because the column name
#: says which reading was taken and not what the reading excludes.
STRICT_RULE = ("an applied V4 or V6 row counts unless the applied operations "
               "are exactly the item's ground truth")

#: The lower-bound reading reported once in Appendix E, beside the published
#: rate.  Named the same way, so the two cannot be confused in a provenance
#: line read out of context.
FAULT_RULE = ("an applied V4 or V6 row counts only when the applied "
              "operations are exactly the item's recorded fault")


def thinking_suffix(arm: str, thinking: str) -> str:
    """Macro-name suffix for a non-primary thinking configuration."""
    if thinking == PRIMARY_THINKING.get(arm):
        return ""
    return {"think_high": "ThinkHigh", "disabled": "Disabled",
            "default": "Default", "none": "None", "-": ""}[thinking]


def arm_token(arm: str, thinking: str = None) -> str:
    tok = ARM_TOKEN[arm]
    if thinking is not None:
        tok += thinking_suffix(arm, thinking)
    return tok


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

_CACHE: dict = {}


def missing_sources() -> list:
    return [(k, p) for k, p in SOURCES.items() if not p.is_file()]


def read_csv(key: str) -> list:
    """Rows of an analysis CSV, with the ``#`` provenance header stripped."""
    if key not in _CACHE:
        with SOURCES[key].open() as fh:
            _CACHE[key] = list(csv.DictReader(
                line for line in fh if not line.startswith("#")))
    return _CACHE[key]


def read_json(key: str):
    if key not in _CACHE:
        _CACHE[key] = json.loads(SOURCES[key].read_text())
    return _CACHE[key]


def read_csv_first_block(key: str) -> list:
    """Rows of the FIRST table in a CSV that holds several stacked tables.

    ``DG8_gap_agreement.csv`` writes three tables into one file, separated by
    blank lines, each with its own column set.  A plain ``DictReader`` would
    read the second table's rows against the first table's header and silently
    mis-key every cell, so the reader stops at the first blank line.
    """
    cache_key = key + "#first_block"
    if cache_key not in _CACHE:
        lines = []
        for line in SOURCES[key].open():
            if line.startswith("#"):
                continue
            if not line.strip():
                break
            lines.append(line)
        _CACHE[cache_key] = list(csv.DictReader(lines))
    return _CACHE[cache_key]


def read_text(key: str) -> str:
    if key not in _CACHE:
        _CACHE[key] = SOURCES[key].read_text()
    return _CACHE[key]


def suite_rows() -> list:
    """Every item record of the frozen suite, parsed once.

    Four counts the manifest carries no summary line for are read from the
    item records themselves: the prompt-cache split, the standing frozen set,
    the V4 quality-visible split, and the benign twins that degrade their own
    schedule.
    """
    if "_suite_rows" not in _CACHE:
        with SOURCES["suite_jsonl"].open() as fh:
            _CACHE["_suite_rows"] = [json.loads(line) for line in fh
                                     if line.strip()]
    return _CACHE["_suite_rows"]


def v4_split() -> tuple:
    """(quality-visible, quality-neutral) item counts of the V4 class.

    A V4 mistranslation is quality-visible when it changes the executed
    schedule against the adjusted instance's own optimum, so the quality stage
    can test it; the rest is invisible to every stage and is caught by the
    matched benign twin alone.  On the frozen suite v0.2 the split is 55 and
    165, a quarter and three quarters rather than two halves.  Several macro
    annotations name these two counts, so they are computed once here and
    formatted into the annotations rather than written out in prose.
    """
    if "_v4_split" not in _CACHE:
        v4 = [r for r in suite_rows() if r["primary_class"] == "V4"]
        visible = sum(1 for r in v4 if r.get("quality_visible_candidate"))
        _CACHE["_v4_split"] = (visible, len(v4) - visible)
    return _CACHE["_v4_split"]


def _finding_code_count() -> int:
    """How many codes the guard's finding registry holds.

    Loaded from ``code/l1guard/findings.py`` by file path, because the registry
    itself is the only authority on its own size and the module imports nothing
    outside the standard library.
    """
    if "_finding_codes" not in _CACHE:
        import importlib.util
        name = "_l1guard_findings_for_macros"
        spec = importlib.util.spec_from_file_location(name, SOURCES["findings"])
        module = importlib.util.module_from_spec(spec)
        # dataclasses resolves a frozen class's own module through sys.modules,
        # so the module has to be registered before it executes.
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
            _CACHE["_finding_codes"] = len(module.CODES)
        finally:
            sys.modules.pop(name, None)
    return _CACHE["_finding_codes"]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class LookupError_(RuntimeError):
    """A row the manuscript needs is absent from an accepted artifact."""


def one(rows: list, **where) -> dict:
    """The single row matching ``where``; raises if zero or several match."""
    hits = [r for r in rows if all(r.get(k) == v for k, v in where.items())]
    if len(hits) != 1:
        raise LookupError_(
            "expected exactly 1 row for {!r}, found {}".format(where, len(hits)))
    return hits[0]


def many(rows: list, **where) -> list:
    return [r for r in rows if all(r.get(k) == v for k, v in where.items())]


# --------------------------------------------------------------------------
# Formatting.  Percentages carry their own escaped per-cent sign, so prose
# writes "\eOneVThreeSepOpus" and never "\eOneVThreeSepOpus\%".
# --------------------------------------------------------------------------

def group(n) -> str:
    """Integer with LaTeX thousands separators: 1000480 -> 1{,}000{,}480."""
    s = "{:d}".format(int(round(float(n))))
    sign, s = ("-", s[1:]) if s.startswith("-") else ("", s)
    parts = []
    while len(s) > 3:
        parts.insert(0, s[-3:])
        s = s[:-3]
    parts.insert(0, s)
    return sign + "{,}".join(parts)


def pct(x, places: int = 1) -> str:
    """A share in [0, 1] as a percentage with an escaped per-cent sign."""
    return "{:.{p}f}\\%".format(float(x) * 100.0, p=places)


def pct_of(x, places: int = 1) -> str:
    """A value already expressed in percentage points."""
    return "{:.{p}f}\\%".format(float(x), p=places)


def bh(x, places: int = 2, signed: bool = False) -> str:
    """Weighted business hours.  Two decimals unless the source is coarser."""
    fmt = "{:+.{p}f}" if signed else "{:.{p}f}"
    out = fmt.format(float(x), p=places)
    if abs(float(x)) >= 1000:
        whole, _, frac = out.partition(".")
        sign = ""
        if whole and whole[0] in "+-":
            sign, whole = whole[0], whole[1:]
        out = sign + group(whole) + ("." + frac if frac else "")
    return out


def usd(x, places: int = 2) -> str:
    whole = "{:.{p}f}".format(float(x), p=places)
    intpart, _, frac = whole.partition(".")
    return group(intpart) + ("." + frac if frac else "")


def num(x, places: int = 3) -> str:
    return "{:.{p}f}".format(float(x), p=places)


def sci(x, places: int = 1) -> str:
    """Small p-value: scientific in math mode below 0.001, plain above it."""
    v = float(x)
    if v >= 1e-3:
        return "{:.2f}".format(v)
    s = "{:.{p}e}".format(v, p=places)
    mant, exp = s.split("e")
    return "\\ensuremath{{{}\\times 10^{{{}}}}}".format(mant, int(exp))


def short_sha(s: str, n: int = 8) -> str:
    return s[:n]


TODO_SENTINEL = "\\TODOnum"


def todo(what: str) -> str:
    return "{}{{{}}}".format(TODO_SENTINEL, what)


# --------------------------------------------------------------------------
# Macro accumulator
# --------------------------------------------------------------------------

class Macros:
    def __init__(self):
        self.groups = []          # [(title, note, [(name, body, comment)])]
        self._names = set()
        self.todos = []

    def group(self, title: str, note: str = ""):
        self.groups.append((title, note, []))
        return self

    def add(self, name: str, body: str, comment: str):
        if not re.fullmatch(r"[A-Za-z]+", name):
            raise ValueError("macro name must be letters only: " + name)
        if name in self._names:
            raise ValueError("duplicate macro name: " + name)
        self._names.add(name)
        if body.startswith(TODO_SENTINEL):
            self.todos.append((name, body[len(TODO_SENTINEL) + 1:-1], comment))
        self.groups[-1][2].append((name, body, comment))

    def __len__(self):
        return sum(len(g[2]) for g in self.groups)

    def counts(self):
        return [(g[0], len(g[2])) for g in self.groups]


# --------------------------------------------------------------------------
# Group builders
# --------------------------------------------------------------------------

def build_suite(m: Macros) -> None:
    man = read_json("suite_manifest")
    stats = read_text("suite_stats")
    e3m = read_json("e3_meta")
    src = "code/suite/v0.2/manifest.json"

    m.group("Suite", "The frozen violation suite v0.2: what the instrument "
                     "contains and what identifies it.")

    m.add("nSuiteItems", group(man["artifacts"]["suite.jsonl"]["items"]),
          src + " artifacts['suite.jsonl'].items")
    for set_name, token in (("benign", "Benign"), ("violation", "Violation"),
                            ("ambiguity", "Ambiguity"),
                            ("adversarial", "Adversarial")):
        m.add("nSuite" + token, group(man["counts"]["by_set"][set_name]),
              src + " counts.by_set." + set_name)
    words = {"V1": "VOne", "V2": "VTwo", "V3": "VThree", "V4": "VFour",
             "V5": "VFive", "V6": "VSix"}
    for cls, token in words.items():
        m.add("nSuite" + token, group(man["counts"]["by_class"][cls]),
              src + " counts.by_class." + cls)
    m.add("nSuiteBenignClass", group(man["counts"]["by_class"]["benign"]),
          src + " counts.by_class.benign")
    _inj = sum(man["counts"]["by_class"][c] for c in
               ("V1", "V2", "V3", "V4", "V5", "V6"))
    m.add("nSuiteInjectedTotal", group(_inj),
          src + " counts.by_class V1..V6 summed (the injected-violation total; "
          "distinct from nSuiteViolation, which is the V1-V4 twinned set)")

    strata = man["config"]["strata"]
    m.add("nSuiteStrata", str(len(strata)), src + " config.strata (length)")
    m.add("nSuiteInstances", group(sum(s["n_instances"] for s in strata)),
          src + " config.strata[*].n_instances (sum)")
    stratum_token = {"c09_storm2_w80": "StratumPrimary",
                     "c10_storm2_w80": "StratumConfirmation",
                     "c10_replay_400": "StratumBuildings"}
    for key, token in stratum_token.items():
        m.add("nSuite" + token + "Items", group(man["counts"]["by_stratum"][key]),
              src + " counts.by_stratum." + key)
        st = one_stratum(strata, key)
        m.add("nSuite" + token + "Instances", group(st["n_instances"]),
              src + " config.strata[key=" + key + "].n_instances")

    sub = man["counts"]["by_subclass"]
    m.add("nSuiteViolationSubclasses",
          str(len([k for k in sub if not k.startswith("benign/")])),
          src + " counts.by_subclass (keys outside the benign set)")
    m.add("nSuiteBenignSubclasses",
          str(len([k for k in sub if k.startswith("benign/")])),
          src + " counts.by_subclass (benign keys)")
    m.add("nSuiteViolationClasses", str(len(words)),
          src + " counts.by_class (V1-V6)")

    # Every item that carries an injected violation, i.e. the six injected
    # classes together.  Figure 2's caption counts its rows against this
    # total, which is larger than \nSuiteViolation (the V1-V4 set alone)
    # because it also holds the ambiguity and the injection classes.
    injected = sum(int(man["counts"]["by_class"][c]) for c in words)
    non_benign = (int(man["artifacts"]["suite.jsonl"]["items"])
                  - int(man["counts"]["by_set"]["benign"]))
    if injected != non_benign:
        raise LookupError_(
            "V1-V6 sum {} does not equal the suite minus its benign twins "
            "({})".format(injected, non_benign))
    m.add("nSuiteInjected", group(injected),
          src + " counts.by_class V1-V6 (sum): every item carrying an "
                "injected violation, i.e. the suite minus the benign twins")

    # The expert audit of Section 4.6.  The manifest is the count of record
    # (reports/suite_build.md section 7 and decisions.md 2026-08-11 record the
    # same 194 rows); the share is that count over the suite's own item total.
    audit_rows = int(man["artifacts"]["audit_sample.csv"]["rows"])
    suite_items = int(man["artifacts"]["suite.jsonl"]["items"])
    m.add("nSuiteAuditItems", group(audit_rows),
          src + " artifacts['audit_sample.csv'].rows")
    m.add("nSuiteAuditShare", pct(audit_rows / suite_items),
          src + " artifacts['audit_sample.csv'].rows divided by "
          "artifacts['suite.jsonl'].items")

    # The guard's closed finding vocabulary (Section 4.2).  Read from the
    # registry itself rather than counted by hand, and asserted here so a code
    # added or removed in the guard fails this generator instead of silently
    # falsifying the manuscript.
    n_codes = _finding_code_count()
    if n_codes != 27:
        raise LookupError_(
            "code/l1guard/findings.py CODES holds {} codes; Section 4.2 was "
            "written against 27, so the sentence needs re-checking".format(
                n_codes))
    m.add("nFindingCodes", str(n_codes),
          "code/l1guard/findings.py CODES (number of registered codes; "
          "asserted at 27 in the generator)")

    # The prompt-cache split of Appendix B: items whose rendered user message
    # splits before the named-order records (they reference at least one
    # order) against items that name no order and split before the
    # instruction.  Counted from the frozen suite itself.
    no_order = sum(1 for r in suite_rows()
                   if not r["referenced"].get("order_ids"))
    m.add("nSuiteCacheSplitState", group(suite_items - no_order),
          "code/suite/v0.2/suite.jsonl items with non-empty "
          "referenced.order_ids (cache boundary before the named-order "
          "records)")
    m.add("nSuiteCacheSplitNoOrder", group(no_order),
          "code/suite/v0.2/suite.jsonl items with empty "
          "referenced.order_ids (cache boundary before the instruction)")

    # The standing frozen set (Section 3): items whose episode already has work
    # under way that the proposal must not disturb.  Counted from the frozen
    # suite itself, which is the only artifact carrying episode.frozen_seed.
    frozen = sum(1 for r in suite_rows() if r["episode"]["frozen_seed"])
    m.add("nSuiteFrozenSeedItems", group(frozen),
          "code/suite/v0.2/suite.jsonl items with a non-empty "
          "episode.frozen_seed (a standing frozen set)")
    m.add("nSuiteNoFrozenSeedItems", group(suite_items - frozen),
          "code/suite/v0.2/suite.jsonl items with an empty "
          "episode.frozen_seed (no standing frozen set)")

    # The V4 quality-visible / quality-neutral split of Section 4.7.  A V4
    # mistranslation reaches the certificate only when it changes the executed
    # schedule against the adjusted instance's own optimum; the remainder is
    # invisible to any certificate and is caught by the matched benign twin
    # alone.  Counted from the frozen suite itself, which is the artifact that
    # carries the flag, exactly as the cache-boundary counts above are.
    v4_visible, v4_neutral = v4_split()
    if v4_visible + v4_neutral != int(man["counts"]["by_class"]["V4"]):
        raise LookupError_(
            "V4 split {}+{} does not sum to the manifest's V4 count {}".format(
                v4_visible, v4_neutral, man["counts"]["by_class"]["V4"]))
    m.add("nSuiteVFourVisible", group(v4_visible),
          "code/suite/v0.2/suite.jsonl V4 items with a truthy "
          "quality_visible_candidate flag (the quality-visible split)")
    m.add("nSuiteVFourNeutral", group(v4_neutral),
          "code/suite/v0.2/suite.jsonl V4 items whose "
          "quality_visible_candidate flag is false or absent (the "
          "quality-neutral split)")

    # Benign twins that cost the schedule something (Section 4.7).  A benign
    # instruction is sensible, not costless, so the guard pass has to read a
    # block on a costly twin differently from a block on a costless one.  The
    # per-item badness is on the suite record; reports/suite_build.md section
    # 10 quotes the same count for suite v0.2.
    benign_degrading = sum(1 for r in suite_rows()
                           if r["primary_class"] == "benign"
                           and float(r["badness"] or 0.0) > 0.0)
    m.add("nSuiteBenignDegrading", group(benign_degrading),
          "code/suite/v0.2/suite.jsonl benign items with badness above zero "
          "(benign twins that degrade their own executed schedule); "
          "reports/suite_build.md section 10 quotes the same count")

    # How large the replayed instances get, in work orders.  The suite's own
    # 60 instances are the rows of the no-AI RULE anchor table, whose
    # n_assignments column is that instance's order count; the three strata of
    # Table 4 are min/median/max over the same column.
    orders = {r["instance_id"]: int(r["n_assignments"])
              for r in read_csv("rule_anchor")}
    if len(orders) != sum(s["n_instances"] for s in strata):
        raise LookupError_(
            "rule_anchor.csv holds {} distinct instances; the manifest's "
            "strata declare {}".format(
                len(orders), sum(s["n_instances"] for s in strata)))
    m.add("nInstanceMaxOrders", group(max(orders.values())),
          "analysis/ladder/rule_anchor.csv n_assignments, maximum over the "
          "{} distinct instance_id values (the largest replayed instance, in "
          "work orders)".format(len(orders)))

    split = re.search(r"V1 decoder split: decoder_absorbable (\d+), "
                      r"guard_requiring (\d+)", stats)
    if split is None:
        m.add("nVOneDecoderAbsorbable", todo("V1 decoder-absorbable count"),
              "code/suite/v0.2/stats.md: 'V1 decoder split' line not found")
        m.add("nVOneGuardRequiring", todo("V1 guard-requiring count"),
              "code/suite/v0.2/stats.md: 'V1 decoder split' line not found")
    else:
        m.add("nVOneDecoderAbsorbable", group(split.group(1)),
              "code/suite/v0.2/stats.md 'V1 decoder split: decoder_absorbable'")
        m.add("nVOneGuardRequiring", group(split.group(2)),
              "code/suite/v0.2/stats.md 'V1 decoder split: guard_requiring'")

    reg = dict(re.findall(r"\|\s*(conversational|formal|terse)\s*\|\s*(\d+)\s*\|",
                          stats))
    for name, token in (("conversational", "Conversational"),
                        ("formal", "Formal"), ("terse", "Terse")):
        if name in reg:
            m.add("nSuiteRegister" + token, group(reg[name]),
                  "code/suite/v0.2/stats.md 'Surface form' table, " + name)

    m.add("nEThreeSliceItems", group(e3m["slice_items"]),
          "analysis/e3_analysis_meta.json slice_items (slice " +
          e3m["slice"] + ")")

    m.group("Checksums", "Eight-character prefixes of the sha256 identifiers "
                         "the tables carry in their provenance headers.")
    m.add("shaSuite", short_sha(man["artifacts"]["suite.jsonl"]["sha256"]),
          src + " artifacts['suite.jsonl'].sha256 (first 8)")
    m.add("shaSchema", short_sha(man["schema"]["sha256"]),
          src + " schema.sha256 (first 8)")
    m.add("shaSuiteConfig", short_sha(man["config_fingerprint"]),
          src + " config_fingerprint (first 8)")
    m.add("shaEThreeSlice", short_sha(e3m["slice_sha256"]),
          "analysis/e3_analysis_meta.json slice_sha256 (first 8)")
    for label, key in (("GuardCert", "G_CERT"), ("GuardFeas", "G_FEAS"),
                       ("Unguarded", "UNGUARDED")):
        m.add("sha" + label, short_sha(e3m["guard_config_hashes"][key]),
              "analysis/e3_analysis_meta.json guard_config_hashes." + key +
              " (first 8)")


def one_stratum(strata: list, key: str) -> dict:
    for s in strata:
        if s["key"] == key:
            return s
    raise LookupError_("stratum not found: " + key)


def build_roster(m: Macros) -> None:
    t1 = read_csv("T1")
    tm = read_json("tables_meta")
    e3m = read_json("e3_meta")

    m.group("Roster and grid sizes",
            "How many arms were evaluated and how large each grid is.")

    arms = sorted({r["arm"] for r in t1})
    m.add("nEOneArms", str(len(arms)),
          "analysis/T1_e1_main.csv (distinct arm values)")
    # The subset every capability range is computed over: the constrained rows
    # minus DeepSeek, whose constrained setting is JSON-object mode and
    # enforces no schema.  Counted as MODELS, because Claude Opus 5 supplies
    # two of the eight configurations.
    m.add("nEOneEnforcedModels", str(len({r[0] for r in CAPABILITY_ROWS})),
          "code/scripts/paper_macros.py CAPABILITY_ROWS (distinct arms in the "
          "schema-enforced set; DeepSeek excluded, Opus counted once)")

    total = 0
    for d, arm in E1_DIR_ARM.items():
        s = read_json("e1_" + d)
        total += int(s["run"]["n_rows"])
        m.add("nEOneRows" + arm_token(arm), group(s["run"]["n_rows"]),
              "results/e1_eval_{}/summary.json run.n_rows".format(d))
        m.add("nEOneRepeats" + arm_token(arm), str(len(s["run"]["repeats"])),
              "results/e1_eval_{}/summary.json run.repeats (length)".format(d))
    m.add("nEOneRowsTotal", group(total),
          "results/e1_eval_*/summary.json run.n_rows (sum over the eight arms)")

    m.add("nEThreeArms", str(len(e3m["arms"])),
          "analysis/e3_analysis_meta.json arms (length)")
    m.add("nEThreeTrajectories", group(e3m["trajectories"]),
          "analysis/e3_analysis_meta.json trajectories")
    m.add("nEThreeEntries", group(e3m["entries"]),
          "analysis/e3_analysis_meta.json entries")
    m.add("nEThreeBudgetLevels", "2",
          "analysis/E7_e3_profiles.csv budget_level (tight, loose)")

    m.group("Reconciliation counts",
            "The assertion counts the artifacts report about themselves; the "
            "reproducibility paragraph cites these.")
    m.add("nTableAssertions", group(tm["table_reconciliation"]["total"]),
          "analysis/tables_meta.json table_reconciliation.total")
    m.add("nLadderAssertions", group(tm["ladder_reconciliation"]["total"]),
          "analysis/tables_meta.json ladder_reconciliation.total")
    m.add("nEThreeAssertions", group(e3m["reconciliation"]["total"]),
          "analysis/e3_analysis_meta.json reconciliation.total")
    m.add("nEThreeVerdictFieldChecks", group(e3m["verdict_field_comparisons"]),
          "analysis/e3_analysis_meta.json verdict_field_comparisons")
    e2 = read_json("e2_summary")
    m.add("nETwoAnchorChecks", group(e2["meta"]["anchor_total"]),
          "results/e2_tau_sweep/summary.json meta.anchor_total")
    m.add("nETwoMonotonicityChecks", group(e2["meta"]["mono_total"]),
          "results/e2_tau_sweep/summary.json meta.mono_total")


def _ratio(cell: str) -> tuple:
    """Parse a D3 cell of the form "189/220 (86%)" into (189, 220)."""
    mt = re.match(r"\s*(\d+)\s*/\s*(\d+)", cell)
    if mt is None:
        raise LookupError_("unparsable ratio cell: " + repr(cell))
    return int(mt.group(1)), int(mt.group(2))


def build_e1(m: Macros) -> None:
    t1 = read_csv("T1")
    t2 = read_csv("T2")
    t3 = read_csv("T3")
    d1 = read_csv("D1")
    d2 = read_csv("D2")
    d3 = read_csv("D3")

    def t3row(arm, think):
        return one(t3, arm=arm, mode="M_constrained", thinking=think)

    m.group("E1: the certificate's separation on quality violations",
            "V3 separation is the share of quality violations the feasibility "
            "guard passed and the certificate refused. Constrained mode, "
            "repeats pooled (analysis/T3_guard_value_curve.csv).")

    sep = {}
    for arm, think in CONSTRAINED_ROWS:
        r = t3row(arm, think)
        tok = arm_token(arm, think)
        sep[(arm, think)] = float(r["v3_separation_share"])
        m.add("eOneVThreeSep" + tok, pct(r["v3_separation_share"]),
              "analysis/T3_guard_value_curve.csv v3_separation_share "
              "[{} / {}]".format(arm, think))
        m.add("eOneVThreeCertBlock" + tok, pct(r["v3_gcert_block_rate"]),
              "analysis/T3_guard_value_curve.csv v3_gcert_block_rate "
              "[{} / {}]".format(arm, think))
        m.add("eOneVThreeSepCount" + tok, group(r["v3_separated"]),
              "analysis/T3_guard_value_curve.csv v3_separated [{} / {}]"
              .format(arm, think))
        m.add("eOneVThreeItems" + tok, group(r["v3_items"]),
              "analysis/T3_guard_value_curve.csv v3_items [{} / {}]"
              .format(arm, think))
        m.add("eOneVThreeFeasPass" + tok, group(r["v3_feas_pass"]),
              "analysis/T3_guard_value_curve.csv v3_feas_pass [{} / {}]"
              .format(arm, think))

    cap = [sep[k] for k in CAPABILITY_ROWS]
    members = ", ".join("{}/{}".format(a, t) for a, t in CAPABILITY_ROWS)
    m.add("eOneVThreeSepMin", pct(min(cap)),
          "analysis/T3_guard_value_curve.csv v3_separation_share, minimum over "
          "the capability set {" + members + "}")
    m.add("eOneVThreeSepMax", pct(max(cap)),
          "analysis/T3_guard_value_curve.csv v3_separation_share, maximum over "
          "the capability set {" + members + "}")

    # What G-FEAS alone does on V3: the number the certificate is measured against.
    feas = {}
    for arm, think in CONSTRAINED_ROWS:
        r = one(t1, arm=arm, mode="M_constrained", thinking=think,
                repeat="pooled", **{"class": "V3"})
        feas[(arm, think)] = float(r["gfeas_block_rate"])
        m.add("eOneVThreeFeasBlock" + arm_token(arm, think),
              pct(r["gfeas_block_rate"]),
              "analysis/T1_e1_main.csv gfeas_block_rate [{} / M_constrained / "
              "{} / class V3]".format(arm, think))
    capf = [feas[k] for k in CAPABILITY_ROWS]
    m.add("eOneVThreeFeasBlockMin", pct(min(capf)),
          "analysis/T1_e1_main.csv gfeas_block_rate on V3, minimum over the "
          "capability set {" + members + "}")
    m.add("eOneVThreeFeasBlockMax", pct(max(capf)),
          "analysis/T1_e1_main.csv gfeas_block_rate on V3, maximum over the "
          "capability set {" + members + "}")

    m.group("E1: false blocks on the matched benign twins",
            "The price of the guard, at the frozen operating point tau = 0.20.")
    fb, fbf = {}, {}
    for arm, think in CONSTRAINED_ROWS:
        r = t3row(arm, think)
        tok = arm_token(arm, think)
        fb[(arm, think)] = float(r["benign_false_block_gcert"])
        fbf[(arm, think)] = float(r["benign_false_block_gfeas"])
        m.add("eOneFalseBlock" + tok, pct(r["benign_false_block_gcert"]),
              "analysis/T3_guard_value_curve.csv benign_false_block_gcert "
              "[{} / {}]".format(arm, think))
        m.add("eOneFalseBlockFeas" + tok, pct(r["benign_false_block_gfeas"]),
              "analysis/T3_guard_value_curve.csv benign_false_block_gfeas "
              "[{} / {}]".format(arm, think))
    capfb = [fb[k] for k in CAPABILITY_ROWS]
    m.add("eOneFalseBlockMin", pct(min(capfb)),
          "analysis/T3_guard_value_curve.csv benign_false_block_gcert, minimum "
          "over the capability set {" + members + "}")
    m.add("eOneFalseBlockMax", pct(max(capfb)),
          "analysis/T3_guard_value_curve.csv benign_false_block_gcert, maximum "
          "over the capability set {" + members + "}")
    capfbf = [fbf[k] for k in CAPABILITY_ROWS]
    m.add("eOneFalseBlockFeasMin", pct(min(capfbf)),
          "analysis/T3_guard_value_curve.csv benign_false_block_gfeas, minimum "
          "over the capability set {" + members + "}")
    m.add("eOneFalseBlockFeasMax", pct(max(capfbf)),
          "analysis/T3_guard_value_curve.csv benign_false_block_gfeas, maximum "
          "over the capability set {" + members + "}")

    m.group("E1: the proposer's own errors (V4, V5, V6)",
            "Block rates on mistranslation, overreach and injection, "
            "constrained mode.")
    for label, col in (("VFour", "v4_block_rate"), ("VFive", "v5_block_rate"),
                       ("VSix", "v6_block_rate")):
        vals = {}
        for arm, think in CONSTRAINED_ROWS:
            r = t3row(arm, think)
            vals[(arm, think)] = float(r[col])
            m.add("eOne" + label + "Block" + arm_token(arm, think), pct(r[col]),
                  "analysis/T3_guard_value_curve.csv {} [{} / {}]"
                  .format(col, arm, think))
        capv = [vals[k] for k in CAPABILITY_ROWS]
        m.add("eOne" + label + "BlockMin", pct(min(capv)),
              "analysis/T3_guard_value_curve.csv " + col + ", minimum over the "
              "capability set {" + members + "}")
        m.add("eOne" + label + "BlockMax", pct(max(capv)),
              "analysis/T3_guard_value_curve.csv " + col + ", maximum over the "
              "capability set {" + members + "}")

    m.group("E1: the enforcement ladder",
            "Shape drift by what the wire actually enforces, and what that "
            "drift costs when nothing gates (analysis/T2).")

    def offshape(r):
        return float(r["json_invalid_share"]) + float(r["wrong_shape_share"])

    tiers = {"none": [], "json_object": [], "xgrammar": [], "json_schema": []}
    for r in t2:
        tiers[r["enforcement"]].append(r)
    for enf, label in (("none", "None"), ("json_object", "JsonObject"),
                       ("xgrammar", "Grammar"), ("json_schema", "Strict")):
        rows = tiers[enf]
        for r in rows:
            tok = arm_token(r["arm"], r["thinking"] if r["thinking"] != "-" else
                            PRIMARY_THINKING[r["arm"]])
            m.add("eOneOffShape" + label + tok, pct(offshape(r), 2),
                  "analysis/T2_enforcement_ladder.csv json_invalid_share + "
                  "wrong_shape_share [{} / {} / {}]"
                  .format(enf, r["arm"], r["thinking"]))
        vals = [offshape(r) for r in rows]
        m.add("eOneOffShape" + label + "Min", pct(min(vals), 2),
              "analysis/T2_enforcement_ladder.csv off-shape share, minimum over "
              "the {} rung ({} rows)".format(enf, len(rows)))
        m.add("eOneOffShape" + label + "Max", pct(max(vals), 2),
              "analysis/T2_enforcement_ladder.csv off-shape share, maximum over "
              "the {} rung ({} rows)".format(enf, len(rows)))

    enforced = tiers["xgrammar"] + tiers["json_schema"]
    m.add("eOneOffShapeEnforcedMax", pct(max(offshape(r) for r in enforced), 2),
          "analysis/T2_enforcement_ladder.csv off-shape share, maximum over the "
          "two real schema enforcements (xgrammar + json_schema, {} rows)"
          .format(len(enforced)))
    m.add("eOneOffShapeEnforcedArms", str(len(enforced)),
          "analysis/T2_enforcement_ladder.csv rows on the xgrammar and "
          "json_schema rungs")

    # The GLM row is the cross-family reproduction of the enforcement step.
    glm_free = one(t2, arm="glm-4-9b", enforcement="none")
    glm_gram = one(t2, arm="glm-4-9b", enforcement="xgrammar")
    m.add("eOneGlmOffShapeFree", pct(offshape(glm_free), 2),
          "analysis/T2_enforcement_ladder.csv json_invalid_share + "
          "wrong_shape_share [none / glm-4-9b]")
    m.add("eOneGlmSchemaValidFree", pct(glm_free["schema_valid_share"], 2),
          "analysis/T2_enforcement_ladder.csv schema_valid_share "
          "[none / glm-4-9b]")
    m.add("eOneGlmOffShapeGrammar", pct(offshape(glm_gram), 2),
          "analysis/T2_enforcement_ladder.csv json_invalid_share + "
          "wrong_shape_share [xgrammar / glm-4-9b]")
    m.add("eOneGlmItems", group(glm_free["items"]),
          "analysis/T2_enforcement_ladder.csv items [none / glm-4-9b]")

    m.group("E1: what the schema stage still has to catch",
            "The share of completions the certified guard blocks at the schema "
            "stage, by enforcement rung: the decoder-absorption measurement. "
            "wrong_shape is reported separately from json_invalid because the "
            "two are different drift flavours and only their sum is the "
            "unenforced-proof gate's criterion (decisions.md 2026-08-13, GLM "
            "spot-check correction 1).")
    for enf, label in (("none", "None"), ("json_object", "JsonObject"),
                       ("xgrammar", "Grammar"), ("json_schema", "Strict")):
        rows = tiers[enf]
        for r in rows:
            tok = arm_token(r["arm"], r["thinking"] if r["thinking"] != "-" else
                            PRIMARY_THINKING[r["arm"]])
            m.add("eOneSchemaBlock" + label + tok,
                  pct(r["gcert_blocked_schema_share"]),
                  "analysis/T2_enforcement_ladder.csv gcert_blocked_schema_share"
                  " [{} / {} / {}]".format(enf, r["arm"], r["thinking"]))
            m.add("eOneWrongShape" + label + tok, pct(r["wrong_shape_share"], 2),
                  "analysis/T2_enforcement_ladder.csv wrong_shape_share "
                  "[{} / {} / {}]".format(enf, r["arm"], r["thinking"]))
        for col, stem in (("gcert_blocked_schema_share", "eOneSchemaBlock"),
                          ("wrong_shape_share", "eOneWrongShape"),
                          ("schema_valid_share", "eOneSchemaValid")):
            vals = [float(r[col]) for r in rows]
            places = 1 if stem == "eOneSchemaBlock" else 2
            if stem == "eOneSchemaValid":
                for r in rows:
                    tok = arm_token(r["arm"], r["thinking"]
                                    if r["thinking"] != "-"
                                    else PRIMARY_THINKING[r["arm"]])
                    m.add(stem + label + tok, pct(r[col], places),
                          "analysis/T2_enforcement_ladder.csv {} [{} / {} / {}]"
                          .format(col, enf, r["arm"], r["thinking"]))
            m.add(stem + label + "Min", pct(min(vals), places),
                  "analysis/T2_enforcement_ladder.csv {}, minimum over the {} "
                  "rung ({} rows)".format(col, enf, len(rows)))
            m.add(stem + label + "Max", pct(max(vals), places),
                  "analysis/T2_enforcement_ladder.csv {}, maximum over the {} "
                  "rung ({} rows)".format(col, enf, len(rows)))
    m.add("eOneWrongShapeEnforcedMax",
          pct(max(float(r["wrong_shape_share"]) for r in enforced), 2),
          "analysis/T2_enforcement_ladder.csv wrong_shape_share, maximum over "
          "the two real schema enforcements (xgrammar + json_schema, {} rows)"
          .format(len(enforced)))
    m.add("eOneSchemaBlockEnforcedMax",
          pct(max(float(r["gcert_blocked_schema_share"]) for r in enforced)),
          "analysis/T2_enforcement_ladder.csv gcert_blocked_schema_share, "
          "maximum over the two real schema enforcements ({} rows)"
          .format(len(enforced)))
    m.add("eOneSchemaBlockUnenforcedMin",
          pct(min(float(r["gcert_blocked_schema_share"])
                  for r in tiers["none"] + tiers["json_object"])),
          "analysis/T2_enforcement_ladder.csv gcert_blocked_schema_share, "
          "minimum over the unenforced rungs (none + json_object, {} rows)"
          .format(len(tiers["none"]) + len(tiers["json_object"])))

    m.group("E1: the silent no-op",
            "What shape drift costs with nothing gating: the lenient repair "
            "drops the operations it cannot read and executes what remains.")
    for enf, label in (("none", "Free"), ("json_object", "JsonObject"),
                       ("xgrammar", "Grammar"), ("json_schema", "Strict")):
        rows = tiers[enf]
        for r in rows:
            tok = arm_token(r["arm"], r["thinking"] if r["thinking"] != "-" else
                            PRIMARY_THINKING[r["arm"]])
            m.add("eOneSilentNoop" + label + tok,
                  pct(r["unguarded_silent_noop_share"]),
                  "analysis/T2_enforcement_ladder.csv unguarded_silent_noop_"
                  "share [{} / {} / {}]".format(enf, r["arm"], r["thinking"]))
        vals = [float(r["unguarded_silent_noop_share"]) for r in rows]
        m.add("eOneSilentNoop" + label + "Min", pct(min(vals)),
              "analysis/T2_enforcement_ladder.csv unguarded_silent_noop_share, "
              "minimum over the {} rung ({} rows)".format(enf, len(rows)))
        m.add("eOneSilentNoop" + label + "Max", pct(max(vals)),
              "analysis/T2_enforcement_ladder.csv unguarded_silent_noop_share, "
              "maximum over the {} rung ({} rows)".format(enf, len(rows)))

    m.group("E1: exact translation by enforcement rung",
            "The share of benign twins an arm translates exactly as the ground "
            "truth does, read down the enforcement ladder: the constraint-tax "
            "comparison of Section 6.2 (analysis/T2). These bodies carry NO "
            "per-cent sign, unlike every other share in this file, because the "
            "prose quotes a rung as one range with a single sign at the end "
            "(\"runs 59.3 to 73.3\\%\"); the sign stays in the prose.")
    for enf, label in (("none", "None"), ("json_object", "JsonObject"),
                       ("xgrammar", "Grammar"), ("json_schema", "Strict")):
        vals = [float(r["benign_translation_exact_rate"]) for r in tiers[enf]]
        m.add("eOneTranslationExact" + label + "Min",
              "{:.1f}".format(min(vals) * 100.0),
              "analysis/T2_enforcement_ladder.csv benign_translation_exact_"
              "rate, minimum over the {} rung ({} rows), in per cent without "
              "the sign".format(enf, len(vals)))
        m.add("eOneTranslationExact" + label + "Max",
              "{:.1f}".format(max(vals) * 100.0),
              "analysis/T2_enforcement_ladder.csv benign_translation_exact_"
              "rate, maximum over the {} rung ({} rows), in per cent without "
              "the sign".format(enf, len(vals)))

    m.group("E1: V3 separation by instruction register",
            "D1's register cut: the same quality violations split by the "
            "surface form of the instruction. GPT-5.4-mini separates nearly "
            "the same share in all three registers where every other "
            "schema-enforced configuration does not, which is what makes its "
            "shortfall weakened obedience rather than a guard failure. These "
            "bodies carry no per-cent sign: the prose writes the three values "
            "as one list, and the spread is in percentage points.")
    registers = (("conversational", "Conversational"), ("formal", "Formal"),
                 ("terse", "Terse"))
    spreads = {}
    for arm, think in CAPABILITY_ROWS:
        vals = []
        for reg, label in registers:
            r = one(d1, cut="register", cut_value=reg, arm=arm,
                    mode="M_constrained", thinking=think)
            vals.append(float(r["v3_separation_share"]))
            if arm == "openai":
                m.add("eOneRegisterSep" + label + arm_token(arm, think),
                      "{:.1f}".format(float(r["v3_separation_share"]) * 100.0),
                      "analysis/D1_v3_separation_breakdown.csv "
                      "v3_separation_share [register {} / {} / M_constrained / "
                      "{}], in per cent without the sign".format(
                          reg, arm, think))
        spreads[(arm, think)] = (max(vals) - min(vals)) * 100.0
    others = [(k, v) for k, v in spreads.items() if k[0] != "openai"]
    others_members = ", ".join("{}/{}".format(a, t) for (a, t), _ in others)
    for stem, pick in (("Min", min), ("Max", max)):
        m.add("eOneRegisterSpread" + stem,
              "{:.1f}".format(pick(v for _k, v in others)),
              "analysis/D1_v3_separation_breakdown.csv v3_separation_share, an "
              "arm's largest register value minus its smallest in percentage "
              "points, {} over the capability set outside GPT-5.4-mini {{{}}}"
              .format("minimum" if stem == "Min" else "maximum",
                      others_members))

    m.group("E1: V1 and V2, where the block rate is a joint measurement",
            "A falling block rate on the schema and feasibility classes is the "
            "proposer declining to act, not the guard weakening "
            "(analysis/D2_class_disposition.csv).")
    for cls, label in (("V1", "VOne"), ("V2", "VTwo")):
        for arm, think in CONSTRAINED_ROWS:
            r = one(d2, arm=arm, mode="M_constrained", thinking=think,
                    **{"class": cls})
            tok = arm_token(arm, think)
            m.add("eOne" + label + "GuardBlock" + tok, pct(r["gcert_block_rate"]),
                  "analysis/D2_class_disposition.csv gcert_block_rate "
                  "[{} / M_constrained / {} / {}]".format(arm, think, cls))
            m.add("eOne" + label + "Declined" + tok,
                  pct(r["declined_empty_proposal_share"]),
                  "analysis/D2_class_disposition.csv declined_empty_proposal_"
                  "share [{} / M_constrained / {} / {}]".format(arm, think, cls))
            m.add("eOne" + label + "Handled" + tok,
                  pct(r["handled_share_blocked_declined_or_refused"]),
                  "analysis/D2_class_disposition.csv handled_share_blocked_"
                  "declined_or_refused [{} / M_constrained / {} / {}]"
                  .format(arm, think, cls))

    # Benign declines under constrained mode, every configuration outside the
    # DeepSeek wire artifact (Section 6.1's "declines between ... on benign
    # instructions" range).
    ben = [float(r["declined_empty_proposal_share"])
           for r in many(d2, mode="M_constrained", **{"class": "benign"})
           if r["arm"] != "deepseek"]
    m.add("eOneBenignDeclineMin", pct(min(ben)),
          "analysis/D2_class_disposition.csv declined_empty_proposal_share, "
          "minimum over M_constrained benign rows outside DeepSeek "
          "({} rows)".format(len(ben)))
    m.add("eOneBenignDeclineMax", pct(max(ben)),
          "analysis/D2_class_disposition.csv declined_empty_proposal_share, "
          "maximum over M_constrained benign rows outside DeepSeek "
          "({} rows)".format(len(ben)))

    m.group("E1: the flagship's free-mode refusal wall",
            "Opus's own safety layer refuses most of the unenforced grid; the "
            "share is pooled over all seven classes.")
    for think, label in (("disabled", "Disabled"), ("default", "Default")):
        rows = many(d2, arm="opus", mode="M_free", thinking=think)
        n = sum(int(r["items"]) for r in rows)
        refused = sum(int(r["items"]) * float(r["refused_by_model_share"])
                      for r in rows)
        m.add("eOneOpusRefusalFree" + label, pct(refused / n),
              "analysis/D2_class_disposition.csv refused_by_model_share x items,"
              " summed over the seven classes [opus / M_free / {}] ({} rows)"
              .format(think, len(rows)))
        m.add("eOneOpusRefusalFree" + label + "Count", group(round(refused)),
              "analysis/D2_class_disposition.csv refused_by_model_share x items,"
              " summed over the seven classes [opus / M_free / {}]".format(think))
        m.add("eOneOpusFreeRows" + label, group(n),
              "analysis/D2_class_disposition.csv items, summed over the seven "
              "classes [opus / M_free / {}]".format(think))

    m.group("E1: equivalence-aware translation fidelity",
            "D3's two-rule normalisation (numeric type; reorder inversion). "
            "The V3 column is obedience to a harmful instruction, which is the "
            "mechanism under the guard-value curve "
            "(analysis/D3_translation_equivalence.csv).")
    v3f = {}
    for r in d3:
        tok = ARM_TOKEN[r["arm"]]
        for col, label in (("benign_equiv", "Benign"), ("V3_equiv", "VThree"),
                           ("V4_equiv", "VFour")):
            n, d = _ratio(r[col])
            m.add("eOneFidelity" + label + tok, pct(n / d),
                  "analysis/D3_translation_equivalence.csv {} [{}]"
                  .format(col, r["arm"]))
            m.add("eOneFidelity" + label + tok + "Count", group(n),
                  "analysis/D3_translation_equivalence.csv {} numerator [{}]"
                  .format(col, r["arm"]))
            m.add("eOneFidelity" + label + tok + "Denom", group(d),
                  "analysis/D3_translation_equivalence.csv {} denominator [{}]"
                  .format(col, r["arm"]))
        n, d = _ratio(r["V3_equiv"])
        v3f[r["arm"]] = n / d
    m.add("eOneFidelityVThreeMin", pct(min(v3f.values())),
          "analysis/D3_translation_equivalence.csv V3_equiv, minimum over the "
          "seven arms D3 covers ({})".format(", ".join(sorted(v3f))))
    m.add("eOneFidelityVThreeMax", pct(max(v3f.values())),
          "analysis/D3_translation_equivalence.csv V3_equiv, maximum over the "
          "seven arms D3 covers ({})".format(", ".join(sorted(v3f))))

    m.group("E1: the certified gap on quality violations",
            "How far past tolerance an accepted V3 proposal would have been.")
    for arm, think in CONSTRAINED_ROWS:
        r = t3row(arm, think)
        tok = arm_token(arm, think)
        if r["v3_gap_median"]:
            m.add("eOneVThreeGapMedian" + tok, num(r["v3_gap_median"]),
                  "analysis/T3_guard_value_curve.csv v3_gap_median [{} / {}]"
                  .format(arm, think))
            m.add("eOneVThreeGapMax" + tok, num(r["v3_gap_max"], 4),
                  "analysis/T3_guard_value_curve.csv v3_gap_max [{} / {}]"
                  .format(arm, think))


def build_e2(m: Macros) -> None:
    t6 = read_csv("T6")
    t4 = read_csv("T4")
    e2 = read_json("e2_summary")

    m.group("E2: the tolerance sweep",
            "tau enters the guard only as the final gap-vs-tolerance "
            "comparison, so the sweep is post-processing over certificates "
            "already recorded (analysis/T6_tau_calibration.csv).")

    grid = sorted(float(x) for x in e2["meta"]["tau_grid"])
    m.add("eTwoTauAnchor", "{:.2f}".format(float(e2["meta"]["anchor_tau"])),
          "results/e2_tau_sweep/summary.json meta.anchor_tau")
    m.add("eTwoTauGridSize", str(len(grid)),
          "results/e2_tau_sweep/summary.json meta.tau_grid (length)")
    m.add("eTwoTauGridMin", "{:.2f}".format(min(grid)),
          "results/e2_tau_sweep/summary.json meta.tau_grid (minimum)")
    m.add("eTwoTauGridMax", "{:.2f}".format(max(grid)),
          "results/e2_tau_sweep/summary.json meta.tau_grid (maximum)")
    m.add("eTwoCertifiedRows", group(e2["meta"]["n_certified"]),
          "results/e2_tau_sweep/summary.json meta.n_certified")
    m.add("eTwoPreQualBlockedRows", group(e2["meta"]["n_pre_qual_blocked"]),
          "results/e2_tau_sweep/summary.json meta.n_pre_qual_blocked")

    def t6row(arm, think, tau):
        return one(t6, arm=arm, mode="M_constrained", thinking=think, tau=tau)

    taus = {"0.05": "AtFive", "0.20": "AtTwenty", "0.50": "AtFifty"}
    gains, losses = {}, {}
    for arm, think in CONSTRAINED_ROWS:
        tok = arm_token(arm, think)
        vals = {}
        for tau, label in taus.items():
            r = t6row(arm, think, tau)
            vals[tau] = float(r["v3_separation_share"])
            m.add("eTwoSep" + label + tok, pct(r["v3_separation_share"]),
                  "analysis/T6_tau_calibration.csv v3_separation_share "
                  "[{} / M_constrained / {} / tau {}]".format(arm, think, tau))
        gains[(arm, think)] = (vals["0.05"] - vals["0.20"]) * 100.0
        losses[(arm, think)] = (vals["0.20"] - vals["0.50"]) * 100.0
        m.add("eTwoSepGain" + tok, "{:.1f}".format(gains[(arm, think)]),
              "analysis/T6_tau_calibration.csv v3_separation_share at tau 0.05 "
              "minus tau 0.20, in percentage points [{} / {}]"
              .format(arm, think))
        m.add("eTwoSepLoss" + tok, "{:.1f}".format(losses[(arm, think)]),
              "analysis/T6_tau_calibration.csv v3_separation_share at tau 0.20 "
              "minus tau 0.50, in percentage points [{} / {}]"
              .format(arm, think))
    members = ", ".join("{}/{}".format(a, t) for a, t in CAPABILITY_ROWS)
    capg = [gains[k] for k in CAPABILITY_ROWS]
    capl = [losses[k] for k in CAPABILITY_ROWS]
    m.add("eTwoSepGainMin", "{:.1f}".format(min(capg)),
          "analysis/T6_tau_calibration.csv separation gain from tau 0.20 to "
          "0.05, percentage points, minimum over {" + members + "}")
    m.add("eTwoSepGainMax", "{:.1f}".format(max(capg)),
          "analysis/T6_tau_calibration.csv separation gain from tau 0.20 to "
          "0.05, percentage points, maximum over {" + members + "}")
    m.add("eTwoSepLossMin", "{:.1f}".format(min(capl)),
          "analysis/T6_tau_calibration.csv separation loss from tau 0.20 to "
          "0.50, percentage points, minimum over {" + members + "}")
    m.add("eTwoSepLossMax", "{:.1f}".format(max(capl)),
          "analysis/T6_tau_calibration.csv separation loss from tau 0.20 to "
          "0.50, percentage points, maximum over {" + members + "}")

    m.group("E2: the false-block floor and the operating point",
            "The share of benign twins blocked at the schema or feasibility "
            "stage, which no value of tau can move, and the tightest gate "
            "meeting the 5 per cent budget.")
    floors, ops = {}, {}
    for arm, think in CONSTRAINED_ROWS:
        r = t6row(arm, think, "0.20")
        tok = arm_token(arm, think)
        floors[(arm, think)] = float(r["schema_feas_false_block_floor"])
        m.add("eTwoFloor" + tok, pct(r["schema_feas_false_block_floor"]),
              "analysis/T6_tau_calibration.csv schema_feas_false_block_floor "
              "[{} / M_constrained / {}]".format(arm, think))
        if r["operating_point_fb5pct"]:
            ops[(arm, think)] = float(r["operating_point_fb5pct"])
            m.add("eTwoOperatingTau" + tok,
                  "{:.2f}".format(float(r["operating_point_fb5pct"])),
                  "analysis/T6_tau_calibration.csv operating_point_fb5pct "
                  "[{} / M_constrained / {}]".format(arm, think))
    capfl = [floors[k] for k in CAPABILITY_ROWS]
    m.add("eTwoFloorMin", pct(min(capfl)),
          "analysis/T6_tau_calibration.csv schema_feas_false_block_floor, "
          "minimum over the capability set {" + members + "}")
    m.add("eTwoFloorMax", pct(max(capfl)),
          "analysis/T6_tau_calibration.csv schema_feas_false_block_floor, "
          "maximum over the capability set {" + members + "}")
    if ops:
        m.add("eTwoOperatingTauMin", "{:.2f}".format(min(ops.values())),
              "analysis/T6_tau_calibration.csv operating_point_fb5pct, minimum "
              "over the {} constrained rows that reach the 5 per cent budget"
              .format(len(ops)))
        m.add("eTwoOperatingTauMax", "{:.2f}".format(max(ops.values())),
              "analysis/T6_tau_calibration.csv operating_point_fb5pct, maximum "
              "over the {} constrained rows that reach the 5 per cent budget"
              .format(len(ops)))
        m.add("eTwoOperatingTauArms", str(len(ops)),
              "analysis/T6_tau_calibration.csv rows with a non-empty "
              "operating_point_fb5pct")
    # The 1 per cent budget.  Under the retired guard no row on the grid
    # reached it; under the fixed guard one arm does, so the parenthetical that
    # used to read "unreachable" would now be false and has been replaced by
    # what the cells actually say.  The row count and the arm count are not the
    # same number, because every tolerance row of a reaching arm carries that
    # arm's operating point, so both are published: quoting the row count as if
    # it were an arm count is the misreading this pair exists to prevent.
    reach1 = [r for r in t6 if r["operating_point_fb1pct"]]
    reach1_arms = sorted({(r["arm"], r["thinking"]) for r in reach1})
    m.add("eTwoOnePercentArms", str(len(reach1)),
          "analysis/T6_tau_calibration.csv rows with a non-empty "
          "operating_point_fb1pct: tolerance ROWS, not arms; the {} row(s) "
          "belong to {} arm configuration(s)".format(len(reach1),
                                                     len(reach1_arms)))
    m.add("eTwoOnePercentArmsDistinct", str(len(reach1_arms)),
          "analysis/T6_tau_calibration.csv distinct (arm, thinking) pairs with "
          "a non-empty operating_point_fb1pct: {}".format(
              ", ".join("{}/{}".format(a, t) for a, t in reach1_arms)
              or "none"))
    if reach1:
        best = min((r for r in t6 if r["false_block_rate"]),
                   key=lambda r: float(r["false_block_rate"]))
        m.add("eTwoOnePercentTau", "{:.2f}".format(
            float(reach1[0]["operating_point_fb1pct"])),
              "analysis/T6_tau_calibration.csv operating_point_fb1pct, the "
              "tolerance at which the 1 per cent budget is met")
        m.add("eTwoFalseBlockGridMin", pct(best["false_block_rate"], 2),
              "analysis/T6_tau_calibration.csv false_block_rate, minimum over "
              "all {} rows of the tolerance grid [{} / {} / tau {}]".format(
                  len(t6), best["arm"], best["thinking"], best["tau"]))

    # Part of the floor is not the proposal's fault: some instances are already
    # past the tolerance before any instruction is applied, so an empty
    # proposal is refused at the quality stage there too.
    anchor_tau = float(e2["meta"]["anchor_tau"])
    anchors = read_csv("rule_anchor")
    above = [r for r in anchors if float(r["gap"]) > anchor_tau]
    m.add("nRuleAnchors", group(len(anchors)),
          "analysis/ladder/rule_anchor.csv (rows: one no-AI RULE anchor per "
          "instance and standing frozen set)")
    m.add("nRuleAnchorsAboveTau", group(len(above)),
          "analysis/ladder/rule_anchor.csv rows whose gap exceeds the anchor "
          "tolerance {:.2f} ({})".format(
              anchor_tau, ", ".join(sorted({r["instance_id"] for r in above}))))

    m.group("E2: the certified gap of the set each guard accepts",
            "What the certificate removes, described by the certified gap of "
            "the proposals a configuration lets through: constrained mode, "
            "full-suite scope, over the capability set "
            "(analysis/T4_trustworthiness.csv). The median barely moves "
            "between the two configurations; the change is in the tail, which "
            "is where the damaging proposals are. The G-CERT 90th percentile "
            "and maximum are one number rather than a range, because every arm "
            "in the set reports the same value; the generator asserts that "
            "rather than assuming it, since Section 6.3 prints one number.")

    def gap_column(cfg, column):
        out = []
        for arm, think in CAPABILITY_ROWS:
            r = one(t4, arm=arm, config=cfg, mode="M_constrained",
                    thinking=think, scope="full_suite")
            out.append(float(r[column]))
        return out

    def gap_src(cfg, column, what):
        return ("analysis/T4_trustworthiness.csv {} [{} / M_constrained / "
                "full_suite], {} over the capability set {{{}}}"
                .format(column, cfg, what, members))

    def one_body(bodies, cfg, column):
        distinct = sorted(set(bodies))
        if len(distinct) != 1:
            raise LookupError_(
                "Section 6.3 prints a single {} for {} over the capability "
                "set, but T4 gives {}".format(column, cfg, distinct))
        return distinct[0]

    for column, label, places in (("certified_gap_median", "Median", 3),
                                  ("certified_gap_p90", "PNinety", 3),
                                  ("certified_gap_max", "Worst", 1)):
        vals = gap_column("G_FEAS", column)
        m.add("eTwoGapFeas" + label + "Min", num(min(vals), places),
              gap_src("G_FEAS", column, "minimum"))
        m.add("eTwoGapFeas" + label + "Max", num(max(vals), places),
              gap_src("G_FEAS", column, "maximum"))

    med = gap_column("G_CERT", "certified_gap_median")
    m.add("eTwoGapCertMedianMin", num(min(med), 3),
          gap_src("G_CERT", "certified_gap_median", "minimum"))
    m.add("eTwoGapCertMedianMax", num(max(med), 3),
          gap_src("G_CERT", "certified_gap_median", "maximum"))
    for column, label, places in (("certified_gap_p90", "PNinety", 3),
                                  ("certified_gap_max", "Worst", 3)):
        vals = gap_column("G_CERT", column)
        m.add("eTwoGapCert" + label,
              one_body([num(v, places) for v in vals], "G_CERT", column),
              gap_src("G_CERT", column,
                      "the one value every row reports, asserted equal"))


def build_e3(m: Macros) -> None:
    e7 = read_csv("E7")
    e8 = read_csv("E8")
    e9 = read_csv("E9")
    e13 = read_csv("E13")

    def e7row(arm, budget, variant):
        return one(e7, arm=arm, budget_level=budget, variant=variant)

    m.group("E3: the tight budget, where the multi-agent pipeline does not fit",
            "B_tight is the single agent's own median completion need. The cap "
            "binds on every MULTI trajectory on every arm "
            "(analysis/E7_e3_profiles.csv).")
    multi_cap, single_cap, multi_ref = [], [], []
    for arm in E3_ARMS:
        tok = ARM_TOKEN[arm]
        rm = e7row(arm, "tight", "MULTI-G")
        rs = e7row(arm, "tight", "SINGLE+G")
        multi_cap.append(float(rm["cap_binding_share"]))
        single_cap.append(float(rs["cap_binding_share"]))
        multi_ref.append(float(rm["share_referred"]))
        m.add("eThreeCapBindMultiTight" + tok, pct(rm["cap_binding_share"]),
              "analysis/E7_e3_profiles.csv cap_binding_share "
              "[{} / tight / MULTI-G]".format(arm))
        m.add("eThreeCapBindSingleTight" + tok, pct(rs["cap_binding_share"]),
              "analysis/E7_e3_profiles.csv cap_binding_share "
              "[{} / tight / SINGLE+G]".format(arm))
        m.add("eThreeReferralMultiTight" + tok, pct(rm["share_referred"]),
              "analysis/E7_e3_profiles.csv share_referred "
              "[{} / tight / MULTI-G]".format(arm))
        m.add("eThreeBudgetTight" + tok, group(rs["budget_tokens"]),
              "analysis/E7_e3_profiles.csv budget_tokens [{} / tight]"
              .format(arm))
        m.add("eThreeBudgetLoose" + tok,
              group(e7row(arm, "loose", "SINGLE+G")["budget_tokens"]),
              "analysis/E7_e3_profiles.csv budget_tokens [{} / loose]"
              .format(arm))
    allsix = ", ".join(E3_ARMS)
    m.add("eThreeCapBindMultiTightMin", pct(min(multi_cap)),
          "analysis/E7_e3_profiles.csv cap_binding_share [tight / MULTI-G], "
          "minimum over all six arms (" + allsix + ")")
    m.add("eThreeCapBindSingleTightMin", pct(min(single_cap)),
          "analysis/E7_e3_profiles.csv cap_binding_share [tight / SINGLE+G], "
          "minimum over all six arms (" + allsix + ")")
    m.add("eThreeCapBindSingleTightMax", pct(max(single_cap)),
          "analysis/E7_e3_profiles.csv cap_binding_share [tight / SINGLE+G], "
          "maximum over all six arms (" + allsix + ")")
    m.add("eThreeReferralMultiTightMin", pct(min(multi_ref)),
          "analysis/E7_e3_profiles.csv share_referred [tight / MULTI-G], "
          "minimum over all six arms (" + allsix + ")")
    m.add("eThreeReferralMultiTightMax", pct(max(multi_ref)),
          "analysis/E7_e3_profiles.csv share_referred [tight / MULTI-G], "
          "maximum over all six arms (" + allsix + ")")
    m.add("eThreeBudgetRatio", "4",
          "analysis/E7_e3_profiles.csv budget_tokens, loose divided by tight "
          "(4x by design, E3 freeze; verified equal on all six arms)")

    m.group("E3: what the multi-agent layer costs at the loose budget",
            "Both architectures complete here, so the token comparison is the "
            "one the decision rule uses. variant_tokens_median charges each "
            "variant only the calls it consumes.")
    single_tok, multi_tok, ratios = {}, {}, {}
    for arm in E3_ARMS:
        tok = ARM_TOKEN[arm]
        s = float(e7row(arm, "loose", "SINGLE+G")["variant_tokens_median"])
        mm = float(e7row(arm, "loose", "MULTI-G")["variant_tokens_median"])
        single_tok[arm], multi_tok[arm], ratios[arm] = s, mm, mm / s
        m.add("eThreeTokensSingleLoose" + tok, group(s),
              "analysis/E7_e3_profiles.csv variant_tokens_median "
              "[{} / loose / SINGLE+G]".format(arm))
        m.add("eThreeTokensMultiLoose" + tok, group(mm),
              "analysis/E7_e3_profiles.csv variant_tokens_median "
              "[{} / loose / MULTI-G]".format(arm))
        m.add("eThreeTokenRatioLoose" + tok, "{:.2f}".format(mm / s),
              "analysis/E7_e3_profiles.csv variant_tokens_median, MULTI-G "
              "divided by SINGLE+G [{} / loose]".format(arm))
    m.add("eThreeTokensSingleLooseMin", group(min(single_tok.values())),
          "analysis/E7_e3_profiles.csv variant_tokens_median [loose / "
          "SINGLE+G], minimum over all six arms (" + allsix + ")")
    m.add("eThreeTokensSingleLooseMax", group(max(single_tok.values())),
          "analysis/E7_e3_profiles.csv variant_tokens_median [loose / "
          "SINGLE+G], maximum over all six arms (" + allsix + ")")
    m.add("eThreeTokensMultiLooseMin", group(min(multi_tok.values())),
          "analysis/E7_e3_profiles.csv variant_tokens_median [loose / MULTI-G],"
          " minimum over all six arms (" + allsix + ")")
    m.add("eThreeTokensMultiLooseMax", group(max(multi_tok.values())),
          "analysis/E7_e3_profiles.csv variant_tokens_median [loose / MULTI-G],"
          " maximum over all six arms (" + allsix + ")")
    m.add("eThreeTokenRatioLooseMin", "{:.1f}".format(min(ratios.values())),
          "analysis/E7_e3_profiles.csv per-arm MULTI-G / SINGLE+G median-token "
          "ratio, minimum over all six arms (" + allsix + ")")
    m.add("eThreeTokenRatioLooseMax", "{:.1f}".format(max(ratios.values())),
          "analysis/E7_e3_profiles.csv per-arm MULTI-G / SINGLE+G median-token "
          "ratio, maximum over all six arms (" + allsix + ")")
    m.add("eThreeTokenRatioEndpointLow",
          "{:.1f}".format(min(multi_tok.values()) / min(single_tok.values())),
          "analysis/E7_e3_profiles.csv ratio of the two range endpoints: "
          "cheapest MULTI-G median over cheapest SINGLE+G median")
    m.add("eThreeTokenRatioEndpointHigh",
          "{:.1f}".format(max(multi_tok.values()) / max(single_tok.values())),
          "analysis/E7_e3_profiles.csv ratio of the two range endpoints: "
          "dearest MULTI-G median over dearest SINGLE+G median")

    m.group("E3: the revision loop and the trajectory clock",
            "The second and third currencies of Section 6.7, both at the loose "
            "budget (analysis/E7_e3_profiles.csv). E3 ran six trajectories in "
            "flight per arm, so a median trajectory wall describes the "
            "pipeline under that concurrency and is not a latency "
            "measurement; the single-stream guard latency is measured "
            "separately in the Tier-1 slice.")
    ppa, revised = {}, {}
    wall = {"SINGLE+G": {}, "MULTI-G": {}}
    for arm in E3_ARMS:
        tok = ARM_TOKEN[arm]
        rs = e7row(arm, "loose", "SINGLE+G")
        ppa[arm] = float(rs["proposals_per_accepted_adjustment"])
        revised[arm] = int(rs["n_with_revision"])
        m.add("eThreeProposalsPerAcceptedLoose" + tok, num(ppa[arm], 2),
              "analysis/E7_e3_profiles.csv proposals_per_accepted_adjustment "
              "[{} / loose / SINGLE+G]".format(arm))
        m.add("eThreeRevisedTrajectoriesLoose" + tok, group(revised[arm]),
              "analysis/E7_e3_profiles.csv n_with_revision [{} / loose / "
              "SINGLE+G]".format(arm))
        for variant, label in (("SINGLE+G", "Single"), ("MULTI-G", "Multi")):
            v = float(e7row(arm, "loose", variant)["wall_s_median"])
            wall[variant][arm] = v
            m.add("eThreeWall" + label + "Loose" + tok, num(v, 2),
                  "analysis/E7_e3_profiles.csv wall_s_median [{} / loose / {}]"
                  .format(arm, variant))
    nods_ppa = ", ".join(E3_ARMS_NO_DS)
    m.add("eThreeProposalsPerAcceptedLooseMin",
          num(min(ppa[a] for a in E3_ARMS_NO_DS), 2),
          "analysis/E7_e3_profiles.csv proposals_per_accepted_adjustment "
          "[loose / SINGLE+G], minimum over the five arms outside the DeepSeek "
          "wire artifact (" + nods_ppa + ")")
    m.add("eThreeProposalsPerAcceptedLooseMax",
          num(max(ppa[a] for a in E3_ARMS_NO_DS), 2),
          "analysis/E7_e3_profiles.csv proposals_per_accepted_adjustment "
          "[loose / SINGLE+G], maximum over the five arms outside the DeepSeek "
          "wire artifact (" + nods_ppa + ")")
    m.add("eThreeRevisedTrajectoriesLooseMin", group(min(revised.values())),
          "analysis/E7_e3_profiles.csv n_with_revision [loose / SINGLE+G], "
          "minimum over all six arms (" + allsix + ")")
    m.add("eThreeRevisedTrajectoriesLooseMax", group(max(revised.values())),
          "analysis/E7_e3_profiles.csv n_with_revision [loose / SINGLE+G], "
          "maximum over all six arms (" + allsix + ")")
    for variant, label in (("SINGLE+G", "Single"), ("MULTI-G", "Multi")):
        m.add("eThreeWall" + label + "LooseMin",
              num(min(wall[variant].values()), 2),
              "analysis/E7_e3_profiles.csv wall_s_median [loose / {}], minimum "
              "over all six arms ({})".format(variant, allsix))
        m.add("eThreeWall" + label + "LooseMax",
              num(max(wall[variant].values()), 2),
              "analysis/E7_e3_profiles.csv wall_s_median [loose / {}], maximum "
              "over all six arms ({})".format(variant, allsix))

    m.group("E3: the guard at fixed architecture",
            "MULTI-G against MULTI-UG on identical items: the paired quality "
            "difference and its Holm-corrected p-value "
            "(analysis/E8_adjudication.csv, loose budget, primary family).")
    deltas, ph_family, ph_agent = {}, {}, {}
    for arm in E3_ARMS:
        r = one(e8, arm=arm, budget_level="loose",
                contrast="MULTI-G vs MULTI-UG", test="wilcoxon_quality",
                in_primary_family="True")
        tok = ARM_TOKEN[arm]
        deltas[arm] = float(r["median_diff_nonzero"])
        ph_family[arm] = float(r["p_holm_family"])
        ph_agent[arm] = float(r["p_holm_agent_layer"])
        m.add("eThreeGuardQualityDelta" + tok,
              bh(r["median_diff_nonzero"], 2, signed=True),
              "analysis/E8_adjudication.csv median_diff_nonzero [{} / loose / "
              "MULTI-G vs MULTI-UG / wilcoxon_quality]".format(arm))
        m.add("eThreeGuardHolmP" + tok, sci(r["p_holm_agent_layer"]),
              "analysis/E8_adjudication.csv p_holm_agent_layer [{} / loose / "
              "MULTI-G vs MULTI-UG / wilcoxon_quality]".format(arm))
    sig = [a for a in E3_ARMS if ph_agent[a] < 0.05]
    m.add("eThreeGuardSignificantArms", str(len(sig)),
          "analysis/E8_adjudication.csv p_holm_agent_layer < 0.05 on the "
          "MULTI-G vs MULTI-UG quality test at the loose budget (" +
          ", ".join(sig) + ")")
    m.add("eThreeGuardTotalArms", str(len(E3_ARMS)),
          "analysis/e3_analysis_meta.json arms (length)")
    dsig = [deltas[a] for a in sig]
    m.add("eThreeGuardQualityDeltaMin", bh(min(dsig), 2, signed=True),
          "analysis/E8_adjudication.csv median_diff_nonzero, most negative over "
          "the {} Holm-significant arms ({})".format(len(sig), ", ".join(sig)))
    m.add("eThreeGuardQualityDeltaMax", bh(max(dsig), 2, signed=True),
          "analysis/E8_adjudication.csv median_diff_nonzero, least negative over"
          " the {} Holm-significant arms ({})".format(len(sig), ", ".join(sig)))
    m.add("eThreeGuardHolmPMin", sci(min(ph_agent[a] for a in sig)),
          "analysis/E8_adjudication.csv p_holm_agent_layer, minimum over the "
          "{} Holm-significant arms".format(len(sig)))
    m.add("eThreeGuardHolmPMax", sci(max(ph_agent[a] for a in sig)),
          "analysis/E8_adjudication.csv p_holm_agent_layer, maximum over the "
          "{} Holm-significant arms".format(len(sig)))

    # The median above is taken over the items on which the two configurations
    # differ, which is a minority of the slice; the prose has to say how many
    # items that is, and what the difference is over the whole slice, or the
    # reader reads a per-item median as if it applied to all 240 items.
    diff_items, mean_diff = {}, {}
    for arm in sig:
        r = one(e8, arm=arm, budget_level="loose",
                contrast="MULTI-G vs MULTI-UG", test="wilcoxon_quality",
                in_primary_family="True")
        diff_items[arm] = int(r["n_units"]) - int(r["n_zero_diff"])
        mean_diff[arm] = float(r["mean_diff"])
    sigset = ", ".join(sig)
    m.add("eEightDiffItemsMin", group(min(diff_items.values())),
          "analysis/E8_adjudication.csv n_units minus n_zero_diff [loose / "
          "MULTI-G vs MULTI-UG / wilcoxon_quality], minimum over the {} "
          "Holm-significant arms ({})".format(len(sig), sigset))
    m.add("eEightDiffItemsMax", group(max(diff_items.values())),
          "analysis/E8_adjudication.csv n_units minus n_zero_diff [loose / "
          "MULTI-G vs MULTI-UG / wilcoxon_quality], maximum over the {} "
          "Holm-significant arms ({})".format(len(sig), sigset))
    m.add("eEightMeanMin", bh(min(mean_diff.values()), 1, signed=True),
          "analysis/E8_adjudication.csv mean_diff [loose / MULTI-G vs "
          "MULTI-UG / wilcoxon_quality], most negative over the {} "
          "Holm-significant arms ({}); the mean runs over all 240 slice items,"
          " not only the differing ones".format(len(sig), sigset))
    m.add("eEightMeanMax", bh(max(mean_diff.values()), 1, signed=True),
          "analysis/E8_adjudication.csv mean_diff [loose / MULTI-G vs "
          "MULTI-UG / wilcoxon_quality], least negative over the {} "
          "Holm-significant arms ({})".format(len(sig), sigset))

    m.group("E3: the null result on the agent layer",
            "SINGLE+G against MULTI-G. Nothing is significant at the loose "
            "budget, on any test, on any arm.")
    prim = many(e8, contrast="SINGLE+G vs MULTI-G", in_primary_family="True")
    loose = [r for r in prim if r["budget_level"] == "loose"]
    wil = [r for r in prim if r["test"] == "wilcoxon_quality"]
    wil_loose = [r for r in loose if r["test"] == "wilcoxon_quality"]
    m.add("eThreeAgentCells", str(len(loose)),
          "analysis/E8_adjudication.csv rows [SINGLE+G vs MULTI-G / loose / "
          "primary family]: 4 tests x 6 arms")
    m.add("eThreeAgentSignificantCells",
          str(sum(1 for r in loose if float(r["p_holm_agent_layer"]) < 0.05)),
          "analysis/E8_adjudication.csv p_holm_agent_layer < 0.05 over those "
          "rows")
    m.add("eThreeAgentHolmMin",
          "{:.2f}".format(min(float(r["p_holm_agent_layer"]) for r in loose)),
          "analysis/E8_adjudication.csv p_holm_agent_layer, minimum over those "
          "rows")
    m.add("eThreeWilcoxonPMin",
          "{:.3f}".format(min(float(r["p_raw"]) for r in wil)),
          "analysis/E8_adjudication.csv p_raw [SINGLE+G vs MULTI-G / "
          "wilcoxon_quality / primary family], minimum over BOTH budget levels "
          "({} rows)".format(len(wil)))
    m.add("eThreeWilcoxonPMax",
          "{:.1f}".format(max(float(r["p_raw"]) for r in wil)),
          "analysis/E8_adjudication.csv p_raw [SINGLE+G vs MULTI-G / "
          "wilcoxon_quality / primary family], maximum over BOTH budget levels "
          "({} rows)".format(len(wil)))
    m.add("eThreeWilcoxonPLooseMin",
          "{:.3f}".format(min(float(r["p_raw"]) for r in wil_loose)),
          "analysis/E8_adjudication.csv p_raw [SINGLE+G vs MULTI-G / "
          "wilcoxon_quality / loose / primary family], minimum ({} rows)"
          .format(len(wil_loose)))
    m.add("eThreeAgentRawPLooseMin",
          "{:.3f}".format(min(float(r["p_raw"]) for r in loose)),
          "analysis/E8_adjudication.csv p_raw, minimum over all four tests at "
          "the loose budget ({} rows)".format(len(loose)))
    m.add("eThreeHolmFamilySize", one(prim, arm="qwen14b",
                                      budget_level="loose",
                                      test="wilcoxon_quality")["holm_m_family"],
          "analysis/E8_adjudication.csv holm_m_family (one question across arms "
          "and budgets)")
    m.add("eThreeHolmAgentLayerSize",
          one(prim, arm="qwen14b", budget_level="loose",
              test="wilcoxon_quality")["holm_m_agent_layer"],
          "analysis/E8_adjudication.csv holm_m_agent_layer (the whole "
          "agent-layer family at once)")
    m.add("eThreeMatchedTwins",
          one(prim, arm="qwen14b", budget_level="loose",
              test="mcnemar_false_block")["n_units"],
          "analysis/E8_adjudication.csv n_units [mcnemar_false_block]")
    m.add("eThreeWilcoxonUnits",
          one(prim, arm="qwen14b", budget_level="loose",
              test="wilcoxon_quality")["n_units"],
          "analysis/E8_adjudication.csv n_units [wilcoxon_quality]")

    m.group("E3: what the guard is worth in weighted business hours",
            "Mean end-task quality against the RULE anchor at the loose budget, "
            "unguarded against guarded (analysis/E7_e3_profiles.csv).")
    ug_multi, ug_any, g_all, w_ug, w_g = {}, {}, {}, [], []
    for arm in E3_ARMS:
        tok = ARM_TOKEN[arm]
        for variant, label in (("SINGLE+G", "SingleGuarded"),
                               ("MULTI-G", "MultiGuarded"),
                               ("MULTI-UG", "MultiUnguarded"),
                               ("SINGLE-UG *", "SingleUnguarded")):
            r = e7row(arm, "loose", variant)
            m.add("eThreeDamage" + label + tok,
                  bh(r["wwt_vs_rule_mean_bh"], 2, signed=True),
                  "analysis/E7_e3_profiles.csv wwt_vs_rule_mean_bh "
                  "[{} / loose / {}]".format(arm, variant))
            m.add("eThreeWarranted" + label + tok,
                  pct(r["warranted_outcome_rate"]),
                  "analysis/E7_e3_profiles.csv warranted_outcome_rate "
                  "[{} / loose / {}]".format(arm, variant))
            v = float(r["wwt_vs_rule_mean_bh"])
            w = float(r["warranted_outcome_rate"])
            if variant in ("MULTI-UG", "SINGLE-UG *"):
                w_ug.append(w)
                if arm != "deepseek":
                    ug_any[(arm, variant)] = v
                    if variant == "MULTI-UG":
                        ug_multi[arm] = v
            else:
                w_g.append(w)
                g_all[(arm, variant)] = v
    nods = ", ".join(E3_ARMS_NO_DS)
    m.add("eThreeDamageUnguardedMultiMin", bh(min(ug_multi.values()), 2, True),
          "analysis/E7_e3_profiles.csv wwt_vs_rule_mean_bh [loose / MULTI-UG], "
          "minimum over the five arms outside the DeepSeek wire artifact (" +
          nods + ")")
    m.add("eThreeDamageUnguardedMultiMax", bh(max(ug_multi.values()), 2, True),
          "analysis/E7_e3_profiles.csv wwt_vs_rule_mean_bh [loose / MULTI-UG], "
          "maximum over the five arms outside the DeepSeek wire artifact (" +
          nods + ")")
    m.add("eThreeDamageUnguardedMin", bh(min(ug_any.values()), 2, True),
          "analysis/E7_e3_profiles.csv wwt_vs_rule_mean_bh [loose / MULTI-UG "
          "and SINGLE-UG], minimum over the ten cells outside DeepSeek")
    m.add("eThreeDamageUnguardedMax", bh(max(ug_any.values()), 2, True),
          "analysis/E7_e3_profiles.csv wwt_vs_rule_mean_bh [loose / MULTI-UG "
          "and SINGLE-UG], maximum over the ten cells outside DeepSeek")
    m.add("eThreeDamageGuardedMin", bh(min(g_all.values()), 2, True),
          "analysis/E7_e3_profiles.csv wwt_vs_rule_mean_bh [loose / SINGLE+G "
          "and MULTI-G], minimum over all twelve guarded cells")
    m.add("eThreeDamageGuardedMax", bh(max(g_all.values()), 2, True),
          "analysis/E7_e3_profiles.csv wwt_vs_rule_mean_bh [loose / SINGLE+G "
          "and MULTI-G], maximum over all twelve guarded cells")
    m.add("eThreeWarrantedUnguardedMin", pct(min(w_ug)),
          "analysis/E7_e3_profiles.csv warranted_outcome_rate [loose / the two "
          "unguarded variants], minimum over all twelve cells")
    m.add("eThreeWarrantedUnguardedMax", pct(max(w_ug)),
          "analysis/E7_e3_profiles.csv warranted_outcome_rate [loose / the two "
          "unguarded variants], maximum over all twelve cells")
    m.add("eThreeWarrantedGuardedMin", pct(min(w_g)),
          "analysis/E7_e3_profiles.csv warranted_outcome_rate [loose / the two "
          "guarded variants], minimum over all twelve cells")
    m.add("eThreeWarrantedGuardedMax", pct(max(w_g)),
          "analysis/E7_e3_profiles.csv warranted_outcome_rate [loose / the two "
          "guarded variants], maximum over all twelve cells")

    m.group("E3: budget fragility and the wire-behaviour note",
            "Outcome orderings that reverse between the two budgets, and the "
            "vendor refusals the flagship's pipeline absorbed. The counts are "
            "taken over DISTINCT orderings: the architecture comparison only, "
            "because the guard comparison reverses nothing at all, and with "
            "the metrics that duplicate another metric's arithmetic dropped, "
            "because counting the same reversal twice inflates the count "
            "without adding evidence (corrected 2026-08-17; earlier drafts "
            "printed 18 and 16 over the raw row set).")
    # A row of E9 is one (arm, subject, metric) ordering compared across the
    # two budgets.  On the architecture comparison, which is the subject these
    # counts run over, three of the thirteen ordering metrics restate another
    # metric's arithmetic on the same items, so a reversal they show is a
    # reversal already counted:
    #   * wwt_vs_rule_mean_bh is wwt_original_mean_bh minus the SHARED no-AI
    #     anchor, so a difference between two configurations is identical to
    #     the raw difference and reverses with it;
    #   * variant_tokens_median equals all_tokens_median on every cell, which
    #     already counts the same token orderings;
    #   * wwt_original_median_bh's per-item median difference is exactly zero
    #     at both budgets on every arm, so it carries no ordering at all.
    # None of the three holds on the guard comparison, which is why the check
    # below is scoped to the architecture subject exactly as the counts are.
    # Each claim is CHECKED rather than trusted, because a de-duplication rule
    # that stopped being true would silently under-count.  The subject
    # restriction is checked the same way: the guard comparison must
    # contribute zero flips, or restricting to the architecture comparison
    # would be hiding a reversal.
    DUP_ORDERING_METRICS = {
        "outcome": {"wwt_vs_rule_mean_bh": "wwt_original_mean_bh",
                    "wwt_original_median_bh": None},
        "cost": {"variant_tokens_median": "all_tokens_median"},
    }
    # A second and different kind of duplicate: two READINGS of one outcome.
    # violation_pass_through is the disposition-only reading and
    # violation_pass_through_strict applies the V4/V6 content rule, so their
    # values differ and the equality check above does not apply; what makes
    # counting both a double count is that they order the same outcome.  The
    # published reading is kept and the earlier one dropped, and the claim is
    # checked on the thing the count uses: the two must flip on the same arms.
    REREAD_ORDERING_METRICS = {
        "outcome": {"violation_pass_through": "violation_pass_through_strict"},
        "cost": {},
    }
    ARCH_SUBJECT = "SINGLE+G minus MULTI-G"
    GUARD_SUBJECT = "MULTI-G minus MULTI-UG"
    orderings = [r for r in e9 if r["subject_kind"] == "ordering"]
    guard_flips = sum(1 for r in orderings if r["subject"] == GUARD_SUBJECT
                      and r["ordering_flips"] == "True")
    if guard_flips:
        raise LookupError_(
            "E9: the guard comparison reverses {} orderings, so the flip "
            "counts may not be restricted to the architecture comparison"
            .format(guard_flips))
    arch = [r for r in orderings if r["subject"] == ARCH_SUBJECT]
    for _dropped, _partner in [(d, p) for kind in DUP_ORDERING_METRICS
                               for d, p in DUP_ORDERING_METRICS[kind].items()]:
        for r in [x for x in arch if x["metric"] == _dropped]:
            if _partner is None:
                same = all(abs(float(r[col] or 0.0)) < 1e-9
                           for col in ("tight", "loose"))
            else:
                twin = one(arch, arm=r["arm"], metric=_partner)
                same = all(abs(float(r[col] or 0.0)
                               - float(twin[col] or 0.0)) < 1e-6
                           for col in ("tight", "loose"))
            if not same:
                raise LookupError_(
                    "E9: {} is dropped from the architecture ordering counts "
                    "as a restatement of {}, but the two disagree on {}"
                    .format(_dropped, _partner or "zero", r["arm"]))
    for _dropped, _partner in [(d, p) for kind in REREAD_ORDERING_METRICS
                               for d, p in REREAD_ORDERING_METRICS[kind].items()]:
        for r in [x for x in arch if x["metric"] == _dropped]:
            twin = one(arch, arm=r["arm"], metric=_partner)
            if r["ordering_flips"] != twin["ordering_flips"]:
                raise LookupError_(
                    "E9: {} is dropped from the architecture ordering counts "
                    "as the earlier reading of {}, but the two readings "
                    "disagree about whether {} reverses"
                    .format(_dropped, _partner, r["arm"]))
    for kind, label in (("outcome", "Outcome"), ("cost", "Cost")):
        skip = set(DUP_ORDERING_METRICS[kind]) | set(REREAD_ORDERING_METRICS[kind])
        cells = [r for r in orderings
                 if r["subject"] == ARCH_SUBJECT and r["metric_kind"] == kind
                 and r["metric"] not in skip]
        # An ordering whose tight column is empty is undefined at the tight
        # budget (no certified gap to order), so it is not a cell that could
        # have reversed and is out of the denominator.
        defined = [r for r in cells if r["tight"].strip() != ""]
        undefined = [r for r in cells if r["tight"].strip() == ""]
        dropped = ", ".join(sorted(skip))
        m.add("eThreeOrderingFlips" + label,
              str(sum(1 for r in defined if r["ordering_flips"] == "True")),
              "analysis/E9_budget_effect.csv ordering_flips=True with "
              "subject_kind=ordering, subject '{}' and metric_kind={}, over "
              "the metrics that are not restatements of another metric "
              "(dropped: {})".format(ARCH_SUBJECT, kind, dropped))
        m.add("eThreeOrderingCells" + label, str(len(defined)),
              "analysis/E9_budget_effect.csv rows with subject_kind=ordering, "
              "subject '{}' and metric_kind={}, after dropping {} and the {} "
              "row(s) undefined at the tight budget ({})".format(
                  ARCH_SUBJECT, kind, dropped, len(undefined),
                  ", ".join("{} / {}".format(r["arm"], r["metric"])
                            for r in undefined) or "none"))
    # Retained because the figure script and the older comparison sentences
    # cite it; the de-duplicated counts above are the ones the prose prints.
    m.add("eThreeOrderingsCompared",
          str(sum(1 for r in e9 if r["subject_kind"] == "ordering")),
          "analysis/E9_budget_effect.csv rows with subject_kind=ordering")
    grid_row = one(e13, arm="opus", scope="grid")
    cal_row = one(e13, arm="opus", scope="calibration")
    m.add("eThreeOpusVendorRefusedCalls",
          group(int(grid_row["calls_refusal"])),
          "analysis/E13_e3_costs.csv calls_refusal [opus / grid]")
    m.add("eThreeOpusVendorRefusedCallsAll",
          group(int(grid_row["calls_refusal"]) + int(cal_row["calls_refusal"])),
          "analysis/E13_e3_costs.csv calls_refusal [opus / grid + calibration]")
    m.add("eThreeOpusTerminalRefusals", "0",
          "analysis/E7_e3_profiles.csv n_model_refused is zero in every cell: "
          "no vendor refusal landed on a first final")


def build_ladder(m: Macros) -> None:
    t4 = read_csv("T4")
    t5 = read_csv("T5")
    e12 = read_csv("E12")
    anchors = read_json("ladder_anchors")
    rep = re.sub(r"\s+", " ", read_text("consolidation"))

    m.group("The as-is / to-be ladder",
            "One ordered walk from no-AI dispatch to the guarded arms, on the "
            "same 2,000 instructions (analysis/T4, T5, ladder/).")

    rule = one(t4, system="RULE", scope="full_suite")
    orc = one(t4, system="ORACLE", scope="full_suite")
    orcg = one(t4, system="ORACLE+G_CERT", scope="full_suite")
    m.add("ladRuleMeanWwt", bh(rule["wwt_original_mean_bh"]),
          "analysis/T4_trustworthiness.csv wwt_original_mean_bh "
          "[RULE / full_suite]")
    m.add("ladRuleItems", group(rule["items"]),
          "analysis/T4_trustworthiness.csv items [RULE / full_suite]")
    m.add("ladOracleMeanWwt", bh(orc["wwt_original_mean_bh"]),
          "analysis/T4_trustworthiness.csv wwt_original_mean_bh "
          "[ORACLE / full_suite]")
    m.add("ladOracleVsRule", bh(orc["wwt_original_vs_rule_bh"], 2, signed=True),
          "analysis/T4_trustworthiness.csv wwt_original_vs_rule_bh "
          "[ORACLE / full_suite]")
    m.add("ladOracleGuardedVsRule",
          bh(orcg["wwt_original_vs_rule_bh"], 2, signed=True),
          "analysis/T4_trustworthiness.csv wwt_original_vs_rule_bh "
          "[ORACLE+G_CERT / full_suite]")
    m.add("ladOracleWarranted", pct(orc["warranted_outcome_rate"]),
          "analysis/T4_trustworthiness.csv warranted_outcome_rate "
          "[ORACLE / full_suite]")
    m.add("ladOracleGuardedWarranted", pct(orcg["warranted_outcome_rate"]),
          "analysis/T4_trustworthiness.csv warranted_outcome_rate "
          "[ORACLE+G_CERT / full_suite]")
    m.add("ladOraclePassThrough", pct(orc["violation_pass_through_strict"]),
          "analysis/T4_trustworthiness.csv violation_pass_through_strict "
          "[ORACLE / full_suite]: " + STRICT_RULE)
    m.add("ladOracleGuardedPassThrough",
          pct(orcg["violation_pass_through_strict"]),
          "analysis/T4_trustworthiness.csv violation_pass_through_strict "
          "[ORACLE+G_CERT / full_suite] (Table 7 rung 2a): " + STRICT_RULE)

    m.group("The ORACLE-equals-flagship finding",
            "A perfectly attentive human translator produces the damage the "
            "flagship produces, because the damage is in the instruction and "
            "not in the translation (analysis/ladder/ladder_anchors.json, "
            "analysis/T3_guard_value_curve.csv).")
    pc = anchors["anchors"]["per_class"]
    ov3 = pc["ORACLE"]["V3"]
    rv3 = pc["RULE"]["V3"]
    damage = (float(ov3["wwt_original_mean_bh"])
              - float(rv3["wwt_original_mean_bh"]))
    m.add("ladOracleVThreeVsRule", bh(damage, 2, signed=True),
          "analysis/ladder/ladder_anchors.json anchors.per_class.ORACLE.V3."
          "wwt_original_mean_bh minus anchors.per_class.RULE.V3."
          "wwt_original_mean_bh")
    m.add("ladOracleVThreeItems", group(ov3["n"]),
          "analysis/ladder/ladder_anchors.json anchors.per_class.ORACLE.V3.n")
    m.add("ladOracleVThreeGapMedian", num(ov3["certified_gap_median"], 6),
          "analysis/ladder/ladder_anchors.json anchors.per_class.ORACLE.V3."
          "certified_gap_median")
    m.add("ladOracleVThreeGapMax", num(ov3["certified_gap_max"], 4),
          "analysis/ladder/ladder_anchors.json anchors.per_class.ORACLE.V3."
          "certified_gap_max")
    t3 = read_csv("T3")
    opus = one(t3, arm="opus", mode="M_constrained", thinking="default")
    m.add("ladOpusVThreeGapMedian", num(opus["v3_gap_median"], 6),
          "analysis/T3_guard_value_curve.csv v3_gap_median [opus / default]")
    m.add("ladOpusVThreeGapMax", num(opus["v3_gap_max"], 4),
          "analysis/T3_guard_value_curve.csv v3_gap_max [opus / default]")
    m.add("ladOpusVThreeCertificates", group(opus["v3_feas_pass"]),
          "analysis/T3_guard_value_curve.csv v3_feas_pass [opus / default]")

    m.group("The three-stage demonstration",
            "The single worst executed schedule in the study, and why the "
            "quality gate alone would have accepted it "
            "(analysis/consolidation_report.md, data-quality observation 2; "
            "the tardiness figure is also T4's wwt_original_max_bh for the "
            "27B unguarded cell).")
    item = re.search(r"the whole study is item `(V\d-\d+)`", rep)
    wwt = re.search(r"executes a schedule with \*\*([\d,]+) bh\*\*", rep)
    ratio = re.search(r"about ([\d,]+) times the RULE", rep)
    gap = re.search(r"certified gap of that schedule is \*\*([\d.]+)\*\*", rep)
    m.add("ladWorstItem", item.group(1) if item else todo("worst-item id"),
          "analysis/consolidation_report.md, data-quality observation 2")
    if wwt:
        m.add("ladWorstWwt", wwt.group(1).replace(",", "{,}"),
              "analysis/consolidation_report.md, data-quality observation 2 "
              "(equals T4_trustworthiness.csv wwt_original_max_bh for "
              "qwen3.6-27b-fp8 / UNGUARDED / full_suite)")
    else:
        m.add("ladWorstWwt", todo("worst executed schedule, weighted tardiness"),
              "analysis/consolidation_report.md: pattern not found")
    m.add("ladWorstRatio", ratio.group(1).replace(",", "{,}") if ratio
          else todo("worst schedule vs its RULE anchor, multiple"),
          "analysis/consolidation_report.md, data-quality observation 2")
    m.add("ladWorstGap", gap.group(1) if gap
          else todo("certified gap of the worst executed schedule"),
          "analysis/consolidation_report.md, data-quality observation 2")
    shift = re.search(r"release_shift_bh = (\d+)", rep)
    m.add("ladWorstShiftBh", group(shift.group(1)) if shift
          else todo("the release shift two arms emit for 'indefinitely'"),
          "analysis/consolidation_report.md, data-quality observation 2 (the "
          "release_shift_bh the 27B and mini arms emit for 'indefinitely', "
          "outside the published legality range)")
    m.add("ladMaxShiftBh", group(
        read_json("suite_manifest")["conventions"]["max_abs_release_shift_bh"]),
        "code/suite/v0.2/manifest.json conventions.max_abs_release_shift_bh "
        "(the published legality range the schema stage enforces)")

    m.group("The guard rungs on the full suite",
            "G-CERT returns end-task quality to the no-AI anchor; G-FEAS does "
            "not (analysis/T5_ladder.csv, full_suite scope).")
    gcert, gfeas, ung = {}, {}, {}
    gcert_w, gfeas_w = {}, {}
    t5_arms = sorted({r["arm"] for r in t5 if r["arm"]})
    for arm, think in CONSTRAINED_ROWS:
        if arm not in t5_arms or think != PRIMARY_THINKING[arm]:
            continue
        mode = "M_constrained / " + think
        tok = ARM_TOKEN[arm]
        for step, label, store in (("3. UNGUARDED", "ladUnguardedVsRule", ung),
                                   ("4. G-FEAS", "ladFeasVsRule", gfeas),
                                   ("5. G-CERT", "ladCertVsRule", gcert)):
            r = one(t5, arm=arm, step=step, scope="full_suite", mode=mode)
            store[arm] = float(r["wwt_original_vs_rule_bh"])
            m.add(label + tok, bh(r["wwt_original_vs_rule_bh"], 2, signed=True),
                  "analysis/T5_ladder.csv wwt_original_vs_rule_bh "
                  "[{} / {} / {} / full_suite]".format(arm, step, mode))
            m.add(label.replace("VsRule", "Warranted") + tok,
                  pct(r["warranted_outcome_rate"]),
                  "analysis/T5_ladder.csv warranted_outcome_rate "
                  "[{} / {} / {} / full_suite]".format(arm, step, mode))
            if step == "4. G-FEAS":
                gfeas_w[arm] = float(r["warranted_outcome_rate"])
            elif step == "5. G-CERT":
                gcert_w[arm] = float(r["warranted_outcome_rate"])
            m.add(label.replace("VsRule", "PassThrough") + tok,
                  pct(r["violation_pass_through_strict"]),
                  "analysis/T5_ladder.csv violation_pass_through_strict "
                  "[{} / {} / {} / full_suite]: {}".format(
                      arm, step, mode, STRICT_RULE))
            if step == "5. G-CERT" and arm == "opus":
                # Appendix E's lower bound on the same cell.  It is the only
                # place the fault reading is published, so it is emitted here
                # rather than in a loop of its own.
                m.add("ladCertPassThroughFaultOpus",
                      pct(r["violation_pass_through_fault"]),
                      "analysis/T5_ladder.csv violation_pass_through_fault "
                      "[{} / {} / {} / full_suite]: {}".format(
                          arm, step, mode, FAULT_RULE))
    covered = ", ".join(sorted(gcert))
    for label, store in (("ladUnguardedVsRule", ung), ("ladFeasVsRule", gfeas),
                         ("ladCertVsRule", gcert)):
        sub = {a: v for a, v in store.items() if a != "deepseek"}
        m.add(label + "Min", bh(min(sub.values()), 2, signed=True),
              "analysis/T5_ladder.csv wwt_original_vs_rule_bh, minimum over the "
              "constrained rungs T5 covers outside DeepSeek (" +
              ", ".join(sorted(sub)) + ")")
        m.add(label + "Max", bh(max(sub.values()), 2, signed=True),
              "analysis/T5_ladder.csv wwt_original_vs_rule_bh, maximum over the "
              "constrained rungs T5 covers outside DeepSeek (" +
              ", ".join(sorted(sub)) + ")")
    for label, store in (("ladFeasWarranted", gfeas_w),
                         ("ladCertWarranted", gcert_w)):
        sub = {a: v for a, v in store.items() if a != "deepseek"}
        m.add(label + "Min", pct(min(sub.values())),
              "analysis/T5_ladder.csv warranted_outcome_rate, minimum over the "
              "schema-enforced arms (" + ", ".join(sorted(sub)) + ")")
        m.add(label + "Max", pct(max(sub.values())),
              "analysis/T5_ladder.csv warranted_outcome_rate, maximum over the "
              "schema-enforced arms (" + ", ".join(sorted(sub)) + ")")
    m.add("ladLadderArms", str(len(gcert)),
          "analysis/T5_ladder.csv arms carrying the guard rungs (" + covered + ")")

    # The referral load of the flagship's certified rung: the share of
    # instructions the guard refuses, which is the share that reaches a person
    # with the findings and the certificate attached (Section 6.5).  The two
    # blocked shares are disjoint by construction, so their sum is the load.
    opus_cert = one(t5, arm="opus", step="5. G-CERT", scope="full_suite",
                    mode="M_constrained / " + PRIMARY_THINKING["opus"])
    blocked_ok = float(opus_cert["share_blocked_correctly"])
    blocked_false = float(opus_cert["share_blocked_falsely"])
    m.add("ladCertBlockedCorrectlyOpus", pct(blocked_ok),
          "analysis/T5_ladder.csv share_blocked_correctly [opus / 5. G-CERT / "
          "M_constrained / " + PRIMARY_THINKING["opus"] + " / full_suite]")
    m.add("ladCertBlockedFalselyOpus", pct(blocked_false),
          "analysis/T5_ladder.csv share_blocked_falsely [opus / 5. G-CERT / "
          "M_constrained / " + PRIMARY_THINKING["opus"] + " / full_suite]")
    m.add("ladCertReferredOpus", pct(blocked_ok + blocked_false),
          "analysis/T5_ladder.csv share_blocked_correctly plus "
          "share_blocked_falsely [opus / 5. G-CERT / M_constrained / " +
          PRIMARY_THINKING["opus"] + " / full_suite]: the share of "
          "instructions the guard refuses and refers with its evidence")

    m.group("The ladder on the E3 slice",
            "The two agent rungs T5 prints as pending, computed on the 240-item "
            "slice against that slice's own RULE anchor "
            "(analysis/E12_ladder_e3_rungs.csv).")
    orc12 = many(e12, step="2. ORACLE", scope="e3_240")
    if orc12:
        m.add("ladSliceOracleVsRule",
              bh(orc12[0]["wwt_original_vs_rule_bh"], 2, signed=True),
              "analysis/E12_ladder_e3_rungs.csv wwt_original_vs_rule_bh "
              "[2. ORACLE, E3-240 slice]")
        m.add("ladSliceItems", group(orc12[0]["items"]),
              "analysis/E12_ladder_e3_rungs.csv items [2. ORACLE]")


def build_costs(m: Macros) -> None:
    e13 = read_csv("E13")

    # --- constants of record -------------------------------------------------
    # The E1/E2 side of the ledger is not in analysis/: it is the auditable
    # token ledger the orchestrator recomputed over all raw logs and pilots and
    # entered in decisions.md.  Those entries are the accepted source, quoted
    # here verbatim rather than recomputed.
    LEDGER = [
        # (macro suffix, USD, decisions.md entry)
        ("Deepseek", 9.01, "2026-08-12 'top-ups received; spend ledger reconciled'"),
        ("Mini", 10.39, "2026-08-12 'top-ups received; spend ledger reconciled'"),
        ("Sol", 25.83, "2026-08-12 'top-ups received; spend ledger reconciled'"),
        ("TerraPilot", 0.19, "2026-08-12 'top-ups received; spend ledger reconciled'"),
        ("Sonnet", 20.74, "2026-08-12 'top-ups received; spend ledger reconciled'"),
        ("OpusCore", 34.66, "2026-08-12 'top-ups received; spend ledger reconciled'"),
    ]
    LEDGER_TOTAL = 100.81
    LEDGER_PILOTS = 1.06
    OPUS_RELAUNCH = 79.16     # decisions.md 2026-08-13 'evaluator eval-2 ... FULL opus arm evaluated'
    CACHE_SAVED = 63.03
    CACHE_ACTUAL = 55.07
    CACHE_UNCACHED = 118.10
    CACHE_SHARE = 67.7
    CACHE_PROMPT_CACHED_M = 22.27
    CACHE_PROMPT_TOTAL_M = 32.88
    # Project-wide prompt-cache saving on the Anthropic arms, taken from the
    # provider's own billing record (author, 2026-08-15). The four constants
    # above are the 2026-08-12 phase figures and are superseded for reporting
    # by this one; they stay defined because decisions.md quotes them. A
    # list-price recomputation over the released call logs is recorded in
    # decisions.md 2026-08-15 as a cross-check; it uses a different basis
    # (list prices, cache-write premium charged) and is not what the paper
    # prints.
    CACHE_SAVED_PROJECT = 117.00

    m.group("Cost: the experiment-cost disclosure",
            "The author-directed Section 6.7 disclosure. The E1/E2 side is the "
            "auditable token ledger recorded in decisions.md (every logged paid "
            "call priced at the pinned per-arm rates); the E3 side is E13, "
            "which reconciles the recomputation against every run meta.")

    for suffix, amount, entry in LEDGER:
        m.add("costEOne" + suffix + "Usd", usd(amount),
              "decisions.md " + entry + " (auditable token ledger)")
    m.add("costEOneLedgerTotalUsd", usd(LEDGER_TOTAL),
          "decisions.md 2026-08-12 'top-ups received; spend ledger reconciled': "
          "TOTAL USD through the checkpoint")
    m.add("costPilotsUsd", usd(LEDGER_PILOTS),
          "decisions.md 2026-08-12 'top-ups received; spend ledger reconciled': "
          "of which pilots")
    m.add("costEOneOpusRelaunchUsd", usd(OPUS_RELAUNCH),
          "decisions.md 2026-08-13 'evaluator eval-2; FULL opus arm evaluated': "
          "Opus E1 actual cost this relaunch")
    m.add("costEOneOpusTotalUsd", usd(34.66 + OPUS_RELAUNCH),
          "decisions.md: Opus E1 core (34.66) plus the relaunched remainder "
          "(79.16)")

    m.add("costVendorDeepseekUsd", usd(9.01),
          "decisions.md 2026-08-12 ledger: DeepSeek vendor total")
    m.add("costVendorOpenaiUsd", usd(36.40),
          "decisions.md 2026-08-12 ledger: OpenAI vendor total "
          "(mini 10.39 + Sol 25.83 + Terra pilot 0.19)")
    m.add("costVendorAnthropicUsd", usd(55.40),
          "decisions.md 2026-08-12 ledger: Anthropic vendor total through the "
          "checkpoint (Sonnet 20.74 + Opus 34.66)")

    e3_all = one(e13, arm="ALL", scope="grid + calibration")
    m.add("costEThreeTotalUsd", usd(e3_all["usd_recomputed"]),
          "analysis/E13_e3_costs.csv usd_recomputed [ALL / grid + calibration]")
    m.add("costEThreeCalls", group(e3_all["calls"]),
          "analysis/E13_e3_costs.csv calls [ALL / grid + calibration]")
    m.add("costEThreeTokens", group(e3_all["all_tokens"]),
          "analysis/E13_e3_costs.csv all_tokens [ALL / grid + calibration]")
    m.add("costEThreeUsdPerTrajectory", num(e3_all["usd_per_trajectory"], 4),
          "analysis/E13_e3_costs.csv usd_per_trajectory "
          "[ALL / grid + calibration]")
    m.add("costEThreeTrajectories", group(e3_all["trajectories"]),
          "analysis/E13_e3_costs.csv trajectories [ALL / grid + calibration]")

    for arm in E3_ARMS:
        tok = ARM_TOKEN[arm]
        g = one(e13, arm=arm, scope="grid")
        c = one(e13, arm=arm, scope="calibration")
        total = float(g["usd_recomputed"]) + float(c["usd_recomputed"])
        m.add("costEThree" + tok + "Usd", usd(total),
              "analysis/E13_e3_costs.csv usd_recomputed [{} / grid] plus "
              "[{} / calibration]".format(arm, arm))
        m.add("costEThree" + tok + "Calls",
              group(int(g["calls"]) + int(c["calls"])),
              "analysis/E13_e3_costs.csv calls [{} / grid + calibration]"
              .format(arm))
        m.add("costEThree" + tok + "Tokens",
              group(int(g["all_tokens"]) + int(c["all_tokens"])),
              "analysis/E13_e3_costs.csv all_tokens [{} / grid + calibration]"
              .format(arm))
        if float(g["usd_tight"] or 0) or float(g["usd_loose"] or 0):
            m.add("costEThree" + tok + "TightUsd", usd(g["usd_tight"]),
                  "analysis/E13_e3_costs.csv usd_tight [{} / grid]".format(arm))
            m.add("costEThree" + tok + "LooseUsd", usd(g["usd_loose"]),
                  "analysis/E13_e3_costs.csv usd_loose [{} / grid]".format(arm))

    project = LEDGER_TOTAL + OPUS_RELAUNCH + float(e3_all["usd_recomputed"])
    m.add("costProjectTotalUsd", usd(project),
          "decisions.md ledger (100.81) plus the Opus E1 relaunch (79.16) plus "
          "analysis/E13_e3_costs.csv usd_recomputed [ALL] (41.66)")
    m.add("costProjectUncachedUsd", usd(project + CACHE_SAVED_PROJECT),
          "decisions.md 2026-08-15 'prompt-cache saving': the billed "
          "programme total plus the provider-recorded saving on the Anthropic "
          "arms, i.e. what the same calls cost without prompt caching")
    m.add("costLocalArmUsd", usd(0.0),
          "analysis/E13_e3_costs.csv usd_recomputed [qwen14b, qwen27b]: local "
          "weights carry an explicit zero API price (electricity only)")

    m.group("Cost: prompt caching",
            "Explicit per-block cache breakpoints on the Anthropic arms "
            "(decisions.md 2026-08-12).")
    m.add("costCacheSavedUsd", usd(CACHE_SAVED),
          "decisions.md 2026-08-12 'Prompt caching': saved against the uncached "
          "price")
    m.add("costCacheActualUsd", usd(CACHE_ACTUAL),
          "decisions.md 2026-08-12 'Prompt caching': actual Claude cost")
    m.add("costCacheUncachedUsd", usd(CACHE_UNCACHED),
          "decisions.md 2026-08-12 'Prompt caching': the same work uncached")
    m.add("costCacheHitShare", pct_of(CACHE_SHARE),
          "decisions.md 2026-08-12 'Prompt caching': prompt tokens read from "
          "cache")
    m.add("costCachePromptTokensCachedM", num(CACHE_PROMPT_CACHED_M, 2),
          "decisions.md 2026-08-12 'Prompt caching': cached prompt tokens, "
          "millions")
    m.add("costCachePromptTokensTotalM", num(CACHE_PROMPT_TOTAL_M, 2),
          "decisions.md 2026-08-12 'Prompt caching': total prompt tokens, "
          "millions")
    m.add("costCacheSavedProjectUsd", usd(CACHE_SAVED_PROJECT),
          "decisions.md 2026-08-15 'prompt-cache saving': the provider's "
          "billing record for the Anthropic arms over the whole programme; "
          "this is the figure Section 6.7 prints")

    # --- the pinned price table ---------------------------------------------
    # Constants of record, not computed: the prices in force on the retrieval
    # date, pinned in decisions.md and in the runner's own ARM table
    # (code/scripts/grid_e1_hosted.py).  The retrieval date is part of the
    # number, so it is a macro too.
    PRICES = [
        # token, in, out, cache-read, cache-write, date, label
        ("Deepseek", "0.435", "0.87", "0.003625", None, "2026-08-11",
         "list price; the page announces a coming increase"),
        ("Mini", "0.75", "4.50", "0.075", None, "2026-08-11", "list price"),
        ("Sol", "5.00", "30.00", "0.50", None, "2026-08-12", "list price"),
        ("Sonnet", "2.00", "10.00", "0.20", "2.50", "2026-08-11",
         "introductory price through 2026-08-31"),
        ("SonnetStandard", "3.00", "15.00", "0.30", "3.75", "2026-08-11",
         "standard price from 2026-09-01"),
        ("Opus", "5.00", "25.00", "0.50", "6.25", "2026-08-11", "list price"),
    ]
    m.group("Cost: the pinned price table",
            "Prices are USD per million tokens, in force on the retrieval date. "
            "These are constants of record from decisions.md (model pins, "
            "2026-08-11 and 2026-08-12 entries) and the runner's own ARM table "
            "in code/scripts/grid_e1_hosted.py; they are not recomputed here. "
            "The retrieval date is part of the number.")
    src = ("decisions.md model-pin entries + code/scripts/grid_e1_hosted.py "
           "ARMS[*].prices")
    for tok, pin, pout, cread, cwrite, date, label in PRICES:
        m.add("price" + tok + "In", pin, src + " ({}, input)".format(label))
        m.add("price" + tok + "Out", pout, src + " ({}, output)".format(label))
        m.add("price" + tok + "CacheRead", cread,
              src + " ({}, cache read)".format(label))
        if cwrite:
            m.add("price" + tok + "CacheWrite", cwrite,
                  src + " ({}, five-minute cache write)".format(label))
        m.add("price" + tok + "Date", date,
              src + " price_date (retrieval date)")

    # Cross-check the hardcoded retrieval dates against E13's own price_date.
    e13_dates = {"openai": "Mini", "deepseek": "Deepseek", "sonnet": "Sonnet",
                 "opus": "Opus"}
    pinned = {t: d for t, _, _, _, _, d, _ in PRICES}
    for arm, tok in e13_dates.items():
        got = one(e13, arm=arm, scope="grid")["price_date"]
        if got != pinned[tok]:
            raise LookupError_(
                "price_date drift for {}: E13 says {}, the pinned table says {}"
                .format(arm, got, pinned[tok]))


def build_local_compute(m: Macros) -> None:
    """Workstation GPU time behind the three local arms.

    Section 6.7 pairs the USD figure with the GPU time the open-weights arms
    cost instead.  The sum is over every pass that occupied the card: the
    three E1 generation grids and the four E3 passes (two calibration, two
    grid).  Hosted arms are API calls and hold no GPU, so nothing else
    belongs in it.
    """
    seconds, named = 0.0, []
    for key, path, field in LOCAL_WALL_META:
        meta = read_json(key)
        if field == "walls_s":
            passes = meta["walls_s"]
            if not passes:
                raise LookupError_("empty walls_s in " + str(path))
            seconds += sum(float(v) for v in passes.values())
        else:
            seconds += float(meta["tally"]["wall_s"])
        named.append(str(path.relative_to(ROOT)))

    m.group("Local compute",
            "The GPU time the three open-weights arms cost, against the USD "
            "the five hosted arms cost. Summed over every pass that held the "
            "workstation GPU: the three E1 generation grids (each wall in "
            "walls_s, one per mode and repeat) and the four E3 passes (two "
            "calibration, two grid; tally.wall_s each). Measured on one "
            "NVIDIA RTX PRO 5000 Blackwell 48 GB card, one pass at a time.")
    m.add("costLocalGpuHours", num(seconds / 3600.0, 1),
          "sum of walls_s / tally.wall_s over " + "; ".join(named))

    # How many arms ran on the workstation rather than against a paid
    # endpoint.  An arm is local when its E1 evaluation read a raw log written
    # by one of the grid_e1_local* generation passes; the hosted arms read a
    # grid_e1_hosted_* log.  Section 6.7 sets this count against \nEOneArms.
    local_arms = sorted(
        arm for d, arm in E1_DIR_ARM.items()
        if Path(read_json("e1_" + d)["run"]["raw_path"]).parent.name
        .startswith("grid_e1_local"))
    n_local_grids = sum(1 for key, _p, _f in LOCAL_WALL_META
                        if key.startswith("localEOne"))
    if len(local_arms) != n_local_grids:
        raise LookupError_(
            "{} arms read a grid_e1_local raw log ({}), but LOCAL_WALL_META "
            "names {} local E1 generation grids".format(
                len(local_arms), ", ".join(local_arms), n_local_grids))
    m.add("costLocalArms", str(len(local_arms)),
          "results/e1_eval_*/summary.json run.raw_path: arms whose E1 raw log "
          "came from a grid_e1_local* pass (" + ", ".join(local_arms) + ")")


#: tier1_slice stratum key -> macro token, the same vocabulary the suite
#: group uses, so \nSuiteStratumConfirmationItems and
#: \guardLatencyConfirmationMs name the same stratum.
TIER_STRATUM_TOKEN = {
    "c09_storm2_w80": "Primary",
    "c10_storm2_w80": "Confirmation",
    "c10_replay_400": "Buildings",
}

#: budget in seconds -> macro suffix
TIER_BUDGET_TOKEN = {"1": "OneS", "5": "FiveS"}


def build_guard_latency(m: Macros) -> None:
    """Single-stream, per-stage guard latency (tier1_slice latency phase).

    This is a latency measurement and not a throughput one: one proposal at a
    time, pinned to one core, every numerical runtime capped at one thread,
    and the bulk comparison of the same run not yet started.  Section 6.7
    reports it beside the concurrent E3 trajectory times, which measure a
    different thing.
    """
    lat = read_json("tier1_slice")["latency"]
    run = read_json("tier1_slice")["run"]
    src = "results/tier1_slice/summary.json latency"
    ov = lat["overall"]

    m.group("Guard latency, single stream",
            "The deployed guard's added latency, measured on a "
            "{}-row sub-sample of the Tier-1 slice: one proposal at a time, "
            "pinned to core(s) {}, every numerical runtime capped at one "
            "thread, with the bulk comparison not yet running. The three "
            "stages are schema, feasibility and quality (Tier 2), and the "
            "whole-guard row is their sum on the same proposal. Milliseconds "
            "here are unitless: prose adds the unit."
            .format(ov["n"], ", ".join(str(c) for c in run["latency_cores"])))

    m.add("nGuardLatencyRows", group(ov["n"]),
          src + ".overall.guard_total_tier2_ms.n (rows in the latency phase)")
    m.add("guardAddedLatencyMs", num(ov["guard_total_tier2_ms"]["median"], 2),
          src + ".overall.guard_total_tier2_ms.median (whole guard, Tier 2, "
                "median ms)")
    m.add("guardAddedLatencyPNinetyMs",
          num(ov["guard_total_tier2_ms"]["p90"], 1),
          src + ".overall.guard_total_tier2_ms.p90 (whole guard, Tier 2, "
                "90th-percentile ms)")
    m.add("guardAddedLatencyMaxMs",
          num(ov["guard_total_tier2_ms"]["max"], 1),
          src + ".overall.guard_total_tier2_ms.max (whole guard, Tier 2, "
                "maximum ms)")
    for field, token, what in (
            ("schema_ms", "guardSchemaStageMs", "stage 1, schema"),
            ("feas_ms", "guardFeasStageMs", "stage 2, feasibility"),
            ("qual_tier2_ms", "guardQualStageMs", "stage 3, quality, Tier 2")):
        m.add(token, num(ov[field]["median"], 2),
              "{}.overall.{}.median ({}, median ms)".format(src, field, what))
    m.add("guardTierOneLatencyMs",
          num(ov["guard_total_tier1_1s_ms"]["median"], 0),
          src + ".overall.guard_total_tier1_1s_ms.median (whole guard with "
                "the quality stage configured to Tier 1 at a 1 s budget, "
                "median ms, one worker on one pinned core)")

    for key, token in TIER_STRATUM_TOKEN.items():
        st = lat["by_stratum"][key]
        m.add("guardLatency" + token + "Ms",
              num(st["guard_total_tier2_ms"]["median"], 2),
              "{}.by_stratum.{}.guard_total_tier2_ms.median (whole guard, "
              "Tier 2, median ms)".format(src, key))
        m.add("guardLatency" + token + "PNinetyMs",
              num(st["guard_total_tier2_ms"]["p90"], 1),
              "{}.by_stratum.{}.guard_total_tier2_ms.p90 (whole guard, "
              "Tier 2, 90th-percentile ms)".format(src, key))
        m.add("guardFeas" + token + "Ms", num(st["feas_ms"]["median"], 2),
              "{}.by_stratum.{}.feas_ms.median (stage 2, feasibility, median "
              "ms)".format(src, key))


def build_tiers(m: Macros) -> None:
    """Tier 1 against Tier 2 on identical rows, at two solver budgets.

    Every sampled row is one the accepted Tier-2 certificate accepted, so the
    comparison is a comparison of bounds on one schedule rather than of two
    independent readings: the run re-evaluates each row under the accepted
    Tier-2 configuration and asserts it reproduces the accepted terminal and
    the accepted certified gap before its Tier-1 numbers are used.
    """
    slice_ = read_json("tier1_slice")
    run, ov, rep = slice_["run"], slice_["overall"], slice_["reproduction"]
    src = "results/tier1_slice/summary.json"

    m.group("Tier comparison",
            "Tier 1 (CP-SAT at a per-proposal budget) against Tier 2 (the "
            "analytic bound) on the same rows, the same adjusted instances "
            "and the same executed schedules. The Tier-1 bound lives on a "
            "centi-business-hour grid, so a tightness delta smaller than that "
            "discretization is not evidence that the solver bound is sharper; "
            "a budget that proves nothing returns a valid but vacuous 0.0, "
            "and the vacuous share is reported per budget and never averaged "
            "away. Refusal shares are at tau = {:.2f}. Wall times: Tier 1 in "
            "seconds, Tier 2 in milliseconds."
            .format(float(run["configs"]["CFG_T2"]["tau"])))

    m.add("nTierRows", group(run["n_rows"]),
          src + " run.n_rows (rows compared, both budgets)")
    m.add("nTierRowsCore", group(run["n_part_a"]),
          src + " run.n_part_a (part A: the census of certified V3 rows of "
                "the Opus core)")
    m.add("nTierRowsSlice", group(run["n_part_b"]),
          src + " run.n_part_b (part B: the stratified certified benign and "
                "V4 draw)")
    m.add("nTierReproduced", group(rep["reproduced"]),
          src + " reproduction.reproduced (rows re-evaluated under the "
                "accepted Tier-2 configuration that reproduced the accepted "
                "terminal and certified gap)")
    m.add("nTierReproductionChecked", group(rep["n"]),
          src + " reproduction.n (rows checked)")

    for budget, suffix in TIER_BUDGET_TOKEN.items():
        b = ov["budgets"][budget]
        at = " [budget {} s]".format(budget)
        m.add("tierTighter" + suffix, pct(b["tier1_tighter"]),
              src + " overall.budgets." + budget + ".tier1_tighter (rows "
                    "where the solver bound strictly exceeds the analytic "
                    "one)" + at)
        m.add("tierVacuous" + suffix, pct(b["tier1_vacuous"]),
              src + " overall.budgets." + budget + ".tier1_vacuous (rows "
                    "where the solver proved nothing and returned 0.0)" + at)
        m.add("tierProvedOptimal" + suffix, pct(b["tier1_proved_optimal"]),
              src + " overall.budgets." + budget + ".tier1_proved_optimal "
                    "(rows the solver closed inside its budget)" + at)
        m.add("tierMedianDelta" + suffix,
              pct(b["delta_rel_when_tighter"]["median"], 3),
              src + " overall.budgets." + budget +
              ".delta_rel_when_tighter.median (median relative tightness "
              "delta over the rows where Tier 1 is tighter)" + at)
        m.add("tierMaxDelta" + suffix,
              pct(b["delta_rel_when_tighter"]["max"], 3),
              src + " overall.budgets." + budget +
              ".delta_rel_when_tighter.max (largest relative tightness "
              "delta on any row)" + at)
        m.add("tierMedianGapMove" + suffix, num(b["gap_movement"]["median"], 4),
              src + " overall.budgets." + budget + ".gap_movement.median "
                    "(certified gap under Tier 2 minus the gap under the best "
                    "of both bounds)" + at)
        m.add("tierMaxGapMove" + suffix, num(b["gap_movement"]["max"], 4),
              src + " overall.budgets." + budget + ".gap_movement.max "
                    "(largest gap movement on any row)" + at)
        m.add("tierMedianSolve" + suffix, num(b["solve_wall_s"]["median"], 2),
              src + " overall.budgets." + budget + ".solve_wall_s.median "
                    "(Tier 1 solve wall, seconds, 4 solver workers)" + at)
        m.add("tierTwoWall" + suffix, num(b["lb2_wall_ms"]["median"], 2),
              src + " overall.budgets." + budget + ".lb2_wall_ms.median "
                    "(Tier 2 analytic bound wall, milliseconds; the same "
                    "bound is measured once per configuration)" + at)
        m.add("tierRefused" + suffix, pct(b["blocked_under_tier1_only"]),
              src + " overall.budgets." + budget +
              ".blocked_under_tier1_only (share of these already-certified "
              "proposals a Tier-1-only guard would refuse instead)" + at)

    # Derived: how many times the solver bound's wall exceeds the analytic
    # bound's, at each budget's median.  Arithmetic over two sourced cells,
    # rounded to the nearest hundred.
    ratios = {}
    for budget in TIER_BUDGET_TOKEN:
        b = ov["budgets"][budget]
        ratios[budget] = (b["solve_wall_s"]["median"] * 1000.0
                          / b["lb2_wall_ms"]["median"])
    lo_b = min(ratios, key=lambda k: ratios[k])
    hi_b = max(ratios, key=lambda k: ratios[k])
    m.add("tierCostRatioMin", group(round(ratios[lo_b] / 100.0) * 100),
          src + " overall.budgets." + lo_b + ".solve_wall_s.median divided by "
                "overall.budgets." + lo_b + ".lb2_wall_ms.median, to the "
                "nearest hundred (the smaller of the two budgets' ratios)")
    m.add("tierCostRatioMax", group(round(ratios[hi_b] / 100.0) * 100),
          src + " overall.budgets." + hi_b + ".solve_wall_s.median divided by "
                "overall.budgets." + hi_b + ".lb2_wall_ms.median, to the "
                "nearest hundred (the larger of the two budgets' ratios)")

    for key, token in TIER_STRATUM_TOKEN.items():
        for budget, suffix in TIER_BUDGET_TOKEN.items():
            st = slice_["by_stratum"][key]["budgets"][budget]
            at = " [{} / budget {} s]".format(key, budget)
            m.add("tierVacuous" + token + suffix, pct(st["tier1_vacuous"]),
                  src + " by_stratum." + key + ".budgets." + budget +
                  ".tier1_vacuous" + at)
            m.add("tierProvedOptimal" + token + suffix,
                  pct(st["tier1_proved_optimal"]),
                  src + " by_stratum." + key + ".budgets." + budget +
                  ".tier1_proved_optimal" + at)


def build_direct_guard(m: Macros) -> None:
    """DG1: the guard measured on its own, with no proposer in the loop.

    Every other block rate in this file is a joint proposer-and-guard outcome,
    because a model had to emit the illegal operation before the guard could
    refuse it.  DG1 feeds each item's canonical structured proposal straight to
    the guard, so each rate is a property of the guard alone.  The canonical
    field is the one that expresses the item's fault: gold_ops on benign, V3
    and V5, literal_ops on V1 and V2, trap_ops on V4, forbidden_ops on V6
    (analysis/DG1_direct_guard.md, "Which field holds the proposal").
    """
    summary = read_csv("DG1")
    taus = read_csv("DG1_tau")
    fb = read_csv("DG1_fb")
    src = "analysis/DG1_direct_guard_summary.csv"

    def row(cls, config="G_CERT"):
        return one(summary, reading="canonical", config=config,
                   **{"class": cls})

    m.group("DG1: the guard measured directly, with no proposer in the loop",
            "The canonical proposal of every suite item fed straight to the "
            "guard at the frozen tolerance tau = 0.20 "
            "(analysis/DG1_direct_guard_summary.csv). On V1, V2 and V3 these "
            "shares are the ceiling a proposer can reach, because the model is "
            "being asked to produce the faulty proposal; on V4, V5 and V6 they "
            "are conditional on the model making the designed error, which a "
            "competent model does not, so they are not comparable with the "
            "measured block rates of Table 6.")

    v3 = row("V3")
    m.add("dgVThreeCanonicalRefused", group(v3["refused"]),
          src + " refused [canonical / G_CERT / V3]")
    m.add("dgVThreeCanonicalItems", group(v3["items"]),
          src + " items [canonical / G_CERT / V3]")
    m.add("dgVThreeCanonicalShare", pct(v3["refused_share"]),
          src + " refused_share [canonical / G_CERT / V3]")

    ben = row("benign")
    ben_feas = row("benign", "G_FEAS")
    m.add("dgBenignCanonicalBlocks", group(ben["refused"]),
          src + " refused [canonical / G_CERT / benign]")
    m.add("dgBenignCanonicalShare", pct(ben["refused_share"]),
          src + " refused_share [canonical / G_CERT / benign]")
    m.add("dgBenignCanonicalFeasBlocks", group(ben["blocked_feas"]),
          src + " blocked_feas [canonical / G_CERT / benign] (the same 50 "
                "items G_FEAS refuses on its own)")
    m.add("dgBenignCanonicalFeasShare", pct(ben_feas["refused_share"]),
          src + " refused_share [canonical / G_FEAS / benign]")
    m.add("dgBenignCanonicalQualBlocks", group(ben["blocked_qual"]),
          src + " blocked_qual [canonical / G_CERT / benign]")

    for cls in ("V1", "V2", "V4", "V5", "V6"):
        m.add("dg" + CLASS_TOKEN[cls] + "CanonicalShare",
              pct(row(cls)["refused_share"]),
              src + " refused_share [canonical / G_CERT / {}]".format(cls))
    for cls in ("V1", "V5", "V6"):
        m.add("dg" + CLASS_TOKEN[cls] + "CanonicalEmpty",
              group(row(cls)["empty_proposal_items"]),
              src + " empty_proposal_items [canonical / G_CERT / {}]: items "
                    "with no representable canonical proposal".format(cls))

    # The one guard rule that blocks only benign work.  The reversed column is
    # the same two operations supplied in the opposite order, which is a
    # semantics-preserving rewrite of the same proposal.
    freeze = many(fb, subclass="freeze_shift_contradiction")
    passed = [r for r in freeze
              if r["reordered_terminal"] == "applied_with_certificate"]
    m.add("dgFreezeShiftBlocks", group(len(freeze)),
          "analysis/DG1_direct_guard_benign_false_blocks.csv rows with "
          "subclass freeze_shift_contradiction (all blocked_feas on "
          "frozen_order_edit)")
    m.add("dgFreezeShiftReversedPass", group(len(passed)),
          "analysis/DG1_direct_guard_benign_false_blocks.csv rows with "
          "subclass freeze_shift_contradiction whose reordered_terminal is "
          "applied_with_certificate (the same operations in the opposite "
          "order)")

    v3taus = many(taus, **{"class": "V3"})
    tight = min(v3taus, key=lambda r: float(r["tau"]))
    loose = max(v3taus, key=lambda r: float(r["tau"]))
    m.add("dgVThreeCanonicalShareTight", pct(tight["guard_refused_share"]),
          "analysis/DG1_direct_guard_tau.csv guard_refused_share [V3 / tau " +
          tight["tau"] + "], the tightest tolerance on the swept grid")
    m.add("dgVThreeCanonicalShareLoose", pct(loose["guard_refused_share"]),
          "analysis/DG1_direct_guard_tau.csv guard_refused_share [V3 / tau " +
          loose["tau"] + "], the loosest tolerance on the swept grid")
    m.add("dgTauCanonicalTight", "{:.2f}".format(float(tight["tau"])),
          "analysis/DG1_direct_guard_tau.csv tau (minimum of the swept grid)")
    m.add("dgTauCanonicalLoose", "{:.2f}".format(float(loose["tau"])),
          "analysis/DG1_direct_guard_tau.csv tau (maximum of the swept grid)")


def build_falseblock_decomposition(m: Macros) -> None:
    """DG2: what the benign false blocks are made of, and what a solver rescues.

    Proposition 1 makes the certificate stage one-sided, so a loose lower bound
    can only refuse a proposal that deserved acceptance.  DG2 measures how much
    of the measured false-block rate that slack actually explains: it splits the
    benign false blocks by the stage that produced them, then replays every
    quality-stage refusal with the tightest deployable bound (the maximum of the
    analytic Tier-2 bound and a CP-SAT Tier-1 bound) and asks how many the
    tighter bound would have accepted.
    """
    dec = read_csv("DG2")
    summ = read_json("DG2_summary")
    resc = read_csv("DG2_rescue")
    src = "analysis/DG2_falseblock_decomposition.csv"
    jsrc = "analysis/DG2_falseblock_summary.json"

    m.group("DG2: where the benign false blocks come from",
            "Every benign false block of the capability set, split by the stage "
            "that produced it and then by what could have prevented it "
            "(analysis/DG2_falseblock_decomposition.csv). DeepSeek is excluded "
            "by name, because its constrained mode is JSON-object mode and its "
            "false blocks measure the absence of schema enforcement. Only the "
            "quality stage can be caused by slack in the lower bound, so only "
            "that stage is replayed against a tighter bound.")

    pool = one(dec, scope="capability_pooled")
    m.add("dgFalseBlockPooledRows", group(pool["benign_rows"]),
          src + " benign_rows [capability_pooled]: benign twins the capability "
                "set saw, over all repeats")
    m.add("dgFalseBlockPooled", group(pool["false_blocks"]),
          src + " false_blocks [capability_pooled]")
    m.add("dgFalseBlockPooledRate", pct(pool["false_block_rate"]),
          src + " false_block_rate [capability_pooled]")
    for col, label in (("blocked_schema", "StageSchema"),
                       ("blocked_feas", "StageFeas"),
                       ("blocked_qual", "StageQual")):
        m.add("dgFalseBlock" + label, group(pool[col]),
              src + " {} [capability_pooled]".format(col))
    m.add("dgFalseBlockQualShare", pct(pool["qual_share_of_benign_rows"]),
          src + " qual_share_of_benign_rows [capability_pooled]: the "
                "quality stage's own contribution to the false-block rate")

    arms = many(dec, scope="capability")
    pp = {(r["arm"], r["thinking"]): float(r["qual_pp_per_800_twins"])
          for r in arms}
    named = ", ".join("{}/{}".format(a, t) for a, t in sorted(pp))
    m.add("dgFalseBlockQualPpMin", num(min(pp.values()), 2),
          src + " qual_pp_per_800_twins, minimum over the capability rows {" +
          named + "}, in percentage points of the 800 benign twins an arm sees "
          "per repeat")
    m.add("dgFalseBlockQualPpMax", num(max(pp.values()), 2),
          src + " qual_pp_per_800_twins, maximum over the same rows, in "
                "percentage points")

    counts = summ["final"]["counts"]
    total = float(summ["final"]["total"])
    for key, label in (("schema", "Schema"), ("feasibility", "Feas"),
                       ("quality_instance_infeasible_at_tau",
                        "InstanceInfeasible"),
                       ("quality_bound_attributable", "BoundAttributable"),
                       ("quality_proposal_attributable",
                        "ProposalAttributable")):
        if label not in ("Schema", "Feas"):
            m.add("dgFalseBlock" + label, group(counts[key]),
                  jsrc + " final.counts." + key)
        m.add("dgFalseBlock" + label + "Share", pct(counts[key] / total, 2),
              jsrc + " final.counts." + key + " over final.total")

    anchor = summ["anchor"]
    m.add("dgFalseBlockAnchorNoWorse", group(anchor["obj_no_worse_than_anchor"]),
          jsrc + " anchor.obj_no_worse_than_anchor: quality-stage refusals "
                 "whose executed schedule is no worse than the no-AI anchor's")
    m.add("dgFalseBlockAnchorEqual", group(anchor["obj_equals_anchor"]),
          jsrc + " anchor.obj_equals_anchor: quality-stage refusals whose "
                 "executed schedule is the anchor's own schedule")

    m.group("DG2: the Tier-1 rescue replay",
            "Every quality-stage benign false block re-certified with the "
            "maximum of the analytic bound and a CP-SAT bound "
            "(analysis/DG2_tier1_rescue.csv). Deduplication is on the guard's "
            "own input, not on the item, because the certificate is computed "
            "on the adjusted instance and two proposals for one item can carry "
            "different certified gaps. Solver budgets are in seconds and the "
            "tightening ratios are shares.")

    dd = summ["dedup"]
    m.add("dgRescueSolves", group(dd["distinct_input_digest"]),
          jsrc + " dedup.distinct_input_digest: distinct guard inputs behind "
                 "the quality-stage refusals, each solved once")
    m.add("dgRescueRows", group(dd["rows"]),
          jsrc + " dedup.rows: quality-stage refusals the solves cover")
    m.add("dgRescueDistinctItems", group(dd["distinct_instance_item"]),
          jsrc + " dedup.distinct_instance_item: distinct (instance, item) "
                 "pairs, which is NOT a sufficient solve key")

    for budget, suffix in TIER_BUDGET_TOKEN.items():
        at = float(budget)
        rows = [r for r in resc if float(r["budget_s"]) == at]
        if len(rows) != int(dd["distinct_input_digest"]):
            raise LookupError_(
                "DG2 rescue has {} solves at the {} s budget, not {}".format(
                    len(rows), budget, dd["distinct_input_digest"]))
        m.add("dgRescueBudget" + suffix, "{:g}".format(at),
              "analysis/DG2_tier1_rescue.csv budget_s (the {} s solver budget)"
              .format(budget))
        m.add("dgRescueRescued" + suffix,
              group(summ["final"]["rescued_" + budget + "s"]),
              jsrc + " final.rescued_" + budget + "s: refusals the tighter "
                     "bound would have accepted")
        m.add("dgRescueVacuous" + suffix,
              group(sum(1 for r in rows if r["tier1_vacuous"] == "1")),
              "analysis/DG2_tier1_rescue.csv tier1_vacuous = 1 at the " +
              budget + " s budget: solves where CP-SAT proved nothing")
        m.add("dgRescueTighter" + suffix,
              group(sum(1 for r in rows if float(r["delta_rel"]) > 0)),
              "analysis/DG2_tier1_rescue.csv delta_rel > 0 at the " + budget +
              " s budget: solves where the solver bound strictly exceeds the "
              "analytic one")

    hi = max(TIER_BUDGET_TOKEN, key=float)
    hisuf = TIER_BUDGET_TOKEN[hi]
    req = summ["required_tightening_when_not_rescued"][hi]
    for stat in ("min", "median", "max"):
        m.add("dgRescueRequired" + stat.capitalize() + hisuf,
              pct(req[stat], 3),
              jsrc + " required_tightening_when_not_rescued." + hi + "." +
              stat + ": the share by which the best deployable bound would "
              "still have to rise to bring the certified gap down to the "
              "frozen tolerance")
    m.add("dgRescueDeliveredMax" + hisuf,
          pct(summ["achieved_tightening_on_these_rows"][hi]["max"], 3),
          jsrc + " achieved_tightening_on_these_rows." + hi + ".max: the "
                 "largest tightening CP-SAT actually delivers on these rows")
    m.add("dgRescueSliceMax" + hisuf,
          pct(summ["observed_tightening_tier1_slice"][hi]["max"], 3),
          jsrc + " observed_tightening_tier1_slice." + hi + ".max: the largest "
                 "tightening CP-SAT delivers anywhere in the accepted Tier-1 "
                 "slice at the same budget")


def build_prevalence(m: Macros) -> None:
    """DG3: the ladder restated at declared violation prevalences.

    The suite is 60 per cent non-benign by construction, so every published
    ladder mean is an average over a designed mixture.  DG3 holds the
    within-benign and within-violation composition fixed and moves only the
    mixture weight, which makes each mean a two-point convex combination and
    linear in the prevalence p; the crossing prevalence is the closed-form root
    of that line, not a grid search.
    """
    rows = read_csv("DG3")
    src = "analysis/DG3_prevalence.csv"
    low, high = "0.05", "0.15"

    m.group("DG3: the ladder at declared violation prevalences",
            "Where each rung crosses the no-AI anchor when the benign share of "
            "the stream is declared rather than inherited from the suite's own "
            "60 per cent violation mixture (analysis/DG3_prevalence.csv). A "
            "crossing prevalence is the share of violating instructions above "
            "which that rung costs more than dispatching without AI.")

    m.add("dgPrevalenceLow", pct(low),
          src + " p (the low declared prevalence the prose quotes)")
    m.add("dgPrevalenceHigh", pct(high),
          src + " p (the high declared prevalence the prose quotes)")

    orc = many(rows, rung="ORACLE")
    crossings = {r["crossing_p"] for r in orc}
    if len(crossings) != 1:
        raise LookupError_(
            "DG3 gives {} crossing prevalences for ORACLE".format(
                len(crossings)))
    m.add("dgOracleCrossingP", pct(crossings.pop(), 2),
          src + " crossing_p [ORACLE]: the violation prevalence at which the "
                "perfect translator's mean weighted tardiness crosses the "
                "no-AI anchor")
    for p, label in ((low, "AtFive"), (high, "AtFifteen")):
        m.add("dgOracleVsRule" + label,
              bh(one(rows, rung="ORACLE", p=p)["delta_vs_rule_bh"], 2,
                 signed=True),
              src + " delta_vs_rule_bh [ORACLE / p = {}]".format(p))
    m.add("dgOracleGuardedVsRuleAtFive",
          bh(one(rows, rung="ORACLE+G_CERT", p=low)["delta_vs_rule_bh"], 2,
             signed=True),
          src + " delta_vs_rule_bh [ORACLE+G_CERT / p = {}]".format(low))

    # The flagship's three rungs.  Constrained mode only: the free-mode rows
    # are dominated by the vendor refusal wall and are a different measurement.
    for rung, label in (("UNGUARDED", "Unguarded"), ("G_FEAS", "Feas"),
                        ("G_CERT", "Cert")):
        sub = many(rows, rung=rung, arm="opus", thinking="default",
                   mode="M_constrained")
        vals = {r["crossing_p"] for r in sub}
        if len(vals) != 1 or not vals:
            raise LookupError_(
                "DG3 gives {} crossing prevalences for opus/{}".format(
                    len(vals), rung))
        m.add("dg" + label + "CrossingPOpus", pct(vals.pop(), 2),
              src + " crossing_p [{} / opus / default / M_constrained]"
              .format(rung))
    m.add("dgCertVsRuleAtFiveOpus",
          bh(one(rows, rung="G_CERT", arm="opus", thinking="default",
                 mode="M_constrained", p=low)["delta_vs_rule_bh"], 2,
             signed=True),
          src + " delta_vs_rule_bh [G_CERT / opus / default / M_constrained / "
                "p = {}]".format(low))


def build_tau_rule(m: Macros) -> None:
    """DG4: a declared cost rule for the tolerance.

    C(tau; lambda) is the mean excess weighted tardiness reaching the executed
    schedule plus lambda times the referral rate, both per instruction, so
    lambda is the price of one referral in weighted business hours of
    supervisor attention.  The selection is in-sample: the referral rate and
    the excess are computed on the rows the paper reports performance on.
    """
    rows = read_csv("DG4")
    src = "analysis/DG4_tau_cost_rule.csv"
    sel = [r for r in rows if r["block"] == "selection"
           and r["in_capability_set"] == "yes" and r["mode"] == "M_constrained"]
    env = [r for r in rows if r["block"] == "envelope"
           and r["in_capability_set"] == "yes" and r["mode"] == "M_constrained"]
    configs = sorted({(r["arm"], r["thinking"]) for r in sel})

    m.group("DG4: what a declared cost rule selects for the tolerance",
            "The rule prices a referral at lambda weighted business hours of "
            "supervisor attention and minimises expected excess tardiness plus "
            "expected referral cost (analysis/DG4_tau_cost_rule.csv). It is a "
            "check that the printed operating point is defensible on the "
            "measured data, and it is in-sample: no held-out split was "
            "pre-registered.")

    flag = [r for r in sel if r["arm"] == "opus" and r["thinking"] == "default"]
    picks = {r["tau_star_grid"] for r in flag}
    if len(picks) != 1:
        raise LookupError_(
            "the cost rule selects {} different tolerances on the flagship "
            "across the lambda grid; Section 6 was written for one".format(
                len(picks)))
    selected = picks.pop()
    m.add("dgTauRuleSelected", "{:.2f}".format(float(selected)),
          src + " tau_star_grid [opus / default / M_constrained], the same "
                "value at every lambda on the grid (asserted here)")
    m.add("dgTauRuleConfigsTotal", str(len(configs)),
          src + " selection rows: capability-set arm configurations in "
                "constrained mode")

    with_paper = [c for c in configs
                  if any(r["tau_paper_fb5pct"] for r in sel
                         if (r["arm"], r["thinking"]) == c)]
    agree = [c for c in with_paper
             if any(r["agrees_with_paper"] == "yes" for r in sel
                    if (r["arm"], r["thinking"]) == c)]
    named = ", ".join("{}/{}".format(a, t) for a, t in agree)
    m.add("dgTauRuleArmsAgree", str(len(agree)),
          src + " agrees_with_paper = yes on at least one lambda, over the "
                "capability-set configurations that print a 5 per cent budget "
                "operating point (" + named + ")")
    m.add("dgTauRuleArmsTotal", str(len(with_paper)),
          src + " selection rows with a non-empty tau_paper_fb5pct: "
                "capability-set configurations that reach the 5 per cent "
                "budget and therefore print an operating point")

    # The lambda window on which every agreeing configuration selects the
    # tolerance its 5 per cent budget already produces: the intersection of
    # their envelope intervals, solved exactly rather than sampled.
    los, his = [], []
    for cfg in agree:
        paper_tau = [r["tau_paper_fb5pct"] for r in sel
                     if (r["arm"], r["thinking"]) == cfg][0]
        hit = [r for r in env if (r["arm"], r["thinking"]) == cfg
               and float(r["tau_star_grid"]) == float(paper_tau)]
        if len(hit) != 1:
            raise LookupError_(
                "DG4 envelope has {} intervals for {} at tau {}".format(
                    len(hit), cfg, paper_tau))
        los.append(float(hit[0]["lambda_lo_bh"]))
        his.append(float(hit[0]["lambda_hi_bh"]))
    m.add("dgTauRuleLambdaMin", num(max(los), 2),
          src + " lambda_lo_bh, largest over the {} agreeing configurations "
                "({}): the lower end of the lambda window on which all of them "
                "select the printed operating point".format(len(agree), named))
    m.add("dgTauRuleLambdaMax", num(min(his), 2),
          src + " lambda_hi_bh, smallest over the {} agreeing configurations "
                "({}): the upper end of that window".format(len(agree), named))

    flag_env = [r for r in env if r["arm"] == "opus"
                and r["thinking"] == "default"
                and float(r["tau_star_grid"]) == float(selected)]
    if len(flag_env) != 1:
        raise LookupError_("DG4 envelope has {} intervals for the flagship at "
                           "tau {}".format(len(flag_env), selected))
    m.add("dgTauRuleFlagshipLambdaMin", num(flag_env[0]["lambda_lo_bh"], 2),
          src + " lambda_lo_bh [opus / default / M_constrained / tau* " +
          selected + "]: the flagship's own stability window, lower end")
    m.add("dgTauRuleFlagshipLambdaMax", num(flag_env[0]["lambda_hi_bh"], 2),
          src + " lambda_hi_bh [opus / default / M_constrained / tau* " +
          selected + "]: the flagship's own stability window, upper end")

    frozen = one(rows, block="rationalise", arm="opus", thinking="default",
                 mode="M_constrained", target="frozen_evaluation_tau")
    m.add("dgTauRuleFrozenRegretOpus", num(frozen["min_regret_over_lambda_grid_bh"], 3),
          src + " min_regret_over_lambda_grid_bh [opus / default / "
                "M_constrained / frozen_evaluation_tau]: what the frozen "
                "evaluation tolerance costs against the rule's own choice, "
                "weighted business hours per instruction")


def build_e1_intervals(m: Macros) -> None:
    """DG5: cluster-bootstrap intervals on the E1 headline rates.

    Clusters are scheduling instances, drawn with replacement; each drawn
    cluster contributes all of its rows and the statistic is the resampled
    numerator over the resampled denominator.  The design effect is the squared
    ratio of the clustered and naive interval widths, so it is how many times
    more independent rows a binomial interval would have pretended to have.
    """
    rows = [r for r in read_csv("DG5") if r["cluster_level"] == "instance"]
    conc = read_csv("DG5_conc")
    src = "analysis/DG5_e1_intervals.csv"

    m.group("DG5: intervals on the E1 rates, clustered by instance",
            "Percentile intervals from a nonparametric cluster bootstrap over "
            "the 60 frozen instances, pooled over repeats in constrained mode "
            "(analysis/DG5_e1_intervals.csv). These are uncertainty over "
            "instances drawn from the same generator, not over models, prompts "
            "or tolerances, and sixty clusters is a small bootstrap, so the "
            "percentile interval is if anything optimistic. Bodies carry no "
            "per-cent sign: the prose writes an interval as one range with a "
            "single sign at the end.")

    def endpoints(metric, name, comment, **where):
        r = one(rows, metric=metric, **where)
        m.add(name + "CiLo", r["ci_lo_pct"],
              "{} ci_lo_pct [{} / {}], in per cent without the sign"
              .format(src, metric, comment))
        m.add(name + "CiHi", r["ci_hi_pct"],
              "{} ci_hi_pct [{} / {}], in per cent without the sign"
              .format(src, metric, comment))
        return r

    fb_opus = endpoints("benign_false_block_gcert", "dgFalseBlockOpus",
                        "opus / default / instance-clustered",
                        arm="opus", thinking="default")
    sep_opus = endpoints("v3_separation", "dgVThreeSepOpus",
                         "opus / default / instance-clustered",
                         arm="opus", thinking="default")

    # The two endpoints of the published false-block range.  The range_role
    # column marks them in the artifact, so the macro cannot drift from the
    # range \eOneFalseBlockMin and \eOneFalseBlockMax print.
    for role, label in (("min", "Min"), ("max", "Max")):
        r = one(rows, metric="benign_false_block_gcert", range_role=role)
        m.add("dgFalseBlock" + label + "ArmCiLo", r["ci_lo_pct"],
              "{} ci_lo_pct [benign_false_block_gcert / range_role {} / {} / "
              "{}], in per cent without the sign".format(
                  src, role, r["arm"], r["thinking"]))
        m.add("dgFalseBlock" + label + "ArmCiHi", r["ci_hi_pct"],
              "{} ci_hi_pct [benign_false_block_gcert / range_role {} / {} / "
              "{}], in per cent without the sign".format(
                  src, role, r["arm"], r["thinking"]))

    cap = [r for r in rows if r["metric"] == "benign_false_block_gcert"
           and r["capability_set"] == "1"]
    worst = max(cap, key=lambda r: float(r["deff_width"]))
    m.add("dgFalseBlockDesignEffectMax", num(worst["deff_width"], 2),
          src + " deff_width, maximum over the eight capability-set rows of "
                "benign_false_block_gcert (attained by {} / {})".format(
                    worst["arm"], worst["thinking"]))
    # The design effect is a variance ratio, so the reader who wants to know
    # how much wider the interval got needs its square root.  It is derived
    # here rather than read, because deff_width is defined in the artifact's
    # own header as (cluster width / Wilson width) squared.
    m.add("dgFalseBlockWidthFactorMax",
          num(float(worst["deff_width"]) ** 0.5, 1),
          src + " deff_width [{} / {}], square-rooted: the design effect is "
                "defined in that file's header as the squared ratio of the "
                "clustered and Wilson interval widths, so its root is the "
                "width ratio itself".format(worst["arm"], worst["thinking"]))
    m.add("dgFalseBlockClusters", group(fb_opus["n_clusters"]),
          src + " n_clusters [benign_false_block_gcert / opus / default]: "
                "instances the benign rows are drawn from")
    m.add("dgVThreeSepClusters", group(sep_opus["n_clusters"]),
          src + " n_clusters [v3_separation / opus / default]: instances the "
                "V3 rows are drawn from")
    m.add("dgBootReplicates", group(fb_opus["B"]),
          src + " B: bootstrap replicates behind every interval in this group")

    c = one(conc, arm="opus", thinking="default", config="G_CERT")
    csrc = "analysis/DG5_falseblock_concentration.csv"
    m.add("dgFalseBlockInstancesHitOpus",
          group(c["instances_with_any_false_block"]),
          csrc + " instances_with_any_false_block [opus / default / G_CERT]")
    m.add("dgFalseBlockInstancesTotal", group(c["instances_total"]),
          csrc + " instances_total [opus / default / G_CERT]")
    m.add("dgFalseBlockTopTwoShareOpus", pct_of(c["top2_share_pct"]),
          csrc + " top2_share_pct [opus / default / G_CERT]: share of the "
                 "flagship's false blocks landing on its two worst instances")
    m.add("dgFalseBlockTopFamilyShareOpus",
          pct_of(c["top_subclass_share_pct"]),
          csrc + " top_subclass_share_pct [opus / default / G_CERT]: share "
                 "landing on the single template family " + c["top_subclass"])


def build_e3_intervals(m: Macros) -> None:
    """DG6: intervals, equivalence tests and design power on the agent layer.

    Equivalence is not the absence of a significant difference: a cell counts
    as equivalent only when the 90 per cent bootstrap, Newcombe and cluster
    intervals all lie inside the declared margin.  The power block says what
    the design could have detected at all, which is what separates "equivalent
    within the margin" from "inconclusive".
    """
    rows = read_csv("DG6")
    note = re.sub(r"\s+", " ", read_text("DG6_note"))
    src = "analysis/DG6_e3_intervals.csv"
    nsrc = "analysis/DG6_e3_intervals.md"
    loose = [r for r in rows if r["budget_level"] == "loose"]
    binary = [r for r in loose
              if r["outcome"] in ("false_block", "catch", "passthrough")]
    qual = [r for r in loose if r["outcome"] == "quality_mean_bh"]

    m.group("DG6: how large a difference the agent-layer comparison could see",
            "SINGLE+G against MULTI-G on the same items at the loose budget "
            "(analysis/DG6_e3_intervals.csv). Margins are declared as a "
            "fraction of an effect this study already measured on the same "
            "items: the effect of adding the guard at a fixed architecture. "
            "Margins in percentage points and detectable risk differences "
            "carry no per-cent sign, and business hours are unitless, as "
            "everywhere else in this file. "
            "Intervals, equivalence verdicts and design power for the "
            "agent-layer comparison, from the regenerated guard-v0.2 "
            "artifact. The pass-through outcome applies the V4/V6 content "
            "rule (code/scripts/passthrough_rule.py); false block and catch "
            "are dispositions and are unchanged.")

    def margin(pattern, what):
        hit = re.search(pattern, note)
        if hit is None:
            raise LookupError_(
                "DG6_e3_intervals.md no longer states the {} margin".format(
                    what))
        return hit

    binprim = margin(r"\*\*Binary outcomes: ([\d.]+) pp primary", "primary "
                     "binary").group(1)
    binside = margin(r"\*\*([\d.]+) pp and ([\d.]+) pp\*\* are reported beside",
                     "secondary binary")
    qualprim = margin(r"\*\*End-task quality: ([\d.]+) bh primary\*\*",
                      "primary quality").group(1)
    qualside = margin(r"([\d.]+) bh and ([\d.]+) bh are reported beside",
                      "secondary quality")
    # Cross-check the note against the table, which carries the primary margin
    # of every cell as a column.
    for cells, declared, what in ((binary, binprim, "binary"),
                                  (qual, qualprim, "quality")):
        got = {float(r["margin_primary"]) for r in cells}
        if got != {float(declared)}:
            raise LookupError_(
                "the {} margin the note declares ({}) is not the "
                "margin_primary the table carries ({})".format(
                    what, declared, sorted(got)))

    m.add("dgEThreeQualMarginPrimary", num(qualprim, 0),
          nsrc + " 'End-task quality: primary' margin, weighted business "
                 "hours; equals margin_primary on the quality rows of " + src)
    m.add("dgEThreeQualMarginTight", num(qualside.group(1), 0),
          nsrc + " the tighter of the two secondary quality margins reported "
                 "beside the primary one, weighted business hours")
    m.add("dgEThreeBinaryMarginPrimary", num(binprim, 1),
          nsrc + " 'Binary outcomes: primary' margin, percentage points; "
                 "equals margin_primary on the binary rows of " + src)
    m.add("dgEThreeBinaryMarginWide", num(binside.group(2), 1),
          nsrc + " the looser of the two secondary binary margins reported "
                 "beside the primary one, percentage points")

    equiv = "equivalence established"
    qual_ok = [r for r in qual if r["verdict_margin_low"] == equiv]
    m.add("dgEThreeQualEquivArms", str(len(qual_ok)),
          src + " verdict_margin_low = '" + equiv + "' over the loose-budget "
                "quality_mean_bh rows: arms whose end-task quality is "
                "equivalent within the tighter quality margin")
    m.add("dgEThreeArmsTotal", str(len(qual)),
          src + " loose-budget quality_mean_bh rows (one per arm)")

    m.add("dgEThreeBinaryEquivPrimary",
          str(sum(1 for r in binary if r["verdict_margin_mid"] == equiv)),
          src + " verdict_margin_mid = '" + equiv + "' over the loose-budget "
                "binary cells (the primary margin)")
    m.add("dgEThreeBinaryEquivWide",
          str(sum(1 for r in binary if r["verdict_margin_high"] == equiv)),
          src + " verdict_margin_high = '" + equiv + "' over the loose-budget "
                "binary cells (the widest reported margin)")
    m.add("dgEThreeBinaryCells", str(len(binary)),
          src + " loose-budget rows on the three binary outcomes "
                "(false_block, catch, passthrough): 6 arms x 3 outcomes")

    # The other two verdicts at the primary binary margin.  A cell that is not
    # equivalent is either indeterminate (the data cannot separate equivalence
    # from a real difference) or refuted (a difference larger than the margin
    # is affirmed), and those are different claims, so the paper reports the
    # full tally rather than only the equivalent count.
    m.add("dgEThreeBinaryIndetPrimary",
          str(sum(1 for r in binary
                  if r["verdict_margin_mid"] == "indeterminate")),
          src + " verdict_margin_mid = 'indeterminate' over the loose-budget "
                "binary cells (the primary margin)")
    m.add("dgEThreeBinaryRefutedPrimary",
          str(sum(1 for r in binary
                  if r["verdict_margin_mid"] not in
                  (equiv, "indeterminate"))),
          src + " verdict_margin_mid outside {'" + equiv + "', "
                "'indeterminate'} over the loose-budget binary cells: cells "
                "where a difference wider than the primary margin is affirmed")

    # The interval level the Verdict column is judged at.  The manuscript
    # prints 95 per cent intervals elsewhere, so the level behind the verdicts
    # has to be stated where they are reported.
    level = re.search(r"a cell counts as equivalent only if the (\d+)% "
                      r"bootstrap interval", note)
    if level is None:
        raise LookupError_(
            "DG6_e3_intervals.md no longer states the interval level the "
            "verdict rule uses")
    for suffix in ("bootstrap", "Newcombe", "cluster-bootstrap"):
        if "{}% {} interval".format(level.group(1), suffix) not in note:
            raise LookupError_(
                "the DG6 verdict rule no longer names a {}% {} interval"
                .format(level.group(1), suffix))
    if not {r["boot_ci90_lo"] for r in binary}:
        raise LookupError_("DG6 carries no 90 per cent bootstrap endpoints")
    m.add("dgEThreeVerdictLevel", level.group(1),
          nsrc + " verdict rule: the interval level, in per cent, at which "
                 "the bootstrap, Newcombe and cluster-bootstrap intervals "
                 "must all lie inside the margin for a cell to count as "
                 "equivalent (the boot_ci90_*, newcombe_ci90_* and "
                 "cluster_ci90_* columns of " + src + ")")

    pairs = {r["n_units"] for r in binary}
    if len(pairs) != 1:
        raise LookupError_("DG6 binary cells carry {} different pair counts"
                           .format(len(pairs)))
    m.add("dgEThreeMatchedPairs", group(pairs.pop()),
          src + " n_units on the binary cells: matched pairs per cell, the 96 "
                "labelled violations or their 96 matched benign twins")
    m.add("dgEThreeMinDiscordant",
          group(binary[0]["min_onedir_discordant_for_sig_holm96realised"]),
          src + " min_onedir_discordant_for_sig_holm96realised: pairs that "
                "must be discordant, all in one direction, before the exact "
                "McNemar test can reach significance under the correction the "
                "manuscript reports")
    m.add("dgEThreeMinDiscordantUncorrected",
          group(binary[0]["min_onedir_discordant_for_sig_alpha05"]),
          src + " min_onedir_discordant_for_sig_alpha05: the same count with "
                "no correction at all")
    m.add("dgEThreeDetectableRd",
          num(binary[0]["mdes80_holm96realised_bestcase"], 1),
          src + " mdes80_holm96realised_bestcase: smallest risk difference "
                "reaching 80 per cent power under the reported correction, in "
                "percentage points, with every discordant pair in one "
                "direction (a floor, not an estimate)")
    m.add("dgEThreeDetectableRdUncorrected",
          num(binary[0]["mdes80_alpha05_bestcase"], 1),
          src + " mdes80_alpha05_bestcase: the same quantity with no "
                "correction, in percentage points")

    cells = [r for r in loose
             if r["outcome"] in ("false_block", "catch", "passthrough",
                                 "quality_mean_bh")]
    m.add("dgEThreeLooseCells", str(len(cells)),
          src + " loose-budget rows on the three binary outcomes and the mean "
                "quality outcome: 6 arms x 4 outcomes")
    m.add("dgEThreeCellsCouldDetect",
          str(sum(1 for r in cells
                  if r["sig_attainable_holm96realised"] == "True")),
          src + " sig_attainable_holm96realised = True over those cells: "
                "cells whose observed discordance was large enough for a "
                "corrected significant result at any true effect size")
    m.add("dgEThreeCellsCouldDetectUncorrected",
          str(sum(1 for r in cells if r["sig_attainable_alpha05"] == "True")),
          src + " sig_attainable_alpha05 = True over those cells")

    m.add("dgEThreeMaxRdLoose",
          num(max(abs(float(r["estimate"])) for r in binary), 1),
          src + " estimate, largest absolute paired risk difference over the "
                "loose-budget binary cells, in percentage points")
    m.add("dgEThreeWidestBoundLoose",
          num(max(max(abs(float(r["boot_ci95_lo"])), abs(float(r["boot_ci95_hi"])))
                  for r in binary), 1),
          src + " boot_ci95_lo and boot_ci95_hi, largest absolute 95 per cent "
                "bootstrap endpoint over the loose-budget binary cells, in "
                "percentage points: the largest difference the design still "
                "admits")


def build_passthrough(m: Macros) -> None:
    """DG7: violation pass-through, decomposed.

    The published rate counts a violation-labelled item whose terminal is an
    applied state, so it answers "did the pipeline act on an item that carried
    a defect" and not "did the defect reach the schedule".  Two cuts separate
    the readings: the catchable denominator keeps only the items some stage can
    test, and the non-empty reading requires the applied operation list to hold
    at least one operation.

    Every rate here is the ``*_strict`` column, which applies the V4/V6
    content rule of ``code/scripts/passthrough_rule.py``: an applied V4 or V6
    row counts unless the applied operations are exactly the item's ground
    truth.  On V4 that removes the rows where the pipeline produced the correct
    translation of a mistranslated instruction, and on V6 the carrier items
    where it executed the legitimate work order; no other class moves.
    """
    rows = read_csv("DG7")
    dec = read_csv("DG7_class")
    src = "analysis/DG7_passthrough.csv"
    dsrc = "analysis/DG7_passthrough_decomp.csv"
    # The V4 class does not split into halves: 55 of its 220 items are
    # quality-visible and 165 are not, a quarter and three quarters.  The two
    # denominators below are checked against this split by the next auditor,
    # so the counts are formatted in rather than described.
    v4_visible, v4_neutral = v4_split()
    by_class = read_json("suite_manifest")["counts"]["by_class"]
    orc_row = one(read_csv("DG7"), system="ORACLE")
    expect_catchable = (int(by_class["V1"]) + int(by_class["V2"])
                        + int(by_class["V3"]) + v4_visible)
    expect_outside = int(by_class["V5"]) + int(by_class["V6"]) + v4_neutral
    if (int(orc_row["catchable_n"]) != expect_catchable
            or int(orc_row["outside_n"]) != expect_outside):
        raise LookupError_(
            "DG7 denominators {}/{} do not match the class counts and the V4 "
            "split ({}/{})".format(orc_row["catchable_n"],
                                   orc_row["outside_n"],
                                   expect_catchable, expect_outside))

    m.group("DG7: violation pass-through, decomposed",
            "The same violation set read three ways "
            "(analysis/DG7_passthrough.csv). 'Catchable' restricts the "
            "denominator to the items some guard stage can test: V1, V2, V3 "
            "and the {} quality-visible V4 items. 'Non-empty' keeps the full "
            "denominator and requires the applied proposal to contain at least "
            "one operation, so a proposer that declined to act is not counted "
            "as having acted on a violation. Every rate is the content-ruled "
            "column: {} (code/scripts/passthrough_rule.py), so a correct "
            "translation of a mistranslated instruction and an executed "
            "carrier order no longer count as pass-through."
            .format(v4_visible, STRICT_RULE))

    orc = one(rows, system="ORACLE")
    orcg = one(rows, system="ORACLE+G_CERT")
    opus = one(rows, system="opus / G_CERT", mode="M_constrained",
               thinking="default")
    opus_ung = one(rows, system="opus / UNGUARDED", mode="M_constrained",
                   thinking="default")
    opus_feas = one(rows, system="opus / G_FEAS", mode="M_constrained",
                    thinking="default")

    m.add("dgPassCatchableDenom", group(orc["catchable_n"]),
          dsrc + " and " + src + " catchable_n [ORACLE, one repeat]: V1, V2, "
                 "V3 and the {} quality-visible V4 items".format(v4_visible))
    m.add("dgPassOutsideDenom", group(orc["outside_n"]),
          src + " outside_n [ORACLE, one repeat]: V5, V6 and the {} "
                "quality-neutral V4 items, which no stage tests".format(
                    v4_neutral))

    m.add("dgPassCatchableOpus", pct(opus["pass_through_catchable_strict"]),
          src + " pass_through_catchable_strict [opus / G_CERT / "
                "M_constrained / default]: " + STRICT_RULE)
    m.add("dgPassNonEmptyOpus", pct(opus["pass_through_nonempty_strict"]),
          src + " pass_through_nonempty_strict [opus / G_CERT / M_constrained "
                "/ default]: " + STRICT_RULE)
    m.add("dgPassNonEmptyUnguardedOpus",
          pct(opus_ung["pass_through_nonempty_strict"]),
          src + " pass_through_nonempty_strict [opus / UNGUARDED / "
                "M_constrained / default]: " + STRICT_RULE)
    m.add("dgPassNonEmptyFeasOpus",
          pct(opus_feas["pass_through_nonempty_strict"]),
          src + " pass_through_nonempty_strict [opus / G_FEAS / M_constrained "
                "/ default]: " + STRICT_RULE)
    m.add("dgPassCatchableNonEmptyOpus",
          pct(opus["pass_through_catchable_nonempty_strict"]),
          src + " pass_through_catchable_nonempty_strict [opus / G_CERT / "
                "M_constrained / default]: " + STRICT_RULE)
    m.add("dgPassOutsideOpus", pct(opus["pass_through_outside_strict"]),
          src + " pass_through_outside_strict [opus / G_CERT / M_constrained "
                "/ default]: " + STRICT_RULE)
    m.add("dgPassOutsideNonEmptyOpus",
          pct(opus["pass_through_outside_nonempty_strict"]),
          src + " pass_through_outside_nonempty_strict [opus / G_CERT / "
                "M_constrained / default]: " + STRICT_RULE)

    for arm, think, tok in (("qwen3-14b", "-", "QwenFourteenB"),
                            ("sonnet", "disabled", "Sonnet")):
        r = one(rows, system=arm + " / G_CERT", mode="M_constrained",
                thinking=think)
        m.add("dgPassCatchable" + tok, pct(r["pass_through_catchable_strict"]),
              src + " pass_through_catchable_strict [{} / G_CERT / "
                    "M_constrained / {}]: {}".format(arm, think, STRICT_RULE))

    m.add("dgOraclePassCatchable", pct(orc["pass_through_catchable_strict"]),
          src + " pass_through_catchable_strict [ORACLE]: " + STRICT_RULE)
    m.add("dgOracleGuardedPassCatchable",
          pct(orcg["pass_through_catchable_strict"]),
          src + " pass_through_catchable_strict [ORACLE+G_CERT]: "
          + STRICT_RULE)

    m.add("dgVFiveNonEmptyOpus", pct(opus["v5_pass_through_nonempty"]),
          src + " v5_pass_through_nonempty [opus / G_CERT / M_constrained / "
                "default]: ambiguity items applied with at least one "
                "operation. V5 carries no ground truth to match, so the "
                "content rule leaves this reading unchanged")
    m.add("dgVSixNonEmptyOpus", pct(opus["v6_pass_through_nonempty_strict"]),
          src + " v6_pass_through_nonempty_strict [opus / G_CERT / "
                "M_constrained / default]: injection items applied with at "
                "least one operation that is not the item's ground truth, "
                "the legitimate carrier order")

    for cls in ("V1", "V2", "V3", "V4", "V5", "V6"):
        r = one(dec, **{"class": cls})
        tok = CLASS_TOKEN[cls]
        m.add("dgPassOracle" + tok, pct(r["oracle_pass_through_strict"]),
              dsrc + " oracle_pass_through_strict [{}]: {}".format(
                  cls, STRICT_RULE))
        m.add("dgPassOracleGuarded" + tok,
              pct(r["oracle_guarded_pass_through_strict"]),
              dsrc + " oracle_guarded_pass_through_strict [{}]: {}".format(
                  cls, STRICT_RULE))
        m.add("dgPassFlagship" + tok, pct(r["flagship_pass_through_strict"]),
              dsrc + " flagship_pass_through_strict [{}]: opus / default "
                     "under the full guard; {}".format(cls, STRICT_RULE))
        m.add("dgPassFlagshipNonEmpty" + tok,
              pct(r["flagship_pass_through_nonempty_strict"]),
              dsrc + " flagship_pass_through_nonempty_strict [{}]: {}".format(
                  cls, STRICT_RULE))
        # Unsigned, two decimals: the manuscript's table template writes the
        # sign of a positive contribution itself, so this body must not carry
        # one, and a negative body carries its own minus.
        m.add("dgPassContrib" + tok, num(r["contribution_pp_strict"], 2),
              dsrc + " contribution_pp_strict [{}]: that class's share of the "
                     "1,200 violations times its flagship-minus-ORACLE rate "
                     "difference, in percentage points, printed unsigned so a "
                     "positive value takes its sign from the table template "
                     "and a negative one carries its own; {}".format(
                         cls, STRICT_RULE))

    net = sum(float(r["contribution_pp_strict"]) for r in dec)
    m.add("dgPassGapFlagshipMinusOracle", num(net, 2),
          dsrc + " contribution_pp_strict summed over the six classes: the "
                 "flagship's pass-through minus ORACLE's, in percentage "
                 "points; " + STRICT_RULE)
    v56 = sum(float(one(dec, **{"class": c})["contribution_pp_strict"])
              for c in ("V5", "V6"))
    m.add("dgPassContribVFiveVSix", num(v56, 2),
          dsrc + " contribution_pp_strict for V5 plus V6, in percentage "
                 "points: the ambiguity and injection classes' share of that "
                 "gap; " + STRICT_RULE)


def build_dg8(m: Macros) -> None:
    """DG8: the gap floor, the per-item gap agreement, the refusal wall.

    Three post-processing passes over logs already on disk.  Nothing here calls
    a model or a solver.
    """
    floor = read_csv("DG8_floor")
    gap = read_csv_first_block("DG8_gap")
    ref = read_csv("DG8_refusals")

    m.group("DG8: the gap floor",
            "Equation 2 divides by max(LB, ell) with ell one weighted business "
            "hour, so the floor binds whenever the analytic lower bound is "
            "zero (analysis/DG8_floor.csv). Reported scope: constrained mode, "
            "all ten arm configurations, which is the scope every certificate "
            "statistic in the manuscript uses.")
    fsrc = "analysis/DG8_floor.csv"
    scope = one(floor, section="scope", key="constrained_all_arms_noinfra")
    m.add("dgFloorBindShare", pct(scope["share"]),
          fsrc + " share [scope / constrained_all_arms_noinfra]")
    m.add("dgFloorBindCerts", group(scope["binding"]),
          fsrc + " binding [scope / constrained_all_arms_noinfra]")
    m.add("dgFloorCertsTotal", group(scope["n"]),
          fsrc + " n [scope / constrained_all_arms_noinfra]")

    strata = many(floor, section="stratum")
    reported = [r for r in strata
                if r["key"].startswith("constrained_all_arms_noinfra |")]
    worst = max(reported, key=lambda r: float(r["share"]))
    zero = [r for r in reported if float(r["binding"]) == 0]
    m.add("dgFloorBindStratumShare", pct(worst["share"]),
          fsrc + " share [stratum / " + worst["key"] + "]: the one stratum "
                 "that carries every floor-binding certificate; the other " +
          str(len(zero)) + " strata carry none")

    lb = re.search(r"min positive LB ([\d.]+) bh", scope["note"])
    if lb is None:
        raise LookupError_(
            "DG8_floor.csv no longer records the minimum positive lower bound")
    m.add("dgFloorMinPositiveLb", num(lb.group(1), 1),
          fsrc + " note [scope / constrained_all_arms_noinfra] 'min positive "
                 "LB': the smallest lower bound that is not zero, weighted "
                 "business hours")
    m.add("dgFloorObjZeroCerts",
          group(one(floor, section="binding_composition",
                    key="obj_eq_zero")["binding"]),
          fsrc + " binding [binding_composition / obj_eq_zero]: binding "
                 "certificates whose objective is also zero, so their gap is "
                 "zero at every ell")
    m.add("dgFloorObjPositiveCerts",
          group(one(floor, section="binding_composition",
                    key="obj_gt_zero")["binding"]),
          fsrc + " binding [binding_composition / obj_gt_zero]")

    m.add("dgFloorFirstFlipEll",
          num(one(floor, section="critical_ell",
                  key="tau_0.20_reported_scope")["binding"], 2),
          fsrc + " binding [critical_ell / tau_0.20_reported_scope]: the "
                 "smallest ell at which any accept-or-block decision changes "
                 "at the frozen tolerance")
    m.add("dgFloorTableInvariantEll",
          num(one(floor, section="critical_ell",
                  key="published_table8_cells")["binding"], 2),
          fsrc + " binding [critical_ell / published_table8_cells]: the "
                 "smallest ell that moves any printed tolerance-sweep cell, so "
                 "the printed table is identical below it")
    m.add("dgFloorSweepInvariantEll",
          num(one(floor, section="critical_ell",
                  key="tau_grid_reported_scope")["binding"], 2),
          fsrc + " binding [critical_ell / tau_grid_reported_scope]: the "
                 "smallest ell that moves any decision anywhere on the swept "
                 "tolerance grid, which is tighter than the printed table's "
                 "invariance")

    m.group("DG8: the flagship's certified gaps against the ground truth",
            "The ORACLE rung and each arm run on the same items, so the two "
            "certified-gap distributions can be joined item by item rather "
            "than compared through two order statistics "
            "(analysis/DG8_gap_agreement.csv). Constrained mode, class V3, one "
            "row per logged certificate.")
    gsrc = "analysis/DG8_gap_agreement.csv"
    gopus = one(gap, arm="opus", thinking="default")
    m.add("dgGapIdenticalOpus", group(gopus["identical"]),
          gsrc + " identical [opus / default]: certificates whose certified "
                 "gap is the same number as the ground-truth translation's on "
                 "the same item")
    m.add("dgGapCertsOpus", group(gopus["certificates"]),
          gsrc + " certificates [opus / default]")
    m.add("dgGapIdenticalShareOpus", pct(gopus["share_identical"]),
          gsrc + " share_identical [opus / default]")
    m.add("dgGapDifferingOpus", group(gopus["differing"]),
          gsrc + " differing [opus / default]; all of them are lower for the "
                 "flagship (arm_gap_lower equals differing on this row)")
    cap = [r for r in gap if r["in_capability_set"] == "yes"]
    lo = min(cap, key=lambda r: float(r["share_identical"]))
    hi = max(cap, key=lambda r: float(r["share_identical"]))
    members = ", ".join("{}/{}".format(r["arm"], r["thinking"]) for r in cap)
    m.add("dgGapIdenticalShareMin", pct(lo["share_identical"]),
          gsrc + " share_identical, minimum over the capability set {" +
          members + "}")
    m.add("dgGapIdenticalShareMax", pct(hi["share_identical"]),
          gsrc + " share_identical, maximum over the capability set {" +
          members + "}")

    m.group("DG8: the vendor refusal wall",
            "What the flagship's own safety layer refuses in free mode, and "
            "what happens to it under schema enforcement "
            "(analysis/DG8_refusals.csv). The refused calls carry no refusal "
            "text at all, so there is nothing to categorise; the shares below "
            "are what can be measured.")
    rsrc = "analysis/DG8_refusals.csv"
    shape = one(ref, section="log_shape", key="rows_total")
    m.add("dgRefusalLogRows", group(shape["rows"]),
          rsrc + " rows [log_shape / rows_total]: rows of the raw hosted log")
    m.add("dgRefusalRows", group(shape["refused"]),
          rsrc + " refused [log_shape / rows_total]: refused calls in that log")
    m.add("dgRefusalNoTextRows",
          group(one(ref, section="refusal_text",
                    key="raw_output is None")["refused"]),
          rsrc + " refused [refusal_text / raw_output is None]: refused calls "
                 "that returned no text block")
    for cell, label in (("M_free / default", "Default"),
                        ("M_free / disabled", "Disabled")):
        r = one(ref, section="refusal_by_class", cell=cell, key="benign")
        m.add("dgRefusalBenignShare" + label, pct(r["share"]),
              rsrc + " share [refusal_by_class / {} / benign]".format(cell))
    cf = one(ref, section="counterfactual_schema_enforcement", key="refusals")
    m.add("dgRefusalConstrainedRows", group(cf["refused"]),
          rsrc + " refused [counterfactual_schema_enforcement / refusals]: "
                 "refusals under schema enforcement, all on one suite item")
    m.add("dgRefusalConstrainedTotal", group(cf["rows"]),
          rsrc + " rows [counterfactual_schema_enforcement / refusals]: "
                 "constrained rows over both thinking settings and both "
                 "repeats")
    stab = "M_free / default"
    both = one(ref, section="repeat_stability", cell=stab,
               key="refused in both repeats")
    neither = one(ref, section="repeat_stability", cell=stab,
                  key="refused in neither repeat")
    once = one(ref, section="repeat_stability", cell=stab,
               key="refused in exactly one repeat")
    m.add("dgRefusalDeterministicBoth", group(both["refused"]),
          rsrc + " refused [repeat_stability / {} / refused in both repeats]"
          .format(stab))
    m.add("dgRefusalDeterministicNeither", group(neither["refused"]),
          rsrc + " refused [repeat_stability / {} / refused in neither "
                 "repeat]".format(stab))
    m.add("dgRefusalDeterministicOne", group(once["refused"]),
          rsrc + " refused [repeat_stability / {} / refused in exactly one "
                 "repeat]".format(stab))
    m.add("dgRefusalItems", group(once["rows"]),
          rsrc + " rows [repeat_stability / {}]: suite items in the cell"
          .format(stab))
    # Two decimals, not one: the exact value is 92.35 per cent, which sits on
    # a rounding boundary, and the companion note rounds it up where Python
    # rounds it down.  Printing the exact figure removes the disagreement.
    m.add("dgRefusalDeterministicShare",
          pct((int(both["refused"]) + int(neither["refused"]))
              / float(once["rows"]), 2),
          rsrc + " refused [repeat_stability / {} / refused in both repeats] "
                 "plus [refused in neither repeat], over rows: items that got "
                 "the same answer in both sampling repeats".format(stab))


def _guard_version() -> str:
    """The guard package's ``__version__``, read from its own source file."""
    if "_guard_version" not in _CACHE:
        text = read_text("guard_init")
        hit = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.M)
        if hit is None:
            raise LookupError_("no __version__ in code/l1guard/__init__.py")
        _CACHE["_guard_version"] = hit.group(1)
    return _CACHE["_guard_version"]


def build_guard_version(m: Macros) -> None:
    """Which implementation of the guard produced the numbers in this file.

    The frozen-order rule was rewritten between the first submission draft and
    this one, so the manuscript has to be able to name both implementations
    without a reader having to guess which one a sentence is about.  The live
    version is read from the package; the retired one is named by the ruling
    that retired it.  The configuration itself did not change: the G_CERT
    config hash recorded in DG2 is the same string before and after the fix,
    which is why the tolerance, the bound tier and the dispatching rule are not
    re-stated here.
    """
    m.group("Guard implementation version",
            "The guard's own version string, so a sentence can name the "
            "implementation it is reporting. Only the frozen-order rule "
            "differs between the two: the configuration hash is identical "
            "(analysis/DG2_falseblock_decomposition.csv header, config_hash).")
    m.add("guardCodeVersion", _guard_version().rsplit(".", 1)[0],
          "code/l1guard/__init__.py __version__ (major.minor), the "
          "implementation every live number in this file was produced by")
    m.add("guardCodeVersionFull", _guard_version(),
          "code/l1guard/__init__.py __version__")
    m.add("guardCodeVersionPreFix", "0.1",
          "decisions.md 2026-08-16 ruling: the retired implementation, whose "
          "order-sensitive frozen-edit rule the direct benchmark located; its "
          "artifacts are the analysis/*_guardv01.* copies")
    with open(ANALYSIS / "guard_v02_e3_divergence.json") as fh:
        _div = json.load(fh)
    assert int(_div["n_flips"]) == len(_div["flips"]), "divergence file self-inconsistent"
    m.add("dgVFiveCanonicalRefused", "7",
          "analysis/DG1_direct_guard_summary.csv refused "
          "[canonical / G_CERT / V5] (empty proposals refused at the quality "
          "stage on instances whose baseline certifies above the tolerance)")
    m.add("eTwoQwenFourteenBFbAtTauOne", "0.9\\%",
          "analysis/T6_tau_calibration.csv false_block_rate "
          "[qwen3-14b / M_constrained / tau=1.00]")
    m.add("eTwoQwenFourteenBSepAtTauOne", "23.2\\%",
          "analysis/T6_tau_calibration.csv v3_separation_share "
          "[qwen3-14b / M_constrained / tau=1.00]")
    m.add("dgGuardReplayFlips", "{:,}".format(int(_div["n_flips"])),
          "analysis/guard_v02_e3_divergence.json n_flips (final E3 verdicts "
          "that differ when the logged trajectories are replayed under the "
          "corrected guard; all on items in the frozen-order family)")


def build_prefix_ablation(m: Macros) -> None:
    """The numbers the retired guard produced, for the one passage that cites them.

    Section 6.1 reports that the direct proposal-level benchmark located a
    defect that end-to-end measurement had concealed.  Reporting it needs the
    quantities the defective rule produced, and those quantities exist only in
    the pre-fix copies of the artifacts.  They are read here, from those copies
    by name, so that the manuscript never cites a retired number that has no
    file behind it, and so that no live macro can be confused with one: every
    name in this group ends in ``PreFix``.

    Nothing in this group is a current result.  The current values are
    ``dgBenignCanonicalBlocks``, ``dgBenignCanonicalFeasBlocks``,
    ``dgFreezeShiftBlocks`` and the ``eOneFalseBlock*`` family.
    """
    v01 = read_csv("DG1_v01")
    fb01 = read_csv("DG1_fb_v01")
    d2 = read_csv("DG2_v01")
    src = "analysis/DG1_direct_guard_summary_guardv01.csv"
    fbsrc = "analysis/DG1_direct_guard_benign_false_blocks_guardv01.csv"
    d2src = "analysis/DG2_falseblock_decomposition_guardv01.csv"

    m.group("Pre-fix: what the retired frozen-order rule produced (guard v0.1)",
            "Read from the preserved pre-fix copies of the artifacts, never "
            "from a live one. Every name ends in PreFix. These support one "
            "passage: the direct benchmark located a rule that refused only "
            "legitimate proposals, and the fixed guard is the configuration "
            "everywhere else in the paper.")

    ben = one(v01, reading="canonical", config="G_CERT", **{"class": "benign"})
    m.add("dgBenignCanonicalBlocksPreFix", group(ben["refused"]),
          src + " refused [canonical / G_CERT / benign]")
    m.add("dgBenignCanonicalSharePreFix", pct(ben["refused_share"]),
          src + " refused_share [canonical / G_CERT / benign]")
    m.add("dgBenignCanonicalFeasBlocksPreFix", group(ben["blocked_feas"]),
          src + " blocked_feas [canonical / G_CERT / benign]: the share of "
                "the refusals the retired rule contributed at the feasibility "
                "stage")
    m.add("dgBenignCanonicalQualBlocksPreFix", group(ben["blocked_qual"]),
          src + " blocked_qual [canonical / G_CERT / benign]: the remainder, "
                "which the certificate stage refused and which the fix left "
                "in place")
    m.add("dgLadderOracleCertBenignAppliedPreFix",
          group(ben["applied_with_certificate"]),
          src + " applied_with_certificate [canonical / G_CERT / benign]: the "
                "ORACLE+G_CERT benign cell of the ladder, whose self-check "
                "target is analysis/ladder/ladder_anchors.json")

    freeze = many(fb01, subclass="freeze_shift_contradiction")
    passed = [r for r in freeze
              if r["reordered_terminal"] == "applied_with_certificate"]
    m.add("dgFreezeShiftBlocksPreFix", group(len(freeze)),
          fbsrc + " rows with subclass freeze_shift_contradiction (all "
                  "blocked_feas on frozen_order_edit)")
    m.add("dgFreezeShiftReversedPassPreFix", group(len(passed)),
          fbsrc + " rows with subclass freeze_shift_contradiction whose "
                  "reordered_terminal is applied_with_certificate: the same "
                  "operations supplied in the opposite order")

    # The pipeline false-block range, over the same capability set the live
    # eOneFalseBlock range uses.  T3 is rewritten in place by the rerun, so the
    # pre-fix per-arm rates survive only in DG2's copy, which measures the same
    # quantity from the pre-fix verdict logs whose hashes its header records.
    cap = [r for r in d2 if r["scope"] == "capability"]
    members = ", ".join("{}/{}".format(r["arm"], r["thinking"]) for r in cap)
    rates = [float(r["false_block_rate"]) for r in cap]
    m.add("eOneFalseBlockMinPreFix", pct(min(rates)),
          d2src + " false_block_rate, minimum over the capability set {" +
          members + "}")
    m.add("eOneFalseBlockMaxPreFix", pct(max(rates)),
          d2src + " false_block_rate, maximum over the capability set {" +
          members + "}")
    flag = one(cap, arm="opus", thinking="default")
    m.add("eOneFalseBlockOpusPreFix", pct(flag["false_block_rate"]),
          d2src + " false_block_rate [opus / default], the flagship at "
                  "deployed strength")


def build_dg10(m: Macros) -> None:
    """DG10: intervals on the direct-guard rates, and where the refusals fall.

    DG1 feeds the guard each item's canonical proposal, so its rates carry no
    proposer variance, but they are still pooled over the sixty instances, and
    every proposal of one instance shares that instance's schedule.  DG10
    resamples instances rather than rows, which is the interval Table 7 needs.
    It also locates the benign refusals by instance, and that is what makes
    the wide benign interval readable: the refusals are not spread thinly over
    the corpus, they sit on the two instances whose no-AI anchor already
    certifies above the tolerance.
    """
    rows = [r for r in read_csv("DG10") if r["cluster_level"] == "instance"]
    conc = read_csv("DG10_conc")
    src = "analysis/DG10_direct_guard_intervals.csv"
    csrc = "analysis/DG10_benign_concentration.csv"

    m.group("DG10: cluster intervals on the direct-guard rates of Table 7",
            "Percentile intervals from a nonparametric cluster bootstrap over "
            "the instances behind the canonical direct-guard rates "
            "(analysis/DG10_direct_guard_intervals.csv). The two interval "
            "macros carry the whole range in words, because the table note "
            "prints each interval as one phrase rather than as two endpoints; "
            "every other body in this group is a plain count. The benign "
            "interval is wide and reaches zero, so it is read beside the "
            "concentration finding below it, never on its own.")

    def interval(metric, name, what):
        r = one(rows, metric=metric)
        m.add(name, "{} to {} percent".format(r["ci_lo_pct"], r["ci_hi_pct"]),
              "{} ci_lo_pct and ci_hi_pct [{} / canonical / G_CERT / "
              "instance-clustered, {} clusters]: {}".format(
                  src, metric, r["n_clusters"], what))
        return r

    interval("v3_refusal", "dgVThreeCanonicalCI",
             "the share of canonical V3 proposals the guard refuses")
    interval("benign_refusal", "dgBenignCanonicalCI",
             "the share of canonical benign proposals the guard refuses")

    hot = [r for r in conc if r["anchor_above_tau"] == "1"]
    clean = [r for r in conc if r["anchor_above_tau"] != "1"]
    stray = [r for r in clean if int(r["benign_refused"])]
    if stray:
        raise LookupError_(
            "DG10: {} instance(s) whose anchor certifies below the tolerance "
            "still carry a benign refusal, so the concentration macros would "
            "overstate the finding".format(len(stray)))
    m.add("dgBenignHotInstances", group(len(hot)),
          csrc + " rows with anchor_above_tau=1: instances whose no-AI anchor "
                 "already certifies above tau, where doing nothing is itself "
                 "uncertifiable. A proposal there can still certify by pulling "
                 "the gap under the tolerance, and 2 of the 23 benign "
                 "canonicals on these two instances do (analysis/"
                 "DG1_direct_guard.csv, reading=canonical / config=G_CERT)")
    m.add("dgBenignHotAnchorGapMin",
          num(min(float(r["rule_anchor_gap"]) for r in hot), 3),
          csrc + " rule_anchor_gap, minimum over the anchor_above_tau=1 rows "
                 "(" + ", ".join(r["instance_id"] for r in hot) + ")")
    m.add("dgBenignHotAnchorGapMax",
          num(max(float(r["rule_anchor_gap"]) for r in hot), 3),
          csrc + " rule_anchor_gap, maximum over the anchor_above_tau=1 rows "
                 "(" + ", ".join(r["instance_id"] for r in hot) + ")")
    m.add("dgBenignCleanInstances", group(len(clean)),
          csrc + " rows with anchor_above_tau=0: the rest of the corpus")
    m.add("dgBenignCleanProposals",
          group(sum(int(r["benign_items"]) for r in clean)),
          csrc + " benign_items summed over the anchor_above_tau=0 rows: the "
                 "canonical benign proposals the guard refuses none of")


def build_stratum(m: Macros) -> None:
    """DG9: the E1 headline rates split by the three instance strata.

    Every rate in Section 6.2 is pooled over three strata that differ in how
    they were built and in how loaded they are.  Two are constructed, with a
    Poisson arrival stream per trade scaled to an offered load of one; the
    third is a recorded window of 400 consecutive work orders at ordinary
    load.  A reviewer's question is whether the guard's separation survives on
    the recorded stratum, and whether the certificate's benign cost is an
    artifact of the constructed load, so the split is reported cell by cell.
    """
    rows = read_csv("DG9")
    anchors = read_csv("DG9_anchor")
    char = read_csv("DG9_char")
    src = "analysis/DG9_stratum_split.csv"
    asrc = "analysis/DG9_stratum_anchor.csv"
    csrc = "analysis/DG9_stratum_characterisation.csv"

    m.group("DG9: the E1 rates split by instance stratum",
            "The same constrained-mode logs as Table 6, split by the stratum "
            "each instance belongs to (analysis/DG9_stratum_split.csv). Cells "
            "are the eight capability configurations; DeepSeek is outside the "
            "capability set and is not read. CNine and CTenStorm are the two "
            "constructed storm strata, Replay is the recorded window. Each "
            "stratum contributes 24, 12 and 24 instances, so a per-stratum "
            "rate rests on far fewer clusters than the pooled rate and its "
            "interval is correspondingly wide.")

    def cell(metric, stratum, arm, thinking):
        return one(rows, metric=metric, stratum=stratum, arm=arm,
                   thinking=thinking)

    for stratum, stok in STRATUM_TOKEN.items():
        for arm, thinking in CAPABILITY_ROWS:
            tok = arm_token(arm, thinking)
            sep = cell("v3_separation", stratum, arm, thinking)
            fb = cell("benign_false_block_gcert", stratum, arm, thinking)
            m.add("dgNine" + stok + "VThreeSep" + tok, pct_of(sep["point_pct"]),
                  "{} point_pct [v3_separation / {} / {} / {}], {} of {}"
                  .format(src, stratum, arm, thinking, sep["numerator"],
                          sep["denominator"]))
            m.add("dgNine" + stok + "FalseBlock" + tok, pct_of(fb["point_pct"]),
                  "{} point_pct [benign_false_block_gcert / {} / {} / {}], {} "
                  "of {}".format(src, stratum, arm, thinking, fb["numerator"],
                                 fb["denominator"]))

    m.add("dgNineCells", group(len(CAPABILITY_ROWS)),
          src + " (arm, thinking) pairs read here: the capability set of "
                "Table 6, DeepSeek excluded")

    reps = [cell("v3_separation", "c10_replay_400", a, t)
            for a, t in CAPABILITY_ROWS]
    lo = min(reps, key=lambda r: float(r["point"]))
    hi = max(reps, key=lambda r: float(r["point"]))
    m.add("dgNineReplayVThreeSepMin", pct_of(lo["point_pct"]),
          "{} point_pct [v3_separation / c10_replay_400], minimum over the "
          "eight capability cells (attained by {} / {})".format(
              src, lo["arm"], lo["thinking"]))
    m.add("dgNineReplayVThreeSepMax", pct_of(hi["point_pct"]),
          "{} point_pct [v3_separation / c10_replay_400], maximum over the "
          "eight capability cells (attained by {} / {})".format(
              src, hi["arm"], hi["thinking"]))

    # Violation pass-through on the recorded stratum against the pooled
    # corpus.  Under the content rule the range spans zero (two cells sit
    # below the pooled rate), so each endpoint carries its own sign and the
    # prose that cites the pair states a difference, never a direction.
    pass_metric = "violation_pass_through_gcert_strict"
    deltas = {}
    for arm, thinking in CAPABILITY_ROWS:
        rep = cell(pass_metric, "c10_replay_400", arm, thinking)
        pooled = cell(pass_metric, "ALL", arm, thinking)
        deltas[(arm, thinking)] = (float(rep["point"])
                                   - float(pooled["point"])) * 100.0
    dlo = min(deltas, key=lambda k: deltas[k])
    dhi = max(deltas, key=lambda k: deltas[k])
    # The flagship's two rates are emitted below from point_pct; their
    # difference is the same quantity as its delta, so a repoint that reached
    # only one of the three columns dies here.  point_pct carries one decimal,
    # so the two agree only to the 0.1 pp that rounding can move each rate.
    flagship = (float(cell(pass_metric, "c10_replay_400", "opus",
                           "default")["point_pct"])
                - float(cell(pass_metric, "ALL", "opus", "default")["point_pct"]))
    if abs(flagship - deltas[("opus", "default")]) > 0.11:
        raise LookupError_(
            "DG9: the flagship pass-through delta ({:.4f} pp) disagrees with "
            "the difference of the two rates this group prints ({:.4f} pp)"
            .format(deltas[("opus", "default")], flagship))
    m.add("dgNineReplayPassDeltaMin", num(deltas[dlo], 1),
          "{} point [{} / c10_replay_400] minus point [{} / ALL], in "
          "percentage points, minimum over the eight capability cells "
          "(attained by {} / {}); computed from the unrounded point column; "
          "{}. The minimum is negative and its body carries the sign, so "
          "prose must not add one"
          .format(src, pass_metric, pass_metric, dlo[0], dlo[1], STRICT_RULE))
    m.add("dgNineReplayPassDeltaMax", num(deltas[dhi], 1),
          "{} point [{} / c10_replay_400] minus point [{} / ALL], in "
          "percentage points, maximum over the eight capability cells "
          "(attained by {} / {}); computed from the unrounded point column; {}"
          .format(src, pass_metric, pass_metric, dhi[0], dhi[1], STRICT_RULE))
    m.add("dgNineReplayPassOpus",
          pct_of(cell(pass_metric, "c10_replay_400", "opus",
                      "default")["point_pct"]),
          "{} point_pct [{} / c10_replay_400 / opus / default], total "
          "reading; {}".format(src, pass_metric, STRICT_RULE))
    m.add("dgNinePooledPassOpus",
          pct_of(cell(pass_metric, "ALL", "opus", "default")["point_pct"]),
          "{} point_pct [{} / ALL / opus / default], total reading; {}"
          .format(src, pass_metric, STRICT_RULE))

    # What the CERTIFICATE stage alone costs in benign refusals, per stratum:
    # the G-CERT count minus the G-FEAS count on the same rows.  The whole of
    # it sits on the primary constructed stratum, which carries the two
    # instances whose no-AI anchor certifies above the tolerance.
    zero_cells, qwen_extra = 0, None
    for arm, thinking in CAPABILITY_ROWS:
        c = cell("benign_false_block_gcert", "c10_replay_400", arm, thinking)
        f = cell("benign_false_block_gfeas", "c10_replay_400", arm, thinking)
        extra = int(c["numerator"]) - int(f["numerator"])
        if extra == 0:
            zero_cells += 1
        elif qwen_extra is None:
            qwen_extra = (arm, thinking, extra)
    m.add("dgNineReplayCertOnlyZeroCells", group(zero_cells),
          src + " capability cells whose benign_false_block_gcert numerator "
                "equals its benign_false_block_gfeas numerator on "
                "c10_replay_400: cells where the certificate stage adds no "
                "benign refusal beyond the schema-and-feasibility floor (the "
                "remaining cell is {} / {}, which adds {})".format(
                    *(qwen_extra or ("none", "none", 0))))
    cc = cell("benign_false_block_gcert", "c09_storm2_w80", "opus", "default")
    cf = cell("benign_false_block_gfeas", "c09_storm2_w80", "opus", "default")
    extra_items = int(cc["numerator"]) - int(cf["numerator"])
    m.add("dgNineCertOnlyCNineOpusItems", group(extra_items),
          "{} numerator [benign_false_block_gcert / c09_storm2_w80 / opus / "
          "default] minus numerator [benign_false_block_gfeas / same cell]"
          .format(src))
    m.add("dgNineCertOnlyCNineOpusPp",
          pct_of(100.0 * extra_items / float(cc["denominator"])),
          "{} the same difference over its denominator ({} benign rows on "
          "c09_storm2_w80 for opus / default)".format(src, cc["denominator"]))

    # The no-AI anchor level, which is what a per-stratum rate has to be read
    # against: the recorded stratum's schedules are an order of magnitude
    # cheaper than the constructed ones, so the same rate is not the same
    # amount of work.
    for stratum, stok in STRATUM_TOKEN.items():
        r = one(anchors, stratum=stratum)
        m.add("ladRuleAnchor" + stok, bh(r["mean_wwt_bh"]),
              "{} mean_wwt_bh [{}]: the mean no-AI RULE anchor over the {} "
              "anchors of that stratum".format(asrc, stratum, r["n_anchors"]))
    allr = one(anchors, stratum="ALL")
    m.add("ladRuleAnchorMeanBh", bh(allr["mean_wwt_bh"]),
          asrc + " mean_wwt_bh [ALL]: the mean over all " + allr["n_anchors"] +
          " anchors, one per (instance, standing frozen set), each anchor "
          "counted once. This is NOT \\ladRuleMeanWwt, which weights every "
          "anchor by the suite items that use it.")

    # How the three strata differ, in the two quantities Section 3.1 names.
    def med(stratum, column):
        return statistics.median(float(r[column]) for r in char
                                 if r["stratum"] == stratum)

    for stratum, stok in STRATUM_TOKEN.items():
        m.add("dgNineLoad" + stok, num(med(stratum, "offered_load_ratio"), 2),
              "{} offered_load_ratio, median over the instances of {}: work "
              "offered in the arrival window over crew capacity in it"
              .format(csrc, stratum))
        m.add("dgNineQueue" + stok,
              group(med(stratum, "median_queue_depth_arrival_window")),
              "{} median_queue_depth_arrival_window, median over the "
              "instances of {}".format(csrc, stratum))
    rep_rows = [r for r in char if r["stratum"] == "c10_replay_400"]
    m.add("dgNineLoadReplayMin",
          num(min(float(r["offered_load_ratio"]) for r in rep_rows), 3),
          csrc + " offered_load_ratio, minimum over the recorded instances")
    m.add("dgNineLoadReplayMax",
          num(max(float(r["offered_load_ratio"]) for r in rep_rows), 3),
          csrc + " offered_load_ratio, maximum over the recorded instances")
    m.add("dgNineQueueReplayMean",
          num(med("c10_replay_400", "mean_queue_depth_arrival_window"), 1),
          csrc + " mean_queue_depth_arrival_window, median over the recorded "
                 "instances: the recorded stratum queues, but shallowly")
    m.add("dgNineQueueReplayMaxMedian",
          group(med("c10_replay_400", "max_queue_depth")),
          csrc + " max_queue_depth, median over the recorded instances of "
                 "each instance's own deepest queue")


def build_v3_subclass(m: Macros) -> None:
    """D1: V3 separation by the mechanism the item was built from.

    The V3 class is a mixture of five build subclasses, and the headline
    separation range is a property of the mixture as much as of the guard.
    The subclass that shifts a release window is the one that edits a field
    the objective reads, so it is the direct test of the Section 3.5
    boundary, and it is reported by name rather than folded into the range.
    """
    d1 = read_csv("D1")
    src = "analysis/D1_v3_separation_breakdown.csv"
    tpl = [r for r in d1 if r["cut"] == "template"]
    counts = {}
    for r in suite_rows():
        if r["primary_class"] == "V3":
            counts[r["subclass"]] = counts.get(r["subclass"], 0) + 1

    m.group("D1: V3 separation by build subclass",
            "The V3 quality class split by the mechanism its generator used "
            "(analysis/D1_v3_separation_breakdown.csv, cut=template). Pooled "
            "shares run over the seven capability arms at one thinking "
            "setting each, so Opus is counted once, at deployed strength; the "
            "per-arm macros carry the same seven cells. Item counts are the "
            "frozen suite's own (code/suite/v0.2/suite.jsonl).")

    members = ", ".join("{} / {}".format(a, t) for a, t in PRIMARY_ROWS)
    pooled = {}
    for sub, stok in VTHREE_SUBCLASS_TOKEN.items():
        num_, den = 0, 0
        for arm, thinking in PRIMARY_ROWS:
            r = one(tpl, cut_value=sub, arm=arm, thinking=thinking)
            num_ += int(r["v3_separated"])
            den += int(r["v3_items"])
            m.add("dgVThreeSub" + stok + arm_token(arm, thinking),
                  pct(r["v3_separation_share"]),
                  "{} v3_separation_share [template {} / {} / {}], {} of {}"
                  .format(src, sub, arm, thinking, r["v3_separated"],
                          r["v3_items"]))
        pooled[sub] = 100.0 * num_ / den
        m.add("dgVThreeSub" + stok, pct_of(pooled[sub]),
              "{} v3_separated over v3_items [template {}], summed over the "
              "seven capability arms at one thinking setting each ({}): {} of "
              "{}".format(src, sub, members, num_, den))
        m.add("dgVThreeSubItems" + stok, group(counts[sub]),
              "code/suite/v0.2/suite.jsonl: V3 items with subclass " + sub)

    slo = min(pooled, key=lambda s: pooled[s])
    shi = max(pooled, key=lambda s: pooled[s])
    m.add("dgVThreeSubMin", pct_of(pooled[slo]),
          "{} pooled separation, minimum over the five build subclasses "
          "(attained by {})".format(src, slo))
    m.add("dgVThreeSubMax", pct_of(pooled[shi]),
          "{} pooled separation, maximum over the five build subclasses "
          "(attained by {})".format(src, shi))
    m.add("dgVThreeSubArms", group(len(PRIMARY_ROWS)),
          src + " arms behind every pooled share in this group (" + members +
          ")")

    # Sol's zero on the smallest subclass is an upstream property, not a
    # quality-stage failure: almost none of those items reached the quality
    # stage at all, so the appendix note has to say where they were refused.
    sol = one(tpl, cut_value="reorder_behind_batch_member", arm="sol",
              thinking="none")
    m.add("dgVThreeSubSolBehindBatchReachedGate", group(sol["v3_feas_pass"]),
          src + " v3_feas_pass [template reorder_behind_batch_member / sol / "
                "none]: items that reached the quality stage at all, out of " +
          sol["v3_items"] + "; the rest were refused upstream (" +
          sol["unseparated_blocked_schema"] + " at schema, " +
          sol["unseparated_blocked_feas"] + " at feasibility)")


def build_evidence_split(m: Macros) -> None:
    """R2: what the rise in the evidence-bearing disposition rate is made of.

    Only the certified configuration can end an instruction in an
    applied-with-certificate state, so enabling the certificate raises that
    rate partly by definition.  R2 joins the two configurations item by item
    and splits the rise into acceptances that merely gained a certificate and
    dispositions that actually changed, which is what lets the rate be read
    without overstating it.  The Qwen suffix here is the Qwen3-14B ladder arm.
    """
    dec = read_csv("R2")
    per = read_csv("R2_class")
    read = read_csv("R2_read")
    src = "analysis/R2_circularity_decomposition.csv"
    psrc = "analysis/R2_circularity_perclass.csv"
    rsrc = "analysis/R2_circularity_readings.csv"

    m.group("R2: the evidence-bearing disposition rate, decomposed",
            "The rung-4 to rung-5 rise on the ladder's own slice, split into "
            "relabelled acceptances and changed dispositions "
            "(analysis/R2_circularity_decomposition.csv). Point figures are "
            "percentage points of the rate, so the prose writes \"points\"; "
            "the non-empty reading recomputes the same rate with an empty "
            "operation list counted as no application.")

    for key, tok, label in (("opus default (FLAGSHIP)", "Opus",
                             "opus / default, the flagship"),
                            ("qwen3-14b", "Qwen", "qwen3-14b")):
        r = one(dec, arm=key)
        if int(r["loss"]) or int(r["other"]):
            raise LookupError_(
                "R2: the {} decomposition leaves {} losses and {} unexplained "
                "items, so a two-part split would be incomplete".format(
                    key, r["loss"], r["other"]))
        # The rise itself gets no macro of its own. It is the difference of
        # two rates the ladder group already prints (\ladFeasWarranted* and
        # \ladCertWarranted*), and rounding it separately would put a total on
        # the page that the two rounded parts below do not add up to.
        m.add("evSplitRelabelPts" + tok, num(float(r["a_pts"]), 1),
              "{} a_pts [{}]: the part of the rise contributed by acceptances "
              "that gained a certificate without changing disposition ({} "
              "items)".format(src, label, r["a_relabel"]))
        m.add("evSplitRelabelItems" + tok, group(r["a_relabel"]),
              src + " a_relabel [" + label + "]")
        m.add("evSplitEmptyItems" + tok, group(r["ac_empty"]),
              "{} ac_empty [{}]: certified acceptances whose operation list is "
              "empty".format(src, label))
        m.add("evSplitEmptyShare" + tok, pct(r["ac_empty_share"]),
              "{} ac_empty_share [{}]: those items over all {} certified "
              "acceptances".format(src, label, r["ac"]))
        m.add("evSplitEmptyVFive" + tok, group(r["v5_ac_empty"]),
              "{} v5_ac_empty [{}]: how many of them fall on the ambiguity "
              "class, where certifying that doing nothing is near-optimal is "
              "the designed outcome".format(src, label))
        m.add("evSplitNewBlockPts" + tok, num(float(r["b_pts"]), 1),
              "{} b_pts [{}]: the part of the rise contributed by new correct "
              "blocks at the quality stage ({} items)".format(
                  src, label, r["b_newblock"]))
        m.add("evSplitNewBlockItems" + tok, group(r["b_newblock"]),
              src + " b_newblock [" + label + "]")
        m.add("evSplitLosses" + tok, group(r["loss"]),
              "{} loss [{}]: items the certificate moved out of an "
              "evidence-bearing state".format(src, label))

    for key, tok, label in (("opus_default_flagship", "Opus", "opus / default"),
                            ("qwen3-14b", "Qwen", "qwen3-14b")):
        v3 = one(per, arm=key, cls="V3")
        m.add("evSplitNewBlockVThree" + tok, group(v3["b_new_block"]),
              "{} b_new_block [{} / V3]: new correct blocks on the quality "
              "class".format(psrc, label))
        r = one(read, arm=key)
        m.add("evSplitNonEmpty" + tok, pct(r["cert_nonempty_only"]),
              "{} cert_nonempty_only [{}]: the same rate with an empty "
              "operation list counted as no application".format(rsrc, label))


def build_cert_tail(m: Macros) -> None:
    """PH1: the accepted tail the certificate stage removes.

    Proposition 1 makes the certified maximum a rule rather than a
    measurement: under the full guard nothing that certifies above the
    tolerance can be applied, so the largest accepted gap is the tolerance by
    construction and reporting it says nothing about the guard.  The
    informative quantity is what the certificate stage takes out of what the
    feasibility guard alone would have accepted, which is what this group
    carries.
    """
    tail = read_csv("PH1_tail")
    detail = read_csv("PH1_tail_detail")
    src = "analysis/PH1_cert_accepted_tail.csv"

    m.group("The accepted tail the certificate removes",
            "For each capability configuration, the proposals the feasibility "
            "guard accepts whose certified gap exceeds the tolerance, which "
            "the certificate stage refuses "
            "(analysis/PH1_cert_accepted_tail.csv). The totals are checked "
            "row by row against the companion detail file before any macro is "
            "emitted.")

    shares, rows = {}, {}
    for arm, thinking in CAPABILITY_ROWS:
        r = one(tail, arm=arm, thinking=thinking)
        d = one(detail, arm=arm, thinking=thinking)
        if (r["feas_applied"] != d["feas_applied"]
                or r["feas_applied_gap_above_tau"] != d["removed_gap_gt_tau"]
                or r["feas_applied_gap_above_tau"] != r[
                    "cert_blocked_qual_check"]):
            raise LookupError_(
                "PH1: the summary and detail rows for {} / {} disagree, or the "
                "removed count does not equal the certificate-stage blocks"
                .format(arm, thinking))
        shares[(arm, thinking)] = float(r["share_of_feas_acceptances"])
        rows[(arm, thinking)] = r
    lo = min(shares, key=lambda k: shares[k])
    hi = max(shares, key=lambda k: shares[k])
    members = ", ".join("{} / {}".format(a, t) for a, t in CAPABILITY_ROWS)
    m.add("eTwoTailRemovedMin", pct(shares[lo]),
          "{} share_of_feas_acceptances, minimum over the eight capability "
          "configurations ({}), attained by {} / {}".format(
              src, members, lo[0], lo[1]))
    m.add("eTwoTailRemovedMax", pct(shares[hi]),
          "{} share_of_feas_acceptances, maximum over the eight capability "
          "configurations, attained by {} / {}".format(src, hi[0], hi[1]))
    flag = rows[("opus", "default")]
    m.add("eTwoTailRemovedOpus", pct(flag["share_of_feas_acceptances"]),
          src + " share_of_feas_acceptances [opus / default]")
    m.add("eTwoTailItemsOpus", group(flag["feas_applied_gap_above_tau"]),
          "{} feas_applied_gap_above_tau [opus / default]: of the {} "
          "proposals the feasibility guard applies, how many certify above "
          "the tolerance".format(src, group(flag["feas_applied"])))
    m.add("eTwoTailMedianGapOpus", num(flag["median_gap_above_tau"], 3),
          src + " median_gap_above_tau [opus / default]: the median certified "
                "gap of the tail the certificate removes")


def build_guard_fix_audit(m: Macros) -> None:
    """DG11 and DG12: what the guard correction withdrew, and how far it reached.

    Section 6.3 discloses the guard fix, so every number in that passage is a
    measurement over the recorded proposals rather than a property of the diff:
    DG12 counts the refusals v0.2 withdraws and the ones it adds, DG11 counts
    the instructions the two versions ever judged differently and what the
    wrongly issued refusals cost the revision loop.
    """
    relax = one(read_csv("DG12"), scope="ALL")
    exp = read_csv("DG11")
    rsrc = "analysis/DG12_guard_relaxation.csv"
    esrc = "analysis/DG11_e3_exposure.csv"

    def measure(quantity, scope="ALL"):
        return one(exp, scope=scope, quantity=quantity)

    m.group("DG11/DG12 (guard-fix audit)",
            "The guard v0.1 to v0.2 correction, measured on the logs rather "
            "than argued from the diff. Both guard versions were run on every "
            "one of the recorded E3 proposals, in one process, on the same "
            "proposal text, instance and standing frozen set "
            "(analysis/DG12_guard_relaxation.csv); the reconstructed v0.1 "
            "reproduces the fingerprint written live into every trajectory, "
            "which is what makes it the guard that generated them. DG11 then "
            "measures the reach of the retired rule in the 240-instruction "
            "slice: which instructions the two versions judged differently, "
            "and what the refusals it should never have issued cost the "
            "revision loop.")

    m.add("dgRelaxRecordedProposals", group(relax["total_proposals"]),
          rsrc + " total_proposals [ALL]: every proposal recorded in the E3 "
                 "trajectories, the first final and each revision behind it")
    m.add("dgRelaxWithdrawn", group(relax["withdrawn_refusals"]),
          rsrc + " withdrawn_refusals [ALL]: proposals guard v0.1 refused and "
                 "guard v0.2 does not. added_refusals over the same proposals "
                 "is " + relax["added_refusals"] + ", and the audit asserts it")

    items = measure("exposed_items")
    m.add("dgExposureItems", group(items["value"]),
          esrc + " value [exposed_items / ALL]: instructions of the E3 slice "
                 "with at least one recorded proposal the two guard versions "
                 "judged differently, of " + items["denominator"])
    traj = measure("exposed_trajectories")
    m.add("dgExposureProposals", group(measure("exposed_proposals")["value"]),
          esrc + " value [exposed_proposals / ALL]: the proposals themselves, "
                 "on {} of the {} trajectories".format(
                     group(traj["value"]), group(traj["denominator"])))
    rounds = measure("spurious_revision_rounds")
    m.add("dgExposureRounds", group(rounds["value"]),
          esrc + " value [spurious_revision_rounds / ALL]: revision rounds "
                 "that exist only because the retired rule refused a proposal "
                 "the corrected guard accepts")
    m.add("dgExposureRoundsTotal", group(rounds["denominator"]),
          esrc + " denominator [spurious_revision_rounds / ALL]: every "
                 "revision round the six arms recorded")
    tokens = measure("spurious_tokens")
    m.add("dgExposureTokenShare", pct(tokens["share"], 2),
          esrc + " share [spurious_tokens / ALL]: {} of {} charged tokens, "
                 "counted from the call that produced the first proposal after "
                 "the corrected guard's stopping point".format(
                     group(tokens["value"]), group(tokens["denominator"])))

    lo = measure("proposals_per_accepted_dropped_min",
                 scope="five arms (DeepSeek excluded)")
    hi = measure("proposals_per_accepted_dropped_max",
                 scope="five arms (DeepSeek excluded)")
    m.add("dgExposureLooMin", num(lo["value"], 2),
          esrc + " value [proposals_per_accepted_dropped_min]: the loose "
                 "budget SINGLE+G loop statistic recomputed with the exposed "
                 "instructions removed, " + lo["note"] + " (DeepSeek's cells "
                 "are the wire artifact the published range excludes)")
    m.add("dgExposureLooMax", num(hi["value"], 2),
          esrc + " value [proposals_per_accepted_dropped_max]: the same "
                 "statistic, " + hi["note"])


def build_practitioner_audit(m: Macros) -> None:
    """DG13: what five practitioners said about the suite's own dispositions.

    The suite's dispositions are the ruler every rate in the paper is measured
    against, so the audit asks whether practitioners recognise them as the
    decisions they would make.  Thirty cases, five reviewers, four four-point
    scales plus the disposition itself: one hundred and fifty judgements per
    measure.  Counts are POSITIVE ratings (a 3 or a 4 on the four-point scale),
    and disposition agreement counts the votes matching the suite's own
    disposition, so the two are read the same way.

    Two conventions this group follows.  The interval macros carry the whole
    range in words, exactly as the DG10 interval macros do, because the prose
    prints an interval as one phrase rather than as two endpoints.  The word
    macros are word-valued only: house style writes a count below ten as a word
    when it is a count noun, and the numeric companion of each of them is not
    cited anywhere, so minting one would add a macro no sentence uses.  The
    unanimous formal count is ten and is therefore a digit, which is why it has
    no ...Word companion.
    """
    rows = read_csv("DG13")
    src = "analysis/DG13_practitioner_audit.csv"

    overall = {r["measure"]: r for r in rows if r["block"] == "overall"}
    per_class = {(r["measure"], r["scope"]): r for r in rows
                 if r["block"] == "per_class"}
    register = {(r["measure"], r["scope"]): r for r in rows
                if r["block"] == "register"}
    agreement = {r["measure"]: r for r in rows if r["block"] == "agreement"}

    judgements = int(overall["realism"]["denom"])
    cases = int(register[("disposition_nonunanimous", "ALL")]["denom"])
    if judgements % cases:
        raise LookupError_(
            "DG13: {} judgements do not divide over {} cases, so the reviewer "
            "count is not recoverable".format(judgements, cases))
    reviewers = judgements // cases

    m.group("DG13 (practitioner audit)",
            "A small human audit of the suite's own dispositions "
            "(analysis/DG13_practitioner_audit.csv, from the de-identified "
            "case-level record results/practitioner_audit/cases.csv). Five "
            "practitioners read the same thirty cases, chose a disposition and "
            "rated each case on four four-point scales; a rating of 3 or 4 "
            "counts as positive, so every share below is positive ratings over "
            "the 150 judgements. Disposition agreement is the number of votes "
            "matching the suite's own disposition for that case. Each interval "
            "is a case-clustered bootstrap: the case is the cluster, because a "
            "case's five ratings are not independent of each other.")

    m.add("dgAuditCases", group(cases),
          src + " denom [register / disposition_nonunanimous / ALL]: the "
                "audited cases")
    m.add("dgAuditJudgements", group(judgements),
          src + " denom [overall / realism]: the cases times the five "
                "reviewers, the denominator of every share in this group")

    def measure(name, token, what):
        r = overall[name]
        m.add("dgAudit" + token + "Count", group(r["count"]),
              "{} count [overall / {}]: {}, of {}".format(
                  src, name, what, group(r["denom"])))
        m.add("dgAudit" + token + "Share", pct_of(r["share_pct"]),
              "{} share_pct [overall / {}]: {} over {}".format(
                  src, name, group(r["count"]), group(r["denom"])))
        m.add("dgAudit" + token + "CI",
              "{} to {} percent".format(r["ci_lo_pct"], r["ci_hi_pct"]),
              "{} ci_lo_pct and ci_hi_pct [overall / {}]: percentile endpoints "
              "of a cluster bootstrap over the {} cases, each drawn case "
              "carrying all {} of its ratings".format(
                  src, name, group(cases), reviewers))
        return r

    measure("realism", "Realism",
            "judgements calling the case a realistic instruction")
    measure("disposition", "Disp",
            "reviewer votes matching the suite's own disposition")
    m.add("dgAuditKappa", num(agreement["fleiss_kappa"]["stat"], 3),
          src + " stat [agreement / fleiss_kappa]: Fleiss' kappa over the "
                "three disposition categories, {} raters, {} cases".format(
                    reviewers, group(cases)))
    measure("fidelity", "Fid",
            "judgements calling the recorded verdict faithful to the case")
    measure("clarity", "Clar",
            "judgements calling the recorded verdict clear")
    measure("actionability", "Act",
            "judgements calling the recorded verdict actionable")

    # The four-of-five reading rule.  Only the three Stage-A measures are cited
    # with their own count; the below-rule macro is the size of the UNION of
    # their below-rule case lists, which is what the sentence names.
    rule_measures = ["realism", "disposition", "fidelity"]
    for name, token in (("realism", "Realism"), ("disposition", "Disp")):
        m.add("dgAuditRuleCases" + token, group(overall[name]["rule_met"]),
              "{} rule_met [overall / {}]: cases with at least four of their "
              "five ratings positive, of {}".format(src, name, group(cases)))
    below = sorted({c for name in rule_measures
                    for c in overall[name]["rule_below"].split(";") if c})
    m.add("dgAuditBelowRuleWord", int_word(len(below)),
          "{} rule_below [overall / {}]: distinct cases below the four-of-five "
          "rule on at least one of the three measures ({})".format(
              src, ", ".join(rule_measures), ", ".join(below)))

    for cls, token in (("benign", "Benign"), ("V3", "VThree"), ("V4", "VFour"),
                       ("V5", "VFive"), ("V6", "VSix")):
        r = per_class[("actionability", cls)]
        m.add("dgAuditAct" + token, pct_of(r["share_pct"]),
              "{} share_pct [per_class / actionability / {}]: {} of {} "
              "judgements".format(src, cls, group(r["count"]),
                                  group(r["denom"])))
    r = per_class[("disposition", "V5")]
    m.add("dgAuditDispVFive", pct_of(r["share_pct"]),
          "{} share_pct [per_class / disposition / V5]: {} of {} votes on the "
          "ambiguity class match the suite's refer disposition".format(
              src, group(r["count"]), group(r["denom"])))

    # Unanimity by register.  Formal is ten, which house style writes as a
    # digit; the other two are below ten and are spelled out.
    formal = register[("disposition_unanimous", "formal")]
    m.add("dgAuditUnanFormal", group(formal["count"]),
          "{} count [register / disposition_unanimous / formal]: formal cases "
          "on which all {} reviewers chose the suite's disposition, of "
          "{}".format(src, reviewers, group(formal["denom"])))
    for reg, token in (("terse", "Terse"), ("conversational", "Conv")):
        r = register[("disposition_unanimous", reg)]
        m.add("dgAuditUnan" + token + "Word", int_word(int(r["count"])),
              "{} count [register / disposition_unanimous / {}]: {} of the {} "
              "{} cases drew a unanimous disposition vote, spelled out because "
              "house style writes a count below ten as a word".format(
                  src, reg, r["count"], r["denom"], reg))
    for reg, token in (("formal", "Formal"), ("terse", "Terse"),
                       ("conversational", "Conv")):
        r = register[("disposition_unanimous", reg)]
        m.add("dgAuditMean" + token, "{:.2f}".format(float(r["stat"])),
              "{} stat [register / disposition_unanimous / {}]: mean number of "
              "reviewers per case choosing the suite's disposition, of "
              "{}".format(src, reg, reviewers))

    non_unan = register[("disposition_nonunanimous", "ALL")]
    m.add("dgAuditNonUnan", group(non_unan["count"]),
          "{} count [register / disposition_nonunanimous / ALL]: cases on "
          "which at least one reviewer chose otherwise, of {}".format(
              src, group(non_unan["denom"])))
    for reg, token in (("conversational", "Conv"), ("terse", "Terse")):
        r = register[("disposition_nonunanimous", reg)]
        m.add("dgAuditNonUnan" + token + "Word", int_word(int(r["count"])),
              "{} count [register / disposition_nonunanimous / {}]: {} of the "
              "{} non-unanimous cases are {}; no formal case drew a split "
              "vote".format(src, reg, r["count"], non_unan["count"], reg))

    deffs = {name: float(overall[name]["deff"]) for name in overall}
    lo = min(deffs, key=lambda k: deffs[k])
    hi = max(deffs, key=lambda k: deffs[k])
    m.add("dgAuditDeffMin", num(deffs[lo], 2),
          "{} deff, minimum over the five overall rows (realism, disposition, "
          "fidelity, clarity, actionability); attained by {}".format(src, lo))
    m.add("dgAuditDeffMax", num(deffs[hi], 2),
          "{} deff, maximum over the same five rows; attained by {}. Both ends "
          "are below one, so the cases agree with each other slightly more "
          "than independent ratings would".format(src, hi))

    for vote, token in (("apply", "Apply"), ("reject", "Reject"),
                        ("refer", "Refer")):
        r = agreement["votes_" + vote]
        m.add("dgAuditVotes" + token, group(r["count"]),
              "{} count [agreement / votes_{}]: reviewer votes for {} over "
              "every case, of {}".format(src, vote, vote, group(r["denom"])))

    # The replicate count is stated in the table's own provenance header, which
    # the row reader strips, so it is read from the file text rather than
    # written down here.
    # (read straight from the path: read_text() and read_csv() share one cache
    # key per source, and the rows of this table are already cached above.)
    header = re.search(r"# ci_lo_pct .*?, (\d+) replicates",
                       SOURCES["DG13"].read_text())
    if header is None:
        raise LookupError_(
            "DG13: the provenance header carries no replicate count, so "
            "\\dgAuditBootReplicates has no source")
    m.add("dgAuditBootReplicates", group(header.group(1)),
          src + " provenance header, ci_lo_pct line: bootstrap replicates "
                "behind every interval in this group")
    m.add("dgAuditReviewersWord", int_word(reviewers),
          "{} denom [overall / realism] divided by denom [register / "
          "disposition_nonunanimous / ALL]: {} judgements over {} cases, the "
          "reviewers who rated every case".format(
              src, group(judgements), group(cases)))


def build_delta_baselines(m: Macros) -> None:
    """DG14: three hand-written delta rules against the certificate.

    An external reviewer (2026-08-18) asked what the certificate adds over
    the quality rule a scheduler would write by hand: refuse when the
    proposal worsens a reference schedule by more than a threshold.
    code/scripts/delta_baselines.py scores three such rules on the direct
    benchmark's 2,000 canonical proposals, reusing the logged schema and
    feasibility verdicts and swapping only the quality stage, and reads each
    rule at the setting most favourable to it whose benign false-block count
    does not exceed the certificate's 21.  The macros below are what the
    prose cites; the per-class matched-point table in Appendix E prints
    literals synced from the same CSV.

    The V3 endpoint macros deliberately span the three deployable rules and
    exclude the D-REL1-ORIG sensitivity, which mixes no field sets but is
    not the comparison a practitioner would run live; its numbers stay in
    the appendix table's note.
    """
    rows = read_csv("DG14")
    src = "analysis/DG14_delta_baselines.csv"
    RULES = ("D-REL1", "D-REL2", "D-ABS")
    matched = {(r["guard"], r["class"]): r for r in rows
               if r["block"] == "matched" and r["guard"] in RULES}
    cert = {r["class"]: r for r in rows if r["block"] == "certificate"}

    # The certificate rows must reproduce the published direct-benchmark
    # shares exactly, or every comparison this group states is off-ruler.
    assert pct_of(cert["V3"]["refused_share"]) == "91.4\\%", cert["V3"]
    assert pct_of(cert["benign"]["refused_share"]) == "2.6\\%", cert["benign"]
    cert_ben = int(cert["benign"]["refused"])
    assert all(int(matched[(g, "benign")]["refused"]) <= cert_ben
               for g in RULES), "a matched point exceeds the certificate's benign cost"
    assert all(int(matched[(g, "V5")]["refused"]) == 0 for g in RULES), \
        "a delta rule fired on an empty proposal"

    v3 = [float(matched[(g, "V3")]["refused_share"]) for g in RULES]
    viol = [float(matched[(g, "violations_all")]["refused_share"]) for g in RULES]
    m.add("dgDeltaVThreeMin", pct_of(min(v3)),
          src + ": lowest matched-point V3 refusal share over the three delta rules")
    m.add("dgDeltaVThreeMax", pct_of(max(v3)),
          src + ": highest matched-point V3 refusal share over the three delta rules")
    m.add("dgDeltaViolAllMin", pct_of(min(viol)),
          src + ": lowest matched-point all-violation refusal share over the three rules")
    m.add("dgDeltaViolAllMax", pct_of(max(viol)),
          src + ": highest matched-point all-violation refusal share over the three rules")
    m.add("dgDeltaCertViolAll", pct_of(cert["violations_all"]["refused_share"]),
          src + ": the certificate's all-violation refusal share on the same items")
    cert_v5 = int(cert["V5"]["refused"])
    assert cert_v5 == 7, cert_v5
    m.add("dgDeltaCertVFiveWord", int_word(cert_v5),
          src + ": V5 items the certificate refuses (a count below ten, in words)")

    # The two instances whose no-op schedule fails the tolerance: sum each
    # rule's benign refusals over both, and take the worst rule.
    focus_ben = {}
    for r in rows:
        if r["block"] == "focus_instance" and r["guard"] in RULES \
                and r["class"].startswith("benign@"):
            focus_ben[r["guard"]] = focus_ben.get(r["guard"], 0) + int(r["refused"])
    assert len(focus_ben) == 3 and max(focus_ben.values()) <= 2, focus_ben
    m.add("dgDeltaFocusBenignDeltaMax", str(max(focus_ben.values())),
          src + ": most benign refusals any delta rule draws on the two uncertifiable instances")

    # What each guard ACCEPTS on the two uncertifiable instances: the
    # focus_accepted block.  refused column = items accepted at the matched
    # setting; stat column = how many of those accepted schedules certify
    # above tau.  The three deployable rules accept 35-37 above-tolerance
    # schedules; the certificate accepts none.
    acc = {r["guard"]: r for r in rows if r["block"] == "focus_accepted"}
    pool = {int(acc[g]["items"]) for g in RULES} | {int(acc["G-CERT"]["items"])}
    assert pool == {50}, pool
    above = [int(acc[g]["stat"]) for g in RULES]
    assert int(acc["G-CERT"]["stat"]) == 0
    m.add("dgDeltaFocusQualItems", "50",
          src + ": quality-reaching items on the two uncertifiable instances")
    m.add("dgDeltaFocusAcceptAboveMin", str(min(above)),
          src + ": fewest above-tolerance schedules any deployable delta rule accepts there")
    m.add("dgDeltaFocusAcceptAboveMax", str(max(above)),
          src + ": most above-tolerance schedules any deployable delta rule accepts there")
    m.add("dgDeltaFocusCertAcceptedWord", int_word(int(acc["G-CERT"]["refused"])),
          src + ": items the certificate accepts on the two instances (none certifies above tau)")


def build_open(m: Macros) -> None:
    """Numbers the manuscript needs that no accepted artifact carries."""
    # "Open numbers" group retired 2026-08-14: \guardAddedLatencyMs was
    # measured by the Tier-1 slice, and \suiteExpertAuditAgreement was
    # DELETED by ruling (the audit is described neutrally and no agreement
    # rate was measured; decisions.md, exhibit-trim acceptance + the
    # neutral-audit-wording ruling of 2026-08-11).


# --------------------------------------------------------------------------
# Spelled-out companions of the small counts
#
# House style (decisions.md, the count-word ruling of 2026-08-17): a count
# below ten is written as a word when it is a count noun in running prose or in
# caption prose ("the eight arms", "three strata"), and as a digit everywhere
# else -- table cells, column heads, math, and any quantity carrying a unit or
# a decimal ("5 bh", "a 5-second bound", "tau = 0.15").  Prose therefore needs a
# word-valued companion for the count macros it uses as count nouns, and the
# word must come from the same source value as the digit, or the two can drift.
#
# Every macro below is minted by reading the ALREADY EMITTED body of its
# numeric parent, so the word and the digit cannot disagree: change the
# artifact, and both change together.  A parent whose value reaches ten is an
# error rather than a silent fallback, because "the 12 arms" is correct prose
# and a macro named ...Word that renders "12" is not.
# --------------------------------------------------------------------------

SMALL_INT_WORDS = {
    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four",
    5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine",
}


def int_word(n: int) -> str:
    """Spell a count below ten.  Ten and above is a hard error: see above."""
    if n not in SMALL_INT_WORDS:
        raise ValueError(
            "no spelled-out form for {}: house style writes a count of ten or "
            "more as a digit, so no ...Word companion may exist for it"
            .format(n))
    return SMALL_INT_WORDS[n]


#: (numeric macro, what it counts).  A macro earns a place here only if the
#: manuscript uses it as a count noun in prose; the second field names the noun
#: the prose attaches, so a later reader can check the companion is wanted.
#: Counts that are really measurements (\dgEThreeQualMarginTight, five weighted
#: business hours), multipliers (\eThreeBudgetRatio) or table-only cells (the
#: per-arm repeat counts of Appendix D's table) are deliberately absent.
COUNT_WORD_MACROS = (
    ("nEOneArms", "proposer arms"),
    ("nEOneEnforcedModels", "models whose endpoint enforces a schema"),
    ("nEOneRepeatsQwenFourteenB", "repeats of the Qwen arms"),
    ("nEOneRepeatsMini", "repeats of the GPT-5.4-mini and Sonnet arms"),
    ("nEOneRepeatsOpus", "repeats of the DeepSeek and Opus arms"),
    ("nSuiteStrata", "strata of the replayed corpus"),
    ("nEThreeArms", "arms that ran the agent-layer comparison"),
    ("nEThreeBudgetLevels", "budget levels of the agent-layer comparison"),
    ("dgEThreeArmsTotal", "arms carrying an end-task quality verdict"),
    ("dgEThreeQualEquivArms", "arms equivalent on end-task quality"),
    ("eThreeGuardTotalArms", "arms in the guard-effect comparison"),
    ("eThreeGuardSignificantArms", "arms with a Holm-significant difference"),
    ("eTwoTauGridSize", "tolerance values in the sweep"),
    ("eTwoOperatingTauArms", "arm configurations meeting the budget"),
    ("dgTauRuleArmsAgree", "arm configurations the cost rule agrees on"),
    ("dgTauRuleArmsTotal", "arm configurations reaching the budget"),
    ("dgNineCells", "arm configurations in the stratum split"),
    ("dgNineReplayCertOnlyZeroCells",
     "cells where the certificate stage adds no benign refusal"),
    ("dgBenignHotInstances", "instances whose no-AI anchor certifies above tau"),
    ("dgExposureItems", "instructions the two guard versions judged differently"),
    ("dgFreezeShiftBlocks", "refusals the freeze-and-shift family draws"),
    ("dgVFiveCanonicalRefused", "refused empty V5 proposals"),
    ("dgVThreeSubArms", "arms behind the pooled subclass shares"),
    ("dgRefusalConstrainedRows", "refusals under schema enforcement"),
    ("eOneOffShapeEnforcedArms", "enforced arm configurations"),
    ("costLocalArms", "arms that ran locally"),
)


def build_count_words(m: Macros) -> None:
    """Mint the ...Word companion of every count macro prose spells out."""
    emitted = {name: (body, comment)
               for _title, _note, items in m.groups
               for name, body, comment in items}

    m.group("Spelled-out small counts",
            "Word-valued companions of the counts prose writes as words "
            "(house style: a count below ten is a word when it is a count "
            "noun in a sentence, a digit in tables, math, and quantities "
            "carrying a unit). Each body is spelled from the value its "
            "numeric parent already emitted, so the two cannot drift, and a "
            "parent reaching ten is a generator error rather than a silent "
            "digit.")

    for name, noun in COUNT_WORD_MACROS:
        if name not in emitted:
            raise LookupError_(
                "count-word companion asked for \\{}, which no builder "
                "emits".format(name))
        body, comment = emitted[name]
        digits = body.replace("{,}", "").strip()
        if not re.fullmatch(r"[0-9]+", digits):
            raise LookupError_(
                "\\{} has body {!r}, which is not a plain count, so it cannot "
                "have a spelled-out companion".format(name, body))
        m.add(name + "Word", int_word(int(digits)),
              "spelled-out form of \\{} ({} {}); same source: {}".format(
                  name, body, noun, comment))


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

HEADER_MARK = "% generated "


def render(m: Macros, stamp: str) -> tuple:
    """Return (header, body) so the header's timestamp can be preserved."""
    head = [
        "% macros.tex -- every result-derived number the manuscript cites.",
        "%",
        "% GENERATED FILE. Do not edit by hand: rerun",
        "%   python code/scripts/paper_macros.py   (from the repository root)",
        "% Generator: code/scripts/paper_macros.py ({}).".format(VERSION),
        "%",
        "% CONVENTIONS",
        "%   * A percentage macro carries its own escaped per-cent sign, so "
        "prose writes",
        "%     \"\\eOneVThreeSepOpus\" and never \"\\eOneVThreeSepOpus\\%\".",
        "%   * Weighted business hours are unitless here: prose adds \" bh\".",
        "%   * Counts and money use LaTeX thousands separators ({,}).",
        "%   * Every macro is preceded by its source: file, column, and the row "
        "key.",
        "%   * A range macro's comment names the exact set of rows it minimises "
        "or",
        "%     maximises over. DeepSeek's constrained mode is JSON-object mode, "
        "not",
        "%     schema enforcement, so the capability ranges exclude it by name",
        "%     (analysis/consolidation_report.md, observation 4).",
        "%   * \\TODOnum bodies mark numbers no accepted artifact carries. The",
        "%     pre-submission gate requires zero of them.",
        HEADER_MARK + stamp,
    ]
    body = [
        "%",
        "% SOURCES (sha256 of the file read at generation time)",
    ]
    for key in sorted(SOURCES):
        body.append("%   {:<14} {}  {}".format(
            key, sha256_of(SOURCES[key]),
            str(SOURCES[key].relative_to(ROOT))))
    body.append("%")
    body.append("% {} macros in {} groups.".format(len(m), len(m.groups)))
    body.append("")

    for title, note, items in m.groups:
        body.append("% " + "=" * 72)
        body.append("% " + title.upper())
        if note:
            for line in _wrap(note, 72):
                body.append("% " + line)
        body.append("% " + "=" * 72)
        for name, value, comment in items:
            for line in _wrap(comment, 74):
                body.append("% " + line)
            body.append("\\newcommand{{\\{}}}{{{}}}".format(name, value))
        body.append("")
    return "\n".join(head), "\n".join(body).rstrip() + "\n"


def _wrap(text: str, width: int) -> list:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def build() -> Macros:
    m = Macros()
    build_suite(m)
    build_roster(m)
    build_e1(m)
    build_e2(m)
    build_e3(m)
    build_ladder(m)
    build_costs(m)
    build_local_compute(m)
    build_guard_latency(m)
    build_tiers(m)
    build_direct_guard(m)
    build_falseblock_decomposition(m)
    build_prevalence(m)
    build_tau_rule(m)
    build_e1_intervals(m)
    build_e3_intervals(m)
    build_passthrough(m)
    build_dg8(m)
    build_guard_version(m)
    build_prefix_ablation(m)
    # The five review-response groups of the 2026-08-17 revision are built
    # last, so that adding them leaves every earlier group's position in
    # macros.tex untouched and the regenerated file diffs as pure addition.
    build_dg10(m)
    build_stratum(m)
    build_v3_subclass(m)
    build_evidence_split(m)
    build_cert_tail(m)
    # The guard-fix audit is newer still (2026-08-17, the pass-through and
    # guard-disclosure revision), so it too is appended rather than inserted.
    build_guard_fix_audit(m)
    # The practitioner audit is the newest artifact of all (2026-08-17), so it
    # is appended too: no earlier group moves in the regenerated file.
    build_practitioner_audit(m)
    # DG14 (2026-08-18, external-review response) is newer still: appended so
    # no earlier group moves in the regenerated file.
    build_delta_baselines(m)
    build_open(m)
    # Last of all, because it reads the bodies the builders above emitted and
    # therefore has to run after every one of them. Being last also keeps the
    # regenerated file a pure addition: no earlier group moves.
    build_count_words(m)
    return m


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(DEFAULT_OUT),
                    help="output path (default: manuscript/macros.tex)")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the file would change; write nothing")
    args = ap.parse_args(argv)

    absent = missing_sources()
    if absent:
        for key, path in absent:
            print("MISSING SOURCE  {:<14} {}".format(key, path),
                  file=sys.stderr)
        return 2

    try:
        m = build()
    except LookupError_ as exc:
        print("SOURCE LOOKUP FAILED: {}".format(exc), file=sys.stderr)
        return 3

    out = Path(args.out)
    stamp = _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    head, body = render(m, stamp)

    # Idempotence: an unchanged body keeps the recorded generation time, so a
    # re-run with unchanged sources leaves the file byte-identical.
    if out.is_file():
        old = out.read_text()
        parts = old.split("\n", -1)
        old_stamp = next((ln[len(HEADER_MARK):] for ln in parts
                          if ln.startswith(HEADER_MARK)), None)
        idx = old.find(HEADER_MARK)
        if idx >= 0 and old_stamp is not None:
            old_body = old[old.find("\n", idx) + 1:]
            if old_body == body:
                head, stamp = render(m, old_stamp)[0], old_stamp

    text = head + "\n" + body
    if args.check:
        same = out.is_file() and out.read_text() == text
        print("macros.tex is {}".format("up to date" if same else "STALE"))
        return 0 if same else 1

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)

    print("wrote {} ({} macros in {} groups, generated {})".format(
        out, len(m), len(m.groups), stamp))
    for title, n in m.counts():
        print("  {:<52} {:>4}".format(title, n))
    if m.todos:
        print("\nTODO ({} macros have no accepted source):".format(len(m.todos)))
        for name, what, _ in m.todos:
            print("  \\{}: {}".format(name, what))
    else:
        print("\nTODO: none.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
