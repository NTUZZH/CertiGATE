"""CP-SAT model of an adjusted instance that honours the instruction's constraints.

WHAT IT BOUNDS
--------------
For an adjusted instance (the fields an instruction installs) and the dispatch
constraints the same instruction imposes, the model brackets

    OPT_c = min over feasible schedules of  sum_j w_j (C_j - d_j)^+

where a schedule is feasible when every order runs once on one technician of
its trade, no technician runs two orders at once, no order starts before its
release, and the constraints below hold.  The relaxed optimum OPT of the same
fields (results/oracle_v1) drops the constraints, so OPT_c >= OPT always.

THE CONSTRAINTS, AS MODELLED
----------------------------
* precedence (a, b): start_a <= start_b, the semantics of ``reorder`` in
  ``l1adapter.apply`` (a successor may start at the same instant).
* pin_next(o): o starts no later than any other order of its trade that is not
  frozen, i.e. it is the first start among the trade's orders.  Several pins
  of one trade start in proposal order.  A pin on a frozen order is dropped,
  because the frozen slot already fixes its start.
* frozen slot (o, tech, start): o runs on that technician at that start.
* batch group (members): every member runs on one technician, and no other
  order runs on that technician between the group's first start and its last
  end.  The order of the members inside the visit is free.  The dispatcher
  serves a group in due-date order, so this is a relaxation of the
  dispatcher's chain and can only lower OPT_c; a lower OPT_c can only lower
  the instruction cost, so the lower end of the cost stays valid.

THE ROUNDED-DOWN GRID (a valid lower bound)
-------------------------------------------
CP-SAT is integer, so time is scaled to centi-business-hours.  The model is
built on a rounded-down copy, exactly the rule of code/scripts/oracle_cost.py:

    p'_j = floor_c(p_j),  r'_j = floor_c(r_j),  d'_j = ceil_c(d_j),
    frozen start g'_o = floor_c(s_o)

For every continuous feasible schedule with starts s_j, the grid starts
g_j = floor_c(s_j) are feasible for the grid model: releases and frozen starts
by monotonicity of floor; one technician's a then b, s_a + p_a <= s_b, gives
g_a + p'_a <= floor_c(s_a + p_a) <= g_b; start_a <= start_b gives
g_a <= g_b; a batch span [g_first, g_last + p'_last] stays clear of every
other order on its technician by the same inequality.  Every grid tardiness
term is at most the continuous one (floor_c(C_j) <= C_j and d'_j >= d_j).
So the CP-SAT best bound on the grid model is a valid lower bound on the
continuous constrained optimum, whatever the time budget.

THE UPPER END
-------------
The solver's incumbent is re-timed in continuous time: the technician of
every order and the order of the orders on each technician are kept, and
each order starts as early as its release, its technician, its precedence
predecessors and the pins allow; a frozen order keeps its slot (the re-timed
schedule is dropped if it cannot).  The re-timed schedule is checked by the
Y1 validator and by :func:`check_constraints`, and scored on the adjusted
fields with ``l1adapter.evaluate.wwt``.

HORIZON
-------
There is a semi-active optimum in which every start is a release or a frozen
start plus processing times along one technician's sequence (precedence and
pins add no processing), so every start is at most max(release, frozen start)
+ sum p'.  The horizon is that number plus one, which cannot cut off the grid
optimum.

SYMMETRY
--------
Technicians of one trade are identical unless a frozen slot names one of them.
Precedence edges, pins and batch groups constrain starts and groupings only, so
a permutation of a trade's technicians maps solutions to solutions.  In every
trade without a frozen slot the Y1 prefix break (``fmwos.cpsat``) is applied:
technician i may be used only if technician i - 1 is.
"""

from __future__ import annotations

import heapq
import json
import math
import time
from collections import defaultdict
from dataclasses import dataclass

from ortools.sat.python import cp_model

GRID_PER_BH = 100
CHECK_TOL_BH = 1e-9

_STATUS_NAME = {
    cp_model.OPTIMAL: "OPTIMAL",
    cp_model.FEASIBLE: "FEASIBLE",
    cp_model.INFEASIBLE: "INFEASIBLE",
    cp_model.MODEL_INVALID: "MODEL_INVALID",
    cp_model.UNKNOWN: "UNKNOWN",
}


# --------------------------------------------------------------------------- #
# Grid rounding (the rules of code/scripts/oracle_cost.py, exact on floats)    #
# --------------------------------------------------------------------------- #
def centi_floor(x: float) -> int:
    """Largest k with k / 100 <= x."""
    k = math.floor(float(x) * 100.0)
    while (k + 1) / 100.0 <= float(x):
        k += 1
    while k / 100.0 > float(x):
        k -= 1
    return int(k)


def centi_ceil(x: float) -> int:
    """Smallest k with k / 100 >= x."""
    k = math.ceil(float(x) * 100.0)
    while (k - 1) / 100.0 >= float(x):
        k -= 1
    while k / 100.0 < float(x):
        k += 1
    return int(k)


# --------------------------------------------------------------------------- #
# Constraints                                                                  #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Constraints:
    """The dispatch constraints an instruction imposes.

    precedence : ((a, b), ...)   start_a <= start_b
    pins       : (o, ...)        pin_next orders, in proposal order
    frozen     : ((o, tech, start_bh), ...) sorted by order id
    batches    : ((m1, m2, ...), ...) batch group members
    """

    precedence: tuple = ()
    pins: tuple = ()
    frozen: tuple = ()
    batches: tuple = ()

    @classmethod
    def from_adjusted(cls, adjusted, include_frozen=True) -> "Constraints":
        frozen = ()
        if include_frozen:
            frozen = tuple(sorted((oid, slot["tech"], float(slot["start_bh"]))
                                  for oid, slot in adjusted.frozen.items()))
        return cls(precedence=tuple(tuple(e) for e in adjusted.precedence),
                   pins=tuple(adjusted.pins), frozen=frozen,
                   batches=tuple(tuple(g.members) for g in adjusted.batches))

    @property
    def empty(self) -> bool:
        return not (self.precedence or self.pins or self.frozen or self.batches)

    def order_ids(self) -> set:
        out = set(self.pins)
        for a, b in self.precedence:
            out.update((a, b))
        out.update(f[0] for f in self.frozen)
        for g in self.batches:
            out.update(g)
        return out

    def restrict(self, order_ids) -> "Constraints":
        """The constraints among ``order_ids``; an edge that leaves the set is an error."""
        keep = set(order_ids)
        prec = []
        for a, b in self.precedence:
            ina, inb = a in keep, b in keep
            if ina and inb:
                prec.append((a, b))
            elif ina or inb:
                raise ValueError("precedence edge {}->{} leaves the sub-problem".format(a, b))
        for g in self.batches:
            inside = [m in keep for m in g]
            if any(inside) and not all(inside):
                raise ValueError("batch group {} leaves the sub-problem".format(g))
        return Constraints(precedence=tuple(prec),
                           pins=tuple(o for o in self.pins if o in keep),
                           frozen=tuple(f for f in self.frozen if f[0] in keep),
                           batches=tuple(g for g in self.batches if g[0] in keep))

    def key(self) -> str:
        """Canonical text; two equal keys impose the same constraints."""
        return json.dumps({"precedence": sorted([list(e) for e in set(self.precedence)]),
                           "pins": list(self.pins),
                           "frozen": [list(f) for f in self.frozen],
                           "batches": sorted([sorted(g) for g in self.batches])},
                          sort_keys=True, separators=(",", ":"))


def trade_components(instance: dict, cons: Constraints) -> list:
    """Groups of trades that carry a constraint, joined by cross-trade edges.

    A technician serves one trade, so without a cross-trade precedence edge
    nothing couples two trades.  Pins, frozen slots and batch groups live in one
    trade each.  Returns sorted tuples of trade codes, sorted; trades with no
    constraint are omitted (their constrained optimum is the relaxed one).
    """
    trade_of = {wo["id"]: wo["trade"] for wo in instance["work_orders"]}
    parent = {}

    def find(t):
        parent.setdefault(t, t)
        while parent[t] != t:
            parent[t] = parent[parent[t]]
            t = parent[t]
        return t

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for oid in cons.order_ids():
        find(trade_of[oid])
    for a, b in cons.precedence:
        union(trade_of[a], trade_of[b])
    groups = defaultdict(list)
    for t in list(parent):
        groups[find(t)].append(t)
    return sorted(tuple(sorted(g)) for g in groups.values())


def sub_instance(instance: dict, trades) -> dict:
    """The instance restricted to the orders and technicians of ``trades``."""
    trades = tuple(sorted(trades))
    keep = set(trades)
    meta = dict(instance["meta"])
    meta["id"] = "{}|{}".format(instance["meta"]["id"], "+".join(trades))
    return {
        "meta": meta,
        "trades": list(trades),
        "technicians": [t for t in instance["technicians"] if t["trade"] in keep],
        "work_orders": [wo for wo in instance["work_orders"] if wo["trade"] in keep],
    }


def _pin_chain(sub: dict, cons: Constraints) -> dict:
    """trade -> pinned order ids in proposal order, frozen pins dropped."""
    frozen_ids = {f[0] for f in cons.frozen}
    trade_of = {wo["id"]: wo["trade"] for wo in sub["work_orders"]}
    out = defaultdict(list)
    for o in cons.pins:
        if o in frozen_ids or o not in trade_of:
            continue
        if o not in out[trade_of[o]]:
            out[trade_of[o]].append(o)
    return dict(out)


def _start_edges(sub: dict, cons: Constraints) -> list:
    """Every start-order relation (a, b), start_a <= start_b: edges and pins."""
    edges = list(dict.fromkeys(tuple(e) for e in cons.precedence))
    frozen_ids = {f[0] for f in cons.frozen}
    by_trade = defaultdict(list)
    for wo in sub["work_orders"]:
        by_trade[wo["trade"]].append(wo["id"])
    for trade, chain in _pin_chain(sub, cons).items():
        for a, b in zip(chain, chain[1:]):
            edges.append((a, b))
        last = chain[-1]
        pinned = set(chain)
        for oid in by_trade[trade]:
            if oid not in pinned and oid not in frozen_ids:
                edges.append((last, oid))
    return edges


# --------------------------------------------------------------------------- #
# The model                                                                    #
# --------------------------------------------------------------------------- #
def solve(sub: dict, cons: Constraints = Constraints(), time_limit_s: float = 60.0,
          workers: int = 8, warm_start: dict | None = None,
          symmetry_break: bool = True) -> dict:
    """Bracket the constrained optimum of ``sub`` on the rounded-down grid.

    Returns a dict with ``status``, ``bound_bh`` (valid lower bound on the
    continuous constrained optimum; +inf when the grid model is infeasible),
    ``grid_obj_bh`` (the incumbent's grid objective), ``incumbent_obj_bh``
    (the re-timed continuous schedule's objective, None when there is none),
    ``schedule`` (that re-timed schedule), ``wall_s`` (whole call),
    ``solve_wall_s`` and ``solve_cpu_s`` (the CP-SAT search alone),
    ``build_s`` and model sizes.
    """
    t_call = time.perf_counter()
    cons = cons.restrict({wo["id"] for wo in sub["work_orders"]})
    wos = sub["work_orders"]
    techs = sub["technicians"]
    n = len(wos)
    idx = {wo["id"]: j for j, wo in enumerate(wos)}
    tech_idx = {t["id"]: u for u, t in enumerate(techs)}

    p = [centi_floor(wo["p_bh"]) for wo in wos]
    r = [centi_floor(wo["release_bh"]) for wo in wos]
    d = [centi_ceil(wo["due_bh"]) for wo in wos]
    w = []
    for wo in wos:
        wt = float(wo["weight"])
        if wt != round(wt) or wt < 0:
            raise ValueError("weight must be a non-negative integer: {}".format(wo["id"]))
        w.append(int(round(wt)))

    frozen = {}
    for oid, tech, start in cons.frozen:
        j = idx[oid]
        if tech not in tech_idx:
            raise ValueError("frozen order {} names an unknown technician {}".format(oid, tech))
        if techs[tech_idx[tech]]["trade"] != wos[j]["trade"]:
            raise ValueError("frozen order {} names a technician of another trade".format(oid))
        g = centi_floor(start)
        if g < r[j]:
            raise ValueError("frozen start of {} precedes its release".format(oid))
        frozen[j] = (tech_idx[tech], g)

    base = max(r) if r else 0
    for j, (_u, g) in frozen.items():
        base = max(base, g)
    horizon = max(1, base + sum(p) + 1)

    techs_by_trade = defaultdict(list)
    for u, t in enumerate(techs):
        techs_by_trade[t["trade"]].append(u)
    frozen_trades = {wos[j]["trade"] for j in frozen}

    batch_of = {}
    groups = []
    for gi, g in enumerate(cons.batches):
        members = [idx[m] for m in g]
        if any(m in frozen for m in members):
            raise ValueError("a batch group contains a frozen order")
        trades_g = {wos[m]["trade"] for m in members}
        if len(trades_g) != 1:
            raise ValueError("a batch group spans trades")
        groups.append(members)
        for m in members:
            if m in batch_of:
                raise ValueError("an order sits in two batch groups")
            batch_of[m] = gi

    model = cp_model.CpModel()
    s_vars, e_vars = [], []
    for j in range(n):
        if j in frozen:
            g = frozen[j][1]
            s = model.NewIntVar(g, g, "s_%d" % j)
        else:
            s = model.NewIntVar(r[j], horizon, "s_%d" % j)
        e = model.NewIntVar(r[j] + p[j], horizon + p[j], "e_%d" % j)
        model.Add(e == s + p[j])
        s_vars.append(s)
        e_vars.append(e)

    x = {}
    intervals_by_tech = defaultdict(list)
    for j, wo in enumerate(wos):
        eligible = techs_by_trade.get(wo["trade"], [])
        if j in frozen:
            eligible = [frozen[j][0]]
        if not eligible:
            raise ValueError("order {} has no eligible technician".format(wo["id"]))
        lits = []
        for u in eligible:
            b = model.NewBoolVar("x_%d_%d" % (j, u))
            x[(j, u)] = b
            lits.append(b)
            if j not in batch_of:
                iv = model.NewOptionalIntervalVar(s_vars[j], p[j], e_vars[j], b,
                                                  "iv_%d_%d" % (j, u))
                intervals_by_tech[u].append(iv)
        model.AddExactlyOne(lits)

    for gi, members in enumerate(groups):
        m0 = members[0]
        trade = wos[m0]["trade"]
        for u in techs_by_trade[trade]:
            for m in members[1:]:
                model.Add(x[(m, u)] == x[(m0, u)])
        span_s = model.NewIntVar(0, horizon, "span_s_%d" % gi)
        span_e = model.NewIntVar(0, horizon + max(p) if p else horizon, "span_e_%d" % gi)
        model.AddMinEquality(span_s, [s_vars[m] for m in members])
        model.AddMaxEquality(span_e, [e_vars[m] for m in members])
        size = model.NewIntVar(0, horizon + (max(p) if p else 0), "span_len_%d" % gi)
        model.Add(size == span_e - span_s)
        for u in techs_by_trade[trade]:
            iv = model.NewOptionalIntervalVar(span_s, size, span_e, x[(m0, u)],
                                              "span_%d_%d" % (gi, u))
            intervals_by_tech[u].append(iv)
        model.AddNoOverlap([model.NewIntervalVar(s_vars[m], p[m], e_vars[m], "bm_%d_%d" % (gi, m))
                            for m in members])

    for u, ivs in intervals_by_tech.items():
        model.AddNoOverlap(ivs)

    edges = _start_edges(sub, cons)
    for a, b in edges:
        model.Add(s_vars[idx[a]] <= s_vars[idx[b]])

    obj = []
    for j in range(n):
        T = model.NewIntVar(0, horizon + p[j], "T_%d" % j)
        model.Add(T >= e_vars[j] - d[j])
        obj.append(w[j] * T)
    model.Minimize(sum(obj))

    n_sym = 0
    if symmetry_break:
        for trade, us in techs_by_trade.items():
            if trade in frozen_trades or len(us) < 2:
                continue
            used = []
            for u in us:
                lits = [x[(j, u)] for j in range(n) if (j, u) in x]
                if not lits:
                    continue
                ub = model.NewBoolVar("used_%d" % u)
                model.AddMaxEquality(ub, lits)
                used.append(ub)
            for a, b in zip(used, used[1:]):
                model.Add(b <= a)
                n_sym += 1

    if warm_start:
        for a in warm_start.get("assignments", []) or []:
            j = idx.get(a.get("wo"))
            u = tech_idx.get(a.get("tech"))
            if j is None:
                continue
            if u is not None and (j, u) in x:
                model.AddHint(x[(j, u)], 1)
            if a.get("start_bh") is not None and j not in frozen:
                model.AddHint(s_vars[j], max(r[j], centi_floor(a["start_bh"])))

    build_s = time.perf_counter() - t_call
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit_s)
    solver.parameters.num_search_workers = int(workers)
    solver.parameters.random_seed = 0
    t0, c0 = time.perf_counter(), time.process_time()
    status = solver.Solve(model)
    solve_wall = time.perf_counter() - t0
    solve_cpu = time.process_time() - c0
    status_name = _STATUS_NAME.get(status, str(status))

    out = {
        "status": status_name, "bound_bh": None, "grid_obj_bh": None,
        "incumbent_obj_bh": None, "schedule": None, "retime_failed": False,
        "n_orders": n, "n_techs": len(techs), "n_edges": len(edges),
        "n_frozen": len(frozen), "n_batches": len(groups), "n_symmetry_rows": n_sym,
        "horizon_centi": horizon, "build_s": build_s,
        "solve_wall_s": solve_wall, "solve_cpu_s": solve_cpu, "workers": int(workers),
        "budget_s": float(time_limit_s),
    }
    if status == cp_model.INFEASIBLE:
        out["bound_bh"] = float("inf")
    elif status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        out["bound_bh"] = solver.BestObjectiveBound() / GRID_PER_BH
        out["grid_obj_bh"] = solver.ObjectiveValue() / GRID_PER_BH
        grid = []
        for j, wo in enumerate(wos):
            u_sel = None
            for u in (techs_by_trade[wo["trade"]] if j not in frozen else [frozen[j][0]]):
                if (j, u) in x and solver.Value(x[(j, u)]) == 1:
                    u_sel = u
                    break
            grid.append({"wo": wo["id"], "tech": techs[u_sel]["id"],
                         "g_start": int(solver.Value(s_vars[j]))})
        sched = retime(sub, grid, cons)
        if sched is None:
            out["retime_failed"] = True
        else:
            out["schedule"] = sched
            out["incumbent_obj_bh"] = schedule_wwt(sub, sched)
    else:
        # UNKNOWN: no incumbent; the bound is still a valid lower bound.
        bnd = solver.BestObjectiveBound()
        out["bound_bh"] = max(0.0, bnd / GRID_PER_BH) if math.isfinite(bnd) else 0.0
    out["wall_s"] = time.perf_counter() - t_call
    return out


# --------------------------------------------------------------------------- #
# Continuous time: re-timing, checking, scoring                                #
# --------------------------------------------------------------------------- #
def schedule_wwt(sub: dict, schedule: dict) -> float:
    by = {wo["id"]: wo for wo in sub["work_orders"]}
    tot = 0.0
    for a in schedule["assignments"]:
        wo = by[a["wo"]]
        tot += float(wo["weight"]) * max(0.0, float(a["end_bh"]) - float(wo["due_bh"]))
    return tot


def _topo_rank(order_ids, edges):
    """Kahn order over the start relations (ids sorted for ties); None on a cycle."""
    succ = defaultdict(list)
    indeg = {o: 0 for o in order_ids}
    for a, b in edges:
        succ[a].append(b)
        indeg[b] += 1
    ready = [o for o, k in indeg.items() if k == 0]
    heapq.heapify(ready)
    rank = {}
    while ready:
        o = heapq.heappop(ready)
        rank[o] = len(rank)
        for b in succ[o]:
            indeg[b] -= 1
            if indeg[b] == 0:
                heapq.heappush(ready, b)
    return rank if len(rank) == len(indeg) else None


def retime(sub: dict, grid: list, cons: Constraints) -> dict | None:
    """Continuous schedule from a grid solution, keeping technicians and sequences.

    ``grid`` rows are ``{"wo", "tech", "g_start"}``.  Orders are processed in
    increasing (grid start, start-relation rank, id); every start relation and
    every technician sequence runs forward in that key, so each order's
    predecessors are placed before it.  Returns None when a frozen order cannot
    keep its slot or the start relations have a cycle.
    """
    cons = cons.restrict({wo["id"] for wo in sub["work_orders"]})
    by = {wo["id"]: wo for wo in sub["work_orders"]}
    edges = _start_edges(sub, cons)
    rank = _topo_rank(list(by), edges)
    if rank is None:
        return None
    preds = defaultdict(list)
    for a, b in edges:
        preds[b].append(a)
    frozen = {f[0]: (f[1], float(f[2])) for f in cons.frozen}
    rows = sorted(grid, key=lambda g: (g["g_start"], rank[g["wo"]], g["wo"]))
    tech_end = {}
    start = {}
    out = []
    for g in rows:
        oid, tech = g["wo"], g["tech"]
        wo = by[oid]
        lb = float(wo["release_bh"])
        lb = max(lb, tech_end.get(tech, 0.0))
        for a in preds[oid]:
            if a not in start:
                return None
            lb = max(lb, start[a])
        if oid in frozen:
            ftech, fs = frozen[oid]
            if ftech != tech or lb > fs + CHECK_TOL_BH:
                return None
            lb = fs
        start[oid] = lb
        end = lb + float(wo["p_bh"])
        tech_end[tech] = end
        out.append({"wo": oid, "tech": tech, "start_bh": lb, "end_bh": end})
    return {"instance_id": sub["meta"]["id"], "method": "cpsat_prec_retimed", "seed": 0,
            "assignments": out}


def check_constraints(sub: dict, schedule: dict, cons: Constraints,
                      tol: float = CHECK_TOL_BH) -> list:
    """Violations of the instruction's constraints by a continuous schedule.

    Release, overlap and eligibility are the Y1 validator's job; this checks
    only what the model adds: start relations, frozen slots and batch visits.
    """
    cons = cons.restrict({wo["id"] for wo in sub["work_orders"]})
    a_by = {a["wo"]: a for a in schedule["assignments"]}
    missing = [wo["id"] for wo in sub["work_orders"] if wo["id"] not in a_by]
    if missing:
        return ["unassigned:{}".format(",".join(missing[:5]))]
    bad = []
    for a, b in _start_edges(sub, cons):
        if float(a_by[a]["start_bh"]) > float(a_by[b]["start_bh"]) + tol:
            bad.append("start_order:{}->{}".format(a, b))
    for oid, tech, st in cons.frozen:
        row = a_by[oid]
        if row["tech"] != tech or abs(float(row["start_bh"]) - float(st)) > tol:
            bad.append("frozen:{}".format(oid))
    for g in cons.batches:
        techs = {a_by[m]["tech"] for m in g}
        if len(techs) != 1:
            bad.append("batch_split:{}".format(g[0]))
            continue
        tech = techs.pop()
        lo = min(float(a_by[m]["start_bh"]) for m in g)
        hi = max(float(a_by[m]["end_bh"]) for m in g)
        members = set(g)
        for a in schedule["assignments"]:
            if a["tech"] == tech and a["wo"] not in members:
                if float(a["start_bh"]) < hi - tol and float(a["end_bh"]) > lo + tol:
                    bad.append("batch_interleaved:{}:{}".format(g[0], a["wo"]))
    return bad


def restrict_schedule(schedule: dict, order_ids) -> dict:
    keep = set(order_ids)
    return {"instance_id": schedule.get("instance_id"), "method": schedule.get("method"),
            "seed": schedule.get("seed", 0),
            "assignments": [a for a in schedule["assignments"] if a["wo"] in keep]}


__all__ = [
    "Constraints",
    "centi_floor",
    "centi_ceil",
    "trade_components",
    "sub_instance",
    "solve",
    "retime",
    "check_constraints",
    "schedule_wwt",
    "restrict_schedule",
]
