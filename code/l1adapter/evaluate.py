"""Scoring a schedule: weighted tardiness, per-order table, referee validation.

The objective is the environment's own: ``WWT = sum_j w_j * max(0, C_j - d_j)``
over the work orders, with ``C_j`` the assignment's ``end_bh``.

**Which fields are used is the caller's choice, and it matters.**  Every
function here reads ``weight``, ``due_bh``, ``priority`` and ``release_bh`` from
the dict it is handed:

* ``wwt(adjusted, schedule)`` or ``wwt(adjusted.instance, schedule)`` scores
  against the ADJUSTED fields (the deadlines the adjusted episode actually ran
  under);
* ``wwt(adjusted.original, schedule)`` scores the same schedule against the
  ORIGINAL fields (what the untouched instance asked for).

The Phase 2 guard needs both, so neither is hard-wired: pass whichever dict the
metric is defined on.
"""

from __future__ import annotations

from ._fmwos import validator as _validator
from .apply import Adjusted


def as_instance(instance_or_adjusted) -> dict:
    """Accept an :class:`~l1adapter.apply.Adjusted` or a plain instance dict."""
    if isinstance(instance_or_adjusted, Adjusted):
        return instance_or_adjusted.instance
    return instance_or_adjusted


def wwt(instance_or_adjusted, schedule: dict) -> float:
    """Weighted tardiness of ``schedule`` under the given instance's fields."""
    inst = as_instance(instance_or_adjusted)
    wo_by_id = {wo["id"]: wo for wo in inst["work_orders"]}
    total = 0.0
    for a in schedule.get("assignments", []) or []:
        wo = wo_by_id.get(a["wo"])
        if wo is None or a.get("end_bh") is None:
            continue
        total += float(wo["weight"]) * max(0.0, float(a["end_bh"]) - float(wo["due_bh"]))
    return total


def tardiness_table(instance_or_adjusted, schedule: dict) -> list[dict]:
    """Per-order tardiness rows, sorted by weighted tardiness then order id.

    Unassigned orders appear with ``start_bh``/``end_bh`` ``None`` and no
    tardiness, so the table is always one row per work order.
    """
    inst = as_instance(instance_or_adjusted)
    by_wo = {a["wo"]: a for a in (schedule.get("assignments", []) or [])}
    rows = []
    for wo in inst["work_orders"]:
        a = by_wo.get(wo["id"])
        end = None if a is None else float(a["end_bh"])
        tard = None if end is None else max(0.0, end - float(wo["due_bh"]))
        rows.append(
            {
                "id": wo["id"],
                "trade": wo["trade"],
                "building": wo["building"],
                "priority": wo["priority"],
                "weight": float(wo["weight"]),
                "p_bh": float(wo["p_bh"]),
                "release_bh": float(wo["release_bh"]),
                "due_bh": float(wo["due_bh"]),
                "tech": None if a is None else a["tech"],
                "start_bh": None if a is None else float(a["start_bh"]),
                "end_bh": end,
                "tardiness_bh": tard,
                "weighted_tardiness_bh": None if tard is None else float(wo["weight"]) * tard,
                "breached": None if tard is None else bool(end > float(wo["due_bh"]) + 1e-9),
            }
        )
    rows.sort(key=lambda r: (-(r["weighted_tardiness_bh"] or 0.0), r["id"]))
    return rows


def validate(instance_or_adjusted, schedule: dict) -> dict:
    """Referee check: ``fmwos.validator.validate``, unmodified (passthrough).

    Returns ``{"feasible": bool, "violations": [...], "metrics": {...}}``; the
    metrics include the validator's own WWT, computed independently of
    :func:`wwt`.
    """
    return _validator.validate(as_instance(instance_or_adjusted), schedule)


def summary(instance_or_adjusted, schedule: dict) -> dict:
    """WWT plus the validator's metrics, for one-line reporting."""
    result = validate(instance_or_adjusted, schedule)
    out = {"wwt": wwt(instance_or_adjusted, schedule), "feasible": result["feasible"]}
    out.update(result["metrics"])
    return out


__all__ = ["as_instance", "wwt", "tardiness_table", "validate", "summary"]
