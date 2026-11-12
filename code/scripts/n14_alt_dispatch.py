#!/usr/bin/env python
"""N14: the decision-time direct benchmark with the site's dispatcher replaced.

QUESTION
--------
At the decision instant the site's ATC dispatcher leaves a zero anchor gap on
almost every known board (1,670 of 1,723 issuable items in N11), so every gate
design prices almost exactly and the decision-time comparison cannot separate
them.  N6 showed, on the full window only, that under dispatching rules far
from the optimum the hand-written rule D-REL2 under-prices the absolute cost
while the certificate does not.  N14 repeats N11's decision-time direct
benchmark with the dispatcher replaced by WSPT, PFIFO (first in first out
within priority class) and EDD, everything else as N11: the same issuable
items, the same decision instant t_d, the same running-work rule, the same
canonical proposals, the same thresholds (tau = 0.20, D-REL1 0.02, D-REL2
0.02, D-ABS 0.8119 bh), the realised outcome executed by the same replaced
dispatcher, damage on the original fields.  ATC runs through the same code
path as the control and must reproduce N11 (assertion group R7 and R10).
The design is the pre-specified design.

READINGS (as N11 Stage 3)
-------------------------
K   the known board at t_d (N11's census board), dispatched by rule R
FI  the full window minus the orders completed by t_d (the full-information
    gate, the control), dispatched by R from t_d
P0  the full window at t = 0 under R (the full-window calibration; extra)

WHAT CHANGES WITH THE RULE R, AND WHAT DOES NOT
-----------------------------------------------
Changes: the baseline and the trajectory up to t_d (so the running, completed
and queued sets at t_d), the slots a ``freeze`` pins, every dispatch of K, FI
and the full instance from t_d, the D-REL2 reference dispatch, the realised
run and its no-proposal anchor.  Unchanged: the items and their t_d (N11's
census rows), the operations, the thresholds, the certificate's bound, the
decision-time oracle of a board (the optimum of the board's relaxed known
orders; dispatcher-free), the full-window oracle brackets (results/oracle_v1).

HOW THE DISPATCHER IS REPLACED
------------------------------
Every dispatch inside N11's ``gen_price`` and N8's ``trajectory`` reads the
rule from ``l1guard.config.G_CERT`` at call time.  ``site_rule(R)`` rebinds
that object to ``G_CERT.with_(rule=R)`` for the duration of a site's
computation and restores it on exit; nothing on disk is edited.  The
oracle's upper-end heuristic (``board_atc``) stays ATC, because the oracle of
a board does not depend on the site's dispatcher.  A wrapper on
``l1adapter.dispatch.dispatch_adjusted`` counts the rule of every dispatch;
assertion group R3 proves that every site dispatch used R and every board
dispatch used ATC.

PFIFO keeps the arrival order at the dispatch origin.  The rule picks the
lowest priority class and, within a class, the earliest release.  At t_d N11
raises every queued order's release to t_d (the dispatch origin,
``n8.raise_releases``); for ATC, EDD and WSPT this changes no pick, because
none of them reads the release, but for PFIFO it would replace the arrival
order of the queue by the order of the identifiers.  N14 therefore runs N6's
``pfifo`` pick with the release recorded before the raise (``pfifo_arrival``,
registered in memory in ``fmwos.pdrs``).  On every dispatch where nothing is
raised (the baseline, the trajectory, every t = 0 run) it is N6's ``pfifo``
exactly (asserted on every instance, R1).

THE ORACLE ON THE KNOWN BOARD
-----------------------------
A board is N11's (``board_record``).  Its trades are keyed by their content
(the trade's orders with their board fields, its technicians with their
availability, and t_d).  A trade whose content equals a trade of an N11 board
reuses N11's bracket; a trade LB2 closes needs no solve; every other trade is
solved once (N11's ``solve_relaxed``: cpsat_avail, 60 s, 4 workers, cores 8-11
exclusively), with the timing record and the foreign_share > 0.10 validity
rule of N11 (re-solved at most twice).

SUBCOMMANDS
-----------
census   deterministic (cores 8-11, 4 workers): every rule's site, prices on
         K, FI and P0, the realised runs, the boards; assertions R0-R8
oracle   CP-SAT on cores 8-11 EXCLUSIVELY: the open trades not covered by N11
analyse  rows, the twin of tab:decision per rule, the anchor gap of the known
         board per rule, pricing error against the known-board optimum,
         macros, summary; assertions R9-R10

Version: l1-n14-alt-dispatch-1
"""

from __future__ import annotations

import os
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import n11_decision_time as D  # noqa: E402  (sets L1_INSTANCE_ROOT to the snapshot)

import argparse  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import platform  # noqa: E402
import socket  # noqa: E402
import subprocess  # noqa: E402
import time  # noqa: E402
from collections import Counter, OrderedDict, defaultdict  # noqa: E402
from contextlib import contextmanager  # noqa: E402
from pathlib import Path  # noqa: E402

VERSION = "l1-n14-alt-dispatch-1"
ROOT = D.ROOT
RESULTS = D.RESULTS
ANALYSIS = D.ANALYSIS
OUT = RESULTS / "n14_altdispatch"
N11_ITEMS = D.OUT / "items.jsonl"
N11_BOARDS = D.OUT / "boards.jsonl"
N11_CENSUS_META = D.OUT / "census_meta.json"
N11_CENSUS_ASSERT = D.OUT / "census_assertions.json"
N11_SOLVES = D.ORACLE_OUT / "trade_solves.jsonl"
N11_BRACKETS = D.ORACLE_OUT / "brackets.jsonl"
N11F_DIR = RESULTS / "n11_forecast"
N11F_FULLINFO = N11F_DIR / "fullinfo_direct.jsonl"
N11F_ANCHORS = N11F_DIR / "anchors_direct.jsonl"
N11F_ASSERT = N11F_DIR / "direct_assertions.json"
N11F_CONSEQUENCE = ANALYSIS / "N11F_consequence.csv"
N11_PRICING = ANALYSIS / "N11_pricing.csv"
N11_WINS = ANALYSIS / "N11_wins.csv"
N6_ANCHOR = ANALYSIS / "N6_anchor_gap_by_rule.csv"

RULES = ("atc", "wspt", "pfifo", "edd")
CONTROL = "atc"
RULE_IMPL = {"atc": "atc", "wspt": "wspt", "pfifo": "pfifo_arrival", "edd": "edd"}
RULE_N6 = {"atc": "atc", "wspt": "wspt", "pfifo": "pfifo", "edd": "edd"}
RULE_LABEL = OrderedDict([
    ("atc", "ATC, k = 2 (the site's dispatcher, control)"),
    ("wspt", "Weighted shortest processing time"),
    ("pfifo", "Priority class, then first in first out"),
    ("edd", "Earliest due date")])
RULE_TOKEN = {"atc": "Atc", "wspt": "Wspt", "pfifo": "Pfifo", "edd": "Edd"}
READINGS = ("K", "FI", "P0")
READING_TOKEN = {"K": "Known", "FI": "FullInfo", "P0": "FullWindow"}
READING_NAME = {"K": "known board", "FI": "full information", "P0": "full window at t = 0"}
CORES = (8, 9, 10, 11)
SEED = 0
TOL = 1e-6
EXACT = 1e-9
CSV_TOL = 1.5e-6
EXPECT_ISSUABLE = 1723
EXPECT_N11_ZERO_GAP = (1670, 1723)
EMPTY_RAW = D.EMPTY_RAW

#: Fields of N11's census rows that the ATC control must reproduce (R7).
R7_FIELDS = (
    "t_d", "t_known", "t_start", "issuable", "issuable_strict", "n_ref", "ref_all_pm",
    "om_term_cert", "om_stage_cert", "om_term_feas", "om_stage_feas", "om_codes", "om_obj",
    "om_obj_orig", "om_lb", "om_lb_running", "om_gap", "om_ref2", "om_ref2_from",
    "om_constraining", "om_n_raised", "om_parse_ok", "om_infra", "om_fp",
    "n_known", "n_queue", "n_scheduled", "n_in_progress", "n_completed", "n_unknown",
    "ref_completed", "ref_running", "ref_unknown", "n_batch_members", "n_batch_members_known",
    "names_unknown", "names_completed", "names_running", "seed_not_frozen_on_K",
    "dt_term_cert", "dt_stage_cert", "dt_term_feas", "dt_stage_feas", "dt_codes", "dt_obj",
    "dt_obj_orig", "dt_lb", "dt_lb_running", "dt_gap", "dt_ref2", "dt_ref2_from",
    "dt_constraining", "dt_n_raised", "dt_parse_ok", "dt_infra", "dt_fp", "dt_n_changed",
    "an_obj", "an_obj_orig", "an_lb", "an_gap", "an_lb_running", "an_term", "rconst",
    "n_running", "rw0_obj", "rw0_obj_orig", "rw0_term")
R7_RW_FIELDS = ("rw_term", "rw_term_feas", "rw_obj", "rw_obj_orig")
#: Fields where a running-work refusal may legitimately differ from N11's Stage 2 rows.
R7_RUNNING_RULE_FIELDS = ("dt_term_cert", "dt_stage_cert", "dt_term_feas", "dt_stage_feas",
                          "dt_codes")

F = None  # n11_forecast, imported lazily (it is only needed for its analysis helpers)


def _F():
    global F
    if F is None:
        import n11_forecast as _f
        F = _f
    return F


# --------------------------------------------------------------------------- #
# The site's dispatcher                                                        #
# --------------------------------------------------------------------------- #
#: order id -> release before the dispatch-origin raise, inside one priced call.
_ARRIVAL: dict = {}
#: rule -> number of adjusted dispatches since the last reset (assertion R3).
AUDIT: Counter = Counter()
_ORIG = {}


def _pick_pfifo_arrival(queue, t, rng):
    """N6's ``pfifo`` with the release recorded before the dispatch-origin raise."""
    return min(queue, key=lambda j: (j["priority"], _ARRIVAL.get(j["id"], j["release_bh"]),
                                     j["id"]))


def install() -> None:
    """Register ``pfifo_arrival`` in memory and wrap the adjusted dispatcher (idempotent)."""
    from l1adapter import dispatch as dm
    from l1adapter._fmwos import pdrs
    import n8_causal as n8

    cur = pdrs._RULES.get("pfifo_arrival")
    if cur is None:
        pdrs._RULES["pfifo_arrival"] = _pick_pfifo_arrival
    elif cur is not _pick_pfifo_arrival:
        raise SystemExit("REFUSING TO RUN: another pfifo_arrival is registered")
    if not getattr(dm.dispatch_adjusted, "_n14_audit", False):
        orig = dm.dispatch_adjusted

        def dispatch_adjusted(adjusted, rule="atc", seed=0):
            AUDIT[rule] += 1
            return orig(adjusted, rule, seed)

        dispatch_adjusted._n14_audit = True
        dm.dispatch_adjusted = dispatch_adjusted
    _ORIG.setdefault("raise", n8.raise_releases)


def _raise_recording(adjusted, t_d):
    for wo in adjusted.instance["work_orders"]:
        _ARRIVAL.setdefault(wo["id"], float(wo["release_bh"]))
    return _ORIG["raise"](adjusted, t_d)


@contextmanager
def site_rule(rule):
    """The guard's configured dispatcher is ``rule`` inside the block; ATC outside."""
    import l1guard.config as gc
    import n8_causal as n8

    install()
    base = gc.G_CERT
    if base.rule != "atc" or base.seed != SEED or n8.raise_releases is not _ORIG["raise"]:
        raise SystemExit("REFUSING TO RUN: G_CERT is not the published configuration on entry")
    gc.G_CERT = base.with_(rule=RULE_IMPL[rule])
    if rule == "pfifo":
        n8.raise_releases = _raise_recording
    _ARRIVAL.clear()
    try:
        yield
    finally:
        gc.G_CERT = base
        n8.raise_releases = _ORIG["raise"]
        _ARRIVAL.clear()


def gp(*args, **kw):
    """N11's ``gen_price`` with a fresh arrival record (one priced call)."""
    _ARRIVAL.clear()
    try:
        return D.gen_price(*args, **kw)
    finally:
        _ARRIVAL.clear()


def trade_sig(binst, avail, trade, t_d) -> str:
    """Content key of one trade of a relaxed board: orders, technicians, availability, t_d."""
    wos = sorted([wo["id"], float(wo["p_bh"]), float(wo["release_bh"]), float(wo["due_bh"]),
                  float(wo["weight"]), int(wo["priority"])]
                 for wo in binst["work_orders"] if wo["trade"] == trade)
    techs = sorted([t["id"], float(avail[t["id"]])] for t in binst["technicians"]
                   if t["trade"] == trade)
    return D.sha_text(json.dumps([trade, float(t_d), wos, techs], separators=(",", ":")))


# --------------------------------------------------------------------------- #
# Census worker: one (rule, instance)                                          #
# --------------------------------------------------------------------------- #
_TASKS: list = []


def _winit(cores):
    D.cap_threads(1)
    if cores:
        os.sched_setaffinity(0, set(cores))
    install()


def census_task(ti) -> dict:
    from l1adapter import dispatch as dispatch_mod
    from l1adapter import evaluate as evaluate_mod
    import n8_causal as n8

    F_ = _F()
    task = _TASKS[ti]
    rule = task["rule"]
    impl = RULE_IMPL[rule]
    t0 = time.perf_counter()
    inst = D.load_instance(task["path"])
    iid = inst["meta"]["id"]
    by_id = {wo["id"]: wo for wo in inst["work_orders"]}
    trade_of = {wo["id"]: wo["trade"] for wo in inst["work_orders"]}
    out = {"rule": rule, "iid": iid, "items": [], "seeds": {}, "boards": [],
           "relaxed_inputs": [], "fi": [], "fi_anchors": [], "fails": [], "counts": Counter(),
           "audit": {}}

    def fail(group, what):
        out["fails"].append([group, "{} [{}] {}".format(iid, rule, what)])

    sites = {}
    board_sites = {}
    need_boards = OrderedDict()
    exec_up = {}
    fi_anchor = {}
    AUDIT.clear()
    with site_rule(rule):
        _ARRIVAL.clear()
        baseline = dispatch_mod.dispatch_baseline(inst, impl, SEED)
        out["plain_wwt"] = evaluate_mod.wwt(inst, baseline)
        if rule == "pfifo":
            plain = dispatch_mod.dispatch_baseline(inst, RULE_N6[rule], SEED)
            # Same assignments and decision count; only the method label differs.
            out["pfifo_plain_equal"] = (plain["assignments"] == baseline["assignments"]
                                        and plain["decisions"] == baseline["decisions"])
        trajs = {}
        for fk, seed in task["seeds"].items():
            _ARRIVAL.clear()
            traj = n8.trajectory(inst, seed, baseline)
            trajs[fk] = traj
            anc = gp(inst, EMPTY_RAW, seed, baseline, 0.0)
            out["seeds"][fk] = {
                "traj_times_equal": D._times(traj) == D._times(baseline),
                "traj_slots_equal": D._slots(traj) == D._slots(baseline),
                "anchor": {k: anc.get(k) for k in ("term_cert", "stage_cert", "obj", "obj_orig",
                                                   "gap", "lb")}}

        def note_exec(t_d, tuples, res, site):
            live = res.get("_live") or {}
            if res.get("term_feas") != "applied_uncertified" or "schedule" not in live:
                return
            run_ids = {r[0] for r in site["running"]}
            adj, sched = live["adjusted"], live["schedule"]
            wt = D.trade_wwt_of(adj.instance, sched, skip=run_ids)
            by_t = defaultdict(list)
            for t in tuples or []:
                if t[0] in trade_of and t[0] not in run_ids:
                    by_t[trade_of[t[0]]].append(tuple(t))
            trades = sorted({wo["trade"] for wo in adj.instance["work_orders"]
                             if wo["id"] not in run_ids})
            for tr in trades:
                tfp = D.fp_of(by_t[tr]) if by_t.get(tr) else D.BASE_FP
                k = (t_d, tr, tfp)
                v = wt.get(tr, 0.0)
                if k not in exec_up or v < exec_up[k]:
                    exec_up[k] = v

        def site_for(fk, seed, t_d):
            key = (fk, t_d)
            if key in sites:
                return sites[key]
            traj = trajs[fk]
            state = n8.site_state(inst, traj, t_d, pm_known=True)
            known = n8.known_instance(inst, state)
            kf = D.kf_fix(state, seed)
            started = state["completed"] + state["in_progress"]
            k_ids = state["queue"] + state["in_progress"] + state["scheduled"]
            base_p = n8.pin_schedule(baseline, traj, started)
            frozen_r = list(started) + [o for o in seed if o not in set(started)]
            site = D.site_of(state, traj, t_d)
            avail = D.availability(inst, site)
            an = gp(known, EMPTY_RAW, kf, base_p, t_d, keep_live=True)
            rw0 = gp(inst, EMPTY_RAW, frozen_r, base_p, t_d, keep_batch=k_ids)
            slot = {a["wo"]: a for a in traj["assignments"]}
            c_done = sum(float(by_id[o]["weight"]) * max(0.0, float(slot[o]["end_bh"])
                                                         - float(by_id[o]["due_bh"]))
                         for o in state["completed"])
            s = {"state": state, "known": known, "kf": kf, "started": started, "k_ids": k_ids,
                 "base_p": base_p, "frozen_r": frozen_r, "site": site, "avail": avail,
                 "an": an, "rw0": rw0, "rconst": D.running_constant(inst, site),
                 "run": list(state["in_progress"]), "c_done": c_done,
                 "completed": set(state["completed"]),
                 "seed_unknown": bool(set(seed) & set(state["unknown"]))}
            sites[key] = s
            bs = board_sites.setdefault(t_d, {
                "site": site, "avail": avail, "mult": D.avail_multiset(inst, avail),
                "running_ids": sorted(r[0] for r in site["running"]),
                "known_ids": sorted(site["known_ids"]), "seeds": []})
            bs["seeds"].append({"fk": fk,
                                "mult_equal": D.avail_multiset(inst, avail) == bs["mult"],
                                "running_equal": sorted(r[0] for r in site["running"])
                                == bs["running_ids"],
                                "known_equal": sorted(site["known_ids"]) == bs["known_ids"]})
            need_boards.setdefault((t_d, D.BASE_FP), [])
            note_exec(t_d, [], an, site)
            return s

        def fi_board(s):
            done = s["completed"]
            fi = {k: v for k, v in inst.items() if k != "work_orders"}
            fi["work_orders"] = [wo for wo in inst["work_orders"] if wo["id"] not in done]
            return fi

        def price_fi(board, s, raw, t_d, ref2=True):
            return gp(board, raw, s["kf"], s["base_p"], t_d, ref2=ref2, keep_batch=s["k_ids"],
                      running_ids=s["run"])

        for it in task["items"]:
            fk, seed = it["fk"], it["seed"]
            traj = trajs[fk]
            starts = {a["wo"]: float(a["start_bh"]) for a in traj["assignments"]}
            iss = D.issuability(it, by_id, starts)
            t_d = float(it["t_d"])
            if abs(iss["t_known"] - t_d) > 0.0:
                fail("R0", "t_known {} differs from N11's t_d {} on {}".format(
                    iss["t_known"], t_d, it["item_id"]))
            ops = it["ops"]
            raw = json.dumps({"operations": ops})
            row = OrderedDict(item_id=it["item_id"], set="published", rule=rule, fk=fk,
                              t_d=t_d, reading="primary")
            for k in ("n_ref", "t_known", "t_start", "issuable", "issuable_strict",
                      "ref_all_pm"):
                row[k] = it["n11"][k]
            row["t_start_rule"] = iss["t_start"]
            row["issuable_rule"] = iss["issuable"]
            # ---- P0: the full window at t = 0 under the rule
            om = gp(inst, raw, seed, baseline, 0.0, ref2=True)
            row.update(D._pick(om, D.PRICE_KEYS, "om_"))
            row["om_fp"] = None if om["tuples"] is None else D.fp_of(om["tuples"])
            # ---- K at t_d under the rule
            s = site_for(fk, seed, t_d)
            st = s["state"]
            ref_set = set(iss["ref_ids"])
            row.update(n_known=len(s["known"]["work_orders"]), n_queue=len(st["queue"]),
                       n_scheduled=len(st["scheduled"]), n_in_progress=len(st["in_progress"]),
                       n_completed=len(st["completed"]), n_unknown=len(st["unknown"]),
                       ref_completed=sorted(ref_set & set(st["completed"])),
                       ref_running=sorted(ref_set & set(st["in_progress"])),
                       ref_unknown=sorted(ref_set & set(st["unknown"])))
            explicit, members = n8.named_orders(ops, inst)
            kset = set(s["k_ids"])
            row.update(n_batch_members=len(members),
                       n_batch_members_known=sum(1 for m in members if m in kset),
                       names_unknown=sorted(o for o in explicit if o in set(st["unknown"])),
                       names_completed=sorted(o for o in explicit if o in set(st["completed"])),
                       names_running=sorted(o for o in explicit if o in set(st["in_progress"])),
                       seed_not_frozen_on_K=sorted(set(seed) & set(st["scheduled"])))
            run_ids = list(st["in_progress"])
            row["names_running_any"] = sorted((set(explicit) | set(members)) & set(run_ids))
            dt = gp(s["known"], raw, s["kf"], s["base_p"], t_d, ref2=True, keep_live=True,
                    running_ids=run_ids)
            row.update(D._pick(dt, D.PRICE_KEYS, "dt_"))
            row["dt_fp"] = None if dt["tuples"] is None else D.fp_of(dt["tuples"])
            row["dt_n_changed"] = None if dt["tuples"] is None else len(dt["tuples"])
            an = s["an"]
            row.update(an_obj=an["obj"], an_obj_orig=an["obj_orig"], an_lb=an["lb"],
                       an_gap=an["gap"], an_lb_running=an["lb_running"],
                       an_term=an["term_cert"], rconst=s["rconst"],
                       n_running=len(s["site"]["running"]))
            row["rw0_obj"], row["rw0_obj_orig"] = s["rw0"]["obj"], s["rw0"]["obj_orig"]
            row["rw0_term"] = s["rw0"]["term_cert"]
            # ---- realised full-window run of the proposal from t_d, executed by the rule
            rw = None
            if "applied_uncertified" in (dt["term_feas"], om["term_feas"]):
                rw = gp(inst, raw, s["frozen_r"], s["base_p"], t_d, keep_batch=s["k_ids"])
            if dt["term_feas"] == "applied_uncertified":
                note_exec(t_d, dt["tuples"], dt, s["site"])
                if dt["stage_cert"] == "qual":
                    need_boards.setdefault((t_d, row["dt_fp"]), dt["tuples"])
            row["rw_term"] = None if rw is None else rw["term_cert"]
            row["rw_term_feas"] = None if rw is None else rw["term_feas"]
            row["rw_obj"] = None if rw is None else rw["obj"]
            row["rw_obj_orig"] = None if rw is None else rw["obj_orig"]
            dt.pop("_live", None)
            # ---- FI: the full window minus the completed orders, from t_d (priced items)
            if dt["stage_cert"] == "qual":
                fkey = (fk, t_d)
                if fkey not in fi_anchor:
                    a = F_.slim(price_fi(fi_board(s), s, EMPTY_RAW, t_d, ref2=False))
                    fi_anchor[fkey] = a
                    out["fi_anchors"].append({"fk": fk, "t_d": t_d, "reading": "FI", "s": 0,
                                              "a": a, "sha": F_.sha_obj(a)})
                    if a["lb"] is not None and a["obj"] is not None and a["lb"] > a["obj"] + TOL:
                        fail("R6", "FI anchor LB above obj at t_d={}".format(t_d))
                a = fi_anchor[fkey]
                p = F_.slim(price_fi(fi_board(s), s, raw, t_d))
                pr = F_.prices_of(p, a)
                out["fi"].append({"uid": it["item_id"], "reading": "FI", "s": 0, "p": p,
                                  "prices": pr})
                if p["lb"] is not None and p["obj"] is not None and p["lb"] > p["obj"] + TOL:
                    fail("R6", "FI proposal LB above obj on " + it["item_id"])
                # R8 (Stage 3 AF1): the full-information board reproduces the realised run
                changed = {t[0] for t in (dt.get("tuples") or [])}
                if s["seed_unknown"] or rw is None or p["obj"] is None:
                    out["counts"]["r8_skipped"] += 1
                elif changed & s["completed"]:
                    out["counts"]["r8_skipped_completed_field"] += 1
                else:
                    c = s["c_done"]
                    out["counts"]["r8_rows"] += 1
                    for what, x, y in (("proposal obj", p["obj"], rw["obj"] - c),
                                       ("anchor obj", a["obj"], s["rw0"]["obj"] - c),
                                       ("proposal original-field obj", p["obj_orig"],
                                        rw["obj_orig"] - c),
                                       ("anchor original-field obj", a["obj_orig"],
                                        s["rw0"]["obj_orig"] - c)):
                        if x is None or y is None or abs(x - y) > TOL:
                            fail("R8", "FI {} != realised - completed constant on {}: {} vs {}"
                                 .format(what, it["item_id"], x, y))
            out["items"].append(row)
    out["audit"]["site"] = dict(AUDIT)
    AUDIT.clear()

    # ---- boards (the oracle's ATC upper end, outside the site's rule)
    for (t_d, fp), tuples in need_boards.items():
        bs = board_sites[t_d]
        rec, live = D.board_record(inst, iid, bs["site"], tuples)
        rec["rule"] = rule
        rec["seeds"] = bs["seeds"]
        rec["avail_multiset"] = bs["mult"]
        rec["running_ids"] = bs["running_ids"]
        for tr, tv in rec["trades"].items():
            tv["sig"] = trade_sig(live["binst"], live["avail"], tr, t_d)
            ex = exec_up.get((t_d, tr, tv["trade_fp"]))
            tv["exec_upper"] = ex
            ups = [(tv["atc"], "atc")] + ([(ex, "executed")] if ex is not None else [])
            tv["upper0"], tv["upper0_source"] = min(ups)
            tv["closed_by_lb2"] = tv["upper0"] <= tv["lb2"] + D.CLOSE_TOL_BH
            if not tv["closed_by_lb2"]:
                ti_ = D.trade_input(live["binst"], live["avail"], tr, live["atc_sched"])
                ti_.update(iid=iid, t_d=t_d, trade=tr, trade_fp=tv["trade_fp"], lb2=tv["lb2"],
                           atc=tv["atc"], exec_upper=ex, n_orders=tv["n_orders"],
                           n_techs=tv["n_techs"], sig=tv["sig"], rule=rule)
                out["relaxed_inputs"].append(ti_)
        out["boards"].append(rec)
    out["audit"]["board"] = dict(AUDIT)
    AUDIT.clear()
    out["counts"] = dict(out["counts"])
    out["wall_s"] = time.perf_counter() - t0
    return out


def run_pool(n, cores, workers, order):
    import multiprocessing as mp

    out = []
    if workers <= 1:
        _winit(cores)
        for i in order:
            out.append(census_task(i))
        return out
    ctx = mp.get_context("fork")
    with ctx.Pool(workers, initializer=_winit, initargs=(cores,), maxtasksperchild=4) as pool:
        for res in pool.imap_unordered(census_task, order):
            out.append(res)
            print("[n14 census] done {} {} ({:.0f}s), {} of {}".format(
                res["rule"], res["iid"], res["wall_s"], len(out), len(order)), flush=True)
    return out


# --------------------------------------------------------------------------- #
# Inputs                                                                       #
# --------------------------------------------------------------------------- #
def code_hashes() -> dict:
    out = OrderedDict()
    for p in (Path(__file__), Path(D.__file__), Path(SCRIPTS_DIR) / "n8_causal.py",
              Path(SCRIPTS_DIR) / "n11_forecast.py", Path(SCRIPTS_DIR) / "n2_pricing.py",
              D.CODE / "l1adapter" / "dispatch.py", D.CODE / "l1adapter" / "apply.py",
              D.CODE / "l1adapter" / "evaluate.py", D.CODE / "l1guard" / "guard.py",
              D.CODE / "l1guard" / "config.py", D.CODE / "l1guard" / "lb2.py",
              D.CODE / "l1oracle" / "cpsat_avail.py",
              Path(((os.environ.get("L1_Y1_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "PaperY-FMScheduling")) + "/src/fmwos/pdrs.py"))):
        out[str(Path(p).resolve())] = D.sha256_file(p)
    return out


def data_hashes() -> dict:
    out = OrderedDict()
    for p in (D.SUITE_PATH, D.CODE / "scripts" / "instance_manifest_l1.json", N11_ITEMS,
              N11_BOARDS, N11_SOLVES, N11_BRACKETS, N11F_FULLINFO, N11F_ANCHORS,
              N11F_CONSEQUENCE, N11_PRICING, N11_WINS, N6_ANCHOR, D.ANCHOR_PATH,
              D.ORACLE_V1 / "brackets.jsonl"):
        out[str(Path(p).relative_to(ROOT)) if str(p).startswith(str(ROOT)) else str(p)] = \
            D.sha256_file(p)
    return out


def load_inputs(check) -> dict:
    """The suite, N11's census rows (by the hashes N11's census wrote) and Stage 3's FI rows."""
    meta = json.loads(N11_CENSUS_META.read_text())
    rep = json.loads(N11_CENSUS_ASSERT.read_text())
    check.true("R0", "N11 census assertions say PASS", rep.get("status") == "PASS",
               rep.get("status"))
    for name in ("items.jsonl", "boards.jsonl"):
        check.true("R0", "N11 census {} carries the hash its census wrote".format(name),
                   D.sha256_file(D.OUT / name) == meta["outputs"][name], name)
    frep = json.loads(N11F_ASSERT.read_text())
    check.true("R0", "N11 Stage 3 direct assertions say PASS", frep.get("status") == "PASS",
               frep.get("status"))
    fmeta = json.loads((N11F_DIR / "run_meta_direct.json").read_text())
    for p in (N11F_FULLINFO, N11F_ANCHORS):
        check.true("R0", "Stage 3 {} carries the hash its run wrote".format(p.name),
                   D.sha256_file(p) == fmeta["outputs"][p.name], p.name)
    pub = OrderedDict((r["item_id"], r) for r in D.load_published(check))
    items = D.read_jsonl(N11_ITEMS)
    iss = [r for r in items if r["set"] == "published" and r["issuable"]]
    check.true("R0", "issuable published items = {}".format(EXPECT_ISSUABLE),
               len(iss) == EXPECT_ISSUABLE, len(iss))
    return {"pub": pub, "n11": {r["item_id"]: r for r in items if r["set"] == "published"},
            "iss": iss}


def build_tasks(inp, rules, instances=None) -> list:
    by_inst = OrderedDict()
    for r in inp["iss"]:
        iid = r["instance_id"]
        if instances and iid not in instances:
            continue
        it = inp["pub"][r["item_id"]]
        seed = list(it["episode"]["frozen_seed"] or [])
        fk = D.frozen_key(seed)
        if fk != r["frozen_seed"]:
            raise SystemExit("R0 FAILURE: frozen key of {} differs from N11".format(r["item_id"]))
        t = by_inst.setdefault(iid, {"iid": iid, "path": D.instance_path(it), "items": [],
                                     "seeds": OrderedDict()})
        t["seeds"].setdefault(fk, seed)
        t["items"].append({"item_id": r["item_id"], "fk": fk, "seed": seed,
                           "ops": D.canonical_ops(it), "referenced": it["referenced"],
                           "t_d": float(r["t_d"]),
                           "n11": {k: r[k] for k in ("n_ref", "t_known", "t_start", "issuable",
                                                     "issuable_strict", "ref_all_pm")}})
    tasks = []
    for rule in rules:
        for t in by_inst.values():
            tasks.append(dict(t, rule=rule))
    return tasks


def task_order(tasks) -> list:
    def rank(i):
        iid = tasks[i]["iid"]
        return (0 if "c10_storm" in iid else 1 if "c09_storm" in iid else 2,
                -len(tasks[i]["items"]), tasks[i]["rule"])
    return sorted(range(len(tasks)), key=rank)


def enrich(rows, pub) -> None:
    """Suite metadata on each census row (the columns N11's cmd_census adds)."""
    for r in rows:
        it = pub[r["item_id"]]
        r["primary_class"] = it["primary_class"]
        r["subclass"] = it["subclass"]
        r["stratum"] = it["instance"]["stratum"]
        r["instance_id"] = it["instance"]["instance_id"]
        r["twin_id"] = it.get("twin_id")
        r["quality_visible"] = bool(it.get("quality_visible_candidate"))
        r["register"] = it.get("register")
        ops = D.canonical_ops(it)
        r["n_ops"] = len(ops)
        r["op_types"] = "|".join(sorted({o.get("op", "?") for o in ops if isinstance(o, dict)}))
        r["split"] = D.op_split(ops)
        r["c_role"] = None
        r["frozen_seed"] = r.pop("fk")


def anchors_of(seeds_rows) -> dict:
    """(instance, frozen key) -> the rule's t = 0 anchor, in rule_anchor.json's fields."""
    out = {}
    for s in seeds_rows:
        a = s["anchor"]
        out[(s["iid"], s["fk"])] = {"wwt_original_bh": a["obj_orig"],
                                    "wwt_adjusted_bh": a["obj"], "gap": a["gap"],
                                    "certificate": {"lb_bh": a["lb"]},
                                    "terminal_cert": a["term_cert"]}
    return out


def same(a, b, tol=EXACT) -> bool:
    if isinstance(a, float) or isinstance(b, float):
        if a is None or b is None:
            return a is None and b is None
        return abs(float(a) - float(b)) <= tol
    return a == b


# --------------------------------------------------------------------------- #
# census                                                                       #
# --------------------------------------------------------------------------- #
def rule_dir(base, rule) -> Path:
    p = base / rule
    p.mkdir(parents=True, exist_ok=True)
    return p


def cmd_census(args) -> int:
    global _TASKS
    cores = D.parse_cores(args.cores)
    D.pin_cores(cores)
    D.cap_threads(1)
    install()
    rules = tuple(args.rules.split(","))
    for r in rules:
        if r not in RULES:
            raise SystemExit("unknown rule {}".format(r))
    smoke = bool(args.instances)
    base = OUT / "smoke" if smoke else OUT
    base.mkdir(parents=True, exist_ok=True)
    check = D.Checker()
    t_start = time.time()
    inp = load_inputs(check)
    instances = set(args.instances.split(",")) if smoke else None
    tasks = build_tasks(inp, rules, instances)
    _TASKS = tasks
    order = task_order(tasks)
    print("[n14 census] rules {}, {} tasks, {} items per rule, workers {} on cores {}".format(
        rules, len(tasks), sum(len(t["items"]) for t in tasks) // max(1, len(rules)),
        args.workers, cores), flush=True)
    results = run_pool(len(tasks), cores, args.workers, order)
    wall = time.time() - t_start
    by_rule = defaultdict(list)
    for res in results:
        by_rule[res["rule"]].append(res)
    summary = OrderedDict()
    outputs = OrderedDict()
    for rule in rules:
        res_r = sorted(by_rule[rule], key=lambda x: x["iid"])
        items, boards, rel, fi, fia, seeds = [], [], [], [], [], []
        for res in res_r:
            items.extend(res["items"])
            boards.extend(res["boards"])
            rel.extend(res["relaxed_inputs"])
            for x in res["fi"]:
                fi.append(dict(x, iid=res["iid"]))
            for x in res["fi_anchors"]:
                fia.append(dict(x, iid=res["iid"]))
            for fk, v in res["seeds"].items():
                seeds.append(dict(v, iid=res["iid"], fk=fk))
        enrich(items, inp["pub"])
        census_checks(check, rule, res_r, items, boards, seeds, inp, smoke)
        if rule == CONTROL:
            r7_fi(check, fi, fia, items, smoke)
        d = rule_dir(base, rule)
        D.write_jsonl(d / "items.jsonl", items)
        D.write_jsonl(d / "boards.jsonl", boards)
        D.write_jsonl(d / "relaxed_inputs.jsonl", rel)
        D.write_jsonl(d / "fullinfo.jsonl", fi)
        D.write_jsonl(d / "fullinfo_anchors.jsonl", fia)
        D.write_jsonl(d / "seeds.jsonl", seeds)
        D.write_json(d / "instances.json", {r["iid"]: {
            "plain_wwt": r["plain_wwt"], "pfifo_plain_equal": r.get("pfifo_plain_equal"),
            "wall_s": r["wall_s"], "counts": r["counts"], "audit": r["audit"]} for r in res_r})
        for p in sorted(d.glob("*.jsonl")) + [d / "instances.json"]:
            outputs["{}/{}".format(rule, p.name)] = D.sha256_file(p)
        n_trades = sum(len(b["trades"]) for b in boards)
        summary[rule] = OrderedDict(
            items=len(items), priced_K=sum(1 for r in items if r["dt_stage_cert"] == "qual"),
            boards=len(boards), trades=n_trades, open_trades=len(rel),
            open_distinct=len({x["sig"] for x in rel}), fi_rows=len(fi),
            names_running_any=sum(1 for r in items if r["names_running_any"]),
            ref_started=sum(1 for r in items if r["ref_completed"] or r["ref_running"]),
            not_issuable_under_rule=sum(1 for r in items if not r["issuable_rule"]),
            r8_rows=sum(r["counts"].get("r8_rows", 0) for r in res_r),
            wall_cpu_s=round(sum(r["wall_s"] for r in res_r), 1))
        if rule == CONTROL:
            summary[rule]["r7_running_rule_items"] = CENSUS_INFO.get("r7_running_rule_items")
            summary[rule]["r7_rw_n8_only"] = CENSUS_INFO.get("r7_rw_n8_only", 0)
    rep = check.report()
    meta = OrderedDict(version=VERSION, stage="census", smoke=smoke, rules=list(rules),
                       instances=sorted(instances) if instances else "all",
                       finished=D.now_iso(), wall_s=wall, cores=cores, workers=args.workers,
                       omp_num_threads=os.environ.get("OMP_NUM_THREADS"),
                       mkl_num_threads=os.environ.get("MKL_NUM_THREADS"),
                       load_avg_end=D.loadavg(), host=socket.gethostname(),
                       python=sys.version.split()[0], summary=summary, code=code_hashes(),
                       data=data_hashes(), outputs=outputs)
    D.write_json(base / "census_meta.json", meta)
    print(json.dumps(summary, indent=1), flush=True)
    check.fatal(base / "census_assertions.json", {"outputs": outputs, "code": meta["code"],
                                                  "data": meta["data"],
                                                  "finished": meta["finished"],
                                                  "rules": list(rules), "smoke": smoke})
    print("[n14 census] PASS: {} checks in {:.0f}s".format(rep["n_checks"], wall), flush=True)
    return 0


def census_checks(check, rule, res_r, items, boards, seeds, inp, smoke):
    """R1-R8 on one rule's census output (R7 only for the control)."""
    tag = "[{}]".format(rule)
    for res in res_r:
        for grp, msg in res["fails"]:
            check.true(grp, msg, False)
        # R3: every site dispatch used the rule, every board dispatch ATC
        site_rules = set(res["audit"].get("site", {}))
        board_rules = set(res["audit"].get("board", {}))
        check.true("R3", "{} site dispatches use {} on {}".format(tag, RULE_IMPL[rule],
                                                                  res["iid"]),
                   site_rules == {RULE_IMPL[rule]}, sorted(site_rules))
        check.true("R3", "{} board dispatches use ATC on {}".format(tag, res["iid"]),
                   board_rules <= {"atc"}, sorted(board_rules))
        if rule == "pfifo":
            check.true("R1", "pfifo_arrival baseline equals N6's pfifo on " + res["iid"],
                       res.get("pfifo_plain_equal") is True)
    # R1: the plain dispatch objective equals N6's anchor (every rule, every instance)
    n6 = {}
    for r in D.read_csv_comments(N6_ANCHOR):
        if r["block"] == "instance":
            n6[(r["rule"], r["instance_id"])] = float(r["anchor_wt"])
    for res in res_r:
        want = n6.get((RULE_N6[rule], res["iid"]))
        check.true("R1", "{} N6 anchor row exists for {}".format(tag, res["iid"]),
                   want is not None)
        if want is not None:
            check.close("R1", "{} plain dispatch equals N6's anchor on {}".format(
                tag, res["iid"]), res["plain_wwt"], want, 1e-5)
    # R2: trajectory and board-site seed invariance
    for s in seeds:
        check.true("R2", "{} trajectory equals the plain dispatch on {} [{}]".format(
            tag, s["iid"], s["fk"]), s["traj_times_equal"])
    for b in boards:
        for s in b["seeds"]:
            check.true("R2", "{} board site of {} t_d={} is seed-invariant ({})".format(
                tag, b["iid"], b["t_d"], s["fk"]),
                s["mult_equal"] and s["running_equal"] and s["known_equal"])
    anchors = anchors_of(seeds)
    # R4 (A7): the no-proposal realised run equals the rule's own t = 0 anchor
    for r in items:
        a = anchors[(r["instance_id"], r["frozen_seed"])]
        check.close("R4", "{} no-proposal realised run equals the rule's anchor on {}".format(
            tag, r["item_id"]), r["rw0_obj_orig"], a["wwt_original_bh"], TOL)
        check.close("R4", "{} no-proposal realised run (adjusted) equals the anchor on {}"
                    .format(tag, r["item_id"]), r["rw0_obj"], a["wwt_adjusted_bh"], TOL)
    # R5 (A8): at t_d = 0 the realised run is the full-window run
    for r in items:
        if r["t_d"] != 0.0 or r["n_batch_members_known"] != r["n_batch_members"]:
            continue
        if r["om_term_feas"] != "applied_uncertified":
            continue
        check.true("R5", "{} realised run exists at t_d = 0 on {}".format(tag, r["item_id"]),
                   r["rw_obj"] is not None)
        check.close("R5", "{} realised objective equals the full window on {}".format(
            tag, r["item_id"]), r["rw_obj"], r["om_obj"], TOL)
        check.close("R5", "{} realised original-field objective equals the full window on {}"
                    .format(tag, r["item_id"]), r["rw_obj_orig"], r["om_obj_orig"], TOL)
    # R6 (A9, A12): bounds and boards
    bkey = {(b["iid"], b["t_d"], b["fp"]): b for b in boards}
    for b in boards:
        check.true("R6", "{} board ATC dispatch is feasible {} t_d={}".format(
            tag, b["iid"], b["t_d"]), b["atc_feasible"])
        for tr, tv in b["trades"].items():
            check.true("R6", "{} LB2 <= upper {} t_d={} {}".format(tag, b["iid"], b["t_d"], tr),
                       tv["lb2"] <= tv["upper0"] + D.CHECK_TOL)
    for r in items:
        if r["dt_lb"] is not None and r["dt_obj"] is not None:
            check.true("R6", "{} LB_K <= obj_K on {}".format(tag, r["item_id"]),
                       r["dt_lb"] <= r["dt_obj"] + D.CHECK_TOL)
        if r["an_lb"] is not None:
            check.true("R6", "{} anchor LB_K <= obj_K on {}".format(tag, r["item_id"]),
                       r["an_lb"] <= r["an_obj"] + D.CHECK_TOL)
        b0 = bkey.get((r["instance_id"], r["t_d"], D.BASE_FP))
        check.true("R6", "{} anchor board exists for {}".format(tag, r["item_id"]),
                   b0 is not None)
        if b0 is None:
            continue
        check.close("R6", "{} running constant equals bound_known on {}".format(
            tag, r["item_id"]), b0["running_const"], r["an_lb_running"], D.CHECK_TOL)
        check.close("R6", "{} anchor board LB2 + running constant equals LB_K on {}".format(
            tag, r["item_id"]), sum(tv["lb2"] for tv in b0["trades"].values())
            + b0["running_const"], r["an_lb"], D.CHECK_TOL)
        if r["dt_stage_cert"] == "qual":
            b = bkey.get((r["instance_id"], r["t_d"], r["dt_fp"]))
            check.true("R6", "{} proposal board exists for {}".format(tag, r["item_id"]),
                       b is not None)
            if b is not None:
                lo = sum(tv["lb2"] for tv in b["trades"].values()) + b["running_const"]
                check.close("R6", "{} proposal board LB2 sum equals LB_K on {}".format(
                    tag, r["item_id"]), lo, r["dt_lb"], D.CHECK_TOL)
                check.true("R6", "{} obj_K at or above the board's LB2 end on {}".format(
                    tag, r["item_id"]), r["dt_obj"] >= lo - D.CHECK_TOL)
    if rule == CONTROL:
        r7_control(check, items, boards, seeds, inp, smoke)


def r7_control(check, items, boards, seeds, inp, smoke):
    """R7: the ATC control reproduces N11's census rows, boards, anchors and FI rows."""
    n11 = inp["n11"]
    pub_anchor = D.load_anchor_records()
    n_running_rule = 0
    for r in items:
        m = n11[r["item_id"]]
        skip = set()
        if r["names_running_any"]:
            n_running_rule += 1
            skip = set(R7_RUNNING_RULE_FIELDS)
            check.true("R7", "running-work refusal is a stop on " + r["item_id"],
                       r["dt_term_cert"] in D.STOP_TERMS)
        check.true("R7", "the control's own t_start equals N11's on " + r["item_id"],
                   same(r["t_start_rule"], m["t_start"]) and r["issuable_rule"] == m["issuable"],
                   "{!r} vs {!r}".format(r["t_start_rule"], m["t_start"]))
        for k in R7_FIELDS:
            if k in skip:
                continue
            check.true("R7", "{} equals N11 on {}".format(k, r["item_id"]), same(r[k], m[k]),
                       "{!r} vs {!r}".format(r[k], m[k]))
        if r["rw_term"] is not None or m["rw_term"] is None:
            for k in R7_RW_FIELDS:
                check.true("R7", "{} equals N11 on {}".format(k, r["item_id"]),
                           same(r[k], m[k]), "{!r} vs {!r}".format(r[k], m[k]))
        else:
            # N11 also ran the realised run when only N8's frozen-set convention applied it.
            check.true("R7", "N11's extra realised run comes from N8's frozen set on "
                       + r["item_id"], bool(m.get("kf_differs")))
            CENSUS_INFO["r7_rw_n8_only"] = CENSUS_INFO.get("r7_rw_n8_only", 0) + 1
    CENSUS_INFO["r7_running_rule_items"] = n_running_rule
    for s in seeds:
        a = pub_anchor[(s["iid"], s["fk"])]
        check.close("R7", "t = 0 anchor equals rule_anchor (adjusted) on {} [{}]".format(
            s["iid"], s["fk"]), s["anchor"]["obj"], float(a["wwt_adjusted_bh"]), TOL)
        check.close("R7", "t = 0 anchor equals rule_anchor (original) on {} [{}]".format(
            s["iid"], s["fk"]), s["anchor"]["obj_orig"], float(a["wwt_original_bh"]), TOL)
        check.close("R7", "t = 0 anchor gap equals rule_anchor on {} [{}]".format(
            s["iid"], s["fk"]), s["anchor"]["gap"], float(a["gap"]), TOL)
    nb = {(b["iid"], float(b["t_d"]), b["fp"]): b for b in D.read_jsonl(N11_BOARDS)}
    for b in boards:
        m = nb.get((b["iid"], float(b["t_d"]), b["fp"]))
        check.true("R7", "N11 board exists for {} t_d={} {}".format(b["iid"], b["t_d"],
                                                                   b["fp"][:10]), m is not None)
        if m is None:
            continue
        for k in ("n_orders", "n_running", "running_const", "atc_feasible", "avail_multiset"):
            check.true("R7", "board {} equals N11 on {} t_d={}".format(k, b["iid"], b["t_d"]),
                       same(b[k], m[k]), "{!r} vs {!r}".format(b[k], m[k]))
        check.true("R7", "board trades equal N11 on {} t_d={}".format(b["iid"], b["t_d"]),
                   sorted(b["trades"]) == sorted(m["trades"]))
        for tr, tv in b["trades"].items():
            mv = m["trades"].get(tr)
            if mv is None:
                continue
            for k in ("trade_fp", "n_orders", "n_techs", "lb2", "atc"):
                check.true("R7", "trade {} equals N11 on {} t_d={} {}".format(
                    k, b["iid"], b["t_d"], tr), same(tv[k], mv[k]),
                    "{!r} vs {!r}".format(tv[k], mv[k]))
            ok = (tv["exec_upper"] is None) or (mv["exec_upper"] is not None and
                                                mv["exec_upper"] <= tv["exec_upper"] + EXACT)
            check.true("R7", "N11's executed upper end is at most the control's on {} {} {}"
                       .format(b["iid"], b["t_d"], tr), ok)


CENSUS_INFO: dict = {}


def r7_fi(check, fi_rows, fi_anchor_rows, items, smoke):
    """R7 (FI part): the control's FI prices and anchors equal Stage 3's, row by row."""
    F_ = _F()
    want = {r["uid"]: r for r in D.read_jsonl(N11F_FULLINFO)}
    priced = {r["item_id"] for r in items if r["dt_stage_cert"] == "qual"}
    got = {r["uid"]: r for r in fi_rows}
    check.true("R7", "FI rows cover every priced control item", set(got) == priced,
               len(set(got) ^ priced))
    for uid, r in got.items():
        w = want.get(uid)
        check.true("R7", "Stage 3 FI row exists for " + uid, w is not None)
        if w is None:
            continue
        check.true("R7", "FI price record equals Stage 3 on " + uid,
                   F_.canon(r["p"]) == F_.canon(w["p"]) and
                   F_.canon(r["prices"]) == F_.canon(w["prices"]),
                   "{} vs {}".format(F_.canon(r["prices"]), F_.canon(w["prices"])))
    if not smoke:
        check.true("R7", "FI rows equal Stage 3's in number", len(got) == len(want),
                   "{} vs {}".format(len(got), len(want)))
    wa = {(r["iid"], r["fk"], float(r["t_d"])): r["a"] for r in D.read_jsonl(N11F_ANCHORS)
          if r["reading"] == "FI"}
    for a in fi_anchor_rows:
        w = wa.get((a["iid"], a["fk"], float(a["t_d"])))
        check.true("R7", "FI anchor equals Stage 3 on {} t_d={}".format(a["iid"], a["t_d"]),
                   w is not None and F_.canon(w) == F_.canon(a["a"]))


# --------------------------------------------------------------------------- #
# oracle                                                                       #
# --------------------------------------------------------------------------- #
def n11_trade_brackets() -> dict:
    """(instance, t_d, trade, trade fingerprint) -> N11's (lower, upper, status) per trade."""
    rel_rows, _ = D.load_rows_last(N11_SOLVES, D.relaxed_key)
    _br, trade_br = D.assemble_boards(D.read_jsonl(N11_BOARDS), rel_rows)
    return trade_br


def sig_map_from_control(base) -> dict:
    """trade content key -> N11's trade bracket, through the control's boards (identical)."""
    tb = n11_trade_brackets()
    out = {}
    for b in D.read_jsonl(base / CONTROL / "boards.jsonl"):
        for tr, tv in b["trades"].items():
            k = (b["iid"], float(b["t_d"]), tr, tv["trade_fp"])
            v = tb.get(k)
            if v is None:
                raise SystemExit("R9 FAILURE: control trade {} has no N11 bracket".format(k))
            prev = out.get(tv["sig"])
            if prev is not None:
                # Two valid brackets of one optimisation problem: keep their intersection.
                v = (max(prev[0], v[0]), min(prev[1], v[1]),
                     prev[2] if prev[2] == v[2] else "{}+{}".format(prev[2], v[2]))
                if v[0] > v[1] + D.CHECK_TOL:
                    raise SystemExit("R9 FAILURE: N11 brackets of one trade content are "
                                     "disjoint: {}".format(k))
            out[tv["sig"]] = v
    return out


def solve_key(r):
    return r["sig"]


def processes_on(cores) -> list:
    """Every process the scheduler last ran on ``cores``, with its affinity mask (ps + taskset)."""
    lines = subprocess.run(["ps", "-eo", "pid,psr,pcpu,args"], capture_output=True, text=True,
                           check=True).stdout.splitlines()[1:]
    out = []
    for ln in lines:
        parts = ln.split(None, 3)
        if len(parts) < 4:
            continue
        pid, psr, pcpu = int(parts[0]), int(parts[1]), float(parts[2])
        if psr not in cores:
            continue
        try:
            mask = sorted(os.sched_getaffinity(pid))
        except OSError:
            mask = None
        pinned = mask is not None and len(mask) < os.cpu_count()
        out.append({"pid": pid, "psr": psr, "pcpu": pcpu, "args": parts[3][:160],
                    "affinity": (mask if pinned else "all"), "pinned": pinned})
    return out


def cmd_oracle(args) -> int:
    cores = D.parse_cores(args.cores)
    D.pin_cores(cores)
    if os.environ.get("OMP_NUM_THREADS") != "1" or os.environ.get("MKL_NUM_THREADS") != "1":
        raise SystemExit("REFUSING TO RUN: launch with OMP_NUM_THREADS=1 MKL_NUM_THREADS=1")
    base = OUT / "smoke" if args.smoke else OUT
    rep = json.loads((base / "census_assertions.json").read_text())
    if rep.get("status") != "PASS":
        raise SystemExit("REFUSING TO RUN: census_assertions.json says {}".format(rep.get("status")))
    for name, digest in rep["outputs"].items():
        if D.sha256_file(base / name) != digest:
            raise SystemExit("REFUSING TO RUN: {} changed since the census".format(name))
    if rep["code"].get(str(Path(D.__file__).resolve())) != D.sha256_file(D.__file__):
        raise SystemExit("REFUSING TO RUN: n11_decision_time.py changed since the census")
    foreign = D.foreign_on_cores(set(cores))
    procs = processes_on(set(cores))
    pinned_foreign = [p for p in procs if p["pinned"] and p["pid"] != os.getpid()
                      and set(p["affinity"]) & set(cores) and p["pcpu"] >= 1.0]
    if foreign or pinned_foreign:
        raise SystemExit("REFUSING TO RUN: foreign processes on cores {}: {} {}".format(
            cores, foreign, pinned_foreign))
    odir = base / "oracle"
    odir.mkdir(parents=True, exist_ok=True)
    import ortools

    sig_map = sig_map_from_control(base)
    rel_in = OrderedDict()
    reuse = Counter()
    for rule in rep["rules"]:
        for ti in D.read_jsonl(base / rule / "relaxed_inputs.jsonl"):
            if ti["sig"] in sig_map:
                reuse[rule] += 1
                continue
            rel_in.setdefault(ti["sig"], ti)
    path = odir / "trade_solves.jsonl"
    meta = OrderedDict(
        version=VERSION, started=D.now_iso(), host=socket.gethostname(),
        python=sys.version.split()[0], platform=platform.platform(), ortools=ortools.__version__,
        cores=cores, workers=args.workers, budget_s=args.budget,
        omp_num_threads=os.environ.get("OMP_NUM_THREADS"),
        mkl_num_threads=os.environ.get("MKL_NUM_THREADS"),
        foreign_share_max=D.FOREIGN_SHARE_MAX, max_resolves=D.MAX_RESOLVES,
        affinity=sorted(os.sched_getaffinity(0)), load_avg_start=D.loadavg(),
        foreign_processes_at_start=foreign, processes_on_cores_at_start=procs,
        census=rep["finished"], reused_from_n11=dict(reuse), to_solve=len(rel_in),
        code=code_hashes())
    D.write_json(odir / "run_meta.json", meta)
    D.append_jsonl(odir / "run_meta_history.jsonl", meta)
    rows, drops = D.load_rows_last(path, solve_key)
    todo = sorted(rel_in.values(), key=lambda r: (r["n_orders"], r["iid"], r["t_d"], r["trade"]))
    resolved = []
    t0 = time.perf_counter()
    n = 0
    for ti in todo:
        k = ti["sig"]
        while k not in rows:
            row = D.solve_relaxed(ti, args, cores)
            row["sig"] = k
            row["rule_first"] = ti["rule"]
            row["n14_version"] = VERSION
            if row["invalid"]:
                resolved.append({"key": k, "foreign_share": row["foreign_share"],
                                 "attempt": drops[k] + 1})
                if drops[k] >= D.MAX_RESOLVES:
                    row["invalid_persistent"] = True
            D.append_jsonl(path, row)
            if row["invalid"] and not row.get("invalid_persistent"):
                drops[k] += 1
                print("[n14 oracle] INVALID (foreign_share {:.3f}) {}; solving again".format(
                    row["foreign_share"], k[:12]), flush=True)
                continue
            rows[k] = row
            n += 1
            print("[n14 oracle] {}/{} {} {} t_d={:.2f} {} n={} status={} [{:.3f}, {:.3f}] "
                  "wall={:.1f}s cpu_share={} solve_cpu_share={} foreign={}".format(
                      n, len(todo), ti["rule"], ti["iid"], ti["t_d"], ti["trade"],
                      ti["n_orders"], row["status"], row["lower"], row["upper"], row["wall_s"],
                      None if row["cpu_share"] is None else round(row["cpu_share"], 3),
                      None if row["solve_cpu_share"] is None else round(row["solve_cpu_share"], 3),
                      None if row["foreign_share"] is None else round(row["foreign_share"], 3)),
                  flush=True)
    for rr in resolved:
        D.append_jsonl(odir / "resolved.jsonl", rr)
    meta.update(finished=D.now_iso(), wall_s=time.perf_counter() - t0, solved=n,
                n_resolved=len(resolved), load_avg_end=D.loadavg(),
                processes_on_cores_at_end=processes_on(set(cores)))
    D.write_json(odir / "run_meta.json", meta)
    D.append_jsonl(odir / "run_meta_history.jsonl", meta)
    print("[n14 oracle] finished: {} solved, {} re-solves, {:.0f}s".format(
        n, len(resolved), meta["wall_s"]), flush=True)
    return 0


# --------------------------------------------------------------------------- #
# analyse                                                                      #
# --------------------------------------------------------------------------- #
def assemble(boards, sig_map, solves) -> list:
    """D.assemble_boards with the trade bracket looked up by content (N11's or this run's)."""
    out = []
    for b in boards:
        lo = up = 0.0
        complete, proved = True, True
        statuses = Counter()
        sources = Counter()
        for tr, tv in b["trades"].items():
            if tv["closed_by_lb2"]:
                tl, tu, st, src = tv["lb2"], tv["upper0"], "CLOSED_BY_LB2", "lb2"
            elif tv["sig"] in sig_map:
                ntl, ntu, st = sig_map[tv["sig"]]
                tl, tu, src = max(ntl, tv["lb2"]), min(ntu, tv["upper0"]), "n11"
            else:
                r = solves.get(tv["sig"])
                if r is None:
                    complete = False
                    statuses["MISSING"] += 1
                    continue
                tl, tu, st, src = float(r["lower"]), min(float(r["upper"]), tv["upper0"]), \
                    r["status"], "n14"
            statuses[st] += 1
            sources[src] += 1
            lo += tl
            up += tu
            proved = proved and (st in ("OPTIMAL", "CLOSED_BY_LB2") or tu - tl <= D.CLOSE_TOL_BH)
        c = b["running_const"]
        rec = OrderedDict(iid=b["iid"], t_d=b["t_d"], fp=b["fp"], n_orders=b["n_orders"],
                          n_running=b["n_running"], running_const=c, complete=complete,
                          lower=(lo + c) if complete else None, upper=(up + c) if complete else None,
                          proved_all=complete and proved, statuses=dict(statuses),
                          sources=dict(sources),
                          lb2_total=sum(tv["lb2"] for tv in b["trades"].values()) + c)
        if complete:
            rec["width_rel"] = (rec["upper"] - rec["lower"]) / max(rec["lower"], D.FLOOR_BH)
            if rec["lower"] > rec["upper"] + D.CHECK_TOL:
                raise SystemExit("R9 FAILURE: board bracket inverted on {} {}".format(
                    b["iid"], b["t_d"]))
        out.append(rec)
    return out


class _N2Check:
    """N2's checker interface (``true(what, ok, detail)``) onto this run's grouped checker."""

    def __init__(self, check, group):
        self.check, self.group = check, group

    def true(self, what, ok, detail=""):
        self.check.true(self.group, what, ok, detail)


class _NoMacros(D.Macros):
    def __init__(self):
        super().__init__({})


def anchor_gap_stats(iss, td_br) -> list:
    """The anchor gap of the known board, per item and per distinct board, by stratum."""
    out = []
    per_item = []
    for r in iss:
        if r["ref1"] is None:
            continue
        b = td_br.get((r["instance_id"], r["t_d"], D.BASE_FP))
        if b is None:
            continue
        lo, up, _p = D.ends(b)
        per_item.append((r, D.gfun(r["ref1"], up), D.gfun(r["ref1"], lo)))
    for unit in ("item", "board"):
        for st in ("all",) + D.STRATA:
            rs = [x for x in per_item if st == "all" or x[0]["stratum"] == st]
            if unit == "board":
                seen = OrderedDict()
                for x in rs:
                    seen.setdefault((x[0]["instance_id"], x[0]["t_d"]), x)
                rs = list(seen.values())
            lo = [x[1] for x in rs]
            hi = [x[2] for x in rs]
            cert = [x[0]["g_cert_anchor"] for x in rs if x[0]["g_cert_anchor"] is not None]
            out.append(OrderedDict(
                unit=unit, stratum=st, n=len(rs),
                median_lo=D.pctl(lo, 50), median_hi=D.pctl(hi, 50),
                p90_lo=D.pctl(lo, 90), p90_hi=D.pctl(hi, 90),
                max_lo=max(lo) if lo else None, max_hi=max(hi) if hi else None,
                mean_lo=(sum(lo) / len(lo)) if lo else None,
                zero=sum(1 for x in hi if x <= 1e-12),
                above_005=sum(1 for x in lo if x > 0.05),
                above_010=sum(1 for x in lo if x > 0.10),
                above_020=sum(1 for x in lo if x > 0.20),
                cert_anchor_gap_median=D.pctl(cert, 50),
                cert_anchor_gap_p90=D.pctl(cert, 90),
                cert_anchor_gap_above_tau=sum(1 for x in cert if x > D.TAU)))
    return out


def full_window_anchor_gap(seeds, full_br) -> list:
    """Each rule's anchor gap on the full window (fk = '' anchors; N6's Table 1 quantity)."""
    out = []
    by = defaultdict(list)
    for s in seeds:
        if s["fk"]:
            continue
        b = full_br.get((s["iid"], D.BASE_FP))
        lo, up, _p = D.ends(b)
        st = next(x for x in D.STRATA if s["iid"].startswith(x))
        g = (D.gfun(s["anchor"]["obj_orig"], up), D.gfun(s["anchor"]["obj_orig"], lo))
        by["all"].append(g)
        by[st].append(g)
    for st in ("all",) + D.STRATA:
        gs = by.get(st, [])
        out.append(OrderedDict(stratum=st, n=len(gs),
                               median_lo=D.pctl([g[0] for g in gs], 50),
                               median_hi=D.pctl([g[1] for g in gs], 50),
                               max_hi=max((g[1] for g in gs), default=None),
                               above_tau=sum(1 for g in gs if g[0] > D.TAU)))
    return out


def discordance(priced, rp, truth_fn, delta=0.10) -> dict:
    """Costly proposals D-REL2 applies while the certificate refers them (and the converse)."""
    F_ = _F()
    out = OrderedDict()
    for rd, cur in rp.items():
        c = Counter()
        for r in priced:
            s_ = truth_fn(r, delta)
            if s_ is None:
                continue
            rec = cur[r["item_id"]]
            rel2 = F_.refers_rec(rec, "D-REL2")
            for g in ("G-CERT", "G-CERT-M"):
                ref = F_.refers_rec(rec, g)
                if s_ == 1:
                    c["costly"] += 1 if g == "G-CERT" else 0
                    c[g + "_refers_rel2_misses"] += int(ref and not rel2)
                    c["rel2_refers_" + g + "_misses"] += int(rel2 and not ref)
                else:
                    c["cheap"] += 1 if g == "G-CERT" else 0
                    c[g + "_fr_rel2_not"] += int(ref and not rel2)
                    c["rel2_fr_" + g + "_not"] += int(rel2 and not ref)
        out[rd] = dict(c)
    return out


def kabs_state(r, delta):
    """+1/0/None: the proposal's absolute cost on the known board against the K oracle."""
    if not r.get("covered"):
        return None
    if r["g_lo"] > delta:
        return 1
    if r["g_hi"] <= delta:
        return 0
    return None


def kmarg_state(r, delta):
    if not r.get("covered_m"):
        return None
    if r["m_lo"] > delta:
        return 1
    if r["m_hi"] <= delta:
        return 0
    return None


def k_panel(priced, rp, boot, state_fn, delta=0.10) -> list:
    """Miss and false referral of the K reading against a truth on the known board."""
    F_ = _F()
    out = []
    cur = rp["K"]
    st = {r["item_id"]: state_fn(r, delta) for r in priced}
    for g in F_.DESIGNS + F_.UNIONS:
        costly = [r for r in priced if st[r["item_id"]] == 1]
        cheap = [r for r in priced if st[r["item_id"]] == 0]
        miss = [not F_.refers_rec(cur[r["item_id"]], g) for r in costly]
        fr = [F_.refers_rec(cur[r["item_id"]], g) for r in cheap]
        lo, hi = boot.ci(costly, miss) if costly else (None, None)
        flo, fhi = boot.ci(cheap, fr) if cheap else (None, None)
        out.append(OrderedDict(gate=g, delta=delta, costly=len(costly), miss=sum(miss),
                               cheap=len(cheap), fr=sum(fr),
                               miss_share=(sum(miss) / len(costly)) if costly else None,
                               fr_share=(sum(fr) / len(cheap)) if cheap else None,
                               miss_lo=lo, miss_hi=hi, fr_lo=flo, fr_hi=fhi))
    return out


def analyse_rule(rule, base, sig_map, solves, full_br, check) -> dict:
    """Everything the tables need for one rule."""
    import n2_pricing as n2

    F_ = _F()
    d = base / rule
    items = D.read_jsonl(d / "items.jsonl")
    boards = D.read_jsonl(d / "boards.jsonl")
    seeds = D.read_jsonl(d / "seeds.jsonl")
    fi_rows = D.read_jsonl(d / "fullinfo.jsonl")
    br = assemble(boards, sig_map, solves)
    td_br = {}
    for b in br:
        if b["complete"]:
            td_br[(b["iid"], float(b["t_d"]), b["fp"])] = b
    anchors = anchors_of(seeds)
    rows = D.build_rows(items, td_br, full_br, anchors)
    by_item = {r["item_id"]: r for r in items}
    iss = [r for r in rows if r["issuable"]]
    priced = [r for r in iss if r["priced"]]
    for r in priced:
        it = by_item[r["item_id"]]
        r["frozen_seed_key"] = it["frozen_seed"]
        a = anchors[(r["instance_id"], it["frozen_seed"])]
        for k in ("om_term_cert", "om_stage_cert", "om_obj_orig", "an_obj_orig"):
            r[k] = it.get(k)
        p0 = dict(it, pub_anchor_wwt=a["wwt_original_bh"], pub_anchor_gap=a["gap"])
        if p0["om_stage_cert"] == "qual":
            D.om_prices(p0)
        for g in F_.DESIGNS:
            r["om_p_" + g] = p0.get("om_p_" + g)
        r["damage_adj"] = None if r["rw_obj"] is None else r["rw_obj"] - a["wwt_adjusted_bh"]
    F_.attach_orig_truth(priced, full_br, anchors)
    fullinfo = defaultdict(list)
    for x in fi_rows:
        fullinfo[(x["uid"], "FI")].append((x["s"], x))
    rp = F_.reading_prices(priced, {}, fullinfo, READINGS)
    pub_ids = {it["instance"]["instance_id"] for it in PUB_CACHE["pub"].values()}
    boot = n2.Boot(pub_ids, n2.SEED, n2.B_BOOT)
    cons = F_.consequence(priced, rp, boot)
    groupings = [("all", lambda r: ["all"]), ("stratum", lambda r: [r["stratum"]]),
                 ("class", lambda r: [r["primary_class"]])]
    pr = n2.pricing_table(priced, "direct_td", groupings)
    rg = D.refgap_section(iss, priced, td_br, pr, n2, _NoMacros())
    wins = n2.wins_table(priced, "direct_td", dict(D.DG14), rg["_by_stratum"],
                         rg["_cert_by_stratum"])
    sound = n2.soundness(priced, _N2Check(check, "R9"), "N14 {}".format(rule), 1e-6)
    ag = anchor_gap_stats(iss, td_br)
    fw = full_window_anchor_gap(seeds, full_br)
    kp = {"absolute": k_panel(priced, rp, boot, kabs_state),
          "marginal": k_panel(priced, rp, boot, kmarg_state)}
    disc = {"orig": discordance(priced, rp, lambda r, dl: F_.costly_of(r, "orig", dl)),
            "origabs": discordance(priced, rp, lambda r, dl: F_.costly_of(r, "origabs", dl)),
            "kabs": discordance(priced, rp, kabs_state)}
    # sensitivity: items issuable under the rule as well (the N11 issuable set restricted)
    both = [r for r in priced if by_item[r["item_id"]]["issuable_rule"]]
    cons_both = F_.consequence(both, {k: v for k, v in rp.items() if k in ("K", "FI")}, boot,
                               groups=("all",)) if both else []
    need = set()
    for r in iss:
        if r["priced"]:
            need.add((r["instance_id"], r["t_d"], r["fingerprint"]))
            need.add((r["instance_id"], r["t_d"], D.BASE_FP))
    covered = sum(1 for k in need if k in td_br)
    for r in priced:
        if r["covered"]:
            check.true("R9", "[{}] obj_K >= board lower on {}".format(rule, r["item_id"]),
                       r["obj"] >= float(r["opt_lower"]) - D.CHECK_TOL)
            check.true("R9", "[{}] certificate bound <= board upper on {}".format(
                rule, r["item_id"]), r["lb_cert"] <= float(r["opt_upper"]) + D.CHECK_TOL)
    for b in br:
        if b["complete"]:
            check.true("R9", "[{}] board lower <= upper {} {}".format(rule, b["iid"], b["t_d"]),
                       b["lower"] <= b["upper"] + D.CHECK_TOL)
    return {"rule": rule, "items": items, "rows": rows, "iss": iss, "priced": priced,
            "rp": rp, "cons": cons, "pricing": pr, "wins": wins, "refgap": rg, "sound": sound,
            "anchor_gap": ag, "full_anchor_gap": fw, "kpanel": kp, "disc": disc,
            "cons_both": cons_both, "n_both": len(both), "brackets": br, "need": len(need),
            "covered": covered, "seeds": seeds, "boards": boards}


PUB_CACHE: dict = {}


def r10_control(check, A) -> dict:
    """R10: the control's analysed cells equal N11's published decision-time cells."""
    out = Counter()
    cons_key = lambda r: (r["truth"], "{:.6f}".format(float(r["delta"])), r["reading"],  # noqa: E731
                          r["agg"], r["gate"], r["group_kind"], str(r["group"]))
    want = {}
    for r in D.read_csv_comments(N11F_CONSEQUENCE):
        if r["reading"] in READINGS and r["agg"] == "median":
            want[cons_key(r)] = r
    mine = {cons_key(dict(r, delta=float(r["delta"]))): r for r in A["cons"]}
    check.true("R10", "control consequence cells equal N11F_consequence.csv in number",
               len(mine) == len(want), "{} vs {}".format(len(mine), len(want)))
    for k, w in want.items():
        m = mine.get(k)
        check.true("R10", "consequence cell exists {}".format(k), m is not None)
        if m is None:
            continue
        out["consequence_cells"] += 1
        for f in ("costly", "miss", "cheap", "fr", "mc_undecided"):
            check.true("R10", "consequence {} equals N11 {}".format(f, k), int(w[f]) == m[f],
                       "{} vs {}".format(w[f], m[f]))
        for f in ("miss_share", "fr_share", "miss_lo", "miss_hi", "fr_lo", "fr_hi"):
            wv = None if w[f] == "" else float(w[f])
            mv = m[f]
            check.true("R10", "consequence {} equals N11 {}".format(f, k),
                       (wv is None and mv is None) or (wv is not None and mv is not None
                                                       and abs(wv - mv) <= CSV_TOL),
                       "{} vs {}".format(wv, mv))
    pkey = lambda r: (r["truth"], r["split"], r["gate"], r["group_kind"], str(r["group"]))  # noqa: E731
    pw = {pkey(r): r for r in D.read_csv_comments(N11_PRICING) if r["dataset"] == "direct_td"}
    pm = {pkey(r): r for r in A["pricing"]}
    check.true("R10", "control pricing cells equal N11_pricing.csv in number",
               len(pm) == len(pw), "{} vs {}".format(len(pm), len(pw)))
    for k, w in pw.items():
        m = pm.get(k)
        check.true("R10", "pricing cell exists {}".format(k), m is not None)
        if m is None:
            continue
        out["pricing_cells"] += 1
        for f, wv in w.items():
            if f in ("dataset", "truth", "split", "gate", "group_kind", "group"):
                continue
            mv = m.get(f)
            if wv == "":
                check.true("R10", "pricing {} equals N11 {}".format(f, k), mv is None, mv)
            else:
                check.true("R10", "pricing {} equals N11 {}".format(f, k),
                           mv is not None and abs(float(wv) - float(mv)) <= CSV_TOL,
                           "{} vs {}".format(wv, mv))
    wkey = lambda r: (r["truth"], "{:.6f}".format(float(r["delta"])), r["rule"],  # noqa: E731
                      r["stratum"], r["cls"], r["split"])
    ww = {wkey(r): r for r in D.read_csv_comments(N11_WINS) if r["dataset"] == "direct_td"}
    wm = {wkey(r): r for r in A["wins"]}
    check.true("R10", "control decision cells equal N11_wins.csv in number",
               len(wm) == len(ww), "{} vs {}".format(len(wm), len(ww)))
    for k, w in ww.items():
        m = wm.get(k)
        check.true("R10", "decision cell exists {}".format(k), m is not None)
        if m is None:
            continue
        out["wins_cells"] += 1
        for f, wv in w.items():
            if f in ("dataset", "truth", "delta", "rule", "stratum", "cls", "split"):
                continue
            mv = m.get(f)
            if wv == "":
                check.true("R10", "decision {} equals N11 {}".format(f, k), mv is None, mv)
            else:
                check.true("R10", "decision {} equals N11 {}".format(f, k),
                           mv is not None and abs(float(wv) - float(mv)) <= CSV_TOL,
                           "{} vs {}".format(wv, mv))
    pooled = next(x for x in A["anchor_gap"] if x["unit"] == "item" and x["stratum"] == "all")
    check.true("R10", "control anchor gap is zero on 1,670 of 1,723 issuable items",
               (pooled["zero"], len(A["iss"])) == EXPECT_N11_ZERO_GAP,
               (pooled["zero"], len(A["iss"])))
    nb = {(b["iid"], float(b["t_d"]), b["fp"]): b for b in D.read_jsonl(N11_BRACKETS)}
    for b in A["brackets"]:
        m = nb.get((b["iid"], float(b["t_d"]), b["fp"]))
        check.true("R10", "N11 bracket exists for control board {} {}".format(b["iid"], b["t_d"]),
                   m is not None and m["complete"])
        if m is None:
            continue
        out["brackets"] += 1
        check.close("R10", "control bracket lower equals N11 on {} {}".format(b["iid"], b["t_d"]),
                    b["lower"], m["lower"], EXACT)
        check.close("R10", "control bracket upper equals N11 on {} {}".format(b["iid"], b["t_d"]),
                    b["upper"], m["upper"], EXACT)
    return dict(out)


# ---- formatting -------------------------------------------------------------
def pct(x, d=1):
    return "n/a" if x is None else "{:.{}f}".format(100.0 * x, d)


def pct_tex(x, d=1):
    return "n/a" if x is None else "{:.{}f}\\%".format(100.0 * x, d)


def ival_pct(lo, hi, d=1):
    if lo is None or hi is None:
        return "n/a"
    a, b = "{:.{}f}".format(100 * lo, d), "{:.{}f}".format(100 * hi, d)
    return a if a == b else "[{}, {}]".format(a, b)


def num(x, d=3):
    return "n/a" if x is None else "{:.{}f}".format(x, d)


def ival(lo, hi, d=3):
    if lo is None or hi is None:
        return "n/a"
    a, b = "{:.{}f}".format(lo, d), "{:.{}f}".format(hi, d)
    return a if a == b else "[{}, {}]".format(a, b)


def crow(table, **kw):
    for r in table:
        ok = True
        for k, v in kw.items():
            rv = r.get(k)
            if isinstance(v, float):
                ok = ok and rv is not None and abs(float(rv) - v) < 1e-12
            else:
                ok = ok and rv == v
        if ok:
            return r
    return None


class N14Macros:
    def __init__(self):
        self.lines = []
        self.names = set()
        self.map = []

    def add(self, name, value, exhibit="", note=""):
        name = "nFourteen" + name
        if not name.isalpha():
            raise SystemExit("macro name {} is not alphabetic".format(name))
        if name in self.names:
            raise SystemExit("macro {} written twice".format(name))
        self.names.add(name)
        self.lines.append("\\newcommand{\\" + name + "}{" + str(value) + "}")
        self.map.append(OrderedDict(macro=name, value=str(value), exhibit=exhibit, note=note))


GATES_TAB = ("G-CERT", "G-CERT-M", "D-REL1", "D-REL2", "D-ABS", "G-CERT-M|D-REL2")
GATE_NAME = {"G-CERT-M|D-REL2": "Union", "G-CERT|D-REL2": "G-CERT or D-REL2"}
GTOK = {"G-CERT": "Cert", "G-CERT-M": "CertM", "D-REL1": "RelOne", "D-REL2": "RelTwo",
        "D-ABS": "Abs", "G-CERT-M|D-REL2": "Union", "G-CERT|D-REL2": "UnionCert"}
TRUTH_TOK = {"orig": "", "origabs": "OrigAbs", "real": "AdjFields"}
STRATUM_TOK = {"all": "All", "c09_storm2_w80": "Primary", "c10_storm2_w80": "Confirmation",
               "c10_replay_400": "Buildings"}


def cmd_analyse(args) -> int:
    cores = D.parse_cores(args.cores)
    D.pin_cores(cores)
    D.cap_threads(1)
    install()
    t0 = time.time()
    base = OUT / "smoke" if args.smoke else OUT
    rep = json.loads((base / "census_assertions.json").read_text())
    if rep.get("status") != "PASS":
        raise SystemExit("REFUSING TO RUN: census_assertions.json says {}".format(rep.get("status")))
    for name, digest in rep["outputs"].items():
        if D.sha256_file(base / name) != digest:
            raise SystemExit("REFUSING TO RUN: {} changed since the census".format(name))
    check = D.Checker()
    PUB_CACHE["pub"] = OrderedDict((r["item_id"], r) for r in D.load_published(check))
    rules = rep["rules"]
    if CONTROL not in rules:
        raise SystemExit("REFUSING TO RUN: the control rule is not in the census")
    full_br = D.full_brackets()
    sig_map = sig_map_from_control(base)
    spath = base / "oracle" / "trade_solves.jsonl"
    solves, drops = D.load_rows_last(spath, solve_key)
    # R9: timing record on every solve row; no invalid row enters a table
    timing_keys = ("affinity", "workers", "omp_num_threads", "load_avg_start", "load_avg_end",
                   "wall_s", "solve_wall_s", "cpu_s", "cpu_share", "solve_cpu_share",
                   "foreign_cpu_s", "foreign_share", "status", "budget_s")
    all_solves = D.read_jsonl(spath)
    for sr in all_solves:
        check.true("R9", "solve row carries the timing record",
                   all(k in sr for k in timing_keys), [k for k in timing_keys if k not in sr])
    for k, sr in solves.items():
        check.true("R9", "no invalid solve row enters a table: {}".format(k[:12]),
                   not sr.get("invalid") or sr.get("invalid_persistent"))
    A = OrderedDict()
    for rule in rules:
        A[rule] = analyse_rule(rule, base, sig_map, solves, full_br, check)
        print("[n14 analyse] {}: {} issuable, {} priced on K, {} of {} boards bracketed".format(
            rule, len(A[rule]["iss"]), len(A[rule]["priced"]), A[rule]["covered"],
            A[rule]["need"]), flush=True)
    r10 = r10_control(check, A[CONTROL]) if not args.smoke else {"skipped": "smoke"}
    complete = all(A[r]["covered"] == A[r]["need"] for r in rules)
    status = "COMPLETE" if complete else "PARTIAL"
    adir = base / "analysis"
    adir.mkdir(parents=True, exist_ok=True)
    M = N14Macros()
    S = write_tables(A, M, adir, status)
    rows_out = n14_rows(A)
    target_rows = ANALYSIS / "N14_rows.csv" if not args.smoke else adir / "N14_rows.csv"
    D.write_csv_rows(target_rows, rows_out,
                     ["N14 rows ({}): one row per (dispatcher, issuable item) of the decision-time "
                      "direct benchmark; status {}".format(VERSION, status),
                      "generated by code/scripts/n14_alt_dispatch.py analyse; prices on K, FI and "
                      "P0 under the rule; truths: K oracle (g, m), realised marginal and absolute "
                      "cost on the original fields (orig_m, orig_g)"],
                     list(rows_out[0].keys()))
    M.add("CoverageStatus", status.lower(), "coverage")
    hdr = "% N14 macros ({}), status {}; generated by code/scripts/n14_alt_dispatch.py " \
          "analyse".format(VERSION, status)
    lines = [hdr] + (["% PARTIAL: not every needed bracket is on disk; not for publication"]
                     if not complete else []) + M.lines
    mpath = ANALYSIS / "N14_macros.tex" if not args.smoke else adir / "N14_macros.tex"
    mpath.write_text("\n".join(lines) + "\n")
    D.write_csv_rows(adir / "N14_macro_map.csv", M.map, ["N14 macro map ({})".format(VERSION)],
                     ["macro", "value", "exhibit", "note"])
    oracle_meta = {}
    if (base / "oracle" / "run_meta.json").is_file():
        oracle_meta = json.loads((base / "oracle" / "run_meta.json").read_text())
    crep = check.report()
    md = summary_md(A, S, status, r10, crep, oracle_meta, all_solves, solves, rep)
    spath_md = ANALYSIS / "N14_summary.md" if not args.smoke else adir / "N14_summary.md"
    spath_md.write_text(md)
    check.fatal(base / "analyse_assertions.json", {"status_coverage": status, "r10": r10,
                                                   "finished": D.now_iso()})
    print("[n14 analyse] {}: {} checks, {:.0f}s".format(status, crep["n_checks"],
                                                        time.time() - t0), flush=True)
    return 0


def n14_rows(A) -> list:
    out = []
    for rule, a in A.items():
        rp = a["rp"]
        pri = {r["item_id"]: r for r in a["priced"]}
        by_item = {r["item_id"]: r for r in a["items"]}
        for r in a["iss"]:
            it = by_item[r["item_id"]]
            p = pri.get(r["item_id"])
            rec = OrderedDict(
                rule=rule, item_id=r["item_id"], primary_class=r["primary_class"],
                subclass=r["subclass"], stratum=r["stratum"], instance_id=r["instance_id"],
                split=r["split"], t_d=r["t_d"], issuable_rule=it["issuable_rule"],
                t_start_rule=it["t_start_rule"], n_running=r["n_running"],
                names_running_any=len(it["names_running_any"]),
                ref_started=len(it["ref_completed"]) + len(it["ref_running"]),
                terminal_K=r["terminal"], stage_K=r["stage"], codes_K=r["codes"],
                priced_K=r["priced"], obj_K=r["obj"], lb_K=r["lb_cert"], anchor_K=r["ref1"],
                anchor_lb_K=r["anchor_lb_K"], ref2_K=r["ref2"],
                opt_K_lower=r.get("opt_lower"), opt_K_upper=r.get("opt_upper"),
                g_anchor_K_lo=r.get("g_anchor_lo"), g_anchor_K_hi=r.get("g_anchor_hi"),
                g_K_lo=r.get("g_lo"), g_K_hi=r.get("g_hi"), m_K_lo=r.get("m_lo"),
                m_K_hi=r.get("m_hi"), rw_obj_orig=r["rw_obj_orig"],
                rw0_obj_orig=r["rw0_obj_orig"], anchor_rule_t0=r["anchor_pub"],
                damage_if_applied=r["damage_if_applied"])
            for rd in READINGS:
                cur = rp[rd].get(r["item_id"]) if p is not None else None
                for g in ("G-CERT", "G-CERT-M", "D-REL1", "D-REL2", "D-ABS"):
                    rec["p_{}_{}".format(rd, g)] = None if cur is None else cur.get("p_" + g)
            rec["orig_m_lo"] = None if p is None else p.get("orig_m_lo")
            rec["orig_m_hi"] = None if p is None else p.get("orig_m_hi")
            rec["orig_g_lo"] = None if p is None else p.get("orig_g_lo")
            rec["orig_g_hi"] = None if p is None else p.get("orig_g_hi")
            out.append(rec)
    return out


def write_tables(A, M, adir, status) -> dict:
    """CSV exhibits and the macros; returns the summary sections."""
    S = OrderedDict()
    cons_all, pricing_all, ag_all, fw_all, kp_all, wins_all = [], [], [], [], [], []
    for rule, a in A.items():
        for r in a["cons"]:
            cons_all.append(dict(r, rule=rule))
        for r in a["pricing"]:
            pricing_all.append(dict(r, rule=rule))
        for r in a["anchor_gap"]:
            ag_all.append(dict(r, rule=rule))
        for r in a["full_anchor_gap"]:
            fw_all.append(dict(r, rule=rule))
        for lab, tab in a["kpanel"].items():
            for r in tab:
                kp_all.append(dict(r, rule=rule, truth="K_" + lab))
        for r in a["wins"]:
            wins_all.append(dict(r, rule_site=rule))
    for name, tab in (("N14_consequence.csv", cons_all), ("N14_pricing.csv", pricing_all),
                      ("N14_anchor_gap_K.csv", ag_all), ("N14_anchor_gap_full.csv", fw_all),
                      ("N14_kpanel.csv", kp_all), ("N14_wins_K.csv", wins_all)):
        if tab:
            cols = ["rule"] + [k for k in tab[0].keys() if k != "rule"]
            if name == "N14_wins_K.csv":
                cols = ["rule_site"] + [k for k in tab[0].keys() if k != "rule_site"]
            D.write_csv_rows(adir / name, tab, ["N14 ({}), status {}".format(VERSION, status)],
                             cols)
    # ---- macros: the headline twin of tab:decision (orig, delta 0.10, all)
    for rule, a in A.items():
        rt = RULE_TOKEN[rule]
        for rd in READINGS:
            for g in GATES_TAB + ("G-CERT|D-REL2",):
                for truth in ("orig", "origabs"):
                    c = crow(a["cons"], truth=truth, delta=0.10, reading=rd, agg="median", gate=g,
                             group_kind="all", group="all")
                    if c is None:
                        continue
                    stem = "{}{}{}{}DeltaTen".format(rt, READING_TOKEN[rd], TRUTH_TOK[truth],
                                                     GTOK[g])
                    M.add(stem + "Miss", pct_tex(c["miss_share"]), "tab:decision twin")
                    M.add(stem + "MissLo", pct(c["miss_lo"]), "tab:decision twin")
                    M.add(stem + "MissHi", pct(c["miss_hi"]), "tab:decision twin")
                    M.add(stem + "FalseRef", pct_tex(c["fr_share"]), "tab:decision twin")
                    M.add(stem + "FalseRefLo", pct(c["fr_lo"]), "tab:decision twin")
                    M.add(stem + "FalseRefHi", pct(c["fr_hi"]), "tab:decision twin")
                    M.add(stem + "MissCount", c["miss"], "tab:decision twin")
                    M.add(stem + "FalseRefCount", c["fr"], "tab:decision twin")
                    if g == "G-CERT":
                        M.add("{}{}{}CostlyDeltaTen".format(rt, READING_TOKEN[rd],
                                                            TRUTH_TOK[truth]),
                              D.group_int(c["costly"]), "tab:decision twin")
                        M.add("{}{}{}CheapDeltaTen".format(rt, READING_TOKEN[rd],
                                                           TRUTH_TOK[truth]),
                              D.group_int(c["cheap"]), "tab:decision twin")
        # ---- the anchor gap of the known board
        for x in a["anchor_gap"]:
            if x["unit"] != "item":
                continue
            st = STRATUM_TOK[x["stratum"]]
            M.add("{}AnchorGapK{}Median".format(rt, st), ival_pct(x["median_lo"],
                                                                  x["median_hi"]) + "\\%",
                  "anchor gap on K")
            M.add("{}AnchorGapK{}PNinety".format(rt, st), ival_pct(x["p90_lo"], x["p90_hi"])
                  + "\\%", "anchor gap on K")
            M.add("{}AnchorGapK{}Max".format(rt, st), ival_pct(x["max_lo"], x["max_hi"]) + "\\%",
                  "anchor gap on K")
            M.add("{}AnchorGapK{}Items".format(rt, st), D.group_int(x["n"]), "anchor gap on K")
            M.add("{}AnchorGapK{}ZeroItems".format(rt, st), D.group_int(x["zero"]),
                  "anchor gap on K")
            M.add("{}AnchorGapK{}NonZeroItems".format(rt, st), D.group_int(x["n"] - x["zero"]),
                  "anchor gap on K")
            M.add("{}AnchorGapK{}AboveTenItems".format(rt, st), D.group_int(x["above_010"]),
                  "anchor gap on K")
        for x in a["full_anchor_gap"]:
            st = STRATUM_TOK[x["stratum"]]
            M.add("{}AnchorGapFull{}Median".format(rt, st),
                  ival_pct(x["median_lo"], x["median_hi"]) + "\\%", "anchor gap, full window")
        # ---- pricing error against the known-board optimum
        for lab, ltok in (("absolute", "Abs"), ("marginal", "Marg")):
            for g in ("G-CERT", "G-CERT-M", "D-REL1", "D-REL2", "D-ABS"):
                for st in ("all",) + D.STRATA:
                    gk, gv = ("all", "all") if st == "all" else ("stratum", st)
                    r = crow(a["pricing"], truth=lab, split="all", gate=g, group_kind=gk, group=gv)
                    if r is None or not r["priced"]:
                        continue
                    stem = "{}PriceK{}{}{}".format(rt, ltok, GTOK[g], STRATUM_TOK[st])
                    M.add(stem + "UnderShare", pct_tex(r["under_share"]), "pricing on K")
                    M.add(stem + "OverShare", pct_tex(r["over_share"]), "pricing on K")
                    M.add(stem + "MedianError", ival(r["e_median_lo"], r["e_median_hi"]),
                          "pricing on K")
                    if st == "all" and g == "G-CERT":
                        M.add("{}PriceK{}Priced".format(rt, ltok), D.group_int(r["priced"]),
                              "pricing on K")
        # ---- the K-oracle panels and the discordance counts
        for lab, tab in a["kpanel"].items():
            ltok = "KAbs" if lab == "absolute" else "KMarg"
            for c in tab:
                if c["gate"] not in GATES_TAB:
                    continue
                stem = "{}{}{}DeltaTen".format(rt, ltok, GTOK[c["gate"]])
                M.add(stem + "Miss", pct_tex(c["miss_share"]), "K-oracle panel")
                M.add(stem + "FalseRef", pct_tex(c["fr_share"]), "K-oracle panel")
                if c["gate"] == "G-CERT":
                    M.add("{}{}CostlyDeltaTen".format(rt, ltok), D.group_int(c["costly"]),
                          "K-oracle panel")
                    M.add("{}{}CheapDeltaTen".format(rt, ltok), D.group_int(c["cheap"]),
                          "K-oracle panel")
        for tlab, dd in a["disc"].items():
            ttok = {"orig": "Orig", "origabs": "OrigAbs", "kabs": "KAbs"}[tlab]
            for rd, cnt in dd.items():
                M.add("{}{}{}CertRefersRelTwoMisses".format(rt, READING_TOKEN[rd], ttok),
                      cnt.get("G-CERT_refers_rel2_misses", 0), "discordance")
                M.add("{}{}{}CertMRefersRelTwoMisses".format(rt, READING_TOKEN[rd], ttok),
                      cnt.get("G-CERT-M_refers_rel2_misses", 0), "discordance")
        M.add("{}PricedK".format(rt), D.group_int(len(a["priced"])), "population")
        M.add("{}Issuable".format(rt), D.group_int(len(a["iss"])), "population")
        by_item = {r["item_id"]: r for r in a["items"]}
        M.add("{}RefStarted".format(rt), D.group_int(sum(
            1 for r in a["items"] if r["ref_completed"] or r["ref_running"])), "population")
        M.add("{}NotIssuableUnderRule".format(rt), D.group_int(sum(
            1 for r in a["items"] if not r["issuable_rule"])), "population")
        M.add("{}NamesRunning".format(rt), D.group_int(sum(
            1 for r in a["items"] if r["names_running_any"])), "population")
        del by_item
    return S


def summary_md(A, S, status, r10, crep, oracle_meta, all_solves, solves, crep_census) -> str:
    F_ = _F()
    L = ["# N14. The gate comparison at the decision instant under other dispatching rules", "",
         "Generated {} by `code/scripts/n14_alt_dispatch.py` ({}). Status {}. {} analyse "
         "assertions passed; census assertions: see "
         "`results/n14_altdispatch/census_assertions.json`.".format(
             D.now_iso(), VERSION, status, crep["n_checks"]), "",
         "## What was computed", "",
         "- Population: the {} issuable published items of N11 with N11's decision instant "
         "t_d = t_known and canonical proposals; thresholds tau = 0.20, D-REL1 0.02, D-REL2 0.02, "
         "D-ABS 0.8119 bh.".format(EXPECT_ISSUABLE),
         "- Dispatchers (the site's rule for the baseline, the trajectory, every dispatch of K, FI "
         "and the full window, the D-REL2 reference and the realised run): " +
         "; ".join("`{}` ({})".format(r, RULE_LABEL[r]) for r in A) + ". PFIFO keeps the "
         "release recorded before the dispatch-origin raise (N6's `pfifo` on every dispatch "
         "where nothing is raised, asserted).",
         "- Readings: K (known board at t_d), FI (full window minus completed orders, at t_d), P0 "
         "(full window at t = 0). Truths: realised marginal cost on the original fields against "
         "the rule's own no-proposal run (`orig`, the tab:decision truth), the realised absolute "
         "cost on the original fields (`origabs`), and the decision-time oracle of the known board "
         "(absolute g and marginal m; dispatcher-free).",
         ""]
    # ---- headline: tab:decision twin
    L += ["## Headline: dispositions at delta = 0.10 (realised marginal cost, original fields)",
          "", "Miss = share of costly proposals applied; FR = share of cheap proposals referred; "
          "95% cluster-bootstrap interval over instances (N2's bootstrap). Union = G-CERT-M or "
          "D-REL2.", ""]
    for rule, a in A.items():
        c0 = crow(a["cons"], truth="orig", delta=0.10, reading="K", agg="median", gate="G-CERT",
                  group_kind="all", group="all")
        L.append("### {} ({}): {} priced on K, {} costly and {} cheap".format(
            rule, RULE_LABEL[rule], len(a["priced"]), c0["costly"] if c0 else "n/a",
            c0["cheap"] if c0 else "n/a"))
        L.append("")
        body = []
        for g in GATES_TAB:
            row = [GATE_NAME.get(g, g)]
            for rd in READINGS:
                c = crow(a["cons"], truth="orig", delta=0.10, reading=rd, agg="median", gate=g,
                         group_kind="all", group="all")
                if c is None:
                    row += ["n/a", "n/a"]
                    continue
                row.append("{} ({}/{}) [{}, {}]".format(pct(c["miss_share"]), c["miss"],
                                                        c["costly"], pct(c["miss_lo"]),
                                                        pct(c["miss_hi"])))
                row.append("{} ({}/{}) [{}, {}]".format(pct(c["fr_share"]), c["fr"], c["cheap"],
                                                        pct(c["fr_lo"]), pct(c["fr_hi"])))
            body.append(row)
        L.append(D.md_table(["design", "K miss", "K FR", "FI miss", "FI FR", "P0 miss",
                             "P0 FR"], body))
        L.append("")
    # ---- anchor gap
    L += ["## The anchor gap of the known board per dispatcher", "",
          "Anchor gap on K = (anchor dispatch of K by the rule - OPT_K)/max(OPT_K, 1 bh), one value "
          "per issuable item (its (instance, t_d) board); OPT_K is the decision-time oracle. The "
          "certified anchor gap is the certificate's own gap of the anchor on K.", ""]
    body = []
    for rule, a in A.items():
        for x in a["anchor_gap"]:
            if x["unit"] != "item":
                continue
            body.append([rule, STRATUM_TOK[x["stratum"]], x["n"],
                         ival_pct(x["median_lo"], x["median_hi"]),
                         ival_pct(x["p90_lo"], x["p90_hi"]), ival_pct(x["max_lo"], x["max_hi"]),
                         x["zero"], x["above_005"], x["above_010"], x["above_020"],
                         pct(x["cert_anchor_gap_median"]), x["cert_anchor_gap_above_tau"]])
    L.append(D.md_table(["rule", "stratum", "items", "median %", "p90 %", "max %", "gap 0",
                         "> 0.05", "> 0.10", "> 0.20", "certified median %",
                         "certified > tau"], body))
    L.append("")
    body = []
    for rule, a in A.items():
        for x in a["anchor_gap"]:
            if x["unit"] != "board" or x["stratum"] != "all":
                continue
            body.append([rule, x["n"], ival_pct(x["median_lo"], x["median_hi"]),
                         ival_pct(x["p90_lo"], x["p90_hi"]), x["zero"], x["above_010"]])
    L += ["Per distinct (instance, t_d) board:", "",
          D.md_table(["rule", "boards", "median %", "p90 %", "gap 0", "> 0.10"], body), ""]
    body = []
    for rule, a in A.items():
        for x in a["full_anchor_gap"]:
            body.append([rule, STRATUM_TOK[x["stratum"]], x["n"],
                         ival_pct(x["median_lo"], x["median_hi"]), pct(x["max_hi"]),
                         x["above_tau"]])
    L += ["Full-window anchor gap of each rule (t = 0, 60 instances; N6's Table 1 quantity, "
          "reproduced):", "",
          D.md_table(["rule", "stratum", "instances", "median %", "max %", "above 0.20"], body),
          ""]
    # ---- pricing error against the known-board optimum
    L += ["## Pricing error against the known-board optimum (Table 14 twin)", "",
          "Error = price - the decision-time oracle's cost on K; under = error below -0.05.", ""]
    for lab in ("absolute", "marginal"):
        body = []
        for rule, a in A.items():
            row = [rule]
            for g in ("G-CERT", "G-CERT-M", "D-REL1", "D-REL2", "D-ABS"):
                r = crow(a["pricing"], truth=lab, split="all", gate=g, group_kind="all",
                         group="all")
                row.append("n/a" if r is None or not r["priced"] else "{} / {}".format(
                    pct(r["under_share"]), ival(r["e_median_lo"], r["e_median_hi"])))
            body.append(row)
        L += ["{} truth (cells: under % / median error):".format(lab.capitalize()), "",
              D.md_table(["rule", "G-CERT", "G-CERT-M", "D-REL1", "D-REL2", "D-ABS"], body), ""]
    body = []
    for rule, a in A.items():
        for st in D.STRATA:
            r = crow(a["pricing"], truth="absolute", split="all", gate="D-REL2",
                     group_kind="stratum", group=st)
            rm = crow(a["pricing"], truth="marginal", split="all", gate="D-REL2",
                      group_kind="stratum", group=st)
            body.append([rule, STRATUM_TOK[st], r["priced"] if r else "n/a",
                         pct(r["under_share"]) if r else "n/a",
                         pct(rm["under_share"]) if rm else "n/a"])
    L += ["D-REL2 by stratum:", "",
          D.md_table(["rule", "stratum", "priced", "absolute under %", "marginal under %"], body),
          ""]
    # ---- K-oracle panels
    L += ["## Dispositions against the known-board oracle (pricing panel of Table 16), "
          "delta = 0.10", ""]
    for lab in ("absolute", "marginal"):
        body = []
        for rule, a in A.items():
            row = [rule]
            for g in GATES_TAB:
                c = next(x for x in a["kpanel"][lab] if x["gate"] == g)
                row.append("{} / {}".format(pct(c["miss_share"]), pct(c["fr_share"])))
            c = a["kpanel"][lab][0]
            row.append("{} / {}".format(c["costly"], c["cheap"]))
            body.append(row)
        L += ["{} cost on K (cells: miss % / FR %):".format(lab.capitalize()), "",
              D.md_table(["rule"] + [GATE_NAME.get(g, g) for g in GATES_TAB] +
                         ["costly / cheap"], body), ""]
    # ---- realised absolute truth
    L += ["## Dispositions against the realised absolute cost (origabs), delta = 0.10", ""]
    body = []
    for rule, a in A.items():
        for rd in ("K", "FI"):
            row = [rule, rd]
            for g in GATES_TAB:
                c = crow(a["cons"], truth="origabs", delta=0.10, reading=rd, agg="median", gate=g,
                         group_kind="all", group="all")
                row.append("n/a" if c is None else "{} / {}".format(pct(c["miss_share"]),
                                                                    pct(c["fr_share"])))
            c = crow(a["cons"], truth="origabs", delta=0.10, reading=rd, agg="median",
                     gate="G-CERT", group_kind="all", group="all")
            row.append("n/a" if c is None else "{} / {}".format(c["costly"], c["cheap"]))
            body.append(row)
    L += [D.md_table(["rule", "reading"] + [GATE_NAME.get(g, g) for g in GATES_TAB] +
                     ["costly / cheap"], body), ""]
    # ---- discordance
    L += ["## Costly proposals D-REL2 applies and the certificate refers (delta = 0.10)", ""]
    body = []
    for rule, a in A.items():
        for tlab in ("kabs", "origabs", "orig"):
            for rd in ("K", "FI"):
                cnt = a["disc"][tlab].get(rd, {})
                body.append([rule, tlab, rd, cnt.get("costly", 0),
                             cnt.get("G-CERT_refers_rel2_misses", 0),
                             cnt.get("G-CERT-M_refers_rel2_misses", 0),
                             cnt.get("rel2_refers_G-CERT-M_misses", 0),
                             cnt.get("cheap", 0), cnt.get("G-CERT_fr_rel2_not", 0),
                             cnt.get("G-CERT-M_fr_rel2_not", 0)])
    L += [D.md_table(["rule", "truth", "reading", "costly", "G-CERT refers, D-REL2 applies",
                      "G-CERT-M refers, D-REL2 applies", "D-REL2 refers, G-CERT-M applies",
                      "cheap", "G-CERT refers cheap, D-REL2 not", "G-CERT-M refers cheap, "
                      "D-REL2 not"], body), ""]
    # ---- populations
    L += ["## Populations and the decision instant under each rule", ""]
    body = []
    for rule, a in A.items():
        items = a["items"]
        body.append([rule, len(a["iss"]), len(a["priced"]),
                     sum(1 for r in items if r["ref_completed"] or r["ref_running"]),
                     sum(1 for r in items if r["names_running_any"]),
                     sum(1 for r in items if not r["issuable_rule"]),
                     sum(1 for r in items if r["dt_term_cert"] in D.STOP_TERMS
                         and r["dt_stage_cert"] != "qual"),
                     a["n_both"]])
    L += [D.md_table(["rule", "issuable (N11)", "priced on K", "named order started by t_d",
                      "names running work", "not issuable under the rule", "stopped before "
                      "the quality stage", "priced and issuable under the rule"], body), "",
          "Sensitivity on the items also issuable under the rule (K and FI, orig, delta 0.10, "
          "miss / FR %):", ""]
    body = []
    for rule, a in A.items():
        for rd in ("K", "FI"):
            row = [rule, rd]
            for g in GATES_TAB:
                c = crow(a["cons_both"], truth="orig", delta=0.10, reading=rd, agg="median",
                         gate=g, group_kind="all", group="all")
                row.append("n/a" if c is None else "{} / {}".format(pct(c["miss_share"]),
                                                                    pct(c["fr_share"])))
            body.append(row)
    L += [D.md_table(["rule", "reading"] + [GATE_NAME.get(g, g) for g in GATES_TAB], body), ""]
    # ---- oracle
    L += ["## Oracle on the known boards", ""]
    body = []
    for rule, a in A.items():
        src = Counter()
        for b in a["brackets"]:
            for k, v in (b.get("sources") or {}).items():
                src[k] += v
        widths = [b["width_rel"] for b in a["brackets"] if b["complete"]]
        body.append([rule, len(a["brackets"]), sum(1 for b in a["brackets"] if b["complete"]),
                     sum(1 for b in a["brackets"] if b["proved_all"]), src.get("lb2", 0),
                     src.get("n11", 0), src.get("n14", 0),
                     num(max(widths) if widths else None, 4)])
    L += [D.md_table(["rule", "boards", "complete", "proved", "trades closed by LB2",
                      "trades reusing N11", "trades solved by N14", "max width_rel"], body), ""]
    if oracle_meta:
        n_bl = sum(1 for r in all_solves if r["status"] not in D.PROVED)
        L += ["Solve stage: {} distinct trades solved ({} reused from N11 by content), {} "
              "re-solves, wall {:.0f} s, cores {}, {} CP-SAT workers, budget {} s. "
              "Budget-limited rows: {}. Max foreign_share on a budget-limited row: {}. "
              "cpu_share (whole call) median {}; recorded on every row, not the validity test "
              "(foreign_share > 0.10 is).".format(
                  oracle_meta.get("solved"), oracle_meta.get("reused_from_n11"),
                  oracle_meta.get("n_resolved"), oracle_meta.get("wall_s", 0.0),
                  oracle_meta.get("cores"), oracle_meta.get("workers"),
                  oracle_meta.get("budget_s"), n_bl,
                  num(max((r["foreign_share"] or 0.0) for r in all_solves
                          if r["status"] not in D.PROVED), 3) if n_bl else "none",
                  num(D.median([r["cpu_share"] for r in all_solves
                                if r.get("cpu_share") is not None]), 3)), ""]
    # ---- soundness and reproduction
    L += ["## Assertions", ""]
    for rule, a in A.items():
        s = a["sound"]
        L.append("- `{}`: the certificate never under-prices g on K (minimum margin over the "
                 "optimistic end {}; {} covered rows).".format(
                     rule, num(s["min_margin_vs_optimistic_end"], 6), s["covered"]))
    L.append("- Control reproduction (R10): {}.".format(json.dumps(r10)))
    L.append("- Analyse checks by group: {}.".format(json.dumps(crep["checks_by_group"])))
    L.append("")
    del F_
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- #
# config: the resolved configuration, and its diff against N11                 #
# --------------------------------------------------------------------------- #
def resolved_config() -> OrderedDict:
    import l1guard.config as gc
    import n2_pricing as n2

    F_ = _F()
    install()
    guard = OrderedDict()
    for rule in RULES:
        with site_rule(rule):
            guard[rule] = gc.G_CERT.to_dict()
    return OrderedDict(
        version=VERSION, rules=list(RULES), rule_impl=RULE_IMPL, control=CONTROL,
        guard_config_inside_site_rule=guard, guard_config_outside=gc.G_CERT.to_dict(),
        board_upper_heuristic="atc (D.board_atc)", readings=list(READINGS),
        items="N11 census rows, published and issuable (results/n11_decision_time/items.jsonl)",
        decision_instant="N11's t_d = t_known (primary reading)", frozen_set_on_K="kf_fix",
        running_work_rule=True, keep_batch_on_FI="k_ids", tau=D.TAU, dg14=dict(D.DG14),
        deltas=list(F_.DELTAS), truths=list(F_.TRUTHS), bootstrap={"seed": n2.SEED,
                                                                   "B": n2.B_BOOT},
        census={"cores": "8-11", "workers": 4, "omp_num_threads": 1, "mkl_num_threads": 1},
        oracle={"cores": "8-11 exclusive", "cpsat_workers": 4, "budget_s": D.BUDGET_S,
                "one_solve_at_a_time": True, "model": "cpsat_avail via D.solve_relaxed",
                "foreign_share_max": D.FOREIGN_SHARE_MAX, "max_resolves": D.MAX_RESOLVES,
                "reuse": "trade content key; N11 brackets through the control's boards"},
        n11_census=json.loads(N11_CENSUS_META.read_text()) and OrderedDict(
            (k, json.loads(N11_CENSUS_META.read_text())[k]) for k in
            ("cores", "workers", "omp_num_threads", "frozen_set", "reading", "version")),
        n11_oracle=OrderedDict((k, json.loads((D.ORACLE_OUT / "run_meta.json").read_text())[k])
                               for k in ("cores", "workers", "budget_s", "foreign_share_max",
                                         "max_resolves", "omp_num_threads", "mkl_num_threads",
                                         "ortools", "python", "version")),
        n11_stage3_direct=OrderedDict(
            (k, json.loads((N11F_DIR / "run_meta_direct.json").read_text())[k])
            for k in ("cores", "workers", "omp_num_threads", "mkl_num_threads", "readings",
                      "version")))


def cmd_config(args) -> int:
    cfg = resolved_config()
    OUT.mkdir(parents=True, exist_ok=True)
    D.write_json(OUT / "resolved_config.json", cfg)
    print(json.dumps(cfg, indent=1, default=str))
    return 0


# --------------------------------------------------------------------------- #
# main                                                                         #
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("census")
    c.add_argument("--rules", default=",".join(RULES))
    c.add_argument("--instances", default="")
    c.add_argument("--cores", default="8-11")
    c.add_argument("--workers", type=int, default=4)
    o = sub.add_parser("oracle")
    o.add_argument("--cores", default="8-11")
    o.add_argument("--workers", type=int, default=4)
    o.add_argument("--budget", type=float, default=D.BUDGET_S)
    o.add_argument("--smoke", action="store_true")
    a = sub.add_parser("analyse")
    a.add_argument("--cores", default="8-11")
    a.add_argument("--smoke", action="store_true")
    sub.add_parser("config")
    args = ap.parse_args(argv)
    if args.cmd == "config":
        return cmd_config(args)
    if args.cmd == "census":
        return cmd_census(args)
    if args.cmd == "oracle":
        if args.budget != D.BUDGET_S or args.workers != 4:
            raise SystemExit("REFUSING TO RUN: the design fixes 60 s and 4 workers")
        return cmd_oracle(args)
    if args.cmd == "analyse":
        return cmd_analyse(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
