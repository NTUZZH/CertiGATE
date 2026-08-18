#!/usr/bin/env python
"""E1 grid, local arm: Qwen3-14B over the full suite, both enforcement modes.

One generation log serves every guard arm: UNGUARDED / G_FEAS / G_CERT are
replay configurations over the same raw outputs, so this runner only GENERATES.
Evaluation is a separate CPU phase (no GPU held), written and reviewed with the
E1 analysis.

Design frozen at launch (orchestrator decision, decisions.md 2026-08-11):

* items    : all 2,000 suite items (v0.2, sha asserted);
* modes    : M_constrained (xgrammar, frozen schema) and M_free (no grammar,
             same prompt) - the enforcement-mode axis;
* repeats  : 3 identical passes per mode (r0/r1/r2), temperature 0, seed 0.
             At temperature 0 any disagreement between repeats measures the
             engine's batch-numeric nondeterminism, not sampling; the run
             prints the pairwise agreement so the analysis can collapse
             identical repeats with evidence rather than assumption;
* budget   : max_tokens 1024, max_model_len 12288 (full-suite prompt audit:
             median 1,536, max 9,914 tokens - env_checks/prompt_length_audit.py);
* prompt   : l1-prompt-1.0.0, top_k 10, chat template with thinking off.

Run (GPU held for the whole run)::

    conda run -n l1 python scripts/grid_e1_local.py            # real run
    conda run -n l1 python scripts/grid_e1_local.py --limit 4  # smoke
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import suite_gate as sg  # noqa: E402  (hash asserts, GPU discipline, prompts)

MODES = ("M_constrained", "M_free")
REPEATS = 3

LAUNCH_QUESTIONS = """\
================================================================================
FOUR LAUNCH QUESTIONS (global CLAUDE.md experiment rules), answered before the run
================================================================================
1. PURPOSE.  The E1 local arm's generation log: Qwen3-14B over all 2,000 suite
   items in both enforcement modes x 3 repeats.  Every E1 number for this arm
   (violation catch rates, false blocks, constraint tax, certified gaps) is
   computed from this log by offline replay; the log also feeds E2 (tau sweep).
2. EXPECTED RESULT.  M_constrained parses 100% (grammar-guaranteed);  M_free
   shows a nonzero malformed share - that difference is the constraint-tax
   numerator.  Repeats agree exactly or nearly; the agreement count is printed
   and recorded either way.  A crash or an empty log is the only failing state.
3. CONTAMINATION.  The output directory must be empty (--force to override);
   the log is written once, append-only, one row per (item, mode, repeat).
   The card is checked free before loading (>=34 GiB, <20% foreign util); the
   model is the pinned snapshot, temperature 0, seed 0, thinking off.
4. DATA ACCURACY.  Suite sha256 and schema sha256 asserted fatal at start (the
   gate's own assertions); instances resolved per item from its stratum;
   prompts rendered by the frozen l1-prompt-1.0.0 module at top_k 10.
================================================================================"""


def generate_mode(llm, sampling_cls, so_params_cls, schema, prompts_text, mode, args):
    kwargs = dict(temperature=0.0, max_tokens=args.max_tokens, seed=0)
    if mode == "M_constrained":
        kwargs["structured_outputs"] = so_params_cls(json=schema)
    sampling = sampling_cls(**kwargs)
    started = time.perf_counter()
    outputs = llm.generate(prompts_text, sampling, use_tqdm=True)
    wall = time.perf_counter() - started
    texts, usages, finish = [], [], []
    for out in outputs:
        comp = out.outputs[0]
        texts.append(comp.text)
        finish.append(comp.finish_reason)
        usages.append({
            "prompt_tokens": len(out.prompt_token_ids or []),
            "completion_tokens": len(comp.token_ids),
        })
    return texts, usages, finish, wall


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(sg.CODE_DIR.parent / "results" / "grid_e1_local"))
    ap.add_argument("--model-path", default=sg.MODEL_PATH,
                    help="pinned local snapshot dir (default: the Qwen3-14B pin; "
                         "the 27B arm passes its own pinned snapshot)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="cap items (smoke runs)")
    ap.add_argument("--repeats", type=int, default=REPEATS)
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--max-tokens", type=int, default=1024)
    ap.add_argument("--max-model-len", type=int, default=12288)
    ap.add_argument("--gpu-mem-util", type=float, default=0.85)
    ap.add_argument("--max-num-seqs", type=int, default=0,
                    help="cap concurrent sequences (0 = vLLM default). The hybrid-"
                         "attention 27B allocates one Mamba cache block per decode "
                         "sequence and its FP8 weights leave room for <256 at 0.85 "
                         "memory utilization, so its runs pass 128 here.")
    args = ap.parse_args()

    print(LAUNCH_QUESTIONS)
    inputs = sg.assert_inputs()
    print("[e1] suite sha256  {} OK".format(inputs["suite_sha256"]))
    print("[e1] schema sha256 {} OK".format(inputs["schema_sha256"]))

    gpu = sg.gpu_state()
    print("[e1] " + sg.describe_gpu(gpu))
    if not gpu["ok"]:
        raise SystemExit("REFUSING TO RUN: GPU condition not met ({})".format(
            gpu["condition"]))

    out_dir = Path(args.out)
    if out_dir.exists() and any(out_dir.iterdir()) and not args.force:
        raise SystemExit("REFUSING TO RUN: {} already has results".format(out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)

    items = sg.load_suite()
    if args.limit:
        items = items[: args.limit]
    print("[e1] {} items x {} modes x {} repeats = {} generations".format(
        len(items), len(MODES), args.repeats, len(items) * len(MODES) * args.repeats))

    instances = sg.Instances()
    prompts_mod = sg.load_prompts_module()
    messages = [prompts_mod.build_messages(instances.get(it), it, args.top_k)
                for it in items]

    import os as _os
    _os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")
    _os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    import vllm
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import StructuredOutputsParams

    with open(sg.SCHEMA_PATH, "r", encoding="utf-8") as fh:
        schema = json.load(fh)

    if not Path(args.model_path).is_dir():
        raise SystemExit("REFUSING TO RUN: model snapshot missing: {}".format(args.model_path))
    print("[e1] loading {} (vllm {})".format(args.model_path, vllm.__version__), flush=True)
    llm_kwargs = dict(
        model=args.model_path,
        max_model_len=args.max_model_len,
        gpu_memory_utilization=args.gpu_mem_util,
        seed=0,
        trust_remote_code=False,
        structured_outputs_config={"backend": "xgrammar"},
    )
    if args.max_num_seqs:
        llm_kwargs["max_num_seqs"] = args.max_num_seqs
    llm = LLM(**llm_kwargs)
    resolved = getattr(
        llm.llm_engine.vllm_config.structured_outputs_config, "backend", "<unknown>")
    if resolved != "xgrammar":
        raise SystemExit("REFUSING TO RUN: backend resolved {!r}".format(resolved))
    print("[e1] structured-outputs backend: xgrammar (read back)", flush=True)

    tok = llm.get_tokenizer()
    prompts_text = []
    for msg in messages:
        try:
            rendered = tok.apply_chat_template(
                msg, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        except TypeError:  # pragma: no cover
            rendered = tok.apply_chat_template(msg, tokenize=False,
                                               add_generation_prompt=True)
        if isinstance(rendered, list):
            rendered = tok.decode(rendered)
        prompts_text.append(rendered)

    raw_path = out_dir / "proposals_raw.jsonl"
    walls = {}
    texts_by = {}
    with open(raw_path, "w", encoding="utf-8") as fh:
        for mode in MODES:
            for repeat in range(args.repeats):
                print("[e1] generating {} r{} ...".format(mode, repeat), flush=True)
                texts, usages, finish, wall = generate_mode(
                    llm, SamplingParams, StructuredOutputsParams, schema,
                    prompts_text, mode, args)
                walls["{}-r{}".format(mode, repeat)] = wall
                texts_by[(mode, repeat)] = texts
                print("[e1] {} r{}: {} generations in {:.1f} s".format(
                    mode, repeat, len(texts), wall), flush=True)
                for item, msg, text, usage, fin in zip(
                        items, messages, texts, usages, finish):
                    fh.write(json.dumps({
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
                        "prompt_hash": prompts_mod.prompt_fingerprint(msg),
                        "prompt_version": prompts_mod.PROMPT_VERSION,
                        "model": args.model_path,
                        "mode": mode,
                        "repeat": repeat,
                        "backend": "xgrammar" if mode == "M_constrained" else "none",
                        "raw_output": text,
                        "finish_reason": fin,
                        "usage": usage,
                    }, sort_keys=True) + "\n")
                fh.flush()

    agreement = {}
    for mode in MODES:
        pairs = []
        for a in range(args.repeats):
            for b in range(a + 1, args.repeats):
                same = sum(1 for x, y in zip(texts_by[(mode, a)], texts_by[(mode, b)])
                           if x == y)
                pairs.append({"pair": "r{}r{}".format(a, b), "identical": same,
                              "of": len(items)})
        agreement[mode] = pairs
        print("[e1] repeat agreement {}: {}".format(mode, pairs), flush=True)

    meta = {
        "date": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "items": len(items), "modes": list(MODES), "repeats": args.repeats,
        "suite_sha256": inputs["suite_sha256"], "schema_sha256": inputs["schema_sha256"],
        "model_snapshot": args.model_path,
        "prompt_version": prompts_mod.PROMPT_VERSION, "top_k": args.top_k,
        "max_tokens": args.max_tokens, "max_model_len": args.max_model_len,
        "temperature": 0.0, "seed": 0, "backend": "xgrammar",
        "gpu_at_launch": gpu["raw"], "walls_s": walls,
        "repeat_agreement": agreement,
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=1))
    print("[e1] raw log: {}".format(raw_path))
    print("[e1] meta   : {}".format(out_dir / "run_meta.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
