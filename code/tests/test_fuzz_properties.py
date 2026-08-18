"""Property fuzz over real instances, as a bounded test.

The same generator and invariant checks as ``scripts/fuzz_ops.py`` (which is run
at a larger size for the build report): random schema-valid proposals are
applied and dispatched, and the result is checked against the referee and
against each constraint the proposal contains.  ``dense=True`` concentrates the
operations on 25 orders of one trade, so pins, precedences, freezes and batch
chains actually interact.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fuzz_ops  # noqa: E402

from l1adapter import apply_operations, dispatch, instances, ops  # noqa: E402
from l1adapter.errors import CyclicPrecedence, FrozenWindowConflict  # noqa: E402


@pytest.mark.parametrize("seed", [3, 17])
@pytest.mark.parametrize("dense", [False, True])
def test_random_proposals_keep_every_invariant(seed, dense):
    rng = random.Random(seed)
    paths = (
        instances.list_instances(9, "storm2")[:4]
        + instances.list_instances(10, "replay", 150)[:4]
        + instances.list_instances(5, "replay", 150)[:4]
    )
    checked = 0
    for path in paths:
        inst = instances.load_instance(path)
        rule = rng.choice(["atc", "edd"])
        baseline = dispatch.dispatch_baseline(inst, rule, 0)
        pool = fuzz_ops.dense_pool(inst, rng) if dense else None
        proposal = fuzz_ops.random_proposal(
            inst, rng, rng.randint(4, 12) if dense else rng.randint(1, 6), pool
        )
        try:
            adj = apply_operations(
                inst,
                ops.parse_operations(proposal, strict_schema=True),
                baseline_schedule=baseline,
            )
            schedule = dispatch.dispatch_adjusted(adj, rule, 0)
        except (CyclicPrecedence, FrozenWindowConflict):
            continue  # refusals are a legal outcome, tested elsewhere
        problems = fuzz_ops.check(adj, schedule, baseline)
        assert not problems, (path.name, proposal["operations"], problems)
        checked += 1
    assert checked >= 6
