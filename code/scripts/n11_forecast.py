#!/usr/bin/env python
"""N11 Stage 3: the decision-time gate priced on the known board plus a forecast of later arrivals.

QUESTION
--------
Stages 1 and 2 price every proposal on the board the site knows at the
decision instant t_d (K).  Against the realised full-window cost every design
misses part of the costly proposals.  Stage 3 prices each proposal on K plus
sampled futures of the corrective orders that arrive after t_d, aggregates the
sampled prices into one price per design, and scores the dispositions against
the realised full-window cost.  The design is
the pre-specified design ("design"); the project's
decisions are the pre-specified design ("design").

READINGS (design, reading labels)
---------------------------------
K      known orders only (Stage 2's primary census rows, S = 0)
F2     K plus sampled corrective arrivals, load estimated by the site: storm
       strata from the arrivals observed in [0, t_d] shrunk to the campus's
       long-run level (one business hour of prior exposure); recorded stratum
       by resampling the campus's 76 other training windows (primary forecast)
F1     K plus sampled arrivals from the process the instance was drawn from
       (storm: the pack at the instance's multiplier; recorded: the window's own
       later orders, resampled), an upper reading
F3-/+  F1 with the load scaled by 0.5 and 1.5 (robustness)
FI     K plus the instance's own later orders (the bound)
P0     the published full board at t = 0

Every board is priced by Stage 1's ``gen_price`` unchanged, with the running-
work rule of Stage 3 addition A.  Futures are keyed by the board (instance,
t_d, reading, s), so a proposal and its anchor share every future.

SUBCOMMANDS
-----------
smoke    3 instances (one per stratum), every reading, the Monte Carlo error
         measurement that fixes S, every assertion, determinism (run twice)
direct   the direct benchmark, every reading (cores 8-11, 4 workers)
e2e      Stage 2's priced end-to-end units (E1, N3 and gold) under F2, F1, FI
analyse  rows, twins, macros, the Stage 3 summary part and the figure data

Every assertion group AF0-AF10 of design Section 7 is run-fatal.
Version: l1-n11-forecast-1
"""

from __future__ import annotations

import os
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import n11_decision_time as D  # noqa: E402  (sets L1_INSTANCE_ROOT to the snapshot)

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import time  # noqa: E402
from collections import Counter, OrderedDict, defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

VERSION = "l1-n11-forecast-1"
ROOT = D.ROOT
RESULTS = D.RESULTS
ANALYSIS = D.ANALYSIS
OUTF = RESULTS / "n11_forecast"
Y1_ROOT = Path(((os.environ.get("L1_Y1_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "PaperY-FMScheduling")) + ""))
SNAPSHOT_INDEX = Path(D.SNAPSHOT_ROOT) / "index.csv"
PACKS = OrderedDict([
    ("c09_storm2_w80", Y1_ROOT / "results" / "p2_generator" / "params_c9.json"),
    ("c10_storm2_w80", Y1_ROOT / "results" / "r4_final" / "gen_params" / "params_c10.json")])
MULTIPLIER = {"c09_storm2_w80": 5.985174971179965, "c10_storm2_w80": 18.01040912557983}
STORM = ("c09_storm2_w80", "c10_storm2_w80")
RECORDED = "c10_replay_400"
POOL_IDS = tuple("c10_replay_400_{:04d}".format(i) for i in range(24, 100))
H0_BH = 1.0
M0 = 1.0
S_MAIN = 20
S_F3 = 10
SPOT_EVERY = 25
S_TOPUP = 50
MC_SE_GATE = 0.01
BOOT_MC_B = 2000
BOOT_MC_SEED = 20261104
SEED_TAG = "l1-n11-forecast-1"
READ_F = ("F2", "F1", "F3-", "F3+")
READ_ALL = ("K", "F2", "F1", "F3-", "F3+", "FI", "P0")
F3_SCALE = {"F3-": 0.5, "F3+": 1.5}
SETTINGS = OrderedDict([("G-CERT", D.TAU), ("G-CERT-M", D.TAU), ("D-REL1", D.DG14["D-REL1"]),
                        ("D-REL2", D.DG14["D-REL2"]), ("D-ABS", D.DG14["D-ABS"])])
DESIGNS = tuple(SETTINGS)
UNIONS = ("G-CERT|D-REL2", "G-CERT-M|D-REL2")
CORES_OK = (8, 9, 10, 11)
TOL = 1e-6


# --------------------------------------------------------------------------- #
# Utilities                                                                    #
# --------------------------------------------------------------------------- #
def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sha_obj(obj) -> str:
    return hashlib.sha256(canon(obj).encode("utf-8")).hexdigest()


def future_seed(iid, t_d, reading, s) -> int:
    """seed = first 8 bytes of SHA-256("l1-n11-forecast-1|iid|t_d|reading|s") mod 2^63."""
    key = "{}|{}|{:.6f}|{}|{}".format(SEED_TAG, iid, float(t_d), reading, int(s))
    return int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "big") % (2 ** 63)


def ensure_dir(p) -> Path:
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p


def stratum_of(iid) -> str:
    for st in D.STRATA:
        if iid.startswith(st):
            return st
    raise ValueError(iid)


def import_y1():
    """Y1's generator and time axis, imported read-only (no bytecode in the Y1 tree)."""
    src = str(Y1_ROOT / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    prev = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        from fmwos import generator as gen
        from fmwos import timeaxis as ta
    finally:
        sys.dont_write_bytecode = prev
    return gen, ta


# --------------------------------------------------------------------------- #
# The forecast model (design Section 1)                                        #
# --------------------------------------------------------------------------- #
def load_pack(stratum) -> dict:
    return json.loads(PACKS[stratum].read_text())


def cm_pack(pack) -> dict:
    """The corrective-only pack: rate_tr (1 - pm_share_tr), pm_share 0, marks unchanged."""
    out = json.loads(json.dumps(pack))
    for tp in out["trades"].values():
        rate = float(tp.get("arrival_rate_per_bh", 0.0))
        tp["arrival_rate_per_bh"] = rate * (1.0 - float(tp.get("pm_share", 0.0)))
        tp["pm_share"] = 0.0
    return out


def lambda1(pack) -> float:
    """Corrective arrival rate at multiplier 1 (orders per business hour)."""
    return sum(float(tp["arrival_rate_per_bh"]) * (1.0 - float(tp.get("pm_share", 0.0)))
               for tp in pack["trades"].values() if float(tp.get("arrival_rate_per_bh", 0.0)) > 0)


def observed_multiplier(inst, t_d, lam1, h0=H0_BH, m0=M0) -> dict:
    """F2's load level: m_hat = (N_obs + h0 Lambda1 m0) / (Lambda1 (t_d + h0))."""
    n_obs = sum(1 for wo in inst["work_orders"]
                if not wo.get("is_pm") and float(wo["release_bh"]) <= float(t_d))
    m_hat = (n_obs + h0 * lam1 * m0) / (lam1 * (float(t_d) + h0))
    return {"n_obs": n_obs, "m_hat": m_hat}


def _cm_order(fid, trade, p_bh, release, prio, sla, weight) -> dict:
    r = round(float(release), 4)
    return {"id": fid, "trade": str(trade), "p_bh": float(p_bh), "release_bh": r,
            "due_bh": round(r + sla[int(prio)], 4), "priority": int(prio),
            "weight": weight[int(prio)], "building": None, "is_pm": False}


def storm_future(gen, ta, cm, m, t_d, H, seed, tag) -> tuple:
    """One storm future: Y1's ``generate_window`` on the corrective pack, shifted by t_d."""
    W = float(H) - float(t_d)
    meta = {"seed": int(seed), "m": float(m), "window": W, "redrawn": False}
    if W <= 0.0 or m <= 0.0:
        return [], meta
    inst = gen.generate_window(cm, W, int(seed), 1.0, float(m))
    if inst["meta"].get("redrawn"):
        # The generator's empty-draw guard fired: the future is empty (never conditioned).
        meta["redrawn"] = True
        return [], meta
    out = []
    for k, wo in enumerate(inst["work_orders"]):
        if wo.get("is_pm"):
            raise SystemExit("AF3 FAILURE: the corrective pack drew a planned order")
        out.append(_cm_order("F{}.{}".format(tag, k), wo["trade"], wo["p_bh"],
                             float(wo["release_bh"]) + float(t_d), wo["priority"],
                             ta.SLA_BH, ta.WEIGHT))
    return out, meta


def corrective_tuples(inst, lo=None, hi=None) -> list:
    """(release, trade, priority, p_bh) of the corrective orders with lo < release <= hi."""
    out = []
    for wo in inst["work_orders"]:
        if wo.get("is_pm"):
            continue
        r = float(wo["release_bh"])
        if lo is not None and not r > lo:
            continue
        if hi is not None and r > hi:
            continue
        out.append((r, str(wo["trade"]), int(wo["priority"]), float(wo["p_bh"])))
    return out


def replay_future_pool(pool, t_d, H, rng, tag, ta) -> tuple:
    """Recorded F2: concatenated resampled campus windows, orders in (t_d, H]."""
    rows, used, offset, guard = [], [], 0.0, 0
    while offset < float(H):
        j = int(rng.integers(0, len(pool)))
        w = pool[j]
        used.append(w["id"])
        for (r, tr, pr, p) in w["cm"]:
            rr = round(r + offset, 4)
            if rr > float(t_d) and rr <= float(H):
                rows.append((rr, tr, pr, p))
        offset += float(w["W"])
        guard += 1
        if guard > 100000:
            raise SystemExit("AF3 FAILURE: pool resampling does not cover the horizon")
    rows.sort(key=lambda x: x[0])
    out = [_cm_order("F{}.{}".format(tag, k), tr, p, r, pr, ta.SLA_BH, ta.WEIGHT)
           for k, (r, tr, pr, p) in enumerate(rows)]
    return out, {"windows": used, "n_windows": len(used)}


def replay_future_own(own, n, rng, tag, ta) -> tuple:
    """Recorded F1/F3: n tuples resampled with replacement from the window's own later orders."""
    if not own or n <= 0:
        return [], {"n_source": len(own), "n_drawn": 0}
    idx = rng.choice(len(own), size=int(n), replace=True)
    rows = sorted((own[int(i)] for i in idx), key=lambda x: x[0])
    out = [_cm_order("F{}.{}".format(tag, k), tr, p, r, pr, ta.SLA_BH, ta.WEIGHT)
           for k, (r, tr, pr, p) in enumerate(rows)]
    return out, {"n_source": len(own), "n_drawn": int(n)}


def load_pool(check) -> list:
    """The 76 other campus-10 400-order training windows, hashed into manifest_pool.json."""
    import csv

    idx = {}
    with open(SNAPSHOT_INDEX, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            idx[r["id"]] = r
    pool, man = [], OrderedDict()
    for pid in POOL_IDS:
        r = idx.get(pid)
        check.true("AF7", "pool window {} is in the snapshot index".format(pid), r is not None)
        if r is None:
            continue
        check.true("AF7", "pool window {} is a training window".format(pid), r["split"] == "train",
                   r["split"])
        path = Path(D.SNAPSHOT_ROOT) / r["path"]
        man[pid] = D.sha256_file(path)
        inst = D.load_instance(path)
        pool.append({"id": pid, "W": float(inst["meta"]["window_bh"]),
                     "cm": corrective_tuples(inst), "anchor": inst["meta"]["window_start"]})
    mpath = OUTF / "manifest_pool.json"
    if mpath.is_file():
        old = json.loads(mpath.read_text())
        check.true("AF7", "pool manifest unchanged since the first run", old["windows"] == man,
                   sorted(k for k in man if old["windows"].get(k) != man[k])[:5])
    else:
        D.write_json(mpath, {"version": VERSION, "created": D.now_iso(), "windows": man})
    return pool


# --------------------------------------------------------------------------- #
# Per-future pricing helpers                                                    #
# --------------------------------------------------------------------------- #
PRICE_FIELDS = ("term_cert", "stage_cert", "term_feas", "stage_feas", "codes", "obj", "obj_orig",
                "lb", "lb_running", "gap", "ref2", "ref2_from")


def slim(res) -> dict:
    return {k: res.get(k) for k in PRICE_FIELDS}


def prices_of(p, a) -> dict:
    """Every design's price of proposal record ``p`` against anchor record ``a`` (design 3)."""
    out = {g: None for g in DESIGNS}
    out["D-ABS-orig"] = None
    if p is None or p.get("stage_cert") != "qual" or a is None or a.get("obj") is None:
        return out
    obj, ref1, ref2 = p["obj"], a["obj"], p["ref2"]
    out["G-CERT"] = p["gap"]
    out["G-CERT-M"] = None if p["gap"] is None or a["gap"] is None else p["gap"] - a["gap"]
    out["D-REL1"] = D.rel_delta(obj, ref1)
    out["D-REL2"] = None if ref2 is None else D.rel_delta(obj, ref2)
    out["D-ABS"] = round(obj - ref1, D.ROUND_BH)
    if p.get("obj_orig") is not None and a.get("obj_orig") is not None:
        out["D-ABS-orig"] = round(p["obj_orig"] - a["obj_orig"], D.ROUND_BH)
    return out


def mc_boot_index(S):
    import numpy as np

    rng = np.random.default_rng(BOOT_MC_SEED)
    return rng.integers(0, S, size=(BOOT_MC_B, S))


_BOOT_IDX: dict = {}


def aggregate(vals, setting=None) -> dict:
    """Median (primary), 80th percentile, mean, spread, refer share, MC interval of the median."""
    import numpy as np

    xs = [v for v in vals if v is not None]
    out = {"n": len(xs), "median": None, "p80": None, "mean": None, "sd": None, "iqr": None,
           "refer_share": None, "mc_se": None, "ci_lo": None, "ci_hi": None, "undecided": False}
    if not xs:
        return out
    a = np.asarray(xs, dtype=float)
    out["median"] = float(np.median(a))
    out["p80"] = float(np.percentile(a, 80))
    out["mean"] = float(a.mean())
    out["sd"] = float(a.std(ddof=1)) if len(a) > 1 else 0.0
    out["iqr"] = float(np.percentile(a, 75) - np.percentile(a, 25))
    out["mc_se"] = 1.253 * out["sd"] / math.sqrt(len(a))
    if setting is not None:
        out["refer_share"] = float(np.mean(a > setting))
    if len(a) > 1:
        S = len(a)
        if S not in _BOOT_IDX:
            _BOOT_IDX[S] = mc_boot_index(S)
        meds = np.median(a[_BOOT_IDX[S]], axis=1)
        out["ci_lo"], out["ci_hi"] = (float(np.percentile(meds, 2.5)),
                                      float(np.percentile(meds, 97.5)))
        out["boot_se"] = float(meds.std(ddof=1))
        if setting is not None:
            out["undecided"] = bool(out["ci_lo"] <= setting < out["ci_hi"])
    return out


def undecided_any(per_future) -> list:
    """Designs whose median is MC-undecided at the frozen setting."""
    out = []
    for g, s in SETTINGS.items():
        ag = aggregate([pf[g] for pf in per_future], s)
        if ag["undecided"]:
            out.append(g)
    return out


# --------------------------------------------------------------------------- #
# Model expectations for AF3 (arrival counts and marks)                         #
# --------------------------------------------------------------------------- #
def _phi(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _Phi(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def clipped_log_moments(mu, sigma, floor, cap) -> tuple:
    """E[Y] and E[Y^2] of Y = clip(N(mu, sigma), log floor, log cap)."""
    a, b = math.log(floor), math.log(cap)
    if sigma <= 0:
        y = min(b, max(a, mu))
        return y, y * y
    al, be = (a - mu) / sigma, (b - mu) / sigma
    pa, pb = _Phi(al), _Phi(be)
    m1 = a * pa + mu * (pb - pa) + sigma * (_phi(al) - _phi(be)) + b * (1.0 - pb)
    m2 = (a * a * pa + b * b * (1.0 - pb) + (mu * mu + sigma * sigma) * (pb - pa)
          + 2.0 * mu * sigma * (_phi(al) - _phi(be))
          + sigma * sigma * (al * _phi(al) - be * _phi(be)))
    return m1, m2


def storm_model(pack, gen) -> dict:
    """Per unit of exposure (m W = 1): expected count, per-priority counts and log-p moments."""
    cap = float(pack["labor_cap"])
    out = {"rate": 0.0, "prio": Counter(), "l1": 0.0, "l2": 0.0}
    for tr, tp in pack["trades"].items():
        lam = float(tp.get("arrival_rate_per_bh", 0.0)) * (1.0 - float(tp.get("pm_share", 0.0)))
        if lam <= 0:
            continue
        out["rate"] += lam
        dist = tp.get("cm_priority_dist", {"3": 1.0})
        tot = sum(float(dist.get(str(c), 0.0)) for c in (1, 2, 3, 4))
        for c in (1, 2, 3, 4):
            out["prio"][c] += lam * (float(dist.get(str(c), 0.0)) / tot if tot > 0 else
                                     (1.0 if c == 3 else 0.0))
        m1, m2 = clipped_log_moments(float(tp.get("logn_mu", 0.0)),
                                     float(tp.get("logn_sigma", 0.0)), gen.P_BH_FLOOR, cap)
        out["l1"] += lam * m1
        out["l2"] += lam * m2
    return out


def pool_moments(pool, t_d, H, n_draw=300, seed=7) -> dict:
    """Recorded F2: Monte Carlo moments of one future's count, priority counts and log-p sum."""
    import numpy as np

    rng = np.random.default_rng(seed)
    pre = []
    for w in pool:
        rel = np.array([x[0] for x in w["cm"]], dtype=float)
        order = np.argsort(rel, kind="stable")
        rel = rel[order]
        pr = np.array([x[2] for x in w["cm"]], dtype=int)[order]
        lp = np.log(np.array([x[3] for x in w["cm"]], dtype=float))[order]
        cum = {c: np.concatenate([[0], np.cumsum(pr == c)]) for c in (1, 2, 3, 4)}
        pre.append((rel, cum, np.concatenate([[0.0], np.cumsum(lp)]), float(w["W"])))
    vals = []
    for _ in range(n_draw):
        offset, n, cs, ls = 0.0, 0, Counter(), 0.0
        while offset < float(H):
            rel, cum, cl, W = pre[int(rng.integers(0, len(pre)))]
            shifted = np.round(rel + offset, 4)
            lo = int(np.searchsorted(shifted, float(t_d), side="right"))
            hi = int(np.searchsorted(shifted, float(H), side="right"))
            if hi > lo:
                n += hi - lo
                for c in (1, 2, 3, 4):
                    cs[c] += int(cum[c][hi] - cum[c][lo])
                ls += float(cl[hi] - cl[lo])
            offset += W
        vals.append([n] + [cs[c] for c in (1, 2, 3, 4)] + [ls])
    a = np.asarray(vals, dtype=float)
    return {"mean": a.mean(axis=0).tolist(), "var": a.var(axis=0, ddof=1).tolist()}


def own_moments(own) -> dict:
    """Per drawn order: priority shares and log-p mean/variance of the window's own later orders."""
    if not own:
        return {"q": {c: 0.0 for c in (1, 2, 3, 4)}, "l1": 0.0, "lvar": 0.0}
    n = float(len(own))
    q = {c: sum(1 for x in own if x[2] == c) / n for c in (1, 2, 3, 4)}
    ls = [math.log(x[3]) for x in own]
    m1 = sum(ls) / n
    return {"q": q, "l1": m1, "lvar": sum((v - m1) ** 2 for v in ls) / n}


# --------------------------------------------------------------------------- #
# The worker: one instance, every unit on it, every reading                     #
# --------------------------------------------------------------------------- #
_TASKS: list = []


def _empty_af3():
    return {"N": 0.0, "E": 0.0, "V": 0.0, "C": [0.0] * 4, "EC": [0.0] * 4, "VC": [0.0] * 4,
            "L": 0.0, "EL": 0.0, "VL": 0.0, "n_futures": 0, "release_bad": 0, "due_bad": 0,
            "id_collide": 0, "trade_unstaffed": 0}


def forecast_instance(ti) -> dict:
    """Every reading's prices of one instance's units (design Sections 2-4)."""
    import numpy as np
    from l1adapter import dispatch as dispatch_mod
    import n8_causal as n8

    gen, ta = import_y1()
    task = _TASKS[ti]
    t0 = time.perf_counter()
    inst = D.load_instance(task["path"])
    iid = inst["meta"]["id"]
    st_name = stratum_of(iid)
    H = float(inst["meta"]["window_bh"])
    baseline = dispatch_mod.dispatch_baseline(inst, "atc", 0)
    trajs = {fk: n8.trajectory(inst, seed, baseline) for fk, seed in task["seeds"].items()}
    inst_ids = {wo["id"] for wo in inst["work_orders"]}
    staffed = {t["trade"] for t in inst["technicians"]}
    readings = OrderedDict(task["readings"])          # name -> S
    out = {"iid": iid, "stratum": st_name, "k": {}, "k_anchor": {}, "futures": [],
           "anchors": [], "prices": [], "fi": [], "af": [], "af3": {}, "af1": [],
           "open_trades": [], "topup": {}, "mhat": {}, "names_running": {}, "counts": Counter()}
    sites = {}
    pack = cm = model = lam1_ = None
    if st_name in STORM:
        pack = load_pack(st_name)
        cm = cm_pack(pack)
        model = storm_model(pack, gen)
        lam1_ = lambda1(pack)
        mult = float(inst["meta"]["arrival_multiplier"])
    pool = task.get("pool")

    def fail(group, what, detail=""):
        out["af"].append([group, "{} on {}: {}".format(what, iid, detail)])

    def site(fk, t_d):
        key = (fk, t_d)
        if key in sites:
            return sites[key]
        seed = task["seeds"][fk]
        traj = trajs[fk]
        state = n8.site_state(inst, traj, t_d, pm_known=True)
        known = n8.known_instance(inst, state)
        kf = D.kf_fix(state, seed)
        started = state["completed"] + state["in_progress"]
        k_ids = state["queue"] + state["in_progress"] + state["scheduled"]
        base_p = n8.pin_schedule(baseline, traj, started)
        sit = D.site_of(state, traj, t_d)
        slot = {a["wo"]: a for a in traj["assignments"]}
        by = {wo["id"]: wo for wo in inst["work_orders"]}
        c_done = sum(float(by[o]["weight"]) * max(0.0, float(slot[o]["end_bh"]) -
                                                  float(by[o]["due_bh"]))
                     for o in state["completed"])
        s = {"state": state, "known": known, "kf": kf, "k_ids": k_ids, "base_p": base_p,
             "site": sit, "run": list(state["in_progress"]), "c_done": c_done,
             "seed_unknown": bool(set(seed) & set(state["unknown"])),
             "completed": set(state["completed"])}
        sites[key] = s
        return s

    def price_at(board, s, raw, t_d, keep_live=False, ref2=True):
        return D.gen_price(board, raw, s["kf"], s["base_p"], t_d, ref2=ref2,
                           keep_batch=s["k_ids"], running_ids=s["run"], keep_live=keep_live)

    # ---- S = 0: K for every unit (AF0) and the names-running census
    units = task["units"]
    changed = {}
    for u in units:
        s = site(u["fk"], u["t_d"])
        if (u["fk"], u["t_d"]) not in out["k_anchor"]:
            a = price_at(s["known"], s, D.EMPTY_RAW, u["t_d"], ref2=False)
            out["k_anchor"][(u["fk"], u["t_d"])] = slim(a)
        r = price_at(s["known"], s, u["raw"], u["t_d"])
        out["k"][u["uid"]] = slim(r)
        changed[u["uid"]] = {t[0] for t in (r.get("tuples") or [])}
        ops = r.get("ops")
        if ops is None:
            try:
                ops = json.loads(u["raw"])["operations"]
            except Exception:  # noqa: BLE001 - a text that does not parse names nothing
                ops = []
        try:
            explicit, members = n8.named_orders(ops, inst)
        except Exception:  # noqa: BLE001
            explicit, members = [], []
        out["names_running"][u["uid"]] = sorted((set(explicit) | set(members)) & set(s["run"]))
    # End-to-end mode: units whose strictly parsed operations and schema findings agree on K
    # share one pricing per board (Stage 2's memo key); every SPOT_EVERY-th member is priced
    # again on the first future of each reading and must match (AF4).
    rep_of = {}
    if task.get("memo"):
        from l1guard import guard as G
        from l1guard.config import G_CERT

        first = {}
        for u in units:
            if not u["forecast"]:
                continue
            s = site(u["fk"], u["t_d"])
            s_find, typed, parse = G._stage_schema(s["known"], u["raw"], G_CERT)
            if typed is None or any(f.blocking for f in s_find):
                continue
            mk = (u["fk"], u["t_d"], json.dumps([op.to_dict() for op in typed], sort_keys=True),
                  json.dumps(sorted((f.code, f.severity) for f in s_find)), bool(parse.get("ok")))
            if mk in first:
                rep_of[u["uid"]] = first[mk]
            else:
                first[mk] = u["uid"]
        out["counts"]["memo_members"] = len(rep_of)
    fc_units = [u for u in units if u["forecast"] and u["uid"] not in rep_of]
    fut0 = {}
    by_td = OrderedDict()
    for u in sorted(fc_units, key=lambda x: (x["t_d"], x["uid"])):
        by_td.setdefault(u["t_d"], []).append(u)

    own_cache = {}
    per_unit = defaultdict(list)

    def own_of(t_d):
        if t_d not in own_cache:
            own_cache[t_d] = corrective_tuples(inst, lo=t_d, hi=H)
        return own_cache[t_d]

    def load_of(reading, t_d):
        if st_name in STORM:
            if reading == "F2":
                mh = observed_multiplier(inst, t_d, lam1_)
                out["mhat"][t_d] = dict(mh, m_true=mult)
                return mh["m_hat"]
            return mult * F3_SCALE.get(reading, 1.0)
        return None

    def make_future(reading, t_d, s_idx):
        seed = future_seed(iid, t_d, reading, s_idx)
        tag = str(s_idx)
        if st_name in STORM:
            m = load_of(reading, t_d)
            fut, meta = storm_future(gen, ta, cm, m, t_d, H, seed, tag)
            exp = {"E": model["rate"] * m * max(0.0, H - t_d)}
            exp["V"] = exp["E"]
            exp["EC"] = [model["prio"][c] * m * max(0.0, H - t_d) for c in (1, 2, 3, 4)]
            exp["VC"] = list(exp["EC"])
            exp["EL"] = model["l1"] * m * max(0.0, H - t_d)
            exp["VL"] = model["l2"] * m * max(0.0, H - t_d)
            meta["load"] = m
        else:
            rng = np.random.default_rng(seed)
            if reading == "F2":
                fut, meta = replay_future_pool(pool, t_d, H, rng, tag, ta)
                key = ("pool", t_d)
                if key not in own_cache:
                    own_cache[key] = pool_moments(pool, t_d, H)
                pm = own_cache[key]
                exp = {"E": pm["mean"][0], "V": pm["var"][0], "EC": pm["mean"][1:5],
                       "VC": pm["var"][1:5], "EL": pm["mean"][5], "VL": pm["var"][5]}
            else:
                own = own_of(t_d)
                n = len(own)
                if reading in F3_SCALE:
                    n = int(math.floor(F3_SCALE[reading] * len(own) + 0.5))
                fut, meta = replay_future_own(own, n, rng, tag, ta)
                om = own_moments(own)
                exp = {"E": float(n), "V": 0.0,
                       "EC": [n * om["q"][c] for c in (1, 2, 3, 4)],
                       "VC": [n * om["q"][c] * (1 - om["q"][c]) for c in (1, 2, 3, 4)],
                       "EL": n * om["l1"], "VL": n * om["lvar"]}
            meta["seed"] = int(seed)
        # AF3 bookkeeping
        acc = out["af3"].setdefault(reading, _empty_af3())
        acc["n_futures"] += 1
        acc["N"] += len(fut)
        acc["E"] += exp["E"]
        acc["V"] += exp["V"]
        acc["L"] += sum(math.log(wo["p_bh"]) for wo in fut)
        acc["EL"] += exp["EL"]
        acc["VL"] += exp["VL"]
        for j, c in enumerate((1, 2, 3, 4)):
            acc["C"][j] += sum(1 for wo in fut if wo["priority"] == c)
            acc["EC"][j] += exp["EC"][j]
            acc["VC"][j] += exp["VC"][j]
        for wo in fut:
            if not (t_d - 1e-9 <= wo["release_bh"] <= H + 1e-9):
                acc["release_bad"] += 1
            if abs(wo["due_bh"] - round(wo["release_bh"] + ta.SLA_BH[wo["priority"]], 4)) > 1e-9:
                acc["due_bad"] += 1
            if wo["id"] in inst_ids:
                acc["id_collide"] += 1
            if wo["trade"] not in staffed:
                acc["trade_unstaffed"] += 1
        rec = OrderedDict(iid=iid, t_d=t_d, reading=reading, s=s_idx, seed=meta.get("seed"),
                          n=len(fut), per_trade=dict(sorted(Counter(w["trade"] for w in fut)
                                                            .items())),
                          sum_p=round(sum(w["p_bh"] for w in fut), 6),
                          load=meta.get("load"), windows=meta.get("windows"),
                          redrawn=meta.get("redrawn", False), sha=sha_obj(fut))
        out["futures"].append(rec)
        return fut

    def board_with(known, fut):
        b = {k: v for k, v in known.items() if k != "work_orders"}
        b["work_orders"] = list(known["work_orders"]) + list(fut)
        return b

    def price_board(reading, t_d, s_idx, fut, us, census_open=False):
        fks = sorted({u["fk"] for u in us})
        anc = {}
        for fk in fks:
            s = site(fk, t_d)
            board = board_with(s["known"], fut)
            a = price_at(board, s, D.EMPTY_RAW, t_d, keep_live=census_open, ref2=False)
            if census_open:
                open_census(board, s, a, fut, reading, t_d, s_idx, fk)
                a.pop("_live", None)
            anc[fk] = slim(a)
            if a["lb"] is not None and a["obj"] is not None and a["lb"] > a["obj"] + TOL:
                fail("AF6", "anchor LB above obj (t_d={}, {}, s={})".format(t_d, reading, s_idx))
            out["anchors"].append({"fk": fk, "t_d": t_d, "reading": reading, "s": s_idx,
                                   "a": anc[fk], "sha": sha_obj(anc[fk])})
        for u in us:
            s = site(u["fk"], t_d)
            board = board_with(s["known"], fut)
            p = slim(price_at(board, s, u["raw"], t_d))
            pr = prices_of(p, anc[u["fk"]])
            check_future(u, p, anc[u["fk"]], pr, reading, s_idx)
            out["prices"].append({"uid": u["uid"], "reading": reading, "s": s_idx, "p": p,
                                  "prices": pr})
            per_unit[(u["uid"], reading)].append(pr)
        return anc

    def check_future(u, p, a, pr, reading, s_idx):
        k = out["k"][u["uid"]]
        tag = "{} {} s={}".format(u["uid"], reading, s_idx)
        if p["stage_cert"] == "schema" and k["stage_cert"] != "schema":
            fail("AF5", "stage-1 verdict differs from K", tag)
        if p["stage_cert"] != k["stage_cert"]:
            out["counts"]["stage_diff_" + reading] += 1
        if p["lb"] is not None and p["obj"] is not None and p["lb"] > p["obj"] + TOL:
            fail("AF6", "proposal LB above obj", tag)
        if u.get("empty"):
            ok = (p["obj"] == a["obj"] and p["gap"] == a["gap"] and p["lb"] == a["lb"]
                  and pr["G-CERT-M"] == 0.0)
            if not ok:
                fail("AF2", "empty proposal differs from its anchor", tag)
        if p["stage_cert"] == "qual" and p.get("ref2_from") == "identical_by_construction":
            if pr["D-REL2"] != 0.0:
                fail("AF2", "D-REL2 of a non-constraining proposal is not 0", tag)

    def open_census(board, s, a, fut, reading, t_d, s_idx, fk):
        """Open trades of an anchor board (LB2 per trade against the best executed upper end)."""
        live = a.get("_live") or {}
        if "schedule" not in live:
            return
        sit = dict(s["site"])
        sit["known_ids"] = list(sit["known_ids"]) + [w["id"] for w in fut]
        rec, _lv = D.board_record(board, iid, sit, [])
        run_ids = {r[0] for r in sit["running"]}
        ex = D.trade_wwt_of(live["adjusted"].instance, live["schedule"], skip=run_ids)
        for tr, tv in rec["trades"].items():
            up = min(tv["atc"], ex.get(tr, 0.0))
            out["open_trades"].append(OrderedDict(
                iid=iid, t_d=t_d, fk=fk, reading=reading, s=s_idx, trade=tr,
                n_orders=tv["n_orders"], n_techs=tv["n_techs"], lb2=tv["lb2"], atc=tv["atc"],
                exec=ex.get(tr, 0.0), open=bool(up > tv["lb2"] + D.CLOSE_TOL_BH)))

    # ---- the forecast readings, board by board
    for t_d, us in by_td.items():
        for reading, S_r in readings.items():
            if reading == "FI":
                continue
            for s_idx in range(S_r):
                fut = make_future(reading, t_d, s_idx)
                if s_idx == 0:
                    fut0[(reading, t_d)] = fut
                census = bool(task.get("open_trades")) and reading == "F1" and s_idx < 3
                price_board(reading, t_d, s_idx, fut, us, census_open=census)
            if task.get("topup") and reading in ("F1", "F2") and S_r < S_TOPUP:
                und = {u["uid"]: undecided_any(per_unit[(u["uid"], reading)]) for u in us}
                need = [u for u in us if und[u["uid"]]]
                for u in need:
                    out["topup"].setdefault(reading, []).append([u["uid"], und[u["uid"]]])
                if need:
                    for s_idx in range(S_r, S_TOPUP):
                        fut = make_future(reading, t_d, s_idx)
                        price_board(reading, t_d, s_idx, fut, need)
        if "FI" in readings:
            for fk in sorted({u["fk"] for u in us}):
                s = site(fk, t_d)
                done = s["completed"]
                fi = {k: v for k, v in inst.items() if k != "work_orders"}
                fi["work_orders"] = [wo for wo in inst["work_orders"] if wo["id"] not in done]
                a = slim(price_at(fi, s, D.EMPTY_RAW, t_d, ref2=False))
                out["anchors"].append({"fk": fk, "t_d": t_d, "reading": "FI", "s": 0, "a": a,
                                       "sha": sha_obj(a)})
                if a["lb"] is not None and a["obj"] is not None and a["lb"] > a["obj"] + TOL:
                    fail("AF6", "FI anchor LB above obj", t_d)
                for u in [x for x in us if x["fk"] == fk]:
                    p = slim(price_at(fi, s, u["raw"], t_d))
                    pr = prices_of(p, a)
                    check_future(u, p, a, pr, "FI", 0)
                    out["prices"].append({"uid": u["uid"], "reading": "FI", "s": 0, "p": p,
                                          "prices": pr})
                    # AF1: the full-window board reproduces the realised run
                    if s["seed_unknown"] or u.get("rw_obj") is None or p["obj"] is None:
                        out["counts"]["af1_skipped"] += 1
                        continue
                    if changed.get(u["uid"], set()) & done:
                        out["counts"]["af1_skipped_completed_field"] += 1
                        continue
                    c = s["c_done"]
                    rec = {"uid": u["uid"], "t_d": t_d,
                           "obj_fi": p["obj"], "rw_obj": u["rw_obj"], "c_done": c,
                           "an_fi": a["obj"], "rw0_obj": u.get("rw0_obj"),
                           "obj_orig_fi": p["obj_orig"], "rw_obj_orig": u.get("rw_obj_orig"),
                           "an_orig_fi": a["obj_orig"], "rw0_obj_orig": u.get("rw0_obj_orig")}
                    out["af1"].append(rec)
                    if abs(p["obj"] - (u["rw_obj"] - c)) > TOL:
                        fail("AF1", "FI proposal obj != rw_obj - completed constant",
                             "{} {} vs {}".format(u["uid"], p["obj"], u["rw_obj"] - c))
                    if u.get("rw0_obj") is not None and abs(a["obj"] - (u["rw0_obj"] - c)) > TOL:
                        fail("AF1", "FI anchor obj != rw0_obj - completed constant",
                             "{} {} vs {}".format(u["uid"], a["obj"], u["rw0_obj"] - c))
                    if u.get("rw_obj_orig") is not None and p["obj_orig"] is not None and \
                            abs(p["obj_orig"] - (u["rw_obj_orig"] - c)) > TOL:
                        fail("AF1", "FI proposal original-field obj != rw_obj_orig - constant",
                             "{} {} vs {}".format(u["uid"], p["obj_orig"], u["rw_obj_orig"] - c))
                    if u.get("rw0_obj_orig") is not None and \
                            abs(a["obj_orig"] - (u["rw0_obj_orig"] - c)) > TOL:
                        fail("AF1", "FI anchor original-field obj != rw0_obj_orig - constant",
                             "{} {} vs {}".format(u["uid"], a["obj_orig"], u["rw0_obj_orig"] - c))
    if rep_of:
        by_uid = defaultdict(list)
        for p in out["prices"]:
            by_uid[p["uid"]].append(p)
        u_of = {u["uid"]: u for u in units}
        for j, (m_uid, r_uid) in enumerate(sorted(rep_of.items())):
            if canon(out["k"][m_uid]) != canon(out["k"][r_uid]):
                fail("AF4", "memo member priced differently on K", "{} as {}".format(m_uid, r_uid))
            for p in by_uid[r_uid]:
                out["prices"].append({"uid": m_uid, "reading": p["reading"], "s": p["s"],
                                      "p": p["p"], "prices": p["prices"], "memo_of": r_uid})
            if j % SPOT_EVERY:
                continue
            u = u_of[m_uid]
            s = site(u["fk"], u["t_d"])
            out["counts"]["memo_spot_checked"] += 1
            for (reading, t_d), fut in fut0.items():
                if t_d != u["t_d"]:
                    continue
                got = slim(price_at(board_with(s["known"], fut), s, u["raw"], t_d))
                want = [p["p"] for p in by_uid[r_uid] if p["reading"] == reading and p["s"] == 0]
                if not want or canon(got) != canon(want[0]):
                    fail("AF4", "memo spot check differs", "{} as {} {}".format(
                        m_uid, r_uid, reading))
    out["counts"] = dict(out["counts"])
    out["k_anchor"] = {"{}|{}".format(k[0], k[1]): v for k, v in out["k_anchor"].items()}
    out["mhat"] = {str(k): v for k, v in out["mhat"].items()}
    out["wall_s"] = time.perf_counter() - t0
    return out


# --------------------------------------------------------------------------- #
# Driver: inputs, tasks, the pool with per-instance parts                       #
# --------------------------------------------------------------------------- #
def code_sha() -> dict:
    return {"n11_forecast.py": D.sha256_file(Path(__file__)),
            "n11_decision_time.py": D.sha256_file(Path(D.__file__)),
            "n8_causal.py": D.sha256_file(Path(SCRIPTS_DIR) / "n8_causal.py")}


def load_forecast_inputs(check) -> dict:
    """Suite, Stage 2's census rows (hash-checked), the packs and the pool (AF7)."""
    import suite_gate as sg

    pub_rows = D.load_published(check)          # suite SHA-256 and row count (A1 labels)
    check.true("AF7", "suite SHA-256 is the published one",
               D.sha256_file(sg.SUITE_PATH) == sg.SUITE_SHA256)
    cmeta = json.loads((D.OUT / "census_meta.json").read_text())
    crep = json.loads((D.OUT / "census_assertions.json").read_text())
    check.true("AF7", "Stage 2 primary census passed", crep.get("status") == "PASS",
               crep.get("status"))
    for name, digest in cmeta["outputs"].items():
        got = D.sha256_file(D.OUT / name)
        check.true("AF7", "Stage 2 census output {} carries the hash its meta wrote".format(name),
                   got == digest, got[:16])
    check.true("AF7", "Stage 2 census used the fixed frozen set",
               cmeta.get("frozen_set") == "fix" and cmeta.get("reading") == "primary")
    items = D.read_jsonl(D.OUT / "items.jsonl")
    packs = OrderedDict((st, D.sha256_file(p)) for st, p in PACKS.items())
    pool = load_pool(check)
    check.true("AF7", "76 pool windows", len(pool) == 76, len(pool))
    paths = {}
    for it in pub_rows:
        iid = it["instance"]["instance_id"]
        if iid not in paths:
            paths[iid] = D.instance_path(it)     # suite_gate, manifest-verified (AF7)
    for st, m in MULTIPLIER.items():
        for iid, pth in paths.items():
            if iid.startswith(st):
                got = D.load_instance(pth)["meta"]["arrival_multiplier"]
                check.true("AF7", "arrival multiplier of {}".format(iid), got == m, got)
    return {"pub": OrderedDict((r["item_id"], r) for r in pub_rows), "items": items,
            "census_meta": cmeta, "packs": packs, "pool": pool, "paths": paths}


def direct_units(inp, check, instances=None) -> list:
    """One task per instance: every published issuable item (forecast if priced on K)."""
    tasks = OrderedDict()
    for r in inp["items"]:
        if r["set"] != "published" or not r["issuable"]:
            continue
        iid = r["instance_id"]
        if instances and iid not in instances:
            continue
        it = inp["pub"][r["item_id"]]
        if iid not in tasks:
            path = D.instance_path(it)           # manifest-verified (AF7)
            tasks[iid] = {"iid": iid, "path": path, "units": [], "seeds": OrderedDict()}
        t = tasks[iid]
        seed = list(it["episode"]["frozen_seed"] or [])
        fk = D.frozen_key(seed)
        check.true("AF7", "frozen key of {} equals the census".format(r["item_id"]),
                   fk == r["frozen_seed"])
        t["seeds"].setdefault(fk, seed)
        ops = D.canonical_ops(it)
        t["units"].append({"uid": r["item_id"], "fk": fk, "t_d": float(r["t_d"]),
                           "raw": json.dumps({"operations": ops}), "forecast":
                           r["dt_stage_cert"] == "qual", "empty": not ops,
                           "rw_obj": r["rw_obj"], "rw_obj_orig": r["rw_obj_orig"],
                           "rw0_obj": r["rw0_obj"], "rw0_obj_orig": r["rw0_obj_orig"]})
    return list(tasks.values())


def e2e_units(inp, check, instances=None) -> tuple:
    """Stage 2's priced end-to-end inputs (E1 rows, N3 m10/m11, gold), deduplicated."""
    e2e = RESULTS / "n11_e2e"
    rep = json.loads((e2e / "e2e_assertions.json").read_text())
    check.true("AF7", "Stage 2 e2e replay passed", rep.get("status") == "PASS")
    meta = json.loads((e2e / "e2e_meta.json").read_text())
    for name, digest in meta["outputs"].items():
        check.true("AF7", "Stage 2 e2e output {} carries its hash".format(name),
                   D.sha256_file(e2e / name) == digest)
    sites = {(s["iid"], s["fk"], float(s["t_d"])): s for s in D.read_jsonl(e2e / "sites.jsonl")}
    tasks = OrderedDict()
    refs = OrderedDict()

    def unit(iid, fk, seed, t_d, raw, ref, kind, rw=None, empty=False):
        if instances and iid not in instances:
            return None
        key = sha_obj([iid, fk, float(t_d), D.raw_key(raw)])[:20]
        it_path = inp["paths"][iid]
        t = tasks.setdefault(iid, {"iid": iid, "path": it_path, "units": [],
                                   "seeds": OrderedDict(), "_seen": set()})
        t["seeds"].setdefault(fk, seed)
        if key not in t["_seen"]:
            t["_seen"].add(key)
            st = sites.get((iid, fk, float(t_d))) or {}
            t["units"].append({"uid": key, "fk": fk, "t_d": float(t_d),
                               "raw": raw, "forecast": True,
                               "empty": bool(empty), "rw_obj": (rw or {}).get("rw_obj"),
                               "rw_obj_orig": (rw or {}).get("rw_obj_orig"),
                               "rw0_obj": st.get("rw0_obj"), "rw0_obj_orig": st.get("rw0_obj_orig")})
        refs.setdefault(key, []).append((kind, ref))
        return key

    seeds_of = {}
    for it in inp["pub"].values():
        seeds_of[it["item_id"]] = list(it["episode"]["frozen_seed"] or [])
    ext = D.load_ext(check)
    for it in ext.values():
        seeds_of[it["item_id"]] = list(it["episode"]["frozen_seed"] or [])
    # The raw texts Stage 2 priced: E1 by (source, item, mode, thinking, repeat); N3 by its
    # disposition key, with the v10 view priced as m10 and the flag payload as m11.
    from l1guard.guard_v11 import read_flag, v10_view

    e1_raw = {(r["src"], r["item_id"], r["mode"], r["thinking"], r["repeat"]): r["raw"]
              for r in D.load_e1(check)}
    n3_raw = {}
    for r in D.load_n3(check):
        d = r["disp"]
        n3_raw[(r["src"], d["arm"], d["item_id"], d["mode"], d.get("thinking"),
                d.get("repeat"))] = r["raw"]
    e1_keys = []
    for r in D.read_jsonl(e2e / "rows_e1_primary.jsonl"):
        if r.get("model_refused") or r.get("stage_cert") != "qual":
            continue
        raw = e1_raw[(r["src"], r["item_id"], r["mode"], r["thinking"], r["repeat"])]
        k = unit(r["instance_id"], r["frozen_seed"], seeds_of[r["item_id"]], r["t_d"],
                 raw, r, "e1", r, empty=r.get("n_ops") == 0)
        if k:
            e1_keys.append(((r["src"], r["item_id"], r["mode"], r["thinking"], r["repeat"]), k))
    n3_keys = []
    for r in D.read_jsonl(e2e / "rows_n3.jsonl"):
        if r.get("refusal"):
            continue
        for mk in ("m10", "m11"):
            m = r[mk]
            if m.get("stage_cert") != "qual":
                continue
            rw = r.get("rw10" if mk == "m10" else "rw11")
            if mk == "m11" and r.get("flag_blocking"):
                continue                 # Stage 2 prices no m11 behind a blocking flag
            text = n3_raw[(r["src"],) + tuple(r["disp_key"])]
            raw = v10_view(text) if mk == "m10" else read_flag(text)[0]
            k = unit(r["instance_id"], r["frozen_seed"], seeds_of[r["item_id"]], r["t_d"],
                     raw, m, "n3", rw, empty=m.get("n_ops") == 0)
            if k:
                n3_keys.append(((r["src"],) + tuple(r["disp_key"]) + (mk,), k))
    import n11_stage2 as S2

    gold_ops = S2.n3_gold_ops(check)
    items_e2e = {r["item_id"]: r for r in D.read_jsonl(e2e / "items.jsonl")}
    gold_keys = []
    for g in D.read_jsonl(e2e / "gold.jsonl"):
        td = g.get("td")
        if not td or td.get("cert") is None:
            continue
        iid_ = g["item_id"]
        it = inp["pub"].get(iid_) or ext.get(iid_)
        inst_id = it["instance"]["instance_id"]
        seed = seeds_of[iid_]
        t_d = items_e2e[iid_]["t_d"]["primary"]
        k = unit(inst_id, D.frozen_key(seed), seed, t_d, {"operations": gold_ops[iid_]}, td,
                 "gold", empty=not gold_ops[iid_])
        if k:
            gold_keys.append((iid_, k))
    out = []
    for t in tasks.values():
        t.pop("_seen")
        out.append(t)
    return out, refs, {"e1": e1_keys, "n3": n3_keys, "gold": gold_keys}


def task_order(tasks) -> list:
    return sorted(range(len(tasks)), key=lambda i: (
        0 if "c10_storm" in tasks[i]["iid"] else 1 if "c09_storm" in tasks[i]["iid"] else 2,
        -sum(1 for u in tasks[i]["units"] if u["forecast"])))


def run_parts(tasks, part_dir, cores, workers, cfg_sha, label):
    """The pool, writing one part per instance as it finishes (resume by config hash)."""
    import multiprocessing as mp
    import pickle

    global _TASKS
    ensure_dir(part_dir)
    results, todo = {}, []
    for i, t in enumerate(tasks):
        pth = part_dir / "{}.pkl".format(t["iid"])
        if pth.is_file():
            with open(pth, "rb") as fh:
                got = pickle.load(fh)
            if got.get("_cfg") == cfg_sha and got.get("_task_sha") == sha_obj(
                    {k: v for k, v in t.items() if k != "pool"}):
                results[t["iid"]] = got
                continue
        todo.append(i)
    _TASKS = tasks
    order = [i for i in task_order(tasks) if i in set(todo)]
    print("[n11f {}] {} instances ({} from parts), {} to run on cores {} with {} workers".format(
        label, len(tasks), len(results), len(order), cores, workers), flush=True)

    def keep(res):
        t = tasks[[k for k, x in enumerate(tasks) if x["iid"] == res["iid"]][0]]
        res["_cfg"] = cfg_sha
        res["_task_sha"] = sha_obj({k: v for k, v in t.items() if k != "pool"})
        tmp = part_dir / "{}.pkl.tmp".format(res["iid"])
        with open(tmp, "wb") as fh:
            pickle.dump(res, fh)
        os.replace(tmp, part_dir / "{}.pkl".format(res["iid"]))
        results[res["iid"]] = res
        print("[n11f {}]   done {} ({:.0f}s), {} of {}".format(
            label, res["iid"], res["wall_s"], len(results), len(tasks)), flush=True)

    if order:
        if workers <= 1:
            D._winit(cores)
            for i in order:
                keep(forecast_instance(i))
        else:
            ctx = mp.get_context("fork")
            with ctx.Pool(workers, initializer=D._winit, initargs=(cores,),
                          maxtasksperchild=2) as pool:
                for res in pool.imap_unordered(forecast_instance, order):
                    keep(res)
    return results


def check_cores(cores) -> list:
    if set(cores) - set(CORES_OK) and not os.environ.get("CERTIGATE_ANY_CORES"):
        raise SystemExit("REFUSING TO RUN: Stage 3 runs on cores 8-11 only, got {}".format(cores))
    foreign = D.foreign_on_cores(set(cores))
    if foreign:
        raise SystemExit("REFUSING TO RUN: foreign processes on cores {}: {}".format(cores,
                                                                                     foreign))
    return foreign


# --------------------------------------------------------------------------- #
# Run-level assertions over the parts                                           #
# --------------------------------------------------------------------------- #
K_FIELDS = (("term_cert", "dt_term_cert"), ("stage_cert", "dt_stage_cert"),
            ("term_feas", "dt_term_feas"), ("stage_feas", "dt_stage_feas"),
            ("obj", "dt_obj"), ("obj_orig", "dt_obj_orig"), ("lb", "dt_lb"), ("gap", "dt_gap"),
            ("ref2", "dt_ref2"))


def assert_k_direct(check, results, items, krows) -> dict:
    """AF0: S = 0 reproduces Stage 2's primary census rows and prices exactly (==)."""
    by = {r["item_id"]: r for r in items}
    kp = {r["item_id"]: r for r in krows}
    touched = []
    for res in results.values():
        for uid, k in res["k"].items():
            r = by[uid]
            names = res["names_running"].get(uid) or []
            for mine, theirs in K_FIELDS:
                check.true("AF0", "{} equals Stage 2 {} on {}".format(mine, theirs, uid),
                           k[mine] == r[theirs], "{!r} vs {!r}".format(k[mine], r[theirs]))
            if k["codes"] != r["dt_codes"]:
                if names and D.RUNNING_WORK_CODE in (k["codes"] or []):
                    touched.append(uid)
                else:
                    check.true("AF0", "codes equal Stage 2 on " + uid, False,
                               "{} vs {}".format(k["codes"], r["dt_codes"]))
            a = res["k_anchor"]["{}|{}".format(r["frozen_seed"], float(r["t_d"]))]
            for mine, theirs in (("obj", "an_obj"), ("gap", "an_gap"), ("lb", "an_lb"),
                                 ("obj_orig", "an_obj_orig")):
                check.true("AF0", "anchor {} equals Stage 2 {} on {}".format(mine, theirs, uid),
                           a[mine] == r[theirs], "{!r} vs {!r}".format(a[mine], r[theirs]))
            if r["dt_stage_cert"] == "qual":
                pr = prices_of(k, a)
                for g in DESIGNS:
                    check.true("AF0", "price {} equals the Stage 2 row on {}".format(g, uid),
                               pr[g] == kp[uid]["p_" + g], "{!r} vs {!r}".format(
                                   pr[g], kp[uid]["p_" + g]))
    return {"rule_touched": sorted(touched)}


def assert_k_e2e(check, results, refs) -> dict:
    n = 0
    for res in results.values():
        for uid, k in res["k"].items():
            for kind, ref in refs[uid]:
                n += 1
                tag = "{} {}".format(kind, uid)
                if kind == "gold":
                    check.true("AF0", "gold certificate price equals Stage 2 on " + tag,
                               k["stage_cert"] == "qual" and k["gap"] == ref["cert"],
                               "{} vs {}".format(k["gap"], ref["cert"]))
                    continue
                for f in ("term_cert", "stage_cert", "obj", "obj_orig", "lb", "gap", "ref2",
                          "codes"):
                    check.true("AF0", "{} equals Stage 2 on {}".format(f, tag), k[f] == ref[f],
                               "{!r} vs {!r}".format(k[f], ref[f]))
    return {"compared": n}


def assert_runs(check, results, smoke=False) -> dict:
    """AF1-AF6, AF8 and AF9 over the worker outputs."""
    summ = {"af3": {}, "af8": {}, "stage_diff": Counter(), "af1_rows": 0, "topup": Counter()}
    for res in results.values():
        for grp, msg in res["af"]:
            check.true(grp, msg, False)
        summ["af1_rows"] += len(res["af1"])
        for k, v in res["counts"].items():
            summ["stage_diff"][k] += v
        for rd, lst in res["topup"].items():
            summ["topup"][rd] += len(lst)
        st = res["stratum"]
        for rd, a in res["af3"].items():
            acc = summ["af3"].setdefault((st, rd), _empty_af3())
            for k, v in a.items():
                if isinstance(v, list):
                    acc[k] = [x + y for x, y in zip(acc[k], v)]
                else:
                    acc[k] += v
        for t_d, mh in res["mhat"].items():
            summ["af8"].setdefault(st, []).append((float(t_d), mh["m_hat"], mh["m_true"]))
    # AF3: arrival counts, priority counts, log-p sums against the model
    for (st, rd), a in sorted(summ["af3"].items()):
        tag = "{} {}".format(D.STRATUM_NAME[st], rd)
        for what, n_, e_, v_ in [("orders", a["N"], a["E"], a["V"])] + \
                [("priority {} orders".format(c), a["C"][j], a["EC"][j], a["VC"][j])
                 for j, c in enumerate((1, 2, 3, 4))] + [("log p_bh sum", a["L"], a["EL"], a["VL"])]:
            if v_ <= 1e-12:
                ok = abs(n_ - e_) <= 1e-6 * max(1.0, abs(e_))
                z = 0.0 if ok else float("inf")
            else:
                z = (n_ - e_) / math.sqrt(v_)
                ok = abs(z) <= 4.0
            a.setdefault("z", {})[what] = z
            check.true("AF3", "{}: sampled {} within 4 SD of the model (z={:.2f})".format(
                tag, what, z), ok, "{} vs {}".format(n_, e_))
        for k in ("release_bad", "due_bad", "id_collide", "trade_unstaffed"):
            check.true("AF3", "{}: {} = 0".format(tag, k), a[k] == 0, a[k])
    # AF8: m_hat = 1 exactly at t_d = 0; the band at t_d >= 20 is reported
    for st, lst in summ["af8"].items():
        for t_d, mh, mt in lst:
            if t_d == 0.0:
                check.true("AF8", "m_hat = 1 at t_d = 0 ({})".format(st), mh == 1.0, mh)
    return summ


def af4_compare(a, b) -> list:
    """Determinism: every future hash and every price row byte-identical."""
    bad = []
    for key in ("futures", "anchors", "prices", "k", "k_anchor", "af3", "mhat", "open_trades"):
        if canon(a.get(key)) != canon(b.get(key)):
            bad.append(key)
    return bad


# --------------------------------------------------------------------------- #
# Subcommands                                                                  #
# --------------------------------------------------------------------------- #
def k_rows(items):
    """Stage 2's analysed rows (prices and truths on K), rebuilt in memory by Stage 1's code."""
    td_br, _br_all, _boards, _src = D.board_brackets_or_closed(D.OUT)
    return D.build_rows(items, td_br, D.full_brackets(), D.load_anchor_records())


def readings_for(S, mode) -> OrderedDict:
    if mode == "direct":
        return OrderedDict([("F2", S), ("F1", S), ("F3-", S_F3), ("F3+", S_F3), ("FI", 1)])
    return OrderedDict([("F2", S), ("F1", S), ("FI", 1)])


def prepare(tasks, inp, readings, topup, open_trades):
    for t in tasks:
        t["readings"] = list(readings.items())
        t["topup"] = topup
        t["open_trades"] = open_trades
        t["pool"] = inp["pool"] if t["iid"].startswith(RECORDED) else None
    return tasks


def cfg_hash(readings, topup, open_trades, mode) -> str:
    return sha_obj({"version": VERSION, "readings": list(readings.items()), "topup": topup,
                    "open_trades": open_trades, "mode": mode, "code": code_sha(),
                    "pool": json.loads((OUTF / "manifest_pool.json").read_text())["windows"],
                    "s_topup": S_TOPUP, "boot": [BOOT_MC_B, BOOT_MC_SEED]})


def run_meta(args, cores, extra=None) -> dict:
    m = OrderedDict(version=VERSION, stage=args.cmd, started=D.now_iso(), cores=cores,
                    workers=args.workers, omp_num_threads=os.environ.get("OMP_NUM_THREADS"),
                    mkl_num_threads=os.environ.get("MKL_NUM_THREADS"),
                    affinity=sorted(os.sched_getaffinity(0)), load_avg_start=D.loadavg(),
                    code=code_sha(), packs={st: D.sha256_file(p) for st, p in PACKS.items()},
                    stage2_census=json.loads((D.OUT / "census_meta.json").read_text())["outputs"])
    if extra:
        m.update(extra)
    return m


def write_outputs(results, out_dir, mode):
    """The assembled JSONL outputs of a run (design Section 10)."""
    ensure_dir(out_dir)
    fut, anc, pri, ot, fi = [], [], [], [], []
    for iid in sorted(results):
        res = results[iid]
        fut += res["futures"]
        for a in res["anchors"]:
            anc.append(dict(a, iid=iid))
        for p in res["prices"]:
            (fi if p["reading"] == "FI" else pri).append(dict(p, iid=iid))
        ot += res["open_trades"]
    D.write_jsonl(out_dir / "futures_{}.jsonl".format(mode), fut)
    D.write_jsonl(out_dir / "anchors_{}.jsonl".format(mode), anc)
    D.write_jsonl(out_dir / "prices_{}.jsonl".format(mode), pri)
    D.write_jsonl(out_dir / "fullinfo_{}.jsonl".format(mode), fi)
    if ot:
        D.write_jsonl(out_dir / "open_trades.jsonl", ot)
    return {p.name: D.sha256_file(p) for p in sorted(out_dir.glob("*_{}.jsonl".format(mode)))}


def mc_measure(results, units_forecast, S) -> dict:
    """Median Monte Carlo SE per design and reading over the forecast units (S futures)."""
    per = defaultdict(lambda: defaultdict(list))
    for res in results.values():
        for p in res["prices"]:
            if p["reading"] in ("F1", "F2") and p["s"] < S:
                per[(p["reading"], p["uid"])]["_"].append(p["prices"])
    out = OrderedDict()
    for rd in ("F2", "F1"):
        for g in DESIGNS:
            se, bse = [], []
            for (r_, uid), d in per.items():
                if r_ != rd:
                    continue
                ag = aggregate([x[g] for x in d["_"]], SETTINGS[g])
                if ag["mc_se"] is not None:
                    se.append(ag["mc_se"])
                    bse.append(ag.get("boot_se", 0.0))
            out["{}|{}".format(rd, g)] = {"n": len(se), "median_mc_se": D.median(se),
                                          "median_boot_se": D.median(bse),
                                          "p90_mc_se": D.pctl(se, 90), "max_mc_se": max(se) if se else None}
    return out


def cmd_smoke(args) -> int:
    cores = D.parse_cores(args.cores)
    D.pin_cores(cores)
    D.cap_threads(1)
    foreign = check_cores(cores)
    t0 = time.time()
    check = D.Checker()
    inp = load_forecast_inputs(check)
    if check.failures:
        check.fatal(OUTF / "smoke_assertions.json", {"stage": "inputs"})
    # one instance per stratum: the one with the fewest priced items among those with >= 5
    cnt = Counter(r["instance_id"] for r in inp["items"]
                  if r["set"] == "published" and r["issuable"] and r["dt_stage_cert"] == "qual")
    pick = []
    for st in D.STRATA:
        c = sorted((n, iid) for iid, n in cnt.items() if iid.startswith(st) and n >= 5)
        pick.append(c[0][1])
    if args.instances:
        pick = args.instances.split(",")
    S = args.S
    readings = readings_for(S, "direct")
    tasks = prepare(direct_units(inp, check, set(pick)), inp, readings, True, True)
    cfg = cfg_hash(readings, True, True, "direct")
    meta = run_meta(args, cores, {"instances": pick, "S": S, "foreign_at_start": foreign})
    r1 = run_parts(tasks, OUTF / "smoke" / "pass1", cores, args.workers, cfg, "smoke pass 1")
    r2 = run_parts(tasks, OUTF / "smoke" / "pass2", cores, args.workers, cfg + "-pass2",
                   "smoke pass 2")
    for iid in pick:
        bad = af4_compare(r1[iid], r2[iid])
        check.true("AF4", "two runs of {} are byte-identical".format(iid), not bad, bad)
    krows = k_rows(inp["items"])
    k_info = assert_k_direct(check, r1, inp["items"], krows)
    summ = assert_runs(check, r1, smoke=True)
    mc = mc_measure(r1, None, S)
    worst = max((mc["{}|G-CERT-M".format(rd)]["median_mc_se"] or 0.0) for rd in ("F2", "F1"))
    S_dec = S_TOPUP if worst > MC_SE_GATE else S_MAIN
    wall = {iid: r1[iid]["wall_s"] for iid in pick}
    n_fc = {t["iid"]: sum(1 for u in t["units"] if u["forecast"]) for t in tasks}
    decision = OrderedDict(S=S_dec, measured_at_S=S, gate=MC_SE_GATE,
                           certm_median_mc_se={rd: mc["{}|G-CERT-M".format(rd)]["median_mc_se"]
                                               for rd in ("F2", "F1")},
                           rule="S = 50 for F1 and F2 if the median MC standard error of "
                                "G-CERT-M over the smoke items exceeds 0.01 at S = 20",
                           mc=mc, instances=pick, wall_s=wall, forecast_units=n_fc,
                           af3={"{}|{}".format(*k): {kk: vv for kk, vv in v.items()}
                                for k, v in summ["af3"].items()},
                           stage_diff=dict(summ["stage_diff"]), topup=dict(summ["topup"]),
                           rule_touched=k_info["rule_touched"], af1_rows=summ["af1_rows"])
    D.write_json(OUTF / "smoke_decision.json", decision)
    write_outputs(r1, OUTF / "smoke", "smoke")
    meta.update(finished=D.now_iso(), wall_s=time.time() - t0, load_avg_end=D.loadavg())
    D.write_json(OUTF / "smoke_meta.json", meta)
    check.fatal(OUTF / "smoke_assertions.json", {"decision_S": S_dec, "finished": D.now_iso()})
    print(json.dumps({k: decision[k] for k in ("S", "certm_median_mc_se", "wall_s",
                                               "forecast_units", "stage_diff", "topup",
                                               "af1_rows")}, indent=1), flush=True)
    print("[n11f smoke] PASS: {} checks in {:.0f}s; S = {}".format(
        check.report()["n_checks"], time.time() - t0, S_dec), flush=True)
    return 0


def smoke_gate(check):
    rep = json.loads((OUTF / "smoke_assertions.json").read_text())
    check.true("AF9", "smoke step passed", rep.get("status") == "PASS", rep.get("status"))
    dec = json.loads((OUTF / "smoke_decision.json").read_text())
    return dec


def cmd_direct(args) -> int:
    cores = D.parse_cores(args.cores)
    D.pin_cores(cores)
    D.cap_threads(1)
    foreign = check_cores(cores)
    t0 = time.time()
    check = D.Checker()
    dec = smoke_gate(check)
    S = int(dec["S"])
    inp = load_forecast_inputs(check)
    if check.failures:
        check.fatal(OUTF / "direct_assertions.json", {"stage": "inputs"})
    readings = readings_for(S, "direct")
    inst = set(args.instances.split(",")) if args.instances else None
    tasks = prepare(direct_units(inp, check, inst), inp, readings, True, True)
    cfg = cfg_hash(readings, True, True, "direct")
    meta = run_meta(args, cores, {"S": S, "readings": list(readings.items()),
                                  "foreign_at_start": foreign})
    res = run_parts(tasks, OUTF / "parts" / "direct", cores, args.workers, cfg, "direct")
    krows = k_rows(inp["items"])
    k_info = assert_k_direct(check, res, inp["items"], krows)
    summ = assert_runs(check, res)
    # AF9: every priced item has every reading at its S
    for t in tasks:
        got = Counter((p["uid"], p["reading"]) for p in res[t["iid"]]["prices"])
        for u in t["units"]:
            if not u["forecast"]:
                continue
            for rd, S_r in readings.items():
                check.true("AF9", "{} has {} futures of {}".format(u["uid"], S_r, rd),
                           got[(u["uid"], rd)] >= S_r, got[(u["uid"], rd)])
    outs = write_outputs(res, OUTF, "direct")
    meta.update(finished=D.now_iso(), wall_s=time.time() - t0, load_avg_end=D.loadavg(),
                outputs=outs, instance_wall_s={k: v["wall_s"] for k, v in res.items()},
                stage_diff=dict(summ["stage_diff"]), topup=dict(summ["topup"]),
                rule_touched=k_info["rule_touched"], af1_rows=summ["af1_rows"],
                af3={"{}|{}".format(*k): v for k, v in summ["af3"].items()})
    D.write_json(OUTF / "run_meta_direct.json", meta)
    check.fatal(OUTF / "direct_assertions.json", {"finished": D.now_iso(), "outputs": outs})
    print("[n11f direct] PASS: {} checks in {:.0f}s".format(check.report()["n_checks"],
                                                            time.time() - t0), flush=True)
    return 0


def cmd_e2e(args) -> int:
    cores = D.parse_cores(args.cores)
    D.pin_cores(cores)
    D.cap_threads(1)
    foreign = check_cores(cores)
    t0 = time.time()
    check = D.Checker()
    dec = smoke_gate(check)
    S = int(dec["S"])
    inp = load_forecast_inputs(check)
    inst = set(args.instances.split(",")) if args.instances else None
    tasks, refs, keys = e2e_units(inp, check, inst)
    if check.failures:
        check.fatal(OUTF / "e2e_assertions.json", {"stage": "inputs"})
    readings = readings_for(S, "e2e")
    tasks = prepare(tasks, inp, readings, False, False)
    for t in tasks:
        t["memo"] = True
    cfg = cfg_hash(readings, False, False, "e2e")
    meta = run_meta(args, cores, {"S": S, "readings": list(readings.items()),
                                  "foreign_at_start": foreign,
                                  "units": sum(len(t["units"]) for t in tasks)})
    part = OUTF / "parts" / ("e2e_smoke" if inst else "e2e")
    res = run_parts(tasks, part, cores, args.workers, cfg, "e2e")
    info = assert_k_e2e(check, res, refs)
    summ = assert_runs(check, res)
    for t in tasks:
        got = Counter((p["uid"], p["reading"]) for p in res[t["iid"]]["prices"])
        for u in t["units"]:
            for rd, S_r in readings.items():
                check.true("AF9", "{} has {} futures of {}".format(u["uid"], S_r, rd),
                           got[(u["uid"], rd)] >= S_r, got[(u["uid"], rd)])
    out_dir = ensure_dir(OUTF / "e2e_smoke") if inst else OUTF
    outs = write_outputs(res, out_dir, "e2e")
    D.write_json(out_dir / "e2e_keys.json", {"keys": keys, "n_units": meta["units"]})
    meta.update(finished=D.now_iso(), wall_s=time.time() - t0, load_avg_end=D.loadavg(),
                outputs=outs, compared=info, instance_wall_s={k: v["wall_s"] for k, v in res.items()},
                stage_diff=dict(summ["stage_diff"]), af1_rows=summ["af1_rows"],
                af3={"{}|{}".format(*k): v for k, v in summ["af3"].items()})
    D.write_json(out_dir / "run_meta_e2e.json", meta)
    check.fatal(out_dir / "e2e_assertions.json", {"finished": D.now_iso(), "outputs": outs})
    print("[n11f e2e] PASS: {} checks in {:.0f}s; {} units".format(
        check.report()["n_checks"], time.time() - t0, meta["units"]), flush=True)
    return 0


# --------------------------------------------------------------------------- #
# Analyse: aggregation per item and reading                                     #
# --------------------------------------------------------------------------- #
READ_TOKEN = OrderedDict([("K", "Known"), ("F2", "SiteRate"), ("F1", "LoadKnown"),
                          ("F3-", "LoadHalf"), ("F3+", "LoadOneHalf"), ("FI", "FullWindow"),
                          ("P0", "Published")])
READ_NAME = OrderedDict([("K", "known orders only"), ("F2", "load estimated from arrivals so far"),
                         ("F1", "load known"), ("F3-", "load halved"), ("F3+", "load raised by half"),
                         ("FI", "all orders of the window"),
                         ("P0", "published, full board at t = 0")])
GTOK = dict(D.GATE_TOKEN, **{"G-CERT|D-REL2": "UnionCert", "G-CERT-M|D-REL2": "Union"})
DTOK = {0.05: "DeltaFive", 0.10: "DeltaTen", 0.20: "DeltaTwenty"}
STOK = OrderedDict([("all", "All")] + list(D.STRATUM_TOKEN.items()))
DELTAS = (0.05, 0.10, 0.20)
TRUTHS = OrderedDict([("orig", "realised marginal cost, original fields (primary)"),
                      ("real", "realised marginal cost, adjusted fields (Stage 1 panel)"),
                      ("origabs", "realised absolute cost, original fields")])
TRUTH_TOK = {"orig": "", "real": "AdjFields", "origabs": "OrigAbs"}
SUMMARY_MARK3 = "\n## Stage 3: the forecast reading (known board plus sampled later arrivals)\n"


def load_prices(path) -> dict:
    """(uid, reading) -> list of (s, record) in future order."""
    out = defaultdict(list)
    for r in D.read_jsonl(path):
        out[(r["uid"], r["reading"])].append((r["s"], r))
    for k in out:
        out[k].sort(key=lambda x: x[0])
    return out


def agg_unit(recs, s_max=None) -> dict:
    """Aggregated prices of one unit under one reading (all futures, or the first s_max)."""
    use = [r for s, r in recs if s_max is None or s < s_max]
    out = OrderedDict(n_futures=len(use),
                      n_priced=sum(1 for r in use if r["p"]["stage_cert"] == "qual"))
    for g in DESIGNS + ("D-ABS-orig",):
        ag = aggregate([r["prices"][g] for r in use], SETTINGS.get(g))
        out[g] = ag
    lbs = [r["p"]["lb"] for r in use if r["p"]["lb"] is not None]
    out["floor_share"] = (sum(1 for x in lbs if x < D.FLOOR_BH) / len(lbs)) if lbs else None
    out["lb_median"] = D.median(lbs)
    return out


def reading_prices(rows, prices, fullinfo, readings) -> dict:
    """reading -> item_id -> {p_<gate>, undecided set, aggregates}."""
    out = OrderedDict()
    for rd in readings:
        cur = {}
        for r in rows:
            iid = r["item_id"]
            rec = {"stopped": False, "undecided": set(), "agg": None}
            if rd == "K":
                for g in DESIGNS:
                    rec["p_" + g] = r["p_" + g]
                rec["p_D-ABS-orig"] = (None if r["obj_orig"] is None or r["an_obj_orig"] is None
                                       else round(r["obj_orig"] - r["an_obj_orig"], D.ROUND_BH))
            elif rd == "P0":
                stop = r["om_term_cert"] in D.STOP_TERMS and r["om_stage_cert"] != "qual"
                rec["stopped"] = stop
                for g in DESIGNS:
                    rec["p_" + g] = r.get("om_p_" + g)
                rec["p_D-ABS-orig"] = (None if r.get("om_obj_orig") is None else
                                       round(r["om_obj_orig"] - r["anchor_pub"], D.ROUND_BH))
            else:
                src = fullinfo if rd == "FI" else prices
                recs = src.get((iid, rd), [])
                if rd in ("F3-", "F3+"):
                    recs = [x for x in recs if x[0] < S_F3]
                ag = agg_unit(recs)
                rec["agg"] = ag
                for g in DESIGNS + ("D-ABS-orig",):
                    rec["p_" + g] = ag[g]["median"]
                    if rd in ("F1", "F2") and g in SETTINGS and ag[g]["undecided"]:
                        rec["undecided"].add(g)
                rec["p80"] = {g: ag[g]["p80"] for g in DESIGNS}
                rec["mean"] = {g: ag[g]["mean"] for g in DESIGNS}
            cur[iid] = rec
        out[rd] = cur
    return out


def refers_rec(rec, gate, agg="median") -> bool:
    if rec["stopped"]:
        return True
    if gate in UNIONS:
        a, b = gate.split("|")
        return refers_rec(rec, a, agg) or refers_rec(rec, b, agg)
    if agg == "median":
        p = rec.get("p_" + gate)
    else:
        p = (rec.get(agg) or {}).get(gate)
        if p is None:
            p = rec.get("p_" + gate)
    return p is not None and p > SETTINGS[gate]


def undecided_rec(rec, gate) -> bool:
    if gate in UNIONS:
        return any(g in rec["undecided"] for g in gate.split("|"))
    return gate in rec["undecided"]


def truth_of(r, truth):
    if truth == "orig":
        return (r["orig_m_lo"], r["orig_m_hi"]) if r.get("orig_covered_m") else None
    if truth == "origabs":
        return (r["orig_g_lo"], r["orig_g_hi"]) if r.get("orig_covered") else None
    return (r["real_m_lo"], r["real_m_hi"]) if r.get("real_covered_m") else None


def costly_of(r, truth, delta):
    t = truth_of(r, truth)
    if t is None:
        return None
    if t[0] > delta:
        return 1
    if t[1] <= delta:
        return 0
    return None


def attach_orig_truth(rows, full_br, anchors):
    for r in rows:
        a = anchors[(r["instance_id"], r["frozen_seed_key"])]
        base = full_br.get((r["instance_id"], D.BASE_FP))
        r["orig_obj"] = r["rw_obj_orig"]
        if r["rw_obj_orig"] is None or base is None:
            r["orig_covered"] = r["orig_covered_m"] = False
            continue
        D.attach_truth(r, base, base, float(a["wwt_original_bh"]), prefix="orig_")


def consequence(rows, rp, boot, groups=("all", "stratum", "class", "split2"), with_ci=True,
                aggs=("median",)) -> list:
    """Miss and false-referral counts per reading, gate, truth, delta and group."""
    out = []

    def gkeys(r):
        k = [("all", "all")]
        if "stratum" in groups:
            k.append(("stratum", r["stratum"]))
        if "class" in groups:
            k.append(("class", r["primary_class"]))
        if "split2" in groups:
            k.append(("split2", "field" if r["split"] == "field_changing" else "seq"))
        return k

    gates = DESIGNS + UNIONS
    for truth in TRUTHS:
        for delta in DELTAS:
            st = {r["item_id"]: costly_of(r, truth, delta) for r in rows}
            for rd, cur in rp.items():
                for agg in aggs:
                    if agg != "median" and rd not in ("F1", "F2", "F3-", "F3+"):
                        continue
                    for g in gates:
                        bins = defaultdict(lambda: {"costly": [], "cheap": [], "miss": [],
                                                    "fr": [], "und": 0})
                        for r in rows:
                            s_ = st[r["item_id"]]
                            if s_ is None:
                                continue
                            rec = cur[r["item_id"]]
                            und = agg == "median" and undecided_rec(rec, g)
                            ref = refers_rec(rec, g, agg)
                            for k in gkeys(r):
                                b = bins[k]
                                if und:
                                    b["und"] += 1
                                    continue
                                if s_ == 1:
                                    b["costly"].append(r)
                                    b["miss"].append(not ref)
                                else:
                                    b["cheap"].append(r)
                                    b["fr"].append(ref)
                        for (gk, gv), b in sorted(bins.items(), key=lambda x: (x[0][0], str(x[0][1]))):
                            rec = OrderedDict(truth=truth, delta=delta, reading=rd, agg=agg,
                                              gate=g, group_kind=gk, group=gv,
                                              costly=len(b["costly"]), miss=sum(b["miss"]),
                                              cheap=len(b["cheap"]), fr=sum(b["fr"]),
                                              mc_undecided=b["und"])
                            rec["miss_share"] = rec["miss"] / rec["costly"] if rec["costly"] else None
                            rec["fr_share"] = rec["fr"] / rec["cheap"] if rec["cheap"] else None
                            lo = hi = flo = fhi = None
                            if with_ci and gk in ("all", "stratum") and agg == "median":
                                if b["costly"]:
                                    lo, hi = boot.ci(b["costly"], b["miss"])
                                if b["cheap"]:
                                    flo, fhi = boot.ci(b["cheap"], b["fr"])
                            rec.update(miss_lo=lo, miss_hi=hi, fr_lo=flo, fr_hi=fhi)
                            out.append(rec)
    return out


def crow(table, **kw):
    for r in table:
        if all((abs(r[k] - v) < 1e-12) if isinstance(v, float) else r[k] == v
               for k, v in kw.items()):
            return r
    return None


def damage_stats(rows, rp) -> list:
    """Predicted damage (aggregated D-ABS) against the realised damage, N8's statistics."""
    from scipy.stats import spearmanr

    out = []
    groups = OrderedDict([
        ("All", lambda r: True), ("VThree", lambda r: r["primary_class"] == "V3"),
        ("Benign", lambda r: r["primary_class"] == "benign"),
        ("Seq", lambda r: r["split"] == "sequencing_only"),
        ("Field", lambda r: r["split"] == "field_changing")])
    for st, tok in D.STRATUM_TOKEN.items():
        groups["VThree" + tok] = (lambda r, st=st: r["primary_class"] == "V3" and r["stratum"] == st)
        groups["DamagingSeq" + tok] = (lambda r, st=st: r["split"] == "sequencing_only"
                                       and r["stratum"] == st and r["damage_if_applied"] is not None
                                       and r["damage_if_applied"] > 2.0)
    groups["DamagingSeqAll"] = (lambda r: r["split"] == "sequencing_only" and
                                r["damage_if_applied"] is not None and r["damage_if_applied"] > 2.0)
    for truth, key, pkey in (("orig", "damage_if_applied", "p_D-ABS"),
                             ("adj", "damage_adj", "p_D-ABS"),
                             ("orig_pred_orig", "damage_if_applied", "p_D-ABS-orig")):
        for rd, cur in rp.items():
            for gname, fn in groups.items():
                pr = [(cur[r["item_id"]][pkey], r[key]) for r in rows if fn(r)
                      and r.get(key) is not None and cur[r["item_id"]].get(pkey) is not None]
                e = [p - q for p, q in pr]
                rho = None
                if len(pr) >= 3:
                    try:
                        rho = spearmanr([p for p, _ in pr], [q for _, q in pr]).statistic
                        rho = None if rho is None or math.isnan(rho) else float(rho)
                    except Exception:  # noqa: BLE001
                        rho = None
                out.append(OrderedDict(
                    truth=truth, reading=rd, group=gname, n=len(pr), spearman=rho,
                    under2=(sum(1 for v in e if v < -2.0) / len(e)) if e else None,
                    under10=(sum(1 for v in e if v < -10.0) / len(e)) if e else None,
                    n_under2=sum(1 for v in e if v < -2.0),
                    median_err=D.median(e), shortfall=sum(max(0.0, -v) for v in e),
                    pred_total=sum(p for p, _ in pr), real_total=sum(q for _, q in pr)))
    return out



def damage_per_instruction(iss, rp, boot, design="G-CERT-M") -> dict:
    """Mean realised damage per issuable instruction under ``design`` (a referral adds 0)."""
    import numpy as np
    import e1_delta_guard_replay as e1dg

    out = OrderedDict()
    for rd, cur in rp.items():
        for cls in ("all", "V3", "benign"):
            rs = [r for r in iss if cls == "all" or r["primary_class"] == cls]
            vals = []
            for r in rs:
                dmg = r["damage_if_applied"]
                if r["terminal_feas"] != "applied_uncertified" or dmg is None:
                    vals.append(0.0)
                    continue
                rec = cur.get(r["item_id"])
                if rec is None:                      # not priced on K: K's terminal stands
                    vals.append(dmg if r["terminal"] == "applied_with_certificate" else 0.0)
                    continue
                vals.append(0.0 if refers_rec(rec, design) else dmg)
            num = np.array(vals, dtype=float)
            idx = np.array([boot.index[r["instance_id"]] for r in rs], dtype=int)
            a, b = e1dg.cluster_sums(num, np.ones(len(rs)), idx, boot.k)
            lo, hi = e1dg.bootstrap_ci(a, b, boot.idx)
            out[(rd, cls)] = {"n": len(rs), "mean": float(num.mean()), "lo": lo, "hi": hi}
    return out


def table10(iss, rp) -> dict:
    """Stopped counts by class: K's terminal, the quality stage by the aggregated G-CERT."""
    out = OrderedDict()
    for rd, cur in rp.items():
        if rd == "P0":
            continue
        for cls in D.CLASSES:
            rs = [r for r in iss if r["primary_class"] == cls]
            stop = qual = 0
            for r in rs:
                rec = cur.get(r["item_id"])
                if rec is None:
                    if r["terminal"] in D.STOP_TERMS:
                        stop += 1
                    continue
                if refers_rec(rec, "G-CERT"):
                    stop += 1
                    qual += 1
            out[(rd, cls)] = {"n": len(rs), "stopped": stop, "qual": qual,
                              "share": stop / len(rs) if rs else None}
    return out


def referral_volume(rows, rp, delta=0.10) -> list:
    out = []
    base = rp["K"]
    for rd, cur in rp.items():
        for g in DESIGNS + UNIONS:
            for cls in ("all", "benign", "V3", "V4"):
                rs = [r for r in rows if cls == "all" or r["primary_class"] == cls]
                ref = [r for r in rs if refers_rec(cur[r["item_id"]], g)]
                ref_k = {r["item_id"] for r in rs if refers_rec(base[r["item_id"]], g)}
                ids = {r["item_id"] for r in ref}
                cheap = [r for r in rs if costly_of(r, "orig", delta) == 0]
                out.append(OrderedDict(reading=rd, gate=g, cls=cls, n=len(rs), referred=len(ref),
                                       added=len(ids - ref_k), removed=len(ref_k - ids),
                                       cheap=len(cheap),
                                       cheap_referred=sum(1 for r in cheap
                                                          if refers_rec(cur[r["item_id"]], g))))
    return out


def mc_section_rows(rows, prices) -> list:
    """Monte Carlo spread per design, reading and stratum; nested S = 10 against S = 20."""
    out = []
    for rd in ("F2", "F1", "F3-", "F3+"):
        S_r = S_MAIN if rd in ("F1", "F2") else S_F3
        for st in ("all",) + D.STRATA:
            rs = [r for r in rows if st == "all" or r["stratum"] == st]
            for g in DESIGNS:
                sd, iqr, se, und20, und_fin, agree, n_ag = [], [], [], 0, 0, 0, 0
                for r in rs:
                    recs = prices.get((r["item_id"], rd), [])
                    a20 = aggregate([x["prices"][g] for s_, x in recs if s_ < S_r], SETTINGS[g])
                    if a20["n"] == 0:
                        continue
                    sd.append(a20["sd"])
                    iqr.append(a20["iqr"])
                    se.append(a20["mc_se"])
                    und20 += int(a20["undecided"])
                    if rd in ("F1", "F2"):
                        af = aggregate([x["prices"][g] for s_, x in recs], SETTINGS[g])
                        und_fin += int(af["undecided"])
                        a10 = aggregate([x["prices"][g] for s_, x in recs if s_ < S_F3],
                                        SETTINGS[g])
                        if a10["median"] is not None and a20["median"] is not None:
                            n_ag += 1
                            agree += int((a10["median"] > SETTINGS[g]) ==
                                         (a20["median"] > SETTINGS[g]))
                out.append(OrderedDict(reading=rd, stratum=st, gate=g, n=len(sd),
                                       sd_median=D.median(sd), iqr_median=D.median(iqr),
                                       mc_se_median=D.median(se), mc_se_p90=D.pctl(se, 90),
                                       undecided_at_S=und20, undecided_final=und_fin,
                                       nested_agree=agree, nested_n=n_ag))
    return out


def diagnostics(rows, futures, items_by, inst_cache) -> dict:
    """Sampled against realised later corrective orders; m_hat / m_i; per stratum and reading."""
    import numpy as np

    per = defaultdict(list)
    for f in futures:
        per[(f["iid"], float(f["t_d"]), f["reading"])].append(f)
    boards = sorted({(r["instance_id"], float(r["t_d"])) for r in rows})
    out = OrderedDict()
    for (iid, t_d) in boards:
        inst = inst_cache(iid)
        H = float(inst["meta"]["window_bh"])
        real = len(corrective_tuples(inst, lo=t_d, hi=H))
        st = stratum_of(iid)
        for rd in READ_F:
            fs = per.get((iid, t_d, rd), [])
            if not fs:
                continue
            ns = np.array([f["n"] for f in fs], dtype=float)
            sd = float(ns.std(ddof=1)) if len(ns) > 1 else 0.0
            d = out.setdefault((st, rd), {"real": 0, "sampled_mean": 0.0, "z": [],
                                          "mhat_ratio": [], "mhat_ratio_pos": []})
            d["real"] += real
            d["sampled_mean"] += float(ns.mean())
            if sd > 0:
                d["z"].append((real - float(ns.mean())) / sd)
            if rd == "F2" and st in STORM:
                ld = fs[0]["load"]
                ratio = ld / MULTIPLIER[st]
                d["mhat_ratio"].append(ratio)
                if t_d > 0:
                    d["mhat_ratio_pos"].append(ratio)
    res = OrderedDict()
    for (st, rd), d in out.items():
        res["{}|{}".format(st, rd)] = OrderedDict(
            stratum=st, reading=rd, realised=d["real"], sampled_mean=d["sampled_mean"],
            ratio=d["sampled_mean"] / d["real"] if d["real"] else None,
            z_median=D.median(d["z"]), z_mean=(sum(d["z"]) / len(d["z"])) if d["z"] else None,
            mhat_ratio_median=D.median(d["mhat_ratio"]),
            mhat_ratio_p10=D.pctl(d["mhat_ratio"], 10), mhat_ratio_p90=D.pctl(d["mhat_ratio"], 90),
            mhat_ratio_pos_median=D.median(d["mhat_ratio_pos"]), boards=len(d["mhat_ratio"]))
    return res


class FMacros:
    """``\nElevenForecast...`` macros with the map; names checked by ``isalpha`` (AF10)."""

    def __init__(self, check):
        self.lines, self.map, self.names, self.check = [], [], set(), check

    def add(self, name, value, exhibit="", note=""):
        ok = name.isalpha()
        self.check.true("AF10", "macro name {} is alphabetic".format(name), ok)
        if not ok or name in self.names:
            self.check.true("AF10", "macro {} written once".format(name), name not in self.names)
            return
        self.names.add(name)
        self.lines.append("\\newcommand{\\" + name + "}{" + str(value) + "}")
        self.map.append(OrderedDict(macro=name, value=str(value), exhibit=exhibit, note=note))


def pct_tex(x, d=1):
    return "n/a" if x is None else "{:.{}f}\\%".format(100.0 * x, d)


def num_tex(x, d=2):
    return "n/a" if x is None else "{:.{}f}".format(x, d)



# --------------------------------------------------------------------------- #
# Analyse: end-to-end twins (Table 11 under a forecast, N3 under F2)            #
# --------------------------------------------------------------------------- #
def e1_forecast_rows(td_rows, keys, agg_of, reading):
    """Stage 2's decision-time E1 rows with the quality stage re-judged on the forecast."""
    kmap = {tuple(k[0]): k[1] for k in keys}
    out, n_changed, n_missing = [], 0, 0
    for r in td_rows:
        if r.get("model_refused") or r.get("stage_cert") != "qual":
            out.append(r)
            continue
        uid = kmap.get((r["src"], r["item_id"], r["mode"], r["thinking"], r["repeat"]))
        ag = agg_of.get((uid, reading))
        if ag is None or ag["G-CERT"]["median"] is None:
            n_missing += 1
            out.append(r)
            continue
        g = ag["G-CERT"]["median"]
        c = dict(r)
        codes = [x for x in (r["codes"] or []) if x != "gap_above_tau"]
        if g > D.TAU:
            codes = sorted(codes + ["gap_above_tau"])
        c.update(gap=g, codes=codes,
                 term_cert="blocked_qual" if g > D.TAU else "applied_with_certificate")
        n_changed += int(c["term_cert"] != r["term_cert"])
        out.append(c)
    return out, n_changed, n_missing


def table11_twin(root, logged, td_rows, issuable, prov, suite) -> dict:
    import n11_stage2 as S2

    S2.write_twin_root(root, logged, td_rows, issuable)
    tab = ensure_dir(root / "tables")
    S2.build_tables(root, tab, prov)
    d3r, _ = S2.d3_rows(suite, keep=issuable)
    S2.write_d3(tab / "D3_translation_equivalence.csv", d3r, "issuable items only")
    return S2.tab11_values(tab / "T3_guard_value_curve.csv", tab / "D3_translation_equivalence.csv")


def n3_forecast_rows(rows_n3, keys_n3, agg_of, reading):
    """N3 rows with m10/m11 re-priced on the forecast (gap; D-REL2 through rel_delta(p, 0))."""
    kmap = {tuple(k[0]): k[1] for k in keys_n3}
    out, n_sub = [], 0
    for r in rows_n3:
        if r.get("refusal"):
            out.append(r)
            continue
        c = dict(r)
        for mk in ("m10", "m11"):
            m = r[mk]
            uid = kmap.get((r["src"],) + tuple(r["disp_key"]) + (mk,))
            ag = agg_of.get((uid, reading)) if uid else None
            if m.get("stage_cert") != "qual" or ag is None or ag["G-CERT"]["median"] is None:
                continue
            mm = dict(m)
            g = ag["G-CERT"]["median"]
            mm["gap"] = g
            codes = [x for x in (m["codes"] or []) if x != "gap_above_tau"]
            if g > D.TAU:
                codes = sorted(codes + ["gap_above_tau"])
            mm["codes"] = codes
            mm["term_cert"] = "blocked_qual" if g > D.TAU else "applied_with_certificate"
            r2 = ag["D-REL2"]["median"]
            if m.get("ref2") is not None and r2 is not None:
                # rel_delta(obj, 0) = round(obj, 6): the forecast D-REL2 median enters N3's
                # disposition through the same function, rounded to 1e-6.
                mm["obj"], mm["ref2"] = r2, 0.0
            c[mk] = mm
            n_sub += 1
        if r["m10"] is r["m11"] or r.get("payload_is_v10"):
            c["m11"] = c["m10"] if r.get("payload_is_v10") else c["m11"]
        out.append(c)
    return out, n_sub


def gold_forecast(gold, keys_gold, agg_of, reading):
    kmap = dict((k[0], k[1]) for k in keys_gold)
    out = {}
    for iid_, g in gold.items():
        c = json.loads(json.dumps(g))
        uid = kmap.get(iid_)
        ag = agg_of.get((uid, reading)) if uid else None
        if ag is not None and c.get("td") and ag["G-CERT"]["median"] is not None:
            cert = ag["G-CERT"]["median"]
            rel2 = ag["D-REL2"]["median"] if c["td"].get("rel2") is not None else None
            c["td"]["cert"], c["td"]["rel2"] = cert, rel2
            c["td"]["union"] = max(x for x in (cert, rel2) if x is not None)
        out[iid_] = c
    return out


# --------------------------------------------------------------------------- #
# Analyse: the command                                                          #
# --------------------------------------------------------------------------- #
def cmd_analyse(args) -> int:
    import n2_pricing as n2

    cores = D.parse_cores(args.cores)
    D.pin_cores(cores)
    D.cap_threads(1)
    t0 = time.time()
    check = D.Checker()
    timing = OrderedDict()

    def lap(name, prev=[t0]):
        timing[name] = round(time.time() - prev[0], 1)
        prev[0] = time.time()
        print("[n11f analyse] {} ({:.0f}s)".format(name, timing[name]), flush=True)

    rep = json.loads((OUTF / "direct_assertions.json").read_text())
    if rep.get("status") != "PASS":
        raise SystemExit("REFUSING TO RUN: direct_assertions.json says {}".format(rep.get("status")))
    dec = json.loads((OUTF / "smoke_decision.json").read_text())
    S = int(dec["S"])
    items = D.read_jsonl(D.OUT / "items.jsonl")
    items_by = {r["item_id"]: r for r in items}
    krows_all = k_rows(items)
    pub_rows = [r for r in krows_all if r["set"] == "published"]
    iss = [r for r in pub_rows if r["issuable"]]
    priced = [r for r in iss if r["priced"]]
    anchors = D.load_anchor_records()
    full_br = D.full_brackets()
    for r in priced:
        it = items_by[r["item_id"]]
        r["frozen_seed_key"] = it["frozen_seed"]
        for k in ("om_term_cert", "om_stage_cert", "om_obj_orig", "an_obj_orig"):
            r[k] = it.get(k)
        for g in DESIGNS:
            r["om_p_" + g] = it.get("om_p_" + g)
        a = anchors[(r["instance_id"], it["frozen_seed"])]
        r["damage_adj"] = None if r["rw_obj"] is None else r["rw_obj"] - float(a["wwt_adjusted_bh"])
    attach_orig_truth(priced, full_br, anchors)
    prices = load_prices(OUTF / "prices_direct.jsonl")
    fullinfo = load_prices(OUTF / "fullinfo_direct.jsonl")
    futures = D.read_jsonl(OUTF / "futures_direct.jsonl")
    rp = reading_prices(priced, prices, fullinfo, READ_ALL)
    boot = n2.Boot({r["instance_id"] for r in pub_rows}, n2.SEED, n2.B_BOOT)
    # AF9: coverage of every priced item under every reading
    missing = [(r["item_id"], rd) for r in priced for rd in READ_F + ("FI",)
               if rp[rd][r["item_id"]]["agg"] is None or rp[rd][r["item_id"]]["agg"]["n_futures"] == 0]
    check.true("AF9", "every priced item has every reading", not missing, missing[:5])
    status = "COMPLETE" if not missing else "PARTIAL"
    lap("inputs and aggregation")

    cons = consequence(priced, rp, boot, aggs=("median", "p80", "mean"))
    lap("consequence tables")
    dmg = damage_stats(priced, rp)
    dpi = damage_per_instruction(iss, rp, boot)
    t10 = table10(iss, rp)
    refv = referral_volume(priced, rp)
    mcs = mc_section_rows(priced, prices)
    inst_cache_d = {}

    def inst_cache(iid):
        if iid not in inst_cache_d:
            inst_cache_d[iid] = D.load_instance(
                [x for x in (D.instance_path(it) for it in [D_item_of(iid)])][0])
        return inst_cache_d[iid]

    pub_suite = OrderedDict((r["item_id"], r) for r in D.load_published(check))
    first_item = {}
    for it in pub_suite.values():
        first_item.setdefault(it["instance"]["instance_id"], it)

    def D_item_of(iid):
        return first_item[iid]

    diag = diagnostics(priced, futures, items_by, inst_cache)
    addition_b_cache["rows"] = addition_b(priced, rp, prices, fullinfo)
    D.write_csv_rows(ANALYSIS / "N11F_addition_b.csv", addition_b_cache["rows"],
                     ["N11 Stage 3 ({}): addition B per reading and gate design".format(VERSION)],
                     list(addition_b_cache["rows"][0].keys()))
    lap("damage, referrals, MC, diagnostics")
    # Table 14 reduced: soundness on every sampled board and the open-trade census
    n_sound, n_bad = 0, 0
    for (uid, rd), recs in list(prices.items()) + list(fullinfo.items()):
        for s_, x in recs:
            p = x["p"]
            if p["lb"] is not None and p["obj"] is not None:
                n_sound += 1
                n_bad += int(p["lb"] > p["obj"] + TOL)
    check.true("AF6", "LB <= obj on every sampled proposal board ({} boards)".format(n_sound),
               n_bad == 0, n_bad)
    ot = D.read_jsonl(OUTF / "open_trades.jsonl")
    ot_open = [o for o in ot if o["open"]]
    ot_s = {"trades": len(ot), "open": len(ot_open),
            "open_orders_median": D.median([o["n_orders"] for o in ot_open]),
            "open_orders_max": max([o["n_orders"] for o in ot_open]) if ot_open else None,
            "boards": len({(o["iid"], o["t_d"], o["fk"], o["s"]) for o in ot}),
            "closed_share": (1 - len(ot_open) / len(ot)) if ot else None,
            "go": len(ot_open) <= 300}
    lap("Table 14 reduction")

    # ---- end-to-end twins
    e2e_md, e2e_vals = [], {}
    e2e_ok = (OUTF / "e2e_assertions.json").is_file() and json.loads(
        (OUTF / "e2e_assertions.json").read_text()).get("status") == "PASS"
    n3_vals = {}
    if e2e_ok:
        import n11_stage2 as S2
        import suite_gate as sg

        e_prices = load_prices(OUTF / "prices_e2e.jsonl")
        e_fi = load_prices(OUTF / "fullinfo_e2e.jsonl")
        keys = json.loads((OUTF / "e2e_keys.json").read_text())["keys"]
        agg_of = {}
        for k, recs in list(e_prices.items()) + list(e_fi.items()):
            agg_of[k] = agg_unit(recs)
        td_rows = D.read_jsonl(RESULTS / "n11_e2e" / "rows_e1_primary.jsonl")
        items_e2e = {r["item_id"]: r for r in D.read_jsonl(RESULTS / "n11_e2e" / "items.jsonl")}
        issuable = {k: bool(v["issuable"]) for k, v in items_e2e.items()}
        logged = S2.load_logged_e1()
        suite = {it["item_id"]: it for it in sg.load_suite()}
        prov = ["N11 Stage 3 forecast twin ({})".format(VERSION)]
        twin = ensure_dir(OUTF / "twin")
        e2e_vals["K"] = S2.tab11_values(RESULTS / "n11_e2e" / "twin" / "primary" / "tables" /
                                        "T3_guard_value_curve.csv",
                                        RESULTS / "n11_e2e" / "twin" / "primary" / "tables" /
                                        "D3_translation_equivalence.csv")
        for rd in ("F2", "F1", "FI"):
            rows_rd, n_ch, n_miss = e1_forecast_rows(td_rows, keys["e1"], agg_of, rd)
            check.true("AF9", "every priced E1 row has its {} price".format(rd), n_miss == 0, n_miss)
            e2e_vals[rd] = table11_twin(twin / ("e1_" + rd), logged, rows_rd, issuable,
                                        prov + ["reading " + rd], suite)
            e2e_md.append("- {}: {} priced E1 rows change terminal against K.".format(rd, n_ch))
            lap("Table 11 twin " + rd)
        # N3 under K (Stage 2's twin) and F2
        rows_n3 = D.read_jsonl(RESULTS / "n11_e2e" / "rows_n3.jsonl")
        gold = {g["item_id"]: g for g in D.read_jsonl(RESULTS / "n11_e2e" / "gold.jsonl")}
        rows_f2, n_sub = n3_forecast_rows(rows_n3, keys["n3"], agg_of, "F2")
        gold_f2 = gold_forecast(gold, keys["gold"], agg_of, "F2")
        dirs = S2.write_n3_twin(twin / "n3_F2", rows_f2, gold_f2, issuable, check)
        n3_vals["F2"] = S2.run_n3_analyze(dirs, twin / "n3_F2" / "analysis",
                                          twin / "n3_F2" / "n3_analyze.log")
        n3_vals["K"] = S2.lines_to_macros((RESULTS / "n11_e2e" / "twin" / "n3_primary" /
                                           "analysis" / "N3_macros.tex").read_text().splitlines())
        e2e_md.append("- N3: {} priced m10/m11 records re-priced under F2.".format(n_sub))
        lap("N3 twin F2")

    # ---- the late reading (addition A)
    late = late_reading(check)
    lap("late reading")

    # ---- macros, rows, figure data, summary
    M = FMacros(check)
    write_macros(M, S, dec, cons, dmg, dpi, t10, refv, mcs, diag, ot_s, e2e_vals, n3_vals, late,
                 status)
    rows_out = forecast_rows_out(priced, rp)
    D.write_csv_rows(ANALYSIS / "N11_rows_forecast.csv", rows_out,
                     ["N11 Stage 3 forecast rows, direct benchmark ({}); one row per (item, "
                      "reading); prices are the median over the sampled futures".format(VERSION),
                      "generated by code/scripts/n11_forecast.py analyse; status {}".format(status)],
                     list(rows_out[0].keys()))
    for name, table in (("N11F_consequence.csv", cons), ("N11F_damage.csv", dmg),
                        ("N11F_referrals.csv", refv), ("N11F_mc.csv", mcs)):
        D.write_csv_rows(ANALYSIS / name, table, ["N11 Stage 3 ({}), status {}".format(
            VERSION, status)], list(table[0].keys()))
    fig = figure_rows(cons, dmg)
    D.write_csv_rows(ANALYSIS / "N11F_fig_forecast.csv", fig,
                     ["Data of fig:forecast (N11 Stage 3, {}). Panel a: share of damaging "
                      "sequencing proposals (realised original-field damage > 2 bh) whose "
                      "predicted damage falls short by more than 2 bh, per reading and stratum. "
                      "Panel b: costly proposals at delta = 0.10 (realised marginal cost, "
                      "original fields) that G-CERT-M at tau = 0.20 does not refer, split into "
                      "field-changing and sequencing.".format(VERSION)], list(fig[0].keys()))
    hdr = "% N11 Stage 3 macros ({}), status {}; generated by code/scripts/n11_forecast.py " \
          "analyse".format(VERSION, status)
    lines = [hdr] + (["% PARTIAL: not every priced item has every reading; not for publication"]
                     if status != "COMPLETE" else []) + M.lines
    if late.get("macros_text"):
        lines += ["% ==== late reading (t_d' = t_start), Stage 3 addition A", late["macros_text"]]
    (ANALYSIS / "N11F_macros.tex").write_text("\n".join(lines) + "\n")
    D.write_csv_rows(ANALYSIS / "N11F_macro_map.csv", M.map + late.get("map", []),
                     ["N11 Stage 3 macro map ({})".format(VERSION)],
                     ["macro", "value", "exhibit", "note"])
    md = summary_part(S, dec, status, cons, dmg, dpi, t10, refv, mcs, diag, ot_s, e2e_vals,
                      e2e_md, n3_vals, late, check, timing, priced, rp)
    summ = (ANALYSIS / "N11_summary.md").read_text().split(SUMMARY_MARK3)[0].rstrip("\n")
    (ANALYSIS / "N11_summary.md").write_text(summ + "\n" + SUMMARY_MARK3 + md + "\n")
    lap("outputs")
    check.fatal(OUTF / "analyse_assertions.json", {"status_coverage": status, "timing": timing})
    print("[n11f analyse] {}: {} checks, {:.0f}s".format(status, check.report()["n_checks"],
                                                         time.time() - t0), flush=True)
    return 0



# --------------------------------------------------------------------------- #
# Analyse: addition B, the late reading, macros, rows, figure data, summary     #
# --------------------------------------------------------------------------- #
def addition_b(priced, rp, prices, fullinfo) -> list:
    """Per reading and design: under-pricing against the realised cost, the anchor gap on the
    priced board, and the referral share of benign items (project addition B)."""
    out = []
    an_gap = {}
    for r in priced:
        for rd in READ_ALL:
            if rd == "K":
                an_gap[(r["item_id"], rd)] = r["g_cert_anchor"]
            elif rd == "P0":
                an_gap[(r["item_id"], rd)] = r["anchor_gap_pub"]
            else:
                src = fullinfo if rd == "FI" else prices
                recs = [x for s_, x in src.get((r["item_id"], rd), [])
                        if rd not in F3_SCALE or s_ < S_F3]
                v = [x["prices"]["G-CERT"] - x["prices"]["G-CERT-M"] for x in recs
                     if x["prices"]["G-CERT"] is not None and x["prices"]["G-CERT-M"] is not None]
                an_gap[(r["item_id"], rd)] = D.median(v)
    tol = n2_tol()
    for rd, cur in rp.items():
        ag = [an_gap[(r["item_id"], rd)] for r in priced if an_gap.get((r["item_id"], rd)) is not None]
        for g in ("G-FEAS",) + DESIGNS + UNIONS:
            under = n_u = amb = 0
            for r in priced:
                rec = cur[r["item_id"]]
                if g in UNIONS:
                    break                # a union has no single price; its miss share is below
                p = 0.0 if g == "G-FEAS" else rec.get("p_" + g)
                if p is None:
                    continue
                if g == "D-ABS":
                    real = r["damage_if_applied"]
                    if real is None:
                        continue
                    n_u += 1
                    under += int(p < real - 2.0)
                    continue
                # N2's convention: under when price - truth_lo < -PRICE_TOL; ambiguous when only
                # the upper end of the truth bracket says so (left out of the denominator)
                t = truth_of(r, "origabs" if g == "G-CERT" else "orig")
                if t is None:
                    continue
                if p - t[0] < -tol:
                    under += 1
                    n_u += 1
                elif p - t[1] < -tol:
                    amb += 1
                else:
                    n_u += 1
            ben = [r for r in priced if r["primary_class"] == "benign"]
            refers = (lambda rec: rec["stopped"]) if g == "G-FEAS" else \
                (lambda rec, g=g: refers_rec(rec, g))
            ben_ref = sum(1 for r in ben if refers(cur[r["item_id"]]))
            costly = [r for r in priced if costly_of(r, "orig", 0.10) == 1]
            cheap = [r for r in priced if costly_of(r, "orig", 0.10) == 0]
            miss = sum(1 for r in costly if not refers(cur[r["item_id"]]))
            fr = sum(1 for r in cheap if refers(cur[r["item_id"]]))
            out.append(OrderedDict(
                reading=rd, gate=g, under=under if g not in UNIONS else None,
                under_n=n_u if g not in UNIONS else None, under_ambiguous=amb,
                under_share=(under / n_u) if n_u else None,
                under_rule=("price below realised damage by > 2 bh" if g == "D-ABS" else
                            "price - truth_lo < -{} ({} truth)".format(
                                tol, "absolute" if g == "G-CERT" else "marginal")
                            if g not in UNIONS else ""),
                anchor_gap_median=D.median(ag) if g != "G-FEAS" else None,
                anchor_gap_above_ten=((sum(1 for x in ag if x > 0.10) / len(ag)) if ag else None)
                if g != "G-FEAS" else None,
                benign=len(ben), benign_referred=ben_ref,
                benign_referred_share=(ben_ref / len(ben)) if ben else None,
                costly_ten=len(costly), missed_ten=miss,
                miss_share_ten=(miss / len(costly)) if costly else None,
                cheap_ten=len(cheap), false_ref_ten=fr,
                false_ref_share_ten=(fr / len(cheap)) if cheap else None))
    return out


def n2_tol():
    import n2_pricing as n2
    return n2.PRICE_TOL


def late_reading(check) -> dict:
    """Addition A: the late census under the running-work rule, its twins, Table 11 late."""
    out = {"md": [], "map": [], "macros_text": ""}
    cen = D.OUT / "late" / "census_assertions.json"
    ana = D.OUT / "late" / "analyse_assertions.json"
    if not cen.is_file() or json.loads(cen.read_text()).get("status") != "PASS":
        out["md"].append("The late census did not pass; no late twin is reported.")
        return out
    crep = json.loads(cen.read_text())
    late = D.read_jsonl(D.OUT / "late" / "items.jsonl")
    old = {r["item_id"]: r for r in D.read_jsonl(OUTF / "stage2_snapshot" / "late_census_failed" /
                                                  "items.jsonl")}
    iss = [r for r in late if r["set"] == "published" and r["issuable"]]
    touched = [r for r in iss if r.get("names_running_any")]
    flips = [r for r in iss if old.get(r["item_id"]) and
             old[r["item_id"]]["dt_term_cert"] != r["dt_term_cert"]]
    out["touched"] = len(touched)
    out["flips"] = [(r["item_id"], old[r["item_id"]]["dt_term_cert"], r["dt_term_cert"])
                    for r in flips]
    out["touched_by_terminal"] = Counter(r["dt_term_cert"] for r in touched)
    out["census_checks"] = crep["n_checks"]
    if not ana.is_file() or json.loads(ana.read_text()).get("status") != "PASS":
        out["md"].append("The late analyse step has not passed; the late twins are not reported.")
        return out
    arep = json.loads(ana.read_text())
    out["analyse"] = arep
    txt = (D.OUT / "late" / "N11_late_macros.tex").read_text()
    for name in re_names(txt):
        check.true("AF10", "late macro name {} is alphabetic".format(name), name.isalpha())
    out["late_summary"] = (D.OUT / "late" / "N11_late_summary.md").read_text()
    extra = []
    le = OUTF / "late_e2e"
    if (le / "e2e_assertions.json").is_file() and json.loads(
            (le / "e2e_assertions.json").read_text()).get("status") == "PASS":
        import n11_stage2 as S2
        import suite_gate as sg

        rows_late = D.read_jsonl(le / "rows_e1_late.jsonl")
        rows_prim = D.read_jsonl(le / "rows_e1_primary.jsonl")
        stage2 = D.read_jsonl(RESULTS / "n11_e2e" / "rows_e1_primary.jsonl")
        key = lambda r: (r["src"], r["item_id"], r["mode"], r["thinking"], r["repeat"])  # noqa
        s2 = {key(r): r for r in stage2}
        diff_term = sum(1 for r in rows_prim if s2[key(r)].get("term_cert") != r.get("term_cert"))
        diff_codes = sum(1 for r in rows_prim if s2[key(r)].get("codes") != r.get("codes"))
        check.true("AF0", "the rule leaves every primary E1 terminal unchanged", diff_term == 0,
                   diff_term)
        out["e2e_primary_codes_changed"] = diff_codes
        out["e2e_late_rows"] = len(rows_late)
        out["e2e_late_names_running"] = sum(1 for r in rows_late if r.get("names_running"))
        items_e2e = {r["item_id"]: r for r in D.read_jsonl(le / "items.jsonl")}
        issuable = {k: bool(v["issuable"]) for k, v in items_e2e.items()}
        logged = S2.load_logged_e1()
        suite = {it["item_id"]: it for it in sg.load_suite()}
        vals = table11_twin(ensure_dir(OUTF / "twin") / "e1_late", logged, rows_late, issuable,
                            ["N11 Stage 3, late reading t_d' = t_start"], suite)
        prim = S2.tab11_values(RESULTS / "n11_e2e" / "twin" / "primary" / "tables" /
                               "T3_guard_value_curve.csv",
                               RESULTS / "n11_e2e" / "twin" / "primary" / "tables" /
                               "D3_translation_equivalence.csv")
        out["tab11_late"], out["tab11_primary"] = vals, prim
        for tok, (disp, vs, _e) in vals.items():
            for j, col in enumerate(S2.TAB11_COLS):
                name = "nElevenLateTabEOne{}{}".format(tok, col)
                v = S2.pct_cell(vs[j], 1)
                check.true("AF10", "macro name {} is alphabetic".format(name), name.isalpha())
                extra.append("\\newcommand{\\" + name + "}{" + v + "}")
                out["map"].append(OrderedDict(macro=name, value=v, exhibit="Table 11 (late)",
                                              note="t_d = t_known: {}".format(
                                                  S2.pct_cell(prim[tok][1][j], 1))))
    else:
        out["md"].append("The late end-to-end replay has not passed; Table 11 late is not "
                         "reported.")
    out["macros_text"] = txt.rstrip("\n") + ("\n" + "\n".join(extra) if extra else "")
    for row in D.read_csv_comments(D.OUT / "late" / "N11_late_macro_map.csv"):
        out["map"].append(OrderedDict(macro=row["twin"], value=row["value"],
                                      exhibit=(row["exhibit"] or "") + " (late)",
                                      note=row.get("note", "")))
    return out


def re_names(txt):
    import re
    return re.findall(r"\\newcommand\{\\([^}]*)\}", txt)



DMG_GROUPS_MAC = ("All", "VThree", "Benign", "Seq", "Field", "DamagingSeqAll") + tuple(
    "DamagingSeq" + t for t in D.STRATUM_TOKEN.values()) + tuple(
    "VThree" + t for t in D.STRATUM_TOKEN.values())


def write_macros(M, S, dec, cons, dmg, dpi, t10, refv, mcs, diag, ot_s, e2e_vals, n3_vals, late,
                 status):
    M.add("nElevenForecastS", str(S), "method", "futures per item for F1 and F2")
    M.add("nElevenForecastSThree", str(S_F3), "method", "futures per item for F3")
    M.add("nElevenForecastSTopUp", str(S_TOPUP), "method", "top-up near a threshold")
    M.add("nElevenForecastHZero", num_tex(H0_BH, 0), "method", "prior exposure of F2 (bh)")
    M.add("nElevenForecastPoolWindows", str(len(POOL_IDS)), "method", "recorded F2 pool")
    M.add("nElevenForecastStatus", status.lower(), "coverage")
    for rd in ("F2", "F1"):
        v = dec["certm_median_mc_se"][rd]
        M.add("nElevenForecast{}SmokeMcSeCertM".format(READ_TOKEN[rd]), num_tex(v, 4),
              "smoke step", "median MC standard error of G-CERT-M at S = 20")
    # Macro scope (the CSVs carry every cell): the primary truth and the median at every delta,
    # pooled; strata and the field/sequencing split at delta 0.10 for G-CERT-M, D-REL2 and the
    # unions; the p80 and mean aggregators and the secondary truths pooled at delta 0.10.
    strat_gates = ("G-CERT-M", "D-REL2", "G-CERT|D-REL2", "G-CERT-M|D-REL2")
    for c in cons:
        if c["group_kind"] == "class":
            continue
        if c["agg"] != "median" or c["truth"] != "orig":
            if not (c["group_kind"] == "all" and c["delta"] == 0.10):
                continue
            if c["agg"] != "median" and c["truth"] != "orig":
                continue
        if c["group_kind"] in ("stratum", "split2") and (
                c["delta"] != 0.10 or c["gate"] not in strat_gates):
            continue
        rt, gt, dt = READ_TOKEN[c["reading"]], GTOK[c["gate"]], DTOK[c["delta"]]
        tt = TRUTH_TOK[c["truth"]]
        at = {"median": "", "p80": "PEighty", "mean": "Mean"}[c["agg"]]
        if c["group_kind"] == "split2":
            sp = "Field" if c["group"] == "field" else "Seq"
            M.add("nElevenForecast{}{}Miss{}{}{}All{}".format(rt, tt, gt, sp, dt, at),
                  str(c["miss"]), "tab:forecast", "costly {} ({})".format(c["costly"], c["group"]))
            continue
        stt = STOK[c["group"]] if c["group_kind"] == "stratum" else "All"
        stem = "nElevenForecast{}{}".format(rt, tt)
        tail = "{}{}{}{}".format(gt, dt, stt, at)
        M.add(stem + "Miss" + tail, str(c["miss"]), "tab:forecast")
        M.add(stem + "Costly" + tail, str(c["costly"]), "tab:forecast")
        M.add(stem + "MissShare" + tail, pct_tex(c["miss_share"]), "tab:forecast")
        M.add(stem + "FalseRef" + tail, str(c["fr"]), "tab:forecast")
        M.add(stem + "Cheap" + tail, str(c["cheap"]), "tab:forecast")
        M.add(stem + "FalseRefShare" + tail, pct_tex(c["fr_share"]), "tab:forecast")
        if c["mc_undecided"]:
            M.add(stem + "McUndecided" + tail, str(c["mc_undecided"]), "tab:forecast")
        if c["miss_lo"] is not None:
            M.add(stem + "MissShare" + tail + "Lo", pct_tex(c["miss_lo"]), "tab:forecast")
            M.add(stem + "MissShare" + tail + "Hi", pct_tex(c["miss_hi"]), "tab:forecast")
    for d in dmg:
        if d["group"] not in DMG_GROUPS_MAC:
            continue
        tt = {"orig": "", "adj": "AdjFields", "orig_pred_orig": "OrigPred"}[d["truth"]]
        stem = "nElevenForecast{}{}".format(READ_TOKEN[d["reading"]], tt)
        M.add(stem + "ErrBhUnderTwo" + d["group"], pct_tex(d["under2"]), "fig:forecast (a)",
              "n = {}".format(d["n"]))
        M.add(stem + "ErrBhUnderTen" + d["group"], pct_tex(d["under10"]), "predicted damage")
        M.add(stem + "Spearman" + d["group"], num_tex(d["spearman"], 2), "predicted damage")
        M.add(stem + "Shortfall" + d["group"], "{:,.0f}".format(d["shortfall"]).replace(",", "{,}"),
              "predicted damage", "total shortfall in bh")
        M.add(stem + "DamageN" + d["group"], str(d["n"]), "predicted damage")
    for (rd, cls), v in dpi.items():
        ct = "All" if cls == "all" else D.CLASS_TOKEN[cls]
        stem = "nElevenForecast{}DamageCertM{}".format(READ_TOKEN[rd], ct)
        M.add(stem, num_tex(v["mean"], 2), "tab:forecast", "bh per issuable instruction")
        M.add(stem + "Lo", num_tex(v["lo"], 2), "tab:forecast")
        M.add(stem + "Hi", num_tex(v["hi"], 2), "tab:forecast")
    for (rd, cls), v in t10.items():
        stem = "nElevenForecast{}Stopped{}".format(READ_TOKEN[rd], D.CLASS_TOKEN[cls])
        M.add(stem, str(v["stopped"]), "Table 10 (forecast)")
        M.add(stem + "Share", pct_tex(v["share"]), "Table 10 (forecast)")
    for r in refv:
        ct = "All" if r["cls"] == "all" else D.CLASS_TOKEN[r["cls"]]
        stem = "nElevenForecast{}".format(READ_TOKEN[r["reading"]])
        g = GTOK[r["gate"]]
        M.add(stem + "Referred" + g + ct, str(r["referred"]), "referral volume")
        if r["cls"] == "all":
            M.add(stem + "Added" + g, str(r["added"]), "referral volume")
            M.add(stem + "Removed" + g, str(r["removed"]), "referral volume")
            M.add(stem + "CheapReferred" + g, str(r["cheap_referred"]), "referral volume")
    for r in mcs:
        stem = "nElevenForecast{}".format(READ_TOKEN[r["reading"]])
        g = D.GATE_TOKEN[r["gate"]]
        st = STOK[r["stratum"]]
        M.add(stem + "McSe" + g + st, num_tex(r["mc_se_median"], 4), "Monte Carlo spread")
        if r["stratum"] == "all":
            M.add(stem + "McUndecided" + g + "All", str(r["undecided_at_S"]), "Monte Carlo spread")
            if r["reading"] in ("F1", "F2"):
                M.add(stem + "McUndecidedFinal" + g + "All", str(r["undecided_final"]),
                      "Monte Carlo spread")
                M.add(stem + "NestedAgree" + g + "All",
                      pct_tex(r["nested_agree"] / r["nested_n"] if r["nested_n"] else None),
                      "Monte Carlo spread", "S = 10 against S = 20 dispositions")
    for k, d in diag.items():
        stem = "nElevenForecast{}".format(READ_TOKEN[d["reading"]])
        st = D.STRATUM_TOKEN[d["stratum"]]
        M.add(stem + "CountRatio" + st, num_tex(d["ratio"], 3), "forecast diagnostics",
              "sampled mean count / realised count of later corrective orders")
        if d["reading"] == "F2" and d["mhat_ratio_median"] is not None:
            M.add(stem + "MhatRatioMedian" + st, num_tex(d["mhat_ratio_median"], 3),
                  "forecast diagnostics", "m_hat / m_i over the boards")
            if d["mhat_ratio_pos_median"] is not None:
                M.add(stem + "MhatRatioPosMedian" + st, num_tex(d["mhat_ratio_pos_median"], 3),
                      "forecast diagnostics", "boards with t_d > 0")
    gt_b = dict(GTOK, **{"G-FEAS": "Feas"})
    for x in addition_b_cache.get("rows") or []:
        stem = "nElevenForecast{}B{}".format(READ_TOKEN[x["reading"]], gt_b[x["gate"]])
        if x["under_share"] is not None:
            M.add(stem + "UnderShare", pct_tex(x["under_share"]), "addition B",
                  "{} of {}; {}".format(x["under"], x["under_n"], x["under_rule"]))
        if x["anchor_gap_median"] is not None and x["gate"] == "G-CERT-M":
            M.add("nElevenForecast{}AnchorGapMedian".format(READ_TOKEN[x["reading"]]),
                  num_tex(x["anchor_gap_median"], 4), "addition B", "anchor gap on the priced board")
            M.add("nElevenForecast{}AnchorGapAboveTenShare".format(READ_TOKEN[x["reading"]]),
                  pct_tex(x["anchor_gap_above_ten"]), "addition B", "share of items above 0.10")
        M.add(stem + "BenignReferredShare", pct_tex(x["benign_referred_share"]), "addition B",
              "{} of {} benign".format(x["benign_referred"], x["benign"]))
        M.add(stem + "MissShareDeltaTen", pct_tex(x["miss_share_ten"]), "addition B",
              "{} of {} costly".format(x["missed_ten"], x["costly_ten"]))
        M.add(stem + "FalseRefShareDeltaTen", pct_tex(x["false_ref_share_ten"]), "addition B",
              "{} of {} cheap".format(x["false_ref_ten"], x["cheap_ten"]))
    M.add("nElevenForecastOpenTrades", str(ot_s["open"]), "Table 14 (forecast)",
          "open trades on the F1 anchor boards of futures 0-2")
    M.add("nElevenForecastOpenTradesAll", str(ot_s["trades"]), "Table 14 (forecast)")
    M.add("nElevenForecastOpenTradesClosedShare", pct_tex(ot_s["closed_share"]),
          "Table 14 (forecast)")
    if e2e_vals:
        import n11_stage2 as S2

        for rd, vals in e2e_vals.items():
            if rd == "K":
                continue
            for tok, (disp, vs, _e) in vals.items():
                for j, col in enumerate(S2.TAB11_COLS):
                    M.add("nElevenForecast{}TabEOne{}{}".format(READ_TOKEN[rd], tok, col),
                          S2.pct_cell(vs[j], 1), "Table 11 (forecast)",
                          "K: {}".format(S2.pct_cell(e2e_vals["K"][tok][1][j], 1)))
    if n3_vals.get("F2"):
        import n11_stage2 as S2

        used = S2.manuscript_tokens()
        for n, v in n3_vals["F2"].items():
            if n in used:
                M.add("nElevenForecastSiteRate" + n[:1].upper() + n[1:], v, "Tables 18-19 (F2)",
                      "K: {}".format(n3_vals["K"].get(n)))


def forecast_rows_out(priced, rp) -> list:
    out = []
    for r in priced:
        for rd, cur in rp.items():
            rec = cur[r["item_id"]]
            row = OrderedDict(item_id=r["item_id"], primary_class=r["primary_class"],
                              subclass=r["subclass"], stratum=r["stratum"],
                              instance_id=r["instance_id"], split=r["split"], t_d=r["t_d"],
                              reading=rd, stopped=rec["stopped"])
            for g in DESIGNS + ("D-ABS-orig",):
                row["p_" + g] = rec.get("p_" + g)
            for g in DESIGNS:
                row["refers_" + g] = refers_rec(rec, g)
            row["refers_union"] = refers_rec(rec, "G-CERT-M|D-REL2")
            row["mc_undecided"] = "|".join(sorted(rec["undecided"]))
            ag = rec.get("agg")
            row["n_futures"] = None if ag is None else ag["n_futures"]
            row["certm_mc_se"] = None if ag is None else ag["G-CERT-M"]["mc_se"]
            row["certm_p80"] = None if ag is None else ag["G-CERT-M"]["p80"]
            row["certm_mean"] = None if ag is None else ag["G-CERT-M"]["mean"]
            row["floor_share"] = None if ag is None else ag["floor_share"]
            row.update(orig_m_lo=r.get("orig_m_lo"), orig_m_hi=r.get("orig_m_hi"),
                       real_m_lo=r.get("real_m_lo"), real_m_hi=r.get("real_m_hi"),
                       orig_g_lo=r.get("orig_g_lo"), orig_g_hi=r.get("orig_g_hi"),
                       damage_orig_bh=r["damage_if_applied"], damage_adj_bh=r.get("damage_adj"))
            out.append(row)
    return out


def figure_rows(cons, dmg) -> list:
    out = []
    for d in dmg:
        if d["truth"] == "orig" and d["group"].startswith("DamagingSeq"):
            st = d["group"][len("DamagingSeq"):]
            out.append(OrderedDict(panel="a", reading=d["reading"],
                                   reading_name=READ_NAME[d["reading"]], stratum=st,
                                   value=d["under2"], k=d["n_under2"], n=d["n"],
                                   part=""))
    for c in cons:
        if (c["truth"] == "orig" and c["agg"] == "median" and abs(c["delta"] - 0.10) < 1e-12
                and c["gate"] == "G-CERT-M" and c["group_kind"] == "split2"):
            out.append(OrderedDict(panel="b", reading=c["reading"],
                                   reading_name=READ_NAME[c["reading"]], stratum="All",
                                   value=c["miss"], k=c["miss"], n=c["costly"],
                                   part="field-changing" if c["group"] == "field" else "sequencing"))
    return out



def md(head, body) -> str:
    return D.md_table(head, body)


def kn(c, which="miss"):
    if c is None:
        return "n/a"
    if which == "miss":
        return "{}/{} ({})".format(c["miss"], c["costly"], D.pctf(c["miss_share"]))
    return "{}/{} ({})".format(c["fr"], c["cheap"], D.pctf(c["fr_share"]))


def summary_part(S, dec, status, cons, dmg, dpi, t10, refv, mcs, diag, ot_s, e2e_vals, e2e_md,
                 n3_vals, late, check, timing, priced, rp) -> str:
    L = []
    smoke = json.loads((OUTF / "smoke_assertions.json").read_text())
    direct = json.loads((OUTF / "direct_assertions.json").read_text())
    e2e_rep = json.loads((OUTF / "e2e_assertions.json").read_text()) \
        if (OUTF / "e2e_assertions.json").is_file() else {}
    L += ["Generated by `code/scripts/n11_forecast.py analyse` ({}). Coverage status: **{}**. "
          "Macros: `analysis/N11F_macros.tex` (map `analysis/N11F_macro_map.csv`); rows: "
          "`analysis/N11_rows_forecast.csv`; figure data: `analysis/N11F_fig_forecast.csv`."
          .format(VERSION, status), "",
          "### What was computed", "",
          "- Population: the {} issuable published items priced at the quality stage on K "
          "(Stage 2's primary census). Every other issuable item keeps K's terminal.".format(
              len(priced)),
          "- Readings: K (known orders only); F2, the primary forecast (storm strata: load "
          "estimated from the corrective arrivals observed in [0, t_d], shrunk to the campus's "
          "long-run level with {} bh of prior exposure; recorded stratum: the 76 other campus-10 "
          "training windows, resampled); F1, the load known (an upper reading: the pack at the "
          "instance's multiplier, or the window's own later orders resampled); F3, F1 with the "
          "load halved or raised by half; FI, all orders of the window (the bound); P0, the "
          "published full board at t = 0.".format(num_tex(H0_BH, 0)),
          "- Futures: S = {} for F1 and F2 (top-up to {} where the bootstrap interval of the "
          "median contains a frozen setting), S = {} for F3, one board for FI. Seeds are SHA-256 "
          "of (instance, t_d, reading, s), so a proposal and its anchor share every future."
          .format(S, S_TOPUP, S_F3),
          "- Price: the median over the futures (80th percentile and mean as sensitivities). "
          "Forecast prices are the median over {} sampled futures of the corrective arrivals. "
          "Each sampled price is certified on its own sampled board, and the median estimates "
          "the cost on the realised window without bounding it.".format(S),
          "- Truth (primary): the realised marginal cost on the original fields, damage / "
          "max(OPT_full,base, 1), with the realised damage in weighted business hours. The "
          "decision-time oracle prices the board without the later arrivals, so it cannot score "
          "a gate whose purpose is to price them; the realised full-window cost is the cost the "
          "site carries once they arrive.",
          "- The relative full-window cost overstates misses: the absolute reading labels a "
          "proposal costly whenever the site's own dispatcher sits more than delta above the "
          "omniscient full-window optimum, which is the dispatcher's own full-window gap and not "
          "the instruction's cost, so the absolute panel is reported as a secondary truth only.",
          "- The F1 reading uses the generating process; it is reported as the load known and "
          "never as what a site obtains. The claim sentence rests on F2.", ""]
    L += ["### Smoke step and the choice of S", "",
          "Smoke instances {} (one per stratum), every reading, run twice (AF4). Median Monte "
          "Carlo standard error of G-CERT-M at S = 20: F2 {}, F1 {} (gate {}). Decision: S = {}."
          .format(", ".join(dec["instances"]), num_tex(dec["certm_median_mc_se"]["F2"], 4),
                  num_tex(dec["certm_median_mc_se"]["F1"], 4), MC_SE_GATE, dec["S"]), "",
          md(["reading | design", "items", "median MC SE", "median bootstrap SE", "p90 MC SE",
              "max MC SE"],
             [[k, v["n"], num_tex(v["median_mc_se"], 4), num_tex(v["median_boot_se"], 4),
               num_tex(v["p90_mc_se"], 4), num_tex(v["max_mc_se"], 4)]
              for k, v in dec["mc"].items()]), ""]
    L += ["### Assertions", "",
          "- smoke: {} ({} checks; groups {}).".format(smoke["status"], smoke["n_checks"],
                                                       smoke["checks_by_group"]),
          "- direct: {} ({} checks; groups {}).".format(direct["status"], direct["n_checks"],
                                                        direct["checks_by_group"]),
          "- e2e: {} ({} checks).".format(e2e_rep.get("status", "not run"),
                                          e2e_rep.get("n_checks")),
          "- analyse: {} checks so far, failures {}.".format(check.report()["n_checks"],
                                                              check.report()["n_failures"]), ""]

    def c(rd, g, delta=0.10, gk="all", gv="all", truth="orig", agg="median"):
        return crow(cons, truth=truth, delta=delta, reading=rd, agg=agg, gate=g, group_kind=gk,
                    group=gv)

    def dg(rd, grp, truth="orig"):
        return next((d for d in dmg if d["truth"] == truth and d["reading"] == rd
                     and d["group"] == grp), None)

    body = []
    for rd in READ_ALL:
        cm, cr = c(rd, "G-CERT-M"), c(rd, "D-REL2")
        fm, fr_ = c(rd, "G-CERT-M", gk="split2", gv="field"), c(rd, "D-REL2", gk="split2",
                                                                gv="field")
        ben = next((x for x in refv if x["reading"] == rd and x["gate"] == "G-CERT-M"
                    and x["cls"] == "benign"), None)
        dd = dpi[(rd, "all")]
        d2 = dg(rd, "DamagingSeqAll")
        da = dg(rd, "All")
        body.append([READ_NAME[rd], kn(cm), fm["miss"] if fm else "n/a", kn(cr),
                     fr_["miss"] if fr_ else "n/a", kn(cm, "fr"), kn(cr, "fr"),
                     "{}/{}".format(ben["referred"], ben["n"]) if ben else "n/a",
                     "{} [{}, {}]".format(num_tex(dd["mean"]), num_tex(dd["lo"]), num_tex(dd["hi"])),
                     num_tex(da["spearman"], 2) if da else "n/a",
                     "{} ({}/{})".format(D.pctf(d2["under2"]), d2["n_under2"], d2["n"]) if d2 else "n/a"])
    L += ["### tab:forecast (pooled over strata, delta = 0.10, realised marginal cost on the "
          "original fields)", "",
          md(["reading", "G-CERT-M costly missed", "of which field-changing", "D-REL2 costly "
              "missed", "of which field-changing", "G-CERT-M cheap referred", "D-REL2 cheap "
              "referred", "benign referred (G-CERT-M)", "mean realised damage per instruction "
              "under G-CERT-M (bh, 95% CI)", "predicted-damage rank correlation", "damaging "
              "sequencing proposals under-predicted by > 2 bh"], body), ""]
    for delta in DELTAS:
        body = []
        for rd in READ_ALL:
            row = [READ_NAME[rd]]
            for g in DESIGNS + UNIONS:
                x = c(rd, g, delta)
                row.append("{} / {}".format(kn(x), kn(x, "fr")))
            body.append(row)
        L += ["### Every gate design at delta = {:.2f} (miss among costly / false referral among "
              "cheap; realised marginal cost, original fields)".format(delta), "",
              md(["reading"] + list(DESIGNS + UNIONS), body), ""]
    for truth in ("real", "origabs"):
        body = []
        for rd in READ_ALL:
            row = [READ_NAME[rd]]
            for g in DESIGNS + UNIONS:
                x = c(rd, g, 0.10, truth=truth)
                row.append("{} / {}".format(kn(x), kn(x, "fr")))
            body.append(row)
        L += ["### Secondary truth: {} (delta = 0.10)".format(TRUTHS[truth]), "",
              md(["reading"] + list(DESIGNS + UNIONS), body), ""]
    body = []
    for st in D.STRATA:
        for rd in READ_ALL:
            row = [D.STRATUM_NAME[st], READ_NAME[rd]]
            for g in ("G-CERT", "G-CERT-M", "D-REL2", "D-ABS"):
                x = c(rd, g, gk="stratum", gv=st)
                row.append(kn(x))
            body.append(row)
    L += ["### Misses by stratum (delta = 0.10, primary truth)", "",
          md(["stratum", "reading", "G-CERT", "G-CERT-M", "D-REL2", "D-ABS"], body), ""]
    body = []
    for rd in ("F2", "F1", "F3-", "F3+"):
        row = [READ_NAME[rd]]
        for agg in ("median", "p80", "mean"):
            x = c(rd, "G-CERT-M", agg=agg)
            row.append("{} / {}".format(kn(x), kn(x, "fr")))
        body.append(row)
    L += ["### Aggregation sensitivity, G-CERT-M at delta = 0.10", "",
          md(["reading", "median", "80th percentile", "mean"], body), ""]
    ab = addition_b_cache.get("rows") or []
    def frac(a, b, sh):
        return "" if a is None or b is None else "{}/{} ({})".format(a, b, D.pctf(sh))

    body = [[READ_NAME[x["reading"]], x["gate"],
             frac(x["under"], x["under_n"], x["under_share"]) or "(union: see miss)",
             num_tex(x["anchor_gap_median"], 4) if x["anchor_gap_median"] is not None else "",
             D.pctf(x["anchor_gap_above_ten"]) if x["anchor_gap_above_ten"] is not None else "",
             frac(x["missed_ten"], x["costly_ten"], x["miss_share_ten"]),
             frac(x["false_ref_ten"], x["cheap_ten"], x["false_ref_share_ten"]),
             frac(x["benign_referred"], x["benign"], x["benign_referred_share"])] for x in ab]
    L += ["### Addition B: per gate design, under-pricing against the realised cost, the anchor "
          "gap on the priced board, and benign referrals", "",
          "Under-pricing follows N2's convention: a relative design under-prices when its price "
          "lies more than 0.05 below the lower end of the realised marginal cost (G-CERT against "
          "the realised absolute cost); items whose truth bracket straddles that line are left "
          "out. D-ABS under-prices when its predicted damage lies more than 2 bh below the "
          "realised damage. G-FEAS prices nothing at the quality stage, so its price is 0. The "
          "anchor gap is the certified gap of the no-proposal dispatch on the priced board "
          "(median over futures per item, then median over items and the share above 0.10). "
          "Miss and false referral at delta = 0.10 use the realised marginal cost on the "
          "original fields.", "",
          md(["reading", "design", "under-priced", "anchor gap median", "anchor gap > 0.10",
              "costly missed (0.10)", "cheap referred (0.10)", "benign referred"], body), ""]
    body = []
    for grp in ("V3", "Seq", "Field", "Benign", "DamagingSeqAll") + tuple(
            "DamagingSeq" + t for t in D.STRATUM_TOKEN.values()) + tuple(
            "VThree" + t for t in D.STRATUM_TOKEN.values()):
        g2 = "VThree" if grp == "V3" else grp
        for rd in READ_ALL:
            d = dg(rd, g2)
            if d is None or not d["n"]:
                continue
            body.append([g2, READ_NAME[rd], d["n"], num_tex(d["spearman"], 2), D.pctf(d["under2"]),
                         D.pctf(d["under10"]), num_tex(d["median_err"], 2),
                         "{:,.0f}".format(d["shortfall"]), "{:,.0f}".format(d["real_total"])])
    L += ["### Predicted-damage accuracy (D-ABS, bh, against the realised original-field damage)",
          "", md(["group", "reading", "n", "rank correlation", "under > 2 bh", "under > 10 bh",
                  "median error", "total shortfall (bh)", "realised total (bh)"], body), "",
          "The adjusted-field version (N8's form) and the original-field predicted damage are "
          "in `analysis/N11F_damage.csv` (truth `adj` and `orig_pred_orig`).", ""]
    body = []
    for x in refv:
        if x["cls"] != "all" or x["gate"] not in ("G-CERT", "G-CERT-M", "D-REL2", "D-ABS",
                                                   "G-CERT-M|D-REL2"):
            continue
        b = next(y for y in refv if y["reading"] == x["reading"] and y["gate"] == x["gate"]
                 and y["cls"] == "benign")
        body.append([READ_NAME[x["reading"]], x["gate"], x["referred"], x["added"], x["removed"],
                     b["referred"], "{}/{}".format(x["cheap_referred"], x["cheap"])])
    L += ["### Referral volume (priced items; added and removed against K)", "",
          md(["reading", "design", "referred", "added", "removed", "benign referred",
              "cheap referred (delta 0.10)"], body), ""]
    body = [[READ_NAME[r["reading"]], D.STRATUM_NAME.get(r["stratum"], "Pooled"), r["gate"], r["n"],
             num_tex(r["sd_median"], 4), num_tex(r["iqr_median"], 4), num_tex(r["mc_se_median"], 4),
             num_tex(r["mc_se_p90"], 4), r["undecided_at_S"],
             r["undecided_final"] if r["reading"] in ("F1", "F2") else "",
             "{}/{}".format(r["nested_agree"], r["nested_n"]) if r["nested_n"] else ""]
            for r in mcs if r["gate"] in ("G-CERT", "G-CERT-M", "D-REL2", "D-ABS")]
    L += ["### Monte Carlo spread", "",
          md(["reading", "stratum", "design", "items", "median SD", "median IQR",
              "median MC SE", "p90 MC SE", "MC-undecided at S", "undecided after top-up",
              "S = 10 agrees with S = 20"], body), ""]
    body = [[D.STRATUM_NAME[d["stratum"]], READ_NAME[d["reading"]], d["realised"],
             "{:.0f}".format(d["sampled_mean"]), num_tex(d["ratio"], 3), num_tex(d["z_median"], 2),
             num_tex(d["mhat_ratio_median"], 3), num_tex(d["mhat_ratio_pos_median"], 3)]
            for d in diag.values()]
    L += ["### Forecast diagnostics (later corrective orders, summed over the priced boards)", "",
          md(["stratum", "reading", "realised", "sampled mean", "ratio", "median z of the "
              "realised count", "m_hat / m_i (all boards)", "m_hat / m_i (t_d > 0)"], body), ""]
    body = []
    for cls in D.CLASSES:
        row = [cls]
        for rd in ("K", "F2", "F1", "F3-", "F3+", "FI"):
            v = t10[(rd, cls)]
            row.append("{} ({})".format(v["stopped"], D.pctf(v["share"])))
        body.append(row)
    L += ["### Table 10 twin under the forecast (stopped issuable items; only the quality stage "
          "moves)", "", md(["class", "K", "F2", "F1", "F3-", "F3+", "FI"], body), ""]
    L += ["### Table 14 under the forecast (reduced)", "",
          "Soundness: LB <= obj on every sampled proposal and anchor board (AF6). Open trades on "
          "the F1 anchor boards of futures 0 to 2: {} of {} trades are open ({} closed by LB2), "
          "median size {} orders, largest {}. Go/no-go for CP-SAT (at most 300 open trades): "
          "{}. A full oracle on the sampled boards is not run; the pricing error on a sampled "
          "board is therefore not reported, and the predicted-damage exhibit carries the size "
          "argument in bh.".format(ot_s["open"], ot_s["trades"], D.pctf(ot_s["closed_share"]),
                                   ot_s["open_orders_median"], ot_s["open_orders_max"],
                                   "go" if ot_s["go"] else "no-go: not solved"), ""]
    if e2e_vals:
        import n11_stage2 as S2

        body = []
        for tok in e2e_vals["K"]:
            row = [e2e_vals["K"][tok][0]]
            for j, col in enumerate(S2.TAB11_COLS):
                if col not in ("VThreeReferred", "VFour", "VFive", "VSix", "BenignCert"):
                    continue
                row.append(" / ".join(S2.pct_cell(e2e_vals[rd][tok][1][j], 1)
                                      for rd in ("K", "F2", "F1", "FI")))
            body.append(row)
        L += ["### Table 11 under the forecast (end to end; cells K / F2 / F1 / FI)", "",
              md(["arm", "V3 referred", "V4 blocked", "V5 blocked", "V6 blocked",
                  "benign false block (G-CERT)"], body), ""] + e2e_md + [""]
        if n3_vals.get("F2"):
            used = S2.manuscript_tokens()
            diffs = [[n, n3_vals["K"].get(n), v] for n, v in n3_vals["F2"].items()
                     if n in used and n3_vals["K"].get(n) != v]
            L += ["### Tables 18 and 19 (N3) under F2", "",
                  "{} manuscript N3 macros twinned under F2; {} differ from K.".format(
                      sum(1 for n in n3_vals["F2"] if n in used), len(diffs)), "",
                  md(["macro", "K", "F2"], diffs[:60]) if diffs else "none", ""]
    L += ["### Late reading (t_d' = t_start) under the running-work rule (addition A)", ""]
    if late.get("touched") is not None:
        L += ["Rule: an operation that names an order already running at t_d is refused at the "
              "feasibility check (finding `names_running_work`), because the technician is on "
              "the job and the site cannot release or re-sequence it; the running constant then "
              "always enters the bound. Late census: PASS ({} checks). Issuable published items "
              "whose proposal names running work at t_start: {} (terminals {}). Terminal flips "
              "against the halted Stage 2 late census: {}.".format(
                  late["census_checks"], late["touched"], dict(late["touched_by_terminal"]),
                  late["flips"]), ""]
    if late.get("e2e_late_rows") is not None:
        L += ["Late end-to-end replay: {} E1 rows; rows naming running work: {}. Primary rows "
              "replayed under the rule: terminals unchanged against Stage 2 (asserted), codes "
              "changed on {} rows.".format(late["e2e_late_rows"], late["e2e_late_names_running"],
                                           late["e2e_primary_codes_changed"]), ""]
    if late.get("tab11_late"):
        import n11_stage2 as S2

        body = []
        for tok, (disp, vs, _e) in late["tab11_late"].items():
            pv = late["tab11_primary"][tok][1]
            body.append([disp] + ["{} / {}".format(S2.pct_cell(pv[j], 1), S2.pct_cell(vs[j], 1))
                                  for j in range(len(S2.TAB11_COLS))])
        L += ["Table 11 twin, late reading (cells t_d = t_known / t_d' = t_start):", "",
              md(["arm"] + list(S2.TAB11_COLS), body), ""]
    if late.get("late_summary"):
        L += ["The late twins of Tables 10, 14 and 16 (from `n11_decision_time.py analyse "
              "--reading late`; macros `\\nElevenLate...` appended to `analysis/N11F_macros.tex`):",
              "", late["late_summary"].replace("### ", "#### "), ""]
    L += late.get("md", [])
    L += ["### Wall times (analyse)", "", md(["step", "s"], [[k, v] for k, v in timing.items()]),
          ""]
    return "\n".join(L)


addition_b_cache: dict = {}


# --------------------------------------------------------------------------- #
# Entry point                                                                  #
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("smoke", "direct", "e2e", "analyse"):
        p = sub.add_parser(name)
        p.add_argument("--cores", default="8-11")
        p.add_argument("--workers", type=int, default=4 if name != "analyse" else 1)
        p.add_argument("--instances", default="")
        if name == "smoke":
            p.add_argument("--S", type=int, default=S_MAIN)
    args = ap.parse_args(argv)
    cores = D.parse_cores(args.cores)
    if (set(cores) & D.FORBIDDEN_CORES or set(cores) - set(CORES_OK)) and not os.environ.get("CERTIGATE_ANY_CORES"):
        raise SystemExit("REFUSING TO RUN: cores {} are not cores 8-11".format(cores))
    if args.workers > len(cores):
        raise SystemExit("REFUSING TO RUN: {} workers on {} cores".format(args.workers,
                                                                         len(cores)))
    fn = {"smoke": cmd_smoke, "direct": cmd_direct, "e2e": cmd_e2e,
          "analyse": globals().get("cmd_analyse")}[args.cmd]
    return fn(args)


if __name__ == "__main__":
    sys.exit(main())
