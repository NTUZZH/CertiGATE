#!/usr/bin/env python3
"""N25: the direct benchmark under a finish-to-start reading of the precedence operation.

Design pre-specified before the run.  Frozen design:
results/n25_finish_to_start/design.md (sha256 asserted before any dispatch under the new
reading); later choices: results/n25_finish_to_start/addendum.md.

The benchmark's `reorder` operation enforces start-after-start: the dispatcher
(code/l1adapter/dispatch.py, `_precedence_ok`) lets a successor start once every predecessor is
in the set `started`.  A maintenance planning manager outside the author team
reads "do A before B" as "B may start
once A is complete".  This script reads every reorder edge as finish-to-start (reading F) and
recomputes the direct benchmark's headline beside the published reading S.

Reading F is implemented without editing any file under code/l1adapter/: `dispatch._run` is
compiled again from its own source with three textual changes (each asserted to occur once):
the eligibility test reads the predecessors' end times, the end time of every placed order is
recorded, and at each instant the trades of the successors of every order completing then join
the sweep.  A switch selects the reading; with the switch off the S code path runs.  The module
attribute `dispatch._run` is swapped only for the duration of each F call.

Steps (all run-fatal assertions abort the run):
  0  frozen-file prefixes, the design's sha256, the sha256 of every .py file under
     code/l1adapter/ (again at the end); n16.section0, n18.section0, n20.section0 on
     n20.build's records;
  P  probes on micro-instances (n24's builders): (a) patch off equals the unpatched module byte
     for byte, (b) patch on: the successor starts at the predecessor's end, (c) a proposal
     without a reorder edge gives the identical schedule with the patch on and off;
  R  replay: every priced reference proposal with a reorder (and 50 sampled without one, and
     the unpriced reference proposals with a reorder) through n11_decision_time.gen_price on
     the known board (K), the full-information board (FI) and the realised whole-window run,
     under S (unpatched), F, and S-off (patched, switch off; K only);
  S  every S board tied to its stored total, price, flags and label;
  F  the F records, the headline in the layout of Block C of N24 (S beside F), per
     stratum, the other designs, discordance, schedule and damage changes, label and
     disposition changes, the restricted headlines, the unpriced proposals, the self-test.

THE FOUR LAUNCH ANSWERS
  1. Purpose: a post hoc sensitivity analysis for one sentence of the main text and one
     paragraph with a small table in the Supplementary Material; every number goes to
     analysis/N25_macros.tex (copied to manuscript/macros_n25.tex) and analysis/N25_summary.md.
  2. Ideal result: the S replay reproduces every stored number (run-fatal); under F the
     reorder proposals cost at least as much and the certificate refers them on both boards.
     Whatever F gives is reported.
  3. Contamination: read-only on every input; deterministic dispatcher replays only (no solver,
     no time budget, no model call, no GPU), so core contention changes wall time only.
  4. Data accuracy: the population is n20.build's 1,356 priced proposals, the replay inputs are
     N11's census inputs (the suite through suite_gate, the instance snapshot, the canonical
     operations), and every S board is tied to its stored total before any F number.

Reuse: code/scripts/n24_conventions.py is imported (it allows core 14); through it
n20_stratum_abs.py, n16_robustness.py, n18_further_checks.py and n13_fromlogs.py are loaded
with their core allowance set to core 14 in memory (files untouched).  Labels:
n11_decision_time.attach_truth / n13.costly_of; prices: l1guard.verdict.certified_gap,
n2.prices and n11_forecast.prices_of restated on the same fields; tallies: n24.headline
(n20.tally, n13.score, n2.Boot: seed 20261026, 20,000 replicates, 60 instance clusters).

Outputs: analysis/N25_macros.tex (prefix \\nTwentyFive, one comment line per macro), copied to
manuscript/macros_n25.tex; analysis/N25_rows.csv; analysis/N25_summary.md;
results/n25_finish_to_start/replay.jsonl and l1adapter_sha256.json.
Run:       OMP_NUM_THREADS=1 taskset -c 14 python -B \\
               code/scripts/n25_finish_to_start.py
Self-test: the same with --selftest: every computation and assertion, writes nothing.  The
           default run performs the same second-path comparisons and records them.
Version: l1-n25-fts-1
"""
import os
import sys

sys.dont_write_bytecode = True
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_v] = "1"

import __future__  # noqa: E402
import csv  # noqa: E402
import hashlib  # noqa: E402
import inspect  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402
import shutil  # noqa: E402
import time  # noqa: E402
from collections import Counter, OrderedDict, defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

ALLOWED_CORES = {14}
_aff = set(os.sched_getaffinity(0))
if not _aff <= ALLOWED_CORES and not os.environ.get("CERTIGATE_ANY_CORES"):
    raise SystemExit("REFUSING TO RUN: affinity {} is not inside core 14 "
                     "(run under taskset -c 14)".format(sorted(_aff)))

SCRIPTS_DIR = Path(__file__).resolve().parent
CODE_DIR = SCRIPTS_DIR.parent
ROOT = CODE_DIR.parent
for _p in (str(CODE_DIR), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

VERSION = "l1-n25-fts-1"
OUT_DIR = ROOT / "results" / "n25_finish_to_start"
DESIGN = OUT_DIR / "design.md"
DESIGN_SHA_FILE = OUT_DIR / "design.sha256"
ADDENDUM = OUT_DIR / "addendum.md"
DESIGN_SHA = "a7ad31fb643899e46daaae635e2d0ceb27a089e66d60ba17735eed830078f32b"
FROZEN = OrderedDict([("n16_robustness.py", "dde428a8cedf"), ("n13_fromlogs.py", "523c1e41df5e"),
                      ("n11_decision_time.py", "05978a918888"),
                      ("n10_field_change.py", "5a790905576d")])
ADAPTER_DIR = CODE_DIR / "l1adapter"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def adapter_hashes():
    return OrderedDict((p.name, sha256_file(p)) for p in sorted(ADAPTER_DIR.glob("*.py")))


def frozen_hashes():
    return OrderedDict((k, sha256_file(SCRIPTS_DIR / k)) for k in FROZEN)


# --- before any import of the analysis code: the frozen files, the design, the adapter ---
_FROZEN0 = frozen_hashes()
for _k, _pre in FROZEN.items():
    if not _FROZEN0[_k].startswith(_pre):
        raise SystemExit("[n25] frozen file {} has sha256 {} (expected prefix {})".format(
            _k, _FROZEN0[_k], _pre))
_dsha = sha256_file(DESIGN)
if _dsha != DESIGN_SHA or DESIGN_SHA_FILE.read_text().split()[0] != DESIGN_SHA:
    raise SystemExit("[n25] design.md sha256 {} differs from the recorded {}".format(
        _dsha, DESIGN_SHA))
if not ADDENDUM.is_file():
    raise SystemExit("[n25] missing addendum " + str(ADDENDUM))
ADAPTER0 = adapter_hashes()

import n24_conventions as n24  # noqa: E402  (allows core 14; loads n20/n16/n18/n13)

n20, n16, n18, n13 = n24.n20, n24.n16, n24.n18, n24.n13
if not (n20.ALLOWED_CORES == n16.ALLOWED_CORES == n18.ALLOWED_CORES == n13.ALLOWED_CORES
        == ALLOWED_CORES):
    raise SystemExit("core allowance not propagated to n20/n16/n18/n13")
D = n13.D
np = n13.np
n2 = n13.n2
import n8_causal as n8  # noqa: E402
from l1adapter import dispatch as dispatch_mod  # noqa: E402
from l1guard.config import G_CERT  # noqa: E402
from l1guard.verdict import certified_gap  # noqa: E402

ANALYSIS = n13.ANALYSIS
RESULTS = n13.RESULTS
OUT_TEX = ANALYSIS / "N25_macros.tex"
OUT_MANU = ROOT / "manuscript" / "macros_n25.tex"
OUT_MD = ANALYSIS / "N25_summary.md"
OUT_CSV = ANALYSIS / "N25_rows.csv"
OUT_REPLAY = OUT_DIR / "replay.jsonl"
OUT_ADAPTER = OUT_DIR / "l1adapter_sha256.json"
IN25 = OrderedDict([
    ("brief", ROOT / "design_notes" / "N25_design.md"),
    ("design", DESIGN), ("addendum", ADDENDUM),
    ("n24_macros", ANALYSIS / "N24_macros.tex"), ("n20_macros", ANALYSIS / "N20_macros.tex"),
    ("n15_macros", ANALYSIS / "N15_macros.tex"),
    ("dispatch_py", ADAPTER_DIR / "dispatch.py"), ("apply_py", ADAPTER_DIR / "apply.py"),
])

#: Inputs the public release does not carry (the analysis's design note). A missing one
#: is recorded as "not shipped" in the provenance block, and the run goes on.
NOT_SHIPPED_OK = ('brief',)


def input_sha256(key, path):
    """The SHA-256 of an input, or "not shipped" for one the public release does not carry."""
    if key in NOT_SHIPPED_OK and not Path(path).is_file():
        return "not shipped"
    return sha256_file(path)

TAU = n13.TAU
FLOOR = D.FLOOR_BH
EPS = 1e-9
SUM_TOL = 1e-9
ANCHOR_TOL = 1e-6
CSV_TOL = 1e-6
SAMPLE_SEED = 20261111
SAMPLE_N = 50
DELTAS = n24.DELTAS                       # DeltaTwenty 0.20, DeltaTen 0.10
DESIGNS = n13.DESIGNS                     # G-CERT, G-CERT-M, D-REL1, D-REL2, D-ABS
SETTINGS = n13.SETTINGS
UNION = n13.UNION
DES_TOK = {"G-CERT": "Cert", "G-CERT-M": "CertM", "D-REL1": "RelOne", "D-REL2": "RelTwo",
           "D-ABS": "Abs"}
ST_TOK = n13.ST_TOK
POPS = OrderedDict([("Pooled", None)] + [(ST_TOK[s], s) for s in D.STRATA])
RDS = ("S", "F")
RD_NAME = {"S": "S (published, start-after-start)", "F": "F (finish-to-start)"}
BOARDS = OrderedDict([("dt", ("K", "known board")), ("fi", ("FI", "full-information board")),
                      ("rw", ("Real", "realised whole-window run"))])
HL_TOK = OrderedDict([(k, v[0]) for k, v in n24.HL_FIELDS.items()])
HL_TOK.update(cd_k="CommonAppK", cd_f="CommonAppFI")

LINES = ["% N25 macros ({}); generated by code/scripts/n25_finish_to_start.py from deterministic "
         "dispatcher replays of the direct benchmark under the published start-after-start "
         "reading (S) and a finish-to-start reading of every reorder edge (F), post hoc "
         "sensitivity analysis (no solve, no model call); each macro follows a comment line "
         "giving its block and definition".format(VERSION)]
NAMES = set()
VAL = OrderedDict()
MD = []
NCHECK = [0]
SELF = []
MAXDIFF = defaultdict(float)
LOG = []

grp, pct, pctv, pctp, pctpv, frac = (n16.grp, n16.pct, n16.pctv, n16.pctp, n16.pctpv, n16.frac)


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def check(what, ok, detail=""):
    if not ok:
        raise SystemExit("[n25] ASSERTION FAILED: {} ({})".format(what, str(detail)[:900]))
    NCHECK[0] += 1


def close(what, a, b, tol, key=""):
    if a is None or b is None:
        check(what + " (both missing)", a is None and b is None, (key, a, b))
        return
    d = abs(float(a) - float(b))
    MAXDIFF[what] = max(MAXDIFF[what], d)
    check(what, d <= tol, (key, a, b, d))


def add(name, value, note):
    full = "nTwentyFive" + name
    if not full.isalpha():
        raise SystemExit("macro name not alphabetic: " + full)
    if full in NAMES:
        raise SystemExit("duplicate macro " + full)
    NAMES.add(full)
    VAL[full] = str(value)
    LINES.append("% " + note)
    LINES.append("\\newcommand{\\" + full + "}{" + str(value) + "}")


def md(*lines):
    MD.extend(lines)


def md_table(head, body):
    MD.append("| " + " | ".join(str(h) for h in head) + " |")
    MD.append("|" + "|".join("---" for _ in head) + "|")
    for row in body:
        MD.append("| " + " | ".join("" if c is None else str(c) for c in row) + " |")
    MD.append("")


def bh1(x):
    return "n/a" if x is None else "{:.1f}".format(x)


def bh2(x):
    return "n/a" if x is None else "{:.2f}".format(x)


def bhm(x):
    """bh with one decimal for a macro, thousands grouped as in the other macro files."""
    return "n/a" if x is None else "{:,.1f}".format(x).replace(",", "{,}")


def say(msg):
    print("[n25] " + msg, flush=True)
    LOG.append(msg)


def lbl(c):
    return {1: "costly", 0: "low-cost", None: "undecided"}[c]


def optypes(ops):
    return {o.get("op") for o in (ops or []) if isinstance(o, dict)}


# --------------------------------------------------------------------------- #
# Reading F: the patched dispatcher (in memory)                                #
# --------------------------------------------------------------------------- #
ORIG_RUN = dispatch_mod._run
SWAPS = [
    ("    started: set[str] = set()\n    queued_ids: set[str] = set()\n",
     "    started: set[str] = set()\n    _n25_end = {}\n    _n25_ending = defaultdict(list)\n"
     "    queued_ids: set[str] = set()\n"),
    ("    def _precedence_ok(oid: str) -> bool:\n        ps = preds.get(oid)\n"
     "        return not ps or all(a in started for a in ps)\n",
     "    def _precedence_ok(oid: str) -> bool:\n        ps = preds.get(oid)\n"
     "        if _N25_FTS[0]:\n"
     "            return not ps or all(_n25_end.get(a, _INF) <= now for a in ps)\n"
     "        return not ps or all(a in started for a in ps)\n"),
    ('        end = start + float(job["p_bh"])\n        assignments.append(\n'
     '            {"wo": jid, "tech": tech_id, "start_bh": start, "end_bh": end}\n        )\n',
     '        end = start + float(job["p_bh"])\n        assignments.append(\n'
     '            {"wo": jid, "tech": tech_id, "start_bh": start, "end_bh": end}\n        )\n'
     '        _n25_end[jid] = end\n        _n25_ending[end].append(jid)\n'),
    ('            end = start + float(job["p_bh"])\n'
     '            assignments.append({"wo": oid, "tech": tid, "start_bh": start, "end_bh": end})\n',
     '            end = start + float(job["p_bh"])\n'
     '            assignments.append({"wo": oid, "tech": tid, "start_bh": start, "end_bh": end})\n'
     '            _n25_end[oid] = end\n            _n25_ending[end].append(oid)\n'),
    ("        sweep = sorted(touched)\n",
     "        if _N25_FTS[0]:\n"
     "            for _n25_oid in _n25_ending.pop(now, ()):\n"
     "                for _n25_nxt in succs.get(_n25_oid, ()):\n"
     "                    touched.add(wo_by_id[_n25_nxt][\"trade\"])\n"
     "        sweep = sorted(touched)\n"),
]


def make_patched_run():
    src = inspect.getsource(ORIG_RUN)
    disk = Path(dispatch_mod.__file__).read_text(encoding="utf-8")
    check("the source of dispatch._run is one slice of dispatch.py on disk", disk.count(src) == 1)
    for old, new in SWAPS:
        check("patch anchor occurs once in dispatch._run: {!r}".format(old[:50]),
              src.count(old) == 1, src.count(old))
        src = src.replace(old, new)
    g = dict(vars(dispatch_mod))
    flag = [False]
    g["_N25_FTS"] = flag
    code = compile(src, "<n25: dispatch._run with the finish-to-start switch>", "exec",
                   flags=__future__.annotations.compiler_flag, dont_inherit=True)
    exec(code, g)  # noqa: S102
    return g["_run"], flag, src


PATCHED_RUN, FTS, PATCHED_SRC = make_patched_run()


class Reading:
    """S: the unpatched module; Soff: the patched function, switch off; F: switch on."""

    def __init__(self, rd):
        if rd not in ("S", "Soff", "F"):
            raise ValueError(rd)
        self.rd = rd

    def __enter__(self):
        if self.rd == "S":
            dispatch_mod._run, FTS[0] = ORIG_RUN, False
        else:
            dispatch_mod._run, FTS[0] = PATCHED_RUN, self.rd == "F"
        return self

    def __exit__(self, *exc):
        dispatch_mod._run, FTS[0] = ORIG_RUN, False
        return False


def sched_json(s):
    return dispatch_mod.canonical_schedule_json(s)


def sched_digest(s):
    return hashlib.sha256(sched_json(s).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# P. Probes on micro-instances                                                 #
# --------------------------------------------------------------------------- #
def probe_run(inst, oplist, rd):
    with Reading(rd):
        parsed = n24.l1ops.parse_operations({"operations": oplist}) if oplist else []
        adj = n24.apply_operations(inst, parsed)
        sch = dispatch_mod.dispatch_adjusted(adj, "atc", 0)
    return sched_json(sch), {a["wo"]: a for a in sch["assignments"]}


def block_p():
    o_ = n24._order
    i1 = n24._instance([o_("A", "D20", 4.0, release_bh=3.0, due_bh=9.0),
                        o_("B", "D30", 2.0, due_bh=1.0)], [("T0", "D20"), ("T1", "D30")])
    i2 = n24._instance([o_("A", "D20", 4.0, release_bh=3.0, due_bh=9.0),
                        o_("B", "D20", 2.0, due_bh=1.0)], [("T0", "D20"), ("T1", "D20")])
    i3 = n24._instance([o_("X", "D20", 6.0, due_bh=1.0), o_("Y", "D20", 2.0)], [("T0", "D20")])
    # a three-order chain across two trades: A (D20, 4 bh) -> B (D30, 2 bh) -> C (D20, 1 bh)
    i4 = n24._instance([o_("A", "D20", 4.0, due_bh=4.0), o_("B", "D30", 2.0, due_bh=1.0),
                        o_("C", "D20", 1.0, due_bh=1.0)], [("T0", "D20"), ("T1", "D30")])
    # a batch micro-instance: three orders of one (building, trade) group and one outside it
    bo = [o_("U", "D20", 2.0, due_bh=10.0), o_("V", "D20", 1.0, due_bh=5.0),
          o_("W", "D20", 3.0, release_bh=1.0, due_bh=8.0), o_("Z", "D20", 2.0, due_bh=2.0)]
    for x in bo[:3]:
        x["building"] = "B1"
    i5 = n24._instance(bo, [("T0", "D20"), ("T1", "D20")])
    reo = [{"op": "reorder", "order_id": "A", "relation": "before", "ref_order_id": "B"}]
    chain = reo + [{"op": "reorder", "order_id": "B", "relation": "before",
                    "ref_order_id": "C"}]
    probes = OrderedDict([
        ("p1", ("probe 1: cross-trade, reorder A before B", i1, reo)),
        ("p2", ("probe 2: same trade, two technicians, reorder A before B", i2, reo)),
        ("p4", ("probe 4: chain A -> B -> C across two trades", i4, chain)),
        ("p1none", ("probe 1 without an operation", i1, [])),
        ("p3shift", ("probe 3: shift of Y by +4 bh", i3,
                     [{"op": "reassign_window", "order_id": "Y", "release_shift_bh": 4.0}])),
        ("p3pin", ("probe 3: pin_next Y", i3, [{"op": "pin_next", "order_id": "Y",
                                                 "trade": "D20"}])),
        ("p5batch", ("probe 5: batch of building B1, trade D20", i5,
                     [{"op": "batch", "building_id": "B1", "trade": "D20"}])),
    ])
    res = OrderedDict()
    for key, (txt, inst, ops) in probes.items():
        out = {rd: probe_run(inst, ops, rd) for rd in ("S", "Soff", "F")}
        check("(a) {}: patch off equals the unpatched module byte for byte".format(txt),
              out["S"][0] == out["Soff"][0], (out["S"][0], out["Soff"][0]))
        has_reorder = any(o["op"] == "reorder" for o in ops)
        if not has_reorder:
            check("(c) {}: no reorder edge, identical schedule with the patch on and off".format(
                txt), out["F"][0] == out["S"][0], (out["S"][0], out["F"][0]))
        res[key] = (txt, out, has_reorder)
    s1, f1 = res["p1"][1]["S"][1], res["p1"][1]["F"][1]
    check("(b) probe 1 under S: B starts with A at 3.0", s1["B"]["start_bh"] == s1["A"]["start_bh"]
          == 3.0, s1)
    check("(b) probe 1 under F: B starts at A's end, 7.0", f1["B"]["start_bh"] == f1["A"]["end_bh"]
          == 7.0 and f1["A"]["start_bh"] == 3.0, f1)
    s2, f2 = res["p2"][1]["S"][1], res["p2"][1]["F"][1]
    check("(b) probe 2 under S: B starts with A at 3.0 on the other technician",
          s2["B"]["start_bh"] == 3.0 and s2["A"]["tech"] != s2["B"]["tech"], s2)
    check("(b) probe 2 under F: B starts at A's end, 7.0", f2["B"]["start_bh"] == f2["A"]["end_bh"]
          == 7.0, f2)
    s4, f4 = res["p4"][1]["S"][1], res["p4"][1]["F"][1]
    check("(b) probe 4 under F: B at A's end and C at B's end",
          f4["B"]["start_bh"] == f4["A"]["end_bh"] and f4["C"]["start_bh"] == f4["B"]["end_bh"],
          f4)
    check("(b) probe 4 under F differs from S", res["p4"][1]["F"][0] != res["p4"][1]["S"][0])
    add("ProbeCrossSuccStartS", bh1(s1["B"]["start_bh"]),
        "[P] probe 1 (cross-trade, reorder A before B; A 4 bh released at 3, B 2 bh released at "
        "0, one technician per trade), reading S: start of B, bh")
    add("ProbeCrossSuccStartF", bh1(f1["B"]["start_bh"]),
        "[P] probe 1, reading F (finish-to-start): start of B, bh")
    add("ProbeCrossPredEnd", bh1(f1["A"]["end_bh"]), "[P] probe 1: end of A, bh")
    add("ProbeSameTradeSuccStartF", bh1(f2["B"]["start_bh"]),
        "[P] probe 2 (same trade, two technicians), reading F: start of B, bh")
    add("ProbeChainThirdStartS", bh1(s4["C"]["start_bh"]),
        "[P] probe 4 (chain A -> B -> C, A and C in D20, B in D30), reading S: start of C, bh")
    add("ProbeChainThirdStartF", bh1(f4["C"]["start_bh"]),
        "[P] probe 4, reading F: start of C, bh")
    md("## P. Probes (in memory, before any replay of the suite)", "",
       "Micro-instances built with n24's probe builders and dispatched with ATC, seed 0 "
       "(apply_operations, then dispatch_adjusted). S = the unpatched module; S-off = the "
       "patched function with the switch off; F = the switch on. (a) S-off equals S byte for "
       "byte on every probe; (b) under F the successor starts at its predecessor's end; (c) "
       "without a reorder edge F equals S byte for byte.", "")
    body = []
    for key, (txt, out, hr) in res.items():
        sm, fm = out["S"][1], out["F"][1]
        body.append([txt, "; ".join("{} {}-{} on {}".format(k, bh1(v["start_bh"]), bh1(v["end_bh"]),
                                                             v["tech"]) for k, v in sorted(sm.items())),
                     "; ".join("{} {}-{} on {}".format(k, bh1(v["start_bh"]), bh1(v["end_bh"]),
                                                       v["tech"]) for k, v in sorted(fm.items())),
                     "yes", "yes" if out["F"][0] == out["S"][0] else "no ({})".format(
                         "reorder edge" if hr else "UNEXPECTED")])
    md_table(["probe", "reading S", "reading F", "S-off = S byte for byte",
              "F = S byte for byte"], body)
    return res


# --------------------------------------------------------------------------- #
# R. The replay                                                                #
# --------------------------------------------------------------------------- #
def summ(res):
    """The board's outcome and, when a schedule exists, its digest and the edge census."""
    if res is None:
        return None
    out = OrderedDict((k, res.get(k)) for k in (
        "term_cert", "stage_cert", "term_feas", "stage_feas", "codes", "infra", "obj",
        "obj_orig", "lb", "gap", "ref2", "ref2_from"))
    out.update(digest=None, complete=None, n_orders=None, edges=0, start_viol_unfrozen=0,
               overlap=0, freeze_wins=0, fts_viol=0, edge_detail=[])
    live = res.get("_live") or {}
    if "schedule" in live:
        adj, sch = live["adjusted"], live["schedule"]
        ids = [a["wo"] for a in sch["assignments"]]
        wids = {w["id"] for w in adj.instance["work_orders"]}
        out["digest"] = sched_digest(sch)
        out["n_orders"] = len(wids)
        out["complete"] = len(ids) == len(set(ids)) == len(wids) and set(ids) == wids
        slot = {a["wo"]: a for a in sch["assignments"]}
        for a, b in adj.precedence:
            sa, ea = float(slot[a]["start_bh"]), float(slot[a]["end_bh"])
            sb = float(slot[b]["start_bh"])
            fz = b in adj.frozen
            out["edges"] += 1
            if sb < sa - EPS and not fz:
                out["start_viol_unfrozen"] += 1
            if sb < ea - EPS:
                out["overlap"] += 1
                if fz:
                    out["freeze_wins"] += 1
                else:
                    out["fts_viol"] += 1
            out["edge_detail"].append([a, b, sa, ea, sb, fz])
    return out


def slim_site(res):
    return {k: res.get(k) for k in ("term_cert", "stage_cert", "term_feas", "obj", "obj_orig",
                                    "lb", "gap")}


def build_tasks(items, suite, items_by, anchors):
    """items: [(item_id, kind)]; tasks grouped by instance as in n23.build_tasks."""
    by_inst = OrderedDict()
    for item_id, kind in sorted(items):
        it = suite[item_id]
        iid = it["instance"]["instance_id"]
        check("suite instance equals items.jsonl", iid == items_by[item_id]["instance_id"],
              item_id)
        t = by_inst.setdefault(iid, {"iid": iid, "path": D.instance_path(it), "items": [],
                                     "seeds": OrderedDict(), "digest": OrderedDict()})
        seed = list(it["episode"]["frozen_seed"] or [])
        fk = D.frozen_key(seed)
        check("frozen key equals items.jsonl", fk == items_by[item_id]["frozen_seed"], item_id)
        t["seeds"].setdefault(fk, seed)
        t["digest"].setdefault(fk, anchors[(iid, fk)]["schedule_digest"])
        ops = D.canonical_ops(it)
        check("canonical operation count equals the census",
              len(ops) == items_by[item_id]["n_ops"], item_id)
        t["items"].append({"item_id": item_id, "kind": kind, "fk": fk, "seed": seed, "ops": ops,
                           "referenced": it["referenced"]})
    return list(by_inst.values())


def replay_instance(task, items_by):
    t0 = time.perf_counter()
    inst = D.load_instance(task["path"])
    iid = inst["meta"]["id"]
    with Reading("S"):
        baseline = dispatch_mod.dispatch_baseline(inst, "atc", 0)
        trajs = {fk: n8.trajectory(inst, seed, baseline) for fk, seed in task["seeds"].items()}
    for fk, tr in trajs.items():
        check("the trajectory's schedule digest equals rule_anchor.json's", sched_digest(tr)
              == task["digest"][fk], (iid, fk))
    by_id = {wo["id"]: wo for wo in inst["work_orders"]}
    sites = {}
    out = {"iid": iid, "items": [], "sites": OrderedDict()}

    def site_for(fk, seed, t_d):
        key = (fk, t_d)
        if key in sites:
            return sites[key]
        traj = trajs[fk]
        state = n8.site_state(inst, traj, t_d, pm_known=True)
        known = n8.known_instance(inst, state)
        kf = D.kf_fix(state, seed)
        started = state["completed"] + state["in_progress"]
        k_ids = state["queue"] + state["in_progress"] + state["scheduled"]
        base_p = n8.pin_schedule(baseline, traj, started)
        frozen_r = list(started) + [o for o in seed if o not in set(started)]
        run_ids = list(state["in_progress"])
        done = set(state["completed"])
        fi_board = {k: v for k, v in inst.items() if k != "work_orders"}
        fi_board["work_orders"] = [wo for wo in inst["work_orders"] if wo["id"] not in done]
        s = {"known": known, "kf": kf, "k_ids": k_ids, "base_p": base_p, "frozen_r": frozen_r,
             "run_ids": run_ids, "fi_board": fi_board, "key": "{}|{:.6f}".format(fk, t_d)}
        sites[key] = s
        return s

    for it in task["items"]:
        fk, seed, kind = it["fk"], it["seed"], it["kind"]
        stored = items_by[it["item_id"]]
        starts = {a["wo"]: float(a["start_bh"]) for a in trajs[fk]["assignments"]}
        iss = D.issuability(it, by_id, starts)
        t_d = D.decision_instant_of(iss, "primary")
        check("decision instant equals items.jsonl", t_d == float(stored["t_d"]), it["item_id"])
        check("issuability equals items.jsonl", iss["issuable"] == stored["issuable"],
              it["item_id"])
        s = site_for(fk, seed, t_d)
        raw = json.dumps({"operations": it["ops"]})
        rec = {"item_id": it["item_id"], "iid": iid, "fk": fk, "t_d": t_d, "site": s["key"],
               "kind": kind, "boards": OrderedDict()}
        reads = ("S", "F", "Soff") if kind == "reorder" else ("S", "F")
        for rd in reads:
            b = OrderedDict()
            with Reading(rd):
                b["dt"] = summ(D.gen_price(s["known"], raw, s["kf"], s["base_p"], t_d, ref2=True,
                                           keep_live=True, running_ids=s["run_ids"]))
                if rd != "Soff":
                    b["fi"] = summ(D.gen_price(s["fi_board"], raw, s["kf"], s["base_p"], t_d,
                                               ref2=True, keep_batch=s["k_ids"],
                                               running_ids=s["run_ids"], keep_live=True))
                    b["rw"] = (None if kind.startswith("unpriced") else
                               summ(D.gen_price(inst, raw, s["frozen_r"], s["base_p"], t_d,
                                                keep_batch=s["k_ids"], keep_live=True)))
            rec["boards"][rd] = b
        if kind == "reorder" and s["key"] not in out["sites"]:
            with Reading("F"):
                an = D.gen_price(s["known"], D.EMPTY_RAW, s["kf"], s["base_p"], t_d)
                rw0 = D.gen_price(inst, D.EMPTY_RAW, s["frozen_r"], s["base_p"], t_d,
                                  keep_batch=s["k_ids"])
                fa = D.gen_price(s["fi_board"], D.EMPTY_RAW, s["kf"], s["base_p"], t_d,
                                 ref2=False, keep_batch=s["k_ids"], running_ids=s["run_ids"])
            out["sites"][s["key"]] = {"t_d": t_d, "fk": fk, "an": slim_site(an),
                                      "rw0": slim_site(rw0), "fa": slim_site(fa)}
        out["items"].append(rec)
    out["wall_s"] = time.perf_counter() - t0
    return out


def run_replay(tasks, items_by):
    order = sorted(range(len(tasks)), key=lambda i: tasks[i]["iid"])
    res = []
    t0 = time.time()
    for j, i in enumerate(order):
        r = replay_instance(tasks[i], items_by)
        res.append(r)
        say("replayed {} ({} proposals, {:.0f}s), {} of {} ({:.0f}s)".format(
            r["iid"], len(r["items"]), r["wall_s"], j + 1, len(order), time.time() - t0))
    return res


# --------------------------------------------------------------------------- #
# Values of one proposal under one reading                                     #
# --------------------------------------------------------------------------- #
def label_interval(rw_obj_orig, base, anchor):
    """The realised marginal-cost interval (n11_forecast.attach_orig_truth's rule)."""
    if rw_obj_orig is None or base is None:
        return None, None
    row = {"orig_obj": rw_obj_orig}
    D.attach_truth(row, base, base, anchor, prefix="orig_")
    if not row.get("orig_covered_m"):
        return None, None
    return row["orig_m_lo"], row["orig_m_hi"]


def values_of(b, it, fi_logged, fa_a, base, anchor):
    """Every price, flag and label of a proposal from its three boards under one reading."""
    dt, fi, rw = b["dt"], b["fi"], b["rw"]
    v = OrderedDict(priced_k=dt["stage_cert"] == "qual", priced_fi=fi["stage_cert"] == "qual",
                    real_ok=rw is not None and rw["obj_orig"] is not None and bool(rw["complete"]))
    v["pk"] = OrderedDict((g, None) for g in DESIGNS)
    v["pf"] = OrderedDict((g, None) for g in DESIGNS)
    v["g_orig"] = v["sp_fi"] = v["c_bh_k"] = v["c_bh_f"] = None
    if v["priced_k"]:
        lb = it["dt_lb"]                                  # the logged bound of the board
        gap = certified_gap(dt["obj"], lb, G_CERT.lb_floor_bh)
        v["gap_k"] = gap
        v["pk"].update([("G-CERT", gap), ("G-CERT-M", gap - it["an_gap"]),
                        ("D-REL1", D.rel_delta(dt["obj"], it["an_obj"])),
                        ("D-REL2", None if dt["ref2"] is None else D.rel_delta(dt["obj"],
                                                                                dt["ref2"])),
                        ("D-ABS", round(dt["obj"] - it["an_obj"], D.ROUND_BH))])
        v["g_orig"] = (dt["obj_orig"] - it["an_lb"]) / max(it["an_lb"], FLOOR)
        v["c_bh_k"] = n13.gap_bh(dt["obj"], lb)
    if v["priced_fi"]:
        lbf = fi_logged["p"]["lb"]
        gapf = certified_gap(fi["obj"], lbf, G_CERT.lb_floor_bh)
        v["gap_f"] = gapf
        v["pf"].update([("G-CERT", gapf), ("G-CERT-M", gapf - fa_a["gap"]),
                        ("D-REL1", D.rel_delta(fi["obj"], fa_a["obj"])),
                        ("D-REL2", None if fi["ref2"] is None else D.rel_delta(fi["obj"],
                                                                                fi["ref2"])),
                        ("D-ABS", round(fi["obj"] - fa_a["obj"], D.ROUND_BH))])
        v["sp_fi"] = (fi["obj_orig"] - fa_a["lb"]) / max(fa_a["lb"], FLOOR)
        v["c_bh_f"] = n13.gap_bh(fi["obj"], lbf)
    v["rw_obj_orig"] = rw["obj_orig"] if v["real_ok"] else None
    v["dmg"] = None if v["rw_obj_orig"] is None else v["rw_obj_orig"] - anchor
    v["lo"], v["hi"] = label_interval(v["rw_obj_orig"], base, anchor)
    return v


def record_of(r, v):
    """The published record r with every reading-dependent field taken from v."""
    x = dict(r)
    x["fi"] = dict(r["fi"])
    x["lo"], x["hi"], x["dmg"] = v["lo"], v["hi"], v["dmg"]
    for g in DESIGNS:
        x["p_" + g] = v["pk"][g]
        x["ref_" + g] = v["pk"][g] is not None and v["pk"][g] > SETTINGS[g]
        if v["priced_fi"]:
            x["fi"]["p_" + g] = v["pf"][g]
            x["fi"]["ref_" + g] = v["pf"][g] is not None and v["pf"][g] > SETTINGS[g]
        else:                                             # addendum 5: refused on FI
            x["fi"]["p_" + g] = None
            x["fi"]["ref_" + g] = True
    x["ref_" + UNION] = x["ref_G-CERT-M"] or x["ref_D-REL2"]
    x["fi"]["ref_" + UNION] = x["fi"]["ref_G-CERT-M"] or x["fi"]["ref_D-REL2"]
    x["g_orig"] = v["g_orig"]
    x["sp"] = v["g_orig"] > TAU
    x["ref_k"] = n13.refers(x, "G-CERT")
    x["ref_f"] = n13.refers(x["fi"], "G-CERT")
    x["two_k"] = n16.sp_flag(x, "G-CERT")
    if v["priced_fi"]:
        x["sp_fi"] = v["sp_fi"]
        x["two_f"] = x["ref_f"] or (x["field"] and v["sp_fi"] > TAU)
        x["c_bh_f"] = v["c_bh_f"]
    else:
        x["sp_fi"], x["two_f"], x["c_bh_f"] = None, True, float("inf")
    x["c_bh_k"] = v["c_bh_k"]
    return x


# --------------------------------------------------------------------------- #
# S. The run-fatal tie of every S board to its stored total                    #
# --------------------------------------------------------------------------- #
def assert_s(rep, sites, recs_by, items_by, fi_logged, fa_logged, anchors, full_br):
    vals = {}
    for iid_item, x in rep.items():
        if x["kind"] != "reorder":
            continue
        it, r = items_by[iid_item], recs_by[iid_item]
        bS, bO = x["boards"]["S"], x["boards"]["Soff"]
        dt, fi, rw = bS["dt"], bS["fi"], bS["rw"]
        # K
        check("S, K: priced", dt["stage_cert"] == "qual" == it["dt_stage_cert"], iid_item)
        check("S, K: terminals and codes equal items.jsonl",
              (dt["term_cert"], dt["term_feas"], dt["codes"]) ==
              (it["dt_term_cert"], it["dt_term_feas"], it["dt_codes"]), iid_item)
        close("S, K: adjusted objective = items.jsonl dt_obj", dt["obj"], it["dt_obj"], SUM_TOL,
              iid_item)
        close("S, K: original-field objective = items.jsonl dt_obj_orig", dt["obj_orig"],
              it["dt_obj_orig"], SUM_TOL, iid_item)
        close("S, K: bound = items.jsonl dt_lb", dt["lb"], it["dt_lb"], SUM_TOL, iid_item)
        close("S, K: certified gap = items.jsonl dt_gap", dt["gap"], it["dt_gap"], SUM_TOL,
              iid_item)
        close("S, K: D-REL2 reference = items.jsonl dt_ref2", dt["ref2"], it["dt_ref2"], SUM_TOL,
              iid_item)
        check("S-off, K: canonical schedule equals the unpatched module's byte for byte",
              bO["dt"]["digest"] == dt["digest"] and bO["dt"]["obj"] == dt["obj"]
              and bO["dt"]["gap"] == dt["gap"], iid_item)
        # FI
        p = fi_logged[iid_item]["p"]
        for k in ("term_cert", "stage_cert", "term_feas", "stage_feas", "codes", "ref2_from"):
            check("S, FI: {} equals fullinfo_direct.jsonl".format(k), fi[k] == p[k],
                  (iid_item, k, fi[k], p[k]))
        for k in ("obj", "obj_orig", "lb", "gap", "ref2"):
            close("S, FI: {} = fullinfo_direct.jsonl".format(k), fi[k], p[k], SUM_TOL, iid_item)
        # realised
        check("S, realised: terminals equal items.jsonl",
              (rw["term_cert"], rw["term_feas"]) == (it["rw_term"], it["rw_term_feas"]),
              iid_item)
        close("S, realised: original-field objective = items.jsonl rw_obj_orig", rw["obj_orig"],
              it["rw_obj_orig"], SUM_TOL, iid_item)
        close("S, realised: adjusted objective = items.jsonl rw_obj", rw["obj"], it["rw_obj"],
              SUM_TOL, iid_item)
        for bk in ("dt", "fi", "rw"):
            check("S: every schedule complete ({})".format(bk), bS[bk]["complete"], iid_item)
            check("S: no unfrozen successor starts before its predecessor ({})".format(bk),
                  bS[bk]["start_viol_unfrozen"] == 0, iid_item)
            check("S: the board carries the reorder edges ({})".format(bk), bS[bk]["edges"] > 0,
                  iid_item)
        a = anchors[(it["instance_id"], it["frozen_seed"])]
        anchor = float(a["wwt_original_bh"])
        base = full_br.get((it["instance_id"], D.BASE_FP))
        fa_a = fa_logged[(it["instance_id"], it["frozen_seed"], float(it["t_d"]))]
        v = values_of(bS, it, fi_logged[iid_item], fa_a, base, anchor)
        vals[iid_item] = v
        # the S values against the published record
        close("S: damage = N11_rows_forecast.csv damage_orig_bh", v["dmg"], r["dmg"], CSV_TOL,
              iid_item)
        close("S: lower end of the realised-cost interval = orig_m_lo", v["lo"], r["lo"],
              CSV_TOL, iid_item)
        close("S: upper end of the realised-cost interval = orig_m_hi", v["hi"], r["hi"],
              CSV_TOL, iid_item)
        x = record_of(r, v)
        for dl in DELTAS.values():
            check("S: label at delta {:.2f} equals the published label".format(dl),
                  n13.costly_of(x, dl) == n13.costly_of(r, dl), iid_item)
        for g in DESIGNS:
            close("S, K: price {} = N11_rows_forecast.csv".format(g), v["pk"][g], r["p_" + g],
                  CSV_TOL, iid_item)
            check("S, K: flag {} equals the published flag".format(g),
                  x["ref_" + g] == r["ref_" + g], (iid_item, g))
            close("S, FI: price {} = N11_rows_forecast.csv".format(g), v["pf"][g],
                  r["fi"]["p_" + g], CSV_TOL, iid_item)
            close("S, FI: price {} = fullinfo_direct.jsonl prices".format(g), v["pf"][g],
                  fi_logged[iid_item]["prices"][g], 1e-12, iid_item)
            check("S, FI: flag {} equals the published flag".format(g),
                  x["fi"]["ref_" + g] == r["fi"]["ref_" + g], (iid_item, g))
        close("S: certificate price from the logged bound = the stored gap", v["gap_k"],
              it["dt_gap"], 1e-12, iid_item)
        close("S: second price (K) = n16's g_orig", v["g_orig"], r["g_orig"], 1e-12, iid_item)
        close("S: second price (FI) = n13 section J's", v["sp_fi"], r["sp_fi"], 1e-12, iid_item)
        close("S: common-denominator bh price (K) = n13 section F's", v["c_bh_k"], r["c_bh_k"],
              1e-9, iid_item)
        close("S: common-denominator bh price (FI) = n13 section F's", v["c_bh_f"], r["c_bh_f"],
              1e-9, iid_item)
        for k in ("ref_k", "ref_f", "two_k", "two_f", "sp", "ref_" + UNION):
            check("S: {} equals the published record".format(k), x[k] == r[k], (iid_item, k))
        check("S: union flag on FI equals the published record",
              x["fi"]["ref_" + UNION] == r["fi"]["ref_" + UNION], iid_item)
    return vals


def assert_sites_f(out_sites, items_by, fa_logged, rep):
    """Every site of a reorder proposal: the no-proposal runs under F equal the stored totals."""
    n = 0
    for x in rep.values():
        if x["kind"] != "reorder":
            continue
        it = items_by[x["item_id"]]
        s = out_sites[(x["iid"], x["site"])]
        close("F, K without the proposal: original-field objective = an_obj_orig",
              s["an"]["obj_orig"], it["an_obj_orig"], SUM_TOL, x["item_id"])
        close("F, K without the proposal: adjusted objective = an_obj", s["an"]["obj"],
              it["an_obj"], SUM_TOL, x["item_id"])
        close("F, K without the proposal: bound = an_lb", s["an"]["lb"], it["an_lb"], SUM_TOL,
              x["item_id"])
        close("F, K without the proposal: certificate = an_gap", s["an"]["gap"], it["an_gap"],
              SUM_TOL, x["item_id"])
        close("F, realised without the proposal: original-field objective = rw0_obj_orig",
              s["rw0"]["obj_orig"], it["rw0_obj_orig"], SUM_TOL, x["item_id"])
        close("F, realised without the proposal = the no-AI anchor (pub_anchor_wwt)",
              s["rw0"]["obj_orig"], it["pub_anchor_wwt"], ANCHOR_TOL, x["item_id"])
        a = fa_logged[(it["instance_id"], it["frozen_seed"], float(it["t_d"]))]
        for k in ("obj", "obj_orig", "lb", "gap"):
            close("F, FI without the proposal: {} = anchors_direct.jsonl".format(k), s["fa"][k],
                  a[k], SUM_TOL, x["item_id"])
        n += 1
    return n


def assert_sample(rep, items_by, fi_logged):
    n = 0
    for iid_item, x in rep.items():
        if x["kind"] != "sample":
            continue
        it = items_by[iid_item]
        bS, bF = x["boards"]["S"], x["boards"]["F"]
        close("sample S, K: dt_obj", bS["dt"]["obj"], it["dt_obj"], SUM_TOL, iid_item)
        close("sample S, K: dt_obj_orig", bS["dt"]["obj_orig"], it["dt_obj_orig"], SUM_TOL,
              iid_item)
        close("sample S, K: dt_gap", bS["dt"]["gap"], it["dt_gap"], SUM_TOL, iid_item)
        close("sample S, realised: rw_obj_orig", bS["rw"]["obj_orig"], it["rw_obj_orig"],
              SUM_TOL, iid_item)
        p = fi_logged[iid_item]["p"]
        close("sample S, FI: obj", bS["fi"]["obj"], p["obj"], SUM_TOL, iid_item)
        close("sample S, FI: gap", bS["fi"]["gap"], p["gap"], SUM_TOL, iid_item)
        for bk in ("dt", "fi", "rw"):
            check("sample: no reorder edge on the board ({})".format(bk), bS[bk]["edges"] == 0
                  and bF[bk]["edges"] == 0, iid_item)
            check("sample: F schedule equals S byte for byte ({})".format(bk),
                  bS[bk]["digest"] == bF[bk]["digest"] and bS[bk]["digest"] is not None,
                  iid_item)
            for k in ("term_cert", "stage_cert", "codes", "obj", "obj_orig", "lb", "gap",
                      "ref2"):
                check("sample: F {} equals S ({})".format(k, bk), bS[bk][k] == bF[bk][k],
                      (iid_item, bk, k))
        n += 1
    return n


# --------------------------------------------------------------------------- #
# Tables                                                                       #
# --------------------------------------------------------------------------- #
def hl_row(h, dtok):
    x = h[dtok]
    return [h["priced"], h["instances"], x["costly"], x["low"],
            "{} / {} / {}".format(x["ref_k"], x["ref_f"], x["ref_both"]),
            "{} / {}".format(x["app_k"], x["app_f"]),
            "{} / {}".format(x["two_app_k"], x["two_app_f"]),
            "{} -> {} ({} -> {})".format(x["low_ref_k"], x["low_two_k"], x["low_ref_f"],
                                         x["low_two_f"]),
            "{} [{}, {}]".format(pctpv(x["lr_share"]), pctpv(x["lr_lo"]), pctpv(x["lr_hi"])),
            "{} [{}, {}]".format(pctpv(x["l2_share"]), pctpv(x["l2_lo"]), pctpv(x["l2_hi"])),
            "{} / {}".format(x["cd_k"], x["cd_f"])]


HL_HEAD = ["priced", "instances", "costly", "low-cost", "costly referred K / FI / both",
           "costly applied K / FI", "applied with second price K / FI",
           "low-cost referred K without -> with second price (FI without -> with)",
           "low-cost share K [95% CI]", "low-cost share K with second price [95% CI]",
           "common denominator applied K / FI"]


def hl_macros(prefix, h, txt):
    add(prefix + "Priced", grp(h["priced"]), "{}: priced proposals".format(txt))
    add(prefix + "Instances", h["instances"], "{}: instances with a priced proposal".format(txt))
    for dtok, delta in DELTAS.items():
        for k, tok in HL_TOK.items():
            ftxt = (n24.HL_FIELDS[k][1] if k in n24.HL_FIELDS else
                    {"cd_k": "costly proposals applied on the known board, common denominator",
                     "cd_f": "costly proposals applied with full information, common "
                             "denominator"}[k])
            add(prefix + dtok + tok, grp(h[dtok][k]),
                "{}, delta = {:.2f}, tau = 0.20: {}".format(txt, delta, ftxt))
        add(prefix + dtok + "Undecided", grp(h[dtok]["und"]),
            "{}, delta = {:.2f}: undecided proposals".format(txt, delta))
        for key, tok, ftxt in (("lr", "LowRefK", "low-cost referral share, certificate on the "
                                                  "known board"),
                               ("l2", "LowTwoRefK", "low-cost referral share with the second "
                                                    "price, known board")):
            add(prefix + dtok + tok + "Share", pctv(h[dtok][key + "_share"]),
                "{}, delta = {:.2f}: {}".format(txt, delta, ftxt))
            add(prefix + dtok + tok + "Lo", pctv(h[dtok][key + "_lo"]),
                "{}, delta = {:.2f}: lower end of the 95% cluster-bootstrap interval of the "
                "same (n2 seed, 20,000 replicates, 60 instance clusters)".format(txt, delta))
            add(prefix + dtok + tok + "Hi", pctv(h[dtok][key + "_hi"]),
                "{}, delta = {:.2f}: upper end of the same interval".format(txt, delta))


def design_counts(recs, g, delta):
    c = [r for r in recs if n13.costly_of(r, delta) == 1]
    lw = [r for r in recs if n13.costly_of(r, delta) == 0]
    return OrderedDict(
        app_k=sum(1 for r in c if not n13.refers(r, g)),
        app_f=sum(1 for r in c if not n13.refers(r["fi"], g)),
        low_ref_k=sum(1 for r in lw if n13.refers(r, g)),
        low_ref_f=sum(1 for r in lw if n13.refers(r["fi"], g)),
        two_app_k=sum(1 for r in c if not n16.sp_flag(r, g)),
        two_low_k=sum(1 for r in lw if n16.sp_flag(r, g)))


def qstats(xs):
    a = np.asarray(xs, dtype=float)
    p10, med, p90 = (float(v) for v in np.percentile(a, [10, 50, 90]))
    return OrderedDict(n=len(xs), median=med, p10=p10, p90=p90, min=float(a.min()),
                       max=float(a.max()))


def boot_ci_here(inst_of, flags, instances):
    """A bootstrap written here with n2's seed and draw order (n23's self-test route)."""
    inst = sorted(instances)
    index = {v: j for j, v in enumerate(inst)}
    rng = np.random.default_rng(20261026)
    idx = rng.integers(0, len(inst), size=(20000, len(inst)))
    num = np.zeros(len(inst))
    den = np.zeros(len(inst))
    for i, f in zip(inst_of, flags):
        den[index[i]] += 1.0
        num[index[i]] += 1.0 if f else 0.0
    ns, ds = num[idx].sum(axis=1), den[idx].sum(axis=1)
    r = ns[ds > 0] / ds[ds > 0]
    lo, hi = np.percentile(r, [2.5, 97.5])
    return float(lo), float(hi)


# --------------------------------------------------------------------------- #
# Self-test (second code path)                                                 #
# --------------------------------------------------------------------------- #
def second_path(rep, reorder_ids, fams_p, fam_all, ids_priced):
    """Headline numbers under F from the raw files (csv/json) and the raw replay outputs."""
    rows = {}
    with open(ANALYSIS / "N11_rows_forecast.csv", encoding="utf-8") as fh:
        for x in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            rows.setdefault(x["reading"], {})[x["item_id"]] = x
    K = rows["K"]
    items = {}
    with open(RESULTS / "n11_decision_time" / "items.jsonl", encoding="utf-8") as fh:
        for ln in fh:
            if ln.strip():
                o = json.loads(ln)
                if o["set"] == "published":
                    items[o["item_id"]] = o
    fip = {}
    with open(RESULTS / "n11_forecast" / "fullinfo_direct.jsonl", encoding="utf-8") as fh:
        for ln in fh:
            if ln.strip():
                o = json.loads(ln)
                fip[o["uid"]] = o["p"]
    fan = {}
    with open(RESULTS / "n11_forecast" / "anchors_direct.jsonl", encoding="utf-8") as fh:
        for ln in fh:
            if ln.strip():
                o = json.loads(ln)
                if o["reading"] == "FI":
                    fan[(o["iid"], o["fk"], float(o["t_d"]))] = o["a"]
    anc = {}
    for o in json.loads((ANALYSIS / "ladder" / "rule_anchor.json").read_text(encoding="utf-8")):
        anc[(Path(o["instance_path"]).stem, ",".join(str(s) for s in o["frozen_seed"]))] = o
    br = {}
    with open(RESULTS / "oracle_v1" / "brackets.jsonl", encoding="utf-8") as fh:
        for ln in fh:
            if ln.strip():
                o = json.loads(ln)
                br[(o["instance_id"], o["fingerprint"])] = o
    fam = {}
    with open(ROOT / "code" / "suite" / "v0.2" / "suite.jsonl", encoding="utf-8") as fh:
        for ln in fh:
            if ln.strip():
                o = json.loads(ln)
                fam[o["item_id"]] = o["family_id"]

    def g(obj, x):
        v = (obj - x) / max(x, 1.0)
        return v if v > 0 else 0.0

    def cost_label(i, obj_orig, d):
        it = items[i]
        b = br[(it["instance_id"], D.BASE_FP)]
        lo_e, up_e = float(b["lower"]), float(b["upper"])
        if float(b["width_rel"]) < 1e-3:
            lo_e = up_e = 0.5 * (lo_e + up_e)
        a = float(anc[(it["instance_id"], it["frozen_seed"])]["wwt_original_bh"])
        xs = sorted({lo_e, up_e} | ({1.0} if lo_e < 1.0 < up_e else set()))
        ms = [g(obj_orig, x) - g(a, x) for x in xs]
        lo, hi = min(ms), max(ms)
        return 1 if lo > d else (0 if hi <= d else None)

    def den_of(i):
        b = br[(items[i]["instance_id"], D.BASE_FP)]
        return max(0.5 * (float(b["lower"]) + float(b["upper"])), 1.0)

    sp = {}
    for i in ids_priced:
        it = items[i]
        if i in reorder_ids:
            bF = rep[i]["boards"]["F"]
            ok, okf = bF["dt"]["stage_cert"] == "qual", bF["fi"]["stage_cert"] == "qual"
            ko, koo = bF["dt"]["obj"], bF["dt"]["obj_orig"]
            fo, foo = bF["fi"]["obj"], bF["fi"]["obj_orig"]
            ro = bF["rw"]["obj_orig"] if bF["rw"] is not None else None
        else:
            ok = okf = True
            ko, koo = it["dt_obj"], it["dt_obj_orig"]
            fo, foo = fip[i]["obj"], fip[i]["obj_orig"]
            ro = it["rw_obj_orig"]
        if not ok:
            continue
        lbk, lbf = it["dt_lb"], fip[i]["lb"]
        fa = fan[(it["instance_id"], it["frozen_seed"], float(it["t_d"]))]
        gk = (ko - lbk) / max(lbk, 1.0)
        ref_k = gk > 0.20
        field = K[i]["split"] == "field_changing"
        two_k = ref_k or (field and (koo - it["an_lb"]) / max(it["an_lb"], 1.0) > 0.20)
        if okf:
            gf = (fo - lbf) / max(lbf, 1.0)
            ref_f = gf > 0.20
            two_f = ref_f or (field and (foo - fa["lb"]) / max(fa["lb"], 1.0) > 0.20)
            cdf = max(0.0, fo - lbf) / den_of(i) > 0.20
        else:
            ref_f = two_f = cdf = True
        sp[i] = dict(ref_k=ref_k, ref_f=ref_f, two_k=two_k, two_f=two_f,
                     cdk=max(0.0, ko - lbk) / den_of(i) > 0.20, cdf=cdf,
                     c20=None if ro is None else cost_label(i, ro, 0.20),
                     c10=None if ro is None else cost_label(i, ro, 0.10),
                     inst=it["instance_id"], fam=fam[i])
    out = OrderedDict()
    c20 = [i for i in sp if sp[i]["c20"] == 1]
    c10 = [i for i in sp if sp[i]["c10"] == 1]
    l20 = [i for i in sp if sp[i]["c20"] == 0]
    out["costly20"] = len(c20)
    out["costly10"] = len(c10)
    out["ref_k20"] = sum(1 for i in c20 if sp[i]["ref_k"])
    out["ref_f20"] = sum(1 for i in c20 if sp[i]["ref_f"])
    out["app_k10"] = sum(1 for i in c10 if not sp[i]["ref_k"])
    out["app_f10"] = sum(1 for i in c10 if not sp[i]["ref_f"])
    out["two_app_k10"] = sum(1 for i in c10 if not sp[i]["two_k"])
    out["low_ref_k20"] = sum(1 for i in l20 if sp[i]["ref_k"])
    out["low_two_k20"] = sum(1 for i in l20 if sp[i]["two_k"])
    out["low_ref_f20"] = sum(1 for i in l20 if sp[i]["ref_f"])
    out["cd_k20"] = sum(1 for i in c20 if not sp[i]["cdk"])
    out["cd_f20"] = sum(1 for i in c20 if not sp[i]["cdf"])
    out["cd_k10"] = sum(1 for i in c10 if not sp[i]["cdk"])
    lo, hi = boot_ci_here([sp[i]["inst"] for i in l20], [sp[i]["ref_k"] for i in l20],
                          {items[i]["instance_id"] for i in items})
    out["lr20"] = "{} [{}, {}]".format(pctv(out["low_ref_k20"] / len(l20)), pctv(lo), pctv(hi))
    out["dis"] = sum(1 for i in sp if sp[i]["ref_k"] != sp[i]["ref_f"])
    ex = [i for i in sp if sp[i]["fam"] not in fam_all]
    out["exall_costly20"] = sum(1 for i in ex if sp[i]["c20"] == 1)
    out["exall_app_k10"] = sum(1 for i in ex if sp[i]["c10"] == 1 and not sp[i]["ref_k"])
    pf = [i for i in sp if sp[i]["fam"] in fams_p]
    out["pfam_costly20"] = sum(1 for i in pf if sp[i]["c20"] == 1)
    out["pfam_ref_k20"] = sum(1 for i in pf if sp[i]["c20"] == 1 and sp[i]["ref_k"])
    d = [rep[i]["boards"]["F"]["rw"]["obj_orig"] - rep[i]["boards"]["S"]["rw"]["obj_orig"]
         for i in sorted(reorder_ids)]
    out["dmg_median"] = bh2(float(np.median(np.array(d))))
    out["dmg_lower"] = sum(1 for v in d if v < -EPS)
    return out


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main(argv):
    selftest_only = "--selftest" in argv
    t_start = time.time()
    for k, p in IN25.items():
        if not Path(p).is_file() and k not in NOT_SHIPPED_OK:
            raise SystemExit("missing input {}: {}".format(k, p))
    say("design.md sha256 {} (asserted); frozen prefixes asserted; {} l1adapter .py files "
        "hashed".format(DESIGN_SHA[:12], len(ADAPTER0)))
    hashes, items_dt, _pub, boot, fc = n13.load_inputs()
    check("60 bootstrap clusters, 20,000 replicates, n2 seed",
          boot.k == 60 and boot.idx.shape == (20000, 60) and n2.SEED == 20261026)
    recs, by, spfi, site, _frecs = n20.build(items_dt, fc, boot)
    check("1,356 priced proposals", len(recs) == 1356, len(recs))
    recs_by = {r["item_id"]: r for r in recs}
    # 0. the published headline by the reused functions
    n16.section0(boot, recs)
    n18.section0(recs, by, spfi, site)
    n20.section0(recs)
    say("published headline asserted (n16, n18, n20 section 0)")
    texts = {"planner_report": Path(n24.IN24["planner_report"]).read_text(encoding="utf-8")}
    suite_n13 = {it["item_id"]: it for it in n13.read_jsonl(n13.IN["suite"])}
    S = n24.setup_b(suite_n13, items_dt, recs, texts)
    dc = D.Checker()
    suite = OrderedDict((x["item_id"], x) for x in D.load_published(dc))
    check("published suite loads through suite_gate (SHA-256 asserted)", not dc.failures)
    check("the two suite readers hold the same items", set(suite) == set(suite_n13))
    items_by = by
    can = S["can"]
    fam = {i: suite_n13[i]["family_id"] for i in suite_n13}
    reorder_ids = sorted(r["item_id"] for r in recs if "reorder" in can[r["item_id"]])
    check("364 priced proposals carry a reorder (N24 block B2)", len(reorder_ids) == 364,
          len(reorder_ids))
    noreo = sorted(r["item_id"] for r in recs if "reorder" not in can[r["item_id"]])
    sample_ids = sorted(random.Random(SAMPLE_SEED).sample(noreo, SAMPLE_N))
    unpriced = sorted(i for i, it in items_by.items() if "reorder" in can[i]
                      and i not in recs_by)
    unp_iss = [i for i in unpriced if items_by[i]["issuable"]]
    unp_not = [i for i in unpriced if not items_by[i]["issuable"]]
    check("660 suite items carry a reorder in the reference proposal",
          sum(1 for i in suite_n13 if "reorder" in can[i]) == 660)
    check("issuable reorder items = priced + issuable refused (409)",
          len(reorder_ids) + len(unp_iss) == 409, (len(reorder_ids), len(unp_iss)))
    check("251 reorder items are not issuable", len(unp_not) == 251, len(unp_not))
    for i in reorder_ids:
        check("items.jsonl op_types carry the reorder", "reorder" in
              items_by[i]["op_types"].split("|"), i)
    MD.extend(["# N25: the direct benchmark under a finish-to-start reading of reorder "
               "({})".format(VERSION), "",
               "Generated by `code/scripts/n25_finish_to_start.py` on core 14 (one thread): "
               "deterministic dispatcher replays (n11_decision_time.gen_price, no solver, no "
               "time budget), no model call, no GPU. Post hoc sensitivity analysis. Frozen "
               "design: `results/n25_finish_to_start/design.md` (sha256 {}), addendum "
               "`results/n25_finish_to_start/addendum.md`. Reused: n24 (imported), and through "
               "it n20/n16/n18/n13 loaded from source with the core allowance set to core 14 in "
               "memory (files untouched): n20.build's records, n13.costly_of, the published "
               "flags, n16.sp_flag, n24.headline (n20.tally, n13.score), n2.Boot (seed {}, {} "
               "replicates, {} instance clusters).".format(DESIGN_SHA, n2.SEED, n2.B_BOOT,
                                                          boot.k), "",
               "Reading S is the published dispatcher (start-after-start: a successor is "
               "eligible once its predecessors have started). Reading F is the same dispatcher "
               "with the eligibility test replaced in memory: a successor is eligible once "
               "every predecessor has completed (end <= now), and the trades of the successors "
               "of an order that completes join the sweep at that instant. Everything else is "
               "unchanged (ATC, seed 0, frozen set 'fix', batch rules, a freeze wins over a "
               "precedence edge, apply.py, the guard's stages, the logged bounds and floor). "
               "K = known board at t_d, FI = full-information board at t_d, realised = the "
               "whole-window run from t_d. bh = business hours.", "",
               "## 0. Published headline", "",
               "n16.section0, n18.section0 and n20.section0 pass on n20.build's records "
               "(1,356 priced proposals; at delta = tau = 0.20, 186 costly, 1,170 low-cost; "
               "168 costly referred on K and the same 168 with FI; 18 applied; the second "
               "price refers all 18; 15 low-cost referred, 22 with the second price; common "
               "denominator 20 / 18, and 40 / 35 at 0.10).", ""])
    # P. probes
    resP = block_p()
    say("probes passed (a, b, c)")
    # R. replay
    anchors = D.load_anchor_records()
    full_br = D.full_brackets()
    fi_logged = {x["uid"]: x for x in n13.read_jsonl(n13.IN["fullinfo"])}
    fa_logged = {}
    for a in n13.read_jsonl(n13.IN["anchors_fc"]):
        if a["reading"] == "FI":
            fa_logged[(a["iid"], a["fk"], float(a["t_d"]))] = a["a"]
    check("every priced proposal has a full-information record priced on FI",
          all(fi_logged[i]["p"]["stage_cert"] == "qual" for i in recs_by), "FI")
    kinds = ([(i, "reorder") for i in reorder_ids] + [(i, "sample") for i in sample_ids]
             + [(i, "unpriced_issuable") for i in unp_iss]
             + [(i, "unpriced_not_issuable") for i in unp_not])
    tasks = build_tasks(kinds, suite, items_by, anchors)
    say("replaying {} reorder + {} sample + {} unpriced proposals on {} instances, core {}".format(
        len(reorder_ids), len(sample_ids), len(unpriced), len(tasks), sorted(_aff)))
    t_rep = time.time()
    cache = os.environ.get("N25_REPLAY_CACHE")
    if cache and Path(cache).is_file():
        import pickle
        if not selftest_only:
            raise SystemExit("[n25] N25_REPLAY_CACHE is for development runs with --selftest; "
                             "the outputs need a fresh replay")
        with open(cache, "rb") as fh:
            results = pickle.load(fh)
        say("replay loaded from the development cache " + cache)
    else:
        results = run_replay(tasks, items_by)
        if cache:
            import pickle
            with open(cache, "wb") as fh:
                pickle.dump(results, fh)
    wall_rep = time.time() - t_rep
    rep = OrderedDict()
    out_sites = {}
    for res in results:
        for x in res["items"]:
            check("one replay per proposal", x["item_id"] not in rep, x["item_id"])
            rep[x["item_id"]] = x
        for k, s in res["sites"].items():
            out_sites[(res["iid"], k)] = s
    check("every proposal replayed", set(rep) == {i for i, _k in kinds}, len(rep))
    # S. the run-fatal tie of every S board
    valsS = assert_s(rep, out_sites, recs_by, items_by, fi_logged, fa_logged, anchors, full_br)
    n_sites = assert_sites_f(out_sites, items_by, fa_logged, rep)
    n_sample = assert_sample(rep, items_by, fi_logged)
    check("50 sampled proposals without a reorder asserted identical", n_sample == SAMPLE_N)
    say("S replay tied to every stored total ({} reorder proposals, their sites under F ({} "
        "checks), {} sampled)".format(len(valsS), n_sites, n_sample))
    # F. values and records
    valsF = OrderedDict()
    recsS, recsF = [], []
    not_priced_F = []
    deadlocks = []
    for r in recs:
        i = r["item_id"]
        if i not in valsS:
            recsS.append(r)
            recsF.append(r)
            continue
        x = rep[i]
        it = items_by[i]
        bF = x["boards"]["F"]
        for bk in ("dt", "fi", "rw"):
            b = bF[bk]
            if b["term_feas"] == "execution_failed" or (b["digest"] is None
                                                        and b["stage_feas"] != "schema"):
                deadlocks.append((i, bk, b["term_feas"], b["codes"]))
            if b["digest"] is not None:
                check("F: every schedule complete ({})".format(bk), b["complete"], (i, bk))
                check("F: every unfrozen successor starts at or after its predecessor's end "
                      "({})".format(bk), b["fts_viol"] == 0, (i, bk, b["edge_detail"]))
        if bF["dt"]["digest"] is not None:
            check("F, K: stages 1-2 outcome equals S (schema, feasibility)",
                  (bF["dt"]["term_feas"], bF["dt"]["stage_feas"])
                  == (x["boards"]["S"]["dt"]["term_feas"], x["boards"]["S"]["dt"]["stage_feas"]),
                  i)
        if bF["dt"]["stage_cert"] == "qual":
            close("F, K: the bound gen_price computes = the logged bound", bF["dt"]["lb"],
                  it["dt_lb"], SUM_TOL, i)
            close("F, K: D-REL2 reference = the logged one", bF["dt"]["ref2"], it["dt_ref2"],
                  SUM_TOL, i)
        if bF["fi"]["stage_cert"] == "qual":
            close("F, FI: the bound gen_price computes = the logged bound", bF["fi"]["lb"],
                  fi_logged[i]["p"]["lb"], SUM_TOL, i)
            close("F, FI: D-REL2 reference = the logged one", bF["fi"]["ref2"],
                  fi_logged[i]["p"]["ref2"], SUM_TOL, i)
        a = anchors[(it["instance_id"], it["frozen_seed"])]
        anchor = float(a["wwt_original_bh"])
        base = full_br.get((it["instance_id"], D.BASE_FP))
        fa_a = fa_logged[(it["instance_id"], it["frozen_seed"], float(it["t_d"]))]
        v = values_of(bF, it, fi_logged[i], fa_a, base, anchor)
        valsF[i] = v
        recsS.append(record_of(r, valsS[i]))
        if not v["priced_k"]:
            not_priced_F.append(i)
            continue
        recsF.append(record_of(r, v))
    say("F records built: {} priced under F ({} reorder proposals not priced on K under F); "
        "{} boards without a schedule".format(len(recsF), len(not_priced_F), len(deadlocks)))
    md("## 1. Checks (all run-fatal, all passed)", "",
       "- Frozen files: n16_robustness.py {}, n13_fromlogs.py {}, n11_decision_time.py {}, "
       "n10_field_change.py {} (sha256 prefixes, before and after the run). Every .py file under "
       "code/l1adapter/ has the same sha256 before and after the run (results/n25_finish_to_start/"
       "l1adapter_sha256.json).".format(*[_FROZEN0[k][:12] for k in FROZEN]),
       "- Probes: (a), (b), (c) of the design pass (block P).",
       "- S replay (unpatched module) of the {} priced reorder proposals: on K the terminals, "
       "codes, adjusted and original-field objectives, bound, certificate and D-REL2 reference "
       "equal items.jsonl; on FI every field of fullinfo_direct.jsonl; on the realised run the "
       "terminals and both objectives; the damage, the realised-cost interval, the label at "
       "0.20 and 0.10, every design's price and flag on K and FI, both second prices and the "
       "common-denominator prices equal the published records.".format(len(valsS)),
       "- S-off (patched function, switch off) gives the unpatched module's known-board "
       "schedule byte for byte on all {} reorder proposals.".format(len(valsS)),
       "- The no-proposal runs of the {} sites of the reorder proposals, recomputed under F, "
       "equal the stored totals (K anchor, FI anchor, realised run = no-AI anchor).".format(
           len({(x["iid"], x["site"]) for x in rep.values() if x["kind"] == "reorder"})),
       "- {} sampled priced proposals without a reorder (random.Random({}).sample) give the "
       "same schedule byte for byte, the same totals and the same terminals under F and S on "
       "all three boards, and S equals the stored totals.".format(n_sample, SAMPLE_SEED),
       "- Under F every schedule is complete, and on every board every unfrozen successor starts "
       "at or after its predecessor's end; the bound and the D-REL2 reference that gen_price "
       "computes under F equal the logged ones; the schema and feasibility stages give the same "
       "outcome as under S on K.", "")
    md_table(["assertion", "largest absolute difference"],
             [[w, "{:.3g}".format(vv)] for w, vv in sorted(MAXDIFF.items())])

    # ---------------- headline S and F ----------------
    resH = OrderedDict()
    for rd, rr in (("S", recsS), ("F", recsF)):
        for p, st in POPS.items():
            resH[(rd, p)] = n24.headline(boot, [r for r in rr if st is None or r["stratum"] == st])
    # S equals the published values (N24 Full row, N20 block A macros)
    m20 = n13.macros_of(IN25["n20_macros"])
    for dtok, delta in DELTAS.items():
        for k, vv in n24.FULL_EXPECT[delta].items():
            check("S pooled {} at {:.2f} = {}".format(k, delta, vv), resH[("S", "Pooled")][dtok][k]
                  == vv, (k, resH[("S", "Pooled")][dtok][k]))
        for p in POPS:
            for k, tok in n24.N20_TOK.items():
                check("S {} {} at {:.2f} = N20 macro".format(p, k, delta),
                      grp(resH[("S", p)][dtok][k]) == m20["nTwentyA" + p + dtok + tok],
                      (p, k, resH[("S", p)][dtok][k]))
    for rd in RDS:
        for dtok in DELTAS:
            for k in HL_TOK:
                check("strata sum to pooled ({} {} {})".format(rd, dtok, k),
                      sum(resH[(rd, q)][dtok][k] for q in POPS if q != "Pooled")
                      == resH[(rd, "Pooled")][dtok][k])
    for rd in RDS:
        for p in POPS:
            hl_macros("H" + p + rd, resH[(rd, p)],
                      "[H] {}, reading {}".format(n20.POP_NAME[p], rd))
    md("## 2. Headline: reading S beside reading F (layout of Block C of N24)", "",
       "Certificate at tau = 0.20 (n24.headline: n20.tally and n13.score). K = known board, FI "
       "= full information. Second price on field edits (n16.sp_flag on K, n20's two_f rule "
       "on FI). Low-cost referral shares with the n2 cluster-bootstrap 95% interval over the 60 "
       "instances (per stratum: the same bootstrap object; replicates without a proposal of "
       "the stratum dropped). Common denominator: applied = costly with gap_bh / den at most "
       "0.20. Reading S reproduces the published values and the N20 block A macros "
       "(asserted). Only the 364 proposals that carry a reorder can change.", "")
    for dtok, delta in DELTAS.items():
        body = []
        for p in POPS:
            for rd in RDS:
                body.append([p, rd] + hl_row(resH[(rd, p)], dtok))
        md("### delta = {:.2f}".format(delta), "")
        md_table(["population", "reading"] + HL_HEAD, body)

    # ---------------- the other designs ----------------
    exp_s = {0.20: dict(app_k=(18, 18, 18, 18, 17), app_f=(18, 18, 18, 18, 16),
                        low_ref_k=(15, 14, 80, 33, 81), two_app_k=(0, 0, 0, 0, 0),
                        two_low_k=(22, 21, 86, 40, 87)),
             0.10: dict(app_k=(25, 26, 21, 21, 20))}
    resG = OrderedDict()
    for rd, rr in (("S", recsS), ("F", recsF)):
        for dtok, delta in DELTAS.items():
            for j, g in enumerate(DESIGNS):
                o = design_counts(rr, g, delta)
                resG[(rd, dtok, g)] = o
                if rd == "S":
                    for k, tup in exp_s[delta].items():
                        check("S design {} {} at {:.2f} = N16 section 0".format(g, k, delta),
                              o[k] == tup[j], (g, k, o[k]))
                for k, tok in (("app_k", "AppK"), ("app_f", "AppFI"), ("low_ref_k", "LowRefK"),
                               ("low_ref_f", "LowRefFI"), ("two_app_k", "TwoAppK"),
                               ("two_low_k", "TwoLowRefK")):
                    add("G" + DES_TOK[g] + rd + dtok + tok, grp(o[k]),
                        "[G] {} at its own threshold ({}), reading {}, delta = {:.2f}: {}".format(
                            g, SETTINGS[g], rd, delta,
                            {"app_k": "costly proposals applied on the known board",
                             "app_f": "costly proposals applied with full information",
                             "low_ref_k": "low-cost proposals referred on the known board",
                             "low_ref_f": "low-cost proposals referred with full information",
                             "two_app_k": "costly proposals applied on the known board with the "
                                          "second price on field edits",
                             "two_low_k": "low-cost proposals referred on the known board with "
                                          "the second price"}[k]))
    md("## 3. Every design at its own threshold, S beside F", "",
       "Thresholds: G-CERT and G-CERT-M 0.20, D-REL1 and D-REL2 0.02, D-ABS 0.8119 weighted bh. "
       "Prices on the logged bound and anchors of each board. Reading S equals N16 section 0 "
       "(asserted).", "")
    for dtok, delta in DELTAS.items():
        body = []
        for g in DESIGNS:
            for rd in RDS:
                o = resG[(rd, dtok, g)]
                body.append([g, rd, "{} / {}".format(o["app_k"], o["app_f"]),
                             "{} / {}".format(o["low_ref_k"], o["low_ref_f"]),
                             o["two_app_k"], o["two_low_k"]])
        md("### delta = {:.2f}".format(delta), "")
        md_table(["design", "reading", "costly applied K / FI", "low-cost referred K / FI",
                  "costly applied K, second price", "low-cost referred K, second price"], body)

    # ---------------- schedule changes, damage changes ----------------
    rbyS = {r["item_id"]: r for r in recsS}
    rbyF = {r["item_id"]: r for r in recsF}
    ch = OrderedDict()
    for bk, (btok, bname) in BOARDS.items():
        diff = [i for i in reorder_ids if rep[i]["boards"]["S"][bk]["digest"]
                != rep[i]["boards"]["F"][bk]["digest"]]
        ovl = [i for i in reorder_ids if rep[i]["boards"]["S"][bk]["fts_viol"] > 0]
        fzw = [i for i in reorder_ids if rep[i]["boards"]["F"][bk]["freeze_wins"] > 0]
        fzs = [i for i in reorder_ids if rep[i]["boards"]["S"][bk]["freeze_wins"] > 0]
        edges = sum(rep[i]["boards"]["S"][bk]["edges"] for i in reorder_ids)
        ovl_e = sum(rep[i]["boards"]["S"][bk]["fts_viol"] for i in reorder_ids)
        same_ovl = [i for i in ovl if i not in diff]
        diff_no_ovl = [i for i in diff if i not in ovl]
        ch[bk] = OrderedDict(diff=diff, ovl=ovl, fzw=fzw, fzs=fzs, edges=edges, ovl_e=ovl_e,
                             same_ovl=same_ovl, diff_no_ovl=diff_no_ovl)
        check("a schedule whose unfrozen successor starts before its predecessor ends under S "
              "changes under F ({})".format(bk), all(rep[i]["boards"]["F"][bk]["digest"]
                                                    != rep[i]["boards"]["S"][bk]["digest"]
                                                    for i in ovl))
        add("SchedDiff" + btok, grp(len(diff)),
            "[D] reorder proposals (of {}) whose {} schedule under F differs from S".format(
                len(reorder_ids), bname))
        add("OverlapS" + btok, grp(len(ovl)),
            "[D] reorder proposals whose {} schedule under S starts an unfrozen successor "
            "before its predecessor has ended (at least one edge)".format(bname))
        add("OverlapEdgesS" + btok, grp(ovl_e),
            "[D] reorder edges (of {}) on the {} under S whose unfrozen successor starts before "
            "the predecessor ends".format(edges, bname))
        add("EdgesS" + btok, grp(edges), "[D] reorder edges on the {} over the reorder "
                                         "proposals".format(bname))
        add("FreezeWinsF" + btok, grp(len(fzw)),
            "[D] reorder proposals with an edge into a frozen order that starts before its "
            "predecessor ends under F on the {} (the freeze wins)".format(bname))
    dd = [valsF[i]["dmg"] - valsS[i]["dmg"] for i in reorder_ids
          if valsF[i]["dmg"] is not None]
    no_real_F = [i for i in reorder_ids if valsF[i]["dmg"] is None]
    add("NoRealisedF", grp(len(no_real_F)), "[D] reorder proposals without a realised run under "
                                            "F (deadlock)")
    qd = qstats(dd)
    n_lower = sum(1 for v in dd if v < -EPS)
    n_higher = sum(1 for v in dd if v > EPS)
    n_equal = len(dd) - n_lower - n_higher
    for nm, key in (("Median", "median"), ("PTen", "p10"), ("PNinety", "p90"), ("Min", "min"),
                    ("Max", "max")):
        add("DmgDiff" + nm, bhm(qd[key]),
            "[D] realised damage under F minus under S over the {} reorder proposals: {}, "
            "weighted bh".format(len(dd), {"median": "median", "p10": "10th percentile "
                                           "(linear)", "p90": "90th percentile (linear)",
                                           "min": "minimum", "max": "maximum"}[key]))
    add("DmgLower", grp(n_lower), "[D] reorder proposals whose realised damage is lower under F "
                                  "(by more than 1e-9 bh)")
    add("DmgLowerShare", pct(n_lower, len(dd)), "[D] the same as a share of the reorder "
                                                "proposals")
    add("DmgHigher", grp(n_higher), "[D] reorder proposals whose realised damage is higher "
                                    "under F")
    add("DmgHigherShare", pct(n_higher, len(dd)), "[D] the same as a share")
    add("DmgEqual", grp(n_equal), "[D] reorder proposals whose realised damage is equal within "
                                  "1e-9 bh")
    pkd = [valsF[i]["pk"]["G-CERT"] - valsS[i]["pk"]["G-CERT"] for i in reorder_ids
           if valsF[i]["priced_k"]]
    pfd = [valsF[i]["pf"]["G-CERT"] - valsS[i]["pf"]["G-CERT"] for i in reorder_ids
           if valsF[i]["priced_fi"]]
    for tok, xs in (("K", pkd), ("FI", pfd)):
        add("CertDiff" + tok + "Higher", grp(sum(1 for v in xs if v > EPS)),
            "[D] reorder proposals whose certificate price on {} is higher under F".format(tok))
        add("CertDiff" + tok + "Lower", grp(sum(1 for v in xs if v < -EPS)),
            "[D] reorder proposals whose certificate price on {} is lower under F".format(tok))
    md("## 4. What changes for the reorder proposals", "",
       "Schedule = the canonical schedule JSON (every assignment). Overlap under S = at least "
       "one edge whose unfrozen successor starts before the predecessor ends (the case the two "
       "readings disagree on). Freeze wins = an edge into a frozen order that starts before the "
       "predecessor ends (the documented conflict order; the frozen order keeps its slot).", "")
    body = []
    for bk, (btok, bname) in BOARDS.items():
        c = ch[bk]
        body.append([bname, len(reorder_ids), len(c["diff"]), len(c["ovl"]),
                     "{} of {}".format(c["ovl_e"], c["edges"]), len(c["diff_no_ovl"]),
                     len(c["fzs"]), len(c["fzw"])])
    md_table(["board", "reorder proposals", "schedule differs under F",
              "overlap under S (proposals)", "overlapping edges under S",
              "differs under F without an overlap under S", "freeze wins under S",
              "freeze wins under F"], body)
    md("Realised damage, F minus S (weighted bh) over the {} reorder proposals: median {}, "
       "p10 {}, p90 {}, min {}, max {}; lower under F {} ({}), higher {} ({}), equal {}.".format(
           len(dd), bh2(qd["median"]), bh2(qd["p10"]), bh2(qd["p90"]), bh2(qd["min"]),
           bh2(qd["max"]), n_lower, pctp(n_lower, len(dd)), n_higher, pctp(n_higher, len(dd)),
           n_equal), "",
       "Certificate price, F minus S: on K higher for {} and lower for {} of {}; on FI higher "
       "for {} and lower for {} of {}.".format(
           sum(1 for v in pkd if v > EPS), sum(1 for v in pkd if v < -EPS), len(pkd),
           sum(1 for v in pfd if v > EPS), sum(1 for v in pfd if v < -EPS), len(pfd)), "")

    # ---------------- label changes, disposition changes ----------------
    md("## 5. Label and disposition changes (reorder proposals)", "")
    lab = OrderedDict()
    for dtok, delta in DELTAS.items():
        tr = Counter()
        for i in reorder_ids:
            cs = n13.costly_of(rbyS[i], delta)
            cf = n13.costly_of(rbyF[i], delta) if i in rbyF else "not priced"
            tr[(cs, cf)] += 1
        lab[dtok] = tr
        add("Label" + dtok + "CostlyToLow", grp(tr[(1, 0)]),
            "[L] delta = {:.2f}: reorder proposals costly under S and low-cost under F".format(
                delta))
        add("Label" + dtok + "LowToCostly", grp(tr[(0, 1)]),
            "[L] delta = {:.2f}: reorder proposals low-cost under S and costly under F".format(
                delta))
        add("Label" + dtok + "ToUndecided", grp(sum(v for (a, b), v in tr.items()
                                                     if b is None and a is not None)),
            "[L] delta = {:.2f}: reorder proposals decided under S and undecided under F".format(
                delta))
        add("Label" + dtok + "Same", grp(sum(v for (a, b), v in tr.items() if a == b)),
            "[L] delta = {:.2f}: reorder proposals with the same label under S and F".format(
                delta))
    body = []
    for dtok, delta in DELTAS.items():
        for (a, b), v in sorted(lab[dtok].items(), key=lambda kv: str(kv[0])):
            body.append(["{:.2f}".format(delta), lbl(a), b if isinstance(b, str) else lbl(b), v])
    md_table(["delta", "label under S", "label under F", "reorder proposals"], body)
    disp = OrderedDict()
    for btok, fk in (("K", lambda r: r["ref_k"]), ("FI", lambda r: r["ref_f"]),
                     ("KTwo", lambda r: r["two_k"]), ("FITwo", lambda r: r["two_f"])):
        ra = [i for i in reorder_ids if i in rbyF and fk(rbyS[i]) and not fk(rbyF[i])]
        ar = [i for i in reorder_ids if i in rbyF and not fk(rbyS[i]) and fk(rbyF[i])]
        disp[btok] = (ra, ar)
        nm = {"K": "the certificate on the known board", "FI": "the certificate with full "
              "information", "KTwo": "the certificate with the second price on the known board",
              "FITwo": "the certificate with the second price with full information"}[btok]
        add("Disp" + btok + "RefToApp", grp(len(ra)),
            "[L] reorder proposals referred under S and applied under F by {}".format(nm))
        add("Disp" + btok + "AppToRef", grp(len(ar)),
            "[L] reorder proposals applied under S and referred under F by {}".format(nm))
    body = []
    for btok, (ra, ar) in disp.items():
        body.append([btok, len(ra), ", ".join(ra) or "-", len(ar), ", ".join(ar) or "-"])
    md_table(["disposition", "referred under S, applied under F", "items",
              "applied under S, referred under F", "items"], body)
    # the label-changed and disposition-changed proposals one by one
    moved = sorted({i for i in reorder_ids if i in rbyF and (
        any(n13.costly_of(rbyS[i], d) != n13.costly_of(rbyF[i], d) for d in DELTAS.values())
        or rbyS[i]["ref_k"] != rbyF[i]["ref_k"] or rbyS[i]["ref_f"] != rbyF[i]["ref_f"]
        or rbyS[i]["two_k"] != rbyF[i]["two_k"])})
    if moved:
        body = []
        for i in moved:
            a, b = rbyS[i], rbyF[i]
            body.append([i, a["st"], fam[i], "{} -> {}".format(bh2(a["dmg"]), bh2(b["dmg"])),
                         "{} -> {}".format(lbl(n13.costly_of(a, 0.20)),
                                           lbl(n13.costly_of(b, 0.20))),
                         "{} -> {}".format(lbl(n13.costly_of(a, 0.10)),
                                           lbl(n13.costly_of(b, 0.10))),
                         "{:.3f} -> {:.3f}".format(a["p_G-CERT"], b["p_G-CERT"]),
                         "{:.3f} -> {:.3f}".format(a["fi"]["p_G-CERT"],
                                                   b["fi"]["p_G-CERT"]
                                                   if b["fi"]["p_G-CERT"] is not None else
                                                   float("nan")),
                         "{} -> {}".format(int(a["ref_k"]), int(b["ref_k"])),
                         "{} -> {}".format(int(a["ref_f"]), int(b["ref_f"]))])
        md("Reorder proposals whose label or certificate disposition changes:", "")
        md_table(["item", "stratum", "family", "damage S -> F (bh)", "label 0.20",
                  "label 0.10", "certificate price K", "certificate price FI",
                  "referred K", "referred FI"], body)

    # ---------------- discordance K vs FI ----------------
    md("## 6. Proposals the certificate refers on one board only (K against FI)", "")
    dis = OrderedDict()
    for rd, rr in (("S", recsS), ("F", recsF)):
        allp = [r for r in rr if r["ref_k"] != r["ref_f"]]
        dis[rd] = OrderedDict(all=allp)
        add("Dis" + rd + "All", grp(len(allp)),
            "[K] reading {}: priced proposals the certificate refers on exactly one of K and "
            "FI".format(rd))
        add("Dis" + rd + "Reorder", grp(sum(1 for r in allp if r["item_id"] in valsS)),
            "[K] reading {}: of these, proposals that carry a reorder".format(rd))
        for dtok, delta in DELTAS.items():
            c = [r for r in allp if n13.costly_of(r, delta) == 1]
            lw = [r for r in allp if n13.costly_of(r, delta) == 0]
            dis[rd][dtok] = (c, lw)
            add("Dis" + rd + dtok + "Costly", grp(len(c)),
                "[K] reading {}, delta = {:.2f}: costly proposals referred on exactly one "
                "board".format(rd, delta))
            add("Dis" + rd + dtok + "CostlyKOnly", grp(sum(1 for r in c if r["ref_k"])),
                "[K] reading {}, delta = {:.2f}: costly proposals referred on K only".format(
                    rd, delta))
            add("Dis" + rd + dtok + "CostlyFIOnly", grp(sum(1 for r in c if r["ref_f"])),
                "[K] reading {}, delta = {:.2f}: costly proposals referred with FI only".format(
                    rd, delta))
            add("Dis" + rd + dtok + "Low", grp(len(lw)),
                "[K] reading {}, delta = {:.2f}: low-cost proposals referred on exactly one "
                "board".format(rd, delta))
    body = []
    for rd in RDS:
        for dtok, delta in DELTAS.items():
            c, lw = dis[rd][dtok]
            body.append([rd, "{:.2f}".format(delta), len(dis[rd]["all"]),
                         sum(1 for r in dis[rd]["all"] if r["item_id"] in valsS),
                         "{} (K only {}, FI only {})".format(len(c), sum(1 for r in c if r["ref_k"]),
                                                             sum(1 for r in c if r["ref_f"])),
                         "{} (K only {}, FI only {})".format(len(lw),
                                                             sum(1 for r in lw if r["ref_k"]),
                                                             sum(1 for r in lw if r["ref_f"]))])
    md_table(["reading", "delta", "discordant (all priced)", "of which carry a reorder",
              "costly discordant", "low-cost discordant"], body)
    ids_s = {r["item_id"] for r in dis["S"]["all"]}
    ids_f = {r["item_id"] for r in dis["F"]["all"]}
    lst = sorted(ids_f | ids_s, key=lambda i: (i not in valsS, i))
    body = []
    for i in lst:
        a = rbyS[i]
        b = rbyF.get(i)
        if b is None:
            continue
        if i not in valsS and i in ids_s and i in ids_f:
            continue                                     # unchanged non-reorder ones: counted
        body.append([i, a["st"], fam[i], "yes" if i in valsS else "no",
                     "yes" if i in ids_s else "no", "yes" if i in ids_f else "no",
                     "{} / {}".format(lbl(n13.costly_of(b, 0.20)), lbl(n13.costly_of(b, 0.10))),
                     "{:.3f} / {:.3f}".format(b["p_G-CERT"], b["fi"]["p_G-CERT"]
                                              if b["fi"]["p_G-CERT"] is not None else float("nan")),
                     "K" if b["ref_k"] else ("FI" if b["ref_f"] else "-")])
    md("Discordant proposals that carry a reorder, or whose discordance changes between the "
       "readings (the {} non-reorder proposals discordant under both readings are counted above "
       "and not listed):".format(len([i for i in ids_s & ids_f if i not in valsS])), "")
    if body:
        md_table(["item", "stratum", "family", "carries reorder", "discordant under S",
                  "discordant under F", "label under F 0.20 / 0.10",
                  "certificate price under F K / FI", "referred under F on"], body)
    else:
        md("(none)", "")

    # ---------------- restricted headlines ----------------
    subs = OrderedDict([
        ("ExAll", ("without the families of every disputed group",
                   lambda r: fam[r["item_id"]] not in S["fam_all"])),
        ("PFam", ("the four precedence families of group P alone",
                  lambda r: fam[r["item_id"]] in S["fams"]["P"])),
    ])
    check("group P has four families", len(S["fams"]["P"]) == 4, S["fams"]["P"])
    m24 = n13.macros_of(IN25["n24_macros"])
    resR = OrderedDict()
    for sk, (txt, keep) in subs.items():
        for rd, rr in (("S", recsS), ("F", recsF)):
            resR[(sk, rd)] = n24.headline(boot, [r for r in rr if keep(r)])
            hl_macros("R" + sk + rd, resR[(sk, rd)], "[R] {}, reading {}".format(txt, rd))
    for dtok in DELTAS:
        for k, tok in HL_TOK.items():
            check("S without every disputed family {} = N24 CExAll".format(k),
                  grp(resR[("ExAll", "S")][dtok][k]) == m24["nTwentyFourCExAll" + dtok + tok],
                  (k, resR[("ExAll", "S")][dtok][k]))
            check("S in the P families {} = N24 CFull - CExPrec".format(k),
                  resR[("PFam", "S")][dtok][k] ==
                  int(m24["nTwentyFourCFull" + dtok + tok].replace("{,}", ""))
                  - int(m24["nTwentyFourCExPrec" + dtok + tok].replace("{,}", "")),
                  (k, resR[("PFam", "S")][dtok][k]))
    md("## 7. The same headline on two restrictions", "",
       "Families as n24 defines them (family_id of the suite). Reading S of the first "
       "restriction equals N24's subset 'without the families of every disputed group' and of "
       "the second equals N24's full set minus its subset without group P (asserted).", "")
    for dtok, delta in DELTAS.items():
        body = []
        for sk, (txt, _k) in subs.items():
            for rd in RDS:
                body.append([txt, rd] + hl_row(resR[(sk, rd)], dtok))
        md("### delta = {:.2f}".format(delta), "")
        md_table(["subset", "reading"] + HL_HEAD, body)

    # ---------------- per family ----------------
    rfams = sorted({fam[i] for i in reorder_ids})
    body = []
    for f in rfams:
        ids = [i for i in reorder_ids if fam[i] == f]
        row = [f, len(ids), "P" if f in S["fams"]["P"] else ("disputed" if f in S["fam_all"]
                                                              else "-")]
        for rd, rb in (("S", rbyS), ("F", rbyF)):
            sel = [rb[i] for i in ids if i in rb]
            c20 = [r for r in sel if n13.costly_of(r, 0.20) == 1]
            c10 = [r for r in sel if n13.costly_of(r, 0.10) == 1]
            row.append("{} / {} / {} / {}".format(
                len(c20), sum(1 for r in c20 if r["ref_k"]), sum(1 for r in c20 if r["ref_f"]),
                sum(1 for r in sel if n13.costly_of(r, 0.20) == 0 and r["ref_k"])))
            row.append("{} / {} / {}".format(len(c10), sum(1 for r in c10 if not r["ref_k"]),
                                              sum(1 for r in c10 if not r["ref_f"])))
        dsub = [valsF[i]["dmg"] - valsS[i]["dmg"] for i in ids if valsF[i]["dmg"] is not None]
        row.append(bh2(float(np.median(np.array(dsub)))) if dsub else "n/a")
        row.append(sum(1 for i in ids if rep[i]["boards"]["S"]["dt"]["digest"]
                       != rep[i]["boards"]["F"]["dt"]["digest"]))
        body.append(row)
    md("## 8. The reorder families", "",
       "Per family: costly at 0.20 / of which referred on K / with FI / low-cost referred on K; "
       "costly at 0.10 / applied on K / applied with FI; median damage change F - S (bh); "
       "proposals whose K schedule changes.", "")
    md_table(["family", "priced reorder proposals", "group", "S: 0.20 costly / ref K / ref FI "
              "/ low ref K", "S: 0.10 costly / app K / app FI", "F: 0.20 costly / ref K / ref FI "
              "/ low ref K", "F: 0.10 costly / app K / app FI", "median damage change (bh)",
              "K schedule changes"], body)

    # ---------------- the unpriced reorder proposals ----------------
    md("## 9. Reference proposals with a reorder that are not priced", "")
    up_rows = []
    extra_codes = Counter()
    for kind, ids in (("unpriced_issuable", unp_iss), ("unpriced_not_issuable", unp_not)):
        cnt = Counter()
        dep = 0
        n_dispatched = 0
        for i in ids:
            x, it = rep[i], items_by[i]
            kS, kF = x["boards"]["S"]["dt"], x["boards"]["F"]["dt"]
            fS, fF = x["boards"]["S"]["fi"], x["boards"]["F"]["fi"]
            check("unpriced S, K: terminal and stage equal items.jsonl",
                  (kS["term_cert"], kS["stage_cert"]) == (it["dt_term_cert"], it["dt_stage_cert"]),
                  (i, kS["term_cert"], kS["stage_cert"]))
            check("unpriced S, K: every code of items.jsonl is among the replay's codes",
                  set(it["dt_codes"] or []) <= set(kS["codes"] or []), (i, kS["codes"]))
            for c_ in sorted(set(kS["codes"] or []) - set(it["dt_codes"] or [])):
                extra_codes[(kind, c_)] += 1
            same = ((kS["term_cert"], kS["stage_cert"], kS["codes"], kS["digest"])
                    == (kF["term_cert"], kF["stage_cert"], kF["codes"], kF["digest"])
                    and (fS["term_cert"], fS["stage_cert"], fS["codes"], fS["digest"])
                    == (fF["term_cert"], fF["stage_cert"], fF["codes"], fF["digest"]))
            if not same:
                dep += 1
            if kS["digest"] is not None or kF["digest"] is not None:
                n_dispatched += 1
            cnt[(kS["stage_cert"], "|".join(kS["codes"]), fS["stage_cert"],
                 "|".join(fS["codes"]), same)] += 1
        up_rows.append((kind, ids, cnt, dep))
        add("Unpriced" + ("Issuable" if kind == "unpriced_issuable" else "NotIssuable")
            + "DispatchedK", grp(n_dispatched),
            "[U] of these, proposals that reach the dispatcher on K under either reading")
        add("Unpriced" + ("Issuable" if kind == "unpriced_issuable" else "NotIssuable"),
            grp(len(ids)), "[U] reference proposals with a reorder, not priced: {}".format(
                "issuable and refused" if kind == "unpriced_issuable" else "not issuable"))
        add("Unpriced" + ("Issuable" if kind == "unpriced_issuable" else "NotIssuable")
            + "ReadingDependent", grp(dep),
            "[U] of these, proposals whose outcome on K or FI differs between S and F")
    body = []
    for kind, ids, cnt, dep in up_rows:
        for (ks, kc, fs, fc_, same), v in sorted(cnt.items(), key=lambda kv: str(kv[0])):
            body.append([kind.replace("_", " "), v, ks, kc, fs, fc_, "yes" if same else "NO"])
    md_table(["population", "proposals", "K stage", "K codes", "FI stage", "FI codes",
              "same outcome under S and F"], body)
    md("K codes of the replay that items.jsonl does not carry (the terminal and the stage agree "
       "with items.jsonl on every proposal, and every logged code is among the replay's): " +
       ("; ".join("{} {}: {}".format(k.replace("_", " "), c_, v)
                  for (k, c_), v in sorted(extra_codes.items())) or "none") + ".", "")

    # ---------------- population macros ----------------
    add("Priced", grp(len(recs)), "[N] priced reference proposals of the direct benchmark "
                                  "(reading S)")
    add("PricedF", grp(len(recsF)), "[N] priced reference proposals under reading F")
    add("ReorderPriced", grp(len(reorder_ids)), "[N] priced reference proposals that carry at "
                                                "least one reorder")
    add("ReorderPricedShare", pct(len(reorder_ids), len(recs)), "[N] the same as a share of the "
                                                                "priced proposals")
    add("ReorderNotPricedF", grp(len(not_priced_F)), "[N] reorder proposals priced under S and "
                                                     "not priced on K under F")
    add("NoScheduleF", grp(len(deadlocks)), "[N] boards of reorder proposals without a schedule "
                                            "under F (deadlock or refusal at dispatch)")
    add("SampleNoReorder", grp(n_sample), "[N] priced proposals without a reorder replayed under "
                                          "both readings and asserted identical")
    add("ReorderSites", grp(len({(x["iid"], x["site"]) for x in rep.values()
                                  if x["kind"] == "reorder"})),
        "[N] decision-instant sites (instance x frozen set x t_d) of the reorder proposals")

    # ---------------- self-test ----------------
    sp2 = second_path(rep, set(reorder_ids), set(S["fams"]["P"]), set(S["fam_all"]),
                      [r["item_id"] for r in recs])
    hF = resH[("F", "Pooled")]

    def cmp(what, main_v, second_v):
        ok = str(main_v) == str(second_v)
        SELF.append((what, main_v, second_v, ok))
        check("self-test " + what, ok, (main_v, second_v))

    cmp("F pooled: costly at 0.20", hF["DeltaTwenty"]["costly"], sp2["costly20"])
    cmp("F pooled: costly at 0.10", hF["DeltaTen"]["costly"], sp2["costly10"])
    cmp("F pooled: costly referred on K at 0.20", hF["DeltaTwenty"]["ref_k"], sp2["ref_k20"])
    cmp("F pooled: costly referred with FI at 0.20", hF["DeltaTwenty"]["ref_f"], sp2["ref_f20"])
    cmp("F pooled: costly applied on K at 0.10", hF["DeltaTen"]["app_k"], sp2["app_k10"])
    cmp("F pooled: costly applied with FI at 0.10", hF["DeltaTen"]["app_f"], sp2["app_f10"])
    cmp("F pooled: costly applied on K with the second price at 0.10",
        hF["DeltaTen"]["two_app_k"], sp2["two_app_k10"])
    cmp("F pooled: low-cost referred on K at 0.20", hF["DeltaTwenty"]["low_ref_k"],
        sp2["low_ref_k20"])
    cmp("F pooled: low-cost referred on K with the second price at 0.20",
        hF["DeltaTwenty"]["low_two_k"], sp2["low_two_k20"])
    cmp("F pooled: low-cost referred with FI at 0.20", hF["DeltaTwenty"]["low_ref_f"],
        sp2["low_ref_f20"])
    cmp("F pooled: common denominator applied on K at 0.20", hF["DeltaTwenty"]["cd_k"],
        sp2["cd_k20"])
    cmp("F pooled: common denominator applied with FI at 0.20", hF["DeltaTwenty"]["cd_f"],
        sp2["cd_f20"])
    cmp("F pooled: common denominator applied on K at 0.10", hF["DeltaTen"]["cd_k"],
        sp2["cd_k10"])
    cmp("F pooled: low-cost referral share on K at 0.20 and 95% interval",
        "{} [{}, {}]".format(pctv(hF["DeltaTwenty"]["lr_share"]), pctv(hF["DeltaTwenty"]["lr_lo"]),
                             pctv(hF["DeltaTwenty"]["lr_hi"])), sp2["lr20"])
    cmp("F: discordant proposals (certificate, K against FI)", len(dis["F"]["all"]), sp2["dis"])
    cmp("F without every disputed family: costly at 0.20",
        resR[("ExAll", "F")]["DeltaTwenty"]["costly"], sp2["exall_costly20"])
    cmp("F without every disputed family: costly applied on K at 0.10",
        resR[("ExAll", "F")]["DeltaTen"]["app_k"], sp2["exall_app_k10"])
    cmp("F in the P families: costly at 0.20", resR[("PFam", "F")]["DeltaTwenty"]["costly"],
        sp2["pfam_costly20"])
    cmp("F in the P families: costly referred on K at 0.20",
        resR[("PFam", "F")]["DeltaTwenty"]["ref_k"], sp2["pfam_ref_k20"])
    cmp("damage change F - S: median (bh)", bh2(qd["median"]), sp2["dmg_median"])
    cmp("damage change F - S: proposals lower under F", n_lower, sp2["dmg_lower"])
    cmp("probe 1 under F: start of B = end of A = 3 + 4 bh (hand arithmetic)",
        bh1(resP["p1"][1]["F"][1]["B"]["start_bh"]), bh1(3.0 + 4.0))
    md("## Self-test (second code path)", "",
       "Each F number is recomputed from analysis/N11_rows_forecast.csv, "
       "results/n11_decision_time/items.jsonl, results/n11_forecast/fullinfo_direct.jsonl and "
       "anchors_direct.jsonl, analysis/ladder/rule_anchor.json, results/oracle_v1/brackets.jsonl "
       "and code/suite/v0.2/suite.jsonl read with the csv and json modules, and the raw F "
       "boards of the replay, with a label function, the prices and a bootstrap written in the "
       "script (no n13/n16/n20/n24 loader, label or tally).", "")
    md_table(["number", "main path", "second path", "equal"],
             [[w, m, s_, "yes" if ok else "NO"] for w, m, s_, ok in SELF])

    # ---------------- end checks, outputs ----------------
    adapter1 = adapter_hashes()
    frozen1 = frozen_hashes()
    check("every .py file under code/l1adapter/ unchanged", adapter1 == ADAPTER0,
          (ADAPTER0, adapter1))
    check("the frozen files unchanged", frozen1 == _FROZEN0)
    n_reused = n24.NCHECK[0] + n20.NCHECK[0] + n16.NCHECK[0] + n18.NCHECK[0] + len(n13.CHECKS)
    wall = time.time() - t_start
    msg = ("[n25] {} macros, {} assertions passed (+{} in the reused functions); self-test {} of "
           "{} equal; replay {:.0f}s, total {:.0f}s".format(
               len(NAMES), NCHECK[0], n_reused, sum(1 for x in SELF if x[3]), len(SELF), wall_rep,
               wall))
    md("## Runtime", "",
       "Replay {:.0f} s for {} proposals on {} instances (core 14, one process; deterministic "
       "replays, so no number depends on the wall time); total {:.0f} s.".format(
           wall_rep, len(rep), len(tasks), wall), "")
    if selftest_only:
        dev = os.environ.get("N25_DEV_SUMMARY")       # development aid: a scratch copy only
        if dev and not str(Path(dev).resolve()).startswith(str(ROOT)):
            Path(dev).write_text("\n".join(MD) + "\n", encoding="utf-8")
            Path(dev + ".tex").write_text("\n".join(LINES) + "\n", encoding="utf-8")
        print(msg + " (self-test mode: nothing written to the project)")
        return 0
    paths = OrderedDict(list(n13.IN.items()) + list(IN25.items()))
    h = OrderedDict(hashes)
    h.update((k, input_sha256(k, p)) for k, p in IN25.items())
    for nm in ("n25_finish_to_start.py", "n24_conventions.py", "n20_stratum_abs.py",
               "n11_decision_time.py", "n8_causal.py"):
        h["code " + nm] = sha256_file(SCRIPTS_DIR / nm)
        paths["code " + nm] = SCRIPTS_DIR / nm
    MD.extend(["## Inputs", ""] + ["- {} `{}` sha256 {}".format(
        k, Path(paths[k]).relative_to(ROOT), vv) for k, vv in h.items()] + [""])
    MD.append("{} assertions passed in n25 (plus {} in the reused functions); self-test {} of {} "
              "numbers equal on the second code path; {} macros.".format(
                  NCHECK[0], n_reused, sum(1 for x in SELF if x[3]), len(SELF), len(NAMES)))
    write_rows(recs, rbyS, rbyF, valsS, valsF, rep, unpriced, items_by, fam, S,
               set(sample_ids), fi_logged)
    with open(OUT_REPLAY, "w", encoding="utf-8") as fh:
        for i, x in rep.items():
            y = json.loads(json.dumps(x))
            for rd in y["boards"]:
                for bk in y["boards"][rd]:
                    if y["boards"][rd][bk] is not None:
                        y["boards"][rd][bk].pop("edge_detail", None)
            fh.write(json.dumps(y, sort_keys=True) + "\n")
    OUT_ADAPTER.write_text(json.dumps({"before": ADAPTER0, "after": adapter1,
                                       "frozen_before": _FROZEN0, "frozen_after": frozen1},
                                      indent=1) + "\n", encoding="utf-8")
    OUT_TEX.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    shutil.copyfile(OUT_TEX, OUT_MANU)
    OUT_MD.write_text("\n".join(MD) + "\n", encoding="utf-8")
    print(msg)
    return 0


def write_rows(recs, rbyS, rbyF, valsS, valsF, rep, unpriced, items_by, fam, S, sample,
               fi_logged):
    def f6(x):
        return "" if x is None else ("inf" if x == float("inf") else "{:.6f}".format(x))

    def b01(x):
        return "" if x is None else int(bool(x))

    def cst(r, d):
        if r is None:
            return ""
        c = n13.costly_of(r, d)
        return "" if c is None else c

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        fh.write("# N25 ({}): one row per priced proposal of the direct benchmark (1,356) and per "
                 "unpriced reference proposal with a reorder; _S = published reading "
                 "(start-after-start), _F = finish-to-start reading of every reorder edge; "
                 "proposals without a reorder keep their published values under F; k = known "
                 "board at t_d, fi = full-information board, real = realised whole-window run; "
                 "p_<design> = price on the logged bound; label: 1 costly, 0 low-cost, empty "
                 "undecided; sched_diff = canonical schedule differs between S and F; overlap_S "
                 "= edges whose successor starts before the predecessor ends under S\n".format(
                     VERSION))
        w = csv.writer(fh, lineterminator="\n")
        head = ["item_id", "population", "instance_id", "stratum", "family", "primary_class",
                "edit_type", "n_ops", "carries_reorder", "in_P_families",
                "in_disputed_families", "in_no_reorder_sample", "k_term_S", "k_term_F",
                "k_codes_S", "k_codes_F", "fi_term_S", "fi_term_F"]
        for side in ("k", "fi"):
            for g in DESIGNS:
                head += ["p_{}_{}_S".format(g, side), "p_{}_{}_F".format(g, side)]
        head += ["second_price_k_S", "second_price_k_F", "second_price_fi_S", "second_price_fi_F",
                 "real_wt_orig_S", "real_wt_orig_F", "damage_S", "damage_F", "m_lo_S", "m_lo_F",
                 "m_hi_S", "m_hi_F", "label020_S", "label020_F", "label010_S", "label010_F",
                 "ref_k_S", "ref_k_F", "ref_fi_S", "ref_fi_F", "two_k_S", "two_k_F", "two_fi_S",
                 "two_fi_F", "cd_bh_k_S", "cd_bh_k_F", "cd_bh_fi_S", "cd_bh_fi_F", "den",
                 "sched_diff_k", "sched_diff_fi", "sched_diff_real", "edges_k", "overlap_S_k",
                 "overlap_S_fi", "overlap_S_real", "freeze_wins_F_k", "freeze_wins_F_fi",
                 "freeze_wins_F_real"]
        w.writerow(head)
        for r in recs:
            i = r["item_id"]
            a, b = rbyS[i], rbyF.get(i)
            x = rep.get(i)
            reo = i in valsS
            pop = "priced_reorder" if reo else "priced_no_reorder"

            def term(rd, bk):
                if x is None or x["kind"] not in ("reorder", "sample"):
                    return (items_by[i]["dt_term_cert"] if bk == "dt"
                            else fi_logged[i]["p"]["term_cert"])
                return x["boards"][rd][bk]["term_cert"]

            def codes(rd):
                if x is None or x["kind"] not in ("reorder", "sample"):
                    return "|".join(items_by[i]["dt_codes"] or [])
                return "|".join(x["boards"][rd]["dt"]["codes"] or [])

            row = [i, pop, r["instance_id"], r["st"], fam[i], r["primary_class"], r["split"],
                   r["n_ops"], int(reo), int(fam[i] in S["fams"]["P"]),
                   int(fam[i] in S["fam_all"]), int(i in sample), term("S", "dt"),
                   term("F", "dt") if b is not None else "not priced", codes("S"), codes("F"),
                   term("S", "fi"), term("F", "fi")]
            for side in ("k", "fi"):
                for g in DESIGNS:
                    sa = a if side == "k" else a["fi"]
                    sb = None if b is None else (b if side == "k" else b["fi"])
                    row += [f6(sa["p_" + g]), "" if sb is None else f6(sb["p_" + g])]
            vS, vF = valsS.get(i), valsF.get(i)
            row += [f6(a["g_orig"]), "" if b is None else f6(b["g_orig"]), f6(a["sp_fi"]),
                    "" if b is None else f6(b["sp_fi"]),
                    f6(vS["rw_obj_orig"] if vS else items_by[i]["rw_obj_orig"]),
                    f6(vF["rw_obj_orig"] if vF else items_by[i]["rw_obj_orig"]),
                    f6(a["dmg"]), "" if b is None else f6(b["dmg"]), f6(a["lo"]),
                    "" if b is None else f6(b["lo"]), f6(a["hi"]), "" if b is None else f6(b["hi"]),
                    cst(a, 0.20), cst(b, 0.20), cst(a, 0.10), cst(b, 0.10), b01(a["ref_k"]),
                    "" if b is None else b01(b["ref_k"]), b01(a["ref_f"]),
                    "" if b is None else b01(b["ref_f"]), b01(a["two_k"]),
                    "" if b is None else b01(b["two_k"]), b01(a["two_f"]),
                    "" if b is None else b01(b["two_f"]), f6(a["c_bh_k"]),
                    "" if b is None else f6(b["c_bh_k"]), f6(a["c_bh_f"]),
                    "" if b is None else f6(b["c_bh_f"]), f6(a["den"])]
            if reo:
                bs, bf = x["boards"]["S"], x["boards"]["F"]
                row += [int(bs[k]["digest"] != bf[k]["digest"]) for k in ("dt", "fi", "rw")]
                row += [bs["dt"]["edges"]] + [bs[k]["overlap"] for k in ("dt", "fi", "rw")]
                row += [bf[k]["freeze_wins"] for k in ("dt", "fi", "rw")]
            else:
                row += [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            w.writerow(row)
        for i in unpriced:
            x, it = rep[i], items_by[i]
            kS, kF = x["boards"]["S"]["dt"], x["boards"]["F"]["dt"]
            fS, fF = x["boards"]["S"]["fi"], x["boards"]["F"]["fi"]
            row = [i, x["kind"], it["instance_id"], ST_TOK[it["stratum"]], fam[i],
                   it["primary_class"], it["split"], it["n_ops"], 1,
                   int(fam[i] in S["fams"]["P"]), int(fam[i] in S["fam_all"]), 0,
                   kS["term_cert"], kF["term_cert"], "|".join(kS["codes"] or []),
                   "|".join(kF["codes"] or []), fS["term_cert"], fF["term_cert"]]
            row += [""] * (len(head) - len(row))
            w.writerow(row)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
