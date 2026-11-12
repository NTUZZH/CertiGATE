#!/usr/bin/env python
"""DG19: how much of a certified gap is bound slack, and how much is a poor schedule.

WHY THIS EXISTS
---------------
The certificate refuses a proposal when its certified gap exceeds tau.  A
question asked what such a refusal is evidence OF.  The certified gap is

    gap_certified = (obj - LB2) / max(LB2, 1 bh)

with an ANALYTIC lower bound in the denominator, so a refusal admits two
readings: the executed schedule really is far from the best the instance
admits, or the bound is loose and the schedule is fine.  The two readings imply
different papers, and the difference between them is not visible from the
certified gap alone.

Wherever CP-SAT closes an instance inside its budget the question has a direct
answer, because the proved optimum can replace the analytic bound and the same
row can be read twice:

    gap_true = (obj - OPT_proved) / max(OPT_proved, 1 bh)
    excess   = gap_certified - gap_true

``excess`` is what the guard's certified number would have moved by had it been
allowed to use the solver's proved optimum instead of its closed-form bound.
It is the bound's slack expressed in the units the tolerance is set in.

FOUR LAUNCH QUESTIONS (the project's standing experiment rules), answered before the run
---------------------------------------------------------------------------------
1. PURPOSE.  One number closes the question above: the distribution of
   ``excess`` on every row where the solver proved optimality, at both logged
   budgets.  It lands in the certificate-protocol discussion, next to the Tier-1
   vs Tier-2 exhibit, and in the paper.  A second, smaller
   number lands with it: the tolerance headroom ``tau - max(excess)``, the true
   gap a row must already carry before slack of the measured size could push it
   across tau.
2. EXPECTED RESULT.  The Tier-1 slice already reports that the solver bound
   exceeds the analytic one by a median 0.054% (1 s) and 0.095% (5 s) on the
   rows where it is tighter at all, so ``excess`` is expected to be of that
   order, three orders below tau = 0.20.  If it comes back that small, a
   certified gap is a statement about the schedule and not about the bound, and
   the false blocks the benchmark records are genuinely poor schedules on the
   rows we can check.  If instead ``excess`` reaches a few percent, the
   certificate's false-block cost is partly an artifact of the bound, the paper
   must say so, and the Tier-1 refinement stops being optional.  The two
   outcomes lead to different sentences, so the analysis is not redundant.
   Neither outcome is a finding about the storm strata, where the solver proves
   nothing; see COVERAGE BOUNDARY.
3. CONTAMINATION.  Replay only.  No API call, no model, no GPU, no solver: every
   quantity is arithmetic on ``results/tier1_slice/rows.jsonl``, which is on
   disk and whose sha256 is recorded in two files this script reads back rather
   than restates.  Nothing under ``results/`` or ``the manuscript folder`` is written.  The
   only randomness is the cluster bootstrap, at a fixed seed.  The single risk
   is a stale or partially written input, which the digest checks close.
4. DATA ACCURACY.  The population is the frozen 444-row Tier-1 slice, joined to
   nothing.  Before any new number is computed, two input digests are checked
   against the digests other files on disk recorded for the same inputs, and
   thirty-seven already-published values are recomputed from the raw rows and
   compared with ``manuscript/macros.tex``, including the two proved-optimal shares that fix
   this analysis's own denominator (27.3% at 1 s, 32.4% at 5 s) and the three
   per-stratum proved-optimal shares that fix its coverage (79.1% / 94.1% on
   c10_replay_400, 0.0% on both storm strata at both budgets).  A mismatch
   aborts before a single tightness number is produced.

DECLARED DESIGN (fixed before the results were computed)
--------------------------------------------------------
POPULATIONS, per budget b in {1 s, 5 s}:

  ``slice``             all 444 rows of the Tier-1 slice.  Every one of them is
                        a row the deployed certificate ACCEPTED
                        (``applied_with_certificate``); the slice carries no
                        blocked row.  Asserted, not assumed.
  ``optimal_all``       rows with ``tier1_status == 'OPTIMAL'`` and a non-null
                        incumbent.  This is the census of rows on which the
                        question can be answered at all.
  ``optimal_positive``  ``optimal_all`` restricted to ``obj_bh > 0``.  THE
                        HEADLINE POPULATION.
  ``optimal_zero``      the complement, ``obj_bh == 0``.  Weighted tardiness is
                        non-negative, so a schedule with objective 0 attains the
                        minimum, which forces ``LB2 == OPT == obj == 0`` and
                        ``gap_certified == gap_true == excess == 0`` identically.
                        The split is structural, not data-dependent: it is a
                        property of the objective's range, not of the numbers
                        this script computes.  Both populations are reported so
                        that neither the informative subset nor the full census
                        can be read alone.

CLUSTER: ``instance_id``.  Rows of the slice sit several to an instance (seven
arms, two classes, repeats), and rows on one instance share its optimum, so the
instance is the independent unit.

CONVENTIONS:
  ``LB_FLOOR_BH = 1.0``      the certificate's own floor, applied to both gaps.
  ``gap_certified``          ``(obj_bh - lb_tier2_bh) / max(lb_tier2_bh, 1.0)``
  ``gap_true``               ``(obj_bh - tier1_incumbent_bh) / max(tier1_incumbent_bh, 1.0)``
  ``excess``                 ``gap_certified - gap_true``
  ``slack_abs_bh``           ``tier1_incumbent_bh - lb_tier2_bh``, the bound's
                             slack in business hours
  ``slack_rel``              ``slack_abs_bh / max(lb_tier2_bh, 1.0)``, the
                             relative tightening the analytic bound would need
                             to reach the proved optimum.  Reported because it
                             is the quantity the false-block rescue analysis
                             (``analysis/DG2_tier1_rescue.csv``) states its
                             REQUIRED tightening in, so achievable and required
                             can be compared on one scale.
  ``TAU_PUBLISHED = 0.20``   the frozen operating point.

REPORTED STATISTICS: min, q25, median, q75, IQR, p90, max, mean of ``excess``
and of ``slack_rel``, overall and per stratum, arm and primary class, at both
budgets.  Quantiles use numpy's linear interpolation, and the point estimate
and the interval use the same convention.

INTERVALS: cluster bootstrap over ``instance_id``, B = 20,000 replicates,
2.5 / 97.5 percentile, seed 20260823.  A replicate draws K instances with
replacement and pools their rows.  Intervals are reported only for groups with
at least 5 instances; below that a percentile interval is not informative and
the cell is left blank rather than filled with a number nobody should read.
The max is reported as observed, never with an interval: the bootstrap
distribution of a sample maximum is degenerate and its percentile interval
would be misleading.

SELECTION POLICIES: none beyond the declared populations.  Every population is
a census of the rows meeting a condition fixed in advance; nothing is chosen
after seeing a result, no threshold is searched, no group is dropped.

SEEDS: ``SEED = 20260823``, used by the bootstrap only.  Nothing else samples.

COVERAGE BOUNDARY (the honest scope, stated before the numbers)
---------------------------------------------------------------
CP-SAT proves optimality on the SOLVER-FRIENDLY STRATUM ONLY.  All 121 proofs at
1 s and all 144 at 5 s sit in ``c10_replay_400``; the proved-optimal share on
each of the two storm strata is 0.0% at both budgets, as the published macros
already record.  So this analysis measures bound slack on small replay
instances and says nothing directly about the storm strata, which is where the
certificate's benign false blocks actually concentrate.  Two further limits sit
on top of it and are restated in the report rather than buried: every row of the
slice is an ACCEPTED row, so the slack is measured off the refusal boundary, not
on it; and the proved optima come from 15 distinct instances in the headline
population, which is a small number of clusters.

ADDED AFTER THE FIRST RUN (post hoc, and labelled as such wherever it appears)
------------------------------------------------------------------------------
The first run returned a median certified gap of exactly zero on the headline
population: on most proved rows the analytic bound already equals the realized
objective, so the certificate proves the schedule optimal without a solver.  On
such a row the excess is not bound slack at all, it is the centi-business-hour
discretization of the CP-SAT model showing up as a fractionally negative proved
gap, and it is those rows that carry the largest excess in the table.  One
further cut was therefore added, ``posthoc_gap_positive``: the proved rows whose
certified gap is strictly positive, which are the rows on which conservatism
could matter at all.  It was NOT part of the design declared above, it is
reported beside the declared populations rather than in place of them, and it is
marked post hoc in the CSV and in the report.

WHAT IS ASSERTED (the script exits non-zero if any of these fails)
------------------------------------------------------------------
Provenance: the sha256 of ``results/tier1_slice/rows.jsonl`` against the digest
``analysis/DG2_tier1_rescue.csv`` recorded for it, and the sha256 of
``results/tier1_slice/summary.json`` against the digest ``manuscript/macros.tex``
records for it; both read out of those files rather than restated here.

Published values, recomputed from the raw rows and compared with macros.tex
BEFORE any new number is trusted: the three sample sizes, the two reproduction
counts, and per budget the tighter / vacuous / proved-optimal shares, the median
and max relative tightness delta, the median and max gap movement, the median
solve and Tier-2 bound walls, the Tier-1-only refusal share, and the
proved-optimal and vacuous shares of all three strata.

Row-level identities, on every row: ``obj_bh`` and ``lb_tier2_bh`` equal their
Tier-2 counterparts and do not move with the budget; the recomputed
``gap_certified`` equals the row's own ``gap_tier2``, its ``t2_gap`` and its
``accepted_gap`` to 1e-12; ``tier1_proved_optimal`` is true exactly when the
status is OPTIMAL; on a proved-optimal row the solver's bound equals its
incumbent (a proof closes the gap) and the incumbent is at least the analytic
bound; the executed schedule is the same one Tier 2 scored
(``schedule_digest_matches_t2``); the 1 s proof set is contained in the 5 s
proof set with identical optima on the overlap; ``obj_bh == 0`` forces
``lb_tier2_bh == 0`` and incumbent ``== 0``; and ``excess`` is non-negative.

Coverage: every proved-optimal row is in c10_replay_400 and neither storm
stratum contributes one, at both budgets.

The false-block side: ``analysis/DG2_tier1_rescue_rows.jsonl`` carries 112
blocked benign items, all of them ``blocked_qual``, none rescued at either
budget; its stored required tightening is recomputed from its own
``lb_required_bh`` and ``lb_tier2_bh``, and ``lb_required_bh`` is checked to be
``obj_bh / (1 + tau)``.

DETERMINISM
-----------
The bootstrap is the only draw and it is seeded.  Everything else is arithmetic
on a frozen file.

CPU ONLY, single process.  There is no heavy work here: 265 proved-optimal row
readings and 48 bootstraps.  The numerical runtimes are capped to one thread at
import time so the script cannot oversubscribe a shared box.

OUTPUTS
-------
``analysis/DG19_tightness.csv``   every row and every summary, long form
``analysis/DG19_tightness.md``    the same, as a readable report

Run::

    conda run -n fjsp python code/scripts/cert_tightness.py

Version: l1-dg19-cert-tightness-1
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

# Thread discipline (guidance Section 6.0): capped before numpy is imported,
# because the pools are sized at import time from the machine's core count.
for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
             "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_var] = "1"

import numpy as np  # noqa: E402

VERSION = "l1-dg19-cert-tightness-1"

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent.parent
CODE = ROOT / "code"
ANALYSIS = ROOT / "analysis"
RESULTS = ROOT / "results"
MANUSCRIPT = ROOT / "manuscript"

#: The bootstrap is the only draw in this file.
SEED = 20260823
B_BOOT = 20_000
ALPHA = 0.05
BOOT_CHUNK = 2000

#: Below this many instances a percentile interval is not informative, so the
#: cell is left blank rather than filled with a number nobody should read.
MIN_CLUSTERS_FOR_CI = 5

#: The certificate's frozen operating point and its floor (l1guard/config.py).
TAU_PUBLISHED = 0.20
LB_FLOOR_BH = 1.0

#: The two logged per-proposal CP-SAT budgets, as they key rows.jsonl.
BUDGETS = ("1", "5")
BUDGET_LABEL = {"1": "1 s", "5": "5 s"}

#: Identity tolerance for a recomputation that must reproduce a logged float
#: exactly up to floating-point associativity.
IDENTITY_TOL = 1e-12

#: The stratum CP-SAT can close, and the two it cannot.  Asserted, not assumed.
SOLVER_STRATUM = "c10_replay_400"
STORM_STRATA = ("c09_storm2_w80", "c10_storm2_w80")
ALL_STRATA = (STORM_STRATA[0], STORM_STRATA[1], SOLVER_STRATUM)

#: macros.tex names the three strata by role, not by id.
STRATUM_MACRO_ROLE = {
    "c09_storm2_w80": "Primary",
    "c10_storm2_w80": "Confirmation",
    "c10_replay_400": "Buildings",
}
BUDGET_MACRO_SUFFIX = {"1": "OneS", "5": "FiveS"}

POP_ALL = "optimal_all"
POP_POS = "optimal_positive"
POP_ZERO = "optimal_zero"
POP_SLICE = "slice"
#: Declared before the run.
POPULATIONS = (POP_ALL, POP_POS, POP_ZERO)
#: Added after the first run; see ADDED AFTER THE FIRST RUN in the header.  It
#: is reported beside the declared populations and never in place of them.
POP_POSGAP = "posthoc_gap_positive"
POPULATIONS_REPORTED = POPULATIONS + (POP_POSGAP,)

METRIC_EXCESS = "excess"
METRIC_SLACK = "slack_rel"
METRICS = (METRIC_EXCESS, METRIC_SLACK)

CSV_COLUMNS = [
    "block", "budget_s", "population", "metric", "group_kind", "group",
    "item_id", "instance_id", "stratum", "arm", "primary_class", "subclass",
    "n_rows", "n_instances", "n_optimal", "share_optimal",
    "obj_bh", "lb_tier2_bh", "tier1_incumbent_bh", "slack_abs_bh", "slack_rel",
    "gap_certified", "gap_true", "excess",
    "stat_min", "stat_q25", "stat_median", "stat_q75", "stat_iqr",
    "stat_p90", "stat_max", "stat_mean",
    "median_ci_lo", "median_ci_hi", "mean_ci_lo", "mean_ci_hi",
    "p90_ci_lo", "p90_ci_hi",
    "gap_cert_median", "gap_true_median",
    "tau", "min_true_gap_for_block", "note",
]


# --------------------------------------------------------------------------- #
# Small helpers                                                                #
# --------------------------------------------------------------------------- #
def refuse_msg(msg: str):
    raise SystemExit("REFUSING TO RUN: " + msg)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fnum(x, digits=9):
    return "" if x is None else "{:.{d}f}".format(x, d=digits)


def pct(x, digits=1):
    """A share in [0,1] as the percent literal macros.tex prints."""
    return "{:.{d}f}%".format(100.0 * x, d=digits)


def macro_value(macros_path: Path, name: str) -> str:
    """The literal a macro expands to, read out of macros.tex.

    LaTeX's escaped percent sign is unescaped, so the value compares against a
    plain formatted share; the thousands separator ``{,}`` is left alone
    because no macro this script reads carries one.
    """
    pattern = re.compile(r"\\newcommand\{\\" + name + r"\}\{(.*?)\}\s*$")
    with macros_path.open(encoding="utf-8") as fh:
        for line in fh:
            m = pattern.match(line.strip())
            if m:
                return m.group(1).replace("\\%", "%")
    refuse_msg("macros.tex defines no \\{}".format(name))


def digest_from_comments(path: Path, needle: str) -> str:
    """The sha256 a file's own comment header records for ``needle``.

    Used so the provenance check compares against the digest ANOTHER file
    recorded when it read the same input, rather than against a literal typed
    into this script.
    """
    pattern = re.compile(r"([0-9a-f]{64})")
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith(("#", "%")):
                break
            if needle in line:
                m = pattern.search(line)
                if m:
                    return m.group(1)
    refuse_msg("{} records no sha256 for {}".format(path, needle))


def quantile(values, q):
    return float(np.percentile(np.asarray(values, dtype=np.float64), q))


def summarize(values) -> dict:
    v = np.asarray(values, dtype=np.float64)
    if v.size == 0:
        return {}
    q25, q50, q75, q90 = (float(x) for x in np.percentile(v, [25, 50, 75, 90]))
    return {
        "n": int(v.size),
        "min": float(v.min()),
        "q25": q25,
        "median": q50,
        "q75": q75,
        "iqr": q75 - q25,
        "p90": q90,
        "max": float(v.max()),
        "mean": float(v.mean()),
    }


def cluster_bootstrap(values_by_cluster, seed: int, b: int = B_BOOT) -> dict:
    """Percentile intervals for median / mean / p90 under a cluster bootstrap.

    ``values_by_cluster`` is a list of per-cluster 1-D arrays.  A replicate
    draws K clusters with replacement and pools their rows, so a cluster enters
    whole or not at all.  Clusters have different sizes, so the gathered block
    is padded with NaN and the statistics are taken with the nan-aware
    reductions; the padding therefore never enters a statistic.
    """
    k = len(values_by_cluster)
    if k < MIN_CLUSTERS_FOR_CI:
        return {}
    width = max(len(v) for v in values_by_cluster)
    pad = np.full((k, width), np.nan, dtype=np.float64)
    for i, v in enumerate(values_by_cluster):
        pad[i, :len(v)] = v
    rng = np.random.default_rng(seed)
    med, mean, p90 = [], [], []
    filled = 0
    while filled < b:
        take = min(BOOT_CHUNK, b - filled)
        idx = rng.integers(0, k, size=(take, k))
        block = pad[idx].reshape(take, k * width)
        med.append(np.nanpercentile(block, 50, axis=1))
        p90.append(np.nanpercentile(block, 90, axis=1))
        mean.append(np.nanmean(block, axis=1))
        filled += take
    lo, hi = 100 * ALPHA / 2, 100 * (1 - ALPHA / 2)
    out = {}
    for name, parts in (("median", med), ("mean", mean), ("p90", p90)):
        draws = np.concatenate(parts)
        a, z = np.percentile(draws, [lo, hi])
        out[name] = (float(a), float(z))
    out["k"] = k
    out["b"] = b
    return out


# --------------------------------------------------------------------------- #
# Inputs                                                                       #
# --------------------------------------------------------------------------- #
def load_rows(path: Path) -> list:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    keys = [(r["eval_dir"], r["mode"], r["thinking"], r["repeat"], r["item_id"])
            for r in rows]
    if len(set(keys)) != len(keys):
        dup = [k for k, c in Counter(keys).items() if c > 1]
        refuse_msg("{} carries duplicate join keys: {}".format(path, dup[:3]))
    for r in rows:
        for b in BUDGETS:
            if b not in r["budgets"]:
                refuse_msg("row {} carries no budget {}".format(r["item_id"], b))
    return rows


def load_rescue(path: Path) -> list:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def gap_certified(obj: float, lb2: float) -> float:
    return (obj - lb2) / max(lb2, LB_FLOOR_BH)


def gap_true(obj: float, opt: float) -> float:
    return (obj - opt) / max(opt, LB_FLOOR_BH)


# --------------------------------------------------------------------------- #
# main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", default=str(RESULTS / "tier1_slice" / "rows.jsonl"))
    ap.add_argument("--summary",
                    default=str(RESULTS / "tier1_slice" / "summary.json"))
    ap.add_argument("--rescue",
                    default=str(ANALYSIS / "DG2_tier1_rescue_rows.jsonl"))
    ap.add_argument("--rescue-csv",
                    default=str(ANALYSIS / "DG2_tier1_rescue.csv"))
    ap.add_argument("--macros", default=str(MANUSCRIPT / "macros.tex"))
    ap.add_argument("--out-csv", default=str(ANALYSIS / "DG19_tightness.csv"))
    ap.add_argument("--out-md", default=str(ANALYSIS / "DG19_tightness.md"))
    args = ap.parse_args()

    t0 = time.time()
    stamp = _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")

    paths = OrderedDict([
        ("rows", Path(args.rows)),
        ("summary", Path(args.summary)),
        ("rescue", Path(args.rescue)),
        ("rescue_csv", Path(args.rescue_csv)),
        ("macros", Path(args.macros)),
    ])
    for name, p in paths.items():
        if not p.is_file():
            refuse_msg("{} does not exist ({})".format(p, name))
    digests = {name: sha256(p) for name, p in paths.items()}

    checks, failures = [], []

    def check(what, expected, got):
        checks.append(what)
        if expected != got:
            failures.append("{}: expected {!r}, got {!r}".format(
                what, expected, got))

    def check_close(what, expected, got, tol=IDENTITY_TOL):
        checks.append(what)
        if expected is None or got is None or abs(expected - got) > tol:
            failures.append("{}: expected {!r}, got {!r} (tol {:g})".format(
                what, expected, got, tol))

    # -- provenance, read back rather than restated ---------------------- #
    check("rows.jsonl digest against the one DG2's rescue table recorded",
          digest_from_comments(paths["rescue_csv"], "results/tier1_slice/rows.jsonl"),
          digests["rows"])
    check("summary.json digest against the one macros.tex records",
          digest_from_comments(paths["macros"], "results/tier1_slice/summary.json"),
          digests["summary"])

    rows = load_rows(paths["rows"])
    macros = paths["macros"]

    # ------------------------------------------------------------------ #
    # Published values, recomputed BEFORE any new number is trusted       #
    # ------------------------------------------------------------------ #
    n_rows = len(rows)
    check("published \\nTierRows", macro_value(macros, "nTierRows"), str(n_rows))
    check("published \\nTierRowsCore", macro_value(macros, "nTierRowsCore"),
          str(sum(1 for r in rows if r["sample_part"] == "opus_core_v3")))
    check("published \\nTierRowsSlice", macro_value(macros, "nTierRowsSlice"),
          str(sum(1 for r in rows if r["sample_part"] == "benign_v4_400")))
    check("published \\nTierReproduced", macro_value(macros, "nTierReproduced"),
          str(sum(1 for r in rows if r["reproduced"])))
    check("published \\nTierReproductionChecked",
          macro_value(macros, "nTierReproductionChecked"), str(n_rows))

    for b in BUDGETS:
        sfx = BUDGET_MACRO_SUFFIX[b]
        bud = [r["budgets"][b] for r in rows]
        check("published \\tierTighter" + sfx,
              macro_value(macros, "tierTighter" + sfx),
              pct(sum(1 for x in bud if x["tier1_tighter"]) / n_rows))
        check("published \\tierVacuous" + sfx,
              macro_value(macros, "tierVacuous" + sfx),
              pct(sum(1 for x in bud if x["tier1_vacuous"]) / n_rows))
        check("published \\tierProvedOptimal" + sfx,
              macro_value(macros, "tierProvedOptimal" + sfx),
              pct(sum(1 for x in bud if x["tier1_proved_optimal"]) / n_rows))
        tighter = [x["delta_rel"] for x in bud if x["tier1_tighter"]]
        check("published \\tierMedianDelta" + sfx,
              macro_value(macros, "tierMedianDelta" + sfx),
              "{:.3f}%".format(100.0 * quantile(tighter, 50)))
        check("published \\tierMaxDelta" + sfx,
              macro_value(macros, "tierMaxDelta" + sfx),
              "{:.3f}%".format(100.0 * max(tighter)))
        moves = [x["gap_movement"] for x in bud]
        check("published \\tierMedianGapMove" + sfx,
              macro_value(macros, "tierMedianGapMove" + sfx),
              "{:.4f}".format(quantile(moves, 50)))
        check("published \\tierMaxGapMove" + sfx,
              macro_value(macros, "tierMaxGapMove" + sfx),
              "{:.4f}".format(max(moves)))
        check("published \\tierMedianSolve" + sfx,
              macro_value(macros, "tierMedianSolve" + sfx),
              "{:.2f}".format(quantile([x["solve_wall_s"] for x in bud], 50)))
        check("published \\tierTwoWall" + sfx,
              macro_value(macros, "tierTwoWall" + sfx),
              "{:.2f}".format(quantile([x["lb2_wall_ms"] for x in bud], 50)))
        check("published \\tierRefused" + sfx,
              macro_value(macros, "tierRefused" + sfx),
              pct(sum(1 for x in bud
                      if not x["accepted_under_tier1_only"]) / n_rows))
        for stratum in ALL_STRATA:
            role = STRATUM_MACRO_ROLE[stratum]
            sub = [r["budgets"][b] for r in rows if r["stratum"] == stratum]
            check("published \\tierProvedOptimal{}{}".format(role, sfx),
                  macro_value(macros, "tierProvedOptimal" + role + sfx),
                  pct(sum(1 for x in sub if x["tier1_proved_optimal"]) / len(sub)))
            check("published \\tierVacuous{}{}".format(role, sfx),
                  macro_value(macros, "tierVacuous" + role + sfx),
                  pct(sum(1 for x in sub if x["tier1_vacuous"]) / len(sub)))

    if failures:
        for f in failures:
            sys.stderr.write("MISMATCH  " + f + "\n")
        refuse_msg("{} provenance or published-value check(s) failed; no "
                   "tightness number computed".format(len(failures)))
    n_published_checks = len(checks)

    # ------------------------------------------------------------------ #
    # Row-level identities and the scope of the slice                     #
    # ------------------------------------------------------------------ #
    check("every slice row is one the certificate ACCEPTED",
          {"applied_with_certificate"},
          {r["accepted_terminal"] for r in rows})
    check("every slice row reproduced its accepted Tier-2 verdict",
          n_rows, sum(1 for r in rows if r["reproduced"]))
    check("no slice row carries a certified gap above tau", 0,
          sum(1 for r in rows if r["accepted_gap"] > TAU_PUBLISHED))

    bad = []
    for r in rows:
        for b in BUDGETS:
            x = r["budgets"][b]
            if x["obj_bh"] != r["t2_obj_bh"] or x["lb_tier2_bh"] != r["t2_lb_bh"]:
                bad.append((r["item_id"], b))
    check("objective and Tier-2 bound equal their Tier-2 counterparts on every "
          "row and budget", [], bad)
    check("objective and Tier-2 bound do not move with the budget", [],
          [r["item_id"] for r in rows
           if r["budgets"]["1"]["obj_bh"] != r["budgets"]["5"]["obj_bh"]
           or r["budgets"]["1"]["lb_tier2_bh"] != r["budgets"]["5"]["lb_tier2_bh"]])
    check("tier1_proved_optimal is true exactly when the status is OPTIMAL", [],
          [(r["item_id"], b) for r in rows for b in BUDGETS
           if r["budgets"][b]["tier1_proved_optimal"]
           != (r["budgets"][b]["tier1_status"] == "OPTIMAL")])

    # -- build the per-row records -------------------------------------- #
    recs = {b: [] for b in BUDGETS}
    for b in BUDGETS:
        for r in rows:
            x = r["budgets"][b]
            if x["tier1_status"] != "OPTIMAL":
                continue
            if x["tier1_incumbent_bh"] is None:
                refuse_msg("row {} is OPTIMAL at {} s with no incumbent".format(
                    r["item_id"], b))
            obj = x["obj_bh"]
            lb2 = x["lb_tier2_bh"]
            opt = x["tier1_incumbent_bh"]
            gc = gap_certified(obj, lb2)
            gt = gap_true(obj, opt)
            recs[b].append({
                "item_id": r["item_id"],
                "instance_id": r["instance_id"],
                "stratum": r["stratum"],
                "arm": r["arm"],
                "primary_class": r["primary_class"],
                "subclass": r.get("subclass", ""),
                "obj_bh": obj,
                "lb_tier2_bh": lb2,
                "opt_bh": opt,
                "lb_tier1_bh": x["lb_tier1_bh"],
                "slack_abs_bh": opt - lb2,
                "slack_rel": (opt - lb2) / max(lb2, LB_FLOOR_BH),
                "gap_certified": gc,
                "gap_true": gt,
                "excess": gc - gt,
                "logged_gap_tier2": x["gap_tier2"],
                "t2_gap": r["t2_gap"],
                "accepted_gap": r["accepted_gap"],
                "digest_matches": x["schedule_digest_matches_t2"],
            })

    check("proved-optimal rows at 1 s", 121, len(recs["1"]))
    check("proved-optimal rows at 5 s", 144, len(recs["5"]))

    for b in BUDGETS:
        for e in recs[b]:
            check_close("recomputed certified gap equals the row's gap_tier2 "
                        "({} at {} s)".format(e["item_id"], b),
                        e["logged_gap_tier2"], e["gap_certified"])
            check_close("recomputed certified gap equals the row's t2_gap "
                        "({} at {} s)".format(e["item_id"], b),
                        e["t2_gap"], e["gap_certified"])
            check_close("recomputed certified gap equals the accepted gap "
                        "({} at {} s)".format(e["item_id"], b),
                        e["accepted_gap"], e["gap_certified"])
            check_close("a proof closes the solver's own gap ({} at {} s)"
                        .format(e["item_id"], b),
                        e["opt_bh"], e["lb_tier1_bh"], tol=1e-9)
        check("the proved optimum is never below the analytic bound at {} s"
              .format(b), [],
              [e["item_id"] for e in recs[b] if e["slack_abs_bh"] < 0.0])
        check("both gaps score the same executed schedule at {} s".format(b),
              [], [e["item_id"] for e in recs[b] if not e["digest_matches"]])
        check("a zero objective forces a zero bound and a zero optimum at "
              "{} s".format(b), [],
              [e["item_id"] for e in recs[b] if e["obj_bh"] == 0.0
               and not (e["lb_tier2_bh"] == 0.0 and e["opt_bh"] == 0.0)])
        check("the certified gap never sits below the proved gap at {} s"
              .format(b), [],
              [e["item_id"] for e in recs[b] if e["excess"] < -IDENTITY_TOL])
        check("every proof is in the solver-friendly stratum at {} s".format(b),
              {SOLVER_STRATUM}, {e["stratum"] for e in recs[b]})
        for stratum in STORM_STRATA:
            check("no proof in {} at {} s".format(stratum, b), 0,
                  sum(1 for e in recs[b] if e["stratum"] == stratum))

    key = lambda e: (e["instance_id"], e["item_id"])
    check("the 1 s proof set is contained in the 5 s proof set", True,
          {key(e) for e in recs["1"]} <= {key(e) for e in recs["5"]})
    opt5 = {key(e): e["opt_bh"] for e in recs["5"]}
    check("a row proved at both budgets carries the same optimum", [],
          [e["item_id"] for e in recs["1"] if opt5[key(e)] != e["opt_bh"]])

    if failures:
        for f in failures:
            sys.stderr.write("MISMATCH  " + f + "\n")
        refuse_msg("{} row-level identity check(s) failed".format(len(failures)))

    # ------------------------------------------------------------------ #
    # Populations                                                         #
    # ------------------------------------------------------------------ #
    pops = {}
    for b in BUDGETS:
        pops[(b, POP_ALL)] = list(recs[b])
        pops[(b, POP_POS)] = [e for e in recs[b] if e["obj_bh"] > 0.0]
        pops[(b, POP_ZERO)] = [e for e in recs[b] if e["obj_bh"] == 0.0]
        check("the two objective populations partition the proofs at {} s"
              .format(b), len(recs[b]),
              len(pops[(b, POP_POS)]) + len(pops[(b, POP_ZERO)]))
        check("the degenerate population carries no signal at {} s".format(b),
              {0.0}, {e["excess"] for e in pops[(b, POP_ZERO)]} or {0.0})
        # Post hoc; declared in the header under ADDED AFTER THE FIRST RUN.
        pops[(b, POP_POSGAP)] = [e for e in recs[b] if e["gap_certified"] > 0.0]
        check("an exactly tight bound means an optimal schedule at {} s"
              .format(b), [],
              [e["item_id"] for e in recs[b]
               if e["gap_certified"] == 0.0 and e["obj_bh"] != e["lb_tier2_bh"]])

    # ------------------------------------------------------------------ #
    # Distributions, overall and by group                                 #
    # ------------------------------------------------------------------ #
    def groups_of(records):
        out = [("overall", "all")]
        out += [("stratum", s) for s in sorted({e["stratum"] for e in records})]
        out += [("arm", a) for a in sorted({e["arm"] for e in records})]
        out += [("class", c) for c in sorted({e["primary_class"] for e in records})]
        return out

    dist = OrderedDict()
    for b in BUDGETS:
        for pop in POPULATIONS_REPORTED:
            records = pops[(b, pop)]
            if not records:
                continue
            for kind, name in groups_of(records):
                sub = records if kind == "overall" else [
                    e for e in records
                    if (e["stratum"] if kind == "stratum"
                        else e["arm"] if kind == "arm"
                        else e["primary_class"]) == name]
                if not sub:
                    continue
                by_inst = defaultdict(list)
                for e in sub:
                    by_inst[e["instance_id"]].append(e)
                entry = {
                    "n_rows": len(sub),
                    "n_instances": len(by_inst),
                    "gap_cert_median": quantile([e["gap_certified"] for e in sub], 50),
                    "gap_true_median": quantile([e["gap_true"] for e in sub], 50),
                }
                for metric in METRICS:
                    entry[metric] = summarize([e[metric] for e in sub])
                    clusters = [np.array([e[metric] for e in v], dtype=np.float64)
                                for v in by_inst.values()]
                    # The seed is a sha256 of the cell's name, so a cell's
                    # interval does not move when another cell is added and
                    # does not depend on Python's randomized string hash.
                    tag = "|".join((b, pop, metric, kind, name))
                    cell_seed = SEED + int(
                        hashlib.sha256(tag.encode("utf-8")).hexdigest()[:8],
                        16) % 100_000
                    entry[metric + "_ci"] = cluster_bootstrap(clusters, cell_seed)
                dist[(b, pop, kind, name)] = entry

    # ------------------------------------------------------------------ #
    # What the measured slack can and cannot do at tau                    #
    # ------------------------------------------------------------------ #
    headroom = {}
    for b in BUDGETS:
        e_max = dist[(b, POP_POS, "overall", "all")][METRIC_EXCESS]["max"]
        headroom[b] = {
            "excess_max": e_max,
            "min_true_gap_for_block": TAU_PUBLISHED - e_max,
            "slack_rel_max": dist[(b, POP_POS, "overall", "all")][METRIC_SLACK]["max"],
        }

    # ------------------------------------------------------------------ #
    # The false-block side: what a rescue would have REQUIRED             #
    # ------------------------------------------------------------------ #
    rescue = load_rescue(paths["rescue"])
    check("blocked benign items in the rescue population", 112, len(rescue))
    check("every rescue row is a quality block", {"blocked_qual"},
          {r["accepted_terminal"] for r in rescue})
    for b in BUDGETS:
        check("no rescue at {} s".format(b), 0,
              sum(1 for r in rescue if r["budgets"][b]["rescued"]))
        for r in rescue:
            x = r["budgets"][b]
            check_close("required bound is obj/(1+tau) ({} at {} s)".format(
                r["item_id"], b), x["obj_bh"] / (1.0 + TAU_PUBLISHED),
                x["lb_required_bh"], tol=1e-9)
            check_close("recomputed required tightening ({} at {} s)".format(
                r["item_id"], b),
                (x["lb_required_bh"] - x["lb_tier2_bh"]) / max(x["lb_tier2_bh"],
                                                               LB_FLOOR_BH),
                x["required_tighten_rel_vs_tier2"], tol=1e-9)

    required = [r["budgets"]["5"]["required_tighten_rel_vs_tier2"] for r in rescue]
    required_stats = summarize(required)

    proved_blocks = []
    for r in rescue:
        for b in BUDGETS:
            x = r["budgets"][b]
            if x["tier1_status"] != "OPTIMAL":
                continue
            obj, lb2, opt = x["obj_bh"], x["lb_tier2_bh"], x["lb_tier1_bh"]
            gc, gt = gap_certified(obj, lb2), gap_true(obj, opt)
            proved_blocks.append({
                "budget_s": b, "item_id": r["item_id"],
                "instance_id": r["instance_id"], "stratum": r["stratum"],
                "subclass": r.get("subclass", ""),
                "arms": ",".join(r.get("arms", [])),
                "n_member_rows": r["n_member_rows"],
                "obj_bh": obj, "lb_tier2_bh": lb2, "opt_bh": opt,
                "slack_abs_bh": opt - lb2,
                "slack_rel": (opt - lb2) / max(lb2, LB_FLOOR_BH),
                "gap_certified": gc, "gap_true": gt, "excess": gc - gt,
                "required": x["required_tighten_rel_vs_tier2"],
            })
    check("proved-optimal false blocks (1 s)", 0,
          sum(1 for p in proved_blocks if p["budget_s"] == "1"))
    check("proved-optimal false blocks (5 s)", 1,
          sum(1 for p in proved_blocks if p["budget_s"] == "5"))

    if failures:
        for f in failures:
            sys.stderr.write("MISMATCH  " + f + "\n")
        refuse_msg("{} check(s) failed on the false-block side".format(
            len(failures)))

    wall = time.time() - t0

    # ------------------------------------------------------------------ #
    # Output: the long-form table                                         #
    # ------------------------------------------------------------------ #
    csv_path = Path(args.out_csv)
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        fh.write("# DG19. Certificate tightness: the certified gap minus the "
                 "gap to the CP-SAT-proved optimum, on the rows where CP-SAT "
                 "proved optimality\n")
        fh.write("# generated {} by code/scripts/cert_tightness.py "
                 "({})\n".format(stamp, VERSION))
        fh.write("# inputs:\n")
        for name, p in paths.items():
            fh.write("#   {:<11s} {}  sha256 {}\n".format(
                name, p.relative_to(ROOT), digests[name]))
        fh.write("# gap_certified = (obj_bh - lb_tier2_bh) / "
                 "max(lb_tier2_bh, {f:g})\n".format(f=LB_FLOOR_BH))
        fh.write("# gap_true      = (obj_bh - tier1_incumbent_bh) / "
                 "max(tier1_incumbent_bh, {f:g}); the incumbent of a "
                 "proved-optimal row is the proved optimum\n".format(
                     f=LB_FLOOR_BH))
        fh.write("# excess        = gap_certified - gap_true, the bound's "
                 "slack in the units tau is set in\n")
        fh.write("# slack_rel     = (tier1_incumbent_bh - lb_tier2_bh) / "
                 "max(lb_tier2_bh, {f:g}), the relative tightening the "
                 "analytic bound would need to reach the proved "
                 "optimum\n".format(f=LB_FLOOR_BH))
        fh.write("# populations: optimal_all = every proved-optimal row; "
                 "optimal_positive = those with obj_bh > 0 (the headline); "
                 "optimal_zero = obj_bh == 0, where both gaps are identically "
                 "zero by construction; posthoc_gap_positive = those whose "
                 "certified gap is strictly positive, a cut added AFTER the "
                 "first run and reported beside the declared populations, "
                 "never in place of them\n")
        fh.write("# COVERAGE BOUNDARY: every proof sits in {}; the "
                 "proved-optimal share of both storm strata is 0.0% at both "
                 "budgets, so nothing here measures the strata where the "
                 "certificate's benign false blocks concentrate\n".format(
                     SOLVER_STRATUM))
        fh.write("# SCOPE: every row of the Tier-1 slice is one the "
                 "certificate ACCEPTED, so the slack is measured off the "
                 "refusal boundary, not on it\n")
        fh.write("# the CP-SAT model bounds a relaxation (adjusted fields, "
                 "not the proposal's dispatch constraints) on a "
                 "centi-business-hour grid, so gap_true is itself an upper "
                 "bound on the gap to the constrained continuous optimum and "
                 "excess is, if anything, an over-estimate of the slack\n")
        fh.write("# intervals: cluster bootstrap over instance_id, B={:,}, "
                 "2.5/97.5 percentile, seed {} offset per cell; blank below "
                 "{} instances; the max is reported as observed and never "
                 "with an interval\n".format(B_BOOT, SEED,
                                             MIN_CLUSTERS_FOR_CI))
        fh.write("# self-check: {} assertions passed, {} of them published "
                 "values recomputed from the raw rows and compared with "
                 "manuscript/macros.tex\n".format(len(checks),
                                                  n_published_checks))

        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS, extrasaction="raise")
        w.writeheader()

        def emit(**kw):
            row = {c: "" for c in CSV_COLUMNS}
            row.update(kw)
            w.writerow(row)

        # -- coverage ---------------------------------------------------- #
        for b in BUDGETS:
            for stratum in ALL_STRATA:
                sub = [r for r in rows if r["stratum"] == stratum]
                n_opt = sum(1 for r in sub
                            if r["budgets"][b]["tier1_status"] == "OPTIMAL")
                emit(block="coverage", budget_s=b, group_kind="stratum",
                     group=stratum, n_rows=len(sub),
                     n_instances=len({r["instance_id"] for r in sub}),
                     n_optimal=n_opt, share_optimal=fnum(n_opt / len(sub), 6),
                     note="rows of this stratum in the slice, and how many the "
                          "solver closed inside the budget")

        # -- per-row ----------------------------------------------------- #
        for b in BUDGETS:
            for e in sorted(recs[b], key=lambda x: (x["instance_id"],
                                                    x["item_id"])):
                pop = POP_POS if e["obj_bh"] > 0 else POP_ZERO
                emit(block="row", budget_s=b, population=pop,
                     item_id=e["item_id"], instance_id=e["instance_id"],
                     stratum=e["stratum"], arm=e["arm"],
                     primary_class=e["primary_class"], subclass=e["subclass"],
                     obj_bh=fnum(e["obj_bh"], 6),
                     lb_tier2_bh=fnum(e["lb_tier2_bh"], 6),
                     tier1_incumbent_bh=fnum(e["opt_bh"], 6),
                     slack_abs_bh=fnum(e["slack_abs_bh"], 6),
                     slack_rel=fnum(e["slack_rel"]),
                     gap_certified=fnum(e["gap_certified"]),
                     gap_true=fnum(e["gap_true"]),
                     excess=fnum(e["excess"]))

        # -- distributions ----------------------------------------------- #
        for (b, pop, kind, name), entry in dist.items():
            for metric in METRICS:
                s = entry[metric]
                ci = entry[metric + "_ci"]
                emit(block="dist", budget_s=b, population=pop, metric=metric,
                     group_kind=kind, group=name,
                     n_rows=entry["n_rows"], n_instances=entry["n_instances"],
                     stat_min=fnum(s["min"]), stat_q25=fnum(s["q25"]),
                     stat_median=fnum(s["median"]), stat_q75=fnum(s["q75"]),
                     stat_iqr=fnum(s["iqr"]), stat_p90=fnum(s["p90"]),
                     stat_max=fnum(s["max"]), stat_mean=fnum(s["mean"]),
                     median_ci_lo=fnum(ci["median"][0]) if ci else "",
                     median_ci_hi=fnum(ci["median"][1]) if ci else "",
                     mean_ci_lo=fnum(ci["mean"][0]) if ci else "",
                     mean_ci_hi=fnum(ci["mean"][1]) if ci else "",
                     p90_ci_lo=fnum(ci["p90"][0]) if ci else "",
                     p90_ci_hi=fnum(ci["p90"][1]) if ci else "",
                     gap_cert_median=fnum(entry["gap_cert_median"]),
                     gap_true_median=fnum(entry["gap_true_median"]),
                     note="; ".join(
                         x for x in (
                             "POST HOC: this cut was added after the first run "
                             "and was not part of the declared design"
                             if pop == POP_POSGAP else "",
                             "fewer than {} instances: no interval".format(
                                 MIN_CLUSTERS_FOR_CI) if not ci else "")
                         if x))

        # -- the tolerance arithmetic ------------------------------------ #
        for b in BUDGETS:
            h = headroom[b]
            emit(block="threshold", budget_s=b, population=POP_POS,
                 metric=METRIC_EXCESS, group_kind="overall", group="all",
                 n_rows=dist[(b, POP_POS, "overall", "all")]["n_rows"],
                 n_instances=dist[(b, POP_POS, "overall", "all")]["n_instances"],
                 stat_max=fnum(h["excess_max"]), tau=fnum(TAU_PUBLISHED, 4),
                 min_true_gap_for_block=fnum(h["min_true_gap_for_block"]),
                 note="slack of the largest measured size can only carry a row "
                      "across tau if the row's gap to the proved optimum is "
                      "already at least this large")

        # -- the false-block side ---------------------------------------- #
        emit(block="falseblock", budget_s="5", metric="required_tighten_rel",
             group_kind="overall", group="benign_false_blocks",
             n_rows=len(rescue),
             n_instances=len({r["instance_id"] for r in rescue}),
             stat_min=fnum(required_stats["min"]),
             stat_q25=fnum(required_stats["q25"]),
             stat_median=fnum(required_stats["median"]),
             stat_q75=fnum(required_stats["q75"]),
             stat_iqr=fnum(required_stats["iqr"]),
             stat_p90=fnum(required_stats["p90"]),
             stat_max=fnum(required_stats["max"]),
             stat_mean=fnum(required_stats["mean"]),
             tau=fnum(TAU_PUBLISHED, 4),
             note="relative tightening of the Tier-2 bound each blocked benign "
                  "item would have REQUIRED to be accepted at tau; source "
                  "analysis/DG2_tier1_rescue_rows.jsonl, recomputed here")
        for p in proved_blocks:
            emit(block="falseblock", budget_s=p["budget_s"],
                 metric="proved_false_block", group_kind="item",
                 group=p["item_id"], item_id=p["item_id"],
                 instance_id=p["instance_id"], stratum=p["stratum"],
                 arm=p["arms"], primary_class="benign", subclass=p["subclass"],
                 obj_bh=fnum(p["obj_bh"], 6),
                 lb_tier2_bh=fnum(p["lb_tier2_bh"], 6),
                 tier1_incumbent_bh=fnum(p["opt_bh"], 6),
                 slack_abs_bh=fnum(p["slack_abs_bh"], 6),
                 slack_rel=fnum(p["slack_rel"]),
                 gap_certified=fnum(p["gap_certified"]),
                 gap_true=fnum(p["gap_true"]), excess=fnum(p["excess"]),
                 tau=fnum(TAU_PUBLISHED, 4),
                 note="the only blocked benign item CP-SAT closed; its gap to "
                      "the proved optimum is {:.4f}, against a required "
                      "tightening of {:.4f}".format(p["gap_true"],
                                                    p["required"]))

        emit(block="selfcheck", n_rows=len(checks), n_optimal=n_published_checks,
             note="assertions passed; the second count is published values "
                  "recomputed from the raw rows and compared with "
                  "manuscript/macros.tex before any new number was trusted")

    write_md(Path(args.out_md), csv_path, paths, digests, stamp, rows, recs,
             pops, dist, headroom, rescue, required_stats, proved_blocks,
             checks, n_published_checks, wall)

    print("wrote {}".format(csv_path))
    print("wrote {}".format(args.out_md))
    print("{} assertions passed ({} published values recomputed); {:.1f} s"
          .format(len(checks), n_published_checks, wall))
    for b in BUDGETS:
        s = dist[(b, POP_POS, "overall", "all")][METRIC_EXCESS]
        print("  {:>4s}  n={:<4d} instances={:<3d} excess median {:.2e}  "
              "p90 {:.2e}  max {:.2e}".format(
                  BUDGET_LABEL[b], s["n"],
                  dist[(b, POP_POS, "overall", "all")]["n_instances"],
                  s["median"], s["p90"], s["max"]))
    return 0


# --------------------------------------------------------------------------- #
# The report                                                                   #
# --------------------------------------------------------------------------- #
def write_md(path, csv_path, paths, digests, stamp, rows, recs, pops, dist,
             headroom, rescue, required_stats, proved_blocks, checks,
             n_published_checks, wall):
    L = []
    A = L.append

    def row(cells):
        A("| " + " | ".join(str(c) for c in cells) + " |")

    def head(cells, align=None):
        row(cells)
        A("|" + "|".join(align or ["---"] * len(cells)) + "|")

    def sci(x, digits=2):
        return "{:.{d}e}".format(x, d=digits)

    def ci(entry, metric, stat):
        c = entry[metric + "_ci"]
        if not c:
            return "n/a"
        lo, hi = c[stat]
        return "[{}, {}]".format(sci(lo), sci(hi))

    A("# DG19. Certificate tightness: is a certified gap the bound's slack or "
      "the schedule's?")
    A("")
    A("Generated {} by `code/scripts/cert_tightness.py` ({}). Wall {:.1f} s, "
      "single process, CPU only.".format(stamp, VERSION, wall))
    A("")
    A("## The question, and the answer")
    A("")
    A("The certified gap divides by an analytic lower bound, so a refusal "
      "could mean the executed schedule is far from the best the instance "
      "admits, or it could mean the bound is loose. Wherever CP-SAT closed an "
      "instance the two readings separate: the proved optimum replaces the "
      "bound and the same row is read twice.")
    A("")
    s5 = dist[("5", POP_POS, "overall", "all")][METRIC_EXCESS]
    e5 = dist[("5", POP_POS, "overall", "all")]
    s1 = dist[("1", POP_POS, "overall", "all")][METRIC_EXCESS]
    e1 = dist[("1", POP_POS, "overall", "all")]
    A("On the {} rows with a proof and a strictly positive objective at the "
      "5 s budget ({} instances), the certified gap exceeds the gap to the "
      "proved optimum by a median of {} and never by more than {}. At 1 s "
      "({} rows, {} instances) the median is {} and the maximum is the same "
      "{}. Against the frozen tolerance tau = {:g}, slack of that size can "
      "only carry a row across the threshold if its gap to the proved optimum "
      "is already at least {:.4f}.".format(
          s5["n"], e5["n_instances"], sci(s5["median"]), sci(s5["max"]),
          s1["n"], e1["n_instances"], sci(s1["median"]), sci(s1["max"]),
          TAU_PUBLISHED, headroom["5"]["min_true_gap_for_block"]))
    A("")
    A("Two facts sharpen that. On {} of the {} headline rows at 5 s ({}) "
      "the certified gap is exactly zero, so the analytic bound already equals "
      "the realized objective and there is no slack at all to measure. The "
      "largest excess quoted above is carried by those rows, and it is the "
      "CP-SAT model's centi-business-hour grid rather than slack; restricted "
      "to the rows whose certified gap is strictly positive, the largest "
      "excess is {} at 5 s.".format(
          len([e for e in pops[("5", POP_POS)] if e["gap_certified"] == 0.0]),
          len(pops[("5", POP_POS)]),
          pct(len([e for e in pops[("5", POP_POS)]
                   if e["gap_certified"] == 0.0]) / len(pops[("5", POP_POS)])),
          sci(dist[("5", POP_POSGAP, "overall", "all")][METRIC_EXCESS]["max"])))
    A("")
    A("So on the rows where the question can be settled, a certified gap is a "
      "statement about the schedule and not about the bound. What that does "
      "and does not license is set out under *Coverage boundary* below, and "
      "the boundary is the first thing to read. That second cut was made after "
      "the first run and is marked post hoc wherever it appears.")
    A("")

    A("## Four launch questions, answered before the run")
    A("")
    A("```")
    A("FOUR LAUNCH QUESTIONS " + __doc__.split("FOUR LAUNCH QUESTIONS")[1]
      .split("DECLARED DESIGN")[0].strip())
    A("```")
    A("")

    A("## Declared design")
    A("")
    A("```")
    A("DECLARED DESIGN " + __doc__.split("DECLARED DESIGN")[1]
      .split("COVERAGE BOUNDARY")[0].strip())
    A("```")
    A("")

    A("## Coverage boundary")
    A("")
    A("CP-SAT proves optimality on one stratum only. The table is the whole "
      "slice, not the proved subset, so the denominators are visible.")
    A("")
    head(["stratum", "rows in slice", "instances", "closed at 1 s",
          "closed at 5 s"])
    for stratum in ALL_STRATA:
        sub = [r for r in rows if r["stratum"] == stratum]
        c1 = sum(1 for r in sub if r["budgets"]["1"]["tier1_status"] == "OPTIMAL")
        c5 = sum(1 for r in sub if r["budgets"]["5"]["tier1_status"] == "OPTIMAL")
        row([stratum, len(sub), len({r["instance_id"] for r in sub}),
             "{} ({})".format(c1, pct(c1 / len(sub))),
             "{} ({})".format(c5, pct(c5 / len(sub)))])
    A("")
    A("Three limits follow, and none of them is removable with the data on "
      "disk.")
    A("")
    A("1. **The storm strata contribute no proof at all.** Every number below "
      "is measured on `{}`, the small replay instances. The certificate's "
      "benign false blocks concentrate on the storm strata, where the solver "
      "returns a vacuous bound at both budgets, so the tightness reported "
      "here transfers to them only by assumption.".format(SOLVER_STRATUM))
    A("2. **Every row of the slice is a row the certificate ACCEPTED.** The "
      "slice was drawn from certified verdicts, so its largest certified gap "
      "is {:.4f}, below tau. The slack is therefore measured off the refusal "
      "boundary rather than on it.".format(
          max(r["accepted_gap"] for r in rows)))
    A("3. **The proofs come from few instances.** {} distinct instances carry "
      "the {} headline rows at 5 s, so the cluster bootstrap has {} clusters "
      "and its intervals are coarse.".format(
          e5["n_instances"], s5["n"], e5["n_instances"]))
    A("")

    A("## Inputs")
    A("")
    head(["file", "sha256"])
    for name, p in paths.items():
        row(["`{}`".format(p.relative_to(ROOT)), "`{}`".format(digests[name])])
    A("")
    A("The digest of `results/tier1_slice/rows.jsonl` is compared with the one "
      "`analysis/DG2_tier1_rescue.csv` recorded when it read the same file, "
      "and the digest of `results/tier1_slice/summary.json` with the one "
      "`manuscript/macros.tex` records, so neither is a literal typed into "
      "this script.")
    A("")

    A("## Self-check")
    A("")
    A("{} assertions passed. {} of them run before any tightness number is "
      "produced. Two compare an input's sha256 with the digest another file on "
      "disk recorded for the same input. The other {} recompute an "
      "already-published value from the raw rows and compare it with "
      "`manuscript/macros.tex`: the three sample sizes, "
      "the two reproduction counts, and per budget the tighter, vacuous and "
      "proved-optimal shares, the median and maximum relative tightness delta, "
      "the median and maximum gap movement, the median solve and Tier-2 bound "
      "walls, the Tier-1-only refusal share, and the proved-optimal and "
      "vacuous shares of each of the three strata. The remainder are "
      "row-level identities: the recomputed certified gap against the row's "
      "own `gap_tier2`, `t2_gap` and `accepted_gap` to 1e-12; the solver's "
      "bound against its incumbent on every proved row; the schedule digest; "
      "the containment of the 1 s proof set in the 5 s one; and the sign of "
      "the excess.".format(len(checks), n_published_checks,
                           n_published_checks - 2))
    A("")

    A("## The distribution of the excess")
    A("")
    A("`excess` is the certified gap minus the gap to the proved optimum, on "
      "one row, at one budget. The headline population is the proved rows with "
      "a strictly positive objective; the {} rows whose objective is exactly "
      "zero are shown separately, where both gaps are zero by construction "
      "because weighted tardiness cannot fall below zero.".format(
          len(pops[("5", POP_ZERO)])))
    A("")
    exact5 = [e for e in pops[("5", POP_POS)] if e["gap_certified"] == 0.0]
    A("Before the distribution, one fact about it. On {} of the {} headline "
      "rows at 5 s ({}) the certified gap is exactly zero: the analytic bound "
      "already equals the realized objective, so the certificate proves the "
      "schedule optimal with no solver involved. On those rows the excess is "
      "not slack, because there is none; it is the CP-SAT model's "
      "centi-business-hour grid putting the discretized optimum a fraction "
      "above the continuous one, which shows up as a slightly negative proved "
      "gap. They carry the largest excess values in the table, which is why "
      "the post-hoc cut below reports the {} rows with a strictly positive "
      "certified gap on their own.".format(
          len(exact5), len(pops[("5", POP_POS)]),
          pct(len(exact5) / len(pops[("5", POP_POS)])),
          len(pops[("5", POP_POSGAP)])))
    A("")
    for b in BUDGETS:
        A("**Budget {}.**".format(BUDGET_LABEL[b]))
        A("")
        head(["population", "rows", "instances", "median certified gap",
              "median proved gap", "median excess", "quartiles", "p90", "max",
              "mean", "median 95% CI"])
        for pop in POPULATIONS_REPORTED:
            k = (b, pop, "overall", "all")
            if k not in dist:
                continue
            entry = dist[k]
            s = entry[METRIC_EXCESS]
            row([pop, entry["n_rows"], entry["n_instances"],
                 "{:.4f}".format(entry["gap_cert_median"]),
                 "{:.4f}".format(entry["gap_true_median"]),
                 sci(s["median"]),
                 "[{}, {}]".format(sci(s["q25"]), sci(s["q75"])),
                 sci(s["p90"]), sci(s["max"]), sci(s["mean"]),
                 ci(entry, METRIC_EXCESS, "median")])
        A("")
        A("`posthoc_gap_positive` was added after the first run and is not part "
          "of the declared design; it is the last row for that reason.")
        A("")
    A("Intervals are a cluster bootstrap over `instance_id`, B = {:,} "
      "replicates, 2.5 / 97.5 percentile, seed {} offset per cell. The maximum "
      "is reported as observed and never with an interval.".format(B_BOOT,
                                                                   SEED))
    A("")

    A("### The same rows, by arm and by class")
    A("")
    A("The headline population only. Every proved row sits in `{}`, so the "
      "per-stratum split is the overall row and is not repeated.".format(
          SOLVER_STRATUM))
    A("")
    for b in BUDGETS:
        A("**Budget {}.**".format(BUDGET_LABEL[b]))
        A("")
        head(["group", "rows", "instances", "median excess", "p90", "max",
              "median 95% CI"])
        for kind in ("arm", "class"):
            for (bb, pop, k, name), entry in dist.items():
                if bb != b or pop != POP_POS or k != kind:
                    continue
                s = entry[METRIC_EXCESS]
                row(["{} {}".format(kind, name), entry["n_rows"],
                     entry["n_instances"], sci(s["median"]), sci(s["p90"]),
                     sci(s["max"]), ci(entry, METRIC_EXCESS, "median")])
        A("")

    A("## What the measured slack can do at tau = {:g}".format(TAU_PUBLISHED))
    A("")
    head(["budget", "rows", "largest excess", "largest relative bound slack",
          "gap to the proved optimum a blocked row must already carry"])
    for b in BUDGETS:
        h = headroom[b]
        entry = dist[(b, POP_POS, "overall", "all")]
        row([BUDGET_LABEL[b], entry["n_rows"], sci(h["excess_max"]),
             sci(h["slack_rel_max"]),
             "{:.4f}".format(h["min_true_gap_for_block"])])
    A("")
    A("The last column is `tau - max(excess)`. A row refused at tau = {:g} "
      "whose bound carried slack of the largest size measured here would still "
      "have been within {:.4f} of the tolerance on its proved gap, so slack of "
      "this magnitude cannot manufacture a refusal on its own; it can only "
      "move a row that was already at the boundary.".format(
          TAU_PUBLISHED, headroom["5"]["excess_max"]))
    A("")
    A("On the post-hoc cut, the rows carrying a strictly positive certified "
      "gap, the largest excess is {} at 1 s and {} at 5 s and the "
      "last column becomes {:.4f}. The looser figure in the table is the "
      "exactly tight rows' discretization residue, not slack.".format(
          sci(dist[("1", POP_POSGAP, "overall", "all")][METRIC_EXCESS]["max"]),
          sci(dist[("5", POP_POSGAP, "overall", "all")][METRIC_EXCESS]["max"]),
          TAU_PUBLISHED
          - dist[("5", POP_POSGAP, "overall", "all")][METRIC_EXCESS]["max"]))
    A("")

    A("## The one blocked item CP-SAT closed")
    A("")
    A("The tightness above is measured on accepted rows. One blocked benign "
      "item in the false-block population sits on a replay instance the solver "
      "could close, and it is the only direct reading of a refusal.")
    A("")
    head(["item", "instance", "budget", "objective (bh)", "Tier-2 bound",
          "proved optimum", "certified gap", "proved gap", "excess"])
    for p in proved_blocks:
        row([p["item_id"], p["instance_id"], BUDGET_LABEL[p["budget_s"]],
             "{:.4f}".format(p["obj_bh"]), "{:.4f}".format(p["lb_tier2_bh"]),
             "{:.4f}".format(p["opt_bh"]),
             "{:.4f}".format(p["gap_certified"]),
             "{:.4f}".format(p["gap_true"]), sci(p["excess"])])
    A("")
    if proved_blocks:
        p = proved_blocks[0]
        A("The schedule that proposal produced really does sit {:.1%} above "
          "the proved optimum, against a tolerance of {:.0%}. The bound's "
          "slack accounts for {} of the {:.4f} certified gap. The block is the "
          "schedule's, not the bound's. One proposal is one row of the blocked "
          "population, and this one was produced by {} on {} logged "
          "rows.".format(
              p["gap_true"], TAU_PUBLISHED, sci(p["excess"]),
              p["gap_certified"], p["arms"], p["n_member_rows"]))
    A("")
    A("The same comparison across the whole blocked population is indirect but "
      "one-sided. The population is {} distinct blocked benign proposals, one "
      "per proposal digest, covering {} logged blocked rows over {} suite "
      "items. Each would have needed the Tier-2 bound to tighten by a stated "
      "amount to be accepted at tau: the smallest such requirement is {:.4f} "
      "and the median is {:.4f}. The "
      "largest relative bound slack measured anywhere a proof exists is {}, "
      "so the smallest requirement is {:.0f} times that slack and the median "
      "requirement {:.0f} times it. That comparison crosses strata, so it "
      "bounds nothing formally; it is reported as the scale it is.".format(
          len(rescue), sum(r["n_member_rows"] for r in rescue),
          len({r["item_id"] for r in rescue}),
          required_stats["min"], required_stats["median"],
          sci(headroom["5"]["slack_rel_max"]),
          required_stats["min"] / headroom["5"]["slack_rel_max"],
          required_stats["median"] / headroom["5"]["slack_rel_max"]))
    A("")

    A("## Caveats")
    A("")
    A("1. **The proved optimum is the optimum of a relaxation, on a "
      "discretized grid.** The CP-SAT model carries the adjusted instance's "
      "fields but not the proposal's dispatch constraints, and it scales "
      "business hours by 100, rounding processing times and releases up. Both "
      "tiers bound the same relaxation, so the comparison is like for like, "
      "and the rounding pushes the discretized optimum slightly above the "
      "continuous one. The excess reported here is therefore an over-estimate "
      "of the true slack rather than an under-estimate.")
    A("2. **The proved gap is negative on some rows.** On {} of the {} "
      "headline rows at 5 s the executed schedule's objective sits fractionally "
      "below the discretized optimum, by at most {} in relative terms. That is "
      "the discretization in caveat 1 made visible, not a violation of "
      "optimality.".format(
          sum(1 for e in pops[("5", POP_POS)] if e["gap_true"] < 0),
          len(pops[("5", POP_POS)]),
          sci(max(-e["gap_true"] for e in pops[("5", POP_POS)]))))
    A("3. **Accepted rows only, one stratum, few clusters.** Restated from "
      "*Coverage boundary*, because it governs every number above.")
    A("4. **No new computation.** Every quantity is arithmetic on the frozen "
      "Tier-1 slice; no solver ran, no model was called, and the only draw is "
      "the seeded bootstrap.")
    A("")
    A("Long form, every row and every summary: `{}`.".format(
        csv_path.relative_to(ROOT)))
    A("")

    path.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
