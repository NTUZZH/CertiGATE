#!/usr/bin/env python
"""N11 Stage 2: the end-to-end replay at the decision instant, its twins, and the late reading.

Stage 1 (``n11_decision_time.py``) priced the direct benchmark's canonical
proposals on the known board K at the decision instant t_d.  This module
replays the logged proposals of the two end-to-end experiments the same way
(design Section 6) and rebuilds the published exhibits they feed with the
published builders:

``e2e``       (cores 8-9, deterministic) every E1 row (78,000, all arms) and
              every N3 row (14,560, protocol v1.1 and v1.2) of an issuable item,
              re-judged on K at t_d = t_known (primary) and, for E1, at the late
              instant t_d' = t_start; proposals that name an order K does not
              hold are refused at the schema stage as dangling identifiers;
              the realised full-window run from t_d of every executed proposal
              on both field sets; the decision-time boards the e2e rows need.
``analyse2``  (cores 8-9) the builder reproductions on the logged t = 0 data,
              then the twins: Table 11 (E1 per arm), the E1 strata, Table 13
              (enforcement), the 5.1 damage sentences (DG17), Tables 18 and 19
              (N3, v1.1 and v1.2), the N10 field-change twin, Fig. 4's inputs,
              the tolerance sweep (Fig. 7, Table S20), the e2e pricing rows,
              Table 12 (direct strata and jackknife), and the late reading of
              Tables 10, 11, 14 and 16.  Macros are appended to
              analysis/N11_macros.tex in the \\nEleven family.

The frozen set on K is Stage 2's convention (``n11_decision_time.kf_fix``).
Every assertion is run-fatal.  Version: l1-n11-stage2-1
"""

from __future__ import annotations

import os
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import n11_decision_time as D  # noqa: E402  (sets L1_INSTANCE_ROOT to the snapshot)

import argparse  # noqa: E402
import copy  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import pickle  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import time  # noqa: E402
from collections import Counter, OrderedDict, defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

VERSION = "l1-n11-stage2-1"
ROOT = D.ROOT
RESULTS = D.RESULTS
ANALYSIS = D.ANALYSIS
E2E_OUT = RESULTS / "n11_e2e"
READINGS = ("primary", "late")
APPLIED = ("applied_with_certificate", "applied_uncertified")
BLOCKED = ("blocked_schema", "blocked_feas", "blocked_qual")
QUAL_CODES = frozenset({"gap_above_tau", "lb_exceeds_objective", "lb_unavailable"})
SPOT_EVERY = 25
#: Probe counts of the design (Section 6), compared and reported, not asserted.
PROBE = {"e1_rows_issuable": 67197, "e1_rows_with_ops": 23939, "e1_names_unknown": 1292}


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def item_of(iid_, pub, ext):
    return ext.get(iid_) if iid_.startswith(("CA-", "CN-")) else pub.get(iid_)


def finding_summary(findings) -> list:
    out = []
    for f in findings:
        item = {"stage": f.stage, "code": f.code, "severity": f.severity}
        sub = (f.detail or {}).get("subcode")
        if sub:
            item["subcode"] = sub
        out.append(item)
    return out


# --------------------------------------------------------------------------- #
# e2e worker: one instance, every E1 and N3 input of its issuable items        #
# --------------------------------------------------------------------------- #
_E2E: list = []
R_KEYS = ("term_cert", "stage_cert", "term_feas", "stage_feas", "codes", "obj", "obj_orig", "lb",
          "lb_running", "gap", "ref2", "ref2_from", "constraining", "n_raised", "parse_ok",
          "infra")


def e2e_instance(ti) -> dict:
    """The decision-time verdicts of one instance's logged proposals (design 6)."""
    from l1adapter import dispatch as dispatch_mod
    from l1guard import guard as G
    from l1guard.config import G_CERT, UNGUARDED
    from l1guard.guard_v11 import read_flag, v10_view
    import n8_causal as n8

    task = _E2E[ti]
    t0 = time.perf_counter()
    inst = D.load_instance(task["path"])
    iid = inst["meta"]["id"]
    baseline = dispatch_mod.dispatch_baseline(inst, "atc", 0)
    by_id = {wo["id"]: wo for wo in inst["work_orders"]}
    trade_of = {wo["id"]: wo["trade"] for wo in inst["work_orders"]}
    trajs = {fk: n8.trajectory(inst, seed, baseline) for fk, seed in task["seeds"].items()}
    out = {"iid": iid, "items": {}, "e1": {}, "n3": {}, "gold": {}, "sites": {}, "boards": [],
           "relaxed_inputs": [], "checks": [], "memo": Counter()}
    sites, board_sites = {}, {}
    need_boards = OrderedDict()
    exec_up = {}
    memo_dt, memo_ung, memo_rw = {}, {}, {}

    def fail(what, detail=""):
        out["checks"].append([what, detail])

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
        an = D.gen_price(known, D.EMPTY_RAW, kf, base_p, t_d, keep_live=True)
        rw0 = D.gen_price(inst, D.EMPTY_RAW, frozen_r, base_p, t_d, keep_batch=k_ids)
        s = {"state": state, "known": known, "kf": kf, "k_ids": k_ids, "base_p": base_p,
             "frozen_r": frozen_r, "site": site, "avail": avail, "an": an, "rw0": rw0,
             "rconst": D.running_constant(inst, site), "kset": set(k_ids),
             "unknown": set(state["unknown"]), "completed": set(state["completed"]),
             "running": set(state["in_progress"]),
             # Stage 3 addition A: operations naming running work are refused on K.
             "run_ids": list(state["in_progress"])}
        sites[key] = s
        board_sites.setdefault(t_d, {"site": site, "avail": avail})
        need_boards.setdefault((t_d, D.BASE_FP), [])
        note_exec(t_d, [], an, site)
        out["sites"]["{}|{}".format(fk, t_d)] = {
            "an_obj": an["obj"], "an_obj_orig": an["obj_orig"], "an_lb": an["lb"],
            "an_gap": an["gap"], "an_lb_running": an["lb_running"], "an_term": an["term_cert"],
            "rw0_obj": rw0["obj"], "rw0_obj_orig": rw0["obj_orig"], "rconst": s["rconst"],
            "n_known": len(known["work_orders"]), "n_running": len(site["running"])}
        return s

    def exec_trades(t_d, tuples, res, site):
        live = res.get("_live") or {}
        if res.get("term_feas") != "applied_uncertified" or "schedule" not in live:
            return None
        run_ids = {r[0] for r in site["running"]}
        adj, sched = live["adjusted"], live["schedule"]
        wt = D.trade_wwt_of(adj.instance, sched, skip=run_ids)
        by_t = defaultdict(list)
        for t in tuples or []:
            if t[0] in trade_of and t[0] not in run_ids:
                by_t[trade_of[t[0]]].append(tuple(t))
        trades = sorted({wo["trade"] for wo in adj.instance["work_orders"]
                         if wo["id"] not in run_ids})
        return [[tr, D.fp_of(by_t[tr]) if by_t.get(tr) else D.BASE_FP, wt.get(tr, 0.0)]
                for tr in trades]

    def note_exec(t_d, tuples, res, site, trades=None):
        trades = trades if trades is not None else exec_trades(t_d, tuples, res, site)
        for tr, tfp, v in trades or []:
            k = (t_d, tr, tfp)
            if k not in exec_up or v < exec_up[k]:
                exec_up[k] = v

    def price_td(s, fk, t_d, raw):
        """gen_price on K at t_d, memoised on the strictly parsed operations."""
        K = s["known"]
        s_find, typed, parse = G._stage_schema(K, raw, G_CERT)
        fsum = finding_summary(s_find)
        blocking = any(f.blocking for f in s_find)
        if blocking or typed is None:
            res = D.gen_price(K, raw, s["kf"], s["base_p"], t_d, ref2=True,
                              running_ids=s["run_ids"])
            r = {k: res.get(k) for k in R_KEYS}
            r.update(fp=None, n_ops=None if typed is None else len(typed), findings=fsum,
                     tuples=None, exec_trades=None, typed_key=None, ops=res.get("ops"))
            out["memo"]["direct"] += 1
            return r
        tkey = json.dumps([op.to_dict() for op in typed], sort_keys=True)
        sig = json.dumps(sorted((f.code, f.severity) for f in s_find))
        key = (fk, t_d, tkey, sig, bool(parse.get("ok")))
        hit = memo_dt.get(key)
        if hit is not None:
            out["memo"]["hit"] += 1
            if out["memo"]["hit"] % SPOT_EVERY == 0:
                res = D.gen_price(K, raw, s["kf"], s["base_p"], t_d, ref2=True,
                                  running_ids=s["run_ids"])
                full = {k: res.get(k) for k in R_KEYS}
                if full != {k: hit[k] for k in R_KEYS}:
                    fail("memo spot check on {} t_d={}".format(iid, t_d),
                         "{} vs {}".format(full, {k: hit[k] for k in R_KEYS}))
                out["memo"]["spot_checked"] += 1
            r = dict(hit)
            r["findings"] = fsum
            return r
        res = D.gen_price(K, raw, s["kf"], s["base_p"], t_d, ref2=True, keep_live=True,
                          running_ids=s["run_ids"])
        r = {k: res.get(k) for k in R_KEYS}
        tuples = res["tuples"]
        r.update(fp=None if tuples is None else D.fp_of(tuples), n_ops=len(typed),
                 findings=fsum, tuples=tuples, typed_key=tkey, ops=res.get("ops"),
                 exec_trades=exec_trades(t_d, tuples, res, s["site"]))
        if r["exec_trades"]:
            note_exec(t_d, tuples, res, s["site"], trades=r["exec_trades"])
        if res["stage_cert"] == "qual" and tuples is not None:
            need_boards.setdefault((t_d, r["fp"]), tuples)
        res.pop("_live", None)
        memo_dt[key] = r
        out["memo"]["miss"] += 1
        return dict(r)

    def unguarded_td(s, fk, t_d, raw):
        K = s["known"]
        _s_u, typed_u, _p = G._stage_schema(K, raw, UNGUARDED)
        ukey = (fk, t_d, None if typed_u is None else json.dumps(
            [op.to_dict() for op in typed_u], sort_keys=True))
        if ukey not in memo_ung:
            memo_ung[ukey] = D._unguarded_terminal(K, raw, s["kf"], s["base_p"], None, None)
        return memo_ung[ukey], None if typed_u is None else len(typed_u)

    def realised(s, fk, t_d, raw, typed_key):
        key = (fk, t_d, typed_key)
        if key not in memo_rw:
            rw = D.gen_price(inst, raw, s["frozen_r"], s["base_p"], t_d, keep_batch=s["k_ids"])
            memo_rw[key] = {"rw_term": rw["term_cert"], "rw_term_feas": rw["term_feas"],
                            "rw_obj": rw["obj"], "rw_obj_orig": rw["obj_orig"]}
        return dict(memo_rw[key])

    def names_of(ops, s):
        try:
            explicit, members = n8.named_orders(ops or [], inst)
        except Exception:  # noqa: BLE001 - a malformed logged op list names nothing
            explicit, members = [], []
        return {"names_unknown": sorted(o for o in explicit if o in s["unknown"]),
                "names_completed": sorted(o for o in explicit if o in s["completed"]),
                "names_running": sorted(o for o in explicit if o in s["running"]),
                "n_batch_members": len(members),
                "n_batch_members_known": sum(1 for m in members if m in s["kset"])}

    # ---- per item: issuability, then every reading's verdicts
    for item_id, it in task["items"].items():
        fk, seed = it["fk"], it["seed"]
        traj = trajs[fk]
        starts = {a["wo"]: float(a["start_bh"]) for a in traj["assignments"]}
        iss = D.issuability({"referenced": it["referenced"]}, by_id, starts)
        rec = {k: iss[k] for k in ("n_ref", "t_known", "t_start", "issuable",
                                   "issuable_strict", "ref_all_pm")}
        rec["t_d"] = {rd: D.decision_instant_of(iss, rd) for rd in READINGS}
        rec["readings"] = list(task["readings"])
        out["items"][item_id] = rec
        # Omniscient checks that cost a parse: UNGUARDED n_ops at t = 0.
        for uk, u in it["e1_units"].items():
            _s, typed_u0, _p = G._stage_schema(inst, u["raw"], UNGUARDED)
            n0 = None if typed_u0 is None else len(typed_u0)
            for want in u["ung_n_ops_logged"]:
                if want != n0:
                    fail("omniscient UNGUARDED n_ops on {}".format(item_id),
                         "{} vs logged {}".format(n0, want))
        if it["gold_ops"] is not None:
            gp = {"operations": it["gold_ops"]}
            g0 = D.gen_price(inst, gp, seed, baseline, 0.0, ref2=True)
            out["gold"].setdefault(item_id, {})["t0"] = gold_record(g0)
        if not iss["issuable"]:
            continue
        for rd in task["readings"]:
            t_d = rec["t_d"][rd]
            if rd == "late" and not it["e1_units"]:
                continue
            s = site_for(fk, seed, t_d)
            for uk, u in it["e1_units"].items():
                r = price_td(s, fk, t_d, u["raw"])
                r["term_ung"], r["n_ops_ung"] = unguarded_td(s, fk, t_d, u["raw"])
                r.update(names_of(u["parsed_ops"], s))
                r["dangling"] = "dangling_order_id" in (r["codes"] or [])
                r["rw_term"] = r["rw_term_feas"] = r["rw_obj"] = r["rw_obj_orig"] = None
                if r["term_feas"] == "applied_uncertified":
                    r.update(realised(s, fk, t_d, u["raw"], r["typed_key"]))
                r.pop("tuples", None)
                r.pop("exec_trades", None)
                r.pop("typed_key", None)
                r["t_d"] = t_d
                r.pop("ops", None)
                out["e1"]["{}|{}|{}".format(rd, item_id, uk)] = r
            if rd != "primary":
                continue
            if it["gold_ops"] is not None:
                gt = D.gen_price(s["known"], {"operations": it["gold_ops"]}, s["kf"],
                                 s["base_p"], t_d, ref2=True)
                g = gold_record(gt)
                if gt["term_feas"] == "applied_uncertified":
                    rw = D.gen_price(inst, {"operations": it["gold_ops"]}, s["frozen_r"],
                                     s["base_p"], t_d, keep_batch=s["k_ids"])
                    g["rw_obj_orig"] = rw["obj_orig"]
                out["gold"][item_id]["td"] = g
            for uk, u in it["n3_units"].items():
                payload, flag, flag_findings, note = read_flag(u["raw"])
                v10 = v10_view(u["raw"])
                same = D.raw_key(payload) == D.raw_key(v10)
                m10 = price_td(s, fk, t_d, v10)
                m11 = m10 if same else price_td(s, fk, t_d, payload)
                fb = any(f.blocking for f in flag_findings)
                rec3 = {"m10": slim(m10), "m11": slim(m11), "flag": flag, "flag_blocking": fb,
                        "payload_is_v10": same, "t_d": t_d,
                        "note": {k: note.get(k) for k in ("flag_present", "flag_raw",
                                                          "flag_missing", "flag_type_error")}}
                rec3["rw10"] = (realised(s, fk, t_d, v10, m10["typed_key"])
                                if m10["term_feas"] == "applied_uncertified" else None)
                rec3["rw11"] = (realised(s, fk, t_d, payload, m11["typed_key"])
                                if not fb and m11["term_feas"] == "applied_uncertified" else None)
                rec3.update(names_of(u["ops_logged"], s))
                out["n3"]["{}|{}".format(item_id, uk)] = rec3

    # ---- boards: per trade LB2, ATC, best executed schedule; open-trade inputs
    seen_inputs = set()
    for (t_d, fp), tuples in need_boards.items():
        bs = board_sites[t_d]
        brec, live = D.board_record(inst, iid, bs["site"], tuples)
        for tr, tv in brec["trades"].items():
            ex = exec_up.get((t_d, tr, tv["trade_fp"]))
            tv["exec_upper"] = ex
            ups = [(tv["atc"], "atc")] + ([(ex, "executed")] if ex is not None else [])
            tv["upper0"], tv["upper0_source"] = min(ups)
            tv["closed_by_lb2"] = tv["upper0"] <= tv["lb2"] + D.CLOSE_TOL_BH
            if not tv["closed_by_lb2"]:
                k = (t_d, tr, tv["trade_fp"])
                if k not in seen_inputs:
                    seen_inputs.add(k)
                    ti_ = D.trade_input(live["binst"], live["avail"], tr, live["atc_sched"])
                    ti_.update(iid=iid, t_d=t_d, trade=tr, trade_fp=tv["trade_fp"],
                               lb2=tv["lb2"], atc=tv["atc"], exec_upper=ex,
                               n_orders=tv["n_orders"], n_techs=tv["n_techs"])
                    out["relaxed_inputs"].append(ti_)
        brec["seeds"] = []
        brec["avail_multiset"] = D.avail_multiset(inst, bs["avail"])
        out["boards"].append(brec)
    out["memo"] = dict(out["memo"])
    out["wall_s"] = time.perf_counter() - t0
    return out


def slim(m) -> dict:
    """A priced verdict without the board-side fields, plus its typed operations."""
    r = {k: m.get(k) for k in R_KEYS + ("fp", "n_ops", "findings", "ops")}
    r["typed_key"] = m.get("typed_key")
    return r


def gold_record(g) -> dict:
    gap = g["gap"] if g["stage_cert"] == "qual" else None
    rel2 = (D.rel_delta(g["obj"], g["ref2"]) if g["term_feas"] == "applied_uncertified"
            and g["ref2"] is not None else None)
    union = None if gap is None and rel2 is None else max(p for p in (gap, rel2) if p is not None)
    return {"cert": gap, "rel2": rel2, "union": union, "feas_terminal": g["term_feas"],
            "cert_terminal": g["term_cert"], "obj_orig": g["obj_orig"], "codes": g["codes"]}


# --------------------------------------------------------------------------- #
# N3 dispositions through the published function, from plain priced values    #
# --------------------------------------------------------------------------- #
class _F:
    def __init__(self, code, stage, blocking=True):
        self.code, self.stage, self.blocking = code, stage, blocking


class _Cert:
    def __init__(self, gap):
        self.gap = gap


class _Verdict:
    """The attributes of a guard verdict that ``n3_evaluate`` reads, from a priced record."""

    def __init__(self, terminal, codes, gap, schema_blocked):
        self.terminal = terminal
        fs = []
        for c in codes or []:
            stage = "qual" if c in QUAL_CODES else ("schema" if schema_blocked else "feas")
            fs.append(_F(c, stage))
        if schema_blocked and not fs:
            fs.append(_F("schema_invalid", "schema"))
        self.findings = fs
        self.certificate = None if gap is None else _Cert(gap)


def n3_disposition(d, gold_ops, m10, m11, flag, flag_blocking, note, gold, anchor, exec10,
                   exec11, raw, refusal):
    """``n3_evaluate._disposition`` on priced values (t = 0 or t_d)."""
    import n3_evaluate as n3e

    row = {k: d[k] for k in ("item_id", "item_set", "arm", "mode", "thinking", "repeat",
                             "instance_id", "stratum", "register", "subclass", "twin_id",
                             "primary_class")}
    row["gold_ops"] = gold_ops
    gold_intent = bool(d["gold_intent"])
    if refusal:
        measures = n3e.flag_measures("", None, None)
        return n3e._disposition(row, None, None, None, None, n3e.MODEL_REFUSED, gold,
                                gold_intent, None, anchor, None, None, measures, v12=None)
    feas11_t = "blocked_schema" if flag_blocking else m11["term_feas"]
    schema11 = feas11_t == "blocked_schema"
    gap11 = None if flag_blocking or m11["stage_cert"] != "qual" else m11["gap"]
    rel11 = (D.rel_delta(m11["obj"], m11["ref2"]) if feas11_t == "applied_uncertified"
             and m11["ref2"] is not None else None)
    feas = _Verdict(feas11_t, [] if feas11_t in APPLIED else (
        m11["codes"] if not flag_blocking else ["schema_invalid"]), None, schema11)
    rel2 = ({"delta": rel11, "reference_from": m11["ref2_from"]} if feas11_t ==
            "applied_uncertified" else {"delta": None, "reference_from": "not_reached"})
    from l1guard.config import POLICIES_V11, TAU_HARD_V11
    from l1guard.guard_v11 import policy_terminal

    pol = POLICIES_V11["P_CERT_V11"].with_(tau_hard=TAU_HARD_V11)
    live = policy_terminal(pol, feas11_t, flag, gap11, rel11)["terminal"]
    measures = n3e.flag_measures(raw, flag, feas)
    gap10 = m10["gap"] if m10["stage_cert"] == "qual" else None
    rel10 = (D.rel_delta(m10["obj"], m10["ref2"]) if m10["term_feas"] == "applied_uncertified"
             and m10["ref2"] is not None else None)
    cert10 = _Verdict(m10["term_cert"], m10["codes"], gap10, m10["term_cert"] == "blocked_schema")
    v12 = {"feas_terminal": m10["term_feas"], "cert_terminal": m10["term_cert"], "cert10": cert10,
           "gap": gap10, "rel2": {"delta": rel10}, "executed": exec10,
           "blocking_codes": [] if m10["term_feas"] in APPLIED else sorted(m10["codes"] or [])}
    ops = m11.get("ops")
    return n3e._disposition(row, feas, gap11, rel2, flag, live, gold, gold_intent, note, anchor,
                            exec11, ops, measures, v12=v12)


def disp_equal(a, b, tol=1e-6) -> list:
    """The keys on which two disposition records differ (floats within tol)."""
    bad = []

    def eq(x, y):
        if isinstance(x, float) or isinstance(y, float):
            return x is not None and y is not None and abs(float(x) - float(y)) <= tol
        if isinstance(x, dict) and isinstance(y, dict):
            return set(x) == set(y) and all(eq(x[k], y[k]) for k in x)
        if isinstance(x, (list, tuple)) and isinstance(y, (list, tuple)):
            return len(x) == len(y) and all(eq(p, q) for p, q in zip(x, y))
        return x == y

    for k in set(a) | set(b):
        if k in ("live_cert_agrees", "live_cert_agrees_v12"):
            continue
        if not eq(a.get(k), b.get(k)):
            bad.append(k)
    return sorted(bad)


# --------------------------------------------------------------------------- #
# e2e driver                                                                   #
# --------------------------------------------------------------------------- #
def n3_gold_ops(check) -> dict:
    out = {}
    for src in D.N3_SOURCES:
        for p in D.read_jsonl(RESULTS / src / "proposals_raw.dedup.jsonl"):
            g = p.get("gold_ops")
            prev = out.setdefault(p["item_id"], g)
            check.true("A1", "N3 gold ops agree across rows of " + p["item_id"], prev == g)
    return out


def omni_gate(check):
    rep = json.loads((D.OUT / "omni_assertions.json").read_text())
    meta = json.loads((D.OUT / "omni_meta.json").read_text())
    check.true("A4", "omniscient reproduction (omni stage) passed", rep.get("status") == "PASS",
               rep.get("status"))
    now = D._inputs_wo_runner()
    rec = {k: v for k, v in meta["inputs"].items() if k in now}
    check.true("A4", "omni stage ran on the current inputs", rec == now,
               sorted(k for k in now if rec.get(k) != now[k]))
    return rep, meta


def cmd_e2e(args) -> int:
    global _E2E
    D.pin_cores(args.cores_t)
    D.cap_threads(1)
    out_dir = ensure_dir(E2E_OUT / "smoke" if args.instances else E2E_OUT)
    if getattr(args, "out_dir", ""):
        # Stage 3: the late-reading replay goes to its own folder, so Stage 2's
        # primary outputs stay as they were written.
        out_dir = ensure_dir(Path(args.out_dir) / ("smoke" if args.instances else ""))
    check = D.Checker()
    t_start = time.time()
    readings = tuple(x for x in args.readings.split(",") if x)
    if not readings or set(readings) - set(READINGS) or readings[0] != "primary":
        raise SystemExit("REFUSING TO RUN: --readings must start with primary, got {}"
                         .format(readings))
    for name, path in (("census", D.OUT / "census_assertions.json"),
                       ("census late", D.OUT / "late" / "census_assertions.json")):
        if name == "census late" and "late" not in readings:
            continue
        rep = json.loads(path.read_text())
        check.true("A1", "{} stage passed".format(name), rep.get("status") == "PASS")
    omni_rep, omni_meta = omni_gate(check)
    pub = OrderedDict((r["item_id"], r) for r in D.load_published(check))
    ext = D.load_ext(check)
    e1rows = D.load_e1(check)
    n3rows = D.load_n3(check)
    gold_ops = n3_gold_ops(check)
    anchors = D.load_anchor_records()

    # ---- the omniscient pool results (proved current by the omni stage)
    with open(D.OUT / "omni_pool_cache.pkl", "rb") as fh:
        cache = pickle.load(fh)
    res_e1, res_n3 = {}, {}
    for res in cache["results"]:
        res_e1.update(res["e1"])
        res_n3.update(res["n3"])

    # ---- N3 dispositions at t = 0 through the published function (shim check)
    gold_pub = {}
    for src in D.N3_SOURCES:
        for g in D.read_jsonl(RESULTS / src / "gold_prices.jsonl"):
            gold_pub.setdefault(g["item_id"], g)
    from l1guard.guard_v11 import read_flag
    n_disp = 0
    for r in n3rows:
        d = r["disp"]
        it = item_of(r["item_id"], pub, ext)
        r["instance_id"] = it["instance"]["instance_id"]
        r["fk"] = D.frozen_key(r["frozen"])
        a = anchors[(r["instance_id"], r["fk"])]
        check.close("A7", "N3 anchor equals the published anchor on " + r["item_id"],
                    d["anchor_bh"], float(a["wwt_original_bh"]), D.CHECK_TOL)
        gpub = gold_pub[r["item_id"]]
        gold = {"prices": gpub["prices"]}
        if r["outcome"] == "refusal":
            got = n3_disposition(d, gold_ops[r["item_id"]], None, None, None, None, None, gold,
                                 d["anchor_bh"], None, None, "", True)
        else:
            uk = D.sha_text(json.dumps([r["instance_id"], r["fk"], D.raw_key(r["raw"])]))
            r["ukey"] = uk
            m = res_n3[uk]
            m10 = dict(m)
            m11 = dict(m.get("v11") or m)
            # The omniscient pool does not keep the typed operations; at t = 0
            # the logged ones are used (the disposition's ``ops`` field only).
            m11["ops"] = d["ops"]
            _p, flag, _ff, note = read_flag(r["raw"])
            e10 = m10["obj_orig"] if m10["term_feas"] == "applied_uncertified" else None
            fb = m["flag_blocking"]
            e11 = m11["obj_orig"] if (not fb and m11["term_feas"] == "applied_uncertified") \
                else None
            got = n3_disposition(d, gold_ops[r["item_id"]], m10, m11, m["flag"], fb, note, gold,
                                 d["anchor_bh"], e10, e11, r["raw"], False)
        bad = disp_equal(got, d)
        check.true("A4", "N3 disposition rebuilt at t = 0 on {}|{}|{}|{}".format(
            r["src"], d["item_id"], d["mode"], d.get("repeat")), not bad, bad[:6])
        n_disp += 1
    check.true("A4", "N3 dispositions rebuilt at t = 0 = 14560", n_disp == 14560, n_disp)
    if check.failures:
        check.fatal(out_dir / "e2e_assertions.json", {"stage": "pre-replay"})

    # ---- tasks per instance
    tasks = OrderedDict()

    def task_for(it):
        iid = it["instance"]["instance_id"]
        if iid not in tasks:
            tasks[iid] = {"iid": iid, "path": D.instance_path(it), "items": OrderedDict(),
                          "seeds": OrderedDict()}
        t = tasks[iid]
        seed = list(it["episode"]["frozen_seed"] or [])
        fk = D.frozen_key(seed)
        t["seeds"].setdefault(fk, seed)
        if it["item_id"] not in t["items"]:
            t["items"][it["item_id"]] = {"fk": fk, "seed": seed, "referenced": it["referenced"],
                                         "e1_units": OrderedDict(), "n3_units": OrderedDict(),
                                         "gold_ops": None}
        return t["items"][it["item_id"]], iid

    ung_logged = defaultdict(list)
    for src in D.E1_SOURCES:
        for v in D.read_jsonl(RESULTS / src / "verdicts_UNGUARDED.jsonl"):
            ung_logged[(src, v["item_id"], v["mode"], v.get("thinking"),
                        int(v["repeat"]))] = v
    for r in e1rows:
        it = pub[r["item_id"]]
        tk, iid = task_for(it)
        r["instance_id"] = iid
        r["primary_class"] = it["primary_class"]
        r["stratum"] = it["instance"]["stratum"]
        if r["v"]["G_CERT"]["terminal"] == "model_refused":
            continue
        uk = D.raw_key(r["raw"])
        r["ukey2"] = uk
        u = tk["e1_units"].setdefault(uk, {"raw": r["raw"], "parsed_ops": r["parsed_ops"],
                                           "ung_n_ops_logged": []})
        vu = ung_logged[(r["src"], r["item_id"], r["mode"], r["thinking"], r["repeat"])]
        check.true("A4", "logged UNGUARDED row carries no instrument fault: " + r["item_id"],
                   not vu["infra"])
        if vu.get("n_ops") not in u["ung_n_ops_logged"]:
            u["ung_n_ops_logged"].append(vu.get("n_ops"))
    for r in n3rows:
        it = item_of(r["item_id"], pub, ext)
        tk, iid = task_for(it)
        tk["gold_ops"] = gold_ops[r["item_id"]]
        if r["outcome"] == "refusal":
            continue
        tk["n3_units"].setdefault(r["ukey"], {"raw": r["raw"], "ops_logged": r["disp"]["ops"]})
    if args.instances:
        keep = set(args.instances.split(","))
        tasks = OrderedDict((k, v) for k, v in tasks.items() if k in keep)
    for t in tasks.values():
        t["readings"] = readings
    _E2E = list(tasks.values())
    n_e1u = sum(len(i["e1_units"]) for t in _E2E for i in t["items"].values())
    n_n3u = sum(len(i["n3_units"]) for t in _E2E for i in t["items"].values())
    print("[n11 e2e] {} instances, {} E1 inputs, {} N3 inputs; workers {} on {}".format(
        len(_E2E), n_e1u, n_n3u, args.workers, args.cores_t), flush=True)
    order = sorted(range(len(_E2E)), key=lambda i: (
        0 if "c10_storm" in _E2E[i]["iid"] else 1 if "c09_storm" in _E2E[i]["iid"] else 2,
        -sum(len(x["e1_units"]) for x in _E2E[i]["items"].values())))
    results = D.run_pool(e2e_instance, len(_E2E), args.cores_t, args.workers, order)
    wall = time.time() - t_start

    # ---- assemble and assert
    items, e1u, n3u, gold, sites, boards, rel_inputs = {}, {}, {}, {}, {}, [], []
    memo = Counter()
    for res in sorted(results, key=lambda r: r["iid"]):
        for what, detail in res["checks"]:
            check.true("A4", what, False, detail)
        items.update(res["items"])
        e1u.update({(res["iid"], k): v for k, v in res["e1"].items()})
        n3u.update(res["n3"])
        gold.update(res["gold"])
        sites.update({(res["iid"],) + tuple(k.split("|")): v for k, v in res["sites"].items()})
        boards.extend(res["boards"])
        rel_inputs.extend(res["relaxed_inputs"])
        memo.update(res["memo"])
    run_checks_e2e(check, items, e1u, n3u, gold, sites, boards, e1rows, n3rows, pub, ext,
                   anchors, res_e1, gold_pub, bool(args.instances), readings)
    rows_e1 = {rd: [] for rd in readings}
    for r in e1rows:
        if r["item_id"] not in items or not items[r["item_id"]]["issuable"]:
            continue
        for rd in readings:
            base = {"src": r["src"], "item_id": r["item_id"], "mode": r["mode"],
                    "thinking": r["thinking"], "repeat": r["repeat"],
                    "instance_id": r["instance_id"], "frozen_seed": D.frozen_key(r["frozen"]),
                    "t_d": items[r["item_id"]]["t_d"][rd], "reading": rd}
            if r["v"]["G_CERT"]["terminal"] == "model_refused":
                base["model_refused"] = True
            else:
                base["model_refused"] = False
                base.update(e1u[(r["instance_id"], "{}|{}|{}".format(rd, r["item_id"],
                                                                     r["ukey2"]))])
            rows_e1[rd].append(base)
    for rd in readings:
        D.write_jsonl(out_dir / "rows_e1_{}.jsonl".format(rd), rows_e1[rd])
    rows_n3 = []
    for r in n3rows:
        if r["item_id"] not in items or not items[r["item_id"]]["issuable"]:
            continue
        rec = {"src": r["src"], "item_id": r["item_id"], "instance_id": r["instance_id"],
               "frozen_seed": r["fk"], "t_d": items[r["item_id"]]["t_d"]["primary"],
               "refusal": r["outcome"] == "refusal", "disp_key": [
                   r["disp"]["arm"], r["disp"]["item_id"], r["disp"]["mode"],
                   r["disp"].get("thinking"), r["disp"].get("repeat")]}
        if not rec["refusal"]:
            rec.update(n3u["{}|{}".format(r["item_id"], r["ukey"])])
        rows_n3.append(rec)
    D.write_jsonl(out_dir / "rows_n3.jsonl", rows_n3)
    D.write_jsonl(out_dir / "items.jsonl", [dict(item_id=k, **v) for k, v in items.items()])
    D.write_jsonl(out_dir / "gold.jsonl", [dict(item_id=k, **v) for k, v in gold.items()])
    D.write_jsonl(out_dir / "sites.jsonl", [dict(iid=k[0], fk=k[1], t_d=float(k[2]), **v)
                                            for k, v in sites.items()])
    D.write_jsonl(out_dir / "boards.jsonl", boards)
    D.write_jsonl(out_dir / "relaxed_inputs.jsonl", rel_inputs)
    meta = {"version": VERSION, "stage": "e2e", "finished": D.now_iso(), "wall_s": wall,
            "cores": args.cores_t, "workers": args.workers,
            "omp_num_threads": os.environ.get("OMP_NUM_THREADS"), "load_avg_end": D.loadavg(),
            "frozen_set": "fix", "readings": readings, "memo": dict(memo),
            "e1_inputs": n_e1u, "n3_inputs": n_n3u, "boards": len(boards),
            "open_relaxed_trades": len(rel_inputs),
            "omni_stage": {"finished": omni_meta.get("finished"),
                           "cache_provenance": omni_meta.get("cache_provenance"),
                           "n_checks": omni_rep.get("n_checks")},
            "inputs": D.input_hashes(),
            "code": {"n11_stage2.py": D.sha256_file(Path(__file__))},
            "outputs": {p.name: D.sha256_file(p) for p in sorted(out_dir.glob("*.jsonl"))}}
    D.write_json(out_dir / "e2e_meta.json", meta)
    check.fatal(out_dir / "e2e_assertions.json", {"finished": meta["finished"],
                                                 "outputs": meta["outputs"]})
    print("[n11 e2e] PASS: {} checks in {:.0f}s; memo {}".format(
        check.report()["n_checks"], wall, dict(memo)), flush=True)
    return 0


def run_checks_e2e(check, items, e1u, n3u, gold, sites, boards, e1rows, n3rows, pub, ext,
                   anchors, res_e1, gold_pub, smoke, readings=READINGS):
    """A1, A3, A5 (gold), A7, A8, A9, A12 and the dangling-identifier rule on the e2e outputs."""
    # ---- A3: issuability agrees with the census on every published item
    census = {r["item_id"]: r for r in D.read_jsonl(D.OUT / "items.jsonl")}
    late = {r["item_id"]: r for r in D.read_jsonl(D.OUT / "late" / "items.jsonl")}
    for iid_, it in items.items():
        c = census.get(iid_)
        if c is not None:
            check.true("A3", "e2e issuability equals the census on " + iid_,
                       c["issuable"] == it["issuable"] and abs(c["t_d"] - it["t_d"]["primary"])
                       <= 1e-12, "{} {}".format(c["issuable"], it["issuable"]))
            lc = late.get(iid_)
            if "late" in readings:
                check.true("A3", "e2e late instant equals the late census on " + iid_,
                           lc is not None and abs(lc["t_d"] - it["t_d"]["late"]) <= 1e-12)
    if not smoke:
        n_pub_ne = sum(1 for k, v in items.items() if k in census and not v["issuable"])
        check.true("A3", "published items not issuable = 277", n_pub_ne == 277, n_pub_ne)
    # ---- A5: omniscient gold prices equal N3's gold_prices.jsonl
    for iid_, g in gold.items():
        gp = gold_pub.get(iid_)
        if gp is None:
            continue
        g0 = g["t0"]
        for k in ("cert", "rel2", "union"):
            check.close("A5", "omniscient gold price {} on {}".format(k, iid_), g0[k],
                        gp["prices"][k], D.CHECK_TOL)
        check.true("A5", "omniscient gold G_FEAS terminal on " + iid_,
                   g0["feas_terminal"] == gp["feas_terminal"],
                   "{} vs {}".format(g0["feas_terminal"], gp["feas_terminal"]))
        if gp.get("gold_obj_original_bh") is not None:
            check.close("A5", "omniscient gold original-field objective on " + iid_,
                        g0["obj_orig"], gp["gold_obj_original_bh"], D.CHECK_TOL)
    # ---- A7: the no-proposal realised run is the published anchor, every site
    for (iid, fk, t_d), s in sites.items():
        a = anchors[(iid, fk)]
        check.close("A7", "no-proposal realised run equals the anchor on {} [{}] t_d={}".format(
            iid, fk, t_d), s["rw0_obj_orig"], float(a["wwt_original_bh"]), D.CHECK_TOL)
        check.close("A7", "no-proposal realised run (adjusted) equals the anchor on {} t_d={}"
                    .format(iid, t_d), s["rw0_obj"], float(a["wwt_adjusted_bh"]), D.CHECK_TOL)
        if s["an_lb"] is not None:
            check.true("A9", "anchor LB_K <= obj_K on {} t_d={}".format(iid, t_d),
                       s["an_lb"] <= s["an_obj"] + D.CHECK_TOL)
    # ---- per E1 row: dangling rule, A8 at t_d = 0, A9
    n_a8 = 0
    for r in e1rows:
        if r["item_id"] not in items or not items[r["item_id"]]["issuable"]:
            continue
        if r["v"]["G_CERT"]["terminal"] == "model_refused":
            continue
        for rd in readings:
            u = e1u[(r["instance_id"], "{}|{}|{}".format(rd, r["item_id"], r["ukey2"]))]
            tag = "{} {}|{}|{}|{}|{}".format(rd, r["src"], r["item_id"], r["mode"], r["thinking"],
                                             r["repeat"])
            if u["names_unknown"] and u["parse_ok"] is not False:
                check.true("A3", "a proposal naming an order unknown at t_d is refused at "
                           "schema as dangling: " + tag,
                           u["term_cert"] == "blocked_schema" and u["dangling"],
                           "{} {}".format(u["term_cert"], u["codes"]))
            if u["lb"] is not None and u["obj"] is not None:
                check.true("A9", "LB_K <= obj_K on " + tag, u["lb"] <= u["obj"] + D.CHECK_TOL)
            m = res_e1.get(D.sha_text(json.dumps([r["instance_id"], D.frozen_key(r["frozen"]),
                                                  D.raw_key(r["raw"])])))
            if (rd == "primary" and u["t_d"] == 0.0 and m is not None
                    and m["term_feas"] == "applied_uncertified"
                    and u["term_feas"] == "applied_uncertified"
                    and u["n_batch_members_known"] == u["n_batch_members"]
                    and r["log_obj_orig"] is not None):
                n_a8 += 1
                check.close("A8", "realised original-field objective at t_d = 0 equals the "
                            "logged full-window objective on " + tag, u["rw_obj_orig"],
                            r["log_obj_orig"], D.CHECK_TOL)
    check.true("A8", "A8 rows compared > 0", n_a8 > 0 or smoke, n_a8)
    D.CENSUS_COUNTS["e2e_a8_rows"] = n_a8
    # ---- A9 / A12 on the boards
    for b in boards:
        check.true("A9", "board ATC dispatch is feasible: {} t_d={} {}".format(
            b["iid"], b["t_d"], b["fp"][:10]), b["atc_feasible"])
        for tr, tv in b["trades"].items():
            check.true("A9", "LB2 <= upper on {} t_d={} {} {}".format(
                b["iid"], b["t_d"], b["fp"][:10], tr), tv["lb2"] <= tv["upper0"] + D.CHECK_TOL)
    # ---- A12 on every priced proposal (E1 and N3): its board's running constant
    # is the certificate's, and the board's LB2 sum plus that constant is LB_K.
    bkey = {(b["iid"], float(b["t_d"]), b["fp"]): b for b in boards}
    priced_units = [(k[0], k[1], u) for k, u in e1u.items()]
    for k, u in n3u.items():
        iid_ = item_of(k.split("|")[0], pub, ext)["instance"]["instance_id"]
        for m in (u["m10"], u["m11"]):
            priced_units.append((iid_, k, dict(m, t_d=u["t_d"])))
    n_a12 = 0
    for iid_, key, u in priced_units:
        if u.get("model_refused") or u.get("stage_cert") != "qual" or u.get("fp") is None:
            continue
        b = bkey.get((iid_, float(u["t_d"]), u["fp"]))
        check.true("A12", "proposal board exists for {} {}".format(iid_, key), b is not None)
        if b is None:
            continue
        n_a12 += 1
        check.close("A12", "proposal board running constant equals LB_K's on {} {}".format(
            iid_, key), b["running_const"], u["lb_running"], D.CHECK_TOL)
        lo = sum(tv["lb2"] for tv in b["trades"].values()) + b["running_const"]
        check.close("A12", "proposal board LB2 sum equals LB_K on {} {}".format(iid_, key),
                    lo, u["lb"], D.CHECK_TOL)
    D.CENSUS_COUNTS["e2e_a12_units"] = n_a12
    base_b = {(b["iid"], float(b["t_d"])): b for b in boards if b["fp"] == D.BASE_FP}
    for (iid, fk, t_d), s in sites.items():
        b0 = base_b.get((iid, float(t_d)))
        check.true("A12", "anchor board exists for {} t_d={}".format(iid, t_d), b0 is not None)
        if b0 is None or s["an_lb"] is None:
            continue
        lb2 = sum(tv["lb2"] for tv in b0["trades"].values())
        check.close("A12", "anchor board LB2 + running constant equals LB_K on {} t_d={}".format(
            iid, t_d), lb2 + b0["running_const"], s["an_lb"], D.CHECK_TOL)


# --------------------------------------------------------------------------- #
# analyse2, part 1: the E1 twin evaluation folders (published schema)          #
# --------------------------------------------------------------------------- #
CONFIGS3 = ("G_CERT", "G_FEAS", "UNGUARDED")
TWIN = E2E_OUT / "twin"


def e1_key(src, item_id, mode, thinking, repeat):
    return (src, item_id, mode, thinking, int(repeat))


def load_logged_e1():
    """Per source: proposals and the three verdict logs, aligned line by line."""
    out = OrderedDict()
    for src in D.E1_SOURCES:
        d = RESULTS / src
        props = D.read_jsonl(d / "proposals.jsonl")
        vs = {c: D.read_jsonl(d / "verdicts_{}.jsonl".format(c)) for c in CONFIGS3}
        out[src] = (props, vs)
    return out


def td_verdicts(base, u):
    """The three verdict rows of one E1 row at t_d, in the logged schema."""
    cert, feas, ung = (dict(base[c]) for c in CONFIGS3)
    if u is None or u.get("model_refused"):
        return cert, feas, ung
    schema_f = list(u["findings"] or [])
    have = {f["code"] for f in schema_f}

    def later(codes):
        return [{"stage": "qual" if c in QUAL_CODES else "feas", "code": c,
                 "severity": "violation"} for c in codes if c not in have]

    codes = list(u["codes"] or [])
    qual = u["stage_cert"] == "qual"
    cert.update(terminal=u["term_cert"], stage_reached=u["stage_cert"], blocking_codes=codes,
                infra=bool(u["infra"]), n_ops=u["n_ops"], parse_ok=bool(u["parse_ok"]),
                fingerprint=None, findings=schema_f + later(codes),
                certificate_gap=u["gap"] if qual else None,
                certificate=({"accepted": u["term_cert"] == "applied_with_certificate",
                              "gap": u["gap"], "lb_bh": u["lb"], "obj_bh": u["obj"],
                              "tier": "tier2"} if qual and u["gap"] is not None else None))
    fcodes = [] if u["term_feas"] in APPLIED else [c for c in codes if c not in QUAL_CODES]
    feas.update(terminal=u["term_feas"], stage_reached=u["stage_feas"], blocking_codes=fcodes,
                infra=bool(u["infra"]) and u["stage_cert"] in ("schema", "feas"),
                n_ops=u["n_ops"], parse_ok=bool(u["parse_ok"]), fingerprint=None,
                findings=schema_f + later(fcodes), certificate_gap=None, certificate=None)
    ung.update(terminal=u["term_ung"], n_ops=u["n_ops_ung"], blocking_codes=[], infra=False,
               fingerprint=None, certificate=None, certificate_gap=None)
    return cert, feas, ung


def analysis_rows(props, vs, keep):
    """``e1_evaluate.Analysis`` inputs from logged proposals and (twin) verdict rows."""
    rows, results = [], []
    for i in keep:
        p = props[i]
        ex = p.get("extra") or {}
        rows.append({"arm": ex.get("arm"), "mode": p["mode"], "thinking": ex.get("thinking"),
                     "repeat": ex.get("repeat"), "primary_class": ex.get("primary_class"),
                     "subclass": ex.get("subclass"), "gold_ops": ex.get("gold_ops"),
                     "item_id": p["instruction_id"], "raw_output": p.get("raw_output"),
                     "usage": {}, "latency_ms": p.get("latency_ms"),
                     "finish_reason": p.get("finish_reason")})
        j = len(rows) - 1
        results.append({"i": j, "record": {"parsed_ops": p.get("parsed_ops")},
                        "verdicts": {c: vs[c][i] for c in CONFIGS3}})
    return rows, results


def summary_groups(props, vs, keep):
    import e1_evaluate as e1

    rows, results = analysis_rows(props, vs, keep)
    a = e1.Analysis(rows, results)
    return json.loads(json.dumps(a.all_groups()))


GROUP_KEYS = ("arm", "mode", "thinking", "repeat", "pooled", "n_rows", "terminals", "infra",
              "blocks", "separation", "separation_by_subclass", "translation",
              "constraint_tax", "gaps")


def write_twin_root(root, logged, td_rows, issuable):
    """One folder per E1 source in the published schema, issuable rows at t_d.

    ``td_rows=None`` writes the logged (t = 0) verdicts of the issuable rows,
    which separates the population change from the decision-instant change.
    """
    use_logged = td_rows is None
    by_key = {}
    for r in td_rows or []:
        by_key[e1_key(r["src"], r["item_id"], r["mode"], r["thinking"], r["repeat"])] = r
    counts = {}
    for src, (props, vs) in logged.items():
        d = ensure_dir(root / src)
        keep, tv = [], {c: [] for c in CONFIGS3}
        for i, p in enumerate(props):
            ex = p.get("extra") or {}
            k = e1_key(src, p["instruction_id"], p["mode"], ex.get("thinking"),
                       ex.get("repeat", 0))
            if not issuable.get(p["instruction_id"]):
                continue
            u = by_key.get(k)
            if u is None and not use_logged:
                raise SystemExit("A4 FAILURE: no decision-time row for {}".format(k))
            c, f, g = td_verdicts({cc: vs[cc][i] for cc in CONFIGS3}, u)
            keep.append(i)
            tv["G_CERT"].append(c)
            tv["G_FEAS"].append(f)
            tv["UNGUARDED"].append(g)
        D.write_jsonl(d / "proposals.jsonl", [props[i] for i in keep])
        for cc in CONFIGS3:
            D.write_jsonl(d / "verdicts_{}.jsonl".format(cc), tv[cc])
        n = len(keep)
        groups = summary_groups([props[i] for i in keep], {cc: tv[cc] for cc in CONFIGS3},
                                list(range(n)))
        D.write_json(d / "summary.json", {"groups": groups, "n11": {
            "reading": root.name, "rows": n, "rows_logged": len(props)}})
        counts[src] = (n, len(props))
    return counts


def build_tables(results_root, out_dir, provenance):
    """paper_tables T1, T2, T3, T6, D1, D2 on one results root (published builders)."""
    import ladder_replay as lr
    import paper_tables as pt

    ensure_dir(out_dir)
    summaries = pt.load_summaries(results_root)
    tables = pt.Tables(out_dir, provenance)
    rec = lr.Reconciler()
    for name, title, fn in (
            ("T1_e1_main", "T1", lambda: pt.build_t1(summaries, rec)),
            ("T2_enforcement_ladder", "T2", lambda: pt.build_t2(summaries, rec)),
            ("T3_guard_value_curve", "T3", lambda: pt.build_t3(summaries, rec)),
            ("T6_tau_calibration", "T6", lambda: pt.build_t6(results_root, rec)),
            ("D1_v3_separation_breakdown", "D1", lambda: pt.build_d1(results_root)),
            ("D2_class_disposition", "D2", lambda: pt.build_d2(results_root))):
        headers, rows, md = fn()
        tables.write(name, title, headers, rows, md)
    return rec


def csv_body(path):
    """The data lines of a CSV with its # provenance lines removed."""
    return [ln for ln in Path(path).read_text().splitlines() if not ln.startswith("#")]


# ---- D3 (the published script runs on import, so its two rules are restated
# here verbatim and asserted to reproduce analysis/D3_translation_equivalence.csv)
D3_ARMS = [
    ("qwen3-14b", RESULTS / "grid_e1_local" / "proposals_raw.jsonl"),
    ("qwen3.6-27b-fp8", RESULTS / "grid_e1_local_27b" / "proposals_raw.jsonl"),
    ("glm-4-9b", RESULTS / "grid_e1_local_glm9b" / "proposals_raw.jsonl"),
    ("mini", RESULTS / "grid_e1_hosted_openai" / "proposals_raw.jsonl"),
    ("sonnet", RESULTS / "grid_e1_hosted_sonnet" / "proposals_raw.jsonl"),
    ("opus", RESULTS / "grid_e1_hosted_opus" / "proposals_raw.dedup.jsonl"),
    ("sol", RESULTS / "grid_e1_hosted_sol" / "proposals_raw.jsonl"),
]


def _d3_norm_op(o):
    o = dict(o)
    for k, v in list(o.items()):
        if isinstance(v, float) and v == int(v):
            o[k] = int(v)
    if o.get("op") == "reorder" and o.get("relation") == "after":
        o["order_id"], o["ref_order_id"] = o.get("ref_order_id"), o.get("order_id")
        o["relation"] = "before"
    return json.dumps(o, sort_keys=True)


def _d3_equiv(emitted, gold):
    if not emitted:
        return False
    return sorted(_d3_norm_op(o) for o in emitted) == sorted(_d3_norm_op(o) for o in gold)


def _d3_ops_of(t):
    try:
        return json.loads(t).get("operations")
    except Exception:  # noqa: BLE001 - the published rule
        return None


def d3_rows(suite, keep=None):
    """[arm, benign_equiv, V3_equiv, V4_equiv] as D3 prints them, on ``keep`` items."""
    out, counts = [], {}
    for arm, rawp in D3_ARMS:
        raw = {}
        for line in open(rawp):
            r = json.loads(line)
            if r["mode"] != "M_constrained" or r.get("repeat") != 0:
                continue
            if r.get("thinking") not in (None, "disabled", "none"):
                continue
            raw[r["item_id"]] = r
        eq, n = Counter(), Counter()
        for iid_, r in raw.items():
            s = suite.get(iid_)
            if not s or (keep is not None and not keep.get(iid_)):
                continue
            cls = s["primary_class"]
            if cls not in ("V3", "V4", "benign"):
                continue
            n[cls] += 1
            if _d3_equiv(_d3_ops_of(r.get("raw_output") or ""), s["gold_ops"]):
                eq[cls] += 1
        out.append([arm] + ["{}/{} ({:.0%})".format(eq[c], n[c], eq[c] / n[c]) if n[c] else "-"
                            for c in ("benign", "V3", "V4")])
        counts[arm] = {c: (eq[c], n[c]) for c in ("benign", "V3", "V4")}
    return out, counts


def write_d3(path, rows, note):
    import csv as _csv

    with open(path, "w", newline="") as f:
        w = _csv.writer(f)
        w.writerow(["# D3 equivalence-aware translation fidelity; " + note])
        w.writerow(["# normalisation: numeric type unified; reorder relation inverted to "
                    "canonical 'before'"])
        w.writerow(["arm", "benign_equiv", "V3_equiv", "V4_equiv"])
        for r in rows:
            w.writerow(r)


# --------------------------------------------------------------------------- #
# analyse2, part 2: paper_macros builders on patched sources                   #
# --------------------------------------------------------------------------- #
def run_pm_builder(builder, patches, before=()):
    """[(name, body, comment)] of one paper_macros builder with SOURCES patched.

    ``before`` names builders run first into the same accumulator (some builders
    compare against macros an earlier group emitted); only ``builder``'s own
    macros are returned.
    """
    import paper_macros as pm

    saved = dict(pm.SOURCES)
    try:
        for k, v in patches.items():
            pm.SOURCES[k] = Path(v)
        pm._CACHE.clear()
        m = pm.Macros()
        for b in before:
            getattr(pm, b)(m)
        n0 = len(m.groups)
        getattr(pm, builder)(m)
        return [(n, b, c) for _t, _note, entries in m.groups[n0:] for (n, b, c) in entries]
    finally:
        pm.SOURCES.clear()
        pm.SOURCES.update(saved)
        pm._CACHE.clear()


def published_macros() -> dict:
    return D.load_macros(D.PUBLISHED_MACRO_FILES + ("manuscript/macros_n3.tex",
                                                    "manuscript/macros_n10.tex"))


def manuscript_tokens() -> set:
    """Every macro name the manuscript sources use."""
    toks = set()
    man = ROOT / "manuscript"
    for p in list(man.glob("drafts/*.tex")) + [man / "main.tex", man / "supplement.tex"]:
        if p.is_file():
            toks.update(re.findall(r"\\([A-Za-z]+)", p.read_text(errors="replace")))
    return toks


def twin_name(published, late=False):
    return ("nElevenLate" if late else "nEleven") + published[:1].upper() + published[1:]


# --------------------------------------------------------------------------- #
# analyse2, part 3: DG17 (the 5.1 damage sentences) with the published code    #
# --------------------------------------------------------------------------- #
def dg17_logged_cells():
    """``e1_delta_guard_replay.load_cell_rows`` on the published logs: the static columns."""
    import e1_delta_guard_replay as e1dg
    import passthrough_rule as pr

    check = e1dg.Checker()
    anchors, _paths, anchor_gaps = e1dg.load_anchors(check)
    suite_ops = pr.load_suite_ops(e1dg.SUITE_PATH)
    cells = OrderedDict()
    for arm, dirname in e1dg.ARM_DIRS.items():
        for row in e1dg.load_cell_rows(arm, dirname, anchors, anchor_gaps, suite_ops,
                                       D.SNAPSHOT_ROOT, check):
            row["src"] = dirname
            cells.setdefault((row["arm"], row["thinking"]), []).append(row)
    if check.failures:
        raise SystemExit("DG17 loader assertions failed: {}".format(check.failures[:5]))
    return cells


def dg17_fill(r):
    import e1_delta_guard_replay as e1dg

    if r["reached_qual"]:
        r["unit_key"] = (r["path"], r["frozen"], json.dumps(r["ops"], sort_keys=True,
                                                             separators=(",", ":")))
    r["delta"] = {rule: e1dg.compute_delta(r, rule) for rule in e1dg.RULES}


def dg17_headline(cells, n_boot, policies=None):
    """The DG17 headline records (published selection, metrics and intervals)."""
    import hashlib as _h

    import numpy as np
    import e1_delta_guard_replay as e1dg

    policies = policies or (e1dg.PRIMARY_POLICY,)
    all_rows = [r for rows in cells.values() for r in rows]
    instances = sorted({r["instance_id"] for r in all_rows})
    inst_index = {iid: i for i, iid in enumerate(instances)}
    k_clusters = len(instances)
    arrays = OrderedDict((cell, e1dg.Cell(rows, inst_index)) for cell, rows in cells.items())
    selections = {}
    for cell, ca in arrays.items():
        for policy in policies:
            family, scheme, budget_kind = e1dg.POLICIES[policy]
            entry = {"per_base": {}}
            fold_masks, fold_ids = e1dg.build_folds(ca, scheme, e1dg.SEED)
            for base in ("feas", "cert"):
                folds, best_of = {}, {}
                for fold in fold_ids:
                    eval_mask = fold_masks[fold]
                    calib_mask = ~eval_mask
                    if budget_kind == "cert":
                        blocked, n_benign, _v3, _v = e1dg.counts_at(ca, "cert", None, None,
                                                                    calib_mask)
                        budget = blocked / n_benign if n_benign else 0.0
                    else:
                        budget = e1dg.FB_BUDGET_FIXED
                    if base == "feas":
                        chosen = {rule: e1dg.tightest_meeting_budget(ca, base, rule, budget,
                                                                     calib_mask)
                                  for rule in e1dg.RULES}
                        best = e1dg.pick_best_rule(ca, base, chosen, calib_mask)
                    else:
                        chosen = dict(entry["per_base"]["feas"]["folds"][fold])
                        best = entry["per_base"]["feas"]["best"][fold]
                    folds[fold] = chosen
                    best_of[fold] = best
                entry["per_base"][base] = {"folds": folds, "best": best_of,
                                           "fold_masks": fold_masks, "fold_ids": fold_ids}
            selections[(cell, policy)] = entry
    headline = []
    for cell, ca in arrays.items():
        rows = cells[cell]
        seed_cell = (e1dg.SEED + int(_h.sha256(("|".join(cell)).encode("utf-8"))
                                     .hexdigest()[:8], 16)) % (2 ** 31)
        rng = np.random.default_rng(seed_cell)
        boot_idx = rng.integers(0, k_clusters, size=(n_boot, k_clusters))
        for config, (base, rule) in e1dg.CONFIGS.items():
            for policy in (["fixed"] if rule is None else list(policies)):
                if rule is None:
                    blocked = ca.blocked(base, None, None)
                    setting_txt = "tau=0.20" if base == "cert" else "no quality stage"
                    n_infeasible, rule_used = 0, ""
                    rule_of_row = np.array([""] * ca.n, dtype=object)
                else:
                    sel = selections[(cell, policy)]["per_base"][base]
                    blocked = np.zeros(ca.n, dtype=bool)
                    rule_of_row = np.array([""] * ca.n, dtype=object)
                    rules_used, parts, n_infeasible = set(), [], 0
                    for fold in sel["fold_ids"]:
                        m = sel["fold_masks"][fold]
                        use_rule = sel["best"][fold] if rule == "D-BEST" else rule
                        setting, feasible = sel["folds"][fold][use_rule]
                        blocked |= m & ca.blocked(base, use_rule, setting)
                        rule_of_row[m] = use_rule
                        rules_used.add(use_rule)
                        parts.append("{}={}".format(fold, e1dg.setting_label(use_rule, setting)))
                        n_infeasible += int(not feasible)
                    rule_used = "/".join(sorted(rules_used))
                    setting_txt = " ".join(parts)
                vec = e1dg.metric_vectors(ca, blocked, config in e1dg.BOUND_CONFIGS)
                rec = OrderedDict()
                rec["block"] = "headline"
                rec["arm"] = cell[0]
                rec["model"] = e1dg.MODEL_LABEL[cell[0]]
                rec["thinking"] = cell[1]
                rec["in_capability_set"] = cell in e1dg.CAPABILITY_SET
                rec["config"] = config
                rec["base"] = base
                rec["rule"] = rule or ""
                rec["rule_used"] = rule_used
                rec["policy"] = policy
                rec["policy_family"] = "logged" if rule is None else e1dg.POLICIES[policy][0]
                rec["fold_scheme"] = "" if rule is None else e1dg.POLICIES[policy][1]
                rec["setting_kind"] = "" if rule is None else e1dg.RULE_KIND.get(rule, "mixed")
                rec["settings_per_fold"] = setting_txt
                rec["n_folds_budget_infeasible"] = n_infeasible
                rec["n_rows"] = len(rows)
                rec["n_instances"] = len(set(r["instance_id"] for r in rows))
                for metric in e1dg.METRIC_ORDER:
                    numv, denv = vec[metric]
                    den_total, num_total = float(denv.sum()), float(numv.sum())
                    rec[metric + "_num"] = round(num_total, 6)
                    rec[metric + "_den"] = round(den_total, 6)
                    rec[metric] = (num_total / den_total) if den_total > 0 else None
                    if metric in e1dg.CI_METRICS:
                        a, b = e1dg.cluster_sums(numv, denv, ca.cluster, k_clusters)
                        lo, hi = e1dg.bootstrap_ci(a, b, boot_idx)
                        rec[metric + "_lo"] = lo
                        rec[metric + "_hi"] = hi
                qual = [r for r in rows if r["reached_qual"]]
                if rule is None:
                    naive = cached = 0.0
                else:
                    need, uniq = 0, set()
                    for i, r in enumerate(rows):
                        if not r["reached_qual"]:
                            continue
                        if rule_of_row[i] == "D-REL2":
                            if r["constraining"]:
                                need += 1
                                uniq.add(r["unit_key"])
                        else:
                            need += 1
                            uniq.add((r["path"], r["frozen"]))
                    naive = need / len(rows)
                    cached = len(uniq) / len(rows)
                rec["extra_dispatch_per_instruction"] = round(naive, 6)
                rec["extra_dispatch_per_instruction_cached"] = round(cached, 6)
                rec["v4qv_separated_on_selfblocking_instances"] = int(np.count_nonzero(
                    ca.is_v4qv & ca.feas_applied & blocked & ca.self_blocking))
                rec["benign_false_blocks_on_selfblocking_instances"] = int(np.count_nonzero(
                    ca.is_benign & blocked & ca.self_blocking))
                rec["v3_separated_on_selfblocking_instances"] = int(np.count_nonzero(
                    ca.is_v3 & ca.feas_applied & blocked & ca.self_blocking))
                lb_ms = [r["lb_wall_ms"] for r in qual if r["lb_wall_ms"] is not None]
                rec["cert_lb_wall_ms_median"] = (round(sorted(lb_ms)[len(lb_ms) // 2], 4)
                                                 if (base == "cert" and lb_ms) else "")
                rec["n_quality_reaching"] = len(qual)
                headline.append(rec)
    return headline


def dg17_compare(mine, path, check, label):
    """Every field of the published headline rows the computation covers, compared."""
    pub = [r for r in D.read_csv_comments(path) if r["block"] == "headline"]
    idx = {(r["arm"], r["thinking"], r["config"], r["policy"]): r for r in pub}
    n = 0
    for rec in mine:
        p = idx.get((rec["arm"], rec["thinking"], rec["config"], rec["policy"]))
        check.true("A5", "{}: DG17 headline row exists for {}".format(
            label, (rec["arm"], rec["thinking"], rec["config"], rec["policy"])), p is not None)
        if p is None:
            continue
        for k, v in rec.items():
            pv = p.get(k)
            if isinstance(v, bool):
                ok = str(v) == pv
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                ok = pv not in (None, "") and abs(float(pv) - float(v)) <= 1e-6 * max(1.0, abs(v))
            elif v is None:
                ok = pv in (None, "")
            else:
                ok = str(v) == str(pv)
            check.true("A5", "{}: DG17 {} on {}".format(label, k, (
                rec["arm"], rec["thinking"], rec["config"], rec["policy"])), ok,
                "{!r} vs {!r}".format(v, pv))
        n += 1
    return n


def write_dg17_twin(path, headline, note):
    """The published DG17 file with its headline block replaced by ``headline``."""
    src = ANALYSIS / "DG17_e2e_delta.csv"
    lines = src.read_text().splitlines()
    comments = [ln for ln in lines if ln.startswith("#")]
    body = [ln for ln in lines if not ln.startswith("#")]
    import csv as _csv
    import io

    rdr = list(_csv.reader(io.StringIO("\n".join(body))))
    header = rdr[0]
    keep = [r for r in rdr[1:] if r and r[0] != "headline"]
    buf = io.StringIO()
    w = _csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for rec in headline:
        w.writerow(["" if rec.get(h) is None else rec.get(h) for h in header])
    for r in keep:
        w.writerow(r)
    Path(path).write_text("\n".join(["# N11 twin of DG17_e2e_delta.csv: " + note] + comments)
                          + "\n" + buf.getvalue())


# ---- DG17 macros (build_e1_delta_replay pins the published values with
# asserts, so it cannot run on a twin; its formulas are restated here verbatim
# and asserted to reproduce every published macro they cover at t = 0)
def dg17_macros(csv_path):
    import paper_macros as pm

    rows = [r for r in D.read_csv_comments(csv_path)
            if r["block"] == "headline" and r["in_capability_set"] == "True"]
    PRIMARY, FIXED, FLAG = "heldout_matched_loso", ("G-FEAS", "G-CERT"), ("opus", "default")

    def cells(config):
        pol = "fixed" if config in FIXED else PRIMARY
        sel = [r for r in rows if r["config"] == config and r["policy"] == pol]
        if len(sel) != 8:
            raise SystemExit("DG17 twin: {} has {} capability cells".format(config, len(sel)))
        return sel

    def cell(config):
        return pm.one(cells(config), arm=FLAG[0], thinking=FLAG[1])

    out = OrderedDict()
    out["dgEOneDeltaFlagshipCertVThreeSep"] = pm.pct(cell("G-CERT")["v3_separation"])
    out["dgEOneDeltaFlagshipRelTwoVThreeSep"] = pm.pct(cell("G-FEAS+D-REL2")["v3_separation"])
    out["dgEOneDeltaFlagshipCertFalseBlock"] = pm.pct(cell("G-CERT")["benign_false_block"])
    out["dgEOneDeltaFlagshipRelTwoFalseBlock"] = pm.pct(
        cell("G-FEAS+D-REL2")["benign_false_block"])
    for tok, config in (("Cert", "G-CERT"), ("RelTwo", "G-FEAS+D-REL2"),
                        ("Abs", "G-FEAS+D-ABS"), ("RelOne", "G-FEAS+D-REL1")):
        v3 = [float(r["v3_separation"]) for r in cells(config)]
        fb = [float(r["benign_false_block"]) for r in cells(config)]
        out["dgEOneDelta" + tok + "VThreeSepMin"] = pm.pct(min(v3))
        out["dgEOneDelta" + tok + "VThreeSepMax"] = pm.pct(max(v3))
        out["dgEOneDelta" + tok + "FalseBlockMin"] = pm.pct(min(fb))
        out["dgEOneDelta" + tok + "FalseBlockMax"] = pm.pct(max(fb))
    for tok, config in (("Feas", "G-FEAS"), ("Cert", "G-CERT"), ("RelTwo", "G-FEAS+D-REL2"),
                        ("RelOne", "G-FEAS+D-REL1"), ("Abs", "G-FEAS+D-ABS"),
                        ("Union", "G-CERT+D-REL2")):
        r = cell(config)
        out["dgEOneDeltaFlagship" + tok + "Damage"] = pm.bh(r["mean_excess_bh"], 2, signed=True)
        out["dgEOneDeltaFlagship" + tok + "DamageLo"] = pm.bh(r["mean_excess_bh_lo"], 2,
                                                              signed=True)
        out["dgEOneDeltaFlagship" + tok + "DamageHi"] = pm.bh(r["mean_excess_bh_hi"], 2,
                                                              signed=True)
    out["dgEOneDeltaCertAcceptedAboveTau"] = pm.pct(
        max(float(r["accepted_above_tau"]) for r in cells("G-CERT")))
    for tok, config in (("RelTwo", "G-FEAS+D-REL2"), ("Abs", "G-FEAS+D-ABS"),
                        ("RelOne", "G-FEAS+D-REL1")):
        vals = [float(r["accepted_above_tau"]) for r in cells(config)]
        out["dgEOneDelta" + tok + "AcceptedAboveTauMin"] = pm.pct(min(vals))
        out["dgEOneDelta" + tok + "AcceptedAboveTauMax"] = pm.pct(max(vals))
    union = {(r["arm"], r["thinking"]): r for r in cells("G-CERT+D-REL2")}
    certs = {(r["arm"], r["thinking"]): r for r in cells("G-CERT")}
    uv3 = [float(r["v3_separation"]) for r in union.values()]
    ufb = [float(r["benign_false_block"]) for r in union.values()]
    inc = [(float(union[k]["benign_false_block"]) - float(certs[k]["benign_false_block"]))
           * 100.0 for k in certs]
    out["dgEOneDeltaUnionVThreeSepMin"] = pm.pct(min(uv3))
    out["dgEOneDeltaUnionVThreeSepMax"] = pm.pct(max(uv3))
    out["dgEOneDeltaUnionFalseBlockMin"] = pm.pct(min(ufb))
    out["dgEOneDeltaUnionFalseBlockMax"] = pm.pct(max(ufb))
    out["dgEOneDeltaUnionFalseBlockIncMin"] = "{:+.1f}".format(min(inc))
    out["dgEOneDeltaUnionFalseBlockIncMax"] = "{:+.1f}".format(max(inc))
    out["dgEOneDeltaUnionFlagshipVThreeSep"] = pm.pct(cell("G-CERT+D-REL2")["v3_separation"])
    out["dgEOneDeltaUnionFlagshipFalseBlock"] = pm.pct(
        cell("G-CERT+D-REL2")["benign_false_block"])
    rel2 = [float(r["extra_dispatch_per_instruction_cached"]) for r in cells("G-FEAS+D-REL2")]
    ref = [float(r["extra_dispatch_per_instruction_cached"])
           for c in ("G-FEAS+D-REL1", "G-FEAS+D-ABS") for r in cells(c)]
    out["dgEOneDeltaRelTwoDispatchMin"] = pm.num(min(rel2), 3)
    out["dgEOneDeltaRelTwoDispatchMax"] = pm.num(max(rel2), 3)
    out["dgEOneDeltaRefDispatchMin"] = pm.num(min(ref), 3)
    out["dgEOneDeltaRefDispatchMax"] = pm.num(max(ref), 3)

    def pooled(config, col):
        return (sum(float(r[col + "_num"]) for r in cells(config)),
                sum(float(r[col + "_den"]) for r in cells(config)))

    cert_num, cert_den = pooled("G-CERT", "v4qv_separation")
    best_rule = max(pooled(c, "v4qv_separation")[0]
                    for c in ("G-FEAS+D-REL1", "G-FEAS+D-REL2", "G-FEAS+D-ABS"))
    out["dgEOneDeltaCertVFourQualSep"] = pm.group(cert_num)
    out["dgEOneDeltaVFourQualRows"] = pm.group(cert_den)
    out["dgEOneDeltaBestRuleVFourQualSep"] = pm.group(best_rule)

    def self_block(config, col):
        return sum(int(r[col]) for r in cells(config))

    out["dgEOneDeltaCertVFourQualSelfBlock"] = pm.group(
        self_block("G-CERT", "v4qv_separated_on_selfblocking_instances"))
    out["dgEOneDeltaCertVThreeSelfBlock"] = pm.group(
        self_block("G-CERT", "v3_separated_on_selfblocking_instances"))
    out["dgEOneDeltaCertVThreeSepTotal"] = pm.group(pooled("G-CERT", "v3_separation")[0])
    out["dgEOneDeltaCertFalseBlockSelfBlock"] = pm.group(
        self_block("G-CERT", "benign_false_blocks_on_selfblocking_instances"))
    out["dgEOneDeltaCertFalseBlockTotal"] = pm.group(pooled("G-CERT", "benign_false_block")[0])
    return out


def n10_rows_of(cells, n10_by_key, reading):
    """N10's row schema on DG17 cell rows: t = 0 rows unchanged, t_d rows on K."""
    import n10_field_change as n10
    import n2_pricing as n2

    out = []
    for rows in cells.values():
        for r in rows:
            k = (r["arm"], r["thinking"], r["repeat"], r["item_id"])
            base = n10_by_key[k]
            if reading == "iss0":
                out.append(base)
                continue
            c = dict(base)
            for f in ("feas_terminal", "cert_terminal", "cert_infra", "feas_infra", "gap", "n_ops",
                      "strict_flag", "self_blocking_instance", "reached_qual", "pre_qual_blocked",
                      "other_terminal", "exec_wwt_orig"):
                c[f] = r[f]
            c["split"] = n2.op_split(c["ops"]) if c["reached_qual"] else None
            c["applied"] = bool(c["reached_qual"] and c["gap"] <= n10.TAU)
            if c["reached_qual"]:
                c["damage_if_applied"] = round(c["exec_wwt_orig"] - c["anchor"], n10.ROUND_BH)
                lb = r.get("an_lb_K")
                obj = r.get("obj_orig_K")
                c["g_orig"] = None if lb is None or obj is None else \
                    (obj - lb) / max(lb, n10.FLOOR_BH)
            else:
                c["damage_if_applied"] = None
                c["g_orig"] = None
            out.append(c)
    return out


def n10_twin(M, dg17_cells, issuable, published, used, note_change):
    """N10's field-change table on the e2e rows at t_d (and on the issuable rows at t = 0)."""
    import n10_field_change as n10

    res = n10_published()
    by_key = {(r["arm"], r["thinking"], r["repeat"], r["item_id"]): r for r in res["rows"]}
    vals = {}
    for name, cells in dg17_cells.items():
        rows = n10_rows_of(cells, by_key, name)
        table, joint = n10.build_tables(rows, res["cells"])
        qual = [r for r in rows if r["reached_qual"]]
        large_qual = {"applied": sum(1 for r in qual if r["applied"]
                                     and r["damage_if_applied"] > n10.LARGE_BH),
                      "any": sum(1 for r in qual if r["damage_if_applied"] > n10.LARGE_BH),
                      "items": len({r["item_id"] for r in qual
                                    if r["damage_if_applied"] > n10.LARGE_BH})}
        vals[name] = lines_to_macros(n10.macros(
            table, joint, res["stopped"], res["large"], res["case"], res["sources"], len(rows),
            len(qual), large_qual))
    # The unguarded-replay (``Stopped``), case and ``Large`` macros read the
    # t = 0 patch file of rows stopped before the quality gate; they are not twins.
    t0_only = ("nTenStopped", "nTenCase", "nTenLarge")
    n_tw = n_ch = 0
    for n, v in vals["primary"].items():
        if n not in used or n.startswith(t0_only):
            continue
        M.twin(n, v, "N10 field change (e2e)", note="issuable t=0: {}".format(vals["iss0"].get(n)))
        n_tw += 1
        if published.get(n) != v:
            n_ch += 1
            note_change("N10 field change (e2e)", n, published.get(n), vals["iss0"].get(n), v)
    return n_tw, n_ch, "g_orig on K = (original-field obj_K - LB_K of the unadjusted K) / max(., 1)"


# --------------------------------------------------------------------------- #
# analyse2, part 4: DG9 (E1 strata), DG5 (flagship intervals), N10             #
# --------------------------------------------------------------------------- #
def _dg9_module():
    import importlib.util

    path = ANALYSIS / "DG9_stratum_split.py"
    spec = importlib.util.spec_from_file_location("dg9_stratum_split", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def dg9_split(results_root):
    """DG9's per-stratum split rows, from the verdict logs under ``results_root``."""
    import hashlib as _h

    import numpy as np
    import passthrough_rule as pr

    g = _dg9_module()
    g.RESULTS = Path(results_root)
    suite = g.load_suite()
    suite_ops = pr.load_suite_ops(g.SUITE)
    cells = OrderedDict()
    for arm, dirname in g.ARM_DIRS.items():
        for row in g.load_arm(arm, dirname, suite, suite_ops):
            cells.setdefault((row["arm"], row["thinking"]), []).append(row)
    split_rows = []
    for key in sorted(cells, key=lambda k: (list(g.ARM_DIRS).index(k[0]), k[1])):
        arm, thinking = key
        rows = cells[key]
        n_repeats = len({r["repeat"] for r in rows})
        for metric, (label, _, _) in g.METRICS.items():
            for stratum in list(g.STRATA) + ["ALL"]:
                sub = rows if stratum == "ALL" else [r for r in rows if r["stratum"] == stratum]
                pairs = [(g.metric_row(metric, r), r) for r in sub]
                den = sum(p[0][0] for p in pairs)
                num = sum(p[0][1] for p in pairs)
                point = num / den if den else None
                agg = defaultdict(lambda: [0, 0])
                for (dd, nn), r in pairs:
                    c = agg[r["instance_id"]]
                    c[0] += dd
                    c[1] += nn
                ks = [k for k in sorted(agg) if agg[k][0] > 0]
                den_a = np.array([agg[k][0] for k in ks], dtype=np.float64)
                num_a = np.array([agg[k][1] for k in ks], dtype=np.float64)
                tag = "|".join((arm, thinking, metric, stratum)).encode("utf-8")
                seed = g.SEED + int(_h.sha256(tag).hexdigest()[:8], 16) % 100_000
                lo, hi = g.cluster_bootstrap(num_a, den_a, seed)
                w_lo, w_hi = g.wilson(num, den)
                split_rows.append(OrderedDict([
                    ("arm", arm), ("thinking", thinking), ("model", g.MODEL_LABEL[arm]),
                    ("n_repeats", n_repeats), ("stratum", stratum),
                    ("stratum_label", g.STRATA.get(stratum, "all three strata pooled")),
                    ("metric", metric), ("metric_label", label), ("numerator", num),
                    ("denominator", den),
                    ("point", "" if point is None else "{:.6f}".format(point)),
                    ("point_pct", g.pct(point)), ("n_instances", len(ks)),
                    ("ci_lo_pct", g.pct(lo)), ("ci_hi_pct", g.pct(hi)),
                    ("wilson_lo_pct", g.pct(w_lo)), ("wilson_hi_pct", g.pct(w_hi)),
                    ("B", g.B), ("seed", seed)]))
    return split_rows


def write_rows_csv(path, rows, note):
    import csv as _csv

    with open(path, "w", newline="") as f:
        f.write("# " + note + "\n")
        w = _csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)


def rows_equal_csv(mine, path) -> list:
    """Keys (row index, column) where ``mine`` differs from the published CSV."""
    pub = D.read_csv_comments(path)
    bad = []
    if len(pub) != len(mine):
        return [("rows", len(mine), len(pub))]
    for i, (a, b) in enumerate(zip(mine, pub)):
        for k, v in a.items():
            if str(v) != str(b.get(k)):
                bad.append((i, k, v, b.get(k)))
    return bad


DG5_NEED = (("benign_false_block_gcert", ("opus", "default")),
            ("v3_separation", ("opus", "default")))


def dg5_intervals(results_root):
    """DG5's instance-clustered intervals for the cells and metrics the manuscript quotes."""
    import hashlib as _h

    import numpy as np
    import e1_intervals as e1i
    import passthrough_rule as pr

    e1i.RESULTS = Path(results_root)
    suite_ops = pr.load_suite_ops(e1i.SUITE)
    cells = OrderedDict()
    for arm, dirname in e1i.ARM_DIRS.items():
        for row in e1i.load_arm(arm, dirname, suite_ops):
            cells.setdefault((row["arm"], row["thinking"]), []).append(row)
    points = {}
    for key, rows in cells.items():
        for metric in ("benign_false_block_gcert", "v3_separation"):
            dd = sum(e1i.metric_row(metric, r)[0] for r in rows)
            nn = sum(e1i.metric_row(metric, r)[1] for r in rows)
            points[(key, metric)] = (nn / dd if dd else None, nn, dd)
    out = OrderedDict()
    want = list(DG5_NEED)
    vals = OrderedDict((k, points[(k, "benign_false_block_gcert")][0])
                       for k in sorted(e1i.CAPABILITY_SET)
                       if points[(k, "benign_false_block_gcert")][0] is not None)
    roles = {"min": min(vals, key=vals.get), "max": max(vals, key=vals.get)}
    for role, k in roles.items():
        want.append(("benign_false_block_gcert", k))
    for metric, (arm, thinking) in want:
        rows = cells[(arm, thinking)]
        pairs = [(e1i.metric_row(metric, r), r) for r in rows]
        agg = defaultdict(lambda: [0, 0])
        for (dd, nn), r in pairs:
            c = agg[e1i.cluster_key("instance", r)]
            c[0] += dd
            c[1] += nn
        ks = sorted(agg)
        den = np.array([agg[k][0] for k in ks], dtype=np.float64)
        num = np.array([agg[k][1] for k in ks], dtype=np.float64)
        keep = den > 0
        den, num = den[keep], num[keep]
        tag = "|".join((arm, thinking, metric, "instance")).encode("utf-8")
        seed = e1i.SEED + int(_h.sha256(tag).hexdigest()[:8], 16) % 100_000
        lo, hi, _se, _reps = e1i.cluster_bootstrap(num, den, seed)
        p, nn, dd = points[((arm, thinking), metric)]
        out[(metric, arm, thinking)] = {"ci_lo_pct": e1i.pct(lo), "ci_hi_pct": e1i.pct(hi),
                                        "point": p, "num": nn, "den": dd,
                                        "n_clusters": int(den.shape[0]), "seed": seed}
    return out, roles


def n10_published():
    import e1_delta_guard_replay as e1dg
    import n10_field_change as n10

    check = e1dg.Checker()
    res = n10.compute(check)
    if check.failures:
        raise SystemExit("N10 assertions failed: {}".format(check.failures[:5]))
    return res


def n10_macro_lines(res, table, joint, large_qual):
    import n10_field_change as n10

    return n10.macros(table, joint, res["stopped"], res["large"], res["case"], res["sources"],
                      res["n_rows"], res["n_qual"], large_qual)


def lines_to_macros(lines) -> OrderedDict:
    pat = re.compile(r"\\newcommand\{\\([A-Za-z]+)\}\{(.*)\}\s*$")
    out = OrderedDict()
    for ln in lines:
        m = pat.match(ln.strip())
        if m:
            out[m.group(1)] = m.group(2)
    return out


# --------------------------------------------------------------------------- #
# analyse2, part 5: the table cells the manuscript prints as literals          #
# --------------------------------------------------------------------------- #
#: Table 11 (tab:e1): display name, T3 arm, T3 thinking, macro token, D3 arm.
TAB11 = (("Qwen3-14B", "qwen3-14b", "-", "QwenFourteen", "qwen3-14b"),
         ("Qwen3.6-27B-FP8", "qwen3.6-27b-fp8", "-", "QwenTwentySeven", "qwen3.6-27b-fp8"),
         ("GLM-4-9B-0414", "glm-4-9b", "-", "Glm", "glm-4-9b"),
         ("GPT-5.4-mini", "openai", "-", "Mini", "mini"),
         ("Claude Sonnet 5", "sonnet", "disabled", "Sonnet", "sonnet"),
         ("Claude Opus 5", "opus", "default", "Opus", "opus"),
         ("Claude Opus 5 (no think)", "opus", "disabled", "OpusNoThink", None),
         ("GPT-5.6 Sol", "sol", "none", "Sol", "sol"),
         ("DeepSeek V4-Pro", "deepseek", "non_think", "Deepseek", None),
         ("DeepSeek V4-Pro (think)", "deepseek", "think_high", "DeepseekThink", None))
TAB11_COLS = ("VThreeFeas", "VThreeReferred", "VFour", "VFive", "VSix", "BenignFeas",
              "BenignCert", "VThreeFidelity")
#: Table 13 (tab:enforce): label, display, T2 enforcement, arm, mode, thinking, token.
TAB13 = (
    ("none", "Qwen3-14B", "none", "qwen3-14b", "M_free", "-", "FreeQwenFourteen"),
    ("none", "Qwen3.6-27B-FP8", "none", "qwen3.6-27b-fp8", "M_free", "-", "FreeQwenTwentySeven"),
    ("none", "GLM-4-9B-0414", "none", "glm-4-9b", "M_free", "-", "FreeGlm"),
    ("none", "GPT-5.4-mini", "none", "openai", "M_free", "-", "FreeMini"),
    ("none", "DeepSeek V4-Pro", "none", "deepseek", "M_free", "non_think", "FreeDeepseek"),
    ("none", "DeepSeek V4-Pro (think)", "none", "deepseek", "M_free", "think_high",
     "FreeDeepseekThink"),
    ("none", "Claude Sonnet 5", "none", "sonnet", "M_free", "disabled", "FreeSonnet"),
    ("none", "Claude Opus 5", "none", "opus", "M_free", "default", "FreeOpus"),
    ("none", "Claude Opus 5 (no think)", "none", "opus", "M_free", "disabled",
     "FreeOpusNoThink"),
    ("JSON object", "DeepSeek V4-Pro", "json_object", "deepseek", "M_constrained", "non_think",
     "JsonDeepseek"),
    ("JSON object", "DeepSeek V4-Pro (think)", "json_object", "deepseek", "M_constrained",
     "think_high", "JsonDeepseekThink"),
    ("grammar", "Qwen3-14B", "xgrammar", "qwen3-14b", "M_constrained", "-", "GrammarQwenFourteen"),
    ("grammar", "Qwen3.6-27B-FP8", "xgrammar", "qwen3.6-27b-fp8", "M_constrained", "-",
     "GrammarQwenTwentySeven"),
    ("grammar", "GLM-4-9B-0414", "xgrammar", "glm-4-9b", "M_constrained", "-", "GrammarGlm"),
    ("schema", "GPT-5.4-mini", "json_schema", "openai", "M_constrained", "-", "SchemaMini"),
    ("schema", "Claude Sonnet 5", "json_schema", "sonnet", "M_constrained", "disabled",
     "SchemaSonnet"),
    ("schema", "Claude Opus 5", "json_schema", "opus", "M_constrained", "default", "SchemaOpus"),
    ("schema", "Claude Opus 5 (no think)", "json_schema", "opus", "M_constrained", "disabled",
     "SchemaOpusNoThink"),
    ("schema", "GPT-5.6 Sol", "json_schema", "sol", "M_constrained", "none", "SchemaSol"))
TAB13_COLS = (("OffShape", 2), ("SchemaValid", 2), ("BlockedSchema", 1), ("SilentNoop", 1),
              ("TranslationExact", 1))


def _f(x):
    return None if x in (None, "", "-") else float(x)


def pct_cell(x, d=1):
    return "n/a" if x is None else "{:.{}f}\\%".format(100.0 * x, d)


def tex_table_rows(label, fname="s6_results.tex"):
    """The data rows of a manuscript table, as lists of cell strings (bold removed)."""
    text = (ROOT / "manuscript" / "drafts" / fname).read_text()
    for m in re.finditer(r"\\begin\{table\*?\}(.*?)\\end\{table\*?\}", text, re.S):
        if "\\label{%s}" % label not in m.group(1):
            continue
        body = m.group(1).split("\\midrule", 1)[1].split("\\bottomrule")[0]
        rows = []
        for ln in body.split("\\\\"):
            ln = ln.replace("\\midrule", "").strip()
            if "&" not in ln:
                continue
            rows.append([re.sub(r"\\textbf\{(.*?)\}", r"\1", c).strip() for c in ln.split("&")])
        return rows
    raise SystemExit("table {} not found in {}".format(label, fname))


def read_csv_rows(path):
    return D.read_csv_comments(path)


def d3_map(path):
    return {r["arm"]: r for r in read_csv_rows(path)}


def tab11_values(t3_path, d3_path):
    t3 = {(r["arm"], r["thinking"]): r for r in read_csv_rows(t3_path)
          if r["mode"] == "M_constrained"}
    d3 = d3_map(d3_path)
    out = OrderedDict()
    for disp, arm, th, tok, d3k in TAB11:
        r = t3.get((arm, th))
        if r is None:
            out[tok] = (disp, [None] * len(TAB11_COLS), {})
            continue
        n, fp = int(r["v3_items"]), int(r["v3_feas_pass"])
        vals = [(n - fp) / n if n else None, _f(r["v3_separation_share"]),
                _f(r["v4_block_rate"]), _f(r["v5_block_rate"]), _f(r["v6_block_rate"]),
                _f(r["benign_false_block_gfeas"]), _f(r["benign_false_block_gcert"])]
        fid = None
        if d3k and d3k in d3:
            a, b = d3[d3k]["V3_equiv"].split(" ")[0].split("/")
            fid = int(a) / int(b) if int(b) else None
        vals.append(fid)
        out[tok] = (disp, vals, {"v3_items": n, "v3_feas_pass": fp,
                                 "v3_separated": int(r["v3_separated"])})
    return out


def tab13_values(t2_path):
    t2 = {(r["enforcement"], r["arm"], r["mode"], r["thinking"]): r
          for r in read_csv_rows(t2_path)}
    out = OrderedDict()
    for lab, disp, enf, arm, mode, th, tok in TAB13:
        r = t2.get((enf, arm, mode, th))
        if r is None:
            out[tok] = (lab, disp, [None] * len(TAB13_COLS), {})
            continue
        vals = [_f(r["json_invalid_share"]) + _f(r["wrong_shape_share"]),
                _f(r["schema_valid_share"]), _f(r["gcert_blocked_schema_share"]),
                _f(r["unguarded_silent_noop_share"]), _f(r["benign_translation_exact_rate"])]
        out[tok] = (lab, disp, vals, {"items": int(r["items"])})
    return out


def check_literal_table(check, label, published_vals, cols_digits, label_cols=1):
    """The published CSV values, formatted as the table prints them, equal the .tex cells.

    The public release does not carry the manuscript text; without the draft the check is
    skipped and says so."""
    if not (ROOT / "manuscript" / "drafts" / "s6_results.tex").is_file():
        print("[n11 analyse2] {}: the results draft s6_results.tex is not shipped, so the check "
              "against the printed table is skipped".format(label), flush=True)
        return
    rows = tex_table_rows(label)
    specs = list(published_vals.items())
    check.true("A5", "{}: {} rows in the manuscript, {} in the spec".format(
        label, len(rows), len(specs)), len(rows) == len(specs), (len(rows), len(specs)))
    for cells_, (tok, rec) in zip(rows, specs):
        vals = rec[-2]
        for j, (v, d) in enumerate(zip(vals, cols_digits)):
            want = cells_[label_cols + j]
            got = pct_cell(v, d)
            check.true("A5", "{} cell {} col {} reproduces the printed value".format(
                label, tok, j), got == want, "{} vs printed {}".format(got, want))


def literal_twin_macros(M, stem, specs_pub, specs_iss, specs_td, cols, digits, exhibit):
    """Macros and comparison rows for a literal table: published, issuable at t = 0, t_d."""
    rows = []
    for tok in specs_pub:
        vp, vi, vt = specs_pub[tok][-2], specs_iss[tok][-2], specs_td[tok][-2]
        for j, col in enumerate(cols):
            name = "nEleven{}{}{}".format(stem, tok, col)
            M.add(name, pct_cell(vt[j], digits[j]), exhibit=exhibit,
                  note="published cell {}; issuable t=0 {}".format(
                      pct_cell(vp[j], digits[j]), pct_cell(vi[j], digits[j])))
            rows.append(OrderedDict(exhibit=exhibit, row=tok, column=col,
                                    published=pct_cell(vp[j], digits[j]),
                                    issuable_t0=pct_cell(vi[j], digits[j]),
                                    decision_time=pct_cell(vt[j], digits[j]), macro=name))
    return rows


# --------------------------------------------------------------------------- #
# analyse2, part 6: builder macros on a twin root                              #
# --------------------------------------------------------------------------- #
def e1_patches(root, tables):
    p = {k: tables / (n + ".csv") for k, n in (
        ("T1", "T1_e1_main"), ("T2", "T2_enforcement_ladder"), ("T3", "T3_guard_value_curve"),
        ("T6", "T6_tau_calibration"), ("D1", "D1_v3_separation_breakdown"),
        ("D2", "D2_class_disposition"), ("D3", "D3_translation_equivalence"),
        ("DG9", "DG9_stratum_split"), ("DG17", "DG17_e2e_delta"))}
    for src in D.E1_SOURCES:
        p["e1_" + src[len("e1_eval_"):]] = root / src / "summary.json"
    return p


def source_rel(path):
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def twin_builder_macros(builder, patches, before=()):
    """(name, body, comment, twinned) of one builder on patched sources.

    A macro is a twin when its comment names a patched source and no
    sub-block other than DG17's headline; one whose comment names only
    unpatched sources is a t = 0 quantity and is reported, not twinned.
    """
    import paper_macros as pm

    pub_paths = {k: source_rel(v) for k, v in pm.SOURCES.items()}
    patched = {pub_paths[k] for k in patches if k in pub_paths}
    every = set(pub_paths.values())
    out = []
    for n, b, c in run_pm_builder(builder, patches, before=before):
        hits = {p for p in every if p and p in c}
        blk = re.findall(r"block=(\w+)", c)
        twinned = bool(hits & patched) and all(x == "headline" for x in blk)
        out.append((n, b, c, twinned))
    return out


# --------------------------------------------------------------------------- #
# analyse2, part 7: DG17 rows at t_d                                           #
# --------------------------------------------------------------------------- #
def dg17_td_cells(cells_logged, td_by_key, site_by, issuable, check):
    """The DG17 cell rows of the issuable items with every guard column at t_d."""
    import e1_delta_guard_replay as e1dg
    import passthrough_rule as pr

    suite_ops = pr.load_suite_ops(e1dg.SUITE_PATH)
    out = OrderedDict()
    for cell, rows in cells_logged.items():
        new = []
        for r0 in rows:
            if not issuable.get(r0["item_id"]):
                continue
            r = dict(r0)
            u = td_by_key.get((r["src"], r["item_id"], e1dg.thinking_label(r["thinking_raw"]),
                               int(r["repeat"])))
            check.true("A4", "DG17 row has its decision-time row: {} {}".format(cell, r["item_id"]),
                       u is not None)
            if u is None:
                continue
            if u.get("model_refused"):
                # The logged terminal stands (the proposer returned nothing to judge).
                check.true("A4", "DG17 model-refused row never reached the quality stage: {} {}"
                           .format(cell, r["item_id"]), not r["reached_qual"])
                r["obj_adj"], r["ref1"], r["ref2"] = None, r["anchor"], None
                r["exec_wwt_orig"] = r["anchor"]
                dg17_fill(r)
                new.append(r)
                continue
            s = site_by[(r["instance_id"], D.frozen_key(r["frozen"]), float(u["t_d"]))]
            tf, tc = u["term_feas"], u["term_cert"]
            reached = tf in e1dg.APPLIED_STATES
            gap = u["gap"] if u["stage_cert"] == "qual" else None
            check.true("A4", "DG17 t_d row: G_FEAS applies exactly when a gap exists: {} {}".format(
                cell, r["item_id"]), reached == (gap is not None), "{} {}".format(tf, gap))
            n_ops = u["n_ops"] or 0
            lists = suite_ops.get(r["item_id"], {})
            applied = pr.applied_ops(r["ops"], n_ops)
            r.update(
                feas_terminal=tf, cert_terminal=tc, cert_infra=bool(u["infra"]),
                feas_infra=bool(u["infra"]) and u["stage_cert"] in ("schema", "feas"),
                gap=gap, n_ops=n_ops,
                strict_flag=bool(pr.counts_as_pass_through(
                    r["primary_class"], True, applied, lists.get("gold_ops"),
                    lists.get("trap_ops"), lists.get("forbidden_ops"), strict=True)),
                self_blocking_instance=(s["an_gap"] is not None
                                        and s["an_gap"] > e1dg.TAU_PUBLISHED),
                reached_qual=reached, pre_qual_blocked=tf in e1dg.PRE_QUAL_BLOCKS,
                other_terminal=(tf not in e1dg.APPLIED_STATES
                                and tf not in e1dg.BLOCKED_STATES))
            if reached:
                check.true("A4", "DG17 t_d row: executed proposal has its realised run: {} {}"
                           .format(cell, r["item_id"]), u["rw_obj_orig"] is not None)
                r["obj_adj"] = u["obj"]
                r["obj_orig_K"] = u["obj_orig"]
                r["an_lb_K"] = s["an_lb"]
                r["ref1"] = s["an_obj"]
                r["ref2"] = u["ref2"]
                r["exec_wwt_orig"] = r["anchor"] if n_ops == 0 else u["rw_obj_orig"]
            else:
                r["obj_adj"] = None
                r["ref1"] = r["anchor"]
                r["ref2"] = None
                r["exec_wwt_orig"] = r["anchor"]
            dg17_fill(r)
            new.append(r)
        out[cell] = new
    return out


def dg17_t0_cells(cells_logged, res_e1, e1rows, pub, issuable=None):
    """The published DG17 fill (t3 reproduction), optionally on the issuable items."""
    m_of = {}
    for r in e1rows:
        if r["mode"] != "M_constrained":
            continue
        iid = pub[r["item_id"]]["instance"]["instance_id"]
        uk = D.sha_text(json.dumps([iid, D.frozen_key(r["frozen"]), D.raw_key(r["raw"])]))
        m_of[(D.SRC_TO_ARM[r["src"]], D.thinking_label(r["thinking"]), r["repeat"],
              r["item_id"])] = res_e1.get(uk)
    out = OrderedDict()
    for cell, rows in cells_logged.items():
        new = []
        for r0 in rows:
            if issuable is not None and not issuable.get(r0["item_id"]):
                continue
            r = dict(r0)
            if not r["reached_qual"]:
                r["obj_adj"], r["ref1"], r["ref2"] = None, r["anchor"], None
                r["exec_wwt_orig"] = r["anchor"]
            else:
                m = m_of[(r["arm"], r["thinking"], r["repeat"], r["item_id"])]
                r["obj_adj"], r["ref1"], r["ref2"] = r["obj_adj_logged"], r["anchor"], m["ref2"]
                r["exec_wwt_orig"] = r["anchor"] if r["n_ops"] == 0 else r["obj_orig_logged"]
            dg17_fill(r)
            new.append(r)
        out[cell] = new
    return out


# --------------------------------------------------------------------------- #
# analyse2, part 8: N3 twin evaluation folders                                 #
# --------------------------------------------------------------------------- #
def write_n3_twin(root, rows_n3, gold, issuable, check, use_logged=False):
    """Published-schema N3 evaluation folders on the issuable items (t_d or logged)."""
    from l1guard.guard_v11 import read_flag

    by = {}
    for r in rows_n3 or []:
        by[(r["src"],) + tuple(r["disp_key"])] = r
    gold_ops = {}
    dirs = []
    for src in D.N3_SOURCES:
        d_in = RESULTS / src
        d_out = ensure_dir(root / src)
        raws = D.read_jsonl(d_in / "proposals_raw.dedup.jsonl")
        for p in raws:
            gold_ops.setdefault(p["item_id"], p.get("gold_ops"))
        keep_raw = [p for p in raws if issuable.get(p["item_id"])]
        raw_of = {(p["arm"], p["item_id"], p["mode"], p.get("thinking"), p.get("repeat")):
                  p.get("raw_output") or "" for p in raws}
        disp_out = []
        for d in D.read_jsonl(d_in / "dispositions.jsonl"):
            if not issuable.get(d["item_id"]):
                continue
            if use_logged:
                disp_out.append(d)
                continue
            k = (src, d["arm"], d["item_id"], d["mode"], d.get("thinking"), d.get("repeat"))
            u = by.get(k)
            check.true("A4", "N3 decision-time row for {}".format(k), u is not None)
            if u is None:
                continue
            g = gold[d["item_id"]]["td"]
            gd = {"prices": {"cert": g["cert"], "rel2": g["rel2"], "union": g["union"]}}
            if u["refusal"]:
                got = n3_disposition(d, gold_ops[d["item_id"]], None, None, None, None, None, gd,
                                     d["anchor_bh"], None, None, "", True)
            else:
                raw = raw_of[(d["arm"], d["item_id"], d["mode"], d.get("thinking"),
                              d.get("repeat"))]
                m10, m11 = u["m10"], u["m11"]
                e10 = None if u["rw10"] is None else u["rw10"]["rw_obj_orig"]
                e11 = None if u["rw11"] is None else u["rw11"]["rw_obj_orig"]
                note = dict(u["note"])
                got = n3_disposition(d, gold_ops[d["item_id"]], m10, m11, u["flag"],
                                     u["flag_blocking"], note, gd, d["anchor_bh"], e10, e11,
                                     raw, False)
            got["n11_t_d"] = u["t_d"]
            disp_out.append(got)
        D.write_jsonl(d_out / "dispositions.jsonl", disp_out)
        D.write_jsonl(d_out / "proposals_raw.dedup.jsonl", keep_raw)
        meta = json.loads((d_in / "run_meta.json").read_text())
        meta["n11"] = {"reading": "logged t = 0, issuable items" if use_logged
                       else "decision instant t_d = t_known, issuable items",
                       "rows": len(disp_out)}
        D.write_json(d_out / "run_meta.json", meta)
        dirs.append(d_out)
    return dirs


def run_n3_analyze(eval_dirs, out_dir, log):
    pos = [str(p) for p in eval_dirs if not p.name.startswith("n3neg_")]
    neg = [str(p) for p in eval_dirs if p.name.startswith("n3neg_")]
    cmd = [sys.executable, str(Path(SCRIPTS_DIR) / "n3_analyze.py"), "--eval"] + pos + \
        ["--out-dir", str(out_dir), "--macros", "--neg-eval"] + neg
    ensure_dir(out_dir)
    with open(log, "w") as fh:
        rc = subprocess.call(cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=str(ROOT))
    if rc != 0:
        raise SystemExit("n3_analyze failed ({}); see {}".format(rc, log))
    return lines_to_macros((Path(out_dir) / "N3_macros.tex").read_text().splitlines())


# --------------------------------------------------------------------------- #
# analyse2, part 9: end-to-end pricing rows at t_d (N2 schema)                 #
# --------------------------------------------------------------------------- #
def published_rows_file(fn, issuable_ids=None):
    """D.published_rows on any N2 row file."""
    out = []
    bools = ("quality_visible", "constraining", "same_as_base", "covered", "covered_m", "point",
             "proved_all")
    keep_str = ("dataset", "row_id", "item_id", "primary_class", "subclass", "stratum",
                "instance_id", "arm", "thinking", "mode", "repeat", "split", "reference_from",
                "fingerprint")
    for r in D.read_csv_comments(ANALYSIS / fn):
        if issuable_ids is not None and r["item_id"] not in issuable_ids:
            continue
        c = {}
        for k, v in r.items():
            if k in keep_str:
                c[k] = v
            elif k in bools:
                c[k] = v == "True"
            else:
                c[k] = D.num_or_none(v)
        lo, up = c.get("opt_lower"), c.get("opt_upper")
        if c["covered"]:
            if c["point"]:
                c["_lo_e"] = c["_up_e"] = 0.5 * (lo + up)
            else:
                c["_lo_e"], c["_up_e"] = lo, up
        out.append(c)
    return out


def e2e_pricing_rows(td_rows, logged, pub, site_by, td_br, full_br, anchors, fp_t0, check):
    """One row per E1 row whose certificate priced it at t_d, in N2's e2e schema."""
    import e1_delta_guard_replay as e1dg
    import n2_pricing as n2

    ops_by = {}
    for src, (props, _vs) in logged.items():
        for p in props:
            ex = p.get("extra") or {}
            ops_by[e1_key(src, p["instruction_id"], p["mode"], ex.get("thinking"),
                          ex.get("repeat", 0))] = p.get("parsed_ops") or []
    rows = []
    for u in td_rows:
        if u.get("model_refused") or u["stage_cert"] != "qual":
            continue
        it = pub[u["item_id"]]
        iid, t_d = u["instance_id"], float(u["t_d"])
        s = site_by[(iid, u["frozen_seed"], t_d)]
        ops = ops_by[e1_key(u["src"], u["item_id"], u["mode"], u["thinking"], u["repeat"])]
        a = anchors[(iid, u["frozen_seed"])]
        anchor_pub = float(a["wwt_original_bh"])
        th = e1dg.thinking_label(u["thinking"])
        r = OrderedDict(
            dataset="e2e_td", row_id="{}|{}|{}|{}|{}".format(u["src"], u["item_id"], u["mode"],
                                                            th, u["repeat"]),
            item_id=u["item_id"], primary_class=it["primary_class"],
            subclass=it.get("subclass"), stratum=it["instance"]["stratum"], instance_id=iid,
            arm=D.SRC_TO_ARM.get(u["src"], u["src"]), thinking=th, mode=u["mode"],
            repeat=int(u["repeat"]), quality_visible=bool(it.get("quality_visible_candidate")),
            n_ops=len(ops), split=n2.op_split(ops),
            constraining=any(isinstance(o, dict) and o.get("op") in n2.CONSTRAINING_OPS
                             for o in ops),
            t_d=t_d, n_known=s["n_known"], n_running=s["n_running"], running_const=s["rconst"],
            terminal=u["term_cert"], terminal_feas=u["term_feas"],
            codes="|".join(u["codes"] or []), obj=u["obj"], obj_orig=u["obj_orig"],
            lb_cert=u["lb"], gap_cert=u["gap"], g_cert_anchor=s["an_gap"], ref1=s["an_obj"],
            ref2=u["ref2"], reference_from=u["ref2_from"], fingerprint=u["fp"],
            anchor_lb_K=s["an_lb"], anchor_pub=anchor_pub, rw_obj=u["rw_obj"],
            rw_obj_orig=u["rw_obj_orig"], names_running=len(u.get("names_running") or []),
            priced=True)
        r["floor_cert"] = u["lb"] < D.FLOOR_BH
        n2.prices(r)
        b = td_br.get((iid, t_d, u["fp"]))
        base = td_br.get((iid, t_d, D.BASE_FP))
        if b is not None and base is not None and u["fp"] == D.BASE_FP:
            b = base
        D.attach_truth(r, b, base, s["an_obj"])
        n2.errors(r)
        r["floor_truth"] = None if b is None else D.ends(b)[0] < D.FLOOR_BH
        r["gap_bh"] = u["obj"] - u["lb"]
        r["damage_if_applied"] = (None if u["rw_obj_orig"] is None
                                  else u["rw_obj_orig"] - anchor_pub)
        r["real_obj"] = u["rw_obj"]
        fp0 = fp_t0.get((u["src"], u["item_id"], u["mode"], th, int(u["repeat"])))
        fb = full_br.get((iid, fp0)) if fp0 else None
        fbase = full_br.get((iid, D.BASE_FP))
        if u["rw_obj"] is not None and fp0 is not None:
            D.attach_truth(r, fb if fp0 != D.BASE_FP else fbase, fbase,
                           float(a["wwt_adjusted_bh"]), prefix="real_")
        else:
            r["real_covered"] = r["real_covered_m"] = False
        if r["covered"]:
            check.true("A9", "e2e obj_K >= board lower on " + r["row_id"],
                       r["obj"] >= float(r["opt_lower"]) - D.CHECK_TOL)
            check.true("A9", "e2e certificate bound <= board upper on " + r["row_id"],
                       r["lb_cert"] <= float(r["opt_upper"]) + D.CHECK_TOL)
        rows.append(r)
    return rows


class EtoeMacros(D.Macros):
    """Stage 1's direct sections reused on the e2e rows: Direct names become Etoe names."""

    def add(self, name, value, twin_of=None, exhibit="", note=""):
        name = name.replace("nElevenNTwoDirect", "nElevenNTwoEtoe").replace(
            "nElevenRealDirect", "nElevenRealEtoe").replace("nElevenDamageDirect",
                                                            "nElevenDamageEtoe")
        if twin_of:
            twin_of = twin_of.replace("nTwoDirect", "nTwoEtoe")
        D.Macros.add(self, name, value, twin_of=twin_of, exhibit=exhibit.replace(
            "Table", "e2e Table"), note=note)

    def twin(self, published, value, exhibit, note=""):
        published = published.replace("nTwoDirect", "nTwoEtoe")
        D.Macros.twin(self, published, value, exhibit, note)


# --------------------------------------------------------------------------- #
# analyse2, part 10: the driver                                                #
# --------------------------------------------------------------------------- #
TABLE_NAMES = ("T1_e1_main", "T2_enforcement_ladder", "T3_guard_value_curve",
               "T6_tau_calibration", "D1_v3_separation_breakdown", "D2_class_disposition")
BUILDERS = (("build_e1", (), "Table 11 / 5.1 (eOne)"), ("build_e2", (), "Fig. 7 / Table S20 (eTwo)"),
            ("build_stratum", (), "Table S (E1 strata, DG9)"),
            ("build_e1_delta_replay", ("build_e1",), "5.1 damage sentences (DG17)"))
ARM_TOKEN = OrderedDict([("e1_eval_qwen14b", "QwenFourteen"), ("e1_eval_qwen27b", "QwenTwentySeven"),
                         ("e1_eval_glm9b", "Glm"), ("e1_eval_gpt54mini", "Mini"),
                         ("e1_eval_deepseek", "Deepseek"), ("e1_eval_sonnet5", "Sonnet"),
                         ("e1_eval_opus5", "Opus"), ("e1_eval_sol", "Sol")])
STAGE2_MARK = "% ==== N11 Stage 2 (n11_stage2.py analyse2) ===="
SUMMARY_MARK = "\n## Stage 2: the end-to-end record at the decision instant\n"


#: The values of the figure script fig3_guard_value.py that its load() reads.  The public
#: release does not carry the figure scripts, so fig4_inputs() computes load() and pearson()
#: from these constants when the script is absent; when it is present, the two must agree.
FIG4_D3_KEY = {"openai": "mini"}
FIG4_EXCLUDED = "deepseek"
FIG4_THINKING = {"opus": "default", "sonnet": "disabled", "sol": "none"}


def _fig4_load(t3_path, d3_path):
    """fig3_guard_value.load() and pearson() on the given T3 and D3 files, from FIG4_*."""
    t3 = D.read_csv_comments(t3_path)
    d3 = {r["arm"]: r for r in D.read_csv_comments(d3_path)}
    arms = []
    for r in t3:
        if r["arm"] == FIG4_EXCLUDED or r["mode"] != "M_constrained":
            continue
        want = FIG4_THINKING.get(r["arm"])
        if want is not None and r["thinking"] != want:
            continue
        num, den = d3[FIG4_D3_KEY.get(r["arm"], r["arm"])]["V3_equiv"].split(" ")[0].split("/")
        arms.append({"arm": r["arm"], "tier": int(r["tier"]),
                     "sep": 100.0 * float(r["v3_separation_share"]),
                     "fid": 100.0 * int(num) / int(den),
                     "spot": "SPOT-CHECK" in r["coverage_note"]})
    arms.sort(key=lambda a: a["tier"])
    xs, ys = [a["sep"] for a in arms], [a["fid"] for a in arms]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    return arms, sxy / (sxx * syy) ** 0.5


def fig4_inputs(t3_path, d3_path):
    """load() and pearson() of the figure script fig3_guard_value.py on the given T3 and D3 files,
    or of the FIG4_* copy when the script is absent."""
    import importlib.util
    import shutil
    import tempfile

    fig_dir = ROOT / "manuscript" / "figures"
    if not (fig_dir / "fig3_guard_value.py").is_file():
        return _fig4_load(t3_path, d3_path)
    if str(fig_dir) not in sys.path:
        sys.path.insert(0, str(fig_dir))
    import matplotlib
    matplotlib.use("Agg")
    spec = importlib.util.spec_from_file_location("n11_fig4", fig_dir / "fig3_guard_value.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with tempfile.TemporaryDirectory(dir=str(E2E_OUT)) as tmp:
        shutil.copy(t3_path, Path(tmp) / "T3_guard_value_curve.csv")
        shutil.copy(d3_path, Path(tmp) / "D3_translation_equivalence.csv")
        mod.ANALYSIS = tmp
        arms = mod.load()
    r = mod.pearson([a["sep"] for a in arms], [a["fid"] for a in arms])
    if (arms, r) != _fig4_load(t3_path, d3_path):
        raise SystemExit("fig4_inputs: FIG4_* no longer equal the values of fig3_guard_value.py")
    return arms, r


def jackknife_envelope(rows, refused_key):
    """DG16's instance-family envelope of the two direct headline rates."""
    import jackknife_direct as jk

    out = {}
    for label, cls in (("v3_refusal", "V3"), ("benign_refusal", "benign")):
        pop = [r for r in rows if r["primary_class"] == cls]
        num = sum(1 for r in pop if refused_key(r))
        cc = jk.cells(rows, "instance_id", lambda r, c=cls: r["primary_class"] == c, refused_key)
        n_total = len({r["instance_id"] for r in rows})
        _folds, st = jk.jackknife(num, len(pop), cc, n_total)
        out[label] = dict(st, num=num, den=len(pop))
    return out


def strata_cut(rows, refused_key):
    out = OrderedDict()
    for st in [None] + list(D.STRATUM_TOKEN):
        for cls in ("V3", "benign"):
            sel = [r for r in rows if r["primary_class"] == cls and (st is None or
                                                                    r["stratum"] == st)]
            out[(st, cls)] = (sum(1 for r in sel if refused_key(r)), len(sel))
    return out


def md(head, body):
    return D.md_table(head, body)


def cmd_analyse2(args) -> int:
    import csv as _csv
    import io

    import e1_delta_guard_replay as e1dg
    import n2_pricing as n2
    import suite_gate as sg

    D.pin_cores(args.cores_t)
    D.cap_threads(1)
    t0 = time.time()
    check = D.Checker()
    e2e_dir = Path(args.e2e_dir) if args.e2e_dir else E2E_OUT
    smoke = e2e_dir != E2E_OUT
    for path in (e2e_dir / "e2e_assertions.json", D.OUT / "census_assertions.json",
                 D.OUT / "analyse_assertions.json", D.OUT / "omni_assertions.json"):
        rep = json.loads(path.read_text())
        if rep.get("status") != "PASS":
            raise SystemExit("REFUSING TO RUN: {} says {}".format(path, rep.get("status")))
    e2e_meta = json.loads((e2e_dir / "e2e_meta.json").read_text())
    twin = ensure_dir(e2e_dir / "twin")
    out_an = ensure_dir(twin / "analysis") if smoke else ANALYSIS
    items_e2e = {r["item_id"]: r for r in D.read_jsonl(e2e_dir / "items.jsonl")}
    issuable = {k: bool(v["issuable"]) for k, v in items_e2e.items()}
    suite = {it["item_id"]: it for it in sg.load_suite()}
    pub = OrderedDict((r["item_id"], r) for r in D.load_published(check))
    published = published_macros()
    used = manuscript_tokens()
    M = D.Macros(published)
    S = OrderedDict()
    changes = []
    prov = ["N11 Stage 2 twin ({}); decision instant t_d = t_known, planned-known, frozen "
            "set kf = running + seed on K".format(VERSION)]
    timing = OrderedDict()

    def lap(name, t_prev=[t0]):
        now = time.time()
        timing[name] = round(now - t_prev[0], 1)
        t_prev[0] = now
        print("[n11 analyse2] {} ({:.0f}s)".format(name, timing[name]), flush=True)

    def note_change(exhibit, what, vpub, viss, vtd):
        changes.append(OrderedDict(exhibit=exhibit, quantity=what, published=vpub,
                                   issuable_t0=viss, decision_time=vtd,
                                   changed="yes" if str(vpub) != str(vtd) else "no"))

    # ================================================================ A5: reproductions at t = 0
    logged = load_logged_e1()
    skip_repro = smoke and args.smoke_skip_repro
    if not skip_repro:
        for src, (props, vs) in logged.items():
            groups = summary_groups(props, vs, list(range(len(props))))
            pk = {(g["arm"], g["mode"], str(g["thinking"]), str(g["repeat"])): g
                  for g in json.loads((RESULTS / src / "summary.json").read_text())["groups"]}
            check.true("A5", "E1 summary group count reproduces " + src, len(groups) == len(pk))
            for g in groups:
                k = (g["arm"], g["mode"], str(g["thinking"]), str(g["repeat"]))
                p = pk.get(k)
                check.true("A5", "E1 summary group reproduces {} {}".format(src, k),
                           p is not None and all(g.get(x) == p.get(x) for x in GROUP_KEYS))
        rep_tables = ensure_dir(twin / "repro_t0" / "tables")
        build_tables(RESULTS, rep_tables, prov)
        for n in TABLE_NAMES:
            check.true("A5", "paper_tables {} reproduces analysis/{}.csv".format(n, n),
                       csv_body(rep_tables / (n + ".csv")) == csv_body(ANALYSIS / (n + ".csv")))
        d3_t0, _ = d3_rows(suite)
        d3_pub = list(_csv.reader(csv_body(ANALYSIS / "D3_translation_equivalence.csv")))[1:]
        check.true("A5", "D3 reproduces analysis/D3_translation_equivalence.csv", d3_t0 == d3_pub)
        for b, before, _ex in BUILDERS + (("build_e1_intervals", (), ""),):
            ms = run_pm_builder(b, {}, before=before)
            bad = [n for n, v, _c in ms if published.get(n) != v]
            check.true("A5", "paper_macros.{} reproduces its {} published macros".format(b, len(ms)),
                       not bad and ms, bad[:5])
        dg9_t0 = dg9_split(RESULTS)
        check.true("A5", "DG9 split reproduces analysis/DG9_stratum_split.csv",
                   not rows_equal_csv(dg9_t0, ANALYSIS / "DG9_stratum_split.csv"))
        dg5_t0, roles_t0 = dg5_intervals(RESULTS)
        dg5_pub = [r for r in D.read_csv_comments(ANALYSIS / "DG5_e1_intervals.csv")
                   if r["cluster_level"] == "instance"]
        for (metric, arm, th), v in dg5_t0.items():
            p = [r for r in dg5_pub if (r["metric"], r["arm"], r["thinking"]) == (metric, arm, th)]
            check.true("A5", "DG5 interval reproduces {} {} {}".format(metric, arm, th),
                       len(p) == 1 and (p[0]["ci_lo_pct"], p[0]["ci_hi_pct"], int(p[0]["n_clusters"]))
                       == (v["ci_lo_pct"], v["ci_hi_pct"], v["n_clusters"]))
        for role, k in roles_t0.items():
            p = [r for r in dg5_pub if r["metric"] == "benign_false_block_gcert"
                 and r["range_role"] == role]
            check.true("A5", "DG5 range endpoint {} reproduces".format(role),
                       len(p) == 1 and (p[0]["arm"], p[0]["thinking"]) == k)
        n10res = n10_published()
        n10_mine = lines_to_macros(n10_macro_lines(n10res, n10res["table"], n10res["joint"],
                                                   n10res["large_qual"]))
        n10_pub = lines_to_macros((ANALYSIS / "N10_macros.tex").read_text().splitlines())
        check.true("A5", "N10 macros reproduce analysis/N10_macros.tex", n10_mine == n10_pub)
        check_literal_table(check, "tab:e1", tab11_values(ANALYSIS / "T3_guard_value_curve.csv",
                                                          ANALYSIS / "D3_translation_equivalence.csv"),
                            [1] * len(TAB11_COLS))
        check_literal_table(check, "tab:enforce", tab13_values(ANALYSIS / "T2_enforcement_ladder.csv"),
                            [d for _c, d in TAB13_COLS], label_cols=2)
        fig_pub, r_pub = fig4_inputs(ANALYSIS / "T3_guard_value_curve.csv",
                                     ANALYSIS / "D3_translation_equivalence.csv")
        # DG16 (Table 12's companion envelope) and the Table 12 strata on DG1's rows
        dg1 = [r for r in D.read_csv_comments(ANALYSIS / "DG1_direct_guard.csv")
               if r["reading"] == "canonical" and r["config"] == "G_CERT"]
        jk_t0 = jackknife_envelope(dg1, lambda r: r["refused"] == "True")
        for lab, tok in (("v3_refusal", "VThree"), ("benign_refusal", "Benign")):
            for k, mac in (("min", "dgJack{}Min"), ("max", "dgJack{}Max")):
                check.true("A5", "DG16 envelope {} {} reproduces".format(lab, k),
                           "{:.2f}\\%".format(100.0 * jk_t0[lab][k]) == published.get(mac.format(tok)),
                           "{} vs {}".format(jk_t0[lab][k], published.get(mac.format(tok))))
        st_t0 = strata_cut(dg1, lambda r: r["refused"] == "True")
        for (st, cls), (num, den) in st_t0.items():
            if st is None:
                continue
            tok = {"c09_storm2_w80": "CNine", "c10_storm2_w80": "CTenStorm",
                   "c10_replay_400": "Replay"}[st]
            name = ("dgVThreeCanonicalRefused" if cls == "V3" else "dgBenignCanonicalBlocks") + tok
            check.true("A5", "Table 12 cell {} reproduces".format(name),
                       published.get(name) == str(num), "{} vs {}".format(num, published.get(name)))
        # DG17 at t = 0 (the omniscient cache supplies ref2 exactly as the published run)
        with open(D.OUT / "omni_pool_cache.pkl", "rb") as fh:
            cache = pickle.load(fh)
        res_e1 = {}
        for res in cache["results"]:
            res_e1.update(res["e1"])
        del cache
        e1rows = D.load_e1(check)
        cells_logged = dg17_logged_cells()
        hl_t0 = dg17_headline(dg17_t0_cells(cells_logged, res_e1, e1rows, pub), e1dg.B_BOOT)
        n_dg17 = dg17_compare(hl_t0, ANALYSIS / "DG17_e2e_delta.csv", check, "t0")
        for n, v in dg17_macros(ANALYSIS / "DG17_e2e_delta.csv").items():
            check.true("A5", "restated DG17 macro {} reproduces".format(n),
                       published.get(n) == v, "{} vs {}".format(v, published.get(n)))
        check.true("A5", "DG17 headline rows compared = 100", n_dg17 == 100, n_dg17)

    else:
        print("[n11 analyse2] SMOKE: reproductions skipped", flush=True)
        dg5_t0, roles_t0 = dg5_intervals(RESULTS)
        fig_pub, r_pub = fig4_inputs(ANALYSIS / "T3_guard_value_curve.csv",
                                     ANALYSIS / "D3_translation_equivalence.csv")
        dg1 = [r for r in D.read_csv_comments(ANALYSIS / "DG1_direct_guard.csv")
               if r["reading"] == "canonical" and r["config"] == "G_CERT"]
        jk_t0 = jackknife_envelope(dg1, lambda r: r["refused"] == "True")
        st_t0 = strata_cut(dg1, lambda r: r["refused"] == "True")
        with open(D.OUT / "omni_pool_cache.pkl", "rb") as fh:
            cache = pickle.load(fh)
        res_e1 = {}
        for res in cache["results"]:
            res_e1.update(res["e1"])
        del cache
        e1rows = D.load_e1(check)
        cells_logged = dg17_logged_cells()
    n3_pub_macros = None
    if not args.skip_n3_analyze:
        n3_pub_macros = run_n3_analyze([RESULTS / s for s in D.N3_SOURCES],
                                       twin / "repro_t0" / "n3", twin / "repro_t0" / "n3.log")
        bad = [k for k, v in n3_pub_macros.items() if published.get(k) != v]
        check.true("A5", "n3_analyze reproduces {} published N3 macros".format(len(n3_pub_macros)),
                   not bad, bad[:5])
    if check.failures:
        check.fatal(twin / "analyse2_assertions.json", {"stage": "reproduction at t = 0"})
    lap("reproductions at t = 0")

    # ================================================================ E1 twin roots
    td_rows = D.read_jsonl(e2e_dir / "rows_e1_primary.jsonl")
    sites = {(s["iid"], s["fk"], float(s["t_d"])): s for s in D.read_jsonl(e2e_dir / "sites.jsonl")}
    counts_iss0 = write_twin_root(twin / "iss0", logged, None, issuable)
    counts_td = write_twin_root(twin / "primary", logged, td_rows, issuable)
    check.true("A4", "the t_d twin root holds the same rows as the issuable t = 0 root",
               counts_iss0 == counts_td)
    check.true("A4", "every decision-time E1 row enters the twin root",
               sum(n for n, _ in counts_td.values()) == len(td_rows),
               "{} vs {}".format(sum(n for n, _ in counts_td.values()), len(td_rows)))
    n_iss_rows = sum(n for n, _ in counts_td.values())
    n_all_rows = sum(m for _, m in counts_td.values())
    if not smoke:
        check.true("A3", "E1 rows on issuable items = 78,000 - 10,803", n_iss_rows == 67197,
                   n_iss_rows)
    td_by_key = {}
    for u in td_rows:
        if u["mode"] == "M_constrained":
            td_by_key[(u["src"], u["item_id"], e1dg.thinking_label(u["thinking"]),
                       int(u["repeat"]))] = u
    roots = OrderedDict([("iss0", twin / "iss0"), ("primary", twin / "primary")])
    dg17_cells = {}
    for name, root in roots.items():
        tab = ensure_dir(root / "tables")
        build_tables(root, tab, prov + ["reading: " + name])
        d3r, _ = d3_rows(suite, keep=issuable)
        write_d3(tab / "D3_translation_equivalence.csv", d3r,
                 "N11 {}: issuable items only (translation is read from the raw text)".format(name))
        write_rows_csv(tab / "DG9_stratum_split.csv", dg9_split(root),
                       "N11 twin of DG9_stratum_split.csv ({})".format(name))
        if name == "iss0":
            cells = dg17_t0_cells(cells_logged, res_e1, e1rows, pub, issuable)
        else:
            cells = dg17_td_cells(cells_logged, td_by_key, sites, issuable, check)
        dg17_cells[name] = cells
        write_dg17_twin(tab / "DG17_e2e_delta.csv", dg17_headline(cells, e1dg.B_BOOT),
                        "headline block recomputed on the {} rows".format(name))
    if check.failures:
        check.fatal(twin / "analyse2_assertions.json", {"stage": "twin roots"})
    lap("E1 twin roots and tables")

    # ================================================================ builder twins
    untwinned = []
    builder_md = []
    for b, before, exhibit in BUILDERS:
        vals = {}
        for name, root in roots.items():
            try:
                vals[name] = twin_builder_macros(b, e1_patches(root, root / "tables"), before)
            except Exception as exc:  # noqa: BLE001 - reported, never hidden
                import traceback

                fr = traceback.extract_tb(exc.__traceback__)[-1]
                vals[name] = type(exc)("{} at {}:{} ({})".format(
                    repr(exc), Path(fr.filename).name, fr.lineno, (fr.line or "").strip()))
        if any(isinstance(v, Exception) for v in vals.values()):
            builder_md.append([b, "refused: " + "; ".join(
                "{}: {}".format(k, str(v)[:220]) for k, v in vals.items()
                if isinstance(v, Exception))])
            continue
        iss = {n: v for n, v, _c, _t in vals["iss0"]}
        n_tw = n_ch = 0
        for n, v, c, tw in vals["primary"]:
            if n not in used:
                continue
            if not tw:
                untwinned.append((b, n, v))
                continue
            M.twin(n, v, exhibit, note="issuable t=0: {}".format(iss.get(n)))
            n_tw += 1
            if published.get(n) != v:
                n_ch += 1
                note_change(exhibit, n, published.get(n), iss.get(n), v)
        builder_md.append([b, "{} twins of manuscript macros, {} differ from the published "
                              "value".format(n_tw, n_ch)])
    dgm = {k: dg17_macros(roots[k] / "tables" / "DG17_e2e_delta.csv") for k in roots}
    n_tw = n_ch = 0
    for n, v in dgm["primary"].items():
        if n not in used:
            continue
        M.twin(n, v, "5.1 damage sentences (DG17)", note="issuable t=0: {}".format(
            dgm["iss0"].get(n)))
        n_tw += 1
        if published.get(n) != v:
            n_ch += 1
            note_change("5.1 damage sentences (DG17)", n, published.get(n), dgm["iss0"].get(n), v)
    n10_tw, n10_ch, n10_md = n10_twin(M, dg17_cells, issuable, published, used, note_change)
    builder_md.append(["n10_field_change.build_tables + macros on the decision-time rows",
                       "{} twins of manuscript macros, {} differ from the published value; {}"
                       .format(n10_tw, n10_ch, n10_md)])
    builder_md.append(["DG17 formulas restated (build_e1_delta_replay pins published values)",
                       "{} twins of manuscript macros, {} differ from the published value".format(
                           n_tw, n_ch)])
    lap("paper_macros builders on the twin roots")

    # ---- Table 11 and Table 13 (literal cells)
    lit = []
    t11 = {k: tab11_values(roots[k] / "tables" / "T3_guard_value_curve.csv",
                           roots[k] / "tables" / "D3_translation_equivalence.csv")
           for k in roots}
    t11_pub = tab11_values(ANALYSIS / "T3_guard_value_curve.csv",
                           ANALYSIS / "D3_translation_equivalence.csv")
    lit += literal_twin_macros(M, "TabEOne", t11_pub, t11["iss0"], t11["primary"], TAB11_COLS,
                               [1] * len(TAB11_COLS), "Table 11")
    t13 = {k: tab13_values(roots[k] / "tables" / "T2_enforcement_ladder.csv") for k in roots}
    t13_pub = tab13_values(ANALYSIS / "T2_enforcement_ladder.csv")
    lit += literal_twin_macros(M, "TabEnforce", t13_pub, t13["iss0"], t13["primary"],
                               [c for c, _d in TAB13_COLS], [d for _c, d in TAB13_COLS],
                               "Table 13")
    for r in lit:
        if r["published"] != r["decision_time"]:
            note_change(r["exhibit"], "{} {}".format(r["row"], r["column"]), r["published"],
                        r["issuable_t0"], r["decision_time"])
    write_rows_csv(out_an / "N11_literal_tables.csv", lit,
                   "N11 Stage 2: Tables 11 and 13 cell by cell (published / issuable at t = 0 / "
                   "decision instant)")

    # ---- DG5 intervals (the cells the prose quotes)
    dg5 = {}
    for name, root in roots.items():
        dg5[name] = dg5_intervals(root)
    for (metric, arm, th), v in dg5["primary"][0].items():
        base = {"benign_false_block_gcert": "dgFalseBlockOpus",
                "v3_separation": "dgVThreeSepOpus"}[metric]
        if (arm, th) != ("opus", "default"):
            continue
        for k, suf in (("ci_lo_pct", "CiLo"), ("ci_hi_pct", "CiHi")):
            M.twin(base + suf, v[k], "DG5 intervals", note="issuable t=0: {}".format(
                dg5["iss0"][0][(metric, arm, th)][k]))
    for role, lab in (("min", "Min"), ("max", "Max")):
        k = dg5["primary"][1][role]
        v = dg5["primary"][0][("benign_false_block_gcert",) + k]
        for kk, suf in (("ci_lo_pct", "CiLo"), ("ci_hi_pct", "CiHi")):
            M.twin("dgFalseBlock{}Arm{}".format(lab, suf), v[kk], "DG5 intervals",
                   note="endpoint arm {} (published {})".format(k, roles_t0[role]))
        if k != roles_t0[role]:
            note_change("DG5", "false-block range {} arm".format(role), roles_t0[role],
                        dg5["iss0"][1][role], k)
    lap("DG5 intervals")

    # ---- Fig. 4 inputs and the tolerance sweep
    fig = {k: fig4_inputs(roots[k] / "tables" / "T3_guard_value_curve.csv",
                          roots[k] / "tables" / "D3_translation_equivalence.csv") for k in roots}
    fig_rows = []
    by_arm = {k: {a["arm"]: a for a in fig[k][0]} for k in roots}
    for a in fig_pub:
        i0, td = by_arm["iss0"].get(a["arm"], {}), by_arm["primary"].get(a["arm"], {})
        fig_rows.append(OrderedDict(
            arm=a["arm"], tier=a["tier"], spot_check=a["spot"],
            referral_pct_published=round(a["sep"], 4), fidelity_pct_published=round(a["fid"], 4),
            referral_pct_issuable_t0=round(i0.get("sep", float("nan")), 4),
            fidelity_pct_issuable_t0=round(i0.get("fid", float("nan")), 4),
            referral_pct_decision_time=round(td.get("sep", float("nan")), 4),
            fidelity_pct_decision_time=round(td.get("fid", float("nan")), 4)))
    write_rows_csv(out_an / "N11_fig4_inputs.csv", fig_rows,
                   "N11 Stage 2: Fig. 4 inputs (fig3_guard_value.load) per arm; Pearson r "
                   "published {:.4f}, issuable t=0 {:.4f}, decision time {:.4f}".format(
                       r_pub, fig["iss0"][1], fig["primary"][1]))
    M.add("nElevenFigFourPearson", "{:.2f}".format(fig["primary"][1]), exhibit="Fig. 4",
          note="published {:.2f}".format(r_pub))
    note_change("Fig. 4", "Pearson r (referral vs fidelity)", round(r_pub, 3),
                round(fig["iss0"][1], 3), round(fig["primary"][1], 3))
    sweep = []
    t6 = {k: D.read_csv_comments(roots[k] / "tables" / "T6_tau_calibration.csv") for k in roots}
    t6_pub = D.read_csv_comments(ANALYSIS / "T6_tau_calibration.csv")
    idx = {k: {(r["arm"], r["mode"], r["thinking"], r["tau"]): r for r in t6[k]} for k in roots}
    for r in t6_pub:
        k = (r["arm"], r["mode"], r["thinking"], r["tau"])
        i0, td = idx["iss0"].get(k, {}), idx["primary"].get(k, {})
        sweep.append(OrderedDict(
            arm=r["arm"], mode=r["mode"], thinking=r["thinking"], tau=r["tau"],
            referral_published=r["v3_separation_share"],
            benign_stop_published=r["false_block_rate"],
            floor_published=r["schema_feas_false_block_floor"],
            operating_point_published=r["operating_point_fb5pct"],
            referral_issuable_t0=i0.get("v3_separation_share"),
            benign_stop_issuable_t0=i0.get("false_block_rate"),
            floor_issuable_t0=i0.get("schema_feas_false_block_floor"),
            operating_point_issuable_t0=i0.get("operating_point_fb5pct"),
            referral_decision_time=td.get("v3_separation_share"),
            benign_stop_decision_time=td.get("false_block_rate"),
            floor_decision_time=td.get("schema_feas_false_block_floor"),
            operating_point_decision_time=td.get("operating_point_fb5pct"),
            v3_items_decision_time=td.get("v3_items")))
    write_rows_csv(out_an / "N11_tau_sweep.csv", sweep,
                   "N11 Stage 2: the tolerance sweep (T6 rebuilt by paper_tables.build_t6 on the "
                   "twin roots); referral = v3_separation_share, benign stop = false_block_rate")
    lap("Fig. 4 inputs and tolerance sweep")

    # ================================================================ Table 12 (direct strata)
    direct = [r for r in D.read_csv_comments(ANALYSIS / "N11_rows_direct.csv")
              if r["set"] == "published" and r["issuable"] == "True"]
    refused_td = (lambda r: r["terminal"] in D.STOP_TERMS)
    st_td = strata_cut(direct, refused_td)
    dg1_iss = [r for r in dg1 if issuable.get(r["item_id"])]
    st_i0 = strata_cut(dg1_iss, lambda r: r["refused"] == "True")
    body12 = []
    for st in [None] + list(D.STRATUM_TOKEN):
        tok = {None: "", "c09_storm2_w80": "CNine", "c10_storm2_w80": "CTenStorm",
               "c10_replay_400": "Replay"}[st]
        row = [D.STRATUM_NAME.get(st, "Pooled") if st else "Pooled"]
        for cls, stem in (("V3", "VThree"), ("benign", "Benign")):
            n, d = st_td[(st, cls)]
            n0, d0 = st_t0[(st, cls)]
            ni, di = st_i0[(st, cls)]
            if tok:
                if cls == "V3":
                    names = ("dgVThreeCanonicalRefused", "dgVThreeCanonicalItems",
                             "dgVThreeCanonicalShare")
                else:
                    names = ("dgBenignCanonicalBlocks", "dgBenignCanonicalItems",
                             "dgBenignCanonicalShare")
                M.twin(names[0] + tok, D.group_int(n), "Table 12")
                M.twin(names[1] + tok, D.group_int(d), "Table 12")
                M.twin(names[2] + tok, D.pct_tex(n / d if d else None), "Table 12")
            row.append("{}/{} ({}) | t=0 issuable {}/{} | published {}/{}".format(
                n, d, D.pctf(n / d if d else None), ni, di, n0, d0))
            note_change("Table 12", "{} {}".format(st or "pooled", cls),
                        "{}/{}".format(n0, d0), "{}/{}".format(ni, di), "{}/{}".format(n, d))
        body12.append(row)
    jk_td = jackknife_envelope(direct, refused_td)
    jk_i0 = jackknife_envelope(dg1_iss, lambda r: r["refused"] == "True")
    for lab, tok in (("v3_refusal", "VThree"), ("benign_refusal", "Benign")):
        st = jk_td[lab]
        for k, suf in (("min", "Min"), ("max", "Max")):
            v = "n/a" if st.get(k) is None else "{:.2f}\\%".format(100.0 * st[k])
            M.twin("dgJack{}{}".format(tok, suf), v, "Table 12 / DG16",
                   note="issuable t=0: {:.2f}".format(100.0 * jk_i0[lab][k])
                   if jk_i0[lab].get(k) is not None else "")
        M.twin("dgJack{}Folds".format(tok), D.group_int(st["n_eff"]), "Table 12 / DG16")
        note_change("DG16", lab + " envelope", "{:.2f} to {:.2f}".format(
            100 * jk_t0[lab]["min"], 100 * jk_t0[lab]["max"]),
            "{:.2f} to {:.2f}".format(100 * jk_i0[lab]["min"], 100 * jk_i0[lab]["max"])
            if jk_i0[lab].get("min") is not None else "n/a",
            "{:.2f} to {:.2f}".format(100 * st["min"], 100 * st["max"])
            if st.get("min") is not None else "n/a")
    lap("Table 12")

    # ================================================================ N3 twins
    rows_n3 = D.read_jsonl(e2e_dir / "rows_n3.jsonl")
    gold = {g["item_id"]: g for g in D.read_jsonl(e2e_dir / "gold.jsonl")}
    n3_dirs = {"iss0": write_n3_twin(twin / "n3_iss0", None, gold, issuable, check,
                                     use_logged=True),
               "primary": write_n3_twin(twin / "n3_primary", rows_n3, gold, issuable, check)}
    n_n3 = sum(len(D.read_jsonl(p / "dispositions.jsonl")) for p in n3_dirs["primary"])
    check.true("A4", "every N3 decision-time row enters the twin", n_n3 == len(rows_n3),
               "{} vs {}".format(n_n3, len(rows_n3)))
    if check.failures:
        check.fatal(twin / "analyse2_assertions.json", {"stage": "N3 twin"})
    n3m = {}
    n3_md = []
    if not args.skip_n3_analyze:
        for name, dirs in n3_dirs.items():
            n3m[name] = run_n3_analyze(dirs, twin / ("n3_" + name) / "analysis",
                                       twin / ("n3_" + name) / "n3_analyze.log")
        n_tw = n_ch = 0
        for n, v in n3m["primary"].items():
            if n not in used:
                continue
            M.twin(n, v, "Tables 18-19 (N3)", note="issuable t=0: {}".format(
                n3m["iss0"].get(n)))
            n_tw += 1
            if published.get(n) != v:
                n_ch += 1
                note_change("Tables 18-19 (N3)", n, published.get(n), n3m["iss0"].get(n), v)
        n3_md.append("{} N3 macros the manuscript uses were twinned; {} differ from the "
                     "published value.".format(n_tw, n_ch))
    n3_flat = []
    for p in n3_dirs["primary"]:
        for d in D.read_jsonl(p / "dispositions.jsonl"):
            row = OrderedDict(src=p.name)
            for k, v in d.items():
                row[k] = json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v
            n3_flat.append(row)
    if n3_flat:
        cols = []
        for r in n3_flat:
            for k in r:
                if k not in cols:
                    cols.append(k)
        D.write_csv_rows(out_an / "N11_rows_n3.csv", n3_flat,
                         ["N11 Stage 2: N3 dispositions at t_d = t_known on the issuable items "
                          "(n3_evaluate._disposition on decision-time prices, gold at t_d, "
                          "realised executed values); {}".format(VERSION)], cols)
    lap("N3 twins")

    # ================================================================ e2e pricing (Tables 14 and 16, e2e rows)
    anchors = D.load_anchor_records()
    full_br = D.full_brackets()
    td_br_e, br_all_e, boards_e, br_source_e = D.board_brackets_or_closed(e2e_dir)
    fp_t0 = {}
    for p in D.read_jsonl(D.ORACLE_V1 / "proposals_index.jsonl"):
        if p.get("executed"):
            fp_t0[(p["source"], p["instruction_id"], p["mode"], e1dg.thinking_label(p["thinking"]),
                   int(p["repeat"]))] = p["fingerprint"]
    erows = e2e_pricing_rows(td_rows, logged, pub, sites, td_br_e, full_br, anchors, fp_t0, check)
    need = set()
    for r in erows:
        need.add((r["instance_id"], r["t_d"], r["fingerprint"]))
        need.add((r["instance_id"], r["t_d"], D.BASE_FP))
    covered = sum(1 for k in need if k in td_br_e)
    status_e = "COMPLETE" if covered == len(need) else "PARTIAL"
    items_d = D.read_jsonl(D.OUT / "items.jsonl")
    td_br_d = D.board_brackets_or_closed(D.OUT)[0]
    rows_d = D.build_rows(items_d, td_br_d, full_br, anchors)
    iss_d = [r for r in rows_d if r["set"] == "published" and r["issuable"]]
    priced_d = [r for r in iss_d if r["priced"]]
    groupings = [("all", lambda r: ["all"]), ("stratum", lambda r: [r["stratum"]]),
                 ("class", lambda r: [r["primary_class"]])]
    rg = D.refgap_section(iss_d, priced_d, td_br_d, n2.pricing_table(priced_d, "direct_td",
                                                                    groupings),
                          n2, D.Macros(published))
    ME = EtoeMacros(published)
    pr_e = n2.pricing_table(erows, "e2e_td", groupings)
    pub_e = published_rows_file("N2_rows_e2e.csv")
    pub_e_iss = [r for r in pub_e if issuable.get(r["item_id"])]
    pr_pub_e = n2.pricing_table(pub_e, "e2e", groupings)
    pr_pub_e_iss = n2.pricing_table(pub_e_iss, "e2e_issuable", groupings)
    sec_price = D.pricing_section(pr_e, pr_pub_e, pr_pub_e_iss, erows, ME)
    boot_e = n2.Boot({r["instance_id"] for r in erows}, n2.SEED, n2.B_BOOT)
    dg14 = dict(D.DG14)
    wins_e = n2.wins_table(erows, "e2e_td", dg14, rg["_by_stratum"], rg["_cert_by_stratum"])
    real_e = D.as_truth(erows, "real_")
    wins_real_e = n2.wins_table(real_e, "e2e_td_realised", dg14, rg["_by_stratum"],
                                rg["_cert_by_stratum"])
    disp_e = n2.disposition_table(erows, "e2e_td", dg14, {}, boot_e)
    sec_dec = D.decision_section(wins_e, wins_real_e, disp_e, ME)
    ME.add("nElevenEtoeCoverageStatus", status_e.lower(), exhibit="coverage")
    ME.add("nElevenEtoeBoardsNeeded", D.group_int(len(need)), exhibit="coverage")
    ME.add("nElevenEtoeBoardsCovered", D.group_int(covered), exhibit="coverage")
    for name, (n, d, pv) in OrderedDict([
            ("e2e rows priced at t_d", (len(erows), None, published.get("nTwoEtoeRows"))),
    ]).items():
        note_change("Table 14 (e2e)", name, pv, None, D.group_int(n))
    for h in sec_price["head"] + sec_dec["head"]:
        note_change("Tables 14/16 (e2e)", h[0], h[1], h[2], h[3])
    cols = list(erows[0].keys()) if erows else []
    for r in erows:
        for k in r:
            if k not in cols:
                cols.append(k)
    cols = [c for c in cols if not c.startswith("_") and not c.startswith("real__")]
    D.write_csv_rows(out_an / "N11_rows_e2e.csv", erows,
                     ["N11 Stage 2: end-to-end rows priced by the certificate at t_d = t_known "
                      "({})".format(VERSION),
                      "truth on K = decision-time oracle ({}), status {} ({} of {} boards)".format(
                          br_source_e, status_e, covered, len(need)),
                      "realised columns: full-window run from t_d; real_* truth = "
                      "results/oracle_v1 bracket of the logged full-window fingerprint"], cols)
    for nm, table in (("N11_e2e_pricing.csv", pr_e + pr_pub_e_iss),
                      ("N11_e2e_wins.csv", wins_e + wins_real_e),
                      ("N11_e2e_disposition.csv", disp_e)):
        if table:
            D.write_csv_rows(out_an / nm, table, ["N11 Stage 2 e2e ({}), status {}".format(
                VERSION, status_e)], list(table[0].keys()))
    lap("e2e pricing")

    # ================================================================ dangling identifiers
    ops_by = {}
    for src, (props, _vs) in logged.items():
        for p in props:
            ex = p.get("extra") or {}
            ops_by[e1_key(src, p["instruction_id"], p["mode"], ex.get("thinking"),
                          ex.get("repeat", 0))] = p.get("parsed_ops") or []
    dang = OrderedDict()
    for u in td_rows:
        k = u["src"]
        c = dang.setdefault(k, Counter())
        c["rows"] += 1
        if u.get("model_refused"):
            c["model_refused"] += 1
            continue
        if ops_by[e1_key(u["src"], u["item_id"], u["mode"], u["thinking"], u["repeat"])]:
            c["with_ops"] += 1
        if u["names_unknown"]:
            c["names_unknown"] += 1
            if u["dangling"] and u["term_cert"] == "blocked_schema":
                c["refused_dangling"] += 1
        if u["names_completed"]:
            c["names_completed"] += 1
        if u["names_running"]:
            c["names_running"] += 1
    body_d = []
    tot = Counter()
    for src, c in dang.items():
        tot.update(c)
        share = c["names_unknown"] / c["with_ops"] if c["with_ops"] else None
        body_d.append([src, c["rows"], c["with_ops"], c["names_unknown"], c["refused_dangling"],
                       D.pctf(share), c["names_completed"], c["names_running"]])
        tok = ARM_TOKEN[src]
        M.add("nElevenDangling{}Rows".format(tok), D.group_int(c["names_unknown"]),
              exhibit="dangling identifiers")
        M.add("nElevenDangling{}WithOps".format(tok), D.group_int(c["with_ops"]),
              exhibit="dangling identifiers")
        M.add("nElevenDangling{}Share".format(tok), D.pct_tex(share), exhibit="dangling identifiers")
    share = tot["names_unknown"] / tot["with_ops"] if tot["with_ops"] else None
    body_d.append(["all", tot["rows"], tot["with_ops"], tot["names_unknown"],
                   tot["refused_dangling"], D.pctf(share), tot["names_completed"],
                   tot["names_running"]])
    M.add("nElevenDanglingRows", D.group_int(tot["names_unknown"]), exhibit="dangling identifiers")
    M.add("nElevenDanglingWithOps", D.group_int(tot["with_ops"]), exhibit="dangling identifiers")
    M.add("nElevenDanglingShare", D.pct_tex(share), exhibit="dangling identifiers")
    M.add("nElevenEOneRowsIssuable", D.group_int(n_iss_rows), exhibit="e2e population")
    M.add("nElevenEOneRowsLogged", D.group_int(n_all_rows), exhibit="e2e population")
    if not smoke:
        check.true("A3", "dangling rows equal their refusals at schema",
                   tot["names_unknown"] == tot["refused_dangling"] + sum(
                       1 for u in td_rows if not u.get("model_refused") and u["names_unknown"]
                       and u.get("parse_ok") is False),
                   "{} vs {}".format(tot["names_unknown"], tot["refused_dangling"]))
    lap("dangling identifiers")

    # ================================================================ Table 10 under the fix
    snap = D.load_macros([str(D.STAGE1_SNAPSHOT.parent / "analysis" / "N11_macros.tex")]) \
        if (D.STAGE1_SNAPSHOT.parent / "analysis" / "N11_macros.tex").is_file() else {}
    now_m = D.load_macros(["analysis/N11_macros.tex"])
    t10 = []
    for row in D.read_csv_comments(ANALYSIS / "N11_macro_map.csv"):
        if row["exhibit"].startswith("Table 10") and row["twin"] in now_m:
            a, b = snap.get(row["twin"]), now_m[row["twin"]]
            if a != b:
                t10.append([row["twin"], row["published_value"], a, b])
    flips = Counter()
    snap_items = {r["item_id"]: r for r in D.read_jsonl(D.STAGE1_SNAPSHOT.parent / "items.jsonl")}
    for r in items_d:
        o = snap_items.get(r["item_id"])
        if o is not None and r["set"] == "published" and o["dt_term_cert"] != r["dt_term_cert"]:
            flips[(r["primary_class"], o["dt_term_cert"], r["dt_term_cert"])] += 1
    lap("Table 10 comparison")

    # ================================================================ write
    for n in ME.names:
        if n in M.names:
            raise SystemExit("macro {} written twice".format(n))
    M.lines += ME.lines
    M.map += ME.map
    M.names |= ME.names
    lines = [STAGE2_MARK, "% N11 Stage 2 macros ({}); end-to-end status {}; generated by "
                          "code/scripts/n11_stage2.py analyse2".format(VERSION, status_e)]
    if status_e != "COMPLETE":
        lines.append("% PARTIAL: not every needed e2e decision-time bracket is on disk; "
                     "not for publication")
    mac_path = out_an / "N11_macros.tex"
    base_txt = (ANALYSIS / "N11_macros.tex").read_text()
    base_txt = base_txt.split(STAGE2_MARK)[0].rstrip("\n") + "\n"
    stage1_names = set(lines_to_macros(base_txt.splitlines()))
    clash = sorted(M.names & stage1_names)
    if clash:
        raise SystemExit("Stage 2 macros collide with Stage 1 macros: {}".format(clash[:10]))
    mac_path.write_text(base_txt + "\n".join(lines + M.lines) + "\n")
    map_path = out_an / "N11_macro_map.csv"
    keep = [r for r in D.read_csv_comments(ANALYSIS / "N11_macro_map.csv")
            if r["twin"] not in M.names]
    D.write_csv_rows(map_path, keep + [dict(r) for r in M.map],
                     ["N11 macro map (Stage 1 and Stage 2)"],
                     ["published_macro", "published_value", "twin", "late_twin", "value",
                      "exhibit", "note"])
    write_rows_csv(out_an / "N11_stage2_changes.csv", changes or [OrderedDict(exhibit="")],
                   "N11 Stage 2: every twin quantity, published / issuable at t = 0 / decision "
                   "instant")
    # ---- summary
    rep = check.report()
    L = [SUMMARY_MARK.strip("\n"), ""]
    L.append("Generated by `code/scripts/n11_stage2.py analyse2` ({}). Population: the {} E1 rows "
             "and {} N3 rows of the issuable items, re-judged on the known board K at t_d = "
             "t_known (planned-known reading; frozen set = running orders plus the seed orders "
             "K holds). Three readings are reported side by side: published (all rows, t = 0), "
             "issuable at t = 0 (the population change alone) and decision time (t_d). "
             "End-to-end oracle status: {} ({} of {} boards).".format(
                 VERSION, D.group_int(n_iss_rows), D.group_int(len(rows_n3)), status_e, covered,
                 len(need)))
    L += ["", "### Assertions", "",
          "{} run-fatal checks, status {} (by group: {}). Every published builder reproduced its "
          "published output on the logged t = 0 data before any twin was built.".format(
              rep["n_checks"], rep["status"], rep["checks_by_group"]), ""]
    L += ["### The frozen-set fix and Table 10", "",
          "Terminal changes of the direct benchmark against Stage 1 (class, Stage 1 terminal, "
          "Stage 2 terminal, items):", "",
          md(["class", "Stage 1", "Stage 2", "items"],
             [[k[0], k[1], k[2], v] for k, v in sorted(flips.items())]), "",
          "Table 10 twin cells that changed:", "",
          md(["macro", "published", "Stage 1", "Stage 2 (fix)"], t10) if t10 else "none", ""]
    L += ["### Dangling identifiers (E1, issuable rows, t_d)", "",
          md(["source", "rows", "with operations", "name an unknown order",
              "refused at schema as dangling", "share of rows with operations",
              "name a completed order", "name a running order"], body_d), ""]
    L += ["### Tables 11 and 13 (literal cells)", "",
          md(["exhibit", "row", "column", "published", "issuable t=0", "t_d"],
             [[r["exhibit"], r["row"], r["column"], r["published"], r["issuable_t0"],
               r["decision_time"]] for r in lit]), ""]
    L += ["### Table 12 (direct benchmark by stratum)", "",
          md(["stratum", "V3 referral (t_d | t=0 issuable | published)",
              "benign false block (t_d | t=0 issuable | published)"], body12), ""]
    L += ["### paper_macros builders on the twin roots", "", md(["builder", "result"], builder_md),
          "", "Macros these builders emit from unpatched (t = 0) sources are not twinned: {}."
          .format(len(untwinned)), ""]
    L += ["### Tables 18 and 19 (N3)", ""] + n3_md + [""]
    L += ["### Tables 14 and 16, end-to-end rows", "", sec_price["md"], "", sec_dec["md"], ""]
    L += ["### Fig. 4 and the tolerance sweep", "",
          "Pearson r of referral against fidelity: published {:.3f}, issuable t=0 {:.3f}, "
          "decision time {:.3f}. Per-arm inputs in `N11_fig4_inputs.csv`; the sweep in "
          "`N11_tau_sweep.csv`.".format(r_pub, fig["iss0"][1], fig["primary"][1]), ""]
    L += ["### What changed against the published reading", "",
          md(["exhibit", "quantity", "published", "issuable t=0", "decision time"],
             [[c["exhibit"], c["quantity"], c["published"], c["issuable_t0"], c["decision_time"]]
              for c in changes if c["changed"] == "yes"][:400]), ""]
    late_rep = json.loads((D.OUT / "late" / "census_assertions.json").read_text())
    late_items = D.read_jsonl(D.OUT / "late" / "items.jsonl")
    run_q = [[r["item_id"], r["instance_id"], r["t_d"], len(r["names_running"]),
              r["dt_term_cert"], r["dt_lb_running"], r["rconst"]]
             for r in late_items if r["issuable"] and r.get("names_running")
             and r["dt_stage_cert"] == "qual"]
    n_run = sum(1 for r in late_items if r["issuable"] and r.get("names_running"))
    L += ["### Late reading (t_d' = t_start): halted at A12", "",
          "The late census ({} checks) failed {} assertion(s): {}. The late reading is therefore "
          "not reported: no late twin of Tables 10, 11, 14 or 16 is written, and the e2e replay "
          "ran the primary instant only.".format(late_rep["n_checks"], late_rep["n_failures"],
                                                  "; ".join(late_rep["failures"])),
          "", "Cause. At t_start the seed orders of {} issuable V6 items have already started, and "
          "their canonical proposals unfreeze them. The guard's frozen-edit rule counts an "
          "`unfreeze` as a legitimate release, so on K the running orders are released, the "
          "certificate's bound treats them as queued work (its running constant is 0), and the "
          "dispatch may restart them. The decision-time board keeps them as running work. Two "
          "items reach the quality stage; on one the running tardiness is non-zero and A12 "
          "fails, on the other it is zero and A12 passes by coincidence:".format(n_run), "",
          md(["item", "instance", "t_d'", "running orders named", "G-CERT terminal on K",
              "certificate running constant", "site running constant"], run_q), "",
          "The primary reading has no such case (no issuable item's proposal names a running "
          "order in the direct benchmark, and the e2e proposal-board A12 check passed on "
          "every priced proposal). The decision needed: whether an operation on an order "
          "already running at t_d is refused (protected) or executed, before the late reading "
          "can be reported.", ""]
    L += ["### Wall times", "", md(["step", "s"], [[k, v] for k, v in timing.items()]), ""]
    summ = (ANALYSIS / "N11_summary.md").read_text().split(SUMMARY_MARK)[0].rstrip("\n")
    (out_an / "N11_summary.md").write_text(summ + "\n" + SUMMARY_MARK + "\n".join(L[1:]) + "\n")
    check.fatal(twin / "analyse2_assertions.json", {"timing": timing, "status_e2e": status_e,
                                                    "boards_needed": len(need),
                                                    "boards_covered": covered})
    print("[n11 analyse2] PASS: {} checks, e2e {}, {:.0f}s".format(
        rep["n_checks"], status_e, time.time() - t0), flush=True)
    return 0


# --------------------------------------------------------------------------- #
# Entry point                                                                  #
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("e2e", "analyse2"):
        p = sub.add_parser(name)
        p.add_argument("--cores", default="8-9")
        p.add_argument("--workers", type=int, default=2)
        p.add_argument("--instances", default="", help="smoke: comma-separated instance ids")
        if name == "analyse2":
            p.add_argument("--skip-n3-analyze", action="store_true")
            p.add_argument("--e2e-dir", default="", help="smoke: an e2e output folder")
            p.add_argument("--smoke-skip-repro", action="store_true",
                           help="with --e2e-dir only: skip the t = 0 reproductions")
        p.add_argument("--readings", default="primary,late",
                       help="decision instants to replay (primary first)")
        if name == "e2e":
            p.add_argument("--out-dir", default="",
                           help="Stage 3: write the replay to this folder instead of "
                                "results/n11_e2e")
    args = ap.parse_args(argv)
    args.cores_t = D.parse_cores(args.cores)
    if set(args.cores_t) & D.FORBIDDEN_CORES:
        raise SystemExit("REFUSING TO RUN: cores {} are not this project's".format(args.cores_t))
    if set(args.cores_t) - set(D.DET_CORES) and not os.environ.get("CERTIGATE_ANY_CORES"):
        raise SystemExit("REFUSING TO RUN: deterministic stages run on cores 8-9 only")
    if args.workers > len(args.cores_t):
        raise SystemExit("REFUSING TO RUN: {} workers on {} cores".format(args.workers,
                                                                         len(args.cores_t)))
    fn = {"e2e": cmd_e2e, "analyse2": globals().get("cmd_analyse2")}[args.cmd]
    return fn(args)


if __name__ == "__main__":
    sys.exit(main())
