#!/usr/bin/env python3
"""N28: the second set of practitioners' instructions through the proposers and the gate.

Design pre-specified before the run.  Frozen design: the decision record, entry
"2026-11-11 01:20", decision 2 (the gate, the certificate, the six designs at their own
thresholds, the second price on field edits with tau = 0.20 and its site variant, the
decision-instant rule, the realised-cost label, the cost levels 0.20 and 0.10), and the entry
"2026-11-12 (early morning)" (the second set's design and the reporting planned before any
return was seen).  The choices of results/field_v1/design_choices.md and
design_choices_addendum.md apply unchanged; the cases they do not settle for the second set are
in results/field_r2/design_choices.md, recorded before any gate result of the second set.

Eight practitioners (Q1 to Q8) wrote 220 instructions on the eight scenario cards of the second
collection (the data-collection pack (not released)).  This script scores them
by the SAME code path that scored the first set: it loads code/scripts/n21_field_instructions.py
FROM SOURCE with the in-memory swaps listed in SWAPS (each asserted to occur exactly the stated
number of times; the file on disk is untouched, its sha256 is asserted, and the replay section
executed in memory is asserted byte-identical to the one on disk).  It re-implements no price,
no check and no replay.

Swapped constants: core allowance {3} (n21's own guard and the allowance it writes into n16's
source), the version string, OUT = results/field_r2, the pack path, the R2 card manifest, the
output names N28_*, the respondent codes and row counts (Q1 27, Q2 25, Q3 27, Q4 31, Q5 25,
Q6 29, Q7 27, Q8 29; 220), the item set "field_r2", the card partners (Q1/Q5, Q2/Q6, Q3/Q7,
Q4/Q8), the spending limit of the GPT arm, the macro prefix \\nTwentyEight, the item token of the
derived macros (G-Q4-14 -> GQFourFourteen), the sent workbook of the provenance step and the
returned file names (Field_Instruction_Workbook_R2_Qk.xlsx), and labels in comments and titles.

Wrapped or replaced n21 functions (first-set facts that a constant cannot swap):
  transcribe     n21.cmd_transcribe reads the first form (eight answer columns, five "About you"
                 rows).  The second form has nine answer columns (an expected-delay column
                 between "Hours" and "Why") and six "About you" rows (approval frequency asked as
                 "How often ...", plus "Did you take part in the first set").  cmd_transcribe
                 below is n21's step for that layout, with n21's reader (read_workbooks, a
                 separate ``python -I`` process), assignment rule and checks, plus the
                 expected-delay dropdown check.
  items          n21 asserts that a card's in-progress set is its first three orders (every
                 first-set card showed three).  Card 8 of the second set shows none, because no
                 suite item on c10_replay_400_0009 has a standing frozen set.  The swap makes
                 the check "the first len(in-progress) orders"; cmd_items adds the stronger
                 assertion that each card's in-progress set equals the suite's standing frozen
                 set on its instance (empty when no suite item there has one), then runs
                 n21.cmd_items unchanged.
  derived macros group 6 (one block per item with a proposal costly at 0.10) asserts that every
                 configuration returning a costly proposal for an item returns the same prices
                 and cost (true on the first set); the block is replaced in memory by a call to
                 group6_r2, one block per (item, configuration).
  field_units    wrapped: after n21's replay, each proposal with a realised run is run again
                 through the SAME call Site.replay makes (n11_decision_time.gen_price on the full
                 instance, keep_live) to read the per-order completion times and per-order
                 weighted tardiness (Site.per_order_wt) that tables h and j need; the re-run's
                 objectives are asserted equal to the replay's, and the per-order split's sum to
                 n21's damage split.
  write_csv      wrapped for the rows file only: the new columns are appended to n21's (a
                 column n21 already writes is not written twice).
  derived_macros wrapped: after n21's groups, tables g to j, their macros, the derived groups
                 [y] (second set, pooled) and [z] (both sets: the first set's values read from
                 analysis/N21_macros.tex and N21_rows.csv, hashes asserted, and the audit count
                 from the manuscript's macro file, value asserted), the derived group [r] (the
                 regularities of the written texts of both sets, read from the sets'
                 text_regularities files and recomputed from their instructions.csv by n21's
                 text_frame), and the n28 self-test.
  summary_md     wrapped: tables g to j, the pooled comparison row, the n28 self-test and the
                 lists of the [y], [z] and [r] macros appended.

Subcommands (as in n21, without ``local``):
  transcribe, items, prompts, verify, provenance, describe, hosted, evaluate.
Restartable: ``hosted`` is n21.cmd_hosted, which never re-sends a key whose answer is logged.

Core 3 only, one thread, no GPU, no time-limited solve: every price is a deterministic dispatch
plus an analytic bound.  Run (from the repository root):
  OMP_NUM_THREADS=1 python code/scripts/n28_field_r2.py transcribe
  ... items | prompts | verify | provenance | describe
  ... hosted --arm sonnet|opus|openai --i-have-approval-to-spend [--limit N]
  ... evaluate
Version: l1-n28-field-r2-1
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_v] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import sys  # noqa: E402

sys.dont_write_bytecode = True  # no __pycache__ file of an existing script is rewritten

ALLOWED_CORES = {3}
_aff = set(os.sched_getaffinity(0))
if not _aff <= ALLOWED_CORES and not os.environ.get("CERTIGATE_ANY_CORES"):
    raise SystemExit("REFUSING TO RUN: affinity {} is not inside core 3 (the project's core)"
                     .format(sorted(_aff)))

import argparse  # noqa: E402
import csv  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import statistics  # noqa: E402
import subprocess  # noqa: E402
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

VERSION = "l1-n28-field-r2-1"
N21_PATH = SCRIPTS_DIR / "n21_field_instructions.py"
#: sha256 of n21_field_instructions.py as this release holds it (asserted before loading).
N21_SHA256 = "cd6b42b0dfcd9f991405dc979397fb801a5cc54074888bc9cec5b6e48b48a842"
MANIFEST_SHA_PREFIX = "ee90a9eb44c9aca28c58"
PACK_REL = ("participant_files/returned_workbooks_r2/"
            "1_Field_Instructions_Round2")
CARDS_R2 = OrderedDict([
    ("Card 1", "c09_storm2_w80_u100_0018"), ("Card 2", "c09_storm2_w80_u100_0019"),
    ("Card 3", "c09_storm2_w80_u100_0002"), ("Card 4", "c09_storm2_w80_u100_0004"),
    ("Card 5", "c10_storm2_w80_u100_0008"), ("Card 6", "c10_replay_400_0021"),
    ("Card 7", "c10_replay_400_0020"), ("Card 8", "c10_replay_400_0009")])

#: (old, new, expected count) applied to n21's source before it is executed.
SWAPS = (
    ("ALLOWED_CORES = {10, 11}", "ALLOWED_CORES = {3}", 2),
    ('"REFUSING TO RUN: affinity {} is not inside cores 10-11 "\n'
     '                     "(run under taskset -c 10-11)"',
     '"REFUSING TO RUN: affinity {} is not inside core 3 "\n'
     '                     "(the project\'s core)"', 1),
    ('VERSION = "l1-n21-field-1"', 'VERSION = "' + VERSION + '"', 1),
    ('OUT = RESULTS / "field_v1"', 'OUT = RESULTS / "field_r2"', 1),
    ('PACK = (ROOT / "participant_files" / "returned_workbooks" /\n'
     '        "1_Field_Instructions")',
     'PACK = (ROOT / "participant_files" / "returned_workbooks_r2" /\n'
     '        "1_Field_Instructions_Round2")', 1),
    ('CARD_MANIFEST = ROOT / "participant_files" / "field_instructions" / "card_manifest.json"',
     'CARD_MANIFEST = ROOT / "participant_files" / "field_instructions_r2" / "card_manifest_r2.json"',
     1),
    ('OUT_TEX = ANALYSIS / "N21_macros.tex"', 'OUT_TEX = ANALYSIS / "N28_macros.tex"', 1),
    ('OUT_MANU = MANU / "macros_n21.tex"', 'OUT_MANU = MANU / "macros_n28.tex"', 1),
    ('OUT_CSV = ANALYSIS / "N21_rows.csv"', 'OUT_CSV = ANALYSIS / "N28_rows.csv"', 1),
    ('OUT_MD = ANALYSIS / "N21_summary.md"', 'OUT_MD = ANALYSIS / "N28_summary.md"', 1),
    ('EXPECTED_ROWS = OrderedDict([("P1", 26), ("P2", 29), ("P3", 31), ("P4", 31), ("P5", 28),\n'
     '                             ("P6", 31), ("P7", 28), ("P8", 31)])\nN_EXPECTED = 235',
     'EXPECTED_ROWS = OrderedDict([("Q1", 27), ("Q2", 25), ("Q3", 27), ("Q4", 31), ("Q5", 25),\n'
     '                             ("Q6", 29), ("Q7", 27), ("Q8", 29)])\nN_EXPECTED = 220', 1),
    ('"trap_ops": None, "set": "field_v1"}', '"trap_ops": None, "set": "field_r2"}', 1),
    ('prompt_chars=pr["prompt_chars"], item_set="field_v1", runner=VERSION)',
     'prompt_chars=pr["prompt_chars"], item_set="field_r2", runner=VERSION)', 1),
    ("budget_usd=4.41", "budget_usd=4.19", 1),
    ('run=3 * gpt["usd_est_no_cache"] < 4.41)', 'run=3 * gpt["usd_est_no_cache"] < 4.19)', 1),
    ('GPT-5.4-mini rule: 3 x {:.3f} = {:.3f} < 4.41 -> {}',
     'GPT-5.4-mini rule: 3 x {:.3f} = {:.3f} < 4.19 -> {}', 1),
    ('"235 transcribed rows"', '"220 transcribed rows"', 1),
    ('list(card["frozen_set_shown"]) == list(card["order_ids"][:3])',
     'list(card["frozen_set_shown"]) == list(card["order_ids"][:len(card["frozen_set_shown"])])',
     1),
    ('comments=["N21 items: names', 'comments=["N28 items: names', 1),
    ('SENT_WORKBOOK = (ROOT / "participant_files" / "data_collection_pack" / "1_Field_Instructions" /\n'
     '                 "Field_Instruction_Workbook.xlsx")',
     'SENT_WORKBOOK = (ROOT / "participant_files" / "data_collection_pack_r2" / '
     '"1_Field_Instructions_Round2" /\n                 "Field_Instruction_Workbook_R2.xlsx")', 1),
    ('"Field_Instruction_Workbook_{}.xlsx"', '"Field_Instruction_Workbook_R2_{}.xlsx"', 2),
    ('PAIRS = (("P1", "P5"), ("P2", "P6"), ("P3", "P7"), ("P4", "P8"))',
     'PAIRS = (("Q1", "Q5"), ("Q2", "Q6"), ("Q3", "Q7"), ("Q4", "Q8"))', 1),
    ('full = "nTwentyOne" + name', 'full = "nTwentyEight" + name', 1),
    ('m = re.fullmatch(r"F-P(\\d+)-(\\d+)", iid)\n    return "FP" + num_word',
     'm = re.fullmatch(r"G-Q(\\d+)-(\\d+)", iid)\n    return "GQ" + num_word', 1),
    ('f_tex = OUT_TEX if deliver else out_dir / "N21_macros.tex"',
     'f_tex = OUT_TEX if deliver else out_dir / "N28_macros.tex"', 1),
    ('f_csv = OUT_CSV if deliver else out_dir / "N21_rows.csv"',
     'f_csv = OUT_CSV if deliver else out_dir / "N28_rows.csv"', 1),
    ('f_md = OUT_MD if deliver else out_dir / "N21_summary.md"',
     'f_md = OUT_MD if deliver else out_dir / "N28_summary.md"', 1),
    ('"N21 rows ({}): first one descriptive row', '"N28 rows ({}): first one descriptive row', 1),
    ('M = Macros("% N21 macros ({}); generated by code/scripts/n21_field_instructions.py from the "',
     'M = Macros("% N28 macros ({}); generated by code/scripts/n28_field_r2.py (which loads "\n'
     '               "code/scripts/n21_field_instructions.py from source) from the "', 1),
    ('"results/field_v1" if deliver else root', '"results/field_r2" if deliver else root', 2),
    ('"[a] arms with a log under results/field_v1"', '"[a] arms with a log under results/field_r2"',
     1),
    ('"check, of all 235"', '"check, of all 220"', 1),
    ('w("# N21: the practitioners\' instructions through the proposers and the gate")',
     'w("# N28: the second set of practitioners\' instructions through the proposers and the '
     'gate")', 1),
    ('w("Generated by code/scripts/n21_field_instructions.py ({}), {}. Logs read from {}. "',
     'w("Generated by code/scripts/n28_field_r2.py, which loads code/scripts/'
     'n21_field_instructions.py from source ({}), {}. Logs read from {}. "', 1),
    ("same command once logs exist under results/field_v1/<arm>/",
     "same command once logs exist under results/field_r2/<arm>/", 1),
    ('w("| arm | of all 235 [95% CI] | of the issuable [95% CI] |")',
     'w("| arm | of all 220 [95% CI] | of the issuable [95% CI] |")', 1),
)
GROUP6_BEGIN = "    # 6. every item with a proposal costly at delta = 0.10\n"
GROUP6_END = "    # 7. no-operation rows by situation\n"
GROUP6_CALL = "    _N28_GROUP6(M, check, units, items, g)\n"


def _sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_n21():
    """n21_field_instructions as a module, with the swaps of SWAPS and the group-6 replacement
    applied in memory.  The file on disk is untouched; its hash and the replay section are
    asserted (the precedent is field_cards_r2.load_n21 and n20's loading of n16)."""
    got = _sha256(N21_PATH)
    if got != N21_SHA256:
        raise SystemExit("REFUSING TO RUN: n21_field_instructions.py sha256 {} is not the "
                         "release's {}".format(got, N21_SHA256))
    disk = N21_PATH.read_text(encoding="utf-8")
    src = disk
    for old, new, count in SWAPS:
        if src.count(old) != count:
            raise SystemExit("n21 swap: {!r} found {} times, expected {}".format(
                old[:80], src.count(old), count))
        src = src.replace(old, new)
    if src.count(GROUP6_BEGIN) != 1 or src.count(GROUP6_END) != 1:
        raise SystemExit("n21 swap: the group-6 markers are not unique")
    a, b = src.index(GROUP6_BEGIN), src.index(GROUP6_END)
    src = src[:a] + GROUP6_CALL + src[b:]

    def section(text):
        i, j = text.index("# REPLAY-SOURCE-BEGIN"), text.index("# REPLAY-SOURCE-END")
        return text[i:j]
    if section(src) != section(disk):
        raise SystemExit("n21 swap: the replay section executed would differ from the disk")
    mod = types.ModuleType("n21_field_instructions")
    mod.__file__ = str(N21_PATH)
    sys.modules["n21_field_instructions"] = mod
    exec(compile(src, str(N21_PATH), "exec"), mod.__dict__)  # noqa: S102
    mod._N28_SOURCE_SHA256 = hashlib.sha256(src.encode("utf-8")).hexdigest()
    return mod


n21 = load_n21()
OUT = n21.OUT
assert OUT == ROOT / "results" / "field_r2", OUT
assert n21.PACK == ROOT / PACK_REL, n21.PACK
assert n21.N_EXPECTED == 220 and sum(n21.EXPECTED_ROWS.values()) == 220
CHOICES = OUT / "design_choices.md"
LOGS = OUT / "logs"
DESCRIBE_R2 = OUT / "text_regularities_r2.json"

# ---- the second form ---------------------------------------------------------------------- #
ANSWER_HEAD_R2 = ("Respondent code", "Card", "Situation (A-H)",
                  "Instruction (exactly as you would say or type it)",
                  "What should the system do?", "Is the delay it causes acceptable?",
                  "Hours (if you chose up to __ hours)",
                  "How much delay do you expect it to cause?", "Why (optional)")
EXP_DELAY_CHOICES = ("none", "up to half a day", "half a day to two days", "more than two days")
EXP_DELAY_TOK = OrderedDict([("none", "None"), ("up to half a day", "HalfDay"),
                             ("half a day to two days", "TwoDays"),
                             ("more than two days", "OverTwoDays")])
ABOUT_KEYS_R2 = OrderedDict([
    ("Respondent code", "respondent"),
    ("Your role (for example maintenance supervisor, facilities manager or dispatcher)", "role"),
    ("Years in facility management", "years"),
    ("How often do you approve work-order changes?", "approval_frequency"),
    ("Do you use a computerised maintenance management system (CMMS)?", "cmms"),
    ("Did you take part in the first set of this study?", "first_set")])
APPROVAL_CHOICES = ("daily", "weekly", "occasionally", "never")
YESNO = ("yes", "no")
#: table j: the expected-delay answer's bracket of the largest added delay (bh)
BRACKETS = OrderedDict([("none", (None, 0.0)), ("up to half a day", (0.0, 4.0)),
                        ("half a day to two days", (4.0, 16.0)),
                        ("more than two days", (16.0, None))])
DELAY_TOL_BH = 1e-6


# --------------------------------------------------------------------------- #
# Step 1: transcription of the second form                                    #
# --------------------------------------------------------------------------- #
def cmd_transcribe(args) -> int:
    """n21.cmd_transcribe for the nine-column form; the role is transcribed, never printed."""
    check = n21.Check()
    OUT.mkdir(parents=True, exist_ok=True)
    paths = [n21.PACK / "Field_Instruction_Workbook_R2_{}.xlsx".format(p)
             for p in n21.EXPECTED_ROWS]
    hashes_before = OrderedDict((p.name, n21.sha256_file(p)) for p in paths)
    data = n21.read_workbooks(paths)
    cards, _m = n21.card_manifest()
    rows, resp, anomalies = [], [], []
    for p in paths:
        code = p.stem.split("_")[-1]
        d = data[str(p)]
        check.true("T1", "sheets present in {}".format(p.name),
                   "Answers" in d["sheets"] and "About you" in d["sheets"], d["sheets"])
        ans = d["Answers"]
        check.true("T1", "Answers header of {}".format(p.name),
                   tuple(ans[0][:9]) == ANSWER_HEAD_R2, ans[0][:9])
        k = 0
        assigned = n21.assignment(int(code[1:]))
        for j, row in enumerate(ans[1:], start=2):
            row = list(row) + [None] * (9 - len(row))
            text = row[3]
            other = [c for i, c in enumerate(row[:9]) if i != 3 and c not in (None, "")]
            if text is None or (isinstance(text, str) and not text.strip()):
                if other:
                    anomalies.append({"workbook": p.name, "sheet_row": j,
                                      "issue": "row with answers but an empty instruction",
                                      "cells": row[:9]})
                continue
            k += 1
            rcode, card, sit, _t, act, delay, hours, exp_delay, why = row[:9]
            item_id = "G-{}-{:02d}".format(code, k)
            issues = []
            if rcode != code:
                issues.append("respondent code {!r} differs from the workbook {}".format(rcode, code))
            if card not in assigned:
                issues.append("card {!r} outside the assigned {}".format(card, list(assigned)))
            if sit not in n21.SITUATIONS:
                issues.append("situation {!r} outside A-H".format(sit))
            if act not in n21.ACTION_CHOICES:
                issues.append("action {!r} outside the dropdown".format(act))
            if delay not in n21.DELAY_CHOICES:
                issues.append("delay {!r} outside the dropdown".format(delay))
            if exp_delay not in EXP_DELAY_CHOICES:
                issues.append("expected delay {!r} outside the dropdown".format(exp_delay))
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
                hours=hours, why=why, expected_delay=exp_delay))
        check.true("T2", "{} filled rows = {}".format(code, n21.EXPECTED_ROWS[code]),
                   k == n21.EXPECTED_ROWS[code], k)
        about = {r[0]: (r[1] if len(r) > 1 else None) for r in d["About you"][1:] if r and r[0]}
        rec = OrderedDict()
        for q, key in ABOUT_KEYS_R2.items():
            check.true("T3", "About you of {} answers '{}'".format(code, key), q in about, key)
            rec[key] = about.get(q)
        check.true("T3", "About you respondent code of {}".format(code), rec["respondent"] == code,
                   "respondent code differs")
        check.true("T3", "About you of {}: approval frequency is a dropdown value".format(code),
                   rec["approval_frequency"] in APPROVAL_CHOICES, "not a dropdown value")
        check.true("T3", "About you of {}: CMMS is yes or no".format(code), rec["cmms"] in YESNO,
                   "not yes/no")
        check.true("T3", "About you of {}: first set is yes or no".format(code),
                   rec["first_set"] in YESNO, "not yes/no")
        resp.append(rec)
    check.true("T2", "220 rows in all", len(rows) == n21.N_EXPECTED, len(rows))
    hashes_after = OrderedDict((p.name, n21.sha256_file(p)) for p in paths)
    check.true("T4", "workbooks unchanged by the read", hashes_before == hashes_after)
    check.stop("transcribe")
    fields = ("item_id", "respondent", "sheet_row", "card", "instance_id", "situation", "text",
              "expected_action", "delay_answer", "hours", "why", "expected_delay")
    n21.write_csv(n21.INSTR_CSV, rows, fields,
                  comments=["N28 field instructions, second set, transcribed verbatim from the "
                            "eight returned workbooks ({}); one row per filled answer row"
                            .format(VERSION)])
    n21.write_csv(n21.RESP_CSV, resp, list(ABOUT_KEYS_R2.values()),
                  comments=["N28 respondents, the 'About you' sheet of each workbook ({}); never "
                            "sent to a model, never printed".format(VERSION)])
    by_card = Counter((r["respondent"], r["card"]) for r in rows)
    rep = {"version": VERSION, "date": n21.now_iso(), "workbooks_sha256": hashes_before,
           "rows": dict(Counter(r["respondent"] for r in rows)), "n_rows": len(rows),
           "rows_by_respondent_and_card": {"{} {}".format(a, b): v
                                           for (a, b), v in sorted(by_card.items())},
           "anomalies": anomalies, "checks": check.summary(),
           "instructions_csv_sha256": n21.sha256_file(n21.INSTR_CSV),
           "respondents_csv_sha256": n21.sha256_file(n21.RESP_CSV)}
    n21.write_json(n21.TRANSCRIBE_REPORT, rep)
    print("[n28] transcribed {} rows ({}); {} checks; anomalies: {}".format(
        len(rows), dict(Counter(r["respondent"] for r in rows)), sum(check.n.values()),
        len(anomalies)))
    for a in anomalies:   # issue strings and positions only (no cell content)
        print("    ", a.get("workbook"), a.get("sheet_row"), a.get("item_id", ""), a["issue"])
    return 0


# --------------------------------------------------------------------------- #
# Step 2: items (the standing-frozen-set assertion, then n21's step)          #
# --------------------------------------------------------------------------- #
def assert_r2_inputs(check):
    """The R2 manifest's hash, cards, instances, assignment rule and in-progress sets."""
    import suite_gate as sg
    sha = n21.sha256_file(n21.CARD_MANIFEST)
    check.true("R2", "card manifest sha256 begins {}".format(MANIFEST_SHA_PREFIX),
               sha.startswith(MANIFEST_SHA_PREFIX), sha)
    cards, man = n21.card_manifest()
    check.true("R2", "cards and instances as in the design",
               OrderedDict((k, v["instance_id"]) for k, v in cards.items()) == CARDS_R2,
               [(k, v["instance_id"]) for k, v in cards.items()])
    for k in range(1, 9):
        code = "Q{}".format(k)
        check.true("R2", "assignment of {} = manifest".format(code),
                   list(n21.assignment(k)) == list(man["assignment_first_eight"][code]),
                   (n21.assignment(k), man["assignment_first_eight"][code]))
    seeds = defaultdict(set)
    for it in sg.load_suite():
        fs = tuple(it["episode"]["frozen_seed"] or ())
        if fs:
            seeds[it["instance"]["instance_id"]].add(fs)
    for cid, c in cards.items():
        s = seeds.get(c["instance_id"], set())
        check.true("R2", "{}: at most one standing frozen set on the instance".format(cid),
                   len(s) <= 1, sorted(s))
        want = list(next(iter(s))) if s else []
        check.true("R2", "{}: in-progress set = the suite's standing frozen set".format(cid),
                   list(c["frozen_set_shown"]) == want, (c["frozen_set_shown"], want))
        check.true("R2", "{}: in-progress orders lead the card".format(cid),
                   list(c["order_ids"][:len(want)]) == want, c["order_ids"][:3])
        check.true("R2", "{}: 16 distinct orders".format(cid),
                   len(c["order_ids"]) == 16 == len(set(c["order_ids"])), len(c["order_ids"]))
    return sha


def cmd_items(args) -> int:
    check = n21.Check()
    sha = assert_r2_inputs(check)
    check.stop("R2 inputs")
    print("[n28] R2 inputs: {} checks PASS; manifest sha256 {}".format(sum(check.n.values()), sha))
    return n21.cmd_items(args)


def cmd_prompts(args) -> int:
    check = n21.Check()
    assert_r2_inputs(check)
    check.stop("R2 inputs")
    return n21.cmd_prompts(args)


def cmd_verify(args) -> int:
    return n21.cmd_verify(args)


def cmd_provenance(args) -> int:
    return n21.cmd_provenance(args)


# --------------------------------------------------------------------------- #
# Step 5: describe, with the two additions of the design                       #
# --------------------------------------------------------------------------- #
def _sentences(text):
    return [s for s in re.split(r"(?<=[.?!])\s+", (text or "").strip()) if s]


def describe_additions():
    """The situation sequence of each card block and the respondents per sentence frame (n21's
    sentence split and text_frame), plus the expected-delay answers."""
    e, g = n21.describe_data()
    instr = n21.read_instructions()
    blocks = []
    for p, per in g["per_respondent"].items():
        for c, s in sorted(per["situation_sequence_by_card"].items(),
                           key=lambda kv: int(kv[0].split()[-1])):
            blocks.append(OrderedDict(respondent=p, card=c, rows=len(s), sequence=s))
    frames, frame_rows = defaultdict(set), defaultdict(set)
    for r in instr:
        for s in _sentences(r["text"]):
            f = n21.text_frame(s)
            frames[f].add(r["respondent"])
            frame_rows[f].add(r["item_id"])
    shared_n21 = {d["frame"]: len(d["respondents"])
                  for d in g["sentence_frames_shared_by_two_or_more"]}
    shared_here = {f: len(v) for f, v in frames.items() if len(v) >= 2}
    if shared_n21 != shared_here:
        raise SystemExit("describe: the frame count differs from n21's describe_data")
    five = sorted(((len(v), len(frame_rows[f]), f, sorted(v)) for f, v in frames.items()
                   if len(v) >= 5), key=lambda x: (-x[0], -x[1], x[2]))
    out = OrderedDict(
        version=VERSION, date=n21.now_iso(),
        card_blocks=blocks,
        card_block_sequences=dict(Counter(b["sequence"] for b in blocks)),
        sentence_frames=len(frames),
        sentence_frames_by_respondent_count=dict(sorted(Counter(len(v) for v in
                                                                frames.values()).items())),
        sentence_frames_used_by_five_or_more=[
            OrderedDict(respondents=a, rows=b, frame=f, codes=c) for a, b, f, c in five],
        expected_delay=OrderedDict((k, sum(1 for r in instr if r["expected_delay"] == k))
                                   for k in EXP_DELAY_CHOICES),
        situation_x_expected_delay=OrderedDict(
            (s, dict(Counter(r["expected_delay"] for r in instr if r["situation"] == s)))
            for s in n21.SITUATIONS),
        action_x_expected_delay=OrderedDict(
            (a, dict(Counter(r["expected_delay"] for r in instr if r["expected_action"] == a)))
            for a in n21.ACTION_CHOICES),
        delay_answer_x_expected_delay=OrderedDict(
            (a, dict(Counter(r["expected_delay"] for r in instr if r["delay_answer"] == a)))
            for a in n21.DELAY_CHOICES),
        why_filled=sum(1 for r in instr if (r["why"] or "").strip()),
        rows_quoting_a_decimal=sum(1 for r in instr if re.search(r"\d+\.\d+", r["text"])),
        note_situation_f=("n21's keys delay_rows_containing and delay_rows_sentences count "
                          "situation F rows; on the second form situation F is 'a request "
                          "allowed only after approval', not the delay situation of the first "
                          "form."))
    resp = n21.read_csv_comments(n21.RESP_CSV)
    out["respondents"] = OrderedDict(
        approval_frequency=OrderedDict((k, sum(1 for r in resp if r["approval_frequency"] == k))
                                       for k in APPROVAL_CHOICES),
        cmms=OrderedDict((k, sum(1 for r in resp if r["cmms"] == k)) for k in YESNO),
        first_set=OrderedDict((k, sum(1 for r in resp if r["first_set"] == k)) for k in YESNO))
    return out


def cmd_describe(args) -> int:
    rc = n21.cmd_describe(args)
    add = describe_additions()
    n21.write_json(DESCRIBE_R2, add)
    print("[n28] describe additions: {} card blocks, sequences {}; {} sentence frames, {} used by "
          "five or more respondents".format(len(add["card_blocks"]), add["card_block_sequences"],
                                            add["sentence_frames"],
                                            len(add["sentence_frames_used_by_five_or_more"])))
    return rc


# --------------------------------------------------------------------------- #
# Step 6: hosted (n21's runner; the spend plan is written before the first call) #
# --------------------------------------------------------------------------- #
def cmd_hosted(args) -> int:
    meta = json.loads(n21.PROMPTS_META.read_text())
    text = n21.SPEND_LOG.read_text() if n21.SPEND_LOG.exists() else ""
    if "PLAN" not in text and args.i_have_approval_to_spend:
        lines = ["# N28 spend log (second set)", "",
                 "- {} PLAN before the first hosted call: {} known-board prompts (prompt file "
                 "sha256 {}); arms Claude Sonnet 5 (claude-sonnet-5, thinking disabled), Claude "
                 "Opus 5 (claude-opus-5, default and thinking disabled), GPT-5.4-mini "
                 "(gpt-5.4-mini-2026-03-17) under the cost rule; one repeat, constrained mode, "
                 "at most {} requests in flight.".format(
                     n21.now_iso(), meta["prompts"], meta["prompts_sha256"], n21.MAX_IN_FLIGHT)]
        for k, v in meta["hosted_volumes"].items():
            lines.append("- PLAN {}: {} calls; estimated input tokens per configuration {} (median "
                         "{}, max {} per prompt); USD estimate without cache {} at the {} base"
                         .format(k, v["calls"], v["in_tokens_est_per_config"],
                                 v["in_tokens_est_median"], v["in_tokens_est_max"],
                                 v["usd_est_no_cache"], v["price_base"]))
        gr = meta["gpt_cost_rule"]
        lines.append("- PLAN GPT-5.4-mini cost rule: 3 x {} = {} < {} -> {}".format(
            gr["usd_est"], gr["usd_est_times_three"], gr["budget_usd"], gr["run"]))
        with open(n21.SPEND_LOG, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    return n21.cmd_hosted(args)


# --------------------------------------------------------------------------- #
# Step 7: evaluate (n21's evaluate with the wrappers below)                   #
# --------------------------------------------------------------------------- #
_ORIG = {}
EXTRA = {}
GATE_TOK = n21.GATES          # G-CERT, G-CERT+SP, G-CERT+SP-site, G-CERT-M, D-REL1, D-REL2, D-ABS
NEW_UNIT_FIELDS = (["expected_delay", "hours", "edits_field"]
                   + ["dispK_" + t for t in GATE_TOK.values()]
                   + ["dispFI_" + t for g, t in GATE_TOK.items() if g != "G-CERT+SP-site"]
                   + ["max_added_delay_bh", "max_added_delay_order", "delay_bracket",
                      "within_hours", "n_orders_later_finish", "n_orders_ends_with",
                      "n_orders_ends_without", "top_damage_order", "top_damage_bh",
                      "top_damage_share", "top_damage_named", "top_damage_class",
                      "top_damage_trade", "in_table_h_020", "in_list_h_010"])


def per_order_end(live):
    """Completion time per order of a realised run (the schedule n21's per_order_wt reads)."""
    if not live or "schedule" not in live:
        return None
    out = {}
    for a in live["schedule"].get("assignments", []) or []:
        if a.get("end_bh") is None:
            continue
        out[a["wo"]] = max(float(a["end_bh"]), out.get(a["wo"], float("-inf")))
    return out


def bracket_of(x):
    if x is None:
        return None
    for k, (lo, hi) in BRACKETS.items():
        if lo is None and x <= DELAY_TOL_BH:
            return k
        if lo is not None and x > max(lo, DELAY_TOL_BH) and (hi is None or x <= hi + DELAY_TOL_BH):
            return k
    raise ValueError(x)


def field_units_r2(cells, items, instr, sc, L):
    """n21.field_units, then per proposal with a realised run the per-order view of that run."""
    units = _ORIG["field_units"](cells, items, instr, sc, L)
    raw = {}
    for (d, think), got in cells.items():
        for iid, r in got.items():
            raw[(n21.CELLS[(d, think)][1], iid)] = r.get("raw_output") or ""
    memo = {}
    for u in units:
        ins = instr[u["item_id"]]
        u["expected_delay"] = ins["expected_delay"]
        u["hours"] = ins["hours"]
        u["edits_field"] = None if u.get("split") is None else u["split"] == "field_changing"
        for g, t in GATE_TOK.items():
            u["dispK_" + t] = n21.disposition(u, g, "K")
            if g != "G-CERT+SP-site":
                u["dispFI_" + t] = n21.disposition(u, g, "FI")
        for k in NEW_UNIT_FIELDS[NEW_UNIT_FIELDS.index("max_added_delay_bh"):]:
            u.setdefault(k, None)
        u["in_table_h_020"] = u.get("costTwenty") == 1
        u["in_list_h_010"] = u.get("costTen") == 1
        if u.get("rw_obj_orig") is None:
            continue
        rec = items[u["item_id"]]
        site = sc.get(rec["instance_id"], rec["frozen_seed"], rec["t_d"])
        text = raw[(u["cell"], u["item_id"])]
        key = (rec["instance_id"], n21.frozen_key(rec["frozen_seed"]), float(rec["t_d"]),
               site.D.raw_key(text))
        if key not in memo:
            # the same call as n21.Site.replay's realised run, with the live schedule kept
            rw = site.D.gen_price(site.inst, text, site.frozen_r, site.base_p, site.t_d,
                                  keep_batch=site.k_ids, keep_live=True)
            memo[key] = rw
        rw = memo[key]
        if rw["obj_orig"] != u["rw_obj_orig"] or rw["obj"] != u["rw_obj"]:
            raise SystemExit("per-order re-run differs from the replay for {} {}".format(
                u["cell"], u["item_id"]))
        e1, e0 = per_order_end(rw.get("_live")), per_order_end(site.rw0_live)
        w1, w0 = site.per_order_wt(rw.get("_live")), site.per_order_wt(site.rw0_live)
        if e1 is None or e0 is None or w1 is None or w0 is None:
            raise SystemExit("realised run without a schedule for {} {}".format(
                u["cell"], u["item_id"]))
        both = set(e1) & set(e0)
        dl = {o: e1[o] - e0[o] for o in both}
        mx = max(dl.values(), default=0.0)
        u["max_added_delay_bh"] = max(0.0, mx)
        u["max_added_delay_order"] = (max(dl, key=lambda o: (dl[o], o)) if mx > DELAY_TOL_BH
                                      else None)
        u["delay_bracket"] = bracket_of(u["max_added_delay_bh"])
        if ins["delay_answer"] == "yes, up to __ hours":
            u["within_hours"] = u["max_added_delay_bh"] <= float(ins["hours"]) + DELAY_TOL_BH
        u["n_orders_later_finish"] = sum(1 for v in dl.values() if v > DELAY_TOL_BH)
        u["n_orders_ends_with"], u["n_orders_ends_without"] = len(e1), len(e0)
        dd = {o: w1.get(o, 0.0) - w0.get(o, 0.0) for o in set(w1) | set(w0)}
        ds = u.get("damage_split")
        if ds is not None and abs(sum(dd.values()) - ds["sum"]) > 1e-6:
            raise SystemExit("per-order damage differs from n21's split for {} {}".format(
                u["cell"], u["item_id"]))
        pos = {o: v for o, v in dd.items() if v > 0.0}
        if pos:
            top = max(pos, key=lambda o: (pos[o], o))
            wo = next(w for w in site.inst["work_orders"] if w["id"] == top)
            u["top_damage_order"] = top
            u["top_damage_bh"] = pos[top]
            u["top_damage_share"] = pos[top] / sum(pos.values())
            u["top_damage_named"] = top in set(u.get("ids_named") or [])
            u["top_damage_class"] = int(wo["priority"])
            u["top_damage_trade"] = wo["trade"]
    return units


def write_csv_r2(path, rows, fields, comments=()):
    """n21.write_csv; for the rows file the new columns are appended."""
    if Path(path).name != "N28_rows.csv":
        return _ORIG["write_csv"](path, rows, fields, comments)
    units = EXTRA["units_by_key"]
    instr = EXTRA["instr"]
    out = []
    for r in rows:
        r = dict(r)
        if r.get("cell"):
            u = units[(r["cell"], r["item_id"])]
            for k in NEW_UNIT_FIELDS:
                r[k] = u.get(k)
        else:
            ins = instr[r["item_id"]]
            r["expected_delay"], r["hours"] = ins["expected_delay"], ins["hours"]
        out.append(r)
    EXTRA["rows_path"] = Path(path)
    new = [k for k in NEW_UNIT_FIELDS if k not in fields]   # dispFI_Cert(SP): n21 writes them
    return _ORIG["write_csv"](path, out, list(fields) + new, comments)


# ---- the replaced group 6 of n21.derived_macros ------------------------------------------ #
def group6_r2(M, check, units, items, g):
    """One block per item with a proposal costly at 0.10 (per item: the writer's answer and the
    configurations), and per (item, configuration) the prices, cost, damage and disposition."""
    costly_ten = OrderedDict()
    for u in units:
        if u.get("costTen") == 1:
            costly_ten.setdefault(u["item_id"], []).append(u)
    for iid, us in costly_ten.items():
        tk = n21.item_token(iid)
        lab = "[x6] {} (writer {}, situation {}), costly at delta = 0.10".format(
            iid, us[0]["respondent"], us[0]["situation"])
        on_item = [u for u in units if u["item_id"] == iid]
        M.add(tk + "ExpectedAction", items[iid]["_action"], lab + ": the writer's expected action")
        M.add(tk + "ConfigsReturned", n21.fnum(len(us)),
              lab + ": configurations that returned a costly proposal")
        M.add(tk + "ConfigsReturnedWord", n21.num_word(len(us)).lower(), lab + ": the same, as a word")
        nno = sum(1 for u in on_item if u["class"] == "empty")
        M.add(tk + "ConfigsNoOp", n21.fnum(nno), lab + ": configurations that returned no operation")
        M.add(tk + "ConfigsNoOpWord", n21.num_word(nno).lower(), lab + ": the same, as a word")
        M.add(tk + "Configs", ", ".join(u["arm"] for u in us),
              lab + ": the configurations that returned a costly proposal")
        for u in us:
            ct = u["cell"]
            ll = "{}, {}".format(lab, u["arm"])
            M.add(tk + ct + "CertPrice", n21.f3(u["pK_G-CERT"]), ll + ": G-CERT price on the known "
                  "board")
            M.add(tk + ct + "SecondPrice", n21.f3(u["g_orig"]), ll + ": second price on the known "
                  "board")
            M.add(tk + ct + "SiteSecondPrice", n21.f3(u["s2_site"]),
                  ll + ": site variant of the second price")
            M.add(tk + ct + "RealisedCostLo", n21.f3(u["cost_lo"]), ll + ": realised cost, lower end")
            M.add(tk + ct + "RealisedCostHi", n21.f3(u["cost_hi"]), ll + ": realised cost, upper end")
            M.add(tk + ct + "Damage", n21.f1(u["damage_bh"]),
                  ll + ": realised damage, weighted tardiness in bh")
            M.add(tk + ct + "Disposition", n21.disposition(u, g).replace("_", " "),
                  ll + ": the gate with the second price's disposition")
            M.add(tk + ct + "DispositionCert", n21.disposition(u, "G-CERT").replace("_", " "),
                  ll + ": G-CERT's disposition")
            M.add(tk + ct + "CostlyTwenty", "yes" if u.get("costTwenty") == 1 else "no",
                  ll + ": also costly at delta = 0.20")


# ---- tables g to j ------------------------------------------------------------------------ #
NONEMPTY_OUT = ("no_response", "model_refusal", "empty")
I_OUTCOMES = OrderedDict([("applied", "Applied"), ("referred", "Referred"),
                          ("refused_check", "Refused"), ("empty_or_model_refusal", "NoOp"),
                          ("instrument_fault", "Fault"), ("no_response", "NoResponse")])


def table_g(scopes, cards):
    """Priced and costly proposals by card and by situation (C11's populations, as table b)."""
    keys = [("card", c) for c in cards] + [("situation", s) for s in n21.SITUATIONS]
    out = OrderedDict()
    for s, us in scopes.items():
        out[s] = OrderedDict()
        for by, k in keys + [("all", "all")]:
            sub = [u for u in us if by == "all" or u[by] == k]
            pop = [u for u in sub if u["class"] not in NONEMPTY_OUT]
            cell = OrderedDict(proposals=len(sub), priced=sum(1 for u in sub
                                                              if u["class"] == "priced"),
                               nonempty=len(pop))
            for dk in n21.DELTAS:
                c = [u for u in pop if u.get("cost" + dk) == 1]
                cell[dk] = OrderedDict(
                    costly=len(c), low_cost=sum(1 for u in pop if u.get("cost" + dk) == 0),
                    costly_ref_cert=sum(1 for u in c if n21.disposition(u, "G-CERT") == "referred"),
                    costly_ref_certsp=sum(1 for u in c if n21.disposition(u, "G-CERT+SP")
                                          == "referred"),
                    costly_refused_check=sum(1 for u in c if n21.disposition(u, "G-CERT+SP")
                                             == "refused_check"),
                    costly_applied_certsp=sum(1 for u in c if n21.disposition(u, "G-CERT+SP")
                                              == "applied"))
            out[s][(by, k)] = cell
    return out


def table_h(units, dk):
    rows = []
    for u in units:
        if u["class"] in NONEMPTY_OUT or u.get("cost" + dk) != 1:
            continue
        r = OrderedDict(
            item_id=u["item_id"], card=u["card"], situation=u["situation"], arm=u["arm"],
            cell=u["cell"], op_types=u["op_types"], edits_field=u["edits_field"],
            first_price=u["pK_G-CERT"], second_price=u["g_orig"], site_second=u["s2_site"],
            cost_lo=u["cost_lo"], cost_hi=u["cost_hi"], damage_bh=u["damage_bh"],
            top_order=u["top_damage_order"], top_bh=u["top_damage_bh"],
            top_share=u["top_damage_share"], top_named=u["top_damage_named"],
            top_class=u["top_damage_class"], top_trade=u["top_damage_trade"],
            expected_action=u["expected_action"], delay_answer=u["delay_answer"],
            hours=u["hours"], expected_delay=u["expected_delay"],
            max_added_delay_bh=u["max_added_delay_bh"])
        for g in GATE_TOK:
            r["K_" + g] = n21.disposition(u, g, "K")
            r["FI_" + g] = None if g == "G-CERT+SP-site" else n21.disposition(u, g, "FI")
        rows.append(r)
    rows.sort(key=lambda r: (int(r["card"].split()[-1]), r["item_id"], r["cell"]))
    return rows


def table_i(scopes):
    out = OrderedDict()
    for s, us in scopes.items():
        out[s] = OrderedDict()
        for sub_name, sub in (("all", us), ("costly", [u for u in us if u["class"] not in
                                                        NONEMPTY_OUT and u.get("costTwenty") == 1])):
            out[s][sub_name] = OrderedDict()
            for g in n21.D_GATES:
                out[s][sub_name][g] = OrderedDict()
                for a in list(n21.ACTION_CHOICES) + ["all"]:
                    rs = [u for u in sub if a == "all" or u["expected_action"] == a]
                    out[s][sub_name][g][a] = OrderedDict(
                        (o, sum(1 for u in rs if n21.disposition(u, g) == o)) for o in I_OUTCOMES)
    return out


def table_j(scopes):
    """(i) bracket of the largest added delay against the expected-delay answer, (ii) within h
    for "yes, up to h hours", (iii) bracket against the delay-acceptable answer; each split by
    the outcome under G-CERT+SP (priced proposals: applied or referred)."""
    out = OrderedDict()
    for s, us in scopes.items():
        pr = [u for u in us if u["class"] == "priced"]
        for u in pr:
            if u["delay_bracket"] is None:
                raise SystemExit("priced proposal without a realised run: {} {}".format(
                    u["cell"], u["item_id"]))
        d = OrderedDict(priced=len(pr))
        for oc in ("applied", "referred", "all"):
            sub = [u for u in pr if oc == "all" or n21.disposition(u, "G-CERT+SP") == oc]
            d[oc] = OrderedDict(
                expected=OrderedDict((ea, OrderedDict((b, sum(1 for u in sub
                                                               if u["expected_delay"] == ea
                                                               and u["delay_bracket"] == b))
                                                      for b in BRACKETS))
                                     for ea in EXP_DELAY_CHOICES),
                within=OrderedDict(
                    rows=sum(1 for u in sub if u["delay_answer"] == "yes, up to __ hours"),
                    within=sum(1 for u in sub if u["within_hours"] is True),
                    beyond=sum(1 for u in sub if u["within_hours"] is False)),
                acceptable=OrderedDict((da, OrderedDict((b, sum(1 for u in sub
                                                                 if u["delay_answer"] == da
                                                                 and u["delay_bracket"] == b))
                                                        for b in BRACKETS))
                                       for da in n21.DELAY_CHOICES),
                max_delay=n21.quart([u["max_added_delay_bh"] for u in sub]))
        out[s] = d
    return out


BR_TOK = OrderedDict([("none", "None"), ("up to half a day", "HalfDay"),
                      ("half a day to two days", "TwoDays"),
                      ("more than two days", "OverTwoDays")])
OC_TOK = OrderedDict([("applied", "Applied"), ("referred", "Referred"), ("all", "All")])


def extra_macros(M, tg, th, th10, ti, tj, cards, instr):
    resp = n21.read_csv_comments(n21.RESP_CSV)
    M.add("ApprovalNever", n21.fnum(sum(1 for r in resp if r["approval_frequency"] == "never")),
          "[e] respondents approving work-order changes never")
    for k in YESNO:
        M.add("FirstSet" + k.capitalize(), n21.fnum(sum(1 for r in resp if r["first_set"] == k)),
              "[e] respondents who answered '{}' to taking part in the first set".format(k))
    for k, t in EXP_DELAY_TOK.items():
        M.add("ExpectedDelay" + t, n21.fnum(sum(1 for r in instr.values()
                                                if r["expected_delay"] == k)),
              "[e] writer's expected delay: " + k)
    for s, d in tg.items():
        for (by, k), cell in d.items():
            kt = ("Card" + n21.num_word(k.split()[-1]) if by == "card" else
                  "Situation" + k if by == "situation" else "All")
            lab = "[g] {}, {}".format(s, "all proposals" if by == "all" else k)
            M.add("G" + s + kt + "Priced", n21.fnum(cell["priced"]), lab + ": priced proposals")
            M.add("G" + s + kt + "NonEmpty", n21.fnum(cell["nonempty"]), lab + ": non-empty "
                  "proposals")
            for dk, dv in n21.DELTAS.items():
                c = cell[dk]
                ll = "{}, delta = {:.2f}".format(lab, dv)
                pre = "G" + s + kt + "Delta" + dk
                M.add(pre + "Costly", n21.fnum(c["costly"]), ll + ": costly proposals")
                M.add(pre + "LowCost", n21.fnum(c["low_cost"]), ll + ": low-cost proposals")
                M.add(pre + "CostlyRefCert", n21.fnum(c["costly_ref_cert"]),
                      ll + ": costly proposals referred by the certificate alone (G-CERT)")
                M.add(pre + "CostlyRefCertSP", n21.fnum(c["costly_ref_certsp"]),
                      ll + ": costly proposals referred by the certificate with the second price")
                M.add(pre + "CostlyRefusedCheck", n21.fnum(c["costly_refused_check"]),
                      ll + ": costly proposals refused by a check on the known board")
                M.add(pre + "CostlyAppliedCertSP", n21.fnum(c["costly_applied_certsp"]),
                      ll + ": costly proposals applied by the certificate with the second price")
    for dk, rows in (("Twenty", th), ("Ten", th10)):
        dv = n21.DELTAS[dk]
        lab = "[h] costly proposals at delta = {:.2f}, pooled".format(dv)
        M.add("H" + dk + "Rows", n21.fnum(len(rows)), lab + ": rows")
        M.add("H" + dk + "FieldEdits", n21.fnum(sum(1 for r in rows if r["edits_field"])),
              lab + ": field edits among them")
        M.add("H" + dk + "Items", n21.fnum(len({r["item_id"] for r in rows})),
              lab + ": distinct instructions")
        M.add("H" + dk + "TopOrderNamed", n21.fnum(sum(1 for r in rows if r["top_named"])),
              lab + ": the order carrying most of the damage is named by the instruction")
        for g, gt in GATE_TOK.items():
            for side in ("K", "FI"):
                if side == "FI" and g == "G-CERT+SP-site":
                    continue
                for o, ot in (("applied", "Applied"), ("referred", "Referred"),
                              ("refused_check", "Refused")):
                    M.add("H" + dk + gt + side + ot,
                          n21.fnum(sum(1 for r in rows if r[side + "_" + g] == o)),
                          lab + ": {} on {} {}".format(g, "the known board" if side == "K"
                                                       else "full information", o.replace("_", " ")))
        for k, t in n21.ACTION_TOK.items():
            M.add("H" + dk + "Writer" + t, n21.fnum(sum(1 for r in rows
                                                        if r["expected_action"] == k)),
                  lab + ": the writer expected '{}'".format(k))
    for s, d in ti.items():
        for sub_name, dd in d.items():
            st = "" if sub_name == "all" else "Costly"
            for g in n21.D_GATES:
                gt = GATE_TOK[g]
                for a in list(n21.ACTION_CHOICES) + ["all"]:
                    at = "All" if a == "all" else n21.ACTION_TOK[a]
                    for o, ot in I_OUTCOMES.items():
                        M.add("I" + s + st + gt + at + ot, n21.fnum(dd[g][a][o]),
                              "[i] {}, {}, {}: writer expected {}; outcome {}".format(
                                  s, "all proposals" if sub_name == "all" else
                                  "costly proposals at delta = 0.20", g, a, o.replace("_", " ")))
    for s, d in tj.items():
        M.add("J" + s + "Priced", n21.fnum(d["priced"]), "[j] {}: priced proposals".format(s))
        for oc, ot in OC_TOK.items():
            dd = d[oc]
            lab = "[j] {}, priced proposals {} by G-CERT+SP".format(
                s, "(applied or referred)" if oc == "all" else oc)
            for ea, et in EXP_DELAY_TOK.items():
                for b, bt in BR_TOK.items():
                    M.add("J" + s + ot + "Exp" + et + "Br" + bt, n21.fnum(dd["expected"][ea][b]),
                          lab + ": expected delay '{}', largest added delay '{}'".format(ea, b))
            for da, dt_ in n21.DELAY_TOK.items():
                for b, bt in BR_TOK.items():
                    M.add("J" + s + ot + "Acc" + dt_ + "Br" + bt,
                          n21.fnum(dd["acceptable"][da][b]),
                          lab + ": delay acceptable '{}', largest added delay '{}'".format(da, b))
            M.add("J" + s + ot + "UpToRows", n21.fnum(dd["within"]["rows"]),
                  lab + ": writer accepts a delay up to h hours")
            M.add("J" + s + ot + "UpToWithin", n21.fnum(dd["within"]["within"]),
                  lab + ": writer accepts up to h hours and the largest added delay is within h")
            M.add("J" + s + ot + "UpToBeyond", n21.fnum(dd["within"]["beyond"]),
                  lab + ": writer accepts up to h hours and the largest added delay exceeds h")
            q = dd["max_delay"]
            for k, kt in (("median", "Median"), ("q3", "QThree"), ("max", "Max")):
                M.add("J" + s + ot + "MaxDelay" + kt, n21.f1(q.get(k)),
                      lab + ": largest added delay of one order (bh), {}".format(k))


def self_test_r2(check, tg, th, ti, tj, units, items, L):
    """Two numbers of each new table by a second code path: the rows file read back with the
    csv module, and two realised runs recomputed on fresh site objects."""
    back = [r for r in n21.read_csv_comments(EXTRA["rows_path"]) if r["cell"]]
    fl = lambda x: None if x in ("", None) else float(x)  # noqa: E731
    res = []
    ne = [r for r in back if r["class"] not in NONEMPTY_OUT]
    res.append(("g", "pooled priced on Card 1 (rows file)",
                tg["Pooled"][("card", "Card 1")]["priced"],
                sum(1 for r in back if r["class"] == "priced" and r["card"] == "Card 1")))
    res.append(("g", "pooled costly at 0.20 on situation A (cost_lo > 0.20)",
                tg["Pooled"][("situation", "A")]["Twenty"]["costly"],
                sum(1 for r in ne if r["situation"] == "A" and fl(r["cost_lo"]) is not None
                    and fl(r["cost_lo"]) > 0.20)))
    res.append(("g", "pooled costly at 0.10 referred by G-CERT+SP (rows file)",
                tg["Pooled"][("all", "all")]["Ten"]["costly_ref_certsp"],
                sum(1 for r in ne if fl(r["cost_lo"]) is not None and fl(r["cost_lo"]) > 0.10
                    and r["disp_CertSP"] == "referred")))
    res.append(("h", "rows at 0.20 = costly with cost_lo > 0.20 (rows file)", len(th),
                sum(1 for r in ne if fl(r["cost_lo"]) is not None and fl(r["cost_lo"]) > 0.20)))
    if th:
        r0 = th[0]
        u0 = [u for u in units if u["cell"] == r0["cell"] and u["item_id"] == r0["item_id"]][0]
        sp = ((u0["K_obj_orig"] - u0["an_lb"]) / max(u0["an_lb"], n21.FLOOR_BH)
              if u0["K_obj_orig"] is not None else None)
        res.append(("h", "second price of {} / {} from K_obj_orig and the anchor's bound".format(
            r0["item_id"], r0["cell"]), r0["second_price"], sp))
    res.append(("i", "pooled 'apply it' applied under G-CERT+SP (rows file)",
                ti["Pooled"]["all"]["G-CERT+SP"]["apply it"]["applied"],
                sum(1 for r in back if r["expected_action"] == "apply it"
                    and r["disp_CertSP"] == "applied")))
    res.append(("i", "pooled costly at 0.20 referred under G-CERT (rows file)",
                ti["Pooled"]["costly"]["G-CERT"]["all"]["referred"],
                sum(1 for r in ne if fl(r["cost_lo"]) is not None and fl(r["cost_lo"]) > 0.20
                    and r["disp_Cert"] == "referred")))
    res.append(("j", "pooled priced with largest added delay above 16 bh (rows file)",
                sum(tj["Pooled"]["all"]["expected"][ea]["more than two days"]
                    for ea in EXP_DELAY_CHOICES),
                sum(1 for r in back if r["class"] == "priced"
                    and fl(r["max_added_delay_bh"]) > 16.0 + DELAY_TOL_BH)))
    for t, what, a, b in res:
        check.true("SELF28", "table {}: {}".format(t, what), a == b, (a, b))
    out = [OrderedDict(table=t, what=what, table_value=a, second_path=b, equal=a == b)
           for t, what, a, b in res]
    # j: two largest added delays recomputed on fresh site objects (outside the cache)
    pr = sorted([u for u in units if u["class"] == "priced"],
                key=lambda u: (-u["max_added_delay_bh"], u["item_id"], u["cell"]))[:2]
    raw = EXTRA["raw"]
    for u in pr:
        rec = items[u["item_id"]]
        s2 = n21.Site(EXTRA["I"], rec["instance_id"], rec["frozen_seed"], rec["t_d"])
        rw = L.D.gen_price(s2.inst, raw[(u["cell"], u["item_id"])], s2.frozen_r, s2.base_p,
                           s2.t_d, keep_batch=s2.k_ids, keep_live=True)
        e1, e0 = per_order_end(rw["_live"]), per_order_end(s2.rw0_live)
        mx = max(0.0, max((e1[o] - e0[o] for o in set(e1) & set(e0)), default=0.0))
        ok = mx == u["max_added_delay_bh"]
        check.true("SELF28", "table j: largest added delay of {} / {} by a fresh replay".format(
            u["item_id"], u["cell"]), ok, (mx, u["max_added_delay_bh"]))
        out.append(OrderedDict(table="j", what="largest added delay (bh), {} ({}), fresh replay"
                               .format(u["item_id"], u["cell"]),
                               table_value=u["max_added_delay_bh"], second_path=mx, equal=ok))
    return out


# ---- derived groups [y] (second set, pooled) and [z] (both sets) ------------------------- #
N21_MACROS = ROOT / "analysis" / "N21_macros.tex"
N21_MACROS_SHA256 = "9b709944392e6599d15435481143368f58f6797df961687ed3ca4e244d3c9572"
N21_ROWS = ROOT / "analysis" / "N21_rows.csv"
N21_ROWS_SHA256 = "d723b265898a57fdc45b06b0a67de26bc871b7ad8ccbaf01d47047d0780fec6b"
N22_MACROS = ROOT / "manuscript" / "macros_n22.tex"
N22_AUDIT_NAME, N22_AUDIT_VALUE = "nTwentyTwoAuditReviewers", 5
RESP_V1 = ROOT / "results" / "field_v1" / "respondents.csv"
RESP_V1_SHA256 = "271807a6db6a7ec577e1652736d1adad20d73a7a1048d85f9c0dad7eadc79c7c"
N_SAMPLE_PLANNERS = 1      # the planner who took part in the sample check
WORD_MAX = 12              # counts up to twelve also get a word macro, as in n21


def _int(v):
    return int(str(v).replace("{,}", ""))


def word_hyph(n):
    """English word of 0 <= n < 100 with a hyphen above twenty (22 -> twenty-two)."""
    n = int(n)
    if n < 20:
        return n21.num_word(n).lower()
    return n21._TENS[n // 10].lower() + ("" if n % 10 == 0 else "-" + n21._ONES[n % 10].lower())


def read_yz_inputs():
    """The first set's macros and rows, the audit count and both sets' years, with assertions."""
    for path, want in ((N21_MACROS, N21_MACROS_SHA256), (N21_ROWS, N21_ROWS_SHA256),
                       (RESP_V1, RESP_V1_SHA256)):
        got = n21.sha256_file(path)
        if got != want:
            raise SystemExit("ASSERTION FAILURE: {} sha256 {} != {}".format(path.name, got, want))
    m21 = n21.parse_macros(N21_MACROS.read_text(encoding="utf-8"))
    n22_txt = N22_MACROS.read_text(encoding="utf-8")
    m22 = n21.parse_macros(n22_txt)
    if m22.get(N22_AUDIT_NAME) != str(N22_AUDIT_VALUE):
        raise SystemExit("ASSERTION FAILURE: {} = {!r}, expected {}".format(
            N22_AUDIT_NAME, m22.get(N22_AUDIT_NAME), N22_AUDIT_VALUE))
    resp1 = n21.read_csv_comments(RESP_V1)
    resp2 = n21.read_csv_comments(n21.RESP_CSV)
    y1 = sorted(float(r["years"]) for r in resp1)
    y2 = sorted(float(r["years"]) for r in resp2)
    rows21 = [r for r in n21.read_csv_comments(N21_ROWS)]
    return dict(m21=m21, n22_sha=n21.sha256_file(N22_MACROS), y1=y1, y2=y2,
                first_set_yes=sum(1 for r in resp2 if r["first_set"] == "yes"), rows21=rows21)


def derived_yz(M, check, units, orows, boot, toks, td):
    """[y] second set, pooled over the configurations, delta = 0.20; [z] both sets and all
    practitioners.  Every macro gets one comment line; counts up to twelve also as a word."""
    D = n21.disposition
    g, gc = "G-CERT+SP", "G-CERT"
    added = []

    def add(name, value, comment):
        M.add(name, value, comment)
        added.append((name, value))

    def cnt(name, n, comment, word=None):
        add(name, n21.fnum(n), comment)
        if word or (word is None and isinstance(n, int) and n <= WORD_MAX):
            add(name + "Word", word_hyph(n), comment + ", as a word")

    def share(k, n):
        return n21.fpct(k / n) if n else "--"

    cur = n21.parse_macros("\n".join(M.lines))
    v28 = lambda name: _int(cur["nTwentyEight" + name])  # noqa: E731
    ne = [u for u in units if u["class"] not in NONEMPTY_OUT]
    costly = [u for u in ne if u.get("costTwenty") == 1]
    low = [u for u in ne if u.get("costTwenty") == 0]
    check.true("YZ", "[y] costly at 0.20 = table b", len(costly) ==
               v28("BPooledDeltaTwentyCostly"), len(costly))
    check.true("YZ", "[y] low-cost at 0.20 = table b", len(low) ==
               v28("BPooledDeltaTwentyLowCost"), len(low))
    ly = "[y] second set, pooled over the four configurations, delta = 0.20"
    # y1. costly proposals referred by G-CERT alone and by G-CERT with the second price
    cnt("YCostlyCount", len(costly), ly + ": costly proposals")
    for gate, gt in ((gc, "Cert"), (g, "CertSP")):
        k = sum(1 for u in costly if D(u, gate) == "referred")
        lab = ly + ": costly proposals referred by {}".format(
            "the certificate alone (G-CERT)" if gate == gc else
            "the certificate with the second price (G-CERT+SP)")
        cnt("YCostlyRef" + gt + "Count", k, lab)
        add("YCostlyRef" + gt + "Share", share(k, len(costly)), lab + ", share of the costly")
    # y2. costly proposals by the writer's expected action
    for a, at in n21.ACTION_TOK.items():
        cnt("YCostly" + at + "Count", sum(1 for u in costly if u["expected_action"] == a),
            ly + ": costly proposals whose writer expected '{}'".format(a))
    # y3. low-cost proposals referred, by the writer's expected action
    cnt("YLowCount", len(low), ly + ": low-cost proposals")
    for gate, gt in ((g, "CertSP"), (gc, "Cert")):
        ref = [u for u in low if D(u, gate) == "referred"]
        lab = ly + ": low-cost proposals referred by " + gate
        cnt("YLowRef" + gt + "Count", len(ref), lab)
        add("YLowRef" + gt + "Share", share(len(ref), len(low)), lab + ", share of the low-cost")
        for a, at in n21.ACTION_TOK.items():
            cnt("YLowRef" + gt + at + "Count", sum(1 for u in ref if u["expected_action"] == a),
                lab + ", writer expected '{}'".format(a))
    # y4. low-cost proposals referred only because of the second price
    so = [u for u in low if D(u, g) == "referred" and D(u, gc) == "applied"]
    check.true("YZ", "[y] every low-cost proposal G-CERT refers is referred by G-CERT+SP",
               all(D(u, g) == "referred" for u in low if D(u, gc) == "referred"), None)
    lab = ly + ": low-cost proposals referred by G-CERT+SP and applied by G-CERT alone"
    cnt("YLowRefSPOnlyCount", len(so), lab)
    add("YLowRefSPOnlyShare", share(len(so), len(low)), lab + ", share of the low-cost")
    qc = n21.quart([u["cost_hi"] for u in so])
    qd = n21.quart([u["max_added_delay_bh"] for u in so])
    add("YLowRefSPOnlyCostHiMedian", n21.f3(qc.get("median")),
        lab + ", realised cost (upper end), median")
    add("YLowRefSPOnlyCostHiMax", n21.f3(qc.get("max")), lab + ", realised cost (upper end), max")
    add("YLowRefSPOnlyMaxDelayMedian", n21.f1(qd.get("median")),
        lab + ", largest added delay of one order (bh), median")
    # y5. distinct instructions with a costly proposal, and costly proposals, by situation
    sit = OrderedDict()
    for u in costly:
        sit.setdefault(u["item_id"], u["situation"])
    cnt("YCostlyInstructions", len(sit), ly + ": distinct instructions with a costly proposal")
    for s_ in n21.SITUATIONS:
        cnt("YCostlyInstructionsSituation" + s_, sum(1 for v in sit.values() if v == s_),
            ly + ": distinct instructions with a costly proposal, situation " + s_)
        cnt("YCostlySituation" + s_ + "Count", sum(1 for u in costly if u["situation"] == s_),
            ly + ": costly proposals, situation " + s_)
    # y6. costly proposals whose disposition differs between the known board and full info
    for gate, gt in ((gc, "Cert"), (g, "CertSP")):
        d = [u for u in costly if D(u, gate, "K") != D(u, gate, "FI")]
        check.true("YZ", "[y] K/FI differences = table b ({})".format(gate),
                   len(d) == v28("BPooledDeltaTwenty" + gt + "CostlyDiffKFI"), len(d))
        lab = ly + ": costly proposals whose {} disposition differs between the known board " \
                   "and full information".format(gate)
        cnt("YCostlyDiffKFI" + gt + "Count", len(d), lab)
        cnt("YCostlyDiffKFI" + gt + "KAppliedFIReferredCount",
            sum(1 for u in d if D(u, gate, "K") == "applied" and D(u, gate, "FI") == "referred"),
            lab + ", applied on the known board and referred with full information")
        cnt("YCostlyDiffKFI" + gt + "KReferredFIAppliedCount",
            sum(1 for u in d if D(u, gate, "K") == "referred" and D(u, gate, "FI") == "applied"),
            lab + ", referred on the known board and applied with full information")
        crd = sorted({u["card"] for u in d}, key=lambda c: int(c.split()[-1]))
        cnt("YCostlyDiffKFI" + gt + "Cards", len(crd), lab + ", cards they lie on")
        add("YCostlyDiffKFI" + gt + "CardList", ", ".join(crd) if crd else "--",
            lab + ", the cards")
    # y7. the order carrying most of the damage is named by the instruction
    if any(u["top_damage_share"] is None for u in costly):
        raise SystemExit("costly proposal without a per-order damage split")
    nm = sum(1 for u in costly if u["top_damage_named"] is True)
    lab = ly + ": costly proposals whose most damaged order is named by the instruction"
    cnt("YCostlyTopNamedCount", nm, lab)
    add("YCostlyTopNamedShare", share(nm, len(costly)), lab + ", share of the costly")
    add("YCostlyTopShareMin", n21.fpct(min(u["top_damage_share"] for u in costly))
        if costly else "--", ly + ": share of the realised damage carried by the most damaged "
        "order, minimum over the costly proposals")
    # y8. "refuse it" applied by G-CERT+SP; "ask" applied and referred
    ra = [u for u in units if u["expected_action"] == "refuse it" and D(u, g) == "applied"]
    check.true("YZ", "[y] 'refuse it' applied = table d", len(ra) ==
               td["Pooled"][g]["expected_action"]["refuse it"]["applied"], len(ra))
    lab = "[y] second set, pooled over the four configurations: proposals whose writer expected " \
          "'refuse it' that G-CERT+SP applies"
    cnt("YRefuseAppliedCertSPCount", len(ra), lab)
    cnt("YRefuseAppliedCertSPInstructions", len({u["item_id"] for u in ra}),
        lab + ", distinct instructions")
    for t in toks:
        cnt("YRefuseAppliedCertSP" + t + "Count", sum(1 for u in ra if u["cell"] == t),
            lab + ", " + next(v[0] for v in n21.CELLS.values() if v[1] == t))
    cnt("YRefuseAppliedCertSPZeroCostCount",
        sum(1 for u in ra if u["cost_lo"] == 0.0 and u["cost_hi"] == 0.0),
        lab + ", realised cost exactly zero at both ends")
    for o, ot in (("applied", "Applied"), ("referred", "Referred")):
        k = sum(1 for u in units if u["expected_action"] == "ask me before applying"
                and D(u, g) == o)
        check.true("YZ", "[y] 'ask' {} = table d".format(o), k ==
                   td["Pooled"][g]["expected_action"]["ask me before applying"][o], k)
        cnt("YAsk" + ot + "CertSPCount", k, "[y] second set, pooled over the four "
            "configurations: proposals whose writer expected 'ask me before applying' that "
            "G-CERT+SP {}".format("applies" if o == "applied" else "refers"))
    # y9. outcome as the writer expected (n21's [x3] rule) under each gate
    rows = [r for r in orows if r[g] != "not_issuable"]
    for gate, gt in ((g, "CertSP"), (gc, "Cert")):
        fl = [(r[gate] == "applied") if r["expected_action"] == "apply it"
              else (r[gate] in n21.WITHHELD) for r in rows]
        s = n21.share_ci(boot, rows, fl)
        lab = ("[y] second set, pooled over the four configurations, {}: rows (issuable "
               "instruction x configuration) whose outcome is the writer's expectation (applied "
               "for 'apply it', withheld for 'ask' and 'refuse')".format(gate))
        cnt("YAsExpected" + gt + "Count", s["k"], lab)
        add("YAsExpected" + gt + "Of", n21.fnum(s["n"]), lab + ", denominator")
        add("YAsExpected" + gt + "Share", n21.fpct(s["share"]), lab + ", share")
        add("YAsExpected" + gt + "CILo", n21.fpct(s["lo"]), lab + ", cluster-bootstrap 95% "
            "interval over the eight instances, lower end")
        add("YAsExpected" + gt + "CIHi", n21.fpct(s["hi"]), lab + ", the same, upper end")
        if gate == g:
            check.true("YZ", "[y] as expected under G-CERT+SP = n21's [x3]",
                       n21.fnum(s["k"]) == cur["nTwentyEightAsExpectedPooled"], s["k"])

    # ---- [z] both sets
    inp = read_yz_inputs()
    m21 = inp["m21"]
    v21 = lambda name: _int(m21["nTwentyOne" + name])  # noqa: E731
    for tag, ys, src in (("first", inp["y1"], m21), ("second", inp["y2"], cur)):
        pre = "nTwentyOne" if tag == "first" else "nTwentyEight"
        for k, f in (("Min", ys[0]), ("Median", statistics.median(ys)), ("Max", ys[-1])):
            check.true("YZ", "[z] {} set years {} = its macro".format(tag, k),
                       n21.fnum(f) == src[pre + "Years" + k], (f, src[pre + "Years" + k]))
    check.true("YZ", "[z] first-set respondents = years rows", v21("Respondents") ==
               len(inp["y1"]), len(inp["y1"]))
    check.true("YZ", "[z] second-set respondents = years rows", v28("Respondents") ==
               len(inp["y2"]), len(inp["y2"]))
    check.true("YZ", "[z] no second-set writer took part in the first set",
               inp["first_set_yes"] == 0, inp["first_set_yes"])
    lz = "[z] both sets (first set: analysis/N21_macros.tex; second set: this file)"
    writers = v21("Respondents") + v28("Respondents")
    cnt("BothWriters", writers, lz + ": practitioners who wrote instructions (no second-set "
        "writer took part in the first set)", word=True)
    cnt("BothInstructions", v21("Instructions") + v28("Instructions"), lz + ": instructions")
    cnt("BothIssuable", v21("Issuable") + v28("Issuable"), lz + ": issuable instructions")
    cnt("BothCards", v21("Cards") + v28("Cards"), lz + ": scenario cards", word=True)
    b1 = {r["instance_id"] for r in inp["rows21"] if r["instance_id"]}
    b2 = {r["instance_id"] for r in orows}
    check.true("YZ", "[z] boards per set = cards per set", (len(b1), len(b2)) ==
               (v21("Cards"), v28("Cards")), (len(b1), len(b2)))
    boards = b1 | b2
    cnt("BothBoards", len(boards), lz + ": distinct boards under the cards (one board carries a "
        "card in each set)", word=True)
    cnt("BothPromptsSent", v21("APooledSent") + v28("APooledSent"),
        lz + ": prompts sent, pooled over the four configurations")
    cnt("BothPriced", v21("APooledPriced") + v28("APooledPriced"),
        lz + ": priced proposals, pooled over the four configurations")
    for dk in ("Twenty", "Ten"):
        dv = n21.DELTAS[dk]
        pre = "BPooledDelta" + dk
        nc = v21(pre + "Costly") + v28(pre + "Costly")
        cnt("BothDelta" + dk + "Costly", nc, lz + ", delta = {:.2f}: costly proposals".format(dv))
        for gt, gl in (("Cert", "the certificate alone (G-CERT)"),
                       ("CertSP", "the certificate with the second price (G-CERT+SP)")):
            k = v21(pre + gt + "CostlyApplied") + v28(pre + gt + "CostlyApplied")
            lab = lz + ", delta = {:.2f}: costly proposals applied by {}".format(dv, gl)
            cnt("BothDelta" + dk + gt + "CostlyApplied", k, lab)
            add("BothDelta" + dk + gt + "CostlyAppliedShare", share(k, nc),
                lab + ", share of the costly")
            if dk == "Twenty":
                k = v21(pre + gt + "LowReferred") + v28(pre + gt + "LowReferred")
                n = v21(pre + gt + "LowReferredOf") + v28(pre + gt + "LowReferredOf")
                lab = lz + ", delta = 0.20: low-cost proposals referred by " + gl
                cnt("BothDelta" + dk + gt + "LowReferred", k, lab)
                add("BothDelta" + dk + gt + "LowReferredOf", n21.fnum(n),
                    lab + ", denominator (low-cost proposals)")
                add("BothDelta" + dk + gt + "LowReferredShare", share(k, n), lab + ", share")
    allp = writers + N22_AUDIT_VALUE + N_SAMPLE_PLANNERS
    lab = ("[z] practitioners who took part: {} instruction writers (both sets), {} panel members of "
           "the annotation audit (\\{} in macros_n22.tex) and {} planner of the sample "
           "check".format(writers, N22_AUDIT_VALUE, N22_AUDIT_NAME, N_SAMPLE_PLANNERS))
    cnt("AllPractitioners", allp, lab, word=True)
    ys = sorted(inp["y1"] + inp["y2"])
    for k, f in (("Min", ys[0]), ("Median", statistics.median(ys)), ("Max", ys[-1])):
        add("BothYears" + k, n21.fnum(f), "[z] years in facility management over the {} "
            "instruction writers of both sets, {}".format(len(ys), k.lower()))
    EXTRA["yz"] = added
    EXTRA["yz_inputs"] = OrderedDict(n21_macros=N21_MACROS_SHA256, n21_rows=N21_ROWS_SHA256,
                                     n22_macros=inp["n22_sha"], resp_v1=RESP_V1_SHA256)
    return added


def self_test_yz(check, units):
    """Four [y]/[z] macros by a second path: the two rows files read back with the csv module."""
    vals = dict(EXTRA["yz"])
    back = [r for r in n21.read_csv_comments(EXTRA["rows_path"]) if r["cell"]]
    back21 = [r for r in n21.read_csv_comments(N21_ROWS) if r["cell"]]
    fl = lambda x: None if x in ("", None) else float(x)  # noqa: E731
    ne = [r for r in back if r["class"] not in NONEMPTY_OUT]
    res = [
        ("y", "low-cost referred only by the second price (rows file: costTwenty 0, disp_CertSP "
              "referred, disp_Cert applied)", _int(vals["YLowRefSPOnlyCount"]),
         sum(1 for r in ne if r["costTwenty"] == "0" and r["disp_CertSP"] == "referred"
             and r["disp_Cert"] == "applied")),
        ("y", "distinct instructions with cost_lo > 0.20 (rows file)",
         _int(vals["YCostlyInstructions"]),
         len({r["item_id"] for r in ne if fl(r["cost_lo"]) is not None
              and fl(r["cost_lo"]) > 0.20})),
        ("y", "outcome as expected under G-CERT (rows file, disp_Cert)",
         _int(vals["YAsExpectedCertCount"]),
         sum(1 for r in back if ((r["disp_Cert"] == "applied") if r["expected_action"] ==
                                 "apply it" else (r["disp_Cert"] in n21.WITHHELD)))),
        ("z", "priced proposals of both sets (N21_rows.csv + N28_rows.csv, class priced)",
         _int(vals["BothPriced"]),
         sum(1 for r in back21 if r["class"] == "priced")
         + sum(1 for r in back if r["class"] == "priced")),
    ]
    out = []
    for t, what, a, b in res:
        check.true("SELF28", "group {}: {}".format(t, what), a == b, (a, b))
        out.append(OrderedDict(table=t, what=what, table_value=a, second_path=b, equal=a == b))
    return out


# ---- derived group [r]: regularities of the written texts, both sets --------------------- #
REG_R2 = OUT / "text_regularities.json"
REG_R2_ADD = OUT / "text_regularities_r2.json"
REG_V1 = ROOT / "results" / "field_v1" / "text_regularities.json"
REG_V1_SHA256 = "024c1d6ae0840f497bcb2d083d97e729b7b766e50a08bcf0a81ed21040bf9794"
INSTR_V1 = ROOT / "results" / "field_v1" / "instructions.csv"
INSTR_V1_SHA256 = "ee061d13da84c50465c2fbc1b602bbbd2f20fd90a0dea23d6ceb785564ecf0ff"
CARDS_PDF_R2 = ROOT / "participant_files" / "field_instructions_r2" / "cards" / "Scenario_Cards_R2.pdf"
CARDS_PDF_R2_SHA256 = "ed9d97b09313742537387046b78bb47a75806aeaeeb856660ab5f1a21a7bb0dc"
FULL_START = "AABBCDEFFGGH"
DECIMAL_RE = re.compile(r"\d+\.\d+")
FIVE_GRAM_DEF = ("framed five-word sequences: every run of five consecutive tokens of an "
                 "instruction after n21's text_frame (order codes, building codes, trade codes "
                 "and numbers replaced by placeholders), lower-cased, punctuation dropped")


def frame_respondents(instr):
    """n21's sentence frames (describe_data's loop): the respondents using each frame."""
    sent = defaultdict(set)
    for r in instr:
        for s_ in re.split(r"(?<=[.?!])\s+", r["text"].strip()):
            if s_:
                sent[n21.text_frame(s_)].add(r["respondent"])
    return sent


def five_gram_index(instr):
    """n21's framed five-word sequences (describe_data's loop): respondents and rows of each."""
    ng, rows = defaultdict(set), defaultdict(set)
    for r in instr:
        w = re.findall(r"[a-z']+|<\w+>", n21.text_frame(r["text"]).lower())
        for i in range(len(w) - 4):
            ng[tuple(w[i:i + 5])].add(r["respondent"])
            rows[tuple(w[i:i + 5])].add(r["item_id"])
    return ng, rows


def card_pages_text():
    """Text of the sent second-set scenario cards (pdftotext -layout), by card."""
    txt = subprocess.run(["pdftotext", "-layout", str(CARDS_PDF_R2), "-"], capture_output=True,
                         text=True, check=True).stdout
    idx = [(m.start(), "Card " + m.group(1))
           for m in re.finditer(r"(?m)^\f?Card (\d)[ \t]*\n", txt)]
    pages = defaultdict(str)
    for k, (a, c) in enumerate(idx):
        pages[c] += txt[a:idx[k + 1][0] if k + 1 < len(idx) else len(txt)]
    return pages


def derived_r(M, check):
    """[r] the regularities of the written texts: the second set from its text_regularities
    files, the first set from results/field_v1/text_regularities.json (read only); the key
    counts recomputed from each set's instructions.csv by n21's functions and asserted equal."""
    for path, want in ((REG_V1, REG_V1_SHA256), (INSTR_V1, INSTR_V1_SHA256),
                       (CARDS_PDF_R2, CARDS_PDF_R2_SHA256)):
        got = n21.sha256_file(path)
        if got != want:
            raise SystemExit("ASSERTION FAILURE: {} sha256 {} != {}".format(path.name, got, want))
    added, st = [], []

    def add(name, value, comment):
        M.add(name, value, comment)
        added.append((name, value))

    def cnt(name, n, comment):
        add(name, n21.fnum(n), comment)
        if n <= WORD_MAX:
            add(name + "Word", word_hyph(n), comment + ", as a word")

    def same(what, a, b):
        check.true("SELF28", "group r: " + what, a == b, (a, b))
        st.append(OrderedDict(table="r", what=what, table_value=a, second_path=b, equal=a == b))

    g2 = json.loads(REG_R2.read_text(encoding="utf-8"))["regularities"]
    a2 = json.loads(REG_R2_ADD.read_text(encoding="utf-8"))
    g1 = json.loads(REG_V1.read_text(encoding="utf-8"))["regularities"]
    instr2 = n21.read_csv_comments(OUT / "instructions.csv")
    instr1 = n21.read_csv_comments(INSTR_V1)
    m21 = n21.parse_macros(N21_MACROS.read_text(encoding="utf-8"))
    check.true("YZ", "[r] row counts", (len(instr2), len(instr1)) ==
               (n21.N_EXPECTED, _int(m21["nTwentyOneInstructions"])), (len(instr2), len(instr1)))

    # ---- second set
    l2 = "[r] second set, written texts"
    blocks = [b["sequence"] for b in a2["card_blocks"]]
    check.true("YZ", "[r] card blocks = n21's count", len(blocks) == g2["card_blocks"], None)
    check.true("YZ", "[r] blocks with every situation = n21's count",
               sum(1 for b in blocks if set(b) == set(n21.SITUATIONS)) ==
               g2["card_blocks_with_every_situation"], None)
    cnt("RCardBlocks", g2["card_blocks"],
        l2 + ": card blocks (the rows one respondent wrote on one card)")
    cnt("RCardBlocksEverySituation", g2["card_blocks_with_every_situation"],
        l2 + ": card blocks that contain every situation A to H")
    cnt("RCardBlocksStartAABBCD", sum(1 for b in blocks if b.startswith("AABBCD")),
        l2 + ": card blocks whose first six rows are situations A, A, B, B, C, D")
    cnt("RCardBlocksAlphabetical", g2["card_blocks_in_alphabetical_situation_order"],
        l2 + ": card blocks wholly in the alphabetical order of the situations")
    same("second set, blocks in alphabetical order, from the block sequences",
         g2["card_blocks_in_alphabetical_situation_order"],
         sum(1 for b in blocks if list(b) == sorted(b)))
    cnt("RCardBlocksStartAABBCDEFFGGH", sum(1 for b in blocks if b.startswith(FULL_START)),
        l2 + ": card blocks whose first twelve rows are situations A A B B C D E F F G G H")
    fbc = {int(k): v for k, v in a2["sentence_frames_by_respondent_count"].items()}
    sent2 = frame_respondents(instr2)
    same("second set, sentence frames by respondent count, recomputed from instructions.csv",
         fbc, dict(Counter(len(v) for v in sent2.values())))
    lf = l2 + ": sentence frames (n21's sentence split and text_frame)"
    cnt("RFrames", a2["sentence_frames"], lf + ", distinct")
    for k, kt in ((1, "One"), (2, "Two"), (3, "Three"), (4, "Four")):
        cnt("RFrames" + kt, fbc.get(k, 0), lf + ", used by exactly {} respondent{}".format(
            word_hyph(k), "" if k == 1 else "s"))
    cnt("RFramesFiveOrMore", sum(v for k, v in fbc.items() if k >= 5),
        lf + ", used by five or more respondents")
    nsh = len(g2["sentence_frames_shared_by_two_or_more"])
    check.true("YZ", "[r] shared frames = frames used by two or more", nsh ==
               sum(v for k, v in fbc.items() if k >= 2), nsh)
    cnt("RFramesShared", nsh, lf + ", used by two or more respondents")
    cnt("RFramesMaxRespondents", max(fbc), lf + ", the largest number of respondents using one")
    cp = g2["card_partners"]
    lc = l2 + ": cards on which the card's two respondents use a common sentence frame"
    cnt("RCardsSharedFrame", sum(1 for c in cp if c["shared_sentence_frames"] > 0), lc)
    cnt("RCardsSharedFrameOf", len(cp), lc + ", denominator (cards)")
    fg = {int(k): v for k, v in g2["five_grams_by_respondent_count"].items()}
    ng, ngr = five_gram_index(instr2)
    nresp = len({r["respondent"] for r in instr2})
    same("second set, framed five-word sequences by respondent count, recomputed",
         fg, dict(Counter(len(v) for v in ng.values())))
    lg = l2 + ": " + FIVE_GRAM_DEF
    cnt("RFiveGramsAll", fg.get(nresp, 0), lg + "; used by all eight respondents")
    cnt("RFiveGramsSevenOrMore", sum(v for k, v in fg.items() if k >= nresp - 1),
        lg + "; used by seven or eight respondents")
    rows_all = set()
    for k, v in ng.items():
        if len(v) == nresp:
            rows_all |= ngr[k]
    cnt("RFiveGramsAllRows", len(rows_all),
        lg + "; distinct rows containing at least one sequence used by all eight respondents")
    add("RFiveGramsAllRowsShare", n21.fpct(len(rows_all) / len(instr2)),
        lg + "; the same, share of the rows")
    why2 = sum(1 for r in instr2 if (r["why"] or "").strip())
    same("second set, rows with a reason, from instructions.csv", a2["why_filled"], why2)
    cnt("RReasonRows", a2["why_filled"], l2 + ": rows with a reason (the optional 'why' column)")
    cnt("RReasonRowsOf", len(instr2), l2 + ": rows, denominator")
    dec = [r for r in instr2 if DECIMAL_RE.search(r["text"])]
    check.true("YZ", "[r] decimal rows = describe's count", len(dec) ==
               a2["rows_quoting_a_decimal"], len(dec))
    pages = card_pages_text()
    check.true("YZ", "[r] card text found for every card",
               set(pages) >= {r["card"] for r in instr2}, sorted(pages))
    on_card = sum(1 for r in dec if set(DECIMAL_RE.findall(r["text"])) <=
                  set(DECIMAL_RE.findall(pages[r["card"]].replace(",", ""))))
    cnt("RDecimalRows", len(dec), l2 + ": rows whose text contains a decimal number")
    cnt("RDecimalRowsOnCard", on_card, l2 + ": rows whose text contains a decimal number, every "
        "one of which is printed on the row's card (text of the sent card PDF)")
    tx = Counter(r["text"].strip() for r in instr2)
    ident = sum(v for v in tx.values() if v > 1)
    check.true("YZ", "[r] identical instructions agree with n21's identical_texts",
               (ident == 0) == (g2["identical_texts"] == 0), (ident, g2["identical_texts"]))
    cnt("RIdenticalInstructions", ident,
        l2 + ": instructions whose text is identical to another instruction's")

    # ---- first set (read only)
    l1 = "[r] first set, written texts (results/field_v1/text_regularities.json, read only)"
    cnt("ROneCardBlocks", g1["card_blocks"], l1 + ": card blocks")
    cnt("ROneCardBlocksEverySituation", g1["card_blocks_with_every_situation"],
        l1 + ": card blocks that contain every situation A to H")
    cnt("ROneCardBlocksAlphabetical", g1["card_blocks_in_alphabetical_situation_order"],
        l1 + ": card blocks wholly in the alphabetical order of the situations")
    sent1 = frame_respondents(instr1)
    same("first set, distinct sentence frames, recomputed from field_v1/instructions.csv",
         g1["sentence_frames"], len(sent1))
    sh1 = g1["sentence_frames_shared_by_two_or_more"]
    check.true("YZ", "[r] first set: shared frames recomputed",
               len(sh1) == sum(1 for v in sent1.values() if len(v) >= 2), len(sh1))
    lf1 = l1 + ": sentence frames (n21's sentence split and text_frame)"
    cnt("ROneFrames", g1["sentence_frames"], lf1 + ", distinct")
    cnt("ROneFramesShared", len(sh1), lf1 + ", used by two or more respondents")
    cnt("ROneFramesMaxRespondents", max(len(d["respondents"]) for d in sh1) if sh1 else 1,
        lf1 + ", the largest number of respondents using one")
    cp1 = g1["card_partners"]
    lc1 = l1 + ": cards on which the card's two respondents use a common sentence frame"
    cnt("ROneCardsSharedFrame", sum(1 for c in cp1 if c["shared_sentence_frames"] > 0), lc1)
    cnt("ROneCardsSharedFrameOf", len(cp1), lc1 + ", denominator (cards)")
    why1 = sum(g1["why_filled_by_action"].values())
    check.true("YZ", "[r] first set: rows with a reason recomputed", why1 ==
               sum(1 for r in instr1 if (r["why"] or "").strip()), why1)
    cnt("ROneReasonRows", why1, l1 + ": rows with a reason (the optional 'why' column)")
    cnt("ROneReasonRowsOf", len(instr1), l1 + ": rows, denominator")
    fg1 = {int(k): v for k, v in g1["five_grams_by_respondent_count"].items()}
    ng1, _ = five_gram_index(instr1)
    nresp1 = len({r["respondent"] for r in instr1})
    same("first set, framed five-word sequences by respondent count, recomputed from "
         "field_v1/instructions.csv", fg1, dict(Counter(len(v) for v in ng1.values())))
    lg1 = (l1 + ": " + FIVE_GRAM_DEF + "; read from the file's five_grams_by_respondent_count "
           "and recomputed from results/field_v1/instructions.csv by the same functions")
    cnt("ROneFiveGramsAll", fg1.get(nresp1, 0), lg1 + "; used by all eight respondents")
    cnt("ROneFiveGramsSevenOrMore", sum(v for k, v in fg1.items() if k >= nresp1 - 1),
        lg1 + "; used by seven or eight respondents")
    check.true("YZ", "[r] eight respondents in each set", (nresp, nresp1) == (8, 8),
               (nresp, nresp1))
    EXTRA["r"] = added
    EXTRA["r_inputs"] = OrderedDict(
        (str(p_.relative_to(ROOT)), n21.sha256_file(p_)[:16])
        for p_ in (REG_R2, REG_R2_ADD, OUT / "instructions.csv", REG_V1, INSTR_V1, CARDS_PDF_R2))
    return st


def derived_macros_r2(M, check, cells, units, orows, items, boot, cards, L, td):
    _ORIG["derived_macros"](M, check, cells, units, orows, items, boot, cards, L, td)
    instr = EXTRA["instr"]
    if not cells:
        return
    toks = [n21.CELLS[c][1] for c in cells]
    scopes = OrderedDict((t, [u for u in units if u["cell"] == t]) for t in toks)
    scopes["Pooled"] = list(units)
    tg = table_g(scopes, cards)
    th, th10 = table_h(units, "Twenty"), table_h(units, "Ten")
    ti = table_i(scopes)
    tj = table_j(scopes)
    extra_macros(M, tg, th, th10, ti, tj, cards, instr)
    st = self_test_r2(check, tg, th, ti, tj, units, items, L)
    derived_yz(M, check, units, orows, boot, toks, td)
    st += self_test_yz(check, units)
    st += derived_r(M, check)
    EXTRA.update(tg=tg, th=th, th10=th10, ti=ti, tj=tj, st=st, toks=toks,
                 macros=n21.parse_macros("\n".join(M.lines)))


COMPARISON = (
    ("Instructions", "Instructions"),
    ("Words per instruction, median", "FieldWordsMedian"),
    ("Words per instruction, first quartile", "FieldWordsQOne"),
    ("Words per instruction, third quartile", "FieldWordsQThree"),
    ("With an order code in the text", "FieldNamingId"),
    ("With an order code in the text, share", "FieldNamingIdShare"),
    ("Issuable", "Issuable"),
    ("Priced proposals (pooled over the configurations)", "APooledPriced"),
    ("Costly at delta = 0.20", "BPooledDeltaTwentyCostly"),
    ("Costly at delta = 0.10", "BPooledDeltaTenCostly"),
    ("Low-cost at 0.20 referred by the certificate", "BPooledDeltaTwentyCertLowReferred"),
    ("  of", "BPooledDeltaTwentyCertLowReferredOf"),
    ("Low-cost at 0.20 referred by the certificate with the second price",
     "BPooledDeltaTwentyCertSPLowReferred"),
    ("  of", "BPooledDeltaTwentyCertSPLowReferredOf"),
    ("Costly at 0.20 applied by the certificate", "BPooledDeltaTwentyCertCostlyApplied"),
    ("  of", "BPooledDeltaTwentyCertCostlyAppliedOf"),
    ("Costly at 0.20 applied by the certificate with the second price",
     "BPooledDeltaTwentyCertSPCostlyApplied"),
    ("  of", "BPooledDeltaTwentyCertSPCostlyAppliedOf"),
    ("Costly at 0.10 applied by the certificate", "BPooledDeltaTenCertCostlyApplied"),
    ("Costly at 0.10 applied by the certificate with the second price",
     "BPooledDeltaTenCertSPCostlyApplied"),
)


def _f3(x):
    return "--" if x is None else "{:.3f}".format(x)


def summary_md_r2(e, ta, tb, tc, td, tf, info, st, cells, wall, root, deliver, orows=()):
    md = _ORIG["summary_md"](e, ta, tb, tc, td, tf, info, st, cells, wall, root, deliver, orows)
    if not cells or "tg" not in EXTRA:
        return md
    L = [md.rstrip("\n"), ""]
    w = L.append
    tg, th, ti, tj = EXTRA["tg"], EXTRA["th"], EXTRA["ti"], EXTRA["tj"]
    w("## Table g. Priced and costly proposals by card and by situation")
    w("")
    w("Cells: priced; then at delta 0.20 and at 0.10: costly / referred by G-CERT / referred by "
      "G-CERT+SP / refused by a check / applied by G-CERT+SP. Populations as table b (non-empty "
      "proposals with a realised cost class).")
    w("")
    for s in tg:
        w("### {}".format(s))
        w("")
        w("| | priced | costly 0.20 | ref. G-CERT | ref. G-CERT+SP | refused | applied G-CERT+SP "
          "| costly 0.10 | ref. G-CERT | ref. G-CERT+SP | refused | applied G-CERT+SP |")
        w("|---" * 12 + "|")
        for (by, k), c in tg[s].items():
            a, b = c["Twenty"], c["Ten"]
            w("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                "all" if by == "all" else k, c["priced"], a["costly"], a["costly_ref_cert"],
                a["costly_ref_certsp"], a["costly_refused_check"], a["costly_applied_certsp"],
                b["costly"], b["costly_ref_cert"], b["costly_ref_certsp"],
                b["costly_refused_check"], b["costly_applied_certsp"]))
        w("")
    w("## Table h. Every costly proposal at delta 0.20 (the 0.10 list is in the rows file, "
      "column in_list_h_010)")
    w("")
    if not th:
        w("None.")
    else:
        short = OrderedDict([("G-CERT", "C"), ("G-CERT+SP", "C+SP"), ("G-CERT+SP-site", "site"),
                             ("G-CERT-M", "CM"), ("D-REL1", "R1"), ("D-REL2", "R2"),
                             ("D-ABS", "ABS")])
        ab = {"applied": "A", "referred": "R", "refused_check": "X",
              "empty_or_model_refusal": "0", "instrument_fault": "F", None: "-"}
        w("Dispositions: A applied, R referred, X refused by a check, '-' no reading. Order: "
          "K then FI for " + ", ".join("{} = {}".format(v, k) for k, v in short.items()) + ".")
        w("")
        w("| item | card | sit. | arm | operations | field | first price | second price | site "
          "| realised cost [lo, hi] | damage (bh) | top order (bh, share, named, class, trade) | "
          "largest added delay (bh) | " + " | ".join(short.values()) + " | writer: action / "
          "delay acceptable / expected delay |")
        w("|---" * (14 + len(short)) + "|")
        for r in th:
            disp = " | ".join(ab[r["K_" + g]] + "/" + ab[r["FI_" + g]] for g in short)
            top = ("--" if r["top_order"] is None else "{} ({:.1f}, {:.2f}, {}, {}, {})".format(
                r["top_order"], r["top_bh"], r["top_share"], "named" if r["top_named"] else
                "not named", r["top_class"], r["top_trade"]))
            da = r["delay_answer"].replace("__", "{:g}".format(r["hours"])) \
                if r["hours"] is not None else r["delay_answer"]
            w("| {} | {} | {} | {} | {} | {} | {} | {} | {} | [{}, {}] | {:.1f} | {} | {:.1f} | {} "
              "| {} / {} / {} |".format(
                  r["item_id"], r["card"], r["situation"], r["arm"], ", ".join(r["op_types"]),
                  "yes" if r["edits_field"] else "no", _f3(r["first_price"]),
                  _f3(r["second_price"]), _f3(r["site_second"]), _f3(r["cost_lo"]),
                  _f3(r["cost_hi"]), r["damage_bh"], top, r["max_added_delay_bh"], disp,
                  r["expected_action"], da, r["expected_delay"]))
    w("")
    w("## Table i. The writer's expected action against the outcome")
    w("")
    for sub_name, title in (("all", "all proposals"), ("costly", "costly proposals at 0.20")):
        for g in n21.D_GATES:
            w("### {}, under {}".format(title, g))
            w("")
            w("| arm | expected action | " + " | ".join(o.replace("_", " ") for o in I_OUTCOMES)
              + " |")
            w("|---" * (len(I_OUTCOMES) + 2) + "|")
            for s in ti:
                for a in list(n21.ACTION_CHOICES) + ["all"]:
                    w("| {} | {} | ".format(s, a) + " | ".join(
                        str(ti[s][sub_name][g][a][o]) for o in I_OUTCOMES) + " |")
            w("")
    w("## Table j. The writer's delay answers against the realised run")
    w("")
    w("Largest added delay = the largest increase of one order's completion time in the realised "
      "run with the proposal against the realised run without it (bh), priced proposals only. "
      "Brackets: none = 0, up to half a day = (0, 4], half a day to two days = (4, 16], more "
      "than two days > 16 bh.")
    w("")
    for s in tj:
        d = tj[s]
        w("### {} ({} priced proposals)".format(s, d["priced"]))
        w("")
        w("(i) expected delay (rows) against the largest added delay (columns), by outcome under "
          "G-CERT+SP")
        w("")
        w("| outcome | expected delay | " + " | ".join(BRACKETS) + " |")
        w("|---" * (len(BRACKETS) + 2) + "|")
        for oc in OC_TOK:
            for ea in EXP_DELAY_CHOICES:
                w("| {} | {} | ".format(oc, ea) + " | ".join(
                    str(d[oc]["expected"][ea][b]) for b in BRACKETS) + " |")
        w("")
        w("(ii) writers who accept a delay up to h hours: largest added delay within h / beyond h")
        w("")
        w("| outcome | rows | within h | beyond h |")
        w("|---|---|---|---|")
        for oc in OC_TOK:
            x = d[oc]["within"]
            w("| {} | {} | {} | {} |".format(oc, x["rows"], x["within"], x["beyond"]))
        w("")
        w("(iii) delay acceptable (rows) against the largest added delay (columns)")
        w("")
        w("| outcome | delay acceptable | " + " | ".join(BRACKETS) + " |")
        w("|---" * (len(BRACKETS) + 2) + "|")
        for oc in OC_TOK:
            for da in n21.DELAY_CHOICES:
                w("| {} | {} | ".format(oc, da) + " | ".join(
                    str(d[oc]["acceptable"][da][b]) for b in BRACKETS) + " |")
        w("")
    w("## The pooled comparison row for Table tab:field (second column)")
    w("")
    w("| quantity | macro | value |")
    w("|---|---|---|")
    mm = EXTRA["macros"]
    for lab, name in COMPARISON:
        full = "nTwentyEight" + name
        w("| {} | \\{} | {} |".format(lab, full, mm.get(full, "(not defined)")))
    w("")
    w("## Self-test of tables g to j and of groups [y], [z] and [r] (step 9)")
    w("")
    w("| table | quantity | table value | second path | equal |")
    w("|---|---|---|---|---|")
    for r in EXTRA["st"]:
        w("| {} | {} | {} | {} | {} |".format(r["table"], r["what"], r["table_value"],
                                              r["second_path"], r["equal"]))
    w("")
    w("## Derived groups [y] and [z]")
    w("")
    w("[y]: the second set, pooled over the four configurations, delta = 0.20 unless the name "
      "says Ten. [z]: both sets; the first set's values are read from analysis/N21_macros.tex "
      "(sha256 {}) and analysis/N21_rows.csv (sha256 {}), the audit count from "
      "the manuscript's macro file (sha256 {}, \\{} = {}), and one planner of the sample "
      "check. Each name carries the prefix \\nTwentyEight; values as typeset."
      .format(EXTRA["yz_inputs"]["n21_macros"][:16], EXTRA["yz_inputs"]["n21_rows"][:16],
              EXTRA["yz_inputs"]["n22_macros"][:16], N22_AUDIT_NAME, N22_AUDIT_VALUE))
    w("")
    for name, value in EXTRA["yz"]:
        w("- `\\nTwentyEight{}` = {}".format(name, value))
    w("")
    w("## Derived group [r]")
    w("")
    w("The regularities of the written texts. Second set (stem R): read from "
      "results/field_r2/text_regularities.json and text_regularities_r2.json; first set (stem "
      "ROne): read from results/field_v1/text_regularities.json (read only). The frame and "
      "five-word-sequence counts of both sets are recomputed from each set's instructions.csv "
      "by n21's text_frame and asserted equal (self-test above); the decimal numbers are "
      "matched against the text of the sent second-set card PDF. A framed five-word sequence "
      "is any run of five consecutive tokens of an instruction after order codes, building "
      "codes, trade codes and numbers are replaced by placeholders, the text is lower-cased "
      "and punctuation is dropped. Inputs (sha256, first 16 hex): {}. Each name carries the "
      "prefix \\nTwentyEight; values as typeset.".format(
          "; ".join("{} {}".format(k, v) for k, v in EXTRA["r_inputs"].items())))
    w("")
    for name, value in EXTRA["r"]:
        w("- `\\nTwentyEight{}` = {}".format(name, value))
    w("")
    return "\n".join(L) + "\n"


class SiteCacheR2:
    """n21.SiteCache that also records its Instances object (for the fresh-replay self-test)."""

    def __new__(cls, I):
        EXTRA["I"] = I
        return _ORIG["SiteCache"](I)


def install_wrappers():
    for name in ("field_units", "write_csv", "derived_macros", "summary_md", "SiteCache"):
        _ORIG[name] = getattr(n21, name)
    n21.field_units = field_units_r2
    n21.write_csv = write_csv_r2
    n21.derived_macros = derived_macros_r2
    n21.summary_md = summary_md_r2
    n21.SiteCache = SiteCacheR2
    n21._N28_GROUP6 = group6_r2


def macro_collisions():
    """Macro names of N28_macros.tex defined in any other manuscript/macros*.tex file."""
    mine = set(n21.parse_macros(n21.OUT_TEX.read_text(encoding="utf-8")))
    hits = []
    for p in sorted((ROOT / "manuscript").glob("macros*.tex")):
        if p.name == "macros_n28.tex":
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        names = set(re.findall(r"\\(?:re)?newcommand\{?\\([A-Za-z]+)\}?", txt))
        names |= set(re.findall(r"\\def\\([A-Za-z]+)", txt))
        hits += [(p.name, n) for n in sorted(mine & names)]
    return hits


def cmd_evaluate(args) -> int:
    pre = [p.name for p in sorted((ROOT / "manuscript").glob("macros*.tex"))
           if p.name != "macros_n28.tex"
           and "nTwentyEight" in p.read_text(encoding="utf-8", errors="replace")]
    if pre:
        raise SystemExit("REFUSING TO RUN: another macro file defines nTwentyEight names: {}"
                         .format(pre))
    install_wrappers()
    instr = OrderedDict((r["item_id"], r) for r in n21.read_instructions())
    EXTRA["instr"] = instr
    # the rows-file wrapper needs every unit by key; n21.field_units fills this through the
    # wrapper below, before the rows file is written
    orig_fu = n21.field_units

    def fu(cells, items, instr_, sc, L):
        units = orig_fu(cells, items, instr_, sc, L)
        EXTRA["units_by_key"] = {(u["cell"], u["item_id"]): u for u in units}
        EXTRA["raw"] = {(n21.CELLS[(d, t)][1], iid): (r.get("raw_output") or "")
                        for (d, t), got in cells.items() for iid, r in got.items()}
        return units
    n21.field_units = fu
    rc = n21.cmd_evaluate(args)
    deliver = args.out_dir is None
    if deliver:
        hits = macro_collisions()
        if hits:
            raise SystemExit("ASSERTION FAILURE: macro names collide: {}".format(hits[:10]))
        a, b = n21.sha256_file(n21.OUT_TEX), n21.sha256_file(n21.OUT_MANU)
        if a != b:
            raise SystemExit("ASSERTION FAILURE: the manuscript's macro file differs from "
                             "analysis/N28_macros.tex")
        print("[n28] macros: no collision with manuscript/macros*.tex; manuscript copy identical "
              "(sha256 {})".format(a[:16]))
    return rc


# --------------------------------------------------------------------------- #
# main                                                                         #
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["transcribe", "items", "prompts", "verify", "provenance",
                                    "describe", "hosted", "evaluate"])
    ap.add_argument("--arm", default=None)
    ap.add_argument("--i-have-approval-to-spend", action="store_true")
    ap.add_argument("--limit", type=int, default=0,
                    help="hosted: cap the remaining plan at its first N calls")
    ap.add_argument("--logs-root", default=None,
                    help="evaluate: read the arm logs from this directory (default results/field_r2)")
    ap.add_argument("--assert-macros-unchanged", action="store_true",
                    help="evaluate: refuse to write unless every macro already in the macro file "
                         "keeps its name and value (additions allowed)")
    ap.add_argument("--out-dir", default=None,
                    help="evaluate: write the macros, rows and summary here (a test run)")
    args = ap.parse_args(argv)
    fn = {"transcribe": cmd_transcribe, "items": cmd_items, "prompts": cmd_prompts,
          "verify": cmd_verify, "provenance": cmd_provenance, "describe": cmd_describe,
          "hosted": cmd_hosted, "evaluate": cmd_evaluate}
    print("[n28] {} {}; n21 loaded from source (sha256 {}; in-memory source sha256 {})".format(
        VERSION, args.cmd, N21_SHA256[:16], n21._N28_SOURCE_SHA256[:16]), flush=True)
    return fn[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
