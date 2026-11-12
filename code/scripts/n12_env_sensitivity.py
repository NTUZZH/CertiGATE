#!/usr/bin/env python
"""N12: gate sensitivity to the environment's derived settings (Stage 4 of the N11 campaign).

QUESTION
--------
Two settings of the benchmark environment are derived, not observed: the
service-level windows (due = release + SLA[priority]) and the crew sizes per
trade.  N12 asks whether the gate designs behave as the paper says when those
two settings move.  Four perturbed environments and the calibrated one:

    cal       windows x1.0, crews x1.0  (identity; must reproduce the published reading)
    win050    windows x0.5  (due = release + 0.5 SLA[p] on every order)
    win150    windows x1.5
    crew075   crews x0.75   (max(1, round(n x 0.75)) technicians per trade)
    crew125   crews x1.25

The design is the pre-specified design; the run
mechanics are those of the pre-specified design; the
design facts are the pre-specified design, Section 9.

DERIVED INSTANCES
-----------------
An environment's instance is built in memory from the manifest-verified
instances_v10 snapshot file (resolved through ``suite_gate.instance_path``);
nothing is ever written into the snapshot tree.  Windows x f: every order's
due date is round(release + f * SLA_BH[priority], 4), the instance builder's
own storage convention (fmwos/instances.py), and ``l1adapter.apply.SLA_BH``
is rebound to the scaled dict in every process, so ``set_priority`` and
``reassign_window`` restart the scaled clock; ``fmwos.timeaxis.SLA_BH`` is
rebound in memory too, so the forecast's sampled orders carry the scaled
windows.  Crews x f: max(1, int(round(n * f))) technicians per trade, trades
in sorted order, renumbered T0, T1, ... (fmwos/generator.py:_technicians).
At f = 1 both transforms are the identity: the derived instance serialised
as the snapshot files are (compact JSON, key order kept) has the snapshot
file's manifest SHA-256 (asserted).  Every derived instance's file-format and
canonical SHA-256 go to results/n12_env/manifest_n12.json.

WHAT IS COMPUTED PER ENVIRONMENT (direct benchmark: the canonical proposal of
every published suite item; labels and thresholds frozen at the published
settings: tau = 0.20, D-REL1 0.02, D-REL2 0.02, D-ABS 0.8119)
-----------------------------------------------------------------------------
census    deterministic, cores 8-11, 4 processes: N11's ``census_instance``
          on the derived instances (issuability, the full-window reading at
          t = 0, the decision-time reading on K at t_d = t_known, the realised
          full-window run from t_d, the decision-time boards and their open
          trades), plus the full-window field tuples of every proposal.
oracle    CP-SAT on cores 8-11 EXCLUSIVELY: (1) the full-window oracle
          bracket of every needed relaxed instance (60 baselines and every
          proposal's field fingerprint), oracle_v1's recipe unchanged
          (code/scripts/oracle_cost.py: per trade, LB2 against the Y1 model on
          the rounded-down grid, 60 s, 4 workers, ATC warm start); (2) the
          decision-time oracle on K for the open known-board trades
          (code/l1oracle/cpsat_avail.py through N11's ``solve_relaxed``).
forecast  deterministic, cores 8-11, 4 processes: N11 Stage 3's forecast
          reading F2 (S = 20 from Stage 3's smoke decision, top-up to 50 near
          a threshold), ``forecast_instance`` unchanged.
analyse   the full-window reading (N2's tables 14, 15, 16 and the Table 10
          referral shares), the decision-time reading (the same against the
          decision-time oracle on K, and the realised consequence on the
          original fields), and the forecast reading F2 (referral shares,
          false referrals, predicted-damage accuracy per design).
report    analysis/N12_macros.tex, N12_rows.csv, N12_summary.md over every
          environment analysed.

ASSERTIONS (run-fatal; a failure writes the failure list and exits non-zero)
---------------------------------------------------------------------------
E1  manifest: every source file's SHA-256 equals the instance manifest; every
    derived instance's hashes are recorded; at f = 1 the derived file-format
    hash equals the manifest hash.
E2  due dates: due = round(release + f * SLA[p], 4) on every order; every other
    order field unchanged.
E3  crews: technicians per trade = max(1, int(round(n * f))), ids T0..T(k-1)
    in sorted trade order; trades unchanged.
E4  the scaled clock: in every worker, apply.SLA_BH and timeaxis.SLA_BH equal
    f * SLA, and set_priority / reassign_window on a probe order install
    release + f * SLA.
E5  LB <= obj everywhere: full-window certificate bound and every board's LB2
    at most every executed objective; oracle lower <= upper on every bracket;
    every executed objective at or above its bracket's lower end; LB_K <= obj_K
    on every decision-time and every sampled forecast board.
E6  identity (cal): the census reproduces N11's primary census rows and boards
    exactly (and N11's A5-A8 battery against DG1, N2, N8, N9 and the anchors);
    the full-window prices reproduce N2_rows_direct.csv; the full-window
    brackets reproduce oracle_v1's (per-trade LB2 and ATC bit-exact, brackets
    equal); the decision-time brackets reproduce N11's; the forecast F2 prices
    reproduce Stage 3's exactly; the analysed headline cells reproduce N2's,
    N11's and N11 Stage 3's published cells.
E7  N11's structural groups on every environment: A2 (trajectory and board site
    seed invariance), A3 (issuable items name no completed, running or unknown
    order), A7 (no-proposal realised run equals the environment's anchor), A8
    (realised run at t_d = 0 equals the full window), A9, A12; Stage 3's AF0
    (S = 0 reproduces the census), AF2, AF3, AF6, AF8, AF9.
E8  every solve row carries the timing record (affinity, threads, load average,
    cpu_share, solve_cpu_share, foreign_share); foreign_share > 0.10 on a
    budget-limited solve invalidates the row (re-solved at most twice).
E9  coverage: every needed full-window and decision-time bracket is on disk.

Version: l1-n12-env-sensitivity-1
"""

from __future__ import annotations

import os
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
# oracle_cost restores OMP/MKL caps to L1_N1_WORKERS when it imports the solver;
# the design caps every thread pool at 1 (CP-SAT's workers are its own threads).
os.environ["L1_N1_WORKERS"] = "1"

import n11_decision_time as D  # noqa: E402  (sets L1_INSTANCE_ROOT to the snapshot)

import argparse  # noqa: E402
import copy  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import platform  # noqa: E402
import socket  # noqa: E402
import time  # noqa: E402
from collections import Counter, OrderedDict, defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

VERSION = "l1-n12-env-sensitivity-1"
ROOT = D.ROOT
RESULTS = D.RESULTS
ANALYSIS = D.ANALYSIS
OUT = RESULTS / "n12_env"
N11F = RESULTS / "n11_forecast"
SNAP = Path(D.SNAPSHOT_ROOT).resolve()
CORES = (8, 9, 10, 11)
WORKERS = 4
BUDGET_S = 60.0
MAX_RESOLVES = 2
FOREIGN_SHARE_MAX = 0.10
TOL = 1e-6
EXACT = 1e-9
STOP_RULE_S = 3 * 3600.0

ENVS = OrderedDict([
    ("cal", {"window": 1.0, "crew": 1.0, "token": "Cal", "label": "calibrated"}),
    ("win050", {"window": 0.5, "crew": 1.0, "token": "WinHalf", "label": "windows x0.5"}),
    ("win150", {"window": 1.5, "crew": 1.0, "token": "WinOneHalf", "label": "windows x1.5"}),
    ("crew075", {"window": 1.0, "crew": 0.75, "token": "CrewThreeQuarters",
                 "label": "crews x0.75"}),
    ("crew125", {"window": 1.0, "crew": 1.25, "token": "CrewFiveQuarters",
                 "label": "crews x1.25"}),
])
PERTURBED = ("win050", "win150", "crew075", "crew125")
DESIGNS = ("G-CERT", "G-CERT-M", "D-REL1", "D-REL2", "D-ABS")
UNIONS = ("G-CERT|D-REL2", "G-CERT-M|D-REL2")
SETTINGS = OrderedDict([("G-CERT", D.TAU), ("G-CERT-M", D.TAU), ("D-REL1", D.DG14["D-REL1"]),
                        ("D-REL2", D.DG14["D-REL2"]), ("D-ABS", D.DG14["D-ABS"])])
DG14 = dict(D.DG14)


# --------------------------------------------------------------------------- #
# Environment: derived instances and the scaled clock                         #
# --------------------------------------------------------------------------- #
_STATE = {"env": None}
_ORIG_LOAD = D.load_instance
_FILE_SHA: dict = {}
_MANIFEST: dict = {}


def env_dir(name) -> Path:
    return OUT / name


def stage_dir(name, stage, smoke=False) -> Path:
    """results/n12_env/<env>/<stage>, or .../<env>/smoke/<stage> for a smoke run."""
    return (OUT / name / "smoke" / stage) if smoke else (OUT / name / stage)


def manifest_files() -> dict:
    """rel path -> SHA-256 of the 60 instances the suite replays (suite_gate's manifest)."""
    if not _MANIFEST:
        import suite_gate as sg
        _MANIFEST.update(sg.instance_manifest().get("files", {}))
    return _MANIFEST


def base_sla() -> dict:
    """The environment's own SLA windows (l1adapter._fmwos copies timeaxis at import)."""
    from l1adapter import _fmwos
    return {int(k): float(v) for k, v in _fmwos.SLA_BH.items()}


def scaled_sla(fw) -> dict:
    return {p: float(fw) * v for p, v in base_sla().items()}


def file_sha(inst) -> str:
    """SHA-256 of the instance serialised as the snapshot files are (compact, key order kept)."""
    return hashlib.sha256(json.dumps(inst, separators=(",", ":")).encode("utf-8")).hexdigest()


def canon_sha(inst) -> str:
    return hashlib.sha256(json.dumps(inst, sort_keys=True, separators=(",", ":"))
                          .encode("utf-8")).hexdigest()


def crew_target(n, fc) -> int:
    """Y1's convention (fmwos/generator.py:_technicians): max(1, round(n x f)), half to even."""
    return max(1, int(round(n * float(fc))))


def derive(inst, env) -> dict:
    """The environment's instance: due = round(release + f_w SLA[p], 4); crews max(1, round(n f_c))."""
    sla = scaled_sla(env["window"])
    out = dict(inst)                      # key order of the snapshot file kept
    out["meta"] = dict(inst["meta"])
    wos = []
    for wo in inst["work_orders"]:
        w = dict(wo)
        w["due_bh"] = round(float(wo["release_bh"]) + sla[int(wo["priority"])], 4)
        wos.append(w)
    n = Counter(t["trade"] for t in inst["technicians"])
    techs, tid = [], 0
    for tr in sorted(n):
        for _ in range(crew_target(n[tr], env["crew"])):
            techs.append({"id": "T{}".format(tid), "trade": tr})
            tid += 1
    out["technicians"] = techs
    out["work_orders"] = wos
    return out


def source_rel(path) -> str:
    p = Path(path).resolve()
    return str(p.relative_to(SNAP))


def env_load_instance(path) -> dict:
    """N11's loader (snapshot-only), then the environment's transform on the 60 manifest files."""
    raw = _ORIG_LOAD(path)
    try:
        rel = source_rel(path)
    except ValueError:
        return raw
    man = manifest_files()
    if rel not in man:
        return raw                          # e.g. the recorded forecast's pool windows
    if rel not in _FILE_SHA:
        _FILE_SHA[rel] = D.sha256_file(path)
    if _FILE_SHA[rel] != man[rel]:
        raise SystemExit("E1 FAILURE: {} does not carry its manifest hash".format(rel))
    name = _STATE["env"]
    if name is None:
        raise SystemExit("REFUSING TO LOAD {}: no environment is active".format(rel))
    return derive(raw, ENVS[name])


def activate(name) -> None:
    """Bind the environment in this process (workers fork after this and inherit it)."""
    from l1adapter import _fmwos
    from l1adapter import apply as apply_mod

    env = ENVS[name]
    sla = scaled_sla(env["window"])
    apply_mod.SLA_BH = dict(sla)
    _fmwos.timeaxis.SLA_BH = dict(sla)
    D.load_instance = env_load_instance
    _STATE["env"] = name


def sla_probe(inst, name) -> dict:
    """E4 inside a worker: the scaled clock is bound and set_priority/reassign_window use it."""
    from l1adapter import _fmwos
    from l1adapter import apply as apply_mod
    from l1adapter.ops import parse_operations

    want = scaled_sla(ENVS[name]["window"])
    out = {"apply_sla": dict(apply_mod.SLA_BH) == want,
           "timeaxis_sla": {int(k): float(v) for k, v in _fmwos.timeaxis.SLA_BH.items()} == want,
           "set_priority": True, "reassign_window": True}
    wo = inst["work_orders"][0]
    new_c = 1 if int(wo["priority"]) != 1 else 2
    typed = parse_operations({"operations": [
        {"op": "set_priority", "order_id": wo["id"], "priority_class": new_c}]})
    adj = apply_mod.apply_operations(inst, typed)
    got = [w for w in adj.instance["work_orders"] if w["id"] == wo["id"]][0]
    out["set_priority"] = got["due_bh"] == round(float(wo["release_bh"]) + want[new_c], 4)
    typed = parse_operations({"operations": [
        {"op": "reassign_window", "order_id": wo["id"], "release_shift_bh": 1.5}]})
    adj = apply_mod.apply_operations(inst, typed)
    got = [w for w in adj.instance["work_orders"] if w["id"] == wo["id"]][0]
    rel = round(max(0.0, float(wo["release_bh"]) + 1.5), 4)
    out["reassign_window"] = got["due_bh"] == round(rel + want[int(wo["priority"])], 4)
    out["ok"] = all(v for k, v in out.items() if k != "ok")
    return out


def check_derivation(check, src, der, env, rel) -> dict:
    """E1-E3 for one instance; returns its manifest record."""
    sla = scaled_sla(env["window"])
    man = manifest_files()
    check.true("E1", "source of {} carries its manifest hash".format(rel),
               D.sha256_file(SNAP / rel) == man[rel])
    so = {w["id"]: w for w in src["work_orders"]}
    check.true("E2", "same orders in {}".format(rel),
               [w["id"] for w in der["work_orders"]] == [w["id"] for w in src["work_orders"]])
    n_bad, n_other = 0, 0
    for w in der["work_orders"]:
        s = so[w["id"]]
        if w["due_bh"] != round(float(w["release_bh"]) + sla[int(w["priority"])], 4):
            n_bad += 1
        if any(w[k] != s[k] for k in s if k != "due_bh") or set(w) != set(s):
            n_other += 1
    check.true("E2", "due = release + f SLA on every order of {}".format(rel), n_bad == 0, n_bad)
    check.true("E2", "no other order field changes in {}".format(rel), n_other == 0, n_other)
    n_src = Counter(t["trade"] for t in src["technicians"])
    n_der = Counter(t["trade"] for t in der["technicians"])
    bad = [tr for tr in n_src if n_der.get(tr, 0) != crew_target(n_src[tr], env["crew"])]
    check.true("E3", "crew per trade = max(1, round(n f)) in {}".format(rel), not bad, bad[:5])
    check.true("E3", "no trade gained or lost in {}".format(rel), set(n_der) == set(n_src))
    check.true("E3", "technicians renumbered T0.. in sorted trade order in {}".format(rel),
               [t["id"] for t in der["technicians"]] == ["T{}".format(i) for i in
                                                         range(len(der["technicians"]))]
               and [t["trade"] for t in der["technicians"]] ==
               sorted(t["trade"] for t in der["technicians"]))
    check.true("E3", "trades list unchanged in {}".format(rel), der.get("trades") == src.get("trades"))
    check.true("E2", "meta unchanged in {}".format(rel), der["meta"] == src["meta"])
    rec = OrderedDict(source=rel, source_sha256=man[rel], derived_file_sha256=file_sha(der),
                      derived_canonical_sha256=canon_sha(der), n_orders=len(der["work_orders"]),
                      n_technicians=len(der["technicians"]),
                      n_technicians_source=len(src["technicians"]),
                      n_due_changed=sum(1 for w in der["work_orders"]
                                        if w["due_bh"] != so[w["id"]]["due_bh"]))
    if env["window"] == 1.0 and env["crew"] == 1.0:
        check.true("E1", "identity transform reproduces the manifest hash of {}".format(rel),
                   rec["derived_file_sha256"] == man[rel], rec["derived_file_sha256"][:16])
    return rec


def write_manifest(name, recs) -> None:
    path = OUT / "manifest_n12.json"
    cur = json.loads(path.read_text()) if path.is_file() else {"version": VERSION, "envs": {}}
    cur["envs"][name] = {"settings": {k: ENVS[name][k] for k in ("window", "crew")},
                         "sla_bh": {str(k): v for k, v in scaled_sla(ENVS[name]["window"]).items()},
                         "written": D.now_iso(), "instances": recs}
    D.write_json(path, cur)


# --------------------------------------------------------------------------- #
# Small helpers                                                                #
# --------------------------------------------------------------------------- #
def pin(cores=CORES) -> None:
    D.pin_cores(cores)
    D.cap_threads(1)
    if os.environ.get("OMP_NUM_THREADS") != "1" or os.environ.get("MKL_NUM_THREADS") != "1":
        raise SystemExit("REFUSING TO RUN: thread caps are not 1")


def stage_gate(name, *stages, smoke=False) -> dict:
    """Refuse unless every named stage of ``name`` passed and its outputs are unchanged."""
    out = {}
    for st in stages:
        p = stage_dir(name, st, smoke) / "assertions.json"
        if not p.is_file():
            raise SystemExit("REFUSING TO RUN: {} is missing".format(p))
        rep = json.loads(p.read_text())
        if rep.get("status") != "PASS":
            raise SystemExit("REFUSING TO RUN: {} says {}".format(p, rep.get("status")))
        if bool(rep.get("smoke")) != bool(smoke):
            raise SystemExit("REFUSING TO RUN: {} is {} a smoke output".format(
                p, "not" if smoke else ""))
        for fname, digest in (rep.get("outputs") or {}).items():
            if D.sha256_file(p.parent / fname) != digest:
                raise SystemExit("REFUSING TO RUN: {} changed since {}".format(fname, st))
        out[st] = {"n_checks": rep.get("n_checks"), "finished": rep.get("finished")}
    return out


def outputs_of(d) -> dict:
    return {p.name: D.sha256_file(p) for p in sorted(Path(d).glob("*.jsonl"))}


def code_hashes() -> dict:
    files = [Path(__file__), Path(D.__file__), SCRIPTS_DIR + "/n11_forecast.py",
             SCRIPTS_DIR + "/oracle_cost.py", SCRIPTS_DIR + "/n2_pricing.py",
             SCRIPTS_DIR + "/n8_causal.py", D.CODE / "l1oracle" / "cpsat_avail.py",
             D.CODE / "l1guard" / "lb2.py", D.CODE / "l1guard" / "guard.py",
             D.CODE / "l1adapter" / "apply.py", D.CODE / "l1adapter" / "dispatch.py",
             D.CODE / "l1adapter" / "evaluate.py", D.CODE / "l1adapter" / "_fmwos.py",
             Path(((os.environ.get("L1_Y1_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "PaperY-FMScheduling")) + "/src/fmwos/cpsat.py"))]
    return {str(Path(p).name): D.sha256_file(p) for p in files}


def load_suite_items(check):
    pub_rows = D.load_published(check)
    return OrderedDict((r["item_id"], r) for r in pub_rows)


def instance_paths(pub) -> OrderedDict:
    out = OrderedDict()
    for it in pub.values():
        iid = it["instance"]["instance_id"]
        if iid not in out:
            out[iid] = D.instance_path(it)
    return out


def strata_of(pub) -> dict:
    return {it["instance"]["instance_id"]: it["instance"]["stratum"] for it in pub.values()}


# --------------------------------------------------------------------------- #
# Stage: census                                                                #
# --------------------------------------------------------------------------- #
def census_worker(ti) -> dict:
    """N11's census of one instance in the active environment, plus the full-window tuples."""
    from l1adapter import apply as apply_mod
    from l1adapter import dispatch as dispatch_mod

    res = D.census_instance(ti)
    task = D._TASKS[ti]
    inst = D.load_instance(task["path"])
    res["probe"] = sla_probe(inst, _STATE["env"])
    baseline = dispatch_mod.dispatch_baseline(inst, "atc", 0)
    by = {r["item_id"]: r for r in res["items"]}
    res["om_tuples"] = {}
    res["om_tuples_bad"] = []
    for it in task["items"]:
        row = by[it["item_id"]]
        if row["om_fp"] is None:
            continue
        adj = apply_mod.apply_proposal(inst, {"operations": it["ops"]}, frozen_seed=it["seed"],
                                       baseline_schedule=baseline, strict_schema=True)
        tl = D.changed_tuples(adj)
        if D.fp_of(tl) != row["om_fp"]:
            res["om_tuples_bad"].append(it["item_id"])
        res["om_tuples"][it["item_id"]] = [list(t) for t in tl]
    res["inst_file_sha"] = file_sha(inst)
    return res


def postprocess_items(items, pub) -> None:
    for r in items:
        it = pub[r["item_id"]]
        r["primary_class"] = it["primary_class"]
        r["subclass"] = it["subclass"]
        r["stratum"] = it["instance"]["stratum"]
        r["instance_id"] = it["instance"]["instance_id"]
        r["twin_id"] = it.get("twin_id")
        r["quality_visible"] = bool(it.get("quality_visible_candidate"))
        r["register"] = it.get("register")
        ops = D.canonical_ops(it)
        r["n_ops"] = len(ops)
        r["op_types"] = "|".join(sorted({o.get("op", "?") for o in ops if isinstance(o, dict)}))
        r["split"] = D.op_split(ops)
        r["c_role"] = None
        r["frozen_seed"] = r.pop("fk")


def env_census_checks(check, items, boards, seeds, anchor_omni, probes, bad_tuples) -> None:
    """N11's environment-agnostic groups (A2, A3, A7, A8, A9, A12) and E4, E5."""
    for iid, pr in probes.items():
        check.true("E4", "scaled clock bound in the worker of {}".format(iid), pr["ok"], pr)
    check.true("E5", "full-window field tuples reproduce the census fingerprint", not bad_tuples,
               bad_tuples[:5])
    for (iid, fk), v in seeds.items():
        check.true("A2", "trajectory starts and ends equal the plain ATC on {} [{}]".format(iid, fk),
                   v["traj_times_equal"])
    for b in boards:
        for s in b["seeds"]:
            check.true("A2", "board site of {} t_d={} is seed-invariant ({})".format(
                b["iid"], b["t_d"], s["fk"]),
                s["mult_equal"] and s["running_equal"] and s["known_equal"])
    plain = {iid: v for (iid, fk), v in anchor_omni.items() if fk == ""}
    for (iid, fk), v in anchor_omni.items():
        check.true("E5", "anchor LB <= obj on {} [{}]".format(iid, fk),
                   v["lb"] is not None and v["obj"] is not None and v["lb"] <= v["obj"] + TOL)
        p = plain.get(iid)
        if p is not None and fk:
            check.close("E5", "frozen-set anchor equals the plain one on {} [{}]".format(iid, fk),
                        v["obj"], p["obj"], EXACT)
            check.close("E5", "frozen-set anchor gap equals the plain one on {} [{}]".format(
                iid, fk), v["gap"], p["gap"], EXACT)
    for r in items:
        if r["issuable"]:
            check.true("A3", "issuable item names no completed or running order: " + r["item_id"],
                       not r["ref_completed"] and not r["ref_running"])
            check.true("A3", "issuable item names no order unknown at t_d: " + r["item_id"],
                       not r["ref_unknown"])
        a = anchor_omni[(r["instance_id"], r["frozen_seed"])]
        check.close("A7", "no-proposal realised run equals the anchor on " + r["item_id"],
                    r["rw0_obj_orig"], a["obj_orig"], TOL)
        check.close("A7", "no-proposal realised run (adjusted) equals the anchor on "
                    + r["item_id"], r["rw0_obj"], a["obj"], TOL)
        if r["om_lb"] is not None and r["om_obj"] is not None:
            check.true("E5", "full-window LB <= obj on " + r["item_id"],
                       r["om_lb"] <= r["om_obj"] + TOL, "{} > {}".format(r["om_lb"], r["om_obj"]))
        if (r["t_d"] == 0.0 and r["n_batch_members_known"] == r["n_batch_members"]
                and r["om_term_feas"] == "applied_uncertified"):
            check.close("A8", "realised objective equals the full window on " + r["item_id"],
                        r["rw_obj"], r["om_obj"], TOL)
            check.close("A8", "realised original-field objective equals the full window on "
                        + r["item_id"], r["rw_obj_orig"], r["om_obj_orig"], TOL)
            check.true("A8", "realised terminal equals the full window on " + r["item_id"],
                       r["rw_term"] == r["om_term_cert"])
    bkey = {(b["iid"], b["t_d"], b["fp"]): b for b in boards}
    for b in boards:
        check.true("A9", "board ATC dispatch is feasible: {} t_d={} {}".format(
            b["iid"], b["t_d"], b["fp"][:10]), b["atc_feasible"])
        for tr, tv in b["trades"].items():
            check.true("A9", "LB2 <= upper on {} t_d={} {} {}".format(b["iid"], b["t_d"],
                                                                     b["fp"][:10], tr),
                       tv["lb2"] <= tv["upper0"] + D.CHECK_TOL)
    for r in items:
        if r["dt_lb"] is not None and r["dt_obj"] is not None:
            check.true("A9", "LB_K <= obj_K on " + r["item_id"], r["dt_lb"] <= r["dt_obj"] + TOL)
        if r["an_lb"] is not None:
            check.true("A9", "anchor LB_K <= obj_K on " + r["item_id"],
                       r["an_lb"] <= r["an_obj"] + TOL)
        b0 = bkey.get((r["instance_id"], r["t_d"], D.BASE_FP))
        check.true("A12", "anchor board exists for " + r["item_id"], b0 is not None)
        if b0 is None:
            continue
        check.close("A12", "running constant equals bound_known lb_running on " + r["item_id"],
                    b0["running_const"], r["an_lb_running"], D.CHECK_TOL)
        check.close("A12", "anchor board LB2 + running constant equals LB_K on " + r["item_id"],
                    sum(tv["lb2"] for tv in b0["trades"].values()) + b0["running_const"],
                    r["an_lb"], D.CHECK_TOL)
        if r["dt_stage_cert"] == "qual":
            b = bkey.get((r["instance_id"], r["t_d"], r["dt_fp"]))
            check.true("A12", "proposal board exists for " + r["item_id"], b is not None)
            if b is not None:
                lo = sum(tv["lb2"] for tv in b["trades"].values()) + b["running_const"]
                check.close("A12", "proposal board LB2 sum equals LB_K on " + r["item_id"], lo,
                            r["dt_lb"], D.CHECK_TOL)
                check.true("A9", "obj_K at or above the board's LB2 end on " + r["item_id"],
                           r["dt_obj"] >= lo - D.CHECK_TOL)


#: Fields of a census row that N12's calibrated environment must reproduce exactly.
SKIP_IDENTITY = {"c_needed", "c_error", "c_keys", "c_trades", "c_role", "set"}


def identity_census(check, items, boards, partial=False) -> dict:
    """E6 (cal): the census rows and boards equal N11's primary census exactly (==)."""
    n11 = {r["item_id"]: r for r in D.read_jsonl(D.OUT / "items.jsonl") if r["set"] == "published"}
    n_fields = 0
    diff = Counter()
    rule_touched = []
    check.true("E6", "N11 primary census holds the 2,000 published items", len(n11) == 2000,
               len(n11))
    check.true("E6", "the census covers every published item", partial or len(items) == 2000,
               len(items))
    for r in items:
        o = n11.get(r["item_id"])
        check.true("E6", "N11 census row exists for " + r["item_id"], o is not None)
        if o is None:
            continue
        for k in sorted(set(r) & set(o)):
            if k in SKIP_IDENTITY:
                continue
            n_fields += 1
            if k == "dt_codes" and r[k] != o[k] and r.get("names_running_any") and \
                    set(o[k] or []) <= set(r[k] or []) and \
                    set(r[k] or []) - set(o[k] or []) == {D.RUNNING_WORK_CODE} and \
                    r["dt_term_cert"] == o["dt_term_cert"]:
                # Stage 3's running-work rule (addition A) adds its code beside an existing
                # blocking finding; the terminal and every price are unchanged (Stage 3 AF0).
                rule_touched.append(r["item_id"])
                continue
            if r[k] != o[k]:
                diff[k] += 1
                check.true("E6", "census field {} equals N11 on {}".format(k, r["item_id"]), False,
                           "{!r} vs {!r}".format(r[k], o[k]))
    nb = {(b["iid"], b["t_d"], b["fp"]): b for b in D.read_jsonl(D.OUT / "boards.jsonl")}
    n_b = 0
    for b in boards:
        o = nb.get((b["iid"], b["t_d"], b["fp"]))
        check.true("E6", "N11 board exists for {} t_d={}".format(b["iid"], b["t_d"]), o is not None)
        if o is None:
            continue
        n_b += 1
        for k in b:
            if k == "seeds":
                continue
            check.true("E6", "board field {} equals N11 on {} t_d={}".format(k, b["iid"], b["t_d"]),
                       b[k] == o.get(k), k)
    return {"fields_compared": n_fields, "fields_differing": dict(diff), "boards_compared": n_b,
            "running_work_code_added": sorted(rule_touched)}


def cmd_census(args) -> int:
    name = args.env
    pin()
    activate(name)
    t0 = time.time()
    smoke = bool(args.instances)
    out_dir = stage_dir(name, "census", smoke)
    out_dir.mkdir(parents=True, exist_ok=True)
    check = D.Checker()
    pub = load_suite_items(check)
    paths = instance_paths(pub)
    # ---- E1-E3 on every derived instance, in the parent, before any work
    recs = OrderedDict()
    for iid, pth in paths.items():
        rel = source_rel(pth)
        src = _ORIG_LOAD(pth)
        der = D.load_instance(pth)
        recs[iid] = check_derivation(check, src, der, ENVS[name], rel)
    if not smoke:
        write_manifest(name, recs)
    if check.failures:
        check.fatal(out_dir / "assertions.json", {"stage": "derivation"})
    tasks = D.build_tasks(pub, OrderedDict(), {})
    if args.instances:
        keep = set(args.instances.split(","))
        tasks = [t for t in tasks if t["iid"] in keep]
    for t in tasks:
        t["kf"], t["reading"] = "fix", "primary"
        for it in t["items"]:
            it["c_needed"] = False
    D._TASKS = tasks
    order = sorted(range(len(tasks)), key=lambda i: (
        0 if "c10_storm" in tasks[i]["iid"] else 1 if "c09_storm" in tasks[i]["iid"] else 2,
        -len(tasks[i]["items"])))
    print("[n12 census {}] {} instances, {} items, {} workers on cores {}".format(
        name, len(tasks), sum(len(t["items"]) for t in tasks), args.workers, list(CORES)),
        flush=True)
    results = D.run_pool(census_worker, len(tasks), list(CORES), args.workers, order)
    items, boards, rel_inputs, seeds, anchor_omni, probes = [], [], [], {}, {}, {}
    tuples, bad_tuples, sha_seen = {}, [], {}
    for res in sorted(results, key=lambda r: r["iid"]):
        items.extend(res["items"])
        boards.extend(res["boards"])
        rel_inputs.extend(res["relaxed_inputs"])
        for fk, v in res["seeds"].items():
            seeds[(res["iid"], fk)] = v
        for fk, v in res["anchor_omni"].items():
            anchor_omni[(res["iid"], fk)] = v
        probes[res["iid"]] = res["probe"]
        tuples.update(res["om_tuples"])
        bad_tuples += res["om_tuples_bad"]
        sha_seen[res["iid"]] = res["inst_file_sha"]
    for iid, s in sha_seen.items():
        check.true("E1", "worker saw the derived instance recorded in the manifest ({})".format(iid),
                   s == recs[iid]["derived_file_sha256"])
    postprocess_items(items, pub)
    env_census_checks(check, items, boards, seeds, anchor_omni, probes, bad_tuples)
    ident = None
    if name == "cal":
        D.CENSUS_COUNTS.clear()
        D.run_checks_census(check, items, boards, seeds, anchor_omni, pub, {}, smoke)
        ident = identity_census(check, items, boards, smoke)
    D.write_jsonl(out_dir / "items.jsonl", items)
    D.write_jsonl(out_dir / "boards.jsonl", boards)
    D.write_jsonl(out_dir / "relaxed_inputs.jsonl", rel_inputs)
    D.write_jsonl(out_dir / "anchors.jsonl",
                  [dict(v, iid=k[0], fk=k[1]) for k, v in sorted(anchor_omni.items())])
    D.write_jsonl(out_dir / "om_tuples.jsonl",
                  [{"item_id": k, "tuples": v} for k, v in sorted(tuples.items())])
    wall = time.time() - t0
    summ = D.census_summary(items, boards, rel_inputs, {})
    meta = OrderedDict(version=VERSION, stage="census", env=name, settings=ENVS[name],
                       finished=D.now_iso(), wall_s=wall, cores=list(CORES), workers=args.workers,
                       omp_num_threads=os.environ.get("OMP_NUM_THREADS"),
                       mkl_num_threads=os.environ.get("MKL_NUM_THREADS"),
                       load_avg_end=D.loadavg(), host=socket.gethostname(), smoke=smoke,
                       summary=summ, identity=ident, code=code_hashes(),
                       instance_wall_s={r["iid"]: r["wall_s"] for r in results},
                       outputs=outputs_of(out_dir))
    D.write_json(out_dir / "meta.json", meta)
    check.fatal(out_dir / "assertions.json", {"outputs": meta["outputs"], "finished": meta["finished"],
                                              "smoke": smoke})
    print(json.dumps(summ, indent=1), flush=True)
    print("[n12 census {}] PASS: {} checks in {:.0f}s".format(name, check.report()["n_checks"], wall),
          flush=True)
    return 0


# --------------------------------------------------------------------------- #
# Stage: oracle (CP-SAT, cores 8-11 exclusive)                                 #
# --------------------------------------------------------------------------- #
def _oc():
    import oracle_cost as OC
    return OC


class EnvStore:
    """oracle_cost.Store on the active environment's derived instances."""

    def __init__(self, paths, strata):
        OC = _oc()
        m = OC.mods()
        self.inst, self.path, self.stratum, self.baseline = {}, {}, {}, {}
        self.base_fields, self.trade_of, self.trades = {}, {}, {}
        for iid, p in paths.items():
            inst = D.load_instance(p)
            self.inst[iid] = inst
            self.path[iid] = str(p)
            self.stratum[iid] = strata[iid]
            self.baseline[iid] = m["dispatch"].dispatch_baseline(inst, OC.EPISODE_RULE,
                                                                 seed=OC.EPISODE_SEED)
            self.base_fields[iid] = {wo["id"]: tuple(wo[f] for f in OC.FIELDS)
                                     for wo in inst["work_orders"]}
            self.trade_of[iid] = {wo["id"]: wo["trade"] for wo in inst["work_orders"]}
            self.trades[iid] = sorted({wo["trade"] for wo in inst["work_orders"]})

    changed_tuples = None
    trade_fps = None
    relaxed = None


def _bind_store_methods():
    OC = _oc()
    EnvStore.changed_tuples = OC.Store.changed_tuples
    EnvStore.trade_fps = OC.Store.trade_fps
    EnvStore.relaxed = OC.Store.relaxed


def full_cache(path) -> tuple:
    """Last valid row per (instance, trade, trade fingerprint); invalid rows dropped (E8)."""
    cache, drops = {}, Counter()
    for r in D.read_jsonl(path):
        k = (r["instance_id"], r["trade"], r["trade_fp"])
        if (r.get("invalid") or r.get("contended")) and not r.get("invalid_persistent"):
            cache.pop(k, None)
            drops[k] += 1
            continue
        cache[k] = r
    return cache, drops


def solve_full_trade(relaxed, tr, atc, lb_t, args, key, n_changed, drops, path, log) -> dict:
    OC = _oc()
    while True:
        row = OC.solve_trade(relaxed, tr, atc, lb_t, args.budget, args.workers)
        row = OrderedDict([("instance_id", key[0]), ("trade", tr), ("trade_fp", key[2]),
                           ("n_changed_orders", n_changed), ("version", VERSION),
                           ("env", _STATE["env"]), ("recipe", OC.VERSION)] + list(row.items()))
        row["load_avg_end"] = D.loadavg()
        row["omp_num_threads"] = os.environ.get("OMP_NUM_THREADS")
        row["mkl_num_threads"] = os.environ.get("MKL_NUM_THREADS")
        row["invalid"] = bool(row["contended"])
        scs = row.get("solve_cpu_share")
        row["low_cpu_share"] = bool(scs is not None and scs < 0.9)
        if row["invalid"] and drops[key] >= MAX_RESOLVES:
            row["invalid_persistent"] = True
        D.append_jsonl(path, row)
        if row["invalid"] and not row.get("invalid_persistent"):
            drops[key] += 1
            log("[n12 oracle] INVALID (foreign_share {:.3f}) {}; solving again".format(
                row["foreign_share"], key))
            continue
        return row


def bracket_full(store, iid, fp, tuples, cache, args, path, drops, dev, log) -> OrderedDict:
    """oracle_cost.bracket_one, with re-solves of invalid rows and exact cache checks."""
    OC = _oc()
    m = OC.mods()
    relaxed = store.relaxed(iid, tuples)
    t0 = time.perf_counter()
    atc = m["dispatch"].dispatch_baseline(relaxed, OC.EPISODE_RULE, seed=OC.EPISODE_SEED)
    atc_total = m["evaluate"].wwt(relaxed, atc)
    lbd = m["lb2"].lb2_detail(relaxed)
    tfps = store.trade_fps(iid, tuples)
    atc_t = OC.trade_wwt(relaxed, atc)
    n_changed_by_trade = Counter(store.trade_of[iid][t[0]] for t in tuples)
    lower = upper = cp_raw = 0.0
    proved = True
    statuses, solved_now = {}, 0
    for tr in store.trades[iid]:
        key = (iid, tr, tfps[tr])
        lb_t = lbd["per_trade"].get(tr, {}).get("bound", 0.0)
        row = cache.get(key)
        if row is None:
            row = solve_full_trade(relaxed, tr, atc, lb_t, args, key,
                                   n_changed_by_trade.get(tr, 0), drops, path, log)
            cache[key] = row
            solved_now += 1
        else:
            da = abs(row["atc_trade_obj"] - atc_t.get(tr, 0.0))
            dl = abs(row["lb2_trade"] - lb_t)
            dev["atc"] = max(dev["atc"], da)
            dev["lb2"] = max(dev["lb2"], dl)
            dev["n"] += 1
            if da > EXACT or dl > EXACT:
                raise SystemExit("E6/E5 FAILURE: cached trade row moved for {}: ATC {} vs {}, "
                                 "LB2 {} vs {}".format(key, row["atc_trade_obj"],
                                                       atc_t.get(tr, 0.0), row["lb2_trade"], lb_t))
        lower += row["lower"]
        upper += row["upper"]
        cp_raw += row["cp_bound"] if row["cp_bound"] is not None else row["lower"]
        closed = row["upper"] - row["lower"] <= OC.CLOSE_TOL_BH
        statuses[tr] = row["status"]
        proved = proved and (row["status"] in ("OPTIMAL", "CLOSED_BY_LB2") or closed)
    if abs(sum(atc_t.values()) - atc_total) > OC.CHECK_TOL_BH:
        raise SystemExit("ATC does not decompose by trade on {} {}".format(iid, fp))
    out = OrderedDict(
        instance_id=iid, stratum=store.stratum[iid], fingerprint=fp,
        n_changed_orders=len(tuples), lower=lower, upper=upper, lb2_total=lbd["lb_bh"],
        cp_bound_total_raw=cp_raw, atc_total=atc_total, proved_all=proved,
        width_abs=upper - lower, width_rel=(upper - lower) / max(lower, OC.FLOOR_BH),
        atc_gap_to_lower=(atc_total - lower) / max(lower, OC.FLOOR_BH),
        statuses=statuses, n_trade_solves_now=solved_now, wall_s=time.perf_counter() - t0,
        budget_s=args.budget, version=VERSION, env=_STATE["env"])
    if out["lower"] > out["upper"] + OC.CHECK_TOL_BH or \
            out["lb2_total"] > out["upper"] + OC.CHECK_TOL_BH:
        raise SystemExit("E5 FAILURE: BRACKET VIOLATION\n" + json.dumps(out))
    return out


def full_need(items, tuples, store) -> OrderedDict:
    OC = _oc()
    need = OrderedDict()
    for iid in store.inst:
        need[(iid, OC.BASE_FP)] = []
    for r in items:
        fp = r.get("om_fp")
        if fp is None:
            continue
        tl = [tuple(t) for t in tuples[r["item_id"]]]
        k = (r["instance_id"], fp)
        if k not in need:
            need[k] = tl
    return need


def model_selfcheck(args, log) -> dict:
    """At f = 1: re-solve oracle_v1 OPTIMAL baseline trades (<= 400 orders) and reproduce them."""
    OC = _oc()
    m = OC.mods()
    import suite_gate as sg

    rows = [r for r in D.read_jsonl(D.ORACLE_V1 / "trade_solves.jsonl")
            if r["trade_fp"] == OC.BASE_FP and r["status"] == "OPTIMAL" and r["n_orders"] <= 400
            and not r.get("contended")]
    rows.sort(key=lambda r: (r["instance_id"], r["trade"]))
    pick = rows[::max(1, len(rows) // 12)][:12]
    pub = OrderedDict((r["item_id"], r) for r in sg.load_suite())
    paths = instance_paths(pub)
    out = []
    for r in pick:
        inst = D.load_instance(paths[r["instance_id"]])
        atc = m["dispatch"].dispatch_baseline(inst, OC.EPISODE_RULE, seed=OC.EPISODE_SEED)
        lbd = m["lb2"].lb2_detail(inst)["per_trade"]
        row = OC.solve_trade(inst, r["trade"], atc, lbd.get(r["trade"], {}).get("bound", 0.0),
                             args.budget, args.workers, force_solve=True)
        rec = {"instance_id": r["instance_id"], "trade": r["trade"], "n_orders": r["n_orders"],
               "status": row["status"], "cp_grid_obj": row["cp_grid_obj"],
               "v1_cp_grid_obj": r["cp_grid_obj"], "lower": row["lower"], "v1_lower": r["lower"],
               "wall_s": row["wall_s"], "foreign_share": row["foreign_share"]}
        rec["ok"] = (row["status"] == "OPTIMAL" and abs(row["cp_grid_obj"] - r["cp_grid_obj"]) <= TOL
                     and abs(row["lower"] - r["lower"]) <= TOL)
        out.append(rec)
        log("[n12 oracle] model self-check {} {} n={} {} grid {} vs {} {}".format(
            r["instance_id"], r["trade"], r["n_orders"], row["status"], row["cp_grid_obj"],
            r["cp_grid_obj"], "OK" if rec["ok"] else "FAIL"))
    return {"rows": out, "fails": [x for x in out if not x["ok"]]}


def dt_solve(ti, args, drops, path, log) -> dict:
    k = D.relaxed_key(ti)
    while True:
        row = D.solve_relaxed(ti, args, list(CORES))
        row["env"] = _STATE["env"]
        row["n12_version"] = VERSION
        row["mkl_num_threads"] = os.environ.get("MKL_NUM_THREADS")
        if row["invalid"] and drops[k] >= MAX_RESOLVES:
            row["invalid_persistent"] = True
        D.append_jsonl(path, row)
        if row["invalid"] and not row.get("invalid_persistent"):
            drops[k] += 1
            log("[n12 oracle] INVALID (foreign_share {:.3f}) {}; solving again".format(
                row["foreign_share"], k))
            continue
        return row


TIMING_KEYS = ("affinity", "workers", "omp_num_threads", "load_avg_start", "load_avg_end",
               "wall_s", "solve_wall_s", "cpu_s", "cpu_share", "solve_cpu_share",
               "foreign_share", "status", "budget_s")


def cmd_oracle(args) -> int:
    name = args.env
    pin()
    activate(name)
    _bind_store_methods()
    OC = _oc()
    OC.mods()
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    smoke = bool(args.smoke)
    gate = stage_gate(name, "census", smoke=smoke)
    foreign = D.foreign_on_cores(set(CORES))
    if foreign:
        raise SystemExit("REFUSING TO RUN: foreign processes on cores 8-11: {}".format(foreign))
    out_dir = stage_dir(name, "oracle", smoke)
    out_dir.mkdir(parents=True, exist_ok=True)
    cdir = stage_dir(name, "census", smoke)
    t_run = time.time()
    check = D.Checker()
    log_lines = []

    def log(msg):
        print(msg, flush=True)

    import ortools
    meta = OrderedDict(version=VERSION, stage="oracle", env=name, started=D.now_iso(),
                       host=socket.gethostname(), python=sys.version.split()[0],
                       platform=platform.platform(), ortools=ortools.__version__,
                       cores=list(CORES), workers=args.workers, budget_s=args.budget,
                       omp_num_threads=os.environ.get("OMP_NUM_THREADS"),
                       mkl_num_threads=os.environ.get("MKL_NUM_THREADS"),
                       foreign_share_max=FOREIGN_SHARE_MAX, max_resolves=MAX_RESOLVES,
                       affinity=sorted(os.sched_getaffinity(0)), load_avg_start=D.loadavg(),
                       foreign_processes_at_start=foreign, gate=gate, code=code_hashes(),
                       recipe=OC.VERSION, cpsat_py_sha256=D.sha256_file(OC.mods()["cpsat"].__file__))
    D.write_json(out_dir / "run_meta.json", meta)
    walls = OrderedDict()
    pub = load_suite_items(check)
    paths = instance_paths(pub)
    strata = strata_of(pub)
    items = D.read_jsonl(cdir / "items.jsonl")
    tuples = {r["item_id"]: r["tuples"] for r in D.read_jsonl(cdir / "om_tuples.jsonl")}
    # ---- model self-check at f = 1 (cal only): the solver reproduces oracle_v1's optima
    if name == "cal" and not args.no_selfcheck:
        t0 = time.time()
        sc = model_selfcheck(args, log)
        D.write_json(out_dir / "selfcheck.json", sc)
        for x in sc["rows"]:
            check.true("E6", "model self-check reproduces oracle_v1 on {} {}".format(
                x["instance_id"], x["trade"]), x["ok"], x)
        walls["selfcheck_s"] = time.time() - t0
    # ---- (1) the full-window oracle
    t0 = time.time()
    if smoke:
        keep = {r["instance_id"] for r in items}
        paths = OrderedDict((k, v) for k, v in paths.items() if k in keep)
    store = EnvStore(paths, strata)
    need = full_need(items, tuples, store)
    for (iid, fp), tl in need.items():
        check.true("E5", "need tuples reproduce the fingerprint {} {}".format(iid, fp[:10]),
                   D.fp_of(tl) == fp and store.changed_tuples(iid, store.relaxed(iid, tl)) == tl)
    trade_path = out_dir / "full_trade_solves.jsonl"
    cache, drops = full_cache(trade_path)
    reused_v1 = 0
    if name == "cal":
        v1, _d = OC.load_trade_cache(D.ORACLE_V1 / "trade_solves.jsonl")
        for k, v in v1.items():
            if k not in cache:
                cache[k] = dict(v, reused_from="oracle_v1")
                reused_v1 += 1
    dev = {"atc": 0.0, "lb2": 0.0, "n": 0}
    queue = OC.solve_queue(store, {k: {} for k in need})
    if args.limit:
        queue = queue[: args.limit]
    br_rows = []
    for i, (iid, fp) in enumerate(queue, 1):
        b = bracket_full(store, iid, fp, need[(iid, fp)], cache, args, trade_path, drops, dev, log)
        br_rows.append(b)
        if b["n_trade_solves_now"] or i % 50 == 0 or i == len(queue):
            log("[n12 oracle {}] full {}/{} {} {} chg={} [{:.4f}, {:.4f}] width={:.4%} proved={} "
                "solves={} wall={:.1f}s elapsed={:.0f}s".format(
                    name, i, len(queue), iid, fp[:10], b["n_changed_orders"], b["lower"],
                    b["upper"], b["width_rel"], b["proved_all"], b["n_trade_solves_now"],
                    b["wall_s"], time.time() - t0))
    D.write_jsonl(out_dir / "full_brackets.jsonl", br_rows)
    walls["full_s"] = time.time() - t0
    # E5: every executed full-window objective sits at or above its bracket's lower end
    bk = {(b["instance_id"], b["fingerprint"]): b for b in br_rows}
    for r in items:
        if r["om_fp"] is None or r["om_obj"] is None:
            continue
        b = bk.get((r["instance_id"], r["om_fp"]))
        if b is None and args.limit:
            continue
        check.true("E5", "full-window objective >= bracket lower on " + r["item_id"],
                   r["om_obj"] >= b["lower"] - TOL, "{} < {}".format(r["om_obj"], b["lower"]))
        if r["om_lb"] is not None:
            check.true("E5", "certificate bound <= bracket upper on " + r["item_id"],
                       r["om_lb"] <= b["upper"] + TOL)
    for b in br_rows:
        check.true("E5", "bracket lower <= upper {} {}".format(b["instance_id"], b["fingerprint"][:10]),
                   b["lower"] <= b["upper"] + TOL and b["lb2_total"] <= b["upper"] + TOL)
    ident = {}
    if name == "cal" and not smoke:
        v1b = {(r["instance_id"], r["fingerprint"]): r for r in D.read_jsonl(D.ORACLE_V1 /
                                                                             "brackets.jsonl")}
        n_new = sum(b["n_trade_solves_now"] for b in br_rows)
        check.true("E6", "cal reuses oracle_v1 for every trade (no new solve)", n_new == 0, n_new)
        for b in br_rows:
            o = v1b.get((b["instance_id"], b["fingerprint"]))
            check.true("E6", "oracle_v1 bracket exists for {} {}".format(b["instance_id"],
                                                                        b["fingerprint"][:10]),
                       o is not None)
            if o is None:
                continue
            for k in ("lower", "upper", "lb2_total", "atc_total", "cp_bound_total_raw"):
                check.close("E6", "bracket {} equals oracle_v1 on {} {}".format(
                    k, b["instance_id"], b["fingerprint"][:10]), b[k], o[k], EXACT)
            check.true("E6", "proved_all equals oracle_v1 on {} {}".format(
                b["instance_id"], b["fingerprint"][:10]), b["proved_all"] == o["proved_all"])
        ident = {"brackets_compared": len(br_rows), "trade_rows_reused": dev["n"],
                 "max_atc_dev": dev["atc"], "max_lb2_dev": dev["lb2"]}
    # ---- (2) the decision-time oracle on K
    t0 = time.time()
    rel_in = D.read_jsonl(cdir / "relaxed_inputs.jsonl")
    boards = D.read_jsonl(cdir / "boards.jsonl")
    dt_path = out_dir / "dt_trade_solves.jsonl"
    rel_rows, dt_drops = D.load_rows_last(dt_path, D.relaxed_key)
    reused_n11 = 0
    if name == "cal":
        n11_rows, _ = D.load_rows_last(D.ORACLE_OUT / "trade_solves.jsonl", D.relaxed_key)
        for ti in rel_in:
            k = D.relaxed_key(ti)
            o = n11_rows.get(k)
            if o is None or k in rel_rows:
                continue
            check.close("E6", "N11 relaxed row LB2 equals the census on {}".format(k), o["lb2"],
                        ti["lb2"], EXACT)
            check.close("E6", "N11 relaxed row ATC equals the census on {}".format(k), o["atc"],
                        ti["atc"], EXACT)
            rel_rows[k] = dict(o, reused_from="n11_oracle")
            reused_n11 += 1
    todo = sorted(rel_in, key=lambda r: (r["n_orders"], r["iid"], r["t_d"], r["trade"]))
    n_dt = 0
    for ti in todo:
        k = D.relaxed_key(ti)
        if k in rel_rows:
            continue
        row = dt_solve(ti, args, dt_drops, dt_path, log)
        rel_rows[k] = row
        n_dt += 1
        log("[n12 oracle {}] dt {} {} t_d={:.2f} {} n={} {} [{:.3f}, {:.3f}] wall={:.1f}s "
            "foreign={}".format(name, n_dt, ti["iid"], ti["t_d"], ti["trade"], ti["n_orders"],
                                row["status"], row["lower"], row["upper"], row["wall_s"],
                                None if row["foreign_share"] is None
                                else round(row["foreign_share"], 3)))
    dt_br, _tb = D.assemble_boards(boards, rel_rows)
    D.write_jsonl(out_dir / "dt_brackets.jsonl", dt_br)
    walls["dt_s"] = time.time() - t0
    if name == "cal" and not smoke:
        check.true("E6", "cal reuses N11 for every decision-time trade (no new solve)", n_dt == 0,
                   n_dt)
        n11b = {(b["iid"], float(b["t_d"]), b["fp"]): b
                for b in D.read_jsonl(D.ORACLE_OUT / "brackets.jsonl")}
        nb = 0
        for b in dt_br:
            o = n11b.get((b["iid"], float(b["t_d"]), b["fp"]))
            if o is None or not o.get("complete"):
                continue
            nb += 1
            for k in ("lower", "upper", "running_const"):
                check.close("E6", "decision-time bracket {} equals N11 on {} {}".format(
                    k, b["iid"], b["t_d"]), b[k], o[k], EXACT)
        ident["dt_brackets_compared"] = nb
        check.true("E6", "decision-time brackets compared with N11", nb > 0, nb)
    # ---- E8, E9
    solve_rows = [r for r in D.read_jsonl(trade_path) if r.get("status") != "CLOSED_BY_LB2"] + \
        D.read_jsonl(dt_path)
    for sr in solve_rows:
        check.true("E8", "solve row carries the timing record",
                   all(k in sr for k in TIMING_KEYS), [k for k in TIMING_KEYS if k not in sr])
    for (iid, fp) in need:
        if args.limit:
            break
        check.true("E9", "full-window bracket on disk for {} {}".format(iid, fp[:10]),
                   (iid, fp) in bk)
    need_dt = set()
    for r in items:
        if r["issuable"] and r["dt_stage_cert"] == "qual":
            need_dt.add((r["instance_id"], float(r["t_d"]), r["dt_fp"]))
            need_dt.add((r["instance_id"], float(r["t_d"]), D.BASE_FP))
    dtk = {(b["iid"], float(b["t_d"]), b["fp"]) for b in dt_br if b["complete"]}
    miss = sorted(need_dt - dtk)
    check.true("E9", "every needed decision-time board is bracketed", not miss, miss[:5])
    for b in dt_br:
        if b["complete"]:
            check.true("E5", "decision-time board lower <= upper {} {}".format(b["iid"], b["t_d"]),
                       b["lower"] <= b["upper"] + TOL)
    new_full = [r for r in D.read_jsonl(trade_path) if r.get("status") != "CLOSED_BY_LB2"]
    prof = timing_profile(new_full, D.read_jsonl(dt_path))
    meta.update(finished=D.now_iso(), wall_s=time.time() - t_run, walls=walls,
                load_avg_end=D.loadavg(), full_brackets=len(br_rows),
                full_proved=sum(1 for b in br_rows if b["proved_all"]),
                dt_boards=len(dt_br), dt_complete=sum(1 for b in dt_br if b["complete"]),
                reused_oracle_v1_rows=reused_v1, reused_n11_rows=reused_n11,
                new_dt_solves=n_dt, identity=ident, timing=prof,
                outputs=outputs_of(out_dir))
    D.write_json(out_dir / "run_meta.json", meta)
    check.fatal(out_dir / "assertions.json", {"outputs": meta["outputs"], "finished": meta["finished"],
                                              "smoke": smoke})
    log("[n12 oracle {}] PASS: {} checks, {:.0f}s (full {:.0f}s, dt {:.0f}s)".format(
        name, check.report()["n_checks"], meta["wall_s"], walls["full_s"], walls["dt_s"]))
    return 0


def timing_profile(full_rows, dt_rows) -> dict:
    out = OrderedDict()
    for label, rows in (("full", full_rows), ("dt", dt_rows)):
        rows = [r for r in rows if r.get("reused_from") is None]
        bl = [r for r in rows if r.get("status") not in ("OPTIMAL", "CLOSED_BY_LB2", "CLOSED")]
        fs = [r["foreign_share"] for r in rows if r.get("foreign_share") is not None]
        fsb = [r["foreign_share"] for r in bl if r.get("foreign_share") is not None]
        cs = [r["cpu_share"] for r in rows if r.get("cpu_share") is not None]
        scs = [r["solve_cpu_share"] for r in rows if r.get("solve_cpu_share") is not None]
        out[label] = OrderedDict(
            solves=len(rows), statuses=dict(Counter(r.get("status") for r in rows)),
            invalid=sum(1 for r in rows if r.get("invalid")),
            invalid_persistent=sum(1 for r in rows if r.get("invalid_persistent")),
            wall_s=sum(float(r.get("wall_s") or 0.0) for r in rows),
            budget_limited=len(bl), foreign_share_max=max(fs) if fs else None,
            foreign_share_max_budget_limited=max(fsb) if fsb else None,
            foreign_share_median=D.median(fs), cpu_share_median=D.median(cs),
            solve_cpu_share_median=D.median(scs),
            low_solve_cpu_share=sum(1 for x in scs if x < 0.9))
    return out


# --------------------------------------------------------------------------- #
# Stage: forecast F2                                                           #
# --------------------------------------------------------------------------- #
def k_rows_env(items, anchors, td_br=None, full_br=None) -> list:
    for r in items:
        a = anchors[(r["instance_id"], r["frozen_seed"])]
        r["pub_anchor_wwt"] = float(a["wwt_original_bh"])
        r["pub_anchor_gap"] = float(a["gap"])
        D.om_prices(r)
    return D.build_rows(items, td_br or {}, full_br or {}, anchors)


def env_anchors(name, smoke=False) -> dict:
    """(instance, frozen key) -> the environment's no-proposal anchor at t = 0, rule_anchor's schema."""
    out = {}
    for a in D.read_jsonl(stage_dir(name, "census", smoke) / "anchors.jsonl"):
        out[(a["iid"], a["fk"])] = {"wwt_original_bh": a["obj_orig"], "wwt_adjusted_bh": a["obj"],
                                    "gap": a["gap"], "certificate": {"lb_bh": a["lb"]},
                                    "term_cert": a["term_cert"]}
    return out


def cmd_forecast(args) -> int:
    import n11_forecast as F

    name = args.env
    pin()
    activate(name)
    smoke = bool(args.smoke)
    gate = stage_gate(name, "census", smoke=smoke)
    foreign = D.foreign_on_cores(set(CORES))
    t0 = time.time()
    out_dir = stage_dir(name, "forecast", smoke)
    out_dir.mkdir(parents=True, exist_ok=True)
    check = D.Checker()
    dec = json.loads((N11F / "smoke_decision.json").read_text())
    rep = json.loads((N11F / "smoke_assertions.json").read_text())
    check.true("AF9", "Stage 3 smoke step passed", rep.get("status") == "PASS")
    S = int(dec["S"])
    pub = load_suite_items(check)
    items = D.read_jsonl(stage_dir(name, "census", smoke) / "items.jsonl")
    pool = F.load_pool(check)                 # read-only: manifest_pool.json exists (AF7)
    check.true("AF7", "76 pool windows", len(pool) == 76, len(pool))
    inp = {"pub": pub, "items": items, "pool": pool}
    inst = set(args.instances.split(",")) if args.instances else None
    readings = OrderedDict([("F2", S)])
    tasks = F.prepare(F.direct_units(inp, check, inst), inp, readings, True, False)
    cfg = F.sha_obj({"version": VERSION, "env": name, "settings": ENVS[name],
                     "readings": list(readings.items()), "topup": True, "open_trades": False,
                     "code": code_hashes(), "forecast_code": F.code_sha(),
                     "pool": json.loads((N11F / "manifest_pool.json").read_text())["windows"],
                     "s_topup": F.S_TOPUP})
    part_dir = out_dir / "parts"
    res = F.run_parts(tasks, part_dir, list(CORES), args.workers, cfg, "n12 {} F2".format(name))
    anchors = env_anchors(name, smoke)
    krows = k_rows_env(D.read_jsonl(stage_dir(name, "census", smoke) / "items.jsonl"), anchors)
    kinfo = F.assert_k_direct(check, res, items, krows)
    summ = F.assert_runs(check, res)
    for t in tasks:
        got = Counter((p["uid"], p["reading"]) for p in res[t["iid"]]["prices"])
        for u in t["units"]:
            if u["forecast"]:
                check.true("AF9", "{} has {} futures of F2".format(u["uid"], S),
                           got[(u["uid"], "F2")] >= S, got[(u["uid"], "F2")])
    n_sound = 0
    for rr in res.values():
        for p in rr["prices"]:
            q = p["p"]
            if q["lb"] is not None and q["obj"] is not None:
                n_sound += 1
                check.true("E5", "LB <= obj on a sampled F2 board ({} s={})".format(p["uid"], p["s"]),
                           q["lb"] <= q["obj"] + TOL)
    ident = None
    if name == "cal" and not smoke:
        ident = identity_forecast(check, res)
    elif name == "cal":
        ident = identity_forecast(check, res, partial=True)
    outs = F.write_outputs(res, out_dir, "direct")
    meta = OrderedDict(version=VERSION, stage="forecast", env=name, S=S, finished=D.now_iso(),
                       wall_s=time.time() - t0, cores=list(CORES), workers=args.workers,
                       omp_num_threads=os.environ.get("OMP_NUM_THREADS"),
                       foreign_at_start=foreign, gate=gate, load_avg_end=D.loadavg(),
                       instance_wall_s={k: v["wall_s"] for k, v in res.items()},
                       stage_diff=dict(summ["stage_diff"]), topup=dict(summ["topup"]),
                       rule_touched=kinfo["rule_touched"], sampled_boards=n_sound,
                       af3={"{}|{}".format(*k): v for k, v in summ["af3"].items()},
                       identity=ident, outputs=outs)
    D.write_json(out_dir / "meta.json", meta)
    check.fatal(out_dir / "assertions.json", {"outputs": outs, "finished": meta["finished"],
                                              "smoke": smoke})
    print("[n12 forecast {}] PASS: {} checks in {:.0f}s".format(name, check.report()["n_checks"],
                                                              time.time() - t0), flush=True)
    return 0


def identity_forecast(check, res, partial=False) -> dict:
    """E6 (cal): every F2 price record equals Stage 3's (uid, s) record exactly."""
    import n11_forecast as F

    want = {}
    for r in D.read_jsonl(N11F / "prices_direct.jsonl"):
        if r["reading"] == "F2":
            want[(r["uid"], r["s"])] = r
    got = {}
    for rr in res.values():
        for p in rr["prices"]:
            got[(p["uid"], p["s"])] = p
    if partial:
        want = {k: v for k, v in want.items() if k in got}
    check.true("E6", "same F2 (item, future) set as Stage 3", set(got) == set(want),
               "{} vs {}".format(len(got), len(want)))
    n = 0
    for k, p in got.items():
        w = want.get(k)
        if w is None:
            continue
        n += 1
        check.true("E6", "F2 price record equals Stage 3 on {}".format(k),
                   F.canon(p["p"]) == F.canon(w["p"]) and F.canon(p["prices"]) == F.canon(w["prices"]))
    return {"records_compared": n}


# --------------------------------------------------------------------------- #
# Stage: analyse                                                               #
# --------------------------------------------------------------------------- #
class N2Check:
    """n2_pricing's Checker interface onto N11's run-fatal Checker (group E5/E6)."""

    def __init__(self, check, group):
        self.c, self.g = check, group

    def true(self, what, value, detail=""):
        self.c.true(self.g, what, value, detail)

    def eq(self, what, expected, got, rtol=None):
        if rtol is not None and isinstance(expected, float):
            self.c.true(self.g, what, abs(expected - got) <= rtol * max(1.0, abs(expected)),
                        "{} vs {}".format(expected, got))
        else:
            self.c.true(self.g, what, expected == got, "{!r} vs {!r}".format(expected, got))

    def done(self):
        pass


def full_rows(items, anchors, fbr, strata) -> list:
    """N2's direct rows on the environment: the full-window reading at t = 0."""
    import n2_pricing as n2

    rows = []
    for it in items:
        if it["om_stage_cert"] != "qual":
            continue
        a = anchors[(it["instance_id"], it["frozen_seed"])]
        r = OrderedDict(
            dataset="direct", row_id=it["item_id"], item_id=it["item_id"],
            primary_class=it["primary_class"], subclass=it["subclass"], stratum=it["stratum"],
            instance_id=it["instance_id"], arm="", thinking="", mode="", repeat="",
            quality_visible=it["quality_visible"], n_ops=it["n_ops"], split=it["split"],
            constraining=bool(it["om_constraining"]), obj=it["om_obj"], lb_cert=it["om_lb"],
            gap_cert=it["om_gap"], fingerprint=it["om_fp"], ref1=float(a["wwt_original_bh"]),
            g_cert_anchor=float(a["gap"]), ref2=it["om_ref2"],
            reference_from=it["om_ref2_from"])
        n2.prices(r)
        rows.append(r)
    binfo = n2.base_info(fbr, strata)
    for r in rows:
        n2.attach_oracle(r, fbr, binfo)
        n2.errors(r)
    return rows


def stopped_by(rec_stop, price, design) -> bool:
    """A design stops an item when the guard stops it before the quality stage or it refers."""
    if rec_stop:
        return True
    if design == "G-FEAS":
        return False
    if design in UNIONS:
        a, b = design.split("|")
        return stopped_by(False, price, a) or stopped_by(False, price, b)
    p = price.get(design)
    return p is not None and p > SETTINGS[design]


REFER_DESIGNS = ("G-FEAS",) + DESIGNS + UNIONS


def referral_shares(rows_all, prices_of_row, pre_stop_of_row) -> OrderedDict:
    """Per design and class: share of items the design stops (Table 10 per design)."""
    out = OrderedDict()
    for g in REFER_DESIGNS:
        for cls in ("all",) + D.CLASSES:
            rs = [r for r in rows_all if cls == "all" or r["primary_class"] == cls]
            k = sum(1 for r in rs if stopped_by(pre_stop_of_row(r), prices_of_row(r), g))
            out[(g, cls)] = {"n": len(rs), "k": k, "share": (k / len(rs)) if rs else None}
    return out


def pricing_cells(pr, prefix_dataset=None) -> OrderedDict:
    """Headline cells of a pricing table: per truth and gate, under/over shares and median."""
    out = OrderedDict()
    for label in ("absolute", "marginal"):
        for g in DESIGNS:
            r = D.prow(pr, label, "all", g)
            if r is None:
                continue
            out[(label, g)] = {k: r[k] for k in ("priced", "covered", "under_n", "under_share",
                                                 "over_n", "over_share", "e_median_lo",
                                                 "e_median_hi", "e_max_hi", "e_min_lo")}
        for sp in ("sequencing_only", "field_changing"):
            r = D.prow(pr, label, sp, "D-REL2")
            if r is not None:
                out[(label, "D-REL2|" + sp)] = {"under_share": r["under_share"],
                                                "priced": r["priced"]}
    for st in D.STRATA:
        r = D.prow(pr, "absolute", "all", "D-REL2", "stratum", st)
        if r is not None:
            out[("absolute", "D-REL2|" + st)] = {"e_median_lo": r["e_median_lo"],
                                                 "e_median_hi": r["e_median_hi"],
                                                 "under_share": r["under_share"],
                                                 "priced": r["priced"]}
    return out


WIN_CELLS = (("absolute", "rule_miss"), ("absolute", "cert_miss"), ("absolute", "certm_miss"),
             ("absolute", "union_miss"), ("marginal", "cert_fr"), ("marginal", "certm_fr"),
             ("marginal", "rule_fr"), ("marginal", "certm_miss"), ("marginal", "unionm_fr"),
             ("marginal", "rule_miss"), ("absolute", "cert_fr"), ("absolute", "rule_fr"))


def win_cells(wins) -> OrderedDict:
    out = OrderedDict()
    for st in ("all",) + D.STRATA:
        for delta in (0.10, 0.20):
            for label, nm in WIN_CELLS:
                w = D.wrow(wins, label, delta, st)
                if w is None:
                    continue
                den = w["oracle_costly"] if nm.endswith("miss") else w["oracle_cheap"]
                out[(st, delta, label, nm)] = {"n": w[nm + "_n"], "den": den,
                                               "rate": w[nm + "_rate"]}
    return out


def refgap_full(refgap_rows, by_stratum, cert_by) -> OrderedDict:
    out = OrderedDict()
    for st in ("all",) + D.STRATA:
        rs = [r for r in refgap_rows if r["covered"] and (st == "all" or r["stratum"] == st)]
        med = by_stratum.get(st, (None, None))
        out[st] = {"n": len(rs), "median_lo": med[0], "median_hi": med[1],
                   "max_lo": max((r["ref_gap_lo"] for r in rs), default=None),
                   "max_hi": max((r["ref_gap_hi"] for r in rs), default=None),
                   "zero": sum(1 for r in rs if r["ref_gap_hi"] <= 1e-12),
                   "cert_anchor_gap_median": cert_by.get(st)}
    return out


def refgap_known(iss, td_br) -> tuple:
    """N11's Table 15 on K: anchor gap of each issuable item's (instance, t_d) board."""
    gaps, certg = defaultdict(list), defaultdict(list)
    for r in iss:
        if r["ref1"] is None:
            continue
        certg["all"].append(r["g_cert_anchor"])
        certg[r["stratum"]].append(r["g_cert_anchor"])
        b = td_br.get((r["instance_id"], r["t_d"], D.BASE_FP))
        if b is None:
            continue
        lo, up, _p = D.ends(b)
        g = (D.gfun(r["ref1"], up), D.gfun(r["ref1"], lo))
        gaps["all"].append(g)
        gaps[r["stratum"]].append(g)
    by, cert_by, out = {}, {}, OrderedDict()
    for st in ("all",) + D.STRATA:
        gs = gaps.get(st, [])
        med = (D.median([g[0] for g in gs]), D.median([g[1] for g in gs])) if gs else (None, None)
        by[st] = med
        cert_by[st] = D.median(certg.get(st, []))
        out[st] = {"n": len(gs), "median_lo": med[0], "median_hi": med[1],
                   "max_lo": max((g[0] for g in gs), default=None),
                   "max_hi": max((g[1] for g in gs), default=None),
                   "zero": sum(1 for g in gs if g[1] <= 1e-12),
                   "cert_anchor_gap_median": cert_by[st]}
    return by, cert_by, out


def td_brackets_env(name, smoke=False) -> dict:
    by = {}
    boards = D.read_jsonl(stage_dir(name, "census", smoke) / "boards.jsonl")
    lb2_tot = {(b["iid"], float(b["t_d"]), b["fp"]):
               sum(tv["lb2"] for tv in b["trades"].values()) + b["running_const"] for b in boards}
    for b in D.read_jsonl(stage_dir(name, "oracle", smoke) / "dt_brackets.jsonl"):
        if b["complete"]:
            b = dict(b)
            b["lb2_total"] = lb2_tot.get((b["iid"], float(b["t_d"]), b["fp"]))
            by[(b["iid"], float(b["t_d"]), b["fp"])] = b
    return by


def soundness_max(rows, key="e_hi_G-CERT"):
    eh = [r[key] for r in rows if r.get(key) is not None]
    return (max(eh) if eh else None), (D.pctl(eh, 95) if eh else None)


def json_key(k):
    return "|".join(str(x) for x in k) if isinstance(k, tuple) else str(k)


def jsonable(d):
    if isinstance(d, dict):
        return OrderedDict((json_key(k), jsonable(v)) for k, v in d.items())
    if isinstance(d, (list, tuple)):
        return [jsonable(x) for x in d]
    if isinstance(d, set):
        return sorted(d)
    return d


def cmd_analyse(args) -> int:
    import n2_pricing as n2
    import n11_forecast as F

    name = args.env
    pin()
    activate(name)
    smoke = bool(args.smoke)
    gates = stage_gate(name, "census", "oracle", "forecast", smoke=smoke)
    t0 = time.time()
    out_dir = stage_dir(name, "analysis", smoke)
    out_dir.mkdir(parents=True, exist_ok=True)
    check = D.Checker()
    n2c = N2Check(check, "E5")
    pub = load_suite_items(check)
    strata = strata_of(pub)
    items = D.read_jsonl(stage_dir(name, "census", smoke) / "items.jsonl")
    items_by = {r["item_id"]: r for r in items}
    anchors = env_anchors(name, smoke)
    fbr = {(b["instance_id"], b["fingerprint"]): b
           for b in D.read_jsonl(stage_dir(name, "oracle", smoke) / "full_brackets.jsonl")}
    td_br = td_brackets_env(name, smoke)
    if smoke:
        keep = {r["instance_id"] for r in items}
        strata = {k: v for k, v in strata.items() if k in keep}
    boot = n2.Boot(set(strata), n2.SEED, n2.B_BOOT)
    M = OrderedDict()            # metrics (JSON)

    # ================================================== full-window reading (t = 0)
    rows = full_rows(items, anchors, fbr, strata)
    cov = sum(1 for r in rows if r["covered"])
    check.true("E9", "every full-window row is covered", cov == len(rows), (cov, len(rows)))
    sound = n2.soundness(rows, n2c, "direct_env", n2.SOUND_TOL_DIRECT)

    def cls_group(r):
        return [r["primary_class"]] + (["V4qv"] if r["primary_class"] == "V4" and
                                       r["quality_visible"] else [])
    groupings = [("all", lambda r: ["all"]), ("stratum", lambda r: [r["stratum"]]),
                 ("class", cls_group)]
    pr_full = n2.pricing_table(rows, "direct", groupings)
    anchors_plain = {iid: anchors[(iid, "")]["wwt_original_bh"] for iid in strata}
    anchor_gaps = {(iid, fk): a["gap"] for (iid, fk), a in anchors.items()}
    refgap_rows, rg_by, crg_by = n2.reference_gap(fbr, anchors_plain, anchor_gaps, strata,
                                                  N2Check(check, "E5"))
    wins_full = n2.wins_table(rows, "direct", DG14, rg_by, crg_by)
    disp_full = n2.disposition_table(rows, "direct", DG14, {}, boot)
    omax, op95 = soundness_max(rows)
    pre_stop_full = (lambda r: r["om_term_cert"] in D.STOP_TERMS and r["om_stage_cert"] != "qual")
    full_price = {r["item_id"]: {g: r["p_" + g] for g in DESIGNS} for r in rows}
    pub_items = [r for r in items]
    ref_full = referral_shares(pub_items, lambda r: full_price.get(r["item_id"], {}), pre_stop_full)
    gcert_term = Counter((r["primary_class"], r["om_term_cert"] in D.STOP_TERMS) for r in pub_items)
    for cls in D.CLASSES:
        n_ = gcert_term[(cls, True)] + gcert_term[(cls, False)]
        check.true("E7", "G-CERT referral share per class equals the terminal count ({})".format(cls),
                   ref_full[("G-CERT", cls)]["k"] == gcert_term[(cls, True)] and
                   ref_full[("G-CERT", cls)]["n"] == n_)
    relabel = OrderedDict()
    for delta in (0.05, 0.10, 0.20):
        v3 = [r for r in rows if r["primary_class"] == "V3" and r["covered"]]
        st_ = [n2.costly_state(r, delta, "absolute") for r in v3]
        relabel[delta] = {"n": len(v3), "costly": sum(1 for s in st_ if s == 1),
                          "undecided": sum(1 for s in st_ if s is None)}
    nb = [fbr[k] for k in sorted(fbr)]
    w = [float(b["width_rel"]) for b in nb]
    oracle_full = {"brackets": len(nb), "proved": sum(1 for b in nb if b["proved_all"]),
                   "width_median": D.pctl(w, 50), "width_p95": D.pctl(w, 95), "width_max": max(w),
                   "upper_at_lb2": sum(1 for b in nb if abs(float(b["upper"]) - float(b["lb2_total"]))
                                       <= 1e-6 * max(1.0, float(b["upper"])))}
    M["full"] = OrderedDict(
        rows=len(rows), covered=cov, soundness=sound, overprice_max=omax, overprice_p95=op95,
        pricing=pricing_cells(pr_full), refgap=refgap_full(refgap_rows, rg_by, crg_by),
        wins=win_cells(wins_full), referral=ref_full, relabel=relabel, oracle=oracle_full,
        n_items=len(pub_items))

    # ================================================== decision-time reading (K at t_d)
    krows = k_rows_env(items, anchors, td_br, fbr)
    iss = [r for r in krows if r["issuable"]]
    priced = [r for r in iss if r["priced"]]
    need = set()
    for r in priced:
        need.add((r["instance_id"], r["t_d"], r["fingerprint"]))
        need.add((r["instance_id"], r["t_d"], D.BASE_FP))
    check.true("E9", "every needed decision-time board is bracketed", all(k in td_br for k in need),
               len([k for k in need if k not in td_br]))
    for r in priced:
        if r["covered"]:
            check.true("E5", "obj_K >= board lower on " + r["item_id"],
                       r["obj"] >= float(r["opt_lower"]) - TOL)
            check.true("E5", "certificate bound <= board upper on " + r["item_id"],
                       r["lb_cert"] <= float(r["opt_upper"]) + TOL)
    sound_k = n2.soundness(priced, N2Check(check, "E5"), "direct_td_env", n2.SOUND_TOL_DIRECT)
    groupings_k = [("all", lambda r: ["all"]), ("stratum", lambda r: [r["stratum"]]),
                   ("class", lambda r: [r["primary_class"]])]
    pr_k = n2.pricing_table(priced, "direct_td", groupings_k)
    rgk_by, crgk_by, rgk = refgap_known(iss, td_br)
    wins_k = n2.wins_table(priced, "direct_td", DG14, rgk_by, crgk_by)
    real_rows = D.as_truth(priced, "real_")
    wins_real = n2.wins_table(real_rows, "direct_td_realised", DG14, rgk_by, crgk_by)
    omax_k, op95_k = soundness_max(priced)
    # forecast rows need the original-field truth and the K-reading fields
    for r in priced:
        it = items_by[r["item_id"]]
        r["frozen_seed_key"] = it["frozen_seed"]
        for k in ("om_term_cert", "om_stage_cert", "om_obj_orig", "an_obj_orig"):
            r[k] = it.get(k)
        for g in DESIGNS:
            r["om_p_" + g] = it.get("om_p_" + g)
        a = anchors[(r["instance_id"], it["frozen_seed"])]
        r["damage_adj"] = None if r["rw_obj"] is None else r["rw_obj"] - float(a["wwt_adjusted_bh"])
    F.attach_orig_truth(priced, fbr, anchors)
    prices = F.load_prices(stage_dir(name, "forecast", smoke) / "prices_direct.jsonl")
    rp = F.reading_prices(priced, prices, {}, ("K", "F2"))
    missing = [r["item_id"] for r in priced if rp["F2"][r["item_id"]]["agg"] is None or
               rp["F2"][r["item_id"]]["agg"]["n_futures"] == 0]
    check.true("AF9", "every priced item has its F2 price", not missing, missing[:5])
    cons = F.consequence(priced, rp, boot, groups=("all", "stratum", "class", "split2"),
                         aggs=("median",))
    dmg = F.damage_stats(priced, rp)
    dpi = OrderedDict()
    for g in ("G-FEAS",) + DESIGNS + UNIONS:
        if g == "G-FEAS":
            continue
        dd = F.damage_per_instruction(iss, rp, boot, design=g)
        for (rd, cls), v in dd.items():
            dpi[(rd, g, cls)] = v
    # G-FEAS: every applicable proposal applies (its damage counts)
    for rd in ("K", "F2"):
        for cls in ("all", "V3", "benign"):
            rs = [r for r in iss if cls == "all" or r["primary_class"] == cls]
            vals = [r["damage_if_applied"] if r["terminal_feas"] == "applied_uncertified" and
                    r["damage_if_applied"] is not None else 0.0 for r in rs]
            dpi[(rd, "G-FEAS", cls)] = {"n": len(rs), "mean": (sum(vals) / len(rs)) if rs else None,
                                        "lo": None, "hi": None}
    addb = F.addition_b(priced, rp, prices, {})
    pr_rec = {r["item_id"]: r for r in priced}

    def pre_stop_k(r):
        return (not r["priced"]) and r["terminal"] in D.STOP_TERMS

    def price_k(r):
        return {g: r["p_" + g] for g in DESIGNS} if r["priced"] else {}

    def price_f2(r):
        if not r["priced"]:
            return {}
        rec = rp["F2"][r["item_id"]]
        return {g: rec.get("p_" + g) for g in DESIGNS}
    ref_k = referral_shares(iss, price_k, pre_stop_k)
    ref_f2 = referral_shares(iss, price_f2, pre_stop_k)
    und_f2 = Counter()
    for r in priced:
        for g in rp["F2"][r["item_id"]]["undecided"]:
            und_f2[g] += 1
    agree = sum(1 for r in iss if (r["terminal"] in D.STOP_TERMS) ==
                (r["terminal_pub"] in D.STOP_TERMS))
    cons_cells = OrderedDict()
    for rd in ("K", "F2"):
        for g in DESIGNS + UNIONS:
            for delta in (0.10, 0.20):
                for st in ("all",) + D.STRATA:
                    c = F.crow(cons, truth="orig", delta=delta, reading=rd, agg="median", gate=g,
                               group_kind="all" if st == "all" else "stratum",
                               group="all" if st == "all" else st)
                    if c is None:
                        continue
                    cons_cells[(rd, g, delta, st)] = {k: c[k] for k in (
                        "costly", "miss", "miss_share", "cheap", "fr", "fr_share", "mc_undecided",
                        "miss_lo", "miss_hi", "fr_lo", "fr_hi")}
    dmg_cells = OrderedDict()
    for x in dmg:
        if x["truth"] == "orig" and x["group"] in ("All", "VThree", "Benign", "DamagingSeqAll",
                                                   "Seq", "Field"):
            dmg_cells[(x["reading"], x["group"])] = {k: x[k] for k in (
                "n", "spearman", "under2", "n_under2", "median_err", "shortfall", "pred_total",
                "real_total")}
    addb_cells = OrderedDict()
    for x in addb:
        addb_cells[(x["reading"], x["gate"])] = {k: x[k] for k in (
            "under", "under_n", "under_share", "benign", "benign_referred",
            "benign_referred_share", "costly_ten", "missed_ten", "miss_share_ten", "cheap_ten",
            "false_ref_ten", "false_ref_share_ten", "anchor_gap_median")}
    M["known"] = OrderedDict(
        issuable=len(iss), priced=len(priced), soundness=sound_k, overprice_max=omax_k,
        overprice_p95=op95_k, pricing=pricing_cells(pr_k), refgap=rgk, wins=win_cells(wins_k),
        wins_real=win_cells(wins_real), referral=ref_k,
        agreement={"n": len(iss), "k": agree, "share": agree / len(iss) if iss else None},
        floor_share=(sum(1 for r in priced if r["floor_cert"]) / len(priced)) if priced else None,
        consequence={k: v for k, v in cons_cells.items() if k[0] == "K"},
        damage={k: v for k, v in dmg_cells.items() if k[0] == "K"},
        damage_per_instruction={k: v for k, v in dpi.items() if k[0] == "K"},
        addition_b={k: v for k, v in addb_cells.items() if k[0] == "K"})
    M["forecast"] = OrderedDict(
        S=int(json.loads((N11F / "smoke_decision.json").read_text())["S"]), priced=len(priced),
        referral=ref_f2, mc_undecided=dict(und_f2),
        consequence={k: v for k, v in cons_cells.items() if k[0] == "F2"},
        damage={k: v for k, v in dmg_cells.items() if k[0] == "F2"},
        damage_per_instruction={k: v for k, v in dpi.items() if k[0] == "F2"},
        addition_b={k: v for k, v in addb_cells.items() if k[0] == "F2"})
    M["census"] = json.loads((stage_dir(name, "census", smoke) / "meta.json").read_text())["summary"]
    M["walls"] = {st: json.loads((stage_dir(name, st, smoke) / ("run_meta.json" if st == "oracle"
                                                              else "meta.json")).read_text()).get("wall_s")
                  for st in ("census", "oracle", "forecast")}
    M["timing"] = json.loads((stage_dir(name, "oracle", smoke) / "run_meta.json").read_text()).get("timing")

    # ================================================== identity at f = 1 (E6)
    ident = None
    if name == "cal" and not smoke:
        ident = identity_analysis(check, rows, priced, pr_full, wins_full, pr_k, wins_k, wins_real,
                                  cons, addb, dmg, M)
    rows_out = env_rows(name, M)
    D.write_csv_rows(out_dir / "rows.csv", rows_out, ["N12 {} ({}): metric rows".format(name, VERSION)],
                     list(rows_out[0].keys()))
    D.write_json(out_dir / "metrics.json", jsonable(M))
    for nm, table in (("pricing_full.csv", pr_full), ("pricing_known.csv", pr_k),
                      ("wins_full.csv", wins_full), ("wins_known.csv", wins_k + wins_real),
                      ("consequence.csv", cons)):
        D.write_csv_rows(out_dir / nm, table, ["N12 {} ({})".format(name, VERSION)],
                         list(table[0].keys()))
    D.write_csv_rows(out_dir / "rows_full.csv", rows, ["N12 {} full-window rows".format(name)],
                     [k for k in rows[0].keys() if not k.startswith("_")])
    rep = check.report()
    check.fatal(out_dir / "assertions.json", {"finished": D.now_iso(), "identity": ident,
                                              "outputs": {}, "gates": gates, "smoke": smoke})
    print("[n12 analyse {}] PASS: {} checks, {:.0f}s".format(name, rep["n_checks"], time.time() - t0),
          flush=True)
    return 0


def pct_macro_value(published, key):
    v = published.get(key)
    if v is None:
        return None
    try:
        return float(v.replace("\\%", "").replace("%", "")) / 100.0
    except ValueError:
        return None


def identity_analysis(check, rows, priced, pr_full, wins_full, pr_k, wins_k, wins_real, cons, addb,
                      dmg, M) -> dict:
    """E6 (cal): the analysed rows and cells reproduce the published N2, N11 and N11F outputs."""
    out = {}
    # N2 direct rows, value by value (the CSV carries 6 decimals)
    n2r = {r["row_id"]: r for r in D.read_csv_comments(ANALYSIS / "N2_rows_direct.csv")}
    check.true("E6", "same full-window population as N2 (1,635 rows)",
               len(rows) == len(n2r) == 1635 and {r["row_id"] for r in rows} == set(n2r),
               (len(rows), len(n2r)))
    cols = ["obj", "lb_cert", "gap_cert", "g_cert_anchor", "ref1", "ref2", "opt_lower", "opt_upper",
            "g_lo", "g_hi", "m_lo", "m_hi"] + ["p_" + g for g in DESIGNS] + \
        ["{}_{}_{}".format(e, s, g) for e in ("e", "em") for s in ("lo", "hi") for g in DESIGNS]
    n = 0
    worst = 0.0
    for r in rows:
        o = n2r.get(r["row_id"])
        if o is None:
            continue
        check.true("E6", "fingerprint equals N2 on " + r["row_id"], r["fingerprint"] == o["fingerprint"])
        for c in cols:
            a, b = r.get(c), D.num_or_none(o.get(c))
            n += 1
            if a is None or b is None:
                check.true("E6", "{} defined alike in N2 on {}".format(c, r["row_id"]),
                           a is None and b is None, "{} vs {}".format(a, b))
                continue
            worst = max(worst, abs(a - b))
            check.true("E6", "{} equals N2 on {}".format(c, r["row_id"]), abs(a - b) <= 2e-6,
                       "{} vs {}".format(a, b))
    out["n2_cells"] = n
    out["n2_max_abs_dev"] = worst
    pubm = D.load_macros(("analysis/N2_macros.tex", "analysis/N11_macros.tex",
                          "analysis/N11F_macros.tex"))
    # N2 headline macros (formatted as N2 formats them)
    for g, tok in D.GATE_TOKEN.items():
        for label, ttag in (("absolute", ""), ("marginal", "Marg")):
            r = D.prow(pr_full, label, "all", g)
            key = "nTwoDirect{}{}UnderShare".format(ttag, tok)
            if key in pubm and r and r["under_share"] is not None:
                check.true("E6", "{} reproduced".format(key),
                           "{:.1f}\\%".format(100 * r["under_share"]) == pubm[key],
                           "{} vs {}".format(r["under_share"], pubm[key]))
            key = "nElevenNTwoDirect{}{}UnderShare".format(ttag, tok)
            rk = D.prow(pr_k, label, "all", g)
            if key in pubm and rk and rk["under_share"] is not None:
                check.true("E6", "{} reproduced".format(key),
                           "{:.1f}\\%".format(100 * rk["under_share"]) == pubm[key],
                           "{} vs {}".format(rk["under_share"], pubm[key]))
    check.true("E6", "nTwoDirectCertOverpriceMax reproduced",
               "{:.3f}".format(M["full"]["overprice_max"]) == pubm.get("nTwoDirectCertOverpriceMax"),
               "{} vs {}".format(M["full"]["overprice_max"], pubm.get("nTwoDirectCertOverpriceMax")))
    for label, ttag, nm, ntok in (("absolute", "", "rule_miss", "RelTwoMissRate"),
                                  ("absolute", "", "cert_miss", "CertMissRate"),
                                  ("absolute", "", "certm_miss", "CertMMissRate"),
                                  ("marginal", "Marg", "cert_fr", "CertFalseReferralRate")):
        for delta, dtok in ((0.10, "Ten"), (0.20, "Twenty")):
            w = D.wrow(wins_full, label, delta, "all")
            key = "nTwoDirect{}{}{}".format(ttag, ntok, dtok)
            if key in pubm and w is not None and w[nm + "_rate"] is not None:
                check.true("E6", "{} reproduced".format(key),
                           "{:.1f}\\%".format(100 * w[nm + "_rate"]) == pubm[key],
                           "{} vs {}".format(w[nm + "_rate"], pubm[key]))
            wk = D.wrow(wins_k, label, delta, "all")
            key = "nElevenNTwoDirect{}{}{}".format(ttag, ntok, dtok)
            if key in pubm and wk is not None and wk[nm + "_rate"] is not None:
                check.true("E6", "{} reproduced".format(key),
                           "{:.1f}\\%".format(100 * wk[nm + "_rate"]) == pubm[key],
                           "{} vs {}".format(wk[nm + "_rate"], pubm[key]))
    # N11 decision-time rows and Stage 3 forecast tables, cell by cell
    n11r = {r["item_id"]: r for r in D.read_csv_comments(ANALYSIS / "N11_rows_direct.csv")
            if r["set"] == "published"}
    m = 0
    for r in priced:
        o = n11r.get(r["item_id"])
        check.true("E6", "N11 row exists for " + r["item_id"], o is not None)
        if o is None:
            continue
        for c in ["obj", "lb_cert", "gap_cert", "ref1", "ref2", "opt_lower", "opt_upper", "g_lo",
                  "g_hi", "m_lo", "m_hi", "rw_obj", "rw_obj_orig", "real_g_lo", "real_g_hi",
                  "real_m_lo", "real_m_hi"] + ["p_" + g for g in DESIGNS]:
            a, b = r.get(c), D.num_or_none(o.get(c))
            m += 1
            if a is None or b is None:
                check.true("E6", "{} defined alike in N11 on {}".format(c, r["item_id"]),
                           a is None and b is None, "{} vs {}".format(a, b))
                continue
            check.true("E6", "{} equals N11 on {}".format(c, r["item_id"]), abs(a - b) <= 2e-6,
                       "{} vs {}".format(a, b))
    out["n11_cells"] = m
    fcons = {}
    for y in D.read_csv_comments(ANALYSIS / "N11F_consequence.csv"):
        fcons[(y["truth"], round(float(y["delta"]), 6), y["reading"], y["agg"], y["gate"],
               y["group_kind"], y["group"])] = y
    k = 0
    for x in cons:
        if x["group_kind"] not in ("all", "stratum"):
            continue
        o = fcons.get((x["truth"], round(x["delta"], 6), x["reading"], x["agg"], x["gate"],
                       x["group_kind"], str(x["group"])))
        check.true("E6", "Stage 3 consequence row exists {}".format(
            (x["truth"], x["delta"], x["reading"], x["gate"], x["group"])), o is not None)
        if o is None:
            continue
        k += 1
        for c in ("costly", "miss", "cheap", "fr", "mc_undecided"):
            check.true("E6", "consequence {} equals Stage 3 {}".format(
                c, (x["truth"], x["delta"], x["reading"], x["gate"], x["group"])),
                int(float(o[c])) == x[c], "{} vs {}".format(x[c], o[c]))
    out["n11f_consequence_rows"] = k
    fadd = {(y["reading"], y["gate"]): y for y in D.read_csv_comments(ANALYSIS / "N11F_addition_b.csv")}
    for x in addb:
        o = fadd.get((x["reading"], x["gate"]))
        check.true("E6", "Stage 3 addition-B row exists {}".format((x["reading"], x["gate"])),
                   o is not None)
        if o is None:
            continue
        for c in ("under", "under_n", "benign_referred", "missed_ten", "false_ref_ten"):
            if x[c] is None:
                continue
            check.true("E6", "addition-B {} equals Stage 3 {}".format(c, (x["reading"], x["gate"])),
                       int(float(o[c])) == x[c], "{} vs {}".format(x[c], o[c]))
    fd = D.read_csv_comments(ANALYSIS / "N11F_damage.csv")
    j = 0
    for x in dmg:
        o = next((y for y in fd if y["truth"] == x["truth"] and y["reading"] == x["reading"]
                  and y["group"] == x["group"]), None)
        if o is None:
            continue
        j += 1
        check.true("E6", "damage n_under2 equals Stage 3 {}".format((x["truth"], x["reading"],
                                                                    x["group"])),
                   int(float(o["n_under2"])) == x["n_under2"] and int(float(o["n"])) == x["n"])
    out["n11f_damage_rows"] = j
    return out


# --------------------------------------------------------------------------- #
# Rows, macros and the summary                                                 #
# --------------------------------------------------------------------------- #
def env_rows(name, M) -> list:
    """Long rows: one per (reading, table, quantity, design, group)."""
    out = []

    def add(reading, table, quantity, design, group, value, n=None, den=None, lo=None, hi=None):
        out.append(OrderedDict(env=name, window=ENVS[name]["window"], crew=ENVS[name]["crew"],
                               reading=reading, table=table, quantity=quantity, design=design,
                               group=group, value=value, n=n, den=den, lo=lo, hi=hi))
    for reading, P in (("full", M["full"]), ("known", M["known"])):
        for (label, g), c in P["pricing"].items():
            for q in ("under_share", "over_share"):
                if c.get(q) is not None:
                    add(reading, "Table 14", "{}_{}".format(label, q), g, "all", c[q],
                        c.get(q.replace("share", "n")), c.get("priced"))
            if c.get("e_median_lo") is not None:
                add(reading, "Table 14", "{}_median_error".format(label), g, "all",
                    0.5 * (c["e_median_lo"] + c["e_median_hi"]), lo=c["e_median_lo"],
                    hi=c["e_median_hi"])
            if c.get("e_max_hi") is not None:
                add(reading, "Table 14", "{}_max_error".format(label), g, "all", c["e_max_hi"])
        add(reading, "Table 14", "certificate_overprice_max", "G-CERT", "all", P["overprice_max"])
        add(reading, "Table 14", "certificate_overprice_p95", "G-CERT", "all", P["overprice_p95"])
        add(reading, "Table 14", "certificate_min_margin", "G-CERT", "all",
            P["soundness"]["min_margin_vs_optimistic_end"])
        for st, c in P["refgap"].items():
            add(reading, "Table 15", "anchor_gap_median", "ATC dispatch", st,
                None if c["median_lo"] is None else 0.5 * (c["median_lo"] + c["median_hi"]),
                c["n"], lo=c["median_lo"], hi=c["median_hi"])
            add(reading, "Table 15", "anchor_gap_max", "ATC dispatch", st, c["max_hi"], c["n"])
            add(reading, "Table 15", "certified_anchor_gap_median", "G-CERT", st,
                c["cert_anchor_gap_median"])
        for (st, delta, label, nm), c in P["wins"].items():
            add(reading, "Table 16 pricing panel", "{}_{}_rate_delta{:g}".format(label, nm, delta),
                nm.split("_")[0], st, c["rate"], c["n"], c["den"])
        if reading == "known":
            for (st, delta, label, nm), c in P["wins_real"].items():
                add(reading, "Table 16 consequence panel (realised, adjusted fields)",
                    "{}_{}_rate_delta{:g}".format(label, nm, delta), nm.split("_")[0], st,
                    c["rate"], c["n"], c["den"])
        for (g, cls), c in P["referral"].items():
            add(reading, "Table 10", "stopped_share", g, cls, c["share"], c["k"], c["n"])
    for reading, P in (("known", M["known"]), ("forecast_F2", M["forecast"])):
        for k, c in P["consequence"].items():
            rd, g, delta, st = k
            add(reading, "consequence (realised marginal cost, original fields)",
                "miss_share_delta{:g}".format(delta), g, st, c["miss_share"], c["miss"],
                c["costly"], c["miss_lo"], c["miss_hi"])
            add(reading, "consequence (realised marginal cost, original fields)",
                "false_referral_share_delta{:g}".format(delta), g, st, c["fr_share"], c["fr"],
                c["cheap"], c["fr_lo"], c["fr_hi"])
        for (rd, grp), c in P["damage"].items():
            add(reading, "predicted damage (D-ABS) vs realised damage", "under_by_2bh_share",
                "D-ABS", grp, c["under2"], c["n_under2"], c["n"])
            add(reading, "predicted damage (D-ABS) vs realised damage", "spearman", "D-ABS", grp,
                c["spearman"], c["n"])
            add(reading, "predicted damage (D-ABS) vs realised damage", "shortfall_bh", "D-ABS",
                grp, c["shortfall"], c["n"])
        for (rd, g, cls), c in P["damage_per_instruction"].items():
            add(reading, "realised damage per issuable instruction (bh)", "mean_damage", g, cls,
                c["mean"], c["n"], lo=c["lo"], hi=c["hi"])
        for (rd, g), c in P["addition_b"].items():
            add(reading, "under-pricing against the realised cost", "under_share", g, "all",
                c["under_share"], c["under"], c["under_n"])
            add(reading, "benign referrals", "benign_referred_share", g, "benign",
                c["benign_referred_share"], c["benign_referred"], c["benign"])
    for (g, cls), c in M["forecast"]["referral"].items():
        add("forecast_F2", "Table 10", "stopped_share", g, cls, c["share"], c["k"], c["n"])
    a = M["known"]["agreement"]
    add("known", "disposition agreement with the full window", "share", "G-CERT", "all",
        a["share"], a["k"], a["n"])
    return out


def g(d, *path):
    for p in path:
        if d is None:
            return None
        d = d.get(p) if isinstance(d, dict) else None
    return d


def pctx(x, d=1):
    return "n/a" if x is None else "{:.{}f}%".format(100.0 * x, d)


def pct_tex(x, d=1):
    return "n/a" if x is None else "{:.{}f}\\%".format(100.0 * x, d)


def numx(x, d=3):
    return "n/a" if x is None else "{:.{}f}".format(x, d)


DES_TOK = {"G-FEAS": "Feas", "G-CERT": "Cert", "G-CERT-M": "CertM", "D-REL1": "RelOne",
           "D-REL2": "RelTwo", "D-ABS": "Abs", "G-CERT|D-REL2": "UnionCert",
           "G-CERT-M|D-REL2": "Union"}
CLS_TOK = {"benign": "Benign", "V1": "VOne", "V2": "VTwo", "V3": "VThree", "V4": "VFour",
           "V5": "VFive", "V6": "VSix", "all": "All"}
ST_TOK = {"all": "Pooled", "c09_storm2_w80": "Primary", "c10_storm2_w80": "Confirmation",
          "c10_replay_400": "Buildings"}


def directions(M) -> OrderedDict:
    """The paper's headline directions, each a test on one environment's metrics."""
    f, k, fc = M["full"], M["known"], M["forecast"]
    out = OrderedDict()

    def put(key, text, ok, value):
        out[key] = {"claim": text, "holds": None if ok is None else bool(ok), "value": value}

    cu = g(f, "pricing", "absolute|G-CERT", "under_share")
    put("sound_full", "the certificate never under-prices the full-window cost (G-CERT absolute "
        "under share 0, minimum margin >= 0)",
        cu is not None and cu == 0.0 and (f["soundness"]["min_margin_vs_optimistic_end"] or 0) >= -1e-6,
        "under {}, min margin {}".format(pctx(cu), numx(f["soundness"]["min_margin_vs_optimistic_end"],
                                                        4)))
    ku = g(k, "pricing", "absolute|G-CERT", "under_share")
    put("sound_known", "on K the certificate never under-prices the decision-time cost",
        ku is not None and ku == 0.0, "under {}".format(pctx(ku)))
    ra = g(f, "pricing", "absolute|D-REL2", "under_share")
    rm = g(f, "pricing", "marginal|D-REL2", "under_share")
    co = g(f, "pricing", "absolute|G-CERT", "over_share")
    put("rule_inherits_gap", "the hand-written rule under-prices the absolute cost more often than "
        "the marginal cost (it inherits the dispatcher's gap)",
        None if ra is None or rm is None else ra > rm,
        "D-REL2 under {} absolute, {} marginal".format(pctx(ra), pctx(rm)))
    put("rule_vs_cert", "the rule under-prices the absolute cost more often than the certificate "
        "over-prices it", None if ra is None or co is None else ra > co,
        "D-REL2 under {} vs G-CERT over {}; G-CERT over-pricing max {}".format(
            pctx(ra), pctx(co), numx(f["overprice_max"])))
    rg = {st: g(f, "refgap", st, "median_hi") for st in D.STRATA}
    er = {st: g(f, "pricing", "absolute|D-REL2|" + st, "e_median_lo") for st in D.STRATA}
    top = max(rg, key=lambda s: -1 if rg[s] is None else rg[s])
    low = min(er, key=lambda s: 1e9 if er[s] is None else er[s])
    put("gap_orders_error", "the stratum with the largest dispatcher gap is where the rule's "
        "absolute median error is most negative (choose a gate by the dispatcher's gap)",
        top == low, "largest gap {} ({}), most negative D-REL2 error {}".format(
            ST_TOK[top], pctx(rg[top]), ST_TOK[low]))
    wr = g(f, "wins", "all|0.1|absolute|rule_miss", "rate")
    wc = g(f, "wins", "all|0.1|absolute|cert_miss", "rate")
    put("table16_rule_misses_more", "at delta = 0.10 the rule misses more full-window-costly "
        "proposals than the certificate (absolute truth)",
        None if wr is None or wc is None else wr > wc,
        "D-REL2 {} vs G-CERT {}".format(pctx(wr), pctx(wc)))
    v3c = g(f, "referral", "G-CERT|V3", "share")
    v3f = g(f, "referral", "G-FEAS|V3", "share")
    bc = g(f, "referral", "G-CERT|benign", "share")
    bf = g(f, "referral", "G-FEAS|benign", "share")
    put("table10_cert_adds_v3", "the certificate stops V3 items the feasibility gate passes, at a "
        "smaller added benign stop share (Table 10)",
        None if None in (v3c, v3f, bc, bf) else (v3c - v3f) > (bc - bf) and v3c > v3f,
        "V3 {} (G-FEAS {}), benign {} (G-FEAS {})".format(pctx(v3c), pctx(v3f), pctx(bc), pctx(bf)))
    ag = g(k, "agreement", "share")
    put("known_agreement", "priced on K, the certificate gives the full-information disposition on "
        "most issuable items", None if ag is None else ag >= 0.5, pctx(ag))
    sp = g(k, "damage", "K|VThree", "spearman")
    put("known_rank", "the decision-time predicted damage ranks the realised damage of V3 "
        "proposals (positive rank correlation)", None if sp is None else sp > 0, numx(sp))
    uk = g(k, "damage", "K|DamagingSeqAll", "under2")
    uf = g(fc, "damage", "F2|DamagingSeqAll", "under2")
    put("forecast_damage", "F2 lowers the share of damaging sequencing proposals whose predicted "
        "damage falls short by more than 2 bh", None if uk is None or uf is None else uf < uk,
        "K {} -> F2 {}".format(pctx(uk), pctx(uf)))
    mk = g(k, "consequence", "K|G-CERT-M|0.1|all", "miss_share")
    mf = g(fc, "consequence", "F2|G-CERT-M|0.1|all", "miss_share")
    bfr = g(fc, "addition_b", "F2|G-CERT-M", "benign_referred_share")
    put("forecast_dispositions", "under F2 the dispositions stay where K puts them (G-CERT-M miss "
        "share within 5 points of K) and G-CERT-M refers no benign item",
        None if mk is None or mf is None or bfr is None else abs(mf - mk) <= 0.05 and bfr == 0.0,
        "G-CERT-M miss K {} -> F2 {}; benign referred under F2 {}".format(pctx(mk), pctx(mf),
                                                                          pctx(bfr)))
    return out


def cmd_report(args) -> int:
    pin()
    have = []
    for name in ENVS:
        p = env_dir(name) / "analysis" / "assertions.json"
        if p.is_file() and json.loads(p.read_text()).get("status") == "PASS":
            have.append(name)
    if "cal" not in have:
        raise SystemExit("REFUSING TO RUN: the calibrated environment is not analysed")
    Ms = OrderedDict((n, json.loads((env_dir(n) / "analysis" / "metrics.json").read_text()))
                     for n in have)
    status = "COMPLETE" if len(have) == len(ENVS) else "PARTIAL"
    rows = []
    for n in have:
        rows += list(D.read_csv_comments(env_dir(n) / "analysis" / "rows.csv"))
    hdr = ["N12 gate sensitivity to the environment's derived settings ({}), status {} "
           "(environments: {})".format(VERSION, status, ", ".join(have)),
           "generated by code/scripts/n12_env_sensitivity.py report; readings: full (t = 0, "
           "full-window oracle), known (K at t_d = t_known, decision-time oracle and realised "
           "consequence), forecast_F2 (K plus sampled later arrivals, S = 20)"]
    D.write_csv_rows(ANALYSIS / "N12_rows.csv", rows, hdr, list(rows[0].keys()))
    dirs = OrderedDict((n, directions(Ms[n])) for n in have)
    lines = ["% N12 macros ({}), status {}; generated by code/scripts/n12_env_sensitivity.py "
             "report".format(VERSION, status)]
    if status != "COMPLETE":
        lines.append("% PARTIAL: not every environment is analysed; not for publication")
    names = set()

    def mac(n, q, v):
        nm = "nTwelve" + ENVS[n]["token"] + q
        if not nm.isalpha() or nm in names:
            raise SystemExit("bad or duplicate macro name {}".format(nm))
        names.add(nm)
        lines.append("\\newcommand{\\" + nm + "}{" + str(v) + "}")
    for n, M in Ms.items():
        f, k, fc = M["full"], M["known"], M["forecast"]
        mac(n, "FullCertOverpriceMax", numx(f["overprice_max"]))
        mac(n, "KnownCertOverpriceMax", numx(k["overprice_max"]))
        for reading, P, rtok in (("full", f, "Full"), ("known", k, "Known")):
            for label, ltok in (("absolute", ""), ("marginal", "Marg")):
                for gname in DESIGNS:
                    c = g(P, "pricing", "{}|{}".format(label, gname))
                    if c and c.get("under_share") is not None:
                        mac(n, "{}{}{}UnderShare".format(rtok, ltok, DES_TOK[gname]),
                            pct_tex(c["under_share"]))
                    if c and c.get("over_share") is not None:
                        mac(n, "{}{}{}OverShare".format(rtok, ltok, DES_TOK[gname]),
                            pct_tex(c["over_share"]))
            for st in ("all",) + D.STRATA:
                c = g(P, "refgap", st)
                if c and c.get("median_hi") is not None:
                    mac(n, "{}RefGap{}Median".format(rtok, ST_TOK[st]), pct_tex(c["median_hi"]))
            for nm, ltok in (("rule_miss", "RelTwoMiss"), ("cert_miss", "CertMiss"),
                             ("certm_miss", "CertMMiss")):
                c = g(P, "wins", "all|0.1|absolute|" + nm)
                if c and c.get("rate") is not None:
                    mac(n, "{}{}RateTen".format(rtok, ltok), pct_tex(c["rate"]))
            c = g(P, "wins", "all|0.1|marginal|cert_fr")
            if c and c.get("rate") is not None:
                mac(n, "{}MargCertFalseReferralRateTen".format(rtok), pct_tex(c["rate"]))
            for gname in ("G-FEAS", "G-CERT", "G-CERT-M", "D-REL2"):
                for cls in ("V3", "benign"):
                    c = g(P, "referral", "{}|{}".format(gname, cls))
                    if c and c.get("share") is not None:
                        mac(n, "{}{}{}StoppedShare".format(rtok, DES_TOK[gname], CLS_TOK[cls]),
                            pct_tex(c["share"]))
        mac(n, "KnownAgreementShare", pct_tex(g(k, "agreement", "share")))
        mac(n, "KnownIssuable", D.group_int(k["issuable"]))
        mac(n, "KnownPriced", D.group_int(k["priced"]))
        mac(n, "FullRows", D.group_int(f["rows"]))
        for gname in DESIGNS + UNIONS:
            for rd, P, rtok in (("K", k, "Known"), ("F2", fc, "Forecast")):
                c = g(P, "consequence", "{}|{}|0.1|all".format(rd, gname))
                if c and c.get("miss_share") is not None:
                    mac(n, "{}Real{}MissShareTen".format(rtok, DES_TOK[gname]),
                        pct_tex(c["miss_share"]))
                if c and c.get("fr_share") is not None:
                    mac(n, "{}Real{}FalseReferralShareTen".format(rtok, DES_TOK[gname]),
                        pct_tex(c["fr_share"]))
        for gname in ("G-FEAS",) + DESIGNS + UNIONS:
            for cls in ("V3", "benign"):
                c = g(fc, "referral", "{}|{}".format(gname, cls))
                if c and c.get("share") is not None:
                    mac(n, "Forecast{}{}StoppedShare".format(DES_TOK[gname], CLS_TOK[cls]),
                        pct_tex(c["share"]))
            c = g(fc, "addition_b", "F2|" + gname)
            if c and c.get("benign_referred_share") is not None:
                mac(n, "Forecast{}BenignReferredShare".format(DES_TOK[gname]),
                    pct_tex(c["benign_referred_share"]))
        for rd, P, rtok in (("K", k, "Known"), ("F2", fc, "Forecast")):
            c = g(P, "damage", rd + "|DamagingSeqAll")
            if c and c.get("under2") is not None:
                mac(n, rtok + "DamagingSeqUnderTwoShare", pct_tex(c["under2"]))
            c = g(P, "damage", rd + "|VThree")
            if c and c.get("spearman") is not None:
                mac(n, rtok + "VThreeSpearman", numx(c["spearman"], 2))
        held = sum(1 for d in dirs[n].values() if d["holds"])
        mac(n, "DirectionsHeld", "{} of {}".format(held, len(dirs[n])))
    (ANALYSIS / "N12_macros.tex").write_text("\n".join(lines) + "\n")
    (ANALYSIS / "N12_summary.md").write_text(summary_md(Ms, dirs, status, have))
    print("[n12 report] {}: {} environments, {} macros, {} rows".format(status, len(have),
                                                                        len(names), len(rows)),
          flush=True)
    return 0


def summary_md(Ms, dirs, status, have) -> str:
    cols = list(Ms)
    head = ["design"] + ["{} ({})".format(n, ENVS[n]["label"]) for n in cols]
    L = ["# N12: gate sensitivity to the environment's derived settings\n",
         "Status: **{}** ({} of {} environments analysed). Generated by "
         "`code/scripts/n12_env_sensitivity.py report` ({}). Every number is in "
         "`analysis/N12_rows.csv` and the headline cells are macros `\\nTwelve<Setting><Quantity>` "
         "in `analysis/N12_macros.tex`.\n".format(status, len(have), len(ENVS), VERSION),
         "## What was computed\n",
         "Five environments: the calibrated one and four perturbed ones (windows: due = release + "
         "f SLA[p] on every order, f = 0.5 and 1.5; crews: max(1, round(n f)) technicians per trade, "
         "f = 0.75 and 1.25). Each environment's 60 instances are derived in memory from the "
         "manifest-verified instances_v10 snapshot (hashes in `results/n12_env/manifest_n12.json`); "
         "the scaled SLA clock is bound in every process, so set_priority and reassign_window "
         "restart it. On each environment the direct benchmark (canonical proposal of every suite "
         "item; labels and thresholds frozen at tau = 0.20, D-REL1 0.02, D-REL2 0.02, D-ABS "
         "0.8119) is read three ways: (1) the full-window reading at t = 0 against new full-window "
         "oracle brackets (oracle_v1's recipe, 60 s per trade, 4 workers); (2) the decision-time "
         "reading on K at t_d = t_known against the decision-time oracle on K and the realised "
         "consequence on the original fields; (3) the forecast reading F2 at S = 20 (Stage 3's "
         "smoke decision, top-up to 50 near a threshold).\n",
         "The calibrated column is computed by the same code path with f = 1 and reproduces the "
         "published reading (assertion E6): N11's census rows and boards, N2's direct rows and "
         "headline cells, oracle_v1's brackets, N11's decision-time brackets and Stage 3's F2 "
         "prices, exactly.\n"]

    def table(title, note, rowspecs):
        L.append("### " + title + "\n")
        if note:
            L.append(note + "\n")
        body = []
        for label, fn in rowspecs:
            body.append([label] + [fn(Ms[n]) for n in cols])
        L.append(D.md_table(head, body))
        L.append("")

    def share_cell(c, kk="share", nk="k", dk="n"):
        if not c or c.get(kk) is None:
            return "n/a"
        return "{} ({}/{})".format(pctx(c[kk]), c.get(nk), c.get(dk))

    L.append("## Full-window reading (t = 0, against the full-window oracle)\n")
    for label, ltxt in (("absolute", "absolute cost"), ("marginal", "marginal cost")):
        table("Table 14, under-pricing share ({}; error < -0.05)".format(ltxt), None,
              [(gname, lambda M, gname=gname, label=label: share_cell(
                  g(M, "full", "pricing", "{}|{}".format(label, gname)), "under_share", "under_n",
                  "priced")) for gname in DESIGNS])
        table("Table 14, over-pricing share ({}; error > +0.05)".format(ltxt), None,
              [(gname, lambda M, gname=gname, label=label: share_cell(
                  g(M, "full", "pricing", "{}|{}".format(label, gname)), "over_share", "over_n",
                  "priced")) for gname in DESIGNS])
        table("Table 14, median signed error ({})".format(ltxt), None,
              [(gname, lambda M, gname=gname, label=label: (lambda c: "n/a" if not c else
                                                             D.ival(c["e_median_lo"], c["e_median_hi"]))(
                  g(M, "full", "pricing", "{}|{}".format(label, gname)))) for gname in DESIGNS])
    table("Certificate soundness and over-pricing (full window)", None,
          [("G-CERT max over-pricing (e_hi)", lambda M: numx(g(M, "full", "overprice_max"))),
           ("G-CERT p95 over-pricing", lambda M: numx(g(M, "full", "overprice_p95"))),
           ("G-CERT minimum margin to the optimistic end",
            lambda M: numx(g(M, "full", "soundness", "min_margin_vs_optimistic_end"), 4)),
           ("rows priced (reached the quality stage)", lambda M: g(M, "full", "rows")),
           ("oracle brackets / proved", lambda M: "{} / {}".format(g(M, "full", "oracle", "brackets"),
                                                                   g(M, "full", "oracle", "proved"))),
           ("bracket width median / max", lambda M: "{} / {}".format(
               pctx(g(M, "full", "oracle", "width_median"), 2),
               pctx(g(M, "full", "oracle", "width_max"), 2))),
           ("V3 oracle-costly share (absolute, delta 0.05)", lambda M: (
               lambda c: "n/a" if not c else "{} ({}/{})".format(pctx(c["costly"] / c["n"]),
                                                                 c["costly"], c["n"]))(
               g(M, "full", "relabel", "0.05")))])
    table("Table 15, anchor gap of the ATC dispatch (median [lo, hi] over instances)",
          "Rows are strata; the last rows give D-REL2's absolute median error per stratum.",
          [("anchor gap, " + ST_TOK[st], lambda M, st=st: (lambda c: "n/a" if not c or
                                                         c["median_lo"] is None else
                                                         D.ival(100 * c["median_lo"],
                                                                100 * c["median_hi"], 1) + "%")(
              g(M, "full", "refgap", st))) for st in ("all",) + D.STRATA] +
          [("D-REL2 median error, " + ST_TOK[st], lambda M, st=st: (
              lambda c: "n/a" if not c else D.ival(c["e_median_lo"], c["e_median_hi"]))(
              g(M, "full", "pricing", "absolute|D-REL2|" + st))) for st in D.STRATA])
    win_specs = [("D-REL2 miss (abs)", "absolute|rule_miss"), ("G-CERT miss (abs)", "absolute|cert_miss"),
                 ("G-CERT-M miss (abs)", "absolute|certm_miss"),
                 ("G-CERT or D-REL2 miss (abs)", "absolute|union_miss"),
                 ("D-REL2 false referral (marg)", "marginal|rule_fr"),
                 ("G-CERT false referral (marg)", "marginal|cert_fr"),
                 ("G-CERT-M false referral (marg)", "marginal|certm_fr"),
                 ("G-CERT-M or D-REL2 false referral (marg)", "marginal|unionm_fr")]
    for delta in ("0.1", "0.2"):
        table("Table 16 pricing panel, pooled, delta = {} (miss: share of oracle-costly proposals "
              "accepted; false referral: share of oracle-cheap proposals referred)".format(delta),
              None, [(lab, lambda M, key=key, delta=delta: (
                  lambda c: "n/a" if not c or c["rate"] is None else "{} ({}/{})".format(
                      pctx(c["rate"]), c["n"], c["den"]))(
                  g(M, "full", "wins", "all|{}|{}".format(delta, key)))) for lab, key in win_specs])
    for cls in ("V3", "benign", "V4", "V6"):
        table("Table 10, stopped share of {} items (all {} items of the class)".format(cls, cls), None,
              [(gname, lambda M, gname=gname, cls=cls: share_cell(
                  g(M, "full", "referral", "{}|{}".format(gname, cls))))
               for gname in REFER_DESIGNS])
    L.append("## Decision-time reading (K at t_d = t_known)\n")
    for label, ltxt in (("absolute", "absolute cost"), ("marginal", "marginal cost")):
        table("Table 14 on K, under-pricing share ({}, against the decision-time oracle)".format(ltxt),
              None, [(gname, lambda M, gname=gname, label=label: share_cell(
                  g(M, "known", "pricing", "{}|{}".format(label, gname)), "under_share", "under_n",
                  "priced")) for gname in DESIGNS])
    table("Certificate on K", None,
          [("G-CERT max over-pricing (e_hi)", lambda M: numx(g(M, "known", "overprice_max"))),
           ("issuable / priced", lambda M: "{} / {}".format(g(M, "known", "issuable"),
                                                            g(M, "known", "priced"))),
           ("floor regime share (LB_K < 1 bh)", lambda M: pctx(g(M, "known", "floor_share"))),
           ("disposition agreement with the full window (G-CERT)",
            lambda M: share_cell(g(M, "known", "agreement")))])
    table("Table 15 on K, anchor gap of the anchor dispatch on K (median upper end)", None,
          [(ST_TOK[st], lambda M, st=st: pctx(g(M, "known", "refgap", st, "median_hi"), 2))
           for st in ("all",) + D.STRATA])
    table("Table 16 on K, pricing panel, pooled, delta = 0.10", None,
          [(lab, lambda M, key=key: (lambda c: "n/a" if not c or c["rate"] is None else
                                     "{} ({}/{})".format(pctx(c["rate"]), c["n"], c["den"]))(
              g(M, "known", "wins", "all|0.1|" + key))) for lab, key in win_specs])
    table("Consequence on K: miss share at delta = 0.10 against the realised marginal cost "
          "(original fields)", None,
          [(gname, lambda M, gname=gname: (lambda c: "n/a" if not c or c["miss_share"] is None
                                           else "{} ({}/{})".format(pctx(c["miss_share"]), c["miss"],
                                                                    c["costly"]))(
              g(M, "known", "consequence", "K|{}|0.1|all".format(gname))))
           for gname in DESIGNS + UNIONS])
    table("Consequence on K: false-referral share at delta = 0.10 (realised marginal cost)", None,
          [(gname, lambda M, gname=gname: (lambda c: "n/a" if not c or c["fr_share"] is None
                                           else "{} ({}/{})".format(pctx(c["fr_share"]), c["fr"],
                                                                    c["cheap"]))(
              g(M, "known", "consequence", "K|{}|0.1|all".format(gname))))
           for gname in DESIGNS + UNIONS])
    table("Realised damage per issuable V3 instruction on K (bh, original fields; a referral adds 0)",
          None, [(gname, lambda M, gname=gname: (lambda c: "n/a" if not c or c["mean"] is None
                                                 else "{} [{}, {}]".format(numx(c["mean"], 2),
                                                                           numx(c["lo"], 2),
                                                                           numx(c["hi"], 2)))(
              g(M, "known", "damage_per_instruction", "K|{}|V3".format(gname))))
              for gname in ("G-FEAS",) + DESIGNS + UNIONS])
    for cls in ("V3", "benign"):
        table("Table 10 on K, stopped share of issuable {} items".format(cls), None,
              [(gname, lambda M, gname=gname, cls=cls: share_cell(
                  g(M, "known", "referral", "{}|{}".format(gname, cls)))) for gname in REFER_DESIGNS])
    L.append("## Forecast reading F2 (K plus sampled later arrivals, S = 20)\n")
    for cls in ("V3", "benign"):
        table("F2, stopped (referred) share of issuable {} items".format(cls), None,
              [(gname, lambda M, gname=gname, cls=cls: share_cell(
                  g(M, "forecast", "referral", "{}|{}".format(gname, cls)))) for gname in REFER_DESIGNS])
    table("F2, benign false referrals among priced benign items", None,
          [(gname, lambda M, gname=gname: share_cell(g(M, "forecast", "addition_b", "F2|" + gname),
                                                     "benign_referred_share", "benign_referred",
                                                     "benign")) for gname in ("G-FEAS",) + DESIGNS])
    table("F2, miss share at delta = 0.10 (realised marginal cost, original fields)", None,
          [(gname, lambda M, gname=gname: (lambda c: "n/a" if not c or c["miss_share"] is None
                                           else "{} ({}/{})".format(pctx(c["miss_share"]), c["miss"],
                                                                    c["costly"]))(
              g(M, "forecast", "consequence", "F2|{}|0.1|all".format(gname))))
           for gname in DESIGNS + UNIONS])
    table("F2, false-referral share at delta = 0.10 (realised marginal cost)", None,
          [(gname, lambda M, gname=gname: (lambda c: "n/a" if not c or c["fr_share"] is None
                                           else "{} ({}/{})".format(pctx(c["fr_share"]), c["fr"],
                                                                    c["cheap"]))(
              g(M, "forecast", "consequence", "F2|{}|0.1|all".format(gname))))
           for gname in DESIGNS + UNIONS])
    table("F2, under-pricing share against the realised cost (N2's 0.05 rule; D-ABS: below the "
          "realised damage by > 2 bh)", None,
          [(gname, lambda M, gname=gname: share_cell(g(M, "forecast", "addition_b", "F2|" + gname),
                                                     "under_share", "under", "under_n"))
           for gname in DESIGNS])
    table("Predicted-damage accuracy (D-ABS against the realised damage, original fields)",
          "Share of damaging sequencing proposals (realised damage > 2 bh) under-predicted by more "
          "than 2 bh, and the Spearman rank correlation on V3, K and F2.",
          [("K, damaging sequencing, under by > 2 bh", lambda M: share_cell(
              g(M, "known", "damage", "K|DamagingSeqAll"), "under2", "n_under2", "n")),
           ("F2, damaging sequencing, under by > 2 bh", lambda M: share_cell(
               g(M, "forecast", "damage", "F2|DamagingSeqAll"), "under2", "n_under2", "n")),
           ("K, V3 Spearman", lambda M: numx(g(M, "known", "damage", "K|VThree", "spearman"), 2)),
           ("F2, V3 Spearman", lambda M: numx(g(M, "forecast", "damage", "F2|VThree", "spearman"), 2)),
           ("F2 items MC-undecided (any design)", lambda M: json.dumps(g(M, "forecast", "mc_undecided")))])
    L.append("## What persists\n")
    body = []
    keys = list(next(iter(dirs.values())).keys())
    for key in keys:
        row = [dirs[cols[0]][key]["claim"]]
        for n in cols:
            d = dirs[n][key]
            row.append("{} ({})".format({True: "holds", False: "fails", None: "n/a"}[d["holds"]],
                                        d["value"]))
        body.append(row)
    L.append(D.md_table(["headline claim"] + ["{} ({})".format(n, ENVS[n]["label"]) for n in cols],
                        body))
    L.append("")
    allp = [key for key in keys if all(dirs[n][key]["holds"] for n in cols)]
    fails = [(key, [n for n in cols if dirs[n][key]["holds"] is False]) for key in keys]
    fails = [(k_, ns) for k_, ns in fails if ns]
    txt = ("Of the {} headline directions, {} hold in every environment analysed ({}). ".format(
        len(keys), len(allp), ", ".join(cols)))
    if fails:
        txt += "The directions that do not hold everywhere: " + "; ".join(
            "{} fails under {}".format(dirs[cols[0]][k_]["claim"], ", ".join(ENVS[n]["label"]
                                                                            for n in ns))
            for k_, ns in fails) + "."
    else:
        txt += "No direction changes sign under the perturbed windows or crews."
    L.append(txt + "\n")
    L.append("## Run record\n")
    body = []
    for n in cols:
        M = Ms[n]
        t = M.get("timing") or {}
        body.append([n, numx(g(M, "walls", "census"), 0), numx(g(M, "walls", "oracle"), 0),
                     numx(g(M, "walls", "forecast"), 0),
                     "{} solves, {} budget-limited, {} invalid".format(
                         g(t, "full", "solves"), g(t, "full", "budget_limited"),
                         g(t, "full", "invalid")),
                     numx(g(t, "full", "foreign_share_max_budget_limited"), 3),
                     "{} solves".format(g(t, "dt", "solves"))])
    L.append(D.md_table(["environment", "census s", "oracle s", "forecast s", "full-window solves",
                         "max foreign_share (budget-limited)", "decision-time solves"], body))
    L.append("")
    return "\n".join(L)


# --------------------------------------------------------------------------- #
# The pipeline: one environment after another, stage after stage, on 8-11    #
# --------------------------------------------------------------------------- #
def cmd_pipeline(args) -> int:
    import subprocess

    envs = args.envs.split(",")
    py = sys.executable
    env_vars = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                    OPENBLAS_NUM_THREADS="1")
    first_perturbed_done = False
    for name in envs:
        t0 = time.time()
        for st in ("census", "oracle", "forecast", "analyse"):
            done = env_dir(name) / (st if st != "analyse" else "analysis") / "assertions.json"
            if done.is_file() and json.loads(done.read_text()).get("status") == "PASS" and \
                    not json.loads(done.read_text()).get("smoke"):
                print("[n12 pipeline] {} {}: already PASS, skipped".format(name, st), flush=True)
                continue
            cmd = ["taskset", "-c", "8-11", py, __file__, st, "--env", name]
            print("[n12 pipeline] {} {}: {}".format(name, st, " ".join(cmd)), flush=True)
            rc = subprocess.call(cmd, env=env_vars)
            if rc != 0:
                print("[n12 pipeline] STOP: {} {} exited {}".format(name, st, rc), flush=True)
                return rc
        wall = time.time() - t0
        rec = {"env": name, "wall_s": wall, "finished": D.now_iso()}
        D.append_jsonl(OUT / "pipeline_walls.jsonl", rec)
        print("[n12 pipeline] {} finished in {:.0f}s".format(name, wall), flush=True)
        if name in PERTURBED and not first_perturbed_done:
            first_perturbed_done = True
            if wall > STOP_RULE_S:
                print("[n12 pipeline] STOP RULE: the first perturbed environment took {:.0f}s "
                      "(> 3 h); reporting before continuing".format(wall), flush=True)
                subprocess.call(["taskset", "-c", "8-11", py, __file__, "report"], env=env_vars)
                return 3
    subprocess.call(["taskset", "-c", "8-11", py, __file__, "report"], env=env_vars)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nm in ("census", "oracle", "forecast", "analyse"):
        p = sub.add_parser(nm)
        p.add_argument("--env", required=True, choices=list(ENVS))
        p.add_argument("--workers", type=int, default=WORKERS)
        p.add_argument("--instances", default="")
        p.add_argument("--budget", type=float, default=BUDGET_S)
        p.add_argument("--no-selfcheck", action="store_true")
        p.add_argument("--smoke", action="store_true",
                       help="read and write results/n12_env/<env>/smoke/<stage>")
        p.add_argument("--limit", type=int, default=0, help="oracle: brackets this call (smoke)")
    sub.add_parser("report")
    p = sub.add_parser("pipeline")
    p.add_argument("--envs", default=",".join(ENVS))
    args = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    if args.cmd == "census":
        return cmd_census(args)
    if args.cmd == "oracle":
        return cmd_oracle(args)
    if args.cmd == "forecast":
        return cmd_forecast(args)
    if args.cmd == "analyse":
        return cmd_analyse(args)
    if args.cmd == "report":
        return cmd_report(args)
    return cmd_pipeline(args)


if __name__ == "__main__":
    sys.exit(main())
