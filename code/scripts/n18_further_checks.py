#!/usr/bin/env python3
"""N18: from-logs further checks, recomputed from the stored rows only.

Design pre-specified before the run.  Blocks:

  A  cost-level sweep (delta 0.05 to 0.50): costly proposals applied by the certificate on
     the known board (K) and with full information (FI), alone, with the second price, and on
     the common denominator, with cluster-bootstrap intervals and the paired K - FI difference;
  B  price margins of the certificate on K and with FI: the 2 x 2 table of dispositions, the
     price quartiles of the 186 costly proposals, the near-threshold subsets, Spearman's rho;
  C  where the 18 applied costly proposals come from, and the known-share distribution of
     field edits and of costly proposals;
  D  referral by equivalence to the reference translation for the eight Table 6 cells, with a
     cluster-bootstrap interval per cell;
  E  a scale for weighted business hours: the no-AI schedule's weighted tardiness over the
     population of the Claude Opus 5 damage band;
  F  the approver who approves exactly the referrals with stated acceptance (named, not
     recomputed: N13 section A and app_n13_n14.tex);
  G  the points outside the drawn window of fig_price_oracle_dt.py;
  H  the forecast shortfall by stratum (N13 section D, recomputed and asserted);
  I  correct translations that edit a priority or a time window under the second price and its
     site-schedule variant, and the 36 costly field edits behind the LLMs;
  J  (follow-up) the headline read by the later share L, the share of the window's orders that
     arrive after t_d (the information gap), in four bands fixed before agreement was read.

Every number comes from result files on disk: no solve, no model call, no GPU.  The script
imports code/scripts/n16_robustness.py (l1-n16-robustness-3, frozen; imported, never edited)
for its loaders and helpers, and through it n13_fromlogs.py (core allowance set to 14-15 in
memory only).  Published counts are asserted before any new number; a drifted input aborts.

Outputs: analysis/N18_macros.tex (prefix \\nEighteen, copied to manuscript/macros_n18.tex),
analysis/N18_summary.md, analysis/N18_fig_delta_sweep.csv, analysis/N18_fig_price_k_fi.csv,
analysis/N18_fig_fidelity_split.csv, analysis/N18_fig_later_share.csv.
Run: OMP_NUM_THREADS=1 taskset -c 14-15 python3 code/scripts/n18_further_checks.py
Version: l1-n18-further-2 (adds block J; every macro of version 1 keeps its value, asserted
against the macros file on disk before it is overwritten)
"""
import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_v] = "1"

import ast  # noqa: E402
import csv  # noqa: E402
import json  # noqa: E402
import shutil  # noqa: E402
import statistics  # noqa: E402
import sys  # noqa: E402
from collections import Counter, OrderedDict, defaultdict  # noqa: E402
from fractions import Fraction  # noqa: E402
from pathlib import Path  # noqa: E402

ALLOWED_CORES = {14, 15}
_aff = set(os.sched_getaffinity(0))
if not _aff <= ALLOWED_CORES and not os.environ.get("CERTIGATE_ANY_CORES"):
    raise SystemExit("REFUSING TO RUN: affinity {} is not inside cores 14-15 "
                     "(run under taskset -c 14-15)".format(sorted(_aff)))

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import n16_robustness as n16  # noqa: E402  (frozen; imported for loaders and helpers)
from scipy import stats as sstats  # noqa: E402

n13 = n16.n13
np = n13.np
D = n13.D
e1dg = n13.e1dg

VERSION = "l1-n18-further-2"
ROOT = n13.ROOT
ANALYSIS = n13.ANALYSIS
RESULTS = n13.RESULTS
OUT_TEX = ANALYSIS / "N18_macros.tex"
OUT_MANU = ROOT / "manuscript" / "macros_n18.tex"
OUT_MD = ANALYSIS / "N18_summary.md"
OUT_SWEEP = ANALYSIS / "N18_fig_delta_sweep.csv"
OUT_PRICE = ANALYSIS / "N18_fig_price_k_fi.csv"
OUT_FID = ANALYSIS / "N18_fig_fidelity_split.csv"
OUT_LATER = ANALYSIS / "N18_fig_later_share.csv"
FIG = ROOT / "manuscript" / "figures"
IN18 = OrderedDict([
    ("n16_macros", ANALYSIS / "N16_macros.tex"),
    ("n15_macros", ANALYSIS / "N15_macros.tex"),
    ("n13_macros", ANALYSIS / "N13_macros.tex"),
    ("n11_macros", ANALYSIS / "N11_macros.tex"),
    ("n11f_paired_macros", ANALYSIS / "N11F_paired_macros.tex"),
    ("n14_rows", ANALYSIS / "N14_rows.csv"),
    ("fig_price_oracle_dt", FIG / "fig_price_oracle_dt.py"),
    ("fig_price_oracle", FIG / "fig_price_oracle.py"),
    ("n13_summary", ANALYSIS / "N13_summary.md"),
    ("app_n13_n14", ROOT / "manuscript" / "drafts" / "app_n13_n14.tex"),
    ("app_limitations", ROOT / "manuscript" / "drafts" / "app_limitations.tex"),
])

#: Inputs the public release does not carry (two supplement drafts, two figure scripts,
#: and N16's figure script). A missing one is recorded as "not shipped" in the provenance
#: block, and the run goes on.
NOT_SHIPPED_OK = ("app_n13_n14", "app_limitations", "fig_price_oracle_dt", "fig_price_oracle",
                  "fig3_dt_script")
#: The window, the offset, the threshold and the designs of fig_price_oracle(_dt).py, as
#: block G asserts them; block G uses these values when the figure scripts are absent.
FIG_WINDOW = {"LO": -0.05, "HI": 1.0, "OFFSET": 0.05, "TAU": 0.20}
FIG_DESIGNS = [("G-CERT", "p_K_G-CERT"), ("D-REL2", "p_K_D-REL2")]


def input_sha256(key, path):
    """The SHA-256 of an input, or "not shipped" for one the public release does not carry."""
    if key in NOT_SHIPPED_OK and not Path(path).is_file():
        return "not shipped"
    return n13.sha256(path)

TAU = n13.TAU
FLOOR = D.FLOOR_BH
CERT = "G-CERT"
SWEEP = OrderedDict((tok, round(0.05 * (i + 1), 2)) for i, tok in enumerate(
    ("Five", "Ten", "Fifteen", "Twenty", "TwentyFive", "Thirty", "ThirtyFive", "Forty",
     "FortyFive", "Fifty")))
A_MACRO_DELTAS = ("Five", "Thirty", "Fifty")
VARIANTS = OrderedDict([("Cert", "certificate alone"),
                        ("CertTwo", "certificate with the second price"),
                        ("Common", "certificate on the common denominator")])
BANDS = OrderedDict([("Low", "known share at most 50%"), ("Mid", "above 50% to 80%"),
                     ("High", "above 80%")])
ST_TOK = n13.ST_TOK
STRATA = D.STRATA
CLS_TOK = OrderedDict([("benign", "Benign"), ("V1", "VOne"), ("V2", "VTwo"), ("V3", "VThree"),
                       ("V4", "VFour"), ("V5", "VFive"), ("V6", "VSix")])
SPLIT_TOK = {"field_changing": "Field", "sequencing_only": "Seq", "empty": "Empty",
             "other": "Other"}

LINES = ["% N18 macros ({}); generated by code/scripts/n18_further_checks.py from the logged "
         "results only (no solve, no model call)".format(VERSION)]
NAMES = set()
MD = []
NCHECK = [0]
OLD_KEPT = [(0, 0, 0)]

grp, pct, pctv, pctp, pctpv, ppv, frac = (n16.grp, n16.pct, n16.pctv, n16.pctp, n16.pctpv,
                                          n16.ppv, n16.frac)
qstats, cost_class, site_price = n16.qstats, n16.cost_class, n16.site_price


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def check(what, ok, detail=""):
    if not ok:
        raise SystemExit("[n18] ASSERTION FAILED: {} ({})".format(what, detail))
    NCHECK[0] += 1


def add(name, value):
    full = "nEighteen" + name
    if not full.isalpha():
        raise SystemExit("macro name not alphabetic: " + full)
    if full in NAMES:
        raise SystemExit("duplicate macro " + full)
    NAMES.add(full)
    LINES.append("\\newcommand{\\" + full + "}{" + str(value) + "}")


def md(*lines):
    MD.extend(lines)


def md_table(head, body):
    MD.append("| " + " | ".join(str(h) for h in head) + " |")
    MD.append("|" + "|".join("---" for _ in head) + "|")
    for row in body:
        MD.append("| " + " | ".join("" if c is None else str(c) for c in row) + " |")
    MD.append("")


def facts(items):
    md("Facts the paper may state:", "")
    for j, f in enumerate(items, 1):
        md("{}. {}".format(j, f))
    md("")


def ci_str(k, n, lo, hi):
    return "{} [{}, {}]".format(frac(k, n), pctpv(lo), pctpv(hi))


def pp_str(d, lo, hi):
    return "{} [{}, {}]".format(ppv(d), ppv(lo), ppv(hi))


def f4(x):
    return "" if x is None else "{:.4f}".format(x)


def band_of(ks):
    if ks <= 0.5:
        return "Low"
    if ks <= 0.8:
        return "Mid"
    return "High"


def family_tok(fam):
    parts = fam.split("_")[1:]
    return "".join(p.capitalize() for p in parts if p.isalpha())


def lit_assign(path, names):
    """Literal values of module-level assignments in a figure script (never imported)."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if isinstance(tgt, ast.Name) and tgt.id in names:
                out[tgt.id] = ast.literal_eval(node.value)
            elif isinstance(tgt, ast.Tuple) and all(isinstance(e, ast.Name) for e in tgt.elts) \
                    and any(e.id in names for e in tgt.elts):
                vals = ast.literal_eval(node.value)
                for e, v in zip(tgt.elts, vals):
                    if e.id in names:
                        out[e.id] = v
    return out


def macros_of(path):
    return n13.macros_of(path)


# --------------------------------------------------------------------------- #
# 0. Published counts                                                          #
# --------------------------------------------------------------------------- #
def section0(recs, by, spfi, site):
    m15 = macros_of(IN18["n15_macros"])
    m16 = macros_of(IN18["n16_macros"])
    iss = [r for r in by.values() if r["issuable"]]
    check("1,723 issuable instructions", len(iss) == 1723, len(iss))
    check("1,356 priced proposals", len(recs) == 1356 and m15["nFifteenPriced"] == "1{,}356",
          len(recs))
    c20 = [r for r in recs if n13.costly_of(r, 0.20) == 1]
    l20 = [r for r in recs if n13.costly_of(r, 0.20) == 0]
    c10 = [r for r in recs if n13.costly_of(r, 0.10) == 1]
    l10 = [r for r in recs if n13.costly_of(r, 0.10) == 0]
    check("186 costly and 1,170 low-cost at delta 0.20",
          (len(c20), len(l20)) == (186, 1170) and m15["nFifteenCostlyTwenty"] == "186"
          and m15["nFifteenLowTwenty"] == "1{,}170", (len(c20), len(l20)))
    check("208 costly and 1,148 low-cost at delta 0.10", (len(c10), len(l10)) == (208, 1148),
          (len(c10), len(l10)))
    rk = {r["item_id"] for r in c20 if n13.refers(r, CERT)}
    rf = {r["item_id"] for r in c20 if n13.refers(r["fi"], CERT)}
    check("168 costly referred on K and the same 168 with FI",
          len(rk) == 168 and rk == rf and m16["nSixteenCertRefKTwenty"] == "168"
          and m16["nSixteenCertRefFITwenty"] == "168" and m16["nSixteenCertRefBothTwenty"] == "168",
          (len(rk), len(rf)))
    applied = [r for r in c20 if r["item_id"] not in rk]
    check("18 costly applied, all field edits, all V4",
          len(applied) == 18 and all(r["split"] == "field_changing" for r in applied)
          and all(r["primary_class"] == "V4" for r in applied)
          and m15["nFifteenCertMissTwenty"] == "18" and m15["nFifteenCertMissFieldTwenty"] == "18"
          and m15["nFifteenCertMissVFourTwenty"] == "18", len(applied))
    frk = sum(1 for r in l20 if n13.refers(r, CERT))
    frf = sum(1 for r in l20 if n13.refers(r["fi"], CERT))
    check("15 and 35 low-cost referred on K and with FI",
          (frk, frf) == (15, 35) and m15["nFifteenCertFrTwenty"] == "15"
          and m15["nFifteenCertFrFITwenty"] == "35", (frk, frf))
    two = [r for r in l20 if n16.sp_flag(r, CERT)]
    two_miss = [r for r in c20 if not n16.sp_flag(r, CERT)]
    check("22 low-cost referred and 0 costly applied with the second price",
          (len(two), len(two_miss)) == (22, 0) and m15["nFifteenCertTwoFrTwenty"] == "22"
          and m15["nFifteenCertTwoMissTwenty"] == "0", (len(two), len(two_miss)))
    # the published flag is the price above tau on both readings
    for r in recs:
        check("G-CERT flag on K = price > 0.20", n13.refers(r, CERT) == (r["p_G-CERT"] > TAU),
              r["item_id"])
        check("G-CERT flag with FI = price > 0.20",
              n13.refers(r["fi"], CERT) == (r["fi"]["p_G-CERT"] > TAU), r["item_id"])
    # the site-schedule variant reproduces N16 block I1
    for dtok, delta in (("Twenty", 0.20), ("Ten", 0.10)):
        cst = [r for r in recs if n13.costly_of(r, delta) == 1]
        low = [r for r in recs if n13.costly_of(r, delta) == 0]

        def fl(r):
            return n13.refers(r, CERT) or (r["split"] == "field_changing" and site[r["item_id"]] > TAU)
        miss = sum(1 for r in cst if not fl(r))
        fr = sum(1 for r in low if fl(r))
        check("s2_site cells equal N16 I1 at delta {}".format(delta),
              (str(miss), str(fr)) == (m16["nSixteenICertSiteMiss" + dtok],
                                       m16["nSixteenICertSiteFr" + dtok]), (miss, fr))
    md("## 0. Published counts asserted before any new number", "",
       "Direct benchmark at the decision instant (analysis/N11_rows_forecast.csv, readings K and "
       "FI; results/n11_decision_time/items.jsonl): 1,723 issuable instructions, 1,356 priced "
       "proposals; at delta = 0.20, 186 costly and 1,170 low-cost; at delta = 0.10, 208 costly and "
       "1,148 low-cost. The certificate refers the same 168 costly proposals on K and with FI and "
       "applies 18 (all field edits of class V4); it refers 15 low-cost proposals on K and 35 with "
       "FI; with the second price it applies none and refers 22 low-cost proposals. Each count "
       "equals the N15/N16 macros (asserted); the published flag equals price > 0.20 on every "
       "row of both readings (asserted). The second price with FI (n13.j_records, the FI board's "
       "own anchor bound) and the site-schedule variant s2_site (N16 block I) are rebuilt and "
       "asserted against N13 section J and N16 block I.", "")
    return c20, applied


# --------------------------------------------------------------------------- #
# A. Cost-level sweep                                                          #
# --------------------------------------------------------------------------- #
def block_a(boot, recs, spfi, frecs):
    fby = {r["item_id"]: r for r in frecs}
    check("common-denominator records cover the 1,356", set(fby) == {r["item_id"] for r in recs})

    def flags(var):
        if var == "Cert":
            return (lambda r: n13.refers(r, CERT), lambda r: n13.refers(r["fi"], CERT))
        if var == "CertTwo":
            return (lambda r: n13.refers(r, CERT) or (r["split"] == "field_changing" and r["sp"]),
                    lambda r: n13.refers(r["fi"], CERT) or (r["split"] == "field_changing"
                                                           and spfi[r["item_id"]] > TAU))
        return (lambda r: fby[r["item_id"]]["c_bh_k"] / fby[r["item_id"]]["den"] > TAU,
                lambda r: fby[r["item_id"]]["c_bh_f"] / fby[r["item_id"]]["den"] > TAU)

    res = OrderedDict()
    rows_csv = []
    for dtok, delta in SWEEP.items():
        costly = [r for r in recs if n13.costly_of(r, delta) == 1]
        low = [r for r in recs if n13.costly_of(r, delta) == 0]
        und = len(recs) - len(costly) - len(low)
        ninst = len({r["instance_id"] for r in costly})
        for c in costly:
            check("common records share the realised cost bracket",
                  fby[c["item_id"]]["lo"] == c["lo"] and fby[c["item_id"]]["hi"] == c["hi"])
        for var in VARIANTS:
            fk, ff = flags(var)
            mk = [not fk(r) for r in costly]
            mf = [not ff(r) for r in costly]
            klo, khi = boot.ci(costly, mk) if costly else (None, None)
            flo, fhi = boot.ci(costly, mf) if costly else (None, None)
            dm, dlo, dhi = n13.paired_ci(boot, costly, [float(x) for x in mk],
                                         [float(x) for x in mf])
            o = OrderedDict(delta=delta, costly=len(costly), low=len(low), und=und, ninst=ninst,
                            mk=sum(mk), mf=sum(mf), klo=klo, khi=khi, flo=flo, fhi=fhi,
                            both=sum(1 for a, b in zip(mk, mf) if a and b),
                            konly=sum(1 for a, b in zip(mk, mf) if a and not b),
                            fonly=sum(1 for a, b in zip(mk, mf) if b and not a),
                            d=dm, dlo=dlo, dhi=dhi,
                            frk=sum(1 for r in low if fk(r)), frf=sum(1 for r in low if ff(r)))
            res[(var, dtok)] = o
            rows_csv.append(["{:.2f}".format(delta), var, o["costly"], o["low"], o["und"], ninst,
                             o["mk"], f4(o["mk"] / o["costly"]), f4(klo), f4(khi), o["mf"],
                             f4(o["mf"] / o["costly"]), f4(flo), f4(fhi), o["both"], o["konly"],
                             o["fonly"], "{:.4f}".format(100 * dm), "{:.4f}".format(100 * dlo),
                             "{:.4f}".format(100 * dhi), o["frk"], o["frf"]])
    # the published rows
    m13 = macros_of(IN18["n13_macros"])
    m16 = macros_of(IN18["n16_macros"])
    m15 = macros_of(IN18["n15_macros"])
    mp = macros_of(IN18["n11f_paired_macros"])
    o = res[("Cert", "Twenty")]
    check("sweep row 0.20, certificate: 186, 18 / 18, difference 0.0 [0.0, 0.0], 15 / 35",
          (o["costly"], o["low"], o["und"], o["mk"], o["mf"], o["konly"], o["fonly"], ppv(o["d"]),
           ppv(o["dlo"]), ppv(o["dhi"]), o["frk"], o["frf"]) ==
          (186, 1170, 0, 18, 18, 0, 0, "0.0", "0.0", "0.0", 15, 35), o)
    check("sweep row 0.20 share equals \\nFifteenCertMissShareTwenty",
          pct(o["mk"], o["costly"]) == m15["nFifteenCertMissShareTwenty"])
    o = res[("Cert", "Ten")]
    check("sweep row 0.10, certificate: 208, 25 / 28, -1.4 [-5.6, 1.7], 0 / 23",
          (o["costly"], o["low"], o["mk"], o["mf"], ppv(o["d"]), ppv(o["dlo"]), ppv(o["dhi"]),
           o["frk"], o["frf"]) ==
          (208, 1148, 25, 28, mp["nElevenPairedCertMissDiffDeltaTen"],
           mp["nElevenPairedCertMissDiffDeltaTenLo"], mp["nElevenPairedCertMissDiffDeltaTenHi"],
           int(m15["nFifteenCertFrTen"]), int(m15["nFifteenCertFrFITen"]))
          and (ppv(o["d"]), ppv(o["dlo"]), ppv(o["dhi"])) == ("-1.4", "-5.6", "1.7")
          and m16["nSixteenGCertDiffTen"] == "-1.4", o)
    for dtok in ("Twenty", "Ten"):
        o = res[("CertTwo", dtok)]
        b = "nThirteenJPub{}CertSecondPriceFieldOnlyDelta" + dtok
        check("sweep row {} with the second price equals N13 section J (K and FI)".format(dtok),
              (str(o["mk"]), str(o["frk"]), str(o["mf"]), str(o["frf"])) ==
              (m13[b.format("K") + "Miss"], m13[b.format("K") + "Fr"],
               m13[b.format("FI") + "Miss"], m13[b.format("FI") + "Fr"]), o)
        check("second-price share intervals on K equal N13 section J ({})".format(dtok),
              (pctv(o["klo"]), pctv(o["khi"])) == (m13[b.format("K") + "MissLo"],
                                                   m13[b.format("K") + "MissHi"])
              and (pctv(o["flo"]), pctv(o["fhi"])) == (m13[b.format("FI") + "MissLo"],
                                                       m13[b.format("FI") + "MissHi"]), o)
        o = res[("Common", dtok)]
        c = "nSixteenCommonCert"
        check("sweep row {} on the common denominator equals N16 block C".format(dtok),
              (str(o["mk"]), str(o["mf"]), ppv(o["d"]), ppv(o["dlo"]), ppv(o["dhi"]),
               str(o["costly"])) ==
              (m16[c + "MissK" + dtok], m16[c + "MissFI" + dtok], m16[c + "Diff" + dtok],
               m16[c + "DiffLo" + dtok], m16[c + "DiffHi" + dtok], m16[c + "Costly" + dtok]), o)
    check("published common-denominator cells 20 / 18 and 40 / 35",
          (res[("Common", "Twenty")]["mk"], res[("Common", "Twenty")]["mf"],
           res[("Common", "Ten")]["mk"], res[("Common", "Ten")]["mf"]) == (20, 18, 40, 35))
    with open(OUT_SWEEP, "w", newline="", encoding="utf-8") as fh:
        fh.write("# N18 ({}): cost-level sweep of the direct benchmark at the decision instant, "
                 "1,356 priced proposals; variant Cert = the certificate's flag (price > 0.20), "
                 "CertTwo = with the second price g_orig > 0.20 on field edits (K: the known "
                 "board's anchor bound; FI: the full-information board's), Common = the "
                 "certificate's price in bh divided by the realised-cost denominator "
                 "max(OPT_full,base, 1 bh) > 0.20; applied = costly not referred; shares with "
                 "95% cluster-bootstrap intervals over instances (n2 seed, 20,000 replicates); "
                 "diff = applied share K minus FI in percentage points, paired cluster "
                 "bootstrap\n".format(VERSION))
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["delta", "variant", "costly", "low_cost", "undecided", "costly_instances",
                    "applied_K", "applied_K_share", "applied_K_lo", "applied_K_hi", "applied_FI",
                    "applied_FI_share", "applied_FI_lo", "applied_FI_hi", "applied_both",
                    "applied_K_only", "applied_FI_only", "diff_pp", "diff_lo_pp", "diff_hi_pp",
                    "lowcost_referred_K", "lowcost_referred_FI"])
        w.writerows(rows_csv)
    # macros
    for dtok in A_MACRO_DELTAS:
        o0 = res[("Cert", dtok)]
        add("ACostlyDelta" + dtok, grp(o0["costly"]))
        add("ALowDelta" + dtok, grp(o0["low"]))
        add("AUndecidedDelta" + dtok, grp(o0["und"]))
        add("ACostlyInstancesDelta" + dtok, o0["ninst"])
        for var in VARIANTS:
            o = res[(var, dtok)]
            p = "A" + var
            add(p + "MissKDelta" + dtok, o["mk"])
            add(p + "MissKShareDelta" + dtok, pct(o["mk"], o["costly"]))
            add(p + "MissKLoDelta" + dtok, pctv(o["klo"]))
            add(p + "MissKHiDelta" + dtok, pctv(o["khi"]))
            add(p + "MissFIDelta" + dtok, o["mf"])
            add(p + "MissFIShareDelta" + dtok, pct(o["mf"], o["costly"]))
            add(p + "MissFILoDelta" + dtok, pctv(o["flo"]))
            add(p + "MissFIHiDelta" + dtok, pctv(o["fhi"]))
            add(p + "MissBothDelta" + dtok, o["both"])
            add(p + "DiffDelta" + dtok, ppv(o["d"]))
            add(p + "DiffLoDelta" + dtok, ppv(o["dlo"]))
            add(p + "DiffHiDelta" + dtok, ppv(o["dhi"]))
            add(p + "FrKDelta" + dtok, o["frk"])
            add(p + "FrFIDelta" + dtok, o["frf"])
    mx = OrderedDict()
    for var in VARIANTS:
        cand = [(abs(round(100 * res[(var, t)]["d"], 1)), t) for t in SWEEP]
        best = max(c[0] for c in cand)
        ties = [t for a, t in cand if a == best]
        t = ties[0]
        o = res[(var, t)]
        mx[var] = (t, ties, o)
        add("A" + var + "MaxAbsDiff", ppv(o["d"]))
        add("A" + var + "MaxAbsDiffLo", ppv(o["dlo"]))
        add("A" + var + "MaxAbsDiffHi", ppv(o["dhi"]))
        add("A" + var + "MaxAbsDiffDelta", "{:.2f}".format(SWEEP[t]))
        add("A" + var + "MaxAbsDiffMissK", o["mk"])
        add("A" + var + "MaxAbsDiffMissFI", o["mf"])
        add("A" + var + "MaxAbsDiffCostly", o["costly"])
    # summary
    md("## A. Cost-level sweep (delta 0.05 to 0.50, tau fixed at 0.20)", "",
       "Costly at delta = realised cost on the original values above delta (lower end of the "
       "bracket above delta); low-cost = upper end at most delta; undecided = the bracket "
       "straddles delta (in neither). Applied = costly and not referred. Three variants: the "
       "certificate's own flag (price > 0.20 on K and with FI); the same with the second price "
       "added on field edits (g_orig > 0.20; on K against the known board's anchor bound, with FI "
       "against the full-information board's anchor bound, n13.j_records); the certificate's "
       "price in weighted bh divided by the realised-cost denominator max(OPT_full,base, 1 bh) "
       "of the untouched window, > 0.20 (N16 block C, n13.section_f's records). Intervals: 95% "
       "cluster bootstrap over the 60 instances (n2 seed 20261026, 20,000 replicates); "
       "difference = applied share on K minus with FI, percentage points, paired cluster "
       "bootstrap (n13.paired_ci). File: analysis/N18_fig_delta_sweep.csv. The 0.20 and 0.10 "
       "rows equal the published cells (asserted: N15, N16 blocks C and G(3), N11F_paired, N13 "
       "section J).", "")
    for var, vname in VARIANTS.items():
        md("### {}".format(vname[0].upper() + vname[1:]), "")
        body = []
        for dtok, delta in SWEEP.items():
            o = res[(var, dtok)]
            body.append(["{:.2f}".format(delta), o["costly"], grp(o["low"]).replace("{,}", ","),
                         o["und"], o["ninst"], ci_str(o["mk"], o["costly"], o["klo"], o["khi"]),
                         ci_str(o["mf"], o["costly"], o["flo"], o["fhi"]), o["both"], o["konly"],
                         o["fonly"], pp_str(o["d"], o["dlo"], o["dhi"]), o["frk"], o["frf"]])
        md_table(["delta", "costly", "low-cost", "undecided", "instances (costly)",
                  "applied K [95% CI]", "applied FI [95% CI]", "both", "K only", "FI only",
                  "K - FI (pp) [95% CI]", "low-cost referred K", "low-cost referred FI"], body)
    md("Largest absolute K - FI difference over the sweep: " + "; ".join(
        "{}: {} pp at delta {:.2f} ({} against {} of {}; interval {} to {}){}".format(
            VARIANTS[v], ppv(o["d"]), SWEEP[t], o["mk"], o["mf"], o["costly"], ppv(o["dlo"]),
            ppv(o["dhi"]), "" if len(ties) == 1 else " (tied at {})".format(
                ", ".join("{:.2f}".format(SWEEP[x]) for x in ties)))
        for v, (t, ties, o) in mx.items()) + ".", "")
    # facts
    c = [res[("Cert", t)] for t in SWEEP]
    zero_cert = [t for t in SWEEP if res[("Cert", t)]["konly"] == 0
                 and res[("Cert", t)]["fonly"] == 0]
    ci_excl = {v: [t for t in SWEEP if res[(v, t)]["dlo"] > 0 or res[(v, t)]["dhi"] < 0]
               for v in VARIANTS}
    fx = []
    mu = max(o["und"] for o in c)
    fx.append("Over the cost levels 0.05 to 0.50 the number of costly proposals falls from {} to "
              "{} of 1,356{}.".format(c[0]["costly"], c[-1]["costly"],
                                     ", and no realised-cost bracket straddles any of the levels"
                                     if mu == 0 else " (at most {} undecided)".format(mu)))
    fx.append("The certificate alone applies the same costly proposals on K and with full "
              "information at {} of the 10 cost levels ({}).".format(
                  len(zero_cert), ", ".join("{:.2f}".format(SWEEP[t]) for t in zero_cert)))
    for v in VARIANTS:
        t, ties, o = mx[v]
        excl = ci_excl[v]
        fx.append("For the {}, the largest absolute difference in applied share between the "
                  "known board and full information is {} percentage points, at delta = {:.2f} "
                  "({} against {} of {} costly proposals, interval {} to {}). The paired interval "
                  "excludes zero at {} of the 10 cost levels{}.".format(
                      VARIANTS[v], ppv(o["d"]), SWEEP[t], o["mk"],
                      o["mf"], o["costly"], ppv(o["dlo"]), ppv(o["dhi"]), len(excl),
                      " ({})".format(", ".join("{:.2f}".format(SWEEP[x]) for x in excl))
                      if excl else ""))
    t2 = [res[("CertTwo", t)] for t in SWEEP]
    fx.append("With the second price the certificate applies {} costly proposals on K and {} with "
              "full information at delta = 0.20, and at most {} on K and {} with full "
              "information at any cost level of the sweep.".format(
                  res[("CertTwo", "Twenty")]["mk"], res[("CertTwo", "Twenty")]["mf"],
                  max(o["mk"] for o in t2), max(o["mf"] for o in t2)))
    facts(fx)
    return res, mx


# --------------------------------------------------------------------------- #
# B. Price margins and near-threshold agreement                                #
# --------------------------------------------------------------------------- #
def block_b(boot, recs, c20):
    pk = {r["item_id"]: r["p_G-CERT"] for r in recs}
    pf = {r["item_id"]: r["fi"]["p_G-CERT"] for r in recs}
    check("both prices logged on all 1,356", all(v is not None for v in pk.values())
          and all(v is not None for v in pf.values()))
    rk = {r["item_id"]: n13.refers(r, CERT) for r in recs}
    rf = {r["item_id"]: n13.refers(r["fi"], CERT) for r in recs}
    pops = OrderedDict([("All", recs), ("Costly", c20),
                        ("Low", [r for r in recs if n13.costly_of(r, 0.20) == 0])])
    check("costly + low-cost = priced at 0.20 (no undecided)",
          len(pops["Costly"]) + len(pops["Low"]) == len(recs))
    body = []
    cells = OrderedDict([("BothRefer", (True, True)), ("KOnlyRefer", (True, False)),
                         ("FIOnlyRefer", (False, True)), ("NeitherRefer", (False, False))])
    tab = {}
    for ptok, sel in pops.items():
        row = [{"All": "all priced", "Costly": "costly at 0.20",
                "Low": "low-cost at 0.20"}[ptok], len(sel)]
        for ct, (a, b) in cells.items():
            k = sum(1 for r in sel if rk[r["item_id"]] == a and rf[r["item_id"]] == b)
            tab[(ptok, ct)] = k
            add("B" + ptok + ct, grp(k))
            row.append(k)
        dis = tab[(ptok, "KOnlyRefer")] + tab[(ptok, "FIOnlyRefer")]
        add("B" + ptok + "Disagree", dis)
        row.append(dis)
        body.append(row)
    check("2 x 2 sums", sum(tab[("All", c)] for c in cells) == len(recs)
          and all(tab[("All", c)] == tab[("Costly", c)] + tab[("Low", c)] for c in cells))
    check("2 x 2 margins equal the published 168 / 168 and 15 / 35",
          tab[("Costly", "BothRefer")] == 168 and tab[("Costly", "KOnlyRefer")] == 0
          and tab[("Costly", "FIOnlyRefer")] == 0
          and tab[("Low", "BothRefer")] + tab[("Low", "KOnlyRefer")] == 15
          and tab[("Low", "BothRefer")] + tab[("Low", "FIOnlyRefer")] == 35)
    add("BAllN", grp(len(recs)))
    dis = sorted((r for r in recs if rk[r["item_id"]] != rf[r["item_id"]]),
                 key=lambda r: r["item_id"])
    dcls = Counter(r["primary_class"] for r in dis)
    dsp = Counter(r["split"] for r in dis)
    for c, ct in CLS_TOK.items():
        add("BDisagree" + ct, dcls.get(c, 0))
    for sp, st in SPLIT_TOK.items():
        add("BDisagree" + st, dsp.get(sp, 0))
    dkonly = [r for r in dis if rk[r["item_id"]]]
    fz = [r for r in dis if not rk[r["item_id"]] and r["t_d"] == 0.0 and pk[r["item_id"]] == 0.0]
    add("BDisagreeInstances", len({r["instance_id"] for r in dis}))
    add("BFIOnlyZeroKAtStart", len(fz))
    add("BFIOnlyZeroKAtStartInstances", len({r["instance_id"] for r in fz}))
    add("BDisagreeKOnlyBenign", sum(1 for r in dkonly if r["primary_class"] == "benign"))
    add("BDisagreeFIOnlyBenign", sum(1 for r in dis if not rk[r["item_id"]]
                                     and r["primary_class"] == "benign"))
    add("BDisagreeTdZero", sum(1 for r in dis if r["t_d"] == 0.0))
    # prices of the 186 costly
    qk = qstats([pk[r["item_id"]] for r in c20])
    qf = qstats([pf[r["item_id"]] for r in c20])
    for nm, a, b in zip(("Min", "QOne", "Median", "QThree", "Max"), qk, qf):
        add("BCostlyPK" + nm, "{:.3f}".format(a))
        add("BCostlyPFI" + nm, "{:.3f}".format(b))
    bins = OrderedDict([("AtMostTwenty", lambda p: p <= 0.20),
                        ("TwentyToThirty", lambda p: 0.20 < p <= 0.30),
                        ("ThirtyToForty", lambda p: 0.30 < p <= 0.40),
                        ("AboveForty", lambda p: p > 0.40)])
    bin_rows = []
    for rd, prices in (("PK", pk), ("PFI", pf)):
        row = ["K" if rd == "PK" else "FI"]
        tot = 0
        for bt, fn in bins.items():
            k = sum(1 for r in c20 if fn(prices[r["item_id"]]))
            tot += k
            add("BCostly" + rd + bt, k)
            row.append(k)
        check("price bins partition the 186 ({})".format(rd), tot == 186, tot)
        bin_rows.append(row)
    check("costly at most 0.20 on K = the 18 applied", bin_rows[0][1] == 18 and bin_rows[1][1] == 18)
    # near-threshold subsets (defined by price alone)
    near = OrderedDict([("Wide", (0.10, 0.30)), ("Narrow", (0.15, 0.25))])
    near_rows = []
    near_res = {}
    for nt, (a, b) in near.items():
        sel = [r for r in recs if a <= pk[r["item_id"]] <= b or a <= pf[r["item_id"]] <= b]
        agree = [rk[r["item_id"]] == rf[r["item_id"]] for r in sel]
        lo, hi = boot.ci(sel, agree)
        nc = sum(1 for r in sel if n13.costly_of(r, 0.20) == 1)
        nc10 = sum(1 for r in sel if n13.costly_of(r, 0.10) == 1)
        cagree = [rk[r["item_id"]] == rf[r["item_id"]] for r in sel
                  if n13.costly_of(r, 0.20) == 1]
        lagree = [rk[r["item_id"]] == rf[r["item_id"]] for r in sel
                  if n13.costly_of(r, 0.20) == 0]
        ninst = len({r["instance_id"] for r in sel})
        both_in = sum(1 for r in sel if a <= pk[r["item_id"]] <= b and a <= pf[r["item_id"]] <= b)
        near_res[nt] = (len(sel), nc, sum(agree), lo, hi)
        add("BNear" + nt + "N", grp(len(sel)))
        add("BNear" + nt + "BothIn", both_in)
        add("BNear" + nt + "Instances", ninst)
        add("BNear" + nt + "Costly", nc)
        add("BNear" + nt + "CostlyTen", nc10)
        add("BNear" + nt + "Agree", grp(sum(agree)))
        add("BNear" + nt + "AgreeShare", pct(sum(agree), len(sel)))
        add("BNear" + nt + "AgreeLo", pctv(lo))
        add("BNear" + nt + "AgreeHi", pctv(hi))
        add("BNear" + nt + "CostlyAgree", sum(cagree))
        add("BNear" + nt + "LowAgree", sum(lagree))
        add("BNear" + nt + "Low", len(lagree))
        near_rows.append(["[{:.2f}, {:.2f}]".format(a, b), len(sel), both_in, ninst, nc, nc10,
                          ci_str(sum(agree), len(sel), lo, hi),
                          "{} of {}".format(sum(cagree), len(cagree)),
                          "{} of {}".format(sum(lagree), len(lagree))])
    xs = [pk[r["item_id"]] for r in recs]
    ys = [pf[r["item_id"]] for r in recs]
    rho = float(sstats.spearmanr(xs, ys).statistic)
    close = sum(1 for a, b in zip(xs, ys) if abs(a - b) <= 0.01)
    equal = sum(1 for a, b in zip(xs, ys) if abs(a - b) <= 1e-9)
    above = sum(1 for a, b in zip(xs, ys) if a > b + 1e-9)
    add("BSpearman", "{:.3f}".format(rho))
    add("BCloseN", grp(close))
    add("BCloseShare", pct(close, len(recs)))
    add("BEqualN", grp(equal))
    add("BKAboveFIN", grp(above))
    # CSV
    with open(OUT_PRICE, "w", newline="", encoding="utf-8") as fh:
        fh.write("# N18 ({}): one row per priced proposal of the direct benchmark at t_d; p_K and "
                 "p_FI = the certificate's price on the known board and with full information "
                 "(median over futures as logged in analysis/N11_rows_forecast.csv; refers when "
                 "above 0.20); costly: 1 costly, 0 low-cost, empty undecided; known_share = "
                 "n_known / (n_completed + n_known + n_unknown)\n".format(VERSION))
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["item_id", "instance_id", "stratum", "primary_class", "edit_type",
                    "costly_delta020", "costly_delta010", "p_K", "p_FI", "refers_K",
                    "refers_FI", "known_share", "t_d"])
        for r in recs:
            c2, c1 = n13.costly_of(r, 0.20), n13.costly_of(r, 0.10)
            w.writerow([r["item_id"], r["instance_id"], r["stratum"], r["primary_class"],
                        r["split"], "" if c2 is None else c2, "" if c1 is None else c1,
                        "{:.6f}".format(pk[r["item_id"]]), "{:.6f}".format(pf[r["item_id"]]),
                        int(rk[r["item_id"]]), int(rf[r["item_id"]]),
                        "{:.6f}".format(r["known_share"]), "{:.4f}".format(r["t_d"])])
    # summary
    md("## B. Price margins and near-threshold agreement (certificate, delta = tau = 0.20)", "",
       "p_K = the certificate's price on the known board at t_d; p_FI = the same gate's price with "
       "every order of the window known; a reading refers when its price exceeds 0.20 (the "
       "published flag, asserted equal on every row). File: analysis/N18_fig_price_k_fi.csv.", "",
       "### B1. Dispositions on K against FI", "")
    md_table(["population", "n", "referred under both", "K only", "FI only", "applied under both",
              "disagree"], body)
    md("The {} disagreements are all low-cost: K only {} (benign {}), FI only {} (benign {}); "
       "classes {}; edit types {}; {} of them have t_d at the window start; {} instances.".format(
           len(dis), len(dkonly), sum(1 for r in dkonly if r["primary_class"] == "benign"),
           len(dis) - len(dkonly), sum(1 for r in dis if not rk[r["item_id"]]
                                        and r["primary_class"] == "benign"),
           ", ".join("{} {}".format(c, dcls[c]) for c in D.CLASSES if dcls.get(c)),
           ", ".join("{} {}".format(s, dsp[s]) for s in sorted(dsp)),
           sum(1 for r in dis if r["t_d"] == 0.0), len({r["instance_id"] for r in dis})), "")
    md_table(["item", "class", "edit type", "stratum", "t_d (bh)", "known share", "p_K", "p_FI",
              "refers", "realised cost"],
             [[r["item_id"], r["primary_class"], r["split"], n13.STRATUM_NAME[r["stratum"]],
               "{:.2f}".format(r["t_d"]), pctpv(r["known_share"]),
               "{:.4f}".format(pk[r["item_id"]]), "{:.4f}".format(pf[r["item_id"]]),
               "K only" if rk[r["item_id"]] else "FI only",
               "[{:.4f}, {:.4f}]".format(r["lo"], r["hi"])] for r in dis])
    md("### B2. Prices of the 186 costly proposals", "",
       "min / Q1 / median / Q3 / max (numpy linear percentiles): p_K {}; p_FI {}.".format(
           " / ".join("{:.3f}".format(v) for v in qk), " / ".join("{:.3f}".format(v) for v in qf)),
       "")
    md_table(["reading", "at most 0.20", "(0.20, 0.30]", "(0.30, 0.40]", "above 0.40"], bin_rows)
    md("### B3. Near-threshold subsets and rank agreement", "",
       "Defined by price alone before agreement is computed: proposals with p_K or p_FI inside "
       "the band (inclusive). Agreement = the two readings give the same disposition; interval: "
       "95% cluster bootstrap over instances.", "")
    md_table(["band", "proposals", "both prices inside", "instances", "costly at 0.20",
              "costly at 0.10", "agreement [95% CI]", "agreement among costly",
              "agreement among low-cost"], near_rows)
    md("Spearman's rho of p_K and p_FI over the 1,356: {:.3f}. |p_K - p_FI| at most 0.01 on {} "
       "of 1,356 ({}); equal within 1e-9 on {}; p_K above p_FI on {}.".format(
           rho, close, pctp(close, len(recs)), equal, above), "")
    wn, wc, wa, wlo, whi = near_res["Wide"]
    nn, nc, na, nlo, nhi = near_res["Narrow"]
    facts([
        "The certificate's dispositions on the known board and with full information agree on "
        "{:,} of 1,356 priced proposals. All {} disagreements are low-cost at delta = 0.20 ({} "
        "referred on the known board only, {} with full information only, on {} instances).".format(
            len(recs) - len(dis), len(dis), len(dkonly), len(dis) - len(dkonly),
            len({r["instance_id"] for r in dis})),
        "{} of the {} proposals referred with full information only have a known-board price of "
        "0 and sit at the window start on {} instances. With full information the gate prices "
        "them at {} to {}.".format(
            len(fz), len(dis) - len(dkonly), len({r["instance_id"] for r in fz}),
            "{:.3f}".format(min(pf[r["item_id"]] for r in fz)) if fz else "n/a",
            "{:.3f}".format(max(pf[r["item_id"]] for r in fz)) if fz else "n/a"),
        "Of the 186 costly proposals, {} carry a price on the known board above 0.40 and {} a "
        "price of at most 0.20.".format(bin_rows[0][4], bin_rows[0][1]),
        "The median price of the 186 costly proposals is {:.3f} on the known board and {:.3f} "
        "with full information.".format(qk[2], qf[2]),
        "{} proposals have a price within 0.10 of the tolerance on either reading ({} of them "
        "costly), and the two readings agree on {} of them ({}, interval {} to {}).".format(
            wn, wc, wa, pctp(wa, wn), pctpv(wlo), pctpv(whi)),
        "Within 0.05 of the tolerance ({} proposals, {} costly) the two readings agree on {} "
        "({}, interval {} to {}), and they agree on every costly proposal in both bands.".format(
            nn, nc, na, pctp(na, nn), pctpv(nlo), pctpv(nhi)),
        "Spearman's rank correlation of the two prices is {:.3f}, and the two prices differ by "
        "at most 0.01 on {} of the 1,356 proposals.".format(rho, pctp(close, len(recs)))])
    return pk, pf


# --------------------------------------------------------------------------- #
# C. Where the 18 applied costly proposals come from                           #
# --------------------------------------------------------------------------- #
def block_c(recs, applied, suite, pk, pf, site):
    rows = []
    fields = Counter()
    for r in sorted(applied, key=lambda r: r["item_id"]):
        it = suite[r["item_id"]]
        ops = D.canonical_ops(it)
        check("the reference proposal's edit type is the recorded split",
              D.op_split(ops) == r["split"] == "field_changing", r["item_id"])
        check("family_id equals template_id", it["family_id"] == it["template_id"], r["item_id"])
        kinds = sorted({o["op"] for o in ops if o.get("op") in D.FIELD_OPS})
        what = " and ".join({"set_priority": "priority", "reassign_window": "time window"}[k]
                            for k in kinds)
        fields[what] += 1
        check("applied with FI as well", not n13.refers(r["fi"], CERT), r["item_id"])
        rows.append([r["item_id"], r["instance_id"], n13.STRATUM_NAME[r["stratum"]],
                     r["primary_class"], it["family_id"], what, pctpv(r["known_share"]),
                     "{:.2f}".format(r["t_d"]), "{:.4f}".format(pk[r["item_id"]]),
                     "{:.4f}".format(pf[r["item_id"]]), "{:.4f}".format(r["g_orig"]),
                     "{:.4f}".format(site[r["item_id"]]),
                     "[{:.4f}, {:.4f}]".format(r["lo"], r["hi"])])
        check("second price refers every applied costly proposal", r["sp"], r["item_id"])
    inst = {r["instance_id"] for r in applied}
    fam = Counter(suite[r["item_id"]]["family_id"] for r in applied)
    win = Counter(r["stratum"] for r in {r["instance_id"]: r for r in applied}.values())
    add("CAppliedN", len(applied))
    add("CInstances", len(inst))
    for st in STRATA:
        add("CWindows" + ST_TOK[st], win.get(st, 0))
        add("CApplied" + ST_TOK[st], sum(1 for r in applied if r["stratum"] == st))
    add("CFamilies", len(fam))
    for f, n in fam.items():
        add("CFamily" + family_tok(f), n)
    add("CPriorityEdits", fields.get("priority", 0))
    add("CWindowEdits", fields.get("time window", 0))
    add("CBothEdits", fields.get("priority and time window", 0))
    check("priority + window edits = 18", sum(fields.values()) == 18)
    add("CKnownShareMax", pctv(max(r["known_share"] for r in applied)))
    add("CKnownShareMin", pctv(min(r["known_share"] for r in applied)))
    add("CTdMedian", "{:.1f}".format(statistics.median(r["t_d"] for r in applied)))
    add("CPKMax", "{:.3f}".format(max(pk[r["item_id"]] for r in applied)))
    add("CPFIMax", "{:.3f}".format(max(pf[r["item_id"]] for r in applied)))
    add("CGOrigMin", "{:.3f}".format(min(r["g_orig"] for r in applied)))
    add("CSiteMin", "{:.3f}".format(min(site[r["item_id"]] for r in applied)))
    add("CSiteRefers", sum(1 for r in applied if site[r["item_id"]] > TAU))
    add("CCostMin", "{:.3f}".format(min(r["lo"] for r in applied)))
    add("CCostMax", "{:.3f}".format(max(r["hi"] for r in applied)))
    # the band comparison
    field = [r for r in recs if r["split"] == "field_changing"]
    seq = [r for r in recs if r["split"] == "sequencing_only"]
    check("531 priced field edits", len(field) == 531, len(field))
    pops = OrderedDict([
        ("priced proposals", recs),
        ("priced field edits", field),
        ("costly field edits, delta 0.20", [r for r in field if n13.costly_of(r, 0.20) == 1]),
        ("costly field edits, delta 0.10", [r for r in field if n13.costly_of(r, 0.10) == 1]),
        ("applied costly field edits, delta 0.20", applied),
        ("referred costly field edits, delta 0.20",
         [r for r in field if n13.costly_of(r, 0.20) == 1 and n13.refers(r, CERT)]),
        ("costly sequencing-only, delta 0.20", [r for r in seq if n13.costly_of(r, 0.20) == 1]),
        ("costly sequencing-only, delta 0.10", [r for r in seq if n13.costly_of(r, 0.10) == 1]),
        ("priced V4 field edits", [r for r in field if r["primary_class"] == "V4"]),
        ("costly V4 field edits, delta 0.20", [r for r in field if r["primary_class"] == "V4"
                                               and n13.costly_of(r, 0.20) == 1])])
    ptok = dict(zip(pops, ("Priced", "Field", "FieldCostlyTwenty", "FieldCostlyTen",
                           "FieldAppliedTwenty", "FieldReferredTwenty", "SeqCostlyTwenty",
                           "SeqCostlyTen", "VFourField", "VFourFieldCostlyTwenty")))
    check("the 60 / 64 costly field edits and 126 / 144 costly sequencing-only",
          [len(pops[k]) for k in list(pops)[2:4] + list(pops)[6:8]] == [60, 64, 126, 144])
    check("the costly V4 field edits at 0.20 are exactly the 18 applied",
          {r["item_id"] for r in pops["costly V4 field edits, delta 0.20"]}
          == {r["item_id"] for r in applied})
    body = []
    for pn, sel in pops.items():
        bc = Counter(band_of(r["known_share"]) for r in sel)
        row = [pn, len(sel)]
        for bt in BANDS:
            add("CBand" + bt + ptok[pn], bc.get(bt, 0))
            row.append("{} ({})".format(bc.get(bt, 0), pctp(bc.get(bt, 0), len(sel))))
        body.append(row)
    # cost of field edits by band, and the boards of each band
    cost_rows, board_rows = [], []
    for bt, bn in BANDS.items():
        sel = [r for r in field if band_of(r["known_share"]) == bt]
        lo = [r["lo"] for r in sel]
        q1, q2, q3 = (float(v) for v in np.percentile(np.asarray(lo), [25, 50, 75]))
        c2 = sum(1 for r in sel if n13.costly_of(r, 0.20) == 1)
        c1 = sum(1 for r in sel if n13.costly_of(r, 0.10) == 1)
        pos = sum(1 for v in lo if v > 1e-9)
        add("CBand" + bt + "FieldCostMedian", "{:.3f}".format(q2))
        add("CBand" + bt + "FieldCostQThree", "{:.3f}".format(q3))
        add("CBand" + bt + "FieldCostMean", "{:.3f}".format(float(np.mean(lo))))
        add("CBand" + bt + "FieldPositiveCost", pos)
        add("CBand" + bt + "FieldCostlyRateTwenty", pct(c2, len(sel)))
        add("CBand" + bt + "FieldCostlyRateTen", pct(c1, len(sel)))
        cost_rows.append([bn, len(sel), "{:.3f} / {:.3f} / {:.3f}".format(q1, q2, q3),
                          "{:.3f}".format(float(np.mean(lo))), frac(pos, len(sel)),
                          frac(c2, len(sel)), frac(c1, len(sel))])
        allb = [r for r in recs if band_of(r["known_share"]) == bt]
        td = statistics.median(r["t_d"] for r in allb)
        comp = statistics.median(r["n_completed"] / r["n_window"] for r in allb)
        later = statistics.median(r["n_unknown"] / r["n_window"] for r in allb)
        z = sum(1 for r in allb if r["t_d"] == 0.0)
        add("CBand" + bt + "TdMedian", "{:.1f}".format(td))
        add("CBand" + bt + "CompletedShareMedian", pctv(comp))
        add("CBand" + bt + "LaterShareMedian", pctv(later))
        add("CBand" + bt + "TdZero", grp(z))
        board_rows.append([bn, len(allb), frac(z, len(allb)), "{:.1f}".format(td), pctpv(comp),
                           pctpv(later)])
    fam_rows = []
    v4f = pops["priced V4 field edits"]
    for f in sorted({suite[r["item_id"]]["family_id"] for r in v4f}):
        row = [f]
        for bt in BANDS:
            sel = [r for r in v4f if suite[r["item_id"]]["family_id"] == f
                   and band_of(r["known_share"]) == bt]
            row.append("{} of {}".format(sum(1 for r in sel if n13.costly_of(r, 0.20) == 1),
                                         len(sel)))
        fam_rows.append(row)
    # summary
    md("## C. Where the 18 applied costly proposals come from", "",
       "The 18 costly proposals (delta = 0.20) that the certificate applies on K and with FI. "
       "Edited field from the reference proposal's operations (suite v0.2, the class's canonical "
       "field: trap_ops for V4): set_priority = priority, reassign_window = time window. t_d in "
       "business hours from the window start (t = 0). Realised cost = the bracket on the "
       "original values. s2_site = (obj_orig_K - WT_anchor_K) / max(WT_anchor_K, 1 bh) (N16 "
       "block I).", "")
    md_table(["item", "instance", "stratum", "class", "template family", "edits", "known share",
              "t_d (bh)", "p_K", "p_FI", "g_orig", "s2_site", "realised cost"], rows)
    md("Counts: {} distinct instances (windows: {}); {} template families ({}); {} priority "
       "edits and {} time-window edits. Every one is referred by the second price (g_orig from "
       "{:.3f}) and by s2_site ({} of 18, s2_site from {:.3f}).".format(
           len(inst), ", ".join("{} {}".format(n13.STRATUM_NAME[s], win.get(s, 0))
                                for s in STRATA),
           len(fam), ", ".join("{} {}".format(f, n) for f, n in fam.most_common()),
           fields.get("priority", 0), fields.get("time window", 0),
           min(r["g_orig"] for r in applied), sum(1 for r in applied if site[r["item_id"]] > TAU),
           min(site[r["item_id"]] for r in applied)), "")
    md("### C1. Known-share bands (share of each population in each band)", "")
    md_table(["population", "n"] + list(BANDS.values()), body)
    md("### C2. Realised cost of the priced field edits by band", "",
       "Lower end of the realised-cost bracket on the original values.", "")
    md_table(["band", "field edits", "Q1 / median / Q3", "mean", "cost above zero",
              "costly at 0.20", "costly at 0.10"], cost_rows)
    md("### C3. The boards of each band (all 1,356 priced proposals)", "",
       "Completed share = orders completed by t_d over the window's orders; later share = "
       "orders arriving after t_d over the window's orders (the orders the known board cannot "
       "see).", "")
    md_table(["band", "priced", "t_d at the window start", "median t_d (bh)",
              "median completed share", "median later share"], board_rows)
    md("### C4. V4 field edits by template family: costly at 0.20 of priced, per band", "")
    md_table(["template family"] + list(BANDS.values()), fam_rows)
    shares = {pn: Counter(band_of(r["known_share"]) for r in sel) for pn, sel in pops.items()}
    fl = shares["priced field edits"]["Low"]
    cfl = shares["costly field edits, delta 0.20"]["Low"]
    rates = [(bt, sum(1 for r in field if band_of(r["known_share"]) == bt
                      and n13.costly_of(r, 0.20) == 1),
              sum(1 for r in field if band_of(r["known_share"]) == bt)) for bt in BANDS]
    lowb = board_rows[0]
    csl = shares["costly sequencing-only, delta 0.20"]["Low"]
    md("Answer to the design's question, from tables C1 to C4. (1) Field edits in general are "
       "not concentrated on boards with at most half of the orders known. {} of the {} priced "
       "field edits ({}) sit there, close to the share of all priced proposals ({} of 1,356, "
       "{}). (2) The costly field edits are concentrated there ({} of 60, {}, at 0.20; all 18 "
       "applied ones), and the share of field edits that are costly falls as the known share "
       "rises ({}). Costly sequencing-only proposals lean the same way, less strongly ({} of "
       "126, {}). (3) The low band is not a band of early boards. Its median t_d is {} bh after "
       "the window start, a median {} of the window's orders are completed by t_d and a median "
       "{} arrive after it. In the two higher bands the median t_d is 0 and a median {} and {} "
       "of the orders arrive later. So the costly field edits sit on late boards, where most of "
       "the window has already run, and not on boards with many orders still unknown. (4) "
       "Within class V4 every costly field edit sits in the low band (C4): 15 of the 25 "
       "sign-flipped shifts there are costly, against none of the 15 in the two higher "
       "bands.".format(
           fl, len(field), pctp(fl, len(field)), shares["priced proposals"]["Low"],
           pctp(shares["priced proposals"]["Low"], len(recs)), cfl, pctp(cfl, 60),
           ", ".join("{} {}".format(BANDS[bt], pctp(k, n)) for bt, k, n in rates),
           csl, pctp(csl, 126), lowb[3], lowb[4], lowb[5], board_rows[1][5],
           board_rows[2][5]), "")
    sf = [r for r in v4f if suite[r["item_id"]]["family_id"] == "v4_sign_flipped_shift"]
    sfb = Counter((band_of(r["known_share"]), n13.costly_of(r, 0.20)) for r in sf)
    check("sign-flipped shifts: 15 of 25 costly in the low band, none of 15 above",
          (sfb[("Low", 1)], sfb[("Low", 1)] + sfb[("Low", 0)],
           sfb[("Mid", 1)] + sfb[("High", 1)],
           sum(v for (b, c), v in sfb.items() if b != "Low")) == (15, 25, 0, 15), sfb)
    facts([
        "The 18 costly proposals that the certificate applies sit on {} instances ({}) and come "
        "from {} template families ({}).".format(
            len(inst), ", ".join("{} {}".format(n13.STRATUM_NAME[s], win.get(s, 0))
                                 for s in STRATA if win.get(s, 0)),
            len(fam), ", ".join("{} {}".format(f, n) for f, n in fam.most_common())),
        "Of these 18, {} edit a time window and {} a priority.".format(
            fields.get("time window", 0), fields.get("priority", 0)),
        "On the known board their certificate price is at most {:.3f}, and with full "
        "information at most {:.3f}.".format(max(pk[r["item_id"]] for r in applied),
                                             max(pf[r["item_id"]] for r in applied)),
        "Field edits are not concentrated on boards with at most half of the orders known "
        "({} of {} priced field edits), but the costly ones are ({} of 60 at delta = 0.20, and "
        "all 18 applied).".format(fl, len(field), cfl),
        "The share of priced field edits that are costly at delta = 0.20 is {} on boards with "
        "at most half of the orders known, {} at 50% to 80% and {} above 80%.".format(
            *[pctp(k, n) for _bt, k, n in rates]),
        "Boards with at most half of the orders known are late boards. Their median decision "
        "instant is {} bh after the window start, a median {} of the window's orders are "
        "completed by then, and a median {} are still to arrive.".format(
            lowb[3], lowb[4], lowb[5])])
    return pops


# --------------------------------------------------------------------------- #
# D. Referral by equivalence to the reference translation, per cell            #
# --------------------------------------------------------------------------- #
def block_d(boot, cells, suite):
    m16 = macros_of(IN18["n16_macros"])
    out = []
    pooled = OrderedDict([("Same", []), ("Diff", [])])
    body = []
    for arm, th, tok, disp in n16.TAB6:
        rows = cells[(arm, th)]
        v3 = [(u, o) for u, o in rows if suite[u["item_id"]]["primary_class"] == "V3"]
        passed = [(u, o) for u, o in v3 if u["term_feas"] in n13.APPLIED]
        reps = len({u["repeat"] for u, o in v3})
        rec = OrderedDict(arm=arm, thinking=th, display=disp, repeats=reps, v3_rows=len(v3),
                          passed=len(passed))
        brow = [disp, th, reps, len(v3), len(passed)]
        add("Split" + tok + "Repeats", reps)
        add("Split" + tok + "Priced", grp(len(passed)))
        for stok in ("Same", "Diff"):
            sel = [(u, o) for u, o in passed
                   if n16.d3_equiv(o, suite[u["item_id"]]["gold_ops"]) == (stok == "Same")]
            fl = [u["stage_cert"] == "qual" and u["gap"] is not None and u["gap"] > TAU
                  for u, o in sel]
            for (u, o), f in zip(sel, fl):
                check("referral = blocked at the quality stage", f == (u["term_cert"] in n13.BLOCKED),
                      u["item_id"])
            rws = [dict(instance_id=u["instance_id"]) for u, o in sel]
            check("every row's instance is a bootstrap cluster",
                  all(x["instance_id"] in boot.index for x in rws))
            lo, hi = boot.ci(rws, fl) if sel else (None, None)
            k = sum(fl)
            ninst = len({x["instance_id"] for x in rws})
            pooled[stok].extend(zip(rws, fl))
            check("N16 block F cell reproduced ({} {})".format(disp, stok),
                  (grp(len(sel)), grp(k), pct(k, len(sel))) ==
                  (m16["nSixteenF" + tok + stok + "N"], m16["nSixteenF" + tok + stok + "Referred"],
                   m16["nSixteenF" + tok + stok + "Share"]), (len(sel), k))
            p = "Split" + tok + stok
            add(p + "N", grp(len(sel)))
            add(p + "Referred", grp(k))
            add(p + "Share", pct(k, len(sel)))
            add(p + "Lo", pctv(lo))
            add(p + "Hi", pctv(hi))
            add(p + "Instances", ninst)
            rec.update({stok.lower() + "_n": len(sel), stok.lower() + "_referred": k,
                        stok.lower() + "_share": k / len(sel) if sel else None,
                        stok.lower() + "_lo": lo, stok.lower() + "_hi": hi,
                        stok.lower() + "_instances": ninst})
            brow.append("{} ({} instances)".format(ci_str(k, len(sel), lo, hi), ninst))
        out.append(rec)
        body.append(brow)
    prec = OrderedDict(arm="pooled", thinking="", display="pooled (eight cells)", repeats="",
                       v3_rows=sum(r["v3_rows"] for r in out), passed=sum(r["passed"] for r in out))
    brow = ["pooled (eight cells)", "", "", prec["v3_rows"], prec["passed"]]
    for stok, lst in pooled.items():
        rws = [x for x, _f in lst]
        fl = [f for _x, f in lst]
        lo, hi = boot.ci(rws, fl)
        k = sum(fl)
        check("pooled cell equals N16 ({})".format(stok),
              (grp(len(fl)), grp(k), pct(k, len(fl)), pctv(lo), pctv(hi)) ==
              (m16["nSixteenFPooled" + stok + "N"], m16["nSixteenFPooled" + stok + "Referred"],
               m16["nSixteenFPooled" + stok + "Share"], m16["nSixteenFPooled" + stok + "ShareLo"],
               m16["nSixteenFPooled" + stok + "ShareHi"]), (len(fl), k, lo, hi))
        p = "SplitPooled" + stok
        add(p + "N", grp(len(fl)))
        add(p + "Referred", grp(k))
        add(p + "Share", pct(k, len(fl)))
        add(p + "Lo", pctv(lo))
        add(p + "Hi", pctv(hi))
        prec.update({stok.lower() + "_n": len(fl), stok.lower() + "_referred": k,
                     stok.lower() + "_share": k / len(fl), stok.lower() + "_lo": lo,
                     stok.lower() + "_hi": hi,
                     stok.lower() + "_instances": len({x["instance_id"] for x in rws})})
        brow.append("{} ({} instances)".format(ci_str(k, len(fl), lo, hi),
                                               prec[stok.lower() + "_instances"]))
    out.append(prec)
    body.append(brow)
    opus = [r for r in out if r["arm"] == "opus" and r["thinking"] == "default"][0]
    check("Claude Opus 5 (default thinking) equals the N16 macros: 268/294 and 10/14",
          (opus["same_referred"], opus["same_n"], opus["diff_referred"], opus["diff_n"])
          == (268, 294, 10, 14) and m16["nSixteenFOpusSameShare"] == "91.2\\%"
          and m16["nSixteenFOpusDiffShare"] == "71.4\\%")
    with open(OUT_FID, "w", newline="", encoding="utf-8") as fh:
        fh.write("# N18 ({}): gate stress test at t_d, constrained mode, the eight Table 6 cells, "
                 "repeats pooled; cost-bearing (V3) proposals that pass the feasibility check, "
                 "split by equivalence to the reference translation (D3's rule on the parsed "
                 "operations); referred = certified gap above 0.20; intervals = 95% cluster "
                 "bootstrap over instances (n2 seed, 20,000 replicates)\n".format(VERSION))
        w = csv.writer(fh, lineterminator="\n")
        cols = ["arm", "thinking", "display", "repeats", "v3_rows", "passed", "same_n",
                "same_referred", "same_share", "same_lo", "same_hi", "same_instances", "diff_n",
                "diff_referred", "diff_share", "diff_lo", "diff_hi", "diff_instances"]
        w.writerow(cols)
        for r in out:
            w.writerow([f4(r[c]) if isinstance(r[c], float) else ("" if r[c] is None else r[c])
                        for c in cols])
    md("## D. Referral by equivalence to the reference translation, per Table 6 cell", "",
       "Gate stress test at t_d, constrained mode, the eight schema-enforced cells of Table 6, "
       "repeats pooled (N16 block F's rows). Priced = the cost-bearing (V3) proposals that pass "
       "the feasibility check. Equivalent = the proposal's operations equal the reference "
       "translation under D3's rule. Referred = certified gap above 0.20. Interval: 95% cluster "
       "bootstrap over instances (n2 seed, 20,000 replicates; the rows of one instance share a "
       "cluster). Every count equals N16 block F (asserted). File: "
       "analysis/N18_fig_fidelity_split.csv.", "")
    md_table(["cell", "thinking", "repeats", "V3 rows", "priced",
              "equivalent: referred / n [95% CI]", "different: referred / n [95% CI]"], body)
    small = [r for r in out[:-1] if r["diff_n"] < 20]
    md("Cells with fewer than 20 different proposals (intervals wide): {}.".format(
        ", ".join("{} ({})".format(r["display"], r["diff_n"]) for r in small) or "none"), "")
    sames = [r["same_share"] for r in out[:-1]]
    facts([
        "In each of the eight cells the certificate refers between {} and {} of the cost-bearing "
        "proposals that equal the reference translation.".format(pctpv(min(sames)),
                                                                pctpv(max(sames))),
        "For the proposals that differ from the reference translation the share ranges from {} "
        "({}) to {} ({}), on {} to {} proposals per cell.".format(
            pctpv(min(r["diff_share"] for r in out[:-1])),
            min(out[:-1], key=lambda r: r["diff_share"])["display"],
            pctpv(max(r["diff_share"] for r in out[:-1])),
            max(out[:-1], key=lambda r: r["diff_share"])["display"],
            min(r["diff_n"] for r in out[:-1]), max(r["diff_n"] for r in out[:-1])),
        "For Claude Opus 5 with default thinking, the certificate refers {} of {} equivalent "
        "proposals ({}, interval {} to {}) and {} of {} different ones ({}, interval {} to "
        "{}).".format(
            opus["same_referred"], opus["same_n"], pctpv(opus["same_share"]),
            pctpv(opus["same_lo"]), pctpv(opus["same_hi"]), opus["diff_referred"],
            opus["diff_n"], pctpv(opus["diff_share"]), pctpv(opus["diff_lo"]),
            pctpv(opus["diff_hi"])),
        "Pooled over the eight cells, the certificate refers {:,} of {:,} equivalent proposals "
        "({}, interval {} to {}) and {} of {} different ones ({}, interval {} to {}).".format(
            prec["same_referred"], prec["same_n"],
            pctpv(prec["same_share"]), pctpv(prec["same_lo"]), pctpv(prec["same_hi"]),
            prec["diff_referred"], prec["diff_n"], pctpv(prec["diff_share"]),
            pctpv(prec["diff_lo"]), pctpv(prec["diff_hi"]))])
    return out


# --------------------------------------------------------------------------- #
# E. A scale for weighted business hours                                       #
# --------------------------------------------------------------------------- #
def block_e(e1cells):
    m11 = macros_of(IN18["n11_macros"])
    cell = ("opus", "default")
    rows = e1cells[cell]
    anchors = {}
    for rec in json.loads(Path(n13.IN["rule_anchor"]).read_text()):
        anchors[(Path(rec["instance_path"]).stem, e1dg.frozen_key(rec["frozen_seed"]))] = \
            float(rec["wwt_original_bh"])
    raw = [u for u in n13.read_jsonl(n13.IN["rows_e1"]) if u["mode"] == "M_constrained"
           and n13.SRC_ARM[u["src"]] == "opus" and e1dg.thinking_label(u["thinking"]) == "default"]
    check("one raw row per load_e1 row (Opus default)", len(raw) == len(rows), (len(raw), len(rows)))
    anc = []
    for u, r in zip(raw, rows):
        check("raw and load_e1 rows in the same order", (u["item_id"], int(u["repeat"]))
              == (r["item_id"], r["repeat"]))
        a = anchors[(u["instance_id"], u["frozen_seed"] or "")]
        if r["reached"] and (u["n_ops"] or 0) > 0:
            check("damage = rw_obj_orig - anchor", abs(float(u["rw_obj_orig"]) - a - r["dmg"]) < 1e-6,
                  u["item_id"])
        anc.append(a)
    sel = [(r, a) for r, a in zip(rows, anc) if not r["infra"]]

    def mean_dmg(design):
        v = []
        for r, _a in sel:
            b = n13.e1_blocked(r, design, "reject_all")
            v.append(0.0 if b is None or b else r["dmg"])
        return float(np.mean(v))
    mc, mf = mean_dmg("G-CERT"), mean_dmg("G-FEAS")
    check("the band +0.42 and +28.81 weighted bh per instruction is reproduced",
          (n13.bh(mc, signed=True), n13.bh(mf, signed=True)) == ("+0.42", "+28.81")
          == (m11["nElevenDgEOneDeltaFlagshipCertDamage"], m11["nElevenDgEOneDeltaFlagshipFeasDamage"]),
          (mc, mf))
    av = [a for _r, a in sel]
    per_item = {}
    for r, a in sel:
        check("one anchor per instruction", per_item.setdefault(r["item_id"], a) == a, r["item_id"])
    mean_a, med_a = float(np.mean(av)), float(np.median(av))
    mean_i, med_i = float(np.mean(list(per_item.values()))), float(np.median(list(per_item.values())))
    reps = Counter(r["repeat"] for r, _a in sel)
    ninf = sum(1 for r in rows if r["infra"])
    add("EOpusRows", grp(len(sel)))
    add("EOpusInfraRows", ninf)
    add("EOpusInstructions", grp(len(per_item)))
    add("EOpusInstances", len({r["instance_id"] for r, _a in sel}))
    add("EOpusAnchorMean", "{:.1f}".format(mean_a))
    add("EOpusAnchorMedian", "{:.1f}".format(med_a))
    add("EOpusAnchorQOne", "{:.1f}".format(float(np.percentile(av, 25))))
    add("EOpusAnchorQThree", "{:.1f}".format(float(np.percentile(av, 75))))
    add("EOpusAnchorMeanInstructions", "{:.1f}".format(mean_i))
    add("EOpusAnchorMedianInstructions", "{:.1f}".format(med_i))
    add("EOpusCertDamage", n13.bh(mc, signed=True))
    add("EOpusFeasDamage", n13.bh(mf, signed=True))
    add("EOpusCertPctOfMean", "{:.2f}\\%".format(100 * mc / mean_a))
    add("EOpusFeasPctOfMean", "{:.1f}\\%".format(100 * mf / mean_a))
    add("EOpusCertPctOfMedian", "{:.2f}\\%".format(100 * mc / med_a))
    add("EOpusFeasPctOfMedian", "{:.1f}\\%".format(100 * mf / med_a))
    md("## E. A scale for weighted business hours (Claude Opus 5 damage band)", "",
       "Population: the rows on which n13 section A computes the band +0.42 (the certificate, "
       "every referral declined) and +28.81 (every referral approved, equal to the "
       "feasibility-only gate) weighted bh per instruction: results/n11_e2e/rows_e1_primary.jsonl, "
       "mode M_constrained, cell opus/default (Claude Opus 5, default thinking), rows without an "
       "infrastructure failure ({} rows: {} instructions x repeats {}; {} infrastructure rows "
       "dropped), the band reproduced from these rows (asserted against "
       "\\nElevenDgEOneDeltaFlagshipCertDamage and ...FeasDamage). The no-AI schedule's weighted "
       "tardiness per row = the published no-AI anchor of the row's instance and frozen seed, "
       "analysis/ladder/rule_anchor.json field wwt_original_bh (the site's dispatching rule over "
       "the whole window, scored on the original values), the same anchor from which each row's "
       "damage is measured (damage = rw_obj_orig - anchor, asserted on every applied row).".format(
           len(sel), len(per_item), dict(sorted(reps.items())), ninf), "")
    md_table(["population", "n", "mean (bh)", "median (bh)", "Q1 / Q3 (bh)",
              "+0.42 as % of mean / median", "+28.81 as % of mean / median"],
             [["rows (instructions x repeats)", len(sel), "{:.1f}".format(mean_a),
               "{:.1f}".format(med_a), "{:.1f} / {:.1f}".format(float(np.percentile(av, 25)),
                                                                float(np.percentile(av, 75))),
               "{:.2f}% / {:.2f}%".format(100 * mc / mean_a, 100 * mc / med_a),
               "{:.1f}% / {:.1f}%".format(100 * mf / mean_a, 100 * mf / med_a)],
              ["distinct instructions", len(per_item), "{:.1f}".format(mean_i),
               "{:.1f}".format(med_i), "", "", ""]])
    md("Percentages use the unrounded band ends ({:.4f} and {:.4f} bh).".format(mc, mf), "")
    facts([
        "Over the {} instructions of the Claude Opus 5 stress test the no-AI schedule carries a "
        "mean weighted tardiness of {:.1f} weighted bh per instruction (median {:.1f}).".format(
            grp(len(per_item)).replace("{,}", ","), mean_a, med_a),
        "The damage band of +0.42 to +28.81 weighted bh per instruction is {:.2f}% to {:.1f}% of "
        "that mean.".format(100 * mc / mean_a, 100 * mf / mean_a)])
    return mean_a, med_a, mc, mf


# --------------------------------------------------------------------------- #
# F. The approver who approves exactly the stated acceptances                  #
# --------------------------------------------------------------------------- #
def block_f(suite, e1cells):
    m13 = macros_of(IN18["n13_macros"])
    # The supplement drafts are checked when present; the public release does not carry them.
    app = Path(IN18["app_n13_n14"]).read_text(encoding="utf-8") \
        if Path(IN18["app_n13_n14"]).is_file() else None
    summ = Path(IN18["n13_summary"]).read_text(encoding="utf-8")
    if app is not None:
        check("the supplement names the policy (app:dt-further-band)",
              "\\label{app:dt-further-band}" in app
              and "\\nThirteenAThreeOpusCostBearingApproveStatedDamage" in app
              and "\\label{tab:dt-band}" in app)
    check("N13 section A states the policy", "approve stated acceptance" in summ)
    # the no-label fact, checked on the suite (not recomputed damage)
    keys = {k for it in suite.values() for k in it}
    check("suite v0.2 carries no stated-acceptance field", not any("accept" in k.lower()
                                                                    for k in keys), keys)
    v3_acc = [i for i, it in suite.items() if it["primary_class"] == "V3"
              and "accept" in it["instruction"].lower()]
    check("no V3 instruction contains an acceptance clause", not v3_acc, v3_acc)
    e1_rows = []
    reps = OrderedDict((e1dg.CELL_TOKEN[c], len({r["repeat"] for r in e1cells[c]}))
                       for c in e1dg.CAPABILITY_SET)
    check("repeats per Table 6 cell", list(reps.values()) == [3, 3, 1, 2, 2, 2, 2, 1], reps)
    names = {"QwenFourteenB": "Qwen3-14B", "QwenTwentySevenB": "Qwen3.6-27B-FP8",
             "Glm": "GLM-4-9B-0414", "Mini": "GPT-5.4-mini", "Sonnet": "Claude Sonnet 5",
             "Opus": "Claude Opus 5", "OpusDisabled": "Claude Opus 5 (no think)",
             "Sol": "GPT-5.6 Sol"}
    for tok, n in reps.items():
        if n < 2:
            continue
        e1_rows.append([names[tok], n, m13["nThirteenAEOne{}CertRejectAllDamage".format(tok)],
                        m13["nThirteenAEOne{}CertApproveAllDamage".format(tok)],
                        "\\nThirteenAEOne{}CertRejectAllDamage".format(tok)])
    n3_rows = []
    for arm, nm in (("Opus", "Claude Opus 5"), ("Sol", "GPT-5.6 Sol"), ("Sonnet", "Claude Sonnet 5"),
                    ("Mini", "GPT-5.4-mini"), ("Deepseek", "DeepSeek V4-Pro")):
        b = "nThirteenAThree{}CostBearing".format(arm)
        n3_rows.append([nm, m13[b + "RejectAllDamage"],
                        "{} [{}, {}]".format(m13[b + "ApproveStatedDamage"],
                                             m13[b + "ApproveStatedDamageLo"],
                                             m13[b + "ApproveStatedDamageHi"]),
                        m13[b + "ApproveAllDamage"], "\\" + b + "ApproveStatedDamage"])
    md("## F. An approver who approves exactly the referrals with stated acceptance", "",
       "Already reported; not recomputed. N13 section A (code/scripts/n13_fromlogs.py, policy "
       "'approve_stated') defines it, and the supplement reports it in "
       "the manuscript text, subsection app:dt-further-band, beside Table "
       "tab:dt-band (the decline-all and approve-all columns), with macros "
       "\\nThirteenAThree<Arm>CostBearingApproveStatedDamage (and ...Lo, ...Hi). The limitations "
       "table (app_limitations.tex, 'The approver's decision') cites the band "
       "\\nThirteenAEOneOpusCertRejectAllDamage to \\nThirteenAEOneOpusCertApproveAllDamage.", "",
       "Why the stress-test logs give no third number: suite v0.2 (the stress test and the direct "
       "benchmark) carries no stated-acceptance label (no field whose name contains 'accept', and "
       "no V3 instruction containing 'accept'; both asserted here). The policy therefore declines "
       "every referral there, and its damage equals the decline-all value of tab:dt-band. Where "
       "the label exists (the protocol v1.1/v1.2 item sets of Section 5.6 at the decision "
       "instant, N3 twin rows; cost-bearing = stated-acceptance items plus their V3 twins; "
       "repeats pooled; n3 instance-cluster bootstrap) N13 computes it.", "",
       "### F1. Stress test, cells with two or more repeats: the policy equals decline all", "")
    md_table(["cell", "repeats", "approve stated = decline all (bh per instruction)",
              "approve all", "macro"], e1_rows)
    md("### F2. Item sets with the label (N3 twin, certificate at tau = 0.20, no override "
       "ceiling), bh per cost-bearing proposal", "")
    md_table(["arm", "decline all", "approve stated [95% CI]", "approve all", "macro"], n3_rows)
    facts([
        "On the stress test the instructions carry no stated-acceptance label, so an approver "
        "who approves exactly the referrals with stated acceptance declines every referral, and "
        "Claude Opus 5's damage stays at {} weighted bh per instruction "
        "(\\nThirteenAEOneOpusCertRejectAllDamage).".format(
            m13["nThirteenAEOneOpusCertRejectAllDamage"]),
        "On the item sets that carry the label, this approver gives Claude Opus 5 a damage of "
        "{} weighted bh per cost-bearing proposal (interval {} to {}), between {} with every "
        "referral declined and {} with every referral approved (supplement, "
        "app:dt-further-band).".format(
            m13["nThirteenAThreeOpusCostBearingApproveStatedDamage"],
            m13["nThirteenAThreeOpusCostBearingApproveStatedDamageLo"],
            m13["nThirteenAThreeOpusCostBearingApproveStatedDamageHi"],
            m13["nThirteenAThreeOpusCostBearingRejectAllDamage"],
            m13["nThirteenAThreeOpusCostBearingApproveAllDamage"])])


# --------------------------------------------------------------------------- #
# G. Points outside the drawn window of fig_price_oracle_dt.py                 #
# --------------------------------------------------------------------------- #
def block_g(recs):
    # The figure scripts are read when present. The public release does not carry them, and
    # then the window, the offset and the designs are the values asserted below.
    figs = all(Path(IN18[k]).is_file() for k in ("fig_price_oracle_dt", "fig_price_oracle"))
    lit = lit_assign(IN18["fig_price_oracle_dt"], {"OUTSIDE", "N_ROWS", "DESIGNS"}) if figs else None
    pubc = lit_assign(IN18["fig_price_oracle"], {"LO", "HI", "OFFSET", "TAU"}) if figs \
        else dict(FIG_WINDOW)
    lo_w, hi_w, off = pubc["LO"], pubc["HI"], pubc["OFFSET"]
    check("figure window and offset", (lo_w, hi_w, off, pubc["TAU"]) == (-0.05, 1.0, 0.05, 0.20))
    designs = [(g, col) for g, col, _t in lit["DESIGNS"]] if figs else list(FIG_DESIGNS)
    check("figure designs", designs == [("G-CERT", "p_K_G-CERT"), ("D-REL2", "p_K_D-REL2")])
    rows = n13.read_csv(IN18["n14_rows"])
    rec_by = {r["item_id"]: r for r in recs}
    body = []
    other_rows = []
    gt = {"G-CERT": "Cert", "D-REL2": "RelTwo"}
    tot = Counter()
    for rule, rtok in (("atc", "Atc"), ("wspt", "Wspt")):
        sel = [r for r in rows if r["rule"] == rule and r["priced_K"] == "True"]
        if figs:
            check("figure row count {}".format(rule), len(sel) == lit["N_ROWS"][rule], len(sel))
        for g, col in designs:
            n_out = n_corner = 0
            ref = app = below = below_off = cst = app_cst = app_low = sp_ref = 0
            for r in sel:
                glo, ghi = float(r["g_K_lo"]), float(r["g_K_hi"])
                check("bracket closed on K", glo == ghi, r["item_id"])
                x = 0.5 * (glo + ghi)
                y = float(r[col])
                inside = lo_w <= x <= hi_w and lo_w <= y <= hi_w
                if inside:
                    continue
                n_out += 1
                corner = x > hi_w and y > hi_w
                n_corner += int(corner)
                referred = y > n16.SETTING[g]
                if rule == "atc":
                    check("atc price flag equals the published flag",
                          referred == n13.refers(rec_by[r["item_id"]], g), r["item_id"])
                ref += int(referred)
                app += int(not referred)
                below += int(y < x - 1e-9)
                below_off += int(y - x < -off)
                cc = cost_class(n13.fnum(r["orig_m_lo"]), n13.fnum(r["orig_m_hi"]), 0.20)
                cst += int(cc == 1)
                app_cst += int(cc == 1 and not referred)
                app_low += int(cc == 0 and not referred)
                if not corner:
                    other_rows.append([rule, g, r["item_id"], r["primary_class"], r["split"],
                                       "{:.4f}".format(x), "{:.4f}".format(y),
                                       "referred" if referred else "applied",
                                       {1: "costly", 0: "low-cost", None: "undecided"}[cc]])
            if figs:
                want = tuple(lit["OUTSIDE"][rule][g])
                check("outside counts equal the figure script's OUTSIDE ({} {})".format(rule, g),
                      (n_out, n_corner, n_out - n_corner) == want, (n_out, n_corner, want))
            p = "G" + rtok + gt[g]
            add(p + "Outside", n_out)
            add(p + "Corner", n_corner)
            add(p + "Other", n_out - n_corner)
            add(p + "Referred", ref)
            add(p + "Applied", app)
            add(p + "BelowDiag", below)
            add(p + "BelowDiagOffset", below_off)
            add(p + "CostlyTwenty", cst)
            add(p + "AppliedCostlyTwenty", app_cst)
            tot["below"] += below
            tot["app"] += app
            body.append(["({}) {}".format("a" if rule == "atc" else "b", rule), g,
                         "{:.2f}".format(n16.SETTING[g]), n_out, n_corner, n_out - n_corner, ref,
                         app, app_cst, app_low, below, below_off])
    check("published totals 91 / 93 / 91 / 99", [b[3] for b in body] == [91, 93, 91, 99])
    md("## G. Points outside the drawn window of the price-against-cost figure", "",
       "the manuscript's figure script (read, not run): x = the absolute cost g on the "
       "known board (g_K_lo = g_K_hi, asserted), y = the design's price on K, from "
       "analysis/N14_rows.csv (priced_K = True; panel (a) atc 1,356 rows, panel (b) wspt 1,346). "
       "Drawn window [-0.05, 1.0] on both axes. Referred = price above the design's published "
       "threshold (certificate 0.20, D-REL2 0.02; under atc equal to the published flag, "
       "asserted); applied = not referred. Below the diagonal = price below g (strictly), and by "
       "more than 0.05 (the figure's offset). Realised cost class at delta = 0.20 from orig_m. "
       "The outside counts equal the script's OUTSIDE constant (asserted).", "")
    md_table(["panel", "design", "threshold", "outside", "cost and price above 1.0", "other",
              "referred", "applied", "applied and costly", "applied and low-cost",
              "below the diagonal", "more than 0.05 below"], body)
    md("Omitted points that are not in the top-right corner:", "")
    md_table(["rule", "design", "item", "class", "edit type", "g", "price", "disposition",
              "realised cost at 0.20"], other_rows)
    b = {(x[0][:3], x[1]): x for x in body}
    check("no omitted point is a costly proposal that its design applies",
          all(x[8] == 0 for x in body))
    facts([
        "Every point that the figure omits for the certificate ({} in panel (a), {} in panel "
        "(b)) has a cost and a price above 1.0, is referred, and lies on or above the "
        "diagonal.".format(b[("(a)", "G-CERT")][3], b[("(b)", "G-CERT")][3]),
        "Of the D-REL2 points the figure omits, {} of {} in panel (a) and {} of {} in panel (b) "
        "are referred, and the {} and {} applied ones are all low-cost.".format(
            b[("(a)", "D-REL2")][6], b[("(a)", "D-REL2")][3], b[("(b)", "D-REL2")][6],
            b[("(b)", "D-REL2")][3], b[("(a)", "D-REL2")][7], b[("(b)", "D-REL2")][7]),
        "The figure omits {} D-REL2 points below the diagonal in panel (a) and {} in panel (b) "
        "({} and {} of them by more than 0.05).".format(b[("(a)", "D-REL2")][10], b[("(b)", "D-REL2")][10],
                                        b[("(a)", "D-REL2")][11], b[("(b)", "D-REL2")][11])])
    return body, other_rows


# --------------------------------------------------------------------------- #
# H. The forecast shortfall by stratum                                         #
# --------------------------------------------------------------------------- #
def block_h(fc):
    m13 = macros_of(IN18["n13_macros"])
    body = []
    res = {}
    groups = OrderedDict([(ST_TOK[s], (s,)) for s in STRATA])
    groups["Constructed"] = ("c09_storm2_w80", "c10_storm2_w80")
    groups["Pooled"] = STRATA
    for rd in ("K", "F2"):
        rt = n13.RD_TOK[rd]
        for gtok, sts in groups.items():
            seq = [r for r in fc[rd].values() if r["split"] == "sequencing_only"
                   and r["dmg"] is not None and r["dmg"] > 2.0 and r["stratum"] in sts]
            n = len(seq)
            real = sum(r["dmg"] for r in seq)
            sf = sum(max(0.0, r["dmg"] - r["p_D-ABS"]) for r in seq)
            short = sum(1 for r in seq if r["dmg"] - r["p_D-ABS"] > 1e-9)
            ninst = len({r["instance_id"] for r in seq})
            res[(rd, gtok)] = (n, sf, real, short, ninst)
            if gtok != "Constructed":
                check("N13 section D cell ({} {})".format(rd, gtok),
                      (pct(sf, real), str(n)) == (m13["nThirteenD{}{}ShortfallShare".format(rt, gtok)],
                                                   m13["nThirteenD{}{}N".format(rt, gtok)]),
                      (sf, real, n))
            p = "H" + rt + gtok
            add(p + "N", n)
            add(p + "Instances", ninst)
            add(p + "ShortfallShare", pct(sf, real))
            add(p + "ShortfallBh", "{:.1f}".format(sf))
            add(p + "RealisedBh", grp(round(real)))
            add(p + "ShortN", short)
            body.append([n13.READ_NAME[rd], {"Primary": "Primary (constructed)",
                                             "Confirmation": "Confirmation (constructed)",
                                             "Buildings": "Buildings (recorded)",
                                             "Constructed": "the two constructed strata",
                                             "Pooled": "pooled"}[gtok], n, ninst,
                         "{:.1f} of {:,.1f} bh".format(sf, real), pctp(sf, real), short])
    check("published 9.8% and 2.1%", pct(res[("K", "Pooled")][1], res[("K", "Pooled")][2])
          == "9.8\\%" and pct(res[("F2", "Pooled")][1], res[("F2", "Pooled")][2]) == "2.1\\%")
    md("## H. The forecast shortfall by stratum", "",
       "N13 section D's quantity (code/scripts/n13_fromlogs.py section_d; rows "
       "analysis/N11_rows_forecast.csv, readings K and F2): the sequencing-only proposals whose "
       "realised damage on the original values exceeds 2 bh; predicted damage = the reading's "
       "D-ABS price (median over the sampled futures); shortfall = realised minus predicted when "
       "positive; share = total shortfall over total realised. Recomputed here and asserted "
       "against \\nThirteenD<K|FTwo><stratum>ShortfallShare and ...N; the constructed pool "
       "(Primary + Confirmation) is new. Buildings is the recorded window; in the two constructed "
       "strata the later orders come from the arrival model that the load-estimated forecast "
       "samples.", "")
    md_table(["reading", "stratum", "proposals", "instances", "shortfall / realised", "share",
              "proposals with any shortfall"], body)
    kb, fb = res[("K", "Buildings")], res[("F2", "Buildings")]
    kc, fcn = res[("K", "Constructed")], res[("F2", "Constructed")]
    facts([
        "On the recorded Buildings stratum the known board understates the realised damage of "
        "re-sequencing proposals by {} and the load-estimated forecast by {}, over {} proposals "
        "on {} instances.".format(pctp(kb[1], kb[2]), pctp(fb[1], fb[2]), kb[0], kb[4]),
        "On the two constructed strata the understatement falls from {} on the known board to "
        "{} with the load-estimated forecast, over {} proposals.".format(
            pctp(kc[1], kc[2]), pctp(fcn[1], fcn[2]), kc[0]),
        "The understatement falls from {} to {} on the Primary stratum ({} proposals) and from "
        "{} to {} on the Confirmation stratum ({} proposals).".format(
            pctp(res[("K", "Primary")][1], res[("K", "Primary")][2]),
            pctp(res[("F2", "Primary")][1], res[("F2", "Primary")][2]), res[("K", "Primary")][0],
            pctp(res[("K", "Confirmation")][1], res[("K", "Confirmation")][2]),
            pctp(res[("F2", "Confirmation")][1], res[("F2", "Confirmation")][2]),
            res[("K", "Confirmation")][0])])
    return res


# --------------------------------------------------------------------------- #
# I. Correct translations under the second price, and the 36 behind the LLMs   #
# --------------------------------------------------------------------------- #
def block_i(recs, site, llm_recs):
    pop = [r for r in recs if r["primary_class"] in ("benign", "V3")
           and r["split"] == "field_changing"]
    cls = Counter(r["primary_class"] for r in pop)
    add("IN", len(pop))
    add("IBenignN", cls.get("benign", 0))
    add("IVThreeN", cls.get("V3", 0))
    body, lst = [], []
    settings = OrderedDict([("Twenty", 0.20), ("Ten", 0.10)])
    res = {}
    for stok, tau in settings.items():
        for which in ("Second", "Site"):
            if which == "Second":
                ref = [r for r in pop if r["g_orig"] > tau]
            else:
                ref = [r for r in pop if site[r["item_id"]] > tau]
            if which == "Site":
                check("s2_site refers a subset of what the second price refers",
                      {r["item_id"] for r in ref} <= {r["item_id"] for r in res[("Second", stok)]})
            c_own = [r for r in ref if n13.costly_of(r, tau) == 1]
            l_own = [r for r in ref if n13.costly_of(r, tau) == 0]
            first = [r for r in ref if r["p_G-CERT"] > tau]
            ben = sum(1 for r in ref if r["primary_class"] == "benign")
            res[(which, stok)] = ref
            p = "I" + which + stok
            add(p, len(ref))
            add(p + "Benign", ben)
            add(p + "VThree", len(ref) - ben)
            add(p + "Costly", len(c_own))
            add(p + "Low", len(l_own))
            add(p + "FirstAlsoRefers", len(first))
            add(p + "CostMedian", "{:.3f}".format(statistics.median(r["lo"] for r in ref))
                if ref else "n/a")
            body.append(["{:.2f}".format(tau), "second price g_orig" if which == "Second"
                         else "site-schedule variant s2_site", len(pop), len(ref),
                         "{} / {}".format(ben, len(ref) - ben),
                         "{} / {} / {}".format(len(c_own), len(l_own),
                                               len(ref) - len(c_own) - len(l_own)),
                         len(first),
                         " / ".join("{:.3f}".format(v) for v in (
                             min(r["lo"] for r in ref), statistics.median(r["lo"] for r in ref),
                             max(r["lo"] for r in ref))) if ref else "none"])
    allref = {r["item_id"]: r for k in res for r in res[k]}
    for iid in sorted(allref):
        r = allref[iid]
        lst.append([iid, r["primary_class"], suite_family(iid), "{:.4f}".format(r["g_orig"]),
                    "{:.4f}".format(site[iid]), "{:.4f}".format(r["p_G-CERT"]),
                    "[{:.4f}, {:.4f}]".format(r["lo"], r["hi"]),
                    {1: "costly", 0: "low-cost", None: "undecided"}[n13.costly_of(r, 0.20)],
                    {1: "costly", 0: "low-cost", None: "undecided"}[n13.costly_of(r, 0.10)]])
    # the 36 costly field edits behind the LLMs
    c36 = [r for r in llm_recs if cost_class(r["lo"], r["hi"], 0.20) == 1]
    check("36 costly applied field edits behind the LLMs, all referred by the second price",
          len(c36) == 36 and all(r["sp"] for r in c36), len(c36))
    m16 = macros_of(IN18["n16_macros"])
    check("equals \\nSixteenLlmAllCostlyTwenty and ...SecondTwenty",
          m16["nSixteenLlmAllCostlyTwenty"] == "36" and m16["nSixteenLlmAllCostlySecondTwenty"] == "36")
    ins = sorted({r["item_id"] for r in c36})
    inst = {r["instance_id"] for r in c36}
    cellc = Counter("{}/{}".format(*r["cell"]) for r in c36)
    k = len(ins)
    lb = float(sstats.beta.ppf(0.05, k, 1))
    check("exact one-sided bound with k of k = 0.05^(1/k)", abs(lb - 0.05 ** (1.0 / k)) < 1e-12)
    lb_rows = float(sstats.beta.ppf(0.05, len(c36), 1))
    add("ILlmCostly", len(c36))
    add("ILlmInstructions", k)
    add("ILlmInstances", len(inst))
    add("ILlmCells", len(cellc))
    add("ILlmLowerBound", "{:.1f}\\%".format(100 * lb))
    add("ILlmLowerBoundRows", "{:.1f}\\%".format(100 * lb_rows))
    icls = Counter(r["cls"] for r in {r["item_id"]: r for r in c36}.values())
    per_ins = Counter(r["item_id"] for r in c36)
    md("## I. Correct translations that edit a priority or a time window, and the 36 behind the "
       "LLMs", "",
       "Population: priced reference proposals of the direct benchmark at t_d whose class makes "
       "the reference proposal a correct translation (benign and cost-bearing V3; the reference "
       "proposal is gold_ops for both) and whose operations set a priority or reassign a window "
       "(edit type field_changing). The second price g_orig = (obj_orig_K - LB_anchor_K) / "
       "max(LB_anchor_K, 1 bh); s2_site replaces the bound by the untouched board's weighted "
       "tardiness under the site's dispatching rule (N16 block I). Each is read alone here (field "
       "edits only), at tau = 0.20 with the cost level 0.20 and at tau = delta = 0.10. "
       "Costly / low-cost at the matching cost level.", "")
    md_table(["tau = delta", "check", "population", "referred", "benign / V3",
              "costly / low-cost / undecided", "first price (G-CERT) also above tau",
              "realised cost of the referred, min / median / max"], body)
    md("The referred proposals:", "")
    md_table(["item", "class", "template family", "g_orig", "s2_site", "p_K (G-CERT)",
              "realised cost", "at 0.20", "at 0.10"], lst or [["none"] + [""] * 8])
    md("### The 36 costly field edits applied behind the LLMs (delta = 0.20)", "",
       "N16 block D2's rows (analysis/N11_rows_e2e.csv, e2e_td, constrained, every cell and "
       "repeat; applied = certified gap at most 0.20; costly = realised cost above 0.20). The "
       "second price refers all 36 (asserted). Lower bound: exact (Clopper-Pearson) one-sided "
       "95% bound on the referral probability with every distinct instruction counted once, "
       "k referred of k, = 0.05^(1/k); the bound over the 36 rows treats repeats and cells of one "
       "instruction as independent and is shown only for contrast.", "")
    md_table(["rows", "distinct instructions", "instances", "model configurations",
              "rows per instruction", "classes (instructions)", "one-sided 95% lower bound "
              "(instructions)", "same over rows"],
             [[len(c36), k, len(inst), len(cellc),
               ", ".join("{} {}".format(i, n) for i, n in sorted(per_ins.items())),
               ", ".join("{} {}".format(c, n) for c, n in sorted(icls.items())),
               "{:.1f}%".format(100 * lb), "{:.1f}%".format(100 * lb_rows)]])
    md("Configurations: " + ", ".join("{} {}".format(c, n) for c, n in sorted(cellc.items())) +
       ".", "")
    s20, t20 = res[("Second", "Twenty")], res[("Site", "Twenty")]
    s10, t10 = res[("Second", "Ten")], res[("Site", "Ten")]
    facts([
        "Of the {} priced reference proposals that are correct translations and edit a priority "
        "or a time window ({} benign, {} cost-bearing), the second price refers {} at tau = 0.20 "
        "({} of them costly) and the site-schedule variant {} ({} costly).".format(
            len(pop), cls.get("benign", 0), cls.get("V3", 0), len(s20),
            sum(1 for r in s20 if n13.costly_of(r, 0.20) == 1), len(t20),
            sum(1 for r in t20 if n13.costly_of(r, 0.20) == 1)),
        "At tau = delta = 0.10 the second price refers {} of them ({} costly at 0.10) and the "
        "site-schedule variant {} ({} costly at 0.10).".format(
            len(s10), sum(1 for r in s10 if n13.costly_of(r, 0.10) == 1), len(t10),
            sum(1 for r in t10 if n13.costly_of(r, 0.10) == 1)),
        "The 36 costly field edits applied behind the LLMs sit on {} distinct instructions, {} "
        "instances and {} model configurations. All {} instructions are referred, so the exact "
        "one-sided 95% lower bound on the referral probability is {:.1f}%.".format(
            k, len(inst), len(cellc), k, 100 * lb)])
    return pop, res, c36, k, lb


# --------------------------------------------------------------------------- #
# J. The headline read by the later share (the information gap)                #
# --------------------------------------------------------------------------- #
LBANDS = OrderedDict([("Zero", "L = 0"), ("UpToTen", "0 < L <= 10%"),
                      ("TenToTwentyFive", "10% < L <= 25%"), ("AboveTwentyFive", "L > 25%")])
LPOPS = OrderedDict([("Priced", "priced proposals"), ("CostlyTwenty", "costly at 0.20"),
                     ("CostlyTen", "costly at 0.10"),
                     ("FieldCostlyTwenty", "costly field edits at 0.20"),
                     ("SeqCostlyTwenty", "costly sequencing-only at 0.20")])
LCUTS = OrderedDict([("AtLeastTen", Fraction(1, 10)), ("AtLeastTwenty", Fraction(1, 5)),
                     ("AtLeastThirty", Fraction(3, 10))])


def lband(fr):
    """Band of a later share given as an exact fraction (fixed before any agreement is read)."""
    if fr == 0:
        return "Zero"
    if fr <= Fraction(1, 10):
        return "UpToTen"
    if fr <= Fraction(1, 4):
        return "TenToTwentyFive"
    return "AboveTwentyFive"


def later_shares(recs, suite):
    """L (orders), C (orders) and W (processing time) per priced proposal.

    L and C come from the census counts of results/n11_decision_time/items.jsonl. W needs the
    processing times of the later orders, which the rows do not carry. They are read from the
    snapshot instance file (n11_decision_time.instance_path / load_instance, no replay). The
    later orders are the orders that n8_causal.site_state classes as unknown at t_d with
    pm_known set: not planned maintenance and released after t_d (an order cannot start before
    its release). The rebuilt set is asserted to have n_unknown members on every row, and the
    instance to hold n_completed + n_known + n_unknown orders.
    """
    cache = {}
    out = {}
    for r in recs:
        iid = r["instance_id"]
        if iid not in cache:
            inst = D.load_instance(D.instance_path(suite[r["item_id"]]))
            cache[iid] = inst["work_orders"]
        wos = cache[iid]
        check("the instance holds the window's orders", len(wos) == r["n_window"], r["item_id"])
        later = [w for w in wos if not w.get("is_pm") and float(w["release_bh"]) > r["t_d"]]
        check("rebuilt later orders = n_unknown", len(later) == r["n_unknown"], r["item_id"])
        tot = sum(float(w["p_bh"]) for w in wos)
        out[r["item_id"]] = dict(
            L=Fraction(r["n_unknown"], r["n_window"]), C=Fraction(r["n_completed"], r["n_window"]),
            W=sum(float(w["p_bh"]) for w in later) / tot)
    check("60 instance files read", len(cache) == 60, len(cache))
    return out


def block_j(boot, recs, suite, spfi, frecs, pk, pf):
    sh = later_shares(recs, suite)
    fby = {r["item_id"]: r for r in frecs}
    L = {i: v["L"] for i, v in sh.items()}
    rk = {r["item_id"]: n13.refers(r, CERT) for r in recs}
    rf = {r["item_id"]: n13.refers(r["fi"], CERT) for r in recs}
    for r in recs:
        check("L + C + known share = 1", sh[r["item_id"]]["L"] + sh[r["item_id"]]["C"]
              + Fraction(r["n_known"], r["n_window"]) == 1, r["item_id"])
        check("L = 0 exactly when no order arrives after t_d",
              (L[r["item_id"]] == 0) == (r["n_unknown"] == 0), r["item_id"])
    c20 = [r for r in recs if n13.costly_of(r, 0.20) == 1]
    c10 = [r for r in recs if n13.costly_of(r, 0.10) == 1]
    pops = OrderedDict([("Priced", recs), ("CostlyTwenty", c20), ("CostlyTen", c10),
                        ("FieldCostlyTwenty", [r for r in c20 if r["split"] == "field_changing"]),
                        ("SeqCostlyTwenty", [r for r in c20 if r["split"] == "sequencing_only"])])
    check("J1 populations 1,356 / 186 / 208 / 60 / 126",
          [len(v) for v in pops.values()] == [1356, 186, 208, 60, 126])
    # ---- J1
    dist = OrderedDict()
    for meas, mtok in (("L", ""), ("W", "Work")):
        for ptok, sel in pops.items():
            xs = [float(sh[r["item_id"]][meas]) for r in sel]
            q = qstats(xs)
            mean = float(np.mean(xs))
            zero = sum(1 for r in sel if sh[r["item_id"]][meas] == 0)
            cuts = OrderedDict()
            for ct, cv in LCUTS.items():
                cuts[ct] = sum(1 for r in sel if sh[r["item_id"]][meas] >= cv)
            dist[(meas, ptok)] = (len(sel), q, mean, zero, cuts)
            p = "Later" + mtok + ptok
            for nm, v in zip(("Min", "QOne", "Median", "QThree", "Max"), q):
                add(p + nm, pctv(v))
            add(p + "Mean", pctv(mean))
            add(p + "ZeroN", grp(zero))
            add(p + "ZeroShare", pct(zero, len(sel)))
            for ct, k in cuts.items():
                add(p + ct + "N", grp(k))
                add(p + ct + "Share", pct(k, len(sel)))
    check("L = 0 and W = 0 on the same proposals",
          all((sh[i]["L"] == 0) == (sh[i]["W"] == 0) for i in sh))
    # ---- J2
    groups = OrderedDict([("All", recs)])
    for bt in LBANDS:
        groups[bt] = [r for r in recs if lband(L[r["item_id"]]) == bt]
    check("bands partition the priced", sum(len(groups[b]) for b in LBANDS) == len(recs))
    j2 = OrderedDict()
    for gtok, sel in groups.items():
        for dtok, delta in (("Twenty", 0.20), ("Ten", 0.10)):
            cst = [r for r in sel if n13.costly_of(r, delta) == 1]
            low = [r for r in sel if n13.costly_of(r, delta) == 0]
            ck = [rk[r["item_id"]] for r in cst]
            cf = [rf[r["item_id"]] for r in cst]
            ok_k = [not x for x in ck]
            ok_f = [not x for x in cf]
            mk_c = [not (fby[r["item_id"]]["c_bh_k"] / fby[r["item_id"]]["den"] > TAU) for r in cst]
            mf_c = [not (fby[r["item_id"]]["c_bh_f"] / fby[r["item_id"]]["den"] > TAU) for r in cst]
            mk_2 = [not (rk[r["item_id"]] or (r["split"] == "field_changing" and r["sp"]))
                    for r in cst]
            mf_2 = [not (rf[r["item_id"]] or (r["split"] == "field_changing"
                                              and spfi[r["item_id"]] > TAU)) for r in cst]
            ninst = len({r["instance_id"] for r in cst})
            o = OrderedDict(
                priced=len(sel), costly=len(cst), low=len(low), ninst=ninst, refk=sum(ck),
                reff=sum(cf), missk=sum(ok_k), missf=sum(ok_f),
                differ=sum(1 for a, b in zip(ck, cf) if a != b),
                frk=sum(1 for r in low if rk[r["item_id"]]),
                frf=sum(1 for r in low if rf[r["item_id"]]),
                dis=sum(1 for r in sel if rk[r["item_id"]] != rf[r["item_id"]]),
                cmk=sum(mk_c), cmf=sum(mf_c),
                cdiffer=sum(1 for a, b in zip(mk_c, mf_c) if a != b),
                tmk=sum(mk_2), tmf=sum(mf_2), d=None, dlo=None, dhi=None, cd=None, cdlo=None,
                cdhi=None)
            if ninst >= 10:
                o["d"], o["dlo"], o["dhi"] = n13.paired_ci(
                    boot, cst, [float(x) for x in ok_k], [float(x) for x in ok_f])
                o["cd"], o["cdlo"], o["cdhi"] = n13.paired_ci(
                    boot, cst, [float(x) for x in mk_c], [float(x) for x in mf_c])
            j2[(gtok, dtok)] = o
            p = "Later" + gtok
            if dtok == "Twenty":
                add(p + "Priced", grp(o["priced"]))
            for k, nm in (("costly", "Costly"), ("low", "Low"), ("ninst", "CostlyInstances"),
                          ("refk", "RefK"), ("reff", "RefFI"), ("missk", "MissK"),
                          ("missf", "MissFI"), ("differ", "CostlyDiffer"), ("frk", "FrK"),
                          ("frf", "FrFI"), ("dis", "Disagree"), ("cmk", "CommonMissK"),
                          ("cmf", "CommonMissFI"), ("cdiffer", "CommonDiffer"),
                          ("tmk", "TwoMissK"), ("tmf", "TwoMissFI")):
                add(p + nm + dtok, grp(o[k]))
            if o["d"] is not None:
                add(p + "MissDiff" + dtok, ppv(o["d"]))
                add(p + "MissDiffLo" + dtok, ppv(o["dlo"]))
                add(p + "MissDiffHi" + dtok, ppv(o["dhi"]))
                add(p + "CommonDiff" + dtok, ppv(o["cd"]))
                add(p + "CommonDiffLo" + dtok, ppv(o["cdlo"]))
                add(p + "CommonDiffHi" + dtok, ppv(o["cdhi"]))
    a20, a10 = j2[("All", "Twenty")], j2[("All", "Ten")]
    check("J2 overall row at 0.20 equals the published cells",
          (a20["costly"], a20["refk"], a20["reff"], a20["missk"], a20["missf"], a20["differ"],
           a20["frk"], a20["frf"], a20["dis"], a20["cmk"], a20["cmf"], a20["tmk"], a20["tmf"])
          == (186, 168, 168, 18, 18, 0, 15, 35, 30, 20, 18, 0, 0), a20)
    check("J2 overall row at 0.10 equals the published cells",
          (a10["costly"], a10["missk"], a10["missf"], a10["frk"], a10["frf"], a10["cmk"],
           a10["cmf"], a10["tmk"], a10["tmf"]) == (208, 25, 28, 0, 23, 40, 35, 6, 10), a10)
    for dtok in ("Twenty", "Ten"):
        for k in ("priced", "costly", "low", "refk", "reff", "missk", "missf", "differ", "frk",
                  "frf", "dis", "cmk", "cmf", "cdiffer", "tmk", "tmf"):
            check("bands sum to the overall row ({} {})".format(k, dtok),
                  sum(j2[(b, dtok)][k] for b in LBANDS) == j2[("All", dtok)][k])
    # ---- J3
    applied = sorted((r for r in c20 if not rk[r["item_id"]]), key=lambda r: r["item_id"])
    dis = sorted((r for r in recs if rk[r["item_id"]] != rf[r["item_id"]]),
                 key=lambda r: r["item_id"])
    check("J3: the 18 applied and the 30 disagreements", (len(applied), len(dis)) == (18, 30))
    ab = Counter(lband(L[r["item_id"]]) for r in applied)
    db = Counter(lband(L[r["item_id"]]) for r in dis)
    for bt in LBANDS:
        check("J3 band counts equal J2", ab.get(bt, 0) == j2[(bt, "Twenty")]["missk"]
              and db.get(bt, 0) == j2[(bt, "Twenty")]["dis"])
    add("LaterAppliedMax", pctv(float(max(L[r["item_id"]] for r in applied))))
    add("LaterAppliedMedian", pctv(float(statistics.median(L[r["item_id"]] for r in applied))))
    add("LaterDisagreeMedian", pctv(float(statistics.median(L[r["item_id"]] for r in dis))))
    add("LaterDisagreeMax", pctv(float(max(L[r["item_id"]] for r in dis))))
    # ---- J4
    pos = [r for r in recs if L[r["item_id"]] > 0]
    ad = [abs(pk[r["item_id"]] - pf[r["item_id"]]) for r in pos]
    lv = [float(L[r["item_id"]]) for r in pos]
    dv = [1.0 if rk[r["item_id"]] != rf[r["item_id"]] else 0.0 for r in pos]
    s1 = sstats.spearmanr(lv, ad)
    s2 = sstats.spearmanr(lv, dv)
    add("LaterPositiveN", grp(len(pos)))
    add("LaterSpearmanAbsDiff", "{:.3f}".format(float(s1.statistic)))
    add("LaterSpearmanAbsDiffP", "{:.2g}".format(float(s1.pvalue)))
    add("LaterSpearmanDisagree", "{:.3f}".format(float(s2.statistic)))
    add("LaterSpearmanDisagreeP", "{:.2g}".format(float(s2.pvalue)))
    j4 = []
    for gtok, sel in groups.items():
        a = [abs(pk[r["item_id"]] - pf[r["item_id"]]) for r in sel]
        m, md_ = float(np.mean(a)), float(np.median(a))
        q3 = float(np.percentile(a, 75))
        close = sum(1 for x in a if x <= 0.01)
        add("Later" + gtok + "AbsDiffMean", "{:.3f}".format(m))
        add("Later" + gtok + "AbsDiffMedian", "{:.3f}".format(md_))
        add("Later" + gtok + "AbsDiffQThree", "{:.3f}".format(q3))
        add("Later" + gtok + "CloseShare", pct(close, len(sel)))
        j4.append([LBANDS.get(gtok, "all priced"), len(sel), "{:.3f}".format(m),
                   "{:.3f}".format(md_), "{:.3f}".format(q3), frac(close, len(sel))])
    # ---- J5
    with open(OUT_LATER, "w", newline="", encoding="utf-8") as fh:
        fh.write("# N18 ({}): one row per priced proposal of the direct benchmark at t_d; "
                 "known_share = n_known / n_window, completed_share = n_completed / n_window, "
                 "later_share = n_unknown / n_window (orders arriving after t_d), "
                 "later_work_share = processing time of those orders over the window's total "
                 "(snapshot instance files); n_window = n_completed + n_known + n_unknown; "
                 "later_band fixed at 0, (0, 10%], (10%, 25%], above 25%; costly: 1 costly, 0 "
                 "low-cost, empty undecided; refers flags of the certificate at 0.20; "
                 "second_price_refers = g_orig > 0.20 on field edits only\n".format(VERSION))
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["item_id", "instance_id", "stratum", "primary_class", "edit_type", "t_d",
                    "known_share", "completed_share", "later_share", "later_work_share",
                    "later_band", "costly_delta020", "costly_delta010", "refers_K_G-CERT",
                    "refers_FI_G-CERT", "second_price_refers"])
        for r in recs:
            v = sh[r["item_id"]]
            c2, c1 = n13.costly_of(r, 0.20), n13.costly_of(r, 0.10)
            w.writerow([r["item_id"], r["instance_id"], r["stratum"], r["primary_class"],
                        r["split"], "{:.4f}".format(r["t_d"]), "{:.6f}".format(r["known_share"]),
                        "{:.6f}".format(float(v["C"])), "{:.6f}".format(float(v["L"])),
                        "{:.6f}".format(v["W"]), lband(v["L"]), "" if c2 is None else c2,
                        "" if c1 is None else c1, int(rk[r["item_id"]]), int(rf[r["item_id"]]),
                        int(r["split"] == "field_changing" and r["sp"])])
    # ---- summary
    md("## J. The headline read by the later share (the information gap)", "",
       "Later share L = the window's orders that arrive after t_d over all orders of the window, "
       "n_unknown / (n_completed + n_known + n_unknown) (census counts, "
       "results/n11_decision_time/items.jsonl). Completed share C likewise with n_completed. "
       "These are the orders the known board cannot see and the full-information gate can. The "
       "later share in work W = the processing time of those orders over the window's total. The "
       "rows carry no processing times, so W is read from the snapshot instance files (no "
       "replay). The later orders are rebuilt as the non-maintenance orders released after t_d "
       "(n8_causal.site_state's rule), and the rebuilt set has n_unknown members on every row "
       "(asserted). Bands, fixed before any agreement was read: L = 0; 0 < L <= 10%; "
       "10% < L <= 25%; L > 25%. The certificate refers when its price exceeds 0.20. The common "
       "denominator and the second price are as in block A. Paired K - FI difference in applied "
       "share (pp, n13 paired cluster bootstrap) when the costly proposals sit on at least 10 "
       "instances. File: analysis/N18_fig_later_share.csv.", "",
       "### J1. Distribution of the later share", "")
    body = []
    for meas, mname in (("L", "orders"), ("W", "work")):
        for ptok, pname in LPOPS.items():
            n, q, mean, zero, cuts = dist[(meas, ptok)]
            body.append([mname, pname, n, " / ".join(pctpv(v) for v in q), pctpv(mean),
                         frac(zero, n)] + [frac(k, n) for k in cuts.values()])
    md_table(["measured in", "population", "n", "min / Q1 / median / Q3 / max", "mean",
              "share = 0", "share >= 10%", "share >= 20%", "share >= 30%"], body)
    for dtok, dname in (("Twenty", "0.20"), ("Ten", "0.10")):
        md("### J2. By band, delta = {}".format(dname), "")
        body = []
        for gtok in groups:
            o = j2[(gtok, dtok)]
            body.append([LBANDS.get(gtok, "all priced"), o["priced"], o["costly"], o["ninst"],
                         o["refk"], o["reff"], o["missk"], o["missf"], o["differ"],
                         "{} [{}, {}]".format(ppv(o["d"]), ppv(o["dlo"]), ppv(o["dhi"]))
                         if o["d"] is not None else "counts only (< 10 instances)",
                         o["frk"], o["frf"], o["dis"],
                         "{} / {} (differ {})".format(o["cmk"], o["cmf"], o["cdiffer"]),
                         "{} / {}".format(o["tmk"], o["tmf"])])
        md_table(["band", "priced", "costly", "instances (costly)", "costly referred K",
                  "costly referred FI", "applied K", "applied FI", "costly where K and FI differ",
                  "applied K - FI (pp) [95% CI]", "low-cost referred K", "low-cost referred FI",
                  "all proposals where K and FI disagree",
                  "common denominator: applied K / FI", "second price: applied K / FI"], body)
    md("### J3. The 18 applied costly proposals and the 30 disagreements, by band", "")
    md_table(["set"] + list(LBANDS.values()) + ["median L", "max L"],
             [["18 applied (delta 0.20)"] + [ab.get(b, 0) for b in LBANDS] +
              [pctpv(float(statistics.median(L[r["item_id"]] for r in applied))),
               pctpv(float(max(L[r["item_id"]] for r in applied)))],
              ["30 disagreements"] + [db.get(b, 0) for b in LBANDS] +
              [pctpv(float(statistics.median(L[r["item_id"]] for r in dis))),
               pctpv(float(max(L[r["item_id"]] for r in dis)))]])
    md_table(["item", "set", "class", "edit type", "t_d (bh)", "later share", "band", "p_K",
              "p_FI"],
             [[r["item_id"], s_, r["primary_class"], r["split"], "{:.2f}".format(r["t_d"]),
               pctpv(float(L[r["item_id"]])), LBANDS[lband(L[r["item_id"]])],
               "{:.4f}".format(pk[r["item_id"]]), "{:.4f}".format(pf[r["item_id"]])]
              for s_, lst_ in (("applied", applied), ("disagreement", dis)) for r in lst_])
    md("### J4. Direction of the effect", "",
       "Over the {:,} priced proposals with L > 0: Spearman's rho of L with |p_K - p_FI| = {:.3f} "
       "(p = {:.2g}), and of L with the indicator that the two readings disagree = {:.3f} "
       "(p = {:.2g}).".format(len(pos), float(s1.statistic), float(s1.pvalue),
                              float(s2.statistic), float(s2.pvalue)), "")
    md_table(["band", "priced", "mean |p_K - p_FI|", "median", "Q3", "|p_K - p_FI| <= 0.01"], j4)
    # facts
    d20, d10 = dist[("L", "CostlyTwenty")], dist[("L", "CostlyTen")]
    dpr = dist[("L", "Priced")]
    hi_b = [b for b in ("TenToTwentyFive", "AboveTwentyFive")]
    hi20 = OrderedDict((k, sum(j2[(b, "Twenty")][k] for b in hi_b))
                       for k in ("priced", "costly", "refk", "reff", "missk", "differ", "frk",
                                 "frf", "dis", "cmk", "cmf", "tmk", "tmf"))
    hi10 = OrderedDict((k, sum(j2[(b, "Ten")][k] for b in hi_b))
                       for k in ("costly", "missk", "missf", "differ"))
    add("LaterAboveTenPriced", grp(hi20["priced"]))
    add("LaterAboveTenCostlyTwenty", hi20["costly"])
    add("LaterAboveTenRefKTwenty", hi20["refk"])
    add("LaterAboveTenRefFITwenty", hi20["reff"])
    add("LaterAboveTenDisagreeTwenty", hi20["dis"])
    add("LaterAboveTenCostlyTen", hi10["costly"])
    add("LaterAboveTenCostlyDifferTen", hi10["differ"])
    md("Above 10% (the two upper bands together): {} priced, {} costly at 0.20 (referred {} on K "
       "and {} with FI, applied {}), {} low-cost referred on K and {} with FI, {} disagreements; "
       "at 0.10, {} costly, applied {} on K and {} with FI, {} differ.".format(
           hi20["priced"], hi20["costly"], hi20["refk"], hi20["reff"], hi20["missk"], hi20["frk"],
           hi20["frf"], hi20["dis"], hi10["costly"], hi10["missk"], hi10["missf"],
           hi10["differ"]), "")
    zr = j2[("Zero", "Twenty")]
    facts([
        "A median {} of the window's orders arrive after the decision instant of a priced "
        "proposal (quartiles {} and {}), and {} of the 1,356 priced proposals have at least 10% "
        "of the orders still to arrive.".format(pctpv(dpr[1][2]), pctpv(dpr[1][1]),
                                                pctpv(dpr[1][3]), pctp(dpr[4]["AtLeastTen"], 1356)),
        "Of the 186 costly proposals at delta = 0.20, {} ({}) are decided with at least 10% of "
        "the window's orders still to arrive and {} ({}) with at least 20%.".format(
            d20[4]["AtLeastTen"], pctp(d20[4]["AtLeastTen"], 186), d20[4]["AtLeastTwenty"],
            pctp(d20[4]["AtLeastTwenty"], 186)),
        "On the {} costly proposals decided with more than 10% of the orders still to arrive, "
        "the certificate refers {} on the known board and {} with full information, and the two "
        "readings differ on {}.".format(hi20["costly"], hi20["refk"], hi20["reff"],
                                        hi20["differ"]),
        ("Only {} priced proposals have no order still to arrive, and none of them is "
         "costly.".format(zr["priced"]) if zr["costly"] == 0 else
         "On the {} costly proposals with no order still to arrive, the certificate refers {} "
         "on both readings and applies {}.".format(zr["costly"], zr["refk"], zr["missk"])),
        "Of the 18 costly proposals the certificate applies, {} are decided with at most 10% of "
        "the orders still to arrive (median {}), and {} of the 30 disagreements between the two "
        "readings sit between 10% and 25%.".format(
            ab.get("UpToTen", 0) + ab.get("Zero", 0),
            pctpv(float(statistics.median(L[r["item_id"]] for r in applied))),
            db.get("TenToTwentyFive", 0)),
        "At delta = 0.10 and with 10% to 25% of the orders still to arrive, the two readings "
        "differ on {} of {} costly proposals ({} applied on the known board and {} with full "
        "information).".format(j2[("TenToTwentyFive", "Ten")]["differ"],
                               j2[("TenToTwentyFive", "Ten")]["costly"],
                               j2[("TenToTwentyFive", "Ten")]["missk"],
                               j2[("TenToTwentyFive", "Ten")]["missf"]),
        "Above 25% there are {} costly proposals on {} instances, and the certificate refers "
        "all of them on both readings.".format(j2[("AboveTwentyFive", "Twenty")]["costly"],
                                              j2[("AboveTwentyFive", "Twenty")]["ninst"])
        if j2[("AboveTwentyFive", "Twenty")]["missk"] == j2[("AboveTwentyFive", "Twenty")]["missf"] == 0
        else "Above 25% the certificate applies {} costly proposals on the known board and {} "
        "with full information.".format(j2[("AboveTwentyFive", "Twenty")]["missk"],
                                        j2[("AboveTwentyFive", "Twenty")]["missf"]),
        "Over the {:,} priced proposals with a later order, Spearman's rank correlation of the "
        "later share with the price difference |p_K - p_FI| is {:.3f}, and with disagreement "
        "of the two readings it is {:.3f}.".format(len(pos), float(s1.statistic),
                                                    float(s2.statistic)),
        "The mean price difference |p_K - p_FI| is {} in the four bands from L = 0 to L above "
        "25%.".format(", ".join(r[2] for r in j4[1:]))])
    return j2, dist, (s1, s2, pos), ab, db, hi20


SUITE = {}


def suite_family(iid):
    return SUITE[iid]["family_id"]


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main():
    for k, p in IN18.items():
        if not Path(p).is_file() and k not in NOT_SHIPPED_OK:
            raise SystemExit("missing input {}: {}".format(k, p))
    hashes, items_dt, _pub, boot, fc = n13.load_inputs()
    check("60 bootstrap clusters, 20,000 replicates, n2 seed",
          boot.k == 60 and boot.idx.shape == (20000, 60) and n13.n2.SEED == 20261026)
    recs, by = n16.build_recs(items_dt, fc)
    suite = {it["item_id"]: it for it in n13.read_jsonl(n13.IN["suite"])}
    SUITE.update(suite)
    full_br = D.full_brackets()
    # the FI second price (n13 section J's records) and the site-schedule variant
    jrec, k_sp = n13.j_records(fc, items_dt)
    spfi = {r["item_id"]: r["sp"] for r in jrec["FI"]}
    for r in recs:
        check("K second price equals n13 section J's", abs(k_sp[r["item_id"]] - r["g_orig"]) < 1e-12,
              r["item_id"])
    site = {}
    for x in n13.read_csv(n13.IN["rows_direct"]):
        if x["dataset"] == "direct_td" and x["item_id"] in by and x["priced"] == "True":
            site[x["item_id"]] = site_price(float(x["obj_orig"]), float(x["ref1"]))
    check("s2_site on every priced proposal", set(site) >= {r["item_id"] for r in recs})
    MD.extend(["# N18: from-logs further checks ({})".format(VERSION), "",
               "Generated by `code/scripts/n18_further_checks.py` on cores 14-15 (one thread) from "
               "the logged results only: no solve, no model call, no GPU. It imports "
               "code/scripts/n16_robustness.py (l1-n16-robustness-3, frozen) for its loaders and "
               "helpers and, through it, n13_fromlogs.py (core allowance set to 14-15 in memory; "
               "the file on disk is untouched). Cluster bootstrap: n2 seed {}, {} replicates, {} "
               "instance clusters. Macros: analysis/N18_macros.tex (prefix \\nEighteen), copied "
               "to manuscript/macros_n18.tex.".format(n13.n2.SEED, n13.n2.B_BOOT, boot.k), ""])
    n16.section0(boot, recs)          # N16's own published-cell assertions, re-run
    c20, applied = section0(recs, by, spfi, site)
    frecs = n13.section_f(boot, fc, items_dt)
    block_a(boot, recs, spfi, frecs)
    pk, pf = block_b(boot, recs, c20)
    block_c(recs, applied, suite, pk, pf, site)
    cells, _suite16 = n16.block_f(boot, fc)
    block_d(boot, cells, suite)
    e1cells = n13.load_e1()
    block_e(e1cells)
    block_f(suite, e1cells)
    block_g(recs)
    block_h(fc)
    llm_recs, _n_rows = n16.block_d2(full_br)
    block_i(recs, site, llm_recs)
    block_j(boot, recs, suite, spfi, frecs, pk, pf)
    hashes18 = OrderedDict(hashes)
    hashes18.update((k, input_sha256(k, p)) for k, p in IN18.items())
    hashes18.update((k, input_sha256(k, p)) for k, p in n16.IN16.items() if k not in hashes18)
    paths = OrderedDict(list(n13.IN.items()) + list(n16.IN16.items()) + list(IN18.items()))
    n_reused = n16.NCHECK[0] + len(n13.CHECKS)
    MD.extend(["## Inputs", ""] + ["- {} `{}` sha256 {}".format(
        k, Path(paths[k]).relative_to(ROOT), v) for k, v in hashes18.items()] + [""])
    # every macro already on disk keeps its value (version 1 against version 2)
    old = macros_of(OUT_TEX) if OUT_TEX.is_file() else {}
    new = {}
    for ln in LINES[1:]:
        head, val = ln.split("}{", 1)
        new[head[len("\\newcommand{\\"):]] = val[:-1]
    kept = [k for k in old if k in new and old[k] == new[k]]
    check("every macro of the file on disk keeps its name and value",
          len(kept) == len(old), sorted(set(old) - set(kept))[:10])
    OLD_KEPT[0] = (len(old), len(kept), len(new) - len(old))
    OUT_TEX.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    shutil.copyfile(OUT_TEX, OUT_MANU)
    OUT_MD.write_text("\n".join(MD + [
        "{} assertions passed in n18 (plus {} in the reused n16 and n13 functions: {} n16, {} "
        "n13); {} macros ({} of the previous macros file kept with the same value, {} "
        "new).".format(NCHECK[0], n_reused, n16.NCHECK[0], len(n13.CHECKS), len(NAMES),
                       OLD_KEPT[0][1], OLD_KEPT[0][2])]) + "\n", encoding="utf-8")
    print("[n18] {} macros, {} assertions passed (+{} reused: n16 {}, n13 {})".format(
        len(NAMES), NCHECK[0], n_reused, n16.NCHECK[0], len(n13.CHECKS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
