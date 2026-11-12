"""N8: the decision-time certificate on hand-built instances.

Covers the site-state partition at the decision instant, the stale rule, the
shift of the dispatch origin to the decision instant, and the self-check that
the causal price equals the full-information price when every order is
released at t = 0.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import n8_causal as N  # noqa: E402
from l1adapter import dispatch as D  # noqa: E402
from l1guard import G_CERT, evaluate_proposal  # noqa: E402
from micro import make_instance, order  # noqa: E402


# --------------------------------------------------------------------------- #
# A 6-order toy instance with a hand-written trajectory                         #
# --------------------------------------------------------------------------- #
def toy():
    return make_instance(
        [
            order("W1", "B20", 2.0, release_bh=0.0, priority=2),
            order("W2", "B20", 5.0, release_bh=0.0, priority=3),
            order("W3", "B20", 2.0, release_bh=1.0, priority=2),
            order("W4", "B20", 1.0, release_bh=3.0, priority=1, due_bh=5.5),
            order("W5", "B20", 2.0, release_bh=4.0, priority=1, due_bh=6.0),
            order("W6", "B20", 1.0, release_bh=10.0, priority=3),
        ],
        [("T1", "B20"), ("T2", "B20")],
    )


def toy_trajectory():
    """At t_d = 4: W1 done, W2 and W3 running, W4 and W5 queued, W6 not yet released."""
    rows = [("W1", "T1", 0.0, 2.0), ("W3", "T1", 2.0, 4.5), ("W2", "T2", 0.0, 5.0),
            ("W4", "T1", 4.5, 5.5), ("W5", "T2", 5.0, 7.0), ("W6", "T1", 10.0, 11.0)]
    return {"assignments": [{"wo": w, "tech": t, "start_bh": s, "end_bh": e}
                            for w, t, s, e in rows]}


def test_state_partition_on_the_toy_instance():
    st = N.site_state(toy(), toy_trajectory(), 4.0)
    assert st["completed"] == ["W1"]
    assert st["in_progress"] == ["W2", "W3"]
    assert st["queue"] == ["W4", "W5"]
    assert st["unknown"] == ["W6"]


def test_state_partition_boundaries_are_exact():
    traj = toy_trajectory()
    # End exactly at t_d counts as completed; start exactly at t_d is queued.
    st = N.site_state(toy(), traj, 2.0)
    assert "W1" in st["completed"]
    assert "W3" in st["queue"]
    # A release exactly at t_d is known; one just after it is not.
    st = N.site_state(toy(), traj, 3.0)
    assert "W4" in st["queue"] and "W5" in st["unknown"]


def test_partition_covers_every_order_once():
    inst = toy()
    traj = toy_trajectory()
    for t in (0.0, 1.0, 2.0, 4.0, 4.5, 6.0, 10.0, 12.0):
        st = N.site_state(inst, traj, t)
        ids = sum(st.values(), [])
        assert sorted(ids) == sorted(w["id"] for w in inst["work_orders"])


def test_known_instance_and_frozen_set():
    inst = toy()
    st = N.site_state(inst, toy_trajectory(), 4.0)
    k = N.known_instance(inst, st)
    assert [w["id"] for w in k["work_orders"]] == ["W2", "W3", "W4", "W5"]
    assert k["technicians"] == inst["technicians"] and k["meta"] == inst["meta"]
    assert N.known_frozen(st, ["W1", "W5"]) == ["W2", "W3", "W5"]


def test_decision_instant_is_the_latest_named_release():
    inst = toy()
    ops = [{"op": "reorder", "order_id": "W5", "relation": "before", "ref_order_id": "W1"}]
    assert N.decision_instant(ops, inst) == 4.0
    assert N.decision_instant([{"op": "set_priority", "order_id": "W1",
                                "priority_class": 1}], inst) == 0.0
    # An identifier the instance does not hold contributes nothing.
    assert N.decision_instant([{"op": "pin_next", "order_id": "NOPE", "trade": "B20"}],
                              inst) == 0.0


def test_batch_members_set_the_decision_instant():
    inst = make_instance(
        [order("A", "B20", 1.0, release_bh=0.0, building="X"),
         order("B", "B20", 1.0, release_bh=6.0, building="X"),
         order("C", "B20", 1.0, release_bh=9.0, building="Y")],
        [("T1", "B20")])
    assert N.decision_instant([{"op": "batch", "building_id": "X", "trade": "B20"}],
                              inst) == 6.0


# --------------------------------------------------------------------------- #
# The stale rule                                                               #
# --------------------------------------------------------------------------- #
def _real_traj(inst):
    base = D.dispatch_baseline(inst, "atc", 0)
    return base, N.trajectory(inst, [], base)


def test_an_operation_on_a_completed_order_is_stale_and_refused_at_schema():
    inst = toy()
    base, traj = _real_traj(inst)
    # W6 is released at 10; by then W1 has long finished.
    ops = [{"op": "reorder", "order_id": "W1", "relation": "before", "ref_order_id": "W6"}]
    row = N.causal_item(inst, ops, [], base, traj)
    assert row["t_d"] == 10.0
    assert row["stale"] and row["stale_ids"] == ["W1"]
    assert row["terminal_c"] == "blocked_schema"
    assert "dangling_order_id" in row["codes_c"]
    assert row["g_c"] is None and row["wwt_real_with"] is None


def test_an_operation_on_known_orders_is_not_stale():
    inst = toy()
    base, traj = _real_traj(inst)
    ops = [{"op": "set_priority", "order_id": "W6", "priority_class": 1}]
    row = N.causal_item(inst, ops, [], base, traj)
    assert not row["stale"]
    assert row["stage_c"] == "qual" and row["g_c"] is not None


# --------------------------------------------------------------------------- #
# The dispatch origin moves to t_d                                             #
# --------------------------------------------------------------------------- #
def test_known_set_is_dispatched_from_the_decision_instant():
    inst = toy()
    base, traj = _real_traj(inst)
    t_d = 4.0
    st = N.site_state(inst, traj, t_d)
    k = N.known_instance(inst, st)
    kf = N.known_frozen(st, [])
    res = N.price(k, [], kf, base, t_d)
    assert res["stage"] == "qual"
    slots = {a["wo"]: a for a in base["assignments"]}
    for a in res["schedule"]["assignments"]:
        if a["wo"] in st["in_progress"]:
            # Running work stays where the trajectory put it.
            assert a["start_bh"] == slots[a["wo"]]["start_bh"]
            assert a["tech"] == slots[a["wo"]]["tech"]
        else:
            assert a["start_bh"] >= t_d
    # Due dates are untouched by the origin shift, so the objective is the
    # weighted tardiness of the same fields.
    due = {w["id"]: w["due_bh"] for w in k["work_orders"]}
    w = {x["id"]: x["weight"] for x in k["work_orders"]}
    obj = sum(w[a["wo"]] * max(0.0, a["end_bh"] - due[a["wo"]])
              for a in res["schedule"]["assignments"])
    assert res["obj_bh"] == pytest.approx(obj, abs=1e-12)


def test_raise_releases_is_the_identity_at_time_zero():
    from l1adapter.apply import apply_operations

    inst = toy()
    adj = apply_operations(inst, [])
    before = [dict(w) for w in adj.instance["work_orders"]]
    assert N.raise_releases(adj, 0.0) == 0
    assert adj.instance["work_orders"] == before


def test_running_orders_enter_the_bound_exactly_and_hold_their_technician():
    inst = make_instance(
        [order("R", "B20", 4.0, release_bh=0.0, priority=1, due_bh=1.0),
         order("Q", "B20", 1.0, release_bh=0.0, priority=1, due_bh=2.0)],
        [("T1", "B20")])
    frozen = {"R": {"tech": "T1", "start_bh": 0.0}}
    b = N.bound_known(inst, frozen, 2.0)
    # R ends at 4, 3 bh late at weight W[1]; Q cannot start before 4 on T1.
    wr = inst["work_orders"][0]["weight"]
    wq = inst["work_orders"][1]["weight"]
    assert b["lb_running_bh"] == pytest.approx(wr * 3.0)
    assert b["lb_bh"] == pytest.approx(wr * 3.0 + wq * (4.0 + 1.0 - 2.0))


# --------------------------------------------------------------------------- #
# Self-check: everything released at t = 0 means causal == full information     #
# --------------------------------------------------------------------------- #
def all_at_zero():
    return make_instance(
        [order("A", "B20", 3.0, priority=1, due_bh=2.0),
         order("B", "B20", 2.0, priority=2, due_bh=4.0),
         order("C", "B20", 4.0, priority=3, due_bh=5.0),
         order("D", "D30", 1.0, priority=1, due_bh=1.0),
         order("E", "D30", 5.0, priority=2, due_bh=3.0),
         order("F", "D30", 2.0, priority=4)],
        [("T1", "B20"), ("T2", "D30")])


SELF_CHECK_PROPOSALS = [
    [{"op": "reorder", "order_id": "C", "relation": "before", "ref_order_id": "A"}],
    [{"op": "set_priority", "order_id": "F", "priority_class": 1}],
    [{"op": "pin_next", "order_id": "E", "trade": "D30"},
     {"op": "reorder", "order_id": "B", "relation": "after", "ref_order_id": "C"}],
    [{"op": "reassign_window", "order_id": "D", "release_shift_bh": 3.0}],
]


@pytest.mark.parametrize("ops", SELF_CHECK_PROPOSALS)
def test_causal_price_equals_full_information_price_when_all_released_at_zero(ops):
    inst = all_at_zero()
    base, traj = _real_traj(inst)
    v = evaluate_proposal(inst, {"operations": ops}, G_CERT, baseline_schedule=base)
    row = N.causal_item(inst, ops, [], base, traj)
    assert row["t_d"] == 0.0
    assert row["n_known"] == len(inst["work_orders"]) and row["n_unknown"] == 0
    assert row["terminal_c"] == v.terminal
    assert v.certificate is not None
    assert row["obj_K"] == v.certificate.obj_bh
    assert row["lb_K"] == v.certificate.lb_bh
    assert row["g_c"] == v.certificate.gap
    # The realised run then sees no later arrival, so it is the same schedule.
    assert row["wwt_real_with"] == v.certificate.obj_bh


def test_omniscient_reading_reproduces_the_guard_with_late_releases():
    inst = toy()
    base, _ = _real_traj(inst)
    ops = [{"op": "set_priority", "order_id": "W6", "priority_class": 1}]
    v = evaluate_proposal(inst, {"operations": ops}, G_CERT, baseline_schedule=base)
    res = N.price(inst, ops, [], base, 0.0)
    assert res["terminal"] == v.terminal
    assert res["gap"] == v.certificate.gap and res["obj_bh"] == v.certificate.obj_bh


# --------------------------------------------------------------------------- #
# Sensitivity: planned maintenance on the calendar from t = 0                   #
# --------------------------------------------------------------------------- #
def test_planned_orders_do_not_delay_the_decision_and_stay_known():
    inst = toy()
    inst["work_orders"][5]["is_pm"] = True          # W6, released at 10
    ops = [{"op": "reorder", "order_id": "W6", "relation": "before", "ref_order_id": "W5"}]
    assert N.decision_instant(ops, inst) == 10.0
    assert N.decision_instant(ops, inst, pm_known=True) == 4.0
    st = N.site_state(inst, toy_trajectory(), 4.0, pm_known=True)
    assert st["scheduled"] == ["W6"] and st["unknown"] == []
    k = N.known_instance(inst, st)
    assert "W6" in [w["id"] for w in k["work_orders"]]
    base, traj = _real_traj(inst)
    row = N.causal_item(inst, ops, [], base, traj, pm_known=True)
    assert row["n_scheduled"] >= 1 and row["stage_c"] == "qual"
