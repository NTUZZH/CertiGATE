#!/usr/bin/env python
"""Anthropic billing pilot: 53 calls on ``claude-sonnet-5``, then the grid cost table.

The key is loaded explicitly from the git-ignored project ``.env`` by
``_envfile.load_env`` (never from a shell profile - an exported
``ANTHROPIC_API_KEY`` would hijack this machine's Claude Code login).  Without a
key the runner prints the plan and exits 2; ``--dry-run`` prints the plan.

Anthropic's wire is NOT OpenAI-compatible, and the grid client for this arm is
written only after this pilot has pinned the shapes empirically.  The pilot
therefore carries its own minimal request builder over the native
``POST /v1/messages`` endpoint (shapes from the claude-api skill, retrieved
2026-08-11):

* strict structured outputs: ``output_config = {"format": {"type":
  "json_schema", "schema": <frozen schema>}}`` (GA, no beta header; only
  ``$schema``/``$id`` stripped in transport);
* prompt caching: ``cache_control: {"type": "ephemeral"}`` on the last stable
  block; hits come back in ``usage.cache_read_input_tokens``, writes in
  ``usage.cache_creation_input_tokens``.  The user text is split into two
  blocks at the cache boundary (state prefix | instruction); the concatenated
  text is byte-identical to the other arms' single-string prompt, and the
  provider-side block separator, if any, is recorded as a pilot finding;
* the 5-series takes no ``temperature`` - probe 1 confirms the rejection on
  the wire so the grid client omits it as a recorded fact, not an assumption;
* thinking: probe 2 sends ``thinking: {"type": "disabled"}``; probe 3 omits
  the field and inspects the returned block types, so the snapshot's default
  (adaptive or off) is measured, not assumed.  Main blocks run with whichever
  non-thinking shape the probes accepted.

Call plan (53 calls)
--------------------
    probes  temperature=0 / thinking-disabled / default-thinking      =  3
    warm    10 instructions x {constrained, free} x 2 repeats         = 40
    cold    10 instructions x constrained on a second instance        = 10

Every response passes through the guard and is appended to the proposal log.

Run::

    python scripts/anthropic_pilot.py --out results/   # key comes from .env
    python scripts/anthropic_pilot.py --dry-run        # plan only, no network
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _envfile import load_env  # noqa: E402
from deepseek_pilot import (  # noqa: E402
    INSTRUCTIONS,
    SYSTEM_PROMPT,
    pick_targets,
)
from l1adapter import dispatch, instances, state  # noqa: E402
from l1guard import G_CERT, evaluate_proposal  # noqa: E402
from l1guard.logging import (  # noqa: E402
    OUTCOME_EMPTY_CONTENT,
    OUTCOME_ERROR,
    OUTCOME_OK,
    OUTCOME_REFUSAL,
    ProposalLog,
    ProposalRecord,
    prompt_hash,
)
from l1guard.models import M_CONSTRAINED, M_FREE, urllib_transport  # noqa: E402
from l1adapter.ops import SCHEMA as FROZEN_SCHEMA  # noqa: E402

MODEL = "claude-sonnet-5"
API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

#: Prices per token, retrieved 2026-08-11.  Two bases: the launch-intro price
#: (in force through 2026-08-31) and the standard price after it.  Cache reads
#: bill at 10% of base input, 5-minute cache writes at 125%.
SONNET_PRICES = {
    "intro (through 2026-08-31)": {
        "in": 2.00 / 1e6, "cache_read": 0.20 / 1e6,
        "cache_write": 2.50 / 1e6, "out": 10.00 / 1e6,
    },
    "standard (from 2026-09-01)": {
        "in": 3.00 / 1e6, "cache_read": 0.30 / 1e6,
        "cache_write": 3.75 / 1e6, "out": 15.00 / 1e6,
    },
}
OPUS_PRICES = {
    "list ($5/$25)": {
        "in": 5.00 / 1e6, "cache_read": 0.50 / 1e6,
        "cache_write": 6.25 / 1e6, "out": 25.00 / 1e6,
    },
}
PRICES_BY_MODEL = {"claude-sonnet-5": SONNET_PRICES, "claude-opus-5": OPUS_PRICES}
PRICES = SONNET_PRICES  # rebound in main() from --model
PRICE_DATE = "2026-08-11"

LAUNCH_QUESTIONS = """\
================================================================================
FOUR LAUNCH QUESTIONS (global CLAUDE.md experiment rules) - answered before the
first paid call
================================================================================
1. PURPOSE.  What does one claude-sonnet-5 call cost in this task (uncached
   input, cache read/write, output), does output_config accept the frozen
   schema with its integer enum, is temperature really rejected, and what is
   the snapshot's default thinking behaviour?  The numbers set the E1/E3 call
   budgets against the SGD 600 cap; the probes pin the grid client's request
   shape.
2. EXPECTED RESULT.  output_config accepts the schema (the official strict-
   tool example carries an integer enum); temperature returns a 400;
   thinking-disabled is accepted.  Warm calls after the first should show
   cache_read_input_tokens near the shared prefix size (~2k tokens; the
   5-minute ephemeral window is refreshed every call).  Sonnet's tokenizer
   runs ~30% heavier than Qwen's on the same text, and that shows up here.
   If output_config rejects the schema, the finding goes to decisions.md and
   the arm design is revisited before any grid.
3. CONTAMINATION.  53 calls, one JSONL log, append-only; no checkpoint and no
   earlier result file read or overwritten.  The two instances are read-only.
   Wall time is a network measurement and is labelled as such.
4. DATA ACCURACY.  Prompts are built from the same state_slice and the same
   ten instructions as the DeepSeek and OpenAI pilots on the same two
   instances; every response passes through the guard and is logged with the
   schema and config hashes, so verdicts replay.
================================================================================
"""


def strip_meta(schema: dict) -> dict:
    schema = dict(schema)
    for key in ("$schema", "$id"):
        schema.pop(key, None)
    return schema


def build_prompt_parts(inst, targets, template: str) -> tuple:
    """The DeepSeek pilot's prompt, split at the cache boundary.

    ``prefix + instruction`` concatenates to exactly the string the other
    pilots send as their single user message.
    """
    slice_json = json.dumps(state.state_slice(inst, top_k=25), sort_keys=True)
    prefix = (
        "Site state (json):\n{}\n\n"
        "Answer for this site only. Use only the work order ids and trade codes "
        "shown above.\n\nInstruction: ".format(slice_json)
    )
    return prefix, template.format(**targets)


def build_body(prefix: str, instruction: str, mode: str, max_tokens: int,
               thinking: dict | None, temperature: float | None) -> dict:
    body = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": [{"type": "text", "text": SYSTEM_PROMPT}],
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prefix,
                 "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": instruction},
            ],
        }],
    }
    if thinking is not None:
        body["thinking"] = thinking
    if temperature is not None:
        body["temperature"] = temperature
    if mode == M_CONSTRAINED:
        body["output_config"] = {
            "format": {"type": "json_schema", "schema": strip_meta(FROZEN_SCHEMA)}
        }
    return body


def anthropic_call(key: str, body: dict, timeout_s: float = 240.0,
                   max_retries: int = 2) -> tuple:
    """POST /v1/messages with retry on 429/5xx; returns (status, payload, wall_ms)."""
    headers = {
        "Content-Type": "application/json",
        "x-api-key": key,
        "anthropic-version": API_VERSION,
    }
    blob = json.dumps(body).encode("utf-8")
    attempt = 0
    while True:
        started = time.perf_counter()
        try:
            status, raw = urllib_transport("POST", API_URL, headers, blob, timeout_s)
        except ConnectionError as exc:
            wall = (time.perf_counter() - started) * 1000.0
            if attempt < max_retries:
                attempt += 1
                time.sleep(2.0 * attempt)
                continue
            return None, {"error": {"message": str(exc)}}, wall
        wall = (time.perf_counter() - started) * 1000.0
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            payload = {"error": {"message": "unparseable body: {}".format(exc)}}
        if status in (429, 500, 502, 503, 529) and attempt < max_retries:
            attempt += 1
            time.sleep(2.0 * attempt)
            continue
        return status, payload, wall


def parse_response(status, payload: dict) -> dict:
    """Normalise one Anthropic response into the pilot's record fields."""
    if status is None or status >= 400 or payload.get("type") == "error":
        err = (payload.get("error") or {})
        return {"outcome": OUTCOME_ERROR, "text": None, "finish": None,
                "error": "HTTP {}: {}".format(status, err.get("message")),
                "usage": {}, "blocks": []}
    content = payload.get("content") or []
    blocks = [b.get("type") for b in content]
    text = next((b.get("text") for b in content if b.get("type") == "text"), None)
    stop = payload.get("stop_reason")
    u = payload.get("usage") or {}
    cache_read = u.get("cache_read_input_tokens") or 0
    cache_write = u.get("cache_creation_input_tokens") or 0
    uncached = u.get("input_tokens") or 0
    usage = {
        "prompt_tokens": uncached + cache_read + cache_write,
        "completion_tokens": u.get("output_tokens"),
        "total_tokens": None,
        "reasoning_tokens": None,  # thinking bills inside output_tokens
        "cache_hit_tokens": cache_read,
        "cache_miss_tokens": uncached + cache_write,
        "cache_hit": bool(cache_read),
        "cache_write_tokens": cache_write,
    }
    if stop == "refusal":
        return {"outcome": OUTCOME_REFUSAL, "text": text, "finish": stop,
                "error": "stop_reason=refusal", "usage": usage, "blocks": blocks}
    if text is None or text.strip() == "":
        return {"outcome": OUTCOME_EMPTY_CONTENT, "text": "" if text is None else text,
                "finish": stop, "error": None, "usage": usage, "blocks": blocks}
    return {"outcome": OUTCOME_OK, "text": text, "finish": stop, "error": None,
            "usage": usage, "blocks": blocks}


def cost(usage: dict, out_tokens: int, base: dict) -> float:
    return (usage["uncached"] * base["in"]
            + usage["cache_read"] * base["cache_read"]
            + usage["cache_write"] * base["cache_write"]
            + out_tokens * base["out"])


def call_plan(warm_path, cold_path, repeats: int) -> list:
    plan = [
        {"block": "probe_temperature", "path": warm_path, "mode": M_FREE,
         "instruction_id": INSTRUCTIONS[0][0], "template": INSTRUCTIONS[0][1]},
        {"block": "probe_thinking_disabled", "path": warm_path, "mode": M_FREE,
         "instruction_id": INSTRUCTIONS[0][0], "template": INSTRUCTIONS[0][1]},
        {"block": "probe_default_thinking", "path": warm_path, "mode": M_FREE,
         "instruction_id": INSTRUCTIONS[0][0], "template": INSTRUCTIONS[0][1]},
    ]
    for repeat in range(repeats):
        for mode in (M_CONSTRAINED, M_FREE):
            for iid, template in INSTRUCTIONS:
                plan.append({"block": "warm", "path": warm_path, "mode": mode,
                             "instruction_id": iid, "template": template,
                             "repeat": repeat})
    for iid, template in INSTRUCTIONS:
        plan.append({"block": "cold", "path": cold_path, "mode": M_CONSTRAINED,
                     "instruction_id": iid, "template": template, "repeat": 0})
    return plan


def main() -> int:
    global MODEL, PRICES
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print the plan, call nothing")
    ap.add_argument("--model", default=MODEL,
                    help="Anthropic model id (v3.7 reuses this pilot for claude-opus-5; "
                         "use a separate --out dir so the sonnet artifacts stay intact)")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--out", default="results")
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--e1-calls", type=int, default=2000,
                    help="E1 stratified core: ~1000 items x 2 enforcement modes x 1 repeat")
    ap.add_argument("--e3-calls", type=int, default=1000,
                    help="E3 reduced: 500 instructions x 2 repeats (single-agent point)")
    args = ap.parse_args()
    MODEL = args.model
    try:
        PRICES = PRICES_BY_MODEL[MODEL]
    except KeyError:
        raise SystemExit(
            "no price table for {}; add it to PRICES_BY_MODEL before running".format(MODEL))

    print(LAUNCH_QUESTIONS)

    warm_path = instances.list_instances(9, "storm2")[0]
    cold_path = instances.list_instances(10, "replay", "150")[0]
    warm = instances.load_instance(warm_path)
    cold = instances.load_instance(cold_path)
    plan = call_plan(warm_path, cold_path, args.repeats)

    print("CALL PLAN")
    print("  model            : {} (no dated snapshot exists; pin the access window)"
          .format(MODEL))
    print("  warm instance    : {} ({} orders)".format(warm_path.name, len(warm["work_orders"])))
    print("  cold instance    : {} ({} orders)".format(cold_path.name, len(cold["work_orders"])))
    print("  calls            : 3 probes + {} warm + {} cold = {}".format(
        sum(1 for c in plan if c["block"] == "warm"),
        sum(1 for c in plan if c["block"] == "cold"), len(plan)))
    print("  enforcement      : M_constrained = output_config json_schema "
          "(frozen schema verbatim, integer enum included)")
    for label, base in PRICES.items():
        print("  prices {:<28s}: ${}/M in, ${}/M cache-read, ${}/M cache-write, ${}/M out"
              .format(label, base["in"] * 1e6, base["cache_read"] * 1e6,
                      base["cache_write"] * 1e6, base["out"] * 1e6))

    load_env()
    key = os.environ.get("ANTHROPIC_API_KEY")
    if args.dry_run or not key:
        print("\nNO CALL MADE ({}).".format(
            "--dry-run" if args.dry_run else "ANTHROPIC_API_KEY is not set"))
        return 0 if args.dry_run else 2

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    log = ProposalLog(out_dir / "anthropic_pilot.jsonl")
    loaded = {str(warm_path): warm, str(cold_path): cold}
    baselines = {}
    rows = []
    empty = 0
    probes = {"temperature_rejected": None, "thinking_disabled_accepted": None,
              "default_blocks": None, "schema_accepted": None,
              "block_separator_note": "user text split prefix|instruction at the "
                                      "cache boundary"}
    thinking_main = {"type": "disabled"}  # revised by probe 2 if rejected

    for i, call in enumerate(plan, 1):
        inst = loaded[str(call["path"])]
        prefix, instruction = build_prompt_parts(inst, pick_targets(inst), call["template"])
        thinking = thinking_main
        temperature = None
        if call["block"] == "probe_temperature":
            thinking, temperature = None, 0.0
        elif call["block"] == "probe_default_thinking":
            thinking = None

        status, payload, wall_ms = anthropic_call(
            key, build_body(prefix, instruction, call["mode"], args.max_tokens,
                            thinking, temperature))
        parsed = parse_response(status, payload)

        if call["block"] == "probe_temperature":
            probes["temperature_rejected"] = parsed["outcome"] == OUTCOME_ERROR
            print("  probe: temperature=0 -> {} ({})".format(
                "REJECTED as researched" if probes["temperature_rejected"]
                else "ACCEPTED (update the model notes!)",
                (parsed["error"] or "HTTP {}".format(status))[:140]))
        elif call["block"] == "probe_thinking_disabled":
            ok = parsed["outcome"] != OUTCOME_ERROR
            probes["thinking_disabled_accepted"] = ok
            print("  probe: thinking disabled -> {}".format(
                "accepted" if ok else "REJECTED: {}".format((parsed["error"] or "")[:140])))
            if not ok:
                thinking_main = None  # omit the field; record the default instead
        elif call["block"] == "probe_default_thinking":
            probes["default_blocks"] = parsed["blocks"]
            print("  probe: default (no thinking field) -> blocks {} out={}".format(
                parsed["blocks"], parsed["usage"].get("completion_tokens")))

        if call["mode"] == M_CONSTRAINED and probes["schema_accepted"] is None:
            probes["schema_accepted"] = parsed["outcome"] != OUTCOME_ERROR
            if parsed["outcome"] == OUTCOME_ERROR:
                print("  probe: OUTPUT_CONFIG SCHEMA REJECTED: {}".format(
                    (parsed["error"] or "")[:300]))

        if parsed["outcome"] == OUTCOME_EMPTY_CONTENT:
            empty += 1
        if str(call["path"]) not in baselines:
            baselines[str(call["path"])] = dispatch.dispatch_baseline(inst, "atc", seed=0)
        verdict = evaluate_proposal(
            inst, parsed["text"] if parsed["text"] is not None else "", G_CERT,
            baseline_schedule=baselines[str(call["path"])],
        )
        usage = parsed["usage"]
        record = ProposalRecord(
            instruction_id="{}-{}-{}-r{}".format(
                call["instruction_id"], call["block"], call["mode"],
                call.get("repeat", 0)),
            instance_id=inst["meta"]["id"],
            instance_path=str(call["path"]),
            model=MODEL,
            mode="{}/{}".format(call["mode"],
                                "think_disabled" if thinking else "think_default"),
            prompt_hash=prompt_hash(SYSTEM_PROMPT, prefix + instruction),
            raw_output=parsed["text"],
            outcome=parsed["outcome"],
            finish_reason=parsed["finish"],
            latency_ms=wall_ms,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            reasoning_tokens=usage.get("reasoning_tokens"),
            cache_hit_tokens=usage.get("cache_hit_tokens"),
            cache_miss_tokens=usage.get("cache_miss_tokens"),
            cache_hit=usage.get("cache_hit"),
            api_error=parsed["error"],
            rule="atc",
        ).attach_verdict(verdict)
        log.append(record)
        rows.append({**{k: v for k, v in call.items() if k != "template"},
                     "usage": usage, "outcome": parsed["outcome"],
                     "wall_ms": wall_ms, "terminal": verdict.terminal,
                     "blocks": parsed["blocks"]})
        print("  {:>3d}/{:<3d} {:<10s} {:<24s} {:<13s} out={:<6s} cache_r={:<6s} "
              "cache_w={:<6s} wall={:>7.0f} ms  {}".format(
                  i, len(plan), call["instruction_id"], call["block"], call["mode"],
                  str(usage.get("completion_tokens")),
                  str(usage.get("cache_hit_tokens")),
                  str(usage.get("cache_write_tokens")),
                  wall_ms, verdict.terminal), flush=True)

    summarise(rows, empty, probes, args, out_dir)
    return 0


def _median(values):
    values = [v for v in values if v is not None]
    return median(values) if values else 0


def summarise(rows, empty: int, probes: dict, args, out_dir: Path) -> None:
    print("\n" + "=" * 96)
    print("MEASURED PER-CALL USAGE")
    print("=" * 96)
    print("{:<26s} {:>4s} {:>10s} {:>10s} {:>10s} {:>11s}".format(
        "block/mode", "n", "prompt", "cache_r", "cache_w", "completion"))
    groups = {}
    for r in rows:
        groups.setdefault((r["block"], r["mode"]), []).append(r)
    per_call = {"uncached": 0, "cache_read": 0, "cache_write": 0}
    for key, sel in sorted(groups.items()):
        u = [r["usage"] for r in sel]
        prompt = _median([x.get("prompt_tokens") for x in u])
        cache_r = _median([x.get("cache_hit_tokens") for x in u])
        cache_w = _median([x.get("cache_write_tokens") for x in u])
        print("{:<26s} {:>4d} {:>10.0f} {:>10.0f} {:>10.0f} {:>11.0f}".format(
            "/".join(key), len(sel), prompt, cache_r, cache_w,
            _median([x.get("completion_tokens") for x in u])))
        if key[0] == "warm":
            per_call["cache_read"] = max(per_call["cache_read"], cache_r)
            per_call["uncached"] = max(
                per_call["uncached"], prompt - cache_r - cache_w)
            per_call["cache_write"] = max(per_call["cache_write"], cache_w)

    print("\nempty-content incidents    : {} / {} calls".format(empty, len(rows)))
    for name in ("temperature_rejected", "thinking_disabled_accepted",
                 "default_blocks", "schema_accepted"):
        print("{:<27s}: {}".format(name, probes[name]))
    print("median wall per call       : {:.0f} ms (network, not compute)".format(
        _median([r["wall_ms"] for r in rows])))

    grids = {"E1": args.e1_calls, "E2 (replay only)": 0, "E3": args.e3_calls}
    tables = {}
    for label, base in PRICES.items():
        print("\n" + "=" * 96)
        print("COST EXTRAPOLATION, {} prices (retrieved {})".format(label, PRICE_DATE))
        print("=" * 96)
        print("{:<20s} {:>8s} {:>16s} {:>14s} {:>14s}".format(
            "grid", "calls", "out tokens/call", "USD per call", "USD total"))
        table = []
        for grid, calls in grids.items():
            for out_tokens in (300, 800, 2000):
                unit = cost(per_call, out_tokens, base)
                table.append({"grid": grid, "calls": calls,
                              "output_tokens_per_call": out_tokens,
                              "usd_per_call": unit, "usd_total": unit * calls})
                print("{:<20s} {:>8d} {:>16d} {:>14.5f} {:>14.2f}".format(
                    grid, calls, out_tokens, unit, unit * calls))
        tables[label] = table
    payload = {"rows": rows, "per_call": per_call, "empty": empty, "probes": probes,
               "cost_tables": tables, "price_date": PRICE_DATE}
    (out_dir / "anthropic_pilot_summary.json").write_text(
        json.dumps(payload, indent=1, default=str))
    print("\nwritten to {}".format(out_dir / "anthropic_pilot_summary.json"))


if __name__ == "__main__":
    sys.exit(main())
