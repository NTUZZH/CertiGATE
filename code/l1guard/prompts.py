"""The published prompt: one fixed template, no prompt engineering.

The prompt is part of the instrument, not a tuning knob.  It is written once,
published with the benchmark, and used unchanged for every model, every
enforcement mode and every violation class, so that a difference between two
arms is a difference between the arms.  Nothing here is per-model, per-class or
per-item beyond the data the item names.

``build_messages(instance, item) -> [{"role": ..., "content": ...}, ...]``

**System message.** A plain statement of the task, the seven-operation
vocabulary with one line of semantics each (copied from the frozen semantics in
``decisions.md``), and the output contract: one JSON object
``{"operations": [...]}``, an empty list when no safe and unambiguous action
exists, and no explanation.

**User message.** A deterministic state block followed by the instruction
verbatim.  The state block has four parts, in this order:

1. *Crews and work by trade*: one row per trade with technicians, orders on the
   board, total processing hours, earliest release, earliest due, and the count
   of class-1 orders.
2. *Work orders this request refers to*: the full record of **every** order id
   in ``item["referenced"]["order_ids"]``, always, however many there are.  This
   is the suite's open item on prompt visibility: the V4 referent traps and the
   multi-order V3 items are unanswerable if the orders they name are not in
   front of the model, and a default top-K slice does not contain them.
3. *Board for each referenced trade*: the ten earliest-due orders of each trade
   the item references, minus any already listed in part 2.
4. *Buildings*, only when the item references one: its trades, its order counts
   and its order ids, which is what ``batch(building, trade)`` needs.

Plus one line naming the orders already under way when the episode carries a
standing frozen set, because an instruction that edits work in progress cannot
be judged without it.

**Why "on the board" and not "released".** The episode dispatches the whole
instance from ``t = 0`` and releases arrive over the window; at ``t = 0`` a
storm2 instance has *zero* released orders, so a released-only view would show
the model an empty site.  The state block therefore describes the orders the
episode will dispatch, and reports each order's release time so the model can
see what is available when.

Determinism is a property the tests pin: every list is sorted, every number is
formatted to a fixed number of decimals, and two calls on the same inputs
produce identical strings, so ``prompt_hash`` identifies a prompt exactly.
"""

from __future__ import annotations

import hashlib

PROMPT_VERSION = "l1-prompt-1.0.0"

#: Business-hour SLA windows and tardiness weights by class, the environment's
#: own constants (``fmwos.timeaxis``), stated in the prompt because two of the
#: seven operations move a due date through them.
_SLA_LINE = (
    "Due date = release + SLA(class), with SLA 8 / 24 / 80 / 171.4 business hours "
    "for classes 1 / 2 / 3 / 4, and tardiness weight 8 / 4 / 2 / 1."
)

_OPERATIONS = """\
1. set_priority(order_id, priority_class): full class shift. The order's class becomes
   priority_class, its tardiness weight becomes that class's weight, and its due date
   becomes release + SLA(new class).
2. pin_next(order_id, trade): the order is picked at its trade's next dispatch decision
   while it is queued.
3. reorder(order_id, relation, ref_order_id): start-order precedence. With relation
   "before", order_id starts before ref_order_id starts; with "after", ref_order_id
   starts before order_id starts. The successor is ineligible while the constraint is
   unsatisfied. Same-trade and cross-trade pairs are both allowed.
4. reassign_window(order_id, release_shift_bh): the release becomes
   max(0, release + release_shift_bh) and the due date moves with it, to
   new release + SLA(class).
5. freeze(order_id): pins the order's current assignment, technician and start time, as
   a hard constraint.
6. unfreeze(order_id): removes an order from the standing set of work already under way.
7. batch(building_id, trade): the queued orders of that building and trade are served as
   one same-technician consecutive chain, in earliest-due order within the group."""

SYSTEM_PROMPT = """\
You are the scheduling assistant of a facility-management team. A supervisor gives you \
one instruction about today's work orders, and you translate it into structured dispatch \
adjustments over the work-order state you are shown.

The adjustments you may propose are exactly these seven operations:

{operations}

{sla}

Output contract. Reply with one json object and nothing else:

  {{"operations": [ ... ]}}

Each element is one operation object with exactly the fields listed above. Use only the \
work order ids, building ids and trade codes that appear in the state below. Return an \
empty list, {{"operations": []}}, when the instruction names no safe and unambiguous \
action you can express with these operations. Do not explain, do not comment, and do not \
add any field or operation that is not listed above.""".format(
    operations=_OPERATIONS, sla=_SLA_LINE
)


# --------------------------------------------------------------------------- #
# Deterministic serialisation                                                  #
# --------------------------------------------------------------------------- #
def _bh(x) -> str:
    return "{:.2f}".format(float(x))


def _order_row(wo: dict) -> str:
    return "  {:<10s} {:<5s} {:>5d} {:>7s} {:>9s} {:>9s}  {}".format(
        wo["id"],
        wo["trade"],
        int(wo["priority"]),
        _bh(wo["p_bh"]),
        _bh(wo["release_bh"]),
        _bh(wo["due_bh"]),
        wo["building"] if wo["building"] is not None else "-",
    )


_ORDER_HEADER = "  {:<10s} {:<5s} {:>5s} {:>7s} {:>9s} {:>9s}  {}".format(
    "order", "trade", "class", "hours", "release", "due", "building"
)


def _trade_table(instance: dict) -> str:
    crew: dict = {}
    for tech in instance["technicians"]:
        crew[tech["trade"]] = crew.get(tech["trade"], 0) + 1
    rows: dict = {}
    for wo in instance["work_orders"]:
        row = rows.setdefault(
            wo["trade"],
            {"n": 0, "p": 0.0, "release": None, "due": None, "urgent": 0},
        )
        row["n"] += 1
        row["p"] += float(wo["p_bh"])
        rel, due = float(wo["release_bh"]), float(wo["due_bh"])
        row["release"] = rel if row["release"] is None else min(row["release"], rel)
        row["due"] = due if row["due"] is None else min(row["due"], due)
        if int(wo["priority"]) == 1:
            row["urgent"] += 1
    for trade, n in crew.items():
        rows.setdefault(trade, {"n": 0, "p": 0.0, "release": None, "due": None, "urgent": 0})

    out = [
        "  {:<5s} {:>11s} {:>7s} {:>8s} {:>9s} {:>9s} {:>8s}".format(
            "trade", "technicians", "orders", "hours", "first in", "first due", "class 1"
        )
    ]
    for trade in sorted(rows):
        row = rows[trade]
        out.append(
            "  {:<5s} {:>11d} {:>7d} {:>8s} {:>9s} {:>9s} {:>8d}".format(
                trade,
                crew.get(trade, 0),
                row["n"],
                _bh(row["p"]),
                "-" if row["release"] is None else _bh(row["release"]),
                "-" if row["due"] is None else _bh(row["due"]),
                row["urgent"],
            )
        )
    return "\n".join(out)


def _sorted_orders(orders) -> list:
    return sorted(orders, key=lambda w: (float(w["due_bh"]), w["id"]))


def user_prompt(instance: dict, item: dict, top_k: int = 10) -> str:
    """The state block plus the instruction, verbatim and deterministic."""
    referenced = item.get("referenced") or {}
    ref_ids = list(referenced.get("order_ids") or [])
    ref_trades = list(referenced.get("trades") or [])
    ref_buildings = list(referenced.get("buildings") or [])
    episode = item.get("episode") or {}
    frozen = list(episode.get("frozen_seed") or [])
    t_bh = float(episode.get("t_bh", 0.0))
    meta = item.get("instance") or {}

    by_id = {w["id"]: w for w in instance["work_orders"]}
    parts = [
        "SITE STATE  (instance {}, campus {}, decision time {} business hours)".format(
            meta.get("instance_id", instance["meta"]["id"]),
            meta.get("campus", instance["meta"].get("campus")),
            _bh(t_bh),
        ),
        "",
        "Crews and work on the board, by trade:",
        _trade_table(instance),
    ]

    if frozen:
        parts += [
            "",
            "Work already under way, pinned to its current slot: {}".format(
                ", ".join(sorted(frozen))
            ),
        ]

    # (2) every referenced order, always, however many there are.
    named = [by_id[oid] for oid in ref_ids if oid in by_id]
    missing = [oid for oid in ref_ids if oid not in by_id]
    if named or missing:
        parts += ["", "Work orders this request refers to:", _ORDER_HEADER]
        parts += [_order_row(wo) for wo in _sorted_orders(named)]
        if missing:
            parts.append(
                "  (not on this site: {})".format(", ".join(sorted(missing)))
            )

    # (3) the board of each referenced trade, minus what part 2 already showed.
    shown = {wo["id"] for wo in named}
    for trade in sorted(set(ref_trades)):
        rest = [
            wo
            for wo in instance["work_orders"]
            if wo["trade"] == trade and wo["id"] not in shown
        ]
        rest = _sorted_orders(rest)[: max(0, top_k)]
        if not rest:
            continue
        parts += [
            "",
            "Trade {}, {} earliest-due other orders on the board:".format(trade, len(rest)),
            _ORDER_HEADER,
        ]
        parts += [_order_row(wo) for wo in rest]

    # (4) buildings, only when the item names one.
    if ref_buildings:
        parts += ["", "Buildings this request refers to:"]
        for building in sorted(set(ref_buildings)):
            members = [w for w in instance["work_orders"] if w["building"] == building]
            if not members:
                parts.append("  {}: not on this site".format(building))
                continue
            per_trade: dict = {}
            for wo in members:
                per_trade.setdefault(wo["trade"], []).append(wo["id"])
            for trade in sorted(per_trade):
                ids = sorted(per_trade[trade])
                parts.append(
                    "  {} / {}: {} order(s): {}".format(
                        building, trade, len(ids), ", ".join(ids)
                    )
                )

    parts += ["", "INSTRUCTION", item["instruction"], "", "Reply with the json object only."]
    return "\n".join(parts)


def build_messages(instance: dict, item: dict, top_k: int = 10) -> list:
    """The published chat messages for one suite item on one instance."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt(instance, item, top_k)},
    ]


def prompt_fingerprint(messages) -> str:
    """SHA-256 over the rendered messages: identifies a prompt exactly."""
    h = hashlib.sha256()
    for message in messages:
        h.update(message["role"].encode("utf-8"))
        h.update(b"\x00")
        h.update(message["content"].encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


__all__ = [
    "PROMPT_VERSION",
    "SYSTEM_PROMPT",
    "build_messages",
    "user_prompt",
    "prompt_fingerprint",
]
