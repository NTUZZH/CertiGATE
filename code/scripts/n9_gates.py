#!/usr/bin/env python
"""N9 (D): the five quality gates on the held-out V3 draw, against c and g.

WHY THIS EXISTS
---------------
The published V3 class was admitted by the dispatcher's own degradation, the
statistic D-REL2 thresholds.  The held-out draw (code/suite/v0.3_heldout) uses
the same five families with no such screen, and its items are labelled by the
instruction cost under optimal execution c (code/scripts/n9_instruction_cost.py)
and by the oracle absolute cost g of the executed schedule.  This script prices
every held-out item and its benign twin with the five gates of the N2 analysis,
at their published operating points, and reports detection, false referral and
under-pricing against both labels.  On the published V3 items it reports how
close the certificate's marginal price m and D-REL2's statistic sit to c.

THE GATES (code/scripts/n2_pricing.py and delta_baselines.py, reused)
--------------------------------------------------------------------
G-CERT    g_cert = (obj - LB2) / max(LB2, 1), refers above tau = 0.20; computed
          here with l1guard.evaluate_proposal (config G_CERT), as the direct
          benchmark does.
G-CERT-M  m_cert = g_cert - g_cert_anchor, refers above tau = 0.20; the anchor is
          the no-op schedule's recorded certificate (analysis/ladder).
D-REL1    (obj - WT_ref1) / max(WT_ref1, 1), refers above theta = 0.02.
D-REL2    (obj - WT_ref2) / max(WT_ref2, 1), refers above theta = 0.02.
D-ABS     obj - WT_ref1 in business hours, refers above A = 0.8119.
The settings are read from analysis/DG14_delta_baselines.csv and asserted.  A
second reading puts every relative gate at threshold = delta.

THE LABELS
----------
c in [c_lo, c_hi] from results/n9_instruction_cost/brackets.jsonl.  At
materiality delta in {0.05, 0.10, 0.20} an item is label-costly when
c_lo > delta, label-cheap when c_hi <= delta, and undecided otherwise;
undecided items are counted and kept out of every rate.
g in [g_lo, g_hi] = (obj - OPT)/max(OPT, 1) over the relaxed bracket of the
item's fields (n2_pricing.attach_oracle, midpoint when width_rel < 1e-3).  A
reorder-only item has the baseline's fields, so its bracket is the baseline
bracket of results/oracle_v1; a window item's bracket is assembled from the
per-trade rows of results/oracle_v1 and results/n9_instruction_cost.

SIGNED ERROR.  e = price - truth; under-priced when the whole interval is below
-0.05, over-priced when it is above +0.05 (n2_pricing).  D-ABS is compared in
business hours and scaled by max(OPT, 1) as in n2_pricing.

|m - c|.  With c an interval, |m - c| lies in [dist(m, [c_lo, c_hi]),
max(|m - c_lo|, |m - c_hi|)]; a share "|m - c| <= x" counts items whose upper
end is <= x, and the items whose interval straddles x are reported as undecided.

INTERVALS.  95% instance-clustered percentile bootstrap (n2_pricing.Boot, the
same B and seed), over the 60 instances.

INPUT CHECKS.  The held-out file's digest equals its manifest; the published
suite's digest is pinned; every guard objective equals the recomputed executed
objective (1e-6 bh); every recomputed WT_ref2 equals the suite's stored
reference (1e-4 bh); on the published items every certified gap, D-REL2 price
and m_cert equals analysis/N2_rows_direct.csv (1e-6).

CPU ONLY, deterministic dispatch; workers pinned with ``--cores``.

OUTPUTS
-------
analysis/N9_heldout.csv         one row per held-out item and twin
analysis/N9_published_v3.csv    one row per published V3 item and twin
analysis/N9_summary.md          the headline numbers, with coverage
analysis/N9_macros.tex          macros \\nNine...
results/n9_instruction_cost/gate_inputs.jsonl   guard and reference cache

Run::

    taskset -c 16-19 python code/scripts/n9_gates.py --cores 16-19 --workers 4

Version: l1-n9-gates-1
"""

from __future__ import annotations

import os

SNAPSHOT_ROOT = ((os.environ.get("L1_Y1_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "PaperY-FMScheduling")) + "/data/processed/instances_v10")
_env = os.environ.get("L1_INSTANCE_ROOT")
if _env and os.path.realpath(_env) != os.path.realpath(SNAPSHOT_ROOT):
    raise SystemExit("REFUSING TO RUN: L1_INSTANCE_ROOT={} is not the snapshot".format(_env))
os.environ["L1_INSTANCE_ROOT"] = SNAPSHOT_ROOT

import argparse  # noqa: E402
import csv  # noqa: E402
import datetime as _dt  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import statistics  # noqa: E402
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

import n2_pricing as n2  # noqa: E402
import oracle_cost as oc  # noqa: E402
import suite_gate as sg  # noqa: E402

VERSION = "l1-n9-gates-1"
ANALYSIS = ROOT / "analysis"
N9_DIR = ROOT / "results" / "n9_instruction_cost"
ORACLE = ROOT / "results" / "oracle_v1"
HELDOUT_PATH = CODE / "suite" / "v0.3_heldout" / "suite_heldout.jsonl"
HELDOUT_MANIFEST = CODE / "suite" / "v0.3_heldout" / "manifest_heldout.json"
CACHE_PATH = N9_DIR / "gate_inputs.jsonl"

GATES = n2.GATES  # G-CERT, G-CERT-M, D-REL1, D-REL2, D-ABS
REL_GATES = (n2.CERT, n2.CERTM, "D-REL1", "D-REL2")
DELTAS = n2.DELTAS
TAU = n2.TAU_PUBLISHED
PRICE_TOL = n2.PRICE_TOL
CLOSE_X = (0.02, 0.05)
FLOOR_BH = 1.0


# --------------------------------------------------------------------------- #
# Guard and references, per item (worker side)                                 #
# --------------------------------------------------------------------------- #
_W = {}


def _init(cores):
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[var] = "1"
    if cores:
        os.sched_setaffinity(0, set(cores))
    from l1guard.replay import InstanceCache
    _W["cache"] = InstanceCache()


def _one(task):
    from l1adapter import apply as apply_mod, dispatch as dispatch_mod, evaluate
    from l1guard import evaluate_proposal
    from l1guard.config import preset

    cache = _W["cache"]
    path = task["path"]
    inst = cache.instance(path)
    base = cache.baseline(path, "atc", 0)
    ops = task["ops"]
    cfg = preset("G_CERT")
    v = evaluate_proposal(inst, json.dumps({"operations": ops}), cfg, baseline_schedule=None,
                          frozen_seed=())
    cert = v.certificate
    adj = apply_mod.apply_proposal(inst, {"operations": ops}, frozen_seed=[],
                                   baseline_schedule=base, strict_schema=True)
    sched = dispatch_mod.dispatch_adjusted(adj, "atc", 0)
    obj = evaluate.wwt(adj, sched)
    if any(o["op"] in n2.CONSTRAINING_OPS for o in ops):
        ref_adj = apply_mod.apply_operations(adj.instance, [], frozen_seed=[],
                                             baseline_schedule=base)
        ref2 = evaluate.wwt(ref_adj, dispatch_mod.dispatch_adjusted(ref_adj, "atc", 0))
        ref_from = "dispatched"
    else:
        ref2, ref_from = obj, "identical_by_construction"
    return {"key": task["key"], "item_id": task["item_id"], "terminal": v.terminal,
            "stage_reached": v.stage_reached,
            "gap_cert": None if cert is None else cert.gap,
            "obj_cert": None if cert is None else cert.obj_bh,
            "lb_cert": None if cert is None else cert.lb_bh,
            "obj": obj, "ref2": ref2, "reference_from": ref_from}


def _chunk(tasks):
    return [_one(t) for t in tasks]


def task_key(item, path_digest):
    blob = json.dumps([VERSION, item["item_id"], item["gold_ops"], path_digest],
                      sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def guard_inputs(items, digests, paths, workers, cores):
    """Guard verdicts and references, cached in gate_inputs.jsonl."""
    cache = {r["key"]: r for r in oc.read_jsonl(CACHE_PATH)}
    tasks = []
    for it in items:
        iid = it["instance"]["instance_id"]
        k = task_key(it, digests[iid])
        if k not in cache:
            tasks.append({"key": k, "item_id": it["item_id"], "path": paths[iid],
                          "ops": list(it["gold_ops"] or []), "iid": iid})
    if tasks:
        import multiprocessing as mp
        groups = defaultdict(list)
        for t in tasks:
            groups[t["iid"]].append(t)
        chunks = sorted(groups.values(), key=len, reverse=True)
        t0 = time.time()
        N9_DIR.mkdir(parents=True, exist_ok=True)
        if workers <= 1:
            _init(cores)
            results = [r for ch in chunks for r in _chunk(ch)]
        else:
            with mp.get_context("fork").Pool(workers, initializer=_init,
                                             initargs=(cores,)) as pool:
                results = [r for res in pool.imap_unordered(_chunk, chunks) for r in res]
        for r in results:
            oc.append_jsonl(CACHE_PATH, r)
            cache[r["key"]] = r
        print("[n9d] guard and references for {} items ({:.0f}s)".format(len(tasks),
                                                                        time.time() - t0))
    out = {}
    for it in items:
        iid = it["instance"]["instance_id"]
        out[it["item_id"]] = cache[task_key(it, digests[iid])]
    return out


# --------------------------------------------------------------------------- #
# Inputs                                                                       #
# --------------------------------------------------------------------------- #
def load_sets(check):
    pub = n2.load_suite(check)
    man = json.loads(HELDOUT_MANIFEST.read_text())
    want = man["artifacts"]["suite_heldout.jsonl"]["sha256"]
    got = n2.sha256_file(HELDOUT_PATH)
    if got != want:
        n2.refuse("held-out file digest {} != manifest {}".format(got, want))
    held = OrderedDict()
    for ln in open(HELDOUT_PATH, encoding="utf-8"):
        if ln.strip():
            r = json.loads(ln)
            held[r["item_id"]] = r
    check.eq("held-out records", 440, len(held))
    pub_v3 = [r for r in pub.values() if r["primary_class"] == "V3"]
    pub_items = pub_v3 + [pub[r["twin_id"]] for r in pub_v3]
    held_v3 = [r for r in held.values() if r["primary_class"] == "V3"]
    held_items = held_v3 + [held[r["twin_id"]] for r in held_v3]
    check.eq("published V3", 220, len(pub_v3))
    check.eq("held-out V3", 220, len(held_v3))
    return pub, held, pub_items, held_items, man


def instance_maps(items, check):
    manifest = sg.instance_manifest()["files"]
    paths, digests = {}, {}
    for it in items:
        iid = it["instance"]["instance_id"]
        if iid in paths:
            continue
        p = Path(sg.instance_path(it))
        rel = str(p.resolve().relative_to(Path(SNAPSHOT_ROOT).resolve()))
        if rel not in manifest:
            n2.refuse("{} not in the instance manifest".format(rel))
        d = n2.sha256_file(p)
        check.eq("instance digest " + iid, manifest[rel], d)
        paths[iid], digests[iid] = str(p), d
    check.true("instances within the 60-instance pool", 0 < len(paths) <= 60, str(len(paths)))
    return paths, digests


def relaxed_brackets(store_rows, need):
    """(iid, fp) -> bracket dict for field fingerprints not in brackets.jsonl."""
    out = {}
    for (iid, fp), info in need.items():
        lo = up = 0.0
        ok = True
        proved = True
        for tr, tfp in info["tfps"].items():
            r = store_rows.get((iid, tr, tfp))
            if r is None:
                ok = False
                break
            lo += float(r["lower"])
            up += float(r["upper"])
            proved = proved and (r["status"] in ("OPTIMAL", "CLOSED_BY_LB2")
                                 or float(r["upper"]) - float(r["lower"]) <= 1e-9)
        if ok:
            out[(iid, fp)] = {"lower": lo, "upper": up, "width_rel": (up - lo) / max(lo, FLOOR_BH),
                              "lb2_total": float("nan"), "proved_all": proved,
                              "assembled_from": "per-trade rows"}
    return out


def trade_rows():
    rows = {}
    for r in oc.read_jsonl(ORACLE / "trade_solves.jsonl"):
        k = (r["instance_id"], r["trade"], r["trade_fp"])
        if r.get("contended"):
            rows.pop(k, None)
            continue
        rows[k] = r
    for r in oc.read_jsonl(N9_DIR / "solves.jsonl"):
        if r.get("kind") != "relaxed":
            continue
        if r.get("invalid") and not r.get("invalid_persistent"):
            continue
        rows.setdefault((r["instance_id"], r["trade"], r["trade_fp"]), r)
    return rows


def c_brackets():
    out = {}
    for r in oc.read_jsonl(N9_DIR / "brackets.jsonl"):
        if r.get("complete"):
            out[r["item_id"]] = r
    return out


# --------------------------------------------------------------------------- #
# Rows                                                                         #
# --------------------------------------------------------------------------- #
def make_rows(items, gin, set_name, anchors, anchor_gaps, check):
    rows = []
    for it in items:
        g = gin[it["item_id"]]
        iid = it["instance"]["instance_id"]
        role = "V3" if it["primary_class"] == "V3" else "twin"
        check.true("{} reached the quality stage".format(it["item_id"]),
                   g["stage_reached"] == "qual", g["terminal"])
        if g["obj_cert"] is not None:
            check.true("guard objective equals the executed objective on " + it["item_id"],
                       abs(g["obj_cert"] - g["obj"]) <= n2.RECOMP_TOL_BH,
                       "{} vs {}".format(g["obj_cert"], g["obj"]))
        stored_ref = (it.get("metrics") or {}).get("wwt_adjusted_reference")
        if stored_ref is not None:
            check.true("WT_ref2 equals the suite's stored reference on " + it["item_id"],
                       abs(g["ref2"] - float(stored_ref)) <= n2.OBJ_TOL_BH,
                       "{} vs {}".format(g["ref2"], stored_ref))
        ops = list(it["gold_ops"] or [])
        fk = (iid, "")
        row = OrderedDict(
            set=set_name, role=role, item_id=it["item_id"], twin_id=it["twin_id"],
            primary_class=it["primary_class"], family_id=it["family_id"],
            subclass=it["subclass"], stratum=it["instance"]["stratum"], instance_id=iid,
            split=n2.op_split(ops), n_ops=len(ops), terminal=g["terminal"],
            stage_reached=g["stage_reached"], obj=g["obj"], lb_cert=g["lb_cert"],
            gap_cert=g["gap_cert"], g_cert_anchor=anchor_gaps[fk], ref1=anchors[fk],
            ref2=g["ref2"], reference_from=g["reference_from"], badness=it.get("badness"),
            badness_relative=(it.get("metrics") or {}).get("badness_relative"))
        row["quality_visible"] = False
        row["_ops"] = ops
        rows.append(row)
    return rows


def attach_fp(rows, store):
    """Field fingerprint and per-trade fingerprints of each row's adjusted fields."""
    from l1adapter import apply as apply_mod
    for r in rows:
        iid = r["instance_id"]
        inst = store[iid]
        adj = apply_mod.apply_proposal(inst, {"operations": r["_ops"]}, frozen_seed=[],
                                       baseline_schedule=None, strict_schema=True)
        base_f = {wo["id"]: tuple(wo[f] for f in oc.FIELDS) for wo in inst["work_orders"]}
        tuples = []
        for wo in adj.instance["work_orders"]:
            cur = tuple(wo[f] for f in oc.FIELDS)
            if cur != base_f[wo["id"]]:
                tuples.append((wo["id"],) + cur)
        tuples.sort(key=lambda t: t[0])
        r["fingerprint"] = oc.fp_of(tuples)
        trade_of = {wo["id"]: wo["trade"] for wo in inst["work_orders"]}
        by = defaultdict(list)
        for t in tuples:
            by[trade_of[t[0]]].append(t)
        trades = sorted({wo["trade"] for wo in inst["work_orders"]})
        r["_tfps"] = {tr: (oc.fp_of(by[tr]) if by.get(tr) else oc.BASE_FP) for tr in trades}


def attach_c(r, cb):
    b = cb.get(r["item_id"])
    r["c_covered"] = b is not None
    for k in ("c_lo", "c_hi", "c_mid", "n_lo", "n_hi", "c_opt_lower", "c_opt_upper"):
        r[k] = None
    if b is None:
        return
    r.update(c_lo=b["c_lo"], c_hi=b["c_hi"], c_mid=b["c_mid"], n_lo=b["n_lo"], n_hi=b["n_hi"],
             c_opt_lower=b["opt_lower"], c_opt_upper=b["opt_upper"])
    if abs(b["obj"] - r["obj"]) > n2.RECOMP_TOL_BH:
        raise SystemExit("c bracket objective differs on {}".format(r["item_id"]))


def c_state(r, delta):
    if not r["c_covered"]:
        return None
    if r["c_lo"] > delta:
        return 1
    if r["c_hi"] <= delta:
        return 0
    return None


def g_state(r, delta):
    if not r["covered"]:
        return None
    if r["g_lo"] > delta:
        return 1
    if r["g_hi"] <= delta:
        return 0
    return None


def err_vs_c(r, gate):
    """(lo, hi) of price - c, or None."""
    if not r["c_covered"]:
        return None
    if gate == "D-ABS":
        d = r["p_D-ABS"]
        lo_x, up_x = r["c_opt_lower"], r["c_opt_upper"]
        eb = (d - r["n_hi"], d - r["n_lo"])
        cands = [e / max(x, FLOOR_BH) for e in eb for x in n2._xs(lo_x, up_x)]
        return min(cands), max(cands)
    p = r["p_" + gate]
    return p - r["c_hi"], p - r["c_lo"]


def err_vs_g(r, gate):
    lo, hi = r.get("e_lo_" + gate), r.get("e_hi_" + gate)
    return None if lo is None else (lo, hi)


def under_over(rows, gate, fn):
    under = over = dec = 0
    for r in rows:
        e = fn(r, gate)
        if e is None:
            continue
        if e[1] < -PRICE_TOL:
            under += 1
        elif e[0] > PRICE_TOL:
            over += 1
        dec += 1
    return under, over, dec


def absdist(m, lo, hi):
    """Interval of |m - c| for c in [lo, hi]."""
    if lo <= m <= hi:
        near = 0.0
    else:
        near = min(abs(m - lo), abs(m - hi))
    return near, max(abs(m - lo), abs(m - hi))


# --------------------------------------------------------------------------- #
# Tables                                                                       #
# --------------------------------------------------------------------------- #
def rate(boot, rows, flags):
    n = len(rows)
    k = sum(1 for f in flags if f)
    lo, hi = boot.ci(rows, flags) if rows else (None, None)
    return {"n": n, "k": k, "rate": (k / n) if n else None, "lo": lo, "hi": hi}


def settings(dg14):
    s = {n2.CERT: TAU, n2.CERTM: TAU}
    s.update(dg14)
    return s


def disposition(rows, boot, dg14, label):
    """Detection on label-costly V3 items, false referral on twins and label-cheap items."""
    st = settings(dg14)
    out = []
    state = c_state if label == "c" else g_state
    v3 = [r for r in rows if r["role"] == "V3"]
    tw = [r for r in rows if r["role"] == "twin"]
    for delta in DELTAS:
        costly = [r for r in v3 if state(r, delta) == 1]
        cheap_v3 = [r for r in v3 if state(r, delta) == 0]
        cheap_tw = [r for r in tw if state(r, delta) == 0]
        undecided = [r for r in v3 if state(r, delta) is None]
        for op in ("published", "at_delta"):
            for gate in GATES:
                if op == "at_delta" and gate == "D-ABS":
                    continue
                thr = st[gate] if op == "published" else delta
                f = lambda r: n2.refers(r, gate, thr)  # noqa: E731
                out.append(OrderedDict(
                    label=label, delta=delta, operating_point=op, gate=gate, setting=thr,
                    v3_items=len(v3), v3_costly=len(costly), v3_cheap=len(cheap_v3),
                    v3_undecided=len(undecided),
                    detect=rate(boot, costly, [f(r) for r in costly]),
                    fr_cheap_v3=rate(boot, cheap_v3, [f(r) for r in cheap_v3]),
                    fr_twins=rate(boot, tw, [f(r) for r in tw]),
                    fr_cheap_twins=rate(boot, cheap_tw, [f(r) for r in cheap_tw])))
    return out


def share(boot, rows, pred):
    flags = [bool(pred(r)) for r in rows]
    return rate(boot, rows, flags)


def closeness(rows, price_key):
    """|price - c| summaries over rows with c."""
    rs = [r for r in rows if r["c_covered"] and r.get(price_key) is not None]
    if not rs:
        return None
    near, far = [], []
    for r in rs:
        a, b = absdist(r[price_key], r["c_lo"], r["c_hi"])
        near.append(a)
        far.append(b)
    out = {"n": len(rs), "median_lo": statistics.median(near), "median_hi": statistics.median(far)}
    for x in CLOSE_X:
        yes = sum(1 for b in far if b <= x)
        no = sum(1 for a in near if a > x)
        out["within_{}".format(x)] = {"yes": yes, "no": no, "undecided": len(rs) - yes - no,
                                      "share_lo": yes / len(rs), "share_hi": (len(rs) - no) / len(rs)}
    return out


# --------------------------------------------------------------------------- #
# Writers                                                                      #
# --------------------------------------------------------------------------- #
COLUMNS = ["set", "role", "item_id", "twin_id", "family_id", "stratum", "instance_id", "split",
           "terminal", "stage_reached", "obj", "lb_cert", "gap_cert", "g_cert_anchor", "ref1",
           "ref2", "reference_from", "badness", "badness_relative", "fingerprint",
           "covered", "opt_lower", "opt_upper", "width_rel", "point", "g_lo", "g_hi",
           "m_lo", "m_hi", "c_covered", "c_lo", "c_hi", "c_mid",
           "p_G-CERT", "p_G-CERT-M", "p_D-REL1", "p_D-REL2", "p_D-ABS",
           "refer_G-CERT", "refer_G-CERT-M", "refer_D-REL1", "refer_D-REL2", "refer_D-ABS"]


def write_rows(path, rows, header):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        for h in header:
            fh.write("# " + h + "\n")
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        for r in rows:
            w.writerow([n2._cell(r.get(c)) for c in COLUMNS])


def macro(name, value, lines):
    lines.append("\\newcommand{\\" + name + "}{" + value + "}")


def mname(*parts):
    words = {"0.05": "Five", "0.1": "Ten", "0.2": "Twenty", "0.02": "Two"}
    out = "nNine"
    for p in parts:
        p = words.get(str(p), str(p))
        p = "".join(ch for ch in p if ch.isalpha())
        out += p[:1].upper() + p[1:]
    return out


def pct_text(x):
    return "--" if x is None else "{:.1f}\\%".format(100.0 * x)


def ci_text(d):
    if d["rate"] is None:
        return "n/a"
    if d["lo"] is None:
        return "{:.1%} ({}/{})".format(d["rate"], d["k"], d["n"])
    return "{:.1%} [{:.1%}, {:.1%}] ({}/{})".format(d["rate"], d["lo"], d["hi"], d["k"], d["n"])


# --------------------------------------------------------------------------- #
# main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cores", default="16-19")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    cores = n2.parse_cores(args.cores)
    os.sched_setaffinity(0, set(cores))
    stamp = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
    check = n2.Checker()

    pub, held, pub_items, held_items, man = load_sets(check)
    paths, digests = instance_maps(pub_items + held_items, check)
    anchors, _ap, anchor_gaps = n2.e1dg.load_anchors(check)
    dg14 = n2.dg14_settings(check)
    brackets, _items, _props, _census, odig = n2.load_oracle(check)
    gin = guard_inputs(pub_items + held_items, digests, paths, args.workers, cores)

    store = {}
    for iid, p in paths.items():
        with open(p, encoding="utf-8") as fh:
            store[iid] = json.load(fh)
    rows_p = make_rows(pub_items, gin, "published", anchors, anchor_gaps, check)
    rows_h = make_rows(held_items, gin, "heldout", anchors, anchor_gaps, check)
    attach_fp(rows_p + rows_h, store)

    # Brackets for field fingerprints the oracle did not compute.
    trows = trade_rows()
    need = {}
    for r in rows_p + rows_h:
        k = (r["instance_id"], r["fingerprint"])
        if k not in brackets:
            need[k] = {"tfps": r["_tfps"]}
    extra = relaxed_brackets(trows, need)
    allb = dict(brackets)
    allb.update(extra)
    binfo = n2.base_info(brackets, sorted(store))
    cb = c_brackets()
    for r in rows_p + rows_h:
        n2.attach_oracle(r, allb, binfo)
        n2.prices(r)
        n2.errors(r)
        attach_c(r, cb)
        st = settings(dg14)
        for gate in GATES:
            r["refer_" + gate] = n2.refers(r, gate, st[gate])

    # Published rows reproduce the N2 direct rows.
    n2rows = {r["item_id"]: r for r in n2.read_csv_comments(ANALYSIS / "N2_rows_direct.csv")}
    for r in rows_p:
        q = n2rows[r["item_id"]]
        for mine, theirs in (("gap_cert", "gap_cert"), ("p_D-REL2", "p_D-REL2"),
                             ("p_G-CERT-M", "p_G-CERT-M"), ("obj", "obj")):
            check.true("{} {} equals N2_rows_direct".format(r["item_id"], mine),
                       abs(float(r[mine]) - float(q[theirs])) <= 1e-6,
                       "{} vs {}".format(r[mine], q[theirs]))
    check.done()

    boot = n2.Boot(sorted(store), n2.SEED, n2.B_BOOT)
    v3h = [r for r in rows_h if r["role"] == "V3"]
    twh = [r for r in rows_h if r["role"] == "twin"]
    v3p = [r for r in rows_p if r["role"] == "V3"]
    c_cov_h = sum(1 for r in rows_h if r["c_covered"])
    c_cov_p = sum(1 for r in rows_p if r["c_covered"])
    g_cov_h = sum(1 for r in rows_h if r["covered"])

    disp_c = disposition(rows_h, boot, dg14, "c") if c_cov_h else []
    st = settings(dg14)

    # ---------------- CSVs ---------------- #
    hdr = ["N9 held-out gates ({}), {}".format(VERSION, stamp),
           "generated by code/scripts/n9_gates.py",
           "held-out file code/suite/v0.3_heldout/suite_heldout.jsonl sha256 {}".format(
               man["artifacts"]["suite_heldout.jsonl"]["sha256"]),
           "published operating points: G-CERT and G-CERT-M tau=0.20; D-REL1 theta={:g}, "
           "D-REL2 theta={:g}, D-ABS A={:g} bh".format(dg14["D-REL1"], dg14["D-REL2"], dg14["D-ABS"]),
           "g = (obj - OPT)/max(OPT,1) over the relaxed bracket; c = (OPT_c - OPT)/max(OPT,1) "
           "from results/n9_instruction_cost/brackets.jsonl",
           "coverage: g {}/{} rows; c {}/{} rows".format(g_cov_h, len(rows_h), c_cov_h, len(rows_h))]
    write_rows(ANALYSIS / "N9_heldout.csv", rows_h, hdr)
    write_rows(ANALYSIS / "N9_published_v3.csv", rows_p,
               hdr[:2] + ["published suite code/suite/v0.2/suite.jsonl sha256 {}".format(
                   sg.SUITE_SHA256)] + hdr[3:5] +
               ["coverage: c {}/{} rows".format(c_cov_p, len(rows_p))])

    # ---------------- summary numbers ---------------- #
    summary = OrderedDict()
    fam = Counter(r["family_id"] for r in v3h)
    summary["heldout_by_family"] = dict(fam)
    summary["heldout_positive_badness_share"] = sum(1 for r in v3h if r["badness"] > 1e-6) / len(v3h)
    summary["heldout_badness_relative_min"] = min(r["badness_relative"] for r in v3h)
    summary["heldout_badness_relative_median"] = statistics.median(r["badness_relative"] for r in v3h)
    summary["heldout_drel2_refers_share"] = sum(1 for r in v3h if r["refer_D-REL2"]) / len(v3h)
    summary["heldout_cert_refers_share"] = sum(1 for r in v3h if r["refer_G-CERT"]) / len(v3h)

    # The no-CP-SAT part: g on reorder-only (and covered) items.
    gcov = [r for r in v3h if r["covered"]]
    g_tables = OrderedDict()
    for delta in DELTAS:
        costly = [r for r in gcov if g_state(r, delta) == 1]
        g_tables[delta] = {gate: rate(boot, costly, [n2.refers(r, gate, st[gate]) for r in costly])
                           for gate in GATES}
        g_tables[delta]["_n_costly"] = len(costly)
        g_tables[delta]["_n_covered"] = len(gcov)
    fr_tw = {gate: rate(boot, twh, [n2.refers(r, gate, st[gate]) for r in twh]) for gate in GATES}
    under_g = {gate: under_over([r for r in rows_h if r["role"] == "V3"], gate, err_vs_g)
               for gate in GATES}

    c_part = None
    if c_cov_h or c_cov_p:
        c_part = OrderedDict()
        for delta in DELTAS:
            c_part["heldout_costly_share_{}".format(delta)] = share(
                boot, [r for r in v3h if r["c_covered"]], lambda r, d=delta: c_state(r, d) == 1)
            c_part["heldout_cheap_share_{}".format(delta)] = share(
                boot, [r for r in v3h if r["c_covered"]], lambda r, d=delta: c_state(r, d) == 0)
        c_part["under_c"] = {gate: under_over(v3h, gate, err_vs_c) for gate in GATES}
        pubc = [r for r in v3p if r["c_covered"]]
        if pubc:
            c_part["published_costly_share_0.05"] = share(boot, pubc, lambda r: c_state(r, 0.05) == 1)
            c_part["published_median_c"] = (statistics.median(r["c_lo"] for r in pubc),
                                            statistics.median(r["c_hi"] for r in pubc))
            c_part["published_mcert_vs_c"] = closeness(pubc, "p_G-CERT-M")
            c_part["published_drel2_vs_c"] = closeness(pubc, "p_D-REL2")
            for r in pubc:
                r["_m_true_mid"] = None if r["m_lo"] is None else 0.5 * (r["m_lo"] + r["m_hi"])
            c_part["published_mtrue_vs_c"] = closeness(pubc, "_m_true_mid")

    # ---------------- summary markdown ---------------- #
    L = []
    A = L.append
    A("# N9. Instruction cost under optimal execution, and the gates on a held-out V3 draw")
    A("")
    A("Generated {} by `code/scripts/n9_gates.py` ({}).".format(stamp, VERSION))
    A("")
    status = "COMPLETE" if c_cov_h == len(rows_h) and c_cov_p == len(rows_p) else "PARTIAL"
    A("**Coverage: {}.** c brackets present for {}/{} held-out rows and {}/{} published rows; "
      "g brackets for {}/{} held-out rows (reorder-only items use the baseline bracket; "
      "window items need the campaign's relaxed solves).".format(
          status, c_cov_h, len(rows_h), c_cov_p, len(rows_p), g_cov_h, len(rows_h)))
    A("")
    A("## Held-out draw (no badness screen)")
    A("")
    A("| family | items |")
    A("|---|---|")
    for f, n in sorted(fam.items()):
        A("| {} | {} |".format(f, n))
    A("")
    A("Share of held-out V3 items whose faithful translation degrades the ATC dispatch "
      "(badness > 0, the published admission statistic): {:.1%}. badness_relative: min {:.4f}, "
      "median {:.4f}.".format(summary["heldout_positive_badness_share"],
                              summary["heldout_badness_relative_min"],
                              summary["heldout_badness_relative_median"]))
    A("")
    A("## Gates at the published operating points, against g (no CP-SAT needed for reorder-only items)")
    A("")
    A("Detection on held-out V3 items with g_lo > delta (whole interval above delta), "
      "among {} items with a g bracket:".format(len(gcov)))
    A("")
    A("| delta | g-costly items | " + " | ".join(GATES) + " |")
    A("|---|---|" + "---|" * len(GATES))
    for delta in DELTAS:
        t = g_tables[delta]
        A("| {:g} | {} | ".format(delta, t["_n_costly"]) +
          " | ".join(ci_text(t[g]) for g in GATES) + " |")
    A("")
    A("Referrals of the 220 held-out benign twins (all twins):")
    A("")
    A("| " + " | ".join(GATES) + " |")
    A("|" + "---|" * len(GATES))
    A("| " + " | ".join(ci_text(fr_tw[g]) for g in GATES) + " |")
    A("")
    A("Under-/over-pricing against g on held-out V3 items (e < -0.05 / e > +0.05, decided rows):")
    A("")
    A("| gate | under | over | decided |")
    A("|---|---|---|---|")
    for g in GATES:
        u, o, d = under_g[g]
        A("| {} | {} | {} | {} |".format(g, u, o, d))
    A("")
    if disp_c:
        A("## Gates against the instruction cost c (held-out)")
        A("")
        A("| delta | point | gate | c-costly | detect | false referral, c-cheap V3 | "
          "false referral, twins | false referral, c-cheap twins |")
        A("|---|---|---|---|---|---|---|---|")
        for d in disp_c:
            A("| {:g} | {} | {} | {} | {} | {} | {} | {} |".format(
                d["delta"], d["operating_point"], d["gate"], d["v3_costly"], ci_text(d["detect"]),
                ci_text(d["fr_cheap_v3"]), ci_text(d["fr_twins"]), ci_text(d["fr_cheap_twins"])))
        A("")
    else:
        A("## Gates against the instruction cost c")
        A("")
        A("Not yet computed: results/n9_instruction_cost/brackets.jsonl holds no complete row. "
          "These tables are filled when the timed campaign has run.")
        A("")
    if c_part:
        A("## Labels from c")
        A("")
        for delta in DELTAS:
            A("- held-out V3 with c_lo > {:g}: {}; with c_hi <= {:g}: {}".format(
                delta, ci_text(c_part["heldout_costly_share_{}".format(delta)]), delta,
                ci_text(c_part["heldout_cheap_share_{}".format(delta)])))
        A("")
        A("| gate | under-priced vs c | over-priced vs c | decided |")
        A("|---|---|---|---|")
        for g in GATES:
            u, o, dd = c_part["under_c"][g]
            A("| {} | {} | {} | {} |".format(g, u, o, dd))
        A("")
        if "published_median_c" in c_part:
            A("Published V3: c_lo > 0.05 on {}; median c [{:.4f}, {:.4f}].".format(
                ci_text(c_part["published_costly_share_0.05"]), *c_part["published_median_c"]))
            for k, lab in (("published_mcert_vs_c", "m_cert (G-CERT-M price)"),
                           ("published_drel2_vs_c", "D-REL2 statistic"),
                           ("published_mtrue_vs_c", "oracle marginal m_true (midpoint)")):
                cc = c_part[k]
                if cc is None:
                    continue
                A("- {} vs c over {} items: median |.-c| in [{:.4f}, {:.4f}]; |.-c| <= 0.02 on "
                  "[{:.1%}, {:.1%}]; <= 0.05 on [{:.1%}, {:.1%}]".format(
                      lab, cc["n"], cc["median_lo"], cc["median_hi"],
                      cc["within_0.02"]["share_lo"], cc["within_0.02"]["share_hi"],
                      cc["within_0.05"]["share_lo"], cc["within_0.05"]["share_hi"]))
            A("")
    (ANALYSIS / "N9_summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # ---------------- macros ---------------- #
    M = ["% N9 macros, generated {} by code/scripts/n9_gates.py ({})".format(stamp, VERSION),
         "% coverage: c {}/{} held-out rows, {}/{} published rows; g {}/{} held-out rows".format(
             c_cov_h, len(rows_h), c_cov_p, len(rows_p), g_cov_h, len(rows_h)),
         "% LaTeX control words cannot carry digits, so the n9 prefix is spelled nNine."]
    macro(mname("Heldout", "Items"), str(len(v3h)), M)
    macro(mname("Heldout", "Positive", "Badness", "Share"),
          pct_text(summary["heldout_positive_badness_share"]), M)
    macro(mname("Heldout", "Badness", "Rel", "Median"),
          "{:.3f}".format(summary["heldout_badness_relative_median"]), M)
    macro(mname("Heldout", "G", "Covered"), str(len(gcov)), M)
    tok = n2.GATE_TOKEN
    for delta in DELTAS:
        macro(mname("Heldout", "G", "Costly", delta), str(g_tables[delta]["_n_costly"]), M)
        for g in GATES:
            macro(mname("Heldout", "G", "Detect", tok[g], delta), pct_text(g_tables[delta][g]["rate"]), M)
    for g in GATES:
        macro(mname("Heldout", "Twin", "Refer", tok[g]), pct_text(fr_tw[g]["rate"]), M)
    if c_part:
        for delta in DELTAS:
            macro(mname("Heldout", "C", "Costly", "Share", delta),
                  pct_text(c_part["heldout_costly_share_{}".format(delta)]["rate"]), M)
        for d in disp_c:
            if d["operating_point"] != "published":
                continue
            macro(mname("Heldout", "C", "Detect", tok[d["gate"]], d["delta"]),
                  pct_text(d["detect"]["rate"]), M)
            macro(mname("Heldout", "C", "Cheap", "Refer", tok[d["gate"]], d["delta"]),
                  pct_text(d["fr_cheap_v3"]["rate"]), M)
        for g in GATES:
            u, o, dd = c_part["under_c"][g]
            macro(mname("Heldout", "Under", "C", tok[g]), pct_text(u / dd if dd else None), M)
        if "published_median_c" in c_part:
            macro(mname("Pub", "C", "Costly", "Share", 0.05),
                  pct_text(c_part["published_costly_share_0.05"]["rate"]), M)
            macro(mname("Pub", "C", "Median", "Lo"), "{:.3f}".format(c_part["published_median_c"][0]), M)
            macro(mname("Pub", "C", "Median", "Hi"), "{:.3f}".format(c_part["published_median_c"][1]), M)
            for k, t in (("published_mcert_vs_c", "CertM"), ("published_drel2_vs_c", "RelTwo")):
                cc = c_part[k]
                if cc is None:
                    continue
                macro(mname("Pub", t, "Dist", "Median"), "{:.3f}".format(cc["median_hi"]), M)
                macro(mname("Pub", t, "Within", 0.02), pct_text(cc["within_0.02"]["share_lo"]), M)
                macro(mname("Pub", t, "Within", 0.05), pct_text(cc["within_0.05"]["share_lo"]), M)
    else:
        M.append("% the c-based macros (\\nNineHeldoutCCostlyShare..., \\nNineHeldoutCDetect..., "
                 "\\nNinePub...) are written once results/n9_instruction_cost/brackets.jsonl "
                 "holds complete rows")
    for g in GATES:
        u, o, dd = under_g[g]
        macro(mname("Heldout", "Under", "G", tok[g]), pct_text(u / dd if dd else None), M)
    (ANALYSIS / "N9_macros.tex").write_text("\n".join(M) + "\n", encoding="utf-8")
    print("[n9d] wrote analysis/N9_heldout.csv, N9_published_v3.csv, N9_summary.md, N9_macros.tex")
    print("[n9d] coverage: c held-out {}/{}, published {}/{}; g held-out {}/{}".format(
        c_cov_h, len(rows_h), c_cov_p, len(rows_p), g_cov_h, len(rows_h)))
    print("\n".join(L[:60]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
