"""l1adapter - environment adapter for the L1 guard-measurement benchmark.

Phase 1 plumbing: it reuses the Paper Y1 FM work-order dispatch environment
(``fmwos``, read-only) and applies the frozen v1.0.0 adjustment operations to an
instance before re-dispatching it.  Nothing here decides whether an adjustment
should be allowed; that is the Phase 2 guard's job.  This layer supplies the
deterministic mechanics the guard will sit on:

    instances  - find and load Y1 instance files
    ops        - parse a proposal against the frozen schema into typed ops
    apply      - apply the operations, producing an Adjusted bundle
    dispatch   - dispatch the baseline or the adjusted instance
    evaluate   - weighted tardiness, per-order table, referee validation
    state      - a compact instance-state slice for later prompt building

Typical use::

    from l1adapter import instances, ops, apply, dispatch, evaluate

    inst = instances.load_instance(instances.list_instances(9, "storm2")[0])
    base = dispatch.dispatch_baseline(inst, "atc", seed=0)
    proposal = {"operations": [{"op": "set_priority", "order_id": "W7",
                                "priority_class": 1}]}
    adj = apply.apply_proposal(inst, proposal, baseline_schedule=base)
    sched = dispatch.dispatch_adjusted(adj, "atc", seed=0)
    print(evaluate.wwt(adj, sched), evaluate.wwt(adj.original, sched))
"""

from __future__ import annotations

from . import apply, dispatch, errors, evaluate, instances, ops, state
from ._fmwos import ROUND_BH, SLA_BH, WEIGHT, Y1_ROOT
from .apply import Adjusted, BatchGroup, apply_operations, apply_proposal
from .dispatch import (
    canonical_schedule,
    canonical_schedule_json,
    dispatch_adjusted,
    dispatch_adjusted_verbose,
    dispatch_baseline,
    schedules_equal,
)
from .evaluate import tardiness_table, validate, wwt
from .instances import list_instances, load_instance
from .ops import parse_operations, to_proposal, validate_proposal, verify_schema
from .state import state_slice

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "apply",
    "dispatch",
    "errors",
    "evaluate",
    "instances",
    "ops",
    "state",
    "Y1_ROOT",
    "SLA_BH",
    "WEIGHT",
    "ROUND_BH",
    "Adjusted",
    "BatchGroup",
    "apply_operations",
    "apply_proposal",
    "dispatch_baseline",
    "dispatch_adjusted",
    "dispatch_adjusted_verbose",
    "canonical_schedule",
    "canonical_schedule_json",
    "schedules_equal",
    "wwt",
    "tardiness_table",
    "validate",
    "list_instances",
    "load_instance",
    "parse_operations",
    "to_proposal",
    "validate_proposal",
    "verify_schema",
    "state_slice",
]
