#!/usr/bin/env python3
"""N20: the headline comparison by stratum and on absolute cost levels, from the logs only.

Design pre-specified before the run.  Blocks:

  0  the published headline of the direct benchmark at delta = tau = 0.20, reproduced from the
     rows n16/n18 use and asserted (the run aborts on any mismatch before a new number);
  A  the headline per stratum (Primary, Confirmation, Buildings; the names of Table
     tab:strata) at delta 0.20 and 0.10, with the no-AI weighted tardiness of each stratum and
     the realised-cost denominator max(OPT_full,base, 1 bh) that turns a cost level into bh;
  B  absolute cost levels: costly = realised damage in weighted bh above X, X in 5, 10, 25, 50,
     100, with the gate unchanged (tau = 0.20), pooled and per stratum;
  C  the resolution of the headline comparison: instances and instructions that carry a costly
     proposal, the exact one-sided 95% (Clopper-Pearson) upper bound on the share whose costly
     disposition differs between the two readings, and the instance-level sign-flip
     permutation test of Section 4.6.2 (e3_intervals.signflip_exact_p, enumerated exactly);
  D  low-cost referral shares over the low-cost proposals that carry an operation, with the
     cluster-bootstrap 95% interval the other shares use;
  E  the floor: priced proposals whose bound is zero and those on which the floor of 1
     weighted bh binds, on the known board and with full information;
  F  a file inspection only: do the stored logs hold per-order completion times of the
     executed schedules?
  G  (version 2) the hand-written rule D-REL2 with the second price against the site's own
     schedule (n16 block I's s2_site, applied to field edits at tau = 0.20), on the known
     board at delta 0.20 and 0.10, with D-REL2 at its own threshold 0.02 and at the equal
     threshold 0.20: costly applied, low-cost referred, benign among them, and the low-cost
     referral share with its cluster-bootstrap interval; the bound-referenced second price
     is computed alongside for comparison (summary only).

THE FOUR LAUNCH ANSWERS
  1. Purpose: backing numbers for the stratum, absolute-level and resolution statements of the
     direct benchmark (Sections 5 and 6 and the supplement); every number goes to
     analysis/N20_macros.tex and analysis/N20_summary.md.
  2. Ideal result: block 0 reproduces exactly (run-fatal); the new numbers are whatever the
     logs give.
  3. Contamination: read-only on every input (hashes recorded); deterministic; no timing.
  4. Data accuracy: the inputs are the files n13/n16/n18 read (the same loaders are reused),
     and the published headline is asserted before any new number.

Every number comes from result files on disk: no solve, no model call, no GPU.  The script
loads code/scripts/n16_robustness.py and code/scripts/n18_further_checks.py from their source
with the core allowance set to cores 10-11 in memory (each constant asserted to occur the
expected number of times; the files on disk are untouched), and n16 loads n13_fromlogs.py the
same way.  It reuses their loaders (n13.load_inputs, n16.build_recs, n13.j_records,
n13.section_f), labels (n13.costly_of, n13.refers, n16.sp_flag) and cluster bootstrap
(n2.Boot via n13: seed 20261026, 20,000 replicates, 60 instance clusters).

Outputs: analysis/N20_macros.tex (prefix \\nTwenty, copied to manuscript/macros_n20.tex),
analysis/N20_summary.md, analysis/N20_rows.csv (one row per priced proposal).
Run:       OMP_NUM_THREADS=1 taskset -c 10-11 python3 code/scripts/n20_stratum_abs.py
Self-test: OMP_NUM_THREADS=1 taskset -c 10-11 python3 code/scripts/n20_stratum_abs.py --selftest
           (recomputes three numbers per block by a second code path that reads the CSV and
           JSONL files directly, compares, and writes nothing; the default run performs the
           same comparisons and records them in the summary).
Version: l1-n20-stratum-2
"""
import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_v] = "1"

import csv  # noqa: E402
import json  # noqa: E402
import shutil  # noqa: E402
import statistics  # noqa: E402
import sys  # noqa: E402
import types  # noqa: E402
from collections import Counter, OrderedDict  # noqa: E402
from itertools import product  # noqa: E402
from pathlib import Path  # noqa: E402

ALLOWED_CORES = {10, 11}
_aff = set(os.sched_getaffinity(0))
if not _aff <= ALLOWED_CORES and not os.environ.get("CERTIGATE_ANY_CORES"):
    raise SystemExit("REFUSING TO RUN: affinity {} is not inside cores 10-11 "
                     "(run under taskset -c 10-11)".format(sorted(_aff)))

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _load_module(name, swaps):
    """A frozen script loaded from its source with its core allowance replaced in memory."""
    path = SCRIPTS_DIR / (name + ".py")
    src = path.read_text(encoding="utf-8")
    for old, new, count in swaps:
        if src.count(old) != count:
            raise SystemExit("{}: '{}' found {} times, expected {}".format(
                path.name, old, src.count(old), count))
        src = src.replace(old, new)
    mod = types.ModuleType(name)
    mod.__file__ = str(path)
    sys.modules[name] = mod
    exec(compile(src, str(path), "exec"), mod.__dict__)  # noqa: S102
    return mod


# n16 holds its own guard and the string it writes into n13's source: both move to {10, 11}.
n16 = _load_module("n16_robustness", [("ALLOWED_CORES = {14, 15}", "ALLOWED_CORES = {10, 11}", 2)])
n18 = _load_module("n18_further_checks",
                   [("ALLOWED_CORES = {14, 15}", "ALLOWED_CORES = {10, 11}", 1)])
n13 = n16.n13
np = n13.np
D = n13.D
import e3_intervals as e3i  # noqa: E402  (the sign-flip test of Section 4.6.2; numpy only)
from scipy import stats as sstats  # noqa: E402

VERSION = "l1-n20-stratum-2"
ROOT = n13.ROOT
ANALYSIS = n13.ANALYSIS
RESULTS = n13.RESULTS
OUT_TEX = ANALYSIS / "N20_macros.tex"
OUT_MANU = ROOT / "manuscript" / "macros_n20.tex"
OUT_MD = ANALYSIS / "N20_summary.md"
OUT_CSV = ANALYSIS / "N20_rows.csv"
IN20 = OrderedDict([
    ("n15_macros", ANALYSIS / "N15_macros.tex"),
    ("n16_macros", ANALYSIS / "N16_macros.tex"),
    ("n13_macros", ANALYSIS / "N13_macros.tex"),
    ("n18_macros", ANALYSIS / "N18_macros.tex"),
    ("suite_macros", ROOT / "manuscript" / "macros.tex"),
    ("strata_table", ROOT / "manuscript" / "drafts" / "s4_instrument.tex"),
    ("stats_section", ROOT / "manuscript" / "drafts" / "s5_setup.tex"),
    ("e3_intervals", SCRIPTS_DIR / "e3_intervals.py"),
])

#: Inputs the public release does not carry (two manuscript drafts). A missing one
#: is recorded as "not shipped" in the provenance block, and the run goes on.
NOT_SHIPPED_OK = ('strata_table', 'stats_section')


def input_sha256(key, path):
    """The SHA-256 of an input, or "not shipped" for one the public release does not carry."""
    if key in NOT_SHIPPED_OK and not Path(path).is_file():
        return "not shipped"
    return n13.sha256(path)

TAU = n13.TAU
FLOOR = D.FLOOR_BH
CERT = "G-CERT"
DELTAS = OrderedDict([("DeltaTwenty", 0.20), ("DeltaTen", 0.10)])
LEVELS = OrderedDict([("XFive", 5.0), ("XTen", 10.0), ("XTwentyFive", 25.0),
                      ("XFifty", 50.0), ("XHundred", 100.0)])
ST_TOK = n13.ST_TOK                        # stratum code -> Primary / Confirmation / Buildings
POPS = OrderedDict([("Pooled", None)] + [(ST_TOK[s], s) for s in D.STRATA])
POP_NAME = {"Pooled": "pooled", "Primary": "Primary stratum",
            "Confirmation": "Confirmation stratum", "Buildings": "Buildings stratum"}
SUITE_INST = {"Primary": "nSuiteStratumPrimaryInstances",
              "Confirmation": "nSuiteStratumConfirmationInstances",
              "Buildings": "nSuiteStratumBuildingsInstances"}
ALPHA_ONE_SIDED = 0.05

LINES = ["% N20 macros ({}); generated by code/scripts/n20_stratum_abs.py from the logged "
         "results only (no solve, no model call); each macro follows a comment line giving "
         "its block and definition".format(VERSION)]
NAMES = set()
VAL = OrderedDict()
MD = []
NCHECK = [0]
SELF = []                                   # (block, what, main value, second-path value)

grp, pct, pctv, pctp, pctpv, ppv, frac = (n16.grp, n16.pct, n16.pctv, n16.pctp, n16.pctpv,
                                          n16.ppv, n16.frac)


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def check(what, ok, detail=""):
    if not ok:
        raise SystemExit("[n20] ASSERTION FAILED: {} ({})".format(what, detail))
    NCHECK[0] += 1


def add(name, value, note):
    full = "nTwenty" + name
    if not full.isalpha():
        raise SystemExit("macro name not alphabetic: " + full)
    if full in NAMES:
        raise SystemExit("duplicate macro " + full)
    NAMES.add(full)
    VAL[full] = str(value)
    LINES.append("% " + note)
    LINES.append("\\newcommand{\\" + full + "}{" + str(value) + "}")


def md(*lines):
    MD.extend(lines)


def md_table(head, body):
    MD.append("| " + " | ".join(str(h) for h in head) + " |")
    MD.append("|" + "|".join("---" for _ in head) + "|")
    for row in body:
        MD.append("| " + " | ".join("" if c is None else str(c) for c in row) + " |")
    MD.append("")


def bh1(x):
    return "n/a" if x is None else "{:.1f}".format(x)


def bhm(x):
    """bh with one decimal for a macro, thousands grouped as the other macro files."""
    return "n/a" if x is None else "{:,.1f}".format(x).replace(",", "{,}")


def pfmt(p):
    """p-value text: two decimals at or above 0.01, two significant digits below."""
    if p is None or p != p:
        return "n/a"
    return "{:.2f}".format(p) if p >= 0.01 else "{:.2g}".format(p)


def sgn(x):
    v = int(round(x))
    return "0" if v == 0 else "{:+d}".format(v)


def ci_str(k, n, lo, hi):
    return "{} [{}, {}]".format(frac(k, n), pctpv(lo), pctpv(hi))


def cp_upper(k, n, alpha=ALPHA_ONE_SIDED):
    """Exact one-sided (1 - alpha) Clopper-Pearson upper bound on a binomial share."""
    if n == 0:
        return None
    if k >= n:
        return 1.0
    return float(sstats.beta.ppf(1.0 - alpha, k + 1, n - k))


def macros_of(path):
    return n13.macros_of(path)


# --------------------------------------------------------------------------- #
# Records                                                                      #
# --------------------------------------------------------------------------- #
def build(items_dt, fc, boot):
    """The 1,356 priced proposals with both readings, both prices, damage and denominators."""
    recs, by = n16.build_recs(items_dt, fc)
    jrec, k_sp = n13.j_records(fc, items_dt)
    spfi = {r["item_id"]: r["sp"] for r in jrec["FI"]}
    for r in recs:
        check("K second price equals n13 section J's", abs(k_sp[r["item_id"]] - r["g_orig"])
              < 1e-12, r["item_id"])
    site = {}
    for x in n13.read_csv(n13.IN["rows_direct"]):
        if x["dataset"] == "direct_td" and x["item_id"] in by and x["priced"] == "True":
            site[x["item_id"]] = n16.site_price(float(x["obj_orig"]), float(x["ref1"]))
    check("s2_site on every priced proposal", set(site) >= {r["item_id"] for r in recs})
    frecs = n13.section_f(boot, fc, items_dt)
    fby = {r["item_id"]: r for r in frecs}
    check("common-denominator records cover the 1,356", set(fby) == {r["item_id"] for r in recs})
    anchors = D.load_anchor_records()
    for r in recs:
        it = by[r["item_id"]]
        f = fby[r["item_id"]]
        a = anchors[(it["instance_id"], it["frozen_seed"])]
        check("no-AI anchor of the row equals rule_anchor wwt_original_bh",
              abs(float(a["wwt_original_bh"]) - it["pub_anchor_wwt"]) < 1e-9, r["item_id"])
        check("damage logged on every priced proposal", r["dmg"] is not None, r["item_id"])
        check("damage = executed original-field objective minus the no-AI anchor",
              abs(r["dmg"] - (it["rw_obj_orig"] - it["pub_anchor_wwt"])) < 1e-6, r["item_id"])
        check("edit type empty iff no operation", (r["split"] == "empty") == (it["n_ops"] == 0),
              r["item_id"])
        field = r["split"] == "field_changing"
        ref_k = n13.refers(r, CERT)
        ref_f = n13.refers(r["fi"], CERT)
        r.update(st=ST_TOK[r["stratum"]], field=field, ref_k=ref_k, ref_f=ref_f,
                 two_k=n16.sp_flag(r, CERT), two_f=ref_f or (field and spfi[r["item_id"]] > TAU),
                 sp_fi=spfi[r["item_id"]], den=f["den"], c_bh_k=f["c_bh_k"], c_bh_f=f["c_bh_f"],
                 lb_k=f["lb_k"], lb_f=f["lb_f"], anchor=it["pub_anchor_wwt"],
                 frozen_seed=it["frozen_seed"], n_ops=it["n_ops"])
        check("two_k = ref_k or (field and g_orig > tau)",
              r["two_k"] == (ref_k or (field and r["g_orig"] > TAU)), r["item_id"])
        check("lb_k is the logged known-board bound", f["lb_k"] == it["dt_lb"], r["item_id"])
    return recs, by, spfi, site, frecs


# --------------------------------------------------------------------------- #
# 0. The published headline                                                    #
# --------------------------------------------------------------------------- #
def section0(recs):
    m15 = macros_of(IN20["n15_macros"])
    m16 = macros_of(IN20["n16_macros"])
    check("1,356 priced proposals", len(recs) == 1356 and m15["nFifteenPriced"] == "1{,}356",
          len(recs))
    c20 = [r for r in recs if n13.costly_of(r, 0.20) == 1]
    l20 = [r for r in recs if n13.costly_of(r, 0.20) == 0]
    check("186 costly and 1,170 low-cost at delta 0.20", (len(c20), len(l20)) == (186, 1170)
          and m15["nFifteenCostlyTwenty"] == "186" and m15["nFifteenLowTwenty"] == "1{,}170",
          (len(c20), len(l20)))
    rk = {r["item_id"] for r in c20 if r["ref_k"]}
    rf = {r["item_id"] for r in c20 if r["ref_f"]}
    check("certificate refers 168 costly on the known board and the same 168 with FI",
          len(rk) == 168 and rk == rf and m16["nSixteenCertRefKTwenty"] == "168"
          and m16["nSixteenCertRefFITwenty"] == "168"
          and m16["nSixteenCertRefBothTwenty"] == "168", (len(rk), len(rf)))
    applied = [r for r in c20 if not r["ref_k"]]
    check("18 costly applied", len(applied) == 18 and m15["nFifteenCertMissTwenty"] == "18",
          len(applied))
    check("the second price refers 18 of the 18 applied (known board)",
          sum(1 for r in applied if r["field"] and r["sp"]) == 18
          and all(r["two_k"] for r in applied) and m15["nFifteenCertTwoMissTwenty"] == "0")
    fr = sum(1 for r in l20 if r["ref_k"])
    fr2 = sum(1 for r in l20 if r["two_k"])
    check("low-cost referred 15 by the certificate, then 22 with the second price",
          (fr, fr2) == (15, 22) and m15["nFifteenCertFrTwenty"] == "15"
          and m15["nFifteenCertTwoFrTwenty"] == "22", (fr, fr2))
    cd = {}
    for dtok, delta in DELTAS.items():
        cst = [r for r in recs if n13.costly_of(r, delta) == 1]
        k = sum(1 for r in cst if not r["c_bh_k"] / r["den"] > TAU)
        f = sum(1 for r in cst if not r["c_bh_f"] / r["den"] > TAU)
        cd[delta] = (k, f)
        t = "Twenty" if delta == 0.20 else "Ten"
        check("common denominator applied at delta {}: N16 block C".format(delta),
              (str(k), str(f)) == (m16["nSixteenCommonCertMissK" + t],
                                   m16["nSixteenCommonCertMissFI" + t]), (k, f))
    check("common denominator 20 against 18 at 0.20 and 40 against 35 at 0.10",
          cd[0.20] == (20, 18) and cd[0.10] == (40, 35), cd)
    md("## 0. The published headline, asserted before any new number", "",
       "Direct benchmark at the decision instant, delta = tau = 0.20, from the rows n16/n18 use "
       "(analysis/N11_rows_forecast.csv readings K and FI, results/n11_decision_time/items.jsonl, "
       "n13.section_f's common-denominator records): 1,356 priced proposals, 186 costly and "
       "1,170 low-cost; the certificate refers 168 costly proposals on the known board and the "
       "same 168 with full information and applies 18; the second price refers all 18; it "
       "refers 15 low-cost proposals, 22 with the second price; on the common denominator it "
       "applies 20 on the known board against 18 with full information (40 against 35 at "
       "delta = 0.10). Each count equals the N15/N16 macro (asserted). n16.section0 and "
       "n18.section0 are re-run on the same records and pass.", "")
    return c20, l20, applied


# --------------------------------------------------------------------------- #
# The shared tally                                                             #
# --------------------------------------------------------------------------- #
FIELDS = OrderedDict([
    ("priced", ("Priced", "priced proposals")),
    ("instances", ("Instances", "instances with a priced proposal")),
    ("costly", ("Costly", "costly proposals")),
    ("low", ("Low", "low-cost proposals")),
    ("und", ("Undecided", "proposals whose realised-cost bracket straddles the level")),
    ("costly_inst", ("CostlyInstances", "instances that carry a costly proposal")),
    ("ref_k", ("CostlyRefK", "costly proposals the certificate refers on the known board")),
    ("ref_f", ("CostlyRefFI", "costly proposals the certificate refers with full information")),
    ("ref_both", ("CostlyRefBoth", "costly proposals referred under both readings")),
    ("app_k", ("AppK", "costly proposals the certificate applies on the known board")),
    ("app_f", ("AppFI", "costly proposals the certificate applies with full information")),
    ("app_both", ("AppBoth", "costly proposals applied under both readings")),
    ("app_k_field", ("AppKField", "field edits among the costly proposals applied on the "
                                  "known board")),
    ("app_f_field", ("AppFIField", "field edits among the costly proposals applied with full "
                                   "information")),
    ("two_app_k", ("TwoAppK", "costly proposals applied on the known board with the second "
                              "price added on field edits")),
    ("two_app_f", ("TwoAppFI", "costly proposals applied with full information with the second "
                               "price added on field edits")),
    ("two_app_k_field", ("TwoAppKField", "field edits among the costly proposals applied with "
                                         "the second price, known board")),
    ("two_app_f_field", ("TwoAppFIField", "field edits among the costly proposals applied with "
                                          "the second price, full information")),
    ("low_ref_k", ("LowRefK", "low-cost proposals the certificate refers on the known board")),
    ("low_ref_f", ("LowRefFI", "low-cost proposals the certificate refers with full "
                               "information")),
    ("low_two_k", ("LowTwoRefK", "low-cost proposals referred on the known board with the "
                                 "second price")),
    ("low_two_f", ("LowTwoRefFI", "low-cost proposals referred with full information with the "
                                  "second price")),
    ("dis", ("Disagree", "priced proposals on which the certificate's disposition differs "
                         "between the known board and full information")),
    ("dis_costly", ("DisagreeCostly", "costly proposals whose disposition differs between the "
                                      "two readings")),
    ("dis_low", ("DisagreeLow", "low-cost proposals whose disposition differs between the two "
                                "readings")),
    ("dis_costly_inst", ("DisagreeCostlyInstances", "instances that carry a costly proposal "
                                                    "whose disposition differs")),
])


def tally(sel, label):
    """Counts of one population under one costly label (1 costly, 0 low-cost, None neither)."""
    costly = [r for r in sel if label(r) == 1]
    low = [r for r in sel if label(r) == 0]
    o = OrderedDict()
    o["priced"] = len(sel)
    o["instances"] = len({r["instance_id"] for r in sel})
    o["costly"] = len(costly)
    o["low"] = len(low)
    o["und"] = len(sel) - len(costly) - len(low)
    o["costly_inst"] = len({r["instance_id"] for r in costly})
    o["ref_k"] = sum(1 for r in costly if r["ref_k"])
    o["ref_f"] = sum(1 for r in costly if r["ref_f"])
    o["ref_both"] = sum(1 for r in costly if r["ref_k"] and r["ref_f"])
    o["app_k"] = sum(1 for r in costly if not r["ref_k"])
    o["app_f"] = sum(1 for r in costly if not r["ref_f"])
    o["app_both"] = sum(1 for r in costly if not r["ref_k"] and not r["ref_f"])
    o["app_k_field"] = sum(1 for r in costly if not r["ref_k"] and r["field"])
    o["app_f_field"] = sum(1 for r in costly if not r["ref_f"] and r["field"])
    o["two_app_k"] = sum(1 for r in costly if not r["two_k"])
    o["two_app_f"] = sum(1 for r in costly if not r["two_f"])
    o["two_app_k_field"] = sum(1 for r in costly if not r["two_k"] and r["field"])
    o["two_app_f_field"] = sum(1 for r in costly if not r["two_f"] and r["field"])
    o["low_ref_k"] = sum(1 for r in low if r["ref_k"])
    o["low_ref_f"] = sum(1 for r in low if r["ref_f"])
    o["low_two_k"] = sum(1 for r in low if r["two_k"])
    o["low_two_f"] = sum(1 for r in low if r["two_f"])
    o["dis"] = sum(1 for r in sel if r["ref_k"] != r["ref_f"])
    o["dis_costly"] = sum(1 for r in costly if r["ref_k"] != r["ref_f"])
    o["dis_low"] = sum(1 for r in low if r["ref_k"] != r["ref_f"])
    o["dis_costly_inst"] = len({r["instance_id"] for r in costly if r["ref_k"] != r["ref_f"]})
    # internal consistency
    check("costly = referred + applied (K, FI)", o["ref_k"] + o["app_k"] == o["costly"]
          and o["ref_f"] + o["app_f"] == o["costly"])
    check("the second price only adds referrals", o["two_app_k"] <= o["app_k"]
          and o["two_app_f"] <= o["app_f"] and o["low_two_k"] >= o["low_ref_k"]
          and o["low_two_f"] >= o["low_ref_f"])
    check("disagreements partition", o["dis_costly"] + o["dis_low"] <= o["dis"]
          and (o["und"] > 0 or o["dis_costly"] + o["dis_low"] == o["dis"]))
    check("discordant costly = K-only + FI-only applied",
          o["dis_costly"] == (o["app_k"] - o["app_both"]) + (o["app_f"] - o["app_both"]))
    return o, costly, low


def additive(res, keys_fn, what):
    """Every count of the three strata sums to the pooled count (instances included)."""
    for key in keys_fn:
        pooled = res[("Pooled",) + key]
        for f in FIELDS:
            s = sum(res[(p,) + key][f] for p in POPS if p != "Pooled")
            check("strata sum to pooled: {} {} {}".format(what, key, f), s == pooled[f],
                  (key, f, s, pooled[f]))


# --------------------------------------------------------------------------- #
# A. Per stratum                                                               #
# --------------------------------------------------------------------------- #
def block_a(recs):
    msuite = macros_of(IN20["suite_macros"])
    # The strata table of the manuscript is checked when its draft is present; the
    # public release does not carry the drafts.
    strata_src = IN20["strata_table"].read_text(encoding="utf-8") \
        if IN20["strata_table"].is_file() else None
    for p in POPS:
        if p != "Pooled" and strata_src is not None:
            check("stratum name {} appears in Table tab:strata".format(p),
                  "\n{}".format(p) in strata_src and p == D.STRATUM_NAME[POPS[p]])
    res = OrderedDict()
    for (p, st), (dtok, delta) in product(POPS.items(), DELTAS.items()):
        sel = [r for r in recs if st is None or r["stratum"] == st]
        o, _c, _l = tally(sel, lambda r, d=delta: n13.costly_of(r, d))
        res[(p, dtok)] = o
    additive(res, [(d,) for d in DELTAS], "A")
    # the pooled rows are the published cells (N18 block A, N16 block A)
    o = res[("Pooled", "DeltaTwenty")]
    check("pooled 0.20 row equals the headline",
          [o[k] for k in ("priced", "instances", "costly", "low", "und", "costly_inst", "ref_k",
                          "ref_f", "ref_both", "app_k", "app_f", "two_app_k", "two_app_f",
                          "low_ref_k", "low_ref_f", "low_two_k", "low_two_f", "dis",
                          "dis_costly", "dis_low")]
          == [1356, 60, 186, 1170, 0, 50, 168, 168, 168, 18, 18, 0, 0, 15, 35, 22, 39, 30, 0,
              30], o)
    o = res[("Pooled", "DeltaTen")]
    check("pooled 0.10 row equals N18 block A and N16 block A",
          [o[k] for k in ("costly", "low", "costly_inst", "ref_k", "ref_f", "ref_both", "app_k",
                          "app_f", "two_app_k", "two_app_f", "low_ref_k", "low_ref_f",
                          "low_two_k", "low_two_f", "dis_costly")]
          == [208, 1148, 54, 183, 180, 178, 25, 28, 6, 10, 0, 23, 6, 27, 7], o)
    for p in POPS:
        if p != "Pooled":
            n_suite = int(msuite[SUITE_INST[p]])
            check("{}: instances with a priced proposal = Table tab:strata instances".format(p),
                  res[(p, "DeltaTwenty")]["instances"] == n_suite,
                  (res[(p, "DeltaTwenty")]["instances"], n_suite))
    # descriptives: no-AI weighted tardiness and the realised-cost denominator
    desc = OrderedDict()
    for p, st in POPS.items():
        sel = [r for r in recs if st is None or r["stratum"] == st]
        anc = {(r["instance_id"], r["frozen_seed"]): r["anchor"] for r in sel}
        den_i = {}
        for r in sel:
            if r["instance_id"] in den_i:
                check("one denominator per instance", den_i[r["instance_id"]] == r["den"])
            den_i[r["instance_id"]] = r["den"]
        di = list(den_i.values())
        dp = [r["den"] for r in sel]
        ap = [r["anchor"] for r in sel]
        av = list(anc.values())
        c20 = [r["dmg"] for r in sel if n13.costly_of(r, 0.20) == 1]
        floor_inst = {i for i, v in den_i.items() if v <= FLOOR}
        desc[p] = OrderedDict(
            den_floor=len(floor_inst),
            den_floor_costly=sum(1 for r in sel if r["instance_id"] in floor_inst
                                 and n13.costly_of(r, 0.20) == 1),
            den_floor_priced=sum(1 for r in sel if r["instance_id"] in floor_inst),
            den_min=min(di), den_max=max(di),
            noai_mean=statistics.fmean(ap), noai_median=statistics.median(ap),
            n_anchor=len(av), anchor_mean=statistics.fmean(av),
            anchor_median=statistics.median(av),
            den_n=len(di), den_mean_i=statistics.fmean(di), den_median_i=statistics.median(di),
            den_mean_p=statistics.fmean(dp), den_median_p=statistics.median(dp),
            lvl20_i=0.20 * statistics.fmean(di), lvl10_i=0.10 * statistics.fmean(di),
            lvl20_p=0.20 * statistics.fmean(dp), lvl10_p=0.10 * statistics.fmean(dp),
            dmg_costly_min=min(c20) if c20 else None,
            dmg_costly_median=statistics.median(c20) if c20 else None)
    # macros
    for (p, dtok), o in res.items():
        dl = DELTAS[dtok]
        for f, (tok, txt) in FIELDS.items():
            add("A" + p + dtok + tok, grp(o[f]),
                "[A] {}, delta = {:.2f}, tau = 0.20: {}".format(POP_NAME[p], dl, txt))
        add("A" + p + dtok + "AppKShare", pct(o["app_k"], o["costly"]),
            "[A] {}, delta = {:.2f}: costly proposals applied on the known board as a share of "
            "the costly proposals".format(POP_NAME[p], dl))
        add("A" + p + dtok + "AppFIShare", pct(o["app_f"], o["costly"]),
            "[A] {}, delta = {:.2f}: costly proposals applied with full information as a share "
            "of the costly proposals".format(POP_NAME[p], dl))
    for p, d in desc.items():
        pn = POP_NAME[p]
        add("A" + p + "NoAIMean", bhm(d["noai_mean"]),
            "[A] {}: mean weighted tardiness of the no-AI schedule (rule_anchor wwt_original_bh, "
            "site's dispatching rule over the whole window, original values) over the priced "
            "proposals, weighted bh".format(pn))
        add("A" + p + "NoAIMedian", bhm(d["noai_median"]),
            "[A] {}: median of the same over the priced proposals, weighted bh".format(pn))
        add("A" + p + "NoAIAnchors", d["n_anchor"],
            "[A] {}: distinct no-AI anchors (instance x frozen seed) behind the priced "
            "proposals".format(pn))
        add("A" + p + "NoAIAnchorMean", bhm(d["anchor_mean"]),
            "[A] {}: mean no-AI weighted tardiness over the distinct anchors, weighted "
            "bh".format(pn))
        add("A" + p + "NoAIAnchorMedian", bhm(d["anchor_median"]),
            "[A] {}: median no-AI weighted tardiness over the distinct anchors, weighted "
            "bh".format(pn))
        add("A" + p + "DenMean", bhm(d["den_mean_i"]),
            "[A] {}: mean over instances of the realised-cost denominator max(OPT_full,base, "
            "1 bh), the midpoint of the full-window oracle bracket of the untouched window, "
            "weighted bh".format(pn))
        add("A" + p + "DenMedian", bhm(d["den_median_i"]),
            "[A] {}: median over instances of the same denominator, weighted bh".format(pn))
        add("A" + p + "DenMeanPriced", bhm(d["den_mean_p"]),
            "[A] {}: mean of the same denominator over the priced proposals, weighted "
            "bh".format(pn))
        add("A" + p + "DenMedianPriced", bhm(d["den_median_p"]),
            "[A] {}: median of the same denominator over the priced proposals, weighted "
            "bh".format(pn))
        add("A" + p + "LevelTwentyBh", bhm(d["lvl20_i"]),
            "[A] {}: the cost level 0.20 in weighted bh, 0.20 times the mean denominator over "
            "instances".format(pn))
        add("A" + p + "LevelTenBh", bhm(d["lvl10_i"]),
            "[A] {}: the cost level 0.10 in weighted bh, 0.10 times the mean denominator over "
            "instances".format(pn))
        add("A" + p + "LevelTwentyBhPriced", bhm(d["lvl20_p"]),
            "[A] {}: 0.20 times the mean denominator over the priced proposals, weighted "
            "bh".format(pn))
        add("A" + p + "DenFloorInstances", d["den_floor"],
            "[A] {}: instances whose realised-cost denominator sits at the floor of 1 weighted "
            "bh (full-window optimum of the untouched window below 1 bh)".format(pn))
        add("A" + p + "DenFloorPriced", grp(d["den_floor_priced"]),
            "[A] {}: priced proposals on those instances".format(pn))
        add("A" + p + "DenFloorCostlyTwenty", d["den_floor_costly"],
            "[A] {}: proposals costly at delta = 0.20 on those instances".format(pn))
        add("A" + p + "DenMin", bhm(d["den_min"]),
            "[A] {}: smallest realised-cost denominator over instances, weighted bh".format(pn))
        add("A" + p + "DenMax", bhm(d["den_max"]),
            "[A] {}: largest realised-cost denominator over instances, weighted bh".format(pn))
        add("A" + p + "CostlyDamageMin", bhm(d["dmg_costly_min"]),
            "[A] {}: smallest realised damage among the proposals costly at delta = 0.20, "
            "weighted bh".format(pn))
        add("A" + p + "CostlyDamageMedian", bhm(d["dmg_costly_median"]),
            "[A] {}: median realised damage among the proposals costly at delta = 0.20, "
            "weighted bh".format(pn))
    # summary
    md("## A. The headline per stratum", "",
       "Strata as in Table tab:strata (Primary = C9 constructed, Confirmation = C10 constructed, "
       "Buildings = C10 recorded). Costly at delta = realised cost on the original values above "
       "delta (lower end of the bracket); low-cost = upper end at most delta. The certificate "
       "refers when its price exceeds tau = 0.20 (the logged flag). Second price = the "
       "certificate plus g_orig > 0.20 on field edits (known board: the known board's anchor "
       "bound; full information: that board's own anchor bound, n13.j_records). Disagree = the "
       "certificate's disposition differs between the known board (K) and full information "
       "(FI). Each stratum's counts sum to the pooled count (asserted).", "")
    head = ["population", "instances", "priced", "costly", "low-cost", "instances (costly)",
            "costly referred K", "FI", "both", "applied K", "applied FI",
            "applied, second price K", "FI", "low-cost referred K", "FI",
            "low-cost referred, second price K", "FI", "disagree (all)", "disagree (costly)"]
    for dtok, delta in DELTAS.items():
        md("### delta = {:.2f}".format(delta), "")
        body = []
        for p in POPS:
            o = res[(p, dtok)]
            body.append([p, o["instances"], o["priced"], o["costly"], o["low"],
                         o["costly_inst"], o["ref_k"], o["ref_f"], o["ref_both"],
                         "{} ({})".format(o["app_k"], pctp(o["app_k"], o["costly"])),
                         "{} ({})".format(o["app_f"], pctp(o["app_f"], o["costly"])),
                         o["two_app_k"], o["two_app_f"], o["low_ref_k"], o["low_ref_f"],
                         o["low_two_k"], o["low_two_f"], o["dis"], o["dis_costly"]])
        md_table(head, body)
    md("### What the levels mean in weighted bh, per stratum", "",
       "No-AI = the weighted tardiness of the no-AI schedule (the site's dispatching rule over "
       "the whole window, scored on the original values; analysis/ladder/rule_anchor.json "
       "wwt_original_bh), the anchor from which each proposal's damage is measured. Denominator "
       "= max(OPT_full,base, 1 bh), the midpoint of the full-window oracle bracket of the "
       "untouched window (n13.section_f), by which the realised damage is divided to give the "
       "realised cost. Cost level in bh = level times the mean denominator over instances.", "")
    body = []
    for p, d in desc.items():
        body.append([p, "{} / {}".format(bh1(d["noai_mean"]), bh1(d["noai_median"])),
                     "{} ({} anchors) / {}".format(bh1(d["anchor_mean"]), d["n_anchor"],
                                                   bh1(d["anchor_median"])),
                     "{} / {} ({} instances)".format(bh1(d["den_mean_i"]),
                                                     bh1(d["den_median_i"]), d["den_n"]),
                     "{} / {}".format(bh1(d["den_mean_p"]), bh1(d["den_median_p"])),
                     bh1(d["lvl20_i"]), bh1(d["lvl10_i"]), bh1(d["lvl20_p"]),
                     "{} / {}".format(bh1(d["dmg_costly_min"]), bh1(d["dmg_costly_median"])),
                     "{} to {}".format(bh1(d["den_min"]), bh1(d["den_max"])),
                     "{} ({} priced, {} costly at 0.20)".format(d["den_floor"],
                                                               d["den_floor_priced"],
                                                               d["den_floor_costly"])])
    md_table(["population", "no-AI WT, mean / median over priced proposals (bh)",
              "no-AI WT over distinct anchors, mean / median (bh)",
              "denominator over instances, mean / median (bh)",
              "denominator over priced proposals, mean / median (bh)",
              "0.20 x mean denominator (bh)", "0.10 x mean denominator (bh)",
              "0.20 x mean denominator over priced (bh)",
              "damage of the costly at 0.20, min / median (bh)",
              "denominator range over instances (bh)",
              "instances with the denominator at the 1 bh floor"], body)
    return res, desc


# --------------------------------------------------------------------------- #
# B. Absolute cost levels                                                      #
# --------------------------------------------------------------------------- #
def block_b(recs):
    res = OrderedDict()
    extra = OrderedDict()
    for (p, st), (xtok, x) in product(POPS.items(), LEVELS.items()):
        sel = [r for r in recs if st is None or r["stratum"] == st]
        o, costly, low = tally(sel, lambda r, x=x: 1 if r["dmg"] > x else 0)
        check("no undecided proposal on an absolute level", o["und"] == 0)
        res[(p, xtok)] = o
        extra[(p, xtok)] = OrderedDict(
            rel_low20=sum(1 for r in costly if n13.costly_of(r, 0.20) == 0),
            rel_costly_low=sum(1 for r in low if n13.costly_of(r, 0.20) == 1))
    additive(res, [(x,) for x in LEVELS], "B")
    for i, (a, b) in enumerate(zip(list(LEVELS)[:-1], list(LEVELS)[1:])):
        check("costly count falls as X rises",
              res[("Pooled", a)]["costly"] >= res[("Pooled", b)]["costly"])
    for (p, xtok), o in res.items():
        x = LEVELS[xtok]
        for f, (tok, txt) in FIELDS.items():
            if f in ("und", "instances", "priced"):
                continue
            add("B" + p + xtok + tok, grp(o[f]),
                "[B] {}, costly = realised damage above {:g} weighted bh (low-cost = at most "
                "{:g}), tau = 0.20 unchanged: {}".format(POP_NAME[p], x, x, txt))
        add("B" + p + xtok + "AppKShare", pct(o["app_k"], o["costly"]),
            "[B] {}, X = {:g} bh: costly proposals applied on the known board as a share of "
            "the costly".format(POP_NAME[p], x))
        e = extra[(p, xtok)]
        add("B" + p + xtok + "CostlyRelLowTwenty", grp(e["rel_low20"]),
            "[B] {}, X = {:g} bh: proposals costly at X that are low-cost on the relative level "
            "delta = 0.20".format(POP_NAME[p], x))
        add("B" + p + xtok + "LowRelCostlyTwenty", grp(e["rel_costly_low"]),
            "[B] {}, X = {:g} bh: proposals low-cost at X that are costly on the relative level "
            "delta = 0.20".format(POP_NAME[p], x))
    md("## B. Absolute cost levels (tau = 0.20 unchanged)", "",
       "Costly at X = the realised damage (executed original-field weighted tardiness from t_d "
       "minus the no-AI anchor, analysis/N11_rows_forecast.csv damage_orig_bh) above X weighted "
       "bh; low-cost = at most X (no bracket, so no undecided proposal). The gate and its "
       "readings are those of block A. 'Rel. low 0.20' = costly at X but low-cost on the "
       "relative level delta = 0.20; 'rel. costly 0.20' = low-cost at X but costly on the "
       "relative level. Field = field edits among the applied.", "")
    body = []
    for xtok, x in LEVELS.items():
        for p in POPS:
            o = res[(p, xtok)]
            e = extra[(p, xtok)]
            body.append(["{:g}".format(x), p, o["costly"], o["costly_inst"], o["ref_k"],
                         o["ref_f"], o["ref_both"],
                         "{} ({})".format(o["app_k"], pctp(o["app_k"], o["costly"])),
                         o["app_f"], "{} / {}".format(o["app_k_field"], o["app_f_field"]),
                         o["two_app_k"], o["two_app_f"],
                         "{} / {}".format(o["two_app_k_field"], o["two_app_f_field"]),
                         o["low_ref_k"], o["low_ref_f"], o["low_two_k"], o["low_two_f"],
                         o["dis_costly"], e["rel_low20"], e["rel_costly_low"]])
    md_table(["X (bh)", "population", "costly", "instances (costly)", "referred K", "FI",
              "both", "applied K", "applied FI", "field among applied K / FI",
              "applied, second price K", "FI", "field among them K / FI", "low-cost referred K",
              "FI", "low-cost referred, second price K", "FI", "costly disagree",
              "rel. low 0.20", "rel. costly 0.20"], body)
    # B2. the damage behind the headline sets at delta = 0.20
    sets = OrderedDict([
        ("AppliedCostly", ("the costly proposals the certificate applies on the known board",
                           [r for r in recs if n13.costly_of(r, 0.20) == 1 and not r["ref_k"]])),
        ("LowRefK", ("the low-cost proposals the certificate refers on the known board",
                     [r for r in recs if n13.costly_of(r, 0.20) == 0 and r["ref_k"]])),
        ("LowRefFI", ("the low-cost proposals the certificate refers with full information",
                      [r for r in recs if n13.costly_of(r, 0.20) == 0 and r["ref_f"]])),
        ("LowRefFIOnly", ("the low-cost proposals referred with full information only",
                          [r for r in recs if n13.costly_of(r, 0.20) == 0 and r["ref_f"]
                           and not r["ref_k"]])),
        ("LowTwoOnlyK", ("the low-cost proposals that only the second price refers on the "
                         "known board", [r for r in recs if n13.costly_of(r, 0.20) == 0
                                         and r["two_k"] and not r["ref_k"]])),
        ("Costly", ("all costly proposals", [r for r in recs if n13.costly_of(r, 0.20) == 1])),
    ])
    check("B2 set sizes 18 / 15 / 35 / 25 / 7 / 186",
          [len(v[1]) for v in sets.values()] == [18, 15, 35, 25, 7, 186])
    b2 = []
    for tok, (txt, sel) in sets.items():
        d = [r["dmg"] for r in sel]
        q = (min(d), statistics.median(d), max(d))
        n25 = sum(1 for v in d if v > 25.0)
        sts = Counter(r["st"] for r in sel)
        add("BTwo" + tok + "N", grp(len(sel)), "[B2] delta = 0.20: number of {}".format(txt))
        for nm, v in zip(("Min", "Median", "Max"), q):
            add("BTwo" + tok + "Damage" + nm, bhm(v),
                "[B2] delta = 0.20: {} realised damage of {}, weighted bh".format(nm.lower(),
                                                                                txt))
        add("BTwo" + tok + "AboveTwentyFive", grp(n25),
            "[B2] delta = 0.20: {} with realised damage above 25 weighted bh".format(txt))
        b2.append([txt, len(sel), " / ".join(bh1(v) for v in q), n25,
                   ", ".join("{} {}".format(k, sts[k]) for k in POPS if sts.get(k))])
    md("### B2. Realised damage behind the headline sets at delta = 0.20", "",
       "Realised damage in weighted bh (as above) of the sets the relative headline counts.", "")
    md_table(["set", "n", "damage min / median / max (bh)", "damage above 25 bh", "strata"], b2)
    return res, extra


# --------------------------------------------------------------------------- #
# C. Resolution of the headline comparison                                     #
# --------------------------------------------------------------------------- #
def signflip(rows, diffs):
    """Instance-level sign-flip test of Section 4.6.2 (e3_intervals, enumerated exactly)."""
    diffs = np.asarray(diffs, dtype=float)
    clusters = e3i.cluster_index_arrays([r["instance_id"] for r in rows])
    sums = e3i.cluster_sums(diffs, clusters)
    live = e3i._live_clusters(sums)
    k = int(live.shape[0])
    p = e3i.signflip_exact_p(sums)
    if k:
        # the two exact routes are the same test; cross-check where both apply
        scaled = np.round(np.asarray(sums) * 2.0)
        check("sign-flip enumeration equals the integer dynamic program",
              k > e3i.EXACT_SIGNFLIP_MAX_K
              or abs(e3i.signflip_exact_p_enum(sums) - e3i.signflip_exact_p_int(scaled)) < 1e-12)
    method = ("degenerate: no instance has a non-zero paired difference, so every sign vector "
              "gives the observed statistic and p = 1" if k == 0 else
              "exact enumeration over 2^{} sign vectors".format(k)
              if k <= e3i.EXACT_SIGNFLIP_MAX_K else "exact integer dynamic program")
    return OrderedDict(n=len(rows), n_clusters=len(clusters), k=k,
                       n_nonzero=int(np.count_nonzero(diffs)), stat=float(diffs.sum()),
                       mean=float(diffs.mean()) if len(rows) else None, p=p, method=method,
                       degenerate=(k == 0))


def block_c(recs, suite):
    out = OrderedDict()
    for dtok, delta in DELTAS.items():
        costly = [r for r in recs if n13.costly_of(r, delta) == 1]
        low = [r for r in recs if n13.costly_of(r, delta) == 0]
        ids = [r["item_id"] for r in costly]
        check("one costly proposal per instruction (item)", len(ids) == len(set(ids)))
        texts = {suite[i]["instruction"] for i in ids}
        inst = {r["instance_id"] for r in costly}
        disc = [r for r in costly if r["ref_k"] != r["ref_f"]]
        dinst = {r["instance_id"] for r in disc}
        o = OrderedDict(n_inst=len(inst), k_inst=len(dinst), n_instr=len(ids), k_instr=len(disc),
                        n_texts=len(texts))
        o["ub_inst"] = cp_upper(o["k_inst"], o["n_inst"])
        o["ub_instr"] = cp_upper(o["k_instr"], o["n_instr"])
        if o["k_inst"] == 0:
            check("zero-event bound = 1 - 0.05^(1/n) (instances)",
                  abs(o["ub_inst"] - (1 - 0.05 ** (1.0 / o["n_inst"]))) < 1e-9)
        if o["k_instr"] == 0:
            check("zero-event bound = 1 - 0.05^(1/n) (instructions)",
                  abs(o["ub_instr"] - (1 - 0.05 ** (1.0 / o["n_instr"]))) < 1e-9)
        o["sf_app"] = signflip(costly, [float(not r["ref_k"]) - float(not r["ref_f"])
                                        for r in costly])
        o["sf_low"] = signflip(low, [float(r["ref_k"]) - float(r["ref_f"]) for r in low])
        o["sf_app_two"] = signflip(costly, [float(not r["two_k"]) - float(not r["two_f"])
                                            for r in costly])
        out[dtok] = o
    o = out["DeltaTwenty"]
    check("headline: 50 instances and 186 instructions carry a costly proposal, none discordant",
          (o["n_inst"], o["k_inst"], o["n_instr"], o["k_instr"]) == (50, 0, 186, 0), o)
    check("headline sign-flip test on the applied costly proposals is degenerate",
          o["sf_app"]["degenerate"] and o["sf_app"]["p"] == 1.0 and o["sf_app"]["stat"] == 0.0)
    check("delta 0.10: 54 instances and 208 instructions, 7 discordant",
          (out["DeltaTen"]["n_inst"], out["DeltaTen"]["n_instr"], out["DeltaTen"]["k_instr"])
          == (54, 208, 7), out["DeltaTen"])
    for dtok, o in out.items():
        dl = DELTAS[dtok]
        p = "C" + dtok
        add(p + "CostlyInstances", o["n_inst"],
            "[C] delta = {:.2f}: instances that carry at least one costly proposal".format(dl))
        add(p + "DiscordantInstances", o["k_inst"],
            "[C] delta = {:.2f}: instances with a costly proposal whose certificate disposition "
            "differs between the known board and full information".format(dl))
        add(p + "InstanceBound", pct(o["ub_inst"], 1.0),
            "[C] delta = {:.2f}: exact one-sided 95% Clopper-Pearson upper bound on the share of "
            "instances with a costly proposal whose disposition differs ({} of {}{})".format(
                dl, o["k_inst"], o["n_inst"],
                "; zero events, 1 - 0.05^(1/n)" if o["k_inst"] == 0 else ""))
        add(p + "CostlyInstructions", grp(o["n_instr"]),
            "[C] delta = {:.2f}: instructions that carry a costly proposal (one reference "
            "proposal per instruction)".format(dl))
        add(p + "CostlyInstructionTexts", grp(o["n_texts"]),
            "[C] delta = {:.2f}: distinct instruction texts among them".format(dl))
        add(p + "DiscordantInstructions", o["k_instr"],
            "[C] delta = {:.2f}: instructions whose costly proposal has a disposition that "
            "differs between the two readings".format(dl))
        add(p + "InstructionBound", pct(o["ub_instr"], 1.0),
            "[C] delta = {:.2f}: exact one-sided 95% Clopper-Pearson upper bound on the share of "
            "instructions with a costly proposal whose disposition differs ({} of {}{})".format(
                dl, o["k_instr"], o["n_instr"],
                "; zero events, 1 - 0.05^(1/n)" if o["k_instr"] == 0 else ""))
        for key, tok, what in (("sf_app", "App", "applied costly proposals (applied on K minus "
                                                  "applied with FI, over the costly)"),
                               ("sf_low", "LowRef", "referred low-cost proposals (referred on K "
                                                    "minus referred with FI, over the "
                                                    "low-cost)"),
                               ("sf_app_two", "TwoApp", "applied costly proposals with the second "
                                                        "price")):
            s = o[key]
            add(p + "SignFlip" + tok + "Stat", sgn(s["stat"]),
                "[C] delta = {:.2f}: sign-flip test of Section 4.6.2, statistic = sum over "
                "instances of the paired differences, {}".format(dl, what))
            add(p + "SignFlip" + tok + "MeanDiff", ppv(s["mean"]),
                "[C] delta = {:.2f}: the same as a mean paired difference, percentage points "
                "({})".format(dl, what))
            add(p + "SignFlip" + tok + "Clusters", s["n_clusters"],
                "[C] delta = {:.2f}: instances in the paired population ({})".format(dl, what))
            add(p + "SignFlip" + tok + "Live", s["k"],
                "[C] delta = {:.2f}: instances whose paired differences do not sum to zero, the "
                "draws the sign-flip null randomises ({})".format(dl, what))
            add(p + "SignFlip" + tok + "P", pfmt(s["p"]),
                "[C] delta = {:.2f}: exact two-sided sign-flip p-value ({}); {}".format(
                    dl, what, s["method"]))
    md("## C. Resolution of the headline comparison", "",
       "Discordant = a costly proposal whose certificate disposition differs between the known "
       "board and full information. Bound = exact one-sided 95% Clopper-Pearson upper bound on "
       "the share of units (instances that carry a costly proposal, or instructions that carry "
       "one) with a discordant costly proposal; with zero events it is 1 - 0.05^(1/n) "
       "(asserted equal), with k events beta(0.95; k + 1, n - k). In the direct benchmark each "
       "instruction carries one reference proposal, so instructions = costly proposals.", "")
    body = []
    for dtok, o in out.items():
        body.append(["{:.2f}".format(DELTAS[dtok]), o["n_inst"], o["k_inst"],
                     "{} ({:.2f}%)".format(pctp(o["ub_inst"], 1.0), 100 * o["ub_inst"]),
                     o["n_instr"], o["n_texts"], o["k_instr"],
                     "{} ({:.2f}%)".format(pctp(o["ub_instr"], 1.0), 100 * o["ub_instr"])])
    md_table(["delta", "instances with a costly proposal (n)", "of them discordant",
              "95% upper bound, instances", "instructions with a costly proposal (n)",
              "distinct instruction texts", "of them discordant", "95% upper bound, instructions"],
             body)
    md("### The sign-flip permutation test of Section 4.6.2", "",
       "Section 4.6.2 (the manuscript text, sec:setup-stats): \"A paired comparison "
       "uses a sign-flip permutation test that flips all paired differences from one instance "
       "together\", and the primary comparison is the certificate on the known board against "
       "the full-information gate at delta = tau = 0.20; app_methods_detail.tex: \"The sign-flip "
       "permutation test is enumerated exactly.\" Implementation reused: "
       "code/scripts/e3_intervals.py (cluster_index_arrays, cluster_sums, signflip_exact_p; "
       "the DG18 cluster test). Paired difference per proposal = indicator on the known board "
       "minus indicator with full information; statistic = the sum over instances (= count on "
       "K minus count with FI); two-sided p over all 2^k sign vectors of the k instances whose "
       "differences do not cancel. The direct benchmark has one proposal per instruction and no "
       "repeat, so 'repeat 0' is the whole population.", "")
    body = []
    for dtok, o in out.items():
        for key, what in (("sf_app", "applied costly (certificate)"),
                          ("sf_app_two", "applied costly (with the second price)"),
                          ("sf_low", "referred low-cost (certificate)")):
            s = o[key]
            body.append(["{:.2f}".format(DELTAS[dtok]), what, s["n"], s["n_clusters"],
                         s["n_nonzero"], s["k"], sgn(s["stat"]),
                         ppv(s["mean"]), pfmt(s["p"]), s["method"]])
    md_table(["delta", "outcome", "proposals", "instances", "proposals that differ",
              "instances with a non-zero sum", "statistic (K - FI)", "mean difference (pp)",
              "exact two-sided p", "note"], body)
    return out


# --------------------------------------------------------------------------- #
# D. Shares over the low-cost proposals with an operation                      #
# --------------------------------------------------------------------------- #
def block_d(boot, recs):
    m15 = macros_of(IN20["n15_macros"])
    out = OrderedDict()
    for dtok, delta in DELTAS.items():
        low = [r for r in recs if n13.costly_of(r, delta) == 0]
        ops = [r for r in low if r["split"] != "empty"]
        check("operation count agrees with the edit type", all(r["n_ops"] >= 1 for r in ops)
              and all(r["n_ops"] == 0 for r in low if r["split"] == "empty"))
        t = "Twenty" if delta == 0.20 else "Ten"
        check("low-cost proposals with an operation equal \\nFifteenLowWithOps" + t,
              grp(len(ops)) == m15["nFifteenLowWithOps" + t], (len(ops), t))
        o = OrderedDict(low=len(low), ops=len(ops), empty=len(low) - len(ops))
        for key, fn in (("cert_k", lambda r: r["ref_k"]), ("cert_f", lambda r: r["ref_f"]),
                        ("two_k", lambda r: r["two_k"]), ("two_f", lambda r: r["two_f"])):
            fl = [bool(fn(r)) for r in ops]
            lo, hi = boot.ci(ops, fl) if ops else (None, None)
            fa = [bool(fn(r)) for r in low]
            alo, ahi = boot.ci(low, fa) if low else (None, None)
            o[key] = OrderedDict(k=sum(fl), lo=lo, hi=hi, k_all=sum(fa), lo_all=alo, hi_all=ahi,
                                 k_empty=sum(fa) - sum(fl))
        out[dtok] = o
    o = out["DeltaTwenty"]
    check("915 low-cost proposals with an operation at delta 0.20", o["ops"] == 915, o["ops"])
    check("certificate on K refers 15 of them (1.6%), as N15",
          o["cert_k"]["k"] == 15 and pct(15, 915) == m15["nFifteenCertFrWithOpsShareTwenty"])
    check("the all-low-cost interval of the certificate on K equals N15 (0.4% to 2.3%)",
          (pctv(o["cert_k"]["lo_all"]), pctv(o["cert_k"]["hi_all"]),
           pct(o["cert_k"]["k_all"], o["low"])) ==
          (m15["nFifteenCertFrShareLoTwenty"], m15["nFifteenCertFrShareHiTwenty"],
           m15["nFifteenCertFrShareTwenty"]), o["cert_k"])
    check("all-low-cost referral counts equal the headline (15, 35, 22, 39)",
          (o["cert_k"]["k_all"], o["cert_f"]["k_all"], o["two_k"]["k_all"],
           o["two_f"]["k_all"]) == (15, 35, 22, 39))
    names = OrderedDict([("cert_k", ("CertK", "the certificate on the known board")),
                         ("cert_f", ("CertFI", "the certificate with full information")),
                         ("two_k", ("TwoK", "the certificate with the second price, known "
                                            "board")),
                         ("two_f", ("TwoFI", "the certificate with the second price, full "
                                             "information"))])
    for dtok, o in out.items():
        dl = DELTAS[dtok]
        p = "D" + dtok
        add(p + "Low", grp(o["low"]), "[D] delta = {:.2f}: low-cost proposals".format(dl))
        add(p + "LowWithOps", grp(o["ops"]),
            "[D] delta = {:.2f}: low-cost proposals that carry at least one operation".format(dl))
        add(p + "LowEmpty", grp(o["empty"]),
            "[D] delta = {:.2f}: low-cost proposals with no operation".format(dl))
        for key, (tok, txt) in names.items():
            s = o[key]
            add(p + tok + "Ref", grp(s["k"]),
                "[D] delta = {:.2f}: low-cost proposals with an operation referred by "
                "{}".format(dl, txt))
            add(p + tok + "Share", pct(s["k"], o["ops"]),
                "[D] delta = {:.2f}: the same as a share of the low-cost proposals with an "
                "operation".format(dl))
            add(p + tok + "ShareLo", pctv(s["lo"]),
                "[D] delta = {:.2f}: lower end of the 95% cluster-bootstrap interval of that "
                "share (60 instances, n2 seed, 20,000 replicates)".format(dl))
            add(p + tok + "ShareHi", pctv(s["hi"]),
                "[D] delta = {:.2f}: upper end of the same interval".format(dl))
            add(p + tok + "RefAll", grp(s["k_all"]),
                "[D] delta = {:.2f}: all low-cost proposals referred by {}".format(dl, txt))
            add(p + tok + "ShareAll", pct(s["k_all"], o["low"]),
                "[D] delta = {:.2f}: the same as a share of all low-cost proposals".format(dl))
            add(p + tok + "ShareAllLo", pctv(s["lo_all"]),
                "[D] delta = {:.2f}: lower end of the 95% cluster-bootstrap interval of the "
                "all-low-cost share".format(dl))
            add(p + tok + "ShareAllHi", pctv(s["hi_all"]),
                "[D] delta = {:.2f}: upper end of the same interval".format(dl))
            add(p + tok + "RefEmpty", grp(s["k_empty"]),
                "[D] delta = {:.2f}: low-cost proposals with no operation referred by "
                "{}".format(dl, txt))
    md("## D. Low-cost referral shares over the proposals that carry an operation", "",
       "Base = the low-cost proposals whose reference proposal carries at least one operation "
       "(edit type not 'empty'; equal to n_ops >= 1, asserted). Interval = 95% cluster "
       "bootstrap over the 60 instances (n2 seed 20261026, 20,000 replicates), the interval "
       "the other shares use. The all-low-cost columns repeat the published base for "
       "comparison (the certificate's interval on K equals N15, asserted).", "")
    body = []
    for dtok, o in out.items():
        for key, (tok, txt) in names.items():
            s = o[key]
            body.append(["{:.2f}".format(DELTAS[dtok]), txt, o["low"], o["ops"],
                         ci_str(s["k"], o["ops"], s["lo"], s["hi"]),
                         ci_str(s["k_all"], o["low"], s["lo_all"], s["hi_all"]), s["k_empty"]])
    md_table(["delta", "check", "low-cost", "with an operation",
              "referred / with an operation [95% CI]", "referred / all low-cost [95% CI]",
              "referred without an operation"], body)
    return out


# --------------------------------------------------------------------------- #
# E. The floor                                                                 #
# --------------------------------------------------------------------------- #
def block_e(recs):
    m15 = macros_of(IN20["n15_macros"])
    m13 = macros_of(IN20["n13_macros"])
    out = OrderedDict()
    for p, st in POPS.items():
        sel = [r for r in recs if st is None or r["stratum"] == st]
        for rd, key in (("K", "lb_k"), ("FI", "lb_f")):
            check("bound logged on every priced proposal ({})".format(rd),
                  all(r[key] is not None for r in sel))
            zero = sum(1 for r in sel if r[key] == 0.0)
            binds = sum(1 for r in sel if r[key] < FLOOR)
            between = sum(1 for r in sel if 0.0 < r[key] < FLOOR)
            neg = sum(1 for r in sel if r[key] < 0.0)
            check("no negative bound ({})".format(rd), neg == 0, neg)
            out[(p, rd)] = OrderedDict(n=len(sel), zero=zero, binds=binds, between=between)
    for rd in ("K", "FI"):
        for f in ("n", "zero", "binds", "between"):
            check("strata sum to pooled (E {} {})".format(rd, f),
                  sum(out[(p, rd)][f] for p in POPS if p != "Pooled") == out[("Pooled", rd)][f])
    o = out[("Pooled", "K")]
    check("known board: 699 zero bounds and 701 with the floor binding (supplement, N15, N13)",
          (o["zero"], o["binds"]) == (699, 701) and m15["nFifteenZeroBound"] == "699"
          and m15["nFifteenFloorBinds"] == "701" and m13["nThirteenCLbZeroCount"] == "699"
          and m13["nThirteenCBindCount"] == "701" and m13["nThirteenCLbBetweenCount"]
          == str(o["between"]), o)
    fz = {r["item_id"] for r in recs if r["lb_f"] == 0.0}
    dz = {r["item_id"] for r in recs if r["den"] <= FLOOR}
    add("EFIZeroOnFloorInstances", grp(len(fz & dz)),
        "[E] priced proposals with a zero full-information bound that sit on the instances whose "
        "full-window optimum is below 1 bh (realised-cost denominator at the floor)")
    add("EFloorInstancesPriced", grp(len(dz)),
        "[E] priced proposals on the instances whose realised-cost denominator is at the floor")
    for (p, rd), o in out.items():
        rn = "the known board" if rd == "K" else "full information"
        add("E" + p + rd + "ZeroBound", grp(o["zero"]),
            "[E] {}: priced proposals whose lower bound on {} is exactly zero".format(
                POP_NAME[p], rn))
        add("E" + p + rd + "FloorBinds", grp(o["binds"]),
            "[E] {}: priced proposals on which the floor of 1 weighted bh binds on {} (bound "
            "below the floor)".format(POP_NAME[p], rn))
        add("E" + p + rd + "FloorBindsShare", pct(o["binds"], o["n"]),
            "[E] {}: the same as a share of the priced proposals".format(POP_NAME[p]))
        add("E" + p + rd + "BetweenZeroOne", grp(o["between"]),
            "[E] {}: priced proposals whose bound on {} lies strictly between 0 and 1 weighted "
            "bh".format(POP_NAME[p], rn))
    md("## E. The floor of 1 weighted bh", "",
       "Bound = the lower bound of the proposal's board that the certificate divides by: on the "
       "known board the logged dt_lb (results/n11_decision_time/items.jsonl), with full "
       "information the logged p.lb (results/n11_forecast/fullinfo_direct.jsonl); the floor "
       "binds when the bound is below 1 weighted bh. The known-board counts equal the "
       "supplement's 699 and 701 (asserted against \\nFifteenZeroBound, \\nFifteenFloorBinds, "
       "\\nThirteenCLbZeroCount, \\nThirteenCBindCount); difference 0.", "")
    body = []
    for p in POPS:
        k, f = out[(p, "K")], out[(p, "FI")]
        body.append([p, k["n"], k["zero"], k["between"], frac(k["binds"], k["n"]), f["zero"],
                     f["between"], frac(f["binds"], f["n"])])
    md("With full information the bound is zero on {} priced proposals, and {} of them are the {} "
       "priced proposals on the instances whose full-window optimum is below 1 bh (all "
       "Buildings; block A).".format(len(fz), len(fz & dz), len(dz)), "")
    md_table(["population", "priced", "K: bound = 0", "K: 0 < bound < 1",
              "K: floor binds", "FI: bound = 0", "FI: 0 < bound < 1", "FI: floor binds"], body)
    return out


# --------------------------------------------------------------------------- #
# F. File inspection: per-order completion times of executed schedules         #
# --------------------------------------------------------------------------- #
def first_record(path):
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            if ln.strip():
                return json.loads(ln)
    return None


def all_keys(o, pre=""):
    out = set()
    if isinstance(o, dict):
        for k, v in o.items():
            out.add(pre + k)
            out |= all_keys(v, pre + k + ".")
    elif isinstance(o, list) and o:
        out |= all_keys(o[0], pre + "[].")
    return out


def block_f():
    tim = ("start_bh", "end_bh", "completion_bh", "completion_time", "finish_bh", "finish_time",
           "c_j", "late_order", "per_order", "n_late")
    files = OrderedDict([
        ("items_dt", (RESULTS / "n11_decision_time" / "items.jsonl",
                      "direct benchmark at t_d, one record per item: the executed schedule of "
                      "the applied proposal enters only as scalars")),
        ("rows_e1", (RESULTS / "n11_e2e" / "rows_e1_primary.jsonl",
                     "gate stress test at t_d, one record per proposal x repeat x mode")),
        ("proposals_opus", (RESULTS / "n11_e2e" / "twin" / "primary" / "e1_eval_opus5" /
                            "proposals.jsonl", "per-proposal verdict log (all cells alike)")),
        ("fullinfo", (RESULTS / "n11_forecast" / "fullinfo_direct.jsonl",
                      "full-information pricing")),
        ("c_components", (RESULTS / "n11_decision_time" / "c_components.jsonl",
                          "oracle inputs: constrained trade components of the known board at "
                          "t_d")),
        ("relaxed_inputs", (RESULTS / "n11_decision_time" / "relaxed_inputs.jsonl",
                            "oracle inputs: relaxed trade sub-boards")),
    ])
    found = OrderedDict()
    for key, (path, what) in files.items():
        rec = first_record(path)
        ks = all_keys(rec)
        n = sum(1 for ln in open(path, encoding="utf-8") if ln.strip())
        hits = sorted(k for k in ks if any(t in k.lower() for t in tim))
        found[key] = (path, what, n, hits, ks)
    # the executed-schedule records carry scalars only
    for key in ("items_dt", "rows_e1", "proposals_opus", "fullinfo"):
        check("no per-order time field in {}".format(key), found[key][3] == [], found[key][3])
    check("items.jsonl carries the executed objective as scalars",
          {"rw_obj", "rw_obj_orig", "rw0_obj_orig", "om_obj_orig"} <= found["items_dt"][4])
    check("proposal log carries a schedule digest and scalar objectives only",
          {"verdict.schedule_digest", "verdict.objective.wwt_original_bh",
           "verdict.objective.n_assignments"} <= found["proposals_opus"][4])
    anchor = json.loads((ANALYSIS / "ladder" / "rule_anchor.json").read_text())[0]
    check("no-AI anchor log: scalars and a digest",
          {"schedule_digest", "wwt_original_bh", "n_assignments"} <= set(anchor)
          and not any(t in k.lower() for k in anchor for t in tim))
    check("per-order times exist only as oracle warm starts",
          "warm.assignments.[].end_bh" in found["c_components"][4]
          and "warm.[].end_bh" in found["relaxed_inputs"][4])
    md("## F. Do the logs hold per-order completion times of the executed schedules?", "",
       "Answer: **no**. File inspection only (every field name of the first record of each "
       "file, nested keys included, searched for start_bh, end_bh, completion_bh, "
       "completion_time, finish_bh, finish_time, c_j, late_order, per_order, n_late):", "")
    body = []
    for key, (path, what, n, hits, ks) in found.items():
        body.append(["`{}`".format(path.relative_to(ROOT)), n, what,
                     ", ".join(hits) if hits else "none"])
    body.append(["`analysis/ladder/rule_anchor.json`", 116, "no-AI anchors", "none"])
    md_table(["file", "records", "content", "per-order time fields"], body)
    md("The executed schedule of an applied proposal (the site's dispatcher replayed over the "
       "rest of the window, scored on the original values) is stored only as scalars: "
       "items.jsonl `rw_obj`, `rw_obj_orig`, `rw0_obj_orig`, `om_obj_orig` (weighted tardiness "
       "in bh), rows_e1_primary.jsonl `rw_obj`, `rw_obj_orig`, and the proposal logs' "
       "`verdict.objective` {`feasible`, `n_assignments`, `wwt_adjusted_bh`, `wwt_original_bh`} "
       "with `verdict.schedule_digest`, a SHA-256 of the schedule and not the schedule; the "
       "no-AI anchors (rule_anchor.json) likewise carry `wwt_*`, `n_assignments` and "
       "`schedule_digest`. Per-order start and end times appear only in "
       "c_components.jsonl `warm.assignments[]` {`wo`, `tech`, `start_bh`, `end_bh`} and "
       "relaxed_inputs.jsonl `warm[]`: the ATC warm starts of the oracle on trade sub-boards of "
       "the known board at t_d (releases raised to t_d, later orders absent), for the oracle "
       "population only (449 and 28 records). They are not the executed schedules. Counting the "
       "new late class-1 and class-2 orders per applied proposal therefore needs a dispatcher "
       "replay of each applied proposal (no solver), which this design excludes.", "")
    return found


# --------------------------------------------------------------------------- #
# G. D-REL2 with the second price against the site's own schedule              #
# --------------------------------------------------------------------------- #
G_DESIGN = "D-REL2"
G_THR = OrderedDict([("OwnThreshold", 0.02), ("EqualThreshold", 0.20)])
G_THR_TXT = {"OwnThreshold": "D-REL2 at its own threshold of 0.02",
             "EqualThreshold": "D-REL2 at the equal threshold of 0.20"}
G_OTHER = (0, 20, 0)      # the other agent's recomputed cell (0.20 threshold, delta 0.20): reported


def g_first(r, thr):
    """D-REL2's first price on the known board above a threshold (n13.j_flag's P1 test)."""
    v = r["p_" + G_DESIGN]
    return v is not None and v > thr


def g_site_flag(r, thr, site):
    """n16 block I's site_flag for D-REL2, with D-REL2's threshold as a parameter."""
    return g_first(r, thr) or (r["split"] == "field_changing" and site[r["item_id"]] > TAU)


def g_bound_flag(r, thr):
    """n16.sp_flag / n13.j_flag (second price on field edits only, at tau = 0.20)."""
    return g_first(r, thr) or (r["split"] == "field_changing" and r["g_orig"] > TAU)


def block_g(boot, recs, by, site):
    m16 = macros_of(IN20["n16_macros"])
    m13 = macros_of(IN20["n13_macros"])
    check("D-REL2's published threshold is 0.02 in n13 and n16",
          n13.SETTINGS[G_DESIGN] == 0.02 and n16.SETTING[G_DESIGN] == 0.02)
    check("n16 block I's exploratory D-REL2 cell is (0, 39, 1)",
          n16.I_EXP["direct20"][G_DESIGN] == (0, 39, 1))
    for r in recs:
        iid = r["item_id"]
        it = by[iid]
        check("the published D-REL2 flag equals price > 0.02 on the known board",
              g_first(r, 0.02) == n13.refers(r, G_DESIGN), iid)
        vf = n16.site_price(it["dt_obj_orig"], it["an_obj"])
        check("printed and full-precision values give the same s2_site referral (n16 block I)",
              (site[iid] > TAU) == (vf > TAU), (iid, site[iid], vf))
        if r["split"] == "field_changing":
            check("s2_site > tau implies s2 > tau (n16 block I)",
                  r["g_orig"] > TAU or not site[iid] > TAU, iid)
        check("the bound version at 0.02 equals n16.sp_flag",
              g_bound_flag(r, 0.02) == n16.sp_flag(r, G_DESIGN), iid)
    out = OrderedDict()
    for dtok, delta in DELTAS.items():
        for ttok, thr in G_THR.items():
            for ref, fn in (("site", lambda r, t=thr: g_site_flag(r, t, site)),
                            ("bound", lambda r, t=thr: g_bound_flag(r, t))):
                s = n13.score(boot, recs, fn, delta, with_ci=True)
                refd = [r for r, f in zip(s["_cheap"], s["_fr"]) if f]
                ben = sum(1 for r in refd if r["primary_class"] == "benign")
                by_first = sum(1 for r in refd if g_first(r, thr))
                applied = [r for r, m in zip(s["_costly"], s["_miss"]) if m]
                out[(dtok, ttok, ref)] = OrderedDict(
                    costly=s["costly"], low=s["cheap"], und=s["und"], app=s["miss"],
                    app_field=sum(1 for r in applied if r["split"] == "field_changing"),
                    fr=s["fr"], ben=ben, by_first=by_first, by_second=s["fr"] - by_first,
                    lo=s["fr_lo"], hi=s["fr_hi"], ref_ids={r["item_id"] for r in refd})
    # the site variant refers a subset of what the bound variant refers, in every cell
    for (dtok, ttok, ref), o in out.items():
        if ref == "site":
            b = out[(dtok, ttok, "bound")]
            check("site-variant referrals are a subset of the bound variant's ({} {})"
                  .format(dtok, ttok), o["ref_ids"] <= b["ref_ids"])
            check("same costly / low-cost bases in both variants",
                  (o["costly"], o["low"]) == (b["costly"], b["low"]))
    # n16 block I at D-REL2's own threshold: the three named macros, then share and interval
    for dtok, mt in (("DeltaTwenty", "Twenty"), ("DeltaTen", "Ten")):
        o = out[(dtok, "OwnThreshold", "site")]
        pre = "nSixteenIRelTwoSite"
        check("0.02 site cell equals \\{}Miss/Fr/FrBenign{}".format(pre, mt),
              (str(o["app"]), str(o["fr"]), str(o["ben"])) ==
              (m16[pre + "Miss" + mt], m16[pre + "Fr" + mt], m16[pre + "FrBenign" + mt]),
              (o["app"], o["fr"], o["ben"]))
        check("0.02 site share and interval equal \\{}FrShare/Lo/Hi{}".format(pre, mt),
              (pct(o["fr"], o["low"]), pctv(o["lo"]), pctv(o["hi"])) ==
              (m16[pre + "FrShare" + mt], m16[pre + "FrLo" + mt], m16[pre + "FrHi" + mt]),
              (o["fr"], o["lo"], o["hi"]))
    # n13 section J for the bound variant
    for dtok, ttok, setting in (("DeltaTwenty", "OwnThreshold", "Pub"),
                                ("DeltaTen", "OwnThreshold", "Pub"),
                                ("DeltaTwenty", "EqualThreshold", "TauDelta")):
        o = out[(dtok, ttok, "bound")]
        jb = "nThirteenJ{}KRelTwoSecondPriceFieldOnly{}".format(setting, dtok)
        check("bound cell equals \\{}Miss/Fr".format(jb),
              (str(o["app"]), str(o["fr"])) == (m13[jb + "Miss"], m13[jb + "Fr"]),
              (o["app"], o["fr"]))
        check("bound share and interval equal \\{}FrShare/Lo/Hi".format(jb),
              (pct(o["fr"], o["low"]), pctv(o["lo"]), pctv(o["hi"])) ==
              (m13[jb + "FrShare"], m13[jb + "FrLo"], m13[jb + "FrHi"]),
              (o["fr"], o["lo"], o["hi"]))
    check("costly / low-cost at delta 0.20 and 0.10 are 186 / 1,170 and 208 / 1,148",
          (out[("DeltaTwenty", "OwnThreshold", "site")]["costly"],
           out[("DeltaTwenty", "OwnThreshold", "site")]["low"],
           out[("DeltaTen", "OwnThreshold", "site")]["costly"],
           out[("DeltaTen", "OwnThreshold", "site")]["low"]) == (186, 1170, 208, 1148))
    eq = out[("DeltaTwenty", "EqualThreshold", "site")]
    other_same = (eq["app"], eq["fr"], eq["ben"]) == G_OTHER
    # macros: the site variant only
    for dtok, delta in DELTAS.items():
        base = out[(dtok, "OwnThreshold", "site")]
        add("G" + dtok + "Costly", base["costly"],
            "[G] delta = {:.2f}: costly proposals (the base of the applied counts)".format(delta))
        add("G" + dtok + "Low", grp(base["low"]),
            "[G] delta = {:.2f}: low-cost proposals (the base of the referral shares)"
            .format(delta))
    for ttok, thr in G_THR.items():
        add("G" + ttok, "{:.2f}".format(thr),
            "[G] {}; the second price keeps tau = 0.20".format(G_THR_TXT[ttok]))
    for dtok, delta in DELTAS.items():
        for ttok, thr in G_THR.items():
            o = out[(dtok, ttok, "site")]
            p = "GRelTwoSite" + ttok
            what = ("[G] delta = {:.2f}, known board, {} or, on a field edit, the second price "
                    "against the site's own schedule s2_site = (obj_orig_K - WT_anchor_K) / "
                    "max(WT_anchor_K, 1 bh) above tau = 0.20 (n16 block I)".format(delta,
                                                                                   G_THR_TXT[ttok]))
            add(p + "Applied" + dtok, o["app"], what + ": costly proposals applied")
            add(p + "LowRef" + dtok, grp(o["fr"]), what + ": low-cost proposals referred")
            add(p + "LowRefBenign" + dtok, o["ben"],
                what + ": benign proposals among the low-cost referred")
            add(p + "LowRefShare" + dtok, pct(o["fr"], o["low"]),
                what + ": low-cost referral share")
            add(p + "LowRefLo" + dtok, pctv(o["lo"]),
                what + ": lower end of the 95% cluster-bootstrap interval of that share (60 "
                "instances, n2 seed, 20,000 replicates)")
            add(p + "LowRefHi" + dtok, pctv(o["hi"]), what + ": upper end of the same interval")
    md("## G. D-REL2 with the second price against the site's own schedule", "",
       "Known board, direct benchmark, 1,356 priced proposals. The gate refers a proposal when "
       "D-REL2's price exceeds its threshold (0.02, its own, or 0.20, equal to the "
       "certificate's tolerance) or, on a field edit, when the second price exceeds tau = 0.20. "
       "Site: the second price against the site's own schedule, s2_site = (obj_orig_K - "
       "WT_anchor_K) / max(WT_anchor_K, 1 bh), n16 block I's definition (n16.site_price on "
       "columns obj_orig and ref1 of the direct_td rows of analysis/N11_rows_direct.csv). "
       "Bound (comparison only, no macro): the bound-referenced second price g_orig = "
       "(obj_orig_K - LB_anchor_K) / max(LB_anchor_K, 1 bh), n16.sp_flag and n13 section J. "
       "Applied = costly and not referred. Benign = primary class 'benign'. Interval = 95% "
       "cluster bootstrap over the 60 instances (n2 seed 20261026, 20,000 replicates), the "
       "interval the other shares use. Asserted: the 0.02 site cells equal "
       "\\nSixteenIRelTwoSite{Miss,Fr,FrBenign,FrShare,FrLo,FrHi}{Twenty,Ten}; the 0.02 bound "
       "cells equal \\nThirteenJPubKRelTwoSecondPriceFieldOnlyDelta{Twenty,Ten}{Miss,Fr,"
       "FrShare,FrLo,FrHi}; the 0.20 bound cell at delta 0.20 equals "
       "\\nThirteenJTauDeltaKRelTwoSecondPriceFieldOnlyDeltaTwenty{Miss,Fr,FrShare,FrLo,FrHi} "
       "(n13's tau = delta setting reads D-REL2 and g_orig at delta, which is 0.20 here; at "
       "delta 0.10 it reads 0.10, so the 0.20 bound cell at delta 0.10 has no n13 counterpart "
       "and is not asserted); the site variant refers a subset of the bound variant's "
       "referrals in every cell.", "")
    body = []
    for dtok, delta in DELTAS.items():
        for ttok, thr in G_THR.items():
            for ref in ("site", "bound"):
                o = out[(dtok, ttok, ref)]
                body.append(["{:.2f}".format(delta), "{:.2f}".format(thr),
                             "site (s2_site)" if ref == "site" else "bound (s2), comparison",
                             o["costly"], "{:,}".format(o["low"]),
                             "{} (field edits {})".format(o["app"], o["app_field"]), o["fr"],
                             "{} / {}".format(o["by_first"], o["by_second"]), o["ben"],
                             "{} [{}, {}]".format(pctp(o["fr"], o["low"]), pctpv(o["lo"]),
                                                  pctpv(o["hi"]))])
    md_table(["delta", "D-REL2 threshold", "second price against", "costly", "low-cost",
              "costly applied", "low-cost referred",
              "referred by D-REL2 / by the second price only", "benign among the referred",
              "low-cost referral share [95% CI]"], body)
    md("The other agent's recomputation of the 0.20 site cell at delta 0.20 (0 costly applied, "
       "20 low-cost referred, 0 benign) is {} by this script ({} / {} / {}); reported, not "
       "asserted.".format("reproduced" if other_same else "NOT reproduced", eq["app"], eq["fr"],
                          eq["ben"]), "")
    return out, other_same


# --------------------------------------------------------------------------- #
# Self-test: a second code path that reads the files directly                  #
# --------------------------------------------------------------------------- #
def selftest(resA, descA, resB, resC, resD, resE, resG):
    """Three numbers per block, recomputed from csv/json without the n13/n16 loaders."""
    rows = {}
    with open(ANALYSIS / "N11_rows_forecast.csv", encoding="utf-8") as fh:
        for x in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            rows.setdefault(x["reading"], {})[x["item_id"]] = x
    K, F = rows["K"], rows["FI"]
    items = {}
    with open(RESULTS / "n11_decision_time" / "items.jsonl", encoding="utf-8") as fh:
        for ln in fh:
            if ln.strip():
                o = json.loads(ln)
                if o["set"] == "published":
                    items[o["item_id"]] = o
    fi = {}
    with open(RESULTS / "n11_forecast" / "fullinfo_direct.jsonl", encoding="utf-8") as fh:
        for ln in fh:
            if ln.strip():
                o = json.loads(ln)
                fi[o["uid"]] = o
    fa = {}
    with open(RESULTS / "n11_forecast" / "anchors_direct.jsonl", encoding="utf-8") as fh:
        for ln in fh:
            if ln.strip():
                o = json.loads(ln)
                if o["reading"] == "FI":
                    fa[(o["iid"], o["fk"], float(o["t_d"]))] = o["a"]
    base_fp = D.BASE_FP
    dens = {}
    with open(RESULTS / "oracle_v1" / "brackets.jsonl", encoding="utf-8") as fh:
        for ln in fh:
            if ln.strip():
                o = json.loads(ln)
                if o["fingerprint"] == base_fp:
                    dens[o["instance_id"]] = max(0.5 * (float(o["lower"]) + float(o["upper"])), 1.0)
    st_name = {"c09_storm2_w80": "Primary", "c10_storm2_w80": "Confirmation",
               "c10_replay_400": "Buildings"}

    def fl(x):
        return None if x == "" else float(x)

    def costly(iid, delta):
        lo, hi = fl(K[iid]["orig_m_lo"]), fl(K[iid]["orig_m_hi"])
        if lo is None or hi is None:
            return None
        return 1 if lo > delta else (0 if hi <= delta else None)

    def refk(iid):
        return float(K[iid]["p_G-CERT"]) > 0.20

    def reff(iid):
        return float(F[iid]["p_G-CERT"]) > 0.20

    def twok(iid):
        it = items[iid]
        g = (it["dt_obj_orig"] - it["an_lb"]) / max(it["an_lb"], 1.0)
        return refk(iid) or (K[iid]["split"] == "field_changing" and g > 0.20)

    def twof(iid):
        it = items[iid]
        a = fa[(it["instance_id"], it["frozen_seed"], float(it["t_d"]))]
        g = (fi[iid]["p"]["obj_orig"] - a["lb"]) / max(a["lb"], 1.0)
        return reff(iid) or (K[iid]["split"] == "field_changing" and g > 0.20)

    ids = sorted(K)
    for iid in ids:
        check("logged K flag equals price > 0.20 (second path)",
              (K[iid]["refers_G-CERT"] == "True") == refk(iid)
              and (F[iid]["refers_G-CERT"] == "True") == reff(iid), iid)

    def cmp(block, what, main, second):
        ok = str(main) == str(second)
        SELF.append((block, what, main, second, ok))
        check("self-test [{}] {}".format(block, what), ok, (main, second))

    # A
    prim = [i for i in ids if st_name[K[i]["stratum"]] == "Primary"]
    cmp("A", "Primary costly at delta 0.20", resA[("Primary", "DeltaTwenty")]["costly"],
        sum(1 for i in prim if costly(i, 0.20) == 1))
    bld = [i for i in ids if st_name[K[i]["stratum"]] == "Buildings"]
    cmp("A", "Buildings costly applied on the known board at delta 0.10",
        resA[("Buildings", "DeltaTen")]["app_k"],
        sum(1 for i in bld if costly(i, 0.10) == 1 and not refk(i)))
    conf = [i for i in ids if st_name[K[i]["stratum"]] == "Confirmation"]
    cmp("A", "Confirmation disagreements (all priced)", resA[("Confirmation", "DeltaTwenty")]["dis"],
        sum(1 for i in conf if refk(i) != reff(i)))
    di = {}
    for i in prim:
        di[items[i]["instance_id"]] = dens[items[i]["instance_id"]]
    cmp("A", "Primary 0.20 x mean denominator over instances (bh)", bh1(descA["Primary"]["lvl20_i"]),
        bh1(0.20 * sum(di.values()) / len(di)))
    ra = {}
    for rec in json.loads((ANALYSIS / "ladder" / "rule_anchor.json").read_text()):
        ra[(Path(rec["instance_path"]).stem,
            ",".join(str(x) for x in (rec["frozen_seed"] or ())))] = float(rec["wwt_original_bh"])
    cmp("A", "Buildings mean no-AI weighted tardiness over priced (bh)",
        bh1(descA["Buildings"]["noai_mean"]),
        bh1(sum(ra[(items[i]["instance_id"], items[i]["frozen_seed"])] for i in bld) / len(bld)))
    # B
    dmg = {i: float(K[i]["damage_orig_bh"]) for i in ids}
    cmp("B", "pooled costly at X = 25 bh", resB[("Pooled", "XTwentyFive")]["costly"],
        sum(1 for i in ids if dmg[i] > 25.0))
    cmp("B", "pooled costly applied on the known board at X = 10 bh",
        resB[("Pooled", "XTen")]["app_k"], sum(1 for i in ids if dmg[i] > 10.0 and not refk(i)))
    cmp("B", "Primary low-cost referred with the second price (K) at X = 50 bh",
        resB[("Primary", "XFifty")]["low_two_k"],
        sum(1 for i in prim if dmg[i] <= 50.0 and twok(i)))
    cmp("B", "Buildings costly applied with the second price (FI) at X = 5 bh",
        resB[("Buildings", "XFive")]["two_app_f"],
        sum(1 for i in bld if dmg[i] > 5.0 and not twof(i)))
    # C
    for dtok, delta in DELTAS.items():
        cst = [i for i in ids if costly(i, delta) == 1]
        cmp("C", "instances with a costly proposal at delta {:.2f}".format(delta),
            resC[dtok]["n_inst"], len({K[i]["instance_id"] for i in cst}))
    n = resC["DeltaTwenty"]["n_inst"]
    cmp("C", "instance-level zero-event bound at delta 0.20",
        "{:.6f}".format(resC["DeltaTwenty"]["ub_inst"]), "{:.6f}".format(1 - 0.05 ** (1.0 / n)))
    # the sign-flip p at delta 0.10 by a brute-force enumeration written here
    cst = [i for i in ids if costly(i, 0.10) == 1]
    sums = {}
    for i in cst:
        d = float(not refk(i)) - float(not reff(i))
        sums[K[i]["instance_id"]] = sums.get(K[i]["instance_id"], 0.0) + d
    live = [v for v in sums.values() if v != 0.0]
    obs = abs(sum(live))
    hit = 0
    for signs in product((1, -1), repeat=len(live)):
        if abs(sum(s * v for s, v in zip(signs, live))) >= obs - 1e-9:
            hit += 1
    cmp("C", "sign-flip p, applied costly at delta 0.10 (brute force)",
        pfmt(resC["DeltaTen"]["sf_app"]["p"]), pfmt(hit / 2 ** len(live) if live else 1.0))
    # D
    low = [i for i in ids if costly(i, 0.20) == 0]
    lops = [i for i in low if items[i]["n_ops"] >= 1]
    cmp("D", "low-cost proposals with an operation at delta 0.20", resD["DeltaTwenty"]["ops"],
        len(lops))
    cmp("D", "of them referred by the certificate with full information",
        resD["DeltaTwenty"]["cert_f"]["k"], sum(1 for i in lops if reff(i)))
    cmp("D", "of them referred with the second price on the known board",
        resD["DeltaTwenty"]["two_k"]["k"], sum(1 for i in lops if twok(i)))
    # the interval by a bootstrap written here with the same seed and draw order as n2.Boot
    inst = sorted({items[i]["instance_id"] for i in items})
    index = {v: j for j, v in enumerate(inst)}
    rng = np.random.default_rng(20261026)
    idx = rng.integers(0, len(inst), size=(20000, len(inst)))
    num = np.zeros(len(inst))
    den = np.zeros(len(inst))
    for i in lops:
        j = index[items[i]["instance_id"]]
        den[j] += 1.0
        num[j] += 1.0 if reff(i) else 0.0
    ns, ds = num[idx].sum(axis=1), den[idx].sum(axis=1)
    r = ns[ds > 0] / ds[ds > 0]
    lo, hi = np.percentile(r, [2.5, 97.5])
    cmp("D", "95% interval of the full-information share over proposals with an operation",
        "{} to {}".format(pctv(resD["DeltaTwenty"]["cert_f"]["lo"]),
                          pctv(resD["DeltaTwenty"]["cert_f"]["hi"])),
        "{} to {}".format(pctv(float(lo)), pctv(float(hi))))
    # E
    cmp("E", "known board: bound exactly zero", resE[("Pooled", "K")]["zero"],
        sum(1 for i in ids if items[i]["dt_lb"] == 0.0))
    cmp("E", "known board: floor binds", resE[("Pooled", "K")]["binds"],
        sum(1 for i in ids if items[i]["dt_lb"] < 1.0))
    cmp("E", "full information: floor binds", resE[("Pooled", "FI")]["binds"],
        sum(1 for i in ids if fi[i]["p"]["lb"] < 1.0))
    cmp("E", "full information: bound exactly zero", resE[("Pooled", "FI")]["zero"],
        sum(1 for i in ids if fi[i]["p"]["lb"] == 0.0))
    # G: D-REL2 at the equal threshold with s2_site, from the two csv files directly
    s2site = {}
    with open(ANALYSIS / "N11_rows_direct.csv", encoding="utf-8") as fh:
        for x in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            if x["dataset"] == "direct_td" and x["item_id"] in K:
                oo, ref1 = float(x["obj_orig"]), float(x["ref1"])
                s2site[x["item_id"]] = (oo - ref1) / max(ref1, 1.0)

    def gref(iid, thr):
        v = fl(K[iid]["p_D-REL2"])
        return (v is not None and v > thr) or (K[iid]["split"] == "field_changing"
                                               and s2site[iid] > 0.20)

    g20 = [i for i in ids if costly(i, 0.20) == 0 and gref(i, 0.20)]
    cmp("G", "low-cost referred, D-REL2 at 0.20 with s2_site, delta 0.20",
        resG[("DeltaTwenty", "EqualThreshold", "site")]["fr"], len(g20))
    cmp("G", "benign among them", resG[("DeltaTwenty", "EqualThreshold", "site")]["ben"],
        sum(1 for i in g20 if K[i]["primary_class"] == "benign"))
    cmp("G", "costly applied, D-REL2 at 0.20 with s2_site, delta 0.10",
        resG[("DeltaTen", "EqualThreshold", "site")]["app"],
        sum(1 for i in ids if costly(i, 0.10) == 1 and not gref(i, 0.20)))


# --------------------------------------------------------------------------- #
# Backing rows                                                                 #
# --------------------------------------------------------------------------- #
def write_rows(recs):
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        fh.write("# N20 ({}): one row per priced proposal of the direct benchmark at t_d "
                 "(1,356); costly_d020 / costly_d010: 1 costly, 0 low-cost, empty undecided on "
                 "the relative level; damage_bh = executed original-field weighted tardiness "
                 "minus the no-AI anchor (no_ai_wt_bh); den_bh = max(OPT_full,base, 1 bh); lb_K "
                 "/ lb_FI = the bound the certificate divides by; p_K / p_FI = the certificate's "
                 "price (refers above 0.20); g_orig_K / g_orig_FI = the second price; "
                 "refers_two_* = certificate or (field edit and second price above "
                 "0.20)\n".format(VERSION))
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["item_id", "instance_id", "stratum", "primary_class", "edit_type", "n_ops",
                    "costly_d020", "costly_d010", "cost_lo", "cost_hi", "damage_bh", "den_bh",
                    "no_ai_wt_bh", "lb_K", "lb_FI", "p_K", "p_FI", "refers_K", "refers_FI",
                    "g_orig_K", "g_orig_FI", "refers_two_K", "refers_two_FI"])
        for r in recs:
            c2, c1 = n13.costly_of(r, 0.20), n13.costly_of(r, 0.10)
            w.writerow([r["item_id"], r["instance_id"], r["st"], r["primary_class"], r["split"],
                        r["n_ops"], "" if c2 is None else c2, "" if c1 is None else c1,
                        "{:.6f}".format(r["lo"]), "{:.6f}".format(r["hi"]),
                        "{:.4f}".format(r["dmg"]), "{:.4f}".format(r["den"]),
                        "{:.4f}".format(r["anchor"]), "{:.4f}".format(r["lb_k"]),
                        "{:.4f}".format(r["lb_f"]), "{:.6f}".format(r["p_G-CERT"]),
                        "{:.6f}".format(r["fi"]["p_G-CERT"]), int(r["ref_k"]), int(r["ref_f"]),
                        "{:.6f}".format(r["g_orig"]), "{:.6f}".format(r["sp_fi"]),
                        int(r["two_k"]), int(r["two_f"])])


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main(argv):
    selftest_only = "--selftest" in argv
    for k, p in IN20.items():
        if not Path(p).is_file() and k not in NOT_SHIPPED_OK:
            raise SystemExit("missing input {}: {}".format(k, p))
    hashes, items_dt, _pub, boot, fc = n13.load_inputs()
    check("60 bootstrap clusters, 20,000 replicates, n2 seed",
          boot.k == 60 and boot.idx.shape == (20000, 60) and n13.n2.SEED == 20261026)
    recs, by, spfi, site, _frecs = build(items_dt, fc, boot)
    suite = {it["item_id"]: it for it in n13.read_jsonl(n13.IN["suite"])}
    MD.extend(["# N20: the headline by stratum and on absolute cost levels ({})".format(VERSION),
               "",
               "Generated by `code/scripts/n20_stratum_abs.py` on cores 10-11 (one thread) from "
               "the logged results only: no solve, no model call, no GPU. It loads "
               "code/scripts/n16_robustness.py and n18_further_checks.py from their source with "
               "the core allowance set to cores 10-11 in memory (the files on disk are "
               "untouched) and, through n16, n13_fromlogs.py; it reuses their loaders, labels and "
               "cluster bootstrap (n2 seed {}, {} replicates, {} instance clusters). Macros: "
               "analysis/N20_macros.tex (prefix \\nTwenty), copied to "
               "manuscript/macros_n20.tex.".format(n13.n2.SEED, n13.n2.B_BOOT, boot.k), ""])
    # the published cells, by the reused functions and then by this script
    n16.section0(boot, recs)
    n18.section0(recs, by, spfi, site)
    section0(recs)
    resA, descA = block_a(recs)
    resB, _extraB = block_b(recs)
    resC = block_c(recs, suite)
    resD = block_d(boot, recs)
    resE = block_e(recs)
    block_f()
    resG, _g_other = block_g(boot, recs, by, site)
    selftest(resA, descA, resB, resC, resD, resE, resG)
    md("## Self-test (second code path)", "",
       "Each number below is recomputed from analysis/N11_rows_forecast.csv, "
       "results/n11_decision_time/items.jsonl, results/n11_forecast/fullinfo_direct.jsonl and "
       "anchors_direct.jsonl, and results/oracle_v1/brackets.jsonl with the csv and json "
       "modules (no n13/n16 loader, label or bootstrap), and compared with the main path; the "
       "sign-flip p is re-enumerated by brute force and the interval by a bootstrap written "
       "here with the n2 seed.", "")
    md_table(["block", "number", "main path", "second path", "equal"],
             [[b, w, m, s, "yes" if ok else "NO"] for b, w, m, s, ok in SELF])
    n_reused = n16.NCHECK[0] + n18.NCHECK[0] + len(n13.CHECKS)
    msg = ("[n20] {} macros, {} assertions passed (+{} in the reused functions: n16 {}, n18 {}, "
           "n13 {}); self-test {} of {} equal".format(
               len(NAMES), NCHECK[0], n_reused, n16.NCHECK[0], n18.NCHECK[0], len(n13.CHECKS),
               sum(1 for x in SELF if x[4]), len(SELF)))
    if selftest_only:
        print(msg + " (self-test mode: nothing written)")
        return 0
    paths = OrderedDict(list(n13.IN.items()) + list(IN20.items()))
    hashes20 = OrderedDict(hashes)
    hashes20.update((k, input_sha256(k, p)) for k, p in IN20.items())
    MD.extend(["## Inputs", ""] + ["- {} `{}` sha256 {}".format(
        k, Path(paths[k]).relative_to(ROOT), v) for k, v in hashes20.items()] + [""])
    MD.append("{} assertions passed in n20 (plus {} in the reused functions: {} n16, {} n18, {} "
              "n13); self-test {} of {} numbers equal on the second code path; {} macros.".format(
                  NCHECK[0], n_reused, n16.NCHECK[0], n18.NCHECK[0], len(n13.CHECKS),
                  sum(1 for x in SELF if x[4]), len(SELF), len(NAMES)))
    write_rows(recs)
    OUT_TEX.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    shutil.copyfile(OUT_TEX, OUT_MANU)
    OUT_MD.write_text("\n".join(MD) + "\n", encoding="utf-8")
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
