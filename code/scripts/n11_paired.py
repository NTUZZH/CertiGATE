#!/usr/bin/env python
"""N11 Stage 3, paired comparison of the known-board gate (K) and the full-information gate (FI).

QUESTION
--------
Stage 3 reports the miss share and the false-referral share of every gate
design under each reading as separate marginal shares with separate
cluster-bootstrap intervals (analysis/N11F_consequence.csv).  K and FI are
scored on the same items against the same truth, so the comparison is paired.
This script computes, per design, the paired difference K minus FI in

  (a) the miss share among costly proposals, and
  (b) the false-referral share among cheap proposals,

with a 95% cluster-bootstrap interval over instances that applies the SAME
resampled instance multiset to both readings in each replicate, plus the
discordant item counts (missed or falsely referred under K only, FI only, both).

INPUTS (read only; no solve is re-run)
-------------------------------------
analysis/N11_rows_forecast.csv          one row per (priced issuable item, reading),
                                        written by n11_forecast.py analyse; carries
                                        refers_<design>, refers_union and the
                                        original-field marginal-cost truth interval
analysis/N11F_consequence.csv           the published K and FI counts and intervals,
                                        reproduced here as a run-fatal assertion
results/n11_decision_time/items.jsonl   the issuable_strict flag and the instance
                                        list that defines the bootstrap clusters

DEFINITIONS (identical to n11_forecast.consequence)
---------------------------------------------------
population   published, issuable (t_known <= t_start), priced at the quality
             stage on K (1,356 items); the strict variant keeps the subset with
             t_known < t_start.
truth        'orig': the realised marginal cost on the original fields, as the
             interval [orig_m_lo, orig_m_hi]; an item without it is excluded.
costly       orig_m_lo > delta; cheap: orig_m_hi <= delta; otherwise excluded.
refers       the published per-reading flag (median aggregation; K and FI carry
             one price each, so no item is Monte Carlo undecided).
miss         a costly item that the design does not refer.
false ref.   a cheap item that the design refers.
bootstrap    n2_pricing.Boot over the sorted published instances, seed
             n2_pricing.SEED, n2_pricing.B_BOOT replicates, percentile interval
             at alpha = 0.05 (e1_delta_guard_replay.ALPHA); the paired replicate
             statistic is sum_c(miss_K - miss_FI) / sum_c(costly), the
             denominator being common to both readings.

Run: taskset -c 12-13 python code/scripts/n11_paired.py
Version: l1-n11-paired-1
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_v] = "1"

import csv  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
from collections import OrderedDict  # noqa: E402
from pathlib import Path  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

ALLOWED_CORES = {12, 13}
_aff = set(os.sched_getaffinity(0))
if not _aff <= ALLOWED_CORES and not os.environ.get("CERTIGATE_ANY_CORES"):
    raise SystemExit("REFUSING TO RUN: affinity {} is not inside cores 12-13 "
                     "(run under taskset -c 12-13)".format(sorted(_aff)))

import numpy as np  # noqa: E402
import n2_pricing as n2  # noqa: E402
import e1_delta_guard_replay as e1dg  # noqa: E402

VERSION = "l1-n11-paired-1"
ROOT = SCRIPTS_DIR.parent.parent
ANALYSIS = ROOT / "analysis"
ROWS_CSV = ANALYSIS / "N11_rows_forecast.csv"
CONS_CSV = ANALYSIS / "N11F_consequence.csv"
ITEMS = ROOT / "results" / "n11_decision_time" / "items.jsonl"
OUT_CSV = ANALYSIS / "N11F_paired.csv"
OUT_TEX = ANALYSIS / "N11F_paired_macros.tex"

DESIGNS = OrderedDict([("G-CERT", "Cert"), ("G-CERT-M", "CertM"), ("D-REL1", "RelOne"),
                       ("D-REL2", "RelTwo"), ("D-ABS", "Abs"), ("G-CERT-M|D-REL2", "UnionM")])
FLAG = {g: ("refers_union" if "|" in g else "refers_" + g) for g in DESIGNS}
DELTAS = OrderedDict([(0.10, "DeltaTen"), (0.20, "DeltaTwenty")])
POPS = OrderedDict([("issuable", ""), ("issuable_strict", "Strict")])
TRUTH = "orig"
TOL = 1e-9


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path) -> list:
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def fnum(x):
    return None if x in ("", None) else float(x)


def fbool(x) -> bool:
    if x not in ("True", "False"):
        raise SystemExit("unexpected boolean cell {!r}".format(x))
    return x == "True"


def costly_of(lo, hi, delta):
    """n11_forecast.costly_of on the 'orig' truth."""
    if lo is None or hi is None:
        return None
    if lo > delta:
        return 1
    if hi <= delta:
        return 0
    return None


def pct(x, d=1) -> str:
    return "n/a" if x is None else "{:.{}f}\\%".format(100.0 * x, d)


def pp(x, d=1) -> str:
    if x is None:
        return "n/a"
    s = "{:.{}f}".format(100.0 * x, d)
    return "0.0" if s in ("-0.0", "0.0") else s


def paired(items, flag_k, flag_f, boot):
    """Counts, marginal and paired shares and intervals for one flag pair."""
    n = len(items)
    out = OrderedDict(n=n)
    if n == 0:
        out.update(k=0, f=0, k_only=0, f_only=0, both=0, neither=0, share_k=None, share_f=None,
                   diff=None, diff_lo=None, diff_hi=None, k_lo=None, k_hi=None, f_lo=None,
                   f_hi=None)
        return out
    ek = np.array([1.0 if flag_k(r) else 0.0 for r in items])
    ef = np.array([1.0 if flag_f(r) else 0.0 for r in items])
    ci_idx = np.array([boot.index[r["instance_id"]] for r in items], dtype=int)
    den = np.ones(n)
    ak, b = e1dg.cluster_sums(ek, den, ci_idx, boot.k)
    af, _ = e1dg.cluster_sums(ef, den, ci_idx, boot.k)
    ad, _ = e1dg.cluster_sums(ek - ef, den, ci_idx, boot.k)
    k_lo, k_hi = e1dg.bootstrap_ci(ak, b, boot.idx)
    f_lo, f_hi = e1dg.bootstrap_ci(af, b, boot.idx)
    # Paired replicate: the same resampled instances for both readings; the
    # replicate statistic is sum(miss_K - miss_FI) / sum(population).
    n_s = ad[boot.idx].sum(axis=1)
    d_s = b[boot.idx].sum(axis=1)
    good = d_s > 0
    r = n_s[good] / d_s[good]
    lo, hi = np.percentile(r, [100 * e1dg.ALPHA / 2, 100 * (1 - e1dg.ALPHA / 2)])
    out.update(k=int(ek.sum()), f=int(ef.sum()),
               k_only=int(((ek == 1) & (ef == 0)).sum()),
               f_only=int(((ek == 0) & (ef == 1)).sum()),
               both=int(((ek == 1) & (ef == 1)).sum()),
               neither=int(((ek == 0) & (ef == 0)).sum()),
               share_k=ek.mean(), share_f=ef.mean(), diff=ek.mean() - ef.mean(),
               diff_lo=float(lo), diff_hi=float(hi), k_lo=k_lo, k_hi=k_hi, f_lo=f_lo, f_hi=f_hi,
               boot_valid=int(good.sum()))
    return out


def main() -> int:
    inputs = OrderedDict((str(p.relative_to(ROOT)), sha256(p)) for p in (ROWS_CSV, CONS_CSV, ITEMS))
    items_all = [json.loads(ln) for ln in open(ITEMS, encoding="utf-8") if ln.strip()]
    pub = [r for r in items_all if r["set"] == "published"]
    strict = {r["item_id"]: bool(r["issuable_strict"]) for r in pub}
    issuable = {r["item_id"]: bool(r["issuable"]) for r in pub}
    assert sum(not v for v in strict.values()) == 731, "strict not-issuable count != 731"
    boot = n2.Boot({r["instance_id"] for r in pub}, n2.SEED, n2.B_BOOT)
    assert boot.k == 60, boot.k

    rows = read_csv(ROWS_CSV)
    by = {}
    for r in rows:
        if r["reading"] not in ("K", "FI"):
            continue
        it = by.setdefault(r["item_id"], {"item_id": r["item_id"],
                                          "instance_id": r["instance_id"],
                                          "split": r["split"],
                                          "primary_class": r["primary_class"],
                                          "lo": fnum(r["orig_m_lo"]), "hi": fnum(r["orig_m_hi"])})
        assert it["instance_id"] == r["instance_id"] and it["lo"] == fnum(r["orig_m_lo"])
        if r["mc_undecided"]:
            raise SystemExit("K/FI row is MC-undecided: {}".format(r["item_id"]))
        it[r["reading"]] = {g: fbool(r[FLAG[g]]) for g in DESIGNS}
    priced = list(by.values())
    assert len(priced) == 1356, len(priced)
    assert all("K" in it and "FI" in it for it in priced)
    assert all(issuable[it["item_id"]] for it in priced)

    # ---- assertion: reproduce the published K and FI cells before writing anything
    cons = read_csv(CONS_CSV)
    pubcell = {}
    for c in cons:
        if (c["truth"] == TRUTH and c["agg"] == "median" and c["group_kind"] == "all"
                and c["reading"] in ("K", "FI")):
            pubcell[(round(float(c["delta"]), 6), c["reading"], c["gate"])] = c
    results = []
    checks = []
    for pop, ptok in POPS.items():
        members = [it for it in priced if pop == "issuable" or strict[it["item_id"]]]
        for delta, dtok in DELTAS.items():
            cl = [(it, costly_of(it["lo"], it["hi"], delta)) for it in members]
            costly = [it for it, s in cl if s == 1]
            cheap = [it for it, s in cl if s == 0]
            for g, gtok in DESIGNS.items():
                m = paired(costly, lambda r, g=g: not r["K"][g], lambda r, g=g: not r["FI"][g], boot)
                f = paired(cheap, lambda r, g=g: r["K"][g], lambda r, g=g: r["FI"][g], boot)
                # field-changing / sequencing split of the discordant misses
                def split_count(cond):
                    return sum(1 for r in costly if cond(r) and r["split"] == "field_changing")
                m_k_only_field = split_count(lambda r: (not r["K"][g]) and r["FI"][g])
                m_f_only_field = split_count(lambda r: r["K"][g] and not r["FI"][g])
                m_both_field = split_count(lambda r: (not r["K"][g]) and not r["FI"][g])
                rec = OrderedDict(version=VERSION, population=pop, truth=TRUTH, delta=delta,
                                  gate=g, costly=m["n"], miss_K=m["k"], miss_FI=m["f"],
                                  miss_share_K=m["share_k"], miss_share_FI=m["share_f"],
                                  miss_lo_K=m["k_lo"], miss_hi_K=m["k_hi"],
                                  miss_lo_FI=m["f_lo"], miss_hi_FI=m["f_hi"],
                                  miss_diff=m["diff"], miss_diff_lo=m["diff_lo"],
                                  miss_diff_hi=m["diff_hi"],
                                  miss_K_only=m["k_only"], miss_FI_only=m["f_only"],
                                  miss_both=m["both"], miss_neither=m["neither"],
                                  miss_K_only_field=m_k_only_field,
                                  miss_FI_only_field=m_f_only_field,
                                  miss_both_field=m_both_field,
                                  cheap=f["n"], fr_K=f["k"], fr_FI=f["f"],
                                  fr_share_K=f["share_k"], fr_share_FI=f["share_f"],
                                  fr_lo_K=f["k_lo"], fr_hi_K=f["k_hi"],
                                  fr_lo_FI=f["f_lo"], fr_hi_FI=f["f_hi"],
                                  fr_diff=f["diff"], fr_diff_lo=f["diff_lo"],
                                  fr_diff_hi=f["diff_hi"],
                                  fr_K_only=f["k_only"], fr_FI_only=f["f_only"],
                                  fr_both=f["both"], fr_neither=f["neither"],
                                  boot_B=n2.B_BOOT, boot_seed=n2.SEED, clusters=boot.k)
                results.append(rec)
                if pop != "issuable":
                    continue
                for rd, mk, fk, mlo, mhi, flo, fhi in (
                        ("K", "miss_K", "fr_K", "miss_lo_K", "miss_hi_K", "fr_lo_K", "fr_hi_K"),
                        ("FI", "miss_FI", "fr_FI", "miss_lo_FI", "miss_hi_FI", "fr_lo_FI",
                         "fr_hi_FI")):
                    c = pubcell[(round(delta, 6), rd, g)]
                    ok = (int(c["costly"]) == rec["costly"] and int(c["miss"]) == rec[mk]
                          and int(c["cheap"]) == rec["cheap"] and int(c["fr"]) == rec[fk]
                          and int(c["mc_undecided"]) == 0)
                    for col, mine in (("miss_lo", rec[mlo]), ("miss_hi", rec[mhi]),
                                      ("fr_lo", rec[flo]), ("fr_hi", rec[fhi])):
                        ok = ok and (c[col] == "" and mine is None or
                                     c[col] != "" and mine is not None
                                     and abs(float(c[col]) - mine) < 5e-7)
                    checks.append((delta, rd, g, ok))
                    if not ok:
                        raise SystemExit("ASSERTION FAILED: published cell not reproduced: "
                                         "delta={} reading={} gate={} published={} mine={}".format(
                                             delta, rd, g, dict(c), dict(rec)))
    # the headline cells named in the design
    def cell(pop, delta, g):
        return next(r for r in results if r["population"] == pop and abs(r["delta"] - delta) < TOL
                    and r["gate"] == g)
    h = cell("issuable", 0.10, "G-CERT-M")
    assert (h["miss_K"], h["costly"], h["miss_FI"]) == (26, 208, 31), h
    assert (h["fr_K"], h["cheap"], h["fr_FI"]) == (0, 1148, 0), h
    for r in results:
        assert r["miss_K"] - r["miss_FI"] == r["miss_K_only"] - r["miss_FI_only"]
        assert r["miss_K"] == r["miss_K_only"] + r["miss_both"]
        assert r["fr_K"] == r["fr_K_only"] + r["fr_both"]
        if r["miss_diff"] is not None:
            assert r["miss_diff_lo"] - TOL <= r["miss_diff"] + 1e-12 or r["miss_K_only"] + \
                r["miss_FI_only"] > 0
    print("[n11 paired] {} published cells reproduced (counts and intervals)".format(len(checks)),
          flush=True)

    # ---- outputs
    cols = list(results[0].keys())
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        fh.write("# N11 Stage 3 paired K versus FI comparison ({}); generated by "
                 "code/scripts/n11_paired.py from analysis/N11_rows_forecast.csv\n".format(VERSION))
        fh.write("# truth orig (realised marginal cost, original fields); median aggregation; "
                 "diff = K minus FI; 95% paired cluster bootstrap over {} instances, B = {}, "
                 "seed {}\n".format(boot.k, n2.B_BOOT, n2.SEED))
        for k, v in inputs.items():
            fh.write("# input {} sha256 {}\n".format(k, v))
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in results:
            w.writerow({k: ("" if v is None else ("{:.6f}".format(v) if isinstance(v, float)
                                                  and k != "delta" else v)) for k, v in r.items()})

    lines = ["% N11 Stage 3 paired K-versus-FI macros ({}); generated by "
             "code/scripts/n11_paired.py; differences in percentage points (K minus FI)".format(
                 VERSION)]
    names = set()

    def add(name, value):
        full = "nElevenPaired" + name
        assert full.isalpha(), full
        assert full not in names, full
        names.add(full)
        lines.append("\\newcommand{\\" + full + "}{" + str(value) + "}")

    add("BootB", n2.B_BOOT)
    add("BootClusters", boot.k)
    for r in results:
        tok = POPS[r["population"]] + DESIGNS[r["gate"]]
        dt = DELTAS[r["delta"]]
        add(tok + "Costly" + dt, r["costly"])
        add(tok + "MissK" + dt, r["miss_K"])
        add(tok + "MissFI" + dt, r["miss_FI"])
        add(tok + "MissShareK" + dt, pct(r["miss_share_K"]))
        add(tok + "MissShareFI" + dt, pct(r["miss_share_FI"]))
        add(tok + "MissDiff" + dt, pp(r["miss_diff"]))
        add(tok + "MissDiff" + dt + "Lo", pp(r["miss_diff_lo"]))
        add(tok + "MissDiff" + dt + "Hi", pp(r["miss_diff_hi"]))
        add(tok + "Discordant" + "KOnly" + dt, r["miss_K_only"])
        add(tok + "Discordant" + "FIOnly" + dt, r["miss_FI_only"])
        add(tok + "Discordant" + "Both" + dt, r["miss_both"])
        add(tok + "Cheap" + dt, r["cheap"])
        add(tok + "FrK" + dt, r["fr_K"])
        add(tok + "FrFI" + dt, r["fr_FI"])
        add(tok + "FrShareK" + dt, pct(r["fr_share_K"]))
        add(tok + "FrShareFI" + dt, pct(r["fr_share_FI"]))
        add(tok + "FrDiff" + dt, pp(r["fr_diff"]))
        add(tok + "FrDiff" + dt + "Lo", pp(r["fr_diff_lo"]))
        add(tok + "FrDiff" + dt + "Hi", pp(r["fr_diff_hi"]))
        add(tok + "FrDiscordantKOnly" + dt, r["fr_K_only"])
        add(tok + "FrDiscordantFIOnly" + dt, r["fr_FI_only"])
        add(tok + "FrDiscordantBoth" + dt, r["fr_both"])
    with open(OUT_TEX, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("[n11 paired] wrote {} rows to {} and {} macros to {}".format(
        len(results), OUT_CSV.relative_to(ROOT), len(names), OUT_TEX.relative_to(ROOT)), flush=True)
    for r in results:
        print("{:16s} {:5.2f} {:16s} miss K {:3d} FI {:3d} /{:4d} diff {:+6.2f} [{:+6.2f}, {:+6.2f}] "
              "Konly {:2d} FIonly {:2d} both {:3d} (field {:2d}/{:2d}/{:3d}) | fr K {:3d} FI {:3d} "
              "/{:5d} diff {:+6.2f} [{:+6.2f}, {:+6.2f}] Konly {:2d} FIonly {:2d} both {:2d}".format(
                  r["population"], r["delta"], r["gate"], r["miss_K"], r["miss_FI"], r["costly"],
                  100 * r["miss_diff"], 100 * r["miss_diff_lo"], 100 * r["miss_diff_hi"],
                  r["miss_K_only"], r["miss_FI_only"], r["miss_both"], r["miss_K_only_field"],
                  r["miss_FI_only_field"], r["miss_both_field"], r["fr_K"], r["fr_FI"],
                  r["cheap"], 100 * r["fr_diff"], 100 * r["fr_diff_lo"], 100 * r["fr_diff_hi"],
                  r["fr_K_only"], r["fr_FI_only"], r["fr_both"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
