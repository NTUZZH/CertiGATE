"""A compact, deterministic state slice of an instance.

This is the data side of the Phase 3 prompt: what a proposer would be shown
about the situation it is asked to adjust.  It contains no prompt text and no
formatting choices, only the numbers, so the prompt template can be written and
rewritten later without touching this layer.

The slice has two parts:

* one row per trade (technician count, released and unreleased order counts,
  queued work in business hours, earliest due date, overdue count);
* the top-K orders by due date, each with the identifiers an operation needs
  (``id``, ``trade``, ``building``) and the quantities a decision turns on
  (``p_bh``, ``due_bh``, ``release_bh``, ``priority``).

"Released" means ``release_bh <= t``, with ``t`` the decision instant (0.0, the
episode start, by default).  Every list is sorted, so two calls on the same
inputs produce the same object and the same JSON.
"""

from __future__ import annotations

from .apply import Adjusted
from .evaluate import as_instance


def state_slice(instance_or_adjusted, top_k: int = 10, t: float = 0.0) -> dict:
    """Return the state slice of an instance (or an :class:`Adjusted`) at ``t``."""
    inst = as_instance(instance_or_adjusted)
    work_orders = inst["work_orders"]
    technicians = inst["technicians"]

    crew: dict[str, int] = {}
    for tech in technicians:
        crew[tech["trade"]] = crew.get(tech["trade"], 0) + 1

    per_trade: dict[str, dict] = {}
    for wo in work_orders:
        row = per_trade.setdefault(
            wo["trade"],
            {
                "trade": wo["trade"],
                "n_technicians": crew.get(wo["trade"], 0),
                "n_released": 0,
                "n_unreleased": 0,
                "queued_p_bh": 0.0,
                "min_due_bh": None,
                "n_overdue": 0,
                "n_priority_1": 0,
            },
        )
        released = float(wo["release_bh"]) <= t
        if released:
            row["n_released"] += 1
            row["queued_p_bh"] += float(wo["p_bh"])
            due = float(wo["due_bh"])
            if row["min_due_bh"] is None or due < row["min_due_bh"]:
                row["min_due_bh"] = due
            if due < t:
                row["n_overdue"] += 1
        else:
            row["n_unreleased"] += 1
        if int(wo["priority"]) == 1:
            row["n_priority_1"] += 1

    for trade, n in crew.items():
        per_trade.setdefault(
            trade,
            {
                "trade": trade,
                "n_technicians": n,
                "n_released": 0,
                "n_unreleased": 0,
                "queued_p_bh": 0.0,
                "min_due_bh": None,
                "n_overdue": 0,
                "n_priority_1": 0,
            },
        )

    trades = [per_trade[k] for k in sorted(per_trade)]
    for row in trades:
        row["queued_p_bh"] = round(row["queued_p_bh"], 4)

    ranked = sorted(work_orders, key=lambda w: (float(w["due_bh"]), w["id"]))[: max(0, top_k)]
    top_orders = [
        {
            "id": wo["id"],
            "trade": wo["trade"],
            "p_bh": float(wo["p_bh"]),
            "release_bh": float(wo["release_bh"]),
            "due_bh": float(wo["due_bh"]),
            "priority": int(wo["priority"]),
            "building": wo["building"],
        }
        for wo in ranked
    ]

    out = {
        "instance_id": inst["meta"]["id"],
        "t_bh": float(t),
        "n_work_orders": len(work_orders),
        "n_technicians": len(technicians),
        "trades": trades,
        "top_orders": top_orders,
    }
    if isinstance(instance_or_adjusted, Adjusted):
        out["adjustment"] = {
            "n_ops": len(instance_or_adjusted.ops),
            "pins": list(instance_or_adjusted.pins),
            "precedence": [list(e) for e in instance_or_adjusted.precedence],
            "frozen": sorted(instance_or_adjusted.frozen),
            "batches": [
                {"building_id": g.building_id, "trade": g.trade, "members": list(g.members)}
                for g in instance_or_adjusted.batches
            ],
            "notes": list(instance_or_adjusted.notes),
        }
    return out


__all__ = ["state_slice"]
