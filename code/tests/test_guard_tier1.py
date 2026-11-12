"""Tier 1: the solver-native certificate, and the read-only Y1 import."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from l1adapter import apply
from l1adapter._fmwos import Y1_SRC
from l1guard.tier1 import DEFAULT_WORKERS, TIER1_VARIANT, _cpsat, cap_threads, tier1_certificate
from micro import make_instance, order


def small():
    # Two 10 bh jobs due at 5 on one technician: the optimum is 15 weighted
    # business hours (the second job finishes at 20, the first at 10, so
    # 1*(10-5) + 1*(20-5) = 20 either way round; CP-SAT proves it).
    return make_instance(
        [
            order("A", "B20", 10.0, priority=4, due_bh=5.0),
            order("B", "B20", 10.0, priority=4, due_bh=5.0),
        ],
        [("T1", "B20")],
    )


def test_the_certificate_carries_the_bound_the_incumbent_and_the_status():
    rec = tier1_certificate(small(), budget_s=10.0, workers=4)
    assert rec["status"] == "OPTIMAL" and rec["proved_optimal"] is True
    assert rec["lb_bh"] == pytest.approx(rec["objective_bh"])
    assert rec["variant"] == TIER1_VARIANT
    assert rec["budget_s"] == 10.0 and rec["workers"] == 4
    assert rec["wall_ms"] > 0.0


def test_the_bound_is_always_a_float_even_when_nothing_was_proved():
    rec = tier1_certificate(small(), budget_s=0.001, workers=1)
    assert isinstance(rec["lb_bh"], float) and rec["lb_bh"] >= 0.0


def test_the_solver_sees_the_adjusted_fields():
    inst = make_instance([order("A", "B20", 12.0, priority=3)], [("T1", "B20")])
    assert tier1_certificate(inst, budget_s=5.0)["objective_bh"] == 0.0
    adj = apply.apply_proposal(
        inst, {"operations": [{"op": "set_priority", "order_id": "A", "priority_class": 1}]}
    )
    # class 1 moves the due date to 8: the job cannot finish before 12, so the
    # optimum is 8 * 4 = 32.
    assert tier1_certificate(adj, budget_s=5.0)["objective_bh"] == pytest.approx(32.0)


def test_the_thread_cap_is_set_in_process():
    cap_threads(4)
    assert os.environ["OMP_NUM_THREADS"] == "4"
    assert os.environ["MKL_NUM_THREADS"] == "4"
    tier1_certificate(small(), budget_s=1.0, workers=2)
    assert os.environ["OMP_NUM_THREADS"] == "2"
    cap_threads(DEFAULT_WORKERS)


def test_the_solver_module_is_imported_from_the_read_only_y1_tree():
    mod = _cpsat()
    assert Path(mod.__file__).resolve().is_relative_to(Path(Y1_SRC).resolve())


def test_importing_the_solver_leaves_the_bytecode_setting_as_it_found_it():
    before = sys.dont_write_bytecode
    _cpsat()
    assert sys.dont_write_bytecode == before


def test_a_solve_writes_nothing_into_the_y1_source_tree():
    def listing():
        root = Path(Y1_SRC)
        return sorted(
            (str(p.relative_to(root)), p.stat().st_size, p.stat().st_mtime_ns)
            for p in root.rglob("*")
            if p.is_file()
        )

    before = listing()
    tier1_certificate(small(), budget_s=1.0, workers=2)
    assert listing() == before
