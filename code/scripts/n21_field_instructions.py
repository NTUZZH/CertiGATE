#!/usr/bin/env python3
"""N21: the practitioners' own instructions through the proposers and the gate.

Design pre-specified before the run.  Frozen design: the decision record, entry
"2026-11-11 01:20", decision 2 (and the freeze of 2026-11-10 20:05).  Choices the design leaves
open: results/field_v1/design_choices.md (recorded 01:32, before any gate result).

Eight facility-management practitioners wrote 235 instructions on eight scenario cards (real
boards of the benchmark).  This script

  transcribe  step 1: every filled answer row of the eight returned workbooks, verbatim, to
              results/field_v1/instructions.csv; "About you" to respondents.csv.  The workbooks
              are data: they are opened only by a separate ``python -I`` process that reads
              cell values (openpyxl, data_only) and prints them as JSON.  Nothing in them is
              executed and they are never written.
  items       step 2: per instruction the order ids it names, the ids not on the instance, the
              decision instant by the benchmark's rule (n11_decision_time.issuability /
              decision_instant_of), issuability (results/field_v1/items.jsonl).
  prompts     step 3 (dry run, CPU, no network): the known-board prompt of every issuable item at
              its decision instant with grid_e1_known's construction and the frozen prompt module;
              the leak assertion (grid_e1_known.leak_of) is run-fatal; prompt hashes and the file
              hash; token estimates and the GPT-5.4-mini cost rule.
  verify      step 5 precondition: the same replay code on 50 published suite items of the same
              eight instances (canonical proposals) and on 50 logged Claude rows (raw text),
              asserted equal to the stored decision-time rows (results/field_v1/verify_report.json).
  provenance  plain facts on the returned files (document properties, entry times, structure
              against the sent workbook), read by a separate ``python -I`` zip reader.
  describe    table e (the field set beside the generated suite) and the text regularities
              (results/field_v1/table_e.json, text_regularities.json); no model, no replay.
  hosted      step 4: one hosted arm (sonnet, opus = both thinking settings, openai) through
              grid_e1_hosted's client, request builder, plan, writer and resume logic; refuses
              without --i-have-approval-to-spend; at most 4 requests in flight; exponential
              backoff in the transport on 429 / 529 / 5xx; never re-sends a logged key; on
              every answered call asserts that the endpoint's model identifier is the pinned
              one, and sends nothing more after a mismatch (exit code 3).
  local       step 4, local arms (GPU, env l1; NOT run by this analysis): the grid_e1_known local
              settings on the field prompts, one repeat, output results/field_v1/<short>/.
  evaluate    steps 5 to 8: every log present under results/field_v1/<arm>/ replayed through the
              schema check, the feasibility check and the six gate designs on the known board at
              t_d, the full-information reading, the second price and its site variant, the
              realised run to the end of the window (realised damage and cost); tables a to f;
              analysis/N21_macros.tex (copied to the manuscript's macro file), analysis/N21_rows.csv,
              analysis/N21_summary.md; the self-test (two numbers per table by a second path).

Reused code paths (nothing is re-implemented): n11_decision_time.gen_price (the guard's three
stages at t_d), issuability, decision_instant_of, kf_fix, full_brackets, load_anchor_records;
n8_causal.trajectory / site_state / known_instance / pin_schedule / named_orders;
n11_forecast.prices_of / slim (the direct benchmark's K and FI prices); n16_robustness
.realised_range / cost_class / site_price (loaded from source with its core allowance set to
10-11 in memory, as n20 does; the file on disk is untouched); n2_pricing.op_split and Boot (the
cluster bootstrap); grid_e1_known.leak_of / split_prompt / id_tokens; grid_e1_hosted's client
path.

Cores 10-11 only, one thread.  No GPU (except the ``local`` subcommand, not run here), no
time-limited solve: every price is a deterministic dispatch plus an analytic bound.

Run (from the repository root):
  OMP_NUM_THREADS=1 taskset -c 10-11 python3 code/scripts/n21_field_instructions.py transcribe
  OMP_NUM_THREADS=1 taskset -c 10-11 python3 code/scripts/n21_field_instructions.py items
  OMP_NUM_THREADS=1 taskset -c 10-11 python3 code/scripts/n21_field_instructions.py prompts
  OMP_NUM_THREADS=1 taskset -c 10-11 python3 code/scripts/n21_field_instructions.py verify
  OMP_NUM_THREADS=1 taskset -c 10-11 python \\
      code/scripts/n21_field_instructions.py hosted --arm sonnet --i-have-approval-to-spend
  OMP_NUM_THREADS=1 taskset -c 10-11 python3 code/scripts/n21_field_instructions.py evaluate
Version: l1-n21-field-1
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_v] = "1"

SNAPSHOT_ROOT = ((os.environ.get("L1_Y1_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "PaperY-FMScheduling")) + "/data/processed/instances_v10")
_env_root = os.environ.get("L1_INSTANCE_ROOT")
if _env_root and os.path.realpath(_env_root) != os.path.realpath(SNAPSHOT_ROOT):
    raise SystemExit("REFUSING TO RUN: L1_INSTANCE_ROOT={} is not the snapshot {}"
                     .format(_env_root, SNAPSHOT_ROOT))
os.environ["L1_INSTANCE_ROOT"] = SNAPSHOT_ROOT

import sys  # noqa: E402

ALLOWED_CORES = {10, 11}
_aff = set(os.sched_getaffinity(0))
if not _aff <= ALLOWED_CORES and not os.environ.get("CERTIGATE_ANY_CORES"):
    raise SystemExit("REFUSING TO RUN: affinity {} is not inside cores 10-11 "
                     "(run under taskset -c 10-11)".format(sorted(_aff)))

import argparse  # noqa: E402
import copy  # noqa: E402
import csv  # noqa: E402
import dataclasses  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import random  # noqa: E402
import re  # noqa: E402
import statistics  # noqa: E402
import subprocess  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
import types  # noqa: E402
from collections import Counter, OrderedDict, defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent
CODE = SCRIPTS_DIR.parent
ROOT = CODE.parent
for _p in (str(CODE), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import suite_gate as sg  # noqa: E402  (hash gates, prompt module, instances)
import grid_e1_known as GK  # noqa: E402  (leak check, known-board version, local arm table)

VERSION = "l1-n21-field-1"
RESULTS = ROOT / "results"
ANALYSIS = ROOT / "analysis"
MANU = ROOT / "manuscript"
OUT = RESULTS / "field_v1"
PACK = (ROOT / "participant_files" / "returned_workbooks" /
        "1_Field_Instructions")
CARD_MANIFEST = ROOT / "participant_files" / "field_instructions" / "card_manifest.json"
INSTANCE_MANIFEST = SCRIPTS_DIR / "instance_manifest_l1.json"
CHOICES = OUT / "design_choices.md"
INSTR_CSV = OUT / "instructions.csv"
RESP_CSV = OUT / "respondents.csv"
TRANSCRIBE_REPORT = OUT / "transcribe_report.json"
ITEMS_JSONL = OUT / "items.jsonl"
ITEMS_CSV = OUT / "items.csv"
PROMPTS_JSONL = OUT / "prompts.jsonl"
PROMPTS_META = OUT / "prompts_meta.json"
VERIFY_REPORT = OUT / "verify_report.json"
SPEND_LOG = OUT / "spend_log.md"
REPLAY_JSONL = OUT / "replay_rows.jsonl"
OUT_TEX = ANALYSIS / "N21_macros.tex"
OUT_MANU = MANU / "macros_n21.tex"
OUT_CSV = ANALYSIS / "N21_rows.csv"
OUT_MD = ANALYSIS / "N21_summary.md"
FJSP_PYTHON = os.environ.get("L1_PYTHON", sys.executable)

EXPECTED_ROWS = OrderedDict([("P1", 26), ("P2", 29), ("P3", 31), ("P4", 31), ("P5", 28),
                             ("P6", 31), ("P7", 28), ("P8", 31)])
N_EXPECTED = 235
SITUATIONS = tuple("ABCDEFGH")
ACTION_CHOICES = ("apply it", "ask me before applying", "refuse it")
DELAY_CHOICES = ("no", "yes, up to __ hours", "yes, any")
ANSWER_HEAD = ("Respondent code", "Card", "Situation (A-H)",
               "Instruction (exactly as you would say or type it)",
               "What should the system do? (apply it / ask me before applying / refuse it)",
               "Delay to other work acceptable? (no / yes, up to __ hours / yes, any)",
               'If "up to", how many hours?', "Why (optional)")
ABOUT_KEYS = OrderedDict([
    ("Respondent code", "respondent"),
    ("Your role (for example maintenance supervisor, facilities manager or dispatcher)", "role"),
    ("Years in facility management", "years"),
    ("Do you approve work-order changes?", "approval_frequency"),
    ("Do you use a computerised maintenance management system (CMMS)?", "cmms")])

KNOWN_VERSION = GK.KNOWN_VERSION        # l1-prompt-1.0.0+known-board
PROMPT_VARIANT = GK.PROMPT_VARIANT
TOP_K = GK.TOP_K
MODE = GK.MODE                          # M_constrained
EMPTY_RAW = json.dumps({"operations": []})
TAU = 0.20
FLOOR_BH = 1.0
SETTINGS = OrderedDict([("G-CERT", 0.20), ("G-CERT-M", 0.20), ("D-REL1", 0.02),
                        ("D-REL2", 0.02), ("D-ABS", 0.8119)])
DESIGNS = tuple(SETTINGS)
DELTAS = OrderedDict([("Twenty", 0.20), ("Ten", 0.10)])
DTOK = OrderedDict([("G-CERT", "Cert"), ("G-CERT-M", "CertM"), ("D-REL1", "RelOne"),
                    ("D-REL2", "RelTwo"), ("D-ABS", "Abs")])
BOOT_SEED = 20261026
BOOT_B = 20000
MAX_IN_FLIGHT = 4
BACKOFF_S = (2, 4, 8, 16, 32, 60)
RETRY_STATUS = (429, 500, 502, 503, 504, 529)

#: The hosted configurations of this analysis, as grid_e1_hosted arms and thinking labels.
HOSTED_ARMS = OrderedDict([("sonnet", "claude"), ("opus", "claude"), ("openai", "gpt")])
#: (arm directory, thinking label) -> (display name, macro token)
CELLS = OrderedDict([
    (("sonnet", "disabled"), ("Claude Sonnet 5", "SonnetFive")),
    (("opus", "default"), ("Claude Opus 5 (default)", "OpusFiveDefault")),
    (("opus", "disabled"), ("Claude Opus 5 (thinking disabled)", "OpusFiveOff")),
    (("openai", None), ("GPT-5.4-mini", "GptMini")),
    (("qwen14b", None), ("Qwen3-14B", "QwenFourteenB")),
    (("qwen27b", None), ("Qwen3.6-27B-FP8", "QwenTwentySevenB")),
    (("glm9b", None), ("GLM-4-9B-0414", "Glm")),
])
LOCAL_SHORT = OrderedDict((spec["short"], arm) for arm, spec in GK.LOCAL_ARMS.items())


# --------------------------------------------------------------------------- #
# Small utilities                                                              #
# --------------------------------------------------------------------------- #
def now_iso() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S %z")


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


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
            fh.write(json.dumps(r, sort_keys=True, default=str) + "\n")
    os.replace(tmp, path)


def write_json(path, obj) -> None:
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, sort_keys=True, default=str))
    os.replace(tmp, path)


def write_csv(path, rows, fields, comments=()) -> None:
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        for c in comments:
            fh.write("# " + c + "\n")
        w = csv.DictWriter(fh, fieldnames=list(fields), extrasaction="raise")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})
    os.replace(tmp, path)


def read_csv_comments(path) -> list:
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def frozen_key(seed) -> str:
    return ",".join(str(x) for x in (seed or ()))


class Check:
    """Run-fatal assertions, counted by group."""

    def __init__(self):
        self.n = Counter()
        self.failures = []

    def true(self, group, what, ok, detail=""):
        self.n[group] += 1
        if not ok:
            self.failures.append("{} {}: {}".format(group, what, str(detail)[:300]))

    def stop(self, where):
        if self.failures:
            print("ASSERTION FAILURES at {} ({} of {}):".format(
                where, len(self.failures), sum(self.n.values())), file=sys.stderr)
            for f in self.failures[:60]:
                print("  - " + f, file=sys.stderr)
            raise SystemExit(2)

    def summary(self):
        return {"n_checks": sum(self.n.values()), "by_group": dict(sorted(self.n.items())),
                "failures": list(self.failures)}


def load_frozen_module(name, swaps):
    """A frozen script loaded from its source with its core allowance replaced in memory.

    The swap is asserted to occur the expected number of times; the file on disk is
    untouched (the precedent is code/scripts/n20_stratum_abs.py)."""
    path = SCRIPTS_DIR / (name + ".py")
    src = path.read_text(encoding="utf-8")
    for old, new, count in swaps:
        if src.count(old) != count:
            raise SystemExit("{}: '{}' found {} times, expected {}".format(
                path.name, old, src.count(old), count))
        src = src.replace(old, new)
    mod = types.ModuleType(name)
    mod.__file__ = str(path)
    sys.modules[name] = mod
    exec(compile(src, str(path), "exec"), mod.__dict__)  # noqa: S102
    return mod


#: sha256 of the frozen files at the freeze of 2026-11-10 20:05 (decision record).
FROZEN_HASHES = OrderedDict([
    ("n16_robustness.py", "dde428a8cedf206a8f43bcd359a72317f72d6197d7a5203a5ca15da74c174481"),
    ("n13_fromlogs.py", "523c1e41df5e9c275e2bdc98e50d85444a227c43a0302d8dcd15802f8dbe3095"),
    ("n11_decision_time.py", "05978a918888782627f1cba89e67e590c306e0e6d52997e0181cbfc1fff2bc90"),
    ("n10_field_change.py", "5a790905576d49c182c19168e1fdb97ee1e479a595c1c2a8089aa127c31ebde5"),
])
#: Every source file the replay path reads code from (hashed into each report).
REUSED = ("n11_decision_time.py", "n11_forecast.py", "n16_robustness.py", "n13_fromlogs.py",
          "n8_causal.py", "n2_pricing.py", "grid_e1_known.py", "grid_e1_hosted.py",
          "suite_gate.py")


def assert_frozen(check) -> dict:
    got = OrderedDict()
    for name, want in FROZEN_HASHES.items():
        h = sha256_file(SCRIPTS_DIR / name)
        got[name] = h
        check.true("FROZEN", "{} sha256 equals the freeze".format(name), h == want, h)
    return got


def code_hashes() -> dict:
    out = OrderedDict((n, sha256_file(SCRIPTS_DIR / n)) for n in REUSED)
    for rel in ("l1guard/guard.py", "l1guard/prompts.py", "l1guard/models.py",
                "l1adapter/apply.py", "l1adapter/dispatch.py", "l1adapter/evaluate.py"):
        out[rel] = sha256_file(CODE / rel)
    out["n21_field_instructions.py"] = sha256_file(Path(__file__))
    return out


def replay_code_hashes() -> dict:
    """The hashes the verify report pins for the evaluation (this script excluded: its
    table code may change after the verification, its replay function is asserted by
    hash of its source text below)."""
    h = code_hashes()
    h.pop("n21_field_instructions.py")
    h["n21.replay_source"] = sha_text(_replay_source())
    return h


# --------------------------------------------------------------------------- #
# Step 1: transcription (workbooks read by a separate isolated interpreter)    #
# --------------------------------------------------------------------------- #
_READER = r'''
import json, sys
import openpyxl
out = {}
for p in sys.argv[1:]:
    wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
    d = {"sheets": list(wb.sheetnames)}
    for name in ("Answers", "About you"):
        ws = wb[name]
        rows = []
        for row in ws.iter_rows(values_only=True):
            rows.append([None if c is None else (c if isinstance(c, (int, float, str)) else str(c))
                         for c in row])
        d[name] = rows
    wb.close()
    out[p] = d
sys.stdout.write(json.dumps(out))
'''


def read_workbooks(paths) -> dict:
    """Cell values of the two sheets, read by ``python -I`` (no script dir, no site customisation,
    no environment variables) in a neutral working directory."""
    py = FJSP_PYTHON if Path(FJSP_PYTHON).is_file() else sys.executable
    res = subprocess.run([py, "-I", "-c", _READER] + [str(p) for p in paths],
                         capture_output=True, text=True, cwd=str(OUT), timeout=300,
                         env={"PATH": "/usr/bin:/bin", "OMP_NUM_THREADS": "1"})
    if res.returncode != 0:
        raise SystemExit("workbook reader failed: " + res.stderr[-2000:])
    return json.loads(res.stdout)


def card_manifest() -> dict:
    m = json.loads(CARD_MANIFEST.read_text())
    return OrderedDict((c["card_id"], c) for c in m["cards"]), m


def assignment(k: int) -> tuple:
    return ("Card {}".format((k - 1) % 8 + 1), "Card {}".format((k + 3) % 8 + 1))


def cmd_transcribe(args) -> int:
    check = Check()
    OUT.mkdir(parents=True, exist_ok=True)
    paths = [PACK / "Field_Instruction_Workbook_{}.xlsx".format(p) for p in EXPECTED_ROWS]
    hashes_before = OrderedDict((p.name, sha256_file(p)) for p in paths)
    data = read_workbooks(paths)
    cards, _m = card_manifest()
    rows, resp, anomalies = [], [], []
    for p in paths:
        code = p.stem.split("_")[-1]
        d = data[str(p)]
        check.true("T1", "sheets present in {}".format(p.name),
                   "Answers" in d["sheets"] and "About you" in d["sheets"], d["sheets"])
        ans = d["Answers"]
        check.true("T1", "Answers header of {}".format(p.name),
                   tuple(ans[0][:8]) == ANSWER_HEAD, ans[0][:8])
        k = 0
        assigned = assignment(int(code[1:]))
        for j, row in enumerate(ans[1:], start=2):
            row = list(row) + [None] * (8 - len(row))
            text = row[3]
            other = [c for i, c in enumerate(row[:8]) if i != 3 and c not in (None, "")]
            if text is None or (isinstance(text, str) and not text.strip()):
                if other:
                    anomalies.append({"workbook": p.name, "sheet_row": j,
                                      "issue": "row with answers but an empty instruction",
                                      "cells": row[:8]})
                continue
            k += 1
            rcode, card, sit, _t, act, delay, hours, why = row[:8]
            item_id = "F-{}-{:02d}".format(code, k)
            issues = []
            if rcode != code:
                issues.append("respondent code {!r} differs from the workbook {}".format(rcode, code))
            if card not in assigned:
                issues.append("card {!r} outside the assigned {}".format(card, list(assigned)))
            if sit not in SITUATIONS:
                issues.append("situation {!r} outside A-H".format(sit))
            if act not in ACTION_CHOICES:
                issues.append("action {!r} outside the dropdown".format(act))
            if delay not in DELAY_CHOICES:
                issues.append("delay {!r} outside the dropdown".format(delay))
            if delay == "yes, up to __ hours":
                if not isinstance(hours, (int, float)) or hours <= 0:
                    issues.append("delay 'up to' without a positive number of hours: {!r}"
                                  .format(hours))
            elif hours not in (None, ""):
                issues.append("hours {!r} given with delay answer {!r}".format(hours, delay))
            for s in issues:
                anomalies.append({"workbook": p.name, "sheet_row": j, "item_id": item_id,
                                  "issue": s})
            inst = cards[card]["instance_id"] if card in cards else None
            rows.append(OrderedDict(
                item_id=item_id, respondent=code, sheet_row=j, card=card, instance_id=inst,
                situation=sit, text=text, expected_action=act, delay_answer=delay,
                hours=hours, why=why))
        check.true("T2", "{} filled rows = {}".format(code, EXPECTED_ROWS[code]),
                   k == EXPECTED_ROWS[code], k)
        about = {r[0]: (r[1] if len(r) > 1 else None) for r in d["About you"][1:] if r and r[0]}
        rec = OrderedDict()
        for q, key in ABOUT_KEYS.items():
            check.true("T3", "About you of {} answers '{}'".format(code, key), q in about, q)
            rec[key] = about.get(q)
        check.true("T3", "About you respondent code of {}".format(code), rec["respondent"] == code,
                   rec["respondent"])
        resp.append(rec)
    check.true("T2", "235 rows in all", len(rows) == N_EXPECTED, len(rows))
    hashes_after = OrderedDict((p.name, sha256_file(p)) for p in paths)
    check.true("T4", "workbooks unchanged by the read", hashes_before == hashes_after)
    check.stop("transcribe")
    fields = ("item_id", "respondent", "sheet_row", "card", "instance_id", "situation", "text",
              "expected_action", "delay_answer", "hours", "why")
    write_csv(INSTR_CSV, rows, fields,
              comments=["N21 field instructions, transcribed verbatim from the eight returned "
                        "workbooks ({}); one row per filled answer row".format(VERSION)])
    write_csv(RESP_CSV, resp, list(ABOUT_KEYS.values()),
              comments=["N21 respondents, the 'About you' sheet of each workbook ({}); never "
                        "sent to a model".format(VERSION)])
    rep = {"version": VERSION, "date": now_iso(), "workbooks_sha256": hashes_before,
           "rows": dict(Counter(r["respondent"] for r in rows)), "n_rows": len(rows),
           "anomalies": anomalies, "checks": check.summary(),
           "instructions_csv_sha256": sha256_file(INSTR_CSV),
           "respondents_csv_sha256": sha256_file(RESP_CSV)}
    write_json(TRANSCRIBE_REPORT, rep)
    print("[n21] transcribed {} rows ({}); anomalies: {}".format(
        len(rows), dict(Counter(r["respondent"] for r in rows)), len(anomalies)))
    for a in anomalies:
        print("   ", a)
    return 0


def read_instructions() -> list:
    rows = read_csv_comments(INSTR_CSV)
    for r in rows:
        r["sheet_row"] = int(r["sheet_row"])
        r["hours"] = None if r["hours"] == "" else float(r["hours"])
    return rows


# --------------------------------------------------------------------------- #
# Step 2: the items (names, decision instant, issuability)                      #
# --------------------------------------------------------------------------- #
TOKEN_RE = GK.TOKEN_RE
ID_RE = {"storm": re.compile(r"^W\d+$"), "replay": re.compile(r"^\d{8}$")}


def id_shape(iid: str) -> str:
    return "replay" if "_replay_" in iid else "storm"


def text_names(text: str, inst: dict, shape: str) -> dict:
    """C3 and C5 of design_choices.md: ids, trades and buildings the text names."""
    toks = TOKEN_RE.findall(text or "")
    ids = []
    for t in toks:
        if ID_RE[shape].match(t) and t not in ids:
            ids.append(t)
    by_id = {w["id"]: w for w in inst["work_orders"]}
    trades_all = {w["trade"] for w in inst["work_orders"]} | {t["trade"] for t in
                                                              inst["technicians"]}
    buildings_all = {w["building"] for w in inst["work_orders"] if w.get("building")}
    on = [o for o in ids if o in by_id]
    off = [o for o in ids if o not in by_id]
    trades_named = sorted({t for t in toks if t in trades_all})
    buildings_named = sorted({t for t in toks if t in buildings_all})
    trades = sorted({by_id[o]["trade"] for o in on} | set(trades_named))
    return {"ids": ids, "ids_on_instance": on, "ids_not_on_instance": off,
            "trades_named": trades_named, "buildings_named": buildings_named,
            "referenced": {"order_ids": sorted(set(ids)), "trades": trades,
                           "buildings": buildings_named}}


class Instances:
    """Instance files of the eight cards, hash-gated, with their baselines and trajectories."""

    def __init__(self):
        import n11_decision_time as D
        from l1adapter import dispatch as dispatch_mod
        import n8_causal as n8
        self.D, self.dispatch, self.n8 = D, dispatch_mod, n8
        self.suite_meta = {}
        for it in sg.load_suite():
            self.suite_meta.setdefault(it["instance"]["instance_id"], it["instance"])
        self.cache = {}

    def get(self, iid):
        if iid not in self.cache:
            meta = self.suite_meta[iid]
            stub = {"item_id": "N21-" + iid, "instance": meta}
            path = self.D.instance_path(stub)         # sg.verify_instance_file: hash gate
            inst = self.D.load_instance(path)
            base = self.dispatch.dispatch_baseline(inst, "atc", 0)
            self.cache[iid] = {"path": path, "inst": inst, "baseline": base, "meta": meta,
                               "trajs": {}, "by_id": {w["id"]: w for w in inst["work_orders"]}}
        return self.cache[iid]

    def traj(self, iid, seed):
        c = self.get(iid)
        fk = frozen_key(seed)
        if fk not in c["trajs"]:
            c["trajs"][fk] = self.n8.trajectory(c["inst"], list(seed), c["baseline"])
        return c["trajs"][fk]


def field_item(r, card, meta, names) -> dict:
    """The suite-item shape the prompt module and the hosted row writer read."""
    return {
        "item_id": r["item_id"], "instruction": r["text"], "referenced": names["referenced"],
        "episode": {"rule": "atc", "seed": 0, "t_bh": 0.0,
                    "frozen_seed": list(card["frozen_set_shown"])},
        "instance": dict(meta), "primary_class": "field", "subclass": None, "twin_id": None,
        "twin_role": None, "quality_visible_candidate": None, "gold_ops": None,
        "trap_ops": None, "set": "field_v1"}


def cmd_items(args) -> int:
    check = Check()
    instr = read_instructions()
    check.true("I0", "235 transcribed rows", len(instr) == N_EXPECTED, len(instr))
    cards, man = card_manifest()
    manifest_files = json.loads(INSTANCE_MANIFEST.read_text())["files"]
    I = Instances()
    D = I.D
    out = []
    for r in instr:
        card = cards[r["card"]]
        iid = card["instance_id"]
        c = I.get(iid)
        if "sha_checked" not in c:
            got = sha256_file(c["path"])
            check.true("I1", "instance {} sha256 = card manifest".format(iid),
                       got == card["sha256"], got)
            rel = card["snapshot_relpath"]
            want = manifest_files.get(rel)
            want = want.get("sha256") if isinstance(want, dict) else want
            check.true("I1", "instance {} sha256 = instance_manifest_l1".format(iid),
                       got == want, (got, want))
            check.true("I1", "card in-progress set = suite standing frozen set",
                       list(card["frozen_set_shown"]) == list(card["order_ids"][:3]),
                       card["frozen_set_shown"])
            c["sha_checked"] = True
        names = text_names(r["text"], c["inst"], id_shape(iid))
        item = field_item(r, card, c["meta"], names)
        seed = item["episode"]["frozen_seed"]
        traj = I.traj(iid, seed)
        starts = {a["wo"]: float(a["start_bh"]) for a in traj["assignments"]}
        iss = D.issuability(item, c["by_id"], starts)
        t_d = D.decision_instant_of(iss, "primary")
        state = I.n8.site_state(c["inst"], traj, t_d, pm_known=True)
        n_window = len(c["inst"]["work_orders"])
        n_known = len(state["queue"]) + len(state["in_progress"]) + len(state["scheduled"])
        rec = OrderedDict(
            item_id=r["item_id"], respondent=r["respondent"], card=r["card"], instance_id=iid,
            stratum=c["meta"]["stratum"], situation=r["situation"],
            n_words=len(r["text"].split()), ids_named=names["ids"],
            ids_on_instance=names["ids_on_instance"],
            ids_not_on_instance=names["ids_not_on_instance"],
            ids_on_card=[o for o in names["ids"] if o in set(card["order_ids"])],
            trades_named=names["trades_named"], buildings_named=names["buildings_named"],
            referenced=names["referenced"], frozen_seed=seed, fk=frozen_key(seed),
            n_ref=iss["n_ref"], t_known=iss["t_known"], t_start=iss["t_start"],
            issuable=iss["issuable"], issuable_strict=iss["issuable_strict"], t_d=t_d,
            ref_all_pm=iss["ref_all_pm"],
            ref_completed=sorted(set(iss["ref_ids"]) & set(state["completed"])),
            ref_running=sorted(set(iss["ref_ids"]) & set(state["in_progress"])),
            n_window=n_window, n_known=n_known, n_completed=len(state["completed"]),
            n_unknown=len(state["unknown"]),
            later_share=len(state["unknown"]) / n_window, item=item)
        check.true("I2", "orders partition at t_d", rec["n_known"] + rec["n_completed"]
                   + rec["n_unknown"] == n_window, r["item_id"])
        if rec["issuable"]:
            check.true("I2", "issuable items name no order completed at t_d",
                       not rec["ref_completed"], r["item_id"])
        out.append(rec)
    check.stop("items")
    write_jsonl(ITEMS_JSONL, out)
    flds = ("item_id", "respondent", "card", "instance_id", "situation", "n_words", "ids_named",
            "ids_not_on_instance", "ids_on_card", "trades_named", "buildings_named", "n_ref",
            "t_known", "t_start", "issuable", "issuable_strict", "t_d", "ref_running",
            "n_window", "n_known", "n_completed", "n_unknown", "later_share")
    flat = []
    for rec in out:
        f = {k: rec[k] for k in flds}
        for k in ("ids_named", "ids_not_on_instance", "ids_on_card", "trades_named",
                  "buildings_named", "ref_running"):
            f[k] = "|".join(f[k])
        flat.append(f)
    write_csv(ITEMS_CSV, flat, flds, comments=["N21 items: names, decision instant, issuability "
                                               "({})".format(VERSION)])
    n_iss = sum(1 for r in out if r["issuable"])
    print("[n21] items: {} rows, {} issuable, {} not issuable; {} name no id; {} name an id "
          "not on the instance; t_d = 0 on {}".format(
              len(out), n_iss, len(out) - n_iss, sum(1 for r in out if not r["ids_named"]),
              sum(1 for r in out if r["ids_not_on_instance"]),
              sum(1 for r in out if r["t_d"] == 0.0)))
    return 0


# --------------------------------------------------------------------------- #
# Step 3: the known-board prompts (dry run)                                     #
# --------------------------------------------------------------------------- #
def current_price(A):
    """The arm's price base in force on the run date.  grid_e1_hosted lists Claude Sonnet 5's
    introductory base (through 2026-08-31) first and its standard base (from 2026-09-01)
    second; every other arm has one base.  The base changes no request, only the estimate."""
    if len(A.prices) == 1:
        return A.prices[0]
    std = [p for p in A.prices if p[0].startswith("standard")]
    if len(std) != 1 or time.strftime("%Y-%m-%d") < "2026-09-01":
        raise SystemExit("REFUSING TO RUN: cannot tell the price base in force for " + A.arm)
    return std[0]


def cmd_prompts(args) -> int:
    check = Check()
    items = read_jsonl(ITEMS_JSONL)
    P = sg.load_prompts_module()
    check.true("P0", "frozen prompt module version", P.PROMPT_VERSION == GK.BASE_VERSION,
               P.PROMPT_VERSION)
    I = Instances()
    D = I.D
    rows = []
    for rec in items:
        if not rec["issuable"]:
            continue
        iid = rec["instance_id"]
        c = I.get(iid)
        seed = rec["frozen_seed"]
        traj = I.traj(iid, seed)
        t_d = float(rec["t_d"])
        state = I.n8.site_state(c["inst"], traj, t_d, pm_known=True)
        known = I.n8.known_instance(c["inst"], state)
        kf = D.kf_fix(state, seed)
        kset = {w["id"] for w in known["work_orders"]}
        unknown = set(state["unknown"])
        item = rec["item"]
        item_k = copy.deepcopy(item)
        item_k["episode"]["t_bh"] = t_d
        item_k["episode"]["frozen_seed"] = list(kf)
        msgs = P.build_messages(known, item_k, TOP_K)
        lk = GK.leak_of(msgs, item["instruction"], unknown)
        check.true("LEAK", "no order unknown at t_d in the board part", not lk["board"],
                   (rec["item_id"], lk["board"][:5]))
        board, _ = GK.split_prompt(msgs[1]["content"], item["instruction"])
        all_ids = set(c["by_id"])
        shown = GK.id_tokens(msgs[0]["content"] + "\n" + board) & all_ids
        check.true("LEAK", "every order id the board shows is on K", shown <= kset,
                   (rec["item_id"], sorted(shown - kset)[:5]))
        check.true("LEAK", "no order completed by t_d in the board part",
                   not (shown & set(state["completed"])), rec["item_id"])
        check.true("P1", "every named order on the instance is on K",
                   all(o in kset for o in rec["ids_on_instance"]), rec["item_id"])
        rows.append(OrderedDict(
            item_id=rec["item_id"], instance_id=iid, stratum=rec["stratum"],
            frozen_seed=list(seed), known_frozen=list(kf), t_d=t_d,
            n_known=len(known["work_orders"]), n_running=len(state["in_progress"]),
            n_completed=len(state["completed"]), n_unknown=len(unknown),
            n_window=len(c["inst"]["work_orders"]), prompt_version=KNOWN_VERSION,
            prompt_hash=P.prompt_fingerprint(msgs),
            prompt_chars=sum(len(m["content"]) for m in msgs),
            leak_board=lk["board"], leak_instruction=lk["instruction"],
            messages=msgs, item=item))
    check.stop("prompts")
    write_jsonl(PROMPTS_JSONL, rows)
    psha = sha256_file(PROMPTS_JSONL)
    import grid_e1_hosted as H
    vols = OrderedDict()
    for arm_key in ("sonnet", "opus", "openai"):
        A = H.ARMS[arm_key]
        n_cfg = len(A.thinking)
        tok = [r["prompt_chars"] / A.chars_per_token + A.schema_tokens for r in rows]
        base = current_price(A)[1]
        out_tok = max(A.out_tokens.values())
        per = sum(tok) * base["in"] + len(rows) * out_tok * base["out"]
        vols[arm_key] = OrderedDict(
            model=A.model, configs=[str(l) for l, _ in A.thinking], prompts=len(rows),
            calls=len(rows) * n_cfg, chars_per_token=A.chars_per_token,
            schema_tokens=A.schema_tokens, in_tokens_est_per_config=round(sum(tok)),
            in_tokens_est_median=round(statistics.median(tok)),
            in_tokens_est_max=round(max(tok)), out_tokens_pilot_per_call=out_tok,
            usd_est_no_cache=round(per * n_cfg, 4), price_base=current_price(A)[0],
            price_source=A.price_source)
    gpt = vols["openai"]
    gpt_rule = OrderedDict(
        price_checked="developers.openai.com/api/docs/pricing.md, retrieved 2026-11-11: "
                      "gpt-5.4-mini $0.75 input, $0.075 cached input, $4.50 output per 1M "
                      "tokens (Standard)", usd_est=gpt["usd_est_no_cache"],
        usd_est_times_three=round(3 * gpt["usd_est_no_cache"], 4), budget_usd=4.41,
        run=3 * gpt["usd_est_no_cache"] < 4.41)
    meta = OrderedDict(version=VERSION, date=now_iso(), prompt_version=KNOWN_VERSION,
                       prompts=len(rows), prompts_sha256=psha,
                       item_set_sha256=sha_text("\n".join(sorted(r["item_id"] for r in rows))),
                       leak_status="PASS", board_leaks=0,
                       instruction_ids_unknown_at_td=sum(1 for r in rows if r["leak_instruction"]),
                       prompt_chars_median=statistics.median(r["prompt_chars"] for r in rows),
                       prompt_chars_max=max(r["prompt_chars"] for r in rows),
                       hosted_volumes=vols, gpt_cost_rule=gpt_rule, checks=check.summary())
    write_json(PROMPTS_META, meta)
    print("[n21] prompts: {} rendered, sha256 {}, 0 board leaks ({} checks)".format(
        len(rows), psha[:16], sum(check.n.values())))
    for k, v in vols.items():
        print("   {}: {} calls, ~{} input tokens per configuration (median {}, max {}), "
              "~USD {:.3f} without cache".format(k, v["calls"], v["in_tokens_est_per_config"],
                                                 v["in_tokens_est_median"],
                                                 v["in_tokens_est_max"], v["usd_est_no_cache"]))
    print("   GPT-5.4-mini rule: 3 x {:.3f} = {:.3f} < 4.41 -> {}".format(
        gpt["usd_est_no_cache"], 3 * gpt["usd_est_no_cache"], gpt_rule["run"]))
    return 0


# --------------------------------------------------------------------------- #
# The replay at the decision instant (shared by verify and evaluate)            #
# --------------------------------------------------------------------------- #
# REPLAY-SOURCE-BEGIN
class Site:
    """The site at (instance, frozen seed, t_d): K, kf, the anchors on K and on FI, the
    no-AI realised run.  Every call is the census / Stage 2 / Stage 3 call of the suite."""

    def __init__(self, I, iid, seed, t_d):
        D, n8 = I.D, I.n8
        c = I.get(iid)
        inst, baseline = c["inst"], c["baseline"]
        traj = I.traj(iid, seed)
        state = n8.site_state(inst, traj, t_d, pm_known=True)
        self.D, self.n8, self.inst, self.iid, self.t_d = D, n8, inst, iid, float(t_d)
        self.seed, self.fk = list(seed), frozen_key(seed)
        self.state = state
        self.known = n8.known_instance(inst, state)
        self.kf = D.kf_fix(state, seed)
        started = state["completed"] + state["in_progress"]
        self.k_ids = state["queue"] + state["in_progress"] + state["scheduled"]
        self.base_p = n8.pin_schedule(baseline, traj, started)
        self.frozen_r = list(started) + [o for o in seed if o not in set(started)]
        self.run_ids = list(state["in_progress"])
        done = set(state["completed"])
        fi = {k: v for k, v in inst.items() if k != "work_orders"}
        fi["work_orders"] = [wo for wo in inst["work_orders"] if wo["id"] not in done]
        self.fi = fi
        # n11_decision_time.census_instance: an = gen_price(known, EMPTY_RAW, kf, base_p, t_d)
        self.an = D.gen_price(self.known, EMPTY_RAW, self.kf, self.base_p, self.t_d)
        # n11_forecast.forecast_instance, FI anchor: price_at(fi, s, EMPTY_RAW, t_d, ref2=False)
        self.a_fi = D.gen_price(fi, EMPTY_RAW, self.kf, self.base_p, self.t_d, ref2=False,
                                keep_batch=self.k_ids, running_ids=self.run_ids)
        # census: rw0 = gen_price(inst, EMPTY_RAW, frozen_r, base_p, t_d, keep_batch=k_ids)
        self.rw0 = D.gen_price(inst, EMPTY_RAW, self.frozen_r, self.base_p, self.t_d,
                               keep_batch=self.k_ids, keep_live=True)
        self.rw0_live = self.rw0.pop("_live", None)
        self.unknown = set(state["unknown"])
        self.completed = done
        self.running = set(state["in_progress"])
        self.kset = set(self.k_ids)
        self.memo = {}

    def per_order_wt(self, live):
        """Weighted tardiness per order on the original fields (evaluate.wwt's formula)."""
        if not live or "schedule" not in live:
            return None
        orig = live["adjusted"].original
        by = {wo["id"]: wo for wo in orig["work_orders"]}
        out = {}
        for a in live["schedule"].get("assignments", []) or []:
            wo = by.get(a["wo"])
            if wo is None or a.get("end_bh") is None:
                continue
            out[a["wo"]] = float(wo["weight"]) * max(0.0, float(a["end_bh"]) - float(wo["due_bh"]))
        return out

    def replay(self, raw, text_ids=()):
        """Every reading of one proposal text (memoised on the exact text)."""
        key = self.D.raw_key(raw)
        if key in self.memo:
            return self.memo[key]
        from l1guard import guard as G
        from l1guard.config import G_CERT
        D = self.D
        # stage 1 strictly, as gen_price runs it (for the empty-proposal class)
        s_find, typed, _parse = G._stage_schema(self.known, raw, G_CERT)
        n_typed = None if typed is None else len(typed)
        # K: n11_decision_time.census_instance's dt call (Stage 2 price_td is the same call)
        k = D.gen_price(self.known, raw, self.kf, self.base_p, self.t_d, ref2=True,
                        running_ids=self.run_ids)
        # FI: n11_forecast price_at(fi, s, raw, t_d)
        f = D.gen_price(self.fi, raw, self.kf, self.base_p, self.t_d, ref2=True,
                        keep_batch=self.k_ids, running_ids=self.run_ids)
        rw = None
        if "applied_uncertified" in (k["term_feas"], f["term_feas"]):
            rw = D.gen_price(self.inst, raw, self.frozen_r, self.base_p, self.t_d,
                             keep_batch=self.k_ids, keep_live=True)
        try:
            lenient = json.loads(raw)["operations"] if isinstance(raw, str) else raw["operations"]
            explicit, members = self.n8.named_orders(lenient, self.inst)
        except Exception:  # noqa: BLE001 - a text that does not parse names nothing
            explicit, members = [], []
        all_ids = {wo["id"] for wo in self.inst["work_orders"]}
        rec = {"n_typed": n_typed, "schema_blocking": any(fi_.blocking for fi_ in s_find),
               "K": {kk: k.get(kk) for kk in D.PRICE_KEYS}, "K_ops": k.get("ops"),
               "K_tuples": k.get("tuples"),
               "FI": {kk: f.get(kk) for kk in D.PRICE_KEYS},
               "rw": None if rw is None else {"term_cert": rw["term_cert"],
                                              "term_feas": rw["term_feas"], "obj": rw["obj"],
                                              "obj_orig": rw["obj_orig"]},
               "names_not_on_instance": sorted(o for o in explicit if o not in all_ids),
               "names_unknown": sorted(o for o in explicit if o in self.unknown),
               "names_completed": sorted(o for o in explicit if o in self.completed),
               "names_running": sorted(o for o in explicit if o in self.running),
               "n_batch_members": len(members)}
        rec["damage_split"] = None
        if rw is not None and self.rw0_live is not None:
            w1 = self.per_order_wt(rw.get("_live"))
            w0 = self.per_order_wt(self.rw0_live)
            if w1 is not None and w0 is not None:
                by = {wo["id"]: wo for wo in self.inst["work_orders"]}
                tids = set(text_ids) & all_ids
                split = Counter()
                cls, trd = Counter(), Counter()
                for o in set(w1) | set(w0):
                    d = w1.get(o, 0.0) - w0.get(o, 0.0)
                    if d == 0.0:
                        continue
                    where = ("named" if o in tids else "known_at_td" if o in self.kset
                             else "later" if o in self.unknown else "completed")
                    split[where] += d
                    cls[int(by[o]["priority"])] += d
                    trd[by[o]["trade"]] += d
                rec["damage_split"] = {"where": dict(split), "class": {str(k_): v for k_, v in
                                                                         cls.items()},
                                       "trade": dict(trd), "sum": sum(split.values()),
                                       "rw_minus_rw0": rw["obj_orig"] - self.rw0["obj_orig"]}
        self.memo[key] = rec
        return rec
# REPLAY-SOURCE-END


def _replay_source() -> str:
    src = Path(__file__).read_text(encoding="utf-8")
    a = src.index("# REPLAY-SOURCE-BEGIN")
    b = src.index("# REPLAY-SOURCE-END")
    return src[a:b]


class Labels:
    """The suite's own price, flag and truth functions, loaded once."""

    def __init__(self):
        import n11_decision_time as D
        import n11_forecast as FC
        import n2_pricing as n2
        self.D, self.FC, self.n2 = D, FC, n2
        # n16 with its core allowance set to cores 10-11 in memory (n20's precedent); it loads
        # n13 the same way.  The files on disk are untouched (their hashes are asserted).
        self.n16 = load_frozen_module(
            "n16_robustness", [("ALLOWED_CORES = {14, 15}", "ALLOWED_CORES = {10, 11}", 2)])
        self.full_br = D.full_brackets()
        self.anchors = D.load_anchor_records()

    def prices(self, p, a):
        """n11_forecast.prices_of on the slim records."""
        return self.FC.prices_of(self.FC.slim(p), self.FC.slim(a))

    def anchor_wwt(self, iid, fk):
        return float(self.anchors[(iid, fk)]["wwt_original_bh"])

    def realised(self, rw_obj_orig, iid, fk):
        return self.n16.realised_range(rw_obj_orig, self.anchor_wwt(iid, fk), iid, self.full_br)

    def cost_class(self, lo, hi, delta):
        return self.n16.cost_class(lo, hi, delta)

    def second(self, obj_orig, a_lb):
        return (obj_orig - a_lb) / max(a_lb, FLOOR_BH)

    def site_second(self, obj_orig, a_obj):
        return self.n16.site_price(obj_orig, a_obj)


def unit_record(site, L, raw, text_ids=()):
    """Every number a table needs for one proposal on one site."""
    rec = site.replay(raw, text_ids)
    K, F = rec["K"], rec["FI"]
    out = OrderedDict()
    st, term = K["stage_cert"], K["term_cert"]
    if rec["schema_blocking"] or st == "schema":
        cls = "schema"
    elif rec["n_typed"] == 0:
        cls = "empty"
    elif st == "feas":
        cls = "feas" if term == "blocked_feas" else "infra_feas"
    elif st == "qual":
        cls = "priced" if term in ("applied_with_certificate", "blocked_qual") else "infra_qual"
    else:
        cls = "other"
    out["class"] = cls
    out["term_cert"], out["term_feas"], out["stage_cert"] = term, K["term_feas"], st
    out["codes"] = list(K["codes"] or [])
    out["dangling"] = "dangling_order_id" in out["codes"]
    out["n_ops"] = rec["n_typed"]
    ops = rec["K_ops"] or []
    out["op_types"] = sorted({o.get("op") for o in ops if isinstance(o, dict)})
    out["split"] = L.n2.op_split(ops) if rec["K_ops"] is not None else None
    for k in ("names_not_on_instance", "names_unknown", "names_completed", "names_running",
              "n_batch_members"):
        out[k] = rec[k]
    an = {kk: getattr(site, "an")[kk] for kk in L.D.PRICE_KEYS}
    afi = {kk: site.a_fi[kk] for kk in L.D.PRICE_KEYS}
    pk = L.prices(K, an)
    pf = L.prices(F, afi)
    out["K_obj"], out["K_obj_orig"], out["K_lb"], out["K_gap"] = (K["obj"], K["obj_orig"],
                                                                  K["lb"], K["gap"])
    out["an_obj"], out["an_lb"], out["an_gap"] = site.an["obj"], site.an["lb"], site.an["gap"]
    out["FI_stage"], out["FI_term"] = F["stage_cert"], F["term_cert"]
    for g in DESIGNS:
        out["pK_" + g] = pk[g]
        out["pFI_" + g] = pf[g]
        out["refK_" + g] = pk[g] is not None and pk[g] > SETTINGS[g]
        out["refFI_" + g] = pf[g] is not None and pf[g] > SETTINGS[g]
    field = out["split"] == "field_changing"
    out["g_orig"] = (L.second(K["obj_orig"], site.an["lb"])
                     if st == "qual" and K["obj_orig"] is not None else None)
    out["s2_site"] = (L.site_second(K["obj_orig"], site.an["obj"])
                      if st == "qual" and K["obj_orig"] is not None else None)
    out["g_orig_FI"] = (L.second(F["obj_orig"], site.a_fi["lb"])
                        if F["stage_cert"] == "qual" and F["obj_orig"] is not None else None)
    out["sp"] = bool(field and out["g_orig"] is not None and out["g_orig"] > TAU)
    out["sp_site"] = bool(field and out["s2_site"] is not None and out["s2_site"] > TAU)
    out["sp_FI"] = bool(field and out["g_orig_FI"] is not None and out["g_orig_FI"] > TAU)
    rw = rec["rw"]
    out["rw_term"] = None if rw is None else rw["term_cert"]
    out["rw_obj"] = None if rw is None else rw["obj"]
    out["rw_obj_orig"] = None if rw is None else rw["obj_orig"]
    aw = L.anchor_wwt(site.iid, site.fk)
    out["anchor_wwt"] = aw
    out["damage_bh"] = None if rw is None else rw["obj_orig"] - aw
    lo, hi = (None, None) if rw is None else L.realised(rw["obj_orig"], site.iid, site.fk)
    out["cost_lo"], out["cost_hi"] = lo, hi
    for dt, dv in DELTAS.items():
        out["cost" + dt] = L.cost_class(lo, hi, dv)
    out["damage_split"] = rec["damage_split"]
    out["rw0_obj_orig"] = site.rw0["obj_orig"]
    return out


class SiteCache:
    def __init__(self, I):
        self.I = I
        self.sites = {}

    def get(self, iid, seed, t_d):
        key = (iid, frozen_key(seed), float(t_d))
        if key not in self.sites:
            self.sites[key] = Site(self.I, iid, seed, t_d)
        return self.sites[key]


# --------------------------------------------------------------------------- #
# Step 5 precondition: reproduction on suite items of the same eight instances #
# --------------------------------------------------------------------------- #
VERIFY_SOURCES = OrderedDict([
    ("e1_eval_sonnet5", ("grid_e1_hosted_sonnet", "sonnet")),
    ("e1_eval_opus5", ("grid_e1_hosted_opus", "opus")),
])


def close(a, b, tol):
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= tol


def cmd_verify(args) -> int:
    check = Check()
    frozen = assert_frozen(check)
    check.stop("frozen hashes")
    cards, _m = card_manifest()
    eight = [c["instance_id"] for c in cards.values()]
    I = Instances()
    L = Labels()
    D = L.D
    suite = {it["item_id"]: it for it in sg.load_suite()}
    items_dt = {r["item_id"]: r for r in read_jsonl(RESULTS / "n11_decision_time" / "items.jsonl")
                if r["set"] == "published"}
    fc = defaultdict(dict)
    for r in read_csv_comments(ANALYSIS / "N11_rows_forecast.csv"):
        fc[r["reading"]][r["item_id"]] = r
    fi_rows = {r["uid"]: r for r in read_jsonl(RESULTS / "n11_forecast" / "fullinfo_direct.jsonl")}
    fn = lambda x: None if x in ("", None) else float(x)  # noqa: E731
    # ---- selection (design_choices C20), fixed before any comparison
    cand = sorted(i for i, r in items_dt.items() if r["instance_id"] in eight and r["issuable"])
    costly = [i for i in cand if i in fc["K"] and fn(fc["K"][i]["orig_m_lo"]) is not None
              and fn(fc["K"][i]["orig_m_lo"]) > 0.20]
    sel = list(costly[:25])
    seeded = [i for i in cand if suite[i]["episode"]["frozen_seed"] and i not in sel]
    sel += seeded[: max(0, 35 - len(sel))]
    rest = [i for i in cand if i not in sel]
    rng = random.Random(20261111)
    sel += rng.sample(rest, 50 - len(sel))
    check.true("V0", "50 direct items selected", len(sel) == 50 and len(set(sel)) == 50, len(sel))
    sc = SiteCache(I)
    n_cmp = Counter()
    direct_rows = []
    for iid_ in sel:
        it = suite[iid_]
        st = items_dt[iid_]
        inst_id = it["instance"]["instance_id"]
        c = I.get(inst_id)
        seed = list(it["episode"]["frozen_seed"] or [])
        traj = I.traj(inst_id, seed)
        starts = {a["wo"]: float(a["start_bh"]) for a in traj["assignments"]}
        iss = D.issuability(it, c["by_id"], starts)
        t_d = D.decision_instant_of(iss, "primary")
        check.true("V1", "t_d equals the census", t_d == float(st["t_d"]), (iid_, t_d, st["t_d"]))
        check.true("V1", "issuable equals the census", iss["issuable"] == st["issuable"], iid_)
        site = sc.get(inst_id, seed, t_d)
        raw = json.dumps({"operations": D.canonical_ops(it)})
        rec = site.replay(raw)
        u = unit_record(site, L, raw)
        K = rec["K"]
        # K reading against results/n11_decision_time/items.jsonl (bitwise: same code)
        for k in ("term_cert", "stage_cert", "term_feas", "stage_feas", "codes", "obj",
                  "obj_orig", "lb", "lb_running", "gap", "ref2", "ref2_from", "constraining",
                  "n_raised", "parse_ok", "infra"):
            check.true("V2", "dt_{} equal".format(k), K[k] == st["dt_" + k], (iid_, K[k],
                                                                                st["dt_" + k]))
            n_cmp["K"] += 1
        for k in ("obj", "obj_orig", "lb", "gap", "lb_running"):
            check.true("V2", "an_{} equal".format(k), site.an[k] == st["an_" + k], iid_)
            n_cmp["anchor"] += 1
        check.true("V2", "rw0 equal", site.rw0["obj"] == st["rw0_obj"]
                   and site.rw0["obj_orig"] == st["rw0_obj_orig"], iid_)
        rw = rec["rw"]
        if K["term_feas"] == "applied_uncertified":
            check.true("V2", "a proposal that passes stage 2 on K has a realised run (both)",
                       rw is not None and st["rw_obj"] is not None, iid_)
        if rw is not None and st["rw_obj"] is not None:
            check.true("V2", "rw_obj / rw_obj_orig / rw_term equal",
                       rw["obj"] == st["rw_obj"] and rw["obj_orig"] == st["rw_obj_orig"]
                       and rw["term_cert"] == st["rw_term"], (iid_, rw, st["rw_obj_orig"]))
            n_cmp["realised"] += 1
        check.true("V2", "anchor equals pub_anchor_wwt", u["anchor_wwt"] == st["pub_anchor_wwt"],
                   iid_)
        # prices, flags and truth against analysis/N11_rows_forecast.csv (six decimals)
        if K["stage_cert"] == "qual":
            fk_ = fc["K"].get(iid_)
            ff_ = fc["FI"].get(iid_)
            check.true("V3", "priced item is in the forecast rows", fk_ is not None
                       and ff_ is not None, iid_)
            for g in DESIGNS:
                check.true("V3", "K price {}".format(g), close(u["pK_" + g], fn(fk_["p_" + g]),
                                                                6e-7), (iid_, g, u["pK_" + g],
                                                                        fk_["p_" + g]))
                check.true("V3", "K flag {}".format(g),
                           u["refK_" + g] == (fk_["refers_" + g] == "True"), (iid_, g))
                check.true("V3", "FI price {}".format(g), close(u["pFI_" + g], fn(ff_["p_" + g]),
                                                                 6e-7), (iid_, g))
                check.true("V3", "FI flag {}".format(g),
                           u["refFI_" + g] == (ff_["refers_" + g] == "True"), (iid_, g))
                check.true("V3", "FI price = fullinfo_direct.jsonl {}".format(g),
                           u["pFI_" + g] == fi_rows[iid_]["prices"][g], (iid_, g))
                n_cmp["prices"] += 4
            for k in ("term_cert", "stage_cert", "obj", "obj_orig", "lb", "gap", "ref2"):
                check.true("V3", "FI {} = fullinfo_direct.jsonl".format(k),
                           rec["FI"][k] == fi_rows[iid_]["p"][k], (iid_, k))
            check.true("V3", "realised cost lo", close(u["cost_lo"], fn(fk_["orig_m_lo"]), 6e-7),
                       (iid_, u["cost_lo"], fk_["orig_m_lo"]))
            check.true("V3", "realised cost hi", close(u["cost_hi"], fn(fk_["orig_m_hi"]), 6e-7),
                       (iid_, u["cost_hi"], fk_["orig_m_hi"]))
            g_pub = (st["dt_obj_orig"] - st["an_lb"]) / max(st["an_lb"], FLOOR_BH)
            check.true("V3", "second price = n16 build_recs", u["g_orig"] == g_pub, iid_)
            check.true("V3", "edit type = the census split", u["split"] == st["split"],
                       (iid_, u["split"], st["split"]))
            n_cmp["truth"] += 2
        direct_rows.append({"item_id": iid_, "class": u["class"], "split": u["split"],
                            "cost20": u["costTwenty"], "refK_cert": u["refK_G-CERT"],
                            "sp": u["sp"]})
    # ---- 50 logged Claude rows (raw text) against results/n11_e2e
    sites_pub = {(s["iid"], s["fk"], float(s["t_d"])): s
                 for s in read_jsonl(RESULTS / "n11_e2e" / "sites.jsonl")}
    raw_by = {}
    for src, (d, _arm) in VERIFY_SOURCES.items():
        for r in read_jsonl(RESULTS / d / "proposals_raw.dedup.jsonl"):
            if r["mode"] == MODE:
                raw_by[(src, r["item_id"], r.get("thinking"), int(r["repeat"]))] = r
    pool = []
    for r in read_jsonl(RESULTS / "n11_e2e" / "rows_e1_primary.jsonl"):
        if (r["src"] in VERIFY_SOURCES and r["mode"] == MODE and r["instance_id"] in eight
                and not r.get("model_refused") and int(r["repeat"]) == 0):
            pool.append(r)
    pool.sort(key=lambda r: (r["src"], r["item_id"], str(r["thinking"])))
    rng2 = random.Random(20261112)
    llm = rng2.sample(pool, 50)
    for r in llm:
        it = suite[r["item_id"]]
        seed = list(it["episode"]["frozen_seed"] or [])
        check.true("V4", "frozen key", frozen_key(seed) == (r["frozen_seed"] or ""), r["item_id"])
        lr = raw_by[(r["src"], r["item_id"], r["thinking"], 0)]
        raw = lr.get("raw_output") or ""
        site = sc.get(r["instance_id"], seed, float(r["t_d"]))
        rec = site.replay(raw)
        K = rec["K"]
        for k in ("term_cert", "stage_cert", "term_feas", "stage_feas", "codes", "obj",
                  "obj_orig", "lb", "lb_running", "gap", "ref2", "ref2_from", "n_raised",
                  "parse_ok", "infra"):
            check.true("V4", "LLM row {}".format(k), K[k] == r[k],
                       (r["src"], r["item_id"], r["thinking"], k, K[k], r[k]))
            n_cmp["llm"] += 1
        check.true("V4", "LLM row dangling flag", ("dangling_order_id" in (K["codes"] or []))
                   == bool(r["dangling"]), r["item_id"])
        check.true("V4", "LLM row names_unknown", rec["names_unknown"] == r["names_unknown"],
                   (r["item_id"], rec["names_unknown"], r["names_unknown"]))
        if r.get("rw_obj_orig") is not None:
            check.true("V4", "LLM row realised run", rec["rw"] is not None
                       and rec["rw"]["obj_orig"] == r["rw_obj_orig"]
                       and rec["rw"]["obj"] == r["rw_obj"], r["item_id"])
            n_cmp["llm_realised"] += 1
        sp = sites_pub[(r["instance_id"], r["frozen_seed"] or "", float(r["t_d"]))]
        check.true("V4", "site anchor = sites.jsonl",
                   site.an["obj"] == sp["an_obj"] and site.an["lb"] == sp["an_lb"]
                   and site.an["gap"] == sp["an_gap"] and site.rw0["obj_orig"] == sp["rw0_obj_orig"]
                   and len(site.known["work_orders"]) == sp["n_known"], r["item_id"])
    check.true("V5", "the replay code is unchanged since this verification (hash recorded)", True)
    rep = OrderedDict(
        version=VERSION, date=now_iso(), status="PASS" if not check.failures else "FAIL",
        direct_items=sel, direct_costly_selected=len(costly[:25]),
        direct_classes=dict(Counter(r["class"] for r in direct_rows)),
        direct_costly_at_020=sum(1 for r in direct_rows if r["cost20"] == 1),
        llm_rows=[[r["src"], r["item_id"], r["thinking"], r["repeat"]] for r in llm],
        llm_classes=dict(Counter(r["term_cert"] for r in llm)),
        compared=dict(n_cmp), frozen_hashes=frozen, code_hashes=replay_code_hashes(),
        checks=check.summary())
    write_json(VERIFY_REPORT, rep)
    if check.failures:
        check.stop("verify")
    print("[n21] verify PASS: {} checks; direct classes {}, {} costly at 0.20; LLM rows {}; "
          "compared {}".format(sum(check.n.values()), rep["direct_classes"],
                               rep["direct_costly_at_020"], rep["llm_classes"], dict(n_cmp)))
    return 0


# --------------------------------------------------------------------------- #
# Provenance of the returned files (plain observations)                        #
# --------------------------------------------------------------------------- #
SENT_WORKBOOK = (ROOT / "participant_files" / "data_collection_pack" / "1_Field_Instructions" /
                 "Field_Instruction_Workbook.xlsx")
PROVENANCE = OUT / "workbook_provenance.json"
_ZIP_READER = r'''
import json, re, sys, zipfile
out = {}
def tag(xml, name):
    m = re.search(r"<(?:\w+:)?" + name + r"\b[^>]*>(.*?)</(?:\w+:)?" + name + ">", xml, re.S)
    return None if m is None else m.group(1)
for p in sys.argv[1:]:
    z = zipfile.ZipFile(p)
    ents = []
    for i in z.infolist():
        ents.append({"name": i.filename, "date_time": "%04d-%02d-%02d %02d:%02d:%02d" % i.date_time,
                     "file_size": i.file_size, "compress_size": i.compress_size,
                     "compress_type": i.compress_type, "create_system": i.create_system,
                     "create_version": i.create_version, "extract_version": i.extract_version,
                     "flag_bits": i.flag_bits, "external_attr": i.external_attr,
                     "crc": "%08x" % i.CRC})
    core = z.read("docProps/core.xml").decode("utf-8", "replace") if "docProps/core.xml" in z.namelist() else ""
    app = z.read("docProps/app.xml").decode("utf-8", "replace") if "docProps/app.xml" in z.namelist() else ""
    wbx = z.read("xl/workbook.xml").decode("utf-8", "replace")
    sheets = []
    for t in re.findall(r"<(?:\w+:)?sheet\b[^>]*>", wbx):
        nm = re.search(r'name="([^"]+)"', t)
        stt = re.search(r'state="(\w+)"', t)
        sheets.append([nm.group(1) if nm else None, stt.group(1) if stt else "visible"])
    root = re.search(r"<(\w+:)?workbook\b", wbx)
    rels = z.read("xl/_rels/workbook.xml.rels").decode("utf-8", "replace")
    rid = re.findall(r'Id="([^"]+)"', rels)
    writer = {"workbook_root_prefix": (root.group(1) if root and root.group(1) else ""),
              "relationship_ids": rid[:3], "n_relationships": len(rid),
              "shared_strings": "xl/sharedStrings.xml" in z.namelist()}
    dv = {}
    for n in z.namelist():
        if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"):
            x = z.read(n).decode("utf-8", "replace")
            dv[n] = {"dataValidations": len(re.findall(r"<dataValidation ", x)),
                     "bytes": len(x)}
    out[p] = {"entries": ents,
              "core": {k: tag(core, k) for k in ("creator", "lastModifiedBy", "created", "modified",
                                                  "title", "description", "revision")},
              "app": {k: tag(app, k) for k in ("Application", "AppVersion", "Company", "DocSecurity",
                                                "TotalTime")},
              "sheets": sheets, "worksheets": dv, "comment": z.comment.decode("latin-1"),
              "writer": writer}
sys.stdout.write(json.dumps(out))
'''


def cmd_provenance(args) -> int:
    paths = [SENT_WORKBOOK] + [PACK / "Field_Instruction_Workbook_{}.xlsx".format(p)
                               for p in EXPECTED_ROWS]
    before = {p.name: sha256_file(p) for p in paths}
    py = FJSP_PYTHON if Path(FJSP_PYTHON).is_file() else sys.executable
    res = subprocess.run([py, "-I", "-c", _ZIP_READER] + [str(p) for p in paths],
                         capture_output=True, text=True, cwd=str(OUT), timeout=300,
                         env={"PATH": "/usr/bin:/bin"})
    if res.returncode != 0:
        raise SystemExit("zip reader failed: " + res.stderr[-2000:])
    data = json.loads(res.stdout)
    after = {p.name: sha256_file(p) for p in paths}
    if before != after:
        raise SystemExit("a workbook changed during the read")
    sent = data[str(SENT_WORKBOOK)]
    sent_names = [e["name"] for e in sent["entries"]]
    out = OrderedDict(version=VERSION, date=now_iso(), sha256=before,
                      sent={"file": str(SENT_WORKBOOK.relative_to(ROOT)), "core": sent["core"],
                            "app": sent["app"], "sheets": sent["sheets"],
                            "entries": [(e["name"], e["date_time"], e["file_size"])
                                        for e in sent["entries"]]},
                      returned=OrderedDict())
    for p in paths[1:]:
        d = data[str(p)]
        names = [e["name"] for e in d["entries"]]
        sizes = {e["name"]: e["file_size"] for e in d["entries"]}
        ssizes = {e["name"]: e["file_size"] for e in sent["entries"]}
        crc = {e["name"]: e["crc"] for e in d["entries"]}
        scrc = {e["name"]: e["crc"] for e in sent["entries"]}
        out["returned"][p.name] = OrderedDict(
            file_mtime=time.strftime("%Y-%m-%d %H:%M:%S %z", time.localtime(p.stat().st_mtime)),
            bytes=p.stat().st_size, core=d["core"], app=d["app"], sheets=d["sheets"],
            entry_dates=sorted(Counter(e["date_time"] for e in d["entries"]).items()),
            entry_names_equal_sent=names == sent_names,
            entries_only_returned=[n for n in names if n not in sent_names],
            entries_only_sent=[n for n in sent_names if n not in names],
            entries_same_bytes_as_sent=sorted(n for n in names if n in scrc and crc[n] == scrc[n]),
            entries_changed=sorted((n, ssizes.get(n), sizes[n]) for n in names
                                   if n in scrc and crc[n] != scrc[n]),
            sheets_equal_sent=d["sheets"] == sent["sheets"], writer=d["writer"],
            crc_equal_across_returned=None,
            data_validations={k: v["dataValidations"] for k, v in d["worksheets"].items()},
            data_validations_sent={k: v["dataValidations"] for k, v in sent["worksheets"].items()},
            zip_meta=sorted(Counter((e["create_system"], e["create_version"],
                                     e["extract_version"], e["flag_bits"], e["compress_type"])
                                    for e in d["entries"]).items()),
            zip_comment=d["comment"])
    out["sent"]["writer"] = sent["writer"]
    crcs = defaultdict(set)
    for p in paths[1:]:
        for e in data[str(p)]["entries"]:
            crcs[e["name"]].add(e["crc"])
    out["entries_identical_in_all_eight_returned"] = sorted(n for n, v in crcs.items()
                                                            if len(v) == 1)
    out["entries_differing_across_returned"] = sorted(n for n, v in crcs.items() if len(v) > 1)
    for p in paths[1:]:
        out["returned"][p.name].pop("crc_equal_across_returned")
    out["sent"]["zip_meta"] = sorted(Counter((e["create_system"], e["create_version"],
                                              e["extract_version"], e["flag_bits"],
                                              e["compress_type"])
                                             for e in sent["entries"]).items())
    write_json(PROVENANCE, out)
    print("[n21] provenance written: {}".format(PROVENANCE))
    return 0


# --------------------------------------------------------------------------- #
# Step 4: generation (hosted arms through grid_e1_hosted; local arms on the GPU) #
# --------------------------------------------------------------------------- #
_BACKOFF = {"lock": threading.Lock(), "retries": Counter(), "slept_s": 0.0}
#: Set when an answered call reports a model identifier other than the pinned one: no further
#: request leaves this process, and the run exits non-zero after writing what it has.
_STOP = threading.Event()
_MISMATCH = []


class StopRun(RuntimeError):
    pass


def backoff_transport(method, url, headers, body, timeout):
    """models.urllib_transport with exponential backoff on 429 / 529 / 5xx and on connection
    errors (2, 4, 8, 16, 32, 60 s, jittered by up to 25%); the client's own retries stay
    on top.  The request is not changed.  After a model-identifier mismatch nothing is sent."""
    from l1guard.models import urllib_transport
    for k in range(len(BACKOFF_S) + 1):
        if _STOP.is_set():
            raise StopRun("n21: stopped after a model-identifier mismatch; request not sent")
        try:
            status, raw = urllib_transport(method, url, headers, body, timeout)
        except ConnectionError:
            if k == len(BACKOFF_S):
                raise
            status, raw = "conn", None
        if (status == "conn" or status in RETRY_STATUS) and k < len(BACKOFF_S):
            d = BACKOFF_S[k] * (1.0 + 0.25 * random.random())
            with _BACKOFF["lock"]:
                _BACKOFF["retries"][str(status)] += 1
                _BACKOFF["slept_s"] += d
            time.sleep(d)
            continue
        return status, raw
    return status, raw


def load_prompt_rows(check) -> list:
    meta = json.loads(PROMPTS_META.read_text())
    check.true("FILE", "prompt file hash as recorded by the dry run",
               sha256_file(PROMPTS_JSONL) == meta["prompts_sha256"])
    check.true("FILE", "dry run recorded the leak check as PASS", meta["leak_status"] == "PASS")
    rows = read_jsonl(PROMPTS_JSONL)
    check.true("FILE", "item set as recorded",
               sha_text("\n".join(sorted(r["item_id"] for r in rows))) == meta["item_set_sha256"])
    # the leak check, again, from the file
    items = {r["item_id"]: r for r in read_jsonl(ITEMS_JSONL)}
    P = sg.load_prompts_module()
    I = Instances()
    for r in rows:
        rec = items[r["item_id"]]
        c = I.get(r["instance_id"])
        traj = I.traj(r["instance_id"], rec["frozen_seed"])
        state = I.n8.site_state(c["inst"], traj, float(r["t_d"]), pm_known=True)
        lk = GK.leak_of(r["messages"], r["item"]["instruction"], set(state["unknown"]))
        check.true("LEAK", "re-check from the file", not lk["board"], r["item_id"])
        check.true("FILE", "prompt hash recomputes", P.prompt_fingerprint(r["messages"])
                   == r["prompt_hash"], r["item_id"])
        check.true("FILE", "no respondent field in the item sent", not any(
            k in r["item"] for k in ("respondent", "role", "expected_action", "why")), r["item_id"])
    return rows


def spend_note(text):
    with open(SPEND_LOG, "a", encoding="utf-8") as fh:
        fh.write(text.rstrip() + "\n")


def cmd_hosted(args) -> int:
    arm_key = args.arm
    if arm_key not in HOSTED_ARMS:
        raise SystemExit("--arm must be one of {}".format(list(HOSTED_ARMS)))
    if not args.i_have_approval_to_spend:
        print("REFUSING TO RUN: --hosted {} calls a paid API. Re-run with "
              "--i-have-approval-to-spend once the spend is approved.".format(arm_key))
        return 2
    meta = json.loads(PROMPTS_META.read_text())
    if arm_key == "openai" and not meta["gpt_cost_rule"]["run"]:
        print("REFUSING TO RUN: the GPT-5.4-mini cost rule fails ({})".format(meta["gpt_cost_rule"]))
        return 2
    import grid_e1_hosted as H
    from l1guard.models import BACKENDS, M_CONSTRAINED, ChatClient

    check = Check()
    inputs = sg.assert_inputs()
    rows = load_prompt_rows(check)
    check.stop("prompt file")
    arm = dataclasses.replace(H.ARMS[arm_key], modes=(M_CONSTRAINED,),
                              prices=(current_price(H.ARMS[arm_key]),))
    backend = BACKENDS[arm.backend]
    items = {r["item_id"]: r for r in read_jsonl(ITEMS_JSONL)}
    I = Instances()
    prepared = []
    for pr in rows:
        msgs = pr["messages"]
        prefix, tail, which = H.split_user_prompt(msgs[1]["content"])
        if prefix + tail != msgs[1]["content"]:
            raise SystemExit("REFUSING TO RUN: split not byte-identical for " + pr["item_id"])
        fp = H.PROMPTS.prompt_fingerprint([msgs[0], {"role": "user", "content": prefix + tail}])
        if fp != pr["prompt_hash"]:
            raise SystemExit("REFUSING TO RUN: split fingerprint differs for " + pr["item_id"])
        if msgs[0]["content"] != H.SYSTEM_PROMPT:
            raise SystemExit("REFUSING TO RUN: system prompt differs from the frozen one")
        item = pr["item"]
        path = str(I.get(pr["instance_id"])["path"])
        p = H.Prepared(item=item, instance_path=path,
                       group=(path, tuple(item["episode"]["frozen_seed"]), pr["t_d"]),
                       prefix=prefix, tail=tail, prompt_hash=pr["prompt_hash"], split_at=which)
        p.known = pr
        prepared.append(p)
    prepared.sort(key=lambda p: (p.group, p.item["item_id"]))
    out_dir = OUT / arm_key
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp_file = out_dir / "prompts_sha256.txt"
    if stamp_file.exists() and stamp_file.read_text().strip() != meta["prompts_sha256"]:
        raise SystemExit("REFUSING TO RUN: {} was written from another prompt file".format(out_dir))
    stamp_file.write_text(meta["prompts_sha256"] + "\n")
    log_path = out_dir / "proposals_raw.jsonl"
    H.PROMPT_VERSION = KNOWN_VERSION
    orig_make_row = H.make_row

    def make_row_field(arm_, call, resp, latency_ms, backend_):
        row = orig_make_row(arm_, call, resp, latency_ms, backend_)
        pr = call["prep"].known
        row.update(prompt_variant=PROMPT_VARIANT, t_d=pr["t_d"], n_known=pr["n_known"],
                   n_running=pr["n_running"], known_frozen=pr["known_frozen"],
                   prompt_chars=pr["prompt_chars"], item_set="field_v1", runner=VERSION)
        # every answered call: the endpoint's model identifier must be the pinned one
        if row["outcome"] != "error" and row.get("model_reported") != arm_.model:
            _MISMATCH.append((row["item_id"], row["thinking"], row.get("model_reported")))
            _STOP.set()
        return row
    H.make_row = make_row_field
    done, nrows, errors, broken = H.read_completed(log_path, arm)
    plan = [c for c in H.build_plan(arm, prepared, 1, 0)
            if H.row_key(c["mode"], c["thinking"], c["repeat"], c["prep"].item["item_id"])
            not in done]
    if args.limit:
        plan = plan[: args.limit]
    vol = meta["hosted_volumes"][arm_key]
    note = ("{} hosted {} ({}): {} prompts x {} configuration(s) {}; planned now {} calls ({} "
            "keys already logged); estimated input tokens per configuration {} (median {}, "
            "max {} per prompt; chars/{} + {} schema tokens), USD estimate without cache {}; "
            "workers {}; prompt file sha256 {}".format(
                now_iso(), arm_key, arm.model, vol["prompts"], len(arm.thinking),
                [str(l) for l, _ in arm.thinking], len(plan), len(done),
                vol["in_tokens_est_per_config"], vol["in_tokens_est_median"],
                vol["in_tokens_est_max"], vol["chars_per_token"], vol["schema_tokens"],
                vol["usd_est_no_cache"], MAX_IN_FLIGHT, meta["prompts_sha256"]))
    print("[n21-h] " + note, flush=True)
    spend_note("- " + note)
    if not plan:
        print("[n21-h] nothing to do")
        return 0
    H.load_env()
    if not os.environ.get(backend.api_key_env):
        print("REFUSING TO RUN: {} is not set".format(backend.api_key_env))
        return 2
    client = ChatClient(arm.backend, model=arm.model, api_key=None, max_tokens=H.MAX_TOKENS,
                        timeout_s=240.0, max_retries=4, retry_sleep_s=2.0,
                        transport=backoff_transport)
    ns = argparse.Namespace(max_tokens=H.MAX_TOKENS, workers=MAX_IN_FLIGHT)
    result = H.run(arm, ns, plan, log_path, client)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    usd = sum(c["usd"] for c in result["tally"].values())
    rm = OrderedDict(
        runner=VERSION, date=now_iso(), arm=arm.arm, model=arm.model, backend=arm.backend,
        wire=backend.wire, modes=[MODE], thinking=[l for l, _ in arm.thinking],
        thinking_bodies={str(l): b for l, b in arm.thinking}, repeats=1, items=len(prepared),
        max_tokens=H.MAX_TOKENS, workers=MAX_IN_FLIGHT, timeout_s=240.0, max_retries=4,
        backoff_s=list(BACKOFF_S), backoff_retries=dict(_BACKOFF["retries"]),
        backoff_slept_s=_BACKOFF["slept_s"], suite_sha256=inputs["suite_sha256"],
        schema_sha256=inputs["schema_sha256"], prompt_version=KNOWN_VERSION,
        prompts_sha256=meta["prompts_sha256"], top_k=TOP_K, cache_boundary=H.CACHE_BOUNDARY,
        price_base=arm.prices[0][0], prices=arm.prices[0][1], planned_calls=len(plan),
        rows_written=result["written"], wall_s=result["wall_s"],
        interrupted=result["interrupted"], usd_estimated=usd,
        per_config={"{}|{}|r{}".format(m, t, r): v for (m, t, r), v in result["tally"].items()})
    write_json(out_dir / "run_meta_{}.json".format(stamp), rm)
    spend_note("- {} hosted {} done: {} rows, USD {:.4f} at the {} base; backoff {}".format(
        now_iso(), arm_key, result["written"], usd, arm.prices[0][0], dict(_BACKOFF["retries"])))
    print("[n21-h] raw log {}; estimated spend USD {:.4f}".format(log_path, usd))
    if _MISMATCH:
        spend_note("- {} hosted {} STOPPED: model identifier mismatch {}".format(
            now_iso(), arm_key, _MISMATCH[:5]))
        print("ASSERTION FAILURE: the endpoint reported another model identifier than {} on "
              "{} answered call(s), first {}; no further request was sent".format(
                  arm.model, len(_MISMATCH), _MISMATCH[:5]), file=sys.stderr)
        return 3
    return 130 if result["interrupted"] else 0


def cmd_local(args) -> int:
    """Local arm generation (GPU, env l1).  NOT run by this analysis: the GPU belongs to the L2
    project until it is released.  Settings are the published ones of the arm (grid_e1_known
    LOCAL_ARMS: temperature 0, seed 0, xgrammar, max_tokens 1024, max_model_len), constrained
    mode, one repeat.  Never re-generates an item already in the log."""
    arm = args.arm
    if arm not in GK.LOCAL_ARMS:
        raise SystemExit("--arm must be one of {}".format(list(GK.LOCAL_ARMS)))
    spec = GK.LOCAL_ARMS[arm]
    check = Check()
    inputs = sg.assert_inputs()
    rows = load_prompt_rows(check)
    check.stop("prompt file")
    meta = json.loads(PROMPTS_META.read_text())
    out_dir = OUT / spec["short"]
    raw_path = out_dir / "proposals_raw.jsonl"
    done = set()
    if raw_path.exists():
        for r in read_jsonl(raw_path):
            if r.get("prompt_version") != KNOWN_VERSION or r.get("arm") != arm:
                raise SystemExit("REFUSING TO RUN: {} holds foreign rows".format(raw_path))
            done.add(r["item_id"])
    todo = [r for r in rows if r["item_id"] not in done]
    if args.limit:
        todo = todo[: args.limit]
    if not todo:
        print("[n21-l] nothing to do")
        return 0
    if not Path(spec["model_snapshot"]).is_dir():
        raise SystemExit("REFUSING TO RUN: pinned snapshot missing: {} (download {} at revision "
                         "{} first)".format(spec["model_snapshot"], spec["repo"], spec["revision"]))
    snap = GK.verify_snapshot(spec)
    if not snap["ok"]:
        raise SystemExit("REFUSING TO RUN: the snapshot does not match {}".format(spec["checksums"]))
    gpu = GK.gpu_check_live()
    if not gpu["ok"]:
        raise SystemExit("REFUSING TO RUN: the card is not free: {}".format("; ".join(
            gpu["reasons"])))
    out_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    import vllm
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import StructuredOutputsParams
    import grid_e1_local as Lc
    with open(sg.SCHEMA_PATH, "r", encoding="utf-8") as fh:
        schema = json.load(fh)
    kw = dict(model=spec["model_snapshot"], max_model_len=spec["max_model_len"],
              gpu_memory_utilization=spec["gpu_memory_utilization"], seed=0,
              trust_remote_code=False, structured_outputs_config={"backend": "xgrammar"})
    if spec["max_num_seqs"]:
        kw["max_num_seqs"] = spec["max_num_seqs"]
    llm = LLM(**kw)
    tok = llm.get_tokenizer()
    texts_in = []
    for r in todo:
        try:
            t = tok.apply_chat_template(r["messages"], tokenize=False, add_generation_prompt=True,
                                        enable_thinking=False)
        except TypeError:  # pragma: no cover
            t = tok.apply_chat_template(r["messages"], tokenize=False, add_generation_prompt=True)
        texts_in.append(t)
    over = [r["item_id"] for r, t in zip(todo, texts_in)
            if len(tok(t).input_ids) >= spec["max_model_len"]]
    if over:
        raise SystemExit("REFUSING TO RUN: prompts exceed max_model_len: {}".format(over[:10]))
    ns = argparse.Namespace(max_tokens=spec["max_tokens"])
    texts, usages, finish, wall = Lc.generate_mode(llm, SamplingParams, StructuredOutputsParams,
                                                   schema, texts_in, MODE, ns)
    with open(raw_path, "a", encoding="utf-8") as fh:
        for r, text, usage, fin in zip(todo, texts, usages, finish):
            row = {"item_id": r["item_id"], "instance_id": r["instance_id"],
                   "stratum": r["stratum"], "frozen_seed": r["frozen_seed"],
                   "instruction": r["item"]["instruction"], "prompt_hash": r["prompt_hash"],
                   "prompt_version": KNOWN_VERSION, "prompt_variant": PROMPT_VARIANT,
                   "t_d": r["t_d"], "n_known": r["n_known"], "known_frozen": r["known_frozen"],
                   "model": spec["model_snapshot"], "arm": arm, "thinking": None, "mode": MODE,
                   "repeat": 0, "backend": "xgrammar", "raw_output": text, "finish_reason": fin,
                   "usage": usage, "outcome": "ok", "item_set": "field_v1", "runner": VERSION}
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    write_json(out_dir / "run_meta_{}.json".format(time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())),
               {"runner": VERSION, "arm": arm, "spec": spec, "items": len(todo), "wall_s": wall,
                "vllm_version": vllm.__version__, "gpu_at_launch": gpu["samples"],
                "snapshot_check": snap, "prompts_sha256": meta["prompts_sha256"],
                "suite_sha256": inputs["suite_sha256"]})
    print("[n21-l] {} rows appended to {}".format(len(todo), raw_path))
    return 0


# --------------------------------------------------------------------------- #
# Table e and the text-level regularities (model-free)                         #
# --------------------------------------------------------------------------- #
REGULARITIES = OUT / "text_regularities.json"
TABLE_E = OUT / "table_e.json"
PAIRS = (("P1", "P5"), ("P2", "P6"), ("P3", "P7"), ("P4", "P8"))
_NUMW = OrderedDict([("one", 1), ("two", 2), ("three", 3), ("four", 4), ("five", 5),
                     ("six", 6), ("seven", 7), ("eight", 8), ("nine", 9), ("ten", 10),
                     ("twelve", 12), ("sixteen", 16), ("twenty", 20), ("forty", 40)])
_HOURS_RE = re.compile(r"\b(?:up to |a |by )?(\d+(?:\.\d+)?|" + "|".join(_NUMW) +
                       r")[- ](?:(working)[- ])?(hours?|hour|days?)\b", re.I)


def quart(vals):
    """Median and quartiles by the suite's rule (statistics.quantiles, method 'inclusive')."""
    v = sorted(vals)
    if not v:
        return {"n": 0}
    q = statistics.quantiles(v, n=4, method="inclusive") if len(v) > 1 else [v[0]] * 3
    return OrderedDict(n=len(v), min=v[0], q1=q[0], median=q[1], q3=q[2], max=v[-1],
                       mean=sum(v) / len(v))


def id_tokens_shape(text, shape):
    """Distinct id-shaped tokens of a text (C3's token rule without the on-instance test)."""
    out = []
    for t in TOKEN_RE.findall(text or ""):
        if ID_RE[shape].match(t) and t not in out:
            out.append(t)
    return out


def text_frame(text):
    """A text with ids, building codes, trade codes and numbers replaced by placeholders."""
    t = re.sub(r"\bW\d+\b|\b\d{8}\b", "<ID>", text)
    t = re.sub(r"\b0\d{3}\b|\bCAMPUS\b", "<BLDG>", t)
    t = re.sub(r"\b[A-E]\d0\b|\bMISC\b", "<TRADE>", t)
    t = re.sub(r"\b\d+(?:\.\d+)?\b", "<N>", t)
    t = re.sub(r"\b(" + "|".join(_NUMW) + r")\b", "<N>", t, flags=re.I)
    return t


def hours_in_text(text):
    """Hours of delay the text states (a working day = 8 h), or None."""
    vals = []
    for m in _HOURS_RE.finditer(text or ""):
        n = m.group(1).lower()
        n = float(_NUMW[n]) if n in _NUMW else float(n)
        vals.append(n * 8.0 if m.group(3).lower().startswith("day") else n)
    return vals


def describe_data():
    """Table e (field set beside the generated suite) and the text regularities."""
    instr = read_instructions()
    items = {r["item_id"]: r for r in read_jsonl(ITEMS_JSONL)}
    resp = read_csv_comments(RESP_CSV)
    cards, _man = card_manifest()
    suite = sg.load_suite()
    words_f = [len(r["text"].split()) for r in instr]
    named_f = [len(items[r["item_id"]]["ids_named"]) for r in instr]
    shape_f = [len(id_tokens_shape(r["text"], id_shape(r["instance_id"]))) for r in instr]
    e = OrderedDict()
    e["field"] = OrderedDict(
        instructions=len(instr), respondents=len(resp), cards=len(cards),
        words=quart(words_f), share_naming_id=sum(1 for n in named_f if n) / len(instr),
        n_naming_id=sum(1 for n in named_f if n), orders_named=quart(named_f),
        orders_named_counts=dict(sorted(Counter(named_f).items())),
        n_naming_id_by_shape=sum(1 for n in shape_f if n),
        situations=OrderedDict((s, sum(1 for r in instr if r["situation"] == s))
                               for s in SITUATIONS),
        expected_actions=OrderedDict((a, sum(1 for r in instr if r["expected_action"] == a))
                                     for a in ACTION_CHOICES),
        delay_answers=OrderedDict((a, sum(1 for r in instr if r["delay_answer"] == a))
                                  for a in DELAY_CHOICES),
        hours_given=quart([r["hours"] for r in instr if r["hours"] is not None]),
        issuable=sum(1 for r in items.values() if r["issuable"]))
    yrs = sorted(float(r["years"]) for r in resp)
    e["respondents"] = OrderedDict(
        years=OrderedDict(min=yrs[0], median=statistics.median(yrs), max=yrs[-1]),
        approval_frequency=dict(Counter(r["approval_frequency"] for r in resp)),
        cmms=dict(Counter(r["cmms"] for r in resp)))
    for label, sub in (("suite", suite),
                       ("suite_benign", [it for it in suite if it["primary_class"] == "benign"])):
        w = [len(it["instruction"].split()) for it in sub]
        nm = [len(id_tokens_shape(it["instruction"], id_shape(it["instance"]["instance_id"])))
              for it in sub]
        e[label] = OrderedDict(
            instructions=len(sub), words=quart(w),
            words_rule_equals_field=all(len(it["instruction"].split()) == it["instruction_words"]
                                        for it in sub),
            share_naming_id=sum(1 for n in nm if n) / len(sub), n_naming_id=sum(1 for n in nm if n),
            orders_named=quart(nm), orders_named_counts=dict(sorted(Counter(nm).items())),
            referenced_field_naming_id=sum(1 for it in sub if it["referenced"].get("order_ids")),
            classes=dict(Counter(it["primary_class"] for it in sub)))
    # ---- text regularities, per respondent and across respondents
    g = OrderedDict()
    by_p = defaultdict(list)
    for r in instr:
        by_p[r["respondent"]].append(r)
    per = OrderedDict()
    for p in EXPECTED_ROWS:
        rs = by_p[p]
        per[p] = OrderedDict(
            rows=len(rs), rows_per_card=dict(Counter(r["card"] for r in rs)),
            words=quart([len(r["text"].split()) for r in rs]),
            sentences=quart([len([s for s in re.split(r"(?<=[.?!])\s+", r["text"].strip()) if s])
                             for r in rs]),
            rows_naming_id=sum(1 for r in rs if items[r["item_id"]]["ids_named"]),
            rows_naming_two_or_more=sum(1 for r in rs if len(items[r["item_id"]]["ids_named"]) >= 2),
            rows_naming_trade_code=sum(1 for r in rs if items[r["item_id"]]["trades_named"]),
            rows_naming_building=sum(1 for r in rs if items[r["item_id"]]["buildings_named"]),
            expected_actions=dict(Counter(r["expected_action"] for r in rs)),
            delay_answers=dict(Counter(r["delay_answer"] for r in rs)),
            why_filled=sum(1 for r in rs if (r["why"] or "").strip()),
            first_words=dict(Counter(r["text"].split()[0].strip(",.").lower()
                                     for r in rs).most_common(5)),
            situation_sequence_by_card={c: "".join(r["situation"] for r in rs if r["card"] == c)
                                        for c in sorted({r["card"] for r in rs})})
    g["per_respondent"] = per
    seqs = [s for p in per.values() for s in p["situation_sequence_by_card"].values()]
    g["card_blocks"] = len(seqs)
    g["card_blocks_in_alphabetical_situation_order"] = sum(1 for s in seqs if list(s) == sorted(s))
    g["card_blocks_with_every_situation"] = sum(1 for s in seqs if set(s) == set(SITUATIONS))
    g["rows_per_card_block"] = quart([len(s) for s in seqs])
    g["situation_x_action"] = OrderedDict(
        (s, dict(Counter(r["expected_action"] for r in instr if r["situation"] == s)))
        for s in SITUATIONS)
    g["situation_x_delay"] = OrderedDict(
        (s, dict(Counter(r["delay_answer"] for r in instr if r["situation"] == s)))
        for s in SITUATIONS)
    g["why_filled_by_action"] = {a: sum(1 for r in instr if r["expected_action"] == a
                                        and (r["why"] or "").strip()) for a in ACTION_CHOICES}
    # hours: the delay rows' text against the hours column
    hrs = []
    for r in instr:
        if r["delay_answer"].startswith("yes, up to"):
            t = hours_in_text(r["text"])
            hrs.append({"item_id": r["item_id"], "hours": r["hours"], "text_hours": t,
                        "match": r["hours"] in t})
    g["delay_rows"] = len(hrs)
    g["delay_rows_text_states_the_hours_column"] = sum(1 for h in hrs if h["match"])
    g["delay_rows_mismatch"] = [h for h in hrs if not h["match"]]
    g["rows_stating_hours_without_delay_answer"] = [
        r["item_id"] for r in instr if not r["delay_answer"].startswith("yes, up to")
        and re.search(r"\b(?:accept|slip|delay)\b", r["text"], re.I) and hours_in_text(r["text"])]
    # repeated texts and sentence frames across respondents
    texts = Counter(r["text"].strip() for r in instr)
    g["identical_texts"] = sum(1 for v in texts.values() if v > 1)
    sent = defaultdict(set)
    for r in instr:
        for s in re.split(r"(?<=[.?!])\s+", r["text"].strip()):
            if s:
                sent[text_frame(s)].add(r["respondent"])
    shared = sorted(((len(v), f, sorted(v)) for f, v in sent.items() if len(v) >= 2),
                    key=lambda x: (-x[0], x[1]))
    g["sentence_frames"] = len(sent)
    g["sentence_frames_shared_by_two_or_more"] = [{"respondents": v, "frame": f}
                                                  for _n, f, v in shared]
    ng = defaultdict(set)
    ng_rows = defaultdict(set)
    for r in instr:
        w = re.findall(r"[a-z']+|<\w+>", text_frame(r["text"]).lower())
        for i in range(len(w) - 4):
            ng[tuple(w[i:i + 5])].add(r["respondent"])
            ng_rows[tuple(w[i:i + 5])].add(r["item_id"])
    top = sorted(((len(v), len(ng_rows[k]), " ".join(k)) for k, v in ng.items() if len(v) >= 4),
                 key=lambda x: (-x[0], -x[1], x[2]))
    g["five_grams_shared_by_four_or_more"] = [{"respondents": a, "rows": b, "five_gram": c}
                                              for a, b, c in top]
    g["five_grams_by_respondent_count"] = dict(sorted(Counter(len(v) for v in ng.values()).items()))
    frows = [r for r in instr if r["situation"] == "F"]
    g["delay_rows_containing"] = OrderedDict(
        (w, sum(1 for r in frows if re.search(r"\b" + w + r"\w*", r["text"], re.I)))
        for w in ("routine", "accept", "ahead of", "slip", "delay", "working hour", "working day"))
    g["delay_rows_sentences"] = dict(Counter(
        len([s for s in re.split(r"(?<=[.?!;])\s+", r["text"].strip()) if s]) for r in frows))
    g["rows_with_question_mark"] = dict(Counter(r["situation"] for r in instr if "?" in r["text"]))
    g["rows_with_please"] = sum(1 for r in instr if re.search(r"\bplease\b", r["text"], re.I))
    g["rows_opening_with_an_id"] = sum(1 for r in instr
                                       if re.match(r"(W\d+|\d{8})\b", r["text"].strip()))
    accept = [r for r in instr if re.search(r"\bI accept up to\b", r["text"])]
    g["rows_with_I_accept_up_to"] = OrderedDict(
        rows=len(accept), respondents=sorted({r["respondent"] for r in accept}),
        situations=dict(Counter(r["situation"] for r in accept)))
    # partners: the two respondents of each card
    part = []
    for a, b in PAIRS:
        for c in sorted({r["card"] for r in by_p[a]} & {r["card"] for r in by_p[b]}):
            ia = {o for r in by_p[a] if r["card"] == c for o in items[r["item_id"]]["ids_named"]}
            ib = {o for r in by_p[b] if r["card"] == c for o in items[r["item_id"]]["ids_named"]}
            fa = {text_frame(s) for r in by_p[a] if r["card"] == c
                  for s in re.split(r"(?<=[.?!])\s+", r["text"].strip()) if s}
            fb = {text_frame(s) for r in by_p[b] if r["card"] == c
                  for s in re.split(r"(?<=[.?!])\s+", r["text"].strip()) if s}
            part.append(OrderedDict(card=c, respondents=[a, b], ids_a=len(ia), ids_b=len(ib),
                                    ids_both=len(ia & ib), ids_union=len(ia | ib),
                                    card_orders_shown=len(cards[c]["order_ids"]),
                                    shared_sentence_frames=len(fa & fb)))
    g["card_partners"] = part
    # orders named per card against the 16 shown
    per_card = OrderedDict()
    for c in sorted(cards):
        rs = [r for r in instr if r["card"] == c]
        cnt = Counter(o for r in rs for o in items[r["item_id"]]["ids_named"])
        shown = set(cards[c]["order_ids"])
        per_card[c] = OrderedDict(rows=len(rs), distinct_ids_named=len(cnt),
                                  shown=len(shown), named_not_shown=sorted(set(cnt) - shown),
                                  in_progress_shown=list(cards[c]["frozen_set_shown"]),
                                  rows_naming_in_progress=sum(
                                      1 for r in rs if set(items[r["item_id"]]["ids_named"])
                                      & set(cards[c]["frozen_set_shown"])),
                                  most_named=cnt.most_common(3))
    g["per_card"] = per_card
    return e, g


def cmd_describe(args) -> int:
    e, g = describe_data()
    write_json(TABLE_E, OrderedDict(version=VERSION, date=now_iso(), table_e=e))
    write_json(REGULARITIES, OrderedDict(version=VERSION, date=now_iso(), regularities=g))
    f, s = e["field"], e["suite"]
    print("[n21] table e: field words median {} [{}, {}], naming an id {}/{}; suite words "
          "median {} [{}, {}], naming an id {}/{}".format(
              f["words"]["median"], f["words"]["q1"], f["words"]["q3"], f["n_naming_id"],
              f["instructions"], s["words"]["median"], s["words"]["q1"], s["words"]["q3"],
              s["n_naming_id"], s["instructions"]))
    print("[n21] regularities: {} card blocks, {} in alphabetical situation order; delay rows "
          "{}, text states the hours column on {}; identical texts {}; shared sentence frames "
          "{}".format(g["card_blocks"], g["card_blocks_in_alphabetical_situation_order"],
                      g["delay_rows"], g["delay_rows_text_states_the_hours_column"],
                      g["identical_texts"], len(g["sentence_frames_shared_by_two_or_more"])))
    return 0


# --------------------------------------------------------------------------- #
# Steps 5 to 8: the logged proposals through the gate; tables a to f; macros    #
# --------------------------------------------------------------------------- #
PASS_SCHEMA = ("feas", "infra_feas", "priced", "infra_qual", "other")
#: gate -> macro token; "+SP" = the gate with the second price (C13), "-site" its site variant
GATES = OrderedDict([("G-CERT", "Cert"), ("G-CERT+SP", "CertSP"), ("G-CERT+SP-site", "CertSPSite"),
                     ("G-CERT-M", "CertM"), ("D-REL1", "RelOne"), ("D-REL2", "RelTwo"),
                     ("D-ABS", "Abs")])
OUTCOMES = OrderedDict([("applied", "Applied"), ("referred", "Referred"),
                        ("refused_check", "Refused"), ("empty_or_model_refusal", "Empty"),
                        ("instrument_fault", "Fault"), ("no_response", "NoResponse"),
                        ("not_sent", "NotSent"), ("not_issuable", "NotIssuable")])
ACTION_TOK = OrderedDict([("apply it", "Apply"), ("ask me before applying", "Ask"),
                          ("refuse it", "Refuse")])
DELAY_TOK = OrderedDict([("no", "No"), ("yes, up to __ hours", "UpTo"), ("yes, any", "Any")])
D_GATES = ("G-CERT+SP", "G-CERT")


def read_jsonl_tolerant(path):
    rows, broken = [], 0
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                broken += 1          # a torn last line of a killed run
    return rows, broken


def arm_identity(d):
    """(arm, model) every row of directory d must carry: the pinned identifiers."""
    if d in HOSTED_ARMS:
        import grid_e1_hosted as H
        return d, H.ARMS[d].model
    arm = LOCAL_SHORT[d]
    return arm, GK.LOCAL_ARMS[arm]["model_snapshot"]


def read_cells(root, prompts, check):
    """cell -> {item_id: logged row} for every cell whose log exists under root."""
    cells, info = OrderedDict(), OrderedDict()
    for (d, think), (disp, tok) in CELLS.items():
        p = Path(root) / d / "proposals_raw.jsonl"
        if not p.exists():
            continue
        arm, model = arm_identity(d)
        rows, broken = read_jsonl_tolerant(p)
        got, n_err, n_rows = {}, 0, 0
        for r in rows:
            if r.get("thinking") != think:
                continue
            n_rows += 1
            iid = r.get("item_id")
            check.true("LOG", "row of the pinned arm and model", r.get("arm") == arm
                       and r.get("model") == model, (p, r.get("arm"), r.get("model")))
            if d in HOSTED_ARMS and r.get("outcome") != "error":
                check.true("LOG", "answered call: the endpoint's model identifier is the pinned one",
                           r.get("model_reported") == model, (p, iid, r.get("model_reported")))
            check.true("LOG", "known-board prompt version", r.get("prompt_version") == KNOWN_VERSION,
                       (p, iid))
            check.true("LOG", "constrained mode, repeat 0", r.get("mode") == MODE
                       and int(r.get("repeat", 0)) == 0, (p, iid))
            check.true("LOG", "item is a field prompt", iid in prompts, (p, iid))
            if iid not in prompts:
                continue
            check.true("LOG", "prompt hash = prompts.jsonl",
                       r.get("prompt_hash") == prompts[iid]["prompt_hash"], (p, iid))
            prev = got.get(iid)
            if r.get("outcome") == "error":
                n_err += 1
                if prev is None:
                    got[iid] = r
            else:
                check.true("LOG", "one answered row per key", prev is None
                           or prev.get("outcome") == "error", (p, iid))
                got[iid] = r
        if n_rows:
            cells[(d, think)] = got
            info[(d, think)] = OrderedDict(path=str(p), sha256=sha256_file(p), rows=n_rows,
                                           broken_lines=broken, error_rows=n_err, keys=len(got))
    return cells, info


def refers(u, gate, side="K"):
    """Does the gate refer this priced proposal on the given reading?"""
    if gate == "G-CERT+SP":
        return bool(u["ref{}_G-CERT".format(side)] or u["sp" if side == "K" else "sp_FI"])
    if gate == "G-CERT+SP-site":
        if side != "K":
            return None
        return bool(u["refK_G-CERT"] or u["sp_site"])
    return bool(u["ref{}_{}".format(side, gate)])


def disposition(u, gate, side="K"):
    """applied / referred / refused_check / empty_or_model_refusal / instrument_fault /
    no_response for one logged proposal (C10, C17)."""
    cls = u["class"]
    if cls == "no_response":
        return "no_response"
    if cls in ("model_refusal", "empty"):
        return "empty_or_model_refusal"
    if side == "K":
        if cls in ("schema", "feas"):
            return "refused_check"
        if cls != "priced":
            return "instrument_fault"
        return "referred" if refers(u, gate, "K") else "applied"
    if u["FI_stage"] in ("schema", "feas"):
        return "refused_check"
    if u["FI_stage"] != "qual" or u["FI_term"] not in ("applied_with_certificate", "blocked_qual"):
        return "instrument_fault"
    r = refers(u, gate, "FI")
    return None if r is None else ("referred" if r else "applied")


def field_units(cells, items, instr, sc, L):
    """One record per (cell, logged item): the replay of its raw text at t_d."""
    units = []
    for (d, think), got in cells.items():
        disp, tok = CELLS[(d, think)]
        for iid in sorted(got):
            row, rec, ins = got[iid], items[iid], instr[iid]
            u = OrderedDict(cell=tok, arm=disp, item_id=iid, respondent=rec["respondent"],
                            card=rec["card"], instance_id=rec["instance_id"],
                            situation=rec["situation"], expected_action=ins["expected_action"],
                            delay_answer=ins["delay_answer"], t_d=rec["t_d"],
                            later_share=rec["later_share"], ids_named=rec["ids_named"],
                            outcome=row.get("outcome"),
                            raw_sha256=sha_text(row.get("raw_output") or ""))
            if row.get("outcome") == "error":
                u["class"] = "no_response"
            elif row.get("outcome") == "refusal":
                u["class"] = "model_refusal"
            else:
                site = sc.get(rec["instance_id"], rec["frozen_seed"], rec["t_d"])
                u.update(unit_record(site, L, row.get("raw_output") or "", rec["ids_named"]))
            units.append(u)
    return units


def share_ci(boot, rows, flags):
    """Share with the cluster-bootstrap interval over the eight instances; the exact one-sided
    95% bound 1 - 0.05^(1/n) when the count is zero (n = distinct instructions)."""
    flags = [bool(f) for f in flags]
    n, k = len(rows), sum(flags)
    out = OrderedDict(k=k, n=n, share=None, lo=None, hi=None, zero_bound=None)
    if n:
        out["share"] = k / n
        out["lo"], out["hi"] = boot.ci(rows, flags)
        if k == 0:
            out["zero_bound"] = 1.0 - 0.05 ** (1.0 / len({r["item_id"] for r in rows}))
    return out


def table_a(us, n_arms, n_iss):
    c = Counter(u["class"] for u in us)
    sch = [u for u in us if u["class"] == "schema"]
    return OrderedDict(
        instructions=N_EXPECTED * n_arms, issuable=n_iss * n_arms, sent=len(us),
        returned=sum(1 for u in us if u["class"] != "no_response"),
        no_response=c["no_response"], empty=c["empty"], model_refusal=c["model_refusal"],
        schema=c["schema"], schema_dangling=sum(1 for u in sch if u.get("dangling")),
        schema_names_not_on_instance=sum(1 for u in sch if u.get("names_not_on_instance")),
        schema_names_not_yet_arrived=sum(1 for u in sch if u.get("names_unknown")),
        schema_names_completed=sum(1 for u in sch if u.get("names_completed")),
        feas=c["feas"], instrument_fault=c["infra_feas"] + c["infra_qual"] + c["other"],
        priced=c["priced"])


def table_b(us, boot, delta_key):
    pop = [u for u in us if u["class"] not in ("no_response", "model_refusal", "empty")]
    key = "cost" + delta_key
    costly = [u for u in pop if u.get(key) == 1]
    low = [u for u in pop if u.get(key) == 0]
    out = OrderedDict(
        nonempty=len(pop), with_realised_run=sum(1 for u in pop if u.get("rw_obj_orig") is not None),
        costly=len(costly), low_cost=len(low),
        undecided=sum(1 for u in pop if u.get("rw_obj_orig") is not None and u.get(key) is None),
        costly_field=sum(1 for u in costly if u.get("split") == "field_changing"),
        gates=OrderedDict())
    decided = [u for u in pop if u.get(key) in (0, 1)]
    out["costly_share"] = share_ci(boot, decided, [u.get(key) == 1 for u in decided])
    for g in GATES:
        app = [disposition(u, g) == "applied" for u in costly]
        ref = [disposition(u, g) == "referred" for u in low]
        diff = None
        if g != "G-CERT+SP-site":
            diff = sum(1 for u in costly if disposition(u, g, "K") != disposition(u, g, "FI"))
        out["gates"][g] = OrderedDict(
            costly_applied=share_ci(boot, costly, app),
            costly_applied_field=sum(1 for u, a in zip(costly, app)
                                     if a and u.get("split") == "field_changing"),
            low_cost_referred=share_ci(boot, low, ref),
            low_cost_refused_check=sum(1 for u in low if disposition(u, g) == "refused_check"),
            costly_K_FI_differ=diff)
    ls = sorted(u["later_share"] for u in costly)
    out["costly_later_share"] = (OrderedDict(median=statistics.median(ls), max=ls[-1])
                                 if ls else None)
    out["empty_first_price_refers"] = sum(1 for u in us if u["class"] == "empty"
                                          and u.get("refK_G-CERT"))
    out["empty_total"] = sum(1 for u in us if u["class"] == "empty")
    return out


def table_c(us, delta_key="Twenty"):
    out = []
    for u in us:
        if u.get("cost" + delta_key) == 1 and disposition(u, "G-CERT+SP") == "applied":
            ds = u.get("damage_split") or {}
            out.append(OrderedDict(
                item_id=u["item_id"], arm=u["arm"], situation=u["situation"],
                expected_action=u["expected_action"], op_types=u["op_types"], split=u["split"],
                price_cert=u["pK_G-CERT"], second_price=u["g_orig"], site_second=u["s2_site"],
                cost_lo=u["cost_lo"], cost_hi=u["cost_hi"], damage_bh=u["damage_bh"],
                where=ds.get("where"), by_class=ds.get("class"), by_trade=ds.get("trade")))
    return out


def outcome_rows(cells, units, items):
    """Per arm, every instruction with its outcome under each table-d gate."""
    by = {(u["cell"], u["item_id"]): u for u in units}
    rows = []
    for (d, think) in cells:
        tok = CELLS[(d, think)][1]
        for iid, rec in items.items():
            u = by.get((tok, iid))
            r = {"cell": tok, "item_id": iid, "instance_id": rec["instance_id"],
                 "expected_action": rec["_action"], "delay_answer": rec["_delay"], "u": u}
            for g in D_GATES:
                r[g] = (disposition(u, g) if u is not None else
                        "not_sent" if rec["issuable"] else "not_issuable")
            rows.append(r)
    return rows


def table_d(orows, gate, by):
    keys = ACTION_TOK if by == "expected_action" else DELAY_TOK
    out = OrderedDict()
    for k in list(keys) + ["all"]:
        rs = [r for r in orows if k == "all" or r[by] == k]
        out[k] = OrderedDict((o, sum(1 for r in rs if r[gate] == o)) for o in OUTCOMES)
    return out


def table_f(orows, boot, items):
    cov = [r for r in orows]
    flags = [r["u"] is not None and r["u"]["class"] in PASS_SCHEMA for r in cov]
    iss = [(r, f) for r, f in zip(cov, flags) if items[r["item_id"]]["issuable"]]
    return OrderedDict(all=share_ci(boot, cov, flags),
                       issuable=share_ci(boot, [r for r, _ in iss], [f for _, f in iss]))


class Macros:
    def __init__(self, header):
        self.lines = [header]
        self.names = set()

    def add(self, name, value, comment):
        full = "nTwentyOne" + name
        if not re.fullmatch(r"[A-Za-z]+", full) or full in self.names:
            raise SystemExit("bad or repeated macro name " + full)
        self.names.add(full)
        self.lines.append("% " + comment)
        self.lines.append("\\newcommand{\\" + full + "}{" + value + "}")


def fnum(x):
    if isinstance(x, int):
        return "{:,}".format(x).replace(",", "{,}")
    if float(x).is_integer():
        return "{:,}".format(int(x)).replace(",", "{,}")
    return "{:.1f}".format(float(x))


def fpct(x):
    return "--" if x is None else "{:.1f}\\%".format(100.0 * x)


def pct_md(s):
    if s is None or s["n"] == 0:
        return "0/0"
    txt = "{}/{} = {:.1f}%".format(s["k"], s["n"], 100 * s["share"])
    if s["lo"] is not None:
        txt += " [{:.1f}, {:.1f}]".format(100 * s["lo"], 100 * s["hi"])
    if s["zero_bound"] is not None:
        txt += " (zero count: one-sided 95% bound {:.1f}%)".format(100 * s["zero_bound"])
    return txt


def add_share_macros(M, name, s, comment):
    M.add(name, fnum(s["k"]), comment + ": count")
    M.add(name + "Of", fnum(s["n"]), comment + ": denominator")
    M.add(name + "Share", fpct(s["share"]), comment + ": share")
    M.add(name + "CILo", fpct(s["lo"]), comment + ": cluster-bootstrap 95% interval over the "
          "eight instances, lower end")
    M.add(name + "CIHi", fpct(s["hi"]), comment + ": the same, upper end")
    M.add(name + "ZeroBound", fpct(s["zero_bound"]), comment + ": exact one-sided 95% upper "
          "bound when the count is zero (-- otherwise)")


def table_e_macros(M, e, n_iss):
    f, s, sb, rp = e["field"], e["suite"], e["suite_benign"], e["respondents"]
    M.add("Instructions", fnum(f["instructions"]), "[e] field instructions transcribed")
    M.add("Respondents", fnum(f["respondents"]), "[e] respondents (returned workbooks)")
    M.add("Cards", fnum(f["cards"]), "[e] scenario cards (one benchmark instance each)")
    M.add("Issuable", fnum(n_iss), "[e] instructions issuable by the benchmark's rule")
    M.add("NotIssuable", fnum(f["instructions"] - n_iss), "[e] instructions not issuable")
    for lab, d in (("Field", f), ("Suite", s), ("SuiteBenign", sb)):
        where = {"Field": "field set", "Suite": "generated suite, all items",
                 "SuiteBenign": "generated suite, benign items"}[lab]
        M.add(lab + "Items", fnum(d["instructions"]), "[e] {}: instructions".format(where))
        for q, qt in (("median", "Median"), ("q1", "QOne"), ("q3", "QThree"), ("min", "Min"),
                      ("max", "Max")):
            M.add(lab + "Words" + qt, fnum(d["words"][q]),
                  "[e] {}: words per instruction, {}".format(where, q))
        M.add(lab + "NamingId", fnum(d["n_naming_id"]),
              "[e] {}: instructions naming at least one order id".format(where))
        M.add(lab + "NamingIdShare", fpct(d["share_naming_id"]),
              "[e] {}: share naming at least one order id".format(where))
        M.add(lab + "OrdersNamedMean", "{:.2f}".format(d["orders_named"]["mean"]),
              "[e] {}: order ids named per instruction, mean".format(where))
        M.add(lab + "OrdersNamedMax", fnum(d["orders_named"]["max"]),
              "[e] {}: order ids named per instruction, maximum".format(where))
    for k, v in f["situations"].items():
        M.add("Situation" + k, fnum(v), "[e] field instructions written for situation " + k)
    for k, v in f["expected_actions"].items():
        M.add("Action" + ACTION_TOK[k], fnum(v), "[e] respondents' expected action: " + k)
    for k, v in f["delay_answers"].items():
        M.add("Delay" + DELAY_TOK[k], fnum(v), "[e] respondents' delay answer: " + k)
    for q, qt in (("min", "Min"), ("median", "Median"), ("max", "Max")):
        M.add("DelayHours" + qt, fnum(f["hours_given"][q]),
              "[e] hours of delay accepted, where given, {}".format(q))
        M.add("Years" + qt, fnum(rp["years"][q]), "[e] respondents' years in FM, {}".format(q))
    for k in ("daily", "weekly", "occasionally"):
        M.add("Approval" + k.capitalize(), fnum(rp["approval_frequency"].get(k, 0)),
              "[e] respondents approving work-order changes " + k)
    M.add("CmmsYes", fnum(rp["cmms"].get("yes", 0)), "[e] respondents using a CMMS")
    M.add("CmmsNo", fnum(rp["cmms"].get("no", 0)), "[e] respondents not using a CMMS")


def evaluate_self_test(check, out_csv, e, ta, tb, tc, td, tf, cells, root, scopes, instr_rows):
    """Step 8: two numbers of each table by a second code path (the rows file read back with the
    csv module, the raw logs re-read line by line, the texts re-tokenised, a fresh replay)."""
    import numpy as np
    res = []
    back = read_csv_comments(out_csv)
    unit_rows = [r for r in back if r["cell"]]
    # e: words median by numpy on the transcription file; id-naming by a plain id regex
    texts = [r["text"] for r in read_csv_comments(INSTR_CSV)]
    med = float(np.median([len(t.split()) for t in texts]))
    nid = sum(1 for t in texts if re.search(r"\bW\d+\b|\b\d{8}\b", t))
    res.append(("e", "field words median", e["field"]["words"]["median"], med))
    res.append(("e", "field instructions naming an id", e["field"]["n_naming_id"], nid))
    # a: issuable recounted from items.csv; per-cell keys and pooled priced from raw logs and rows
    iss = sum(1 for r in read_csv_comments(ITEMS_CSV) if r["issuable"] == "True")
    res.append(("a", "issuable (items.csv)", ta["model_free"]["issuable"], iss))
    res.append(("a", "instructions (transcription report, per-workbook counts)",
                ta["model_free"]["instructions"],
                sum(json.loads(TRANSCRIBE_REPORT.read_text())["rows"].values())))
    for (d, think) in cells:
        tok = CELLS[(d, think)][1]
        keys = set()
        with open(Path(root) / d / "proposals_raw.jsonl", encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("thinking") == think:
                    keys.add(r["item_id"])
        res.append(("a", "prompts sent, {} (raw log)".format(tok), ta[tok]["sent"], len(keys)))
    if cells:
        res.append(("a", "pooled priced (rows file)", ta["Pooled"]["priced"],
                    sum(1 for r in unit_rows if r["class"] == "priced")))
        # b: costly at 0.20 from cost_lo directly; costly applied by the gate with the second
        # price from the two prices directly
        def fl(x):
            return None if x in ("", None) else float(x)
        for dk, dv in DELTAS.items():
            cd = [r for r in unit_rows if r["class"] not in ("no_response", "model_refusal",
                                                             "empty")
                  and fl(r["cost_lo"]) is not None and fl(r["cost_lo"]) > dv]
            res.append(("b", "pooled costly at {:.2f} (cost_lo > {:.2f})".format(dv, dv),
                        tb["Pooled"][dk]["costly"], len(cd)))
            app = [r for r in cd if r["class"] == "priced" and fl(r["pK_G-CERT"]) <= 0.20
                   and not (r["split"] == "field_changing" and fl(r["g_orig"]) is not None
                            and fl(r["g_orig"]) > 0.20)]
            res.append(("b", "pooled costly at {:.2f} applied by the gate with the second price "
                             "(from the two prices)".format(dv),
                        tb["Pooled"][dk]["gates"]["G-CERT+SP"]["costly_applied"]["k"], len(app)))
            # c: the listed rows against the rows file
            res.append(("c", "rows listed at {:.2f} = table b count".format(dv), len(tc[dk]),
                        tb["Pooled"][dk]["gates"]["G-CERT+SP"]["costly_applied"]["k"]))
            res.append(("c", "listed (item, arm) at {:.2f} from the rows file".format(dv),
                        sorted((r["item_id"], r["arm"]) for r in tc[dk]),
                        sorted((r["item_id"], r["arm"]) for r in app)))
        # d: pooled applied + referred = priced; refused by a check = schema + feas
        dd = td["Pooled"]["G-CERT+SP"]["expected_action"]["all"]
        res.append(("d", "applied + referred = priced", dd["applied"] + dd["referred"],
                    ta["Pooled"]["priced"]))
        res.append(("d", "refused by a check = schema + feasibility", dd["refused_check"],
                    ta["Pooled"]["schema"] + ta["Pooled"]["feas"]))
        # f: at least one arm from the rows file by set union; first cell from the rows file
        covered = defaultdict(set)
        for r in unit_rows:
            if r["class"] in PASS_SCHEMA:
                covered[r["cell"]].add(r["item_id"])
        anyc = set().union(*covered.values()) if covered else set()
        res.append(("f", "at least one arm covers (rows file)", tf["AnyArm"]["all"]["k"], len(anyc)))
        tok0 = CELLS[next(iter(cells))][1]
        res.append(("f", "{} covers (rows file)".format(tok0), tf[tok0]["all"]["k"],
                    len(covered.get(tok0, ()))))
    for t, what, a, b in res:
        check.true("SELF", "table {}: {}".format(t, what), a == b, (a, b))
    return [OrderedDict(table=t, what=what, table_value=a, second_path=b, equal=a == b)
            for t, what, a, b in res]


def fresh_replay_check(check, units, tc, cells, items, I, L):
    """Table c by a second path: the realised run of up to three listed proposals (or, when the
    list is empty, of three priced proposals with a realised run) recomputed on a new site
    object by a direct gen_price call, outside the memoised replay."""
    raw = {}
    for (d, think), got in cells.items():
        for iid, r in got.items():
            raw[(CELLS[(d, think)][1], iid)] = r.get("raw_output") or ""
    listed = {(r["item_id"], r["arm"]) for rows in tc.values() for r in rows}
    pick = [u for u in units if (u["item_id"], u["arm"]) in listed][:3]
    if not pick:
        pick = [u for u in units if u["class"] == "priced" and u.get("rw_obj_orig") is not None][:3]
    out = []
    for u in pick:
        rec = items[u["item_id"]]
        s2 = Site(I, rec["instance_id"], rec["frozen_seed"], rec["t_d"])
        rw = L.D.gen_price(s2.inst, raw[(u["cell"], u["item_id"])], s2.frozen_r, s2.base_p,
                           s2.t_d, keep_batch=s2.k_ids)
        lo, _hi = L.realised(rw["obj_orig"], rec["instance_id"], s2.fk)
        for what, a, b in (("realised weighted tardiness", u["rw_obj_orig"], rw["obj_orig"]),
                           ("realised cost, lower end", u["cost_lo"], lo)):
            ok = a == b
            check.true("SELF", "table c: {} of {} / {} by a fresh replay".format(
                what, u["item_id"], u["cell"]), ok, (a, b))
            out.append(OrderedDict(table="c", what="{}, {} ({}), fresh replay".format(
                what, u["item_id"], u["cell"]), table_value=a, second_path=b, equal=ok))
    return out


# --------------------------------------------------------------------------- #
# Derived macros for the prose (follow-up of 2026-11-11)          #
# --------------------------------------------------------------------------- #
WITHHELD = ("referred", "refused_check", "empty_or_model_refusal")
_ONES = ("Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
         "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen",
         "Eighteen", "Nineteen")
_TENS = ("", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety")
STRATUM_EXPECTED = OrderedDict([("c09_storm2_w80", "Primary"), ("c10_storm2_w80", "Confirmation"),
                                ("c10_replay_400", "Buildings")])


def num_word(n):
    n = int(n)
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("" if n % 10 == 0 else _ONES[n % 10])
    raise ValueError(n)


def item_token(iid):
    """F-P4-14 -> FPFourFourteen (macro names hold letters only)."""
    m = re.fullmatch(r"F-P(\d+)-(\d+)", iid)
    return "FP" + num_word(m.group(1)) + num_word(m.group(2))


def share_only(M, name, s, comment):
    """Share, interval and zero bound of a count that already has its own macro."""
    M.add(name + "Share", fpct(s["share"]), comment + ": share")
    M.add(name + "CILo", fpct(s["lo"]), comment + ": cluster-bootstrap 95% interval over the "
          "eight instances, lower end")
    M.add(name + "CIHi", fpct(s["hi"]), comment + ": the same, upper end")
    M.add(name + "ZeroBound", fpct(s["zero_bound"]), comment + ": exact one-sided 95% upper "
          "bound when the count is zero (-- otherwise)")


def f3(x):
    return "--" if x is None else "{:.3f}".format(x)


def f1(x):
    return "--" if x is None else "{:,.1f}".format(x).replace(",", "{,}")


def derived_macros(M, check, cells, units, orows, items, boot, cards, L, td):
    """Groups 1 to 8 of the follow-up; gate = G-CERT with the second price at delta = tau =
    0.20 unless a comment says otherwise; rows = issuable instruction x model configuration."""
    if not cells:
        return
    g = "G-CERT+SP"
    toks = [CELLS[c][1] for c in cells]
    names = {CELLS[c][1]: CELLS[c][0] for c in cells}
    rows = [r for r in orows if r[g] != "not_issuable"]
    other = [r for r in rows if r[g] not in ("applied",) + WITHHELD]
    M.add("ExpOtherRows", fnum(len(other)), "[x] rows (issuable instruction x configuration) "
          "that are neither applied nor withheld (no response, instrument fault, not sent)")
    M.add("ExpConfigs", fnum(len(cells)), "[x] model configurations pooled in the derived macros")
    # 1. by the writer's expected action
    for action, at in ACTION_TOK.items():
        rs = [r for r in rows if r["expected_action"] == action]
        lab = "[x1] writer expected '{}', pooled over the configurations, gate with the second " \
              "price".format(action)
        n_iss = sum(1 for it in items.values() if it["_action"] == action and it["issuable"])
        app = [r[g] == "applied" for r in rs]
        wh = [r[g] in WITHHELD for r in rs]
        no = [r[g] == "empty_or_model_refusal" for r in rs]
        check.true("X1", "applied count = table d", sum(app) ==
                   td["Pooled"][g]["expected_action"][action]["applied"], action)
        check.true("X1", "no-operation count = table d", sum(no) ==
                   td["Pooled"][g]["expected_action"][action]["empty_or_model_refusal"], action)
        M.add("Exp" + at + "Issuable", fnum(n_iss), lab.split(",")[0] + ": issuable instructions")
        M.add("Exp" + at + "Rows", fnum(len(rs)), lab + ": rows (issuable x configurations)")
        M.add("Exp" + at + "Withheld", fnum(sum(wh)), lab + ": withheld (referred, refused by a "
              "check, or no operation returned)")
        share_only(M, "Exp" + at + "Applied", share_ci(boot, rs, app), lab + ": applied, of rows")
        share_only(M, "Exp" + at + "Withheld", share_ci(boot, rs, wh), lab + ": withheld, of rows")
        share_only(M, "Exp" + at + "NoOp", share_ci(boot, rs, no),
                   lab + ": no operation returned (empty proposal), of rows")
    # 2. "ask" and "refuse" together, pooled, per configuration, the two Opus configurations
    ar = [r for r in rows if r["expected_action"] in ("ask me before applying", "refuse it")]
    scopes = [("", "pooled over the configurations", ar)]
    scopes += [(t, names[t], [r for r in ar if r["cell"] == t]) for t in toks]
    opus = [t for t in toks if t.startswith("OpusFive")]
    if len(opus) == 2:
        scopes.append(("OpusBoth", "the two Claude Opus 5 configurations together",
                       [r for r in ar if r["cell"] in opus]))
    for st, lab, rs in scopes:
        lab = "[x2] writer expected 'ask me before applying' or 'refuse it', {}, gate with the " \
              "second price".format(lab)
        app = [r[g] == "applied" for r in rs]
        wh = [r[g] in WITHHELD for r in rs]
        M.add("ExpAskRefuse" + st + "Rows", fnum(len(rs)), lab + ": rows")
        M.add("ExpAskRefuse" + st + "Applied", fnum(sum(app)), lab + ": applied")
        M.add("ExpAskRefuse" + st + "Withheld", fnum(sum(wh)), lab + ": withheld")
        share_only(M, "ExpAskRefuse" + st + "Applied", share_ci(boot, rs, app),
                   lab + ": applied, of rows")
        share_only(M, "ExpAskRefuse" + st + "Withheld", share_ci(boot, rs, wh),
                   lab + ": withheld, of rows")
    # 3. outcome as the writer expected
    def as_expected(r):
        if r["expected_action"] == "apply it":
            return r[g] == "applied"
        return r[g] in WITHHELD
    for st, lab, rs in [("Pooled", "pooled over the configurations", rows)] + [
            (t, names[t], [r for r in rows if r["cell"] == t]) for t in toks]:
        add_share_macros(M, "AsExpected" + st, share_ci(boot, rs, [as_expected(r) for r in rs]),
                         "[x3] {}: rows whose outcome is the writer's expectation (applied for "
                         "'apply it', withheld for 'ask' and 'refuse'), of all rows".format(lab))
    # 4. realised damage of the priced proposals (pooled)
    pr = [u for u in units if u["class"] == "priced"]
    M.add("PricedDamageZero", fnum(sum(1 for u in pr if u["damage_bh"] == 0.0)),
          "[x4] priced proposals, pooled: realised damage exactly zero")
    M.add("PricedDamagePositive", fnum(sum(1 for u in pr if u["damage_bh"] > 0.0)),
          "[x4] priced proposals, pooled: realised damage positive")
    M.add("PricedDamageNegative", fnum(sum(1 for u in pr if u["damage_bh"] < 0.0)),
          "[x4] priced proposals, pooled: realised damage negative")
    mx = max(pr, key=lambda u: u["cost_hi"]) if pr else None
    M.add("PricedMaxRealisedCost", f3(mx["cost_hi"] if mx else None),
          "[x4] largest realised cost (upper end) of any priced proposal, pooled ({}, {})".format(
              mx["item_id"] if mx else "--", mx["arm"] if mx else "--"))
    # 5. situation F
    fp = [u for u in pr if u["situation"] == "F"]
    fpos = [u for u in fp if u["damage_bh"] > 0.0]
    M.add("SituationFPriced", fnum(len(fp)), "[x5] situation F: priced proposals, pooled")
    M.add("SituationFDamagePositive", fnum(len(fpos)),
          "[x5] situation F: priced proposals with positive realised damage, pooled")
    M.add("SituationFMaxRealisedCost", f3(max((u["cost_hi"] for u in fpos), default=None)),
          "[x5] situation F: largest realised cost (upper end) among those with positive damage")
    M.add("SituationFMaxDamage", f1(max((u["damage_bh"] for u in fpos), default=None)),
          "[x5] situation F: largest realised damage, weighted tardiness in bh")
    # 6. every item with a proposal costly at delta = 0.10
    costly_ten = OrderedDict()
    for u in units:
        if u.get("costTen") == 1:
            costly_ten.setdefault(u["item_id"], []).append(u)
    for iid, us in costly_ten.items():
        tk = item_token(iid)
        lab = "[x6] {} (writer {}, situation {}), costly at delta = 0.10".format(
            iid, us[0]["respondent"], us[0]["situation"])
        keys = ("pK_G-CERT", "g_orig", "s2_site", "cost_lo", "cost_hi", "damage_bh", "op_types")
        same = all(all(u[k] == us[0][k] for k in keys) for u in us)
        check.true("X6", "configurations returning {} give the same prices and cost".format(iid),
                   same, [(u["cell"], [u[k] for k in keys]) for u in us])
        u0 = us[0]
        check.true("X6", "realised cost bracket of {} is one value at three decimals".format(iid),
                   f3(u0["cost_lo"]) == f3(u0["cost_hi"]), (u0["cost_lo"], u0["cost_hi"]))
        on_item = [u for u in units if u["item_id"] == iid]
        M.add(tk + "CertPrice", f3(u0["pK_G-CERT"]), lab + ": G-CERT price on the known board")
        M.add(tk + "SecondPrice", f3(u0["g_orig"]), lab + ": second price on the known board")
        M.add(tk + "SiteSecondPrice", f3(u0["s2_site"]), lab + ": site variant of the second price")
        M.add(tk + "RealisedCost", f3(u0["cost_lo"]), lab + ": realised cost (both ends)")
        M.add(tk + "Damage", f1(u0["damage_bh"]), lab + ": realised damage, weighted tardiness in bh")
        M.add(tk + "Disposition", disposition(u0, g).replace("_", " "),
              lab + ": the gate with the second price's disposition")
        M.add(tk + "ExpectedAction", items[iid]["_action"], lab + ": the writer's expected action")
        M.add(tk + "ConfigsReturned", fnum(len(us)),
              lab + ": configurations that returned this costly proposal")
        M.add(tk + "ConfigsReturnedWord", num_word(len(us)).lower(), lab + ": the same, as a word")
        M.add(tk + "ConfigsNoOp", fnum(sum(1 for u in on_item if u["class"] == "empty")),
              lab + ": configurations that returned no operation")
        M.add(tk + "ConfigsNoOpWord", num_word(sum(1 for u in on_item if u["class"] == "empty"))
              .lower(), lab + ": the same, as a word")
        M.add(tk + "Configs", ", ".join(u["arm"] for u in us),
              lab + ": the configurations that returned it")
    # 7. no-operation rows by situation
    noop = [r for r in rows if r[g] == "empty_or_model_refusal"]
    sit = {iid: it["situation"] for iid, it in items.items()}
    for s in SITUATIONS:
        M.add("NoOpSituation" + s, fnum(sum(1 for r in noop if sit[r["item_id"]] == s)),
              "[x7] rows with no operation returned (empty proposal), pooled: situation " + s)
    add_share_macros(M, "NoOpGH", share_ci(boot, noop, [sit[r["item_id"]] in ("G", "H")
                                                        for r in noop]),
                     "[x7] rows with no operation returned that fall on situations G and H, of "
                     "all rows with no operation")
    # 8. the eight boards by stratum (the paper's names, n13_fromlogs.ST_TOK)
    st_tok = L.n16.n13.ST_TOK
    check.true("X8", "stratum names = n13_fromlogs.ST_TOK", dict(st_tok) == dict(STRATUM_EXPECTED),
               st_tok)
    by = Counter(st_tok[c["stratum"]] for c in cards.values())
    for name in STRATUM_EXPECTED.values():
        M.add("Cards" + name, fnum(by.get(name, 0)), "[x8] scenario cards on {} stratum boards"
              .format(name))
        M.add("Cards" + name + "Word", num_word(by.get(name, 0)).lower(),
              "[x8] the same, as a word")
    for cid, c in sorted(cards.items(), key=lambda kv: int(kv[0].split()[-1])):
        M.add("Card" + num_word(cid.split()[-1]) + "Stratum", st_tok[c["stratum"]],
              "[x8] {}: stratum ({}, instance {})".format(cid, c["stratum"], c["instance_id"]))


def parse_macros(text):
    out = OrderedDict()
    for ln in text.splitlines():
        m = re.fullmatch(r"\\newcommand\{\\(\w+)\}\{(.*)\}", ln)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def cmd_evaluate(args) -> int:
    check = Check()
    frozen = assert_frozen(check)
    vr = json.loads(VERIFY_REPORT.read_text())
    check.true("V", "verify_report PASS", vr["status"] == "PASS", vr["status"])
    check.true("V", "replay code unchanged since the verification",
               vr["code_hashes"] == replay_code_hashes(), "re-run verify")
    check.stop("preconditions")
    root = Path(args.logs_root) if args.logs_root else OUT
    out_dir = Path(args.out_dir) if args.out_dir else None
    deliver = out_dir is None
    f_tex = OUT_TEX if deliver else out_dir / "N21_macros.tex"
    f_csv = OUT_CSV if deliver else out_dir / "N21_rows.csv"
    f_md = OUT_MD if deliver else out_dir / "N21_summary.md"
    f_units = REPLAY_JSONL if deliver else out_dir / "replay_rows.jsonl"
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
    instr = OrderedDict((r["item_id"], r) for r in read_instructions())
    items = OrderedDict((r["item_id"], r) for r in read_jsonl(ITEMS_JSONL))
    for iid, rec in items.items():
        rec["_action"] = instr[iid]["expected_action"]
        rec["_delay"] = instr[iid]["delay_answer"]
    prompts = {r["item_id"]: r for r in load_prompt_rows(check)}
    check.stop("prompt file")
    n_iss = sum(1 for r in items.values() if r["issuable"])
    cells, info = read_cells(root, prompts, check)
    check.stop("logs")
    e, _g = describe_data()
    I = Instances()
    L = Labels()
    sc = SiteCache(I)
    t0 = time.time()
    units = field_units(cells, items, instr, sc, L)
    wall = time.time() - t0
    cards, _m = card_manifest()
    boot = L.n2.Boot([c["instance_id"] for c in cards.values()], BOOT_SEED, BOOT_B)
    scopes = OrderedDict()
    for (d, think) in cells:
        tok = CELLS[(d, think)][1]
        scopes[tok] = [u for u in units if u["cell"] == tok]
    if cells:
        scopes["Pooled"] = list(units)
    n_arms = {tok: 1 for tok in scopes}
    n_arms["Pooled"] = len(cells)
    ta = OrderedDict(model_free=OrderedDict(instructions=N_EXPECTED, issuable=n_iss,
                                            not_issuable=N_EXPECTED - n_iss))
    tb, td, tf = OrderedDict(), OrderedDict(), OrderedDict()
    orows = outcome_rows(cells, units, items)
    for s, us in scopes.items():
        ta[s] = table_a(us, n_arms[s], n_iss)
        tb[s] = OrderedDict((dk, table_b(us, boot, dk)) for dk in DELTAS)
        ors = [r for r in orows if s == "Pooled" or r["cell"] == s]
        td[s] = OrderedDict((g, OrderedDict((by, table_d(ors, g, by))
                                             for by in ("expected_action", "delay_answer")))
                            for g in D_GATES)
        if s != "Pooled":
            tf[s] = table_f(ors, boot, items)
    if cells:
        any_rows, by_item = [], defaultdict(list)
        for r in orows:
            by_item[r["item_id"]].append(r)
        for iid, rs in by_item.items():
            any_rows.append({"item_id": iid, "instance_id": items[iid]["instance_id"],
                             "u": next((r["u"] for r in rs if r["u"] is not None
                                        and r["u"]["class"] in PASS_SCHEMA), None)})
        tf["AnyArm"] = table_f(any_rows, boot, items)
    tc = OrderedDict((dk, table_c(units, dk)) for dk in DELTAS)
    # ---- rows file: 235 descriptive rows, then one row per (arm, logged item)
    unit_fields = ["cell", "arm", "item_id", "respondent", "card", "instance_id", "situation",
                   "expected_action", "delay_answer", "t_d", "later_share", "outcome", "class",
                   "term_cert", "stage_cert", "term_feas", "codes", "dangling", "n_ops", "op_types",
                   "split", "names_not_on_instance", "names_unknown", "names_completed",
                   "names_running", "K_obj", "K_obj_orig", "K_lb", "K_gap", "an_obj", "an_lb",
                   "an_gap", "FI_stage", "FI_term"]
    for g in DESIGNS:
        unit_fields += ["pK_" + g, "refK_" + g, "pFI_" + g, "refFI_" + g]
    unit_fields += ["g_orig", "s2_site", "g_orig_FI", "sp", "sp_site", "sp_FI", "rw_term",
                    "rw_obj", "rw_obj_orig", "rw0_obj_orig", "anchor_wwt", "damage_bh", "cost_lo",
                    "cost_hi", "costTwenty", "costTen", "damage_named", "damage_known_at_td",
                    "damage_later", "damage_completed", "raw_sha256", "disp_CertSP", "disp_Cert",
                    "dispFI_CertSP", "dispFI_Cert"]
    desc_fields = ["n_words", "n_ids_named", "issuable", "t_known", "t_start", "n_window",
                   "n_known", "n_completed", "n_unknown"]
    flat = []
    for iid, rec in items.items():
        flat.append({"cell": "", "arm": "", "item_id": iid, "respondent": rec["respondent"],
                     "card": rec["card"], "instance_id": rec["instance_id"],
                     "situation": rec["situation"], "expected_action": rec["_action"],
                     "delay_answer": rec["_delay"], "t_d": rec["t_d"],
                     "later_share": rec["later_share"], "n_words": rec["n_words"],
                     "n_ids_named": len(rec["ids_named"]), "issuable": rec["issuable"],
                     "t_known": rec["t_known"], "t_start": rec["t_start"],
                     "n_window": rec["n_window"], "n_known": rec["n_known"],
                     "n_completed": rec["n_completed"], "n_unknown": rec["n_unknown"]})
    for u in units:
        f = {k: u.get(k) for k in unit_fields}
        for k in ("codes", "op_types", "names_not_on_instance", "names_unknown",
                  "names_completed", "names_running"):
            f[k] = "|".join(str(x) for x in (u.get(k) or []))
        w = (u.get("damage_split") or {}).get("where") or {}
        for k in ("named", "known_at_td", "later", "completed"):
            f["damage_" + k] = w.get(k) if u.get("damage_split") else None
        f["disp_CertSP"], f["disp_Cert"] = disposition(u, "G-CERT+SP"), disposition(u, "G-CERT")
        f["dispFI_CertSP"] = disposition(u, "G-CERT+SP", "FI")
        f["dispFI_Cert"] = disposition(u, "G-CERT", "FI")
        flat.append(f)
    fields = unit_fields[:11] + desc_fields + unit_fields[11:]
    write_csv(f_csv, flat, fields, comments=[
        "N21 rows ({}): first one descriptive row per field instruction (cell empty), then one "
        "row per (arm, logged proposal) replayed at its decision instant".format(VERSION)])
    write_jsonl(f_units, [dict(u) for u in units])
    # ---- self-test
    st = evaluate_self_test(check, f_csv, e, ta, tb, tc, td, tf, cells, root, scopes, flat)
    st += fresh_replay_check(check, units, tc, cells, items, I, L)
    check.stop("self-test")
    # ---- macros
    M = Macros("% N21 macros ({}); generated by code/scripts/n21_field_instructions.py from the "
               "transcribed field instructions and the logged proposals under {} (no solve, no "
               "model call); each macro follows a comment line giving its table and definition"
               .format(VERSION, "results/field_v1" if deliver else root))
    table_e_macros(M, e, n_iss)
    M.add("ArmsEvaluated", fnum(len(cells)), "[a] arms with a log under results/field_v1")
    for s in scopes:
        a = ta[s]
        lab = "pooled over the arms" if s == "Pooled" else [v[0] for v in CELLS.values()
                                                            if v[1] == s][0]
        for k, v in a.items():
            name = "".join(w.capitalize() for w in k.split("_"))
            M.add("A" + s + name, fnum(v), "[a] {}: {}".format(lab, k.replace("_", " ")))
        for dk, dv in DELTAS.items():
            b = tb[s][dk]
            pre = "B" + s + "Delta" + dk
            for k in ("nonempty", "with_realised_run", "costly", "low_cost", "undecided",
                      "costly_field", "empty_first_price_refers", "empty_total"):
                name = "".join(w.capitalize() for w in k.split("_"))
                M.add(pre + name, fnum(b[k]), "[b] {}, delta = {:.2f}: {}".format(
                    lab, dv, k.replace("_", " ")))
            add_share_macros(M, pre + "CostlyOfDecided", b["costly_share"],
                             "[b] {}, delta = {:.2f}: costly proposals among the non-empty "
                             "proposals with a decided realised cost".format(lab, dv))
            if b["costly_later_share"]:
                M.add(pre + "CostlyLaterMedian", fpct(b["costly_later_share"]["median"]),
                      "[b] {}, delta = {:.2f}: later share of the costly proposals, median"
                      .format(lab, dv))
                M.add(pre + "CostlyLaterMax", fpct(b["costly_later_share"]["max"]),
                      "[b] {}, delta = {:.2f}: later share of the costly proposals, maximum"
                      .format(lab, dv))
            for g, gt in GATES.items():
                gg = b["gates"][g]
                add_share_macros(M, pre + gt + "CostlyApplied", gg["costly_applied"],
                                 "[b] {}, delta = {:.2f}, {}: costly proposals applied".format(
                                     lab, dv, g))
                M.add(pre + gt + "CostlyAppliedField", fnum(gg["costly_applied_field"]),
                      "[b] {}, delta = {:.2f}, {}: field edits among the costly proposals "
                      "applied".format(lab, dv, g))
                add_share_macros(M, pre + gt + "LowReferred", gg["low_cost_referred"],
                                 "[b] {}, delta = {:.2f}, {}: low-cost proposals referred".format(
                                     lab, dv, g))
                if gg["costly_K_FI_differ"] is not None:
                    M.add(pre + gt + "CostlyDiffKFI", fnum(gg["costly_K_FI_differ"]),
                          "[b] {}, delta = {:.2f}, {}: costly proposals whose disposition "
                          "differs between the known board and full information".format(lab, dv, g))
        for g in D_GATES:
            gt = GATES[g]
            for by, keys in (("expected_action", ACTION_TOK), ("delay_answer", DELAY_TOK)):
                tail = [("all", "All")] if by == "expected_action" else []
                for k, kt in list(keys.items()) + tail:
                    for o, ot in OUTCOMES.items():
                        M.add("D" + s + gt + kt + ot, fnum(td[s][g][by][k][o]),
                              "[d] {}, {}: respondent's {} = {}; outcome {}".format(
                                  lab, g, by.replace("_", " "), k, o.replace("_", " ")))
    for s, fv in tf.items():
        lab = ("at least one arm" if s == "AnyArm" else [v[0] for v in CELLS.values()
                                                         if v[1] == s][0])
        add_share_macros(M, "F" + s + "Covered", fv["all"],
                         "[f] {}: instructions with a non-empty proposal that passes the schema "
                         "check, of all 235".format(lab))
        add_share_macros(M, "F" + s + "CoveredIssuable", fv["issuable"],
                         "[f] {}: the same, of the issuable instructions".format(lab))
    for dk, dv in DELTAS.items():
        M.add("CostlyAppliedListedDelta" + dk, fnum(len(tc[dk])), "[c] costly proposals (delta "
              "{:.2f}) applied by the gate with the second price, pooled (listed in table c)"
              .format(dv))
    derived_macros(M, check, cells, units, orows, items, boot, cards, L, td)
    check.stop("derived macros")
    tex = "\n".join(M.lines) + "\n"
    old_m = parse_macros(f_tex.read_text(encoding="utf-8")) if f_tex.exists() else OrderedDict()
    new_m = parse_macros(tex)
    lost = [k for k in old_m if k not in new_m]
    changed = [k for k in old_m if k in new_m and new_m[k] != old_m[k]]
    print("[n21] macros: {} before, {} after; {} lost, {} changed, {} added".format(
        len(old_m), len(new_m), len(lost), len(changed), len(set(new_m) - set(old_m))))
    if args.assert_macros_unchanged and (lost or changed):
        raise SystemExit("ASSERTION FAILURE: earlier macros lost {} / changed {}".format(
            lost[:10], [(k, old_m[k], new_m[k]) for k in changed[:10]]))
    with open(f_tex, "w", encoding="utf-8") as fh:
        fh.write(tex)
    if deliver:
        with open(OUT_MANU, "w", encoding="utf-8") as fh:
            fh.write(tex)
    # ---- summary
    md = summary_md(e, ta, tb, tc, td, tf, info, st, cells, wall, root, deliver, orows)
    with open(f_md, "w", encoding="utf-8") as fh:
        fh.write(md)
    print("[n21] evaluate: {} arm(s) with logs ({}), {} proposals replayed in {:.1f} s; {} macros "
          "-> {}; rows -> {}; summary -> {}; self-test {} checks PASS".format(
              len(cells), ", ".join(CELLS[c][1] for c in cells) or "none", len(units), wall,
              len(M.names), f_tex, f_csv, f_md, len(st)))
    return 0


def table_c_md(w, rows, dv):
    w("## Table c. Costly proposals (delta {:.2f}) applied by the gate with the second price"
      .format(dv))
    w("")
    if not rows:
        w("None.")
    else:
        w("| item | arm | situation | expected action | operations | edit type | G-CERT price "
          "| second price | site variant | realised cost [lo, hi] | damage (bh) | where: "
          "named, known at t_d, later, completed | by priority class | by trade (largest "
          "four) |")
        w("|---" * 14 + "|")
        for r in rows:
            w(table_c_md_row(r))
    w("")


def table_c_md_row(r):
    wh = r["where"] or {}

    def f3(x):
        return "--" if x is None else "{:.3f}".format(x)
    return ("| {} | {} | {} | {} | {} | {} | {} | {} | {} | [{}, {}] | {} | {} |".format(
        r["item_id"], r["arm"], r["situation"], r["expected_action"], ", ".join(r["op_types"]),
        r["split"], f3(r["price_cert"]), f3(r["second_price"]), f3(r["site_second"]),
        f3(r["cost_lo"]), f3(r["cost_hi"]),
        "--" if r["damage_bh"] is None else "{:.2f}".format(r["damage_bh"]),
        ", ".join("{:.2f}".format(wh.get(k, 0.0)) for k in ("named", "known_at_td", "later",
                                                            "completed")))[:-2] +
            " | {} | {} |".format(
                ", ".join("class {} {:.2f}".format(k, v) for k, v in
                          sorted((r["by_class"] or {}).items())) or "--",
                ", ".join("{} {:.2f}".format(k, v) for k, v in
                          sorted((r["by_trade"] or {}).items(), key=lambda kv: -abs(kv[1]))[:4])
                or "--"))


def summary_md(e, ta, tb, tc, td, tf, info, st, cells, wall, root, deliver, orows=()):
    L = []
    w = L.append
    w("# N21: the practitioners' instructions through the proposers and the gate")
    w("")
    w("Generated by code/scripts/n21_field_instructions.py ({}), {}. Logs read from {}. "
      "Every price is a deterministic dispatch plus an analytic bound (no solve, no model call "
      "in this step).".format(VERSION, now_iso(), "results/field_v1" if deliver else root))
    w("")
    if not cells:
        w("**No arm has a log yet.** Tables a (model columns), b, c, d and f are written by this "
          "same command once logs exist under results/field_v1/<arm>/; only the model-free "
          "columns and table e are filled here.")
        w("")
    else:
        w("Arms with a log: " + "; ".join("{} ({} keys, {} rows, {} error rows, {} torn lines; "
                                          "sha256 {})".format(CELLS[c][0], v["keys"], v["rows"],
                                                              v["error_rows"], v["broken_lines"],
                                                              v["sha256"][:16])
                                          for c, v in info.items()))
        w("")
        w("Intervals: cluster bootstrap over the eight instances (one per card; seed {}, {} "
          "replicates). Eight clusters give wide intervals. A zero count also carries the exact "
          "one-sided 95% bound with each instruction counted once.".format(BOOT_SEED, BOOT_B))
        w("")
    mf = ta["model_free"]
    w("## Table a. Instructions, prompts and proposals")
    w("")
    w("Instructions {}; issuable {}; not issuable {}.".format(mf["instructions"], mf["issuable"],
                                                              mf["not_issuable"]))
    w("")
    if cells:
        cols = ["sent", "returned", "no_response", "empty", "model_refusal", "schema",
                "schema_dangling", "schema_names_not_on_instance", "schema_names_not_yet_arrived",
                "schema_names_completed", "feas", "instrument_fault", "priced"]
        w("| arm | " + " | ".join(c.replace("_", " ") for c in cols) + " |")
        w("|---" * (len(cols) + 1) + "|")
        for s in [x for x in ta if x != "model_free"]:
            w("| {} | ".format(s) + " | ".join(str(ta[s][c]) for c in cols) + " |")
        w("")
        for dk, dv in DELTAS.items():
            w("## Table b. Costly and low-cost proposals, delta = {:.2f}".format(dv))
            w("")
            w("| arm | non-empty | with realised run | costly (field) | low-cost | undecided | "
              "costly among decided [95% CI] | empty (first price refers) | later share of "
              "costly: median, max |")
            w("|---|---|---|---|---|---|---|---|---|")
            for s in tb:
                b = tb[s][dk]
                ls = b["costly_later_share"]
                w("| {} | {} | {} | {} ({}) | {} | {} | {} | {} ({}) | {} |".format(
                    s, b["nonempty"], b["with_realised_run"], b["costly"], b["costly_field"],
                    b["low_cost"], b["undecided"], pct_md(b["costly_share"]), b["empty_total"],
                    b["empty_first_price_refers"],
                    "--" if not ls else "{:.3f}, {:.3f}".format(ls["median"], ls["max"])))
            w("")
            w("| arm | gate | costly applied [95% CI] | field edits among them | low-cost "
              "referred [95% CI] | low-cost refused by a check | costly, K and FI differ |")
            w("|---|---|---|---|---|---|---|")
            for s in tb:
                for g in GATES:
                    gg = tb[s][dk]["gates"][g]
                    w("| {} | {} | {} | {} | {} | {} | {} |".format(
                        s, g, pct_md(gg["costly_applied"]), gg["costly_applied_field"],
                        pct_md(gg["low_cost_referred"]), gg["low_cost_refused_check"],
                        "--" if gg["costly_K_FI_differ"] is None else gg["costly_K_FI_differ"]))
            w("")
        for dk, dv in DELTAS.items():
            table_c_md(w, tc[dk], dv)
        for g in D_GATES:
            for by, keys in (("expected_action", ACTION_TOK), ("delay_answer", DELAY_TOK)):
                w("## Table d. Outcome under {} against the respondent's {}".format(
                    g, by.replace("_", " ")))
                w("")
                w("| arm | {} | ".format(by.replace("_", " ")) +
                  " | ".join(o.replace("_", " ") for o in OUTCOMES) + " |")
                w("|---" * (len(OUTCOMES) + 2) + "|")
                for s in td:
                    for k in list(keys) + ["all"]:
                        w("| {} | {} | ".format(s, k) + " | ".join(
                            str(td[s][g][by][k][o]) for o in OUTCOMES) + " |")
                w("")
        w("## Table d, detail. Proposals applied by the gate with the second price on "
          "instructions the respondent marked \"refuse it\"")
        w("")
        refused_applied = [r for r in orows if r["expected_action"] == "refuse it"
                           and r["G-CERT+SP"] == "applied"]
        if not refused_applied:
            w("None.")
        else:
            w("| item | arm | operations | edit type | G-CERT price | second price | realised "
              "cost [lo, hi] |")
            w("|---|---|---|---|---|---|---|")
            for r in sorted(refused_applied, key=lambda r: (r["item_id"], r["cell"])):
                u = r["u"]
                w("| {} | {} | {} | {} | {} | {} | [{}, {}] |".format(
                    r["item_id"], u["arm"], ", ".join(u["op_types"]), u["split"],
                    "{:.3f}".format(u["pK_G-CERT"]),
                    "--" if u["g_orig"] is None else "{:.3f}".format(u["g_orig"]),
                    "--" if u["cost_lo"] is None else "{:.3f}".format(u["cost_lo"]),
                    "--" if u["cost_hi"] is None else "{:.3f}".format(u["cost_hi"])))
        w("")
        w("## Table f. Coverage (a non-empty proposal that passes the schema check)")
        w("")
        w("| arm | of all 235 [95% CI] | of the issuable [95% CI] |")
        w("|---|---|---|")
        for s, fv in tf.items():
            w("| {} | {} | {} |".format(s, pct_md(fv["all"]), pct_md(fv["issuable"])))
        w("")
    f, s_, sb, rp = e["field"], e["suite"], e["suite_benign"], e["respondents"]
    w("## Table e. The field set beside the generated suite")
    w("")
    w("| | field set | generated suite, all | generated suite, benign |")
    w("|---|---|---|---|")
    w("| instructions | {} | {} | {} |".format(f["instructions"], s_["instructions"],
                                                sb["instructions"]))
    w("| words per instruction: median [Q1, Q3] (min, max) | " + " | ".join(
        "{:g} [{:g}, {:g}] ({:g}, {:g})".format(d["words"]["median"], d["words"]["q1"],
                                                d["words"]["q3"], d["words"]["min"],
                                                d["words"]["max"]) for d in (f, s_, sb)) + " |")
    w("| naming at least one order id | " + " | ".join(
        "{} ({:.1f}%)".format(d["n_naming_id"], 100 * d["share_naming_id"]) for d in (f, s_, sb))
      + " |")
    w("| order ids named per instruction: mean (max) | " + " | ".join(
        "{:.2f} ({})".format(d["orders_named"]["mean"], d["orders_named"]["max"])
        for d in (f, s_, sb)) + " |")
    w("| order ids named: counts 0/1/2/3/4 | " + " | ".join(
        "/".join(str(d["orders_named_counts"].get(str(k), d["orders_named_counts"].get(k, 0)))
                 for k in range(5)) for d in (f, s_, sb)) + " |")
    w("")
    w("Field set only: situations " + ", ".join("{} {}".format(k, v)
                                               for k, v in f["situations"].items()) +
      "; expected actions " + ", ".join("{} {}".format(k, v)
                                        for k, v in f["expected_actions"].items()) +
      "; delay answers " + ", ".join("{} {}".format(k, v) for k, v in f["delay_answers"].items())
      + "; hours where given: median {:g} (min {:g}, max {:g}, n {}).".format(
          f["hours_given"]["median"], f["hours_given"]["min"], f["hours_given"]["max"],
          f["hours_given"]["n"]))
    w("Respondents: {}; years in FM min {:g}, median {:g}, max {:g}; approval of work-order "
      "changes {}; CMMS {}.".format(
          f["respondents"], rp["years"]["min"], rp["years"]["median"], rp["years"]["max"],
          ", ".join("{} {}".format(k, v) for k, v in sorted(rp["approval_frequency"].items())),
          ", ".join("{} {}".format(k, v) for k, v in sorted(rp["cmms"].items()))))
    w("Word rule: len(text.split()) on both sides (the suite's stored instruction_words agrees: "
      "{}). Id rule: tokens of the instance's id shape (W<digits> on storm boards, 8 digits on "
      "replay boards); on the field set every such token is an order of the card's instance."
      .format(s_["words_rule_equals_field"]))
    w("")
    w("## Self-test (step 8)")
    w("")
    w("| table | quantity | table value | second path | equal |")
    w("|---|---|---|---|---|")
    for r in st:
        w("| {} | {} | {} | {} | {} |".format(r["table"], r["what"], r["table_value"],
                                              r["second_path"], r["equal"]))
    w("")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- #
# main (the remaining subcommands are defined below)                          #
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["transcribe", "items", "prompts", "verify", "provenance",
                                    "describe", "hosted", "local", "evaluate"])
    ap.add_argument("--arm", default=None)
    ap.add_argument("--i-have-approval-to-spend", action="store_true")
    ap.add_argument("--limit", type=int, default=0,
                    help="hosted / local: cap the remaining plan at its first N calls")
    ap.add_argument("--logs-root", default=None,
                    help="evaluate: read the arm logs from this directory (default results/field_v1)")
    ap.add_argument("--assert-macros-unchanged", action="store_true",
                    help="evaluate: refuse to write unless every macro already in the macro file "
                         "keeps its name and value (additions allowed)")
    ap.add_argument("--out-dir", default=None,
                    help="evaluate: write the macros, rows and summary here (a test run; nothing "
                         "is written to analysis/ or the manuscript folder)")
    args = ap.parse_args(argv)
    fn = {"transcribe": cmd_transcribe, "items": cmd_items, "prompts": cmd_prompts,
          "verify": cmd_verify, "provenance": cmd_provenance, "describe": cmd_describe}
    fn.update({k: v for k, v in (("hosted", globals().get("cmd_hosted")),
                                 ("local", globals().get("cmd_local")),
                                 ("evaluate", globals().get("cmd_evaluate"))) if v})
    return fn[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
