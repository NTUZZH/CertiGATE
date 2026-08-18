#!/usr/bin/env python
"""Cluster-bootstrap confidence intervals on the E1 headline rates (DG5).

Why this exists
---------------
The E1 tables report pooled rates with no uncertainty attached.  Instructions in
the suite are not independent draws: 2,000 instructions are replayed on 60
frozen instances, and every instruction is re-run over 1 to 3 repeats.  A rate
computed over rows therefore has an effective sample size far below its row
count, and a Wilson interval on the row count understates the uncertainty.  This
script attaches a nonparametric cluster bootstrap to every E1 headline rate.

Estimator
---------
For a rate written as a pooled ratio R = (sum of numerator over rows) / (sum of
denominator over rows), rows are partitioned into clusters.  One bootstrap
replicate draws K clusters with replacement from the K observed clusters (each
drawn cluster contributes ALL of its rows) and recomputes
R* = (sum numerator over drawn clusters) / (sum denominator over drawn clusters).
The reported interval is the 2.5 / 97.5 percentile of B = 20,000 replicates.
This is the standard nonparametric cluster (block) bootstrap of a ratio
estimator; it makes no independence assumption within a cluster.

Cluster levels
--------------
``instance``          primary.  Cluster = ``instance_id`` (60 frozen instances).
                      The instance is the unit that is genuinely resampled if
                      the study were repeated on a new portfolio of projects.
``item``              sensitivity.  Cluster = ``item_id``, so the repeats of one
                      instruction move together but instructions are treated as
                      independent.  This isolates repeat correlation from
                      instance correlation.
``instance_family``   sensitivity.  Cluster = (``instance_id``, ``subclass``).
                      ``subclass`` is the generating template family.  Template
                      family ALONE is not offered as a primary level: V3 has only
                      five families, and a five-cluster bootstrap has no
                      resolution.

Metrics (definitions taken verbatim from code/scripts/e1_evaluate.py)
--------------------------------------------------------------------
``v3_separation``          over V3 rows eligible under both G_FEAS and G_CERT:
                           G_FEAS terminal in APPLIED_STATES and G_CERT terminal
                           in BLOCKED_STATES.  (Analysis.separation)
``benign_false_block_gcert`` over benign rows eligible under G_CERT: G_CERT
                           terminal in BLOCKED_STATES.  (Analysis.blocks)
``benign_false_block_gfeas`` same, under G_FEAS.
``violation_pass_through_gcert`` over non-benign rows eligible under G_CERT:
                           G_CERT terminal in APPLIED_STATES.  (The E3 convention
                           of e3_replay.py: a refusal is neither passed nor
                           blocked, so it sits in the denominator only.)
``violation_pass_through_gfeas`` same, under G_FEAS.
``violation_pass_through_gcert_strict`` / ``..._gfeas_strict`` the same two
                           rates under the V4/V6 content rule
                           (code/scripts/passthrough_rule.py): an applied V4 or
                           V6 row counts unless the applied operations are
                           exactly the item's non-empty ``gold_ops``.  Added
                           beside the legacy metrics, which keep their
                           definition.

A row is *eligible* under a configuration when it carries no ``infra_error``
finding under it (e1_evaluate.Analysis.eligible).  Measured on these logs the
filter removes nothing: zero rows carry an infra finding under any configuration.

Scope
-----
Constrained mode only (``mode == "M_constrained"``), repeats pooled, matching
analysis/T3_guard_value_curve.csv.  Cells are (arm, thinking).  The eight-cell
"capability set" the manuscript ranges over is
{qwen3-14b/-, qwen3.6-27b-fp8/-, glm-4-9b/-, openai/-, sonnet/disabled,
opus/default, opus/disabled, sol/none}; the two DeepSeek cells are reported but
flagged out of the set, as macros.tex does.

Self-check
----------
Before anything is written, the script re-derives two published quantities from
the raw verdict logs and aborts if either differs:
  * opus / default V3 separation  == 398/440 (\eOneVThreeSepOpus = 90.5%)
  * opus / default benign false block under G_CERT == 63/1600
    (\eOneFalseBlockOpus = 3.9%)
It then checks every (cell, metric) point estimate against
analysis/T3_guard_value_curve.csv and aborts on any mismatch beyond 5e-7.

Usage::

    OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 taskset -c 0-3 \
        python code/scripts/e1_intervals.py

Read-only on results/, manuscript/ and code/suite/.  Writes
analysis/DG5_e1_intervals.csv, analysis/DG5_falseblock_concentration.csv and
analysis/DG5_e1_intervals.md.

Version: l1-dg5-intervals-1.
"""

from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import json
import math
import os
import sys
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import passthrough_rule as pr  # noqa: E402  (the V4/V6 content rule, one source)

VERSION = "l1-dg5-intervals-1"

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS = ROOT / "results"
ANALYSIS = ROOT / "analysis"
SUITE = ROOT / "code" / "suite" / "v0.2" / "suite.jsonl"

B = 20_000
SEED = 20260814
ALPHA = 0.05
Z = 1.959963984540054            # two-sided normal quantile at 0.975

# Terminal vocabulary, copied from code/scripts/suite_gate.py (asserted equal to
# e1_evaluate's own import at line 1243-1244 of that file).
APPLIED_STATES = ("applied_with_certificate", "applied_uncertified")
BLOCKED_STATES = ("blocked_schema", "blocked_feas", "blocked_qual")

CONFIGS = ("G_CERT", "G_FEAS")
MODE = "M_constrained"

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

# The manuscript's capability set, verbatim from manuscript/macros.tex
# ("minimum over the capability set {...}").
CAPABILITY_SET = {
    ("qwen3-14b", "-"), ("qwen3.6-27b-fp8", "-"), ("glm-4-9b", "-"),
    ("openai", "-"), ("sonnet", "disabled"), ("opus", "default"),
    ("opus", "disabled"), ("sol", "none"),
}

# metric key -> (label, T3 column it must reproduce or None)
METRICS = OrderedDict([
    ("v3_separation", ("V3 separation (G_FEAS applies, G_CERT blocks)",
                       "v3_separation_share")),
    ("v3_block_gcert", ("V3 block rate under G_CERT", "v3_gcert_block_rate")),
    ("v3_block_gfeas", ("V3 block rate under G_FEAS", None)),
    ("benign_false_block_gcert", ("Benign false block under G_CERT",
                                  "benign_false_block_gcert")),
    ("benign_false_block_gfeas", ("Benign false block under G_FEAS",
                                  "benign_false_block_gfeas")),
    ("v4_block_gcert", ("V4 block rate under G_CERT", "v4_block_rate")),
    ("v5_block_gcert", ("V5 block rate under G_CERT", "v5_block_rate")),
    ("v6_block_gcert", ("V6 block rate under G_CERT", "v6_block_rate")),
    ("violation_pass_through_gcert", ("Violation pass-through under G_CERT", None)),
    ("violation_pass_through_gfeas", ("Violation pass-through under G_FEAS", None)),
    ("violation_pass_through_gcert_strict",
     ("Violation pass-through under G_CERT, V4/V6 content rule", None)),
    ("violation_pass_through_gfeas_strict",
     ("Violation pass-through under G_FEAS, V4/V6 content rule", None)),
])

# The ranges manuscript/macros.tex prints over the capability set, as
# (min macro, max macro, metric).  Reported endpoint-by-endpoint with the
# clustered interval on each endpoint.
PRINTED_RANGES = [
    ("\\eOneVThreeSepMin", "\\eOneVThreeSepMax", "v3_separation"),
    ("\\eOneVThreeFeasBlockMin", "\\eOneVThreeFeasBlockMax", "v3_block_gfeas"),
    ("\\eOneFalseBlockMin", "\\eOneFalseBlockMax", "benign_false_block_gcert"),
    ("\\eOneFalseBlockFeasMin", "\\eOneFalseBlockFeasMax", "benign_false_block_gfeas"),
    ("\\eOneVFourBlockMin", "\\eOneVFourBlockMax", "v4_block_gcert"),
    ("\\eOneVFiveBlockMin", "\\eOneVFiveBlockMax", "v5_block_gcert"),
    ("\\eOneVSixBlockMin", "\\eOneVSixBlockMax", "v6_block_gcert"),
]

CLUSTER_LEVELS = ("instance", "item", "instance_family")


# --------------------------------------------------------------------------- #
# IO                                                                           #
# --------------------------------------------------------------------------- #
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def thinking_label(value) -> str:
    return "-" if value is None else str(value)


def load_proposal_ops(dirname: str) -> dict:
    """(mode, thinking, repeat, item_id) -> the strict-parsed operation list.

    The verdict logs carry ``n_ops`` but not the operations themselves, and the
    V4/V6 content rule needs the content.  One proposal serves both guard
    configurations, which is why the join is on the proposal key.
    """
    out = {}
    with open(RESULTS / dirname / "proposals.jsonl", "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            ex = r.get("extra") or {}
            key = (r["mode"], thinking_label(ex.get("thinking")),
                   ex.get("repeat"), r["instruction_id"])
            out[key] = r.get("parsed_ops")
    return out


def load_arm(arm: str, dirname: str, suite_ops: dict) -> list:
    """One list of merged rows for an arm: G_CERT and G_FEAS joined on the key.

    The join key is (mode, thinking, repeat, item_id), which is the dedup key the
    accepted tables use ("last row per (mode, thinking, repeat, item_id)").  The
    verdict logs are already deduplicated to that key; a duplicate here is a hard
    error rather than a silent overwrite.
    """
    per_config = {}
    for config in CONFIGS:
        path = RESULTS / dirname / "verdicts_{}.jsonl".format(config)
        table = {}
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if r["mode"] != MODE:
                    continue
                key = (r["mode"], thinking_label(r["thinking"]), r["repeat"], r["item_id"])
                if key in table:
                    raise SystemExit(
                        "REFUSING TO RUN: duplicate key {} in {}; the verdict log "
                        "was expected to be deduplicated already.".format(key, path))
                table[key] = r
        per_config[config] = table

    keys = set(per_config["G_CERT"])
    if keys != set(per_config["G_FEAS"]):
        raise SystemExit(
            "REFUSING TO RUN: {} G_CERT and G_FEAS cover different keys".format(arm))

    ops_by_key = load_proposal_ops(dirname)
    if keys - set(ops_by_key):
        raise SystemExit(
            "REFUSING TO RUN: {} proposals.jsonl misses {} of the {} verdict "
            "keys; a silent miss would score every V4 and V6 row as "
            "unrecoverable and reproduce the legacy rate.".format(
                arm, len(keys - set(ops_by_key)), len(keys)))

    rows = []
    for key in sorted(keys):
        c = per_config["G_CERT"][key]
        f = per_config["G_FEAS"][key]
        for field in ("instance_id", "primary_class", "subclass", "item_id"):
            if c[field] != f[field]:
                raise SystemExit(
                    "REFUSING TO RUN: {} disagrees on {} for {}".format(arm, field, key))
        rows.append({
            "arm": c["arm"],
            "thinking": thinking_label(c["thinking"]),
            "repeat": c["repeat"],
            "item_id": c["item_id"],
            "instance_id": c["instance_id"],
            "primary_class": c["primary_class"],
            "subclass": c["subclass"],
            "twin_id": c["twin_id"],
            "cert_terminal": c["terminal"],
            "feas_terminal": f["terminal"],
            "cert_infra": bool(c["infra"]),
            "feas_infra": bool(f["infra"]),
        })
        # The V4/V6 content rule, evaluated once per row per configuration so
        # the metric functions stay pure counters.
        lists = suite_ops.get(c["item_id"], {})
        ops = ops_by_key.get(key)
        for prefix, terminal, n_ops in (
                ("cert", c["terminal"], c.get("n_ops")),
                ("feas", f["terminal"], f.get("n_ops"))):
            rows[-1][prefix + "_pass_strict"] = pr.counts_as_pass_through(
                c["primary_class"], terminal in APPLIED_STATES,
                pr.applied_ops(ops, n_ops), lists.get("gold_ops"),
                lists.get("trap_ops"), lists.get("forbidden_ops"))
    return rows


# --------------------------------------------------------------------------- #
# Metric definitions: each returns (in_denominator, in_numerator) for one row    #
# --------------------------------------------------------------------------- #
def metric_row(metric: str, row: dict):
    cls = row["primary_class"]
    if metric == "v3_separation":
        if cls != "V3" or row["cert_infra"] or row["feas_infra"]:
            return 0, 0
        num = (row["feas_terminal"] in APPLIED_STATES
               and row["cert_terminal"] in BLOCKED_STATES)
        return 1, int(num)
    if metric in ("v3_block_gcert", "v4_block_gcert", "v5_block_gcert",
                  "v6_block_gcert"):
        want = metric.split("_")[0].upper()
        if cls != want or row["cert_infra"]:
            return 0, 0
        return 1, int(row["cert_terminal"] in BLOCKED_STATES)
    if metric == "v3_block_gfeas":
        if cls != "V3" or row["feas_infra"]:
            return 0, 0
        return 1, int(row["feas_terminal"] in BLOCKED_STATES)
    if metric == "benign_false_block_gcert":
        if cls != "benign" or row["cert_infra"]:
            return 0, 0
        return 1, int(row["cert_terminal"] in BLOCKED_STATES)
    if metric == "benign_false_block_gfeas":
        if cls != "benign" or row["feas_infra"]:
            return 0, 0
        return 1, int(row["feas_terminal"] in BLOCKED_STATES)
    if metric == "violation_pass_through_gcert":
        if cls == "benign" or row["cert_infra"]:
            return 0, 0
        return 1, int(row["cert_terminal"] in APPLIED_STATES)
    if metric == "violation_pass_through_gfeas":
        if cls == "benign" or row["feas_infra"]:
            return 0, 0
        return 1, int(row["feas_terminal"] in APPLIED_STATES)
    if metric == "violation_pass_through_gcert_strict":
        if cls == "benign" or row["cert_infra"]:
            return 0, 0
        return 1, int(row["cert_pass_strict"])
    if metric == "violation_pass_through_gfeas_strict":
        if cls == "benign" or row["feas_infra"]:
            return 0, 0
        return 1, int(row["feas_pass_strict"])
    raise KeyError(metric)


def cluster_key(level: str, row: dict):
    if level == "instance":
        return row["instance_id"]
    if level == "item":
        return row["item_id"]
    if level == "instance_family":
        return (row["instance_id"], row["subclass"])
    raise KeyError(level)


# --------------------------------------------------------------------------- #
# Interval machinery                                                           #
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
    suite_ops = pr.load_suite_ops(SUITE)
    cells = OrderedDict()          # (arm, thinking) -> [row]
    for arm, dirname in ARM_DIRS.items():
        for config in CONFIGS:
            p = RESULTS / dirname / "verdicts_{}.jsonl".format(config)
            sources[str(p.relative_to(ROOT))] = sha256(p)
        p = RESULTS / dirname / "proposals.jsonl"
        sources[str(p.relative_to(ROOT))] = sha256(p)
        for row in load_arm(arm, dirname, suite_ops):
            cells.setdefault((row["arm"], row["thinking"]), []).append(row)
    sources[str(SUITE.relative_to(ROOT))] = sha256(SUITE)
    t3_path = ANALYSIS / "T3_guard_value_curve.csv"
    sources[str(t3_path.relative_to(ROOT))] = sha256(t3_path)

    # ---------------------------------------------------------------- self-check
    checks = []
    flagship = cells[("opus", "default")]
    den = sum(metric_row("v3_separation", r)[0] for r in flagship)
    num = sum(metric_row("v3_separation", r)[1] for r in flagship)
    checks.append(("opus/default V3 separation", num, den, 398, 440))
    den2 = sum(metric_row("benign_false_block_gcert", r)[0] for r in flagship)
    num2 = sum(metric_row("benign_false_block_gcert", r)[1] for r in flagship)
    checks.append(("opus/default benign false block under G_CERT", num2, den2, 63, 1600))
    for label, got_n, got_d, want_n, want_d in checks:
        if (got_n, got_d) != (want_n, want_d):
            raise SystemExit(
                "SELF-CHECK FAILED: {} recomputed as {}/{}, macros.tex says {}/{}. "
                "Stopping rather than reporting a new number off a broken "
                "pipeline.".format(label, got_n, got_d, want_n, want_d))
    print("self-check OK: {}".format("; ".join(
        "{} = {}/{}".format(c[0], c[1], c[2]) for c in checks)))

    # T3 cross-check on every cell and the three metrics T3 carries.
    t3 = {}
    with open(t3_path, "r", encoding="utf-8") as fh:
        lines = [ln for ln in fh if not ln.startswith("#")]
    for rec in csv.DictReader(lines):
        if rec["mode"] != MODE:
            continue
        t3[(rec["arm"], rec["thinking"])] = rec

    mismatches = []
    for key, rows in cells.items():
        rec = t3.get(key)
        if rec is None:
            mismatches.append("{} has no T3 row".format(key))
            continue
        for metric, (_, col) in METRICS.items():
            if col is None:
                continue
            d = sum(metric_row(metric, r)[0] for r in rows)
            n = sum(metric_row(metric, r)[1] for r in rows)
            want = float(rec[col])
            got = n / d if d else float("nan")
            if abs(got - want) > 5e-7:
                mismatches.append("{} {}: recomputed {:.6f}, T3 {:.6f}".format(
                    key, metric, got, want))
    # T1 carries the one metric T3 does not: the G_FEAS block rate on V3.
    t1_path = ANALYSIS / "T1_e1_main.csv"
    sources[str(t1_path.relative_to(ROOT))] = sha256(t1_path)
    with open(t1_path, "r", encoding="utf-8") as fh:
        t1_lines = [ln for ln in fh if not ln.startswith("#")]
    t1 = {}
    for rec in csv.DictReader(t1_lines):
        if rec["mode"] != MODE or rec["repeat"] != "pooled" or rec["class"] != "V3":
            continue
        t1[(rec["arm"], rec["thinking"])] = float(rec["gfeas_block_rate"])
    for key, rows in cells.items():
        want = t1.get(key)
        if want is None:
            mismatches.append("{} has no pooled V3 row in T1".format(key))
            continue
        d = sum(metric_row("v3_block_gfeas", r)[0] for r in rows)
        n = sum(metric_row("v3_block_gfeas", r)[1] for r in rows)
        got = n / d if d else float("nan")
        if abs(got - want) > 5e-7:
            mismatches.append("{} v3_block_gfeas: recomputed {:.6f}, T1 {:.6f}".format(
                key, got, want))
    if mismatches:
        raise SystemExit("CROSS-CHECK FAILED:\n  " + "\n  ".join(mismatches))
    n_published = sum(1 for _, (_, col) in METRICS.items() if col) + 1
    print("cross-check OK: {} cells x {} published metrics (T3 + T1)".format(
        len(cells), n_published))

    # ---------------------------------------------------------------- intervals
    stamp = _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    header = [
        "# generated {} by code/scripts/e1_intervals.py ({})".format(stamp, VERSION),
        "# DG5: cluster-bootstrap 95% intervals on the E1 headline rates.",
        "# scope: mode M_constrained, repeats pooled, cells are (arm, thinking).",
        "# estimator: nonparametric cluster bootstrap of a pooled ratio; clusters "
        "resampled with replacement, each contributing all its rows; "
        "B={} replicates, seed={}, 2.5/97.5 percentile.".format(B, SEED),
        "# wilson_*: Wilson score interval on the ROW count (the naive interval "
        "that assumes rows are independent).",
        "# deff_width = (cluster CI width / Wilson CI width)^2; "
        "deff_lin = (linearised cluster-robust SE / sqrt(p(1-p)/n))^2; "
        "deff_boot = (bootstrap SE / sqrt(p(1-p)/n))^2.",
        "# metric definitions taken from code/scripts/e1_evaluate.py "
        "(Analysis.separation, Analysis.blocks) and code/scripts/e3_replay.py "
        "(violation pass-through).  Zero rows carry an infra_error finding, so "
        "the eligibility filter removes nothing on these logs.",
        "# capability_set follows manuscript/macros.tex: the DeepSeek cells are "
        "outside it and are reported for completeness only.",
    ]
    for path, digest in sources.items():
        header.append("# {} sha256 {}".format(path, digest))

    interval_rows = []
    concentration_rows = []
    cache = {}   # (arm, thinking, metric) -> (point, num, den)

    # Pre-pass: every point estimate, so the capability-set argmin / argmax that
    # define each printed range can be marked on the interval rows themselves.
    for key, rows in cells.items():
        for metric in METRICS:
            d = sum(metric_row(metric, r)[0] for r in rows)
            n = sum(metric_row(metric, r)[1] for r in rows)
            cache[(key[0], key[1], metric)] = (n / d if d else None, n, d)
    endpoints = {}   # metric -> {"min": cell, "max": cell}
    for metric in METRICS:
        # sorted() so a tie breaks the same way on every run: a Python set of
        # tuples iterates in salted-hash order, which is not reproducible.
        vals = OrderedDict((k, cache[(k[0], k[1], metric)][0])
                           for k in sorted(CAPABILITY_SET)
                           if cache[(k[0], k[1], metric)][0] is not None)
        if vals:
            endpoints[metric] = {"min": min(vals, key=vals.get),
                                 "max": max(vals, key=vals.get)}

    for key in sorted(cells, key=lambda k: (list(ARM_DIRS).index(k[0]), k[1])):
        arm, thinking = key
        rows = cells[key]
        repeats = sorted({r["repeat"] for r in rows})
        in_set = key in CAPABILITY_SET

        for metric, (label, _) in METRICS.items():
            pairs = [(metric_row(metric, r), r) for r in rows]
            den_tot = sum(p[0][0] for p in pairs)
            num_tot = sum(p[0][1] for p in pairs)
            point = num_tot / den_tot if den_tot else None
            cache[(arm, thinking, metric)] = (point, num_tot, den_tot)

            # per-repeat point estimates (uneven pooling made visible)
            per_rep = []
            for rep in repeats:
                d = sum(mr[0] for mr, r in pairs if r["repeat"] == rep)
                n = sum(mr[1] for mr, r in pairs if r["repeat"] == rep)
                per_rep.append(n / d if d else None)
            per_rep_clean = [v for v in per_rep if v is not None]
            rep_min = min(per_rep_clean) if per_rep_clean else None
            rep_max = max(per_rep_clean) if per_rep_clean else None

            w_lo, w_hi = wilson(num_tot, den_tot)
            srs_se = (math.sqrt(point * (1 - point) / den_tot)
                      if point is not None and den_tot else None)

            for level in CLUSTER_LEVELS:
                agg = defaultdict(lambda: [0, 0])
                for (d, n), r in pairs:
                    c = agg[cluster_key(level, r)]
                    c[0] += d
                    c[1] += n
                keys_sorted = sorted(agg)
                den_arr = np.array([agg[k][0] for k in keys_sorted], dtype=np.float64)
                num_arr = np.array([agg[k][1] for k in keys_sorted], dtype=np.float64)
                # Clusters contributing no rows to this metric's denominator carry
                # no information about the ratio; keeping them only adds zero-zero
                # draws.  They are dropped and the count is recorded.
                keep = den_arr > 0
                n_clusters_all = int(den_arr.shape[0])
                den_arr, num_arr = den_arr[keep], num_arr[keep]
                n_clusters = int(den_arr.shape[0])

                # Deterministic per-cell stream: Python's str hash is salted per
                # process, so a stable digest is used instead.
                tag = "|".join((arm, thinking, metric, level)).encode("utf-8")
                seed = SEED + int(hashlib.sha256(tag).hexdigest()[:8], 16) % 100_000
                lo, hi, boot_se, reps = cluster_bootstrap(num_arr, den_arr, seed)
                lin_se = linearised_se(num_arr, den_arr)
                frac_zero = (float((reps == 0.0).mean()) if reps.size else None)

                def deff(se):
                    if se is None or not srs_se:
                        return None
                    return (se / srs_se) ** 2

                if lo is None or w_lo is None:
                    deff_width = None
                else:
                    ww = w_hi - w_lo
                    deff_width = ((hi - lo) / ww) ** 2 if ww > 0 else None

                interval_rows.append(OrderedDict([
                    ("arm", arm),
                    ("thinking", thinking),
                    ("model", MODEL_LABEL[arm]),
                    ("capability_set", int(in_set)),
                    ("metric", metric),
                    ("metric_label", label),
                    ("range_role", ("min" if endpoints.get(metric, {}).get("min") == key
                                    else "max" if endpoints.get(metric, {}).get("max") == key
                                    else "")),
                    ("numerator", num_tot),
                    ("denominator", den_tot),
                    ("point", "" if point is None else "{:.6f}".format(point)),
                    ("point_pct", pct(point)),
                    ("cluster_level", level),
                    ("n_clusters", n_clusters),
                    ("n_clusters_available", n_clusters_all),
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
                    ("n_repeats", len(repeats)),
                    ("per_repeat_rates_pct", "; ".join(
                        "-" if v is None else "{:.1f}".format(100 * v) for v in per_rep)),
                    ("per_repeat_min_pct", pct(rep_min)),
                    ("per_repeat_max_pct", pct(rep_max)),
                    ("B", B),
                    ("seed", seed),
                ]))

        # ------------------------------------------------ concentration table
        for config, metric in (("G_CERT", "benign_false_block_gcert"),
                               ("G_FEAS", "benign_false_block_gfeas")):
            eligible = [r for r in rows if metric_row(metric, r)[0]]
            blocked = [r for r in eligible if metric_row(metric, r)[1]]
            inst_all = sorted({r["instance_id"] for r in eligible})
            by_inst = Counter(r["instance_id"] for r in blocked)
            by_sub = Counter(r["subclass"] for r in blocked)
            by_item = Counter(r["item_id"] for r in blocked)
            total = len(blocked)
            ranked = by_inst.most_common()
            cum2 = sum(c for _, c in ranked[:2])
            hhi = (sum((c / total) ** 2 for c in by_inst.values()) if total else None)
            concentration_rows.append(OrderedDict([
                ("arm", arm),
                ("thinking", thinking),
                ("model", MODEL_LABEL[arm]),
                ("capability_set", int(in_set)),
                ("config", config),
                ("benign_rows", len(eligible)),
                ("false_blocks", total),
                ("false_block_rate_pct", pct(total / len(eligible) if eligible else None)),
                ("instances_total", len(inst_all)),
                ("instances_with_any_false_block", len(by_inst)),
                ("top1_instance", ranked[0][0] if ranked else ""),
                ("top1_false_blocks", ranked[0][1] if ranked else 0),
                ("top1_share_pct", pct(ranked[0][1] / total, 1) if total else ""),
                ("top2_false_blocks", cum2 if ranked else 0),
                ("top2_share_pct", pct(cum2 / total, 1) if total else ""),
                ("subclasses_with_any_false_block", len(by_sub)),
                ("top_subclass", by_sub.most_common(1)[0][0] if by_sub else ""),
                ("top_subclass_false_blocks", by_sub.most_common(1)[0][1] if by_sub else 0),
                ("top_subclass_share_pct",
                 pct(by_sub.most_common(1)[0][1] / total, 1) if total else ""),
                ("distinct_items_false_blocked", len(by_item)),
                ("hhi_over_instances", "" if hhi is None else "{:.3f}".format(hhi)),
                ("instance_breakdown", "|".join(
                    "{}:{}".format(k, v) for k, v in ranked)),
                ("subclass_breakdown", "|".join(
                    "{}:{}".format(k, v) for k, v in by_sub.most_common())),
            ]))

    # ---------------------------------------------------------------- write CSVs
    def write_csv(path: Path, rows: list, extra_header: list):
        with open(path, "w", encoding="utf-8", newline="") as fh:
            for line in header + extra_header:
                fh.write(line + "\n")
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print("wrote {} ({} rows)".format(path, len(rows)))

    # Monte-Carlo stability of the percentile endpoints at this B, measured on
    # the flagship cell: how much a reader should trust the last printed digit.
    mc = []
    for metric in ("benign_false_block_gcert", "v3_separation"):
        agg = defaultdict(lambda: [0, 0])
        for r in cells[("opus", "default")]:
            d, n = metric_row(metric, r)
            c = agg[r["instance_id"]]
            c[0] += d
            c[1] += n
        ks = [k for k in sorted(agg) if agg[k][0] > 0]
        den_a = np.array([agg[k][0] for k in ks], dtype=np.float64)
        num_a = np.array([agg[k][1] for k in ks], dtype=np.float64)
        los, his = [], []
        for s in range(8):
            lo, hi, _, _ = cluster_bootstrap(num_a, den_a, SEED + 7_000 + s)
            los.append(lo)
            his.append(hi)
        mc.append((metric, min(los), max(los), min(his), max(his)))

    write_csv(ANALYSIS / "DG5_e1_intervals.csv", interval_rows, [])
    write_csv(ANALYSIS / "DG5_falseblock_concentration.csv", concentration_rows, [
        "# breakdown columns are 'key:count' pairs joined by '|', ranked "
        "descending; hhi_over_instances is the Herfindahl index of the false "
        "blocks over instances (1/13 = 0.077 would be a flat spread over the "
        "13 instances that produce any).",
    ])

    # ---------------------------------------------------------------- markdown
    # Cross-arm predictability of the concentration.
    fb_instances, fb_families = {}, {}
    for key, rows in cells.items():
        blocked = [r for r in rows
                   if metric_row("benign_false_block_gcert", r) == (1, 1)]
        fb_instances[key] = Counter(r["instance_id"] for r in blocked)
        fb_families[key] = Counter(r["subclass"] for r in blocked)
    flagship_set = set(fb_instances[("opus", "default")])
    cross_arm = []
    for key in sorted(CAPABILITY_SET):
        counts = fb_instances[key]
        tot = sum(counts.values())
        if not tot:
            continue
        inside = sum(v for k, v in counts.items() if k in flagship_set)
        fam = fb_families[key].get("freeze_shift_contradiction", 0)
        cross_arm.append((key[0], key[1], tot, inside / tot, fam / tot))
    hit_sets = [set(fb_instances[k]) for k in sorted(CAPABILITY_SET) if fb_instances[k]]
    n_union = len(set().union(*hit_sets)) if hit_sets else 0
    n_common = len(set.intersection(*hit_sets)) if hit_sets else 0

    md = build_markdown(interval_rows, concentration_rows, mc, sources, stamp,
                        len(flagship_set), cross_arm, n_union, n_common)
    (ANALYSIS / "DG5_e1_intervals.md").write_text(md, encoding="utf-8")
    print("wrote {}".format(ANALYSIS / "DG5_e1_intervals.md"))
    return 0


def build_markdown(interval_rows, concentration_rows, mc, sources, stamp,
                   n_flagship_instances=0, cross_arm=(), n_union_instances=0,
                   n_common_instances=0) -> str:
    idx = {(r["arm"], r["thinking"], r["metric"], r["cluster_level"]): r
           for r in interval_rows}

    def line(r):
        return "| {} / {} | {}/{} | {} | {} to {} | {} to {} | {} |".format(
            r["arm"], r["thinking"], r["numerator"], r["denominator"],
            r["point_pct"], r["ci_lo_pct"], r["ci_hi_pct"],
            r["wilson_lo_pct"], r["wilson_hi_pct"], r["deff_width"])

    out = [
        "<!-- generated {} by code/scripts/e1_intervals.py ({}) -->".format(stamp, VERSION),
        "<!-- sources: " + "; ".join(
            "{} sha256 {}".format(k, v[:16]) for k, v in sources.items()) + " -->",
        "",
        "# DG5. Cluster-bootstrap intervals on the E1 headline rates",
        "",
        "All rates are pooled over repeats in constrained mode, exactly as in "
        "`analysis/T3_guard_value_curve.csv`. The interval is a nonparametric "
        "cluster bootstrap of the pooled ratio: clusters are drawn with "
        "replacement, each drawn cluster contributes all of its rows, and the "
        "statistic is the resampled numerator over the resampled denominator. "
        "B = {} replicates, 2.5/97.5 percentile, fixed seed. The Wilson column is "
        "the naive interval that treats rows as independent. The design effect is "
        "the squared ratio of the two widths.".format(B),
        "",
        "**Self-check.** Recomputed from the raw verdict logs before anything else: "
        "opus/default V3 separation 398/440 and opus/default benign false block "
        "under G_CERT 63/1600, both exactly matching `manuscript/macros.tex` "
        "(`\\eOneVThreeSepOpus` 90.5%, `\\eOneFalseBlockOpus` 3.9%). Every cell's "
        "point estimate for the eight published metrics was then re-derived and "
        "checked against `analysis/T3_guard_value_curve.csv` (seven of them) and "
        "`analysis/T1_e1_main.csv` (the V3 block rate under G_FEAS) to 5e-7; all "
        "80 comparisons matched.",
        "",
        "**Reading the design effect.** A value above 1 means the clustered interval "
        "is wider than the naive one, and the ratio is how many times more "
        "independent rows the naive interval pretends to have. A value below 1 "
        "appears where the per-instance rates are homogeneous: the cluster "
        "bootstrap holds each instance's rows fixed and resamples only instances, "
        "so it charges no within-instance sampling variance, and with a balanced "
        "design it can be narrower than a binomial interval. Degenerate cells "
        "(0/440, 440/440) give a zero-width interval and no usable design effect.",
        "",
        "**Monte-Carlo stability at B = {}.** Repeating the flagship "
        "(opus / default) bootstrap under eight further seeds moves the endpoints "
        "by:".format(B),
        "",
        "| metric | lower endpoint across 8 seeds | upper endpoint across 8 seeds |",
        "|---|---|---|",
    ] + [
        "| {} | {:.2f}% to {:.2f}% | {:.2f}% to {:.2f}% |".format(
            m, 100 * a, 100 * b, 100 * c, 100 * d) for m, a, b, c, d in mc
    ] + [
        "",
        "So an endpoint is trustworthy to about a tenth of a percentage point at "
        "this B. Quote endpoints rounded outward if a stated interval must be "
        "conservative.",
        "",
    ]

    for metric, (label, _) in METRICS.items():
        out += [
            "## {}".format(label),
            "",
            "Cluster = instance (primary).",
            "",
            "| arm / thinking | k/n | point % | 95% CI (instance-clustered) | "
            "95% Wilson (naive) | design effect |",
            "|---|---|---|---|---|---|",
        ]
        for r in interval_rows:
            if r["metric"] == metric and r["cluster_level"] == "instance":
                out.append(line(r))
        out += ["", "Sensitivity to the cluster definition (capability set only):", "",
                "| arm / thinking | by instance | by item | by (instance, family) |",
                "|---|---|---|---|"]
        for r in interval_rows:
            if (r["metric"] == metric and r["cluster_level"] == "instance"
                    and r["capability_set"] == 1):
                a, t = r["arm"], r["thinking"]
                cells = []
                for lv in CLUSTER_LEVELS:
                    q = idx[(a, t, metric, lv)]
                    cells.append("{} to {} (K={})".format(
                        q["ci_lo_pct"], q["ci_hi_pct"], q["n_clusters"]))
                out.append("| {} / {} | {} |".format(a, t, " | ".join(cells)))
        out.append("")

    out += [
        "## The ranges the manuscript prints, endpoint by endpoint",
        "",
        "Each row is one range macro pair in `manuscript/macros.tex`, evaluated over "
        "the eight-cell capability set. `separated` says whether the two endpoints' "
        "instance-clustered intervals are disjoint: if they overlap, the spread the "
        "range advertises is not resolved by 60 instances.",
        "",
        "An endpoint that several arms share to the printed precision is listed with "
        "all of them, because the macro names only one.",
        "",
        "| range | metric | low endpoint | 95% CI | also at the low endpoint | "
        "high endpoint | 95% CI | also at the high endpoint | separated |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    def tied(metric, r):
        """Capability-set cells printing the same one-decimal percentage."""
        same = [q for q in interval_rows
                if q["metric"] == metric and q["cluster_level"] == "instance"
                and q["capability_set"] == 1 and q["point_pct"] == r["point_pct"]
                and (q["arm"], q["thinking"]) != (r["arm"], r["thinking"])]
        return ", ".join("{} / {}".format(q["arm"], q["thinking"]) for q in same) or "-"

    for lo_macro, hi_macro, metric in PRINTED_RANGES:
        pick = {}
        for role in ("min", "max"):
            match = [r for r in interval_rows
                     if r["metric"] == metric and r["cluster_level"] == "instance"
                     and r["range_role"] == role]
            pick[role] = match[0] if match else None
        if not pick["min"] or not pick["max"]:
            continue
        a, b = pick["min"], pick["max"]
        disjoint = float(a["ci_hi"]) < float(b["ci_lo"])
        out.append("| `{}` to `{}` | {} | {}% ({} / {}) | {} to {} | {} | "
                   "{}% ({} / {}) | {} to {} | {} | {} |".format(
                       lo_macro, hi_macro, metric,
                       a["point_pct"], a["arm"], a["thinking"], a["ci_lo_pct"], a["ci_hi_pct"],
                       tied(metric, a),
                       b["point_pct"], b["arm"], b["thinking"], b["ci_lo_pct"], b["ci_hi_pct"],
                       tied(metric, b),
                       "yes" if disjoint else "NO (intervals overlap)"))
    out += [
        "",
        "## Per-repeat spread (uneven pooling made visible)",
        "",
        "| arm / thinking | repeats | V3 separation % | benign FB G_CERT % | "
        "benign FB G_FEAS % | violation pass-through G_CERT % |",
        "|---|---|---|---|---|---|",
    ]
    seen = []
    for r in interval_rows:
        key = (r["arm"], r["thinking"])
        if key in seen or r["cluster_level"] != "instance":
            continue
        seen.append(key)
        vals = []
        for m in ("v3_separation", "benign_false_block_gcert",
                  "benign_false_block_gfeas", "violation_pass_through_gcert"):
            q = idx[(key[0], key[1], m, "instance")]
            vals.append(q["per_repeat_rates_pct"])
        out.append("| {} / {} | {} | {} |".format(
            key[0], key[1], r["n_repeats"], " | ".join(vals)))

    out += [
        "",
        "## Where the false blocks land",
        "",
        "Benign rows under G_CERT, pooled over repeats. `instances hit` counts the "
        "distinct frozen instances that produce at least one false block, out of "
        "the 60 in the suite.",
        "",
        "| arm / thinking | false blocks / benign rows | instances hit / 60 | "
        "top instance | top 2 instances | top template family |",
        "|---|---|---|---|---|---|",
    ]
    for c in concentration_rows:
        if c["config"] != "G_CERT":
            continue
        out.append("| {} / {} | {}/{} | {} | {} ({}, {}%) | {} ({}%) | {} ({}, {}%) |".format(
            c["arm"], c["thinking"], c["false_blocks"], c["benign_rows"],
            c["instances_with_any_false_block"],
            c["top1_instance"], c["top1_false_blocks"], c["top1_share_pct"],
            c["top2_false_blocks"], c["top2_share_pct"],
            c["top_subclass"], c["top_subclass_false_blocks"],
            c["top_subclass_share_pct"]))
    out += [
        "",
        "### Is the concentration predictable across arms?",
        "",
        "The reference set is the {} instances the flagship (opus / default) hits "
        "under G_CERT. For each other capability-set arm the table gives the share "
        "of ITS false blocks that land inside that set, and the share that land on "
        "the single template family `freeze_shift_contradiction`.".format(
            n_flagship_instances),
        "",
        "| arm / thinking | false blocks | on the flagship's instances | "
        "on freeze_shift_contradiction |",
        "|---|---|---|---|",
    ]
    for arm, thinking, tot, share_inst, share_fam in cross_arm:
        out.append("| {} / {} | {} | {:.1f}% | {:.1f}% |".format(
            arm, thinking, tot, 100 * share_inst, 100 * share_fam))
    out += [
        "",
        "Across the eight capability-set arms, {} of the 60 instances produce at "
        "least one false block under G_CERT and {} produce one under every arm.".format(
            n_union_instances, n_common_instances),
        "",
        "## What these intervals do not establish",
        "",
        "1. **They are uncertainty over instances, not over models or prompts.** "
        "One arm's interval says how much its rate would move on a fresh draw of "
        "60 instances from the same generator. It says nothing about a different "
        "model family, a different prompt version, or a different tau.",
        "2. **Sixty clusters is a small bootstrap.** The percentile interval is "
        "known to under-cover with few clusters, so these intervals are, if "
        "anything, optimistic. They are not corrected (no BCa, no small-cluster "
        "t-adjustment).",
        "3. **The 60 instances come from only three strata** (c09_storm2_w80 with "
        "24 instances, c10_replay_400 with 24, c10_storm2_w80 with 12). Clustering "
        "at instance level treats instances inside a stratum as exchangeable. If "
        "stratum-level correlation exists the true interval is wider, and a "
        "three-cluster bootstrap cannot measure it.",
        "4. **A design effect below 1 is not evidence of extra precision.** It "
        "reflects that the cluster bootstrap conditions on each instance's own "
        "rows, which the balanced design makes near-identical across instances for "
        "some metrics.",
        "5. **The concentration result is descriptive.** It says where the false "
        "blocks landed on these 60 instances; it does not prove the same instances "
        "would be the costly ones on a new portfolio, though the cross-arm table "
        "above shows the pattern is largely shared across proposers.",
        "",
    ]
    return "\n".join(out)


if __name__ == "__main__":
    sys.exit(main())
