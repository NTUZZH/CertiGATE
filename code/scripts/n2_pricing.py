#!/usr/bin/env python
"""N2: how accurately each quality gate prices a proposal, against the oracle.

WHY THIS EXISTS
---------------
Every quality gate in the study turns a proposal's executed schedule into a
price and refuses (refers) the proposal when the price exceeds a threshold.
The certificate prices against an analytic lower bound,

    g_cert = (obj - LB2) / max(LB2, 1 bh)            (verdicts_G_CERT.jsonl)

and the three hand-written rules price against a dispatch reference,

    D-REL1 = (obj - WT_ref1) / max(WT_ref1, 1)       WT_ref1: no-op dispatch
    D-REL2 = (obj - WT_ref2) / max(WT_ref2, 1)       WT_ref2: the adjusted
                                                     fields dispatched without
                                                     the proposal's constraints
    D-ABS  =  obj - WT_ref1                          (business hours)

(code/scripts/delta_baselines.py, e1_delta_guard_replay.py).  Neither
reference is the best schedule the adjusted instance admits, so until now the
gates could only be compared with each other, on a violation class that one of
them had admitted.  N1 (code/scripts/oracle_cost.py) brackets that best
schedule: OPT, the optimum of the relaxed adjusted instance, lies in
[lower, upper] (results/oracle_v1/brackets.jsonl).  This script reads the
brackets and measures every gate's price against the true price

    g_true = (obj - OPT) / max(OPT, 1 bh)

on the direct benchmark (the suite's canonical proposal for every item) and on
the end-to-end record (every executed proposal of results/e1_eval_*/).

FOUR LAUNCH QUESTIONS (the project's standing experiment rules), answered before the run
---------------------------------------------------------------------------------
1. PURPOSE.  One question: how far is each gate's price from the oracle's, and
   in which direction?  The numbers land in the pricing-accuracy table (signed
   error per gate, soundness), the gate-price-versus-oracle-cost figure (the
   per-row files), the decision table "which gate, in which situation" (the
   per-stratum reference gap against each gate's misses and false referrals),
   and the re-labelled quality class (how many constructed V3 items are costly
   against the optimum and not only against a heuristic reference).
2. EXPECTED RESULT.  LB2 <= OPT, so the certificate never under-prices: its
   signed error is at least minus the bracket width on every row (asserted).
   Where the bracket's lower end equals LB2, its over-pricing is at most the
   bracket width.  D-REL2's reference is an ATC dispatch, so it under-prices by
   about the reference's own gap to the optimum, which N1's first brackets put
   at 0 on c10 and up to 12% on c09.  If instead the certificate under-prices
   anywhere, the bound or the join is wrong and the script aborts.  If D-REL2
   turns out to price accurately on every stratum, the decision table has no
   row where the certificate's price matters, and the paper says so.
3. CONTAMINATION.  Read-only on results/oracle_v1/ and results/e1_eval_*/; the
   N1 campaign appends to the former while this runs, so every JSONL file is
   read once into memory (last row per key wins, as in N1) and the digests of
   the bytes read are recorded.  Outputs go to analysis/N2_* only, and nothing
   under the manuscript folder is written.  The only computation is deterministic
   dispatch (no time budget, so not a timing measurement), run on cores 8-11
   by default; cores 0-7 and 12-23 belong to other jobs and are refused.
4. DATA ACCURACY.  The suite's SHA-256 and every instance file's SHA-256
   against code/scripts/instance_manifest_l1.json (the instances_v10 snapshot,
   the one N1 and DG17 use).  The direct rows are the published
   analysis/DG1_direct_guard.csv (reading canonical, config G_CERT); the
   recomputed rules reproduce DG14's matched operating points cell by cell
   (asserted).  Every recomputed objective equals the logged one (1e-6 bh); the
   certificate's logged obj_bh and lb_bh are compared with the oracle files'
   objective and LB2 (1e-4 bh) and the mismatch counts are reported.

DECLARED DESIGN (fixed before the results were computed)
--------------------------------------------------------
POPULATION.  A row enters when its proposal reached the quality stage, so an
executed schedule and a certified gap exist.  Direct: the 1,635 such items of
DG1 (canonical reading).  End to end: the executed proposals of
proposals_index.jsonl, both modes, every arm, every repeat.  A row is COVERED
when the bracket of its (instance, field fingerprint) is on disk.

THE ORACLE PRICE AS AN INTERVAL.  g is decreasing in OPT, so OPT in
[lower, upper] gives g_true in [g(upper), g(lower)], clamped at zero as the
certificate's gap is.  When the bracket's width_rel is below 1e-3 the midpoint
of [lower, upper] is used as a point; otherwise the interval is carried.  Every
statistic is computed at both ends of the interval: a percentile is reported as
[lo, hi]; a row is under-priced, over-priced, costly or cheap only when the
whole interval says so, and the undecided rows are counted separately and kept
out of every rate's numerator and denominator.

SIGNED ERROR.  e = price - g_true for the relative gates.  For D-ABS the error
is carried in business hours, e_bh = (obj - WT_ref1) - (obj - OPT), and its
under/over shares use e_bh / max(OPT, 1).  Under-priced means e < -0.05,
over-priced e > +0.05.

OPERATING POINTS.  "published": the certificate at tau = 0.20, each rule at
the DG14 matched-benign-cost setting read from analysis/DG14_delta_baselines.csv
(block "matched"); applied to direct and end-to-end rows alike.
"dg17_heldout": end-to-end constrained rows only, each rule at the setting
DG17's primary policy (heldout_matched_loso, base G-FEAS) selected for the
row's own (arm, thinking, held-out stratum), read from the "fold" block of
analysis/DG17_e2e_delta.csv.  "at_delta": every relative gate at threshold =
delta (D-ABS has no relative threshold and is not read there).  The union is
the certificate OR D-REL2, each at its own setting.

MATERIALITY.  delta in {0.05, 0.10, 0.20}.  Oracle-costly means g_true > delta.
True positive rate on oracle-costly rows, false positive rate on oracle-cheap
rows, by class (benign, V3, V4 quality-visible, all), with 95% instance-
clustered percentile bootstrap intervals (B = 20,000, seed 20261026, one index
matrix over the 60 instances reused for every rate so the intervals are paired;
e1_delta_guard_replay.cluster_sums and bootstrap_ci).

RELABEL.  For delta in the same set: the share of the 220 V3 items whose gold
proposal has g_true > delta; the same for the 8 benign items whose canonical
D-REL2 quantity is positive (suite metric badness_relative > 0) and the 55 V4
quality-visible items (their trap proposal, the canonical one, and their gold
proposal); all 800 benign items for context.  Items use items.jsonl's executed
objectives and fingerprints.

REFERENCE GAP.  Per instance, (WT_ATC - OPT) / max(OPT, 1) on the 60 baseline
brackets, with WT_ATC the bracket's atc_total, asserted equal to the published
no-op anchor (analysis/ladder/rule_anchor.json).

THE MARGINAL READING.  g_true charges a proposal for everything between its
executed schedule and the optimum, including what the dispatcher already loses
on the untouched instance.  The instruction's own cost is the difference

    g_anchor = (ATC_base - OPT_base) / max(OPT_base, 1)   (baseline brackets)
    m_true   = g_true - g_anchor
    m_true_bh = (obj - OPT_adj) - (ATC_base - OPT_base)

When the proposal leaves every field as it was (its fingerprint is the
baseline's), OPT_adj is OPT_base and both terms share one OPT, so m_true is
evaluated as one function of OPT over the bracket; otherwise the two brackets
are independent and the interval is their difference.  The certificate's
counterpart uses recorded data only: g_cert_anchor is the anchor's own
certified gap (analysis/ladder/rule_anchor.json, asserted equal to
(ATC_base - LB2_base)/max(LB2_base, 1)), m_cert = g_cert - g_cert_anchor, and
the fifth gate G-CERT-M refers when m_cert > tau = 0.20.  The form the protocol
would deploy is the same referral rule with g_cert logged on every row, so
every acceptance still carries its absolute bound; the count of G-CERT-M
acceptances whose logged g_cert exceeds tau is reported.  G-CERT-M has no
soundness guarantee (two bounds are subtracted), so its error against m_true
is reported and not asserted.  Every table carries both truths (column
``truth``: absolute or marginal).

THE SPLIT BY OPERATION TYPE.  Every table is also split by the executed
operation list: empty; sequencing_only (pin_next, reorder, freeze, unfreeze,
batch and nothing else); field_changing (any set_priority or reassign_window).
Expectation, stated before the run: for sequencing-only proposals the relaxed
adjusted instance is the baseline, so D-REL2's delta (obj - ATC)/ATC and
m_true = (obj - ATC)/OPT differ only in the denominator, by the factor
1 + g_anchor, and D-REL2 should be near-exact against m_true there.  For
field-changing proposals OPT_adj and ATC_adj both move and the rule can
mis-price.  If D-REL2 instead mis-prices sequencing-only proposals against
m_true, the reference it dispatches is not the baseline ATC and the join is
wrong.  N2_cert_marginal.csv counts the certificate's referrals that G-CERT-M
removes, and among the covered ones those "explained by the anchor": g_true >
tau while m_true <= tau, i.e. the anchor's own gap carries the price over tau.

COVERAGE GATE.  The needed brackets are the 60 baselines plus every
(instance, fingerprint) of a population row.  If any is missing the script
refuses to write unless --partial is passed; with --partial every output is
written and marked PARTIAL with its coverage.

DETERMINISM.  The dispatcher is deterministic at (atc, seed 0); the bootstrap
is seeded; every tie-break is a total order.  WT_ref2 is cached in
analysis/N2_ref2_cache.jsonl keyed by (instance, frozen set, operation list),
with the instance file's digest, so a rerun dispatches only new units.

OUTPUTS (analysis/)
-------------------
N2_rows_direct.csv, N2_rows_e2e.csv   one row per population row: prices,
                                      bracket, g_true interval
N2_pricing_direct.csv, N2_pricing_e2e.csv   signed-error distribution per gate
N2_reference_gap.csv                  per-instance reference gap
N2_disposition.csv                    TPR/FPR per gate, operating point, delta
N2_wins.csv                           rule misses, certificate false referrals,
                                      union; decision-table skeleton
N2_cert_marginal.csv                  certificate referrals removed or added by
                                      the marginal gate, by split and class
N2_relabel.csv                        oracle-costly share of constructed classes
N2_summary.md                         headline numbers with coverage
N2_macros.tex                         with --macros

Run::

    taskset -c 8-11 python \\
        code/scripts/n2_pricing.py [--partial] [--macros]

Version: l1-n2-pricing-2
"""

from __future__ import annotations

import os

SNAPSHOT_ROOT = ((os.environ.get("L1_Y1_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "PaperY-FMScheduling")) + "/data/processed/instances_v10")
_env_root = os.environ.get("L1_INSTANCE_ROOT")
if _env_root and os.path.realpath(_env_root) != os.path.realpath(SNAPSHOT_ROOT):
    raise SystemExit("REFUSING TO RUN: L1_INSTANCE_ROOT={} is not the snapshot {}"
                     .format(_env_root, SNAPSHOT_ROOT))
os.environ["L1_INSTANCE_ROOT"] = SNAPSHOT_ROOT

import argparse  # noqa: E402
import csv  # noqa: E402
import datetime as _dt  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from collections import Counter, OrderedDict, defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent.parent
CODE = ROOT / "code"
RESULTS = ROOT / "results"
ANALYSIS = ROOT / "analysis"
ORACLE = RESULTS / "oracle_v1"
for _p in (str(CODE), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# The DG17 module caps every numerical thread pool at one on import, which is
# what each dispatch worker wants; one worker runs per pinned core.
import e1_delta_guard_replay as e1dg  # noqa: E402
import numpy as np  # noqa: E402
import suite_gate as sg  # noqa: E402

VERSION = "l1-n2-pricing-2"
#: The WT_ref2 cache rows are keyed by the version that computed them; the
#: dispatch is unchanged since version 1, so its rows stay valid.
CACHE_VERSION = "l1-n2-pricing-1"

SEED = 20261026
B_BOOT = 20_000
FLOOR_BH = 1.0
ROUND_BH = 6
TAU_PUBLISHED = 0.20
DELTAS = (0.05, 0.10, 0.20)
PRICE_TOL = 0.05
POINT_WIDTH_REL = 1e-3
OBJ_TOL_BH = 1e-4
RECOMP_TOL_BH = 1e-6
SOUND_TOL = 1e-9
#: DG1_direct_guard.csv prints the certified gap to six decimals, so the direct
#: rows' soundness test allows the printing precision.
SOUND_TOL_DIRECT = 1e-6
DEFAULT_CORES = "8-11"
FORBIDDEN_CORES = frozenset() if os.environ.get("CERTIGATE_ANY_CORES") else frozenset(range(0, 8)) | frozenset(range(12, 24))

CLASSES = ("benign", "V1", "V2", "V3", "V4", "V5", "V6")
STRATA = ("c09_storm2_w80", "c10_storm2_w80", "c10_replay_400")
RULES = ("D-REL1", "D-REL2", "D-ABS")
CERT = "G-CERT"
CERTM = "G-CERT-M"
UNION = "G-CERT|D-REL2"
UNION_M = "G-CERT-M|D-REL2"
GATES = (CERT, CERTM) + RULES
FIELD_OPS = frozenset({"set_priority", "reassign_window"})
SPLITS = ("all", "empty", "sequencing_only", "field_changing")
LABELS = ("absolute", "marginal")
DISP_CLASSES = ("benign", "V3", "V4qv", "all")
CONSTRAINING_OPS = e1dg.CONSTRAINING_OPS
CANONICAL_FIELD = {
    "benign": "gold_ops", "V1": "literal_ops", "V2": "literal_ops",
    "V3": "gold_ops", "V4": "trap_ops", "V5": "gold_ops", "V6": "forbidden_ops",
}
#: The DG14 matched settings, restated only to be asserted against the CSV.
DG14_EXPECTED = {"D-REL1": 0.02, "D-REL2": 0.02, "D-ABS": 0.8119}
#: DG14's matched tallies at those settings (DG14_delta_baselines.md), reproduced
#: here from the recomputed references: (benign refused, V3 refused).
DG14_EXPECTED_TALLY = {"D-REL1": (12, 217), "D-REL2": (0, 217), "D-ABS": (21, 220),
                       CERT: (21, 201)}
SRC_TO_ARM = {v: k for k, v in e1dg.ARM_DIRS.items()}


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


def read_jsonl_bytes(path: Path):
    """Rows and the digest of exactly the bytes read (the file may be growing)."""
    data = path.read_bytes()
    # A writer may be mid-line; keep complete lines only.
    cut = data.rfind(b"\n") + 1
    data = data[:cut]
    rows = [json.loads(ln) for ln in data.decode("utf-8").splitlines() if ln.strip()]
    return rows, hashlib.sha256(data).hexdigest(), len(data)


def read_csv_comments(path: Path):
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def read_csv_sections(path: Path):
    """Rows of a multi-block CSV whose every block repeats its own header row."""
    out, header = [], None
    with open(path, encoding="utf-8") as fh:
        for row in csv.reader(ln for ln in fh if not ln.startswith("#")):
            if not row:
                continue
            if row[0] == "block":
                header = row
                continue
            out.append(dict(zip(header, row)))
    return out


def parse_cores(text):
    out = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return sorted(out)


def gfun(obj, x):
    """The certificate's gap convention: (obj - x) / max(x, 1), clamped at zero."""
    v = (float(obj) - float(x)) / max(float(x), FLOOR_BH)
    return v if v > 0.0 else 0.0


def rel_delta(obj, ref):
    return round(obj - ref, ROUND_BH) / max(ref, FLOOR_BH)


def fmt(x, spec="{:.6f}"):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return ""
    return spec.format(x)


def pct(x, digits=1):
    return "" if x is None else "{:.{d}f}".format(100.0 * x, d=digits)


def interval_text(lo, hi, spec="{:.3f}"):
    if lo is None:
        return "n/a"
    a, b = spec.format(lo), spec.format(hi)
    if a == b:
        return a
    return "[" + a + ", " + b + "]"


class Checker:
    def __init__(self):
        self.n = 0
        self.failures = []

    def eq(self, what, expected, got, rtol=None):
        self.n += 1
        if rtol is not None and isinstance(expected, float) and isinstance(got, float):
            if abs(expected - got) > rtol * max(1.0, abs(expected)):
                self.failures.append("{}: expected {!r}, got {!r}".format(what, expected, got))
            return
        if expected != got:
            self.failures.append("{}: expected {!r}, got {!r}".format(what, expected, got))

    def true(self, what, value, detail=""):
        self.n += 1
        if not value:
            self.failures.append("{} {}".format(what, detail).strip())

    def done(self):
        if self.failures:
            print("ASSERTION FAILURES ({} of {}):".format(len(self.failures), self.n))
            for f in self.failures[:60]:
                print("  -", f)
            raise SystemExit(2)


# --------------------------------------------------------------------------- #
# Inputs                                                                       #
# --------------------------------------------------------------------------- #
def load_suite(check):
    got = sha256_file(sg.SUITE_PATH)
    if got != sg.SUITE_SHA256:
        refuse("suite sha256 {} != {}".format(got, sg.SUITE_SHA256))
    items = OrderedDict()
    for ln in open(sg.SUITE_PATH, encoding="utf-8"):
        if ln.strip():
            it = json.loads(ln)
            items[it["item_id"]] = it
    check.eq("suite items", 2000, len(items))
    return items


def instance_paths(suite, check):
    """instance_id -> snapshot path, every file verified against the manifest."""
    manifest = sg.instance_manifest()
    files = manifest["files"]
    out, digests = {}, {}
    for it in suite.values():
        iid = it["instance"]["instance_id"]
        if iid in out:
            continue
        p = Path(sg.instance_path(it))
        rel = str(p.resolve().relative_to(Path(SNAPSHOT_ROOT).resolve()))
        if rel not in files:
            refuse("{} is not in the instance manifest".format(rel))
        d = sha256_file(p)
        if d != files[rel]:
            refuse("{} hash mismatch against the manifest".format(rel))
        out[iid], digests[iid] = str(p), d
    check.eq("distinct suite instances", 60, len(out))
    return out, digests


def load_oracle(check):
    br_rows, br_sha, br_len = read_jsonl_bytes(ORACLE / "brackets.jsonl")
    brackets = {}
    for r in br_rows:
        brackets[(r["instance_id"], r["fingerprint"])] = r  # last row wins
    for r in brackets.values():
        check.true("bracket lower <= upper", r["lower"] <= r["upper"] + 1e-6,
                   json.dumps([r["instance_id"], r["fingerprint"][:10]]))
        check.true("bracket lb2 <= upper", r["lb2_total"] <= r["upper"] + 1e-6)
    items, it_sha, _ = read_jsonl_bytes(ORACLE / "items.jsonl")
    props, pr_sha, _ = read_jsonl_bytes(ORACLE / "proposals_index.jsonl")
    check.eq("oracle item rows", 2000, len(items))
    check.eq("oracle proposal rows", 78000, len(props))
    with open(ORACLE / "census.json") as fh:
        census = json.load(fh)
    digests = {"brackets.jsonl": (br_sha, br_len, len(br_rows)),
               "items.jsonl": (it_sha, None, len(items)),
               "proposals_index.jsonl": (pr_sha, None, len(props))}
    return brackets, {r["item_id"]: r for r in items}, props, census, digests


def base_fp():
    return hashlib.sha256(b"[]").hexdigest()


def dg14_settings(check):
    out = {}
    for r in read_csv_sections(ANALYSIS / "DG14_delta_baselines.csv"):
        if r["block"] == "matched" and r["class"] == "benign":
            out[r["guard"]] = float(r["setting"])
    for g, v in DG14_EXPECTED.items():
        check.true("DG14 matched setting of {}".format(g), abs(out.get(g, -1) - v) < 1e-9,
                   "csv says {}".format(out.get(g)))
    check.true("DG14 certificate operating point", abs(out.get(CERT, -1) - TAU_PUBLISHED) < 1e-12)
    return {g: out[g] for g in RULES}


def dg17_settings(check):
    """(arm, thinking, held-out stratum, rule) -> setting, primary policy, base G-FEAS."""
    out = {}
    for r in read_csv_sections(ANALYSIS / "DG17_e2e_delta.csv"):
        if r["block"] != "fold" or r["policy"] != "heldout_matched_loso" or r["base"] != "feas":
            continue
        if r["rule"] not in RULES:
            continue
        s = float("inf") if r["setting"] == "never" else float(r["setting"])
        out[(r["arm"], r["thinking"], r["fold"], r["rule"])] = s
    check.eq("DG17 primary-policy fold settings (10 cells x 3 strata x 3 rules)", 90, len(out))
    return out


# --------------------------------------------------------------------------- #
# The counterfactual reference, with a cache                                   #
# --------------------------------------------------------------------------- #
def unit_key(iid, frozen, ops):
    blob = json.dumps([iid, list(frozen), ops], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _measure_nonstrict(unit):
    """``e1dg._measure_unit`` with the schema check relaxed, for rows the guard
    applied under a lenient parse.  Same calls otherwise."""
    from l1adapter import apply as apply_mod, dispatch as dispatch_mod, evaluate

    cache = e1dg._STATE["cache"]
    path = unit["path"]
    instance = cache.instance(path)
    frozen = list(unit["frozen"])
    ops = list(unit["ops"])
    baseline = cache.baseline(path, e1dg.EPISODE_RULE, e1dg.EPISODE_SEED)
    try:
        adjusted = apply_mod.apply_proposal(
            instance, {"operations": ops}, frozen_seed=frozen,
            baseline_schedule=baseline, strict_schema=False)
        schedule = dispatch_mod.dispatch_adjusted(adjusted, e1dg.EPISODE_RULE, e1dg.EPISODE_SEED)
        obj_adjusted = evaluate.wwt(adjusted, schedule)
    except Exception as exc:  # noqa: BLE001
        return {"key": unit["key"], "error": "{}: {}".format(type(exc).__name__, exc)}
    try:
        ref_adjusted = apply_mod.apply_operations(
            adjusted.instance, [], frozen_seed=frozen, baseline_schedule=baseline)
        ref_schedule = dispatch_mod.dispatch_adjusted(ref_adjusted, e1dg.EPISODE_RULE,
                                                      e1dg.EPISODE_SEED)
        reference = evaluate.wwt(ref_adjusted, ref_schedule)
        reference_from = "dispatched_nonstrict"
    except Exception as exc:  # noqa: BLE001
        reference, reference_from = None, "unavailable:" + type(exc).__name__
    return {"key": unit["key"], "obj_adjusted": obj_adjusted, "ref2": reference,
            "reference_from": reference_from}


def _chunk(units):
    out = []
    for u in units:
        r = e1dg._measure_unit(u)
        if "error" in r:
            r = _measure_nonstrict(u)
        out.append(r)
    return out


def measure_units(units, workers, cores):
    import multiprocessing as mp

    groups = defaultdict(list)
    for u in units:
        groups[u["path"]].append(u)
    chunks = sorted(groups.values(), key=len, reverse=True)
    out = []
    if not chunks:
        return out
    if workers <= 1:
        e1dg._init(cores)
        for ch in chunks:
            out.extend(_chunk(ch))
    else:
        ctx = mp.get_context("fork")
        with ctx.Pool(workers, initializer=e1dg._init, initargs=(cores,)) as pool:
            for res in pool.imap_unordered(_chunk, chunks):
                out.extend(res)
    return out


def resolve_ref2(needed, paths, digests, cache_path, workers, cores, use_cache):
    """key -> {obj_adjusted, ref2, reference_from}; dispatches only what is new."""
    cache = {}
    if use_cache and cache_path.is_file():
        for ln in open(cache_path, encoding="utf-8"):
            if ln.strip():
                r = json.loads(ln)
                if r.get("version") == CACHE_VERSION and digests.get(r["instance_id"]) == r["instance_sha256"]:
                    cache[r["key"]] = r
    pending = [u for k, u in needed.items() if k not in cache]
    t0 = time.time()
    res = measure_units(pending, workers, cores)
    wall = time.time() - t0
    failed = [r for r in res if "error" in r]
    if failed:
        refuse("{} units could not be replayed although the log records them at the "
               "quality stage; first: {}".format(len(failed), failed[0]))
    with open(cache_path, "a", encoding="utf-8") as fh:
        for r in res:
            u = needed[r["key"]]
            row = {"key": r["key"], "instance_id": u["instance_id"],
                   "instance_sha256": digests[u["instance_id"]], "obj_adjusted": r["obj_adjusted"],
                   "ref2": r["ref2"], "reference_from": r["reference_from"],
                   "version": CACHE_VERSION}
            fh.write(json.dumps(row, sort_keys=True) + "\n")
            cache[r["key"]] = row
    return cache, len(pending), wall


# --------------------------------------------------------------------------- #
# Rows                                                                         #
# --------------------------------------------------------------------------- #
def op_split(ops):
    """empty / sequencing_only / field_changing, by the executed operation types."""
    if not ops:
        return "empty"
    kinds = {o.get("op") for o in ops if isinstance(o, dict)}
    if kinds & FIELD_OPS:
        return "field_changing"
    if kinds <= CONSTRAINING_OPS:
        return "sequencing_only"
    return "other"


def base_info(brackets, strata):
    """Per instance: the baseline bracket (effective ends) and the anchor gap interval."""
    bfp = base_fp()
    out = {}
    for iid in strata:
        b = brackets.get((iid, bfp))
        if b is None:
            out[iid] = None
            continue
        lo, up = float(b["lower"]), float(b["upper"])
        point = b["width_rel"] < POINT_WIDTH_REL
        if point:
            lo = up = 0.5 * (lo + up)
        atc = float(b["atc_total"])
        out[iid] = {"atc": atc, "lo": lo, "up": up, "point": point,
                    "lb2": float(b["lb2_total"]),
                    "ga_lo": gfun(atc, up), "ga_hi": gfun(atc, lo)}
    return out


def _xs(lo, up):
    xs = {lo, up}
    if lo < FLOOR_BH < up:
        xs.add(FLOOR_BH)
    return sorted(xs)


def attach_oracle(row, brackets, binfo):
    """Absolute interval g_true and marginal interval m_true for one row."""
    fp = row.get("fingerprint")
    b = brackets.get((row["instance_id"], fp)) if fp else None
    row["covered"] = b is not None
    row["same_as_base"] = fp == base_fp()
    for k in ("opt_lower", "opt_upper", "width_rel", "point", "g_lo", "g_hi", "lb2_oracle",
              "proved_all", "g_anchor_lo", "g_anchor_hi", "m_lo", "m_hi", "mbh_lo", "mbh_hi",
              "_lo_e", "_up_e"):
        row[k] = None
    row["covered_m"] = False
    if b is None:
        return
    lo, up = float(b["lower"]), float(b["upper"])
    point = b["width_rel"] < POINT_WIDTH_REL
    lo_e, up_e = (0.5 * (lo + up),) * 2 if point else (lo, up)
    obj = row["obj"]
    row.update(opt_lower=lo, opt_upper=up, width_rel=float(b["width_rel"]), point=point,
               g_lo=gfun(obj, up_e), g_hi=gfun(obj, lo_e), lb2_oracle=float(b["lb2_total"]),
               proved_all=bool(b["proved_all"]), _lo_e=lo_e, _up_e=up_e)
    base = binfo.get(row["instance_id"])
    if base is None:
        return
    row["covered_m"] = True
    row["g_anchor_lo"], row["g_anchor_hi"] = base["ga_lo"], base["ga_hi"]
    if row["same_as_base"]:
        # One relaxed instance, one OPT: both terms share it.
        ms = [gfun(obj, x) - gfun(base["atc"], x) for x in _xs(lo_e, up_e)]
        row["m_lo"], row["m_hi"] = min(ms), max(ms)
        row["mbh_lo"] = row["mbh_hi"] = obj - base["atc"]
    else:
        row["m_lo"] = row["g_lo"] - base["ga_hi"]
        row["m_hi"] = row["g_hi"] - base["ga_lo"]
        row["mbh_lo"] = (obj - up_e) - (base["atc"] - base["lo"])
        row["mbh_hi"] = (obj - lo_e) - (base["atc"] - base["up"])


def truth(r, label):
    if label == "absolute":
        return (r["g_lo"], r["g_hi"]) if r["covered"] else None
    return (r["m_lo"], r["m_hi"]) if r["covered_m"] else None


def prices(row):
    """Each gate's price on the row; None where the gate cannot price it."""
    obj, r1, r2 = row["obj"], row["ref1"], row["ref2"]
    row["p_" + CERT] = row["gap_cert"]
    row["p_" + CERTM] = row["gap_cert"] - row["g_cert_anchor"]
    row["p_D-REL1"] = rel_delta(obj, r1)
    row["p_D-REL2"] = None if r2 is None else rel_delta(obj, r2)
    row["p_D-ABS"] = round(obj - r1, ROUND_BH)


def errors(row):
    """Signed error intervals per gate against both truths ("e" absolute, "em" marginal)."""
    for label, pre in (("absolute", "e"), ("marginal", "em")):
        t = truth(row, label)
        for g in GATES:
            row["{}_lo_{}".format(pre, g)] = row["{}_hi_{}".format(pre, g)] = None
        row[pre + "bh_lo_D-ABS"] = row[pre + "bh_hi_D-ABS"] = None
        if t is None:
            continue
        t_lo, t_hi = t
        for g in (CERT, CERTM, "D-REL1", "D-REL2"):
            p = row["p_" + g]
            if p is not None:
                row["{}_lo_{}".format(pre, g)] = p - t_hi
                row["{}_hi_{}".format(pre, g)] = p - t_lo
        d, obj = row["p_D-ABS"], row["obj"]
        lo_e, up_e = row["_lo_e"], row["_up_e"]
        if label == "absolute":
            eb = (d - (obj - lo_e), d - (obj - up_e))
        else:
            eb = (d - row["mbh_hi"], d - row["mbh_lo"])
        row[pre + "bh_lo_D-ABS"], row[pre + "bh_hi_D-ABS"] = min(eb), max(eb)
        cands = [e / max(x, FLOOR_BH) for e in eb for x in _xs(lo_e, up_e)]
        row[pre + "_lo_D-ABS"], row[pre + "_hi_D-ABS"] = min(cands), max(cands)


def direct_rows(suite, oracle_items, anchors, anchor_gaps, check):
    out = []
    for r in read_csv_comments(ANALYSIS / "DG1_direct_guard.csv"):
        if r["reading"] != "canonical" or r["config"] != "G_CERT":
            continue
        if r["stage_reached"] != "qual":
            continue
        it = suite[r["item_id"]]
        cls = r["primary_class"]
        fld = CANONICAL_FIELD[cls]
        orow = oracle_items[r["item_id"]]
        check.eq("oracle canonical field for " + r["item_id"], fld, orow["canonical_field"])
        rec = orow[fld]
        frozen = list(it["episode"]["frozen_seed"])
        iid = r["instance_id"]
        ops = list(it.get(fld) or [])
        fk = (iid, e1dg.frozen_key(frozen))
        out.append({
            "dataset": "direct", "row_id": r["item_id"], "item_id": r["item_id"],
            "primary_class": cls, "subclass": r["subclass"], "stratum": r["stratum"],
            "instance_id": iid, "arm": "", "thinking": "", "mode": "", "repeat": "",
            "quality_visible": bool(it.get("quality_visible_candidate")),
            "n_ops": len(ops), "ops": ops, "frozen": frozen, "split": op_split(ops),
            "constraining": any(o.get("op") in CONSTRAINING_OPS for o in ops),
            "obj": float(r["obj_bh"]), "lb_cert": float(r["lb_bh"]),
            "gap_cert": float(r["certified_gap"]),
            "obj_oracle": rec["executed_wt"], "fingerprint": rec["fingerprint"],
            "ref1": anchors[fk], "g_cert_anchor": anchor_gaps[fk],
        })
    check.eq("direct rows reaching the quality stage", 1635, len(out))
    return out


def e2e_rows(suite, props_index, anchors, anchor_gaps, check):
    """Executed proposals joined to their G_CERT verdict and their logged ops."""
    by_src = defaultdict(list)
    for p in props_index:
        if p["executed"]:
            by_src[p["source"]].append(p)
    out = []
    for src in sorted(by_src):
        d = RESULTS / src
        verd = {}
        for v in e1dg.read_jsonl(d / "verdicts_G_CERT.jsonl"):
            verd[(v["item_id"], v["mode"], v.get("thinking"), int(v["repeat"]))] = v
        ops_by = {}
        for p in e1dg.read_jsonl(d / "proposals.jsonl"):
            ex = p.get("extra") or {}
            k = (p["instruction_id"], p["mode"], ex.get("thinking"), int(ex.get("repeat", 0)))
            ops_by[k] = (p.get("parsed_ops") or [], list(p.get("frozen_seed") or []))
        for p in by_src[src]:
            k = (p["instruction_id"], p["mode"], p["thinking"], int(p["repeat"]))
            v = verd.get(k)
            if v is None:
                refuse("no G_CERT verdict for {} in {}".format(k, src))
            cert = v.get("certificate") or {}
            if v.get("certificate_gap") is None or cert.get("obj_bh") is None:
                refuse("executed proposal {} in {} carries no certificate".format(k, src))
            ops, frozen = ops_by[k]
            it = suite[p["instruction_id"]]
            iid = p["instance_id"]
            fk = (iid, e1dg.frozen_key(frozen))
            out.append({
                "dataset": "e2e",
                "row_id": "{}|{}|{}|{}|{}".format(src, p["instruction_id"], p["mode"],
                                                  p["thinking"], p["repeat"]),
                "item_id": p["instruction_id"], "primary_class": p["primary_class"],
                "subclass": it.get("subclass"), "stratum": p["stratum"], "instance_id": iid,
                "arm": SRC_TO_ARM.get(src, src), "thinking": e1dg.thinking_label(v.get("thinking")),
                "mode": p["mode"], "repeat": int(p["repeat"]),
                "quality_visible": bool(it.get("quality_visible_candidate")),
                "n_ops": len(ops), "ops": ops, "frozen": frozen, "split": op_split(ops),
                "constraining": any(isinstance(o, dict) and o.get("op") in CONSTRAINING_OPS
                                    for o in ops),
                "obj": float(cert["obj_bh"]), "lb_cert": float(cert["lb_bh"]),
                "gap_cert": float(v["certificate_gap"]),
                "obj_oracle": p["logged_wt"], "fingerprint": p["fingerprint"],
                "ref1": anchors[fk], "g_cert_anchor": anchor_gaps[fk],
            })
    check.eq("executed end-to-end proposals", sum(len(v) for v in by_src.values()), len(out))
    return out


# --------------------------------------------------------------------------- #
# Statistics                                                                   #
# --------------------------------------------------------------------------- #
def pctl(vals, q):
    return float(np.percentile(np.asarray(vals, dtype=float), q)) if len(vals) else None


def pricing_table(rows, dataset, groupings):
    """Signed-error distribution per truth label, split, gate and group."""
    out = []
    for label, pre in (("absolute", "e"), ("marginal", "em")):
        cov_key = "covered" if label == "absolute" else "covered_m"
        for split in SPLITS:
            srows = [r for r in rows if split == "all" or r["split"] == split]
            for gkind, gfn in groupings:
                groups = defaultdict(list)
                for r in srows:
                    for gv in gfn(r):
                        groups[gv].append(r)
                for gv in sorted(groups, key=str):
                    rs = groups[gv]
                    cov = [r for r in rs if r[cov_key]]
                    for g in GATES:
                        klo, khi = "{}_lo_{}".format(pre, g), "{}_hi_{}".format(pre, g)
                        ok = [r for r in cov if r.get(klo) is not None]
                        lo = [r[klo] for r in ok]
                        hi = [r[khi] for r in ok]
                        under = sum(1 for r in ok if r[khi] < -PRICE_TOL)
                        under_amb = sum(1 for r in ok if r[klo] < -PRICE_TOL <= r[khi])
                        over = sum(1 for r in ok if r[klo] > PRICE_TOL)
                        over_amb = sum(1 for r in ok if r[klo] <= PRICE_TOL < r[khi])
                        und_den = len(ok) - under_amb
                        ovr_den = len(ok) - over_amb
                        rec = OrderedDict(
                            dataset=dataset, truth=label, split=split, gate=g,
                            group_kind=gkind, group=gv, rows=len(rs), covered=len(cov),
                            priced=len(ok), point_rows=sum(1 for r in ok if r["point"]),
                            interval_rows=sum(1 for r in ok if not r["point"]),
                            e_median_lo=pctl(lo, 50), e_median_hi=pctl(hi, 50),
                            e_p05_lo=pctl(lo, 5), e_p05_hi=pctl(hi, 5),
                            e_p95_lo=pctl(lo, 95), e_p95_hi=pctl(hi, 95),
                            e_min_lo=min(lo) if lo else None, e_max_hi=max(hi) if hi else None,
                            under_n=under, under_undecided=under_amb,
                            under_share=(under / und_den) if und_den else None,
                            over_n=over, over_undecided=over_amb,
                            over_share=(over / ovr_den) if ovr_den else None,
                            ebh_median_lo=None, ebh_median_hi=None)
                        if g == "D-ABS":
                            rec["ebh_median_lo"] = pctl([r[pre + "bh_lo_D-ABS"] for r in ok], 50)
                            rec["ebh_median_hi"] = pctl([r[pre + "bh_hi_D-ABS"] for r in ok], 50)
                        out.append(rec)
    return out


def soundness(rows, check, dataset, tol):
    """The certificate never under-prices g_true; its over-pricing against the bracket."""
    cov = [r for r in rows if r["covered"]]
    worst = None
    over_vs_width = []
    lb_above_lower = lb_below_lower = 0
    for r in cov:
        g_up_end = gfun(r["obj"], r["opt_upper"])  # g at the optimistic end
        margin = r["gap_cert"] - g_up_end
        check.true("certificate never under-prices ({})".format(dataset),
                   margin >= -tol, r["row_id"])
        g_low_end = gfun(r["obj"], r["opt_lower"])
        width_g = g_low_end - g_up_end
        over_vs_width.append((r["gap_cert"] - g_up_end) - width_g)
        if r["lb_cert"] > r["opt_lower"] + OBJ_TOL_BH:
            lb_above_lower += 1
        if r["lb_cert"] < r["opt_lower"] - OBJ_TOL_BH:
            lb_below_lower += 1
        worst = margin if worst is None else min(worst, margin)
    out = {"covered": len(cov), "min_margin_vs_optimistic_end": worst,
           "max_overprice_beyond_width": max(over_vs_width) if over_vs_width else None,
           "rows_overprice_beyond_width": sum(1 for x in over_vs_width if x > tol),
           "rows_lb_cert_above_bracket_lower": lb_above_lower,
           "rows_lb_cert_below_bracket_lower": lb_below_lower}
    # The marginal gate carries no soundness guarantee (two bounds are subtracted);
    # its error against m_true is reported, per split, not asserted.
    for split in SPLITS:
        rs = [r for r in rows if r["covered_m"] and (split == "all" or r["split"] == split)]
        out["marginal_" + split] = {
            "rows": len(rs),
            "certm_error_min": min((r["em_lo_" + CERTM] for r in rs), default=None),
            "certm_error_max": max((r["em_hi_" + CERTM] for r in rs), default=None),
            "certm_under_rows": sum(1 for r in rs if r["em_hi_" + CERTM] < -tol),
        }
    return out


def costly_state(r, delta, label):
    """+1 costly, 0 cheap, None undecided or uncovered, under the given truth."""
    t = truth(r, label)
    if t is None:
        return None
    if t[0] > delta:
        return 1
    if t[1] <= delta:
        return 0
    return None


def class_masks(r):
    out = ["all"]
    if r["primary_class"] in ("benign", "V3"):
        out.append(r["primary_class"])
    if r["primary_class"] == "V4" and r["quality_visible"]:
        out.append("V4qv")
    return out


def refers(r, gate, setting):
    """Does the gate refer (refuse at the quality stage) at this setting?"""
    if gate in (UNION, UNION_M):
        s_cert, s_rule = setting
        return refers(r, CERT if gate == UNION else CERTM, s_cert) or \
            refers(r, "D-REL2", s_rule)
    p = r["p_" + gate]
    return p is not None and p > setting


class Boot:
    def __init__(self, instances, seed, b):
        self.index = {iid: k for k, iid in enumerate(sorted(instances))}
        self.k = len(self.index)
        rng = np.random.default_rng(seed)
        self.idx = rng.integers(0, self.k, size=(b, self.k))

    def ci(self, rows, flags):
        num = np.array([1.0 if f else 0.0 for f in flags])
        den = np.ones(len(rows))
        ci_idx = np.array([self.index[r["instance_id"]] for r in rows], dtype=int)
        a, b = e1dg.cluster_sums(num, den, ci_idx, self.k)
        if b.sum() <= 0:
            return None, None
        return e1dg.bootstrap_ci(a, b, self.idx)


def operating_points(dataset, dg14, dg17):
    """(op name, gate) -> function row -> setting (None: the row is out of scope)."""
    ops = OrderedDict()
    ops[("published", CERT)] = lambda r: TAU_PUBLISHED
    ops[("published", CERTM)] = lambda r: TAU_PUBLISHED
    for g in RULES:
        ops[("published", g)] = lambda r, g=g: dg14[g]
    ops[("published", UNION)] = lambda r: (TAU_PUBLISHED, dg14["D-REL2"])
    ops[("published", UNION_M)] = lambda r: (TAU_PUBLISHED, dg14["D-REL2"])
    if dataset == "e2e":
        def d17(r, g):
            if r["mode"] != e1dg.MODE:
                return None
            return dg17.get((r["arm"], r["thinking"], r["stratum"], g))

        def tau_c(r):
            return TAU_PUBLISHED if r["mode"] == e1dg.MODE else None
        ops[("dg17_heldout", CERT)] = tau_c
        ops[("dg17_heldout", CERTM)] = tau_c
        for g in RULES:
            ops[("dg17_heldout", g)] = lambda r, g=g: d17(r, g)
        for u in (UNION, UNION_M):
            ops[("dg17_heldout", u)] = lambda r: (
                None if d17(r, "D-REL2") is None else (TAU_PUBLISHED, d17(r, "D-REL2")))
    return ops


def disposition_table(rows, dataset, dg14, dg17, boot):
    out = []
    buckets = defaultdict(list)
    for r in rows:
        for c in class_masks(r):
            for s in ("all", r["split"]):
                buckets[(c, s)].append(r)
    base_plans = list(operating_points(dataset, dg14, dg17).items())
    for label in LABELS:
        for delta in DELTAS:
            state = {id(r): costly_state(r, delta, label) for r in rows}
            plans = list(base_plans)
            for g in (CERT, CERTM, "D-REL1", "D-REL2"):
                plans.append((("at_delta", g), (lambda r, d=delta: d)))
            for u in (UNION, UNION_M):
                plans.append((("at_delta", u), (lambda r, d=delta: (d, d))))
            for (op, gate), sfn in plans:
                for split in SPLITS:
                    for cls in DISP_CLASSES:
                        scope = [r for r in buckets.get((cls, split), []) if sfn(r) is not None]
                        costly = [r for r in scope if state[id(r)] == 1]
                        cheap = [r for r in scope if state[id(r)] == 0]
                        covk = "covered" if label == "absolute" else "covered_m"
                        n_cov = sum(1 for r in scope if r[covk])
                        tp_flags = [refers(r, gate, sfn(r)) for r in costly]
                        fp_flags = [refers(r, gate, sfn(r)) for r in cheap]
                        tpr_ci = boot.ci(costly, tp_flags) if costly else (None, None)
                        fpr_ci = boot.ci(cheap, fp_flags) if cheap else (None, None)
                        setting = sfn(scope[0]) if scope else None
                        if op == "dg17_heldout" and gate in RULES + (UNION, UNION_M):
                            setting_label = "per (arm, thinking, stratum)"
                        elif isinstance(setting, tuple):
                            setting_label = "tau={:g}; D-REL2 theta={:g}".format(*setting)
                        elif setting is None:
                            setting_label = ""
                        else:
                            setting_label = "{:g}".format(setting)
                        out.append(OrderedDict(
                            dataset=dataset, truth=label, split=split, operating_point=op,
                            gate=gate, setting=setting_label, delta=delta, cls=cls,
                            rows_in_scope=len(scope), covered=n_cov,
                            oracle_costly=len(costly), oracle_cheap=len(cheap),
                            undecided=n_cov - len(costly) - len(cheap),
                            tp=sum(tp_flags), fp=sum(fp_flags),
                            tpr=(sum(tp_flags) / len(costly)) if costly else None,
                            tpr_lo=tpr_ci[0], tpr_hi=tpr_ci[1],
                            fpr=(sum(fp_flags) / len(cheap)) if cheap else None,
                            fpr_lo=fpr_ci[0], fpr_hi=fpr_ci[1]))
    return out


WIN_SETS = ("rule_miss", "rule_fr", "cert_miss", "cert_fr", "certm_miss", "certm_fr",
            "union_miss", "union_fr", "unionm_miss", "unionm_fr")


def wins_table(rows, dataset, dg14, ref_gap_by_stratum, cert_ref_gap_by_stratum):
    out = []

    def cls_keys(r):
        k = ["all", r["primary_class"]]
        if r["primary_class"] == "V4" and r["quality_visible"]:
            k.append("V4qv")
        return k

    keys_of = [[(s, c, sp) for s in ("all", r["stratum"]) for c in cls_keys(r)
                for sp in ("all", r["split"])] for r in rows]
    cert_ref = [refers(r, CERT, TAU_PUBLISHED) for r in rows]
    certm_ref = [refers(r, CERTM, TAU_PUBLISHED) for r in rows]
    for label in LABELS:
        tr = [truth(r, label) for r in rows]
        covk = "covered" if label == "absolute" else "covered_m"
        for delta in DELTAS:
            st = [costly_state(r, delta, label) for r in rows]
            for rule in RULES:
                rule_ref = [refers(r, rule, dg14[rule]) for r in rows]
                bins = defaultdict(lambda: defaultdict(list))
                for i, r in enumerate(rows):
                    s_ = st[i]
                    hits = {}
                    if s_ == 1:
                        hits = {"costly": True, "rule_miss": not rule_ref[i],
                                "cert_miss": not cert_ref[i], "certm_miss": not certm_ref[i],
                                "union_miss": not (cert_ref[i] or rule_ref[i]),
                                "unionm_miss": not (certm_ref[i] or rule_ref[i])}
                    elif s_ == 0:
                        hits = {"cheap": True, "rule_fr": rule_ref[i], "cert_fr": cert_ref[i],
                                "certm_fr": certm_ref[i],
                                "union_fr": cert_ref[i] or rule_ref[i],
                                "unionm_fr": certm_ref[i] or rule_ref[i]}
                    for k in keys_of[i]:
                        b = bins[k]
                        b["rows"].append(1)
                        if r[covk]:
                            b["covered"].append(1)
                        for name, on in hits.items():
                            if on:
                                b[name].append(tr[i])
                for s in ("all",) + STRATA:
                    for c in ("all",) + CLASSES + ("V4qv",):
                        for sp in SPLITS:
                            b = bins.get((s, c, sp))
                            if b is None:
                                continue
                            nc_, nh_ = len(b["costly"]), len(b["cheap"])
                            rg = ref_gap_by_stratum.get(s, (None, None))
                            rec = OrderedDict(
                                dataset=dataset, truth=label, delta=delta, rule=rule,
                                rule_setting=dg14[rule], stratum=s, cls=c, split=sp,
                                reference_gap_median_lo=rg[0], reference_gap_median_hi=rg[1],
                                certified_anchor_gap_median=cert_ref_gap_by_stratum.get(s),
                                rows=len(b["rows"]), covered=len(b["covered"]),
                                oracle_costly=nc_, oracle_cheap=nh_)
                            for name in WIN_SETS:
                                lst = b.get(name, [])
                                den = nc_ if name.endswith("miss") else nh_
                                rec[name + "_n"] = len(lst)
                                rec[name + "_rate"] = (len(lst) / den) if den else None
                                rec[name + "_truth_median_lo"] = pctl([t[0] for t in lst], 50)
                                rec[name + "_truth_median_hi"] = pctl([t[1] for t in lst], 50)
                            out.append(rec)
    return out


def cert_marginal_table(rows, dataset):
    """What subtracting the certified anchor gap does to the certificate's referrals."""
    out = []
    for split in SPLITS:
        for cls in DISP_CLASSES:
            rs = [r for r in rows if (split == "all" or r["split"] == split)
                  and cls in class_masks(r)]
            ref = [r for r in rs if refers(r, CERT, TAU_PUBLISHED)]
            refm = [r for r in rs if refers(r, CERTM, TAU_PUBLISHED)]
            removed = [r for r in ref if not refers(r, CERTM, TAU_PUBLISHED)]
            added = [r for r in refm if not refers(r, CERT, TAU_PUBLISHED)]
            ref_cov = [r for r in ref if r["covered_m"]]
            abs_costly = sum(1 for r in ref_cov if r["g_lo"] > TAU_PUBLISHED)
            marg_cheap = sum(1 for r in ref_cov if r["m_hi"] <= TAU_PUBLISHED)
            explained = sum(1 for r in ref_cov if r["g_lo"] > TAU_PUBLISHED
                            and r["m_hi"] <= TAU_PUBLISHED)
            rem_cov = [r for r in removed if r["covered_m"]]
            out.append(OrderedDict(
                dataset=dataset, split=split, cls=cls, rows=len(rs),
                cert_referred=len(ref), certm_referred=len(refm),
                removed_by_marginal=len(removed), added_by_marginal=len(added),
                removed_with_logged_gap_above_tau=sum(1 for r in removed
                                                      if r["gap_cert"] > TAU_PUBLISHED),
                cert_referred_covered=len(ref_cov),
                cert_referred_oracle_absolute_costly=abs_costly,
                cert_referred_oracle_marginal_cheap=marg_cheap,
                cert_referred_explained_by_anchor=explained,
                explained_share=(explained / len(ref_cov)) if ref_cov else None,
                removed_covered=len(rem_cov),
                removed_oracle_marginal_cheap=sum(1 for r in rem_cov
                                                  if r["m_hi"] <= TAU_PUBLISHED),
                removed_oracle_marginal_costly=sum(1 for r in rem_cov
                                                   if r["m_lo"] > TAU_PUBLISHED),
                certm_accepted_with_logged_gap_above_tau=sum(
                    1 for r in rs if not refers(r, CERTM, TAU_PUBLISHED)
                    and r["gap_cert"] > TAU_PUBLISHED)))
    return out


def reference_gap(brackets, anchors_plain, anchor_gaps, strata, check):
    bfp = base_fp()
    out = []
    for iid in sorted(strata):
        b = brackets.get((iid, bfp))
        cg = anchor_gaps[(iid, "")]
        rec = OrderedDict(instance_id=iid, stratum=strata[iid], covered=b is not None,
                          wt_atc=None, wt_anchor=anchors_plain[iid], opt_lower=None,
                          opt_upper=None, width_rel=None, proved_all=None,
                          ref_gap_lo=None, ref_gap_hi=None, ref_gap_point="",
                          certified_anchor_gap=cg, certified_anchor_gap_recomputed=None,
                          lb2_base=None)
        if b is not None:
            check.true("baseline ATC equals the published no-op anchor on " + iid,
                       abs(b["atc_total"] - anchors_plain[iid]) <= RECOMP_TOL_BH,
                       "{} vs {}".format(b["atc_total"], anchors_plain[iid]))
            recomputed = gfun(b["atc_total"], b["lb2_total"])
            check.true("recorded anchor certificate equals (ATC - LB2)/max(LB2,1) on " + iid,
                       abs(recomputed - cg) <= 1e-9, "{} vs {}".format(recomputed, cg))
            lo, up = b["lower"], b["upper"]
            if b["width_rel"] < POINT_WIDTH_REL:
                g = gfun(b["atc_total"], 0.5 * (lo + up))
                glo = ghi = g
                rec["ref_gap_point"] = fmt(g)
            else:
                glo, ghi = gfun(b["atc_total"], up), gfun(b["atc_total"], lo)
            rec.update(wt_atc=b["atc_total"], opt_lower=lo, opt_upper=up,
                       width_rel=b["width_rel"], proved_all=b["proved_all"],
                       ref_gap_lo=glo, ref_gap_hi=ghi, certified_anchor_gap_recomputed=recomputed,
                       lb2_base=b["lb2_total"])
        out.append(rec)
    by_stratum, cert_by_stratum = {}, {}
    for s in ("all",) + STRATA:
        rs = [r for r in out if r["covered"] and (s == "all" or r["stratum"] == s)]
        by_stratum[s] = (pctl([r["ref_gap_lo"] for r in rs], 50),
                         pctl([r["ref_gap_hi"] for r in rs], 50)) if rs else (None, None)
        cert_by_stratum[s] = pctl([r["certified_anchor_gap"] for r in out
                                   if s == "all" or r["stratum"] == s], 50)
    return out, by_stratum, cert_by_stratum


def relabel_table(suite, oracle_items, brackets, binfo):
    groups = OrderedDict()
    groups[("V3", "gold_ops")] = [i for i in suite.values() if i["primary_class"] == "V3"]
    groups[("benign_degrading", "gold_ops")] = [
        i for i in suite.values() if i["primary_class"] == "benign"
        and (i.get("metrics") or {}).get("badness_relative", 0.0) > 0.0]
    v4qv = [i for i in suite.values() if i["primary_class"] == "V4"
            and i.get("quality_visible_candidate")]
    groups[("V4qv", "trap_ops")] = v4qv
    groups[("V4qv", "gold_ops")] = v4qv
    groups[("benign_all", "gold_ops")] = [i for i in suite.values()
                                         if i["primary_class"] == "benign"]
    out = []
    for (name, fld), items in groups.items():
        recs = []
        for it in items:
            o = oracle_items[it["item_id"]][fld]
            row = {"instance_id": it["instance"]["instance_id"], "fingerprint": o["fingerprint"],
                   "obj": o["executed_wt"], "row_id": it["item_id"],
                   "split": op_split(it.get(fld) or [])}
            if row["obj"] is None or row["fingerprint"] is None:
                row.update(covered=False, covered_m=False)
            else:
                attach_oracle(row, brackets, binfo)
            recs.append(row)
        for label in LABELS:
            covk = "covered" if label == "absolute" else "covered_m"
            for delta in DELTAS:
                st = [costly_state(r, delta, label) for r in recs]
                n_cov = sum(1 for r in recs if r[covk])
                costly = sum(1 for s in st if s == 1)
                cheap = sum(1 for s in st if s == 0)
                und = n_cov - costly - cheap
                tl = [truth(r, label) for r in recs if r[covk]]
                out.append(OrderedDict(
                    group=name, proposal_field=fld, truth=label, delta=delta, items=len(recs),
                    field_changing_items=sum(1 for r in recs if r["split"] == "field_changing"),
                    covered=n_cov, oracle_costly=costly, oracle_cheap=cheap, undecided=und,
                    costly_share_decided=(costly / (costly + cheap)) if costly + cheap else None,
                    costly_share_lo=(costly / n_cov) if n_cov else None,
                    costly_share_hi=((costly + und) / n_cov) if n_cov else None,
                    truth_median_lo=pctl([t[0] for t in tl], 50),
                    truth_median_hi=pctl([t[1] for t in tl], 50)))
    return out


# --------------------------------------------------------------------------- #
# Writers                                                                      #
# --------------------------------------------------------------------------- #
def write_csv(path, rows, header_lines, columns=None):
    columns = columns or (list(rows[0].keys()) if rows else ["empty"])
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        for ln in header_lines:
            fh.write("# " + ln + "\n")
        w = csv.writer(fh)
        w.writerow(columns)
        for r in rows:
            w.writerow([_cell(r.get(c)) for c in columns])
    os.replace(tmp, path)


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, float):
        if math.isinf(v):
            return "inf"
        return "{:.6f}".format(v)
    return v


ROW_COLUMNS = (
    ["dataset", "row_id", "item_id", "primary_class", "subclass", "stratum", "instance_id",
     "arm", "thinking", "mode", "repeat", "quality_visible", "n_ops", "split", "constraining",
     "obj", "lb_cert", "gap_cert", "g_cert_anchor", "ref1", "ref2", "reference_from",
     "fingerprint", "same_as_base", "covered", "covered_m", "opt_lower", "opt_upper",
     "width_rel", "point", "proved_all", "lb2_oracle", "g_lo", "g_hi", "g_anchor_lo",
     "g_anchor_hi", "m_lo", "m_hi", "mbh_lo", "mbh_hi"]
    + ["p_" + g for g in GATES]
    + ["{}_{}_{}".format(pre, end, g) for pre in ("e", "em") for g in GATES
       for end in ("lo", "hi")]
    + ["ebh_lo_D-ABS", "ebh_hi_D-ABS", "embh_lo_D-ABS", "embh_hi_D-ABS"])


def macro_name(*parts):
    words = {"0.05": "Five", "0.1": "Ten", "0.2": "Twenty", "0.10": "Ten", "0.20": "Twenty"}
    out = "nTwo"
    for p in parts:
        p = words.get(str(p), str(p))
        p = "".join(ch for ch in p if ch.isalpha())
        out += p[:1].upper() + p[1:]
    return out


GATE_TOKEN = {CERT: "Cert", CERTM: "CertM", "D-REL1": "RelOne", "D-REL2": "RelTwo",
              "D-ABS": "Abs"}
SPLIT_TOKEN = {"all": "All", "empty": "Empty", "sequencing_only": "Seq",
               "field_changing": "Field"}


# --------------------------------------------------------------------------- #
# main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--partial", action="store_true",
                    help="write the outputs although some needed brackets are missing")
    ap.add_argument("--macros", action="store_true", help="also write analysis/N2_macros.tex")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--cores", default=DEFAULT_CORES)
    ap.add_argument("--boot", type=int, default=B_BOOT)
    ap.add_argument("--no-cache", dest="cache", action="store_false")
    args = ap.parse_args()

    cores = parse_cores(args.cores)
    if set(cores) & FORBIDDEN_CORES:
        refuse("cores {} overlap cores that belong to other jobs".format(cores))
    if args.workers > len(cores):
        refuse("{} workers on {} cores".format(args.workers, len(cores)))
    os.sched_setaffinity(0, set(cores))
    stamp = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
    t_start = time.time()
    check = Checker()

    # ---------------------------------------------------------------- inputs
    suite = load_suite(check)
    paths, digests = instance_paths(suite, check)
    strata = {it["instance"]["instance_id"]: it["instance"]["stratum"] for it in suite.values()}
    brackets, oracle_items, props_index, census, oracle_digests = load_oracle(check)
    anchors, _anchor_paths, anchor_gaps = e1dg.load_anchors(check)
    anchors_plain = {k[0]: v for k, v in anchors.items() if k[1] == ""}
    check.eq("plain anchors", 60, len(anchors_plain))
    for (iid, fk), gv in anchor_gaps.items():
        check.true("frozen-set anchor certificate equals the plain one on " + iid,
                   abs(gv - anchor_gaps[(iid, "")]) <= 1e-9)
    dg14 = dg14_settings(check)
    dg17 = dg17_settings(check)
    check.done()

    drows = direct_rows(suite, oracle_items, anchors, anchor_gaps, check)
    erows = e2e_rows(suite, props_index, anchors, anchor_gaps, check)
    for r in drows + erows:
        check.true("operation list falls in a declared split", r["split"] != "other", r["row_id"])
    check.done()

    # ---------------------------------------------------------------- WT_ref2
    needed = OrderedDict()
    for r in drows + erows:
        if r["constraining"]:
            k = unit_key(r["instance_id"], r["frozen"], r["ops"])
            r["unit"] = k
            if k not in needed:
                needed[k] = {"key": k, "kind": "unit", "instance_id": r["instance_id"],
                             "path": paths[r["instance_id"]], "frozen": list(r["frozen"]),
                             "ops": list(r["ops"])}
    ref2, n_new, wall_units = resolve_ref2(
        needed, paths, digests, ANALYSIS / "N2_ref2_cache.jsonl", args.workers, cores, args.cache)
    n_obj_recomp = 0
    for r in drows + erows:
        if r["constraining"]:
            m = ref2[r["unit"]]
            check.true("recomputed objective equals the logged one",
                       abs(m["obj_adjusted"] - r["obj"]) <= RECOMP_TOL_BH, r["row_id"])
            n_obj_recomp += 1
            r["ref2"], r["reference_from"] = m["ref2"], m["reference_from"]
        else:
            r["ref2"], r["reference_from"] = r["obj"], "identical_by_construction"
        prices(r)
    check.done()

    # The rules recomputed here reproduce DG14's matched tallies.
    for g, (ben, v3) in DG14_EXPECTED_TALLY.items():
        s = TAU_PUBLISHED if g == CERT else dg14[g]
        nb = sum(1 for r in drows if r["primary_class"] == "benign" and refers(r, g, s))
        nv = sum(1 for r in drows if r["primary_class"] == "V3" and refers(r, g, s))
        check.eq("DG14 matched tally of {} (benign, V3)".format(g), (ben, v3), (nb, nv))
    check.done()

    # The DG17 primary-policy settings reproduce DG17's held-out V3 separation
    # count per cell and rule (G-FEAS + rule).
    dg17_repro = []
    head = {}
    for r in read_csv_sections(ANALYSIS / "DG17_e2e_delta.csv"):
        if r["block"] == "headline" and r["policy"] == "heldout_matched_loso" \
                and r["base"] == "feas" and r["rule"] in RULES:
            head[(r["arm"], r["thinking"], r["rule"])] = int(float(r["v3_separation_num"]))
    for (arm, th, rule), expected in sorted(head.items()):
        got = 0
        for r in erows:
            if r["mode"] != e1dg.MODE or r["arm"] != arm or r["thinking"] != th:
                continue
            if r["primary_class"] != "V3":
                continue
            s = dg17.get((arm, th, r["stratum"], rule))
            if s is not None and refers(r, rule, s):
                got += 1
        dg17_repro.append((arm, th, rule, expected, got))
    n_dg17_exact = sum(1 for x in dg17_repro if x[3] == x[4])

    # ---------------------------------------------------------------- oracle join
    binfo = base_info(brackets, strata)
    for r in drows + erows:
        attach_oracle(r, brackets, binfo)
        errors(r)

    # Certificate objective and bound against the oracle files.
    mism = OrderedDict()
    for name, rows in (("direct", drows), ("e2e", erows)):
        obj_bad = sum(1 for r in rows if r["obj_oracle"] is not None
                      and abs(r["obj_oracle"] - r["obj"]) > OBJ_TOL_BH)
        obj_n = sum(1 for r in rows if r["obj_oracle"] is not None)
        lb_rows = [r for r in rows if r["covered"]]
        lb_bad = [r for r in lb_rows if abs(r["lb2_oracle"] - r["lb_cert"]) > OBJ_TOL_BH]
        mism[name] = {"obj_checked": obj_n, "obj_mismatch": obj_bad,
                      "lb_checked": len(lb_rows), "lb_mismatch": len(lb_bad),
                      "lb_mismatch_examples": [(r["row_id"], r["lb_cert"], r["lb2_oracle"])
                                               for r in lb_bad[:5]]}
        check.eq("{} rows whose certificate objective differs from the oracle file's".format(name),
                 0, obj_bad)

    sound = {"direct": soundness(drows, check, "direct", SOUND_TOL_DIRECT),
             "e2e": soundness(erows, check, "e2e", SOUND_TOL)}
    check.done()

    # ---------------------------------------------------------------- coverage
    bfp = base_fp()
    need_br = {(iid, bfp) for iid in strata}
    need_br |= {(r["instance_id"], r["fingerprint"]) for r in drows + erows}
    have_br = {k for k in need_br if k in brackets}
    cov = OrderedDict(
        brackets_on_disk=len(brackets), brackets_needed=len(need_br),
        brackets_needed_present=len(have_br),
        baseline_brackets_present=sum(1 for iid in strata if (iid, bfp) in brackets),
        direct_rows=len(drows), direct_covered=sum(1 for r in drows if r["covered"]),
        direct_covered_m=sum(1 for r in drows if r["covered_m"]),
        e2e_rows=len(erows), e2e_covered=sum(1 for r in erows if r["covered"]),
        e2e_covered_m=sum(1 for r in erows if r["covered_m"]),
        census_brackets=60 + census.get("distinct_adjusted_field_instances", 0))
    split_cov = OrderedDict()
    for name, rows in (("direct", drows), ("e2e", erows)):
        for sp in SPLITS[1:]:
            rs = [r for r in rows if r["split"] == sp]
            split_cov[(name, sp)] = (len(rs), sum(1 for r in rs if r["covered"]))
    complete = cov["brackets_needed_present"] == cov["brackets_needed"]
    status = "COMPLETE" if complete else "PARTIAL"
    print("[n2] coverage: {} of {} needed brackets ({} baselines); direct {}/{}, e2e {}/{}"
          .format(cov["brackets_needed_present"], cov["brackets_needed"],
                  cov["baseline_brackets_present"], cov["direct_covered"], cov["direct_rows"],
                  cov["e2e_covered"], cov["e2e_rows"]))
    if not complete and not args.partial:
        refuse("{} of {} needed brackets are missing; pass --partial to write marked partial "
               "outputs".format(cov["brackets_needed"] - cov["brackets_needed_present"],
                                cov["brackets_needed"]))

    # ---------------------------------------------------------------- tables
    boot = Boot(strata.keys(), SEED, args.boot)
    refgap_rows, refgap_by_stratum, cert_refgap_by_stratum = reference_gap(
        brackets, anchors_plain, anchor_gaps, strata, check)
    check.done()

    def cls_group(r):
        return [r["primary_class"]] + (
            ["V4qv"] if r["primary_class"] == "V4" and r["quality_visible"] else [])
    groupings_d = [("all", lambda r: ["all"]), ("stratum", lambda r: [r["stratum"]]),
                   ("class", cls_group)]
    groupings_e = groupings_d + [("mode", lambda r: [r["mode"]])]
    pr_d = pricing_table(drows, "direct", groupings_d)
    pr_e = pricing_table(erows, "e2e", groupings_e)
    disp = disposition_table(drows, "direct", dg14, dg17, boot) + \
        disposition_table(erows, "e2e", dg14, dg17, boot)
    wins = wins_table(drows, "direct", dg14, refgap_by_stratum, cert_refgap_by_stratum) + \
        wins_table(erows, "e2e", dg14, refgap_by_stratum, cert_refgap_by_stratum)
    certm = cert_marginal_table(drows, "direct") + cert_marginal_table(erows, "e2e")
    relabel = relabel_table(suite, oracle_items, brackets, binfo)

    # ---------------------------------------------------------------- write
    header = [
        "N2. Pricing accuracy per gate against the oracle ({}), {}".format(VERSION, stamp),
        "generated by code/scripts/n2_pricing.py",
        "coverage: {} ({} of {} needed brackets present, {} of 60 baselines; direct rows "
        "covered {}/{}, end-to-end rows covered {}/{})".format(
            status, cov["brackets_needed_present"], cov["brackets_needed"],
            cov["baseline_brackets_present"], cov["direct_covered"], cov["direct_rows"],
            cov["e2e_covered"], cov["e2e_rows"]),
        "oracle files read: " + "; ".join("{} sha256 {} ({} rows)".format(k, v[0], v[2])
                                          for k, v in oracle_digests.items()),
        "absolute truth g_true = (obj - OPT)/max(OPT,1); marginal truth m_true = g_true - "
        "g_anchor, g_anchor = (ATC_base - OPT_base)/max(OPT_base,1); OPT in [lower, upper], "
        "midpoint when width_rel < 1e-3, else every statistic at both ends ([lo, hi])",
        "G-CERT-M prices m_cert = g_cert - g_cert_anchor (both recorded) and refers when "
        "m_cert > tau; g_cert stays logged on every row",
        "split by executed operation types: empty, sequencing_only (pin_next, reorder, freeze, "
        "unfreeze, batch only), field_changing (any set_priority or reassign_window)",
        "signed error e = price - truth; under-priced e < -0.05, over-priced e > +0.05; "
        "undecided rows are excluded from the share's numerator and denominator",
        "published operating point: G-CERT and G-CERT-M tau=0.20; D-REL1 theta={:g}, "
        "D-REL2 theta={:g}, D-ABS A={:g} bh (DG14 matched)".format(
            dg14["D-REL1"], dg14["D-REL2"], dg14["D-ABS"]),
    ]
    if not complete:
        header.insert(0, "PARTIAL: not every needed bracket is on disk; every number below "
                         "is a partial reading and is not for publication")
    write_csv(ANALYSIS / "N2_rows_direct.csv", drows, header, ROW_COLUMNS)
    write_csv(ANALYSIS / "N2_rows_e2e.csv", erows, header, ROW_COLUMNS)
    write_csv(ANALYSIS / "N2_pricing_direct.csv", pr_d, header)
    write_csv(ANALYSIS / "N2_pricing_e2e.csv", pr_e, header)
    write_csv(ANALYSIS / "N2_reference_gap.csv", refgap_rows, header + [
        "ref_gap = (WT_ATC - OPT)/max(OPT,1) on the baseline instance; WT_ATC asserted "
        "equal to the published no-op anchor; certified_anchor_gap is the recorded anchor "
        "certificate (analysis/ladder/rule_anchor.json), asserted equal to "
        "(WT_ATC - LB2)/max(LB2,1)"])
    write_csv(ANALYSIS / "N2_disposition.csv", disp, header + [
        "oracle-costly: truth > delta over the whole interval; oracle-cheap: truth <= delta "
        "over the whole interval; tpr = refers | costly, fpr = refers | cheap",
        "95% instance-clustered percentile bootstrap, B={}, seed {}, one index matrix over "
        "the 60 instances".format(args.boot, SEED),
        "dg17_heldout: end-to-end constrained rows only, DG17 primary policy "
        "(heldout_matched_loso, base G-FEAS) per (arm, thinking, held-out stratum)"])
    write_csv(ANALYSIS / "N2_wins.csv", wins, header + [
        "miss: the gate accepts and the truth says costly; fr (false referral): the gate refers "
        "and the truth says cheap; union = G-CERT OR the rule, unionm = G-CERT-M OR the rule, "
        "all at their published settings"])
    write_csv(ANALYSIS / "N2_cert_marginal.csv", certm, header + [
        "removed_by_marginal: referred by G-CERT (g_cert > tau) and accepted by G-CERT-M "
        "(m_cert <= tau); explained_by_anchor: g_true > tau while m_true <= tau over the "
        "whole interval, i.e. the anchor's own gap carries the price over tau"])
    write_csv(ANALYSIS / "N2_relabel.csv", relabel, header + [
        "costly_share_decided over decided items; costly_share_lo/hi over covered items "
        "with undecided items counted cheap/costly"])

    # ---------------------------------------------------------------- summary
    def prow(table, truth_l, split, gate, kind, group):
        for r in table:
            if (r["truth"], r["split"], r["gate"], r["group_kind"], r["group"]) == \
                    (truth_l, split, gate, kind, group):
                return r
        return None

    def drow(dataset, truth_l, split, op, gate, delta, cls):
        for r in disp:
            if (r["dataset"], r["truth"], r["split"], r["operating_point"], r["gate"],
                    r["delta"], r["cls"]) == (dataset, truth_l, split, op, gate, delta, cls):
                return r
        return None

    def wrow(dataset, truth_l, delta, rule, stratum, cls, split):
        for r in wins:
            if (r["dataset"], r["truth"], r["delta"], r["rule"], r["stratum"], r["cls"],
                    r["split"]) == (dataset, truth_l, delta, rule, stratum, cls, split):
                return r
        return None

    def crow(dataset, split, cls):
        for r in certm:
            if (r["dataset"], r["split"], r["cls"]) == (dataset, split, cls):
                return r
        return None

    def relrow(group, fld, truth_l, delta):
        for r in relabel:
            if (r["group"], r["proposal_field"], r["truth"], r["delta"]) == \
                    (group, fld, truth_l, delta):
                return r
        return None

    def share_txt(n, x, und):
        return "n/a" if x is None else "{} = {}% ({} undecided)".format(n, pct(x), und)

    def rate_txt(r, name):
        x = r[name + "_rate"]
        return "n/a" if x is None else "{}% ({})".format(pct(x), r[name + "_n"])

    def tpr_txt(r, k):
        x = r[k]
        return "n/a" if x is None else "{}% [{}, {}]".format(pct(x), pct(r[k + "_lo"]),
                                                             pct(r[k + "_hi"]))

    DS_NAME = {"direct": "Direct benchmark", "e2e": "End to end"}
    L = []
    A = L.append
    A("# N2. Pricing accuracy per gate against the oracle")
    A("")
    if not complete:
        A("**PARTIAL READING.** {} of {} needed brackets were on disk ({} of 60 baselines). "
          "Every number below covers only the rows whose bracket exists and is not for "
          "publication. Direct rows covered: {} of {}. End-to-end rows covered: {} of {}."
          .format(cov["brackets_needed_present"], cov["brackets_needed"],
                  cov["baseline_brackets_present"], cov["direct_covered"], cov["direct_rows"],
                  cov["e2e_covered"], cov["e2e_rows"]))
        A("")
    A("Generated {} by `code/scripts/n2_pricing.py` (`{}`). Every number here is read "
      "from the CSVs named beside it.".format(stamp, VERSION))
    A("")
    A("Two readings of cost are carried side by side. The **absolute** truth is the executed "
      "schedule's gap to the optimum, g_true = (obj - OPT)/max(OPT, 1). The **marginal** truth "
      "subtracts what the dispatcher already loses on the untouched instance, m_true = g_true "
      "- g_anchor with g_anchor = (ATC_base - OPT_base)/max(OPT_base, 1), so it is the "
      "instruction's own cost. G-CERT-M is the certificate read the same way from recorded "
      "data only: m_cert = g_cert - g_cert_anchor, referred when m_cert > 0.20, with g_cert "
      "still logged on every row.")
    A("")
    A("## Inputs and joins")
    A("")
    A("| input | rows |")
    A("|---|---|")
    A("| direct benchmark, `analysis/DG1_direct_guard.csv` canonical/G_CERT reaching the "
      "quality stage, joined to `results/oracle_v1/items.jsonl` on item and canonical field | {} |"
      .format(len(drows)))
    A("| end-to-end, `proposals_index.jsonl` executed rows joined to `verdicts_G_CERT.jsonl` "
      "on (source, item, mode, thinking, repeat) and to `proposals.jsonl` for the operations | {} |"
      .format(len(erows)))
    A("| distinct constraining operation lists dispatched for WT_ref2 (new this run / total) | "
      "{} / {} |".format(n_new, len(needed)))
    A("| brackets on disk / needed / needed and present | {} / {} / {} |".format(
        cov["brackets_on_disk"], cov["brackets_needed"], cov["brackets_needed_present"]))
    A("")
    A("Rows and covered rows by operation split (`split` column of the row files):")
    A("")
    A("| dataset | empty | sequencing only | field changing |")
    A("|---|---|---|---|")
    for name in ("direct", "e2e"):
        A("| {} | {} | {} | {} |".format(name, *["{} / {} covered".format(*split_cov[(name, sp)])
                                                  for sp in SPLITS[1:]]))
    A("")
    A("Rule settings read: D-REL1 theta = {:g}, D-REL2 theta = {:g}, D-ABS A = {:g} bh "
      "(`DG14_delta_baselines.csv`, block matched; their benign and V3 tallies reproduce DG14 "
      "exactly). DG17 primary-policy settings: 90 (arm, thinking, held-out stratum, rule) cells "
      "from `DG17_e2e_delta.csv`; with them the recomputed held-out V3 separation count "
      "reproduces DG17 on {} of {} (cell, rule) pairs.".format(
          dg14["D-REL1"], dg14["D-REL2"], dg14["D-ABS"], n_dg17_exact, len(dg17_repro)))
    A("")
    A("Certificate against the oracle files: objective mismatches above 1e-4 bh, direct {} of "
      "{}, end to end {} of {}; bound (logged lb_bh against the bracket's LB2) mismatches, "
      "direct {} of {}, end to end {} of {}. The recorded anchor certificate equals "
      "(ATC_base - LB2_base)/max(LB2_base, 1) on all 60 instances (asserted).".format(
          mism["direct"]["obj_mismatch"], mism["direct"]["obj_checked"],
          mism["e2e"]["obj_mismatch"], mism["e2e"]["obj_checked"],
          mism["direct"]["lb_mismatch"], mism["direct"]["lb_checked"],
          mism["e2e"]["lb_mismatch"], mism["e2e"]["lb_checked"]))
    A("")
    A("## 1. Soundness and pricing error (`N2_pricing_direct.csv`, `N2_pricing_e2e.csv`)")
    A("")
    for ds, table in (("direct", pr_d), ("e2e", pr_e)):
        A("**{}, absolute truth, all splits.** Signed error e = price - g_true over covered "
          "rows; [lo, hi] where a bracket is wider than 1e-3.".format(DS_NAME[ds]))
        A("")
        A("| gate | priced rows | median e | 5th pct | 95th pct | under-priced > 0.05 | "
          "over-priced > 0.05 |")
        A("|---|---|---|---|---|---|---|")
        for g in GATES:
            r = prow(table, "absolute", "all", g, "all", "all")
            A("| {} | {} | {} | {} | {} | {} | {} |".format(
                g, r["priced"], interval_text(r["e_median_lo"], r["e_median_hi"]),
                interval_text(r["e_p05_lo"], r["e_p05_hi"]),
                interval_text(r["e_p95_lo"], r["e_p95_hi"]),
                share_txt(r["under_n"], r["under_share"], r["under_undecided"]),
                share_txt(r["over_n"], r["over_share"], r["over_undecided"])))
        A("")
        s = sound[ds]
        A("Soundness: on {} covered rows the certificate's gap minus the oracle's optimistic end "
          "has minimum {}, so it never under-prices g_true (asserted). Rows whose over-pricing "
          "exceeds the bracket's own width: {}. The logged bound sits strictly below the "
          "bracket's lower end on {} rows and above it on {}.".format(
              s["covered"], fmt(s["min_margin_vs_optimistic_end"], "{:.2e}"),
              s["rows_overprice_beyond_width"], s["rows_lb_cert_below_bracket_lower"],
              s["rows_lb_cert_above_bracket_lower"]))
        A("")
        A("**{}, marginal truth, by split.** Signed error e = price - m_true.".format(DS_NAME[ds]))
        A("")
        A("| split | gate | priced rows | median e | 5th pct | 95th pct | under-priced > 0.05 | "
          "over-priced > 0.05 |")
        A("|---|---|---|---|---|---|---|---|")
        for sp in ("sequencing_only", "field_changing", "empty", "all"):
            for g in (CERTM, "D-REL2", CERT, "D-ABS"):
                r = prow(table, "marginal", sp, g, "all", "all")
                if r is None:
                    continue
                A("| {} | {} | {} | {} | {} | {} | {} | {} |".format(
                    sp, g, r["priced"], interval_text(r["e_median_lo"], r["e_median_hi"]),
                    interval_text(r["e_p05_lo"], r["e_p05_hi"]),
                    interval_text(r["e_p95_lo"], r["e_p95_hi"]),
                    share_txt(r["under_n"], r["under_share"], r["under_undecided"]),
                    share_txt(r["over_n"], r["over_share"], r["over_undecided"])))
        A("")
        A("G-CERT-M against m_true (no guarantee, reported): error range per split " + "; ".join(
            "{} [{}, {}] on {} rows, {} rows below zero".format(
                sp, fmt(s["marginal_" + sp]["certm_error_min"], "{:.4f}"),
                fmt(s["marginal_" + sp]["certm_error_max"], "{:.4f}"),
                s["marginal_" + sp]["rows"], s["marginal_" + sp]["certm_under_rows"])
            for sp in SPLITS) + ".")
        A("")
        A("D-REL2 median signed error by stratum, all splits, with the stratum's median reference "
          "gap:")
        A("")
        A("| stratum | D-REL2 median e (absolute) | D-REL2 median e (marginal) | G-CERT-M median "
          "e (marginal) | median reference gap | median certified anchor gap |")
        A("|---|---|---|---|---|---|")
        for st in STRATA:
            ra = prow(table, "absolute", "all", "D-REL2", "stratum", st)
            rm = prow(table, "marginal", "all", "D-REL2", "stratum", st)
            rc = prow(table, "marginal", "all", CERTM, "stratum", st)
            rg = refgap_by_stratum.get(st, (None, None))

            def it(r):
                return interval_text(r["e_median_lo"], r["e_median_hi"]) if r else "n/a"
            A("| {} | {} | {} | {} | {} | {} |".format(
                st, it(ra), it(rm), it(rc), interval_text(rg[0], rg[1]),
                fmt(cert_refgap_by_stratum.get(st), "{:.3f}")))
        A("")
    A("## Reference gap per instance (`N2_reference_gap.csv`)")
    A("")
    A("| stratum | instances covered | median oracle gap | max oracle gap | median certified "
      "anchor gap | instances certified above 0.20 |")
    A("|---|---|---|---|---|---|")
    for st in ("all",) + STRATA:
        rs = [r for r in refgap_rows if r["covered"] and (st == "all" or r["stratum"] == st)]
        allr = [r for r in refgap_rows if st == "all" or r["stratum"] == st]
        A("| {} | {} | {} | {} | {} | {} |".format(
            st, len(rs), interval_text(*refgap_by_stratum.get(st, (None, None))),
            interval_text(max(r["ref_gap_lo"] for r in rs), max(r["ref_gap_hi"] for r in rs))
            if rs else "n/a", fmt(cert_refgap_by_stratum.get(st), "{:.3f}"),
            sum(1 for r in allr if r["certified_anchor_gap"] > TAU_PUBLISHED)))
    A("")
    A("## 2. The certificate's referrals under the marginal reading (`N2_cert_marginal.csv`)")
    A("")
    A("| dataset | split | class | G-CERT referred | G-CERT-M referred | removed | added | "
      "referred and covered | of these, explained by the anchor gap |")
    A("|---|---|---|---|---|---|---|---|---|")
    for ds in ("direct", "e2e"):
        for sp in SPLITS:
            for cls in ("benign", "V3", "V4qv", "all"):
                r = crow(ds, sp, cls)
                if not r["rows"]:
                    continue
                A("| {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                    ds, sp, cls, r["cert_referred"], r["certm_referred"],
                    r["removed_by_marginal"], r["added_by_marginal"],
                    r["cert_referred_covered"], r["cert_referred_explained_by_anchor"]))
    A("")
    A("## 3. Disposition agreement with the oracle (`N2_disposition.csv`)")
    A("")
    for truth_l in LABELS:
        for ds in ("direct", "e2e"):
            A("**{}, {} truth**, published operating points, all classes, all splits.".format(
                DS_NAME[ds], truth_l))
            A("")
            A("| delta | gate | costly / cheap / undecided | TPR [95% CI] | FPR [95% CI] |")
            A("|---|---|---|---|---|")
            for delta in DELTAS:
                for g in (CERT, CERTM, "D-REL2", UNION, UNION_M):
                    r = drow(ds, truth_l, "all", "published", g, delta, "all")
                    A("| {:g} | {} | {} / {} / {} | {} | {} |".format(
                        delta, g, r["oracle_costly"], r["oracle_cheap"], r["undecided"],
                        tpr_txt(r, "tpr"), tpr_txt(r, "fpr")))
            A("")
    A("**Marginal truth, every gate at threshold = delta** (the published points compare a "
      "rule at theta = 0.02 with a certificate at tau = 0.20, so this is the like-for-like "
      "reading), all classes.")
    A("")
    A("| dataset | split | delta | gate | costly / cheap | TPR [95% CI] | FPR [95% CI] |")
    A("|---|---|---|---|---|---|---|")
    for ds in ("direct", "e2e"):
        for sp in ("all", "sequencing_only", "field_changing"):
            for delta in DELTAS:
                for g in (CERT, CERTM, "D-REL2", UNION_M):
                    r = drow(ds, "marginal", sp, "at_delta", g, delta, "all")
                    if r is None or not r["rows_in_scope"]:
                        continue
                    A("| {} | {} | {:g} | {} | {} / {} | {} | {} |".format(
                        ds, sp, delta, g, r["oracle_costly"], r["oracle_cheap"],
                        tpr_txt(r, "tpr"), tpr_txt(r, "fpr")))
    A("")
    A("**Marginal truth by split and class, delta = 0.10, published operating points.**")
    A("")
    A("| dataset | split | class | gate | costly / cheap | TPR | FPR |")
    A("|---|---|---|---|---|---|---|")
    for ds in ("direct", "e2e"):
        for sp in ("sequencing_only", "field_changing"):
            for cls in ("benign", "V3", "V4qv", "all"):
                for g in (CERT, CERTM, "D-REL2", UNION_M):
                    r = drow(ds, "marginal", sp, "published", g, 0.10, cls)
                    if r is None or not r["rows_in_scope"]:
                        continue
                    A("| {} | {} | {} | {} | {} / {} | {} | {} |".format(
                        ds, sp, cls, g, r["oracle_costly"], r["oracle_cheap"],
                        "n/a" if r["tpr"] is None else pct(r["tpr"]) + "%",
                        "n/a" if r["fpr"] is None else pct(r["fpr"]) + "%"))
    A("")
    A("## 4. Where each gate wins (`N2_wins.csv`), D-REL2 against the certificate, "
      "published settings, all splits")
    A("")
    for truth_l in LABELS:
        for ds in ("direct", "e2e"):
            A("**{}, {} truth**.".format(DS_NAME[ds], truth_l))
            A("")
            A("| delta | stratum | median reference gap | D-REL2 miss | G-CERT false referral | "
              "G-CERT-M miss | G-CERT-M false referral | union (G-CERT-M or D-REL2) miss | "
              "union false referral |")
            A("|---|---|---|---|---|---|---|---|---|")
            for delta in DELTAS:
                for st in ("all",) + STRATA:
                    r = wrow(ds, truth_l, delta, "D-REL2", st, "all", "all")
                    if r is None:
                        continue
                    A("| {:g} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                        delta, st, interval_text(r["reference_gap_median_lo"],
                                                 r["reference_gap_median_hi"]),
                        rate_txt(r, "rule_miss"), rate_txt(r, "cert_fr"),
                        rate_txt(r, "certm_miss"), rate_txt(r, "certm_fr"),
                        rate_txt(r, "unionm_miss"), rate_txt(r, "unionm_fr")))
            A("")
    A("## 5. Re-labelled quality class (`N2_relabel.csv`)")
    A("")
    A("| group | proposal | delta | covered / items | absolute: costly / cheap / undecided "
      "(share) | marginal: costly / cheap / undecided (share) |")
    A("|---|---|---|---|---|---|")
    for (name, fld) in (("V3", "gold_ops"), ("benign_degrading", "gold_ops"),
                        ("V4qv", "trap_ops"), ("V4qv", "gold_ops"), ("benign_all", "gold_ops")):
        for delta in DELTAS:
            ra, rm = relrow(name, fld, "absolute", delta), relrow(name, fld, "marginal", delta)

            def sh(r):
                return "{} / {} / {} ({})".format(
                    r["oracle_costly"], r["oracle_cheap"], r["undecided"],
                    "n/a" if r["costly_share_decided"] is None
                    else pct(r["costly_share_decided"]) + "%")
            A("| {} | {} | {:g} | {} / {} | {} | {} |".format(
                name, fld, delta, ra["covered"], ra["items"], sh(ra), sh(rm)))
    A("")
    A("## Checks")
    A("")
    A("{} assertions passed. Dispatch: {} new units in {:.1f} s on {} worker(s) pinned to "
      "cores {}; {} recomputed objectives equal the logged ones to 1e-6 bh. Total wall "
      "{:.1f} s.".format(check.n, n_new, wall_units, args.workers,
                         ",".join(map(str, cores)), n_obj_recomp, time.time() - t_start))
    A("")
    (ANALYSIS / "N2_summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # ---------------------------------------------------------------- macros
    if args.macros:
        M = ["% N2 macros, generated {} by code/scripts/n2_pricing.py ({})".format(stamp, VERSION),
             "% {}".format(header[2] if complete else header[3]),
             "% LaTeX control words cannot carry digits, so the n2 prefix is spelled nTwo."]
        if not complete:
            M.insert(0, "% PARTIAL: not every needed bracket is on disk; not for publication")

        def nc(name, val):
            M.append("\\newcommand{\\" + name + "}{" + val + "}")
        nc("nTwoCoverageStatus", status.lower())
        nc("nTwoBracketsPresent", e1dg.group(cov["brackets_needed_present"]))
        nc("nTwoBracketsNeeded", e1dg.group(cov["brackets_needed"]))
        nc("nTwoDirectCovered", e1dg.group(cov["direct_covered"]))
        nc("nTwoDirectRows", e1dg.group(cov["direct_rows"]))
        nc("nTwoEtoeCovered", e1dg.group(cov["e2e_covered"]))
        nc("nTwoEtoeRows", e1dg.group(cov["e2e_rows"]))
        for ds, table, tag in (("direct", pr_d, "Direct"), ("e2e", pr_e, "Etoe")):
            for truth_l, ttag in (("absolute", ""), ("marginal", "Marg")):
                for sp in SPLITS:
                    for g in GATES:
                        r = prow(table, truth_l, sp, g, "all", "all")
                        if r is None or not r["priced"]:
                            continue
                        stem = (tag, ttag, SPLIT_TOKEN[sp] if sp != "all" else "", GATE_TOKEN[g])
                        if r["e_median_lo"] is not None:
                            nc(macro_name(*stem, "MedianError"),
                               interval_text(r["e_median_lo"], r["e_median_hi"]))
                        if r["under_share"] is not None:
                            nc(macro_name(*stem, "UnderShare"), pct(r["under_share"]) + "\\%")
                        if r["over_share"] is not None:
                            nc(macro_name(*stem, "OverShare"), pct(r["over_share"]) + "\\%")
            for cls, ctok in (("benign", "Benign"), ("all", "All")):
                r = crow(ds, "all", cls)
                nc(macro_name(tag, ctok, "CertReferred"), e1dg.group(r["cert_referred"]))
                nc(macro_name(tag, ctok, "CertMReferred"), e1dg.group(r["certm_referred"]))
                nc(macro_name(tag, ctok, "CertMRemoved"), e1dg.group(r["removed_by_marginal"]))
                nc(macro_name(tag, ctok, "CertReferredExplainedByAnchor"),
                   e1dg.group(r["cert_referred_explained_by_anchor"]))
        for st, tok in zip(("all",) + STRATA, ("All", "CNineStorm", "CTenStorm", "CTenReplay")):
            lo, hi = refgap_by_stratum.get(st, (None, None))
            if lo is not None:
                nc(macro_name("RefGap", tok, "Median"),
                   interval_text(100 * lo, 100 * hi, "{:.1f}") + "\\%")
                nc(macro_name("RefGap", tok, "MedianLow"), "{:.1f}\\%".format(100 * lo))
                nc(macro_name("RefGap", tok, "MedianHigh"), "{:.1f}\\%".format(100 * hi))
        for delta in DELTAS:
            dtok = "{:g}".format(delta)
            for truth_l, ttag in (("absolute", ""), ("marginal", "Marg")):
                for name, ntok, fld in (("V3", "VThree", "gold_ops"),
                                        ("benign_degrading", "BenignDegrading", "gold_ops"),
                                        ("V4qv", "VFourVisible", "trap_ops")):
                    r = relrow(name, fld, truth_l, delta)
                    if r["costly_share_decided"] is not None:
                        nc(macro_name(ttag, ntok, "CostlyShare", dtok),
                           pct(r["costly_share_decided"]) + "\\%")
                        nc(macro_name(ttag, ntok, "CostlyCount", dtok), str(r["oracle_costly"]))
                        nc(macro_name(ttag, ntok, "DecidedCount", dtok),
                           str(r["oracle_costly"] + r["oracle_cheap"]))
                        nc(macro_name(ttag, ntok, "UndecidedCount", dtok), str(r["undecided"]))
                for ds, tag in (("direct", "Direct"), ("e2e", "Etoe")):
                    w = wrow(ds, truth_l, delta, "D-REL2", "all", "all", "all")
                    if w is None:
                        continue
                    for name, ntok in (("rule_miss", "RelTwoMissRate"),
                                       ("cert_fr", "CertFalseReferralRate"),
                                       ("certm_miss", "CertMMissRate"),
                                       ("certm_fr", "CertMFalseReferralRate")):
                        if w[name + "_rate"] is not None:
                            nc(macro_name(tag, ttag, ntok, dtok), pct(w[name + "_rate"]) + "\\%")

        # Macros for the oracle section (4.3), the pricing section (5.2) and their
        # supplement tables. Every name above keeps its value; the names below are
        # new and are checked against the ones already written.
        def defined():
            return {ln[len("\\newcommand{\\"):].split("}", 1)[0] for ln in M
                    if ln.startswith("\\newcommand{\\")}
        n_before = len(defined())
        st_tok = OrderedDict(zip(STRATA, ("CNineStorm", "CTenStorm", "CTenReplay")))

        def rate_ci(stem, x, lo, hi):
            nc(macro_name(*stem), pct(x) + "\\%")
            nc(macro_name(*stem, "CiLo"), pct(lo))
            nc(macro_name(*stem, "CiHi"), pct(hi))
            nc(macro_name(*stem, "Ci"), "{} to {}\\%".format(pct(lo), pct(hi)))

        # Largest anchor gap per stratum (N2_reference_gap.csv), as the median above.
        for st, tok in zip(("all",) + STRATA, ("All",) + tuple(st_tok.values())):
            rs = [r for r in refgap_rows if r["covered"] and (st == "all" or r["stratum"] == st)]
            if rs:
                nc(macro_name("RefGap", tok, "Max"),
                   interval_text(100 * max(r["ref_gap_lo"] for r in rs),
                                 100 * max(r["ref_gap_hi"] for r in rs), "{:.1f}") + "\\%")

        for ds, table, tag in (("direct", pr_d, "Direct"), ("e2e", pr_e, "Etoe")):
            for truth_l, ttag in (("absolute", ""), ("marginal", "Marg")):
                # 5th and 95th percentile of the signed error, every gate, all splits.
                for g in GATES:
                    r = prow(table, truth_l, "all", g, "all", "all")
                    if r is None or not r["priced"]:
                        continue
                    nc(macro_name(tag, ttag, GATE_TOKEN[g], "PFiveError"),
                       interval_text(r["e_p05_lo"], r["e_p05_hi"]))
                    nc(macro_name(tag, ttag, GATE_TOKEN[g], "PNinetyFiveError"),
                       interval_text(r["e_p95_lo"], r["e_p95_hi"]))
                # D-REL2 and G-CERT-M by stratum: median error, and the D-REL2
                # under-pricing count over its priced rows in the absolute reading.
                for st, stok in st_tok.items():
                    for g in ("D-REL2", CERTM):
                        r = prow(table, truth_l, "all", g, "stratum", st)
                        if r is None or not r["priced"]:
                            continue
                        stem = (tag, ttag, stok, GATE_TOKEN[g])
                        nc(macro_name(*stem, "MedianError"),
                           interval_text(r["e_median_lo"], r["e_median_hi"]))
                        if truth_l == "absolute" and g == "D-REL2":
                            nc(macro_name(*stem, "UnderCount"), e1dg.group(r["under_n"]))
                            nc(macro_name(*stem, "Priced"), e1dg.group(r["priced"]))
                            if r["under_share"] is not None:
                                nc(macro_name(*stem, "UnderShare"),
                                   pct(r["under_share"]) + "\\%")
            # D-REL2 prices only the rows whose reference dispatch exists.
            r = prow(table, "absolute", "all", "D-REL2", "all", "all")
            rf = prow(table, "absolute", "field_changing", "D-REL2", "all", "all")
            unpriced = r["covered"] - r["priced"]
            if unpriced != rf["covered"] - rf["priced"]:
                refuse("{}: D-REL2 leaves rows unpriced outside the field-changing split"
                       .format(ds))
            nc(macro_name(tag, "RelTwo", "Priced"), e1dg.group(r["priced"]))
            nc(macro_name(tag, "RelTwo", "Covered"), e1dg.group(r["covered"]))
            nc(macro_name(tag, "RelTwo", "Unpriced"), e1dg.group(unpriced))
            # The certificate's referrals of cost-bearing (V3) instructions.
            r = crow(ds, "all", "V3")
            nc(macro_name(tag, "VThree", "CertReferred"), e1dg.group(r["cert_referred"]))
            nc(macro_name(tag, "VThree", "CertMReferred"), e1dg.group(r["certm_referred"]))
            nc(macro_name(tag, "VThree", "CertMRemoved"), e1dg.group(r["removed_by_marginal"]))
            nc(macro_name(tag, "VThree", "CertReferredExplainedByAnchor"),
               e1dg.group(r["cert_referred_explained_by_anchor"]))
            # Every gate at threshold = delta, marginal reading, all classes and splits.
            for g in (CERT, CERTM, "D-REL2"):
                for kind, ktok in (("tpr", "Tpr"), ("fpr", "Fpr")):
                    got = []
                    for delta in DELTAS:
                        r = drow(ds, "marginal", "all", "at_delta", g, delta, "all")
                        if r is None or r[kind] is None:
                            continue
                        rate_ci((tag, "Marg", GATE_TOKEN[g], "AtDelta", ktok,
                                 "{:g}".format(delta)), r[kind], r[kind + "_lo"], r[kind + "_hi"])
                        got.append(r)
                    if g == "D-REL2" and kind == "tpr" and got:
                        r = min(got, key=lambda x: x["tpr"])  # first delta on a tie
                        rate_ci((tag, "Marg", GATE_TOKEN[g], "AtDelta", ktok, "Min"),
                                r["tpr"], r["tpr_lo"], r["tpr_hi"])
            # Decision-table cells (N2_wins.csv): D-REL2, all classes, all splits, by
            # stratum and pooled; pooled names already written above are skipped.
            for delta in DELTAS:
                dtok = "{:g}".format(delta)
                for truth_l, ttag, name, ntok in (
                        ("absolute", "", "rule_miss", "RelTwoMissRate"),
                        ("absolute", "", "cert_miss", "CertMissRate"),
                        ("absolute", "", "certm_miss", "CertMMissRate"),
                        ("marginal", "Marg", "cert_fr", "CertFalseReferralRate"),
                        ("marginal", "Marg", "certm_miss", "CertMMissRate"),
                        ("marginal", "Marg", "unionm_fr", "UnionFalseReferralRate")):
                    for st, stok in (("all", ""),) + tuple(st_tok.items()):
                        w = wrow(ds, truth_l, delta, "D-REL2", st, "all", "all")
                        if w is None or w[name + "_rate"] is None:
                            continue
                        mname = macro_name(tag, ttag, stok, ntok, dtok)
                        if st == "all" and mname in defined():
                            continue
                        nc(mname, pct(w[name + "_rate"]) + "\\%")

        # Oracle brackets over the needed set (the coverage gate's need_br).
        nb = [brackets[k] for k in sorted(need_br) if k in brackets]
        for st, stok in (("all", "Pooled"),) + tuple(st_tok.items()):
            bs = [b for b in nb if st == "all" or strata[b["instance_id"]] == st]
            if not bs:
                continue
            w = [float(b["width_rel"]) for b in bs]
            proved = sum(1 for b in bs if b["proved_all"])
            at_lb2 = sum(1 for b in bs if abs(float(b["lower"]) - float(b["lb2_total"])) <= 1e-9)
            stem = ("Oracle", stok)
            nc(macro_name(*stem, "Brackets"), e1dg.group(len(bs)))
            nc(macro_name(*stem, "Proved"), e1dg.group(proved))
            nc(macro_name(*stem, "ProvedShare"), pct(proved / len(bs)) + "\\%")
            nc(macro_name(*stem, "WidthMedian"), pct(pctl(w, 50), 2) + "\\%")
            nc(macro_name(*stem, "WidthPNinetyFive"), pct(pctl(w, 95), 2) + "\\%")
            nc(macro_name(*stem, "WidthMax"), pct(max(w), 2) + "\\%")
            nc(macro_name(*stem, "LowerAtLBTwo"), e1dg.group(at_lb2))
            # Solver-independent tightness: a feasible schedule (the solver's
            # incumbent or the site's dispatch) attains the analytic bound, so
            # OPT equals LB on that bracket with no solver bound involved.
            up_eq = sum(1 for b in bs
                        if abs(float(b["upper"]) - float(b["lb2_total"]))
                        <= 1e-6 * max(1.0, float(b["upper"])))
            nc(macro_name(*stem, "UpperAtLBTwo"), e1dg.group(up_eq))
            nc(macro_name(*stem, "UpperAtLBTwoShare"), pct(up_eq / len(bs)) + "\\%")
            # The solver's own proved bound on the rounded copy against LB2.
            cp_lt = sum(1 for b in bs
                        if float(b["cp_bound_total_raw"]) < float(b["lb2_total"]) - 1e-6)
            short = [(float(b["lb2_total"]) - float(b["cp_bound_total_raw"]))
                     / max(float(b["lb2_total"]), 1.0) for b in bs]
            nc(macro_name(*stem, "CpBelowLBTwo"), e1dg.group(cp_lt))
            nc(macro_name(*stem, "CpBelowLBTwoShare"), pct(cp_lt / len(bs)) + "\\%")
            nc(macro_name(*stem, "CpShortfallMedian"), pct(pctl(short, 50), 2) + "\\%")
            nc(macro_name(*stem, "CpShortfallPNinetyFive"), pct(pctl(short, 95), 2) + "\\%")
            nc(macro_name(*stem, "CpShortfallMax"), pct(max(short), 2) + "\\%")

        # Costly proposals at each materiality level, by instruction class,
        # read back from the row files written above: the oracle label over
        # every class, so the decision tables do not rest on V3 admission.
        import io as _io
        for ds, fn in (("Direct", "N2_rows_direct.csv"), ("Etoe", "N2_rows_e2e.csv")):
            lines = [ln for ln in (ANALYSIS / fn).read_text(encoding="utf-8").splitlines(True)
                     if not ln.startswith("#")]
            rws = list(csv.DictReader(_io.StringIO("".join(lines))))
            for rtag, col in (("Abs", "g_lo"), ("Marg", "m_lo")):
                for dtok, d in (("Five", 0.05), ("Ten", 0.10), ("Twenty", 0.20)):
                    costly = []
                    for r in rws:
                        try:
                            v = float(r[col])
                        except (TypeError, ValueError):
                            continue
                        if v > d:
                            costly.append(r)
                    non = [r for r in costly if r["primary_class"] != "V3"]
                    stem = ("", ds, rtag, "CostlyAt", dtok)
                    nc(macro_name(*stem), e1dg.group(len(costly)))
                    nc(macro_name(*stem, "NonVThree"), e1dg.group(len(non)))
                    nc(macro_name(*stem, "NonVThreeShare"),
                       (pct(len(non) / len(costly)) if costly else "0.0") + "\\%")
                    nben = sum(1 for r in non if r["primary_class"] == "benign")
                    nc(macro_name(*stem, "Benign"), e1dg.group(nben))
            # The certificate's over-pricing in gap units: price minus the
            # optimistic end of the truth interval (e_hi), largest and 95th pct.
            eh = []
            for r in rws:
                try:
                    eh.append(float(r["e_hi_G-CERT"]))
                except (TypeError, ValueError):
                    pass
            if eh:
                nc(macro_name("", ds, "CertOverpriceMax"), "{:.3f}".format(max(eh)))
                nc(macro_name("", ds, "CertOverpricePNinetyFive"), "{:.3f}".format(pctl(eh, 95)))
            # The tolerance in weighted business hours: tau * max(LB, 1) per row,
            # median by stratum (direct rows only, one per canonical proposal).
            if ds == "Direct":
                bh = {}
                for r in rws:
                    try:
                        lb = float(r["lb_cert"])
                    except (TypeError, ValueError):
                        continue
                    bh.setdefault(r["stratum"], []).append(TAU_PUBLISHED * max(lb, 1.0))
                for st_name, stok in st_tok.items():
                    if st_name in bh:
                        nc(macro_name("TauBh", stok, "Median"), "{:.0f}".format(pctl(bh[st_name], 50)))
                allbh = [v for vs in bh.values() for v in vs]
                if allbh:
                    nc(macro_name("TauBh", "Pooled", "Median"), "{:.0f}".format(pctl(allbh, 50)))

        names = [ln[len("\\newcommand{\\"):].split("}", 1)[0] for ln in M
                 if ln.startswith("\\newcommand{\\")]
        if len(names) != len(set(names)):
            refuse("duplicate macro names: {}".format(
                sorted(n for n, c in Counter(names).items() if c > 1)))
        print("[n2] macros: {} before the oracle and pricing additions, {} after".format(
            n_before, len(names)))
        (ANALYSIS / "N2_macros.tex").write_text("\n".join(M) + "\n", encoding="utf-8")

    print("[n2] {}: wrote N2_* to {} ({} assertions, {:.1f} s)".format(
        status, ANALYSIS, check.n, time.time() - t_start))
    print("[n2] certificate vs oracle files:", json.dumps(mism, default=str))
    print("[n2] soundness:", json.dumps(sound))
    print("[n2] DG17 reproduction: {} of {} exact; mismatches: {}".format(
        n_dg17_exact, len(dg17_repro), [x for x in dg17_repro if x[3] != x[4]][:10]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
