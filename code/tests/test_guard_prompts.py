"""The published prompt: fixed, deterministic, and it always shows the referents."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from l1adapter import instances
from l1guard import prompts
from l1guard.prompts import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_messages,
    prompt_fingerprint,
    user_prompt,
)
from micro import make_instance, order

SUITE = Path(__file__).resolve().parent.parent / "suite" / "v0.2" / "suite.jsonl"


@pytest.fixture(scope="module")
def suite():
    if not SUITE.exists():  # pragma: no cover - the suite is a sibling deliverable
        pytest.skip("suite v0.2 not on disk")
    return [json.loads(line) for line in SUITE.open()]


@pytest.fixture(scope="module")
def loader():
    cache: dict = {}

    def load(item):
        meta = item["instance"]
        key = meta["file"]
        if key not in cache:
            campus = int(meta["campus"][1:])
            size = meta["size"] or None
            path = [
                p
                for p in instances.list_instances(campus, meta["track"], size)
                if p.name == key
            ][0]
            cache[key] = instances.load_instance(path)
        return cache[key]

    return load


def micro_item(**over):
    item = {
        "item_id": "T-1",
        "instruction": "Please raise work order A to the most urgent class.",
        "referenced": {"order_ids": ["A"], "trades": ["B20"], "buildings": []},
        "episode": {"frozen_seed": [], "rule": "atc", "seed": 0, "t_bh": 0.0},
        "instance": {"instance_id": "micro", "campus": "c00"},
    }
    item.update(over)
    return item


@pytest.fixture()
def inst():
    return make_instance(
        [
            order("A", "B20", 1.0, building="BLD1"),
            order("B", "B20", 2.0, priority=1, building="BLD1"),
            order("C", "C10", 3.0, priority=2),
        ],
        [("T1", "B20"), ("T2", "C10")],
    )


# --------------------------------------------------------------------------- #
# the system message                                                           #
# --------------------------------------------------------------------------- #
def test_the_system_message_names_all_seven_operations():
    for op in (
        "set_priority",
        "pin_next",
        "reorder",
        "reassign_window",
        "freeze",
        "unfreeze",
        "batch",
    ):
        assert op in SYSTEM_PROMPT


def test_the_system_message_states_the_output_contract():
    assert '{"operations": [ ... ]}' in SYSTEM_PROMPT
    assert '{"operations": []}' in SYSTEM_PROMPT
    assert "json" in SYSTEM_PROMPT  # DeepSeek's JSON mode requires the word
    assert "Do not explain" in SYSTEM_PROMPT


def test_the_system_message_carries_the_frozen_operation_semantics():
    # The load-bearing clauses, copied from decisions.md.
    assert "full class shift" in SYSTEM_PROMPT
    assert "next dispatch decision" in SYSTEM_PROMPT
    assert "start-order precedence" in SYSTEM_PROMPT
    assert "max(0, release + release_shift_bh)" in SYSTEM_PROMPT
    assert "same-technician consecutive chain" in SYSTEM_PROMPT
    assert "8 / 24 / 80 / 171.4" in SYSTEM_PROMPT


def test_the_prompt_is_versioned():
    assert PROMPT_VERSION == "l1-prompt-1.0.0"


# --------------------------------------------------------------------------- #
# determinism                                                                  #
# --------------------------------------------------------------------------- #
def test_two_calls_render_the_same_bytes(inst):
    item = micro_item()
    a = build_messages(inst, item)
    b = build_messages(inst, item)
    assert a == b
    assert prompt_fingerprint(a) == prompt_fingerprint(b)


def test_the_fingerprint_separates_two_items(inst):
    a = build_messages(inst, micro_item())
    b = build_messages(inst, micro_item(instruction="Freeze work order A."))
    assert prompt_fingerprint(a) != prompt_fingerprint(b)


def test_order_of_the_referenced_lists_does_not_change_the_prompt(inst):
    a = user_prompt(inst, micro_item(referenced={"order_ids": ["A", "B"],
                                                 "trades": ["B20", "C10"], "buildings": []}))
    b = user_prompt(inst, micro_item(referenced={"order_ids": ["B", "A"],
                                                 "trades": ["C10", "B20"], "buildings": []}))
    assert a == b


def test_build_messages_returns_exactly_a_system_and_a_user_turn(inst):
    messages = build_messages(inst, micro_item())
    assert [m["role"] for m in messages] == ["system", "user"]
    assert messages[0]["content"] == SYSTEM_PROMPT


# --------------------------------------------------------------------------- #
# what the state block must contain                                            #
# --------------------------------------------------------------------------- #
def test_every_referenced_order_appears_in_full(inst):
    text = user_prompt(inst, micro_item(referenced={"order_ids": ["A", "C"],
                                                    "trades": [], "buildings": []}))
    assert "Work orders this request refers to:" in text
    for oid in ("A", "C"):
        assert "\n  {:<10s}".format(oid) in text


def test_a_referenced_order_that_is_not_on_the_site_is_named_as_such(inst):
    text = user_prompt(inst, micro_item(referenced={"order_ids": ["A", "W999"],
                                                    "trades": [], "buildings": []}))
    assert "not on this site: W999" in text


def test_the_trade_table_covers_every_trade_with_crews_and_counts(inst):
    text = user_prompt(inst, micro_item())
    assert "Crews and work on the board, by trade:" in text
    assert "\n  B20  " in text and "\n  C10  " in text


def test_the_per_trade_board_is_capped_and_excludes_what_was_already_listed(inst):
    text = user_prompt(inst, micro_item(referenced={"order_ids": ["A"], "trades": ["B20"],
                                                    "buildings": []}), top_k=1)
    board = text.split("Trade B20")[1]
    assert "B" in board  # the other B20 order
    assert board.count("\n  A ") == 0  # A was already shown as a referent


def test_the_building_block_appears_only_when_a_building_is_referenced(inst):
    without = user_prompt(inst, micro_item())
    assert "Buildings this request refers to:" not in without
    with_building = user_prompt(
        inst, micro_item(referenced={"order_ids": [], "trades": [], "buildings": ["BLD1"]})
    )
    assert "BLD1 / B20: 2 order(s): A, B" in with_building


def test_a_referenced_building_that_is_not_on_the_site_is_named_as_such(inst):
    text = user_prompt(
        inst, micro_item(referenced={"order_ids": [], "trades": [], "buildings": ["TOWER9"]})
    )
    assert "TOWER9: not on this site" in text


def test_work_already_under_way_is_named_only_when_the_episode_has_a_frozen_set(inst):
    plain = user_prompt(inst, micro_item())
    assert "already under way" not in plain
    frozen = user_prompt(
        inst, micro_item(episode={"frozen_seed": ["B", "A"], "rule": "atc", "seed": 0,
                                  "t_bh": 0.0})
    )
    assert "Work already under way, pinned to its current slot: A, B" in frozen


def test_the_instruction_is_carried_verbatim_and_last(inst):
    item = micro_item(instruction="Move W1 back two days, the lift is out.")
    text = user_prompt(inst, item)
    assert "INSTRUCTION\nMove W1 back two days, the lift is out." in text
    assert text.rstrip().endswith("Reply with the json object only.")


def test_the_decision_instant_is_stated(inst):
    text = user_prompt(inst, micro_item())
    assert "decision time 0.00 business hours" in text


# --------------------------------------------------------------------------- #
# against the real suite                                                       #
# --------------------------------------------------------------------------- #
def test_referenced_orders_reach_the_prompt_on_real_suite_items(suite, loader):
    sample = [r for r in suite if r["primary_class"] in ("V3", "V4")][:40]
    sample += [r for r in suite if len(r["referenced"]["order_ids"]) > 20][:5]
    assert sample
    for item in sample:
        instance = loader(item)
        present = {w["id"] for w in instance["work_orders"]}
        text = user_prompt(instance, item)
        for oid in item["referenced"]["order_ids"]:
            if oid in present:
                assert "\n  {:<10s}".format(oid) in text, (item["item_id"], oid)


def test_real_prompts_stay_token_lean(suite, loader):
    sample = [r for r in suite if r["primary_class"] in ("V3", "V4")][:60]
    sizes = []
    for item in sample:
        messages = build_messages(loader(item), item)
        sizes.append(sum(len(m["content"]) for m in messages))
    sizes.sort()
    median = sizes[len(sizes) // 2]
    # ~3.6 chars per token: a 10,800-character prompt is about 3k tokens.
    assert median < 10800, median


def test_the_prompt_module_stands_alone_so_generation_needs_no_solver_stack():
    """Phase A imports this file directly in the vLLM environment."""
    source = Path(prompts.__file__).read_text()
    assert "import l1adapter" not in source
    assert "from l1adapter" not in source
    assert "from ." not in source and "from l1guard" not in source
