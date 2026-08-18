#!/usr/bin/env python
"""DG8-A: how often the Eq. 2 gap-denominator floor binds, and how much it matters.

Equation 2 of the manuscript is ``gap = (obj - LB) / max(LB, ell)`` with
``ell = 1`` weighted business hour (manuscript/drafts/s3_formulation.tex:207-219).
The manuscript declares the floor but never reports how often ``max(LB, ell)``
resolves to ``ell`` rather than to ``LB``.  Two verification passes produced two
slightly different shares because they scoped the denominator differently.  This
script computes the share under EVERY defensible scope so the choice can be made
in the open, reports the per-stratum split, the minimum positive lower bound, and
the sensitivity of the accept-or-block decision to ``ell``.

Sources (read-only)
-------------------
* ``results/e1_eval_<arm>/verdicts_G_CERT.jsonl`` for the eight E1 arms: one row
  per (arm, mode, thinking, repeat, item_id), carrying ``certificate.obj_bh``,
  ``certificate.lb_bh``, ``certificate_gap``, ``infra``, ``stratum``,
  ``primary_class``.
* ``results/e1_eval_<arm>/verdicts_G_FEAS.jsonl`` for the same grid, needed only
  to reproduce Table 8's V3-separation denominator (feasibility-passed rows).
* ``analysis/T6_tau_calibration.csv`` as the published answer the self-check is
  compared against.

Self-check (runs first; the script exits non-zero if it fails)
--------------------------------------------------------------
1. The logged ``certificate_gap`` is reproduced exactly by
   ``(obj_bh - lb_bh) / max(lb_bh, 1.0)`` clamped at zero, on every certificate.
2. Every published cell of Table 8 (``analysis/T6_tau_calibration.csv``:
   ``v3_separation_share``, ``false_block_rate``, ``schema_feas_false_block_floor``,
   ``operating_point_fb5pct``) is reproduced from the raw verdict logs at
   ``ell = 1``, for all ten constrained arm configurations at every swept tau.

Only after both pass does the script report anything new.

Version: l1-dg8-floor-1
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

VERSION = "l1-dg8-floor-1"

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS = ROOT / "results"
ANALYSIS = ROOT / "analysis"

# ---- the sweep's own vocabulary, copied from code/scripts/e2_tau_sweep.py ---- #
TAU_GRID = (0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 1.00)
ANCHOR_TAU = 0.20
APPLIED_WITH_CERTIFICATE = "applied_with_certificate"
APPLIED_UNCERTIFIED = "applied_uncertified"
BLOCKED_SCHEMA = "blocked_schema"
BLOCKED_FEAS = "blocked_feas"
BLOCKED_QUAL = "blocked_qual"
PRE_QUAL_BLOCKS = (BLOCKED_SCHEMA, BLOCKED_FEAS)
BLOCKED_STATES = (BLOCKED_SCHEMA, BLOCKED_FEAS, BLOCKED_QUAL)
APPLIED_STATES = (APPLIED_WITH_CERTIFICATE, APPLIED_UNCERTIFIED)
BENIGN = "benign"
CLASSES = ["benign", "V1", "V2", "V3", "V4", "V5", "V6"]

#: The ell values swept.  1.0 is the declared convention.
ELL_GRID = (0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 25.0, 50.0, 100.0, 500.0)

E1_DIRS = ["qwen14b", "qwen27b", "glm9b", "gpt54mini", "deepseek",
           "sonnet5", "opus5", "sol"]

#: The paper's constrained-mode roster, in table order (paper_macros.py
#: CONSTRAINED_ROWS).  The capability set is this minus DeepSeek's two rows
#: (paper_macros.py CAPABILITY_ROWS; decisions.md 2026-08-13 ruling 2).
CONSTRAINED_ROWS = [
    ("qwen3-14b", "-"), ("qwen3.6-27b-fp8", "-"), ("glm-4-9b", "-"),
    ("openai", "-"), ("deepseek", "non_think"), ("deepseek", "think_high"),
    ("sonnet", "disabled"), ("opus", "default"), ("opus", "disabled"),
    ("sol", "none"),
]
CAPABILITY_ROWS = [r for r in CONSTRAINED_ROWS if r[0] != "deepseek"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def certified_gap(obj_bh: float, lb_bh: float, floor_bh: float) -> float:
    """Verbatim from code/l1guard/verdict.py:73-84."""
    denom = lb_bh if lb_bh > floor_bh else floor_bh
    gap = (float(obj_bh) - float(lb_bh)) / float(denom)
    return gap if gap > 0.0 else 0.0


def tau_label(tau: float) -> str:
    return "{:.2f}".format(tau)


def load_rows() -> tuple[list, dict]:
    """Join G_CERT and G_FEAS verdicts on (arm, mode, thinking, repeat, item_id)."""
    rows = []
    hashes = OrderedDict()
    for d in E1_DIRS:
        cert_path = RESULTS / ("e1_eval_" + d) / "verdicts_G_CERT.jsonl"
        feas_path = RESULTS / ("e1_eval_" + d) / "verdicts_G_FEAS.jsonl"
        for p in (cert_path, feas_path):
            if not p.is_file():
                raise SystemExit("missing source: {}".format(p))
            hashes[str(p.relative_to(ROOT))] = sha256(p)

        feas_by_key = {}
        with feas_path.open() as fh:
            for line in fh:
                r = json.loads(line)
                key = (r["arm"], r["mode"], r.get("thinking"), r.get("repeat"),
                       r["item_id"])
                if key in feas_by_key:
                    raise SystemExit("duplicate G_FEAS key {}".format(key))
                feas_by_key[key] = r

        with cert_path.open() as fh:
            for line in fh:
                r = json.loads(line)
                key = (r["arm"], r["mode"], r.get("thinking"), r.get("repeat"),
                       r["item_id"])
                feas = feas_by_key.get(key)
                if feas is None:
                    raise SystemExit("G_CERT row with no G_FEAS twin: {}".format(key))
                cert = r.get("certificate")
                rows.append({
                    # T6/T1 print a bare "-" where the arm sends no thinking
                    # field at all; the verdict log carries JSON null.  Normalise
                    # so the join against the published tables is exact.
                    "arm": r["arm"], "mode": r["mode"],
                    "thinking": r.get("thinking") or "-", "repeat": r.get("repeat"),
                    "item_id": r["item_id"], "instance_id": r["instance_id"],
                    "primary_class": r["primary_class"],
                    "stratum": r["stratum"],
                    "cert_terminal": r["terminal"],
                    "cert_infra": bool(r["infra"]),
                    "feas_terminal": feas["terminal"],
                    "feas_infra": bool(feas["infra"]),
                    "gap": r.get("certificate_gap"),
                    "obj_bh": None if cert is None else cert.get("obj_bh"),
                    "lb_bh": None if cert is None else cert.get("lb_bh"),
                    "blocking_codes": tuple(r.get("blocking_codes") or ()),
                })
    return rows, hashes


# --------------------------------------------------------------------------- #
# Self-check 1: the logged gap is Eq. 2 at ell = 1                             #
# --------------------------------------------------------------------------- #
def selfcheck_gap_formula(rows: list) -> dict:
    n = 0
    worst = 0.0
    bad = []
    for r in rows:
        if r["gap"] is None:
            continue
        if r["obj_bh"] is None or r["lb_bh"] is None:
            bad.append((r["item_id"], "certificate without obj/lb"))
            continue
        n += 1
        recomputed = certified_gap(r["obj_bh"], r["lb_bh"], 1.0)
        delta = abs(recomputed - r["gap"])
        worst = max(worst, delta)
        if delta > 0.0:
            bad.append((r["item_id"], delta))
    return {"n_certificates": n, "max_abs_delta": worst, "n_mismatch": len(bad),
            "examples": bad[:5]}


# --------------------------------------------------------------------------- #
# Self-check 2: reproduce every published Table 8 cell from the raw logs       #
# --------------------------------------------------------------------------- #
def terminal_at(row: dict, tau: float, ell: float) -> str:
    """The G_CERT terminal this row would have had at tolerance tau and floor ell."""
    terminal = row["cert_terminal"]
    if terminal in PRE_QUAL_BLOCKS:
        return terminal
    if row["gap"] is None:
        return terminal
    gap = row["gap"] if ell == 1.0 else certified_gap(row["obj_bh"], row["lb_bh"], ell)
    return BLOCKED_QUAL if gap > tau else APPLIED_WITH_CERTIFICATE


def group_curve(rows: list, ell: float) -> dict:
    """Table 8's quantities for one (arm, mode, thinking) group at every tau."""
    cert_eligible = [r for r in rows if not r["cert_infra"]]
    both_eligible = [r for r in rows if not r["cert_infra"] and not r["feas_infra"]]
    benign_sel = [r for r in cert_eligible if r["primary_class"] == BENIGN]
    v3_sel = [r for r in both_eligible if r["primary_class"] == "V3"]
    v3_feas_pass = [r for r in v3_sel if r["feas_terminal"] in APPLIED_STATES]

    # The floor is the share of benign twins blocked before stage 3; no tau or
    # ell can move it.
    floor = (sum(1 for r in benign_sel if r["cert_terminal"] in PRE_QUAL_BLOCKS)
             / len(benign_sel)) if benign_sel else None

    points = OrderedDict()
    for tau in TAU_GRID:
        fb = sum(1 for r in benign_sel if terminal_at(r, tau, ell) in BLOCKED_STATES)
        sep = sum(1 for r in v3_feas_pass
                  if terminal_at(r, tau, ell) in BLOCKED_STATES)
        points[tau_label(tau)] = {
            "false_block_rate": None if not benign_sel else fb / len(benign_sel),
            "v3_items": len(v3_sel),
            "v3_separated": sep,
            "v3_separation_share": None if not v3_sel else sep / len(v3_sel),
        }
    qualifying = [t for t in TAU_GRID
                  if points[tau_label(t)]["false_block_rate"] is not None
                  and points[tau_label(t)]["false_block_rate"] <= 0.05]
    return {"points": points, "floor": floor,
            "operating_tau_fb5": (min(qualifying) if qualifying else None),
            "n_rows": len(rows), "n_cert_eligible": len(cert_eligible)}


def selfcheck_table8(rows: list) -> dict:
    """Assert every published T6 cell for the constrained rows is reproduced."""
    t6 = ANALYSIS / "T6_tau_calibration.csv"
    published = {}
    with t6.open() as fh:
        body = [ln for ln in fh if not ln.startswith("#")]
    for rec in csv.DictReader(body):
        key = (rec["arm"], rec["mode"], rec["thinking"], rec["tau"])
        published[key] = rec

    groups = OrderedDict()
    for r in rows:
        groups.setdefault((r["arm"], r["mode"], r["thinking"]), []).append(r)

    checked = 0
    mismatches = []
    for (arm, mode, thinking), grp in groups.items():
        curve = group_curve(grp, 1.0)
        for tau in TAU_GRID:
            key = (arm, mode, thinking, "{:.2f}".format(tau))
            rec = published.get(key)
            if rec is None:
                continue
            mine = curve["points"][tau_label(tau)]
            for col, val in (
                ("v3_separation_share", mine["v3_separation_share"]),
                ("false_block_rate", mine["false_block_rate"]),
                ("schema_feas_false_block_floor", curve["floor"]),
                ("v3_items", float(mine["v3_items"])),
                ("v3_separated", float(mine["v3_separated"])),
            ):
                want = rec.get(col, "")
                if want == "":
                    continue
                checked += 1
                if abs(float(want) - float(val)) > 5e-7:
                    mismatches.append((key, col, want, val))
            want_op = rec.get("operating_point_fb5pct", "")
            checked += 1
            got_op = curve["operating_tau_fb5"]
            if want_op == "":
                if got_op is not None:
                    mismatches.append((key, "operating_point_fb5pct", "", got_op))
            else:
                if got_op is None or abs(float(want_op) - got_op) > 1e-9:
                    mismatches.append((key, "operating_point_fb5pct", want_op, got_op))
    return {"cells_checked": checked, "mismatches": mismatches[:10],
            "n_mismatch": len(mismatches),
            "source": str(t6.relative_to(ROOT)), "sha256": sha256(t6)}


# --------------------------------------------------------------------------- #
# The new numbers                                                              #
# --------------------------------------------------------------------------- #
FILTERS = OrderedDict()
FILTERS["all_e1_certificates"] = dict(
    label="every E1 certificate (8 arms, both modes, both thinking settings, "
          "infra rows kept)",
    fn=lambda r: True,
)
FILTERS["all_modes_noinfra"] = dict(
    label="both modes, infra rows dropped, all ten arm configurations",
    fn=lambda r: not r["cert_infra"],
)
FILTERS["constrained_all_arms"] = dict(
    label="constrained mode, all ten arm configurations, infra rows kept",
    fn=lambda r: r["mode"] == "M_constrained",
)
FILTERS["constrained_all_arms_noinfra"] = dict(
    label="constrained mode, all ten arm configurations, infra rows dropped "
          "(THE REPORTED SCOPE)",
    fn=lambda r: r["mode"] == "M_constrained" and not r["cert_infra"],
)
FILTERS["capability_constrained_noinfra"] = dict(
    label="constrained mode, capability set (DeepSeek's two rows excluded), "
          "infra rows dropped",
    fn=lambda r: (r["mode"] == "M_constrained" and not r["cert_infra"]
                  and (r["arm"], r["thinking"]) in CAPABILITY_ROWS),
)
FILTERS["free_all_arms_noinfra"] = dict(
    label="free mode, all arm configurations, infra rows dropped",
    fn=lambda r: r["mode"] == "M_free" and not r["cert_infra"],
)
FILTERS["accepted_only"] = dict(
    label="certificates the guard accepted at tau = 0.20, constrained mode, "
          "infra rows dropped",
    fn=lambda r: (r["mode"] == "M_constrained" and not r["cert_infra"]
                  and r["cert_terminal"] == APPLIED_WITH_CERTIFICATE),
)

REPORTED = "constrained_all_arms_noinfra"


def critical_ell_table8(rows: list, keep) -> dict:
    """Smallest ell that moves a cell PUBLISHED IN TABLE 8, exactly.

    Table 8's six columns are functions of only two (row, tolerance) families:
    benign rows at every swept tolerance (the false-block column, the floor,
    and the operating point), and feasibility-passed V3 rows at the three
    printed tolerances 0.05, 0.20 and 0.50 (the separation columns).  A flip
    anywhere else moves the underlying sweep artifact but no printed cell.
    """
    best = None
    witness = None
    for r in rows:
        if r["gap"] is None or not keep(r):
            continue
        if r["mode"] != "M_constrained":
            continue
        cls = r["primary_class"]
        if cls == BENIGN and not r["cert_infra"]:
            taus = TAU_GRID
        elif (cls == "V3" and not r["cert_infra"] and not r["feas_infra"]
              and r["feas_terminal"] in APPLIED_STATES):
            taus = (0.05, 0.20, 0.50)
        else:
            continue
        obj, lb = r["obj_bh"], r["lb_bh"]
        for tau in taus:
            if certified_gap(obj, lb, 1.0) > tau:
                need = (obj - lb) / tau
                if need > max(lb, 1.0) and (best is None or need < best):
                    best = need
                    witness = {"item_id": r["item_id"], "arm": r["arm"],
                               "class": cls, "tau": tau, "obj_bh": obj,
                               "lb_bh": lb}
    return {"smallest_ell_that_moves_a_published_table8_cell": best,
            "witness": witness}


def critical_ell(rows: list, keep, taus=TAU_GRID) -> dict:
    """The exact ell at which the first accept-or-block decision changes.

    The gap is non-increasing in ell (the denominator max(LB, ell) is
    non-decreasing), so a decision can only move from blocked to accepted as ell
    grows.  A row blocked at floor ell = 1 under tolerance tau becomes accepted
    exactly when ell >= (obj - LB) / tau, provided that value exceeds max(LB, 1).
    Below ell = 1 the only rows whose gap can move are those with LB < 1, and in
    this corpus every one of them has LB = 0 exactly; each either has obj = 0
    (gap = 0 at every ell) or obj large enough that no grid tolerance accepts it,
    so nothing flips downward.  Both directions are checked numerically here
    rather than assumed.
    """
    sel = [r for r in rows if r["gap"] is not None and keep(r)]
    best_up = None
    best_up_at = None
    down_flip_possible = []
    for r in sel:
        obj, lb = r["obj_bh"], r["lb_bh"]
        for tau in taus:
            gap1 = certified_gap(obj, lb, 1.0)
            if gap1 > tau:
                # blocked at ell = 1; flips to accepted at ell >= (obj-LB)/tau
                need = (obj - lb) / tau if tau > 0 else float("inf")
                if need > max(lb, 1.0):
                    if best_up is None or need < best_up:
                        best_up = need
                        best_up_at = {"item_id": r["item_id"], "arm": r["arm"],
                                      "tau": tau, "obj_bh": obj, "lb_bh": lb}
            else:
                # accepted at ell = 1; can only flip if the denominator SHRINKS,
                # which needs ell < 1 and LB < 1.
                if lb < 1.0 and obj > lb:
                    down_flip_possible.append((r["item_id"], tau, obj, lb))
    return {
        "smallest_ell_above_one_that_flips_any_decision": best_up,
        "witness": best_up_at,
        "n_rows_that_could_flip_below_ell_one": len(down_flip_possible),
        "examples_below": down_flip_possible[:3],
    }


def floor_stats(rows: list, keep) -> dict:
    sel = [r for r in rows if r["lb_bh"] is not None and keep(r)]
    n = len(sel)
    lt1 = [r for r in sel if r["lb_bh"] < 1.0]
    eq0 = [r for r in sel if r["lb_bh"] == 0.0]
    strictly_between = [r for r in sel if 0.0 < r["lb_bh"] < 1.0]
    pos = [r["lb_bh"] for r in sel if r["lb_bh"] > 0.0]
    return {
        "n_certificates": n,
        "n_lb_lt_floor": len(lt1),
        "share_lb_lt_floor": (len(lt1) / n) if n else None,
        "n_lb_eq_zero": len(eq0),
        "share_lb_eq_zero": (len(eq0) / n) if n else None,
        "n_lb_strictly_between_zero_and_floor": len(strictly_between),
        "min_positive_lb_bh": min(pos) if pos else None,
        "n_binding_with_obj_zero": sum(1 for r in lt1 if r["obj_bh"] == 0.0),
        "max_obj_among_binding_nonzero": (
            max([r["obj_bh"] for r in lt1 if r["obj_bh"] != 0.0], default=None)),
        "min_obj_among_binding_nonzero": (
            min([r["obj_bh"] for r in lt1 if r["obj_bh"] != 0.0], default=None)),
    }


def ell_flip_counts(rows: list, keep, tau: float = ANCHOR_TAU) -> "OrderedDict":
    """Accept-or-block decisions that differ from the ell = 1 decision."""
    sel = [r for r in rows if r["gap"] is not None and keep(r)]
    base = [terminal_at(r, tau, 1.0) for r in sel]
    out = OrderedDict()
    for ell in ELL_GRID:
        now = [terminal_at(r, tau, ell) for r in sel]
        out["{:g}".format(ell)] = sum(1 for a, b in zip(base, now) if a != b)
    return out, len(sel)


def table8_at_ell(rows: list, ell: float) -> "OrderedDict":
    groups = OrderedDict()
    for r in rows:
        if r["mode"] != "M_constrained":
            continue
        groups.setdefault((r["arm"], r["thinking"]), []).append(r)
    out = OrderedDict()
    for key in CONSTRAINED_ROWS:
        grp = groups.get(key)
        if grp is None:
            continue
        c = group_curve(grp, ell)
        out[key] = {
            "sep_005": c["points"]["0.05"]["v3_separation_share"],
            "sep_020": c["points"]["0.20"]["v3_separation_share"],
            "sep_050": c["points"]["0.50"]["v3_separation_share"],
            "fb_020": c["points"]["0.20"]["false_block_rate"],
            "floor": c["floor"],
            "operating_tau": c["operating_tau_fb5"],
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-csv", default=str(ANALYSIS / "DG8_floor.csv"))
    args = ap.parse_args()

    print("[{}] loading E1 verdict logs ...".format(VERSION), file=sys.stderr)
    rows, hashes = load_rows()
    print("  {} joined G_CERT rows".format(len(rows)), file=sys.stderr)

    # ---------------- self-check 1 ---------------------------------------- #
    sc1 = selfcheck_gap_formula(rows)
    print("SELF-CHECK 1  Eq.2 at ell=1 reproduces the logged gap on {} "
          "certificates; mismatches = {}, max |delta| = {}".format(
              sc1["n_certificates"], sc1["n_mismatch"], sc1["max_abs_delta"]),
          file=sys.stderr)
    if sc1["n_mismatch"]:
        print("SELF-CHECK 1 FAILED: {}".format(sc1["examples"]), file=sys.stderr)
        return 1

    # ---------------- self-check 2 ---------------------------------------- #
    sc2 = selfcheck_table8(rows)
    print("SELF-CHECK 2  reproduced {} published Table 8 / T6 cells from the raw "
          "logs; mismatches = {}".format(sc2["cells_checked"], sc2["n_mismatch"]),
          file=sys.stderr)
    if sc2["n_mismatch"]:
        print("SELF-CHECK 2 FAILED: {}".format(sc2["mismatches"]), file=sys.stderr)
        return 1

    # ---------------- reconcile the two verification filters --------------- #
    # The two passes differed on three axes: mode, DeepSeek, and infra rows.
    # The infra axis turns out to be vacuous on this population, and saying so
    # is what collapses the disagreement to one real choice (mode + DeepSeek).
    n_cert_rows = sum(1 for r in rows if r["lb_bh"] is not None)
    n_cert_infra = sum(1 for r in rows if r["lb_bh"] is not None and r["cert_infra"])
    n_rows_infra = sum(1 for r in rows if r["cert_infra"])
    print("RECONCILIATION  {} of {} certificate-carrying rows also carry an "
          "infra_error finding ({} infra rows overall, none of which certified)"
          .format(n_cert_infra, n_cert_rows, n_rows_infra), file=sys.stderr)

    # ---------------- floor shares under every scope ---------------------- #
    scopes = OrderedDict()
    for name, spec in FILTERS.items():
        scopes[name] = floor_stats(rows, spec["fn"])

    keep = FILTERS[REPORTED]["fn"]

    # ---------------- per-stratum split, every scope ----------------------- #
    strata_by_scope = OrderedDict()
    for name, spec in FILTERS.items():
        st = OrderedDict()
        for r in rows:
            if r["lb_bh"] is None or not spec["fn"](r):
                continue
            s = st.setdefault(r["stratum"], {"n": 0, "binding": 0})
            s["n"] += 1
            if r["lb_bh"] < 1.0:
                s["binding"] += 1
        strata_by_scope[name] = OrderedDict(sorted(st.items()))
    strata = strata_by_scope[REPORTED]

    # ---------------- per-arm split (reported scope) ---------------------- #
    per_arm = OrderedDict()
    for r in rows:
        if r["lb_bh"] is None or not keep(r):
            continue
        k = (r["arm"], r["thinking"])
        a = per_arm.setdefault(k, {"n": 0, "binding": 0})
        a["n"] += 1
        if r["lb_bh"] < 1.0:
            a["binding"] += 1
    per_arm = OrderedDict((k, per_arm[k]) for k in CONSTRAINED_ROWS if k in per_arm)

    # ---------------- per-class split of the binding set ------------------ #
    per_class = Counter()
    for r in rows:
        if r["lb_bh"] is None or not keep(r):
            continue
        if r["lb_bh"] < 1.0:
            per_class[r["primary_class"]] += 1

    # ---------------- ell sensitivity ------------------------------------- #
    flips_reported, n_flip_base_reported = ell_flip_counts(rows, keep)
    flips_all, n_flip_base_all = ell_flip_counts(rows, lambda r: True)

    # The exact boundary, not the grid's first hit: at tau = 0.20 alone, and
    # over the whole swept tolerance grid (which is what Table 8 depends on).
    crit_anchor = critical_ell(rows, lambda r: True, taus=(ANCHOR_TAU,))
    crit_grid = critical_ell(rows, lambda r: True, taus=TAU_GRID)
    crit_anchor_reported = critical_ell(rows, keep, taus=(ANCHOR_TAU,))
    crit_grid_constrained = critical_ell(rows, keep, taus=TAU_GRID)
    crit_t8 = critical_ell_table8(rows, lambda r: True)

    # The whole swept artifact, not just Table 8's printed subset: every
    # constrained row's terminal at every tolerance on the grid.
    constrained_rows = [r for r in rows if r["mode"] == "M_constrained"]

    def sweep_fingerprint(ell: float) -> list:
        return [terminal_at(r, tau, ell)
                for r in constrained_rows for tau in TAU_GRID]

    pair_index = [(r, tau) for r in constrained_rows for tau in TAU_GRID]
    base_sweep = sweep_fingerprint(1.0)
    sweep_diff = OrderedDict()
    sweep_diff_detail = OrderedDict()
    for ell in ELL_GRID:
        now = sweep_fingerprint(ell)
        idx = [i for i, (a, b) in enumerate(zip(base_sweep, now)) if a != b]
        sweep_diff["{:g}".format(ell)] = len(idx)
        sweep_diff_detail["{:g}".format(ell)] = Counter(
            (tau_label(pair_index[i][1]), pair_index[i][0]["primary_class"])
            for i in idx)

    # ---------------- Table 8 identity across ell ------------------------- #
    base_t8 = table8_at_ell(rows, 1.0)
    t8_identical = OrderedDict()
    for ell in ELL_GRID:
        got = table8_at_ell(rows, ell)
        diffs = []
        for key, cells in base_t8.items():
            for col, want in cells.items():
                have = got[key][col]
                if want is None or have is None:
                    if want is not have:
                        diffs.append((key, col, want, have))
                elif abs(float(want) - float(have)) > 5e-7:
                    diffs.append((key, col, want, have))
        t8_identical["{:g}".format(ell)] = {"n_cells_differing": len(diffs),
                                            "examples": diffs[:4]}

    # ---------------- write the CSV --------------------------------------- #
    out = Path(args.out_csv)
    stamp = _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    with out.open("w", newline="") as fh:
        fh.write("# DG8-A. The Eq. 2 gap-denominator floor: binding share and "
                 "ell sensitivity\n")
        fh.write("# generated {} by code/scripts/dg8_floor.py ({})\n".format(
            stamp, VERSION))
        fh.write("# Eq. 2: gap = (obj - LB) / max(LB, ell), ell = 1 weighted "
                 "business hour (manuscript/drafts/s3_formulation.tex:207-219)\n")
        fh.write("# self-check 1: Eq.2 at ell=1 reproduces the logged "
                 "certificate_gap on {} certificates, {} mismatches, max |delta| "
                 "{}\n".format(sc1["n_certificates"], sc1["n_mismatch"],
                               sc1["max_abs_delta"]))
        fh.write("# self-check 2: {} published cells of Table 8 "
                 "(analysis/T6_tau_calibration.csv sha256 {}) reproduced from the "
                 "raw verdict logs, {} mismatches\n".format(
                     sc2["cells_checked"], sc2["sha256"], sc2["n_mismatch"]))
        for path, h in hashes.items():
            fh.write("# {} sha256 {}\n".format(path, h))
        fh.write("# REPORTED SCOPE: {} ({})\n".format(
            REPORTED, FILTERS[REPORTED]["label"]))
        fh.write("# reconciliation: {} of {} certificate-carrying rows carry an "
                 "infra_error finding, so dropping infra rows changes no "
                 "certificate count; the two verification filters differ only in "
                 "mode and in whether DeepSeek's two constrained rows are kept\n"
                 .format(n_cert_infra, n_cert_rows))
        w = csv.writer(fh)
        w.writerow(["section", "key", "label", "n", "binding", "share", "note"])

        for name, st in scopes.items():
            w.writerow(["scope", name, FILTERS[name]["label"],
                        st["n_certificates"], st["n_lb_lt_floor"],
                        "" if st["share_lb_lt_floor"] is None
                        else "{:.6f}".format(st["share_lb_lt_floor"]),
                        "LB==0 on {} of them; {} certificates have 0<LB<1; "
                        "min positive LB {} bh".format(
                            st["n_lb_eq_zero"],
                            st["n_lb_strictly_between_zero_and_floor"],
                            st["min_positive_lb_bh"])])

        for scope_name, st in strata_by_scope.items():
            for stratum, s in st.items():
                w.writerow(["stratum", "{} | {}".format(scope_name, stratum),
                            FILTERS[scope_name]["label"], s["n"], s["binding"],
                            "{:.6f}".format(s["binding"] / s["n"]),
                            "REPORTED SCOPE" if scope_name == REPORTED else ""])

        for (arm, thinking), a in per_arm.items():
            w.writerow(["arm", "{} / {}".format(arm, thinking), "reported scope",
                        a["n"], a["binding"],
                        "{:.6f}".format(a["binding"] / a["n"]), ""])

        for cls in CLASSES:
            w.writerow(["binding_by_class", cls, "reported scope", "",
                        per_class.get(cls, 0), "",
                        "count of floor-binding certificates in this class"])

        st = scopes[REPORTED]
        w.writerow(["binding_composition", "obj_eq_zero", "reported scope", "",
                    st["n_binding_with_obj_zero"], "",
                    "gap = 0 at every ell"])
        w.writerow(["binding_composition", "obj_gt_zero", "reported scope", "",
                    st["n_lb_lt_floor"] - st["n_binding_with_obj_zero"], "",
                    "obj range {} to {} bh".format(
                        st["min_obj_among_binding_nonzero"],
                        st["max_obj_among_binding_nonzero"])])

        for ell, k in flips_reported.items():
            w.writerow(["ell_flips_reported_scope", ell,
                        "decisions differing from ell=1 at tau=0.20",
                        n_flip_base_reported, k,
                        "{:.6f}".format(k / n_flip_base_reported), ""])
        for ell, k in flips_all.items():
            w.writerow(["ell_flips_all_e1_certificates", ell,
                        "decisions differing from ell=1 at tau=0.20",
                        n_flip_base_all, k,
                        "{:.6f}".format(k / n_flip_base_all), ""])
        for ell, d in t8_identical.items():
            w.writerow(["table8_cells_differing_from_ell_1", ell,
                        "60 cells = 10 arm configurations x 6 published columns",
                        60, d["n_cells_differing"], "",
                        "" if not d["examples"] else repr(d["examples"])])

        for ell, k in sweep_diff.items():
            w.writerow(["full_sweep_row_tolerance_pairs_differing", ell,
                        "constrained rows x 8 swept tolerances; the whole T6 "
                        "artifact and Fig. 4, not only Table 8's printed cells",
                        len(base_sweep), k, "{:.8f}".format(k / len(base_sweep)),
                        "by (tolerance, class): {}".format(
                            dict(sweep_diff_detail[ell])) if k else ""])

        w.writerow(["critical_ell", "published_table8_cells",
                    "smallest ell that moves any PRINTED Table 8 cell", "",
                    crit_t8["smallest_ell_that_moves_a_published_table8_cell"],
                    "", "witness {}".format(crit_t8["witness"])])

        for key, crit, note in (
            ("tau_0.20_all_e1", crit_anchor, "all 33,404 E1 certificates"),
            ("tau_0.20_reported_scope", crit_anchor_reported, "reported scope"),
            ("tau_grid_all_e1", crit_grid,
             "smallest ell that moves ANY decision anywhere on the swept "
             "tolerance grid 0.02-1.00 (the T6 artifact and Fig. 4, which "
             "print tolerances Table 8 does not)"),
            ("tau_grid_reported_scope", crit_grid_constrained, "reported scope"),
        ):
            w.writerow(["critical_ell", key, note, "",
                        crit["smallest_ell_above_one_that_flips_any_decision"],
                        "", "witness {}; rows able to flip below ell=1: {}".format(
                            crit["witness"],
                            crit["n_rows_that_could_flip_below_ell_one"])])

    # ---------------- console report --------------------------------------- #
    report = {
        "version": VERSION,
        "self_check_gap_formula": sc1,
        "self_check_table8": {k: v for k, v in sc2.items() if k != "mismatches"},
        "reconciliation": {
            "n_certificate_rows": n_cert_rows,
            "n_certificate_rows_with_infra_finding": n_cert_infra,
            "n_infra_rows_overall": n_rows_infra,
        },
        "scopes": scopes,
        "strata_by_scope": strata_by_scope,
        "per_arm": {"{}/{}".format(*k): v for k, v in per_arm.items()},
        "binding_by_class": dict(per_class),
        "ell_flips_reported_scope": {"denominator": n_flip_base_reported,
                                     "flips": flips_reported},
        "ell_flips_all_e1": {"denominator": n_flip_base_all, "flips": flips_all},
        "table8_cells_differing": {k: v["n_cells_differing"]
                                   for k, v in t8_identical.items()},
        "full_sweep_pairs_differing": {
            "denominator_row_tolerance_pairs": len(base_sweep),
            "differing": sweep_diff,
            "differing_by_tolerance_and_class": {
                k: {"{}|{}".format(*kk): vv for kk, vv in c.items()}
                for k, c in sweep_diff_detail.items() if c}},
        "critical_ell": {
            "published_table8_cells": crit_t8,
            "tau_0.20_all_e1": crit_anchor,
            "tau_0.20_reported_scope": crit_anchor_reported,
            "tau_grid_all_e1": crit_grid,
            "tau_grid_reported_scope": crit_grid_constrained,
        },
    }
    print(json.dumps(report, indent=1, default=str))
    print("wrote {}".format(out), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
