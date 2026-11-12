#!/usr/bin/env python3
"""N27b: the gate priced on a known board from which unstarted orders, planned or corrective, are withheld.

Designs: the pre-specified design of N27 and its extension to planned
orders.  Frozen designs: results/n27_withheld_orders/design.md (N27) and
results/n27_withheld_orders/design_n27b_2026-11-11.md (this variant), both sha256 asserted
before anything else; later choices: results/n27_withheld_orders/addendum_n27b.md.

N27 withheld only unstarted corrective orders, and the known board is mostly the planned
maintenance calendar, so its candidate set was small.  This variant prices the same proposals
on K minus a share f of H2 = every unstarted order of K (queued, or planned on the calendar),
named neither by the instruction nor by the proposal, not in the standing frozen set, planned
and corrective alike, for f in {0.25, 0.50, 0.75, 1.00}, five random draws per level below 1
and one at 1.  It departs from the benchmark's premise that the maintenance calendar is known:
it stresses the information the gate is given and makes no claim about a site.  The labels
stay the stored ones.  f = 0 is the benchmark's known board and is the self-check.

Steps (every assertion is run-fatal):
  0  frozen-file prefixes, both designs' sha256, the sha256 of every .py file under
     code/l1adapter/ (again at the end); n16.section0, n18.section0 and n20.section0 on
     n20.build's records; the frozen counts and N18's later share of the costly proposals;
  P  a probe on a micro-instance: withholding removes exactly the drawn orders from the board
     and leaves everything else unchanged; queued and calendar planned orders and unnamed
     queued corrective orders are candidates, named, running and frozen orders are not;
  R  replay of every priced proposal on K and on each thinned board (two worker processes):
     n11_decision_time.gen_price for the proposal and for the no-proposal run on the same
     board;
  Z  f = 0 tied to the stored census, prices and flags of every design for all 1,356, and to
     N27's f = 0 rows;
  T  the tables of the design (items 1 to 6), the figure data, the rows, the self-test.

Reuse: n20_stratum_abs loaded from its source with its core allowance set to cores 8 and 9 in
memory (file untouched), and through it n16, n18 and n13: n20.build's records, n13.costly_of,
n16.sp_flag's rule, n2.Boot (seed 20261026, 20,000 replicates, 60 instance clusters).

Outputs: analysis/N27b_macros.tex (prefix \\nTwentySevenAll, one comment line per macro),
copied to manuscript/macros_n27b.tex; analysis/N27b_rows.csv; analysis/N27b_numbers.json;
analysis/N27b_summary.md; analysis/N27b_fig_data.csv; results/n27_withheld_orders/
replay_n27b.jsonl and l1adapter_sha256_n27b.json.
Run:       OMP_NUM_THREADS=1 taskset -c 8,9 python -B code/scripts/n27b_withheld_all.py
Self-test: the same with --selftest: every computation and assertion, writes nothing.
Rebuild:   the same with --from-stored: every output rebuilt from the stored replay of the
           official run (results/n27_withheld_orders/replay_n27b.jsonl), no new replay.
Version: l1-n27b-withheld-all-1
"""
import os
import sys

sys.dont_write_bytecode = True
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_v] = "1"

import csv  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import random  # noqa: E402
import shutil  # noqa: E402
import statistics  # noqa: E402
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

VERSION = "l1-n27b-withheld-all-1"
OUT_DIR = ROOT / "results" / "n27_withheld_orders"
DESIGN = OUT_DIR / "design.md"
DESIGN_SHA_FILE = OUT_DIR / "design.sha256"
ADDENDUM = OUT_DIR / "addendum_n27b.md"
DESIGN_B = OUT_DIR / "design_n27b_2026-11-11.md"
DESIGN_B_SHA_FILE = OUT_DIR / "design_n27b_2026-11-11.sha256"
DESIGN_B_SHA = "18b8dc72ef98f4d42045bf32af6ebfa606398e896ada81eb0348a1d80baa5c96"
DESIGN_SHA = "db71daa42aa711e888c55a1434ae8cfc2d221e232b2ed7295bcca5ece0734625"
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
        raise SystemExit("[n27b] frozen file {} has sha256 {} (expected prefix {})".format(
            _k, _FROZEN0[_k], _pre))
_dsha = sha256_file(DESIGN)
if _dsha != DESIGN_SHA or DESIGN_SHA_FILE.read_text().split()[0] != DESIGN_SHA:
    raise SystemExit("[n27b] design.md sha256 {} differs from the recorded {}".format(
        _dsha, DESIGN_SHA))
_dsha_b = sha256_file(DESIGN_B)
if _dsha_b != DESIGN_B_SHA or DESIGN_B_SHA_FILE.read_text().split()[0] != DESIGN_B_SHA:
    raise SystemExit("[n27b] design_n27b sha256 {} differs from the recorded {}".format(
        _dsha_b, DESIGN_B_SHA))
if not ADDENDUM.is_file():
    raise SystemExit("[n27b] missing addendum " + str(ADDENDUM))
ADAPTER0 = adapter_hashes()


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
np = n13.np
n2 = n13.n2
import n8_causal as n8  # noqa: E402
from l1adapter import apply as apply_mod  # noqa: E402
from l1adapter import dispatch as dispatch_mod  # noqa: E402
from l1guard.config import G_CERT  # noqa: E402
from l1guard.verdict import certified_gap  # noqa: E402

ANALYSIS = ROOT / "analysis"
OUT_TEX = ANALYSIS / "N27b_macros.tex"
OUT_MANU = ROOT / "manuscript" / "macros_n27b.tex"
OUT_MD = ANALYSIS / "N27b_summary.md"
OUT_CSV = ANALYSIS / "N27b_rows.csv"
OUT_JSON = ANALYSIS / "N27b_numbers.json"
OUT_FIG = ANALYSIS / "N27b_fig_data.csv"
OUT_REPLAY = OUT_DIR / "replay_n27b.jsonl"
OUT_ADAPTER = OUT_DIR / "l1adapter_sha256_n27b.json"
IN27B = OrderedDict([
    ("brief", ROOT / "design_notes" / "N27_design.md"),
    ("design", DESIGN), ("design_n27b", DESIGN_B), ("addendum_n27b", ADDENDUM),
    ("n27_rows", ANALYSIS / "N27_rows.csv"),
    ("n18_macros", ANALYSIS / "N18_macros.tex"), ("n15_macros", ANALYSIS / "N15_macros.tex"),
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
TOL = 1e-9
CSV_TOL = 1e-6
WORKERS = 2
LEVELS = OrderedDict([("FZero", 0.0), ("FQuarter", 0.25), ("FHalf", 0.50),
                      ("FThreeQuarters", 0.75), ("FOne", 1.00)])
NDRAWS = {0.0: 1, 0.25: 5, 0.50: 5, 0.75: 5, 1.00: 1}
DELTAS = OrderedDict([("DeltaTwenty", 0.20), ("DeltaTen", 0.10)])
DESIGNS = n13.DESIGNS                      # G-CERT, G-CERT-M, D-REL1, D-REL2, D-ABS
SETTINGS = n13.SETTINGS
GATES = OrderedDict([("Cert", "the certificate (G-CERT, tau 0.20)"),
                     ("CertSP", "the certificate with the second price on field edits"),
                     ("CertM", "the marginal certificate (G-CERT-M, 0.20)"),
                     ("RelOne", "D-REL1 (0.02)"), ("RelTwo", "D-REL2 (0.02)"),
                     ("Abs", "D-ABS (0.8119 weighted bh)")])
GATE_DESIGN = {"Cert": "G-CERT", "CertM": "G-CERT-M", "RelOne": "D-REL1", "RelTwo": "D-REL2",
               "Abs": "D-ABS"}
MAIN_GATES = ("Cert", "CertSP")
BANDS = OrderedDict([("UpToTen", (None, 0.10, "up to 10%")), ("TenToTwentyFive",
                                                              (0.10, 0.25, "10 to 25%")),
                     ("TwentyFiveToFifty", (0.25, 0.50, "25 to 50%")),
                     ("AboveFifty", (0.50, None, "above 50%"))])
EDIT_TOK = OrderedDict([("sequencing_only", "Seq"), ("field_changing", "Field"),
                        ("empty", "Empty"), ("other", "Other")])

LINES = ["% N27b macros ({}); generated by code/scripts/n27b_withheld_all.py from deterministic "
         "replays of the direct benchmark's known-board pricing on boards from which a share f "
         "of the unstarted, unnamed, unfrozen orders, planned or corrective, is withheld; labels "
         "unchanged. Post hoc stress on the gate's information, departing from the benchmark's "
         "premise that the maintenance calendar is known; designs: results/n27_withheld_orders/"
         "design.md and design_n27b_2026-11-11.md.".format(VERSION)]
NAMES = set()
VAL = OrderedDict()
MD = []
NCHECK = [0]
SELF = []
MAXDIFF = defaultdict(float)
NUM = OrderedDict()

grp, pctv, pctpv = n16.grp, n16.pctv, n16.pctpv


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def check(what, ok, detail=""):
    if not ok:
        raise SystemExit("[n27b] ASSERTION FAILED: {} ({})".format(what, str(detail)[:900]))
    NCHECK[0] += 1


def close(what, a, b, tol, key=""):
    if a is None or b is None:
        check(what + " (both missing)", a is None and b is None, (key, a, b))
        return
    d = abs(float(a) - float(b))
    MAXDIFF[what] = max(MAXDIFF[what], d)
    check(what, d <= tol, (key, a, b, d))


def add(name, value, note):
    full = "nTwentySevenAll" + name
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


def say(msg):
    print("[n27b] " + msg, flush=True)


def m1(x):
    return "n/a" if x is None else "{:.1f}".format(x)


def p3(x):
    return "n/a" if x is None else "{:.3f}".format(x)


def fx(x):
    if x is None:
        return ""
    return repr(float(x))


def b01(x):
    return "" if x is None else int(bool(x))


def pct1(x):
    return "n/a" if x is None else "{:.1f}%".format(100.0 * x)


def quart(xs):
    a = np.asarray(xs, dtype=float)
    q1, med, q3 = (float(v) for v in np.percentile(a, [25, 50, 75]))
    return OrderedDict(n=len(xs), q1=q1, median=med, q3=q3, max=float(a.max()),
                       min=float(a.min()), mean=float(a.mean()))


def jsonable(x):
    """Dictionary keys as strings (tuples joined by spaces), for the numbers file."""
    if isinstance(x, dict):
        return OrderedDict((" ".join(str(y) for y in k) if isinstance(k, tuple) else
                            (k if isinstance(k, str) else str(k)), jsonable(v))
                           for k, v in x.items())
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if isinstance(x, set):
        return sorted(jsonable(v) for v in x)
    return x


def sched_digest(s):
    return hashlib.sha256(dispatch_mod.canonical_schedule_json(s).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Withholding                                                                  #
# --------------------------------------------------------------------------- #
def candidates(known, state, kf, ops, referenced, instance):
    """H2: unstarted (queued or on the calendar), unnamed, not frozen orders of the known board,
    planned and corrective alike."""
    by = {w["id"]: w for w in known["work_orders"]}
    explicit, members = n8.named_orders(ops, instance)
    named = set(explicit) | set(members) | set((referenced or {}).get("order_ids") or [])
    kfs = set(kf)
    return sorted(o for o in list(state["queue"]) + list(state["scheduled"])
                  if o in by and o not in named and o not in kfs)


def n_withheld(f, n_h):
    return int(math.floor(f * n_h + 0.5))


def withheld_of(item_id, f, draw, H):
    k = n_withheld(f, len(H))
    if k == 0:
        return []
    seed = int(hashlib.sha256("all|{}|{:.2f}|{}".format(item_id, f, draw).encode("utf-8"))
               .hexdigest()[:16], 16)
    return sorted(random.Random(seed).sample(sorted(H), k))


def board_key(withheld):
    """The empty string for K itself, otherwise a digest of the sorted withheld ids."""
    if not withheld:
        return ""
    return hashlib.sha256("|".join(sorted(withheld)).encode("utf-8")).hexdigest()[:24]


def thinned(known, withheld):
    w = set(withheld)
    out = {k: v for k, v in known.items() if k != "work_orders"}
    out["work_orders"] = [wo for wo in known["work_orders"] if wo["id"] not in w]
    return out


# --------------------------------------------------------------------------- #
# P. Probe on a micro-instance                                                 #
# --------------------------------------------------------------------------- #
def block_p():
    from l1adapter import SLA_BH, WEIGHT

    def o_(oid, trade, p_bh, release_bh=0.0, priority=3, pm=False):
        return {"id": oid, "trade": trade, "p_bh": float(p_bh), "release_bh": float(release_bh),
                "due_bh": round(float(release_bh) + SLA_BH[priority], 4),
                "priority": priority, "weight": float(WEIGHT[priority]), "building": None,
                "is_pm": pm}
    orders = [o_("R", "D20", 4.0), o_("P", "D20", 1.0, pm=True), o_("N", "D20", 2.0),
              o_("I", "D20", 2.0), o_("F", "D20", 1.0), o_("C1", "D20", 1.0),
              o_("C2", "D20", 3.0), o_("C3", "D20", 2.0), o_("S", "D20", 1.0, release_bh=9.0,
                                                               pm=True),
              o_("G", "D20", 1.0, release_bh=9.5, pm=True), o_("U", "D20", 1.0, release_bh=9.0)]
    inst = {"meta": {"id": "n27b-probe", "campus": 0, "track": "micro", "size_class": len(orders),
                     "window_start": "synthetic", "window_bh": 0.0, "provenance": "T",
                     "seed": None},
            "trades": ["D20"], "technicians": [{"id": "T0", "trade": "D20"},
                                               {"id": "T1", "trade": "D20"}],
            "work_orders": orders}
    # R is running, P is a queued planned order, N is named by the proposal, I by the
    # instruction, F is a frozen queued order, C1-C3 are unnamed queued corrective orders, S is a
    # planned order on the calendar, G a frozen planned order on the calendar, U arrives later
    # (not on the known board)
    state = {"completed": [], "in_progress": ["R"], "queue": ["P", "N", "I", "F", "C1", "C2",
                                                            "C3"],
             "scheduled": ["S", "G"], "unknown": ["U"]}
    known = n8.known_instance(inst, state)
    k_ids = ["R", "P", "N", "I", "F", "C1", "C2", "C3", "S", "G"]
    check("probe: the known board holds the queued, running and scheduled orders",
          [w["id"] for w in known["work_orders"]] == k_ids)
    kf = D.kf_fix(state, ["F", "G"])
    check("probe: the frozen set holds the running order and the seed orders on K",
          sorted(kf) == ["F", "G", "R"], kf)
    ops = [{"op": "set_priority", "order_id": "N", "priority_class": 1}]
    H = candidates(known, state, kf, ops, {"order_ids": ["I"]}, inst)
    check("probe: H2 holds the unnamed, unstarted, unfrozen orders, planned and corrective",
          H == ["C1", "C2", "C3", "P", "S"], H)
    counts = {f: n_withheld(f, len(H)) for f in LEVELS.values()}
    check("probe: withheld counts at |H2| = 5 are 0, 1, 3, 4, 5", [counts[f] for f in
                                                                    LEVELS.values()]
          == [0, 1, 3, 4, 5], counts)
    w = withheld_of("PROBE", 0.50, 0, H)
    check("probe: the draw is reproducible", w == withheld_of("PROBE", 0.50, 0, H) and len(w) == 3)
    check("probe: f = 1 withholds H2", withheld_of("PROBE", 1.0, 0, H) == H)
    b = thinned(known, w)
    kept = [wo for wo in known["work_orders"] if wo["id"] not in set(w)]
    check("probe: the thinned board is the known board without exactly the withheld orders",
          b["work_orders"] == kept and len(b["work_orders"]) == len(known["work_orders"]) - 3)
    check("probe: technicians, trades and meta unchanged",
          all(b[k] == known[k] for k in known if k != "work_orders"))
    check("probe: named, running and frozen orders stay on the board",
          {"R", "N", "I", "F", "G"} <= {x["id"] for x in b["work_orders"]})
    bf = thinned(known, H)
    check("probe: at f = 1 the board holds exactly the running, named and frozen orders",
          [x["id"] for x in bf["work_orders"]] == ["R", "N", "I", "F", "G"])
    check("probe: the known board itself is not modified",
          [x["id"] for x in known["work_orders"]] == k_ids)
    for brd, wh in ((b, w), (bf, H)):
        adj = apply_mod.apply_operations(brd, [])
        sch = dispatch_mod.dispatch_adjusted(adj, "atc", 0)
        got = {a["wo"] for a in sch["assignments"]}
        check("probe: the dispatched thinned board schedules every kept order and no withheld "
              "one", got == {x["id"] for x in brd["work_orders"]} and not (got & set(wh)), got)
    add("ProbeCandidates", len(H), "[P] probe: candidates on the micro board (of 10 known "
        "orders: one running, three planned of which one frozen, one named by the proposal, one "
        "by the instruction, one frozen corrective, three unnamed queued corrective orders)")
    md("## P. Probe (in memory, before any replay)", "",
       "A micro board with a running order R, a queued planned order P, two planned orders on "
       "the calendar S and G (G frozen), an order N named by the proposal, an order I named by "
       "the instruction, a frozen queued order F and three unnamed queued corrective orders C1 "
       "to C3 (U arrives later and is not on the known board). H2 = {C1, C2, C3, P, S}. At "
       "|H2| = 5 the levels withhold 0, 1, 3, 4 and 5 orders, and the draw at f = 0.50 "
       "withholds " + ", ".join(w) + ". The thinned board is the known board without exactly "
       "those orders (technicians, trades and meta unchanged). At f = 1 it holds exactly R, N, "
       "I, F and G. Both dispatch every kept order and no withheld one. All asserted.", "")


# --------------------------------------------------------------------------- #
# R. The replay (worker processes)                                             #
# --------------------------------------------------------------------------- #
def slim(res):
    return OrderedDict((k, res.get(k)) for k in (
        "term_cert", "stage_cert", "term_feas", "stage_feas", "codes", "infra", "obj",
        "obj_orig", "lb", "gap", "ref2", "ref2_from"))


def build_tasks(recs, suite, by, anchors):
    by_inst = OrderedDict()
    for r in sorted(recs, key=lambda x: x["item_id"]):
        it = suite[r["item_id"]]
        st = by[r["item_id"]]
        iid = it["instance"]["instance_id"]
        check("suite instance equals the stored census", iid == st["instance_id"], r["item_id"])
        t = by_inst.setdefault(iid, {"iid": iid, "path": D.instance_path(it), "items": [],
                                     "seeds": OrderedDict(), "digest": OrderedDict()})
        seed = list(it["episode"]["frozen_seed"] or [])
        fk = D.frozen_key(seed)
        check("frozen key equals the stored census", fk == st["frozen_seed"], r["item_id"])
        t["seeds"].setdefault(fk, seed)
        t["digest"].setdefault(fk, anchors[(iid, fk)]["schedule_digest"])
        ops = D.canonical_ops(it)
        check("canonical operation count equals the census", len(ops) == st["n_ops"],
              r["item_id"])
        t["items"].append({"item_id": r["item_id"], "fk": fk, "seed": seed, "ops": ops,
                           "referenced": it["referenced"]})
    return list(by_inst.values())


def replay_task(task):
    t0 = time.perf_counter()
    inst = D.load_instance(task["path"])
    iid = inst["meta"]["id"]
    baseline = dispatch_mod.dispatch_baseline(inst, "atc", 0)
    trajs = {fk: n8.trajectory(inst, seed, baseline) for fk, seed in task["seeds"].items()}
    out = {"iid": iid, "items": [], "n_window": len(inst["work_orders"]),
           "traj_digest": {fk: sched_digest(tr) for fk, tr in trajs.items()}}
    by_id = {wo["id"]: wo for wo in inst["work_orders"]}
    sites = {}
    anchor_cache = {}

    def site_for(fk, seed, t_d):
        key = (fk, t_d)
        if key in sites:
            return sites[key]
        traj = trajs[fk]
        state = n8.site_state(inst, traj, t_d, pm_known=True)
        known = n8.known_instance(inst, state)
        kf = D.kf_fix(state, seed)
        started = state["completed"] + state["in_progress"]
        base_p = n8.pin_schedule(baseline, traj, started)
        s = {"state": state, "known": known, "kf": kf, "base_p": base_p,
             "run_ids": list(state["in_progress"]), "key": "{}|{:.6f}".format(fk, t_d)}
        sites[key] = s
        return s

    for it in task["items"]:
        fk, seed, ops = it["fk"], it["seed"], it["ops"]
        starts = {a["wo"]: float(a["start_bh"]) for a in trajs[fk]["assignments"]}
        iss = D.issuability(it, by_id, starts)
        t_d = D.decision_instant_of(iss, "primary")
        s = site_for(fk, seed, t_d)
        st = s["state"]
        H = candidates(s["known"], st, s["kf"], ops, it["referenced"], inst)
        raw = json.dumps({"operations": ops})
        rec = {"item_id": it["item_id"], "iid": iid, "fk": fk, "t_d": t_d,
               "issuable": iss["issuable"], "n_K": len(s["known"]["work_orders"]),
               "n_H": len(H), "n_completed": len(st["completed"]),
               "n_unknown": len(st["unknown"]), "n_queue": len(st["queue"]),
               "n_running": len(st["in_progress"]), "n_scheduled": len(st["scheduled"]),
               "n_pm_queue": sum(1 for o in st["queue"] if by_id[o].get("is_pm")),
               "configs": [], "boards": OrderedDict()}
        for f in LEVELS.values():
            for d in range(NDRAWS[f]):
                w = withheld_of(it["item_id"], f, d, H)
                bkey = board_key(w)
                if bkey not in rec["boards"]:
                    board = thinned(s["known"], w)
                    p = D.gen_price(board, raw, s["kf"], s["base_p"], t_d, ref2=True,
                                    running_ids=s["run_ids"])
                    akey = (s["key"], bkey)
                    if akey not in anchor_cache:
                        anchor_cache[akey] = slim(D.gen_price(board, D.EMPTY_RAW, s["kf"],
                                                              s["base_p"], t_d))
                    rec["boards"][bkey] = {"p": slim(p), "an": anchor_cache[akey],
                                           "n_orders": len(board["work_orders"])}
                rec["configs"].append({"f": f, "draw": d, "n_w": len(w), "board": bkey,
                                       "n_w_pm": sum(1 for o in w if by_id[o].get("is_pm"))})
        out["items"].append(rec)
    out["wall_s"] = time.perf_counter() - t0
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
                -len(tasks[i]["items"]), iid)

    order = sorted(range(len(tasks)), key=weight)
    res = [None] * len(tasks)
    t0 = time.time()
    ctx = mp.get_context("fork")
    with ctx.Pool(WORKERS, maxtasksperchild=6) as pool:
        for j, (ti, r, err) in enumerate(pool.imap_unordered(_work, order)):
            if err is not None:
                pool.terminate()
                raise SystemExit("[n27b] replay of {} failed:\n{}".format(tasks[ti]["iid"], err))
            res[ti] = r
            say("replayed {} ({} proposals, {} boards, {:.0f}s), {} of {} ({:.0f}s)".format(
                r["iid"], len(r["items"]), sum(len(x["boards"]) for x in r["items"]),
                r["wall_s"], j + 1, len(order), time.time() - t0))
    return res


# --------------------------------------------------------------------------- #
# Prices and dispositions on one board                                         #
# --------------------------------------------------------------------------- #
def gate_of(board, field):
    p, an = board["p"], board["an"]
    check("the no-proposal run on the board is priced", an["stage_cert"] == "qual"
          and an["obj"] is not None and an["lb"] is not None and an["gap"] is not None,
          (an["term_cert"], an["codes"]))
    v = OrderedDict(priced=p["stage_cert"] == "qual" and p["obj"] is not None
                    and p["lb"] is not None and p["term_cert"] != "execution_failed")
    v["pk"] = OrderedDict((g, None) for g in DESIGNS)
    v["g_orig"] = None
    v["disp"] = OrderedDict()
    if v["priced"]:
        gap = certified_gap(p["obj"], p["lb"], G_CERT.lb_floor_bh)
        v["pk"].update([("G-CERT", gap), ("G-CERT-M", gap - an["gap"]),
                        ("D-REL1", D.rel_delta(p["obj"], an["obj"])),
                        ("D-REL2", None if p["ref2"] is None else D.rel_delta(p["obj"],
                                                                               p["ref2"])),
                        ("D-ABS", round(p["obj"] - an["obj"], D.ROUND_BH))])
        v["g_orig"] = (p["obj_orig"] - an["lb"]) / max(an["lb"], FLOOR)
    for tok, g in GATE_DESIGN.items():
        if not v["priced"]:
            v["disp"][tok] = "refused"
        else:
            ref = v["pk"][g] is not None and v["pk"][g] > SETTINGS[g]
            v["disp"][tok] = "referred" if ref else "applied"
    if not v["priced"]:
        v["disp"]["CertSP"] = "refused"
    else:
        two = v["disp"]["Cert"] == "referred" or (field and v["g_orig"] > TAU)
        v["disp"]["CertSP"] = "referred" if two else "applied"
    return v


# --------------------------------------------------------------------------- #
# Z. f = 0 against the stored census and records                              #
# --------------------------------------------------------------------------- #
def tie_zero(x, it, r):
    i = x["item_id"]
    cz = [c for c in x["configs"] if c["f"] == 0.0]
    check("one f = 0 configuration, nothing withheld", len(cz) == 1 and cz[0]["n_w"] == 0, i)
    b = x["boards"][cz[0]["board"]]
    p, an = b["p"], b["an"]
    check("f = 0: priced", p["stage_cert"] == "qual" == it["dt_stage_cert"], i)
    check("f = 0: terminals and codes equal the stored census",
          (p["term_cert"], p["term_feas"], p["codes"]) ==
          (it["dt_term_cert"], it["dt_term_feas"], it["dt_codes"]), i)
    check("f = 0: the board is the stored known board (order count)", b["n_orders"] ==
          it["n_known"], (i, b["n_orders"], it["n_known"]))
    for k, s in (("obj", "dt_obj"), ("obj_orig", "dt_obj_orig"), ("lb", "dt_lb"),
                 ("gap", "dt_gap"), ("ref2", "dt_ref2")):
        close("f = 0: {} = {}".format(k, s), p[k], it[s], TOL, i)
    for k, s in (("obj", "an_obj"), ("obj_orig", "an_obj_orig"), ("lb", "an_lb"),
                 ("gap", "an_gap")):
        close("f = 0, no proposal: {} = {}".format(k, s), an[k], it[s], TOL, i)
    v = gate_of(b, r["field"])
    for g in DESIGNS:
        close("f = 0: price {} = the stored record".format(g), v["pk"][g], r["p_" + g], CSV_TOL, i)
    for tok, g in GATE_DESIGN.items():
        check("f = 0: flag {} equals the stored flag".format(g),
              (v["disp"][tok] == "referred") == bool(r["ref_" + g]), (i, g))
    close("f = 0: second price = n16's g_orig", v["g_orig"], r["g_orig"], TOL, i)
    check("f = 0: the certificate with the second price equals the stored flag",
          (v["disp"]["CertSP"] == "referred") == bool(r["two_k"]), i)
    check("f = 0: window counts equal the stored census",
          (x["n_completed"], x["n_unknown"], x["n_K"]) ==
          (it["n_completed"], it["n_unknown"], it["n_known"]), i)
    return v


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main(argv):
    selftest_only = "--selftest" in argv
    from_stored = "--from-stored" in argv
    t_start = time.time()
    for k, p in IN27B.items():
        if not Path(p).is_file() and k not in NOT_SHIPPED_OK:
            raise SystemExit("missing input {}: {}".format(k, p))
    say("design.md sha256 {} (asserted); frozen prefixes asserted; {} l1adapter .py files "
        "hashed; cores {}".format(DESIGN_SHA[:12], len(ADAPTER0), sorted(_aff)))
    hashes, items_dt, _pub, boot, fc = n13.load_inputs()
    check("60 bootstrap clusters, 20,000 replicates, n2 seed",
          boot.k == 60 and boot.idx.shape == (20000, 60) and n2.SEED == 20261026)
    recs, by, spfi, site, _frecs = n20.build(items_dt, fc, boot)
    check("1,356 priced proposals", len(recs) == 1356, len(recs))
    n16.section0(boot, recs)
    n18.section0(recs, by, spfi, site)
    n20.section0(recs)
    dc = D.Checker()
    suite = OrderedDict((x["item_id"], x) for x in D.load_published(dc))
    check("published suite loads through suite_gate (SHA-256 asserted)", not dc.failures)
    for r in recs:
        r["family"] = suite[r["item_id"]]["family_id"]
    # the frozen counts from the stored records
    for delta, want in ((0.20, dict(costly=186, ref_k=168, app_k=18, two_app_k=0, low=1170,
                                    low_ref_k=15, low_two_k=22)),
                        (0.10, dict(costly=208, app_k=25, two_app_k=6))):
        o, _c, _l = n20.tally(recs, lambda r, d=delta: n13.costly_of(r, d))
        for k, v in want.items():
            check("frozen count at {:.2f}: {} = {}".format(delta, k, v), o[k] == v, o[k])
    # N18's later share of the costly proposals at 0.20
    m18 = n13.macros_of(IN27B["n18_macros"])
    L = {r["item_id"]: by[r["item_id"]]["n_unknown"] / (
        by[r["item_id"]]["n_completed"] + by[r["item_id"]]["n_known"]
        + by[r["item_id"]]["n_unknown"]) for r in recs}
    c20 = [r for r in recs if n13.costly_of(r, 0.20) == 1]
    check("N18 later share of the costly proposals: median and maximum",
          (pctv(statistics.median(L[r["item_id"]] for r in c20)),
           pctv(max(L[r["item_id"]] for r in c20))) ==
          (m18["nEighteenLaterCostlyTwentyMedian"], m18["nEighteenLaterCostlyTwentyMax"]))
    say("published headline and frozen counts asserted (186 costly, 168 referred, 18 applied, "
        "0 with the second price, 15 -> 22 low-cost referred; 208, 25, 6 at 0.10)")
    block_p()
    say("probe passed")
    anchors = D.load_anchor_records()
    tasks = build_tasks(recs, suite, by, anchors)
    smoke = os.environ.get("N27B_SMOKE")
    if smoke:
        if not selftest_only:
            raise SystemExit("[n27b] N27B_SMOKE is for test runs with --selftest")
        tasks = [t for t in tasks if t["iid"] in set(smoke.split(","))]
    say("replaying {} proposals on {} windows, {} workers on cores {}".format(
        sum(len(t["items"]) for t in tasks), len(tasks), WORKERS, sorted(_aff)))
    t_rep = time.time()
    cache = os.environ.get("N27B_REPLAY_CACHE")
    stored_sha = None
    if from_stored:
        # the stored replay of the official fresh run: one JSON line per proposal, in task order
        check("stored replay present", OUT_REPLAY.is_file(), str(OUT_REPLAY))
        stored_sha = sha256_file(OUT_REPLAY)
        by_iid = OrderedDict()
        with open(OUT_REPLAY, encoding="utf-8") as fh:
            for ln in fh:
                x = json.loads(ln)
                by_iid.setdefault(x["iid"], []).append(x)
        check("stored replay holds 1,356 proposals", sum(len(v) for v in by_iid.values())
              == 1356)
        results = []
        for t in tasks:
            inst = D.load_instance(t["path"])
            check("stored replay: proposals of the window equal the tasks'",
                  [x["item_id"] for x in by_iid[t["iid"]]] == [i["item_id"] for i in t["items"]],
                  t["iid"])
            results.append({"iid": t["iid"], "items": by_iid[t["iid"]],
                            "n_window": len(inst["work_orders"]), "traj_digest": None,
                            "wall_s": 0.0})
        say("replay loaded from the stored official replay (sha256 {})".format(stored_sha[:12]))
    elif cache and Path(cache).is_file():
        import pickle
        if not selftest_only:
            raise SystemExit("[n27b] N27B_REPLAY_CACHE is for test runs with --selftest; the "
                             "outputs need a fresh replay")
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
    nwin = {}
    ncorr = {}
    for t in tasks:                       # corrective orders of each window (descriptive 5c)
        inst = D.load_instance(t["path"])
        ncorr[inst["meta"]["id"]] = sum(1 for wo in inst["work_orders"] if not wo.get("is_pm"))
    for t, res in zip(tasks, results):
        check("task and result agree", t["iid"] == res["iid"])
        for fk, dg in (res["traj_digest"] or {}).items():
            check("the trajectory's schedule digest equals rule_anchor.json's",
                  dg == t["digest"][fk], (t["iid"], fk))
        nwin[res["iid"]] = res["n_window"]
        for x in res["items"]:
            check("one replay per proposal", x["item_id"] not in rep, x["item_id"])
            rep[x["item_id"]] = x
    recs_by = {r["item_id"]: r for r in recs}
    if not smoke:
        check("every priced proposal replayed", set(rep) == set(recs_by), len(rep))
    for i, x in rep.items():
        it = by[i]
        check("decision instant equals the stored census", x["t_d"] == float(it["t_d"]), i)
        check("issuable", x["issuable"] and it["issuable"], i)
        check("window size = completed + known + unknown", nwin[x["iid"]] ==
              it["n_completed"] + it["n_known"] + it["n_unknown"], i)
        x["n_corr_window"] = ncorr[x["iid"]]
        check("orders arriving after t_d are corrective (planned ones are on the calendar)",
              x["n_corr_window"] >= x["n_unknown"], i)
        for c in x["configs"]:
            check("withheld planned orders within the withheld set", 0 <= c["n_w_pm"] <= c["n_w"],
                  i)
            check("withheld corrective orders fit the window's corrective orders",
                  x["n_unknown"] + c["n_w"] - c["n_w_pm"] <= x["n_corr_window"], i)
    # Z. f = 0
    zero = {i: tie_zero(x, by[i], recs_by[i]) for i, x in rep.items()}
    say("f = 0 tied to the stored census, prices and flags of every design ({} proposals)".format(
        len(zero)))
    # records per (proposal, level, draw)
    R = OrderedDict()
    for i, x in rep.items():
        r = recs_by[i]
        it = by[i]
        n_window = it["n_completed"] + it["n_known"] + it["n_unknown"]
        for c in x["configs"]:
            b = x["boards"][c["board"]]
            v = gate_of(b, r["field"])
            R[(i, c["f"], c["draw"])] = OrderedDict(
                item_id=i, f=c["f"], draw=c["draw"], n_w=c["n_w"], n_K=x["n_K"], n_H=x["n_H"],
                n_window=n_window, n_unknown=x["n_unknown"],
                unseen=(x["n_unknown"] + c["n_w"]) / n_window,
                unseen_corr=(x["n_unknown"] + c["n_w"] - c["n_w_pm"]) / x["n_corr_window"],
                n_corr_window=x["n_corr_window"], n_w_pm=c["n_w_pm"],
                k_share=c["n_w"] / x["n_K"],
                h_share=x["n_H"] / x["n_K"], board=b, v=v,
                reused=c["n_w"] == 0 and c["f"] > 0, r=r)
    if smoke:
        for i in sorted(rep):
            x = rep[i]
            say("smoke {}: |K| {} |H| {} boards {}".format(i, x["n_K"], x["n_H"], len(x["boards"])))
        say("smoke run: {} checks, replay {:.0f}s".format(NCHECK[0], wall_rep))
        return 0
    if from_stored:
        check("stored replay: written by the same code path (rewritten byte for byte)",
              "".join(json.dumps(x, sort_keys=True) + "\n" for x in rep.values()).encode("utf-8")
              == OUT_REPLAY.read_bytes())
    return analyse(dict(recs=recs, by=by, boot=boot, rep=rep, R=R, zero=zero,
                        from_stored=from_stored, stored_sha=stored_sha,
                        wall_rep=wall_rep, t_start=t_start, selftest_only=selftest_only,
                        tasks=tasks, suite=suite, hashes=hashes))


# --------------------------------------------------------------------------- #
# Analysis                                                                     #
# --------------------------------------------------------------------------- #
def lvl_tok(f):
    return [k for k, v in LEVELS.items() if v == f][0]


def band_of(u):
    for tok, (lo, hi, _t) in BANDS.items():
        if (lo is None or u > lo) and (hi is None or u <= hi):
            return tok
    raise ValueError(u)


def disp_counts(A, sel, f, gate):
    """Per draw: referred, applied, refused among sel (a list of item ids)."""
    out = []
    for d in range(NDRAWS[f]):
        c = Counter(A["R"][(i, f, d)]["v"]["disp"][gate] for i in sel)
        out.append(OrderedDict(referred=c["referred"], applied=c["applied"],
                               refused=c["refused"]))
    return out


def mean_rng(xs):
    return (sum(xs) / len(xs), min(xs), max(xs))


def analyse(A):
    recs, boot, R = A["recs"], A["boot"], A["R"]
    ids = [r["item_id"] for r in recs]
    lab = {dl: {r["item_id"]: n13.costly_of(r, dl) for r in recs} for dl in DELTAS.values()}
    check("no proposal undecided at either level", all(v is not None for d in lab.values()
                                                        for v in d.values()))
    T = OrderedDict()                                   # (delta, f, gate) -> summary
    for dtok, dl in DELTAS.items():
        costly = [i for i in ids if lab[dl][i] == 1]
        low = [i for i in ids if lab[dl][i] == 0]
        for ftok, f in LEVELS.items():
            for gate in GATES:
                pc = disp_counts(A, costly, f, gate)
                pl = disp_counts(A, low, f, gate)
                o = OrderedDict(n_costly=len(costly), n_low=len(low))
                for k in ("referred", "applied", "refused"):
                    o["c_" + k] = mean_rng([x[k] for x in pc])
                    o["l_" + k] = mean_rng([x[k] for x in pl])
                flips = Counter()
                lists = defaultdict(list)
                for i in costly:
                    d0 = R[(i, 0.0, 0)]["v"]["disp"][gate]
                    ds = [R[(i, f, d)]["v"]["disp"][gate] for d in range(NDRAWS[f])]
                    if any(x != d0 for x in ds):
                        flips["any"] += 1
                        lists["any"].append(i)
                    if d0 == "referred" and "applied" in ds:
                        flips["ra"] += 1
                        lists["ra"].append(i)
                    if d0 == "applied" and "referred" in ds:
                        flips["ar"] += 1
                        lists["ar"].append(i)
                    if "refused" in ds:
                        flips["rf"] += 1
                o["flip_any"], o["flip_ra"], o["flip_ar"], o["flip_rf"] = (
                    flips["any"], flips["ra"], flips["ar"], flips["rf"])
                o["flip_lists"] = {k: v for k, v in lists.items()}
                lr = [R[(i, f, 0)] for i in low]
                flags = [x["v"]["disp"][gate] == "referred" for x in lr]
                rows = [{"instance_id": x["r"]["instance_id"]} for x in lr]
                o["l_share0"] = sum(flags) / len(flags)
                o["l_lo0"], o["l_hi0"] = boot.ci(rows, flags)
                o["l_share_mean"] = o["l_referred"][0] / len(low)
                T[(dl, f, gate)] = o
    # f = 0 against the stored tallies
    for dl in DELTAS.values():
        o, _c, _l = n20.tally(recs, lambda r, d=dl: n13.costly_of(r, d))
        z = T[(dl, 0.0, "Cert")]
        check("f = 0 tables equal the stored tally (certificate)",
              (z["c_referred"][0], z["c_applied"][0], z["l_referred"][0], z["c_refused"][0])
              == (o["ref_k"], o["app_k"], o["low_ref_k"], 0))
        z2 = T[(dl, 0.0, "CertSP")]
        check("f = 0 tables equal the stored tally (second price)",
              (z2["c_applied"][0], z2["l_referred"][0]) == (o["two_app_k"], o["low_two_k"]))
        s = n13.score(boot, recs, lambda r: r["ref_k"], dl)
        check("f = 0 low-cost interval equals n13.score's", (pctv(s["fr_lo"]), pctv(s["fr_hi"]))
              == (pctv(T[(dl, 0.0, "Cert")]["l_lo0"]), pctv(T[(dl, 0.0, "Cert")]["l_hi0"])))
    # macros for items 1 and 2
    for (dl, f, gate), o in T.items():
        dtok = [k for k, v in DELTAS.items() if v == dl][0]
        pre = lvl_tok(f) + dtok + gate
        ctx = "f = {:.2f}, delta = {:.2f}, {}".format(f, dl, GATES[gate])
        main = gate in MAIN_GATES
        for k, tok in (("c_referred", "CostlyRef"), ("c_applied", "CostlyApp"),
                       ("c_refused", "CostlyRefused"), ("l_referred", "LowRef")):
            if not main and k in ("c_refused",):
                continue
            mean, lo, hi = o[k]
            add(pre + tok + "Mean", m1(mean), "[1-2] {}: {} (mean over {} draw{})".format(
                ctx, {"c_referred": "costly proposals referred", "c_applied": "costly proposals "
                      "applied", "c_refused": "costly proposals refused by a check",
                      "l_referred": "low-cost proposals referred"}[k], NDRAWS[f],
                "s" if NDRAWS[f] > 1 else ""))
            if main or k == "c_applied":
                add(pre + tok + "Min", grp(lo), "[1-2] {}: the same, smallest over draws".format(
                    ctx))
                add(pre + tok + "Max", grp(hi), "[1-2] {}: the same, largest over draws".format(
                    ctx))
        add(pre + "FlipAny", grp(o["flip_any"]),
            "[1] {}: costly proposals whose disposition differs from f = 0 in at least one "
            "draw".format(ctx))
        if main:
            add(pre + "FlipRefToApp", grp(o["flip_ra"]),
                "[1] {}: of these, referred at f = 0 and applied in some draw".format(ctx))
            add(pre + "FlipAppToRef", grp(o["flip_ar"]),
                "[1] {}: of these, applied at f = 0 and referred in some draw".format(ctx))
            add(pre + "LowRefShare", pctv(o["l_share0"]),
                "[2] {}: low-cost referral share on draw 0".format(ctx))
            add(pre + "LowRefLo", pctv(o["l_lo0"]),
                "[2] {}: lower end of its 95% cluster-bootstrap interval (n2 seed, 20,000 "
                "replicates, 60 instance clusters)".format(ctx))
            add(pre + "LowRefHi", pctv(o["l_hi0"]), "[2] {}: upper end of the same "
                "interval".format(ctx))
    NUM["dispositions"] = OrderedDict(("delta {:.2f} f {:.2f} {}".format(*k),
                                       {kk: vv for kk, vv in v.items()}) for k, v in T.items())
    # 3. by edit type and stratum
    S3 = OrderedDict()
    for dl in DELTAS.values():
        for dim, keyf, toks in (("edit", lambda r: r["split"], EDIT_TOK),
                                ("stratum", lambda r: r["stratum"],
                                 OrderedDict((s, n13.ST_TOK[s]) for s in D.STRATA))):
            for val, tok in toks.items():
                sel = [r["item_id"] for r in recs if keyf(r) == val]
                if not sel:
                    continue
                costly = [i for i in sel if lab[dl][i] == 1]
                low = [i for i in sel if lab[dl][i] == 0]
                for f in LEVELS.values():
                    for gate in MAIN_GATES:
                        pc = disp_counts(A, costly, f, gate) if costly else [Counter()]
                        pl = disp_counts(A, low, f, gate) if low else [Counter()]
                        S3[(dl, dim, tok, f, gate)] = OrderedDict(
                            n=len(sel), n_costly=len(costly), n_low=len(low),
                            c_ref=mean_rng([x.get("referred", 0) for x in pc]),
                            c_app=mean_rng([x.get("applied", 0) for x in pc]),
                            l_ref=mean_rng([x.get("referred", 0) for x in pl]))
    for (dl, dim, tok, f, gate), o in S3.items():
        if dl != 0.20:
            continue
        dtok = "DeltaTwenty"
        add(lvl_tok(f) + dtok + gate + tok + "CostlyAppMean", m1(o["c_app"][0]),
            "[3] f = {:.2f}, delta = 0.20, {}, {} {}: costly proposals applied (mean over "
            "draws, of {})".format(f, GATES[gate], dim, tok, o["n_costly"]))
        add(lvl_tok(f) + dtok + gate + tok + "LowRefMean", m1(o["l_ref"][0]),
            "[3] f = {:.2f}, delta = 0.20, {}, {} {}: low-cost proposals referred (mean over "
            "draws, of {})".format(f, GATES[gate], dim, tok, o["n_low"]))
    NUM["by_group"] = OrderedDict(("delta {:.2f} {} {} f {:.2f} {}".format(*k), v)
                                  for k, v in S3.items())
    # 4. bands of the share not seen (costly proposals)
    B4 = OrderedDict()
    for dl in DELTAS.values():
        costly = [i for i in ids if lab[dl][i] == 1]
        for f in LEVELS.values():
            cell = OrderedDict((b, OrderedDict(pairs=0, ref=0, ref_sp=0, props=set()))
                               for b in BANDS)
            for i in costly:
                for d in range(NDRAWS[f]):
                    x = R[(i, f, d)]
                    b = band_of(x["unseen"])
                    cell[b]["pairs"] += 1
                    cell[b]["ref"] += x["v"]["disp"]["Cert"] == "referred"
                    cell[b]["ref_sp"] += x["v"]["disp"]["CertSP"] == "referred"
                    cell[b]["props"].add(i)
            for b, c in cell.items():
                c["props"] = len(c["props"])
            B4[(dl, f)] = cell
    for f in LEVELS.values():
        for b, c in B4[(0.20, f)].items():
            add(lvl_tok(f) + "DeltaTwentyBand" + b + "Pairs", grp(c["pairs"]),
                "[4] f = {:.2f}, delta = 0.20: costly proposal-draws whose share not seen is "
                "{}".format(f, BANDS[b][2]))
            add(lvl_tok(f) + "DeltaTwentyBand" + b + "CertRef", grp(c["ref"]),
                "[4] f = {:.2f}, delta = 0.20: of these, referred by the certificate".format(f))
    NUM["bands"] = OrderedDict(("delta {:.2f} f {:.2f}".format(*k), v) for k, v in B4.items())
    # 5. distributions
    D5 = OrderedDict()
    for pop, sel in (("Priced", ids), ("Costly", [i for i in ids if lab[0.20][i] == 1])):
        D5[(pop, "h_share")] = quart([R[(i, 0.0, 0)]["h_share"] for i in sel])
        D5[(pop, "n_H")] = quart([R[(i, 0.0, 0)]["n_H"] for i in sel])
        D5[(pop, "h_zero")] = sum(1 for i in sel if R[(i, 0.0, 0)]["n_H"] == 0)
        for f in LEVELS.values():
            us = [R[(i, f, d)]["unseen"] for i in sel for d in range(NDRAWS[f])]
            D5[(pop, "unseen", f)] = quart(us)
            D5[(pop, "added", f)] = quart([R[(i, f, d)]["unseen"] - R[(i, 0.0, 0)]["unseen"]
                                           for i in sel for d in range(NDRAWS[f])])
            D5[(pop, "n_w", f)] = quart([R[(i, f, d)]["n_w"] for i in sel
                                         for d in range(NDRAWS[f])])
            D5[(pop, "k_share", f)] = quart([R[(i, f, d)]["k_share"] for i in sel
                                             for d in range(NDRAWS[f])])
            D5[(pop, "pm_share_w", f)] = quart([R[(i, f, d)]["n_w_pm"] / R[(i, f, d)]["n_w"]
                                                for i in sel for d in range(NDRAWS[f])
                                                if R[(i, f, d)]["n_w"] > 0] or [0.0])
    ptxt = {"Priced": "all 1,356 priced proposals", "Costly": "the 186 costly proposals (0.20)"}
    for pop in ("Priced", "Costly"):
        q = D5[(pop, "h_share")]
        for k, tok in (("median", "Median"), ("q1", "QOne"), ("q3", "QThree"), ("max", "Max")):
            add(pop + "HShare" + tok, pct1(q[k]).replace("%", "\\%"),
                "[5] {}: |H2| / |K| (candidates over the known board), {}".format(ptxt[pop], k))
        q = D5[(pop, "n_H")]
        add(pop + "HMedian", m1(q["median"]), "[5] {}: |H2|, median".format(ptxt[pop]))
        add(pop + "HMax", grp(int(q["max"])), "[5] {}: |H2|, maximum".format(ptxt[pop]))
        add(pop + "HZero", grp(D5[(pop, "h_zero")]),
            "[5] {}: proposals with no candidate order (|H2| = 0)".format(ptxt[pop]))
        for f in LEVELS.values():
            q = D5[(pop, "unseen", f)]
            for k, tok in (("median", "Median"), ("q1", "QOne"), ("q3", "QThree"),
                           ("max", "Max")):
                add(lvl_tok(f) + pop + "Unseen" + tok, pctv(q[k]),
                    "[5] f = {:.2f}, {}: share of the window not seen by the gate, {} over "
                    "proposal-draws".format(f, ptxt[pop], k))
            qk = D5[(pop, "k_share", f)]
            for k, tok in (("median", "Median"), ("q1", "QOne"), ("q3", "QThree"),
                           ("max", "Max")):
                add(lvl_tok(f) + pop + "KWithheld" + tok, pctv(qk[k]),
                    "[5] f = {:.2f}, {}: share of the known board withheld (n_w / |K|), {} over "
                    "proposal-draws".format(f, ptxt[pop], k))
            qa = D5[(pop, "added", f)]
            add(lvl_tok(f) + pop + "AddedMax", pctv(qa["max"]),
                "[5] f = {:.2f}, {}: largest rise of the share not seen over f = 0 (percentage "
                "points of the window)".format(f, ptxt[pop]))
            add(lvl_tok(f) + pop + "AddedMedian", pctv(qa["median"]),
                "[5] f = {:.2f}, {}: median rise of the share not seen over f = 0".format(
                    f, ptxt[pop]))
    NUM["distributions"] = OrderedDict(("{} {}".format(k[0], " ".join(str(x) for x in k[1:])), v)
                                       for k, v in D5.items())
    # 5b. composition of the known board (descriptive, as in N27)
    X = OrderedDict()
    comp = OrderedDict([("Running", "running"), ("QueuedPlanned", "queued planned orders"),
                        ("CalendarPlanned", "planned orders on the calendar"),
                        ("QueuedCorrective", "queued corrective orders"),
                        ("NamedFrozen", "unstarted orders named or frozen"),
                        ("Candidates", "candidates H2")])

    def parts(x):
        out = OrderedDict([("Running", x["n_running"]), ("QueuedPlanned", x["n_pm_queue"]),
                           ("CalendarPlanned", x["n_scheduled"]),
                           ("QueuedCorrective", x["n_queue"] - x["n_pm_queue"]),
                           ("NamedFrozen", x["n_queue"] + x["n_scheduled"] - x["n_H"]),
                           ("Candidates", x["n_H"])])
        check("K = running + queued + calendar, and unstarted = candidates + named or frozen",
              out["Running"] + out["QueuedPlanned"] + out["CalendarPlanned"]
              + out["QueuedCorrective"] == x["n_K"] and out["NamedFrozen"] >= 0
              and out["QueuedCorrective"] >= 0, x["item_id"])
        return out
    for pop, sel in (("Priced", ids), ("Costly", [i for i in ids if lab[0.20][i] == 1])):
        ps = [parts(A["rep"][i]) for i in sel]
        for tok in comp:
            X[(pop, "comp", tok)] = quart([q[tok] / A["rep"][i]["n_K"] for q, i in zip(ps, sel)])
            X[(pop, "compn", tok)] = quart([q[tok] for q in ps])
        X[(pop, "K")] = quart([A["rep"][i]["n_K"] for i in sel])
        X[(pop, "planned_share")] = quart([(q["QueuedPlanned"] + q["CalendarPlanned"])
                                           / A["rep"][i]["n_K"] for q, i in zip(ps, sel)])
    for pop in ("Priced", "Costly"):
        q = X[(pop, "planned_share")]
        add(pop + "PlannedShareMedian", pctv(q["median"]),
            "[5b] {}: planned orders (queued or on the calendar) as a share of K, median".format(
                ptxt[pop]))
        add(pop + "PlannedShareMin", pctv(q["min"]),
            "[5b] {}: the same, minimum".format(ptxt[pop]))
        add(pop + "KMedian", grp(int(round(X[(pop, "K")]["median"]))),
            "[5b] {}: orders on K, median".format(ptxt[pop]))
    # 5c. share of the window's corrective orders not seen (descriptive, as in N27): every order
    # that arrives after t_d is corrective; the withheld corrective orders are added to them
    for pop, sel in (("Priced", ids), ("Costly", [i for i in ids if lab[0.20][i] == 1])):
        for f in LEVELS.values():
            X[(pop, "unseen_corr", f)] = quart([R[(i, f, d)]["unseen_corr"] for i in sel
                                                for d in range(NDRAWS[f])])
    for pop in ("Priced", "Costly"):
        for f in LEVELS.values():
            q = X[(pop, "unseen_corr", f)]
            for k, tok in (("median", "Median"), ("q1", "QOne"), ("q3", "QThree"),
                           ("max", "Max")):
                add(lvl_tok(f) + pop + "CorrUnseen" + tok, pctv(q[k]),
                    "[5c] f = {:.2f}, {}: share of the window's corrective orders not seen by "
                    "the gate, {} over proposal-draws".format(f, ptxt[pop], k))
    for dl in DELTAS.values():
        costly = [i for i in ids if lab[dl][i] == 1]
        for f in LEVELS.values():
            cell = OrderedDict((b, OrderedDict(pairs=0, ref=0, ref_sp=0, props=set()))
                               for b in BANDS)
            for i in costly:
                for d in range(NDRAWS[f]):
                    x = R[(i, f, d)]
                    b = band_of(x["unseen_corr"])
                    cell[b]["pairs"] += 1
                    cell[b]["ref"] += x["v"]["disp"]["Cert"] == "referred"
                    cell[b]["ref_sp"] += x["v"]["disp"]["CertSP"] == "referred"
                    cell[b]["props"].add(i)
            for b, c in cell.items():
                c["props"] = len(c["props"])
            X[("bands_corr", dl, f)] = cell
    for f in LEVELS.values():
        for b, c in X[("bands_corr", 0.20, f)].items():
            add(lvl_tok(f) + "DeltaTwentyCorrBand" + b + "Pairs", grp(c["pairs"]),
                "[5c] f = {:.2f}, delta = 0.20: costly proposal-draws whose share of corrective "
                "orders not seen is {}".format(f, BANDS[b][2]))
            add(lvl_tok(f) + "DeltaTwentyCorrBand" + b + "CertRef", grp(c["ref"]),
                "[5c] f = {:.2f}, delta = 0.20: of these, referred by the certificate".format(f))
    # 6b. movement of the certificate price (descriptive, as in N27)
    for dtok, dl in DELTAS.items():
        costly = [i for i in ids if lab[dl][i] == 1]
        mv = OrderedDict()
        for pop, sel in (("Priced", ids), ("Costly", costly)):
            ds = []
            for i in sel:
                p0 = R[(i, 0.0, 0)]["v"]["pk"]["G-CERT"]
                ds.append(max(abs(R[(i, f, d)]["v"]["pk"]["G-CERT"] - p0)
                              for f in LEVELS.values() for d in range(NDRAWS[f])
                              if R[(i, f, d)]["v"]["pk"]["G-CERT"] is not None))
            mv[pop] = OrderedDict(changed=sum(1 for x in ds if x > 1e-9), n=len(ds),
                                  q=quart(ds))
        ref0 = [i for i in costly if R[(i, 0.0, 0)]["v"]["disp"]["Cert"] == "referred"]
        app0 = [i for i in costly if R[(i, 0.0, 0)]["v"]["disp"]["Cert"] == "applied"]
        for f in LEVELS.values():
            pr = [R[(i, f, d)]["v"]["pk"]["G-CERT"] for i in ref0 for d in range(NDRAWS[f])
                  if R[(i, f, d)]["v"]["pk"]["G-CERT"] is not None]
            pa = [R[(i, f, d)]["v"]["pk"]["G-CERT"] for i in app0 for d in range(NDRAWS[f])
                  if R[(i, f, d)]["v"]["pk"]["G-CERT"] is not None]
            mv[("ref_min", f)] = min(pr) if pr else None
            mv[("app_max", f)] = max(pa) if pa else None
        X[("move", dl)] = mv
        for pop in ("Priced", "Costly"):
            add(dtok + pop + "CertMoved", grp(mv[pop]["changed"]),
                "[6b] delta = {:.2f}, {}: proposals whose certificate price differs from f = 0 "
                "in some draw of some level (by more than 1e-9)".format(dl, "all 1,356 priced "
                                                                       "proposals" if pop ==
                                                                       "Priced" else "costly"))
            add(dtok + pop + "CertMoveMax", "{:.3f}".format(mv[pop]["q"]["max"]),
                "[6b] delta = {:.2f}, {}: largest change of the certificate price from f = 0 "
                "over all draws and levels".format(dl, pop.lower()))
            add(dtok + pop + "CertMoveMedian", "{:.4f}".format(mv[pop]["q"]["median"]),
                "[6b] delta = {:.2f}, {}: median over proposals of the largest change of the "
                "certificate price".format(dl, pop.lower()))
        for f in LEVELS.values():
            add(lvl_tok(f) + dtok + "CertRefMinPrice", p3(mv[("ref_min", f)]),
                "[6b] f = {:.2f}, delta = {:.2f}: smallest certificate price among the costly "
                "proposals the certificate refers at f = 0 (over draws; threshold 0.20)".format(
                    f, dl))
            add(lvl_tok(f) + dtok + "CertAppMaxPrice", p3(mv[("app_max", f)]),
                "[6b] f = {:.2f}, delta = {:.2f}: largest certificate price among the costly "
                "proposals the certificate applies at f = 0 (over draws)".format(f, dl))
    NUM["composition_and_movement"] = OrderedDict((" ".join(str(y) for y in k), v)
                                                  for k, v in X.items())
    # 6. costly proposals whose disposition changes, and where the first change occurs
    L6 = OrderedDict()
    CH = OrderedDict()
    for dtok, dl in DELTAS.items():
        costly = [i for i in ids if lab[dl][i] == 1]
        for gate in GATES:
            chg = OrderedDict()
            for i in costly:
                d0 = R[(i, 0.0, 0)]["v"]["disp"][gate]
                hits = [(f, d) for f in LEVELS.values() for d in range(NDRAWS[f])
                        if R[(i, f, d)]["v"]["disp"][gate] != d0]
                if hits:
                    chg[i] = hits
            allhits = [(f, d, i) for i, hs in chg.items() for f, d in hs]
            o = OrderedDict(ids=list(chg), n=len(chg),
                            ra=sum(1 for i in chg if R[(i, 0.0, 0)]["v"]["disp"][gate] ==
                                   "referred" and any(R[(i, f, d)]["v"]["disp"][gate] ==
                                                      "applied" for f, d in chg[i])),
                            ar=sum(1 for i in chg if R[(i, 0.0, 0)]["v"]["disp"][gate] ==
                                   "applied" and any(R[(i, f, d)]["v"]["disp"][gate] ==
                                                     "referred" for f, d in chg[i])),
                            rf=sum(1 for i in chg if any(R[(i, f, d)]["v"]["disp"][gate] ==
                                                         "refused" for f, d in chg[i])),
                            first_level=None, first_unseen_min=None, first_k_min=None,
                            unseen_min=None, k_min=None, first_n=0)
            if allhits:
                fl = min(f for f, _d, _i in allhits)
                at = [(f, d, i) for f, d, i in allhits if f == fl]
                o["first_level"] = fl
                o["first_n"] = len({i for _f, _d, i in at})
                o["first_unseen_min"] = min(R[(i, f, d)]["unseen"] for f, d, i in at)
                o["first_k_min"] = min(R[(i, f, d)]["k_share"] for f, d, i in at)
                o["unseen_min"] = min(R[(i, f, d)]["unseen"] for f, d, i in allhits)
                o["k_min"] = min(R[(i, f, d)]["k_share"] for f, d, i in allhits)
            CH[(dl, gate)] = o
            ctx = "delta = {:.2f}, {}".format(dl, GATES[gate])
            add(dtok + gate + "ChangedN", grp(o["n"]),
                "[6] {}: costly proposals whose disposition differs from f = 0 in some draw of "
                "some level".format(ctx))
            add(dtok + gate + "ChangedRefToApp", grp(o["ra"]),
                "[6] {}: of these, referred at f = 0 and applied in some draw".format(ctx))
            add(dtok + gate + "ChangedAppToRef", grp(o["ar"]),
                "[6] {}: of these, applied at f = 0 and referred in some draw".format(ctx))
            add(dtok + gate + "ChangedRefused", grp(o["rf"]),
                "[6] {}: of these, refused by a check in some draw".format(ctx))
            if gate in MAIN_GATES:
                add(dtok + gate + "FirstLevel", "none" if o["first_level"] is None else
                    "{:.2f}".format(o["first_level"]),
                    "[6] {}: lowest level at which a costly proposal's disposition changes in "
                    "some draw".format(ctx))
                add(dtok + gate + "FirstLevelN", grp(o["first_n"]),
                    "[6] {}: costly proposals that change at that lowest level".format(ctx))
                add(dtok + gate + "FirstUnseenMin", pctv(o["first_unseen_min"]),
                    "[6] {}: smallest share of the window not seen among the changed "
                    "proposal-draws at that lowest level".format(ctx))
                add(dtok + gate + "FirstKWithheldMin", pctv(o["first_k_min"]),
                    "[6] {}: smallest share of K withheld among the changed proposal-draws at "
                    "that lowest level".format(ctx))
                add(dtok + gate + "ChangeUnseenMin", pctv(o["unseen_min"]),
                    "[6] {}: smallest share of the window not seen among all changed "
                    "proposal-draws".format(ctx))
                add(dtok + gate + "ChangeKWithheldMin", pctv(o["k_min"]),
                    "[6] {}: smallest share of K withheld among all changed proposal-draws".format(
                        ctx))
        L6[dl] = sorted(set(CH[(dl, "Cert")]["ids"]) | set(CH[(dl, "CertSP")]["ids"]))
    # facts about the costly proposals whose certificate disposition changes at delta = 0.20
    chg = CH[(0.20, "Cert")]["ids"]
    chg_sp = CH[(0.20, "CertSP")]["ids"]
    check("some costly proposal changes under the certificate at 0.20", len(chg) > 0)
    rc = [R[(i, 0.0, 0)]["r"] for i in chg]
    p0 = [R[(i, 0.0, 0)]["v"]["pk"]["G-CERT"] for i in chg]
    p1 = [R[(i, 1.0, 0)]["v"]["pk"]["G-CERT"] for i in chg]
    check("the changed proposals are priced at f = 0 and f = 1",
          all(x is not None for x in p0 + p1))
    CHX = OrderedDict([
        ("Instances", (grp(len({r["instance_id"] for r in rc})),
                       "distinct instances the changed proposals lie on")),
        ("CostMin", ("{:.3f}".format(min(r["lo"] for r in rc)),
                     "smallest realised cost (lower end of the realised-cost interval)")),
        ("CostMax", ("{:.3f}".format(max(r["hi"] for r in rc)),
                     "largest realised cost (upper end of the realised-cost interval)")),
        ("PriceFZeroMin", ("{:.3f}".format(min(p0)), "smallest certificate price at f = 0")),
        ("PriceFZeroMax", ("{:.3f}".format(max(p0)), "largest certificate price at f = 0")),
        ("PriceFOneMin", ("{:.3f}".format(min(p1)), "smallest certificate price at f = 1")),
        ("PriceFOneMax", ("{:.3f}".format(max(p1)), "largest certificate price at f = 1")),
        ("SequencingOnly", (grp(sum(1 for r in rc if r["split"] == "sequencing_only")),
                            "how many of them only re-sequence work"))])
    for tok, (val, txt) in CHX.items():
        add("DeltaTwentyCertChanged" + tok, val,
            "[6] delta = 0.20, the certificate: of the costly proposals whose disposition "
            "differs from f = 0 in some draw of some level, {}".format(txt))
    add("DeltaTwentyCertSPChangedFieldEdits",
        grp(sum(1 for i in chg_sp if R[(i, 0.0, 0)]["r"]["split"] == "field_changing")),
        "[6] delta = 0.20, the certificate with the second price: of the costly proposals whose "
        "disposition differs from f = 0 in some draw of some level, how many are field edits")
    NUM["changed_cert_delta020"] = OrderedDict((k, v[0]) for k, v in CHX.items())
    X["changed_macros"] = ["nTwentySevenAllDeltaTwentyCertChanged" + k for k in CHX] + [
        "nTwentySevenAllDeltaTwentyCertSPChangedFieldEdits"]
    NUM["changed"] = OrderedDict(("delta {:.2f} {}".format(*k), v) for k, v in CH.items())
    # figure data
    fig = []
    for dl in DELTAS.values():
        for f in LEVELS.values():
            for gate in GATES:
                o = T[(dl, f, gate)]
                mean, lo, hi = o["c_referred"]
                fig.append([f, "{:.2f}".format(dl), gate, "costly_referred_share",
                            mean / o["n_costly"], lo / o["n_costly"], hi / o["n_costly"],
                            "range over draws", NDRAWS[f]])
                fig.append([f, "{:.2f}".format(dl), gate, "lowcost_referred_share",
                            o["l_share0"], o["l_lo0"], o["l_hi0"],
                            "draw 0, 95% cluster bootstrap over instances", NDRAWS[f]])
                fig.append([f, "{:.2f}".format(dl), gate, "lowcost_referred_share_mean",
                            o["l_share_mean"], o["l_referred"][1] / o["n_low"],
                            o["l_referred"][2] / o["n_low"], "range over draws", NDRAWS[f]])
        for pop in ("Priced", "Costly"):
            if dl != 0.20:
                continue
            for f in LEVELS.values():
                q = D5[(pop, "unseen", f)]
                fig.append([f, "", "all" if pop == "Priced" else "costly at 0.20",
                            "median_share_not_seen", q["median"], q["q1"], q["q3"],
                            "quartiles over proposal-draws", NDRAWS[f]])
                qk = D5[(pop, "k_share", f)]
                fig.append([f, "", "all" if pop == "Priced" else "costly at 0.20",
                            "median_share_of_K_withheld", qk["median"], qk["q1"], qk["q3"],
                            "quartiles over proposal-draws", NDRAWS[f]])
                qc = X[(pop, "unseen_corr", f)]
                fig.append([f, "", "all" if pop == "Priced" else "costly at 0.20",
                            "median_corrective_share_not_seen", qc["median"], qc["q1"], qc["q3"],
                            "quartiles over proposal-draws", NDRAWS[f]])
    rows = build_rows(A, lab)
    n27 = {}
    with open(IN27B["n27_rows"], encoding="utf-8") as fh:
        for x in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            if x["f"] == "0.00":
                n27[x["item_id"]] = x
    z27 = [x for x in rows if x["f"] == "0.00"]
    check("f = 0 rows cover N27's f = 0 rows", len(z27) == len(n27) == 1356, len(n27))
    for x in z27:
        y = n27[x["item_id"]]
        for col in ("p_cert", "p_certm", "p_rel1", "p_rel2", "p_abs", "second_price",
                    "disp_cert", "disp_cert_sp", "disp_certm", "disp_rel1", "disp_rel2",
                    "disp_abs", "k_stage", "k_term", "n_K", "n_unknown", "n_window", "m_lo",
                    "m_hi", "label020", "label010"):
            check("f = 0 row equals N27's f = 0 row ({})".format(col), str(x[col]) == y[col],
                  (x["item_id"], col, x[col], y[col]))
    say("f = 0 rows equal N27's f = 0 rows in every price, second price and disposition")
    second_path(A, rows, T, lab)
    check("self-test: at least ten numbers compared", len(SELF) >= 10, len(SELF))
    check("self-test: every number equal on the second code path", all(x[3] for x in SELF),
          [x for x in SELF if not x[3]][:5])
    adapter1 = adapter_hashes()
    frozen1 = frozen_hashes()
    check("nothing under code/l1adapter/ changed during the run", adapter1 == ADAPTER0)
    check("the frozen files unchanged", frozen1 == _FROZEN0)
    write_summary(A, T, S3, B4, D5, L6, lab, X, CH)
    n_reused = n20.NCHECK[0] + n16.NCHECK[0] + n18.NCHECK[0] + len(n13.CHECKS)
    wall = time.time() - A["t_start"]
    n_boards = sum(len(x["boards"]) for x in A["rep"].values())
    if A["from_stored"]:
        md("## Runtime", "",
           "Rebuilt from the stored replay of the official fresh run "
           "(results/n27_withheld_orders/replay_n27b.jsonl, sha256 {}, {} proposals, {} distinct "
           "boards, each priced with and without the proposal, on {} windows); the replay itself "
           "ran on cores 8 and 9 with {} worker processes and one thread each (addendum_n27b.md). "
           "Deterministic replays, so no number depends on the wall time; this rebuild took "
           "{:.0f} s.".format(A["stored_sha"], len(A["rep"]), n_boards, len(A["tasks"]), WORKERS,
                              wall), "")
    else:
        md("## Runtime", "",
           "Replay {:.0f} s for {} proposals ({} distinct boards, each priced with and without "
           "the proposal) on {} windows ({} worker processes on cores 8 and 9, one thread each; "
           "deterministic replays, so no number depends on the wall time); total {:.0f} s.".format(
               A["wall_rep"], len(A["rep"]), n_boards, len(A["tasks"]), WORKERS, wall), "")
    msg = ("[n27b] {} macros, {} assertions passed (+{} in the reused functions); self-test {} of "
           "{} equal; {} boards; replay {:.0f}s, total {:.0f}s".format(
               len(NAMES), NCHECK[0], n_reused, sum(1 for x in SELF if x[3]), len(SELF),
               n_boards, A["wall_rep"], wall))
    NUM["macros"] = VAL
    NUM["self_test"] = [list(x) for x in SELF]
    NUM["version"] = VERSION
    json_text = json.dumps(jsonable(NUM), indent=1, default=str) + "\n"
    check("numbers file serialises and reads back", json.loads(json_text)["version"] == VERSION)
    if A["selftest_only"]:
        dev = os.environ.get("N27B_DEV_SUMMARY")       # a copy outside the project, for test runs
        if dev and not str(Path(dev).resolve()).startswith(str(ROOT)):
            Path(dev).write_text("\n".join(MD) + "\n", encoding="utf-8")
            Path(dev + ".tex").write_text("\n".join(LINES) + "\n", encoding="utf-8")
        print(msg + " (self-test mode: nothing written to the project)")
        return 0
    inputs = OrderedDict((k, input_sha256(k, p)) for k, p in IN27B.items())
    for nm in ("n27b_withheld_all.py", "n20_stratum_abs.py", "n11_decision_time.py",
               "n8_causal.py"):
        inputs["code " + nm] = sha256_file(SCRIPTS_DIR / nm)
    if A["from_stored"]:
        inputs["stored replay replay_n27b.jsonl"] = A["stored_sha"]
    MD.extend(["## Inputs", ""] + ["- {} sha256 {}".format(k, v) for k, v in inputs.items()]
              + [""])
    MD.append("{} assertions passed in n27b (plus {} in the reused functions); self-test {} of {} "
              "numbers equal on the second code path; {} macros.".format(
                  NCHECK[0], n_reused, sum(1 for x in SELF if x[3]), len(SELF), len(NAMES)))
    write_rows(rows)
    with open(OUT_FIG, "w", newline="", encoding="utf-8") as fh:
        fh.write("# N27b ({}) figure data: one row per level, delta, design and quantity; value "
                 "with its lower and upper end (see the column interval)\n".format(VERSION))
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["f", "delta", "design", "quantity", "value", "lo", "hi", "interval",
                    "draws"])
        for row in fig:
            w.writerow([row[0], row[1], row[2], row[3]] + [fx(v) for v in row[4:7]] + row[7:])
    with open(OUT_REPLAY, "w", encoding="utf-8") as fh:
        for i, x in A["rep"].items():
            fh.write(json.dumps(x, sort_keys=True) + "\n")
    OUT_ADAPTER.write_text(json.dumps({"before": ADAPTER0, "after": adapter1,
                                       "frozen_before": _FROZEN0, "frozen_after": frozen1},
                                      indent=1) + "\n", encoding="utf-8")
    NUM["inputs"] = inputs
    OUT_JSON.write_text(json.dumps(jsonable(NUM), indent=1, default=str) + "\n",
                        encoding="utf-8")
    OUT_TEX.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    shutil.copyfile(OUT_TEX, OUT_MANU)
    check("manuscript copy byte-identical", OUT_MANU.read_bytes() == OUT_TEX.read_bytes())
    OUT_MD.write_text("\n".join(MD) + "\n", encoding="utf-8")
    print(msg)
    return 0


# --------------------------------------------------------------------------- #
# Rows and the second code path                                                #
# --------------------------------------------------------------------------- #
ROW_HEAD = ["item_id", "instance_id", "stratum", "primary_class", "family", "edit_type",
            "label020", "label010", "m_lo", "m_hi", "f", "draw", "n_window", "n_unknown", "n_K",
            "n_H", "n_withheld", "n_withheld_planned", "share_not_seen", "share_K_withheld",
            "n_corr_window", "corr_share_not_seen", "h_share", "board_as_f0", "k_stage",
            "k_term", "p_cert", "p_certm", "p_rel1", "p_rel2", "p_abs", "second_price",
            "disp_cert", "disp_cert_sp", "disp_certm", "disp_rel1", "disp_rel2", "disp_abs"]


def build_rows(A, lab):
    out = []
    for key, x in A["R"].items():
        r, v, p = x["r"], x["v"], x["board"]["p"]
        out.append(OrderedDict([
            ("item_id", x["item_id"]), ("instance_id", r["instance_id"]),
            ("stratum", r["stratum"]), ("primary_class", r["primary_class"]),
            ("family", r["family"]), ("edit_type", r["split"]),
            ("label020", lab[0.20][x["item_id"]]), ("label010", lab[0.10][x["item_id"]]),
            ("m_lo", fx(r["lo"])), ("m_hi", fx(r["hi"])), ("f", "{:.2f}".format(x["f"])),
            ("draw", x["draw"]), ("n_window", x["n_window"]), ("n_unknown", x["n_unknown"]),
            ("n_K", x["n_K"]), ("n_H", x["n_H"]), ("n_withheld", x["n_w"]),
            ("n_withheld_planned", x["n_w_pm"]), ("share_not_seen", fx(x["unseen"])),
            ("share_K_withheld", fx(x["k_share"])), ("n_corr_window", x["n_corr_window"]),
            ("corr_share_not_seen", fx(x["unseen_corr"])), ("h_share", fx(x["h_share"])),
            ("board_as_f0", int(x["n_w"] == 0)), ("k_stage", p["stage_cert"]),
            ("k_term", p["term_cert"]), ("p_cert", fx(v["pk"]["G-CERT"])),
            ("p_certm", fx(v["pk"]["G-CERT-M"])), ("p_rel1", fx(v["pk"]["D-REL1"])),
            ("p_rel2", fx(v["pk"]["D-REL2"])), ("p_abs", fx(v["pk"]["D-ABS"])),
            ("second_price", fx(v["g_orig"])), ("disp_cert", v["disp"]["Cert"]),
            ("disp_cert_sp", v["disp"]["CertSP"]), ("disp_certm", v["disp"]["CertM"]),
            ("disp_rel1", v["disp"]["RelOne"]), ("disp_rel2", v["disp"]["RelTwo"]),
            ("disp_abs", v["disp"]["Abs"])]))
    for row in out:
        check("row carries every column", list(row.keys()) == ROW_HEAD)
    return out


def write_rows(rows):
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        fh.write("# N27b ({}): one row per priced proposal of the direct benchmark (1,356), "
                 "level f and draw; the gate priced on the known board at t_d minus n_withheld "
                 "of the n_H candidate orders (unstarted, unnamed, not frozen, planned or "
                 "corrective; n_withheld_planned of them planned); labels (1 costly, 0 low-cost) "
                 "and the realised-cost interval are the stored ones; share_not_seen = "
                 "(n_unknown + n_withheld) / n_window; share_K_withheld = n_withheld / n_K; "
                 "corr_share_not_seen = (n_unknown + n_withheld - n_withheld_planned) / "
                 "n_corr_window, the corrective orders of the window; p_<design> = "
                 "price on the thinned board against the no-proposal run on the same board; "
                 "second_price = (objective on the original values minus the no-proposal "
                 "bound) / max(that bound, 1); disp = referred, applied or refused\n".format(
                     VERSION))
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(ROW_HEAD)
        for row in rows:
            w.writerow([row[h] for h in ROW_HEAD])


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


def second_path(A, rows, T, lab):
    """Counts recomputed from the rows with a label rule and flags written here."""
    def flo(s):
        return None if s == "" else float(s)

    def label(x, d):
        lo, hi = flo(x["m_lo"]), flo(x["m_hi"])
        return 1 if lo > d else (0 if hi <= d else None)

    def cert(x):
        if x["k_stage"] != "qual" or x["k_term"] == "execution_failed" or x["p_cert"] == "":
            return "refused"
        return "referred" if flo(x["p_cert"]) > 0.20 else "applied"

    def cert_sp(x):
        c = cert(x)
        if c != "applied":
            return c
        return ("referred" if x["edit_type"] == "field_changing" and flo(x["second_price"]) > 0.20
                else "applied")

    by = defaultdict(list)
    for x in rows:
        by[(x["f"], int(x["draw"]))].append(x)
    insts = set(A["boot"].index)               # the 60 instance clusters of the suite
    check("self-test: the rows cover only bootstrap clusters",
          {x["instance_id"] for x in rows} <= insts)
    for dl in DELTAS.values():
        for ftok, f in LEVELS.items():
            fk = "{:.2f}".format(f)
            for gate, fn in (("Cert", cert), ("CertSP", cert_sp)):
                refs, apps, lows = [], [], []
                for d in range(NDRAWS[f]):
                    sel = by[(fk, d)]
                    c = [x for x in sel if label(x, dl) == 1]
                    lw = [x for x in sel if label(x, dl) == 0]
                    refs.append(sum(fn(x) == "referred" for x in c))
                    apps.append(sum(fn(x) == "applied" for x in c))
                    lows.append(sum(fn(x) == "referred" for x in lw))
                o = T[(dl, f, gate)]
                for nm, a, b in (("costly referred", mean_rng(refs), o["c_referred"]),
                                 ("costly applied", mean_rng(apps), o["c_applied"]),
                                 ("low-cost referred", mean_rng(lows), o["l_referred"])):
                    SELF.append(("dispositions", "delta {:.2f} f {} {} {}".format(dl, fk, gate, nm),
                                 b, all(abs(u - w) < 1e-12 for u, w in zip(a, b))))
            if dl == 0.20 and f == 1.0:
                lw = [x for x in by[(fk, 0)] if label(x, dl) == 0]
                lo, hi = boot_ci_here([x["instance_id"] for x in lw],
                                      [cert(x) == "referred" for x in lw], insts)
                o = T[(dl, f, "Cert")]
                SELF.append(("bootstrap", "f 1.00 low-cost share interval",
                             (pctv(o["l_lo0"]), pctv(o["l_hi0"])),
                             (pctv(lo), pctv(hi)) == (pctv(o["l_lo0"]), pctv(o["l_hi0"]))))
    # the share not seen at f = 1 from the counts in the rows
    for x in by[("1.00", 0)][:200]:
        u = (int(x["n_unknown"]) + int(x["n_withheld"])) / int(x["n_window"])
        uc = ((int(x["n_unknown"]) + int(x["n_withheld"]) - int(x["n_withheld_planned"]))
              / int(x["n_corr_window"]))
        uk = int(x["n_withheld"]) / int(x["n_K"])
        if (abs(u - float(x["share_not_seen"])) > 1e-12 or int(x["n_withheld"]) != int(x["n_H"])
                or abs(uc - float(x["corr_share_not_seen"])) > 1e-12
                or abs(uk - float(x["share_K_withheld"])) > 1e-12):
            SELF.append(("share", "share not seen of " + x["item_id"], x["share_not_seen"], False))
    SELF.append(("share", "share not seen, share of K withheld and corrective share not seen "
                 "at f = 1 recomputed from the counts (200 rows)", "ok", True))


# --------------------------------------------------------------------------- #
# Summary                                                                      #
# --------------------------------------------------------------------------- #
def write_summary(A, T, S3, B4, D5, L6, lab, X, CH):
    R = A["R"]
    head = ["# N27b: the gate on a known board from which planned and corrective orders are "
            "withheld ({})".format(VERSION), "",
            "Generated by `code/scripts/n27b_withheld_all.py` on cores 8 and 9 (one thread per "
            "process): deterministic replays of the direct benchmark's known-board pricing "
            "(n11_decision_time.gen_price, no solver, no time budget), no model call, no GPU. "
            "Post hoc analysis. Frozen designs: `results/n27_withheld_orders/design.md` (sha256 "
            "{}) and `results/n27_withheld_orders/design_n27b_2026-11-11.md` (sha256 {}), "
            "addendum `results/n27_withheld_orders/addendum_n27b.md`.".format(DESIGN_SHA,
                                                                            DESIGN_B_SHA), "",
            "This variant departs from the benchmark's premise that the maintenance calendar is "
            "known at the decision instant. It stresses the information the gate is given and "
            "makes no claim about a site.", "",
            "At level f the gate prices each of the 1,356 priced proposals on the known board K "
            "at t_d minus floor(f |H2| + 0.5) of the candidate orders H2 (not started, queued or "
            "on the calendar, planned or corrective, named neither by the instruction nor by the "
            "proposal, not frozen), drawn at random (five draws at f = 0.25, 0.50, 0.75, one at "
            "f = 1, which withholds H2). The labels are the stored ones. Refused = stopped by the "
            "schema or feasibility check on the thinned board, or ended in an instrument fault. "
            "Mean and range are over draws. Low-cost shares carry the n2 cluster bootstrap "
            "interval on draw 0.", "",
            "## 0. Checks before any thinned-board number (all run-fatal, all passed)", "",
            "- Frozen files: {} (sha256 prefixes, before and after). Every .py file under "
            "code/l1adapter/ unchanged.".format(", ".join("{} {}".format(k, _FROZEN0[k][:12])
                                                          for k in FROZEN)),
            "- n16.section0, n18.section0 and n20.section0 pass; the frozen counts hold (186 "
            "costly at 0.20, 168 referred, 18 applied, 0 with the second price, 15 and 22 "
            "low-cost referred of 1,170; 208, 25 and 6 at 0.10); N18's later share of the costly "
            "proposals (median 8.6%, maximum 38.5%) is reproduced.",
            "- f = 0 for all 1,356 proposals: the replayed known board and no-proposal run equal "
            "the stored census (terminals, codes, objectives, bound, certificate, D-REL2 "
            "reference; no-proposal objective, bound and gap; window counts), and every "
            "design's price and flag, the second price and its flag equal the stored records. "
            "Largest differences: " + "; ".join("{} {:.1e}".format(k, v) for k, v in sorted(
                MAXDIFF.items(), key=lambda t: -t[1])[:4]) + ".",
            "- f = 0 rows equal N27's f = 0 rows (analysis/N27_rows.csv) in every price, the "
            "second price and every disposition.",
            "- The probe (block P) passes.", ""]
    MD[:0] = head
    for dtok, dl in DELTAS.items():
        md("## 1-2. Dispositions by level, delta = {:.2f}".format(dl), "")
        for gate in GATES:
            if gate == "CertM":
                md("Other designs (each at its own threshold):", "")
            body = []
            for f in LEVELS.values():
                o = T[(dl, f, gate)]
                body.append([
                    "{:.2f}".format(f), NDRAWS[f],
                    "{} [{}, {}]".format(m1(o["c_referred"][0]), o["c_referred"][1],
                                         o["c_referred"][2]),
                    "{} [{}, {}]".format(m1(o["c_applied"][0]), o["c_applied"][1],
                                         o["c_applied"][2]),
                    "{} [{}, {}]".format(m1(o["c_refused"][0]), o["c_refused"][1],
                                         o["c_refused"][2]),
                    "{} ({} / {} / {})".format(o["flip_any"], o["flip_ra"], o["flip_ar"],
                                               o["flip_rf"]),
                    "{} [{}, {}]".format(m1(o["l_referred"][0]), o["l_referred"][1],
                                         o["l_referred"][2]),
                    "{} [{}, {}]".format(pct1(o["l_share0"]), pct1(o["l_lo0"]),
                                         pct1(o["l_hi0"]))])
            md("### {} ({} costly, {} low-cost)".format(GATES[gate], T[(dl, 0.0, gate)]["n_costly"],
                                                        T[(dl, 0.0, gate)]["n_low"]), "")
            md_table(["f", "draws", "costly referred, mean [min, max]",
                      "costly applied, mean [min, max]", "costly refused, mean [min, max]",
                      "costly whose disposition differs from f = 0 in some draw (referred -> "
                      "applied / applied -> referred / refused)",
                      "low-cost referred, mean [min, max]",
                      "low-cost share, draw 0 [95% CI]"], body)
    md("## 3. By edit type and stratum (delta = 0.20; mean over draws)", "")
    for gate in MAIN_GATES:
        body = []
        for (dl, dim, tok, f, g), o in S3.items():
            if dl != 0.20 or g != gate:
                continue
            body.append([dim, tok, "{:.2f}".format(f), o["n"], o["n_costly"],
                         m1(o["c_ref"][0]), m1(o["c_app"][0]),
                         "{} [{}, {}]".format(m1(o["c_app"][0]), o["c_app"][1], o["c_app"][2]),
                         o["n_low"], m1(o["l_ref"][0])])
        md("### " + GATES[gate], "")
        md_table(["split", "group", "f", "priced", "costly", "costly referred", "costly applied",
                  "costly applied [min, max]", "low-cost", "low-cost referred"], body)
    md("Delta = 0.10 by group: analysis/N27b_numbers.json, key by_group.", "")
    md("## 4. Costly proposals by band of the share not seen (proposal-draws)", "")
    for dl in DELTAS.values():
        body = []
        for f in LEVELS.values():
            cell = B4[(dl, f)]
            body.append(["{:.2f}".format(f)] + ["{} ({} prop.): {} / {}".format(
                c["pairs"], c["props"], c["ref"], c["ref_sp"]) for c in cell.values()])
        md("### delta = {:.2f}: proposal-draws (distinct proposals): referred by the certificate "
           "/ with the second price".format(dl), "")
        md_table(["f"] + [v[2] for v in BANDS.values()], body)
    md("## 5. Distributions", "")
    body = []
    for pop in ("Priced", "Costly"):
        q, qh = D5[(pop, "h_share")], D5[(pop, "n_H")]
        body.append([pop, "{} [{}, {}], max {}".format(pct1(q["median"]), pct1(q["q1"]),
                                                       pct1(q["q3"]), pct1(q["max"])),
                     "{} [{}, {}], max {}".format(m1(qh["median"]), m1(qh["q1"]), m1(qh["q3"]),
                                                  int(qh["max"])), D5[(pop, "h_zero")]])
    md_table(["proposals", "|H2| / |K|, median [quartiles], max",
              "|H2|, median [quartiles], max", "proposals with |H2| = 0"], body)
    body = []
    for pop in ("Priced", "Costly"):
        for f in LEVELS.values():
            q, qa, qw = D5[(pop, "unseen", f)], D5[(pop, "added", f)], D5[(pop, "n_w", f)]
            qk, qp = D5[(pop, "k_share", f)], D5[(pop, "pm_share_w", f)]
            body.append([pop, "{:.2f}".format(f), "{} [{}, {}], max {}".format(
                pct1(q["median"]), pct1(q["q1"]), pct1(q["q3"]), pct1(q["max"])),
                "{} [{}, {}], max {}".format(pct1(qk["median"]), pct1(qk["q1"]), pct1(qk["q3"]),
                                             pct1(qk["max"])),
                "{} (max {})".format(pct1(qa["median"]), pct1(qa["max"])),
                "{} (max {})".format(m1(qw["median"]), int(qw["max"])), pct1(qp["median"])])
    md_table(["proposals", "f", "share of the window not seen, median [quartiles], max",
              "share of K withheld, median [quartiles], max",
              "rise of the share not seen over f = 0, median (max), points of the window",
              "orders withheld, median (max)", "planned share of the withheld orders, median"],
             body)
    md("## 5b. Composition of the known board (descriptive)", "",
       "Shares of K at t_d, median [quartiles] over proposals, with the median count.", "")
    body = []
    for pop in ("Priced", "Costly"):
        for tok, txt in (("Running", "running"), ("QueuedPlanned", "queued planned orders"),
                         ("CalendarPlanned", "planned orders on the calendar"),
                         ("QueuedCorrective", "queued corrective orders"),
                         ("NamedFrozen", "unstarted orders named or frozen"),
                         ("Candidates", "candidates H2")):
            q, qn = X[(pop, "comp", tok)], X[(pop, "compn", tok)]
            body.append([pop, txt, "{} [{}, {}]".format(pct1(q["median"]), pct1(q["q1"]),
                                                        pct1(q["q3"])), m1(qn["median"]),
                         int(qn["max"])])
        q = X[(pop, "planned_share")]
        body.append([pop, "planned orders, both kinds", "{} [{}, {}], min {}".format(
            pct1(q["median"]), pct1(q["q1"]), pct1(q["q3"]), pct1(q["min"])), "", ""])
    md_table(["proposals", "part of K", "share of K, median [quartiles]", "count, median",
              "count, max"], body)
    md("## 5c. Share of the window's corrective orders not seen (descriptive)", "",
       "(n_unknown + withheld corrective orders) / corrective orders of the window. Every "
       "order that arrives after t_d is corrective, since planned orders after t_d are on the "
       "calendar, so this is the share of the corrective workload the gate does not see.", "")
    body = []
    for pop in ("Priced", "Costly"):
        for f in LEVELS.values():
            q = X[(pop, "unseen_corr", f)]
            body.append([pop, "{:.2f}".format(f), "{} [{}, {}], max {}".format(
                pct1(q["median"]), pct1(q["q1"]), pct1(q["q3"]), pct1(q["max"]))])
    md_table(["proposals", "f", "corrective share not seen, median [quartiles], max"], body)
    for dl in DELTAS.values():
        body = []
        for f in LEVELS.values():
            cell = X[("bands_corr", dl, f)]
            body.append(["{:.2f}".format(f)] + ["{} ({} prop.): {} / {}".format(
                c["pairs"], c["props"], c["ref"], c["ref_sp"]) for c in cell.values()])
        md("### delta = {:.2f}: costly proposal-draws by band of the corrective share not seen "
           "(distinct proposals): referred by the certificate / with the second price".format(dl),
           "")
        md_table(["f"] + [v[2] for v in BANDS.values()], body)
    md("## 6b. Movement of the certificate price (descriptive)", "",
       "Per proposal, the largest absolute change of the certificate price from f = 0 over all "
       "draws and levels; and, per level, the smallest price among the costly proposals the "
       "certificate refers at f = 0 and the largest among those it applies.", "")
    for dl in DELTAS.values():
        mv = X[("move", dl)]
        body = []
        for pop in ("Priced", "Costly"):
            q = mv[pop]["q"]
            body.append([pop, mv[pop]["n"], mv[pop]["changed"], "{:.4f}".format(q["median"]),
                         "{:.4f}".format(q["q3"]), "{:.4f}".format(q["max"])])
        md("### delta = {:.2f}".format(dl), "")
        md_table(["proposals", "n", "price changes in some draw", "largest change, median",
                  "upper quartile", "max"], body)
        md_table(["f", "smallest price, costly referred at f = 0",
                  "largest price, costly applied at f = 0"],
                 [["{:.2f}".format(f), p3(mv[("ref_min", f)]), p3(mv[("app_max", f)])]
                  for f in LEVELS.values()])
    md("## 6. Costly proposals whose disposition changes at some level", "")
    body = []
    for dl in DELTAS.values():
        for gate in GATES:
            o = CH[(dl, gate)]
            body.append(["{:.2f}".format(dl), GATES[gate], o["n"], o["ra"], o["ar"], o["rf"],
                         "none" if o["first_level"] is None else "{:.2f}".format(o["first_level"]),
                         o["first_n"], pct1(o["first_unseen_min"]), pct1(o["first_k_min"]),
                         pct1(o["unseen_min"]), pct1(o["k_min"])])
    md("### First change, by delta and design", "")
    md_table(["delta", "design", "costly that change", "referred -> applied",
              "applied -> referred", "refused in some draw", "lowest level with a change",
              "costly changing there", "smallest share not seen there",
              "smallest share of K withheld there", "smallest share not seen, any level",
              "smallest share of K withheld, any level"], body)
    md("Macros on the costly proposals whose certificate disposition changes at delta = 0.20: "
       + ", ".join("\\" + n for n in X["changed_macros"]) + ".", "")
    code = {"referred": "R", "applied": "A", "refused": "F"}
    for dl in DELTAS.values():
        body = []
        for i in L6[dl]:
            r = A["R"][(i, 0.0, 0)]["r"]
            cells = []
            for f in LEVELS.values():
                parts_ = []
                for d in range(NDRAWS[f]):
                    x = R[(i, f, d)]
                    parts_.append("{}/{} {}{} ({:.0%})".format(
                        p3(x["v"]["pk"]["G-CERT"]), p3(x["v"]["g_orig"]),
                        code[x["v"]["disp"]["Cert"]], code[x["v"]["disp"]["CertSP"]],
                        x["unseen"]))
                cells.append(", ".join(parts_))
            body.append([i, r["primary_class"], r["family"], r["split"],
                         "{:.3f}-{:.3f}".format(r["lo"], r["hi"]),
                         A["R"][(i, 0.0, 0)]["n_H"]] + cells)
        md("### delta = {:.2f}: {} costly proposals whose disposition under the certificate or "
           "the certificate with the second price changes".format(dl, len(L6[dl])), "",
           "Per draw: certificate price / second price, dispositions under the certificate and "
           "with the second price (R referred, A applied, F refused), share of the window not "
           "seen in brackets.", "")
        md_table(["proposal", "class", "family", "edit type", "realised cost", "|H2|"]
                 + ["f = {:.2f}".format(f) for f in LEVELS.values()], body)
    md("## 7. Self-test (second code path)", "",
       "Counts recomputed from the rows of analysis/N27b_rows.csv with a label rule, the "
       "certificate and second-price flags, and a bootstrap written in the script.", "")
    md_table(["block", "number", "value", "equal"],
             [[a, b, c, "yes" if d else "NO"] for a, b, c, d in SELF])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
