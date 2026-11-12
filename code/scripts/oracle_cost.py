#!/usr/bin/env python
"""N1: an oracle bracket on the best achievable weighted tardiness of every
instruction's relaxed adjusted instance.

WHY THIS EXISTS
---------------
Every gate in the study prices a proposal against a reference it can compute
cheaply.  The certificate divides by an analytic lower bound (LB2); the
deterministic rule D-REL2 divides by one ATC dispatch of the same adjusted
fields.  Neither reference is the best schedule the adjusted instance admits,
so neither gate's price can be checked against the other's.  This script
produces the third quantity that both can be checked against: for every suite
item and every recorded proposal that reached a schedule, a bracket
[lower, upper] on

    OPT_relaxed = min over feasible schedules of  sum_j w_j (C_j - d_j)^+

on the RELAXED adjusted instance.  "Relaxed" means the fields the operations
install are applied (priority, weight, due date, release) and every dispatch
constraint is dropped (pins, precedence edges, freezes, batch chains, and the
episode's standing frozen set).  Those constraints only remove schedules, so
OPT_relaxed is at most the objective of any schedule the proposal can execute.
The N2 analysis reads the brackets; this script only produces them.

FOUR LAUNCH QUESTIONS (the project's standing experiment rules), answered before the run
---------------------------------------------------------------------------------
1. PURPOSE.  The brackets are the label set of the revised benchmark: an
   instruction's oracle cost is its executed objective minus OPT_relaxed, read
   off a bracket rather than off any gate's own reference.  They land in the
   pricing-accuracy table (signed error of each gate's price against the
   oracle), in the gate-price-versus-oracle-cost figure, and in the decision
   table's load boundary.
2. EXPECTED RESULT.  On the c10 replay stratum every trade proves optimal in
   about a second and the bracket closes to the grid resolution.  On the c09
   storm stratum the probe closed one instance to 0.2% width at 30 s per trade.
   On the c10 storm stratum CP-SAT finds no useful incumbent on the two largest
   trades, but the ATC schedule already sits on LB2 there, so the bracket is
   closed by ATC and LB2 together.  If instead wide brackets come back on a
   stratum, N2 reports pricing error only where the bracket is narrower than the
   error being measured and states the coverage as a number.  A bracket with
   lower > upper is a defect and aborts the run.
3. CONTAMINATION.  Output goes to results/oracle_v1/ only; nothing else under
   results/ or the manuscript folder is written.  The files are append-only JSONL and the
   run resumes from them: a trade already solved under the same fields is never
   solved again, and a budget-limited solve during which other processes took
   more than 10% of the pinned cores is dropped on resume and solved again.  CP-SAT is a timed job, so it runs on the
   exclusive core set 8-15 with 8 workers, one solve at a time; the affinity,
   the load average, the cpu_share and the foreign CPU share on those cores are
   recorded on every solve row.
4. DATA ACCURACY.  Instances are read from the instances_v10 snapshot only and
   every file is checked against code/scripts/instance_manifest_l1.json by the
   loader of code/scripts/suite_gate.py; a file outside the manifest aborts.
   The suite's SHA-256 is asserted.  Every suite item's executed objective is
   recomputed through the adapter and compared with the suite's stored
   wwt_adjusted to 1e-4; every proposal's ops are re-applied, and its logged
   objective is later required to sit above its bracket's lower end.

DECLARED DESIGN (fixed before the results were computed)
--------------------------------------------------------
DECOMPOSITION.  A technician serves only its own trade and, with the dispatch
constraints dropped, nothing couples two trades, so OPT_relaxed is the sum of
per-trade optima.  Each trade is bracketed on its own and the brackets add.
Only trades that contain an order whose fields differ from the baseline
instance are solved again; every other trade reuses the baseline instance's
row for that trade.

THE FIELD FINGERPRINT.  For an adjusted instance, the tuples
(order_id, release_bh, due_bh, weight, priority) of every order whose fields
differ from the baseline instance, sorted, serialised as compact JSON and
hashed with SHA-256.  The baseline instance has the fingerprint of the empty
list.  The per-trade fingerprint is the same hash over that trade's tuples
only.  A relaxed instance is rebuilt from the baseline plus its tuples, so two
proposals with the same fingerprint share one bracket.

THE LOWER BOUND, AND WHY THE SOLVER IS GIVEN A ROUNDED-DOWN GRID.  The Y1
CP-SAT model (``fmwos.cpsat.solve``, used unmodified) is integer on a
centi-business-hour grid.  It rounds processing times and releases UP and due
dates to NEAREST.  That grid is a restriction of the continuous problem, so
its best bound can exceed the continuous optimum (the probes saw 208.54
proved optimal on the grid against an ATC schedule of 208.46 in continuous
time).  Taking min(CP bound, best incumbent) repairs the visible cases but is
not a valid bound when no incumbent happens to sit below the grid optimum.
This script therefore hands the Y1 model a rounded-DOWN copy of each trade:

    p'_j = floor_c(p_j),   r'_j = floor_c(r_j),   d'_j = ceil_c(d_j)

where floor_c and ceil_c round to the 0.01 bh grid.  The values are exact grid
points, so the model's own roundings leave them unchanged (asserted).  For
every continuous feasible schedule with starts s_j, the grid starts
g_j = floor_c(s_j) are feasible for the rounded-down copy: g_j >= r'_j, and on
one technician s_a + p_a <= s_b gives
g_a + p'_a <= floor_c(s_a + p_a) <= g_b.  The grid completion is at most
floor_c(C_j) <= C_j and the grid due date is at least d_j, so every grid
tardiness term is at most the continuous one.  Hence the CP-SAT best bound on
the rounded-down copy is a valid lower bound on the continuous per-trade
optimum, with no grid slack to argue about.  The trade's lower end is
max(LB2_trade, CP bound); both are valid, so their maximum is.

THE UPPER BOUND.  Two incumbents per trade, each a feasible continuous
schedule scored on the adjusted fields with ``l1adapter.evaluate.wwt``:
(a) the ATC dispatch of the relaxed instance (``dispatch_baseline``, the Y1
dispatcher, rule atc, seed 0) restricted to the trade; (b) the CP-SAT
incumbent's technician assignment and sequence, re-timed in continuous time
(each order starts at max(its release, the previous order's end) in the
solver's order) and checked by the Y1 validator.  The trade's upper end is the
smaller of the two.  The whole-instance ``atc_total`` is recorded separately,
because on an instance without a standing frozen set it is the D-REL2
reference itself.

WHAT "PROVED" MEANS.  ``proved_all`` is true when every trade was either closed
by LB2 or had its rounded-down grid copy solved to OPTIMAL.  A proved trade can
still carry a small width: the grid optimum is a valid lower end, and the
re-timed grid schedule is a valid upper end, but the two differ by the grid's
resolution, and which of several tied grid optima the solver returns varies
between runs (multi-worker CP-SAT is not deterministic).  ``width_rel`` is
always reported; every bracket is valid whichever optimum was returned.

SHORTCUT.  A trade whose ATC objective already equals LB2_trade to 1e-9 bh is
closed without a solve (status CLOSED_BY_LB2).  This is exact, not a
heuristic: lower = upper.

WARM START.  The trade's ATC schedule is passed as ``warm_start``; the Y1 API
turns its assignments and starts into CP-SAT hints, never constraints.

BUDGET.  60 s per trade by default (``--budget``), 8 workers, one solve at a
time.  A trade that does not prove inside the budget keeps whatever bound and
incumbent the solver reached; when CP-SAT returns no incumbent the ATC
objective is the trade's upper end.

CPU SHARE AND CONTENTION.  Three numbers per solve: ``cpu_share`` over the
whole call (model build included, single-threaded Python), ``solve_cpu_share``
over the CP-SAT search call alone, both process CPU seconds / (wall seconds x
workers), and ``foreign_share``, the busy CPU time on the pinned cores (from
/proc/stat) minus this process's own, over (wall seconds x cores).  CP-SAT
does not keep 8 workers busy in presolve or on small models, so an
uncontended solve reads cpu_share 0.5 to 0.9 (smoke run, 2026-10-26) and
cpu_share alone cannot separate contention from the solver's own idling;
``foreign_share`` can.  A proved-optimal result does not depend on the CPU it
received, so only a budget-limited solve (status other than OPTIMAL) with
``foreign_share`` above 0.10 is flagged ``contended``; such a row is dropped on
resume and solved again.

PROPOSALS.  Every row of results/e1_eval_*/proposals.jsonl (78,000) is joined to
its row of the same directory's verdicts_G_CERT.jsonl by (instruction, mode,
thinking, repeat).  A proposal gets a fingerprint when its ops apply; it enters
the solve census only when it reached the quality stage, that is, when an
executed schedule exists.  Refusals, parse failures and schema blocks carry a
reason and no fingerprint.  An empty operation list that was applied executes
the baseline and carries the baseline fingerprint.

SUITE ITEMS.  Each item is mapped twice: its gold ops, and, where the class's
canonical proposal is a different field (literal_ops for V1/V2, trap_ops for
V4, forbidden_ops for V6), the canonical ops.  The executed objective of each is
recomputed exactly as l1suite/checks.py does (apply with the episode's frozen
seed and the ATC baseline, dispatch_adjusted at atc/0, wwt on the adjusted
fields) and compared with the suite's stored value where it stores one.

SELF-CHECKS (``--selfcheck``; any violation aborts with the row printed)
-----------------------------------------------------------------------
(a) On the first 10 instances of c10_replay_400, the whole-instance CP-SAT solve
    of the rounded-down copy (30 s, must prove OPTIMAL) equals the sum of the
    per-trade proved optima to 1e-6 bh.  The two solves see the same grid, so
    the allowed slack is zero; 1e-6 covers the division by 100 only.  The Y1
    default grid's optimum is printed beside it, with the best continuous
    incumbent, to show the size of the discretisation.
(b) On every bracket on disk: lower <= upper + 1e-6, lb2_total <= upper + 1e-6.
(c) On every item row: executed objective >= its bracket's lower - 1e-6.
(d) On every executed proposal: logged objective >= its bracket's lower - 1e-6.

OUTPUTS (results/oracle_v1/)
---------------------------
``trade_solves.jsonl``      one row per (instance, trade, trade fingerprint)
``brackets.jsonl``          one row per distinct relaxed instance
``items.jsonl``             every suite item -> fingerprints, executed objectives
                            (reused on resume when ``items.meta.json`` matches)
``proposals_index.jsonl``   every recorded proposal -> fingerprint or reason
``census.json``             the census, written by ``--census`` and ``--run``
``run_meta.json``           input digests, versions, affinity, arguments (this
                            launch; every launch is also appended to
                            ``run_meta_history.jsonl``)

On resume, the last row for a key wins in every JSONL file.

Run::

    taskset -c 8-15 python \\
        code/scripts/oracle_cost.py --census
    taskset -c 8-15 ... oracle_cost.py --run [--limit N] [--budget 60]
    taskset -c 8-15 ... oracle_cost.py --selfcheck

Version: l1-n1-oracle-cost-1
"""

from __future__ import annotations

import argparse
import datetime as _dt
import glob
import hashlib
import json
import math
import os
import platform
import socket
import sys
import time
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

VERSION = "l1-n1-oracle-cost-1"

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent.parent
CODE = ROOT / "code"
RESULTS = ROOT / "results"
OUT_DIR = RESULTS / "oracle_v1"

SNAPSHOT_ROOT = Path(((os.environ.get("L1_Y1_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "PaperY-FMScheduling")) + "/data/processed/instances_v10"))
DEFAULT_CORES = tuple(range(8, 16))
DEFAULT_WORKERS = 8
DEFAULT_BUDGET_S = 60.0
SELFCHECK_BUDGET_S = 30.0
SELFCHECK_N = 10

EPISODE_RULE = "atc"
EPISODE_SEED = 0
FIELD_OPS = frozenset({"set_priority", "reassign_window"})
FIELDS = ("release_bh", "due_bh", "weight", "priority")
FOREIGN_SHARE_MAX = 0.10
CLOSE_TOL_BH = 1e-9
CHECK_TOL_BH = 1e-6
ITEM_TOL_BH = 1e-4
FLOOR_BH = 1.0

#: The canonical proposal field per class (direct_guard_benchmark.CANONICAL_FIELD).
CANONICAL_FIELD = {
    "benign": "gold_ops",
    "V1": "literal_ops",
    "V2": "literal_ops",
    "V3": "gold_ops",
    "V4": "trap_ops",
    "V5": "gold_ops",
    "V6": "forbidden_ops",
}

#: Stored executed objective per (class, ops field), as l1suite wrote it.
SUITE_METRIC = {
    ("benign", "gold_ops"): "wwt_adjusted",
    ("V3", "gold_ops"): "wwt_adjusted",
    ("V6", "gold_ops"): "wwt_adjusted",
    ("V4", "gold_ops"): "wwt_gold_adjusted",
    ("V4", "trap_ops"): "wwt_trap_adjusted",
}

STRATA_ORDER = ("c10_replay_400", "c09_storm2_w80", "c10_storm2_w80")


# --------------------------------------------------------------------------- #
# Environment: threads, cores and the instance root, before anything heavy     #
# --------------------------------------------------------------------------- #
def parse_cores(text: str) -> tuple:
    out = set()
    for part in text.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a), int(b) + 1))
        elif part.strip():
            out.add(int(part))
    return tuple(sorted(out))


def setup_environment(cores: tuple, workers: int) -> None:
    """Pin the process, cap the thread pools, point the loader at the snapshot."""
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                "NUMEXPR_NUM_THREADS"):
        os.environ[var] = str(int(workers))
    os.sched_setaffinity(0, set(cores))
    got = tuple(sorted(os.sched_getaffinity(0)))
    if got != tuple(sorted(cores)):
        raise SystemExit("REFUSING TO RUN: affinity {} != requested {}".format(got, cores))
    env_root = os.environ.get("L1_INSTANCE_ROOT")
    if env_root and Path(env_root).resolve() != SNAPSHOT_ROOT.resolve():
        raise SystemExit("REFUSING TO RUN: L1_INSTANCE_ROOT={} is not the snapshot {}"
                         .format(env_root, SNAPSHOT_ROOT))
    os.environ["L1_INSTANCE_ROOT"] = str(SNAPSHOT_ROOT)
    sys.path.insert(0, str(CODE))
    sys.path.insert(0, str(SCRIPTS_DIR))


_MODS = {}


def mods():
    """Import the adapter, the bound, the gate loader and the Y1 model once."""
    if not _MODS:
        import suite_gate as sg
        from l1adapter import apply as apply_mod, dispatch as dispatch_mod, evaluate
        from l1adapter import errors as errors_mod
        import importlib
        lb2_mod = importlib.import_module("l1guard.lb2")
        from l1guard import tier1
        from ortools.sat.python import cp_model

        if Path(sg.INSTANCE_ROOT).resolve() != SNAPSHOT_ROOT.resolve():
            raise SystemExit("REFUSING TO RUN: suite_gate resolved INSTANCE_ROOT={}"
                             .format(sg.INSTANCE_ROOT))
        cpsat = tier1._cpsat()
        _MODS.update(sg=sg, apply=apply_mod, dispatch=dispatch_mod, evaluate=evaluate,
                     errors=errors_mod, lb2=lb2_mod, cpsat=cpsat, cp_model=cp_model)
        # l1guard.tier1 caps the thread pools at its own default on import;
        # restore the cap this run declared.
        workers = os.environ.get("L1_N1_WORKERS", str(DEFAULT_WORKERS))
        for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
            os.environ[var] = workers
    return _MODS


# --------------------------------------------------------------------------- #
# Small utilities                                                              #
# --------------------------------------------------------------------------- #
def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fp_of(tuples) -> str:
    rows = sorted([list(t) for t in tuples], key=lambda t: t[0])
    blob = json.dumps(rows, separators=(",", ":"), sort_keys=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


BASE_FP = fp_of([])


def read_jsonl(path: Path) -> list:
    if not path.is_file():
        return []
    out = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def append_jsonl(path: Path, row: dict) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def write_jsonl(path: Path, rows) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    os.replace(tmp, path)


def loadavg() -> list:
    with open("/proc/loadavg") as fh:
        return [float(x) for x in fh.read().split()[:3]]


_CLK_TCK = os.sysconf("SC_CLK_TCK")


def core_busy_s(cores) -> float:
    """Busy CPU seconds so far on ``cores`` (user+nice+system+irq+softirq+steal)."""
    want = {"cpu{}".format(c) for c in cores}
    busy = 0
    with open("/proc/stat") as fh:
        for line in fh:
            parts = line.split()
            if parts and parts[0] in want:
                v = [int(x) for x in parts[1:9]]
                busy += v[0] + v[1] + v[2] + v[5] + v[6] + v[7]
    return busy / float(_CLK_TCK)


def centi_floor(x: float) -> int:
    k = math.floor(float(x) * 100.0)
    while (k + 1) / 100.0 <= float(x):
        k += 1
    while k / 100.0 > float(x):
        k -= 1
    return int(k)


def centi_ceil(x: float) -> int:
    k = math.ceil(float(x) * 100.0)
    while (k - 1) / 100.0 >= float(x):
        k -= 1
    while k / 100.0 < float(x):
        k += 1
    return int(k)


def ops_changes_fields(ops) -> bool:
    return any(isinstance(o, dict) and o.get("op") in FIELD_OPS for o in (ops or []))


# --------------------------------------------------------------------------- #
# Instances: the snapshot, through the gate's own loader                       #
# --------------------------------------------------------------------------- #
class Store:
    """The 60 suite instances, their ATC baselines and baseline field tuples."""

    def __init__(self, suite: list):
        m = mods()
        sg = m["sg"]
        manifest = sg.instance_manifest()
        files = manifest.get("files", {})
        self.inst = {}
        self.path = {}
        self.stratum = {}
        self.baseline = {}
        self.base_fields = {}
        self.trade_of = {}
        self.trades = {}
        for item in suite:
            iid = item["instance"]["instance_id"]
            if iid in self.inst:
                continue
            path = sg.instance_path(item)  # verifies against the manifest
            rel = str(Path(path).resolve().relative_to(SNAPSHOT_ROOT.resolve()))
            if rel not in files:
                raise SystemExit("REFUSING TO RUN: {} is not in the instance manifest"
                                 .format(rel))
            if sha256_file(path) != files[rel]:  # belt and braces: the gate hashed it
                raise SystemExit("REFUSING TO RUN: {} hash mismatch".format(rel))
            with open(path, "r", encoding="utf-8") as fh:
                inst = json.load(fh)
            if inst["meta"]["id"] != iid:
                raise SystemExit("instance id mismatch: {} vs {}".format(inst["meta"]["id"], iid))
            for wo in inst["work_orders"]:
                w = float(wo["weight"])
                if w != round(w):
                    raise SystemExit("non-integer weight in {}: {}".format(iid, w))
            self.inst[iid] = inst
            self.path[iid] = str(path)
            self.stratum[iid] = item["instance"]["stratum"]
            self.baseline[iid] = m["dispatch"].dispatch_baseline(inst, EPISODE_RULE,
                                                                 seed=EPISODE_SEED)
            self.base_fields[iid] = {wo["id"]: tuple(wo[f] for f in FIELDS)
                                     for wo in inst["work_orders"]}
            self.trade_of[iid] = {wo["id"]: wo["trade"] for wo in inst["work_orders"]}
            self.trades[iid] = sorted({wo["trade"] for wo in inst["work_orders"]})

    def changed_tuples(self, iid: str, adjusted_instance: dict) -> list:
        base = self.base_fields[iid]
        out = []
        for wo in adjusted_instance["work_orders"]:
            cur = tuple(wo[f] for f in FIELDS)
            if cur != base[wo["id"]]:
                out.append((wo["id"],) + cur)
        out.sort(key=lambda t: t[0])
        return out

    def trade_fps(self, iid: str, tuples: list) -> dict:
        by_trade = defaultdict(list)
        for t in tuples:
            by_trade[self.trade_of[iid][t[0]]].append(t)
        return {tr: (fp_of(by_trade[tr]) if by_trade.get(tr) else BASE_FP)
                for tr in self.trades[iid]}

    def relaxed(self, iid: str, tuples: list) -> dict:
        """The baseline instance with the changed field tuples written in."""
        base = self.inst[iid]
        repl = {t[0]: t for t in tuples}
        wos = []
        for wo in base["work_orders"]:
            t = repl.get(wo["id"])
            if t is None:
                wos.append(wo)
            else:
                w = dict(wo)
                for f, v in zip(FIELDS, t[1:]):
                    w[f] = v
                wos.append(w)
        out = dict(base)
        out["work_orders"] = wos
        return out


def load_suite() -> list:
    sg = mods()["sg"]
    got = sha256_file(sg.SUITE_PATH)
    if got != sg.SUITE_SHA256:
        raise SystemExit("REFUSING TO RUN: suite sha256 {} != {}".format(got, sg.SUITE_SHA256))
    rows = read_jsonl(Path(sg.SUITE_PATH))
    if len(rows) != 2000:
        raise SystemExit("suite has {} rows, expected 2000".format(len(rows)))
    for r in rows:
        e = r["episode"]
        if e["rule"] != EPISODE_RULE or int(e["seed"]) != EPISODE_SEED or float(e["t_bh"]) != 0.0:
            raise SystemExit("item {} declares an unexpected episode {}".format(r["item_id"], e))
    return rows


# --------------------------------------------------------------------------- #
# Census: items and proposals -> fingerprints                                  #
# --------------------------------------------------------------------------- #
def apply_ops(store: Store, iid: str, ops, frozen_seed, strict: bool):
    m = mods()
    return m["apply"].apply_proposal(
        store.inst[iid], {"operations": list(ops or [])}, frozen_seed=list(frozen_seed or []),
        baseline_schedule=store.baseline[iid], strict_schema=strict)


def map_items(store: Store, suite: list, execute: bool) -> list:
    """Every item -> gold (and canonical) fingerprints, optionally executed WT."""
    m = mods()
    out = []
    for item in suite:
        iid = item["instance"]["instance_id"]
        frozen = list(item["episode"]["frozen_seed"])
        cls = item["primary_class"]
        fields = ["gold_ops"]
        canon = CANONICAL_FIELD[cls]
        if canon != "gold_ops":
            fields.append(canon)
        row = OrderedDict(item_id=item["item_id"], primary_class=cls, instance_id=iid,
                          stratum=store.stratum[iid], has_frozen_seed=bool(frozen),
                          canonical_field=canon)
        for fld in fields:
            ops = item.get(fld) or []
            rec = OrderedDict(n_ops=len(ops), fingerprint=None, n_changed_orders=None,
                              changed=None, apply_error=None, executed_wt=None,
                              dispatch_error=None, suite_wt=None, suite_metric=None,
                              suite_match=None)
            try:
                adj = apply_ops(store, iid, ops, frozen, strict=True)
            except Exception as exc:  # adapter errors are data here
                rec["apply_error"] = type(exc).__name__
                row[fld] = rec
                continue
            tuples = store.changed_tuples(iid, adj.instance)
            rec["fingerprint"] = fp_of(tuples)
            rec["n_changed_orders"] = len(tuples)
            rec["changed"] = [list(t) for t in tuples]
            if execute:
                try:
                    sched = m["dispatch"].dispatch_adjusted(adj, EPISODE_RULE, EPISODE_SEED)
                    rec["executed_wt"] = m["evaluate"].wwt(adj, sched)
                except Exception as exc:
                    rec["dispatch_error"] = type(exc).__name__
                key = SUITE_METRIC.get((cls, fld))
                metrics = item.get("metrics") or {}
                if key and key in metrics:
                    rec["suite_metric"] = key
                    rec["suite_wt"] = metrics[key]
                    if rec["executed_wt"] is not None:
                        rec["suite_match"] = abs(rec["executed_wt"] - metrics[key]) <= ITEM_TOL_BH
            row[fld] = rec
        out.append(row)
    return out


def proposal_files() -> list:
    return sorted(glob.glob(str(RESULTS / "e1_eval_*" / "proposals.jsonl")))


def map_proposals(store: Store, suite: list) -> list:
    """Every recorded proposal -> fingerprint, or the reason it has none."""
    item_by_id = {r["item_id"]: r for r in suite}
    out = []
    apply_cache = {}
    for pf in proposal_files():
        d = Path(pf).parent
        vrows = read_jsonl(d / "verdicts_G_CERT.jsonl")
        vby = {}
        for v in vrows:
            k = (v["item_id"], v["mode"], v.get("thinking"), int(v["repeat"]))
            if k in vby:
                raise SystemExit("duplicate verdict key {} in {}".format(k, d))
            vby[k] = v
        n_rows = 0
        with open(pf, "r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                p = json.loads(line)
                n_rows += 1
                ex = p.get("extra") or {}
                key = (p["instruction_id"], p["mode"], ex.get("thinking"), int(ex.get("repeat", 0)))
                v = vby.get(key)
                if v is None:
                    raise SystemExit("proposal {} in {} has no verdict row".format(key, d))
                item = item_by_id[p["instruction_id"]]
                iid = item["instance"]["instance_id"]
                if p["instance_id"] != iid:
                    raise SystemExit("proposal {} names instance {}, suite says {}"
                                     .format(key, p["instance_id"], iid))
                pv = p.get("verdict") or {}
                terminal = pv.get("terminal") or v.get("terminal")
                stage = pv.get("stage_reached") or v.get("stage_reached")
                if pv and pv.get("terminal") != v.get("terminal"):
                    raise SystemExit("terminal mismatch for {} in {}: {} vs {}".format(
                        key, d, pv.get("terminal"), v.get("terminal")))
                obj = (pv.get("objective") or {}).get("wwt_adjusted_bh")
                cert_obj = (v.get("certificate") or {}).get("obj_bh")
                if obj is not None and cert_obj is not None and abs(obj - cert_obj) > ITEM_TOL_BH:
                    raise SystemExit("objective mismatch for {} in {}".format(key, d))
                if obj is None:
                    obj = cert_obj
                ops = p.get("parsed_ops")
                row = OrderedDict(
                    source=d.name, arm=ex.get("arm"), mode=p["mode"], thinking=ex.get("thinking"),
                    repeat=int(ex.get("repeat", 0)), instruction_id=p["instruction_id"],
                    primary_class=item["primary_class"], instance_id=iid,
                    stratum=store.stratum[iid], has_frozen_seed=bool(p.get("frozen_seed")),
                    terminal=terminal, stage_reached=stage, executed=(stage == "qual"),
                    logged_wt=obj, n_ops=None if ops is None else len(ops),
                    empty=(ops is not None and len(ops) == 0),
                    fingerprint=None, n_changed_orders=None, reason=None)
                parse_ok = (pv.get("parse") or {}).get("ok", v.get("parse_ok"))
                if terminal == "model_refused":
                    row["reason"] = "model_refused"
                elif terminal is None:
                    row["reason"] = "no_verdict"
                elif parse_ok is False:
                    row["reason"] = "parse_failure"
                elif terminal == "blocked_schema":
                    row["reason"] = "blocked_schema"
                if row["reason"] is not None:
                    out.append(row)
                    continue
                frozen = list(p.get("frozen_seed") or [])
                if frozen != list(item["episode"]["frozen_seed"]):
                    raise SystemExit("proposal {} frozen seed differs from the suite's".format(key))
                ck = (iid, json.dumps(ops, sort_keys=True), json.dumps(frozen))
                if ck not in apply_cache:
                    if not ops_changes_fields(ops) and stage == "qual":
                        # It applied in the run; no field edit means the baseline fields.
                        apply_cache[ck] = ("ok", [])
                    else:
                        try:
                            adj = apply_ops(store, iid, ops, frozen, strict=False)
                            apply_cache[ck] = ("ok", store.changed_tuples(iid, adj.instance))
                        except Exception as exc:
                            apply_cache[ck] = ("err", type(exc).__name__)
                status, val = apply_cache[ck]
                if status == "err":
                    row["reason"] = "apply_error:" + val
                    if row["executed"]:
                        raise SystemExit("proposal {} reached the quality stage but its ops "
                                         "do not apply now ({})".format(key, val))
                else:
                    row["fingerprint"] = fp_of(val)
                    row["n_changed_orders"] = len(val)
                    row["_tuples"] = val
                    if not row["executed"]:
                        row["reason"] = terminal  # applies, but no schedule was executed
                out.append(row)
        if n_rows != len(vrows):
            raise SystemExit("{}: {} proposals vs {} verdicts".format(d, n_rows, len(vrows)))
    return out


def build_census(store: Store, items: list, props: list) -> dict:
    """Distinct relaxed instances and trades needed, with their tuples."""
    need = OrderedDict()  # (iid, fp) -> {"tuples":..., "sources": Counter}
    for iid in store.inst:
        need[(iid, BASE_FP)] = {"tuples": [], "sources": Counter({"baseline": 1})}
    for row in items:
        for fld in ("gold_ops", row["canonical_field"]):
            rec = row.get(fld)
            if not rec or rec["fingerprint"] is None:
                continue
            k = (row["instance_id"], rec["fingerprint"])
            ent = need.setdefault(k, {"tuples": [tuple(t) for t in rec["changed"]],
                                      "sources": Counter()})
            ent["sources"]["item"] += 1
    for row in props:
        if not row["executed"] or row["fingerprint"] is None:
            continue
        k = (row["instance_id"], row["fingerprint"])
        ent = need.setdefault(k, {"tuples": list(row["_tuples"]), "sources": Counter()})
        ent["sources"]["proposal"] += 1
    return need


def census_summary(store: Store, need: dict, items: list, props: list) -> dict:
    by_src = Counter()
    for (iid, fp), ent in need.items():
        if fp == BASE_FP:
            continue
        if ent["sources"].get("item"):
            by_src["adjusted_from_items"] += 1
        if ent["sources"].get("proposal"):
            by_src["adjusted_from_proposals"] += 1
        if ent["sources"].get("proposal") and not ent["sources"].get("item"):
            by_src["adjusted_from_proposals_only"] += 1
    trades_needed = set()
    trades_base = set()
    per_stratum = Counter()
    for (iid, fp), ent in need.items():
        tfps = store.trade_fps(iid, ent["tuples"])
        for tr, tfp in tfps.items():
            if tfp == BASE_FP:
                trades_base.add((iid, tr))
            else:
                if (iid, tr, tfp) not in trades_needed:
                    per_stratum[store.stratum[iid]] += 1
                trades_needed.add((iid, tr, tfp))
        if fp != BASE_FP:
            per_stratum["brackets:" + store.stratum[iid]] += 1
    reasons = Counter()
    for r in props:
        reasons[r["reason"] or ("ok_executed" if r["executed"] else "ok")] += 1
    item_err = Counter()
    for row in items:
        for fld in ("gold_ops", row["canonical_field"]):
            rec = row.get(fld)
            if rec and rec["apply_error"]:
                item_err["{}:{}:{}".format(row["primary_class"], fld, rec["apply_error"])] += 1
    return {
        "distinct_baseline_instances": len(store.inst),
        "distinct_adjusted_field_instances": sum(1 for k in need if k[1] != BASE_FP),
        **dict(by_src),
        "baseline_trades": len(trades_base),
        "adjusted_trades_to_resolve": len(trades_needed),
        "per_stratum": dict(sorted(per_stratum.items())),
        "proposals_total": len(props),
        "proposals_executed": sum(1 for r in props if r["executed"]),
        "proposals_executed_empty": sum(1 for r in props if r["executed"] and r["empty"]),
        "proposal_reasons": dict(sorted(reasons.items())),
        "item_apply_errors": dict(sorted(item_err.items())),
        "items_with_frozen_seed": sum(1 for r in items if r["has_frozen_seed"]),
    }


def estimate_wall(store: Store, need: dict, budget: float, solved: dict) -> dict:
    """Projected solve wall: closed trades cost nothing, others by size or history.

    Needs one ATC dispatch per distinct relaxed instance, so it is not free.
    ``solved`` maps (iid, trade) -> wall_s of a baseline solve already on disk.
    """
    m = mods()

    # Per-trade solve wall by trade size, calibrated on the smoke run of
    # 2026-10-26 (rounded-down grid, ATC warm start, 8 workers): 355 orders 0.7 s,
    # 598-642 orders 3-6 s, 2,837 orders 40 s.  Sizes above 1,500 are charged
    # the full budget.
    buckets = ((150, 0.1), (400, 1.0), (700, 8.0), (1500, 30.0))

    def by_size(n):
        for cap_n, sec in buckets:
            if n <= cap_n:
                return min(sec, budget)
        return budget

    def bucket_name(n):
        for cap_n, _sec in buckets:
            if n <= cap_n:
                return "<={}".format(cap_n)
        return ">1500"

    seen = set()
    total = 0.0
    total_cap = 0.0
    n_closed = n_open = 0
    per_stratum = Counter()
    size_hist = Counter()
    for (iid, fp), ent in need.items():
        tfps = store.trade_fps(iid, ent["tuples"])
        todo = [tr for tr, tfp in tfps.items()
                if (iid, tr, tfp) not in seen and (fp == BASE_FP or tfp != BASE_FP)]
        if not todo:
            continue
        relaxed = store.relaxed(iid, ent["tuples"])
        atc = m["dispatch"].dispatch_baseline(relaxed, EPISODE_RULE, seed=EPISODE_SEED)
        lbd = m["lb2"].lb2_detail(relaxed)["per_trade"]
        atc_t = trade_wwt(relaxed, atc)
        n_t = Counter(wo["trade"] for wo in relaxed["work_orders"])
        for tr in todo:
            seen.add((iid, tr, tfps[tr]))
            lb = lbd.get(tr, {}).get("bound", 0.0)
            if atc_t.get(tr, 0.0) <= lb + CLOSE_TOL_BH:
                n_closed += 1
                continue
            n_open += 1
            size_hist["{}:{}".format(store.stratum[iid], bucket_name(n_t[tr]))] += 1
            est = solved.get((iid, tr))
            est = by_size(n_t[tr]) if est is None else est
            total += est
            total_cap += budget
            per_stratum[store.stratum[iid]] += est
    return {"trades_closed_by_lb2": n_closed, "trades_to_solve": n_open,
            "est_solve_wall_h": total / 3600.0, "cap_solve_wall_h": total_cap / 3600.0,
            "est_by_stratum_h": {k: v / 3600.0 for k, v in sorted(per_stratum.items())},
            "open_trades_by_stratum_and_size": dict(sorted(size_hist.items()))}


# --------------------------------------------------------------------------- #
# Solving one trade                                                            #
# --------------------------------------------------------------------------- #
def trade_wwt(instance: dict, schedule: dict) -> dict:
    wo_by_id = {wo["id"]: wo for wo in instance["work_orders"]}
    out = defaultdict(float)
    for a in schedule.get("assignments", []) or []:
        wo = wo_by_id[a["wo"]]
        out[wo["trade"]] += float(wo["weight"]) * max(0.0, float(a["end_bh"]) - float(wo["due_bh"]))
    return dict(out)


def sub_instance(instance: dict, trade: str) -> dict:
    meta = dict(instance["meta"])
    meta["id"] = "{}|{}".format(instance["meta"]["id"], trade)
    return {
        "meta": meta,
        "trades": [trade],
        "technicians": [t for t in instance["technicians"] if t["trade"] == trade],
        "work_orders": [wo for wo in instance["work_orders"] if wo["trade"] == trade],
    }


def rounded_down(sub: dict) -> dict:
    """The rounded-down grid copy whose CP-SAT bound is a valid continuous bound."""
    cps = mods()["cpsat"]
    wos = []
    for wo in sub["work_orders"]:
        kp, kr, kd = centi_floor(wo["p_bh"]), centi_floor(wo["release_bh"]), centi_ceil(wo["due_bh"])
        w = dict(wo)
        w["p_bh"], w["release_bh"], w["due_bh"] = kp / 100.0, kr / 100.0, kd / 100.0
        # The model's own roundings must leave the grid points where they are.
        if (cps._centi_ceil(w["p_bh"]) != kp or cps._centi_ceil(w["release_bh"]) != kr
                or cps._centi_round(w["due_bh"]) != kd):
            raise SystemExit("grid point moved under the model's rounding: {}".format(wo["id"]))
        if int(round(w["weight"])) != w["weight"]:
            raise SystemExit("non-integer weight {}".format(wo["id"]))
        wos.append(w)
    out = dict(sub)
    out["work_orders"] = wos
    return out


def retime(sub: dict, assignments: list) -> dict:
    """Keep the solver's assignment and order; start each job as early as allowed."""
    wo_by_id = {wo["id"]: wo for wo in sub["work_orders"]}
    by_tech = defaultdict(list)
    for a in assignments:
        by_tech[a["tech"]].append(a)
    out = []
    for tech in sorted(by_tech):
        seq = sorted(by_tech[tech], key=lambda a: (a["start_bh"], a["end_bh"], a["wo"]))
        t = 0.0
        for a in seq:
            wo = wo_by_id[a["wo"]]
            s = max(float(wo["release_bh"]), t)
            e = s + float(wo["p_bh"])
            out.append({"wo": a["wo"], "tech": tech, "start_bh": s, "end_bh": e})
            t = e
    return {"instance_id": sub["meta"]["id"], "method": "cpsat_retimed", "seed": 0,
            "assignments": out}


class SolveTimer:
    """Process CPU and wall around CpSolver.Solve alone (search, no model build)."""

    def __init__(self):
        self.rec = {}

    def __enter__(self):
        cp_model = mods()["cp_model"]
        self._orig = cp_model.CpSolver.Solve
        rec = self.rec
        orig = self._orig

        def wrapped(solver, model, *a, **k):
            t0, c0 = time.perf_counter(), time.process_time()
            r = orig(solver, model, *a, **k)
            rec["wall"] = time.perf_counter() - t0
            rec["cpu"] = time.process_time() - c0
            return r

        cp_model.CpSolver.Solve = wrapped
        return self

    def __exit__(self, *exc):
        mods()["cp_model"].CpSolver.Solve = self._orig
        return False


def solve_trade(relaxed: dict, trade: str, atc_sched: dict, lb2_trade: float,
                budget: float, workers: int, force_solve: bool = False) -> dict:
    """Bracket one trade of a relaxed instance."""
    m = mods()
    sub = sub_instance(relaxed, trade)
    ids = {wo["id"] for wo in sub["work_orders"]}
    atc_assign = [a for a in atc_sched["assignments"] if a["wo"] in ids]
    atc_sub = {"instance_id": sub["meta"]["id"], "assignments": atc_assign}
    atc_t = m["evaluate"].wwt(sub, atc_sub)
    row = OrderedDict(n_orders=len(sub["work_orders"]), n_techs=len(sub["technicians"]),
                      lb2_trade=lb2_trade, atc_trade_obj=atc_t, status=None,
                      cp_obj=None, cp_grid_obj=None, cp_bound=None, lower=None, upper=None,
                      upper_source=None, wall_s=0.0, solve_wall_s=0.0, cpu_s=0.0,
                      cpu_share=None, solve_cpu_share=None, foreign_cpu_s=None,
                      foreign_share=None, budget_s=budget, workers=workers,
                      warm_start="atc", contended=False,
                      affinity=sorted(os.sched_getaffinity(0)), load_avg_start=loadavg())
    if not force_solve and atc_t <= lb2_trade + CLOSE_TOL_BH:
        row.update(status="CLOSED_BY_LB2", lower=lb2_trade, upper=atc_t, upper_source="atc",
                   warm_start=None)
        return row
    grid = rounded_down(sub)
    cores = sorted(os.sched_getaffinity(0))
    b0 = core_busy_s(cores)
    t0, c0 = time.perf_counter(), time.process_time()
    with SolveTimer() as st:
        res = m["cpsat"].solve(grid, time_limit_s=float(budget), workers=int(workers),
                               warm_start=atc_sub)
    wall = time.perf_counter() - t0
    cpu = time.process_time() - c0
    foreign = max(0.0, (core_busy_s(cores) - b0) - cpu)
    cp_bound = float(res.get("best_bound_bh") or 0.0)
    cp_obj = None
    if res.get("assignments"):
        sched = retime(sub, res["assignments"])
        val = m["evaluate"].validate(sub, sched)
        if not val["feasible"]:
            raise SystemExit("re-timed CP-SAT schedule infeasible on {}: {}".format(
                sub["meta"]["id"], val["violations"][:3]))
        cp_obj = m["evaluate"].wwt(sub, sched)
    lower = max(lb2_trade, cp_bound)
    if cp_obj is not None and cp_obj < atc_t:
        upper, src = cp_obj, "cpsat"
    else:
        upper, src = atc_t, "atc"
    s_wall = st.rec.get("wall", wall)
    s_cpu = st.rec.get("cpu", cpu)
    row.update(status=res.get("status"), cp_obj=cp_obj, cp_grid_obj=res.get("objective_bh"),
               cp_bound=cp_bound, lower=lower, upper=upper, upper_source=src,
               wall_s=wall, solve_wall_s=s_wall, cpu_s=cpu,
               cpu_share=cpu / (wall * workers) if wall > 0 else None,
               solve_cpu_share=s_cpu / (s_wall * workers) if s_wall > 0 else None,
               foreign_cpu_s=foreign,
               foreign_share=foreign / (wall * len(cores)) if wall > 0 else None)
    # Contention is judged on the CPU OTHER processes took from our cores during
    # the solve.  The solver's own cpu_share is recorded but is not the test:
    # CP-SAT leaves workers idle in presolve and on small models, so an
    # uncontended solve routinely reads 0.5 to 0.9 (smoke run, 2026-10-26).
    # A proved optimum does not depend on the CPU it received and is never
    # flagged.
    row["contended"] = bool(row["status"] != "OPTIMAL" and row["foreign_share"] is not None
                            and row["foreign_share"] > FOREIGN_SHARE_MAX)
    if lower > upper + CHECK_TOL_BH:
        raise SystemExit("BRACKET VIOLATION on {}: lower {} > upper {}\n{}".format(
            sub["meta"]["id"], lower, upper, json.dumps(row)))
    return row


# --------------------------------------------------------------------------- #
# The runner                                                                   #
# --------------------------------------------------------------------------- #
def solve_queue(store: Store, need: dict) -> list:
    """Baselines first, then adjusted instances; round-robin over strata."""
    def rr(keys):
        lanes = defaultdict(list)
        for k in keys:
            lanes[store.stratum[k[0]]].append(k)
        for s in lanes:
            lanes[s].sort()
        order = [s for s in STRATA_ORDER if s in lanes] + sorted(set(lanes) - set(STRATA_ORDER))
        out = []
        while any(lanes[s] for s in order):
            for s in order:
                if lanes[s]:
                    out.append(lanes[s].pop(0))
        return out

    base = [k for k in need if k[1] == BASE_FP]
    adj = [k for k in need if k[1] != BASE_FP]
    return rr(base) + rr(adj)


def load_trade_cache(path: Path) -> tuple:
    cache = {}
    dropped = 0
    for r in read_jsonl(path):
        k = (r["instance_id"], r["trade"], r["trade_fp"])
        if r.get("contended"):
            cache.pop(k, None)
            dropped += 1
            continue
        cache[k] = r
    return cache, dropped


def bracket_one(store: Store, iid: str, fp: str, tuples: list, cache: dict, args,
                trade_path: Path) -> dict:
    m = mods()
    relaxed = store.relaxed(iid, tuples)
    t0 = time.perf_counter()
    atc = m["dispatch"].dispatch_baseline(relaxed, EPISODE_RULE, seed=EPISODE_SEED)
    atc_total = m["evaluate"].wwt(relaxed, atc)
    lbd = m["lb2"].lb2_detail(relaxed)
    tfps = store.trade_fps(iid, tuples)
    atc_t = trade_wwt(relaxed, atc)
    n_changed_by_trade = Counter(store.trade_of[iid][t[0]] for t in tuples)
    lower = upper = cp_raw = 0.0
    proved = True
    resolved, reused, statuses, solved_now = [], [], {}, 0
    for tr in store.trades[iid]:
        key = (iid, tr, tfps[tr])
        lb_t = lbd["per_trade"].get(tr, {}).get("bound", 0.0)
        row = cache.get(key)
        if row is None:
            row = solve_trade(relaxed, tr, atc, lb_t, args.budget, args.workers)
            row = OrderedDict([("instance_id", iid), ("trade", tr), ("trade_fp", tfps[tr]),
                               ("n_changed_orders", n_changed_by_trade.get(tr, 0)),
                               ("version", VERSION)] + list(row.items()))
            append_jsonl(trade_path, row)
            cache[key] = row
            solved_now += 1
        else:
            if abs(row["atc_trade_obj"] - atc_t.get(tr, 0.0)) > CHECK_TOL_BH:
                raise SystemExit("ATC per-trade objective moved for {}: cached {} now {}".format(
                    key, row["atc_trade_obj"], atc_t.get(tr, 0.0)))
            if abs(row["lb2_trade"] - lb_t) > CHECK_TOL_BH:
                raise SystemExit("LB2 per-trade moved for {}".format(key))
        (resolved if tfps[tr] != BASE_FP else reused).append(tr)
        lower += row["lower"]
        upper += row["upper"]
        cp_raw += row["cp_bound"] if row["cp_bound"] is not None else row["lower"]
        closed = row["upper"] - row["lower"] <= CLOSE_TOL_BH
        statuses[tr] = row["status"]
        proved = proved and (row["status"] in ("OPTIMAL", "CLOSED_BY_LB2") or closed)
    if abs(sum(atc_t.values()) - atc_total) > CHECK_TOL_BH:
        raise SystemExit("ATC does not decompose by trade on {} {}".format(iid, fp))
    out = OrderedDict(
        instance_id=iid, stratum=store.stratum[iid], fingerprint=fp,
        n_changed_orders=len(tuples), trades_resolved=sorted(resolved) if fp != BASE_FP else
        list(store.trades[iid]), trades_reused=sorted(reused) if fp != BASE_FP else [],
        lower=lower, upper=upper, lb2_total=lbd["lb_bh"], cp_bound_total_raw=cp_raw,
        atc_total=atc_total, proved_all=proved,
        width_abs=upper - lower, width_rel=(upper - lower) / max(lower, FLOOR_BH),
        atc_gap_to_lower=(atc_total - lower) / max(lower, FLOOR_BH),
        statuses=statuses, n_trade_solves_now=solved_now,
        wall_s=time.perf_counter() - t0, budget_s=args.budget, version=VERSION)
    if out["lower"] > out["upper"] + CHECK_TOL_BH or out["lb2_total"] > out["upper"] + CHECK_TOL_BH:
        raise SystemExit("BRACKET VIOLATION\n" + json.dumps(out))
    return out


def run_meta(args, extra: dict) -> dict:
    m = mods()
    sg = m["sg"]
    return {
        "version": VERSION,
        "started": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "host": socket.gethostname(), "python": sys.version.split()[0],
        "platform": platform.platform(),
        "ortools": __import__("ortools").__version__,
        "cpsat_py": str(Path(m["cpsat"].__file__)),
        "cpsat_py_sha256": sha256_file(m["cpsat"].__file__),
        "suite_sha256": sg.SUITE_SHA256,
        "instance_root": str(sg.INSTANCE_ROOT),
        "instance_manifest_sha256": sha256_file(sg.INSTANCE_MANIFEST_PATH),
        "proposal_files": {p: sha256_file(p) for p in proposal_files()},
        "affinity": sorted(os.sched_getaffinity(0)),
        "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
        "args": vars(args), "load_avg": loadavg(),
        "base_fingerprint": BASE_FP, **extra,
    }


def foreign_on_cores(cores) -> list:
    """Processes other than this one currently sitting on our cores with real CPU."""
    import subprocess
    try:
        out = subprocess.run(["ps", "-eo", "pid,psr,pcpu,comm"], capture_output=True,
                             text=True, check=True).stdout.splitlines()[1:]
    except Exception:
        return []
    rows = []
    me = os.getpid()
    for line in out:
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        pid, psr, pcpu, comm = int(parts[0]), int(parts[1]), float(parts[2]), parts[3]
        if pid != me and psr in cores and pcpu >= 5.0:
            rows.append({"pid": pid, "psr": psr, "pcpu": pcpu, "comm": comm})
    return rows


def prepare(args):
    suite = load_suite()
    t0 = time.perf_counter()
    store = Store(suite)
    print("[n1] instances loaded and verified: {} ({:.1f}s)".format(len(store.inst),
                                                                    time.perf_counter() - t0))
    return suite, store


def do_census(args, write_index: bool):
    suite, store = prepare(args)
    t0 = time.perf_counter()
    items_path = OUT_DIR / "items.jsonl"
    items_meta_path = OUT_DIR / "items.meta.json"
    items_meta = {"version": VERSION, "suite_sha256": mods()["sg"].SUITE_SHA256,
                  "instance_manifest_sha256": sha256_file(mods()["sg"].INSTANCE_MANIFEST_PATH)}
    items = None
    if write_index and items_path.is_file() and items_meta_path.is_file():
        with open(items_meta_path) as fh:
            if json.load(fh) == items_meta:
                items = read_jsonl(items_path)
                if len(items) != len(suite):
                    items = None
        if items is not None:
            print("[n1] items reused from {} (same version and inputs)".format(items_path))
    if items is None:
        items = map_items(store, suite, execute=write_index)
        if write_index:
            write_jsonl(items_path, items)
            with open(items_meta_path, "w") as fh:
                json.dump(items_meta, fh, indent=2, sort_keys=True)
    print("[n1] items mapped ({:.1f}s)".format(time.perf_counter() - t0))
    t0 = time.perf_counter()
    props = map_proposals(store, suite)
    print("[n1] proposals mapped: {} ({:.1f}s)".format(len(props), time.perf_counter() - t0))
    need = build_census(store, items, props)
    summ = census_summary(store, need, items, props)
    cache, _ = load_trade_cache(OUT_DIR / "trade_solves.jsonl")
    solved = {(r["instance_id"], r["trade"]): r["wall_s"] for r in cache.values()
              if r["trade_fp"] == BASE_FP and r["status"] != "CLOSED_BY_LB2"}
    if args.estimate:
        t0 = time.perf_counter()
        summ["wall_estimate"] = estimate_wall(store, need, args.budget, solved)
        summ["wall_estimate"]["baseline_solves_used"] = len(solved)
        print("[n1] estimate computed ({:.1f}s)".format(time.perf_counter() - t0))
    if write_index:
        mism = []
        for row in items:
            for fld in ("gold_ops", row["canonical_field"]):
                rec = row.get(fld)
                if rec and rec["suite_match"] is False:
                    mism.append((row["item_id"], fld, rec["executed_wt"], rec["suite_wt"]))
        summ["item_suite_mismatches"] = len(mism)
        summ["item_suite_checked"] = sum(
            1 for row in items for fld in ("gold_ops", row["canonical_field"])
            if row.get(fld) and row[fld]["suite_match"] is not None)
        if mism:
            print("[n1] ITEM MISMATCHES against the suite's stored objective:")
            for x in mism[:50]:
                print("   ", x)
        write_jsonl(OUT_DIR / "proposals_index.jsonl",
                    [{k: v for k, v in r.items() if not k.startswith("_")} for r in props])
    with open(OUT_DIR / "census.json", "w") as fh:
        json.dump(summ, fh, indent=2, sort_keys=True)
    print(json.dumps(summ, indent=2, sort_keys=True))
    return suite, store, items, props, need, summ


def cmd_run(args):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    args.estimate = False
    suite, store, items, props, need, summ = do_census(args, write_index=True)
    if summ.get("item_suite_mismatches"):
        print("[n1] note: {} item objectives differ from the suite's stored value; see above"
              .format(summ["item_suite_mismatches"]))
    trade_path = OUT_DIR / "trade_solves.jsonl"
    br_path = OUT_DIR / "brackets.jsonl"
    cache, dropped = load_trade_cache(trade_path)
    done = {(r["instance_id"], r["fingerprint"]) for r in read_jsonl(br_path)}
    foreign = foreign_on_cores(set(args.cores_t))
    meta = run_meta(args, {"census": summ, "resume_trade_rows": len(cache),
                           "resume_dropped_contended": dropped,
                           "resume_brackets_done": len(done),
                           "foreign_processes_on_cores_at_start": foreign})
    with open(OUT_DIR / "run_meta.json", "w") as fh:
        json.dump(meta, fh, indent=2, sort_keys=True)
    append_jsonl(OUT_DIR / "run_meta_history.jsonl", meta)
    if foreign:
        print("[n1] WARNING: other processes on our cores at start: {}".format(foreign))
    queue = [k for k in solve_queue(store, need) if k not in done]
    if args.limit:
        queue = queue[: args.limit]
    print("[n1] queue: {} brackets ({} already done, {} trade rows cached, {} contended dropped)"
          .format(len(queue), len(done), len(cache), dropped))
    t_run = time.perf_counter()
    for i, (iid, fp) in enumerate(queue, 1):
        b = bracket_one(store, iid, fp, need[(iid, fp)]["tuples"], cache, args, trade_path)
        append_jsonl(br_path, b)
        el = time.perf_counter() - t_run
        print("[n1] {}/{} {} {} chg={} lower={:.4f} upper={:.4f} width={:.4%} proved={} "
              "solves={} wall={:.1f}s elapsed={:.0f}s".format(
                  i, len(queue), iid, fp[:10], b["n_changed_orders"], b["lower"], b["upper"],
                  b["width_rel"], b["proved_all"], b["n_trade_solves_now"], b["wall_s"], el),
              flush=True)
    print("[n1] run finished: {} brackets in {:.1f}s".format(len(queue), time.perf_counter() - t_run))
    return 0


def cmd_census(args):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    do_census(args, write_index=False)
    return 0


def cmd_selfcheck(args):
    m = mods()
    suite, store = prepare(args)
    replay = sorted(i for i in store.inst if store.stratum[i] == "c10_replay_400")[:SELFCHECK_N]
    print("[n1] (a) whole-instance vs per-trade on {} replay instances, {} s".format(
        len(replay), SELFCHECK_BUDGET_S))
    for iid in replay:
        inst = store.inst[iid]
        whole_sub = {"meta": dict(inst["meta"]), "trades": inst["trades"],
                     "technicians": inst["technicians"], "work_orders": inst["work_orders"]}
        grid = rounded_down(whole_sub)
        w = m["cpsat"].solve(grid, time_limit_s=SELFCHECK_BUDGET_S, workers=args.workers)
        if w["status"] != "OPTIMAL":
            raise SystemExit("selfcheck (a): whole-instance solve did not prove on {}: {}"
                             .format(iid, w["status"]))
        atc = store.baseline[iid]
        lbd = m["lb2"].lb2_detail(inst)["per_trade"]
        tot_opt, tot_up, tot_lo = 0.0, 0.0, 0.0
        for tr in store.trades[iid]:
            r = solve_trade(inst, tr, atc, lbd.get(tr, {}).get("bound", 0.0),
                            SELFCHECK_BUDGET_S, args.workers, force_solve=True)
            if r["status"] != "OPTIMAL":
                raise SystemExit("selfcheck (a): trade {} of {} did not prove".format(tr, iid))
            tot_opt += r["cp_grid_obj"]
            tot_up += r["upper"]
            tot_lo += r["lower"]
        y1 = m["cpsat"].solve(inst, time_limit_s=SELFCHECK_BUDGET_S, workers=args.workers)
        ok = abs(w["objective_bh"] - tot_opt) <= CHECK_TOL_BH
        print("   {}  whole(rounded-down)={:.4f}  sum per-trade={:.4f}  {}  | bracket [{:.4f}, {:.4f}]"
              "  Y1-grid {} {:.4f}  ATC {:.4f}".format(
                  iid, w["objective_bh"], tot_opt, "OK" if ok else "FAIL", tot_lo, tot_up,
                  y1["status"],
                  float("nan") if y1["objective_bh"] is None else y1["objective_bh"],
                  m["evaluate"].wwt(inst, atc)))
        if not ok:
            raise SystemExit("selfcheck (a) FAILED on {}".format(iid))
        if tot_lo > tot_up + CHECK_TOL_BH:
            raise SystemExit("selfcheck (a): bracket inverted on {}".format(iid))
    print("[n1] (b)-(d) checks on the files on disk")
    br = {}
    for r in read_jsonl(OUT_DIR / "brackets.jsonl"):
        br[(r["instance_id"], r["fingerprint"])] = r
    for r in br.values():
        if r["lower"] > r["upper"] + CHECK_TOL_BH or r["lb2_total"] > r["upper"] + CHECK_TOL_BH:
            raise SystemExit("selfcheck (b) FAILED:\n" + json.dumps(r))
    n_items = 0
    for row in read_jsonl(OUT_DIR / "items.jsonl"):
        for fld in ("gold_ops", row["canonical_field"]):
            rec = row.get(fld)
            if not rec or rec["executed_wt"] is None:
                continue
            b = br.get((row["instance_id"], rec["fingerprint"]))
            if b is None:
                continue
            n_items += 1
            if rec["executed_wt"] < b["lower"] - CHECK_TOL_BH:
                raise SystemExit("selfcheck (c) FAILED:\n{}\n{}".format(json.dumps(row), json.dumps(b)))
    n_props = 0
    for row in read_jsonl(OUT_DIR / "proposals_index.jsonl"):
        if not row["executed"] or row["logged_wt"] is None:
            continue
        b = br.get((row["instance_id"], row["fingerprint"]))
        if b is None:
            continue
        n_props += 1
        if row["logged_wt"] < b["lower"] - CHECK_TOL_BH:
            raise SystemExit("selfcheck (d) FAILED:\n{}\n{}".format(json.dumps(row), json.dumps(b)))
    print("[n1] selfcheck passed: {} brackets, {} item objectives, {} proposal objectives checked"
          .format(len(br), n_items, n_props))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--census", action="store_true")
    g.add_argument("--run", action="store_true")
    g.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="brackets to compute this call")
    ap.add_argument("--budget", type=float, default=DEFAULT_BUDGET_S, help="seconds per trade")
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    ap.add_argument("--cores", default="8-15")
    ap.add_argument("--no-estimate", dest="estimate", action="store_false",
                    help="census without the ATC pass that classifies closed trades")
    args = ap.parse_args()
    args.cores_t = parse_cores(args.cores)
    if len(args.cores_t) != args.workers:
        raise SystemExit("REFUSING TO RUN: {} workers on {} cores".format(args.workers,
                                                                         len(args.cores_t)))
    os.environ["L1_N1_WORKERS"] = str(args.workers)
    setup_environment(args.cores_t, args.workers)
    if args.census:
        return cmd_census(args)
    if args.run:
        return cmd_run(args)
    return cmd_selfcheck(args)


if __name__ == "__main__":
    sys.exit(main())
