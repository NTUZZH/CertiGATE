#!/usr/bin/env python
"""DG16: instance-selection sensitivity of the direct benchmark's headline rates.

WHY THIS EXISTS
---------------
The direct benchmark's two headline numbers are read off 2,000 items that sit
on only 60 scheduling instances, and both numbers are class shares pooled over
those instances.  A reader is entitled to ask how much of each number is a
property of the guard and how much is a property of the particular sixty
instances the suite happens to carry.  This script answers that by deleting
one instance at a time and recomputing every published rate on what is left,
and it repeats the exercise for the two other ways the suite is partitioned:
its three strata and its thirty-three subclasses.

THE FOUR LAUNCH ANSWERS (written before the run, per the house rule)
--------------------------------------------------------------------
1. PURPOSE.  Quantify how far the direct benchmark's published rates move when
   any one instance, stratum or subclass is removed, and name the units that
   move them.  The numbers land in the manuscript as a one- or two-sentence
   robustness statement next to the published direct-benchmark table, and in
   the Supplemental Materials as the envelope table this script writes.  There
   is no new experiment and no new model call: this is a re-read of a log the
   paper already publishes.
2. IDEAL RESULT.  Every rate stays inside a band a reader would call the same
   number, and the leave-one-instance-out jackknife standard error reproduces
   the cluster-bootstrap standard error the paper already publishes for the
   same rates (analysis/DG10_direct_guard_intervals.csv).  If instead one
   instance moved a headline rate by more than a few percentage points, the
   correct conclusion would be that the rate is a property of that instance,
   the manuscript would have to say so, and the sentence would be written
   around the named instance rather than around the pooled share.  The benign
   false-block rate is expected to be the sensitive one, because the paper's
   own concentration analysis already reports that every false block of the
   deployed guard sits on two instances; this script must therefore RECOVER
   that fact, not discover it.
3. CONTAMINATION.  Nothing is trained, sampled or written outside analysis/.
   The single input log is read-only and is checksummed into the output
   header.  The only way this analysis could be contaminated is by reading a
   different population than the published one, so the reading, the config,
   the item count, the per-class denominators and the stage counts are all
   asserted against analysis/DG1_direct_guard_summary.csv before any fold is
   computed, and the full-sample rates are asserted against the manuscript folder
   macros.tex.  No output of this script is an input to any other.
4. DATA ACCURACY.  The population is exactly the one the published macros are
   computed from: reading = canonical, config = G_CERT, 2,000 items, loaded
   through delta_baselines.load_direct_rows so that the filter, the
   infrastructure-error check and the field parsing are the same code the
   DG14 baseline comparison uses.  The per-metric numerators and denominators
   are additionally cross-checked against DG10's own numerator and denominator
   columns, so this script and the published intervals are demonstrably
   reading the same rows.

THE DESIGN, DECLARED BEFORE ANY RESULT IS COMPUTED
--------------------------------------------------
POPULATION.  The 2,000 canonical / G_CERT items of analysis/DG1_direct_guard.csv,
covering 60 instances, 3 strata and 33 subclasses.

METRICS (17).  Every published per-class refusal share of the direct benchmark,
each with its own population and its own denominator convention:

    benign_refusal              refused / all benign items      (the false-block floor)
    v1..v6 _refusal_all_items   refused / all items of the class
    v1, v6 _refusal_representable
                                refused / items whose canonical proposal is
                                non-empty (V5 has no representable item at all,
                                so it has no representable metric)
    violations_all              refused / all V1-V6 items
    benign_block_qual,
    benign_block_feas           benign items refused AT that stage / all benign
    stage_reached_qual,
    stage_block_schema,
    stage_block_feas,
    stage_block_qual,
    all_refusal                 counted over all 2,000 items

FOLD FAMILIES (3).  Each family is a partition of the 2,000 items, and one fold
deletes one cell of that partition:

    instance   60 folds, the sampling unit.  The instances are what the paper's
               published intervals cluster on, so this family is the one whose
               jackknife standard error is a sampling standard error.
    stratum     3 folds, a design cell.
    subclass   33 folds, a design cell.

    For the two design families the spread across folds is descriptive: strata
    and subclasses are constructed by the suite generator, not drawn, so a
    standard error over them would answer a question nobody asked.  Their
    jackknife columns are still printed, and are labelled as spread rather than
    as sampling error wherever they appear.

EFFECTIVE FOLDS.  A fold is effective for a metric when deleting it removes at
least one item from that metric's denominator.  Deleting a V5-only subclass
cannot move the V3 refusal rate, and an identity fold in a min/max envelope is
noise in the table, so only effective folds are written out and only effective
folds enter the statistics.  Every envelope row still carries n_folds_total,
n_folds_effective, n_folds_identity and n_folds_degenerate, so the reader can
see how many folds were set aside and why.  Four of the sixty instances carry
no V3 item, which is why the V3 rate has 56 effective instance folds and the
benign rate has 60; those are the same two cluster counts the published
intervals report.

STATISTICS.  For metric p = Y/N and effective folds i = 1..n with fold values
p_(i) = (Y - y_i) / (N - n_i):

    envelope        min_i p_(i), max_i p_(i), and the fold attaining each
    jackknife mean  p_bar = (1/n) sum_i p_(i)
    jackknife SE    sqrt( ((n-1)/n) * sum_i (p_(i) - p_bar)^2 )
    jackknife bias  (n-1) * (p_bar - p)
    bias-corrected  n*p - (n-1)*p_bar, which is p - bias

The full-sample p always lies inside the envelope, because deleting a cell
raises the pooled rate exactly when that cell's own rate is below it; the
script asserts the containment rather than relying on the argument.

SELECTION POLICIES.  None that touch an estimate.  Nothing is chosen, tuned or
picked: every fold of every family is computed, every metric is reported, and
the only ordering is the fixed one declared in METRICS and FAMILIES.  The two
instances the report singles out are singled out by an assertion against a
constant that already exists in the repository
(delta_baselines.FOCUS_INSTANCES), not by a search over this script's own
output.  One PRESENTATIONAL threshold exists and is declared here rather than
chosen after the fact: the report's prose names the metrics whose
leave-one-subclass-out envelope spans more than SUBCLASS_SPAN_HIGHLIGHT_PP =
10 percentage points, so that the reader is pointed at them; every metric is
in the table either way and no estimate depends on the threshold.

SEEDS.  There is no draw anywhere: the jackknife is a deterministic enumeration
of the folds.  SEED exists only so a future addition that needs a draw has one
place to take it from.

WHAT IS ASSERTED (the script exits non-zero if any of these fails)
-----------------------------------------------------------------
The population (2,000 items, 60 instances, 3 strata, 33 subclasses, the
per-class denominators, the empty-proposal counts, the stage counts) against
analysis/DG1_direct_guard_summary.csv; every full-sample rate and count against
the literal manuscript/macros.tex prints, read with
delta_baselines.macro_value() rather than restated; every metric's numerator and
denominator against analysis/DG10_direct_guard_intervals.csv, so this script and
the published cluster-bootstrap intervals are reading the same rows; the
leave-one-instance-out jackknife standard error against DG10's linearised
cluster-robust standard error and its bootstrap standard error for all nine
metrics DG10 carries; the two cluster counts (60 and 56) against the macros that
print them; that each family's folds partition the population exactly; that the
full-sample value lies inside every envelope; and the influential-instance
cross-check below.

THE INFLUENTIAL-INSTANCE CROSS-CHECK
------------------------------------
This script must AGREE with what the repository already reports, not announce a
finding.  Three agreements are asserted:

  (a) the instances carrying at least one benign false block are exactly
      delta_baselines.FOCUS_INSTANCES, the two instances whose own no-op
      schedule certifies above tau;
  (b) the instances whose deletion strictly lowers the benign false-block rate
      are that same pair, and the leave-one-instance-out minimum for that rate
      is attained on one of them;
  (c) every capability-set arm of analysis/DG5_falseblock_concentration.csv,
      read at G_CERT, names that same pair as its two most false-blocked
      instances.

DETERMINISM AND COST
--------------------
CPU only, single process, stdlib only.  The work is counting 2,000 rows into
96 folds, so there is no multiprocessing and the 12-worker ceiling does not
bind; the thread-pool variables are pinned to one anyway so the script cannot
inherit a different numerical runtime's idea of how many threads it owns.

OUTPUTS
-------
``analysis/DG16_jackknife.csv``   population, every effective fold, every
                                  envelope, and every cross-check, long form
``analysis/DG16_jackknife.md``    the envelope tables and the two-sentence
                                  reading the manuscript can use

Run::

    conda run -n fjsp python code/scripts/jackknife_direct.py

Version: l1-dg16-jackknife-1
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import math
import os
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
             "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

VERSION = "l1-dg16-jackknife-1"

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent.parent
CODE = ROOT / "code"
ANALYSIS = ROOT / "analysis"
MANUSCRIPT = ROOT / "manuscript"

sys.path.insert(0, str(CODE))
sys.path.insert(0, str(SCRIPTS_DIR))

import delta_baselines as db  # noqa: E402  (path is set above)

#: Only so a future addition that needs a draw has one place to take it from.
#: Nothing in this file samples; the jackknife is an enumeration.
SEED = 20260823

#: The population is delta_baselines' population, reused rather than restated.
READING = db.READING
CONFIG = db.CONFIG
N_ITEMS = db.N_ITEMS
CLASSES = db.CLASSES
VIOLATION_CLASSES = db.VIOLATION_CLASSES
BENIGN = db.BENIGN
FOCUS_INSTANCES = db.FOCUS_INSTANCES

#: The suite's own partition sizes, asserted rather than assumed.
N_INSTANCES = 60
N_STRATA = 3
N_SUBCLASSES = 33

#: Agreement tolerances for the cross-file standard-error checks, absolute, on
#: the proportion scale.  The linearised cluster-robust standard error is an
#: analytic quantity and the jackknife is its delete-one counterpart, so they
#: agree to well under a twentieth of a percentage point; the bootstrap
#: standard error carries Monte-Carlo noise from 20,000 replicates and is given
#: twice the room.
SE_TOL_LIN = 5e-4
SE_TOL_BOOT = 1e-3

#: Presentational only (see SELECTION POLICIES in the module docstring): the
#: report's prose names the metrics whose leave-one-subclass-out envelope spans
#: more than this many percentage points.  No estimate depends on it.
SUBCLASS_SPAN_HIGHLIGHT_PP = 10.0


# --------------------------------------------------------------------------- #
# The metrics                                                                  #
# --------------------------------------------------------------------------- #
def _cls(name):
    return lambda r: r["primary_class"] == name


def _cls_nonempty(name):
    return lambda r: r["primary_class"] == name and not r["proposal_empty"]


def _refused(r):
    return r["cert_refused"]


def _all(r):
    return True


def _refused_at(stage):
    return lambda r: r["cert_refused"] and r["refused_stage"] == stage


def _reached(stage):
    return lambda r: r["stage_reached"] == stage


#: name -> (label, population predicate, numerator predicate, DG10 metric name
#: or "", published share macro or "", published count macro or "").
#: The order is the order every table in this analysis prints.
METRICS = OrderedDict([
    ("benign_refusal", (
        "Benign canonical proposal refused (the guard's false-block floor)",
        _cls(BENIGN), _refused,
        "benign_refusal", "dgBenignCanonicalShare", "dgBenignCanonicalBlocks")),
    ("v3_refusal", (
        "V3 canonical proposal refused (the violation only the certificate sees)",
        _cls("V3"), _refused,
        "v3_refusal", "dgVThreeCanonicalShare", "dgVThreeCanonicalRefused")),
    ("v1_refusal_all_items", (
        "V1 refused, over all V1 items",
        _cls("V1"), _refused,
        "v1_refusal_all_items", "dgVOneCanonicalShare", "")),
    ("v1_refusal_representable", (
        "V1 refused, over V1 items carrying a non-empty canonical proposal",
        _cls_nonempty("V1"), _refused,
        "v1_refusal_representable", "", "")),
    ("v2_refusal", (
        "V2 refused, over all V2 items",
        _cls("V2"), _refused,
        "v2_refusal", "dgVTwoCanonicalShare", "")),
    ("v4_refusal", (
        "V4 refused, over all V4 items",
        _cls("V4"), _refused,
        "v4_refusal", "dgVFourCanonicalShare", "")),
    ("v5_refusal_all_items", (
        "V5 refused, over all V5 items (every V5 proposal is empty)",
        _cls("V5"), _refused,
        "v5_refusal_all_items", "dgVFiveCanonicalShare",
        "dgVFiveCanonicalRefused")),
    ("v6_refusal_all_items", (
        "V6 refused, over all V6 items",
        _cls("V6"), _refused,
        "v6_refusal_all_items", "dgVSixCanonicalShare", "")),
    ("v6_refusal_representable", (
        "V6 refused, over V6 items carrying a non-empty canonical proposal",
        _cls_nonempty("V6"), _refused,
        "v6_refusal_representable", "", "")),
    ("violations_all", (
        "Any violation item refused, over all V1-V6 items",
        lambda r: r["primary_class"] in VIOLATION_CLASSES, _refused, "", "", "")),
    ("benign_block_feas", (
        "Benign items blocked at the feasibility stage, over all benign items",
        _cls(BENIGN), _refused_at("feas"), "", "",
        "dgBenignCanonicalFeasBlocks")),
    ("benign_block_qual", (
        "Benign items blocked at the quality stage, over all benign items",
        _cls(BENIGN), _refused_at("qual"), "", "",
        "dgBenignCanonicalQualBlocks")),
    ("stage_block_schema", (
        "Items blocked at the schema stage, over all items",
        _all, _reached("schema"), "", "", "")),
    ("stage_block_feas", (
        "Items blocked at the feasibility stage, over all items",
        _all, _reached("feas"), "", "", "")),
    ("stage_reached_qual", (
        "Items reaching the quality stage, over all items",
        _all, _reached("qual"), "", "", "")),
    ("stage_block_qual", (
        "Items blocked at the quality stage, over all items",
        _all, _refused_at("qual"), "", "", "")),
    ("all_refusal", (
        "Items refused at any stage, over all items",
        _all, _refused, "", "", "")),
])

#: The two headline metrics, in the order the manuscript states them.
HEADLINE = ("v3_refusal", "benign_refusal")

#: family -> (row key, prose name, folds are the sampling unit?).
FAMILIES = OrderedDict([
    ("instance", ("instance_id", "leave-one-instance-out", True)),
    ("stratum", ("stratum", "leave-one-stratum-out", False)),
    ("subclass", ("subclass", "leave-one-subclass-out", False)),
])

#: The published stage counts of the direct benchmark, asserted against the
#: summary file rather than trusted (direct_guard_benchmark.py writes both).
STAGE_COUNTS = {"schema": 165, "feas": 200, "qual": 1635}


# --------------------------------------------------------------------------- #
# Small helpers                                                                #
# --------------------------------------------------------------------------- #
def pct1(p):
    """The one-decimal percent the published macros print."""
    return "" if p is None else "{:.1f}%".format(100.0 * p)


def fpct(p, digits=4):
    return "" if p is None else "{:.{d}f}".format(100.0 * p, d=digits)


def fnum(x, digits=6):
    return "" if x is None else "{:.{d}f}".format(x, d=digits)


def load_dg10(path: Path) -> dict:
    """The published instance-clustered interval row per metric."""
    out = {}
    for r in db.read_csv_skipping_comments(path):
        if r["cluster_level"] != "instance":
            continue
        if r["reading"] != READING or r["config"] != CONFIG:
            continue
        out[r["metric"]] = r
    return out


def load_concentration(path: Path) -> list:
    return db.read_csv_skipping_comments(path)


# --------------------------------------------------------------------------- #
# The jackknife                                                                #
# --------------------------------------------------------------------------- #
def cells(rows, key, population, numerator):
    """fold key -> (items in this metric's population, of which numerator)."""
    out = defaultdict(lambda: [0, 0])
    for r in rows:
        if not population(r):
            continue
        c = out[r[key]]
        c[0] += 1
        if numerator(r):
            c[1] += 1
    return {k: tuple(v) for k, v in out.items()}


def jackknife(full_num, full_den, cell_counts, n_folds_total):
    """Delete-one-cell jackknife of the pooled ratio full_num / full_den.

    ``cell_counts`` is fold key -> (items, numerator) restricted to the
    metric's own population, so a fold of the family that is absent from it
    removes nothing from this metric and is an IDENTITY fold: it is counted
    and reported, never written out and never entered into a statistic.  A
    fold that would empty the population is DEGENERATE and is treated the same
    way.  Returns the effective folds in key order plus the envelope and the
    jackknife statistics.
    """
    folds = []
    for k in sorted(cell_counts):
        n_i, y_i = cell_counts[k]
        den = full_den - n_i
        if den <= 0:                      # the fold would empty the population
            folds.append((k, n_i, y_i, None))
            continue
        folds.append((k, n_i, y_i, (full_num - y_i) / den))

    values = [(v, k) for k, _n, _y, v in folds if v is not None]
    stats = {"n_total": n_folds_total, "n_eff": len(values),
             "n_degenerate": len(folds) - len(values),
             "n_identity": n_folds_total - len(folds)}
    if not values:
        return folds, stats

    full = full_num / full_den
    lo, argmin = min(values)
    hi, argmax = max(values)
    xs = [v for v, _k in values]
    n = len(xs)
    mean = sum(xs) / n
    var = sum((x - mean) ** 2 for x in xs)
    stats.update({
        "full": full,
        "min": lo, "argmin": argmin,
        "max": hi, "argmax": argmax,
        "range": hi - lo,
        "max_abs_delta": max(abs(x - full) for x in xs),
        "mean": mean,
        "se": math.sqrt((n - 1) / n * var) if n > 1 else None,
        "bias": (n - 1) * (mean - full) if n > 1 else None,
    })
    stats["bc"] = full - stats["bias"] if stats["bias"] is not None else None
    return folds, stats


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--direct", default=str(ANALYSIS / "DG1_direct_guard.csv"))
    ap.add_argument("--summary",
                    default=str(ANALYSIS / "DG1_direct_guard_summary.csv"))
    ap.add_argument("--intervals",
                    default=str(ANALYSIS / "DG10_direct_guard_intervals.csv"))
    ap.add_argument("--concentration",
                    default=str(ANALYSIS / "DG5_falseblock_concentration.csv"))
    ap.add_argument("--macros", default=str(MANUSCRIPT / "macros.tex"))
    ap.add_argument("--out-csv", default=str(ANALYSIS / "DG16_jackknife.csv"))
    ap.add_argument("--out-md", default=str(ANALYSIS / "DG16_jackknife.md"))
    args = ap.parse_args()

    paths = {k: Path(v) for k, v in (("direct", args.direct),
                                     ("summary", args.summary),
                                     ("intervals", args.intervals),
                                     ("concentration", args.concentration),
                                     ("macros", args.macros))}
    for name, p in paths.items():
        if not p.is_file():
            db.refuse_msg("{} does not exist ({})".format(p, name))

    checks, failures = [], []

    def check(what, expected, got):
        checks.append(what)
        if expected != got:
            failures.append("{}: expected {!r}, got {!r}".format(
                what, expected, got))

    def check_close(what, expected, got, tol):
        checks.append(what)
        if expected is None or got is None or abs(expected - got) > tol:
            failures.append("{}: expected {!r} +/- {:g}, got {!r}".format(
                what, expected, tol, got))

    # ------------------------------------------------------------------ #
    # Inputs and the population                                           #
    # ------------------------------------------------------------------ #
    direct = db.load_direct_rows(paths["direct"])
    summary = db.load_summary(paths["summary"])
    dg10 = load_dg10(paths["intervals"])
    conc = load_concentration(paths["concentration"])

    check("direct-benchmark items", N_ITEMS, len(direct))
    check("instances", N_INSTANCES, len({r["instance_id"] for r in direct}))
    check("strata", N_STRATA, len({r["stratum"] for r in direct}))
    check("subclasses", N_SUBCLASSES, len({r["subclass"] for r in direct}))

    for cls in CLASSES:
        got = sum(1 for r in direct if r["primary_class"] == cls)
        check("class denominator " + cls, int(summary[cls]["items"]), got)
        check("empty-proposal items " + cls,
              int(summary[cls]["empty_proposal_items"]),
              sum(1 for r in direct if r["primary_class"] == cls
                  and r["proposal_empty"]))
        check("class refusals " + cls, int(summary[cls]["refused"]),
              sum(1 for r in direct if r["primary_class"] == cls
                  and r["cert_refused"]))
    check("class denominators sum to the benchmark", N_ITEMS,
          sum(int(summary[c]["items"]) for c in CLASSES))

    for stage, want in sorted(STAGE_COUNTS.items()):
        check("items reaching the {} stage".format(stage), want,
              sum(1 for r in direct if r["stage_reached"] == stage))
        check("summary blocked_{} over all classes".format(stage),
              sum(int(summary[c]["blocked_" + stage]) for c in CLASSES),
              sum(1 for r in direct if r["cert_refused"]
                  and r["refused_stage"] == stage))

    # Each family must be a partition of the benchmark, or a fold would be
    # deleting rows twice or not at all.
    for family, (key, _name, _unit) in FAMILIES.items():
        sizes = defaultdict(int)
        for r in direct:
            sizes[r[key]] += 1
        check("{} folds partition the benchmark".format(family), N_ITEMS,
              sum(sizes.values()))
        check("{} folds are all non-empty".format(family), [],
              sorted(k for k, v in sizes.items() if v == 0))

    # ------------------------------------------------------------------ #
    # Full-sample rates, asserted against the published macros            #
    # ------------------------------------------------------------------ #
    full = OrderedDict()
    for name, (label, pop, num, dg10_name, macro_share, macro_count) in \
            METRICS.items():
        P = [r for r in direct if pop(r)]
        den = len(P)
        if den == 0:
            db.refuse_msg("metric {} has an empty population".format(name))
        numer = sum(1 for r in P if num(r))
        full[name] = {"num": numer, "den": den, "p": numer / den,
                      "label": label, "rows": P}

        if macro_share:
            check("macros.tex \\{}".format(macro_share),
                  db.macro_value(paths["macros"], macro_share),
                  pct1(numer / den))
        if macro_count:
            check("macros.tex \\{}".format(macro_count),
                  db.macro_value(paths["macros"], macro_count), str(numer))
        if dg10_name:
            d = dg10.get(dg10_name)
            if d is None:
                db.refuse_msg("{} carries no instance-clustered row for "
                              "{}".format(paths["intervals"], dg10_name))
            check("DG10 numerator " + dg10_name, int(d["numerator"]), numer)
            check("DG10 denominator " + dg10_name, int(d["denominator"]), den)

    # Two more macro literals that the population itself must reproduce.
    check("macros.tex \\dgVThreeCanonicalItems",
          db.macro_value(paths["macros"], "dgVThreeCanonicalItems"),
          str(full["v3_refusal"]["den"]))
    for cls, macro in (("V1", "dgVOneCanonicalEmpty"),
                       ("V5", "dgVFiveCanonicalEmpty"),
                       ("V6", "dgVSixCanonicalEmpty")):
        check("macros.tex \\" + macro, db.macro_value(paths["macros"], macro),
              str(sum(1 for r in direct if r["primary_class"] == cls
                      and r["proposal_empty"])))

    # ------------------------------------------------------------------ #
    # The folds                                                           #
    # ------------------------------------------------------------------ #
    results = OrderedDict()          # (family, metric) -> (folds, stats)
    for family, (key, _name, _unit) in FAMILIES.items():
        n_folds_total = len({r[key] for r in direct})
        for name, (label, pop, num, _d, _ms, _mc) in METRICS.items():
            cc = cells(direct, key, pop, num)
            folds, stats = jackknife(full[name]["num"], full[name]["den"], cc,
                                     n_folds_total)
            results[(family, name)] = (folds, stats)

            # The cells of a family must exhaust the metric's own population.
            check("{} cells exhaust the {} population".format(family, name),
                  full[name]["den"], sum(n for n, _y in cc.values()))
            check("{} cells exhaust the {} numerator".format(family, name),
                  full[name]["num"], sum(y for _n, y in cc.values()))
            if stats["n_eff"]:
                # Deleting a cell raises the pooled rate exactly when that
                # cell's own rate is below it, so the pooled rate can never
                # sit outside the envelope.
                if not (stats["min"] - 1e-12 <= stats["full"]
                        <= stats["max"] + 1e-12):
                    failures.append(
                        "{} / {}: full-sample {} outside the fold envelope "
                        "[{}, {}]".format(family, name, stats["full"],
                                          stats["min"], stats["max"]))
                checks.append("{} / {} envelope contains the full sample"
                              .format(family, name))

    # Cluster counts: the effective instance folds ARE the cluster counts the
    # published intervals report, and two of them are printed as macros.
    for name in METRICS:
        d = dg10.get(METRICS[name][3])
        if d is None:
            continue
        check("DG10 cluster count " + name, int(d["n_clusters"]),
              results[("instance", name)][1]["n_eff"])
    check("macros.tex \\dgFalseBlockClusters",
          db.macro_value(paths["macros"], "dgFalseBlockClusters"),
          str(results[("instance", "benign_refusal")][1]["n_eff"]))
    check("macros.tex \\dgVThreeSepClusters",
          db.macro_value(paths["macros"], "dgVThreeSepClusters"),
          str(results[("instance", "v3_refusal")][1]["n_eff"]))

    # The jackknife standard error against the two the paper already publishes.
    for name in METRICS:
        dg10_name = METRICS[name][3]
        d = dg10.get(dg10_name)
        if d is None:
            continue
        se = results[("instance", name)][1]["se"]
        check_close("jackknife vs linearised cluster SE, " + dg10_name,
                    float(d["lin_se"]), se, SE_TOL_LIN)
        check_close("jackknife vs cluster-bootstrap SE, " + dg10_name,
                    float(d["boot_se"]), se, SE_TOL_BOOT)

    # ------------------------------------------------------------------ #
    # The influential-instance cross-check                                #
    # ------------------------------------------------------------------ #
    fb_rows = [r for r in direct
               if r["primary_class"] == BENIGN and r["cert_refused"]]
    fb_instances = sorted({r["instance_id"] for r in fb_rows})
    check("instances carrying at least one benign false block",
          list(FOCUS_INSTANCES), fb_instances)
    check("benign false blocks all sit at the quality stage",
          [], sorted({r["refused_stage"] for r in fb_rows} - {"qual"}))
    check("strata carrying a benign false block", ["c09_storm2_w80"],
          sorted({r["stratum"] for r in fb_rows}))

    ben_folds, ben_stats = results[("instance", "benign_refusal")]
    lowering = sorted(k for k, _n, _y, v in ben_folds
                      if v is not None and v < ben_stats["full"] - 1e-12)
    check("instances whose deletion lowers the benign false-block rate",
          list(FOCUS_INSTANCES), lowering)
    check("the instance attaining the benign leave-one-out minimum is one of "
          "them", True, ben_stats["argmin"] in FOCUS_INSTANCES)

    conc_arms = []
    for r in conc:
        if r["config"] != "G_CERT" or r["capability_set"] != "1":
            continue
        top2 = [x.split(":")[0]
                for x in r["instance_breakdown"].split("|")[:2]]
        conc_arms.append((r["arm"], r["thinking"], top2))
    check("capability-set arms in the concentration file", True,
          len(conc_arms) >= 6)
    bad_arms = ["{}/{}".format(a, t) for a, t, top2 in conc_arms
                if sorted(top2) != sorted(FOCUS_INSTANCES)]
    check("capability-set arms whose two most false-blocked instances are not "
          "the same pair", [], bad_arms)

    if failures:
        for f in failures:
            print("ASSERTION FAILED  " + f, file=sys.stderr)
        return 2

    # ------------------------------------------------------------------ #
    # Output: the table                                                   #
    # ------------------------------------------------------------------ #
    stamp = _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    digests = {name: db.sha256(p) for name, p in paths.items()
               if name != "macros"}

    csv_path = Path(args.out_csv)
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        fh.write("# DG16. Instance-selection sensitivity of the direct "
                 "benchmark's published rates, on its {} canonical / {} "
                 "items\n".format(N_ITEMS, CONFIG))
        fh.write("# generated {} by code/scripts/jackknife_direct.py "
                 "({})\n".format(stamp, VERSION))
        fh.write("# inputs:\n")
        for name in ("direct", "summary", "intervals", "concentration"):
            fh.write("#   {:<14s} {}  sha256 {}\n".format(
                name, paths[name].relative_to(ROOT), digests[name]))
        fh.write("#   {:<14s} {}  (read for the published literals only)\n"
                 .format("macros", paths["macros"].relative_to(ROOT)))
        fh.write("# three fold families, each a partition of the same {} "
                 "items: instance ({} folds), stratum ({}), subclass ({})\n"
                 .format(N_ITEMS, N_INSTANCES, N_STRATA, N_SUBCLASSES))
        fh.write("# a fold deletes one cell and every rate is recomputed on "
                 "what is left; only EFFECTIVE folds are written, a fold "
                 "being effective for a metric when it removes at least one "
                 "item from that metric's denominator\n")
        fh.write("# jackknife SE = sqrt(((n-1)/n) * sum_i (p_(i) - p_bar)^2) "
                 "over the n effective folds; bias = (n-1)*(p_bar - p); "
                 "bias-corrected = p - bias\n")
        fh.write("# instances are the sampling unit, so only the instance "
                 "family's SE is a sampling standard error; the stratum and "
                 "subclass families are design cells and their spread is "
                 "descriptive\n")
        fh.write("# no randomness anywhere: the jackknife enumerates the "
                 "folds, nothing is drawn, and no setting is selected\n")
        fh.write("# self-check: {} assertions passed\n".format(len(checks)))

        w = csv.writer(fh)
        w.writerow(["block", "family", "fold", "metric", "metric_label",
                    "numerator", "denominator", "rate_pct", "delta_pp",
                    "n_folds_total", "n_folds_effective", "n_folds_identity",
                    "n_folds_degenerate", "full_pct",
                    "min_pct", "argmin", "max_pct", "argmax", "range_pp",
                    "max_abs_delta_pp", "jack_mean_pct", "jack_se_pct",
                    "jack_bias_pp", "jack_bc_pct", "stat", "note"])

        # -- population --------------------------------------------------- #
        for name, f in full.items():
            _l, _p, _n, dg10_name, macro_share, macro_count = METRICS[name]
            note = "published as \\{} = {}".format(
                macro_share, db.macro_value(paths["macros"], macro_share)) \
                if macro_share else ""
            if macro_count:
                note = (note + "; " if note else "") + \
                    "count published as \\{}".format(macro_count)
            if dg10_name:
                note = (note + "; " if note else "") + \
                    "DG10 metric {}".format(dg10_name)
            w.writerow(["population", "", "", name, f["label"], f["num"],
                        f["den"], fpct(f["p"]), "", "", "", "", "",
                        fpct(f["p"]),
                        "", "", "", "", "", "", "", "", "", "", "", note])

        for family, (key, fname, unit) in FAMILIES.items():
            sizes = defaultdict(int)
            for r in direct:
                sizes[r[key]] += 1
            w.writerow(["population", family, "", "", fname, "", N_ITEMS, "",
                        "", len(sizes), "", "", "", "", "", "", "", "", "",
                        "", "", "", "", "",
                        "{} to {} items per fold".format(
                            min(sizes.values()), max(sizes.values())),
                        "folds are the sampling unit" if unit else
                        "folds are design cells, not sampled units"])

        # -- every effective fold ----------------------------------------- #
        for (family, name), (folds, stats) in results.items():
            p_full = full[name]["p"]
            for k, n_i, y_i, v in folds:
                if v is None:
                    continue
                w.writerow(["fold", family, k, name, "",
                            full[name]["num"] - y_i, full[name]["den"] - n_i,
                            fpct(v), fnum(100.0 * (v - p_full), 4),
                            "", "", "", "", fpct(p_full),
                            "", "", "", "", "", "", "", "", "", "", n_i,
                            "this fold removes {} of the metric's {} items, "
                            "{} of them in the numerator".format(
                                n_i, full[name]["den"], y_i)])

        # -- the envelopes ------------------------------------------------ #
        for (family, name), (_folds, s) in results.items():
            if not s["n_eff"]:
                continue
            unit = FAMILIES[family][2]
            d = dg10.get(METRICS[name][3])
            note = "instances are the sampling unit; SE is a sampling " \
                "standard error" if unit else \
                "design cells, not sampled units; the spread is descriptive"
            if unit and d is not None:
                note += "; DG10 publishes lin_se {} and boot_se {} on the " \
                    "proportion scale".format(d["lin_se"], d["boot_se"])
            w.writerow(["envelope", family, "", name, full[name]["label"],
                        full[name]["num"], full[name]["den"],
                        fpct(full[name]["p"]), "", s["n_total"], s["n_eff"],
                        s["n_identity"], s["n_degenerate"], fpct(s["full"]),
                        fpct(s["min"]), s["argmin"], fpct(s["max"]),
                        s["argmax"], fnum(100.0 * s["range"], 4),
                        fnum(100.0 * s["max_abs_delta"], 4),
                        fpct(s["mean"]),
                        fnum(100.0 * s["se"], 4) if s["se"] is not None else "",
                        fnum(100.0 * s["bias"], 6)
                        if s["bias"] is not None else "",
                        fpct(s["bc"]) if s["bc"] is not None else "", "",
                        note])

        # -- the cross-checks --------------------------------------------- #
        w.writerow(["crosscheck", "instance", "", "benign_refusal", "", "", "",
                    "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
                    "", "", len(fb_instances),
                    "the {} benign false blocks sit on {} instances, {}, "
                    "which are delta_baselines.FOCUS_INSTANCES: the instances "
                    "whose own no-op schedule certifies above tau".format(
                        len(fb_rows), len(fb_instances),
                        ", ".join(fb_instances))])
        w.writerow(["crosscheck", "instance", "", "benign_refusal", "", "", "",
                    "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
                    "", "", len(lowering),
                    "deleting any other instance raises the false-block rate; "
                    "only {} lower it, and the leave-one-out minimum {} is "
                    "attained on {}".format(", ".join(lowering),
                                            fpct(ben_stats["min"], 2),
                                            ben_stats["argmin"])])
        w.writerow(["crosscheck", "", "", "", "", "", "", "", "", "", "", "",
                    "", "", "", "", "", "", "", "", "", "", "", "",
                    len(conc_arms),
                    "analysis/DG5_falseblock_concentration.csv: every one of "
                    "the {} capability-set arms read at G_CERT names the same "
                    "two instances as its two most false-blocked, so the "
                    "jackknife recovers a concentration the repository "
                    "already reports rather than a new one".format(
                        len(conc_arms))])

    write_md(Path(args.out_md), csv_path, paths, digests, stamp, direct, full,
             results, dg10, fb_rows, fb_instances, lowering, ben_stats,
             conc_arms, checks)

    print("wrote {}".format(csv_path))
    print("wrote {}".format(args.out_md))
    print("{} assertions passed".format(len(checks)))
    for name in HEADLINE:
        s = results[("instance", name)][1]
        print("  {:<16s} full {:>6s}   leave-one-instance-out {:>6s} to {:>6s}"
              "   jackknife SE {:>5s} pp   ({} folds)".format(
                  name, fpct(s["full"], 2), fpct(s["min"], 2),
                  fpct(s["max"], 2), fnum(100.0 * s["se"], 2), s["n_eff"]))
    return 0


# --------------------------------------------------------------------------- #
# The report                                                                   #
# --------------------------------------------------------------------------- #
def write_md(path, csv_path, paths, digests, stamp, direct, full, results,
             dg10, fb_rows, fb_instances, lowering, ben_stats, conc_arms,
             checks):
    L = []
    A = L.append

    def row(cells_):
        A("| " + " | ".join(str(c) for c in cells_) + " |")

    v3 = results[("instance", "v3_refusal")][1]
    ben = results[("instance", "benign_refusal")][1]

    A("# DG16. How far the direct benchmark's rates move when an instance is "
      "removed")
    A("")
    A("Generated {} by `code/scripts/jackknife_direct.py` (`{}`). Companion "
      "table: `{}`.".format(stamp, VERSION, csv_path.relative_to(ROOT)))
    A("")
    A("## The question")
    A("")
    A("The direct benchmark's published rates are class shares pooled over "
      "{} items that sit on only {} scheduling instances. This note deletes "
      "one instance at a time, recomputes every published rate on what is "
      "left, and repeats the exercise for the two other partitions of the "
      "same items, the {} strata and the {} subclasses. No model is in the "
      "loop and nothing is re-run: it is a re-read of "
      "`{}`.".format(N_ITEMS, N_INSTANCES, N_STRATA, N_SUBCLASSES,
                      paths["direct"].relative_to(ROOT)))
    A("")
    A("## The design")
    A("")
    A("A fold deletes one cell of a partition and every rate is recomputed on "
      "the remaining items. A fold counts as **effective** for a metric when "
      "it removes at least one item from that metric's denominator; deleting "
      "a V5-only subclass cannot move the V3 refusal rate, so identity folds "
      "are counted and reported but never enter a statistic and are never "
      "written out. For a metric `p = Y/N` with effective folds `p_(i)`, the "
      "table reports the envelope `min p_(i)` and `max p_(i)`, the jackknife "
      "standard error `sqrt(((n-1)/n) * sum (p_(i) - p_bar)^2)`, the bias "
      "`(n-1)(p_bar - p)`, and the bias-corrected value `p - bias`. Instances "
      "are the sampling unit and are what the published intervals cluster on, "
      "so only the instance family's standard error is a sampling standard "
      "error; strata and subclasses are constructed by the suite generator, "
      "and their spread is descriptive.")
    A("")
    A("No estimate here depends on a choice. Every fold of every family is "
      "computed, every metric is reported, and the jackknife is an "
      "enumeration rather than a resample. The one threshold in the note is "
      "presentational: the prose below names the metrics whose subclass "
      "envelope spans more than {:g} percentage points, and the full table is "
      "printed either way.".format(SUBCLASS_SPAN_HIGHLIGHT_PP))
    A("")
    A("## Leave one instance out")
    A("")
    A("Percentages; the `min` and `max` columns name the instance whose "
      "deletion attains them; `SE` and `bias` are in percentage points. The "
      "last column is the cluster-bootstrap standard error the manuscript "
      "already publishes for the same rate in "
      "`analysis/DG10_direct_guard_intervals.csv`, on the same scale.")
    A("")
    A("The fold count is the number of instances carrying at least one item "
      "of that metric's population: {} of the {} instances carry no V3 item, "
      "so the V3 rate has {} folds where the benign rate has {}. Those are "
      "the same cluster counts the published intervals report."
      .format(N_INSTANCES - v3["n_eff"], N_INSTANCES, v3["n_eff"],
              ben["n_eff"]))
    A("")
    row(["metric", "full", "folds", "min (instance)", "max (instance)",
         "range (pp)", "jackknife SE (pp)", "bias (pp)", "published SE (pp)"])
    row(["---"] * 9)
    for name in METRICS:
        s = results[("instance", name)][1]
        d = dg10.get(METRICS[name][3])
        row([name, fpct(s["full"], 2), s["n_eff"],
             "{} ({})".format(fpct(s["min"], 2), s["argmin"]),
             "{} ({})".format(fpct(s["max"], 2), s["argmax"]),
             fnum(100.0 * s["range"], 2),
             fnum(100.0 * s["se"], 3) if s["se"] is not None else "n/a",
             fnum(100.0 * s["bias"], 3) if s["bias"] is not None else "n/a",
             fnum(100.0 * float(d["boot_se"]), 3) if d is not None else "-"])
    A("")
    dev_lin, dev_boot, n_dg10 = 0.0, 0.0, 0
    for name in METRICS:
        d = dg10.get(METRICS[name][3])
        if d is None:
            continue
        n_dg10 += 1
        se = results[("instance", name)][1]["se"]
        dev_lin = max(dev_lin, abs(se - float(d["lin_se"])))
        dev_boot = max(dev_boot, abs(se - float(d["boot_se"])))
    A("The jackknife standard error reproduces the two standard errors the "
      "interval file already publishes on all {} rates it carries: the "
      "largest disagreement is {:.3f} percentage points against the "
      "linearised cluster-robust standard error and {:.3f} against the "
      "cluster bootstrap. The script asserts the agreement at {:.2g} and "
      "{:.2g} percentage points and exits non-zero otherwise, so the "
      "envelope above and the published intervals are two readings of one "
      "estimate rather than two estimates.".format(
          n_dg10, 100.0 * dev_lin, 100.0 * dev_boot,
          100.0 * SE_TOL_LIN, 100.0 * SE_TOL_BOOT))
    A("")
    A("## Leave one stratum out")
    A("")
    A("Three folds, so the spread is a description of the design rather than "
      "a standard error. The strata differ in what they contain, and the "
      "table shows how much of each rate each one carries.")
    A("")
    strata = sorted({r["stratum"] for r in direct})
    row(["metric", "full"] + ["without " + s for s in strata] + ["range (pp)"])
    row(["---"] * (len(strata) + 3))
    for name in METRICS:
        folds, s = results[("stratum", name)]
        by = {k: v for k, _n, _y, v in folds}
        row([name, fpct(s["full"], 2)] +
            [fpct(by.get(st), 2) if by.get(st) is not None else "n/a"
             for st in strata] +
            [fnum(100.0 * s["range"], 2)])
    A("")
    A("## Leave one subclass out")
    A("")
    A("{} folds, of which only the ones carrying items of a given metric can "
      "move it; the rest are identity folds and are counted rather than "
      "printed.".format(N_SUBCLASSES))
    A("")
    row(["metric", "full", "effective folds", "identity folds",
         "min (subclass)", "max (subclass)", "range (pp)"])
    row(["---"] * 7)
    for name in METRICS:
        st = results[("subclass", name)][1]
        row([name, fpct(st["full"], 2), st["n_eff"], st["n_identity"],
             "{} ({})".format(fpct(st["min"], 2), st["argmin"]),
             "{} ({})".format(fpct(st["max"], 2), st["argmax"]),
             fnum(100.0 * st["range"], 2)])
    A("")
    wide = [(n, results[("subclass", n)][1]) for n in METRICS
            if 100.0 * results[("subclass", n)][1]["range"]
            > SUBCLASS_SPAN_HIGHLIGHT_PP]
    if wide:
        A("{} span more than {:g} percentage points across subclass folds, "
          "and the reason is the suite's design rather than the guard's "
          "stability: each of those classes has its refusals concentrated in "
          "one designed subclass, so removing that subclass removes most of "
          "the numerator. {}. A subclass is a construction of the suite "
          "generator, not a sample, which is why this family is reported as a "
          "description of the design and carries no standard error."
          .format(", ".join("`{}`".format(n) for n, _s in wide),
                  SUBCLASS_SPAN_HIGHLIGHT_PP,
                  "; ".join(
                      ("Dropping" if i == 0 else "dropping") +
                      " `{}` takes `{}` from {} to {}".format(
                          st["argmin"], n, fpct(st["full"], 2),
                          fpct(st["min"], 2))
                      for i, (n, st) in enumerate(wide))))
        A("")
    A("## Where the movement sits, and what it agrees with")
    A("")
    A("All {} benign false blocks of the deployed guard sit on {} of the {} "
      "instances, {}. Those are exactly the two instances "
      "`delta_baselines.FOCUS_INSTANCES` names, the two whose own no-op "
      "schedule certifies above the deployed tolerance, and deleting either "
      "is the only way to lower the false-block rate at all: every other "
      "instance raises it. The leave-one-instance-out minimum, {}, is "
      "attained on {}.".format(
          len(fb_rows), len(fb_instances), N_INSTANCES,
          " and ".join("`{}`".format(i) for i in fb_instances),
          fpct(ben_stats["min"], 2), "`{}`".format(ben_stats["argmin"])))
    A("")
    A("This agrees with what the repository already reports rather than "
      "adding to it. In `analysis/DG5_falseblock_concentration.csv`, all {} "
      "capability-set arms read at `G_CERT` name that same pair as their two "
      "most false-blocked instances. The jackknife recovers the "
      "concentration; it does not find it.".format(len(conc_arms)))
    A("")
    A("The same concentration is what makes the leave-one-stratum-out row "
      "for the false-block rate read as it does: the whole of the guard's "
      "false-block cost lies in `c09_storm2_w80`, so removing that stratum "
      "sends the rate to {} while removing either of the other two raises "
      "it.".format(
          fpct({k: v for k, _n, _y, v in results[("stratum",
                                                  "benign_refusal")][0]}
               ["c09_storm2_w80"], 2)))
    A("")
    A("## The reading, for the manuscript")
    A("")
    A("> Deleting any one of the {} instances leaves the V3 refusal rate "
      "between {}% and {}% and the benign false-block rate between {}% and "
      "{}%, against full-sample values of {}% and {}%, and the "
      "leave-one-instance-out jackknife standard errors of {} and {} "
      "percentage points agree with the cluster-bootstrap standard errors "
      "reported for the same two rates. Only the two instances whose own "
      "no-op schedule already certifies above the deployed tolerance lower "
      "the false-block rate when they are removed, so that rate measures the "
      "cost of two schedules rather than a property of the benchmark as a "
      "whole.".format(
          N_INSTANCES,
          fpct(v3["min"], 1), fpct(v3["max"], 1),
          fpct(ben["min"], 1), fpct(ben["max"], 1),
          fpct(v3["full"], 1), fpct(ben["full"], 1),
          fnum(100.0 * v3["se"], 2), fnum(100.0 * ben["se"], 2)))
    A("")
    A("## Provenance and self-check")
    A("")
    row(["input", "sha256"])
    row(["---", "---"])
    for name in ("direct", "summary", "intervals", "concentration"):
        row(["`{}`".format(paths[name].relative_to(ROOT)), digests[name]])
    A("")
    A("`{}` is read for the published literals only and is never written."
      .format(paths["macros"].relative_to(ROOT)))
    A("")
    A("{} assertions pass, covering the population against "
      "`analysis/DG1_direct_guard_summary.csv`, every full-sample rate and "
      "count against the macros the manuscript prints, every numerator and "
      "denominator against `analysis/DG10_direct_guard_intervals.csv`, the "
      "jackknife standard error against both published cluster standard "
      "errors, the partition property of each fold family, envelope "
      "containment of the full-sample value, and the influential-instance "
      "agreement above. The script exits non-zero on any failure and writes "
      "nothing.".format(len(checks)))
    A("")

    path.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
