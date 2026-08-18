#!/usr/bin/env python
"""DeepSeek billing pilot: 50 calls, then the cost table for the three grids.

The key is loaded explicitly from the git-ignored project ``.env`` by
``_envfile.load_env`` (never from a shell profile; see the v3.6 entry in
decisions.md).  Without a key the runner prints the plan and exits 2, and
``--dry-run`` prints the plan even when a key is present.  Nothing here is
speculative: the call plan, the prompt, the recorded fields and the cost model
are all fixed below.

What the 50 calls buy
---------------------
Three numbers the grid budgets depend on, none of which can be read off the
price page:

1. **Output tokens per call**, separately for non-thinking and thinking-high.
   Reasoning tokens are billed as output (inferred: the docs track them in
   ``completion_tokens_details.reasoning_tokens`` and state no separate rate),
   so a thinking-high call can cost several times a non-thinking one.
2. **Cache behaviour.** Every call in the warm block shares one long instance
   state prefix, so ``prompt_cache_hit_tokens`` says how much of the prompt is
   billed at $0.003625/M instead of $0.435/M.  The cold block repeats the same
   ten instructions against a *different* instance, which is what a fresh
   prefix costs.
3. **Empty-content incidence.**  DeepSeek's documented empty-completion
   behaviour is an outcome class of its own, never a schema violation; the
   pilot counts it so the grid can carry a retry budget.

Call plan (50 calls)
--------------------
    warm block  10 instructions x {non-think, think-high} x 2 repeats = 40
    cold block  10 instructions x {non-think} on a second instance     = 10

Every response is passed through the guard and written to the proposal log, so
the pilot is also a real (tiny) run: its verdicts replay like any other.

Run::

    python scripts/deepseek_pilot.py --out results/   # key comes from .env
    python scripts/deepseek_pilot.py --dry-run        # plan only, no network
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
from l1adapter import dispatch, instances, state  # noqa: E402
from l1guard import G_CERT, evaluate_proposal  # noqa: E402
from l1guard.logging import (  # noqa: E402
    OUTCOME_EMPTY_CONTENT,
    ProposalLog,
    ProposalRecord,
    prompt_hash,
)
from l1guard.models import M_CONSTRAINED, ChatClient  # noqa: E402

MODEL = "deepseek-v4-pro"

# Prices retrieved 2026-08-11 from https://api-docs.deepseek.com/quick_start/pricing.
# The page carries a forward-looking warning of a significant increase, so the
# retrieval date is part of the number.
PRICE_IN_MISS = 0.435 / 1e6
PRICE_IN_HIT = 0.003625 / 1e6
PRICE_OUT = 0.87 / 1e6
PRICE_DATE = "2026-08-11"

#: Reasoning-effort axis for v4-pro: "high" and "max" only ("low" is flash-only).
THINKING_MODES = {
    "non_think": {"thinking": {"type": "disabled"}},
    "think_high": {"thinking": {"type": "enabled"}, "reasoning_effort": "high"},
}

LAUNCH_QUESTIONS = """\
================================================================================
FOUR LAUNCH QUESTIONS (global CLAUDE.md experiment rules) - answered before the
first paid call
================================================================================
1. PURPOSE.  What does one DeepSeek V4-Pro call cost in this task, split into
   cache-miss input, cache-hit input, and output (reasoning included)?  The
   numbers set the E1/E2/E3 call budgets against the SGD 300 cap and land in
   the cost-accounting subsection of the results (Section 6.7) and in the
   reserve-rule check.
2. EXPECTED RESULT.  Non-thinking calls should cost a few hundred output
   tokens; thinking-high should cost several times that.  With a shared
   instance-state prefix, most of the prompt should come back as
   prompt_cache_hit_tokens after the first call of each block.  If the cache
   hit rate is near zero, the shared-prefix prompt design does not pay and the
   grid must either shrink or drop the thinking axis; if thinking-high costs
   more than about 3k output tokens per call, the thinking axis is priced per
   cell rather than run everywhere.
3. CONTAMINATION.  Fifty calls, one JSONL log, written append-only; no
   checkpoint and no earlier result file is read or overwritten.  The two
   instances are read-only inputs.  Wall time is recorded but is a network
   measurement, not a compute measurement, and is labelled as such.  The
   thinking-parameter wire shape is PARTIAL in the API reference, so the first
   call probes it and the probe result is recorded with the run.
4. DATA ACCURACY.  The prompt is built from l1adapter.state.state_slice on
   named instances (printed below with their order counts), the ten
   instructions are fixed in this file, and every response is passed through
   the guard and logged with the schema hash and config hash, so the pilot's
   own verdicts are reproducible by replay.
================================================================================
"""

SYSTEM_PROMPT = (
    "You are a facility-management dispatcher's assistant. You convert one "
    "instruction into a json object of scheduling operations over the work "
    "orders you are shown. Reply with the json object only, no prose.\n"
    'The object is {"operations": [ ... ]} and each operation is exactly one of:\n'
    '  {"op": "set_priority", "order_id": <id>, "priority_class": 1|2|3|4}\n'
    '  {"op": "pin_next", "order_id": <id>, "trade": <trade code>}\n'
    '  {"op": "reorder", "order_id": <id>, "relation": "before"|"after", '
    '"ref_order_id": <id>}\n'
    '  {"op": "reassign_window", "order_id": <id>, "release_shift_bh": <number>}\n'
    '  {"op": "freeze", "order_id": <id>}\n'
    '  {"op": "unfreeze", "order_id": <id>}\n'
    '  {"op": "batch", "building_id": <id>, "trade": <trade code>}\n'
    "Priority class 1 is the most urgent and 4 the least. Times are in business "
    "hours. If the instruction cannot be carried out with these operations, "
    'return {"operations": []}.'
)

#: Ten instructions covering all seven operations, one ambiguity case, and one
#: request that the vocabulary cannot express (the refusal signal).
INSTRUCTIONS = [
    ("I01", "The tenant in the top-floor unit escalated {urgent}; treat it as the most "
            "urgent class."),
    ("I02", "Put the {trade} crew on {urgent} at their next free moment."),
    ("I03", "{urgent} cannot start before {other} is under way."),
    ("I04", "Push {routine} back to next week; the parts are not in."),
    ("I05", "{urgent} is already being worked on, so leave its slot exactly as planned."),
    ("I06", "We moved {urgent} earlier by mistake; release the hold on it."),
    ("I07", "Send one technician round {building} to do all the {trade} jobs there in "
            "one trip."),
    ("I08", "{routine} is routine, drop it to the lowest class and pull {urgent} "
            "forward."),
    ("I09", "Deal with the leak on the third floor as soon as you can."),
    ("I10", "Hire a second electrician for the afternoon shift."),
]


def build_prompt(inst, targets, template: str) -> tuple:
    """Shared state prefix first, the one-line instruction last (cache-friendly)."""
    slice_json = json.dumps(state.state_slice(inst, top_k=25), sort_keys=True)
    prefix = (
        "Site state (json):\n{}\n\n"
        "Answer for this site only. Use only the work order ids and trade codes "
        "shown above.\n\nInstruction: ".format(slice_json)
    )
    user = prefix + template.format(**targets)
    return SYSTEM_PROMPT, user


def pick_targets(inst) -> dict:
    """Named targets for the instruction templates.

    "Urgent" is the earliest-due order of the MOST urgent class PRESENT and
    "routine" the longest order of the LEAST urgent class present: replay-track
    instances carry no priority-1 orders at all (the first cold run crashed on
    exactly that), so the classes are resolved per instance rather than assumed.
    """
    orders = inst["work_orders"]
    best_pri = min(int(w["priority"]) for w in orders)
    worst_pri = max(int(w["priority"]) for w in orders)
    urgent = min(
        (w for w in orders if int(w["priority"]) == best_pri),
        key=lambda w: (float(w["due_bh"]), w["id"]),
    )
    other = min(
        (w for w in orders if w["id"] != urgent["id"]),
        key=lambda w: (float(w["due_bh"]), w["id"]),
    )
    routine = max(
        (w for w in orders if int(w["priority"]) == worst_pri),
        key=lambda w: (float(w["p_bh"]), w["id"]),
    )
    building = next(
        (w["building"] for w in orders if w["building"] is not None), "BLDG-UNKNOWN"
    )
    return {
        "urgent": urgent["id"],
        "other": other["id"],
        "routine": routine["id"],
        "trade": urgent["trade"],
        "building": building,
    }


def call_plan(warm_path, cold_path, repeats: int) -> list:
    plan = []
    for repeat in range(repeats):
        for mode in ("non_think", "think_high"):
            for iid, template in INSTRUCTIONS:
                plan.append(
                    {"block": "warm", "path": warm_path, "instruction_id": iid,
                     "template": template, "thinking": mode, "repeat": repeat}
                )
    for iid, template in INSTRUCTIONS:
        plan.append(
            {"block": "cold", "path": cold_path, "instruction_id": iid,
             "template": template, "thinking": "non_think", "repeat": 0}
        )
    return plan


def cost(prompt_hit: int, prompt_miss: int, output: int) -> float:
    return prompt_hit * PRICE_IN_HIT + prompt_miss * PRICE_IN_MISS + output * PRICE_OUT


def extrapolate(per_call: dict, grids: dict, output_scenarios) -> list:
    """Cost per grid under each assumed output-token budget."""
    rows = []
    for grid, calls in grids.items():
        for out_tokens in output_scenarios:
            unit = cost(per_call["hit"], per_call["miss"], out_tokens)
            rows.append(
                {
                    "grid": grid,
                    "calls": calls,
                    "output_tokens_per_call": out_tokens,
                    "usd_per_call": unit,
                    "usd_total": unit * calls,
                }
            )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print the plan, call nothing")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--out", default="results")
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--e1-calls", type=int, default=6000,
                    help="suite size x 2 modes x 3 repeats (one generation pass serves "
                         "all three guard arms by replay)")
    ap.add_argument("--e2-calls", type=int, default=0,
                    help="E2 is offline replay over the E1 log: no new calls")
    ap.add_argument("--e3-calls", type=int, default=5000,
                    help="500 instructions x 2 repeats x (1 single + 4 multi-agent calls)")
    args = ap.parse_args()

    print(LAUNCH_QUESTIONS)

    warm_path = instances.list_instances(9, "storm2")[0]
    cold_path = instances.list_instances(10, "replay", "150")[0]
    warm = instances.load_instance(warm_path)
    cold = instances.load_instance(cold_path)
    plan = call_plan(warm_path, cold_path, args.repeats)

    print("CALL PLAN")
    print("  model            : {} (no snapshot pinning exists; pin the access window)"
          .format(MODEL))
    print("  warm instance    : {} ({} orders)".format(warm_path.name, len(warm["work_orders"])))
    print("  cold instance    : {} ({} orders)".format(cold_path.name, len(cold["work_orders"])))
    print("  instructions     : {}".format(len(INSTRUCTIONS)))
    print("  thinking modes   : {}".format(", ".join(THINKING_MODES)))
    print("  repeats (warm)   : {}".format(args.repeats))
    print("  calls            : {} warm + {} cold = {}".format(
        sum(1 for c in plan if c["block"] == "warm"),
        sum(1 for c in plan if c["block"] == "cold"),
        len(plan),
    ))
    print("  enforcement      : M_constrained = JSON-object mode (DeepSeek has no "
          "user-supplied schema mode)")
    print("  prices ({})      : ${}/M in-miss, ${}/M in-hit, ${}/M out".format(
        PRICE_DATE, PRICE_IN_MISS * 1e6, PRICE_IN_HIT * 1e6, PRICE_OUT * 1e6))

    sys_prompt, user_prompt = build_prompt(warm, pick_targets(warm), INSTRUCTIONS[0][1])
    print("  prompt size      : system {} chars, user {} chars (state prefix first, "
          "instruction last)".format(len(sys_prompt), len(user_prompt)))

    load_env()
    key = os.environ.get("DEEPSEEK_API_KEY")
    if args.dry_run or not key:
        print("\nNO CALL MADE ({}).".format(
            "--dry-run" if args.dry_run else "DEEPSEEK_API_KEY is not set"))
        print(
            "Set DEEPSEEK_API_KEY and re-run to execute the {} calls; the report "
            "template below is filled from the measured usage fields.".format(len(plan))
        )
        print_report_template(args, plan)
        return 0 if args.dry_run else 2

    # ---------------------------------------------------------------- run -- #
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    log = ProposalLog(out_dir / "deepseek_pilot.jsonl")
    client = ChatClient("deepseek", model=MODEL, max_tokens=args.max_tokens)
    loaded = {str(warm_path): warm, str(cold_path): cold}
    baselines = {}
    rows = []
    empty = 0

    for i, call in enumerate(plan, 1):
        inst = loaded[str(call["path"])]
        targets = pick_targets(inst)
        sys_prompt, user_prompt = build_prompt(inst, targets, call["template"])
        extra = dict(THINKING_MODES[call["thinking"]])
        started = time.perf_counter()
        resp = client.complete(
            sys_prompt, user_prompt, mode=M_CONSTRAINED, extra_body=extra
        )
        wall_ms = (time.perf_counter() - started) * 1000.0
        if resp.outcome == OUTCOME_EMPTY_CONTENT:
            empty += 1

        if str(call["path"]) not in baselines:
            baselines[str(call["path"])] = dispatch.dispatch_baseline(inst, "atc", seed=0)
        verdict = evaluate_proposal(
            inst,
            resp.text if resp.text is not None else "",
            G_CERT,
            baseline_schedule=baselines[str(call["path"])],
        )
        record = ProposalRecord(
            instruction_id="{}-{}-{}-r{}".format(
                call["instruction_id"], call["block"], call["thinking"], call["repeat"]
            ),
            instance_id=inst["meta"]["id"],
            instance_path=str(call["path"]),
            model=MODEL,
            mode="M_constrained/{}".format(call["thinking"]),
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
        print(
            "  {:>3d}/{:<3d} {:<10s} {:<10s} {:<14s} out={:<6s} reason={:<6s} "
            "hit={:<6s} wall={:>7.0f} ms  {}".format(
                i, len(plan), call["instruction_id"], call["block"], call["thinking"],
                str(resp.usage.get("completion_tokens")),
                str(resp.usage.get("reasoning_tokens")),
                str(resp.usage.get("cache_hit_tokens")),
                wall_ms, verdict.terminal,
            ),
            flush=True,
        )

    summarise(rows, empty, args, out_dir)
    return 0


def _median(values):
    values = [v for v in values if v is not None]
    return median(values) if values else 0


def summarise(rows, empty: int, args, out_dir: Path) -> None:
    print("\n" + "=" * 96)
    print("MEASURED PER-CALL USAGE")
    print("=" * 96)
    print("{:<20s} {:>7s} {:>10s} {:>11s} {:>11s} {:>11s} {:>10s}".format(
        "block/mode", "n", "prompt", "cache hit", "cache miss", "completion", "reasoning"))
    groups = {}
    for r in rows:
        groups.setdefault((r["block"], r["thinking"]), []).append(r)
    per_call = {"hit": 0, "miss": 0}
    for key, sel in sorted(groups.items()):
        u = [r["usage"] for r in sel]
        row = (
            _median([x.get("prompt_tokens") for x in u]),
            _median([x.get("cache_hit_tokens") for x in u]),
            _median([x.get("cache_miss_tokens") for x in u]),
            _median([x.get("completion_tokens") for x in u]),
            _median([x.get("reasoning_tokens") for x in u]),
        )
        print("{:<20s} {:>7d} {:>10.0f} {:>11.0f} {:>11.0f} {:>11.0f} {:>10.0f}".format(
            "/".join(key), len(sel), *row))
        if key[0] == "warm":
            per_call["hit"] = max(per_call["hit"], row[1])
            per_call["miss"] = max(per_call["miss"], row[2])

    print("\nempty-content incidents: {} / {} calls".format(empty, len(rows)))
    print("median wall per call   : {:.0f} ms (network, not compute)".format(
        _median([r["wall_ms"] for r in rows])))

    grids = {"E1": args.e1_calls, "E2 (replay only)": args.e2_calls, "E3": args.e3_calls}
    print("\n" + "=" * 96)
    print("COST EXTRAPOLATION at {} prices, from the measured prompt profile".format(
        PRICE_DATE))
    print("=" * 96)
    print("{:<20s} {:>8s} {:>16s} {:>14s} {:>14s}".format(
        "grid", "calls", "out tokens/call", "USD per call", "USD total"))
    table = extrapolate(per_call, grids, (600, 1500, 3100))
    for row in table:
        print("{:<20s} {:>8d} {:>16d} {:>14.5f} {:>14.2f}".format(
            row["grid"], row["calls"], row["output_tokens_per_call"],
            row["usd_per_call"], row["usd_total"]))
    payload = {"rows": rows, "per_call": per_call, "empty": empty, "cost_table": table,
               "price_date": PRICE_DATE}
    (out_dir / "deepseek_pilot_summary.json").write_text(json.dumps(payload, indent=1,
                                                                    default=str))
    print("\nwritten to {}".format(out_dir / "deepseek_pilot_summary.json"))


def print_report_template(args, plan) -> None:
    grids = {"E1": args.e1_calls, "E2 (replay only)": args.e2_calls, "E3": args.e3_calls}
    print("\n" + "=" * 96)
    print("REPORT TEMPLATE (fill from the run; the cost model is fixed)")
    print("=" * 96)
    print("""\
Per-call usage, median per block and thinking mode:
  warm/non_think   prompt ____  cache hit ____  cache miss ____  completion ____  reasoning ____
  warm/think_high  prompt ____  cache hit ____  cache miss ____  completion ____  reasoning ____
  cold/non_think   prompt ____  cache hit ____  cache miss ____  completion ____  reasoning ____
Empty-content incidents: ____ / {n} calls.
Thinking-parameter wire shape accepted by the API: ____ (open item 6 in the model
research; the first call probes it).
Reasoning-token billing: reconcile the invoice against output tokens (open item 5:
"reasoning billed as output" is inferred, not stated).

Cost model, prices retrieved {date}:
  USD = hit_tokens * {hit:.9f} + miss_tokens * {miss:.9f} + output_tokens * {out:.9f}

Grid budgets to fill in (calls are the current plan, not measurements):""".format(
        n=len(plan), date=PRICE_DATE, hit=PRICE_IN_HIT, miss=PRICE_IN_MISS, out=PRICE_OUT))
    for grid, calls in grids.items():
        print("  {:<20s} {:>6d} calls x USD ____ = USD ____".format(grid, calls))
    print("""
Scenarios to report per grid: 600, 1500 and 3100 output tokens per call.
Decision the table drives: whether the thinking-high axis runs on the full E1
grid, on a stratified subset, or not at all, and whether the reserve rule
(>= SGD 75 untouched until E3) still holds after E1.""")


if __name__ == "__main__":
    sys.exit(main())
