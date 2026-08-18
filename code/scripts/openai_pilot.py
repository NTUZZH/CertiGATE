#!/usr/bin/env python
"""OpenAI billing pilot: 41 calls on ``gpt-5.4-mini-2026-03-17``, then the grid cost table.

The key is loaded explicitly from the git-ignored project ``.env`` by
``_envfile.load_env`` (never from a shell profile).  Without a key the runner
prints the plan and exits 2; ``--dry-run`` prints the plan even with a key.

What the calls buy
------------------
The two open strict-mode questions from the model-pins research, answered on the
wire, plus the token profile the grid budget needs:

1. **Temperature acceptance.**  ``gpt-5.4-mini`` is reasoning-capable; whether it
   accepts ``temperature`` (the client sends 0.0 by default) is undocumented for
   this snapshot.  Probe call 1 sends it; on rejection the pilot registers
   ``temperature`` in the backend's ``drop_params`` and records the fact - the
   grid then runs without the field, as a configuration line, not an edit.
2. **The frozen schema under strict mode, integer enums included.**  The first
   M_constrained call sends the frozen schema verbatim (only ``$schema``/``$id``
   stripped).  ``priority_class`` is an integer enum; acceptance or a 400 here
   decides whether the M_constrained arm exists for this provider as designed.
3. **Token profile.**  Output tokens per call under reasoning effort ``none``
   vs the snapshot default, prompt caching behaviour on a shared instance-state
   prefix (OpenAI caches prefixes >= 1024 tokens automatically, billed at
   $0.075/M instead of $0.75/M), and the empty/refusal incidence.

Call plan (41 calls)
--------------------
    probe   1 x M_free, effort none, temperature as default        =  1
    warm   10 instructions x {constrained/none, constrained/default,
                              free/none}                           = 30
    cold   10 instructions x constrained/none on a second instance = 10

Every response passes through the guard and is appended to the proposal log, so
the pilot is also a real (tiny) run whose verdicts replay like any other.

Run::

    python scripts/openai_pilot.py --out results/   # key comes from .env
    python scripts/openai_pilot.py --dry-run        # plan only, no network
"""

from __future__ import annotations

import argparse
import dataclasses
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
    build_prompt,
    pick_targets,
)
from l1adapter import dispatch, instances  # noqa: E402
from l1guard import G_CERT, evaluate_proposal  # noqa: E402
from l1guard.logging import (  # noqa: E402
    OUTCOME_EMPTY_CONTENT,
    OUTCOME_ERROR,
    ProposalLog,
    ProposalRecord,
    prompt_hash,
)
from l1guard.models import BACKENDS, M_CONSTRAINED, M_FREE, ChatClient  # noqa: E402

MODEL = "gpt-5.4-mini-2026-03-17"

# Prices retrieved 2026-08-11 (re-verified 2026-08-12 live) from
# https://developers.openai.com/api/docs/pricing.  Reasoning tokens are billed
# inside completion_tokens, with the split in completion_tokens_details.
PRICES_BY_MODEL = {
    "gpt-5.4-mini-2026-03-17": {"in": 0.75 / 1e6, "cached": 0.075 / 1e6,
                                "out": 4.50 / 1e6},
    "gpt-5.6-terra": {"in": 2.00 / 1e6, "cached": 0.20 / 1e6, "out": 12.00 / 1e6},
    "gpt-5.6-sol": {"in": 5.00 / 1e6, "cached": 0.50 / 1e6, "out": 30.00 / 1e6},
}
PRICE_IN = PRICES_BY_MODEL[MODEL]["in"]
PRICE_IN_CACHED = PRICES_BY_MODEL[MODEL]["cached"]
PRICE_OUT = PRICES_BY_MODEL[MODEL]["out"]
PRICE_DATE = "2026-08-11"

#: (mode, reasoning_effort) cells of the warm block.  ``None`` effort = omit the
#: field and take the snapshot default, which is itself a measurement.
WARM_CELLS = (
    (M_CONSTRAINED, "none"),
    (M_CONSTRAINED, None),
    (M_FREE, "none"),
)

LAUNCH_QUESTIONS = """\
================================================================================
FOUR LAUNCH QUESTIONS (global CLAUDE.md experiment rules) - answered before the
first paid call
================================================================================
1. PURPOSE.  What does one gpt-5.4-mini call cost in this task (cached input,
   uncached input, output incl. reasoning), does the endpoint accept
   temperature, and does strict mode accept the frozen schema with its integer
   enum?  The numbers set the E1/E3 call budgets against the SGD 600 cap and
   the two probes decide the M_constrained arm's existence and request shape.
2. EXPECTED RESULT.  Strict mode accepts the schema (the docs' schema subset
   covers closed enums and additionalProperties:false; integer enums are the
   open point).  Effort-none calls should emit a few hundred output tokens;
   default-effort several times that.  The shared prefix (~1.9k tokens) should
   come back as cached_tokens from the second warm call on.  If strict mode
   rejects the schema, the finding goes to decisions.md and the arm design is
   revisited before any grid.
3. CONTAMINATION.  41 calls, one JSONL log, append-only; no checkpoint and no
   earlier result file is read or overwritten.  The two instances are read-only
   inputs.  Wall time is a network measurement and is labelled as such.
4. DATA ACCURACY.  Prompts are built by the same code path as the DeepSeek
   pilot (same instances, same ten instructions); every response passes through
   the guard and is logged with schema and config hashes, so verdicts replay.
================================================================================
"""


def cost(cached: int, uncached: int, output: int) -> float:
    return cached * PRICE_IN_CACHED + uncached * PRICE_IN + output * PRICE_OUT


def call_plan(warm_path, cold_path) -> list:
    plan = [{"block": "probe_temperature", "path": warm_path,
             "instruction_id": INSTRUCTIONS[0][0], "template": INSTRUCTIONS[0][1],
             "mode": M_FREE, "effort": "none"}]
    for mode, effort in WARM_CELLS:
        for iid, template in INSTRUCTIONS:
            plan.append({"block": "warm", "path": warm_path, "instruction_id": iid,
                         "template": template, "mode": mode, "effort": effort})
    for iid, template in INSTRUCTIONS:
        plan.append({"block": "cold", "path": cold_path, "instruction_id": iid,
                     "template": template, "mode": M_CONSTRAINED, "effort": "none"})
    return plan


def extrapolate(per_call: dict, grids: dict, output_scenarios) -> list:
    rows = []
    for grid, calls in grids.items():
        for out_tokens in output_scenarios:
            unit = cost(per_call["cached"], per_call["uncached"], out_tokens)
            rows.append({"grid": grid, "calls": calls,
                         "output_tokens_per_call": out_tokens,
                         "usd_per_call": unit, "usd_total": unit * calls})
    return rows


def main() -> int:
    global MODEL, PRICE_IN, PRICE_IN_CACHED, PRICE_OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print the plan, call nothing")
    ap.add_argument("--model", default=MODEL,
                    help="OpenAI model id (v3.10 reuses this pilot for gpt-5.6-terra; "
                         "use a separate --out dir so the mini artifacts stay intact)")
    ap.add_argument("--out", default="results")
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--e1-calls", type=int, default=2000,
                    help="E1 stratified core: ~1000 items x 2 enforcement modes x 1 repeat")
    ap.add_argument("--e3-calls", type=int, default=1000,
                    help="E3 reduced: 500 instructions x 2 repeats (single-agent point)")
    args = ap.parse_args()
    MODEL = args.model
    try:
        prices = PRICES_BY_MODEL[MODEL]
    except KeyError:
        raise SystemExit(
            "no price table for {}; add it to PRICES_BY_MODEL before running".format(MODEL))
    PRICE_IN, PRICE_IN_CACHED, PRICE_OUT = (
        prices["in"], prices["cached"], prices["out"])

    print(LAUNCH_QUESTIONS)

    warm_path = instances.list_instances(9, "storm2")[0]
    cold_path = instances.list_instances(10, "replay", "150")[0]
    warm = instances.load_instance(warm_path)
    cold = instances.load_instance(cold_path)
    plan = call_plan(warm_path, cold_path)

    print("CALL PLAN")
    print("  model            : {} (dated snapshot)".format(MODEL))
    print("  warm instance    : {} ({} orders)".format(warm_path.name, len(warm["work_orders"])))
    print("  cold instance    : {} ({} orders)".format(cold_path.name, len(cold["work_orders"])))
    print("  warm cells       : {}".format(
        ", ".join("{}/{}".format(m, e or "default") for m, e in WARM_CELLS)))
    print("  calls            : 1 probe + {} warm + {} cold = {}".format(
        sum(1 for c in plan if c["block"] == "warm"),
        sum(1 for c in plan if c["block"] == "cold"), len(plan)))
    print("  enforcement      : M_constrained = strict json_schema (frozen schema verbatim, "
          "integer enum included)")
    print("  prices ({})      : ${}/M in, ${}/M cached-in, ${}/M out".format(
        PRICE_DATE, PRICE_IN * 1e6, PRICE_IN_CACHED * 1e6, PRICE_OUT * 1e6))

    load_env()
    key = os.environ.get("OPENAI_API_KEY")
    if args.dry_run or not key:
        print("\nNO CALL MADE ({}).".format(
            "--dry-run" if args.dry_run else "OPENAI_API_KEY is not set"))
        return 0 if args.dry_run else 2

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    log = ProposalLog(out_dir / "openai_pilot.jsonl")
    client = ChatClient("openai", model=MODEL, max_tokens=args.max_tokens)
    loaded = {str(warm_path): warm, str(cold_path): cold}
    baselines = {}
    rows = []
    empty = 0
    probes = {"temperature_accepted": None, "strict_schema_accepted": None,
              "default_effort_note": "effort omitted on the wire; snapshot default applies"}

    for i, call in enumerate(plan, 1):
        inst = loaded[str(call["path"])]
        sys_prompt, user_prompt = build_prompt(inst, pick_targets(inst), call["template"])
        started = time.perf_counter()
        resp = client.complete(
            sys_prompt, user_prompt, mode=call["mode"], reasoning=call["effort"]
        )
        wall_ms = (time.perf_counter() - started) * 1000.0

        if call["block"] == "probe_temperature":
            rejected = (resp.outcome == OUTCOME_ERROR and resp.error
                        and "temperature" in resp.error.lower())
            probes["temperature_accepted"] = not rejected
            print("  probe: temperature {} ({})".format(
                "REJECTED - dropping the field for all further calls" if rejected
                else "accepted", (resp.error or "HTTP {}".format(resp.status))[:120]))
            if rejected:
                BACKENDS["openai"] = dataclasses.replace(
                    BACKENDS["openai"], drop_params=("temperature",))
                client = ChatClient("openai", model=MODEL, max_tokens=args.max_tokens)
                started = time.perf_counter()
                resp = client.complete(
                    sys_prompt, user_prompt, mode=call["mode"], reasoning=call["effort"]
                )
                wall_ms = (time.perf_counter() - started) * 1000.0

        if call["mode"] == M_CONSTRAINED and probes["strict_schema_accepted"] is None:
            probes["strict_schema_accepted"] = resp.outcome != OUTCOME_ERROR
            if resp.outcome == OUTCOME_ERROR:
                print("  probe: STRICT SCHEMA REJECTED: {}".format((resp.error or "")[:300]))

        if resp.outcome == OUTCOME_EMPTY_CONTENT:
            empty += 1
        if str(call["path"]) not in baselines:
            baselines[str(call["path"])] = dispatch.dispatch_baseline(inst, "atc", seed=0)
        verdict = evaluate_proposal(
            inst, resp.text if resp.text is not None else "", G_CERT,
            baseline_schedule=baselines[str(call["path"])],
        )
        record = ProposalRecord(
            instruction_id="{}-{}-{}-{}".format(
                call["instruction_id"], call["block"], call["mode"],
                call["effort"] or "default"),
            instance_id=inst["meta"]["id"],
            instance_path=str(call["path"]),
            model=MODEL,
            mode="{}/{}".format(call["mode"], call["effort"] or "default"),
            prompt_hash=prompt_hash(sys_prompt, user_prompt),
            raw_output=resp.text,
            outcome=resp.outcome,
            finish_reason=resp.finish_reason,
            latency_ms=wall_ms,
            prompt_tokens=resp.usage.get("prompt_tokens"),
            completion_tokens=resp.usage.get("completion_tokens"),
            reasoning_tokens=resp.usage.get("reasoning_tokens"),
            cache_hit_tokens=resp.usage.get("cache_hit_tokens"),
            cache_miss_tokens=resp.usage.get("cache_miss_tokens"),
            cache_hit=resp.usage.get("cache_hit"),
            api_error=resp.error,
            rule="atc",
        ).attach_verdict(verdict)
        log.append(record)
        rows.append({**call, "usage": resp.usage, "outcome": resp.outcome,
                     "wall_ms": wall_ms, "terminal": verdict.terminal})
        print("  {:>3d}/{:<3d} {:<10s} {:<18s} {:<24s} out={:<6s} reason={:<6s} "
              "cached={:<6s} wall={:>7.0f} ms  {}".format(
                  i, len(plan), call["instruction_id"], call["block"],
                  "{}/{}".format(call["mode"], call["effort"] or "default"),
                  str(resp.usage.get("completion_tokens")),
                  str(resp.usage.get("reasoning_tokens")),
                  str(resp.usage.get("cache_hit_tokens")),
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
    print("{:<30s} {:>4s} {:>10s} {:>11s} {:>11s} {:>10s}".format(
        "block/mode/effort", "n", "prompt", "cached", "completion", "reasoning"))
    groups = {}
    for r in rows:
        groups.setdefault(
            (r["block"], r["mode"], r["effort"] or "default"), []).append(r)
    per_call = {"cached": 0, "uncached": 0}
    for key, sel in sorted(groups.items()):
        u = [r["usage"] for r in sel]
        prompt = _median([x.get("prompt_tokens") for x in u])
        cached = _median([x.get("cache_hit_tokens") for x in u])
        print("{:<30s} {:>4d} {:>10.0f} {:>11.0f} {:>11.0f} {:>10.0f}".format(
            "/".join(str(k) for k in key), len(sel), prompt, cached,
            _median([x.get("completion_tokens") for x in u]),
            _median([x.get("reasoning_tokens") for x in u]) or 0))
        if key[0] == "warm":
            per_call["cached"] = max(per_call["cached"], cached)
            per_call["uncached"] = max(per_call["uncached"], prompt - cached)

    print("\nempty-content incidents : {} / {} calls".format(empty, len(rows)))
    print("temperature accepted    : {}".format(probes["temperature_accepted"]))
    print("strict schema accepted  : {} (frozen schema verbatim, integer enum included)".format(
        probes["strict_schema_accepted"]))
    print("median wall per call    : {:.0f} ms (network, not compute)".format(
        _median([r["wall_ms"] for r in rows])))

    grids = {"E1": args.e1_calls, "E2 (replay only)": 0, "E3": args.e3_calls}
    print("\n" + "=" * 96)
    print("COST EXTRAPOLATION at {} prices, from the measured prompt profile".format(PRICE_DATE))
    print("=" * 96)
    print("{:<20s} {:>8s} {:>16s} {:>14s} {:>14s}".format(
        "grid", "calls", "out tokens/call", "USD per call", "USD total"))
    table = extrapolate(per_call, grids, (300, 800, 2000))
    for row in table:
        print("{:<20s} {:>8d} {:>16d} {:>14.5f} {:>14.2f}".format(
            row["grid"], row["calls"], row["output_tokens_per_call"],
            row["usd_per_call"], row["usd_total"]))
    payload = {"rows": rows, "per_call": per_call, "empty": empty, "probes": probes,
               "cost_table": table, "price_date": PRICE_DATE}
    (out_dir / "openai_pilot_summary.json").write_text(
        json.dumps(payload, indent=1, default=str))
    print("\nwritten to {}".format(out_dir / "openai_pilot_summary.json"))


if __name__ == "__main__":
    sys.exit(main())
