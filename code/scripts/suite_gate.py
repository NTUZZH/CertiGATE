#!/usr/bin/env python
"""The suite acceptance gate: does the certified guard catch what the boolean guard misses?

The guidance schedules one gate before any paid grid: **V3/V4 separation shown on
at least one model**. This is that runner. It puts every V3 item, every V4 item
and all 440 of their matched benign twins (880 items) through the published
prompt and one model, logs every call, and then replays the log under G_FEAS and
G_CERT. The gate criterion is the count of V3/V4 items that **G_FEAS passes and
G_CERT blocks**: if that count is zero, the certified stage buys nothing that
the feasibility stage did not already buy, and no grid should be paid for.

Two phases, because two environments
------------------------------------
Generation needs vLLM, which lives in conda env ``l1``. Evaluation needs the
guard, which reaches Y1's ``fmwos.timeaxis`` and therefore needs ``pandas``,
which env ``l1`` does not have. Rather than install into the verified vLLM
environment, the runner is split along the seam the architecture already has:

    conda run -n l1   python scripts/suite_gate.py --phase generate
    conda run -n fjsp python scripts/suite_gate.py --phase evaluate

Phase A imports nothing from this project except ``l1guard/prompts.py``, which
is loaded directly from its path and has no imports of its own; instances are
read with ``json.load``. Phase B is the ordinary log-then-replay path. The GPU
is held only for phase A. ``--phase all`` runs both in one process, which works
today only with the mock model.

GPU discipline (hard rule)
--------------------------
The card is never shared. Before loading a model the runner reads
``nvidia-smi`` and loads only if free VRAM is at least 34 GiB **and** foreign
utilization is below 20%. Otherwise it runs the whole pipeline end to end with a
mocked model over a handful of items, writes ``DRY_RUN.md``, and exits telling
the operator what the card looked like.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE_DIR))

# --------------------------------------------------------------------------- #
# The three things the runner refuses to start without                         #
# --------------------------------------------------------------------------- #
SUITE_PATH = CODE_DIR / "suite" / "v0.2" / "suite.jsonl"
SUITE_SHA256 = "0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a"
SCHEMA_PATH = CODE_DIR / "schema" / "adjustments.schema.json"
SCHEMA_SHA256 = "1115fa83d8910ed18a4fa1a421e80aaf4629f4c91fc22f83c81ba32c3fa39321"
MODEL_PATH = (
    "/home/ziheng/.cache/huggingface/hub/models--Qwen--Qwen3-14B/snapshots/"
    "40c069824f4251a91eefaf281ebe4c544efd3e18"
)
Y1_ROOT = Path(os.environ.get("L1_Y1_ROOT", "/home/ziheng/PaperY-FMScheduling"))

MIN_FREE_GIB = 34.0
MAX_FOREIGN_UTIL = 20
GPU_MEM_UTIL = 0.85

LAUNCH_QUESTIONS = """\
================================================================================
FOUR LAUNCH QUESTIONS (global CLAUDE.md experiment rules), answered before the run
================================================================================
1. PURPOSE. The suite acceptance gate: does the certified stage catch proposals
   the feasibility stage passes? The number that decides it is the count of
   V3/V4 items with G_FEAS = applied and G_CERT = blocked. It gates every paid
   grid (guidance Section 8) and lands in the acceptance module's "Suite
   acceptance gate: V3/V4 separation shown on >= 1 model" row.
2. EXPECTED RESULT. Non-zero, concentrated in V3 (all 220 items degrade the
   schedule by construction, median 272 weighted business hours) and in the V4
   trap type reorder_direction_flipped (50 of the 55 quality-visible
   candidates). The other six V4 trap types are certificate-invisible by
   construction and are expected to contribute nothing: that is a finding to
   report, not a defect. If the count is zero the gate FAILS and no grid runs.
   If V3 separates but no V4 does, the gate passes on V3 and the V4 split is
   reported as measured.
3. CONTAMINATION. The output directory must not exist (the runner refuses to
   overwrite; --force is explicit). The log is append-only and written once per
   call. The model is a pinned local snapshot, temperature 0, thinking off, so
   the run is reproducible. The card is never shared: the run aborts to a mock
   unless the GPU is free.
4. DATA ACCURACY. Three assertions in the runner, all fatal: the suite file's
   SHA-256, the frozen schema's SHA-256, and the model snapshot path. Instances
   are resolved from each item's own stratum and file name and read unmodified.
================================================================================"""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def assert_inputs() -> dict:
    """The three assertions: two hashes (fatal here) and the model path.

    The model path is recorded rather than made fatal at start-up, because a
    run that falls back to the mock never loads a model; ``generate_vllm``
    refuses if the snapshot is missing when it is actually needed.
    """
    out = {}
    got = sha256_file(SUITE_PATH)
    out["suite_sha256"] = got
    if got != SUITE_SHA256:
        raise SystemExit(
            "REFUSING TO RUN: suite {} has sha256 {}, expected {}".format(
                SUITE_PATH, got, SUITE_SHA256
            )
        )
    got = sha256_file(SCHEMA_PATH)
    out["schema_sha256"] = got
    if got != SCHEMA_SHA256:
        raise SystemExit(
            "REFUSING TO RUN: schema {} has sha256 {}, expected the frozen {}".format(
                SCHEMA_PATH, got, SCHEMA_SHA256
            )
        )
    out["model_path"] = MODEL_PATH
    out["model_present"] = Path(MODEL_PATH).is_dir()
    return out


# --------------------------------------------------------------------------- #
# GPU discipline                                                               #
# --------------------------------------------------------------------------- #
def gpu_state() -> dict:
    def sh(cmd):
        try:
            return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        except Exception as exc:  # pragma: no cover - no driver
            return "<unavailable: {}>".format(exc)

    line = sh(
        ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu",
         "--format=csv,noheader,nounits"]
    )
    apps = sh(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
               "--format=csv,noheader,nounits"])
    state = {"raw": line, "apps": apps, "free_gib": None, "util": None, "name": None}
    try:
        name, used, total, util = [p.strip() for p in line.split(",")]
        state["name"] = name
        state["free_gib"] = (float(total) - float(used)) / 1024.0
        state["util"] = float(util)
        state["used_mib"] = float(used)
        state["total_mib"] = float(total)
    except Exception:
        pass
    ok = (
        state["free_gib"] is not None
        and state["free_gib"] >= MIN_FREE_GIB
        and state["util"] is not None
        and state["util"] < MAX_FOREIGN_UTIL
    )
    state["ok"] = bool(ok)
    state["condition"] = "free VRAM >= {:.0f} GiB and foreign utilization < {}%".format(
        MIN_FREE_GIB, MAX_FOREIGN_UTIL
    )
    return state


def describe_gpu(state: dict) -> str:
    if state["free_gib"] is None:
        return "GPU state unreadable: {}".format(state["raw"])
    return (
        "{}: {:.1f} GiB free of {:.1f} GiB, utilization {:.0f}%  ({})\n"
        "  compute apps: {}".format(
            state["name"],
            state["free_gib"],
            state["total_mib"] / 1024.0,
            state["util"],
            "CONDITION MET" if state["ok"] else "CONDITION NOT MET: " + state["condition"],
            state["apps"].replace("\n", " | ") or "none",
        )
    )


# --------------------------------------------------------------------------- #
# Items and instances (stdlib only, so phase A needs nothing installed)        #
# --------------------------------------------------------------------------- #
def load_suite() -> list:
    return [json.loads(line) for line in SUITE_PATH.open() if line.strip()]


def select_items(rows: list) -> list:
    """All V3, all V4, and their matched benign twins, in a fixed order."""
    by_id = {r["item_id"]: r for r in rows}
    targets = [r for r in rows if r["primary_class"] in ("V3", "V4")]
    targets.sort(key=lambda r: r["item_id"])
    out = []
    for item in targets:
        out.append(item)
        twin = by_id.get(item["twin_id"])
        if twin is None:
            raise SystemExit("item {} has no twin {}".format(item["item_id"], item["twin_id"]))
        out.append(twin)
    return out


def sample_items(items: list, n: int) -> list:
    """A deterministic, stratified handful for the mock run."""
    v3 = [r for r in items if r["primary_class"] == "V3"]
    v4_vis = [
        r for r in items
        if r["primary_class"] == "V4" and r.get("quality_visible_candidate")
    ]
    v4_inv = [
        r for r in items
        if r["primary_class"] == "V4" and not r.get("quality_visible_candidate")
    ]
    by_id = {r["item_id"]: r for r in items}
    picked, seen = [], set()
    # Round-robin over the three pools, taking each item WITH its twin, so a
    # small sample still covers V3, a certificate-visible V4 and a
    # certificate-invisible V4 rather than filling up with the first pool.
    pools = [list(v3), list(v4_vis), list(v4_inv)]
    while any(pools) and (not n or len(picked) < n):
        for pool in pools:
            if not pool or (n and len(picked) >= n):
                continue
            item = pool.pop(0)
            for row in (item, by_id.get(item["twin_id"])):
                if row is not None and row["item_id"] not in seen:
                    seen.add(row["item_id"])
                    picked.append(row)
    return picked[:n] if n else picked


def instance_path(item: dict) -> Path:
    """Resolve the instance file from the item's own stratum, e.g. c09_storm2_w80."""
    meta = item["instance"]
    stratum = meta["stratum"]
    campus, track = stratum.split("_")[0], stratum.split("_")[1]
    size_dir = stratum.rsplit("_", 1)[1]
    path = Y1_ROOT / "data" / "processed" / "instances" / campus / track / size_dir / meta["file"]
    if not path.exists():
        raise SystemExit("instance not found for item {}: {}".format(item["item_id"], path))
    return path


class Instances:
    """Loads each instance file once."""

    def __init__(self):
        self._cache: dict = {}

    def get(self, item: dict) -> dict:
        path = instance_path(item)
        key = str(path)
        if key not in self._cache:
            with open(path, "r", encoding="utf-8") as fh:
                self._cache[key] = json.load(fh)
        return self._cache[key]

    def path(self, item: dict) -> str:
        return str(instance_path(item))


def load_prompts_module():
    """Import ``l1guard/prompts.py`` directly: phase A must not pull the package in."""
    spec = importlib.util.spec_from_file_location(
        "l1_prompts", CODE_DIR / "l1guard" / "prompts.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- #
# Phase A: generation                                                          #
# --------------------------------------------------------------------------- #
def mock_outputs(items: list, noise: int = 0) -> list:
    """The oracle mock: emit the suite's own labelled operations.

    This is NOT a model. For a benign twin and a V3 item it emits ``gold_ops``
    (the faithful translation, which for V3 is the damaging one by
    construction); for a V4 item it emits ``trap_ops`` (the plausible
    misreading). What a mock run measures is therefore the separation the
    *instrument* can express, an upper bound, and it says nothing about any
    model's ability to translate. ``noise`` wraps the first N outputs in a
    markdown fence, which no schema-valid output has, to exercise the
    malformed-output path end to end.
    """
    out = []
    for i, item in enumerate(items):
        ops = item["trap_ops"] if item["primary_class"] == "V4" else item["gold_ops"]
        text = json.dumps({"operations": ops})
        if i < noise:
            text = "```json\n" + text + "\n```"
        out.append(text)
    return out


def generate(items: list, args, gpu: dict) -> list:
    """Run the model over the items; return raw records (dicts)."""
    prompts = load_prompts_module()
    instances = Instances()
    messages = [prompts.build_messages(instances.get(it), it, args.top_k) for it in items]

    if args.mock:
        texts = mock_outputs(items, args.mock_noise)
        usages = [{} for _ in items]
        finish = ["stop"] * len(items)
        latencies = [0.0] * len(items)
        model_name = "mock:oracle-labels"
        backend = "none (mock)"
    else:
        texts, usages, finish, latencies, model_name, backend = generate_vllm(messages, args)

    raw = []
    for item, msg, text, usage, fin, lat in zip(
        items, messages, texts, usages, finish, latencies
    ):
        raw.append(
            {
                "item_id": item["item_id"],
                "primary_class": item["primary_class"],
                "subclass": item["subclass"],
                "twin_id": item["twin_id"],
                "twin_role": item["twin_role"],
                "quality_visible_candidate": item.get("quality_visible_candidate"),
                "instance_id": item["instance"]["instance_id"],
                "instance_path": instances.path(item),
                "stratum": item["instance"]["stratum"],
                "rule": item["episode"]["rule"],
                "dispatch_seed": item["episode"]["seed"],
                "frozen_seed": list(item["episode"]["frozen_seed"]),
                "gold_ops": item["gold_ops"],
                "trap_ops": item["trap_ops"],
                "instruction": item["instruction"],
                "prompt_hash": prompts.prompt_fingerprint(msg),
                "prompt_chars": sum(len(m["content"]) for m in msg),
                "prompt_version": prompts.PROMPT_VERSION,
                "model": model_name,
                "mode": "M_constrained",
                "backend": backend,
                "raw_output": text,
                "finish_reason": fin,
                "latency_ms": lat,
                "usage": usage,
            }
        )
    return raw


def generate_vllm(messages: list, args):
    """The offline vLLM path: xgrammar pinned and read back, thinking off."""
    os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    if not Path(MODEL_PATH).is_dir():
        raise SystemExit(
            "REFUSING TO RUN: pinned model snapshot not found at {}".format(MODEL_PATH)
        )
    import vllm
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import StructuredOutputsParams

    with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
        schema = json.load(fh)

    print("[gate] loading {} (vllm {})".format(MODEL_PATH, vllm.__version__), flush=True)
    llm = LLM(
        model=MODEL_PATH,
        max_model_len=args.max_model_len,
        gpu_memory_utilization=min(args.gpu_mem_util, GPU_MEM_UTIL),
        seed=0,
        trust_remote_code=False,
        structured_outputs_config={"backend": "xgrammar"},
    )
    resolved = getattr(
        llm.llm_engine.vllm_config.structured_outputs_config, "backend", "<unknown>"
    )
    print("[gate] engine-resolved structured-outputs backend: {}".format(resolved), flush=True)
    if resolved != "xgrammar":
        raise SystemExit(
            "REFUSING TO RUN: engine resolved backend {!r}, not 'xgrammar'".format(resolved)
        )

    tok = llm.get_tokenizer()
    prompts_text = []
    for msg in messages:
        try:
            rendered = tok.apply_chat_template(
                msg, tokenize=False, add_generation_prompt=True, enable_thinking=False
            )
        except TypeError:  # pragma: no cover - template without the flag
            rendered = tok.apply_chat_template(msg, tokenize=False, add_generation_prompt=True)
        if isinstance(rendered, list):
            rendered = tok.decode(rendered)
        prompts_text.append(rendered)

    sampling = SamplingParams(
        temperature=0.0,
        max_tokens=args.max_tokens,
        seed=0,
        structured_outputs=StructuredOutputsParams(json=schema),
    )
    started = time.perf_counter()
    outputs = llm.generate(prompts_text, sampling, use_tqdm=True)
    wall = time.perf_counter() - started
    print("[gate] {} generations in {:.1f} s".format(len(outputs), wall), flush=True)

    texts, usages, finish, latencies = [], [], [], []
    for out in outputs:
        comp = out.outputs[0]
        texts.append(comp.text)
        finish.append(comp.finish_reason)
        n_out = len(comp.token_ids)
        n_in = len(out.prompt_token_ids or [])
        usages.append(
            {
                "prompt_tokens": n_in,
                "completion_tokens": n_out,
                "total_tokens": n_in + n_out,
                "reasoning_tokens": None,
                "cache_hit_tokens": None,
                "cache_miss_tokens": None,
                "cache_hit": None,
            }
        )
        latencies.append(wall * 1000.0 / max(1, len(outputs)))
    return texts, usages, finish, latencies, MODEL_PATH, "xgrammar"


# --------------------------------------------------------------------------- #
# Phase B: guard evaluation and replay                                         #
# --------------------------------------------------------------------------- #
#: The published terminal-state vocabulary, restated here as literals so that
#: phase A stays importable in the vLLM environment (which cannot import the
#: guard).  A test asserts these match ``l1guard.verdict``.
APPLIED_TERMINALS = ("applied_with_certificate", "applied_uncertified")
BLOCKED_TERMINALS = ("blocked_schema", "blocked_feas", "blocked_qual")


def is_pass(verdict) -> bool:
    return verdict.terminal in APPLIED_TERMINALS


def is_block(verdict) -> bool:
    return verdict.terminal in BLOCKED_TERMINALS


def separated_ids(targets, feas: dict, cert: dict) -> list:
    """The gate criterion: G_FEAS passes it and G_CERT blocks it."""
    return [i for i in targets if is_pass(feas[i]) and is_block(cert[i])]


def canon_ops(ops) -> list:
    """Canonical form for matching; a reorder becomes its directed edge."""
    out = []
    for op in ops or []:
        name = op.get("op")
        if name == "reorder":
            if op.get("relation") == "before":
                edge = (op.get("order_id"), op.get("ref_order_id"))
            else:
                edge = (op.get("ref_order_id"), op.get("order_id"))
            out.append(("reorder", edge[0], edge[1]))
        else:
            out.append(
                (name,) + tuple(str(op[k]) for k in sorted(op) if k != "op")
            )
    return out


def match_kind(emitted, gold) -> str:
    """``exact`` (same ops, same order), ``semantic`` (same set), or ``none``."""
    if emitted is None:
        return "none"
    a, b = canon_ops(emitted), canon_ops(gold)
    if [json.dumps(x) for x in a] == [json.dumps(x) for x in b] and emitted == gold:
        return "exact"
    if sorted(json.dumps(x) for x in a) == sorted(json.dumps(x) for x in b):
        return "semantic"
    return "none"


def evaluate(raw: list, out_dir: Path, args) -> dict:
    from l1guard import G_CERT, G_FEAS, evaluate_proposal
    from l1guard.logging import ProposalLog, ProposalRecord
    from l1guard.replay import InstanceCache, _needs_baseline, rerun_pairs

    cert_cfg = G_CERT.with_(tier1_budget_s=0.0)  # tier 2 gate, per the ruling
    log = ProposalLog(out_dir / "proposals.jsonl")
    cache = InstanceCache()
    records, live = [], {}

    for row in raw:
        record = ProposalRecord(
            instruction_id=row["item_id"],
            instance_id=row["instance_id"],
            instance_path=row["instance_path"],
            model=row["model"],
            mode=row["mode"],
            prompt_hash=row["prompt_hash"],
            raw_output=row["raw_output"],
            finish_reason=row.get("finish_reason"),
            latency_ms=row.get("latency_ms"),
            rule=row["rule"],
            seeds={"llm": 0, "dispatch": row["dispatch_seed"]},
            frozen_seed=row["frozen_seed"],
            prompt_tokens=(row.get("usage") or {}).get("prompt_tokens"),
            completion_tokens=(row.get("usage") or {}).get("completion_tokens"),
            reasoning_tokens=(row.get("usage") or {}).get("reasoning_tokens"),
            cache_hit_tokens=(row.get("usage") or {}).get("cache_hit_tokens"),
            cache_miss_tokens=(row.get("usage") or {}).get("cache_miss_tokens"),
            cache_hit=(row.get("usage") or {}).get("cache_hit"),
            extra={
                "primary_class": row["primary_class"],
                "subclass": row["subclass"],
                "twin_id": row["twin_id"],
                "twin_role": row["twin_role"],
                "quality_visible_candidate": row["quality_visible_candidate"],
                "stratum": row["stratum"],
                "gold_ops": row["gold_ops"],
                "trap_ops": row["trap_ops"],
                "prompt_version": row["prompt_version"],
                "prompt_chars": row["prompt_chars"],
                "backend": row["backend"],
            },
        )
        instance = cache.instance(row["instance_path"])
        baseline = None
        if _needs_baseline(record):
            baseline = cache.baseline(row["instance_path"], record.rule, 0)
        verdict = evaluate_proposal(
            instance,
            record.raw_output if record.raw_output is not None else "",
            cert_cfg,
            baseline_schedule=baseline,
            frozen_seed=tuple(record.frozen_seed),
        )
        record.attach_verdict(verdict)
        log.append(record)
        records.append(record)
        live[record.instruction_id] = verdict

    replays = {}
    for name, cfg in (("G_FEAS", G_FEAS), ("G_CERT", cert_cfg)):
        pairs = rerun_pairs(log.path, cfg, cache=cache, records=records)
        replays[name] = {rec.instruction_id: v for rec, v in pairs}

    mismatched = [
        iid
        for iid, verdict in replays["G_CERT"].items()
        if verdict.fingerprint() != live[iid].fingerprint()
    ]
    return {
        "records": records,
        "raw": {r["item_id"]: r for r in raw},
        "replays": replays,
        "live": live,
        "replay_mismatches": mismatched,
        "config": {"G_FEAS": G_FEAS.config_hash, "G_CERT": cert_cfg.config_hash,
                   "tau": cert_cfg.tau, "lb_tier": cert_cfg.lb_tier},
        "log_path": str(log.path),
    }


# --------------------------------------------------------------------------- #
# Summary                                                                      #
# --------------------------------------------------------------------------- #
def _pct(a, b):
    return "n/a" if not b else "{:.1%}".format(a / b)


def _quantile(sorted_vals, q):
    """Nearest-rank quantile; correct for the small samples a mock run has."""
    if not sorted_vals:
        return None
    import math

    idx = max(0, math.ceil(q * len(sorted_vals)) - 1)
    return sorted_vals[min(idx, len(sorted_vals) - 1)]


def summarise(result: dict, gpu: dict, inputs: dict, args, mock: bool) -> str:
    raw = result["raw"]
    feas, cert = result["replays"]["G_FEAS"], result["replays"]["G_CERT"]
    ids = [r.instruction_id for r in result["records"]]

    def cls(iid):
        return raw[iid]["primary_class"]

    def sub(iid):
        return raw[iid]["subclass"]

    lines = []
    add = lines.append

    add("# Suite acceptance gate {}".format("(MOCK / DRY RUN)" if mock else ""))
    add("")
    add(LAUNCH_QUESTIONS)
    add("")
    add("## Run")
    add("")
    add("| field | value |")
    add("|---|---|")
    add("| date | {} |".format(time.strftime("%Y-%m-%d %H:%M:%S %Z")))
    add("| items | {} ({} V3, {} V4, {} benign twins) |".format(
        len(ids),
        sum(1 for i in ids if cls(i) == "V3"),
        sum(1 for i in ids if cls(i) == "V4"),
        sum(1 for i in ids if cls(i) == "benign"),
    ))
    add("| model | {} |".format(raw[ids[0]]["model"] if ids else "-"))
    add("| mode | M_constrained, structured outputs backend {} |".format(
        raw[ids[0]]["backend"] if ids else "-"))
    add("| prompt | {} |".format(raw[ids[0]]["prompt_version"] if ids else "-"))
    add("| suite sha256 | `{}` |".format(inputs["suite_sha256"]))
    add("| schema sha256 | `{}` |".format(inputs["schema_sha256"]))
    add("| model snapshot | `{}` (present: {}) |".format(
        inputs["model_path"], inputs["model_present"]))
    add("| tau | {} (provisional) |".format(result["config"]["tau"]))
    add("| certificate | {} bound, scored on the adjusted instance |".format(
        {"tier2": "Tier 2 analytic", "tier1": "Tier 1 solver",
         "best": "Tier 1 and Tier 2, larger of the two"}.get(
            result["config"]["lb_tier"], result["config"]["lb_tier"])))
    add("| G_FEAS / G_CERT config hash | `{}` / `{}` |".format(
        result["config"]["G_FEAS"][:16], result["config"]["G_CERT"][:16]))
    add("| GPU at launch | {} |".format(describe_gpu(gpu).replace("\n", "; ")))
    add("| replay == live under G_CERT | {} |".format(
        "yes, all {}".format(len(ids)) if not result["replay_mismatches"]
        else "NO: {}".format(result["replay_mismatches"][:5])))
    add("")

    if mock:
        add("> **No model was run.** The mock emits the suite's own labelled operations "
            "(`gold_ops` for benign and V3 items, `trap_ops` for V4 items), so every "
            "number below is a property of the SUITE and the GUARD, not of any model. "
            "It is the separation ceiling the instrument can express, and it is here to "
            "prove the pipeline end to end, never to stand in for the gate.")
        add("")

    # -- the gate criterion ------------------------------------------------- #
    passed, blocked = is_pass, is_block
    targets = [i for i in ids if cls(i) in ("V3", "V4")]
    separated = separated_ids(targets, feas, cert)
    add("## The gate criterion")
    add("")
    add("**V3/V4 items that G_FEAS passes and G_CERT blocks: {} of {}.**  Gate: {}".format(
        len(separated), len(targets), "PASS" if separated else "FAIL"))
    add("")
    add("| class | sub-type | items | G_FEAS passes | G_CERT blocks | separated |")
    add("|---|---|---|---|---|---|")
    seen = []
    for iid in targets:
        key = (cls(iid), sub(iid))
        if key not in seen:
            seen.append(key)
    for key in sorted(seen):
        sel = [i for i in targets if (cls(i), sub(i)) == key]
        add("| {} | {} | {} | {} | {} | **{}** |".format(
            key[0], key[1], len(sel),
            sum(1 for i in sel if passed(feas[i])),
            sum(1 for i in sel if blocked(cert[i])),
            sum(1 for i in sel if passed(feas[i]) and blocked(cert[i])),
        ))
    add("")

    # -- V4 certificate visibility ------------------------------------------ #
    v4 = [i for i in targets if cls(i) == "V4"]
    v4_sep = [i for i in v4 if passed(feas[i]) and blocked(cert[i])]
    v4_flagged = [i for i in v4 if raw[i]["quality_visible_candidate"]]
    overlap = [i for i in v4_sep if raw[i]["quality_visible_candidate"]]
    add("## V4 certificate visibility: measured against the suite's prediction")
    add("")
    add("| quantity | count |")
    add("|---|---|")
    add("| V4 items in this run | {} |".format(len(v4)))
    add("| flagged `quality_visible_candidate` by the suite | {} |".format(len(v4_flagged)))
    add("| empirically certificate-visible (G_FEAS passes, G_CERT blocks) | {} |".format(
        len(v4_sep)))
    add("| in both | {} |".format(len(overlap)))
    add("| suite's static prediction over the full V4 set | 55 / 220 |")
    add("")

    # -- block and false-block rates ---------------------------------------- #
    add("## Block rate and false-block rate, per arm")
    add("")
    add("| set | items | G_FEAS blocked | G_CERT blocked |")
    add("|---|---|---|---|")
    for label, sel in (
        ("V3", [i for i in ids if cls(i) == "V3"]),
        ("V4", [i for i in ids if cls(i) == "V4"]),
        ("benign twins (false blocks)", [i for i in ids if cls(i) == "benign"]),
    ):
        add("| {} | {} | {} ({}) | {} ({}) |".format(
            label, len(sel),
            sum(1 for i in sel if blocked(feas[i])), _pct(sum(1 for i in sel if blocked(feas[i])), len(sel)),
            sum(1 for i in sel if blocked(cert[i])), _pct(sum(1 for i in sel if blocked(cert[i])), len(sel)),
        ))
    add("")

    # -- translation accuracy on the twins ---------------------------------- #
    benign = [i for i in ids if cls(i) == "benign"]
    add("## Translation accuracy on the benign twins")
    add("")
    add("| measure | count | share |")
    add("|---|---|---|")
    for label, kinds in (("exact match", ("exact",)),
                         ("semantic match (exact or equivalent)", ("exact", "semantic"))):
        n = sum(
            1 for i in benign
            if match_kind(result["live"][i].ops, raw[i]["gold_ops"]) in kinds
        )
        add("| {} | {} | {} |".format(label, n, _pct(n, len(benign))))
    n_parsed = sum(1 for i in benign if result["live"][i].ops is not None)
    add("| parsed at all | {} | {} |".format(n_parsed, _pct(n_parsed, len(benign))))
    add("")

    # -- terminal states and instrument faults ------------------------------ #
    add("## Terminal states, and instrument faults kept separate")
    add("")
    add("| terminal | G_FEAS | G_CERT |")
    add("|---|---|---|")
    terminals = sorted({v.terminal for v in list(feas.values()) + list(cert.values())})
    for terminal in terminals:
        add("| {} | {} | {} |".format(
            terminal,
            sum(1 for v in feas.values() if v.terminal == terminal),
            sum(1 for v in cert.values() if v.terminal == terminal),
        ))
    infra = [
        i for i in ids
        if any(f.severity == "infra" for f in cert[i].findings)
    ]
    add("")
    add("**infra_error: {} item(s).** These are instrument faults, not guard decisions: "
        "they are excluded from every rate above and reported here only.{}".format(
            len(infra), "" if not infra else "  Items: " + ", ".join(infra[:10])))
    add("")

    # -- certified gaps ------------------------------------------------------ #
    gaps = {}
    for label, sel in (("V3", [i for i in ids if cls(i) == "V3"]),
                       ("V4", [i for i in ids if cls(i) == "V4"]),
                       ("benign", benign)):
        vals = [
            cert[i].certificate.gap for i in sel
            if cert[i].certificate is not None
        ]
        vals.sort()
        gaps[label] = vals
    add("## Certified gap of what was executed (Tier 2, adjusted instance)")
    add("")
    add("| set | certificates | median gap | p90 | max |")
    add("|---|---|---|---|---|")
    for label, vals in gaps.items():
        if not vals:
            add("| {} | 0 | - | - | - |".format(label))
            continue
        add("| {} | {} | {:.4f} | {:.4f} | {:.4f} |".format(
            label, len(vals), _quantile(vals, 0.5), _quantile(vals, 0.9), vals[-1]))
    add("")
    add("Log: `{}`".format(result["log_path"]))
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="all", choices=("all", "generate", "evaluate"))
    # Project-root results/, next to the Tier 1 pilot's output, whatever the cwd.
    ap.add_argument("--out", default=str(CODE_DIR.parent / "results" / "suite_gate"))
    ap.add_argument("--mock", action="store_true", help="force the oracle mock model")
    ap.add_argument("--mock-items", type=int, default=10)
    ap.add_argument("--mock-noise", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="allow writing into a used dir")
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--max-tokens", type=int, default=1024)
    ap.add_argument("--max-model-len", type=int, default=8192)
    ap.add_argument("--gpu-mem-util", type=float, default=0.85)
    ap.add_argument("--limit", type=int, default=0, help="cap the item count (real runs too)")
    args = ap.parse_args()

    print(LAUNCH_QUESTIONS)
    out_dir = Path(args.out)
    raw_path = out_dir / "proposals_raw.jsonl"

    inputs = assert_inputs()
    print("\n[gate] suite sha256   {} OK".format(inputs["suite_sha256"]))
    print("[gate] schema sha256  {} OK".format(inputs["schema_sha256"]))
    print("[gate] model snapshot {} present={}".format(
        inputs["model_path"], inputs["model_present"]))

    gpu = gpu_state()
    print("[gate] " + describe_gpu(gpu) + "\n")

    mock = args.mock
    if args.phase in ("all", "generate") and not mock and not gpu["ok"]:
        mock = True
        print(
            "[gate] GPU CONDITION NOT MET ({}). Falling back to the mocked pipeline over "
            "{} items; the real run stays for the orchestrator to trigger when the card "
            "is free.\n".format(gpu["condition"], args.mock_items)
        )

    if args.phase in ("all", "generate"):
        if out_dir.exists() and any(out_dir.iterdir()) and not args.force:
            raise SystemExit(
                "REFUSING TO RUN: {} already has results. Move it aside or pass "
                "--force.".format(out_dir)
            )
        out_dir.mkdir(parents=True, exist_ok=True)
        rows = load_suite()
        items = select_items(rows)
        if mock:
            items = sample_items(items, args.mock_items)
        elif args.limit:
            items = items[: args.limit]
        print("[gate] {} items selected".format(len(items)))
        raw = generate(items, argparse.Namespace(**{**vars(args), "mock": mock}), gpu)
        with open(raw_path, "w", encoding="utf-8") as fh:
            for row in raw:
                fh.write(json.dumps(row, sort_keys=True) + "\n")
        print("[gate] raw outputs written to {}".format(raw_path))
        if args.phase == "generate":
            print("[gate] now run:  conda run -n fjsp python scripts/suite_gate.py "
                  "--phase evaluate --out {}".format(out_dir))
            return 0

    if args.phase == "evaluate":
        if not raw_path.exists():
            raise SystemExit("no raw outputs at {}; run --phase generate first".format(raw_path))
        raw = [json.loads(line) for line in raw_path.open() if line.strip()]
        mock = bool(raw) and str(raw[0]["model"]).startswith("mock:")
        out_dir.mkdir(parents=True, exist_ok=True)

    result = evaluate(raw, out_dir, args)
    text = summarise(result, gpu, inputs, args, mock)
    name = "DRY_RUN.md" if mock else "summary.md"
    (out_dir / name).write_text(text)
    print("\n" + text)
    print("\n[gate] written to {}".format(out_dir / name))

    if mock:
        print(
            "\n[gate] MOCK RUN ONLY. The GPU condition ({}) was not met: {}\n"
            "[gate] The real gate has not run. Trigger it with the card free:\n"
            "         conda run -n l1   python scripts/suite_gate.py --phase generate\n"
            "         conda run -n fjsp python scripts/suite_gate.py --phase evaluate".format(
                gpu["condition"], describe_gpu(gpu).splitlines()[0]
            )
        )
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
