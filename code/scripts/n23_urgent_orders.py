#!/usr/bin/env python3
"""N23: urgent orders made late by a proposal, and intervals for the stress-test table.

Design pre-specified before the run.  Two parts.

PART A  The gate prices a proposal by the weighted tardiness of the whole board, so a proposal
        that makes one urgent order late while the board's total stays within the tolerance can
        be applied (limitations row "Whole-board price", the manuscript text).
        The stored logs hold no per-order completion times (N20 block F), so every one of the
        1,356 priced reference proposals of the direct benchmark is replayed here with the
        project's dispatcher (n11_decision_time.gen_price, unchanged) at its decision instant:
          realised   the full window from t_d with the proposal (N11's realised run) and without
                     it (the no-proposal run: the schedule the realised damage is measured
                     against; its weighted tardiness equals the no-AI anchor's, N11 assertion
                     A7, and its start and end time of every order equal the anchor schedule's,
                     asserted here per site);
          K          the known board at t_d with and without the proposal (N11's dt and an);
          FI         the full-information board at t_d (every order of the window except those
                     completed at t_d, n11_forecast's FI reading) with and without the proposal.
        Before any number is formed, the weighted tardiness summed from the per-order
        completions on the original values equals, for every proposal, the stored totals
        (items.jsonl rw_obj_orig, rw0_obj_orig, dt_obj_orig, an_obj_orig; the rule_anchor.json
        no-AI weighted tardiness; fullinfo_direct.jsonl and anchors_direct.jsonl obj_orig; the
        damage_orig_bh of analysis/N11_rows_forecast.csv); any mismatch aborts the run.
        Lateness is read on the ORIGINAL due dates and priority classes.  An order is newly late
        when it finishes on time without the proposal and late with it (C - d > 1e-9 bh).  An
        urgent order is an order of priority class 1 or 2 (Section sec:prob-env and Table
        tab:env-provenance: class 1 = response target 24 hours, SLA 8 bh, weight 8; class 2 =
        72 hours, SLA 24 bh, weight 4; classes 3 and 4 = 14 and 30 days, SLA 80 and 171.4 bh,
        weights 2 and 1; planned maintenance takes class 4).  An urgent-late proposal makes at
        least one urgent order newly late in the realised run.
        Tables (delta = tau = 0.20, headline counts at delta = 0.10, pooled and per stratum):
          1  proposals with at least one newly late urgent order, costly / low-cost;
          2  the six designs at their own thresholds (G-CERT, G-CERT with the second price,
             G-CERT-M, D-REL1, D-REL2, D-ABS): of the proposals each applies, the urgent-late
             ones, the low-cost ones among them (the limitations-row cases), and the largest
             tardiness added to one urgent order (median, 90th percentile, maximum);
          3  tables 1 and 2 split by operation type;
          4  the per-order rule "refer when, on the known board at t_d, the proposal makes an
             order of class 1 or 2 newly late", alone and with the gate: costly applied,
             low-cost referred, urgent-late applied, with the cluster-bootstrap 95% intervals;
          5  tables 2 to 4 for the full-information reading (summary only).
PART B  Table tab:e1 (the manuscript text): for every share, per model configuration,
        the 95% cluster-bootstrap interval by instance (n2.Boot: seed 20261026, 20,000
        replicates, 60 instance clusters, repeats pooled, as N16 block F and N18 block D) and
        the minimum and maximum over repeats.  The point values are computed with
        n19_known_prompt_eval's records and measures on the published files (its
        --check-published path) and asserted against the table's macros
        (\\nElevenTabEOne<Arm><Column> in manuscript/macros_n11.tex for seven columns and
        \\nSixteenFidelity<Arm>Share in manuscript/macros_n16.tex for the fidelity column).

THE FOUR LAUNCH ANSWERS
  1. Purpose: backing numbers for the "Whole-board price" limitations row (Part A) and the
     intervals of Table tab:e1 (Part B); every number goes to analysis/N23_macros.tex
     (copied to manuscript/macros_n23.tex) and analysis/N23_summary.md.
  2. Ideal result: every stored total and every table macro reproduces (run-fatal); the new
     counts are whatever the replay gives, reported whether or not they flatter the gate.
  3. Contamination: read-only on every input; deterministic dispatcher replays and recounts of
     stored logs only (no solver, no time budget, no model call, no GPU), so core contention
     changes wall time only.
  4. Data accuracy: the population is n20's 1,356 priced proposals (n20.build, its headline
     asserted by n16.section0 and n20.section0); the replay inputs are N11's census inputs
     (the suite through suite_gate, the instance snapshot, the canonical operations), and every
     replayed board is tied to its stored total before use.

Reuse: n20_stratum_abs.py is loaded from its source with its core allowance set to cores 12-13
in memory (its three occurrences asserted); through it n16_robustness.py and
n18_further_checks.py (allowances set to 12-13 in memory, files untouched) and n13_fromlogs.py.
n19_known_prompt_eval.py is imported (it allows cores 12-13).  Labels: n13.costly_of; flags:
n13.refers and n20's two_k / two_f (the second price); bootstrap: n2.Boot via n13 (seed
20261026, 20,000 replicates, 60 instance clusters).  The frozen files n16_robustness.py,
n13_fromlogs.py, n11_decision_time.py and n10_field_change.py are never edited.  Part B's
context is built from the same loaders as n19.Ctx without the known-board dry-run prompt file,
which only the known-board checks read.

Outputs: analysis/N23_macros.tex (prefix \\nTwentyThree, one comment line per macro), copied to
manuscript/macros_n23.tex; analysis/N23_rows.csv (one row per priced proposal);
analysis/N23_summary.md.
Run:       OMP_NUM_THREADS=1 taskset -c 12-13 python \\
               code/scripts/n23_urgent_orders.py
Self-test: the same with --selftest: every computation and assertion of the run, plus a second
           code path that recomputes two numbers per table from the raw files (csv / json
           modules, numpy arrays of the per-order completions, a bootstrap written here with the
           n2 seed and draw order) and a fresh replay of sample proposals in the parent
           process; writes nothing.  The default run performs the same comparisons and records
           them in the summary.
Version: l1-n23-urgent-1
"""
import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_v] = "1"

import csv  # noqa: E402
import json  # noqa: E402
import multiprocessing as mp  # noqa: E402
import shutil  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import types  # noqa: E402
from collections import Counter, OrderedDict, defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

ALLOWED_CORES = {12, 13}
_aff = set(os.sched_getaffinity(0))
if not _aff <= ALLOWED_CORES and not os.environ.get("CERTIGATE_ANY_CORES"):
    raise SystemExit("REFUSING TO RUN: affinity {} is not inside cores 12-13 "
                     "(run under taskset -c 12-13)".format(sorted(_aff)))
CORES = sorted(_aff)

SCRIPTS_DIR = Path(__file__).resolve().parent
for _p in (str(SCRIPTS_DIR.parent), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


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


# n20 holds its own guard and the two strings it writes into n16's and n18's sources: all three
# move to {12, 13}; n16 then writes {12, 13} into n13 (n13's own allowance).
n20 = _load_module("n20_stratum_abs", [("ALLOWED_CORES = {10, 11}", "ALLOWED_CORES = {12, 13}", 3)])
n16 = n20.n16
n18 = n20.n18
n13 = n20.n13
D = n13.D
np = n13.np
n2 = n13.n2
import n8_causal as n8  # noqa: E402
import n19_known_prompt_eval as N19  # noqa: E402  (allows cores 12-13; no work at import)

VERSION = "l1-n23-urgent-1"
ROOT = n13.ROOT
ANALYSIS = n13.ANALYSIS
RESULTS = n13.RESULTS
OUT_TEX = ANALYSIS / "N23_macros.tex"
OUT_MANU = ROOT / "manuscript" / "macros_n23.tex"
OUT_MD = ANALYSIS / "N23_summary.md"
OUT_CSV = ANALYSIS / "N23_rows.csv"
IN23 = OrderedDict([
    ("n15_macros", ANALYSIS / "N15_macros.tex"),
    ("n16_macros", ANALYSIS / "N16_macros.tex"),
    ("macros_n11_manu", ROOT / "manuscript" / "macros_n11.tex"),
    ("macros_n16_manu", ROOT / "manuscript" / "macros_n16.tex"),
    ("table_e1", ROOT / "manuscript" / "drafts" / "s6_e1.tex"),
    ("limitations", ROOT / "manuscript" / "drafts" / "app_limitations.tex"),
    ("env_appendix", ROOT / "manuscript" / "drafts" / "app_env.tex"),
    ("formulation", ROOT / "manuscript" / "drafts" / "s3_formulation.tex"),
    ("rows_e1", RESULTS / "n11_e2e" / "rows_e1_primary.jsonl"),
    ("sites_e1", RESULTS / "n11_e2e" / "sites.jsonl"),
    ("items_e2e", RESULTS / "n11_e2e" / "items.jsonl"),
])

#: Inputs the public release does not carry (four manuscript drafts). A missing one
#: is recorded as "not shipped" in the provenance block, and the run goes on.
NOT_SHIPPED_OK = ('table_e1', 'limitations', 'env_appendix', 'formulation')


def input_sha256(key, path):
    """The SHA-256 of an input, or "not shipped" for one the public release does not carry."""
    if key in NOT_SHIPPED_OK and not Path(path).is_file():
        return "not shipped"
    return n13.sha256(path)

TAU = n13.TAU
EPS = 1e-9                     # late when C - d > EPS bh (schedule times carry four decimals)
GROW_BH = 1.0                  # "tardiness grows by more than 1 business hour"
URGENT = (1, 2)
SUM_TOL = 1e-9                 # per-order sum against a stored full-precision total
ANCHOR_TOL = 1e-6              # against rule_anchor.json (N11 assertion A7's tolerance)
CSV_TOL = 1e-6                 # against the six-decimal damage of N11_rows_forecast.csv
DELTAS = OrderedDict([("Twenty", 0.20), ("Ten", 0.10)])
ST_TOK = n13.ST_TOK
POPS = OrderedDict([("Pooled", None)] + [(ST_TOK[s], s) for s in D.STRATA])
POP_NAME = {"Pooled": "pooled", "Primary": "Primary stratum",
            "Confirmation": "Confirmation stratum", "Buildings": "Buildings stratum"}
SPLITS = OrderedDict([("sequencing_only", ("Seq", "sequencing only")),
                      ("field_changing", ("Field", "field edits")),
                      ("empty", ("Empty", "no operation"))])
#: the six designs of Table 2: token, display, K flag, FI flag (the published flags; the second
#: price is n20's two_k / two_f = n16.sp_flag on K and its full-information counterpart).
DESIGNS = OrderedDict([
    ("Cert", ("G-CERT", lambda r: n13.refers(r, "G-CERT"),
              lambda r: n13.refers(r["fi"], "G-CERT"))),
    ("CertTwo", ("G-CERT with the second price", lambda r: r["two_k"], lambda r: r["two_f"])),
    ("CertM", ("G-CERT-M", lambda r: n13.refers(r, "G-CERT-M"),
               lambda r: n13.refers(r["fi"], "G-CERT-M"))),
    ("RelOne", ("D-REL1", lambda r: n13.refers(r, "D-REL1"),
                lambda r: n13.refers(r["fi"], "D-REL1"))),
    ("RelTwo", ("D-REL2", lambda r: n13.refers(r, "D-REL2"),
                lambda r: n13.refers(r["fi"], "D-REL2"))),
    ("Abs", ("D-ABS", lambda r: n13.refers(r, "D-ABS"), lambda r: n13.refers(r["fi"], "D-ABS"))),
])
THRESH = {"Cert": "0.20", "CertTwo": "0.20 and 0.20", "CertM": "0.20", "RelOne": "0.02",
          "RelTwo": "0.02", "Abs": "0.8119 bh"}
#: Table 4 variants: token, display, function (r, reading) -> refers
VARIANTS = OrderedDict([
    ("Rule", "the per-order rule alone"),
    ("Cert", "G-CERT alone (comparison)"),
    ("CertRule", "G-CERT plus the per-order rule"),
    ("CertTwo", "G-CERT with the second price (comparison)"),
    ("CertTwoRule", "G-CERT with the second price plus the per-order rule"),
])

LINES = ["% N23 macros ({}); generated by code/scripts/n23_urgent_orders.py from deterministic "
         "dispatcher replays of the direct benchmark and the logged results (no solve, no model "
         "call); each macro follows a comment line giving its table and definition".format(
             VERSION)]
NAMES = set()
VAL = OrderedDict()
MD = []
NCHECK = [0]
SELF = []
MAXDIFF = defaultdict(float)

grp, pct, pctv, pctp, pctpv, frac = (n16.grp, n16.pct, n16.pctv, n16.pctp, n16.pctpv, n16.frac)


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def check(what, ok, detail=""):
    if not ok:
        raise SystemExit("[n23] ASSERTION FAILED: {} ({})".format(what, str(detail)[:800]))
    NCHECK[0] += 1


def close(what, a, b, tol, key=""):
    d = abs(float(a) - float(b))
    MAXDIFF[what] = max(MAXDIFF[what], d)
    check(what, d <= tol, (key, a, b, d))


def add(name, value, note):
    full = "nTwentyThree" + name
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


def bh2(x):
    return "n/a" if x is None else "{:.2f}".format(x)


def bhm(x):
    return "n/a" if x is None else "{:,.2f}".format(x).replace(",", "{,}")


def ci_str(k, n, lo, hi):
    return "{} [{}, {}]".format(frac(k, n), pctpv(lo), pctpv(hi))


def qdist(xs):
    """(median, 90th percentile, maximum), numpy linear percentiles; None when empty."""
    if not xs:
        return None, None, None
    a = np.asarray(xs, dtype=float)
    med, p90 = (float(v) for v in np.percentile(a, [50, 90]))
    return med, p90, float(a.max())


# --------------------------------------------------------------------------- #
# The replay (worker side)                                                     #
# --------------------------------------------------------------------------- #
_TASKS = []


def order_map(res):
    """Per-order (C, due, weight, class) on the board's original fields and their WT sum."""
    live = res.get("_live") or {}
    if "schedule" not in live:
        return None, None
    adj, sched = live["adjusted"], live["schedule"]
    orig = {wo["id"]: wo for wo in adj.original["work_orders"]}
    out = {}
    tot = 0.0
    for a in sched["assignments"]:
        wo = orig[a["wo"]]
        c, d, w = float(a["end_bh"]), float(wo["due_bh"]), float(wo["weight"])
        tot += w * max(0.0, c - d)
        if a["wo"] in out:
            raise RuntimeError("order {} scheduled twice".format(a["wo"]))
        out[a["wo"]] = (c, d, w, int(wo["priority"]))
    if set(out) != set(orig):
        raise RuntimeError("schedule does not cover the board ({} of {})".format(
            len(out), len(orig)))
    return out, tot


def changed_orders(m_with, m_without):
    """[id, class, due, weight, C without, C with] for every order whose completion differs."""
    if set(m_with) != set(m_without):
        raise RuntimeError("the two schedules hold different orders")
    out = []
    for oid, (cw, d, w, cls) in m_with.items():
        cn, d2, w2, c2 = m_without[oid]
        if (d2, w2, c2) != (d, w, cls):
            raise RuntimeError("original fields differ between the two runs on " + oid)
        if cw != cn:
            out.append([oid, cls, d, w, cn, cw])
    out.sort()
    return out


def slim(res, tot):
    return {"term_feas": res["term_feas"], "stage_cert": res["stage_cert"],
            "obj": res["obj"], "obj_orig": res["obj_orig"], "gap": res["gap"], "lb": res["lb"],
            "sum_orig": tot}


def replay_instance(ti):
    """Every board of one instance's priced proposals, with and without the proposal."""
    from l1adapter import dispatch as dispatch_mod

    task = _TASKS[ti]
    t0 = time.perf_counter()
    inst = D.load_instance(task["path"])
    iid = inst["meta"]["id"]
    baseline = dispatch_mod.dispatch_baseline(inst, "atc", 0)
    by_id = {wo["id"]: wo for wo in inst["work_orders"]}
    import hashlib

    trajs = {fk: n8.trajectory(inst, seed, baseline) for fk, seed in task["seeds"].items()}
    # the trajectory is the no-AI anchor's schedule (its digest equals rule_anchor.json's)
    traj_ok = {fk: hashlib.sha256(dispatch_mod.canonical_schedule_json(tr).encode("utf-8"))
               .hexdigest() == task["digest"][fk] for fk, tr in trajs.items()}
    sites = {}
    out = {"iid": iid, "items": [], "sites": {}}

    def site_for(fk, seed, t_d):
        key = (fk, t_d)
        if key in sites:
            return sites[key]
        traj = trajs[fk]
        state = n8.site_state(inst, traj, t_d, pm_known=True)
        known = n8.known_instance(inst, state)
        kf = D.kf_fix(state, seed)                      # N11 census site_for, kf "fix"
        started = state["completed"] + state["in_progress"]
        k_ids = state["queue"] + state["in_progress"] + state["scheduled"]
        base_p = n8.pin_schedule(baseline, traj, started)
        frozen_r = list(started) + [o for o in seed if o not in set(started)]
        run_ids = list(state["in_progress"])
        done = set(state["completed"])
        fi_board = {k: v for k, v in inst.items() if k != "work_orders"}   # n11_forecast FI
        fi_board["work_orders"] = [wo for wo in inst["work_orders"] if wo["id"] not in done]
        an = D.gen_price(known, D.EMPTY_RAW, kf, base_p, t_d, keep_live=True)
        rw0 = D.gen_price(inst, D.EMPTY_RAW, frozen_r, base_p, t_d, keep_batch=k_ids,
                          keep_live=True)
        fa = D.gen_price(fi_board, D.EMPTY_RAW, kf, base_p, t_d, ref2=False, keep_batch=k_ids,
                         running_ids=run_ids, keep_live=True)
        m_an, t_an = order_map(an)
        m_rw0, t_rw0 = order_map(rw0)
        m_fa, t_fa = order_map(fa)
        tt = {a["wo"]: (a["start_bh"], a["end_bh"]) for a in traj["assignments"]}
        rt = {a["wo"]: (a["start_bh"], a["end_bh"])
              for a in rw0["_live"]["schedule"]["assignments"]}
        s = {"known": known, "kf": kf, "k_ids": k_ids, "base_p": base_p, "frozen_r": frozen_r,
             "run_ids": run_ids, "fi_board": fi_board, "m_an": m_an, "m_rw0": m_rw0,
             "m_fa": m_fa}
        out["sites"]["{}|{:.6f}".format(fk, t_d)] = {
            "fk": fk, "t_d": t_d, "an": slim(an, t_an), "rw0": slim(rw0, t_rw0),
            "fa": slim(fa, t_fa), "n_completed": len(done), "n_running": len(run_ids),
            "n_known": len(known["work_orders"]), "n_fi": len(fi_board["work_orders"]),
            "n_window": len(inst["work_orders"]), "traj_is_anchor": traj_ok[fk],
            "rw0_times_eq_anchor": tt == rt}
        sites[key] = s
        return s

    for it in task["items"]:
        fk, seed = it["fk"], it["seed"]
        starts = {a["wo"]: float(a["start_bh"]) for a in trajs[fk]["assignments"]}
        iss = D.issuability(it, by_id, starts)
        t_d = D.decision_instant_of(iss, "primary")
        s = site_for(fk, seed, t_d)
        raw = json.dumps({"operations": it["ops"]})
        dt = D.gen_price(s["known"], raw, s["kf"], s["base_p"], t_d, ref2=True, keep_live=True,
                         running_ids=s["run_ids"])
        rw = D.gen_price(inst, raw, s["frozen_r"], s["base_p"], t_d, keep_batch=s["k_ids"],
                         keep_live=True)
        fi = D.gen_price(s["fi_board"], raw, s["kf"], s["base_p"], t_d, ref2=True,
                         keep_batch=s["k_ids"], running_ids=s["run_ids"], keep_live=True)
        m_dt, t_dt = order_map(dt)
        m_rw, t_rw = order_map(rw)
        m_fi, t_fi = order_map(fi)
        rec = {"item_id": it["item_id"], "iid": iid, "fk": fk, "t_d": t_d,
               "site": "{}|{:.6f}".format(fk, t_d),
               "dt": slim(dt, t_dt), "rw": slim(rw, t_rw), "fi": slim(fi, t_fi),
               "ch_real": None, "ch_k": None, "ch_fi": None}
        if m_rw is not None:
            rec["ch_real"] = changed_orders(m_rw, s["m_rw0"])
        if m_dt is not None:
            rec["ch_k"] = changed_orders(m_dt, s["m_an"])
        if m_fi is not None:
            rec["ch_fi"] = changed_orders(m_fi, s["m_fa"])
        out["items"].append(rec)
    out["wall_s"] = time.perf_counter() - t0
    return out


def _winit(cores):
    D.cap_threads(1)
    os.sched_setaffinity(0, set(cores))


def run_replay(tasks, workers):
    global _TASKS
    _TASKS = tasks
    order = sorted(range(len(tasks)), key=lambda i: (
        0 if "c10_storm" in tasks[i]["iid"] else 1 if "c09_storm" in tasks[i]["iid"] else 2,
        -len(tasks[i]["items"])))
    res = []
    t0 = time.time()
    if workers <= 1:
        _winit(CORES)
        for i in order:
            res.append(replay_instance(i))
    else:
        ctx = mp.get_context("fork")
        with ctx.Pool(workers, initializer=_winit, initargs=(CORES,), maxtasksperchild=4) as pool:
            for r in pool.imap_unordered(replay_instance, order):
                res.append(r)
                print("[n23]   replayed {} ({:.0f}s), {} of {} ({:.0f}s)".format(
                    r["iid"], r["wall_s"], len(res), len(order), time.time() - t0), flush=True)
    return res


# --------------------------------------------------------------------------- #
# Per-order outcomes                                                           #
# --------------------------------------------------------------------------- #
def outcome(ch):
    """Newly late counts by class, the largest tardiness added to an urgent order, and more."""
    o = OrderedDict(late_by_cls=Counter(), ontime_by_cls=Counter(), urgent_ids=[],
                    max_add=0.0, max_add_id="", grow1=0, grow=0, better=0, wt_urgent=0.0,
                    wt_all=0.0, n_changed=len(ch))
    for oid, cls, d, w, cn, cw in ch:
        tn, tw = max(0.0, cn - d), max(0.0, cw - d)
        late_n, late_w = cn - d > EPS, cw - d > EPS
        if late_w and not late_n:
            o["late_by_cls"][cls] += 1
            if cls in URGENT:
                o["urgent_ids"].append(oid)
        if late_n and not late_w:
            o["ontime_by_cls"][cls] += 1
        inc = tw - tn
        o["wt_all"] += w * inc
        if cls in URGENT:
            o["wt_urgent"] += w * inc
            if inc > o["max_add"] + 1e-12:
                o["max_add"], o["max_add_id"] = inc, oid
            if inc > GROW_BH:
                o["grow1"] += 1
            if inc > EPS:
                o["grow"] += 1
            if inc < -EPS:
                o["better"] += 1
    o["n_urgent_late"] = len(o["urgent_ids"])
    o["n_late_any"] = sum(o["late_by_cls"].values())
    o["urgent_late"] = o["n_urgent_late"] > 0
    return o


# --------------------------------------------------------------------------- #
# Inputs and assertions                                                        #
# --------------------------------------------------------------------------- #
def build_tasks(recs, suite, items_by):
    anchors = D.load_anchor_records()
    by_inst = OrderedDict()
    for r in sorted(recs, key=lambda x: x["item_id"]):
        it = suite[r["item_id"]]
        iid = it["instance"]["instance_id"]
        check("suite instance equals the record's", iid == r["instance_id"], r["item_id"])
        t = by_inst.setdefault(iid, {"iid": iid, "path": D.instance_path(it), "items": [],
                                     "seeds": OrderedDict(), "digest": OrderedDict()})
        seed = list(it["episode"]["frozen_seed"] or [])
        fk = D.frozen_key(seed)
        check("frozen key equals items.jsonl", fk == items_by[r["item_id"]]["frozen_seed"],
              r["item_id"])
        t["seeds"].setdefault(fk, seed)
        t["digest"].setdefault(fk, anchors[(iid, fk)]["schedule_digest"])
        ops = D.canonical_ops(it)
        check("canonical operation count equals the census", len(ops) == r["n_ops"],
              r["item_id"])
        t["items"].append({"item_id": r["item_id"], "fk": fk, "seed": seed, "ops": ops,
                           "referenced": it["referenced"]})
    return list(by_inst.values())


def assert_replay(results, recs, items_by):
    """The run-fatal tie of every replayed board to its stored total (before any number)."""
    anchors = D.load_anchor_records()
    fi = {x["uid"]: x for x in n13.read_jsonl(n13.IN["fullinfo"])}
    fa = {}
    for a in n13.read_jsonl(n13.IN["anchors_fc"]):
        if a["reading"] == "FI":
            fa[(a["iid"], a["fk"], float(a["t_d"]))] = a["a"]
    rep = {}
    sites = {}
    for res in results:
        for k, s in res["sites"].items():
            sites[(res["iid"], k)] = s
        for x in res["items"]:
            check("one replay per proposal", x["item_id"] not in rep, x["item_id"])
            rep[x["item_id"]] = x
    check("every priced proposal replayed", set(rep) == {r["item_id"] for r in recs},
          len(rep))
    for r in recs:
        iid = r["item_id"]
        x, it = rep[iid], items_by[iid]
        s = sites[(x["iid"], x["site"])]
        check("decision instant equals items.jsonl", x["t_d"] == float(it["t_d"]), iid)
        for b in ("dt", "rw", "fi"):
            check("{}: a schedule exists for the proposal".format(b),
                  x[b]["term_feas"] == "applied_uncertified" and x[b]["sum_orig"] is not None,
                  (iid, x[b]["term_feas"]))
        for b in ("an", "rw0", "fa"):
            check("{}: a schedule exists without the proposal".format(b),
                  s[b]["term_feas"] == "applied_uncertified", (iid, b))
        check("the trajectory's schedule digest equals rule_anchor.json's (the no-AI anchor's "
              "schedule)", s["traj_is_anchor"], iid)
        check("the realised run without the proposal has the anchor's start and end time for "
              "every order", s["rw0_times_eq_anchor"], iid)
        # per-order sums against the evaluator of the same run
        for b, v in (("dt", x["dt"]), ("rw", x["rw"]), ("fi", x["fi"]), ("an", s["an"]),
                     ("rw0", s["rw0"]), ("fa", s["fa"])):
            close("per-order WT sum = evaluate.wwt on the original fields ({})".format(b),
                  v["sum_orig"], v["obj_orig"], SUM_TOL, iid)
        # the realised run: the totals behind the realised damage
        close("realised run with the proposal: per-order sum = items.jsonl rw_obj_orig",
              x["rw"]["sum_orig"], it["rw_obj_orig"], SUM_TOL, iid)
        close("realised run without the proposal: per-order sum = items.jsonl rw0_obj_orig",
              s["rw0"]["sum_orig"], it["rw0_obj_orig"], SUM_TOL, iid)
        a = anchors[(it["instance_id"], it["frozen_seed"])]
        close("realised run without the proposal: per-order sum = rule_anchor.json "
              "wwt_original_bh (the no-AI anchor)", s["rw0"]["sum_orig"],
              float(a["wwt_original_bh"]), ANCHOR_TOL, iid)
        close("pub_anchor_wwt of items.jsonl = rule_anchor.json", it["pub_anchor_wwt"],
              float(a["wwt_original_bh"]), 0.0, iid)
        close("realised damage from the per-order sums = N11_rows_forecast.csv damage_orig_bh",
              x["rw"]["sum_orig"] - float(a["wwt_original_bh"]), r["dmg"], CSV_TOL, iid)
        close("realised run with the proposal (adjusted fields) = items.jsonl rw_obj",
              x["rw"]["obj"], it["rw_obj"], SUM_TOL, iid)
        # the known board
        close("known board with the proposal: per-order sum = items.jsonl dt_obj_orig",
              x["dt"]["sum_orig"], it["dt_obj_orig"], SUM_TOL, iid)
        close("known board with the proposal: adjusted objective = items.jsonl dt_obj",
              x["dt"]["obj"], it["dt_obj"], SUM_TOL, iid)
        close("known board with the proposal: certified gap = items.jsonl dt_gap",
              x["dt"]["gap"], it["dt_gap"], SUM_TOL, iid)
        close("known board without the proposal: per-order sum = items.jsonl an_obj_orig",
              s["an"]["sum_orig"], it["an_obj_orig"], SUM_TOL, iid)
        close("known board without the proposal: bound = items.jsonl an_lb",
              s["an"]["lb"], it["an_lb"], SUM_TOL, iid)
        # the full-information board
        p = fi[iid]["p"]
        close("FI board with the proposal: per-order sum = fullinfo_direct.jsonl obj_orig",
              x["fi"]["sum_orig"], p["obj_orig"], SUM_TOL, iid)
        close("FI board with the proposal: certified gap = fullinfo_direct.jsonl gap",
              x["fi"]["gap"], p["gap"], SUM_TOL, iid)
        aa = fa[(it["instance_id"], it["frozen_seed"], float(it["t_d"]))]
        close("FI board without the proposal: per-order sum = anchors_direct.jsonl obj_orig",
              s["fa"]["sum_orig"], aa["obj_orig"], SUM_TOL, iid)
        # the changed-order lists carry the whole difference of the totals
        for ch, w_, n_ in (("ch_real", x["rw"], s["rw0"]), ("ch_k", x["dt"], s["an"]),
                           ("ch_fi", x["fi"], s["fa"])):
            o = outcome(x[ch])
            close("changed orders carry the whole WT difference ({})".format(ch),
                  o["wt_all"], w_["sum_orig"] - n_["sum_orig"], 1e-6, iid)
        check("an empty proposal changes no order",
              r["n_ops"] > 0 or (not x["ch_real"] and not x["ch_k"] and not x["ch_fi"]), iid)
    return rep, sites


# --------------------------------------------------------------------------- #
# Records                                                                      #
# --------------------------------------------------------------------------- #
def attach(recs, rep, sites):
    for r in recs:
        x = rep[r["item_id"]]
        s = sites[(x["iid"], x["site"])]
        r["real"] = outcome(x["ch_real"])
        r["kb"] = outcome(x["ch_k"])
        r["fib"] = outcome(x["ch_fi"])
        r["ul"] = r["real"]["urgent_late"]
        r["rule_k"] = r["kb"]["urgent_late"]
        r["rule_f"] = r["fib"]["urgent_late"]
        r["site_n"] = s
        r["rep"] = x
        for tok, (_disp, fk, ff) in DESIGNS.items():
            r["d_k_" + tok] = bool(fk(r))
            r["d_f_" + tok] = bool(ff(r))


def variant_flag(r, tok, rd):
    rule = r["rule_k"] if rd == "K" else r["rule_f"]
    cert = r["d_{}_Cert".format("k" if rd == "K" else "f")]
    two = r["d_{}_CertTwo".format("k" if rd == "K" else "f")]
    return {"Rule": rule, "Cert": cert, "CertRule": cert or rule, "CertTwo": two,
            "CertTwoRule": two or rule}[tok]


def sel_pop(recs, st):
    return [r for r in recs if st is None or r["stratum"] == st]


# --------------------------------------------------------------------------- #
# 0. The published headline (reused functions) and the replay census           #
# --------------------------------------------------------------------------- #
def section0(boot, recs, by, spfi, site, results, wall):
    n16.section0(boot, recs)
    n18.section0(recs, by, spfi, site)
    n20.section0(recs)
    m15 = n13.macros_of(IN23["n15_macros"])
    exp = {"Cert": (18, 15), "CertTwo": (0, 22), "CertM": (18, 14), "RelOne": (18, 80),
           "RelTwo": (18, 33), "Abs": (17, 81)}
    for tok, (k_app, k_fr) in exp.items():
        c20 = [r for r in recs if n13.costly_of(r, 0.20) == 1]
        l20 = [r for r in recs if n13.costly_of(r, 0.20) == 0]
        app = sum(1 for r in c20 if not r["d_k_" + tok])
        fr = sum(1 for r in l20 if r["d_k_" + tok])
        check("{} at its own threshold: {} costly applied and {} low-cost referred at 0.20 "
              "(N16 section 0, N15)".format(tok, k_app, k_fr), (app, fr) == (k_app, k_fr),
              (app, fr))
    check("N15: 186 costly / 1,170 low-cost", m15["nFifteenCostlyTwenty"] == "186"
          and m15["nFifteenLowTwenty"] == "1{,}170")
    n_sites = sum(len(x["sites"]) for x in results)
    n_items = sum(len(x["items"]) for x in results)
    md("## 0. Published headline and the replay", "",
       "The published headline of the direct benchmark at delta = tau = 0.20 is asserted first by "
       "n16.section0, n18.section0 and n20.section0 on n20.build's records (1,356 priced "
       "proposals, 186 costly, 1,170 low-cost; G-CERT applies 18 costly and refers 15 low-cost; "
       "with the second price 0 and 22), and the six designs' published flags are tied to "
       "N16/N15: G-CERT 18 / 15, G-CERT with the second price 0 / 22, G-CERT-M 18 / 14, D-REL1 "
       "18 / 80, D-REL2 18 / 33, D-ABS 17 / 81 (costly applied / low-cost referred at 0.20).", "",
       "Replay: {} proposals on {} instances, {} decision-instant sites (instance x frozen set x "
       "t_d); per proposal three boards with the proposal (realised full window, known board, "
       "full-information board) and per site the same three without it, all through "
       "n11_decision_time.gen_price (ATC, seed 0, the site's dispatcher) with N11's frozen-set "
       "convention 'fix'. Wall time {:.0f} s on cores {} ({} workers, one thread each).".format(
           n_items, len(results), n_sites, wall, CORES, len(CORES)), "",
       "The run without the proposal is the schedule the realised damage is measured against: "
       "at every site its start and end time of every order equal those of the baseline "
       "trajectory, whose schedule digest equals the no-AI anchor's schedule_digest in "
       "analysis/ladder/rule_anchor.json (asserted per site; the digest of the run itself can "
       "differ only by the label of an identical technician of the same trade, the case "
       "n8_causal.pin_schedule describes), and its weighted tardiness equals the anchor's "
       "(below).", "")


def section_assert():
    rows = sorted(MAXDIFF.items())
    md("## Assertions on the replay (run-fatal, every proposal)", "",
       "Each line is asserted for each of the 1,356 proposals (or each site); the column gives "
       "the largest absolute difference met. Tolerances: {} against full-precision stored "
       "totals, {} against rule_anchor.json, {} against the six-decimal damage of "
       "N11_rows_forecast.csv.".format(SUM_TOL, ANCHOR_TOL, CSV_TOL), "")
    md_table(["assertion", "largest absolute difference"],
             [[w, "{:.3g}".format(v)] for w, v in rows])


# --------------------------------------------------------------------------- #
# Table 1: urgent-late proposals, costly / low-cost                            #
# --------------------------------------------------------------------------- #
def table1(recs):
    res = OrderedDict()
    for (p, st), (dtok, delta) in ((a, b) for a in POPS.items() for b in DELTAS.items()):
        sel = sel_pop(recs, st)
        ul = [r for r in sel if r["ul"]]
        o = OrderedDict(
            priced=len(sel), ul=len(ul),
            ul_costly=sum(1 for r in ul if n13.costly_of(r, delta) == 1),
            ul_low=sum(1 for r in ul if n13.costly_of(r, delta) == 0),
            ul_und=sum(1 for r in ul if n13.costly_of(r, delta) is None),
            costly=sum(1 for r in sel if n13.costly_of(r, delta) == 1),
            low=sum(1 for r in sel if n13.costly_of(r, delta) == 0),
            any_late=sum(1 for r in sel if r["real"]["n_late_any"] > 0),
            orders=sum(r["real"]["n_urgent_late"] for r in sel),
            orders_c1=sum(r["real"]["late_by_cls"][1] for r in sel),
            orders_c2=sum(r["real"]["late_by_cls"][2] for r in sel),
            grow1=sum(1 for r in sel if r["real"]["grow1"] > 0),
            g1_costly=sum(1 for r in sel if r["real"]["grow1"] > 0
                          and n13.costly_of(r, delta) == 1),
            g1_low=sum(1 for r in sel if r["real"]["grow1"] > 0
                       and n13.costly_of(r, delta) == 0),
            g1_orders=sum(r["real"]["grow1"] for r in sel),
            instances=len({r["instance_id"] for r in ul}),
            dist=qdist([r["real"]["max_add"] for r in ul]),
            dist_g1=qdist([r["real"]["max_add"] for r in sel if r["real"]["grow1"] > 0]))
        check("urgent-late = costly + low-cost + undecided",
              o["ul"] == o["ul_costly"] + o["ul_low"] + o["ul_und"])
        res[(p, dtok)] = o
    for dtok in DELTAS:
        for f in ("priced", "ul", "ul_costly", "ul_low", "ul_und", "orders", "any_late"):
            check("Table 1 strata sum to pooled ({} {})".format(dtok, f),
                  sum(res[(p, dtok)][f] for p in POPS if p != "Pooled")
                  == res[("Pooled", dtok)][f])
    for (p, dtok), o in res.items():
        dl = DELTAS[dtok]
        pn = POP_NAME[p]
        pre = "TOne" + p + dtok
        if dtok == "Twenty":
            add(pre + "Priced", grp(o["priced"]), "[T1] {}: priced proposals".format(pn))
            add(pre + "UrgentLate", grp(o["ul"]),
                "[T1] {}: proposals that make at least one order of class 1 or 2 newly late in "
                "the realised run (on time without the proposal, late with it; original due "
                "dates and classes)".format(pn))
            add(pre + "UrgentLateShare", pct(o["ul"], o["priced"]),
                "[T1] {}: the same as a share of the priced proposals".format(pn))
            add(pre + "UrgentLateInstances", o["instances"],
                "[T1] {}: instances that carry an urgent-late proposal".format(pn))
            add(pre + "UrgentOrders", grp(o["orders"]),
                "[T1] {}: newly late orders of class 1 or 2 summed over the priced proposals"
                .format(pn))
            add(pre + "UrgentOrdersClassOne", grp(o["orders_c1"]),
                "[T1] {}: of these, orders of class 1".format(pn))
            add(pre + "UrgentOrdersClassTwo", grp(o["orders_c2"]),
                "[T1] {}: of these, orders of class 2".format(pn))
            add(pre + "AnyLate", grp(o["any_late"]),
                "[T1] {}: proposals that make at least one order of any class newly late"
                .format(pn))
            add(pre + "GrowOne", grp(o["grow1"]),
                "[T1] {}: proposals that add more than 1 bh of tardiness to at least one order "
                "of class 1 or 2 (late before or not)".format(pn))
            add(pre + "GrowOneOrders", grp(o["g1_orders"]),
                "[T1] {}: orders of class 1 or 2 whose tardiness grows by more than 1 bh, summed "
                "over the priced proposals".format(pn))
            for nm, v in zip(("Median", "PNinety", "Max"), o["dist_g1"]):
                add(pre + "GrowOneMaxAdd" + nm, bhm(v),
                    "[T1] {}: {} over the proposals that add more than 1 bh to an urgent order of "
                    "the largest tardiness added to one urgent order, bh".format(
                        pn, {"Median": "median", "PNinety": "90th percentile (linear)",
                             "Max": "maximum"}[nm]))
            for nm, v in zip(("Median", "PNinety", "Max"), o["dist"]):
                add(pre + "MaxAdd" + nm, bhm(v),
                    "[T1] {}: {} over the urgent-late proposals of the largest tardiness added "
                    "to one order of class 1 or 2, bh".format(
                        pn, {"Median": "median", "PNinety": "90th percentile (linear)",
                             "Max": "maximum"}[nm]))
        add(pre + "UrgentLateCostly", grp(o["ul_costly"]),
            "[T1] {}, delta = {:.2f}: urgent-late proposals that are costly (realised cost "
            "above delta)".format(pn, dl))
        add(pre + "UrgentLateLow", grp(o["ul_low"]),
            "[T1] {}, delta = {:.2f}: urgent-late proposals that are low-cost (realised cost at "
            "most delta)".format(pn, dl))
        add(pre + "UrgentLateLowShare", pct(o["ul_low"], o["ul"]),
            "[T1] {}, delta = {:.2f}: low-cost proposals as a share of the urgent-late "
            "proposals".format(pn, dl))
        add(pre + "GrowOneCostly", grp(o["g1_costly"]),
            "[T1] {}, delta = {:.2f}: proposals that add more than 1 bh to an urgent order and "
            "are costly".format(pn, dl))
        add(pre + "GrowOneLow", grp(o["g1_low"]),
            "[T1] {}, delta = {:.2f}: proposals that add more than 1 bh to an urgent order and "
            "are low-cost".format(pn, dl))
    md("## Table 1. Proposals that make an urgent order newly late (realised run)", "",
       "Priced = the 1,356 priced reference proposals of the direct benchmark (n20's "
       "population). Urgent-late = at least one order of priority class 1 or 2 finishes on time "
       "in the realised run without the proposal and late with it, on the original due dates and "
       "classes (late: C - d > 1e-9 bh). Costly / low-cost = the whole-board label (realised "
       "cost on the original fields above delta / at most delta, n13.costly_of). Orders = newly "
       "late orders of class 1 or 2 summed over the proposals. Max add = the largest tardiness "
       "added to one urgent order (bh; median / 90th percentile / maximum over the urgent-late "
       "proposals). >1 bh = proposals that add more than 1 bh of tardiness to at least one "
       "urgent order (whether or not it was already late).", "")
    body = []
    for dtok, delta in DELTAS.items():
        for p in POPS:
            o = res[(p, dtok)]
            body.append(["{:.2f}".format(delta), p, o["priced"],
                         "{} ({})".format(o["ul"], pctp(o["ul"], o["priced"])), o["ul_costly"],
                         o["ul_low"], o["ul_und"], o["costly"], o["low"],
                         "{} ({} / {})".format(o["orders"], o["orders_c1"], o["orders_c2"]),
                         o["any_late"], o["grow1"],
                         " / ".join(bh2(v) for v in o["dist"]) if dtok == "Twenty" else ""])
    md_table(["delta", "population", "priced", "urgent-late", "of which costly", "low-cost",
              "undecided", "costly (all)", "low-cost (all)",
              "newly late urgent orders (class 1 / 2)", "any order newly late",
              "urgent tardiness +>1 bh", "max add median / p90 / max (bh)"], body)
    md("### Table 1b. The second outcome: an urgent order's tardiness grows by more than 1 bh", "",
       "Proposals that add more than 1 bh of tardiness to at least one order of class 1 or 2, "
       "whether that order was already late without the proposal or not (the design's second "
       "per-proposal count). Orders = urgent orders with such growth, summed. Max add as above, "
       "over these proposals.", "")
    body = []
    for dtok, delta in DELTAS.items():
        for p in POPS:
            o = res[(p, dtok)]
            body.append(["{:.2f}".format(delta), p, o["priced"],
                         "{} ({})".format(o["grow1"], pctp(o["grow1"], o["priced"])),
                         o["g1_costly"], o["g1_low"], o["grow1"] - o["g1_costly"] - o["g1_low"],
                         o["g1_orders"],
                         " / ".join(bh2(v) for v in o["dist_g1"]) if dtok == "Twenty" else ""])
    md_table(["delta", "population", "priced", "urgent tardiness +>1 bh", "of which costly",
              "low-cost", "undecided", "urgent orders +>1 bh", "max add median / p90 / max (bh)"],
             body)
    return res


def list_urgent_late(recs):
    """Every urgent-late proposal, one line each (summary only)."""
    ul = sorted((r for r in recs if r["ul"]), key=lambda r: (r["st"], r["item_id"]))
    md("### Table 1c. The urgent-late proposals one by one", "",
       "Label = the whole-board label at 0.20 / 0.10 (C costly, L low-cost). Applied by = the "
       "designs (known board) that apply the proposal. Rule K / FI = flagged by the per-order "
       "rule on the known board / the full-information board. Late orders = the newly late "
       "urgent orders (id, class, tardiness without -> with, bh).", "")
    body = []
    for r in ul:
        x = r["rep"]["ch_real"]
        late = []
        for oid, cls, d, w, cn, cw in x:
            if oid in r["real"]["urgent_ids"]:
                late.append("{} c{} {:.2f}->{:.2f}".format(oid, cls, max(0.0, cn - d),
                                                         max(0.0, cw - d)))
        lab = "/".join({1: "C", 0: "L", None: "U"}[n13.costly_of(r, d)] for d in (0.20, 0.10))
        body.append([r["item_id"], r["st"], r["primary_class"], r["split"], lab,
                     "{:.2f}".format(r["dmg"]), "{:.3f}".format(r["p_G-CERT"]),
                     ", ".join(DESIGNS[t][0] for t in DESIGNS if not r["d_k_" + t]) or "none",
                     "{} / {}".format(int(r["rule_k"]), int(r["rule_f"])),
                     "; ".join(late), "{:.2f}".format(r["real"]["max_add"]),
                     r["real"]["grow1"]])
    md_table(["item", "stratum", "class", "operation type", "label 0.20 / 0.10",
              "realised damage (weighted bh)", "G-CERT price on K", "applied by",
              "rule K / FI", "newly late urgent orders", "max add (bh)",
              "urgent orders +>1 bh"], body)
    return ul


# --------------------------------------------------------------------------- #
# Table 2 (and 3): the designs' applied proposals                              #
# --------------------------------------------------------------------------- #
def design_cell(sel, tok, rd, delta):
    app = [r for r in sel if not r["d_{}_{}".format("k" if rd == "K" else "f", tok)]]
    ul = [r for r in app if r["ul"]]
    low = [r for r in ul if n13.costly_of(r, delta) == 0]
    cst = [r for r in ul if n13.costly_of(r, delta) == 1]
    g1 = [r for r in app if r["real"]["grow1"] > 0]
    g1_low = [r for r in g1 if n13.costly_of(r, delta) == 0]
    return OrderedDict(
        n=len(sel), applied=len(app), ul=len(ul), ul_low=len(low), ul_costly=len(cst),
        ul_und=len(ul) - len(low) - len(cst),
        orders=sum(r["real"]["n_urgent_late"] for r in ul),
        grow1=len(g1), g1_low=len(g1_low),
        g1_costly=sum(1 for r in g1 if n13.costly_of(r, delta) == 1),
        g1_orders=sum(r["real"]["grow1"] for r in g1),
        dist=qdist([r["real"]["max_add"] for r in ul]),
        dist_low=qdist([r["real"]["max_add"] for r in low]),
        dist_g1=qdist([r["real"]["max_add"] for r in g1]),
        dist_g1_low=qdist([r["real"]["max_add"] for r in g1_low]),
        ids_low=sorted(r["item_id"] for r in low))


def table2(recs, rd):
    res = OrderedDict()
    for tok in DESIGNS:
        for p, st in POPS.items():
            for dtok, delta in DELTAS.items():
                res[(tok, p, dtok)] = design_cell(sel_pop(recs, st), tok, rd, delta)
    for tok in DESIGNS:
        for dtok in DELTAS:
            for f in ("applied", "ul", "ul_low", "ul_costly"):
                check("Table 2 strata sum to pooled ({} {} {} {})".format(rd, tok, dtok, f),
                      sum(res[(tok, p, dtok)][f] for p in POPS if p != "Pooled")
                      == res[(tok, "Pooled", dtok)][f])
    if rd == "K":
        for (tok, p, dtok), o in res.items():
            disp = DESIGNS[tok][0]
            pn = POP_NAME[p]
            dl = DELTAS[dtok]
            pre = "TTwo" + tok + p + dtok
            what = "[T2] {}, {} at its own threshold ({}), known board, delta = {:.2f}".format(
                pn, disp, THRESH[tok], dl)
            if dtok == "Twenty":
                add(pre + "Applied", grp(o["applied"]), what + ": proposals applied")
                add(pre + "UrgentLateOrders", grp(o["orders"]),
                    what + ": newly late orders of class 1 or 2 summed over the applied "
                    "urgent-late proposals")
                add(pre + "GrowOne", grp(o["grow1"]),
                    what + ": applied proposals that add more than 1 bh of tardiness to an order "
                    "of class 1 or 2")
                for nm, v in zip(("Median", "PNinety", "Max"), o["dist"]):
                    add(pre + "MaxAdd" + nm, bhm(v),
                        what + ": {} of the largest tardiness added to one urgent order over the "
                        "applied urgent-late proposals, bh".format(
                            {"Median": "median", "PNinety": "90th percentile (linear)",
                             "Max": "maximum"}[nm]))
                for nm, v in zip(("Median", "PNinety", "Max"), o["dist_low"]):
                    add(pre + "LowMaxAdd" + nm, bhm(v),
                        what + ": {} of the same over the applied urgent-late proposals that are "
                        "low-cost, bh".format({"Median": "median",
                                               "PNinety": "90th percentile (linear)",
                                               "Max": "maximum"}[nm]))
            add(pre + "UrgentLate", grp(o["ul"]),
                what + ": applied proposals that make an order of class 1 or 2 newly late "
                "(realised run)")
            add(pre + "UrgentLateLow", grp(o["ul_low"]),
                what + ": of these, low-cost by the whole-board label (one urgent order delayed "
                "while the board's realised cost stays at most delta)")
            add(pre + "UrgentLateCostly", grp(o["ul_costly"]),
                what + ": of these, costly by the whole-board label")
            add(pre + "GrowOneLow", grp(o["g1_low"]),
                what + ": applied proposals that add more than 1 bh to an urgent order and are "
                "low-cost by the whole-board label")
            add(pre + "GrowOneCostly", grp(o["g1_costly"]),
                what + ": applied proposals that add more than 1 bh to an urgent order and are "
                "costly")
            if dtok == "Twenty":
                for nm, v in zip(("Median", "PNinety", "Max"), o["dist_g1"]):
                    add(pre + "GrowOneMaxAdd" + nm, bhm(v),
                        what + ": {} of the largest tardiness added to one urgent order over the "
                        "applied proposals that add more than 1 bh to an urgent order, bh".format(
                            {"Median": "median", "PNinety": "90th percentile (linear)",
                             "Max": "maximum"}[nm]))
    return res


def md_table2(res, rd):
    rn = "known board (K)" if rd == "K" else "full information (FI)"
    body = []
    for dtok, delta in DELTAS.items():
        for tok, (disp, _fk, _ff) in DESIGNS.items():
            for p in POPS:
                if dtok == "Ten" and p != "Pooled":
                    continue
                o = res[(tok, p, dtok)]
                body.append(["{:.2f}".format(delta), disp, THRESH[tok], p, o["applied"],
                             o["ul"], o["ul_low"], o["ul_costly"], o["ul_und"], o["orders"],
                             o["grow1"], " / ".join(bh2(v) for v in o["dist"]),
                             " / ".join(bh2(v) for v in o["dist_low"])])
    md_table(["delta", "design", "threshold", "population", "applied", "urgent-late applied",
              "of which low-cost", "costly", "undecided", "newly late urgent orders",
              "applied with urgent tardiness +>1 bh",
              "max add median / p90 / max (bh)", "max add, low-cost ones (bh)"], body)
    md("Second outcome, {}: applied proposals that add more than 1 bh of tardiness to an urgent "
       "order (late before or not).".format(rn), "")
    body = []
    for dtok, delta in DELTAS.items():
        for tok, (disp, _fk, _ff) in DESIGNS.items():
            for p in POPS:
                if dtok == "Ten" and p != "Pooled":
                    continue
                o = res[(tok, p, dtok)]
                body.append(["{:.2f}".format(delta), disp, p, o["applied"], o["grow1"],
                             o["g1_low"], o["g1_costly"], o["grow1"] - o["g1_low"] - o["g1_costly"],
                             o["g1_orders"], " / ".join(bh2(v) for v in o["dist_g1"]),
                             " / ".join(bh2(v) for v in o["dist_g1_low"])])
    md_table(["delta", "design", "population", "applied", "applied with urgent tardiness +>1 bh",
              "of which low-cost", "costly", "undecided", "urgent orders +>1 bh",
              "max add median / p90 / max (bh)", "max add, low-cost ones (bh)"], body)
    return rn


def table3(recs, rd):
    res = OrderedDict()
    for sp in SPLITS:
        sel = [r for r in recs if r["split"] == sp]
        for dtok, delta in DELTAS.items():
            ul = [r for r in sel if r["ul"]]
            res[("T1", sp, dtok)] = OrderedDict(
                priced=len(sel), ul=len(ul),
                ul_costly=sum(1 for r in ul if n13.costly_of(r, delta) == 1),
                ul_low=sum(1 for r in ul if n13.costly_of(r, delta) == 0))
            for tok in DESIGNS:
                res[(tok, sp, dtok)] = design_cell(sel, tok, rd, delta)
    check("every priced proposal is sequencing only, a field edit or empty",
          sum(res[("T1", sp, "Twenty")]["priced"] for sp in SPLITS) == len(recs))
    for dtok in DELTAS:
        check("Table 3 op types sum to the pooled urgent-late count ({})".format(dtok),
              sum(res[("T1", sp, dtok)]["ul"] for sp in SPLITS)
              == sum(1 for r in recs if r["ul"]))
    if rd == "K":
        for sp, (stok, sname) in SPLITS.items():
            o = res[("T1", sp, "Twenty")]
            pre = "TThree" + stok
            add(pre + "Priced", grp(o["priced"]), "[T3] {}: priced proposals".format(sname))
            add(pre + "UrgentLate", grp(o["ul"]),
                "[T3] {}: urgent-late proposals (realised run)".format(sname))
            add(pre + "UrgentLateLow", grp(o["ul_low"]),
                "[T3] {}, delta = 0.20: of these, low-cost".format(sname))
            add(pre + "UrgentLateCostly", grp(o["ul_costly"]),
                "[T3] {}, delta = 0.20: of these, costly".format(sname))
            for tok, (disp, _a, _b) in DESIGNS.items():
                c = res[(tok, sp, "Twenty")]
                what = "[T3] {}, {} at its own threshold, known board, delta = 0.20".format(
                    sname, disp)
                add(pre + tok + "Applied", grp(c["applied"]), what + ": proposals applied")
                add(pre + tok + "UrgentLate", grp(c["ul"]),
                    what + ": applied urgent-late proposals")
                add(pre + tok + "UrgentLateLow", grp(c["ul_low"]),
                    what + ": of these, low-cost")
    return res


def md_table3(res):
    body = []
    for dtok, delta in DELTAS.items():
        for sp, (_stok, sname) in SPLITS.items():
            o = res[("T1", sp, dtok)]
            body.append(["{:.2f}".format(delta), sname, "all priced", o["priced"], o["ul"],
                         o["ul_low"], o["ul_costly"], "", ""])
            for tok, (disp, _a, _b) in DESIGNS.items():
                c = res[(tok, sp, dtok)]
                body.append(["{:.2f}".format(delta), sname, disp, c["applied"], c["ul"],
                             c["ul_low"], c["ul_costly"], " / ".join(bh2(v) for v in c["dist"]),
                             " / ".join(bh2(v) for v in c["dist_low"])])
    md_table(["delta", "operation type", "design (applied) or all priced", "proposals",
              "urgent-late", "of which low-cost", "costly",
              "max add median / p90 / max (bh)", "max add, low-cost ones (bh)"], body)


# --------------------------------------------------------------------------- #
# Table 4: the per-order rule                                                  #
# --------------------------------------------------------------------------- #
def table4(boot, recs, rd):
    res = OrderedDict()
    for tok in VARIANTS:
        for p, st in POPS.items():
            for dtok, delta in DELTAS.items():
                sel = sel_pop(recs, st)
                costly = [r for r in sel if n13.costly_of(r, delta) == 1]
                low = [r for r in sel if n13.costly_of(r, delta) == 0]
                ul = [r for r in sel if r["ul"]]
                fa = [not variant_flag(r, tok, rd) for r in costly]
                fl = [variant_flag(r, tok, rd) for r in low]
                fu = [not variant_flag(r, tok, rd) for r in ul]
                ul_low = [r for r in ul if n13.costly_of(r, delta) == 0]
                g1 = [r for r in sel if r["real"]["grow1"] > 0]
                fg = [not variant_flag(r, tok, rd) for r in g1]
                o = OrderedDict(costly=len(costly), c_app=sum(fa), low=len(low), l_ref=sum(fl),
                                ul=len(ul), u_app=sum(fu),
                                ul_low=len(ul_low),
                                ul_low_app=sum(1 for r in ul_low
                                               if not variant_flag(r, tok, rd)),
                                ref_all=sum(1 for r in sel if variant_flag(r, tok, rd)),
                                g1=len(g1), g1_app=sum(fg))
                o["c_lo"], o["c_hi"] = boot.ci(costly, fa) if costly else (None, None)
                o["l_lo"], o["l_hi"] = boot.ci(low, fl) if low else (None, None)
                o["u_lo"], o["u_hi"] = boot.ci(ul, fu) if ul else (None, None)
                o["g_lo"], o["g_hi"] = boot.ci(g1, fg) if g1 else (None, None)
                res[(tok, p, dtok)] = o
    # the rule's agreement with the realised outcome
    agree = OrderedDict()
    for p, st in POPS.items():
        sel = sel_pop(recs, st)
        rk = "rule_k" if rd == "K" else "rule_f"
        agree[p] = OrderedDict(
            flagged=sum(1 for r in sel if r[rk]), ul=sum(1 for r in sel if r["ul"]),
            both=sum(1 for r in sel if r[rk] and r["ul"]),
            flag_only=sum(1 for r in sel if r[rk] and not r["ul"]),
            ul_only=sum(1 for r in sel if r["ul"] and not r[rk]))
    for tok in VARIANTS:
        for dtok in DELTAS:
            for f in ("costly", "c_app", "low", "l_ref", "ul", "u_app"):
                check("Table 4 strata sum to pooled ({} {} {} {})".format(rd, tok, dtok, f),
                      sum(res[(tok, p, dtok)][f] for p in POPS if p != "Pooled")
                      == res[(tok, "Pooled", dtok)][f])
    c = res[("Cert", "Pooled", "Twenty")]
    if rd == "K":
        check("Table 4 G-CERT row equals the headline (18 / 186 applied, 15 / 1,170 referred)",
              (c["c_app"], c["costly"], c["l_ref"], c["low"]) == (18, 186, 15, 1170), c)
        c2 = res[("CertTwo", "Pooled", "Twenty")]
        check("Table 4 second-price row equals the headline (0 applied, 22 referred)",
              (c2["c_app"], c2["l_ref"]) == (0, 22), c2)
    if rd == "K":
        for (tok, p, dtok), o in res.items():
            if dtok == "Ten" and p != "Pooled":
                continue
            pn = POP_NAME[p]
            dl = DELTAS[dtok]
            pre = "TFour" + tok + p + dtok
            what = "[T4] {}, {}, decided on the known board at t_d, delta = {:.2f}".format(
                pn, VARIANTS[tok], dl)
            add(pre + "Costly", grp(o["costly"]), what + ": costly proposals")
            add(pre + "CostlyApplied", grp(o["c_app"]), what + ": costly proposals applied")
            add(pre + "CostlyAppliedShare", pct(o["c_app"], o["costly"]),
                what + ": costly applied as a share of the costly")
            add(pre + "CostlyAppliedLo", pctv(o["c_lo"]),
                what + ": lower end of the 95% cluster-bootstrap interval of that share (60 "
                "instances, n2 seed 20261026, 20,000 replicates)")
            add(pre + "CostlyAppliedHi", pctv(o["c_hi"]), what + ": upper end of that interval")
            add(pre + "Low", grp(o["low"]), what + ": low-cost proposals")
            add(pre + "LowReferred", grp(o["l_ref"]), what + ": low-cost proposals referred")
            add(pre + "LowReferredShare", pct(o["l_ref"], o["low"]),
                what + ": low-cost referred as a share of the low-cost")
            add(pre + "LowReferredLo", pctv(o["l_lo"]),
                what + ": lower end of the 95% cluster-bootstrap interval of that share")
            add(pre + "LowReferredHi", pctv(o["l_hi"]), what + ": upper end of that interval")
            add(pre + "UrgentLate", grp(o["ul"]),
                what + ": urgent-late proposals (realised run)")
            add(pre + "UrgentLateApplied", grp(o["u_app"]),
                what + ": urgent-late proposals applied")
            add(pre + "UrgentLateAppliedShare", pct(o["u_app"], o["ul"]),
                what + ": urgent-late applied as a share of the urgent-late")
            add(pre + "UrgentLateAppliedLo", pctv(o["u_lo"]),
                what + ": lower end of the 95% cluster-bootstrap interval of that share")
            add(pre + "UrgentLateAppliedHi", pctv(o["u_hi"]),
                what + ": upper end of that interval")
            add(pre + "UrgentLateLowApplied", grp(o["ul_low_app"]),
                what + ": urgent-late proposals that are low-cost and applied")
            add(pre + "GrowOne", grp(o["g1"]),
                what + ": proposals that add more than 1 bh to an urgent order (realised run)")
            add(pre + "GrowOneApplied", grp(o["g1_app"]), what + ": of these, applied")
            add(pre + "GrowOneAppliedShare", pct(o["g1_app"], o["g1"]),
                what + ": the same as a share")
            add(pre + "GrowOneAppliedLo", pctv(o["g_lo"]),
                what + ": lower end of the 95% cluster-bootstrap interval of that share")
            add(pre + "GrowOneAppliedHi", pctv(o["g_hi"]), what + ": upper end of that interval")
        for p, a in agree.items():
            pn = POP_NAME[p]
            add("TFourAgree" + p + "Flagged", grp(a["flagged"]),
                "[T4] {}: proposals the per-order rule flags on the known board".format(pn))
            add("TFourAgree" + p + "Both", grp(a["both"]),
                "[T4] {}: flagged on the known board and urgent-late in the realised run"
                .format(pn))
            add("TFourAgree" + p + "FlagOnly", grp(a["flag_only"]),
                "[T4] {}: flagged on the known board, not urgent-late in the realised run"
                .format(pn))
            add("TFourAgree" + p + "MissOnly", grp(a["ul_only"]),
                "[T4] {}: urgent-late in the realised run, not flagged on the known board"
                .format(pn))
    return res, agree


def md_table4(res, agree, rd):
    body = []
    for dtok, delta in DELTAS.items():
        for tok, disp in VARIANTS.items():
            for p in POPS:
                if dtok == "Ten" and p != "Pooled":
                    continue
                o = res[(tok, p, dtok)]
                body.append(["{:.2f}".format(delta), disp, p,
                             ci_str(o["c_app"], o["costly"], o["c_lo"], o["c_hi"]),
                             ci_str(o["l_ref"], o["low"], o["l_lo"], o["l_hi"]),
                             ci_str(o["u_app"], o["ul"], o["u_lo"], o["u_hi"]),
                             "{} / {}".format(o["ul_low_app"], o["ul_low"]),
                             ci_str(o["g1_app"], o["g1"], o["g_lo"], o["g_hi"]), o["ref_all"]])
    md_table(["delta", "variant", "population", "costly applied [95% CI]",
              "low-cost referred [95% CI]", "urgent-late applied [95% CI]",
              "urgent-late low-cost applied / urgent-late low-cost",
              "urgent tardiness +>1 bh applied [95% CI]", "referred (all priced)"],
             body)
    md("Agreement of the per-order rule ({}) with the realised outcome:".format(
        "known board" if rd == "K" else "full-information board"), "")
    md_table(["population", "flagged by the rule", "urgent-late (realised)",
              "flagged and urgent-late", "flagged only", "urgent-late only"],
             [[p, a["flagged"], a["ul"], a["both"], a["flag_only"], a["ul_only"]]
              for p, a in agree.items()])


# --------------------------------------------------------------------------- #
# Part B: intervals for Table tab:e1                                           #
# --------------------------------------------------------------------------- #
B_COLS = OrderedDict([("VThreeFeas", "V3 cost-bearing, G-FEAS (blocked by feasibility)"),
                      ("VThreeReferred", "V3 cost-bearing, referred"),
                      ("VFour", "V4 blocked"), ("VFive", "V5 blocked"), ("VSix", "V6 blocked"),
                      ("BenignFeas", "benign false-block rate, G-FEAS"),
                      ("BenignCert", "benign false-block rate, G-CERT"),
                      ("VThreeFidelity", "V3 fidelity (N16 block H rule, repeat 0)")])


def b_context(check_):
    """n19.Ctx without the known-board dry-run prompt file (only the known-board checks read
    it): the same loaders, bootstrap and macro files."""
    ctx = object.__new__(N19.Ctx)
    ctx.check = check_
    dc = D.Checker()
    ctx.suite = OrderedDict((r["item_id"], r) for r in D.load_published(dc))
    check("Part B: published suite loads through suite_gate", not dc.failures, dc.failures[:3])
    ctx.items_e2e = {r["item_id"]: r for r in D.read_jsonl(N19.E2E / "items.jsonl")}
    ctx.issuable = {k for k, v in ctx.items_e2e.items() if v["issuable"] and k in ctx.suite}
    ctx.issuable_all = set(ctx.issuable)
    check("Part B: 1,723 issuable instructions", len(ctx.issuable) == 1723, len(ctx.issuable))
    ctx.instances = sorted({it["instance"]["instance_id"] for it in ctx.suite.values()})
    check("Part B: 60 instance clusters", len(ctx.instances) == 60)
    ctx.only = None
    ctx.inst_index = {iid: i for i, iid in enumerate(ctx.instances)}
    ctx.k = len(ctx.instances)
    ctx.anchor = {}
    for rec in json.loads(Path(n13.IN["rule_anchor"]).read_text()):
        ctx.anchor[(Path(rec["instance_path"]).stem, N19.e1dg.frozen_key(rec["frozen_seed"]))] = \
            float(rec["wwt_original_bh"])
    ctx.full_br = D.full_brackets()
    ctx.boot = n2.Boot(ctx.instances, n2.SEED, n2.B_BOOT)
    check("Part B: n2 bootstrap seed 20261026, 20,000 replicates, 60 clusters",
          (n2.SEED, n2.B_BOOT, ctx.boot.k) == (20261026, 20000, 60))
    ctx._cell_boot = {}
    ctx.macros = {}
    for p in N19.MACRO_FILES:
        ctx.macros.update(n13.macros_of(p))
    ctx.instr_borne = set()
    ctx.prompt_hash = {}
    ctx._pub_td = None
    ctx._pub_sites = None
    return ctx


def fid_spec(rep):
    return ("FidelityRep", "pct", "n2", lambda r, k=rep: r["cls"] == "V3" and r["repeat"] == k,
            lambda r: r["equiv"], None, "V3 translation fidelity, repeat {}".format(rep))


def part_b():
    chk = N19.Check()
    ctx = b_context(chk)
    # Table tab:e1 of the manuscript is checked when its draft is present; the public
    # release does not carry the drafts.
    tab_src = IN23["table_e1"].read_text(encoding="utf-8") if IN23["table_e1"].is_file() else None
    out = OrderedDict()
    cells_rows = OrderedDict()
    for arm in N19.ARMS:
        b = N19.pub_bundle(ctx, arm)
        recs = N19.records(ctx, b)
        cells = sorted({r["cell"] for r in recs if r["mode"] == N19.MODE},
                       key=lambda c: list(N19.TAB6).index(c))
        for cell in cells:
            rs, ms = N19.cell_measures(ctx, recs, cell)
            c6, _g = N19.tab6_cells(ctx, b, recs, cell, ms)
            disp, tok, _d3k = N19.TAB6[cell]
            if tab_src is not None:
                check("Part B: {} is a row of Table tab:e1".format(disp),
                      "\\nElevenTabEOne{}VThreeFeas{{}}".format(tok) in tab_src
                      and "\\nSixteenFidelity{}Share{{}}".format(tok) in tab_src, tok)
            reps = sorted({r["repeat"] for r in rs})
            row = OrderedDict()
            for col in B_COLS:
                if col == "VThreeFidelity":
                    m = ms["Fidelity"]
                    want = ctx.macros["nSixteenFidelity" + tok + "Share"]
                    got = N19.N16["pct"](int(m["num"]), int(m["den"]))
                    per = [N19.measure(ctx, rs, fid_spec(k), cell)["value"] for k in reps]
                else:
                    m = ms[col]
                    want = ctx.macros["nElevenTabEOne" + tok + col]
                    got = N19.S.pct_cell(m["value"], 1)
                    check("Part B: Analysis cell equals the per-row value ({} {})".format(tok, col),
                          c6[col] == got, (c6[col], got))
                    spec = N19.MEASURE_OF[col]
                    per = [N19.measure(ctx, [r for r in rs if r["repeat"] == k], spec,
                                       cell)["value"] for k in reps]
                check("Part B: point value equals the table macro ({} {})".format(tok, col),
                      got == want, (got, want))
                check("Part B: interval brackets the point value ({} {})".format(tok, col),
                      m["lo"] is not None and m["lo"] - 1e-12 <= m["value"] <= m["hi"] + 1e-12,
                      (m["lo"], m["value"], m["hi"]))
                row[col] = OrderedDict(num=int(m["num"]), den=int(m["den"]), value=m["value"],
                                       lo=m["lo"], hi=m["hi"], per=per, macro=want)
            out[cell] = OrderedDict(disp=disp, tok=tok, reps=reps, rows=len(rs), cols=row)
            cells_rows[cell] = rs
    check("Part B: the eight model configurations of Table tab:e1", len(out) == 8, list(out))
    check("Part B: the n19 checks pass", chk.report()["status"] == "PASS")
    for cell, o in out.items():
        tok = o["tok"]
        add("B" + tok + "Repeats", len(o["reps"]),
            "[B] {}: repeats of the configuration in the gate stress test (constrained mode)"
            .format(o["disp"]))
        for col, c in o["cols"].items():
            what = "[B] {}, Table tab:e1 column '{}' (point value {})".format(
                o["disp"], B_COLS[col], c["macro"].replace("\\%", "%"))
            add("B" + tok + col + "Lo", pctv(c["lo"]),
                what + ": lower end of the 95% cluster-bootstrap interval by instance (n2 seed "
                "20261026, 20,000 replicates, 60 instances{})".format(
                    ", repeats pooled" if col != "VThreeFidelity" else ", repeat 0"))
            add("B" + tok + col + "Hi", pctv(c["hi"]), what + ": upper end of that interval")
            if len(o["reps"]) > 1:
                add("B" + tok + col + "RepMin", pctv(min(c["per"])),
                    what + ": smallest value over the {} repeats{}".format(
                        len(o["reps"]), " (the same rule applied to each repeat)"
                        if col == "VThreeFidelity" else ""))
                add("B" + tok + col + "RepMax", pctv(max(c["per"])),
                    what + ": largest value over the {} repeats".format(len(o["reps"])))
    md("## Part B. Intervals for Table tab:e1 (gate stress test at the decision instant)", "",
       "Point values: n19_known_prompt_eval's records and measures on the published files "
       "(results/e1_eval_<arm>/, the t_d twin verdicts results/n11_e2e/twin/primary/ and "
       "rows_e1_primary.jsonl), constrained mode, issuable instructions, repeats pooled; each "
       "equals the table's macro (asserted: \\nElevenTabEOne<Arm><Column> for the seven "
       "gate columns, \\nSixteenFidelity<Arm>Share for the fidelity column, which is repeat 0 "
       "under N16 block H's rule on the parsed operations). Interval: 95% cluster bootstrap by "
       "instance (n2.Boot: seed 20261026, 20,000 replicates, 60 instances; a configuration's "
       "rows of one instance, all repeats, form one cluster; percentile interval of the pooled "
       "ratio), the interval of N16 block F and N18 block D. Repeats: the same share computed "
       "on each repeat alone; for the fidelity column the same rule applied to each repeat "
       "(the table prints repeat 0). A zero count gives the degenerate interval [0.0%, 0.0%].",
       "")
    body = []
    for cell, o in out.items():
        for col, c in o["cols"].items():
            body.append([o["disp"], B_COLS[col], c["macro"].replace("\\%", "%"),
                         "{}/{}".format(c["num"], c["den"]),
                         "[{}, {}]".format(pctpv(c["lo"]), pctpv(c["hi"])),
                         len(o["reps"]),
                         "{} to {}".format(pctpv(min(c["per"])), pctpv(max(c["per"])))
                         if len(o["reps"]) > 1 else "one repeat",
                         ", ".join(pctpv(v) for v in c["per"])])
    md_table(["configuration", "column", "table value", "count", "95% CI",
              "repeats", "min to max over repeats", "per repeat"], body)
    return out, cells_rows, ctx


# --------------------------------------------------------------------------- #
# Self-test: a second code path                                                #
# --------------------------------------------------------------------------- #
def boot_ci_here(inst_of, flags, instances):
    """A bootstrap written here with n2's seed and draw order (n20's self-test route)."""
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


def selftest(recs, rep, res1, res2, res3, res4, resb, fi2, fi4):
    """Two numbers per table recomputed from the raw files without the n13/n16/n20 loaders,
    labels or tallies; the per-order outcomes from numpy arrays of the changed orders."""
    rows = {}
    with open(ANALYSIS / "N11_rows_forecast.csv", encoding="utf-8") as fh:
        for x in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            rows.setdefault(x["reading"], {})[x["item_id"]] = x
    K, F = rows["K"], rows["FI"]
    items = {}
    with open(RESULTS / "n11_decision_time" / "items.jsonl", encoding="utf-8") as fh:
        for ln in fh:
            if ln.strip():
                o = json.loads(ln)
                if o["set"] == "published":
                    items[o["item_id"]] = o
    st_name = {"c09_storm2_w80": "Primary", "c10_storm2_w80": "Confirmation",
               "c10_replay_400": "Buildings"}
    ids = sorted(K)

    def costly(i, d):
        lo, hi = K[i]["orig_m_lo"], K[i]["orig_m_hi"]
        if lo == "" or hi == "":
            return None
        lo, hi = float(lo), float(hi)
        return 1 if lo > d else (0 if hi <= d else None)

    def refk(i, g, thr):
        v = K[i]["p_" + g]
        return v != "" and float(v) > thr

    def reff(i, g, thr):
        v = F[i]["p_" + g]
        return v != "" and float(v) > thr

    def twok(i):
        it = items[i]
        g = (it["dt_obj_orig"] - it["an_lb"]) / max(it["an_lb"], 1.0)
        return refk(i, "G-CERT", 0.20) or (K[i]["split"] == "field_changing" and g > 0.20)

    def arrays(ch):
        if not ch:
            return None
        a = np.array([[c[1], c[2], c[3], c[4], c[5]] for c in ch], dtype=float)
        return a

    def ul_and_max(ch):
        a = arrays(ch)
        if a is None:
            return False, 0.0
        cls, d, cn, cw = a[:, 0], a[:, 1], a[:, 3], a[:, 4]
        urg = (cls == 1) | (cls == 2)
        newly = urg & (cw - d > EPS) & ~(cn - d > EPS)
        inc = np.clip(cw - d, 0, None) - np.clip(cn - d, 0, None)
        mx = float(inc[urg].max()) if urg.any() else 0.0
        return bool(newly.any()), max(mx, 0.0)

    def grows(ch):
        a = arrays(ch)
        if a is None:
            return 0
        cls, d, cn, cw = a[:, 0], a[:, 1], a[:, 3], a[:, 4]
        inc = np.clip(cw - d, 0, None) - np.clip(cn - d, 0, None)
        return int((((cls == 1) | (cls == 2)) & (inc > GROW_BH)).sum())

    ul2, mx2, rk2, rf2 = {}, {}, {}, {}
    for i in ids:
        ul2[i], mx2[i] = ul_and_max(rep[i]["ch_real"])
        rk2[i] = ul_and_max(rep[i]["ch_k"])[0]
        rf2[i] = ul_and_max(rep[i]["ch_fi"])[0]

    def cmp(table, what, main, second):
        ok = str(main) == str(second)
        SELF.append((table, what, main, second, ok))
        check("self-test [{}] {}".format(table, what), ok, (main, second))

    # Table 1
    cmp("T1", "pooled urgent-late proposals", res1[("Pooled", "Twenty")]["ul"],
        sum(1 for i in ids if ul2[i]))
    bld = [i for i in ids if st_name[K[i]["stratum"]] == "Buildings"]
    cmp("T1", "Buildings urgent-late low-cost at delta 0.20",
        res1[("Buildings", "Twenty")]["ul_low"],
        sum(1 for i in bld if ul2[i] and costly(i, 0.20) == 0))
    cmp("T1", "pooled urgent-late costly at delta 0.10", res1[("Pooled", "Ten")]["ul_costly"],
        sum(1 for i in ids if ul2[i] and costly(i, 0.10) == 1))
    g1 = {i: grows(rep[i]["ch_real"]) for i in ids}
    cmp("T1", "pooled proposals that add more than 1 bh to an urgent order, low-cost at 0.20",
        res1[("Pooled", "Twenty")]["g1_low"],
        sum(1 for i in ids if g1[i] > 0 and costly(i, 0.20) == 0))
    cmp("T2", "G-CERT applied proposals that add more than 1 bh to an urgent order",
        res2[("Cert", "Pooled", "Twenty")]["grow1"],
        sum(1 for i in ids if g1[i] > 0 and not refk(i, "G-CERT", 0.20)))
    # Table 2
    app = [i for i in ids if not refk(i, "G-CERT", 0.20)]
    gl = [i for i in app if ul2[i] and costly(i, 0.20) == 0]
    cmp("T2", "G-CERT applied, urgent-late, low-cost, pooled, delta 0.20",
        res2[("Cert", "Pooled", "Twenty")]["ul_low"], len(gl))
    abs_app = [i for i in ids if not refk(i, "D-ABS", 0.8119)]
    cmp("T2", "D-ABS applied urgent-late, pooled", res2[("Abs", "Pooled", "Twenty")]["ul"],
        sum(1 for i in abs_app if ul2[i]))
    gu = [mx2[i] for i in app if ul2[i]]
    cmp("T2", "G-CERT: 90th percentile of the largest added urgent tardiness (bh)",
        bh2(res2[("Cert", "Pooled", "Twenty")]["dist"][1]),
        bh2(float(np.percentile(np.array(gu), 90)) if gu else None))
    two_app = [i for i in ids if not twok(i)]
    cmp("T2", "G-CERT with the second price: applied urgent-late low-cost, Primary",
        res2[("CertTwo", "Primary", "Twenty")]["ul_low"],
        sum(1 for i in two_app if ul2[i] and costly(i, 0.20) == 0
            and st_name[K[i]["stratum"]] == "Primary"))
    # Table 3
    cmp("T3", "field edits applied by G-CERT that are urgent-late",
        res3[("Cert", "field_changing", "Twenty")]["ul"],
        sum(1 for i in app if ul2[i] and K[i]["split"] == "field_changing"))
    cmp("T3", "sequencing-only urgent-late proposals (all priced)",
        res3[("T1", "sequencing_only", "Twenty")]["ul"],
        sum(1 for i in ids if ul2[i] and K[i]["split"] == "sequencing_only"))
    # Table 4
    low = [i for i in ids if costly(i, 0.20) == 0]
    cmp("T4", "rule alone: low-cost referred, pooled", res4[("Rule", "Pooled", "Twenty")]["l_ref"],
        sum(1 for i in low if rk2[i]))
    ul_ids = [i for i in ids if ul2[i]]
    fl = [not (refk(i, "G-CERT", 0.20) or rk2[i]) for i in ul_ids]
    lo, hi = boot_ci_here([K[i]["instance_id"] for i in ul_ids], fl,
                          {items[i]["instance_id"] for i in items})
    o = res4[("CertRule", "Pooled", "Twenty")]
    cmp("T4", "gate plus rule: urgent-late applied share and 95% interval",
        "{} [{}, {}]".format(pct(o["u_app"], o["ul"]), pctv(o["u_lo"]), pctv(o["u_hi"])),
        "{} [{}, {}]".format(pct(sum(fl), len(fl)), pctv(lo), pctv(hi)))
    # Table 5 (FI): two numbers
    fapp = [i for i in ids if not reff(i, "G-CERT", 0.20)]
    cmp("T5", "FI: G-CERT applied urgent-late low-cost, pooled",
        fi2[("Cert", "Pooled", "Twenty")]["ul_low"],
        sum(1 for i in fapp if ul2[i] and costly(i, 0.20) == 0))
    cmp("T5", "FI: rule alone urgent-late applied, pooled",
        fi4[("Rule", "Pooled", "Twenty")]["u_app"], sum(1 for i in ul_ids if not rf2[i]))
    # Part B: from the twin verdict files with the json module
    suite = {}
    with open(n13.IN["suite"], encoding="utf-8") as fh:
        for ln in fh:
            if ln.strip():
                o = json.loads(ln)
                suite[o["item_id"]] = o
    iss = set()
    with open(RESULTS / "n11_e2e" / "items.jsonl", encoding="utf-8") as fh:
        for ln in fh:
            if ln.strip():
                o = json.loads(ln)
                if o["issuable"] and o["item_id"] in suite:
                    iss.add(o["item_id"])
    blocked = {"blocked_schema", "blocked_feas", "blocked_qual"}

    def verdicts(src, cfg):
        out = []
        with open(RESULTS / "n11_e2e" / "twin" / "primary" / src / "verdicts_{}.jsonl".format(
                cfg), encoding="utf-8") as fh:
            for ln in fh:
                if ln.strip():
                    v = json.loads(ln)
                    if v["mode"] == "M_constrained" and v["item_id"] in iss:
                        out.append(v)
        return out

    vq = [v for v in verdicts("e1_eval_qwen14b", "G_CERT")
          if suite[v["item_id"]]["primary_class"] == "V5" and not v["infra"]]
    per = []
    for k in sorted({int(v["repeat"]) for v in vq}):
        vk = [v for v in vq if int(v["repeat"]) == k]
        per.append(sum(1 for v in vk if v["terminal"] in blocked) / len(vk))
    q = resb[("qwen3-14b", "-")]["cols"]["VFive"]
    cmp("B", "Qwen3-14B V5 blocked: min and max over repeats",
        "{} to {}".format(pctv(min(q["per"])), pctv(max(q["per"]))),
        "{} to {}".format(pctv(min(per)), pctv(max(per))))
    vs = [v for v in verdicts("e1_eval_sonnet5", "G_CERT")
          if suite[v["item_id"]]["primary_class"] == "benign" and not v["infra"]]
    lo, hi = boot_ci_here([v["instance_id"] for v in vs],
                          [v["terminal"] in blocked for v in vs],
                          {o["instance"]["instance_id"] for o in suite.values()})
    s = resb[("sonnet", "disabled")]["cols"]["BenignCert"]
    cmp("B", "Claude Sonnet 5 benign false-block rate (G-CERT): value and 95% interval",
        "{} [{}, {}]".format(pctv(s["value"]), pctv(s["lo"]), pctv(s["hi"])),
        "{} [{}, {}]".format(pctv(sum(1 for v in vs if v["terminal"] in blocked) / len(vs)),
                             pctv(lo), pctv(hi)))


def fresh_replay(tasks, rep, picks):
    """A second replay of sample instances in the parent process; every per-order list equal."""
    global _TASKS
    _TASKS = tasks
    n = 0
    for ti, t in enumerate(tasks):
        if t["iid"] not in picks:
            continue
        r = replay_instance(ti)
        for x in r["items"]:
            y = rep[x["item_id"]]
            for k in ("ch_real", "ch_k", "ch_fi"):
                check("fresh replay reproduces {} on {}".format(k, x["item_id"]),
                      json.dumps(x[k]) == json.dumps(y[k]))
            for b in ("dt", "rw", "fi"):
                check("fresh replay reproduces {} totals on {}".format(b, x["item_id"]),
                      x[b] == y[b])
            n += 1
    return n


# --------------------------------------------------------------------------- #
# Backing rows                                                                 #
# --------------------------------------------------------------------------- #
def write_rows(recs):
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        fh.write("# N23 ({}): one row per priced proposal of the direct benchmark at t_d (1,356); "
                 "urgent = original priority class 1 or 2; newly late = on time without the "
                 "proposal and late with it on the original due date (C - d > 1e-9 bh); real_* = "
                 "the realised full-window run from t_d against the no-proposal run (= the no-AI "
                 "anchor); k_* = the known board at t_d with and without the proposal (the "
                 "per-order rule refers when k_urgent_late = 1); fi_* = the full-information "
                 "board at t_d; max_add = the largest tardiness added to one urgent order (bh); "
                 "grow1 = urgent orders whose tardiness grows by more than 1 bh; ref_K_<design> / "
                 "ref_FI_<design> = the published referral flags at each design's own "
                 "threshold; costly_d020 / costly_d010: 1 costly, 0 low-cost, empty undecided "
                 "(whole-board label)\n".format(VERSION))
        w = csv.writer(fh, lineterminator="\n")
        head = ["item_id", "instance_id", "stratum", "primary_class", "edit_type", "n_ops",
                "costly_d020", "costly_d010", "damage_bh", "real_wt_with_bh",
                "real_wt_without_bh", "real_urgent_late", "real_n_urgent_late",
                "real_n_late_class1", "real_n_late_class2", "real_n_late_any",
                "real_max_add_urgent_bh", "real_max_add_order", "real_n_urgent_grow1",
                "real_urgent_wt_delta_bh", "real_n_changed", "real_urgent_late_ids",
                "k_urgent_late", "k_n_urgent_late", "k_max_add_urgent_bh", "fi_urgent_late",
                "fi_n_urgent_late", "fi_max_add_urgent_bh"]
        head += ["ref_K_" + t for t in DESIGNS] + ["ref_FI_" + t for t in DESIGNS]
        w.writerow(head)
        for r in recs:
            c2, c1 = n13.costly_of(r, 0.20), n13.costly_of(r, 0.10)
            x = r["rep"]
            s = r["site_n"]
            o, k, f = r["real"], r["kb"], r["fib"]
            w.writerow([r["item_id"], r["instance_id"], r["st"], r["primary_class"], r["split"],
                        r["n_ops"], "" if c2 is None else c2, "" if c1 is None else c1,
                        "{:.4f}".format(r["dmg"]), "{:.4f}".format(x["rw"]["sum_orig"]),
                        "{:.4f}".format(s["rw0"]["sum_orig"]), int(o["urgent_late"]),
                        o["n_urgent_late"], o["late_by_cls"][1], o["late_by_cls"][2],
                        o["n_late_any"], "{:.4f}".format(o["max_add"]), o["max_add_id"],
                        o["grow1"], "{:.4f}".format(o["wt_urgent"]), o["n_changed"],
                        "|".join(o["urgent_ids"]), int(k["urgent_late"]), k["n_urgent_late"],
                        "{:.4f}".format(k["max_add"]), int(f["urgent_late"]), f["n_urgent_late"],
                        "{:.4f}".format(f["max_add"])]
                       + [int(r["d_k_" + t]) for t in DESIGNS]
                       + [int(r["d_f_" + t]) for t in DESIGNS])


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main(argv):
    selftest_only = "--selftest" in argv
    t_start = time.time()
    for k, p in IN23.items():
        if not Path(p).is_file() and k not in NOT_SHIPPED_OK:
            raise SystemExit("missing input {}: {}".format(k, p))
    hashes, items_dt, _pub, boot, fc = n13.load_inputs()
    check("60 bootstrap clusters, 20,000 replicates, n2 seed",
          boot.k == 60 and boot.idx.shape == (20000, 60) and n2.SEED == 20261026)
    recs, by, spfi, site, _frecs = n20.build(items_dt, fc, boot)
    check("1,356 priced proposals", len(recs) == 1356, len(recs))
    dc = D.Checker()
    suite = OrderedDict((r["item_id"], r) for r in D.load_published(dc))
    check("published suite loads through suite_gate (SHA-256 asserted)", not dc.failures)
    tasks = build_tasks(recs, suite, by)
    check("60 instances carry a priced proposal", len(tasks) == 60, len(tasks))
    print("[n23] replaying {} proposals on {} instances, {} workers on cores {}".format(
        len(recs), len(tasks), len(CORES), CORES), flush=True)
    t_rep = time.time()
    results = run_replay(tasks, len(CORES))
    wall_rep = time.time() - t_rep
    return finish(selftest_only, t_start, hashes, boot, recs, by, spfi, site, tasks, results,
                  wall_rep)


def finish(selftest_only, t_start, hashes, boot, recs, by, spfi, site, tasks, results, wall_rep):
    """Everything after the replay: the run-fatal tie to the stored totals, then the tables."""
    rep, sites = assert_replay(results, recs, by)
    print("[n23] replay asserted ({:.0f}s): every per-order sum equals its stored total".format(
        wall_rep), flush=True)
    attach(recs, rep, sites)
    MD.extend(["# N23: urgent orders made late by a proposal, and intervals for the stress-test "
               "table ({})".format(VERSION), "",
               "Generated by `code/scripts/n23_urgent_orders.py` on cores 12-13 (one thread per "
               "process): deterministic dispatcher replays (n11_decision_time.gen_price, no "
               "solver, no time budget) and recounts of the logged results; no model call, no "
               "GPU. Reused: n20.build's records (n16/n18/n13 loaded from source with the core "
               "allowance set to 12-13 in memory; files untouched), n13.costly_of, the published "
               "flags, n20's second price, n2.Boot (seed {}, {} replicates, {} instance "
               "clusters), n19's Table 6 records and measures. Macros: analysis/N23_macros.tex "
               "(prefix \\nTwentyThree), copied to manuscript/macros_n23.tex. Rows: "
               "analysis/N23_rows.csv.".format(n2.SEED, n2.B_BOOT, boot.k), "",
               "Definitions. Urgent order = an order of priority class 1 or 2 on the original "
               "fields (Section sec:prob-env, Table tab:env-provenance: class 1 has the 24-hour "
               "response target, SLA 8 bh, tardiness weight 8; class 2 the 72-hour target, SLA "
               "24 bh, weight 4; classes 3 and 4 have 14 and 30 days, SLA 80 and 171.4 bh, "
               "weights 2 and 1; planned maintenance takes class 4). Newly late = finishes on "
               "time without the proposal and late with it, on the original due date (C - d > "
               "1e-9 bh; schedule times carry four decimals). Realised = the full-window run "
               "from t_d with the proposal against the run without it (the schedule the realised "
               "damage is measured against; its weighted tardiness equals the no-AI anchor). "
               "Applied = not referred by the design on the stated reading. Low-cost / costly = "
               "the whole-board label at delta. bh = business hours (eight per weekday).", ""])
    section0(boot, recs, by, spfi, site, results, wall_rep)
    section_assert()
    res1 = table1(recs)
    list_urgent_late(recs)
    res2 = table2(recs, "K")
    md("## Table 2. Urgent-late proposals among those each design applies (known board)", "",
       "Each design at its own threshold, decided on the known board at t_d (the published "
       "flags; the second price is n20's two_k: G-CERT, or on a field edit the second price "
       "above 0.20). Urgent-late applied = applied and urgent-late in the realised run. Of "
       "which low-cost = the cases of the limitations row (one urgent order made late while "
       "the board's realised cost stays at most delta). Max add = largest tardiness added to one "
       "urgent order, median / 90th percentile / maximum over the applied urgent-late proposals "
       "(and over the low-cost ones among them). Rows at delta = 0.10 are pooled only (the "
       "per-stratum counts at 0.10 are macros).", "")
    md_table2(res2, "K")
    res3 = table3(recs, "K")
    md("## Table 3. Tables 1 and 2 by operation type (known board)", "",
       "Operation type of the reference proposal (N11 op_split): sequencing only, field edits "
       "(the proposal sets a priority or reassigns a window), no operation.", "")
    md_table3(res3)
    res4, agree4 = table4(boot, recs, "K")
    md("## Table 4. The per-order rule on the known board", "",
       "Rule: refer a proposal when, on the known board at t_d (the orders the site knows, "
       "dispatched from t_d with and without the proposal, N11's dt and an runs), it makes an "
       "order of class 1 or 2 newly late on the original due dates. Only what is known at t_d "
       "enters the rule. Outcomes are measured on the realised run and the whole-board label. "
       "Intervals: 95% cluster bootstrap over the 60 instances (n2 seed 20261026, 20,000 "
       "replicates), the interval the other shares use; costly applied over the costly, "
       "low-cost referred over the low-cost, urgent-late applied over the urgent-late.", "")
    md_table4(res4, agree4, "K")
    # FI reading (summary only)
    fi2 = table2(recs, "FI")
    fi3 = table3(recs, "FI")
    fi4, fiag = table4(boot, recs, "FI")
    md("## Table 5. Tables 2 to 4 with full information (summary only)", "",
       "Each design's full-information flag (the same gate at t_d with every order of the "
       "window known; the second price is n20's two_f), and the per-order rule on the "
       "full-information board (every order of the window except those completed at t_d, "
       "dispatched from t_d with and without the proposal: n11_forecast's FI board). Table 1 "
       "does not depend on the reading (realised outcome).", "", "### 5a. Table 2 with full "
       "information", "")
    md_table2(fi2, "FI")
    md("### 5b. Table 3 with full information", "")
    md_table3(fi3)
    md("### 5c. Table 4 with full information", "")
    md_table4(fi4, fiag, "FI")
    resb, _b_rows, _ctx = part_b()
    # self-test
    selftest(recs, rep, res1, res2, res3, res4, resb, fi2, fi4)
    picks = sorted({t["iid"] for t in tasks if "replay" in t["iid"]})[:1] + \
        sorted({t["iid"] for t in tasks if "c09_storm" in t["iid"]})[:1]
    n_fresh = fresh_replay(tasks, rep, set(picks))
    SELF.append(("replay", "fresh replay in the parent process of every proposal on {}".format(
        ", ".join(picks)), "{} proposals".format(n_fresh), "identical per-order lists and "
        "totals", True))
    md("## Self-test (second code path)", "",
       "Each number below is recomputed from analysis/N11_rows_forecast.csv, "
       "results/n11_decision_time/items.jsonl and the twin verdict files with the csv and json "
       "modules (no n13/n16/n20 loader, label or tally), the per-order outcomes from numpy "
       "arrays of the changed orders, and the intervals by a bootstrap written here with the n2 "
       "seed and draw order; the replay of two instances is repeated in the parent process.",
       "")
    md_table(["table", "number", "main path", "second path", "equal"],
             [[b, w, m, s, "yes" if ok else "NO"] for b, w, m, s, ok in SELF])
    n_reused = n16.NCHECK[0] + n18.NCHECK[0] + n20.NCHECK[0] + len(n13.CHECKS)
    wall = time.time() - t_start
    msg = ("[n23] {} macros, {} assertions passed (+{} in the reused functions); self-test {} of "
           "{} equal; replay {:.0f}s, total {:.0f}s".format(
               len(NAMES), NCHECK[0], n_reused, sum(1 for x in SELF if x[4]), len(SELF),
               wall_rep, wall))
    if selftest_only:
        print(msg + " (self-test mode: nothing written)")
        return 0
    paths = OrderedDict(list(n13.IN.items()) + list(IN23.items()))
    h = OrderedDict(hashes)
    h.update((k, input_sha256(k, p)) for k, p in IN23.items())
    for nm in ("n23_urgent_orders.py", "n20_stratum_abs.py", "n19_known_prompt_eval.py",
               "n11_decision_time.py", "n8_causal.py"):
        h["code " + nm] = n13.sha256(SCRIPTS_DIR / nm)
        paths["code " + nm] = SCRIPTS_DIR / nm
    MD.extend(["## Inputs", ""] + ["- {} `{}` sha256 {}".format(
        k, Path(paths[k]).relative_to(ROOT), v) for k, v in h.items()] + [""])
    MD.append("{} assertions passed in n23 (plus {} in the reused functions); self-test {} of {} "
              "numbers equal on the second code path; {} macros; replay {:.0f} s, total {:.0f} s."
              .format(NCHECK[0], n_reused, sum(1 for x in SELF if x[4]), len(SELF), len(NAMES),
                      wall_rep, wall))
    write_rows(recs)
    OUT_TEX.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    shutil.copyfile(OUT_TEX, OUT_MANU)
    OUT_MD.write_text("\n".join(MD) + "\n", encoding="utf-8")
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
