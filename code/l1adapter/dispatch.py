"""Dispatching an adjusted instance under the Y1 rules, with constraints.

``dispatch_baseline`` is a passthrough to ``fmwos.pdrs.dispatch``.  The Y1
dispatcher is the reference and is never patched.

``dispatch_adjusted`` runs the same event-driven, non-delay list-scheduling
protocol, re-implemented here so that the four *dispatch-time* constraints can
be honoured.  The rules themselves are not re-implemented: the pick callable
comes from ``fmwos.pdrs.get_rule(name)``, the documented extension point.

Why the loop is re-implemented rather than wrapped
--------------------------------------------------
Three of the constraints cannot be expressed as a filter on ``pick()``:
``freeze`` reserves a fixed interval on a named technician (so technician
availability, not just job eligibility, changes), ``batch`` binds a technician
to a chain and lets it idle until the chain's next member is released (the Y1
dispatcher never idles), and cross-trade ``reorder`` edges can unblock an order
in a trade whose state did not change at that instant.  The loop below is a
faithful superset of ``fmwos.pdrs.dispatch``: with no constraints active every
branch collapses to the Y1 code path (same event heap, same sequence counter,
same tie-breaks, same float arithmetic), which the parity gate checks on real
instances rather than by inspection.

What each constraint does at a dispatch decision
------------------------------------------------
* **eligibility filter** - an order may be picked when it is released, not
  frozen, all its precedence predecessors have started, and it is either outside
  every batch group or the current head of a group that has not been bound to a
  technician yet.  The rule sees only the eligible subset, so a queue-dependent
  rule such as ATC computes its ``pbar`` over that subset.
* **pin_next** - if any eligible order carries a pin, the pin wins over the
  rule; two competing pins are ordered by their position in the proposal.
* **reorder** - ``start_a <= start_b`` is enforced conservatively: ``b`` waits
  until ``a`` has been dispatched.  Within one instant the sweep repeats until
  no further assignment is possible, so ``a`` and ``b`` can still start at the
  same time.
* **freeze** - the order never enters a queue; it is dispatched at exactly its
  baseline ``(technician, start_bh)``.  A technician is only offered a job that
  finishes at or before its next frozen start, which is what keeps the pinned
  slot free.  A frozen order counts as started at its pinned start, so an
  outgoing precedence edge is satisfied from that instant on and its successors
  become eligible then, in any trade.
* **batch** - the group's head competes normally; whichever technician takes it
  is bound to the group and serves the rest consecutively, idling until the next
  member is released, and no other technician may take a group member.  The head
  is the earliest-due member that is free to start, that is, released and not
  precedence-blocked: a reorder that contradicts the group's EDD order moves the
  blocked member down the chain rather than stalling the chain (recorded as
  ``precedence_overrides_batch_edd`` when the operations are applied).

Conflicts between constraints are resolved by a fixed precedence, because a
Phase 1 primitive must be deterministic rather than clever: a freeze wins over a
batch chain (the chain resumes after the frozen job) and over a precedence edge
(a frozen order starts at its pinned time regardless).  Both situations are
recorded in ``Adjusted.notes`` when the operations are applied, and in the
diagnostics returned by :func:`dispatch_adjusted_verbose`, for the Phase 2 guard
to score.
"""

from __future__ import annotations

import heapq
import itertools
import json
import random
import time
from collections import defaultdict

from ._fmwos import pdrs
from .apply import Adjusted
from .errors import CyclicPrecedence, DispatchDeadlock, FrozenSlotConflict

_KIND_FREE = 0      # a technician becomes available
_KIND_RELEASE = 1   # a work order is released
_KIND_FROZEN = 2    # a frozen order reaches its pinned start
_EPS = 1e-9
_INF = float("inf")

RULES = ("edd", "wspt", "atc", "pfifo", "mor", "random")


def dispatch_baseline(instance: dict, rule: str = "atc", seed: int = 0) -> dict:
    """Run the unmodified Y1 dispatcher (``fmwos.pdrs.dispatch``)."""
    return pdrs.dispatch(instance, rule, seed)


def dispatch_adjusted(adjusted, rule: str = "atc", seed: int = 0) -> dict:
    """Dispatch an :class:`~l1adapter.apply.Adjusted` (or a plain instance).

    Returns a schedule dict with exactly the Y1 keys (``instance_id``,
    ``method``, ``seed``, ``wall_seconds``, ``decisions``, ``assignments``), so
    it can be handed to ``fmwos.validator.validate`` unchanged.  Raises
    :class:`~l1adapter.errors.CyclicPrecedence` when the reorder graph has no
    start order, and :class:`~l1adapter.errors.DispatchDeadlock` if constraints
    leave an order unassignable.
    """
    schedule, _ = _run(adjusted, rule, seed)
    return schedule


def dispatch_adjusted_verbose(adjusted, rule: str = "atc", seed: int = 0):
    """Same as :func:`dispatch_adjusted`, plus a diagnostics dict."""
    return _run(adjusted, rule, seed)


# --------------------------------------------------------------------------- #
# Schedule comparison helpers (wall_seconds is a measurement, not content)     #
# --------------------------------------------------------------------------- #
def canonical_schedule(schedule: dict) -> dict:
    """The schedule's content: everything except the measured wall time."""
    return {k: v for k, v in schedule.items() if k != "wall_seconds"}


def canonical_schedule_json(schedule: dict) -> str:
    return json.dumps(canonical_schedule(schedule), sort_keys=True, separators=(",", ":"))


def schedules_equal(a: dict, b: dict) -> bool:
    return canonical_schedule(a) == canonical_schedule(b)


# --------------------------------------------------------------------------- #
# The loop                                                                     #
# --------------------------------------------------------------------------- #
def _run(adjusted, rule: str, seed: int):
    t_start = time.perf_counter()

    adj = (
        adjusted
        if isinstance(adjusted, Adjusted)
        else Adjusted(instance=adjusted, original=adjusted)
    )
    instance = adj.instance
    technicians = instance["technicians"]
    work_orders = instance["work_orders"]

    constrained = adj.is_constrained
    if constrained:
        cycles = adj.find_cycles()
        if cycles:
            raise CyclicPrecedence(cycles)

    pick = pdrs.get_rule(rule)
    rng = random.Random(seed)

    wo_by_id = {wo["id"]: wo for wo in work_orders}
    tech_trade = {t["id"]: t["trade"] for t in technicians}

    # ---- constraint state (all empty when the adjustment is unconstrained) --
    preds = adj.predecessors()
    succs = adj.successors()
    pin_rank = {oid: i for i, oid in enumerate(adj.pins)}
    frozen = adj.frozen

    groups = []
    group_of: dict[str, int] = {}
    trade_groups: dict[str, list[int]] = defaultdict(list)
    for gi, g in enumerate(adj.batches):
        groups.append({"trade": g.trade, "remaining": set(g.members)})
        trade_groups[g.trade].append(gi)
        for member in g.members:
            group_of[member] = gi
    tech_group: dict[str, int] = {}   # technician -> group it is bound to
    group_tech: dict[int, str] = {}   # group -> the technician it is bound to
    group_free: dict[int, str] = {}   # group -> its bound technician, idle now

    frozen_by_tech: dict[str, list] = defaultdict(list)
    for oid, slot in sorted(frozen.items()):
        frozen_by_tech[slot["tech"]].append((float(slot["start_bh"]), oid))
    for tid in frozen_by_tech:
        frozen_by_tech[tid].sort()
    frozen_ptr = {tid: 0 for tid in frozen_by_tech}

    started: set[str] = set()
    queued_ids: set[str] = set()
    # Only precedence and batch membership can make a released order ineligible;
    # pins and freezes never do.
    need_filter = bool(preds or group_of)

    # ---- event heap (identical construction to fmwos.pdrs.dispatch) ---------
    queue = defaultdict(list)
    idle = defaultdict(list)
    counter = itertools.count()
    events: list = []

    for tech in technicians:
        heapq.heappush(events, (0.0, next(counter), _KIND_FREE, tech["id"], tech["trade"]))
    for wo in work_orders:
        heapq.heappush(events, (float(wo["release_bh"]), next(counter), _KIND_RELEASE, wo))
    for oid, slot in sorted(frozen.items()):
        heapq.heappush(events, (float(slot["start_bh"]), next(counter), _KIND_FROZEN, oid))

    assignments: list[dict] = []
    decisions = 0
    n_forced = 0
    n_pin_deferred = 0
    n_sweeps = 0
    n_group_waits = 0

    # ---- helpers ------------------------------------------------------------
    def _next_frozen_start(tid: str) -> float:
        lst = frozen_by_tech.get(tid)
        if not lst:
            return _INF
        i = frozen_ptr[tid]
        while i < len(lst) and lst[i][1] in started:
            i += 1
        frozen_ptr[tid] = i
        return lst[i][0] if i < len(lst) else _INF

    def _precedence_ok(oid: str) -> bool:
        ps = preds.get(oid)
        return not ps or all(a in started for a in ps)

    def _group_head(gi: int):
        """The chain's next member: earliest due among those free to start.

        "Free to start" means released and not blocked by a precedence edge, so
        a reorder that contradicts the group's EDD order moves the blocked
        member down the chain instead of stalling it.
        """
        best_key = None
        best_id = None
        for oid in groups[gi]["remaining"]:
            if oid in queued_ids and _precedence_ok(oid):
                key = (float(wo_by_id[oid]["due_bh"]), oid)
                if best_key is None or key < best_key:
                    best_key, best_id = key, oid
        return best_id

    def _eligible(job: dict) -> bool:
        jid = job["id"]
        if not _precedence_ok(jid):
            return False
        gi = group_of.get(jid)
        if gi is not None:
            if gi in group_tech:
                return False          # bound: only its own technician serves it
            return jid == _group_head(gi)
        return True

    def _forced(cand):
        best_rank = None
        best_job = None
        for j in cand:
            r = pin_rank.get(j["id"])
            if r is not None and (best_rank is None or r < best_rank):
                best_rank, best_job = r, j
        return best_job

    def _take_tech(free: list, now: float, job: dict):
        """Pop the technician that will run ``job``; None if none can host it."""
        if not frozen_by_tech:
            return heapq.heappop(free)
        p = float(job["p_bh"])
        for tid in sorted(free):
            if now + p <= _next_frozen_start(tid) + _EPS:
                free.remove(tid)
                heapq.heapify(free)
                return tid
        return None

    def _assign(job: dict, tech_id: str, trade: str, now, q: list):
        nonlocal decisions
        q.remove(job)
        jid = job["id"]
        queued_ids.discard(jid)
        started.add(jid)
        start = float(now)
        end = start + float(job["p_bh"])
        assignments.append(
            {"wo": jid, "tech": tech_id, "start_bh": start, "end_bh": end}
        )
        decisions += 1
        heapq.heappush(events, (end, next(counter), _KIND_FREE, tech_id, trade))
        gi = group_of.get(jid)
        if gi is not None:
            g = groups[gi]
            g["remaining"].discard(jid)
            group_tech[gi] = tech_id
            tech_group[tech_id] = gi
            if not g["remaining"]:
                tech_group.pop(tech_id, None)

    def _serve_groups(trade: str, now) -> bool:
        """Let each bound, idle technician take its chain's next member."""
        nonlocal n_group_waits
        progressed = False
        for gi in trade_groups.get(trade, ()):
            tid = group_free.get(gi)
            if tid is None or not groups[gi]["remaining"]:
                continue
            head = _group_head(gi)
            if head is None:
                n_group_waits += 1
                continue
            job = wo_by_id[head]
            if now + float(job["p_bh"]) > _next_frozen_start(tid) + _EPS:
                continue
            del group_free[gi]
            _assign(job, tid, trade, now, queue[trade])
            progressed = True
        return progressed

    def try_dispatch(trade: str, now) -> bool:
        nonlocal n_forced, n_pin_deferred
        progressed = False
        q = queue[trade]
        free = idle[trade]
        blocked: set[str] = set()
        while free and q:
            # The filter is only built when something can actually block a
            # pick.  Its cost is O(|queue|), the same order as the rule's own
            # min-scan over the queue, so the wrapper stays in the complexity
            # class of the Y1 dispatcher.
            if constrained and (need_filter or blocked):
                cand = [j for j in q if j["id"] not in blocked and _eligible(j)]
                if not cand:
                    break
            else:
                cand = q
            job = _forced(cand) if pin_rank else None
            forced = job is not None
            if job is None:
                job = pick(cand, now, rng)
            tech_id = _take_tech(free, now, job)
            if tech_id is None:
                blocked.add(job["id"])
                if forced:
                    n_pin_deferred += 1
                continue
            if forced:
                n_forced += 1
            _assign(job, tech_id, trade, now, q)
            progressed = True
        return progressed

    # ---- main loop ----------------------------------------------------------
    while events:
        now = events[0][0]
        touched = set()
        frozen_now = []
        # Drain every event at this instant before any pick is made.
        while events and events[0][0] == now:
            _, _, kind, *payload = heapq.heappop(events)
            if kind == _KIND_FREE:
                tech_id, trade = payload
                gi = tech_group.get(tech_id)
                if gi is not None and groups[gi]["remaining"]:
                    group_free[gi] = tech_id
                else:
                    if gi is not None:
                        tech_group.pop(tech_id, None)
                    heapq.heappush(idle[trade], tech_id)
                touched.add(trade)
            elif kind == _KIND_RELEASE:
                wo = payload[0]
                if wo["id"] in frozen:
                    continue          # frozen orders run at their pinned slot
                queue[wo["trade"]].append(wo)
                queued_ids.add(wo["id"])
                touched.add(wo["trade"])
            else:  # _KIND_FROZEN
                frozen_now.append(payload[0])

        for oid in sorted(frozen_now):
            slot = frozen[oid]
            tid = slot["tech"]
            trade = tech_trade[tid]
            job = wo_by_id[oid]
            if tid in idle[trade]:
                idle[trade].remove(tid)
                heapq.heapify(idle[trade])
            else:
                gi = tech_group.get(tid)
                if gi is not None and group_free.get(gi) == tid:
                    del group_free[gi]
                else:
                    raise FrozenSlotConflict(
                        oid, tid, slot["start_bh"],
                        "the technician is not idle at the pinned start",
                    )
            start = float(slot["start_bh"])
            end = start + float(job["p_bh"])
            assignments.append({"wo": oid, "tech": tid, "start_bh": start, "end_bh": end})
            decisions += 1
            started.add(oid)
            heapq.heappush(events, (end, next(counter), _KIND_FREE, tid, trade))
            touched.add(trade)
            # A frozen order starting satisfies its outgoing precedence edges,
            # which can make a successor eligible in a trade that had no event
            # at this instant.  The sweep below is seeded from the touched
            # trades, so those successors' trades have to be added here or they
            # are never re-examined (they would wait for an event that no
            # longer exists, which is what deadlocked before 2026-08-11).
            for nxt in succs.get(oid, ()):
                touched.add(wo_by_id[nxt]["trade"])

        sweep = sorted(touched)
        while True:
            n_sweeps += 1
            progressed = False
            for trade in sweep:
                if groups:
                    progressed |= _serve_groups(trade, now)
                progressed |= try_dispatch(trade, now)
            if not constrained or not progressed:
                break
            # A dispatch can unblock an order in a trade that no event touched
            # (cross-trade precedence), so re-sweep every trade that can still
            # move at this instant.
            sweep = [
                tr
                for tr in sorted(queue)
                if queue[tr]
                and (idle[tr] or any(gi in group_free for gi in trade_groups.get(tr, ())))
            ]
            if not sweep:
                break

    if len(assignments) != len(work_orders):
        assigned = {a["wo"] for a in assignments}
        raise DispatchDeadlock([w["id"] for w in work_orders if w["id"] not in assigned])

    schedule = {
        "instance_id": instance["meta"]["id"],
        "method": rule,
        "seed": seed,
        "wall_seconds": time.perf_counter() - t_start,
        "decisions": decisions,
        "assignments": assignments,
    }
    diagnostics = {
        "constrained": constrained,
        "n_pins": len(pin_rank),
        "n_forced_picks": n_forced,
        "n_pin_deferred": n_pin_deferred,
        "n_precedence_edges": len(adj.precedence),
        "n_frozen": len(frozen),
        "n_batch_groups": len(groups),
        "n_group_waits": n_group_waits,
        "n_sweeps": n_sweeps,
        "notes": list(adj.notes),
    }
    return schedule, diagnostics


__all__ = [
    "RULES",
    "dispatch_baseline",
    "dispatch_adjusted",
    "dispatch_adjusted_verbose",
    "canonical_schedule",
    "canonical_schedule_json",
    "schedules_equal",
]
