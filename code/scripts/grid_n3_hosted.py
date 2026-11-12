#!/usr/bin/env python
"""N3 grid, hosted arms: stated acceptance of cost under protocol v1.1.0.

Same job and the same raw-row contract as ``grid_e1_hosted.py``, which this
runner imports for the arm table, the cache split, the call plan, the cost
model and the offline transport: it only GENERATES.  Every guard disposition
is a replay over the raw log (``n3_evaluate.py``).

Frozen design (revision plan, Section 6, 2026-10-26)
----------------------------------------------------
* items    : three sets, 640 items per pass, all named by
             ``code/suite/v1.1/manifest.json`` (its sha256 and the extension
             file's sha256 are asserted):
             (a) the 220 ``costly_accepted`` items of ``suite_ext.jsonl``,
             (b) their 220 V3 twins from suite v0.2 (the same text without the
                 acceptance clause), and
             (c) the 200-item benign control from suite v0.2;
* prompt   : ``l1-prompt-1.1.0`` = the v1.0.0 prompt plus one sentence in
             the output contract.  For every item from suite v0.2 the v1.1.0
             user message is asserted equal to the v1.0.0 one, and the v1.0.0
             fingerprint is asserted equal to the ``prompt_hash`` published in
             the E1 log; for every ``costly_accepted`` item the user message is
             asserted equal to its twin's with the instruction replaced;
* schema   : M_constrained sends the canonical schema file
             ``l1-adjustments-1.1.0`` on every structured wire (Anthropic
             ``output_config``, OpenAI strict ``json_schema``), in which
             ``issuer_accepts_cost`` is a required boolean, so the contract is
             the same on every provider; DeepSeek's JSON-object mode carries
             no schema;
* arms     : deepseek, openai (GPT-5.4-mini), sol (GPT-5.6), sonnet (Claude
             Sonnet 5), opus (Claude Opus 5), each at the thinking setting the
             E1 analysis treats as primary (``paper_macros.PRIMARY_THINKING``)
             and in BOTH modes, including sol, whose E1 spot check ran
             M_constrained only;
* repeats  : 2; max_tokens 4096; the prompt-caching split, call order, worker
             pool and resumable append-only log of the E1 runner.

The run meta records the extension sha256, the manifest sha256, the source
suite sha256, both schema hashes and the prompt version, and the runner
refuses a log written by another arm or another prompt version.

Run::

    python scripts/grid_n3_hosted.py --arm sonnet --dry-run
    python scripts/grid_n3_hosted.py --arm sonnet --mock --limit 40
    python scripts/grid_n3_hosted.py --arm sonnet          # paid

The negated-acceptance control (``code/suite/v1.1/suite_ext_neg.jsonl``, the
220 V3 twins with a clause that refuses the knock-on delay, gold intent
false) runs on its own, constrained mode only, into ``results/n3neg_<arm>``::

    python scripts/grid_n3_hosted.py --arm sonnet --item-sets costly_negated \
        --modes constrained --dry-run

For every ``costly_negated`` item the user message is asserted equal to its
V3 twin's with the instruction replaced; the twins are rendered for that
check (and for their own v1.0.0 checks) but are not called.

``--mock`` uses an offline transport that answers each request with the
item's own gold operations and the flag true exactly when the instruction
carries an acceptance clause (false otherwise), except on every seventh V3
twin, where it writes true anyway so the false-acceptance path is exercised,
and on every eleventh benign control, where it writes the flag inside the
operation object so the misplaced-flag path is exercised.  It is an
instrument check, never a model.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

# The instance snapshot the published results were computed on.  The suite
# gate's manifest check still runs on every file; this only chooses the tree.
os.environ.setdefault("L1_INSTANCE_ROOT",
                      ((os.environ.get("L1_Y1_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "PaperY-FMScheduling")) + "/data/processed/instances_v10"))

import grid_e1_hosted as gh  # noqa: E402
import suite_gate as sg  # noqa: E402
from _envfile import load_env  # noqa: E402
from l1adapter import ops as ops_mod  # noqa: E402
from l1guard.logging import OUTCOME_ERROR, OUTCOME_OK  # noqa: E402
from l1guard.models import (  # noqa: E402
    BACKENDS,
    ENF_JSON_SCHEMA,
    ENF_NONE,
    M_CONSTRAINED,
    M_FREE,
    WIRE_ANTHROPIC,
    ChatClient,
)

PROMPTS = sg.load_prompts_module()
PROMPT_VERSION = PROMPTS.PROMPT_VERSION_V11
PROMPT_KEY = "1.1.0"
SYSTEM_PROMPT = PROMPTS.system_prompt(PROMPT_KEY)
if PROMPT_VERSION != "l1-prompt-1.1.0":
    raise SystemExit("REFUSING TO RUN: prompt module reports {!r}".format(PROMPT_VERSION))

EXT_DIR = sg.CODE_DIR / "suite" / "v1.1"
EXT_PATH = EXT_DIR / "suite_ext.jsonl"
EXT_MANIFEST = EXT_DIR / "manifest.json"
#: Recorded when the extension was built (2026-10-26).
EXT_SHA256 = "2bc5789a3d15aca0e97991407622dabbb9d225d38c3eb69096044844b30f38c5"
#: The negated-acceptance control and its own manifest (built 2026-10-26 by
#: ``build_suite_ext_neg.py``); ``manifest.json`` is not touched by it.
EXT_NEG_PATH = EXT_DIR / "suite_ext_neg.jsonl"
EXT_NEG_MANIFEST = EXT_DIR / "manifest_neg.json"
EXT_NEG_SHA256 = "5205e34621fa60a816c9ecdda145fbf3ecab71d952ada684fa084c27469dfb02"

#: The published E1 log whose prompt_hash column is the v1.0.0 fingerprint.
PUBLISHED_PROMPT_LOG = sg.CODE_DIR.parent / "results" / "e1_eval_opus5" / "proposals.jsonl"

ITEM_SETS = ("costly_accepted", "v3_twin", "benign_control")
NEG_SET = "costly_negated"
ALL_ITEM_SETS = ITEM_SETS + (NEG_SET,)
#: Item sets whose instruction extends a V3 twin's (no v1.0.0 render exists).
EXT_SETS = ("costly_accepted", NEG_SET)
SET_SIZES = {"costly_accepted": 220, "v3_twin": 220, "benign_control": 200, NEG_SET: 220}
MODE_CHOICES = {"both": None, "constrained": (M_CONSTRAINED,)}
REPEATS = 2

#: The thinking label each arm runs at: the E1 analysis's primary setting.
PRIMARY_THINKING = {"deepseek": "non_think", "openai": None, "sol": "none",
                    "sonnet": "disabled", "opus": "default"}

#: Price bases in force on the launch date.  The E1 table lists Sonnet 5's
#: introductory base first (through 2026-08-31); from 2026-09-01 the standard
#: base applies, so it is moved to the front and the intro base kept second.
_PRICE_ORDER = {"sonnet": ("standard (from 2026-09-01)", "intro (through 2026-08-31)")}


def n3_arm(name: str) -> gh.Arm:
    base = gh.ARMS[name]
    label = PRIMARY_THINKING[name]
    thinking = tuple(t for t in base.thinking if t[0] == label)
    if len(thinking) != 1:
        raise SystemExit("arm {} has no thinking label {!r}".format(name, label))
    prices = base.prices
    if name in _PRICE_ORDER:
        order = _PRICE_ORDER[name]
        prices = tuple(sorted(prices, key=lambda p: order.index(p[0])))
    return dataclasses.replace(base, thinking=thinking, prices=prices, modes=gh.MODES)


ARMS = {name: n3_arm(name) for name in PRIMARY_THINKING}


def wire_schema(arm: gh.Arm):
    """The schema this arm's constrained wire carries: the canonical v1.1.0 file."""
    backend = BACKENDS[arm.backend]
    if backend.constrained != ENF_JSON_SCHEMA:
        return None
    return ops_mod.SCHEMA_V11


# --------------------------------------------------------------------------- #
# Items                                                                        #
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    return sg.sha256_file(path)


def load_item_sets() -> tuple:
    """``(items, inputs)``: the 640 items of the published N3 run, plus the hashes checked."""
    items, inputs, _ = load_run_item_sets(ITEM_SETS)
    return items, inputs


def load_run_item_sets(item_sets=ITEM_SETS) -> tuple:
    """``(items, inputs, check_twins)``: the run's items in set order, the hashes
    checked, and the V3 twins rendered only for the twin check (not called)."""
    item_sets = tuple(item_sets)
    inputs = sg.assert_inputs()
    got = sha256_file(EXT_PATH)
    if got != EXT_SHA256:
        raise SystemExit("REFUSING TO RUN: {} has sha256 {}, expected {}".format(
            EXT_PATH, got, EXT_SHA256))
    manifest = json.loads(EXT_MANIFEST.read_text())
    if manifest["artifacts"]["suite_ext.jsonl"]["sha256"] != EXT_SHA256:
        raise SystemExit("REFUSING TO RUN: the manifest names another extension file")
    if manifest["source_suite"]["sha256"] != inputs["suite_sha256"]:
        raise SystemExit("REFUSING TO RUN: the extension was built from another suite")
    inputs["suite_ext_sha256"] = got
    inputs["suite_ext_manifest_sha256"] = sha256_file(EXT_MANIFEST)
    inputs["schema_v11_sha256"] = ops_mod.verify_schema_v11()

    base = {r["item_id"]: r for r in sg.load_suite()}
    ext = [json.loads(line) for line in EXT_PATH.open() if line.strip()]
    sets = manifest["item_sets"]
    items = []
    if "costly_accepted" in item_sets:
        for item in ext:
            items.append(dict(item, item_set="costly_accepted", gold_intent_flag=True))
    for set_name in ("v3_twin", "benign_control"):
        if set_name not in item_sets:
            continue
        for item_id in sets[set_name]["item_ids"]:
            items.append(dict(base[item_id], item_set=set_name, gold_intent_flag=False))
    check_twins = []
    if NEG_SET in item_sets:
        got_neg = sha256_file(EXT_NEG_PATH)
        if got_neg != EXT_NEG_SHA256:
            raise SystemExit("REFUSING TO RUN: {} has sha256 {}, expected {}".format(
                EXT_NEG_PATH, got_neg, EXT_NEG_SHA256))
        neg_manifest = json.loads(EXT_NEG_MANIFEST.read_text())
        if neg_manifest["artifacts"]["suite_ext_neg.jsonl"]["sha256"] != EXT_NEG_SHA256:
            raise SystemExit("REFUSING TO RUN: the negation manifest names another file")
        if neg_manifest["source_suite"]["sha256"] != inputs["suite_sha256"]:
            raise SystemExit("REFUSING TO RUN: the negated set was built from another suite")
        if neg_manifest["companion_extension"]["sha256"] != EXT_SHA256:
            raise SystemExit("REFUSING TO RUN: the negated set names another extension file")
        inputs["suite_ext_neg_sha256"] = got_neg
        inputs["suite_ext_neg_manifest_sha256"] = sha256_file(EXT_NEG_MANIFEST)
        neg = [json.loads(line) for line in EXT_NEG_PATH.open() if line.strip()]
        if [it["item_id"] for it in neg] != neg_manifest["item_sets"][NEG_SET]["item_ids"]:
            raise SystemExit("REFUSING TO RUN: the negated items differ from their manifest")
        twin_ids = set(sets["v3_twin"]["item_ids"])
        for item in neg:
            if item["twin_id"] not in twin_ids or item["gold_intent_flag"] is not False or \
                    item["gold_intent"] != {ops_mod.FLAG_FIELD: False}:
                raise SystemExit("REFUSING TO RUN: {} is not a negated V3 twin".format(
                    item["item_id"]))
            items.append(dict(item, item_set=NEG_SET, gold_intent_flag=False))
        if "v3_twin" not in item_sets:
            check_twins = [dict(base[i], item_set="v3_twin", gold_intent_flag=False)
                           for i in sets["v3_twin"]["item_ids"]]
    counts = {s: sum(1 for it in items if it["item_set"] == s) for s in item_sets}
    want = {s: SET_SIZES[s] for s in item_sets}
    if counts != want:
        raise SystemExit("REFUSING TO RUN: item sets {} != {}".format(counts, want))
    if len({it["item_id"] for it in items}) != len(items):
        raise SystemExit("REFUSING TO RUN: an item id appears in two sets")
    inputs["item_set_counts"] = counts
    return items, inputs, check_twins


def published_hashes(path: Path) -> dict:
    if not path.exists():
        return {}
    out: dict = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                row = json.loads(line)
                out.setdefault(row["instruction_id"], set()).add(row["prompt_hash"])
    return out


def prepare(items: list, instances, top_k: int, published: dict,
            check_twins: list = ()) -> tuple:
    """Render, split and fingerprint every item under v1.1.0; fatal on any mismatch.

    ``check_twins`` are V3 twins that are not called in this run: each is
    rendered (with its own v1.0.0 checks) only so that the extension items
    can be compared with their twin's user message.
    """
    prepared, checks = [], {"v10_hash_equal": 0, "v10_hash_absent": 0,
                            "user_equal_v10": 0, "twin_user_equal": 0}
    if any(it["item_set"] == NEG_SET for it in items):
        checks["neg_twin_user_equal"] = 0
    if check_twins:
        checks["twins_rendered_for_check"] = 0
    users_v10: dict = {}
    v3_instruction: dict = {}

    def v10_checks(item, instance, user):
        v10 = PROMPTS.build_messages(instance, item, top_k)
        if v10[1]["content"] != user:
            raise SystemExit("REFUSING TO RUN: the v1.1.0 user message differs from "
                             "the v1.0.0 one for {}".format(item["item_id"]))
        checks["user_equal_v10"] += 1
        users_v10[item["item_id"]] = user
        v3_instruction[item["item_id"]] = item["instruction"]
        want = published.get(item["item_id"])
        if want is None:
            checks["v10_hash_absent"] += 1
        elif want != {PROMPTS.prompt_fingerprint(v10)}:
            raise SystemExit("REFUSING TO RUN: the v1.0.0 render of {} no longer "
                             "matches the published prompt_hash".format(item["item_id"]))
        else:
            checks["v10_hash_equal"] += 1

    for twin in check_twins:
        instance = instances.get(twin)
        messages = PROMPTS.build_messages(instance, twin, top_k, version=PROMPT_KEY)
        if messages[0]["content"] != SYSTEM_PROMPT:
            raise SystemExit("REFUSING TO RUN: system prompt is not the v1.1.0 text")
        v10_checks(twin, instance, messages[1]["content"])
        checks["twins_rendered_for_check"] += 1

    for item in items:
        instance = instances.get(item)
        messages = PROMPTS.build_messages(instance, item, top_k, version=PROMPT_KEY)
        system, user = messages[0]["content"], messages[1]["content"]
        if system != SYSTEM_PROMPT:
            raise SystemExit("REFUSING TO RUN: system prompt is not the v1.1.0 text")
        if item["item_set"] not in EXT_SETS:
            v10_checks(item, instance, user)
        prefix, tail, which = gh.split_user_prompt(user)
        if prefix + tail != user:
            raise SystemExit("REFUSING TO RUN: split not byte-identical for {}".format(
                item["item_id"]))
        full = PROMPTS.prompt_fingerprint(messages)
        split = PROMPTS.prompt_fingerprint(
            [{"role": "system", "content": system}, {"role": "user", "content": prefix + tail}])
        if split != full:
            raise SystemExit("REFUSING TO RUN: fingerprint changed under the split for "
                             "{}".format(item["item_id"]))
        path = instances.path(item)
        prepared.append(gh.Prepared(item=item, instance_path=path,
                                    group=(path, tuple(item["episode"]["frozen_seed"])),
                                    prefix=prefix, tail=tail, prompt_hash=full, split_at=which))
    for prep in prepared:
        item = prep.item
        if item["item_set"] not in EXT_SETS:
            continue
        twin_user = users_v10.get(item["twin_id"])
        if twin_user is None:
            raise SystemExit("REFUSING TO RUN: twin {} of {} is not in the run".format(
                item["twin_id"], item["item_id"]))
        if item["base_instruction"] != v3_instruction[item["twin_id"]]:
            raise SystemExit("REFUSING TO RUN: {} does not extend its twin's instruction".format(
                item["item_id"]))
        marker = "\nINSTRUCTION\n"
        expected = twin_user.replace(marker + item["base_instruction"] + "\n",
                                     marker + item["instruction"] + "\n", 1)
        if expected == twin_user or expected != prep.prefix + prep.tail:
            raise SystemExit("REFUSING TO RUN: {} is not its twin's prompt with the "
                             "instruction replaced".format(item["item_id"]))
        checks["twin_user_equal" if item["item_set"] == "costly_accepted"
               else "neg_twin_user_equal"] += 1
    prepared.sort(key=lambda p: (p.group[0], p.group[1], p.item["item_id"]))
    return prepared, checks


# --------------------------------------------------------------------------- #
# The offline transport                                                        #
# --------------------------------------------------------------------------- #
class N3MockTransport(gh.MockTransport):
    """The E1 mock with the item's gold operations and the gold flag as its answer."""

    def __init__(self, arm, by_instruction: dict, fail_every: int = 0):
        super().__init__(arm, fail_every=fail_every)
        self.by_instruction = by_instruction

    def _answer(self, payload: dict) -> str:
        if "messages" in payload and payload["messages"] and \
                isinstance(payload["messages"][0].get("content"), list):
            user = "".join(b["text"] for b in payload["messages"][0]["content"])
        else:
            user = payload["messages"][1]["content"]
        text = user.split("\nINSTRUCTION\n", 1)[1].split("\n\nReply with", 1)[0]
        item = self.by_instruction[text]
        number = int(item["item_id"].split("-")[1])
        flag = item["item_set"] == "costly_accepted"
        if item["item_set"] in ("v3_twin", NEG_SET) and number % 7 == 0:
            flag = True
        if item["item_set"] == "benign_control" and number % 11 == 0 and item["gold_ops"]:
            ops = [dict(item["gold_ops"][0], **{ops_mod.FLAG_FIELD: True})] + \
                list(item["gold_ops"][1:])
            return json.dumps({"operations": ops})
        return json.dumps({"operations": item["gold_ops"], ops_mod.FLAG_FIELD: flag})

    def __call__(self, method, url, headers, body, timeout):
        status, raw = super().__call__(method, url, headers, body, timeout)
        if status != 200:
            return status, raw
        payload = json.loads(body.decode("utf-8"))
        reply = json.loads(raw.decode("utf-8"))
        text = self._answer(payload)
        if "content" in reply:
            for block in reply["content"]:
                if block.get("type") == "text":
                    block["text"] = text
        else:
            reply["choices"][0]["message"]["content"] = text
        return status, json.dumps(reply).encode()


# --------------------------------------------------------------------------- #
# Rows, resume and the run                                                     #
# --------------------------------------------------------------------------- #
def read_completed(path: Path, arm, expected_hashes: dict | None = None) -> tuple:
    """Completed keys of an existing log, refusing rows of another prompt.

    ``expected_hashes`` maps item id to the prompt fingerprint this run will
    send.  A logged row whose fingerprint differs was generated under another
    prompt text, even if it carries the same version label, and the log is
    refused rather than resumed.
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
                broken += 1
                continue
            if row.get("arm") != arm.arm or row.get("model") != arm.model:
                raise SystemExit("REFUSING TO RUN: {} holds rows for arm {!r} model {!r}".format(
                    path, row.get("arm"), row.get("model")))
            if row.get("prompt_version") != PROMPT_VERSION:
                raise SystemExit("REFUSING TO RUN: {} holds rows for prompt version {!r}".format(
                    path, row.get("prompt_version")))
            if expected_hashes is not None and \
                    expected_hashes.get(row["item_id"]) != row.get("prompt_hash"):
                raise SystemExit("REFUSING TO RUN: {} holds a row for {} rendered under "
                                 "another prompt text".format(path, row["item_id"]))
            rows += 1
            key = gh.row_key(row["mode"], row.get("thinking"), row["repeat"], row["item_id"])
            if row.get("outcome") == OUTCOME_ERROR:
                errors += 1
                done.discard(key)
            else:
                done.add(key)
    return done, rows, errors, broken


def make_row(arm, call: dict, resp, latency_ms: float, backend) -> dict:
    row = gh.make_row(arm, call, resp, latency_ms, backend)
    item = call["prep"].item
    row["prompt_version"] = PROMPT_VERSION
    row["item_set"] = item["item_set"]
    row["gold_intent"] = {ops_mod.FLAG_FIELD: bool(item["gold_intent_flag"])}
    row["register"] = item["register"]
    row["suite_version"] = item.get("suite_version")
    row["schema_version"] = ops_mod.SCHEMA_V11_VERSION
    return row


def one_call(client, arm, call: dict, kwargs: dict, backend) -> dict:
    prep = call["prep"]
    started = time.perf_counter()
    try:
        resp = client.complete(SYSTEM_PROMPT, (prep.prefix, prep.tail), mode=call["mode"],
                               **kwargs)
    except Exception as exc:  # noqa: BLE001 - the row records it and the key retries
        resp = gh._FailedCall(arm.model, "{}: {}".format(type(exc).__name__, exc))
    return make_row(arm, call, resp, (time.perf_counter() - started) * 1000.0, backend)


def run(arm, args, plan: list, log_path: Path, client) -> dict:
    """The E1 run loop: a warm call per group, a pool for the rest, one writer."""
    backend = BACKENDS[arm.backend]
    base = arm.prices[0][1]
    schema = wire_schema(arm)
    tally: dict = {}
    started_all = time.perf_counter()
    written = 0
    interrupted = False
    passes = gh.split_into_passes(plan)
    with open(log_path, "a", encoding="utf-8") as fh:
        def write(row: dict) -> None:
            nonlocal written
            fh.write(json.dumps(row, sort_keys=True) + "\n")
            fh.flush()
            written += 1
            cell = tally.setdefault((row["mode"], row["thinking"], row["repeat"]),
                                    {"calls": 0, "ok": 0, "error": 0, "other": 0,
                                     "usd": 0.0, "out_tokens": 0, "latency_ms": 0.0})
            cell["calls"] += 1
            if row["outcome"] == OUTCOME_OK:
                cell["ok"] += 1
            elif row["outcome"] == OUTCOME_ERROR:
                cell["error"] += 1
            else:
                cell["other"] += 1
            cell["usd"] += gh.call_usd(base, row["usage"] or {})
            cell["out_tokens"] += (row["usage"] or {}).get("completion_tokens") or 0
            cell["latency_ms"] += row["latency_ms"]

        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            try:
                for index, ((mode, label, repeat), groups) in enumerate(passes, 1):
                    kwargs = {"max_tokens": args.max_tokens}
                    if mode == M_CONSTRAINED and schema is not None:
                        kwargs["schema"] = schema
                    body = gh.thinking_body(arm, label)
                    if body:
                        kwargs["extra_body"] = body
                    print("\n[n3h] pass {}/{}  {} thinking={} r{}  ({} groups, {} calls)".format(
                        index, len(passes), mode, gh.label_text(label), repeat, len(groups),
                        sum(len(m) for _, m in groups)), flush=True)
                    for g, (group_key, members) in enumerate(groups, 1):
                        write(one_call(client, arm, members[0], kwargs, backend))
                        futures = [pool.submit(one_call, client, arm, c, kwargs, backend)
                                   for c in members[1:]]
                        for future in as_completed(futures):
                            write(future.result())
                        cell = tally[(mode, label, repeat)]
                        print("  group {:>3d}/{:<3d} {:<32s} n={:<3d} done={:<5d} ok={:<5d} "
                              "err={:<3d} usd={:>7.3f} elapsed={:.0f}s".format(
                                  g, len(groups), Path(group_key[0]).name, len(members),
                                  cell["calls"], cell["ok"], cell["error"], cell["usd"],
                                  time.perf_counter() - started_all), flush=True)
            except KeyboardInterrupt:
                interrupted = True
                print("\n[n3h] INTERRUPTED after {} rows".format(written), flush=True)
    return {"written": written, "tally": tally, "interrupted": interrupted,
            "wall_s": time.perf_counter() - started_all}


# --------------------------------------------------------------------------- #
# Printing                                                                     #
# --------------------------------------------------------------------------- #
def launch_questions(arm, repeats: int, log_path: Path) -> str:
    return """\
================================================================================
FOUR LAUNCH QUESTIONS (house experiment rules), answered before the
first paid call
================================================================================
1. PURPOSE.  The N3 generation log for the {arm} arm ({model}): 640 items (220
   costly_accepted, their 220 V3 twins, 200 benign controls) x {{{modes}}} x
   thinking {label} x {repeats} repeats, under prompt l1-prompt-1.1.0.  The
   numbers land in the new results subsection on stated acceptance of cost:
   intent fidelity (flag rate on the accepted items, false acceptance on the
   twins and the controls), disposition correctness under policy v1.1.0 per
   gate, and the channel value (approver simulated with the true intent versus
   the model's flag).
2. EXPECTED RESULT.  The flag is set on most costly_accepted items and on few
   twins or controls; the benign controls emit the same operation lists as in
   their v1.0.0 E1 runs.  If the flag rate on the accepted items is low, the
   channel does not carry intent at this prompt and the section reports that;
   if false acceptance is high, the override path is unsafe without the hard
   ceiling and the section reports the rate as the dangerous error.
3. CONTAMINATION.  Append-only log keyed by (mode, thinking, repeat, item_id),
   flushed per row; completed keys are skipped on restart, error rows retried.
   A log written by another arm or another prompt version is refused.  The
   output directory is new (results/n3_<arm>/); no E1 file is read for writing.
   Wall time is a network measurement.
   Log: {log}
4. DATA ACCURACY.  Fatal before the first call: suite v0.2 sha256, schema
   v1.0.0 sha256, schema v1.1.0 sha256, extension sha256 and its manifest; the
   v1.1.0 system prompt; for every v0.2 item the v1.1.0 user message equals the
   v1.0.0 one and the v1.0.0 fingerprint equals the published prompt_hash; for
   every costly_accepted item the user message equals its twin's with the
   instruction replaced; instance files hash-checked against the manifest from
   the instances_v10 snapshot.
================================================================================""".format(
        arm=arm.arm, model=arm.model, modes=", ".join(arm.modes),
        label=gh.label_text(arm.thinking[0][0]), repeats=repeats, log=log_path)


def launch_questions_neg(arm, repeats: int, log_path: Path) -> str:
    return """\
================================================================================
FOUR LAUNCH QUESTIONS (house experiment rules), answered before the
first paid call: the negated-acceptance control
================================================================================
1. PURPOSE.  Whether the stated-acceptance flag answers the vocabulary of delay
   or an explicit acceptance.  The {arm} arm ({model}): 220 costly_negated items
   (the V3 twins with a clause that refuses the knock-on delay, gold intent
   false) x {{{modes}}} x thinking {label} x {repeats} repeats, under prompt
   l1-prompt-1.1.0.  A flag set here is the sharpest false acceptance.  The
   numbers land in the intent-fidelity table as one more control column and
   in the false-acceptance profile.
2. EXPECTED RESULT.  The flag rate is at most the arm's rate on the V3 twins.
   If an arm still flags negated items, implied displacement is read as
   acceptance and the hard ceiling tau_hard is what contains it; if all arms
   drop to zero, the negation is read correctly.  Either outcome is reported.
3. CONTAMINATION.  New output directory (results/n3neg_<arm>/), never a
   resume into results/n3_<arm>/; append-only log keyed by (mode, thinking,
   repeat, item_id); a log of another arm, prompt version or prompt text is
   refused.  suite_ext.jsonl and manifest.json are read, never written.
   Wall time is a network measurement.
   Log: {log}
4. DATA ACCURACY.  Fatal before the first call: suite v0.2, schema v1.0.0 and
   v1.1.0, suite_ext.jsonl and suite_ext_neg.jsonl sha256 and their
   manifests; the v1.1.0 system prompt; every V3 twin rendered and checked
   against its v1.0.0 render and published prompt_hash; for every
   costly_negated item the user message equals its twin's with the
   instruction replaced; instance files hash-checked against the manifest
   from the instances_v10 snapshot.
================================================================================\
""".format(arm=arm.arm, model=arm.model, modes=", ".join(arm.modes),
           label=gh.label_text(arm.thinking[0][0]), repeats=repeats, log=log_path)


def print_plan(arm, args, stats: dict, plan: list, done: set, log_path: Path,
               resume: tuple, checks: dict) -> None:
    backend = BACKENDS[arm.backend]
    rows, errors, broken = resume
    print("\nCALL PLAN  (arm {}, model {}, wire {})".format(arm.arm, arm.model, backend.wire))
    print("  items            : {} per pass ({})".format(stats["items"], ", ".join(
        "{} {}".format(k, v) for k, v in args.item_set_counts.items())))
    print("  modes            : {}".format(", ".join(arm.modes)))
    print("  prompt checks    : {}".format(checks))
    print("  groups           : {} | distinct prefixes per pass: {}".format(
        stats["groups"], stats["cache_writes_per_pass"]))
    schema = wire_schema(arm)
    print("  M_constrained    : {} ({})".format(
        backend.constrained,
        "no schema on the wire" if schema is None else
        "canonical v1.1.0 schema, flag required"))
    print("  thinking         : {}".format("; ".join(
        "{} -> {}".format(gh.label_text(lab), json.dumps(body) if body else "no field sent")
        for lab, body in arm.thinking)))
    print("  repeats          : {} | max_tokens {} | workers {}".format(
        args.repeats, args.max_tokens, args.workers))
    total = stats["items"] * args.repeats * len(arm.modes) * len(arm.thinking)
    print("  calls            : {} planned in full".format(total))
    if args.limit:
        print("  --limit {}: the plan is truncated to its first {} calls".format(
            args.limit, args.limit))
    print("  already logged   : {} rows, {} API errors{}".format(
        rows, errors, ", {} torn lines".format(broken) if broken else ""))
    print("  complete keys    : {} | this run would make {} calls".format(len(done), len(plan)))
    print("  log              : {}".format(log_path))


def projection(arm, args, stats: dict) -> dict:
    """USD per arm at each listed price base, pilot output and 3x pilot output."""
    anthropic = BACKENDS[arm.backend].wire == WIRE_ANTHROPIC
    out = {}
    for label, base in arm.prices:
        cells = {"pilot": 0.0, "3x_out": 0.0}
        for mode in arm.modes:
            for lab, _ in arm.thinking:
                tokens = arm.out_tokens[lab]
                cells["pilot"] += gh.project_pass(arm, stats, mode, tokens, base,
                                                  anthropic)["usd"] * args.repeats
                cells["3x_out"] += gh.project_pass(arm, stats, mode, 3 * tokens, base,
                                                   anthropic)["usd"] * args.repeats
        out[label] = cells
    return out


def measured_projection(arm, args, stats: dict) -> dict:
    """USD from the E1 log of the same arm: measured usage per call, N3 call count.

    The E1 runs used the same prompt builder over the same instances, the same
    cache split and the same call order, so their per-call usage (cached and
    uncached input, output) is the best available estimate.  Each logged call
    is re-priced at the N3 price base; the mean per (mode, thinking) cell is
    multiplied by the N3 calls of that cell.  A mode E1 never ran for this arm
    (sol M_free) borrows the other mode's mean and is flagged.
    """
    path = sg.CODE_DIR.parent / "results" / "grid_e1_hosted_{}".format(arm.arm) / \
        "proposals_raw.dedup.jsonl"
    if not path.exists():
        return {"source": None}
    label = arm.thinking[0][0]
    sums: dict = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("thinking") != label or row.get("outcome") == OUTCOME_ERROR:
                continue
            cell = sums.setdefault(row["mode"], [0, {lab: 0.0 for lab, _ in arm.prices}])
            cell[0] += 1
            for lab, base in arm.prices:
                cell[1][lab] += gh.call_usd(base, row.get("usage") or {})
    out = {"source": str(path), "borrowed_modes": [], "usd": {lab: 0.0 for lab, _ in arm.prices}}
    for mode in arm.modes:
        src = mode if mode in sums else next(iter(sums), None)
        if src is None:
            return {"source": None}
        if src != mode:
            out["borrowed_modes"].append("{} <- {}".format(mode, src))
        n, usd = sums[src]
        calls = stats["items"] * args.repeats
        for lab, _ in arm.prices:
            out["usd"][lab] += usd[lab] / n * calls
    return out


def print_projection(arm, args, stats: dict) -> dict:
    proj = projection(arm, args, stats)
    print("\nPROJECTED COST  (prices retrieved {}; {})".format(arm.price_date, arm.price_source))
    print("  token model: {:.2f} chars/token, pilot output {}/call ({})".format(
        arm.chars_per_token, arm.out_tokens[arm.thinking[0][0]], arm.pilot_note))
    for label, cells in proj.items():
        print("  {:<30s} USD {:>7.2f} at pilot output, USD {:>7.2f} at 3x output".format(
            label, cells["pilot"], cells["3x_out"]))
    measured = measured_projection(arm, args, stats)
    if measured.get("source"):
        for label, usd in measured["usd"].items():
            print("  {:<30s} USD {:>7.2f} from E1-measured usage per call{}".format(
                label, usd, " (borrowed: {})".format(", ".join(measured["borrowed_modes"]))
                if measured["borrowed_modes"] else ""))
    proj["e1_measured"] = measured
    return proj


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arm", required=True, choices=sorted(ARMS))
    ap.add_argument("--out", default=None, help="output dir (default results/n3_<arm>)")
    ap.add_argument("--limit", type=int, default=0, help="cap the plan to its first N CALLS")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--repeats", type=int, default=REPEATS)
    ap.add_argument("--max-tokens", type=int, default=gh.MAX_TOKENS)
    ap.add_argument("--top-k", type=int, default=gh.TOP_K)
    ap.add_argument("--timeout-s", type=float, default=240.0)
    ap.add_argument("--max-retries", type=int, default=4)
    ap.add_argument("--mock", action="store_true", help="offline transport, no network, no key")
    ap.add_argument("--mock-fail-every", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true", help="plan and cost only, call nothing")
    ap.add_argument("--item-sets", nargs="+", default=list(ITEM_SETS), choices=ALL_ITEM_SETS,
                    help="item sets to plan (default: the three published N3 sets); "
                         "costly_negated must run alone")
    ap.add_argument("--modes", default="both", choices=sorted(MODE_CHOICES),
                    help="both modes (default) or the constrained mode only")
    args = ap.parse_args()

    item_sets = tuple(s for s in ALL_ITEM_SETS if s in args.item_sets)
    negated = NEG_SET in item_sets
    if negated and item_sets != (NEG_SET,):
        raise SystemExit("REFUSING TO RUN: costly_negated runs alone (its own log)")
    arm = ARMS[args.arm]
    if MODE_CHOICES[args.modes] is not None:
        arm = dataclasses.replace(arm, modes=MODE_CHOICES[args.modes])
    backend = BACKENDS[arm.backend]
    results_dir = sg.CODE_DIR.parent / "results"
    out_dir = Path(args.out) if args.out else (
        results_dir / "{}_{}".format("n3neg" if negated else "n3", arm.arm))
    if negated and out_dir.resolve().name == "n3_{}".format(arm.arm):
        raise SystemExit("REFUSING TO RUN: the negated set never writes into "
                         "results/n3_{}".format(arm.arm))
    if not negated and out_dir.resolve().name.startswith("n3neg_"):
        raise SystemExit("REFUSING TO RUN: an n3neg_ directory holds the negated set only")
    log_path = out_dir / "proposals_raw.jsonl"
    print((launch_questions_neg if negated else launch_questions)(arm, args.repeats, log_path))

    items, inputs, check_twins = load_run_item_sets(item_sets)
    args.item_set_counts = inputs["item_set_counts"]
    for key in ("suite_sha256", "schema_sha256", "schema_v11_sha256", "suite_ext_sha256",
                "suite_ext_manifest_sha256", "suite_ext_neg_sha256",
                "suite_ext_neg_manifest_sha256"):
        if key in inputs:
            print("[n3h] {:<29s} {} OK".format(key, inputs[key]))
    print("[n3h] prompt version {} OK".format(PROMPT_VERSION))
    if backend.requires_json_word and "json" not in SYSTEM_PROMPT.lower():
        raise SystemExit("REFUSING TO RUN: JSON-object mode needs the word 'json'")

    instances = sg.Instances()
    started = time.perf_counter()
    prepared, checks = prepare(items, instances, args.top_k,
                               published_hashes(PUBLISHED_PROMPT_LOG), check_twins)
    print("[n3h] {} prompts rendered, split and checked in {:.1f}s".format(
        len(prepared), time.perf_counter() - started))
    if checks["v10_hash_absent"]:
        print("[n3h] WARNING: {} v0.2 items had no published prompt_hash to compare "
              "({} absent)".format(checks["v10_hash_absent"], PUBLISHED_PROMPT_LOG))

    stats = gh.prompt_stats(prepared, len(SYSTEM_PROMPT))
    done, rows, errors, broken = read_completed(
        log_path, arm, {p.item["item_id"]: p.prompt_hash for p in prepared})
    plan = [c for c in gh.build_plan(arm, prepared, args.repeats, args.limit)
            if gh.row_key(c["mode"], c["thinking"], c["repeat"],
                          c["prep"].item["item_id"]) not in done]
    print_plan(arm, args, stats, plan, done, log_path, (rows, errors, broken), checks)
    proj = print_projection(arm, args, stats)

    if args.dry_run:
        print("\nNO CALL MADE (--dry-run).")
        return 0
    if not plan:
        print("\nNothing to do: every planned key is already logged.")
        return 0

    transport = None
    api_key = None
    if args.mock:
        by_instruction = {p.item["instruction"]: p.item for p in prepared}
        transport = N3MockTransport(arm, by_instruction, fail_every=args.mock_fail_every)
        api_key = "mock-key-not-a-real-key"
        print("\n[n3h] MOCK TRANSPORT: no network, no key, no cost.")
    else:
        loaded = load_env()
        if not os.environ.get(backend.api_key_env):
            print("\nREFUSING TO RUN: {} is not set ({} names loaded from the project "
                  ".env).".format(backend.api_key_env, len(loaded)))
            return 2
        print("\n[n3h] key {} present (never printed).".format(backend.api_key_env))

    out_dir.mkdir(parents=True, exist_ok=True)
    client = ChatClient(arm.backend, model=arm.model, api_key=api_key,
                        max_tokens=args.max_tokens, timeout_s=args.timeout_s,
                        max_retries=args.max_retries,
                        retry_sleep_s=0.0 if args.mock else 2.0, transport=transport)
    try:
        result = run(arm, args, plan, log_path, client)
    except KeyboardInterrupt:
        result = {"written": None, "tally": {}, "interrupted": True, "wall_s": None}
    interrupted = bool(result.get("interrupted"))

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    schema = wire_schema(arm)
    meta = {
        "date": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "analysis": "N3 stated acceptance of cost, protocol v1.1.0",
        "arm": arm.arm, "model": arm.model, "backend": arm.backend, "wire": backend.wire,
        "modes": list(arm.modes), "thinking": [lab for lab, _ in arm.thinking],
        "thinking_bodies": {str(lab): body for lab, body in arm.thinking},
        "repeats": args.repeats, "items": stats["items"], "groups": stats["groups"],
        "item_set_counts": inputs["item_set_counts"],
        "max_tokens": args.max_tokens, "workers": args.workers,
        "timeout_s": args.timeout_s, "max_retries": args.max_retries,
        "suite_sha256": inputs["suite_sha256"],
        "suite_ext_sha256": inputs["suite_ext_sha256"],
        "suite_ext_manifest_sha256": inputs["suite_ext_manifest_sha256"],
        "item_sets": list(item_sets),
        "suite_ext_neg_sha256": inputs.get("suite_ext_neg_sha256"),
        "suite_ext_neg_manifest_sha256": inputs.get("suite_ext_neg_manifest_sha256"),
        "schema_sha256": inputs["schema_sha256"],
        "schema_v11_sha256": inputs["schema_v11_sha256"],
        "schema_version": ops_mod.SCHEMA_V11_VERSION,
        "wire_schema": None if schema is None else "canonical",
        "wire_schema_sha256": None if schema is None else hashlib.sha256(
            json.dumps(schema, sort_keys=True).encode("utf-8")).hexdigest(),
        "prompt_version": PROMPT_VERSION, "top_k": args.top_k,
        "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
        "prompt_checks": checks,
        "instance_root": str(sg.INSTANCE_ROOT),
        "cache_boundary": gh.CACHE_BOUNDARY,
        "mock": bool(args.mock), "interrupted": interrupted,
        "planned_calls": len(plan), "rows_written": result["written"],
        "wall_s": result["wall_s"],
        "price_base": arm.prices[0][0], "price_date": arm.price_date,
        "usd_projected": proj,
        "usd_estimated": sum(c["usd"] for c in result["tally"].values()),
        "per_config": {"{}|{}|r{}".format(m, t, r): v
                       for (m, t, r), v in result["tally"].items()},
        "dedupe_rule": "last row per (arm, mode, thinking, repeat, item_id) wins; an "
                       "earlier row for a key is a superseded API error",
    }
    meta_path = out_dir / "run_meta_{}.json".format(stamp)
    meta_path.write_text(json.dumps(meta, indent=1, default=str))
    print("\n[n3h] raw log : {}".format(log_path))
    print("[n3h] meta    : {}".format(meta_path))
    if not args.mock:
        print("[n3h] estimated spend this session: USD {:.2f}".format(meta["usd_estimated"]))
    return 130 if interrupted else 0


if __name__ == "__main__":
    sys.exit(main())
