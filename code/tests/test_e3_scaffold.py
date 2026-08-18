"""The E3 trajectory runner: the budget governor, the tools, the log, the replay.

Every test here is offline.  The model is the scripted mock transport, so the
real request builders and the real guard run, and no key is ever read: nothing
in this file touches the project ``.env`` or constructs a live client.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pytest

CODE_DIR = Path(__file__).resolve().parent.parent
for _p in (str(CODE_DIR), str(CODE_DIR / "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import e3_replay as e3r  # noqa: E402
import e3_sample  # noqa: E402
import e3_scaffold as e3s  # noqa: E402
import suite_gate as sg  # noqa: E402
from l1guard.models import M_CONSTRAINED, M_FREE, ChatClient  # noqa: E402

ARM = e3s.ARMS["sonnet"]


# --------------------------------------------------------------------------- #
# Fixtures: a handful of real items, rendered once                             #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def suite_rows():
    if not sg.SUITE_PATH.exists():  # pragma: no cover - sibling deliverable
        pytest.skip("suite v0.2 not on disk")
    return sg.load_suite()


@pytest.fixture(scope="module")
def items(suite_rows):
    """Five items off the frozen slice, one per class the mock scenarios need.

    Five, because the mock walks its five scenarios over the item order, so a
    five-item fixture exercises every one of them exactly once.
    """
    by_id = {r["item_id"]: r for r in suite_rows}
    ids = e3_sample.load_slice(e3_sample.SLICE_E3_300, rows=suite_rows)
    picked = []
    for cls in ("benign", "V3", "V4", "V5", "V6"):
        for item_id in ids:
            if by_id[item_id]["primary_class"] == cls:
                picked.append(by_id[item_id])
                break
    assert len(picked) == len(e3s.SCENARIOS) == 5
    return picked


@pytest.fixture(scope="module")
def preps(items):
    try:
        return e3s.prepare(items, sg.Instances(), e3s.TOP_K)
    except SystemExit as exc:  # pragma: no cover - Y1 instances absent
        pytest.skip("instances not resolvable: {}".format(exc))


@pytest.fixture(scope="module")
def services():
    return e3s.Services(top_k=e3s.TOP_K)


def make_args(**over):
    """The runner's own defaults, as the argument namespace the pipelines read."""
    args = argparse.Namespace(
        max_tokens=e3s.MAX_TOKENS,
        max_tool_rounds=e3s.MAX_TOOL_ROUNDS,
        max_revisions=e3s.MAX_REVISIONS,
        no_revision=False,
        workers=1,
        scenario_of=lambda item_id: "happy",
    )
    for key, value in over.items():
        setattr(args, key, value)
    return args


def mock_client(arm=ARM, **kwargs):
    """A client whose transport is the offline mock: no network, no key."""
    transport = e3s.MockTransport(arm, **kwargs)
    client = ChatClient(arm.backend, model=arm.model, api_key="mock-key-not-a-real-key",
                        max_tokens=e3s.MAX_TOKENS, transport=transport, max_retries=0,
                        retry_sleep_s=0.0)
    return client, transport


def run_trajectory(prep, services, pipeline, budget_tokens, scenario, args=None,
                   arm=ARM, transport=None, client=None):
    """One trajectory end to end, exactly as the runner drives it."""
    args = args or make_args()
    if client is None:
        client, transport = mock_client(arm)
    transport.set_scenario(scenario, prep.item["gold_ops"])
    traj = e3s.Trajectory(
        arm=arm, prep=prep, pipeline=pipeline, budget_level="test", repeat=0,
        run_uid="test", budget=e3s.Budget(budget_tokens, arm.chars_per_token,
                                          args.max_tokens),
        services=services, client=client, args=args,
    )
    e3s.PIPELINE_FUNCS[pipeline](traj)
    if not args.no_revision:
        e3s.guarded_tail(traj)
    return traj


# --------------------------------------------------------------------------- #
# The budget governor                                                          #
# --------------------------------------------------------------------------- #
def test_the_accounting_is_the_sum_of_prompt_and_completion_over_every_call():
    budget = e3s.Budget(10000, 2.0)
    budget.charge({"prompt_tokens": 100, "completion_tokens": 20}, 0)
    budget.charge({"prompt_tokens": 300, "completion_tokens": 40}, 0)
    assert budget.prompt_tokens == 400
    assert budget.completion_tokens == 60
    assert budget.spent == 460
    assert budget.calls == 2


def test_the_accounting_is_cache_blind():
    """A cached prompt costs the same as an uncached one: caching is billing."""
    cached = e3s.Budget(10000, 2.0)
    cached.charge({"prompt_tokens": 1000, "completion_tokens": 10,
                   "cache_hit_tokens": 990, "cache_miss_tokens": 10}, 0)
    fresh = e3s.Budget(10000, 2.0)
    fresh.charge({"prompt_tokens": 1000, "completion_tokens": 10,
                  "cache_hit_tokens": 0, "cache_miss_tokens": 1000}, 0)
    assert cached.spent == fresh.spent == 1010


def test_a_call_with_no_reported_usage_is_charged_the_estimate():
    budget = e3s.Budget(10000, 2.0)
    charged = budget.charge({}, 137)
    assert charged["from_estimate"] is True
    assert budget.spent == 137
    assert budget.estimated_calls == 1


def test_the_estimate_is_the_characters_over_the_arms_own_rate():
    budget = e3s.Budget(10000, 2.0)
    assert budget.estimate(1000) == 500
    assert budget.estimate(1001) == 501  # rounded up: never under-count
    assert budget.estimate(0) == 1


def test_a_call_that_cannot_be_afforded_is_refused_and_the_budget_is_exhausted():
    budget = e3s.Budget(1000, 2.0)
    budget.charge({"prompt_tokens": 800, "completion_tokens": 100}, 0)
    ok, max_tokens = budget.allow(prompt_chars=1000)  # 500 more tokens, only 100 left
    assert ok is False
    assert max_tokens == 0
    assert budget.exhausted is True


def test_max_tokens_is_clipped_to_what_the_budget_leaves():
    budget = e3s.Budget(1000, 2.0, max_tokens=512)
    ok, max_tokens = budget.allow(prompt_chars=1200)  # 600 tokens of prompt
    assert ok is True
    assert max_tokens == 400  # 1000 - 0 spent - 600 projected
    budget.charge({"prompt_tokens": 600, "completion_tokens": 100}, 0)
    ok, max_tokens = budget.allow(prompt_chars=200)  # 100 tokens of prompt
    assert (ok, max_tokens) == (True, 200)


def test_max_tokens_never_exceeds_the_per_call_ceiling():
    budget = e3s.Budget(1000000, 2.0, max_tokens=64)
    assert budget.allow(prompt_chars=100) == (True, 64)


def test_an_uncapped_budget_never_refuses_and_never_clips_below_the_ceiling():
    budget = e3s.Budget(0, 2.0, max_tokens=256)
    budget.charge({"prompt_tokens": 10 ** 6, "completion_tokens": 10 ** 6}, 0)
    assert budget.allow(prompt_chars=10 ** 7) == (True, 256)
    assert budget.remaining() is None


# --------------------------------------------------------------------------- #
# The governor inside a trajectory                                             #
# --------------------------------------------------------------------------- #
def test_a_budget_too_small_for_the_first_call_ends_in_a_referral(preps, services):
    prep = list(preps.values())[0]
    traj = run_trajectory(prep, services, e3s.PIPELINE_SINGLE, 200, "happy")
    assert traj.calls == []
    assert traj.budget.exhausted is True
    assert [f["reason"] for f in traj.forced] == [e3s.FORCE_BUDGET]
    assert traj.first_final["source"] == "forced_referral"
    assert json.loads(traj.first_final["raw_output"])["operations"] == []


def test_the_budget_binds_mid_pipeline_and_the_arm_finalises_from_its_best(preps,
                                                                          services):
    prep = list(preps.values())[0]
    row = None
    for budget in (3000, 3500, 4000, 4500, 5000):
        traj = run_trajectory(prep, services, e3s.PIPELINE_MULTI, budget, "budget")
        if traj.calls and traj.budget.exhausted:
            row = traj
            break
    assert row is not None, "no budget in the sweep bound mid-pipeline"
    assert any(f["reason"] == e3s.FORCE_BUDGET for f in row.forced)
    assert row.first_final is not None  # the arm still ends with a disposition
    assert row.stopped is True
    # Every call it did make stayed inside the ceiling.
    assert row.budget.spent <= row.budget.budget + row.args.max_tokens


def test_the_trajectory_stops_at_the_first_refusal(preps, services):
    """Prompts only grow, so a stage that cannot be afforded ends the trajectory."""
    prep = list(preps.values())[0]
    traj = run_trajectory(prep, services, e3s.PIPELINE_MULTI, 3600, "budget")
    forced = [f for f in traj.forced if f["reason"] == e3s.FORCE_BUDGET]
    assert len(forced) <= 1
    assert len(traj.stages) == len(traj.calls)


def test_every_call_of_a_trajectory_is_charged_to_one_counter(preps, services):
    prep = list(preps.values())[0]
    traj = run_trajectory(prep, services, e3s.PIPELINE_MULTI, 0, "tools")
    assert traj.budget.calls == len(traj.calls)
    assert traj.budget.spent == sum(
        c["charged"]["charged"] for c in traj.calls)
    assert traj.budget.spent == sum(
        (c["usage"] or {}).get("prompt_tokens", 0)
        + (c["usage"] or {}).get("completion_tokens", 0) for c in traj.calls)


def test_the_revision_tail_is_charged_to_the_same_budget(preps, services):
    prep = [p for p in preps.values() if p.item["primary_class"] == "benign"][0]
    traj = run_trajectory(prep, services, e3s.PIPELINE_SINGLE, 0, "blocked")
    assert traj.revisions, "the blocked scenario must produce a revision tail"
    assert "revision" in traj.stages
    assert traj.budget.calls == len(traj.calls)  # the tail is inside the accounting


# --------------------------------------------------------------------------- #
# Prompt assembly                                                              #
# --------------------------------------------------------------------------- #
def test_the_user_message_is_the_frozen_state_block_then_the_stage_block(preps):
    prep = list(preps.values())[0]
    prefix, tail = e3s.user_message(prep, "STAGE BLOCK")
    assert prefix == prep.state
    assert prefix + tail == prep.state + e3s.STATE_STAGE_SEPARATOR + "STAGE BLOCK"
    assert prep.state == e3s.PROMPTS.user_prompt(
        sg.Instances().get(prep.item), prep.item, e3s.TOP_K)


def test_operations_stages_carry_the_byte_identical_e1_system_prompt():
    for stage, kind in e3s.STAGE_KINDS.items():
        system = e3s.system_for(stage)
        if kind == e3s.KIND_OPS:
            assert system == e3s.PROMPTS.SYSTEM_PROMPT
            assert e3s.mode_for(stage, ARM) == M_CONSTRAINED
        else:
            assert system == e3s.SYSTEM_REASON
            assert e3s.mode_for(stage, ARM) == M_FREE


def test_the_stages_that_emit_an_operations_list_are_the_constrained_ones():
    assert {s for s, k in e3s.STAGE_KINDS.items() if k == e3s.KIND_OPS} == {
        "single_final", "multi_plan", "multi_ctrl", "revision"}


def test_the_tool_vocabulary_is_closed_and_shared():
    assert e3s.TOOLS == (e3s.TOOL_GET_STATE, e3s.TOOL_PREVIEW, e3s.TOOL_NONE)


def test_the_two_pipelines_ask_the_same_two_tools_in_the_same_words():
    single = e3s.block_single_act([], 2, 2)
    multi = e3s.block_multi_sched("obs", [], 2, 2)
    contract = e3s._TOOL_CONTRACT.format(left=2, total=2)
    assert contract in single and contract in multi


# --------------------------------------------------------------------------- #
# The two deterministic tools                                                  #
# --------------------------------------------------------------------------- #
def test_get_state_is_deterministic_and_never_raises(preps, services):
    prep = list(preps.values())[0]
    order = prep.item["referenced"]["order_ids"]
    for query in (order[0] if order else "board", "", "NOT_A_THING", "W1 W2 D30"):
        first = services.get_state(prep, query)
        assert first == services.get_state(prep, query)
        assert isinstance(first, str) and first


def test_get_state_answers_with_the_state_blocks_own_rendering(preps, services):
    prep = [p for p in preps.values() if p.item["referenced"]["order_ids"]][0]
    order_id = prep.item["referenced"]["order_ids"][0]
    text = services.get_state(prep, order_id)
    if order_id in prep.state:  # a dangling id is not on the board by construction
        assert order_id in text
        assert e3s.PROMPTS._ORDER_HEADER in text


def test_preview_dispatch_reports_the_objective_and_is_deterministic(preps, services):
    prep = [p for p in preps.values() if p.item["gold_ops"]][0]
    first = services.preview_dispatch(prep, prep.item["gold_ops"])
    assert first == services.preview_dispatch(prep, prep.item["gold_ops"])
    assert "weighted tardiness with your operations" in first
    assert "weighted tardiness as the board stands" in first
    # The simulator never leaks a certificate: the guard stays outside.
    assert "gap" not in first.lower() and "lower bound" not in first.lower()


def test_preview_dispatch_refuses_rather_than_raises(preps, services):
    prep = list(preps.values())[0]
    for bad in ("not a list", [{"op": "teleport"}], [{"op": "set_priority",
                                                      "order_id": "NOPE",
                                                      "priority_class": 1}]):
        text = services.preview_dispatch(prep, bad)
        assert text.startswith("PREVIEW REFUSED") or text.startswith("PREVIEW FAILED")


# --------------------------------------------------------------------------- #
# Parsing what a stage returned                                                #
# --------------------------------------------------------------------------- #
def test_an_action_is_read_through_fences_and_prose():
    assert e3s.parse_action('{"tool": "none"}')["tool"] == e3s.TOOL_NONE
    assert e3s.parse_action('```json\n{"tool": "get_state", "query": "W1"}\n```') == {
        "tool": "get_state", "query": "W1"}
    assert e3s.parse_action('here you go: {"tool": "none"} thanks')["tool"] == "none"


def test_an_unparseable_action_becomes_no_tool_and_records_why():
    action = e3s.parse_action("I would like to look at the board please")
    assert action["tool"] == e3s.TOOL_NONE
    assert action["parse_error"]


def test_a_strategy_is_not_a_tool_call():
    action = e3s.parse_action('{"strategy": "raise W1 and pin it"}')
    assert action["tool"] == e3s.TOOL_NONE
    assert action["strategy"] == "raise W1 and pin it"


def test_the_operation_count_of_a_proposal():
    assert e3s.n_ops('{"operations": []}') == 0
    assert e3s.n_ops('{"operations": [{"op": "freeze", "order_id": "W1"}]}') == 1
    assert e3s.n_ops("not json") == -1


# --------------------------------------------------------------------------- #
# The five mock scenarios                                                      #
# --------------------------------------------------------------------------- #
def test_the_happy_path_answers_in_two_calls_and_is_not_blocked(preps, services):
    prep = [p for p in preps.values() if p.item["primary_class"] == "benign"][0]
    traj = run_trajectory(prep, services, e3s.PIPELINE_SINGLE, 0, "happy")
    assert traj.stages == ["single_act", "single_final"]
    assert traj.first_final["source"] == "call"
    assert traj.guard_chain and traj.guard_chain[0]["blocked"] is False
    assert traj.revisions == []


def test_the_tool_scenario_uses_both_tools_and_shows_their_results(preps, services):
    prep = [p for p in preps.values() if p.item["primary_class"] == "benign"][0]
    traj = run_trajectory(prep, services, e3s.PIPELINE_SINGLE, 0, "tools")
    assert [e["tool"] for e in traj.tool_rounds] == [e3s.TOOL_GET_STATE,
                                                     e3s.TOOL_PREVIEW]
    assert traj.stages == ["single_act", "single_act", "single_final"]
    # The tool result is injected as text into the next prompt, for every vendor.
    assert "TOOL ROUNDS SO FAR" in e3s.block_single_final(traj.tool_rounds)
    assert traj.calls[0]["tool_result"]


def test_the_blocked_scenario_is_refused_then_revised(preps, services):
    prep = [p for p in preps.values() if p.item["primary_class"] == "benign"][0]
    traj = run_trajectory(prep, services, e3s.PIPELINE_MULTI, 0, "blocked")
    assert traj.guard_chain[0]["blocked"] is True
    assert traj.guard_chain[0]["terminal"] == "blocked_schema"
    assert len(traj.revisions) == 1
    assert traj.guard_chain[-1]["blocked"] is False
    assert traj.stages[-1] == "revision"


def test_the_refusal_scenario_emits_the_empty_operations_list(preps, services):
    prep = list(preps.values())[0]
    traj = run_trajectory(prep, services, e3s.PIPELINE_SINGLE, 0, "refusal")
    assert traj.first_final["n_ops"] == 0
    assert json.loads(traj.first_final["raw_output"]) == {"operations": []}


def test_a_provider_error_stops_the_trajectory_and_marks_the_row(preps, services):
    prep = list(preps.values())[0]
    client, transport = mock_client(fail_every=1)  # every call is a terminal 400
    traj = run_trajectory(prep, services, e3s.PIPELINE_SINGLE, 0, "happy",
                          transport=transport, client=client)
    assert traj.error and "HTTP 400" in traj.error
    assert traj.stopped is True
    row = e3s.trajectory_row(traj, 0.0)
    assert row["outcome"] == "error"


def test_a_raising_service_becomes_an_error_row_and_never_kills_the_grid(preps,
                                                                        services,
                                                                        monkeypatch):
    prep = list(preps.values())[0]
    client, transport = mock_client()
    args = make_args()
    monkeypatch.setattr(services, "guard",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    row, calls = e3s.run_one(
        {"item_id": prep.item["item_id"], "budget_level": "test", "budget_tokens": 0,
         "pipeline": e3s.PIPELINE_SINGLE, "repeat": 0, "arm": ARM.arm},
        ARM, preps, services, client, args, transport)
    assert row["outcome"] == "error"
    assert "RuntimeError: boom" in row["error"]
    assert row["first_final"] is not None
    assert calls  # the calls it did make are still in the record


def test_the_multi_pipeline_runs_four_roles_and_no_deterministic_checker(preps,
                                                                        services):
    prep = [p for p in preps.values() if p.item["primary_class"] == "benign"][0]
    traj = run_trajectory(prep, services, e3s.PIPELINE_MULTI, 0, "happy",
                          args=make_args(no_revision=True))
    assert traj.stages == ["multi_obs", "multi_sched", "multi_plan", "multi_ctrl"]
    assert traj.first_final["stage"] == "multi_ctrl"  # the executor has the last word
    assert traj.guard_chain == []  # the guard is outside the architecture


# --------------------------------------------------------------------------- #
# The log, the resume, and the replay                                          #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def logged(tmp_path_factory, preps, services):
    """A complete mock grid over the fixture items, in a temporary directory."""
    out = tmp_path_factory.mktemp("e3run")
    args = make_args(workers=1)
    order = list(preps)
    args.scenario_of = lambda item_id: e3s.SCENARIOS[order.index(item_id) % 5]
    client, transport = mock_client()
    levels = [(e3s.BUDGET_TIGHT, 0), (e3s.BUDGET_LOOSE, 0)]
    groups = e3s.build_plan(ARM, order, levels, list(e3s.PIPELINES), 1)
    tally = e3s.run(ARM, groups, preps, services, client, args, transport,
                    out / "trajectories.jsonl", out / "calls.jsonl")
    return {"dir": out, "tally": tally, "groups": groups, "args": args,
            "client": client, "transport": transport, "levels": levels}


def read_rows(path):
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def test_the_log_holds_one_row_per_trajectory_and_one_per_call(logged, preps):
    traj_rows = read_rows(logged["dir"] / "trajectories.jsonl")
    call_rows = read_rows(logged["dir"] / "calls.jsonl")
    assert len(traj_rows) == len(preps) * 2 * 2  # items x budgets x pipelines
    assert len(call_rows) == sum(r["n_calls"] for r in traj_rows)
    keys = {e3s.traj_key(r) for r in traj_rows}
    assert len(keys) == len(traj_rows)  # the resume key is unique per trajectory


def test_every_call_row_carries_the_usage_fields_and_its_trajectory(logged):
    for row in read_rows(logged["dir"] / "calls.jsonl"):
        assert set(row) >= {"run_uid", "call_index", "stage", "mode", "enforcement",
                            "prompt_hash", "max_tokens_sent", "raw_output", "usage",
                            "charged", "tokens_after", "is_first_final", "arm",
                            "item_id", "pipeline", "budget_level", "repeat"}
        assert set(row["usage"]) >= {"prompt_tokens", "completion_tokens",
                                     "cache_hit_tokens", "cache_miss_tokens"}


def test_the_first_final_is_marked_as_the_replay_boundary(logged):
    calls = read_rows(logged["dir"] / "calls.jsonl")
    by_traj = {}
    for row in calls:
        by_traj.setdefault(row["run_uid"], []).append(row)
    for rows in by_traj.values():
        marked = [r for r in rows if r["is_first_final"]]
        assert len(marked) <= 1
        if marked:
            assert e3s.STAGE_KINDS[marked[0]["stage"]] == e3s.KIND_OPS


def test_a_relaunch_over_a_complete_log_adds_no_rows(logged, preps, services):
    path = logged["dir"] / "trajectories.jsonl"
    before = len(read_rows(path))
    done, rows, errors, broken = e3s.read_completed(path, ARM)
    assert rows == before
    assert errors == 0
    remaining = e3s.remaining_groups(logged["groups"], done, ARM, 0)
    assert remaining == []
    assert e3s.count_jobs(remaining) == 0
    # And running what is left writes nothing.
    e3s.run(ARM, remaining, preps, services, logged["client"], logged["args"],
            logged["transport"], path, logged["dir"] / "calls.jsonl")
    assert len(read_rows(path)) == before


def test_an_error_row_is_not_complete_and_is_retried(tmp_path, logged):
    path = tmp_path / "trajectories.jsonl"
    rows = read_rows(logged["dir"] / "trajectories.jsonl")
    broken = dict(rows[0], outcome="error", error="HTTP 500")
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
        fh.write(json.dumps(broken) + "\n")  # the later row supersedes the good one
    done, _rows, errors, _broken = e3s.read_completed(path, ARM)
    assert errors == 1
    assert e3s.traj_key(broken) not in done
    remaining = e3s.remaining_groups(logged["groups"], done, ARM, 0)
    assert e3s.count_jobs(remaining) == 1


def test_a_log_written_by_another_arm_is_refused(tmp_path, logged):
    path = tmp_path / "trajectories.jsonl"
    rows = read_rows(logged["dir"] / "trajectories.jsonl")
    path.write_text(json.dumps(dict(rows[0], arm="opus", model="claude-opus-5")) + "\n")
    with pytest.raises(SystemExit):
        e3s.read_completed(path, ARM)


def test_a_log_from_another_prompt_version_is_refused(tmp_path, logged):
    path = tmp_path / "trajectories.jsonl"
    rows = read_rows(logged["dir"] / "trajectories.jsonl")
    path.write_text(json.dumps(dict(rows[0], e3_prompt_version="l1-e3-prompt-0.0.1"))
                    + "\n")
    with pytest.raises(SystemExit):
        e3s.read_completed(path, ARM)


# --------------------------------------------------------------------------- #
# Replay                                                                       #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def replayed(logged):
    rows, stats = e3r.load_trajectories([logged["dir"] / "trajectories.jsonl"])
    return rows, stats, e3r.evaluate_rows(rows, workers=1)


def test_the_same_log_replays_to_the_same_verdicts(logged, replayed):
    rows, _stats, first = replayed
    again = e3r.evaluate_rows(rows, workers=1)
    assert len(first) == len(again) == len(rows)
    for a, b in zip(first, again):
        assert a["key"] == b["key"]
        for name in a["variants"]:
            assert a["variants"][name] == b["variants"][name]


def test_the_replayed_verdict_equals_the_one_the_runner_logged_live(replayed):
    _rows, _stats, verdicts = replayed
    assert [v["replay_mismatch"] for v in verdicts if v["replay_mismatch"]] == []


def test_each_pipeline_yields_its_guarded_and_unguarded_variant(replayed):
    rows, _stats, verdicts = replayed
    by_key = {tuple(v["key"]): v for v in verdicts}
    for row in rows:
        names = set(by_key[e3r.traj_key(row)]["variants"])
        if row["pipeline"] == "SINGLE":
            assert names == {"SINGLE-UG", "SINGLE+G"}
        else:
            assert names == {"MULTI-UG", "MULTI-G"}


def test_an_empty_operations_list_is_a_referral_not_an_acceptance(replayed):
    rows, _stats, verdicts = replayed
    by_key = {tuple(v["key"]): v for v in verdicts}
    seen = 0
    for row in rows:
        if (row["first_final"] or {}).get("n_ops") != 0:
            continue
        seen += 1
        for verdict in by_key[e3r.traj_key(row)]["variants"].values():
            assert verdict["terminal"] == e3r.T_REFERRED
    assert seen, "the fixture must contain at least one refusal"


def test_the_guarded_variant_walks_the_revision_tail(replayed):
    rows, _stats, verdicts = replayed
    by_key = {tuple(v["key"]): v for v in verdicts}
    revised = [r for r in rows if r["revisions"]]
    assert revised, "the fixture must contain at least one revised trajectory"
    for row in revised:
        variants = by_key[e3r.traj_key(row)]["variants"]
        guarded = variants["SINGLE+G" if row["pipeline"] == "SINGLE" else "MULTI-G"]
        unguarded = variants["{}-UG".format(row["pipeline"])]
        assert guarded["proposals"] == len(row["revisions"]) + 1
        assert guarded["applied_source"].startswith("revision")
        assert unguarded["proposals"] == 1  # the unguarded arm never sees the tail
        assert unguarded["applied_source"] == "first_final"


def test_a_block_is_correct_on_a_violation_and_false_on_a_benign_twin(replayed):
    rows, _stats, verdicts = replayed
    by_key = {tuple(v["key"]): v for v in verdicts}
    for row in rows:
        for verdict in by_key[e3r.traj_key(row)]["variants"].values():
            if verdict["terminal"] == e3r.T_BLOCKED_FALSE:
                assert row["primary_class"] == "benign"
            if verdict["terminal"] == e3r.T_BLOCKED_CORRECT:
                assert row["primary_class"] != "benign"


def test_the_profile_counts_every_trajectory_once_per_variant(replayed):
    rows, _stats, verdicts = replayed
    cells = e3r.aggregate(rows, verdicts)
    good = [r for r in rows if r.get("outcome") != "error"]
    assert sum(c["n"] for c in cells.values()) == 2 * len(good)
    for cell in cells.values():
        assert sum(cell["terminals"].values()) == cell["n"]
        assert set(cell["terminals"]) <= set(e3r.TERMINALS)
        assert cell["warranted"] == sum(
            cell["terminals"].get(t, 0) for t in e3r.WARRANTED)


def test_the_summary_renders(replayed, logged):
    rows, stats, verdicts = replayed
    cells = e3r.aggregate(rows, verdicts)
    text = e3r.summarise(cells, e3r.twin_pairs(rows, verdicts), rows, stats,
                         {"UNGUARDED": "a" * 64, "G_CERT": "b" * 64}, [])
    assert "Trustworthiness profile" in text
    assert "warranted" in text


def test_the_budget_flag_survives_into_the_verdict_rows(replayed):
    rows, _stats, verdicts = replayed
    by_key = {tuple(v["key"]): v for v in verdicts}
    assert all(e3r.traj_key(r) in by_key for r in rows)


def test_an_api_error_trajectory_is_reported_but_never_enters_a_rate(replayed):
    rows, _stats, verdicts = replayed
    failed = dict(rows[0], outcome="error", error="HTTP 500")
    cells = e3r.aggregate(rows[1:] + [failed], verdicts)
    assert sum(c["errors"] for c in cells.values()) == 2  # both of its variants
    assert sum(c["n"] for c in cells.values()) == 2 * (len(rows) - 1)
    for cell in cells.values():
        assert sum(cell["terminals"].values()) == cell["n"]


# --------------------------------------------------------------------------- #
# The wire: one uniform contract across vendors                                #
# --------------------------------------------------------------------------- #
def _bodies_for(arm, preps, services, pipeline=e3s.PIPELINE_MULTI):
    client, transport = mock_client(arm)
    prep = [p for p in preps.values() if p.item["primary_class"] == "benign"][0]
    run_trajectory(prep, services, pipeline, 0, "tools", arm=arm,
                   transport=transport, client=client)
    return transport.bodies, prep


@pytest.mark.parametrize("arm_name", ["sonnet", "openai", "deepseek", "qwen14b"])
def test_no_vendor_native_tool_api_is_ever_sent(arm_name, preps, services):
    bodies, _prep = _bodies_for(e3s.ARMS[arm_name], preps, services)
    assert bodies
    for body in bodies:
        assert "tools" not in body
        assert "tool_choice" not in body
        assert "functions" not in body


@pytest.mark.parametrize("arm_name,field", [("sonnet", "output_config"),
                                            ("openai", "response_format"),
                                            ("deepseek", "response_format"),
                                            ("qwen14b", "structured_outputs")])
def test_only_the_operations_stages_carry_the_enforcement_field(arm_name, field,
                                                                preps, services):
    arm = e3s.ARMS[arm_name]
    bodies, _prep = _bodies_for(arm, preps, services)
    constrained = [b for b in bodies if field in b]
    # MULTI emits an operations list twice (plan, execute) plus any revision.
    assert len(constrained) >= 2
    assert len(constrained) < len(bodies)  # the observe and select stages are free


def test_the_anthropic_wire_splits_the_user_message_and_caches_the_state_block(
        preps, services):
    bodies, prep = _bodies_for(e3s.ARMS["sonnet"], preps, services)
    for body in bodies:
        blocks = body["messages"][0]["content"]
        assert len(blocks) == 2
        assert blocks[0]["cache_control"] == {"type": "ephemeral"}
        assert blocks[0]["text"] == prep.state  # the whole frozen state block
        assert "cache_control" not in blocks[1]
        assert body.get("thinking") == {"type": "disabled"}
        assert "temperature" not in body  # the 5-series rejects it


def test_the_two_wires_send_the_same_prompt(preps, services):
    anthropic, prep = _bodies_for(e3s.ARMS["sonnet"], preps, services)
    openai, _ = _bodies_for(e3s.ARMS["openai"], preps, services)
    a_user = ["".join(b["text"] for b in body["messages"][0]["content"])
              for body in anthropic]
    o_user = [body["messages"][1]["content"] for body in openai]
    assert a_user[0] == o_user[0]
    assert a_user[0].startswith(prep.state)


def test_the_json_object_arm_keeps_the_word_json_in_the_operations_prompt():
    assert "json" in e3s.SYSTEM_OPS.lower()


# --------------------------------------------------------------------------- #
# The arm table and the envelope                                               #
# --------------------------------------------------------------------------- #
def test_every_arm_runs_one_enforcement_mode_and_one_thinking_label():
    for name, arm in e3s.ARMS.items():
        assert arm.mode == M_CONSTRAINED, name
        assert isinstance(arm.thinking_body, dict)
        assert arm.repeats >= 1
        assert arm.e1.prices and arm.chars_per_token > 0


def test_the_local_arms_reuse_the_e1_arm_record_shape():
    for name in ("qwen14b", "qwen27b"):
        arm = e3s.ARMS[name]
        assert arm.backend == "vllm"
        assert arm.e1.prices[0][1]["in"] == 0.0
        assert Path(arm.model).name  # a pinned snapshot path, not an API id


def test_the_hosted_arms_take_their_prices_from_the_e1_table():
    import grid_e1_hosted as e1h

    for name in ("deepseek", "openai", "sonnet", "opus"):
        assert e3s.ARMS[name].e1 is e1h.ARMS[name]


def test_the_envelope_is_the_freezes(capsys):
    assert e3s.ENVELOPE_USD["anthropic"] == 45.0
    assert e3s.ENVELOPE_USD["openai"] == 8.0
    assert e3s.ENVELOPE_USD["deepseek"] == 8.0
    assert e3s.launch_gate(e3s.ARMS["openai"], 3.9) is True
    assert e3s.launch_gate(e3s.ARMS["sonnet"], 20.0, partner=30.0) is False
    out = capsys.readouterr().out
    assert "BUSTS THE ENVELOPE" in out
    assert "E3-240" in out  # the pre-declared fallback, never an ad-hoc trim


def test_the_guard_in_the_loop_is_e1s_own_configuration():
    import e1_evaluate as e1e

    services = e3s.Services()
    assert services.guard_config.config_hash == e1e.guard_configs()["G_CERT"].config_hash
    assert services.guard_config.tau == 0.2
    assert services.guard_config.lb_tier == "tier2"
