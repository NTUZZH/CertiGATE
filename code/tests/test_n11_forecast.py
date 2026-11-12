"""N11 Stage 3 (forecast reading): futures, seeds, the F2 estimator, the S = 0 and FI identities.

Run pinned::

    OMP_NUM_THREADS=1 taskset -c 8-9 python -m pytest code/tests/test_n11_forecast.py -q
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

import n11_decision_time as D  # noqa: E402
import n11_forecast as F  # noqa: E402

GEN, TA = F.import_y1()
CENSUS = {r["item_id"]: r for r in D.read_jsonl(D.OUT / "items.jsonl")}


def _suite():
    import suite_gate as sg
    return {r["item_id"]: r for r in sg.load_suite()}


SUITE = _suite()


def _task(iid, item_ids, readings, units_extra=None):
    """A worker task for ``item_ids`` of instance ``iid`` (direct benchmark units)."""
    units, seeds = [], {}
    path = None
    for item_id in item_ids:
        r = CENSUS[item_id]
        it = SUITE[item_id]
        path = D.instance_path(it)
        seed = list(it["episode"]["frozen_seed"] or [])
        fk = D.frozen_key(seed)
        seeds[fk] = seed
        ops = D.canonical_ops(it)
        units.append({"uid": item_id, "fk": fk, "t_d": float(r["t_d"]),
                      "raw": json.dumps({"operations": ops}), "forecast": r["dt_stage_cert"] == "qual",
                      "empty": not ops, "rw_obj": r["rw_obj"], "rw_obj_orig": r["rw_obj_orig"],
                      "rw0_obj": r["rw0_obj"], "rw0_obj_orig": r["rw0_obj_orig"]})
    return {"iid": iid, "path": path, "units": units, "seeds": seeds,
            "readings": list(readings.items()), "topup": False, "open_trades": False,
            "pool": None}


def _priced(iid, n, cond=lambda r: True):
    out = [k for k, r in sorted(CENSUS.items()) if r["instance_id"] == iid
           and r["set"] == "published" and r["issuable"] and r["dt_stage_cert"] == "qual"
           and cond(r)]
    return out[:n]


def test_seed_is_a_pure_function_of_the_board():
    a = F.future_seed("c09_storm2_w80_u100_0000", 6.2, "F1", 3)
    assert a == F.future_seed("c09_storm2_w80_u100_0000", 6.2, "F1", 3)
    assert a != F.future_seed("c09_storm2_w80_u100_0000", 6.2, "F1", 4)
    assert a != F.future_seed("c09_storm2_w80_u100_0000", 6.2, "F2", 3)
    assert 0 <= a < 2 ** 63


def test_storm_future_is_deterministic_and_well_formed():
    pack = F.load_pack("c09_storm2_w80")
    cm = F.cm_pack(pack)
    seed = F.future_seed("x", 10.0, "F1", 0)
    f1, m1 = F.storm_future(GEN, TA, cm, 5.98, 10.0, 80.0, seed, "0")
    f2, _m2 = F.storm_future(GEN, TA, cm, 5.98, 10.0, 80.0, seed, "0")
    assert F.sha_obj(f1) == F.sha_obj(f2) and f1
    for wo in f1:
        assert 10.0 <= wo["release_bh"] <= 80.0
        assert wo["due_bh"] == round(wo["release_bh"] + TA.SLA_BH[wo["priority"]], 4)
        assert wo["weight"] == TA.WEIGHT[wo["priority"]]
        assert wo["building"] is None and not wo["is_pm"] and wo["id"].startswith("F0.")


def test_corrective_pack_draws_the_expected_count():
    pack = F.load_pack("c10_storm2_w80")
    cm = F.cm_pack(pack)
    lam = F.lambda1(pack)
    assert abs(sum(t["arrival_rate_per_bh"] for t in cm["trades"].values()) - lam) < 1e-12
    m, W, n = 2.0, 20.0, 60
    tot = sum(len(F.storm_future(GEN, TA, cm, m, 0.0, W, 1000 + k, str(k))[0]) for k in range(n))
    e = lam * m * W * n
    assert abs(tot - e) <= 4.0 * math.sqrt(e)


def test_redraw_flag_yields_an_empty_future(monkeypatch):
    def fake(params, window_bh, seed, crew, mult):
        return {"meta": {"redrawn": True}, "work_orders": [{"id": "W0"}]}

    monkeypatch.setattr(GEN, "generate_window", fake)
    fut, meta = F.storm_future(GEN, TA, {}, 1.0, 0.0, 80.0, 1, "0")
    assert fut == [] and meta["redrawn"]


def test_m_hat_is_the_long_run_level_at_zero():
    pack = F.load_pack("c09_storm2_w80")
    lam = F.lambda1(pack)
    inst = {"work_orders": [{"is_pm": False, "release_bh": 0.5}, {"is_pm": True, "release_bh": 0.1}]}
    assert F.observed_multiplier(inst, 0.0, lam)["m_hat"] == 1.0
    got = F.observed_multiplier(inst, 1.0, lam)
    assert got["n_obs"] == 1
    assert abs(got["m_hat"] - (1 + lam) / (lam * 2.0)) < 1e-12


def test_recorded_pool_covers_the_horizon():
    import numpy as np

    pool = [{"id": "a", "W": 3.0, "cm": [(0.0, "D20", 3, 1.0), (2.5, "D20", 2, 0.5)]},
            {"id": "b", "W": 5.0, "cm": [(1.0, "B20", 1, 2.0)]}]
    rng = np.random.default_rng(3)
    fut, meta = F.replay_future_pool(pool, 2.0, 20.0, rng, "0", TA)
    W = sum({"a": 3.0, "b": 5.0}[w] for w in meta["windows"])
    assert W >= 20.0 and W - {"a": 3.0, "b": 5.0}[meta["windows"][-1]] < 20.0
    assert all(2.0 < wo["release_bh"] <= 20.0 for wo in fut)
    assert [wo["release_bh"] for wo in fut] == sorted(wo["release_bh"] for wo in fut)


def test_running_work_is_refused_at_feasibility():
    """V6-0090 at its late instant unfreezes three running seed orders (Stage 2's A12 case)."""
    import n8_causal as n8
    from l1adapter import dispatch as dispatch_mod

    late = {r["item_id"]: r for r in D.read_jsonl(D.OUT / "late" / "items.jsonl")}
    r = late["V6-0090"]
    it = SUITE["V6-0090"]
    inst = D.load_instance(D.instance_path(it))
    base = dispatch_mod.dispatch_baseline(inst, "atc", 0)
    seed = list(it["episode"]["frozen_seed"])
    traj = n8.trajectory(inst, seed, base)
    st = n8.site_state(inst, traj, r["t_d"], pm_known=True)
    K = n8.known_instance(inst, st)
    started = st["completed"] + st["in_progress"]
    raw = json.dumps({"operations": D.canonical_ops(it)})
    kf = D.kf_fix(st, seed)
    bp = n8.pin_schedule(base, traj, started)
    res = D.gen_price(K, raw, kf, bp, r["t_d"], running_ids=st["in_progress"])
    assert res["term_cert"] == "blocked_feas" and D.RUNNING_WORK_CODE in res["codes"]
    free = D.gen_price(K, raw, kf, bp, r["t_d"])
    assert free["term_cert"] != "blocked_feas"


def test_s0_reproduces_the_known_board_prices():
    iid = "c10_replay_400_0009"
    ids = _priced(iid, 4)
    F._TASKS[:] = [_task(iid, ids, {})]
    out = F.forecast_instance(0)
    krows = {r["item_id"]: r for r in F.k_rows([CENSUS[i] for i in ids])}
    for uid in ids:
        k, r = out["k"][uid], CENSUS[uid]
        for mine, theirs in F.K_FIELDS:
            assert k[mine] == r[theirs], (uid, mine)
        a = out["k_anchor"]["{}|{}".format(r["frozen_seed"], float(r["t_d"]))]
        pr = F.prices_of(k, a)
        for g in F.DESIGNS:
            assert pr[g] == krows[uid]["p_" + g], (uid, g)


@pytest.mark.parametrize("iid", ["c10_replay_400_0009", "c09_storm2_w80_u100_0014"])
def test_full_window_board_reproduces_the_realised_run(iid):
    ids = _priced(iid, 2, cond=lambda r: r["rw_obj"] is not None)
    F._TASKS[:] = [_task(iid, ids, {"FI": 1})]
    out = F.forecast_instance(0)
    assert not out["af"], out["af"][:3]
    assert out["af1"], "no AF1 row compared"
    for rec in out["af1"]:
        assert abs(rec["obj_fi"] - (rec["rw_obj"] - rec["c_done"])) <= 1e-6


def test_e2e_units_reproduce_stage2_and_share_prices_by_memo():
    """End-to-end units: K equals Stage 2's logged prices; memo members copy their representative."""
    from collections import OrderedDict

    iid = "c10_replay_400_0009"
    check = D.Checker()
    inp = F.load_forecast_inputs(check)
    tasks, refs, _keys = F.e2e_units(inp, check, {iid})
    tasks = F.prepare(tasks, inp, OrderedDict([("F2", 1), ("FI", 1)]), False, False)
    for t in tasks:
        t["memo"] = True
    F._TASKS[:] = tasks
    out = F.forecast_instance(0)
    assert not out["af"], out["af"][:3]
    F.assert_k_e2e(check, {iid: out}, refs)
    assert not check.failures, check.failures[:3]
    assert out["counts"].get("memo_members", 0) > 0
    got = {(p["uid"], p["reading"]) for p in out["prices"]}
    for u in tasks[0]["units"]:
        assert (u["uid"], "F2") in got and (u["uid"], "FI") in got
