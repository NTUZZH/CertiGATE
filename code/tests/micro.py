"""Hand-built micro-instances, small enough that every effect is provable.

The factory writes the same instance schema the Y1 store uses (``meta``,
``trades``, ``technicians``, ``work_orders``), so the referee validator and the
Y1 dispatcher accept these instances unchanged.
"""

from __future__ import annotations

from l1adapter import SLA_BH, WEIGHT
from l1adapter import evaluate


def order(oid, trade, p_bh, release_bh=0.0, priority=3, due_bh=None, building=None, is_pm=False):
    """One work order; ``due_bh`` defaults to the environment's r + SLA(class)."""
    rel = float(release_bh)
    due = round(rel + SLA_BH[int(priority)], 4) if due_bh is None else float(due_bh)
    return {
        "id": oid,
        "trade": trade,
        "p_bh": float(p_bh),
        "release_bh": rel,
        "due_bh": due,
        "priority": int(priority),
        "weight": float(WEIGHT[int(priority)]),
        "building": building,
        "is_pm": bool(is_pm),
    }


def make_instance(orders, technicians, inst_id="micro"):
    """``technicians`` is a list of ``(tech_id, trade)`` pairs."""
    techs = [{"id": tid, "trade": tr} for tid, tr in technicians]
    trades = sorted({tr for _, tr in technicians} | {o["trade"] for o in orders})
    return {
        "meta": {
            "id": inst_id,
            "campus": 0,
            "track": "micro",
            "size_class": len(orders),
            "window_start": "synthetic",
            "window_bh": 0.0,
            "provenance": "T",
            "seed": None,
        },
        "trades": trades,
        "technicians": techs,
        "work_orders": list(orders),
    }


def order_ids(schedule):
    """Assignment order (by start time, then technician, then order id)."""
    rows = sorted(
        schedule["assignments"], key=lambda a: (a["start_bh"], a["tech"], a["wo"])
    )
    return [a["wo"] for a in rows]


def by_wo(schedule):
    return {a["wo"]: a for a in schedule["assignments"]}


def by_tech(schedule):
    out = {}
    for a in sorted(schedule["assignments"], key=lambda a: (a["start_bh"], a["wo"])):
        out.setdefault(a["tech"], []).append(a)
    return out


def assert_feasible(instance_or_adjusted, schedule):
    """Every schedule produced in the tests must pass the Y1 referee."""
    result = evaluate.validate(instance_or_adjusted, schedule)
    assert result["feasible"], result["violations"]
    return result
