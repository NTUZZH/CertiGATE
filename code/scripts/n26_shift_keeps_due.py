#!/usr/bin/env python3
"""N26: the direct benchmark when a time-window shift keeps the due date.

Design pre-specified before the run.  Frozen design:
results/n26_shift_keeps_due/design.md (sha256 asserted before anything else); later choices:
results/n26_shift_keeps_due/addendum.md.

The benchmark's `reassign_window` operation moves the release time by a signed number of
business hours and restarts the SLA clock, so the due date moves with it (convention B,
code/l1adapter/apply.py).  The price is computed on the edited values, so a shifted due date
hides the lateness a shift causes.  Convention D moves the release time only and keeps the due
date.  Everything else is unchanged: set_priority still resets weight and due date from the
release it sees, precedence stays start-after-start, the guard, ATC, seed 0, the frozen set
"fix", the bound and the floor are those of the benchmark.

Convention D is implemented without editing any file under code/l1adapter/:
`apply.apply_operations` is compiled again from its own source with one textual change (the
due-date line of the `reassign_window` branch runs only when a switch is off).  The attributes
`l1adapter.apply.apply_operations` and `l1adapter.apply_operations` point to the patched
function only while a D board (or a B board through the patched function, "Boff") is priced.

Steps (every assertion is run-fatal):
  0  frozen-file prefixes, the design's sha256, the sha256 of every .py file under
     code/l1adapter/ (again at the end);
  B  convention B from the stored records reproduces the frozen counts of the suite (n20.build's
     1,356 records) and of the three fresh draws (n17_heldout.build_records on the stored
     replays, the 3,733 held-out rows of analysis/N17_rows.csv);
  P  probes on micro-instances: (a) the patched function with the switch off equals the
     unpatched module byte for byte, (b) with the switch on a shift keeps the due date,
     (c) without a shift the switch changes nothing;
  R  replay of every reference proposal that carries a reassign_window (priced and unpriced),
     and of 50 sampled priced proposals without one, through n11_decision_time.gen_price on the
     known board (K), the full-information board (FI) and the realised whole-window run, under
     B (unpatched) and D, and under Boff on K for a sample; two worker processes;
  T  every B board tied to its stored values; every D board checked (complete schedule, the
     shifted orders' due dates kept);
  D  the D records and the reported tables: headline B beside D, the fate of the costly
     proposals applied under B, the correct translations that carry a shift, label and
     schedule changes, the damage change, the unpriced proposals, the self-test.

Reuse: n17_heldout (imported; cores 8-11 allowed) for the held-out records; n20_stratum_abs
loaded from its source with its core allowance set to cores 8 and 9 in memory (file
untouched), and through it n16, n18 and n13: n20.build's records, n20.tally, n13.costly_of,
n13.score, n16.sp_flag, n2.Boot (seed 20261026, 20,000 replicates, 60 instance clusters).

Outputs: analysis/N26_macros.tex (prefix \\nTwentySix, one comment line per macro), copied to
manuscript/macros_n26.tex; analysis/N26_rows.csv; analysis/N26_numbers.json;
analysis/N26_summary.md; results/n26_shift_keeps_due/replay.jsonl and l1adapter_sha256.json.
Run:       OMP_NUM_THREADS=1 taskset -c 8,9 python -B code/scripts/n26_shift_keeps_due.py
Self-test: the same with --selftest: every computation and assertion, writes nothing.
Version: l1-n26-shift-1
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
import traceback  # noqa: E402
import types  # noqa: E402
from collections import Counter, OrderedDict, defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

ALLOWED_CORES = {8, 9}
_aff = set(os.sched_getaffinity(0))
if not _aff <= ALLOWED_CORES and not os.environ.get("CERTIGATE_ANY_CORES"):
    raise SystemExit("REFUSING TO RUN: affinity {} is not inside cores 8 and 9 "
                     "(run under taskset -c 8,9)".format(sorted(_aff)))

SCRIPTS_DIR = Path(__file__).resolve().parent
CODE_DIR = SCRIPTS_DIR.parent
ROOT = CODE_DIR.parent
for _p in (str(CODE_DIR), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

VERSION = "l1-n26-shift-1"
OUT_DIR = ROOT / "results" / "n26_shift_keeps_due"
DESIGN = OUT_DIR / "design.md"
DESIGN_SHA_FILE = OUT_DIR / "design.sha256"
ADDENDUM = OUT_DIR / "addendum.md"
DESIGN_SHA = "db8a8e6b36c76888563be05350e35c3b18f0cb73969ce9c52aa3eedec4c58bf9"
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
        raise SystemExit("[n26] frozen file {} has sha256 {} (expected prefix {})".format(
            _k, _FROZEN0[_k], _pre))
_dsha = sha256_file(DESIGN)
if _dsha != DESIGN_SHA or DESIGN_SHA_FILE.read_text().split()[0] != DESIGN_SHA:
    raise SystemExit("[n26] design.md sha256 {} differs from the recorded {}".format(
        _dsha, DESIGN_SHA))
if not ADDENDUM.is_file():
    raise SystemExit("[n26] missing addendum " + str(ADDENDUM))
ADAPTER0 = adapter_hashes()

import n17_heldout as n17  # noqa: E402  (allows cores 8-11; asserts the frozen digests)


def _load_module(name, swaps):
    """A script loaded from its source with its core allowance replaced in memory."""
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


# n20 holds its own allowance and the two strings it writes into n16's and n18's sources; all
# three move to {8, 9}; n16 in turn writes {8, 9} into n13's source.
n20 = _load_module("n20_stratum_abs", [("ALLOWED_CORES = {10, 11}", "ALLOWED_CORES = {8, 9}", 3)])
n16, n18, n13 = n20.n16, n20.n18, n20.n13
if not (n20.ALLOWED_CORES == n16.ALLOWED_CORES == n18.ALLOWED_CORES == n13.ALLOWED_CORES
        == ALLOWED_CORES):
    raise SystemExit("core allowance not propagated to n20/n16/n18/n13")
D = n13.D
if D is not n17.D:
    raise SystemExit("n11_decision_time loaded twice")
FC = n17.F
np = n13.np
n2 = n13.n2
import n8_causal as n8  # noqa: E402
import l1adapter  # noqa: E402
from l1adapter import SLA_BH  # noqa: E402
from l1adapter import apply as apply_mod  # noqa: E402
from l1adapter import dispatch as dispatch_mod  # noqa: E402
from l1adapter import ops as l1ops  # noqa: E402
from l1guard.config import G_CERT  # noqa: E402
from l1guard.verdict import certified_gap  # noqa: E402

ANALYSIS = ROOT / "analysis"
OUT_TEX = ANALYSIS / "N26_macros.tex"
OUT_MANU = ROOT / "manuscript" / "macros_n26.tex"
OUT_MD = ANALYSIS / "N26_summary.md"
OUT_CSV = ANALYSIS / "N26_rows.csv"
OUT_JSON = ANALYSIS / "N26_numbers.json"
OUT_REPLAY = OUT_DIR / "replay.jsonl"
OUT_ADAPTER = OUT_DIR / "l1adapter_sha256.json"
SEEDS = ("20261110", "20261111", "20261112")
SEED_TOK = OrderedDict([("20261110", "SeedA"), ("20261111", "SeedB"), ("20261112", "SeedC")])
IN26 = OrderedDict([
    ("brief", ROOT / "design_notes" / "N26_design.md"),
    ("design", DESIGN), ("addendum", ADDENDUM),
    ("n17_rows", ANALYSIS / "N17_rows.csv"), ("n17_macros", ANALYSIS / "N17_macros.tex"),
    ("n15_macros", ANALYSIS / "N15_macros.tex"), ("n16_macros", ANALYSIS / "N16_macros.tex"),
    ("apply_py", ADAPTER_DIR / "apply.py"), ("dispatch_py", ADAPTER_DIR / "dispatch.py"),
] + [("heldout_suite_" + s, CODE_DIR / "suite" / ("v1.1_heldout_" + s) / "suite.jsonl")
     for s in SEEDS] + [
    ("heldout_" + nm + "_" + s, ROOT / "results" / "n17_heldout" / "replay" / s / nm)
    for s in SEEDS for nm in ("items.jsonl", "fullinfo.jsonl", "fi_anchors.jsonl")])

TAU = n13.TAU
FLOOR = D.FLOOR_BH
EPS = 1e-9
TOL = 1e-9                                 # full-precision fields
CSV_TOL = 1e-6                             # fields read from a six-decimal file
SAMPLE_SEED = 20261111
SAMPLE_N = 50
BOFF_N = 50
WORKERS = 2
DELTAS = OrderedDict([("DeltaTwenty", 0.20), ("DeltaTen", 0.10)])
DESIGNS = n13.DESIGNS                      # G-CERT, G-CERT-M, D-REL1, D-REL2, D-ABS
SETTINGS = n13.SETTINGS
UNION = n13.UNION
CERT = "G-CERT"
CONVS = ("B", "D")
SCOPES = OrderedDict([("Suite", "the suite (1,356 priced proposals)"),
                      ("New", "the three new draws pooled (3,733 priced held-out proposals)")])
FAMS = OrderedDict([("Shift", "v4_sign_flipped_shift"), ("Prio", "v4_objective_shifting")])
CORRECT_CLS = OrderedDict([("Benign", "benign"), ("VThree", "V3")])
HL = OrderedDict([
    ("costly", ("Costly", "costly proposals")),
    ("low", ("Low", "low-cost proposals")),
    ("und", ("Und", "undecided proposals")),
    ("ref_k", ("CostlyRefK", "costly proposals the certificate refers on the known board")),
    ("ref_f", ("CostlyRefFI", "costly proposals the certificate refers with full information")),
    ("ref_both", ("CostlyRefBoth", "costly proposals referred on the known board and with full "
                                   "information")),
    ("app_k", ("AppK", "costly proposals the certificate applies on the known board")),
    ("app_f", ("AppFI", "costly proposals the certificate applies with full information")),
    ("two_app_k", ("TwoAppK", "costly proposals applied on the known board with the second "
                              "price on field edits")),
    ("two_app_f", ("TwoAppFI", "costly proposals applied with full information with the second "
                               "price on field edits")),
    ("low_ref_k", ("LowRefK", "low-cost proposals the certificate refers on the known board")),
    ("low_two_k", ("LowTwoRefK", "low-cost proposals referred on the known board with the "
                                 "second price")),
    ("low_ref_f", ("LowRefFI", "low-cost proposals the certificate refers with full "
                               "information")),
    ("low_two_f", ("LowTwoRefFI", "low-cost proposals referred with full information with the "
                                  "second price")),
])

#: Inputs the public release does not carry (the analysis's design note). A missing one
#: is recorded as "not shipped" in the provenance block, and the run goes on.
NOT_SHIPPED_OK = ('brief',)


def input_sha256(key, path):
    """The SHA-256 of an input, or "not shipped" for one the public release does not carry."""
    if key in NOT_SHIPPED_OK and not Path(path).is_file():
        return "not shipped"
    return sha256_file(path)
FROZEN_COUNTS = {
    ("Suite", 0.20): dict(priced=1356, costly=186, low=1170, ref_k=168, ref_f=168, ref_both=168,
                          app_k=18, two_app_k=0, low_ref_k=15, low_two_k=22),
    ("Suite", 0.10): dict(costly=208, app_k=25, app_f=28, two_app_k=6),
    ("New", 0.20): dict(priced=3733, costly=529, low=3204, app_k=45, two_app_k=4, low_ref_k=65,
                        low_two_k=98),
}

LINES = ["% N26 macros ({}); generated by code/scripts/n26_shift_keeps_due.py from deterministic "
         "replays of the direct benchmark under two conventions of the time-window shift: B "
         "(benchmark, the due date moves with the release) and D (the due date is kept). "
         "Post hoc sensitivity analysis; design: results/n26_shift_keeps_due/design.md.".format(
             VERSION)]
NAMES = set()
VAL = OrderedDict()
MD = []
NCHECK = [0]
SELF = []
MAXDIFF = defaultdict(float)
NUM = OrderedDict()                        # structured numbers for N26_numbers.json

grp, pctv, pctpv = n16.grp, n16.pctv, n16.pctpv


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def check(what, ok, detail=""):
    if not ok:
        raise SystemExit("[n26] ASSERTION FAILED: {} ({})".format(what, str(detail)[:900]))
    NCHECK[0] += 1


def close(what, a, b, tol, key=""):
    if a is None or b is None:
        check(what + " (both missing)", a is None and b is None, (key, a, b))
        return
    d = abs(float(a) - float(b))
    MAXDIFF[what] = max(MAXDIFF[what], d)
    check(what, d <= tol, (key, a, b, d))


def add(name, value, note):
    full = "nTwentySix" + name
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
    print("[n26] " + msg, flush=True)


def lbl(c):
    return {1: "costly", 0: "low-cost", None: "undecided"}[c]


def optypes(ops):
    return {o.get("op") for o in (ops or []) if isinstance(o, dict)}


def fx(x):
    """A float written so that it reads back exactly (empty for a missing value)."""
    if x is None:
        return ""
    if x == float("inf"):
        return "inf"
    return repr(float(x))


def b01(x):
    return "" if x is None else int(bool(x))


# --------------------------------------------------------------------------- #
# Convention D: the patched apply_operations (in memory)                       #
# --------------------------------------------------------------------------- #
ORIG_APPLY = apply_mod.apply_operations
if l1adapter.apply_operations is not ORIG_APPLY:
    raise SystemExit("l1adapter.apply_operations is not l1adapter.apply.apply_operations")
SWAP_OLD = ('            wo["release_bh"] = release\n'
            '            wo["due_bh"] = _round_bh(release + SLA_BH[int(wo["priority"])])\n')
SWAP_NEW = ('            wo["release_bh"] = release\n'
            '            if not _N26_KEEP_DUE[0]:\n'
            '                wo["due_bh"] = _round_bh(release + SLA_BH[int(wo["priority"])])\n')


def make_patched_apply():
    src = inspect.getsource(ORIG_APPLY)
    disk = Path(apply_mod.__file__).read_text(encoding="utf-8")
    check("the source of apply_operations is one slice of apply.py on disk", disk.count(src) == 1)
    check("the due-date line of reassign_window occurs once in apply_operations",
          src.count(SWAP_OLD) == 1, src.count(SWAP_OLD))
    check("the set_priority due-date line is a different line",
          src.count('wo["due_bh"] = _round_bh(float(wo["release_bh"]) + SLA_BH[cls])') == 1)
    src = src.replace(SWAP_OLD, SWAP_NEW)
    g = dict(vars(apply_mod))
    flag = [False]
    g["_N26_KEEP_DUE"] = flag
    code = compile(src, "<n26: apply_operations with the due-date switch>", "exec",
                   flags=__future__.annotations.compiler_flag, dont_inherit=True)
    exec(code, g)  # noqa: S102
    return g["apply_operations"], flag


PATCHED_APPLY, KEEP_DUE = make_patched_apply()


class Conv:
    """B: the unpatched module; Boff: the patched function, switch off; D: switch on."""

    def __init__(self, cv):
        if cv not in ("B", "Boff", "D"):
            raise ValueError(cv)
        self.cv = cv

    def __enter__(self):
        fn = ORIG_APPLY if self.cv == "B" else PATCHED_APPLY
        apply_mod.apply_operations = fn
        l1adapter.apply_operations = fn
        KEEP_DUE[0] = self.cv == "D"
        return self

    def __exit__(self, *exc):
        apply_mod.apply_operations = ORIG_APPLY
        l1adapter.apply_operations = ORIG_APPLY
        KEEP_DUE[0] = False
        return False


def sched_json(s):
    return dispatch_mod.canonical_schedule_json(s)


def sched_digest(s):
    return hashlib.sha256(sched_json(s).encode("utf-8")).hexdigest()


def expected_fields(ops, oid, rel0, due0, prio0, cv):
    """Release and due date of one order after the operations, restated from apply.py."""
    rel, due, prio = float(rel0), float(due0), int(prio0)
    for o in ops:
        if not isinstance(o, dict) or o.get("order_id") != oid:
            continue
        if o.get("op") == "set_priority":
            prio = int(o["priority_class"])
            due = round(rel + SLA_BH[prio], 4)
        elif o.get("op") == "reassign_window":
            rel = round(max(0.0, rel + float(o["release_shift_bh"])), 4)
            if cv != "D":
                due = round(rel + SLA_BH[prio], 4)
    return rel, due


# --------------------------------------------------------------------------- #
# P. Probes on micro-instances                                                 #
# --------------------------------------------------------------------------- #
def _order(oid, trade, p_bh, release_bh=0.0, priority=3, due_bh=None):
    rel = float(release_bh)
    due = round(rel + SLA_BH[int(priority)], 4) if due_bh is None else float(due_bh)
    return {"id": oid, "trade": trade, "p_bh": float(p_bh), "release_bh": rel, "due_bh": due,
            "priority": int(priority), "weight": float(l1adapter.WEIGHT[int(priority)]),
            "building": None, "is_pm": False}


def _instance(orders, technicians):
    trades = sorted({tr for _, tr in technicians} | {o["trade"] for o in orders})
    return {"meta": {"id": "n26-probe", "campus": 0, "track": "micro",
                     "size_class": len(orders), "window_start": "synthetic", "window_bh": 0.0,
                     "provenance": "T", "seed": None},
            "trades": trades, "technicians": [{"id": t, "trade": tr} for t, tr in technicians],
            "work_orders": list(orders)}


def probe_run(inst, oplist, cv):
    with Conv(cv):
        parsed = l1ops.parse_operations({"operations": oplist}) if oplist else []
        adj = apply_mod.apply_operations(inst, parsed)
        sch = dispatch_mod.dispatch_adjusted(adj, "atc", 0)
    fields = json.dumps(adj.instance["work_orders"], sort_keys=True)
    return (fields, sched_json(sch), {w["id"]: w for w in adj.instance["work_orders"]},
            {a["wo"]: a for a in sch["assignments"]})


def block_p():
    o_ = _order
    # one technician; A (3 bh, class 3, due 80) and B (2 bh, class 2, due 24)
    i1 = _instance([o_("A", "D20", 3.0), o_("B", "D20", 2.0, priority=2)], [("T0", "D20")])
    # A released at 2 (due 82): a shift of -5 bh clips the release at 0
    i2 = _instance([o_("A", "D20", 3.0, release_bh=2.0), o_("B", "D20", 2.0, priority=2)],
                   [("T0", "D20")])
    # two orders of one (building, trade) group, EDD order inside the group
    bo = [o_("U", "D20", 2.0, due_bh=10.0), o_("V", "D20", 1.0, due_bh=5.0),
          o_("Z", "D20", 2.0, due_bh=2.0)]
    for x in bo[:2]:
        x["building"] = "B1"
    i3 = _instance(bo, [("T0", "D20"), ("T1", "D20")])
    sh = {"op": "reassign_window", "order_id": "A", "release_shift_bh": 10.0}
    sp = {"op": "set_priority", "order_id": "A", "priority_class": 1}
    probes = OrderedDict([
        ("shift", ("shift of A by +10 bh", i1, [sh])),
        ("clip", ("shift of A by -5 bh (release clipped at 0)", i2,
                  [{"op": "reassign_window", "order_id": "A", "release_shift_bh": -5.0}])),
        ("prio_then_shift", ("set_priority A to class 1, then shift A by +10 bh", i1, [sp, sh])),
        ("shift_then_prio", ("shift A by +10 bh, then set_priority A to class 1", i1, [sh, sp])),
        ("none", ("no operation", i1, [])),
        ("prio", ("set_priority A to class 1 (no shift)", i1, [sp])),
        ("pin", ("pin_next B (no shift)", i1, [{"op": "pin_next", "order_id": "B",
                                                "trade": "D20"}])),
        ("batch", ("batch of building B1, trade D20 (no shift)", i3,
                   [{"op": "batch", "building_id": "B1", "trade": "D20"}])),
    ])
    res = OrderedDict()
    for key, (txt, inst, ops) in probes.items():
        out = {cv: probe_run(inst, ops, cv) for cv in ("B", "Boff", "D")}
        check("(a) {}: the patched function with the switch off equals the unpatched module "
              "byte for byte".format(txt), out["B"][:2] == out["Boff"][:2])
        shifts = [o for o in ops if o["op"] == "reassign_window"]
        if not shifts:
            check("(c) {}: without a shift the switch changes nothing".format(txt),
                  out["D"][:2] == out["B"][:2])
        for o in shifts:
            w0 = {w["id"]: w for w in inst["work_orders"]}[o["order_id"]]
            for cv in ("B", "D"):
                rel, due = expected_fields(ops, o["order_id"], w0["release_bh"], w0["due_bh"],
                                           w0["priority"], cv)
                w = out[cv][2][o["order_id"]]
                check("(b) {} under {}: release and due as stated".format(txt, cv),
                      abs(w["release_bh"] - rel) < EPS and abs(w["due_bh"] - due) < EPS,
                      (w, rel, due))
        res[key] = (txt, inst, ops, out)
    a_b, a_d = res["shift"][3]["B"][2]["A"], res["shift"][3]["D"][2]["A"]
    check("(b) shift: B moves the due date to 90, D keeps 80", (a_b["due_bh"], a_d["due_bh"])
          == (90.0, 80.0) and a_b["release_bh"] == a_d["release_bh"] == 10.0, (a_b, a_d))
    c_b, c_d = res["clip"][3]["B"][2]["A"], res["clip"][3]["D"][2]["A"]
    check("(b) clip: release 0 under both; due 80 under B, 82 under D",
          (c_b["release_bh"], c_b["due_bh"], c_d["release_bh"], c_d["due_bh"])
          == (0.0, 80.0, 0.0, 82.0), (c_b, c_d))
    p_b, p_d = res["prio_then_shift"][3]["B"][2]["A"], res["prio_then_shift"][3]["D"][2]["A"]
    check("(b) set_priority then shift: due 18 under B, 8 under D",
          (p_b["due_bh"], p_d["due_bh"]) == (18.0, 8.0), (p_b, p_d))
    q_b, q_d = res["shift_then_prio"][3]["B"][2]["A"], res["shift_then_prio"][3]["D"][2]["A"]
    check("(b) shift then set_priority: due 18 under both (set_priority restarts the clock)",
          (q_b["due_bh"], q_d["due_bh"]) == (18.0, 18.0), (q_b, q_d))
    add("ProbeDueB", bh1(a_b["due_bh"]),
        "[P] probe: order A (3 bh, class 3, release 0, due 80) shifted by +10 bh, convention B: "
        "due date after the shift, bh")
    add("ProbeDueD", bh1(a_d["due_bh"]), "[P] the same probe, convention D: due date, bh")
    add("ProbeRelease", bh1(a_d["release_bh"]),
        "[P] the same probe: release after the shift under both conventions, bh")
    md("## P. Probes (in memory, before any replay)", "",
       "Micro-instances dispatched with ATC, seed 0 (apply_operations, then dispatch_adjusted). "
       "B = the unpatched module; Boff = the patched function with the switch off; D = the "
       "switch on. (a) Boff equals B byte for byte (adjusted fields and schedule) on every "
       "probe; (b) the shifted order's release and due date equal the stated rule; (c) without "
       "a shift D equals B byte for byte.", "")
    body = []
    for key, (txt, inst, ops, out) in res.items():
        oid = ops[0]["order_id"] if ops and "order_id" in ops[0] else None
        cell = {}
        for cv in ("B", "D"):
            if oid is not None:
                w = out[cv][2][oid]
                cell[cv] = "{} release {} due {}; schedule {}".format(
                    oid, bh1(w["release_bh"]), bh1(w["due_bh"]), "; ".join(
                        "{} {}-{}".format(k, bh1(v["start_bh"]), bh1(v["end_bh"]))
                        for k, v in sorted(out[cv][3].items())))
            else:
                cell[cv] = "; ".join("{} {}-{}".format(k, bh1(v["start_bh"]), bh1(v["end_bh"]))
                                     for k, v in sorted(out[cv][3].items()))
        body.append([txt, cell["B"], cell["D"], "yes",
                     "yes" if out["D"][:2] == out["B"][:2] else "no (shift)"])
    md_table(["probe", "convention B", "convention D", "Boff = B byte for byte",
              "D = B byte for byte"], body)
    return res


# --------------------------------------------------------------------------- #
# R. The replay (worker processes)                                             #
# --------------------------------------------------------------------------- #
def summ(res, ops, t_d):
    """The board's outcome and, when a schedule exists, its digest and the shifted orders."""
    if res is None:
        return None
    out = OrderedDict((k, res.get(k)) for k in (
        "term_cert", "stage_cert", "term_feas", "stage_feas", "codes", "infra", "obj",
        "obj_orig", "lb", "gap", "ref2", "ref2_from"))
    out.update(digest=None, complete=None, n_orders=None, shifted=[])
    live = res.get("_live") or {}
    if "schedule" in live:
        adj, sch = live["adjusted"], live["schedule"]
        ids = [a["wo"] for a in sch["assignments"]]
        wids = {w["id"] for w in adj.instance["work_orders"]}
        out["digest"] = sched_digest(sch)
        out["n_orders"] = len(wids)
        out["complete"] = len(ids) == len(set(ids)) == len(wids) and set(ids) == wids
        wa = {w["id"]: w for w in adj.instance["work_orders"]}
        wo = {w["id"]: w for w in adj.original["work_orders"]}
        seen = []
        for o in ops:
            oid = o.get("order_id") if isinstance(o, dict) else None
            if o.get("op") == "reassign_window" and oid in wa and oid not in seen:
                seen.append(oid)
                rel_e, due_e = {}, {}
                for cv in ("B", "D"):
                    rel_e[cv], due_e[cv] = expected_fields(ops, oid, wo[oid]["release_bh"],
                                                           wo[oid]["due_bh"],
                                                           wo[oid]["priority"], cv)
                out["shifted"].append(dict(
                    oid=oid, rel0=wo[oid]["release_bh"], due0=wo[oid]["due_bh"],
                    rel=wa[oid]["release_bh"], due=wa[oid]["due_bh"],
                    frozen=oid in adj.frozen, rel_b=rel_e["B"], due_b=due_e["B"],
                    rel_d=rel_e["D"], due_d=due_e["D"], t_d=t_d))
    return out


def build_tasks(kinds, items_of, stored_of, anchors, boff_ids):
    """kinds: [((set, item_id), kind)]; tasks grouped by (set, instance)."""
    by_inst = OrderedDict()
    for key, kind in sorted(kinds):
        st, item_id = key
        it = items_of[st][item_id]
        iid = it["instance"]["instance_id"]
        stored = stored_of[st][item_id]
        check("suite instance equals the stored census", iid == stored["instance_id"], key)
        t = by_inst.setdefault((st, iid), {"set": st, "iid": iid, "path": D.instance_path(it),
                                           "items": [], "seeds": OrderedDict(),
                                           "digest": OrderedDict()})
        seed = list(it["episode"]["frozen_seed"] or [])
        fk = D.frozen_key(seed)
        check("frozen key equals the stored census", fk == stored["frozen_seed"], key)
        t["seeds"].setdefault(fk, seed)
        t["digest"].setdefault(fk, anchors[(iid, fk)]["schedule_digest"])
        ops = D.canonical_ops(it)
        check("canonical operation count equals the census", len(ops) == stored["n_ops"], key)
        t["items"].append({"key": [st, item_id], "item_id": item_id, "kind": kind, "fk": fk,
                           "seed": seed, "ops": ops, "referenced": it["referenced"],
                           "boff": key in boff_ids})
    return list(by_inst.values())


def replay_task(task):
    t0 = time.perf_counter()
    inst = D.load_instance(task["path"])
    iid = inst["meta"]["id"]
    with Conv("B"):
        baseline = dispatch_mod.dispatch_baseline(inst, "atc", 0)
        trajs = {fk: n8.trajectory(inst, seed, baseline) for fk, seed in task["seeds"].items()}
    out = {"set": task["set"], "iid": iid, "items": [],
           "traj_digest": {fk: sched_digest(tr) for fk, tr in trajs.items()}}
    by_id = {wo["id"]: wo for wo in inst["work_orders"]}
    sites = {}

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
             "run_ids": run_ids, "fi_board": fi_board}
        sites[key] = s
        return s

    for it in task["items"]:
        fk, seed, kind, ops = it["fk"], it["seed"], it["kind"], it["ops"]
        starts = {a["wo"]: float(a["start_bh"]) for a in trajs[fk]["assignments"]}
        iss = D.issuability(it, by_id, starts)
        t_d = D.decision_instant_of(iss, "primary")
        s = site_for(fk, seed, t_d)
        raw = json.dumps({"operations": ops})
        rec = {"key": it["key"], "item_id": it["item_id"], "set": task["set"], "iid": iid,
               "fk": fk, "t_d": t_d, "issuable": iss["issuable"], "kind": kind,
               "boards": OrderedDict()}
        convs = ("B", "D") + (("Boff",) if it["boff"] else ())
        for cv in convs:
            b = OrderedDict()
            with Conv(cv):
                b["dt"] = summ(D.gen_price(s["known"], raw, s["kf"], s["base_p"], t_d, ref2=True,
                                           keep_live=True, running_ids=s["run_ids"]), ops, t_d)
                if cv != "Boff":
                    b["fi"] = summ(D.gen_price(s["fi_board"], raw, s["kf"], s["base_p"], t_d,
                                               ref2=True, keep_batch=s["k_ids"],
                                               running_ids=s["run_ids"], keep_live=True), ops,
                                   t_d)
                    b["rw"] = (None if kind.startswith("unpriced") else
                               summ(D.gen_price(inst, raw, s["frozen_r"], s["base_p"], t_d,
                                                keep_batch=s["k_ids"], keep_live=True), ops,
                                    t_d))
            rec["boards"][cv] = b
        out["items"].append(rec)
    out["wall_s"] = time.perf_counter() - t0
    out["pid"] = os.getpid()
    return out


TASKS = []


def _work(ti):
    try:
        return ti, replay_task(TASKS[ti]), None
    except BaseException:  # noqa: BLE001 - reported to the parent, which stops the run
        return ti, None, traceback.format_exc()


def run_replay(tasks):
    import multiprocessing as mp

    TASKS[:] = tasks

    def weight(i):
        iid = tasks[i]["iid"]
        return (0 if "c10_storm" in iid else 1 if "c09_storm" in iid else 2,
                -len(tasks[i]["items"]), tasks[i]["set"], iid)

    order = sorted(range(len(tasks)), key=weight)
    res = [None] * len(tasks)
    t0 = time.time()
    ctx = mp.get_context("fork")
    with ctx.Pool(WORKERS, maxtasksperchild=6) as pool:
        for j, (ti, r, err) in enumerate(pool.imap_unordered(_work, order)):
            if err is not None:
                pool.terminate()
                raise SystemExit("[n26] replay of {} {} failed:\n{}".format(
                    tasks[ti]["set"], tasks[ti]["iid"], err))
            res[ti] = r
            say("replayed {} {} ({} proposals, {:.0f}s), {} of {} ({:.0f}s)".format(
                r["set"], r["iid"], len(r["items"]), r["wall_s"], j + 1, len(order),
                time.time() - t0))
    return res


# --------------------------------------------------------------------------- #
# Values of one proposal under one convention                                  #
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


def values_of(b, it, fa_a, base, anchor):
    """Every price, flag input and label of a proposal from its three boards."""
    dt, fi, rw = b["dt"], b["fi"], b["rw"]
    v = OrderedDict(priced_k=dt["stage_cert"] == "qual", priced_fi=fi["stage_cert"] == "qual",
                    real_ok=rw is not None and rw["obj_orig"] is not None and bool(rw["complete"]))
    v["pk"] = OrderedDict((g, None) for g in DESIGNS)
    v["pf"] = OrderedDict((g, None) for g in DESIGNS)
    v["g_orig"] = v["sp_fi"] = v["c_bh_k"] = v["c_bh_f"] = v["gap_k"] = v["gap_f"] = None
    if v["priced_k"]:
        gap = certified_gap(dt["obj"], dt["lb"], G_CERT.lb_floor_bh)
        v["gap_k"] = gap
        v["pk"].update([("G-CERT", gap), ("G-CERT-M", gap - it["an_gap"]),
                        ("D-REL1", D.rel_delta(dt["obj"], it["an_obj"])),
                        ("D-REL2", None if dt["ref2"] is None else D.rel_delta(dt["obj"],
                                                                                dt["ref2"])),
                        ("D-ABS", round(dt["obj"] - it["an_obj"], D.ROUND_BH))])
        v["g_orig"] = (dt["obj_orig"] - it["an_lb"]) / max(it["an_lb"], FLOOR)
        v["c_bh_k"] = n13.gap_bh(dt["obj"], dt["lb"])
    if v["priced_fi"]:
        gapf = certified_gap(fi["obj"], fi["lb"], G_CERT.lb_floor_bh)
        v["gap_f"] = gapf
        v["pf"].update([("G-CERT", gapf), ("G-CERT-M", gapf - fa_a["gap"]),
                        ("D-REL1", D.rel_delta(fi["obj"], fa_a["obj"])),
                        ("D-REL2", None if fi["ref2"] is None else D.rel_delta(fi["obj"],
                                                                                fi["ref2"])),
                        ("D-ABS", round(fi["obj"] - fa_a["obj"], D.ROUND_BH))])
        v["sp_fi"] = (fi["obj_orig"] - fa_a["lb"]) / max(fa_a["lb"], FLOOR)
        v["c_bh_f"] = n13.gap_bh(fi["obj"], fi["lb"])
    v["rw_obj_orig"] = rw["obj_orig"] if v["real_ok"] else None
    v["dmg"] = None if v["rw_obj_orig"] is None else v["rw_obj_orig"] - anchor
    v["lo"], v["hi"] = label_interval(v["rw_obj_orig"], base, anchor)
    return v


def record_of(r, v):
    """The stored record r with every convention-dependent field taken from v."""
    x = dict(r)
    x["fi"] = dict(r["fi"])
    x["lo"], x["hi"], x["dmg"] = v["lo"], v["hi"], v["dmg"]
    for g in DESIGNS:
        x["p_" + g] = v["pk"][g]
        x["ref_" + g] = v["pk"][g] is not None and v["pk"][g] > SETTINGS[g]
        if v["priced_fi"]:
            x["fi"]["p_" + g] = v["pf"][g]
            x["fi"]["ref_" + g] = v["pf"][g] is not None and v["pf"][g] > SETTINGS[g]
        else:
            x["fi"]["p_" + g] = None
            x["fi"]["ref_" + g] = True
    x["ref_" + UNION] = x["ref_G-CERT-M"] or x["ref_D-REL2"]
    x["fi"]["ref_" + UNION] = x["fi"]["ref_G-CERT-M"] or x["fi"]["ref_D-REL2"]
    x["g_orig"] = v["g_orig"]
    x["sp"] = v["g_orig"] > TAU
    x["ref_k"] = n13.refers(x, CERT)
    x["ref_f"] = n13.refers(x["fi"], CERT)
    x["two_k"] = n16.sp_flag(x, CERT)
    if v["priced_fi"]:
        x["sp_fi"] = v["sp_fi"]
        x["two_f"] = x["ref_f"] or (x["field"] and v["sp_fi"] > TAU)
        x["c_bh_f"] = v["c_bh_f"]
    else:
        x["sp_fi"], x["two_f"], x["c_bh_f"] = None, True, float("inf")
    x["c_bh_k"] = v["c_bh_k"]
    return x


# --------------------------------------------------------------------------- #
# T. The run-fatal tie of every B board, and the D board checks                 #
# --------------------------------------------------------------------------- #
def check_shifted(b, cv, key, bk):
    """On a board with a schedule, each shifted order's release and due date as stated."""
    for s in b["shifted"]:
        rel_e = s["rel_d"] if cv == "D" else s["rel_b"]
        due_e = s["due_d"] if cv == "D" else s["due_b"]
        check("{}, {}: the shifted order's due date follows the convention".format(cv, bk),
              abs(float(s["due"]) - due_e) < EPS, (key, s))
        raised = (not s["frozen"]) and rel_e < float(s["t_d"])
        rel_w = float(s["t_d"]) if raised else rel_e
        check("{}, {}: the shifted order's release is the shifted release (raised to t_d when "
              "earlier, as the benchmark does)".format(cv, bk), abs(float(s["rel"]) - rel_w)
              < EPS, (key, s))


def tie_b(x, it, r, fi_p, fi_prices, fa_a, base, anchor, ptol, sp_fi_ref):
    """The B replay of one priced shift proposal against its stored values; returns v."""
    key = tuple(x["key"])
    bB = x["boards"]["B"]
    dt, fi, rw = bB["dt"], bB["fi"], bB["rw"]
    check("B, K: priced", dt["stage_cert"] == "qual" == it["dt_stage_cert"], key)
    check("B, K: terminals and codes equal the stored census",
          (dt["term_cert"], dt["term_feas"], dt["codes"]) ==
          (it["dt_term_cert"], it["dt_term_feas"], it["dt_codes"]), key)
    close("B, K: adjusted objective = dt_obj", dt["obj"], it["dt_obj"], TOL, key)
    close("B, K: original-field objective = dt_obj_orig", dt["obj_orig"], it["dt_obj_orig"],
          TOL, key)
    close("B, K: bound = the logged dt_lb", dt["lb"], it["dt_lb"], TOL, key)
    close("B, K: certified gap = dt_gap", dt["gap"], it["dt_gap"], TOL, key)
    close("B, K: D-REL2 reference = dt_ref2", dt["ref2"], it["dt_ref2"], TOL, key)
    if "Boff" in x["boards"]:
        o = x["boards"]["Boff"]["dt"]
        check("Boff, K: the patched function with the switch off gives the unpatched schedule "
              "byte for byte", o["digest"] == dt["digest"] and o["obj"] == dt["obj"]
              and o["gap"] == dt["gap"] and o["lb"] == dt["lb"], key)
    for k in ("term_cert", "stage_cert", "term_feas", "stage_feas", "codes", "ref2_from"):
        check("B, FI: {} equals the stored full-information record".format(k), fi[k] == fi_p[k],
              (key, k, fi[k], fi_p[k]))
    for k in ("obj", "obj_orig", "lb", "gap", "ref2"):
        close("B, FI: {} = the stored full-information record".format(k), fi[k], fi_p[k], TOL,
              key)
    check("B, realised: terminals equal the stored census",
          (rw["term_cert"], rw["term_feas"]) == (it["rw_term"], it["rw_term_feas"]), key)
    close("B, realised: original-field objective = rw_obj_orig", rw["obj_orig"],
          it["rw_obj_orig"], TOL, key)
    close("B, realised: adjusted objective = rw_obj", rw["obj"], it["rw_obj"], TOL, key)
    for bk in ("dt", "fi", "rw"):
        check("B: every schedule complete ({})".format(bk), bB[bk]["complete"], key)
        check("B: the board carries the shifted order ({})".format(bk),
              len(bB[bk]["shifted"]) > 0, key)
        check_shifted(bB[bk], "B", key, bk)
    v = values_of(bB, it, fa_a, base, anchor)
    close("B: damage = the stored damage", v["dmg"], r["dmg"], ptol, key)
    close("B: lower end of the realised-cost interval", v["lo"], r["lo"], ptol, key)
    close("B: upper end of the realised-cost interval", v["hi"], r["hi"], ptol, key)
    x2 = record_of(r, v)
    for dl in DELTAS.values():
        check("B: label at delta {:.2f} equals the stored label".format(dl),
              n13.costly_of(x2, dl) == n13.costly_of(r, dl), key)
    for g in DESIGNS:
        close("B, K: price {} = the stored record".format(g), v["pk"][g], r["p_" + g], ptol, key)
        check("B, K: flag {} equals the stored flag".format(g), x2["ref_" + g] == r["ref_" + g],
              (key, g))
        close("B, FI: price {} = the stored record".format(g), v["pf"][g], r["fi"]["p_" + g],
              ptol, key)
        close("B, FI: price {} = the stored full-information prices".format(g), v["pf"][g],
              fi_prices[g], 1e-12, key)
        check("B, FI: flag {} equals the stored flag".format(g),
              x2["fi"]["ref_" + g] == r["fi"]["ref_" + g], (key, g))
    close("B: certificate price from the board's bound = the stored gap", v["gap_k"],
          it["dt_gap"], 1e-12, key)
    close("B: second price (K) = n16's g_orig", v["g_orig"], r["g_orig"], 1e-12, key)
    close("B: second price (FI) = the stored rule", v["sp_fi"], sp_fi_ref, 1e-12, key)
    for k in ("ref_k", "ref_f", "two_k", "two_f", "sp", "ref_" + UNION):
        check("B: {} equals the stored record".format(k), x2[k] == r[k], (key, k))
    return v


def check_d(x, key):
    bD = x["boards"]["D"]
    for bk in ("dt", "fi", "rw"):
        b = bD[bk]
        if b is None:
            continue
        check("D: no instrument fault ({})".format(bk), b["term_feas"] != "execution_failed",
              (key, bk, b["codes"]))
        if b["digest"] is not None:
            check("D: every schedule complete ({})".format(bk), b["complete"], (key, bk))
            check_shifted(b, "D", key, bk)
            bb = x["boards"]["B"][bk]
            check("D: the shifted orders' releases equal B's ({})".format(bk),
                  [(s["oid"], s["rel"]) for s in b["shifted"]]
                  == [(s["oid"], s["rel"]) for s in bb["shifted"]], (key, bk))
    if bD["dt"]["digest"] is not None:
        check("D, K: stages 1-2 outcome equals B (schema, feasibility)",
              (bD["dt"]["term_feas"], bD["dt"]["stage_feas"])
              == (x["boards"]["B"]["dt"]["term_feas"], x["boards"]["B"]["dt"]["stage_feas"]),
              key)


# --------------------------------------------------------------------------- #
# Tallies                                                                      #
# --------------------------------------------------------------------------- #
def headline(boot, sel):
    out = OrderedDict(priced=len(sel), instances=len({r["instance_id"] for r in sel}))
    for dtok, delta in DELTAS.items():
        o, _c, _l = n20.tally(sel, lambda r, d=delta: n13.costly_of(r, d))
        h = OrderedDict((k, o[k]) for k in HL)
        for key, flag in (("lr", lambda r: r["ref_k"]), ("l2", lambda r: r["two_k"])):
            s = n13.score(boot, sel, flag, delta)
            check("score() agrees with the tally ({})".format(key),
                  (s["costly"], s["cheap"]) == (o["costly"], o["low"])
                  and s["fr"] == (o["low_ref_k"] if key == "lr" else o["low_two_k"])
                  and s["miss"] == (o["app_k"] if key == "lr" else o["two_app_k"]))
            h[key + "_share"], h[key + "_lo"], h[key + "_hi"] = (s["fr_share"], s["fr_lo"],
                                                                  s["fr_hi"])
        out[dtok] = h
    return out


def hl_cells(h, dtok):
    x = h[dtok]
    return [h["priced"], x["costly"], x["low"], x["und"],
            "{} / {} / {}".format(x["ref_k"], x["ref_f"], x["ref_both"]),
            "{} / {}".format(x["app_k"], x["app_f"]),
            "{} / {}".format(x["two_app_k"], x["two_app_f"]),
            "{} -> {}".format(x["low_ref_k"], x["low_two_k"]),
            "{} -> {}".format(x["low_ref_f"], x["low_two_f"]),
            "{} [{}, {}]".format(pctpv(x["lr_share"]), pctpv(x["lr_lo"]), pctpv(x["lr_hi"])),
            "{} [{}, {}]".format(pctpv(x["l2_share"]), pctpv(x["l2_lo"]), pctpv(x["l2_hi"]))]


HL_HEAD = ["priced", "costly", "low-cost", "undecided", "costly referred K / FI / both",
           "costly applied K / FI", "costly applied with second price K / FI",
           "low-cost referred K, without -> with second price",
           "low-cost referred FI, without -> with second price",
           "low-cost share K [95% CI]", "low-cost share K with second price [95% CI]"]


def hl_macros(scope, cv, h):
    txt = SCOPES[scope]
    add(scope + "Priced" + cv, grp(h["priced"]),
        "[1] {}, convention {}: priced proposals".format(txt, cv))
    for dtok, delta in DELTAS.items():
        for k, (tok, ftxt) in HL.items():
            add(scope + dtok + tok + cv, grp(h[dtok][k]),
                "[1-4] {}, convention {}, delta = {:.2f}, tau = 0.20: {}".format(
                    txt, cv, delta, ftxt))
        for key, tok, ftxt in (("lr", "LowRefK", "low-cost referral share, certificate on the "
                                                  "known board"),
                               ("l2", "LowTwoRefK", "low-cost referral share with the second "
                                                    "price, known board")):
            add(scope + dtok + tok + "Share" + cv, pctv(h[dtok][key + "_share"]),
                "[4] {}, convention {}, delta = {:.2f}: {}".format(txt, cv, delta, ftxt))
            add(scope + dtok + tok + "Lo" + cv, pctv(h[dtok][key + "_lo"]),
                "[4] {}, convention {}, delta = {:.2f}: lower end of the 95% cluster-bootstrap "
                "interval of the same (n2 seed, 20,000 replicates, 60 instance clusters)".format(
                    txt, cv, delta))
            add(scope + dtok + tok + "Hi" + cv, pctv(h[dtok][key + "_hi"]),
                "[4] {}, convention {}, delta = {:.2f}: upper end of the same interval".format(
                    txt, cv, delta))


def qstats(xs):
    a = np.asarray(xs, dtype=float)
    p10, med, p90 = (float(v) for v in np.percentile(a, [10, 50, 90]))
    return OrderedDict(n=len(xs), median=med, p10=p10, p90=p90, min=float(a.min()),
                       max=float(a.max()))


def boot_ci_here(inst_of, flags, instances):
    """A bootstrap written here with n2's seed and draw order (the second code path)."""
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
# Stored inputs                                                                #
# --------------------------------------------------------------------------- #
def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


def load_suite_side(boot_holder):
    hashes, items_dt, _pub, boot, fc = n13.load_inputs()
    check("60 bootstrap clusters, 20,000 replicates, n2 seed",
          boot.k == 60 and boot.idx.shape == (20000, 60) and n2.SEED == 20261026)
    boot_holder.append(boot)
    recs, by, _spfi, _site, _frecs = n20.build(items_dt, fc, boot)
    check("1,356 priced proposals (suite)", len(recs) == 1356, len(recs))
    dc = D.Checker()
    suite = OrderedDict((x["item_id"], x) for x in D.load_published(dc))
    check("published suite loads through suite_gate (SHA-256 asserted)", not dc.failures)
    fi_logged = {}
    for x in n13.read_jsonl(n13.IN["fullinfo"]):
        check("one full-information record per suite proposal", x["uid"] not in fi_logged,
              x["uid"])
        fi_logged[x["uid"]] = x
    fa_logged = {}
    for a in n13.read_jsonl(n13.IN["anchors_fc"]):
        if a["reading"] == "FI":
            fa_logged[(a["iid"], a["fk"], float(a["t_d"]))] = a["a"]
    for r in recs:
        r["scope"], r["set"] = "Suite", "suite"
        r["family"] = suite[r["item_id"]]["family_id"]
        r["subclass"] = suite[r["item_id"]]["subclass"]
    return dict(recs=recs, by=by, suite=suite, fi=fi_logged, fa=fa_logged, hashes=hashes)


def load_new_side(boot):
    n17rows = [x for x in n13.read_csv(IN26["n17_rows"])]
    held = {(x["seed"], x["item_id"]): x for x in n17rows if x["held_out"] == "True"}
    check("3,733 held-out rows in N17_rows.csv", len(held) == 3733, len(held))
    out = dict(recs=[], by={}, suite={}, fi={}, fa={}, rows=held, all_rows={})
    for x in n17rows:
        out["all_rows"][(x["seed"], x["item_id"])] = x
    for seed in SEEDS:
        items, fi_rows, meta, _rep = n17.check_replay(seed)
        check("the stored replay of seed {} ran on the fresh suite file".format(seed),
              meta["suite_sha256"] == sha256_file(IN26["heldout_suite_" + seed]))
        suite = OrderedDict((it["item_id"], it) for it in read_jsonl(
            IN26["heldout_suite_" + seed]))
        check("fresh suite {}: 2,000 items".format(seed), len(suite) == 2000)
        out["suite"][seed] = suite
        recs, by_dt, _priced, _krows = n17.build_records(items, fi_rows)
        out["by"][seed] = {r["item_id"]: r for r in items}
        fi = {}
        for p in fi_rows:
            check("one full-information record per held-out proposal (s = 0)",
                  p["uid"] not in fi and p["s"] == 0 and p["reading"] == "FI", (seed, p["uid"]))
            fi[p["uid"]] = p
        out["fi"][seed] = fi
        fa = {}
        for a in read_jsonl(IN26["heldout_fi_anchors.jsonl_" + seed]):
            if a["reading"] == "FI":
                fa[(a["iid"], a["fk"], float(a["t_d"]))] = a["a"]
        out["fa"][seed] = fa
        anchors = D.load_anchor_records()
        for r in recs:
            k = (seed, r["item_id"])
            if k not in out["all_rows"]:
                continue
            row = out["all_rows"][k]
            it = by_dt[r["item_id"]]
            r["seed"], r["scope"], r["set"] = seed, "New", seed
            r["held_out"] = row["held_out"] == "True"
            r["family"] = suite[r["item_id"]]["family_id"]
            r["field"] = r["split"] == "field_changing"
            r["ref_k"] = n13.refers(r, CERT)
            r["ref_f"] = n13.refers(r["fi"], CERT)
            r["two_k"] = n16.sp_flag(r, CERT)
            p = fi[r["item_id"]]
            a = fa[(it["instance_id"], it["frozen_seed"], float(it["t_d"]))]
            r["sp_fi"] = (p["p"]["obj_orig"] - a["lb"]) / max(a["lb"], FLOOR)
            r["two_f"] = r["ref_f"] or (r["field"] and r["sp_fi"] > TAU)
            r["n_ops"] = it["n_ops"]
            check("held-out anchor of the row equals rule_anchor",
                  abs(float(anchors[(it["instance_id"], it["frozen_seed"])]["wwt_original_bh"])
                      - it["pub_anchor_wwt"]) < 1e-9, k)
            # the record against the published row
            close("held-out record: certificate price = N17_rows p_cert_K", r["p_G-CERT"],
                  float(row["p_cert_K"]), CSV_TOL, k)
            close("held-out record: FI certificate price = N17_rows p_cert_FI",
                  r["fi"]["p_G-CERT"], float(row["p_cert_FI"]), CSV_TOL, k)
            close("held-out record: g_orig = N17_rows", r["g_orig"], float(row["g_orig"]),
                  CSV_TOL, k)
            check("held-out record: class, op types and edit type equal N17_rows",
                  (r["primary_class"], r["op_types"], r["split"]) ==
                  (row["primary_class"], row["op_types"], row["edit_type"]), k)
            for dl, col in ((0.20, "cost_class_020"), (0.10, "cost_class_010")):
                check("held-out record: label equals N17_rows {}".format(col),
                      n16.cost_word(n13.costly_of(r, dl)) == row[col], k)
            check("held-out record: flags equal N17_rows",
                  (str(r["ref_k"]), str(r["ref_f"]), str(r["two_k"])) ==
                  (row["refers_cert"], row["refers_certfi"], row["refers_certsp"]), k)
            if r["held_out"]:
                out["recs"].append(r)
    check("3,733 held-out records built from the stored replays", len(out["recs"]) == 3733,
          len(out["recs"]))
    check("held-out records cover the 60 bootstrap clusters",
          {r["instance_id"] for r in out["recs"]} <= set(boot.index))
    return out


def b_selfcheck(boot, suite_recs, new_recs):
    """Block B: the frozen counts from the stored records (before any D number)."""
    hb = OrderedDict([("Suite", headline(boot, suite_recs)), ("New", headline(boot, new_recs))])
    for (scope, delta), want in FROZEN_COUNTS.items():
        dtok = "DeltaTwenty" if delta == 0.20 else "DeltaTen"
        for k, v in want.items():
            got = hb[scope]["priced"] if k == "priced" else hb[scope][dtok][k]
            check("B self-check: {} at delta {:.2f}: {} = {}".format(scope, delta, k, v),
                  got == v, got)
    hs = hb["Suite"]["DeltaTwenty"]
    rk = {r["item_id"] for r in suite_recs if n13.costly_of(r, 0.20) == 1 and r["ref_k"]}
    rf = {r["item_id"] for r in suite_recs if n13.costly_of(r, 0.20) == 1 and r["ref_f"]}
    check("B self-check: the same 168 costly proposals referred on K and with FI (suite)",
          rk == rf and len(rk) == 168 == hs["ref_both"])
    m17 = n13.macros_of(IN26["n17_macros"])
    hn = hb["New"]["DeltaTwenty"]
    for key, tok in (("lr", "CertLowRef"), ("l2", "CertSPLowRef")):
        check("B self-check: new-draw low-cost share and interval equal N17 ({})".format(tok),
              (pctv(hn[key + "_share"]), pctv(hn[key + "_lo"]), pctv(hn[key + "_hi"])) ==
              (m17["nSeventeenPooled" + tok + "ShareTwenty"],
               m17["nSeventeenPooled" + tok + "LoTwenty"],
               m17["nSeventeenPooled" + tok + "HiTwenty"]),
              (hn[key + "_share"], hn[key + "_lo"], hn[key + "_hi"]))
    for dtok, t in (("DeltaTwenty", "Twenty"), ("DeltaTen", "Ten")):
        o = hb["New"][dtok]
        for k, name in (("costly", "Costly"), ("low", "Low"), ("app_k", "CertApplied"),
                        ("ref_k", "CertReferred"), ("low_ref_k", "CertLowRef"),
                        ("app_f", "CertFIApplied"), ("ref_f", "CertFIReferred"),
                        ("low_ref_f", "CertFILowRef"), ("two_app_k", "CertSPApplied"),
                        ("low_two_k", "CertSPLowRef")):
            check("B self-check: new draws {} {} equals N17 macro".format(dtok, k),
                  grp(o[k]) == m17["nSeventeenPooled" + name + t], (o[k],))
    m15 = n13.macros_of(IN26["n15_macros"])
    check("B self-check: suite 1,356 priced equals N15", m15["nFifteenPriced"] == "1{,}356")
    return hb


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main(argv):
    selftest_only = "--selftest" in argv
    t_start = time.time()
    for k, p in IN26.items():
        if not Path(p).is_file() and k not in NOT_SHIPPED_OK:
            raise SystemExit("missing input {}: {}".format(k, p))
    say("design.md sha256 {} (asserted); frozen prefixes asserted; {} l1adapter .py files "
        "hashed; cores {}".format(DESIGN_SHA[:12], len(ADAPTER0), sorted(_aff)))
    boot_h = []
    SU = load_suite_side(boot_h)
    boot = boot_h[0]
    NE = load_new_side(boot)
    # B. the frozen counts, before any replay
    HB = b_selfcheck(boot, SU["recs"], NE["recs"])
    say("B self-check passed: suite 1,356 priced, 186 costly, 168/168 referred, 18 applied, 0 "
        "with the second price, 15 -> 22 low-cost referred; new draws 3,733 priced, 529 "
        "costly, 45 applied, 4 with the second price, 65 -> 98 of 3,204")
    # populations
    items_of = {"suite": SU["suite"]}
    stored_of = {"suite": SU["by"]}
    for seed in SEEDS:
        items_of[seed] = NE["suite"][seed]
        stored_of[seed] = NE["by"][seed]
    rec_of = {}
    for r in SU["recs"]:
        rec_of[("suite", r["item_id"])] = r
    for r in NE["recs"]:
        rec_of[(r["seed"], r["item_id"])] = r

    def can_of(key):
        return optypes(D.canonical_ops(items_of[key[0]][key[1]]))

    shift_keys = sorted(k for k in rec_of if "reassign_window" in can_of(k))
    for k in shift_keys:
        check("stored op_types carry the shift", "reassign_window" in
              stored_of[k[0]][k[1]]["op_types"].split("|"), k)
    noshift = sorted(k for k in rec_of if "reassign_window" not in can_of(k))
    sample_keys = sorted(random.Random(SAMPLE_SEED).sample(noshift, SAMPLE_N))
    boff_keys = set(random.Random(SAMPLE_SEED + 1).sample(shift_keys, BOFF_N))
    unpriced = []
    for st, items in items_of.items():
        for i, it in items.items():
            if "reassign_window" in optypes(D.canonical_ops(it)) and (st, i) not in rec_of:
                if st != "suite" and (st, i) in NE["all_rows"]:
                    continue                    # priced, a duplicate of a published item
                unpriced.append((st, i))
    unpriced.sort()
    n_shift_suite = sum(1 for k in shift_keys if k[0] == "suite")
    n_shift_new = len(shift_keys) - n_shift_suite
    check("351 priced suite proposals carry a reassign_window (N24 block B2)",
          n_shift_suite == 351, n_shift_suite)
    check("942 priced held-out proposals carry a reassign_window", n_shift_new == 942,
          n_shift_new)
    kinds = ([(k, "shift") for k in shift_keys] + [(k, "sample") for k in sample_keys]
             + [(k, "unpriced_issuable" if stored_of[k[0]][k[1]]["issuable"]
                 else "unpriced_not_issuable") for k in unpriced])
    smoke = os.environ.get("N26_SMOKE")
    if smoke:
        if not selftest_only:
            raise SystemExit("[n26] N26_SMOKE is for test runs with --selftest")
        keep = set(smoke.split(","))
        kinds = [(k, kd) for k, kd in kinds
                 if items_of[k[0]][k[1]]["instance"]["instance_id"] in keep]
    # P. probes
    block_p()
    say("probes passed (a, b, c)")
    # R. replay
    anchors = D.load_anchor_records()
    full_br = D.full_brackets()
    tasks = build_tasks(kinds, items_of, stored_of, anchors, boff_keys)
    say("replaying {} shift + {} sample + {} unpriced proposals in {} (set, instance) tasks, "
        "{} workers on cores {}".format(sum(1 for _k, kd in kinds if kd == "shift"),
                                        sum(1 for _k, kd in kinds if kd == "sample"),
                                        sum(1 for _k, kd in kinds if kd.startswith("unpriced")),
                                        len(tasks), WORKERS, sorted(_aff)))
    t_rep = time.time()
    cache = os.environ.get("N26_REPLAY_CACHE")
    if cache and Path(cache).is_file():
        import pickle
        if not selftest_only:
            raise SystemExit("[n26] N26_REPLAY_CACHE is for test runs with --selftest; "
                             "the outputs need a fresh replay")
        with open(cache, "rb") as fh:
            results = pickle.load(fh)
        say("replay loaded from the replay cache")
    else:
        results = run_replay(tasks)
        if cache:
            import pickle
            with open(cache, "wb") as fh:
                pickle.dump(results, fh)
    wall_rep = time.time() - t_rep
    rep = OrderedDict()
    for t, res in zip(tasks, results):
        check("task and result agree", (t["set"], t["iid"]) == (res["set"], res["iid"]))
        for fk, dg in res["traj_digest"].items():
            check("the trajectory's schedule digest equals rule_anchor.json's",
                  dg == t["digest"][fk], (t["iid"], fk))
        for x in res["items"]:
            k = tuple(x["key"])
            check("one replay per proposal", k not in rep, k)
            rep[k] = x
    check("every proposal replayed", set(rep) == {k for k, _kd in kinds}, len(rep))
    for k, x in rep.items():
        st = stored_of[k[0]][k[1]]
        check("decision instant equals the stored census", x["t_d"] == float(st["t_d"]), k)
        check("issuability equals the stored census", x["issuable"] == st["issuable"], k)
    # T. the B tie of every priced shift proposal
    valsB, valsD = OrderedDict(), OrderedDict()
    for k, x in rep.items():
        if x["kind"] != "shift":
            continue
        st, i = k
        it = stored_of[st][i]
        r = rec_of[k]
        a = anchors[(it["instance_id"], it["frozen_seed"])]
        anchor = float(a["wwt_original_bh"])
        base = full_br.get((it["instance_id"], D.BASE_FP))
        if st == "suite":
            fi_p, fi_pr = SU["fi"][i]["p"], SU["fi"][i]["prices"]
            fa_a = SU["fa"][(it["instance_id"], it["frozen_seed"], float(it["t_d"]))]
            ptol = CSV_TOL
        else:
            fi_p, fi_pr = NE["fi"][st][i]["p"], NE["fi"][st][i]["prices"]
            fa_a = NE["fa"][st][(it["instance_id"], it["frozen_seed"], float(it["t_d"]))]
            ptol = TOL
        valsB[k] = tie_b(x, it, r, fi_p, fi_pr, fa_a, base, anchor, ptol, r["sp_fi"])
        check_d(x, k)
        valsD[k] = values_of(x["boards"]["D"], it, fa_a, base, anchor)
    # the sample: B equals the stored totals, D equals B byte for byte
    n_sample = 0
    for k, x in rep.items():
        if x["kind"] != "sample":
            continue
        st, i = k
        it = stored_of[st][i]
        fi_p = (SU["fi"][i] if st == "suite" else NE["fi"][st][i])["p"]
        bB, bD = x["boards"]["B"], x["boards"]["D"]
        close("sample B, K: dt_obj", bB["dt"]["obj"], it["dt_obj"], TOL, k)
        close("sample B, K: dt_gap", bB["dt"]["gap"], it["dt_gap"], TOL, k)
        close("sample B, realised: rw_obj_orig", bB["rw"]["obj_orig"], it["rw_obj_orig"], TOL, k)
        close("sample B, FI: obj", bB["fi"]["obj"], fi_p["obj"], TOL, k)
        close("sample B, FI: gap", bB["fi"]["gap"], fi_p["gap"], TOL, k)
        for bk in ("dt", "fi", "rw"):
            check("sample: no shifted order on the board ({})".format(bk),
                  bB[bk]["shifted"] == [] == bD[bk]["shifted"], k)
            check("sample: D schedule equals B byte for byte ({})".format(bk),
                  bB[bk]["digest"] == bD[bk]["digest"] and bB[bk]["digest"] is not None, k)
            for f in ("term_cert", "stage_cert", "codes", "obj", "obj_orig", "lb", "gap",
                      "ref2"):
                check("sample: D {} equals B ({})".format(f, bk), bB[bk][f] == bD[bk][f],
                      (k, bk, f))
        n_sample += 1
    if not smoke:
        check("50 sampled proposals without a shift asserted identical", n_sample == SAMPLE_N)
    # the unpriced shift proposals: B equals the stored census, D equals B
    unp = OrderedDict()
    for k, x in rep.items():
        if not x["kind"].startswith("unpriced"):
            continue
        st, i = k
        it = stored_of[st][i]
        kB, kD = x["boards"]["B"]["dt"], x["boards"]["D"]["dt"]
        fB, fD = x["boards"]["B"]["fi"], x["boards"]["D"]["fi"]
        check("unpriced B, K: terminal and stage equal the stored census",
              (kB["term_cert"], kB["stage_cert"]) == (it["dt_term_cert"], it["dt_stage_cert"]),
              (k, kB["term_cert"], it["dt_term_cert"]))
        extra = sorted(set(kB["codes"]) - set(it["dt_codes"] or []))
        check("unpriced B, K: the stored codes are among the replayed codes",
              set(it["dt_codes"] or []) <= set(kB["codes"]), (k, kB["codes"], it["dt_codes"]))
        check("unpriced B, K: a replayed code beyond the stored ones is the running-work code "
              "on an item outside the direct benchmark", not extra
              or (extra == [n17.RUNNING_CODE] and not it["issuable"]), (k, extra))
        same = all(kB[f] == kD[f] for f in ("term_cert", "stage_cert", "codes", "obj", "gap")) \
            and all(fB[f] == fD[f] for f in ("term_cert", "stage_cert", "codes", "obj", "gap"))
        unp[k] = dict(kind=x["kind"], stage=kB["stage_cert"], term=kB["term_cert"],
                      codes=kB["codes"], fi_stage=fB["stage_cert"], fi_term=fB["term_cert"],
                      same=same, d_term=kD["term_cert"], d_stage=kD["stage_cert"],
                      d_fi_term=fD["term_cert"], extra=extra,
                      digest_same=kB["digest"] == kD["digest"])
    say("B replay tied to every stored value ({} shift proposals, {} sampled, {} unpriced)".format(
        len(valsB), n_sample, len(unp)))
    if smoke:
        for k, v in valsD.items():
            say("smoke {}: K price B {:.4f} D {:.4f}; FI B {:.4f} D {:.4f}; g_orig B {:.4f} D "
                "{:.4f}; damage B {} D {}".format(
                    k, valsB[k]["pk"][CERT], v["pk"][CERT], valsB[k]["pf"][CERT], v["pf"][CERT],
                    valsB[k]["g_orig"], v["g_orig"], bh1(valsB[k]["dmg"]), bh1(v["dmg"])))
        say("smoke run: {} checks, replay {:.0f}s".format(NCHECK[0], wall_rep))
        return 0
    # D. records
    recsB = OrderedDict([("Suite", SU["recs"]), ("New", NE["recs"])])
    recsD = OrderedDict([("Suite", []), ("New", [])])
    rbyB, rbyD = {}, {}
    not_priced_D = []
    for scope, recs in recsB.items():
        for r in recs:
            k = ("suite", r["item_id"]) if scope == "Suite" else (r["seed"], r["item_id"])
            rbyB[k] = r
            if k not in valsD:
                recsD[scope].append(r)
                rbyD[k] = r
                continue
            v = valsD[k]
            if not v["priced_k"]:
                not_priced_D.append(k)
                continue
            x = record_of(r, v)
            recsD[scope].append(x)
            rbyD[k] = x
    say("D records built: suite {}, new draws {} priced ({} shift proposals not priced on K "
        "under D)".format(len(recsD["Suite"]), len(recsD["New"]), len(not_priced_D)))
    return analyse(dict(SU=SU, NE=NE, HB=HB, boot=boot, rep=rep, valsB=valsB, valsD=valsD,
                        recsB=recsB, recsD=recsD, rbyB=rbyB, rbyD=rbyD, unp=unp,
                        not_priced_D=not_priced_D, shift_keys=shift_keys,
                        sample_keys=sample_keys, boff_keys=boff_keys, wall_rep=wall_rep,
                        t_start=t_start, selftest_only=selftest_only, tasks=tasks,
                        stored_of=stored_of, items_of=items_of))


# --------------------------------------------------------------------------- #
# Analysis, outputs                                                            #
# --------------------------------------------------------------------------- #
def scope_of(k):
    return "Suite" if k[0] == "suite" else "New"


def analyse(A):
    boot, rep = A["boot"], A["rep"]
    recsB, recsD, rbyB, rbyD = A["recsB"], A["recsD"], A["rbyB"], A["rbyD"]
    valsB, valsD = A["valsB"], A["valsD"]
    shift_keys = A["shift_keys"]
    check("no shift proposal loses its price on K under D", not A["not_priced_D"],
          A["not_priced_D"][:10])
    # 1-4. headline
    H = OrderedDict()
    for scope in SCOPES:
        H[(scope, "B")] = A["HB"][scope]
        H[(scope, "D")] = headline(boot, recsD[scope])
    for scope in SCOPES:
        check("{}: priced the same under B and D".format(scope),
              H[(scope, "B")]["priced"] == H[(scope, "D")]["priced"])
        for cv in CONVS:
            hl_macros(scope, cv, H[(scope, cv)])
    NUM["headline"] = OrderedDict(("{} {}".format(s, c), h) for (s, c), h in H.items())
    # per seed (summary only)
    HS = OrderedDict()
    for seed in SEEDS:
        for cv in CONVS:
            HS[(seed, cv)] = headline(boot, [r for r in recsB["New"] if r["seed"] == seed]
                                      if cv == "B" else
                                      [r for r in recsD["New"] if r["seed"] == seed])
    for dtok in DELTAS:
        for k in ("priced", "costly", "ref_k", "app_k", "two_app_k", "low_ref_k", "low_two_k"):
            for cv in CONVS:
                tot = (sum(HS[(s, cv)]["priced"] for s in SEEDS) if k == "priced" else
                       sum(HS[(s, cv)][dtok][k] for s in SEEDS))
                ref = H[("New", cv)]["priced"] if k == "priced" else H[("New", cv)][dtok][k]
                check("new draws: pooled = sum of the three seeds ({} {} {})".format(dtok, k, cv),
                      tot == ref, (tot, ref))
    # 5. the fate of the costly proposals applied under B at 0.20
    fate = OrderedDict()
    for scope in SCOPES:
        M = [r for r in recsB[scope] if n13.costly_of(r, 0.20) == 1 and not r["ref_k"]]
        want = {"Suite": (18, 15, 3), "New": (45, 33, 12)}[scope]
        check("{}: the costly proposals applied under B by template family".format(scope),
              (len(M), sum(1 for r in M if r["family"] == FAMS["Shift"]),
               sum(1 for r in M if r["family"] == FAMS["Prio"])) == want,
              Counter(r["family"] for r in M))
        for fam_tok, fam in [("All", None)] + list(FAMS.items()):
            sel = [r for r in M if fam is None or r["family"] == fam]
            rows = []
            for r in sel:
                k = ("suite", r["item_id"]) if scope == "Suite" else (r["seed"], r["item_id"])
                x = rbyD[k]
                rows.append((k, r, x))
            o = OrderedDict(n=len(sel))
            o["shift"] = sum(1 for k, _r, _x in rows if k in valsD)
            o["costly"] = sum(1 for _k, _r, x in rows if n13.costly_of(x, 0.20) == 1)
            o["low"] = sum(1 for _k, _r, x in rows if n13.costly_of(x, 0.20) == 0)
            o["und"] = o["n"] - o["costly"] - o["low"]
            o["ref_k"] = sum(1 for _k, _r, x in rows if x["ref_k"])
            o["ref_f"] = sum(1 for _k, _r, x in rows if x["ref_f"])
            o["two_k"] = sum(1 for _k, _r, x in rows if x["two_k"])
            o["two_f"] = sum(1 for _k, _r, x in rows if x["two_f"])
            o["costly_app_k"] = sum(1 for _k, _r, x in rows
                                    if n13.costly_of(x, 0.20) == 1 and not x["ref_k"])
            o["costly_app_f"] = sum(1 for _k, _r, x in rows
                                    if n13.costly_of(x, 0.20) == 1 and not x["ref_f"])
            o["costly_two_app_k"] = sum(1 for _k, _r, x in rows
                                        if n13.costly_of(x, 0.20) == 1 and not x["two_k"])
            o["costly_two_app_f"] = sum(1 for _k, _r, x in rows
                                        if n13.costly_of(x, 0.20) == 1 and not x["two_f"])
            o["b_two_k"] = sum(1 for _k, r, _x in rows if r["two_k"])
            sh = [k for k, _r, _x in rows if k in valsD]
            o["obj_rise_k"] = sum(rep[k]["boards"]["D"]["dt"]["obj"]
                                  - rep[k]["boards"]["B"]["dt"]["obj"] for k in sh)
            o["lb_rise_k"] = sum(rep[k]["boards"]["D"]["dt"]["lb"]
                                 - rep[k]["boards"]["B"]["dt"]["lb"] for k in sh)
            o["max_cert_k_d"] = max([valsD[k]["pk"][CERT] for k in sh], default=None)
            o["rows"] = rows
            fate[(scope, fam_tok)] = o
        for k in [kk for kk in (fate[(scope, "Prio")]["rows"])]:
            check("{}: the priority edits carry no shift, so D equals B".format(scope),
                  k[0] not in valsD and k[2] is k[1], k[0])
    fate_tok = OrderedDict([
        ("n", ("N", "costly proposals the certificate applies on the known board under "
                    "convention B (delta = tau = 0.20)")),
        ("costly", ("CostlyD", "of these, still costly under convention D")),
        ("low", ("LowD", "of these, low-cost under convention D")),
        ("und", ("UndD", "of these, undecided under convention D")),
        ("ref_k", ("RefKD", "of these, referred by the certificate on the known board under D")),
        ("ref_f", ("RefFID", "of these, referred by the certificate with full information "
                             "under D")),
        ("two_k", ("TwoRefKD", "of these, referred on the known board with the second price "
                               "under D")),
        ("two_f", ("TwoRefFID", "of these, referred with full information with the second "
                                "price under D")),
        ("costly_app_k", ("CostlyAppKD", "of these, still costly and applied by the "
                                         "certificate on the known board under D")),
        ("costly_app_f", ("CostlyAppFID", "of these, still costly and applied by the "
                                          "certificate with full information under D")),
        ("costly_two_app_k", ("CostlyTwoAppKD", "of these, still costly and applied on the "
                                                "known board with the second price under D")),
        ("costly_two_app_f", ("CostlyTwoAppFID", "of these, still costly and applied with full "
                                                 "information with the second price under D")),
        ("b_two_k", ("TwoRefKB", "of these, referred on the known board with the second price "
                                 "under B")),
    ])
    fam_txt = {"All": "all template families", "Shift": "template family "
               "v4_sign_flipped_shift (sign-reversed shifts)", "Prio": "template family "
               "v4_objective_shifting (priority edits)"}
    for (scope, fam_tok), o in fate.items():
        for k, (tok, ftxt) in fate_tok.items():
            add(scope + "Miss" + fam_tok + tok, grp(o[k]),
                "[5] {}, {}: {}".format(SCOPES[scope], fam_txt[fam_tok], ftxt))
        if fam_tok == "Shift":
            add(scope + "MissShiftObjRiseK", bhm(o["obj_rise_k"]),
                "[5] {}, {}: rise of the known-board objective on the edited values, D minus "
                "B, summed over these proposals, weighted bh".format(SCOPES[scope],
                                                                     fam_txt[fam_tok]))
            add(scope + "MissShiftLbRiseK", bhm(o["lb_rise_k"]),
                "[5] {}, {}: rise of the known-board bound (LB2 on the edited values), D minus "
                "B, summed over the same proposals, weighted bh".format(SCOPES[scope],
                                                                        fam_txt[fam_tok]))
            add(scope + "MissShiftMaxCertKD", bh2(o["max_cert_k_d"]),
                "[5] {}, {}: largest certificate price on the known board under D".format(
                    SCOPES[scope], fam_txt[fam_tok]))
    NUM["fate"] = OrderedDict(("{} {}".format(s, f), {k: v for k, v in o.items() if k != "rows"})
                              for (s, f), o in fate.items())
    # 6. correct translations that carry a shift
    corr = OrderedDict()
    for scope in SCOPES:
        for ctok, cls in [("All", None)] + list(CORRECT_CLS.items()):
            for cv in CONVS:
                src = recsB[scope] if cv == "B" else recsD[scope]
                sel = [r for r in src if r["primary_class"] in (("benign", "V3") if cls is None
                                                                else (cls,))
                       and (("suite", r["item_id"]) if scope == "Suite"
                            else (r["seed"], r["item_id"])) in valsD]
                o = OrderedDict(priced=len(sel))
                for dtok, delta in DELTAS.items():
                    lowf = [r for r in sel if n13.costly_of(r, delta) == 0]
                    cst = [r for r in sel if n13.costly_of(r, delta) == 1]
                    o[dtok] = OrderedDict(
                        costly=len(cst), low=len(lowf),
                        ref_k=sum(1 for r in sel if r["ref_k"]),
                        ref_k_low=sum(1 for r in lowf if r["ref_k"]),
                        ref_f=sum(1 for r in sel if r["ref_f"]),
                        ref_f_low=sum(1 for r in lowf if r["ref_f"]),
                        two_k=sum(1 for r in sel if r["two_k"]),
                        two_k_low=sum(1 for r in lowf if r["two_k"]))
                corr[(scope, ctok, cv)] = o
    ctxt = {"All": "correct translations that carry a shift (classes benign and V3)",
            "Benign": "benign correct translations that carry a shift",
            "VThree": "V3 correct translations that carry a shift"}
    ctok_f = OrderedDict([
        ("costly", ("Costly", "costly")), ("low", ("Low", "low-cost")),
        ("ref_k", ("RefK", "referred by the certificate on the known board")),
        ("ref_k_low", ("RefKLow", "low-cost and referred by the certificate on the known "
                                  "board")),
        ("ref_f", ("RefFI", "referred by the certificate with full information")),
        ("ref_f_low", ("RefFILow", "low-cost and referred by the certificate with full "
                                   "information")),
        ("two_k", ("TwoRefK", "referred on the known board with the second price")),
        ("two_k_low", ("TwoRefKLow", "low-cost and referred on the known board with the second "
                                     "price"))])
    for (scope, ctok, cv), o in corr.items():
        add(scope + "Correct" + ctok + "Priced" + cv, grp(o["priced"]),
            "[6] {}, {}, convention {}: priced".format(SCOPES[scope], ctxt[ctok], cv))
        for dtok, delta in DELTAS.items():
            for k, (tok, ftxt) in ctok_f.items():
                add(scope + "Correct" + ctok + dtok + tok + cv, grp(o[dtok][k]),
                    "[6] {}, {}, convention {}, delta = {:.2f}: {}".format(
                        SCOPES[scope], ctxt[ctok], cv, delta, ftxt))
    NUM["correct_translations"] = OrderedDict(("{} {} {}".format(*k), v)
                                              for k, v in corr.items())
    # 7. label and schedule changes; damage change
    chg = OrderedDict()
    dmg = OrderedDict()
    for scope in SCOPES:
        keys = [k for k in shift_keys if scope_of(k) == scope]
        o = OrderedDict(shift=len(keys))
        for dtok, delta in DELTAS.items():
            moves = Counter()
            lists = defaultdict(list)
            for k in keys:
                a, b = n13.costly_of(rbyB[k], delta), n13.costly_of(rbyD[k], delta)
                if a != b:
                    moves[(a, b)] += 1
                    lists[(a, b)].append(k)
            o[dtok] = OrderedDict(
                low_to_costly=moves[(0, 1)], costly_to_low=moves[(1, 0)],
                to_und=sum(v for (a, b), v in moves.items() if b is None and a is not None),
                from_und=sum(v for (a, b), v in moves.items() if a is None and b is not None),
                lists={"{}->{}".format(lbl(a), lbl(b)): ["{}:{}".format(*kk) for kk in v]
                       for (a, b), v in lists.items()})
        for bk, tok in (("dt", "K"), ("fi", "FI"), ("rw", "Real")):
            o["sched_diff_" + tok] = sum(
                1 for k in keys if rep[k]["boards"]["B"][bk]["digest"]
                != rep[k]["boards"]["D"][bk]["digest"])
        o["k_price_up"] = sum(1 for k in keys if valsD[k]["pk"][CERT] > valsB[k]["pk"][CERT]
                              + EPS)
        o["k_price_down"] = sum(1 for k in keys if valsD[k]["pk"][CERT] < valsB[k]["pk"][CERT]
                                - EPS)
        o["ref_k_on"] = sum(1 for k in keys if rbyD[k]["ref_k"] and not rbyB[k]["ref_k"])
        o["ref_k_off"] = sum(1 for k in keys if rbyB[k]["ref_k"] and not rbyD[k]["ref_k"])
        o["two_k_on"] = sum(1 for k in keys if rbyD[k]["two_k"] and not rbyB[k]["two_k"])
        o["two_k_off"] = sum(1 for k in keys if rbyB[k]["two_k"] and not rbyD[k]["two_k"])
        o["ref_f_on"] = sum(1 for k in keys if rbyD[k]["ref_f"] and not rbyB[k]["ref_f"])
        o["ref_f_off"] = sum(1 for k in keys if rbyB[k]["ref_f"] and not rbyD[k]["ref_f"])
        chg[scope] = o
        dd = [valsD[k]["dmg"] - valsB[k]["dmg"] for k in keys]
        q = qstats(dd)
        q["lower"] = sum(1 for d in dd if d < -EPS)
        q["higher"] = sum(1 for d in dd if d > EPS)
        q["equal"] = len(dd) - q["lower"] - q["higher"]
        q["argmin"] = "{}:{}".format(*keys[int(np.argmin(dd))])
        q["argmax"] = "{}:{}".format(*keys[int(np.argmax(dd))])
        dmg[scope] = q
        txt = SCOPES[scope]
        add(scope + "ShiftPriced", grp(len(keys)),
            "[7] {}: priced proposals that carry a reassign_window (replayed under D)".format(txt))
        for dtok, delta in DELTAS.items():
            for k, tok, ftxt in (("low_to_costly", "LabelLowToCostly", "low-cost under B, costly "
                                                                       "under D"),
                                 ("costly_to_low", "LabelCostlyToLow", "costly under B, "
                                                                       "low-cost under D"),
                                 ("to_und", "LabelToUnd", "decided under B, undecided under D"),
                                 ("from_und", "LabelFromUnd", "undecided under B, decided under "
                                                              "D")):
                add(scope + dtok + tok, grp(o[dtok][k]),
                    "[7] {}, delta = {:.2f}: shift proposals {}".format(txt, delta, ftxt))
        for tok, ftxt in (("K", "known boards"), ("FI", "full-information boards"),
                          ("Real", "realised whole-window runs")):
            add(scope + "SchedDiff" + tok, grp(o["sched_diff_" + tok]),
                "[7] {}: shift proposals whose schedule differs between B and D, {}".format(
                    txt, ftxt))
        for k, tok, ftxt in (("k_price_up", "CertPriceUpK", "certificate price on the known "
                                                            "board higher under D"),
                             ("k_price_down", "CertPriceDownK", "certificate price on the known "
                                                                "board lower under D"),
                             ("ref_k_on", "RefKOn", "referred on the known board under D, "
                                                    "applied under B"),
                             ("ref_k_off", "RefKOff", "applied on the known board under D, "
                                                      "referred under B"),
                             ("ref_f_on", "RefFIOn", "referred with full information under D, "
                                                     "applied under B"),
                             ("ref_f_off", "RefFIOff", "applied with full information under D, "
                                                       "referred under B"),
                             ("two_k_on", "TwoRefKOn", "referred with the second price under D, "
                                                       "applied under B"),
                             ("two_k_off", "TwoRefKOff", "applied with the second price under D, "
                                                         "referred under B")):
            add(scope + tok, grp(o[k]), "[7] {}: shift proposals {}".format(txt, ftxt))
        for k, tok, ftxt in (("median", "Median", "median"), ("p10", "PTen", "10th percentile"),
                             ("p90", "PNinety", "90th percentile"), ("min", "Min", "minimum"),
                             ("max", "Max", "maximum")):
            add(scope + "DmgDiff" + tok, bhm(q[k]),
                "[7] {}: realised damage, D minus B, weighted bh, {}".format(txt, ftxt))
        for k, tok in (("lower", "Lower"), ("higher", "Higher"), ("equal", "Equal")):
            add(scope + "DmgDiff" + tok, grp(q[k]),
                "[7] {}: shift proposals whose realised damage is {} under D".format(
                    txt, {"lower": "lower", "higher": "higher", "equal": "equal"}[k]))
    NUM["changes"] = chg
    NUM["damage_change"] = dmg
    # unpriced
    U = OrderedDict()
    for scope in SCOPES:
        ks = [k for k in A["unp"] if scope_of(k) == scope]
        o = OrderedDict(n=len(ks), issuable=sum(1 for k in ks if A["unp"][k]["kind"]
                                               == "unpriced_issuable"))
        o["not_issuable"] = o["n"] - o["issuable"]
        o["stages"] = Counter("{} {}".format(A["unp"][k]["stage"], A["unp"][k]["term"])
                              for k in ks)
        o["same"] = sum(1 for k in ks if A["unp"][k]["same"])
        o["refused_before_dispatch"] = sum(1 for k in ks if A["unp"][k]["stage"] in
                                           ("schema", "feas") and A["unp"][k]["term"] !=
                                           "applied_uncertified")
        o["extra_code"] = sum(1 for k in ks if A["unp"][k]["extra"])
        U[scope] = o
        add(scope + "Unpriced", grp(o["n"]),
            "[U] {}: reference proposals that carry a reassign_window and are not priced "
            "(refused by a check or not issuable)".format(SCOPES[scope]))
        add(scope + "UnpricedSame", grp(o["same"]),
            "[U] {}: of these, outcome on the known board and with full information identical "
            "under B and D".format(SCOPES[scope]))
    NUM["unpriced"] = U
    # self-test on a second code path (from the rows as written)
    rows = build_rows(A)
    second_path(A, rows, H, fate, chg)
    check("self-test: at least ten numbers compared", len(SELF) >= 10, len(SELF))
    check("self-test: every number equal on the second code path", all(x[3] for x in SELF),
          [x for x in SELF if not x[3]][:5])
    # adapter and frozen files after
    adapter1 = adapter_hashes()
    frozen1 = frozen_hashes()
    check("nothing under code/l1adapter/ changed during the run", adapter1 == ADAPTER0,
          (ADAPTER0, adapter1))
    check("the frozen files unchanged", frozen1 == _FROZEN0)
    write_summary(A, H, HS, fate, corr, chg, dmg, U)
    n_reused = n20.NCHECK[0] + n16.NCHECK[0] + n18.NCHECK[0] + len(n13.CHECKS)
    wall = time.time() - A["t_start"]
    md("## Runtime", "",
       "Replay {:.0f} s for {} proposals in {} (set, instance) tasks ({} worker processes on "
       "cores 8 and 9, one thread each; deterministic replays, so no number depends on the "
       "wall time); total {:.0f} s.".format(A["wall_rep"], len(rep), len(A["tasks"]), WORKERS,
                                            wall), "")
    msg = ("[n26] {} macros, {} assertions passed (+{} in the reused functions); self-test {} of "
           "{} equal; replay {:.0f}s, total {:.0f}s".format(
               len(NAMES), NCHECK[0], n_reused, sum(1 for x in SELF if x[3]), len(SELF),
               A["wall_rep"], wall))
    if A["selftest_only"]:
        dev = os.environ.get("N26_DEV_SUMMARY")       # a copy outside the project, for test runs
        if dev and not str(Path(dev).resolve()).startswith(str(ROOT)):
            Path(dev).write_text("\n".join(MD) + "\n", encoding="utf-8")
            Path(dev + ".tex").write_text("\n".join(LINES) + "\n", encoding="utf-8")
        print(msg + " (self-test mode: nothing written to the project)")
        return 0
    inputs = OrderedDict((k, input_sha256(k, p)) for k, p in IN26.items())
    for nm in ("n26_shift_keeps_due.py", "n17_heldout.py", "n20_stratum_abs.py",
               "n11_decision_time.py", "n11_forecast.py", "n8_causal.py"):
        inputs["code " + nm] = sha256_file(SCRIPTS_DIR / nm)
    MD.extend(["## Inputs", ""] + ["- {} sha256 {}".format(k, v) for k, v in inputs.items()]
              + [""])
    MD.append("{} assertions passed in n26 (plus {} in the reused functions); self-test {} of {} "
              "numbers equal on the second code path; {} macros.".format(
                  NCHECK[0], n_reused, sum(1 for x in SELF if x[3]), len(SELF), len(NAMES)))
    write_rows(rows)
    with open(OUT_REPLAY, "w", encoding="utf-8") as fh:
        for k, x in rep.items():
            fh.write(json.dumps(x, sort_keys=True) + "\n")
    OUT_ADAPTER.write_text(json.dumps({"before": ADAPTER0, "after": adapter1,
                                       "frozen_before": _FROZEN0, "frozen_after": frozen1},
                                      indent=1) + "\n", encoding="utf-8")
    NUM["macros"] = VAL
    NUM["self_test"] = [list(x) for x in SELF]
    NUM["inputs"] = inputs
    NUM["version"] = VERSION
    OUT_JSON.write_text(json.dumps(NUM, indent=1, default=str) + "\n", encoding="utf-8")
    OUT_TEX.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    shutil.copyfile(OUT_TEX, OUT_MANU)
    check("manuscript copy byte-identical", OUT_MANU.read_bytes() == OUT_TEX.read_bytes())
    OUT_MD.write_text("\n".join(MD) + "\n", encoding="utf-8")
    print(msg)
    return 0


# --------------------------------------------------------------------------- #
# Rows and the second code path                                                #
# --------------------------------------------------------------------------- #
ROW_HEAD = ["scope", "set", "item_id", "instance_id", "stratum", "primary_class", "subclass",
            "family", "op_types", "edit_type", "population", "carries_shift",
            "correct_translation", "in_no_shift_sample"]
for _cv in CONVS:
    ROW_HEAD += [h + "_" + _cv for h in (
        "k_term", "fi_term", "p_cert_k", "p_certm_k", "p_rel1_k", "p_rel2_k", "p_abs_k",
        "p_cert_fi", "lb_k", "obj_k", "obj_orig_k", "second_price_k", "second_price_fi",
        "real_wt_orig", "damage", "m_lo", "m_hi", "label020", "label010", "ref_k", "ref_fi",
        "two_k", "two_fi")]
ROW_HEAD += ["sched_diff_k", "sched_diff_fi", "sched_diff_real"]


def build_rows(A):
    rep, valsB, valsD = A["rep"], A["valsB"], A["valsD"]
    sample = set(A["sample_keys"])
    out = []

    def cst(r, d):
        if r is None:
            return ""
        c = n13.costly_of(r, d)
        return "" if c is None else c

    for scope in SCOPES:
        for r in A["recsB"][scope]:
            k = ("suite", r["item_id"]) if scope == "Suite" else (r["seed"], r["item_id"])
            st = A["stored_of"][k[0]][k[1]]
            shift = k in valsD
            corr = shift and r["primary_class"] in ("benign", "V3")
            row = OrderedDict([("scope", scope), ("set", k[0]), ("item_id", k[1]),
                               ("instance_id", r["instance_id"]), ("stratum", r["stratum"]),
                               ("primary_class", r["primary_class"]),
                               ("subclass", r.get("subclass", "")), ("family", r["family"]),
                               ("op_types", st["op_types"]), ("edit_type", r["split"]),
                               ("population", "priced_shift" if shift else "priced_no_shift"),
                               ("carries_shift", int(shift)), ("correct_translation", int(corr)),
                               ("in_no_shift_sample", int(k in sample))])
            for cv in CONVS:
                x = A["rbyB"][k] if cv == "B" else A["rbyD"].get(k)
                v = (valsB if cv == "B" else valsD).get(k)
                if v is not None:
                    bd = rep[k]["boards"][cv]
                    k_term, fi_term = bd["dt"]["term_cert"], bd["fi"]["term_cert"]
                    lb, obj, objo = bd["dt"]["lb"], bd["dt"]["obj"], bd["dt"]["obj_orig"]
                    rwo = v["rw_obj_orig"]
                else:
                    k_term = st["dt_term_cert"]
                    fi_term = (A["SU"]["fi"][k[1]] if k[0] == "suite"
                               else A["NE"]["fi"][k[0]][k[1]])["p"]["term_cert"]
                    lb, obj, objo, rwo = st["dt_lb"], st["dt_obj"], st["dt_obj_orig"], \
                        st["rw_obj_orig"]
                row["k_term_" + cv] = k_term
                row["fi_term_" + cv] = fi_term
                for g, col in (("G-CERT", "p_cert_k"), ("G-CERT-M", "p_certm_k"),
                               ("D-REL1", "p_rel1_k"), ("D-REL2", "p_rel2_k"),
                               ("D-ABS", "p_abs_k")):
                    row[col + "_" + cv] = fx(x["p_" + g])
                row["p_cert_fi_" + cv] = fx(x["fi"]["p_G-CERT"])
                row["lb_k_" + cv] = fx(lb)
                row["obj_k_" + cv] = fx(obj)
                row["obj_orig_k_" + cv] = fx(objo)
                row["second_price_k_" + cv] = fx(x["g_orig"])
                row["second_price_fi_" + cv] = fx(x["sp_fi"])
                row["real_wt_orig_" + cv] = fx(rwo)
                row["damage_" + cv] = fx(x["dmg"])
                row["m_lo_" + cv] = fx(x["lo"])
                row["m_hi_" + cv] = fx(x["hi"])
                row["label020_" + cv] = cst(x, 0.20)
                row["label010_" + cv] = cst(x, 0.10)
                row["ref_k_" + cv] = b01(x["ref_k"])
                row["ref_fi_" + cv] = b01(x["ref_f"])
                row["two_k_" + cv] = b01(x["two_k"])
                row["two_fi_" + cv] = b01(x["two_f"])
            for bk, col in (("dt", "sched_diff_k"), ("fi", "sched_diff_fi"),
                            ("rw", "sched_diff_real")):
                row[col] = (int(rep[k]["boards"]["B"][bk]["digest"]
                                != rep[k]["boards"]["D"][bk]["digest"]) if shift else 0)
            out.append(row)
    for k, u in A["unp"].items():
        it = A["items_of"][k[0]][k[1]]
        st = A["stored_of"][k[0]][k[1]]
        row = OrderedDict((h, "") for h in ROW_HEAD)
        row.update(scope=scope_of(k), set=k[0], item_id=k[1],
                   instance_id=it["instance"]["instance_id"], stratum=it["instance"]["stratum"],
                   primary_class=it["primary_class"], subclass=it["subclass"],
                   family=it["family_id"], op_types=st["op_types"], edit_type=st["split"],
                   population=u["kind"], carries_shift=1,
                   correct_translation=int(it["primary_class"] in ("benign", "V3")),
                   in_no_shift_sample=0, k_term_B=u["term"], k_term_D=u["d_term"],
                   fi_term_B=u["fi_term"], fi_term_D=u["d_fi_term"])
        out.append(row)
    for row in out:
        check("row carries every column", list(row.keys()) == ROW_HEAD, list(row.keys())[:5])
    return out


def write_rows(rows):
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        fh.write("# N26 ({}): one row per priced proposal of the direct benchmark (suite 1,356; "
                 "three new draws 3,733 held-out) and per unpriced reference proposal with a "
                 "reassign_window; _B = benchmark convention (the shift moves the release and the "
                 "due date), _D = the shift moves the release only; proposals without a "
                 "reassign_window keep their B values under D; k = known board at t_d, fi = "
                 "full-information board, real = realised whole-window run; p_<design> = price "
                 "on the board's own bound; label: 1 costly, 0 low-cost, empty undecided; "
                 "sched_diff = canonical schedule differs between B and D\n".format(VERSION))
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(ROW_HEAD)
        for row in rows:
            w.writerow([row[h] for h in ROW_HEAD])


def second_path(A, rows, H, fate, chg):
    """Headline numbers recomputed from the rows with a label rule, flags and a bootstrap
    written here."""
    pr = [x for x in rows if x["population"].startswith("priced")]

    def f(s):
        return None if s == "" else float(s)

    def label(x, cv, d):
        lo, hi = f(x["m_lo_" + cv]), f(x["m_hi_" + cv])
        if lo is None or hi is None:
            return None
        return 1 if lo > d else (0 if hi <= d else None)

    def ref_k(x, cv):
        p = f(x["p_cert_k_" + cv])
        return p is not None and p > 0.20

    def ref_f(x, cv):
        p = f(x["p_cert_fi_" + cv])
        return True if p is None else p > 0.20

    def two_k(x, cv):
        sp = f(x["second_price_k_" + cv])
        return ref_k(x, cv) or (x["edit_type"] == "field_changing" and sp is not None
                                and sp > 0.20)

    for scope in SCOPES:
        sel = [x for x in pr if x["scope"] == scope]
        for cv in CONVS:
            for dtok, d in DELTAS.items():
                c = [x for x in sel if label(x, cv, d) == 1]
                lw = [x for x in sel if label(x, cv, d) == 0]
                h = H[(scope, cv)][dtok]
                pairs = [("costly", len(c), h["costly"]), ("low", len(lw), h["low"]),
                         ("ref_k", sum(ref_k(x, cv) for x in c), h["ref_k"]),
                         ("ref_f", sum(ref_f(x, cv) for x in c), h["ref_f"]),
                         ("app_k", sum(not ref_k(x, cv) for x in c), h["app_k"]),
                         ("two_app_k", sum(not two_k(x, cv) for x in c), h["two_app_k"]),
                         ("low_ref_k", sum(ref_k(x, cv) for x in lw), h["low_ref_k"]),
                         ("low_two_k", sum(two_k(x, cv) for x in lw), h["low_two_k"])]
                for nm, a, b in pairs:
                    SELF.append(("headline", "{} {} {} {}".format(scope, cv, dtok, nm), b, a == b))
                if dtok == "DeltaTwenty":
                    lo, hi = boot_ci_here([x["instance_id"] for x in lw],
                                          [ref_k(x, cv) for x in lw],
                                          {x["instance_id"] for x in pr})
                    SELF.append(("bootstrap", "{} {} low-cost share K interval".format(scope, cv),
                                 (pctv(h["lr_lo"]), pctv(h["lr_hi"])),
                                 (pctv(lo), pctv(hi)) == (pctv(h["lr_lo"]), pctv(h["lr_hi"]))))
        # item 5 from the rows
        m = [x for x in sel if label(x, "B", 0.20) == 1 and not ref_k(x, "B")]
        o = fate[(scope, "All")]
        for nm, a, b in (("n", len(m), o["n"]),
                         ("still costly under D", sum(label(x, "D", 0.20) == 1 for x in m),
                          o["costly"]),
                         ("referred on K under D", sum(ref_k(x, "D") for x in m), o["ref_k"]),
                         ("referred with second price under D", sum(two_k(x, "D") for x in m),
                          o["two_k"])):
            SELF.append(("fate", "{} {}".format(scope, nm), b, a == b))
        # item 7 from the rows
        sh = [x for x in sel if x["carries_shift"] == 1]
        a = sum(1 for x in sh if label(x, "B", 0.20) == 0 and label(x, "D", 0.20) == 1)
        b = chg[scope]["DeltaTwenty"]["low_to_costly"]
        SELF.append(("labels", "{} low-cost to costly at 0.20".format(scope), b, a == b))
        a = sum(1 for x in sh if label(x, "B", 0.20) == 1 and label(x, "D", 0.20) == 0)
        b = chg[scope]["DeltaTwenty"]["costly_to_low"]
        SELF.append(("labels", "{} costly to low-cost at 0.20".format(scope), b, a == b))
        a = sum(int(x["sched_diff_k"]) for x in sh)
        SELF.append(("schedules", "{} known boards that differ".format(scope),
                     chg[scope]["sched_diff_K"], a == chg[scope]["sched_diff_K"]))


# --------------------------------------------------------------------------- #
# Summary                                                                      #
# --------------------------------------------------------------------------- #
def write_summary(A, H, HS, fate, corr, chg, dmg, U):
    head = ["# N26: the direct benchmark when a time-window shift keeps the due date "
            "({})".format(VERSION), "",
            "Generated by `code/scripts/n26_shift_keeps_due.py` on cores 8 and 9 (one thread per "
            "process): deterministic dispatcher replays (n11_decision_time.gen_price, no solver, "
            "no time budget), no model call, no GPU. Post hoc sensitivity analysis. Frozen "
            "design: `results/n26_shift_keeps_due/design.md` (sha256 {}), addendum "
            "`results/n26_shift_keeps_due/addendum.md`.".format(DESIGN_SHA), "",
            "Convention B is the benchmark: `reassign_window` moves the release and the due date "
            "(the SLA clock restarts). Convention D moves the release only and keeps the due "
            "date. Everything else is unchanged. K = known board at t_d, FI = full-information "
            "board at t_d, realised = the whole-window run from t_d. Certificate at tau = 0.20 "
            "on the board's own bound (LB2 on the fields the guard is given). Second price on "
            "field edits: (objective on the original values minus the no-proposal bound) over "
            "that bound, above 0.20. bh = business hours.", "",
            "## B. Self-check (before any D number)", "",
            "From the stored records (suite: n20.build; new draws: n17_heldout.build_records on "
            "the stored replays, the held-out rows of analysis/N17_rows.csv): suite 1,356 "
            "priced; at 0.20, 186 costly, 1,170 low-cost, 168 referred on K and the same 168 "
            "with FI, 18 applied, 0 applied with the second price, 15 and 22 low-cost "
            "referred; at 0.10, 208 costly, 25 applied on K, 28 with FI, 6 with the second "
            "price. New draws: 3,733 priced; at 0.20, 529 costly, 3,204 low-cost, 45 applied, 4 "
            "with the second price, 65 and 98 low-cost referred, shares and intervals equal to "
            "the N17 macros. All asserted.", "",
            "The B replay of every shift proposal reproduces its stored values on K, FI and the "
            "realised run (see section 1). Largest differences: " + "; ".join(
                "{} {:.1e}".format(k, v) for k, v in sorted(MAXDIFF.items(), key=lambda t: -t[1])
                [:6]) + ".", ""]
    MD[:0] = head
    md("## 1. Checks (all run-fatal, all passed)", "",
       "- Frozen files: {} (sha256 prefixes, before and after the run). Every .py file under "
       "code/l1adapter/ has the same sha256 before and after the run.".format(", ".join(
           "{} {}".format(k, _FROZEN0[k][:12]) for k in FROZEN)),
       "- Probes (a), (b), (c) pass (block P).",
       "- B replay of the {} priced shift proposals (suite {}, new draws {}): terminals, codes, "
       "both objectives, bound, certificate and D-REL2 reference on K; every field of the "
       "stored full-information record on FI; terminals and both objectives on the realised "
       "run; damage, realised-cost interval, labels at 0.20 and 0.10, every design's price and "
       "flag on K and FI, the second price on K and FI equal the stored records.".format(
           len(A["valsB"]), sum(1 for k in A["valsB"] if k[0] == "suite"),
           sum(1 for k in A["valsB"] if k[0] != "suite")),
       "- The patched function with the switch off (Boff) gives the unpatched known-board "
       "schedule byte for byte on {} sampled shift proposals.".format(len(A["boff_keys"])),
       "- {} sampled priced proposals without a shift: D equals B byte for byte on all three "
       "boards, and B equals the stored totals.".format(SAMPLE_N),
       "- Under D: no instrument fault, every schedule complete, each shifted order's due date "
       "equals its due date before the operation and its release equals the B release, and "
       "the schema and feasibility outcome on K equals B's. {} shift proposals lose their price "
       "on K under D.".format(len(A["not_priced_D"])), "")
    md("## 2. Headline, B beside D (items 1 to 4)", "")
    for scope in SCOPES:
        for dtok, delta in DELTAS.items():
            md("### {}, delta = {:.2f}".format(SCOPES[scope], delta), "")
            md_table(["convention"] + HL_HEAD,
                     [[cv] + hl_cells(H[(scope, cv)], dtok) for cv in CONVS])
    md("### New draws per seed, delta = 0.20", "")
    body = []
    for seed in SEEDS:
        for cv in CONVS:
            body.append([seed, cv] + hl_cells(HS[(seed, cv)], "DeltaTwenty"))
    md_table(["seed", "convention"] + HL_HEAD, body)
    md("## 3. The costly proposals the certificate applies under B at delta = tau = 0.20 "
       "(item 5)", "",
       "Under D: label at 0.20, certificate on K and with FI, and the second price. The "
       "priority edits carry no shift, so their D values equal B by construction.", "")
    body = []
    for (scope, fam_tok), o in fate.items():
        body.append([scope, fam_tok, o["n"], o["costly"], o["low"], o["und"], o["ref_k"],
                     o["ref_f"], o["two_k"], o["two_f"], o["costly_app_k"], o["costly_app_f"],
                     o["costly_two_app_k"], o["costly_two_app_f"]])
    md_table(["scope", "family", "applied costly under B", "still costly (D)", "low-cost (D)",
              "undecided (D)", "referred K (D)", "referred FI (D)", "referred K, second price "
              "(D)", "referred FI, second price (D)", "still costly and applied K (D)",
              "still costly and applied FI (D)", "still costly, applied with second price K (D)",
              "still costly, applied with second price FI (D)"], body)
    for scope in SCOPES:
        body = []
        for k, r, x in fate[(scope, "All")]["rows"]:
            vb = A["valsB"].get(k)
            if vb is not None:
                kb, kd = A["rep"][k]["boards"]["B"]["dt"], A["rep"][k]["boards"]["D"]["dt"]
                ol = "{} / {}; {} / {}".format(bh1(kb["obj"]), bh1(kd["obj"]), bh1(kb["lb"]),
                                               bh1(kd["lb"]))
            else:
                st = A["stored_of"][k[0]][k[1]]
                ol = "{} / same; {} / same".format(bh1(st["dt_obj"]), bh1(st["dt_lb"]))
            body.append(["{}:{}".format(*k) if k[0] != "suite" else k[1], r["family"], ol,
                         bh2(r["p_G-CERT"]), bh2(x["p_G-CERT"]), bh2(r["fi"]["p_G-CERT"]),
                         bh2(x["fi"]["p_G-CERT"]), bh2(r["g_orig"]), bh2(x["g_orig"]),
                         bh1(r["dmg"]), bh1(x["dmg"]),
                         "{:.3f}-{:.3f}".format(r["lo"], r["hi"]),
                         "n/a" if x["lo"] is None else "{:.3f}-{:.3f}".format(x["lo"], x["hi"]),
                         lbl(n13.costly_of(x, 0.20)),
                         "referred" if x["ref_k"] else "applied",
                         "referred" if x["two_k"] else "applied",
                         "yes" if vb is not None else "no"])
        md("### {}: each applied costly proposal".format(SCOPES[scope]), "")
        md_table(["proposal", "family", "K objective B / D; K bound B / D (bh)", "cert K (B)",
                  "cert K (D)", "cert FI (B)", "cert FI (D)",
                  "second price K (B)", "second price K (D)", "damage bh (B)", "damage bh (D)",
                  "realised cost (B)", "realised cost (D)", "label 0.20 (D)", "certificate K "
                  "(D)", "second price K (D)", "replayed"], body)
    md("## 4. Correct translations that carry a shift (item 6)", "",
       "Classes benign and V3 (their reference proposal is the recorded reading), priced, with "
       "a reassign_window. Referred = by the certificate; 'of which low-cost' = referred and "
       "low-cost at that delta.", "")
    for dtok, delta in DELTAS.items():
        body = []
        for scope in SCOPES:
            for ctok in ("All", "Benign", "VThree"):
                for cv in CONVS:
                    o = corr[(scope, ctok, cv)]
                    x = o[dtok]
                    body.append([scope, ctok, cv, o["priced"], x["costly"], x["low"],
                                 "{} ({})".format(x["ref_k"], x["ref_k_low"]),
                                 "{} ({})".format(x["ref_f"], x["ref_f_low"]),
                                 "{} ({})".format(x["two_k"], x["two_k_low"])])
        md("### delta = {:.2f}".format(delta), "")
        md_table(["scope", "class", "convention", "priced", "costly", "low-cost",
                  "referred K (of which low-cost)", "referred FI (of which low-cost)",
                  "referred K with second price (of which low-cost)"], body)
    md("## 5. Label, schedule and damage changes of the shift proposals (item 7)", "")
    body = []
    for scope in SCOPES:
        o = chg[scope]
        for dtok, delta in DELTAS.items():
            x = o[dtok]
            body.append([scope, "{:.2f}".format(delta), o["shift"], x["low_to_costly"],
                         x["costly_to_low"], x["to_und"], x["from_und"]])
    md_table(["scope", "delta", "shift proposals", "low-cost -> costly", "costly -> low-cost",
              "decided -> undecided", "undecided -> decided"], body)
    for scope in SCOPES:
        for dtok in DELTAS:
            for k, v in chg[scope][dtok]["lists"].items():
                md("- {} {} {}: {}".format(scope, dtok, k, ", ".join(v)))
    md("")
    body = [[scope, chg[scope]["shift"], chg[scope]["sched_diff_K"], chg[scope]["sched_diff_FI"],
             chg[scope]["sched_diff_Real"], chg[scope]["k_price_up"], chg[scope]["k_price_down"],
             "{} / {}".format(chg[scope]["ref_k_on"], chg[scope]["ref_k_off"]),
             "{} / {}".format(chg[scope]["ref_f_on"], chg[scope]["ref_f_off"]),
             "{} / {}".format(chg[scope]["two_k_on"], chg[scope]["two_k_off"])]
            for scope in SCOPES]
    md_table(["scope", "shift proposals", "K schedules differ", "FI schedules differ",
              "realised schedules differ", "cert price K higher under D", "lower under D",
              "certificate K: newly referred / newly applied",
              "certificate FI: newly referred / newly applied",
              "second price K: newly referred / newly applied"], body)
    md("Shift proposals whose label at 0.20 or 0.10, or whose disposition (certificate on K or "
       "with FI, second price on K or with FI), differs between B and D:", "")
    body = []
    for k in A["shift_keys"]:
        rb, rd = A["rbyB"][k], A["rbyD"][k]
        moved = (any(n13.costly_of(rb, d) != n13.costly_of(rd, d) for d in DELTAS.values())
                 or any(rb[f] != rd[f] for f in ("ref_k", "ref_f", "two_k", "two_f")))
        if not moved:
            continue

        def disp(r):
            return "/".join("R" if r[f] else "A" for f in ("ref_k", "ref_f", "two_k", "two_f"))

        body.append(["{}:{}".format(*k) if k[0] != "suite" else k[1], rb["primary_class"],
                     rb["family"], "{} -> {}".format(lbl(n13.costly_of(rb, 0.20)),
                                                     lbl(n13.costly_of(rd, 0.20))),
                     "{} -> {}".format(lbl(n13.costly_of(rb, 0.10)),
                                       lbl(n13.costly_of(rd, 0.10))),
                     "{:.3f} -> {:.3f}".format(rb["hi"], rd["hi"]),
                     "{:.3f} -> {:.3f}".format(rb["p_G-CERT"], rd["p_G-CERT"]),
                     "{:.3f} -> {:.3f}".format(rb["fi"]["p_G-CERT"], rd["fi"]["p_G-CERT"]),
                     "{:.3f} -> {:.3f}".format(rb["g_orig"], rd["g_orig"]),
                     "{} -> {}".format(disp(rb), disp(rd))])
    md_table(["proposal", "class", "family", "label 0.20", "label 0.10",
              "realised cost (upper end)", "cert K", "cert FI", "second price K",
              "disposition K / FI / second price K / second price FI (R referred, A applied)"],
             body)
    body = [[scope, dmg[scope]["n"], bh2(dmg[scope]["median"]), bh2(dmg[scope]["p10"]),
             bh2(dmg[scope]["p90"]), "{} ({})".format(bh2(dmg[scope]["min"]),
                                                      dmg[scope]["argmin"]),
             "{} ({})".format(bh2(dmg[scope]["max"]), dmg[scope]["argmax"]),
             dmg[scope]["lower"], dmg[scope]["equal"], dmg[scope]["higher"]]
            for scope in SCOPES]
    md("Realised damage, D minus B, weighted bh:", "")
    md_table(["scope", "n", "median", "p10", "p90", "min", "max", "lower under D", "equal",
              "higher under D"], body)
    md("## 6. Unpriced reference proposals with a reassign_window", "")
    body = []
    for scope in SCOPES:
        o = U[scope]
        body.append([scope, o["n"], o["issuable"], o["not_issuable"],
                     "; ".join("{} {}".format(k, v) for k, v in sorted(o["stages"].items())),
                     o["same"], o["extra_code"]])
    md_table(["scope", "unpriced", "issuable", "not issuable", "stage and terminal under B (K)",
              "identical under B and D (K and FI)", "with the running-work code beyond the "
              "stored ones"], body)
    md("## 7. Self-test (second code path)", "",
       "Counts recomputed from the rows of analysis/N26_rows.csv as written, with a label rule "
       "(lower end above delta: costly; upper end at most delta: low-cost), the flags "
       "(price above 0.20; FI refused counts as referred; second price on field edits) and a "
       "bootstrap written in the script.", "")
    md_table(["block", "number", "value", "equal"],
             [[a, b, c, "yes" if d else "NO"] for a, b, c, d in SELF])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
