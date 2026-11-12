#!/usr/bin/env python
"""DG17: the end-to-end threshold-guard replay of the E1 model proposals.

WHY THIS EXISTS
---------------
DG14 asked whether a hand-written threshold on a reference schedule can stand
in for the optimality certificate, and answered it on the 2,000 CANONICAL
items of the direct benchmark, where the proposal is the suite's own
ground-truth (or fault) operation list and no model is in the loop.  The
reader's question is the harder one: what happens end to end, on the
proposals real models actually emitted, when the quality stage is a threshold
rule instead of the certificate?  This script answers it by re-adjudicating
every logged E1 proposal under alternative deterministic quality guards.  No
model is called; nothing is sampled; the model output is frozen.

THE FOUR LAUNCH ANSWERS (written before the run, per the house rule)
--------------------------------------------------------------------
1. PURPOSE.  One question: on the E1 logs, does a deterministic threshold on a
   reference schedule reach the certificate's separation on quality violations
   at the certificate's own benign false-block cost, and what does it cost and
   fail to deliver when it does?  The numbers land in the paper's
   delta-baseline defence (the DG14 paragraph and its table), extended from
   the canonical benchmark to the end-to-end evaluation, and in the reader
   response that asks for exactly this experiment.

2. IDEAL RESULT.  The honest outcome is whatever the logs say.  Two readings
   are prepared in advance so that neither can be chosen after the fact.  If
   the threshold rules match or beat the certificate's V3 separation at a
   held-out operating point, the paper cannot claim the certificate detects
   more damage than a hand-written rule, and the contribution must be carried
   by what the threshold rules structurally cannot do: they issue no bound on
   what they accept, they cannot fire on an empty proposal, and their accept
   decision is relative to a reference that may itself be far from what the
   instance admits.  If the threshold rules fall behind, the certificate's
   separation is the contribution and the composition is a free improvement.
   Both readings are written into the output; the data picks one.

3. CONTAMINATION.  Checked, and one real problem was found and fixed.
   (a) The instance files the E1 logs name, under
       PaperY-FMScheduling/data/processed/instances, were REGENERATED on
       2026-08-19, after the E1 evaluation (2026-08-16) and after DG14.  46 of
       the 60 instances this study uses now carry different content, and a
       no-op dispatch of the drifted file reproduces neither the suite's
       stored episode baseline nor the published ladder anchor.  Three
       untouched copies of the original data exist (instances_v10 in the same
       tree, and two copies under PaperY3).  This script therefore resolves
       every instance through a candidate list of roots and REFUSES TO RUN
       unless the chosen root reproduces all 116 published ladder anchors
       exactly.  The chosen root and the digests are recorded in the outputs.
   (b) No checkpoint, no device, no partially written result file: every input
       is a frozen log read read-only, and the two outputs are written once at
       the end after every assertion has passed.
   (c) No leakage in the threshold-selection policies: the primary reading
       selects each threshold on calibration rows only and evaluates it on
       held-out rows.  The in-sample reading is reported as an explicitly
       labelled upper bound, never as the headline.

4. DATA ACCURACY.  The population, the join keys and the metric definitions
   are the ones the published E1 analysis already uses, and each is asserted
   rather than assumed: the verdict logs and the proposal log are joined 1:1
   on (mode, thinking, repeat, item_id); the published per-cell V3 separation,
   V3 feasibility-block, and benign false-block shares are recomputed from the
   raw logs and compared with manuscript/macros.tex; the damage term is
   compared with analysis/T5_ladder.csv; the delta-rule arithmetic is
   round-tripped against code/scripts/delta_baselines.py's own functions on
   canonical items whose objectives are asserted equal to the published direct
   benchmark's.

THE DECLARED DESIGN (declared before any result was computed)
-------------------------------------------------------------
POPULATION.  Constrained mode only (``M_constrained``), repeats pooled, which
is the scope of every published E1 rate.  40,000 rows over ten cells
(arm, thinking).  Rows are kept in their denominators whatever their terminal,
including the four Opus rows the model refused: under the E1 convention a
refusal is neither applied nor blocked, so it sits in the denominator only
(code/scripts/e1_intervals.py, e3_replay.py).  A row is eligible under a
configuration when it carries no instrument fault under it; measured on these
logs the filter removes nothing (zero infra rows).

The PRIMARY population is the eight capability cells over the seven
schema-enforced arms.  DeepSeek's constrained mode is JSON-object mode, which
enforces no schema, so the manuscript excludes its two cells from every
capability reading (analysis/consolidation_report.md observation 4;
the decision record 2026-08-13 ruling 2; code/scripts/paper_macros.py
CAPABILITY_ROWS).  This script follows that convention: the DeepSeek cells are
computed, written, and flagged ``in_capability_set = False``.

WHAT A DELTA RULE REPLACES.  The quality stage only, exactly as in DG14.  The
schema and feasibility stages are the guard's, they are cheap, and no
threshold on a schedule can reproduce them: an operation list that does not
parse never produces a schedule to score.  Every configuration below therefore
reuses the LOGGED G_FEAS schema and feasibility verdicts unchanged, and the
rules act only on the rows that reach the quality stage.  On these logs
{G_FEAS applies} and {G_CERT carries a certified gap} are the same 29,980
rows, which is asserted.

GUARD CONFIGURATIONS.

  G-FEAS                the logged feasibility guard: schema and feasibility
                        gate, no quality stage.
  G-CERT                the deployed guard, at the frozen tau = 0.20, taken
                        verbatim from the logged verdicts.
  G-FEAS+D-REL1         schema and feasibility from the log, then refuse iff
                        (WT_prop - WT_ref1) / max(WT_ref1, 1) > theta
  G-FEAS+D-REL2         ... > theta, against WT_ref2
  G-FEAS+D-ABS          ... refuse iff WT_prop - WT_ref1 > A business hours
  G-FEAS+D-BEST         the same, with the rule itself chosen per fold on the
                        calibration rows (never on the held-out rows)
  G-CERT+D-REL1 ...     the composition: refuse iff EITHER the certificate at
  G-CERT+D-BEST         tau = 0.20 refuses OR the threshold rule refuses,
                        with the rule at the SAME per-fold setting as its own
                        G-FEAS+rule row (the composition never re-tightens
                        the rule under a certificate-inclusive budget)

WT_prop is the weighted tardiness of the schedule the logged proposal actually
produced, scored on the fields the proposal installed: the guard's own
``certificate.obj_bh``, recomputed here and asserted equal.  WT_ref1 is the
no-op reference, the unadjusted instance dispatched with the same rule, seed
and standing frozen set (analysis/ladder/rule_anchor.csv).  WT_ref2 is the
counterfactual reference, the same adjusted fields dispatched with the
proposal's added dispatch constraints removed; it is recomputed here from the
LOGGED ``parsed_ops`` (DG14 computes it from the suite's canonical field).
Every weighted-tardiness difference is rounded to 6 decimals in business hours
before it is thresholded, and the ratio carries the certificate's own
``max(., 1)`` floor: both conventions are copied from DG14 so the two analyses
cannot drift apart.

THRESHOLD OPERATING-POINT POLICIES.  All three are reported, each labelled.

  (a) HELD-OUT MATCHED FALSE BLOCK  *primary*
      Two fold structures, both reported: leave-one-stratum-out (3 folds, the
      three instance strata) and grouped 5-fold over the 60 instances at a
      fixed seed.  Within one cell and one fold, the threshold is the TIGHTEST
      setting whose benign false-block rate on the CALIBRATION rows does not
      exceed the certificate's benign false-block rate on the same calibration
      rows.  It is then applied to the held-out rows, and the held-out results
      of all folds are pooled.  "Tightest" is the paper's own operating-point
      convention (code/scripts/tau_cost_rule.py::operating_point_fb).
  (b) FIXED 5% BENIGN FALSE-BLOCK BUDGET
      The same fold structures and the same selection rule, with the budget
      fixed at 0.05, which is the convention the manuscript's Table 8 prints.
      A cell whose schema-and-feasibility floor already exceeds 5% has no
      feasible setting; the fold then takes the no-quality-gate setting and is
      flagged.
  (c) IN-SAMPLE MOST FAVOURABLE  *upper bound, labelled as such*
      DG14's own reading, reproduced cell by cell: over the whole cell, the
      setting whose benign false-block COUNT does not exceed the certificate's
      on the same rows, maximising V3 separations, ties to higher overall
      violation blocking, then fewer benign false blocks, then the widest
      setting.  It is the number a rule can reach when it is allowed to see
      the test set, and it is reported for continuity with the direct-benchmark
      table, never as the headline.  Two variants are written: over DG14's grid
      (which reproduces the published DG14 settings exactly) and over every
      threshold the data realises (DG14's own unrestricted diagnostic).

CANDIDATE SETTINGS.  A threshold rule only changes its answer at a value the
data realises, so the exact candidate set is DG14's grids (50 tolerances from
0.02 to 1.00, 20 log-spaced absolute tolerances from 0.5 to 50 bh) TOGETHER
WITH the realised quantities themselves, computed on the calibration rows only.
Using the grid alone would misreport two rules in opposite directions: D-REL2
selects the grid's tightest value in almost every fold, so its separation would
be under-read, and D-REL1 falls off the grid's widest value, so it would be
handicapped by where the grid stops.  Negative thresholds are excluded, as in
DG14, because a rule that refuses a proposal for improving the schedule is not
one anybody would write.  The widest candidate is "never refuse", which reduces
a configuration to its base and is what makes the selection always feasible.

METRICS, all with the definitions the published analysis uses.

  v3_separation                    over ALL V3 rows: G_FEAS applies and the
                                   configuration blocks (e1_intervals.py)
  v4qv_separation                  the same over the V4 rows the suite flags
                                   ``quality_visible_candidate``
  benign_false_block               over benign rows: the configuration blocks
  violation_pass_through           over non-benign rows: the configuration
                                   applies (a refusal is neither passed nor
                                   blocked, so it is in the denominator only)
  violation_pass_through_nonempty  the same, applied with a non-empty list
  violation_pass_through_strict    the published content rule: an applied V4
                                   or V6 row counts unless the applied
                                   operations are exactly the item's non-empty
                                   gold_ops (code/scripts/passthrough_rule.py)
  mean_excess_bh                   executed-schedule damage against the no-AI
                                   anchor, in weighted business hours per
                                   instruction: executed minus anchor, where
                                   executed is the guard-recorded
                                   ``wwt_original_bh`` when the instruction is
                                   applied and the anchor otherwise, because a
                                   blocked, referred or refused instruction
                                   leaves the baseline schedule standing
                                   (ladder_replay.py::arm_entries,
                                   tau_cost_rule.py::point_at)
  accepted_above_tau               over the rows a configuration APPLIES: the
                                   share whose own executed schedule certifies
                                   at a gap above tau = 0.20
  certificate_availability         over the rows a configuration APPLIES: the
                                   share carrying a certified bound.  Zero for
                                   every threshold rule by construction
  extra_dispatch_per_instruction   the cost channel: extra reference dispatches
                                   the rule needs per instruction, uncached and
                                   with the per-instance reference cached

HOW THE SUITE WAS BUILT, AND WHY IT BOUNDS THE V3 READING.  Measured here from
the suite file rather than quoted, and written to the output as its own block.
``l1suite/checks.py::measure`` records ``badness_relative = (WWT_adjusted -
WWT_adjusted_reference) / max(WWT_adjusted_reference, 1)``, which is exactly
the quantity D-REL2 thresholds, computed on the item's canonical operation
list.  ``l1suite/templates.py`` sets ``requires_positive_badness = True`` on
all five V3 families and ``l1suite/generate.py`` redraws a V3 candidate until
that quantity is strictly positive.  The certificate's tolerance is used
nowhere in the suite build.  D-REL2's separation on V3 is therefore partly a
construction artifact, and the output says so beside every number that depends
on it.  The comparisons that do not have this property are the benign false
block, the executed-schedule damage, the availability of a bound on accept, and
the share of accepts whose own schedule certifies above tau.

95% cluster-bootstrap percentile intervals over the 60 instances, B = 20,000,
one index matrix per cell reused across that cell's configurations so the
intervals are paired within a cell (e1_intervals.py::cluster_bootstrap).

WHAT IS ASSERTED BEFORE ANY NEW NUMBER IS COMPUTED
--------------------------------------------------
  * the resolved instance root reproduces all 116 published ladder anchors
    exactly; the root the logs name is checked first and is REJECTED if it
    does not;
  * the published per-cell E1 cells, recomputed from the raw logs and compared
    with manuscript/macros.tex through ``delta_baselines.macro_value``:
    V3 separation share and count, V3 block rate under G_FEAS, and benign
    false block under both G_CERT and G_FEAS, for all ten cells;
  * every recomputed objective equals the logged one, on all 29,980
    quality-reaching E1 rows and on all 1,635 quality-reaching canonical items
    of the direct benchmark;
  * the delta-rule arithmetic against ``delta_baselines``' own functions:
    100 canonical items, every guard, every setting on the grid, comparing
    ``_compute_delta`` and ``refuses`` value by value, and the in-sample
    favourable selection against ``delta_baselines.matched_point`` on the full
    2,000-item canonical population, whose settings are compared with the
    published analysis/DG14_delta_baselines.csv;
  * the damage term against analysis/T5_ladder.csv: at tau = 0.20 the mean
    excess reproduces the published G-CERT ``wwt_original_vs_rule_bh`` for
    every cell, and the mean anchor reproduces the published RULE row;
  * applied zero-operation rows carry the anchor objective exactly;
  * refusal counts are monotone in every threshold.

Any failure prints every failing assertion and exits 2.  No number is ever
adjusted to make a check pass.

DETERMINISM
-----------
Nothing samples except the bootstrap, whose generator is seeded from a fixed
constant and the cell name.  The dispatcher is deterministic at (rule, seed)
taken from each logged row and asserted to be (atc, 0) throughout.  The grids
are literals and every tie-break is a total order.

CPU ONLY.  No model call of any kind.  The only real work is 3,142 distinct
apply+dispatch units for the E1 references and 1,635 for the canonical
round-trip; each worker forces its thread pools to one and is pinned with
``os.sched_setaffinity``.

OUTPUTS
-------
``analysis/DG17_e2e_delta.csv``  one row per cell x configuration x policy,
                                 with every metric and its interval, plus the
                                 per-fold selected thresholds and the in-sample
                                 sweeps
``analysis/DG17_e2e_delta.md``   the design, the definitions, the headline
                                 reading and the caveats

Run::

    conda run -n fjsp python code/scripts/e1_delta_guard_replay.py

Version: l1-dg17-e2e-delta-1
"""

from __future__ import annotations

import os

# Thread caps before any numeric import: every numerical runtime sizes its pool
# from the machine's core count, not from this process's share of it, so two
# jobs pinned to the same cores would otherwise spawn one thread per core on
# the whole box and fight.
for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
             "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_var] = "1"

import argparse  # noqa: E402
import csv  # noqa: E402
import datetime as _dt  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from collections import Counter, OrderedDict, defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

VERSION = "l1-dg17-e2e-delta-1"

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent.parent
CODE = ROOT / "code"
RESULTS = ROOT / "results"
ANALYSIS = ROOT / "analysis"
LADDER = ANALYSIS / "ladder"
MANUSCRIPT = ROOT / "manuscript"
SUITE_PATH = CODE / "suite" / "v0.2" / "suite.jsonl"

for _p in (str(CODE), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import delta_baselines as db  # noqa: E402  (the DG14 rules, one source)
import passthrough_rule as pr  # noqa: E402  (the V4/V6 content rule, one source)

# --------------------------------------------------------------------------- #
# Declared constants                                                           #
# --------------------------------------------------------------------------- #

#: The bootstrap is the only thing in this file that draws.
SEED = 20260823
B_BOOT = 20_000
ALPHA = 0.05

#: The published operating point of the certificate, and its floor.  Both are
#: DG14's, restated here only so this file can be read on its own; the values
#: are asserted equal to delta_baselines' at import.
TAU_PUBLISHED = 0.20
FLOOR_BH = 1.0
ROUND_BH = 6

#: The budget the manuscript's Table 8 prints its operating point from.
FB_BUDGET_FIXED = 0.05

#: The scope of every published E1 rate.
MODE = "M_constrained"

#: Terminal vocabulary (code/scripts/suite_gate.py, e1_evaluate.py).
APPLIED_STATES = ("applied_with_certificate", "applied_uncertified")
BLOCKED_STATES = ("blocked_schema", "blocked_feas", "blocked_qual")
PRE_QUAL_BLOCKS = ("blocked_schema", "blocked_feas")
BENIGN = "benign"

#: The three dispositions a configuration can reach on a row.
APPLIED, BLOCKED, OTHER = 0, 1, 2

#: The episode every E1 row declares, asserted rather than assumed.
EPISODE_RULE = "atc"
EPISODE_SEED = 0

#: Operations that constrain the dispatcher (l1suite/checks.py).  A proposal
#: with none of them only edits fields, so the counterfactual reference is the
#: objective itself and D-REL2 cannot separate it.
CONSTRAINING_OPS = frozenset({"pin_next", "reorder", "freeze", "unfreeze",
                              "batch"})

ARM_DIRS = OrderedDict([
    ("qwen3-14b", "e1_eval_qwen14b"),
    ("qwen3.6-27b-fp8", "e1_eval_qwen27b"),
    ("glm-4-9b", "e1_eval_glm9b"),
    ("openai", "e1_eval_gpt54mini"),
    ("deepseek", "e1_eval_deepseek"),
    ("sonnet", "e1_eval_sonnet5"),
    ("opus", "e1_eval_opus5"),
    ("sol", "e1_eval_sol"),
])

MODEL_LABEL = {
    "qwen3-14b": "Qwen3-14B (open, local, BF16)",
    "qwen3.6-27b-fp8": "Qwen3.6-27B-FP8 (open, local, quantized)",
    "glm-4-9b": "GLM-4-9B (open, local, SPOT-CHECK)",
    "openai": "GPT-5.4-mini (closed, budget tier)",
    "deepseek": "DeepSeek V4-Pro (open weights, hosted)",
    "sonnet": "Claude Sonnet 5 (closed)",
    "opus": "Claude Opus 5 (closed, flagship)",
    "sol": "GPT-5.6 Sol (closed, flagship spot-check)",
}

#: The manuscript's capability set: the constrained cells minus DeepSeek's two.
CAPABILITY_SET = (
    ("qwen3-14b", "-"), ("qwen3.6-27b-fp8", "-"), ("glm-4-9b", "-"),
    ("openai", "-"), ("sonnet", "disabled"), ("opus", "default"),
    ("opus", "disabled"), ("sol", "none"),
)

#: (arm, thinking) -> the macro-name token paper_macros.py builds.  Transcribed
#: from code/scripts/paper_macros.py ARM_TOKEN + thinking_suffix so the macro
#: assertions below name real macros.
CELL_TOKEN = OrderedDict([
    (("qwen3-14b", "-"), "QwenFourteenB"),
    (("qwen3.6-27b-fp8", "-"), "QwenTwentySevenB"),
    (("glm-4-9b", "-"), "Glm"),
    (("openai", "-"), "Mini"),
    (("deepseek", "non_think"), "Deepseek"),
    (("deepseek", "think_high"), "DeepseekThinkHigh"),
    (("sonnet", "disabled"), "Sonnet"),
    (("opus", "default"), "Opus"),
    (("opus", "disabled"), "OpusDisabled"),
    (("sol", "none"), "Sol"),
])

#: The instance roots tried, in order.  The first entry is the root the logs
#: name; it is checked and not trusted, because that tree was regenerated after
#: the E1 run.  The remaining entries are untouched copies of the data the run
#: used.  The first root reproducing all published anchors exactly is used.
#: The root written into every logged ``instance_path``.  Overridable with
#: ``L1_LOGGED_INSTANCE_ROOT`` so a checkout elsewhere can rewrite the prefix.
INSTANCE_ROOT_LOGGED = os.environ.get(
    "L1_LOGGED_INSTANCE_ROOT",
    "${L1_Y1_ROOT}/data/processed/instances")

#: The candidate roots, in order.  ``L1_INSTANCE_ROOTS`` (colon-separated) or
#: ``--instance-roots`` replaces the list; ``--instance-root`` pins one.
INSTANCE_ROOTS = tuple(
    p for p in os.environ.get("L1_INSTANCE_ROOTS", ":".join([
        INSTANCE_ROOT_LOGGED,
        ((os.environ.get("L1_Y1_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "PaperY-FMScheduling")) + "/data/processed/instances_v10"),
    ])).split(":") if p)

#: The rules and their grids, taken from DG14 rather than restated.
RULES = ("D-REL1", "D-REL2", "D-ABS")
RULE_KIND = {"D-REL1": "theta", "D-REL2": "theta", "D-ABS": "A_bh"}
NEVER = float("inf")            # the "no quality gate" setting

#: Fold structures.  Both are reported for the two held-out policies.
FOLD_SCHEMES = ("loso", "gkf5")
N_GKF = 5

#: The policies, in report order.  ``family`` groups the two fold structures.
POLICIES = OrderedDict([
    ("heldout_matched_loso", ("matched_heldout", "loso", "cert")),
    ("heldout_matched_gkf5", ("matched_heldout", "gkf5", "cert")),
    ("heldout_budget5_loso", ("budget5_heldout", "loso", "fixed")),
    ("heldout_budget5_gkf5", ("budget5_heldout", "gkf5", "fixed")),
    ("insample_favourable_grid", ("insample_upper_bound", "none", "cert")),
    ("insample_favourable_continuum", ("insample_upper_bound", "none", "cert")),
])

#: The in-sample policy read over every threshold the data realises rather than
#: over DG14's grid.  Its grid twin exists so the published DG14 table can be
#: reproduced exactly; this one exists so the upper bound is not an artifact of
#: where the grid stops.
CONTINUUM_POLICY = "insample_favourable_continuum"
PRIMARY_POLICY = "heldout_matched_loso"

#: The configurations, in report order.  ``base`` is the stage-1/2 source and
#: whether the certificate also votes; ``rule`` is None for the two logged
#: configurations.
CONFIGS = OrderedDict()
CONFIGS["G-FEAS"] = ("feas", None)
CONFIGS["G-CERT"] = ("cert", None)
for _r in RULES + ("D-BEST",):
    CONFIGS["G-FEAS+" + _r] = ("feas", _r)
for _r in RULES + ("D-BEST",):
    CONFIGS["G-CERT+" + _r] = ("cert", _r)

#: Configurations whose accept decision carries a certified bound.
BOUND_CONFIGS = frozenset(name for name, (base, _rule) in CONFIGS.items()
                          if base == "cert")

#: The metrics carrying a cluster-bootstrap interval.
CI_METRICS = ("v3_separation", "v4qv_separation", "benign_false_block",
              "violation_pass_through", "violation_pass_through_nonempty",
              "violation_pass_through_strict", "mean_excess_bh",
              "accepted_above_tau")

#: Every metric written, in column order.
METRIC_ORDER = CI_METRICS + ("certificate_availability", "block_rate")


# --------------------------------------------------------------------------- #
# Small helpers                                                                #
# --------------------------------------------------------------------------- #
def refuse(msg):
    raise SystemExit("REFUSING TO RUN: " + msg)


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path):
    out = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def read_csv_skipping_comments(path):
    with open(path, "r", encoding="utf-8") as fh:
        lines = [ln for ln in fh if not ln.startswith("#")]
    return list(csv.DictReader(lines))


def thinking_label(value):
    return "-" if value is None else str(value)


def frozen_key(frozen_seed):
    return ",".join(str(x) for x in (frozen_seed or ()))


def pct(x, digits=1):
    return "" if x is None else "{:.{d}f}".format(100.0 * x, d=digits)


def num(x, spec="{:.6f}"):
    return "" if x is None else spec.format(x)


def setting_label(rule, setting):
    if rule is None:
        return ""
    if setting is None:
        return ""
    if setting == NEVER:
        return "never"
    return "{:.6g}".format(setting)


def group(n) -> str:
    """Integer with the LaTeX thousands separator paper_macros.py writes."""
    s = "{:d}".format(int(round(float(n))))
    sign, s = ("-", s[1:]) if s.startswith("-") else ("", s)
    parts = []
    while len(s) > 3:
        parts.insert(0, s[-3:])
        s = s[:-3]
    parts.insert(0, s)
    return sign + "{,}".join(parts)


class Checker:
    """Every assertion, recorded rather than raised, so one failure hides none."""

    def __init__(self):
        self.n = 0
        self.failures = []

    def eq(self, what, expected, got, rtol=None):
        self.n += 1
        if rtol is not None and isinstance(expected, float) \
                and isinstance(got, float):
            ok = abs(expected - got) <= rtol * max(1.0, abs(expected))
        else:
            ok = expected == got
        if not ok:
            self.failures.append("{}: expected {!r}, got {!r}".format(
                what, expected, got))

    def true(self, what, value):
        self.eq(what, True, bool(value))


# --------------------------------------------------------------------------- #
# Inputs                                                                       #
# --------------------------------------------------------------------------- #
def load_anchors(check):
    """(instance_id, frozen set) -> the no-AI anchor in bh, with its cross-checks.

    Read from rule_anchor.json, cross-checked against rule_anchor.csv exactly as
    tau_cost_rule.load_anchors does, and additionally checked for the property
    delta_baselines.load_anchor relies on: a frozen-set anchor carries the same
    weighted tardiness as the plain one on the same instance, so joining on the
    instance alone and joining on (instance, frozen set) cannot disagree.
    """
    records = json.loads((LADDER / "rule_anchor.json").read_text())
    by_key, by_instance_plain, frozen_seen = {}, {}, defaultdict(list)
    for rec in records:
        iid = Path(rec["instance_path"]).stem
        fk = frozen_key(rec["frozen_seed"])
        by_key[(iid, fk)] = rec
        check.eq("anchor {} is a zero-operation baseline".format((iid, fk)),
                 0, rec["n_ops"])
        check.eq("anchor {} original equals adjusted".format((iid, fk)),
                 float(rec["wwt_adjusted_bh"]), float(rec["wwt_original_bh"]),
                 rtol=1e-12)
        if fk == "":
            by_instance_plain[iid] = float(rec["wwt_original_bh"])
        else:
            frozen_seen[iid].append(float(rec["wwt_original_bh"]))

    for row in read_csv_skipping_comments(LADDER / "rule_anchor.csv"):
        fk = "" if row["frozen_seed"] == "-" else row["frozen_seed"].replace("|", ",")
        rec = by_key[(row["instance_id"], fk)]
        check.eq("rule_anchor.csv wwt_bh equals the json objective for {}"
                 .format(row["instance_id"]), float(row["wwt_bh"]),
                 float(rec["wwt_original_bh"]), rtol=1e-9)

    # The property delta_baselines.load_anchor relies on: a frozen-set anchor
    # carries the same weighted tardiness as the plain one, so joining on the
    # instance alone and joining on (instance, frozen set) cannot disagree.
    drift = [iid for iid, values in frozen_seen.items()
             for v in values if abs(v - by_instance_plain[iid]) > 1e-9]
    check.eq("instances whose frozen-set anchor differs from the plain one",
             [], sorted(set(drift)))

    return ({k: float(v["wwt_original_bh"]) for k, v in by_key.items()},
            {k: v["instance_path"] for k, v in by_key.items()},
            {k: float(v["gap"]) for k, v in by_key.items()})


def resolve_instance_root(anchor_paths, anchors, workers, cores, check):
    """The first candidate root whose no-op dispatch reproduces every anchor.

    The root the logs name is a candidate like any other and is rejected when
    it fails: the upstream instance tree was regenerated after this study's
    logs were written, and silently dispatching the new files would produce a
    publishable-looking number from data the run never saw.
    """
    tried = []
    for root in INSTANCE_ROOTS:
        tasks = []
        ok_paths = True
        for (iid, fk), path in anchor_paths.items():
            candidate = str(path).replace(INSTANCE_ROOT_LOGGED, root)
            if not Path(candidate).is_file():
                ok_paths = False
                break
            frozen = tuple(fk.split(",")) if fk else ()
            tasks.append(((iid, fk), candidate, frozen))
        if not ok_paths:
            tried.append((root, "missing files"))
            continue
        got = _run_units([_anchor_unit(t) for t in tasks], workers, cores,
                         kind="anchor")
        bad = [key for key in anchors
               if key not in got or abs(got[key] - anchors[key]) > 1e-6]
        if bad:
            tried.append((root, "{} of {} anchors differ".format(
                len(bad), len(tasks))))
            continue
        tried.append((root, "reproduces all {} anchors".format(len(tasks))))
        check.eq("instance root reproduces every published ladder anchor",
                 0, len(bad))
        return root, tried
    refuse("no candidate instance root reproduces the published ladder "
           "anchors; the logs' own root has drifted and no untouched copy was "
           "found. Tried: " + "; ".join("{} ({})".format(r, why)
                                        for r, why in tried))


def _anchor_unit(task):
    key, path, frozen = task
    return {"kind": "anchor", "key": key, "path": path,
            "frozen": list(frozen), "ops": []}


# --------------------------------------------------------------------------- #
# The replay workers                                                           #
# --------------------------------------------------------------------------- #
_STATE = {}


def _init(cores):
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                "NUMEXPR_NUM_THREADS"):
        os.environ[var] = "1"
    if cores:
        try:
            os.sched_setaffinity(0, set(cores))
        except (AttributeError, OSError):
            pass
    from l1guard.replay import InstanceCache

    _STATE["cache"] = InstanceCache()


def _measure_unit(unit):
    """Objective and both references for one (instance, frozen set, op list).

    This is ``l1suite/checks.py::measure`` reproduced call for call, which is
    also what ``delta_baselines._measure_one`` does, with the operation list
    taken from the LOG rather than from the suite's canonical field.  The
    baseline schedule is always supplied, so a proposal carrying a freeze or an
    instance carrying a standing frozen set behaves exactly as the guard's own
    replay path does.
    """
    from l1adapter import apply as apply_mod, dispatch as dispatch_mod, evaluate

    cache = _STATE["cache"]
    path = unit["path"]
    instance = cache.instance(path)
    frozen = list(unit["frozen"])
    ops = list(unit["ops"])
    # The baseline is always supplied, as delta_baselines._measure_one does.
    # The guard's own replay path computes it only when a freeze or a standing
    # frozen set can need it, and an operation that needs one without having
    # one raises MissingBaseline, which blocks the row at the feasibility stage
    # and keeps it out of this population entirely.  Supplying it therefore
    # cannot change a verdict, and the objective assertion below proves it.
    baseline = cache.baseline(path, EPISODE_RULE, EPISODE_SEED)

    try:
        adjusted = apply_mod.apply_proposal(
            instance, {"operations": ops}, frozen_seed=frozen,
            baseline_schedule=baseline, strict_schema=True)
        schedule = dispatch_mod.dispatch_adjusted(adjusted, EPISODE_RULE,
                                                  EPISODE_SEED)
        obj_adjusted = evaluate.wwt(adjusted, schedule)
        obj_original = evaluate.wwt(adjusted.original, schedule)
    except Exception as exc:  # noqa: BLE001 - the message must survive pickling
        return {"key": unit["key"], "error": "{}: {}".format(
            type(exc).__name__, exc)}

    if unit["kind"] == "anchor":
        return {"key": unit["key"], "wwt": obj_adjusted}

    if any(o.get("op") in CONSTRAINING_OPS for o in ops):
        # Removing the proposal's dispatch constraints can leave a counterfactual
        # that does not exist: a proposal whose only constraining operation is an
        # ``unfreeze`` of a standing frozen order, taken together with a window
        # shift on that same order, has no "same fields, constraints removed"
        # schedule, because reinstating the freeze contradicts the shifted
        # release.  That is a property of the RULE, not an instrument fault, so
        # it is recorded and the rule is given no delta on those rows rather than
        # a fabricated one.
        try:
            ref_adjusted = apply_mod.apply_operations(
                adjusted.instance, [], frozen_seed=frozen,
                baseline_schedule=baseline)
            ref_schedule = dispatch_mod.dispatch_adjusted(
                ref_adjusted, EPISODE_RULE, EPISODE_SEED)
            reference = evaluate.wwt(ref_adjusted, ref_schedule)
            reference_from = "dispatched"
        except Exception as exc:  # noqa: BLE001 - see the comment above
            reference = None
            reference_from = "unavailable:" + type(exc).__name__
    else:
        reference = obj_adjusted
        reference_from = "identical_by_construction"

    return {"key": unit["key"], "obj_adjusted": obj_adjusted,
            "obj_original": obj_original, "ref2": reference,
            "reference_from": reference_from}


def _chunk(units):
    return [_measure_unit(u) for u in units]


def _run_units(units, workers, cores, kind="unit"):
    """Instance-grouped chunking so a worker loads each instance once."""
    import multiprocessing as mp

    groups = defaultdict(list)
    for u in units:
        groups[u["path"]].append(u)
    chunks = sorted(groups.values(), key=len, reverse=True)

    out = []
    if workers <= 1:
        _init(cores)
        for ch in chunks:
            out.extend(_chunk(ch))
    else:
        ctx = mp.get_context("fork")
        with ctx.Pool(workers, initializer=_init, initargs=(cores,)) as pool:
            for res in pool.imap_unordered(_chunk, chunks):
                out.extend(res)
    if len(out) != len(units):
        refuse("{} {} measurements returned for {} units".format(
            len(out), kind, len(units)))
    failed = [r for r in out if "error" in r]
    if failed:
        if kind == "anchor":
            return {}
        refuse("{} {} units could not be replayed at all, though the log "
               "records them reaching the quality stage; first three: {}"
               .format(len(failed), kind,
                       "; ".join("{} -> {}".format(r["key"], r["error"])
                                 for r in failed[:3])))
    if kind == "anchor":
        return {r["key"]: r["wwt"] for r in out}
    return {r["key"]: r for r in out}


# --------------------------------------------------------------------------- #
# The E1 rows                                                                  #
# --------------------------------------------------------------------------- #
def load_cell_rows(arm, dirname, anchors, anchor_gaps, suite_ops,
                   instance_root, check):
    """One list of merged rows per arm, joined 1:1 across the three logs."""
    eval_dir = RESULTS / dirname
    proposals = {}
    for rec in read_jsonl(eval_dir / "proposals.jsonl"):
        if rec["mode"] != MODE:
            continue
        extra = rec.get("extra") or {}
        key = (rec["mode"], thinking_label(extra.get("thinking")),
               extra.get("repeat"), rec["instruction_id"])
        if key in proposals:
            refuse("{} has two proposal rows for {}".format(eval_dir, key))
        proposals[key] = rec

    verdicts = {}
    for config in ("G_CERT", "G_FEAS"):
        table = {}
        for row in read_jsonl(eval_dir / "verdicts_{}.jsonl".format(config)):
            if row["mode"] != MODE:
                continue
            key = (row["mode"], thinking_label(row["thinking"]), row["repeat"],
                   row["item_id"])
            if key in table:
                refuse("{} verdicts_{} has two rows for {}".format(
                    eval_dir, config, key))
            table[key] = row
        if set(table) != set(proposals):
            refuse("{} verdicts_{} covers {} keys and proposals.jsonl covers "
                   "{}".format(eval_dir, config, len(table), len(proposals)))
        verdicts[config] = table

    rows = []
    for key in sorted(proposals):
        prop = proposals[key]
        cert = verdicts["G_CERT"][key]
        feas = verdicts["G_FEAS"][key]
        for field in ("instance_id", "primary_class", "subclass", "stratum"):
            if cert[field] != feas[field]:
                refuse("{} disagrees on {} for {}".format(arm, field, key))
        check.eq("{} row {} declares the episode the references use"
                 .format(arm, key),
                 (EPISODE_RULE, EPISODE_SEED),
                 (prop.get("rule"), (prop.get("seeds") or {}).get("dispatch")))

        akey = (prop["instance_id"], frozen_key(prop.get("frozen_seed")))
        if akey not in anchors:
            refuse("no no-AI anchor for {}; a blocked instruction cannot be "
                   "priced".format(akey))

        verdict = prop.get("verdict") or {}
        objective = verdict.get("objective") or {}
        certificate = prop.get("certificate") or {}
        n_ops = cert.get("n_ops") or 0
        ops = prop.get("parsed_ops")
        feas_applied = feas["terminal"] in APPLIED_STATES
        has_gap = cert.get("certificate_gap") is not None
        if feas_applied != has_gap:
            refuse("{} {}: G_FEAS applies but no certified gap is logged (or "
                   "the reverse); the delta rules act on exactly the rows the "
                   "quality stage sees".format(arm, key))

        extra = prop.get("extra") or {}
        lists = suite_ops.get(cert["item_id"], {})
        applied_ops = pr.applied_ops(ops, n_ops)
        strict_flag = pr.counts_as_pass_through(
            cert["primary_class"], True, applied_ops, lists.get("gold_ops"),
            lists.get("trap_ops"), lists.get("forbidden_ops"), strict=True)

        path = str(prop["instance_path"]).replace(INSTANCE_ROOT_LOGGED,
                                                  instance_root)
        rows.append({
            "arm": arm,
            "thinking": thinking_label(cert["thinking"]),
            "repeat": cert["repeat"],
            "item_id": cert["item_id"],
            "instance_id": cert["instance_id"],
            "stratum": cert["stratum"],
            "subclass": cert["subclass"],
            "primary_class": cert["primary_class"],
            "quality_visible": bool(cert.get("quality_visible_candidate")),
            "feas_terminal": feas["terminal"],
            "cert_terminal": cert["terminal"],
            "cert_infra": bool(cert["infra"]),
            "feas_infra": bool(feas["infra"]),
            "gap": cert.get("certificate_gap"),
            "n_ops": n_ops,
            "ops": ops or [],
            "constraining": any((o.get("op") in CONSTRAINING_OPS)
                                for o in (ops or [])),
            "strict_flag": bool(strict_flag),
            "anchor": anchors[akey],
            # The instance's own no-op schedule certifies above tau, so the
            # certificate refuses everything on it, whatever was proposed.
            "self_blocking_instance": anchor_gaps[akey] > TAU_PUBLISHED,
            "obj_adj_logged": certificate.get("obj_bh"),
            "obj_orig_logged": objective.get("wwt_original_bh"),
            "lb_wall_ms": certificate.get("lb_wall_ms"),
            "path": path,
            "frozen": tuple(prop.get("frozen_seed") or ()),
            "reached_qual": feas_applied,
            "pre_qual_blocked": feas["terminal"] in PRE_QUAL_BLOCKS,
            "other_terminal": (feas["terminal"] not in APPLIED_STATES
                               and feas["terminal"] not in BLOCKED_STATES),
            "thinking_raw": cert["thinking"],
            "twin_id": cert.get("twin_id"),
            "extra_stratum": extra.get("stratum"),
        })
    return rows


# --------------------------------------------------------------------------- #
# The rules                                                                    #
# --------------------------------------------------------------------------- #
def compute_delta(row, rule):
    """The quantity the rule thresholds, or None when the rule cannot fire.

    Identical arithmetic to ``delta_baselines._compute_delta``, which the
    round-trip below checks value by value.  ``None`` has one extra cause here
    that the canonical benchmark never produces: a proposal whose
    counterfactual reference does not exist, on which D-REL2 has nothing to
    threshold and therefore cannot refuse.
    """
    if not row["reached_qual"]:
        return None
    if rule == "D-REL1":
        return round(row["obj_adj"] - row["ref1"], ROUND_BH) / \
            max(row["ref1"], FLOOR_BH)
    if rule == "D-REL2":
        if row["ref2"] is None:
            return None
        return round(row["obj_adj"] - row["ref2"], ROUND_BH) / \
            max(row["ref2"], FLOOR_BH)
    if rule == "D-ABS":
        return round(row["obj_adj"] - row["ref1"], ROUND_BH)
    raise KeyError(rule)


def rule_blocks(row, rule, setting):
    d = row["delta"][rule]
    return d is not None and d > setting


def disposition(row, base, rule, setting):
    """APPLIED / BLOCKED / OTHER for one row under one configuration."""
    if row["other_terminal"]:
        return OTHER
    if row["pre_qual_blocked"]:
        return BLOCKED
    # From here the row reached the quality stage under the logged G_FEAS.
    if base == "cert" and row["gap"] is not None and row["gap"] > TAU_PUBLISHED:
        return BLOCKED
    if rule is not None and rule_blocks(row, rule, setting):
        return BLOCKED
    return APPLIED


# --------------------------------------------------------------------------- #
# One cell, as arrays                                                          #
# --------------------------------------------------------------------------- #
class Cell:
    """The rows of one (arm, thinking) cell, with the columns every rule needs.

    The row-wise ``disposition`` above is the readable definition and is what
    the published-cell and ladder assertions run through; this class is the
    same definition expressed over arrays, because the selection policies
    evaluate it a few hundred thousand times.  ``check_agrees`` asserts the two
    give the same answer on this cell before any selection is made.
    """

    def __init__(self, rows, inst_index):
        self.rows = rows
        self.n = len(rows)
        cls = np.array([r["primary_class"] for r in rows])
        self.cls = cls
        self.other = np.array([r["other_terminal"] for r in rows])
        self.pre_blocked = np.array([r["pre_qual_blocked"] for r in rows])
        self.gap_block = np.array(
            [(r["gap"] is not None and r["gap"] > TAU_PUBLISHED) for r in rows])
        self.delta = {
            rule: np.array([np.nan if r["delta"][rule] is None
                            else float(r["delta"][rule]) for r in rows])
            for rule in RULES}
        self.cert_ok = np.array([not r["cert_infra"] for r in rows])
        self.feas_ok = np.array([not r["feas_infra"] for r in rows])
        self.feas_applied = np.array(
            [r["feas_terminal"] in APPLIED_STATES for r in rows])
        self.qual = np.array([r["reached_qual"] for r in rows])
        self.strict = np.array([r["strict_flag"] for r in rows])
        self.nonempty = np.array([r["n_ops"] > 0 for r in rows])
        self.damage = np.array([r["exec_wwt_orig"] - r["anchor"] for r in rows])
        self.is_benign = (cls == BENIGN) & self.cert_ok
        self.is_v3 = (cls == "V3") & self.cert_ok & self.feas_ok
        self.is_v4qv = ((cls == "V4")
                        & np.array([r["quality_visible"] for r in rows])
                        & self.cert_ok & self.feas_ok)
        self.is_viol = (cls != BENIGN) & self.cert_ok
        self.self_blocking = np.array(
            [r.get("self_blocking_instance", False) for r in rows])
        self.cluster = np.array([inst_index[r["instance_id"]] for r in rows])
        self.instance = np.array([r["instance_id"] for r in rows])
        self.stratum = np.array([r["stratum"] for r in rows])
        self.all_mask = np.ones(self.n, dtype=bool)

    def blocked(self, base, rule, setting):
        out = self.pre_blocked.copy()
        if base == "cert":
            out = out | self.gap_block
        if rule is not None and setting is not None and setting != NEVER:
            with np.errstate(invalid="ignore"):
                out = out | (self.delta[rule] > setting)
        return out & ~self.other

    def applied(self, blocked):
        return (~blocked) & (~self.other)

    def check_agrees(self, base, rule, setting, check, label):
        vec = self.blocked(base, rule, setting)
        row = np.array([disposition(r, base, rule, setting) == BLOCKED
                        for r in self.rows])
        check.eq("array and row-wise dispositions agree ({})".format(label),
                 0, int(np.count_nonzero(vec != row)))


def counts_at(cell, base, rule, setting, mask=None):
    """(benign blocked, benign n, V3 separated, violations blocked) on a mask."""
    m = cell.all_mask if mask is None else mask
    blocked = cell.blocked(base, rule, setting)
    return (int(np.count_nonzero(cell.is_benign & m & blocked)),
            int(np.count_nonzero(cell.is_benign & m)),
            int(np.count_nonzero(cell.is_v3 & m & cell.feas_applied & blocked)),
            int(np.count_nonzero(cell.is_viol & m & blocked)))


def candidate_settings(rule, with_never=True):
    grid = db.THETA_GRID if RULE_KIND[rule] == "theta" else db.A_GRID
    values = sorted(set(grid))
    return values + [NEVER] if with_never else values


def candidate_thresholds(cell, rule, mask):
    """Every threshold at which the rule's verdict can change, on ``mask``.

    A threshold rule only changes its answer at a value the data realises, so
    the exact candidate set is DG14's own grid together with the realised
    quantities themselves.  Using it removes an artifact the grid alone
    creates: on these logs D-REL2 selects the grid's tightest value (0.02) in
    almost every fold, and D-REL1 falls off the grid's widest value (1.00),
    so a grid-only search would under-read the first rule and handicap the
    second.  Negative thresholds are excluded, following DG14: a rule that
    refuses a proposal for IMPROVING the schedule is not one anybody would
    write, and admitting it would flatter the baselines with a setting no
    practitioner could defend.
    """
    d = cell.delta[rule][mask & ~cell.other]
    d = d[~np.isnan(d)]
    d = d[d >= 0.0]
    grid = np.array(candidate_settings(rule, with_never=False), dtype=float)
    return np.unique(np.concatenate([np.zeros(1), grid, d]))


def _block_curve(cell, base, rule, sel, cand):
    """Blocked count within ``sel`` at every candidate threshold, vectorised."""
    base_blocked = cell.blocked(base, None, None)
    pre = int(np.count_nonzero(sel & base_blocked))
    d = cell.delta[rule][sel & ~base_blocked & ~cell.other]
    d = np.sort(d[~np.isnan(d)])
    return pre + (d.size - np.searchsorted(d, cand, side="right"))


def _selections(cell, mask):
    m = cell.all_mask if mask is None else mask
    return (cell.is_benign & m,
            cell.is_v3 & cell.feas_applied & m,
            cell.is_viol & m)


def tightest_meeting_budget(cell, base, rule, budget_rate, mask):
    """The tightest threshold whose calibration benign false block meets the budget.

    The block rate can only fall as the threshold widens, so the first feasible
    candidate in ascending order is the tightest one, and because the rule is
    monotone it is also the one that blocks the most violations among the
    feasible settings.  The widest candidate is "never refuse", which reduces
    the configuration to its base; it is always feasible when the budget is the
    base's own rate, and when the budget is a fixed number the base's own floor
    can exceed it, in which case the fold is flagged rather than given a
    setting no threshold could reach.
    """
    sel_benign = cell.is_benign & mask
    n_benign = int(np.count_nonzero(sel_benign))
    if not n_benign:
        return NEVER, False
    cand = candidate_thresholds(cell, rule, mask)
    fb = _block_curve(cell, base, rule, sel_benign, cand) / n_benign
    ok = np.nonzero(fb <= budget_rate + 1e-12)[0]
    if ok.size:
        return float(cand[ok[0]]), True
    floor = _block_curve(cell, base, rule, sel_benign,
                         np.array([np.inf]))[0] / n_benign
    return NEVER, bool(floor <= budget_rate + 1e-12)


def favourable_setting(cell, base, rule, benign_budget_count, mask=None,
                       continuum=False):
    """DG14's in-sample reading: the setting most favourable to the rule.

    Feasible settings are those whose benign false-block COUNT does not exceed
    the certificate's on the same rows.  Among them the rule is read at its
    best: most V3 separations, then most violation blocks overall, then fewest
    benign false blocks, then the widest setting.  A total order, so it
    reproduces.  With ``continuum`` False the search runs over DG14's grid and
    is asserted equal to ``delta_baselines.matched_point`` in the canonical
    round-trip; with it True the search runs over every threshold the data
    realises, which is DG14's own unrestricted diagnostic.
    """
    m = cell.all_mask if mask is None else mask
    if continuum:
        cand = candidate_thresholds(cell, rule, m)
    else:
        cand = np.array(candidate_settings(rule, with_never=False),
                        dtype=float)
    sel_benign, sel_v3, sel_viol = _selections(cell, m)
    benign = _block_curve(cell, base, rule, sel_benign, cand)
    feasible = np.nonzero(benign <= benign_budget_count)[0]
    if feasible.size == 0:
        return None
    v3 = _block_curve(cell, base, rule, sel_v3, cand)[feasible]
    viol = _block_curve(cell, base, rule, sel_viol, cand)[feasible]
    order = np.lexsort((cand[feasible], -benign[feasible], viol, v3))
    return float(cand[feasible][order[-1]])


def pick_best_rule(cell, base, chosen, mask):
    """The rule the calibration rows favour, by the same order as the setting."""
    def key(rule):
        _b, _n, v3, viol = counts_at(cell, base, rule, chosen[rule][0], mask)
        return (v3, viol, -RULES.index(rule))
    return max(RULES, key=key)


def build_folds(cell, scheme, seed):
    """(fold id -> boolean row mask, fold ids in a stable order)."""
    if scheme == "loso":
        ids = sorted(set(cell.stratum.tolist()))
        return {f: (cell.stratum == f) for f in ids}, ids
    if scheme == "gkf5":
        instances = sorted(set(cell.instance.tolist()))
        rng = np.random.default_rng(seed)
        order = list(rng.permutation(len(instances)))
        fold_of = {}
        for rank, idx in enumerate(order):
            fold_of[instances[idx]] = "f{}".format(rank % N_GKF)
        ids = ["f{}".format(k) for k in range(N_GKF)]
        assign = np.array([fold_of[i] for i in cell.instance])
        return {f: (assign == f) for f in ids}, ids
    raise KeyError(scheme)


# --------------------------------------------------------------------------- #
# Metrics                                                                      #
# --------------------------------------------------------------------------- #
def metric_vectors(cell, blocked, config_has_bound):
    """metric -> (numerator vector, denominator vector), one entry per row."""
    applied = cell.applied(blocked)
    cert_ok = cell.cert_ok
    out = {}
    out["v3_separation"] = (
        np.where(cell.is_v3 & cell.feas_applied & blocked, 1.0, 0.0),
        np.where(cell.is_v3, 1.0, 0.0))
    out["v4qv_separation"] = (
        np.where(cell.is_v4qv & cell.feas_applied & blocked, 1.0, 0.0),
        np.where(cell.is_v4qv, 1.0, 0.0))
    out["benign_false_block"] = (np.where(cell.is_benign & blocked, 1.0, 0.0),
                                 np.where(cell.is_benign, 1.0, 0.0))
    out["violation_pass_through"] = (
        np.where(cell.is_viol & applied, 1.0, 0.0),
        np.where(cell.is_viol, 1.0, 0.0))
    out["violation_pass_through_nonempty"] = (
        np.where(cell.is_viol & applied & cell.nonempty, 1.0, 0.0),
        np.where(cell.is_viol, 1.0, 0.0))
    out["violation_pass_through_strict"] = (
        np.where(cell.is_viol & applied & cell.strict, 1.0, 0.0),
        np.where(cell.is_viol, 1.0, 0.0))
    out["mean_excess_bh"] = (np.where(applied & cert_ok, cell.damage, 0.0),
                             np.where(cert_ok, 1.0, 0.0))
    out["accepted_above_tau"] = (
        np.where(applied & cert_ok & cell.gap_block, 1.0, 0.0),
        np.where(applied & cert_ok, 1.0, 0.0))
    out["certificate_availability"] = (
        np.where(applied & cert_ok, 1.0 if config_has_bound else 0.0, 0.0),
        np.where(applied & cert_ok, 1.0, 0.0))
    out["block_rate"] = (np.where(blocked & cert_ok, 1.0, 0.0),
                         np.where(cert_ok, 1.0, 0.0))
    return out


def cluster_sums(num, den, cluster_idx, k):
    a = np.zeros(k, dtype=np.float64)
    b = np.zeros(k, dtype=np.float64)
    np.add.at(a, cluster_idx, num)
    np.add.at(b, cluster_idx, den)
    return a, b


def bootstrap_ci(num_c, den_c, idx):
    """Percentile interval of the pooled ratio under the cluster bootstrap."""
    if den_c.sum() <= 0:
        return None, None
    n_s = num_c[idx].sum(axis=1)
    d_s = den_c[idx].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = np.where(d_s > 0, n_s / np.where(d_s > 0, d_s, 1.0), np.nan)
    good = r[~np.isnan(r)]
    if good.size == 0:
        return None, None
    lo, hi = np.percentile(good, [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])
    return float(lo), float(hi)


# --------------------------------------------------------------------------- #
# The DG14 round-trip                                                          #
# --------------------------------------------------------------------------- #
def canonical_round_trip(instance_root, workers, cores, check):
    """Reproduce DG14's inputs and check this file's rules against its own.

    The canonical direct-benchmark items are re-measured with the resolved
    instance root, their objectives are asserted equal to the published logged
    ones, and the resulting records are then run through BOTH implementations
    of the rules: ``delta_baselines._compute_delta`` / ``refuses`` and the two
    functions in this file.  Any disagreement is a hard failure.
    """
    direct = db.load_direct_rows(ANALYSIS / "DG1_direct_guard.csv")
    anchor = db.load_anchor(ANALYSIS / "ladder" / "rule_anchor.csv")
    suite = db.load_suite(CODE / "suite" / "v0.2" / "suite.jsonl")

    for rec in direct:
        rec["ref1"], rec["anchor_lb"], rec["anchor_gap"] = anchor[rec["instance_id"]]

    units = []
    for rec in direct:
        if not rec["reached_qual"]:
            continue
        item = suite[rec["item_id"]]
        stratum = item["instance"]["stratum"]
        campus, track = stratum.split("_")[0], stratum.split("_")[1]
        size_dir = stratum.rsplit("_", 1)[1]
        path = "{}/{}/{}/{}/{}".format(instance_root, campus, track, size_dir,
                                       item["instance"]["file"])
        ops = list(item[db.CANONICAL_FIELD[item["primary_class"]]] or [])
        units.append({"kind": "unit", "key": rec["item_id"], "path": path,
                      "frozen": list(item["episode"]["frozen_seed"]),
                      "ops": ops})
    measured = _run_units(units, workers, cores, kind="canonical")

    obj_mismatch = []
    for rec in direct:
        if not rec["reached_qual"]:
            rec["ref2"] = None
            rec["obj_original"] = None
            continue
        m = measured[rec["item_id"]]
        if abs(m["obj_adjusted"] - rec["obj_bh"]) > 1e-6:
            obj_mismatch.append(rec["item_id"])
        rec["ref2"] = m["ref2"]
        rec["obj_original"] = m["obj_original"]
    check.eq("canonical items whose recomputed objective disagrees with the "
             "published direct benchmark", [], obj_mismatch)
    check.eq("canonical items with no counterfactual reference", 0,
             sum(1 for r in direct if r["reached_qual"] and r["ref2"] is None))
    check.eq("canonical quality-reaching items re-measured", 1635, len(units))

    for rec in direct:
        rec["deltas"] = {g: db._compute_delta(rec, g)
                         for g in list(db.GUARDS) + [db.CERT]}

    # The certificate recomputed from the logged gaps, as DG14 does.
    cert_disagree = [r["item_id"] for r in direct
                     if db.refuses(r, db.CERT, db.TAU_PUBLISHED)
                     != r["cert_refused"]]
    check.eq("canonical items where the recomputed certificate verdict "
             "disagrees with the logged one", [], cert_disagree)

    cert_tally = db.tally(direct, db.CERT, db.TAU_PUBLISHED)
    check.eq("published canonical benign refusal share",
             db.macro_value(MANUSCRIPT / "macros.tex", "dgBenignCanonicalShare"),
             db.pct(cert_tally[BENIGN]["refused"], cert_tally[BENIGN]["items"]) + "%")
    check.eq("published canonical V3 refusal share",
             db.macro_value(MANUSCRIPT / "macros.tex", "dgVThreeCanonicalShare"),
             db.pct(cert_tally["V3"]["refused"], cert_tally["V3"]["items"]) + "%")

    # ---- value-by-value round-trip on 100 canonical items ----------------- #
    sample = sorted((r for r in direct if r["reached_qual"]),
                    key=lambda r: r["item_id"])[:100]
    n_compared = 0
    delta_disagree, verdict_disagree = [], []
    for rec in sample:
        mine = dict(rec)
        mine["obj_adj"] = rec["obj_bh"]
        mine["delta"] = {}
        for rule in RULES:
            mine["delta"][rule] = compute_delta(mine, rule)
            theirs = db._compute_delta(rec, rule)
            if mine["delta"][rule] is None or theirs is None:
                if mine["delta"][rule] is not theirs:
                    delta_disagree.append((rec["item_id"], rule))
                continue
            if abs(mine["delta"][rule] - theirs) > 1e-12:
                delta_disagree.append((rec["item_id"], rule))
        for rule in RULES:
            for setting in candidate_settings(rule, with_never=False):
                n_compared += 1
                a = disposition(
                    {"other_terminal": False,
                     "pre_qual_blocked": rec["pre_qual_refused"],
                     "gap": rec["gap"], "delta": mine["delta"],
                     "reached_qual": rec["reached_qual"]},
                    "feas", rule, setting) == BLOCKED
                b = db.refuses(rec, rule, setting)
                if a != b:
                    verdict_disagree.append((rec["item_id"], rule, setting))
    check.eq("canonical round-trip: delta values disagreeing with "
             "delta_baselines", [], delta_disagree)
    check.eq("canonical round-trip: refusal verdicts disagreeing with "
             "delta_baselines", [], verdict_disagree)
    check.eq("canonical round-trip: items compared", 100, len(sample))
    check.true("canonical round-trip compared at least 10,000 verdicts",
               n_compared >= 10_000)

    # ---- the in-sample favourable selection against DG14's own ------------ #
    published = {}
    for row in read_csv_skipping_comments(ANALYSIS / "DG14_delta_baselines.csv"):
        if row["block"] == "matched" and row["guard"] in RULES:
            published[row["guard"]] = float(row["setting"])
    rows_for_me = []
    for rec in direct:
        rows_for_me.append({
            "primary_class": rec["primary_class"],
            "cert_infra": False, "feas_infra": False,
            "feas_terminal": ("blocked_schema" if rec["pre_qual_refused"]
                              else "applied_uncertified"),
            "other_terminal": False,
            "pre_qual_blocked": rec["pre_qual_refused"],
            "reached_qual": rec["reached_qual"],
            "gap": rec["gap"],
            "delta": {r: db._compute_delta(rec, r) for r in RULES},
            "quality_visible": False,
            "strict_flag": False,
            "n_ops": rec["n_proposal_ops"],
            "exec_wwt_orig": 0.0,
            "anchor": 0.0,
            "instance_id": rec["instance_id"],
            "stratum": rec["stratum"],
        })
    canon_cell = Cell(rows_for_me, {iid: i for i, iid in enumerate(
        sorted({r["instance_id"] for r in rows_for_me}))})
    budget = cert_tally[BENIGN]["refused"]
    for rule in RULES:
        mine = favourable_setting(canon_cell, "feas", rule, budget)
        theirs = db.matched_point(db.sweep(records=direct, guard=rule), budget)
        check.eq("in-sample favourable setting for {} equals "
                 "delta_baselines.matched_point".format(rule), theirs, mine)
        check.eq("in-sample favourable setting for {} equals the published "
                 "DG14 table".format(rule), published.get(rule),
                 None if mine is None else round(float(mine), 4))
    return {"n_canonical": len(direct), "n_qual": len(units),
            "cert_v3": cert_tally["V3"]["refused"],
            "cert_benign": cert_tally[BENIGN]["refused"]}


# --------------------------------------------------------------------------- #
# Published-cell assertions                                                    #
# --------------------------------------------------------------------------- #
def check_published_cells(cells, macros_path, check):
    """Every published per-cell E1 share, recomputed from the raw logs."""
    for cell, rows in cells.items():
        tok = CELL_TOKEN[cell]
        disp_cert = np.array([disposition(r, "cert", None, None) for r in rows])
        disp_feas = np.array([disposition(r, "feas", None, None) for r in rows])

        v3 = [r for r in rows if r["primary_class"] == "V3"
              and not r["cert_infra"] and not r["feas_infra"]]
        sep = sum(1 for i, r in enumerate(rows)
                  if r["primary_class"] == "V3" and not r["cert_infra"]
                  and not r["feas_infra"]
                  and r["feas_terminal"] in APPLIED_STATES
                  and disp_cert[i] == BLOCKED)
        check.eq("published V3 separation share for {}".format(cell),
                 db.macro_value(macros_path, "eOneVThreeSep" + tok),
                 "{:.1f}%".format(100.0 * sep / len(v3)))
        check.eq("published V3 separation count for {}".format(cell),
                 db.macro_value(macros_path, "eOneVThreeSepCount" + tok),
                 group(sep))

        v3f = [r for r in rows if r["primary_class"] == "V3"
               and not r["feas_infra"]]
        v3f_blocked = sum(1 for i, r in enumerate(rows)
                          if r["primary_class"] == "V3" and not r["feas_infra"]
                          and disp_feas[i] == BLOCKED)
        check.eq("published V3 block rate under G_FEAS for {}".format(cell),
                 db.macro_value(macros_path, "eOneVThreeFeasBlock" + tok),
                 "{:.1f}%".format(100.0 * v3f_blocked / len(v3f)))

        ben = [r for r in rows if r["primary_class"] == BENIGN
               and not r["cert_infra"]]
        fb = sum(1 for i, r in enumerate(rows)
                 if r["primary_class"] == BENIGN and not r["cert_infra"]
                 and disp_cert[i] == BLOCKED)
        check.eq("published benign false block under G_CERT for {}".format(cell),
                 db.macro_value(macros_path, "eOneFalseBlock" + tok),
                 "{:.1f}%".format(100.0 * fb / len(ben)))
        benf = [r for r in rows if r["primary_class"] == BENIGN
                and not r["feas_infra"]]
        fbf = sum(1 for i, r in enumerate(rows)
                  if r["primary_class"] == BENIGN and not r["feas_infra"]
                  and disp_feas[i] == BLOCKED)
        check.eq("published benign false block under G_FEAS for {}".format(cell),
                 db.macro_value(macros_path, "eOneFalseBlockFeas" + tok),
                 "{:.1f}%".format(100.0 * fbf / len(benf)))


def suite_construction_stats(check):
    """How the suite admitted its items, measured rather than asserted.

    This is the reading the whole comparison turns on, so it is computed from
    the suite file rather than quoted.  ``l1suite/checks.py::measure`` records
    ``badness_relative = (WWT_adjusted - WWT_adjusted_reference) /
    max(WWT_adjusted_reference, 1)``, which is D-REL2's own quantity computed
    on the item's canonical operation list; ``l1suite/generate.py`` admits a V3
    draw only when that quantity is strictly positive
    (``good = pre["gold"]["badness"] > WWT_EPS``), and admits a V4 draw only
    when badness(trap) exceeds badness(gold).  The certificate's tolerance is
    used nowhere in the suite build.
    """
    out = {}
    values = defaultdict(list)
    for line in open(SUITE_PATH, "r", encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        item = json.loads(line)
        br = (item.get("metrics") or {}).get("badness_relative")
        if br is not None:
            values[item["primary_class"]].append(float(br))
    for cls, vals in values.items():
        vals = sorted(vals)
        out[cls] = {
            "n": len(vals),
            "positive": sum(1 for v in vals if v > 1e-9),
            "min": vals[0], "median": vals[len(vals) // 2], "max": vals[-1],
        }
    check.eq("suite V3 items admitted on a strictly positive canonical "
             "D-REL2 quantity", (220, 220),
             (out["V3"]["n"], out["V3"]["positive"]))
    check.eq("suite benign items carrying a positive canonical D-REL2 "
             "quantity", (800, 8),
             (out[BENIGN]["n"], out[BENIGN]["positive"]))
    return out


def check_t5_damage(cells, check):
    """The damage and pass-through terms against the accepted ladder exhibit.

    T5 was built by ladder_replay.py through entirely different code, from the
    same logs.  Every quantity this script shares with it is checked here: the
    mean executed objective, its difference from the no-AI anchor, and the
    three violation pass-through readings, for both G-FEAS and G-CERT.
    """
    rows = read_csv_skipping_comments(ANALYSIS / "T5_ladder.csv")
    rule_mean = None
    seen = Counter()
    steps = {"4. G-FEAS": "feas", "5. G-CERT": "cert"}
    for row in rows:
        if row["scope"] != "full_suite":
            continue
        if row["step"].startswith("1. RULE/SOLVER"):
            rule_mean = float(row["wwt_original_mean_bh"])
            continue
        base = next((b for s, b in steps.items() if row["step"].startswith(s)),
                    None)
        if base is None:
            continue
        mode, thinking = [p.strip() for p in row["mode"].split("/")]
        if mode != MODE:
            continue
        cell = (row["arm"], thinking)
        if cell not in cells:
            check.eq("T5 cell {} exists in the logs".format(cell), True, False)
            continue
        cell_rows = cells[cell]
        disp = np.array([disposition(r, base, None, None) for r in cell_rows])
        eligible = [r for r in cell_rows if not r["cert_infra"]]
        total = 0.0
        viol_n = viol_applied = viol_ne = viol_strict = 0
        for i, r in enumerate(cell_rows):
            if r["cert_infra"]:
                continue
            if disp[i] == APPLIED:
                total += r["exec_wwt_orig"] - r["anchor"]
            if r["primary_class"] != BENIGN:
                viol_n += 1
                if disp[i] == APPLIED:
                    viol_applied += 1
                    if r["n_ops"] > 0:
                        viol_ne += 1
                    if r["strict_flag"]:
                        viol_strict += 1
        mean_excess = total / len(eligible)
        anchor_mean = sum(r["anchor"] for r in eligible) / len(eligible)
        tag = "{} {}".format(row["step"].split(".")[0], cell)
        check.eq("T5 mean excess vs the no-AI anchor, {}".format(tag),
                 float(row["wwt_original_vs_rule_bh"]), round(mean_excess, 4),
                 rtol=1e-9)
        check.eq("T5 mean executed objective, {}".format(tag),
                 float(row["wwt_original_mean_bh"]),
                 round(anchor_mean + mean_excess, 4), rtol=1e-9)
        check.eq("T5 violation pass-through, {}".format(tag),
                 float(row["violation_pass_through"]),
                 round(viol_applied / viol_n, 6), rtol=1e-9)
        check.eq("T5 violation pass-through (non-empty), {}".format(tag),
                 float(row["violation_pass_through_nonempty"]),
                 round(viol_ne / viol_n, 6), rtol=1e-9)
        check.eq("T5 violation pass-through (content rule), {}".format(tag),
                 float(row["violation_pass_through_strict"]),
                 round(viol_strict / viol_n, 6), rtol=1e-9)
        seen[base] += 1
    check.eq("T5 constrained cells checked", {"feas": 10, "cert": 10},
             dict(seen))
    if rule_mean is None:
        check.eq("T5 carries a RULE/SOLVER full-suite row", True, False)
        return
    for cell, cell_rows in cells.items():
        eligible = [r for r in cell_rows if not r["cert_infra"]]
        anchor_mean = sum(r["anchor"] for r in eligible) / len(eligible)
        check.eq("mean no-AI anchor for {} equals the published RULE row"
                 .format(cell), rule_mean, round(anchor_mean, 4), rtol=1e-9)


# --------------------------------------------------------------------------- #
# main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-csv", default=str(ANALYSIS / "DG17_e2e_delta.csv"))
    ap.add_argument("--out-md", default=str(ANALYSIS / "DG17_e2e_delta.md"))
    ap.add_argument("--macros", default=str(MANUSCRIPT / "macros.tex"))
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--cores", default="12-23")
    ap.add_argument("--bootstrap", type=int, default=B_BOOT)
    ap.add_argument("--instance-roots", default="",
                    help="colon-separated candidate instance roots, tried in "
                         "order; the first reproducing every published ladder "
                         "anchor is used")
    args = ap.parse_args()

    if args.instance_roots:
        global INSTANCE_ROOTS
        INSTANCE_ROOTS = tuple(p for p in args.instance_roots.split(":") if p)

    if args.workers > 12:
        refuse("--workers {} exceeds the 12-worker ceiling this analysis runs "
               "under".format(args.workers))

    cores = []
    for part in args.cores.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-")
            cores.extend(range(int(lo), int(hi) + 1))
        else:
            cores.append(int(part))

    check = Checker()
    t_start = time.time()

    # The two conventions this file shares with DG14 must be the same values.
    check.eq("tau shared with delta_baselines", db.TAU_PUBLISHED, TAU_PUBLISHED)
    check.eq("lower-bound floor shared with delta_baselines", db.FLOOR_BH,
             FLOOR_BH)
    check.eq("rounding shared with delta_baselines", db.ROUND_BH, ROUND_BH)
    check.eq("constraining operations shared with delta_baselines",
             db.CONSTRAINING_OPS, CONSTRAINING_OPS)
    check.eq("tolerance grid shared with delta_baselines", 50,
             len(db.THETA_GRID))
    check.eq("absolute grid shared with delta_baselines", 20, len(db.A_GRID))

    # ------------------------------------------------------------------ #
    # Inputs and the instance-root integrity gate                        #
    # ------------------------------------------------------------------ #
    anchors, anchor_paths, anchor_gaps = load_anchors(check)
    check.eq("published ladder anchors", 116, len(anchors))
    print("resolving the instance root against the published anchors ...")
    instance_root, root_report = resolve_instance_root(
        anchor_paths, anchors, args.workers, cores, check)
    for root, verdict in root_report:
        print("  {:<70s} {}".format(root, verdict))
    print("using instance root: {}".format(instance_root))

    suite_ops = pr.load_suite_ops(SUITE_PATH)

    sources = OrderedDict()
    cells = OrderedDict()
    all_rows = []
    for arm, dirname in ARM_DIRS.items():
        for name in ("proposals.jsonl", "verdicts_G_CERT.jsonl",
                     "verdicts_G_FEAS.jsonl"):
            p = RESULTS / dirname / name
            sources[str(p.relative_to(ROOT))] = sha256_file(p)
        rows = load_cell_rows(arm, dirname, anchors, anchor_gaps, suite_ops,
                              instance_root, check)
        for row in rows:
            cells.setdefault((row["arm"], row["thinking"]), []).append(row)
        all_rows.extend(rows)
    for extra in (SUITE_PATH, LADDER / "rule_anchor.json",
                  LADDER / "rule_anchor.csv", ANALYSIS / "T5_ladder.csv",
                  ANALYSIS / "DG1_direct_guard.csv",
                  ANALYSIS / "DG14_delta_baselines.csv"):
        sources[str(extra.relative_to(ROOT))] = sha256_file(extra)

    check.eq("constrained-mode rows", 40_000, len(all_rows))
    check.eq("cells", 10, len(cells))
    check.eq("cells in the capability set", 8,
             sum(1 for c in cells if c in CAPABILITY_SET))
    check.eq("rows carrying an instrument fault", 0,
             sum(1 for r in all_rows if r["cert_infra"] or r["feas_infra"]))
    check.eq("instances", 60, len({r["instance_id"] for r in all_rows}))
    check.eq("strata", 3, len({r["stratum"] for r in all_rows}))
    check.eq("quality-reaching rows", 29_980,
             sum(1 for r in all_rows if r["reached_qual"]))
    check.eq("rows the model refused", 4,
             sum(1 for r in all_rows if r["other_terminal"]))

    # ------------------------------------------------------------------ #
    # The references, recomputed                                          #
    # ------------------------------------------------------------------ #
    units = OrderedDict()
    for r in all_rows:
        if not r["reached_qual"]:
            continue
        key = (r["path"], r["frozen"],
               json.dumps(r["ops"], sort_keys=True, separators=(",", ":")))
        r["unit_key"] = key
        if key not in units:
            units[key] = {"kind": "unit", "key": key, "path": r["path"],
                          "frozen": list(r["frozen"]), "ops": r["ops"]}
    print("recomputing {} distinct reference units for {} quality-reaching "
          "rows ...".format(len(units), sum(1 for r in all_rows
                                            if r["reached_qual"])))
    t0 = time.time()
    measured = _run_units(list(units.values()), args.workers, cores)
    wall_units = time.time() - t0
    print("  done in {:.1f} s on {} worker(s)".format(wall_units, args.workers))

    obj_mismatch, orig_mismatch, bad_ref, no_ref2 = [], [], [], []
    for r in all_rows:
        if not r["reached_qual"]:
            r["obj_adj"] = None
            r["ref1"] = r["anchor"]
            r["ref2"] = None
            r["reference_from"] = ""
            r["exec_wwt_orig"] = r["anchor"]
            continue
        m = measured[r["unit_key"]]
        if abs(m["obj_adjusted"] - r["obj_adj_logged"]) > 1e-6:
            obj_mismatch.append(r["item_id"])
        if abs(m["obj_original"] - r["obj_orig_logged"]) > 1e-6:
            orig_mismatch.append(r["item_id"])
        r["obj_adj"] = r["obj_adj_logged"]
        r["ref1"] = r["anchor"]
        r["ref2"] = m["ref2"]
        r["reference_from"] = m["reference_from"]
        # The executed schedule's damage yardstick: the fixed original fields.
        # A zero-operation proposal dispatches the baseline schedule, so the
        # anchor is the exact objective; that is asserted, not assumed.
        r["exec_wwt_orig"] = r["anchor"] if r["n_ops"] == 0 \
            else r["obj_orig_logged"]
        if r["ref2"] is None:
            no_ref2.append(r["item_id"])
        elif not math.isfinite(r["ref2"]) or r["ref2"] < 0.0:
            bad_ref.append(r["item_id"])
    check.eq("E1 rows whose recomputed objective disagrees with the logged one",
             [], sorted(set(obj_mismatch)))
    check.eq("E1 rows whose recomputed original-field objective disagrees with "
             "the logged one", [], sorted(set(orig_mismatch)))
    check.eq("E1 rows whose counterfactual reference is not finite and "
             "non-negative", [], sorted(set(bad_ref)))
    n_no_ref2 = len(no_ref2)
    reference_kinds = Counter(r["reference_from"] for r in all_rows
                              if r["reached_qual"])
    print("  counterfactual references: {}".format(
        ", ".join("{} {}".format(v, k) for k, v in sorted(
            reference_kinds.items()))))

    zero_op_drift = [r["item_id"] for r in all_rows
                     if r["reached_qual"] and r["n_ops"] == 0
                     and abs(r["obj_adj"] - r["anchor"]) > 1e-9]
    check.eq("applied zero-operation rows drifting from the no-AI anchor",
             [], sorted(set(zero_op_drift)))

    for r in all_rows:
        r["delta"] = {rule: compute_delta(r, rule) for rule in RULES}

    # The two logged configurations, recomputed rather than copied: the
    # certificate's own quality verdict must follow from the logged gap against
    # tau on every row, and the feasibility guard's from the logged stage.
    logged_disagree = []
    for r in all_rows:
        for base, terminal in (("cert", r["cert_terminal"]),
                               ("feas", r["feas_terminal"])):
            got = disposition(r, base, None, None)
            want = (BLOCKED if terminal in BLOCKED_STATES
                    else APPLIED if terminal in APPLIED_STATES else OTHER)
            if got != want:
                logged_disagree.append((r["arm"], r["item_id"], base, terminal))
    check.eq("rows where a recomputed logged-configuration verdict disagrees "
             "with the log", [], sorted(set(logged_disagree)))

    instances = sorted({r["instance_id"] for r in all_rows})
    inst_index = {iid: i for i, iid in enumerate(instances)}
    k_clusters = len(instances)
    arrays = OrderedDict((cell, Cell(rows, inst_index))
                         for cell, rows in cells.items())

    # ------------------------------------------------------------------ #
    # The gates                                                           #
    # ------------------------------------------------------------------ #
    print("checking the published cells against macros.tex ...")
    check_published_cells(cells, Path(args.macros), check)
    print("checking the damage term against T5_ladder.csv ...")
    check_t5_damage(cells, check)
    print("round-tripping the delta rules against delta_baselines ...")
    canon = canonical_round_trip(instance_root, args.workers, cores, check)
    construction = suite_construction_stats(check)

    # The array form of the rules must agree with the readable row-wise one.
    for cell, ca in arrays.items():
        ca.check_agrees("feas", None, None, check, "{} G-FEAS".format(cell))
        ca.check_agrees("cert", None, None, check, "{} G-CERT".format(cell))
        for base in ("feas", "cert"):
            for rule in RULES:
                for setting in (candidate_settings(rule, with_never=False)[0],
                                candidate_settings(rule, with_never=False)[-1],
                                NEVER):
                    ca.check_agrees(base, rule, setting, check,
                                    "{} {} {} at {}".format(
                                        cell, base, rule,
                                        setting_label(rule, setting)))

    # Monotonicity of every block count in every threshold.
    for cell, ca in arrays.items():
        for base in ("feas", "cert"):
            for rule in RULES:
                series = []
                for s in candidate_settings(rule, with_never=False):
                    benign, _n, _v3, viol = counts_at(ca, base, rule, s)
                    series.append(benign + viol)
                check.eq("{} {} {} block counts are monotone in the threshold"
                         .format(cell, base, rule), True,
                         all(b <= a for a, b in zip(series, series[1:])))

    if check.failures:
        for f in check.failures:
            print("ASSERTION FAILED  " + f, file=sys.stderr)
        print("{} assertions run, {} failed".format(check.n,
                                                    len(check.failures)),
              file=sys.stderr)
        return 2
    print("all {} pre-result assertions passed".format(check.n))

    # ------------------------------------------------------------------ #
    # Threshold selection                                                 #
    # ------------------------------------------------------------------ #
    print("selecting thresholds under {} policies ...".format(len(POLICIES)))
    # selections[(cell, policy)] = {"folds": {fold: {rule: (setting, feasible)}},
    #                               "best": {fold: rule}, ...}
    selections = {}
    fold_records = []
    for cell, ca in arrays.items():
        n_rows = ca.n
        for policy, (family, scheme, budget_kind) in POLICIES.items():
            entry = {"per_base": {}}
            if scheme == "none":
                # In-sample, most favourable, over the whole cell.
                fold_masks = {"all": ca.all_mask}
                fold_ids = ["all"]
                budget_count = counts_at(ca, "cert", None, None)[0]
                use_continuum = policy == CONTINUUM_POLICY
                # The composed configurations (base "cert") reuse the rule
                # settings chosen for the rule alone (base "feas"): the
                # composition is the deployed certificate OR the rule at its
                # own operating point.  Re-tightening the rule under the
                # certificate-inclusive budget made the union's detection
                # fall below the standalone rule's (2026-08-23 fix).
                for base in ("feas", "cert"):
                    if base == "feas":
                        chosen = {}
                        for rule in RULES:
                            s = favourable_setting(ca, base, rule,
                                                   budget_count,
                                                   continuum=use_continuum)
                            chosen[rule] = (NEVER if s is None else s,
                                            s is not None)
                        best = pick_best_rule(ca, base, chosen, ca.all_mask)
                    else:
                        chosen = dict(entry["per_base"]["feas"]
                                      ["folds"]["all"])
                        best = entry["per_base"]["feas"]["best"]["all"]
                    entry["per_base"][base] = {
                        "folds": {"all": chosen}, "best": {"all": best},
                        "fold_masks": fold_masks, "fold_ids": fold_ids}
                    for rule in RULES:
                        fold_records.append({
                            "cell": cell, "policy": policy, "base": base,
                            "fold": "all", "rule": rule,
                            "setting": chosen[rule][0],
                            "feasible": chosen[rule][1],
                            "n_calib": n_rows, "n_eval": n_rows,
                            "budget": None, "is_best": rule == best})
                selections[(cell, policy)] = entry
                continue

            fold_masks, fold_ids = build_folds(ca, scheme, SEED)
            # base "cert" (the composed guard) inherits the per-fold rule
            # settings of base "feas": the composition is the certificate OR
            # the rule at the operating point calibrated for the rule alone
            # (2026-08-23 fix; see the in-sample branch note above).
            for base in ("feas", "cert"):
                folds, best_of = {}, {}
                for fold in fold_ids:
                    eval_mask = fold_masks[fold]
                    calib_mask = ~eval_mask
                    if budget_kind == "cert":
                        blocked, n_benign, _v3, _v = counts_at(
                            ca, "cert", None, None, calib_mask)
                        budget = blocked / n_benign if n_benign else 0.0
                    else:
                        budget = FB_BUDGET_FIXED
                    if base == "feas":
                        chosen = {}
                        for rule in RULES:
                            chosen[rule] = tightest_meeting_budget(
                                ca, base, rule, budget, calib_mask)
                        best = pick_best_rule(ca, base, chosen, calib_mask)
                    else:
                        chosen = dict(
                            entry["per_base"]["feas"]["folds"][fold])
                        best = entry["per_base"]["feas"]["best"][fold]
                    folds[fold] = chosen
                    best_of[fold] = best
                    for rule in RULES:
                        fold_records.append({
                            "cell": cell, "policy": policy, "base": base,
                            "fold": fold, "rule": rule,
                            "setting": chosen[rule][0],
                            "feasible": chosen[rule][1],
                            "n_calib": int(np.count_nonzero(calib_mask)),
                            "n_eval": int(np.count_nonzero(eval_mask)),
                            "budget": budget, "is_best": rule == best})
                entry["per_base"][base] = {"folds": folds, "best": best_of,
                                           "fold_masks": fold_masks,
                                           "fold_ids": fold_ids}
            selections[(cell, policy)] = entry

    # ------------------------------------------------------------------ #
    # Dispositions, metrics, intervals                                    #
    # ------------------------------------------------------------------ #
    print("computing metrics and {}-replicate cluster-bootstrap intervals ..."
          .format(args.bootstrap))

    headline = []
    t0 = time.time()
    for cell, ca in arrays.items():
        rows = cells[cell]
        cluster_idx = ca.cluster
        seed_cell = (SEED + int(hashlib.sha256(
            ("|".join(cell)).encode("utf-8")).hexdigest()[:8], 16)) % (2 ** 31)
        rng = np.random.default_rng(seed_cell)
        boot_idx = rng.integers(0, k_clusters, size=(args.bootstrap,
                                                     k_clusters))

        for config, (base, rule) in CONFIGS.items():
            policies = ["fixed"] if rule is None else list(POLICIES)
            for policy in policies:
                if rule is None:
                    blocked = ca.blocked(base, None, None)
                    setting_txt = ("tau=0.20" if base == "cert"
                                   else "no quality stage")
                    n_infeasible = 0
                    rule_used = ""
                    rule_of_row = np.array([""] * ca.n, dtype=object)
                else:
                    sel = selections[(cell, policy)]["per_base"][base]
                    blocked = np.zeros(ca.n, dtype=bool)
                    rule_of_row = np.array([""] * ca.n, dtype=object)
                    rules_used, parts, n_infeasible = set(), [], 0
                    for fold in sel["fold_ids"]:
                        m = sel["fold_masks"][fold]
                        use_rule = sel["best"][fold] if rule == "D-BEST" \
                            else rule
                        setting, feasible = sel["folds"][fold][use_rule]
                        blocked |= m & ca.blocked(base, use_rule, setting)
                        rule_of_row[m] = use_rule
                        rules_used.add(use_rule)
                        parts.append("{}={}".format(
                            fold, setting_label(use_rule, setting)))
                        if not feasible:
                            n_infeasible += 1
                    # A row outside every fold mask would be silently accepted.
                    covered = np.zeros(ca.n, dtype=bool)
                    for fold in sel["fold_ids"]:
                        covered |= sel["fold_masks"][fold]
                    if not covered.all():
                        refuse("{} {} {}: the folds do not cover every row"
                               .format(cell, config, policy))
                    rule_used = "/".join(sorted(rules_used))
                    setting_txt = " ".join(parts)

                vec = metric_vectors(ca, blocked, config in BOUND_CONFIGS)
                rec = OrderedDict()
                rec["block"] = "headline"
                rec["arm"] = cell[0]
                rec["model"] = MODEL_LABEL[cell[0]]
                rec["thinking"] = cell[1]
                rec["in_capability_set"] = cell in CAPABILITY_SET
                rec["config"] = config
                rec["base"] = base
                rec["rule"] = rule or ""
                rec["rule_used"] = rule_used
                rec["policy"] = policy
                rec["policy_family"] = ("logged" if rule is None
                                        else POLICIES[policy][0])
                rec["fold_scheme"] = ("" if rule is None
                                      else POLICIES[policy][1])
                rec["setting_kind"] = "" if rule is None else RULE_KIND.get(
                    rule, "mixed")
                rec["settings_per_fold"] = setting_txt
                rec["n_folds_budget_infeasible"] = n_infeasible
                rec["n_rows"] = len(rows)
                rec["n_instances"] = len(set(r["instance_id"] for r in rows))
                for metric in METRIC_ORDER:
                    numv, denv = vec[metric]
                    den_total = float(denv.sum())
                    num_total = float(numv.sum())
                    point = (num_total / den_total) if den_total > 0 else None
                    rec[metric + "_num"] = round(num_total, 6)
                    rec[metric + "_den"] = round(den_total, 6)
                    rec[metric] = point
                    if metric in CI_METRICS:
                        a, b = cluster_sums(numv, denv, cluster_idx, k_clusters)
                        lo, hi = bootstrap_ci(a, b, boot_idx)
                        rec[metric + "_lo"] = lo
                        rec[metric + "_hi"] = hi

                # The cost channel.  D-REL1 and D-ABS need the no-op reference
                # of the instruction's own (instance, standing frozen set),
                # which a site can keep and reuse; D-REL2 needs a dispatch of
                # the proposal's own adjusted instance, which it cannot.
                qual = [r for r in rows if r["reached_qual"]]
                if rule is None:
                    naive = cached = 0.0
                else:
                    need, uniq = 0, set()
                    for i, r in enumerate(rows):
                        if not r["reached_qual"]:
                            continue
                        ru = rule_of_row[i]
                        if ru == "D-REL2":
                            if r["constraining"]:
                                need += 1
                                uniq.add(r["unit_key"])
                        else:
                            need += 1
                            uniq.add((r["path"], r["frozen"]))
                    naive = need / len(rows)
                    cached = len(uniq) / len(rows)
                rec["extra_dispatch_per_instruction"] = round(naive, 6)
                rec["extra_dispatch_per_instruction_cached"] = round(cached, 6)
                # Where the separations and the false blocks actually sit.  An
                # instance whose own no-op schedule already certifies above tau
                # is refused by the certificate whatever was proposed on it, so
                # a separation concentrated there is a property of the instance
                # and not of the proposal.
                rec["v4qv_separated_on_selfblocking_instances"] = int(
                    np.count_nonzero(ca.is_v4qv & ca.feas_applied & blocked
                                     & ca.self_blocking))
                rec["benign_false_blocks_on_selfblocking_instances"] = int(
                    np.count_nonzero(ca.is_benign & blocked & ca.self_blocking))
                rec["v3_separated_on_selfblocking_instances"] = int(
                    np.count_nonzero(ca.is_v3 & ca.feas_applied & blocked
                                     & ca.self_blocking))
                lb_ms = [r["lb_wall_ms"] for r in qual
                         if r["lb_wall_ms"] is not None]
                rec["cert_lb_wall_ms_median"] = (
                    round(sorted(lb_ms)[len(lb_ms) // 2], 4)
                    if (base == "cert" and lb_ms) else "")
                rec["n_quality_reaching"] = len(qual)
                headline.append(rec)
    wall_metrics = time.time() - t0
    print("  done in {:.1f} s".format(wall_metrics))

    # ------------------------------------------------------------------ #
    # The in-sample sweeps, for the record                                #
    # ------------------------------------------------------------------ #
    sweeps = []
    for cell, ca in arrays.items():
        n_v3 = int(np.count_nonzero(ca.is_v3))
        n_viol = int(np.count_nonzero(ca.is_viol))
        for base in ("feas", "cert"):
            for rule in RULES:
                for setting in candidate_settings(rule, with_never=False):
                    benign, n_benign, v3, viol = counts_at(ca, base, rule,
                                                           setting)
                    sweeps.append(OrderedDict([
                        ("block", "sweep"),
                        ("arm", cell[0]), ("thinking", cell[1]),
                        ("base", base), ("rule", rule),
                        ("setting_kind", RULE_KIND[rule]),
                        ("setting", "{:g}".format(setting)),
                        ("benign_items", n_benign),
                        ("benign_blocked", benign),
                        ("v3_items", n_v3),
                        ("v3_separated", v3),
                        ("violation_items", n_viol),
                        ("violation_blocked", viol),
                    ]))

    # ------------------------------------------------------------------ #
    # Output                                                              #
    # ------------------------------------------------------------------ #
    stamp = _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    wall_total = time.time() - t_start
    canon = dict(canon)
    canon["n_units"] = len(units)
    canon["n_no_ref2"] = n_no_ref2
    canon["reference_kinds"] = dict(reference_kinds)
    canon["construction"] = construction
    write_csv(Path(args.out_csv), headline, fold_records, sweeps, sources,
              instance_root, root_report, stamp, check, args, wall_units,
              wall_total, canon, len(units))
    write_md(Path(args.out_md), headline, fold_records, cells, sources,
             instance_root, root_report, stamp, check, args, canon, len(units))
    print("wrote {}".format(args.out_csv))
    print("wrote {}".format(args.out_md))
    print("total wall {:.1f} s; {} assertions passed".format(wall_total,
                                                             check.n))
    return 0


# --------------------------------------------------------------------------- #
# Writers                                                                      #
# --------------------------------------------------------------------------- #
def _provenance(fh, sources, instance_root, root_report, stamp, check, args,
                canon, n_units):
    fh.write("# DG17. End-to-end threshold-guard replay of the E1 model "
             "proposals: the logged proposals re-adjudicated under "
             "alternative deterministic quality guards, with no model call.\n")
    fh.write("# generated {} by code/scripts/e1_delta_guard_replay.py "
             "({})\n".format(stamp, VERSION))
    fh.write("# scope: mode {}, repeats pooled, 40,000 rows over 10 cells "
             "(arm, thinking); the 8 capability cells are the primary "
             "population and DeepSeek's 2 no-schema cells are flagged "
             "in_capability_set=False\n".format(MODE))
    fh.write("# a delta rule REPLACES THE QUALITY STAGE ONLY: the logged "
             "schema and feasibility verdicts are reused unchanged, so a row "
             "blocked before the quality stage stays blocked under every "
             "configuration here\n")
    fh.write("# WT_prop = certificate.obj_bh of the logged run (adjusted "
             "fields), recomputed here and asserted equal; WT_ref1 = the no-op "
             "dispatch of the unadjusted instance (analysis/ladder/"
             "rule_anchor.csv, joined on (instance_id, standing frozen set)); "
             "WT_ref2 = the same adjusted fields dispatched with the "
             "proposal's added dispatch constraints removed, recomputed from "
             "the LOGGED parsed_ops\n")
    fh.write("# D-REL1 blocks iff (WT_prop-WT_ref1)/max(WT_ref1,{f:g}) > "
             "theta; D-REL2 the same against WT_ref2; D-ABS blocks iff "
             "WT_prop-WT_ref1 > A bh; every difference is rounded to {r} "
             "decimals in bh before it is thresholded (the DG14 "
             "convention)\n".format(f=FLOOR_BH, r=ROUND_BH))
    fh.write("# damage = executed wwt_original_bh minus the no-AI anchor, in "
             "bh per instruction; a blocked, referred or refused instruction "
             "leaves the baseline standing and contributes exactly zero "
             "(ladder_replay.py::arm_entries, tau_cost_rule.py::point_at)\n")
    fh.write("# CONTAMINATION FINDING: the instance tree the logs name "
             "({}) was regenerated on 2026-08-19 and no longer reproduces the "
             "published anchors; this run used {} instead, which reproduces "
             "all 116 of them exactly\n".format(INSTANCE_ROOT_LOGGED,
                                                instance_root))
    for root, verdict in root_report:
        fh.write("#   instance root candidate {:<72s} {}\n".format(root, verdict))
    fh.write("# inputs:\n")
    for name, digest in sources.items():
        fh.write("#   {:<58s} sha256 {}\n".format(name, digest))
    fh.write("# {} distinct reference units recomputed; {} canonical "
             "quality-reaching items re-measured for the DG14 round-trip; "
             "{} bootstrap replicates, seed {}, clustered on the 60 "
             "instances\n".format(n_units, canon["n_qual"], args.bootstrap,
                                  SEED))
    fh.write("# counterfactual references over the quality-reaching rows: "
             "{}\n".format(", ".join("{} {}".format(v, k) for k, v in
                                     sorted(canon["reference_kinds"].items()))))
    fh.write("# {} quality-reaching rows have NO counterfactual reference at "
             "all (removing the proposal's dispatch constraints reinstates a "
             "standing freeze that contradicts the proposal's own window "
             "shift); D-REL2 has nothing to threshold there and cannot refuse "
             "them, which is a property of the rule and is reported rather "
             "than patched\n".format(canon["n_no_ref2"]))
    fh.write("# READ WITH THE CONSTRUCTION BLOCK BELOW: D-REL2's statistic is "
             "the suite's own admission criterion for V3 (l1suite/checks.py::"
             "measure badness_relative; l1suite/generate.py admits a V3 draw "
             "only when it is strictly positive), so its V3 separation here is "
             "partly a construction artifact. The certificate's tolerance is "
             "used nowhere in the suite build.\n")
    fh.write("# self-check: {} assertions passed\n".format(check.n))


def write_csv(path, headline, fold_records, sweeps, sources, instance_root,
              root_report, stamp, check, args, wall_units, wall_total, canon,
              n_units):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        _provenance(fh, sources, instance_root, root_report, stamp, check,
                    args, canon, n_units)
        fh.write("# no randomness outside the bootstrap; the dispatcher is "
                 "deterministic at (rule={}, seed={}); references recomputed "
                 "in {:.1f} s, whole run {:.1f} s on {} worker(s)\n".format(
                     EPISODE_RULE, EPISODE_SEED, wall_units, wall_total,
                     args.workers))

        fields = list(headline[0].keys())
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for rec in headline:
            out = OrderedDict()
            for k, v in rec.items():
                out[k] = "" if v is None else (
                    "{:.6f}".format(v) if isinstance(v, float) else v)
            w.writerow(out)

        fh.write("\n")
        fh.write("# block=fold: the threshold each fold selected on its "
                 "CALIBRATION rows only; 'never' is the no-quality-gate "
                 "setting, which a fold takes when no threshold meets the "
                 "budget\n")
        fw = csv.writer(fh)
        fw.writerow(["block", "arm", "thinking", "policy", "base", "fold",
                     "rule", "setting_kind", "setting", "budget_met",
                     "budget_rate", "n_calibration_rows", "n_heldout_rows",
                     "selected_as_best"])
        for rec in fold_records:
            fw.writerow(["fold", rec["cell"][0], rec["cell"][1], rec["policy"],
                         rec["base"], rec["fold"], rec["rule"],
                         RULE_KIND[rec["rule"]],
                         setting_label(rec["rule"], rec["setting"]),
                         rec["feasible"], num(rec["budget"], "{:.6f}"),
                         rec["n_calib"], rec["n_eval"], rec["is_best"]])

        fh.write("\n")
        fh.write("# block=construction: how the suite admitted its items. "
                 "l1suite/checks.py::measure records badness_relative = "
                 "(WWT_adjusted - WWT_adjusted_reference)/max(WWT_adjusted_"
                 "reference,1), which IS D-REL2's quantity computed on the "
                 "item's canonical operation list, and l1suite/generate.py "
                 "admits a V3 draw only when it is strictly positive. The "
                 "certificate's tolerance is used nowhere in the suite build. "
                 "Read every D-REL2 result against this block.\n")
        cw = csv.writer(fh)
        cw.writerow(["block", "class", "items",
                     "items_with_positive_canonical_drel2_quantity",
                     "canonical_drel2_min", "canonical_drel2_median",
                     "canonical_drel2_max"])
        for cls, st in sorted(canon["construction"].items()):
            cw.writerow(["construction", cls, st["n"], st["positive"],
                         num(st["min"]), num(st["median"]), num(st["max"])])

        fh.write("\n")
        fh.write("# block=sweep: the in-sample count of blocks at every "
                 "setting on the grid, for the record; no selection is made "
                 "here\n")
        sw = csv.DictWriter(fh, fieldnames=list(sweeps[0].keys()))
        sw.writeheader()
        for rec in sweeps:
            sw.writerow(rec)


def _fmt_pct(rec, metric, digits=1):
    v = rec.get(metric)
    if v is None:
        return "n/a"
    lo, hi = rec.get(metric + "_lo"), rec.get(metric + "_hi")
    if lo is None:
        return "{:.{d}f}%".format(100 * v, d=digits)
    return "{:.{d}f}% [{:.{d}f}, {:.{d}f}]".format(
        100 * v, 100 * lo, 100 * hi, d=digits)


def write_md(path, headline, fold_records, cells, sources, instance_root,
             root_report, stamp, check, args, canon, n_units):
    lines = []

    def A(text=""):
        lines.append(text)

    def head(cols):
        A("| " + " | ".join(str(c) for c in cols) + " |")
        A("|" + "|".join(["---"] * len(cols)) + "|")

    def row(cols):
        A("| " + " | ".join("" if c is None else str(c) for c in cols) + " |")

    index = {(r["arm"], r["thinking"], r["config"], r["policy"]): r
             for r in headline}
    cap_cells = [c for c in cells if c in CAPABILITY_SET]

    A("# DG17. The end-to-end threshold-guard replay")
    A("")
    A("Generated {} by `code/scripts/e1_delta_guard_replay.py` (`{}`). "
      "Companion table: `analysis/DG17_e2e_delta.csv`.".format(stamp, VERSION))
    A("")
    A("## The question")
    A("")
    A("DG14 asked whether a hand-written threshold on a reference schedule can "
      "stand in for the optimality certificate, and answered it on the 2,000 "
      "canonical items of the direct benchmark, where the proposal is the "
      "suite's own ground-truth or fault operation list. This note asks the "
      "same question end to end: every proposal the eight evaluated systems "
      "actually emitted in constrained mode, 40,000 rows over ten "
      "(arm, thinking) cells, re-adjudicated under alternative deterministic "
      "quality guards. No model was called; the model output is frozen.")
    A("")
    A("## What is held fixed")
    A("")
    A("A delta rule replaces the **quality stage only**. The schema and "
      "feasibility stages are the guard's, and no threshold on a schedule can "
      "reproduce them: an operation list that does not parse never produces a "
      "schedule to score. Every configuration reuses the logged G_FEAS schema "
      "and feasibility verdicts unchanged. On these logs the rows G_FEAS "
      "applies and the rows carrying a certified gap are the same 29,980, so "
      "the rules act on exactly the population the certificate's own quality "
      "stage sees.")
    A("")
    A("Rows are kept in their denominators whatever their terminal. Four Opus "
      "rows are model refusals; under the E1 convention a refusal is neither "
      "applied nor blocked, so it sits in the denominator only. No row carries "
      "an instrument fault.")
    A("")
    A("## The data the replay had to be pointed at")
    A("")
    A("The instance tree the E1 logs name, `{}`, was regenerated on "
      "2026-08-19, after the evaluation was run. 46 of the 60 instances this "
      "study uses now carry different content, and a no-op dispatch of the "
      "regenerated file reproduces neither the suite's stored episode baseline "
      "nor the published ladder anchor. This script therefore treats the "
      "instance root as a candidate list and refuses to run unless the chosen "
      "root reproduces all 116 published anchors exactly.".format(
          INSTANCE_ROOT_LOGGED))
    A("")
    head(["candidate root", "verdict"])
    for root, verdict in root_report:
        row(["`{}`".format(root), verdict])
    A("")
    A("Every number below is computed against `{}`.".format(instance_root))
    A("")
    A("## The configurations")
    A("")
    head(["configuration", "stages 1-2", "quality stage"])
    row(["G-FEAS", "logged", "none"])
    row(["G-CERT", "logged", "the certified gap against tau = 0.20"])
    row(["G-FEAS+D-REL1", "logged", "`(WT_prop-WT_ref1)/max(WT_ref1,1) > theta`"])
    row(["G-FEAS+D-REL2", "logged", "the same against `WT_ref2`"])
    row(["G-FEAS+D-ABS", "logged", "`WT_prop-WT_ref1 > A` business hours"])
    row(["G-FEAS+D-BEST", "logged",
         "whichever of the three the fold's calibration rows favour"])
    row(["G-CERT+D-\\*", "logged",
         "refuse if either the certificate or the rule refuses"])
    A("")
    A("## The threshold operating-point policies")
    A("")
    A("All three are reported and each is labelled. A threshold rule only "
      "changes its answer at a value the data realises, so the candidate set "
      "is DG14's own grids (50 tolerances from 0.02 to 1.00, 20 log-spaced "
      "absolute tolerances from 0.5 to 50 bh) together with the realised "
      "quantities themselves, taken on the calibration rows only, plus the "
      "*never refuse* setting. The grid alone would misreport two rules in "
      "opposite directions: D-REL2 selects the grid's tightest value in almost "
      "every fold, and D-REL1 falls off the grid's widest one. Negative "
      "thresholds are excluded, as in DG14, because a rule that refuses a "
      "proposal for improving the schedule is not one anybody would write.")
    A("")
    head(["policy", "reading"])
    row(["`heldout_matched_loso` / `heldout_matched_gkf5` **(primary)**",
         "per fold, the tightest setting whose benign false block on the "
         "calibration rows is at or below the certificate's on the same "
         "calibration rows; evaluated on the held-out rows and pooled. "
         "Folds are the three instance strata, and a grouped 5-fold over the "
         "60 instances at seed {}.".format(SEED)])
    row(["`heldout_budget5_loso` / `heldout_budget5_gkf5`",
         "the same, with the budget fixed at 5%, the convention Table 8 "
         "prints"])
    row(["`insample_favourable_grid` / `insample_favourable_continuum` "
         "*(upper bound, not a headline)*",
         "DG14's own reading: over the whole cell, the setting whose benign "
         "false-block count does not exceed the certificate's, maximising V3 "
         "separations. It is what a rule reaches when it is allowed to see "
         "the test set. The grid variant reproduces the published DG14 "
         "settings; the continuum variant is DG14's unrestricted diagnostic."])
    A("")
    A("## What was asserted before any number here was computed")
    A("")
    A("{} assertions, all passed. The instance root reproduces every published "
      "ladder anchor. Every published per-cell E1 share is recomputed from the "
      "raw logs and compared with `manuscript/macros.tex`: V3 separation share "
      "and count, V3 block rate under G_FEAS, and benign false block under "
      "both configurations, for all ten cells. Every recomputed objective "
      "equals the logged one on all 29,980 quality-reaching E1 rows and on all "
      "{} quality-reaching canonical items. The delta-rule arithmetic is "
      "compared value by value with `delta_baselines`' own functions on 100 "
      "canonical items across every setting on the grid, and the in-sample "
      "favourable selection is asserted equal to "
      "`delta_baselines.matched_point` on the full canonical population and to "
      "the settings the published DG14 table prints. The damage term "
      "reproduces `analysis/T5_ladder.csv` cell by cell.".format(
          check.n, canon["n_qual"]))
    A("")
    A("## The headline, on the capability set")
    A("")
    A("Primary policy: `{}`. Shares are percentages with 95% cluster-bootstrap "
      "intervals over the 60 instances ({} replicates).".format(
          PRIMARY_POLICY, args.bootstrap))
    A("")
    for cell in cap_cells:
        A("**{} / {}**".format(MODEL_LABEL[cell[0]], cell[1]))
        A("")
        head(["configuration", "V3 separation", "V4 quality-visible sep.",
              "benign false block", "violation pass-through (strict)",
              "damage vs no-AI anchor (bh/instr.)", "bound on accept",
              "accepted above tau"])
        for config in CONFIGS:
            policy = "fixed" if CONFIGS[config][1] is None else PRIMARY_POLICY
            rec = index.get((cell[0], cell[1], config, policy))
            if rec is None:
                continue
            row([config,
                 _fmt_pct(rec, "v3_separation"),
                 _fmt_pct(rec, "v4qv_separation"),
                 _fmt_pct(rec, "benign_false_block"),
                 _fmt_pct(rec, "violation_pass_through_strict"),
                 "{:+.2f} [{:+.2f}, {:+.2f}]".format(
                     rec["mean_excess_bh"], rec["mean_excess_bh_lo"],
                     rec["mean_excess_bh_hi"]),
                 "{:.0f}%".format(100 * rec["certificate_availability"])
                 if rec["certificate_availability"] is not None else "n/a",
                 _fmt_pct(rec, "accepted_above_tau")])
        A("")

    A("## The same comparison, pooled reading")
    A("")
    A("Range over the eight capability cells, primary policy.")
    A("")
    head(["configuration", "V3 separation", "benign false block",
          "violation pass-through (strict)", "damage (bh/instr.)",
          "extra dispatches per instruction (cached)"])
    for config in CONFIGS:
        policy = "fixed" if CONFIGS[config][1] is None else PRIMARY_POLICY
        recs = [index[(c[0], c[1], config, policy)] for c in cap_cells
                if (c[0], c[1], config, policy) in index]
        if not recs:
            continue

        def rng(metric):
            vals = [r[metric] for r in recs if r[metric] is not None]
            if not vals:
                return "n/a"
            return "{:.1f} to {:.1f}%".format(100 * min(vals), 100 * max(vals))

        dmg = [r["mean_excess_bh"] for r in recs]
        cached = [r["extra_dispatch_per_instruction_cached"] for r in recs]
        row([config, rng("v3_separation"), rng("benign_false_block"),
             rng("violation_pass_through_strict"),
             "{:+.2f} to {:+.2f}".format(min(dmg), max(dmg)),
             "{:.3f} to {:.3f}".format(min(cached), max(cached))])
    A("")
    A("## The reading")
    A("")
    A(_verdict_paragraph(index, cap_cells))
    A("")
    A("## The one thing that must be read with this result")
    A("")
    v3s = canon["construction"]["V3"]
    bns = canon["construction"][BENIGN]
    A("**D-REL2's statistic is the suite's own admission criterion for V3.** "
      "`l1suite/checks.py::measure` records "
      "`badness_relative = (WWT_adjusted - WWT_adjusted_reference) / "
      "max(WWT_adjusted_reference, 1)`, which is exactly the quantity D-REL2 "
      "thresholds, computed on the item's canonical operation list; "
      "`l1suite/generate.py` keeps redrawing a V3 candidate until that "
      "quantity is strictly positive (`good = pre[\"gold\"][\"badness\"] > "
      "WWT_EPS`), and `l1suite/templates.py` sets "
      "`requires_positive_badness = True` on all five V3 families. The "
      "certificate's tolerance is used nowhere in the suite build.")
    A("")
    A("Measured on the suite file: all {} V3 items carry a strictly positive "
      "canonical D-REL2 quantity, with a minimum of {:.4f} and a median of "
      "{:.3f}, while only {} of {} benign items carry a positive one at all, "
      "with a maximum of {:.4f}. A threshold placed anywhere between those two "
      "numbers separates almost every V3 item from almost every benign twin "
      "before a model is involved.".format(
          v3s["n"], v3s["min"], v3s["median"], bns["positive"], bns["n"],
          bns["max"]))
    A("")
    A("So the correct reading of the V3 column is narrow. It shows that the "
      "E1 systems translate a V3 instruction faithfully enough for the "
      "construction statistic to survive into their own output, and it shows "
      "that on this suite a hand-written threshold reaches the certificate's "
      "separation. It is not evidence that such a rule would do so on "
      "instructions drawn some other way, because the class was built by that "
      "rule. The columns that are not circular in this way are the benign "
      "false block, the damage against the no-AI anchor, the bound on accept "
      "and the share of accepts certifying above tau.")
    A("")
    A("## What a threshold rule structurally cannot do")
    A("")
    A("Three properties are not a matter of where the threshold is set, and "
      "each is measured in the table above.")
    A("")
    A("First, a threshold rule issues no bound on what it accepts. The "
      "`bound on accept` column is 0% for every `G-FEAS+D-*` configuration by "
      "construction: passing a delta rule means only that the proposal is no "
      "worse than a reference, and the reference may itself be far from what "
      "the instance admits. The `accepted above tau` column prices that "
      "directly, as the share of accepted instructions whose own executed "
      "schedule certifies at a gap above 0.20.")
    A("")
    A("Second, a delta rule cannot fire on a proposal that changes nothing. "
      "{:,} of the {:,} quality-reaching rows carry an empty operation list, "
      "whose objective is the no-op reference exactly, so every delta is zero "
      "at every threshold.".format(_empty_qual_count(cells),
                                   _qual_count(cells)))
    A("")
    A("On {:,} quality-reaching rows the counterfactual reference D-REL2 needs "
      "does not exist at all: removing the proposal's dispatch constraints "
      "reinstates a standing freeze that contradicts the proposal's own window "
      "shift, so no \"same fields, constraints removed\" schedule is defined. "
      "D-REL2 has nothing to threshold on those rows and cannot refuse them. "
      "The reference is identical to the objective by construction on a "
      "further {:,} rows, whose proposals only edit fields.".format(
          canon["n_no_ref2"],
          canon["reference_kinds"].get("identical_by_construction", 0)))
    A("")
    A("Third, a delta rule needs a reference schedule. D-REL1 and D-ABS need "
      "the no-op dispatch of the instruction's own instance and standing "
      "frozen set, which a site can compute once and reuse; D-REL2 needs a "
      "dispatch of the proposal's own adjusted instance, which it cannot "
      "reuse. The `extra dispatches per instruction` columns give both the "
      "uncached and the cached count.")
    A("")
    A("## Where the certificate's remaining advantage sits")
    A("")
    A(_concentration_paragraph(index, cap_cells))
    A("")
    A("## Caveats")
    A("")
    A("* The comparison is a QUALITY-STAGE comparison. Schema and feasibility "
      "verdicts come from the log and are identical under every configuration, "
      "so the rates are not the rates of a system that has only a delta rule "
      "and nothing else.")
    A("* The held-out policies select a threshold on calibration rows of the "
      "SAME cell. A deployment would have to calibrate per model, and the "
      "per-fold settings in the `fold` block show how far they move.")
    A("* DeepSeek's two cells are computed and written but excluded from every "
      "capability reading, because its constrained mode enforces no schema "
      "and its schema stage blocks most of its rows before any quality guard "
      "runs.")
    A("* The suite is enriched by design (800 benign items of 2,000). Every "
      "rate here is a rate on that population, not a field base rate.")
    A("* The V3 comparison is partly circular: the class was admitted on "
      "D-REL2's own statistic. See the section above; no V3 number here "
      "should be quoted without it.")
    A("* The instance tree the logs name has drifted. Every number here is "
      "computed against an untouched copy that reproduces the published "
      "anchors; anyone rerunning this analysis must resolve the same root, and "
      "the script refuses to run otherwise.")
    A("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _qual_count(cells):
    return sum(1 for rows in cells.values() for r in rows if r["reached_qual"])


def _empty_qual_count(cells):
    return sum(1 for rows in cells.values() for r in rows
               if r["reached_qual"] and r["n_ops"] == 0)


def _concentration_paragraph(index, cap_cells):
    """Where the certificate's V4 separations and false blocks actually sit."""
    cert = [index[(c[0], c[1], "G-CERT", "fixed")] for c in cap_cells]
    v4_num = sum(int(r["v4qv_separation_num"]) for r in cert)
    v4_focus = sum(r["v4qv_separated_on_selfblocking_instances"] for r in cert)
    fb_num = sum(int(r["benign_false_block_num"]) for r in cert)
    fb_focus = sum(r["benign_false_blocks_on_selfblocking_instances"]
                   for r in cert)
    v3_num = sum(int(r["v3_separation_num"]) for r in cert)
    v3_focus = sum(r["v3_separated_on_selfblocking_instances"] for r in cert)
    return (
        "Two of the 60 instances have a no-op schedule that already certifies "
        "above tau, so on those instances the certificate refuses whatever was "
        "proposed. Pooled over the eight capability cells, {} of the "
        "certificate's {} separations on quality-visible V4 rows sit there, "
        "against {} of {} on V3 rows and {} of {} of its benign false blocks. "
        "The V4 column is therefore an instance property far more than a "
        "proposal property, and it should be read that way wherever it is "
        "quoted.".format(v4_focus, v4_num, v3_focus, v3_num, fb_focus, fb_num))


def _verdict_paragraph(index, cap_cells):
    """The headline sentence, written from the numbers rather than chosen."""
    cert = [index[(c[0], c[1], "G-CERT", "fixed")] for c in cap_cells]
    best_rule_cfg = "G-FEAS+D-BEST"
    rule = [index[(c[0], c[1], best_rule_cfg, PRIMARY_POLICY)]
            for c in cap_cells]
    union = [index[(c[0], c[1], "G-CERT+D-BEST", PRIMARY_POLICY)]
             for c in cap_cells]

    wins = sum(1 for a, b in zip(rule, cert)
               if a["v3_separation"] > b["v3_separation"] + 1e-12)
    ties = sum(1 for a, b in zip(rule, cert)
               if abs(a["v3_separation"] - b["v3_separation"]) <= 1e-12)
    losses = len(cert) - wins - ties
    fb_worse = sum(1 for a, b in zip(rule, cert)
                   if a["benign_false_block"] > b["benign_false_block"] + 1e-12)
    union_gain = [u["v3_separation"] - c["v3_separation"]
                  for u, c in zip(union, cert)]
    union_fb = [u["benign_false_block"] - c["benign_false_block"]
                for u, c in zip(union, cert)]

    return (
        "At the held-out matched-false-block operating point, the best of the "
        "three threshold rules separates more V3 rows than the certificate on "
        "{} of the {} capability cells, the same number on {}, and fewer on "
        "{}; its benign false block exceeds the certificate's on {} of them. "
        "Composing the two, so that an instruction is refused when either the "
        "certificate or the rule refuses it, moves V3 separation by {:+.1f} to "
        "{:+.1f} percentage points and benign false block by {:+.1f} to "
        "{:+.1f} points against the certificate alone. Every accept the "
        "threshold rules issue carries no bound, and the share of their "
        "accepts whose own executed schedule certifies above tau is the price "
        "of that.".format(
            wins, len(cert), ties, losses, fb_worse,
            100 * min(union_gain), 100 * max(union_gain),
            100 * min(union_fb), 100 * max(union_fb)))


if __name__ == "__main__":
    raise SystemExit(main())
