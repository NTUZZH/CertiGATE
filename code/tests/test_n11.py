"""N11 (decision-time evaluation): issuability, the availability model, omniscient equivalence.

Run pinned, as the project's other solver tests::

    OMP_NUM_THREADS=1 taskset -c 8-9 python -m pytest code/tests/test_n11.py -q
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "code" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
os.environ.setdefault("L1_INSTANCE_ROOT",
                      ((os.environ.get("L1_Y1_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "PaperY-FMScheduling")) + "/data/processed/instances_v10"))

import n11_decision_time as n11  # noqa: E402
from l1oracle import cpsat_avail as ca  # noqa: E402
from l1oracle import cpsat_prec as cp  # noqa: E402


# --------------------------------------------------------------------------- #
# Issuability (design 1.2)                                                     #
# --------------------------------------------------------------------------- #
def _wo(oid, release, is_pm=False):
    return {"id": oid, "release_bh": release, "is_pm": is_pm}


def _iss(order_ids, orders, starts):
    by_id = {o["id"]: o for o in orders}
    return n11.issuability({"referenced": {"order_ids": order_ids}}, by_id, starts)


def test_empty_named_set_is_issuable_at_zero():
    r = _iss([], [_wo("A", 3.0)], {"A": 4.0})
    assert r["t_known"] == 0.0 and r["t_start"] is None
    assert r["issuable"] and r["issuable_strict"]


def test_ids_not_on_the_site_contribute_nothing():
    r = _iss(["ZZZ"], [_wo("A", 3.0)], {"A": 4.0})
    assert r["n_ref"] == 0 and r["t_known"] == 0.0 and r["issuable"]


def test_planned_order_is_known_from_zero():
    r = _iss(["P"], [_wo("P", 10.0, is_pm=True)], {"P": 12.0})
    assert r["t_known"] == 0.0 and r["t_start"] == 12.0 and r["issuable"]
    assert r["ref_all_pm"]


def test_closed_rule_admits_the_arrival_instant_strict_rule_does_not():
    r = _iss(["A"], [_wo("A", 5.0)], {"A": 5.0})
    assert r["t_known"] == 5.0 and r["t_start"] == 5.0
    assert r["issuable"] and not r["issuable_strict"]


def test_latest_release_and_earliest_start_decide():
    orders = [_wo("A", 2.0), _wo("B", 7.0)]
    # A starts at 6, before B is known at 7: the instruction cannot be issued.
    r = _iss(["A", "B"], orders, {"A": 6.0, "B": 9.0})
    assert r["t_known"] == 7.0 and r["t_start"] == 6.0 and not r["issuable"]
    r = _iss(["A", "B"], orders, {"A": 8.0, "B": 9.0})
    assert r["issuable"] and r["issuable_strict"]


# --------------------------------------------------------------------------- #
# cpsat_avail                                                                  #
# --------------------------------------------------------------------------- #
def _inst(techs, jobs):
    return {"meta": {"id": "toy"}, "trades": sorted({t[1] for t in techs}),
            "technicians": [{"id": tid, "trade": tr} for tid, tr in techs],
            "work_orders": [{"id": j, "trade": tr, "p_bh": p, "release_bh": r, "due_bh": d,
                             "weight": w} for j, tr, p, r, d, w in jobs]}


def test_availability_rounds_down_to_the_grid():
    techs = [{"id": "T0"}, {"id": "T1"}, {"id": "T2"}, {"id": "T3"}]
    got = ca.grid_availability(techs, {"T0": 1.239, "T1": 1.24, "T2": 0.0})
    assert got == [123, 124, 0, 0]
    assert ca.grid_availability(techs, None) == [0, 0, 0, 0]


def test_symmetry_groups_share_trade_and_grid_availability():
    techs = [{"id": "T%d" % i, "trade": "A"} for i in range(5)] + \
            [{"id": "U0", "trade": "B"}, {"id": "U1", "trade": "B"}]
    avail = [0, 0, 500, 500, 700, 0, 0]
    assert ca.symmetry_groups(techs, avail, frozenset()) == [[0, 1], [2, 3], [5, 6]]
    assert ca.symmetry_groups(techs, avail, frozenset({"B"})) == [[0, 1], [2, 3]]


def test_availability_binds_and_the_incumbent_is_retimed_at_a_u():
    inst = _inst([("T0", "A"), ("T1", "A")],
                 [("J1", "A", 3.0, 0.0, 3.0, 1), ("J2", "A", 3.0, 0.0, 3.0, 1)])
    free = ca.solve(inst, workers=1, time_limit_s=10)
    assert free["status"] == "OPTIMAL" and free["bound_bh"] == pytest.approx(0.0)
    busy = ca.solve(inst, workers=1, time_limit_s=10, tech_available={"T1": 5.0})
    assert busy["status"] == "OPTIMAL"
    assert busy["bound_bh"] == pytest.approx(3.0)
    assert busy["incumbent_obj_bh"] == pytest.approx(3.0)
    assert not ca.check_availability(busy["schedule"], {"T1": 5.0})
    assert busy["n_avail_intervals"] == 1


def test_off_grid_availability_keeps_a_valid_bound():
    inst = _inst([("T0", "A")], [("J1", "A", 1.0, 0.0, 1.0, 2)])
    res = ca.solve(inst, workers=1, time_limit_s=10, tech_available={"T0": 0.555})
    # Continuous optimum 2 * 0.555 = 1.11; the grid bound uses floor(0.555) = 0.55.
    assert res["bound_bh"] == pytest.approx(1.10)
    assert res["bound_bh"] <= 1.11 + 1e-9
    assert res["incumbent_obj_bh"] == pytest.approx(1.11)
    assert res["schedule"]["assignments"][0]["start_bh"] == pytest.approx(0.555)


def test_symmetry_break_within_groups_keeps_the_optimum():
    jobs = [("J%d" % k, "A", 2.0 + 0.5 * k, 0.25 * k, 2.0 + k, 1 + k % 3) for k in range(7)]
    inst = _inst([("T0", "A"), ("T1", "A"), ("T2", "A"), ("T3", "A")], jobs)
    av = {"T2": 1.5, "T3": 1.5}
    on = ca.solve(inst, workers=1, time_limit_s=30, tech_available=av, symmetry_break=True)
    off = ca.solve(inst, workers=1, time_limit_s=30, tech_available=av, symmetry_break=False)
    assert on["status"] == off["status"] == "OPTIMAL"
    assert on["bound_bh"] == pytest.approx(off["bound_bh"])
    assert on["n_symmetry_groups"] == 2 and on["n_symmetry_rows"] == 2


def test_retime_starts_each_technician_at_its_availability():
    inst = _inst([("T0", "A"), ("T1", "A")],
                 [("J1", "A", 1.0, 0.0, 9.0, 1), ("J2", "A", 1.0, 0.0, 9.0, 1)])
    grid = [{"wo": "J1", "tech": "T0", "g_start": 0}, {"wo": "J2", "tech": "T1", "g_start": 250}]
    out = ca.retime(inst, grid, cp.Constraints(), {"T1": 2.5})
    st = {a["wo"]: a["start_bh"] for a in out["assignments"]}
    assert st == {"J1": 0.0, "J2": 2.5}
    plain = cp.retime(inst, grid, cp.Constraints())
    assert {a["wo"]: a["start_bh"] for a in plain["assignments"]}["J2"] == 0.0


def test_frozen_start_before_availability_is_refused():
    inst = _inst([("T0", "A")], [("J1", "A", 1.0, 0.0, 9.0, 1)])
    cons = cp.Constraints(frozen=(("J1", "T0", 1.0),))
    with pytest.raises(ValueError):
        ca.solve(inst, cons, workers=1, time_limit_s=5, tech_available={"T0": 2.0})


def _capture_protos(monkeypatch):
    from ortools.sat.python import cp_model

    seen = []
    orig = cp_model.CpSolver.Solve

    def wrapped(self, model, *a, **k):
        seen.append(str(model.Proto()))
        return orig(self, model, *a, **k)

    monkeypatch.setattr(cp_model.CpSolver, "Solve", wrapped)
    return seen


def test_without_availability_the_model_is_cpsat_prec(monkeypatch):
    jobs = [("J%d" % k, "AB"[k % 2], 1.0 + 0.3 * k, 0.2 * k, 3.0 + k, 1 + k % 2)
            for k in range(8)]
    inst = _inst([("T0", "A"), ("T1", "A"), ("T2", "B"), ("T3", "B")], jobs)
    cons = cp.Constraints(precedence=(("J0", "J2"), ("J3", "J1")), pins=("J4",),
                          batches=(("J5", "J7"),))
    seen = _capture_protos(monkeypatch)
    a = ca.solve(inst, cons, workers=1, time_limit_s=10)
    b = cp.solve(inst, cons, workers=1, time_limit_s=10)
    assert len(seen) == 2 and seen[0] == seen[1]
    for k in ("status", "bound_bh", "grid_obj_bh", "incumbent_obj_bh", "n_symmetry_rows",
              "horizon_centi"):
        assert a[k] == b[k], k
    assert [(x["wo"], x["tech"], x["start_bh"]) for x in a["schedule"]["assignments"]] == \
        [(x["wo"], x["tech"], x["start_bh"]) for x in b["schedule"]["assignments"]]
    # Zero availability everywhere is no availability.
    c = ca.solve(inst, cons, workers=1, time_limit_s=10,
                 tech_available={"T0": 0.0, "T1": 0.0, "T2": 0.0, "T3": 0.0})
    assert seen[2] == seen[0] and c["bound_bh"] == a["bound_bh"]


# --------------------------------------------------------------------------- #
# Omniscient equivalence on one small instance                                 #
# --------------------------------------------------------------------------- #
SMALL = "c10_replay_400_0000"


def _small():
    import suite_gate as sg

    for ln in open(sg.SUITE_PATH, encoding="utf-8"):
        it = json.loads(ln)
        if it["instance"]["instance_id"] == SMALL:
            path = n11.instance_path(it)
            return it, n11.load_instance(path), path
    raise AssertionError("no item on " + SMALL)


def test_generalised_price_equals_the_guard_at_t_zero():
    from l1adapter import dispatch as dispatch_mod
    from l1guard import evaluate_proposal
    from l1guard.config import G_CERT, G_FEAS, UNGUARDED
    import suite_gate as sg

    items = [json.loads(ln) for ln in open(sg.SUITE_PATH, encoding="utf-8")]
    items = [it for it in items if it["instance"]["instance_id"] == SMALL][:25]
    _it, inst, _p = _small()
    base = dispatch_mod.dispatch_baseline(inst, "atc", 0)
    raws = ['{"operations": []}', "not json", '{"operations": [{"op": "pin_next"}]}']
    for it in items:
        raws.append(json.dumps({"operations": n11.canonical_ops(it)}))
    n_qual = 0
    for raw in raws:
        mine = n11.gen_price(inst, raw, [], base, 0.0, unguarded=True)
        for cfg, term in ((G_CERT, mine["term_cert"]), (G_FEAS, mine["term_feas"]),
                          (UNGUARDED, mine["term_ung"])):
            v = evaluate_proposal(inst, raw, cfg, baseline_schedule=base, frozen_seed=())
            assert v.terminal == term, (raw, cfg.name, v.terminal, term)
            if cfg is G_CERT and v.certificate is not None:
                n_qual += 1
                assert mine["gap"] == pytest.approx(v.certificate.gap, abs=1e-12)
                assert mine["obj"] == pytest.approx(v.certificate.obj_bh, abs=1e-12)
                assert mine["lb"] == pytest.approx(v.certificate.lb_bh, abs=1e-12)
    assert n_qual >= 5


def test_full_board_at_t_zero_is_the_relaxed_instance():
    from l1adapter import dispatch as dispatch_mod
    from l1guard.lb2 import lb2_detail

    _it, inst, _p = _small()
    site = {"t_d": 0.0, "known_ids": [wo["id"] for wo in inst["work_orders"]], "running": []}
    rec, _live = n11.board_record(inst, SMALL, site, [])
    atc = dispatch_mod.dispatch_baseline(inst, "atc", 0)
    per = n11.trade_wwt_of(inst, atc)
    lbd = lb2_detail(inst)["per_trade"]
    assert rec["running_const"] == 0.0 and rec["atc_feasible"]
    for tr, tv in rec["trades"].items():
        assert tv["trade_fp"] == n11.BASE_FP
        assert tv["lb2"] == lbd[tr]["bound"]
        assert tv["atc"] == per.get(tr, 0.0)


def test_board_at_a_later_instant_has_running_work_as_availability():
    from l1adapter import dispatch as dispatch_mod
    import n8_causal as n8

    _it, inst, _p = _small()
    base = dispatch_mod.dispatch_baseline(inst, "atc", 0)
    starts = sorted({a["start_bh"] for a in base["assignments"]})
    t_d = starts[len(starts) // 2]
    state = n8.site_state(inst, base, t_d, pm_known=True)
    site = n11.site_of(state, base, t_d)
    avail = n11.availability(inst, site)
    assert all(a >= t_d for a in avail.values())
    for oid, tech, s, e in site["running"]:
        assert s < t_d < e and avail[tech] >= e
    rec, live = n11.board_record(inst, SMALL, site, [])
    assert rec["atc_feasible"]
    assert all(wo["release_bh"] >= t_d for wo in live["binst"]["work_orders"])
    known = n8.known_instance(inst, state)
    kf = n8.known_frozen(state, [])
    bnd = n8.bound_known(known, {a["wo"]: a for a in base["assignments"] if a["wo"] in kf}, t_d)
    assert rec["running_const"] == pytest.approx(bnd["lb_running_bh"], abs=1e-9)
    lb2_sum = sum(tv["lb2"] for tv in rec["trades"].values())
    assert lb2_sum + rec["running_const"] == pytest.approx(bnd["lb_bh"], abs=1e-6)
    assert math.isfinite(lb2_sum)


# --------------------------------------------------------------------------- #
# Stage 2: frozen set, decision instants, memoised pricing, dangling ids       #
# --------------------------------------------------------------------------- #
def _state():
    return {"completed": ["c1"], "in_progress": ["r1", "r2"], "queue": ["q1", "q2"],
            "scheduled": ["p1"], "unknown": ["u1"]}


def test_kf_fix_freezes_every_seed_order_the_known_board_holds():
    kf = n11.kf_fix(_state(), ["q1", "p1", "u1", "c1", "r1"])
    assert kf == ["r1", "r2", "q1", "p1"]


def test_n8_frozen_set_leaves_the_scheduled_seed_order_free():
    kf8 = set(n11._kf_n8(_state(), ["q1", "p1"]))
    assert "p1" not in kf8 and {"r1", "r2", "q1"} <= kf8


def test_decision_instants_of_the_two_readings():
    iss = {"t_known": 2.0, "t_start": 5.5, "issuable": True}
    assert n11.decision_instant_of(iss, "primary") == 2.0
    assert n11.decision_instant_of(iss, "late") == 5.5
    late_ne = {"t_known": 9.0, "t_start": 5.5, "issuable": False}
    assert n11.decision_instant_of(late_ne, "late") == 9.0
    with pytest.raises(ValueError):
        n11.decision_instant_of(iss, "forecast")


def _board_at(fraction):
    from l1adapter import dispatch as dispatch_mod
    import n8_causal as n8

    _it, inst, _p = _small()
    base = dispatch_mod.dispatch_baseline(inst, "atc", 0)
    starts = sorted({a["start_bh"] for a in base["assignments"]})
    t_d = starts[int(len(starts) * fraction)]
    state = n8.site_state(inst, base, t_d, pm_known=True)
    known = n8.known_instance(inst, state)
    kf = n11.kf_fix(state, [])
    started = state["completed"] + state["in_progress"]
    pins = n8.pin_schedule(base, base, started)
    return inst, known, kf, pins, t_d, state


def test_pricing_depends_on_the_typed_operations_not_on_the_text():
    import n11_stage2 as s2

    _inst, known, kf, pins, t_d, state = _board_at(0.3)
    oid = state["queue"][0]
    ops = [{"op": "reassign_window", "order_id": oid, "release_shift_bh": 8.0}]
    a = n11.gen_price(known, json.dumps({"operations": ops}), kf, pins, t_d, ref2=True)
    b = n11.gen_price(known, json.dumps({"operations": ops}, indent=2), kf, pins, t_d, ref2=True)
    assert a["stage_cert"] != "schema", a["codes"]
    for k in s2.R_KEYS:
        assert a.get(k) == b.get(k), k


def test_an_order_unknown_at_t_d_is_a_dangling_identifier():
    _inst, known, kf, pins, t_d, state = _board_at(0.3)
    if not state["unknown"]:
        pytest.skip("no order arrives after this instant on the small instance")
    raw = json.dumps({"operations": [{"op": "reassign_window", "order_id": state["unknown"][0],
                                      "release_shift_bh": 8.0}]})
    res = n11.gen_price(known, raw, kf, pins, t_d)
    assert res["term_cert"] == "blocked_schema"
    assert "dangling_order_id" in (res["codes"] or [])
