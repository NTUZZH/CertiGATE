"""Regression: precedence edges out of a frozen order (fixed 2026-08-11).

Defect (found during the Phase 3 suite build): ``freeze(x)`` combined with
``reorder(x, "before", y)`` exhausted the event loop and raised
``DispatchDeadlock`` whenever ``y`` sat in a trade that had no event at the
instant ``x``'s pinned slot began.  The combination is satisfiable: ``x`` holds
its baseline slot and ``y`` only has to start no earlier than ``s_x``.  The loop
now marks the successors' trades as touched when a frozen order starts, so they
are re-examined at that instant.

The genuinely impossible sibling case, two frozen orders whose pinned starts
contradict the edge, is refused at apply time with ``FrozenPrecedenceConflict``.

Orchestrator ruling: decisions.md, 2026-08-11.
"""

from __future__ import annotations

import pytest

from l1adapter import apply_operations, dispatch, instances, ops
from l1adapter.errors import FrozenPrecedenceConflict
from micro import assert_feasible, by_wo, make_instance, order

REPRODUCER = "c10_replay_400_0000"
REPRO_FROZEN = "37454197"      # trade D20, baseline T16 @ 805.8194
REPRO_SUCCESSOR = "37448872"   # trade C10, released 734.8039 -- another trade


def op(**kw):
    return ops.parse_operations({"operations": [kw]})[0]


def cross_trade_instance():
    """X (D20) is frozen at bh 5; Y (C10) is queued from bh 0 in another trade."""
    inst = make_instance(
        [
            order("X", "D20", 1.0, release_bh=0.0, due_bh=20.0),
            order("Y", "C10", 1.0, release_bh=0.0, due_bh=2.0),
        ],
        [("T0", "D20"), ("T1", "C10")],
    )
    baseline = {
        "assignments": [
            {"wo": "X", "tech": "T0", "start_bh": 5.0, "end_bh": 6.0},
            {"wo": "Y", "tech": "T1", "start_bh": 0.0, "end_bh": 1.0},
        ]
    }
    return inst, baseline


# --------------------------------------------------------------------------- #
# the reported reproducer                                                      #
# --------------------------------------------------------------------------- #
def test_the_reported_reproducer_dispatches_cleanly():
    path = next(
        p for p in instances.list_instances(10, "replay", 400) if p.stem == REPRODUCER
    )
    inst = instances.load_instance(path)
    baseline = dispatch.dispatch_baseline(inst, "atc", 0)
    slot = by_wo(baseline)[REPRO_FROZEN]

    proposal = {
        "operations": [
            {"op": "freeze", "order_id": REPRO_FROZEN},
            {"op": "reorder", "order_id": REPRO_FROZEN, "relation": "before",
             "ref_order_id": REPRO_SUCCESSOR},
        ]
    }
    adj = apply_operations(
        inst, ops.parse_operations(proposal, strict_schema=True), baseline_schedule=baseline
    )
    schedule = dispatch.dispatch_adjusted(adj, "atc", 0)

    assert len(schedule["assignments"]) == len(inst["work_orders"])
    assert_feasible(adj, schedule)

    rows = by_wo(schedule)
    got = rows[REPRO_FROZEN]
    assert (got["tech"], got["start_bh"]) == (slot["tech"], slot["start_bh"])
    assert rows[REPRO_SUCCESSOR]["start_bh"] >= got["start_bh"]

    again = dispatch.dispatch_adjusted(adj, "atc", 0)
    assert dispatch.canonical_schedule_json(schedule) == dispatch.canonical_schedule_json(again)


# --------------------------------------------------------------------------- #
# frozen -> unfrozen                                                           #
# --------------------------------------------------------------------------- #
def test_an_edge_out_of_a_frozen_order_unblocks_a_successor_in_another_trade():
    """The deadlock geometry: the successor's trade sees no event at s_x."""
    inst, baseline = cross_trade_instance()
    adj = apply_operations(
        inst,
        [
            op(op="freeze", order_id="X"),
            op(op="reorder", order_id="X", relation="before", ref_order_id="Y"),
        ],
        baseline_schedule=baseline,
    )
    schedule = dispatch.dispatch_adjusted(adj, "edd", 0)
    rows = by_wo(schedule)
    assert (rows["X"]["tech"], rows["X"]["start_bh"]) == ("T0", 5.0)
    # Y is eligible from the pinned start, and start_x <= start_y allows the
    # same instant, so it starts exactly then (it would have run at bh 0).
    assert rows["Y"]["start_bh"] == pytest.approx(5.0)
    assert_feasible(adj, schedule)


def test_an_edge_out_of_a_frozen_order_works_within_one_trade_too():
    inst = make_instance(
        [
            order("X", "D20", 1.0, release_bh=0.0, due_bh=20.0),
            order("Y", "D20", 1.0, release_bh=0.0, due_bh=2.0),
        ],
        [("T0", "D20"), ("T1", "D20")],
    )
    baseline = {
        "assignments": [
            {"wo": "X", "tech": "T0", "start_bh": 5.0, "end_bh": 6.0},
            {"wo": "Y", "tech": "T1", "start_bh": 0.0, "end_bh": 1.0},
        ]
    }
    adj = apply_operations(
        inst,
        [
            op(op="freeze", order_id="X"),
            op(op="reorder", order_id="X", relation="before", ref_order_id="Y"),
        ],
        baseline_schedule=baseline,
    )
    schedule = dispatch.dispatch_adjusted(adj, "edd", 0)
    rows = by_wo(schedule)
    assert (rows["X"]["tech"], rows["X"]["start_bh"]) == ("T0", 5.0)
    assert rows["Y"]["start_bh"] == pytest.approx(5.0)
    assert_feasible(adj, schedule)


def test_a_chain_out_of_a_frozen_order_dispatches_in_order():
    inst = make_instance(
        [
            order("X", "D20", 1.0, release_bh=0.0, due_bh=20.0),
            order("Y", "C10", 1.0, release_bh=0.0, due_bh=2.0),
            order("Z", "E10", 1.0, release_bh=0.0, due_bh=1.0),
        ],
        [("T0", "D20"), ("T1", "C10"), ("T2", "E10")],
    )
    baseline = {
        "assignments": [
            {"wo": "X", "tech": "T0", "start_bh": 5.0, "end_bh": 6.0},
            {"wo": "Y", "tech": "T1", "start_bh": 0.0, "end_bh": 1.0},
            {"wo": "Z", "tech": "T2", "start_bh": 0.0, "end_bh": 1.0},
        ]
    }
    adj = apply_operations(
        inst,
        [
            op(op="freeze", order_id="X"),
            op(op="reorder", order_id="X", relation="before", ref_order_id="Y"),
            op(op="reorder", order_id="Y", relation="before", ref_order_id="Z"),
        ],
        baseline_schedule=baseline,
    )
    schedule = dispatch.dispatch_adjusted(adj, "edd", 0)
    rows = by_wo(schedule)
    assert rows["X"]["start_bh"] <= rows["Y"]["start_bh"] <= rows["Z"]["start_bh"]
    assert rows["X"]["start_bh"] == pytest.approx(5.0)
    assert_feasible(adj, schedule)


def test_an_edge_into_a_frozen_order_is_unchanged():
    """Freeze still wins over an incoming edge, and still says so in the notes."""
    inst, baseline = cross_trade_instance()
    adj = apply_operations(
        inst,
        [
            op(op="freeze", order_id="X"),
            op(op="reorder", order_id="Y", relation="before", ref_order_id="X"),
        ],
        baseline_schedule=baseline,
    )
    assert "precedence_into_frozen_order:Y->X" in adj.notes
    schedule = dispatch.dispatch_adjusted(adj, "edd", 0)
    rows = by_wo(schedule)
    assert (rows["X"]["tech"], rows["X"]["start_bh"]) == ("T0", 5.0)
    assert rows["Y"]["start_bh"] == pytest.approx(0.0)
    assert_feasible(adj, schedule)


# --------------------------------------------------------------------------- #
# frozen -> frozen                                                             #
# --------------------------------------------------------------------------- #
def two_frozen(start_x: float, start_y: float):
    inst = make_instance(
        [
            order("X", "D20", 1.0, release_bh=0.0, due_bh=20.0),
            order("Y", "C10", 1.0, release_bh=0.0, due_bh=20.0),
        ],
        [("T0", "D20"), ("T1", "C10")],
    )
    baseline = {
        "assignments": [
            {"wo": "X", "tech": "T0", "start_bh": start_x, "end_bh": start_x + 1.0},
            {"wo": "Y", "tech": "T1", "start_bh": start_y, "end_bh": start_y + 1.0},
        ]
    }
    return inst, baseline


def test_two_frozen_orders_with_consistent_starts_dispatch():
    inst, baseline = two_frozen(2.0, 4.0)
    adj = apply_operations(
        inst,
        [
            op(op="freeze", order_id="X"),
            op(op="freeze", order_id="Y"),
            op(op="reorder", order_id="X", relation="before", ref_order_id="Y"),
        ],
        baseline_schedule=baseline,
    )
    schedule = dispatch.dispatch_adjusted(adj, "edd", 0)
    rows = by_wo(schedule)
    assert (rows["X"]["tech"], rows["X"]["start_bh"]) == ("T0", 2.0)
    assert (rows["Y"]["tech"], rows["Y"]["start_bh"]) == ("T1", 4.0)
    assert rows["X"]["start_bh"] <= rows["Y"]["start_bh"]
    assert_feasible(adj, schedule)


def test_two_frozen_orders_with_equal_starts_are_consistent():
    inst, baseline = two_frozen(3.0, 3.0)
    adj = apply_operations(
        inst,
        [
            op(op="freeze", order_id="X"),
            op(op="freeze", order_id="Y"),
            op(op="reorder", order_id="X", relation="before", ref_order_id="Y"),
        ],
        baseline_schedule=baseline,
    )
    assert_feasible(adj, dispatch.dispatch_adjusted(adj, "edd", 0))


@pytest.mark.parametrize(
    "blocks",
    [
        # freeze, freeze, reorder-before
        [
            {"op": "freeze", "order_id": "X"},
            {"op": "freeze", "order_id": "Y"},
            {"op": "reorder", "order_id": "X", "relation": "before", "ref_order_id": "Y"},
        ],
        # the same edge spelled with "after"
        [
            {"op": "freeze", "order_id": "X"},
            {"op": "freeze", "order_id": "Y"},
            {"op": "reorder", "order_id": "Y", "relation": "after", "ref_order_id": "X"},
        ],
        # the reorder first, the freezes after: the check is order-independent
        [
            {"op": "reorder", "order_id": "X", "relation": "before", "ref_order_id": "Y"},
            {"op": "freeze", "order_id": "Y"},
            {"op": "freeze", "order_id": "X"},
        ],
    ],
)
def test_two_frozen_orders_with_inconsistent_starts_are_impossible(blocks):
    inst, baseline = two_frozen(6.0, 2.0)
    with pytest.raises(FrozenPrecedenceConflict) as exc:
        apply_operations(
            inst, ops.parse_operations({"operations": blocks}), baseline_schedule=baseline
        )
    assert exc.value.order_id == "X" and exc.value.ref_order_id == "Y"
    assert exc.value.start_bh == 6.0 and exc.value.ref_start_bh == 2.0


def test_the_conflict_also_fires_on_a_seeded_frozen_pair():
    inst, baseline = two_frozen(6.0, 2.0)
    with pytest.raises(FrozenPrecedenceConflict):
        apply_operations(
            inst,
            [op(op="reorder", order_id="X", relation="before", ref_order_id="Y")],
            frozen_seed=["X", "Y"],
            baseline_schedule=baseline,
        )


# --------------------------------------------------------------------------- #
# frozen -> unfrozen -> frozen: the transitive conflict                        #
# --------------------------------------------------------------------------- #
def chain_instance(start_x: float, start_y: float, n_middle: int = 1):
    """X (frozen) -> U [-> V] -> Y (frozen), each order in its own trade."""
    middles = ["U", "V"][:n_middle]
    trades = ["C10", "E10"][:n_middle]
    orders = [
        order("X", "D20", 1.0, release_bh=0.0, due_bh=40.0),
        order("Y", "D30", 1.0, release_bh=0.0, due_bh=40.0),
    ]
    techs = [("T0", "D20"), ("T1", "D30")]
    for i, (m, tr) in enumerate(zip(middles, trades)):
        orders.append(order(m, tr, 1.0, release_bh=0.0, due_bh=2.0 + i))
        techs.append(("T{}".format(i + 2), tr))
    baseline = {
        "assignments": [
            {"wo": "X", "tech": "T0", "start_bh": start_x, "end_bh": start_x + 1.0},
            {"wo": "Y", "tech": "T1", "start_bh": start_y, "end_bh": start_y + 1.0},
        ]
        + [
            {"wo": m, "tech": "T{}".format(i + 2), "start_bh": 0.0, "end_bh": 1.0}
            for i, m in enumerate(middles)
        ]
    }
    chain = ["X"] + middles + ["Y"]
    edges = [
        op(op="reorder", order_id=a, relation="before", ref_order_id=b)
        for a, b in zip(chain, chain[1:])
    ]
    return make_instance(orders, techs), baseline, edges, chain


def test_a_three_node_path_through_an_unfrozen_order_is_refused():
    inst, baseline, edges, _ = chain_instance(6.0, 2.0)
    with pytest.raises(FrozenPrecedenceConflict) as exc:
        apply_operations(
            inst,
            [op(op="freeze", order_id="X"), op(op="freeze", order_id="Y")] + edges,
            baseline_schedule=baseline,
        )
    assert (exc.value.order_id, exc.value.ref_order_id) == ("X", "Y")
    assert (exc.value.start_bh, exc.value.ref_start_bh) == (6.0, 2.0)
    assert exc.value.path == ("X", "U", "Y")
    assert "X -> U -> Y" in str(exc.value)


def test_the_transitive_check_is_order_independent():
    inst, baseline, edges, _ = chain_instance(6.0, 2.0)
    blocks = edges + [op(op="freeze", order_id="Y"), op(op="freeze", order_id="X")]
    with pytest.raises(FrozenPrecedenceConflict):
        apply_operations(inst, blocks, baseline_schedule=baseline)
    # and through the standing frozen set instead of freeze operations
    with pytest.raises(FrozenPrecedenceConflict):
        apply_operations(
            inst, edges, frozen_seed=["X", "Y"], baseline_schedule=baseline
        )


def test_the_same_path_with_consistent_starts_dispatches():
    inst, baseline, edges, _ = chain_instance(2.0, 6.0)
    adj = apply_operations(
        inst,
        [op(op="freeze", order_id="X"), op(op="freeze", order_id="Y")] + edges,
        baseline_schedule=baseline,
    )
    schedule = dispatch.dispatch_adjusted(adj, "edd", 0)
    rows = by_wo(schedule)
    assert (rows["X"]["tech"], rows["X"]["start_bh"]) == ("T0", 2.0)
    assert (rows["Y"]["tech"], rows["Y"]["start_bh"]) == ("T1", 6.0)
    assert rows["X"]["start_bh"] <= rows["U"]["start_bh"] <= rows["Y"]["start_bh"]
    assert_feasible(adj, schedule)


def test_a_four_node_mixed_chain_both_ways():
    # contradiction: X frozen at 8, Y frozen at 3, two unfrozen orders between
    inst, baseline, edges, _ = chain_instance(8.0, 3.0, n_middle=2)
    with pytest.raises(FrozenPrecedenceConflict) as exc:
        apply_operations(
            inst,
            [op(op="freeze", order_id="X"), op(op="freeze", order_id="Y")] + edges,
            baseline_schedule=baseline,
        )
    assert exc.value.path == ("X", "U", "V", "Y")

    # consistent: the whole chain fits between the two pinned starts
    inst, baseline, edges, chain = chain_instance(1.0, 9.0, n_middle=2)
    adj = apply_operations(
        inst,
        [op(op="freeze", order_id="X"), op(op="freeze", order_id="Y")] + edges,
        baseline_schedule=baseline,
    )
    schedule = dispatch.dispatch_adjusted(adj, "edd", 0)
    rows = by_wo(schedule)
    starts = [rows[o]["start_bh"] for o in chain]
    assert starts == sorted(starts), starts
    assert starts[0] == pytest.approx(1.0) and starts[-1] == pytest.approx(9.0)
    assert_feasible(adj, schedule)


def test_two_frozen_orders_with_no_path_between_them_are_untouched():
    """The check refuses contradictions on paths, not every out-of-order pair."""
    inst, baseline, edges, _ = chain_instance(6.0, 2.0)
    # keep the freezes, drop the edges that connect X to Y
    adj = apply_operations(
        inst,
        [
            op(op="freeze", order_id="X"),
            op(op="freeze", order_id="Y"),
            op(op="reorder", order_id="U", relation="before", ref_order_id="Y"),
        ],
        baseline_schedule=baseline,
    )
    assert adj.frozen["X"]["start_bh"] == 6.0 and adj.frozen["Y"]["start_bh"] == 2.0
    assert_feasible(adj, dispatch.dispatch_adjusted(adj, "edd", 0))


def test_a_cycle_among_unfrozen_orders_does_not_hang_the_path_search():
    inst, baseline, _, _ = chain_instance(2.0, 6.0)
    adj = apply_operations(
        inst,
        [
            op(op="freeze", order_id="X"),
            op(op="freeze", order_id="Y"),
            op(op="reorder", order_id="X", relation="before", ref_order_id="U"),
            op(op="reorder", order_id="U", relation="before", ref_order_id="Y"),
            op(op="reorder", order_id="Y", relation="before", ref_order_id="U"),
        ],
        baseline_schedule=baseline,
    )
    assert adj.find_cycles() == [["U", "Y"]]   # left to the dispatcher's refusal
