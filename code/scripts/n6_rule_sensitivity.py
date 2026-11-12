#!/usr/bin/env python
"""N6: how the anchor gap and the D-REL2 price depend on the site's dispatching rule.

WHY THIS EXISTS
---------------
Every schedule in the study is produced by one dispatching rule, ATC with
look-ahead k = 2 at seed 0 (the published episode).  N2 found that D-REL2,
whose reference is that same dispatcher run on the adjusted fields without the
proposal's constraints, under-prices a proposal against the oracle by about
the dispatcher's own gap to the optimum on the untouched instance,

    g_anchor = (WT_rule(base) - OPT_base) / max(OPT_base, 1 bh),

and that it prices the instruction's own cost almost exactly once that gap is
subtracted (the marginal reading).  Both statements were measured for ATC
only.  This script repeats the two measurements under other dispatching rules
of the Y1 environment (fmwos.pdrs), so the result says whether "the rule's
absolute under-pricing equals the dispatcher's own gap" holds for every
dispatcher.

RULES
-----
``atc`` (k = 2, the published rule, re-run as the reproduction control),
``edd`` (earliest due date), ``wspt`` (weighted shortest processing time),
``pfifo`` (priority class first, first in first out within a class),
``wmdd`` (weighted modified due date), ``atc_k1`` and ``atc_k3`` (ATC at
look-ahead 1 and 3).  Every rule is the environment's own pick function
(``fmwos.pdrs.get_rule``); none is re-implemented here.  The seed is 0
throughout; no rule above draws from the seeded generator.

TWO READINGS OF "THE SITE'S RULE"
---------------------------------
site_rule       The site runs rule R everywhere: the baseline schedule (from
                which freezes and the episode's standing frozen set take their
                slots), the proposal's executed schedule obj_R, and the D-REL2
                reference WT_ref2,R (the same adjusted fields dispatched by R
                without the proposal's constraints).  A proposal without a
                constraining operation has WT_ref2,R = obj_R by construction
                (asserted by dispatching it).
reference_only  The site keeps the published episode (baseline, adjusted
                instance and executed objective under ATC, so obj is the
                logged objective), and only the gate's reference is dispatched
                by R on that same adjusted instance at the same seed.  Here a
                proposal without a constraining operation has a non-zero price
                whenever R and ATC disagree on the adjusted fields.
For ATC the two readings coincide with N2 (asserted row by row).

PRICES AND TRUTHS (the N2 conventions, code/scripts/n2_pricing.py)
-----------------------------------------------------------------
price           p = (obj - WT_ref2) / max(WT_ref2, 1), obj and WT_ref2 rounded
                as n2_pricing.rel_delta does.
absolute truth  g_true = (obj - OPT_adj) / max(OPT_adj, 1), clamped at zero.
marginal truth  m_true = g_true - g_anchor,R, with g_anchor,R the anchor gap of
                the reference rule R on the untouched instance.  In the
                site_rule reading obj is executed by R, so m_true is the
                instruction's own cost under that site; in the reference_only
                reading it is the price left after removing what R itself
                loses, which is the quantity D-REL2,R should equal if its
                under-pricing is the reference's own gap.
OPT             the oracle bracket [lower, upper] of results/oracle_v1/
                brackets.jsonl (baseline: the row whose fingerprint is that of
                the empty change list, i.e. n_changed_orders = 0).  As in N2,
                a bracket with width_rel < 1e-3 is read at its midpoint and a
                wider one is carried as an interval: a row counts as
                under-priced only when the whole interval says so, and the
                undecided rows leave the share's numerator and denominator.
                Every table also carries the reading at the bracket's lower
                end (columns *_at_lower), the most demanding truth.
under-priced    p - truth < -0.05; over-priced p - truth > +0.05.

FOUR LAUNCH QUESTIONS (the project's standing experiment rules), answered before the run
---------------------------------------------------------------------------------
1. PURPOSE.  One question: is D-REL2's absolute under-pricing the reference
   dispatcher's own anchor gap for every dispatcher, and is the marginal
   reading near-exact for every dispatcher?  The numbers land in one new
   Supplementary table (anchor gap by rule and stratum; D-REL2 under-pricing by
   rule, reading and stratum) and one body sentence on the dispatcher
   sensitivity of the pricing result.
2. EXPECTED RESULT.  Weaker rules (EDD, WSPT, PFIFO) carry larger anchor gaps
   on the Primary stratum than ATC, so their absolute under-pricing shares
   grow with the gap, while their marginal under-pricing shares stay near
   N2's ATC values.  If instead the marginal share grows with the rule, the
   N2 decomposition is specific to ATC and the paper says so.
3. CONTAMINATION.  Read-only on results/oracle_v1/, analysis/DG1_direct_guard
   .csv, analysis/N2_*.csv and N2_macros.tex; outputs go to analysis/N6_*
   only; nothing under the manuscript folder is written.  The only computation is
   deterministic dispatch (no time budget, so not a timing measurement), run
   on cores 8-11 with one numerical thread per worker; cores 0-7 and 12-23
   belong to other jobs and are refused.
4. DATA ACCURACY.  The suite's SHA-256 and every instance file's SHA-256
   against code/scripts/instance_manifest_l1.json (the instances_v10 snapshot,
   loaded through suite_gate).  Every proposal is re-applied through the
   adapter and its executed ATC objective compared with the logged one (DG1
   and N2, 1e-6 bh; the oracle item file, 1e-4 bh); its field fingerprint is
   recomputed under every rule and compared with the oracle's; the ATC
   reference reproduces N2's WT_ref2 on every row; the ATC anchor gaps
   reproduce N2's \\nTwoRefGap* macros to their printed precision; the ATC
   pricing counts reproduce N2_pricing_direct.csv cell by cell; every rule's
   plain Y1 dispatch equals the adapter's no-op dispatch.  Any failure aborts.

OUTPUTS (analysis/)
-------------------
N6_anchor_gap_by_rule.csv   per rule and stratum (block "stratum") and per
                            rule and instance (block "instance")
N6_rel2_by_rule.csv         D-REL2 pricing per rule, reading, truth, split
                            and stratum
N6_summary.md               what was computed, the tables, one sentence each
N6_macros.tex               with --macros

Run::

    taskset -c 8-11 python \\
        code/scripts/n6_rule_sensitivity.py --macros

Version: l1-n6-rule-sensitivity-1
"""

from __future__ import annotations

import os

for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
             "NUMEXPR_NUM_THREADS"):
    os.environ[_var] = "1"

import argparse  # noqa: E402
import csv  # noqa: E402
import datetime as _dt  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from collections import OrderedDict, defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# n2_pricing pins the instance root to the snapshot and refuses any other.
import n2_pricing as n2  # noqa: E402
import oracle_cost as oc  # noqa: E402

e1dg = n2.e1dg
sg = n2.sg
np = n2.np

VERSION = "l1-n6-rule-sensitivity-1"
ANALYSIS = n2.ANALYSIS

PUBLISHED_RULE = "atc"
SEED = 0
RULES = ("atc", "edd", "wspt", "pfifo", "wmdd", "atc_k1", "atc_k3")
RULE_LABEL = OrderedDict([
    ("atc", "ATC, k = 2 (published)"), ("edd", "Earliest due date"),
    ("wspt", "Weighted shortest processing time"),
    ("pfifo", "Priority class, then first in first out"),
    ("wmdd", "Weighted modified due date"), ("atc_k1", "ATC, k = 1"),
    ("atc_k3", "ATC, k = 3")])
RULE_TOKEN = {"atc": "Atc", "edd": "Edd", "wspt": "Wspt", "pfifo": "Pfifo",
              "wmdd": "Wmdd", "atc_k1": "AtcKOne", "atc_k3": "AtcKThree"}
READINGS = ("site_rule", "reference_only")
READING_TOKEN = {"site_rule": "Site", "reference_only": "Ref"}
TRUTHS = ("absolute", "marginal")
STRATA = n2.STRATA
STRATUM_NAME = {"all": "Pooled", "c09_storm2_w80": "Primary",
                "c10_storm2_w80": "Confirmation", "c10_replay_400": "Buildings"}
SPLITS = n2.SPLITS
TAU = 0.20
PRICE_TOL = n2.PRICE_TOL
FLOOR_BH = n2.FLOOR_BH
RECOMP_TOL_BH = n2.RECOMP_TOL_BH
#: N2_rows_direct.csv prints bh values to six decimals.
CSV_TOL_BH = 1.5e-6
#: N2_pricing_direct.csv prints errors to six decimals.
CSV_TOL_ERR = 1.5e-6
DEFAULT_CORES = "8-11"
FORBIDDEN_CORES = n2.FORBIDDEN_CORES
N2_STRATUM_TOKEN = {"all": "All", "c09_storm2_w80": "CNineStorm",
                    "c10_storm2_w80": "CTenStorm", "c10_replay_400": "CTenReplay"}

gfun = n2.gfun
pctl = n2.pctl
pct = n2.pct
interval_text = n2.interval_text
fmt = n2.fmt
refuse = n2.refuse


# --------------------------------------------------------------------------- #
# Dispatch workers                                                             #
# --------------------------------------------------------------------------- #
def _fields_fp(instance, adjusted_instance):
    """The oracle's field fingerprint of an adjusted instance (oracle_cost.Store)."""
    base = {wo["id"]: tuple(wo[f] for f in oc.FIELDS) for wo in instance["work_orders"]}
    tuples = []
    for wo in adjusted_instance["work_orders"]:
        cur = tuple(wo[f] for f in oc.FIELDS)
        if cur != base[wo["id"]]:
            tuples.append((wo["id"],) + cur)
    return oc.fp_of(tuples)


def _apply(apply_mod, instance, ops, frozen, baseline):
    """The adapter's apply, strict first and lenient as N2's fallback does."""
    try:
        return apply_mod.apply_proposal(instance, {"operations": ops}, frozen_seed=frozen,
                                        baseline_schedule=baseline, strict_schema=True), True
    except Exception:  # noqa: BLE001 - the lenient parse is retried below
        return apply_mod.apply_proposal(instance, {"operations": ops}, frozen_seed=frozen,
                                        baseline_schedule=baseline, strict_schema=False), False


def _reference(apply_mod, dispatch_mod, evaluate, adjusted, frozen, baseline, rule):
    """WT_ref2 under ``rule``: the adjusted fields without the proposal's constraints."""
    try:
        ref_adj = apply_mod.apply_operations(adjusted.instance, [], frozen_seed=frozen,
                                             baseline_schedule=baseline)
        sched = dispatch_mod.dispatch_adjusted(ref_adj, rule, SEED)
        return evaluate.wwt(ref_adj, sched), "dispatched"
    except Exception as exc:  # noqa: BLE001 - recorded, as N2 does
        return None, "unavailable:" + type(exc).__name__


def _measure_row(unit):
    from l1adapter import apply as apply_mod, dispatch as dispatch_mod, evaluate

    cache = e1dg._STATE["cache"]
    path = unit["path"]
    inst = cache.instance(path)
    frozen, ops = list(unit["frozen"]), list(unit["ops"])
    base_pub = cache.baseline(path, PUBLISHED_RULE, SEED)
    out = {"key": unit["key"], "rules": {}}
    adj_pub, strict_pub = _apply(apply_mod, inst, ops, frozen, base_pub)
    sched_pub = dispatch_mod.dispatch_adjusted(adj_pub, PUBLISHED_RULE, SEED)
    out["obj_pub"] = evaluate.wwt(adj_pub, sched_pub)
    out["fp_pub"] = _fields_fp(inst, adj_pub.instance)
    out["strict_pub"] = strict_pub
    for rule in unit["rules"]:
        rec = {}
        rec["ref_reference_only"], rec["from_reference_only"] = _reference(
            apply_mod, dispatch_mod, evaluate, adj_pub, frozen, base_pub, rule)
        base_r = cache.baseline(path, rule, SEED)
        try:
            adj_r, strict_r = _apply(apply_mod, inst, ops, frozen, base_r)
            sched_r = dispatch_mod.dispatch_adjusted(adj_r, rule, SEED)
            rec["obj_site_rule"] = evaluate.wwt(adj_r, sched_r)
            rec["fp_site_rule"] = _fields_fp(inst, adj_r.instance)
            rec["strict_site_rule"] = strict_r
            rec["ref_site_rule"], rec["from_site_rule"] = _reference(
                apply_mod, dispatch_mod, evaluate, adj_r, frozen, base_r, rule)
        except Exception as exc:  # noqa: BLE001 - the proposal cannot run at this site
            rec["obj_site_rule"] = None
            rec["fp_site_rule"] = None
            rec["strict_site_rule"] = None
            rec["ref_site_rule"] = None
            rec["from_site_rule"] = "not_executable:" + type(exc).__name__
        out["rules"][rule] = rec
    return out


def _measure_anchor(unit):
    """Per (instance, frozen set): each rule's plain Y1 dispatch and no-op adapter dispatch."""
    from l1adapter import apply as apply_mod, dispatch as dispatch_mod, evaluate

    cache = e1dg._STATE["cache"]
    path = unit["path"]
    inst = cache.instance(path)
    out = {"key": unit["key"], "rules": {}}
    for rule in unit["rules"]:
        base = cache.baseline(path, rule, SEED)
        plain = evaluate.wwt(inst, base)
        adj = apply_mod.apply_proposal(inst, {"operations": []}, frozen_seed=list(unit["frozen"]),
                                       baseline_schedule=base, strict_schema=True)
        noop = evaluate.wwt(adj, dispatch_mod.dispatch_adjusted(adj, rule, SEED))
        out["rules"][rule] = {"plain": plain, "noop": noop}
    return out


def _chunk(units):
    return [(_measure_anchor(u) if u["kind"] == "anchor" else _measure_row(u)) for u in units]


def run_units(units, workers, cores):
    import multiprocessing as mp

    groups = defaultdict(list)
    for u in units:
        groups[u["path"]].append(u)
    chunks = sorted(groups.values(), key=len, reverse=True)
    out = []
    if workers <= 1:
        e1dg._init(cores)
        for ch in chunks:
            out.extend(_chunk(ch))
        return out
    ctx = mp.get_context("fork")
    with ctx.Pool(workers, initializer=e1dg._init, initargs=(cores,)) as pool:
        for res in pool.imap_unordered(_chunk, chunks):
            out.extend(res)
    return out


# --------------------------------------------------------------------------- #
# Anchor gaps                                                                  #
# --------------------------------------------------------------------------- #
def anchor_records(binfo, brackets, anchors_by_rule, strata):
    """Per rule and instance: the anchor and its gap (N2 interval, and at the lower end)."""
    bfp = n2.base_fp()
    out = []
    for rule in RULES:
        for iid in sorted(strata):
            b = binfo[iid]
            raw = brackets[(iid, bfp)]
            a = anchors_by_rule[rule][iid]
            out.append(OrderedDict(
                block="instance", rule=rule, stratum=strata[iid], instance_id=iid,
                anchor_wt=a, opt_lower=float(raw["lower"]), opt_upper=float(raw["upper"]),
                width_rel=float(raw["width_rel"]), point=b["point"],
                gap_lo=gfun(a, b["up"]), gap_hi=gfun(a, b["lo"]),
                gap_at_lower=gfun(a, float(raw["lower"]))))
    return out


def anchor_summary(inst_rows):
    out = []
    for rule in RULES:
        for st in ("all",) + STRATA:
            rs = [r for r in inst_rows if r["rule"] == rule and (st == "all" or r["stratum"] == st)]
            lo = [r["gap_lo"] for r in rs]
            hi = [r["gap_hi"] for r in rs]
            at = [r["gap_at_lower"] for r in rs]
            out.append(OrderedDict(
                block="stratum", rule=rule, stratum=st, instances=len(rs),
                anchor_wt_median=pctl([r["anchor_wt"] for r in rs], 50),
                gap_median_lo=pctl(lo, 50), gap_median_hi=pctl(hi, 50),
                gap_p90_lo=pctl(lo, 90), gap_p90_hi=pctl(hi, 90),
                gap_max_lo=max(lo), gap_max_hi=max(hi),
                gap_median_at_lower=pctl(at, 50), gap_p90_at_lower=pctl(at, 90),
                gap_max_at_lower=max(at),
                above_tau=sum(1 for r in rs if r["gap_lo"] > TAU),
                above_tau_undecided=sum(1 for r in rs if r["gap_lo"] <= TAU < r["gap_hi"]),
                above_tau_at_lower=sum(1 for r in rs if r["gap_at_lower"] > TAU),
                zero_gap=sum(1 for r in rs if r["gap_hi"] <= 1e-9)))
    return out


# --------------------------------------------------------------------------- #
# Pricing                                                                      #
# --------------------------------------------------------------------------- #
def rule_binfo(binfo, anchors):
    out = {}
    for iid, b in binfo.items():
        nb = dict(b)
        nb["atc"] = anchors[iid]
        nb["ga_lo"], nb["ga_hi"] = gfun(anchors[iid], b["up"]), gfun(anchors[iid], b["lo"])
        out[iid] = nb
    return out


def priced_row(base_row, obj, ref, fingerprint, binfo_r, brackets, anchor_r, base_lower):
    """One row's D-REL2 price, its truths (N2 conventions) and its errors."""
    r = {k: base_row[k] for k in ("row_id", "item_id", "primary_class", "stratum",
                                  "instance_id", "split", "constraining")}
    r["obj"] = obj
    r["ref"] = ref
    r["fingerprint"] = fingerprint
    if obj is None or fingerprint is None:
        r["covered"] = r["covered_m"] = False
        r["p"] = None
        return r
    n2.attach_oracle(r, brackets, binfo_r)
    r["p"] = None if ref is None else n2.rel_delta(obj, ref)
    if r["covered"]:
        g_low = gfun(obj, r["opt_lower"])
        r["g_at_lower"] = g_low
        r["m_at_lower"] = g_low - gfun(anchor_r, base_lower)
    for truth, pre in (("absolute", "e"), ("marginal", "em")):
        t = n2.truth(r, truth)
        r[pre + "_lo"] = r[pre + "_hi"] = r[pre + "_at_lower"] = None
        if t is None or r["p"] is None:
            continue
        r[pre + "_lo"], r[pre + "_hi"] = r["p"] - t[1], r["p"] - t[0]
        r[pre + "_at_lower"] = r["p"] - (r["g_at_lower"] if truth == "absolute"
                                         else r["m_at_lower"])
    return r


def pricing_stats(rows, rule, reading):
    out = []
    for truth, pre in (("absolute", "e"), ("marginal", "em")):
        for split in SPLITS:
            for st in ("all",) + STRATA:
                rs = [r for r in rows if (split == "all" or r["split"] == split)
                      and (st == "all" or r["stratum"] == st)]
                ok = [r for r in rs if r.get(pre + "_lo") is not None]
                lo = [r[pre + "_lo"] for r in ok]
                hi = [r[pre + "_hi"] for r in ok]
                at = [r[pre + "_at_lower"] for r in ok]
                under = sum(1 for r in ok if r[pre + "_hi"] < -PRICE_TOL)
                under_u = sum(1 for r in ok if r[pre + "_lo"] < -PRICE_TOL <= r[pre + "_hi"])
                over = sum(1 for r in ok if r[pre + "_lo"] > PRICE_TOL)
                over_u = sum(1 for r in ok if r[pre + "_lo"] <= PRICE_TOL < r[pre + "_hi"])
                under_at = sum(1 for x in at if x < -PRICE_TOL)
                over_at = sum(1 for x in at if x > PRICE_TOL)
                ud, od = len(ok) - under_u, len(ok) - over_u
                out.append(OrderedDict(
                    rule=rule, reading=reading, truth=truth, split=split, stratum=st,
                    rows=len(rs), not_executable=sum(1 for r in rs if r["obj"] is None),
                    no_reference=sum(1 for r in rs if r["obj"] is not None and r["ref"] is None),
                    priced=len(ok),
                    e_median_lo=pctl(lo, 50), e_median_hi=pctl(hi, 50),
                    e_p05_lo=pctl(lo, 5), e_p05_hi=pctl(hi, 5),
                    e_p95_lo=pctl(lo, 95), e_p95_hi=pctl(hi, 95),
                    under_n=under, under_undecided=under_u,
                    under_share=(under / ud) if ud else None,
                    over_n=over, over_undecided=over_u,
                    over_share=(over / od) if od else None,
                    e_median_at_lower=pctl(at, 50),
                    under_n_at_lower=under_at,
                    under_share_at_lower=(under_at / len(ok)) if ok else None,
                    over_n_at_lower=over_at,
                    over_share_at_lower=(over_at / len(ok)) if ok else None))
    return out


# --------------------------------------------------------------------------- #
# Reproduction against N2                                                      #
# --------------------------------------------------------------------------- #
def read_macros(path):
    out = {}
    for ln in open(path, encoding="utf-8"):
        m = re.match(r"\\newcommand\{\\(\w+)\}\{(.*)\}\s*$", ln.strip())
        if m:
            out[m.group(1)] = m.group(2)
    return out


def check_refgap_macros(check, summary_rows):
    macros = read_macros(ANALYSIS / "N2_macros.tex")
    texts = {}
    for r in summary_rows:
        if r["rule"] != PUBLISHED_RULE:
            continue
        tok = N2_STRATUM_TOKEN[r["stratum"]]
        med = interval_text(100 * r["gap_median_lo"], 100 * r["gap_median_hi"], "{:.1f}") + "\\%"
        mx = interval_text(100 * r["gap_max_lo"], 100 * r["gap_max_hi"], "{:.1f}") + "\\%"
        for name, got in (("nTwoRefGap{}Median".format(tok), med),
                          ("nTwoRefGap{}Max".format(tok), mx)):
            check.eq("ATC anchor gap reproduces \\" + name, macros.get(name), got)
            texts[name] = got
    return texts


def check_pricing_vs_n2(check, stats_atc):
    """The ATC rows of both readings reproduce N2_pricing_direct.csv for D-REL2."""
    want = {}
    for r in n2.read_csv_comments(ANALYSIS / "N2_pricing_direct.csv"):
        if r["gate"] != "D-REL2" or r["group_kind"] not in ("all", "stratum"):
            continue
        want[(r["truth"], r["split"], r["group"])] = r
    n_cells = 0
    for s in stats_atc:
        w = want.get((s["truth"], s["split"], s["stratum"]))
        if w is None:
            continue
        n_cells += 1
        tag = "{}/{}/{}/{}".format(s["reading"], s["truth"], s["split"], s["stratum"])
        for k in ("priced", "under_n", "under_undecided", "over_n", "over_undecided"):
            check.eq("N2 D-REL2 {} {}".format(k, tag), int(w[k]), s[k])
        for k in ("e_median_lo", "e_median_hi", "e_p05_lo", "e_p95_hi"):
            check.true("N2 D-REL2 {} {}".format(k, tag),
                       abs(float(w[k]) - s[k]) <= CSV_TOL_ERR,
                       "{} vs {}".format(w[k], s[k]))
    return n_cells


# --------------------------------------------------------------------------- #
# Writing                                                                      #
# --------------------------------------------------------------------------- #
def _cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, float):
        return "{:.6f}".format(v)
    return str(v)


def write_csv(path, rows, header_lines):
    cols = list(rows[0].keys())
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        for ln in header_lines:
            fh.write("# " + ln + "\n")
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            w.writerow([_cell(r.get(c)) for c in cols])


def macro_name(*parts):
    out = "nSix"
    for p in parts:
        p = "".join(ch for ch in str(p) if ch.isalpha())
        out += p[:1].upper() + p[1:]
    return out


# --------------------------------------------------------------------------- #
# main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--macros", action="store_true", help="also write analysis/N6_macros.tex")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--cores", default=DEFAULT_CORES)
    args = ap.parse_args()

    cores = n2.parse_cores(args.cores)
    if set(cores) & FORBIDDEN_CORES:
        refuse("cores {} overlap cores that belong to other jobs".format(cores))
    if args.workers > len(cores):
        refuse("{} workers on {} cores".format(args.workers, len(cores)))
    os.sched_setaffinity(0, set(cores))
    stamp = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
    t_start = time.time()
    check = n2.Checker()

    # ---------------------------------------------------------------- inputs
    suite = n2.load_suite(check)
    paths, digests = n2.instance_paths(suite, check)
    strata = {it["instance"]["instance_id"]: it["instance"]["stratum"] for it in suite.values()}
    brackets, oracle_items, _props, _census, oracle_digests = n2.load_oracle(check)
    anchors, _anchor_paths, anchor_gaps = e1dg.load_anchors(check)
    anchors_plain = {k[0]: v for k, v in anchors.items() if k[1] == ""}
    check.eq("plain anchors", 60, len(anchors_plain))
    binfo = n2.base_info(brackets, strata)
    missing = sorted(i for i, b in binfo.items() if b is None)
    check.eq("instances without a baseline bracket", [], missing)
    bfp = n2.base_fp()
    for iid in strata:
        b = brackets[(iid, bfp)]
        check.eq("baseline bracket of {} has no changed order".format(iid), 0,
                 int(b.get("n_changed_orders", 0)))
    check.done()

    drows = n2.direct_rows(suite, oracle_items, anchors, anchor_gaps, check)
    n2rows = {r["row_id"]: r for r in n2.read_csv_comments(ANALYSIS / "N2_rows_direct.csv")}
    check.eq("N2 direct rows", len(drows), len(n2rows))
    for r in drows:
        r["split"] = n2.op_split(r["ops"])
        check.true("row in a declared split", r["split"] != "other", r["row_id"])
        check.eq("N2 split of " + r["row_id"], n2rows[r["row_id"]]["split"], r["split"])
    check.done()

    # ---------------------------------------------------------------- dispatch
    units = []
    for r in drows:
        units.append({"kind": "row", "key": r["row_id"], "path": paths[r["instance_id"]],
                      "frozen": list(r["frozen"]), "ops": list(r["ops"]), "rules": RULES})
    seen = set()
    for r in drows:
        k = (r["instance_id"], e1dg.frozen_key(r["frozen"]))
        if k not in seen:
            seen.add(k)
            units.append({"kind": "anchor", "key": k, "path": paths[r["instance_id"]],
                          "frozen": list(r["frozen"]), "rules": RULES})
    for iid in strata:
        if (iid, "") not in seen:
            seen.add((iid, ""))
            units.append({"kind": "anchor", "key": (iid, ""), "path": paths[iid],
                          "frozen": [], "rules": RULES})
    t0 = time.time()
    res = run_units(units, args.workers, cores)
    wall_dispatch = time.time() - t0
    by_row = {x["key"]: x for x in res if isinstance(x["key"], str)}
    by_anchor = {x["key"]: x for x in res if isinstance(x["key"], tuple)}
    check.eq("measured rows", len(drows), len(by_row))

    # ---------------------------------------------------------------- anchors
    anchors_by_rule = {rule: {} for rule in RULES}
    frozen_anchor_drift = defaultdict(list)
    for (iid, fk), a in by_anchor.items():
        for rule in RULES:
            v = a["rules"][rule]
            check.true("plain Y1 dispatch equals the adapter's no-op dispatch ({}, {}, {})"
                       .format(rule, iid, fk), abs(v["plain"] - v["noop"]) <= 1e-9,
                       "{} vs {}".format(v["plain"], v["noop"]))
            if fk == "":
                anchors_by_rule[rule][iid] = v["plain"]
    for (iid, fk), a in by_anchor.items():
        if fk:
            for rule in RULES:
                if abs(a["rules"][rule]["noop"] - anchors_by_rule[rule][iid]) > 1e-9:
                    frozen_anchor_drift[rule].append((iid, fk))
    for rule in RULES:
        check.eq("anchors under " + rule, 60, len(anchors_by_rule[rule]))
    check.eq("ATC frozen-set anchors that differ from the plain one",
             [], frozen_anchor_drift.get(PUBLISHED_RULE, []))
    for iid in strata:
        a = anchors_by_rule[PUBLISHED_RULE][iid]
        check.true("ATC anchor equals the published no-op anchor on " + iid,
                   abs(a - anchors_plain[iid]) <= RECOMP_TOL_BH)
        check.true("ATC anchor equals the bracket's atc_total on " + iid,
                   abs(a - float(brackets[(iid, bfp)]["atc_total"])) <= RECOMP_TOL_BH)
    check.done()

    inst_rows = anchor_records(binfo, brackets, anchors_by_rule, strata)
    anc_summary = anchor_summary(inst_rows)
    refgap_texts = check_refgap_macros(check, anc_summary)
    check.done()

    # ---------------------------------------------------------------- rows
    n_obj = n_fp = n_ref = n_lenient = 0
    for r in drows:
        m = by_row[r["row_id"]]
        n2r = n2rows[r["row_id"]]
        check.true("re-applied objective equals the logged one (DG1) on " + r["row_id"],
                   abs(m["obj_pub"] - r["obj"]) <= RECOMP_TOL_BH,
                   "{} vs {}".format(m["obj_pub"], r["obj"]))
        check.true("re-applied objective equals N2's on " + r["row_id"],
                   abs(m["obj_pub"] - float(n2r["obj"])) <= CSV_TOL_BH)
        check.true("re-applied objective equals the oracle item's on " + r["row_id"],
                   abs(m["obj_pub"] - float(r["obj_oracle"])) <= n2.OBJ_TOL_BH)
        check.eq("fingerprint (published episode) of " + r["row_id"], r["fingerprint"],
                 m["fp_pub"])
        n_obj += 1
        n_lenient += 0 if m["strict_pub"] else 1
        atc = m["rules"][PUBLISHED_RULE]
        for reading in READINGS:
            ref = atc["ref_" + reading]
            check.true("ATC reference ({}) equals N2's WT_ref2 on {}".format(reading, r["row_id"]),
                       ref is not None and abs(ref - float(n2r["ref2"])) <= CSV_TOL_BH,
                       "{} vs {}".format(ref, n2r["ref2"]))
            n_ref += 1
        check.true("ATC site objective equals the published one on " + r["row_id"],
                   atc["obj_site_rule"] is not None
                   and abs(atc["obj_site_rule"] - m["obj_pub"]) <= 1e-9)
        for rule in RULES:
            rec = m["rules"][rule]
            if rec["obj_site_rule"] is None:
                continue
            check.eq("fingerprint under {} of {}".format(rule, r["row_id"]), r["fingerprint"],
                     rec["fp_site_rule"])
            n_fp += 1
            if not r["constraining"]:
                check.true("unconstrained proposal: reference equals objective ({}, {})"
                           .format(rule, r["row_id"]),
                           rec["ref_site_rule"] is not None
                           and abs(rec["ref_site_rule"] - rec["obj_site_rule"]) <= 1e-9)
    check.done()

    # ---------------------------------------------------------------- pricing
    priced = {}
    stats = []
    cert_sound = {}
    for rule in RULES:
        bi = rule_binfo(binfo, anchors_by_rule[rule])
        for reading in READINGS:
            rows = []
            for r in drows:
                m = by_row[r["row_id"]]
                rec = m["rules"][rule]
                if reading == "site_rule":
                    obj, ref, fp = rec["obj_site_rule"], rec["ref_site_rule"], rec["fp_site_rule"]
                else:
                    obj, ref, fp = m["obj_pub"], rec["ref_reference_only"], m["fp_pub"]
                base_lower = float(brackets[(r["instance_id"], bfp)]["lower"])
                rows.append(priced_row(r, obj, ref, fp, bi, brackets,
                                       anchors_by_rule[rule][r["instance_id"]], base_lower))
            priced[(rule, reading)] = rows
            stats.extend(pricing_stats(rows, rule, reading))
        # The certificate's price stays sound under every site rule: LB2 <= OPT.
        worst = None
        for pr in priced[(rule, "site_rule")]:
            if not pr.get("covered"):
                continue
            margin = gfun(pr["obj"], pr["lb2_oracle"]) - gfun(pr["obj"], pr["opt_upper"])
            check.true("certificate never under-prices under " + rule, margin >= -1e-9,
                       pr["row_id"])
            worst = margin if worst is None else min(worst, margin)
        cert_sound[rule] = worst
    n_cells = check_pricing_vs_n2(check, [s for s in stats if s["rule"] == PUBLISHED_RULE])
    check.eq("N2 pricing cells compared (2 readings x 2 truths x 4 splits x 4 groups)", 64,
             n_cells)
    for s in stats:
        if s["rule"] != PUBLISHED_RULE:
            continue
        twin = [t for t in stats if t["rule"] == PUBLISHED_RULE and t["reading"] != s["reading"]
                and t["truth"] == s["truth"] and t["split"] == s["split"]
                and t["stratum"] == s["stratum"]][0]
        check.eq("ATC readings coincide ({}/{}/{})".format(s["truth"], s["split"], s["stratum"]),
                 (s["priced"], s["under_n"], s["over_n"]),
                 (twin["priced"], twin["under_n"], twin["over_n"]))
    check.done()

    # ---------------------------------------------------------------- outputs
    def srow(rule, reading, truth, split, st):
        for s in stats:
            if (s["rule"], s["reading"], s["truth"], s["split"], s["stratum"]) == \
                    (rule, reading, truth, split, st):
                return s
        return None

    def arow(rule, st):
        for a in anc_summary:
            if a["rule"] == rule and a["stratum"] == st:
                return a
        return None

    hdr = ["N6. Anchor gap of each dispatching rule against the oracle ({}), {}".format(
               VERSION, stamp),
           "generated by code/scripts/n6_rule_sensitivity.py",
           "anchor gap = (WT_rule(base) - OPT_base)/max(OPT_base, 1), OPT_base from the baseline "
           "bracket (results/oracle_v1/brackets.jsonl, empty change list); gap_lo/gap_hi: N2 "
           "convention (midpoint when width_rel < 1e-3, else the interval); gap_at_lower: at "
           "the bracket's lower end",
           "above_tau: instances whose whole interval exceeds tau = 0.20; seed 0; rules from "
           "fmwos.pdrs",
           "oracle brackets.jsonl sha256 {}".format(oracle_digests["brackets.jsonl"][0])]
    write_csv(ANALYSIS / "N6_anchor_gap_by_rule.csv", anc_summary + inst_rows, hdr)
    hdr2 = ["N6. D-REL2 pricing under each dispatching rule against the oracle ({}), {}".format(
                VERSION, stamp),
            "generated by code/scripts/n6_rule_sensitivity.py; 1,635 direct-benchmark proposals "
            "(DG1 canonical reading, quality stage)",
            "reading site_rule: baseline, executed schedule and reference all dispatched by the "
            "rule; reading reference_only: published ATC episode, reference dispatched by the rule",
            "price p = (obj - WT_ref2)/max(WT_ref2, 1); truth absolute g_true = (obj - "
            "OPT_adj)/max(OPT_adj, 1); marginal m_true = g_true - anchor gap of the rule",
            "e = p - truth; under-priced e < -0.05 over the whole oracle interval (undecided rows "
            "out of the share); *_at_lower: truth at the bracket's lower end",
            "not_executable: proposal raises when applied or dispatched at that site; "
            "no_reference: the reference counterfactual does not exist (N2 convention)"]
    write_csv(ANALYSIS / "N6_rel2_by_rule.csv", stats, hdr2)

    # ---------------------------------------------------------------- summary
    def gap_txt(a, k):
        return interval_text(100 * a[k + "_lo"], 100 * a[k + "_hi"], "{:.1f}") + "%"

    def share_txt(s, k="under"):
        if s is None or s[k + "_share"] is None:
            return "n/a"
        t = pct(s[k + "_share"]) + "%"
        if s[k + "_undecided"]:
            t += " ({} undecided)".format(s[k + "_undecided"])
        return t

    L = []
    A = L.append
    A("# N6. Sensitivity of the anchor gap and of D-REL2's pricing to the dispatching rule")
    A("")
    A("Generated {} by `code/scripts/n6_rule_sensitivity.py` ({}). {} assertions passed; "
      "dispatch wall time {:.1f} s on cores {} ({} workers, one numerical thread each); "
      "deterministic, no time budget.".format(stamp, VERSION, check.n, wall_dispatch,
                                              args.cores, args.workers))
    A("")
    A("## What was computed")
    A("")
    A("- Rules (the environment's own `fmwos.pdrs` pick functions, seed 0): " +
      "; ".join("`{}` ({})".format(k, v) for k, v in RULE_LABEL.items()) + ".")
    A("- Anchor gap of rule R on each of the 60 replayed instances: (WT_R(untouched) - OPT_base)"
      " / max(OPT_base, 1 bh), with OPT_base the baseline oracle bracket. Intervals follow N2"
      " (midpoint when the bracket's relative width is below 1e-3); the CSV also carries the"
      " value at the bracket's lower end.")
    A("- D-REL2 price of the 1,635 direct-benchmark proposals with R as the reference"
      " dispatcher, in two readings. *Site rule*: the site dispatches everything with R"
      " (baseline slots for freezes, the executed schedule, and the reference). *Reference"
      " only*: the published ATC episode and executed objective are kept, and only the"
      " reference is dispatched by R on the same adjusted instance.")
    A("- Under-priced: price minus truth below -0.05. Absolute truth g_true = (obj - OPT_adj)"
      " / max(OPT_adj, 1); marginal truth m_true = g_true minus R's own anchor gap.")
    A("")
    A("## Assertions")
    A("")
    A("- Suite SHA-256 and all 60 instance files verified against the instances_v10 manifest.")
    A("- {} proposals re-applied through the adapter; executed ATC objective equal to DG1's and"
      " N2's logged objective (1e-6 bh) and to the oracle item file (1e-4 bh); field"
      " fingerprint equal to the oracle's under the published episode and under every rule"
      " where the proposal executes ({} rule-row checks); {} rows needed the lenient parse,"
      " as in N2.".format(n_obj, n_fp, n_lenient))
    A("- ATC reference equal to N2's WT_ref2 on all {} row-readings; ATC pricing counts and"
      " error percentiles equal N2_pricing_direct.csv in all {} D-REL2 cells (2 readings x 2"
      " truths x 4 splits x 4 groups).".format(n_ref, n_cells))
    A("- ATC anchor gaps reproduce N2's macros: " +
      ", ".join("\\{} = {}".format(k, v.replace("\\%", "%")) for k, v in refgap_texts.items()) +
      ".")
    A("- Every rule's plain Y1 dispatch equals the adapter's no-op dispatch on every instance"
      " and frozen set. Frozen-set anchors that differ from the plain anchor (site rule): " +
      ("; ".join("{}: {}".format(k, len(v)) for k, v in frozen_anchor_drift.items() if v)
       or "none") + ".")
    same_pairs = []
    for i, ra in enumerate(RULES):
        for rb in RULES[i + 1:]:
            if all(abs(anchors_by_rule[ra][iid] - anchors_by_rule[rb][iid]) <= 1e-9
                   for iid in strata) and all(
                    by_row[k]["rules"][ra]["obj_site_rule"] == by_row[k]["rules"][rb]["obj_site_rule"]
                    and by_row[k]["rules"][ra]["ref_site_rule"] == by_row[k]["rules"][rb]["ref_site_rule"]
                    for k in by_row):
                same_pairs.append((ra, rb))
    A("- Rules that give the same objective on every instance and every proposal: " +
      ("; ".join("{} and {}".format(a, b) for a, b in same_pairs) or "none") +
      "; each such pair makes the same pick at every dispatch decision on these instances,"
      " so their rows are identical." if same_pairs else
      "- No two rules give the same objective on every instance and proposal.")
    A("- The certificate's price stays sound under every site rule (minimum margin over the"
      " optimistic end of the bracket: " +
      ", ".join("{} {:.2e}".format(k, v) for k, v in cert_sound.items()) + ").")
    A("")

    A("## Table 1. Anchor gap by rule and stratum (60 instances)")
    A("")
    A("Primary = c09_storm2_w80, Confirmation = c10_storm2_w80, Buildings = c10_replay_400."
      " Above 0.20: instances whose whole anchor-gap interval exceeds tau = 0.20. Zero gap:"
      " instances on which the rule is optimal.")
    A("")
    A("| Rule | Stratum | n | median | 90th pct | max | above 0.20 | zero gap |")
    A("|---|---|---|---|---|---|---|---|")
    for rule in RULES:
        for st in ("all",) + STRATA:
            a = arow(rule, st)
            above = str(a["above_tau"])
            if a["above_tau_undecided"]:
                above += " (+{} undecided)".format(a["above_tau_undecided"])
            A("| {} | {} | {} | {} | {} | {} | {} | {} |".format(
                rule, STRATUM_NAME[st], a["instances"], gap_txt(a, "gap_median"),
                gap_txt(a, "gap_p90"), gap_txt(a, "gap_max"), above, a["zero_gap"]))
    A("")
    prim = {rule: arow(rule, "c09_storm2_w80") for rule in RULES}
    alt = [r for r in RULES if r != PUBLISHED_RULE]
    lo_rule = min(alt, key=lambda r: prim[r]["gap_median_hi"])
    hi_rule = max(alt, key=lambda r: prim[r]["gap_median_hi"])
    bld_max = max(arow(r, "c10_replay_400")["gap_max_hi"] for r in RULES)
    A("What it shows: on the Primary stratum the median anchor gap is {} under ATC and ranges"
      " from {} ({}) to {} ({}) under the alternative rules, while on Buildings no rule is more"
      " than {:.1f}% above the optimum.".format(
          gap_txt(prim[PUBLISHED_RULE], "gap_median"), gap_txt(prim[lo_rule], "gap_median"),
          lo_rule, gap_txt(prim[hi_rule], "gap_median"), hi_rule, 100 * bld_max))
    A("")

    A("## Table 2. D-REL2 share under-priced by more than 0.05 (1,635 proposals)")
    A("")
    A("Absolute: against g_true. Marginal: against g_true minus the rule's own anchor gap."
      " Undecided rows (oracle interval straddles the threshold) are out of the share.")
    A("")
    for reading in READINGS:
        A("### Reading: {}".format(reading.replace("_", " ")))
        A("")
        A("| Rule | Stratum | priced | absolute | marginal | marginal over-priced | median e"
          " (absolute) | median e (marginal) |")
        A("|---|---|---|---|---|---|---|---|")
        for rule in RULES:
            for st in ("all",) + STRATA:
                sa = srow(rule, reading, "absolute", "all", st)
                sm = srow(rule, reading, "marginal", "all", st)
                pr = str(sa["priced"])
                miss = sa["not_executable"] + sa["no_reference"]
                if miss:
                    pr += " (of {})".format(sa["rows"])
                A("| {} | {} | {} | {} | {} | {} | {} | {} |".format(
                    rule, STRATUM_NAME[st], pr, share_txt(sa), share_txt(sm),
                    share_txt(sm, "over"),
                    interval_text(sa["e_median_lo"], sa["e_median_hi"]),
                    interval_text(sm["e_median_lo"], sm["e_median_hi"])))
        A("")
    site_abs = {r: srow(r, "site_rule", "absolute", "all", "all")["under_share"] for r in RULES}
    site_marg = {r: srow(r, "site_rule", "marginal", "all", "all")["under_share"] for r in RULES}
    ref_marg = {r: srow(r, "reference_only", "marginal", "all", "all")["under_share"]
                for r in RULES}
    worst_m = max(RULES, key=lambda r: site_marg[r])
    rest = [r for r in RULES if r != worst_m]
    lo_a = min(RULES, key=lambda r: site_abs[r])
    hi_a = max(RULES, key=lambda r: site_abs[r])
    ref_over = {r: srow(r, "reference_only", "marginal", "all", "all")["over_share"]
                for r in RULES}
    A("What it shows: with the site's own rule as the reference, the pooled share of proposals"
      " under-priced against the optimum follows the rule's anchor gap, from {:.1f}% ({}) to"
      " {:.1f}% ({}); after the rule's own anchor gap is subtracted the share falls to {:.1f}%"
      " to {:.1f}% for {} and to {:.1f}% for {}. When only the reference changes and the site"
      " keeps ATC, the marginal under-pricing share is {:.1f}% to {:.1f}%, and {} over-prices"
      " {:.1f}% of proposals because its own gap is larger than the one ATC loses.".format(
          100 * site_abs[lo_a], lo_a, 100 * site_abs[hi_a], hi_a,
          100 * min(site_marg[r] for r in rest), 100 * max(site_marg[r] for r in rest),
          ", ".join(rest), 100 * site_marg[worst_m], worst_m,
          100 * min(ref_marg.values()), 100 * max(ref_marg.values()),
          max(RULES, key=lambda r: ref_over[r]), 100 * max(ref_over.values())))
    A("")
    A("## Split by operation type (pooled, site rule)")
    A("")
    A("| Rule | split | priced | absolute | marginal |")
    A("|---|---|---|---|---|")
    for rule in RULES:
        for split in SPLITS[1:]:
            sa = srow(rule, "site_rule", "absolute", split, "all")
            sm = srow(rule, "site_rule", "marginal", split, "all")
            A("| {} | {} | {} | {} | {} |".format(rule, split, sa["priced"], share_txt(sa),
                                                 share_txt(sm)))
    A("")
    sm_split = {(r, sp): srow(r, "site_rule", "marginal", sp, "all")["under_share"]
                for r in RULES for sp in SPLITS[1:]}
    empty_max = max(sm_split[(r, "empty")] for r in RULES)
    seq_hi = max(RULES, key=lambda r: sm_split[(r, "sequencing_only")])
    A("What it shows: the marginal under-pricing that remains is {:.1f}% at most on proposals"
      " with no operation under every rule, and it sits mainly in sequencing-only proposals,"
      " where the reference and the executed schedule are both dispatched by the rule (largest"
      " share {:.1f}%, under {}).".format(
          100 * empty_max, 100 * sm_split[(seq_hi, "sequencing_only")], seq_hi))
    A("")
    (ANALYSIS / "N6_summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # ---------------------------------------------------------------- macros
    if args.macros:
        M = ["% N6 macros, generated {} by code/scripts/n6_rule_sensitivity.py ({})".format(
                 stamp, VERSION),
             "% GENERATED FILE. Do not edit by hand: rerun the script with --macros."]

        def nc(name, val):
            M.append("\\newcommand{\\" + name + "}{" + val + "}")

        nc(macro_name("Instances"), e1dg.group(len(strata)))
        nc(macro_name("Proposals"), e1dg.group(len(drows)))
        nc(macro_name("Rules"), e1dg.group(len(RULES)))
        for rule in RULES:
            rt = RULE_TOKEN[rule]
            for st in ("all",) + STRATA:
                stok = STRATUM_NAME[st]
                a = arow(rule, st)
                for k, tok in (("gap_median", "AnchorGapMedian"), ("gap_p90", "AnchorGapPNinety"),
                               ("gap_max", "AnchorGapMax")):
                    nc(macro_name(rt, stok, tok),
                       interval_text(100 * a[k + "_lo"], 100 * a[k + "_hi"], "{:.1f}") + "\\%")
                nc(macro_name(rt, stok, "AnchorAboveTau"), e1dg.group(a["above_tau"]))
                nc(macro_name(rt, stok, "AnchorAboveTauUndecided"),
                   e1dg.group(a["above_tau_undecided"]))
                for reading in READINGS:
                    rd = READING_TOKEN[reading]
                    sa = srow(rule, reading, "absolute", "all", st)
                    sm = srow(rule, reading, "marginal", "all", st)
                    nc(macro_name(rt, stok, rd, "Priced"), e1dg.group(sa["priced"]))
                    for s, tok in ((sa, "UnderAbs"), (sm, "UnderMarg")):
                        if s["under_share"] is not None:
                            nc(macro_name(rt, stok, rd, tok), pct(s["under_share"]) + "\\%")
                    if sm["over_share"] is not None:
                        nc(macro_name(rt, stok, rd, "OverMarg"), pct(sm["over_share"]) + "\\%")
        names = [ln[len("\\newcommand{\\"):].split("}", 1)[0] for ln in M
                 if ln.startswith("\\newcommand{\\")]
        if len(names) != len(set(names)):
            refuse("duplicate macro names")
        (ANALYSIS / "N6_macros.tex").write_text("\n".join(M) + "\n", encoding="utf-8")
        print("[n6] macros: {}".format(len(names)))

    print("[n6] COMPLETE: wrote N6_* to {} ({} assertions, {:.1f} s, dispatch {:.1f} s)".format(
        ANALYSIS, check.n, time.time() - t_start, wall_dispatch))
    return 0


if __name__ == "__main__":
    sys.exit(main())
