"""Typed errors for mechanically impossible adjustment proposals.

These are PRIMITIVES, not policy.  Each one marks a proposal that cannot be
executed against the given instance at all (a dangling id, a trade that does not
exist, a freeze with no baseline to freeze onto).  Whether such a proposal is
rejected, repaired, or counted against a guard is a Phase 2 decision; this layer
only reports the mechanical fact, with the offending identifiers attached.

``SchemaViolation`` is the one structural error: it is raised while parsing a
proposal that does not match the frozen JSON schema, before any instance is
consulted.
"""

from __future__ import annotations


class AdapterError(Exception):
    """Base class for every error raised by l1adapter."""


class SchemaViolation(AdapterError):
    """The proposal does not match the frozen adjustments schema (structure only)."""


class DanglingOrderID(AdapterError):
    """An operation names a work order id that is not in the instance."""

    def __init__(self, order_id, op=None):
        self.order_id = order_id
        self.op = op
        super().__init__(
            "work order {!r} is not in the instance (op={!r})".format(order_id, op)
        )


class DanglingBuildingID(AdapterError):
    """A batch operation names a building id that is not in the instance."""

    def __init__(self, building_id, op="batch"):
        self.building_id = building_id
        self.op = op
        super().__init__(
            "building {!r} is not in the instance (op={!r})".format(building_id, op)
        )


class UnknownTrade(AdapterError):
    """An operation names a trade that this instance does not staff."""

    def __init__(self, trade, op=None):
        self.trade = trade
        self.op = op
        super().__init__(
            "trade {!r} is not one of the instance's trades (op={!r})".format(trade, op)
        )


class TradeMismatch(AdapterError):
    """pin_next names a trade that differs from the work order's own trade."""

    def __init__(self, order_id, order_trade, stated_trade):
        self.order_id = order_id
        self.order_trade = order_trade
        self.stated_trade = stated_trade
        super().__init__(
            "pin_next names trade {!r} but work order {!r} has trade {!r}".format(
                stated_trade, order_id, order_trade
            )
        )


class NotFrozen(AdapterError):
    """unfreeze names an order that is not in the standing frozen set."""

    def __init__(self, order_id):
        self.order_id = order_id
        super().__init__(
            "work order {!r} is not frozen, so it cannot be unfrozen".format(order_id)
        )


class MissingBaseline(AdapterError):
    """A freeze needs a baseline schedule (or the order is absent from it)."""

    def __init__(self, order_id=None, reason="no baseline_schedule was given"):
        self.order_id = order_id
        self.reason = reason
        if order_id is None:
            msg = "freeze requires a baseline schedule: {}".format(reason)
        else:
            msg = "cannot freeze work order {!r}: {}".format(order_id, reason)
        super().__init__(msg)


class FrozenWindowConflict(AdapterError):
    """A frozen order's pinned start is before its own adjusted release.

    Raised when one proposal both freezes an order (pinning the baseline start)
    and moves that order's release past that start: the two operations cannot
    both hold, and executing the freeze anyway would produce a schedule the
    referee rejects under check (c).  Not in the original error list; added
    because ``freeze`` and ``reassign_window`` can contradict each other on the
    same order (see reports/adapter_build.md).
    """

    def __init__(self, order_id, start_bh, release_bh):
        self.order_id = order_id
        self.start_bh = float(start_bh)
        self.release_bh = float(release_bh)
        super().__init__(
            "work order {!r} is frozen at bh {} but its adjusted release is bh {}; "
            "the freeze and the window shift contradict each other".format(
                order_id, start_bh, release_bh
            )
        )


class FrozenPrecedenceConflict(AdapterError):
    """Two frozen orders whose pinned starts contradict a precedence path.

    ``reorder(x, "before", y)`` requires ``start_x <= start_y``.  When both
    orders are frozen, both starts are already fixed by the baseline, so the
    ordering is decided before dispatch: if ``s_x > s_y`` no execution satisfies
    both, and the proposal is mechanically impossible.  This holds for a direct
    edge and equally for a path ``x -> u -> ... -> y`` through unfrozen
    intermediates, because the operation constrains starts only and every
    intermediate can start anywhere inside ``[s_x, s_y]``.  ``path`` records the
    edges the conflict runs along.

    An edge out of a frozen order into an *unfrozen* one is NOT a conflict: the
    successor simply becomes eligible at the frozen order's pinned start
    (decisions.md 2026-08-11).
    """

    def __init__(self, order_id, ref_order_id, start_bh, ref_start_bh, path=()):
        self.order_id = order_id
        self.ref_order_id = ref_order_id
        self.start_bh = float(start_bh)
        self.ref_start_bh = float(ref_start_bh)
        self.path = tuple(path) or (order_id, ref_order_id)
        via = ""
        if len(self.path) > 2:
            via = " along the precedence path {}".format(" -> ".join(self.path))
        super().__init__(
            "work order {!r} must start no later than {!r}{}, but both are frozen and "
            "their pinned starts are bh {} and bh {}".format(
                order_id, ref_order_id, via, start_bh, ref_start_bh
            )
        )


class CyclicPrecedence(AdapterError):
    """The reorder precedence graph contains a cycle, so no start order exists.

    Raised by :func:`l1adapter.dispatch.dispatch_adjusted`, never by
    :func:`l1adapter.apply.apply_operations`: applying the operations is legal
    and records the cycle (the Phase 2 guard is what calls it a violation), but
    a cyclic instance cannot be dispatched.
    """

    def __init__(self, cycles):
        self.cycles = cycles
        super().__init__(
            "reorder precedence graph is cyclic: {}".format(cycles)
        )


class DispatchDeadlock(AdapterError):
    """Dispatch ran out of events with work orders still unassigned."""

    def __init__(self, unassigned):
        self.unassigned = list(unassigned)
        super().__init__(
            "dispatch deadlocked with {} work order(s) unassigned: {}".format(
                len(self.unassigned), self.unassigned[:10]
            )
        )


class FrozenSlotConflict(AdapterError):
    """A frozen order's baseline slot is not available at its pinned start."""

    def __init__(self, order_id, tech_id, start_bh, reason):
        self.order_id = order_id
        self.tech_id = tech_id
        self.start_bh = start_bh
        self.reason = reason
        super().__init__(
            "frozen work order {!r} cannot start on technician {!r} at {}: {}".format(
                order_id, tech_id, start_bh, reason
            )
        )


__all__ = [
    "AdapterError",
    "SchemaViolation",
    "DanglingOrderID",
    "DanglingBuildingID",
    "UnknownTrade",
    "TradeMismatch",
    "NotFrozen",
    "MissingBaseline",
    "FrozenWindowConflict",
    "FrozenPrecedenceConflict",
    "CyclicPrecedence",
    "DispatchDeadlock",
    "FrozenSlotConflict",
]
