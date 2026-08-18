#!/usr/bin/env python
"""Per-stratum split of the E1 headline rates, plus stratum characterisation (DG9).

Why this exists
---------------
The E1 tables pool 2,000 instructions over 60 frozen instances that sit in three
strata (Table 6 of the manuscript): C9 storm2 (24 instances, 1,009 items), C10
storm2 (12, 386) and C10 replay 400 (24, 605).  A reviewer who sees only the
pooled rate cannot tell whether the certificate's headline value is carried by
one stratum.  Two of the three strata are constructed high-load scenarios and
only one is a recorded window of the corpus, so the question is sharp: does the
result survive on the recorded stratum alone?  This script splits every E1
headline rate by stratum, re-derives the no-AI (RULE) anchor level per stratum,
and characterises the three strata from the instance files themselves.

Part 1: the split
-----------------
For each of the seven schema-enforced E1 arms (qwen3-14b, qwen3.6-27b-fp8,
glm-4-9b, openai/GPT-5.4-mini, sonnet, opus, sol), constrained mode, repeats
pooled, cells are (arm, thinking) exactly as in analysis/T1_e1_main.csv and
analysis/T3_guard_value_curve.csv.  Those seven arms contribute exactly the
eight cells of the manuscript's capability set; DeepSeek is the ninth and tenth
cell of the logs and is outside the set, so it is excluded here.

Metrics, taken verbatim from code/scripts/e1_evaluate.py and reused unchanged
from code/scripts/e1_intervals.py:

``v3_separation``               over V3 rows eligible under both G_FEAS and
                                G_CERT: G_FEAS terminal in APPLIED_STATES and
                                G_CERT terminal in BLOCKED_STATES
                                (Analysis.separation, share = separated / n).
``benign_false_block_gcert``    over benign rows eligible under G_CERT: G_CERT
                                terminal in BLOCKED_STATES (Analysis.blocks).
``violation_pass_through_gcert``over non-benign rows eligible under G_CERT:
                                G_CERT terminal in APPLIED_STATES (the E3
                                convention of code/scripts/e3_replay.py; a
                                refusal is neither passed nor blocked, so it
                                sits in the denominator only).

Pass-through is read two ways, as in analysis/DG7_passthrough.csv.  The *total*
reading above counts any applied terminal, including an applied proposal that
carries no operation.  The *non-empty* reading
(``violation_pass_through_gcert_nonempty``) adds the condition ``n_ops > 0`` to
the numerator and leaves the denominator unchanged, so a violation that was
applied as a no-op does not count as having passed through.  On the flagship
cell the two differ by more than a factor of two, so the per-stratum split is
reported under both.

Four further metrics are carried because the headline pair is only readable
against them: ``v3_block_gfeas`` (what the feasibility guard alone does on V3),
``benign_false_block_gfeas``, ``violation_pass_through_gfeas`` and its
non-empty reading.

A row is *eligible* under a configuration when it carries no ``infra_error``
finding under it (e1_evaluate.Analysis.eligible).  Measured on these logs the
filter removes nothing: zero rows carry an infra finding under any
configuration.

How the slice differs from analysis/T1_e1_main.csv
--------------------------------------------------
It does not, except by partition.  The rows entering a stratum's rate are a
subset of the rows entering the published pooled rate, selected on the verdict
row's own ``stratum`` field, and the script asserts that the three strata's
numerators and denominators sum exactly to the published pooled ones for every
(cell, metric).  The verdict logs' ``stratum`` and ``instance_id`` fields were
independently checked against code/suite/v0.2/suite.jsonl on all 156,000 rows of
the eight evaluation directories: zero mismatches.

Intervals
---------
Each stratum rate carries a nonparametric cluster bootstrap interval at the
instance level (the estimator of code/scripts/e1_intervals.py: clusters drawn
with replacement, each contributing all its rows, statistic = resampled
numerator over resampled denominator, B = 20,000, 2.5/97.5 percentile).  The
cluster counts are small by construction (24, 12, 24), so these intervals are
wide and, with few clusters, known to under-cover.  The Wilson interval on the
row count is printed alongside as the naive comparator.

Part 2: the no-AI anchor level per stratum
------------------------------------------
analysis/ladder/rule_anchor.json holds one RULE anchor per (instance, standing
frozen set): 116 anchors over the 60 instances.  Two means are reported, per
stratum and overall: the plain mean over anchors, and the mean weighted by how
many suite items actually run on each anchor (the quantity the ladder's rung-1
number is built from).  The anchor for an item is keyed by
(instance_id, frozen_key) exactly as in code/scripts/ladder_replay.py.

Part 3: stratum characterisation
--------------------------------
Read from the Y1 instance store the suite replays
(/home/ziheng/PaperY-FMScheduling/data/processed/instances, overridable with
L1_Y1_ROOT).  Per instance: work-order count, technician count, offered load
(sum of processing times), the arrival window from the file's own metadata, the
provenance flag, and, for the constructed strata, the generator's declared
target utilisation.  Two derived quantities:

``offered_load_ratio``  sum(p_bh) / (technicians * window_bh).  This is the
                        corpus's own utilisation definition
                        (fmwos.generator.base_utilization: a per-business-hour
                        work rate over the technician count actually built),
                        evaluated on the realised file rather than on the fitted
                        parameter pack.  It aggregates over trades, so it hides
                        a trade-level mismatch; the bottleneck-trade ratio is
                        reported next to it.
``median_queue_depth``  time-weighted median of the baseline queue length.  The
                        instance is dispatched with the unmodified Y1
                        dispatcher (l1adapter.dispatch.dispatch_baseline, rule
                        atc, seed 0, which is the suite's own episode setting);
                        the queue length at time t is the number of orders with
                        release_bh <= t and start_bh > t, and the median is over
                        elapsed time on [0, makespan], not over events.

Self-check
----------
Before anything is written the script re-derives two published quantities from
the raw verdict logs and aborts if either differs:
  * opus / default V3 separation                    == 398/440
  * opus / default benign false block under G_CERT  == 63/1600
It then checks every (cell, metric) pooled point estimate against
analysis/T3_guard_value_curve.csv, analysis/T1_e1_main.csv and
analysis/DG7_passthrough.csv to 5e-7, and asserts that the per-stratum counts
sum to the pooled counts exactly.

Usage::

    OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 taskset -c 0-3 \
        python3 analysis/DG9_stratum_split.py

Read-only on results/, manuscript/, code/suite/ and the Y1 instance store.
Writes analysis/DG9_stratum_split.csv, analysis/DG9_stratum_split.md,
analysis/DG9_stratum_anchor.csv and analysis/DG9_stratum_characterisation.csv.

Version: l1-dg9-stratum-1.
"""

from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import json
import math
import os
import statistics
import sys
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

import numpy as np

VERSION = "l1-dg9-stratum-1"

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
ANALYSIS = ROOT / "analysis"
SUITE = ROOT / "code" / "suite" / "v0.2" / "suite.jsonl"
LADDER = ANALYSIS / "ladder"
Y1_ROOT = Path(os.environ.get("L1_Y1_ROOT", "/home/ziheng/PaperY-FMScheduling"))
INSTANCE_ROOT = Y1_ROOT / "data" / "processed" / "instances"

sys.path.insert(0, str(ROOT / "code" / "scripts"))
import passthrough_rule as pr  # noqa: E402  (the V4/V6 content rule, one source)

B = 20_000
SEED = 20260817
ALPHA = 0.05
Z = 1.959963984540054            # two-sided normal quantile at 0.975

# Terminal vocabulary, copied from code/scripts/suite_gate.py.
APPLIED_STATES = ("applied_with_certificate", "applied_uncertified")
BLOCKED_STATES = ("blocked_schema", "blocked_feas", "blocked_qual")

CONFIGS = ("G_CERT", "G_FEAS")
MODE = "M_constrained"

# The seven schema-enforced arms.  DeepSeek's evaluation directory exists in
# results/ but is outside the manuscript's capability set, so it is not read.
ARM_DIRS = OrderedDict([
    ("qwen3-14b", "e1_eval_qwen14b"),
    ("qwen3.6-27b-fp8", "e1_eval_qwen27b"),
    ("glm-4-9b", "e1_eval_glm9b"),
    ("openai", "e1_eval_gpt54mini"),
    ("sonnet", "e1_eval_sonnet5"),
    ("opus", "e1_eval_opus5"),
    ("sol", "e1_eval_sol"),
])

MODEL_LABEL = {
    "qwen3-14b": "Qwen3-14B (open, local, BF16)",
    "qwen3.6-27b-fp8": "Qwen3.6-27B-FP8 (open, local, quantized)",
    "glm-4-9b": "GLM-4-9B (open, local, SPOT-CHECK)",
    "openai": "GPT-5.4-mini (closed, budget tier)",
    "sonnet": "Claude Sonnet 5 (closed)",
    "opus": "Claude Opus 5 (closed, flagship)",
    "sol": "GPT-5.6 Sol (closed, flagship spot-check)",
}

FLAGSHIP = ("opus", "default")

STRATA = OrderedDict([
    ("c09_storm2_w80", "C9 storm2 (primary, constructed)"),
    ("c10_storm2_w80", "C10 storm2 (confirmation, constructed)"),
    ("c10_replay_400", "C10 replay 400 (buildings, recorded)"),
])

STRATUM_DIR = {
    "c09_storm2_w80": ("c09", "storm2", "w80"),
    "c10_storm2_w80": ("c10", "storm2", "w80"),
    "c10_replay_400": ("c10", "replay", "400"),
}

# metric key -> (label, pooled cross-check column, source table)
METRICS = OrderedDict([
    ("v3_separation", ("V3 separation (G-FEAS applies, G-CERT blocks)",
                       "v3_separation_share", "T3")),
    ("benign_false_block_gcert", ("Benign false block under G-CERT",
                                  "benign_false_block_gcert", "T3")),
    ("violation_pass_through_gcert",
     ("Violation pass-through under G-CERT (total reading)",
      "pass_through_total", "DG7:G_CERT")),
    ("violation_pass_through_gcert_nonempty",
     ("Violation pass-through under G-CERT (non-empty reading)",
      "pass_through_nonempty", "DG7:G_CERT")),
    ("violation_pass_through_gcert_strict",
     ("Violation pass-through under G-CERT (total reading, V4/V6 content rule)",
      "pass_through_total_strict", "DG7:G_CERT")),
    ("v3_block_gfeas", ("V3 block rate under G-FEAS", "gfeas_block_rate", "T1")),
    ("benign_false_block_gfeas", ("Benign false block under G-FEAS",
                                  "benign_false_block_gfeas", "T3")),
    ("violation_pass_through_gfeas",
     ("Violation pass-through under G-FEAS (total reading)",
      "pass_through_total", "DG7:G_FEAS")),
    ("violation_pass_through_gfeas_nonempty",
     ("Violation pass-through under G-FEAS (non-empty reading)",
      "pass_through_nonempty", "DG7:G_FEAS")),
    ("violation_pass_through_gfeas_strict",
     ("Violation pass-through under G-FEAS (total reading, V4/V6 content rule)",
      "pass_through_total_strict", "DG7:G_FEAS")),
])

HEADLINE = ("v3_separation", "benign_false_block_gcert",
            "violation_pass_through_gcert",
            "violation_pass_through_gcert_nonempty")


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


def load_suite() -> dict:
    """item_id -> (stratum, instance_id, primary_class, frozen_key)."""
    out = {}
    with open(SUITE, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            frozen = d["episode"].get("frozen_seed") or ()
            out[d["item_id"]] = (
                d["instance"]["stratum"],
                d["instance"]["instance_id"],
                d["primary_class"],
                ",".join(str(x) for x in frozen),
            )
    return out


def load_proposal_ops(dirname: str) -> dict:
    """(mode, thinking, repeat, item_id) -> the strict-parsed operation list.

    The verdict logs carry ``n_ops`` but not the operations themselves, and the
    V4/V6 content rule needs the content.  One proposal serves all three guard
    configurations, which is why the join is on the proposal key.
    """
    out = {}
    path = RESULTS / dirname / "proposals.jsonl"
    with open(path, "r", encoding="utf-8") as fh:
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


def load_arm(arm: str, dirname: str, suite: dict, suite_ops: dict) -> list:
    """Merged rows for an arm: G_CERT and G_FEAS joined on the dedup key.

    The join key is (mode, thinking, repeat, item_id), the dedup key the
    accepted tables use.  Every row's ``stratum`` and ``instance_id`` are
    checked against the suite; a disagreement is a hard error.
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
                key = (r["mode"], thinking_label(r["thinking"]),
                       r["repeat"], r["item_id"])
                if key in table:
                    raise SystemExit(
                        "REFUSING TO RUN: duplicate key {} in {}".format(key, path))
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
        for field in ("instance_id", "primary_class", "subclass", "item_id",
                      "stratum"):
            if c[field] != f[field]:
                raise SystemExit(
                    "REFUSING TO RUN: {} disagrees on {} for {}".format(
                        arm, field, key))
        s_stratum, s_instance, s_class, _ = suite[c["item_id"]]
        if (c["stratum"], c["instance_id"], c["primary_class"]) != (
                s_stratum, s_instance, s_class):
            raise SystemExit(
                "REFUSING TO RUN: {} row {} disagrees with the suite on "
                "(stratum, instance, class)".format(arm, key))
        rows.append({
            "arm": c["arm"],
            "thinking": thinking_label(c["thinking"]),
            "repeat": c["repeat"],
            "item_id": c["item_id"],
            "instance_id": c["instance_id"],
            "stratum": c["stratum"],
            "primary_class": c["primary_class"],
            "subclass": c["subclass"],
            "cert_terminal": c["terminal"],
            "feas_terminal": f["terminal"],
            "cert_infra": bool(c["infra"]),
            "feas_infra": bool(f["infra"]),
            # n_ops is null on a row the strict parse rejected; DG7's own tally
            # reads it as ``(n_ops or 0)``, which is reused here.
            "cert_n_ops": int(c.get("n_ops") or 0),
            "feas_n_ops": int(f.get("n_ops") or 0),
        })
        # The V4/V6 content rule, evaluated once per row per configuration so
        # the metric functions below stay pure counters.
        lists = suite_ops.get(c["item_id"], {})
        ops = ops_by_key.get(key)
        for prefix, terminal, n_ops in (
                ("cert", c["terminal"], rows[-1]["cert_n_ops"]),
                ("feas", f["terminal"], rows[-1]["feas_n_ops"])):
            rows[-1][prefix + "_pass_strict"] = pr.counts_as_pass_through(
                c["primary_class"], terminal in APPLIED_STATES,
                pr.applied_ops(ops, n_ops), lists.get("gold_ops"),
                lists.get("trap_ops"), lists.get("forbidden_ops"))
    return rows


# --------------------------------------------------------------------------- #
# Metric definitions (verbatim from code/scripts/e1_intervals.py)              #
# --------------------------------------------------------------------------- #
def metric_row(metric: str, row: dict):
    cls = row["primary_class"]
    if metric == "v3_separation":
        if cls != "V3" or row["cert_infra"] or row["feas_infra"]:
            return 0, 0
        num = (row["feas_terminal"] in APPLIED_STATES
               and row["cert_terminal"] in BLOCKED_STATES)
        return 1, int(num)
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
    if metric == "violation_pass_through_gcert_nonempty":
        if cls == "benign" or row["cert_infra"]:
            return 0, 0
        return 1, int(row["cert_terminal"] in APPLIED_STATES
                      and row["cert_n_ops"] > 0)
    if metric == "violation_pass_through_gcert_strict":
        if cls == "benign" or row["cert_infra"]:
            return 0, 0
        return 1, int(row["cert_pass_strict"])
    if metric == "violation_pass_through_gfeas":
        if cls == "benign" or row["feas_infra"]:
            return 0, 0
        return 1, int(row["feas_terminal"] in APPLIED_STATES)
    if metric == "violation_pass_through_gfeas_strict":
        if cls == "benign" or row["feas_infra"]:
            return 0, 0
        return 1, int(row["feas_pass_strict"])
    if metric == "violation_pass_through_gfeas_nonempty":
        if cls == "benign" or row["feas_infra"]:
            return 0, 0
        return 1, int(row["feas_terminal"] in APPLIED_STATES
                      and row["feas_n_ops"] > 0)
    raise KeyError(metric)


# --------------------------------------------------------------------------- #
# Interval machinery (verbatim from code/scripts/e1_intervals.py)              #
# --------------------------------------------------------------------------- #
def wilson(k: int, n: int):
    if n == 0:
        return None, None
    p = k / n
    denom = 1.0 + Z * Z / n
    centre = (p + Z * Z / (2 * n)) / denom
    half = (Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def cluster_bootstrap(num: np.ndarray, den: np.ndarray, seed: int, b: int = B):
    k = num.shape[0]
    if k == 0:
        return None, None
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
    return float(lo), float(hi)


def pct(x, digits=1):
    return "" if x is None else "{:.{d}f}".format(100 * x, d=digits)


# --------------------------------------------------------------------------- #
# Part 3 helpers: instance characterisation                                    #
# --------------------------------------------------------------------------- #
def _queue_segments(instance: dict, schedule: dict):
    """The baseline queue length as a step function: [(length, elapsed time)].

    The queue length at time t is the number of orders released at or before t
    that have not started by t.  Events are +1 at every release and -1 at every
    start; the step function runs from the first event to the makespan.
    """
    starts = {a["wo"]: float(a["start_bh"]) for a in schedule["assignments"]}
    events = []
    for w in instance["work_orders"]:
        oid = str(w["id"])
        if oid not in starts:
            continue
        events.append((float(w["release_bh"]), 1))
        events.append((starts[oid], -1))
    if not events:
        return []
    events.sort()
    horizon = max(float(a["end_bh"]) for a in schedule["assignments"])
    segments = []            # (queue length, start, end)
    q = 0
    prev = events[0][0]
    i = 0
    n = len(events)
    while i < n:
        t = events[i][0]
        if t > prev:
            segments.append((q, prev, t))
        while i < n and events[i][0] == t:
            q += events[i][1]
            i += 1
        prev = t
    if horizon > prev:
        segments.append((q, prev, horizon))
    return segments


def queue_stats(segments, upto: float = None):
    """Time-weighted median, mean and max of a queue step function.

    ``upto`` truncates the integration at that time, which is how the
    arrival-window figure is taken: a replay instance releases its 400 orders
    over a few business hours and then runs a long tail of large jobs with an
    empty queue, so a median over the whole makespan reports the tail rather
    than the congestion.
    """
    parts = []
    for q, a, b in segments:
        end = b if upto is None else min(b, upto)
        if end > a:
            parts.append((q, end - a))
    total = sum(dt for _, dt in parts)
    if total <= 0:
        return None, None, None
    mean_q = sum(qv * dt for qv, dt in parts) / total
    max_q = max(qv for qv, _ in parts)
    parts.sort()
    acc = 0.0
    med_q = parts[-1][0]
    for qv, dt in parts:
        acc += dt
        if acc >= total / 2.0:
            med_q = qv
            break
    return float(med_q), float(mean_q), int(max_q)


def characterise_instance(path: Path, dispatch_mod):
    inst = json.load(open(path, "r", encoding="utf-8"))
    meta = inst["meta"]
    wos = inst["work_orders"]
    techs = inst["technicians"]
    n_tech = len(techs)
    window_bh = float(meta["window_bh"])
    load = sum(float(w["p_bh"]) for w in wos)

    per_trade_load = defaultdict(float)
    per_trade_tech = Counter(t["trade"] for t in techs)
    for w in wos:
        per_trade_load[str(w["trade"])] += float(w["p_bh"])
    trade_ratios = {}
    for tr, lo in per_trade_load.items():
        cap = per_trade_tech.get(tr, 0) * window_bh
        if cap > 0:
            trade_ratios[tr] = lo / cap
    bottleneck = max(trade_ratios.items(), key=lambda kv: kv[1]) if trade_ratios else ("", None)

    sched = dispatch_mod.dispatch_baseline(inst, "atc", 0)
    makespan = max(float(a["end_bh"]) for a in sched["assignments"])
    segments = _queue_segments(inst, sched)
    med_q, mean_q, max_q = queue_stats(segments)
    med_q_w, mean_q_w, _ = queue_stats(segments, upto=window_bh)
    release_of = {str(w["id"]): float(w["release_bh"]) for w in wos}
    waits = [float(a["start_bh"]) - release_of[a["wo"]]
             for a in sched["assignments"]]
    n_queued = sum(1 for w in waits if w > 1e-6)

    return OrderedDict([
        ("instance_id", meta["id"]),
        ("stratum", ""),
        ("provenance", meta.get("provenance", "")),
        ("window_start", str(meta.get("window_start", ""))),
        ("n_work_orders", len(wos)),
        ("n_technicians", n_tech),
        ("n_trades_with_orders", len(per_trade_load)),
        ("window_bh", "{:.4f}".format(window_bh)),
        ("offered_load_bh", "{:.2f}".format(load)),
        ("capacity_bh", "{:.2f}".format(n_tech * window_bh)),
        ("offered_load_ratio", "{:.4f}".format(load / (n_tech * window_bh))),
        ("bottleneck_trade", bottleneck[0]),
        ("bottleneck_trade_ratio",
         "" if bottleneck[1] is None else "{:.4f}".format(bottleneck[1])),
        ("u_target_declared",
         "" if meta.get("u_target") is None else "{:.2f}".format(float(meta["u_target"]))),
        ("arrival_multiplier_declared",
         "" if meta.get("arrival_multiplier") is None
         else "{:.4f}".format(float(meta["arrival_multiplier"]))),
        ("makespan_bh", "{:.4f}".format(makespan)),
        ("median_queue_depth", "" if med_q is None else "{:.1f}".format(med_q)),
        ("mean_queue_depth", "" if mean_q is None else "{:.1f}".format(mean_q)),
        ("max_queue_depth", "" if max_q is None else str(max_q)),
        ("median_queue_depth_arrival_window",
         "" if med_q_w is None else "{:.1f}".format(med_q_w)),
        ("mean_queue_depth_arrival_window",
         "" if mean_q_w is None else "{:.1f}".format(mean_q_w)),
        ("share_orders_that_queued",
         "{:.4f}".format(n_queued / len(waits)) if waits else ""),
        ("median_wait_bh", "{:.4f}".format(statistics.median(waits)) if waits else ""),
        ("mean_wait_bh", "{:.4f}".format(sum(waits) / len(waits)) if waits else ""),
    ])


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> int:
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ.setdefault(var, "4")

    suite = load_suite()
    suite_ops = pr.load_suite_ops(SUITE)
    sources = OrderedDict()
    sources[str(SUITE.relative_to(ROOT))] = sha256(SUITE)

    cells = OrderedDict()          # (arm, thinking) -> [row]
    for arm, dirname in ARM_DIRS.items():
        for config in CONFIGS:
            p = RESULTS / dirname / "verdicts_{}.jsonl".format(config)
            sources[str(p.relative_to(ROOT))] = sha256(p)
        p = RESULTS / dirname / "proposals.jsonl"
        sources[str(p.relative_to(ROOT))] = sha256(p)
        for row in load_arm(arm, dirname, suite, suite_ops):
            cells.setdefault((row["arm"], row["thinking"]), []).append(row)

    t3_path = ANALYSIS / "T3_guard_value_curve.csv"
    t1_path = ANALYSIS / "T1_e1_main.csv"
    dg7_path = ANALYSIS / "DG7_passthrough.csv"
    anchor_path = LADDER / "rule_anchor.json"
    for p in (t3_path, t1_path, dg7_path, anchor_path):
        sources[str(p.relative_to(ROOT))] = sha256(p)

    # ---------------------------------------------------------------- self-check
    flagship = cells[FLAGSHIP]
    checks = []
    for metric, want in (("v3_separation", (398, 440)),
                         ("benign_false_block_gcert", (63, 1600))):
        d = sum(metric_row(metric, r)[0] for r in flagship)
        n = sum(metric_row(metric, r)[1] for r in flagship)
        if (n, d) != want:
            raise SystemExit(
                "SELF-CHECK FAILED: opus/default {} recomputed as {}/{}, "
                "macros.tex says {}/{}.".format(metric, n, d, want[0], want[1]))
        checks.append("{} = {}/{}".format(metric, n, d))
    print("self-check OK: " + "; ".join(checks))

    # T3 / T1 cross-check on every cell, and the stratum-sum identity.
    with open(t3_path, "r", encoding="utf-8") as fh:
        t3_lines = [ln for ln in fh if not ln.startswith("#")]
    t3 = {}
    for rec in csv.DictReader(t3_lines):
        if rec["mode"] != MODE:
            continue
        t3[(rec["arm"], rec["thinking"])] = rec
    with open(t1_path, "r", encoding="utf-8") as fh:
        t1_lines = [ln for ln in fh if not ln.startswith("#")]
    t1 = {}
    for rec in csv.DictReader(t1_lines):
        if rec["mode"] != MODE or rec["repeat"] != "pooled" or rec["class"] != "V3":
            continue
        t1[(rec["arm"], rec["thinking"])] = rec
    with open(dg7_path, "r", encoding="utf-8") as fh:
        dg7_lines = [ln for ln in fh if not ln.startswith("#")]
    dg7 = {}
    for rec in csv.DictReader(dg7_lines):
        if rec["mode"] != MODE or rec["config"] not in CONFIGS:
            continue
        # DG7 prints the same thinking labels the verdict logs carry
        # ("-", "disabled", "default", "none"), so the key needs no mapping.
        dg7[(rec["arm"], rec["thinking"], rec["config"])] = rec

    tables = {"T3": t3, "T1": t1}
    mismatches = []
    n_checked = 0
    for key, rows in cells.items():
        for metric, (_, col, table) in METRICS.items():
            d_all = sum(metric_row(metric, r)[0] for r in rows)
            n_all = sum(metric_row(metric, r)[1] for r in rows)
            d_sum = n_sum = 0
            for stratum in STRATA:
                sub = [r for r in rows if r["stratum"] == stratum]
                d_sum += sum(metric_row(metric, r)[0] for r in sub)
                n_sum += sum(metric_row(metric, r)[1] for r in sub)
            if (d_sum, n_sum) != (d_all, n_all):
                mismatches.append(
                    "{} {}: strata sum to {}/{} but the pooled slice is "
                    "{}/{}".format(key, metric, n_sum, d_sum, n_all, d_all))
            if col is None:
                continue
            if table.startswith("DG7:"):
                rec = dg7.get((key[0], key[1], table.split(":", 1)[1]))
            else:
                rec = tables[table].get(key)
            if rec is None:
                mismatches.append("{} has no {} row".format(key, table))
                continue
            want = float(rec[col])
            got = n_all / d_all if d_all else float("nan")
            n_checked += 1
            if abs(got - want) > 5e-7:
                mismatches.append("{} {}: recomputed {:.6f}, {} {:.6f}".format(
                    key, metric, got, table, want))
    if mismatches:
        raise SystemExit("CROSS-CHECK FAILED:\n  " + "\n  ".join(mismatches))
    print("cross-check OK: {} published point estimates re-derived, and the "
          "three strata sum exactly to the pooled counts on all {} "
          "(cell, metric) pairs".format(n_checked, len(cells) * len(METRICS)))

    # ---------------------------------------------------------------- the split
    stamp = _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    split_rows = []
    for key in sorted(cells, key=lambda k: (list(ARM_DIRS).index(k[0]), k[1])):
        arm, thinking = key
        rows = cells[key]
        n_repeats = len({r["repeat"] for r in rows})
        for metric, (label, _, _) in METRICS.items():
            for stratum in list(STRATA) + ["ALL"]:
                sub = rows if stratum == "ALL" else [
                    r for r in rows if r["stratum"] == stratum]
                pairs = [(metric_row(metric, r), r) for r in sub]
                den = sum(p[0][0] for p in pairs)
                num = sum(p[0][1] for p in pairs)
                point = num / den if den else None

                agg = defaultdict(lambda: [0, 0])
                for (d, n), r in pairs:
                    c = agg[r["instance_id"]]
                    c[0] += d
                    c[1] += n
                ks = [k for k in sorted(agg) if agg[k][0] > 0]
                den_a = np.array([agg[k][0] for k in ks], dtype=np.float64)
                num_a = np.array([agg[k][1] for k in ks], dtype=np.float64)
                tag = "|".join((arm, thinking, metric, stratum)).encode("utf-8")
                seed = SEED + int(hashlib.sha256(tag).hexdigest()[:8], 16) % 100_000
                lo, hi = cluster_bootstrap(num_a, den_a, seed)
                w_lo, w_hi = wilson(num, den)

                split_rows.append(OrderedDict([
                    ("arm", arm),
                    ("thinking", thinking),
                    ("model", MODEL_LABEL[arm]),
                    ("n_repeats", n_repeats),
                    ("stratum", stratum),
                    ("stratum_label", STRATA.get(stratum, "all three strata pooled")),
                    ("metric", metric),
                    ("metric_label", label),
                    ("numerator", num),
                    ("denominator", den),
                    ("point", "" if point is None else "{:.6f}".format(point)),
                    ("point_pct", pct(point)),
                    ("n_instances", len(ks)),
                    ("ci_lo_pct", pct(lo)),
                    ("ci_hi_pct", pct(hi)),
                    ("wilson_lo_pct", pct(w_lo)),
                    ("wilson_hi_pct", pct(w_hi)),
                    ("B", B),
                    ("seed", seed),
                ]))

    # ---------------------------------------------------- the no-AI RULE anchor
    anchors = json.load(open(anchor_path, "r", encoding="utf-8"))
    by_key = {}
    for a in anchors:
        iid = Path(a["instance_path"]).stem
        fk = ",".join(str(x) for x in (a["frozen_seed"] or ()))
        by_key[(iid, fk)] = float(a["wwt_adjusted_bh"])
    if len(by_key) != len(anchors):
        raise SystemExit("REFUSING TO RUN: duplicate (instance, frozen set) anchors")
    instance_stratum = {}
    item_weight = Counter()
    for item_id, (stratum, instance_id, _, fk) in suite.items():
        instance_stratum[instance_id] = stratum
        akey = (instance_id, fk)
        if akey not in by_key:
            raise SystemExit(
                "REFUSING TO RUN: no RULE anchor for {}".format(akey))
        item_weight[akey] += 1

    anchor_rows = []
    for stratum in list(STRATA) + ["ALL"]:
        keys = [k for k in by_key
                if stratum == "ALL" or instance_stratum[k[0]] == stratum]
        vals = [by_key[k] for k in sorted(keys)]
        w_num = sum(by_key[k] * item_weight[k] for k in sorted(keys))
        w_den = sum(item_weight[k] for k in sorted(keys))
        anchor_rows.append(OrderedDict([
            ("stratum", stratum),
            ("stratum_label", STRATA.get(stratum, "all three strata pooled")),
            ("n_instances", len({k[0] for k in keys})),
            ("n_anchors", len(keys)),
            ("n_suite_items", w_den),
            ("mean_wwt_bh", "{:.2f}".format(statistics.mean(vals))),
            ("sd_wwt_bh", "{:.2f}".format(statistics.stdev(vals)) if len(vals) > 1 else ""),
            ("min_wwt_bh", "{:.2f}".format(min(vals))),
            ("median_wwt_bh", "{:.2f}".format(statistics.median(vals))),
            ("max_wwt_bh", "{:.2f}".format(max(vals))),
            ("item_weighted_mean_wwt_bh", "{:.2f}".format(w_num / w_den)),
        ]))

    # ------------------------------------------------ stratum characterisation
    sys.path.insert(0, str(ROOT / "code"))
    from l1adapter import dispatch as _dispatch      # noqa: E402

    char_rows = []
    used_instances = sorted({v[1] for v in suite.values()})
    for iid in used_instances:
        stratum = instance_stratum[iid]
        campus, track, size = STRATUM_DIR[stratum]
        path = INSTANCE_ROOT / campus / track / size / (iid + ".json")
        if not path.is_file():
            raise SystemExit("REFUSING TO RUN: instance file missing: {}".format(path))
        rec = characterise_instance(path, _dispatch)
        rec["stratum"] = stratum
        char_rows.append(rec)
        sources[str(path)] = sha256(path)
    print("characterised {} instances".format(len(char_rows)))

    def agg_stat(stratum, col, fn):
        vals = [float(r[col]) for r in char_rows
                if r["stratum"] == stratum and r[col] != ""]
        return fn(vals) if vals else None

    char_summary = []
    for stratum in STRATA:
        sub = [r for r in char_rows if r["stratum"] == stratum]
        prov = sorted({r["provenance"] for r in sub})
        utgt = sorted({r["u_target_declared"] for r in sub})
        char_summary.append(OrderedDict([
            ("stratum", stratum),
            ("stratum_label", STRATA[stratum]),
            ("n_instances", len(sub)),
            ("provenance", "|".join(prov)),
            ("u_target_declared", "|".join(x for x in utgt if x) or "none (recorded)"),
            ("n_work_orders_min", int(agg_stat(stratum, "n_work_orders", min))),
            ("n_work_orders_median", agg_stat(stratum, "n_work_orders", statistics.median)),
            ("n_work_orders_max", int(agg_stat(stratum, "n_work_orders", max))),
            ("n_technicians", int(agg_stat(stratum, "n_technicians", max))),
            ("window_bh_min", "{:.2f}".format(agg_stat(stratum, "window_bh", min))),
            ("window_bh_median", "{:.2f}".format(agg_stat(stratum, "window_bh", statistics.median))),
            ("window_bh_max", "{:.2f}".format(agg_stat(stratum, "window_bh", max))),
            ("offered_load_ratio_min", "{:.3f}".format(agg_stat(stratum, "offered_load_ratio", min))),
            ("offered_load_ratio_median", "{:.3f}".format(agg_stat(stratum, "offered_load_ratio", statistics.median))),
            ("offered_load_ratio_max", "{:.3f}".format(agg_stat(stratum, "offered_load_ratio", max))),
            ("bottleneck_trade_ratio_median", "{:.3f}".format(agg_stat(stratum, "bottleneck_trade_ratio", statistics.median))),
            ("median_queue_depth_min", "{:.1f}".format(agg_stat(stratum, "median_queue_depth", min))),
            ("median_queue_depth_median", "{:.1f}".format(agg_stat(stratum, "median_queue_depth", statistics.median))),
            ("median_queue_depth_max", "{:.1f}".format(agg_stat(stratum, "median_queue_depth", max))),
            ("mean_queue_depth_median", "{:.1f}".format(agg_stat(stratum, "mean_queue_depth", statistics.median))),
            ("median_queue_depth_arrival_window_median",
             "{:.1f}".format(agg_stat(stratum, "median_queue_depth_arrival_window", statistics.median))),
            ("mean_queue_depth_arrival_window_median",
             "{:.1f}".format(agg_stat(stratum, "mean_queue_depth_arrival_window", statistics.median))),
            ("max_queue_depth_median",
             "{:.0f}".format(agg_stat(stratum, "max_queue_depth", statistics.median))),
            ("share_orders_that_queued_median",
             "{:.3f}".format(agg_stat(stratum, "share_orders_that_queued", statistics.median))),
            ("median_wait_bh_median", "{:.2f}".format(agg_stat(stratum, "median_wait_bh", statistics.median))),
            ("makespan_bh_median", "{:.2f}".format(agg_stat(stratum, "makespan_bh", statistics.median))),
        ]))

    # suite-declared queue state, per stratum (l1suite.facts.Facts.queue_state:
    # orders per technician on the item's target trade; deep >= 20, moderate
    # >= 5, shallow below 5)
    qstate = Counter()
    with open(SUITE, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            qstate[(d["instance"]["stratum"], d["queue_state"])] += 1

    # ---------------------------------------------------------------- write out
    header = [
        "# generated {} by analysis/DG9_stratum_split.py ({})".format(stamp, VERSION),
        "# DG9: the E1 headline rates split by stratum, the no-AI RULE anchor "
        "level per stratum, and a characterisation of the three strata.",
        "# scope: mode M_constrained, repeats pooled, cells are (arm, thinking) "
        "over the seven schema-enforced arms (the manuscript's capability set; "
        "DeepSeek is outside it and is not read).",
        "# metric definitions taken from code/scripts/e1_evaluate.py "
        "(Analysis.separation, Analysis.blocks) and code/scripts/e3_replay.py "
        "(violation pass-through), reused unchanged from "
        "code/scripts/e1_intervals.py.  Zero rows carry an infra_error finding, "
        "so the eligibility filter removes nothing on these logs.",
        "# stratum comes from the verdict row's own stratum field, checked "
        "against code/suite/v0.2/suite.jsonl on every row.",
        "# self-check: opus/default V3 separation 398/440 and benign false block "
        "under G-CERT 63/1600 (macros.tex); every pooled point estimate "
        "re-derived against T3/T1 to 5e-7; the three strata sum exactly to the "
        "pooled numerator and denominator on every (cell, metric) pair.",
        "# CI: nonparametric cluster bootstrap of the pooled ratio, cluster = "
        "instance, B={}, 2.5/97.5 percentile.  Wilson is the naive interval on "
        "the row count.  Cluster counts are 24 / 12 / 24 by stratum, so these "
        "intervals are wide and under-cover.".format(B),
    ]
    for path, digest in sources.items():
        header.append("# {} sha256 {}".format(path, digest))

    def write_csv(path: Path, rows: list, extra: list = ()):
        if path.exists():
            raise SystemExit(
                "REFUSING TO OVERWRITE an existing analysis file: {}".format(path))
        with open(path, "w", encoding="utf-8", newline="") as fh:
            for line in list(header) + list(extra):
                fh.write(line + "\n")
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print("wrote {} ({} rows)".format(path, len(rows)))

    write_csv(ANALYSIS / "DG9_stratum_split.csv", split_rows)
    write_csv(ANALYSIS / "DG9_stratum_anchor.csv", anchor_rows, [
        "# RULE anchor = the zero-operation proposal on one (instance, standing "
        "frozen set); analysis/ladder/rule_anchor.json holds 116 of them over "
        "the 60 instances.  mean_wwt_bh weights each anchor once; "
        "item_weighted_mean_wwt_bh weights each anchor by the number of suite "
        "items that run on it, which is the weighting the ladder's rung-1 "
        "number uses.",
    ])
    write_csv(ANALYSIS / "DG9_stratum_characterisation.csv",
              [OrderedDict(list(r.items())) for r in char_rows], [
        "# one row per replayed instance.  offered_load_ratio = sum(p_bh) / "
        "(technicians * window_bh), the corpus's own utilisation definition "
        "(fmwos.generator.base_utilization) evaluated on the realised file.  "
        "median_queue_depth is the time-weighted median of the number of "
        "released-but-not-started orders under the baseline ATC dispatch "
        "(l1adapter.dispatch.dispatch_baseline, seed 0).",
        "# provenance R = recorded replay window of the corpus "
        "(fmwos.instances.build_instance); C = constructed by the Poisson "
        "generator (fmwos.generator.generate_window).",
    ])

    md = build_markdown(split_rows, anchor_rows, char_summary, char_rows,
                        qstate, sources, stamp)
    md_path = ANALYSIS / "DG9_stratum_split.md"
    if md_path.exists():
        raise SystemExit("REFUSING TO OVERWRITE {}".format(md_path))
    md_path.write_text(md, encoding="utf-8")
    print("wrote {}".format(md_path))
    return 0


def build_markdown(split_rows, anchor_rows, char_summary, char_rows, qstate,
                   sources, stamp) -> str:
    idx = {(r["arm"], r["thinking"], r["metric"], r["stratum"]): r
           for r in split_rows}
    cells = []
    for r in split_rows:
        k = (r["arm"], r["thinking"])
        if k not in cells:
            cells.append(k)

    out = [
        "<!-- generated {} by analysis/DG9_stratum_split.py ({}) -->".format(
            stamp, VERSION),
        "",
        "# DG9. The E1 headline rates, split by stratum",
        "",
        "The 2,000 suite instructions replay on 60 frozen instances in three "
        "strata. Two of the three are constructed high-load scenarios drawn "
        "from a fitted Poisson model of the campus, and one is a recorded "
        "window of the corpus. Every rate below is the published pooled rate "
        "restricted to one stratum's rows; the three strata sum exactly to the "
        "pooled numerator and denominator on every cell and metric, which the "
        "script asserts before writing.",
        "",
        "Constrained mode, repeats pooled, cells are (arm, thinking) over the "
        "seven schema-enforced arms. Intervals are instance-clustered "
        "bootstraps with 24, 12 and 24 clusters, so they are wide; read them as "
        "an order of magnitude for the uncertainty, not as a test.",
        "",
        "Pass-through is read two ways, as in `analysis/DG7_passthrough.csv`. "
        "The total reading counts any applied terminal; the non-empty reading "
        "adds `n_ops > 0` to the numerator, so a violation applied as a no-op "
        "does not count as having passed through. The denominator is the same "
        "in both. The `_strict` rows apply the V4/V6 content rule "
        "(`code/scripts/passthrough_rule.py`) to the total reading: an applied "
        "V4 or V6 row counts unless its operations are exactly the item's "
        "non-empty `gold_ops`.",
        "",
    ]

    for metric in HEADLINE:
        label = METRICS[metric][0]
        out += [
            "## {}".format(label),
            "",
            "| arm / thinking | C9 storm2 (24 inst.) | C10 storm2 (12 inst.) | "
            "C10 replay 400 (24 inst.) | all three pooled |",
            "|---|---|---|---|---|",
        ]
        for arm, thinking in cells:
            parts = []
            for stratum in list(STRATA) + ["ALL"]:
                r = idx[(arm, thinking, metric, stratum)]
                parts.append("{}% ({}/{}) [{} to {}]".format(
                    r["point_pct"], r["numerator"], r["denominator"],
                    r["ci_lo_pct"], r["ci_hi_pct"]))
            out.append("| {} / {} | {} |".format(arm, thinking, " | ".join(parts)))
        out.append("")

    out += [
        "## The supporting rates",
        "",
        "| metric | arm / thinking | C9 storm2 | C10 storm2 | C10 replay 400 | pooled |",
        "|---|---|---|---|---|---|",
    ]
    for metric in ("v3_block_gfeas", "benign_false_block_gfeas",
                   "violation_pass_through_gcert_strict",
                   "violation_pass_through_gfeas",
                   "violation_pass_through_gfeas_nonempty",
                   "violation_pass_through_gfeas_strict"):
        for arm, thinking in cells:
            parts = []
            for stratum in list(STRATA) + ["ALL"]:
                r = idx[(arm, thinking, metric, stratum)]
                parts.append("{}% ({}/{})".format(
                    r["point_pct"], r["numerator"], r["denominator"]))
            out.append("| {} | {} / {} | {} |".format(
                metric, arm, thinking, " | ".join(parts)))
    out.append("")

    out += [
        "## The no-AI (RULE) anchor level per stratum",
        "",
        "The RULE anchor is the zero-operation proposal: the instruction is not "
        "applied at all, so the schedule is the baseline dispatch. There is one "
        "anchor per (instance, standing frozen set). The plain mean weights each "
        "anchor once; the item-weighted mean weights each anchor by how many "
        "suite items run on it, which is the weighting the ladder's rung-1 "
        "number carries.",
        "",
        "| stratum | instances | anchors | suite items | mean (bh) | median (bh) "
        "| min (bh) | max (bh) | item-weighted mean (bh) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in anchor_rows:
        out.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            r["stratum"], r["n_instances"], r["n_anchors"], r["n_suite_items"],
            r["mean_wwt_bh"], r["median_wwt_bh"], r["min_wwt_bh"],
            r["max_wwt_bh"], r["item_weighted_mean_wwt_bh"]))
    out.append("")

    out += [
        "## What the three strata are",
        "",
        "Read from the instance files themselves. `provenance` is the corpus's "
        "own flag: `R` is a recorded replay window built by "
        "`fmwos.instances.build_instance` (the first N work orders released "
        "after a weekday-08:00 anchor, with the corpus's real order "
        "identifiers, buildings and timestamps); `C` is constructed by "
        "`fmwos.generator.generate_window`, a homogeneous Poisson superposition "
        "per trade drawn over a fixed 80-business-hour window from the campus's "
        "fitted parameter pack, with `window_start` literally set to "
        "`synthetic`. The `w80` in a storm2 filename is that 80-bh window; the "
        "`u100` is the generator's target utilisation of 1.00, reached by "
        "scaling the fitted arrival rates by `u_target / u0`.",
        "",
        "| stratum | provenance | declared u_target | work orders "
        "(min/median/max) | technicians | window bh (median) | offered load "
        "ratio (min/median/max) | bottleneck-trade ratio (median) | median "
        "queue depth over the makespan (min/median/max) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in char_summary:
        out.append("| {} | {} | {} | {} / {} / {} | {} | {} | {} / {} / {} | {} | "
                   "{} / {} / {} |".format(
                       r["stratum"], r["provenance"], r["u_target_declared"],
                       r["n_work_orders_min"], r["n_work_orders_median"],
                       r["n_work_orders_max"], r["n_technicians"],
                       r["window_bh_median"],
                       r["offered_load_ratio_min"], r["offered_load_ratio_median"],
                       r["offered_load_ratio_max"],
                       r["bottleneck_trade_ratio_median"],
                       r["median_queue_depth_min"], r["median_queue_depth_median"],
                       r["median_queue_depth_max"]))
    out += [
        "",
        "The offered-load ratio is `sum(p_bh) / (technicians * window_bh)`, the "
        "corpus's own utilisation definition evaluated on the realised file "
        "rather than on the fitted parameter pack. It aggregates over trades, "
        "so the bottleneck-trade column is given next to it. The median queue "
        "depth is the time-weighted median of the number of released but "
        "not-yet-started orders under the baseline ATC dispatch.",
        "",
        "The queue figure has to be read twice, because the two constructed "
        "strata and the recorded one have different shapes. A storm2 instance "
        "releases work at a constant rate for 80 business hours against a crew "
        "sized to that rate, so the queue is deep for essentially the whole "
        "horizon. A replay instance releases its 400 recorded orders over a "
        "short window (median 8.9 bh) and then runs a long tail of large jobs "
        "with an empty queue, so a median over the whole makespan reports the "
        "tail rather than the congestion. The second table takes the same "
        "measure over the arrival window only.",
        "",
        "| stratum | median queue depth over the arrival window (median over "
        "instances) | mean queue depth over the arrival window (median) | peak "
        "queue depth (median) | share of orders that waited at all (median) | "
        "median wait, bh (median) |",
        "|---|---|---|---|---|---|",
    ]
    for r in char_summary:
        out.append("| {} | {} | {} | {} | {} | {} |".format(
            r["stratum"], r["median_queue_depth_arrival_window_median"],
            r["mean_queue_depth_arrival_window_median"],
            r["max_queue_depth_median"],
            r["share_orders_that_queued_median"],
            r["median_wait_bh_median"]))
    out += [
        "",
        "The suite's own congestion label agrees. `queue_state` "
        "(`l1suite.facts.Facts.queue_state`) is the target trade's orders per "
        "technician over the whole window: deep at 20 or more, moderate at 5 or "
        "more, shallow below 5.",
        "",
        "| stratum | deep | moderate | shallow | not applicable |",
        "|---|---|---|---|---|",
    ]
    for stratum in STRATA:
        out.append("| {} | {} | {} | {} | {} |".format(
            stratum,
            qstate.get((stratum, "deep"), 0),
            qstate.get((stratum, "moderate"), 0),
            qstate.get((stratum, "shallow"), 0),
            qstate.get((stratum, "not_applicable"), 0)))

    out += [
        "",
        "## Sources",
        "",
    ] + ["- `{}` sha256 `{}`".format(k, v) for k, v in sources.items()] + [""]
    return "\n".join(out)


if __name__ == "__main__":
    sys.exit(main())
