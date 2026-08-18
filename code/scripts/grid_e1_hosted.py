#!/usr/bin/env python
"""E1 grid, hosted arms: one runner for DeepSeek, OpenAI and the two Claude models.

Same job as ``grid_e1_local.py`` and the same raw-row contract, over the API
instead of a local engine: this script only GENERATES.  UNGUARDED / G_FEAS /
G_CERT are replay configurations over the raw outputs, so one generation log per
arm serves every guard arm of E1, and the evaluation is a separate offline phase.

Design frozen at launch (decisions.md, 2026-08-11, "DESIGN FREEZE: hosted E1
grids + E1 evaluation"); nothing here is a tuning knob:

* items    : all 2,000 suite items (v0.2 sha asserted), prompt l1-prompt-1.0.0
             UNCHANGED - the same ``build_messages`` render the local arms used;
* arms     : one ``--arm`` per run, from the table below;
* modes    : M_constrained and M_free, the enforcement-mode axis;
* thinking : per arm, always set EXPLICITLY through ``extra_body`` and never
             through the ``reasoning`` kwarg.  The Anthropic request builder
             silently drops ``temperature``, ``seed`` and ``reasoning`` (that is
             what lets one client serve both wires), so a reasoning kwarg on a
             Claude arm would be a configuration that never reached the wire;
* repeats  : 2 identical passes (r0, r1) per configuration.  The hosted
             endpoints are not deterministic, so the pair measures API
             nondeterminism the way the local arm's repeats measure engine
             nondeterminism;
* budget   : max_tokens 4096; temperature left at the client default (0.0 on the
             OpenAI wire, never sent on the Anthropic wire); no seed.

Prompt caching.  The rendered user string is split at the first
``"\\n\\nWork orders this request refers to:"`` (fallback ``"\\n\\nINSTRUCTION"``)
into ``(stable_prefix, tail)`` and passed as that 2-tuple.  On the Anthropic wire
the prefix becomes a ``cache_control`` text block; on the OpenAI wire the two are
concatenated byte-identically.  The runner asserts, for every item, that
``prefix + tail`` is the untouched render, that the fingerprint of the split
prompt equals the fingerprint of ``build_messages``, and (when the local 14B log
is on disk) that both equal the local arm's logged ``prompt_hash``.  A paid arm
that quietly re-worded the prompt would not be comparable with anything, so all
three checks are fatal.

Call order and workers.  Calls are ordered by ``(instance_path, frozen_seed,
item_id)``; the items sharing an ``(instance_path, frozen_seed)`` group share
their prompt prefix.  The first call of each group runs alone so the provider
writes that prefix into its cache, and the rest of the group goes through a
worker pool (``--workers``, default 8).  One writer loop appends the rows.

Resumability.  The raw log is append-only, flushed per row, and keyed by
``(mode, thinking, repeat, item_id)``.  On start the existing log is read and
completed keys are skipped, so an interrupted paid run is resumed by re-running
the same command.  A row whose outcome is ``error`` does NOT count as complete
and is retried; the error row stays in the log for the record, and the last row
for a key is the one that counts (``dedupe_rule`` in the run meta).

``latency_ms`` is the wall time around one ``complete()`` call, retries and
their backoff included, and it is a network measurement, not a compute one.
``--limit N`` caps the plan at its first N CALLS (not items), so a smoke run and
its resume share one prefix of the same ordered plan.

Run::

    conda run -n fjsp python scripts/grid_e1_hosted.py --arm sonnet --dry-run
    conda run -n fjsp python scripts/grid_e1_hosted.py --arm sonnet --mock --limit 40
    conda run -n fjsp python scripts/grid_e1_hosted.py --arm sonnet          # paid

``--mock`` injects an offline transport that answers both wire shapes, so the
whole pipeline (splitting, the caching tuple, usage normalisation, logging,
resume) runs end to end with no network and no key.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))  # scripts/: suite_gate, _envfile
sys.path.insert(0, str(_HERE.parent))  # code/: l1guard, l1adapter

import suite_gate as sg  # noqa: E402  (suite + schema hash asserts, prompts, instances)
from _envfile import load_env  # noqa: E402
from l1guard.logging import OUTCOME_ERROR, OUTCOME_OK  # noqa: E402
from l1guard.models import (  # noqa: E402
    BACKENDS,
    ENF_NONE,
    M_CONSTRAINED,
    M_FREE,
    WIRE_ANTHROPIC,
    ChatClient,
)

#: The frozen prompt module, loaded exactly the way the local arms loaded it.
PROMPTS = sg.load_prompts_module()
SYSTEM_PROMPT = PROMPTS.SYSTEM_PROMPT
PROMPT_VERSION = PROMPTS.PROMPT_VERSION

MODES = (M_CONSTRAINED, M_FREE)
REPEATS = 2
MAX_TOKENS = 4096
TOP_K = 10

#: The cache boundary in the rendered user prompt: part 2 of the state block is
#: the first part that varies within an (instance, frozen_seed) group.  1,713 of
#: the 2,000 items carry it; the other 287 name no order and are split at the
#: instruction instead (measured on the suite, not assumed).
CACHE_BOUNDARY = "\n\nWork orders this request refers to:"
CACHE_BOUNDARY_FALLBACK = "\n\nINSTRUCTION"

#: The local 14B generation log, used as an independent prompt-hash reference.
LOCAL_LOG = sg.CODE_DIR.parent / "results" / "grid_e1_local" / "proposals_raw.jsonl"


# --------------------------------------------------------------------------- #
# The arm table: the frozen grid, as data                                      #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Arm:
    """One hosted arm: what to call, how to ask it to think, and what it costs.

    ``thinking`` is an ordered tuple of ``(label, extra_body)``.  The label is
    what the raw row records (``None`` when the arm sends no thinking field at
    all); the extra body is merged into the request verbatim.  ``prices`` are
    USD per token, the first base being the one in force on ``price_date``.  The
    pilot numbers are measurements, each carrying the file it came from, and
    they are used only for the ``--dry-run`` projection.
    """

    arm: str
    backend: str
    model: str
    thinking: tuple
    prices: tuple
    price_date: str
    price_source: str
    chars_per_token: float  # measured: pilot prompt chars / reported prompt tokens
    #: The M_constrained input surcharge for the frozen schema, measured as the
    #: pilot's M_constrained-minus-M_free prompt tokens.  Both pilots show it
    #: arriving inside the CACHED prefix (Anthropic: cache_read 3,219 -> 4,736
    #: with uncached flat at 22; OpenAI: cached 2,304 -> 2,816), so the
    #: projection caches it rather than billing it fresh on every call.
    schema_tokens: int
    out_tokens: dict  # thinking label -> pilot median output tokens per call
    pilot_note: str
    #: Modes this arm runs.  Full arms run both; the v3.10 Sol SPOT-CHECK runs
    #: M_constrained only (config-matched to the Opus thinking-disabled core).
    modes: tuple = MODES


ARMS: dict = {
    "deepseek": Arm(
        arm="deepseek",
        backend="deepseek",
        model="deepseek-v4-pro",
        thinking=(
            ("non_think", {"thinking": {"type": "disabled"}}),
            ("think_high", {"thinking": {"type": "enabled"}, "reasoning_effort": "high"}),
        ),
        prices=(
            ("list", {"in": 0.435 / 1e6, "cache_read": 0.003625 / 1e6,
                      "cache_write": None, "out": 0.87 / 1e6}),
        ),
        price_date="2026-08-11",
        price_source="api-docs.deepseek.com/quick_start/pricing (the page warns of a "
                     "coming increase, so the retrieval date is part of the number)",
        chars_per_token=2.26,
        schema_tokens=0,  # JSON-object mode carries no schema on the wire
        out_tokens={"non_think": 14, "think_high": 330},
        pilot_note="results/deepseek_pilot_summary.json, warm-block medians "
                   "(non_think 13.5 out; think_high 330 out, 324 of them reasoning)",
    ),
    "openai": Arm(
        arm="openai",
        backend="openai",
        model="gpt-5.4-mini-2026-03-17",
        # Reasoning effort is omitted on the wire = the snapshot default.  The
        # pilot measured zero reasoning tokens on this task, so the axis buys
        # nothing here and the freeze records the omission as the design.
        thinking=((None, {}),),
        prices=(
            ("list", {"in": 0.75 / 1e6, "cache_read": 0.075 / 1e6,
                      "cache_write": None, "out": 4.50 / 1e6}),
        ),
        price_date="2026-08-11",
        price_source="developers.openai.com/api/docs/pricing.md",
        chars_per_token=2.33,
        schema_tokens=424,  # measured M_constrained minus M_free prompt tokens
        out_tokens={None: 30},
        pilot_note="results/openai_pilot_summary.json, warm-block medians "
                   "(30 out under M_constrained, 0 reasoning tokens)",
    ),
    "sol": Arm(
        arm="sol",
        backend="openai",
        model="gpt-5.6-sol",
        # Flagship-tier cross-vendor SPOT-CHECK (v3.10): M_constrained only,
        # reasoning effort "none" - config-matched to the Opus 5
        # thinking-disabled core unit; run with --repeats 1.  Honestly labelled
        # a spot-check in the paper, never a full arm.
        thinking=(("none", {"reasoning_effort": "none"}),),
        prices=(
            ("list", {"in": 5.00 / 1e6, "cache_read": 0.50 / 1e6,
                      "cache_write": None, "out": 30.00 / 1e6}),
        ),
        price_date="2026-08-12",
        price_source="developers.openai.com/api/docs/pricing (re-verified live)",
        chars_per_token=2.33,
        schema_tokens=424,  # same wire and schema transport as the mini arm
        out_tokens={"none": 24},
        pilot_note="results/sol_pilot/openai_pilot_summary.json (temperature, "
                   "strict schema + integer enum, effort none: all accepted)",
        modes=(M_CONSTRAINED,),
    ),
    "sonnet": Arm(
        arm="sonnet",
        backend="anthropic",
        model="claude-sonnet-5",
        # Thinking off, explicitly: the pilot probe accepted the field, and this
        # arm is the config-matched partner of the Opus "disabled" half.
        thinking=(("disabled", {"thinking": {"type": "disabled"}}),),
        prices=(
            ("intro (through 2026-08-31)",
             {"in": 2.00 / 1e6, "cache_read": 0.20 / 1e6,
              "cache_write": 2.50 / 1e6, "out": 10.00 / 1e6}),
            ("standard (from 2026-09-01)",
             {"in": 3.00 / 1e6, "cache_read": 0.30 / 1e6,
              "cache_write": 3.75 / 1e6, "out": 15.00 / 1e6}),
        ),
        price_date="2026-08-11",
        price_source="Anthropic pricing (cache read 10% of input, 5-minute write 125%)",
        chars_per_token=1.92,
        schema_tokens=1517,  # measured M_constrained minus M_free prompt tokens
        out_tokens={"disabled": 37},
        pilot_note="results/anthropic_pilot_summary.json, warm-block medians (37 out "
                   "constrained, 34.5 free; temperature rejected, thinking-disabled "
                   "accepted, default content blocks ['text'])",
    ),
    "opus": Arm(
        arm="opus",
        backend="anthropic",
        model="claude-opus-5",
        # Two halves: "disabled" is config-matched to Sonnet (capability at a
        # fixed configuration); "default" sends NO thinking field at all, which
        # is the flagship at deployed strength (the pilot saw ['thinking','text']
        # come back).  The pair isolates thinking's contribution at the top rung.
        thinking=(
            ("disabled", {"thinking": {"type": "disabled"}}),
            ("default", {}),
        ),
        prices=(
            ("list", {"in": 5.00 / 1e6, "cache_read": 0.50 / 1e6,
                      "cache_write": 6.25 / 1e6, "out": 25.00 / 1e6}),
        ),
        price_date="2026-08-11",
        price_source="Anthropic pricing ($5/$25 per M, cache 0.5/6.25)",
        chars_per_token=1.92,
        schema_tokens=1517,
        out_tokens={"disabled": 29, "default": 68},
        pilot_note="results/opus5_pilot/anthropic_pilot_summary.json (29 out "
                   "constrained thinking-disabled; the single default-thinking probe "
                   "returned 68 output tokens, thinking billed inside them)",
    ),
}


def thinking_body(arm: Arm, label) -> dict:
    return dict(dict(arm.thinking)[label])


def pass_list(arm: Arm, repeats: int) -> list:
    """Every ``(mode, thinking label, repeat)`` pass, in call order."""
    out = []
    for mode in arm.modes:
        for label, _ in arm.thinking:
            for repeat in range(repeats):
                out.append((mode, label, repeat))
    return out


def label_text(label) -> str:
    return "(omitted)" if label is None else label


# --------------------------------------------------------------------------- #
# Prompts: rendered once, split at the cache boundary, fingerprint-asserted     #
# --------------------------------------------------------------------------- #
@dataclass
class Prepared:
    """One suite item, ready to call: its group, its split prompt, its hash."""

    item: dict
    instance_path: str
    group: tuple
    prefix: str
    tail: str
    prompt_hash: str
    split_at: str


def split_user_prompt(text: str) -> tuple:
    """``(stable_prefix, tail, which_boundary)`` for one rendered user prompt."""
    at = text.find(CACHE_BOUNDARY)
    which = "orders"
    if at < 0:
        at = text.find(CACHE_BOUNDARY_FALLBACK)
        which = "instruction"
    if at <= 0:
        raise SystemExit(
            "REFUSING TO RUN: no cache boundary in the rendered prompt; the prompt "
            "module changed and the split is no longer defined"
        )
    return text[:at], text[at:], which


def prepare(items: list, instances, top_k: int) -> list:
    """Render, split and fingerprint every item; fatal on any mismatch."""
    prepared = []
    for item in items:
        messages = PROMPTS.build_messages(instances.get(item), item, top_k)
        system, user = messages[0]["content"], messages[1]["content"]
        prefix, tail, which = split_user_prompt(user)
        if prefix + tail != user:
            raise SystemExit(
                "REFUSING TO RUN: the split is not byte-identical for {}".format(
                    item["item_id"])
            )
        full = PROMPTS.prompt_fingerprint(messages)
        split = PROMPTS.prompt_fingerprint(
            [{"role": "system", "content": system},
             {"role": "user", "content": prefix + tail}]
        )
        if split != full:
            raise SystemExit(
                "REFUSING TO RUN: the prompt fingerprint changed under the split for "
                "{} ({} != {})".format(item["item_id"], split, full)
            )
        prepared.append(
            Prepared(
                item=item,
                instance_path=instances.path(item),
                group=(instances.path(item), tuple(item["episode"]["frozen_seed"])),
                prefix=prefix,
                tail=tail,
                prompt_hash=full,
                split_at=which,
            )
        )
    prepared.sort(key=lambda p: (p.group[0], p.group[1], p.item["item_id"]))
    return prepared


def crosscheck_local(prepared: list, path: Path) -> str:
    """Assert every prompt hash equals the local 14B arm's, when that log exists."""
    if not path.exists():
        return "local 14B log absent ({}), prompt-hash cross-check skipped".format(path)
    local = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                row = json.loads(line)
                local[row["item_id"]] = row["prompt_hash"]
    checked, missing = 0, 0
    for prep in prepared:
        want = local.get(prep.item["item_id"])
        if want is None:
            missing += 1
            continue
        if want != prep.prompt_hash:
            raise SystemExit(
                "REFUSING TO RUN: the prompt hash differs from the local arm for {} "
                "({} != {})".format(prep.item["item_id"], prep.prompt_hash, want)
            )
        checked += 1
    return ("{} prompt hashes identical to the local 14B log"
            "{}".format(checked, ", {} items not in it".format(missing) if missing else ""))


def group_runs(prepared: list) -> list:
    """The prepared items as ordered ``(group_key, [Prepared, ...])`` runs."""
    runs: list = []
    for prep in prepared:
        if not runs or runs[-1][0] != prep.group:
            runs.append((prep.group, []))
        runs[-1][1].append(prep)
    return runs


def prompt_stats(prepared: list, system_chars: int) -> dict:
    """The character sizes the cost projection needs, from the real prompts."""
    seen = set()
    write_chars = 0
    total_prefix = total_tail = 0
    for prep in prepared:
        total_prefix += len(prep.prefix)
        total_tail += len(prep.tail)
        key = (prep.group, prep.prefix)
        if key not in seen:
            seen.add(key)
            write_chars += len(prep.prefix) + system_chars
    return {
        "items": len(prepared),
        "system_chars": system_chars,
        "prefix_chars_total": total_prefix,
        "tail_chars_total": total_tail,
        "cache_writes_per_pass": len(seen),
        "write_chars_per_pass": write_chars,
        "groups": len({p.group for p in prepared}),
    }


# --------------------------------------------------------------------------- #
# The call plan and the resume set                                             #
# --------------------------------------------------------------------------- #
def row_key(mode: str, thinking, repeat, item_id: str) -> tuple:
    return (mode, thinking, int(repeat), item_id)


def read_completed(path: Path, arm: Arm) -> tuple:
    """Keys already logged with a non-error outcome, plus the row counts.

    Also refuses a log written by another arm or another prompt version: the
    default output directory is per arm, but ``--out`` can point anywhere and a
    mixed log would silently corrupt both runs.
    """
    done: set = set()
    rows = errors = broken = 0
    if not path.exists():
        return done, rows, errors, broken
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
            if row.get("prompt_version") != PROMPT_VERSION:
                raise SystemExit(
                    "REFUSING TO RUN: {} holds rows for prompt version {!r}, not "
                    "{!r}".format(path, row.get("prompt_version"), PROMPT_VERSION)
                )
            rows += 1
            key = row_key(row["mode"], row.get("thinking"), row["repeat"], row["item_id"])
            if row.get("outcome") == OUTCOME_ERROR:
                errors += 1
                done.discard(key)
            else:
                done.add(key)
    return done, rows, errors, broken


def build_plan(arm: Arm, prepared: list, repeats: int, limit: int) -> list:
    """The flat call plan in wire order, truncated by ``--limit`` (a CALL cap)."""
    runs = group_runs(prepared)
    plan = []
    for mode, label, repeat in pass_list(arm, repeats):
        for _, members in runs:
            for prep in members:
                plan.append({"mode": mode, "thinking": label, "repeat": repeat,
                             "prep": prep})
        if limit and len(plan) >= limit:
            break
    return plan[:limit] if limit else plan


# --------------------------------------------------------------------------- #
# The mock transport: both wire shapes, offline                                #
# --------------------------------------------------------------------------- #
class MockTransport:
    """Answers a request the way the provider would, with no network.

    It reads the request body, so it exercises exactly what the runner sends:
    the two Anthropic text blocks and their ``cache_control``, the OpenAI joined
    string, the enforcement field and the thinking field.  Token counts are
    estimated from characters and the prefix cache is simulated per wire, so
    usage normalisation, the cost accounting and the resume logic all run on
    plausible numbers.  It is never used for a paid run.
    """

    APPROX_CHARS_PER_TOKEN = 4

    def __init__(self, arm: Arm, fail_every: int = 0):
        self.arm = arm
        self.fail_every = int(fail_every)
        self._lock = threading.Lock()
        self._seen: set = set()
        self.calls = 0
        self.bodies: list = []  # every request body, for the wire checks

    def _tokens(self, text: str) -> int:
        return max(1, len(text) // self.APPROX_CHARS_PER_TOKEN)

    def __call__(self, method, url, headers, body, timeout):
        payload = json.loads(body.decode("utf-8"))
        with self._lock:
            self.calls += 1
            index = self.calls
            self.bodies.append(payload)
        if self.fail_every and index % self.fail_every == 0:
            # 400 is not in the retry set: a terminal error, which is what the
            # resume path must treat as "not complete".
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
            thinking_on = (payload.get("thinking") or {}).get("type") != "disabled"
        else:
            content = payload["messages"][1]["content"]
            at = content.find(CACHE_BOUNDARY)
            if at < 0:
                at = max(0, content.find(CACHE_BOUNDARY_FALLBACK))
            prefix, tail = content[:at], content[at:]
            system = payload["messages"][0]["content"]
            constrained = "response_format" in payload
            thinking_on = (payload.get("thinking") or {}).get("type") == "enabled"

        with self._lock:
            cache_key = (payload["model"], constrained, system, prefix)
            hit = cache_key in self._seen
            self._seen.add(cache_key)
        cached = self._tokens(system) + self._tokens(prefix)
        uncached = self._tokens(tail)
        if constrained:  # the frozen schema, inside the cached prefix as measured
            cached += 1500 if anthropic else 400

        text = ('{"operations": []}' if index % 5
                else '{"operations": [{"op": "freeze", "order_id": "W0001"}]}')
        out_tokens = self._tokens(text) + (300 if thinking_on else 0)

        if anthropic:
            blocks_out = []
            if thinking_on:
                blocks_out.append({"type": "thinking", "thinking": "mock reasoning",
                                   "signature": "mock"})
            blocks_out.append({"type": "text", "text": text})
            return 200, json.dumps({
                "id": "msg_mock_{:06d}".format(index),
                "type": "message",
                "role": "assistant",
                "model": payload["model"],
                "content": blocks_out,
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {
                    "input_tokens": uncached,
                    "cache_read_input_tokens": cached if hit else 0,
                    "cache_creation_input_tokens": 0 if hit else cached,
                    "output_tokens": out_tokens,
                },
            }).encode()

        usage = {
            "prompt_tokens": cached + uncached,
            "completion_tokens": out_tokens,
            "total_tokens": cached + uncached + out_tokens,
            "completion_tokens_details": {"reasoning_tokens": 300 if thinking_on else 0},
        }
        if self.arm.backend == "deepseek":  # its own two counters
            usage["prompt_cache_hit_tokens"] = cached if hit else 0
            usage["prompt_cache_miss_tokens"] = uncached + (0 if hit else cached)
        else:
            usage["prompt_tokens_details"] = {"cached_tokens": cached if hit else 0}
        return 200, json.dumps({
            "id": "chatcmpl-mock-{:06d}".format(index),
            "object": "chat.completion",
            "created": 0,
            "model": payload["model"],
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": text}}],
            "usage": usage,
        }).encode()


# --------------------------------------------------------------------------- #
# Cost                                                                         #
# --------------------------------------------------------------------------- #
def call_usd(base: dict, usage: dict) -> float:
    """USD for one measured call, from its normalised usage."""
    read = usage.get("cache_hit_tokens") or 0
    write = usage.get("cache_write_tokens") or 0
    miss = usage.get("cache_miss_tokens")
    if miss is None:
        miss = max(0, (usage.get("prompt_tokens") or 0) - read)
    uncached = max(0, miss - write)
    out = usage.get("completion_tokens") or 0
    write_price = base["cache_write"] if base.get("cache_write") else base["in"]
    return (uncached * base["in"] + read * base["cache_read"]
            + write * write_price + out * base["out"])


def project_pass(arm: Arm, stats: dict, mode: str, out_tokens: float, base: dict,
                 anthropic: bool) -> dict:
    """Projected tokens and USD for ONE pass (one configuration, one repeat).

    The prefix of each distinct cached block is paid once per pass (a cache
    write on the Anthropic wire, plain input on the others) and read back on
    every later call that shares it; the frozen schema of M_constrained sits
    inside that cached block on both wires (see ``Arm.schema_tokens``).  Token
    counts come from the measured characters and the arm's measured
    chars-per-token, so this is an estimate with a stated basis, not a quote.
    """
    cpt = arm.chars_per_token
    n = stats["items"]
    writes = stats["cache_writes_per_pass"]
    schema = arm.schema_tokens if mode == M_CONSTRAINED else 0
    cacheable = (n * stats["system_chars"] + stats["prefix_chars_total"]) / cpt + n * schema
    write = stats["write_chars_per_pass"] / cpt + writes * schema
    read = cacheable - write
    uncached = stats["tail_chars_total"] / cpt
    if not anthropic:  # these wires have no explicit write: a miss is plain input
        uncached += write
        write = 0.0
    out = n * out_tokens
    write_price = base["cache_write"] if base.get("cache_write") else base["in"]
    usd = (uncached * base["in"] + read * base["cache_read"]
           + write * write_price + out * base["out"])
    return {"calls": n, "uncached": uncached, "read": read, "write": write,
            "out": out, "usd": usd}


# --------------------------------------------------------------------------- #
# Printing: the four launch questions, the plan, the projection                #
# --------------------------------------------------------------------------- #
def launch_questions(arm: Arm, repeats: int, log_path: Path) -> str:
    labels = ", ".join(label_text(lab) for lab, _ in arm.thinking)
    modes = ", ".join(arm.modes)
    return """\
================================================================================
FOUR LAUNCH QUESTIONS (global CLAUDE.md experiment rules), answered before the
first paid call
================================================================================
1. PURPOSE.  The E1 generation log for the {arm} arm ({model}): all 2,000 suite
   items x {{{modes}}} x thinking {{{labels}}} x {repeats} repeats.
   Every E1 exhibit for this arm is computed from this log by offline replay:
   the terminal-state tables, the per-class V1-V6 catch rates under G_FEAS and
   G_CERT, the benign-twin false-block rates, the constraint-tax decomposition
   (invalid JSON / parseable-but-wrong-shape / schema-valid), the certified-gap
   distributions, translation accuracy, verdict-level repeat agreement, and the
   guard-value-against-proposer-strength comparison (C1/C2 evidence) that the
   hosted arms complete by adding the capability axis above the local models.
2. EXPECTED RESULT.  M_constrained parses at or near 100% (provider-side
   enforcement); M_free shows a nonzero malformed or wrong-shape share, and that
   difference is the constraint-tax numerator.  The two repeats agree on most
   items; the disagreement rate is the API-nondeterminism number and is reported
   either way.  A crash, an empty log, or a systematic HTTP error is the only
   failing state, and none of those needs a second paid pass to diagnose.
3. CONTAMINATION.  The raw log is append-only, flushed per row, and keyed by
   (mode, thinking, repeat, item_id): a restart skips completed keys and never
   overwrites, so no earlier result file is read or rewritten.  Rows whose
   outcome is an API error are not counted as complete and are retried on the
   next run; the last row for a key is the one that counts.  A log written by
   another arm or another prompt version is refused.  Wall time here is a
   network measurement, not a compute measurement, and is labelled as such.
   Log: {log}
4. DATA ACCURACY.  Fatal assertions before the first call: the suite file's
   SHA-256 and the frozen schema's SHA-256 (the gate's own assertions); the
   prompt is the unchanged {version} build_messages render at top_k 10; for every
   item the (prefix, tail) split concatenates back to that exact render, the
   split prompt's fingerprint equals the unsplit one, and, when the local 14B log
   is present, both equal the local arm's logged prompt_hash.  The word "json" is
   asserted present in the system prompt for the JSON-object arm.
================================================================================""".format(
        arm=arm.arm, model=arm.model, labels=labels, modes=modes, repeats=repeats, log=log_path,
        version=PROMPT_VERSION)


def print_plan(arm: Arm, args, stats: dict, plan: list, done: set, log_path: Path,
               resume: tuple) -> None:
    backend = BACKENDS[arm.backend]
    anthropic = backend.wire == WIRE_ANTHROPIC
    rows, errors, broken = resume
    print("\nCALL PLAN  (arm {}, model {}, wire {})".format(
        arm.arm, arm.model, backend.wire))
    print("  items            : {} (suite v0.2, full)".format(stats["items"]))
    print("  groups           : {} (instance x frozen_seed); the first call of each "
          "runs alone to warm the cache".format(stats["groups"]))
    print("  distinct prefixes: {} per pass (a group can hold several: the items that "
          "name no order split later)".format(stats["cache_writes_per_pass"]))
    print("  enforcement      : M_constrained = {}, M_free = {}".format(
        backend.constrained, ENF_NONE))
    print("  thinking         : {}".format("; ".join(
        "{} -> {}".format(label_text(lab), json.dumps(body) if body else "no field sent")
        for lab, body in arm.thinking)))
    print("  max_tokens       : {} | temperature: {} | seed: none".format(
        args.max_tokens,
        "never sent (anthropic wire)" if anthropic else "client default 0.0"))
    print("  workers          : {} | timeout {:.0f}s | max_retries {}".format(
        args.workers, args.timeout_s, args.max_retries))
    print("  log              : {}".format(log_path))

    print("\n  {:<14s} {:<12s} {:>8s} {:>8s} {:>10s}".format(
        "mode", "thinking", "repeats", "items", "calls"))
    total = 0
    for mode in arm.modes:
        for label, _ in arm.thinking:
            calls = stats["items"] * args.repeats
            total += calls
            print("  {:<14s} {:<12s} {:>8d} {:>8d} {:>10d}".format(
                mode, label_text(label), args.repeats, stats["items"], calls))
    print("  {:<14s} {:<12s} {:>8s} {:>8s} {:>10d}".format("TOTAL", "", "", "", total))
    if args.limit:
        print("  --limit {}: the plan is truncated to its first {} calls (smoke run)"
              .format(args.limit, args.limit))
    print("\n  already logged   : {} rows, {} of them API errors{}".format(
        rows, errors, ", {} torn lines skipped".format(broken) if broken else ""))
    print("  complete keys    : {} | this run would make {} calls".format(
        len(done), len(plan)))


def print_projection(arm: Arm, args, stats: dict) -> None:
    anthropic = BACKENDS[arm.backend].wire == WIRE_ANTHROPIC
    label, base = arm.prices[0]
    print("\nPROJECTED COST  ({} prices, retrieved {}; {})".format(
        label, arm.price_date, arm.price_source))
    print("  token model : {:.2f} chars per token and the pilot's output tokens per "
          "call, both measured".format(arm.chars_per_token))
    print("  pilot source: {}".format(arm.pilot_note))
    print("\n  {:<26s} {:>7s} {:>10s} {:>10s} {:>9s} {:>10s} {:>10s} {:>10s}".format(
        "config", "calls", "in-uncach", "cache-read", "cache-wr",
        "USD pilot", "USD 3x out", "USD max"))
    totals = [0.0, 0.0, 0.0]
    grand_calls = 0
    for mode in arm.modes:
        for lab, _ in arm.thinking:
            pilot_out = arm.out_tokens[lab]
            cells = [project_pass(arm, stats, mode, out, base, anthropic)
                     for out in (pilot_out, 3 * pilot_out, args.max_tokens)]
            calls = cells[0]["calls"] * args.repeats
            grand_calls += calls
            usd = [c["usd"] * args.repeats for c in cells]
            for i in range(3):
                totals[i] += usd[i]
            print("  {:<26s} {:>7d} {:>10.0f} {:>10.0f} {:>9.0f} {:>10.2f} {:>10.2f} "
                  "{:>10.2f}".format(
                      "{}/{}".format(mode, label_text(lab)), calls,
                      cells[0]["uncached"] * args.repeats,
                      cells[0]["read"] * args.repeats,
                      cells[0]["write"] * args.repeats, usd[0], usd[1], usd[2]))
    print("  {:<26s} {:>7d} {:>10s} {:>10s} {:>9s} {:>10.2f} {:>10.2f} {:>10.2f}".format(
        "ARM TOTAL", grand_calls, "", "", "", *totals))
    for extra_label, extra_base in arm.prices[1:]:
        alt = sum(project_pass(arm, stats, mode, arm.out_tokens[lab], extra_base,
                               anthropic)["usd"] * args.repeats
                  for mode in arm.modes for lab, _ in arm.thinking)
        print("  the same plan at the {} base: USD {:.2f} at pilot output".format(
            extra_label, alt))
    per_100 = grand_calls * 100 * base["out"]
    print("  output sensitivity: every extra 100 output tokens per call adds USD {:.2f} "
          "to this arm.".format(per_100))
    print("  scenarios: 'pilot' uses the pilot's measured output tokens per call; "
          "'3x out' covers\n  the longer E1 prompts (the local 14B arm answered this "
          "suite with ~50 completion\n  tokens per call against 13.5 in the DeepSeek "
          "pilot); 'max' is the ceiling, every\n  call hitting max_tokens={} (a bound, "
          "not a forecast).".format(args.max_tokens))


# --------------------------------------------------------------------------- #
# The run                                                                      #
# --------------------------------------------------------------------------- #
class _FailedCall:
    """The shape of a ChatResponse, for an exception the client did not catch."""

    def __init__(self, model: str, error: str):
        self.text = None
        self.outcome = OUTCOME_ERROR
        self.model = model
        self.finish_reason = None
        self.usage = {}
        self.error = error


def make_row(arm: Arm, call: dict, resp, latency_ms: float, backend) -> dict:
    prep = call["prep"]
    item = prep.item
    return {
        "item_id": item["item_id"],
        "primary_class": item["primary_class"],
        "subclass": item["subclass"],
        "twin_id": item["twin_id"],
        "twin_role": item["twin_role"],
        "quality_visible_candidate": item.get("quality_visible_candidate"),
        "instance_id": item["instance"]["instance_id"],
        "instance_path": prep.instance_path,
        "stratum": item["instance"]["stratum"],
        "rule": item["episode"]["rule"],
        "dispatch_seed": item["episode"]["seed"],
        "frozen_seed": list(item["episode"]["frozen_seed"]),
        "gold_ops": item["gold_ops"],
        "trap_ops": item["trap_ops"],
        "instruction": item["instruction"],
        "prompt_hash": prep.prompt_hash,
        "prompt_version": PROMPT_VERSION,
        "model": arm.model,
        "model_reported": resp.model,
        "arm": arm.arm,
        "mode": call["mode"],
        "thinking": call["thinking"],
        "repeat": call["repeat"],
        "backend": backend.constrained if call["mode"] == M_CONSTRAINED else ENF_NONE,
        "raw_output": resp.text,
        "finish_reason": resp.finish_reason,
        "outcome": resp.outcome,
        "api_error": resp.error,
        "latency_ms": latency_ms,
        "usage": resp.usage,
    }


def one_call(client: ChatClient, arm: Arm, call: dict, kwargs: dict, backend) -> dict:
    """One API call; never raises, so one bad item cannot kill a pass."""
    prep = call["prep"]
    started = time.perf_counter()
    try:
        resp = client.complete(
            SYSTEM_PROMPT, (prep.prefix, prep.tail), mode=call["mode"], **kwargs)
    except Exception as exc:  # noqa: BLE001 - the row records it and the key retries
        resp = _FailedCall(arm.model, "{}: {}".format(type(exc).__name__, exc))
    return make_row(arm, call, resp, (time.perf_counter() - started) * 1000.0, backend)


def split_into_passes(plan: list) -> list:
    """The remaining plan as ``[((mode, thinking, repeat), [(group, [calls])])]``.

    The first survivor of a group is its warm call, whether or not it was the
    group's original first item: after a restart the provider cache is cold
    anyway, so the warm call is simply the first one this run makes.
    """
    passes: list = []
    for call in plan:
        key = (call["mode"], call["thinking"], call["repeat"])
        if not passes or passes[-1][0] != key:
            passes.append((key, []))
        groups = passes[-1][1]
        if not groups or groups[-1][0] != call["prep"].group:
            groups.append((call["prep"].group, []))
        groups[-1][1].append(call)
    return passes


def run(arm: Arm, args, plan: list, log_path: Path, client: ChatClient) -> dict:
    """Execute the plan: a warm call per group, a pool for the rest, one writer.

    Ctrl-C stops after the current group and still returns what the session
    spent and wrote, because a paid run that is interrupted must not lose its
    own accounting; every row already written stays valid and its key is
    skipped on the next run.
    """
    backend = BACKENDS[arm.backend]
    base = arm.prices[0][1]
    tally: dict = {}
    started_all = time.perf_counter()
    written = 0
    interrupted = False
    passes = split_into_passes(plan)

    with open(log_path, "a", encoding="utf-8") as fh:
        def write(row: dict) -> None:
            nonlocal written
            fh.write(json.dumps(row, sort_keys=True) + "\n")
            fh.flush()
            written += 1
            cell = tally.setdefault(
                (row["mode"], row["thinking"], row["repeat"]),
                {"calls": 0, "ok": 0, "error": 0, "other": 0, "usd": 0.0,
                 "out_tokens": 0, "latency_ms": 0.0})
            cell["calls"] += 1
            if row["outcome"] == OUTCOME_OK:
                cell["ok"] += 1
            elif row["outcome"] == OUTCOME_ERROR:
                cell["error"] += 1
            else:
                cell["other"] += 1
            cell["usd"] += call_usd(base, row["usage"] or {})
            cell["out_tokens"] += (row["usage"] or {}).get("completion_tokens") or 0
            cell["latency_ms"] += row["latency_ms"]

        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            try:
                for index, ((mode, label, repeat), groups) in enumerate(passes, 1):
                    kwargs = {"max_tokens": args.max_tokens}
                    body = thinking_body(arm, label)
                    if body:
                        kwargs["extra_body"] = body
                    print("\n[e1h] pass {}/{}  {} thinking={} r{}  ({} groups, {} calls)"
                          .format(index, len(passes), mode, label_text(label), repeat,
                                  len(groups), sum(len(m) for _, m in groups)), flush=True)
                    for g, (group_key, members) in enumerate(groups, 1):
                        write(one_call(client, arm, members[0], kwargs, backend))
                        futures = [pool.submit(one_call, client, arm, c, kwargs, backend)
                                   for c in members[1:]]
                        for future in as_completed(futures):
                            write(future.result())
                        cell = tally[(mode, label, repeat)]
                        print("  group {:>3d}/{:<3d} {:<32s} n={:<3d} done={:<5d} "
                              "ok={:<5d} err={:<3d} usd={:>7.3f} elapsed={:.0f}s".format(
                                  g, len(groups), Path(group_key[0]).name, len(members),
                                  cell["calls"], cell["ok"], cell["error"], cell["usd"],
                                  time.perf_counter() - started_all), flush=True)
                    cell = tally[(mode, label, repeat)]
                    print("[e1h] pass done: {} calls, {} ok, {} error, {} other, {} "
                          "output tokens, USD {:.3f}, {:.0f} ms mean per call".format(
                              cell["calls"], cell["ok"], cell["error"], cell["other"],
                              cell["out_tokens"], cell["usd"],
                              cell["latency_ms"] / max(1, cell["calls"])), flush=True)
            except KeyboardInterrupt:
                interrupted = True
                print("\n[e1h] INTERRUPTED after {} rows; waiting for the calls already "
                      "in flight, then stopping.".format(written), flush=True)
    return {"written": written, "tally": tally, "interrupted": interrupted,
            "wall_s": time.perf_counter() - started_all}


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arm", required=True, choices=sorted(ARMS))
    ap.add_argument("--out", default=None,
                    help="output dir (default results/grid_e1_hosted_<arm>)")
    ap.add_argument("--limit", type=int, default=0,
                    help="cap the plan to its first N CALLS (smoke runs)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--repeats", type=int, default=REPEATS)
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--top-k", type=int, default=TOP_K)
    ap.add_argument("--timeout-s", type=float, default=240.0)
    ap.add_argument("--max-retries", type=int, default=4,
                    help="per call, on 429/5xx (529 too on the anthropic wire)")
    ap.add_argument("--mock", action="store_true",
                    help="offline transport for both wires: no network, no key")
    ap.add_argument("--mock-fail-every", type=int, default=0,
                    help="mock only: return a terminal HTTP 400 every N calls, to "
                         "exercise the error and resume path")
    ap.add_argument("--mock-dump-bodies", action="store_true",
                    help="mock only: write the first request body of each "
                         "configuration to mock_bodies.json in the output dir")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan and the cost projection, call nothing")
    args = ap.parse_args()

    arm = ARMS[args.arm]
    backend = BACKENDS[arm.backend]
    out_dir = Path(args.out) if args.out else (
        sg.CODE_DIR.parent / "results" / "grid_e1_hosted_{}".format(arm.arm))
    log_path = out_dir / "proposals_raw.jsonl"

    print(launch_questions(arm, args.repeats, log_path))

    inputs = sg.assert_inputs()
    print("[e1h] suite sha256  {} OK".format(inputs["suite_sha256"]))
    print("[e1h] schema sha256 {} OK".format(inputs["schema_sha256"]))
    if backend.requires_json_word:
        if "json" not in SYSTEM_PROMPT.lower():
            raise SystemExit(
                "REFUSING TO RUN: {} JSON-object mode needs the word 'json' in the "
                "prompt, and the frozen system prompt does not contain it".format(
                    arm.backend))
        print("[e1h] the frozen system prompt contains the word 'json' ({}x) OK".format(
            SYSTEM_PROMPT.lower().count("json")))

    items = sg.load_suite()
    instances = sg.Instances()
    started = time.perf_counter()
    prepared = prepare(items, instances, args.top_k)
    print("[e1h] {} prompts rendered and split in {:.1f}s ({} at the orders boundary, "
          "{} at the instruction)".format(
              len(prepared), time.perf_counter() - started,
              sum(1 for p in prepared if p.split_at == "orders"),
              sum(1 for p in prepared if p.split_at == "instruction")))
    print("[e1h] split and fingerprint asserted on every item: prefix+tail is the "
          "unchanged render, and the split leaves prompt_fingerprint unchanged")
    print("[e1h] {}".format(crosscheck_local(prepared, LOCAL_LOG)))

    stats = prompt_stats(prepared, len(SYSTEM_PROMPT))
    done, rows, errors, broken = read_completed(log_path, arm)
    plan = [c for c in build_plan(arm, prepared, args.repeats, args.limit)
            if row_key(c["mode"], c["thinking"], c["repeat"],
                       c["prep"].item["item_id"]) not in done]
    print_plan(arm, args, stats, plan, done, log_path, (rows, errors, broken))
    print_projection(arm, args, stats)

    if args.dry_run:
        print("\nNO CALL MADE (--dry-run).")
        return 0
    if not plan:
        print("\nNothing to do: every planned key is already logged.")
        return 0

    transport = None
    api_key = None
    if args.mock:
        transport = MockTransport(arm, fail_every=args.mock_fail_every)
        api_key = "mock-key-not-a-real-key"
        print("\n[e1h] MOCK TRANSPORT: no network, no key, no cost.")
    else:
        loaded = load_env()
        if not os.environ.get(backend.api_key_env):
            print("\nREFUSING TO RUN: {} is not set ({} names loaded from the project "
                  ".env).".format(backend.api_key_env, len(loaded)))
            return 2
        print("\n[e1h] key {} present (never printed).".format(backend.api_key_env))

    out_dir.mkdir(parents=True, exist_ok=True)
    client = ChatClient(
        arm.backend,
        model=arm.model,
        api_key=api_key,
        max_tokens=args.max_tokens,
        timeout_s=args.timeout_s,
        max_retries=args.max_retries,
        retry_sleep_s=0.0 if args.mock else 2.0,
        transport=transport,
    )

    try:
        result = run(arm, args, plan, log_path, client)
    except KeyboardInterrupt:  # a second Ctrl-C, or one outside the run loop
        result = {"written": None, "tally": {}, "interrupted": True, "wall_s": None}
    interrupted = bool(result.get("interrupted"))
    if interrupted:
        print("\n[e1h] INTERRUPTED: the log is append-only and flushed per row; "
              "re-run the same command to resume from the last completed key.")

    if args.mock and args.mock_dump_bodies:
        first: dict = {}
        for body in transport.bodies:
            key = "{}|{}".format(
                "M_constrained" if ("response_format" in body or "output_config" in body)
                else "M_free",
                json.dumps(body.get("thinking")) if "thinking" in body
                else "no-thinking-field")
            first.setdefault(key, body)
        (out_dir / "mock_bodies.json").write_text(json.dumps(first, indent=1))
        print("[e1h] first request body per configuration: {}".format(
            out_dir / "mock_bodies.json"))

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    meta = {
        "date": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "arm": arm.arm, "model": arm.model, "backend": arm.backend,
        "wire": backend.wire, "modes": list(arm.modes),
        "thinking": [lab for lab, _ in arm.thinking],
        "thinking_bodies": {str(lab): body for lab, body in arm.thinking},
        "repeats": args.repeats, "items": stats["items"], "groups": stats["groups"],
        "cache_prefixes_per_pass": stats["cache_writes_per_pass"],
        "max_tokens": args.max_tokens, "workers": args.workers,
        "timeout_s": args.timeout_s, "max_retries": args.max_retries,
        "suite_sha256": inputs["suite_sha256"],
        "schema_sha256": inputs["schema_sha256"],
        "prompt_version": PROMPT_VERSION, "top_k": args.top_k,
        "cache_boundary": CACHE_BOUNDARY,
        "cache_boundary_fallback": CACHE_BOUNDARY_FALLBACK,
        "mock": bool(args.mock), "interrupted": interrupted,
        "planned_calls": len(plan), "rows_written": result["written"],
        "wall_s": result["wall_s"],
        "price_base": arm.prices[0][0], "price_date": arm.price_date,
        "usd_estimated": sum(c["usd"] for c in result["tally"].values()),
        "per_config": {"{}|{}|r{}".format(m, t, r): v
                       for (m, t, r), v in result["tally"].items()},
        "dedupe_rule": "last row per (arm, mode, thinking, repeat, item_id) wins; an "
                       "earlier row for a key is a superseded API error",
    }
    meta_path = out_dir / "run_meta_{}.json".format(stamp)
    meta_path.write_text(json.dumps(meta, indent=1, default=str))
    print("\n[e1h] raw log : {}".format(log_path))
    print("[e1h] meta    : {}".format(meta_path))
    if not args.mock:
        print("[e1h] estimated spend this session: USD {:.2f} ({} base, retrieved {})"
              .format(meta["usd_estimated"], arm.prices[0][0], arm.price_date))
    elif args.mock_fail_every:
        print("[e1h] the mock injected {} terminal errors".format(
            sum(c["error"] for c in result["tally"].values())))
    return 130 if interrupted else 0


if __name__ == "__main__":
    sys.exit(main())
