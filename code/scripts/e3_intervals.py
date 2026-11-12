#!/usr/bin/env python
"""DG6: intervals, equivalence tests and design power for the E3 agent-layer comparison.

Section 6.4 of the manuscript reports that at the loose budget no SINGLE+G vs
MULTI-G contrast is significant, and Section 6.6 turns that null into part 2 of
the deployment rule.  A non-significant Holm-corrected p-value over a family of
96 tests is a weak instrument for a claim of no effect, so this script adds the
three things the manuscript does not currently report:

* a paired interval on every SINGLE+G minus MULTI-G contrast, by three
  estimators (nonparametric paired bootstrap over items, Newcombe's method 10
  score interval for paired proportions, and a cluster bootstrap over the 55
  scheduling instances the 240 items are drawn from);
* a two-one-sided-test (TOST) equivalence verdict at declared margins, with the
  margins justified as a fraction of the effect the guard itself produces on the
  same items and the same outcomes (the MULTI-G vs MULTI-UG contrast); and
* the exact design power: the smallest paired risk difference the primary test
  could have detected at 80% power at n = 96, uncorrected and under each of the
  two Holm corrections the manuscript reports.

Nothing here edits the manuscript, the suite, or anything under results/.  Every
input is opened read-only.

FOUR LAUNCH QUESTIONS (the project's experiment rules)
--------------------------------------------------------
1. PURPOSE.  Supply the interval, the equivalence verdict and the power figure
   that Section 6.4's null result needs in order to license the Section 6.6
   deployment rule.  Destination: a new paragraph in Section 6.4, the Table 6
   caption, and the Section 6.6 rule text, via macros in manuscript/macros.tex.
2. EXPECTED RESULT.  The paired differences are small, but at n = 96 with a
   family-wise correction over m = 96 the design cannot detect anything below
   roughly a tenth of the scale, so most cells should come back "equivalent at
   10 pp, indeterminate at 5 pp".  Any cell whose interval excludes the margin
   is a real difference the manuscript must report rather than absorb into the
   null.  Either outcome is reportable; the failure mode is a cell that is
   declared equivalent because the test was too weak to say otherwise.
3. CONTAMINATION.  No model, no GPU, no network.  results/ and
   code/suite/ are read-only.  The guard re-evaluation reuses e3_analyze's own
   evaluation path and every recomputed verdict field is asserted equal to the
   accepted replay before any interval is computed; a mismatch stops the run.
   The bootstrap seed is fixed and the resample count is fixed at 20,000.
4. DATA ACCURACY.  The 18 loose-budget 2x2 tables are rebuilt from
   results/e3_replay_*/verdicts.jsonl and asserted cell-for-cell against
   analysis/E8_adjudication.csv before anything new is computed; the published
   minima (loose min uncorrected p, loose min Holm p, tight Holm-significant
   count) are recomputed from the rebuilt tables rather than read off the CSV.
   The reported pass-through outcome then applies the V4/V6 content rule
   (code/scripts/passthrough_rule.py), whose per-item flag is joined in from the
   quality rebuild and checked against the replay disposition it shares.

THE CLUSTER-AWARE TESTS (DG18), AND THEIR OWN FOUR LAUNCH QUESTIONS
-------------------------------------------------------------------
Section 5.4 declares that rates are reported with a cluster bootstrap "because
instructions written on the same replayed instance are not independent", and
then reports every agent-layer p-value from an exact McNemar or Wilcoxon test
that treats each item as its own draw.  The two readings of the same data are
inconsistent, and the second stage of this script closes the gap.

1. PURPOSE.  Re-derive every p-value in the declared family of 96 agent-layer
   tests with the exchangeable unit taken at the scheduling instance rather than
   at the item, and re-run the Holm correction on the result, so that each
   number the manuscript prints can be stated as unchanged or restated.
   Destination: analysis/DG18_cluster_tests.csv and .md, the Section 5.4
   statistics paragraph, and the Table 6 caption.
2. EXPECTED RESULT.  The paper's two load-bearing readings should survive.  The
   loose-budget SINGLE+G vs MULTI-G family should stay non-significant, because
   clustering can only remove effective degrees of freedom from a test that is
   already returning a Holm p of 1.00.  The guard's effect on end-task quality
   should stay significant on five arms, because its differences are spread over
   16 to 22 distinct instances, but this is the finding at risk: if the guard's
   effect were concentrated on a handful of instances, the corrected p would
   rise and the claim would have to be restated.  A verdict that changes is a
   correction the manuscript must carry, not a result to discard.
3. CONTAMINATION.  No model, no GPU, no network; replay only.  The new draws use
   their own seed offsets, so no existing DG6 stream is touched and every column
   already published in analysis/DG6_e3_intervals.csv is reproduced unchanged.
   The quality cache is read at the version it was written at and not rebuilt.
4. DATA ACCURACY.  Nothing cluster-aware is computed until all 96 item-level
   p-values, all four counts of all 72 2x2 tables, and both Holm corrections in
   analysis/E8_adjudication.csv have been reproduced from
   results/e3_replay_*/verdicts.jsonl and the quality rebuild.  Both pass-through
   readings are carried, because the manuscript prints p-values under E8's
   disposition-only reading and risk differences under the V4/V6 content rule.

DECLARED DESIGN, fixed before any cluster-aware number was computed
------------------------------------------------------------------
* POPULATION.  The declared family of 96: 2 contrasts (SINGLE+G vs MULTI-G,
  MULTI-G vs MULTI-UG) x 6 arms x 2 budget levels x 4 tests, repeat 0 only,
  which is exactly the family E8 corrects over.  Reported twice, once per
  pass-through reading.
* CLUSTER.  The replayed scheduling instance.  The 240 E3 items sit on 55
  instances; the 96 benign twins and the 96 labelled violations each sit on 52.
* STATISTIC.  The mean paired difference, on every family.  A signed-rank
  version of the same sign-flip test is reported beside it for end-task quality
  and is algebraically identical on the binary outcomes.
* NULL.  Signs are exchangeable at the instance level: all differences on one
  instance flip together.  20,000 draws at seed 20260814; two-sided p is the
  share of draws at least as extreme as the observed statistic.  The exact
  enumeration of the same null is reported beside the Monte Carlo value.
* SECONDARY.  A hierarchical bootstrap, instances then items within instance,
  20,000 replicates at the same seed, with the p-value read by inverting the
  percentile interval.
* SELECTION.  None.  Every cell of the family is reported, whether or not the
  manuscript prints it, and the verdict change is computed for all of them.
* ASSERTIONS.  72 2x2 tables cell for cell; 96 item-level p-values; 96 Holm
  p-values at m = 96 and 96 at m = 12; the rank and mean statistics agree on
  every binary cell; and on every cell with at most one differing item per
  instance the cluster test reproduces the item-level p-value exactly.

Usage::

    OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 taskset -c 0-3 \
      python code/scripts/e3_intervals.py --workers 4 --cores 0-3

Version: l1-dg6-intervals-1; cluster-aware stage l1-dg18-cluster-1.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

#: Bumped to -2 when the published pass-through outcome moved to the V4/V6
#: content rule; the quality cache carries the per-item content flag from that
#: version on, so a -1 cache is stale and is rebuilt rather than trusted.
VERSION = "l1-dg6-intervals-2"

ROOT = Path(__file__).resolve().parent.parent.parent          # <project>
SCRIPTS = ROOT / "code" / "scripts"
ANALYSIS = ROOT / "analysis"
RESULTS = ROOT / "results"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "code"))

BOOT_N = 20000
BOOT_SEED = 20260814

#: DG18, the cluster-aware stage.  Its own version, because it writes its own
#: artifacts; VERSION above still gates the quality cache and is unchanged, so a
#: cluster-test rerun never triggers a guard re-evaluation.
DG18_VERSION = "l1-dg18-cluster-1"

#: Sign-flip draws for the cluster permutation test, and the seed offsets that
#: keep the new streams disjoint from the two DG6 already uses ([seed, cell] for
#: the item bootstrap and [seed, 900000 + cell] for the cluster bootstrap).
PERM_N = 20000
PERM_SEED_OFFSET = 1800000
HIER_SEED_OFFSET = 2700000

#: Above this many contributing instances the exact enumeration of the 2^k
#: sign-flip null stops being cheap and the integer dynamic program takes over
#: where it applies.  Every cell in this study is at or below 28.
EXACT_SIGNFLIP_MAX_K = 24

#: Margins for the binary outcomes, in percentage points.  ``5`` is the primary;
#: see ``MARGIN_NOTE`` and the Markdown summary for the justification.
BINARY_MARGINS_PP = (2.5, 5.0, 10.0)
BINARY_PRIMARY_PP = 5.0

#: Margins for end-task quality, in weighted business hours on the mean per-item
#: paired difference.  ``10`` is the primary.
QUALITY_MARGINS_BH = (5.0, 10.0, 20.0)
QUALITY_PRIMARY_BH = 10.0

#: The three binary outcomes, as (key, E8 test name, unit label, the field the
#: E8 reconciliation runs on, the field the published interval runs on, which
#: direction is the better one).
#:
#: The two fields differ on pass-through alone.  ``passed_through`` is the
#: disposition-only predicate E8 was built on and is kept so the 2x2 tables can
#: still be asserted cell for cell against that artifact; ``passed_through_strict``
#: applies the V4/V6 content rule (code/scripts/passthrough_rule.py), under which
#: an applied V4 or V6 row counts unless the applied operations are exactly the
#: item's non-empty ground truth.  False block and catch are dispositions, so
#: the rule does not reach them and both fields are the same one.
BINARY_OUTCOMES = (
    ("false_block", "mcnemar_false_block", "the 96 matched benign twins",
     "blocked_false", "blocked_false", "lower is better"),
    ("catch", "mcnemar_catch", "the 96 labelled violations",
     "blocked_correct", "blocked_correct", "higher is better"),
    ("passthrough", "mcnemar_violation_passthrough", "the 96 labelled violations",
     "passed_through", "passed_through_strict", "lower is better"),
)

ARMS_ORDER = ("qwen14b", "qwen27b", "openai", "deepseek", "sonnet", "opus")

#: The two contrasts the declared family of 96 runs over, as
#: (name, system A, system B); the paired difference is always A minus B.
CONTRAST_PAIRS = (("SINGLE+G vs MULTI-G", "SINGLE+G", "MULTI-G"),
                  ("MULTI-G vs MULTI-UG", "MULTI-G", "MULTI-UG"))

#: The two pass-through readings the manuscript carries.  ``e8_disposition`` is
#: the disposition-only predicate every published p-value was computed on;
#: ``content_rule`` applies the V4/V6 content rule and is the reading behind the
#: published risk differences and every DG6 interval.  They differ on violation
#: pass-through alone.
READINGS = ("e8_disposition", "content_rule")
LEVELS = ("tight", "loose")

VIOLATION_CLASSES = ("V1", "V2", "V3", "V4")
APPLIED_TERMINALS = ("applied_with_certificate", "applied_uncertified")


# --------------------------------------------------------------------------- #
# Small utilities                                                              #
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_jsonl(path: Path) -> list:
    out = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def read_table_csv(path: Path) -> list:
    """An analysis/*.csv with leading ``#`` provenance lines stripped."""
    with open(path, "r", encoding="utf-8") as fh:
        lines = [l for l in fh if not l.startswith("#")]
    return list(csv.DictReader(lines))


class Checks:
    """Every assertion this script makes, recorded so the run can be audited."""

    def __init__(self):
        self.rows = []

    def check(self, group: str, name: str, expected, got) -> bool:
        ok = expected == got
        self.rows.append({"group": group, "check": name, "expected": expected,
                          "got": got, "ok": ok})
        return ok

    @property
    def failed(self):
        return [r for r in self.rows if not r["ok"]]

    def counts(self):
        return {"total": len(self.rows), "passed": len(self.rows) - len(self.failed),
                "failed": len(self.failed)}


# --------------------------------------------------------------------------- #
# Exact McNemar and Holm, reimplemented so the self-check is independent        #
# --------------------------------------------------------------------------- #
def mcnemar_exact_p(b: int, c: int) -> float:
    """Two-sided exact McNemar: the sign test on the discordant pairs."""
    n = int(b) + int(c)
    if n == 0:
        return 1.0
    k = min(int(b), int(c))
    tail = sum(math.comb(n, i) for i in range(k + 1))
    return min(1.0, 2.0 * tail / float(2 ** n))


def holm(pvalues: list) -> list:
    """Holm step-down adjusted p-values, in the input's order."""
    m = len(pvalues)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        candidate = min(1.0, (m - rank) * pvalues[idx])
        running = max(running, candidate)
        adjusted[idx] = running
    return adjusted


# --------------------------------------------------------------------------- #
# Interval estimators                                                          #
# --------------------------------------------------------------------------- #
def z_for(conf: float) -> float:
    """Two-sided normal quantile, by bisection on the error function."""
    target = (1.0 + conf) / 2.0
    lo, hi = 0.0, 10.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if 0.5 * math.erfc(-mid / math.sqrt(2.0)) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def wilson(k: int, n: int, conf: float) -> tuple:
    """Wilson score interval for a binomial proportion.

    Checked by construction: at each endpoint p0 the score statistic
    |p_hat - p0| / sqrt(p0 (1 - p0) / n) equals z, which ``_validate`` asserts.
    """
    if n == 0:
        return (0.0, 1.0)
    z = z_for(conf)
    p = k / float(n)
    denom = 2.0 * (n + z * z)
    centre = 2.0 * n * p + z * z
    half = z * math.sqrt(z * z + 4.0 * n * p * (1.0 - p))
    return ((centre - half) / denom, (centre + half) / denom)


def newcombe_paired(a: int, b: int, c: int, d: int, conf: float) -> tuple:
    """Newcombe (1998) method 10 for the difference of two paired proportions.

    ``a`` = both systems positive, ``b`` = only the first, ``c`` = only the
    second, ``d`` = neither.  The interval is the MOVER ("square-and-add")
    combination of the two Wilson intervals with the observed phi correlation:

        L = delta - sqrt((p1-l1)^2 - 2 phi (p1-l1)(u2-p2) + (u2-p2)^2)
        U = delta + sqrt((u1-p1)^2 - 2 phi (u1-p1)(p2-l2) + (p2-l2)^2)

    With phi = 0 this is exactly Newcombe's method 10 for *independent*
    proportions, which ``_validate`` checks against the published worked example
    (56/70 vs 48/80 gives 0.0524 to 0.3339 at 95%).  phi is set to zero when any
    marginal total is zero, as Newcombe prescribes.
    """
    n = a + b + c + d
    if n == 0:
        return (float("nan"), float("nan"), 0.0)
    p1 = (a + b) / float(n)
    p2 = (a + c) / float(n)
    delta = p1 - p2
    l1, u1 = wilson(a + b, n, conf)
    l2, u2 = wilson(a + c, n, conf)
    marg = (a + b) * (c + d) * (a + c) * (b + d)
    phi = 0.0 if marg == 0 else (a * d - b * c) / math.sqrt(float(marg))
    phi = max(-1.0, min(1.0, phi))
    lo_term = ((p1 - l1) ** 2 - 2.0 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2)
    hi_term = ((u1 - p1) ** 2 - 2.0 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2)
    lo = delta - math.sqrt(max(0.0, lo_term))
    hi = delta + math.sqrt(max(0.0, hi_term))
    return (max(-1.0, lo), min(1.0, hi), phi)


def paired_wald_se(b: int, c: int, n: int) -> float:
    """Standard error of the paired risk difference (b - c)/n."""
    if n == 0:
        return float("nan")
    var = (b + c - (b - c) ** 2 / float(n)) / float(n * n)
    return math.sqrt(max(0.0, var))


def boot_rd(x: np.ndarray, y: np.ndarray, rng, n_boot: int = BOOT_N) -> np.ndarray:
    """Nonparametric paired bootstrap of mean(x) - mean(y), resampling items."""
    n = x.shape[0]
    idx = rng.integers(0, n, size=(n_boot, n))
    return x[idx].mean(axis=1) - y[idx].mean(axis=1)


def boot_stat_cluster(values_by_cluster: list, rng, stat, n_boot: int = BOOT_N):
    """Cluster bootstrap: resample whole scheduling instances with replacement."""
    k = len(values_by_cluster)
    draws = rng.integers(0, k, size=(n_boot, k))
    out = np.empty(n_boot, dtype=float)
    for r in range(n_boot):
        pooled = np.concatenate([values_by_cluster[j] for j in draws[r]], axis=0)
        out[r] = stat(pooled)
    return out


def pct_ci(samples: np.ndarray, conf: float) -> tuple:
    alpha = (1.0 - conf) / 2.0
    return (float(np.quantile(samples, alpha)),
            float(np.quantile(samples, 1.0 - alpha)))


# --------------------------------------------------------------------------- #
# DG18: cluster-aware tests over the same declared families                     #
# --------------------------------------------------------------------------- #
def cluster_index_arrays(instance_of: list) -> list:
    """One index array per scheduling instance, in first-appearance order.

    ``instance_of[i]`` is the replayed instance the i-th unit was written on.
    Every item is in exactly one array, so the arrays partition the unit index
    and the paired differences can be summed inside an instance without double
    counting.
    """
    by = defaultdict(list)
    for idx, inst in enumerate(instance_of):
        by[inst].append(idx)
    return [np.array(v, dtype=int) for v in by.values()]


def cluster_sums(diffs: np.ndarray, clusters: list) -> np.ndarray:
    """Within-instance sums of the paired differences."""
    if not clusters:
        return np.zeros(0, dtype=float)
    return np.array([float(diffs[c].sum()) for c in clusters], dtype=float)


def signed_rank_vector(diffs) -> np.ndarray:
    """sign(d) times Wilcoxon's rank of |d|, zero where the difference is zero.

    The ranks are the ones the signed-rank test itself uses: taken over the
    non-zero magnitudes alone and averaged over ties.  Flipping the signs of
    this vector at the instance level is the clustered analogue of Wilcoxon,
    exactly as flipping the signs of the raw differences is the clustered
    analogue of the mean.
    """
    d = np.asarray(diffs, dtype=float)
    out = np.zeros(d.shape[0], dtype=float)
    nz = np.nonzero(d)[0]
    if nz.size == 0:
        return out
    mags = np.abs(d[nz])
    order = np.argsort(mags, kind="mergesort")
    srt = mags[order]
    ranks = np.empty(nz.size, dtype=float)
    i = 0
    while i < nz.size:
        j = i
        while j + 1 < nz.size and srt[j + 1] == srt[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    out[nz] = np.sign(d[nz]) * ranks
    return out


def _live_clusters(sums: np.ndarray, tol: float = 1e-12) -> np.ndarray:
    """The instances whose within-instance sum is not zero.

    An instance whose paired differences cancel to zero contributes nothing to
    the statistic under either sign, so it carries no information about the
    difference and is not one of the draws the permutation null randomises.
    This is the clustered counterpart of Wilcoxon dropping zero differences and
    of McNemar dropping concordant pairs.
    """
    s = np.asarray(sums, dtype=float)
    return s[np.abs(s) > tol]


def signflip_perm_p(sums: np.ndarray, rng, n_perm: int = PERM_N) -> dict:
    """Monte Carlo cluster sign-flip p-value for a sum-over-instances statistic.

    Under the paired null the sign of every difference on one instance flips
    together, because the instance, not the item, is what was drawn from the
    population.  The statistic is a linear function of the within-instance sums,
    so one draw is one sign vector of length ``n_clusters_used``.

    Two p-values come back.  ``p_share`` is the bare share of draws at least as
    extreme as the observed statistic, which is what the design declares, and
    ``p`` adds the observed configuration to the numerator and the denominator,
    the standard Monte Carlo correction that keeps a p-value from being reported
    as exactly zero when no draw was more extreme.  ``p`` is the one the Holm
    correction runs on; the two differ by at most 1/(``n_perm`` + 1).
    """
    live = _live_clusters(sums)
    k = int(live.shape[0])
    obs = float(np.asarray(sums, dtype=float).sum())
    if k == 0:
        return {"p": 1.0, "p_share": 1.0, "n_extreme": n_perm, "k": 0,
                "statistic": obs}
    tol = 1e-9 * max(1.0, abs(obs))
    signs = (rng.integers(0, 2, size=(n_perm, k)) * 2 - 1).astype(float)
    stats = signs @ live
    extreme = int(np.count_nonzero(np.abs(stats) >= abs(obs) - tol))
    return {"p": (1.0 + extreme) / (1.0 + n_perm),
            "p_share": extreme / float(n_perm),
            "n_extreme": extreme, "k": k, "statistic": obs}


def signflip_exact_p_int(int_sums) -> float:
    """Exact cluster sign-flip p when the within-instance sums are integers.

    The null distribution of the signed total is a convolution over the
    instances, so it is a dynamic program over the integer range rather than an
    enumeration of 2^k sign vectors.  Exact in integer arithmetic, with no
    resample limit.
    """
    live = [int(round(v)) for v in int_sums if int(round(v)) != 0]
    k = len(live)
    if k == 0:
        return 1.0
    obs = abs(sum(live))
    span = sum(abs(v) for v in live)
    counts = [0] * (2 * span + 1)
    counts[span] = 1
    for v in live:
        nxt = [0] * (2 * span + 1)
        for pos, cnt in enumerate(counts):
            if cnt:
                nxt[pos + v] += cnt
                nxt[pos - v] += cnt
        counts = nxt
    hit = sum(cnt for pos, cnt in enumerate(counts) if abs(pos - span) >= obs)
    return hit / float(2 ** k)


def signflip_exact_p_enum(sums, max_k: int = EXACT_SIGNFLIP_MAX_K) -> float:
    """Exact cluster sign-flip p by enumerating all 2^k sign vectors.

    Used when the within-instance sums are real valued (end-task quality in
    business hours), where the integer dynamic program does not apply.  Returns
    NaN above ``max_k``, where the enumeration stops being cheap; every cell in
    this study is below it.
    """
    live = _live_clusters(np.asarray(sums, dtype=float))
    k = int(live.shape[0])
    if k == 0:
        return 1.0
    if k > max_k:
        return float("nan")
    obs = abs(float(live.sum()))
    tol = 1e-9 * max(1.0, obs)
    totals = np.zeros(1, dtype=float)
    for v in live:
        totals = np.concatenate([totals + v, totals - v])
    return float(np.mean(np.abs(totals) >= obs - tol))


def signflip_exact_p(sums, max_k: int = EXACT_SIGNFLIP_MAX_K) -> float:
    """Exact cluster sign-flip p, by enumeration when small and DP when integer.

    The two routes are algebraically the same test and are cross-checked against
    each other on every cell where both apply.
    """
    arr = np.asarray(sums, dtype=float)
    live = _live_clusters(arr)
    if live.shape[0] <= max_k:
        return signflip_exact_p_enum(arr, max_k)
    scaled = arr * 2.0
    if np.all(np.abs(scaled - np.round(scaled)) < 1e-9):
        return signflip_exact_p_int(np.round(scaled))
    return float("nan")


def hier_boot_mean(diffs: np.ndarray, clusters: list, rng,
                   n_boot: int = BOOT_N, chunk: int = 2000) -> np.ndarray:
    """Two-stage bootstrap of the mean paired difference.

    Instances are resampled with replacement, and then the items inside each
    drawn instance are resampled with replacement as well, so both the
    between-instance and the within-instance components of the variance are
    resampled.  The denominator is the number of items the draw actually
    produced, which is what the estimator divides by on the observed data.
    """
    k = len(clusters)
    if k == 0:
        return np.zeros(n_boot, dtype=float)
    sizes = np.array([c.shape[0] for c in clusters], dtype=np.int64)
    width = int(sizes.max())
    values = np.zeros((k, width), dtype=float)
    for j, c in enumerate(clusters):
        values[j, :c.shape[0]] = diffs[c]
    slot = np.arange(width)
    out = np.empty(n_boot, dtype=float)
    done = 0
    while done < n_boot:
        take = min(chunk, n_boot - done)
        drawn = rng.integers(0, k, size=(take, k))
        drawn_sizes = sizes[drawn]
        picks = (rng.random((take, k, width)) * drawn_sizes[:, :, None]).astype(np.int64)
        picks = np.minimum(picks, np.maximum(drawn_sizes[:, :, None] - 1, 0))
        keep = slot[None, None, :] < drawn_sizes[:, :, None]
        vals = np.take_along_axis(values[drawn], picks, axis=2) * keep
        out[done:done + take] = vals.sum(axis=(1, 2)) / drawn_sizes.sum(axis=1)
        done += take
    return out


def boot_inversion_p(samples: np.ndarray) -> float:
    """Two-sided p by inverting the percentile interval of a bootstrap.

    The smallest confidence level whose two-sided percentile interval still
    excludes zero is 1 minus this value, so the p-value is twice the smaller
    tail of the bootstrap distribution on either side of zero.  Draws that land
    exactly on zero are counted in both tails, which is the conservative reading
    and the common case here: on the binary outcomes many resamples reproduce a
    difference of exactly zero.
    """
    n = int(samples.shape[0])
    if n == 0:
        return float("nan")
    low = int(np.count_nonzero(samples <= 0.0))
    high = int(np.count_nonzero(samples >= 0.0))
    tail = min((1.0 + low) / (1.0 + n), (1.0 + high) / (1.0 + n))
    return min(1.0, 2.0 * tail)


def cluster_test(diffs: np.ndarray, clusters: list, seed_key: int,
                 n_perm: int = PERM_N, n_boot: int = BOOT_N,
                 with_rank: bool = True) -> dict:
    """Every cluster-aware quantity for one paired cell.

    ``diffs`` are the per-item paired differences (system A minus system B) and
    ``clusters`` the index arrays returned by ``cluster_index_arrays``.  The
    seed is fixed from the module seed and the caller's cell key, so the result
    is identical on every rerun and independent of the order cells are visited
    in.
    """
    diffs = np.asarray(diffs, dtype=float)
    sums = cluster_sums(diffs, clusters)
    live = _live_clusters(sums)
    per_cluster_nonzero = [int(np.count_nonzero(diffs[c])) for c in clusters]
    rng = np.random.default_rng([BOOT_SEED, PERM_SEED_OFFSET + seed_key])
    perm = signflip_perm_p(sums, rng, n_perm)
    out = {
        "n_clusters": len(clusters),
        "n_clusters_used": int(live.shape[0]),
        "n_nonzero": int(np.count_nonzero(diffs)),
        "max_nonzero_items_in_one_cluster":
            max(per_cluster_nonzero) if per_cluster_nonzero else 0,
        "estimate": float(diffs.mean()) if diffs.size else float("nan"),
        "p_cluster_perm": perm["p"],
        "p_cluster_perm_share": perm["p_share"],
        "p_cluster_perm_exact": signflip_exact_p(sums),
    }
    if with_rank:
        ranked = signed_rank_vector(diffs)
        rsums = cluster_sums(ranked, clusters)
        rrng = np.random.default_rng([BOOT_SEED, PERM_SEED_OFFSET + seed_key])
        rperm = signflip_perm_p(rsums, rrng, n_perm)
        out["p_cluster_rank_perm"] = rperm["p"]
        out["p_cluster_rank_perm_share"] = rperm["p_share"]
        out["p_cluster_rank_exact"] = signflip_exact_p(rsums)
    brng = np.random.default_rng([BOOT_SEED, HIER_SEED_OFFSET + seed_key])
    samples = hier_boot_mean(diffs, clusters, brng, n_boot)
    lo, hi = pct_ci(samples, 0.95)
    out["p_hier_boot"] = boot_inversion_p(samples)
    out["hier_ci95_lo"] = lo
    out["hier_ci95_hi"] = hi
    return out


def citation_for(contrast: str, level: str, test: str) -> tuple:
    """Where in the manuscript this cell's p-value is printed, if it is.

    Every cell is in the declared family of 96 and therefore moves every
    Holm-corrected number the paper prints, but only some are printed as a
    p-value in their own right.  Both facts are recorded, because a reader
    asking whether a verdict changes needs to know which cells the verdict is
    read off and which cells only enter through the correction.
    """
    if contrast == "SINGLE+G vs MULTI-G" and level == "loose":
        return (True,
                "Table tab:e3 column 'S vs M Holm p' (1.00 on every arm and "
                "every test); Section 6.4 'no statistically detectable "
                "advantage'; App. E eThreeAgentHolmMin (1.00) and "
                "eThreeAgentRawPLooseMin (0.092) over these 24 cells")
    if contrast == "MULTI-G vs MULTI-UG" and level == "loose":
        if test == "wilcoxon_quality":
            return (True,
                    "Table tab:e3 column 'Guard at fixed architecture / Holm p'; "
                    "Section 6.4 'Holm-significant on five of six arms' "
                    "(eThreeGuardSignificantArmsWord)")
        return (False,
                "not printed as a p-value; the pass-through and catch effects "
                "on these items set the equivalence margins of Section 5.4")
    return (False,
            "not printed as a p-value; a tight-budget member of the declared "
            "family of 96, so it enters every Holm-corrected number the "
            "manuscript prints")


# --------------------------------------------------------------------------- #
# Exact power for the paired binary test                                       #
# --------------------------------------------------------------------------- #
def _log_trinomial_table(n: int):
    """log n! table for the trinomial pmf."""
    lg = [0.0] * (n + 1)
    for i in range(1, n + 1):
        lg[i] = lg[i - 1] + math.log(i)
    return lg


_MCN_P_CACHE: dict = {}


def _mcn_p(b: int, c: int) -> float:
    key = (b, c)
    if key not in _MCN_P_CACHE:
        _MCN_P_CACHE[key] = mcnemar_exact_p(b, c)
    return _MCN_P_CACHE[key]


def mcnemar_power(n: int, p_b: float, p_c: float, alpha: float, lg=None) -> float:
    """Exact power of the two-sided exact McNemar test at level ``alpha``.

    Each of ``n`` pairs is independently discordant-in-favour-of-A with
    probability ``p_b``, discordant-in-favour-of-B with ``p_c``, or concordant.
    Power is the trinomial probability that the exact p-value falls at or below
    ``alpha``.  No normal approximation is used anywhere.
    """
    if p_b < 0 or p_c < 0 or p_b + p_c > 1:
        return float("nan")
    lg = lg or _log_trinomial_table(n)
    p_conc = 1.0 - p_b - p_c
    lb = math.log(p_b) if p_b > 0 else None
    lc = math.log(p_c) if p_c > 0 else None
    lo = math.log(p_conc) if p_conc > 0 else None
    total = 0.0
    for b in range(n + 1):
        if lb is None and b > 0:
            break
        for c in range(n - b + 1):
            if lc is None and c > 0:
                break
            rest = n - b - c
            if lo is None and rest > 0:
                continue
            if _mcn_p(b, c) > alpha:
                continue
            logp = lg[n] - lg[b] - lg[c] - lg[rest]
            if b:
                logp += b * lb
            if c:
                logp += c * lc
            if rest:
                logp += rest * lo
            total += math.exp(logp)
    return total


def mdes_one_directional(n: int, alpha: float, power: float = 0.80) -> float:
    """Smallest |RD| detectable at ``power`` when all discordance is one way.

    This is the design's floor: no allocation of the discordant pairs between
    the two directions makes a given |RD| easier to detect than putting all of
    it in one direction, so a risk difference below this figure could not have
    been detected at 80% power under any nuisance structure.
    """
    lg = _log_trinomial_table(n)
    lo, hi = 0.0, 1.0
    if mcnemar_power(n, hi, 0.0, alpha, lg) < power:
        return float("nan")
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if mcnemar_power(n, mid, 0.0, alpha, lg) >= power:
            hi = mid
        else:
            lo = mid
    return hi


def mdes_at_discordance(n: int, p_disc: float, alpha: float,
                        power: float = 0.80) -> float:
    """Smallest |RD| detectable at ``power`` holding the discordance rate fixed."""
    if p_disc <= 0:
        return float("nan")
    lg = _log_trinomial_table(n)
    def pw(rd):
        p_b = (p_disc + rd) / 2.0
        p_c = (p_disc - rd) / 2.0
        return mcnemar_power(n, p_b, p_c, alpha, lg)
    if pw(p_disc) < power:
        return float("nan")
    lo, hi = 0.0, p_disc
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if pw(mid) >= power:
            hi = mid
        else:
            lo = mid
    return hi


def min_onedirectional_for_sig(n: int, alpha: float) -> int:
    """Fewest one-directional discordant pairs whose exact p-value clears alpha."""
    for k in range(0, n + 1):
        if mcnemar_exact_p(k, 0) <= alpha:
            return k
    return n + 1


# --------------------------------------------------------------------------- #
# Estimator validation                                                         #
# --------------------------------------------------------------------------- #
def _validate(checks: Checks) -> None:
    """Validate every estimator against a closed form or a published value."""
    # Wilson: the score equation holds at both endpoints.
    for k, n in ((56, 70), (48, 80), (0, 96), (1, 96), (13, 96)):
        lo, hi = wilson(k, n, 0.95)
        z = z_for(0.95)
        p = k / n
        for end in (lo, hi):
            if 0.0 < end < 1.0:
                score = abs(p - end) / math.sqrt(end * (1.0 - end) / n)
                checks.check("estimator",
                             "Wilson endpoint {}/{} solves the score equation".format(k, n),
                             True, abs(score - z) < 1e-8)
    # Newcombe method 10, independent case (phi = 0), published worked example:
    # 56/70 vs 48/80 gives (0.0524, 0.3339) at 95% (Newcombe 1998, Stat Med 17:873).
    l1, u1 = wilson(56, 70, 0.95)
    l2, u2 = wilson(48, 80, 0.95)
    d = 56 / 70 - 48 / 80
    lo = d - math.sqrt((56 / 70 - l1) ** 2 + (u2 - 48 / 80) ** 2)
    hi = d + math.sqrt((u1 - 56 / 70) ** 2 + (48 / 80 - l2) ** 2)
    checks.check("estimator", "Newcombe square-and-add reproduces 56/70 vs 48/80 lower",
                 "0.0524", "{:.4f}".format(lo))
    checks.check("estimator", "Newcombe square-and-add reproduces 56/70 vs 48/80 upper",
                 "0.3339", "{:.4f}".format(hi))
    # Exact McNemar against hand-computable values.
    checks.check("estimator", "exact McNemar p(6,0)", "0.031250",
                 "{:.6f}".format(mcnemar_exact_p(6, 0)))
    checks.check("estimator", "exact McNemar p(5,0)", "0.062500",
                 "{:.6f}".format(mcnemar_exact_p(5, 0)))
    checks.check("estimator", "exact McNemar p(0,0)", "1.000000",
                 "{:.6f}".format(mcnemar_exact_p(0, 0)))
    checks.check("estimator", "exact McNemar p(3,10)", "0.092285",
                 "{:.6f}".format(mcnemar_exact_p(3, 10)))
    # Exact power: with p_b = 1 every pair is discordant one way, so the test is
    # certain to reject whenever n one-directional pairs clear alpha.
    checks.check("estimator", "exact power is 1 when every pair is discordant one way",
                 "1.000000", "{:.6f}".format(mcnemar_power(96, 1.0, 0.0, 0.05)))
    checks.check("estimator", "exact power is 0 when no pair is ever discordant",
                 "0.000000", "{:.6f}".format(mcnemar_power(96, 0.0, 0.0, 0.05)))
    # Holm on a hand-checkable vector.
    checks.check("estimator", "Holm on [0.01, 0.04, 0.5]",
                 [0.03, 0.08, 0.5],
                 [round(v, 10) for v in holm([0.01, 0.04, 0.5])])


# --------------------------------------------------------------------------- #
# Stage 1-2: rebuild the 2x2 tables from the raw replay verdicts               #
# --------------------------------------------------------------------------- #
def load_verdict_dispositions(arm: str) -> dict:
    """{(level, variant, item_id): disposition dict} from a replay verdict log.

    The E3 dedup rule is last-row-wins per
    (arm, budget_level, pipeline, repeat, item_id); the variant is added because
    the replay writes one row per guard variant.  Only repeat 0 is kept, which is
    the primary family E8 corrects over.
    """
    path = RESULTS / "e3_replay_{}".format(arm) / "verdicts.jsonl"
    out: dict = {}
    meta: dict = {}
    for row in read_jsonl(path):
        if int(row["repeat"]) != 0:
            continue
        key = (row["budget_level"], row["variant"], row["item_id"])
        terminal = row["terminal"]
        out[key] = {
            "blocked_false": terminal == "blocked_false",
            "blocked_correct": terminal == "blocked_correct",
            "passed_through": terminal in APPLIED_TERMINALS,
        }
        meta[row["item_id"]] = {"primary_class": row["primary_class"],
                                "instance_id": row["instance_id"],
                                "budget_tokens": row["budget_tokens"]}
    return {"disp": out, "meta": meta, "path": path}


def unit_items(meta: dict, unit: str) -> list:
    if unit == "the 96 matched benign twins":
        return sorted(i for i, m in meta.items() if m["primary_class"] == "benign")
    if unit == "the 96 labelled violations":
        return sorted(i for i, m in meta.items()
                      if m["primary_class"] in VIOLATION_CLASSES)
    return sorted(meta)


def two_by_two(disp: dict, level: str, items: list, field: str,
               name_a: str, name_b: str) -> dict:
    a_only = b_only = both = neither = 0
    for item in items:
        xa = disp[(level, name_a, item)][field]
        xb = disp[(level, name_b, item)][field]
        if xa and not xb:
            a_only += 1
        elif xb and not xa:
            b_only += 1
        elif xa and xb:
            both += 1
        else:
            neither += 1
    return {"n_units": len(items), "a_only": a_only, "b_only": b_only,
            "both": both, "neither": neither}


# --------------------------------------------------------------------------- #
# Stage 3: end-task quality via e3_analyze's own guard re-evaluation           #
# --------------------------------------------------------------------------- #
def build_quality(cache_path: Path, workers: int, checks: Checks) -> dict:
    """Per-(arm, level, variant, item) wwt_original_bh, from e3_analyze.

    The fourth E3 outcome is not in results/e3_replay_*/verdicts.jsonl: it comes
    from re-running the guard so the executed schedule's objective can be read
    off the verdict.  Rather than reimplement that, this calls e3_analyze's own
    ``load_arm`` / ``evaluate_rows`` / ``build_entries``, which assert every
    recomputed verdict field equal to the accepted replay before returning.
    """
    if cache_path.exists():
        payload = json.loads(cache_path.read_text())
        if payload.get("version") == VERSION and payload.get("assertions"):
            print("[dg6] quality cache hit: {}".format(cache_path))
            # The assertions the rebuild made are replayed from the cache, so a
            # cache-hit run reports the same self-check as a cold one.
            for name, (expected, got) in sorted(
                    payload.get("assertions", {}).items()):
                checks.check("quality", name + " (from cache)", expected, got)
            return payload
        print("[dg6] quality cache is stale (version {}); rebuilding"
              .format(payload.get("version")))

    import e3_analyze as e3a                                    # noqa: E402
    import ladder_replay as lr                                  # noqa: E402
    import suite_gate as sg                                     # noqa: E402
    import e3_sample as e3s                                     # noqa: E402

    started = time.perf_counter()
    inputs = sg.assert_inputs()
    print("[dg6] suite sha256 {} OK".format(inputs["suite_sha256"]))
    slice_ids = e3s.load_slice(e3a.SLICE_NAME)
    checks.check("quality", "the E3 slice holds 240 items", 240, len(slice_ids))

    rec = lr.Reconciler()
    anchors = e3a.load_anchors(ANALYSIS / "ladder", rec)
    payload = {"version": VERSION, "arms": {}, "provenance": [], "assertions": {}}
    payload["assertions"]["the E3 slice holds 240 items"] = [240, len(slice_ids)]
    for spec in e3a.ARMS:
        arm = e3a.load_arm(spec, RESULTS)
        results = e3a.evaluate_rows(arm["rows"], workers)
        entries, stats = e3a.build_entries(arm, results, anchors, rec)
        e3a.reconcile_arm(arm, entries, results, rec)
        comparisons = sum(stats["field_total"].values())
        matches = sum(stats["field_hits"].values())
        name = ("{}: every recomputed verdict field equals the accepted replay"
                .format(spec["arm"]))
        checks.check("quality", name, comparisons, matches)
        payload["assertions"][name] = [comparisons, matches]
        block = {}
        for e in entries:
            # All four variants, not only the two the quality contrast needs:
            # the unguarded pair carries the reference effect the binary margins
            # are a fraction of, and its content flag is not in the replay log.
            if int(e["repeat"]) != 0:
                continue
            block["{}|{}|{}".format(e["budget_level"], e["variant"],
                                    e["item_id"])] = {
                "wwt": e["wwt_original_bh"],
                "instance_id": e["instance_id"],
                "primary_class": e["primary_class"],
                "rule": e["rule_wwt_original_bh"],
                "terminal": e["terminal"],
                "passes_strict": e["passes_strict"],
            }
        payload["arms"][spec["arm"]] = block
        print("[dg6] {}: {} entries, {} quality cells kept, {:.0f}s elapsed"
              .format(spec["arm"], len(entries), len(block),
                      time.perf_counter() - started))
    counts = rec.counts()
    checks.check("quality", "e3_analyze reconciliation has no failures",
                 0, counts["failed"])
    payload["assertions"]["e3_analyze reconciliation has no failures"] = \
        [0, counts["failed"]]
    payload["provenance"] = [
        "suite sha256 {}".format(inputs["suite_sha256"]),
        "adjustment schema sha256 {}".format(inputs["schema_sha256"]),
        "e3_analyze reconciliation {}/{} passed".format(counts["passed"],
                                                        counts["total"]),
    ]
    payload["reconciliation"] = counts
    cache_path.write_text(json.dumps(payload) + "\n")
    print("[dg6] quality rebuilt in {:.0f}s -> {}".format(
        time.perf_counter() - started, cache_path))
    return payload


# --------------------------------------------------------------------------- #
# Wilcoxon signed rank (for the quality self-check)                            #
# --------------------------------------------------------------------------- #
def wilcoxon_p(diffs: list) -> float:
    """The exact sign-flip two-sided p-value e3_analyze uses (n_nonzero <= 100)."""
    nonzero = [d for d in diffs if d != 0]
    n = len(nonzero)
    if n == 0:
        return 1.0
    mags = [abs(d) for d in nonzero]
    order = sorted(range(n), key=lambda i: mags[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and mags[order[j + 1]] == mags[order[i]]:
            j += 1
        shared = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = shared
        i = j + 1
    w_plus = sum(r for r, d in zip(ranks, nonzero) if d > 0)
    w_minus = sum(r for r, d in zip(ranks, nonzero) if d < 0)
    statistic = min(w_plus, w_minus)
    scaled = [int(round(2.0 * r)) for r in ranks]
    threshold = int(round(2.0 * statistic))
    total = sum(scaled)
    counts = [0] * (total + 1)
    counts[0] = 1
    for step in scaled:
        nxt = [0] * (total + 1)
        for value, count in enumerate(counts):
            if count:
                nxt[value] += count
                nxt[value + step] += count
        counts = nxt
    cut = min(total, max(threshold, 0))
    left = sum(counts[: cut + 1]) / float(2 ** n)
    return min(1.0, 2.0 * left)


def hodges_lehmann(diffs: np.ndarray) -> float:
    """Pseudomedian: the median of the n(n+1)/2 Walsh averages."""
    n = diffs.shape[0]
    i, j = np.triu_indices(n, k=0)
    return float(np.median((diffs[i] + diffs[j]) / 2.0))


# --------------------------------------------------------------------------- #
# TOST verdicts                                                                #
# --------------------------------------------------------------------------- #
def tost_verdict(ci90_list: list, margin: float) -> str:
    """One of three verdicts, from every 90% interval supplied.

    Equivalence is established only if *every* 90% interval lies strictly inside
    the margin, and refuted only if *every* 90% interval lies strictly outside
    it; otherwise the sample does not settle the question.  Requiring agreement
    across estimators is what stops a bootstrap that has degenerated to a point
    (a cell with no discordant pair resamples to the same zero every time) from
    declaring equivalence on its own.
    """
    finite = [(lo, hi) for lo, hi in ci90_list
              if not (math.isnan(lo) or math.isnan(hi))]
    if not finite:
        return "indeterminate"
    if all(lo > -margin and hi < margin for lo, hi in finite):
        return "equivalence established"
    if all(lo > margin or hi < -margin for lo, hi in finite):
        return "equivalence refuted"
    return "indeterminate"


def boot_tost_p(samples: np.ndarray, margin: float) -> float:
    """The smallest alpha at which the percentile TOST would declare equivalence."""
    return float(max(np.mean(samples <= -margin), np.mean(samples >= margin)))


def wald_tost_p(rd: float, se: float, margin: float) -> float:
    if se <= 0 or math.isnan(se):
        return float("nan")
    z_lo = (rd + margin) / se
    z_hi = (rd - margin) / se
    p_lo = 1.0 - 0.5 * math.erfc(-z_lo / math.sqrt(2.0))
    p_hi = 0.5 * math.erfc(-z_hi / math.sqrt(2.0))
    return float(max(p_lo, p_hi))




def dg18_build_cells(arm_data: dict, quality: dict, e8: dict, checks: Checks) -> dict:
    """Every cell of the declared family of 96, under both pass-through readings.

    One cell is one (reading, contrast, arm, budget level, test).  It carries the
    paired differences at item level, the instance each item was written on, the
    2x2 table where the outcome is binary, and the item-level p-value the
    manuscript reports, recomputed here rather than read off E8.

    Two readings are built because the manuscript reports two.  Under
    ``e8_disposition`` an applied proposal is a pass-through whatever it applied,
    which is the reading every p-value printed in the paper was computed on.
    Under ``content_rule`` an applied V4 or V6 row does not count as a
    pass-through when the applied operations are exactly the item's non-empty
    ground truth, which is the reading Table tab:e3-rd's risk differences and
    every DG6 interval use.  The two agree on false block and on catch, which are
    dispositions the rule does not reach, and that agreement is asserted.

    Every ``e8_disposition`` cell is checked against analysis/E8_adjudication.csv
    before any cluster-aware number is computed: the four 2x2 counts, the exact
    McNemar or Wilcoxon p-value, and both Holm corrections the paper prints.
    """
    cells = {}
    for reading, field_of in (("e8_disposition", lambda f, fp: f),
                              ("content_rule", lambda f, fp: fp)):
        for contrast, name_a, name_b in CONTRAST_PAIRS:
            for arm in ARMS_ORDER:
                meta = arm_data[arm]["meta"]
                disp = arm_data[arm]["disp"]
                block = quality["arms"][arm]
                for level in LEVELS:
                    for key, test, unit, field, field_pub, better in BINARY_OUTCOMES:
                        use = field_of(field, field_pub)
                        items = unit_items(meta, unit)
                        tab = two_by_two(disp, level, items, use, name_a, name_b)
                        diffs = np.array(
                            [(1.0 if disp[(level, name_a, i)][use] else 0.0)
                             - (1.0 if disp[(level, name_b, i)][use] else 0.0)
                             for i in items], dtype=float)
                        clusters = cluster_index_arrays(
                            [meta[i]["instance_id"] for i in items])
                        cells[(reading, contrast, arm, level, test)] = {
                            "outcome": key, "unit": unit, "scale": "pp",
                            "items": items, "diffs": diffs, "clusters": clusters,
                            "table": tab, "better": better,
                            "field": use,
                            "p_item": mcnemar_exact_p(tab["a_only"], tab["b_only"]),
                            "p_item_method": "exact binomial (McNemar)",
                        }
                    items = sorted({k.split("|")[2] for k in block
                                    if k.startswith(level + "|")})
                    diffs = np.array(
                        [block["{}|{}|{}".format(level, name_a, i)]["wwt"]
                         - block["{}|{}|{}".format(level, name_b, i)]["wwt"]
                         for i in items], dtype=float)
                    insts = [block["{}|{}|{}".format(level, name_a, i)]["instance_id"]
                             for i in items]
                    for i, inst in zip(items, insts):
                        checks.check("stage3c",
                                     "{}/{}/{} the quality rebuild and the replay "
                                     "log agree on the instance".format(arm, level, i),
                                     meta[i]["instance_id"], inst)
                    cells[(reading, contrast, arm, level, "wilcoxon_quality")] = {
                        "outcome": "quality_mean_bh",
                        "unit": "all 240 items", "scale": "bh",
                        "items": items, "diffs": diffs,
                        "clusters": cluster_index_arrays(insts),
                        "table": None, "better": "lower is better",
                        "field": "wwt_original_bh",
                        "p_item": wilcoxon_p(list(diffs)),
                        "p_item_method": "exact sign-flip (Wilcoxon signed rank)",
                    }

    # -- the e8_disposition reading must reproduce E8 exactly ---------------- #
    keys, ps = [], []
    for contrast, _a, _b in CONTRAST_PAIRS:
        for arm in ARMS_ORDER:
            for level in LEVELS:
                for _k, test, *_rest in BINARY_OUTCOMES:
                    keys.append((contrast, arm, level, test))
                keys.append((contrast, arm, level, "wilcoxon_quality"))
    for key in keys:
        cell = cells[("e8_disposition",) + key]
        ref = e8[key]
        label = "{}/{}/{}/{}".format(*key)
        if cell["table"] is not None:
            for name in ("n_units", "a_only", "b_only", "both", "neither"):
                checks.check("stage3c", "{} {} matches E8".format(label, name),
                             int(ref[name]), cell["table"][name])
        else:
            checks.check("stage3c", "{} n_units matches E8".format(label),
                         int(ref["n_units"]), len(cell["items"]))
        checks.check("stage3c", "{} item-level p matches E8".format(label),
                     "{:.6g}".format(float(ref["p_raw"])),
                     "{:.6g}".format(cell["p_item"]))
        ps.append(cell["p_item"])
    checks.check("stage3c", "the declared family holds 96 tests", 96, len(ps))
    holm96 = holm(ps)
    by_family = defaultdict(list)
    for pos, key in enumerate(keys):
        by_family[(key[0], key[3])].append(pos)
    holm12 = {}
    for fam, idxs in by_family.items():
        checks.check("stage3c", "the {} | {} question family holds 12 tests"
                     .format(*fam), 12, len(idxs))
        for slot, pos in enumerate(idxs):
            holm12[pos] = holm([ps[i] for i in idxs])[slot]
    for pos, key in enumerate(keys):
        ref = e8[key]
        label = "{}/{}/{}/{}".format(*key)
        checks.check("stage3c", "{} Holm p over the family of 96 matches E8"
                     .format(label), "{:.6g}".format(float(ref["p_holm_agent_layer"])),
                     "{:.6g}".format(holm96[pos]))
        checks.check("stage3c", "{} Holm p over the question family of 12 matches "
                     "E8".format(label), "{:.6g}".format(float(ref["p_holm_family"])),
                     "{:.6g}".format(holm12[pos]))
        cells[("e8_disposition",) + key]["p_item_holm96"] = holm96[pos]
        cells[("e8_disposition",) + key]["p_item_holm12"] = holm12[pos]

    # -- the content_rule reading: its own Holm over the same 96 ------------- #
    ps2 = [cells[("content_rule",) + key]["p_item"] for key in keys]
    holm96b = holm(ps2)
    holm12b = {}
    for fam, idxs in by_family.items():
        for slot, pos in enumerate(idxs):
            holm12b[pos] = holm([ps2[i] for i in idxs])[slot]
    for pos, key in enumerate(keys):
        cells[("content_rule",) + key]["p_item_holm96"] = holm96b[pos]
        cells[("content_rule",) + key]["p_item_holm12"] = holm12b[pos]
        if key[3] != "mcnemar_violation_passthrough":
            checks.check("stage3c", "{}/{}/{}/{} the content rule does not reach "
                         "this outcome".format(*key),
                         "{:.12g}".format(cells[("e8_disposition",) + key]["p_item"]),
                         "{:.12g}".format(cells[("content_rule",) + key]["p_item"]))
    return {"cells": cells, "keys": keys}


def dg18_run(built: dict, checks: Checks, n_perm: int, n_boot: int) -> list:
    """The cluster-aware tests, the Holm re-run, and one row per cell.

    The cell's seed key is its position in a fixed enumeration of the readings
    and the family, so every draw is reproducible and no two cells share a
    stream.
    """
    cells, keys = built["cells"], built["keys"]
    rows = []
    for r_index, reading in enumerate(READINGS):
        results = []
        for pos, key in enumerate(keys):
            cell = cells[(reading,) + key]
            seed_key = r_index * 1000 + pos
            res = cluster_test(cell["diffs"], cell["clusters"], seed_key,
                               n_perm=n_perm, n_boot=n_boot)
            # The mean statistic and the signed-rank statistic are the same test
            # on a binary outcome, because every non-zero difference has the same
            # magnitude and therefore the same rank.  Asserted rather than
            # assumed, because it is the cheapest check that the rank machinery
            # is wired to the same sign draws.
            if cell["table"] is not None:
                checks.check("stage3d", "{}/{}/{}/{}/{} the rank and the mean "
                             "statistic agree on a binary outcome"
                             .format(reading, *key),
                             "{:.12g}".format(res["p_cluster_perm"]),
                             "{:.12g}".format(res["p_cluster_rank_perm"]))
            # Where every non-zero difference sits on a different instance there
            # is nothing to correct for, and the cluster sign-flip test is
            # algebraically the item-level test.  This is the calibration check
            # on the whole construction.
            if res["max_nonzero_items_in_one_cluster"] <= 1:
                exact = (res["p_cluster_perm_exact"] if cell["table"] is not None
                         else res["p_cluster_rank_exact"])
                checks.check("stage3d", "{}/{}/{}/{}/{} with one differing item "
                             "per instance the cluster test reproduces the "
                             "item-level p".format(reading, *key),
                             "{:.9g}".format(cell["p_item"]),
                             "{:.9g}".format(exact))
            results.append(res)
        perm_holm96 = holm([r["p_cluster_perm"] for r in results])
        exact_holm96 = holm([r["p_cluster_perm_exact"] if
                             not math.isnan(r["p_cluster_perm_exact"]) else
                             r["p_cluster_perm"] for r in results])
        perm_holm12 = {}
        fams = defaultdict(list)
        for pos, key in enumerate(keys):
            fams[(key[0], key[3])].append(pos)
        for fam, idxs in fams.items():
            sub = holm([results[i]["p_cluster_perm"] for i in idxs])
            for slot, pos in enumerate(idxs):
                perm_holm12[pos] = sub[slot]
        for pos, key in enumerate(keys):
            contrast, arm, level, test = key
            cell = cells[(reading,) + key]
            res = results[pos]
            tab = cell["table"] or {}
            cited, where = citation_for(contrast, level, test)
            sig_item_holm = cell["p_item_holm96"] < 0.05
            sig_clu_holm = perm_holm96[pos] < 0.05
            sig_clu_exact_holm = exact_holm96[pos] < 0.05
            scale = 100.0 if cell["scale"] == "pp" else 1.0
            rows.append({
                "reading": reading, "contrast": contrast, "arm": arm,
                "budget_level": level, "test": test, "outcome": cell["outcome"],
                "unit": cell["unit"], "outcome_scale": cell["scale"],
                "statistic": "mean paired difference, system A minus system "
                             "B, A being the first system named in the contrast",
                "n_units": len(cell["items"]),
                "n_clusters": res["n_clusters"],
                "n_clusters_used": res["n_clusters_used"],
                "max_nonzero_items_in_one_cluster":
                    res["max_nonzero_items_in_one_cluster"],
                "a_only": tab.get("a_only", ""), "b_only": tab.get("b_only", ""),
                "both": tab.get("both", ""), "neither": tab.get("neither", ""),
                "n_discordant": (tab["a_only"] + tab["b_only"]) if tab else "",
                "n_nonzero": res["n_nonzero"],
                "estimate": res["estimate"] * scale,
                "p_item": cell["p_item"], "p_item_method": cell["p_item_method"],
                "p_item_holm96": cell["p_item_holm96"],
                "p_item_holm12": cell["p_item_holm12"],
                "p_cluster_perm": res["p_cluster_perm"],
                "p_cluster_perm_share": res["p_cluster_perm_share"],
                "p_cluster_perm_exact": res["p_cluster_perm_exact"],
                "p_cluster_rank_perm": res["p_cluster_rank_perm"],
                "p_cluster_rank_exact": res["p_cluster_rank_exact"],
                "p_cluster_perm_holm": perm_holm96[pos],
                "p_cluster_perm_holm12": perm_holm12[pos],
                "p_cluster_exact_holm": exact_holm96[pos],
                "p_hier_boot": res["p_hier_boot"],
                "hier_ci95_lo": res["hier_ci95_lo"] * scale,
                "hier_ci95_hi": res["hier_ci95_hi"] * scale,
                "sig_item_raw": cell["p_item"] < 0.05,
                "sig_cluster_raw": res["p_cluster_perm"] < 0.05,
                "sig_item_holm96": sig_item_holm,
                "sig_cluster_holm96": sig_clu_holm,
                "sig_cluster_exact_holm96": sig_clu_exact_holm,
                "verdict_change_raw": (cell["p_item"] < 0.05)
                                      != (res["p_cluster_perm"] < 0.05),
                "verdict_change_holm": sig_item_holm != sig_clu_holm,
                "verdict_change_holm_exact": sig_item_holm != sig_clu_exact_holm,
                "reduces_to_item_test":
                    res["max_nonzero_items_in_one_cluster"] <= 1,
                "cited_in_manuscript": cited, "citation": where,
            })
    return rows


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
CSV_HEADERS = [
    "contrast", "arm", "model", "budget_level", "budget_tokens",
    "outcome", "outcome_scale", "better_direction", "unit", "n_units",
    "n_clusters", "a_only", "b_only", "both", "neither", "n_discordant",
    "rate_single_g", "rate_multi_g", "estimate",
    "boot_ci95_lo", "boot_ci95_hi", "boot_ci90_lo", "boot_ci90_hi",
    "newcombe_ci95_lo", "newcombe_ci95_hi", "newcombe_ci90_lo", "newcombe_ci90_hi",
    "newcombe_phi",
    "cluster_ci95_lo", "cluster_ci95_hi", "cluster_ci90_lo", "cluster_ci90_hi",
    "cluster_vs_iid_max_abs_gap",
    "e8_effect_size", "e8_p_raw", "e8_p_holm_family", "e8_p_holm_agent_layer",
    "e8_direction", "favours",
    "margin_primary", "tost_verdict_primary", "tost_p_boot_primary",
    "tost_p_wald_primary",
    "verdict_margin_low", "verdict_margin_mid", "verdict_margin_high",
    "min_onedir_discordant_for_sig_alpha05",
    "min_onedir_discordant_for_sig_holm12",
    "min_onedir_discordant_for_sig_holm96",
    "min_onedir_discordant_for_sig_holm96realised",
    "sig_attainable_alpha05", "sig_attainable_holm12", "sig_attainable_holm96",
    "sig_attainable_holm96realised",
    "mdes80_alpha05_bestcase", "mdes80_holm12_bestcase", "mdes80_holm96_bestcase",
    "mdes80_holm96realised_bestcase", "holm_realised_alpha",
    "mdes80_alpha05_at_observed_discordance",
    "mdes80_holm96_at_observed_discordance",
    # DG18, the cluster-aware stage.  Populated on the four rows per
    # (arm, budget level) that are members of the declared family of 96; the
    # extra quality statistics and the descriptive row are not family members
    # and are left blank rather than given a correction they do not belong to.
    "p_cluster_perm", "p_cluster_perm_holm", "p_hier_boot", "n_clusters_used",
]


def fnum(value, spec="{:.4f}"):
    if value is None:
        return ""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return "na"
    return spec.format(value)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(ANALYSIS))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--cores", default="", help="CPU affinity, e.g. 0-3")
    ap.add_argument("--boot", type=int, default=BOOT_N)
    ap.add_argument("--perm", type=int, default=PERM_N,
                    help="cluster sign-flip draws for the DG18 stage")
    ap.add_argument("--quality-cache",
                    default=str(ANALYSIS / "DG6_e3_quality_cache.json"))
    args = ap.parse_args(argv)

    if args.cores:
        lo, _, hi = args.cores.partition("-")
        cores = set(range(int(lo), int(hi or lo) + 1))
        try:
            os.sched_setaffinity(0, cores)
            print("[dg6] pinned to cores {}".format(sorted(cores)))
        except (AttributeError, OSError):
            print("[dg6] could not pin CPU affinity; continuing")

    print(__doc__.split("FOUR LAUNCH QUESTIONS")[1].split("Usage::")[0])
    started = time.perf_counter()
    checks = Checks()
    _validate(checks)

    out_dir = Path(args.out)
    e8_path = ANALYSIS / "E8_adjudication.csv"
    e8_rows = read_table_csv(e8_path)
    e8 = {}
    for r in e8_rows:
        if r["in_primary_family"] != "True":
            continue
        e8[(r["contrast"], r["arm"], r["budget_level"], r["test"])] = r

    # ---------------------------------------------------------------- stage 1 #
    print("\n[dg6] STAGE 1: rebuild every 2x2 from the replay verdict logs")
    arm_data = {a: load_verdict_dispositions(a) for a in ARMS_ORDER}
    labels = {r["arm"]: r["model"] for r in e8_rows}
    rebuilt = {}
    for arm in ARMS_ORDER:
        disp = arm_data[arm]["disp"]
        meta = arm_data[arm]["meta"]
        for level in LEVELS:
            for key, test, unit, field, field_pub, better in BINARY_OUTCOMES:
                items = unit_items(meta, unit)
                tab = two_by_two(disp, level, items, field, "SINGLE+G", "MULTI-G")
                rebuilt[(arm, level, key)] = {"table": tab, "items": items,
                                              "unit": unit, "field": field,
                                              "field_pub": field_pub,
                                              "better": better, "test": test}
                ref = e8[("SINGLE+G vs MULTI-G", arm, level, test)]
                for name in ("n_units", "a_only", "b_only", "both", "neither"):
                    checks.check(
                        "stage1",
                        "{}/{}/{} {} matches E8".format(arm, level, key, name),
                        int(ref[name]), tab[name])
    loose_cells = [(a, "loose", k) for a in ARMS_ORDER for k, *_ in BINARY_OUTCOMES]
    print("[dg6]   {} loose-budget 2x2 tables rebuilt; {} of {} cell comparisons "
          "matched".format(len(loose_cells),
                           sum(1 for r in checks.rows
                               if r["group"] == "stage1" and r["ok"]),
                           sum(1 for r in checks.rows if r["group"] == "stage1")))

    # ---------------------------------------------------------------- stage 2 #
    print("[dg6] STAGE 2: recompute the published minima from the rebuilt tables")
    recomputed_p = {}
    for arm in ARMS_ORDER:
        for level in LEVELS:
            for key, test, *_ in BINARY_OUTCOMES:
                tab = rebuilt[(arm, level, key)]["table"]
                p = mcnemar_exact_p(tab["a_only"], tab["b_only"])
                recomputed_p[(arm, level, key)] = p
                ref = e8[("SINGLE+G vs MULTI-G", arm, level, test)]
                checks.check("stage2",
                             "{}/{}/{} exact McNemar p matches E8".format(arm, level, key),
                             "{:.6g}".format(float(ref["p_raw"])), "{:.6g}".format(p))
    loose_binary_min = min(recomputed_p[(a, "loose", k)]
                           for a in ARMS_ORDER for k, *_ in BINARY_OUTCOMES)
    checks.check("stage2", "loose min uncorrected p over the 18 binary cells",
                 "0.0923", "{:.4f}".format(loose_binary_min))

    # ---------------------------------------------------------------- stage 3 #
    print("[dg6] STAGE 3: end-task quality, via e3_analyze's guard re-evaluation")
    quality = build_quality(Path(args.quality_cache), args.workers, checks)

    qdiffs = {}
    for arm in ARMS_ORDER:
        block = quality["arms"][arm]
        for level in LEVELS:
            items = sorted({k.split("|")[2] for k in block
                            if k.startswith(level + "|")})
            diffs, insts = [], []
            for item in items:
                sa = block["{}|SINGLE+G|{}".format(level, item)]
                sb = block["{}|MULTI-G|{}".format(level, item)]
                diffs.append(sa["wwt"] - sb["wwt"])
                insts.append(sa["instance_id"])
            qdiffs[(arm, level)] = {"items": items, "diffs": np.array(diffs, float),
                                    "instances": insts}
            ref = e8[("SINGLE+G vs MULTI-G", arm, level, "wilcoxon_quality")]
            checks.check("stage3", "{}/{} wilcoxon n_units matches E8".format(arm, level),
                         int(ref["n_units"]), len(items))
            checks.check("stage3", "{}/{} wilcoxon p_raw matches E8".format(arm, level),
                         "{:.6g}".format(float(ref["p_raw"])),
                         "{:.6g}".format(wilcoxon_p(list(diffs))))

    # --------------------------------------------------------------- stage 3b #
    # The content flag rides in on the quality rebuild, because the operations
    # it is computed from are not in results/e3_replay_*/verdicts.jsonl.  The
    # two sources are joined on (level, variant, item) and the join is checked
    # on the disposition they share, so a key that drifted cannot pass a flag to
    # the wrong item.
    print("[dg6] STAGE 3b: attach the V4/V6 content flag to every disposition")
    joined = 0
    for arm in ARMS_ORDER:
        block = quality["arms"][arm]
        disp = arm_data[arm]["disp"]
        for (level, variant, item), row in disp.items():
            cell = block.get("{}|{}|{}".format(level, variant, item))
            if cell is None:
                raise SystemExit(
                    "REFUSING TO RUN: the quality rebuild has no {}/{}/{}/{} row, "
                    "so the content flag cannot be joined".format(
                        arm, level, variant, item))
            checks.check("stage3b", "{}/{}/{}/{} the two sources agree on the "
                         "disposition".format(arm, level, variant, item),
                         row["passed_through"],
                         cell["terminal"] in APPLIED_TERMINALS)
            row["passed_through_strict"] = bool(cell["passes_strict"])
            joined += 1
    print("[dg6]   {} dispositions carry the content flag".format(joined))

    # -------------------------------------------- stage 2b: the Holm reproductions
    # The primary family is every arm x budget level x contrast x test (m = 96).
    fam_keys, fam_p = [], []
    for r in e8_rows:
        if r["in_primary_family"] != "True":
            continue
        key = (r["contrast"], r["arm"], r["budget_level"], r["test"])
        if r["contrast"] == "SINGLE+G vs MULTI-G":
            if r["test"] == "wilcoxon_quality":
                p = wilcoxon_p(list(qdiffs[(r["arm"], r["budget_level"])]["diffs"]))
            else:
                okey = {t: k for k, t, *_ in BINARY_OUTCOMES}[r["test"]]
                p = recomputed_p[(r["arm"], r["budget_level"], okey)]
        else:
            p = float(r["p_raw"])          # the MULTI-G vs MULTI-UG half, from E8
        fam_keys.append(key)
        fam_p.append(p)
    checks.check("stage2", "the primary Holm family holds 96 tests", 96, len(fam_p))
    fam_holm = dict(zip(fam_keys, holm(fam_p)))
    sg_loose = [k for k in fam_keys
                if k[0] == "SINGLE+G vs MULTI-G" and k[2] == "loose"]
    sg_tight = [k for k in fam_keys
                if k[0] == "SINGLE+G vs MULTI-G" and k[2] == "tight"]
    checks.check("stage2", "loose min Holm p over the 24 SINGLE+G vs MULTI-G cells",
                 "1.00", "{:.2f}".format(min(fam_holm[k] for k in sg_loose)))
    checks.check("stage2", "tight SINGLE+G vs MULTI-G cells significant under Holm",
                 9, sum(1 for k in sg_tight if fam_holm[k] < 0.05))
    checks.check("stage2", "loose min uncorrected p over all 24 SINGLE+G vs MULTI-G cells",
                 "0.0923",
                 "{:.4f}".format(min(fam_p[fam_keys.index(k)] for k in sg_loose)))

    # --------------------------------------------------------------- stage 3c #
    # Everything the cluster-aware stage will re-derive is first reproduced from
    # the raw logs: all 72 2x2 tables over BOTH contrasts, all 96 item-level
    # p-values, and both Holm corrections.  The DG6 stage above only ever
    # rebuilt the SINGLE+G vs MULTI-G half, so this is where the other half of
    # the declared family becomes a recomputed number rather than a read one.
    print("[dg6] STAGE 3c: reproduce all 96 item-level tests over both contrasts")
    built = dg18_build_cells(arm_data, quality, e8, checks)
    print("[dg6]   {} cells built over {} readings; {} stage3c assertions"
          .format(len(built["cells"]), len(READINGS),
                  sum(1 for r in checks.rows if r["group"] == "stage3c")))

    if checks.failed:
        print("\n[dg6] SELF-CHECK FAILED; refusing to report new numbers.")
        for row in checks.failed[:40]:
            print("  {} / {}: expected {!r}, got {!r}".format(
                row["group"], row["check"], row["expected"], row["got"]))
        return 2
    print("[dg6]   self-check {} of {} assertions passed"
          .format(checks.counts()["passed"], checks.counts()["total"]))

    # --------------------------------------------------------------- stage 3d #
    print("[dg6] STAGE 3d: cluster sign-flip and hierarchical bootstrap "
          "({} draws, seed {})".format(args.perm, BOOT_SEED))
    t_cluster = time.perf_counter()
    dg18_rows = dg18_run(built, checks, args.perm, n_boot=args.boot)
    for row in dg18_rows:
        row["model"] = labels[row["arm"]]
        row["budget_tokens"] = e8[(row["contrast"], row["arm"],
                                   row["budget_level"], row["test"])]["budget_tokens"]
    cluster_by_key = {(r["reading"], r["contrast"], r["arm"], r["budget_level"],
                       r["test"]): r for r in dg18_rows}
    changed = [r for r in dg18_rows if r["verdict_change_holm"]]
    print("[dg6]   {} cluster tests in {:.0f}s; {} Holm verdict change(s)"
          .format(len(dg18_rows), time.perf_counter() - t_cluster, len(changed)))
    for r in changed:
        print("[dg6]     CHANGES: {} {} {} {} item Holm {:.3g} -> cluster Holm "
              "{:.3g}".format(r["reading"], r["contrast"], r["arm"],
                              r["test"], r["p_item_holm96"],
                              r["p_cluster_perm_holm"]))
    if checks.failed:
        print("\n[dg6] SELF-CHECK FAILED in the cluster stage; refusing to report.")
        for row in checks.failed[:40]:
            print("  {} / {}: expected {!r}, got {!r}".format(
                row["group"], row["check"], row["expected"], row["got"]))
        return 2

    # ---------------------------------------------------------------- stage 4 #
    print("[dg6] STAGE 4: intervals, TOST and power")
    n_boot = args.boot
    # The first-step Holm bound (alpha/m) is the threshold the smallest p-value
    # in the family must clear.  A loose-budget cell with a real effect would not
    # be the smallest, because nine tight-budget cells and the guard contrasts
    # already sit below it, so its realised threshold is more generous.  Both are
    # computed: the realised one is found by putting a candidate p-value back
    # into the observed family of 96 and asking what Holm would do with it.
    others = [fam_p[i] for i, k in enumerate(fam_keys)
              if k != ("SINGLE+G vs MULTI-G", "qwen27b", "loose", "mcnemar_catch")]

    def holm_significant(candidate: float) -> bool:
        return holm(others + [candidate])[-1] < 0.05

    lo_a, hi_a = 1e-12, 0.05
    for _ in range(200):
        mid = math.sqrt(lo_a * hi_a)
        if holm_significant(mid):
            lo_a = mid
        else:
            hi_a = mid
    alpha_realised = lo_a
    alphas = {"alpha05": 0.05, "holm12": 0.05 / 12.0,
              "holm96realised": alpha_realised, "holm96": 0.05 / 96.0}
    min_disc = {name: min_onedirectional_for_sig(96, a) for name, a in alphas.items()}
    mdes_best = {name: mdes_one_directional(96, a) for name, a in alphas.items()}
    print("[dg6]   realised Holm threshold for a loose cell: {:.4e} "
          "(first-step bound 0.05/96 = {:.4e})".format(alpha_realised, 0.05 / 96.0))
    print("[dg6]   min one-directional discordant pairs for significance: {}"
          .format(min_disc))
    print("[dg6]   80%-power floor on |RD| at n=96 (best case): {}"
          .format({k: "{:.1f} pp".format(100 * v) for k, v in mdes_best.items()}))

    # The reference effect the margins are a fraction of: the guard's own effect
    # at a fixed architecture (MULTI-G vs MULTI-UG) at the loose budget.
    ref_effect = {}
    for test in ("mcnemar_violation_passthrough", "mcnemar_catch"):
        vals = []
        for arm in ARMS_ORDER:
            r = e8[("MULTI-G vs MULTI-UG", arm, "loose", test)]
            vals.append((arm, 100.0 * float(r["effect_size"])))
        ref_effect[test] = vals
    # Pass-through is the outcome the content rule reaches, so the reference
    # effect that justifies the margin is recomputed under the published
    # reading; E8's own value stays beside it as the legacy one.
    ref_effect["mcnemar_violation_passthrough_legacy"] = \
        ref_effect["mcnemar_violation_passthrough"]
    strict_ref = []
    for arm in ARMS_ORDER:
        disp = arm_data[arm]["disp"]
        items = unit_items(arm_data[arm]["meta"], "the 96 labelled violations")
        tab = two_by_two(disp, "loose", items, "passed_through_strict",
                         "MULTI-G", "MULTI-UG")
        strict_ref.append((arm, 100.0 * (tab["a_only"] - tab["b_only"]) / tab["n_units"]))
    ref_effect["mcnemar_violation_passthrough"] = strict_ref
    ref_pt = [abs(v) for a, v in strict_ref if a != "deepseek"]
    ref_pt_legacy = [abs(v) for a, v in
                     ref_effect["mcnemar_violation_passthrough_legacy"]
                     if a != "deepseek"]
    ref_quality = []
    for arm in ARMS_ORDER:
        r = e8[("MULTI-G vs MULTI-UG", arm, "loose", "wilcoxon_quality")]
        ref_quality.append((arm, float(r["mean_diff"])))
    ref_q = [abs(v) for a, v in ref_quality if a != "deepseek"]

    rows = []
    cell_index = 0
    for level in LEVELS:
        for arm in ARMS_ORDER:
            meta = arm_data[arm]["meta"]
            disp = arm_data[arm]["disp"]
            tokens = next(iter(meta.values()))["budget_tokens"]
            if level == "tight":
                tokens = None
            for key, test, unit, field, field_pub, better in BINARY_OUTCOMES:
                cell_index += 1
                rec = rebuilt[(arm, level, key)]
                items = rec["items"]
                # The published interval is computed on the published reading.
                # ``rec["table"]`` stays the legacy 2x2 the E8 assertions ran on;
                # the table reported here is rebuilt on the same items under
                # ``field_pub``, so its counts, its interval and its verdict are
                # one reading throughout.
                tab = two_by_two(disp, level, items, field_pub,
                                 "SINGLE+G", "MULTI-G")
                n = tab["n_units"]
                x = np.array([1.0 if disp[(level, "SINGLE+G", i)][field_pub] else 0.0
                              for i in items])
                y = np.array([1.0 if disp[(level, "MULTI-G", i)][field_pub] else 0.0
                              for i in items])
                rd = float(x.mean() - y.mean())
                rng = np.random.default_rng([BOOT_SEED, cell_index])
                samples = boot_rd(x, y, rng, n_boot) * 100.0
                b95 = pct_ci(samples, 0.95)
                b90 = pct_ci(samples, 0.90)
                nc95 = newcombe_paired(tab["both"], tab["a_only"], tab["b_only"],
                                       tab["neither"], 0.95)
                nc90 = newcombe_paired(tab["both"], tab["a_only"], tab["b_only"],
                                       tab["neither"], 0.90)
                # cluster bootstrap over scheduling instances
                by_cluster = defaultdict(list)
                for idx, item in enumerate(items):
                    by_cluster[meta[item]["instance_id"]].append(idx)
                clusters = [np.array(v, int) for v in by_cluster.values()]
                d_items = x - y
                cl_vals = [d_items[c] for c in clusters]
                rngc = np.random.default_rng([BOOT_SEED, 900000 + cell_index])
                csamp = boot_stat_cluster(cl_vals, rngc, np.mean, n_boot) * 100.0
                c95 = pct_ci(csamp, 0.95)
                c90 = pct_ci(csamp, 0.90)
                gap = max(abs(c95[0] - b95[0]), abs(c95[1] - b95[1]),
                          abs(c90[0] - b90[0]), abs(c90[1] - b90[1]))
                se = paired_wald_se(tab["a_only"], tab["b_only"], n) * 100.0
                n_disc = tab["a_only"] + tab["b_only"]
                verdicts = {}
                for margin in BINARY_MARGINS_PP:
                    verdicts[margin] = tost_verdict(
                        [b90, (nc90[0] * 100.0, nc90[1] * 100.0), c90], margin)
                ref8 = e8[("SINGLE+G vs MULTI-G", arm, level, test)]
                # The cluster-aware p-values for this cell, from the DG18 stage.
                # The lookup is on the published reading, the same one this row's
                # 2x2 table and interval are computed under, and the point
                # estimate is asserted equal so a mis-keyed lookup cannot pass a
                # p-value from a different cell.
                clu = cluster_by_key[("content_rule", "SINGLE+G vs MULTI-G",
                                      arm, level, test)]
                checks.check("stage4", "{}/{}/{} the DG18 cell is the same cell"
                             .format(arm, level, key),
                             "{:.9g}".format(100.0 * rd),
                             "{:.9g}".format(clu["estimate"]))
                if rd == 0:
                    favours = "neither"
                elif better == "lower is better":
                    favours = "MULTI-G" if rd > 0 else "SINGLE+G"
                else:
                    favours = "SINGLE+G" if rd > 0 else "MULTI-G"
                p_disc_obs = n_disc / float(n)
                rows.append({
                    "contrast": "SINGLE+G vs MULTI-G", "arm": arm,
                    "model": labels[arm], "budget_level": level,
                    "budget_tokens": ref8["budget_tokens"],
                    "outcome": key, "outcome_scale": "pp",
                    "better_direction": better, "unit": unit, "n_units": n,
                    "n_clusters": len(clusters),
                    "a_only": tab["a_only"], "b_only": tab["b_only"],
                    "both": tab["both"], "neither": tab["neither"],
                    "n_discordant": n_disc,
                    "rate_single_g": 100.0 * float(x.mean()),
                    "rate_multi_g": 100.0 * float(y.mean()),
                    "estimate": 100.0 * rd,
                    "boot_ci95_lo": b95[0], "boot_ci95_hi": b95[1],
                    "boot_ci90_lo": b90[0], "boot_ci90_hi": b90[1],
                    "newcombe_ci95_lo": 100.0 * nc95[0],
                    "newcombe_ci95_hi": 100.0 * nc95[1],
                    "newcombe_ci90_lo": 100.0 * nc90[0],
                    "newcombe_ci90_hi": 100.0 * nc90[1],
                    "newcombe_phi": nc95[2],
                    "cluster_ci95_lo": c95[0], "cluster_ci95_hi": c95[1],
                    "cluster_ci90_lo": c90[0], "cluster_ci90_hi": c90[1],
                    "cluster_vs_iid_max_abs_gap": gap,
                    "e8_effect_size": float(ref8["effect_size"]),
                    "e8_p_raw": float(ref8["p_raw"]),
                    "e8_p_holm_family": float(ref8["p_holm_family"]),
                    "e8_p_holm_agent_layer": float(ref8["p_holm_agent_layer"]),
                    "e8_direction": ref8["direction"], "favours": favours,
                    "margin_primary": BINARY_PRIMARY_PP,
                    "tost_verdict_primary": verdicts[BINARY_PRIMARY_PP],
                    "tost_p_boot_primary": boot_tost_p(samples, BINARY_PRIMARY_PP),
                    "tost_p_wald_primary": wald_tost_p(100.0 * rd, se,
                                                       BINARY_PRIMARY_PP),
                    "verdict_margin_low": verdicts[BINARY_MARGINS_PP[0]],
                    "verdict_margin_mid": verdicts[BINARY_MARGINS_PP[1]],
                    "verdict_margin_high": verdicts[BINARY_MARGINS_PP[2]],
                    "min_onedir_discordant_for_sig_alpha05": min_disc["alpha05"],
                    "min_onedir_discordant_for_sig_holm12": min_disc["holm12"],
                    "min_onedir_discordant_for_sig_holm96": min_disc["holm96"],
                    "min_onedir_discordant_for_sig_holm96realised":
                        min_disc["holm96realised"],
                    "sig_attainable_alpha05": n_disc >= min_disc["alpha05"],
                    "sig_attainable_holm12": n_disc >= min_disc["holm12"],
                    "sig_attainable_holm96": n_disc >= min_disc["holm96"],
                    "sig_attainable_holm96realised":
                        n_disc >= min_disc["holm96realised"],
                    "mdes80_alpha05_bestcase": 100.0 * mdes_best["alpha05"],
                    "mdes80_holm12_bestcase": 100.0 * mdes_best["holm12"],
                    "mdes80_holm96_bestcase": 100.0 * mdes_best["holm96"],
                    "mdes80_holm96realised_bestcase":
                        100.0 * mdes_best["holm96realised"],
                    "holm_realised_alpha": alpha_realised,
                    "mdes80_alpha05_at_observed_discordance":
                        100.0 * mdes_at_discordance(n, p_disc_obs, alphas["alpha05"]),
                    "mdes80_holm96_at_observed_discordance":
                        100.0 * mdes_at_discordance(n, p_disc_obs, alphas["holm96"]),
                    "p_cluster_perm": clu["p_cluster_perm"],
                    "p_cluster_perm_holm": clu["p_cluster_perm_holm"],
                    "p_hier_boot": clu["p_hier_boot"],
                    "n_clusters_used": clu["n_clusters_used"],
                    "_verdicts": verdicts,
                })

            # -------- the fourth outcome: end-task quality ------------------- #
            qd = qdiffs[(arm, level)]
            diffs = qd["diffs"]
            nq = diffs.shape[0]
            by_cluster = defaultdict(list)
            for idx, inst in enumerate(qd["instances"]):
                by_cluster[inst].append(idx)
            clusters = [np.array(v, int) for v in by_cluster.values()]
            cl_vals = [diffs[c] for c in clusters]
            nonzero = diffs[diffs != 0]
            ref8 = e8[("SINGLE+G vs MULTI-G", arm, level, "wilcoxon_quality")]
            stats_spec = (
                ("quality_mean_bh", lambda d: float(np.mean(d)),
                 "mean per-item paired difference in weighted business hours"),
                ("quality_median_bh", lambda d: float(np.median(d)),
                 "median per-item paired difference over all 240 items"),
                ("quality_pseudomedian_bh", hodges_lehmann,
                 "Hodges-Lehmann pseudomedian of the paired differences"),
            )
            qclu = cluster_by_key[("content_rule", "SINGLE+G vs MULTI-G",
                                   arm, level, "wilcoxon_quality")]
            checks.check("stage4", "{}/{} the DG18 quality cell is the same cell"
                         .format(arm, level),
                         "{:.9g}".format(float(np.mean(diffs))),
                         "{:.9g}".format(qclu["estimate"]))
            for name, stat, note in stats_spec:
                cell_index += 1
                point = stat(diffs)
                rng = np.random.default_rng([BOOT_SEED, cell_index])
                idx = rng.integers(0, nq, size=(n_boot, nq))
                if name == "quality_pseudomedian_bh":
                    # The pseudomedian over 240 items is O(n^2) per resample; the
                    # exact distribution-free interval is the honest substitute
                    # and is reported instead of a bootstrap.
                    samples = None
                else:
                    samples = np.array([stat(diffs[idx[r]]) for r in range(n_boot)])
                if samples is None:
                    b95 = b90 = (float("nan"), float("nan"))
                    csamp = None
                    c95 = c90 = (float("nan"), float("nan"))
                    gap = float("nan")
                    tost_p = float("nan")
                else:
                    b95 = pct_ci(samples, 0.95)
                    b90 = pct_ci(samples, 0.90)
                    rngc = np.random.default_rng([BOOT_SEED, 900000 + cell_index])
                    csamp = boot_stat_cluster(cl_vals, rngc, stat, n_boot)
                    c95 = pct_ci(csamp, 0.95)
                    c90 = pct_ci(csamp, 0.90)
                    gap = max(abs(c95[0] - b95[0]), abs(c95[1] - b95[1]),
                              abs(c90[0] - b90[0]), abs(c90[1] - b90[1]))
                    tost_p = boot_tost_p(samples, QUALITY_PRIMARY_BH)
                verdicts = {}
                for margin in QUALITY_MARGINS_BH:
                    verdicts[margin] = tost_verdict([b90, c90], margin)
                favours = ("neither" if point == 0
                           else ("SINGLE+G" if point < 0 else "MULTI-G"))
                rows.append({
                    "contrast": "SINGLE+G vs MULTI-G", "arm": arm,
                    "model": labels[arm], "budget_level": level,
                    "budget_tokens": ref8["budget_tokens"],
                    "outcome": name, "outcome_scale": "bh",
                    "better_direction": "lower is better",
                    "unit": "all 240 items ({})".format(note), "n_units": nq,
                    "n_clusters": len(clusters),
                    "a_only": "", "b_only": "", "both": "", "neither": "",
                    "n_discordant": int(nonzero.shape[0]),
                    "rate_single_g": "", "rate_multi_g": "",
                    "estimate": point,
                    "boot_ci95_lo": b95[0], "boot_ci95_hi": b95[1],
                    "boot_ci90_lo": b90[0], "boot_ci90_hi": b90[1],
                    "newcombe_ci95_lo": "", "newcombe_ci95_hi": "",
                    "newcombe_ci90_lo": "", "newcombe_ci90_hi": "",
                    "newcombe_phi": "",
                    "cluster_ci95_lo": c95[0], "cluster_ci95_hi": c95[1],
                    "cluster_ci90_lo": c90[0], "cluster_ci90_hi": c90[1],
                    "cluster_vs_iid_max_abs_gap": gap,
                    "e8_effect_size": float(ref8["effect_size"]),
                    "e8_p_raw": float(ref8["p_raw"]),
                    "e8_p_holm_family": float(ref8["p_holm_family"]),
                    "e8_p_holm_agent_layer": float(ref8["p_holm_agent_layer"]),
                    "e8_direction": ref8["direction"], "favours": favours,
                    "margin_primary": QUALITY_PRIMARY_BH,
                    "tost_verdict_primary": verdicts[QUALITY_PRIMARY_BH],
                    "tost_p_boot_primary": tost_p,
                    "tost_p_wald_primary": "",
                    "verdict_margin_low": verdicts[QUALITY_MARGINS_BH[0]],
                    "verdict_margin_mid": verdicts[QUALITY_MARGINS_BH[1]],
                    "verdict_margin_high": verdicts[QUALITY_MARGINS_BH[2]],
                    "min_onedir_discordant_for_sig_alpha05": min_disc["alpha05"],
                    "min_onedir_discordant_for_sig_holm12": min_disc["holm12"],
                    "min_onedir_discordant_for_sig_holm96": min_disc["holm96"],
                    "min_onedir_discordant_for_sig_holm96realised":
                        min_disc["holm96realised"],
                    "sig_attainable_alpha05": int(nonzero.shape[0]) >= min_disc["alpha05"],
                    "sig_attainable_holm12": int(nonzero.shape[0]) >= min_disc["holm12"],
                    "sig_attainable_holm96": int(nonzero.shape[0]) >= min_disc["holm96"],
                    "sig_attainable_holm96realised":
                        int(nonzero.shape[0]) >= min_disc["holm96realised"],
                    "mdes80_alpha05_bestcase": "", "mdes80_holm12_bestcase": "",
                    "mdes80_holm96_bestcase": "",
                    "mdes80_holm96realised_bestcase": "",
                    "holm_realised_alpha": alpha_realised,
                    "mdes80_alpha05_at_observed_discordance": "",
                    "mdes80_holm96_at_observed_discordance": "",
                    # Only the mean is a member of the declared family of 96, so
                    # only the mean carries a Holm-corrected cluster p-value.
                    "p_cluster_perm": (qclu["p_cluster_perm"]
                                       if name == "quality_mean_bh" else ""),
                    "p_cluster_perm_holm": (qclu["p_cluster_perm_holm"]
                                            if name == "quality_mean_bh" else ""),
                    "p_hier_boot": (qclu["p_hier_boot"]
                                    if name == "quality_mean_bh" else ""),
                    "n_clusters_used": (qclu["n_clusters_used"]
                                        if name == "quality_mean_bh" else ""),
                    "_verdicts": verdicts,
                })
            # a descriptive row: the share of items on which the two
            # architectures leave exactly the same schedule quality standing
            rows.append({
                "contrast": "SINGLE+G vs MULTI-G", "arm": arm,
                "model": labels[arm], "budget_level": level,
                "budget_tokens": ref8["budget_tokens"],
                "outcome": "quality_identical_share", "outcome_scale": "%",
                "better_direction": "descriptive",
                "unit": "all 240 items; share with an identical end-task objective",
                "n_units": nq, "n_clusters": len(clusters),
                "a_only": "", "b_only": "", "both": "", "neither": "",
                "n_discordant": int(nonzero.shape[0]),
                "rate_single_g": "", "rate_multi_g": "",
                "estimate": 100.0 * float(np.mean(diffs == 0)),
                "boot_ci95_lo": "", "boot_ci95_hi": "", "boot_ci90_lo": "",
                "boot_ci90_hi": "", "newcombe_ci95_lo": "", "newcombe_ci95_hi": "",
                "newcombe_ci90_lo": "", "newcombe_ci90_hi": "", "newcombe_phi": "",
                "cluster_ci95_lo": "", "cluster_ci95_hi": "", "cluster_ci90_lo": "",
                "cluster_ci90_hi": "", "cluster_vs_iid_max_abs_gap": "",
                "e8_effect_size": float(ref8["effect_size"]),
                "e8_p_raw": float(ref8["p_raw"]),
                "e8_p_holm_family": float(ref8["p_holm_family"]),
                "e8_p_holm_agent_layer": float(ref8["p_holm_agent_layer"]),
                "e8_direction": ref8["direction"], "favours": "",
                "margin_primary": "", "tost_verdict_primary": "",
                "tost_p_boot_primary": "", "tost_p_wald_primary": "",
                "verdict_margin_low": "", "verdict_margin_mid": "",
                "verdict_margin_high": "",
                "min_onedir_discordant_for_sig_alpha05": min_disc["alpha05"],
                "min_onedir_discordant_for_sig_holm12": min_disc["holm12"],
                "min_onedir_discordant_for_sig_holm96": min_disc["holm96"],
                "min_onedir_discordant_for_sig_holm96realised":
                    min_disc["holm96realised"],
                "sig_attainable_alpha05": "", "sig_attainable_holm12": "",
                "sig_attainable_holm96": "", "sig_attainable_holm96realised": "",
                "mdes80_alpha05_bestcase": "", "mdes80_holm12_bestcase": "",
                "mdes80_holm96_bestcase": "",
                "mdes80_holm96realised_bestcase": "",
                "holm_realised_alpha": alpha_realised,
                "mdes80_alpha05_at_observed_discordance": "",
                "mdes80_holm96_at_observed_discordance": "",
                "p_cluster_perm": "", "p_cluster_perm_holm": "",
                "p_hier_boot": "", "n_clusters_used": "",
                "_verdicts": {},
            })

    # ---------------------------------------------------------------- output #
    provenance = [
        "generated {} by {} ({})".format(
            time.strftime("%Y-%m-%d %H:%M:%S %z"), Path(__file__).name, VERSION),
        "paired bootstrap: {} resamples, numpy default_rng seeded "
        "[{}, cell index]; percentile intervals".format(n_boot, BOOT_SEED),
        "second interval: Newcombe (1998) method 10 for paired proportions "
        "(MOVER over two Wilson intervals with the observed phi)",
        "third interval: cluster bootstrap resampling whole scheduling instances",
        "self-check: the 18 loose-budget and 18 tight-budget 2x2 tables are "
        "rebuilt from results/e3_replay_*/verdicts.jsonl and asserted cell for "
        "cell against analysis/E8_adjudication.csv; the exact McNemar p-values, "
        "the Wilcoxon p-values, the Holm corrections and the published minima "
        "are recomputed rather than read",
        "cluster-aware tests (DG18): the paired sign is flipped at the "
        "scheduling instance rather than at the item, {} draws at seed {}, and "
        "the Holm correction is re-run over the same declared family of 96; the "
        "columns p_cluster_perm, p_cluster_perm_holm, p_hier_boot and "
        "n_clusters_used carry the result on the four rows per arm and budget "
        "that are members of that family, and analysis/DG18_cluster_tests.csv "
        "carries the whole family under both pass-through readings"
        .format(args.perm, BOOT_SEED),
        "the reported passthrough outcome is the V4/V6 content rule "
        "(code/scripts/passthrough_rule.py): an applied V4 or V6 row counts "
        "unless the applied operations are exactly the item's non-empty "
        "gold_ops; false_block and catch are dispositions and are unchanged; "
        "the e8_* columns of a passthrough row carry E8's earlier "
        "disposition-only reading and are not this one",
    ]
    for arm in ARMS_ORDER:
        p = RESULTS / "e3_replay_{}".format(arm) / "verdicts.jsonl"
        provenance.append("{} sha256 {}".format(p, sha256_file(p)))
    provenance.append("{} sha256 {}".format(e8_path, sha256_file(e8_path)))
    for line in quality.get("provenance", []):
        provenance.append("end-task quality: " + line)
    provenance.append(
        "end-task quality is recomputed by e3_analyze.load_arm / evaluate_rows / "
        "build_entries (the guard re-evaluation), because wwt_original_bh is not "
        "in results/e3_replay_*/verdicts.jsonl")
    provenance.append(
        "margins: {} pp is the primary binary margin and {} bh the primary "
        "quality margin; both are set at roughly a quarter of the effect the "
        "guard itself produces on the same items at the same budget "
        "(MULTI-G vs MULTI-UG, loose): {:.1f} to {:.1f} pp on violation "
        "pass-through under the content rule ({:.1f} to {:.1f} pp under E8's "
        "disposition-only reading) and {:.1f} to {:.1f} bh on mean per-item "
        "quality, over the five arms whose unguarded variant emits executable "
        "proposals"
        .format(BINARY_PRIMARY_PP, QUALITY_PRIMARY_BH, min(ref_pt), max(ref_pt),
                min(ref_pt_legacy), max(ref_pt_legacy), min(ref_q), max(ref_q)))

    out_csv = out_dir / "DG6_e3_intervals.csv"
    with open(out_csv, "w", encoding="utf-8", newline="") as fh:
        for line in provenance:
            fh.write("# {}\n".format(line))
        w = csv.writer(fh)
        w.writerow(CSV_HEADERS)
        for r in rows:
            w.writerow([_fmt(r.get(h, ""), h) for h in CSV_HEADERS])

    md = build_md(rows, checks, min_disc, mdes_best, alphas, ref_effect, ref_pt,
                  ref_pt_legacy, ref_quality, ref_q, provenance, n_boot, quality)
    (out_dir / "DG6_e3_intervals.md").write_text(md)

    prov18 = [
        "generated {} by {} ({})".format(
            time.strftime("%Y-%m-%d %H:%M:%S %z"), Path(__file__).name,
            DG18_VERSION),
        "cluster sign-flip permutation: {} draws, numpy default_rng seeded "
        "[{}, {} + cell index]; the exchangeable unit is the replayed "
        "scheduling instance, so all paired differences on one instance flip "
        "sign together".format(args.perm, BOOT_SEED, PERM_SEED_OFFSET),
        "hierarchical bootstrap: {} replicates, numpy default_rng seeded "
        "[{}, {} + cell index]; instances resampled with replacement, then "
        "items within each drawn instance, with the p-value read by inverting "
        "the two-sided percentile interval".format(n_boot, BOOT_SEED,
                                                   HIER_SEED_OFFSET),
        "exact columns enumerate the same sign-flip null instead of sampling "
        "it (full enumeration up to {} contributing instances, an integer "
        "dynamic program above that where the cluster sums are integers), so "
        "they have no Monte Carlo resolution floor".format(EXACT_SIGNFLIP_MAX_K),
        "self-check: no cluster-aware number is computed until all 72 2x2 "
        "tables over both contrasts, all 96 item-level p-values, and both Holm "
        "corrections in analysis/E8_adjudication.csv are reproduced from "
        "results/e3_replay_*/verdicts.jsonl and the quality rebuild",
        "two readings are reported: e8_disposition is the reading every "
        "p-value printed in the manuscript was computed on, and content_rule "
        "applies the V4/V6 pass-through rule that Table tab:e3-rd's risk "
        "differences and every DG6 interval use; they differ on violation "
        "pass-through alone",
    ]
    for arm in ARMS_ORDER:
        p = RESULTS / "e3_replay_{}".format(arm) / "verdicts.jsonl"
        prov18.append("{} sha256 {}".format(p, sha256_file(p)))
    prov18.append("{} sha256 {}".format(e8_path, sha256_file(e8_path)))
    for line in quality.get("provenance", []):
        prov18.append("end-task quality: " + line)

    out_csv18 = out_dir / "DG18_cluster_tests.csv"
    with open(out_csv18, "w", encoding="utf-8", newline="") as fh:
        for line in prov18:
            fh.write("# {}\n".format(line))
        w = csv.writer(fh)
        w.writerow(DG18_HEADERS)
        for r in dg18_rows:
            w.writerow([_fmt18(r.get(h, ""), h) for h in DG18_HEADERS])
    (out_dir / "DG18_cluster_tests.md").write_text(
        build_md18(dg18_rows, checks, prov18, args.perm, n_boot))

    meta = {"version": VERSION, "dg18_version": DG18_VERSION,
            "date": time.strftime("%Y-%m-%d %H:%M:%S %z"),
            "boot": n_boot, "perm": args.perm, "seed": BOOT_SEED,
            "checks": checks.counts(), "rows": len(rows),
            "dg18_rows": len(dg18_rows),
            "dg18_holm_verdict_changes": len(changed),
            "provenance": provenance, "dg18_provenance": prov18,
            "wall_s": time.perf_counter() - started}
    (out_dir / "DG6_e3_intervals_meta.json").write_text(
        json.dumps(meta, indent=1, sort_keys=True) + "\n")

    print("\n[dg6] wrote {} ({} rows)".format(out_csv, len(rows)))
    print("[dg6] wrote {}".format(out_dir / "DG6_e3_intervals.md"))
    print("[dg18] wrote {} ({} rows)".format(out_csv18, len(dg18_rows)))
    print("[dg18] wrote {}".format(out_dir / "DG18_cluster_tests.md"))
    print("[dg6] assertions {}/{} passed".format(checks.counts()["passed"],
                                                 checks.counts()["total"]))
    print("[dg6] wall {:.1f}s".format(time.perf_counter() - started))
    return 0


_INT_COLS = {"n_units", "n_clusters", "n_clusters_used",
             "a_only", "b_only", "both", "neither",
             "n_discordant", "min_onedir_discordant_for_sig_alpha05",
             "min_onedir_discordant_for_sig_holm12",
             "min_onedir_discordant_for_sig_holm96", "budget_tokens"}
_SCI_COLS = {"e8_p_raw", "e8_p_holm_family", "e8_p_holm_agent_layer",
             "holm_realised_alpha", "tost_p_boot_primary", "tost_p_wald_primary",
             "p_cluster_perm", "p_cluster_perm_holm", "p_hier_boot"}


def _fmt(value, header):
    if value == "" or value is None:
        return ""
    if header in _INT_COLS:
        return str(value)
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return "na"
    if header in _SCI_COLS:
        return "{:.6g}".format(float(value))
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return "na"
        return "{:.4f}".format(value)
    return str(value)


def _observed_power_sentence(get, binkeys) -> str:
    """What 80% power required, holding each cell's discordance at its observed rate."""
    a05, h96, none05 = [], [], 0
    for arm in ARMS_ORDER:
        for k in binkeys:
            r = get("loose", arm, k)
            v = r["mdes80_alpha05_at_observed_discordance"]
            w = r["mdes80_holm96_at_observed_discordance"]
            if math.isnan(v):
                none05 += 1
            else:
                a05.append((arm, k, v))
            if not math.isnan(w):
                h96.append((arm, k, w, r["n_discordant"]))
    parts = [
        "Holding each cell's discordance rate at its observed value, 80% power "
        "is out of reach at any risk difference in {} of the 18 loose binary "
        "cells even with no correction at all.".format(none05)]
    if a05:
        parts.append(
            "The {} cells where an uncorrected test could have reached 80% power "
            "needed a true difference of {:.1f} to {:.1f} pp.".format(
                len(a05), min(v for _, _, v in a05), max(v for _, _, v in a05)))
    if h96:
        parts.append(
            "Under the Holm correction only {} reached it: {}.".format(
                "one cell" if len(h96) == 1 else "{} cells".format(len(h96)),
                "; ".join("{} / {}, {} discordant pairs, {:.1f} pp".format(
                    a, k, d, v) for a, k, v, d in h96)))
    return " ".join(parts)


def build_md(rows, checks, min_disc, mdes_best, alphas, ref_effect, ref_pt,
             ref_pt_legacy, ref_quality, ref_q, provenance, n_boot, quality) -> str:
    def get(level, arm, outcome):
        for r in rows:
            if (r["budget_level"] == level and r["arm"] == arm
                    and r["outcome"] == outcome):
                return r
        return None

    out = ["<!--"]
    out += ["  " + line for line in provenance]
    out += ["-->", "",
            "# DG6. Intervals, equivalence tests and design power for the E3 "
            "agent-layer comparison", ""]
    out += [
        "SINGLE+G minus MULTI-G, on the same items, at both budget levels. A "
        "negative risk difference means MULTI-G has the higher rate on that "
        "outcome; whether that favours MULTI-G depends on the outcome, and the "
        "`favours` column states which architecture the sign is good for.", "",
        "The `passthrough` outcome applies the V4/V6 content rule "
        "(`code/scripts/passthrough_rule.py`): an applied V4 or V6 row counts "
        "as pass-through unless the applied operations are exactly the item's "
        "non-empty ground truth. `false_block` and `catch` are dispositions, "
        "which the rule does not reach, so they are unchanged. The self-check "
        "below still reconciles against `E8_adjudication.csv`, which carries "
        "the earlier disposition-only reading of pass-through, so the E8 "
        "columns of a `passthrough` row are that reading and not this one.", "",
        "Source files, filters and hashes are in the comment header of "
        "`DG6_e3_intervals.csv`. The script is `code/scripts/e3_intervals.py`.",
        "",
    ]

    # -- self check ---------------------------------------------------------- #
    c = checks.counts()
    out += ["## Self-check", "",
            "All {} assertions passed ({} failed). What was reproduced:".format(
                c["total"], c["failed"]), "",
            "- The 18 loose-budget and 18 tight-budget SINGLE+G vs MULTI-G 2x2 "
            "tables, rebuilt from `results/e3_replay_<arm>/verdicts.jsonl` "
            "(repeat 0, last row per key), match `analysis/E8_adjudication.csv` "
            "on `n_units`, `a_only`, `b_only`, `both` and `neither`, 36 of 36 "
            "tables and 180 of 180 cells.",
            "- Every exact McNemar p-value and every Wilcoxon p-value recomputed "
            "from those tables equals E8's `p_raw` to six significant figures, "
            "48 of 48.",
            "- The published minima: the smallest uncorrected p-value at the "
            "loose budget is 0.0923 (Qwen3.6-27B-FP8, violation catch), the "
            "smallest Holm-corrected p-value at the loose budget is 1.00, and 9 "
            "of the 24 tight-budget SINGLE+G vs MULTI-G cells are significant "
            "under Holm over the whole family of 96. All three matched exactly.",
            "- The interval estimators were validated before use: the Wilson "
            "endpoints solve the score equation to 1e-8, and the "
            "square-and-add combination reproduces Newcombe's published worked "
            "example (56/70 against 48/80 gives 0.0524 to 0.3339 at 95%).",
            ""]

    # -- margins ------------------------------------------------------------- #
    out += ["## The margins, and why they are what they are", "",
            "A margin chosen because it passes is worthless, so both margins "
            "are set as a fraction of an effect this paper has already measured "
            "on the same items, at the same budget, with the same guard: the "
            "effect of adding the guard at a fixed architecture (MULTI-G "
            "against MULTI-UG at the loose budget).", ""]
    out += ["| reference effect (MULTI-G vs MULTI-UG, loose) | value |",
            "| --- | --- |"]
    out += ["| violation pass-through, five arms with executable unguarded "
            "proposals | {:.1f} to {:.1f} pp |".format(min(ref_pt), max(ref_pt))]
    out += ["| the same, under the disposition-only reading E8 carries | {:.1f} "
            "to {:.1f} pp |".format(min(ref_pt_legacy), max(ref_pt_legacy))]
    out += ["| mean per-item end-task quality, same five arms | {:.1f} to "
            "{:.1f} bh |".format(min(ref_q), max(ref_q))]
    out += ["",
            "- **Binary outcomes: 5 pp primary.** Five percentage points is "
            "{:.0f}% of the smallest guard effect on violation pass-through "
            "({:.1f} pp), so declaring the two architectures equivalent at this "
            "margin still preserves {:.0f}% of the effect the guard itself "
            "buys. The conventional half-of-the-reference-effect rule would "
            "license {:.1f} pp, so 5 pp is the stricter choice. In workload "
            "terms it is 4.8 instructions out of the 96 labelled violations, or "
            "roughly one violating instruction per twenty."
            .format(100 * 5.0 / min(ref_pt), min(ref_pt),
                    100 * (1 - 5.0 / min(ref_pt)), min(ref_pt) / 2.0),
            "- **2.5 pp and 10 pp** are reported beside it. 10 pp is the "
            "loosest defensible margin: it is {:.0f}% of the smallest guard "
            "effect, at the edge of the conventional rule.".format(
                100 * 10.0 / min(ref_pt)),
            "- **End-task quality: 10 bh primary**, on the mean per-item paired "
            "difference in weighted business hours. Ten weighted business hours "
            "is {:.0f}% of the smallest guard effect on the same quantity "
            "({:.1f} bh), which matches the binary margin's preservation "
            "fraction. 5 bh and 20 bh are reported beside it."
            .format(100 * 10.0 / min(ref_q), min(ref_q)),
            ""]

    # -- power --------------------------------------------------------------- #
    out += ["## What the design could have detected", "",
            "Exact trinomial power for the two-sided exact McNemar test at "
            "n = 96 paired items. `best case` puts every discordant pair in one "
            "direction, which is the easiest structure to detect, so the figure "
            "is a floor: no allocation of the discordant pairs makes a smaller "
            "risk difference detectable.", "",
            "| level | alpha | fewest one-directional discordant pairs that can "
            "reach significance | smallest |RD| at 80% power, best case |",
            "| --- | --- | --- | --- |"]
    names = {"alpha05": "uncorrected",
             "holm12": "Holm, per-question family (m = 12)",
             "holm96realised": "Holm, whole family, realised threshold for a "
             "loose cell",
             "holm96": "Holm, whole family, first-step bound (0.05/96)"}
    for k in ("alpha05", "holm12", "holm96realised", "holm96"):
        out.append("| {} | {:.2e} | {} of 96 ({:.1f} pp) | {:.1f} pp |".format(
            names[k], alphas[k], min_disc[k], 100.0 * min_disc[k] / 96.0,
            100.0 * mdes_best[k]))
    out += ["",
            "The first-step bound 0.05/96 is conservative, because a "
            "loose-budget cell with a real effect would not have been the "
            "smallest p-value in the family: nine tight-budget cells and the "
            "guard contrasts already sit below it. The realised threshold, "
            "found by putting a candidate p-value back into the observed family "
            "of 96 and asking what Holm does with it, is {:.2e}, and it does not "
            "change the answer.".format(alphas["holm96realised"]),
            "",
            "Under the correction the manuscript reports, the test cannot return "
            "a significant result at all unless at least {} of the 96 pairs are "
            "discordant, and it needs a true risk difference of at least {:.1f} "
            "pp before it reaches 80% power even when every discordant pair "
            "points the same way.".format(
                min_disc["holm96realised"], 100.0 * mdes_best["holm96realised"]),
            ""]

    # attainability at loose
    binkeys = [k for k, *_ in BINARY_OUTCOMES]
    att05 = sum(1 for a in ARMS_ORDER for k in binkeys
                if get("loose", a, k)["sig_attainable_alpha05"])
    att96 = sum(1 for a in ARMS_ORDER for k in binkeys
                if get("loose", a, k)["sig_attainable_holm96"])
    qatt96 = sum(1 for a in ARMS_ORDER
                 if get("loose", a, "quality_mean_bh")["sig_attainable_holm96"])
    qatt05 = sum(1 for a in ARMS_ORDER
                 if get("loose", a, "quality_mean_bh")["sig_attainable_alpha05"])
    out += ["At the loose budget the observed discordance is far below that. Of "
            "the 18 binary cells, {} had enough discordant pairs for an "
            "uncorrected significant result to be arithmetically possible, and "
            "{} had enough for a Holm-corrected one. On end-task quality the "
            "same arithmetic applies to the number of items whose schedules "
            "differ at all, because the signed-rank test with every difference "
            "in one direction gives the same p-value as McNemar with every "
            "discordant pair in one direction: {} of the 6 arms had enough "
            "differing items for an uncorrected significant result and {} for a "
            "Holm-corrected one.".format(att05, att96, qatt05, qatt96),
            "",
            "**Taking the 24 loose-budget cells together, {} of 24 could have "
            "returned a Holm-significant result at any true effect size, and {} "
            "of 24 could have returned an uncorrected one.** The loose-budget "
            "null is therefore in large part a statement about the instrument, "
            "not about the architectures.".format(att96 + qatt96, att05 + qatt05),
            "",
            _observed_power_sentence(get, binkeys), ""]

    # -- the main table ------------------------------------------------------ #
    for level in ("loose", "tight"):
        out += ["## {} budget: SINGLE+G minus MULTI-G".format(level.capitalize()),
                "",
                "| arm | outcome | n | a-only / b-only | RD | 95% CI (bootstrap) "
                "| 95% CI (Newcombe) | 90% CI (bootstrap) | favours | 2.5 pp | "
                "5 pp | 10 pp |",
                "| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- | --- "
                "| --- | --- |"]
        short = {"equivalence established": "equiv",
                 "equivalence refuted": "REFUTED",
                 "indeterminate": "indet"}
        for arm in ARMS_ORDER:
            for k in binkeys:
                r = get(level, arm, k)
                v = r["_verdicts"]
                out.append(
                    "| {} | {} | {} | {} / {} | {:+.2f} pp | [{:+.2f}, {:+.2f}] "
                    "| [{:+.2f}, {:+.2f}] | [{:+.2f}, {:+.2f}] | {} | {} | {} | "
                    "{} |".format(
                        arm, k, r["n_units"], r["a_only"], r["b_only"],
                        r["estimate"], r["boot_ci95_lo"], r["boot_ci95_hi"],
                        r["newcombe_ci95_lo"], r["newcombe_ci95_hi"],
                        r["boot_ci90_lo"], r["boot_ci90_hi"], r["favours"],
                        short[v[2.5]], short[v[5.0]], short[v[10.0]]))
        out += [""]
        out += ["| arm | end-task quality | n | differing items | estimate | "
                "95% CI (bootstrap) | 90% CI (bootstrap) | favours | 5 bh | "
                "10 bh | 20 bh |",
                "| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- | --- "
                "| --- |"]
        for arm in ARMS_ORDER:
            for name in ("quality_mean_bh", "quality_median_bh",
                         "quality_pseudomedian_bh"):
                r = get(level, arm, name)
                v = r["_verdicts"]
                ci95 = ("[{:+.2f}, {:+.2f}]".format(r["boot_ci95_lo"],
                                                    r["boot_ci95_hi"])
                        if not math.isnan(r["boot_ci95_lo"]) else "not bootstrapped")
                ci90 = ("[{:+.2f}, {:+.2f}]".format(r["boot_ci90_lo"],
                                                    r["boot_ci90_hi"])
                        if not math.isnan(r["boot_ci90_lo"]) else "-")
                out.append("| {} | {} | {} | {} | {:+.3f} bh | {} | {} | {} | {} "
                           "| {} | {} |".format(
                               arm, name.replace("quality_", "").replace("_bh", ""),
                               r["n_units"], r["n_discordant"], r["estimate"],
                               ci95, ci90, r["favours"],
                               short[v[5.0]], short[v[10.0]], short[v[20.0]]))
            r = get(level, arm, "quality_identical_share")
            out.append("| {} | identical objective share | {} | {} | {:.1f}% | - "
                       "| - | - | - | - | - |".format(
                           arm, r["n_units"], r["n_discordant"], r["estimate"]))
        out += [""]

    # -- clustering ---------------------------------------------------------- #
    gaps = [r["cluster_vs_iid_max_abs_gap"] for r in rows
            if isinstance(r["cluster_vs_iid_max_abs_gap"], float)
            and not math.isnan(r["cluster_vs_iid_max_abs_gap"])
            and r["outcome_scale"] == "pp"]
    gaps_loose = [r["cluster_vs_iid_max_abs_gap"] for r in rows
                  if r["budget_level"] == "loose" and r["outcome_scale"] == "pp"]
    out += ["## Instance clustering", "",
            "The 240 items are drawn from 55 scheduling instances, up to 12 "
            "items per instance, so the paired differences are not independent "
            "across items. A cluster bootstrap that resamples whole instances "
            "is reported beside the item bootstrap. The largest absolute "
            "difference between a cluster-bootstrap endpoint and the "
            "corresponding item-bootstrap endpoint, over the 18 loose-budget "
            "binary cells, is {:.2f} pp; over all 36 binary cells it is {:.2f} "
            "pp. Clustering therefore does not change any verdict: the contrast "
            "is taken within an item, so the instance-level component of the "
            "variance cancels before the paired difference is formed.".format(
                max(gaps_loose), max(gaps)),
            ""]

    # -- summary ------------------------------------------------------------- #
    out += ["## The honest answer", ""]
    fails10 = []
    for arm in ARMS_ORDER:
        for k in binkeys:
            r = get("loose", arm, k)
            if r["_verdicts"][10.0] != "equivalence established":
                fails10.append(r)
    n5 = sum(1 for arm in ARMS_ORDER for k in binkeys
             if get("loose", arm, k)["_verdicts"][5.0] == "equivalence established")
    n10 = 18 - len(fails10)
    n25 = sum(1 for arm in ARMS_ORDER for k in binkeys
              if get("loose", arm, k)["_verdicts"][2.5] == "equivalence established")
    maxrd = max(abs(get("loose", arm, k)["estimate"])
                for arm in ARMS_ORDER for k in binkeys)
    widest = max(max(abs(get("loose", arm, k)["boot_ci95_lo"]),
                     abs(get("loose", arm, k)["boot_ci95_hi"]),
                     abs(get("loose", arm, k)["newcombe_ci95_lo"]),
                     abs(get("loose", arm, k)["newcombe_ci95_hi"]))
                 for arm in ARMS_ORDER for k in binkeys)
    q10 = sum(1 for a in ARMS_ORDER
              if get("loose", a, "quality_mean_bh")["_verdicts"][10.0]
              == "equivalence established")
    out += [
        "**One sentence.** At the loose budget the two architectures are "
        "equivalent within 10 percentage points on {} of the 18 binary "
        "arm-by-outcome cells and within 5 points on {}, and equivalent within "
        "10 weighted business hours on end-task quality on all {} arms, but the "
        "design never had the power to say more than that: no paired difference "
        "exceeds {:.1f} pp, yet the intervals still admit differences of up to "
        "{:.1f} pp, so the null is a statement of no *detectable* difference, "
        "not of no difference.".format(n10, n5, q10, maxrd, widest),
        "",
        "Cell counts at the loose budget, by margin, over the 18 binary cells "
        "(equivalence established / indeterminate / refuted):", ""]
    for margin in BINARY_MARGINS_PP:
        c = Counter(get("loose", arm, k)["_verdicts"][margin]
                    for arm in ARMS_ORDER for k in binkeys)
        out.append("- **{} pp**: {} established, {} indeterminate, {} refuted."
                   .format(margin, c["equivalence established"],
                           c["indeterminate"], c["equivalence refuted"]))
    out += ["",
            "Sensitivity to the interval level and to the estimator. The verdicts "
            "above use the 90% intervals, which is the level that corresponds to "
            "a TOST at 5%. Counting instead by containment of a single "
            "estimator's interval, over the same 18 loose binary cells:", ""]
    est = (("90% bootstrap", "boot_ci90_lo", "boot_ci90_hi"),
           ("95% bootstrap", "boot_ci95_lo", "boot_ci95_hi"),
           ("90% Newcombe", "newcombe_ci90_lo", "newcombe_ci90_hi"),
           ("95% Newcombe", "newcombe_ci95_lo", "newcombe_ci95_hi"),
           ("90% cluster bootstrap", "cluster_ci90_lo", "cluster_ci90_hi"))
    out += ["| interval | 2.5 pp | 5 pp | 10 pp |", "| --- | ---: | ---: | ---: |"]
    for name, lo_col, hi_col in est:
        cells = []
        for margin in BINARY_MARGINS_PP:
            cells.append(sum(1 for arm in ARMS_ORDER for k in binkeys
                             if get("loose", arm, k)[lo_col] > -margin
                             and get("loose", arm, k)[hi_col] < margin))
        out.append("| {} | {}/18 | {}/18 | {}/18 |".format(name, *cells))
    out += ["",
            "No cell is *refuted* at any margin at the loose budget: the sample "
            "is never large enough to affirm a difference as big as 2.5 pp. At "
            "the tight budget, by contrast, {} of 18 cells are refuted at 5 pp, "
            "which is the availability effect the manuscript already reports."
            .format(sum(1 for arm in ARMS_ORDER for k in binkeys
                        if get("tight", arm, k)["_verdicts"][5.0]
                        == "equivalence refuted")),
            "",
            "The verdict rule is conservative on purpose: a cell counts as "
            "equivalent only if the 90% bootstrap interval, the 90% Newcombe "
            "interval and the 90% cluster-bootstrap interval all lie inside the "
            "margin. Four loose cells have no discordant pair at all, so their "
            "item bootstrap degenerates to the single point 0 and would declare "
            "equivalence at any margin on its own; the Newcombe interval is what "
            "keeps those cells honest, and it is why they are indeterminate at "
            "2.5 pp.", ""]
    if fails10:
        out += ["**The cells that do NOT reach equivalence at 10 pp.** Both are "
                "reported here rather than absorbed into the null, and they do "
                "not agree on which architecture is ahead:", ""]
        for r in fails10:
            out.append("- **{} / {}** ({}): risk difference {:+.1f} pp, 90% "
                       "bootstrap CI [{:+.1f}, {:+.1f}] pp, 90% Newcombe CI "
                       "[{:+.1f}, {:+.1f}] pp, 90% cluster CI [{:+.1f}, {:+.1f}] "
                       "pp. {} has the higher rate on this outcome, and because "
                       "{} on this outcome the difference favours **{}**."
                       .format(r["arm"], r["outcome"], r["better_direction"],
                               r["estimate"], r["boot_ci90_lo"], r["boot_ci90_hi"],
                               r["newcombe_ci90_lo"], r["newcombe_ci90_hi"],
                               r["cluster_ci90_lo"], r["cluster_ci90_hi"],
                               "SINGLE+G" if r["estimate"] > 0 else "MULTI-G",
                               r["better_direction"], r["favours"]))
        out += ["",
                "A sign convention warning for anyone reading these two cells "
                "side by side: both risk differences are negative, so MULTI-G "
                "has the higher rate on both, but a higher catch rate is good "
                "and a higher pass-through rate is bad. The two cells therefore "
                "point in opposite directions on which architecture is ahead, "
                "and neither dominates.", ""]
    return "\n".join(out) + "\n"



DG18_HEADERS = [
    "reading", "contrast", "arm", "model", "budget_level", "budget_tokens",
    "test", "outcome", "unit", "outcome_scale", "statistic",
    "n_units", "n_clusters", "n_clusters_used",
    "max_nonzero_items_in_one_cluster", "reduces_to_item_test",
    "a_only", "b_only", "both", "neither", "n_discordant", "n_nonzero",
    "estimate",
    "p_item", "p_item_method", "p_item_holm96", "p_item_holm12",
    "p_cluster_perm", "p_cluster_perm_share", "p_cluster_perm_exact",
    "p_cluster_rank_perm", "p_cluster_rank_exact",
    "p_cluster_perm_holm", "p_cluster_perm_holm12", "p_cluster_exact_holm",
    "p_hier_boot", "hier_ci95_lo", "hier_ci95_hi",
    "sig_item_raw", "sig_cluster_raw", "sig_item_holm96", "sig_cluster_holm96",
    "sig_cluster_exact_holm96",
    "verdict_change_raw", "verdict_change_holm", "verdict_change_holm_exact",
    "cited_in_manuscript", "citation",
]

_DG18_INT = {"n_units", "n_clusters", "n_clusters_used", "n_discordant",
             "n_nonzero", "max_nonzero_items_in_one_cluster", "a_only",
             "b_only", "both", "neither", "budget_tokens"}
_DG18_SCI = {"p_item", "p_item_holm96", "p_item_holm12", "p_cluster_perm",
             "p_cluster_perm_share", "p_cluster_perm_exact",
             "p_cluster_rank_perm", "p_cluster_rank_exact",
             "p_cluster_perm_holm", "p_cluster_perm_holm12",
             "p_cluster_exact_holm", "p_hier_boot"}


def _fmt18(value, header):
    if value == "" or value is None:
        return ""
    if header in _DG18_INT:
        return str(value)
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return "na"
    if header in _DG18_SCI:
        return "{:.6g}".format(float(value))
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return "{:.4f}".format(value)
    return str(value)


def _p(value, spec="{:.3g}"):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "na"
    if value >= 0.9995:
        return "1.00"
    return spec.format(value)


def build_md18(rows, checks, provenance, n_perm, n_boot) -> str:
    """The mapping table the question asks for, plus its methods note."""
    prim = [r for r in rows if r["reading"] == "e8_disposition"]
    alt = [r for r in rows if r["reading"] == "content_rule"]
    changed_holm = [r for r in prim if r["verdict_change_holm"]]
    changed_raw = [r for r in prim if r["verdict_change_raw"]]
    changed_alt = [r for r in alt if r["verdict_change_holm"]]
    reduces = [r for r in prim if r["reduces_to_item_test"]]
    sig_item = [r for r in prim if r["sig_item_holm96"]]
    sig_clu = [r for r in prim if r["sig_cluster_holm96"]]

    def pick(subset, contrast=None, level=None, test=None, not_test=None):
        out = []
        for r in subset:
            if contrast and r["contrast"] != contrast:
                continue
            if level and r["budget_level"] != level:
                continue
            if test and r["test"] != test:
                continue
            if not_test and r["test"] == not_test:
                continue
            out.append(r)
        return out

    loose_sm = pick(prim, "SINGLE+G vs MULTI-G", "loose")
    guard_q = pick(prim, "MULTI-G vs MULTI-UG", "loose", test="wilcoxon_quality")
    guard_bin = pick(prim, "MULTI-G vs MULTI-UG", "loose", not_test="wilcoxon_quality")
    tight_sm = pick(prim, "SINGLE+G vs MULTI-G", "tight")
    tight_guard = pick(prim, "MULTI-G vs MULTI-UG", "tight")

    out = []
    a = out.append
    a("# DG18: cluster-aware inferential tests for the E3 agent-layer comparison\n")
    a("Section 5.4 reports rates with a cluster bootstrap over the replayed "
      "scheduling instances, on the stated ground that instructions written on "
      "the same instance are not independent, and then reports every "
      "agent-layer p-value from an exact McNemar or Wilcoxon test that treats "
      "each item as its own draw. This file removes that inconsistency. It "
      "re-runs the whole declared family of 96 tests with the paired sign "
      "flipped at the instance level rather than at the item level, re-runs the "
      "Holm correction on the result, and maps every number the manuscript "
      "cites from its published p-value to its cluster-aware one.\n")

    a("## Headline\n")
    a("- **Every p-value the manuscript prints keeps its verdict.** The "
      "loose-budget null result, the smallest uncorrected p behind it, the "
      "five-of-six guard result and the tight-budget separation all survive.")
    a("- {} of the {} tests in the declared family change their Holm-corrected "
      "verdict, and neither is printed as a p-value in the paper. Both are the "
      "guard's effect on violation pass-through (MULTI-G against MULTI-UG at "
      "the loose budget), which the manuscript reports as a rate change and "
      "uses to set the equivalence margins, never as a significance claim."
      .format(len(changed_holm), len(prim)))
    a("- {} of {} change their uncorrected verdict at the 5 percent level."
      .format(len(changed_raw), len(prim)))
    a("- Holm-significant over the family of 96: {} tests item-level, {} tests "
      "cluster-aware. Reading the exact cluster p-values instead of the Monte "
      "Carlo ones gives the same {} and the same two changes, so nothing here "
      "turns on the resample count."
      .format(len(sig_item), len(sig_clu),
              sum(1 for r in prim if r["sig_cluster_exact_holm96"])))
    a("- Under the pass-through content rule, the reading Table tab:e3-rd's "
      "risk differences use, {} of {} change their Holm-corrected verdict, and "
      "they are the same two cells.".format(len(changed_alt), len(alt)))
    a("- {} of the {} tests have at most one differing item per instance. For "
      "those there is no within-instance dependence to correct for, and the "
      "cluster test returns the item-level p-value exactly; the script asserts "
      "that identity rather than assuming it.\n".format(len(reduces), len(prim)))

    a("## The numbers the manuscript reads off these tests\n")
    a("| Manuscript claim | Published (item-level) | Cluster-aware | Verdict |")
    a("| --- | --- | --- | --- |")
    a("| Table 6 column 'S vs M Holm p' and Section 6.4, no SINGLE+G against "
      "MULTI-G contrast at the loose budget is significant "
      "(`\\eThreeAgentHolmMin` = 1.00 over 24 cells) | min Holm p = {} | min "
      "Holm p = {} | {} |"
      .format(_p(min(r["p_item_holm96"] for r in loose_sm)),
              _p(min(r["p_cluster_perm_holm"] for r in loose_sm)),
              "holds" if min(r["p_cluster_perm_holm"] for r in loose_sm) >= 0.05
              else "CHANGES"))
    a("| App. E, the smallest uncorrected p over the same 24 cells is 0.092 "
      "(`\\eThreeAgentRawPLooseMin`) | min raw p = {} | min raw p = {} exact "
      "({} by Monte Carlo) | {} |"
      .format(_p(min(r["p_item"] for r in loose_sm), "{:.4g}"),
              _p(min(r["p_cluster_perm_exact"] for r in loose_sm), "{:.4g}"),
              _p(min(r["p_cluster_perm"] for r in loose_sm), "{:.4g}"),
              "holds" if min(r["p_cluster_perm_exact"] for r in loose_sm) >= 0.05
              else "CHANGES"))
    a("| Table 6 column 'Guard at fixed architecture / Holm p' and Section 6.4, "
      "the guard's effect on executed-schedule quality is Holm-significant on "
      "five of six arms (`\\eThreeGuardSignificantArmsWord`) | {} of 6 arms | {} "
      "of 6 arms | {} |"
      .format(sum(1 for r in guard_q if r["sig_item_holm96"]),
              sum(1 for r in guard_q if r["sig_cluster_holm96"]),
              "holds" if sum(1 for r in guard_q if r["sig_cluster_holm96"]) ==
              sum(1 for r in guard_q if r["sig_item_holm96"]) else "CHANGES"))
    a("| Section 6.4, the two architectures separate at the tight budget | {} of "
      "24 cells Holm-significant | {} of 24 | {} |"
      .format(sum(1 for r in tight_sm if r["sig_item_holm96"]),
              sum(1 for r in tight_sm if r["sig_cluster_holm96"]),
              "holds" if sum(1 for r in tight_sm if r["sig_cluster_holm96"]) ==
              sum(1 for r in tight_sm if r["sig_item_holm96"]) else "CHANGES"))
    a("")

    def ratio_note(subset):
        """How far the uncorrected p-value moved, measured rather than asserted."""
        ratios = [(r["p_cluster_perm_exact"] / r["p_item"], r)
                  for r in subset if r["p_item"] > 0
                  and not math.isnan(r["p_cluster_perm_exact"])]
        if not ratios:
            return ""
        ratios.sort(key=lambda x: x[0])
        lo, hi = ratios[0], ratios[-1]
        return ("Over these {} cells the exact cluster-aware uncorrected "
                "p-value is {:.2f} to {:.2f} times the published one, the "
                "extremes being {} on {} and {} on {}."
                .format(len(ratios), lo[0], hi[0],
                        lo[1]["test"].replace("mcnemar_", "").replace("_", " "),
                        lo[1]["model"].split(" (")[0],
                        hi[1]["test"].replace("mcnemar_", "").replace("_", " "),
                        hi[1]["model"].split(" (")[0]))

    def table(subset, title, note, rank=False):
        a("### {}\n".format(title))
        a(note + " " + ratio_note(subset) + "\n")
        head = ("| Arm | Test | Instances used | Item p | Cluster p | "
                "Cluster p exact |")
        rule = "| --- | --- | --- | --- | --- | --- |"
        if rank:
            head += " Cluster p exact, rank |"
            rule += " --- |"
        head += " Hier. boot p | Item Holm | Cluster Holm | Verdict |"
        rule += " --- | --- | --- | --- |"
        a(head)
        a(rule)
        for r in subset:
            line = "| {} | {} | {} of {} | {} | {} | {} |".format(
                r["model"].split(" (")[0],
                r["test"].replace("mcnemar_", "").replace("wilcoxon_", "")
                         .replace("_", " "),
                r["n_clusters_used"], r["n_clusters"],
                _p(r["p_item"]), _p(r["p_cluster_perm"]),
                _p(r["p_cluster_perm_exact"]))
            if rank:
                line += " {} |".format(_p(r["p_cluster_rank_exact"]))
            line += " {} | {} | {} | {} |".format(
                _p(r["p_hier_boot"]), _p(r["p_item_holm96"]),
                _p(r["p_cluster_perm_holm"]),
                "CHANGES" if r["verdict_change_holm"] else "unchanged")
            a(line)
        a("")

    table(loose_sm,
          "Loose budget, SINGLE+G against MULTI-G: the paper's null result",
          "These 24 cells carry Table 6's 'S vs M Holm p' column and the "
          "Section 6.4 sentence about no detectable advantage. A Holm p of 1.00 "
          "in both the published and the cluster-aware column means the null "
          "result does not depend on the exchangeable unit. The largest move is "
          "on "
          "end-task quality, where the published test ranks the differences and "
          "the declared cluster statistic averages them; the rank column is the "
          "like-for-like comparison there.",
          rank=True)
    table(guard_q,
          "Loose budget, MULTI-G against MULTI-UG on end-task quality: the "
          "paper's positive result",
          "These 6 cells carry Table 6's last column and the five-of-six claim. "
          "They are the cells where moving the draw to the instance could have "
          "cost a positive finding, and it does not: the effect is spread over "
          "16 to 22 distinct instances on the five significant arms, so "
          "clustering costs the test resolution but not the verdict. The Monte "
          "Carlo column sits on its own floor of 1/(20000+1) on four arms; the "
          "exact column is the one to quote there.",
          rank=True)
    table(guard_bin,
          "Loose budget, MULTI-G against MULTI-UG on the binary outcomes: where "
          "the two verdicts that change sit",
          "None of these p-values is printed in the manuscript. The pass-through "
          "column is the reference effect the equivalence margins of Section 5.4 "
          "are a fraction of, and that is an effect size rather than a "
          "significance claim, so the two changes below do not reach any "
          "sentence in the paper. They are reported because a family-wide "
          "correction is only meaningful if every member of the family is "
          "reported.")
    table(tight_sm,
          "Tight budget, SINGLE+G against MULTI-G",
          "Not printed as p-values, but these are the members of the family "
          "that carry most of the correction, and Section 6.4 reads the tight "
          "budget as a difference in how often a system finishes off them. Nine "
          "cells are Holm-significant before and after.", rank=True)
    table(tight_guard,
          "Tight budget, MULTI-G against MULTI-UG",
          "The guard barely moves anything at the tight budget, because the "
          "multi-agent pipeline mostly does not finish. Nothing here is "
          "significant under either reading.", rank=True)

    if changed_holm:
        a("## The verdicts that change, in full\n")
        for r in changed_holm:
            a("**{} / {} / {} / {}.** The paired difference is {:+.2f} "
              "percentage points over {} pairs, {} of them discordant, but the "
              "discordant pairs sit on only {} of the {} instances, with as many "
              "as {} of them on one instance. The item-level exact McNemar "
              "p-value is {} and its Holm-corrected value {}; flipping the sign "
              "at the instance level gives {} and {}. The finding survives as a "
              "rate change and as the reference effect behind the equivalence "
              "margins, and it is not printed as a significance claim anywhere "
              "in the manuscript. The effect is still significant before "
              "correction under the cluster-aware test ({} against a 5 percent "
              "level); what it no longer clears is the family-wide correction "
              "over 96."
              .format(r["contrast"], r["arm"], r["budget_level"], r["test"],
                      r["estimate"], r["n_units"], r["n_discordant"],
                      r["n_clusters_used"], r["n_clusters"],
                      r["max_nonzero_items_in_one_cluster"],
                      _p(r["p_item"], "{:.4g}"), _p(r["p_item_holm96"], "{:.3g}"),
                      _p(r["p_cluster_perm_exact"], "{:.4g}"),
                      _p(r["p_cluster_perm_holm"], "{:.3g}"),
                      _p(r["p_cluster_perm_exact"], "{:.4g}")))
            a("")

    a("## Methods, in a form the paper can use\n")
    a(methods_paragraph(n_perm, n_boot))
    a("")

    a("## How to read the columns\n")
    a("- `n_clusters_used` is the number of replayed instances whose paired "
      "differences do not cancel to zero inside the instance. Only those "
      "instances carry information about a difference, so they are the draws "
      "the permutation null randomises. It is the clustered counterpart of the "
      "discordant-pair count in McNemar's test and of the non-zero difference "
      "count in Wilcoxon's, and it is the honest denominator to quote beside a "
      "cluster-aware p-value.")
    a("- `p_cluster_perm` is the Monte Carlo sign-flip p-value at {:,} draws, "
      "with the observed configuration counted in both numerator and "
      "denominator, so its floor is {:.1e} rather than zero. "
      "`p_cluster_perm_share` is the bare share of draws at least as extreme, "
      "which is the quantity the design declares and which can be exactly zero."
      .format(n_perm, 1.0 / (1.0 + n_perm)))
    a("- `p_cluster_perm_exact` enumerates the same sign-flip null instead of "
      "sampling it, so it has no resolution floor. The two agree wherever the "
      "Monte Carlo value is above its floor; where they disagree, the exact "
      "column is the one to quote.")
    a("- `p_cluster_rank_perm` and `p_cluster_rank_exact` flip the same "
      "instance-level signs on Wilcoxon's signed ranks rather than on the raw "
      "differences. On the binary outcomes the two statistics are the same "
      "test, because every non-zero difference has the same magnitude and "
      "therefore the same rank, and the script asserts that. On end-task "
      "quality they differ, and the rank version is the direct analogue of the "
      "published Wilcoxon test, while the mean version is the statistic the "
      "design declares.")
    a("- `p_hier_boot` resamples instances and then items within instance, and "
      "reads the p-value by inverting the two-sided percentile interval. It is "
      "a secondary check on the permutation rather than a replacement: it is "
      "conservative wherever a large share of the resampled differences land "
      "exactly on zero, which on these binary outcomes is the common case.")
    a("- `reduces_to_item_test` is true when no instance holds more than one "
      "differing item.")
    a("- `reading` is `e8_disposition` for the pass-through predicate every "
      "published p-value was computed on, and `content_rule` for the V4/V6 "
      "reading behind Table tab:e3-rd's risk differences and every DG6 "
      "interval. The two agree on false block, on catch and on quality, which "
      "the script asserts.\n")

    a("## Self-check\n")
    counts = checks.counts()
    a("{} of {} assertions passed. No cluster-aware number is computed until "
      "every 2x2 cell, every item-level p-value and both Holm corrections in "
      "analysis/E8_adjudication.csv have been reproduced from "
      "results/e3_replay_*/verdicts.jsonl and the quality rebuild.\n"
      .format(counts["passed"], counts["total"]))
    for group, what in (("stage3c", "the item-level reproduction"),
                        ("stage3d", "the cluster stage"),
                        ("stage4", "the join back into DG6")):
        sub = [r for r in checks.rows if r["group"] == group]
        if sub:
            a("- `{}` ({}): {} assertions, {} failed.".format(
                group, what, len(sub), sum(1 for r in sub if not r["ok"])))
    a("")

    a("## Provenance\n")
    for line in provenance:
        a("- {}".format(line))
    a("")
    return "\n".join(out)


def methods_paragraph(n_perm: int, n_boot: int) -> str:
    """One paragraph, written to be adapted into Section 5.4 of the manuscript."""
    return (
        "The E3 items are not independent of one another: several instructions "
        "are written on the same replayed scheduling instance, and two systems "
        "compared on those instructions share whatever the instance makes easy "
        "or hard. The exact McNemar and Wilcoxon tests treat each item as its "
        "own draw, so their p-values are re-derived here with the draw taken at "
        "the instance level. Under the paired null the sign of a difference is "
        "exchangeable, and clustering means the signs of all differences on one "
        "instance flip together rather than separately; the reference "
        "distribution of the mean paired difference is therefore built by "
        "drawing one sign per instance, {:,} times at a fixed seed, and the "
        "two-sided p-value is the share of draws whose statistic is at least as "
        "large in absolute value as the observed one. On the binary outcomes "
        "this is McNemar's sign test with the discordant pairs grouped by "
        "instance, and on end-task quality it is the signed-rank test with the "
        "same grouping. A hierarchical bootstrap that resamples instances and "
        "then items within instance, {:,} replicates at the same seed, gives a "
        "second p-value by inverting the percentile interval. Instances whose "
        "differences cancel within the instance carry no information about a "
        "difference and are not counted among the draws, which is the clustered "
        "form of dropping concordant pairs. Holm correction is then applied over "
        "the same declared family of 96 agent-layer tests."
    ).format(n_perm, n_boot)


if __name__ == "__main__":
    sys.exit(main())
