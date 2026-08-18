#!/usr/bin/env python
"""E3 trajectory runner: SINGLE and MULTI, at matched all-token budgets.

E3 asks one question (decisions.md, 2026-08-12, "E3 DESIGN FREEZE"): at matched
all-token budgets, with the deterministic guard held constant OUTSIDE both
architectures, does the multi-agent layer add anything over one tool-equipped
model?  This script produces the evidence, and nothing else: it runs each
pipeline once per ``(arm, budget level, pipeline, repeat, item)`` and logs every
call.  The guard variants (MULTI-UG, MULTI-G, SINGLE+G) are replayed offline
from that log by ``scripts/e3_replay.py``, exactly as E1's three guard arms are
replayed from one generation log.

The two pipelines
-----------------
``SINGLE``
    One model behind one prompt.  It gets a uniform JSON action loop over
    exactly two deterministic tools, ``get_state(query)`` and
    ``preview_dispatch(op_list)``, for at most two rounds, and then emits a
    final operations list on the frozen E1 schema.
``MULTI``
    A MASC-style observe -> select solver/rule -> plan -> execute pipeline
    reimplemented for the work-order environment: ObsAgent (situation summary),
    SchedAgent (ReAct-style strategy selection, may call the same two tools for
    at most two rounds), PlanAgent (operations list), CtrlAgent (LLM-side
    self-check, emits the list that should actually be executed).  There is no
    deterministic checker inside the pipeline; that absence is the point, and it
    is why the guard sits outside both architectures.  Never described as
    "evaluating MASC": the architectural class is what is under test.

Both architectures get exactly the same two tools, implemented here as
deterministic functions over the Phase 1 adapter and injected as **text**.  No
vendor-native tool API is used anywhere, so a difference between two arms is a
difference between the arms.

The budget governor
-------------------
One counter per trajectory: the sum over EVERY call (pipeline stages, tool
rounds, revision tails) of full ``prompt_tokens + completion_tokens``,
cache-status blind, because caching is a billing optimisation and not a resource
discount.  Before each call the runner projects that call's prompt from its
characters and the arm's measured chars-per-token; if the projected minimum
(prompt + 1 token) would pass the ceiling, the call is refused and the arm must
finalise from its current best proposal or refer, with ``budget_exhausted``
flagged.  Otherwise the completion is clipped with ``max_tokens = remaining``.
The projection is an estimate; the accounting is the provider's own reported
usage, and a provider that reports nothing is charged the estimate rather than
zero.

Enforcement
-----------
One enforcement mode per arm (the enforcement axis lives in E1).  Within a
trajectory the split is by stage: every stage that emits an operations list
(SINGLE's final, PlanAgent, CtrlAgent, and any revision) is constrained by the
arm's own mechanism (xgrammar locally, ``output_config`` on the Anthropic wire,
strict ``response_format`` on the OpenAI wire, JSON-object mode on DeepSeek),
and carries the byte-identical frozen E1 system prompt; the observe, select and
tool-loop stages are unconstrained free text under a short E3 system prompt.

Prompt caching.  Every call's user message is the frozen ``l1-prompt-1.0.0``
state block followed by the stage block, split at E1's own cache boundary and
passed as the ``(stable_prefix, tail)`` pair.  All calls of one item share that
prefix, so the trajectories of an item are run back to back and the provider
writes it once.

Two deviations from the build brief, both reported to the orchestrator
----------------------------------------------------------------------
1. The local arms drive a **vLLM server** (the ``vllm`` backend of
   ``l1guard.models``), not the offline engine.  The offline engine lives in
   conda env ``l1``, which has no ``pandas``, so neither ``preview_dispatch``
   nor the in-loop guard can run there; E1 could split generation from
   evaluation across the two environments, and E3 cannot, because the tools and
   the guard are inside the loop.  Start the server in env ``l1`` and run this
   script in env ``fjsp``; the runner reads ``/server_info`` back and refuses
   unless the engine resolved ``xgrammar``.
2. ``SINGLE-UG`` is emitted by the replay alongside the freeze's three
   configurations.  It is the same truncation of the same log that MULTI-UG is,
   costs nothing, and completes the 2x2; it is labelled as an addition.

Run::

    conda run -n fjsp python scripts/e3_scaffold.py --arm sonnet --dry-run
    conda run -n fjsp python scripts/e3_scaffold.py --arm sonnet --mock --limit 10
    conda run -n fjsp python scripts/e3_scaffold.py --arm sonnet --calibrate
    conda run -n fjsp python scripts/e3_scaffold.py --arm sonnet \\
        --budget-tight 6000 --budget-loose 24000          # paid

``--mock`` swaps in an offline transport that answers both wire shapes and
walks five scripted scenarios (happy path, tool use, blocked then revised,
budget exhaustion mid-pipeline, refusal); no network, no key, no cost.
"""

from __future__ import annotations

import os

# Thread caps before any numeric import: a tool call and a guard call both
# dispatch a whole instance, and every numerical runtime sizes its pool from the
# machine's core count rather than from this process's share of it (global
# CLAUDE.md, "Running experiments").
for _var in (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ.setdefault(_var, "1")

import argparse  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import re  # noqa: E402
import statistics  # noqa: E402
import sys  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402
from pathlib import Path  # noqa: E402

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))  # scripts/: suite_gate, grid_e1_hosted, e1_evaluate
sys.path.insert(0, str(_HERE.parent))  # code/: l1guard, l1adapter

import e1_evaluate as e1e  # noqa: E402  (the E1 guard configurations, verbatim)
import e3_sample  # noqa: E402  (the frozen slice)
import grid_e1_hosted as e1h  # noqa: E402  (arm table, prices, cost formula, split)
import suite_gate as sg  # noqa: E402  (hash asserts, suite, instances, prompts)
from _envfile import load_env  # noqa: E402
from l1adapter import apply as apply_mod  # noqa: E402
from l1adapter import dispatch as dispatch_mod  # noqa: E402
from l1adapter import evaluate as evaluate_mod  # noqa: E402
from l1adapter import ops as ops_mod  # noqa: E402
from l1adapter.errors import AdapterError, SchemaViolation  # noqa: E402
from l1guard.logging import OUTCOME_ERROR, OUTCOME_OK, OUTCOME_REFUSAL  # noqa: E402
from l1guard.models import (  # noqa: E402
    BACKENDS,
    ENF_NONE,
    M_CONSTRAINED,
    M_FREE,
    WIRE_ANTHROPIC,
    ChatClient,
    assert_xgrammar_backend,
)
from l1guard.replay import InstanceCache  # noqa: E402

PROMPTS = sg.load_prompts_module()
SYSTEM_OPS = PROMPTS.SYSTEM_PROMPT  # byte-identical to E1's; used by every ops stage
PROMPT_VERSION = PROMPTS.PROMPT_VERSION
E3_PROMPT_VERSION = "l1-e3-prompt-1.0.0"
SCAFFOLD_VERSION = "l1-e3-scaffold-1"

TOP_K = 10
MAX_TOOL_ROUNDS = 2
MAX_REVISIONS = 1
MAX_TOKENS = 1024  # per call ceiling; the governor clips below it

PIPELINE_SINGLE = "SINGLE"
PIPELINE_MULTI = "MULTI"
PIPELINES = (PIPELINE_SINGLE, PIPELINE_MULTI)

BUDGET_TIGHT = "tight"
BUDGET_LOOSE = "loose"
BUDGET_CAL = "cal"

#: Stage -> kind.  ``ops`` stages emit an operations list on the frozen schema
#: and are constrained; ``reason`` stages are free text and are not.
KIND_REASON = "reason"
KIND_OPS = "ops"
STAGE_KINDS = {
    "single_act": KIND_REASON,
    "single_final": KIND_OPS,
    "multi_obs": KIND_REASON,
    "multi_sched": KIND_REASON,
    "multi_plan": KIND_OPS,
    "multi_ctrl": KIND_OPS,
    "revision": KIND_OPS,
}

TOOL_GET_STATE = "get_state"
TOOL_PREVIEW = "preview_dispatch"
TOOL_NONE = "none"
TOOLS = (TOOL_GET_STATE, TOOL_PREVIEW, TOOL_NONE)

#: Why a stage produced nothing usable.  All four are recorded on the trajectory
#: row, so a forced finalisation always says what forced it.
FORCE_BUDGET = "budget_exhausted"
FORCE_ERROR = "call_error"
FORCE_EMPTY = "empty_completion"
FORCE_REFUSAL = "provider_refusal"

#: The launch-gate envelope (the freeze).  Anthropic is a joint cap over both
#: Claude arms, so the gate prints the pair whenever one of them is selected.
ENVELOPE_USD = {"anthropic": 45.0, "openai": 8.0, "deepseek": 8.0, "vllm": 0.0}


# --------------------------------------------------------------------------- #
# The arm table: E1's prices and token model, E3's grid                        #
# --------------------------------------------------------------------------- #
#: The two local arms, in E1's own ``Arm`` shape so the projection, the cost
#: formula and the token model are literally one implementation.  Prices are
#: zero (electricity), and ``chars_per_token`` is measured on the E1 local logs
#: (2,000 M_constrained prompts against their reported prompt tokens).
LOCAL_ARMS = {
    "qwen14b": e1h.Arm(
        arm="qwen14b",
        backend="vllm",
        model=sg.MODEL_PATH,
        thinking=((None, {}),),
        prices=(("local (electricity only)",
                 {"in": 0.0, "cache_read": 0.0, "cache_write": None, "out": 0.0}),),
        price_date="-",
        price_source="local weights on the RTX PRO 5000; no API price",
        chars_per_token=2.585,
        schema_tokens=0,
        out_tokens={None: 37},
        pilot_note="results/grid_e1_local (E1 local arm: 2.585 chars per token, "
                   "median 37 completion tokens per M_constrained call)",
        modes=(M_CONSTRAINED,),
    ),
    "qwen27b": e1h.Arm(
        arm="qwen27b",
        backend="vllm",
        model="/home/ziheng/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B-FP8/"
              "snapshots/e89b16ebf1988b3d6befa7de50abc2d76f26eb09",
        thinking=((None, {}),),
        prices=(("local (electricity only)",
                 {"in": 0.0, "cache_read": 0.0, "cache_write": None, "out": 0.0}),),
        price_date="-",
        price_source="local FP8 weights; no API price",
        chars_per_token=2.545,
        schema_tokens=0,
        out_tokens={None: 55},
        pilot_note="results/grid_e1_local_27b (2.545 chars per token, median 55 "
                   "completion tokens per M_constrained call)",
        modes=(M_CONSTRAINED,),
    ),
}


@dataclass(frozen=True)
class E3Arm:
    """One E3 arm: an E1 arm record plus the grid the freeze gives it.

    ``thinking`` is the single label this arm runs in E3 (the thinking axis was
    measured in E1 and E3 does not adjudicate it), ``mode`` is its single
    enforcement mode, and ``repeats`` is the freeze's repeat count.
    """

    arm: str
    e1: object
    mode: str
    thinking: object
    thinking_body: dict
    repeats: int
    note: str

    @property
    def backend(self) -> str:
        return self.e1.backend

    @property
    def model(self) -> str:
        return self.e1.model

    @property
    def chars_per_token(self) -> float:
        return self.e1.chars_per_token


def _e1_arm(key: str):
    return LOCAL_ARMS[key] if key in LOCAL_ARMS else e1h.ARMS[key]


ARMS: dict = {
    "qwen14b": E3Arm(
        arm="qwen14b", e1=LOCAL_ARMS["qwen14b"], mode=M_CONSTRAINED,
        # E1's offline template call passed enable_thinking=False; on the
        # server wire the same convention travels as chat_template_kwargs,
        # which also keeps xgrammar active (it is disabled inside reasoning
        # content unless the server opts in).
        thinking=None,
        thinking_body={"chat_template_kwargs": {"enable_thinking": False}},
        repeats=2,
        note="the clean enforcement arm: xgrammar over a local vLLM server, "
             "temperature 0; 2 repeats measure engine nondeterminism",
    ),
    "qwen27b": E3Arm(
        arm="qwen27b", e1=LOCAL_ARMS["qwen27b"], mode=M_CONSTRAINED,
        thinking=None,
        thinking_body={"chat_template_kwargs": {"enable_thinking": False}},
        repeats=1,
        note="optional breadth (quantized; carries no capability claim); 1 repeat, "
             "run only if GPU time allows",
    ),
    "deepseek": E3Arm(
        arm="deepseek", e1=e1h.ARMS["deepseek"], mode=M_CONSTRAINED,
        thinking="non_think", thinking_body={"thinking": {"type": "disabled"}}, repeats=1,
        note="prompted-JSON (JSON-object mode), thinking disabled",
    ),
    "openai": E3Arm(
        arm="openai", e1=e1h.ARMS["openai"], mode=M_CONSTRAINED,
        thinking=None, thinking_body={}, repeats=1,
        note="server-side strict schema; reasoning effort omitted = the snapshot "
             "default, as in E1",
    ),
    "sonnet": E3Arm(
        arm="sonnet", e1=e1h.ARMS["sonnet"], mode=M_CONSTRAINED,
        thinking="disabled", thinking_body={"thinking": {"type": "disabled"}}, repeats=1,
        note="server-side strict schema, thinking disabled",
    ),
    "opus": E3Arm(
        arm="opus", e1=e1h.ARMS["opus"], mode=M_CONSTRAINED,
        thinking="disabled", thinking_body={"thinking": {"type": "disabled"}}, repeats=1,
        note="the capability gradient's top rung, thinking disabled; default-thinking "
             "E3 is not run (that axis was measured in E1)",
    ),
}

#: Both Claude arms share one cap, so the gate needs to name them together.
ANTHROPIC_ARMS = tuple(sorted(k for k, a in ARMS.items() if a.backend == "anthropic"))


# --------------------------------------------------------------------------- #
# The E3 system prompt for the free-text stages                                #
# --------------------------------------------------------------------------- #
SYSTEM_REASON = """\
You are the scheduling assistant of a facility-management team, working through one \
supervisor instruction in steps. Each step tells you exactly what to produce; produce \
that and nothing else, with no preamble and no closing remark. Use only the work order \
ids, building ids and trade codes that appear in the state you are shown, and never \
invent one. You are reading the same site state at every step, so do not repeat it back."""


# --------------------------------------------------------------------------- #
# Stage blocks                                                                 #
# --------------------------------------------------------------------------- #
RULE = "-" * 78

_TOOL_CONTRACT = """\
You may call a deterministic tool before you answer. Two tools exist, and they are \
the only ones:

  {{"tool": "get_state", "query": "<work order ids, trade codes or building ids you \
want the recorded state of>"}}
  {{"tool": "preview_dispatch", "operations": [ <operations, exactly as in the output \
contract> ]}}
      applies those operations to today's board, re-dispatches it, and reports the \
resulting weighted tardiness beside the board's current one.
  {{"tool": "none"}}
      you need no tool.

You have {left} tool call(s) left of {total}.
Reply with one json object and nothing else."""


def _transcript(rounds: list) -> str:
    """The tool rounds so far, as text; this is what makes a tool result visible."""
    if not rounds:
        return ""
    parts = ["", "TOOL ROUNDS SO FAR"]
    for i, entry in enumerate(rounds, 1):
        parts.append("")
        parts.append("({}) you called: {}".format(i, entry["call_text"]))
        parts.append("    it returned:")
        parts.extend("      " + line for line in entry["result"].splitlines())
    return "\n".join(parts)


def block_single_act(rounds: list, left: int, total: int) -> str:
    return "\n".join([
        RULE,
        "STEP 1 OF 2 OF THE SINGLE-MODEL PIPELINE: INFORMATION",
        "",
        _TOOL_CONTRACT.format(left=left, total=total),
        _transcript(rounds),
    ])


def block_single_final(rounds: list) -> str:
    return "\n".join([
        RULE,
        "STEP 2 OF 2 OF THE SINGLE-MODEL PIPELINE: THE ANSWER",
        _transcript(rounds),
        "",
        "Give the operations list for the instruction above, as one json object on the",
        "output contract stated at the top. Return an empty list if the instruction",
        "names no safe and unambiguous action you can express.",
    ])


def block_multi_obs() -> str:
    return "\n".join([
        RULE,
        "STEP 1 OF 4, OBSERVE (ObsAgent)",
        "",
        "Summarise the situation this instruction lands in, in at most six short lines:",
        "which work orders and trades it touches, how loaded those trades are, what is",
        "due soonest, and anything in the state that would make the instruction hard or",
        "unsafe to carry out. Plain text. No operations, no json.",
    ])


def block_multi_sched(observation: str, rounds: list, left: int, total: int) -> str:
    return "\n".join([
        RULE,
        "STEP 2 OF 4, SELECT THE STRATEGY (SchedAgent)",
        "",
        "The observe step reported:",
        observation.strip() or "(nothing)",
        "",
        "Decide how today's board should be adjusted for this instruction: which orders",
        "to touch, with which of the seven operations, and why. You may call a tool",
        "first, or state the strategy now.",
        "",
        _TOOL_CONTRACT.format(left=left, total=total),
        "",
        "To state the strategy instead, reply with exactly:",
        '  {"strategy": "<one or two sentences>"}',
        _transcript(rounds),
    ])


def block_multi_plan(observation: str, strategy: str, rounds: list) -> str:
    return "\n".join([
        RULE,
        "STEP 3 OF 4, PLAN (PlanAgent)",
        "",
        "The observe step reported:",
        observation.strip() or "(nothing)",
        "",
        "The select step chose:",
        strategy.strip() or "(nothing)",
        _transcript(rounds),
        "",
        "Write the operations list that carries out that strategy for the instruction",
        "above, as one json object on the output contract stated at the top. Return an",
        "empty list if the instruction names no safe and unambiguous action.",
    ])


def block_multi_ctrl(proposal: str) -> str:
    return "\n".join([
        RULE,
        "STEP 4 OF 4, EXECUTE AND SELF-CHECK (CtrlAgent)",
        "",
        "The plan step proposed:",
        proposal.strip() or "(nothing)",
        "",
        "Check it yourself against the instruction and the state above: are the ids real",
        "and on this site, do the operations say what the supervisor asked for, and is",
        "anything missing or extra? Then output the operations list that should actually",
        "be executed, as one json object on the output contract stated at the top.",
        "Repeat the proposal unchanged if it is already right, and return an empty list",
        "if no safe and unambiguous action exists.",
    ])


def block_revision(proposal: str, verdict) -> str:
    lines = [
        RULE,
        "THE DETERMINISTIC GUARD REFUSED THIS PROPOSAL",
        "",
        "You proposed:",
        proposal.strip() or "(nothing)",
        "",
        "The guard's verdict: {}".format(verdict["terminal"]),
    ]
    for finding in verdict["blocking_findings"]:
        lines.append("  - {}: {}".format(finding["code"], finding["message"]))
    if verdict.get("gap") is not None:
        lines.append(
            "  certified gap {:.4f} against a tolerance of {:.4f}".format(
                verdict["gap"], verdict["tau"])
        )
    lines += [
        "",
        "Emit a corrected operations list as one json object on the output contract",
        "stated at the top, or an empty list if no safe and unambiguous action exists.",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Prompt assembly: the frozen state block, then the stage block                #
# --------------------------------------------------------------------------- #
STATE_STAGE_SEPARATOR = "\n\n"


@dataclass
class Prepared:
    """One suite item, rendered once: the frozen state block and its cache prefix."""

    item: dict
    instance_path: str
    state: str
    split_at: str


def prepare(items: list, instances, top_k: int) -> dict:
    """Render every item's frozen state block; fatal on any mismatch.

    E1's own boundary check is run for the record (it proves the prompt module
    is the one E1 used), but E3's cache boundary is the END of the state block
    rather than E1's mid-block one.  The reason is what the prefix is shared
    BETWEEN: in E1 many items share one instance, so the boundary sits before
    the per-item order table; in E3 the trajectories of ONE item share
    everything the item shows, so the whole state block is stable and only the
    stage block varies.
    """
    out = {}
    for item in items:
        state = PROMPTS.user_prompt(instances.get(item), item, top_k)
        prefix, tail, which = e1h.split_user_prompt(state)
        if prefix + tail != state:
            raise SystemExit(
                "REFUSING TO RUN: the cache split is not byte-identical for {}".format(
                    item["item_id"])
            )
        out[item["item_id"]] = Prepared(
            item=item,
            instance_path=instances.path(item),
            state=state,
            split_at=which,
        )
    return out


def user_message(prep: Prepared, stage_block: str) -> tuple:
    """The ``(stable_prefix, tail)`` pair for one call of one item."""
    return (prep.state, STATE_STAGE_SEPARATOR + stage_block)


def system_for(stage: str) -> str:
    return SYSTEM_OPS if STAGE_KINDS[stage] == KIND_OPS else SYSTEM_REASON


def mode_for(stage: str, arm: E3Arm) -> str:
    return arm.mode if STAGE_KINDS[stage] == KIND_OPS else M_FREE


# --------------------------------------------------------------------------- #
# The two deterministic tools, and the guard, over the Phase 1 adapter          #
# --------------------------------------------------------------------------- #
class Services:
    """Everything deterministic a trajectory needs: the two tools and the guard.

    One instance is shared by every worker.  ``InstanceCache`` loads each
    instance file and each baseline schedule once; the lock protects those two
    dicts, not the computation, which works on the deep copy
    ``apply_operations`` makes.
    """

    def __init__(self, top_k: int = TOP_K, guard_config=None):
        self.cache = InstanceCache()
        self.top_k = int(top_k)
        self.guard_config = guard_config or e1e.guard_configs()["G_CERT"]
        self._lock = threading.Lock()
        self.n_get_state = 0
        self.n_preview = 0
        self.n_guard = 0

    # -- shared state -------------------------------------------------------- #
    def instance(self, path: str) -> dict:
        with self._lock:
            return self.cache.instance(path)

    def baseline(self, path: str, rule: str, seed: int) -> dict:
        with self._lock:
            return self.cache.baseline(path, rule, seed)

    # -- tool 1 -------------------------------------------------------------- #
    def get_state(self, prep: Prepared, query: str) -> str:
        """The recorded state of whatever the query names.  Never raises."""
        with self._lock:
            self.n_get_state += 1
        instance = self.instance(prep.instance_path)
        text = str(query or "")
        by_id = {w["id"]: w for w in instance["work_orders"]}
        trades = sorted({w["trade"] for w in instance["work_orders"]})
        buildings = sorted(
            {w["building"] for w in instance["work_orders"] if w["building"] is not None}
        )
        tokens = set(re.findall(r"[A-Za-z0-9_\-]+", text))
        upper = {t.upper() for t in tokens}

        named_orders = [o for o in sorted(by_id) if o.upper() in upper]
        named_trades = [t for t in trades if t.upper() in upper]
        named_buildings = [b for b in buildings if b.upper() in upper]
        unknown = sorted(
            t for t in tokens
            if re.fullmatch(r"[A-Za-z]{1,3}\d+", t)
            and t.upper() not in {o.upper() for o in by_id}
            and t.upper() not in {b.upper() for b in buildings}
            and t.upper() not in {x.upper() for x in trades}
        )

        parts = []
        if named_orders:
            parts += ["Work orders:", PROMPTS._ORDER_HEADER]
            parts += [PROMPTS._order_row(by_id[o]) for o in named_orders]
        for trade in named_trades:
            rest = [w for w in instance["work_orders"] if w["trade"] == trade]
            rest = PROMPTS._sorted_orders(rest)[: self.top_k]
            parts += [
                "",
                "Trade {}, {} earliest-due orders on the board:".format(trade, len(rest)),
                PROMPTS._ORDER_HEADER,
            ]
            parts += [PROMPTS._order_row(w) for w in rest]
        for building in named_buildings:
            members = [w for w in instance["work_orders"] if w["building"] == building]
            per_trade: dict = {}
            for wo in members:
                per_trade.setdefault(wo["trade"], []).append(wo["id"])
            parts.append("")
            parts.append("Building {}:".format(building))
            for trade in sorted(per_trade):
                parts.append(
                    "  {} / {}: {} order(s): {}".format(
                        building, trade, len(per_trade[trade]), ", ".join(sorted(per_trade[trade]))
                    )
                )
        if unknown:
            parts.append("Not on this site: {}".format(", ".join(unknown)))
        if not parts:
            parts = [
                "The query named nothing on this site. Crews and work by trade:",
                PROMPTS._trade_table(instance),
            ]
        return "\n".join(parts)

    # -- tool 2 -------------------------------------------------------------- #
    def preview_dispatch(self, prep: Prepared, operations) -> str:
        """Apply, re-dispatch, and report the objective.  Never raises.

        The rule and the seed are the guard's own, so the simulator dispatches
        exactly what the guard will score: a preview that ran under a different
        seed would mislead the arm about its own proposal.  The certificate is
        deliberately absent: this is a simulator, not a guard, and the guard
        stays outside both architectures.
        """
        with self._lock:
            self.n_preview += 1
        item = prep.item
        instance = self.instance(prep.instance_path)
        rule = item["episode"]["rule"] or self.guard_config.rule
        seed = int(self.guard_config.seed)
        frozen_seed = tuple(item["episode"]["frozen_seed"] or ())
        if not isinstance(operations, list):
            return "PREVIEW REFUSED: 'operations' must be a json array of operations."
        try:
            typed = ops_mod.parse_operations({"operations": operations})
        except SchemaViolation as exc:
            return "PREVIEW REFUSED: {}".format(exc)

        baseline = None
        raw_blob = json.dumps(operations)
        if frozen_seed or "freeze" in raw_blob:
            baseline = self.baseline(prep.instance_path, rule, seed)
        try:
            adjusted = apply_mod.apply_operations(
                instance, typed, frozen_seed=frozen_seed, baseline_schedule=baseline
            )
            schedule = dispatch_mod.dispatch_adjusted(adjusted, rule=rule, seed=seed)
        except AdapterError as exc:
            return "PREVIEW REFUSED: the operations cannot be executed together: {}".format(exc)
        except Exception as exc:  # noqa: BLE001 - a simulator fault is data, not a crash
            return "PREVIEW FAILED: {}: {}".format(type(exc).__name__, exc)

        base_schedule = self.baseline(prep.instance_path, rule, seed)
        now = evaluate_mod.wwt(adjusted.instance, schedule)
        before = evaluate_mod.wwt(instance, base_schedule)
        rows = [
            r for r in evaluate_mod.tardiness_table(adjusted.instance, schedule)
            if (r["weighted_tardiness_bh"] or 0.0) > 0.0
        ]
        worst = ", ".join(
            "{} ({:.1f})".format(r["id"], r["weighted_tardiness_bh"]) for r in rows[:3]
        ) or "none"
        lines = [
            "PREVIEW of {} operation(s) on today's board:".format(len(typed)),
            "  weighted tardiness with your operations : {:.2f} business hours".format(now),
            "  weighted tardiness as the board stands   : {:.2f} business hours".format(before),
            "  change                                   : {:+.2f} (lower is better)".format(
                now - before),
            "  orders finishing late                    : {} of {}".format(
                len(rows), len(adjusted.instance["work_orders"])),
            "  worst three                              : {}".format(worst),
        ]
        for note in adjusted.notes[:3]:
            lines.append("  note: {}".format(note))
        return "\n".join(lines)

    # -- the guard, for the revision tail ------------------------------------ #
    def guard(self, prep: Prepared, raw_output: str) -> dict:
        """G_CERT on one raw proposal, through E1's own configuration."""
        with self._lock:
            self.n_guard += 1
        from l1guard import evaluate_proposal

        item = prep.item
        cfg = self.guard_config
        rule = item["episode"]["rule"]
        if rule != cfg.rule:
            cfg = cfg.with_(rule=rule)
        instance = self.instance(prep.instance_path)
        baseline = None
        if item["episode"]["frozen_seed"] or "freeze" in (raw_output or ""):
            baseline = self.baseline(prep.instance_path, cfg.rule, cfg.seed)
        verdict = evaluate_proposal(
            instance,
            raw_output if raw_output is not None else "",
            cfg,
            baseline_schedule=baseline,
            frozen_seed=tuple(item["episode"]["frozen_seed"] or ()),
        )
        return summarise_guard(verdict, cfg)


def summarise_guard(verdict, cfg) -> dict:
    """The guard fields the log keeps: enough to rebuild the revision prompt."""
    cert = verdict.certificate
    return {
        "terminal": verdict.terminal,
        "stage_reached": verdict.stage_reached,
        "blocked": verdict.blocked,
        "accepted": verdict.accepted,
        "fingerprint": verdict.digest(),
        "blocking_findings": [
            {"code": f.code, "stage": f.stage, "message": f.message}
            for f in verdict.findings if f.blocking
        ],
        "infra": any(f.severity == "infra" for f in verdict.findings),
        "gap": None if cert is None else cert.gap,
        "tau": cfg.tau,
        "n_ops": None if verdict.ops is None else len(verdict.ops),
        "config_name": cfg.name,
        "config_hash": cfg.config_hash,
    }


# --------------------------------------------------------------------------- #
# The budget governor                                                          #
# --------------------------------------------------------------------------- #
class Budget:
    """All-token accounting for one trajectory, and the ceiling it enforces.

    ``spent`` is the sum over every call of ``prompt_tokens + completion_tokens``
    as the provider reported them, cache-status blind.  When a provider reports
    no usage the estimate is charged instead, because an unreported call is
    still a call.
    """

    def __init__(self, budget_tokens, chars_per_token: float, max_tokens: int = MAX_TOKENS):
        self.budget = None if not budget_tokens else int(budget_tokens)
        self.cpt = float(chars_per_token)
        self.max_tokens = int(max_tokens)
        self.spent = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.calls = 0
        self.estimated_calls = 0
        self.exhausted = False

    def estimate(self, chars: int) -> int:
        """Pre-call projection of a prompt, from characters and the arm's own rate."""
        return int(math.ceil(max(1, int(chars)) / self.cpt))

    def remaining(self):
        return None if self.budget is None else max(0, self.budget - self.spent)

    def allow(self, prompt_chars: int):
        """``(ok, max_tokens)`` for the next call; ``ok=False`` forces finalisation."""
        need = self.estimate(prompt_chars)
        if self.budget is None:
            return True, self.max_tokens
        if self.spent + need + 1 > self.budget:
            self.exhausted = True
            return False, 0
        room = self.budget - self.spent - need
        return True, max(1, min(self.max_tokens, room))

    def charge(self, usage: dict, estimated_prompt: int) -> dict:
        """Charge one completed call; returns what was charged, for the log."""
        usage = usage or {}
        prompt = usage.get("prompt_tokens")
        completion = usage.get("completion_tokens")
        estimated = prompt is None
        if prompt is None:
            prompt = estimated_prompt
        if completion is None:
            completion = 0
        prompt, completion = int(prompt), int(completion)
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.spent += prompt + completion
        self.calls += 1
        if estimated:
            self.estimated_calls += 1
        if self.budget is not None and self.spent >= self.budget:
            self.exhausted = True
        return {"prompt_tokens": prompt, "completion_tokens": completion,
                "charged": prompt + completion, "from_estimate": estimated}


# --------------------------------------------------------------------------- #
# Parsing what a stage returned                                                #
# --------------------------------------------------------------------------- #
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text):
    """The first json object in a completion, fences and prose tolerated.

    Only the free-text stages go through here: an operations list is parsed by
    the guard, on the raw output, exactly as in E1.  This is prompt plumbing,
    not a measurement, so it is tolerant on purpose and every failure is logged.
    """
    if not text:
        return None, "empty completion"
    blob = text.strip()
    match = _FENCE.search(blob)
    if match:
        blob = match.group(1).strip()
    try:
        return json.loads(blob), None
    except (json.JSONDecodeError, TypeError):
        pass
    start = blob.find("{")
    while start >= 0:
        depth, in_str, escape = 0, False, False
        for i in range(start, len(blob)):
            ch = blob[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(blob[start:i + 1]), None
                    except json.JSONDecodeError:
                        break
        start = blob.find("{", start + 1)
    return None, "no json object in the completion"


def parse_action(text) -> dict:
    """``{"tool": ..., "query"/"operations": ...}`` or a strategy, from a completion."""
    obj, error = extract_json(text)
    if obj is None or not isinstance(obj, dict):
        return {"tool": TOOL_NONE, "parse_error": error or "not a json object"}
    if "strategy" in obj and "tool" not in obj:
        return {"tool": TOOL_NONE, "strategy": str(obj["strategy"])}
    tool = obj.get("tool")
    if tool == TOOL_GET_STATE:
        return {"tool": TOOL_GET_STATE, "query": str(obj.get("query", ""))}
    if tool == TOOL_PREVIEW:
        return {"tool": TOOL_PREVIEW, "operations": obj.get("operations")}
    if tool == TOOL_NONE:
        return {"tool": TOOL_NONE}
    if "operations" in obj:  # a model that answered early: treat it as a preview
        return {"tool": TOOL_PREVIEW, "operations": obj.get("operations")}
    return {"tool": TOOL_NONE, "parse_error": "unknown tool {!r}".format(tool)}


def n_ops(raw_output) -> int:
    """Operation count of a raw proposal, or -1 when it does not parse at all."""
    obj, _ = extract_json(raw_output)
    if isinstance(obj, dict) and isinstance(obj.get("operations"), list):
        return len(obj["operations"])
    return -1


# --------------------------------------------------------------------------- #
# One trajectory                                                               #
# --------------------------------------------------------------------------- #
@dataclass
class Trajectory:
    """The live state of one ``(arm, budget, pipeline, repeat, item)`` run."""

    arm: E3Arm
    prep: Prepared
    pipeline: str
    budget_level: str
    repeat: int
    run_uid: str
    budget: Budget
    services: Services
    client: object
    args: object
    calls: list = field(default_factory=list)
    tool_rounds: list = field(default_factory=list)
    stages: list = field(default_factory=list)
    forced: list = field(default_factory=list)
    best_proposal: str = None
    best_source: str = None
    first_final: dict = None
    guard_chain: list = field(default_factory=list)
    revisions: list = field(default_factory=list)
    error: str = None
    stopped: bool = False

    # -- one call ------------------------------------------------------------ #
    def call(self, stage: str, stage_block: str):
        """One LLM call, governed and logged.  ``None`` means the stage did not run.

        A refusal stops the whole trajectory rather than only that stage: the
        transcript only grows, so every later prompt is larger than the one just
        refused, and the arm's job from here is to finalise or refer.
        """
        if self.stopped:
            return None
        user = user_message(self.prep, stage_block)
        system = system_for(stage)
        prompt_chars = len(system) + len(user[0]) + len(user[1])
        ok, max_tokens = self.budget.allow(prompt_chars)
        estimated = self.budget.estimate(prompt_chars)
        if not ok:
            self.stopped = True
            self.forced.append({"stage": stage, "reason": FORCE_BUDGET,
                                "spent": self.budget.spent, "budget": self.budget.budget,
                                "projected_prompt": estimated})
            return None

        mode = mode_for(stage, self.arm)
        kwargs = {"max_tokens": max_tokens}
        if self.arm.thinking_body:
            kwargs["extra_body"] = dict(self.arm.thinking_body)
        started = time.perf_counter()
        try:
            resp = self.client.complete(system, user, mode=mode, **kwargs)
        except Exception as exc:  # noqa: BLE001 - one bad call must not kill the grid
            resp = e1h._FailedCall(self.arm.model,
                                   "{}: {}".format(type(exc).__name__, exc))
        latency_ms = (time.perf_counter() - started) * 1000.0
        charged = self.budget.charge(resp.usage, estimated)

        row = {
            "run_uid": self.run_uid,
            "call_index": len(self.calls),
            "stage": stage,
            "stage_kind": STAGE_KINDS[stage],
            "mode": mode,
            "enforcement": (BACKENDS[self.arm.backend].constrained
                            if mode == M_CONSTRAINED else ENF_NONE),
            "system": "frozen" if STAGE_KINDS[stage] == KIND_OPS else "e3_reason",
            "prompt_chars": prompt_chars,
            "prompt_hash": PROMPTS.prompt_fingerprint(
                [{"role": "system", "content": system},
                 {"role": "user", "content": user[0] + user[1]}]),
            "max_tokens_sent": max_tokens,
            "projected_prompt_tokens": estimated,
            "raw_output": resp.text,
            "finish_reason": resp.finish_reason,
            "outcome": resp.outcome,
            "api_error": resp.error,
            "latency_ms": latency_ms,
            "usage": resp.usage,
            "charged": charged,
            "tokens_after": self.budget.spent,
            "is_first_final": False,
            "tool_call": None,
            "tool_result": None,
        }
        self.calls.append(row)
        self.stages.append(stage)
        if resp.outcome == OUTCOME_ERROR:
            self.error = resp.error
            self.stopped = True
            self.forced.append({"stage": stage, "reason": FORCE_ERROR, "error": resp.error})
            return None
        if resp.outcome == OUTCOME_REFUSAL:
            # An explicit provider refusal: not a failure, and the trajectory
            # ends in a referral rather than in a proposal.
            self.forced.append({"stage": stage, "reason": FORCE_REFUSAL,
                                "detail": resp.error})
            return ""
        if not (resp.text or "").strip():
            self.forced.append({"stage": stage, "reason": FORCE_EMPTY})
            return ""
        return resp.text

    # -- one tool round ------------------------------------------------------ #
    def run_tool(self, action: dict) -> str:
        if action["tool"] == TOOL_GET_STATE:
            call_text = json.dumps({"tool": TOOL_GET_STATE, "query": action.get("query", "")})
            result = self.services.get_state(self.prep, action.get("query", ""))
        else:
            operations = action.get("operations")
            call_text = json.dumps({"tool": TOOL_PREVIEW, "operations": operations})
            result = self.services.preview_dispatch(self.prep, operations)
            if isinstance(operations, list) and not result.startswith("PREVIEW REFUSED"):
                self.best_proposal = json.dumps({"operations": operations})
                self.best_source = "preview_dispatch"
        entry = {"call_text": call_text, "result": result, "tool": action["tool"]}
        self.tool_rounds.append(entry)
        self.calls[-1]["tool_call"] = {k: v for k, v in action.items() if k != "operations"}
        self.calls[-1]["tool_call"]["operations"] = action.get("operations")
        self.calls[-1]["tool_result"] = result
        return result

    # -- the answer ---------------------------------------------------------- #
    def set_first_final(self, stage: str, raw: str, source: str) -> None:
        self.first_final = {
            "stage": stage,
            "source": source,
            "call_index": len(self.calls) - 1 if source == "call" else None,
            "raw_output": raw,
            "n_ops": n_ops(raw),
        }
        if source == "call":
            self.calls[-1]["is_first_final"] = True

    def finalise(self, stage: str, stage_block: str) -> None:
        """Run the answering stage; fall back to the best proposal, else refer."""
        text = self.call(stage, stage_block)
        if text:
            self.best_proposal = text
            self.best_source = stage
            self.set_first_final(stage, text, "call")
            return
        if self.best_proposal:
            self.set_first_final(stage, self.best_proposal,
                                 "forced_from:{}".format(self.best_source))
            return
        self.set_first_final(stage, json.dumps({"operations": []}), "forced_referral")


def run_single(traj: Trajectory) -> None:
    """SINGLE: at most two tool rounds through the uniform action loop, then answer."""
    total = traj.args.max_tool_rounds
    used = 0
    while used < total:
        text = traj.call("single_act", block_single_act(traj.tool_rounds, total - used, total))
        if text is None:
            break
        action = parse_action(text)
        if action["tool"] == TOOL_NONE:
            break
        traj.run_tool(action)
        used += 1
    traj.finalise("single_final", block_single_final(traj.tool_rounds))


def run_multi(traj: Trajectory) -> None:
    """MULTI: observe -> select -> plan -> execute, four roles, no checker inside."""
    observation = traj.call("multi_obs", block_multi_obs()) or ""

    total = traj.args.max_tool_rounds
    used = 0
    strategy = ""
    while True:
        text = traj.call(
            "multi_sched", block_multi_sched(observation, traj.tool_rounds, total - used, total)
        )
        if text is None:
            break
        action = parse_action(text)
        if action.get("strategy"):
            strategy = action["strategy"]
            break
        if action["tool"] == TOOL_NONE or used >= total:
            strategy = text.strip()
            break
        traj.run_tool(action)
        used += 1

    plan = traj.call(
        "multi_plan", block_multi_plan(observation, strategy, traj.tool_rounds)
    )
    if plan:
        traj.best_proposal = plan
        traj.best_source = "multi_plan"
    traj.finalise("multi_ctrl", block_multi_ctrl(plan or traj.best_proposal or ""))


PIPELINE_FUNCS = {PIPELINE_SINGLE: run_single, PIPELINE_MULTI: run_multi}


def guarded_tail(traj: Trajectory) -> None:
    """Guard the first final; on a block, feed the verdict back and let the arm revise.

    These revision calls are the only live calls beyond the pipeline, they are
    charged to the same trajectory budget, and they are what the guarded arms
    (SINGLE+G, MULTI-G) replay.  MULTI-UG is the same trajectory truncated at
    the first final, so no separate run exists for it.
    """
    raw = traj.first_final["raw_output"]
    verdict = traj.services.guard(traj.prep, raw)
    traj.guard_chain.append({"source": "first_final", **verdict})
    k = 0
    while verdict["blocked"] and k < traj.args.max_revisions:
        text = traj.call("revision", block_revision(raw, verdict))
        if not text:
            break
        raw = text
        verdict = traj.services.guard(traj.prep, raw)
        k += 1
        traj.revisions.append({
            "index": k,
            "call_index": len(traj.calls) - 1,
            "raw_output": raw,
            "n_ops": n_ops(raw),
        })
        traj.guard_chain.append({"source": "revision-{}".format(k), **verdict})


# --------------------------------------------------------------------------- #
# The log                                                                      #
# --------------------------------------------------------------------------- #
def traj_key(row: dict) -> tuple:
    return (row["arm"], row["budget_level"], row["pipeline"], int(row["repeat"]),
            row["item_id"])


def trajectory_row(traj: Trajectory, wall_s: float) -> dict:
    item = traj.prep.item
    return {
        "scaffold_version": SCAFFOLD_VERSION,
        "run_uid": traj.run_uid,
        "arm": traj.arm.arm,
        "model": traj.arm.model,
        "backend": traj.arm.backend,
        "mode": traj.arm.mode,
        "thinking": traj.arm.thinking,
        "pipeline": traj.pipeline,
        "budget_level": traj.budget_level,
        "budget_tokens": traj.budget.budget,
        "repeat": traj.repeat,
        "item_id": item["item_id"],
        "primary_class": item["primary_class"],
        "subclass": item["subclass"],
        "register": item["register"],
        "twin_id": item["twin_id"],
        "twin_role": item["twin_role"],
        "quality_visible_candidate": item.get("quality_visible_candidate"),
        "instance_id": item["instance"]["instance_id"],
        "instance_path": traj.prep.instance_path,
        "stratum": item["instance"]["stratum"],
        "rule": item["episode"]["rule"],
        "dispatch_seed": item["episode"]["seed"],
        "frozen_seed": list(item["episode"]["frozen_seed"]),
        "gold_ops": item["gold_ops"],
        "trap_ops": item["trap_ops"],
        "instruction": item["instruction"],
        "prompt_version": PROMPT_VERSION,
        "e3_prompt_version": E3_PROMPT_VERSION,
        "stages": list(traj.stages),
        "n_calls": len(traj.calls),
        "tool_rounds": [
            {"tool": e["tool"], "call": e["call_text"], "result_chars": len(e["result"])}
            for e in traj.tool_rounds
        ],
        "tokens": {
            "prompt": traj.budget.prompt_tokens,
            "completion": traj.budget.completion_tokens,
            "all": traj.budget.spent,
            "calls_charged_from_estimate": traj.budget.estimated_calls,
        },
        "budget_exhausted": bool(traj.budget.exhausted
                                 or any(f["reason"] == FORCE_BUDGET for f in traj.forced)),
        "forced": list(traj.forced),
        "first_final": traj.first_final,
        "guard_chain": traj.guard_chain,
        "revisions": traj.revisions,
        "outcome": OUTCOME_ERROR if traj.error else OUTCOME_OK,
        "error": traj.error,
        "wall_s": wall_s,
    }


def read_completed(path: Path, arm: E3Arm) -> tuple:
    """Keys whose LAST trajectory row is not an error, plus the row counts."""
    done: dict = {}
    rows = errors = broken = 0
    if not path.exists():
        return set(), rows, errors, broken
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                broken += 1  # a torn last line from a killed run
                continue
            if row.get("arm") != arm.arm or row.get("model") != arm.model:
                raise SystemExit(
                    "REFUSING TO RUN: {} already holds rows for arm {!r} model {!r}; "
                    "point --out at this arm's own directory".format(
                        path, row.get("arm"), row.get("model"))
                )
            if row.get("e3_prompt_version") != E3_PROMPT_VERSION:
                raise SystemExit(
                    "REFUSING TO RUN: {} holds rows for E3 prompt version {!r}, not "
                    "{!r}".format(path, row.get("e3_prompt_version"), E3_PROMPT_VERSION)
                )
            rows += 1
            if row.get("outcome") == OUTCOME_ERROR:
                errors += 1
            done[traj_key(row)] = row.get("outcome")
    return {k for k, v in done.items() if v != OUTCOME_ERROR}, rows, errors, broken


# --------------------------------------------------------------------------- #
# The plan                                                                     #
# --------------------------------------------------------------------------- #
def build_plan(arm: E3Arm, item_ids: list, levels: list, pipelines: list,
               repeats: int) -> list:
    """Every trajectory, grouped by item: ``[{"item_id": ..., "jobs": [...]}, ...]``.

    The group is the unit of work, and it is what makes the provider's prefix
    cache pay: every call of an item shares that item's state block, so the
    group runs on one worker, writes the prefix on its first call and reads it
    back on the rest, all inside one cache lifetime.  Spreading an item's
    trajectories over four workers would write the same prefix four times.
    """
    groups = []
    for item_id in item_ids:
        jobs = []
        for level, budget in levels:
            for pipeline in pipelines:
                for repeat in range(repeats):
                    jobs.append({"item_id": item_id, "budget_level": level,
                                 "budget_tokens": budget, "pipeline": pipeline,
                                 "repeat": repeat, "arm": arm.arm})
        groups.append({"item_id": item_id, "jobs": jobs})
    return groups


def remaining_groups(groups: list, done: set, arm: E3Arm, limit: int) -> list:
    """The first ``limit`` items of the slice, minus the trajectories already logged.

    ``limit`` caps ITEMS, not trajectories, and it is applied before the resume
    filter: a smoke run and its resume therefore work the same prefix of the same
    ordered plan, and re-running a finished smoke run does nothing.
    """
    out = []
    for group in (groups[:limit] if limit else groups):
        jobs = [j for j in group["jobs"]
                if (arm.arm, j["budget_level"], j["pipeline"], j["repeat"],
                    j["item_id"]) not in done]
        if jobs:
            out.append({"item_id": group["item_id"], "jobs": jobs})
    return out


def count_jobs(groups: list) -> int:
    return sum(len(g["jobs"]) for g in groups)


# --------------------------------------------------------------------------- #
# The mock transport: both wire shapes, five scripted scenarios, offline        #
# --------------------------------------------------------------------------- #
SCENARIOS = ("happy", "tools", "blocked", "budget", "refusal")


class MockTransport:
    """Answers a request the way a provider would, with no network and no key.

    It reads the request body, so the real request builders are exercised: the
    Anthropic two-block ``cache_control`` split, the OpenAI joined string, the
    enforcement field and the thinking field.  The stage is recognised from the
    prompt text, and the scenario is set per trajectory by the runner through a
    thread-local, because each trajectory runs start to finish on one worker.

    The five scenarios walk the paths that matter: a clean answer, a real tool
    round, a proposal the guard refuses followed by a revision, a completion
    long enough to exhaust a tight budget mid-pipeline, and a refusal (the
    empty operations list, which is the frozen prompt's own refusal signal).
    """

    APPROX_CHARS_PER_TOKEN = 4
    #: One row of the state block's order table.  The second column must start
    #: with a letter, which is what tells an order row (id, trade, class, ...)
    #: from a trade-table row (trade, technicians, orders, ...) whose second
    #: column is a count.
    ORDER_ROW = re.compile(r"^  (\S+)\s+([A-Za-z][A-Za-z0-9_]*)\s+\d+\s+\d", re.MULTILINE)

    def __init__(self, arm: E3Arm, fail_every: int = 0, long_chars: int = 12000):
        self.arm = arm
        self.fail_every = int(fail_every)
        self.long_chars = int(long_chars)
        self._local = threading.local()
        self._lock = threading.Lock()
        self._seen: set = set()
        self.calls = 0
        self.bodies: list = []
        self.by_stage: dict = {}

    # -- scenario, per trajectory -------------------------------------------- #
    def set_scenario(self, name: str, gold_ops=None) -> None:
        """The runner sets these before each trajectory; one worker, one thread."""
        self._local.scenario = name
        self._local.gold = list(gold_ops or [])

    @property
    def scenario(self) -> str:
        return getattr(self._local, "scenario", "happy")

    @property
    def gold(self) -> list:
        """The item's own labelled operations, as the suite gate's mock uses them.

        This is not a model: on the paths where a scenario is meant to succeed it
        emits the suite's ``gold_ops``, so a mock run measures the instrument and
        never stands in for a model's translation ability.
        """
        return getattr(self._local, "gold", None)

    def _tokens(self, text: str) -> int:
        return max(1, len(text) // self.APPROX_CHARS_PER_TOKEN)

    # -- what the prompt says the stage is ------------------------------------ #
    def _stage(self, user: str) -> str:
        if "THE DETERMINISTIC GUARD REFUSED" in user:
            return "revision"
        if "STEP 1 OF 2 OF THE SINGLE-MODEL PIPELINE" in user:
            return "single_act"
        if "STEP 2 OF 2 OF THE SINGLE-MODEL PIPELINE" in user:
            return "single_final"
        if "STEP 1 OF 4" in user:
            return "multi_obs"
        if "STEP 2 OF 4" in user:
            return "multi_sched"
        if "STEP 3 OF 4" in user:
            return "multi_plan"
        if "STEP 4 OF 4" in user:
            return "multi_ctrl"
        return "unknown"

    def _orders(self, user: str) -> list:
        return self.ORDER_ROW.findall(user)

    def _final(self, user: str, scenario: str) -> str:
        if scenario == "refusal":
            return json.dumps({"operations": []})
        if scenario == "blocked":
            return json.dumps({"operations": [
                {"op": "set_priority", "order_id": "W9999999", "priority_class": 1}]})
        if self.gold:
            return json.dumps({"operations": self.gold})
        # V1 and V5 items have no gold operations by construction (nothing valid
        # exists for them), so the scenario falls back to a proposal built from
        # the state: a mock must still exercise the applied path on those items.
        orders = self._orders(user)
        if not orders:
            return json.dumps({"operations": []})
        order_id, trade = orders[0]
        return json.dumps({"operations": [
            {"op": "set_priority", "order_id": order_id, "priority_class": 2},
            {"op": "pin_next", "order_id": order_id, "trade": trade},
        ]})

    def _text(self, user: str) -> str:
        stage = self._stage(user)
        scenario = self.scenario
        used = "TOOL ROUNDS SO FAR" in user
        with self._lock:
            self.by_stage[stage] = self.by_stage.get(stage, 0) + 1

        if stage == "revision":
            return self._final(user, "happy")
        if stage in ("single_act", "multi_sched"):
            if scenario == "tools" and not used:
                orders = self._orders(user)
                query = orders[0][0] if orders else "board"
                return json.dumps({"tool": TOOL_GET_STATE, "query": query})
            if scenario == "tools" and used and stage == "single_act":
                obj, _ = extract_json(self._final(user, "happy"))
                return json.dumps({"tool": TOOL_PREVIEW, "operations": obj["operations"]})
            if stage == "multi_sched":
                return json.dumps({"strategy": "raise the named order and pin it next"})
            return json.dumps({"tool": TOOL_NONE})
        if stage == "multi_obs":
            if scenario == "budget":
                return ("the board is loaded and the instruction touches one trade. "
                        * (self.long_chars // 62))
            return "One trade is loaded; the instruction names one order due soon."
        if stage == "unknown":
            return json.dumps({"operations": []})
        if scenario == "budget" and stage in ("single_act",):
            return json.dumps({"tool": TOOL_NONE})
        if scenario == "budget" and stage == "single_final":
            return self._final(user, "happy")
        return self._final(user, scenario)

    # -- the wire ------------------------------------------------------------- #
    def __call__(self, method, url, headers, body, timeout):
        payload = json.loads(body.decode("utf-8"))
        with self._lock:
            self.calls += 1
            index = self.calls
            self.bodies.append(payload)
        if self.fail_every and index % self.fail_every == 0:
            return 400, json.dumps(
                {"error": {"type": "invalid_request_error",
                           "message": "mock injected failure"}}).encode()

        anthropic = url.endswith("/v1/messages")
        if anthropic:
            blocks = payload["messages"][0]["content"]
            prefix = blocks[0]["text"]
            tail = "".join(b["text"] for b in blocks[1:])
            system = "".join(b["text"] for b in payload.get("system") or [])
            constrained = "output_config" in payload
        else:
            content = payload["messages"][1]["content"]
            at = content.find(e1h.CACHE_BOUNDARY)
            if at < 0:
                at = max(0, content.find(e1h.CACHE_BOUNDARY_FALLBACK))
            prefix, tail = content[:at], content[at:]
            system = payload["messages"][0]["content"]
            constrained = "response_format" in payload or "structured_outputs" in payload

        text = self._text(prefix + tail)
        max_tokens = payload.get("max_tokens") or payload.get("max_completion_tokens") or 1024
        out_tokens = min(self._tokens(text), int(max_tokens))

        with self._lock:
            key = (payload["model"], constrained, system, prefix)
            hit = key in self._seen
            self._seen.add(key)
        cached = self._tokens(system) + self._tokens(prefix)
        uncached = self._tokens(tail)

        if anthropic:
            return 200, json.dumps({
                "id": "msg_mock_{:06d}".format(index),
                "type": "message", "role": "assistant", "model": payload["model"],
                "content": [{"type": "text", "text": text}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": uncached,
                          "cache_read_input_tokens": cached if hit else 0,
                          "cache_creation_input_tokens": 0 if hit else cached,
                          "output_tokens": out_tokens},
            }).encode()

        usage = {"prompt_tokens": cached + uncached, "completion_tokens": out_tokens,
                 "total_tokens": cached + uncached + out_tokens}
        if self.arm.backend == "deepseek":
            usage["prompt_cache_hit_tokens"] = cached if hit else 0
            usage["prompt_cache_miss_tokens"] = uncached + (0 if hit else cached)
        else:
            usage["prompt_tokens_details"] = {"cached_tokens": cached if hit else 0}
        return 200, json.dumps({
            "id": "chatcmpl-mock-{:06d}".format(index),
            "object": "chat.completion", "created": 0, "model": payload["model"],
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": text}}],
            "usage": usage,
        }).encode()


class PaperTransport(MockTransport):
    """The projection's transport: fixed-length answers, one tool round, no guard.

    ``--dry-run`` walks every item through both pipelines with this transport, so
    the projected prompt sizes come from the REAL stage templates rather than
    from an assumed constant.  Its answers are as long as the arm's measured
    pilot output, and it uses ``get_state`` once (never ``preview_dispatch``,
    which would dispatch the instance and make a dry run cost minutes).
    """

    def __init__(self, arm: E3Arm, out_tokens: int):
        super().__init__(arm)
        self.out_chars = max(1, int(out_tokens * self.APPROX_CHARS_PER_TOKEN))

    def _text(self, user: str) -> str:
        stage = self._stage(user)
        with self._lock:
            self.by_stage[stage] = self.by_stage.get(stage, 0) + 1
        used = "TOOL ROUNDS SO FAR" in user
        if stage in ("single_act", "multi_sched") and not used:
            orders = self._orders(user)
            return json.dumps({"tool": TOOL_GET_STATE,
                               "query": orders[0][0] if orders else "board"})
        if stage in ("single_act",):
            return json.dumps({"tool": TOOL_NONE})
        if stage == "multi_sched":
            return json.dumps({"strategy": "x" * max(1, self.out_chars - 20)})
        if stage == "multi_obs":
            return "x" * self.out_chars
        return self._final(user, "happy")


# --------------------------------------------------------------------------- #
# Cost projection and the launch gate                                          #
# --------------------------------------------------------------------------- #
def project_arm(arm: E3Arm, preps: dict, item_ids: list, services: Services,
                args, out_tokens: int) -> dict:
    """Walk every item through both pipelines on paper; return tokens and USD.

    Nothing is called and nothing is guarded: the transport answers offline and
    the revision tail is added analytically at the assumed block rate, which is
    the one number in here that is an assumption rather than a measurement.
    """
    transport = PaperTransport(arm, out_tokens)
    client = ChatClient(arm.backend, model=arm.model, api_key="paper",
                        max_tokens=args.max_tokens, transport=transport,
                        max_retries=0, retry_sleep_s=0.0)
    anthropic = BACKENDS[arm.backend].wire == WIRE_ANTHROPIC
    schema_tokens = arm.e1.schema_tokens
    cpt = arm.chars_per_token

    # The grid runs every item at every budget level and repeat; the paper walk
    # below covers one such pass, and ``factor`` is the rest.  The cache write is
    # NOT multiplied by it: an item's trajectories run together on one worker, so
    # each prefix is written once and read back by every later call of that item.
    factor = len(args.levels) * args.repeats
    prefix_tokens: dict = {}
    prefix_calls: dict = {}
    ops_cached: list = []
    ops_tails: list = []
    uncached = out = 0.0
    calls = 0
    per_pipeline: dict = {}
    for item_id in item_ids:
        prep = preps[item_id]
        transport.set_scenario("happy", prep.item["gold_ops"])
        for pipeline in PIPELINES:
            traj = Trajectory(
                arm=arm, prep=prep, pipeline=pipeline, budget_level="paper", repeat=0,
                run_uid="paper", budget=Budget(None, cpt, args.max_tokens),
                services=services, client=client, args=args,
            )
            PIPELINE_FUNCS[pipeline](traj)
            cell = per_pipeline.setdefault(pipeline, {"calls": 0, "prompt": 0.0, "out": 0.0})
            for row in traj.calls:
                calls += 1
                cell["calls"] += 1
                constrained = row["mode"] == M_CONSTRAINED
                head = len(system_for(row["stage"])) + len(prep.state)
                cached = head / cpt + (schema_tokens if constrained else 0)
                tail_tokens = (row["prompt_chars"] - head) / cpt
                key = (item_id, row["system"], constrained)
                prefix_tokens[key] = cached
                prefix_calls[key] = prefix_calls.get(key, 0) + 1
                uncached += tail_tokens
                out += out_tokens
                cell["prompt"] += cached + tail_tokens
                cell["out"] += out_tokens
                if constrained:
                    ops_cached.append(cached)
                    ops_tails.append(tail_tokens)

    write = sum(prefix_tokens.values())
    read = sum(prefix_tokens[k] * (prefix_calls[k] * factor - 1) for k in prefix_tokens)
    uncached *= factor
    out *= factor

    # The revision tail: one more operations-stage call on the share of first
    # finals the guard blocks.  Its prefix is already in the cache by then, so it
    # is charged as a read plus the average operations-stage tail.
    revisions = args.block_rate * len(item_ids) * len(PIPELINES) * factor
    read += revisions * (sum(ops_cached) / max(1, len(ops_cached)))
    uncached += revisions * (sum(ops_tails) / max(1, len(ops_tails)))
    out += revisions * out_tokens

    if not anthropic:  # these wires have no explicit write: a miss is plain input
        uncached += write
        write = 0.0
    base = arm.e1.prices[0][1]
    usage = {"cache_hit_tokens": read, "cache_write_tokens": write,
             "cache_miss_tokens": uncached + write, "prompt_tokens": read + uncached + write,
             "completion_tokens": out}
    return {
        "calls": calls * factor + revisions,
        "trajectories": len(item_ids) * len(PIPELINES) * factor,
        "write": write, "read": read, "uncached": uncached, "out": out,
        "usd": e1h.call_usd(base, usage),
        "per_pipeline": per_pipeline,
        "price_base": arm.e1.prices[0][0],
        "revisions": revisions,
    }


def print_projection(arm: E3Arm, preps: dict, item_ids: list, services: Services,
                     args) -> dict:
    pilot = arm.e1.out_tokens[arm.thinking]
    print("\nPROJECTED COST  ({} prices, retrieved {}; {})".format(
        arm.e1.prices[0][0], arm.e1.price_date, arm.e1.price_source))
    print("  token model : {:.3f} chars per token, measured; prompts walked through the "
          "REAL\n                stage templates on all {} items, so only the output "
          "length and the\n                revision rate are assumptions".format(
              arm.chars_per_token, len(item_ids)))
    print("  pilot source: {}".format(arm.e1.pilot_note))
    print("  assumptions : {} tool round at get_state (never preview_dispatch, which "
          "would\n                dispatch the instance), block rate {:.0%} -> one "
          "revision call each".format(1, args.block_rate))
    print("\n  {:<22s} {:>9s} {:>9s} {:>10s} {:>10s} {:>9s} {:>11s}".format(
        "output scenario", "traject.", "calls", "cache-wr", "cache-read", "in-uncach",
        "USD"))
    cells = {}
    for label, tokens in (("pilot ({} out)".format(pilot), pilot),
                          ("3x pilot", 3 * pilot),
                          ("max_tokens={}".format(args.max_tokens), args.max_tokens)):
        cell = project_arm(arm, preps, item_ids, services, args, tokens)
        cells[label] = cell
        print("  {:<22s} {:>9.0f} {:>9.0f} {:>10.0f} {:>10.0f} {:>9.0f} {:>11.2f}".format(
            label, cell["trajectories"], cell["calls"], cell["write"], cell["read"],
            cell["uncached"], cell["usd"]))
    for extra_label, extra_base in arm.e1.prices[1:]:
        alt = project_arm(arm, preps, item_ids, services, args, pilot)
        usage = {"cache_hit_tokens": alt["read"], "cache_write_tokens": alt["write"],
                 "cache_miss_tokens": alt["uncached"] + alt["write"],
                 "prompt_tokens": alt["read"] + alt["uncached"] + alt["write"],
                 "completion_tokens": alt["out"]}
        print("  the same plan at the {} base: USD {:.2f} at pilot output".format(
            extra_label, e1h.call_usd(extra_base, usage)))
    return cells


def launch_gate(arm: E3Arm, projected: float, partner: float = None) -> bool:
    """Print the envelope check.  ``False`` means the freeze's fallback applies."""
    backend = arm.backend
    cap = ENVELOPE_USD.get(backend)
    print("\nLAUNCH GATE  (the freeze's envelope)")
    if backend == "vllm":
        print("  local arm: no API cost, no envelope. GPU time is the only budget.")
        return True
    total = projected if partner is None else projected + partner
    if partner is not None:
        print("  Anthropic cap is joint over {}: this arm USD {:.2f} + the other "
              "USD {:.2f} = USD {:.2f}".format(
                  " and ".join(ANTHROPIC_ARMS), projected, partner, total))
    print("  {:<12s} projected USD {:>7.2f}   cap USD {:>6.2f}   {}".format(
        backend, total, cap, "PASS" if total <= cap else "BUSTS THE ENVELOPE"))
    if total > cap:
        print("  The freeze's pre-declared response is the E3-240 slice (never an "
              "ad-hoc trim):\n    --slice E3-240   -> 240 of the 300 items, the same "
              "draw, a strict subset,\n    so every trajectory already logged stays "
              "valid.  Projected USD {:.2f}.".format(total * 240.0 / 300.0))
    return total <= cap


# --------------------------------------------------------------------------- #
# The four launch questions                                                    #
# --------------------------------------------------------------------------- #
def launch_questions(arm: E3Arm, args, log_path: Path, slice_name: str, n_items: int) -> str:
    return """\
================================================================================
FOUR LAUNCH QUESTIONS (global CLAUDE.md experiment rules), answered before the
first paid call
================================================================================
1. PURPOSE.  The E3 trajectory log for the {arm} arm ({model}): {n} items x
   {levels} budget level(s) x {pipes} pipelines x {repeats} repeat(s).  It is the
   only E3 generation this arm needs: MULTI-UG, MULTI-G and SINGLE+G are replay
   configurations over these trajectories (scripts/e3_replay.py), exactly as
   E1's three guard arms replay from one generation log.  The numbers it feeds
   are the agent-layer decision (SINGLE+G vs MULTI-G at matched budgets), the
   cap-binding share per budget level, the terminal-state profile of Section
   5.4, and the register-stratified secondary tables.
2. EXPECTED RESULT.  The freeze adjudicates two stated priors: the generic
   evidence says the agent layer's marginal value is small, conditional or
   negative at matched budgets; the in-venue comparison reports the opposite at
   unmatched budgets.  Either direction is a result.  What would be a DEFECT and
   not a finding: a cap that binds in one pipeline and not the other at the same
   level (the budget would no longer be matched), an arm whose first final never
   parses, or trajectories whose token accounting is dominated by calls charged
   from the estimate rather than from reported usage.  All three are printed.
3. CONTAMINATION.  Both logs are append-only and flushed per row, keyed by
   (arm, budget level, pipeline, repeat, item_id); a restart skips completed
   keys and never rewrites.  A trajectory whose row records an error is not
   complete and is retried; its calls stay in the log under their own run_uid,
   and the last row for a key is the one that counts.  A log written by another
   arm or another E3 prompt version is refused.  The guard runs in the loop only
   to produce the revision tail, at E1's own G_CERT configuration, and every
   verdict is recomputed offline by the replay from the raw output.
   Trajectories: {log}
4. DATA ACCURACY.  Fatal assertions before the first call: the suite file's
   SHA-256 and the frozen schema's SHA-256; the item slice is {slice_name}
   recomputed from the suite and checked against results/e3_sample/e3_slice.json;
   the state block is the unchanged {version} render at top_k {top_k} and every
   (prefix, tail) split concatenates back to it byte for byte; the operations
   stages carry the byte-identical E1 system prompt; the guard configuration
   hash is E1's own, printed below.
================================================================================""".format(
        arm=arm.arm, model=arm.model, n=n_items, levels=len(args.levels),
        pipes=len(args.pipelines), repeats=args.repeats, log=log_path,
        slice_name=slice_name, version=PROMPT_VERSION, top_k=args.top_k)


# --------------------------------------------------------------------------- #
# The run                                                                      #
# --------------------------------------------------------------------------- #
def run_one(job: dict, arm: E3Arm, preps: dict, services: Services, client, args,
            transport) -> tuple:
    """One trajectory, start to finish, on one worker thread: ``(row, call rows)``."""
    prep = preps[job["item_id"]]
    if transport is not None and hasattr(transport, "set_scenario"):
        transport.set_scenario(args.scenario_of(job["item_id"]), prep.item["gold_ops"])
    run_uid = "{}|{}|{}|r{}|{}|{:.6f}".format(
        arm.arm, job["budget_level"], job["pipeline"], job["repeat"], job["item_id"],
        time.time())
    traj = Trajectory(
        arm=arm, prep=prep, pipeline=job["pipeline"], budget_level=job["budget_level"],
        repeat=job["repeat"], run_uid=run_uid,
        budget=Budget(job["budget_tokens"], arm.chars_per_token, args.max_tokens),
        services=services, client=client, args=args,
    )
    started = time.perf_counter()
    try:
        PIPELINE_FUNCS[job["pipeline"]](traj)
        if not args.no_revision:
            guarded_tail(traj)
    except Exception as exc:  # noqa: BLE001 - one bad item must not kill a paid grid
        traj.error = "{}: {}".format(type(exc).__name__, exc)
        traj.stopped = True
        traj.forced.append({"stage": traj.stages[-1] if traj.stages else None,
                            "reason": FORCE_ERROR, "error": traj.error})
        if traj.first_final is None:
            traj.set_first_final("aborted", json.dumps({"operations": []}), "aborted")
    return trajectory_row(traj, time.perf_counter() - started), traj.calls


def run(arm: E3Arm, groups: list, preps: dict, services: Services, client, args,
        transport, traj_path: Path, calls_path: Path) -> dict:
    """Run every group; one item's trajectories stay together on one worker."""
    tally = {"trajectories": 0, "calls": 0, "usd": 0.0, "tokens": 0, "errors": 0,
             "exhausted": 0, "blocked_first": 0, "revised": 0}
    base = arm.e1.prices[0][1]
    total = count_jobs(groups)
    lock = threading.Lock()
    started = time.perf_counter()
    interrupted = False

    with open(traj_path, "a", encoding="utf-8") as tf, \
            open(calls_path, "a", encoding="utf-8") as cf:

        def write(row: dict, calls: list) -> None:
            with lock:
                for call in calls:
                    cf.write(json.dumps(dict(call, arm=arm.arm, model=arm.model,
                                             item_id=row["item_id"],
                                             pipeline=row["pipeline"],
                                             budget_level=row["budget_level"],
                                             repeat=row["repeat"]),
                                        sort_keys=True) + "\n")
                cf.flush()
                tf.write(json.dumps(row, sort_keys=True) + "\n")
                tf.flush()
                tally["trajectories"] += 1
                tally["calls"] += row["n_calls"]
                tally["tokens"] += row["tokens"]["all"]
                tally["usd"] += sum(e1h.call_usd(base, c.get("usage") or {})
                                    for c in calls)
                tally["errors"] += 1 if row["outcome"] == OUTCOME_ERROR else 0
                tally["exhausted"] += 1 if row["budget_exhausted"] else 0
                chain = row["guard_chain"]
                if chain and chain[0]["blocked"]:
                    tally["blocked_first"] += 1
                if row["revisions"]:
                    tally["revised"] += 1
                _progress(tally, total, started)

        def work(group):
            return [run_one(job, arm, preps, services, client, args, transport)
                    for job in group["jobs"]]

        try:
            if args.workers <= 1:
                for group in groups:
                    for row, calls in work(group):
                        write(row, calls)
            else:
                with ThreadPoolExecutor(max_workers=args.workers) as pool:
                    for done_group in pool.map(work, groups):
                        for row, calls in done_group:
                            write(row, calls)
        except KeyboardInterrupt:
            interrupted = True
            print("\n[e3] INTERRUPTED after {} trajectories; the logs are append-only "
                  "and every completed key is skipped on the next run."
                  .format(tally["trajectories"]), flush=True)
    tally["interrupted"] = interrupted
    tally["wall_s"] = time.perf_counter() - started
    return tally


def _progress(tally: dict, total: int, started: float) -> None:
    n = tally["trajectories"]
    if n % 10 and n != total:
        return
    print("  {:>5d}/{:<5d} trajectories  calls={:<6d} tokens={:<9d} usd={:>7.3f} "
          "err={:<3d} exhausted={:<4d} blocked={:<4d} elapsed={:.0f}s".format(
              n, total, tally["calls"], tally["tokens"], tally["usd"], tally["errors"],
              tally["exhausted"], tally["blocked_first"], time.perf_counter() - started),
          flush=True)


# --------------------------------------------------------------------------- #
# Calibration                                                                  #
# --------------------------------------------------------------------------- #
def calibration_summary(rows: list, out_dir: Path, arm: E3Arm, ceiling: int) -> dict:
    """B_tight = p50 of this arm's own SINGLE all-token need, rounded up to 500."""
    totals = sorted(r["tokens"]["all"] for r in rows)
    if not totals:
        raise SystemExit("REFUSING TO REPORT: the calibration pass logged no trajectory")
    p50 = statistics.median(totals)
    tight = int(math.ceil(p50 / 500.0) * 500)
    loose = 4 * tight
    hit_ceiling = sum(1 for r in rows if r["budget_exhausted"])
    summary = {
        "arm": arm.arm, "model": arm.model, "pipeline": PIPELINE_SINGLE,
        "n": len(totals), "safety_ceiling_tokens": ceiling,
        "trajectories_that_hit_the_ceiling": hit_ceiling,
        "all_tokens": {
            "min": totals[0], "p25": totals[max(0, int(0.25 * len(totals)) - 1)],
            "p50": p50, "p75": totals[max(0, int(0.75 * len(totals)) - 1)],
            "p90": totals[max(0, int(0.90 * len(totals)) - 1)], "max": totals[-1],
            "mean": statistics.mean(totals),
        },
        "B_tight": tight, "B_loose": loose,
        "rule": "B_tight = p50 of this arm's own SINGLE-pipeline all-token need on "
                "E3-CAL-60, rounded UP to the nearest 500; B_loose = 4 x B_tight",
    }
    (out_dir / "calibration.json").write_text(json.dumps(summary, indent=1))
    print("\nCALIBRATION  ({} SINGLE trajectories on E3-CAL-60)".format(len(totals)))
    print("  all-token need per trajectory (prompt + completion, every call, "
          "cache-blind)")
    print("    min {min:.0f} | p25 {p25:.0f} | p50 {p50:.0f} | p75 {p75:.0f} | "
          "p90 {p90:.0f} | max {max:.0f}".format(**summary["all_tokens"]))
    if hit_ceiling:
        print("  WARNING: {} trajectory(ies) hit the {} token safety ceiling, so p50 is "
              "a floor,\n  not the need; re-run with a larger --calibrate-ceiling."
              .format(hit_ceiling, ceiling))
    print("  B_tight = {}  (p50 rounded up to the nearest 500)".format(tight))
    print("  B_loose = {}  (4 x B_tight)".format(loose))
    print("  launch the grid with:  --budget-tight {} --budget-loose {}".format(
        tight, loose))
    return summary


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arm", required=True, choices=sorted(ARMS))
    ap.add_argument("--out", default=None,
                    help="output dir (default results/e3_<arm>[_calibration])")
    ap.add_argument("--slice", default=e3_sample.SLICE_E3_300,
                    choices=list(e3_sample.SLICE_NAMES))
    ap.add_argument("--budget-tight", type=int, default=0,
                    help="B_tight in all-tokens per trajectory (from --calibrate)")
    ap.add_argument("--budget-loose", type=int, default=0, help="B_loose, normally 4x")
    ap.add_argument("--budget-level", default="both", choices=("tight", "loose", "both"))
    ap.add_argument("--pipeline", default="both", choices=("SINGLE", "MULTI", "both"))
    ap.add_argument("--repeats", type=int, default=0, help="0 = the arm's frozen count")
    ap.add_argument("--limit", type=int, default=0,
                    help="cap the plan to the first N ITEMS of the slice (smoke runs); "
                         "a resume works the same prefix of the same ordered plan")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--top-k", type=int, default=TOP_K)
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--max-tool-rounds", type=int, default=MAX_TOOL_ROUNDS)
    ap.add_argument("--max-revisions", type=int, default=MAX_REVISIONS)
    ap.add_argument("--no-revision", action="store_true",
                    help="skip the guarded revision tail (MULTI-UG only; not the grid)")
    ap.add_argument("--timeout-s", type=float, default=240.0)
    ap.add_argument("--max-retries", type=int, default=4)
    ap.add_argument("--block-rate", type=float, default=0.35,
                    help="dry-run only: assumed share of first finals the guard blocks")
    ap.add_argument("--calibrate", action="store_true",
                    help="60-item SINGLE-only pass; prints B_tight and B_loose")
    ap.add_argument("--calibrate-ceiling", type=int, default=60000,
                    help="safety ceiling for the uncapped calibration trajectories")
    ap.add_argument("--mock", action="store_true",
                    help="offline transport, five scripted scenarios: no network, no key")
    ap.add_argument("--mock-fail-every", type=int, default=0,
                    help="mock only: a terminal HTTP 400 every N calls (resume path)")
    ap.add_argument("--mock-scenario", default=None, choices=list(SCENARIOS),
                    help="mock only: force one scenario for every item")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the grid, the projection and the launch gate; call nothing")
    ap.add_argument("--skip-server-check", action="store_true",
                    help="local arms only: do not read /server_info back")
    args = ap.parse_args()

    arm = ARMS[args.arm]
    backend = BACKENDS[arm.backend]
    args.repeats = args.repeats or arm.repeats
    args.pipelines = list(PIPELINES) if args.pipeline == "both" else [args.pipeline]

    slice_name = e3_sample.SLICE_CAL_60 if args.calibrate else args.slice
    default_dir = "e3_{}{}".format(arm.arm, "_calibration" if args.calibrate else "")
    out_dir = Path(args.out) if args.out else (sg.CODE_DIR.parent / "results" / default_dir)
    traj_path = out_dir / "trajectories.jsonl"
    calls_path = out_dir / "calls.jsonl"

    if args.calibrate:
        args.pipelines = [PIPELINE_SINGLE]
        args.repeats = 1
        args.levels = [(BUDGET_CAL, args.calibrate_ceiling)]
    else:
        levels = []
        if args.budget_level in ("tight", "both"):
            levels.append((BUDGET_TIGHT, args.budget_tight))
        if args.budget_level in ("loose", "both"):
            levels.append((BUDGET_LOOSE, args.budget_loose))
        args.levels = levels

    print(launch_questions(arm, args, traj_path, slice_name,
                           e3_sample.SLICE_SIZES[slice_name]))
    inputs = sg.assert_inputs()
    print("[e3] suite sha256  {} OK".format(inputs["suite_sha256"]))
    print("[e3] schema sha256 {} OK".format(inputs["schema_sha256"]))

    rows = sg.load_suite()
    by_id = {r["item_id"]: r for r in rows}
    item_ids = e3_sample.load_slice(slice_name, rows=rows)
    items = [by_id[i] for i in item_ids]
    print("[e3] slice {}: {} items, sha256 {}".format(
        slice_name, len(item_ids), e3_sample.list_sha256(item_ids)))

    instances = sg.Instances()
    t0 = time.perf_counter()
    preps = prepare(items, instances, args.top_k)
    print("[e3] {} state blocks rendered and split in {:.1f}s ({} at the orders "
          "boundary, {} at the instruction); prefix+tail is the unchanged {} render"
          .format(len(preps), time.perf_counter() - t0,
                  sum(1 for p in preps.values() if p.split_at == "orders"),
                  sum(1 for p in preps.values() if p.split_at == "instruction"),
                  PROMPT_VERSION))
    guard_cfg = e1e.guard_configs()["G_CERT"]
    print("[e3] guard in the loop: {} config_hash {} (E1's own, tau {}, lb_tier {})"
          .format(guard_cfg.name, guard_cfg.config_hash[:16], guard_cfg.tau,
                  guard_cfg.lb_tier))
    services = Services(top_k=args.top_k, guard_config=guard_cfg)

    if backend.requires_json_word and "json" not in SYSTEM_OPS.lower():
        raise SystemExit(
            "REFUSING TO RUN: {} JSON-object mode needs the word 'json' in the prompt "
            "and the frozen system prompt does not contain it".format(arm.backend))

    # -- the plan ------------------------------------------------------------- #
    done, logged, errors, broken = read_completed(traj_path, arm)
    plan_all = build_plan(arm, item_ids, args.levels, args.pipelines, args.repeats)
    groups = remaining_groups(plan_all, done, arm, args.limit)

    print("\nGRID  (arm {}, model {}, wire {})".format(arm.arm, arm.model, backend.wire))
    print("  role             : {}".format(arm.note))
    print("  items            : {} ({})".format(len(item_ids), slice_name))
    print("  budget levels    : {}".format(", ".join(
        "{}={}".format(lab, tok or "uncapped") for lab, tok in args.levels)))
    print("  pipelines        : {}   repeats: {}".format(
        ", ".join(args.pipelines), args.repeats))
    print("  enforcement      : ops stages {} = {}, reasoning stages {}".format(
        arm.mode, backend.constrained, ENF_NONE))
    print("  thinking         : {}".format(
        json.dumps(arm.thinking_body) if arm.thinking_body else "no field sent"))
    print("  tools            : get_state, preview_dispatch; <= {} round(s), text "
          "results, no vendor tool API".format(args.max_tool_rounds))
    print("  revision tail    : {}".format(
        "disabled (--no-revision)" if args.no_revision
        else "<= {} revision(s) on a guard block".format(args.max_revisions)))
    print("  trajectories     : {} planned, {} already complete, {} to run in {} "
          "item group(s)".format(count_jobs(plan_all), len(done), count_jobs(groups),
                                 len(groups)))
    print("  already logged   : {} rows, {} of them errors{}".format(
        logged, errors, ", {} torn lines skipped".format(broken) if broken else ""))
    print("  logs             : {}\n                     {}".format(traj_path, calls_path))

    missing_budgets = not args.calibrate and any(not tok for _lab, tok in args.levels)
    if missing_budgets:
        head = "NOTE (--dry-run)" if args.dry_run else "REFUSING TO RUN"
        print("\n{}: --budget-tight and --budget-loose are required for a grid; they "
              "come from\n--calibrate, which measures this arm's own p50 all-token "
              "need.  The projection below\nis of the calls the pipelines make, and "
              "does not depend on the ceiling.".format(head))
        if not args.dry_run:
            return 2

    # -- projection and the launch gate --------------------------------------- #
    if args.dry_run:
        args.scenario_of = lambda item_id: "happy"
        cells = print_projection(arm, preps, item_ids, services, args)
        pilot_label = [k for k in cells if k.startswith("pilot")][0]
        projected = cells[pilot_label]["usd"]
        partner = None
        if arm.backend == "anthropic":
            other = [a for a in ANTHROPIC_ARMS if a != arm.arm]
            if other:
                partner_arm = ARMS[other[0]]
                partner = project_arm(
                    partner_arm, preps, item_ids, services, args,
                    partner_arm.e1.out_tokens[partner_arm.thinking])["usd"]
        launch_gate(arm, projected, partner)
        print("\nNO CALL MADE (--dry-run).")
        return 0

    if not groups:
        print("\nNothing to do: every planned trajectory is already logged.")
        return 0

    # -- the client ------------------------------------------------------------ #
    transport = None
    api_key = None
    if args.mock:
        transport = MockTransport(arm, fail_every=args.mock_fail_every)
        api_key = "mock-key-not-a-real-key"
        order = {item_id: i for i, item_id in enumerate(item_ids)}
        args.scenario_of = (
            (lambda item_id: args.mock_scenario) if args.mock_scenario
            else (lambda item_id: SCENARIOS[order[item_id] % len(SCENARIOS)])
        )
        print("\n[e3] MOCK TRANSPORT: no network, no key, no cost. Scenarios cycle "
              "{} over the slice order.".format(", ".join(SCENARIOS)))
    else:
        args.scenario_of = lambda item_id: "live"
        if arm.backend == "vllm":
            if not args.skip_server_check:
                base_url = (os.environ.get(backend.base_url_env)
                            or backend.default_base_url)
                resolved = assert_xgrammar_backend(base_url)
                print("\n[e3] vLLM structured-outputs backend read back: {}".format(
                    resolved))
        else:
            loaded = load_env()
            if not os.environ.get(backend.api_key_env):
                print("\nREFUSING TO RUN: {} is not set ({} names loaded from the "
                      "project .env).".format(backend.api_key_env, len(loaded)))
                return 2
            print("\n[e3] key {} present (never printed).".format(backend.api_key_env))

    out_dir.mkdir(parents=True, exist_ok=True)
    client = ChatClient(
        arm.backend, model=arm.model, api_key=api_key, max_tokens=args.max_tokens,
        timeout_s=args.timeout_s, max_retries=args.max_retries,
        retry_sleep_s=0.0 if args.mock else 2.0, transport=transport,
    )

    print("\n[e3] running {} trajectories ({} item groups) on {} worker(s)".format(
        count_jobs(groups), len(groups), args.workers))
    tally = run(arm, groups, preps, services, client, args, transport, traj_path,
                calls_path)

    print("\n[e3] {} trajectories, {} calls, {} all-tokens, {} errors, {} budget-"
          "exhausted, {} blocked at the first final, {} revised".format(
              tally["trajectories"], tally["calls"], tally["tokens"], tally["errors"],
              tally["exhausted"], tally["blocked_first"], tally["revised"]))
    print("[e3] tools used: get_state {}, preview_dispatch {}; guard calls {}".format(
        services.n_get_state, services.n_preview, services.n_guard))

    summary = None
    if args.calibrate:
        written = [json.loads(line) for line in open(traj_path, encoding="utf-8")
                   if line.strip()]
        summary = calibration_summary(written, out_dir, arm, args.calibrate_ceiling)

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    meta = {
        "date": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "scaffold_version": SCAFFOLD_VERSION,
        "arm": arm.arm, "model": arm.model, "backend": arm.backend, "wire": backend.wire,
        "mode": arm.mode, "thinking": arm.thinking, "thinking_body": arm.thinking_body,
        "slice": slice_name, "slice_sha256": e3_sample.list_sha256(item_ids),
        "items": len(item_ids), "pipelines": args.pipelines, "repeats": args.repeats,
        "budget_levels": [{"level": lab, "tokens": tok} for lab, tok in args.levels],
        "max_tokens": args.max_tokens, "max_tool_rounds": args.max_tool_rounds,
        "max_revisions": 0 if args.no_revision else args.max_revisions,
        "workers": args.workers, "top_k": args.top_k,
        "prompt_version": PROMPT_VERSION, "e3_prompt_version": E3_PROMPT_VERSION,
        "guard_config": guard_cfg.name, "guard_config_hash": guard_cfg.config_hash,
        "suite_sha256": inputs["suite_sha256"], "schema_sha256": inputs["schema_sha256"],
        "mock": bool(args.mock), "planned": count_jobs(plan_all), "tally": tally,
        "calibration": summary,
        "dedupe_rule": "last row per (arm, budget_level, pipeline, repeat, item_id) "
                       "wins; earlier rows for a key are superseded attempts, and each "
                       "call row carries the run_uid of the attempt that produced it",
        "budget_accounting": "sum over every call of reported prompt_tokens + "
                             "completion_tokens, cache-status blind; a call with no "
                             "reported usage is charged the pre-call estimate",
    }
    meta_path = out_dir / "run_meta_{}.json".format(stamp)
    meta_path.write_text(json.dumps(meta, indent=1, default=str))
    print("[e3] meta   : {}".format(meta_path))
    if not args.mock:
        print("[e3] estimated spend this session: USD {:.2f} ({} base, retrieved {})"
              .format(tally["usd"], arm.e1.prices[0][0], arm.e1.price_date))
    return 130 if tally.get("interrupted") else 0


if __name__ == "__main__":
    sys.exit(main())
