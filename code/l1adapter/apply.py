"""Applying adjustment operations to an instance (frozen v1.0.0 semantics).

:func:`apply_operations` turns an instance plus a list of typed operations into
an :class:`Adjusted` bundle: a deep-copied instance whose *fields* already carry
the field-level operations, plus the *dispatch constraints* (pins, precedences,
freezes, batch chains) that :mod:`l1adapter.dispatch` honours while it runs.

Frozen semantics (decisions.md, 2026-08-11), one paragraph each:

``set_priority(order_id, c)``
    Full class shift.  ``priority = c``, ``weight = WEIGHT[c]`` and
    ``due_bh = release_bh + SLA_BH[c]``, reusing the environment's own constants
    (``fmwos.timeaxis``), which is exactly how the instance builder defines a due
    date in the first place.

``pin_next(order_id, trade)``
    The order must be picked at its trade's next dispatch decision while it is
    queued.  Recorded here, enforced in dispatch.

``reorder(a, relation, b)``
    Start-order precedence.  ``before`` requires ``start_a <= start_b``;
    ``after`` is the same edge with the ends swapped.  The successor is
    ineligible until the predecessor has started.  Same-trade and cross-trade
    pairs are both allowed.  Cycles are recorded, never rejected here:
    :meth:`Adjusted.find_cycles` reports them and the Phase 2 guard decides.

``reassign_window(order_id, shift)``
    ``release_bh' = max(0, release_bh + shift)`` and the SLA clock restarts:
    ``due_bh' = release_bh' + SLA_BH[priority]``.

``freeze(order_id)`` / ``unfreeze(order_id)``
    Freeze pins the order's baseline technician and start time as a hard
    constraint on the adjusted dispatch (so it needs ``baseline_schedule``).
    Unfreeze removes an order from the standing frozen set that the episode
    carries in ``frozen_seed`` (in-progress work, mirroring Y1's rolling
    replanner) or that an earlier ``freeze`` put there.

``batch(building_id, trade)``
    The orders of that (building, trade) are served as one same-technician
    consecutive chain, in EDD order within the group.

Operations apply in the listed order, so a ``set_priority`` followed by a
``reassign_window`` on the same order restarts the *new* class's SLA clock.
Field edits use the environment's own storage convention of 4-decimal business
hours (``fmwos.instances`` writes releases and dues rounded to 4 dp).

Nothing here accepts or rejects a proposal beyond mechanical impossibility: a
dangling id, an unknown trade, a pin whose trade contradicts the order, an
unfreeze of an order that is not frozen, a freeze with no baseline, a freeze
whose pinned start would sit before the same order's shifted release, and two
frozen orders whose pinned starts contradict a precedence path between them.
Everything else (out-of-range shifts, cycles, empty batch groups, precedence
edges that contradict a batch group's EDD order) is recorded in
:attr:`Adjusted.notes` for the Phase 2 guard to score.
"""

from __future__ import annotations

import copy
from collections import deque
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from . import ops as ops_mod
from ._fmwos import ROUND_BH, SLA_BH, WEIGHT
from .errors import (
    DanglingBuildingID,
    DanglingOrderID,
    FrozenPrecedenceConflict,
    FrozenWindowConflict,
    MissingBaseline,
    NotFrozen,
    TradeMismatch,
    UnknownTrade,
)


@dataclass(frozen=True)
class BatchGroup:
    """One ``batch`` chain: members in EDD order, to be served consecutively."""

    building_id: str
    trade: str
    members: tuple[str, ...]  # order ids, sorted by (due_bh, id) after all edits


@dataclass
class Adjusted:
    """An instance with the operations applied, plus the dispatch constraints.

    Attributes
    ----------
    instance : dict
        Deep copy of the input with the field-level edits applied.  ``meta`` is
        left untouched on purpose (unlike ``fmwos.sensitivity.scale_sla``, which
        suffixes ``meta.id``): the schedule's ``instance_id`` must keep matching
        the instance it was produced from, and a zero-operation adjustment must
        stay byte-identical to the baseline in every field.
    original : dict
        Deep copy of the input as it was, for scoring against original fields.
    ops : tuple
        The operations, in the order they were applied.
    pins : tuple[str, ...]
        Order ids to force at their trade's next dispatch decision, in proposal
        order (that order is the tie-break when two pins compete).
    precedence : tuple[tuple[str, str], ...]
        Edges ``(a, b)`` meaning ``start_a <= start_b``.
    frozen : dict[str, dict]
        ``order_id -> {"tech": str, "start_bh": float}`` from the baseline.
    batches : tuple[BatchGroup, ...]
    notes : tuple[str, ...]
        Non-fatal observations for the Phase 2 guard (cycles, empty groups,
        frozen/precedence conflicts, releases clipped at 0).
    """

    instance: dict
    original: dict
    ops: tuple = ()
    pins: tuple = ()
    precedence: tuple = ()
    frozen: dict = field(default_factory=dict)
    batches: tuple = ()
    notes: tuple = ()

    # -- constraint summary -------------------------------------------------- #
    @property
    def is_constrained(self) -> bool:
        """True when dispatch has to honour something beyond the plain rule."""
        return bool(self.pins or self.precedence or self.frozen or self.batches)

    def successors(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for a, b in self.precedence:
            out.setdefault(a, []).append(b)
        return out

    def predecessors(self) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for a, b in self.precedence:
            out.setdefault(b, set()).add(a)
        return out

    def find_cycles(self) -> list[list[str]]:
        """Return the unsatisfiable groups of the precedence graph.

        Each returned group is either a self-loop (``[a]`` from
        ``reorder(a, "before", a)``) or a strongly connected component of two or
        more orders, whose start-order constraints cannot all hold at once.  An
        empty list means the graph admits a start order.  Groups and their
        members are sorted, so the output is deterministic.
        """
        return _sccs_with_cycles(self.precedence)

    # -- convenience --------------------------------------------------------- #
    def order(self, order_id: str) -> dict:
        for wo in self.instance["work_orders"]:
            if wo["id"] == order_id:
                return wo
        raise DanglingOrderID(order_id)

    def field_changes(self) -> dict[str, dict]:
        """``order_id -> {field: (before, after)}`` for every field edit."""
        before = {w["id"]: w for w in self.original["work_orders"]}
        out: dict[str, dict] = {}
        for wo in self.instance["work_orders"]:
            b = before.get(wo["id"])
            if b is None:
                continue
            diff = {k: (b[k], wo[k]) for k in wo if k in b and b[k] != wo[k]}
            if diff:
                out[wo["id"]] = diff
        return out


# --------------------------------------------------------------------------- #
# Precedence graph helpers                                                     #
# --------------------------------------------------------------------------- #
def _sccs_with_cycles(edges: Sequence[tuple[str, str]]) -> list[list[str]]:
    """Iterative Tarjan; returns SCCs of size > 1 plus self-loops, sorted."""
    if not edges:
        return []
    succ: dict[str, list[str]] = {}
    nodes: list[str] = []
    seen: set[str] = set()
    self_loops: set[str] = set()
    for a, b in edges:
        for n in (a, b):
            if n not in seen:
                seen.add(n)
                nodes.append(n)
        succ.setdefault(a, []).append(b)
        if a == b:
            self_loops.add(a)
    nodes.sort()
    for k in succ:
        succ[k] = sorted(succ[k])

    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: dict[str, bool] = {}
    stack: list[str] = []
    counter = [0]
    out: list[list[str]] = []

    for root in nodes:
        if root in index:
            continue
        work = [(root, 0)]
        while work:
            node, pi = work[-1]
            if pi == 0:
                index[node] = low[node] = counter[0]
                counter[0] += 1
                stack.append(node)
                on_stack[node] = True
            children = succ.get(node, ())
            if pi < len(children):
                work[-1] = (node, pi + 1)
                child = children[pi]
                if child not in index:
                    work.append((child, 0))
                elif on_stack.get(child):
                    low[node] = min(low[node], index[child])
            else:
                work.pop()
                if work:
                    parent = work[-1][0]
                    low[parent] = min(low[parent], low[node])
                if low[node] == index[node]:
                    comp = []
                    while True:
                        w = stack.pop()
                        on_stack[w] = False
                        comp.append(w)
                        if w == node:
                            break
                    if len(comp) > 1 or comp[0] in self_loops:
                        out.append(sorted(comp))
    return sorted(out)


def _frozen_path_conflict(precedence: Sequence[tuple[str, str]], frozen: dict):
    """First frozen pair whose pinned starts contradict a precedence path.

    ``reorder`` constrains starts only, so a path ``a -> u -> ... -> b`` is
    satisfiable exactly when ``s_a <= s_b``: every unfrozen intermediate can
    start anywhere inside the interval.  When both endpoints are frozen their
    starts are already fixed by the baseline, so ``s_a > s_b`` on any path
    (direct or transitive) is a genuine infeasibility, and it has to be refused
    here rather than fall through to a dispatch deadlock (orchestrator ruling,
    decisions.md 2026-08-11).

    Returns ``(a, b, s_a, s_b, path)`` for the first violation, or ``None``.
    The search runs over frozen sources in sorted order and breadth-first with
    sorted adjacency, so the pair and the reported path are deterministic, and
    the path is a shortest one.  Cycles are safe (each node is visited once) and
    remain the dispatcher's ``CyclicPrecedence`` case when no frozen pair
    contradicts.
    """
    if not precedence or len(frozen) < 2:
        return None
    succ: dict[str, list[str]] = {}
    for a, b in precedence:
        succ.setdefault(a, []).append(b)
    for node in succ:
        succ[node] = sorted(dict.fromkeys(succ[node]))

    for src in sorted(frozen):
        if src not in succ:
            continue
        s_src = float(frozen[src]["start_bh"])
        parent: dict[str, str | None] = {src: None}
        queue = deque([src])
        while queue:
            node = queue.popleft()
            for nxt in succ.get(node, ()):
                if nxt in parent:
                    continue
                parent[nxt] = node
                if nxt in frozen and float(frozen[nxt]["start_bh"]) < s_src - 1e-9:
                    path = [nxt]
                    while parent[path[-1]] is not None:
                        path.append(parent[path[-1]])
                    return (
                        src,
                        nxt,
                        s_src,
                        float(frozen[nxt]["start_bh"]),
                        tuple(reversed(path)),
                    )
                queue.append(nxt)
    return None


# --------------------------------------------------------------------------- #
# apply_operations                                                             #
# --------------------------------------------------------------------------- #
def _round_bh(x: float) -> float:
    return round(float(x), ROUND_BH)


def _baseline_index(baseline_schedule) -> dict[str, dict]:
    if baseline_schedule is None:
        return {}
    out = {}
    for a in baseline_schedule.get("assignments", []) or []:
        out[a["wo"]] = a
    return out


def apply_operations(
    instance: dict,
    ops: Iterable,
    frozen_seed: Iterable[str] = (),
    baseline_schedule: dict | None = None,
) -> Adjusted:
    """Apply typed operations to ``instance`` and return an :class:`Adjusted`.

    ``frozen_seed`` is the episode's standing frozen set (orders already pinned
    to their baseline slot before the proposal is read, e.g. in-progress work);
    ``unfreeze`` removes from it and ``freeze`` adds to it.  Any non-empty
    frozen set needs ``baseline_schedule``.

    The input instance is never mutated.
    """
    ops = list(ops)
    original = copy.deepcopy(instance)
    adjusted = copy.deepcopy(instance)

    by_id = {wo["id"]: wo for wo in adjusted["work_orders"]}
    buildings = {wo["building"] for wo in adjusted["work_orders"] if wo["building"] is not None}
    known_trades = set(adjusted.get("trades", []) or [])
    known_trades.update(t["trade"] for t in adjusted.get("technicians", []) or [])
    known_trades.update(wo["trade"] for wo in adjusted["work_orders"])

    base_by_wo = _baseline_index(baseline_schedule)
    notes: list[str] = []

    def _need_order(order_id, op_name):
        if order_id not in by_id:
            raise DanglingOrderID(order_id, op_name)
        return by_id[order_id]

    tech_trade = {t["id"]: t["trade"] for t in adjusted.get("technicians", []) or []}

    def _freeze(order_id, op_name):
        wo = _need_order(order_id, op_name)
        if baseline_schedule is None:
            raise MissingBaseline(order_id, "no baseline_schedule was given")
        a = base_by_wo.get(order_id)
        if a is None:
            raise MissingBaseline(order_id, "the order is absent from the baseline schedule")
        if tech_trade.get(a["tech"]) != wo["trade"]:
            raise MissingBaseline(
                order_id,
                "the baseline assigns technician {!r} (trade {!r}), which cannot serve "
                "trade {!r}: the baseline is not this instance's".format(
                    a["tech"], tech_trade.get(a["tech"]), wo["trade"]
                ),
            )
        return {"tech": a["tech"], "start_bh": float(a["start_bh"])}

    # Standing frozen set first, then the proposal's own freezes/unfreezes.
    frozen: dict[str, dict] = {}
    for oid in frozen_seed:
        frozen[oid] = _freeze(oid, "frozen_seed")

    pins: list[str] = []
    precedence: list[tuple[str, str]] = []
    batch_keys: list[tuple[str, str]] = []

    for op in ops:
        name = op.op
        if name == "set_priority":
            wo = _need_order(op.order_id, name)
            cls = int(op.priority_class)
            wo["priority"] = cls
            wo["weight"] = WEIGHT[cls]
            wo["due_bh"] = _round_bh(float(wo["release_bh"]) + SLA_BH[cls])
        elif name == "pin_next":
            wo = _need_order(op.order_id, name)
            if op.trade not in known_trades:
                raise UnknownTrade(op.trade, name)
            if wo["trade"] != op.trade:
                raise TradeMismatch(op.order_id, wo["trade"], op.trade)
            if op.order_id not in pins:
                pins.append(op.order_id)
        elif name == "reorder":
            _need_order(op.order_id, name)
            _need_order(op.ref_order_id, name)
            edge = (
                (op.order_id, op.ref_order_id)
                if op.relation == "before"
                else (op.ref_order_id, op.order_id)
            )
            if edge not in precedence:
                precedence.append(edge)
        elif name == "reassign_window":
            wo = _need_order(op.order_id, name)
            shifted = float(wo["release_bh"]) + float(op.release_shift_bh)
            if shifted < 0.0:
                notes.append("release_clipped_at_zero:{}".format(op.order_id))
            release = _round_bh(max(0.0, shifted))
            wo["release_bh"] = release
            wo["due_bh"] = _round_bh(release + SLA_BH[int(wo["priority"])])
        elif name == "freeze":
            frozen[op.order_id] = _freeze(op.order_id, name)
        elif name == "unfreeze":
            _need_order(op.order_id, name)
            if op.order_id not in frozen:
                raise NotFrozen(op.order_id)
            del frozen[op.order_id]
        elif name == "batch":
            if op.building_id not in buildings:
                raise DanglingBuildingID(op.building_id)
            if op.trade not in known_trades:
                raise UnknownTrade(op.trade, name)
            key = (op.building_id, op.trade)
            if key not in batch_keys:
                batch_keys.append(key)
        else:  # pragma: no cover - parse_operations closes the vocabulary
            raise ValueError("unhandled operation {!r}".format(name))

    # Batch groups are materialised after every field edit, so the EDD order
    # inside a group reflects the final adjusted due dates.
    batches = []
    for building_id, trade in batch_keys:
        members = [
            wo
            for wo in adjusted["work_orders"]
            if wo["building"] == building_id and wo["trade"] == trade
        ]
        kept = [wo for wo in members if wo["id"] not in frozen]
        if len(kept) != len(members):
            notes.append("batch_members_frozen:{}/{}".format(building_id, trade))
        if not kept:
            notes.append("batch_group_empty:{}/{}".format(building_id, trade))
            continue
        kept.sort(key=lambda w: (float(w["due_bh"]), w["id"]))
        batches.append(BatchGroup(building_id, trade, tuple(w["id"] for w in kept)))

    # A freeze and a window shift on the same order can contradict each other:
    # the pinned start would sit before the order's own adjusted release, which
    # no feasible schedule can satisfy.
    for oid, slot in sorted(frozen.items()):
        wo = by_id[oid]
        if slot["start_bh"] < float(wo["release_bh"]) - 1e-9:
            raise FrozenWindowConflict(oid, slot["start_bh"], wo["release_bh"])
    # Two frozen orders decide their ordering before dispatch, whether the edge
    # between them is direct or runs through unfrozen intermediates.
    conflict = _frozen_path_conflict(precedence, frozen)
    if conflict is not None:
        a, b, s_a, s_b, path = conflict
        raise FrozenPrecedenceConflict(a, b, s_a, s_b, path)

    frozen_ids = set(frozen)
    for a, b in precedence:
        if b in frozen_ids:
            notes.append("precedence_into_frozen_order:{}->{}".format(a, b))
    for group in batches:
        rank = {oid: i for i, oid in enumerate(group.members)}
        for a, b in precedence:
            if a in rank and b in rank and rank[a] > rank[b]:
                notes.append("precedence_overrides_batch_edd:{}->{}".format(a, b))
    for group in _sccs_with_cycles(precedence):
        notes.append("precedence_cycle:{}".format(",".join(group)))

    return Adjusted(
        instance=adjusted,
        original=original,
        ops=tuple(ops),
        pins=tuple(pins),
        precedence=tuple(precedence),
        frozen=frozen,
        batches=tuple(batches),
        notes=tuple(notes),
    )


def apply_proposal(
    instance: dict,
    proposal,
    frozen_seed: Iterable[str] = (),
    baseline_schedule: dict | None = None,
    strict_schema: bool = False,
) -> Adjusted:
    """Parse a raw ``{"operations": [...]}`` proposal, then apply it."""
    parsed = ops_mod.parse_operations(proposal, strict_schema=strict_schema)
    return apply_operations(
        instance, parsed, frozen_seed=frozen_seed, baseline_schedule=baseline_schedule
    )


__all__ = ["Adjusted", "BatchGroup", "apply_operations", "apply_proposal"]
