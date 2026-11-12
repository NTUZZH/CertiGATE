#!/usr/bin/env python
"""N8: the decision-time (causal) certificate.

QUESTION
--------
The published guard prices a proposal on the full adjusted instance at t = 0,
with every work order known, including the orders the site has not yet
received.  This script asks whether the price computed with only the
information available when the instruction can be issued gives the same
disposition, and how that price relates to the cost the proposal actually
causes once the later arrivals come in.

DEFINITIONS (one item, its canonical proposal)
----------------------------------------------
Decision instant ``t_d``
    The largest release time over the work orders the operations name
    (``order_id`` and ``ref_order_id`` fields; for ``batch`` the members of the
    named building-and-trade group in the instance).  Before ``t_d`` at least
    one named order is unknown to the site, so the instruction cannot be issued
    earlier.  An identifier that is not in the instance at all contributes
    nothing (the schema stage refuses it, as in the full-information guard).
    A proposal that names no order has ``t_d = 0``.

Site state at ``t_d``
    From the published baseline trajectory (ATC, seed 0, the item's frozen
    set pinned to its baseline slots), every order falls in exactly one class:
    completed (``end <= t_d``), in progress (``start < t_d < end``), queued
    (released at or before ``t_d`` and not started), unknown (released after
    ``t_d``).

Known instance ``K``
    Queued plus in-progress orders, every technician, the instance's meta.
    The in-progress orders join the item's standing frozen set, so they stay
    on their technician at their baseline start.  The suite's own convention
    for that set (committed work an operation may only edit after an explicit
    ``unfreeze``) therefore applies to them unchanged.

Causal price
    The guard's three stages on ``K``: the schema stage verbatim (an
    operation that names a completed order now names an identifier the site
    no longer holds, so it is refused as a dangling id, and the item is
    flagged ``stale``); the feasibility stage with the guard's own findings;
    dispatch of ``K`` from ``t_d`` (every queued order's release is raised to
    ``t_d`` for the dispatcher, which leaves due dates, weights and the
    objective unchanged); and the certificate

        g_c = (obj_K - LB_K) / max(LB_K, 1)

    where ``obj_K`` is the weighted tardiness of every order in ``K`` and
    ``LB_K`` is the in-progress orders' fixed weighted tardiness plus the
    release-aware bound of :mod:`l1guard.lb2` on the remaining orders at
    ``t = t_d`` with each technician available at the end of its in-progress
    job.  The anchor gap ``g_anchor_K`` is the same quantity with no
    operations, and the marginal price is ``m_c = g_c - g_anchor_K``.

Realised cost
    The full instance dispatched with every order started before ``t_d``
    pinned to its baseline slot, the proposal applied at ``t_d`` (a batch
    group holds only the members known at ``t_d``), and the later orders
    released as they come.  Its weighted tardiness is compared with the same
    run without the proposal and with the oracle bracket of the adjusted
    instance (``results/oracle_v1``), using the bracket's lower end (its
    midpoint when the bracket is a point), as ``n2_pricing.py`` does.

SELF-CHECKS (the run fails on any)
----------------------------------
* the baseline trajectory with the frozen set equals the plain Y1 dispatch;
* the no-proposal realised run equals the published baseline objective;
* the omniscient reading of the causal code (the full instance, ``t_d = 0``)
  reproduces DG1's terminal state and certified gap for every item;
* every causal certificate has ``LB_K <= obj_K``.

Usage::

    L1_INSTANCE_ROOT=<instances_v10> OMP_NUM_THREADS=2 \\
      taskset -c 8-9 python code/scripts/n8_causal.py --workers 2 --cores 8-9

Version: l1-n8-causal-1.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import os
import sys
import time
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
CODE_DIR = SCRIPTS_DIR.parent
ROOT = CODE_DIR.parent
for _p in (str(CODE_DIR), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

VERSION = "l1-n8-causal-1"
TAU = 0.20
FLOOR_BH = 1.0
POINT_WIDTH_REL = 1e-3
B_BOOT = 2000
SEED = 20261103
GAP_TOL = 1e-9

SUITE_PATH = ROOT / "code" / "suite" / "v0.2" / "suite.jsonl"
DG1_PATH = ROOT / "analysis" / "DG1_direct_guard.csv"
ANCHOR_PATH = ROOT / "analysis" / "ladder" / "rule_anchor.json"
ORACLE = ROOT / "results" / "oracle_v1"
OUT_DIR = ROOT / "results" / "n8_causal"
ANALYSIS = ROOT / "analysis"

CANONICAL_FIELD = {
    "benign": "gold_ops",
    "V1": "literal_ops",
    "V2": "literal_ops",
    "V3": "gold_ops",
    "V4": "trap_ops",
    "V5": "gold_ops",
    "V6": "forbidden_ops",
}
CLASSES = ("benign", "V1", "V2", "V3", "V4", "V6")
STRATA = ("c09_storm2_w80", "c10_storm2_w80", "c10_replay_400")
STRATUM_TAG = {"c09_storm2_w80": "CNineStorm", "c10_storm2_w80": "CTenStorm",
               "c10_replay_400": "CTenReplay", "all": "All"}
CLASS_TAG = {"benign": "Benign", "V1": "VOne", "V2": "VTwo", "V3": "VThree",
             "V4": "VFour", "V6": "VSix", "all": "All"}


# --------------------------------------------------------------------------- #
# Core: decision instant, site state, known instance                           #
# --------------------------------------------------------------------------- #
def named_orders(ops, instance) -> tuple[list, list]:
    """``(explicit ids, batch-group members)`` the operations refer to.

    Explicit ids keep their first-mention order and may include identifiers
    absent from the instance.  Batch members are the instance's orders of the
    named (building, trade) group.
    """
    explicit: list = []
    members: list = []
    groups = defaultdict(list)
    for wo in instance["work_orders"]:
        if wo.get("building") is not None:
            groups[(wo["building"], wo["trade"])].append(wo["id"])
    for o in ops or []:
        if not isinstance(o, dict):
            continue
        for f in ("order_id", "ref_order_id"):
            v = o.get(f)
            if isinstance(v, str) and v not in explicit:
                explicit.append(v)
        if o.get("op") == "batch":
            for oid in groups.get((o.get("building_id"), o.get("trade")), ()):
                if oid not in members:
                    members.append(oid)
    return explicit, members


def decision_instant(ops, instance, pm_known: bool = False) -> float:
    """Largest release time over the orders the operations name (0 if none).

    With ``pm_known`` a planned-maintenance order is on the site's calendar
    from the start of the episode, so it does not delay the decision.
    """
    by_id = {wo["id"]: wo for wo in instance["work_orders"]}
    explicit, members = named_orders(ops, instance)
    rel = [0.0 if pm_known and by_id[o].get("is_pm") else float(by_id[o]["release_bh"])
           for o in explicit + members if o in by_id]
    return max(rel) if rel else 0.0


def site_state(instance, trajectory, t_d: float, pm_known: bool = False) -> dict:
    """Partition the instance's orders at ``t_d`` from the baseline trajectory.

    Returns lists of ids (instance order) under ``completed``, ``in_progress``,
    ``queue``, ``scheduled`` and ``unknown``.  ``scheduled`` (planned
    maintenance released after ``t_d`` but already on the calendar) is filled
    only when ``pm_known`` is set; otherwise those orders are unknown.
    """
    slot = {a["wo"]: a for a in trajectory["assignments"]}
    out = {"completed": [], "in_progress": [], "queue": [], "scheduled": [], "unknown": []}
    for wo in instance["work_orders"]:
        a = slot[wo["id"]]
        s, e = float(a["start_bh"]), float(a["end_bh"])
        if e <= t_d:
            out["completed"].append(wo["id"])
        elif s < t_d:
            out["in_progress"].append(wo["id"])
        elif float(wo["release_bh"]) <= t_d:
            out["queue"].append(wo["id"])
        elif pm_known and wo.get("is_pm"):
            out["scheduled"].append(wo["id"])
        else:
            out["unknown"].append(wo["id"])
    return out


def known_instance(instance, state) -> dict:
    """Queued, in-progress and scheduled orders, every technician, the same meta."""
    keep = set(state["queue"]) | set(state["in_progress"]) | set(state.get("scheduled", ()))
    out = {k: v for k, v in instance.items() if k != "work_orders"}
    out["work_orders"] = [wo for wo in instance["work_orders"] if wo["id"] in keep]
    return out


def known_frozen(state, frozen_seed) -> list:
    """The standing frozen set on ``K``: in-progress orders plus the item's seed."""
    k_ids = set(state["queue"]) | set(state["in_progress"])
    out = list(state["in_progress"])
    for oid in frozen_seed or ():
        if oid in k_ids and oid not in out:
            out.append(oid)
    return out


def stale_ids(ops, state) -> list:
    """Explicitly named orders that are already completed at ``t_d``."""
    done = set(state["completed"])
    explicit, _ = named_orders(ops, {"work_orders": []})
    return [o for o in explicit if o in done]


# --------------------------------------------------------------------------- #
# Core: dispatch from t_d and the bound on the known set                        #
# --------------------------------------------------------------------------- #
def raise_releases(adjusted, t_d: float) -> int:
    """Raise every unfrozen order's release to ``t_d`` (dispatch origin).

    Due dates and weights are untouched, so the weighted tardiness of any
    schedule is unchanged; the release-aware bound evaluated at ``t = t_d``
    is unchanged as well, because it already starts every order no earlier
    than its technicians' availability, which is at least ``t_d``.  Returns
    the number of orders raised.  At ``t_d = 0`` nothing changes.
    """
    n = 0
    for wo in adjusted.instance["work_orders"]:
        if wo["id"] in adjusted.frozen:
            continue
        if float(wo["release_bh"]) < t_d:
            wo["release_bh"] = t_d
            n += 1
    return n


def restrict_batches(adjusted, keep_ids):
    """Drop batch members outside ``keep_ids`` (the orders known at ``t_d``)."""
    from l1adapter.apply import BatchGroup

    keep = set(keep_ids)
    groups = []
    for g in adjusted.batches:
        members = tuple(m for m in g.members if m in keep)
        if members:
            groups.append(BatchGroup(g.building_id, g.trade, members))
    adjusted.batches = tuple(groups)
    return adjusted


def bound_known(fields: dict, frozen: dict, t_d: float) -> dict:
    """Admissible bound on the weighted tardiness of ``fields`` from ``t_d`` on.

    Orders frozen with a start before ``t_d`` are running: their completion is
    fixed, so their weighted tardiness enters exactly, and their technician is
    available only when they finish.  Every other order is bounded by the
    release-aware LB2 at ``t = t_d``.  With nothing running and ``t_d = 0`` this
    is LB2 with every technician free at 0, the full-information certificate.
    """
    from l1guard.lb2 import lb2_detail

    by_id = {wo["id"]: wo for wo in fields["work_orders"]}
    busy: dict = {}
    fixed = 0.0
    running = set()
    for oid, slot in sorted(frozen.items()):
        s = float(slot["start_bh"])
        if s >= t_d:
            continue
        wo = by_id[oid]
        e = s + float(wo["p_bh"])
        busy[slot["tech"]] = max(busy.get(slot["tech"], t_d), e)
        fixed += float(wo["weight"]) * max(0.0, e - float(wo["due_bh"]))
        running.add(oid)
    taus: dict = {}
    for tech in fields["technicians"]:
        taus.setdefault(tech["trade"], []).append(max(float(t_d), busy.get(tech["id"], t_d)))
    ids = [wo["id"] for wo in fields["work_orders"] if wo["id"] not in running]
    detail = lb2_detail(fields, tau_by_trade=taus, t=float(t_d), order_ids=ids)
    lb = detail["lb_bh"] + fixed if running else detail["lb_bh"]
    return {"lb_bh": lb, "lb_running_bh": fixed, "n_running": len(running),
            "lb_queue_bh": detail["lb_bh"]}


def price(instance, ops, frozen, baseline, t_d: float, keep_batch=None, config=None,
          protect=None) -> dict:
    """The guard's three stages on ``instance``, dispatched from ``t_d``.

    ``frozen`` is the standing frozen set, ``baseline`` the schedule whose slots
    a freeze pins (the guard's own baseline).  ``protect`` is the set the
    guard's frozen-edit rule protects (default: ``frozen``).  ``keep_batch``
    restricts batch groups to the given ids (used by the realised run).  Returns the terminal
    state, the codes, the objective, the bound, the gap and the schedule.
    """
    from l1adapter import apply as apply_mod
    from l1adapter import dispatch as dispatch_mod
    from l1adapter import evaluate as evaluate_mod
    from l1adapter.errors import AdapterError, DispatchDeadlock
    from l1guard import findings as F
    from l1guard import guard as G
    from l1guard.config import G_CERT
    from l1guard.verdict import certified_gap

    config = config or G_CERT
    raw = json.dumps({"operations": list(ops or [])})
    res = {"terminal": None, "stage": None, "codes": [], "obj_bh": None, "lb_bh": None,
           "gap": None, "schedule": None, "n_raised": 0, "lb_running_bh": None}

    def done(term, stage, findings):
        res["terminal"], res["stage"] = term, stage
        res["codes"] = sorted({f.code for f in findings if f.blocking})
        return res

    s_find, typed, _parse = G._stage_schema(instance, raw, config)
    if any(f.blocking for f in s_find):
        return done("blocked_schema", "schema", s_find)
    if typed is None:
        return done("execution_failed", "schema", s_find)

    out = G._cycle_findings(typed)
    out.extend(G._frozen_edit_findings(instance, typed, frozen if protect is None else protect))
    try:
        adj = apply_mod.apply_operations(instance, typed, frozen_seed=frozen,
                                         baseline_schedule=baseline)
    except AdapterError as exc:
        out.append(G._error_finding(exc))
        return done("blocked_feas", "feas", out)
    for note in adj.notes:
        code = G._NOTE_CODES.get(note.split(":", 1)[0])
        if code is not None:
            out.append(F.make(code, "adapter note: {}".format(note), note=note))
    if any(f.code == "precedence_cycle" for f in out) or any(f.blocking for f in out):
        return done("blocked_feas", "feas", out)

    if keep_batch is not None:
        restrict_batches(adj, keep_batch)
    res["n_raised"] = raise_releases(adj, t_d)
    try:
        schedule = dispatch_mod.dispatch_adjusted(adj, rule=config.rule, seed=config.seed)
    except DispatchDeadlock:
        return done("execution_failed", "feas", out)
    except AdapterError as exc:
        out.append(G._error_finding(exc))
        return done("blocked_feas", "feas", out)
    validation = evaluate_mod.validate(adj, schedule)
    if not validation["feasible"]:
        out.append(F.make("validator_infeasible", "the referee rejects the schedule",
                          n_violations=len(validation["violations"]),
                          violations=validation["violations"][:5]))
        if any(f.blocking for f in out):
            return done("blocked_feas", "feas", out)

    obj = evaluate_mod.wwt(adj.instance, schedule)
    bnd = bound_known(adj.instance, adj.frozen, t_d)
    gap = certified_gap(obj, bnd["lb_bh"], config.lb_floor_bh)
    res.update(obj_bh=obj, lb_bh=bnd["lb_bh"], gap=gap, schedule=schedule,
               lb_running_bh=bnd["lb_running_bh"])
    term = "applied_with_certificate" if gap <= config.tau else "blocked_qual"
    return done(term, "qual", out)


def realised(instance, ops, started, frozen_seed, baseline, t_d: float, known_ids, config=None,
             protect=None):
    """Full-instance run: the trajectory up to ``t_d``, then the proposal, then arrivals."""
    frozen = list(started)
    for oid in frozen_seed or ():
        if oid not in frozen:
            frozen.append(oid)
    return price(instance, ops, frozen, baseline, t_d, keep_batch=known_ids, config=config,
                 protect=protect)


def trajectory(instance, frozen_seed, baseline, config=None):
    """The published baseline trajectory: ATC seed 0 with the frozen set pinned."""
    from l1adapter import apply as apply_mod
    from l1adapter import dispatch as dispatch_mod
    from l1guard.config import G_CERT

    config = config or G_CERT
    adj = apply_mod.apply_operations(instance, [], frozen_seed=list(frozen_seed or ()),
                                     baseline_schedule=baseline)
    return dispatch_mod.dispatch_adjusted(adj, rule=config.rule, seed=config.seed)


def pin_schedule(baseline, traj, started) -> dict:
    """Slots a pin uses: the trajectory's for work started before t_d, else the baseline's.

    The trajectory and the plain dispatch place every order at the same start
    and end; on a few replay instances they assign it to a different, identical
    technician of the same trade.  Work already running must stay on the
    technician the trajectory gave it, while a ``freeze`` in the proposal pins
    the guard's own baseline slot, as in the full-information guard.
    """
    done = set(started)
    t_slot = {a["wo"]: a for a in traj["assignments"]}
    rows = [t_slot[a["wo"]] if a["wo"] in done else a for a in baseline["assignments"]]
    return {k: v for k, v in baseline.items() if k != "assignments"} | {"assignments": rows}


def causal_item(instance, ops, frozen_seed, baseline, traj, anchor_cache=None,
                lenient=False, pm_known=False) -> dict:
    """Everything N8 records for one item, except the joins to published files.

    ``lenient=False`` (primary): the in-progress orders join the standing frozen
    set in full, so the guard's frozen-edit rule protects them as it protects
    the suite's own frozen set.  ``lenient=True`` (sensitivity): they are still
    pinned to their slot, but only the item's own frozen set is protected, so an
    operation that names running work is executed with the pin winning (a
    precedence edge into a running order is recorded and has no effect).
    ``pm_known=True`` (sensitivity): planned-maintenance orders are known from
    the start of the episode, so they neither delay ``t_d`` nor leave ``K``;
    one released after ``t_d`` enters ``K`` with its own release.
    """
    anchor_cache = {} if anchor_cache is None else anchor_cache
    t_d = decision_instant(ops, instance, pm_known)
    state = site_state(instance, traj, t_d, pm_known)
    known = known_instance(instance, state)
    kf = known_frozen(state, frozen_seed)
    k_ids_set = set(state["queue"]) | set(state["in_progress"]) | set(state["scheduled"])
    protect_k = [o for o in (frozen_seed or ()) if o in k_ids_set] if lenient else kf
    protect_r = list(frozen_seed or ()) if lenient else None
    stale = stale_ids(ops, state)
    explicit, members = named_orders(ops, instance)
    in_prog = set(state["in_progress"])
    started = state["completed"] + state["in_progress"]
    k_ids = state["queue"] + state["in_progress"] + state["scheduled"]
    baseline = pin_schedule(baseline, traj, started)
    row = OrderedDict(
        t_d=t_d, n_known=len(known["work_orders"]), n_queue=len(state["queue"]),
        n_scheduled=len(state["scheduled"]),
        n_in_progress=len(state["in_progress"]), n_completed=len(state["completed"]),
        n_unknown=len(state["unknown"]), stale=bool(stale), stale_ids=stale,
        names_in_progress=sorted(o for o in explicit if o in in_prog),
        n_batch_members=len(members),
        n_batch_members_known=sum(1 for m in members if m in k_ids_set),
    )
    cp = price(known, ops, kf, baseline, t_d, protect=protect_k)
    row.update(terminal_c=cp["terminal"], stage_c=cp["stage"], codes_c=cp["codes"],
               obj_K=cp["obj_bh"], lb_K=cp["lb_bh"], lb_running_K=cp["lb_running_bh"],
               g_c=cp["gap"])
    akey = (t_d, bool(pm_known))
    if akey not in anchor_cache:
        an = price(known, [], kf, baseline, t_d)
        rw0 = realised(instance, [], started, frozen_seed, baseline, t_d, k_ids)
        anchor_cache[akey] = (
            {k: an[k] for k in ("obj_bh", "lb_bh", "gap", "terminal")},
            {k: rw0[k] for k in ("obj_bh", "terminal")})
    an, rw0 = anchor_cache[akey]
    row.update(obj_anchor_K=an["obj_bh"], lb_anchor_K=an["lb_bh"], g_anchor_K=an["gap"],
               terminal_anchor_K=an["terminal"])
    row["m_c"] = None if cp["gap"] is None or an["gap"] is None else cp["gap"] - an["gap"]
    row["wwt_real_without"] = rw0["obj_bh"]
    row["wwt_real_with"] = None
    row["terminal_real"] = None
    if cp["stage"] == "qual":
        rw = realised(instance, ops, started, frozen_seed, baseline, t_d, k_ids,
                      protect=protect_r)
        row["wwt_real_with"] = rw["obj_bh"]
        row["terminal_real"] = rw["terminal"]
    return row


def gfun(obj, x):
    """The certificate's gap convention: (obj - x) / max(x, 1), clamped at zero."""
    v = (float(obj) - float(x)) / max(float(x), FLOOR_BH)
    return v if v > 0.0 else 0.0


# --------------------------------------------------------------------------- #
# Inputs                                                                       #
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv_comments(path: Path) -> list:
    with open(path, newline="") as fh:
        return list(csv.DictReader(line for line in fh if not line.startswith("#")))


def load_jsonl(path: Path) -> list:
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def frozen_key(frozen_seed) -> str:
    return ",".join(str(x) for x in (frozen_seed or ()))


def canonical_ops(item) -> list:
    return list(item[CANONICAL_FIELD[item["primary_class"]]] or [])


def select_items(items) -> list:
    return [it for it in items if it["primary_class"] != "V5" and canonical_ops(it)]


def load_dg1() -> dict:
    out = {}
    for r in read_csv_comments(DG1_PATH):
        if r["reading"] == "canonical" and r["config"] == "G_CERT":
            out[r["item_id"]] = r
    return out


def load_anchor_gaps() -> dict:
    out = {}
    for rec in json.loads(ANCHOR_PATH.read_text()):
        iid = Path(rec["instance_path"]).stem
        out[(iid, frozen_key(rec["frozen_seed"]))] = (float(rec["gap"]),
                                                      float(rec["wwt_original_bh"]))
    return out


def load_oracle():
    brackets = {}
    for r in load_jsonl(ORACLE / "brackets.jsonl"):
        brackets[(r["instance_id"], r["fingerprint"])] = r  # last row wins, as in N2
    items = {r["item_id"]: r for r in load_jsonl(ORACLE / "items.jsonl")}
    return brackets, items


def opt_lower(b):
    """The bracket's lower end, or its midpoint when the bracket is a point (N2)."""
    if b is None:
        return None
    lo, up = float(b["lower"]), float(b["upper"])
    if float(b["width_rel"]) < POINT_WIDTH_REL:
        return 0.5 * (lo + up)
    return lo


# --------------------------------------------------------------------------- #
# Workers                                                                      #
# --------------------------------------------------------------------------- #
_GROUPS: list = []


def _init(cores):
    if cores:
        try:
            os.sched_setaffinity(0, set(cores))
        except (AttributeError, OSError):
            pass


def _run_group(gi: int) -> dict:
    from l1adapter import dispatch as dispatch_mod
    from l1adapter import evaluate as evaluate_mod
    from l1adapter import instances as instances_mod

    g = _GROUPS[gi]
    instance = instances_mod.load_instance(g["instance_path"])
    baseline = dispatch_mod.dispatch_baseline(instance, "atc", 0)
    traj = trajectory(instance, g["frozen_seed"], baseline)
    # Pinned orders are appended when their slot comes up, so the list order
    # can differ; the schedule itself is the set of (order, technician, start,
    # end) rows.
    traj_equal = _slots(traj) == _slots(baseline)
    traj_relabel = _times(traj) == _times(baseline)
    w_traj = evaluate_mod.wwt(instance, traj)
    cache: dict = {}
    rows = []
    for it in g["items"]:
        ops = it["ops"]
        om = price(instance, ops, g["frozen_seed"], baseline, 0.0)
        strict = causal_item(instance, ops, g["frozen_seed"], baseline, traj, cache)
        len_row = causal_item(instance, ops, g["frozen_seed"], baseline, traj, cache,
                              lenient=True)
        pm_row = causal_item(instance, ops, g["frozen_seed"], baseline, traj, cache,
                             pm_known=True)
        row = OrderedDict(item_id=it["item_id"])
        row.update(strict)
        for k in ("terminal_c", "stage_c", "codes_c", "obj_K", "lb_K", "g_c", "m_c",
                  "wwt_real_with", "terminal_real"):
            row[k + "_len"] = len_row[k]
        for k in ("terminal_c", "stage_c", "codes_c", "obj_K", "lb_K", "g_c", "m_c",
                  "wwt_real_with", "terminal_real", "t_d", "n_known", "n_queue",
                  "n_scheduled", "stale", "names_in_progress", "g_anchor_K",
                  "wwt_real_without", "obj_anchor_K", "lb_anchor_K"):
            row[k + "_pm"] = pm_row[k]
        row.update(omni_terminal=om["terminal"], omni_gap=om["gap"], omni_obj=om["obj_bh"])
        rows.append(row)
    return {"gi": gi, "rows": rows, "traj_equal": traj_equal, "traj_relabel": traj_relabel,
            "w_traj": w_traj}


def _slots(schedule) -> set:
    return {(a["wo"], a["tech"], a["start_bh"], a["end_bh"]) for a in schedule["assignments"]}


def _times(schedule) -> set:
    return {(a["wo"], a["start_bh"], a["end_bh"]) for a in schedule["assignments"]}


def run_groups(groups, cores, workers):
    import multiprocessing as mp

    global _GROUPS
    _GROUPS = groups
    order = sorted(range(len(groups)), key=lambda i: -len(groups[i]["items"]))
    out = []
    if workers <= 1:
        _init(cores)
        for i in order:
            out.append(_run_group(i))
    else:
        ctx = mp.get_context("fork")
        with ctx.Pool(workers, initializer=_init, initargs=(cores,)) as pool:
            for res in pool.imap_unordered(_run_group, order):
                out.append(res)
    return out


# --------------------------------------------------------------------------- #
# Joins and dispositions                                                       #
# --------------------------------------------------------------------------- #
def disposition(terminal, value):
    """applied / referred on the quality stage, the refusing stage otherwise."""
    if terminal in ("applied_with_certificate", "blocked_qual"):
        return "applied" if value <= TAU else "referred"
    return {"blocked_schema": "refused_schema", "blocked_feas": "refused_feas"}.get(
        terminal, "failed")


def build_rows(items, results, dg1, anchor_gaps, brackets, oracle_items, check):
    by_item = {}
    for res in results:
        for r in res["rows"]:
            by_item[r["item_id"]] = r
    base_fp = hashlib.sha256(b"[]").hexdigest()
    rows = []
    for it in items:
        r = by_item[it["item_id"]]
        cls = it["primary_class"]
        iid = it["instance"]["instance_id"]
        fk = frozen_key(it["episode"]["frozen_seed"])
        d = dg1[it["item_id"]]
        g_anchor_full, w_base_pub = anchor_gaps[(iid, fk)]
        g_full = float(d["certified_gap"]) if d["certified_gap"] not in ("", None) else None
        obj_full = float(d["obj_bh"]) if d["obj_bh"] not in ("", None) else None
        # Omniscient reading of the causal code must be the published guard.
        check("omniscient terminal equals DG1 on " + it["item_id"],
              r["omni_terminal"] == d["terminal"], "{} vs {}".format(r["omni_terminal"],
                                                                     d["terminal"]))
        if g_full is not None:
            check("omniscient gap equals DG1 on " + it["item_id"],
                  r["omni_gap"] is not None and abs(r["omni_gap"] - g_full) <= 1e-6,
                  "{} vs {}".format(r["omni_gap"], g_full))
        check("no-proposal realised run equals the published anchor on " + it["item_id"],
              r["wwt_real_without"] is not None
              and abs(r["wwt_real_without"] - w_base_pub) <= 1e-6,
              "{} vs {}".format(r["wwt_real_without"], w_base_pub))
        if r["lb_K"] is not None:
            check("LB_K <= obj_K on " + it["item_id"], r["lb_K"] <= r["obj_K"] + 1e-6)
        if r["lb_anchor_K"] is not None:
            check("anchor LB_K <= obj_K on " + it["item_id"],
                  r["lb_anchor_K"] <= r["obj_anchor_K"] + 1e-6)
        for sfx in ("_len", "_pm"):
            if r["lb_K" + sfx] is not None:
                check("LB_K <= obj_K ({}) on {}".format(sfx, it["item_id"]),
                      r["lb_K" + sfx] <= r["obj_K" + sfx] + 1e-6)
        if r["lb_anchor_K_pm"] is not None:
            check("anchor LB_K <= obj_K (_pm) on " + it["item_id"],
                  r["lb_anchor_K_pm"] <= r["obj_anchor_K_pm"] + 1e-6)
        check("no-proposal realised run (_pm) equals the published anchor on " + it["item_id"],
              r["wwt_real_without_pm"] is not None
              and abs(r["wwt_real_without_pm"] - w_base_pub) <= 1e-6)

        m_full = None if g_full is None else g_full - g_anchor_full
        fld = CANONICAL_FIELD[cls]
        orow = oracle_items.get(it["item_id"], {})
        fp = (orow.get(fld) or {}).get("fingerprint")
        opt_item = opt_lower(brackets.get((iid, fp))) if fp else None
        opt_base = opt_lower(brackets.get((iid, base_fp)))

        out = OrderedDict(
            item_id=it["item_id"], primary_class=cls, subclass=it["subclass"],
            stratum=it["instance"]["stratum"], instance_id=iid, frozen_seed=fk,
            n_ops=len(canonical_ops(it)), op_types="|".join(sorted({o.get("op", "?")
                                                                   for o in canonical_ops(it)})),
        )
        for k in ("t_d", "n_known", "n_queue", "n_in_progress", "n_completed", "n_unknown",
                  "stale", "n_batch_members", "n_batch_members_known"):
            out[k] = r[k]
        out["names_in_progress"] = bool(r["names_in_progress"])
        out["share_unknown"] = r["n_unknown"] / max(1, r["n_unknown"] + r["n_known"]
                                                    + r["n_completed"])
        for k in ("t_d", "n_known", "n_queue", "n_scheduled", "stale", "g_anchor_K"):
            out[k + "_pm"] = r[k + "_pm"]
        out["names_in_progress_pm"] = bool(r["names_in_progress_pm"])
        for suffix in ("", "_len", "_pm"):
            term = r["terminal_c" + suffix]
            g_c, m_c = r["g_c" + suffix], r["m_c" + suffix]
            out["terminal_c" + suffix] = term
            out["codes_c" + suffix] = "|".join(r["codes_c" + suffix])
            out["obj_K" + suffix] = r["obj_K" + suffix]
            out["lb_K" + suffix] = r["lb_K" + suffix]
            out["g_c" + suffix] = g_c
            out["m_c" + suffix] = m_c
            out["disp_c_abs" + suffix] = disposition(term, g_c)
            out["disp_c_marg" + suffix] = disposition(term, m_c)
            if suffix == "":
                out["g_anchor_K"] = r["g_anchor_K"]
                out["terminal_full"] = d["terminal"]
                out["g_full"] = g_full
                out["g_anchor_full"] = g_anchor_full
                out["m_full"] = m_full
                out["disp_full_abs"] = disposition(d["terminal"], g_full)
                out["disp_full_marg"] = disposition(d["terminal"], m_full)
                out["wwt_full_info"] = obj_full
                out["wwt_base_published"] = w_base_pub
                out["wwt_real_without"] = r["wwt_real_without"]
                out["opt_item_lower"] = opt_item
                out["opt_base_lower"] = opt_base
            w_with = r["wwt_real_with" + suffix]
            out["wwt_real_with" + suffix] = w_with
            real_abs = real_marg = None
            if w_with is not None and opt_item is not None and opt_base is not None:
                real_abs = gfun(w_with, opt_item)
                real_marg = real_abs - gfun(w_base_pub, opt_base)
            out["real_abs" + suffix] = real_abs
            out["real_marg" + suffix] = real_marg
            # Added damage in weighted business hours: what the known-set
            # dispatch predicts at t_d, and what the full run realises.
            obj_an = r["obj_anchor_K_pm"] if suffix == "_pm" else r["obj_anchor_K"]
            out["obj_anchor_K" + suffix] = obj_an
            obj_k = r["obj_K" + suffix]
            pred_bh = None if obj_k is None or obj_an is None else obj_k - obj_an
            real_bh = None if w_with is None else w_with - w_base_pub
            out["pred_bh" + suffix] = pred_bh
            out["real_bh" + suffix] = real_bh
            out["err_bh" + suffix] = (None if pred_bh is None or real_bh is None
                                      else pred_bh - real_bh)
            out["err_abs" + suffix] = None if real_abs is None or g_c is None else g_c - real_abs
            out["err_marg" + suffix] = (None if real_marg is None or m_c is None
                                        else m_c - real_marg)
            if suffix == "":
                # The same comparison for the full-information certificate,
                # whose executed cost is the full-information schedule.
                fa = fm = None
                if obj_full is not None and opt_item is not None and opt_base is not None:
                    fa = gfun(obj_full, opt_item)
                    fm = fa - gfun(w_base_pub, opt_base)
                out["full_true_abs"] = fa
                out["full_true_marg"] = fm
                out["err_full_abs"] = None if fa is None or g_full is None else g_full - fa
                out["err_full_marg"] = None if fm is None or m_full is None else m_full - fm
                out["real_minus_full_bh"] = (None if w_with is None or obj_full is None
                                             else w_with - obj_full)
        rows.append(out)
    return rows


# --------------------------------------------------------------------------- #
# Summary statistics                                                           #
# --------------------------------------------------------------------------- #
def cell_seed(*parts) -> int:
    digest = hashlib.sha256("|".join([str(SEED)] + [str(p) for p in parts]).encode()).digest()
    return int.from_bytes(digest[:4], "big")


def share(rows, pred, name, b=B_BOOT):
    """Pooled share with its instance-cluster bootstrap interval (95%)."""
    import numpy as np

    import e1_intervals as ei

    if not rows:
        return {"n": 0, "k": 0, "value": None, "lo": None, "hi": None}
    clusters = OrderedDict()
    for r in rows:
        clusters.setdefault(r["instance_id"], len(clusters))
    num = np.zeros(len(clusters))
    den = np.zeros(len(clusters))
    for r in rows:
        c = clusters[r["instance_id"]]
        den[c] += 1
        num[c] += 1 if pred(r) else 0
    lo, hi, _, _ = ei.cluster_bootstrap(num, den, cell_seed(name), b)
    return {"n": int(den.sum()), "k": int(num.sum()), "value": float(num.sum() / den.sum()),
            "lo": lo, "hi": hi, "clusters": len(clusters)}


def pctl(values, q):
    import numpy as np

    vals = [v for v in values if v is not None]
    return float(np.percentile(vals, q)) if vals else None


def group_rows(rows, cls, stratum):
    return [r for r in rows if (cls == "all" or r["primary_class"] == cls)
            and (stratum == "all" or r["stratum"] == stratum)]


def summarise(rows, b=B_BOOT) -> list:
    out = []
    for cls in ("all",) + CLASSES:
        for st in ("all",) + STRATA:
            rs = group_rows(rows, cls, st)
            if not rs:
                continue
            name = "{}|{}".format(cls, st)
            both = [r for r in rs if r["disp_full_abs"] in ("applied", "referred")
                    and r["disp_c_abs"] in ("applied", "referred")]
            priced = [r for r in rs if r["err_abs"] is not None]
            priced_len = [r for r in rs if r["err_abs_len"] is not None]
            priced_pm = [r for r in rs if r["err_abs_pm"] is not None]
            rec = OrderedDict(primary_class=cls, stratum=st, n=len(rs))
            rec["stale"] = share(rs, lambda r: r["stale"], name + "|stale", b)
            rec["names_in_progress"] = share(rs, lambda r: r["names_in_progress"],
                                             name + "|inprog", b)
            rec["agree_abs"] = share(rs, lambda r: r["disp_c_abs"] == r["disp_full_abs"],
                                     name + "|agree_abs", b)
            rec["agree_marg"] = share(rs, lambda r: r["disp_c_marg"] == r["disp_full_marg"],
                                      name + "|agree_marg", b)
            rec["stale_pm"] = share(rs, lambda r: r["stale_pm"], name + "|stale_pm", b)
            rec["agree_abs_pm"] = share(rs, lambda r: r["disp_c_abs_pm"] == r["disp_full_abs"],
                                        name + "|agree_abs_pm", b)
            rec["agree_marg_pm"] = share(
                rs, lambda r: r["disp_c_marg_pm"] == r["disp_full_marg"], name + "|agree_marg_pm", b)
            live = [r for r in rs if not r["stale"]]
            rec["n_live"] = len(live)
            rec["agree_abs_live"] = share(live, lambda r: r["disp_c_abs"] == r["disp_full_abs"],
                                          name + "|agree_abs_live", b)
            rec["agree_marg_live"] = share(
                live, lambda r: r["disp_c_marg"] == r["disp_full_marg"], name + "|agree_marg_live", b)
            rec["agree_abs_len"] = share(
                rs, lambda r: r["disp_c_abs_len"] == r["disp_full_abs"], name + "|agree_abs_len", b)
            rec["agree_marg_len"] = share(
                rs, lambda r: r["disp_c_marg_len"] == r["disp_full_marg"],
                name + "|agree_marg_len", b)
            rec["n_both_priced"] = len(both)
            rec["agree_abs_priced"] = share(both, lambda r: r["disp_c_abs"] == r["disp_full_abs"],
                                            name + "|agree_abs_priced", b)
            rec["agree_marg_priced"] = share(
                both, lambda r: r["disp_c_marg"] == r["disp_full_marg"],
                name + "|agree_marg_priced", b)
            for reading, key in (("abs", "disp_c_abs"), ("marg", "disp_c_marg"),
                                 ("abs_len", "disp_c_abs_len"), ("marg_len", "disp_c_marg_len"),
                                 ("abs_pm", "disp_c_abs_pm"), ("marg_pm", "disp_c_marg_pm"),
                                 ("full_abs", "disp_full_abs"), ("full_marg", "disp_full_marg")):
                rec["referred_" + reading] = share(rs, lambda r, k=key: r[k] == "referred",
                                                   name + "|ref_" + reading, b)
                rec["applied_" + reading] = share(rs, lambda r, k=key: r[k] == "applied",
                                                  name + "|app_" + reading, b)
                rec["refused_" + reading] = share(rs, lambda r, k=key: r[k].startswith("refused"),
                                                  name + "|refd_" + reading, b)
            rec["n_priced"] = len(priced)
            rec["n_priced_len"] = len(priced_len)
            rec["n_priced_pm"] = len(priced_pm)
            for k in ("err_abs", "err_marg", "err_abs_len", "err_marg_len", "err_abs_pm",
                      "err_marg_pm", "err_full_abs", "err_full_marg"):
                if k.endswith("_len"):
                    src = priced_len
                elif k.endswith("_pm"):
                    src = priced_pm
                else:
                    src = rs if k.startswith("err_full") else priced
                vals = [r[k] for r in src]
                rec[k + "_median"] = pctl(vals, 50)
                rec[k + "_p95"] = pctl(vals, 95)
                rec[k + "_p05"] = pctl(vals, 5)
                good = [v for v in vals if v is not None]
                rec[k + "_under"] = (sum(1 for v in good if v < -0.05) / len(good)) if good else None
            for k in ("n_known", "n_queue", "t_d", "share_unknown", "t_d_pm", "n_known_pm"):
                rec[k + "_median"] = pctl([r[k] for r in rs], 50)
            out.append(rec)
    return out


def flat(rec) -> OrderedDict:
    out = OrderedDict()
    for k, v in rec.items():
        if isinstance(v, dict):
            out[k] = v["value"]
            out[k + "_lo"] = v["lo"]
            out[k + "_hi"] = v["hi"]
            out[k + "_k"] = v["k"]
        else:
            out[k] = v
    return out


# --------------------------------------------------------------------------- #
# Writers                                                                      #
# --------------------------------------------------------------------------- #
def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, float):
        return "{:.6f}".format(v)
    return str(v)


def write_csv(path: Path, rows: list, header_lines: list):
    with open(path, "w", newline="") as fh:
        for line in header_lines:
            fh.write("# " + line + "\n")
        w = csv.writer(fh)
        keys = list(rows[0].keys())
        w.writerow(keys)
        for r in rows:
            w.writerow([_fmt(r[k]) for k in keys])


def pct(v, d=1):
    return "--" if v is None else "{:.{d}f}\\%".format(100.0 * v, d=d)


def pct_md(v, d=1):
    return "--" if v is None else "{:.{d}f}%".format(100.0 * v, d=d)


def num(v, d=3):
    return "--" if v is None else "{:.{d}f}".format(v, d=d)


def count(v):
    return "{:,}".format(int(v)).replace(",", "{,}")


def bh_stats(rows) -> dict:
    """Errors in weighted business hours and the planned-known detail."""
    from scipy.stats import spearmanr

    out = {"err": OrderedDict(), "detail": OrderedDict(), "v3_td": None}
    for cls in ("all",) + CLASSES:
        rs = group_rows(rows, cls, "all")
        for sfx in ("", "_pm"):
            pr = [r for r in rs if r["err_bh" + sfx] is not None]
            e = [r["err_bh" + sfx] for r in pr]
            rec = OrderedDict(n=len(pr))
            rec["median"], rec["p05"], rec["p95"] = pctl(e, 50), pctl(e, 5), pctl(e, 95)
            rec["under2"] = (sum(1 for v in e if v < -2.0) / len(e)) if e else None
            rec["under10"] = (sum(1 for v in e if v < -10.0) / len(e)) if e else None
            rho = None
            if len(pr) >= 3:
                rho = spearmanr([r["pred_bh" + sfx] for r in pr],
                                [r["real_bh" + sfx] for r in pr]).statistic
                rho = None if rho is None or math.isnan(rho) else float(rho)
            rec["spearman"] = rho
            out["err"][(cls, sfx)] = rec
    for cls in ("V3", "benign", "V4"):
        rs = group_rows(rows, cls, "all")
        app = [r for r in rs if r["disp_c_abs_pm"] == "applied"]
        dmg = [r["real_bh_pm"] for r in app if r["real_bh_pm"] is not None]
        codes = Counter()
        for r in rs:
            if r["disp_c_abs_pm"].startswith("refused"):
                for c in (r["codes_c_pm"] or "none").split("|"):
                    codes[c] += 1
        out["detail"][cls] = OrderedDict(
            n=len(rs), applied=len(app),
            referred=sum(1 for r in rs if r["disp_c_abs_pm"] == "referred"),
            refused=sum(1 for r in rs if r["disp_c_abs_pm"].startswith("refused")),
            codes=codes, dmg_n=len(dmg), dmg_median=pctl(dmg, 50),
            dmg_max=max(dmg) if dmg else None,
            dmg_over2=sum(1 for v in dmg if v > 2.0))
    v3 = group_rows(rows, "V3", "all")
    rest = [r["t_d_pm"] for r in v3 if r["t_d_pm"] > 0.0]
    out["v3_td"] = OrderedDict(n=len(v3), zero=len(v3) - len(rest),
                               zero_share=(len(v3) - len(rest)) / len(v3),
                               rest_median=pctl(rest, 50))
    return out


def macros(summary, meta, extra=None) -> list:
    lines = ["% N8 macros, generated {} by code/scripts/n8_causal.py ({})".format(
        meta["date"], VERSION),
        "% GENERATED FILE. Do not edit by hand: rerun the script."]
    book = OrderedDict()

    def add(name, value):
        assert name.isalpha(), name
        book["nEight" + name] = value

    add("Tau", "0.20")
    add("Items", count(meta["n_items"]))
    add("Instances", count(meta["n_instances"]))
    add("BootstrapB", count(meta["B"]))
    idx = {(r["primary_class"], r["stratum"]): r for r in summary}
    cells = [(c, "all") for c in ("all",) + CLASSES] + [("all", s) for s in STRATA]
    cells += [("benign", s) for s in STRATA] + [("V3", s) for s in STRATA]
    for cls, st in cells:
        r = idx.get((cls, st))
        if r is None:
            continue
        tag = CLASS_TAG[cls] + ("" if st == "all" else STRATUM_TAG[st])
        add(tag + "N", count(r["n"]))
        add(tag + "StaleShare", pct(r["stale"]["value"]))
        add(tag + "InProgressShare", pct(r["names_in_progress"]["value"]))
        for key, mname in (("agree_abs", "AgreeAbs"), ("agree_marg", "AgreeMarg"),
                           ("agree_abs_len", "AgreeAbsLenient"),
                           ("agree_marg_len", "AgreeMargLenient"),
                           ("agree_abs_priced", "AgreeAbsPriced"),
                           ("agree_marg_priced", "AgreeMargPriced"),
                           ("agree_abs_live", "AgreeAbsLive"),
                           ("agree_marg_live", "AgreeMargLive"),
                           ("agree_abs_pm", "AgreeAbsPlanned"),
                           ("agree_marg_pm", "AgreeMargPlanned")):
            v = r[key]
            add(tag + mname, pct(v["value"]))
            add(tag + mname + "Lo", pct(v["lo"]))
            add(tag + mname + "Hi", pct(v["hi"]))
        add(tag + "NBothPriced", count(r["n_both_priced"]))
        add(tag + "NLive", count(r["n_live"]))
        add(tag + "StaleSharePlanned", pct(r["stale_pm"]["value"]))
        for key, mname in (("referred_abs", "ReferredAbs"), ("referred_marg", "ReferredMarg"),
                           ("referred_abs_len", "ReferredAbsLenient"),
                           ("referred_marg_len", "ReferredMargLenient"),
                           ("referred_full_abs", "ReferredFullAbs"),
                           ("referred_full_marg", "ReferredFullMarg"),
                           ("referred_abs_pm", "ReferredAbsPlanned"),
                           ("referred_marg_pm", "ReferredMargPlanned"),
                           ("applied_abs", "AppliedAbs"), ("applied_marg", "AppliedMarg"),
                           ("applied_full_abs", "AppliedFullAbs"),
                           ("applied_abs_pm", "AppliedAbsPlanned"),
                           ("applied_abs_len", "AppliedAbsLenient"),
                           ("refused_abs", "RefusedAbs"), ("refused_abs_len", "RefusedAbsLenient"),
                           ("refused_abs_pm", "RefusedAbsPlanned"),
                           ("refused_full_abs", "RefusedFullAbs")):
            add(tag + mname, pct(r[key]["value"]))
        add(tag + "NPriced", count(r["n_priced"]))
        add(tag + "NPricedPlanned", count(r["n_priced_pm"]))
        add(tag + "NPricedLenient", count(r["n_priced_len"]))
        for key, mname in (("err_abs", "ErrAbs"), ("err_marg", "ErrMarg"),
                           ("err_abs_pm", "ErrAbsPlanned"), ("err_marg_pm", "ErrMargPlanned"),
                           ("err_abs_len", "ErrAbsLenient"), ("err_marg_len", "ErrMargLenient"),
                           ("err_full_abs", "ErrFullAbs"), ("err_full_marg", "ErrFullMarg")):
            add(tag + mname + "Median", pct(r[key + "_median"]))
            add(tag + mname + "PNinetyFive", pct(r[key + "_p95"]))
        add(tag + "KnownMedian", count(round(r["n_known_median"])))
        add(tag + "QueueMedian", count(round(r["n_queue_median"])))
        add(tag + "DecisionMedian", "{:.1f}".format(r["t_d_median"]))
        add(tag + "DecisionPlannedMedian", "{:.1f}".format(r["t_d_pm_median"]))
        add(tag + "KnownPlannedMedian", count(round(r["n_known_pm_median"])))
        add(tag + "UnknownShareMedian", pct(r["share_unknown_median"]))
    if extra is not None:
        def bh(v):
            return "--" if v is None else "{:.2f}".format(v)

        for (cls, sfx), r in extra["err"].items():
            tag = CLASS_TAG[cls] + "ErrBh" + ("Planned" if sfx else "")
            add(tag + "N", count(r["n"]))
            add(tag + "Median", bh(r["median"]))
            add(tag + "PFive", bh(r["p05"]))
            add(tag + "PNinetyFive", bh(r["p95"]))
            add(tag + "UnderTwo", pct(r["under2"]))
            add(tag + "UnderTen", pct(r["under10"]))
            add(tag + "Spearman", "--" if r["spearman"] is None
                else "{:.2f}".format(r["spearman"]))
        for cls, d in extra["detail"].items():
            tag = CLASS_TAG[cls] + "Planned"
            add(tag + "Applied", count(d["applied"]))
            add(tag + "Referred", count(d["referred"]))
            add(tag + "Refused", count(d["refused"]))
            add(tag + "AppliedDamageMedian", bh(d["dmg_median"]))
            add(tag + "AppliedDamageMax", bh(d["dmg_max"]))
            add(tag + "AppliedDamageOverTwo", count(d["dmg_over2"]))
        t = extra["v3_td"]
        add("VThreePlannedDecisionZero", count(t["zero"]))
        add("VThreePlannedDecisionZeroShare", pct(t["zero_share"]))
        add("VThreePlannedDecisionRestMedian", "--" if t["rest_median"] is None
            else "{:.1f}".format(t["rest_median"]))
    for k, v in book.items():
        lines.append("\\newcommand{\\" + k + "}{" + v + "}")
    return lines


def summary_md(summary, rows, meta, extra=None) -> str:
    idx = {(r["primary_class"], r["stratum"]): r for r in summary}
    L = []
    A = L.append
    A("# N8. Decision-time (causal) certificate")
    A("")
    A("Generated {} by `code/scripts/n8_causal.py` ({}). {} assertions passed; wall time "
      "{:.1f} s on cores {} ({} workers); deterministic, no time budget.".format(
          meta["date"], VERSION, meta["n_checks"], meta["wall_s"], meta["cores_str"],
          meta["workers"]))
    A("")
    A("## What was computed")
    A("")
    A("- Items: every suite item with a non-empty canonical proposal (benign `gold_ops`, V1 and "
      "V2 `literal_ops`, V3 `gold_ops`, V4 `trap_ops`, V6 `forbidden_ops`; V5 has none), "
      "{} items on {} instances.".format(meta["n_items"], meta["n_instances"]))
    A("- Decision instant t_d: the largest release time over the orders the operations name "
      "(`order_id`, `ref_order_id`; for `batch` the members of the named building-and-trade "
      "group). Identifiers absent from the instance contribute nothing; a proposal naming no "
      "order has t_d = 0.")
    A("- Site state at t_d from the published baseline trajectory (ATC, seed 0, the item's "
      "frozen set pinned): completed (end <= t_d), in progress (start < t_d < end), queued "
      "(released by t_d, not started), unknown (released after t_d). Known set K = queued + "
      "in progress.")
    A("- Causal price: the guard's schema and feasibility stages on K, with the in-progress "
      "orders added to the standing frozen set; dispatch of K from t_d (unfrozen releases "
      "raised to t_d for the dispatcher only); g_c = (obj_K - LB_K) / max(LB_K, 1), where LB_K "
      "is the in-progress orders' fixed weighted tardiness plus LB2 at t = t_d on the other "
      "orders with each technician available when its running job ends. Anchor g_anchor_K: "
      "the same with no operations; marginal price m_c = g_c - g_anchor_K.")
    A("- Stale: an operation names an order that is completed at t_d. On K that identifier "
      "no longer exists, so the guard's schema stage refuses it as a dangling id.")
    A("- Planned-known reading (sensitivity): planned-maintenance orders (`is_pm`) are on the "
      "site's calendar from t = 0, so a named planned order does not delay t_d, and a planned "
      "order released after t_d stays in K with its own release.")
    A("- Lenient reading (sensitivity): in-progress orders stay pinned to their slot but are "
      "not protected by the guard's frozen-edit rule; a precedence edge into a running order "
      "is then recorded and has no effect.")
    A("- Realised cost: the full instance with every order started before t_d pinned to its "
      "baseline slot, the proposal applied at t_d (batch groups restricted to the members "
      "known at t_d), later orders released as they come. Absolute realised cost "
      "(W_with - OPT) / max(OPT, 1) with OPT the oracle bracket's lower end of the adjusted "
      "instance (midpoint when the bracket is a point, as in N2); marginal realised cost = "
      "that minus the same quantity for the no-proposal run on the baseline bracket.")
    A("- Dispositions at tau = {:.2f}: applied (price <= tau), referred (price > tau), refused "
      "at the schema or feasibility stage. Full-information dispositions: DG1 G_CERT "
      "canonical certified gap (absolute) and that gap minus the published anchor gap of "
      "`analysis/ladder/rule_anchor.json` (marginal).".format(TAU))
    A("- Intervals: 95% instance-cluster bootstrap, B = {}, over the instances that carry "
      "items of the cell.".format(meta["B"]))
    A("")
    A("## Assertions")
    A("")
    for line in meta["assertion_lines"]:
        A("- " + line)
    A("")
    A("## Table 1. Disposition agreement, causal vs full information (tau = 0.20)")
    A("")
    A("| Class | Stratum | n | stale | names running work | agree abs | agree marg | "
      "agree abs, both priced (n) | agree marg, both priced | agree abs lenient | "
      "agree marg lenient |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    for cls in ("all",) + CLASSES:
        for st in ("all",) + STRATA:
            r = idx.get((cls, st))
            if r is None or (cls != "all" and st != "all"):
                continue
            A("| {} | {} | {} | {} | {} | {} [{}, {}] | {} [{}, {}] | {} ({}) | {} | {} | {} |"
              .format(cls, st, r["n"], pct_md(r["stale"]["value"]),
                      pct_md(r["names_in_progress"]["value"]),
                      pct_md(r["agree_abs"]["value"]), pct_md(r["agree_abs"]["lo"]),
                      pct_md(r["agree_abs"]["hi"]),
                      pct_md(r["agree_marg"]["value"]), pct_md(r["agree_marg"]["lo"]),
                      pct_md(r["agree_marg"]["hi"]),
                      pct_md(r["agree_abs_priced"]["value"]), r["n_both_priced"],
                      pct_md(r["agree_marg_priced"]["value"]),
                      pct_md(r["agree_abs_len"]["value"]), pct_md(r["agree_marg_len"]["value"])))
    A("")
    A("## Table 1b. Sensitivity readings")
    A("")
    A("Live: items that are not stale (every named order still open at t_d). Planned "
      "known: planned-maintenance orders are on the calendar from t = 0, so they neither "
      "delay t_d nor leave K.")
    A("")
    A("| Class | n | agree abs, live (n) | agree marg, live | stale, planned known | "
      "agree abs, planned known | agree marg, planned known | referred abs, planned known | "
      "refused, planned known | median t_d, planned known |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for cls in ("all",) + CLASSES:
        r = idx.get((cls, "all"))
        A("| {} | {} | {} ({}) | {} | {} | {} [{}, {}] | {} [{}, {}] | {} | {} | {:.1f} |".format(
            cls, r["n"], pct_md(r["agree_abs_live"]["value"]), r["n_live"],
            pct_md(r["agree_marg_live"]["value"]), pct_md(r["stale_pm"]["value"]),
            pct_md(r["agree_abs_pm"]["value"]), pct_md(r["agree_abs_pm"]["lo"]),
            pct_md(r["agree_abs_pm"]["hi"]),
            pct_md(r["agree_marg_pm"]["value"]), pct_md(r["agree_marg_pm"]["lo"]),
            pct_md(r["agree_marg_pm"]["hi"]),
            pct_md(r["referred_abs_pm"]["value"]), pct_md(r["refused_abs_pm"]["value"]),
            r["t_d_pm_median"]))
    A("")
    A("## Table 2. Dispositions by reading")
    A("")
    A("| Class | Stratum | n | referred full abs | referred causal abs | referred causal "
      "abs lenient | referred full marg | referred causal marg | applied full abs | "
      "applied causal abs | refused causal (schema or feas) |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    for cls, st in [(c, "all") for c in ("all",) + CLASSES] + [("benign", s) for s in STRATA] \
            + [("V3", s) for s in STRATA]:
        r = idx.get((cls, st))
        if r is None:
            continue
        rs = group_rows(rows, cls, st)
        refused = sum(1 for x in rs if x["disp_c_abs"].startswith("refused")) / len(rs)
        A("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            cls, st, r["n"], pct_md(r["referred_full_abs"]["value"]),
            pct_md(r["referred_abs"]["value"]), pct_md(r["referred_abs_len"]["value"]),
            pct_md(r["referred_full_marg"]["value"]), pct_md(r["referred_marg"]["value"]),
            pct_md(r["applied_full_abs"]["value"]), pct_md(r["applied_abs"]["value"]),
            pct_md(refused)))
    A("")
    A("## Table 3. Causal price against the realised cost")
    A("")
    A("Error = price minus realised cost, on items the causal guard prices and the oracle "
      "covers. The full-information rows compare the published certificate with the cost of "
      "its own (full-information) schedule.")
    A("")
    A("| Class | Stratum | n priced | abs p05 | abs median | abs p95 | marg p05 | marg median | "
      "marg p95 | marg under -5 pts | n priced, planned known | marg median, planned known | "
      "marg p95, planned known | full-info abs median | full-info marg median | "
      "full-info marg p95 |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for cls, st in [(c, "all") for c in ("all",) + CLASSES] + [("all", s) for s in STRATA]:
        r = idx.get((cls, st))
        if r is None:
            continue
        A("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |"
          .format(cls, st, r["n_priced"], pct_md(r["err_abs_p05"]), pct_md(r["err_abs_median"]),
                  pct_md(r["err_abs_p95"]), pct_md(r["err_marg_p05"]),
                  pct_md(r["err_marg_median"]), pct_md(r["err_marg_p95"]),
                  pct_md(r["err_marg_under"]), r["n_priced_pm"],
                  pct_md(r["err_marg_pm_median"]), pct_md(r["err_marg_pm_p95"]),
                  pct_md(r["err_full_abs_median"]), pct_md(r["err_full_marg_median"]),
                  pct_md(r["err_full_marg_p95"])))
    A("")
    A("## Table 4. Information at the decision instant")
    A("")
    A("| Class | Stratum | n | median t_d (bh) | median known set | median queue | "
      "median share unknown |")
    A("|---|---|---|---|---|---|---|")
    for cls, st in [(c, "all") for c in ("all",) + CLASSES] + [("all", s) for s in STRATA]:
        r = idx.get((cls, st))
        if r is None:
            continue
        A("| {} | {} | {} | {:.1f} | {:.0f} | {:.0f} | {} |".format(
            cls, st, r["n"], r["t_d_median"], r["n_known_median"], r["n_queue_median"],
            pct_md(r["share_unknown_median"])))
    A("")
    A("## Table 5. Causal refusal codes (primary reading)")
    A("")
    A("| Class | code | items |")
    A("|---|---|---|")
    for cls in CLASSES:
        c = Counter()
        for x in rows:
            if x["primary_class"] == cls and x["disp_c_abs"].startswith("refused"):
                for code in (x["codes_c"] or "none").split("|"):
                    c[code] += 1
        for code, k in c.most_common():
            A("| {} | {} | {} |".format(cls, code, k))
    A("")
    A("## Table 6. Transitions, full-information to causal (absolute reading)")
    A("")
    A("| Class | full information | causal | items |")
    A("|---|---|---|---|")
    for cls in CLASSES:
        c = Counter((x["disp_full_abs"], x["disp_c_abs"]) for x in rows
                    if x["primary_class"] == cls)
        for (a, b), k in sorted(c.items(), key=lambda t: -t[1]):
            A("| {} | {} | {} | {} |".format(cls, a, b, k))
    A("")
    if extra is None:
        return "\n".join(L) + "\n"
    A("## Table 7. Added damage in weighted business hours")
    A("")
    A("Predicted added damage = obj_K(proposal) - obj_K(no proposal) at t_d; realised added "
      "damage = W_full(proposal at t_d) - W_full(baseline). Error = predicted - realised, on "
      "items the causal guard prices. Under 2 bh / 10 bh: share with the prediction below the "
      "realised damage by more than 2 bh / 10 bh. Spearman: rank correlation of predicted and "
      "realised added damage.")
    A("")
    A("| Class | reading | n | median (bh) | p05 (bh) | p95 (bh) | under 2 bh | under 10 bh | "
      "Spearman |")
    A("|---|---|---|---|---|---|---|---|---|")
    for (cls, sfx), r in extra["err"].items():
        A("| {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            cls, "planned known" if sfx else "primary", r["n"], num(r["median"], 2),
            num(r["p05"], 2), num(r["p95"], 2), pct_md(r["under2"]), pct_md(r["under10"]),
            num(r["spearman"], 2)))
    A("")
    A("## Table 8. Planned-known reading: dispositions and the damage of applied items")
    A("")
    A("| Class | n | applied | referred | refused | refusal codes | applied with realised "
      "damage (n) | median damage (bh) | max damage (bh) | applied above 2 bh |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for cls, d in extra["detail"].items():
        codes = ", ".join("{} {}".format(c, k) for c, k in d["codes"].most_common())
        A("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            cls, d["n"], d["applied"], d["referred"], d["refused"], codes or "--", d["dmg_n"],
            num(d["dmg_median"], 2), num(d["dmg_max"], 2), d["dmg_over2"]))
    A("")
    t = extra["v3_td"]
    A("V3 under the planned-known reading: {} of {} items ({}) have t_d = 0 (every named "
      "order is planned maintenance); the median t_d of the other {} is {} bh.".format(
          t["zero"], t["n"], pct_md(t["zero_share"]), t["n"] - t["zero"],
          num(t["rest_median"], 1)))
    A("")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def parse_cores(text):
    if not text:
        return []
    out = set()
    for part in text.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return sorted(out)


def main(argv=None):
    import suite_gate as sg

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--cores", default="8-9")
    ap.add_argument("--B", type=int, default=B_BOOT)
    ap.add_argument("--limit", type=int, default=0, help="first N items only (smoke test)")
    args = ap.parse_args(argv)
    cores = parse_cores(args.cores)

    t0 = time.time()
    items_all = load_jsonl(SUITE_PATH)
    items = select_items(items_all)
    if args.limit:
        items = items[: args.limit]
    dg1 = load_dg1()
    anchor_gaps = load_anchor_gaps()
    brackets, oracle_items = load_oracle()

    groups_by_key = OrderedDict()
    for it in items:
        path = str(sg.instance_path(it))
        fs = list(it["episode"]["frozen_seed"] or ())
        key = (path, frozen_key(fs))
        g = groups_by_key.setdefault(key, {"instance_path": path, "frozen_seed": fs,
                                           "items": []})
        g["items"].append({"item_id": it["item_id"], "ops": canonical_ops(it)})
    groups = list(groups_by_key.values())

    t_run = time.time()
    results = run_groups(groups, cores, args.workers)
    dispatch_wall = time.time() - t_run

    n_checks = [0]
    failures = []

    def check(name, ok, detail=""):
        n_checks[0] += 1
        if not ok:
            failures.append("{}: {}".format(name, detail))

    for res in results:
        g = groups[res["gi"]]
        check("baseline trajectory with the frozen set places every order at the Y1 "
              "dispatch's start and end on " + Path(g["instance_path"]).stem
              + " [" + frozen_key(g["frozen_seed"]) + "]", res["traj_relabel"])
    n_relabel = sum(1 for res in results if not res["traj_equal"])
    rows = build_rows(items, results, dg1, anchor_gaps, brackets, oracle_items, check)
    if failures:
        for f in failures[:30]:
            print("FAIL", f, file=sys.stderr)
        raise SystemExit("{} of {} checks failed".format(len(failures), n_checks[0]))

    summary = summarise(rows, args.B)
    wall = time.time() - t0
    if args.limit:
        for r in summary:
            if r["stratum"] == "all":
                print(r["primary_class"], r["n"], "stale", r["stale"]["value"],
                      "agree", r["agree_abs"]["value"], r["agree_marg"]["value"],
                      "err", r["err_abs_median"], r["err_abs_p95"])
        print("smoke run: {} items, {} checks, {:.1f} s; nothing written".format(
            len(rows), n_checks[0], wall))
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "items.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")

    inputs = OrderedDict()
    for p in (SUITE_PATH, DG1_PATH, ANCHOR_PATH, ORACLE / "brackets.jsonl",
              ORACLE / "items.jsonl", Path(__file__)):
        inputs[str(p.relative_to(ROOT))] = sha256_file(p)
    n_omni = sum(1 for r in rows if r["g_full"] is not None)
    assertion_lines = [
        "Suite SHA-256 {} ; all {} instance files verified against the instances_v10 "
        "manifest by `suite_gate.instance_path`.".format(inputs["code/suite/v0.2/suite.jsonl"][:16],
                                                         len({r['instance_id'] for r in rows})),
        "Baseline trajectory with each item's frozen set places every order at the plain Y1 "
        "ATC dispatch's start and end on all {} (instance, frozen set) groups; on {} of them "
        "some orders sit on a different, identical technician of the same trade, and running "
        "work is pinned to the trajectory's technician.".format(len(groups), n_relabel),
        "Omniscient reading of the causal code (full instance, t_d = 0) reproduces DG1's "
        "G_CERT terminal on all {} items and its certified gap on all {} priced items "
        "(tolerance 1e-6).".format(len(rows), n_omni),
        "No-proposal realised run (prefix pinned, continuation from t_d) equals the published "
        "anchor objective on every item (1e-6 bh).",
        "LB_K <= obj_K on every causal certificate and every causal anchor.",
    ]
    date = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    meta = OrderedDict(
        version=VERSION, date=date, wall_s=wall, dispatch_wall_s=dispatch_wall,
        cores=cores, cores_str=args.cores, workers=args.workers,
        omp_num_threads=os.environ.get("OMP_NUM_THREADS"),
        n_items=len(rows), n_instances=len({r["instance_id"] for r in rows}),
        n_groups=len(groups), n_checks=n_checks[0], B=args.B, tau=TAU, seed=SEED,
        instance_root=os.environ.get("L1_INSTANCE_ROOT"),
        inputs=inputs, assertion_lines=assertion_lines,
    )
    with open(OUT_DIR / "run_meta.json", "w") as fh:
        json.dump(meta, fh, indent=1)

    header = ["N8: decision-time (causal) certificate, one row per item",
              "generator: code/scripts/n8_causal.py ({})".format(VERSION),
              "inputs: code/suite/v0.2/suite.jsonl, analysis/DG1_direct_guard.csv, "
              "analysis/ladder/rule_anchor.json, results/oracle_v1/{brackets,items}.jsonl",
              "tau = {:.2f}; dispositions applied / referred / refused_schema / refused_feas"
              .format(TAU)]
    write_csv(ANALYSIS / "N8_causal.csv", rows, header)
    write_csv(ANALYSIS / "N8_causal_summary.csv", [flat(r) for r in summary],
              ["N8 summary by class and stratum", "generator: code/scripts/n8_causal.py ({})"
               .format(VERSION), "intervals: 95% instance-cluster bootstrap, B = {}".format(args.B)])
    extra = bh_stats(rows)
    (ANALYSIS / "N8_summary.md").write_text(summary_md(summary, rows, meta, extra))
    (ANALYSIS / "N8_macros.tex").write_text("\n".join(macros(summary, meta, extra)) + "\n")
    print("N8 done: {} items, {} checks, wall {:.1f} s (dispatch {:.1f} s)".format(
        len(rows), n_checks[0], wall, dispatch_wall))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
