#!/usr/bin/env python3
"""DG10. Cluster-bootstrap 95% intervals on the direct-guard headline rates.

Table 7 of the manuscript reports the guard's refusal share on the canonical
structured proposal of every suite item, with no model in the loop.  Two of
those cells are the abstract's lead numbers:

    V3 quality   201 / 220 refused   91.4%
    benign        21 / 800 refused    2.6%

Neither carries an interval, while every rate measured through a proposer
(DG5, DG6) carries a nonparametric cluster bootstrap over instances.  This
script attaches the same estimator to the direct-guard rates so the two
families of numbers are comparable.

Estimator, copied from code/scripts/e1_intervals.py (l1-dg5-intervals-1),
functions `cluster_bootstrap`, `wilson`, `linearised_se` and `cluster_key`:

    Every rate is a pooled ratio R = (sum numerator) / (sum denominator) over
    rows.  Rows are partitioned into clusters.  One bootstrap replicate draws K
    clusters with replacement from the K observed clusters (each drawn cluster
    contributes ALL of its rows) and recomputes R* over the draw.  The reported
    interval is the 2.5 / 97.5 percentile of B = 20,000 replicates.  This makes
    no independence assumption within a cluster.

The primary cluster is the instance, as in DG5.  Two sensitivity levels are
also reported: the item (in this benchmark each item contributes exactly one
row per class, so the item-clustered interval IS the ordinary row bootstrap and
should track Wilson), and (instance, subclass).

Input is the per-item table `analysis/DG1_direct_guard.csv`, restricted to
`reading == canonical` and `config == G_CERT`, which is the deployed guard
(schema + feasibility + certificate at tau = 0.20).  Nothing is recomputed from
the guard itself; the script reads verdicts already published by
code/scripts/direct_guard_benchmark.py and asserts the counts it derives match
that script's own published summary before computing anything.

Outputs (additive, nothing is overwritten by design):
    analysis/DG10_direct_guard_intervals.csv
    analysis/DG10_direct_guard_intervals.md
    analysis/DG10_benign_concentration.csv
"""

import csv
import datetime as _dt
import hashlib
import math
import os
import sys
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

import numpy as np

VERSION = "l1-dg10-direct-guard-intervals-1"

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS = ROOT / "analysis"
SCRIPTS = ROOT / "code" / "scripts"
SUITE = ROOT / "code" / "suite" / "v0.2" / "suite.jsonl"
DG1 = ANALYSIS / "DG1_direct_guard.csv"
RULE_ANCHOR = ANALYSIS / "ladder" / "rule_anchor.csv"

# Estimator constants, identical to code/scripts/e1_intervals.py.
B = 20_000
SEED = 20260814
ALPHA = 0.05
Z = 1.959963984540054            # two-sided normal quantile at 0.975

TAU = 0.20
READING = "canonical"
CONFIG = "G_CERT"

CLUSTER_LEVELS = ("instance", "item", "instance_family")

# metric key -> (primary_class, denominator rule, label, published cell it must
# reproduce as (numerator, denominator)).  "with_proposal" drops the items whose
# canonical field is empty; "all" keeps every item of the class.
METRICS = OrderedDict([
    ("benign_refusal", (
        "benign", "all",
        "Benign canonical proposal refused (the guard's false-block floor)",
        (21, 800))),
    ("v3_refusal", (
        "V3", "all",
        "V3 quality canonical proposal refused (the certificate's ceiling)",
        (201, 220))),
    ("v4_refusal", (
        "V4", "all",
        "V4 mistranslation canonical proposal refused",
        (46, 220))),
    ("v6_refusal_representable", (
        "V6", "with_proposal",
        "V6 injection canonical proposal refused, over items carrying one",
        (39, 175))),
    ("v6_refusal_all_items", (
        "V6", "all",
        "V6 injection canonical proposal refused, over all items of the class",
        (39, 200))),
    ("v1_refusal_representable", (
        "V1", "with_proposal",
        "V1 schema canonical proposal refused, over items carrying one",
        (130, 130))),
    ("v1_refusal_all_items", (
        "V1", "all",
        "V1 schema canonical proposal refused, over all items of the class",
        (130, 160))),
    ("v2_refusal", (
        "V2", "all",
        "V2 constraint canonical proposal refused",
        (200, 200))),
    ("v5_refusal_all_items", (
        "V5", "all",
        "V5 ambiguity: empty proposal refused (a property of the instance)",
        (7, 200))),
])

HEADLINE = ("v3_refusal", "benign_refusal")


# --------------------------------------------------------------------------- #
# IO                                                                           #
# --------------------------------------------------------------------------- #
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_dg1(path: Path) -> list:
    """The per-item direct-guard rows, comment lines stripped."""
    with open(path, encoding="utf-8") as fh:
        lines = [ln for ln in fh if not ln.startswith("#")]
    return list(csv.DictReader(lines))


def load_rule_anchor(path: Path) -> dict:
    """instance_id -> ATC anchor gap on the unmodified instance."""
    out = {}
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            gap = float(row["gap"])
            prev = out.get(row["instance_id"])
            if prev is not None and abs(prev - gap) > 1e-9:
                raise SystemExit(
                    "rule_anchor.csv disagrees with itself on {}: {} vs {}"
                    .format(row["instance_id"], prev, gap))
            out[row["instance_id"]] = gap
    return out


# --------------------------------------------------------------------------- #
# Metric definitions                                                           #
# --------------------------------------------------------------------------- #
def metric_row(metric: str, row: dict):
    """(denominator contribution, numerator contribution) for one item row."""
    cls, rule, _, _ = METRICS[metric]
    if row["primary_class"] != cls:
        return 0, 0
    if rule == "with_proposal" and row["proposal_empty"] == "True":
        return 0, 0
    return 1, int(row["refused"] == "True")


def cluster_key(level: str, row: dict):
    if level == "instance":
        return row["instance_id"]
    if level == "item":
        return row["item_id"]
    if level == "instance_family":
        return (row["instance_id"], row["subclass"])
    raise KeyError(level)


# --------------------------------------------------------------------------- #
# Interval machinery (verbatim from code/scripts/e1_intervals.py)              #
# --------------------------------------------------------------------------- #
def wilson(k: int, n: int):
    """Wilson score interval, the naive (rows-are-independent) comparator."""
    if n == 0:
        return None, None
    p = k / n
    denom = 1.0 + Z * Z / n
    centre = (p + Z * Z / (2 * n)) / denom
    half = (Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def cluster_bootstrap(num: np.ndarray, den: np.ndarray, seed: int, b: int = B):
    """Percentile interval and SE of a pooled ratio under the cluster bootstrap.

    ``num`` / ``den`` are per-cluster sums.  A replicate draws K cluster indices
    with replacement and forms sum(num)/sum(den) over the draw.
    """
    k = num.shape[0]
    if k == 0:
        return None, None, None, np.empty(0)
    rng = np.random.default_rng(seed)
    out = np.empty(b, dtype=np.float64)
    step = 2000
    filled = 0
    while filled < b:
        take = min(step, b - filled)
        idx = rng.integers(0, k, size=(take, k))
        n_s = num[idx].sum(axis=1)
        d_s = den[idx].sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            r = np.where(d_s > 0, n_s / np.maximum(d_s, 1), np.nan)
        out[filled:filled + take] = r
        filled += take
    good = out[~np.isnan(out)]
    lo, hi = np.percentile(good, [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])
    return float(lo), float(hi), float(good.std(ddof=1)), good


def linearised_se(num: np.ndarray, den: np.ndarray):
    """Textbook cluster-robust SE of a ratio estimator (Taylor linearization).

    Var(R) = K / ((K-1) * D^2) * sum_k (y_k - R * m_k)^2, with D = sum m_k.
    """
    k = num.shape[0]
    d_tot = den.sum()
    if k < 2 or d_tot == 0:
        return None
    r = num.sum() / d_tot
    resid = num - r * den
    var = k / ((k - 1) * d_tot ** 2) * float((resid ** 2).sum())
    return math.sqrt(max(var, 0.0))


def pct(x, digits=1):
    return "" if x is None else "{:.{d}f}".format(100 * x, d=digits)


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> int:
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ.setdefault(var, "4")

    sources = OrderedDict()
    for p in (DG1, SUITE, RULE_ANCHOR,
              SCRIPTS / "direct_guard_benchmark.py",
              SCRIPTS / "e1_intervals.py"):
        sources[str(p.relative_to(ROOT))] = sha256(p)

    all_rows = load_dg1(DG1)
    rows = [r for r in all_rows
            if r["reading"] == READING and r["config"] == CONFIG]
    if not rows:
        raise SystemExit("no {} / {} rows in {}".format(READING, CONFIG, DG1))

    # ---------------------------------------------------------------- self-check
    # Every denominator and numerator below must reproduce the published
    # "Sensitivity: the share of canonical proposals the guard refuses" table of
    # analysis/DG1_direct_guard.md.  A mismatch means the input moved under this
    # script, and reporting a new interval off a moved input is worse than
    # reporting nothing.
    mismatches = []
    for metric, (_, _, _, want) in METRICS.items():
        pairs = [metric_row(metric, r) for r in rows]
        got = (sum(n for _, n in pairs), sum(d for d, _ in pairs))
        if got != want:
            mismatches.append(
                "{}: recomputed {}/{}, DG1_direct_guard.md says {}/{}"
                .format(metric, got[0], got[1], want[0], want[1]))
    if any(r["infra_error"] == "True" for r in rows):
        mismatches.append("some canonical/G_CERT rows carry infra_error=True; "
                          "the direct benchmark should have none")
    if mismatches:
        raise SystemExit("SELF-CHECK FAILED:\n  " + "\n  ".join(mismatches))
    print("self-check OK: {} metrics reproduce DG1_direct_guard.md".format(len(METRICS)))

    # ---------------------------------------------------------------- intervals
    stamp = _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    interval_rows = []
    for metric, (cls, rule, label, _) in METRICS.items():
        pairs = [(metric_row(metric, r), r) for r in rows]
        den_tot = sum(p[0][0] for p in pairs)
        num_tot = sum(p[0][1] for p in pairs)
        point = num_tot / den_tot if den_tot else None
        w_lo, w_hi = wilson(num_tot, den_tot)
        srs_se = (math.sqrt(point * (1 - point) / den_tot)
                  if point is not None and den_tot else None)

        for level in CLUSTER_LEVELS:
            agg = defaultdict(lambda: [0, 0])
            for (d, n), r in pairs:
                if d == 0:
                    continue
                c = agg[cluster_key(level, r)]
                c[0] += d
                c[1] += n
            keys_sorted = sorted(agg)
            den_arr = np.array([agg[k][0] for k in keys_sorted], dtype=np.float64)
            num_arr = np.array([agg[k][1] for k in keys_sorted], dtype=np.float64)
            n_clusters = int(den_arr.shape[0])

            # Deterministic per-cell stream: Python's str hash is salted per
            # process, so a stable digest is used instead (same construction as
            # code/scripts/e1_intervals.py).
            tag = "|".join(("direct", metric, level)).encode("utf-8")
            seed = SEED + int(hashlib.sha256(tag).hexdigest()[:8], 16) % 100_000
            lo, hi, boot_se, reps = cluster_bootstrap(num_arr, den_arr, seed)
            lin_se = linearised_se(num_arr, den_arr)
            frac_zero = (float((reps == 0.0).mean()) if reps.size else None)

            def deff(se):
                if se is None or not srs_se:
                    return None
                return (se / srs_se) ** 2

            if lo is None or w_lo is None or (w_hi - w_lo) <= 0:
                deff_width = None
            else:
                deff_width = ((hi - lo) / (w_hi - w_lo)) ** 2

            interval_rows.append(OrderedDict([
                ("metric", metric),
                ("metric_label", label),
                ("primary_class", cls),
                ("denominator_rule", rule),
                ("reading", READING),
                ("config", CONFIG),
                ("tau", TAU),
                ("numerator", num_tot),
                ("denominator", den_tot),
                ("point", "" if point is None else "{:.6f}".format(point)),
                ("point_pct", pct(point)),
                ("cluster_level", level),
                ("n_clusters", n_clusters),
                ("ci_lo", "" if lo is None else "{:.6f}".format(lo)),
                ("ci_hi", "" if hi is None else "{:.6f}".format(hi)),
                ("ci_lo_pct", pct(lo)),
                ("ci_hi_pct", pct(hi)),
                ("wilson_lo", "" if w_lo is None else "{:.6f}".format(w_lo)),
                ("wilson_hi", "" if w_hi is None else "{:.6f}".format(w_hi)),
                ("wilson_lo_pct", pct(w_lo)),
                ("wilson_hi_pct", pct(w_hi)),
                ("boot_se", "" if boot_se is None else "{:.6f}".format(boot_se)),
                ("lin_se", "" if lin_se is None else "{:.6f}".format(lin_se)),
                ("srs_se", "" if srs_se is None else "{:.6f}".format(srs_se)),
                ("deff_width", "" if deff_width is None else "{:.2f}".format(deff_width)),
                ("deff_lin", "" if deff(lin_se) is None else "{:.2f}".format(deff(lin_se))),
                ("deff_boot", "" if deff(boot_se) is None else "{:.2f}".format(deff(boot_se))),
                ("boot_frac_zero", "" if frac_zero is None else "{:.4f}".format(frac_zero)),
                ("B", B),
                ("seed", seed),
            ]))

    # -------------------------------------------- Monte-Carlo stability at this B
    mc = []
    for metric in HEADLINE:
        agg = defaultdict(lambda: [0, 0])
        for r in rows:
            d, n = metric_row(metric, r)
            if d == 0:
                continue
            c = agg[r["instance_id"]]
            c[0] += d
            c[1] += n
        ks = sorted(agg)
        den_a = np.array([agg[k][0] for k in ks], dtype=np.float64)
        num_a = np.array([agg[k][1] for k in ks], dtype=np.float64)
        los, his = [], []
        for s in range(8):
            lo, hi, _, _ = cluster_bootstrap(num_a, den_a, SEED + 7_000 + s)
            los.append(lo)
            his.append(hi)
        mc.append((metric, min(los), max(los), min(his), max(his)))

    # ------------------------------------------------------- benign concentration
    anchor = load_rule_anchor(RULE_ANCHOR)
    benign = [r for r in rows if r["primary_class"] == "benign"]
    blocked = [r for r in benign if r["refused"] == "True"]
    by_inst_all = Counter(r["instance_id"] for r in benign)
    by_inst_blk = Counter(r["instance_id"] for r in blocked)
    conc_rows = []
    for inst in sorted(by_inst_all):
        gap = anchor.get(inst)
        k = by_inst_blk.get(inst, 0)
        conc_rows.append(OrderedDict([
            ("instance_id", inst),
            ("benign_items", by_inst_all[inst]),
            ("benign_refused", k),
            ("refusal_share", "{:.4f}".format(k / by_inst_all[inst])),
            ("rule_anchor_gap", "" if gap is None else "{:.6f}".format(gap)),
            ("anchor_above_tau", "" if gap is None else int(gap > TAU)),
            ("refused_items", "|".join(sorted(r["item_id"] for r in blocked
                                              if r["instance_id"] == inst))),
            ("accepted_items", "|".join(sorted(r["item_id"] for r in benign
                                               if r["instance_id"] == inst
                                               and r["refused"] != "True"))
             if k else ""),
        ]))

    # ------------------------------------------------------------------- write
    def write_csv(path: Path, data, extra_header):
        if path.exists():
            raise SystemExit(
                "refusing to overwrite {} (this script is additive-only)".format(path))
        head = ["# generated {} by analysis/DG10_direct_guard_intervals.py ({})"
                .format(stamp, VERSION)]
        head += extra_header
        for p, digest in sources.items():
            head.append("# {} sha256 {}".format(p, digest))
        with open(path, "w", newline="", encoding="utf-8") as fh:
            for ln in head:
                fh.write(ln + "\n")
            w = csv.DictWriter(fh, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)
        print("wrote {} ({} rows)".format(path, len(data)))

    write_csv(ANALYSIS / "DG10_direct_guard_intervals.csv", interval_rows, [
        "# DG10: cluster-bootstrap 95% intervals on the direct-guard headline "
        "rates (Table 7), no model in the loop.",
        "# scope: analysis/DG1_direct_guard.csv, reading=canonical, "
        "config=G_CERT (schema + feasibility + certificate at tau={}).".format(TAU),
        "# estimator: nonparametric cluster bootstrap of a pooled ratio; "
        "clusters resampled with replacement, each contributing all its rows; "
        "B={} replicates, base seed={}, 2.5/97.5 percentile.".format(B, SEED),
        "# estimator code copied from code/scripts/e1_intervals.py "
        "(cluster_bootstrap, wilson, linearised_se, cluster_key).",
        "# wilson_*: Wilson score interval on the ROW count (the naive interval "
        "that assumes rows are independent).",
        "# deff_width = (cluster CI width / Wilson CI width)^2; "
        "deff_lin = (linearised cluster-robust SE / sqrt(p(1-p)/n))^2; "
        "deff_boot = (bootstrap SE / sqrt(p(1-p)/n))^2.",
        "# cluster_level=item is one row per cluster here, so it IS the ordinary "
        "row bootstrap and is printed as a control on the instance level.",
    ])
    write_csv(ANALYSIS / "DG10_benign_concentration.csv", conc_rows, [
        "# DG10 companion: the 800 canonical benign proposals by instance, with "
        "the no-AI ATC anchor gap of analysis/ladder/rule_anchor.csv.",
        "# anchor_above_tau=1 marks an instance whose unmodified schedule "
        "already certifies above tau={}.".format(TAU),
    ])

    md_path = ANALYSIS / "DG10_direct_guard_intervals.md"
    if md_path.exists():
        raise SystemExit(
            "refusing to overwrite {} (this script is additive-only)".format(md_path))
    md_path.write_text(build_markdown(interval_rows, conc_rows, mc, sources,
                                      stamp, anchor), encoding="utf-8")
    print("wrote {}".format(md_path))
    return 0


def build_markdown(interval_rows, conc_rows, mc, sources, stamp, anchor) -> str:
    idx = {(r["metric"], r["cluster_level"]): r for r in interval_rows}
    out = [
        "# DG10. Cluster-bootstrap intervals on the direct-guard rates",
        "",
        "<!-- generated {} by analysis/DG10_direct_guard_intervals.py ({}) -->"
        .format(stamp, VERSION),
    ]
    for p, digest in sources.items():
        out.append("<!-- {} sha256 {} -->".format(p, digest))
    out += [
        "",
        "Table 7 measures the guard alone: the canonical structured proposal of "
        "every suite item is fed straight to the deployed guard (schema, "
        "feasibility, certificate at tau = {}), with no model in the loop. Those "
        "cells are printed as bare shares. Every rate the manuscript measures "
        "through a proposer carries a nonparametric cluster bootstrap over "
        "instances (DG5, DG6), so the same estimator is attached here.".format(TAU),
        "",
        "**Estimator.** A rate is a pooled ratio over rows. Rows are partitioned "
        "into clusters; a replicate draws K clusters with replacement from the K "
        "observed clusters, each drawn cluster contributing all of its rows, and "
        "recomputes the ratio. The interval is the 2.5 / 97.5 percentile of "
        "B = {:,} replicates at a fixed seed. The code is copied from "
        "`code/scripts/e1_intervals.py`; only the input table changes.".format(B),
        "",
        "**Self-check.** Every numerator and denominator below reproduces the "
        "published sensitivity table of `analysis/DG1_direct_guard.md` exactly; "
        "the script aborts otherwise.",
        "",
        "## 1. The headline rates, clustered on the instance",
        "",
        "| rate | k/n | point | 95% CI (instance-clustered) | 95% CI (Wilson, rows independent) | clusters | design effect |",
        "|---|---|---|---|---|---|---|",
    ]
    for metric in METRICS:
        r = idx[(metric, "instance")]
        out.append("| {} | {}/{} | {}% | {}% to {}% | {}% to {}% | {} | {} |".format(
            METRICS[metric][2], r["numerator"], r["denominator"], r["point_pct"],
            r["ci_lo_pct"], r["ci_hi_pct"], r["wilson_lo_pct"], r["wilson_hi_pct"],
            r["n_clusters"], r["deff_width"]))
    out += [
        "",
        "The design effect is (clustered width / Wilson width)^2. Above 1 means "
        "the instances disagree with each other more than independent rows would, "
        "so the naive interval is too narrow.",
        "",
        "## 2. Sensitivity to the cluster definition",
        "",
        "One row per item per class in this benchmark, so clustering on the item "
        "is the ordinary row bootstrap and is printed as a control.",
        "",
        "| rate | instance | item (= row bootstrap) | (instance, subclass) |",
        "|---|---|---|---|",
    ]
    for metric in METRICS:
        cells = []
        for level in CLUSTER_LEVELS:
            r = idx[(metric, level)]
            cells.append("{}% to {}% (K={})".format(
                r["ci_lo_pct"], r["ci_hi_pct"], r["n_clusters"]))
        out.append("| {} | {} |".format(METRICS[metric][2], " | ".join(cells)))
    out += [
        "",
        "## 3. Monte-Carlo stability at B = {:,}".format(B),
        "",
        "Eight further seeds on the two headline rates, instance-clustered.",
        "",
        "| rate | lower endpoint across 8 seeds | upper endpoint across 8 seeds |",
        "|---|---|---|",
    ]
    for metric, lo_min, lo_max, hi_min, hi_max in mc:
        out.append("| {} | {}% to {}% | {}% to {}% |".format(
            METRICS[metric][2], pct(lo_min, 2), pct(lo_max, 2),
            pct(hi_min, 2), pct(hi_max, 2)))

    blk = [r for r in conc_rows if int(r["benign_refused"]) > 0]
    total_blk = sum(int(r["benign_refused"]) for r in conc_rows)
    hot = [r for r in conc_rows if r["anchor_above_tau"] == 1]
    out += [
        "",
        "## 4. How concentrated are the benign refusals",
        "",
        "The {} benign false blocks sit on {} of the {} instances that carry a "
        "benign item.".format(total_blk, len(blk), len(conc_rows)),
        "",
        "| instance | benign items | refused | share | ATC anchor gap | anchor above tau |",
        "|---|---|---|---|---|---|",
    ]
    for r in blk:
        out.append("| {} | {} | {} | {:.1f}% | {} | {} |".format(
            r["instance_id"], r["benign_items"], r["benign_refused"],
            100 * float(r["refusal_share"]), r["rule_anchor_gap"],
            "yes" if r["anchor_above_tau"] == 1 else "no"))
    out += [
        "",
        "Instances whose no-AI ATC anchor certifies above tau = {} "
        "(`analysis/ladder/rule_anchor.csv`): {}.".format(
            TAU, ", ".join("{} (gap {:.4f})".format(r["instance_id"],
                                                    float(r["rule_anchor_gap"]))
                           for r in hot) or "none"),
        "",
        "This is the same mechanism DG2 section 5 assigns to 53.14% of the "
        "pipeline's benign false blocks: on an instance whose unmodified "
        "schedule already certifies above the tolerance, the certificate has no "
        "room for any proposal that leaves the objective where it found it.",
        "",
    ]
    return "\n".join(out)


if __name__ == "__main__":
    sys.exit(main())
