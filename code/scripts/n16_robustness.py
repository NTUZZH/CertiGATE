#!/usr/bin/env python3
"""N16: robustness of the decision-time comparison, recomputed from the logs only.

Blocks (pre-specified design):

  A  costly proposals referred on the known board (K) and with full information
     (FI), with the K-only and FI-only splits and the split by edit type;
  B  the comparison where the information gap is large: the known share of the
     window at t_d, and the K-versus-FI scoring within t_d groups, known-share
     bands and known-share quartiles (paired cluster bootstrap);
  C  the K and FI prices of G-CERT and G-CERT-M on one common denominator at
     tau = 0.20 (n13 section F, extended to delta 0.20 and to G-CERT);
  D  the second price under the four dispatching rules (D1) and behind the LLM
     proposers of the gate stress test (D2);
  E  operating curves over the threshold on K, alone and with the second price;
  F  referral of cost-bearing proposals that pass the feasibility check, split
     by equivalence to the reference translation (Table 6 arms);
  G  small facts (orders arriving after the window start, the strict
     issuability rule, the paired G-CERT difference at delta 0.10);
  H  (follow-up) translation fidelity on repeat 0 for each Table 6 cell, and the
     per-arm figure input of fig3_guard_value_dt.py with the Opus fidelity read
     from the default-thinking cell;
  I  (follow-up, design J5) the second price against the site's own schedule: the
     bound of the untouched known board replaced by that board's weighted tardiness
     under the dispatching rule, on the direct benchmark (I1), under the three other
     rules (I2), behind the LLM proposers (I3) and with the tolerance lowered to the
     cost level (I4).

Every number comes from result files on disk: no solve, no model call, no GPU.
The script imports n13_fromlogs.py for its loaders, its scoring and its cluster
bootstrap (same seed and replicate count), asserts the published cells first and
aborts on any mismatch.  n13_fromlogs.py refuses to run outside cores 12-13; this
script runs on cores 14-15, so it loads n13's source with that one constant set to
{14, 15} (asserted to occur exactly once) and leaves the file on disk untouched.

Outputs: analysis/N16_macros.tex (prefix \\nSixteen), analysis/N16_summary.md,
analysis/N16_fig_known_share.csv, analysis/N16_fig_curves.csv,
analysis/N16_fig_guard_value.csv.
Run: OMP_NUM_THREADS=1 taskset -c 14-15 python3 code/scripts/n16_robustness.py
Version: l1-n16-robustness-3 (adds block I and the \\nSixteenI... macros; version 2 added
the translation fidelity by Table 6 cell, the \\nSixteenFidelity... macros and
analysis/N16_fig_guard_value.csv)
"""
import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_v] = "1"

import csv  # noqa: E402
import json  # noqa: E402
import statistics  # noqa: E402
import sys  # noqa: E402
import types  # noqa: E402
from collections import Counter, OrderedDict, defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

ALLOWED_CORES = {14, 15}
_aff = set(os.sched_getaffinity(0))
if not _aff <= ALLOWED_CORES and not os.environ.get("CERTIGATE_ANY_CORES"):
    raise SystemExit("REFUSING TO RUN: affinity {} is not inside cores 14-15 "
                     "(run under taskset -c 14-15)".format(sorted(_aff)))

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _load_n13():
    """n13_fromlogs as a module, with its core allowance set to this script's cores."""
    path = SCRIPTS_DIR / "n13_fromlogs.py"
    src = path.read_text(encoding="utf-8")
    old = "ALLOWED_CORES = {12, 13}"
    if src.count(old) != 1:
        raise SystemExit("n13_fromlogs.py core allowance not found exactly once")
    src = src.replace(old, "ALLOWED_CORES = {14, 15}")
    mod = types.ModuleType("n13_fromlogs")
    mod.__file__ = str(path)
    sys.modules["n13_fromlogs"] = mod
    exec(compile(src, str(path), "exec"), mod.__dict__)  # noqa: S102
    return mod


n13 = _load_n13()
np = n13.np
D = n13.D
e1dg = n13.e1dg

VERSION = "l1-n16-robustness-3"
ROOT = n13.ROOT
ANALYSIS = n13.ANALYSIS
RESULTS = n13.RESULTS
OUT_TEX = ANALYSIS / "N16_macros.tex"
OUT_MD = ANALYSIS / "N16_summary.md"
OUT_KS = ANALYSIS / "N16_fig_known_share.csv"
OUT_CURVES = ANALYSIS / "N16_fig_curves.csv"
OUT_GUARD = ANALYSIS / "N16_fig_guard_value.csv"
TWIN = RESULTS / "n11_e2e" / "twin"
IN16 = OrderedDict([
    ("n14_rows", ANALYSIS / "N14_rows.csv"),
    ("n15_macros", ANALYSIS / "N15_macros.tex"),
    ("n13_macros", ANALYSIS / "N13_macros.tex"),
    ("n11_macros", ANALYSIS / "N11_macros.tex"),
    ("n11f_paired_macros", ANALYSIS / "N11F_paired_macros.tex"),
    ("n11_literal_tables", ANALYSIS / "N11_literal_tables.csv"),
    ("d3_td", RESULTS / "n11_e2e" / "twin" / "primary" / "tables" /
     "D3_translation_equivalence.csv"),
    ("macros_n11_manu", ROOT / "manuscript" / "macros_n11.tex"),
    ("fig4_inputs", ANALYSIS / "N11_fig4_inputs.csv"),
    ("fig3_dt_script", ROOT / "manuscript" / "figures" / "fig3_guard_value_dt.py"),
    ("opus_raw", RESULTS / "grid_e1_hosted_opus" / "proposals_raw.dedup.jsonl"),
    ("t3_pub", ANALYSIS / "T3_guard_value_curve.csv"),
    ("d3_pub", ANALYSIS / "D3_translation_equivalence.csv"),
    ("t3_iss0", RESULTS / "n11_e2e" / "twin" / "iss0" / "tables" / "T3_guard_value_curve.csv"),
    ("d3_iss0", RESULTS / "n11_e2e" / "twin" / "iss0" / "tables" /
     "D3_translation_equivalence.csv"),
    ("t3_td", RESULTS / "n11_e2e" / "twin" / "primary" / "tables" / "T3_guard_value_curve.csv"),
])
RULES = OrderedDict([("atc", "Atc"), ("wspt", "Wspt"), ("pfifo", "Pfifo"), ("edd", "Edd")])
RULE_NAME = {"atc": "ATC (k = 2), the site's rule", "wspt": "WSPT",
             "pfifo": "priority class, then FIFO", "edd": "EDD"}

DELTAS = OrderedDict([("Twenty", 0.20), ("Ten", 0.10)])
TOK = OrderedDict([("G-CERT", "Cert"), ("G-CERT-M", "CertM"), ("D-REL1", "RelOne"),
                   ("D-REL2", "RelTwo"), ("D-ABS", "Abs")])
RATIO = ("G-CERT", "G-CERT-M", "D-REL1", "D-REL2")
SETTING = OrderedDict([("G-CERT", 0.20), ("G-CERT-M", 0.20), ("D-REL1", 0.02),
                       ("D-REL2", 0.02), ("D-ABS", 0.8119)])
TAU = n13.TAU
FLOOR = D.FLOOR_BH
SPLIT_TOK = OrderedDict([("sequencing_only", "Seq"), ("field_changing", "Field")])

LINES = ["% N16 macros ({}); generated by code/scripts/n16_robustness.py from the logged "
         "results only (no solve, no model call)".format(VERSION)]
NAMES = set()
MD = []
NCHECK = [0]


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def check(what, ok, detail=""):
    if not ok:
        raise SystemExit("[n16] ASSERTION FAILED: {} ({})".format(what, detail))
    NCHECK[0] += 1


def add(name, value):
    full = "nSixteen" + name
    if not full.isalpha():
        raise SystemExit("macro name not alphabetic: " + full)
    if full in NAMES:
        raise SystemExit("duplicate macro " + full)
    NAMES.add(full)
    LINES.append("\\newcommand{\\" + full + "}{" + str(value) + "}")


def grp(n):
    return "{:,}".format(int(n)).replace(",", "{,}")


def pct(k, n):
    return "{:.1f}\\%".format(100.0 * k / n) if n else "n/a"


def pctv(x):
    return "n/a" if x is None else "{:.1f}\\%".format(100.0 * x)


def pctp(k, n):
    return "{:.1f}%".format(100.0 * k / n) if n else "n/a"


def pctpv(x):
    return "n/a" if x is None else "{:.1f}%".format(100.0 * x)


def ppv(x):
    """Percentage points with one decimal, '-0.0' printed as '0.0'."""
    if x is None:
        return "n/a"
    s = "{:.1f}".format(100.0 * x)
    return "0.0" if s == "-0.0" else s


def frac(k, n):
    return "{}/{} ({})".format(k, n, pctp(k, n))


def norm_pp(s):
    return "0.0" if s == "-0.0" else s


def md(*lines):
    MD.extend(lines)


def md_table(head, body):
    out = ["| " + " | ".join(str(h) for h in head) + " |",
           "|" + "|".join("---" for _ in head) + "|"]
    for row in body:
        out.append("| " + " | ".join("" if c is None else str(c) for c in row) + " |")
    out.append("")
    MD.extend(out)


def f6(x):
    return "" if x is None else "{:.6f}".format(x)


def qstats(xs):
    """(min, Q1, median, Q3, max), numpy linear percentiles as n13.qtiles."""
    a = np.asarray(xs, dtype=float)
    q1, q2, q3 = (float(v) for v in np.percentile(a, [25, 50, 75]))
    return float(a.min()), q1, q2, q3, float(a.max())


def realised_range(obj, anchor, iid, full_br):
    """The realised marginal cost on the original fields, as n11_forecast.attach_orig_truth
    reads it (D.attach_truth with the untouched full-window bracket as both brackets)."""
    b = full_br.get((iid, D.BASE_FP))
    if b is None or obj is None:
        return None, None
    lo_e, up_e, _p = D.ends(b)
    ms = [D.gfun(obj, x) - D.gfun(anchor, x) for x in D.xs_of(lo_e, up_e)]
    return min(ms), max(ms)


def cost_class(lo, hi, delta):
    if lo is None or hi is None:
        return None
    if lo > delta:
        return 1
    if hi <= delta:
        return 0
    return None


# --------------------------------------------------------------------------- #
# Inputs and the published cells                                               #
# --------------------------------------------------------------------------- #
def build_recs(items_dt, fc):
    by = {r["item_id"]: r for r in items_dt if r["set"] == "published"}
    recs = []
    for iid in sorted(fc["K"]):
        r = fc["K"][iid]
        it = by[iid]
        g = (it["dt_obj_orig"] - it["an_lb"]) / max(it["an_lb"], FLOOR)
        tot = it["n_completed"] + it["n_known"] + it["n_unknown"]
        recs.append(dict(r, g_orig=g, sp=(g > TAU), fi=fc["FI"][iid], t_d=float(it["t_d"]),
                         n_known=it["n_known"], n_completed=it["n_completed"],
                         n_unknown=it["n_unknown"], n_window=tot,
                         known_share=it["n_known"] / tot))
    return recs, by


def sp_flag(r, g):
    return n13.refers(r, g) or (r["split"] == "field_changing" and r["sp"])


def section0(boot, recs):
    """The published cells named in the design, before any new number."""
    n15m = n13.macros_of(IN16["n15_macros"])
    exp = {0.20: dict(costly=186, low=1170, miss=(18, 18, 18, 18, 17),
                      miss_fi=(18, 18, 18, 18, 16), fr=(15, 14, 80, 33, 81),
                      miss_two=(0, 0, 0, 0, 0), fr_two=(22, 21, 86, 40, 87)),
           0.10: dict(costly=208, low=1148, miss=(25, 26, 21, 21, 20))}
    check("1,356 priced proposals", len(recs) == 1356, len(recs))
    rows = []
    for dtok, delta in DELTAS.items():
        e = exp[delta]
        costly = [r for r in recs if n13.costly_of(r, delta) == 1]
        low = [r for r in recs if n13.costly_of(r, delta) == 0]
        check("costly / low-cost at delta {}".format(delta),
              (len(costly), len(low)) == (e["costly"], e["low"]), (len(costly), len(low)))
        check("N15 macros costly / low at delta {}".format(delta),
              n15m["nFifteenCostly" + dtok] == str(len(costly))
              and n15m["nFifteenLow" + dtok] == grp(len(low)))
        for j, (g, gt) in enumerate(TOK.items()):
            s = n13.score(boot, recs, lambda r, g=g: n13.refers(r, g), delta, with_ci=False)
            s2 = n13.score(boot, recs, lambda r, g=g: sp_flag(r, g), delta, with_ci=False)
            mfi = sum(1 for r in costly if not n13.refers(r["fi"], g))
            check("applied on K, {} delta {}".format(g, delta), s["miss"] == e["miss"][j],
                  s["miss"])
            check("N15 macro {}Miss{}".format(gt, dtok),
                  n15m["nFifteen{}Miss{}".format(gt, dtok)] == str(s["miss"]))
            if delta == 0.20:
                check("applied with FI, {}".format(g), mfi == e["miss_fi"][j], mfi)
                check("low-cost referred on K, {}".format(g), s["fr"] == e["fr"][j], s["fr"])
                check("second price applied, {}".format(g), s2["miss"] == e["miss_two"][j],
                      s2["miss"])
                check("second price low-cost referred, {}".format(g),
                      s2["fr"] == e["fr_two"][j], s2["fr"])
                check("N15 macros {} FI / Fr / Two".format(g),
                      n15m["nFifteen{}MissFI{}".format(gt, dtok)] == str(mfi)
                      and n15m["nFifteen{}Fr{}".format(gt, dtok)] == str(s["fr"])
                      and n15m["nFifteen{}TwoMiss{}".format(gt, dtok)] == str(s2["miss"])
                      and n15m["nFifteen{}TwoFr{}".format(gt, dtok)] == str(s2["fr"]))
            rows.append(["{:.2f}".format(delta), g, "{}/{}".format(s["miss"], s["costly"]),
                         mfi if delta == 0.20 else "", "{}/{}".format(s["fr"], s["cheap"]),
                         "{}/{}".format(s2["miss"], s2["costly"]),
                         "{}/{}".format(s2["fr"], s2["cheap"])])
    md("## 0. Published cells asserted before any new number", "",
       "Direct benchmark at the decision instant, 1,356 priced proposals, truth = realised "
       "marginal cost on the original fields. Each cell below equals the design's list and the "
       "N15 macro (analysis/N15_macros.tex); the run aborts on any mismatch.", "")
    md_table(["delta", "design", "applied K", "applied FI", "low-cost referred K",
              "applied, second price", "low-cost referred, second price"], rows)


# --------------------------------------------------------------------------- #
# A. Costly proposals referred on K and with FI                               #
# --------------------------------------------------------------------------- #
def block_a(recs):
    md("## A. Costly proposals referred on K and with FI", "",
       "Referred is the complement of applied: a costly proposal (realised cost above delta) "
       "that the design refers. K = known board at t_d, FI = the same gate at t_d with every "
       "order of the window known. Both = referred under K and under FI; K only = referred on "
       "K and applied with FI; FI only = the reverse. Edit type as in N15: field edit = the "
       "proposal sets a priority or reassigns a window; sequencing only = every other "
       "proposal with operations (no costly proposal is empty, asserted).", "")
    sets = {}
    for dtok, delta in DELTAS.items():
        costly = [r for r in recs if n13.costly_of(r, delta) == 1]
        check("no costly proposal without operations at {}".format(delta),
              all(r["split"] in SPLIT_TOK for r in costly))
        cs = Counter(r["split"] for r in costly)
        for sp, st in SPLIT_TOK.items():
            add("Costly" + st + dtok, cs.get(sp, 0))
        body = []
        for g, gt in TOK.items():
            rk = {r["item_id"] for r in costly if n13.refers(r, g)}
            rf = {r["item_id"] for r in costly if n13.refers(r["fi"], g)}
            sets[(g, delta)] = (rk, rf)
            vals = OrderedDict([("K", rk), ("FI", rf), ("Both", rk & rf), ("KOnly", rk - rf),
                                ("FIOnly", rf - rk)])
            for k, v in vals.items():
                add(gt + "Ref" + k + dtok, len(v))
            row = [g, len(costly)] + ["{} ({})".format(len(v), pctp(len(v), len(costly)))
                                      for v in vals.values()]
            for sp, st in SPLIT_TOK.items():
                ids = {r["item_id"] for r in costly if r["split"] == sp}
                for k in ("K", "FI", "Both"):
                    add(gt + "Ref" + st + k + dtok, len(vals[k] & ids))
                row.append("{} / {} / {} of {}".format(len(vals["K"] & ids), len(vals["FI"] & ids),
                                                     len(vals["Both"] & ids), len(ids)))
            body.append(row)
        md("### delta = {:.2f}: {} costly proposals ({} sequencing only, {} field edits)".format(
            delta, len(costly), cs.get("sequencing_only", 0), cs.get("field_changing", 0)), "")
        md_table(["design", "costly", "referred K", "referred FI", "under both", "K only",
                  "FI only", "sequencing only: K / FI / both", "field edits: K / FI / both"],
                 body)
    # the set identity at delta 0.20
    costly20 = [r for r in recs if n13.costly_of(r, 0.20) == 1]
    seq20 = {r["item_id"] for r in costly20 if r["split"] == "sequencing_only"}
    ref_set = sets[("G-CERT", 0.20)][0]
    for g in RATIO:
        rk, rf = sets[(g, 0.20)]
        check("delta 0.20, {}: the K set equals the FI set".format(g), rk == rf,
              (len(rk - rf), len(rf - rk)))
        check("delta 0.20, {}: 168 referred".format(g), len(rk) == 168, len(rk))
        check("delta 0.20, {}: every sequencing-only costly proposal referred under both"
              .format(g), seq20 <= (rk & rf), len(seq20 - (rk & rf)))
        check("delta 0.20, {}: the same 168 proposals as G-CERT".format(g), rk == ref_set)
    check("126 sequencing-only costly proposals at 0.20", len(seq20) == 126, len(seq20))
    applied20 = [r for r in costly20 if r["item_id"] not in ref_set]
    check("the costly proposals the ratio designs apply at 0.20 are all field edits",
          all(r["split"] == "field_changing" for r in applied20))
    rk, rf = sets[("D-ABS", 0.20)]
    fi_only = sorted(rf - rk)
    md("Set identity at delta = 0.20 (asserted): the four ratio designs refer the same {} of "
       "the {} costly proposals on K and with FI (the K set equals the FI set for each design "
       "and the four sets are identical), and those {} contain all {} sequencing-only costly "
       "proposals; the {} applied ones are all field edits. D-ABS refers {} on K and {} with "
       "FI; the FI-only proposal{}: {}.".format(
           len(ref_set), len(costly20), len(ref_set), len(seq20), len(applied20), len(rk),
           len(rf), "" if len(fi_only) == 1 else "s", ", ".join(fi_only) if fi_only else "none"),
       "")
    ten = {g: sets[(g, 0.10)] for g in TOK}
    md("At delta = 0.10 the K and FI sets differ for G-CERT ({} K only, {} FI only), G-CERT-M "
       "({} K only, {} FI only) and D-ABS ({} K only, {} FI only); D-REL1 and D-REL2 refer the "
       "same {} costly proposals under both readings.".format(
           len(ten["G-CERT"][0] - ten["G-CERT"][1]), len(ten["G-CERT"][1] - ten["G-CERT"][0]),
           len(ten["G-CERT-M"][0] - ten["G-CERT-M"][1]),
           len(ten["G-CERT-M"][1] - ten["G-CERT-M"][0]),
           len(ten["D-ABS"][0] - ten["D-ABS"][1]), len(ten["D-ABS"][1] - ten["D-ABS"][0]),
           len(ten["D-REL2"][0])), "")
    check("D-REL1 and D-REL2 refer the same set at 0.10, K = FI",
          ten["D-REL1"][0] == ten["D-REL1"][1] == ten["D-REL2"][0] == ten["D-REL2"][1])


# --------------------------------------------------------------------------- #
# B. Where the information gap is large                                        #
# --------------------------------------------------------------------------- #
B_DESIGNS = OrderedDict([("G-CERT", "Cert"), ("G-CERT-M", "CertM"), ("D-REL2", "RelTwo")])


def group_scores(boot, sel, g, delta):
    costly = [r for r in sel if n13.costly_of(r, delta) == 1]
    low = [r for r in sel if n13.costly_of(r, delta) == 0]
    mk = [not n13.refers(r, g) for r in costly]
    mf = [not n13.refers(r["fi"], g) for r in costly]
    out = OrderedDict(
        priced=len(sel), costly=len(costly), low=len(low), miss_k=sum(mk), miss_fi=sum(mf),
        both=sum(1 for a, b in zip(mk, mf) if a and b),
        k_only=sum(1 for a, b in zip(mk, mf) if a and not b),
        fi_only=sum(1 for a, b in zip(mk, mf) if b and not a),
        fr_k=sum(1 for r in low if n13.refers(r, g)),
        fr_fi=sum(1 for r in low if n13.refers(r["fi"], g)),
        n_inst=len({r["instance_id"] for r in costly}), diff=None, lo=None, hi=None)
    if out["n_inst"] >= 10:
        out["diff"], out["lo"], out["hi"] = n13.paired_ci(
            boot, costly, [1.0 if m else 0.0 for m in mk], [1.0 if m else 0.0 for m in mf])
    return out


def shortfall(sel):
    seq = [r for r in sel if r["split"] == "sequencing_only" and r["dmg"] is not None
           and r["dmg"] > 2.0]
    sf = [max(0.0, r["dmg"] - r["p_D-ABS"]) for r in seq]
    real = sum(r["dmg"] for r in seq)
    return (len(seq), statistics.median(sf) if sf else None, sum(sf), real)


def block_b(boot, recs, by):
    md("## B. The comparison where the information gap is large", "",
       "Known share at t_d (n13 section H): the orders on the known board K at t_d (queued, "
       "running and planned orders already on the calendar, the items' n_known) over all "
       "orders of the window (n_completed + n_known + n_unknown). Orders completed by t_d sit "
       "in the denominator and not in the numerator; orders arriving after t_d are n_unknown "
       "(the 'later orders'). The window starts at t = 0.", "")
    iss = sorted((r for r in by.values() if r["issuable"]), key=lambda r: r["item_id"])
    check("1,723 issuable instructions", len(iss) == 1723, len(iss))
    for r in iss:
        check("t_d = t_known on every issuable item", r["t_d"] == r["t_known"], r["item_id"])
    pops = OrderedDict([
        ("Priced", [dict(known_share=r["known_share"], later=r["n_unknown"], t_d=r["t_d"],
                         comp=r["n_completed"], win=r["n_window"]) for r in recs]),
        ("Issuable", [dict(known_share=r["n_known"] / (r["n_completed"] + r["n_known"]
                                                       + r["n_unknown"]),
                           later=r["n_unknown"], t_d=float(r["t_d"]), comp=r["n_completed"],
                           win=r["n_completed"] + r["n_known"] + r["n_unknown"])
                      for r in iss])])
    body = []
    for pname, xs in pops.items():
        ks = qstats([x["known_share"] for x in xs])
        lt = qstats([x["later"] for x in xs])
        rel = qstats([(x["win"] - x["later"]) / x["win"] for x in xs])
        z = sum(1 for x in xs if x["t_d"] == 0.0)
        for nm, v in zip(("Min", "QOne", "Median", "QThree", "Max"), ks):
            add("BKnownShare" + nm + pname, pctv(v))
        for nm, v in zip(("Min", "QOne", "Median", "QThree", "Max"), lt):
            add("BLater" + nm + pname, grp(round(v)))
        add("BTdZeroCount" + pname, grp(z))
        add("BTdZeroShare" + pname, pct(z, len(xs)))
        add("BN" + pname, grp(len(xs)))
        body.append([pname.lower(), len(xs),
                     " / ".join(pctpv(v) for v in ks),
                     " / ".join("{:.0f}".format(v) for v in lt),
                     " / ".join(pctpv(v) for v in rel), frac(z, len(xs))])
    md("### B0. Distribution (min / Q1 / median / Q3 / max)", "")
    md_table(["population", "n", "known share", "orders arriving after t_d",
              "share released by t_d (completed + known)", "t_d at the window start"], body)
    # groups
    groups = OrderedDict()
    groups["TdZero"] = ("t_d at the window start", [r for r in recs if r["t_d"] == 0.0])
    groups["TdLater"] = ("t_d after the window start", [r for r in recs if r["t_d"] > 0.0])
    groups["BandLow"] = ("known share at most 50%", [r for r in recs if r["known_share"] <= 0.5])
    groups["BandMid"] = ("known share above 50% to 80%",
                         [r for r in recs if 0.5 < r["known_share"] <= 0.8])
    groups["BandHigh"] = ("known share above 80%", [r for r in recs if r["known_share"] > 0.8])
    order = sorted(recs, key=lambda r: (r["known_share"], r["item_id"]))
    n = len(order)
    cuts = []
    for j, qt in enumerate(("QOne", "QTwo", "QThree", "QFour")):
        sel = order[j * n // 4:(j + 1) * n // 4]
        groups[qt] = ("known-share quartile {} ({} to {})".format(
            j + 1, pctpv(sel[0]["known_share"]), pctpv(sel[-1]["known_share"])), sel)
        if j < 3:
            nxt = order[(j + 1) * n // 4]
            cuts.append((sel[-1]["known_share"], nxt["known_share"], sel[-1]["item_id"],
                         nxt["item_id"]))
    check("groups partition the priced proposals",
          len(groups["TdZero"][1]) + len(groups["TdLater"][1]) == n
          and sum(len(groups[k][1]) for k in ("BandLow", "BandMid", "BandHigh")) == n
          and sum(len(groups[k][1]) for k in ("QOne", "QTwo", "QThree", "QFour")) == n)
    for j, (a, b, ia, ib) in enumerate(cuts):
        add("BCut" + ("One", "Two", "Three")[j], pctv(a))
    md("Quartile cut points (known share of the last proposal of a quartile and of the first "
       "of the next, sorted by known share and then item id): " + "; ".join(
           "Q{}/Q{}: {} ({}) | {} ({}){}".format(j + 1, j + 2, pctpv(a), ia, pctpv(b), ib,
                                                 " (a tie straddles the cut)" if a == b else "")
           for j, (a, b, ia, ib) in enumerate(cuts)) + ".", "")
    rows = []
    small = []
    for gtok, (gname, sel) in groups.items():
        for dtok, delta in DELTAS.items():
            first = True
            for g, dt in B_DESIGNS.items():
                s = group_scores(boot, sel, g, delta)
                if first:
                    add("B" + gtok + "Priced" + dtok, grp(s["priced"]))
                    add("B" + gtok + "Costly" + dtok, grp(s["costly"]))
                    add("B" + gtok + "Low" + dtok, grp(s["low"]))
                    add("B" + gtok + "CostlyInstances" + dtok, s["n_inst"])
                    if delta == 0.20 and s["costly"] < 15:
                        small.append("{} ({} costly)".format(gname, s["costly"]))
                    first = False
                pre = "B" + gtok + dt
                add(pre + "MissK" + dtok, s["miss_k"])
                add(pre + "MissFI" + dtok, s["miss_fi"])
                add(pre + "MissBoth" + dtok, s["both"])
                add(pre + "MissKOnly" + dtok, s["k_only"])
                add(pre + "MissFIOnly" + dtok, s["fi_only"])
                add(pre + "FrK" + dtok, s["fr_k"])
                add(pre + "FrFI" + dtok, s["fr_fi"])
                if s["diff"] is not None:
                    add(pre + "MissDiff" + dtok, ppv(s["diff"]))
                    add(pre + "MissDiffLo" + dtok, ppv(s["lo"]))
                    add(pre + "MissDiffHi" + dtok, ppv(s["hi"]))
                rows.append([gname, "{:.2f}".format(delta), g, s["priced"], s["costly"],
                             s["low"], s["n_inst"], frac(s["miss_k"], s["costly"]),
                             frac(s["miss_fi"], s["costly"]), s["both"], s["k_only"],
                             s["fi_only"], frac(s["fr_k"], s["low"]), frac(s["fr_fi"], s["low"]),
                             "{} [{}, {}]".format(ppv(s["diff"]), ppv(s["lo"]), ppv(s["hi"]))
                             if s["diff"] is not None else "counts only (< 10 instances)"])
    md("### B1. Scores within each group", "",
       "Per group: priced, costly and low-cost proposals; the instances holding the costly "
       "ones; costly proposals applied on K, with FI, under both, on K only, with FI only; "
       "low-cost proposals referred on K and with FI; the paired difference K minus FI in "
       "applied share (percentage points, n13 paired cluster bootstrap over instances, n2 "
       "seed and replicates) when the costly proposals sit in at least 10 instances.", "")
    md_table(["group", "delta", "design", "priced", "costly", "low-cost", "instances (costly)",
              "applied K", "applied FI", "applied under both", "applied on K only",
              "applied with FI only", "low-cost referred K", "low-cost referred FI",
              "applied K - FI (pp) [95% CI]"], rows)
    md("Groups with fewer than 15 costly proposals at delta = 0.20 (kept as they are, not "
       "merged): {}.".format("; ".join(small) if small else "none"), "")
    # shortfall
    body = []
    for gtok, (gname, sel) in groups.items():
        nn, med, sf, real = shortfall(sel)
        body.append([gname, nn, "{:.2f}".format(med) if med is not None else "n/a",
                     "{:.1f} of {:.1f} bh ({})".format(sf, real, pctpv(sf / real if real else None))])
        if med is not None:
            add("B" + gtok + "ShortfallMedian", "{:.2f}".format(med))
        add("B" + gtok + "ShortfallN", nn)
    nn, _med, sf, real = shortfall(recs)
    check("damaging sequencing proposals: 160, shortfall 4,414 of 45,225 bh (n13 section D)",
          nn == 160 and grp(round(sf)) == "4{,}414" and grp(round(real)) == "45{,}225",
          (nn, sf, real))
    md("### B2. Realised-damage shortfall of the known board", "",
       "n13 section D's quantity per group: the sequencing-only proposals whose realised "
       "original-field damage exceeds 2 bh; shortfall = realised damage minus the known "
       "board's predicted damage (the D-ABS price on K) when positive. Pooled: {} proposals, "
       "{:,.0f} of {:,.0f} bh (equal to n13 section 0, asserted).".format(nn, sf, real), "")
    md_table(["group", "damaging sequencing proposals", "median shortfall (bh)",
              "total shortfall / realised"], body)
    # the CSV
    cols = ["item_id", "instance_id", "stratum", "primary_class", "edit_type", "t_d",
            "known_share", "n_later_orders", "costly_delta020", "costly_delta010"]
    cols += ["refers_{}_{}".format(rd, g) for rd in ("K", "FI") for g in TOK]
    cols += ["second_price_refers"]
    with open(OUT_KS, "w", newline="", encoding="utf-8") as fh:
        fh.write("# N16 ({}): one row per priced proposal of the direct benchmark at t_d; "
                 "known_share = n_known / (n_completed + n_known + n_unknown); costly: 1 "
                 "costly, 0 low-cost, empty undecided; refers flags 1/0 at the published "
                 "thresholds; second_price_refers = g_orig > 0.20 on field edits only\n"
                 .format(VERSION))
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(cols)
        for r in recs:
            c20, c10 = n13.costly_of(r, 0.20), n13.costly_of(r, 0.10)
            row = [r["item_id"], r["instance_id"], r["stratum"], r["primary_class"], r["split"],
                   "{:.4f}".format(r["t_d"]), f6(r["known_share"]), r["n_unknown"],
                   "" if c20 is None else c20, "" if c10 is None else c10]
            row += [int(n13.refers(r if rd == "K" else r["fi"], g)) for rd in ("K", "FI")
                    for g in TOK]
            row += [int(r["split"] == "field_changing" and r["sp"])]
            w.writerow(row)


# --------------------------------------------------------------------------- #
# C. One common denominator at the tolerance                                   #
# --------------------------------------------------------------------------- #
def block_c(boot, fc, items_dt):
    md("## C. One common denominator at the tolerance", "",
       "n13 section F's definition: the bh price of G-CERT is the certified gap in bh, "
       "max(0, obj - LB) on the priced board; G-CERT-M's is that minus the anchor's gap in bh "
       "on the same board. Both readings divide by the realised-cost denominator "
       "max(OPT_full,base, 1 bh) of the untouched window and refer above tau = 0.20. Applied = "
       "a costly proposal the design does not refer. Paired cluster bootstrap (n13 paired_ci). "
       "The recs are n13.section_f's own (its assertions run again here).", "")
    frecs = n13.section_f(boot, fc, items_dt)
    n13m = n13.macros_of(IN16["n13_macros"])
    body = []
    order = (("G-CERT-M", 0.10), ("G-CERT-M", 0.20), ("G-CERT", 0.20), ("G-CERT", 0.10))
    for g, delta in order:
        gt = TOK[g]
        dtok = "Twenty" if delta == 0.20 else "Ten"
        cst = [r for r in frecs if n13.costly_of(r, delta) == 1]

        def bh(r, rd, g=g):
            if g == "G-CERT-M":
                return r["m_bh_k"] if rd == "K" else r["m_bh_f"]
            return r["c_bh_k"] if rd == "K" else r["c_bh_f"]
        mk = [0.0 if bh(r, "K") / r["den"] > TAU else 1.0 for r in cst]
        mf = [0.0 if bh(r, "FI") / r["den"] > TAU else 1.0 for r in cst]
        dm, lo, hi = n13.paired_ci(boot, cst, mk, mf)
        if (g, delta) == ("G-CERT-M", 0.10):
            check("common denominator: G-CERT-M applies 41 on K and 40 with FI at 0.10",
                  (int(sum(mk)), int(sum(mf))) == (41, 40), (sum(mk), sum(mf)))
        base = "nThirteenFCommon{}Delta{}".format(gt, dtok)
        check("N13 common-scale cells {} {}".format(g, delta),
              str(int(sum(mk))) == n13m[base + "MissK"] and str(int(sum(mf))) == n13m[base + "MissFI"]
              and ppv(dm) == norm_pp(n13m[base + "MissDiff"])
              and ppv(lo) == norm_pp(n13m[base + "MissDiffLo"])
              and ppv(hi) == norm_pp(n13m[base + "MissDiffHi"]),
              (sum(mk), sum(mf), dm, lo, hi))
        add("Common" + gt + "MissK" + dtok, int(sum(mk)))
        add("Common" + gt + "MissFI" + dtok, int(sum(mf)))
        add("Common" + gt + "Diff" + dtok, ppv(dm))
        add("Common" + gt + "DiffLo" + dtok, ppv(lo))
        add("Common" + gt + "DiffHi" + dtok, ppv(hi))
        add("Common" + gt + "Costly" + dtok, len(cst))
        k_only = sum(1 for a, b in zip(mk, mf) if a and not b)
        f_only = sum(1 for a, b in zip(mk, mf) if b and not a)
        body.append([g, "{:.2f}".format(delta), len(cst), frac(int(sum(mk)), len(cst)),
                     frac(int(sum(mf)), len(cst)), k_only, f_only,
                     "{} [{}, {}]".format(ppv(dm), ppv(lo), ppv(hi))])
    md_table(["design", "delta", "costly", "applied K", "applied FI", "K only", "FI only",
              "applied K - FI (pp) [95% CI]"], body)
    md("Every cell equals the n13 macros \\nThirteenFCommon... (asserted), so the extension to "
       "delta 0.20 and to G-CERT uses exactly section F's definition.", "")


# --------------------------------------------------------------------------- #
# D1. The second price under the four dispatching rules                        #
# --------------------------------------------------------------------------- #
def block_d1(recs):
    md("## D1. The second price under each dispatching rule", "",
       "Per rule, from analysis/N14_rows.csv (priced on K, the rule's own prices p_K_* and "
       "realised cost orig_m) and results/n14_altdispatch/<rule>/items.jsonl (dt_obj_orig and "
       "the untouched board's bound an_lb under that rule's census). Second price g_orig = "
       "(dt_obj_orig - an_lb) / max(an_lb, 1 bh), on field edits, refers above 0.20. First "
       "prices at their published thresholds. Benign = benign among the low-cost referred.", "")
    rows = n13.read_csv(IN16["n14_rows"])
    n14 = defaultdict(dict)
    for r in rows:
        n14[r["rule"]][r["item_id"]] = r
    items = {}
    for rule in RULES:
        items[rule] = {}
        for ln in open(RESULTS / "n14_altdispatch" / rule / "items.jsonl", encoding="utf-8"):
            if ln.strip():
                it = json.loads(ln)
                items[rule][it["item_id"]] = it
        check("1,723 rows per rule", len(n14[rule]) == 1723 and len(items[rule]) == 1723)
    n15m = n13.macros_of(IN16["n15_macros"])
    rec_by = {r["item_id"]: r for r in recs}
    priced = {}
    body = []
    for rule, rt in RULES.items():
        pr = [n14[rule][i] for i in sorted(n14[rule]) if n14[rule][i]["priced_K"] == "True"]
        priced[rule] = {r["item_id"] for r in pr}
        for r in pr:
            it = items[rule][r["item_id"]]
            check("priced row carries both second-price inputs ({})".format(rule),
                  it["dt_obj_orig"] is not None and it["an_lb"] is not None, r["item_id"])
            r["_sp"] = ((it["dt_obj_orig"] - it["an_lb"]) / max(it["an_lb"], FLOOR)) > TAU
            r["_lo"], r["_hi"] = n13.fnum(r["orig_m_lo"]), n13.fnum(r["orig_m_hi"])
            if rule == "atc":
                k = rec_by[r["item_id"]]
                check("atc second price equals the direct benchmark's", r["_sp"] == k["sp"],
                      r["item_id"])
        for dtok, delta in DELTAS.items():
            costly = [r for r in pr if cost_class(r["_lo"], r["_hi"], delta) == 1]
            low = [r for r in pr if cost_class(r["_lo"], r["_hi"], delta) == 0]
            add("D" + rt + "Priced" + dtok, grp(len(pr)))
            add("D" + rt + "Costly" + dtok, grp(len(costly)))
            add("D" + rt + "Low" + dtok, grp(len(low)))
            for g, gt in TOK.items():
                def ref1(r, g=g):
                    v = n13.fnum(r["p_K_" + g])
                    return v is not None and v > SETTING[g]
                cell = []
                for stok, flag in (("", ref1),
                                   ("Two", lambda r, ref1=ref1: ref1(r) or (
                                       r["split"] == "field_changing" and r["_sp"]))):
                    miss = [r for r in costly if not flag(r)]
                    fr = [r for r in low if flag(r)]
                    ben = sum(1 for r in fr if r["primary_class"] == "benign")
                    pre = "D" + rt + gt + stok
                    add(pre + "Miss" + dtok, len(miss))
                    add(pre + "Fr" + dtok, len(fr))
                    add(pre + "FrBenign" + dtok, ben)
                    add(pre + "FrShare" + dtok, pct(len(fr), len(low)))
                    cell.append((len(miss), len(fr), ben))
                    if rule == "atc":
                        nm = "nFifteen{}{}".format(gt, stok)
                        check("atc equals N15 ({} {} {})".format(g, stok or "alone", delta),
                              (str(len(miss)), str(len(fr)), str(ben)) ==
                              (n15m[nm + "Miss" + dtok], n15m[nm + "Fr" + dtok],
                               n15m[nm + "FrBenign" + dtok]),
                              (len(miss), len(fr), ben))
                body.append([rule, "{:.2f}".format(delta), g, len(pr), len(costly), len(low),
                             "{}/{}".format(cell[0][0], len(costly)),
                             "{}/{}".format(cell[1][0], len(costly)),
                             frac(cell[0][1], len(low)), frac(cell[1][1], len(low)),
                             "{} / {}".format(cell[0][2], cell[1][2])])
    md_table(["rule", "delta", "first price", "priced", "costly", "low-cost", "applied alone",
              "applied with second price", "low-cost referred alone",
              "low-cost referred with second price", "benign among referred (alone / with)"],
             body)
    # what the second price adds behind G-CERT-M
    add_rows = []
    for rule, rt in RULES.items():
        pr = [n14[rule][i] for i in sorted(n14[rule]) if n14[rule][i]["priced_K"] == "True"]
        for dtok, delta in DELTAS.items():
            low = [r for r in pr if cost_class(r["_lo"], r["_hi"], delta) == 0]
            added = [r for r in low if not (n13.fnum(r["p_K_G-CERT-M"]) > TAU)
                     and r["split"] == "field_changing" and r["_sp"]]
            def anchor_g(r, rule=rule):
                it = items[rule][r["item_id"]]
                return (it["an_obj_orig"] - it["an_lb"]) / max(it["an_lb"], FLOOR)
            selfb = [r for r in added if anchor_g(r) > TAU]
            ben = [r for r in added if r["primary_class"] == "benign"]
            ben_self = [r for r in ben if anchor_g(r) > TAU]
            add("D" + rt + "CertMAdded" + dtok, len(added))
            add("D" + rt + "CertMAddedSelfBlocking" + dtok, len(selfb))
            add("D" + rt + "CertMAddedBenign" + dtok, len(ben))
            add("D" + rt + "CertMAddedBenignSelfBlocking" + dtok, len(ben_self))
            add_rows.append([rule, "{:.2f}".format(delta), len(added), len(selfb), len(ben),
                             len(ben_self), ", ".join(r["item_id"] for r in ben) or "none"])
    md("Low-cost proposals that the second price adds to G-CERT-M's referrals, and how many sit "
       "on a board whose untouched dispatch under the rule already prices above 0.20 on the "
       "original fields ((an_obj_orig - an_lb) / max(an_lb, 1 bh) > 0.20; on such a board a "
       "field edit that leaves the schedule's original-field objective unchanged inherits the "
       "board's own gap as its second price):", "")
    md_table(["rule", "delta", "added low-cost referrals", "on boards above 0.20 untouched",
              "benign among the added", "benign on boards above 0.20", "benign items"],
             add_rows)
    # does the bound depend on the rule?
    keys = ("n_completed", "n_running", "n_queue", "n_known", "rconst", "an_lb_running")
    lb_rows = []
    for rule in RULES:
        if rule == "atc":
            continue
        c = Counter()
        for iid in sorted(items["atc"]):
            a, b = items["atc"][iid], items[rule][iid]
            same_board = all(a[k] == b[k] for k in keys)
            same_lb = abs(a["an_lb"] - b["an_lb"]) < 1e-9
            c[(same_board, same_lb)] += 1
        check("{}: no item with the same board carries a different an_lb".format(rule),
              c.get((True, False), 0) == 0, dict(c))
        n_diff = c.get((False, False), 0)
        add("DLbDiffers" + RULES[rule], grp(n_diff))
        add("DBoardDiffers" + RULES[rule], grp(n_diff + c.get((False, True), 0)))
        lb_rows.append([rule, 1723, c.get((True, True), 0), n_diff + c.get((False, True), 0),
                        n_diff, c.get((True, False), 0)])
    md("### Does the untouched board's bound an_lb depend on the rule?", "",
       "It depends on the rule only through the board. The known board at t_d is the state "
       "the rule's own trajectory from t = 0 reaches (completed, running and queued orders), "
       "so a different rule can reach a different board; given the board, the bound is the "
       "same. Board identity tested on (n_completed, n_running, n_queue, n_known, running "
       "constant, running part of the bound) against ATC; no item with an identical board "
       "has a different an_lb (asserted).", "")
    md_table(["rule", "items", "same board as ATC", "different board", "different an_lb",
              "same board, different an_lb"], lb_rows)
    # priced totals
    md("### Why the priced totals differ", "",
       "Items priced under ATC and not under the rule (lost), and the reverse (gained), grouped "
       "by where the stopping rule's gate stops them (analysis/N14_rows.csv stage_K, "
       "terminal_K, codes_K). 't_start < t_d' counts items whose first referenced order starts "
       "before t_d under the stopping rule (t_start_rule); 'names running work' counts items "
       "that name an order running at t_d under it (names_running_any > 0).", "")
    prow = []
    for rule in RULES:
        if rule == "atc":
            continue
        lost = sorted(priced["atc"] - priced[rule])
        gained = sorted(priced[rule] - priced["atc"])
        for kind, ids, who in (("lost", lost, rule), ("gained", gained, "atc")):
            groups_ = OrderedDict()
            for iid in ids:
                stop = n14[who][iid]
                key = (stop["stage_K"], stop["terminal_K"], stop["codes_K"],
                       stop["issuable_rule"])
                groups_.setdefault(key, []).append(iid)
            for (stage, term, codes, iss), gids in sorted(groups_.items()):
                cls = Counter(n14["atc"][i]["primary_class"] for i in gids)
                early = sum(1 for i in gids if float(n14[who][i]["t_start_rule"])
                            < float(n14[who][i]["t_d"]))
                run = sum(1 for i in gids if int(n14[who][i]["names_running_any"] or 0) > 0)
                prow.append([rule, kind, len(gids), who.upper(), stage, term, codes or "none",
                             iss, early, run,
                             ", ".join("{} {}".format(c, v) for c, v in sorted(cls.items())),
                             ", ".join(gids)])
        add("DLost" + RULES[rule], len(lost))
        add("DGained" + RULES[rule], len(gained))
        check("{}: 1,356 - lost + gained = priced".format(rule),
              1356 - len(lost) + len(gained) == len(priced[rule]))
    md_table(["rule", "against ATC", "items", "stopped by", "stage", "terminal", "codes",
              "issuable under the stopping rule", "t_start < t_d", "names running work",
              "class", "items named"], prow)
    md("Reading of the codes (code/l1guard/findings.py): dangling_order_id = 'an operation "
       "names a work order the instance does not contain' (the known board at t_d holds no "
       "order that has already started, so a name of an order that the rule has started is "
       "dangling there); frozen_order_edit = 'an operation edits an order that is frozen', "
       "with names_running_work, the decision-time code for an order running at t_d; "
       "frozen_window_conflict = 'a frozen order's pinned start sits before its own shifted "
       "release'. Every change is a stage change of the gate on the board that the rule's own "
       "trajectory reaches by t_d; no change comes from a price.", "")
    check("priced totals 1,356 / 1,346 / 1,358 / 1,358",
          [len(priced[r]) for r in RULES] == [1356, 1346, 1358, 1358],
          [len(priced[r]) for r in RULES])
    return n14, items


# --------------------------------------------------------------------------- #
# D2. Behind the LLM proposers                                                 #
# --------------------------------------------------------------------------- #
def e1_cells_tokens():
    return OrderedDict((cell, tok) for cell, tok in e1dg.CELL_TOKEN.items())


def block_d2(full_br):
    md("## D2. Behind the LLM proposers (gate stress test at the decision instant)", "",
       "Rows: analysis/N11_rows_e2e.csv, dataset e2e_td, constrained mode, every cell and "
       "repeat (the rows that reach the quality check, out of the constrained rows of "
       "results/n11_e2e/rows_e1_primary.jsonl; the rows of n11_stage2's N10 twin, macros "
       "\\nElevenNTenAll...). Applied field edit = edit type field_changing with certified gap "
       "at most tau = 0.20. Damage = rw_obj_orig - the no-AI anchor (bh). Second price = "
       "(obj_orig on K - anchor_lb_K) / max(anchor_lb_K, 1 bh) > 0.20. Realised cost = the "
       "direct benchmark's truth: n11_forecast.attach_orig_truth on rw_obj_orig, the anchor's "
       "wwt_original_bh and the untouched full-window bracket (the reimplementation reproduces "
       "orig_m_lo/hi of all 1,356 priced direct proposals, asserted). Per-100 denominators are "
       "the constrained rows (instructions x repeats) of the scope.", "")
    nm = n13.macros_of(IN16["n11_macros"])
    anchors = {}
    for rec in json.loads(Path(n13.IN["rule_anchor"]).read_text()):
        anchors[(Path(rec["instance_path"]).stem, e1dg.frozen_key(rec["frozen_seed"]))] = \
            float(rec["wwt_original_bh"])
    n_rows = Counter()
    fk_of = {}
    for u in n13.read_jsonl(n13.IN["rows_e1"]):
        if u["mode"] != "M_constrained":
            continue
        cell = (n13.SRC_ARM[u["src"]], e1dg.thinking_label(u["thinking"]))
        n_rows[cell] += 1
        rid = "|".join([u["src"], u["item_id"], "M_constrained",
                        e1dg.thinking_label(u["thinking"]), str(u["repeat"])])
        fk_of[rid] = (u["instance_id"], u["frozen_seed"] or "")
    check("34,460 constrained rows", sum(n_rows.values()) == 34460, sum(n_rows.values()))
    rows = [r for r in n13.read_csv(n13.IN["rows_e2e"])
            if r["dataset"] == "e2e_td" and r["mode"] == "M_constrained"]
    check("24,343 quality-reaching constrained rows", len(rows) == 24343, len(rows))
    md("Constrained rows: {:,}; reaching the quality check: {:,}.".format(
        sum(n_rows.values()), len(rows)), "")
    recs = []
    for r in rows:
        if r["split"] != "field_changing":
            continue
        gap = float(r["gap_cert"])
        if gap > TAU:
            continue
        akey = fk_of[r["row_id"]]
        anchor = float(r["anchor_pub"])
        check("anchor_pub equals the rule anchor", abs(anchor - anchors[akey]) < 2e-6,
              r["row_id"])
        dmg = float(r["damage_if_applied"])
        rw = float(r["rw_obj_orig"])
        check("damage = rw_obj_orig - anchor", abs(rw - anchor - dmg) < 2e-6, r["row_id"])
        lb = float(r["anchor_lb_K"])
        g = (float(r["obj_orig"]) - lb) / max(lb, FLOOR)
        lo, hi = realised_range(rw, anchors[akey], r["instance_id"], full_br)
        recs.append(dict(cell=(r["arm"], r["thinking"]), item_id=r["item_id"],
                         instance_id=r["instance_id"], cls=r["primary_class"],
                         stratum=r["stratum"], repeat=r["repeat"], dmg=dmg, g=g, sp=g > TAU,
                         lo=lo, hi=hi, row_id=r["row_id"]))
    big = [r for r in recs if r["dmg"] > 10.0]
    big_sp = [r for r in big if r["sp"]]
    check("8,824 applied field edits (\\nElevenNTenAllFieldApplied)",
          grp(len(recs)) == nm["nElevenNTenAllFieldApplied"] == "8{,}824", len(recs))
    check("81 applied field edits damage > 10 bh, 49 referred by the second price",
          (len(big), len(big_sp)) == (81, 49)
          and nm["nElevenNTenAllFieldDmgTenCount"] == "81"
          and nm["nElevenNTenAllFieldOrigAboveTauDmgTen"] == "49", (len(big), len(big_sp)))
    check("realised cost available on every applied field edit",
          all(r["lo"] is not None for r in recs))

    def cat(r):
        if r["lo"] > 0.20:
            return "costly at 0.20"
        if r["lo"] > 0.10 and r["hi"] <= 0.20:
            return "costly at 0.10 only"
        if r["hi"] <= 0.10:
            return "low-cost (at most 0.10)"
        return "undecided (bracket straddles 0.10 or 0.20)"
    cats = ("costly at 0.20", "costly at 0.10 only", "low-cost (at most 0.10)",
            "undecided (bracket straddles 0.10 or 0.20)")
    ctok = dict(zip(cats, ("CostlyTwenty", "CostlyTenOnly", "Low", "Undecided")))
    body = []
    for c in cats:
        sel = [r for r in big if cat(r) == c]
        k = sum(1 for r in sel if r["sp"])
        add("LlmBig" + ctok[c], len(sel))
        add("LlmBig" + ctok[c] + "Second", k)
        body.append([c, len(sel), k, len(sel) - k])
    add("LlmRows", grp(sum(n_rows.values())))
    add("LlmFieldApplied", grp(len(recs)))
    add("LlmBig", len(big))
    add("LlmBigSecond", len(big_sp))
    add("LlmBigNotSecond", len(big) - len(big_sp))
    md("### The 81 applied field edits that damage the original schedule by more than 10 bh",
       "", "Pooled over the ten constrained cells and every repeat (the scope of "
       "\\nElevenNTenAllFieldDmgTenCount = 81 and \\nElevenNTenAllFieldOrigAboveTauDmgTen = 49, "
       "asserted).", "")
    md_table(["realised cost", "applied field edits > 10 bh", "second price refers",
              "second price does not refer"], body)
    # the ones the second price leaves
    left = sorted((r for r in big if not r["sp"]),
                  key=lambda r: (r["lo"], r["item_id"], r["cell"], r["repeat"]))
    add("LlmLeftAtMostTwenty", sum(1 for r in left if r["hi"] <= 0.20))
    add("LlmLeftAtMostTen", sum(1 for r in left if r["hi"] <= 0.10))
    add("LlmLeftCostMax", "{:.3f}".format(max(r["hi"] for r in left)))
    add("LlmLeftCostMedian", "{:.3f}".format(statistics.median(r["lo"] for r in left)))
    add("LlmLeftGMax", "{:.3f}".format(max(r["g"] for r in left)))
    add("LlmLeftGMedian", "{:.3f}".format(statistics.median(r["g"] for r in left)))
    add("LlmLeftDmgMax", "{:.2f}".format(max(r["dmg"] for r in left)))
    lb = qstats([r["lo"] for r in left])
    gq = qstats([r["g"] for r in left])
    md("### The {} that the second price does not refer".format(len(left)), "",
       "Realised cost (lower end) min / Q1 / median / Q3 / max: {}; second price g_orig: {}. "
       "{} of {} have a realised cost of at most 0.20 (upper end), {} of at most 0.10. "
       "Strata: {}. Classes: {}. Cells: {}.".format(
           " / ".join("{:.3f}".format(v) for v in lb), " / ".join("{:.3f}".format(v) for v in gq),
           sum(1 for r in left if r["hi"] <= 0.20), len(left),
           sum(1 for r in left if r["hi"] <= 0.10),
           ", ".join("{} {}".format(n13.STRATUM_NAME[k], v) for k, v in
                     sorted(Counter(r["stratum"] for r in left).items())),
           ", ".join("{} {}".format(k, v) for k, v in
                     sorted(Counter(r["cls"] for r in left).items())),
           ", ".join("{}/{} {}".format(k[0], k[1], v) for k, v in
                     sorted(Counter(r["cell"] for r in left).items()))), "")
    md_table(["item", "class", "stratum", "cell", "repeat", "damage (bh)", "realised cost",
              "second price"],
             [[r["item_id"], r["cls"], n13.STRATUM_NAME[r["stratum"]],
               "{}/{}".format(*r["cell"]), r["repeat"], "{:.2f}".format(r["dmg"]),
               "[{:.4f}, {:.4f}]".format(r["lo"], r["hi"]), "{:.4f}".format(r["g"])]
              for r in left])
    # all applied field edits, by scope
    scopes = OrderedDict()
    scopes["all ten cells"] = ("All", list(n_rows), recs)
    cap = [c for c in e1dg.CAPABILITY_SET]
    scopes["Table 6 arms (eight cells)"] = ("TableSix", cap,
                                           [r for r in recs if r["cell"] in cap])
    for cell, tok in e1_cells_tokens().items():
        scopes["{}/{}".format(*cell)] = (tok, [cell], [r for r in recs if r["cell"] == cell])
    body = []
    for sname, (stok, cells, sel) in scopes.items():
        nr = sum(n_rows[c] for c in cells)
        rec = [sname, nr, len(sel)]
        add("Llm" + stok + "Rows", grp(nr))
        add("Llm" + stok + "Applied", grp(len(sel)))
        b10 = [r for r in sel if r["dmg"] > 10.0]
        add("Llm" + stok + "Big", len(b10))
        add("Llm" + stok + "BigSecond", sum(1 for r in b10 if r["sp"]))
        rec.append("{} / {}".format(sum(1 for r in b10 if r["sp"]), len(b10)))
        for dtok, delta in DELTAS.items():
            cst = [r for r in sel if cost_class(r["lo"], r["hi"], delta) == 1]
            lowr = [r for r in sel if cost_class(r["lo"], r["hi"], delta) == 0]
            k = sum(1 for r in cst if r["sp"])
            fl = sum(1 for r in lowr if r["sp"])
            add("Llm" + stok + "Costly" + dtok, len(cst))
            add("Llm" + stok + "CostlySecond" + dtok, k)
            add("Llm" + stok + "Low" + dtok, grp(len(lowr)))
            add("Llm" + stok + "LowSecond" + dtok, fl)
            add("Llm" + stok + "LowSecondPerHundred" + dtok,
                "{:.2f}".format(100.0 * fl / nr) if nr else "n/a")
            rec += ["{} / {}".format(k, len(cst)), "{} / {}".format(fl, len(lowr)),
                    "{:.2f}".format(100.0 * fl / nr) if nr else "n/a"]
        body.append(rec)
    md("### Every applied field edit, by scope", "",
       "Costly / low-cost by the realised cost at each delta (undecided brackets in neither). "
       "The 'Table 6 arms' scope is the eight schema-enforced cells of Table 6, repeats pooled "
       "as the table pools them; DeepSeek's two JSON-object cells are in 'all ten cells'.", "")
    md_table(["scope", "constrained rows", "applied field edits",
              "> 10 bh: second price refers / n",
              "costly at 0.20: second price refers / n",
              "low-cost at 0.20: second price refers / n", "per 100 rows (0.20)",
              "costly at 0.10: second price refers / n",
              "low-cost at 0.10: second price refers / n", "per 100 rows (0.10)"], body)
    return recs, n_rows


# --------------------------------------------------------------------------- #
# E. Operating curves over the threshold                                       #
# --------------------------------------------------------------------------- #
def block_e(recs):
    md("## E. Operating curves over the threshold (K, site's rule)", "",
       "Ratio designs: threshold 0.00, 0.01, ..., 0.60 on the K price; D-ABS: 61 equally "
       "spaced values from 0 to the 99th percentile of its K price over the 1,356 priced "
       "proposals. A design refers when its price exceeds the threshold; 'with second price' "
       "adds g_orig > 0.20 on field edits. Applied = costly not referred; referred = low-cost "
       "referred. Curves in analysis/N16_fig_curves.csv.", "")
    p99 = float(np.percentile(np.asarray([r["p_D-ABS"] for r in recs], dtype=float), 99))
    grids = OrderedDict((g, [round(0.01 * i, 2) for i in range(61)]) for g in RATIO)
    grids["D-ABS"] = [p99 * i / 60.0 for i in range(61)]
    add("EAbsGridMax", "{:.2f}".format(p99))
    curves = OrderedDict()
    out = []
    for dtok, delta in DELTAS.items():
        costly = [r for r in recs if n13.costly_of(r, delta) == 1]
        low = [r for r in recs if n13.costly_of(r, delta) == 0]
        for g in TOK:
            for two in (False, True):
                pts = []
                for thr in grids[g]:
                    def flag(r, thr=thr, g=g, two=two):
                        f = r["p_" + g] > thr
                        return f or (two and r["split"] == "field_changing" and r["sp"])
                    a = sum(1 for r in costly if not flag(r))
                    f = sum(1 for r in low if flag(r))
                    pts.append((thr, a, f))
                    out.append([g, "{:.2f}".format(delta), "{:.6f}".format(thr), int(two),
                                len(costly), len(low), a, f, "{:.6f}".format(a / len(costly)),
                                "{:.6f}".format(f / len(low))])
                curves[(g, delta, two)] = pts
                if g in RATIO:
                    at = [p for p in pts if p[0] == SETTING[g]][0]
                    s = n13.score(None, recs, (lambda r, g=g, two=two: sp_flag(r, g) if two
                                               else n13.refers(r, g)), delta, with_ci=False)
                    check("curve at the published threshold equals the published flag ({} {} "
                          "{})".format(g, delta, two), (at[1], at[2]) == (s["miss"], s["fr"]),
                          (at, s["miss"], s["fr"]))
    with open(OUT_CURVES, "w", newline="", encoding="utf-8") as fh:
        fh.write("# N16 ({}): operating curves on K at the site's rule; applied = costly "
                 "proposals not referred, referred = low-cost proposals referred; "
                 "with_second_price = 1 adds g_orig > 0.20 on field edits\n".format(VERSION))
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["design", "delta", "threshold", "with_second_price", "costly", "low",
                    "applied", "referred", "applied_share", "referred_share"])
        w.writerows(out)
    # equality of G-CERT-M and D-REL2
    diffs = [abs(r["p_G-CERT-M"] - r["p_D-REL2"]) for r in recs]
    n_diff = sum(1 for d in diffs if d > 1e-6)
    add("ECertMRelTwoPriceDiffer", n_diff)
    add("ECertMRelTwoPriceMaxDiff", "{:.6f}".format(max(diffs)))
    body = []
    for dtok, delta in DELTAS.items():
        for two, ttok in ((False, ""), (True, "Two")):
            m = curves[("G-CERT-M", delta, two)]
            r2 = curves[("D-REL2", delta, two)]
            c = curves[("G-CERT", delta, two)]
            same = sum(1 for a, b in zip(m, r2) if a[1:] == b[1:])
            md_diff = [(a, b) for a, b in zip(m, r2) if a[1:] != b[1:]]
            cd = [(a, b) for a, b in zip(c, m) if a[1:] != b[1:]]
            add("ECurvesCoincide" + dtok + ttok, same)
            add("ECertDiffers" + dtok + ttok, len(cd))
            body.append(["{:.2f}".format(delta), "with second price" if two else "alone",
                         "{} of {}".format(same, len(m)),
                         "; ".join("{:.2f}: {}/{} vs {}/{}".format(a[0], a[1], a[2], b[1], b[2])
                                   for a, b in md_diff) or "none",
                         "{} of {}".format(len(cd), len(c)),
                         "; ".join("{:.2f}: {}/{} vs {}/{}".format(a[0], a[1], a[2], b[1], b[2])
                                   for a, b in cd) or "none"])
    big = sorted(((d, r["item_id"]) for d, r in zip(diffs, recs) if d > 1e-6), reverse=True)
    md("G-CERT-M and D-REL2 prices on K differ by more than 1e-6 on {} of {} priced "
       "proposals; the largest difference is {:.6f}{}.".format(
           n_diff, len(recs), max(diffs),
           " ({})".format(", ".join("{} {:.4f}".format(i, d) for d, i in big[:10]))
           if big else ""), "")
    md_table(["delta", "variant", "G-CERT-M and D-REL2 curves coincide at",
              "where they differ (threshold: G-CERT-M applied/referred vs D-REL2)",
              "G-CERT's curve differs from G-CERT-M's at",
              "where (threshold: G-CERT applied/referred vs G-CERT-M)"], body)


# --------------------------------------------------------------------------- #
# F. Referral that the design does not fix                                     #
# --------------------------------------------------------------------------- #
TAB6 = (("qwen3-14b", "-", "QwenFourteen", "Qwen3-14B"),
        ("qwen3.6-27b-fp8", "-", "QwenTwentySeven", "Qwen3.6-27B-FP8"),
        ("glm-4-9b", "-", "Glm", "GLM-4-9B-0414"),
        ("openai", "-", "Mini", "GPT-5.4-mini"),
        ("sonnet", "disabled", "Sonnet", "Claude Sonnet 5"),
        ("opus", "default", "Opus", "Claude Opus 5"),
        ("opus", "disabled", "OpusNoThink", "Claude Opus 5 (no think)"),
        ("sol", "none", "Sol", "GPT-5.6 Sol"))
D3_ARM = {"qwen3-14b": "qwen3-14b", "qwen3.6-27b-fp8": "qwen3.6-27b-fp8", "glm-4-9b": "glm-4-9b",
          "openai": "mini", "sonnet": "sonnet", "opus": "opus", "sol": "sol"}


def _d3_norm_op(o):
    """n11_stage2._d3_norm_op (D3's two normalisation rules), restated."""
    o = dict(o)
    for k, v in list(o.items()):
        if isinstance(v, float) and v == int(v):
            o[k] = int(v)
    if o.get("op") == "reorder" and o.get("relation") == "after":
        o["order_id"], o["ref_order_id"] = o.get("ref_order_id"), o.get("order_id")
        o["relation"] = "before"
    return json.dumps(o, sort_keys=True)


def d3_equiv(emitted, gold):
    if not emitted:
        return False
    return sorted(_d3_norm_op(o) for o in emitted) == sorted(_d3_norm_op(o) for o in gold)


def block_f(boot, fc):
    md("## F. Referral that the design does not fix", "",
       "Gate stress test at t_d, constrained mode, the eight schema-enforced cells of Table 6 "
       "(DeepSeek's JSON-object cells are not in the table), every repeat pooled as the table "
       "pools them. Cost-bearing = V3. 'Pass the feasibility check' = the feasibility terminal "
       "applies the proposal, so the certificate prices it. Equivalent = the proposal's "
       "operations equal the reference translation (the item's gold_ops, the direct "
       "benchmark's proposal) under D3's rule (numeric types unified, 'after' reorders "
       "inverted), on the parsed operations of results/<arm>/proposals.jsonl. Referred = "
       "certified gap above 0.20 at t_d. Pooled interval: n2 cluster bootstrap over instances "
       "(rows of all arms on one instance share a cluster).", "")
    suite = {it["item_id"]: it for it in n13.read_jsonl(n13.IN["suite"])}
    ops = {}
    for arm, d in e1dg.ARM_DIRS.items():
        with open(RESULTS / d / "proposals.jsonl", encoding="utf-8") as fh:
            for ln in fh:
                if not ln.strip():
                    continue
                rec = json.loads(ln)
                if rec["mode"] != "M_constrained":
                    continue
                ex = rec.get("extra") or {}
                key = (d, e1dg.thinking_label(ex.get("thinking")), ex.get("repeat"),
                       rec["instruction_id"])
                check("one proposal row per key", key not in ops, key)
                ops[key] = rec.get("parsed_ops")
    cells = defaultdict(list)
    for u in n13.read_jsonl(n13.IN["rows_e1"]):
        if u["mode"] != "M_constrained":
            continue
        th = e1dg.thinking_label(u["thinking"])
        key = (u["src"], th, u["repeat"], u["item_id"])
        check("every E1 row has its logged operations", key in ops, key)
        cells[(n13.SRC_ARM[u["src"]], th)].append((u, ops[key]))
    lit = {(r["row"], r["column"]): r for r in n13.read_csv(IN16["n11_literal_tables"])
           if r["exhibit"] == "Table 11"}
    d3 = {r["arm"]: r for r in n13.read_csv(IN16["d3_td"])}
    pooled = OrderedDict([("Same", []), ("Diff", [])])
    pooled0 = OrderedDict([("Same", []), ("Diff", [])])
    agree = Counter()
    body = []
    for arm, th, tok, disp in TAB6:
        rows = cells[(arm, th)]
        v3 = [(u, o) for u, o in rows if suite[u["item_id"]]["primary_class"] == "V3"]
        sep = sum(1 for u, o in v3 if u["term_feas"] in n13.APPLIED
                  and u["term_cert"] in n13.BLOCKED)
        check("Table 6 referred column reproduced ({})".format(disp),
              pctv(sep / len(v3)) == lit[(tok, "VThreeReferred")]["decision_time"],
              (sep, len(v3), lit[(tok, "VThreeReferred")]["decision_time"]))
        r0 = [(u, o) for u, o in v3 if u["repeat"] == 0]
        eq0 = sum(1 for u, o in r0 if d3_equiv(o, suite[u["item_id"]]["gold_ops"]))
        if th in ("-", "disabled", "none") and arm in D3_ARM:
            want = d3[D3_ARM[arm]]["V3_equiv"].split(" ")[0]
            check("D3 V3 equivalence reproduced on repeat 0 ({})".format(disp),
                  "{}/{}".format(eq0, len(r0)) == want, (eq0, len(r0), want))
        passed = [(u, o) for u, o in v3 if u["term_feas"] in n13.APPLIED]
        rec = [disp, len({u["repeat"] for u, o in v3}), len(v3), len(passed)]
        for stok in ("Same", "Diff"):
            sel = [(u, o) for u, o in passed
                   if d3_equiv(o, suite[u["item_id"]]["gold_ops"]) == (stok == "Same")]
            k = 0
            for u, o in sel:
                ref = u["stage_cert"] == "qual" and u["gap"] is not None and u["gap"] > TAU
                check("referred at the quality stage = G-CERT blocked after feasibility",
                      ref == (u["term_cert"] in n13.BLOCKED), (u["item_id"], u["term_cert"]))
                k += int(ref)
                pooled[stok].append((u, ref))
                if stok == "Same":
                    dk = fc["K"].get(u["item_id"])
                    if dk is None:
                        agree["not priced in the direct benchmark"] += 1
                    else:
                        agree["priced"] += 1
                        agree["same referral"] += int(ref == n13.refers(dk, "G-CERT"))
                        agree["same gap (1e-6)"] += int(abs(u["gap"] - dk["p_G-CERT"]) < 1e-6)
                if u["repeat"] == 0:
                    pooled0[stok].append((u, ref))
            add("F" + tok + stok + "N", grp(len(sel)))
            add("F" + tok + stok + "Referred", grp(k))
            add("F" + tok + stok + "Share", pct(k, len(sel)))
            rec.append(frac(k, len(sel)))
        body.append(rec)
    prow = ["pooled (eight cells)", "", sum(r[2] for r in body), sum(r[3] for r in body)]
    for stok, lst in pooled.items():
        rows_ = [dict(instance_id=u["instance_id"]) for u, _f in lst]
        flags = [f for _u, f in lst]
        lo, hi = boot.ci(rows_, flags)
        k = sum(flags)
        add("FPooled" + stok + "N", grp(len(lst)))
        add("FPooled" + stok + "Referred", grp(k))
        add("FPooled" + stok + "Share", pct(k, len(lst)))
        add("FPooled" + stok + "ShareLo", pctv(lo))
        add("FPooled" + stok + "ShareHi", pctv(hi))
        prow.append("{} [{}, {}]".format(frac(k, len(lst)), pctpv(lo), pctpv(hi)))
    body.append(prow)
    md_table(["arm", "repeats", "V3 rows", "V3 rows passing feasibility",
              "equivalent to the reference: referred / n", "different: referred / n"], body)
    r0 = ["repeat 0 only, pooled", "", "", ""]
    for stok, lst in pooled0.items():
        k = sum(f for _u, f in lst)
        r0.append(frac(k, len(lst)))
    v3d = [r for r in fc["K"].values() if r["primary_class"] == "V3"]
    v3d_ref = sum(1 for r in v3d if n13.refers(r, "G-CERT"))
    add("FDirectVThreePriced", len(v3d))
    add("FDirectVThreeReferred", v3d_ref)
    add("FDirectVThreeShare", pct(v3d_ref, len(v3d)))
    add("FSameAgreeDirect", grp(agree["same referral"]))
    add("FSamePricedDirect", grp(agree["priced"]))
    md("Repeat 0 only (one row per arm and item), pooled over the eight cells: equivalent {}, "
       "different {}.".format(r0[4], r0[5]), "",
       "By construction: an equivalent proposal is the direct benchmark's reference proposal of "
       "the same item on the same known board. Of the {} equivalent rows, {} are on items priced "
       "in the direct benchmark and {} are not; on the priced ones the stress-test referral "
       "equals the direct benchmark's G-CERT flag on {} rows and the certified gap agrees "
       "within 1e-6 on {}. The direct benchmark itself refers {} of its priced V3 "
       "proposals.".format(len(pooled["Same"]), agree["priced"],
                           agree["not priced in the direct benchmark"], agree["same referral"],
                           agree["same gap (1e-6)"], frac(v3d_ref, len(v3d))), "",
       "Ties to the paper: the share of V3 rows that pass feasibility and are referred "
       "reproduces Table 6's 'referred' column for all eight arms (denominator: every V3 row, "
       "repeats pooled), and the per-row equivalence reproduces D3's V3 fidelity on repeat 0 "
       "for the seven arms D3 covers (asserted). D3's 'opus' entry reads the thinking-disabled "
       "raw outputs, so the fidelity printed in Table 6's 'Claude Opus 5' row is the "
       "no-think cell's repeat-0 value (Section H).", "")
    return cells, suite


# --------------------------------------------------------------------------- #
# H. Translation fidelity by Table 6 cell, and the figure input                #
# --------------------------------------------------------------------------- #
FIG_ARMS = ("qwen3-14b", "qwen3.6-27b-fp8", "glm-4-9b", "openai", "sonnet", "opus", "sol")
NOTHINK_KEY = "opus-disabled"


def pearson(xs, ys):
    """the manuscript's figure script, restated."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    return sxy / (sxx * syy) ** 0.5


def raw_ops(text):
    """n11_stage2._d3_ops_of (the published D3 parse of the raw output), restated."""
    try:
        return json.loads(text).get("operations")
    except Exception:  # noqa: BLE001 - the published rule
        return None


def block_h(cells, suite):
    md("## H. Translation fidelity by Table 6 cell (follow-up)", "",
       "Fidelity = the share of the 154 issuable cost-bearing (V3) instructions whose repeat-0 "
       "constrained proposal equals the reference translation under D3's rule, computed per "
       "row from the parsed operations of results/<arm>/proposals.jsonl (Section F's "
       "equivalence). Upstream, Table 6's fidelity column comes from D3 "
       "(code/scripts/n11_stage2.py: D3_ARMS, d3_rows, TAB11, tab11_values), which reads "
       "results/grid_e1_hosted_opus/proposals_raw.dedup.jsonl for 'opus' and keeps only "
       "repeat 0 with thinking in (None, disabled, none). For Claude Opus 5 that keeps the "
       "thinking-disabled rows, and TAB11 maps the 'Claude Opus 5' row (thinking default) to "
       "this entry and gives the no-think row no fidelity.", "")
    pub = n13.macros_of(IN16["macros_n11_manu"])
    ana = n13.macros_of(IN16["n11_macros"])
    items_e2e = {r["item_id"]: r for r in n13.read_jsonl(n13.IN["items_e2e"])}
    v3_iss = sorted(i for i, it in suite.items() if it["primary_class"] == "V3"
                    and items_e2e[i]["issuable"])
    check("154 issuable cost-bearing instructions", len(v3_iss) == 154, len(v3_iss))
    res = OrderedDict()
    body = []
    for arm, th, tok, disp in TAB6:
        r0 = [(u, o) for u, o in cells[(arm, th)]
              if suite[u["item_id"]]["primary_class"] == "V3" and u["repeat"] == 0]
        ids = sorted(u["item_id"] for u, o in r0)
        check("repeat 0 covers the 154 issuable V3 instructions once ({})".format(disp),
              ids == v3_iss, len(ids))
        eq = sorted(u["item_id"] for u, o in r0
                    if d3_equiv(o, suite[u["item_id"]]["gold_ops"]))
        res[tok] = (len(r0), eq)
        add("Fidelity" + tok + "N", len(r0))
        add("Fidelity" + tok + "Count", len(eq))
        add("Fidelity" + tok + "Share", pct(len(eq), len(r0)))
        mname = "nElevenTabEOne" + tok + "VThreeFidelity"
        body.append([disp, th, len(r0), len(eq), pctp(len(eq), len(r0)),
                     pub[mname].replace("\\", ""), ana[mname].replace("\\", "")])
    md_table(["Table 6 row", "thinking", "N (repeat 0)", "equivalent", "fidelity (N16)",
              "published macro (manuscript/macros_n11.tex)", "analysis/N11_macros.tex"], body)
    six = ("QwenFourteen", "QwenTwentySeven", "Glm", "Mini", "Sonnet", "Sol")
    for tok in six:
        n, eq = res[tok]
        mname = "nElevenTabEOne" + tok + "VThreeFidelity"
        check("fidelity equals the published macro ({})".format(tok),
              pct(len(eq), n) == pub[mname] == ana[mname], (len(eq), n, pub[mname]))
    nt_n, nt_eq = res["OpusNoThink"]
    op_n, op_eq = res["Opus"]
    check("the published 'Opus' fidelity equals the no-think cell's",
          pct(len(nt_eq), nt_n) == pub["nElevenTabEOneOpusVThreeFidelity"]
          == ana["nElevenTabEOneOpusVThreeFidelity"], (len(nt_eq), nt_n))
    check("the published no-think fidelity is n/a",
          pub["nElevenTabEOneOpusNoThinkVThreeFidelity"] == "n/a"
          == ana["nElevenTabEOneOpusNoThinkVThreeFidelity"])
    only_def = sorted(set(op_eq) - set(nt_eq))
    only_dis = sorted(set(nt_eq) - set(op_eq))
    add("FidelityOpusOnlyDefault", len(only_def))
    add("FidelityOpusOnlyDisabled", len(only_dis))
    # D3's own parse of the raw text, both Opus cells
    raw = defaultdict(dict)
    with open(IN16["opus_raw"], encoding="utf-8") as fh:
        for ln in fh:
            if not ln.strip():
                continue
            r = json.loads(ln)
            if r["mode"] != "M_constrained" or r.get("repeat") != 0:
                continue
            check("one raw row per (thinking, item)", r["item_id"] not in raw[r.get("thinking")])
            raw[r.get("thinking")][r["item_id"]] = r
    check("the raw file holds the two Opus thinking settings",
          sorted(k for k in raw) == ["default", "disabled"], sorted(raw))
    raw_eq = {}
    for th in ("default", "disabled"):
        raw_eq[th] = sorted(i for i in v3_iss
                            if d3_equiv(raw_ops(raw[th][i].get("raw_output") or ""),
                                        suite[i]["gold_ops"]))
    v3_all = sorted(i for i, it in suite.items() if it["primary_class"] == "V3")
    pub_eq = {th: sorted(i for i in v3_all
                         if d3_equiv(raw_ops(raw[th][i].get("raw_output") or ""),
                                     suite[i]["gold_ops"])) for th in ("default", "disabled")}
    d3pub = {r["arm"]: r for r in n13.read_csv(IN16["d3_pub"])}
    check("published D3 'opus' (all 220 V3 items) equals the thinking-disabled raw parse",
          "{}/{}".format(len(pub_eq["disabled"]), len(v3_all))
          == d3pub["opus"]["V3_equiv"].split(" ")[0], (len(pub_eq["disabled"]), len(v3_all)))
    for th, ttok in (("default", "Opus"), ("disabled", "OpusNoThink")):
        add("FidelityAllItems" + ttok + "N", len(v3_all))
        add("FidelityAllItems" + ttok + "Count", len(pub_eq[th]))
        add("FidelityAllItems" + ttok + "Share", pct(len(pub_eq[th]), len(v3_all)))
    d3td = {r["arm"]: r for r in n13.read_csv(IN16["d3_td"])}
    check("D3's 'opus' entry equals the thinking-disabled raw parse",
          "{}/154".format(len(raw_eq["disabled"])) == d3td["opus"]["V3_equiv"].split(" ")[0])
    check("raw-text parse and parsed operations agree item by item (both Opus cells)",
          raw_eq["default"] == op_eq and raw_eq["disabled"] == nt_eq)
    md("Claude Opus 5, repeat 0, 154 issuable V3 instructions: default thinking {} equivalent "
       "({}), thinking disabled {} ({}). D3's own parse of the raw text in "
       "proposals_raw.dedup.jsonl gives the same item sets in both cells (asserted), and the "
       "disabled count equals D3's 'opus' entry {} (asserted). Items equivalent under default "
       "thinking only: {}. Items equivalent with thinking disabled only: {}.".format(
           len(op_eq), pctp(len(op_eq), op_n), len(nt_eq), pctp(len(nt_eq), nt_n),
           d3td["opus"]["V3_equiv"].split(" ")[0], ", ".join(only_def) or "none",
           ", ".join(only_dis) or "none"), "",
       "Over all {} published V3 items (the reading of fidelity_pct_published), D3's raw-text "
       "rule gives {} ({}) under default thinking and {} ({}) with thinking disabled; the "
       "disabled count equals analysis/D3_translation_equivalence.csv's 'opus' entry "
       "(asserted).".format(len(v3_all), len(pub_eq["default"]),
                            pctp(len(pub_eq["default"]), len(v3_all)), len(pub_eq["disabled"]),
                            pctp(len(pub_eq["disabled"]), len(v3_all))), "")
    # the figure input
    t3 = {}
    d3 = {}
    for rd, tp, dp in (("published", IN16["t3_pub"], IN16["d3_pub"]),
                       ("issuable_t0", IN16["t3_iss0"], IN16["d3_iss0"]),
                       ("decision_time", IN16["t3_td"], IN16["d3_td"])):
        t3[rd] = {(r["arm"], r["thinking"]): r for r in n13.read_csv(tp)
                  if r["mode"] == "M_constrained"}
        d3[rd] = {r["arm"]: r for r in n13.read_csv(dp)}
    thinking = {"opus": "default", "sonnet": "disabled", "sol": "none"}
    d3_key = {"openai": "mini"}

    def fig_vals(arm, th, rd):
        """the manuscript's figure script() on one reading, one cell."""
        r = t3[rd][(arm, th)]
        num, den = d3[rd][d3_key.get(arm, arm)]["V3_equiv"].split(" ")[0].split("/")
        return (int(r["tier"]), round(100.0 * float(r["v3_separation_share"]), 4),
                round(100.0 * int(num) / int(den), 4), "SPOT-CHECK" in r["coverage_note"])
    with open(IN16["fig4_inputs"], encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    head = [ln for ln in lines if ln.startswith("#")]
    rows_ = list(csv.reader(ln for ln in lines if not ln.startswith("#")))
    cols, data = rows_[0], rows_[1:]
    want_cols = ["arm", "tier", "spot_check", "referral_pct_published", "fidelity_pct_published",
                 "referral_pct_issuable_t0", "fidelity_pct_issuable_t0",
                 "referral_pct_decision_time", "fidelity_pct_decision_time"]
    check("N11_fig4_inputs.csv columns", cols == want_cols, cols)
    check("the figure reads the seven arms, in this order",
          tuple(r[0] for r in data) == FIG_ARMS, [r[0] for r in data])
    # The figure script is checked when present; the public release does not carry it.
    if Path(IN16["fig3_dt_script"]).is_file():
        src = Path(IN16["fig3_dt_script"]).read_text(encoding="utf-8")
        check("fig3_guard_value_dt.py reads analysis/N11_fig4_inputs.csv and these columns",
              '"N11_fig4_inputs.csv"' in src and all(c in src for c in (
                  '"referral_pct_decision_time"', '"fidelity_pct_decision_time"', '"tier"',
                  '"spot_check"', '"arm"')))
    ci = {c: j for j, c in enumerate(cols)}
    for r in data:
        arm = r[0]
        th = thinking.get(arm, "-")
        for rd in ("published", "issuable_t0", "decision_time"):
            tier, sep, fid, spot = fig_vals(arm, th, rd)
            check("figure input rebuilt from T3/D3 ({} {})".format(arm, rd),
                  abs(float(r[ci["referral_pct_" + rd]]) - sep) < 1e-9
                  and abs(float(r[ci["fidelity_pct_" + rd]]) - fid) < 1e-9
                  and int(r[ci["tier"]]) == tier and r[ci["spot_check"]] == str(spot),
                  (arm, rd, r, tier, sep, fid, spot))
    op_row = [r for r in data if r[0] == "opus"][0]
    check("the figure's Opus fidelity is the no-think cell's",
          abs(float(op_row[ci["fidelity_pct_decision_time"]])
              - round(100.0 * len(nt_eq) / nt_n, 4)) < 1e-9)
    check("the figure's Opus referral is the default cell's (278/308)",
          op_row[ci["referral_pct_decision_time"]] == repr(round(100.0 * 278 / 308, 4)))
    corrected = repr(round(100.0 * len(op_eq) / op_n, 4))
    out_rows = []
    for r in data:
        r2 = list(r)
        if r[0] == "opus":
            r2[ci["fidelity_pct_decision_time"]] = corrected
        out_rows.append(r2)
    nt = OrderedDict()
    for rd in ("published", "issuable_t0", "decision_time"):
        nt[rd] = fig_vals("opus", "disabled", rd)
    check("one tier and one spot flag for the no-think row",
          len({v[0] for v in nt.values()}) == 1 and len({v[3] for v in nt.values()}) == 1)
    check("the no-think decision-time fidelity equals the per-row count",
          abs(nt["decision_time"][2] - round(100.0 * len(nt_eq) / nt_n, 4)) < 1e-9)
    nt_row = [NOTHINK_KEY, str(nt["decision_time"][0]), str(nt["decision_time"][3])]
    for rd in ("published", "issuable_t0", "decision_time"):
        nt_row += [repr(nt[rd][1]), repr(nt[rd][2])]
    out_rows.append(nt_row)
    with open(OUT_GUARD, "w", newline="", encoding="utf-8") as fh:
        fh.write("# N16 ({}): copy of analysis/N11_fig4_inputs.csv (the per-arm input of "
                 "the manuscript's figure script), identical except "
                 "fidelity_pct_decision_time of 'opus', read from the default-thinking cell "
                 "({}/{} instead of {}/{}), and one added row '{}' for the thinking-disabled "
                 "Opus cell, built as the other rows are (fig3_guard_value.load on the T3 and "
                 "D3 tables of each reading)\n".format(VERSION, len(op_eq), op_n, len(nt_eq),
                                                       nt_n, NOTHINK_KEY))
        for h in head:
            fh.write("# upstream header: " + h.lstrip("# ") + "\n")
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(cols)
        w.writerows(out_rows)
    seven_old = pearson([float(r[ci["fidelity_pct_decision_time"]]) for r in data],
                        [float(r[ci["referral_pct_decision_time"]]) for r in data])
    seven_new = pearson([float(r[ci["fidelity_pct_decision_time"]]) for r in out_rows[:7]],
                        [float(r[ci["referral_pct_decision_time"]]) for r in out_rows[:7]])
    eight = pearson([float(r[ci["fidelity_pct_decision_time"]]) for r in out_rows],
                    [float(r[ci["referral_pct_decision_time"]]) for r in out_rows])
    check("the published decision-time Pearson r (0.972) is reproduced",
          abs(seven_old - 0.972) < 0.0005, seven_old)
    add("FigGuardPearsonPublished", "{:.3f}".format(seven_old))
    add("FigGuardPearsonCorrected", "{:.3f}".format(seven_new))
    add("FigGuardPearsonEightCells", "{:.3f}".format(eight))
    md("### Figure input analysis/N16_fig_guard_value.csv", "",
       "Same columns and row order as analysis/N11_fig4_inputs.csv, which "
       "the manuscript's figure script reads in full (seven arms; it plots arm, "
       "tier, spot_check, referral_pct_decision_time and fidelity_pct_decision_time). Every "
       "value of the seven rows is copied unchanged except Opus's fidelity_pct_decision_time, "
       "{} -> {} (default-thinking cell, {}/{}); the Opus row's referral is the default cell's "
       "278/308 (asserted). The figure's row set has no no-think cell, so one row is "
       "appended, arm key '{}', tier {} and spot_check {} from T3, values for the three "
       "readings built by fig3_guard_value.load's rule (asserted to reproduce every value of "
       "the seven upstream rows). Opus's fidelity_pct_published ({}) and "
       "fidelity_pct_issuable_t0 ({}) also come from D3's thinking-disabled entry and are "
       "left unchanged, as asked. Pearson r of referral against fidelity at the decision "
       "instant: {:.4f} as published (seven arms), {:.4f} with the corrected Opus value, "
       "{:.4f} over the eight cells. The unchanged figure script would not accept this file "
       "as its input: it asserts the fidelity against \\nElevenTabEOneOpusVThreeFidelity, the "
       "arm set against its seven keys and r against 0.972.".format(
           op_row[ci["fidelity_pct_decision_time"]], corrected, len(op_eq), op_n, NOTHINK_KEY,
           nt_row[1], nt_row[2], op_row[ci["fidelity_pct_published"]],
           op_row[ci["fidelity_pct_issuable_t0"]], seven_old, seven_new, eight), "")
    return res, only_def, only_dis                                                               #
# --------------------------------------------------------------------------- #
def block_g(boot, recs, by):
    md("## G. Small facts", "")
    pub = sorted(by.values(), key=lambda r: r["item_id"])
    later = [r for r in pub if r["t_known"] > 0]
    iss = [r for r in later if r["issuable"]]
    niss = [r for r in later if not r["issuable"]]
    check("1,009 of the 2,000 instructions name an order arriving after the window start",
          len(pub) == 2000 and len(later) == 1009, len(later))
    check("an issuable instruction naming a later order has t_d after the window start",
          all(r["t_d"] > 0 for r in iss))
    pr = {r["item_id"] for r in recs}
    add("GLaterNamed", grp(len(later)))
    add("GLaterNamedShare", pct(len(later), len(pub)))
    add("GLaterIssuable", grp(len(iss)))
    add("GLaterIssuablePriced", grp(sum(1 for r in iss if r["item_id"] in pr)))
    add("GLaterNotIssuable", grp(len(niss)))
    iss_all = [r for r in pub if r["issuable"]]
    td_later = [r for r in iss_all if r["t_d"] > 0]
    check("every issuable item with t_d after the window start names a later order",
          {r["item_id"] for r in td_later} == {r["item_id"] for r in iss})
    md("(1) {} of the {} instructions ({}) name an order released after t = 0 (t_known > 0). "
       "{} of them are issuable, and each of these has t_d = t_known after the window start "
       "({} priced at the quality stage); {} are not issuable. Conversely every issuable "
       "instruction with t_d after the window start names such an order ({} = {}).".format(
           len(later), len(pub), pctp(len(later), len(pub)), len(iss),
           sum(1 for r in iss if r["item_id"] in pr), len(niss), len(td_later), len(iss)), "",
       "By class: " + "; ".join("{} {} named, {} issuable".format(
           c, sum(1 for r in later if r["primary_class"] == c),
           sum(1 for r in iss if r["primary_class"] == c))
           for c in D.CLASSES) + ".", "")
    # strict issuability
    pm = n13.macros_of(IN16["n11f_paired_macros"])
    strict = [r for r in recs if by[r["item_id"]]["issuable_strict"]]
    body = []
    for g, gt in (("G-CERT", "Cert"), ("G-CERT-M", "CertM")):
        costly = [r for r in strict if n13.costly_of(r, 0.20) == 1]
        mk = {r["item_id"] for r in costly if not n13.refers(r, g)}
        mf = {r["item_id"] for r in costly if not n13.refers(r["fi"], g)}
        b = "nElevenPairedStrict" + gt
        check("strict rule, {} at 0.20 equals N11F_paired".format(g),
              (str(len(costly)), str(len(mk)), str(len(mf)), str(len(mk & mf))) ==
              (pm[b + "CostlyDeltaTwenty"], pm[b + "MissKDeltaTwenty"],
               pm[b + "MissFIDeltaTwenty"], pm[b + "DiscordantBothDeltaTwenty"]),
              (len(costly), len(mk), len(mf), len(mk & mf)))
        if g == "G-CERT-M":
            check("G-CERT-M strict: 10 of 52", (len(mk), len(costly)) == (10, 52))
        add("GStrict" + gt + "Costly", len(costly))
        add("GStrict" + gt + "MissK", len(mk))
        add("GStrict" + gt + "MissFI", len(mf))
        add("GStrict" + gt + "MissBoth", len(mk & mf))
        body.append([g, len(strict), len(costly), frac(len(mk), len(costly)),
                     frac(len(mf), len(costly)), len(mk & mf)])
    add("GStrictPriced", grp(len(strict)))
    md("(2) Strict issuability rule (t_known < t_start), delta = 0.20, priced proposals:", "")
    md_table(["design", "priced (strict)", "costly", "applied K", "applied FI", "under both"],
             body)
    # paired difference at 0.10
    costly = [r for r in recs if n13.costly_of(r, 0.10) == 1]
    body = []
    for g, gt in (("G-CERT", "Cert"), ("G-CERT-M", "CertM")):
        mk = [0.0 if n13.refers(r, g) else 1.0 for r in costly]
        mf = [0.0 if n13.refers(r["fi"], g) else 1.0 for r in costly]
        dm, lo, hi = n13.paired_ci(boot, costly, mk, mf)
        b = "nElevenPaired" + gt + "MissDiffDeltaTen"
        check("paired K - FI applied share at 0.10 equals N11F_paired ({})".format(g),
              (ppv(dm), ppv(lo), ppv(hi)) == (pm[b], pm[b + "Lo"], pm[b + "Hi"]),
              (dm, lo, hi))
        add("G" + gt + "DiffTen", ppv(dm))
        add("G" + gt + "DiffTenLo", ppv(lo))
        add("G" + gt + "DiffTenHi", ppv(hi))
        body.append([g, len(costly), int(sum(mk)), int(sum(mf)),
                     "{} [{}, {}]".format(ppv(dm), ppv(lo), ppv(hi))])
    md("(3) Paired difference K minus FI in applied share at delta = 0.10 (pp, n13 paired "
       "cluster bootstrap; both rows equal analysis/N11F_paired_macros.tex, asserted):", "")
    md_table(["design", "costly", "applied K", "applied FI", "K - FI (pp) [95% CI]"], body)


# --------------------------------------------------------------------------- #
# I. Second price against the site's own schedule                              #
# --------------------------------------------------------------------------- #
I_RULES = ("wspt", "pfifo", "edd")
I2_DESIGNS = ("G-CERT", "G-CERT-M", "D-REL2")
I_CI = ("G-CERT", "D-REL2")
I_TD = 0.10                      # tau = delta: the tolerance lowered to the cost level
I_ID_TOL = 4e-4                  # WT_anchor_K = LB + gap x max(LB, 1 bh) on printed values
CLS_TOK = OrderedDict([("benign", "Benign"), ("V1", "VOne"), ("V2", "VTwo"), ("V3", "VThree"),
                       ("V4", "VFour"), ("V5", "VFive"), ("V6", "VSix")])
# the design's exploratory cells, asserted
I_EXP = dict(direct20={"G-CERT": (0, 21, 0), "G-CERT-M": (0, 20, 0), "D-REL1": (0, 86, 33),
                       "D-REL2": (0, 39, 1), "D-ABS": (0, 87, 34)},
             differ=(1, 531), rel2_ten=(2, 208, 19), llm=(50, 66, 16))


def site_price(obj_orig, wt_anchor):
    """The second price against the site's own schedule of the untouched known board."""
    return (obj_orig - wt_anchor) / max(wt_anchor, FLOOR)


def own_macros():
    """The N16 macros written so far (name without backslash -> value)."""
    out = {}
    for ln in LINES[1:]:
        head, val = ln.split("}{", 1)
        out[head[len("\\newcommand{\\"):]] = val[:-1]
    return out


def cost_word(c):
    return {1: "costly", 0: "low-cost", None: "undecided"}[c]


def class_counts(rs, key):
    c = Counter(r[key] for r in rs)
    return ", ".join("{} {}".format(k, c[k]) for k in D.CLASSES if c.get(k)) or "none"


def block_i(boot, recs, by, d1, llm):
    n14, items = d1
    llm_recs, n_rows = llm
    own = own_macros()
    n13m = n13.macros_of(IN16["n13_macros"])
    check("class tokens cover the classes", tuple(CLS_TOK) == tuple(D.CLASSES), D.CLASSES)
    check("D-ABS setting equals n13's", SETTING["D-ABS"] == n13.DG14["D-ABS"])
    check("design tokens equal n13's", all(n13.DES_TOK[g] == gt for g, gt in TOK.items()))
    md("## I. Second price against the site's own schedule", "",
       "A variant of the second price that needs no lower bound. It replaces the bound of the "
       "untouched known board by the weighted tardiness of that board as the site's dispatching "
       "rule schedules it: s2_site = (obj_orig_K - WT_anchor_K) / max(WT_anchor_K, 1 bh), and a "
       "field edit is referred when s2_site > tau. obj_orig_K is the executed schedule's "
       "weighted tardiness on the known board scored on the original priorities and time "
       "windows (column obj_orig). WT_anchor_K is column ref1 of analysis/N11_rows_direct.csv "
       "and analysis/N11_rows_e2e.csv (the reference of D-REL1); under the three other rules it "
       "is column anchor_K of analysis/N14_rows.csv. The bound-referenced second price of "
       "blocks 0, D1 and D2 is s2 = (obj_orig_K - LB_anchor_K) / max(LB_anchor_K, 1 bh). "
       "Costly, low-cost, benign, applied and referred are defined as in blocks C and D. First "
       "prices are read at their published thresholds, and either second price is applied to "
       "field edits only. WT_anchor_K is at least LB_anchor_K, so s2_site > tau implies "
       "s2 > tau; the variant refers a subset of the field edits that s2 refers (asserted on "
       "every row).", "")

    # ---- I1: the direct benchmark under the site's rule
    rows_d = OrderedDict()
    for x in n13.read_csv(n13.IN["rows_direct"]):
        if x["dataset"] == "direct_td":
            check("one direct row per item", x["item_id"] not in rows_d, x["item_id"])
            rows_d[x["item_id"]] = x
    check("2,000 direct rows", len(rows_d) == 2000, len(rows_d))
    site, zero = {}, {}
    dev_direct = 0.0
    for r in recs:
        iid = r["item_id"]
        x, it = rows_d[iid], by[iid]
        oo, lb, ref1, ga = (float(x[k]) for k in ("obj_orig", "anchor_lb_K", "ref1",
                                                  "g_cert_anchor"))
        check("direct row priced, with the same edit type",
              x["priced"] == "True" and x["split"] == r["split"], iid)
        dev = abs(ref1 - (lb + ga * max(lb, FLOOR)))
        dev_direct = max(dev_direct, dev)
        check("ref1 = anchor_lb_K + g_cert_anchor x max(anchor_lb_K, 1 bh) within 4e-4 (direct)",
              dev < I_ID_TOL, (iid, dev))
        check("direct row equals the census: obj_orig = dt_obj_orig, anchor_lb_K = an_lb, "
              "ref1 = an_obj = an_obj_orig",
              abs(oo - it["dt_obj_orig"]) < 1e-6 and abs(lb - it["an_lb"]) < 1e-6
              and abs(ref1 - it["an_obj"]) < 1e-6 and abs(ref1 - it["an_obj_orig"]) < 1e-6, iid)
        v = site_price(oo, ref1)
        vf = site_price(it["dt_obj_orig"], it["an_obj"])
        check("printed and full-precision values give the same variant referral",
              (v > TAU) == (vf > TAU) and (v > I_TD) == (vf > I_TD), (iid, v, vf))
        gb = (oo - lb) / max(lb, FLOOR)
        check("printed values give block 0's bound-referenced referral",
              (gb > TAU) == r["sp"] and (gb > I_TD) == (r["g_orig"] > I_TD), iid)
        site[iid] = v
        zero[iid] = x["obj_orig"] == x["ref1"]
    field = [r for r in recs if r["split"] == "field_changing"]
    for r in field:
        check("the variant refers a subset of what s2 refers (direct)",
              r["sp"] or not site[r["item_id"]] > TAU, r["item_id"])
    differ = [r for r in field if (site[r["item_id"]] > TAU) != r["sp"]]
    check("the design: the two second prices differ on 1 of the 531 priced field edits",
          (len(differ), len(field)) == I_EXP["differ"], (len(differ), len(field)))
    add("IFieldPriced", len(field))
    add("ISiteDiffer", len(differ))
    add("ISiteDifferZeroDamage", sum(1 for r in differ if zero[r["item_id"]]))

    def site_flag(r, g):
        return n13.refers(r, g) or (r["split"] == "field_changing" and site[r["item_id"]] > TAU)

    i1 = {}
    body = []
    for dtok, delta in DELTAS.items():
        for g, gt in TOK.items():
            ci = g in I_CI
            s = n13.score(boot, recs, lambda r, g=g: site_flag(r, g), delta, with_ci=ci)
            b = n13.score(boot, recs, lambda r, g=g: sp_flag(r, g), delta, with_ci=ci)
            ben = sum(1 for r, f in zip(s["_cheap"], s["_fr"]) if f
                      and r["primary_class"] == "benign")
            bben = sum(1 for r, f in zip(b["_cheap"], b["_fr"]) if f
                       and r["primary_class"] == "benign")
            pre = "nSixteenDAtc" + gt + "Two"
            check("s2 cells equal block D1's ATC row ({} {})".format(g, delta),
                  (str(b["miss"]), str(b["fr"]), str(bben)) ==
                  (own[pre + "Miss" + dtok], own[pre + "Fr" + dtok], own[pre + "FrBenign" + dtok]),
                  (b["miss"], b["fr"], bben))
            if ci:
                jb = "nThirteenJPubK{}SecondPriceFieldOnlyDelta{}".format(gt, dtok)
                check("s2 interval equals n13 section J ({} {})".format(g, delta),
                      (str(b["miss"]), str(b["fr"]), pctv(b["fr_share"]), pctv(b["fr_lo"]),
                       pctv(b["fr_hi"])) ==
                      (n13m[jb + "Miss"], n13m[jb + "Fr"], n13m[jb + "FrShare"],
                       n13m[jb + "FrLo"], n13m[jb + "FrHi"]), (b["fr"], b["fr_lo"], b["fr_hi"]))
            if delta == 0.20:
                check("the design's direct cell ({} at 0.20)".format(g),
                      (s["miss"], s["fr"], ben) == I_EXP["direct20"][g], (s["miss"], s["fr"], ben))
            if (g, delta) == ("D-REL2", 0.10):
                check("the design's direct cell (D-REL2 at 0.10)",
                      (s["miss"], s["costly"], s["fr"]) == I_EXP["rel2_ten"],
                      (s["miss"], s["costly"], s["fr"]))
            i1[(g, delta)] = (s["miss"], s["fr"], ben)
            p = "I" + gt + "Site"
            add(p + "Miss" + dtok, s["miss"])
            add(p + "Fr" + dtok, s["fr"])
            add(p + "FrBenign" + dtok, ben)
            add(p + "FrShare" + dtok, pct(s["fr"], s["cheap"]))
            if ci:
                add(p + "FrLo" + dtok, pctv(s["fr_lo"]))
                add(p + "FrHi" + dtok, pctv(s["fr_hi"]))
            body.append(["{:.2f}".format(delta), g, s["costly"], "{:,}".format(s["cheap"]),
                         "{} / {}".format(b["miss"], s["miss"]),
                         "{} / {}".format(b["fr"], s["fr"]), "{} / {}".format(bben, ben),
                         "{} [{}, {}]".format(pctpv(b["fr_share"]), pctpv(b["fr_lo"]),
                                              pctpv(b["fr_hi"])) if ci else "",
                         "{} [{}, {}]".format(pctpv(s["fr_share"]), pctpv(s["fr_lo"]),
                                              pctpv(s["fr_hi"])) if ci else ""])
    md("### I1. Direct benchmark, site's rule (ATC), 1,356 priced proposals", "",
       "Each cell is s2 / s2_site. The s2 cells equal block D1's ATC row (\\nSixteenDAtc...Two..., "
       "asserted), and the s2 intervals equal n13 section J "
       "(\\nThirteenJPubK...SecondPriceFieldOnlyDelta..., asserted). Intervals: n13 cluster "
       "bootstrap over instances, n2 seed and replicates.", "")
    md_table(["delta", "first price", "costly", "low-cost", "costly applied (s2 / s2_site)",
              "low-cost referred (s2 / s2_site)", "benign among the referred (s2 / s2_site)",
              "low-cost referral share, s2 [95% CI]", "low-cost referral share, s2_site [95% CI]"],
             body)
    md("The two second prices give different referrals on {} of the {} priced field edits "
       "(tau = 0.20): {}.".format(
           len(differ), len(field), "; ".join(
               "{} ({}, {} at 0.20 and {} at 0.10; s2 = {:.4f}, s2_site = {:.4f}; obj_orig {} "
               "ref1)".format(r["item_id"], r["primary_class"],
                              cost_word(n13.costly_of(r, 0.20)), cost_word(n13.costly_of(r, 0.10)),
                              r["g_orig"], site[r["item_id"]],
                              "equals" if zero[r["item_id"]] else "differs from")
               for r in differ) or "none"), "")

    # ---- I2: the three other dispatching rules
    body, dbody, cbody = [], [], []
    dev_rule = {}
    for rule in ("atc",) + I_RULES:
        rt = RULES[rule]
        pr = [n14[rule][i] for i in sorted(n14[rule]) if n14[rule][i]["priced_K"] == "True"]
        sv, zr = {}, {}
        dev_rule[rule] = 0.0
        for r in pr:
            iid = r["item_id"]
            it = items[rule][iid]
            check("anchor_K logged on every priced row ({})".format(rule),
                  r["anchor_K"] != "" and r["anchor_lb_K"] != "", iid)
            a, lb = float(r["anchor_K"]), float(r["anchor_lb_K"])
            dev = abs(a - (lb + it["an_gap"] * max(lb, FLOOR)))
            dev_rule[rule] = max(dev_rule[rule], dev)
            check("anchor_K = anchor_lb_K + an_gap x max(anchor_lb_K, 1 bh) within 4e-4 ({})"
                  .format(rule), dev < I_ID_TOL, (iid, dev))
            check("anchor_K = an_obj = an_obj_orig and anchor_lb_K = an_lb ({})".format(rule),
                  abs(a - it["an_obj"]) < 1e-6 and abs(a - it["an_obj_orig"]) < 1e-6
                  and abs(lb - it["an_lb"]) < 1e-6, iid)
            v = site_price(it["dt_obj_orig"], a)
            check("printed and full-precision anchors give the same variant referral ({})"
                  .format(rule), (v > TAU) == (site_price(it["dt_obj_orig"], it["an_obj"]) > TAU),
                  iid)
            sv[iid] = v
            zr[iid] = abs(it["dt_obj_orig"] - it["an_obj"]) < 1e-6
            if rule == "atc":
                check("ATC variant price equals the direct benchmark's", abs(v - site[iid]) < 1e-6,
                      (iid, v, site[iid]))
        fld = [r for r in pr if r["split"] == "field_changing"]
        for r in fld:
            check("the variant refers a subset of what s2 refers ({})".format(rule),
                  r["_sp"] or not sv[r["item_id"]] > TAU, r["item_id"])
        dif = [r for r in fld if (sv[r["item_id"]] > TAU) != r["_sp"]]

        def anchor_g(r, rule=rule):
            it = items[rule][r["item_id"]]
            return (it["an_obj_orig"] - it["an_lb"]) / max(it["an_lb"], FLOOR)
        nz = sum(1 for r in dif if zr[r["item_id"]])
        nsb = sum(1 for r in dif if anchor_g(r) > TAU)
        if rule == "atc":
            check("ATC: the same field edits and the same differing set as the direct benchmark",
                  len(fld) == len(field) and {r["item_id"] for r in dif} ==
                  {r["item_id"] for r in differ})
        else:
            add("I" + rt + "FieldPriced", len(fld))
            add("I" + rt + "SiteDiffer", len(dif))
            add("I" + rt + "SiteDifferZeroDamage", nz)
            add("I" + rt + "SiteDifferSelfBlocking", nsb)
        cc = Counter((cost_word(cost_class(r["_lo"], r["_hi"], 0.20)),
                      cost_word(cost_class(r["_lo"], r["_hi"], 0.10))) for r in dif)
        dc10 = [r for r in dif if cost_class(r["_lo"], r["_hi"], 0.10) == 1]
        check("no differing field edit is costly at 0.20 ({})".format(rule),
              all(cost_class(r["_lo"], r["_hi"], 0.20) != 1 for r in dif))
        if rule != "atc":
            add("I" + rt + "SiteDifferCostlyTen", len(dc10))
        for r in dc10:
            it = items[rule][r["item_id"]]
            cbody.append([rule, r["item_id"], r["primary_class"],
                          "[{:.4f}, {:.4f}]".format(r["_lo"], r["_hi"]),
                          "{:.4f}".format((it["dt_obj_orig"] - it["an_lb"])
                                          / max(it["an_lb"], FLOOR)),
                          "{:.4f}".format(sv[r["item_id"]]),
                          " / ".join("{:.4f}".format(n13.fnum(r["p_K_" + g])) for g in I2_DESIGNS),
                          ", ".join(g for g in I2_DESIGNS
                                    if not n13.fnum(r["p_K_" + g]) > SETTING[g]) or "none"])
        dbody.append([rule, "{:,}".format(len(pr)), len(fld), len(dif), nz, nsb,
                      class_counts(dif, "primary_class"),
                      ", ".join("{} at 0.20 / {} at 0.10: {}".format(a, b, n)
                                for (a, b), n in sorted(cc.items())) or "none",
                      ", ".join(r["item_id"] for r in dif) or "none"])
        for dtok, delta in DELTAS.items():
            costly = [r for r in pr if cost_class(r["_lo"], r["_hi"], delta) == 1]
            low = [r for r in pr if cost_class(r["_lo"], r["_hi"], delta) == 0]
            for g in I2_DESIGNS:
                gt = TOK[g]

                def f1(r, g=g):
                    v = n13.fnum(r["p_K_" + g])
                    return v is not None and v > SETTING[g]

                cells = OrderedDict()
                for key in ("two", "site"):
                    def fl(r, key=key, f1=f1, sv=sv):
                        sec = r["_sp"] if key == "two" else sv[r["item_id"]] > TAU
                        return f1(r) or (r["split"] == "field_changing" and sec)
                    fr = [r for r in low if fl(r)]
                    cells[key] = (sum(1 for r in costly if not fl(r)), len(fr),
                                  sum(1 for r in fr if r["primary_class"] == "benign"))
                dcd = [r for r in dif if cost_class(r["_lo"], r["_hi"], delta) == 1]
                check("the variant's extra applied proposals are the costly differing field edits "
                      "that the first price leaves ({} {} {})".format(rule, g, delta),
                      cells["site"][0] - cells["two"][0] == sum(1 for r in dcd if not f1(r)),
                      (cells, len(dcd)))
                pre = "nSixteenD" + rt + gt + "Two"
                check("s2 cells equal block D1 ({} {} {})".format(rule, g, delta),
                      tuple(str(v) for v in cells["two"]) ==
                      (own[pre + "Miss" + dtok], own[pre + "Fr" + dtok],
                       own[pre + "FrBenign" + dtok]), cells["two"])
                if rule == "atc":
                    check("ATC rows of N14 reproduce I1 ({} {})".format(g, delta),
                          cells["site"] == i1[(g, delta)], (cells["site"], i1[(g, delta)]))
                else:
                    p = "I" + rt + gt + "Site"
                    add(p + "Miss" + dtok, cells["site"][0])
                    add(p + "Fr" + dtok, cells["site"][1])
                    add(p + "FrBenign" + dtok, cells["site"][2])
                    add(p + "FrShare" + dtok, pct(cells["site"][1], len(low)))
                body.append([rule, "{:.2f}".format(delta), g, "{:,}".format(len(pr)), len(costly),
                             "{:,}".format(len(low)),
                             "{} / {}".format(cells["two"][0], cells["site"][0]),
                             "{} / {}".format(cells["two"][1], cells["site"][1]),
                             "{} / {}".format(cells["two"][2], cells["site"][2])])
    md("### I2. Under each dispatching rule", "",
       "Per rule, from analysis/N14_rows.csv and results/n14_altdispatch/<rule>/items.jsonl, as "
       "in block D1. WT_anchor_K is column anchor_K of analysis/N14_rows.csv, the weighted "
       "tardiness of the untouched known board under the rule; it equals the rule's "
       "an_lb + an_gap x max(an_lb, 1 bh) and an_obj (asserted). obj_orig_K is the rule's "
       "dt_obj_orig, which block D1's s2 reads. Each cell is s2 / s2_site; the s2 cells equal "
       "block D1's \\nSixteenD<rule><design>Two... macros (asserted). The ATC rows equal I1 "
       "(asserted). The design asks for delta = 0.20; the delta = 0.10 rows are block D1's "
       "second delta.", "")
    md_table(["rule", "delta", "first price", "priced", "costly", "low-cost",
              "costly applied (s2 / s2_site)", "low-cost referred (s2 / s2_site)",
              "benign among the referred (s2 / s2_site)"], body)
    md("Field edits on which the two second prices give different referrals (tau = 0.20). "
       "'Zero damage' = obj_orig_K equals WT_anchor_K (difference below 1e-6 bh). 'Board above "
       "0.20 untouched' = the untouched board's own certified gap under the rule, "
       "(an_obj_orig - an_lb) / max(an_lb, 1 bh), exceeds 0.20 (block D1's reading).", "")
    md_table(["rule", "priced", "priced field edits", "differ", "zero damage among them",
              "board above 0.20 untouched", "class", "cost class", "items"], dbody)
    md("Differing field edits that are costly at delta = 0.10 (none is costly at 0.20). The "
       "variant does not refer them, so each is applied behind every listed first price that "
       "does not refer it at its published threshold:", "")
    md_table(["rule", "item", "class", "realised cost", "s2", "s2_site",
              "first price: " + " / ".join(I2_DESIGNS), "applied behind (with s2_site)"],
             cbody or [["none", "", "", "", "", "", "", ""]])

    # ---- I3: behind the LLM proposers
    e2e = {}
    for x in n13.read_csv(n13.IN["rows_e2e"]):
        if x["dataset"] == "e2e_td" and x["mode"] == "M_constrained" \
                and x["split"] == "field_changing":
            check("one e2e row per row id", x["row_id"] not in e2e, x["row_id"])
            e2e[x["row_id"]] = x
    lsite, lzero = {}, {}
    dev_e2e = 0.0
    for r in llm_recs:
        x = e2e[r["row_id"]]
        oo, lb, ref1, ga = (float(x[k]) for k in ("obj_orig", "anchor_lb_K", "ref1",
                                                  "g_cert_anchor"))
        dev = abs(ref1 - (lb + ga * max(lb, FLOOR)))
        dev_e2e = max(dev_e2e, dev)
        check("ref1 = anchor_lb_K + g_cert_anchor x max(anchor_lb_K, 1 bh) within 4e-4 (e2e)",
              dev < I_ID_TOL, (r["row_id"], dev))
        check("the row's s2 equals block D2's", (oo - lb) / max(lb, FLOOR) == r["g"], r["row_id"])
        lsite[r["row_id"]] = site_price(oo, ref1)
        lzero[r["row_id"]] = x["obj_orig"] == x["ref1"]
        check("the variant refers a subset of what s2 refers (e2e)",
              r["sp"] or not lsite[r["row_id"]] > TAU, r["row_id"])
    cap = [c for c in e1dg.CAPABILITY_SET]
    scopes = OrderedDict()
    scopes["all ten cells"] = ("All", list(n_rows), llm_recs)
    scopes["Table 6 arms (eight cells)"] = ("TableSix", cap,
                                           [r for r in llm_recs if r["cell"] in cap])
    body, gbody = [], []
    for sname, (stok, cells, sel) in scopes.items():
        nr = sum(n_rows[c] for c in cells)

        def vs(r):
            return lsite[r["row_id"]] > TAU
        c20 = [r for r in sel if cost_class(r["lo"], r["hi"], 0.20) == 1]
        l20 = [r for r in sel if cost_class(r["lo"], r["hi"], 0.20) == 0]
        c10 = [r for r in sel if cost_class(r["lo"], r["hi"], 0.10) == 1]
        l10 = [r for r in sel if cost_class(r["lo"], r["hi"], 0.10) == 0]
        big = [r for r in sel if r["dmg"] > 10.0]
        gone = [r for r in sel if r["sp"] and not vs(r)]
        nb, ns = sum(1 for r in sel if r["sp"]), sum(1 for r in sel if vs(r))
        nzero = sum(1 for r in gone if lzero[r["row_id"]])
        pre = "nSixteenLlm" + stok
        check("I3 populations and s2 counts equal block D2 ({})".format(stok),
              (grp(len(sel)), grp(nr), str(len(big)), str(sum(1 for r in big if r["sp"])),
               str(len(c20)), str(sum(1 for r in c20 if r["sp"])), grp(len(l20)),
               str(sum(1 for r in l20 if r["sp"])), str(len(c10)),
               str(sum(1 for r in c10 if r["sp"])), grp(len(l10)),
               str(sum(1 for r in l10 if r["sp"]))) ==
              (own[pre + "Applied"], own[pre + "Rows"], own[pre + "Big"], own[pre + "BigSecond"],
               own[pre + "CostlyTwenty"], own[pre + "CostlySecondTwenty"], own[pre + "LowTwenty"],
               own[pre + "LowSecondTwenty"], own[pre + "CostlyTen"], own[pre + "CostlySecondTen"],
               own[pre + "LowTen"], own[pre + "LowSecondTen"]))
        if stok == "All":
            check("the design: the variant refers 50 of the 8,824 applied field edits against "
                  "66, and the 16 it does not refer have obj_orig equal to ref1",
                  (ns, nb, len(gone)) == I_EXP["llm"] and nzero == len(gone) and len(sel) == 8824,
                  (ns, nb, len(gone), nzero))
        p = "ILlm" + stok
        add(p + "SecondRefers", nb)
        add(p + "SiteRefers", ns)
        add(p + "SiteCostlyTwenty", sum(1 for r in c20 if vs(r)))
        add(p + "SiteLowTwenty", sum(1 for r in l20 if vs(r)))
        add(p + "SiteLowPerHundredTwenty",
            "{:.2f}".format(100.0 * sum(1 for r in l20 if vs(r)) / nr))
        add(p + "SiteBig", sum(1 for r in big if vs(r)))
        add(p + "SiteCostlyTen", sum(1 for r in c10 if vs(r)))
        add(p + "SiteLowTen", sum(1 for r in l10 if vs(r)))
        add(p + "SiteLowPerHundredTen",
            "{:.2f}".format(100.0 * sum(1 for r in l10 if vs(r)) / nr))
        add(p + "SecondNotSite", len(gone))
        add(p + "SecondNotSiteZeroDamage", nzero)
        add(p + "SecondNotSiteItems", len({r["item_id"] for r in gone}))
        gcls = Counter(r["cls"] for r in gone)
        for c, ct in CLS_TOK.items():
            add(p + "SecondNotSite" + ct, gcls.get(c, 0))

        def two(rs):
            return "{} / {} of {:,}".format(sum(1 for r in rs if r["sp"]),
                                            sum(1 for r in rs if vs(r)), len(rs))
        body.append([sname, "{:,}".format(nr), "{:,}".format(len(sel)),
                     "{} / {}".format(nb, ns), two(c20), two(l20),
                     "{:.2f}".format(100.0 * sum(1 for r in l20 if vs(r)) / nr), two(big),
                     two(c10), two(l10)])
        gc = Counter((cost_word(cost_class(r["lo"], r["hi"], 0.20)),
                      cost_word(cost_class(r["lo"], r["hi"], 0.10))) for r in gone)
        gbody.append([sname, len(gone), nzero, ", ".join(
            "{} {}".format(k, gcls[k]) for k in D.CLASSES if gcls.get(k)) or "none",
            ", ".join(sorted({r["item_id"] for r in gone})) or "none",
            ", ".join("{} at 0.20 / {} at 0.10: {}".format(a, b, n)
                      for (a, b), n in sorted(gc.items())) or "none",
            ", ".join("{}/{} {}".format(k[0], k[1], v) for k, v in
                      sorted(Counter(r["cell"] for r in gone).items())) or "none",
            "{:.2f}".format(max(r["dmg"] for r in gone)) if gone else "n/a"])
    md("### I3. Behind the LLM proposers (block D2's rows)", "",
       "Applied field edits as in block D2 (edit type field_changing, certified gap at most "
       "0.20), every constrained cell and repeat. Each cell is s2 / s2_site, and the "
       "populations and s2 counts equal block D2's \\nSixteenLlm<scope>... macros (asserted). "
       "Per 100 rows: low-cost referrals by s2_site per 100 constrained rows of the scope.", "")
    md_table(["scope", "constrained rows", "applied field edits", "referred (s2 / s2_site)",
              "costly at 0.20", "low-cost at 0.20", "per 100 rows, s2_site (0.20)",
              "damage > 10 bh", "costly at 0.10", "low-cost at 0.10"], body)
    md("Applied field edits that s2 refers and s2_site does not. 'Zero damage on the known "
       "board' = the printed obj_orig equals the printed ref1.", "")
    md_table(["scope", "rows", "zero damage on the known board", "class", "items",
              "realised cost class", "cells", "max damage if applied (bh)"], gbody)

    # ---- I4: the tolerance lowered to the cost level
    jb_recs = [dict(r, sp=r["g_orig"]) for r in recs]
    js_recs = [dict(r, sp=site[r["item_id"]]) for r in recs]
    fdiff = sum(1 for r in field if (r["g_orig"] > I_TD) != (site[r["item_id"]] > I_TD))
    add("ITauDeltaSiteDifferTen", fdiff)
    body = []
    for g, gt in TOK.items():
        ci = g in I_CI

        def fl(r, g=g):
            return n13.j_flag(r, g, "second", "fieldonly", "taudelta", I_TD)
        b = n13.score(boot, jb_recs, fl, I_TD, with_ci=ci)
        s = n13.score(boot, js_recs, fl, I_TD, with_ci=ci)
        bben = sum(1 for r, f in zip(b["_cheap"], b["_fr"]) if f and r["primary_class"] == "benign")
        ben = sum(1 for r, f in zip(s["_cheap"], s["_fr"]) if f and r["primary_class"] == "benign")
        jb = "nThirteenJTauDeltaK{}SecondPriceFieldOnlyDeltaTen".format(n13.DES_TOK[g])
        got = (str(b["miss"]), str(b["fr"]), pctv(b["fr_share"]))
        exp = (n13m[jb + "Miss"], n13m[jb + "Fr"], n13m[jb + "FrShare"])
        if ci:
            got += (pctv(b["fr_lo"]), pctv(b["fr_hi"]))
            exp += (n13m[jb + "FrLo"], n13m[jb + "FrHi"])
        check("tau = delta, s2 cells equal n13 section J ({})".format(g), got == exp, (got, exp))
        p = "ITauDelta" + gt + "Site"
        add(p + "MissTen", s["miss"])
        add(p + "FrTen", s["fr"])
        add(p + "FrBenignTen", ben)
        add(p + "FrShareTen", pct(s["fr"], s["cheap"]))
        if ci:
            add(p + "FrLoTen", pctv(s["fr_lo"]))
            add(p + "FrHiTen", pctv(s["fr_hi"]))
        body.append([g, "0.8119 bh" if g == "D-ABS" else "0.10", s["costly"],
                     "{:,}".format(s["cheap"]), "{} / {}".format(b["miss"], s["miss"]),
                     "{} / {}".format(b["fr"], s["fr"]), "{} / {}".format(bben, ben),
                     "{} [{}, {}]".format(pctpv(b["fr_share"]), pctpv(b["fr_lo"]),
                                          pctpv(b["fr_hi"])) if ci else "",
                     "{} [{}, {}]".format(pctpv(s["fr_share"]), pctpv(s["fr_lo"]),
                                          pctpv(s["fr_hi"])) if ci else ""])
    md("### I4. The tolerance lowered to the cost level (tau = delta = 0.10), direct benchmark",
       "", "n13 section J's 'tau = delta' reading: every first price except D-ABS and the "
       "second price are read at 0.10, D-ABS stays at 0.8119 bh, and the second price is applied "
       "to field edits only (n13.j_flag, with the second price replaced by s2_site for the "
       "variant). Each cell is s2 / s2_site. The s2 cells equal "
       "\\nThirteenJTauDeltaK<design>SecondPriceFieldOnlyDeltaTen... (asserted). At tau = 0.10 "
       "the two second prices give different referrals on {} of the {} priced field edits."
       .format(fdiff, len(field)), "")
    md_table(["first price", "first-price threshold", "costly", "low-cost",
              "costly applied (s2 / s2_site)", "low-cost referred (s2 / s2_site)",
              "benign among the referred (s2 / s2_site)", "low-cost referral share, s2 [95% CI]",
              "low-cost referral share, s2_site [95% CI]"], body)
    md("Identity WT_anchor_K = LB_anchor_K + certified anchor gap x max(LB_anchor_K, 1 bh), "
       "largest deviation (printed values; asserted below 4e-4): direct benchmark {:.1e}, LLM "
       "rows {:.1e}, {}.".format(dev_direct, dev_e2e, ", ".join(
           "{} {:.1e}".format(rule, dev_rule[rule]) for rule in ("atc",) + I_RULES)), "")


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main():
    for k, p in IN16.items():
        if not Path(p).is_file() and k != "fig3_dt_script":
            raise SystemExit("missing input {}: {}".format(k, p))
    hashes, items_dt, _pub, boot, fc = n13.load_inputs()
    recs, by = build_recs(items_dt, fc)
    full_br = D.full_brackets()
    # the realised-cost reimplementation used in D2, tied to the direct benchmark
    # (N11_rows_forecast.csv prints orig_m_lo/hi with six decimals)
    for r in recs:
        it = by[r["item_id"]]
        lo, hi = realised_range(it["rw_obj_orig"], it["pub_anchor_wwt"], r["instance_id"],
                                full_br)
        check("realised cost reproduces orig_m_lo/hi ({})".format(r["item_id"]),
              lo is not None and abs(lo - r["lo"]) < 6e-7 and abs(hi - r["hi"]) < 6e-7,
              (lo, hi, r["lo"], r["hi"]))
    MD.extend(["# N16: robustness of the decision-time comparison ({})".format(VERSION), "",
               "Generated by `code/scripts/n16_robustness.py` on cores 14-15 (one thread) from "
               "the logged results only: no solve, no model call, no GPU. It reuses "
               "n13_fromlogs.py (load_inputs, score, costly_of, refers, paired_ci, section_f "
               "and the n2 cluster bootstrap: seed {}, {} replicates, {} instance clusters); "
               "n13's source is loaded with its core allowance set to cores 14-15 and is not "
               "modified on disk. Macros: analysis/N16_macros.tex (prefix \\nSixteen). Figure "
               "data: analysis/N16_fig_known_share.csv, analysis/N16_fig_curves.csv.".format(
                   n13.n2.SEED, n13.n2.B_BOOT, boot.k), ""])
    section0(boot, recs)
    block_a(recs)
    block_b(boot, recs, by)
    block_c(boot, fc, items_dt)
    d1 = block_d1(recs)
    llm = block_d2(full_br)
    block_e(recs)
    cells, suite = block_f(boot, fc)
    block_g(boot, recs, by)
    block_h(cells, suite)
    block_i(boot, recs, by, d1, llm)
    hashes16 = OrderedDict(hashes)
    hashes16.update((k, n13.sha256(p) if Path(p).is_file() else "not shipped")
                    for k, p in IN16.items())
    paths = OrderedDict(list(n13.IN.items()) + list(IN16.items()))
    MD.extend(["## Inputs", ""] + ["- {} `{}` sha256 {}".format(
        k, Path(paths[k]).relative_to(ROOT), v) for k, v in hashes16.items()] + [""])
    OUT_TEX.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    OUT_MD.write_text("\n".join(MD + ["{} assertions passed; {} macros.".format(
        NCHECK[0], len(NAMES))]) + "\n", encoding="utf-8")
    print("[n16] {} macros, {} assertions passed".format(len(NAMES), NCHECK[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
