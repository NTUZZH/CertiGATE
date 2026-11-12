"""Tier 2 certificate: an admissible lower bound on weighted tardiness.

This is a restatement, extended to be release-aware, of the closed-form
admissible bound the Y1 line uses as a shaping potential
(``src/fmwos/lb.py`` and ``notes/lemma_lb.md`` in that repository).  L1 uses it
for one purpose only: to certify how far a proposed schedule's objective can be
from the best achievable objective on the same instance.  No bound improvement
is claimed here.

What it bounds
--------------
For an instance I with work orders j (processing time ``p_j > 0``, release
``r_j``, due ``d_j``, weight ``w_j > 0``, trade ``g_j``) and technicians grouped
by trade, let

    OPT(I, t, tau) = min over feasible schedules of  sum_j w_j (C_j - d_j)^+

where a feasible schedule assigns every order to a technician of its own trade,
runs it without preemption for ``p_j``, starts it no earlier than
``max(r_j, tau_u)`` on technician ``u``, and never overlaps two orders on one
technician.  ``tau_u`` is the business-hour time at which technician ``u``
becomes available (``t``, the decision instant, for an idle technician).

:func:`lb2` returns a quantity ``LB(I, t, tau)`` with ``LB <= OPT``, so for any
schedule S of I with objective ``obj(S)``,

    (obj(S) - LB) / max(LB, floor)   >=   (obj(S) - OPT) / max(OPT, floor),

that is, the certified gap never understates the true optimality gap.  Accepting
a proposal because its certified gap is at or below tau therefore *proves* its
true gap is at or below tau; the cost of the bound's slack is false blocks, not
false accepts.

Where it is evaluated in the guard
----------------------------------
On the FULL adjusted instance at ``t = 0`` with every technician free, which is
the state the episode is dispatched from.  ``tau_by_trade`` is kept in the
signature so a mid-episode certification (a rolling snapshot, where some
technicians are still busy) needs no change to this module.

The bound also holds for the *constrained* problem the proposal induces
(pins, precedence edges, freezes and batch chains), because those operations
only add constraints: every schedule the adjusted dispatch can produce is a
feasible schedule of the relaxation above, so ``LB <= OPT(relaxation) <=
OPT(with the proposal's constraints) <= obj(realized schedule)``.

The lemma, extended (both components, with release-awareness marked)
--------------------------------------------------------------------
Trades are independent: eligibility is exact trade-match and technician pools
are disjoint, so ``OPT = sum_g OPT_g`` and it is enough to bound each trade.
Fix a trade g with k technicians, availabilities ``tau_1..tau_k`` (each already
clamped to ``max(t, tau_u)``), ``tau_min = min_u tau_u``, and job set ``Q_g``.

**Component (i), per-job earliest completion (release-aware).**

    LB_i = sum_{j in Q_g} w_j * max(0, max(tau_min, r_j) + p_j - d_j).

*Proof.* In any feasible schedule job j starts on some technician u, so it
starts no earlier than ``tau_u >= tau_min``; **and it starts no earlier than its
own release ``r_j`` (this is where release-awareness enters, and it is the only
change to the original step)**.  Hence ``start_j >= max(tau_min, r_j)`` and
``C_j = start_j + p_j >= max(tau_min, r_j) + p_j``.  Since ``x -> w_j (x-d_j)^+``
is non-decreasing, ``w_j (C_j - d_j)^+ >= w_j (max(tau_min, r_j) + p_j - d_j)^+``
term by term, and summing over ``Q_g`` gives ``OPT_g >= LB_i``.  ∎

**Component (ii), capacity overflow (release-aware in the work counted).**
For a threshold ``d`` let ``A_d = { j in Q_g : d_j <= d }``,

    D(d)   = sum_{j in A_d} p_j        <- ALL orders due by d, released or not
    cap(d) = sum_u max(0, d - tau_u)   <- unchanged: technician time before d
    O(d)   = max(0, D(d) - cap(d))
    rho_min(d) = min_{j in A_d} (w_j / p_j)

    LB_ii(d) = rho_min(d) * O(d)^2 / (2k)   is a lower bound on OPT_g.

*Proof, step by step.*
1. Total technician time available strictly before ``d`` is ``cap(d)``, whatever
   the schedule does with it.  So at most ``cap(d)`` hours of ``A_d``-work can
   be completed by ``d``, and at least ``O(d) = (D(d) - cap(d))^+`` hours of
   ``A_d``-work remain unprocessed at ``d``.  **This is where release-awareness
   enters component (ii): an order with ``r_j > d`` cannot be worked on before
   ``d`` at all, so counting it in ``D(d)`` is valid.  Formally, step 1 bounds
   completed work from above by machine time alone and never assumes a job was
   available; enlarging ``A_d`` to every order due by ``d`` therefore preserves
   the inequality, and it can only increase ``O(d)``.  A release-aware cap
   (which would also cap the work by ``sum_j min(p_j, (d - r_j)^+)``) would give
   a larger ``O(d)`` still; we do not use it, so the implemented bound is the
   conservative one.**
2. Let ``W(x)`` be the ``A_d``-work still unprocessed at time ``x >= d``.  Then
   ``W(d) >= O(d)`` and ``W`` decreases at rate at most ``k``, because at most
   ``k`` technicians of this trade run in parallel.  A profile of height at
   least ``O(d)`` with slope at least ``-k`` encloses at least the area of the
   triangle, so ``integral_d^inf W(x) dx >= O(d)^2 / (2k)``.
3. For one job j processed on one technician, ``integral_d^inf r_j(x) dx <=
   p_j (C_j - d)^+`` where ``r_j(x)`` is its remaining work; summing over
   ``A_d`` gives ``integral_d^inf W(x) dx <= sum_{j in A_d} p_j (C_j - d)^+``.
4. Combining 2 and 3: ``sum_{j in A_d} p_j (C_j - d)^+ >= O(d)^2 / (2k)``.
5. Convert the work-weighted area to the objective.  For ``j in A_d`` we have
   ``d_j <= d``, so ``w_j (C_j - d_j)^+ >= w_j (C_j - d)^+ = (w_j/p_j) p_j
   (C_j - d)^+ >= rho_min(d) p_j (C_j - d)^+``.  Summing and using 4,
   ``OPT_g >= rho_min(d) * O(d)^2 / (2k) = LB_ii(d)``.  ∎

Between consecutive due dates ``A_d`` is fixed, so ``D(d)`` and ``rho_min(d)``
are constant while ``cap(d)`` grows; ``O(d)`` and therefore ``LB_ii(d)`` are
non-increasing on each such interval.  Each interval begins at a due date and
``O(d) = 0`` below the earliest one, so ``max_d LB_ii(d)`` is attained at one
of the distinct due dates, which is what the implementation scans.

**Combining.** ``LB_i`` and every ``LB_ii(d)`` are lower bounds on ``OPT_g``, so
their maximum is one too, and summing the independent trades gives
``LB = sum_g max(LB_i, max_d LB_ii(d)) <= sum_g OPT_g = OPT``.  ∎

Note on the constant: ``rho_min = min w_j/p_j`` (cheapest weight per unit work)
is the factor produced by step 5.  The plain cheapest *weight* would bound the
fluid area rather than the objective and is not admissible; the Y1 module
documents that correction and this restatement keeps it.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from time import perf_counter

#: Identifier recorded in every Tier 2 certificate, so a logged certificate can
#: be tied to the exact bound implementation that produced it.
LB2_VARIANT = "lb2-release-aware-v1"

_EPS = 1e-12


def _as_instance(instance_or_adjusted) -> dict:
    """Accept a plain instance dict or anything carrying ``.instance``."""
    return getattr(instance_or_adjusted, "instance", instance_or_adjusted)


def _cap_fn(taus: list[float]):
    """Return ``cap(d) = sum_u max(0, d - tau_u)`` as an O(log k) callable."""
    taus = sorted(taus)
    prefix = [0.0]
    for x in taus:
        prefix.append(prefix[-1] + x)

    def cap(d: float) -> float:
        m = bisect_left(taus, d)
        if m == 0:
            return 0.0
        return m * d - prefix[m]

    return cap


def _lb_trade(jobs, taus, t: float) -> dict:
    """Bound one trade.  ``jobs`` is a list of ``(p, r, d, w)`` tuples."""
    k = len(taus)
    out = {
        "n_jobs": len(jobs),
        "k": k,
        "bound_i": 0.0,
        "bound_ii": 0.0,
        "bound": 0.0,
        "argmax_due_bh": None,
        "no_technician": False,
    }
    if not jobs:
        return out
    if k == 0:
        # The environment guarantees at least one technician per trade; an
        # instance without one is infeasible, and contributing 0 keeps the
        # bound admissible (0 is a lower bound on any non-negative objective).
        out["no_technician"] = True
        return out

    clamped = [tau if tau > t else t for tau in taus]
    tau_min = min(clamped)

    # ---- (i) per-job earliest completion, release-aware -------------------- #
    bound_i = 0.0
    for (p, r, d, w) in jobs:
        start = tau_min if tau_min > r else r
        ec = start + p
        if ec > d:
            bound_i += w * (ec - d)

    # ---- (ii) capacity overflow over the distinct due dates ---------------- #
    cap = _cap_fn(clamped)
    two_k = 2.0 * k
    ordered = sorted(jobs, key=lambda j: j[2])
    n = len(ordered)
    d_work = 0.0
    rho_min = math.inf
    bound_ii = 0.0
    argmax_due = None
    i = 0
    while i < n:
        d = ordered[i][2]
        while i < n and ordered[i][2] == d:
            p, _r, _d, w = ordered[i]
            d_work += p
            rho = w / p if p > _EPS else w / _EPS
            if rho < rho_min:
                rho_min = rho
            i += 1
        overflow = d_work - cap(d)
        if overflow > 0.0:
            term = rho_min * overflow * overflow / two_k
            if term > bound_ii:
                bound_ii = term
                argmax_due = d

    out["bound_i"] = bound_i
    out["bound_ii"] = bound_ii
    out["bound"] = bound_i if bound_i > bound_ii else bound_ii
    out["argmax_due_bh"] = argmax_due
    return out


def lb2_detail(
    instance_or_adjusted,
    tau_by_trade: dict | None = None,
    t: float = 0.0,
    order_ids=None,
) -> dict:
    """Bound with its per-trade breakdown and wall time.

    Parameters
    ----------
    instance_or_adjusted
        An instance dict, or an ``l1adapter.apply.Adjusted`` (its adjusted
        fields are used).
    tau_by_trade
        ``trade -> [availability_bh per technician]``.  Default: every
        technician of every trade is free at ``t``.  Kept in the signature so
        mid-episode certification needs no change here.
    t
        The decision instant, in business hours.  0.0 is the episode start.
    order_ids
        Optional subset of work orders to bound (a mid-episode queue).  Default:
        every order of the instance, released or not.
    """
    started = perf_counter()
    inst = _as_instance(instance_or_adjusted)

    keep = None if order_ids is None else set(order_ids)
    jobs_by_trade: dict[str, list] = {}
    for wo in inst["work_orders"]:
        if keep is not None and wo["id"] not in keep:
            continue
        jobs_by_trade.setdefault(wo["trade"], []).append(
            (
                float(wo["p_bh"]),
                float(wo["release_bh"]),
                float(wo["due_bh"]),
                float(wo["weight"]),
            )
        )

    taus: dict[str, list] = {}
    if tau_by_trade is None:
        for tech in inst["technicians"]:
            taus.setdefault(tech["trade"], []).append(float(t))
    else:
        for trade, vals in tau_by_trade.items():
            taus[trade] = [float(v) for v in vals]

    per_trade = {}
    total = 0.0
    for trade in sorted(jobs_by_trade):
        row = _lb_trade(jobs_by_trade[trade], taus.get(trade, []), float(t))
        per_trade[trade] = row
        total += row["bound"]

    return {
        "lb_bh": total,
        "variant": LB2_VARIANT,
        "t_bh": float(t),
        "n_orders": sum(r["n_jobs"] for r in per_trade.values()),
        "per_trade": per_trade,
        "wall_ms": (perf_counter() - started) * 1000.0,
    }


def lb2(
    instance_or_adjusted,
    tau_by_trade: dict | None = None,
    t: float = 0.0,
    order_ids=None,
) -> float:
    """The admissible lower bound, in weighted business hours."""
    return lb2_detail(instance_or_adjusted, tau_by_trade, t, order_ids)["lb_bh"]


__all__ = ["LB2_VARIANT", "lb2", "lb2_detail"]
