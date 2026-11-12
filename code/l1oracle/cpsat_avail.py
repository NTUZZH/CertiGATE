"""CP-SAT model of a known board at a decision instant: technician availability.

WHAT IT ADDS TO ``cpsat_prec``
------------------------------
:mod:`l1oracle.cpsat_prec` brackets the optimum of an adjusted instance on
which every technician is free at t = 0.  At a decision instant t_d some
technicians are still on a job that started before t_d.  That running work is
the site's state, not a dispatch constraint, so the board the gate sees at t_d
is the queued and planned work, every technician of its trades, and for each
technician u the instant a_u = max(t_d, end of u's running job) from which u
can take a new job.  This module is ``cpsat_prec.solve`` with that one extra
input, ``tech_available = {tech_id: a_u}``, and two corrections that the
availability needs.  ``cpsat_prec.py`` itself is not edited: its SHA-256 is
recorded by the N9 campaign (results/n9_instruction_cost/run_meta.json).

AVAILABILITY, AS MODELLED
-------------------------
Each technician u with a grid availability a'_u > 0 gets the fixed interval
[0, a'_u) in its no-overlap set, the device of the Y1 model
(``fmwos.cpsat``, the ``tech_available`` branch), so no job of u can start
before a'_u.

THE ROUNDED-DOWN GRID STAYS A VALID LOWER BOUND
-----------------------------------------------
The Y1 model rounds availability UP (``_centi_ceil``), which is right for a
feasible grid schedule and wrong for a bound.  This module rounds it DOWN,
a'_u = floor_c(a_u), with the rules of ``cpsat_prec`` for the other data
(p' = floor_c(p), r' = floor_c(r), d' = ceil_c(d), frozen g' = floor_c(s)).
For every continuous feasible schedule with starts s_j the grid starts
g_j = floor_c(s_j) remain feasible: a job of u starts at s_j >= a_u, so
g_j >= floor_c(a_u) = a'_u by monotonicity of floor, and every other step of
the argument in ``cpsat_prec`` is unchanged.  So the CP-SAT best bound on the
grid model is a valid lower bound on the continuous optimum of the board,
whatever the time budget.

SYMMETRY
--------
``cpsat_prec`` applies the Y1 prefix break (technician i may be used only if
technician i - 1 is) in every trade without a frozen slot.  The Y1 model drops
the break altogether when availability is given, because a busy technician
and a free one are not interchangeable.  Two technicians of one trade with the
same grid availability are interchangeable, so this module keeps the prefix
break within every group of technicians of one trade that share a'_u (trades
with a frozen slot still get none).  The groups partition the trade, and a
permutation inside a group maps solutions to solutions with the same
objective, so the break is valid group by group.  Without availability every
technician of a trade is in one group, which is exactly ``cpsat_prec``.

THE UPPER END
-------------
``cpsat_prec.retime`` starts every technician at t = 0
(``tech_end.get(tech, 0.0)``).  :func:`retime` here starts technician u at its
continuous availability a_u, so the re-timed incumbent is feasible for the
board.  :func:`check_availability` verifies it.

Without ``tech_available`` the model, the re-timing and the outputs are those of
``cpsat_prec.solve`` (asserted by tests/test_n11.py and by the N11 runner).
"""

from __future__ import annotations

import math
import time
from collections import defaultdict

from ortools.sat.python import cp_model

from .cpsat_prec import (
    CHECK_TOL_BH,
    GRID_PER_BH,
    Constraints,
    _STATUS_NAME,
    _start_edges,
    _topo_rank,
    centi_ceil,
    centi_floor,
    check_constraints,
    restrict_schedule,
    schedule_wwt,
    sub_instance,
    trade_components,
)

VERSION = "l1-n11-cpsat-avail-1"


def grid_availability(techs, tech_available) -> list:
    """Per technician index, the grid availability floor_c(a_u) (0 when absent)."""
    out = []
    for t in techs:
        a = 0.0 if not tech_available else float(tech_available.get(t["id"], 0.0) or 0.0)
        out.append(centi_floor(a) if a > 0.0 else 0)
    return out


def symmetry_groups(techs, avail_c, frozen_trades) -> list:
    """Lists of technician indices that are interchangeable: same trade, same a'_u.

    Trades holding a frozen slot are left out (a slot names one technician).
    Each list keeps the instance order of its technicians.
    """
    # First-seen order of (trade, a'_u), as cpsat_prec iterates its trades, so
    # that without availability the model is built constraint for constraint
    # as cpsat_prec builds it.
    groups = {}
    for u, t in enumerate(techs):
        if t["trade"] in frozen_trades:
            continue
        groups.setdefault((t["trade"], avail_c[u]), []).append(u)
    return [g for g in groups.values() if len(g) >= 2]


def solve(sub: dict, cons: Constraints = Constraints(), time_limit_s: float = 60.0,
          workers: int = 8, warm_start: dict | None = None, symmetry_break: bool = True,
          tech_available: dict | None = None) -> dict:
    """Bracket the optimum of ``sub`` with technician availability on the rounded-down grid.

    ``tech_available`` maps technician id -> a_u in business hours (missing or
    0 = free from t = 0).  Returns the keys of ``cpsat_prec.solve`` plus
    ``n_avail_intervals`` and ``n_symmetry_groups``.
    """
    t_call = time.perf_counter()
    cons = cons.restrict({wo["id"] for wo in sub["work_orders"]})
    wos = sub["work_orders"]
    techs = sub["technicians"]
    n = len(wos)
    idx = {wo["id"]: j for j, wo in enumerate(wos)}
    tech_idx = {t["id"]: u for u, t in enumerate(techs)}
    avail_c = grid_availability(techs, tech_available)

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
        if g < avail_c[tech_idx[tech]]:
            raise ValueError("frozen start of {} precedes its technician's availability"
                             .format(oid))
        frozen[j] = (tech_idx[tech], g)

    base = max(r) if r else 0
    for j, (_u, g) in frozen.items():
        base = max(base, g)
    if avail_c:
        base = max(base, max(avail_c))
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

    # Availability: the Y1 dummy interval [0, a'_u), with a'_u rounded down.
    n_avail = 0
    for u in range(len(techs)):
        a_c = avail_c[u]
        if a_c > 0:
            intervals_by_tech[u].append(model.NewIntervalVar(0, a_c, a_c, "avail_%d" % u))
            n_avail += 1

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
    sym_groups = symmetry_groups(techs, avail_c, frozen_trades) if symmetry_break else []
    for us in sym_groups:
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
        "n_symmetry_groups": len(sym_groups), "n_avail_intervals": n_avail,
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
        sched = retime(sub, grid, cons, tech_available)
        if sched is None:
            out["retime_failed"] = True
        else:
            out["schedule"] = sched
            out["incumbent_obj_bh"] = schedule_wwt(sub, sched)
    else:
        bnd = solver.BestObjectiveBound()
        out["bound_bh"] = max(0.0, bnd / GRID_PER_BH) if math.isfinite(bnd) else 0.0
    out["wall_s"] = time.perf_counter() - t_call
    return out


def retime(sub: dict, grid: list, cons: Constraints, tech_available: dict | None = None):
    """``cpsat_prec.retime`` with every technician starting at its availability a_u."""
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
    avail = {} if not tech_available else {k: float(v or 0.0) for k, v in tech_available.items()}
    rows = sorted(grid, key=lambda g: (g["g_start"], rank[g["wo"]], g["wo"]))
    tech_end = {}
    start = {}
    out = []
    for g in rows:
        oid, tech = g["wo"], g["tech"]
        wo = by[oid]
        lb = float(wo["release_bh"])
        lb = max(lb, tech_end.get(tech, avail.get(tech, 0.0)))
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
    return {"instance_id": sub["meta"]["id"], "method": "cpsat_avail_retimed", "seed": 0,
            "assignments": out}


def check_availability(schedule: dict, tech_available: dict | None,
                       tol: float = CHECK_TOL_BH) -> list:
    """Assignments that start before their technician's availability."""
    if not tech_available:
        return []
    bad = []
    for a in schedule.get("assignments", []) or []:
        av = float(tech_available.get(a["tech"], 0.0) or 0.0)
        if float(a["start_bh"]) < av - tol:
            bad.append("before_availability:{}:{}".format(a["wo"], a["tech"]))
    return bad


__all__ = [
    "VERSION",
    "Constraints",
    "centi_floor",
    "centi_ceil",
    "trade_components",
    "sub_instance",
    "grid_availability",
    "symmetry_groups",
    "solve",
    "retime",
    "check_constraints",
    "check_availability",
    "schedule_wwt",
    "restrict_schedule",
]
