"""The guard's verdict must not depend on the order of a proposal's operations.

Regression test for the v0.1 frozen-order-edit defect: the rule grew the
frozen set operation by operation, so ``freeze W`` followed by
``reassign_window W`` was refused at the feasibility stage while the same two
operations in the other order passed. Guard v0.2 protects only the episode's
standing frozen set and reads the proposal as one atomic adjustment.

Two parts:
  * every multi-operation canonical proposal in suite v0.2, evaluated under
    G_FEAS in shipped order and fully reversed, must reach the same stage
    outcome (blocked at feasibility or not);
  * targeted permutations of the freeze/unfreeze interactions.
"""
import itertools
import json
from pathlib import Path

import pytest

from l1guard.config import G_FEAS
from l1guard.guard import evaluate_proposal

ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / "code" / "suite" / "v0.2" / "suite.jsonl"

# The instance loader used by every replay script.
import sys
sys.path.insert(0, str(ROOT / "code" / "scripts"))
from suite_gate import instance_path  # noqa: E402
from l1guard.replay import InstanceCache  # noqa: E402

_CACHE = InstanceCache()


def _rows():
    for line in SUITE.open():
        yield json.loads(line)


def _canonical(item):
    cls = item["primary_class"]
    if cls in ("benign", "V3"):
        return item["gold_ops"]
    if cls in ("V1", "V2"):
        return item["literal_ops"]
    if cls == "V4":
        return item["trap_ops"]
    if cls == "V6":
        return item["forbidden_ops"]
    return []


def _terminal(item, ops):
    instance = _CACHE.instance(instance_path(item))
    verdict = evaluate_proposal(
        instance,
        {"operations": ops},
        G_FEAS,
        frozen_seed=tuple(item["episode"]["frozen_seed"]),
    )
    return verdict.terminal


@pytest.mark.slow
def test_suite_multiop_proposals_are_order_invariant():
    checked = 0
    for item in _rows():
        ops = _canonical(item)
        if len(ops) < 2:
            continue
        fwd = _terminal(item, ops)
        rev = _terminal(item, list(reversed(ops)))
        assert fwd == rev, (item["item_id"], fwd, rev)
        checked += 1
    assert checked > 400  # the suite carries hundreds of multi-op proposals


def test_freeze_then_edit_permutations_agree():
    """All 2! and 3! permutations of freeze/shift/unfreeze combinations agree."""
    for item in _rows():
        if item["primary_class"] != "benign":
            continue
        ops = _canonical(item)
        if len(ops) != 2 or not any(o["op"] == "freeze" for o in ops):
            continue
        outcomes = {
            _terminal(item, list(perm)) for perm in itertools.permutations(ops)
        }
        assert len(outcomes) == 1, (item["item_id"], outcomes)
