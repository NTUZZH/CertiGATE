#!/usr/bin/env python
"""N9 (C): the cost of an instruction under optimal execution, bracketed.

WHY THIS EXISTS
---------------
The published V3 class is admitted by the dispatcher's own degradation, the
statistic D-REL2 thresholds, and the certificate's marginal price m is a
difference of two relative gaps.  Neither says what the instruction costs when
the site executes it as well as it can.  This script brackets that cost,

    c = (OPT_c - OPT) / max(OPT, 1 bh)

where OPT is the optimum of the relaxed adjusted instance (the fields the
instruction installs, no dispatch constraint; the oracle of
results/oracle_v1) and OPT_c is the optimum of the same fields with the
instruction's precedence edges, pins, frozen slots and batch visits imposed
(code/l1oracle/cpsat_prec.py).  No gate and no dispatcher computes c.

FOUR LAUNCH QUESTIONS (the project's standing experiment rules)
---------------------------------------------------------------
1. PURPOSE.  c labels (i) the 220 published V3 items, (ii) their 220 benign
   twins, (iii) the 220 held-out V3 items of code/suite/v0.3_heldout and their
   220 twins.  The labels land in the suite section (the share of V3 items that
   cost something under optimal execution), the oracle section (the definition
   of c), the pricing section (each gate's referral rate on the label-defined
   cost-bearing set; |m - c|) and the circularity disclosure.
2. EXPECTED RESULT.  Most published V3 items carry c well above zero, because
   a late predecessor parks a deadline-critical order whatever the schedule;
   their twins carry c = 0 (the edge restates a start order the optimum can
   keep).  The held-out set, drawn without the screen, contains items with
   c = 0, which is what makes it a test of the gates.  If c is near zero on
   most published V3 items, the published class measures dispatcher
   brittleness rather than instruction cost, and the paper says so.
3. CONTAMINATION.  CP-SAT is timed.  The campaign runs on exclusive cores given
   by ``--cores`` with ``--workers`` equal to their number; every solve row
   records the affinity, the load average, cpu_share, solve_cpu_share and
   foreign_share (busy CPU time other processes took on the pinned cores).  A
   budget-limited solve (status FEASIBLE or UNKNOWN) with foreign_share above
   0.10 is marked ``invalid`` (solve_cpu_share below 0.90 is recorded as
   ``low_cpu_share`` and is diagnostic only); invalid rows are
   dropped on resume and solved again, at most twice per key, after which the
   row is kept and carries ``invalid_persistent``.  A proved optimum (OPTIMAL),
   a closed bracket and the rounded-grid lower bound do not depend on the CPU
   received, so they are never invalid.  Outputs go to
   results/n9_instruction_cost/ only (``--smoke`` writes to its smoke/
   subfolder).  results/oracle_v1 is read, never written.
4. DATA ACCURACY.  Instances from the instances_v10 snapshot, every file checked
   against code/scripts/instance_manifest_l1.json (suite_gate loader); the
   published suite's and the held-out file's SHA-256 asserted; every item's
   executed objective recomputed and compared with the suite's stored
   wwt_adjusted (1e-4 bh); the relaxed per-trade brackets reused from
   results/oracle_v1/trade_solves.jsonl only under the same per-trade field
   fingerprint, and every baseline instance's assembled bracket compared with
   results/oracle_v1/brackets.jsonl (1e-6 bh).

DECLARED DESIGN
---------------
THE CONSTRAINED COMPONENTS.  A technician serves one trade, so OPT and OPT_c
both decompose by trade, except that a cross-trade precedence edge couples
its two trades.  The trades that carry a constraint are grouped into
components (``cpsat_prec.trade_components``); every other trade has
OPT_c,t = OPT_t and drops out of the numerator.  Each component is one solve.

THE BRACKET OF c.  For a component k with relaxed per-trade brackets summed to
[L_k, U_k] and constrained bracket [Lc_k, Uc_k]:

    Lc_k = max(CP-SAT bound on the rounded-down constrained grid, L_k)
    Uc_k = min(constrained ATC dispatch on the component, re-timed incumbent)

The ATC schedule enters Uc_k only when it satisfies the model's constraints
(``check_constraints``).  The numerator N = OPT_c - OPT = sum_k (OPT_c,k -
OPT_k) >= 0 lies in

    N_lo = sum_k max(0, Lc_k - U_k),     N_hi = sum_k (Uc_k - L_k),

and OPT lies in [L, U], the whole-instance relaxed bracket.  c = N / max(OPT, 1)
is increasing in N and non-increasing in OPT, so over that box

    c_lo = N_lo / max(U, 1),             c_hi = N_hi / max(L, 1).

This is the conservative reading.  The alternative "(OPT_c_lower - OPT_upper)
/ OPT_lower" is not a valid lower end when the difference is positive, because
dividing a positive difference by the smaller denominator overstates it.  The
interval is always reported; c_mid is the midpoint and is used only where a
statistic needs a point, and every such statistic is also reported at both
ends.

SHORTCUT.  A component whose constrained ATC objective already equals L_k to
1e-9 bh is closed without a solve: OPT_c,k = OPT_k = L_k exactly and the
component adds nothing to N.

RELAXED BRACKETS FOR NEW FIELDS.  A held-out window item moves a release, so
its trade's relaxed bracket may not be on disk.  It is computed here with the
same model and no constraint (the self-check below shows that model reproduces
the oracle's lower ends), with the oracle's rules: lower = max(LB2_t, bound),
upper = min(ATC_t, re-timed incumbent), closed by LB2 when ATC_t equals LB2_t.

STANDING FROZEN SET.  OPT drops the episode's standing frozen set.  Every V3
item and every twin here carries none (asserted), so OPT_c honours exactly the
instruction's own constraints.

WARM START.  The constrained ATC schedule (restricted to the component) is
passed as hints, never as constraints.

SELF-CHECK (``--selfcheck``)
----------------------------
With no constraint, the model's bound on every baseline trade the oracle
solved must equal the oracle's grid optimum to 1e-6 bh where both proved
optimal (the two programs are the same integer program); on every small trade
the oracle closed by LB2, the bound must not exceed the trade's objective; and
the per-instance lower end sum_t max(LB2_t, bound_t) is compared with
results/oracle_v1/brackets.jsonl, with the maximum deviation reported.

Run::

    taskset -c <cores> python code/scripts/n9_instruction_cost.py --run --cores <cores> \\
        --workers <n> [--budget 60] [--limit N]
    ... --census | --selfcheck | --smoke N

Version: l1-n9-instruction-cost-1
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import platform
import socket
import sys
import time
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
CODE = SCRIPTS_DIR.parent
ROOT = CODE.parent
for _p in (str(CODE), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import oracle_cost as oc  # noqa: E402  (helpers only; nothing runs on import)

VERSION = "l1-n9-instruction-cost-1"
OUT_DIR = ROOT / "results" / "n9_instruction_cost"
ORACLE = ROOT / "results" / "oracle_v1"
HELDOUT_PATH = CODE / "suite" / "v0.3_heldout" / "suite_heldout.jsonl"
HELDOUT_MANIFEST = CODE / "suite" / "v0.3_heldout" / "manifest_heldout.json"

DEFAULT_BUDGET_S = 60.0
SMOKE_BUDGET_S = 5.0
SELFCHECK_CLOSED_MAX_ORDERS = 400
SELFCHECK_CLOSED_BUDGET_S = 10.0
FOREIGN_SHARE_MAX = 0.10
CPU_SHARE_MIN = 0.90
MAX_RESOLVES = 2
CLOSE_TOL_BH = 1e-9
CHECK_TOL_BH = 1e-6
ITEM_TOL_BH = 1e-4
FLOOR_BH = 1.0
PROVED = ("OPTIMAL", "CLOSED", "CLOSED_BY_LB2", "INFEASIBLE")
SETS = ("published", "heldout")


# --------------------------------------------------------------------------- #
# Environment                                                                  #
# --------------------------------------------------------------------------- #
_M = {}


def mods():
    if not _M:
        import suite_gate as sg
        from l1adapter import apply as apply_mod, dispatch as dispatch_mod, evaluate
        import importlib
        lb2_mod = importlib.import_module("l1guard.lb2")  # the package exports a function of the same name
        from l1oracle import cpsat_prec as cp

        if Path(sg.INSTANCE_ROOT).resolve() != oc.SNAPSHOT_ROOT.resolve():
            raise SystemExit("REFUSING TO RUN: suite_gate INSTANCE_ROOT={}".format(sg.INSTANCE_ROOT))
        workers = os.environ.get("L1_N9_WORKERS", "8")
        for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
            os.environ[var] = workers
        _M.update(sg=sg, apply=apply_mod, dispatch=dispatch_mod, evaluate=evaluate,
                  lb2=lb2_mod, cp=cp)
    return _M


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def last_rows(path: Path, keyf) -> dict:
    out = {}
    for r in oc.read_jsonl(path):
        out[keyf(r)] = r
    return out


# --------------------------------------------------------------------------- #
# Inputs                                                                       #
# --------------------------------------------------------------------------- #
def load_items(sets) -> list:
    """(set, role) ordered: published V3, published twins, held-out V3, held-out twins."""
    sg = mods()["sg"]
    out = []
    if "published" in sets:
        if oc.sha256_file(sg.SUITE_PATH) != sg.SUITE_SHA256:
            raise SystemExit("REFUSING TO RUN: published suite digest mismatch")
        rows = {r["item_id"]: r for r in oc.read_jsonl(Path(sg.SUITE_PATH))}
        v3 = sorted((r for r in rows.values() if r["primary_class"] == "V3"),
                    key=lambda r: r["item_id"])
        if len(v3) != 220:
            raise SystemExit("published V3 has {} items".format(len(v3)))
        out += [("published", "V3", r) for r in v3]
        out += [("published", "twin", rows[r["twin_id"]]) for r in v3]
    if "heldout" in sets:
        man = json.loads(HELDOUT_MANIFEST.read_text())
        want = man["artifacts"]["suite_heldout.jsonl"]["sha256"]
        if oc.sha256_file(HELDOUT_PATH) != want:
            raise SystemExit("REFUSING TO RUN: held-out file digest != its manifest")
        rows = {r["item_id"]: r for r in oc.read_jsonl(HELDOUT_PATH)}
        v3 = sorted((r for r in rows.values() if r["primary_class"] == "V3"),
                    key=lambda r: r["item_id"])
        out += [("heldout", "V3", r) for r in v3]
        out += [("heldout", "twin", rows[r["twin_id"]]) for r in v3]
    for s, role, r in out:
        if r["episode"]["frozen_seed"]:
            raise SystemExit("{} carries a standing frozen set".format(r["item_id"]))
        if r["episode"]["rule"] != oc.EPISODE_RULE or int(r["episode"]["seed"]) != oc.EPISODE_SEED:
            raise SystemExit("{} declares another episode".format(r["item_id"]))
        if role == "twin" and r["primary_class"] != "benign":
            raise SystemExit("{} is not a benign twin".format(r["item_id"]))
    return out


class Instances:
    """Snapshot instances (manifest-checked), ATC baselines, baseline fields."""

    def __init__(self):
        self.inst, self.base, self.fields, self.stratum = {}, {}, {}, {}

    def get(self, item):
        iid = item["instance"]["instance_id"]
        if iid not in self.inst:
            m = mods()
            path = m["sg"].instance_path(item)  # verifies the digest
            with open(path, encoding="utf-8") as fh:
                inst = json.load(fh)
            if inst["meta"]["id"] != iid:
                raise SystemExit("instance id mismatch {}".format(iid))
            self.inst[iid] = inst
            self.base[iid] = m["dispatch"].dispatch_baseline(inst, oc.EPISODE_RULE,
                                                             seed=oc.EPISODE_SEED)
            self.fields[iid] = {wo["id"]: tuple(wo[f] for f in oc.FIELDS)
                                for wo in inst["work_orders"]}
            self.stratum[iid] = item["instance"]["stratum"]
        return iid


def changed_tuples(base_fields, adjusted_instance) -> list:
    out = []
    for wo in adjusted_instance["work_orders"]:
        cur = tuple(wo[f] for f in oc.FIELDS)
        if cur != base_fields[wo["id"]]:
            out.append((wo["id"],) + cur)
    out.sort(key=lambda t: t[0])
    return out


def trade_fps(instance, tuples) -> dict:
    trade_of = {wo["id"]: wo["trade"] for wo in instance["work_orders"]}
    by = defaultdict(list)
    for t in tuples:
        by[trade_of[t[0]]].append(t)
    trades = sorted({wo["trade"] for wo in instance["work_orders"]})
    return {tr: (oc.fp_of(by[tr]) if by.get(tr) else oc.BASE_FP) for tr in trades}


def oracle_trade_rows() -> dict:
    out = {}
    for r in oc.read_jsonl(ORACLE / "trade_solves.jsonl"):
        k = (r["instance_id"], r["trade"], r["trade_fp"])
        if r.get("contended"):
            out.pop(k, None)
            continue
        out[k] = r
    return out


# --------------------------------------------------------------------------- #
# Units                                                                        #
# --------------------------------------------------------------------------- #
def prepare(item, store: Instances) -> dict:
    """Apply the item's faithful translation; components, keys, ATC, fields."""
    m = mods()
    cp = m["cp"]
    iid = store.get(item)
    inst = store.inst[iid]
    ops = list(item["gold_ops"] or [])
    adj = m["apply"].apply_proposal(inst, {"operations": ops}, frozen_seed=[],
                                    baseline_schedule=store.base[iid], strict_schema=True)
    sched = m["dispatch"].dispatch_adjusted(adj, oc.EPISODE_RULE, oc.EPISODE_SEED)
    obj = m["evaluate"].wwt(adj, sched)
    stored = (item.get("metrics") or {}).get("wwt_adjusted")
    if stored is not None and abs(obj - float(stored)) > ITEM_TOL_BH:
        raise SystemExit("{}: executed objective {} != stored {}".format(item["item_id"], obj, stored))
    tuples = changed_tuples(store.fields[iid], adj.instance)
    tfps = trade_fps(adj.instance, tuples)
    cons = cp.Constraints.from_adjusted(adj)
    comps = []
    atc_t = oc.trade_wwt(adj.instance, sched)
    for trades in cp.trade_components(adj.instance, cons):
        oids = {wo["id"] for wo in adj.instance["work_orders"] if wo["trade"] in trades}
        sub_cons = cons.restrict(oids)
        comp_tuples = [t for t in tuples if t[0] in oids]
        key = sha_text(json.dumps([iid, list(trades), oc.fp_of(comp_tuples), sub_cons.key()]))
        sub_sched = cp.restrict_schedule(sched, oids)
        sub = cp.sub_instance(adj.instance, trades)
        atc_ok = not cp.check_constraints(sub, sub_sched, sub_cons)
        comps.append({"trades": list(trades), "key": key, "n_orders": len(oids),
                      "atc_obj": sum(atc_t.get(t, 0.0) for t in trades), "atc_valid": atc_ok,
                      "n_edges": len(sub_cons.precedence), "n_pins": len(sub_cons.pins),
                      "n_batches": len(sub_cons.batches), "n_frozen": len(sub_cons.frozen),
                      "_cons": sub_cons, "_oids": oids, "_sched": sub_sched})
    return {"item": item, "iid": iid, "adj": adj, "sched": sched, "obj": obj,
            "tuples": tuples, "tfps": tfps, "cons": cons, "comps": comps}


def relaxed_need(unit, oracle_rows, own_rows) -> list:
    """Trades of the instance whose relaxed bracket is on no file yet."""
    need = []
    for tr, tfp in unit["tfps"].items():
        k = (unit["iid"], tr, tfp)
        if k not in oracle_rows and k not in own_rows:
            need.append(tr)
    return need


def relaxed_bracket(unit, oracle_rows, own_rows) -> dict:
    """trade -> (lower, upper, source) for every trade of the relaxed instance."""
    out = {}
    for tr, tfp in unit["tfps"].items():
        k = (unit["iid"], tr, tfp)
        r = oracle_rows.get(k)
        src = "oracle_v1"
        if r is None:
            r = own_rows.get(k)
            src = "n9"
        if r is None:
            return None
        out[tr] = (float(r["lower"]), float(r["upper"]), src)
    return out


# --------------------------------------------------------------------------- #
# Timed solves                                                                 #
# --------------------------------------------------------------------------- #
def timed(fn, cores, workers):
    b0 = oc.core_busy_s(cores)
    la0 = oc.loadavg()
    t0, c0 = time.perf_counter(), time.process_time()
    res = fn()
    wall = time.perf_counter() - t0
    cpu = time.process_time() - c0
    foreign = max(0.0, (oc.core_busy_s(cores) - b0) - cpu)
    meta = {"wall_s": wall, "cpu_s": cpu,
            "cpu_share": cpu / (wall * workers) if wall > 0 else None,
            "foreign_cpu_s": foreign,
            "foreign_share": foreign / (wall * len(cores)) if wall > 0 else None,
            "affinity": sorted(os.sched_getaffinity(0)), "load_avg_start": la0,
            "load_avg_end": oc.loadavg(), "workers": workers,
            "omp_num_threads": os.environ.get("OMP_NUM_THREADS")}
    return res, meta


def validity(row) -> None:
    st = row["status"]
    if st in PROVED:
        row["invalid"] = False
        return
    scs = row.get("solve_cpu_share")
    fs = row.get("foreign_share")
    # Validity rests on contention alone. CP-SAT's own search workers idle
    # part of the time on a large component (solve_cpu_share near 0.7 with no
    # foreign load is normal), so the recorded solve_cpu_share is kept as a
    # diagnostic and does not invalidate a budget-limited solve by itself.
    row["invalid"] = bool(fs is not None and fs > FOREIGN_SHARE_MAX)
    row["low_cpu_share"] = bool(scs is not None and scs < CPU_SHARE_MIN)


def solve_constrained(unit, comp, relaxed, args, cores) -> dict:
    m = mods()
    cp = m["cp"]
    L_k = sum(relaxed[t][0] for t in comp["trades"])
    U_k = sum(relaxed[t][1] for t in comp["trades"])
    row = OrderedDict(kind="constrained", key=comp["key"], instance_id=unit["iid"],
                      trades=comp["trades"], n_orders=comp["n_orders"],
                      n_edges=comp["n_edges"], n_pins=comp["n_pins"],
                      n_batches=comp["n_batches"], n_frozen=comp["n_frozen"],
                      relaxed_lower=L_k, relaxed_upper=U_k, atc_obj=comp["atc_obj"],
                      atc_valid=comp["atc_valid"], budget_s=args.budget, version=VERSION)
    if comp["atc_valid"] and comp["atc_obj"] <= L_k + CLOSE_TOL_BH:
        row.update(status="CLOSED", bound=None, incumbent=None, grid_obj=None,
                   lower=L_k, upper=comp["atc_obj"], upper_source="atc", wall_s=0.0,
                   cpu_s=0.0, cpu_share=None, solve_wall_s=0.0, solve_cpu_share=None,
                   foreign_share=None, affinity=sorted(os.sched_getaffinity(0)),
                   load_avg_start=oc.loadavg(), workers=args.workers)
        validity(row)
        return row
    sub = cp.sub_instance(unit["adj"].instance, comp["trades"])
    res, meta = timed(lambda: cp.solve(sub, comp["_cons"], time_limit_s=args.budget,
                                       workers=args.workers, warm_start=comp["_sched"]),
                      cores, args.workers)
    inc = res["incumbent_obj_bh"]
    if res["schedule"] is not None:
        val = m["evaluate"].validate(sub, res["schedule"])
        bad = cp.check_constraints(sub, res["schedule"], comp["_cons"])
        if not val["feasible"] or bad:
            raise SystemExit("re-timed incumbent infeasible on {}: {} {}".format(
                comp["key"][:12], val["violations"][:3], bad[:3]))
    bound = res["bound_bh"]
    if bound == float("inf"):
        raise SystemExit("constrained model infeasible on {} ({})".format(unit["item"]["item_id"],
                                                                          comp["trades"]))
    lower = max(bound, L_k)
    ups = []
    if comp["atc_valid"]:
        ups.append((comp["atc_obj"], "atc"))
    if inc is not None:
        ups.append((inc, "cpsat"))
    if not ups:
        raise SystemExit("no feasible constrained schedule for {}".format(unit["item"]["item_id"]))
    upper, src = min(ups)
    if lower > upper + CHECK_TOL_BH:
        raise SystemExit("BRACKET VIOLATION {} lower {} upper {}".format(comp["key"][:12], lower, upper))
    row.update(status=res["status"], bound=bound, incumbent=inc, grid_obj=res["grid_obj_bh"],
               lower=lower, upper=upper, upper_source=src, retime_failed=res["retime_failed"],
               build_s=res["build_s"], solve_wall_s=res["solve_wall_s"],
               solve_cpu_s=res["solve_cpu_s"],
               solve_cpu_share=(res["solve_cpu_s"] / (res["solve_wall_s"] * args.workers)
                                if res["solve_wall_s"] > 0 else None),
               horizon_centi=res["horizon_centi"], n_symmetry_rows=res["n_symmetry_rows"],
               **meta)
    validity(row)
    return row


def solve_relaxed_trade(unit, trade, args, cores, force=False) -> dict:
    """The oracle's per-trade bracket, computed with the new model and no constraint."""
    m = mods()
    cp = m["cp"]
    relaxed = unit["adj"].instance
    atc = m["dispatch"].dispatch_baseline(relaxed, oc.EPISODE_RULE, seed=oc.EPISODE_SEED)
    lbd = m["lb2"].lb2_detail(relaxed)["per_trade"]
    lb_t = lbd.get(trade, {}).get("bound", 0.0)
    sub = cp.sub_instance(relaxed, (trade,))
    ids = {wo["id"] for wo in sub["work_orders"]}
    atc_sub = cp.restrict_schedule(atc, ids)
    atc_t = m["evaluate"].wwt(sub, atc_sub)
    row = OrderedDict(kind="relaxed", instance_id=unit["iid"], trade=trade,
                      trade_fp=unit["tfps"][trade], n_orders=len(ids), lb2_trade=lb_t,
                      atc_trade_obj=atc_t, budget_s=args.budget, version=VERSION)
    if not force and atc_t <= lb_t + CLOSE_TOL_BH:
        row.update(status="CLOSED_BY_LB2", bound=None, incumbent=None, lower=lb_t, upper=atc_t,
                   upper_source="atc", wall_s=0.0, cpu_share=None, solve_cpu_share=None,
                   foreign_share=None, affinity=sorted(os.sched_getaffinity(0)),
                   load_avg_start=oc.loadavg(), workers=args.workers)
        validity(row)
        return row
    res, meta = timed(lambda: cp.solve(sub, cp.Constraints(), time_limit_s=args.budget,
                                       workers=args.workers, warm_start=atc_sub),
                      cores, args.workers)
    inc = res["incumbent_obj_bh"]
    if res["schedule"] is not None:
        val = m["evaluate"].validate(sub, res["schedule"])
        if not val["feasible"]:
            raise SystemExit("re-timed relaxed incumbent infeasible on {}".format(sub["meta"]["id"]))
    bound = res["bound_bh"] if res["bound_bh"] is not None else 0.0
    lower = max(lb_t, bound)
    upper, src = (inc, "cpsat") if inc is not None and inc < atc_t else (atc_t, "atc")
    if lower > upper + CHECK_TOL_BH:
        raise SystemExit("BRACKET VIOLATION relaxed {} {}".format(sub["meta"]["id"], (lower, upper)))
    row.update(status=res["status"], bound=bound, incumbent=inc, grid_obj=res["grid_obj_bh"],
               lower=lower, upper=upper, upper_source=src, build_s=res["build_s"],
               solve_wall_s=res["solve_wall_s"], solve_cpu_s=res["solve_cpu_s"],
               solve_cpu_share=(res["solve_cpu_s"] / (res["solve_wall_s"] * args.workers)
                                if res["solve_wall_s"] > 0 else None), **meta)
    validity(row)
    return row


# --------------------------------------------------------------------------- #
# Brackets                                                                     #
# --------------------------------------------------------------------------- #
def gfun(obj, x):
    v = (float(obj) - float(x)) / max(float(x), FLOOR_BH)
    return v if v > 0.0 else 0.0


def assemble(unit, set_name, role, relaxed, comp_rows) -> dict:
    item = unit["item"]
    L = sum(v[0] for v in relaxed.values())
    U = sum(v[1] for v in relaxed.values())
    comps, n_lo, n_hi, complete = [], 0.0, 0.0, True
    shares, foreign, statuses = [], [], []
    for comp in unit["comps"]:
        r = comp_rows.get(comp["key"])
        L_k = sum(relaxed[t][0] for t in comp["trades"])
        U_k = sum(relaxed[t][1] for t in comp["trades"])
        if r is None:
            complete = False
            comps.append({"trades": comp["trades"], "key": comp["key"], "status": None})
            continue
        lc, uc = max(float(r["lower"]), L_k), float(r["upper"])
        n_lo += max(0.0, lc - U_k)
        n_hi += uc - L_k
        statuses.append(r["status"])
        if r.get("solve_cpu_share") is not None:
            shares.append(r["solve_cpu_share"])
        if r.get("foreign_share") is not None:
            foreign.append(r["foreign_share"])
        comps.append({"trades": comp["trades"], "key": comp["key"], "status": r["status"],
                      "n_orders": comp["n_orders"], "n_edges": comp["n_edges"],
                      "lc": lc, "uc": uc, "relaxed_lower": L_k, "relaxed_upper": U_k,
                      "atc_obj": comp["atc_obj"], "atc_valid": comp["atc_valid"],
                      "invalid": bool(r.get("invalid")),
                      "invalid_persistent": bool(r.get("invalid_persistent"))})
    out = OrderedDict(
        item_id=item["item_id"], set=set_name, role=role, primary_class=item["primary_class"],
        family_id=item["family_id"], twin_id=item["twin_id"], instance_id=unit["iid"],
        stratum=item["instance"]["stratum"],
        field_changing=bool(unit["tuples"]), fingerprint=oc.fp_of(unit["tuples"]),
        n_changed_orders=len(unit["tuples"]), obj=unit["obj"],
        badness=item.get("badness"),
        badness_relative=(item.get("metrics") or {}).get("badness_relative"),
        opt_lower=L, opt_upper=U, n_components=len(unit["comps"]),
        trades_per_component=[len(c["trades"]) for c in unit["comps"]],
        components=comps, complete=complete,
        relaxed_sources=dict(Counter(v[2] for v in relaxed.values())),
        g_lo=gfun(unit["obj"], U), g_hi=gfun(unit["obj"], L),
        n_lo=n_lo if complete else None, n_hi=n_hi if complete else None,
        c_lo=(n_lo / max(U, FLOOR_BH)) if complete else None,
        c_hi=(n_hi / max(L, FLOOR_BH)) if complete else None,
        statuses=statuses, min_solve_cpu_share=min(shares) if shares else None,
        max_foreign_share=max(foreign) if foreign else None,
        affinity=sorted(os.sched_getaffinity(0)), load_avg=oc.loadavg(), version=VERSION)
    if complete:
        out["c_mid"] = 0.5 * (out["c_lo"] + out["c_hi"])
        if out["c_lo"] > out["c_hi"] + 1e-12:
            raise SystemExit("c bracket inverted on {}".format(item["item_id"]))
    return out


# --------------------------------------------------------------------------- #
# Driver                                                                       #
# --------------------------------------------------------------------------- #
def load_own(out_dir: Path):
    """Own solve rows, last per key, invalid rows dropped (counted per key)."""
    con, rel, drops = {}, {}, Counter()
    for r in oc.read_jsonl(out_dir / "solves.jsonl"):
        if r["kind"] == "constrained":
            k, dest = r["key"], con
        else:
            k, dest = (r["instance_id"], r["trade"], r["trade_fp"]), rel
        if r.get("invalid") and not r.get("invalid_persistent"):
            drops[k] += 1
            dest.pop(k, None)
            continue
        dest[k] = r
    return con, rel, drops


def census(units, oracle_rows, args) -> dict:
    by_set = Counter()
    keys = {}
    closed_keys = set()
    rel_need = set()
    for (s, role, _), u in units:
        rel = relaxed_bracket(u, oracle_rows, {})
        for tr in relaxed_need(u, oracle_rows, {}):
            rel_need.add((u["iid"], tr, u["tfps"][tr]))
        for comp in u["comps"]:
            keys.setdefault(comp["key"], comp)
            if rel is not None:
                L_k = sum(rel[t][0] for t in comp["trades"])
                if comp["atc_valid"] and comp["atc_obj"] <= L_k + CLOSE_TOL_BH:
                    closed_keys.add(comp["key"])
        by_set["{}:{}".format(s, role)] += 1
    open_keys = [k for k in keys if k not in closed_keys]
    sizes = Counter()
    tpc = Counter()
    est = 0.0
    buckets = ((150, 0.5), (400, 3.0), (700, 15.0), (1500, 45.0))
    for k in open_keys:
        n = keys[k]["n_orders"]
        tpc[len(keys[k]["trades"])] += 1
        for cap_n, sec in buckets:
            if n <= cap_n:
                sizes["<={}".format(cap_n)] += 1
                est += min(sec, args.budget)
                break
        else:
            sizes[">1500"] += 1
            est += args.budget
    return {"items": dict(by_set), "distinct_components": len(keys),
            "components_closed_without_solve": len(closed_keys),
            "constrained_solves": len(open_keys),
            "trades_per_solve": dict(sorted(tpc.items())),
            "solves_by_component_orders": dict(sorted(sizes.items())),
            "relaxed_trades_to_solve": len(rel_need),
            "cap_wall_h": (len(open_keys) + len(rel_need)) * args.budget / 3600.0,
            "est_wall_h_by_size": est / 3600.0,
            "items_with_relaxed_gaps": sum(1 for (_, _, _), u in units
                                           if relaxed_need(u, oracle_rows, {}))}


def run(args, out_dir: Path, units, oracle_rows, cores):
    out_dir.mkdir(parents=True, exist_ok=True)
    solves_path = out_dir / "solves.jsonl"
    br_path = out_dir / "brackets.jsonl"
    con, rel, drops = load_own(out_dir)
    done = {r["item_id"] for r in oc.read_jsonl(br_path) if r.get("complete")}
    t_run = time.perf_counter()
    n_done = 0
    for (s, role, item), u in units:
        if item["item_id"] in done:
            continue
        for tr in relaxed_need(u, oracle_rows, rel):
            k = (u["iid"], tr, u["tfps"][tr])
            row = solve_relaxed_trade(u, tr, args, cores)
            if row["invalid"] and drops[k] >= MAX_RESOLVES:
                row["invalid_persistent"] = True
            oc.append_jsonl(solves_path, row)
            if not row["invalid"] or row.get("invalid_persistent"):
                rel[k] = row
        relaxed = relaxed_bracket(u, oracle_rows, rel)
        if relaxed is None:
            print("[n9] {} relaxed bracket incomplete (invalid solve); left for resume"
                  .format(item["item_id"]))
            continue
        for comp in u["comps"]:
            if comp["key"] in con:
                continue
            row = solve_constrained(u, comp, relaxed, args, cores)
            if row["invalid"] and drops[comp["key"]] >= MAX_RESOLVES:
                row["invalid_persistent"] = True
            oc.append_jsonl(solves_path, row)
            if not row["invalid"] or row.get("invalid_persistent"):
                con[comp["key"]] = row
            print("[n9]   {} {} orders={} edges={} status={} lower={:.4f} upper={:.4f} "
                  "wall={:.1f}s cpu_share={} foreign={}".format(
                      item["item_id"], "+".join(comp["trades"]), comp["n_orders"],
                      comp["n_edges"], row["status"], row["lower"], row["upper"],
                      row.get("wall_s") or 0.0,
                      None if row.get("solve_cpu_share") is None else round(row["solve_cpu_share"], 3),
                      None if row.get("foreign_share") is None else round(row["foreign_share"], 3)),
                  flush=True)
        b = assemble(u, s, role, relaxed, con)
        oc.append_jsonl(br_path, b)
        n_done += 1
        print("[n9] {} {}/{} {} c=[{}, {}] complete={} elapsed={:.0f}s".format(
            n_done, s, role, item["item_id"],
            None if b["c_lo"] is None else round(b["c_lo"], 5),
            None if b["c_hi"] is None else round(b["c_hi"], 5), b["complete"],
            time.perf_counter() - t_run), flush=True)
        if args.limit and n_done >= args.limit:
            break
    return n_done, time.perf_counter() - t_run


def check_baselines(store, oracle_rows):
    """Assembled baseline brackets equal results/oracle_v1/brackets.jsonl."""
    br = last_rows(ORACLE / "brackets.jsonl", lambda r: (r["instance_id"], r["fingerprint"]))
    worst = 0.0
    for iid, inst in store.inst.items():
        b = br[(iid, oc.BASE_FP)]
        trades = sorted({wo["trade"] for wo in inst["work_orders"]})
        L = sum(float(oracle_rows[(iid, t, oc.BASE_FP)]["lower"]) for t in trades)
        U = sum(float(oracle_rows[(iid, t, oc.BASE_FP)]["upper"]) for t in trades)
        dev = max(abs(L - b["lower"]), abs(U - b["upper"]))
        worst = max(worst, dev)
        if dev > CHECK_TOL_BH:
            raise SystemExit("baseline bracket of {} does not reassemble: {}".format(iid, dev))
    return worst


def run_meta(args, extra) -> dict:
    m = mods()
    return {"version": VERSION,
            "started": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "host": socket.gethostname(), "python": sys.version.split()[0],
            "platform": platform.platform(), "ortools": __import__("ortools").__version__,
            "cpsat_prec_sha256": oc.sha256_file(m["cp"].__file__),
            "published_suite_sha256": m["sg"].SUITE_SHA256,
            "heldout_sha256": oc.sha256_file(HELDOUT_PATH) if HELDOUT_PATH.is_file() else None,
            "oracle_trade_solves_sha256": oc.sha256_file(ORACLE / "trade_solves.jsonl"),
            "instance_manifest_sha256": oc.sha256_file(m["sg"].INSTANCE_MANIFEST_PATH),
            "affinity": sorted(os.sched_getaffinity(0)),
            "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
            "load_avg": oc.loadavg(), "args": {k: v for k, v in vars(args).items()
                                               if k != "cores_t"},
            "foreign_processes_on_cores_at_start": oc.foreign_on_cores(set(args.cores_t)),
            **extra}


def build_units(args):
    items = load_items(args.sets)
    store = Instances()
    t0 = time.perf_counter()
    units = []
    for s, role, item in items:
        units.append(((s, role, item), prepare(item, store)))
    print("[n9] {} items prepared on {} instances ({:.1f}s)".format(
        len(units), len(store.inst), time.perf_counter() - t0), flush=True)
    return store, units


def smoke_selection(units, n):
    """n items, round-robin over (set, role, family), deterministic."""
    lanes = OrderedDict()
    for x in units:
        (s, role, item), _u = x
        lanes.setdefault((s, role, item["family_id"]), []).append(x)
    out = []
    while len(out) < n and any(lanes.values()):
        for k in list(lanes):
            if lanes[k] and len(out) < n:
                out.append(lanes[k].pop(0))
    return out


def cmd_selfcheck(args, cores):
    m = mods()
    cp = m["cp"]
    oracle_rows = oracle_trade_rows()
    items = load_items(["published"])
    store = Instances()
    for _s, _r, item in items:
        store.get(item)
    sg = m["sg"]
    for r in oc.read_jsonl(Path(sg.SUITE_PATH)):
        store.get(r)
    if len(store.inst) != 60:
        raise SystemExit("expected 60 baseline instances, got {}".format(len(store.inst)))
    worst_assembly = check_baselines(store, oracle_rows)
    br = last_rows(ORACLE / "brackets.jsonl", lambda r: (r["instance_id"], r["fingerprint"]))
    out_path = OUT_DIR / "selfcheck.jsonl"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    max_dev_proved, max_dev_all, n_proved_pairs = 0.0, 0.0, 0
    fails = []
    t0 = time.perf_counter()
    for iid in sorted(store.inst):
        inst = store.inst[iid]
        atc = store.base[iid]
        trades = sorted({wo["trade"] for wo in inst["work_orders"]})
        lower_mine = 0.0
        for tr in trades:
            orow = oracle_rows[(iid, tr, oc.BASE_FP)]
            sub = cp.sub_instance(inst, (tr,))
            ids = {wo["id"] for wo in sub["work_orders"]}
            closed = orow["status"] == "CLOSED_BY_LB2"
            if closed and len(ids) > SELFCHECK_CLOSED_MAX_ORDERS:
                lower_mine += float(orow["lower"])
                continue
            budget = SELFCHECK_CLOSED_BUDGET_S if closed else args.budget
            res, meta = timed(lambda: cp.solve(sub, cp.Constraints(), time_limit_s=budget,
                                               workers=args.workers,
                                               warm_start=cp.restrict_schedule(atc, ids)),
                              cores, args.workers)
            lb_t = float(orow["lb2_trade"])
            my_lower = max(lb_t, res["bound_bh"] or 0.0)
            lower_mine += my_lower
            row = {"instance_id": iid, "trade": tr, "n_orders": len(ids),
                   "oracle_status": orow["status"], "oracle_cp_bound": orow.get("cp_bound"),
                   "oracle_lower": orow["lower"], "oracle_upper": orow["upper"],
                   "status": res["status"], "bound": res["bound_bh"],
                   "grid_obj": res["grid_obj_bh"], "incumbent": res["incumbent_obj_bh"],
                   "lower": my_lower, "budget_s": budget,
                   "solve_cpu_share": (res["solve_cpu_s"] / (res["solve_wall_s"] * args.workers)
                                       if res["solve_wall_s"] > 0 else None), **meta}
            if res["bound_bh"] is not None and res["bound_bh"] > float(orow["upper"]) + CHECK_TOL_BH:
                fails.append(("bound above the oracle's upper end", iid, tr))
            if closed:
                if res["bound_bh"] is not None and res["bound_bh"] > float(orow["upper"]) + CHECK_TOL_BH:
                    fails.append(("closed trade bound above its objective", iid, tr))
            elif orow["status"] == "OPTIMAL" and res["status"] == "OPTIMAL":
                dev = abs(res["bound_bh"] - float(orow["cp_bound"]))
                row["dev_grid_optimum"] = dev
                max_dev_proved = max(max_dev_proved, dev)
                n_proved_pairs += 1
                if dev > CHECK_TOL_BH:
                    fails.append(("grid optimum differs by {}".format(dev), iid, tr))
            rows.append(row)
            oc.append_jsonl(out_path, row)
        b = br[(iid, oc.BASE_FP)]
        dev_i = lower_mine - float(b["lower"])
        max_dev_all = max(max_dev_all, abs(dev_i))
        print("[n9 selfcheck] {} lower mine={:.6f} oracle={:.6f} dev={:+.2e} elapsed={:.0f}s".format(
            iid, lower_mine, float(b["lower"]), dev_i, time.perf_counter() - t0), flush=True)
        oc.append_jsonl(out_path, {"instance_id": iid, "summary": True, "lower_mine": lower_mine,
                                   "lower_oracle": b["lower"], "upper_oracle": b["upper"],
                                   "dev": dev_i})
        if lower_mine > float(b["upper"]) + CHECK_TOL_BH:
            fails.append(("instance lower above the oracle's upper end", iid, None))
    summary = {"instances": len(store.inst), "trades_solved": len(rows),
               "proved_pairs_compared": n_proved_pairs,
               "max_dev_grid_optimum_proved_bh": max_dev_proved,
               "max_abs_dev_instance_lower_bh": max_dev_all,
               "baseline_reassembly_max_dev_bh": worst_assembly,
               "grid_resolution_bh": 0.01, "failures": fails,
               "wall_s": time.perf_counter() - t0, "workers": args.workers,
               "affinity": sorted(os.sched_getaffinity(0))}
    (OUT_DIR / "selfcheck_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    if fails:
        raise SystemExit("SELFCHECK FAILED: {}".format(fails[:5]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--run", action="store_true")
    g.add_argument("--census", action="store_true")
    g.add_argument("--selfcheck", action="store_true")
    g.add_argument("--smoke", type=int, default=0, metavar="N")
    ap.add_argument("--cores", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--budget", type=float, default=None, help="seconds per solve")
    ap.add_argument("--limit", type=int, default=0, help="items to complete this call")
    ap.add_argument("--sets", default="published,heldout")
    args = ap.parse_args()
    args.sets = [s for s in args.sets.split(",") if s]
    if any(s not in SETS for s in args.sets):
        raise SystemExit("unknown set in {}".format(args.sets))
    args.cores_t = oc.parse_cores(args.cores)
    if len(args.cores_t) != args.workers:
        raise SystemExit("REFUSING TO RUN: {} workers on {} cores".format(args.workers,
                                                                         len(args.cores_t)))
    if args.budget is None:
        args.budget = SMOKE_BUDGET_S if args.smoke else DEFAULT_BUDGET_S
    os.environ["L1_N9_WORKERS"] = str(args.workers)
    oc.setup_environment(args.cores_t, args.workers)
    cores = list(args.cores_t)
    if args.selfcheck:
        return cmd_selfcheck(args, cores)
    store, units = build_units(args)
    oracle_rows = oracle_trade_rows()
    worst = check_baselines(store, oracle_rows)
    summ = census(units, oracle_rows, args)
    summ["baseline_reassembly_max_dev_bh"] = worst
    print(json.dumps(summ, indent=2), flush=True)
    if args.census:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "census.json").write_text(json.dumps(summ, indent=2) + "\n")
        return 0
    out_dir = OUT_DIR / "smoke" if args.smoke else OUT_DIR
    if args.smoke:
        units = smoke_selection(units, args.smoke)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = run_meta(args, {"census": summ})
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    oc.append_jsonl(out_dir / "run_meta_history.jsonl", meta)
    if meta["foreign_processes_on_cores_at_start"]:
        print("[n9] WARNING: other processes on our cores: {}".format(
            meta["foreign_processes_on_cores_at_start"]))
    n, wall = run(args, out_dir, units, oracle_rows, cores)
    print("[n9] finished: {} items in {:.1f}s".format(n, wall))
    return 0


if __name__ == "__main__":
    sys.exit(main())
