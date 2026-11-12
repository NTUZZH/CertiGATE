#!/usr/bin/env python
"""N11: the decision-time primary evaluation (Stage 1, the direct benchmark).

QUESTION
--------
The published gate prices a proposal on the full adjusted instance at t = 0,
with every work order known, including the orders the site receives only
later.  N11 prices every proposal with every gate design on the board the site
knows at the instant the instruction can be issued, dispositions it there, and
scores the consequence on the full window once the later orders arrive.  Stage
1 does this for the direct benchmark (the canonical proposal of every suite
item) and for the cost labels of the held-out test; Stage 2 replays the logged
end-to-end proposals.  The design is the pre-specified design
(cited below as "design"), the decisions on its open points are
the pre-specified design ("design").

DEFINITIONS (design 1-5, design "Decisions")
-------------------------------------------
Named set R_i      the ids of ``referenced.order_ids`` present in the instance.
t_known(i)         max over R_i of (0 for a planned order, else its release); 0
                   when R_i is empty (planned-known reading, design decision 3).
t_start(i)         min over R_i of the baseline start (ATC, seed 0, frozen set
                   pinned; equal to the plain dispatch, assertion A2).
Issuable           t_known <= t_start (closed rule, primary, design decision 1);
                   the strict rule t_known < t_start is a subset sensitivity.
t_d                t_known (design decision 2).
K, kf              N8's known instance and frozen set at t_d, planned-known.
Designs on K       G-FEAS (stages 1-2), G-CERT g_c = (obj_K - LB_K)/max(LB_K,1),
                   G-CERT-M m_c = g_c - g_anchor_K, D-REL1 against the no-op
                   dispatch of K, D-REL2 against K with the installed fields and
                   no constraining operation, D-ABS in bh, and the unions.
Board B(i, t_d)    the orders of K that are not running, with the installed
                   fields and release max(r', t_d); every technician, free from
                   a_u = max(t_d, end of its running job); the running orders'
                   weighted tardiness as a constant; no dispatch constraint.
Oracle on B        per trade, lower = max(LB2 at t_d, CP-SAT bound on the
                   rounded-down copy with availability); upper = min(ATC dispatch
                   of B, every executed K-schedule with the same board key,
                   re-timed CP-SAT incumbent).  code/l1oracle/cpsat_avail.py.
Decision-time c    c_K = (OPT_c,K - OPT_K)/max(OPT_K, 1) with the instruction's
                   precedence, pins, frozen slots and batches on the board,
                   bracketed in N9's conservative direction.
Realised run       N8's: the full instance, every order started before t_d
                   pinned to its trajectory slot, the proposal applied at t_d,
                   later orders released as they come; weighted tardiness on the
                   adjusted AND the original fields.

SUBCOMMANDS
-----------
census   deterministic (cores 8-9): issuability, the omniscient checks on the
         direct benchmark, decision-time pricing, realised runs, the board
         census with LB2 and the dispatch upper ends, the solve inputs.
omni     deterministic (cores 8-9): the omniscient reading of the logged
         end-to-end rows (assertion A4 and the end-to-end parts of A5).
oracle   CP-SAT on cores 8-11 EXCLUSIVELY, detached: model self-check (A11),
         relaxed board brackets, decision-time c.  Refuses to start unless the
         census and omni assertion files say PASS for the inputs on disk.
analyse  tables, macros, summary (A9, A13, A14).

Every assertion group of design Section 8 is run-fatal: a failure writes the
failure list and exits non-zero; no output of a failed stage is used.

Version: l1-n11-decision-time-1
"""

from __future__ import annotations

import os

SNAPSHOT_ROOT = ((os.environ.get("L1_Y1_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "PaperY-FMScheduling")) + "/data/processed/instances_v10")
_env_root = os.environ.get("L1_INSTANCE_ROOT")
if _env_root and os.path.realpath(_env_root) != os.path.realpath(SNAPSHOT_ROOT):
    raise SystemExit("REFUSING TO RUN: L1_INSTANCE_ROOT={} is not the snapshot {}"
                     .format(_env_root, SNAPSHOT_ROOT))
os.environ["L1_INSTANCE_ROOT"] = SNAPSHOT_ROOT

import argparse  # noqa: E402
import copy  # noqa: E402
import csv  # noqa: E402
import datetime as _dt  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import platform  # noqa: E402
import socket  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from collections import Counter, OrderedDict, defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent
CODE = SCRIPTS_DIR.parent
ROOT = CODE.parent
for _p in (str(CODE), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

VERSION = "l1-n11-decision-time-1"
RESULTS = ROOT / "results"
ANALYSIS = ROOT / "analysis"
OUT = RESULTS / "n11_decision_time"
ORACLE_OUT = RESULTS / "n11_oracle"
ORACLE_V1 = RESULTS / "oracle_v1"
N8_ITEMS = RESULTS / "n8_causal" / "items.jsonl"
N9_DIR = RESULTS / "n9_instruction_cost"
SUITE_PATH = CODE / "suite" / "v0.2" / "suite.jsonl"
HELDOUT_PATH = CODE / "suite" / "v0.3_heldout" / "suite_heldout.jsonl"
HELDOUT_MANIFEST = CODE / "suite" / "v0.3_heldout" / "manifest_heldout.json"
EXT_PATH = CODE / "suite" / "v1.1" / "suite_ext.jsonl"
EXT_NEG_PATH = CODE / "suite" / "v1.1" / "suite_ext_neg.jsonl"
EXT_MANIFEST = CODE / "suite" / "v1.1" / "manifest.json"
EXT_NEG_MANIFEST = CODE / "suite" / "v1.1" / "manifest_neg.json"
DG1_PATH = ANALYSIS / "DG1_direct_guard.csv"
ANCHOR_PATH = ANALYSIS / "ladder" / "rule_anchor.json"

TAU = 0.20
FLOOR_BH = 1.0
ROUND_BH = 6
DG14 = OrderedDict([("D-REL1", 0.02), ("D-REL2", 0.02), ("D-ABS", 0.8119)])
DG14_TALLY = {"D-REL1": (12, 217), "D-REL2": (0, 217), "D-ABS": (21, 220), "G-CERT": (21, 201)}
EXPECT_NOT_ISSUABLE = {"closed": 277, "strict": 731}
CLOSE_TOL_BH = 1e-9
CHECK_TOL = 1e-6
N8_TOL = 1e-9
BUDGET_S = 60.0
FOREIGN_SHARE_MAX = 0.10
MAX_RESOLVES = 2
DET_CORES = (8, 9)
ORACLE_CORES = (8, 9, 10, 11)
FORBIDDEN_CORES = frozenset() if os.environ.get("CERTIGATE_ANY_CORES") else frozenset(range(0, 8)) | frozenset(range(12, 24))

CANONICAL_FIELD = {"benign": "gold_ops", "V1": "literal_ops", "V2": "literal_ops",
                   "V3": "gold_ops", "V4": "trap_ops", "V5": "gold_ops", "V6": "forbidden_ops"}
CLASSES = ("benign", "V1", "V2", "V3", "V4", "V5", "V6")
STRATA = ("c09_storm2_w80", "c10_storm2_w80", "c10_replay_400")
STRATUM_NAME = {"c09_storm2_w80": "Primary", "c10_storm2_w80": "Confirmation",
                "c10_replay_400": "Buildings"}
FIELDS = ("release_bh", "due_bh", "weight", "priority")
CONSTRAINING_OPS = frozenset({"pin_next", "reorder", "freeze", "unfreeze", "batch"})
FIELD_OPS = frozenset({"set_priority", "reassign_window"})
EMPTY_RAW = json.dumps({"operations": []})


# --------------------------------------------------------------------------- #
# Small utilities                                                              #
# --------------------------------------------------------------------------- #
def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fp_of(tuples) -> str:
    """oracle_cost.fp_of, restated so this module imports no solver at load time."""
    rows = sorted([list(t) for t in tuples], key=lambda t: t[0])
    blob = json.dumps(rows, separators=(",", ":"), sort_keys=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


BASE_FP = fp_of([])


def read_jsonl(path) -> list:
    path = Path(path)
    if not path.is_file():
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def append_jsonl(path, row) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


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
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=True, default=str)
    os.replace(tmp, path)


def read_csv_comments(path) -> list:
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def parse_cores(text) -> list:
    out = set()
    for part in str(text).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return sorted(out)


def frozen_key(frozen_seed) -> str:
    return ",".join(str(x) for x in (frozen_seed or ()))


def gfun(obj, x):
    v = (float(obj) - float(x)) / max(float(x), FLOOR_BH)
    return v if v > 0.0 else 0.0


def rel_delta(obj, ref):
    return round(obj - ref, ROUND_BH) / max(ref, FLOOR_BH)


def loadavg() -> list:
    with open("/proc/loadavg") as fh:
        return [float(x) for x in fh.read().split()[:3]]


def now_iso() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


class Checker:
    """Run-fatal assertions, grouped by the design's A1-A14 labels."""

    def __init__(self):
        self.n = Counter()
        self.failures = []

    def true(self, group, what, ok, detail=""):
        self.n[group] += 1
        if not ok:
            self.failures.append("{} {}: {}".format(group, what, detail))

    def close(self, group, what, a, b, tol):
        ok = (a is None and b is None) or (
            a is not None and b is not None and abs(float(a) - float(b)) <= tol)
        self.true(group, what, ok, "{!r} vs {!r}".format(a, b))

    def report(self) -> dict:
        return {"status": "PASS" if not self.failures else "FAIL",
                "checks_by_group": dict(sorted(self.n.items())),
                "n_checks": sum(self.n.values()), "n_failures": len(self.failures),
                "failures": self.failures[:200]}

    def fatal(self, path, extra=None):
        rep = self.report()
        if extra:
            rep.update(extra)
        write_json(path, rep)
        if self.failures:
            print("ASSERTION FAILURES ({} of {}):".format(len(self.failures), rep["n_checks"]),
                  file=sys.stderr)
            for f in self.failures[:40]:
                print("  -", f, file=sys.stderr)
            raise SystemExit(2)
        return rep


def pin_cores(cores) -> None:
    cores = set(cores)
    if cores & FORBIDDEN_CORES:
        raise SystemExit("REFUSING TO RUN: cores {} overlap cores of other projects".format(
            sorted(cores)))
    os.sched_setaffinity(0, cores)
    got = set(os.sched_getaffinity(0))
    if got != cores:
        raise SystemExit("REFUSING TO RUN: affinity {} != requested {}".format(sorted(got),
                                                                              sorted(cores)))


def cap_threads(n: int) -> None:
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        os.environ[var] = str(int(n))


# --------------------------------------------------------------------------- #
# Inputs: suites and instances, only through suite_gate                       #
# --------------------------------------------------------------------------- #
def load_published(check) -> list:
    import suite_gate as sg

    got = sha256_file(sg.SUITE_PATH)
    check.true("A1", "published suite SHA-256", got == sg.SUITE_SHA256, got)
    rows = read_jsonl(sg.SUITE_PATH)
    check.true("A1", "published suite rows", len(rows) == 2000, len(rows))
    return rows


def load_heldout(check) -> list:
    man = json.loads(HELDOUT_MANIFEST.read_text())
    want = man["artifacts"]["suite_heldout.jsonl"]["sha256"]
    got = sha256_file(HELDOUT_PATH)
    check.true("A1", "held-out file SHA-256 equals its manifest", got == want, got)
    return read_jsonl(HELDOUT_PATH)


def load_ext(check) -> dict:
    out = {}
    for path, mpath in ((EXT_PATH, EXT_MANIFEST), (EXT_NEG_PATH, EXT_NEG_MANIFEST)):
        man = json.loads(Path(mpath).read_text())
        digests = [v.get("sha256") for v in (man.get("artifacts") or {}).values()
                   if isinstance(v, dict)]
        got = sha256_file(path)
        check.true("A1", "{} SHA-256 equals its manifest".format(Path(path).name),
                   got in digests, got)
        for r in read_jsonl(path):
            out[r["item_id"]] = r
    return out


def instance_path(item) -> str:
    """The snapshot file of an item, manifest-verified; never a logged path."""
    import suite_gate as sg

    p = Path(sg.instance_path(item)).resolve()
    if not str(p).startswith(str(Path(SNAPSHOT_ROOT).resolve()) + os.sep):
        raise SystemExit("REFUSING TO RUN: {} resolves outside the snapshot".format(p))
    return str(p)


def load_instance(path) -> dict:
    p = Path(path).resolve()
    if not str(p).startswith(str(Path(SNAPSHOT_ROOT).resolve()) + os.sep):
        raise SystemExit("REFUSING TO OPEN {}: not in the snapshot".format(p))
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def load_anchor_records() -> dict:
    out = {}
    for rec in json.loads(ANCHOR_PATH.read_text()):
        iid = Path(rec["instance_path"]).stem
        out[(iid, frozen_key(rec["frozen_seed"]))] = rec
    return out


# --------------------------------------------------------------------------- #
# The guard's stages, generalised to a decision instant (design 3, note)       #
# --------------------------------------------------------------------------- #
def changed_tuples(adjusted) -> list:
    """(id, release, due, weight, priority) of every order whose fields differ from the input."""
    before = {wo["id"]: wo for wo in adjusted.original["work_orders"]}
    out = []
    for wo in adjusted.instance["work_orders"]:
        b = before[wo["id"]]
        cur = tuple(wo[f] for f in FIELDS)
        if cur != tuple(b[f] for f in FIELDS):
            out.append((wo["id"],) + cur)
    out.sort(key=lambda t: t[0])
    return out


def trade_wwt_of(fields_inst, schedule, skip=()) -> dict:
    """Weighted tardiness per trade of ``schedule`` on ``fields_inst``, skipping ids."""
    by = {wo["id"]: wo for wo in fields_inst["work_orders"]}
    skip = set(skip)
    out = defaultdict(float)
    for a in schedule.get("assignments", []) or []:
        if a["wo"] in skip:
            continue
        wo = by[a["wo"]]
        out[wo["trade"]] += float(wo["weight"]) * max(0.0, float(a["end_bh"]) - float(wo["due_bh"]))
    return dict(out)


RUNNING_WORK_CODE = "names_running_work"


def running_work_findings(instance, typed, running_ids) -> list:
    """Stage 3 addition A: an operation that names work already running at t_d.

    The technician is on the job, so the site can neither release nor
    re-sequence it: an ``unfreeze``, ``reorder``, ``pin_next``, ``freeze``,
    ``set_priority`` or ``reassign_window`` naming a running order, or a
    ``batch`` whose (building, trade) group holds one, is refused at the
    feasibility stage.  The finding is built directly (the published guard's
    code registry is not edited); it is a blocking violation of stage 2.
    """
    from l1guard import findings as F
    import n8_causal as n8

    run = set(running_ids or ())
    if not run or not typed:
        return []
    explicit, members = n8.named_orders([op.to_dict() for op in typed], instance)
    hits = sorted((set(explicit) | set(members)) & run)
    if not hits:
        return []
    return [F.Finding(stage=F.STAGE_FEAS, code=RUNNING_WORK_CODE,
                      message="the proposal names work already running at the decision "
                              "instant: {}".format(", ".join(hits)),
                      severity=F.VIOLATION, detail={"order_ids": hits})]


def gen_price(instance, raw, frozen, baseline, t_d, protect=None, keep_batch=None,
              unguarded=False, ref2=False, keep_live=False, running_ids=None) -> dict:
    """The guard's three stages on ``instance`` dispatched from ``t_d``.

    Generalises ``n8_causal.price`` in the three ways of the design (3, note):
    stage 1 runs on ``raw`` exactly as the guard does (text or object), the
    original-field objective is recorded beside the adjusted one, and an
    instrument fault ends in ``execution_failed`` as in ``l1guard.guard``.
    Returns the G_CERT and G_FEAS terminals and stages (and the UNGUARDED
    terminal on request), the codes, obj, obj_orig, the bound on the known
    set, the gap, the changed field tuples and, on request, the D-REL2
    reference of the same fields with no constraining operation.

    ``running_ids`` (Stage 3, addition A): the orders running at ``t_d``; an
    operation naming one is refused at stage 2 (``running_work_findings``).
    ``None`` (the default, and every t = 0 call) leaves the guard unchanged.
    """
    from l1adapter import apply as apply_mod
    from l1adapter import dispatch as dispatch_mod
    from l1adapter import evaluate as evaluate_mod
    from l1adapter.errors import AdapterError, DispatchDeadlock
    from l1guard import findings as F
    from l1guard import guard as G
    from l1guard.config import G_CERT, UNGUARDED
    from l1guard.verdict import certified_gap
    import n8_causal as n8

    frozen = list(frozen or ())
    res = {"term_cert": None, "stage_cert": None, "term_feas": None, "stage_feas": None,
           "term_ung": None, "codes": [], "obj": None, "obj_orig": None, "lb": None,
           "lb_running": None, "lb_queue": None, "gap": None, "ops": None, "tuples": None,
           "n_raised": 0, "ref2": None, "ref2_from": None, "constraining": False,
           "infra": False, "parse_ok": None}
    live = {}

    def finish(term, stage, findings, qual=False):
        res["codes"] = sorted({f.code for f in findings if f.blocking})
        res["infra"] = any(f.severity == F.INFRA for f in findings)
        if qual:
            res["term_cert"], res["stage_cert"] = term, stage
        else:
            res["term_cert"], res["stage_cert"] = term, stage
            res["term_feas"], res["stage_feas"] = term, stage
        return res

    # ---- stage 1, strictly (G_CERT and G_FEAS share stages 1 and 2) ---- #
    s_find, typed, parse = G._stage_schema(instance, raw, G_CERT)
    res["parse_ok"] = bool(parse.get("ok"))
    res["ops"] = None if typed is None else [op.to_dict() for op in typed]
    res["constraining"] = bool(typed) and any(op.op in CONSTRAINING_OPS for op in typed)
    if unguarded:
        res["term_ung"] = _unguarded_terminal(instance, raw, frozen, baseline, typed, s_find)
    if any(f.blocking for f in s_find):
        return finish("blocked_schema", "schema", s_find)
    if typed is None:
        return finish("execution_failed", "schema", s_find)

    # ---- stage 2 ---- #
    out = list(s_find) + G._cycle_findings(typed)
    out.extend(G._frozen_edit_findings(instance, typed, frozen if protect is None else protect))
    if running_ids:
        out.extend(running_work_findings(instance, typed, running_ids))
    try:
        adj = apply_mod.apply_operations(instance, typed, frozen_seed=frozen,
                                         baseline_schedule=baseline)
    except AdapterError as exc:
        out.append(G._error_finding(exc))
        return finish("blocked_feas", "feas", out)
    for note in adj.notes:
        code = G._NOTE_CODES.get(note.split(":", 1)[0])
        if code is not None:
            out.append(F.make(code, "adapter note: {}".format(note), note=note))
    if any(f.blocking for f in out):
        return finish("blocked_feas", "feas", out)
    res["tuples"] = [list(t) for t in changed_tuples(adj)]
    if keep_batch is not None:
        n8.restrict_batches(adj, keep_batch)
    res["n_raised"] = n8.raise_releases(adj, t_d)
    try:
        schedule = dispatch_mod.dispatch_adjusted(adj, rule=G_CERT.rule, seed=G_CERT.seed)
    except DispatchDeadlock as exc:
        out.append(G._infra_finding(exc, F.STAGE_FEAS))
        return finish("execution_failed", "feas", out)
    except AdapterError as exc:
        out.append(G._error_finding(exc))
        return finish("blocked_feas", "feas", out)
    except Exception as exc:  # noqa: BLE001 - an instrument fault is data
        out.append(G._infra_finding(exc, F.STAGE_FEAS))
        return finish("execution_failed", "feas", out)
    res["obj"] = evaluate_mod.wwt(adj.instance, schedule)
    res["obj_orig"] = evaluate_mod.wwt(adj.original, schedule)
    try:
        validation = evaluate_mod.validate(adj, schedule)
    except Exception as exc:  # noqa: BLE001
        out.append(G._infra_finding(exc, F.STAGE_FEAS))
        return finish("execution_failed", "feas", out)
    if not validation["feasible"]:
        out.append(F.make("validator_infeasible", "the referee rejects the adjusted schedule",
                          n_violations=len(validation["violations"]),
                          violations=validation["violations"][:5]))
        return finish("blocked_feas", "feas", out)
    res["term_feas"], res["stage_feas"] = "applied_uncertified", "feas"
    live["adjusted"], live["schedule"] = adj, schedule

    if ref2:
        if res["constraining"]:
            try:
                ref_adj = apply_mod.apply_operations(adj.instance, [], frozen_seed=frozen,
                                                     baseline_schedule=baseline)
                n8.raise_releases(ref_adj, t_d)
                ref_sched = dispatch_mod.dispatch_adjusted(ref_adj, G_CERT.rule, G_CERT.seed)
                res["ref2"] = evaluate_mod.wwt(ref_adj, ref_sched)
                res["ref2_from"] = "dispatched"
            except Exception as exc:  # noqa: BLE001 - a missing counterfactual is data
                res["ref2"], res["ref2_from"] = None, "unavailable:" + type(exc).__name__
        else:
            res["ref2"], res["ref2_from"] = res["obj"], "identical_by_construction"

    # ---- stage 3 (G_CERT only) ---- #
    qual = []
    try:
        bnd = n8.bound_known(adj.instance, adj.frozen, t_d)
        lb = bnd["lb_bh"]
        res.update(lb=lb, lb_running=bnd["lb_running_bh"], lb_queue=bnd["lb_queue_bh"])
        if lb > res["obj"] + 1e-6:
            qual.append(F.make("lb_exceeds_objective", "bound above the objective",
                               lb_bh=lb, obj_bh=res["obj"], tier="tier2"))
        gap = certified_gap(res["obj"], lb, G_CERT.lb_floor_bh)
        res["gap"] = gap
        if gap > G_CERT.tau:
            qual.append(F.make("gap_above_tau", "certified gap above tau", gap=gap,
                               tau=G_CERT.tau, obj_bh=res["obj"], lb_bh=lb, tier="tier2"))
    except Exception as exc:  # noqa: BLE001
        qual = [G._infra_finding(exc, F.STAGE_QUAL)]
        res["gap"] = None
    if keep_live:
        res["_live"] = live
    if any(f.severity == F.INFRA for f in qual):
        return finish("execution_failed", "qual", out + qual, qual=True)
    if any(f.blocking for f in qual):
        return finish("blocked_qual", "qual", out + qual, qual=True)
    return finish("applied_with_certificate", "qual", out + qual, qual=True)


def _unguarded_terminal(instance, raw, frozen, baseline, typed_strict, s_find) -> str:
    """The UNGUARDED arm: lenient parse, no stage gates; executes what applies."""
    from l1guard import guard as G
    from l1guard.config import UNGUARDED

    s_u, typed_u, _p = G._stage_schema(instance, raw, UNGUARDED)
    if typed_u is None:
        return "execution_failed"
    _f, _adj, sched, _val = G._stage_feas(instance, typed_u, UNGUARDED, baseline,
                                          tuple(frozen or ()))
    return "applied_uncertified" if sched is not None else "execution_failed"


# --------------------------------------------------------------------------- #
# Issuability (design 1.2)                                                     #
# --------------------------------------------------------------------------- #
def issuability(item, by_id, starts) -> dict:
    ref = [o for o in item["referenced"]["order_ids"] if o in by_id]
    rel = [0.0 if by_id[o].get("is_pm") else float(by_id[o]["release_bh"]) for o in ref]
    t_known = max(rel) if rel else 0.0
    t_start = min(starts[o] for o in ref) if ref else math.inf
    return {"n_ref": len(ref), "ref_ids": ref, "t_known": t_known,
            "t_start": None if math.isinf(t_start) else t_start,
            "issuable": t_known <= t_start, "issuable_strict": t_known < t_start,
            "ref_all_pm": bool(ref) and all(by_id[o].get("is_pm") for o in ref)}


def kf_fix(state, frozen_seed) -> list:
    """Stage 2 frozen set on K: running orders plus every seed order K holds.

    N8's ``known_frozen`` keeps only queued and running seed orders, so a
    planned seed order already on the calendar (``scheduled``) is left free to
    move on K although it is frozen in the published reading.
    """
    k_ids = set(state["queue"]) | set(state["in_progress"]) | set(state["scheduled"])
    out = list(state["in_progress"])
    for oid in frozen_seed or ():
        if oid in k_ids and oid not in out:
            out.append(oid)
    return out


def _kf_n8(state, frozen_seed) -> list:
    import n8_causal as n8
    return n8.known_frozen(state, frozen_seed)


KF_FUNCS = {"fix": kf_fix, "n8": _kf_n8}
READINGS = ("primary", "late")


def decision_instant_of(iss, reading) -> float:
    """t_d = t_known (primary); t_d' = t_start for issuable items (late)."""
    if reading == "primary":
        return iss["t_known"]
    if reading == "late":
        if iss["issuable"] and iss["t_start"] is not None:
            return float(iss["t_start"])
        return iss["t_known"]
    raise ValueError(reading)


# --------------------------------------------------------------------------- #
# The board at t_d (design 4.1)                                                #
# --------------------------------------------------------------------------- #
def site_of(state, pins, t_d) -> dict:
    """Non-running known ids, running (id, tech, start, end), and a_u per technician."""
    slot = {a["wo"]: a for a in pins["assignments"]}
    running = []
    for oid in state["in_progress"]:
        a = slot[oid]
        running.append([oid, a["tech"], float(a["start_bh"]), float(a["end_bh"])])
    running.sort()
    run_ids = {r[0] for r in running}
    known = [o for o in state["queue"] + state["scheduled"] if o not in run_ids]
    return {"t_d": float(t_d), "known_ids": known, "running": running}


def availability(instance, site) -> dict:
    t_d = site["t_d"]
    out = {t["id"]: float(t_d) for t in instance["technicians"]}
    for _oid, tech, _s, e in site["running"]:
        out[tech] = max(out[tech], float(e))
    return out


def avail_multiset(instance, avail) -> dict:
    by_trade = defaultdict(list)
    for t in instance["technicians"]:
        by_trade[t["trade"]].append(round(avail[t["id"]], 9))
    return {k: sorted(v) for k, v in sorted(by_trade.items())}


def running_constant(instance, site) -> float:
    by = {wo["id"]: wo for wo in instance["work_orders"]}
    tot = 0.0
    for oid, _tech, s, e in site["running"]:
        wo = by[oid]
        tot += float(wo["weight"]) * max(0.0, e - float(wo["due_bh"]))
    return tot


def board_instance(instance, site, tuples) -> dict:
    """The relaxed board: non-running known orders, installed fields, release >= t_d."""
    t_d = site["t_d"]
    repl = {t[0]: t for t in (tuples or [])}
    keep = set(site["known_ids"])
    wos = []
    for wo in instance["work_orders"]:
        if wo["id"] not in keep:
            continue
        w = dict(wo)
        t = repl.get(wo["id"])
        if t is not None:
            for f, v in zip(FIELDS, t[1:]):
                w[f] = v
        if float(w["release_bh"]) < t_d:
            w["release_bh"] = t_d
        wos.append(w)
    meta = dict(instance["meta"])
    return {"meta": meta, "trades": instance.get("trades", []),
            "technicians": instance["technicians"], "work_orders": wos}


def trade_fps(board_inst, tuples) -> dict:
    trade_of = {wo["id"]: wo["trade"] for wo in board_inst["work_orders"]}
    by = defaultdict(list)
    for t in tuples or []:
        if t[0] in trade_of:
            by[trade_of[t[0]]].append(tuple(t))
    trades = sorted({wo["trade"] for wo in board_inst["work_orders"]})
    return {tr: (fp_of(by[tr]) if by.get(tr) else BASE_FP) for tr in trades}


def board_atc(instance, site, tuples):
    """ATC dispatch of the board from t_d with the running work pinned (upper source 1)."""
    from l1adapter import apply as apply_mod
    from l1adapter import dispatch as dispatch_mod
    import n8_causal as n8

    keep = set(site["known_ids"]) | {r[0] for r in site["running"]}
    repl = {t[0]: t for t in (tuples or [])}
    wos = []
    for wo in instance["work_orders"]:
        if wo["id"] not in keep:
            continue
        w = dict(wo)
        t = repl.get(wo["id"])
        if t is not None:
            for f, v in zip(FIELDS, t[1:]):
                w[f] = v
        wos.append(w)
    kinst = {k: v for k, v in instance.items() if k != "work_orders"}
    kinst["work_orders"] = wos
    base = {"assignments": [{"wo": oid, "tech": tech, "start_bh": s, "end_bh": e}
                            for oid, tech, s, e in site["running"]]}
    adj = apply_mod.apply_operations(kinst, [], frozen_seed=[r[0] for r in site["running"]],
                                     baseline_schedule=base)
    n8.raise_releases(adj, site["t_d"])
    sched = dispatch_mod.dispatch_adjusted(adj, "atc", 0)
    return adj, sched


def board_record(instance, iid, site, tuples, need_inputs=True) -> dict:
    """LB2 and the ATC upper end per trade of one board, and the open-trade inputs."""
    from l1adapter import evaluate as evaluate_mod
    from l1guard.lb2 import lb2_detail

    t_d = site["t_d"]
    binst = board_instance(instance, site, tuples)
    avail = availability(instance, site)
    taus = defaultdict(list)
    for t in instance["technicians"]:
        taus[t["trade"]].append(avail[t["id"]])
    lbd = lb2_detail(binst, tau_by_trade=dict(taus), t=t_d)["per_trade"]
    adj, sched = board_atc(instance, site, tuples)
    val = evaluate_mod.validate(adj, sched)
    run_ids = {r[0] for r in site["running"]}
    atc_t = trade_wwt_of(adj.instance, sched, skip=run_ids)
    tfps = trade_fps(binst, tuples)
    n_t = Counter(wo["trade"] for wo in binst["work_orders"])
    trades = OrderedDict()
    for tr in sorted(tfps):
        trades[tr] = {"trade_fp": tfps[tr], "n_orders": n_t[tr],
                      "n_techs": len(taus.get(tr, [])),
                      "lb2": lbd.get(tr, {}).get("bound", 0.0), "atc": atc_t.get(tr, 0.0)}
    rec = {"iid": iid, "t_d": t_d, "fp": fp_of(tuples or []), "tuples": tuples or [],
           "n_orders": len(binst["work_orders"]), "n_running": len(site["running"]),
           "running_const": running_constant(instance, site), "atc_feasible": val["feasible"],
           "trades": trades}
    live = {"binst": binst, "avail": avail, "atc_sched": sched}
    return rec, live


def trade_input(binst, avail, trade, warm_sched) -> dict:
    """The solve input of one open trade: its orders, technicians, availability, warm start."""
    wos = [wo for wo in binst["work_orders"] if wo["trade"] == trade]
    techs = [t for t in binst["technicians"] if t["trade"] == trade]
    ids = {wo["id"] for wo in wos}
    meta = dict(binst["meta"])
    meta["id"] = "{}|{}".format(binst["meta"]["id"], trade)
    return {"sub": {"meta": meta, "trades": [trade], "technicians": techs, "work_orders": wos},
            "tech_available": {t["id"]: avail[t["id"]] for t in techs},
            "warm": [a for a in warm_sched["assignments"] if a["wo"] in ids]}


# --------------------------------------------------------------------------- #
# The decision-time constrained components (decision-time c, design 4.2)      #
# --------------------------------------------------------------------------- #
def cons_to_dict(cons) -> dict:
    return {"precedence": [list(e) for e in cons.precedence], "pins": list(cons.pins),
            "frozen": [list(f) for f in cons.frozen], "batches": [list(g) for g in cons.batches]}


def cons_from_dict(d):
    from l1oracle.cpsat_prec import Constraints

    return Constraints(precedence=tuple(tuple(e) for e in d["precedence"]),
                       pins=tuple(d["pins"]),
                       frozen=tuple((f[0], f[1], float(f[2])) for f in d["frozen"]),
                       batches=tuple(tuple(g) for g in d["batches"]))


def c_components(iid, t_d, live, site, avail, tuples) -> dict:
    """The instruction's constraints on the board at t_d, split into trade components.

    The running orders leave the board (they are availability and a constant),
    so their frozen slots leave the constraint set; an edge or a batch group
    that would leave the board is recorded as an error, never dropped.
    Releases are max(r', t_d) as on the relaxed board.  The constrained ATC
    schedule of the component is the K-dispatch of the proposal, used as an
    upper end only when it satisfies the constraints and the availability.
    """
    from l1oracle import cpsat_avail as ca
    from l1oracle.cpsat_prec import Constraints

    adj, sched = live["adjusted"], live["schedule"]
    run_ids = {r[0] for r in site["running"]}
    full = ca.Constraints.from_adjusted(adj)
    cons0 = Constraints(precedence=full.precedence, pins=full.pins,
                        frozen=tuple(f for f in full.frozen if f[0] not in run_ids),
                        batches=full.batches)
    t_dv = float(t_d)
    wos = []
    for wo in adj.instance["work_orders"]:
        if wo["id"] in run_ids:
            continue
        w = dict(wo)
        if float(w["release_bh"]) < t_dv:
            w["release_bh"] = t_dv
        wos.append(w)
    binst = {"meta": dict(adj.instance["meta"]), "trades": adj.instance.get("trades", []),
             "technicians": adj.instance["technicians"], "work_orders": wos}
    try:
        cons = cons0.restrict({wo["id"] for wo in wos})
    except ValueError as exc:
        return {"error": "constraint_leaves_board: {}".format(exc), "components": []}
    trade_of = {wo["id"]: wo["trade"] for wo in wos}
    by_t = defaultdict(list)
    for t in tuples or []:
        if t[0] in trade_of:
            by_t[trade_of[t[0]]].append(tuple(t))
    comps = []
    for trades in ca.trade_components(binst, cons):
        oids = {wo["id"] for wo in wos if wo["trade"] in trades}
        sub_cons = cons.restrict(oids)
        sub = ca.sub_instance(binst, trades)
        av = {t["id"]: avail[t["id"]] for t in sub["technicians"]}
        sub_sched = ca.restrict_schedule(sched, oids)
        bad = ca.check_constraints(sub, sub_sched, sub_cons) + ca.check_availability(sub_sched, av)
        comp_tuples = sorted([t for tr in trades for t in by_t.get(tr, [])], key=lambda t: t[0])
        tfps = {tr: (fp_of(by_t[tr]) if by_t.get(tr) else BASE_FP) for tr in trades}
        key = sha_text(json.dumps([iid, t_dv, list(trades), fp_of(comp_tuples), sub_cons.key(),
                                   sorted(av.items())], separators=(",", ":")))
        comps.append({"key": key, "iid": iid, "t_d": t_dv, "trades": list(trades),
                      "trade_fps": tfps, "n_orders": len(oids),
                      "n_edges": len(sub_cons.precedence), "n_pins": len(sub_cons.pins),
                      "n_batches": len(sub_cons.batches), "n_frozen": len(sub_cons.frozen),
                      "atc_obj": ca.schedule_wwt(sub, sub_sched), "atc_valid": not bad,
                      "atc_violations": bad[:5], "sub": sub, "cons": cons_to_dict(sub_cons),
                      "tech_available": av, "warm": sub_sched})
    return {"error": None, "components": comps}


# --------------------------------------------------------------------------- #
# Census worker: one instance, every item on it                                #
# --------------------------------------------------------------------------- #
_TASKS: list = []


def _winit(cores):
    cap_threads(1)
    if cores:
        os.sched_setaffinity(0, set(cores))


def _times(schedule) -> set:
    return {(a["wo"], a["start_bh"], a["end_bh"]) for a in schedule["assignments"]}


def _slots(schedule) -> set:
    return {(a["wo"], a["tech"], a["start_bh"], a["end_bh"]) for a in schedule["assignments"]}


def _pick(res, keys, prefix):
    return {prefix + k: res.get(k) for k in keys}


PRICE_KEYS = ("term_cert", "stage_cert", "term_feas", "stage_feas", "codes", "obj", "obj_orig",
              "lb", "lb_running", "gap", "ref2", "ref2_from", "constraining", "n_raised",
              "parse_ok", "infra")


def census_instance(ti) -> dict:
    """Every deterministic quantity of one instance's items (design 1-5)."""
    from l1adapter import dispatch as dispatch_mod
    import n8_causal as n8

    task = _TASKS[ti]
    t0 = time.perf_counter()
    inst = load_instance(task["path"])
    iid = inst["meta"]["id"]
    baseline = dispatch_mod.dispatch_baseline(inst, "atc", 0)
    by_id = {wo["id"]: wo for wo in inst["work_orders"]}
    trade_of = {wo["id"]: wo["trade"] for wo in inst["work_orders"]}
    out = {"iid": iid, "items": [], "seeds": {}, "boards": [], "relaxed_inputs": [],
           "c_components": [], "anchor_omni": {}, "sites": {}}
    trajs = {}
    for fk, seed in task["seeds"].items():
        traj = n8.trajectory(inst, seed, baseline)
        trajs[fk] = traj
        anc = gen_price(inst, EMPTY_RAW, seed, baseline, 0.0)
        out["seeds"][fk] = {"traj_times_equal": _times(traj) == _times(baseline),
                            "traj_slots_equal": _slots(traj) == _slots(baseline)}
        out["anchor_omni"][fk] = _pick(anc, ("term_cert", "obj", "obj_orig", "gap", "lb"), "")
    sites = {}      # (fk, t_d) -> decision-time state on K
    board_sites = {}  # t_d -> running set and availability (seed-free)
    need_boards = OrderedDict()   # (t_d, fp) -> tuples
    exec_up = {}   # (t_d, trade, trade_fp) -> min executed weighted tardiness on the board

    kf_func = KF_FUNCS[task.get("kf", "fix")]
    reading = task.get("reading", "primary")

    def site_for(fk, seed, t_d):
        key = (fk, t_d)
        if key in sites:
            return sites[key]
        traj = trajs[fk]
        state = n8.site_state(inst, traj, t_d, pm_known=True)
        known = n8.known_instance(inst, state)
        # Stage 2 decision 1: the standing frozen set on K is the running work
        # plus every seed order K holds (queued, running or scheduled); N8's
        # convention is kept beside it only for the continuity assertion A6.
        kf = kf_func(state, seed)
        kf8 = n8.known_frozen(state, seed)
        started = state["completed"] + state["in_progress"]
        k_ids = state["queue"] + state["in_progress"] + state["scheduled"]
        base_p = n8.pin_schedule(baseline, traj, started)
        frozen_r = list(started) + [o for o in seed if o not in set(started)]
        site = site_of(state, traj, t_d)
        avail = availability(inst, site)
        an = gen_price(known, EMPTY_RAW, kf, base_p, t_d, keep_live=True)
        an8 = an if kf8 == kf else gen_price(known, EMPTY_RAW, kf8, base_p, t_d)
        rw0 = gen_price(inst, EMPTY_RAW, frozen_r, base_p, t_d, keep_batch=k_ids)
        s = {"state": state, "known": known, "kf": kf, "kf8": kf8, "started": started,
             "k_ids": k_ids, "base_p": base_p, "frozen_r": frozen_r, "site": site,
             "avail": avail, "an": an, "an8": an8, "rw0": rw0,
             "rconst": running_constant(inst, site)}
        sites[key] = s
        bs = board_sites.setdefault(t_d, {"site": site, "avail": avail,
                                          "mult": avail_multiset(inst, avail),
                                          "running_ids": sorted(r[0] for r in site["running"]),
                                          "known_ids": sorted(site["known_ids"]),
                                          "seeds": []})
        bs["seeds"].append({"fk": fk, "mult_equal": avail_multiset(inst, avail) == bs["mult"],
                            "running_equal": sorted(r[0] for r in site["running"])
                            == bs["running_ids"],
                            "known_equal": sorted(site["known_ids"]) == bs["known_ids"]})
        need_boards.setdefault((t_d, BASE_FP), [])
        note_exec(t_d, [], an, site)
        return s

    def note_exec(t_d, tuples, res, site):
        live = res.get("_live") or {}
        if res.get("term_feas") != "applied_uncertified" or "schedule" not in live:
            return
        run_ids = {r[0] for r in site["running"]}
        adj, sched = live["adjusted"], live["schedule"]
        wt = trade_wwt_of(adj.instance, sched, skip=run_ids)
        by_t = defaultdict(list)
        for t in tuples or []:
            if t[0] in trade_of and t[0] not in run_ids:
                by_t[trade_of[t[0]]].append(tuple(t))
        trades = sorted({wo["trade"] for wo in adj.instance["work_orders"]
                         if wo["id"] not in run_ids})
        for tr in trades:
            tfp = fp_of(by_t[tr]) if by_t.get(tr) else BASE_FP
            k = (t_d, tr, tfp)
            v = wt.get(tr, 0.0)
            if k not in exec_up or v < exec_up[k]:
                exec_up[k] = v

    for it in task["items"]:
        fk, seed = it["fk"], it["seed"]
        traj = trajs[fk]
        starts = {a["wo"]: float(a["start_bh"]) for a in traj["assignments"]}
        iss = issuability(it, by_id, starts)
        t_d = decision_instant_of(iss, reading)
        ops = it["ops"]
        raw = json.dumps({"operations": ops})
        row = OrderedDict(item_id=it["item_id"], set=it["set"], fk=fk, t_d=t_d,
                          reading=reading)
        row.update({k: iss[k] for k in ("n_ref", "t_known", "t_start", "issuable",
                                        "issuable_strict", "ref_all_pm")})
        # ---- omniscient reading (t_d = 0, full instance): the published guard
        om = gen_price(inst, raw, seed, baseline, 0.0, unguarded=True, ref2=True)
        row.update(_pick(om, PRICE_KEYS + ("term_ung",), "om_"))
        row["om_fp"] = None if om["tuples"] is None else fp_of(om["tuples"])
        # ---- decision-time reading on K
        s = site_for(fk, seed, t_d)
        st = s["state"]
        ref_set = set(iss["ref_ids"])
        row.update(n_known=len(s["known"]["work_orders"]), n_queue=len(st["queue"]),
                   n_scheduled=len(st["scheduled"]), n_in_progress=len(st["in_progress"]),
                   n_completed=len(st["completed"]), n_unknown=len(st["unknown"]),
                   ref_completed=sorted(ref_set & set(st["completed"])),
                   ref_running=sorted(ref_set & set(st["in_progress"])),
                   ref_unknown=sorted(ref_set & set(st["unknown"])))
        explicit, members = n8.named_orders(ops, inst)
        kset = set(s["k_ids"])
        row.update(n_batch_members=len(members),
                   n_batch_members_known=sum(1 for m in members if m in kset),
                   names_unknown=sorted(o for o in explicit if o in set(st["unknown"])),
                   names_completed=sorted(o for o in explicit if o in set(st["completed"])),
                   names_running=sorted(o for o in explicit if o in set(st["in_progress"])),
                   seed_not_frozen_on_K=sorted(set(seed) & set(st["scheduled"])))
        need_live = True
        # Stage 3 addition A: an operation naming work running at t_d is refused.
        run_ids = list(st["in_progress"])
        row["names_running_any"] = sorted(
            (set(explicit) | set(members)) & set(run_ids))
        dt = gen_price(s["known"], raw, s["kf"], s["base_p"], t_d, ref2=True,
                       keep_live=need_live, running_ids=run_ids)
        row.update(_pick(dt, PRICE_KEYS, "dt_"))
        row["dt_fp"] = None if dt["tuples"] is None else fp_of(dt["tuples"])
        row["dt_n_changed"] = None if dt["tuples"] is None else len(dt["tuples"])
        # N8's frozen-set convention, for A6 only.
        row["kf_differs"] = s["kf8"] != s["kf"]
        if row["kf_differs"]:
            dt8 = gen_price(s["known"], raw, s["kf8"], s["base_p"], t_d, running_ids=run_ids)
        else:
            dt8 = dt
        row.update(a6_term_cert=dt8["term_cert"], a6_stage_cert=dt8["stage_cert"],
                   a6_term_feas=dt8["term_feas"], a6_gap=dt8["gap"], a6_obj=dt8["obj"],
                   a6_lb=dt8["lb"], a6_an_gap=s["an8"]["gap"])
        an = s["an"]
        row.update(an_obj=an["obj"], an_obj_orig=an["obj_orig"], an_lb=an["lb"],
                   an_gap=an["gap"], an_lb_running=an["lb_running"], an_term=an["term_cert"],
                   rconst=s["rconst"], n_running=len(s["site"]["running"]))
        row["rw0_obj"], row["rw0_obj_orig"] = s["rw0"]["obj"], s["rw0"]["obj_orig"]
        row["rw0_term"] = s["rw0"]["term_cert"]
        # ---- realised full-window run of the proposal from t_d
        rw = None
        if "applied_uncertified" in (dt["term_feas"], om["term_feas"], dt8["term_feas"]):
            rw = gen_price(inst, raw, s["frozen_r"], s["base_p"], t_d, keep_batch=s["k_ids"])
        if dt["term_feas"] == "applied_uncertified":
            note_exec(t_d, dt["tuples"], dt, s["site"])
            if dt["stage_cert"] == "qual":
                need_boards.setdefault((t_d, row["dt_fp"]), dt["tuples"])
        row["rw_term"] = None if rw is None else rw["term_cert"]
        row["rw_term_feas"] = None if rw is None else rw["term_feas"]
        row["rw_obj"] = None if rw is None else rw["obj"]
        row["rw_obj_orig"] = None if rw is None else rw["obj_orig"]
        # ---- decision-time c components (V3, twins, held-out)
        row["c_needed"] = bool(it.get("c_needed")) and reading == "primary"
        row["c_error"] = None
        row["c_keys"] = None
        if row["c_needed"] and dt["term_feas"] == "applied_uncertified":
            cc = c_components(iid, t_d, dt["_live"], s["site"], s["avail"], dt["tuples"])
            row["c_error"] = cc["error"]
            row["c_keys"] = [c["key"] for c in cc["components"]]
            row["c_trades"] = [c["trades"] for c in cc["components"]]
            out["c_components"].extend(cc["components"])
        elif row["c_needed"]:
            row["c_error"] = "not_executed_on_K:{}".format(dt["term_cert"])
        dt.pop("_live", None)
        out["items"].append(row)

    # ---- boards: per trade LB2, ATC, best executed schedule; open-trade inputs
    seen_inputs = set()
    for (t_d, fp), tuples in need_boards.items():
        bs = board_sites[t_d]
        rec, live = board_record(inst, iid, bs["site"], tuples)
        rec["seeds"] = bs["seeds"]
        rec["avail_multiset"] = bs["mult"]
        for tr, tv in rec["trades"].items():
            ex = exec_up.get((t_d, tr, tv["trade_fp"]))
            tv["exec_upper"] = ex
            ups = [(tv["atc"], "atc")] + ([(ex, "executed")] if ex is not None else [])
            tv["upper0"], tv["upper0_source"] = min(ups)
            tv["closed_by_lb2"] = tv["upper0"] <= tv["lb2"] + CLOSE_TOL_BH
            if not tv["closed_by_lb2"]:
                k = (t_d, tr, tv["trade_fp"])
                if k not in seen_inputs:
                    seen_inputs.add(k)
                    ti_ = trade_input(live["binst"], live["avail"], tr, live["atc_sched"])
                    ti_.update(iid=iid, t_d=t_d, trade=tr, trade_fp=tv["trade_fp"],
                               lb2=tv["lb2"], atc=tv["atc"], exec_upper=ex,
                               n_orders=tv["n_orders"], n_techs=tv["n_techs"])
                    out["relaxed_inputs"].append(ti_)
        out["boards"].append(rec)
    out["wall_s"] = time.perf_counter() - t0
    return out


def run_pool(fn, n, cores, workers, order=None):
    import multiprocessing as mp

    order = list(range(n)) if order is None else order
    out = []
    if workers <= 1:
        _winit(cores)
        for i in order:
            out.append(fn(i))
    else:
        ctx = mp.get_context("fork")
        with ctx.Pool(workers, initializer=_winit, initargs=(cores,), maxtasksperchild=4) as pool:
            for res in pool.imap_unordered(fn, order):
                out.append(res)
                print("[n11]   done {} ({:.0f}s), {} of {}".format(
                    res.get("iid"), res.get("wall_s", 0.0), len(out), len(order)), flush=True)
    return out


# --------------------------------------------------------------------------- #
# Census: driver and the assertions it carries (A1-A3, A5 direct, A6-A9, A12)  #
# --------------------------------------------------------------------------- #
def canonical_ops(item) -> list:
    return list(item.get(CANONICAL_FIELD[item["primary_class"]]) or [])


def num_or_none(v):
    if v in ("", None):
        return None
    return float(v)


def load_n8_items() -> dict:
    return {r["item_id"]: r for r in read_jsonl(N8_ITEMS)}


def load_dg1() -> dict:
    out = {}
    for r in read_csv_comments(DG1_PATH):
        if r["reading"] == "canonical":
            out[(r["item_id"], r["config"])] = r
    return out


def c_population(pub, held) -> dict:
    """item_id -> (set, role) for the decision-time c label (N9's population)."""
    out = {}
    for name, rows in (("published", pub), ("heldout", held)):
        v3 = sorted((r for r in rows.values() if r["primary_class"] == "V3"),
                    key=lambda r: r["item_id"])
        for r in v3:
            out[r["item_id"]] = (name, "V3")
            out[r["twin_id"]] = (name, "twin")
    return out


def build_tasks(pub, held, cpop) -> list:
    by_inst = OrderedDict()
    for set_name, rows in (("published", pub), ("heldout", held)):
        for it in rows.values():
            iid = it["instance"]["instance_id"]
            t = by_inst.setdefault(iid, {"iid": iid, "path": instance_path(it), "items": [],
                                         "seeds": OrderedDict()})
            seed = list(it["episode"]["frozen_seed"] or [])
            fk = frozen_key(seed)
            t["seeds"].setdefault(fk, seed)
            ops = canonical_ops(it) if set_name == "published" else list(it.get("gold_ops") or [])
            t["items"].append({"item_id": it["item_id"], "set": set_name, "fk": fk,
                               "seed": seed, "ops": ops, "referenced": it["referenced"],
                               "c_needed": it["item_id"] in cpop})
    return list(by_inst.values())


def cmd_census(args) -> int:
    global _TASKS
    pin_cores(args.cores_t)
    cap_threads(1)
    reading = getattr(args, "reading", "primary")
    base_dir = OUT if reading == "primary" else OUT / reading
    out_dir = base_dir / "smoke" if args.instances else base_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    check = Checker()
    t_start = time.time()
    pub_rows = load_published(check)
    held_rows = load_heldout(check)
    pub = OrderedDict((r["item_id"], r) for r in pub_rows)
    held = OrderedDict((r["item_id"], r) for r in held_rows)
    cpop = c_population(pub, held)
    check.true("A1", "decision-time c population is N9's 880 items", len(cpop) == 880,
               len(cpop))
    for iid_, (sname, role) in cpop.items():
        it = pub.get(iid_) or held.get(iid_)
        check.true("A1", "c item carries no standing frozen set: " + iid_,
                   not it["episode"]["frozen_seed"])
    tasks = build_tasks(pub, held, cpop)
    if args.instances:
        keep = set(args.instances.split(","))
        tasks = [t for t in tasks if t["iid"] in keep]
    for t in tasks:
        t["kf"], t["reading"] = "fix", reading
    _TASKS = tasks
    order = sorted(range(len(tasks)), key=lambda i: -sum(len(t["items"]) for t in [tasks[i]])
                   * max(1, len(tasks[i]["items"])))
    # Large instances first: the replay strata are cheap, storm strata dominate.
    order = sorted(range(len(tasks)), key=lambda i: (
        0 if "c10_storm" in tasks[i]["iid"] else 1 if "c09_storm" in tasks[i]["iid"] else 2,
        -len(tasks[i]["items"])))
    print("[n11 census] {} instances, {} items, workers {} on cores {}".format(
        len(tasks), sum(len(t["items"]) for t in tasks), args.workers, args.cores_t), flush=True)
    results = run_pool(census_instance, len(tasks), args.cores_t, args.workers, order)
    wall = time.time() - t_start

    items, boards, rel_inputs, comps = [], [], [], {}
    seeds = {}
    anchor_omni = {}
    for res in sorted(results, key=lambda r: r["iid"]):
        items.extend(res["items"])
        boards.extend(res["boards"])
        rel_inputs.extend(res["relaxed_inputs"])
        for c in res["c_components"]:
            comps.setdefault(c["key"], c)
        for fk, v in res["seeds"].items():
            seeds[(res["iid"], fk)] = v
        for fk, v in res["anchor_omni"].items():
            anchor_omni[(res["iid"], fk)] = v
    by_item = {r["item_id"]: r for r in items}
    meta_of = {}
    for set_name, rows in (("published", pub), ("heldout", held)):
        for it in rows.values():
            meta_of[it["item_id"]] = it
    for r in items:
        it = meta_of[r["item_id"]]
        r["primary_class"] = it["primary_class"]
        r["subclass"] = it["subclass"]
        r["stratum"] = it["instance"]["stratum"]
        r["instance_id"] = it["instance"]["instance_id"]
        r["twin_id"] = it.get("twin_id")
        r["quality_visible"] = bool(it.get("quality_visible_candidate"))
        r["register"] = it.get("register")
        ops = canonical_ops(it) if r["set"] == "published" else list(it.get("gold_ops") or [])
        r["n_ops"] = len(ops)
        r["op_types"] = "|".join(sorted({o.get("op", "?") for o in ops if isinstance(o, dict)}))
        r["split"] = op_split(ops)
        r["c_role"] = cpop.get(r["item_id"], (None, None))[1]
        r["frozen_seed"] = r.pop("fk")

    smoke = bool(args.instances)
    run_checks_census(check, items, boards, seeds, anchor_omni, pub, held, smoke)
    rep = check.report()
    write_jsonl(out_dir / "items.jsonl", items)
    write_jsonl(out_dir / "boards.jsonl", boards)
    write_jsonl(out_dir / "relaxed_inputs.jsonl", rel_inputs)
    write_jsonl(out_dir / "c_components.jsonl", list(comps.values()))
    summ = census_summary(items, boards, rel_inputs, comps)
    meta = {"version": VERSION, "stage": "census", "reading": reading, "frozen_set": "fix",
            "finished": now_iso(), "wall_s": wall,
            "cores": args.cores_t, "workers": args.workers,
            "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
            "load_avg_end": loadavg(), "host": socket.gethostname(),
            "python": sys.version.split()[0], "smoke": smoke, "summary": summ,
            "inputs": input_hashes(),
            "outputs": {p.name: sha256_file(p) for p in sorted(out_dir.glob("*.jsonl"))}}
    write_json(out_dir / "census_meta.json", meta)
    rep_path = out_dir / "census_assertions.json"
    check.fatal(rep_path, {"outputs": meta["outputs"], "inputs": meta["inputs"],
                           "finished": meta["finished"]})
    print(json.dumps(summ, indent=1), flush=True)
    print("[n11 census] PASS: {} checks in {:.0f}s".format(rep["n_checks"], wall), flush=True)
    return 0


def op_split(ops):
    if not ops:
        return "empty"
    kinds = {o.get("op") for o in ops if isinstance(o, dict)}
    if kinds & FIELD_OPS:
        return "field_changing"
    if kinds <= CONSTRAINING_OPS:
        return "sequencing_only"
    return "other"


def input_hashes() -> dict:
    import suite_gate as sg

    files = [sg.SUITE_PATH, HELDOUT_PATH, EXT_PATH, EXT_NEG_PATH, sg.INSTANCE_MANIFEST_PATH,
             DG1_PATH, ANCHOR_PATH, N8_ITEMS, ANALYSIS / "N2_rows_direct.csv",
             ANALYSIS / "N2_rows_e2e.csv", ANALYSIS / "N2_ref2_cache.jsonl",
             ANALYSIS / "N9_heldout.csv", ANALYSIS / "N9_published_v3.csv",
             ANALYSIS / "N10_rows.csv", ANALYSIS / "DG14_delta_baselines.csv",
             ANALYSIS / "DG17_e2e_delta.csv", ORACLE_V1 / "trade_solves.jsonl",
             ORACLE_V1 / "brackets.jsonl", ORACLE_V1 / "items.jsonl",
             N9_DIR / "solves.jsonl", N9_DIR / "brackets.jsonl"]
    code = [Path(__file__), CODE / "l1oracle" / "cpsat_avail.py",
            CODE / "l1oracle" / "cpsat_prec.py", SCRIPTS_DIR / "n8_causal.py",
            CODE / "l1guard" / "guard.py", CODE / "l1guard" / "guard_v11.py",
            CODE / "l1guard" / "lb2.py", CODE / "l1adapter" / "apply.py",
            CODE / "l1adapter" / "dispatch.py", CODE / "l1adapter" / "evaluate.py"]
    out = {}
    for p in files + code:
        p = Path(p)
        out[str(p.relative_to(ROOT)) if str(p).startswith(str(ROOT)) else str(p)] = (
            sha256_file(p) if p.is_file() else None)
    return out


def run_checks_census(check, items, boards, seeds, anchor_omni, pub, held, smoke):
    ITEM_INDEX.clear()
    ITEM_INDEX.update((r["item_id"], r) for r in items)
    anchors = load_anchor_records()
    dg1 = load_dg1()
    n8 = load_n8_items()
    # ---- A2: trajectory, seed invariance of the board site
    for (iid, fk), v in seeds.items():
        check.true("A2", "trajectory starts and ends equal the plain ATC on {} [{}]".format(
            iid, fk), v["traj_times_equal"])
    for b in boards:
        for s in b["seeds"]:
            check.true("A2", "board site of {} t_d={} is seed-invariant ({})".format(
                b["iid"], b["t_d"], s["fk"]),
                s["mult_equal"] and s["running_equal"] and s["known_equal"])
    # ---- A3: issuability
    pub_items = [r for r in items if r["set"] == "published"]
    for r in items:
        if r["issuable"]:
            check.true("A3", "issuable item names no completed or running order: " + r["item_id"],
                       not r["ref_completed"] and not r["ref_running"],
                       "{} {}".format(r["ref_completed"], r["ref_running"]))
            check.true("A3", "issuable item names no order unknown at t_d: " + r["item_id"],
                       not r["ref_unknown"], r["ref_unknown"])
    if not smoke:
        n_closed = sum(1 for r in pub_items if not r["issuable"])
        n_strict = sum(1 for r in pub_items if not r["issuable_strict"])
        check.true("A3", "items not issuable (closed rule) = 277", n_closed == 277, n_closed)
        check.true("A3", "items not issuable (strict rule) = 731", n_strict == 731, n_strict)
    # ---- A5 direct: the omniscient reading is the published guard
    n2rows = {r["item_id"]: r for r in read_csv_comments(ANALYSIS / "N2_rows_direct.csv")}
    ref2_cache = {}
    for r in read_jsonl(ANALYSIS / "N2_ref2_cache.jsonl"):
        ref2_cache[r["key"]] = r
    n_qual = 0
    for r in pub_items:
        iid = r["instance_id"]
        it = pub[r["item_id"]]
        d = dg1[(r["item_id"], "G_CERT")]
        check.true("A5", "omniscient G_CERT terminal equals DG1: " + r["item_id"],
                   r["om_term_cert"] == d["terminal"], "{} vs {}".format(r["om_term_cert"],
                                                                          d["terminal"]))
        check.true("A5", "omniscient G_CERT stage equals DG1: " + r["item_id"],
                   r["om_stage_cert"] == d["stage_reached"],
                   "{} vs {}".format(r["om_stage_cert"], d["stage_reached"]))
        if num_or_none(d["certified_gap"]) is not None:
            check.close("A5", "omniscient gap equals DG1: " + r["item_id"], r["om_gap"],
                        float(d["certified_gap"]), CHECK_TOL)
        if num_or_none(d["obj_bh"]) is not None:
            check.close("A5", "omniscient objective equals DG1: " + r["item_id"], r["om_obj"],
                        float(d["obj_bh"]), CHECK_TOL)
        for cfg, key in (("G_FEAS", "om_term_feas"), ("UNGUARDED", "om_term_ung")):
            dd = dg1.get((r["item_id"], cfg))
            check.true("A5", "omniscient {} terminal equals DG1: {}".format(cfg, r["item_id"]),
                       dd is not None and r[key] == dd["terminal"],
                       "{} vs {}".format(r[key], None if dd is None else dd["terminal"]))
        fk = r["frozen_seed"]
        a = anchors[(iid, fk)]
        r["pub_anchor_wwt"] = float(a["wwt_original_bh"])
        r["pub_anchor_gap"] = float(a["gap"])
        if r["om_stage_cert"] == "qual":
            n_qual += 1
            om_prices(r)
            n2 = n2rows.get(r["item_id"])
            check.true("A5", "N2 direct row exists: " + r["item_id"], n2 is not None)
            if n2 is None:
                continue
            for k_mine, k_pub in (("om_obj", "obj"), ("om_lb", "lb_cert"), ("om_gap", "gap_cert"),
                                  ("om_ref2", "ref2"), ("om_p_G-CERT", "p_G-CERT"),
                                  ("om_p_G-CERT-M", "p_G-CERT-M"), ("om_p_D-REL1", "p_D-REL1"),
                                  ("om_p_D-REL2", "p_D-REL2"), ("om_p_D-ABS", "p_D-ABS")):
                check.close("A5", "{} equals N2 {} on {}".format(k_mine, k_pub, r["item_id"]),
                            r[k_mine], num_or_none(n2[k_pub]), 1e-6)
            if r["om_constraining"]:
                ukey = unit_key(iid, it["episode"]["frozen_seed"], canonical_ops(it))
                c = ref2_cache.get(ukey)
                check.true("A5", "N2 WT_ref2 cache row exists: " + r["item_id"], c is not None)
                if c is not None:
                    check.close("A5", "WT_ref2 equals N2_ref2_cache on " + r["item_id"],
                                r["om_ref2"], c["ref2"], CHECK_TOL)
    if not smoke:
        check.true("A5", "direct rows reaching the quality stage = 1635", n_qual == 1635, n_qual)
        for g, (ben, v3) in DG14_TALLY.items():
            s = TAU if g == "G-CERT" else DG14[g]
            nb = sum(1 for r in pub_items if r["om_stage_cert"] == "qual"
                     and r["primary_class"] == "benign" and price_refers(r, "om_p_" + g, s))
            nv = sum(1 for r in pub_items if r["om_stage_cert"] == "qual"
                     and r["primary_class"] == "V3" and price_refers(r, "om_p_" + g, s))
            check.true("A5", "DG14 matched tally of {} (benign, V3) = {}".format(g, (ben, v3)),
                       (nb, nv) == (ben, v3), (nb, nv))
    for (iid, fk), v in anchor_omni.items():
        a = anchors[(iid, fk)]
        check.close("A5", "omniscient anchor objective equals rule_anchor on {} [{}]".format(
            iid, fk), v["obj"], float(a["wwt_adjusted_bh"]), CHECK_TOL)
        check.close("A5", "omniscient anchor gap equals rule_anchor on {} [{}]".format(iid, fk),
                    v["gap"], float(a["gap"]), CHECK_TOL)
    # Held-out and published V3 rows of N9 (gate inputs at t = 0).
    for path in (ANALYSIS / "N9_heldout.csv", ANALYSIS / "N9_published_v3.csv"):
        for n9r in read_csv_comments(path):
            r = ITEM_INDEX.get(n9r["item_id"])
            if r is None:
                continue
            fk = r["frozen_seed"]
            a = anchors[(r["instance_id"], fk)]
            r["pub_anchor_wwt"] = float(a["wwt_original_bh"])
            r["pub_anchor_gap"] = float(a["gap"])
            om_prices(r)
            for k_mine, k_pub in (("om_obj", "obj"), ("om_gap", "gap_cert"), ("om_ref2", "ref2"),
                                  ("om_p_G-CERT", "p_G-CERT"), ("om_p_G-CERT-M", "p_G-CERT-M"),
                                  ("om_p_D-REL1", "p_D-REL1"), ("om_p_D-REL2", "p_D-REL2"),
                                  ("om_p_D-ABS", "p_D-ABS")):
                check.close("A5", "{} equals {} {} on {}".format(k_mine, path.name, k_pub,
                                                                 r["item_id"]),
                            r[k_mine], num_or_none(n9r[k_pub]), 1e-6)
    # ---- A6: continuity with N8's planned-known reading
    # Stage 2: A6 runs with N8's frozen-set function (the a6_* fields); every
    # reported quantity runs with the fix (the dt_* fields).
    n_a6 = 0
    for r in (pub_items if all(x.get("reading", "primary") == "primary" for x in items) else []):
        n8r = n8.get(r["item_id"])
        if n8r is None or n8r.get("t_d_pm") is None:
            continue
        if abs(float(n8r["t_d_pm"]) - r["t_d"]) > 1e-12:
            continue
        n_a6 += 1
        check.true("A6", "terminal equals N8 (_pm) on " + r["item_id"],
                   r["a6_term_cert"] == n8r["terminal_c_pm"],
                   "{} vs {}".format(r["a6_term_cert"], n8r["terminal_c_pm"]))
        mine_m = (None if r["a6_gap"] is None or r["a6_an_gap"] is None
                  else r["a6_gap"] - r["a6_an_gap"])
        for mine, theirs, what in ((r["a6_gap"], n8r["g_c_pm"], "g_c"),
                                   (mine_m, n8r["m_c_pm"], "m_c"),
                                   (r["a6_obj"] if r["a6_stage_cert"] == "qual" else None,
                                    n8r["obj_K_pm"], "obj_K"),
                                   (r["a6_lb"], n8r["lb_K_pm"], "lb_K"),
                                   (r["rw_obj"] if r["a6_stage_cert"] == "qual" else None,
                                    n8r["wwt_real_with_pm"], "realised objective")):
            check.close("A6", "{} equals N8 (_pm) on {}".format(what, r["item_id"]), mine,
                        theirs, N8_TOL)
    if not smoke and all(x.get("reading", "primary") == "primary" for x in items):
        check.true("A6", "items compared with N8 = 1704", n_a6 == 1704, n_a6)
    # ---- A7: the no-proposal realised run is the published anchor
    for r in items:
        a = anchors[(r["instance_id"], r["frozen_seed"])]
        check.close("A7", "no-proposal realised run equals the anchor on " + r["item_id"],
                    r["rw0_obj_orig"], float(a["wwt_original_bh"]), CHECK_TOL)
        check.close("A7", "no-proposal realised run (adjusted) equals the anchor on "
                    + r["item_id"], r["rw0_obj"], float(a["wwt_adjusted_bh"]), CHECK_TOL)
    # ---- A8: realised at t_d = 0 is the full-window executed schedule
    n_a8 = 0
    for r in pub_items:
        if r["t_d"] != 0.0 or r["n_batch_members_known"] != r["n_batch_members"]:
            continue
        if r["om_term_feas"] != "applied_uncertified":
            continue
        n_a8 += 1
        d = dg1[(r["item_id"], "G_CERT")]
        check.true("A8", "realised run exists at t_d = 0 on " + r["item_id"],
                   r["rw_obj"] is not None)
        check.close("A8", "realised adjusted-field objective equals the full window on "
                    + r["item_id"], r["rw_obj"], r["om_obj"], CHECK_TOL)
        if num_or_none(d["obj_bh"]) is not None:
            check.close("A8", "realised objective equals DG1 on " + r["item_id"], r["rw_obj"],
                        float(d["obj_bh"]), CHECK_TOL)
        check.close("A8", "realised original-field objective equals the full window on "
                    + r["item_id"], r["rw_obj_orig"], r["om_obj_orig"], CHECK_TOL)
        check.true("A8", "realised terminal equals the full window on " + r["item_id"],
                   r["rw_term"] == r["om_term_cert"])
    CENSUS_COUNTS["a8_items"] = n_a8
    CENSUS_COUNTS["a6_items"] = n_a6
    # ---- A9 (census part) and A12
    bkey = {(b["iid"], b["t_d"], b["fp"]): b for b in boards}
    for b in boards:
        check.true("A9", "board ATC dispatch is feasible: {} t_d={} {}".format(
            b["iid"], b["t_d"], b["fp"][:10]), b["atc_feasible"])
        for tr, tv in b["trades"].items():
            check.true("A9", "LB2 <= upper on {} t_d={} {} {}".format(b["iid"], b["t_d"],
                                                                     b["fp"][:10], tr),
                       tv["lb2"] <= tv["upper0"] + CHECK_TOL,
                       "{} > {}".format(tv["lb2"], tv["upper0"]))
    for r in items:
        if r["dt_lb"] is not None and r["dt_obj"] is not None:
            check.true("A9", "LB_K <= obj_K on " + r["item_id"],
                       r["dt_lb"] <= r["dt_obj"] + CHECK_TOL)
        if r["an_lb"] is not None:
            check.true("A9", "anchor LB_K <= obj_K on " + r["item_id"],
                       r["an_lb"] <= r["an_obj"] + CHECK_TOL)
        b0 = bkey.get((r["instance_id"], r["t_d"], BASE_FP))
        check.true("A12", "anchor board exists for " + r["item_id"], b0 is not None)
        if b0 is None:
            continue
        check.close("A12", "running constant equals bound_known lb_running on "
                    + r["item_id"], b0["running_const"], r["an_lb_running"], CHECK_TOL)
        lb2_sum = sum(tv["lb2"] for tv in b0["trades"].values())
        check.close("A12", "anchor board LB2 + running constant equals LB_K on "
                    + r["item_id"], lb2_sum + b0["running_const"], r["an_lb"], CHECK_TOL)
        if r["dt_stage_cert"] == "qual":
            b = bkey.get((r["instance_id"], r["t_d"], r["dt_fp"]))
            check.true("A12", "proposal board exists for " + r["item_id"], b is not None)
            if b is not None:
                check.close("A12", "proposal board running constant equals LB_K's on "
                            + r["item_id"], b["running_const"], r["dt_lb_running"], CHECK_TOL)
                lo = sum(tv["lb2"] for tv in b["trades"].values()) + b["running_const"]
                check.close("A12", "proposal board LB2 sum equals LB_K on " + r["item_id"],
                            lo, r["dt_lb"], CHECK_TOL)
                check.true("A9", "obj_K at or above the board's LB2 end on " + r["item_id"],
                           r["dt_obj"] >= lo - CHECK_TOL, "{} < {}".format(r["dt_obj"], lo))


ITEM_INDEX: dict = {}
CENSUS_COUNTS: dict = {}


def unit_key(iid, frozen, ops):
    blob = json.dumps([iid, list(frozen), ops], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def price_refers(r, key, setting):
    p = r.get(key)
    return p is not None and p > setting


def om_prices(r):
    """N2's prices on the omniscient reading (published anchor as reference 1)."""
    obj, ref1 = r["om_obj"], r["pub_anchor_wwt"]
    r["om_p_G-CERT"] = r["om_gap"]
    r["om_p_G-CERT-M"] = None if r["om_gap"] is None else r["om_gap"] - r["pub_anchor_gap"]
    r["om_p_D-REL1"] = None if obj is None else rel_delta(obj, ref1)
    r["om_p_D-REL2"] = None if obj is None or r["om_ref2"] is None else rel_delta(obj, r["om_ref2"])
    r["om_p_D-ABS"] = None if obj is None else round(obj - ref1, ROUND_BH)


def dt_prices(r):
    """Every design's price on K at t_d (design 3)."""
    obj, ref1, ref2 = r["dt_obj"], r["an_obj"], r["dt_ref2"]
    ok = r["dt_stage_cert"] == "qual"
    r["p_G-CERT"] = r["dt_gap"] if ok else None
    r["p_G-CERT-M"] = (r["dt_gap"] - r["an_gap"]) if ok and r["an_gap"] is not None else None
    r["p_D-REL1"] = rel_delta(obj, ref1) if ok else None
    r["p_D-REL2"] = rel_delta(obj, ref2) if ok and ref2 is not None else None
    r["p_D-ABS"] = round(obj - ref1, ROUND_BH) if ok else None


def census_summary(items, boards, rel_inputs, comps) -> dict:
    sizes = Counter()
    for ti in rel_inputs:
        n = ti["n_orders"]
        sizes["<=150" if n <= 150 else "<=400" if n <= 400 else "<=700" if n <= 700
              else "<=1500" if n <= 1500 else ">1500"] += 1
    n_trades = sum(len(b["trades"]) for b in boards)
    closed = sum(1 for b in boards for tv in b["trades"].values() if tv["closed_by_lb2"])
    c_sizes = Counter()
    c_maybe_closed = 0
    lb2_of = {}
    for b in boards:
        for tr, tv in b["trades"].items():
            lb2_of[(b["iid"], b["t_d"], tr, tv["trade_fp"])] = tv["lb2"]
    for c in comps.values():
        lb = sum(lb2_of.get((c["iid"], c["t_d"], tr, c["trade_fps"][tr]), 0.0)
                 for tr in c["trades"])
        if c["atc_valid"] and c["atc_obj"] <= lb + CLOSE_TOL_BH:
            c_maybe_closed += 1
        n = c["n_orders"]
        c_sizes["<=150" if n <= 150 else "<=400" if n <= 400 else "<=700" if n <= 700
                else "<=1500" if n <= 1500 else ">1500"] += 1
    pub = [r for r in items if r["set"] == "published"]
    return {"items": len(items), "published": len(pub),
            "published_not_issuable_closed": sum(1 for r in pub if not r["issuable"]),
            "published_not_issuable_strict": sum(1 for r in pub if not r["issuable_strict"]),
            "boards": len(boards), "board_trades": n_trades, "trades_closed_by_lb2": closed,
            "open_relaxed_trades": len(rel_inputs), "open_relaxed_by_size": dict(sizes),
            "c_components": len(comps), "c_components_closed_by_lb2_already": c_maybe_closed,
            "c_components_by_size": dict(c_sizes),
            "c_items_with_error": sum(1 for r in items if r["c_needed"] and r["c_error"]),
            "a6_items": CENSUS_COUNTS.get("a6_items"), "a8_items": CENSUS_COUNTS.get("a8_items")}


# --------------------------------------------------------------------------- #
# Omni: the omniscient reading of the logged end-to-end rows (A4, A5 e2e, A10) #
# --------------------------------------------------------------------------- #
E1_SOURCES = ("e1_eval_qwen14b", "e1_eval_qwen27b", "e1_eval_glm9b", "e1_eval_gpt54mini",
              "e1_eval_deepseek", "e1_eval_sonnet5", "e1_eval_opus5", "e1_eval_sol")
N3_SOURCES = ("n3_eval_opus", "n3_eval_sol", "n3_eval_sonnet", "n3_eval_openai",
              "n3_eval_deepseek", "n3neg_eval_opus", "n3neg_eval_sol", "n3neg_eval_sonnet",
              "n3neg_eval_openai")
SRC_TO_ARM = {"e1_eval_qwen14b": "qwen3-14b", "e1_eval_qwen27b": "qwen3.6-27b-fp8",
              "e1_eval_glm9b": "glm-4-9b", "e1_eval_gpt54mini": "openai",
              "e1_eval_deepseek": "deepseek", "e1_eval_sonnet5": "sonnet",
              "e1_eval_opus5": "opus", "e1_eval_sol": "sol"}
E2E_MODE = "M_constrained"


def thinking_label(v):
    return "-" if v is None else str(v)


def raw_key(raw) -> str:
    if isinstance(raw, str):
        return "t:" + raw
    return "o:" + json.dumps(raw, sort_keys=True)


def load_e1(check) -> list:
    """Every E1 row joined line by line to its three verdicts (keys asserted)."""
    rows = []
    for src in E1_SOURCES:
        d = RESULTS / src
        props = read_jsonl(d / "proposals.jsonl")
        vs = {c: read_jsonl(d / "verdicts_{}.jsonl".format(c))
              for c in ("G_CERT", "G_FEAS", "UNGUARDED")}
        check.true("A4", "{} verdict files align with the proposals".format(src),
                   all(len(v) == len(props) for v in vs.values()))
        for i, p in enumerate(props):
            ex = p.get("extra") or {}
            key = (p["instruction_id"], p["mode"], ex.get("thinking"), int(ex.get("repeat", 0)))
            vrow = {}
            for c, v in vs.items():
                vr = v[i]
                ok = (vr["item_id"], vr["mode"], vr.get("thinking"), int(vr["repeat"])) == key
                check.true("A4", "{} line {} joins its {} verdict".format(src, i, c), ok)
                vrow[c] = vr
            pv = p.get("verdict") or {}
            rows.append({"src": src, "item_id": p["instruction_id"], "mode": p["mode"],
                         "thinking": ex.get("thinking"), "repeat": int(ex.get("repeat", 0)),
                         "raw": p.get("raw_output") or "", "frozen": list(p.get("frozen_seed") or []),
                         "parsed_ops": p.get("parsed_ops"), "rule": p.get("rule"),
                         "outcome": p.get("outcome"),
                         "log_obj_orig": (pv.get("objective") or {}).get("wwt_original_bh"),
                         "v": {c: {"terminal": vr["terminal"], "stage": vr["stage_reached"],
                                   "gap": vr.get("certificate_gap"),
                                   "obj": (vr.get("certificate") or {}).get("obj_bh")}
                               for c, vr in vrow.items()}})
    check.true("A4", "E1 rows = 78000", len(rows) == 78000, len(rows))
    return rows


def load_n3(check) -> list:
    rows = []
    for src in N3_SOURCES:
        d = RESULTS / src
        props = {}
        for p in read_jsonl(d / "proposals_raw.dedup.jsonl"):
            props[(p["arm"], p["item_id"], p["mode"], p.get("thinking"), p.get("repeat"))] = p
        disp = read_jsonl(d / "dispositions.jsonl")
        check.true("A4", "{} dispositions join the proposals 1:1".format(src),
                   len(disp) == len(props), "{} vs {}".format(len(disp), len(props)))
        for r in disp:
            k = (r["arm"], r["item_id"], r["mode"], r.get("thinking"), r.get("repeat"))
            p = props.get(k)
            check.true("A4", "{} disposition {} has its proposal".format(src, k), p is not None)
            if p is None:
                continue
            rows.append({"src": src, "item_id": r["item_id"], "raw": p.get("raw_output") or "",
                         "frozen": list(p.get("frozen_seed") or []), "outcome": p.get("outcome"),
                         "gold_intent": bool((p.get("gold_intent") or {}).get("issuer_accepts_cost")),
                         "disp": r})
    check.true("A4", "N3 rows = 14560", len(rows) == 14560, len(rows))
    return rows


_OMNI: list = []


def omni_instance(ti) -> dict:
    """gen_price at t_d = 0 on every distinct E1 and N3 input of one instance; A10 boards."""
    from l1adapter import dispatch as dispatch_mod
    from l1guard.guard_v11 import read_flag, v10_view

    task = _OMNI[ti]
    t0 = time.perf_counter()
    inst = load_instance(task["path"])
    iid = inst["meta"]["id"]
    baseline = dispatch_mod.dispatch_baseline(inst, "atc", 0)
    e1 = {}
    for uk, u in task["e1_units"].items():
        res = gen_price(inst, u["raw"], u["frozen"], baseline, 0.0, unguarded=True, ref2=True)
        e1[uk] = {k: res.get(k) for k in PRICE_KEYS + ("term_ung", "tuples")}
    n3 = {}
    for uk, u in task["n3_units"].items():
        payload, flag, flag_findings, _note = read_flag(u["raw"])
        v10 = v10_view(u["raw"])
        same = raw_key(payload) == raw_key(v10)
        res = gen_price(inst, v10, u["frozen"], baseline, 0.0, ref2=True)
        rec = {k: res.get(k) for k in PRICE_KEYS}
        rec.update(flag=flag, flag_blocking=any(f.blocking for f in flag_findings),
                   payload_is_v10=same)
        if not same:
            r11 = gen_price(inst, payload, u["frozen"], baseline, 0.0, ref2=True)
            rec["v11"] = {k: r11.get(k) for k in PRICE_KEYS}
        n3[uk] = rec
    boards = {}
    site = {"t_d": 0.0, "known_ids": [wo["id"] for wo in inst["work_orders"]], "running": []}
    for fp, tuples in task["boards"].items():
        rec, _live = board_record(inst, iid, site, tuples)
        boards[fp] = {tr: {"trade_fp": tv["trade_fp"], "lb2": tv["lb2"], "atc": tv["atc"]}
                      for tr, tv in rec["trades"].items()}
    return {"iid": iid, "e1": e1, "n3": n3, "boards": boards,
            "wall_s": time.perf_counter() - t0}


def omni_check_e1(check, e1rows, res_e1):
    n_ref = 0
    for r in e1rows:
        lg = r["v"]
        if lg["G_CERT"]["terminal"] == "model_refused":
            n_ref += 1
            check.true("A4", "model_refused under every configuration: {} {}".format(
                r["src"], r["item_id"]),
                all(lg[c]["terminal"] == "model_refused" for c in lg))
            continue
        m = res_e1[r["ukey"]]
        r["m"] = m
        tag = "{}|{}|{}|{}|{}".format(r["src"], r["item_id"], r["mode"], r["thinking"],
                                      r["repeat"])
        check.true("A4", "G_CERT terminal on " + tag, m["term_cert"] == lg["G_CERT"]["terminal"],
                   "{} vs {}".format(m["term_cert"], lg["G_CERT"]["terminal"]))
        check.true("A4", "G_CERT stage on " + tag, m["stage_cert"] == lg["G_CERT"]["stage"],
                   "{} vs {}".format(m["stage_cert"], lg["G_CERT"]["stage"]))
        if lg["G_CERT"]["gap"] is not None:
            check.close("A4", "G_CERT gap on " + tag, m["gap"], lg["G_CERT"]["gap"], CHECK_TOL)
        if lg["G_CERT"]["obj"] is not None:
            check.close("A4", "G_CERT objective on " + tag, m["obj"], lg["G_CERT"]["obj"],
                        CHECK_TOL)
        if r["log_obj_orig"] is not None:
            check.close("A4", "original-field objective on " + tag, m["obj_orig"],
                        r["log_obj_orig"], CHECK_TOL)
        check.true("A4", "G_FEAS terminal on " + tag, m["term_feas"] == lg["G_FEAS"]["terminal"],
                   "{} vs {}".format(m["term_feas"], lg["G_FEAS"]["terminal"]))
        check.true("A4", "G_FEAS stage on " + tag, m["stage_feas"] == lg["G_FEAS"]["stage"],
                   "{} vs {}".format(m["stage_feas"], lg["G_FEAS"]["stage"]))
        check.true("A4", "UNGUARDED terminal on " + tag,
                   m["term_ung"] == lg["UNGUARDED"]["terminal"],
                   "{} vs {}".format(m["term_ung"], lg["UNGUARDED"]["terminal"]))
    return n_ref


def omni_check_n3(check, n3rows, res_n3):
    from l1guard.config import POLICIES_V11, TAU_HARD_SWEEP_V11
    from l1guard.guard_v11 import policy_terminal

    def tk(t):
        return "none" if t is None else "{:.2f}".format(t)

    n_ref = 0
    for r in n3rows:
        d = r["disp"]
        tag = "{}|{}|{}|{}|{}".format(r["src"], d["item_id"], d["mode"], d.get("thinking"),
                                      d.get("repeat"))
        if r["outcome"] == "refusal":
            n_ref += 1
            ok = all(d["policies"][n][tk(t)]["terminal_model_flag"] == "model_refused"
                     for n in POLICIES_V11 for t in TAU_HARD_SWEEP_V11)
            check.true("A4", "N3 model refusal kept on " + tag, ok)
            continue
        m = res_n3[r["ukey"]]
        m11 = m.get("v11") or m
        feas10 = m["term_feas"]
        feas11 = "blocked_schema" if m["flag_blocking"] else m11["term_feas"]
        gap10 = m["gap"]
        gap11 = None if m["flag_blocking"] else m11["gap"]
        rel10 = (rel_delta(m["obj"], m["ref2"]) if feas10 == "applied_uncertified"
                 and m["ref2"] is not None else None)
        rel11 = (rel_delta(m11["obj"], m11["ref2"]) if feas11 == "applied_uncertified"
                 and m11["ref2"] is not None else None)
        flag = m["flag"]
        truth_flag = True if r["gold_intent"] else None
        approver = bool(r["gold_intent"])
        check.close("A4", "N3 price_cert on " + tag, gap11, d["price_cert"], CHECK_TOL)
        check.close("A4", "N3 price_rel2 on " + tag, rel11, d["price_rel2"], CHECK_TOL)
        check.close("A4", "N3 price_cert_v12 on " + tag, gap10, d["price_cert_v12"], CHECK_TOL)
        check.close("A4", "N3 price_rel2_v12 on " + tag, rel10, d["price_rel2_v12"], CHECK_TOL)
        check.true("A4", "N3 G_FEAS_V11 terminal on " + tag, feas11 == d["feas_v11_terminal"],
                   "{} vs {}".format(feas11, d["feas_v11_terminal"]))
        for name, base in POLICIES_V11.items():
            for th in TAU_HARD_SWEEP_V11:
                pol = base.with_(tau_hard=th)
                logged = d["policies"][name][tk(th)]
                got_m = policy_terminal(pol, feas11, flag, gap11, rel11)
                got_t = policy_terminal(pol, feas11, truth_flag, gap11, rel11)
                got_v = policy_terminal(pol, feas10, approver, gap10, rel10)
                for what, got, want in (("model-flag terminal", got_m["terminal"],
                                         logged["terminal_model_flag"]),
                                        ("true-intent terminal", got_t["terminal"],
                                         logged["terminal_true_intent"]),
                                        ("v1.2 terminal", got_v["terminal"],
                                         logged["terminal_v12"])):
                    check.true("A4", "N3 {} {} tau_hard={} on {}".format(name, what, tk(th), tag),
                               got == want, "{} vs {}".format(got, want))
                check.close("A4", "N3 {} price tau_hard={} on {}".format(name, tk(th), tag),
                            got_m["price"], logged["price"], CHECK_TOL)
                check.close("A4", "N3 {} v1.2 price tau_hard={} on {}".format(name, tk(th), tag),
                            got_v["price"], logged["price_v12"], CHECK_TOL)
    return n_ref


OMNI_CHECK_FUNCS = ("cmd_omni", "dg17_repro", "n10_repro", "omni_check_e1", "omni_check_n3",
                    "tau_terminal")


def _worker_code_sha(extra) -> str:
    """Hash of every function the omni pool runs: module functions defined above the oracle
    section, the post-pool check functions excepted (they may be fixed without recomputing)."""
    import inspect

    mod = sys.modules[__name__]
    limit = inspect.getsourcelines(core_busy_s)[1]
    srcs = []
    for name, f in sorted(vars(mod).items()):
        if inspect.isfunction(f) and f.__module__ == __name__ and name not in OMNI_CHECK_FUNCS:
            if inspect.getsourcelines(f)[1] < limit:
                srcs.append(inspect.getsource(f))
    return sha_text(json.dumps([extra] + srcs))


def _inputs_wo_runner() -> dict:
    runner = str(Path(__file__).relative_to(ROOT))
    return {k: v for k, v in input_hashes().items() if k != runner}


def cmd_omni(args) -> int:
    global _OMNI
    pin_cores(args.cores_t)
    cap_threads(1)
    check = Checker()
    t_start = time.time()
    pub = OrderedDict((r["item_id"], r) for r in load_published(check))
    ext = load_ext(check)
    e1rows = load_e1(check)
    n3rows = load_n3(check)
    for r in e1rows:
        check.true("A4", "E1 row declares the ATC episode", r["rule"] == "atc", r["rule"])
    tasks = OrderedDict()

    def task_for(item):
        iid = item["instance"]["instance_id"]
        if iid not in tasks:
            tasks[iid] = {"iid": iid, "path": instance_path(item), "e1_units": {},
                          "n3_units": {}, "boards": OrderedDict([(BASE_FP, [])])}
        return tasks[iid]

    for r in e1rows:
        it = pub[r["item_id"]]
        r["instance_id"] = it["instance"]["instance_id"]
        r["primary_class"] = it["primary_class"]
        r["stratum"] = it["instance"]["stratum"]
        check.true("A4", "E1 frozen seed equals the suite's on {}".format(r["item_id"]),
                   r["frozen"] == list(it["episode"]["frozen_seed"]))
        if r["v"]["G_CERT"]["terminal"] == "model_refused":
            continue
        t = task_for(it)
        uk = sha_text(json.dumps([r["instance_id"], frozen_key(r["frozen"]), raw_key(r["raw"])]))
        r["ukey"] = uk
        t["e1_units"].setdefault(uk, {"raw": r["raw"], "frozen": r["frozen"]})
    for r in n3rows:
        iid_ = r["item_id"]
        it = ext.get(iid_) if iid_.startswith(("CA-", "CN-")) else pub.get(iid_)
        check.true("A1", "N3 item resolves to a suite record: " + iid_, it is not None)
        if it is None:
            continue
        r["instance_id"] = it["instance"]["instance_id"]
        check.true("A4", "N3 frozen seed equals the suite's on " + iid_,
                   r["frozen"] == list(it["episode"]["frozen_seed"]))
        if r["outcome"] == "refusal":
            continue
        t = task_for(it)
        uk = sha_text(json.dumps([r["instance_id"], frozen_key(r["frozen"]), raw_key(r["raw"])]))
        r["ukey"] = uk
        t["n3_units"].setdefault(uk, {"raw": r["raw"], "frozen": r["frozen"]})
    # A10 boards: every relaxed instance oracle_v1 solved, from its own census inputs.
    for orow in read_jsonl(ORACLE_V1 / "items.jsonl"):
        it = pub[orow["item_id"]]
        t = task_for(it)
        for fld in ("gold_ops", orow["canonical_field"]):
            rec = orow.get(fld) or {}
            if rec.get("fingerprint"):
                t["boards"].setdefault(rec["fingerprint"], [tuple(x) for x in rec["changed"]])
    smoke = bool(args.instances)
    if smoke:
        keep = set(args.instances.split(","))
        tasks = OrderedDict((k, v) for k, v in tasks.items() if k in keep)
    _OMNI = list(tasks.values())
    n_units = sum(len(t["e1_units"]) + len(t["n3_units"]) for t in _OMNI)
    print("[n11 omni] {} instances, {} distinct inputs, workers {} on {}".format(
        len(_OMNI), n_units, args.workers, args.cores_t), flush=True)
    order = sorted(range(len(_OMNI)), key=lambda i: (
        0 if "c10_storm" in _OMNI[i]["iid"] else 1 if "c09_storm" in _OMNI[i]["iid"] else 2,
        -(len(_OMNI[i]["e1_units"]) + len(_OMNI[i]["n3_units"]))))
    import pickle

    cache_path = (OUT / "smoke_omni" if smoke else OUT) / "omni_pool_cache.pkl"
    worker_sha = _worker_code_sha([n_units, sorted(tasks)])
    cached = None
    if cache_path.is_file():
        with open(cache_path, "rb") as fh:
            cached = pickle.load(fh)
        provenance = None
        if cached.get("inputs") != _inputs_wo_runner():
            cached = None
        elif cached.get("worker_sha") != worker_sha:
            ok, why = omni_cache_provenance(cached, [n_units, sorted(tasks)])
            print("[n11 omni] cache provenance against the Stage 1 snapshot: {} ({})".format(
                "PROVED" if ok else "NOT PROVED", why), flush=True)
            if ok:
                provenance = why
            else:
                cached = None
        if cached is not None:
            OMNI_PROVENANCE.clear()
            OMNI_PROVENANCE.update({"worker_sha_cached": cached.get("worker_sha"),
                                    "worker_sha_now": worker_sha, "provenance": provenance})
    if cached is None and os.environ.get("N11_OMNI_REQUIRE_CACHE") == "1":
        raise SystemExit("REFUSING TO RECOMPUTE: N11_OMNI_REQUIRE_CACHE=1 and the cached pool "
                         "results are not proved current")
    if cached is not None:
        print("[n11 omni] reusing the pool results of {} (same worker code and inputs)".format(
            cached["finished"]), flush=True)
        results = cached["results"]
    else:
        results = run_pool(omni_instance, len(_OMNI), args.cores_t, args.workers, order)
    res_e1, res_n3, boards = {}, {}, {}
    for res in results:
        res_e1.update(res["e1"])
        res_n3.update(res["n3"])
        for fp, trades in res["boards"].items():
            boards[(res["iid"], fp)] = trades
    # Second pass: proposal-only relaxed instances of oracle_v1 need the recomputed tuples.
    extra = OrderedDict()
    for r in e1rows:
        m = res_e1.get(r.get("ukey"))
        if m is None or m["stage_cert"] != "qual" or m["tuples"] is None:
            continue
        fp = fp_of(m["tuples"])
        if (r["instance_id"], fp) not in boards:
            extra.setdefault(r["instance_id"], OrderedDict()).setdefault(fp, m["tuples"])
    if extra:
        _OMNI = [{"iid": iid, "path": tasks[iid]["path"], "e1_units": {}, "n3_units": {},
                  "boards": fps} for iid, fps in extra.items()]
        if cached is not None:
            extra_results = cached["extra_results"]
        else:
            extra_results = run_pool(omni_instance, len(_OMNI), args.cores_t, args.workers)
        for res in extra_results:
            for fp, trades in res["boards"].items():
                boards[(res["iid"], fp)] = trades
    else:
        extra_results = []
    if cached is None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "wb") as fh:
            pickle.dump({"worker_sha": worker_sha, "inputs": _inputs_wo_runner(),
                         "finished": now_iso(), "pool_wall_s": time.time() - t_start,
                         "results": results, "extra_results": extra_results}, fh)
    wall = time.time() - t_start if cached is None else cached["pool_wall_s"]

    if smoke:
        e1rows = [r for r in e1rows if r["instance_id"] in tasks]
        n3rows = [r for r in n3rows if r.get("instance_id") in tasks]
    n_ref_e1 = omni_check_e1(check, e1rows, res_e1)
    n_ref_n3 = omni_check_n3(check, n3rows, res_n3)
    if not smoke:
        check.true("A4", "E1 model refusals = 6133", n_ref_e1 == 6133, n_ref_e1)
    # ---- A10: oracle_v1's per-trade fingerprint, LB2 and ATC objective
    by_trade = {}
    for (iid, fp), trades in boards.items():
        for tr, tv in trades.items():
            by_trade.setdefault((iid, tr, tv["trade_fp"]), []).append(tv)
    n_exact = 0
    trows = read_jsonl(ORACLE_V1 / "trade_solves.jsonl")
    if smoke:
        trows = [o for o in trows if o["instance_id"] in tasks]
    for o in trows:
        k = (o["instance_id"], o["trade"], o["trade_fp"])
        got = by_trade.get(k)
        check.true("A10", "oracle_v1 trade row {} rebuilt by the board builder".format(k),
                   got is not None)
        if not got:
            continue
        tv = got[0]
        ok_lb = all(abs(g["lb2"] - float(o["lb2_trade"])) <= CLOSE_TOL_BH for g in got)
        ok_atc = all(abs(g["atc"] - float(o["atc_trade_obj"])) <= CLOSE_TOL_BH for g in got)
        check.true("A10", "LB2 of {} equals oracle_v1".format(k), ok_lb,
                   "{} vs {}".format(tv["lb2"], o["lb2_trade"]))
        check.true("A10", "ATC of {} equals oracle_v1".format(k), ok_atc,
                   "{} vs {}".format(tv["atc"], o["atc_trade_obj"]))
        if tv["lb2"] == float(o["lb2_trade"]) and tv["atc"] == float(o["atc_trade_obj"]):
            n_exact += 1
    if not smoke:
        check.true("A10", "oracle_v1 trade rows = 2017", len(trows) == 2017, len(trows))
    # ---- A5 end to end: N2 e2e prices, the WT_ref2 cache, DG17, N10, the tau anchor
    anchors = load_anchor_records()
    erows = []
    for r in e1rows:
        m = r.get("m")
        if m is None or m["stage_cert"] != "qual":
            continue
        a = anchors[(r["instance_id"], frozen_key(r["frozen"]))]
        obj = m["obj"]
        e = {"row_id": "{}|{}|{}|{}|{}".format(r["src"], r["item_id"], r["mode"], r["thinking"],
                                               r["repeat"]),
             "src": r["src"], "item_id": r["item_id"], "mode": r["mode"],
             "arm": SRC_TO_ARM[r["src"]], "thinking": thinking_label(r["thinking"]),
             "stratum": r["stratum"], "primary_class": r["primary_class"],
             "obj": obj, "lb": m["lb"], "gap": m["gap"], "ref2": m["ref2"],
             "constraining": m["constraining"], "obj_orig": m["obj_orig"],
             "anchor": float(a["wwt_original_bh"]), "parsed_ops": r["parsed_ops"],
             "frozen": r["frozen"], "instance_id": r["instance_id"],
             "p_G-CERT": m["gap"], "p_G-CERT-M": m["gap"] - float(a["gap"]),
             "p_D-REL1": rel_delta(obj, float(a["wwt_original_bh"])),
             "p_D-REL2": None if m["ref2"] is None else rel_delta(obj, m["ref2"]),
             "p_D-ABS": round(obj - float(a["wwt_original_bh"]), ROUND_BH)}
        erows.append(e)
    n2e = {r["row_id"]: r for r in read_csv_comments(ANALYSIS / "N2_rows_e2e.csv")}
    if smoke:
        n2e = {k: v for k, v in n2e.items() if v["instance_id"] in tasks}
    check.true("A5", "e2e rows reaching the quality stage equal N2's", len(erows) == len(n2e),
               "{} vs {}".format(len(erows), len(n2e)))
    ref2_cache = {r["key"]: r for r in read_jsonl(ANALYSIS / "N2_ref2_cache.jsonl")}
    for e in erows:
        n2 = n2e.get(e["row_id"])
        check.true("A5", "N2 e2e row exists: " + e["row_id"], n2 is not None)
        if n2 is None:
            continue
        for k_mine, k_pub in (("obj", "obj"), ("lb", "lb_cert"), ("gap", "gap_cert"),
                              ("ref2", "ref2"), ("p_G-CERT", "p_G-CERT"),
                              ("p_G-CERT-M", "p_G-CERT-M"), ("p_D-REL1", "p_D-REL1"),
                              ("p_D-REL2", "p_D-REL2"), ("p_D-ABS", "p_D-ABS")):
            check.close("A5", "{} equals N2 e2e on {}".format(k_mine, e["row_id"]), e[k_mine],
                        num_or_none(n2[k_pub]), 1e-6)
        if e["constraining"]:
            c = ref2_cache.get(unit_key(e["instance_id"], e["frozen"], e["parsed_ops"] or []))
            check.true("A5", "WT_ref2 cache row exists: " + e["row_id"], c is not None)
            if c is not None:
                check.close("A5", "WT_ref2 equals N2_ref2_cache on " + e["row_id"], e["ref2"],
                            c["ref2"], CHECK_TOL)
    full_checks = not smoke or os.environ.get("N11_SMOKE_ALL") == "1"
    n_dg17 = dg17_repro(check, erows) if full_checks else None
    n_n10 = n10_repro(check, e1rows, anchors) if full_checks else None
    mism = sum(1 for r in e1rows if r.get("m") is not None
               and tau_terminal(r["m"], TAU) != r["v"]["G_CERT"]["terminal"])
    check.true("A5", "tau-sweep anchor: terminals at tau = 0.20 reproduce every E1 row",
               mism == 0, mism)
    out_dir = OUT / "smoke_omni" if smoke else OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    e1_out = []
    for r in e1rows:
        m = r.get("m")
        e1_out.append({"src": r["src"], "item_id": r["item_id"], "mode": r["mode"],
                       "thinking": r["thinking"], "repeat": r["repeat"],
                       "terminal": r["v"]["G_CERT"]["terminal"],
                       "fp": None if m is None or m["tuples"] is None else fp_of(m["tuples"])})
    write_jsonl(out_dir / "omni_e1_index.jsonl", e1_out)
    meta = {"version": VERSION, "stage": "omni", "finished": now_iso(), "wall_s": wall,
            "cores": args.cores_t, "workers": args.workers, "load_avg_end": loadavg(),
            "e1_rows": len(e1rows), "e1_model_refused": n_ref_e1, "n3_rows": len(n3rows),
            "n3_model_refused": n_ref_n3, "distinct_inputs": n_units,
            "a10_trade_rows": len(trows), "a10_bit_exact": n_exact,
            "dg17_cells_exact": n_dg17, "n10_rows": n_n10, "inputs": input_hashes(),
            "pool_results_from_cache": cached is not None,
            "cache_provenance": dict(OMNI_PROVENANCE) if cached is not None else None}
    write_json(out_dir / "omni_meta.json", meta)
    check.fatal(out_dir / "omni_assertions.json", {"inputs": meta["inputs"],
                                               "finished": meta["finished"]})
    print("[n11 omni] PASS: {} checks in {:.0f}s; {}".format(check.report()["n_checks"], wall,
                                                             json.dumps(meta)[:600]), flush=True)
    return 0


def tau_terminal(m, tau):
    t = m["term_cert"]
    if t in ("blocked_schema", "blocked_feas"):
        return t
    if m["gap"] is not None and m["stage_cert"] == "qual" and t in (
            "applied_with_certificate", "blocked_qual"):
        return "blocked_qual" if m["gap"] > tau else "applied_with_certificate"
    return t


def dg17_repro(check, erows) -> int:
    """DG17's held-out V3 separation count per (arm, thinking, rule), from the recomputed prices."""
    import n2_pricing as n2

    settings = {}
    head = {}
    for r in n2.read_csv_sections(ANALYSIS / "DG17_e2e_delta.csv"):
        if r["block"] not in ("fold", "headline"):
            continue
        if r["policy"] != "heldout_matched_loso" or r["base"] != "feas" or r["rule"] not in DG14:
            continue
        if r["block"] == "fold":
            s = float("inf") if r["setting"] == "never" else float(r["setting"])
            settings[(r["arm"], r["thinking"], r["fold"], r["rule"])] = s
        elif r["block"] == "headline":
            head[(r["arm"], r["thinking"], r["rule"])] = int(float(r["v3_separation_num"]))
    check.true("A5", "DG17 fold settings = 90", len(settings) == 90, len(settings))
    n_exact = 0
    for (arm, th, rule), want in sorted(head.items()):
        got = 0
        for e in erows:
            if e["mode"] != E2E_MODE or e["arm"] != arm or e["thinking"] != th:
                continue
            if e["primary_class"] != "V3":
                continue
            s = settings.get((arm, th, e["stratum"], rule))
            p = e["p_" + rule]
            if s is not None and p is not None and p > s:
                got += 1
        check.true("A5", "DG17 separation of ({}, {}, {}) = {}".format(arm, th, rule, want),
                   got == want, got)
        n_exact += int(got == want)
    check.true("A5", "DG17 cells reproduced = 30", n_exact == 30 and len(head) == 30,
               "{} of {}".format(n_exact, len(head)))
    return n_exact


def n10_repro(check, e1rows, anchors) -> int:
    """N10's applied field-changing rows (gap, original-field objective, damage)."""
    pub_rows = {r["row_id"]: r for r in read_csv_comments(ANALYSIS / "N10_rows.csv")}
    mine = {}
    for r in e1rows:
        m = r.get("m")
        if r["mode"] != E2E_MODE or m is None or m["stage_cert"] != "qual":
            continue
        if m["term_feas"] != "applied_uncertified" or m["gap"] is None or m["gap"] > TAU:
            continue
        if op_split(r["parsed_ops"] or []) != "field_changing":
            continue
        a = anchors[(r["instance_id"], frozen_key(r["frozen"]))]
        rid = "{}|{}|{}|{}|{}".format(r["src"], r["item_id"], r["mode"], r["thinking"],
                                      r["repeat"])
        mine[rid] = {"gap": m["gap"], "obj_orig": m["obj_orig"],
                     "damage": round(m["obj_orig"] - float(a["wwt_original_bh"]), ROUND_BH)}
    check.true("A5", "N10 applied field-changing rows reproduce",
               set(mine) == set(pub_rows), "{} mine vs {} published".format(len(mine),
                                                                            len(pub_rows)))
    for rid, p in pub_rows.items():
        m = mine.get(rid)
        if m is None:
            continue
        check.close("A5", "N10 gap on " + rid, m["gap"], float(p["gap_cert"]), 1e-6)
        check.close("A5", "N10 original-field objective on " + rid, m["obj_orig"],
                    float(p["wwt_original_bh"]), 1e-6)
        check.close("A5", "N10 damage on " + rid, m["damage"], float(p["damage_bh"]), 1e-6)
    return len(mine)


# --------------------------------------------------------------------------- #
# Oracle: CP-SAT on cores 8-11 exclusively (A11, A13; design 4)                #
# --------------------------------------------------------------------------- #
_CLK_TCK = os.sysconf("SC_CLK_TCK")
PROVED = ("OPTIMAL", "CLOSED", "CLOSED_BY_LB2", "INFEASIBLE")
SELFCHECK_V1_N = 12
SELFCHECK_N9_N = 8
SELFCHECK_AVAIL_N = 20


def core_busy_s(cores) -> float:
    want = {"cpu{}".format(c) for c in cores}
    busy = 0
    with open("/proc/stat") as fh:
        for line in fh:
            parts = line.split()
            if parts and parts[0] in want:
                v = [int(x) for x in parts[1:9]]
                busy += v[0] + v[1] + v[2] + v[5] + v[6] + v[7]
    return busy / float(_CLK_TCK)


def foreign_on_cores(cores, threshold=5.0) -> list:
    import subprocess

    out = subprocess.run(["ps", "-eo", "pid,ppid,psr,pcpu,comm"], capture_output=True,
                         text=True, check=True).stdout.splitlines()[1:]
    me = os.getpid()
    rows = []
    for line in out:
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        pid, ppid, psr, pcpu = int(parts[0]), int(parts[1]), int(parts[2]), float(parts[3])
        if pid == me or ppid == me:
            continue
        if psr in cores and pcpu >= threshold:
            rows.append({"pid": pid, "psr": psr, "pcpu": pcpu, "comm": parts[4]})
    return rows


def timed_solve(fn, cores, workers):
    b0 = core_busy_s(cores)
    la0 = loadavg()
    t0, c0 = time.perf_counter(), time.process_time()
    res = fn()
    wall = time.perf_counter() - t0
    cpu = time.process_time() - c0
    foreign = max(0.0, (core_busy_s(cores) - b0) - cpu)
    meta = {"wall_s": wall, "cpu_s": cpu,
            "cpu_share": cpu / (wall * workers) if wall > 0 else None,
            "foreign_cpu_s": foreign,
            "foreign_share": foreign / (wall * len(cores)) if wall > 0 else None,
            "affinity": sorted(os.sched_getaffinity(0)), "load_avg_start": la0,
            "load_avg_end": loadavg(), "workers": workers,
            "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
            "mkl_num_threads": os.environ.get("MKL_NUM_THREADS")}
    if res.get("solve_wall_s"):
        meta["solve_cpu_share"] = res["solve_cpu_s"] / (res["solve_wall_s"] * workers)
    else:
        meta["solve_cpu_share"] = None
    return res, meta


def validity(row) -> None:
    """foreign_share > 0.10 invalidates a budget-limited row (design decision 4)."""
    if row["status"] in PROVED:
        row["invalid"] = False
    else:
        fs = row.get("foreign_share")
        row["invalid"] = bool(fs is not None and fs > FOREIGN_SHARE_MAX)
    scs = row.get("solve_cpu_share")
    row["low_cpu_share"] = bool(scs is not None and scs < 0.9)


def closed_row(**kw) -> OrderedDict:
    row = OrderedDict(kw)
    row.update(wall_s=0.0, solve_wall_s=0.0, cpu_s=0.0, cpu_share=None, solve_cpu_share=None,
               foreign_cpu_s=None, foreign_share=None, affinity=sorted(os.sched_getaffinity(0)),
               load_avg_start=loadavg(), load_avg_end=loadavg(),
               omp_num_threads=os.environ.get("OMP_NUM_THREADS"))
    validity(row)
    return row


def load_rows_last(path, keyf):
    rows, drops = {}, Counter()
    for r in read_jsonl(path):
        k = keyf(r)
        if r.get("invalid") and not r.get("invalid_persistent"):
            drops[k] += 1
            rows.pop(k, None)
            continue
        rows[k] = r
    return rows, drops


def relaxed_key(r):
    return (r["iid"], float(r["t_d"]), r["trade"], r["trade_fp"])


def solve_relaxed(ti, args, cores) -> OrderedDict:
    from l1adapter import evaluate as evaluate_mod
    from l1oracle import cpsat_avail as ca

    sub, ta = ti["sub"], ti["tech_available"]
    ex = ti.get("exec_upper")
    res, meta = timed_solve(lambda: ca.solve(sub, ca.Constraints(), time_limit_s=args.budget,
                                             workers=args.workers, warm_start={"assignments": ti["warm"]},
                                             tech_available=ta), cores, args.workers)
    inc = res["incumbent_obj_bh"]
    if res["schedule"] is not None:
        val = evaluate_mod.validate(sub, res["schedule"])
        bad = ca.check_availability(res["schedule"], ta)
        if not val["feasible"] or bad:
            raise SystemExit("A9 FAILURE: re-timed relaxed incumbent infeasible on {}: {} {}".format(
                relaxed_key(ti), val["violations"][:3], bad[:3]))
    bound = res["bound_bh"] if res["bound_bh"] is not None else 0.0
    if bound == float("inf"):
        raise SystemExit("A9 FAILURE: relaxed board infeasible on {}".format(relaxed_key(ti)))
    lower = max(float(ti["lb2"]), bound)
    ups = [(float(ti["atc"]), "atc")]
    if ex is not None:
        ups.append((float(ex), "executed"))
    if inc is not None:
        ups.append((inc, "cpsat"))
    upper, src = min(ups)
    if lower > upper + CHECK_TOL:
        raise SystemExit("A9 FAILURE: BRACKET VIOLATION relaxed {} lower {} upper {}".format(
            relaxed_key(ti), lower, upper))
    row = OrderedDict(kind="relaxed", iid=ti["iid"], t_d=float(ti["t_d"]), trade=ti["trade"],
                      trade_fp=ti["trade_fp"], n_orders=ti["n_orders"], n_techs=ti["n_techs"],
                      n_busy_techs=sum(1 for v in ta.values() if v > float(ti["t_d"]) + 1e-12),
                      lb2=float(ti["lb2"]), atc=float(ti["atc"]), exec_upper=ex,
                      status=res["status"], bound=res["bound_bh"], incumbent=inc,
                      grid_obj=res["grid_obj_bh"], lower=lower, upper=upper, upper_source=src,
                      retime_failed=res["retime_failed"], build_s=res["build_s"],
                      solve_wall_s=res["solve_wall_s"], solve_cpu_s=res["solve_cpu_s"],
                      n_symmetry_groups=res["n_symmetry_groups"],
                      n_avail_intervals=res["n_avail_intervals"], horizon_centi=res["horizon_centi"],
                      budget_s=args.budget, version=VERSION, **meta)
    validity(row)
    return row


def solve_component(c, L_k, U_k, args, cores) -> OrderedDict:
    from l1adapter import evaluate as evaluate_mod
    from l1oracle import cpsat_avail as ca

    head = OrderedDict(kind="constrained", key=c["key"], iid=c["iid"], t_d=c["t_d"],
                       trades=c["trades"], n_orders=c["n_orders"], n_edges=c["n_edges"],
                       n_pins=c["n_pins"], n_batches=c["n_batches"], n_frozen=c["n_frozen"],
                       relaxed_lower=L_k, relaxed_upper=U_k, atc_obj=c["atc_obj"],
                       atc_valid=c["atc_valid"], budget_s=args.budget, version=VERSION)
    if c["atc_valid"] and c["atc_obj"] <= L_k + CLOSE_TOL_BH:
        return closed_row(**head, status="CLOSED", bound=None, incumbent=None, grid_obj=None,
                          lower=L_k, upper=c["atc_obj"], upper_source="atc", workers=args.workers)
    sub, ta = c["sub"], c["tech_available"]
    cons = cons_from_dict(c["cons"])
    res, meta = timed_solve(lambda: ca.solve(sub, cons, time_limit_s=args.budget,
                                             workers=args.workers, warm_start=c["warm"],
                                             tech_available=ta), cores, args.workers)
    inc = res["incumbent_obj_bh"]
    if res["schedule"] is not None:
        val = evaluate_mod.validate(sub, res["schedule"])
        bad = ca.check_constraints(sub, res["schedule"], cons) + \
            ca.check_availability(res["schedule"], ta)
        if not val["feasible"] or bad:
            raise SystemExit("A9 FAILURE: re-timed constrained incumbent infeasible on {}: {} {}"
                             .format(c["key"][:12], val["violations"][:3], bad[:3]))
    bound = res["bound_bh"]
    if bound == float("inf"):
        raise SystemExit("A9 FAILURE: constrained board infeasible on {} ({})".format(
            c["key"][:12], c["trades"]))
    lower = max(bound or 0.0, L_k)
    ups = []
    if c["atc_valid"]:
        ups.append((c["atc_obj"], "atc"))
    if inc is not None:
        ups.append((inc, "cpsat"))
    if not ups:
        row = OrderedDict(head)
        row.update(status=res["status"], bound=bound, incumbent=None, grid_obj=None, lower=lower,
                   upper=None, upper_source=None, solve_wall_s=res["solve_wall_s"],
                   solve_cpu_s=res["solve_cpu_s"], **meta)
        validity(row)
        row["invalid"] = row["invalid"] or False
        return row
    upper, src = min(ups)
    if lower > upper + CHECK_TOL:
        raise SystemExit("A9 FAILURE: BRACKET VIOLATION constrained {} lower {} upper {}".format(
            c["key"][:12], lower, upper))
    row = OrderedDict(head)
    row.update(status=res["status"], bound=bound, incumbent=inc, grid_obj=res["grid_obj_bh"],
               lower=lower, upper=upper, upper_source=src, retime_failed=res["retime_failed"],
               build_s=res["build_s"], solve_wall_s=res["solve_wall_s"],
               solve_cpu_s=res["solve_cpu_s"], n_symmetry_groups=res["n_symmetry_groups"],
               n_avail_intervals=res["n_avail_intervals"], horizon_centi=res["horizon_centi"],
               **meta)
    validity(row)
    return row


def oracle_gate(check_paths) -> dict:
    """Refuse unless the census and omni assertion files say PASS for the data on disk."""
    out = {}
    cur = input_hashes()
    runner = str(Path(__file__).relative_to(ROOT))
    for name, path in check_paths.items():
        if not path.is_file():
            raise SystemExit("REFUSING TO RUN: {} is missing".format(path))
        rep = json.loads(path.read_text())
        if rep.get("status") != "PASS":
            raise SystemExit("REFUSING TO RUN: {} says {}".format(path.name, rep.get("status")))
        drift = [k for k, v in (rep.get("inputs") or {}).items() if k != runner and cur.get(k) != v]
        if drift:
            raise SystemExit("REFUSING TO RUN: inputs changed since {}: {}".format(name, drift))
        for fname, digest in (rep.get("outputs") or {}).items():
            got = sha256_file(path.parent / fname)
            if got != digest:
                raise SystemExit("REFUSING TO RUN: {} changed since the census".format(fname))
        out[name] = {"status": rep["status"], "n_checks": rep["n_checks"],
                     "finished": rep.get("finished"),
                     "runner_sha256_at_stage": (rep.get("inputs") or {}).get(runner)}
    return out


def selfcheck(args, cores, log) -> dict:
    """A11: the model without availability is the oracle's and N9's; with it, Y1's."""
    from l1adapter import dispatch as dispatch_mod
    from l1guard import tier1
    from l1oracle import cpsat_avail as ca
    import n8_causal as n8
    import suite_gate as sg

    fails, rows = [], []
    pub = [json.loads(ln) for ln in open(sg.SUITE_PATH, encoding="utf-8")]
    item_of = {}
    for it in pub:
        item_of.setdefault(it["instance"]["instance_id"], it)
    insts = {}

    def inst_of(iid):
        if iid not in insts:
            inst = load_instance(instance_path(item_of[iid]))
            insts[iid] = (inst, dispatch_mod.dispatch_baseline(inst, "atc", 0))
        return insts[iid]

    # (a) oracle_v1 proved grid optima, baseline fields, no availability.
    v1 = [r for r in read_jsonl(ORACLE_V1 / "trade_solves.jsonl")
          if r["status"] == "OPTIMAL" and r["trade_fp"] == BASE_FP and 40 <= r["n_orders"] <= 400]
    v1.sort(key=lambda r: (r["instance_id"], r["trade"]))
    step = max(1, len(v1) // SELFCHECK_V1_N)
    for o in v1[::step][:SELFCHECK_V1_N]:
        inst, base = inst_of(o["instance_id"])
        sub = ca.sub_instance(inst, (o["trade"],))
        ids = {wo["id"] for wo in sub["work_orders"]}
        warm = ca.restrict_schedule(base, ids)
        res, meta = timed_solve(lambda: ca.solve(sub, ca.Constraints(), time_limit_s=args.budget,
                                                 workers=args.workers, warm_start=warm),
                                cores, args.workers)
        rec = {"check": "oracle_v1_grid_optimum", "instance_id": o["instance_id"],
               "trade": o["trade"], "n_orders": len(ids), "status": res["status"],
               "bound": res["bound_bh"], "oracle_cp_bound": o["cp_bound"], **meta}
        if res["status"] == "OPTIMAL":
            rec["dev"] = abs(res["bound_bh"] - float(o["cp_bound"]))
            if rec["dev"] > CHECK_TOL:
                fails.append(("oracle_v1 grid optimum differs", o["instance_id"], o["trade"],
                              rec["dev"]))
        rows.append(rec)
        log(rec)
    # (b) N9 proved constrained bounds, no availability.
    os.environ["L1_N9_WORKERS"] = "1"
    import n9_instruction_cost as n9
    cap_threads(1)
    n9_rows = [r for r in read_jsonl(N9_DIR / "solves.jsonl")
               if r.get("kind") == "constrained" and r["status"] == "OPTIMAL"
               and r["n_orders"] <= 400]
    n9_rows.sort(key=lambda r: r["key"])
    by_key = {}
    for b in read_jsonl(N9_DIR / "brackets.jsonl"):
        for comp in b.get("components", []):
            by_key.setdefault(comp["key"], b["item_id"])
    held = {r["item_id"]: r for r in read_jsonl(HELDOUT_PATH)}
    pubd = {r["item_id"]: r for r in pub}
    store = n9.Instances()
    step = max(1, len(n9_rows) // SELFCHECK_N9_N)
    for o in n9_rows[::step][:SELFCHECK_N9_N]:
        item = pubd.get(by_key.get(o["key"])) or held.get(by_key.get(o["key"]))
        if item is None:
            fails.append(("N9 row without its item", o["key"][:12]))
            continue
        unit = n9.prepare(item, store)
        comp = next((c for c in unit["comps"] if c["key"] == o["key"]), None)
        if comp is None:
            fails.append(("N9 component not rebuilt", o["key"][:12]))
            continue
        sub = ca.sub_instance(unit["adj"].instance, comp["trades"])
        res, meta = timed_solve(lambda: ca.solve(sub, comp["_cons"], time_limit_s=args.budget,
                                                 workers=args.workers, warm_start=comp["_sched"]),
                                cores, args.workers)
        rec = {"check": "n9_constrained_bound", "key": o["key"], "item_id": item["item_id"],
               "n_orders": comp["n_orders"], "status": res["status"], "bound": res["bound_bh"],
               "n9_bound": o["bound"], **meta}
        if res["status"] == "OPTIMAL":
            rec["dev"] = abs(res["bound_bh"] - float(o["bound"]))
            if rec["dev"] > CHECK_TOL:
                fails.append(("N9 constrained bound differs", o["key"][:12], rec["dev"]))
        rows.append(rec)
        log(rec)
    # (c) availability: Y1 cpsat.solve(tech_available) on grid-aligned small trades.
    y1 = tier1._cpsat()
    cap_threads(1)
    boards = read_jsonl(OUT / "boards.jsonl")
    sites = sorted({(b["iid"], b["t_d"]) for b in boards if b["n_running"] > 0})
    picked = 0
    for iid, t_d in sites:
        if picked >= SELFCHECK_AVAIL_N:
            break
        if iid not in item_of:
            continue
        inst, base = inst_of(iid)
        state = n8.site_state(inst, base, t_d, pm_known=True)
        site = site_of(state, base, t_d)
        avail = availability(inst, site)
        binst = board_instance(inst, site, [])
        for tr in sorted({wo["trade"] for wo in binst["work_orders"]}):
            sub = ca.sub_instance(binst, (tr,))
            n = len(sub["work_orders"])
            busy = [t["id"] for t in sub["technicians"] if avail[t["id"]] > t_d + 1e-9]
            if not (4 <= n <= 30) or not busy:
                continue
            g = []
            for wo in sub["work_orders"]:
                w = dict(wo)
                w["p_bh"] = ca.centi_floor(wo["p_bh"]) / 100.0
                w["release_bh"] = ca.centi_floor(wo["release_bh"]) / 100.0
                w["due_bh"] = ca.centi_ceil(wo["due_bh"]) / 100.0
                g.append(w)
            gsub = dict(sub)
            gsub["work_orders"] = g
            ta = {t["id"]: ca.centi_floor(avail[t["id"]]) / 100.0 for t in sub["technicians"]}
            mine, meta = timed_solve(lambda: ca.solve(gsub, ca.Constraints(), time_limit_s=30.0,
                                                      workers=args.workers, tech_available=ta),
                                     cores, args.workers)
            theirs = y1.solve(gsub, time_limit_s=30.0, workers=args.workers, tech_available=ta)
            rec = {"check": "y1_availability", "instance_id": iid, "t_d": t_d, "trade": tr,
                   "n_orders": n, "n_busy": len(busy), "status": mine["status"],
                   "grid_obj": mine["grid_obj_bh"], "bound": mine["bound_bh"],
                   "y1_status": theirs.get("status"), "y1_objective": theirs.get("objective_bh"),
                   "y1_bound": theirs.get("best_bound_bh"), **meta}
            if mine["status"] == "OPTIMAL" and theirs.get("status") == "OPTIMAL":
                rec["dev"] = abs(mine["grid_obj_bh"] - float(theirs["objective_bh"]))
                if rec["dev"] > CHECK_TOL:
                    fails.append(("availability optimum differs from Y1", iid, t_d, tr,
                                  rec["dev"]))
                picked += 1
            rows.append(rec)
            log(rec)
            break
    n_cmp = {k: sum(1 for r in rows if r["check"] == k and "dev" in r)
             for k in ("oracle_v1_grid_optimum", "n9_constrained_bound", "y1_availability")}
    if n_cmp["oracle_v1_grid_optimum"] < 10 or n_cmp["n9_constrained_bound"] < 5 \
            or n_cmp["y1_availability"] < SELFCHECK_AVAIL_N:
        fails.append(("too few proved pairs compared", n_cmp))
    return {"rows": rows, "fails": fails, "compared": n_cmp,
            "max_dev": max((r.get("dev", 0.0) for r in rows), default=0.0)}


def assemble_boards(boards, rel_rows) -> tuple:
    """Per board: the bracket on K's relaxed optimum; per trade key: its bracket."""
    trade_br = {}
    out = []
    for b in boards:
        lo = up = 0.0
        complete, proved = True, True
        statuses = Counter()
        for tr, tv in b["trades"].items():
            k = (b["iid"], float(b["t_d"]), tr, tv["trade_fp"])
            if tv["closed_by_lb2"]:
                tl, tu, st = tv["lb2"], tv["upper0"], "CLOSED_BY_LB2"
            else:
                r = rel_rows.get(k)
                if r is None:
                    complete = False
                    statuses["MISSING"] += 1
                    continue
                # Any executed or dispatched schedule of the board is an upper end
                # too, so the bracket keeps the lower of the two (Stage 2).
                tl, tu, st = float(r["lower"]), min(float(r["upper"]), tv["upper0"]), r["status"]
            trade_br[k] = (tl, tu, st)
            statuses[st] += 1
            lo += tl
            up += tu
            proved = proved and (st in ("OPTIMAL", "CLOSED_BY_LB2") or tu - tl <= CLOSE_TOL_BH)
        c = b["running_const"]
        rec = OrderedDict(iid=b["iid"], t_d=b["t_d"], fp=b["fp"], n_orders=b["n_orders"],
                          n_running=b["n_running"], running_const=c, complete=complete,
                          lower=(lo + c) if complete else None, upper=(up + c) if complete else None,
                          lower_relaxed=lo if complete else None,
                          upper_relaxed=up if complete else None, proved_all=complete and proved,
                          statuses=dict(statuses))
        if complete:
            rec["width_rel"] = (rec["upper"] - rec["lower"]) / max(rec["lower"], FLOOR_BH)
            if rec["lower"] > rec["upper"] + CHECK_TOL:
                raise SystemExit("A9 FAILURE: board bracket inverted on {} {} {}".format(
                    b["iid"], b["t_d"], b["fp"][:10]))
        out.append(rec)
    return out, trade_br


def assemble_c(items, brackets, trade_br, comps, c_rows) -> list:
    bk = {(b["iid"], float(b["t_d"]), b["fp"]): b for b in brackets}
    out = []
    for r in items:
        if not r.get("c_needed"):
            continue
        rec = OrderedDict(item_id=r["item_id"], set=r["set"], role=r["c_role"],
                          primary_class=r["primary_class"], stratum=r["stratum"],
                          instance_id=r["instance_id"], t_d=r["t_d"], issuable=r["issuable"],
                          c_error=r.get("c_error"), complete=False)
        if r.get("c_error") or r.get("c_keys") is None:
            out.append(rec)
            continue
        b = bk.get((r["instance_id"], float(r["t_d"]), r["dt_fp"]))
        if b is None or not b["complete"]:
            out.append(rec)
            continue
        L, U = b["lower"], b["upper"]
        n_lo = n_hi = 0.0
        complete = True
        statuses = []
        for key in r["c_keys"]:
            c = comps[key]
            row = c_rows.get(key)
            tb = [trade_br.get((c["iid"], float(c["t_d"]), tr, c["trade_fps"][tr]))
                  for tr in c["trades"]]
            if row is None or any(x is None for x in tb) or row.get("upper") is None:
                complete = False
                continue
            L_k = sum(x[0] for x in tb)
            U_k = sum(x[1] for x in tb)
            lc, uc = max(float(row["lower"]), L_k), float(row["upper"])
            n_lo += max(0.0, lc - U_k)
            n_hi += uc - L_k
            statuses.append(row["status"])
        rec.update(complete=complete, opt_lower=L, opt_upper=U, n_components=len(r["c_keys"]),
                   statuses=statuses)
        if complete:
            rec.update(n_lo=n_lo, n_hi=n_hi, c_lo=n_lo / max(U, FLOOR_BH),
                       c_hi=n_hi / max(L, FLOOR_BH))
            rec["c_mid"] = 0.5 * (rec["c_lo"] + rec["c_hi"])
            if rec["c_lo"] > rec["c_hi"] + 1e-12:
                raise SystemExit("A9 FAILURE: c bracket inverted on {}".format(r["item_id"]))
        out.append(rec)
    return out


def cmd_oracle(args) -> int:
    pin_cores(args.cores_t)
    os.environ["OMP_NUM_THREADS"] = os.environ.get("OMP_NUM_THREADS", "1")
    if os.environ.get("OMP_NUM_THREADS") != "1" or os.environ.get("MKL_NUM_THREADS") != "1":
        raise SystemExit("REFUSING TO RUN: launch with OMP_NUM_THREADS=1 MKL_NUM_THREADS=1")
    cores = list(args.cores_t)
    extra_dirs = [Path(x) for x in (getattr(args, "extra_inputs", "") or "").split(",") if x]
    gate_paths = {"census": OUT / "census_assertions.json", "omni": OUT / "omni_assertions.json"}
    for d in extra_dirs:
        names = [n for n in ("census_assertions.json", "e2e_assertions.json")
                 if (d / n).is_file()]
        if not names:
            raise SystemExit("REFUSING TO RUN: {} carries no assertion file".format(d))
        gate_paths[str(d.relative_to(ROOT))] = d / names[0]
    gate = oracle_gate(gate_paths)
    foreign = foreign_on_cores(set(cores))
    if foreign:
        raise SystemExit("REFUSING TO RUN: foreign processes on cores 8-11: {}".format(foreign))
    ORACLE_OUT.mkdir(parents=True, exist_ok=True)
    log_path = ORACLE_OUT / "selfcheck.jsonl"
    import ortools

    meta = OrderedDict(
        version=VERSION, started=now_iso(), host=socket.gethostname(),
        python=sys.version.split()[0], platform=platform.platform(), ortools=ortools.__version__,
        cores=cores, workers=args.workers, budget_s=args.budget, phase=args.phase,
        omp_num_threads=os.environ.get("OMP_NUM_THREADS"),
        mkl_num_threads=os.environ.get("MKL_NUM_THREADS"),
        foreign_share_max=FOREIGN_SHARE_MAX, max_resolves=MAX_RESOLVES,
        affinity=sorted(os.sched_getaffinity(0)), load_avg_start=loadavg(),
        foreign_processes_at_start=foreign, gate=gate, inputs=input_hashes(),
        census_outputs={p.name: sha256_file(p) for p in sorted(OUT.glob("*.jsonl"))
                        if p.name in ("items.jsonl", "boards.jsonl", "relaxed_inputs.jsonl",
                                      "c_components.jsonl")})
    write_json(ORACLE_OUT / "run_meta.json", meta)
    append_jsonl(ORACLE_OUT / "run_meta_history.jsonl", meta)
    t_run = time.perf_counter()
    walls = OrderedDict()

    if args.phase in ("all", "selfcheck"):
        t0 = time.perf_counter()
        sc = selfcheck(args, cores, lambda rec: append_jsonl(log_path, rec))
        walls["selfcheck_s"] = time.perf_counter() - t0
        summ = {k: v for k, v in sc.items() if k != "rows"}
        write_json(ORACLE_OUT / "selfcheck_summary.json", summ)
        print("[n11 oracle] A11 self-check: {}".format(json.dumps(summ)[:800]), flush=True)
        if sc["fails"]:
            meta["a11"] = "FAIL"
            write_json(ORACLE_OUT / "run_meta.json", meta)
            raise SystemExit("A11 FAILURE: {}".format(sc["fails"][:5]))
        meta["a11"] = "PASS"

    items = read_jsonl(OUT / "items.jsonl")
    boards = read_jsonl(OUT / "boards.jsonl")
    rel_in = read_jsonl(OUT / "relaxed_inputs.jsonl")
    seen_k = {relaxed_key(r) for r in rel_in}
    for d in extra_dirs:
        for r in read_jsonl(d / "relaxed_inputs.jsonl"):
            if relaxed_key(r) not in seen_k:
                seen_k.add(relaxed_key(r))
                rel_in.append(r)
    comps = {c["key"]: c for c in read_jsonl(OUT / "c_components.jsonl")}
    rel_path = ORACLE_OUT / "trade_solves.jsonl"
    c_path = ORACLE_OUT / "c_solves.jsonl"
    resolved = []

    if args.phase in ("all", "relaxed"):
        t0 = time.perf_counter()
        rel_rows, drops = load_rows_last(rel_path, relaxed_key)
        todo = sorted(rel_in, key=lambda r: (r["n_orders"], r["iid"], r["t_d"], r["trade"]))
        n = 0
        for ti in todo:
            k = relaxed_key(ti)
            while k not in rel_rows:
                row = solve_relaxed(ti, args, cores)
                if row["invalid"]:
                    resolved.append({"kind": "relaxed", "key": list(k), "foreign_share":
                                     row["foreign_share"], "attempt": drops[k] + 1})
                    if drops[k] >= MAX_RESOLVES:
                        row["invalid_persistent"] = True
                append_jsonl(rel_path, row)
                if row["invalid"] and not row.get("invalid_persistent"):
                    drops[k] += 1
                    print("[n11 oracle] INVALID (foreign_share {:.3f}) {}; solving again".format(
                        row["foreign_share"], k), flush=True)
                    continue
                rel_rows[k] = row
                n += 1
                print("[n11 oracle] relaxed {}/{} {} t_d={:.2f} {} n={} status={} [{:.3f}, {:.3f}] "
                      "wall={:.1f}s solve_cpu_share={} foreign={}".format(
                          n, len(todo), ti["iid"], ti["t_d"], ti["trade"], ti["n_orders"],
                          row["status"], row["lower"], row["upper"], row["wall_s"],
                          None if row["solve_cpu_share"] is None else round(row["solve_cpu_share"], 3),
                          None if row["foreign_share"] is None else round(row["foreign_share"], 3)),
                      flush=True)
            if args.limit and n >= args.limit:
                break
        walls["relaxed_s"] = time.perf_counter() - t0
    rel_rows, _ = load_rows_last(rel_path, relaxed_key)
    brackets, trade_br = assemble_boards(boards, rel_rows)
    write_jsonl(ORACLE_OUT / "brackets.jsonl", brackets)
    for d in extra_dirs:
        b_x, _t = assemble_boards(read_jsonl(d / "boards.jsonl"), rel_rows)
        write_jsonl(d / "brackets.jsonl", b_x)
        meta.setdefault("extra_brackets", {})[str(d.relative_to(ROOT))] = {
            "boards": len(b_x), "complete": sum(1 for b in b_x if b["complete"])}

    if args.phase in ("all", "c"):
        t0 = time.perf_counter()
        c_rows, drops = load_rows_last(c_path, lambda r: r["key"])
        need = []
        for r in items:
            for key in r.get("c_keys") or []:
                if key not in need:
                    need.append(key)
        todo = sorted(need, key=lambda k: (comps[k]["n_orders"], k))
        n = 0
        for key in todo:
            c = comps[key]
            tb = [trade_br.get((c["iid"], float(c["t_d"]), tr, c["trade_fps"][tr]))
                  for tr in c["trades"]]
            if any(x is None for x in tb):
                print("[n11 oracle] component {} lacks a relaxed bracket; skipped".format(key[:12]),
                      flush=True)
                continue
            L_k, U_k = sum(x[0] for x in tb), sum(x[1] for x in tb)
            while key not in c_rows:
                row = solve_component(c, L_k, U_k, args, cores)
                if row["invalid"]:
                    resolved.append({"kind": "constrained", "key": key,
                                     "foreign_share": row["foreign_share"],
                                     "attempt": drops[key] + 1})
                    if drops[key] >= MAX_RESOLVES:
                        row["invalid_persistent"] = True
                append_jsonl(c_path, row)
                if row["invalid"] and not row.get("invalid_persistent"):
                    drops[key] += 1
                    print("[n11 oracle] INVALID (foreign_share {:.3f}) {}; solving again".format(
                        row["foreign_share"], key[:12]), flush=True)
                    continue
                c_rows[key] = row
                n += 1
                print("[n11 oracle] c {}/{} {} t_d={:.2f} {} n={} edges={} status={} "
                      "[{}, {}] wall={:.1f}s solve_cpu_share={} foreign={}".format(
                          n, len(todo), c["iid"], c["t_d"], "+".join(c["trades"]), c["n_orders"],
                          c["n_edges"], row["status"], row["lower"], row["upper"],
                          row["wall_s"],
                          None if row["solve_cpu_share"] is None else round(row["solve_cpu_share"], 3),
                          None if row["foreign_share"] is None else round(row["foreign_share"], 3)),
                      flush=True)
            if args.limit and n >= args.limit:
                break
        walls["c_s"] = time.perf_counter() - t0
    c_rows, _ = load_rows_last(c_path, lambda r: r["key"])
    cb = assemble_c(items, brackets, trade_br, comps, c_rows)
    write_jsonl(ORACLE_OUT / "c_brackets.jsonl", cb)
    for rr in resolved:
        append_jsonl(ORACLE_OUT / "resolved.jsonl", rr)
    meta.update(finished=now_iso(), wall_s=time.perf_counter() - t_run, walls=walls,
                load_avg_end=loadavg(), n_resolved=len(resolved),
                boards=len(brackets), boards_complete=sum(1 for b in brackets if b["complete"]),
                c_items=len(cb), c_complete=sum(1 for b in cb if b["complete"]))
    write_json(ORACLE_OUT / "run_meta.json", meta)
    append_jsonl(ORACLE_OUT / "run_meta_history.jsonl", meta)
    print("[n11 oracle] finished: {}".format(json.dumps({k: meta[k] for k in (
        "wall_s", "walls", "n_resolved", "boards", "boards_complete", "c_items",
        "c_complete")})), flush=True)
    return 0


# --------------------------------------------------------------------------- #
# Stage 2: reuse of the omniscient pool results across a census-only change    #
# --------------------------------------------------------------------------- #
#: The Stage 1 runner as it computed ``omni_pool_cache.pkl`` (results/
#: n11_decision_time/stage1_snapshot/SHA256SUMS).
STAGE1_SNAPSHOT = OUT / "stage1_snapshot" / "n11_decision_time_stage1.py"
STAGE1_RUNNER_SHA = "0f287ae49ef7c976"
#: The functions Stage 2 changed or added above the oracle section.  None of
#: them is reachable from the omniscient pool worker (asserted below).
CENSUS_ONLY = ("census_instance", "cmd_census", "run_checks_census", "kf_fix", "_kf_n8",
               "decision_instant_of")
OMNI_PROVENANCE: dict = {}


def _pool_functions(mod) -> dict:
    import inspect

    limit = inspect.getsourcelines(mod.core_busy_s)[1]
    out = {}
    for name, f in vars(mod).items():
        if inspect.isfunction(f) and f.__module__ == mod.__name__ \
                and name not in mod.OMNI_CHECK_FUNCS and inspect.getsourcelines(f)[1] < limit:
            out[name] = inspect.getsource(f)
    return out


IMPORT_TIME_NAMES = ("_env_root", "_p")


def omni_cache_provenance(cached, extra):
    """Prove that the cached omniscient pool results are what the current code computes.

    The worker hash covers every function above the oracle section, so the
    Stage 2 census edits change it although the pool never runs them.  The
    proof: (1) the Stage 1 snapshot of the runner has the recorded SHA-256
    prefix and reproduces the cached worker hash exactly; (2) every function
    whose source differs between the snapshot and the current module, or that
    exists in one only, is in ``CENSUS_ONLY``; (3) no other function's source
    names a ``CENSUS_ONLY`` function; (4) every plain module constant shared by
    the two has the same value.  Then the pool computes the same results.
    """
    import importlib.util
    import re

    if not STAGE1_SNAPSHOT.is_file():
        return False, "no Stage 1 snapshot"
    sha = sha256_file(STAGE1_SNAPSHOT)
    if not sha.startswith(STAGE1_RUNNER_SHA):
        return False, "snapshot sha {} does not start {}".format(sha[:16], STAGE1_RUNNER_SHA)
    spec = importlib.util.spec_from_file_location("n11_stage1_snapshot", STAGE1_SNAPSHOT)
    snap = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = snap
    spec.loader.exec_module(snap)
    if snap._worker_code_sha(extra) != cached.get("worker_sha"):
        return False, "the snapshot does not reproduce the cached worker hash"
    a, b = _pool_functions(snap), _pool_functions(sys.modules[__name__])
    diff = sorted(n for n in set(a) | set(b) if a.get(n) != b.get(n))
    if not set(diff) <= set(CENSUS_ONLY):
        return False, "pool-reachable functions changed: {}".format(
            sorted(set(diff) - set(CENSUS_ONLY)))
    pat = re.compile(r"\b(" + "|".join(CENSUS_ONLY) + r")\b")
    leaks = sorted(n for n, src in b.items() if n not in CENSUS_ONLY and pat.search(src))
    if leaks:
        return False, "functions naming census-only code: {}".format(leaks)
    plain = (str, int, float, bool, tuple, frozenset, type(None))
    const_diff = []
    # Two import-time names are not computation constants: ``_env_root`` is the
    # environment read at import (the snapshot is imported after this module set
    # L1_INSTANCE_ROOT; both modules refuse any root other than SNAPSHOT_ROOT),
    # and ``_p`` is the sys.path loop variable (the snapshot sits in its own folder).
    for name in IMPORT_TIME_NAMES:
        v = vars(snap).get(name)
        if name == "_env_root" and v is not None and \
                os.path.realpath(v) != os.path.realpath(SNAPSHOT_ROOT):
            return False, "snapshot imported under another instance root: {}".format(v)
    for name, v in vars(snap).items():
        if name.startswith("__") or name not in vars(sys.modules[__name__]):
            continue
        if name in IMPORT_TIME_NAMES:
            continue
        w = vars(sys.modules[__name__])[name]
        if isinstance(v, plain) or (isinstance(v, dict) and all(
                isinstance(x, plain) for x in list(v.keys()) + list(v.values()))):
            if v != w:
                const_diff.append(name)
    if const_diff:
        return False, "module constants differ: {}".format(const_diff)
    return True, {"snapshot_sha256": sha, "changed_functions": diff,
                  "worker_sha_snapshot": cached.get("worker_sha")}


# --------------------------------------------------------------------------- #
# Analyse: rows, twins of the published exhibits, macros, summary              #
# --------------------------------------------------------------------------- #
POINT_WIDTH_REL = 1e-3
CLASS_TOKEN = OrderedDict([("benign", "Benign"), ("V1", "VOne"), ("V2", "VTwo"), ("V3", "VThree"),
                           ("V4", "VFour"), ("V5", "VFive"), ("V6", "VSix")])
STRATUM_TOKEN = OrderedDict([("c09_storm2_w80", "CNineStorm"), ("c10_storm2_w80", "CTenStorm"),
                             ("c10_replay_400", "CTenReplay")])
GATE_TOKEN = {"G-CERT": "Cert", "G-CERT-M": "CertM", "D-REL1": "RelOne", "D-REL2": "RelTwo",
              "D-ABS": "Abs"}
SPLIT_TOKEN = {"all": "All", "empty": "Empty", "sequencing_only": "Seq",
               "field_changing": "Field"}
PUBLISHED_MACRO_FILES = ("manuscript/macros.tex", "analysis/N2_macros.tex",
                         "analysis/N9_macros.tex", "analysis/N10_macros.tex",
                         "analysis/N8_macros.tex")


def load_macros(paths) -> dict:
    import re

    out = {}
    pat = re.compile(r"\\newcommand\{\\([A-Za-z]+)\}\{(.*)\}\s*$")
    for p in paths:
        p = ROOT / p
        if not p.is_file():
            continue
        for ln in open(p, encoding="utf-8"):
            m = pat.match(ln.strip())
            if m:
                out[m.group(1)] = m.group(2)
    return out


def ends(b):
    """(lower, upper, point) of a bracket, midpoint when it is a point (N2's rule)."""
    lo, up = float(b["lower"]), float(b["upper"])
    point = float(b["width_rel"]) < POINT_WIDTH_REL
    if point:
        lo = up = 0.5 * (lo + up)
    return lo, up, point


def xs_of(lo, up):
    xs = {lo, up}
    if lo < FLOOR_BH < up:
        xs.add(FLOOR_BH)
    return sorted(xs)


def attach_truth(row, b, base, anchor_obj, prefix=""):
    """N2's attach_oracle on any pair of brackets: g and m intervals of ``row['obj']``."""
    P = prefix
    for k in ("covered", "covered_m", "same_as_base", "opt_lower", "opt_upper", "width_rel",
              "point", "g_lo", "g_hi", "lb2_oracle", "proved_all", "g_anchor_lo",
              "g_anchor_hi", "m_lo", "m_hi", "mbh_lo", "mbh_hi", "_lo_e", "_up_e"):
        row[P + k] = None
    row[P + "covered"] = b is not None
    row[P + "covered_m"] = False
    if b is None:
        return
    lo_e, up_e, point = ends(b)
    obj = row["obj"] if not P else row[P + "obj"]
    row.update({P + "opt_lower": float(b["lower"]), P + "opt_upper": float(b["upper"]),
                P + "width_rel": float(b["width_rel"]), P + "point": point,
                P + "g_lo": gfun(obj, up_e), P + "g_hi": gfun(obj, lo_e),
                P + "lb2_oracle": b.get("lb2_total"), P + "proved_all": bool(b.get("proved_all")),
                P + "_lo_e": lo_e, P + "_up_e": up_e})
    if base is None or anchor_obj is None:
        return
    blo, bup, _bp = ends(base)
    row[P + "covered_m"] = True
    row[P + "same_as_base"] = b is base
    ga_lo, ga_hi = gfun(anchor_obj, bup), gfun(anchor_obj, blo)
    row[P + "g_anchor_lo"], row[P + "g_anchor_hi"] = ga_lo, ga_hi
    if b is base:
        ms = [gfun(obj, x) - gfun(anchor_obj, x) for x in xs_of(lo_e, up_e)]
        row[P + "m_lo"], row[P + "m_hi"] = min(ms), max(ms)
        row[P + "mbh_lo"] = row[P + "mbh_hi"] = obj - anchor_obj
    else:
        row[P + "m_lo"] = row[P + "g_lo"] - ga_hi
        row[P + "m_hi"] = row[P + "g_hi"] - ga_lo
        row[P + "mbh_lo"] = (obj - up_e) - (anchor_obj - blo)
        row[P + "mbh_hi"] = (obj - lo_e) - (anchor_obj - bup)


def board_brackets_or_closed(out_dir=None):
    """Board brackets of ``out_dir``'s census boards, assembled from the relaxed solves on disk.

    Stage 2: the brackets are always assembled from the current boards and the
    solve log (keyed by (instance, t_d, trade, trade fingerprint)), so a board a
    re-run of the census adds is bracketed by the solves that cover it and never
    read from a stale brackets file.
    """
    boards = read_jsonl((out_dir or OUT) / "boards.jsonl")
    path = ORACLE_OUT / "trade_solves.jsonl"
    if path.is_file():
        rel_rows, _ = load_rows_last(path, relaxed_key)
        br, trade_br = assemble_boards(boards, rel_rows)
        source = "oracle"
    else:
        br, trade_br = assemble_boards(boards, {})
        source = "census (LB2-closed boards only)"
    by = {}
    for b in br:
        if b["complete"]:
            b = dict(b)
            b["lb2_total"] = None
            by[(b["iid"], float(b["t_d"]), b["fp"])] = b
    lb2_tot = {(b["iid"], float(b["t_d"]), b["fp"]):
               sum(tv["lb2"] for tv in b["trades"].values()) + b["running_const"] for b in boards}
    for k, b in by.items():
        b["lb2_total"] = lb2_tot.get(k)
    return by, br, boards, source


def full_brackets() -> dict:
    out = {}
    for r in read_jsonl(ORACLE_V1 / "brackets.jsonl"):
        out[(r["instance_id"], r["fingerprint"])] = r
    return out


def build_rows(items, td_br, full_br, anchors):
    """One row per item in N2's row schema, decision-time reading, plus N11's columns."""
    import n2_pricing as n2

    rows = []
    for it in items:
        iid, t_d = it["instance_id"], float(it["t_d"])
        a = anchors[(iid, it["frozen_seed"])]
        anchor_pub = float(a["wwt_original_bh"])
        r = OrderedDict(
            dataset="direct_td" if it["set"] == "published" else "heldout_td",
            row_id=it["item_id"], item_id=it["item_id"], set=it["set"],
            primary_class=it["primary_class"], subclass=it["subclass"], stratum=it["stratum"],
            instance_id=iid, twin_id=it.get("twin_id"), role=it.get("c_role"),
            arm="", thinking="", mode="", repeat="", quality_visible=it["quality_visible"],
            n_ops=it["n_ops"], split=it["split"], constraining=bool(it["dt_constraining"]),
            issuable=it["issuable"], issuable_strict=it["issuable_strict"], t_d=t_d,
            t_start=it["t_start"], n_ref=it["n_ref"], n_known=it["n_known"],
            n_running=it["n_running"], running_const=it["rconst"],
            seed_not_frozen_on_K=len(it.get("seed_not_frozen_on_K") or []),
            terminal=it["dt_term_cert"], stage=it["dt_stage_cert"],
            terminal_feas=it["dt_term_feas"], codes="|".join(it["dt_codes"] or []),
            names_unknown=len(it["names_unknown"]), terminal_pub=it["om_term_cert"],
            terminal_feas_pub=it["om_term_feas"], gap_pub=it["om_gap"], obj_pub=it["om_obj"],
            obj_orig_pub=it["om_obj_orig"], anchor_pub=anchor_pub,
            anchor_gap_pub=float(a["gap"]), anchor_lb_pub=float(a["certificate"]["lb_bh"]),
            obj=None, obj_orig=it["dt_obj_orig"], lb_cert=it["dt_lb"], gap_cert=it["dt_gap"],
            g_cert_anchor=it["an_gap"], ref1=it["an_obj"], ref2=it["dt_ref2"],
            reference_from=it["dt_ref2_from"], fingerprint=it["dt_fp"], anchor_lb_K=it["an_lb"],
            floor_cert=None, rw_terminal=it["rw_term"], rw_obj=it["rw_obj"],
            rw_obj_orig=it["rw_obj_orig"], rw0_obj_orig=it["rw0_obj_orig"],
            pm_pub=it.get("om_p_G-CERT-M"), p2_pub=it.get("om_p_D-REL2"))
        priced = it["dt_stage_cert"] == "qual"
        r["priced"] = priced
        if priced:
            r["obj"] = it["dt_obj"]
            r["floor_cert"] = it["dt_lb"] < FLOOR_BH
            n2.prices(r)
            b = td_br.get((iid, t_d, it["dt_fp"]))
            base = td_br.get((iid, t_d, BASE_FP))
            if b is not None and base is not None and it["dt_fp"] == BASE_FP:
                b = base
            attach_truth(r, b, base, it["an_obj"])
            n2.errors(r)
            r["floor_truth"] = None if b is None else ends(b)[0] < FLOOR_BH
            r["gap_bh"] = it["dt_obj"] - it["dt_lb"]
        else:
            for g in GATE_TOKEN:
                r["p_" + g] = None
            r["covered"] = r["covered_m"] = False
        # Realised consequence: damage on the original fields, and the realised
        # marginal cost against the full-window oracle of the item's fields.
        r["damage_if_applied"] = (None if it["rw_obj_orig"] is None
                                  else it["rw_obj_orig"] - anchor_pub)
        r["damage_if_applied_pub"] = (None if it["om_obj_orig"] is None
                                      else it["om_obj_orig"] - anchor_pub)
        r["real_obj"] = it["rw_obj"]
        fb = full_br.get((iid, it["om_fp"])) if it.get("om_fp") else None
        fbase = full_br.get((iid, BASE_FP))
        if it["rw_obj"] is not None:
            attach_truth(r, fb if it["om_fp"] != BASE_FP else fbase, fbase,
                         float(a["wwt_adjusted_bh"]), prefix="real_")
        else:
            r["real_covered"] = r["real_covered_m"] = False
        rows.append(r)
    return rows


def as_truth(rows, prefix):
    """Copies of the rows whose truth keys are the realised ones (consequence panel)."""
    import n2_pricing as n2

    out = []
    for r in rows:
        c = dict(r)
        for k in ("covered", "covered_m", "same_as_base", "opt_lower", "opt_upper", "width_rel",
                  "point", "g_lo", "g_hi", "g_anchor_lo", "g_anchor_hi", "m_lo", "m_hi",
                  "mbh_lo", "mbh_hi", "_lo_e", "_up_e"):
            c[k] = r.get(prefix + k)
        if not c["covered"]:
            c["covered"] = c["covered_m"] = False
        n2.errors(c)
        out.append(c)
    return out


def published_rows(issuable_ids=None):
    """N2's direct rows as published (types restored), optionally on the issuable items."""
    out = []
    bools = ("quality_visible", "constraining", "same_as_base", "covered", "covered_m", "point",
             "proved_all")
    keep_str = ("dataset", "row_id", "item_id", "primary_class", "subclass", "stratum",
                "instance_id", "arm", "thinking", "mode", "repeat", "split", "reference_from",
                "fingerprint")
    for r in read_csv_comments(ANALYSIS / "N2_rows_direct.csv"):
        if issuable_ids is not None and r["item_id"] not in issuable_ids:
            continue
        c = {}
        for k, v in r.items():
            if k in keep_str:
                c[k] = v
            elif k in bools:
                c[k] = v == "True"
            else:
                c[k] = num_or_none(v)
        lo, up = c.get("opt_lower"), c.get("opt_upper")
        if c["covered"]:
            if c["point"]:
                c["_lo_e"] = c["_up_e"] = 0.5 * (lo + up)
            else:
                c["_lo_e"], c["_up_e"] = lo, up
        out.append(c)
    return out


def share_ci(boot, rows, flags):
    n = len(rows)
    k = sum(1 for f in flags if f)
    lo, hi = boot.ci(rows, flags) if rows else (None, None)
    return {"n": n, "k": k, "share": (k / n) if n else None, "lo": lo, "hi": hi}


def pctf(x, d=1):
    return "n/a" if x is None else "{:.{}f}%".format(100.0 * x, d)


def numf(x, d=3):
    return "n/a" if x is None else "{:.{}f}".format(x, d)


def median(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


def pctl(xs, q):
    import numpy as np

    xs = [x for x in xs if x is not None]
    return float(np.percentile(np.asarray(xs, dtype=float), q)) if xs else None


def md_table(head, body) -> str:
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    for b in body:
        out.append("| " + " | ".join(str(x) for x in b) + " |")
    return "\n".join(out)


def write_csv_rows(path, rows, header_lines, columns=None):
    columns = columns or list(rows[0].keys()) if rows else []
    with open(path, "w", newline="", encoding="utf-8") as fh:
        for h in header_lines:
            fh.write("# " + h + "\n")
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: fmt_cell(r.get(k)) for k in columns})


def fmt_cell(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return "{:.6f}".format(v)
    if isinstance(v, (list, dict)):
        return json.dumps(v, sort_keys=True)
    return v


class Macros:
    def __init__(self, published):
        self.lines = []
        self.map = []
        self.names = set()
        self.published = published

    def add(self, name, value, twin_of=None, exhibit="", note=""):
        if not name.isalpha():
            raise SystemExit("macro name {} is not alphabetic".format(name))
        if name in self.names:
            raise SystemExit("macro {} written twice".format(name))
        self.names.add(name)
        self.lines.append("\\newcommand{\\" + name + "}{" + str(value) + "}")
        self.map.append(OrderedDict(published_macro=twin_of or "",
                                    published_value=self.published.get(twin_of, "") if twin_of else "",
                                    twin=name, late_twin=("nElevenLate" + name[len("nEleven"):])
                                    if twin_of else "", value=str(value), exhibit=exhibit,
                                    note=note))

    def twin(self, published, value, exhibit, note=""):
        name = "nEleven" + published[:1].upper() + published[1:]
        if published not in self.published:
            note = (note + "; " if note else "") + "published macro not found"
        self.add(name, value, twin_of=published, exhibit=exhibit, note=note)


def pct_tex(x, d=1):
    return "n/a" if x is None else "{:.{}f}\\%".format(100.0 * x, d)


def group_int(n):
    return "{:,}".format(int(n)).replace(",", "{,}")


def cmd_analyse(args) -> int:
    import n2_pricing as n2
    import n9_gates as n9g

    pin_cores(args.cores_t)
    cap_threads(1)
    t0 = time.time()
    reading = getattr(args, "reading", "primary")
    in_dir = OUT if reading == "primary" else OUT / reading
    for path in (in_dir / "census_assertions.json", OUT / "omni_assertions.json"):
        rep = json.loads(path.read_text())
        if rep.get("status") != "PASS":
            raise SystemExit("REFUSING TO RUN: {} says {}".format(path, rep.get("status")))
    items = read_jsonl(in_dir / "items.jsonl")
    anchors = load_anchor_records()
    td_br, br_all, boards, br_source = board_brackets_or_closed(in_dir)
    full_br = full_brackets()
    rows_all = build_rows(items, td_br, full_br, anchors)
    pub_rows = [r for r in rows_all if r["set"] == "published"]
    held_rows = [r for r in rows_all if r["set"] == "heldout"]
    iss = [r for r in pub_rows if r["issuable"]]
    iss_ids = {r["item_id"] for r in iss}
    priced = [r for r in iss if r["priced"]]
    check = Checker()

    # ---- A14: coverage of every needed board
    need = set()
    for r in iss + [h for h in held_rows if h["issuable"]]:
        if r["priced"]:
            need.add((r["instance_id"], r["t_d"], r["fingerprint"]))
            need.add((r["instance_id"], r["t_d"], BASE_FP))
    covered = sum(1 for k in need if k in td_br)
    complete = covered == len(need)
    status = "COMPLETE" if complete else "PARTIAL"
    # ---- A13: every solve row carries the timing record; no invalid row in a table
    timing_keys = ("affinity", "workers", "omp_num_threads", "load_avg_start", "load_avg_end",
                   "wall_s", "solve_wall_s", "cpu_s", "cpu_share", "solve_cpu_share",
                   "foreign_cpu_s", "foreign_share", "status", "budget_s")
    solve_rows = read_jsonl(ORACLE_OUT / "trade_solves.jsonl") + \
        read_jsonl(ORACLE_OUT / "c_solves.jsonl")
    for sr in solve_rows:
        check.true("A13", "solve row carries the timing record", all(k in sr for k in timing_keys),
                   [k for k in timing_keys if k not in sr])
    rel_rows, rel_drops = load_rows_last(ORACLE_OUT / "trade_solves.jsonl", relaxed_key)
    c_rows, c_drops = load_rows_last(ORACLE_OUT / "c_solves.jsonl", lambda r: r["key"])
    for k, sr in list(rel_rows.items()) + list(c_rows.items()):
        check.true("A13", "no invalid solve row enters a table: {}".format(k),
                   not sr.get("invalid") or sr.get("invalid_persistent"))
    n_persist = sum(1 for sr in list(rel_rows.values()) + list(c_rows.values())
                    if sr.get("invalid_persistent"))
    # ---- A9 (oracle part): obj_K at or above the board's lower end; LB_K <= obj
    for r in priced:
        if r["covered"]:
            check.true("A9", "obj_K >= board lower on " + r["item_id"],
                       r["obj"] >= float(r["opt_lower"]) - CHECK_TOL,
                       "{} < {}".format(r["obj"], r["opt_lower"]))
            check.true("A9", "certificate bound <= board upper on " + r["item_id"],
                       r["lb_cert"] <= float(r["opt_upper"]) + CHECK_TOL,
                       "{} > {}".format(r["lb_cert"], r["opt_upper"]))
    for b in br_all:
        if b["complete"]:
            check.true("A9", "board lower <= upper {} {}".format(b["iid"], b["t_d"]),
                       b["lower"] <= b["upper"] + CHECK_TOL)

    published = load_macros(PUBLISHED_MACRO_FILES)
    M = Macros(published) if reading == "primary" else LateMacros(published)
    boot = n2.Boot({r["instance_id"] for r in pub_rows}, n2.SEED, n2.B_BOOT)
    S = OrderedDict()  # summary sections (markdown)

    # ================================================================ census
    S["census"] = census_section(pub_rows, held_rows, M)

    # ================================================================ Table 10
    S["direct"] = direct_section(pub_rows, iss, boot, M)

    # ================================================================ Table 14
    groupings = [("all", lambda r: ["all"]), ("stratum", lambda r: [r["stratum"]]),
                 ("class", lambda r: [r["primary_class"]])]
    pr_td = n2.pricing_table(priced, "direct_td", groupings)
    pub_all = published_rows()
    pub_iss = published_rows(iss_ids)
    pr_pub = n2.pricing_table(pub_all, "direct", groupings)
    pr_pub_iss = n2.pricing_table(pub_iss, "direct_issuable", groupings)
    S["pricing"] = pricing_section(pr_td, pr_pub, pr_pub_iss, priced, M)

    # ================================================================ Table 15
    S["refgap"] = refgap_section(iss, priced, td_br, pr_td, n2, M)

    # ================================================================ Table 16
    dg14 = dict(DG14)
    rg_by, crg_by = S["refgap"]["_by_stratum"], S["refgap"]["_cert_by_stratum"]
    wins_td = n2.wins_table(priced, "direct_td", dg14, rg_by, crg_by)
    real_rows = as_truth(priced, "real_")
    wins_real = n2.wins_table(real_rows, "direct_td_realised", dg14, rg_by, crg_by)
    disp_td = n2.disposition_table(priced, "direct_td", dg14, {}, boot)
    disp_real = n2.disposition_table(real_rows, "direct_td_realised", dg14, {}, boot)
    S["decision"] = decision_section(wins_td, wins_real, disp_td, M)

    # ================================================================ Table 17
    if reading == "primary":
        cb = {r["item_id"]: r for r in read_jsonl(ORACLE_OUT / "c_brackets.jsonl")}
        S["heldout"] = heldout_section(held_rows, pub_rows, cb, dg14, boot, n9g, M)

    # ================================================================ S10, 5.1, information
    S["field"] = field_section(iss, M)
    S["damage"] = damage_section(iss, pub_rows, boot, M)
    S["info"] = info_section(priced, M)
    S["oracle"] = oracle_section(need, td_br, rel_rows, c_rows, M)
    if reading == "primary":
        S["n8"] = n8_section(published, M)
    S["changes"] = changes_section(S, published, M)
    if reading != "primary":
        return write_late_outputs(args, in_dir, S, M, rows_all, pr_td, wins_td, wins_real,
                                  disp_td, disp_real, check, status, covered, need, br_source,
                                  n_persist, items, t0)

    # ================================================================ outputs
    cols = list(rows_all[0].keys())
    for r in rows_all:
        for k in r:
            if k not in cols and not k.startswith("_"):
                cols.append(k)
    cols = [c for c in cols if not c.startswith("_") and not c.startswith("real__")]
    hdr = ["N11 decision-time rows, direct benchmark and held-out set ({})".format(VERSION),
           "generated by code/scripts/n11_decision_time.py analyse; truth on K = decision-time "
           "oracle ({}), status {}".format(br_source, status),
           "realised columns: full-window run from t_d, original fields; real_* truth = "
           "results/oracle_v1 brackets of the item's full-window fields"]
    write_csv_rows(ANALYSIS / "N11_rows_direct.csv", rows_all, hdr, cols)
    for name, table in (("N11_pricing.csv", pr_td + pr_pub_iss), ("N11_wins.csv", wins_td + wins_real),
                        ("N11_disposition.csv", disp_td + disp_real)):
        if table:
            write_csv_rows(ANALYSIS / name, table, hdr[:2], list(table[0].keys()))
    M.lines.insert(0, "% N11 macros ({}), status {}; generated by code/scripts/"
                      "n11_decision_time.py analyse".format(VERSION, status))
    if not complete:
        M.lines.insert(0, "% PARTIAL: not every needed decision-time bracket is on disk; "
                          "not for publication")
    M.add("nElevenCoverageStatus", status.lower(), exhibit="coverage")
    M.add("nElevenBoardsNeeded", group_int(len(need)), exhibit="coverage")
    M.add("nElevenBoardsCovered", group_int(covered), exhibit="coverage")
    (ANALYSIS / "N11_macros.tex").write_text("\n".join(M.lines) + "\n")
    write_csv_rows(ANALYSIS / "N11_macro_map.csv", M.map, hdr[:1],
                   ["published_macro", "published_value", "twin", "late_twin", "value",
                    "exhibit", "note"])
    rep = check.report()
    summary = summary_md(S, status, covered, len(need), br_source, rep, n_persist, items)
    (ANALYSIS / "N11_summary.md").write_text(summary)
    check.fatal(OUT / "analyse_assertions.json", {"status_coverage": status,
                                                  "boards_needed": len(need),
                                                  "boards_covered": covered})
    print("[n11 analyse] {} ({} of {} boards), {} checks, {:.0f}s".format(
        status, covered, len(need), rep["n_checks"], time.time() - t0), flush=True)
    return 0


class LateMacros(Macros):
    """The late reading's macros: every name carries ``Late`` after ``nEleven``."""

    def add(self, name, value, twin_of=None, exhibit="", note=""):
        if name.startswith("nEleven") and not name.startswith("nElevenLate"):
            name = "nElevenLate" + name[len("nEleven"):]
        Macros.add(self, name, value, twin_of=twin_of, exhibit=exhibit, note=note)
        self.map[-1]["late_twin"] = ""


def write_late_outputs(args, in_dir, S, M, rows_all, pr_td, wins_td, wins_real, disp_td,
                       disp_real, check, status, covered, need, br_source, n_persist, items, t0):
    """The late reading's rows, macros and summary, kept in its own folder for analyse2."""
    cols = list(rows_all[0].keys())
    for r in rows_all:
        for k in r:
            if k not in cols and not k.startswith("_"):
                cols.append(k)
    cols = [c for c in cols if not c.startswith("_") and not c.startswith("real__")]
    hdr = ["N11 late reading (t_d' = t_start), direct benchmark ({})".format(VERSION),
           "generated by code/scripts/n11_decision_time.py analyse --reading late; truth on K = "
           "decision-time oracle ({}), status {}".format(br_source, status)]
    write_csv_rows(in_dir / "N11_late_rows_direct.csv", rows_all, hdr, cols)
    for name, table in (("N11_late_pricing.csv", pr_td), ("N11_late_wins.csv", wins_td + wins_real),
                        ("N11_late_disposition.csv", disp_td + disp_real)):
        if table:
            write_csv_rows(in_dir / name, table, hdr[:2], list(table[0].keys()))
    M.add("nElevenLateCoverageStatus", status.lower(), exhibit="coverage")
    M.add("nElevenLateBoardsNeeded", group_int(len(need)), exhibit="coverage")
    M.add("nElevenLateBoardsCovered", group_int(covered), exhibit="coverage")
    (in_dir / "N11_late_macros.tex").write_text("\n".join(M.lines) + "\n")
    write_csv_rows(in_dir / "N11_late_macro_map.csv", M.map, hdr[:1],
                   ["published_macro", "published_value", "twin", "late_twin", "value",
                    "exhibit", "note"])
    md = []
    for key, title in (("census", "Issuability at the late instant"),
                       ("direct", "Table 10 twin (late reading)"),
                       ("pricing", "Table 14 twin (late reading)"),
                       ("refgap", "Table 15 twin (late reading)"),
                       ("decision", "Table 16 twin (late reading)"),
                       ("field", "Table S10 twin (late reading, direct)"),
                       ("damage", "Section 5.1 twin (late reading, direct)"),
                       ("oracle", "Oracle coverage (late reading)"),
                       ("changes", "What changed against the published reading (late)")):
        if key in S:
            md += ["### " + title, "", S[key]["md"], ""]
    (in_dir / "N11_late_summary.md").write_text("\n".join(md) + "\n")
    rep = check.report()
    check.fatal(in_dir / "analyse_assertions.json", {"status_coverage": status,
                                                     "boards_needed": len(need),
                                                     "boards_covered": covered})
    print("[n11 analyse late] {} ({} of {} boards), {} checks, {:.0f}s".format(
        status, covered, len(need), rep["n_checks"], time.time() - t0), flush=True)
    return 0


# --------------------------------------------------------------------------- #
# Analyse: sections                                                             #
# --------------------------------------------------------------------------- #
STOP_TERMS = ("blocked_schema", "blocked_feas", "blocked_qual")


def prow(table, truth, split, gate, gkind="all", gv="all"):
    for r in table:
        if (r["truth"] == truth and r["split"] == split and r["gate"] == gate
                and r["group_kind"] == gkind and str(r["group"]) == str(gv)):
            return r
    return None


def wrow(table, truth, delta, stratum="all", cls="all", split="all", rule="D-REL2"):
    for r in table:
        if (r["truth"] == truth and abs(r["delta"] - delta) < 1e-12 and r["rule"] == rule
                and r["stratum"] == stratum and r["cls"] == cls and r["split"] == split):
            return r
    return None


def drow(table, truth, op, gate, delta, cls="all", split="all"):
    for r in table:
        if (r["truth"] == truth and r["operating_point"] == op and r["gate"] == gate
                and abs(r["delta"] - delta) < 1e-12 and r["cls"] == cls and r["split"] == split):
            return r
    return None


def ival(lo, hi, d=3):
    if lo is None:
        return "n/a"
    if abs(lo - hi) < 0.5 * 10 ** (-d):
        return "{:.{}f}".format(lo, d)
    return "{:.{}f} to {:.{}f}".format(lo, d, hi, d)


def census_section(pub_rows, held_rows, M) -> dict:
    out = {"head": []}
    lines = []
    body = []
    tot = Counter()
    for cls, tok in CLASS_TOKEN.items():
        rs = [r for r in pub_rows if r["primary_class"] == cls]
        ex = [r for r in rs if not r["issuable"]]
        exs = [r for r in rs if not r["issuable_strict"]]
        ok = [r for r in rs if r["issuable"]]
        td_med = median([r["t_d"] for r in ok])
        k_med = median([r["n_known"] for r in ok])
        body.append([cls, len(rs), len(ok), len(ex), pctf(len(ex) / len(rs)), len(exs),
                     numf(td_med, 1), numf(k_med, 0)])
        tot.update(items=len(rs), ok=len(ok), ex=len(ex), exs=len(exs))
        M.add("nElevenIssuable{}Items".format(tok), group_int(len(ok)), exhibit="census")
        M.add("nElevenIssuable{}Excluded".format(tok), group_int(len(ex)), exhibit="census")
        M.add("nElevenIssuable{}ExcludedShare".format(tok), pct_tex(len(ex) / len(rs)),
              exhibit="census")
        M.add("nElevenIssuableStrict{}Excluded".format(tok), group_int(len(exs)), exhibit="census")
        if td_med is not None:
            M.add("nElevenInfo{}DecisionMedian".format(tok), "{:.1f}".format(td_med),
                  exhibit="census")
    body.append(["all", tot["items"], tot["ok"], tot["ex"], pctf(tot["ex"] / tot["items"]),
                 tot["exs"], numf(median([r["t_d"] for r in pub_rows if r["issuable"]]), 1),
                 numf(median([r["n_known"] for r in pub_rows if r["issuable"]]), 0)])
    M.add("nElevenIssuableAllItems", group_int(tot["ok"]), exhibit="census")
    M.add("nElevenIssuableAllExcluded", group_int(tot["ex"]), exhibit="census")
    M.add("nElevenIssuableAllExcludedShare", pct_tex(tot["ex"] / tot["items"]), exhibit="census")
    M.add("nElevenIssuableStrictAllExcluded", group_int(tot["exs"]), exhibit="census")
    M.add("nElevenInfoKnownMedian", group_int(median([r["n_known"] for r in pub_rows
                                                      if r["issuable"]])), exhibit="census")
    lines.append("### Issuability by class (published suite, closed rule; strict rule as subset)\n")
    lines.append(md_table(["class", "items", "issuable", "not issuable", "not-issuable share",
                           "not issuable (strict)", "median t_d (bh)", "median |K|"], body))
    # by stratum
    body = []
    for st, stok in STRATUM_TOKEN.items():
        row = [STRATUM_NAME[st]]
        for cls in ("benign", "V3", "V4"):
            rs = [r for r in pub_rows if r["primary_class"] == cls and r["stratum"] == st]
            ex = sum(1 for r in rs if not r["issuable"])
            row.append("{} of {}".format(ex, len(rs)))
        rs = [r for r in pub_rows if r["stratum"] == st]
        row.append("{} of {}".format(sum(1 for r in rs if not r["issuable"]), len(rs)))
        body.append(row)
    lines.append("\n### Not issuable by stratum\n")
    lines.append(md_table(["stratum", "benign", "V3", "V4", "all"], body))
    # by subclass
    sub = defaultdict(lambda: [0, 0, 0])
    for r in pub_rows:
        k = (r["primary_class"], r["subclass"])
        sub[k][0] += 1
        sub[k][1] += int(not r["issuable"])
        sub[k][2] += int(not r["issuable_strict"])
    body = [[c, s_, n, e, es] for (c, s_), (n, e, es) in sorted(sub.items()) if e or es]
    lines.append("\n### Subclasses with excluded items (closed and strict rule)\n")
    lines.append(md_table(["class", "subclass", "items", "not issuable", "not issuable (strict)"],
                          body))
    full = [s_ for (c, s_), (n, e, es) in sub.items() if e == n]
    lines.append("\nSubclasses with no decision-time reading (every item excluded): {}.".format(
        ", ".join(sorted(full)) or "none"))
    # twins and held-out
    by = {r["item_id"]: r for r in pub_rows}
    pairs = [(r, by.get(r["twin_id"])) for r in pub_rows if r["primary_class"] in ("V3", "V4")
             and r.get("twin_id") in by]
    comp = Counter()
    for a, b in pairs:
        comp[(a["primary_class"], a["issuable"] and b["issuable"])] += 1
    hv = [r for r in held_rows if r["primary_class"] == "V3"]
    ht = [r for r in held_rows if r["primary_class"] == "benign"]
    hv_ok, ht_ok = sum(1 for r in hv if r["issuable"]), sum(1 for r in ht if r["issuable"])
    M.add("nElevenIssuableHeldoutVThree", group_int(hv_ok), exhibit="census")
    M.add("nElevenIssuableHeldoutTwins", group_int(ht_ok), exhibit="census")
    nsf = sum(1 for r in pub_rows if r["seed_not_frozen_on_K"])
    nsf_iss = sum(1 for r in pub_rows if r["seed_not_frozen_on_K"] and r["issuable"])
    M.add("nElevenInfoSeedNotFrozen", group_int(nsf_iss), exhibit="census",
          note="issuable items whose standing frozen set holds a planned order not frozen on K")
    lines.append("\nTwin-complete pairs (both members issuable): V3 {} of {}, V4 {} of {}. "
                 "Held-out: {} of {} V3 items and {} of {} benign twins are issuable.".format(
                     comp[("V3", True)], comp[("V3", True)] + comp[("V3", False)],
                     comp[("V4", True)], comp[("V4", True)] + comp[("V4", False)],
                     hv_ok, len(hv), ht_ok, len(ht)))
    lines.append("\nItems whose standing frozen set holds a planned order released after t_d "
                 "and already on the calendar at t_d: {} items, {} of them issuable. Stage 2 "
                 "freezes these orders on K (the frozen set is the running work plus every "
                 "seed order K holds); N8's `known_frozen`, which keeps only queued and running "
                 "seed orders, is used for the continuity assertion A6 only.".format(
                     nsf, nsf_iss))
    out["md"] = "\n".join(lines)
    out["head"].append(("Items not issuable (closed rule)", None, None, tot["ex"], "count"))
    return out


def direct_section(pub_rows, iss, boot, M) -> dict:
    out = {"head": []}
    body = []
    for cls, tok in CLASS_TOKEN.items():
        allr = [r for r in pub_rows if r["primary_class"] == cls]
        rs = [r for r in iss if r["primary_class"] == cls]
        wp = sum(1 for r in rs if r["n_ops"] > 0)
        st = Counter(r["terminal"] for r in rs)
        stp = Counter(r["terminal_pub"] for r in rs)
        sta = Counter(r["terminal_pub"] for r in allr)
        stopped = sum(st[t] for t in STOP_TERMS)
        stopped_pi = sum(stp[t] for t in STOP_TERMS)
        stopped_pa = sum(sta[t] for t in STOP_TERMS)
        flags = [r["terminal"] in STOP_TERMS for r in rs]
        ci = share_ci(boot, rs, flags)
        body.append([cls, len(allr), len(rs), wp, "{} ({})".format(stopped, pctf(ci["share"])),
                     st["blocked_schema"], st["blocked_feas"], st["blocked_qual"],
                     "{} ({})".format(stopped_pi, pctf(stopped_pi / len(rs) if rs else None)),
                     "{} ({})".format(stopped_pa, pctf(stopped_pa / len(allr)))])
        if cls == "benign":
            M.twin("dgBenignCanonicalBlocks", group_int(stopped), "Table 10")
            M.twin("dgBenignCanonicalShare", pct_tex(ci["share"]), "Table 10")
            M.twin("dgBenignCanonicalFeasBlocks", group_int(st["blocked_feas"]), "Table 10")
            M.twin("dgBenignCanonicalFeasShare", pct_tex(st["blocked_feas"] / len(rs)), "Table 10")
            M.twin("dgBenignCanonicalQualBlocks", group_int(st["blocked_qual"]), "Table 10")
            out["benign_codes"] = Counter(r["codes"] for r in rs if r["terminal"] in STOP_TERMS)
            out["head"].append(("Table 10: benign stopped share", sta and stopped_pa / len(allr),
                                stopped_pi / len(rs), ci["share"], "share"))
        else:
            M.twin("dg{}CanonicalShare".format(tok), pct_tex(ci["share"]), "Table 10")
        if cls == "V3":
            M.twin("dgVThreeCanonicalRefused", group_int(st["blocked_qual"]), "Table 10")
            M.twin("dgVThreeCanonicalItems", group_int(len(rs)), "Table 10")
            M.twin("dgVThreeCanonicalCI", "{:.1f} to {:.1f} percent".format(
                100 * ci["lo"], 100 * ci["hi"]) if ci["lo"] is not None else "n/a", "Table 10")
            out["head"].append(("Table 10: V3 referral share (stopped)", stopped_pa / len(allr),
                                stopped_pi / len(rs), ci["share"], "share"))
            out["v3_ci"] = ci
        if cls in ("V1", "V5", "V6"):
            M.twin("dg{}CanonicalEmpty".format(tok), group_int(len(rs) - wp), "Table 10")
        if cls == "V5":
            M.twin("dgVFiveCanonicalRefused", group_int(st["blocked_qual"]), "Table 10")
        if cls in ("V2", "V4", "V6", "V1"):
            out["head"].append(("Table 10: {} stopped share".format(cls), stopped_pa / len(allr),
                                stopped_pi / len(rs) if rs else None, ci["share"], "share"))
    md = ["Stopped counts at t_d among issuable items; the right two columns give the "
          "published (t = 0) reading on the same issuable items and on all items.\n",
          md_table(["class", "items", "issuable", "with a proposal", "stopped at t_d",
                    "schema", "feas.", "quality", "t=0 on issuable", "t=0 all items"], body)]
    bc = out.get("benign_codes") or Counter()
    md.append("\nBenign stops at t_d by blocking code: " + (", ".join(
        "{} {}".format(k or "(quality)", v) for k, v in bc.most_common()) or "none") + ".")
    # Attribution of the terminal changes to N8's frozen-set convention.
    chg = Counter()
    for r in iss:
        if r["terminal"] != r["terminal_pub"]:
            chg[(r["primary_class"], r["terminal_pub"], r["terminal"],
                 "names an order unknown at t_d" if r["names_unknown"] else
                 ("seed holds a planned order scheduled at t_d" if r["seed_not_frozen_on_K"]
                  else "other"))] += 1
    if chg:
        md.append("\nTerminal changes between t = 0 and t_d on issuable items, with the cause "
                  "(an item counts under 'seed holds a planned order scheduled at t_d' when its "
                  "standing frozen set holds a planned order released after t_d; under the "
                  "Stage 2 frozen set that order is frozen on K):\n")
        md.append(md_table(["class", "t = 0 terminal", "t_d terminal", "cause", "items"],
                           [list(k) + [v] for k, v in sorted(chg.items())]))
        n_conv = sum(v for k, v in chg.items()
                     if k[3] == "seed holds a planned order scheduled at t_d")
        M.add("nElevenTerminalChangesFrozenConvention", group_int(n_conv), exhibit="Table 10")
        M.add("nElevenTerminalChanges", group_int(sum(chg.values())), exhibit="Table 10")
        md.append("")
    v3 = out.get("v3_ci")
    if v3:
        md.append("V3 stopped share at t_d {} (95% cluster bootstrap {} to {}, n = {}).".format(
            pctf(v3["share"]), pctf(v3["lo"]), pctf(v3["hi"]), v3["n"]))
    out["md"] = "\n".join(md)
    return out


def floor_lines(priced) -> str:
    n = len(priced)
    fc = sum(1 for r in priced if r["floor_cert"])
    ft = sum(1 for r in priced if r.get("floor_truth"))
    gap_bh = [r["gap_bh"] for r in priced]
    ebh = [0.5 * (r["ebh_lo_D-ABS"] + r["ebh_hi_D-ABS"]) for r in priced
           if r.get("ebh_lo_D-ABS") is not None]
    obj_opt = [r["obj"] - 0.5 * (r["_lo_e"] + r["_up_e"]) for r in priced if r["covered"]]
    return ("Floor regime: {} of {} priced rows ({}) have LB_K < 1 bh, so their certified gap "
            "is obj - LB in bh; {} ({}) have an oracle lower end below 1 bh. bh-scale reading: "
            "median obj_K - LB_K {} bh (p95 {}), median obj_K - OPT_K {} bh (p95 {}), median "
            "D-ABS error {} bh.".format(fc, n, pctf(fc / n if n else None), ft,
                                        pctf(ft / n if n else None), numf(median(gap_bh), 3),
                                        numf(pctl(gap_bh, 95), 3), numf(median(obj_opt), 3),
                                        numf(pctl(obj_opt, 95), 3), numf(median(ebh), 3)))


def pricing_section(pr_td, pr_pub, pr_pub_iss, priced, M) -> dict:
    out = {"head": []}
    md = []
    for label, ttag, lab in (("absolute", "", "Absolute"), ("marginal", "Marg", "Marginal")):
        body = []
        for g, gt in GATE_TOKEN.items():
            r = prow(pr_td, label, "all", g)
            rp = prow(pr_pub, label, "all", g)
            ri = prow(pr_pub_iss, label, "all", g)
            if r is None or not r["priced"]:
                body.append([g, "n/a"] * 1 + [""] * 6)
                continue
            stem = "nTwoDirect" + ttag + gt
            M.twin(stem + "MedianError", ival(r["e_median_lo"], r["e_median_hi"]), "Table 14")
            if r["under_share"] is not None:
                M.twin(stem + "UnderShare", pct_tex(r["under_share"]), "Table 14")
            if r["over_share"] is not None:
                M.twin(stem + "OverShare", pct_tex(r["over_share"]), "Table 14")
            body.append([g, r["priced"], ival(r["e_median_lo"], r["e_median_hi"]),
                         pctf(r["under_share"]), pctf(r["over_share"]),
                         "{} / {} / {}".format(ival(rp["e_median_lo"], rp["e_median_hi"]),
                                               pctf(rp["under_share"]), pctf(rp["over_share"]))
                         if rp else "n/a",
                         "{} / {} / {}".format(ival(ri["e_median_lo"], ri["e_median_hi"]),
                                               pctf(ri["under_share"]), pctf(ri["over_share"]))
                         if ri else "n/a"])
            out["head"].append(("Table 14 {}: {} under share".format(lab.lower(), g),
                                rp and rp["under_share"], ri and ri["under_share"],
                                r["under_share"], "share"))
            out["head"].append(("Table 14 {}: {} median error".format(lab.lower(), g),
                                rp and 0.5 * (rp["e_median_lo"] + rp["e_median_hi"]),
                                ri and 0.5 * (ri["e_median_lo"] + ri["e_median_hi"]),
                                0.5 * (r["e_median_lo"] + r["e_median_hi"]), "signed"))
        md.append("\n### {} reading (error = price - decision-time oracle cost on K)\n".format(lab))
        md.append(md_table(["gate", "n priced", "median error", "under", "over",
                            "t=0 all (median / under / over)",
                            "t=0 issuable (median / under / over)"], body))
    body = []
    for g, gt in GATE_TOKEN.items():
        row = [g]
        for sp in ("sequencing_only", "field_changing", "empty"):
            r = prow(pr_td, "marginal", sp, g)
            if r is not None and r["under_share"] is not None:
                M.twin("nTwoDirectMarg{}{}UnderShare".format(SPLIT_TOKEN[sp], gt),
                       pct_tex(r["under_share"]), "Table 14")
                row.append("{} (n={})".format(pctf(r["under_share"]), r["priced"]))
            else:
                row.append("n/a")
        body.append(row)
    md.append("\n### Marginal under share by operation type\n")
    md.append(md_table(["gate", "sequencing only", "field changing", "empty"], body))
    md.append("\n" + floor_lines(priced))
    r = prow(pr_td, "absolute", "all", "G-CERT")
    M.twin("nTwoDirectCovered", group_int(r["covered"] if r else 0), "Table 14 / Fig. 5")
    M.twin("nTwoDirectRows", group_int(len(priced)), "Table 14")
    out["md"] = "\n".join(md)
    return out


def refgap_section(iss, priced, td_br, pr_td, n2, M) -> dict:
    out = {"head": []}
    gaps = defaultdict(list)
    certg = defaultdict(list)
    for r in iss:
        if r["ref1"] is None:
            continue
        b = td_br.get((r["instance_id"], r["t_d"], BASE_FP))
        certg["all"].append(r["g_cert_anchor"])
        certg[r["stratum"]].append(r["g_cert_anchor"])
        if b is None:
            continue
        lo, up, _p = ends(b)
        g = (gfun(r["ref1"], up), gfun(r["ref1"], lo))
        gaps["all"].append(g)
        gaps[r["stratum"]].append(g)
    by_stratum, cert_by = {}, {}
    body = []
    for st, tok, name in [("all", "All", "Pooled")] + [(s_, t, STRATUM_NAME[s_])
                                                        for s_, t in STRATUM_TOKEN.items()]:
        gs = gaps.get(st, [])
        med = (median([g[0] for g in gs]), median([g[1] for g in gs])) if gs else (None, None)
        mx = (max(g[0] for g in gs), max(g[1] for g in gs)) if gs else (None, None)
        by_stratum[st] = med
        cert_by[st] = median(certg.get(st, []))
        zero = sum(1 for g in gs if g[1] <= 1e-12)
        if med[0] is not None:
            M.twin("nTwoRefGap{}Median".format(tok),
                   ival(100 * med[0], 100 * med[1], 1) + "\\%", "Table 15")
            M.twin("nTwoRefGap{}Max".format(tok), ival(100 * mx[0], 100 * mx[1], 1) + "\\%",
                   "Table 15")
        ra = prow(pr_td, "absolute", "all", "D-REL2", "stratum" if st != "all" else "all",
                  st if st != "all" else "all")
        rm = prow(pr_td, "marginal", "all", "D-REL2", "stratum" if st != "all" else "all",
                  st if st != "all" else "all")
        stt = "" if st == "all" else tok
        if ra and ra["priced"]:
            M.twin("nTwoDirect{}RelTwoMedianError".format(stt),
                   ival(ra["e_median_lo"], ra["e_median_hi"]), "Table 15") if stt else None
        if rm and rm["priced"]:
            M.twin("nTwoDirectMarg{}RelTwoMedianError".format(stt),
                   ival(rm["e_median_lo"], rm["e_median_hi"]), "Table 15") if stt else None
        body.append([name, len(gs), ival(med[0], med[1]), ival(mx[0], mx[1]), zero,
                     ival(ra["e_median_lo"], ra["e_median_hi"]) if ra and ra["priced"] else "n/a",
                     ival(rm["e_median_lo"], rm["e_median_hi"]) if rm and rm["priced"] else "n/a"])
    md = ["Anchor gap on K at t_d = (anchor dispatch of K - OPT_K)/max(OPT_K, 1), one value per "
          "issuable item (its (instance, t_d) board).\n",
          md_table(["stratum", "items", "anchor gap median", "max", "items with gap 0",
                    "D-REL2 median error (abs)", "D-REL2 median error (marg)"], body)]
    cm = n2.cert_marginal_table(priced, "direct_td")
    body = []
    for cls, tok in (("benign", "Benign"), ("V3", "VThree"), ("all", "All")):
        r = next((x for x in cm if x["split"] == "all" and x["cls"] == cls), None)
        if r is None:
            continue
        for k, nm in (("cert_referred", "CertReferred"), ("certm_referred", "CertMReferred"),
                      ("removed_by_marginal", "CertMRemoved"),
                      ("cert_referred_explained_by_anchor", "CertReferredExplainedByAnchor")):
            if cls == "V3" and k == "cert_referred":
                continue
            M.twin("nTwoDirect{}{}".format(tok, nm), group_int(r[k]), "Table 15")
        body.append([cls, r["cert_referred"], r["certm_referred"], r["removed_by_marginal"],
                     r["added_by_marginal"], r["cert_referred_explained_by_anchor"]])
        if cls == "benign":
            out["head"].append(("Table 15: benign G-CERT referrals", None, None,
                                r["cert_referred"], "count"))
    md.append("\nCertificate referrals at tau = 0.20 that the marginal certificate removes (t_d):\n")
    md.append(md_table(["class", "G-CERT referred", "G-CERT-M referred", "removed", "added",
                        "explained by anchor gap"], body))
    out["md"] = "\n".join(md)
    out["_by_stratum"] = by_stratum
    out["_cert_by_stratum"] = cert_by
    out["head"].append(("Table 15: pooled anchor-gap median", None, None,
                        by_stratum["all"][1] if by_stratum.get("all") else None, "share"))
    return out


def decision_section(wins_td, wins_real, disp_td, M) -> dict:
    out = {"head": []}
    md = []
    cells = (("absolute", "", "rule_miss", "RelTwoMissRate"),
             ("absolute", "", "cert_miss", "CertMissRate"),
             ("absolute", "", "certm_miss", "CertMMissRate"),
             ("marginal", "Marg", "cert_fr", "CertFalseReferralRate"),
             ("marginal", "Marg", "certm_miss", "CertMMissRate"),
             ("marginal", "Marg", "unionm_fr", "UnionFalseReferralRate"))
    for table, panel in ((wins_td, "pricing (decision-time oracle on K)"),
                         (wins_real, "consequence (realised marginal cost, full window)")):
        body = []
        for st, stok in [("all", "")] + list(STRATUM_TOKEN.items()):
            for delta in (0.10, 0.20):
                row = [STRATUM_NAME.get(st, "Pooled"), delta]
                for truth_l, ttag, name, ntok in cells:
                    w = wrow(table, truth_l, delta, st)
                    if w is None or w[name + "_rate"] is None:
                        row.append("n/a")
                        continue
                    den = w["oracle_costly"] if name.endswith("miss") else w["oracle_cheap"]
                    row.append("{} ({}/{})".format(pctf(w[name + "_rate"]), w[name + "_n"], den))
                    if table is wins_td:
                        dtok = "Ten" if delta == 0.10 else "Twenty"
                        M.twin("nTwoDirect{}{}{}{}".format(ttag, stok, ntok, dtok),
                               pct_tex(w[name + "_rate"]), "Table 16")
                    else:
                        dtok = "Ten" if delta == 0.10 else "Twenty"
                        M.add("nElevenRealDirect{}{}{}{}".format(ttag, stok, ntok, dtok),
                              pct_tex(w[name + "_rate"]), exhibit="Table 16 consequence panel")
                body.append(row)
        md.append("\n### Panel: {}\n".format(panel))
        md.append(md_table(["stratum", "delta", "D-REL2 miss (abs)", "G-CERT miss (abs)",
                            "G-CERT-M miss (abs)", "G-CERT false ref. (marg)",
                            "G-CERT-M miss (marg)", "Union false ref. (marg)"], body))
    # delta sweep: every relative gate at threshold = delta, marginal reading
    body = []
    for g in ("G-CERT", "G-CERT-M", "D-REL2", "D-REL1"):
        row = [g]
        for delta in (0.05, 0.10, 0.20):
            r = drow(disp_td, "marginal", "at_delta", g, delta)
            if r is None:
                row.append("n/a")
                continue
            row.append("TPR {} (n={}), FPR {} (n={})".format(pctf(r["tpr"]), r["oracle_costly"],
                                                             pctf(r["fpr"]), r["oracle_cheap"]))
            dtok = {0.05: "Five", 0.10: "Ten", 0.20: "Twenty"}[delta]
            for kind, ktok in (("tpr", "Tpr"), ("fpr", "Fpr")):
                if r[kind] is not None:
                    M.twin("nTwoDirectMarg{}AtDelta{}{}".format(GATE_TOKEN[g], ktok, dtok),
                           pct_tex(r[kind]), "Table 16 / delta sweep")
        body.append(row)
    md.append("\n### Delta sweep: each gate at threshold = delta (marginal reading, pricing truth)\n")
    md.append(md_table(["gate", "delta 0.05", "delta 0.10", "delta 0.20"], body))
    body = []
    for g in ("G-CERT", "G-CERT-M", "D-REL1", "D-REL2", "D-ABS", "G-CERT-M|D-REL2"):
        row = [g]
        for delta in (0.10, 0.20):
            r = drow(disp_td, "absolute", "published", g, delta)
            row.append("miss {} of {} costly, false ref. {} of {} cheap".format(
                "n/a" if r is None or r["tpr"] is None else pctf(1 - r["tpr"]),
                r["oracle_costly"] if r else 0,
                "n/a" if r is None or r["fpr"] is None else pctf(r["fpr"]),
                r["oracle_cheap"] if r else 0))
        body.append(row)
    md.append("\n### Dispositions at the frozen settings (absolute pricing truth, all classes)\n")
    md.append(md_table(["gate", "delta 0.10", "delta 0.20"], body))
    def pub_share(macro):
        v = M.published.get(macro)
        try:
            return float(v.replace("\\%", "").replace("%", "")) / 100.0
        except (AttributeError, ValueError):
            return None

    for truth_l, name, lab, mac in (
            ("absolute", "rule_miss", "D-REL2 miss", "nTwoDirectRelTwoMissRateTen"),
            ("absolute", "cert_miss", "G-CERT miss", "nTwoDirectCertMissRateTen"),
            ("absolute", "certm_miss", "G-CERT-M miss", "nTwoDirectCertMMissRateTen"),
            ("marginal", "cert_fr", "G-CERT false referral (marg)",
             "nTwoDirectMargCertFalseReferralRateTen")):
        w = wrow(wins_td, truth_l, 0.10)
        wr = wrow(wins_real, truth_l, 0.10)
        out["head"].append(("Table 16 pooled delta 0.10: " + lab + ", pricing truth",
                            pub_share(mac), None, None if w is None else w[name + "_rate"],
                            "share"))
        out["head"].append(("Table 16 pooled delta 0.10: " + lab + ", consequence truth",
                            pub_share(mac), None, None if wr is None else wr[name + "_rate"],
                            "share"))
    out["md"] = "\n".join(md)
    return out


def heldout_section(held_rows, pub_rows, cb, dg14, boot, n9g, M) -> dict:
    out = {"head": []}

    def attach(r):
        b = cb.get(r["item_id"])
        r["c_covered"] = bool(b and b.get("complete"))
        for k in ("c_lo", "c_hi", "c_mid", "n_lo", "n_hi", "c_opt_lower", "c_opt_upper"):
            r[k] = None
        if r["c_covered"]:
            r.update(c_lo=b["c_lo"], c_hi=b["c_hi"], c_mid=b["c_mid"], n_lo=b["n_lo"],
                     n_hi=b["n_hi"], c_opt_lower=b["opt_lower"], c_opt_upper=b["opt_upper"])
        return r

    rows = [attach(dict(r)) for r in held_rows if r["issuable"] and r["priced"]]
    blocked = [r for r in held_rows if r["issuable"] and not r["priced"]]
    disp = n9g.disposition(rows, boot, dg14, "c")
    body = []
    for g, gt in GATE_TOKEN.items():
        d = next((x for x in disp if x["gate"] == g and x["operating_point"] == "published"
                  and abs(x["delta"] - 0.20) < 1e-12), None)
        ug = n9g.under_over(rows, g, n9g.err_vs_g)
        uc = n9g.under_over(rows, g, n9g.err_vs_c)
        if d is None:
            continue
        M.twin("nNineHeldoutCDetect{}Twenty".format(gt), pct_tex(d["detect"]["rate"]), "Table 17")
        M.twin("nNineHeldoutCCheapRefer{}Twenty".format(gt), pct_tex(d["fr_cheap_v3"]["rate"]),
               "Table 17")
        M.twin("nNineHeldoutTwinRefer{}".format(gt), pct_tex(d["fr_twins"]["rate"]), "Table 17")
        M.twin("nNineHeldoutUnderG{}".format(gt), pct_tex(ug[0] / ug[2] if ug[2] else None),
               "Table 17")
        M.twin("nNineHeldoutUnderC{}".format(gt), pct_tex(uc[0] / uc[2] if uc[2] else None),
               "Table 17")
        body.append([g, "{} ({}/{})".format(pctf(d["detect"]["rate"]), d["detect"]["k"],
                                            d["detect"]["n"]),
                     "{} ({}/{})".format(pctf(d["fr_cheap_v3"]["rate"]), d["fr_cheap_v3"]["k"],
                                         d["fr_cheap_v3"]["n"]),
                     "{} ({}/{})".format(pctf(d["fr_twins"]["rate"]), d["fr_twins"]["k"],
                                         d["fr_twins"]["n"]),
                     "{} ({}/{})".format(pctf(ug[0] / ug[2] if ug[2] else None), ug[0], ug[2]),
                     "{} ({}/{})".format(pctf(uc[0] / uc[2] if uc[2] else None), uc[0], uc[2])])
        out["head"].append(("Table 17: {} detection of c-costly items".format(g), None, None,
                            d["detect"]["rate"], "share"))
        out["head"].append(("Table 17: {} referral of items within tau".format(g), None, None,
                            d["fr_cheap_v3"]["rate"], "share"))
    v3 = [r for r in rows if r["role"] == "V3"]
    M.twin("nNineHeldoutItems", group_int(len(v3)), "Table 17")
    costly = sum(1 for r in v3 if r["c_covered"] and r["c_lo"] > TAU)
    cheap = sum(1 for r in v3 if r["c_covered"] and r["c_hi"] <= TAU)
    md = ["Held-out items issuable and priced on K: {} V3 and {} twins ({} issuable items blocked "
          "before pricing on K). Decision-time c covered on {} V3 items; c-costly at tau {}, "
          "within tau {}.\n".format(len(v3), len(rows) - len(v3), len(blocked),
                                    sum(1 for r in v3 if r["c_covered"]), costly, cheap),
          md_table(["gate", "costly items referred", "items within tau referred",
                    "twins referred", "under-priced vs g_K", "under-priced vs c_K"], body)]
    # published V3: |m - c| at t_d
    pv = [attach(dict(r)) for r in pub_rows if r["primary_class"] == "V3" and r["issuable"]
          and r["priced"]]
    body = []
    for key, tok in (("p_G-CERT-M", "CertM"), ("p_D-REL2", "RelTwo")):
        c = n9g.closeness(pv, key)
        if c is None:
            continue
        w5 = c["within_0.05"]
        M.twin("nNinePub{}WithinFive".format(tok), pct_tex(w5["share_lo"]), "Section 5.2")
        M.twin("nNinePub{}DistMedian".format(tok), "{:.3f}".format(c["median_hi"]), "Section 5.2")
        body.append([key[2:], c["n"], "{} to {}".format(pctf(w5["share_lo"]), pctf(w5["share_hi"])),
                     "{:.3f} to {:.3f}".format(c["median_lo"], c["median_hi"])])
    md.append("\nPublished V3 items (issuable, priced on K): distance of the price to c_K.\n")
    md.append(md_table(["price", "n", "share within 0.05", "median |price - c_K|"], body))
    out["md"] = "\n".join(md)
    return out


def field_section(iss, M) -> dict:
    out = {"head": []}
    body = []
    groups = (("benign", "Benign"), ("V3", "VThree"), ("V4", "VFour"), ("other", "Other"))
    for cls, tok in groups:
        for sp, stok in (("field_changing", "Field"), ("sequencing_only", "Seq")):
            rs = [r for r in iss if r["split"] == sp and (r["primary_class"] == cls or (
                cls == "other" and r["primary_class"] not in ("benign", "V3", "V4")))]
            q = [r for r in rs if r["priced"]]
            ap = [r for r in q if r["p_G-CERT"] <= TAU]
            dm = [r["damage_if_applied"] for r in ap if r["damage_if_applied"] is not None]
            orig = [(r["obj_orig"] - r["anchor_lb_K"]) / max(r["anchor_lb_K"], FLOOR_BH)
                    for r in ap if r["obj_orig"] is not None and r["anchor_lb_K"] is not None]
            above = sum(1 for g in orig if g > TAU)
            # published reading on the same items
            qp = [r for r in rs if r["terminal_pub"] in ("applied_with_certificate", "blocked_qual")]
            app = [r for r in qp if r["gap_pub"] is not None and r["gap_pub"] <= TAU]
            dmp = [r["damage_if_applied_pub"] for r in app if r["damage_if_applied_pub"] is not None]
            origp = [(r["obj_orig_pub"] - r["anchor_lb_pub"]) / max(r["anchor_lb_pub"], FLOOR_BH)
                     for r in app if r["obj_orig_pub"] is not None]
            abovep = sum(1 for g in origp if g > TAU)
            pre = "nElevenFieldDirect{}{}".format(tok, stok)
            M.add(pre + "Qual", group_int(len(q)), exhibit="Table S10 (direct)")
            M.add(pre + "Applied", group_int(len(ap)), exhibit="Table S10 (direct)")
            M.add(pre + "DmgTwoCount", group_int(sum(1 for d in dm if d > 2.0)),
                  exhibit="Table S10 (direct)")
            M.add(pre + "DmgTenCount", group_int(sum(1 for d in dm if d > 10.0)),
                  exhibit="Table S10 (direct)")
            if sp == "field_changing":
                M.add(pre + "OrigAboveTau", group_int(above), exhibit="Table S10 (direct)")
            body.append([cls, sp, len(rs), len(q), len(ap), sum(1 for d in dm if d > 2.0),
                         sum(1 for d in dm if d > 10.0), numf(max(dm) if dm else None, 2),
                         above if sp == "field_changing" else "",
                         "{} / {} / {} / {}".format(len(qp), len(app),
                                                   sum(1 for d in dmp if d > 10.0),
                                                   abovep if sp == "field_changing" else "-")])
    md = ["Direct benchmark, issuable items. Applied = priced on K with G-CERT <= tau. Damage = "
          "realised original-field tardiness from t_d minus the published anchor (bh). g_orig on "
          "K = (original-field obj_K - LB_K of the unadjusted K)/max(., 1). The last column is "
          "the published (t = 0) reading on the same items: quality-reaching / applied / damage "
          "> 10 bh / g_orig above tau.\n",
          md_table(["class", "split", "items", "priced on K", "applied", "damage > 2 bh",
                    "damage > 10 bh", "max damage (bh)", "g_orig_K > tau", "t = 0 reading"],
                   body)]
    out["md"] = "\n".join(md)
    return out


def damage_section(iss, pub_rows, boot, M) -> dict:
    out = {"head": []}

    def applies(r, design, reading):
        if reading == "td":
            feas = r["terminal_feas"] == "applied_uncertified"
            pc, pm, p2 = r["p_G-CERT"], r["p_G-CERT-M"], r["p_D-REL2"]
            dmg = r["damage_if_applied"]
        else:
            feas = r["terminal_feas_pub"] == "applied_uncertified"
            pc, pm, p2 = r["gap_pub"], r["pm_pub"], r["p2_pub"]
            dmg = r["damage_if_applied_pub"]
        if not feas or dmg is None:
            return 0.0
        if design == "G-FEAS":
            return dmg
        if design == "G-CERT":
            return dmg if pc is not None and pc <= TAU else 0.0
        if design == "G-CERT-M":
            return dmg if pm is not None and pm <= TAU else 0.0
        if design == "D-REL2":
            return dmg if p2 is None or p2 <= DG14["D-REL2"] else 0.0
        if design == "G-CERT-M|D-REL2":
            ok = (pm is not None and pm <= TAU) and (p2 is None or p2 <= DG14["D-REL2"])
            return dmg if ok else 0.0
        raise ValueError(design)

    import numpy as np

    body = []
    for cls, tok in (("V3", "VThree"), ("benign", "Benign"), ("V4", "VFour"), ("all", "All")):
        rs = [r for r in iss if cls == "all" or r["primary_class"] == cls]
        row = [cls, len(rs)]
        for design, dtok in (("G-FEAS", "Feas"), ("G-CERT", "Cert"), ("G-CERT-M", "CertM"),
                             ("D-REL2", "RelTwo"), ("G-CERT-M|D-REL2", "Union")):
            vals = [applies(r, design, "td") for r in rs]
            valp = [applies(r, design, "pub") for r in rs]
            num = np.array(vals, dtype=float)
            den = np.ones(len(rs))
            ci_idx = np.array([boot.index[r["instance_id"]] for r in rs], dtype=int)
            import e1_delta_guard_replay as e1dg
            a_, b_ = e1dg.cluster_sums(num, den, ci_idx, boot.k)
            lo, hi = e1dg.bootstrap_ci(a_, b_, boot.idx) if len(rs) else (None, None)
            mean = float(num.mean()) if len(rs) else None
            meanp = float(np.mean(valp)) if len(rs) else None
            M.add("nElevenDamageDirect{}{}".format(tok, dtok), numf(mean, 2),
                  exhibit="Section 5.1 (direct)")
            M.add("nElevenDamageDirect{}{}Lo".format(tok, dtok), numf(lo, 2),
                  exhibit="Section 5.1 (direct)")
            M.add("nElevenDamageDirect{}{}Hi".format(tok, dtok), numf(hi, 2),
                  exhibit="Section 5.1 (direct)")
            M.add("nElevenDamageDirectPub{}{}".format(tok, dtok), numf(meanp, 2),
                  exhibit="Section 5.1 (direct, t = 0 on issuable)")
            row.append("{} [{}, {}] (t=0: {})".format(numf(mean, 2), numf(lo, 2), numf(hi, 2),
                                                     numf(meanp, 2)))
            if cls == "V3" and design in ("G-FEAS", "G-CERT"):
                out["head"].append(("5.1 direct V3 mean damage under {} (bh)".format(design),
                                    None, meanp, mean, "bh"))
        body.append(row)
    md = ["Mean realised damage per issuable instruction (bh, original fields, 95% cluster "
          "bootstrap over instances); a referred or refused proposal adds 0. D-REL2 at its DG14 "
          "setting on the G-FEAS base; t = 0 reading on the same items in parentheses (D-REL2 "
          "there uses the N2 price).\n",
          md_table(["class", "items", "G-FEAS", "G-CERT", "G-CERT-M", "D-REL2 (0.02)",
                    "G-CERT-M or D-REL2"], body)]
    out["md"] = "\n".join(md)
    return out


def info_section(priced, M) -> dict:
    out = {"head": []}
    body = []
    for cls, tok in (("V3", "VThree"), ("benign", "Benign"), ("all", "All")):
        rs = [r for r in priced if cls == "all" or r["primary_class"] == cls]
        ia, im, eb = [], [], []
        for r in rs:
            if r.get("real_covered") and r.get("real_g_lo") is not None:
                ia.append(r["p_G-CERT"] - 0.5 * (r["real_g_lo"] + r["real_g_hi"]))
            if r.get("real_covered_m") and r.get("real_m_lo") is not None:
                im.append(r["p_G-CERT-M"] - 0.5 * (r["real_m_lo"] + r["real_m_hi"]))
            if r["damage_if_applied"] is not None:
                eb.append(r["p_D-ABS"] - r["damage_if_applied"])
        for vals, nm in ((ia, "ErrAbs"), (im, "ErrMarg"), (eb, "ErrBh")):
            if vals:
                M.add("nElevenInfo{}{}Median".format(tok, nm), numf(median(vals), 3),
                      exhibit="information gap (replaces Table 20)")
                M.add("nElevenInfo{}{}PNinetyFive".format(tok, nm), numf(pctl(vals, 95), 3),
                      exhibit="information gap (replaces Table 20)")
        body.append([cls, len(rs), len(ia), numf(median(ia)), numf(pctl(ia, 95)),
                     numf(median(im)), numf(pctl(im, 95)), len(eb), numf(median(eb)),
                     numf(pctl(eb, 5)), numf(pctl(eb, 95))])
    md = ["Information gap: the price on K minus the realised cost of the same proposal on the "
          "full window (G-CERT against the realised absolute cost, G-CERT-M against the realised "
          "marginal cost, bracket midpoints), and the predicted added tardiness on K (D-ABS, bh) "
          "minus the realised damage on the original fields.\n",
          md_table(["class", "priced", "n (abs)", "median G-CERT - g_real", "p95",
                    "median G-CERT-M - m_real", "p95", "n (bh)", "median predicted - realised bh",
                    "p5", "p95"], body)]
    out["md"] = "\n".join(md)
    return out


def oracle_section(need, td_br, rel_rows, c_rows, M) -> dict:
    out = {"head": []}
    body = []
    for st, tok in [("all", "Pooled")] + list(STRATUM_TOKEN.items()):
        bs = [td_br[k] for k in need if k in td_br
              and (st == "all" or k[0].startswith(st))]
        if not bs:
            continue
        w = [b["width_rel"] for b in bs]
        proved = sum(1 for b in bs if b["proved_all"])
        M.twin("nTwoOracle{}Brackets".format(tok), group_int(len(bs)), "Table S7")
        M.twin("nTwoOracle{}Proved".format(tok), group_int(proved), "Table S7")
        M.twin("nTwoOracle{}ProvedShare".format(tok), pct_tex(proved / len(bs)), "Table S7")
        M.twin("nTwoOracle{}WidthPNinetyFive".format(tok), pct_tex(pctl(w, 95), 2), "Table S7")
        M.twin("nTwoOracle{}WidthMax".format(tok), pct_tex(max(w), 2), "Table S7")
        body.append([STRATUM_NAME.get(st, "Pooled"),
                     sum(1 for k in need if st == "all" or k[0].startswith(st)), len(bs), proved,
                     pctf(pctl(w, 50), 2), pctf(pctl(w, 95), 2), pctf(max(w), 2)])
    md = [md_table(["stratum", "boards needed", "bracketed", "proved", "width median",
                    "width p95", "width max"], body)]
    for name, rows in (("relaxed trade solves", list(rel_rows.values())),
                       ("constrained (c) solves", list(c_rows.values()))):
        solved = [r for r in rows if r["status"] not in ("CLOSED", "CLOSED_BY_LB2")]
        st = Counter(r["status"] for r in rows)
        walls = [r["wall_s"] for r in solved]
        sizes = defaultdict(list)
        for r in solved:
            n = r["n_orders"]
            b = ("<=150" if n <= 150 else "<=400" if n <= 400 else "<=700" if n <= 700
                 else "<=1500" if n <= 1500 else ">1500")
            sizes[b].append(r["wall_s"])
        scs = [r["solve_cpu_share"] for r in solved if r.get("solve_cpu_share") is not None]
        cs = [r["cpu_share"] for r in solved if r.get("cpu_share") is not None]
        fs = [r["foreign_share"] for r in solved if r.get("foreign_share") is not None]
        md.append("\n{}: {} rows, statuses {}; solved {} in {:.0f} s (median {} s, p95 {} s, "
                  "max {} s); cpu_share median {}, solve_cpu_share median {} (min {}), "
                  "foreign_share median {} (max {}). Wall by size: {}.".format(
                      name, len(rows), dict(st), len(solved), sum(walls), numf(median(walls), 1),
                      numf(pctl(walls, 95), 1), numf(max(walls) if walls else None, 1),
                      numf(median(cs), 2), numf(median(scs), 2), numf(min(scs) if scs else None, 2),
                      numf(median(fs), 3), numf(max(fs) if fs else None, 3),
                      ", ".join("{} n={} median {:.1f}s max {:.1f}s".format(
                          k, len(sizes[k]), median(sizes[k]), max(sizes[k]))
                          for k in ("<=150", "<=400", "<=700", "<=1500", ">1500") if sizes[k])))
        lim = [r for r in solved if r["status"] not in PROVED]
        if lim:
            fl = [r["foreign_share"] for r in lim if r.get("foreign_share") is not None]
            one = sum(1 for r in lim if r.get("solve_cpu_share") is not None
                      and r["solve_cpu_share"] < 0.26)
            md.append("Budget-limited rows (not proved): {}, smallest {} orders, foreign_share max "
                      "{}; {} of them used about one of the four workers for the whole budget "
                      "(solve_cpu_share about 0.25, CP-SAT still in its single-threaded presolve), "
                      "so their brackets are the relaxed lower bound against the ATC upper bound."
                      .format(len(lim), min(r["n_orders"] for r in lim),
                              numf(max(fl) if fl else None, 3), one))
    md.append("\ncpu_share is not the contention test for CP-SAT: its search workers idle in "
              "presolve and on small or nearly closed models, so an uncontended budget-limited "
              "solve reads 0.4 to 0.7 (oracle_v1 median solve_cpu_share 0.68 on proved rows; N9 "
              "0.41 to 0.43). The test is foreign_share, the busy CPU other processes took on "
              "cores 8-11 during the solve; a budget-limited row above 0.10 is invalid and "
              "solved again (at most twice).")
    out["md"] = "\n".join(md)
    return out


def n8_section(published, M) -> dict:
    keys = (("Agreement with the full-window disposition, absolute", "nEightAllAgreeAbs",
             "nEightAllAgreeAbsPlanned"),
            ("Agreement, marginal", "nEightAllAgreeMarg", "nEightAllAgreeMargPlanned"),
            ("Referred share, absolute", "nEightAllReferredAbs", "nEightAllReferredAbsPlanned"),
            ("Applied share, absolute", "nEightAllAppliedAbs", "nEightAllAppliedAbsPlanned"),
            ("Refused share, absolute", "nEightAllRefusedAbs", "nEightAllRefusedAbsPlanned"),
            ("Median decision instant (bh)", "nEightAllDecisionMedian",
             "nEightAllDecisionPlannedMedian"),
            ("Median known orders", "nEightAllKnownMedian", "nEightAllKnownPlannedMedian"))
    body = [[lab, published.get(a, "n/a"), published.get(b, "n/a")] for lab, a, b in keys]
    md = ["Carried over from N8 (analysis/N8_macros.tex, no new compute): the corrective-only "
          "reading against the planned-known reading N11 takes as primary.\n",
          md_table(["quantity", "corrective-only (N8 primary)", "planned-known (N11 primary)"],
                   body)]
    return {"md": "\n".join(md), "head": []}


def changes_section(S, published, M) -> dict:
    heads = []
    for k, sec in S.items():
        if isinstance(sec, dict):
            heads.extend(sec.get("head", []))
    body = []
    changes = []
    for lab, pub_all, pub_iss, td, kind in heads:
        if td is None:
            continue
        ref = pub_all if pub_all is not None else pub_iss
        delta = None if ref is None else td - ref
        flag = ""
        if kind == "signed" and ref is not None and (ref > 1e-9 > td or ref < -1e-9 < td
                                                     or (abs(ref) <= 1e-9 < abs(td))):
            flag = "sign"
        fmtv = (lambda v: pctf(v)) if kind == "share" else (lambda v: numf(v, 3)) \
            if kind in ("signed", "bh") else (lambda v: "n/a" if v is None else str(v))
        body.append([lab, fmtv(pub_all), fmtv(pub_iss), fmtv(td),
                     "" if delta is None else (pctf(delta) if kind == "share" else numf(delta, 3)),
                     flag])
        if delta is not None:
            changes.append((abs(delta) * (100 if kind == "share" else 1), lab, ref, td, kind))
    # gate order changes (Table 14 under share, absolute and marginal)
    order_notes = []
    for lab in ("absolute", "marginal"):
        hs = [(h[0].split(": ")[1].replace(" under share", ""), h[1], h[3]) for h in heads
              if h[0].startswith("Table 14 {}:".format(lab)) and h[0].endswith("under share")]
        if hs and all(h[1] is not None and h[2] is not None for h in hs):
            o_pub = ["{} ({})".format(h[0], pctf(h[1])) for h in sorted(hs, key=lambda h: (h[1], h[0]))]
            o_td = ["{} ({})".format(h[0], pctf(h[2])) for h in sorted(hs, key=lambda h: (h[2], h[0]))]
            n_pub = [h[0] for h in sorted(hs, key=lambda h: (h[1], h[0]))]
            n_td = [h[0] for h in sorted(hs, key=lambda h: (h[2], h[0]))]
            if n_pub != n_td:
                order_notes.append("Table 14 {} under-share order of the gates changes from {} "
                                   "(t = 0) to {} (t_d).".format(lab, " < ".join(o_pub),
                                                                " < ".join(o_td)))
    changes.sort(reverse=True)
    md = ["Each headline number of the twins: the published reading (t = 0, all items), the "
          "same reading on the issuable items, and the decision-time reading. 'sign' marks a "
          "signed quantity whose sign changes.\n",
          md_table(["quantity", "t = 0, all", "t = 0, issuable", "t_d", "t_d - t = 0", "flag"],
                   body)]
    if order_notes:
        md.append("\n" + "\n".join("- " + x for x in order_notes))
    return {"md": "\n".join(md), "head": [], "_largest": changes[:8], "_order": order_notes}


def summary_md(S, status, covered, n_need, br_source, rep, n_persist, items) -> str:
    cen = json.loads((OUT / "census_assertions.json").read_text())
    omn = json.loads((OUT / "omni_assertions.json").read_text())
    om_meta = json.loads((OUT / "omni_meta.json").read_text())
    cmeta = json.loads((OUT / "census_meta.json").read_text())
    orm = json.loads((ORACLE_OUT / "run_meta.json").read_text()) \
        if (ORACLE_OUT / "run_meta.json").is_file() else {}
    sc = json.loads((ORACLE_OUT / "selfcheck_summary.json").read_text()) \
        if (ORACLE_OUT / "selfcheck_summary.json").is_file() else {}
    L = ["# N11 Stage 1: the decision-time reading of the direct benchmark ({})".format(VERSION),
         "",
         "Generated by `code/scripts/n11_decision_time.py analyse`. Coverage status: **{}** "
         "({} of {} needed decision-time boards bracketed; truth source: {}). Every number "
         "below is also a macro in `analysis/N11_macros.tex` (map: "
         "`analysis/N11_macro_map.csv`).".format(status, covered, n_need, br_source), "",
         "## What was computed", "",
         "- Population: the 2,000 published items (canonical proposal per class) and the 440 "
         "held-out items (gold translation). Issuable: t_known <= t_start over the instruction's "
         "own referenced ids (closed rule, primary); strict rule as a subset sensitivity.",
         "- Decision instant t_d = t_known; K, kf, the dispatch from t_d and LB_K are N8's "
         "planned-known functions; every design priced on K; the D-REL2 reference dispatched on "
         "K with the installed fields and no constraining operation.",
         "- Ground truth: pricing tables against the decision-time oracle on the relaxed known "
         "board (per trade max(LB2 at t_d, CP-SAT bound with availability) to min(ATC of the "
         "board, executed K-schedules, re-timed incumbent), running work as availability plus a "
         "constant); consequence tables against the realised full-window run from t_d, "
         "original fields (adjusted fields recorded too).",
         "- Decision-time c: the instruction's constraints on the board, availability-aware, "
         "N9's conservative bracket, on published V3, their twins and the held-out set.", "",
         "## Assertions", "",
         "- census: {} ({} checks; groups {}).".format(cen["status"], cen["n_checks"],
                                                        cen["checks_by_group"]),
         "- omni: {} ({} checks; groups {}); E1 {} rows ({} model refusals kept), N3 {} rows; "
         "A10 rebuilt {} oracle_v1 trade rows, {} bit-exact; DG17 cells exact {}; N10 rows {}."
         .format(omn["status"], omn["n_checks"], omn["checks_by_group"], om_meta["e1_rows"],
                 om_meta["e1_model_refused"], om_meta["n3_rows"], om_meta["a10_trade_rows"],
                 om_meta["a10_bit_exact"], om_meta["dg17_cells_exact"], om_meta["n10_rows"]),
         "- oracle A11 self-check: {}; compared {}; max deviation {}.".format(
             orm.get("a11", "not run"), sc.get("compared"), sc.get("max_dev")),
         "- analyse (A9 oracle part, A13, A14): {} ({} checks); persistent invalid rows kept: {}."
         .format(rep["status"], rep["n_checks"], n_persist),
         "- census wall {:.0f} s on cores {}; omni wall {:.0f} s; oracle wall {}.".format(
             cmeta["wall_s"], cmeta["cores"], om_meta["wall_s"],
             "n/a" if not orm.get("wall_s") else "{:.0f} s ({})".format(orm["wall_s"],
                                                                         orm.get("walls"))),
         ""]
    for key, title in (("census", "Issuability census"),
                       ("direct", "Table 10 twin: the gate measured directly at t_d"),
                       ("pricing", "Table 14 twin: pricing error against the decision-time oracle"),
                       ("refgap", "Table 15 twin: the anchor gap at t_d"),
                       ("decision", "Table 16 twin: miss and false referral, two truths"),
                       ("heldout", "Table 17 twin: held-out items against decision-time c"),
                       ("field", "Table S10 twin (direct benchmark): field-changing proposals"),
                       ("damage", "Section 5.1 twin (direct benchmark): realised damage"),
                       ("info", "Information gap (replaces Table 20)"),
                       ("oracle", "Table S7 twin and the solve-time profile"),
                       ("n8", "Planned-known against corrective-only (carried over from N8)"),
                       ("changes", "What changed against the published reading")):
        L += ["## " + title, "", S[key]["md"], ""]
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- #
# Entry point                                                                  #
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("census", "omni", "oracle", "analyse", "e2e", "analyse2"):
        p = sub.add_parser(name)
        p.add_argument("--cores", default="8-9" if name != "oracle" else "8-11")
        p.add_argument("--workers", type=int, default=2 if name != "oracle" else 4)
        p.add_argument("--instances", default="", help="smoke: comma-separated instance ids")
        if name == "oracle":
            p.add_argument("--budget", type=float, default=BUDGET_S)
            p.add_argument("--phase", default="all", choices=("all", "selfcheck", "relaxed", "c"))
            p.add_argument("--limit", type=int, default=0)
            p.add_argument("--extra-inputs", default="",
                           help="comma-separated folders whose relaxed_inputs.jsonl and "
                                "boards.jsonl are bracketed too (Stage 2)")
        if name in ("census", "analyse"):
            p.add_argument("--reading", default="primary", choices=READINGS)
    args = ap.parse_args(argv)
    args.cores_t = parse_cores(args.cores)
    if set(args.cores_t) & FORBIDDEN_CORES:
        raise SystemExit("REFUSING TO RUN: cores {} are not this project's".format(args.cores_t))
    if args.cmd in ("census", "omni", "e2e") and set(args.cores_t) - set(DET_CORES) and not os.environ.get("CERTIGATE_ANY_CORES"):
        raise SystemExit("REFUSING TO RUN: deterministic stages run on cores 8-9 only")
    if args.cmd == "oracle" and tuple(args.cores_t) != ORACLE_CORES and not os.environ.get("CERTIGATE_ANY_CORES"):
        raise SystemExit("REFUSING TO RUN: the oracle runs on cores 8-11 exactly")
    if args.workers > len(args.cores_t):
        raise SystemExit("REFUSING TO RUN: {} workers on {} cores".format(args.workers,
                                                                         len(args.cores_t)))
    fn = {"census": cmd_census, "omni": globals().get("cmd_omni"),
          "oracle": globals().get("cmd_oracle"), "analyse": globals().get("cmd_analyse"),
          "e2e": globals().get("cmd_e2e"), "analyse2": globals().get("cmd_analyse2")}[args.cmd]
    return fn(args)


if __name__ == "__main__":
    sys.exit(main())
