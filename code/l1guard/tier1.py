"""Tier 1 certificate: the solver-native bound from CP-SAT.

The adjusted instance is handed to the Y1 exact model
(``fmwos.cpsat.solve``) at a per-proposal time budget; the certificate's lower
bound is the solver's ``best_bound_bh`` (CP-SAT's ``BestObjectiveBound``), and
the incumbent it found is recorded alongside.  Nothing in the Y1 repository is
modified: the model is imported through the same read-only device the adapter
uses.

Three facts about this tier that the certificate records rather than hides.

1. **It bounds the relaxation, and that is sound.**  The CP-SAT model carries
   the adjusted instance's *fields* (releases, dues, weights, processing times,
   trade eligibility).  It does not carry the proposal's dispatch constraints
   (pins, precedence edges, freezes, batch chains), which only ever add
   constraints.  A bound on the relaxation is therefore a valid bound on the
   constrained optimum as well, and the realized schedule is feasible for both,
   so the certified gap never understates the true gap.  ``tier1_relaxation``
   on the certificate names this.
2. **The bound lives on a centi-business-hour grid.**  The Y1 model scales
   business hours by 100, rounding processing times and releases up and due
   dates to nearest.  ``best_bound_bh`` is therefore a lower bound on the
   discretized model's optimum; it differs from the continuous optimum by at
   most the discretization, which the Y1 module documents.  Tier 2 has no such
   caveat, which is one reason both tiers are reported.
3. **A budget that proves nothing still returns 0.0**, which is a valid but
   vacuous bound (weighted tardiness is non-negative).  The pilot table reports
   how often that happens per cell and budget; the guard records the solver
   status so a vacuous certificate is never mistaken for a tight one.

Thread discipline (guidance Section 6.0): the solver gets a fixed, small worker
count and the numerical runtimes are capped to the same number in-process, so a
solver sharing the box with a vLLM server cannot silently oversubscribe the
cores it was given.  Setting the environment variables here, at import time and
before OR-Tools is imported, is what makes the cap take effect; pinning the
cores themselves (``taskset``) remains the caller's job.
"""

from __future__ import annotations

import os
import sys
from time import perf_counter

#: Workers for CP-SAT and the cap for the numerical runtimes' thread pools.
DEFAULT_WORKERS = 4

TIER1_VARIANT = "cpsat-best-bound"


def cap_threads(n: int = DEFAULT_WORKERS) -> None:
    """Cap the numerical runtimes' thread pools at ``n`` (in-process)."""
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[var] = str(int(n))


cap_threads(DEFAULT_WORKERS)  # before OR-Tools is imported anywhere below


_CPSAT = None


def _cpsat():
    """Import ``fmwos.cpsat`` without writing anything into the Y1 tree."""
    global _CPSAT
    if _CPSAT is None:
        from l1adapter._fmwos import Y1_SRC  # inserts the Y1 src on sys.path

        if str(Y1_SRC) not in sys.path:
            sys.path.insert(0, str(Y1_SRC))
        prev = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            from fmwos import cpsat as _mod
        finally:
            sys.dont_write_bytecode = prev
        _CPSAT = _mod
    return _CPSAT


def _as_instance(instance_or_adjusted) -> dict:
    return getattr(instance_or_adjusted, "instance", instance_or_adjusted)


def tier1_certificate(
    instance_or_adjusted,
    budget_s: float = 5.0,
    workers: int = DEFAULT_WORKERS,
    warm_start: dict | None = None,
) -> dict:
    """Solve the adjusted instance to the budget and return the bound record.

    Returns ``{lb_bh, objective_bh, status, wall_ms, budget_s, workers,
    variant, branches, proved_optimal}``.  ``lb_bh`` is always a float: CP-SAT
    returns 0.0 when it proved nothing, which is vacuous but valid.
    """
    cap_threads(workers)
    cpsat = _cpsat()
    inst = _as_instance(instance_or_adjusted)
    started = perf_counter()
    res = cpsat.solve(
        inst, time_limit_s=float(budget_s), workers=int(workers), warm_start=warm_start
    )
    wall_ms = (perf_counter() - started) * 1000.0
    lb = res.get("best_bound_bh")
    return {
        "lb_bh": 0.0 if lb is None else float(lb),
        "objective_bh": res.get("objective_bh"),
        "status": res.get("status"),
        "wall_ms": wall_ms,
        "solver_wall_s": res.get("wall_seconds"),
        "budget_s": float(budget_s),
        "workers": int(workers),
        "variant": TIER1_VARIANT,
        "branches": res.get("decisions"),
        "proved_optimal": res.get("status") == "OPTIMAL",
    }


__all__ = ["DEFAULT_WORKERS", "TIER1_VARIANT", "cap_threads", "tier1_certificate"]
