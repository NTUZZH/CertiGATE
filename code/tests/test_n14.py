"""N14 (decision-time benchmark under other dispatching rules): the rule swap and its controls.

Run pinned, as the project's other N11 tests::

    OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 taskset -c 8-11 python -m pytest code/tests/test_n14.py -q
"""

from __future__ import annotations

import json
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
import n14_alt_dispatch as n14  # noqa: E402

SMALL = "c10_replay_400_0000"


def _small():
    import suite_gate as sg

    for ln in open(sg.SUITE_PATH, encoding="utf-8"):
        it = json.loads(ln)
        if it["instance"]["instance_id"] == SMALL:
            path = n11.instance_path(it)
            return it, n11.load_instance(path), path
    raise AssertionError("no item on " + SMALL)


def _toy():
    """One trade, one technician busy until 5 with a running order; two queued orders.

    Z1 arrives at 1.0 and B2 at 2.0, both priority 2, so first in first out serves Z1
    first while the identifier order serves B2 first.
    """
    wos = [{"id": "R0", "trade": "A", "p_bh": 5.0, "release_bh": 0.0, "due_bh": 30.0,
            "priority": 2, "weight": 4.0, "building": None, "is_pm": False},
           {"id": "Z1", "trade": "A", "p_bh": 1.0, "release_bh": 1.0, "due_bh": 25.0,
            "priority": 2, "weight": 4.0, "building": None, "is_pm": False},
           {"id": "B2", "trade": "A", "p_bh": 1.0, "release_bh": 2.0, "due_bh": 26.0,
            "priority": 2, "weight": 4.0, "building": None, "is_pm": False}]
    return {"meta": {"id": "toy", "window_bh": 80.0}, "trades": ["A"],
            "technicians": [{"id": "T0", "trade": "A"}], "work_orders": wos}


# --------------------------------------------------------------------------- #
# The rule swap                                                                #
# --------------------------------------------------------------------------- #
def test_pfifo_arrival_is_n6_pfifo_when_nothing_is_raised():
    from l1adapter import dispatch as dm

    n14.install()
    _it, inst, _p = _small()
    a = dm.dispatch_baseline(inst, "pfifo_arrival", 0)
    b = dm.dispatch_baseline(inst, "pfifo", 0)
    assert a["assignments"] == b["assignments"] and a["decisions"] == b["decisions"]


def test_pfifo_arrival_keeps_the_arrival_order_after_the_dispatch_origin_raise():
    from l1adapter import apply as apply_mod
    from l1adapter import dispatch as dm
    import n8_causal as n8

    n14.install()
    inst = _toy()
    base = {"assignments": [{"wo": "R0", "tech": "T0", "start_bh": 0.0, "end_bh": 5.0}]}

    def order(rule, record):
        adj = apply_mod.apply_operations(inst, [], frozen_seed=["R0"], baseline_schedule=base)
        if record:
            with n14.site_rule("pfifo"):
                n8.raise_releases(adj, 3.0)
                sched = dm.dispatch_adjusted(adj, rule, 0)
        else:
            n8.raise_releases(adj, 3.0)
            sched = dm.dispatch_adjusted(adj, rule, 0)
        return [a["wo"] for a in sorted(sched["assignments"], key=lambda a: a["start_bh"])]

    assert order("pfifo_arrival", True) == ["R0", "Z1", "B2"]
    # Without the recorded arrival the raise leaves only the identifiers to order the queue.
    assert order("pfifo", False) == ["R0", "B2", "Z1"]


def test_site_rule_sets_and_restores_the_guard_dispatcher():
    import l1guard.config as gc
    import n8_causal as n8

    n14.install()
    orig_raise = n8.raise_releases
    with n14.site_rule("wspt"):
        assert gc.G_CERT.rule == "wspt" and gc.G_CERT.seed == 0
        assert n8.raise_releases is orig_raise
    assert gc.G_CERT.rule == "atc"
    with pytest.raises(RuntimeError):
        with n14.site_rule("pfifo"):
            assert gc.G_CERT.rule == "pfifo_arrival"
            assert n8.raise_releases is not orig_raise
            raise RuntimeError("leave the block")
    assert gc.G_CERT.rule == "atc" and n8.raise_releases is orig_raise
    assert not n14._ARRIVAL


def test_gen_price_dispatches_with_the_site_rule_and_the_board_with_atc():
    from l1adapter import dispatch as dm

    n14.install()
    _it, inst, _p = _small()
    base = dm.dispatch_baseline(inst, "edd", 0)
    n14.AUDIT.clear()
    with n14.site_rule("edd"):
        r = n14.gp(inst, n14.EMPTY_RAW, [], base, 0.0, ref2=True)
    assert set(n14.AUDIT) == {"edd"} and r["term_cert"] is not None
    n14.AUDIT.clear()
    site = {"t_d": 0.0, "known_ids": [wo["id"] for wo in inst["work_orders"]], "running": []}
    n11.board_record(inst, SMALL, site, [])
    assert set(n14.AUDIT) == {"atc"}
    n14.AUDIT.clear()


def test_edd_site_objective_is_the_edd_dispatch():
    from l1adapter import dispatch as dm
    from l1adapter import evaluate as ev

    n14.install()
    _it, inst, _p = _small()
    base = dm.dispatch_baseline(inst, "edd", 0)
    with n14.site_rule("edd"):
        r = n14.gp(inst, n14.EMPTY_RAW, [], base, 0.0)
    assert r["obj"] == pytest.approx(ev.wwt(inst, base), abs=1e-9)


# --------------------------------------------------------------------------- #
# The oracle on the known board                                                #
# --------------------------------------------------------------------------- #
def test_trade_signature_is_the_trade_content():
    inst = _toy()
    avail = {"T0": 5.0}
    s0 = n14.trade_sig(inst, avail, "A", 3.0)
    assert s0 == n14.trade_sig(json.loads(json.dumps(inst)), dict(avail), "A", 3.0)
    assert s0 != n14.trade_sig(inst, {"T0": 5.5}, "A", 3.0)
    assert s0 != n14.trade_sig(inst, avail, "A", 3.5)
    other = json.loads(json.dumps(inst))
    other["work_orders"][1]["due_bh"] = 24.0
    assert s0 != n14.trade_sig(other, avail, "A", 3.0)


def test_assemble_uses_lb2_closure_then_n11_then_this_run():
    def tv(sig, lb2, up0, closed):
        return {"sig": sig, "lb2": lb2, "upper0": up0, "closed_by_lb2": closed}

    b = {"iid": "x", "t_d": 1.0, "fp": n11.BASE_FP, "n_orders": 3, "n_running": 1,
         "running_const": 2.0,
         "trades": {"A": tv("a", 1.0, 1.0, True), "B": tv("b", 3.0, 9.0, False),
                    "C": tv("c", 4.0, 8.0, False)}}
    sig_map = {"b": (3.5, 10.0, "OPTIMAL")}
    solves = {"c": {"lower": 5.0, "upper": 7.0, "status": "OPTIMAL"}}
    (rec,) = n14.assemble([b], sig_map, solves)
    assert rec["complete"] and rec["proved_all"]
    assert rec["lower"] == pytest.approx(1.0 + 3.5 + 5.0 + 2.0)
    assert rec["upper"] == pytest.approx(1.0 + 9.0 + 7.0 + 2.0)
    assert rec["sources"] == {"lb2": 1, "n11": 1, "n14": 1}
    (rec,) = n14.assemble([b], sig_map, {})
    assert not rec["complete"] and rec["lower"] is None


# --------------------------------------------------------------------------- #
# The control reproduces N11                                                   #
# --------------------------------------------------------------------------- #
def test_control_reproduces_n11_census_rows_on_a_small_instance():
    n14.install()
    check = n11.Checker()
    inp = n14.load_inputs(check)
    tasks = n14.build_tasks(inp, ("atc",), {SMALL})
    n14._TASKS[:] = tasks
    res = n14.census_task(0)
    assert not res["fails"]
    assert set(res["audit"]["site"]) == {"atc"} and set(res["audit"]["board"]) <= {"atc"}
    rows = res["items"]
    n14.enrich(rows, inp["pub"])
    assert rows
    for r in rows:
        m = inp["n11"][r["item_id"]]
        for k in n14.R7_FIELDS:
            assert n14.same(r[k], m[k]), (r["item_id"], k, r[k], m[k])
