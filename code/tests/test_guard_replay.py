"""Log-then-replay: a logged proposal re-derives its verdict exactly, offline."""

from __future__ import annotations

import json

import pytest

from l1adapter import dispatch, instances
from l1guard import G_CERT, G_FEAS, UNGUARDED, evaluate_proposal
from l1guard.logging import (
    OUTCOME_EMPTY_CONTENT,
    ProposalLog,
    ProposalRecord,
    prompt_hash,
    read_log,
)
from l1guard.replay import (
    InstanceCache,
    finding_counts,
    rerun,
    rerun_pairs,
    terminal_counts,
    _needs_baseline,
)

#: Twenty synthetic proposals: the clean ones, one of every stage-1 and stage-2
#: violation class the vocabulary has, the refusal signal, and a quality
#: violation.  They stand in for model outputs; no model is involved.
PROPOSALS = [
    '{"operations": []}',
    '{"operations": [{"op": "set_priority", "order_id": "%(o0)s", "priority_class": 1}]}',
    '{"operations": [{"op": "pin_next", "order_id": "%(o0)s", "trade": "%(trade)s"}]}',
    '{"operations": [{"op": "reassign_window", "order_id": "%(o1)s", "release_shift_bh": 8.0}]}',
    '{"operations": [{"op": "reassign_window", "order_id": "%(o1)s", '
    '"release_shift_bh": 5000.0}]}',
    '{"operations": [{"op": "freeze", "order_id": "%(o2)s"}]}',
    '{"operations": [{"op": "unfreeze", "order_id": "%(o2)s"}]}',
    '{"operations": [{"op": "set_priority", "order_id": "NO_SUCH_ORDER", "priority_class": 2}]}',
    '{"operations": [{"op": "batch", "building_id": "NO_SUCH_BUILDING", '
    '"trade": "%(trade)s"}]}',
    '{"operations": [{"op": "teleport", "order_id": "%(o0)s"}]}',
    '{"operations": [{"op": "set_priority", "order_id": "%(o0)s", "priority_class": 9}]}',
    '{"operations": [{"op": "set_priority", "order_id": "%(o0)s"}]}',
    "{not json at all",
    '```json\n{"operations": []}\n```',
    '{"operations": [{"op": "reorder", "order_id": "%(o0)s", "relation": "before", '
    '"ref_order_id": "%(o1)s"}]}',
    '{"operations": [{"op": "reorder", "order_id": "%(o2)s", "relation": "after", '
    '"ref_order_id": "%(o3)s"}]}',
    '{"operations": [{"op": "set_priority", "order_id": "%(o0)s", "priority_class": 4}, '
    '{"op": "set_priority", "order_id": "%(o0)s", "priority_class": 1}]}',
    '{"operations": [{"op": "pin_next", "order_id": "%(o0)s", "trade": "MISC"}]}',
    '[{"op": "freeze", "order_id": "%(o3)s"}]',
    '{"operations": [{"op": "set_priority", "order_id": "%(o1)s", "priority_class": 1}, '
    '{"op": "reassign_window", "order_id": "%(o1)s", "release_shift_bh": -4.0}]}',
]


def _fill(template: str, orders, trade: str) -> str:
    """Substitute real identifiers from the instance into a template."""
    fields = {"o{}".format(i): oid for i, oid in enumerate(orders)}
    fields["trade"] = trade
    return template % fields


@pytest.fixture(scope="module")
def records():
    paths = instances.list_instances(10, "replay", "150")[:2]
    out = []
    for k, path in enumerate(paths):
        inst = instances.load_instance(path)
        ids = [w["id"] for w in inst["work_orders"][:4]]
        trade = inst["work_orders"][0]["trade"]
        for i, template in enumerate(PROPOSALS):
            raw = _fill(template, ids, trade)
            out.append(
                ProposalRecord(
                    instruction_id="synthetic-{}-{}".format(k, i),
                    instance_id=inst["meta"]["id"],
                    instance_path=str(path),
                    model="synthetic",
                    mode="M_free",
                    prompt_hash=prompt_hash("system", raw),
                    raw_output=raw,
                    rule="atc",
                    seeds={"llm": 0, "dispatch": 0},
                )
            )
    return out


@pytest.fixture(scope="module")
def log_path(tmp_path_factory, records):
    path = tmp_path_factory.mktemp("logs") / "proposals.jsonl"
    log = ProposalLog(path)
    for rec in records:
        log.append(rec)
    return path


def _direct(record, config):
    """Evaluate a record without going through the log."""
    inst = instances.load_instance(record.instance_path)
    baseline = None
    if _needs_baseline(record):
        baseline = dispatch.dispatch_baseline(inst, config.rule, seed=config.seed)
    return evaluate_proposal(
        inst,
        record.raw_output,
        config,
        baseline_schedule=baseline,
        frozen_seed=tuple(record.frozen_seed or ()),
    )


def test_the_log_holds_one_line_per_call(log_path, records):
    assert len(ProposalLog(log_path)) == len(records) == 40
    assert len(read_log(log_path)) == 40


def test_every_line_is_valid_json_with_the_documented_fields(log_path):
    with open(log_path, "r", encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh]
    required = {
        "instruction_id", "instance_id", "model", "mode", "prompt_hash", "raw_output",
        "parsed_ops", "parse_error", "findings", "verdict", "certificate", "timings_ms",
        "seeds", "schema_hash", "config_hash", "timestamp", "reasoning_tokens",
        "cache_hit_tokens", "cache_hit", "outcome",
    }
    for row in rows:
        assert required <= set(row)


def test_g_cert_replay_reproduces_the_direct_verdict_exactly(log_path, records):
    replayed = rerun(log_path, G_CERT)
    assert len(replayed) == len(records)
    for record, verdict in zip(records, replayed):
        direct = _direct(record, G_CERT)
        assert verdict.fingerprint() == direct.fingerprint(), record.instruction_id
        assert verdict.digest() == direct.digest()


def test_the_three_arms_replay_from_the_same_log(log_path):
    per_arm = {
        cfg.name: terminal_counts(rerun(log_path, cfg))
        for cfg in (UNGUARDED, G_FEAS, G_CERT)
    }
    assert per_arm["UNGUARDED"].get("blocked_schema") is None
    assert per_arm["UNGUARDED"].get("blocked_feas") is None
    assert per_arm["G_FEAS"]["blocked_schema"] > 0
    assert per_arm["G_FEAS"].get("applied_with_certificate") is None
    assert per_arm["G_CERT"]["applied_with_certificate"] > 0
    # Everything G_FEAS applies, G_CERT either certifies or refuses on quality.
    applied_feas = per_arm["G_FEAS"].get("applied_uncertified", 0)
    cert = per_arm["G_CERT"].get("applied_with_certificate", 0)
    blocked_qual = per_arm["G_CERT"].get("blocked_qual", 0)
    assert applied_feas == cert + blocked_qual


def test_replay_accepts_a_preset_name(log_path):
    assert len(rerun(log_path, "G_FEAS")) == 40
    with pytest.raises(TypeError):
        rerun(log_path, 17)


def test_a_tau_sweep_is_a_replay(log_path):
    counts = {}
    for tau in (0.0, 0.2, 10.0, 1e9):
        verdicts = rerun(log_path, G_CERT.with_(tau=tau))
        counts[tau] = terminal_counts(verdicts).get("applied_with_certificate", 0)
    assert counts[0.0] <= counts[0.2] <= counts[10.0] <= counts[1e9]


def test_baselines_are_dispatched_only_when_a_proposal_can_need_one(log_path):
    cache = InstanceCache()
    rerun(log_path, G_CERT, cache=cache)
    assert cache.n_instance_loads == 2  # two distinct instances, loaded once each
    assert cache.n_baseline_dispatches == 2  # one per instance, for the freeze proposals


def test_the_finding_profile_is_recoverable_from_a_replay(log_path):
    verdicts = rerun(log_path, G_CERT)
    counts = finding_counts(verdicts)
    for code in (
        "malformed_json",
        "schema_invalid",
        "dangling_order_id",
        "dangling_building_id",
        "release_shift_out_of_range",
        "duplicate_operation",
        "empty_proposal",
        "not_frozen",
    ):
        assert counts.get(code, 0) > 0, code


def test_a_record_round_trips_through_json(records):
    rec = records[0]
    again = ProposalRecord.from_dict(json.loads(json.dumps(rec.to_dict())))
    assert again.to_dict() == rec.to_dict()


def test_an_unknown_field_in_a_log_line_is_kept_in_extra():
    rec = ProposalRecord.from_dict(
        {
            "instruction_id": "i",
            "instance_id": "x",
            "model": "m",
            "mode": "M_free",
            "future_field": 1,
        }
    )
    assert rec.extra == {"future_field": 1}


def test_attaching_a_verdict_fills_the_guard_side_of_the_record(records):
    verdict = _direct(records[0], G_CERT)
    rec = ProposalRecord(
        instruction_id="x", instance_id=verdict.instance_id, model="m", mode="M_free"
    )
    rec.attach_verdict(verdict)
    assert rec.verdict["terminal"] == verdict.terminal
    assert rec.certificate["gap"] == verdict.certificate.gap
    assert rec.schema_hash == verdict.schema_hash
    assert rec.config_name == "G_CERT"


def test_an_empty_completion_replays_as_a_schema_block_not_a_silent_pass(tmp_path):
    path = instances.list_instances(10, "replay", "150")[0]
    inst = instances.load_instance(path)
    log = ProposalLog(tmp_path / "empty.jsonl")
    log.append(
        ProposalRecord(
            instruction_id="empty-1",
            instance_id=inst["meta"]["id"],
            instance_path=str(path),
            model="synthetic",
            mode="M_free",
            raw_output="",
            outcome=OUTCOME_EMPTY_CONTENT,
        )
    )
    pairs = rerun_pairs(tmp_path / "empty.jsonl", G_CERT)
    record, verdict = pairs[0]
    assert record.outcome == OUTCOME_EMPTY_CONTENT  # the outcome class survives
    assert verdict.terminal == "blocked_schema"
    assert [f.code for f in verdict.findings] == ["malformed_json"]


def test_an_unresolvable_instance_path_fails_loudly(tmp_path):
    log = ProposalLog(tmp_path / "bad.jsonl")
    log.append(
        ProposalRecord(
            instruction_id="x",
            instance_id="nowhere",
            instance_path="/does/not/exist.json",
            model="m",
            mode="M_free",
            raw_output='{"operations": []}',
        )
    )
    with pytest.raises(FileNotFoundError):
        rerun(tmp_path / "bad.jsonl", G_CERT)


def test_the_prompt_hash_is_stable_and_order_sensitive():
    assert prompt_hash("a", "b") == prompt_hash("a", "b")
    assert prompt_hash("a", "b") != prompt_hash("b", "a")
    assert prompt_hash("a", None) == prompt_hash("a")
