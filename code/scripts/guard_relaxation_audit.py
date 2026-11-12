#!/usr/bin/env python
"""DG12: is guard v0.2 a relaxation of v0.1 on every recorded E3 proposal?

Section 6.3 states that the corrected guard withdraws refusals and adds none,
and that the replay therefore never adjudicates a proposal the model produced
only because the defective rule had refused an earlier one.  Both halves are
claims about every proposal in the logs, so both are measured here rather than
argued from the diff.

METHOD
------
Every recorded E3 proposal (the first final and each revision behind it) is put
through the guard TWICE in one process, on its own instance, its own standing
frozen set and the same ``G_CERT`` configuration the accepted replay uses:
once with the shipped v0.2 frozen-order rule, once with the v0.1 rule restored
verbatim (``_frozen_edit_findings_v01`` below).  The evaluation itself is
``e3_replay._evaluate``, the accepted replay's own function, so this audit
cannot drift from the replay it audits.

The reconstruction is validated before anything is counted: the v0.1 verdict
digest must equal the fingerprint written into ``trajectories.jsonl`` while the
run was live, on every proposal.  A reconstruction that reproduces the live log
byte for byte IS the guard that generated the trajectories; one that does not
is a different guard and its counts would mean nothing.

WHAT IS ASSERTED (the script exits non-zero if any of these fails)
-----------------------------------------------------------------
* the v0.1 reconstruction reproduces all 8,855 live fingerprints;
* v0.1 refuses and v0.2 accepts on 25 proposals;
* v0.2 refuses and v0.1 accepts on 0 -- the relaxation claim itself;
* the replay's chain walk never stops later under v0.2 than under v0.1, which
  is what "no post-divergence proposal is used" means operationally.

OUTPUTS
-------
``analysis/DG12_guard_relaxation.csv``   one row per arm plus an ALL row
``analysis/DG12_guard_relaxation_proposals.jsonl``   the per-proposal dump the
    exposure analysis (``code/scripts/e3_exposure.py``) reads, so the paired
    evaluation runs once rather than once per consumer

Run::

    conda run -n fjsp python code/scripts/guard_relaxation_audit.py --workers 8

Version: l1-dg12-relaxation-1
"""

from __future__ import annotations

import os

# Thread caps before any numeric import: a numerical runtime sizes its pool
# from the machine's core count, not from this process's share of it.
for _var in (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ[_var] = "1"

import argparse  # noqa: E402
import csv  # noqa: E402
import datetime as _dt  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import multiprocessing as mp  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from collections import Counter, OrderedDict  # noqa: E402
from pathlib import Path  # noqa: E402

VERSION = "l1-dg12-relaxation-1"

SCRIPTS_DIR = Path(__file__).resolve().parent
CODE_DIR = SCRIPTS_DIR.parent
ROOT = CODE_DIR.parent
for _p in (str(CODE_DIR), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import e3_replay as e3r  # noqa: E402  (load_trajectories, _proposal_chain, _evaluate)
import l1guard  # noqa: E402
from l1guard import findings as F  # noqa: E402
from l1guard import guard as gmod  # noqa: E402

RESULTS = ROOT / "results"
ANALYSIS = ROOT / "analysis"

#: The six grid logs.  The calibration logs are a different population and the
#: replay excludes them, so they are excluded here too.
ARMS = ["deepseek", "openai", "opus", "qwen14b", "qwen27b", "sonnet"]

#: The counts Section 6.3 states.  They are asserted, not printed: a change in
#: the logs or in the guard must fail this script rather than quietly move a
#: number the manuscript has already published.
EXPECT_PROPOSALS = 8855
EXPECT_FINGERPRINT_MATCHES = 8855
EXPECT_WITHDRAWN = 25
EXPECT_ADDED = 0

_V02_RULE = gmod._frozen_edit_findings


# --------------------------------------------------------------------------- #
# The retired rule                                                             #
# --------------------------------------------------------------------------- #
# Verbatim from release/CertiGATE, ``git show a6594ec^:code/l1guard/guard.py``
# (the pre-fix side of the v0.2 commit; the guard is byte-identical to the tag
# that generated the E3 trajectories everywhere else).  It is copied rather
# than imported because the release repository holds it only in git history,
# and a body reconstructed by hand would be exactly the thing this audit is
# supposed to rule out.  The fidelity check below is what proves the copy is
# the rule that produced the logs.
def _frozen_edit_findings_v01(instance: dict, typed_ops, frozen_seed) -> list:
    """Operations that edit an order frozen at that point in the proposal.

    The frozen set starts as the episode's standing set and evolves with the
    proposal's own ``freeze`` / ``unfreeze``, so a proposal that unfreezes an
    order before editing it is doing the legitimate thing and is not flagged.
    A ``freeze`` of an already-frozen order changes nothing and is not an edit.
    """
    out: list = []
    live = set(frozen_seed or ())
    members_of = {}
    for wo in instance["work_orders"]:
        if wo["building"] is not None:
            members_of.setdefault((wo["building"], wo["trade"]), []).append(wo["id"])

    def flag(i, name, order_id):
        out.append(
            F.make(
                "frozen_order_edit",
                "{} edits work order {!r}, which is frozen at this point in the "
                "proposal".format(name, order_id),
                op_index=i,
                op=name,
                order_id=order_id,
            )
        )

    for i, op in enumerate(typed_ops):
        name = op.op
        if name == "unfreeze":
            live.discard(op.order_id)
            continue
        if name == "freeze":
            live.add(op.order_id)
            continue
        if name == "batch":
            hit = [o for o in members_of.get((op.building_id, op.trade), []) if o in live]
            for order_id in sorted(hit):
                flag(i, name, order_id)
            continue
        if name == "reorder":
            for order_id in (op.order_id, op.ref_order_id):
                if order_id in live:
                    flag(i, name, order_id)
            continue
        if op.order_id in live:
            flag(i, name, op.order_id)
    return out


# --------------------------------------------------------------------------- #
# Worker side                                                                  #
# --------------------------------------------------------------------------- #
_ROWS: list = []


def _init_worker(cores=None):
    if cores:
        try:
            os.sched_setaffinity(0, set(cores))
        except (AttributeError, OSError):
            pass
    # The replay's own worker state: one InstanceCache and the accepted guard
    # configurations.  Sharing it is what makes _evaluate here identical to
    # _evaluate in the replay.
    e3r._init_worker()


def _snapshot(verdict) -> dict:
    return {
        "blocked": bool(verdict.blocked),
        "accepted": bool(verdict.accepted),
        "terminal": verdict.terminal,
        "stage_reached": verdict.stage_reached,
        "blocking_codes": sorted({f.code for f in verdict.findings if f.blocking}),
        "fingerprint": verdict.digest(),
        "n_ops": None if verdict.ops is None else len(verdict.ops),
    }


def _one(index: int) -> dict:
    """Both guards on every proposal of one trajectory, in recorded order."""
    row = _ROWS[index]
    cert = e3r._STATE["cfgs"]["G_CERT"]
    chain = e3r._proposal_chain(row)
    logged = row.get("guard_chain") or []
    if logged and len(logged) != len(chain):
        raise SystemExit(
            "REFUSING TO RUN: trajectory {} logs {} guard_chain entries for {} "
            "recorded proposals; the per-proposal join would be off by one."
            .format(row["item_id"], len(logged), len(chain)))
    props = []
    for idx, link in enumerate(chain):
        gmod._frozen_edit_findings = _V02_RULE
        v02 = _snapshot(e3r._evaluate(row, link["raw"], cert))
        gmod._frozen_edit_findings = _frozen_edit_findings_v01
        v01 = _snapshot(e3r._evaluate(row, link["raw"], cert))
        gmod._frozen_edit_findings = _V02_RULE
        log = logged[idx] if idx < len(logged) else None
        props.append({
            "prop_index": idx,
            "source": link["source"],
            "logged_fingerprint": (log or {}).get("fingerprint"),
            "logged_blocked": (log or {}).get("blocked"),
            "v01": v01,
            "v02": v02,
        })

    def stop(key):
        """The proposal the replay adjudicates: the first one not blocked."""
        u = 0
        while props[u][key]["blocked"] and u + 1 < len(props):
            u += 1
        return u

    return {
        "arm": row["arm"], "budget_level": row["budget_level"],
        "pipeline": row["pipeline"], "repeat": int(row["repeat"]),
        "item_id": row["item_id"], "primary_class": row["primary_class"],
        "subclass": row.get("subclass"),
        "n_chain": len(props),
        "n_revisions": len(row.get("revisions") or []),
        "stop_v01": stop("v01"), "stop_v02": stop("v02"),
        "props": props,
    }


def _chunk(indices: list) -> list:
    return [_one(i) for i in indices]


# --------------------------------------------------------------------------- #
# Aggregation                                                                  #
# --------------------------------------------------------------------------- #
def _tally(trajectories: list) -> "OrderedDict[str, dict]":
    """Per-arm and pooled counts of the four per-proposal transitions."""
    scopes = OrderedDict((a, _empty_tally()) for a in ARMS)
    scopes["ALL"] = _empty_tally()
    for t in trajectories:
        for scope in (t["arm"], "ALL"):
            s = scopes[scope]
            s["trajectories"] += 1
            s["recorded_revision_rounds"] += t["n_revisions"]
            if t["stop_v02"] < t["stop_v01"]:
                s["stop_index_earlier"] += 1
            elif t["stop_v02"] > t["stop_v01"]:
                s["stop_index_later"] += 1
            else:
                s["stop_index_same"] += 1
            for p in t["props"]:
                s["total_proposals"] += 1
                if p["logged_fingerprint"] is not None:
                    s["logged_fingerprints"] += 1
                    if p["logged_fingerprint"] == p["v01"]["fingerprint"]:
                        s["fingerprint_matches"] += 1
                    if p["logged_fingerprint"] != p["v02"]["fingerprint"]:
                        s["v02_differs_from_log"] += 1
                a, b = p["v01"]["blocked"], p["v02"]["blocked"]
                if a and not b:
                    s["withdrawn_refusals"] += 1
                    s["withdrawn_first_final" if p["source"] == "first_final"
                      else "withdrawn_revision"] += 1
                elif b and not a:
                    s["added_refusals"] += 1
                elif a and b:
                    s["unchanged_refused"] += 1
                    if p["v01"]["blocking_codes"] != p["v02"]["blocking_codes"]:
                        s["refused_both_codes_dropped"] += 1
                else:
                    s["unchanged_accepted"] += 1
    return scopes


def _empty_tally() -> dict:
    return dict.fromkeys((
        "trajectories", "total_proposals", "recorded_revision_rounds",
        "logged_fingerprints", "fingerprint_matches", "v02_differs_from_log",
        "withdrawn_refusals", "added_refusals", "unchanged_refused",
        "unchanged_accepted", "withdrawn_first_final", "withdrawn_revision",
        "refused_both_codes_dropped", "stop_index_same", "stop_index_earlier",
        "stop_index_later"), 0)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_cores(text):
    if not text:
        return None
    cores = set()
    for part in str(text).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            cores.update(range(int(lo), int(hi) + 1))
        else:
            cores.add(int(part))
    return sorted(cores) or None


# --------------------------------------------------------------------------- #
# main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--cores", default="", help="CPU affinity, e.g. 0-7")
    ap.add_argument("--out-csv", default=str(ANALYSIS / "DG12_guard_relaxation.csv"))
    ap.add_argument("--out-jsonl",
                    default=str(ANALYSIS / "DG12_guard_relaxation_proposals.jsonl"))
    args = ap.parse_args()

    if l1guard.__version__ != "0.2.0":
        raise SystemExit(
            "REFUSING TO RUN: this audit compares the shipped guard against the "
            "retired rule, and the shipped guard is version {}, not 0.2.0."
            .format(l1guard.__version__))

    cores = parse_cores(args.cores)
    if cores:
        try:
            os.sched_setaffinity(0, set(cores))
        except (AttributeError, OSError):
            pass

    paths = [RESULTS / ("e3_" + arm) / "trajectories.jsonl" for arm in ARMS]
    hashes = OrderedDict()
    for p in paths + [CODE_DIR / "l1guard" / "guard.py"]:
        hashes[str(p.relative_to(ROOT))] = sha256(p)

    global _ROWS
    _ROWS, stats = e3r.load_trajectories([str(p) for p in paths])
    print("trajectories: {}".format(json.dumps(stats)), file=sys.stderr)

    started = time.time()
    tasks = [list(range(len(_ROWS)))[i::args.workers * 4]
             for i in range(args.workers * 4)]
    if args.workers <= 1:
        _init_worker(cores)
        chunks = [_chunk(t) for t in tasks]
    else:
        ctx = mp.get_context("fork")
        with ctx.Pool(processes=args.workers, initializer=_init_worker,
                      initargs=(cores,)) as pool:
            chunks = pool.map(_chunk, tasks, chunksize=1)
    trajectories = [t for chunk in chunks for t in chunk]
    trajectories.sort(key=lambda t: (t["arm"], t["budget_level"], t["pipeline"],
                                     t["repeat"], t["item_id"]))
    wall = time.time() - started
    print("evaluated {} trajectories in {:.1f}s".format(len(trajectories), wall),
          file=sys.stderr)

    scopes = _tally(trajectories)
    allrow = scopes["ALL"]

    # ------------------------------------------------------------------ #
    # Assertions.  Every one of them is a sentence the manuscript prints.  #
    # ------------------------------------------------------------------ #
    checks, failures = [], []

    def check(what, expected, got):
        checks.append(what)
        if expected != got:
            failures.append("{}: expected {}, got {}".format(what, expected, got))

    check("recorded proposals", EXPECT_PROPOSALS, allrow["total_proposals"])
    check("proposals carrying a live fingerprint", EXPECT_FINGERPRINT_MATCHES,
          allrow["logged_fingerprints"])
    check("v0.1 reconstruction reproduces the live fingerprint",
          EXPECT_FINGERPRINT_MATCHES, allrow["fingerprint_matches"])
    check("refusals v0.2 withdraws", EXPECT_WITHDRAWN, allrow["withdrawn_refusals"])
    check("refusals v0.2 adds", EXPECT_ADDED, allrow["added_refusals"])
    check("trajectories whose adjudicated proposal moves later under v0.2",
          0, allrow["stop_index_later"])
    check("transitions summing to the proposal count", allrow["total_proposals"],
          allrow["withdrawn_refusals"] + allrow["added_refusals"]
          + allrow["unchanged_refused"] + allrow["unchanged_accepted"])
    if failures:
        for f in failures:
            print("ASSERTION FAILED  " + f, file=sys.stderr)
        return 2

    # ------------------------------------------------------------------ #
    # Outputs                                                             #
    # ------------------------------------------------------------------ #
    withdrawn = [(t, p) for t in trajectories for p in t["props"]
                 if p["v01"]["blocked"] and not p["v02"]["blocked"]]
    by_codes = Counter(tuple(p["v01"]["blocking_codes"]) for _, p in withdrawn)
    by_class = Counter(t["primary_class"] for t, _ in withdrawn)
    by_subclass = Counter(t["subclass"] for t, _ in withdrawn)

    jsonl = Path(args.out_jsonl)
    with jsonl.open("w", encoding="utf-8") as fh:
        for t in trajectories:
            fh.write(json.dumps(t, sort_keys=True) + "\n")

    stamp = _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    out = Path(args.out_csv)
    with out.open("w", newline="") as fh:
        fh.write("# DG12. Guard v0.2 against guard v0.1 on every recorded E3 "
                 "proposal: what the correction withdrew, and what it added\n")
        fh.write("# generated {} by code/scripts/guard_relaxation_audit.py "
                 "({})\n".format(stamp, VERSION))
        fh.write("# both guards run in one process on the same recorded "
                 "proposal text, instance, standing frozen set and G_CERT "
                 "configuration, through e3_replay._evaluate\n")
        fh.write("# v0.1 rule: release/CertiGATE git show "
                 "a6594ec^:code/l1guard/guard.py, _frozen_edit_findings, "
                 "copied verbatim into this script\n")
        fh.write("# fidelity: the reconstructed v0.1 verdict digest equals the "
                 "fingerprint logged live in trajectories.jsonl on {} of {} "
                 "proposals\n".format(allrow["fingerprint_matches"],
                                      allrow["logged_fingerprints"]))
        fh.write("# withdrawn = refused by v0.1 and not by v0.2; added = the "
                 "reverse, which is the counterexample to the relaxation claim\n")
        fh.write("# stop_index_* compare the proposal the replay adjudicates "
                 "(e3_replay.py:294-305, the first proposal not blocked): "
                 "later would mean the replay needs a proposal v0.1 never "
                 "reached\n")
        fh.write("# per-proposal dump: {}\n".format(
            str(jsonl.relative_to(ROOT))))
        fh.write("# withdrawn refusals by v0.1 blocking-code set: {}\n".format(
            {"+".join(k): v for k, v in by_codes.most_common()}))
        fh.write("# withdrawn refusals by class: {}; by subclass: {}\n".format(
            dict(by_class.most_common()), dict(by_subclass.most_common())))
        for path, h in hashes.items():
            fh.write("# {} sha256 {}\n".format(path, h))
        cols = ["scope", "trajectories", "total_proposals",
                "recorded_revision_rounds", "fingerprint_matches",
                "withdrawn_refusals", "added_refusals", "unchanged_refused",
                "unchanged_accepted", "withdrawn_first_final",
                "withdrawn_revision", "refused_both_codes_dropped",
                "v02_differs_from_log", "stop_index_same",
                "stop_index_earlier", "stop_index_later"]
        w = csv.writer(fh)
        w.writerow(cols)
        for scope in ["ALL"] + ARMS:
            s = scopes[scope]
            w.writerow([scope] + [s[c] for c in cols[1:]])

    print(json.dumps({
        "version": VERSION,
        "trajectories": len(trajectories),
        "proposals": allrow["total_proposals"],
        "fingerprint_matches": allrow["fingerprint_matches"],
        "withdrawn_refusals": allrow["withdrawn_refusals"],
        "added_refusals": allrow["added_refusals"],
        "unchanged_refused": allrow["unchanged_refused"],
        "unchanged_accepted": allrow["unchanged_accepted"],
        "stop_index_later": allrow["stop_index_later"],
        "stop_index_earlier": allrow["stop_index_earlier"],
        "withdrawn_by_class": dict(by_class),
        "withdrawn_by_subclass": dict(by_subclass),
        "wall_s": round(wall, 1),
    }, indent=1))
    print("wrote {} and {}".format(out, jsonl), file=sys.stderr)
    print("all {} assertions passed".format(len(checks)), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
