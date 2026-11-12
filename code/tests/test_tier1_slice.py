"""The Tier 1 slice's two load-bearing pieces: the sampler and the gate.

The sampler decides which rows the tier comparison is computed on, so a draw
that moved between runs would make the exhibit unreproducible; it is tested for
determinism, for independence from the order the caller happened to build the
pool in, and for the even spread across cells the design freeze asks for.

The reproduction gate is what makes the comparison a comparison: each sampled
row is re-evaluated under the accepted Tier 2 configuration, and its Tier 1
numbers are used only if the replay reproduces the accepted terminal and gap.
A checker that never fires is worse than no checker, so it is run against a row
doctored by one number and must report exactly that number.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

CODE_DIR = Path(__file__).resolve().parent.parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        name, CODE_DIR / "scripts" / "{}.py".format(name)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def ts():
    return _load("tier1_slice")


def _row(eval_dir, item_id, cls="benign", stratum="c10_replay_400", repeat=0):
    return {
        "eval_dir": eval_dir,
        "arm": eval_dir.replace("e1_eval_", ""),
        "item_id": item_id,
        "mode": "M_constrained",
        "thinking": None,
        "repeat": repeat,
        "primary_class": cls,
        "stratum": stratum,
    }


def _pool(ts, arms=("e1_eval_a", "e1_eval_b"), per_cell=40):
    pool = {}
    for arm in arms:
        for cls in ("benign", "V4"):
            for stratum in ("c09_storm2_w80", "c10_replay_400", "c10_storm2_w80"):
                pool[(arm, cls, stratum)] = [
                    _row(arm, "{}-{}-{}-{:04d}".format(cls, stratum, arm, i), cls, stratum)
                    for i in range(per_cell)
                ]
    return pool


# --------------------------------------------------------------------------- #
# The sampler                                                                 #
# --------------------------------------------------------------------------- #
def test_the_draw_is_identical_across_calls(ts):
    pool = _pool(ts)
    first = ts.draw_even(pool, 100, seed=0)
    second = ts.draw_even(pool, 100, seed=0)
    assert [ts.row_key(r) for r in first] == [ts.row_key(r) for r in second]
    assert len(first) == 100


def test_the_draw_does_not_depend_on_the_order_the_pool_was_built_in(ts):
    pool = _pool(ts)
    shuffled = {k: list(reversed(v)) for k, v in reversed(list(pool.items()))}
    assert [ts.row_key(r) for r in ts.draw_even(pool, 100, seed=0)] == [
        ts.row_key(r) for r in ts.draw_even(shuffled, 100, seed=0)
    ]


def test_a_different_seed_draws_a_different_sample(ts):
    pool = _pool(ts)
    a = {ts.row_key(r) for r in ts.draw_even(pool, 100, seed=0)}
    b = {ts.row_key(r) for r in ts.draw_even(pool, 100, seed=1)}
    assert a != b


def test_the_draw_is_even_across_cells_and_never_repeats_a_row(ts):
    pool = _pool(ts)  # 12 cells x 40 candidates
    drawn = ts.draw_even(pool, 96, seed=0)
    keys = [ts.row_key(r) for r in drawn]
    assert len(keys) == len(set(keys)) == 96
    per_cell = {}
    for r in drawn:
        per_cell[(r["eval_dir"], r["primary_class"], r["stratum"])] = (
            per_cell.get((r["eval_dir"], r["primary_class"], r["stratum"]), 0) + 1
        )
    assert set(per_cell.values()) == {8}


def test_a_small_cell_gives_up_its_share_to_the_cells_that_have_room(ts):
    pool = _pool(ts, arms=("e1_eval_a",), per_cell=40)
    pool[("e1_eval_a", "V4", "c10_storm2_w80")] = pool[("e1_eval_a", "V4", "c10_storm2_w80")][:2]
    drawn = ts.draw_even(pool, 60, seed=0)
    assert len(drawn) == 60
    small = [r for r in drawn if r["primary_class"] == "V4" and r["stratum"] == "c10_storm2_w80"]
    assert len(small) == 2  # the whole cell, and no more


def test_allocate_never_asks_a_cell_for_more_than_it_holds(ts):
    cells = ["a", "b", "c"]
    quota = ts.allocate(cells, 10, {"a": 1, "b": 2, "c": 100})
    assert quota["a"] == 1 and quota["b"] == 2 and quota["c"] == 7
    assert sum(quota.values()) == 10


def test_allocate_stops_when_the_pool_is_smaller_than_the_request(ts):
    quota = ts.allocate(["a", "b"], 10, {"a": 2, "b": 3})
    assert sum(quota.values()) == 5


def test_the_latency_subsample_is_deterministic_and_a_subset(ts):
    rows = []
    for part in ("opus_core_v3", "benign_v4_400"):
        for stratum in ("c09_storm2_w80", "c10_replay_400", "c10_storm2_w80"):
            for i in range(20):
                r = _row("e1_eval_a", "{}-{}-{:03d}".format(part, stratum, i),
                         stratum=stratum)
                r["sample_part"] = part
                rows.append(r)
    a = ts.draw_latency_subsample(rows, 30, seed=0)
    b = ts.draw_latency_subsample(rows, 30, seed=0)
    assert [ts.row_key(r) for r in a] == [ts.row_key(r) for r in b]
    assert len(a) == 30
    assert {ts.row_key(r) for r in a} <= {ts.row_key(r) for r in rows}


# --------------------------------------------------------------------------- #
# The Tier 2 reproduction gate                                                #
# --------------------------------------------------------------------------- #
ACCEPTED = {"terminal": "applied_with_certificate", "certificate_gap": 0.1238119606068551}


def test_the_gate_passes_a_faithful_replay(ts):
    replayed = {"terminal": "applied_with_certificate", "gap": 0.1238119606068551}
    assert ts.reproduction_mismatch(ACCEPTED, replayed) is None


def test_the_gate_fires_on_a_doctored_gap(ts):
    doctored = dict(ACCEPTED, certificate_gap=0.1238119606068552 + 1e-6)
    found = ts.reproduction_mismatch(
        doctored, {"terminal": "applied_with_certificate", "gap": 0.1238119606068551}
    )
    assert found is not None and set(found) == {"certificate_gap"}
    assert found["certificate_gap"]["accepted"] == pytest.approx(doctored["certificate_gap"])
    assert found["certificate_gap"]["replayed"] == pytest.approx(ACCEPTED["certificate_gap"])


def test_the_gate_fires_on_a_doctored_terminal(ts):
    found = ts.reproduction_mismatch(
        dict(ACCEPTED, terminal="blocked_qual"),
        {"terminal": "applied_with_certificate", "gap": ACCEPTED["certificate_gap"]},
    )
    assert found is not None and set(found) == {"terminal"}
    assert found["terminal"] == {"accepted": "blocked_qual",
                                 "replayed": "applied_with_certificate"}


def test_the_gate_fires_on_both_at_once_and_reports_both(ts):
    found = ts.reproduction_mismatch(
        dict(ACCEPTED, terminal="blocked_qual", certificate_gap=0.5),
        {"terminal": "applied_with_certificate", "gap": ACCEPTED["certificate_gap"]},
    )
    assert set(found) == {"terminal", "certificate_gap"}


def test_the_gate_fires_when_a_certificate_went_missing(ts):
    found = ts.reproduction_mismatch(
        ACCEPTED, {"terminal": "applied_with_certificate", "gap": None}
    )
    assert found is not None and set(found) == {"certificate_gap"}


def test_the_gate_tolerates_only_the_json_round_trip(ts):
    # One ulp of a float that survived a JSON round trip is not a mismatch; a
    # relative change of 1e-9 is.
    gap = ACCEPTED["certificate_gap"]
    assert ts.reproduction_mismatch(ACCEPTED, {"terminal": ACCEPTED["terminal"],
                                               "gap": float(repr(gap))}) is None
    assert ts.reproduction_mismatch(
        ACCEPTED, {"terminal": ACCEPTED["terminal"], "gap": gap * (1 + 1e-9)}
    ) is not None


# --------------------------------------------------------------------------- #
# The configurations the run is defined by                                    #
# --------------------------------------------------------------------------- #
def test_the_tier2_configuration_is_the_accepted_one(ts):
    from l1guard.config import G_CERT

    assert ts.CFG_T2.config_hash == G_CERT.with_(tier1_budget_s=0.0).config_hash
    assert ts.CFG_T2.lb_tier == "tier2"


def test_every_tier1_configuration_actually_calls_the_solver(ts):
    # G_CERT.lb_tier is "tier2", so a budget alone would never reach CP-SAT.
    for budget, cfg in ts.CFG_BEST.items():
        assert cfg.lb_tier == "best"
        assert cfg.tier1_budget_s == budget
        assert cfg.tau == ts.CFG_T2.tau and cfg.lb_floor_bh == ts.CFG_T2.lb_floor_bh
    assert ts.CFG_T1_LAT.lb_tier == "tier1"
    assert ts.CFG_T1_LAT.tier1_workers == 1
