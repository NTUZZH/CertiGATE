#!/usr/bin/env python
"""Gate stress test with prompts limited to the known board: the generation runner.

WHY
---
In the published stress test (Table 6, tab:e1) every proposer was prompted with
the board of the whole dispatch window (``l1-prompt-1.0.0``,
``build_messages(instance, item)`` on the full instance), and its logged
proposals were replayed through the gate at the decision instant t_d.  In the
deployed condition the proposer sees only the orders the site knows at t_d.  This
runner renders, for each of the 1,723 issuable instructions of the published
suite, the SAME frozen prompt module and template on the known board K at t_d
and generates with the published settings of each arm.  Nothing else changes.

HOW THE KNOWN BOARD IS SHOWN TO THE PROPOSER (design decisions)
---------------------------------------------------------------
* The board is the gate's own board at t_d: ``n8_causal.known_instance`` of the
  site state at t_d (planned-known reading, ``pm_known=True``), built from the
  published baseline trajectory exactly as ``n11_stage2.e2e_instance`` builds the
  instance K on which it replays a logged proposal.  K holds the queued orders,
  the orders in progress at t_d and the planned-maintenance orders already on the
  calendar, every technician, and the instance meta.  Orders completed by t_d and
  orders the site has not received are absent.
* ``build_messages(K, item_k, top_k=10)`` of the frozen module is called
  unchanged; ``item_k`` is the suite item with two episode fields set to the
  decision instant: ``t_bh = t_d`` (the header prints "decision time t_d") and
  ``frozen_seed = kf``, the gate's frozen set on K (``n11_decision_time.kf_fix``:
  the orders in progress at t_d plus every seed order K still holds).  The prompt
  module's one line for committed work, "Work already under way, pinned to its
  current slot: ...", therefore names exactly the work the gate pins on K and
  refuses to edit (Stage 3 addition A).  Every aggregate of the trade table
  (orders, hours, first in, first due, class-1 count) is computed over K, so no
  count or time of a later order reaches the prompt.
* The board of ``n11_decision_time.board_instance`` is not used: it drops the
  running orders and raises every release to t_d, which is the relaxed board the
  oracle bounds, not the board the gate applies a proposal to.  Raised releases
  would also change the due-date arithmetic the model is told about
  (set_priority and reassign_window act on the recorded release).
* Item text, operation vocabulary, system prompt, top_k and the instruction are
  the published ones.  Prompt version string: ``l1-prompt-1.0.0+known-board``.

PHASES
------
--dry-run     CPU only, no GPU, no network (python3 or env fjsp: K needs the
              gate's dispatch).  Renders every prompt, asserts the leak check,
              audits token lengths, prints the hosted token volumes, writes
              results/grid_e1_known_dryrun/ and diffs the resolved configuration
              of every arm against the published run_meta.
--arm A       GPU, env l1: generation for one local arm (qwen3-14b,
              qwen3.6-27b-fp8, glm-4-9b), constrained mode, the published repeats.
              Reads the dry run's prompt file and re-verifies it before loading.
--hosted A    network, env fjsp: generation for one hosted arm through
              grid_e1_hosted.py's client; refuses to run without
              --i-have-approval-to-spend.
--token-audit internal: the tokenizer count in env l1, started by --dry-run
              with CUDA_VISIBLE_DEVICES='' when a pinned snapshot is on disk.

Run::

    OMP_NUM_THREADS=1 taskset -c 12-13 python3 code/scripts/grid_e1_known.py --dry-run
    conda run -n l1 python code/scripts/grid_e1_known.py --arm qwen3-14b
"""

from __future__ import annotations

import os

# The instance snapshot the published results were computed on.  Set before
# suite_gate is imported, because suite_gate reads it at import.
SNAPSHOT_ROOT = ((os.environ.get("L1_Y1_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "PaperY-FMScheduling")) + "/data/processed/instances_v10")
_env_root = os.environ.get("L1_INSTANCE_ROOT")
if _env_root and os.path.realpath(_env_root) != os.path.realpath(SNAPSHOT_ROOT):
    raise SystemExit("REFUSING TO RUN: L1_INSTANCE_ROOT={} is not the snapshot {}"
                     .format(_env_root, SNAPSHOT_ROOT))
os.environ["L1_INSTANCE_ROOT"] = SNAPSHOT_ROOT

import argparse  # noqa: E402
import copy  # noqa: E402
import dataclasses  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import statistics  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from collections import Counter, OrderedDict  # noqa: E402
from pathlib import Path  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent
for _p in (str(SCRIPTS_DIR.parent), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import suite_gate as sg  # noqa: E402  (stdlib only: hashes, GPU state, prompts, instances)

VERSION = "l1-grid-e1-known-1"
BASE_VERSION = "l1-prompt-1.0.0"
KNOWN_VERSION = BASE_VERSION + "+known-board"
PROMPT_VARIANT = "known-board"
TOP_K = 10
MODE = "M_constrained"
ROOT = sg.CODE_DIR.parent
RESULTS = ROOT / "results"
DRY = RESULTS / "grid_e1_known_dryrun"
PROMPTS_FILE = DRY / "prompts.jsonl"
UNKNOWN_FILE = DRY / "unknown_ids.jsonl"
CONFIG_FILE = DRY / "resolved_config.json"
REPORT_FILE = DRY / "dryrun_report.json"
TOKEN_FILE = DRY / "token_audit.json"
E2E_ITEMS = RESULTS / "n11_e2e" / "items.jsonl"
E2E_SITES = RESULTS / "n11_e2e" / "sites.jsonl"
L1_PYTHON = os.environ.get("L1_VLLM_PYTHON", "python")
N_ISSUABLE = 1723
INSTRUCTION_MARK = "\n\nINSTRUCTION\n"
INSTRUCTION_TAIL = "\n\nReply with the json object only."
TOKEN_RE = re.compile(r"[A-Za-z0-9]+")

#: The three local arms, with the settings of their published runs
#: (results/<published_dir>/run_meta.json).  ``max_num_seqs`` is not recorded in
#: any run_meta: 0 (vLLM's default) for the 14B and GLM arms (the GLM launch log,
#: results/grid_e1_local_glm9b_20260813.log, lists the non-default engine
#: arguments and max_num_seqs is not among them), 128 for the 27B arm (the
#: runner's --max-num-seqs help text, written 2026-08-11 18:42 before the 27B
#: launch: "its runs pass 128 here"; the decision record line 1694).
LOCAL_ARMS = OrderedDict([
    ("qwen3-14b", {
        "short": "qwen14b", "display": "Qwen3-14B", "published_dir": "grid_e1_local",
        "repo": "Qwen/Qwen3-14B", "revision": "40c069824f4251a91eefaf281ebe4c544efd3e18",
        "model_snapshot": os.environ.get("L1_QWEN14B_PATH") or os.path.join(os.environ.get("HF_HUB_CACHE") or os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub"), "models--Qwen--Qwen3-14B", "snapshots", "40c069824f4251a91eefaf281ebe4c544efd3e18"),
        "repeats": 3, "max_tokens": 1024, "max_model_len": 12288,
        "gpu_memory_utilization": 0.85, "max_num_seqs": 0,
        "max_num_seqs_source": "vLLM default (runner default 0, not recorded in run_meta)",
        "checksums": "env_checks/qwen14b_sha256.txt"}),
    ("qwen3.6-27b-fp8", {
        "short": "qwen27b", "display": "Qwen3.6-27B-FP8", "published_dir": "grid_e1_local_27b",
        "repo": "Qwen/Qwen3.6-27B-FP8", "revision": "e89b16ebf1988b3d6befa7de50abc2d76f26eb09",
        "model_snapshot": os.environ.get("L1_QWEN27B_PATH") or os.path.join(os.environ.get("HF_HUB_CACHE") or os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub"), "models--Qwen--Qwen3.6-27B-FP8", "snapshots", "e89b16ebf1988b3d6befa7de50abc2d76f26eb09", ""),
        "repeats": 3, "max_tokens": 1024, "max_model_len": 16384,
        "gpu_memory_utilization": 0.85, "max_num_seqs": 128,
        "max_num_seqs_source": "inferred: grid_e1_local.py --max-num-seqs help text and "
                               "the decision record 1694 (not recorded in run_meta)",
        "checksums": "env_checks/qwen27b_sha256.txt"}),
    ("glm-4-9b", {
        "short": "glm9b", "display": "GLM-4-9B-0414", "published_dir": "grid_e1_local_glm9b",
        "repo": "zai-org/GLM-4-9B-0414", "revision": "645b8482494e31b6b752272bf7f7f273ef0f3caf",
        "model_snapshot": os.environ.get("L1_GLM9B_PATH") or os.path.join(os.environ.get("HF_HUB_CACHE") or os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub"), "models--zai-org--GLM-4-9B-0414", "snapshots", "645b8482494e31b6b752272bf7f7f273ef0f3caf"),
        "repeats": 1, "max_tokens": 1024, "max_model_len": 12288,
        "gpu_memory_utilization": 0.85, "max_num_seqs": 0,
        "max_num_seqs_source": "vLLM default (absent from the non-default args of "
                               "results/grid_e1_local_glm9b_20260813.log)",
        "checksums": None}),
])

#: The hosted arms of grid_e1_hosted.py and their published raw logs.  The
#: published repeats are the defaults (Sol is a one-repeat spot-check); DeepSeek
#: is not a row of Table 6 (JSON-object mode enforces no schema).
HOSTED = OrderedDict([
    ("openai", {"display": "GPT-5.4-mini", "dir": "grid_e1_hosted_openai", "repeats": 2,
                "table6": True}),
    ("sonnet", {"display": "Claude Sonnet 5", "dir": "grid_e1_hosted_sonnet", "repeats": 2,
                "table6": True}),
    ("opus", {"display": "Claude Opus 5 (two thinking settings)", "dir": "grid_e1_hosted_opus",
              "repeats": 2, "table6": True}),
    ("sol", {"display": "GPT-5.6 Sol", "dir": "grid_e1_hosted_sol", "repeats": 1,
             "table6": True}),
    ("deepseek", {"display": "DeepSeek V4-Pro (not in Table 6)", "dir": "grid_e1_hosted_deepseek",
                  "repeats": 2, "table6": False}),
])

#: Configuration keys compared with the published run_meta, and the only
#: categories a difference may fall into (the design).
LOCAL_KEYS = ("items", "modes", "repeats", "suite_sha256", "schema_sha256", "model_snapshot",
              "prompt_version", "top_k", "max_tokens", "max_model_len", "temperature", "seed",
              "backend")
HOSTED_KEYS = ("arm", "model", "backend", "wire", "modes", "thinking", "thinking_bodies",
               "repeats", "items", "max_tokens", "workers", "timeout_s", "max_retries",
               "suite_sha256", "schema_sha256", "prompt_version", "top_k", "cache_boundary",
               "cache_boundary_fallback")
ALLOWED_DIFF = {"items": "item set", "modes": "modes", "prompt_version": "prompt version",
                # design M3 (2026-11-11): at most 4 requests in flight per arm, because
                # another agent calls the same Claude endpoints; concurrency changes no
                # request body, only the wall time and the cache-hit pattern
                "workers": "request cap (design M3: at most 4 in flight per arm)"}

#: design M3 (2026-11-11), the hosted known-board rerun of the three Claude cells.
#: The prompt file the dry run wrote and the design pins; asserted inside the run.
EXPECTED_PROMPTS_SHA256 = "513f2cf8f59c590eb2016b54b1d322b3ddddb111070d0a31271be58549295eda"
HOSTED_MAX_WORKERS = 4
#: Exponential backoff on rate limits (429) and overload (529), inside the transport:
#: the first try plus six waits of 2, 4, 8, 16, 32 and 64 s (the provider's
#: retry-after wins when longer, each wait capped at 120 s, plus up to 25% jitter).
#: After the last try the status goes back to the published client, whose own
#: linear retries (max_retries 4) then apply unchanged.
RATE_LIMIT_STATUS = (429, 529)
BACKOFF_TRIES = 7
BACKOFF_BASE_S = 2.0
BACKOFF_CAP_S = 120.0
#: Request fields the published Anthropic request never carries (and so must not carry).
NOT_SENT = ("temperature", "top_p", "top_k", "stop_sequences", "stream", "metadata", "tools",
            "tool_choice", "service_tier", "inference_geo", "speed", "fallbacks")

#: GPU discipline, stricter than suite_gate's launch condition: the card must
#: carry no foreign process at all.
GPU_MAX_USED_MIB = 1024.0
GPU_MAX_UTIL = 1.0
GPU_SAMPLES = 3

LAUNCH_QUESTIONS = """\
================================================================================
FOUR LAUNCH QUESTIONS (the project's experiment rules), answered before the run
================================================================================
1. PURPOSE.  The deployed condition of the gate stress test: each proposer sees
   only the orders the site knows at the decision instant t_d.  One generation
   log per arm, constrained mode, over the 1,723 issuable instructions: Qwen3-14B
   (3 repeats), Qwen3.6-27B-FP8 (3), GLM-4-9B-0414 (1), and the hosted arms only
   with spend approval.  The numbers land, through
   code/scripts/n19_known_prompt_eval.py, beside Table 6 (tab:e1: referral of
   cost-bearing instructions, fidelity, blocks, benign false blocks), the
   referral range and the dangling-identifier sentence of Section 5.1, the
   field-edit block of N16 (D2) and the approver band of N13 (A).
2. EXPECTED RESULT.  The share of proposals that name an order unknown at t_d
   falls to zero (the prompt holds no such order).  Referral and fidelity move
   by a few points at most, because the cost-bearing instructions name orders
   that are all on K.  If referral or fidelity fall materially, Section 5.1
   reports the known-board reading as the deployed one and the whole-window
   reading as the stress reading; if they hold, the whole-window reading is
   shown to carry over.  Either outcome changes the text, so the run is needed.
3. CONTAMINATION.  Output results/grid_e1_known_<arm>/ must be empty; no
   existing analysis glob matches the name (the dry run lists the globs it
   checked); every row carries prompt_version l1-prompt-1.0.0+known-board.  The
   card must carry no foreign process, memory above 1 GiB or utilisation; one
   GPU job at a time.  Generation only: evaluation is a separate CPU phase.
4. DATA ACCURACY.  Suite and schema SHA-256 fatal; instances from the snapshot
   instances_v10, manifest-verified; issuability and t_d asserted equal to
   results/n11_e2e/items.jsonl, K sizes to results/n11_e2e/sites.jsonl; the
   whole-window render reproduces every logged prompt hash; the prompt file's
   SHA-256 is recorded by the dry run and re-verified at launch with every
   prompt hash and the leak check recomputed; the resolved configuration is
   diffed against the published run_meta and may differ only in prompt
   version, item set and modes.
================================================================================"""


# --------------------------------------------------------------------------- #
# Small utilities                                                              #
# --------------------------------------------------------------------------- #
def sha256_file(path) -> str:
    return sg.sha256_file(Path(path))


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_jsonl(path) -> list:
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                out.append(json.loads(line))
    return out


def write_jsonl(path, rows) -> None:
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    os.replace(tmp, path)


def write_json(path, obj) -> None:
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, sort_keys=True, default=str))
    os.replace(tmp, path)


def frozen_key(seed) -> str:
    return ",".join(str(x) for x in (seed or ()))


def item_set_sha(ids) -> str:
    return sha_text("\n".join(sorted(ids)))


def quantile(vals, q):
    vals = sorted(vals)
    if not vals:
        return None
    return vals[min(len(vals) - 1, int(q * len(vals)))]


class Fatal:
    """Collects run-fatal assertions and counts the passed ones."""

    def __init__(self):
        self.n = Counter()
        self.failures = []

    def true(self, group, what, ok, detail=""):
        self.n[group] += 1
        if not ok:
            self.failures.append("{} {}: {}".format(group, what, detail))

    def stop_if_failed(self, where):
        if self.failures:
            print("ASSERTION FAILURES at {} ({} of {}):".format(
                where, len(self.failures), sum(self.n.values())), file=sys.stderr)
            for f in self.failures[:40]:
                print("  - " + f, file=sys.stderr)
            raise SystemExit(2)

    def summary(self) -> dict:
        return {"n_checks": sum(self.n.values()), "by_group": dict(sorted(self.n.items())),
                "failures": list(self.failures)}


# --------------------------------------------------------------------------- #
# The leak check (stdlib only, so the generation phase can rerun it)           #
# --------------------------------------------------------------------------- #
def split_prompt(user: str, instruction: str) -> tuple:
    """(board part, instruction part) of a rendered user prompt; fatal if the tail moved."""
    if INSTRUCTION_MARK not in user:
        raise SystemExit("REFUSING TO RUN: rendered prompt has no INSTRUCTION block")
    board, tail = user.rsplit(INSTRUCTION_MARK, 1)
    if tail != instruction + INSTRUCTION_TAIL:
        raise SystemExit("REFUSING TO RUN: the instruction is not verbatim at the prompt's end")
    return board, tail


def id_tokens(text: str) -> set:
    """Maximal alphanumeric runs: order ids are W<digits> or 8-digit numbers, and a
    number printed with two decimals splits at the point, so no count, hour or
    time can form an 8-digit token."""
    return set(TOKEN_RE.findall(text))


def leak_of(messages, instruction, unknown) -> dict:
    system, user = messages[0]["content"], messages[1]["content"]
    board, _tail = split_prompt(user, instruction)
    board_hits = sorted(id_tokens(system + "\n" + board) & unknown)
    instr_hits = sorted(id_tokens(instruction) & unknown)
    full_hits = sorted(id_tokens(system + "\n" + user) & unknown)
    return {"board": board_hits, "instruction": instr_hits, "full": full_hits}


# --------------------------------------------------------------------------- #
# GPU discipline                                                               #
# --------------------------------------------------------------------------- #
def gpu_verdict(lines, apps) -> dict:
    """Decide from nvidia-smi samples whether the card is free of every foreign job.

    ``lines``: one or more "name, memory.used, memory.total, utilization.gpu"
    samples; ``apps``: the compute-apps query output.  Refuses when any compute
    process is listed, used memory exceeds 1 GiB in any sample, utilisation is
    at least 1% in any sample, or suite_gate's own condition (>= 34 GiB free,
    < 20% utilisation) fails.
    """
    reasons = []
    used, util, free = [], [], []
    for line in lines:
        try:
            _name, u, total, ut = [p.strip() for p in line.split(",")]
            used.append(float(u))
            util.append(float(ut))
            free.append((float(total) - float(u)) / 1024.0)
        except Exception:  # noqa: BLE001
            reasons.append("unreadable nvidia-smi line {!r}".format(line))
    if apps and apps.strip() and not apps.startswith("<unavailable"):
        reasons.append("foreign compute process(es) on the card: {}".format(
            apps.strip().replace("\n", " | ")))
    if used and max(used) > GPU_MAX_USED_MIB:
        reasons.append("used memory {:.0f} MiB > {:.0f} MiB".format(max(used), GPU_MAX_USED_MIB))
    if util and max(util) >= GPU_MAX_UTIL:
        reasons.append("utilisation {:.0f}% in a sample".format(max(util)))
    if free and min(free) < sg.MIN_FREE_GIB:
        reasons.append("free {:.1f} GiB < {:.0f} GiB".format(min(free), sg.MIN_FREE_GIB))
    if not lines:
        reasons.append("no nvidia-smi sample")
    return {"ok": not reasons, "reasons": reasons, "samples": list(lines), "apps": apps}


def gpu_check_live() -> dict:
    """Sample the card GPU_SAMPLES times, one second apart (generation phase only)."""
    lines = []
    apps = ""
    for i in range(GPU_SAMPLES):
        st = sg.gpu_state()
        lines.append(st["raw"])
        apps = st["apps"] or apps
        if i + 1 < GPU_SAMPLES:
            time.sleep(1.0)
    return gpu_verdict(lines, apps)


def gpu_selftest(check) -> list:
    """The refusal logic on canned samples; the dry run never calls nvidia-smi."""
    free_line = "NVIDIA RTX PRO 5000 Blackwell, 443, 48935, 0"   # the published launch state
    cases = [
        ("published launch state, no app", [free_line] * 3, "", True),
        ("foreign app listed", [free_line] * 3, "75268, /x/python, 420", False),
        ("foreign memory 9 GiB", ["NVIDIA RTX PRO 5000 Blackwell, 9300, 48935, 0"] * 3, "", False),
        ("utilisation spike in one sample", [free_line, free_line.replace(", 0", ", 37"),
                                             free_line], "", False),
        ("L2 vLLM server holding 21 GiB", ["NVIDIA RTX PRO 5000 Blackwell, 21800, 48935, 64"],
         "116267, VLLM::EngineCore, 21500", False),
    ]
    out = []
    for name, lines, apps, want in cases:
        got = gpu_verdict(lines, apps)
        check.true("GPU", "refusal logic: " + name, got["ok"] == want, got["reasons"])
        out.append({"case": name, "ok": got["ok"], "reasons": got["reasons"]})
    return out


# --------------------------------------------------------------------------- #
# Rendering the known-board prompts (needs the gate: python3 or env fjsp)       #
# --------------------------------------------------------------------------- #
def render_all(check, top_k=TOP_K) -> dict:
    import n11_decision_time as D   # noqa: F401  (asserts the snapshot root)
    import n8_causal as n8
    from l1adapter import dispatch as dispatch_mod

    prompts_mod = sg.load_prompts_module()
    check.true("A0", "frozen prompt module version", prompts_mod.PROMPT_VERSION == BASE_VERSION,
               prompts_mod.PROMPT_VERSION)
    items = sg.load_suite()
    pub_items = {r["item_id"]: r for r in read_jsonl(E2E_ITEMS)}
    pub_sites = {(s["iid"], s["fk"], float(s["t_d"])): s for s in read_jsonl(E2E_SITES)}
    by_inst = OrderedDict()
    for it in items:
        by_inst.setdefault(it["instance"]["instance_id"], []).append(it)
    rows, unknown_rows = {}, OrderedDict()
    stats = Counter()
    instr_unknown = []
    whole_leaks = []
    t0 = time.perf_counter()
    for iid, its in by_inst.items():
        path = D.instance_path(its[0])
        inst = D.load_instance(path)
        all_ids = {w["id"] for w in inst["work_orders"]}
        by_id = {w["id"]: w for w in inst["work_orders"]}
        baseline = dispatch_mod.dispatch_baseline(inst, "atc", 0)
        trajs, sites = {}, {}
        for it in its:
            check.true("A1", "episode rule is the site's rule", it["episode"]["rule"] == "atc",
                       it["item_id"])
            seed = list(it["episode"]["frozen_seed"] or [])
            fk = frozen_key(seed)
            if fk not in trajs:
                trajs[fk] = n8.trajectory(inst, seed, baseline)
            traj = trajs[fk]
            starts = {a["wo"]: float(a["start_bh"]) for a in traj["assignments"]}
            iss = D.issuability({"referenced": it["referenced"]}, by_id, starts)
            pub = pub_items[it["item_id"]]
            check.true("A1", "issuability equals results/n11_e2e/items.jsonl",
                       iss["issuable"] == pub["issuable"], it["item_id"])
            if not iss["issuable"]:
                stats["not_issuable"] += 1
                continue
            t_d = D.decision_instant_of(iss, "primary")
            check.true("A1", "t_d equals results/n11_e2e/items.jsonl",
                       t_d == float(pub["t_d"]["primary"]), (it["item_id"], t_d))
            key = (fk, t_d)
            if key not in sites:
                state = n8.site_state(inst, traj, t_d, pm_known=True)
                known = n8.known_instance(inst, state)
                kf = D.kf_fix(state, seed)
                sites[key] = (state, known, kf)
                unknown_rows[(iid, fk, t_d)] = {
                    "instance_id": iid, "frozen_seed": fk, "t_d": t_d,
                    "unknown": sorted(state["unknown"]), "n_completed": len(state["completed"])}
            state, known, kf = sites[key]
            kset = {w["id"] for w in known["work_orders"]}
            unknown = set(state["unknown"])
            ps = pub_sites.get((iid, fk, t_d))
            check.true("A2", "K site is a published site", ps is not None, (iid, fk, t_d))
            if ps is not None:
                check.true("A2", "n_known equals results/n11_e2e/sites.jsonl",
                           len(known["work_orders"]) == ps["n_known"], (iid, t_d))
                check.true("A2", "n_running equals results/n11_e2e/sites.jsonl",
                           len(state["in_progress"]) == ps["n_running"], (iid, t_d))
            ref = [o for o in it["referenced"]["order_ids"] if o in all_ids]
            check.true("A2", "every referenced order is on K and not running",
                       all(o in kset and o not in set(state["in_progress"]) for o in ref),
                       it["item_id"])
            item_k = copy.deepcopy(it)
            item_k["episode"]["t_bh"] = t_d
            item_k["episode"]["frozen_seed"] = list(kf)
            msgs = prompts_mod.build_messages(known, item_k, top_k)
            msgs_w = prompts_mod.build_messages(inst, it, top_k)
            # ---- the leak check (fatal on the board; the instruction is verbatim)
            lk = leak_of(msgs, it["instruction"], unknown)
            check.true("LEAK", "no order unknown at t_d in the board part of the prompt",
                       not lk["board"], (it["item_id"], lk["board"][:5]))
            board, _ = split_prompt(msgs[1]["content"], it["instruction"])
            shown = id_tokens(msgs[0]["content"] + "\n" + board) & all_ids
            check.true("LEAK", "every order id the board shows is on K",
                       shown <= kset, (it["item_id"], sorted(shown - kset)[:5]))
            check.true("LEAK", "no order completed by t_d in the board part",
                       not (shown & set(state["completed"])), it["item_id"])
            if lk["instruction"]:
                instr_unknown.append({"item_id": it["item_id"], "ids": lk["instruction"]})
            lw = leak_of(msgs_w, it["instruction"], unknown)
            if lw["board"]:
                whole_leaks.append(len(lw["board"]))
            stats["rendered"] += 1
            rows[it["item_id"]] = OrderedDict(
                item_id=it["item_id"], instance_id=iid, stratum=it["instance"]["stratum"],
                primary_class=it["primary_class"], subclass=it["subclass"],
                frozen_seed=seed, known_frozen=list(kf), t_d=t_d,
                n_known=len(known["work_orders"]), n_running=len(state["in_progress"]),
                n_completed=len(state["completed"]), n_unknown=len(unknown),
                n_window=len(inst["work_orders"]),
                prompt_version=KNOWN_VERSION,
                prompt_hash=prompts_mod.prompt_fingerprint(msgs),
                prompt_hash_whole_window=prompts_mod.prompt_fingerprint(msgs_w),
                prompt_chars=sum(len(m["content"]) for m in msgs),
                prompt_chars_whole_window=sum(len(m["content"]) for m in msgs_w),
                leak_board=lk["board"], leak_instruction=lk["instruction"],
                messages=msgs, prompt_text=msgs[1]["content"])
    ordered = [rows[it["item_id"]] for it in items if it["item_id"] in rows]
    check.true("A1", "1,723 issuable instructions", len(ordered) == N_ISSUABLE, len(ordered))
    return {"rows": ordered, "unknown": list(unknown_rows.values()), "stats": dict(stats),
            "instr_unknown": instr_unknown, "whole_leaks": whole_leaks,
            "wall_s": time.perf_counter() - t0}


def crosscheck_logged_hashes(check, rows) -> dict:
    """The whole-window render of this script equals every published arm's logged hash."""
    want = {r["item_id"]: r["prompt_hash_whole_window"] for r in rows}
    out = OrderedDict()
    logs = [(k, RESULTS / v["published_dir"] / "proposals_raw.jsonl") for k, v in LOCAL_ARMS.items()]
    logs += [(k, RESULTS / v["dir"] / "proposals_raw.dedup.jsonl") for k, v in HOSTED.items()]
    for arm, path in logs:
        n_eq = n_ne = 0
        for r in read_jsonl(path):
            w = want.get(r["item_id"])
            if w is None or r.get("mode") != MODE:
                continue
            if r.get("prompt_hash") == w:
                n_eq += 1
            else:
                n_ne += 1
        check.true("A3", "whole-window render reproduces the logged prompt hash ({})".format(arm),
                   n_ne == 0 and n_eq > 0, (n_eq, n_ne))
        out[arm] = {"rows_compared": n_eq + n_ne, "equal": n_eq}
    return out


# --------------------------------------------------------------------------- #
# Token audit                                                                  #
# --------------------------------------------------------------------------- #
def tokenizer_present(path) -> bool:
    p = Path(path)
    return p.is_dir() and (p / "tokenizer_config.json").is_file() and (
        (p / "tokenizer.json").is_file() or (p / "vocab.json").is_file())


def logged_prompt_tokens(spec) -> dict:
    """item_id -> vLLM's logged prompt token count of the whole-window prompt (r0)."""
    out = {}
    for r in read_jsonl(RESULTS / spec["published_dir"] / "proposals_raw.jsonl"):
        if r.get("mode") == MODE and int(r.get("repeat", 0)) == 0:
            out[r["item_id"]] = int((r.get("usage") or {}).get("prompt_tokens"))
    return out


def char_estimate(spec, rows) -> dict:
    """Character-based token estimate, calibrated on the arm's published log.

    For each item, the published run logged vLLM's prompt token count of the
    whole-window prompt.  The known-board count is estimated as that logged count
    plus b x (known-board chars - whole-window chars), b the least-squares slope
    of logged tokens on whole-window chars over the issuable items.  The fit's
    largest residual is reported, and the bound adds it to the largest estimate.
    """
    tok = logged_prompt_tokens(spec)
    xs = [r["prompt_chars_whole_window"] for r in rows if r["item_id"] in tok]
    ys = [tok[r["item_id"]] for r in rows if r["item_id"] in tok]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    a = my - b * mx
    resid = [y - (a + b * x) for x, y in zip(xs, ys)]
    est = [tok[r["item_id"]] + b * (r["prompt_chars"] - r["prompt_chars_whole_window"])
           for r in rows]
    reg = [a + b * r["prompt_chars"] for r in rows]
    max_res = max(abs(v) for v in resid)
    lim = spec["max_model_len"]
    return {
        "method": "character-based estimate (no tokenizer on disk): logged whole-window "
                  "count + slope x char difference; slope from a least-squares fit of the "
                  "arm's logged prompt tokens on whole-window chars",
        "items": len(rows), "fit_items": n, "slope_tokens_per_char": b, "intercept": a,
        "fit_max_abs_residual": max_res,
        "whole_window_logged": {"median": statistics.median(ys), "max": max(ys)},
        "known_board_estimate": {"median": statistics.median(est), "p90": quantile(est, 0.9),
                                 "max": max(est), "max_plus_residual": max(est) + max_res},
        "known_board_regression": {"median": statistics.median(reg), "max": max(reg)},
        "max_model_len": lim, "max_tokens": spec["max_tokens"],
        "exceed_max_model_len": sum(1 for v in est if v >= lim),
        "exceed_max_model_len_with_residual": sum(1 for v in est if v + max_res >= lim),
        "exceed_room_for_max_tokens": sum(1 for v in est if v + spec["max_tokens"] > lim),
        "whole_window_logged_exceed": sum(1 for v in ys if v >= lim),
    }


def token_audit_subprocess(arm, spec, probe_path=None) -> dict:
    """Run --token-audit in env l1 with no GPU visible and no network."""
    env = dict(os.environ)
    env.update({"CUDA_VISIBLE_DEVICES": "", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                "TOKENIZERS_PARALLELISM": "false", "OMP_NUM_THREADS": "1"})
    cmd = [L1_PYTHON, str(Path(__file__).resolve()), "--token-audit", "--audit-arm", arm]
    if probe_path:
        cmd += ["--tokenizer-path", probe_path]
    res = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=3600)
    if res.returncode != 0:
        return {"ok": False, "stderr": res.stderr[-2000:]}
    return json.loads(res.stdout.strip().splitlines()[-1])


def cmd_token_audit(args) -> int:
    """env l1: count tokens of every known-board and whole-window prompt with the tokenizer."""
    if os.environ.get("CUDA_VISIBLE_DEVICES", None) != "":
        raise SystemExit("REFUSING TO RUN: --token-audit needs CUDA_VISIBLE_DEVICES=''")
    from transformers import AutoTokenizer  # noqa: E402

    spec = LOCAL_ARMS[args.audit_arm]
    path = args.tokenizer_path or spec["model_snapshot"]
    tok = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
    rows = read_jsonl(PROMPTS_FILE)
    items = {it["item_id"]: it for it in sg.load_suite()}
    inst = sg.Instances()
    prompts_mod = sg.load_prompts_module()
    logged = {} if args.tokenizer_path else logged_prompt_tokens(spec)

    def count(msgs):
        try:
            text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True,
                                           enable_thinking=False)
        except TypeError:
            text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        return len(tok(text).input_ids), len(tok(text, add_special_tokens=False).input_ids)

    known, whole, eq_def, eq_nos = [], [], 0, 0
    for r in rows:
        k_def, _k_nos = count(r["messages"])
        known.append(k_def)
        it = items[r["item_id"]]
        w_def, w_nos = count(prompts_mod.build_messages(inst.get(it), it, TOP_K))
        whole.append(w_def)
        if r["item_id"] in logged:
            eq_def += int(w_def == logged[r["item_id"]])
            eq_nos += int(w_nos == logged[r["item_id"]])
    lim = spec["max_model_len"]
    out = {"ok": True, "arm": args.audit_arm, "tokenizer_path": path,
           "probe_only": bool(args.tokenizer_path), "items": len(rows),
           "known_board": {"median": statistics.median(known), "max": max(known),
                           "exceed_max_model_len": sum(1 for v in known if v >= lim),
                           "exceed_room_for_max_tokens":
                               sum(1 for v in known if v + spec["max_tokens"] > lim)},
           "whole_window": {"median": statistics.median(whole), "max": max(whole)},
           "whole_window_equal_to_logged": {"add_special_tokens": eq_def,
                                            "no_special_tokens": eq_nos, "of": len(logged)},
           "torch_imported": "torch" in sys.modules,
           "max_model_len": lim}
    print(json.dumps(out))
    return 0


# --------------------------------------------------------------------------- #
# Hosted token volumes from the published logs                                 #
# --------------------------------------------------------------------------- #
def price_in_force(A):
    """(label, prices) of the base in force for a run launched today."""
    for label, prices in A.prices:
        if label.startswith("standard"):
            return label, prices
    return A.prices[0]


def hosted_volumes(rows) -> dict:
    import grid_e1_hosted as H

    iss = {r["item_id"]: r for r in rows}
    out = OrderedDict()
    for arm, spec in HOSTED.items():
        A = H.ARMS[arm]
        # The price base in force today (2026-11-10): grid_e1_hosted lists the base
        # in force on its price_date first; Sonnet's "intro" base ended 2026-08-31,
        # so its "standard" base applies to a run launched now.
        pname, base = price_in_force(A)
        per = OrderedDict()
        for r in read_jsonl(RESULTS / spec["dir"] / "proposals_raw.dedup.jsonl"):
            if r.get("mode") != MODE or r["item_id"] not in iss:
                continue
            key = (r.get("thinking"), int(r.get("repeat", 0)))
            c = per.setdefault(key, Counter())
            u = r.get("usage") or {}
            c["calls"] += 1
            c["in"] += int(u.get("prompt_tokens") or 0)
            c["out"] += int(u.get("completion_tokens") or 0)
            c["cache_read"] += int(u.get("cache_hit_tokens") or 0)
            c["usd_logged"] += H.call_usd(base, u)
            c["usd_nocache"] += ((u.get("prompt_tokens") or 0) * base["in"]
                                 + (u.get("completion_tokens") or 0) * base["out"])
        delta_chars = sum(r["prompt_chars"] - r["prompt_chars_whole_window"] for r in rows)
        labels = OrderedDict()
        for (th, rep), c in per.items():
            labels.setdefault(th, []).append(c)
        arm_out = OrderedDict()
        tot = Counter()
        for th, cs in labels.items():
            n_rep = len(cs)
            mean = {k: sum(c[k] for c in cs) / n_rep for k in ("calls", "in", "out", "cache_read",
                                                                "usd_logged", "usd_nocache")}
            d_in = delta_chars / A.chars_per_token
            two = {"calls": 2 * mean["calls"], "in_tokens": 2 * (mean["in"] + d_in),
                   "out_tokens": 2 * mean["out"],
                   "usd_at_logged_cache_pattern": 2 * mean["usd_logged"],
                   "usd_no_cache": 2 * (mean["usd_nocache"] + d_in * base["in"])}
            for k, v in two.items():
                tot[k] += v
            arm_out[str(th)] = {"published_repeats": n_rep, "per_pass_logged": mean,
                                "known_board_input_delta_tokens_per_pass": d_in,
                                "two_repeat_run": two}
        out[arm] = {"display": spec["display"], "table6": spec["table6"],
                    "price_base": pname, "price_date": A.price_date,
                    "chars_per_token": A.chars_per_token, "by_thinking": arm_out,
                    "two_repeat_total": dict(tot)}
    return out


# --------------------------------------------------------------------------- #
# Resolved configurations and their diff against the published run_meta        #
# --------------------------------------------------------------------------- #
def local_config(arm, inputs, items_sha, prompts_sha) -> OrderedDict:
    s = LOCAL_ARMS[arm]
    return OrderedDict(
        arm=arm, items=N_ISSUABLE, item_set_sha256=items_sha, modes=[MODE],
        repeats=s["repeats"], suite_sha256=inputs["suite_sha256"],
        schema_sha256=inputs["schema_sha256"], model_snapshot=s["model_snapshot"],
        model_repo=s["repo"], model_revision=s["revision"], prompt_version=KNOWN_VERSION,
        prompt_variant=PROMPT_VARIANT, prompts_sha256=prompts_sha, top_k=TOP_K,
        max_tokens=s["max_tokens"], max_model_len=s["max_model_len"], temperature=0.0,
        seed=0, backend="xgrammar", gpu_memory_utilization=s["gpu_memory_utilization"],
        max_num_seqs=s["max_num_seqs"], max_num_seqs_source=s["max_num_seqs_source"],
        trust_remote_code=False, chat_template="the snapshot's own, enable_thinking=False",
        env={"VLLM_USE_FLASHINFER_SAMPLER": "0", "TOKENIZERS_PARALLELISM": "false"},
        out_dir="results/grid_e1_known_{}".format(s["short"]))


def published_local_meta(arm) -> dict:
    return json.loads((RESULTS / LOCAL_ARMS[arm]["published_dir"] / "run_meta.json").read_text())


def hosted_config(arm, inputs, items_sha, prompts_sha, workers=8, arm_obj=None,
                  out_dir=None) -> OrderedDict:
    import grid_e1_hosted as H
    from l1guard.models import BACKENDS

    A = arm_obj if arm_obj is not None else H.ARMS[arm]
    return OrderedDict(
        arm=A.arm, model=A.model, backend=A.backend, wire=BACKENDS[A.backend].wire,
        modes=[MODE], thinking=[lab for lab, _ in A.thinking],
        thinking_bodies={str(lab): body for lab, body in A.thinking},
        repeats=HOSTED[arm]["repeats"], items=N_ISSUABLE, item_set_sha256=items_sha,
        max_tokens=H.MAX_TOKENS, workers=int(workers), timeout_s=240.0, max_retries=4,
        suite_sha256=inputs["suite_sha256"], schema_sha256=inputs["schema_sha256"],
        prompt_version=KNOWN_VERSION, prompt_variant=PROMPT_VARIANT,
        prompts_sha256=prompts_sha, top_k=TOP_K, cache_boundary=H.CACHE_BOUNDARY,
        cache_boundary_fallback=H.CACHE_BOUNDARY_FALLBACK,
        cache_group="(instance, frozen seed, t_d): the known board differs between decision "
                    "instants, so items share a cached prefix only within one t_d",
        out_dir=out_dir or "results/grid_e1_known_{}".format(arm))


def published_hosted_meta(arm) -> dict:
    metas = []
    for p in sorted((RESULTS / HOSTED[arm]["dir"]).glob("run_meta_*.json")):
        m = json.loads(p.read_text())
        if not m.get("mock"):
            metas.append((p.name, m))
    if not metas:
        raise SystemExit("no published run_meta for hosted arm {}".format(arm))
    # The first file is the main run; later files are resumes that retried API
    # errors, some with fewer workers.  The main run is the comparator.
    return {"file": metas[0][0], "meta": metas[0][1], "n_files": len(metas)}


def diff_config(cfg, pub, keys) -> list:
    out = []
    for k in keys:
        if k not in pub:
            out.append({"key": k, "published": "<not recorded>", "known_board": cfg.get(k),
                        "category": "not recorded in the published run_meta"})
            continue
        a, b = pub[k], cfg.get(k)
        if a != b:
            out.append({"key": k, "published": a, "known_board": b,
                        "category": ALLOWED_DIFF.get(k, "NOT ALLOWED")})
    for k in cfg:
        if k not in keys and k not in pub:
            out.append({"key": k, "published": "<not recorded>", "known_board": cfg[k],
                        "category": "not recorded in the published run_meta"})
    return out


def check_diff(check, arm, diffs):
    bad = [d for d in diffs if d["category"] == "NOT ALLOWED"]
    check.true("CFG", "every configuration difference is prompt version, item set or modes "
               "({})".format(arm), not bad, bad)


# --------------------------------------------------------------------------- #
# Analysis globs the new directory names must not match                        #
# --------------------------------------------------------------------------- #
GLOB_RE = re.compile(r"""["']([^"'\n]*[*?][^"'\n]*)["']""")


def glob_audit(check, extra_names=()) -> dict:
    """Every glob pattern in the analysis code, matched against the new directory names."""
    import fnmatch

    names = ["grid_e1_known_" + s["short"] for s in LOCAL_ARMS.values()]
    names += ["grid_e1_known_" + a for a in HOSTED] + ["grid_e1_known_dryrun",
                                                         "n19_known_eval", "n19_selftest"]
    names += [n for n in extra_names if n not in names]
    files = sorted(set(list((ROOT / "code" / "scripts").glob("*.py"))
                       + list((ROOT / "analysis").glob("*.py"))
                       + list((ROOT / "manuscript" / "figures").glob("*.py"))
                       + list((ROOT / "manuscript" / "tools").glob("*.py"))))
    hits, patterns, wildcard = [], [], []
    for f in files:
        if f.name in ("grid_e1_known.py", "n19_known_prompt_eval.py"):
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if "glob" not in line:
                continue
            for m in GLOB_RE.finditer(line):
                pat = m.group(1)
                patterns.append("{}: {}".format(f.name, pat))
                for part in [x for x in re.split(r"[/\\]", pat) if x]:
                    if part == "*":
                        # a bare wildcard component matches any directory: listed
                        # for review, judged by what the pattern then requires
                        wildcard.append("{}: {}".format(f.name, pat))
                        continue
                    for n in names:
                        if fnmatch.fnmatch(n, part):
                            hits.append((f.name, pat, n))
        for lit in ("grid_e1_local", "grid_e1_hosted"):
            for m in re.finditer(r"""startswith\(\s*["']({}[^"']*)["']""".format(lit), text):
                patterns.append("{}: startswith {}".format(f.name, m.group(1)))
                for n in names:
                    if n.startswith(m.group(1)):
                        hits.append((f.name, "startswith " + m.group(1), n))
    check.true("GLOB", "no analysis glob or prefix test matches a new directory name",
               not hits, hits)
    return {"files_scanned": len(files), "patterns": sorted(set(patterns)), "hits": hits,
            "wildcard_components": sorted(set(wildcard)), "names": names}


# --------------------------------------------------------------------------- #
# --dry-run                                                                    #
# --------------------------------------------------------------------------- #
def cmd_dry_run(args) -> int:
    print(LAUNCH_QUESTIONS)
    check = Fatal()
    inputs = sg.assert_inputs()
    print("[known] suite sha256  {} OK".format(inputs["suite_sha256"]))
    print("[known] schema sha256 {} OK".format(inputs["schema_sha256"]))
    DRY.mkdir(parents=True, exist_ok=True)

    print("[known] rendering the known-board prompts on K at t_d ...", flush=True)
    res = render_all(check)
    check.stop_if_failed("render")
    rows = res["rows"]
    print("[known] {} prompts rendered in {:.0f} s ({} items not issuable)".format(
        len(rows), res["wall_s"], res["stats"].get("not_issuable", 0)))
    xh = crosscheck_logged_hashes(check, rows)
    check.stop_if_failed("prompt-hash cross-check")
    for arm, v in xh.items():
        print("[known] whole-window render = logged prompt_hash: {:<16s} {}/{} rows".format(
            arm, v["equal"], v["rows_compared"]))

    write_jsonl(PROMPTS_FILE, rows)
    write_jsonl(UNKNOWN_FILE, res["unknown"])
    prompts_sha = sha256_file(PROMPTS_FILE)
    unknown_sha = sha256_file(UNKNOWN_FILE)
    items_sha = item_set_sha(r["item_id"] for r in rows)

    # ---- leak re-check from the files, exactly as the generation phase runs it
    rel = recheck_leak_from_files(check, prompts_sha, unknown_sha)
    check.stop_if_failed("leak re-check")

    n_known = [r["n_known"] for r in rows]
    share = [r["n_known"] / r["n_window"] for r in rows]
    n_td0 = sum(1 for r in rows if r["t_d"] == 0.0)
    chars = [r["prompt_chars"] for r in rows]
    chars_w = [r["prompt_chars_whole_window"] for r in rows]
    leak_summary = {
        "prompts": len(rows), "board_leaks": 0,
        "board_check": "no id token of an order unknown at t_d in the system prompt and the "
                       "state block (fatal, all prompts); every order id shown is on K; no "
                       "order completed by t_d is shown",
        "instruction_text_naming_unknown": len(res["instr_unknown"]),
        "instruction_examples": res["instr_unknown"][:10],
        "full_text_prompts_with_unknown_id": len(res["instr_unknown"]),
        "whole_window_prompts_naming_unknown": len(res["whole_leaks"]),
        "whole_window_unknown_ids_median": (statistics.median(res["whole_leaks"])
                                            if res["whole_leaks"] else 0),
        "recheck_from_files": rel,
    }

    # ---- token audit
    token = OrderedDict()
    for arm, spec in LOCAL_ARMS.items():
        if tokenizer_present(spec["model_snapshot"]):
            token[arm] = token_audit_subprocess(arm, spec)
            token[arm]["method"] = "local tokenizer of the pinned snapshot, env l1, no GPU"
        else:
            token[arm] = char_estimate(spec, rows)
            token[arm]["snapshot_on_disk"] = False
    probe = None
    if args.tokenizer_probe:
        probe = token_audit_subprocess("qwen3-14b", LOCAL_ARMS["qwen3-14b"], args.tokenizer_probe)
        probe["note"] = ("code-path probe only: another model's tokenizer, run to exercise the "
                         "env-l1 audit path with no GPU; it is not a count for any arm")
    write_json(TOKEN_FILE, {"arms": token, "probe": probe})

    # ---- hosted volumes, configurations, diffs
    vols = hosted_volumes(rows)
    configs, diffs = OrderedDict(), OrderedDict()
    for arm in LOCAL_ARMS:
        cfg = local_config(arm, inputs, items_sha, prompts_sha)
        d = diff_config(cfg, published_local_meta(arm), LOCAL_KEYS)
        check_diff(check, arm, d)
        configs[arm], diffs[arm] = cfg, d
    for arm in HOSTED:
        cfg = hosted_config(arm, inputs, items_sha, prompts_sha)
        pub = published_hosted_meta(arm)
        d = diff_config(cfg, pub["meta"], HOSTED_KEYS)
        check_diff(check, arm, d)
        configs["hosted:" + arm], diffs["hosted:" + arm] = cfg, d
    globs = glob_audit(check)
    gpu = gpu_selftest(check)
    check.stop_if_failed("configuration")

    meta = OrderedDict(
        version=VERSION, date=time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        prompt_version=KNOWN_VERSION, base_prompt_version=BASE_VERSION, top_k=TOP_K,
        items=len(rows), item_set_sha256=items_sha, prompts_file=str(PROMPTS_FILE.relative_to(ROOT)),
        prompts_sha256=prompts_sha, unknown_file=str(UNKNOWN_FILE.relative_to(ROOT)),
        unknown_sha256=unknown_sha, suite_sha256=inputs["suite_sha256"],
        schema_sha256=inputs["schema_sha256"], instance_root=SNAPSHOT_ROOT,
        leak_status="PASS", leak=leak_summary, configs=configs, diffs=diffs,
        board={"n_known_median": statistics.median(n_known), "n_known_max": max(n_known),
               "known_share_median": statistics.median(share),
               "known_share_q1": quantile(share, 0.25), "known_share_q3": quantile(share, 0.75),
               "t_d_at_window_start": n_td0,
               "prompt_chars_median": statistics.median(chars),
               "prompt_chars_whole_window_median": statistics.median(chars_w),
               "prompt_chars_max": max(chars), "prompt_chars_whole_window_max": max(chars_w)},
        logged_hash_crosscheck=xh, glob_audit=globs, gpu_refusal_selftest=gpu,
        nvidia_smi_called=False, checks=check.summary())
    write_json(CONFIG_FILE, meta)
    write_json(REPORT_FILE, {"token_audit": token, "hosted_volumes": vols, "leak": leak_summary,
                             "board": meta["board"], "diffs": diffs, "checks": check.summary()})
    print_dry_summary(meta, token, probe, vols, diffs, globs)
    return 0


def recheck_leak_from_files(check, prompts_sha, unknown_sha) -> dict:
    """The generation phase's leak check: stdlib only, from the two dry-run files."""
    check.true("FILE", "prompt file SHA-256 as recorded", sha256_file(PROMPTS_FILE) == prompts_sha)
    check.true("FILE", "unknown-id file SHA-256 as recorded",
               sha256_file(UNKNOWN_FILE) == unknown_sha)
    prompts_mod = sg.load_prompts_module()
    unk = {(u["instance_id"], u["frozen_seed"], float(u["t_d"])): set(u["unknown"])
           for u in read_jsonl(UNKNOWN_FILE)}
    items = {it["item_id"]: it for it in sg.load_suite()}
    n, n_board, n_full = 0, 0, 0
    for r in read_jsonl(PROMPTS_FILE):
        it = items[r["item_id"]]
        check.true("FILE", "prompt hash recomputes from the stored messages",
                   prompts_mod.prompt_fingerprint(r["messages"]) == r["prompt_hash"], r["item_id"])
        check.true("FILE", "system message is the frozen one",
                   r["messages"][0]["content"] == prompts_mod.SYSTEM_PROMPT, r["item_id"])
        check.true("FILE", "prompt version", r["prompt_version"] == KNOWN_VERSION, r["item_id"])
        u = unk[(r["instance_id"], frozen_key(r["frozen_seed"]), float(r["t_d"]))]
        lk = leak_of(r["messages"], it["instruction"], u)
        n += 1
        n_board += int(bool(lk["board"]))
        n_full += int(bool(lk["full"]))
        check.true("LEAK", "file re-check: no unknown order in the board part", not lk["board"],
                   r["item_id"])
    check.true("FILE", "1,723 prompts in the file", n == N_ISSUABLE, n)
    return {"prompts": n, "board_leaks": n_board, "full_text_hits": n_full}


def print_dry_summary(meta, token, probe, vols, diffs, globs):
    b, lk = meta["board"], meta["leak"]
    print("\n" + "=" * 80)
    print("DRY-RUN SUMMARY  (no model loaded, no GPU touched, nvidia-smi not called)")
    print("=" * 80)
    print("prompts      : {} rendered on K at t_d, version {}".format(meta["items"],
                                                                     meta["prompt_version"]))
    print("               file {} sha256 {}".format(meta["prompts_file"], meta["prompts_sha256"]))
    print("               known board: median {:.0f} orders, known share median {:.1%} "
          "(Q1 {:.1%}, Q3 {:.1%}); t_d = 0 for {}".format(
              b["n_known_median"], b["known_share_median"], b["known_share_q1"],
              b["known_share_q3"], b["t_d_at_window_start"]))
    print("               chars median {:.0f} (whole window {:.0f}), max {} (whole window {})"
          .format(b["prompt_chars_median"], b["prompt_chars_whole_window_median"],
                  b["prompt_chars_max"], b["prompt_chars_whole_window_max"]))
    print("leak check   : PASS on {} prompts (board part: 0 unknown ids); re-check from the "
          "files: {} board leaks".format(lk["prompts"], lk["recheck_from_files"]["board_leaks"]))
    print("               instructions whose own text names an order unknown at t_d: {}".format(
        lk["instruction_text_naming_unknown"]))
    print("               whole-window prompts of the same items naming an unknown order: {}"
          .format(lk["whole_window_prompts_naming_unknown"]))
    print("token audit  :")
    for arm, t in token.items():
        if "known_board_estimate" in t:
            e = t["known_board_estimate"]
            print("  {:<16s} {}: median {:.0f}, p90 {:.0f}, max {:.0f} (max + fit residual "
                  "{:.0f}); max_model_len {} -> {} exceed ({} with residual); whole window "
                  "logged median {:.0f}, max {}".format(
                      arm, "CHAR ESTIMATE", e["median"], e["p90"], e["max"],
                      e["max_plus_residual"], t["max_model_len"], t["exceed_max_model_len"],
                      t["exceed_max_model_len_with_residual"], t["whole_window_logged"]["median"],
                      t["whole_window_logged"]["max"]))
        else:
            print("  {:<16s} {}".format(arm, json.dumps(t)[:300]))
    if probe:
        print("  probe          {}".format(json.dumps(probe)[:400]))
    print("hosted token volume of a two-repeat known-board run (constrained, 1,723 items):")
    for arm, v in vols.items():
        t = v["two_repeat_total"]
        print("  {:<9s} {:<38s} in {:>6.2f} M, out {:>5.2f} M tokens; USD {:.0f} at the logged "
              "cache pattern, {:.0f} with no cache hit ({} prices)".format(
                  arm, v["display"], t["in_tokens"] / 1e6, t["out_tokens"] / 1e6,
                  t["usd_at_logged_cache_pattern"], t["usd_no_cache"], v["price_base"]))
    print("configuration diff against the published run_meta:")
    for arm, ds in diffs.items():
        print("  {}:".format(arm))
        for d in ds:
            if d["category"].startswith("not recorded"):
                continue
            print("    {:<26s} {:<38s} published {} -> {}".format(
                d["key"], "[" + d["category"] + "]", json.dumps(d["published"])[:60],
                json.dumps(d["known_board"])[:60]))
        nr = [d["key"] for d in ds if d["category"].startswith("not recorded")]
        if nr:
            print("    not recorded in the published run_meta (known-board value kept in "
                  "resolved_config.json): {}".format(", ".join(nr)))
    print("glob audit   : {} files, {} patterns, {} hits on {}".format(
        globs["files_scanned"], len(globs["patterns"]), len(globs["hits"]), globs["names"]))
    print("checks       : {} passed".format(meta["checks"]["n_checks"]))
    print("NO MODEL LOADED, NO GPU CALL, NO NETWORK (--dry-run).")


# --------------------------------------------------------------------------- #
# The dry-run artifacts, verified before any generation                        #
# --------------------------------------------------------------------------- #
def load_artifacts(check) -> dict:
    if not CONFIG_FILE.is_file():
        raise SystemExit("REFUSING TO RUN: no dry run on disk ({}); run --dry-run first"
                         .format(CONFIG_FILE))
    meta = json.loads(CONFIG_FILE.read_text())
    check.true("FILE", "dry run recorded the leak check as PASS", meta.get("leak_status") == "PASS")
    check.true("FILE", "dry run prompt version", meta.get("prompt_version") == KNOWN_VERSION)
    rel = recheck_leak_from_files(check, meta["prompts_sha256"], meta["unknown_sha256"])
    rows = read_jsonl(PROMPTS_FILE)
    check.true("FILE", "item set SHA-256 as recorded",
               item_set_sha(r["item_id"] for r in rows) == meta["item_set_sha256"])
    # items.jsonl also lists the N3 protocol items (CA-/CN-); the suite's items only
    suite_ids = {it["item_id"] for it in sg.load_suite()}
    check.true("FILE", "item set equals the issuable suite items of results/n11_e2e/items.jsonl",
               {r["item_id"] for r in rows}
               == {r["item_id"] for r in read_jsonl(E2E_ITEMS)
                   if r["issuable"] and r["item_id"] in suite_ids})
    check.stop_if_failed("dry-run artifacts")
    print("[known] dry-run artifacts verified: {} prompts, sha256 {}, leak re-check {} board "
          "leaks".format(len(rows), meta["prompts_sha256"][:16], rel["board_leaks"]))
    return {"meta": meta, "rows": rows, "leak_recheck": rel}


def suite_rows_for(rows) -> list:
    items = {it["item_id"]: it for it in sg.load_suite()}
    return [items[r["item_id"]] for r in rows]


def verify_snapshot(spec) -> dict:
    """SHA-256 of the snapshot's files against env_checks/ (the published download's record).

    A file named in the record must exist and match; GLM-4-9B-0414 has no record, so its
    weight files are hashed and the hashes are kept in run_meta as the first record."""
    snap = Path(spec["model_snapshot"])
    if spec.get("checksums"):
        rec = ROOT / spec["checksums"]
        want = []
        for ln in rec.read_text().splitlines():
            if ln.strip():
                h, name = ln.split(None, 1)
                fp = Path(name.strip())
                want.append((h, fp if fp.is_absolute() else snap / fp))
        bad = []
        for h, fp in want:
            got = sha256_file(fp) if fp.is_file() else None
            if got != h:
                bad.append({"file": str(fp), "want": h, "got": got})
        return {"ok": not bad, "record": spec["checksums"], "n_files": len(want), "bad": bad,
                "summary": "{} of {} files match {}".format(len(want) - len(bad), len(want),
                                                             spec["checksums"])}
    files = sorted(p for p in snap.iterdir() if p.suffix in (".safetensors", ".json"))
    got = {p.name: sha256_file(p) for p in files}
    return {"ok": True, "record": None, "n_files": len(got), "bad": [], "computed": got,
            "summary": "no checksum record for this snapshot; {} files hashed and recorded in "
                       "run_meta".format(len(got))}


def base_row(item, pr, instance_path) -> dict:
    """grid_e1_local's row schema, plus the known-board fields."""
    return {
        "item_id": item["item_id"], "primary_class": item["primary_class"],
        "subclass": item["subclass"], "twin_id": item["twin_id"],
        "twin_role": item["twin_role"],
        "quality_visible_candidate": item.get("quality_visible_candidate"),
        "instance_id": item["instance"]["instance_id"], "instance_path": instance_path,
        "stratum": item["instance"]["stratum"], "rule": item["episode"]["rule"],
        "dispatch_seed": item["episode"]["seed"],
        "frozen_seed": list(item["episode"]["frozen_seed"]),
        "gold_ops": item["gold_ops"], "trap_ops": item["trap_ops"],
        "instruction": item["instruction"], "prompt_hash": pr["prompt_hash"],
        "prompt_hash_whole_window": pr["prompt_hash_whole_window"],
        "prompt_version": KNOWN_VERSION, "prompt_variant": PROMPT_VARIANT,
        "t_d": pr["t_d"], "n_known": pr["n_known"], "n_running": pr["n_running"],
        "known_frozen": pr["known_frozen"], "prompt_chars": pr["prompt_chars"],
    }


# --------------------------------------------------------------------------- #
# --arm: local generation (env l1, GPU)                                         #
# --------------------------------------------------------------------------- #
def cmd_local(args) -> int:
    arm = args.arm
    spec = LOCAL_ARMS[arm]
    print(LAUNCH_QUESTIONS)
    check = Fatal()
    inputs = sg.assert_inputs()
    print("[known] suite sha256  {} OK".format(inputs["suite_sha256"]))
    print("[known] schema sha256 {} OK".format(inputs["schema_sha256"]))
    art = load_artifacts(check)
    rows = art["rows"]
    cfg = local_config(arm, inputs, art["meta"]["item_set_sha256"], art["meta"]["prompts_sha256"])
    diffs = diff_config(cfg, published_local_meta(arm), LOCAL_KEYS)
    check_diff(check, arm, diffs)
    check.stop_if_failed("configuration")
    for d in diffs:
        print("[known] config vs published: {:<24s} [{}] {} -> {}".format(
            d["key"], d["category"], json.dumps(d["published"])[:50],
            json.dumps(d["known_board"])[:50]))
    if args.limit:
        rows = rows[: args.limit]
    out_dir = Path(args.out) if args.out else RESULTS / "grid_e1_known_{}".format(spec["short"])
    if args.limit:
        out_dir = out_dir.with_name(out_dir.name + "_smoke")
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit("REFUSING TO RUN: {} already has results".format(out_dir))
    if not Path(spec["model_snapshot"]).is_dir():
        raise SystemExit("REFUSING TO RUN: pinned snapshot missing: {} (download {} at revision "
                         "{} first, see the run sheet)".format(spec["model_snapshot"],
                                                              spec["repo"], spec["revision"]))
    snap = verify_snapshot(spec)
    print("[known] snapshot: {}".format(snap["summary"]), flush=True)
    if not snap["ok"]:
        raise SystemExit("REFUSING TO RUN: the snapshot does not match {}: {}".format(
            spec["checksums"], snap["bad"][:5]))
    gpu = gpu_check_live()
    print("[known] GPU samples: {} | apps: {}".format(gpu["samples"], gpu["apps"] or "none"))
    if not gpu["ok"]:
        raise SystemExit("REFUSING TO RUN: the card is not free: {}".format("; ".join(
            gpu["reasons"])))
    out_dir.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    import vllm
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import StructuredOutputsParams
    import grid_e1_local as L

    with open(sg.SCHEMA_PATH, "r", encoding="utf-8") as fh:
        schema = json.load(fh)
    print("[known] loading {} (vllm {})".format(spec["model_snapshot"], vllm.__version__),
          flush=True)
    llm_kwargs = dict(model=spec["model_snapshot"], max_model_len=spec["max_model_len"],
                      gpu_memory_utilization=spec["gpu_memory_utilization"], seed=0,
                      trust_remote_code=False, structured_outputs_config={"backend": "xgrammar"})
    if spec["max_num_seqs"]:
        llm_kwargs["max_num_seqs"] = spec["max_num_seqs"]
    llm = LLM(**llm_kwargs)
    resolved = getattr(llm.llm_engine.vllm_config.structured_outputs_config, "backend", "?")
    if resolved != "xgrammar":
        raise SystemExit("REFUSING TO RUN: backend resolved {!r}".format(resolved))
    tok = llm.get_tokenizer()
    prompts_text, n_tok = [], []
    for r in rows:
        try:
            text = tok.apply_chat_template(r["messages"], tokenize=False,
                                           add_generation_prompt=True, enable_thinking=False)
        except TypeError:  # pragma: no cover
            text = tok.apply_chat_template(r["messages"], tokenize=False,
                                           add_generation_prompt=True)
        if isinstance(text, list):
            text = tok.decode(text)
        prompts_text.append(text)
        n_tok.append(len(tok(text).input_ids))
    over = [r["item_id"] for r, n in zip(rows, n_tok) if n >= spec["max_model_len"]]
    print("[known] prompt tokens: median {}, max {}, {} at or above max_model_len {}".format(
        statistics.median(n_tok), max(n_tok), len(over), spec["max_model_len"]), flush=True)
    if over:
        raise SystemExit("REFUSING TO RUN: {} prompts exceed max_model_len: {}".format(
            len(over), over[:10]))

    items = suite_rows_for(rows)
    inst = sg.Instances()
    ns = argparse.Namespace(max_tokens=spec["max_tokens"])
    raw_path = out_dir / "proposals_raw.jsonl"
    walls, texts_by = {}, {}
    with open(raw_path, "w", encoding="utf-8") as fh:
        for repeat in range(spec["repeats"]):
            print("[known] generating {} r{} ...".format(MODE, repeat), flush=True)
            texts, usages, finish, wall = L.generate_mode(
                llm, SamplingParams, StructuredOutputsParams, schema, prompts_text, MODE, ns)
            walls["{}-r{}".format(MODE, repeat)] = wall
            texts_by[repeat] = texts
            print("[known] {} r{}: {} generations in {:.1f} s".format(MODE, repeat, len(texts),
                                                                      wall), flush=True)
            for item, pr, text, usage, fin in zip(items, rows, texts, usages, finish):
                row = base_row(item, pr, inst.path(item))
                row.update({"model": spec["model_snapshot"], "arm": arm, "thinking": None,
                            "mode": MODE, "repeat": repeat, "backend": "xgrammar",
                            "raw_output": text, "finish_reason": fin, "usage": usage})
                fh.write(json.dumps(row, sort_keys=True) + "\n")
            fh.flush()
    agreement = []
    for a in range(spec["repeats"]):
        for b in range(a + 1, spec["repeats"]):
            same = sum(1 for x, y in zip(texts_by[a], texts_by[b]) if x == y)
            agreement.append({"pair": "r{}r{}".format(a, b), "identical": same, "of": len(rows)})
    written = read_jsonl(raw_path)
    post = {"rows": len(written), "expected": len(rows) * spec["repeats"],
            "prompt_version_ok": all(r["prompt_version"] == KNOWN_VERSION for r in written),
            "truncated": sum(1 for r in written if r["finish_reason"] == "length")}
    meta = dict(cfg)
    meta.update(date=time.strftime("%Y-%m-%d %H:%M:%S %Z"), items=len(rows),
                gpu_at_launch=gpu["samples"], gpu_apps_at_launch=gpu["apps"], walls_s=walls,
                repeat_agreement={MODE: agreement}, diffs_vs_published=diffs,
                vllm_version=vllm.__version__, post_run=post, runner=VERSION,
                limit=args.limit, snapshot_check=snap)
    write_json(out_dir / "run_meta.json", meta)
    print("[known] repeat agreement: {}".format(agreement))
    print("[known] post-run: {}".format(post))
    print("[known] raw log: {}".format(raw_path))
    if post["rows"] != post["expected"] or not post["prompt_version_ok"]:
        raise SystemExit("POST-RUN CHECK FAILED: {}".format(post))
    return 0


# --------------------------------------------------------------------------- #
# --hosted: hosted generation (env fjsp, network, paid)                         #
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# design M3: the same-day whole-window control, its frozen item list            #
# --------------------------------------------------------------------------- #
CONTROL_DIR = RESULTS / "grid_e1_known_prelaunch_m3"
CONTROL_ITEMS_FILE = CONTROL_DIR / "control_items.json"
CONTROL_N = 200
CONTROL_SEED = 20261111
#: SHA-256 of CONTROL_ITEMS_FILE as written by --make-control-items on 2026-11-11, before
#: any control or known-board answer existed; asserted by the runner and by N19.
CONTROL_ITEMS_SHA256 = "4d07fb9bdf75d447cc9905f4a77737096f6ebb2e1e6d7415579250c575727e31"
CONTROL_RULE = (
    "Population: the 1,723 issuable instructions of the published suite (the dry run's "
    "prompts.jsonl, sha256 513f2cf8...). Cells: instruction class (benign, V1 to V6) x "
    "stratum (the three strata), 21 cells. Quota: 200 x cell size / 1,723, rounded down, the "
    "remaining places given one each to the cells with the largest remainders (ties by cell "
    "name, class then stratum). Draw: random.Random({seed}); for the cells in sorted order, "
    "sample(sorted item ids of the cell, quota). The list is the union, sorted. One repeat "
    "(r0) per Claude configuration, with the whole-window prompt of the logged run, sent on "
    "the day of the known-board run.").format(seed=CONTROL_SEED)


def control_selection(rows) -> OrderedDict:
    """The deterministic stratified draw of CONTROL_RULE over the dry run's prompt rows."""
    import random

    cells = OrderedDict()
    for r in sorted(rows, key=lambda x: x["item_id"]):
        cells.setdefault((r["primary_class"], r["stratum"]), []).append(r["item_id"])
    cells = OrderedDict(sorted(cells.items()))
    total = sum(len(v) for v in cells.values())
    exact = {c: CONTROL_N * len(v) / total for c, v in cells.items()}
    quota = {c: int(exact[c]) for c in cells}
    left = CONTROL_N - sum(quota.values())
    for c in sorted(cells, key=lambda c: (-(exact[c] - quota[c]), c))[:left]:
        quota[c] += 1
    rng = random.Random(CONTROL_SEED)
    chosen = []
    for c, ids in cells.items():
        chosen += rng.sample(sorted(ids), quota[c])
    return OrderedDict(
        rule=CONTROL_RULE, seed=CONTROL_SEED, n=CONTROL_N, population=total,
        population_sha256=EXPECTED_PROMPTS_SHA256,
        cells=[OrderedDict(primary_class=c[0], stratum=c[1], population=len(cells[c]),
                           quota=quota[c], exact_share=round(exact[c], 4)) for c in cells],
        items=sorted(chosen))


def cmd_make_control_items(args) -> int:
    check = Fatal()
    check.true("CTL", "prompt file is the pinned one",
               sha256_file(PROMPTS_FILE) == EXPECTED_PROMPTS_SHA256)
    check.stop_if_failed("control items")
    rows = read_jsonl(PROMPTS_FILE)
    sel = control_selection(rows)
    assert len(sel["items"]) == CONTROL_N == len(set(sel["items"]))
    text = json.dumps(sel, indent=1, sort_keys=False) + "\n"
    if CONTROL_ITEMS_FILE.exists():
        if CONTROL_ITEMS_FILE.read_text() != text:
            raise SystemExit("REFUSING TO RUN: {} exists with other content".format(
                CONTROL_ITEMS_FILE))
        print("[known] control item list already on disk and identical")
    else:
        CONTROL_DIR.mkdir(parents=True, exist_ok=True)
        CONTROL_ITEMS_FILE.write_text(text)
    print("[known] {} control items, sha256 {}".format(len(sel["items"]),
                                                       sha256_file(CONTROL_ITEMS_FILE)))
    return 0


def load_control_items(check) -> list:
    got = sha256_file(CONTROL_ITEMS_FILE) if CONTROL_ITEMS_FILE.is_file() else None
    check.true("CTL", "control item list SHA-256 is the recorded one",
               CONTROL_ITEMS_SHA256 is not None and got == CONTROL_ITEMS_SHA256, got)
    check.stop_if_failed("control items")
    sel = json.loads(CONTROL_ITEMS_FILE.read_text())
    check.true("CTL", "the list is reproduced by the rule",
               sel["items"] == control_selection(read_jsonl(PROMPTS_FILE))["items"])
    check.stop_if_failed("control items")
    return sel["items"]


def probe_verdict(log_path, arm) -> int:
    """design M3 step 5 on the probe log: every key answered, the answer parses and validates
    against the frozen schema, and the endpoint reported the pinned model; 0 = pass, 4 = fail."""
    from l1adapter.ops import validate_proposal

    last = OrderedDict()
    for r in read_jsonl(log_path):
        last[(r["mode"], r.get("thinking"), int(r["repeat"]), r["item_id"])] = r
    bad, usage = [], Counter()
    for k, r in last.items():
        why = None
        if r.get("outcome") != "ok":
            why = "outcome {} ({})".format(r.get("outcome"), str(r.get("api_error"))[:120])
        elif r.get("model_reported") != arm.model:
            why = "model {!r}".format(r.get("model_reported"))
        else:
            try:
                validate_proposal(json.loads(r["raw_output"]))
            except Exception as exc:  # noqa: BLE001
                why = "schema: {}".format(str(exc)[:120])
        if why:
            bad.append((k, why))
        u = r.get("usage") or {}
        for f in ("prompt_tokens", "completion_tokens", "cache_hit_tokens", "cache_write_tokens"):
            usage[f] += int(u.get(f) or 0)
    n = len(last)
    usd = sum(__import__("grid_e1_hosted").call_usd(arm.prices[0][1], r.get("usage") or {})
              for r in last.values())
    print("[probe] {} keys; {} pass (parse + schema + model id), {} fail; tokens {}; USD {:.4f} "
          "for these calls".format(n, n - len(bad), len(bad), dict(usage), usd), flush=True)
    for k, why in bad[:10]:
        print("[probe]   FAIL {}: {}".format(k, why), flush=True)
    return 0 if n and not bad else 4


class BackoffTransport:
    """The published client's urllib transport, with exponential backoff on 429 and 529.

    The request is built exactly as ``l1guard.models.urllib_transport`` builds it (the
    same method, URL, headers and body bytes, and the same ConnectionError on a URL
    error), so nothing on the wire changes.  Only the wait between attempts differs: a
    rate-limited (429) or overloaded (529) answer is retried after 2, 4, 8, 16, 32 and
    64 s (the provider's retry-after header wins when it is longer, each wait capped at
    120 s, plus up to 25% jitter).  After the last try the status is handed back to the
    client, whose own linear retries then apply unchanged.  design M3: another agent
    calls the same endpoints, so a burst of 429s must slow the run down and not turn
    into error rows.
    """

    def __init__(self):
        import threading

        self.lock = threading.Lock()
        self.rate_limited = 0
        self.by_status = Counter()
        self.slept_s = 0.0
        self.gave_up = 0
        self.requests = 0

    def __call__(self, method, url, headers, body, timeout):
        import random
        import urllib.error
        import urllib.request

        delay = BACKOFF_BASE_S
        for attempt in range(BACKOFF_TRIES):
            with self.lock:
                self.requests += 1
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            retry_after = None
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.status, resp.read()
            except urllib.error.HTTPError as exc:
                status, payload = exc.code, exc.read()
                retry_after = exc.headers.get("retry-after") if exc.headers is not None else None
            except urllib.error.URLError as exc:
                raise ConnectionError("{} {}: {}".format(method, url, exc)) from exc
            if status not in RATE_LIMIT_STATUS:
                return status, payload
            if attempt + 1 == BACKOFF_TRIES:
                with self.lock:
                    self.gave_up += 1
                return status, payload
            wait = delay
            try:
                wait = max(wait, float(retry_after))
            except (TypeError, ValueError):
                pass
            wait = min(BACKOFF_CAP_S, wait) * (1.0 + 0.25 * random.random())
            with self.lock:
                self.rate_limited += 1
                self.by_status[status] += 1
                self.slept_s += wait
            time.sleep(wait)
            delay *= 2.0
        raise AssertionError("unreachable")  # pragma: no cover

    def summary(self) -> dict:
        return {"http_requests": self.requests, "rate_limited_answers": self.rate_limited,
                "by_status": {str(k): v for k, v in self.by_status.items()},
                "backoff_slept_s": round(self.slept_s, 1), "gave_up_to_client": self.gave_up,
                "policy": "exponential on {}: {} tries, base {} s, x2, cap {} s, +<=25% jitter, "
                          "retry-after honoured".format(list(RATE_LIMIT_STATUS), BACKOFF_TRIES,
                                                        BACKOFF_BASE_S, BACKOFF_CAP_S)}


class RunAborted(KeyboardInterrupt):
    """Raised for calls that would start after an abort; grid_e1_hosted.run's
    KeyboardInterrupt handler then stops the pass loop and returns its accounting."""


class ModelGuard:
    """Asserts, on every answered call, that the endpoint reports the pinned model id.

    A mismatch writes the offending row to aborted_rows.jsonl (it is not appended to
    the raw log), sets the abort reason, and stops the run through the published
    runner's own interrupt path; calls not yet started are not sent.
    """

    def __init__(self, pinned: str, out_dir: Path):
        import threading

        self.pinned = pinned
        self.path = out_dir / "aborted_rows.jsonl"
        self.lock = threading.Lock()
        self.reason = None
        self.checked = 0
        self.reported = Counter()

    def wrap(self, orig, outcome_error):
        def one_call_known(client, arm_, call, kwargs, backend_):
            if self.reason is not None:
                raise RunAborted(self.reason)
            row = orig(client, arm_, call, kwargs, backend_)
            if row.get("outcome") != outcome_error:
                with self.lock:
                    self.checked += 1
                    self.reported[str(row.get("model_reported"))] += 1
                    bad = row.get("model_reported") != self.pinned
                    if bad and self.reason is None:
                        self.reason = ("the endpoint reported model {!r} for {} (pinned {!r})"
                                       .format(row.get("model_reported"), row["item_id"],
                                               self.pinned))
                    if bad:
                        with open(self.path, "a", encoding="utf-8") as fh:
                            fh.write(json.dumps(row, sort_keys=True) + "\n")
                if bad:
                    raise KeyboardInterrupt(self.reason)
            return row
        return one_call_known


def wire_record(client, H, arm, prep_known, prep_whole, check) -> dict:
    """The request each thinking setting sends, known board against whole window.

    Built with the published client's own request builder for the first planned item.
    Asserted: the two requests are identical except for the two user text blocks; the
    schema under output_config is the frozen schema file (metadata keys dropped); no
    field outside the published request is present.  Texts are replaced by their
    SHA-256 and length so the record holds no prompt.
    """
    import copy as _copy

    from l1guard.models import M_CONSTRAINED as _MC

    schema = json.loads(sg.SCHEMA_PATH.read_text(encoding="utf-8"))
    for k in ("$schema", "$id"):
        schema.pop(k, None)
    out = OrderedDict()
    for label, body in arm.thinking:
        kw = {"max_tokens": H.MAX_TOKENS}
        if body:
            kw["extra_body"] = body
        path, hdr, bk = client.build_request_anthropic(H.SYSTEM_PROMPT,
                                                       (prep_known.prefix, prep_known.tail),
                                                       _MC, **kw)
        _p, _h, bw = client.build_request_anthropic(H.SYSTEM_PROMPT,
                                                    (prep_whole.prefix, prep_whole.tail), _MC, **kw)

        def masked(b):
            b = _copy.deepcopy(b)
            for blk in b["messages"][0]["content"]:
                blk["text"] = "<{} chars, sha256 {}>".format(len(blk["text"]),
                                                             sha_text(blk["text"])[:16])
            return b
        mk, mw = masked(bk), masked(bw)
        same_but_text = (
            {k: v for k, v in mk.items() if k != "messages"}
            == {k: v for k, v in mw.items() if k != "messages"}
            and [{x: y for x, y in blk.items() if x != "text"} for blk in mk["messages"][0]["content"]]
            == [{x: y for x, y in blk.items() if x != "text"} for blk in mw["messages"][0]["content"]]
            and mk["messages"][0]["role"] == mw["messages"][0]["role"] == "user"
            and len(mk["messages"]) == len(mw["messages"]) == 1)
        check.true("WIRE", "known-board and whole-window requests differ only in the user "
                   "text ({})".format(label), same_but_text)
        check.true("WIRE", "output_config carries the frozen schema ({})".format(label),
                   bk.get("output_config") == {"format": {"type": "json_schema",
                                                          "schema": schema}})
        check.true("WIRE", "no field outside the published request ({})".format(label),
                   not [k for k in NOT_SENT if k in bk], [k for k in NOT_SENT if k in bk])
        check.true("WIRE", "system prompt is the frozen one ({})".format(label),
                   bk["system"] == [{"type": "text", "text": H.SYSTEM_PROMPT}])
        out[str(label)] = {
            "path": path, "headers_sent_besides_key": dict(hdr, **{"Content-Type":
                                                                   "application/json"}),
            "body_keys": sorted(bk), "model": bk["model"], "max_tokens": bk["max_tokens"],
            "thinking_field": bk.get("thinking", "<not sent: provider default>"),
            "output_config_schema_sha256": sha_text(json.dumps(bk["output_config"],
                                                               sort_keys=True)),
            "system_prompt_sha256": sha_text(H.SYSTEM_PROMPT),
            "user_blocks_known": [{x: y for x, y in blk.items()}
                                  for blk in mk["messages"][0]["content"]],
            "user_blocks_whole_window": [{x: y for x, y in blk.items()}
                                         for blk in mw["messages"][0]["content"]],
            "fields_not_sent": [k for k in NOT_SENT if k not in bk],
            "identical_except_user_text": same_but_text}
    return out


def cmd_hosted(args) -> int:
    arm_key = args.hosted
    if not args.i_have_approval_to_spend and not args.print_config:
        print("REFUSING TO RUN: --hosted {} calls a paid API. Re-run with "
              "--i-have-approval-to-spend once the author has approved the spend (the dry "
              "run prints the token volume).".format(arm_key))
        return 2
    if args.workers > HOSTED_MAX_WORKERS or args.workers < 1:
        print("REFUSING TO RUN: --workers {} (design M3: 1 to {} requests in flight per arm)"
              .format(args.workers, HOSTED_MAX_WORKERS))
        return 2
    import grid_e1_hosted as H
    from l1guard.logging import OUTCOME_ERROR
    from l1guard.models import BACKENDS, M_CONSTRAINED, ChatClient

    print(LAUNCH_QUESTIONS)
    check = Fatal()
    inputs = sg.assert_inputs()
    art = load_artifacts(check)
    rows = art["rows"]
    # ---- design M3 assertions, inside the run (fatal)
    check.true("RUN", "prompt file SHA-256 equals the pinned 513f2cf8...", (
        sha256_file(PROMPTS_FILE) == EXPECTED_PROMPTS_SHA256
        and art["meta"]["prompts_sha256"] == EXPECTED_PROMPTS_SHA256), sha256_file(PROMPTS_FILE))
    check.true("RUN", "1,723 prompts", len(rows) == N_ISSUABLE, len(rows))
    check.true("RUN", "zero board leaks in the prompt file",
               art["leak_recheck"]["board_leaks"] == 0 and art["leak_recheck"]["prompts"]
               == N_ISSUABLE, art["leak_recheck"])
    base_arm = H.ARMS[arm_key]
    thinking = base_arm.thinking
    if args.thinking:
        thinking = tuple(t for t in base_arm.thinking if str(t[0]) == args.thinking)
        if not thinking:
            print("REFUSING TO RUN: --thinking {!r} is not a setting of {} ({})".format(
                args.thinking, arm_key, [t[0] for t in base_arm.thinking]))
            return 2
    arm = dataclasses.replace(base_arm, modes=(M_CONSTRAINED,), thinking=thinking)
    suffix = "_" + args.thinking if args.thinking else ""
    kind = "control" if args.control else "known"
    out_dir = Path(args.out) if args.out else RESULTS / "grid_e1_{}_{}{}".format(kind, arm_key,
                                                                                suffix)
    ctl_items = load_control_items(check) if args.control else None
    if args.limit:
        out_dir = out_dir.with_name(out_dir.name + "_smoke")
    cfg = hosted_config(arm_key, inputs, art["meta"]["item_set_sha256"],
                        art["meta"]["prompts_sha256"], workers=args.workers, arm_obj=arm,
                        out_dir=str(out_dir.relative_to(ROOT)) if str(out_dir).startswith(
                            str(ROOT)) else str(out_dir))
    if args.control:
        # the comparator's own request, today: whole-window prompt, one repeat, 200 items
        cfg.update(repeats=1, items=len(ctl_items), prompt_version=BASE_VERSION,
                   prompt_variant="whole-window-control", prompts_sha256=None,
                   control_items_file=str(CONTROL_ITEMS_FILE.relative_to(ROOT)),
                   control_items_sha256=CONTROL_ITEMS_SHA256,
                   cache_group="(instance, frozen seed): the comparator's own grouping")
    pubm = published_hosted_meta(arm_key)
    pub = dict(pubm["meta"])
    split_note = None
    if args.thinking:
        check.true("CFG", "the setting exists in the published run with the same body",
                   args.thinking in [str(x) for x in pub["thinking"]]
                   and pub["thinking_bodies"].get(args.thinking) == dict(thinking)[thinking[0][0]],
                   (pub["thinking"], pub["thinking_bodies"]))
        split_note = {"key": "thinking", "published": list(pub["thinking"]),
                      "known_board": cfg["thinking"],
                      "category": "process split: this process runs one of the published "
                                  "settings, with the same request body (design M3: one "
                                  "process per Claude configuration, each within the cap)"}
        pub["thinking"] = [x for x in pub["thinking"] if str(x) == args.thinking]
        pub["thinking_bodies"] = {k: v for k, v in pub["thinking_bodies"].items()
                                  if k == args.thinking}
    diffs = diff_config(cfg, pub, HOSTED_KEYS)
    for d in diffs:
        if args.control and d["key"] == "repeats":
            d["category"] = "control design (design M3): one repeat, compared with r0 and r1"
    if split_note:
        diffs.append(split_note)
    check_diff(check, arm_key, diffs)
    check.stop_if_failed("configuration")
    backend = BACKENDS[arm.backend]
    items = suite_rows_for(rows)
    inst = sg.Instances()
    prepared = []
    if args.control:
        rows_by = {r["item_id"]: r for r in rows}
        logged = {}
        for r in read_jsonl(RESULTS / HOSTED[arm_key]["dir"] / "proposals_raw.dedup.jsonl"):
            if r.get("mode") == MODE and str(r.get("thinking")) in [str(t[0]) for t in thinking] \
                    and int(r.get("repeat", 0)) == 0:
                logged[r["item_id"]] = r["prompt_hash"]
        want = set(ctl_items)
        prepared = H.prepare([it for it in items if it["item_id"] in want], inst, TOP_K)
        for p in prepared:
            iid_ = p.item["item_id"]
            check.true("CTL", "control prompt = the comparator's logged prompt (hash)",
                       p.prompt_hash == logged.get(iid_)
                       == rows_by[iid_]["prompt_hash_whole_window"], iid_)
            p.known = rows_by[iid_]
        check.true("CTL", "200 control items prepared", len(prepared) == CONTROL_N
                   and {p.item["item_id"] for p in prepared} == want, len(prepared))
        rows, items = [], []
    for item, pr in zip(items, rows):
        msgs = pr["messages"]
        prefix, tail, which = H.split_user_prompt(msgs[1]["content"])
        if prefix + tail != msgs[1]["content"]:
            raise SystemExit("REFUSING TO RUN: split not byte-identical for " + item["item_id"])
        fp = H.PROMPTS.prompt_fingerprint([msgs[0], {"role": "user", "content": prefix + tail}])
        if fp != pr["prompt_hash"]:
            raise SystemExit("REFUSING TO RUN: split fingerprint differs for " + item["item_id"])
        if msgs[0]["content"] != H.SYSTEM_PROMPT:
            raise SystemExit("REFUSING TO RUN: system prompt differs from the frozen one")
        path = inst.path(item)
        p = H.Prepared(item=item, instance_path=path,
                       group=(path, tuple(item["episode"]["frozen_seed"]), pr["t_d"]),
                       prefix=prefix, tail=tail, prompt_hash=pr["prompt_hash"], split_at=which)
        p.known = pr  # carried into every row by the make_row wrapper below
        prepared.append(p)
    prepared.sort(key=lambda p: (p.group, p.item["item_id"]))
    n_items = CONTROL_N if args.control else N_ISSUABLE
    check.true("RUN", "{} prepared calls per pass".format(n_items), len(prepared) == n_items
               and len({p.item["item_id"] for p in prepared}) == n_items, len(prepared))
    full_plan = H.build_plan(arm, prepared, cfg["repeats"], 0)
    check.true("RUN", "plan = items x repeats x settings", len(full_plan) ==
               n_items * cfg["repeats"] * len(arm.thinking), len(full_plan))
    check.stop_if_failed("run assertions")
    if args.limit:
        prepared = prepared[: args.limit]

    loaded = H.load_env()  # before the client, as grid_e1_hosted.main: base URL
    transport = BackoffTransport()
    client = ChatClient(arm.backend, model=arm.model, api_key=None, max_tokens=H.MAX_TOKENS,
                        timeout_s=240.0, max_retries=4, retry_sleep_s=2.0, transport=transport)
    check.true("RUN", "endpoint is the published default", client.base_url ==
               backend.default_base_url.rstrip("/"), client.base_url)
    # the whole-window render of the first planned item, for the wire comparison
    whole = H.prepare([prepared[0].item], inst, TOP_K)[0]
    check.true("RUN", "whole-window render of the first item has the logged hash",
               whole.prompt_hash == prepared[0].known["prompt_hash_whole_window"])
    if args.control:
        check.true("RUN", "control request is the whole-window request",
                   (whole.prefix, whole.tail) == (prepared[0].prefix, prepared[0].tail))
    wire = wire_record(client, H, arm, prepared[0], whole, check)
    check.stop_if_failed("wire")
    globs = glob_audit(check, extra_names=[out_dir.name, out_dir.name + "_smoke",
                                           "grid_e1_known_prelaunch_m3"]
                       + ["grid_e1_control_" + n for n in ("sonnet", "opus_default",
                                                           "opus_disabled")])
    check.stop_if_failed("glob audit")
    resolved = OrderedDict(
        config=cfg, comparator_run_meta=pubm["file"], comparator_meta=pubm["meta"],
        comparator_meta_files=pubm["n_files"], diffs_vs_published=diffs,
        endpoint=client.base_url + "/v1/messages", anthropic_version_header=wire[
            str(arm.thinking[0][0])]["headers_sent_besides_key"].get("anthropic-version"),
        temperature="never sent on the anthropic wire (published client)",
        seed="none (published client drops it)", stop_conditions="none sent: the model's own "
        "end of turn, max_tokens 4096, or a refusal", effort="not sent: the model's default",
        retries={"client": {"max_retries": 4, "retry_sleep_s": 2.0, "schedule": "linear "
                            "2 x attempt on 429/5xx/529 and connection errors"},
                 "transport": transport.summary()["policy"]},
        wire=wire, glob_audit={"hits": globs["hits"], "names": globs["names"],
                               "files_scanned": globs["files_scanned"]},
        plan_calls_total=len(full_plan), out_dir=str(out_dir), checks=check.summary())
    if args.print_config:
        dst = RESULTS / "grid_e1_known_prelaunch_m3"
        dst.mkdir(parents=True, exist_ok=True)
        fn = dst / "resolved_{}{}{}.json".format("control_" if args.control else "", arm_key,
                                                 suffix)
        write_json(fn, resolved)
        print(json.dumps({"diffs": diffs, "wire": wire, "endpoint": resolved["endpoint"]},
                         indent=1, default=str))
        print("[known-h] resolved configuration written to {} (no call made)".format(fn))
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    stamp_file = out_dir / "prompts_sha256.txt"
    stamp = (CONTROL_ITEMS_SHA256 + " control items (whole-window prompts)" if args.control
             else art["meta"]["prompts_sha256"])
    if stamp_file.exists() and stamp_file.read_text().strip() != stamp:
        raise SystemExit("REFUSING TO RUN: {} was written from another prompt file".format(out_dir))
    stamp_file.write_text(stamp + "\n")
    log_path = out_dir / "proposals_raw.jsonl"

    # The published client, request builder, retry and resume logic, unchanged:
    # the module's prompt-version constant (row field and resume guard) and its
    # row builder are pointed at the known-board variant for this process only;
    # one_call is wrapped by the model-identifier assertion.
    H.PROMPT_VERSION = BASE_VERSION if args.control else KNOWN_VERSION
    orig_make_row = H.make_row

    def make_row_known(arm_, call, resp, latency_ms, backend_):
        row = orig_make_row(arm_, call, resp, latency_ms, backend_)
        pr = call["prep"].known
        if args.control:
            row.update(prompt_variant="whole-window-control", t_d=pr["t_d"],
                       control_items_sha256=CONTROL_ITEMS_SHA256)
            return row
        row.update(prompt_variant=PROMPT_VARIANT, t_d=pr["t_d"], n_known=pr["n_known"],
                   n_running=pr["n_running"], known_frozen=pr["known_frozen"],
                   prompt_hash_whole_window=pr["prompt_hash_whole_window"],
                   prompt_chars=pr["prompt_chars"])
        return row
    H.make_row = make_row_known
    guard = ModelGuard(arm.model, out_dir)
    H.one_call = guard.wrap(H.one_call, OUTCOME_ERROR)
    done, nrows, errors, broken = H.read_completed(log_path, arm)
    plan = [c for c in H.build_plan(arm, prepared, cfg["repeats"], 0)
            if H.row_key(c["mode"], c["thinking"], c["repeat"],
                         c["prep"].item["item_id"]) not in done]
    print("[known-h] arm {} ({}), settings {}, {} calls planned, {} keys already logged "
          "({} rows, {} error rows, {} torn), workers {}".format(
              arm.arm, arm.model, [t[0] for t in arm.thinking], len(plan), len(done), nrows,
              errors, broken, args.workers), flush=True)
    if not os.environ.get(backend.api_key_env):
        print("REFUSING TO RUN: {} is not set ({} names loaded)".format(backend.api_key_env,
                                                                       len(loaded)))
        return 2
    if not plan:
        print("[known-h] nothing to do: every planned key is already logged")
        return probe_verdict(log_path, arm) if args.limit else 0
    ns = argparse.Namespace(max_tokens=H.MAX_TOKENS, workers=args.workers)
    result = H.run(arm, ns, plan, log_path, client)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    meta = dict(cfg)
    meta.update(date=time.strftime("%Y-%m-%d %H:%M:%S %Z"), planned_calls=len(plan),
                rows_written=result["written"], wall_s=result["wall_s"],
                interrupted=result["interrupted"], diffs_vs_published=diffs,
                comparator_run_meta=pubm["file"],
                price_base=arm.prices[0][0], price_date=arm.price_date,
                usd_estimated=sum(c["usd"] for c in result["tally"].values()),
                per_config={"{}|{}|r{}".format(m, t, r): v
                            for (m, t, r), v in result["tally"].items()},
                model_guard={"pinned": arm.model, "answered_rows_checked": guard.checked,
                             "reported": dict(guard.reported), "abort_reason": guard.reason},
                transport=transport.summary(), endpoint=resolved["endpoint"], wire=wire,
                runner=VERSION + "+m3", mock=False, limit=args.limit,
                dedupe_rule="last row per (arm, mode, thinking, repeat, item_id) wins; an "
                            "earlier row for a key is a superseded API error",
                launch_checks=check.summary())
    write_json(out_dir / "run_meta_{}.json".format(stamp), meta)
    print("[known-h] raw log {}; estimated spend this session USD {:.2f} ({} base); model "
          "guard: {} answered rows checked, reported {}; transport {}".format(
              log_path, meta["usd_estimated"], arm.prices[0][0], guard.checked,
              dict(guard.reported), transport.summary()), flush=True)
    if guard.reason:
        print("ABORTED: {} (offending row kept in {})".format(guard.reason, guard.path),
              flush=True)
        return 3
    if result["interrupted"]:
        return 130
    if args.limit:
        return probe_verdict(log_path, arm)
    done2, _n, _e, _b = H.read_completed(log_path, arm)
    missing = [c for c in H.build_plan(arm, prepared, cfg["repeats"], 0)
               if H.row_key(c["mode"], c["thinking"], c["repeat"], c["prep"].item["item_id"])
               not in done2]
    if missing:
        print("[known-h] INCOMPLETE: {} keys end in an API error; re-run the same command to "
              "retry them".format(len(missing)), flush=True)
        return 5
    print("[known-h] COMPLETE: every planned key is answered", flush=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--arm", choices=list(LOCAL_ARMS))
    g.add_argument("--hosted", choices=list(HOSTED))
    g.add_argument("--token-audit", action="store_true", help=argparse.SUPPRESS)
    g.add_argument("--make-control-items", dest="make_ctl", action="store_true",
                   help="write the frozen control item list of design M3 (refuses to change it)")
    ap.add_argument("--i-have-approval-to-spend", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--limit", type=int, default=0,
                    help="first N items only; the output directory gets the suffix _smoke")
    ap.add_argument("--workers", type=int, default=HOSTED_MAX_WORKERS,
                    help="hosted only: requests in flight (design M3: at most 4 per arm)")
    ap.add_argument("--thinking", default=None,
                    help="hosted only: run one thinking setting of the arm (output folder gets "
                         "the suffix _<setting>)")
    ap.add_argument("--control", action="store_true",
                    help="hosted only: the same-day whole-window control on the frozen 200 "
                         "items (design M3), output results/grid_e1_control_<arm>[_<setting>]/")
    ap.add_argument("--print-config", action="store_true",
                    help="hosted only: resolve and record the configuration, the wire request "
                         "and the diff against the published run; no call is made")
    ap.add_argument("--audit-arm", choices=list(LOCAL_ARMS), help=argparse.SUPPRESS)
    ap.add_argument("--tokenizer-path", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--tokenizer-probe", default=None,
                    help="dry run only: a local tokenizer directory to exercise the env-l1 "
                         "audit path (reported as a probe, never as an arm's count)")
    args = ap.parse_args(argv)
    if args.dry_run:
        return cmd_dry_run(args)
    if args.token_audit:
        return cmd_token_audit(args)
    if args.make_ctl:
        return cmd_make_control_items(args)
    if args.arm:
        return cmd_local(args)
    return cmd_hosted(args)


if __name__ == "__main__":
    sys.exit(main())
