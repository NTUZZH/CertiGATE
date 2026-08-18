#!/usr/bin/env python
"""DG11: how far the retired guard-v0.1 rule reached into the E3 slice.

Section 6.3 bounds the defect's reach with four quantities: how many of the 240
instructions the two guard versions ever judged differently, how many revision
rounds and tokens the wrongly issued refusals bought, and how much the
published loop statistic moves when those instructions are dropped.  This
script measures all four.

WHAT COUNTS AS EXPOSED
----------------------
An instruction is exposed when at least one of its recorded proposals draws a
different guard verdict under v0.1 and v0.2 -- a different blocked flag, a
different blocking-code set, or a different terminal.  The same set falls out
of the stricter "the verdict digests differ" definition, which is the wording
``analysis/guard_v02_e3_divergence.json`` now records; the two are asserted
equal here rather than assumed, because they are not equal by construction.

Exposure is assigned at ITEM level and pooled over arms: if any arm's
trajectory on an item diverged, that item is dropped from the leave-one-out
recomputation for every arm.  That is the conservative direction.

INPUTS
------
The paired v0.1/v0.2 evaluation is NOT recomputed here.  It is read from
``analysis/DG12_guard_relaxation_proposals.jsonl``, written by
``code/scripts/guard_relaxation_audit.py``, which asserts its own headline
counts; running the guard twice over 8,855 proposals once and reading it twice
is what keeps the two analyses on identical inputs.  Run that script first.

WHAT IS ASSERTED (the script exits non-zero if any of these fails)
-----------------------------------------------------------------
* 8 exposed instructions, 64 exposed trajectories, 64 exposed proposals;
* the digest definition selects the same trajectories as the verdict one;
* 19 revision rounds exist only because of the retired rule, out of 2,135;
* every flipped final verdict of ``guard_v02_e3_divergence.json`` sits on an
  exposed trajectory;
* the leave-one-out loop statistic runs 1.77 to 2.00 over the five arms
  outside the DeepSeek wire artifact;
* the all-items loop statistic of every E7 cell is reproduced exactly.

OUTPUTS
-------
``analysis/DG11_e3_exposure.csv``          the measurements
``analysis/guard_v02_e3_divergence.json``  repaired in place: its
    ``contaminated_trajectories`` field recorded 288, which no definition in
    this repository reproduces and which no script regenerates.  This script
    replaces it with the 64 it measures, states the definition in a sibling
    key, and rewrites ``contaminated_per_arm`` from the same measurement.
    Every other key keeps its recorded value.

Run::

    conda run -n fjsp python code/scripts/e3_exposure.py

Version: l1-dg11-exposure-1
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import json
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

VERSION = "l1-dg11-exposure-1"

SCRIPTS_DIR = Path(__file__).resolve().parent
CODE_DIR = SCRIPTS_DIR.parent
ROOT = CODE_DIR.parent
for _p in (str(CODE_DIR), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import e3_replay as e3r  # noqa: E402  (load_trajectories, traj_key: the accepted dedup)

RESULTS = ROOT / "results"
ANALYSIS = ROOT / "analysis"

ARMS = ["deepseek", "openai", "opus", "qwen14b", "qwen27b", "sonnet"]

#: The cell the published loop statistic reports, and the arm its own note
#: excludes: DeepSeek's unguarded cells are the lenient-repair / empty-list
#: wire artifact, not a model behaviour (decisions.md 2026-08-13, E3 ruling 2).
LOO_BUDGET = "loose"
LOO_VARIANT = "SINGLE+G"
LOO_ARMS = [a for a in ARMS if a != "deepseek"]

GUARDED = {"SINGLE": "SINGLE+G", "MULTI": "MULTI-G"}

#: The counts Section 6.3 prints.  A change in the logs must fail this script
#: rather than move a published number quietly.
EXPECT_ITEMS = 8
EXPECT_TRAJECTORIES = 64
EXPECT_PROPOSALS = 64
EXPECT_SPURIOUS_ROUNDS = 19
EXPECT_LOO_MIN = "1.77"
EXPECT_LOO_MAX = "2.00"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verdict_diverges(prop: dict) -> bool:
    """The guard's answer on this proposal differs between the two versions."""
    a, b = prop["v01"], prop["v02"]
    return (a["blocked"] != b["blocked"]
            or a["blocking_codes"] != b["blocking_codes"]
            or a["terminal"] != b["terminal"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--paired",
                    default=str(ANALYSIS / "DG12_guard_relaxation_proposals.jsonl"))
    ap.add_argument("--out-csv", default=str(ANALYSIS / "DG11_e3_exposure.csv"))
    ap.add_argument("--divergence",
                    default=str(ANALYSIS / "guard_v02_e3_divergence.json"))
    args = ap.parse_args()

    paired_path = Path(args.paired)
    if not paired_path.is_file():
        raise SystemExit(
            "REFUSING TO RUN: {} does not exist. Run "
            "code/scripts/guard_relaxation_audit.py first; this script never "
            "re-derives the paired evaluation, so the two analyses cannot "
            "diverge.".format(paired_path))

    # ------------------------------------------------------------------ #
    # Inputs                                                              #
    # ------------------------------------------------------------------ #
    paired = [json.loads(line) for line in paired_path.open() if line.strip()]

    traj_paths = [RESULTS / ("e3_" + a) / "trajectories.jsonl" for a in ARMS]
    rows, stats = e3r.load_trajectories([str(p) for p in traj_paths])
    trajectories = {e3r.traj_key(r): r for r in rows}
    if len(paired) != len(trajectories):
        raise SystemExit(
            "REFUSING TO RUN: the paired dump carries {} trajectories and the "
            "logs carry {}; they are not the same population."
            .format(len(paired), len(trajectories)))

    calls = defaultdict(list)
    for arm in ARMS:
        with (RESULTS / ("e3_" + arm) / "calls.jsonl").open() as fh:
            for line in fh:
                c = json.loads(line)
                calls[c["run_uid"]].append(c)

    verdicts = defaultdict(dict)
    for arm in ARMS:
        with (RESULTS / ("e3_replay_" + arm) / "verdicts.jsonl").open() as fh:
            for line in fh:
                v = json.loads(line)
                key = (v["arm"], v["budget_level"], v["pipeline"],
                       int(v["repeat"]), v["item_id"])
                verdicts[key][v["variant"]] = v

    with (ANALYSIS / "E7_e3_profiles.csv").open() as fh:
        e7 = {(r["arm"], r["budget_level"], r["variant"]): r
              for r in csv.DictReader(l for l in fh if not l.startswith("#"))}

    # ------------------------------------------------------------------ #
    # (a) exposure                                                        #
    # ------------------------------------------------------------------ #
    exposed_traj, digest_traj = set(), set()
    exposed_items, exposed_props = set(), 0
    exposed_traj_per_arm = defaultdict(int)
    exposed_items_per_arm = defaultdict(set)
    withdrawn_stop = {}          # trajectory -> first proposal v0.2 accepts
    total_props = total_rounds = 0
    for t in paired:
        key = (t["arm"], t["budget_level"], t["pipeline"], t["repeat"],
               t["item_id"])
        total_props += len(t["props"])
        total_rounds += t["n_revisions"]
        hit = digest_hit = False
        for p in t["props"]:
            if verdict_diverges(p):
                hit = True
                exposed_props += 1
            if p["v01"]["fingerprint"] != p["v02"]["fingerprint"]:
                digest_hit = True
            if p["v01"]["blocked"] and not p["v02"]["blocked"]:
                withdrawn_stop[key] = min(withdrawn_stop.get(key, 1 << 30),
                                          p["prop_index"])
        if hit:
            exposed_traj.add(key)
            exposed_items.add(t["item_id"])
            exposed_traj_per_arm[t["arm"]] += 1
            exposed_items_per_arm[t["arm"]].add(t["item_id"])
        if digest_hit:
            digest_traj.add(key)

    # ------------------------------------------------------------------ #
    # (b) the loop the retired rule bought                                #
    # ------------------------------------------------------------------ #
    # The correction only withdraws refusals, so on a trajectory whose stop
    # moves earlier every later round exists only because of the retired rule,
    # and every token charged at or after the call that produced the next
    # proposal is spend the corrected guard would not have incurred.
    spurious_rounds = spurious_tokens = 0
    spurious_per_arm = defaultdict(int)
    for key, stop in withdrawn_stop.items():
        row = trajectories[key]
        revs = row.get("revisions") or []
        if stop >= len(revs):
            continue
        call_index = revs[stop]["call_index"]
        spurious_rounds += len(revs) - stop
        spend = sum(c["charged"]["charged"] for c in calls[row["run_uid"]]
                    if c["call_index"] >= call_index)
        spurious_tokens += spend
        spurious_per_arm[key[0]] += spend
    all_tokens = sum(r["tokens"]["all"] for r in trajectories.values())

    # ------------------------------------------------------------------ #
    # (c) leave-one-out on the published loop statistic                   #
    # ------------------------------------------------------------------ #
    def ppa(cells: list):
        """Proposals per accepted adjustment, exactly as e3_analyze computes it."""
        accepted = [c for c in cells if c["accepted"]]
        if not accepted:
            return None
        return sum(c["proposals"] for c in cells) / len(accepted)

    cells = defaultdict(list)
    for key, row in trajectories.items():
        arm, budget, pipeline, repeat, item = key
        v = verdicts.get(key, {}).get(GUARDED[pipeline])
        if v is None:
            raise SystemExit(
                "REFUSING TO RUN: no {} replay verdict for {}".format(
                    GUARDED[pipeline], key))
        cells[(arm, budget, GUARDED[pipeline])].append({
            "item": item,
            "proposals": v["proposals_guarded"],
            "accepted": v["terminal"] == "applied_with_certificate",
            "exposed": item in exposed_items,
        })

    e7_checked = e7_bad = 0
    for cell_key, recs in sorted(cells.items()):
        published = e7.get(cell_key)
        if published is None:
            continue
        want = published["proposals_per_accepted_adjustment"]
        got = ppa(recs)
        e7_checked += 1
        if want == "":
            if got is not None:
                e7_bad += 1
            continue
        if got is None or abs(float(want) - got) > 5e-3:
            e7_bad += 1
            print("E7 MISMATCH {}: published {} recomputed {}".format(
                cell_key, want, got), file=sys.stderr)

    loo = OrderedDict()
    for arm in ARMS:
        recs = cells[(arm, LOO_BUDGET, LOO_VARIANT)]
        loo[arm] = (ppa(recs), ppa([r for r in recs if not r["exposed"]]))
    loo_dropped = [loo[a][1] for a in LOO_ARMS]

    # ------------------------------------------------------------------ #
    # (d) the flips the released artifact records                         #
    # ------------------------------------------------------------------ #
    div_path = Path(args.divergence)
    divergence = json.loads(div_path.read_text(), object_pairs_hook=OrderedDict)
    flip_keys = {(f["arm"], f["budget_level"], f["architecture"],
                  int(f["repeat"]), f["item_id"]) for f in divergence["flips"]}
    flips_outside = sorted(k for k in flip_keys if k not in exposed_traj)

    # ------------------------------------------------------------------ #
    # Assertions                                                          #
    # ------------------------------------------------------------------ #
    checks, failures = [], []

    def check(what, expected, got):
        checks.append(what)
        if expected != got:
            failures.append("{}: expected {!r}, got {!r}".format(
                what, expected, got))

    check("exposed instructions", EXPECT_ITEMS, len(exposed_items))
    check("exposed trajectories", EXPECT_TRAJECTORIES, len(exposed_traj))
    check("exposed proposals", EXPECT_PROPOSALS, exposed_props)
    check("the digest definition selects the same trajectories",
          exposed_traj, digest_traj)
    check("recorded revision rounds", total_props - len(paired), total_rounds)
    check("revision rounds the retired rule bought", EXPECT_SPURIOUS_ROUNDS,
          spurious_rounds)
    check("flipped final verdicts sitting outside the exposed set", [],
          flips_outside)
    check("E7 loop statistics reproduced", 0, e7_bad)
    check("leave-one-out minimum over the five arms", EXPECT_LOO_MIN,
          "{:.2f}".format(min(loo_dropped)))
    check("leave-one-out maximum over the five arms", EXPECT_LOO_MAX,
          "{:.2f}".format(max(loo_dropped)))
    if failures:
        for f in failures:
            print("ASSERTION FAILED  " + f, file=sys.stderr)
        return 2

    # ------------------------------------------------------------------ #
    # Repair the divergence artifact                                      #
    # ------------------------------------------------------------------ #
    before = div_path.read_text()
    old_total = divergence["contaminated_trajectories"]
    old_per_arm = dict(divergence["contaminated_per_arm"])
    divergence["contaminated_trajectories"] = len(exposed_traj)
    divergence["contaminated_definition"] = (
        "trajectories with at least one recorded proposal whose guard v0.1 and "
        "v0.2 verdict digests differ")
    # The quoted ruling predates the repair and mentions the retired 288
    # figure; the ruling text itself is a historical record and stays.
    divergence["ruling_note"] = (
        "the 288 in the quoted ruling was an earlier count that does not "
        "reproduce under any definition tried; the corrected count is "
        "contaminated_trajectories under contaminated_definition, and the 16 "
        "flips all sit inside that set")
    divergence["contaminated_per_arm"] = OrderedDict(
        (a, exposed_traj_per_arm[a]) for a in sorted(ARMS))
    after = json.dumps(divergence, indent=1, sort_keys=True) + "\n"
    div_path.write_text(after)
    print("--- {} (repaired)".format(div_path.relative_to(ROOT)))
    print("  contaminated_trajectories  {} -> {}".format(
        old_total, len(exposed_traj)))
    print("  contaminated_per_arm       {} -> {}".format(
        old_per_arm, dict(divergence["contaminated_per_arm"])))
    print("  contaminated_definition    (absent) -> {!r}".format(
        divergence["contaminated_definition"]))
    unchanged = [k for k in divergence
                 if k not in ("contaminated_trajectories",
                              "contaminated_per_arm", "contaminated_definition",
                              "ruling_note")]
    old = json.loads(before, object_pairs_hook=OrderedDict)
    same = [k for k in unchanged
            if json.dumps(old[k], sort_keys=True)
            == json.dumps(divergence[k], sort_keys=True)]
    print("  unchanged keys ({}/{}): {}".format(
        len(same), len(unchanged), ", ".join(unchanged)))
    if len(same) != len(unchanged):
        raise SystemExit("REFUSING TO FINISH: the repair moved a key it must "
                         "not touch")

    # ------------------------------------------------------------------ #
    # Output                                                              #
    # ------------------------------------------------------------------ #
    hashes = OrderedDict()
    for p in [paired_path] + traj_paths:
        hashes[str(p.relative_to(ROOT))] = sha256(p)
    for arm in ARMS:
        for name in ("calls.jsonl",):
            p = RESULTS / ("e3_" + arm) / name
            hashes[str(p.relative_to(ROOT))] = sha256(p)
        p = RESULTS / ("e3_replay_" + arm) / "verdicts.jsonl"
        hashes[str(p.relative_to(ROOT))] = sha256(p)
    hashes["analysis/E7_e3_profiles.csv"] = sha256(ANALYSIS / "E7_e3_profiles.csv")

    def share(a, b):
        return "" if not b else "{:.6f}".format(a / b)

    stamp = _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    out = Path(args.out_csv)
    with out.open("w", newline="") as fh:
        fh.write("# DG11. The reach of the retired guard-v0.1 frozen-order "
                 "rule in the 240-instruction E3 slice\n")
        fh.write("# generated {} by code/scripts/e3_exposure.py ({})\n".format(
            stamp, VERSION))
        fh.write("# exposed = at least one recorded proposal whose v0.1 and "
                 "v0.2 guard verdict differ (blocked flag, blocking codes or "
                 "terminal); the digest definition selects the same set\n")
        fh.write("# exposure is assigned per item and pooled over arms: an "
                 "item exposed in any arm is dropped for every arm in the "
                 "leave-one-out\n")
        fh.write("# the paired v0.1/v0.2 evaluation is read from "
                 "analysis/DG12_guard_relaxation_proposals.jsonl, not "
                 "recomputed\n")
        fh.write("# spurious rounds and tokens: on the {} trajectories where "
                 "v0.1 refused a proposal v0.2 accepts, every later revision "
                 "round and every token charged from that call onward\n".format(
                     len(withdrawn_stop)))
        fh.write("# self-check: {} assertions passed, including {} E7 loop "
                 "statistics reproduced with 0 mismatches\n".format(
                     len(checks), e7_checked))
        fh.write("# exposed items: {}\n".format(", ".join(sorted(exposed_items))))
        for path, h in hashes.items():
            fh.write("# {} sha256 {}\n".format(path, h))
        w = csv.writer(fh)
        w.writerow(["section", "scope", "quantity", "value", "denominator",
                    "share", "note"])

        w.writerow(["exposure", "ALL", "exposed_items", len(exposed_items), 240,
                    share(len(exposed_items), 240),
                    "instructions of the E3 slice the two guard versions ever "
                    "judged differently"])
        w.writerow(["exposure", "ALL", "exposed_trajectories",
                    len(exposed_traj), len(paired),
                    share(len(exposed_traj), len(paired)), ""])
        w.writerow(["exposure", "ALL", "exposed_proposals", exposed_props,
                    total_props, share(exposed_props, total_props), ""])
        w.writerow(["exposure", "ALL", "withdrawn_refusal_trajectories",
                    len(withdrawn_stop), len(paired),
                    share(len(withdrawn_stop), len(paired)),
                    "trajectories where v0.1 refused a proposal v0.2 accepts; "
                    "the direction is one-way"])
        for arm in ARMS:
            w.writerow(["exposure", arm, "exposed_trajectories",
                        exposed_traj_per_arm[arm], "", "", ""])
            w.writerow(["exposure", arm, "exposed_items",
                        len(exposed_items_per_arm[arm]), 240,
                        share(len(exposed_items_per_arm[arm]), 240), ""])

        w.writerow(["loop_cost", "ALL", "spurious_revision_rounds",
                    spurious_rounds, total_rounds,
                    share(spurious_rounds, total_rounds),
                    "revision rounds that exist only because the retired rule "
                    "refused a proposal the corrected guard accepts"])
        w.writerow(["loop_cost", "ALL", "spurious_tokens", spurious_tokens,
                    all_tokens, share(spurious_tokens, all_tokens),
                    "charged tokens from the call that produced the first "
                    "proposal after the corrected guard's stopping point"])
        for arm in ARMS:
            w.writerow(["loop_cost", arm, "spurious_tokens",
                        spurious_per_arm[arm], "", "", ""])

        for arm in ARMS:
            allv, dropped = loo[arm]
            note = ("the wire artifact the macro range excludes"
                    if arm == "deepseek" else "")
            w.writerow(["leave_one_out", arm,
                        "proposals_per_accepted_all_items",
                        "{:.6f}".format(allv), "", "",
                        "loose budget, SINGLE+G; equals "
                        "analysis/E7_e3_profiles.csv "
                        "proposals_per_accepted_adjustment"])
            w.writerow(["leave_one_out", arm,
                        "proposals_per_accepted_dropped",
                        "{:.6f}".format(dropped), "", "",
                        "the same cell with the exposed instructions removed"
                        + ("; " + note if note else "")])
        w.writerow(["leave_one_out", "five arms (DeepSeek excluded)",
                    "proposals_per_accepted_dropped_min",
                    "{:.6f}".format(min(loo_dropped)), "", "",
                    "minimum over " + ", ".join(LOO_ARMS)])
        w.writerow(["leave_one_out", "five arms (DeepSeek excluded)",
                    "proposals_per_accepted_dropped_max",
                    "{:.6f}".format(max(loo_dropped)), "", "",
                    "maximum over " + ", ".join(LOO_ARMS)])

    print(json.dumps({
        "version": VERSION,
        "trajectories": len(paired),
        "proposals": total_props,
        "exposed_items": sorted(exposed_items),
        "exposed_trajectories": len(exposed_traj),
        "exposed_proposals": exposed_props,
        "exposed_trajectories_per_arm": dict(exposed_traj_per_arm),
        "spurious_revision_rounds": spurious_rounds,
        "recorded_revision_rounds": total_rounds,
        "spurious_tokens": spurious_tokens,
        "all_tokens": all_tokens,
        "spurious_token_share_pct": round(100 * spurious_tokens / all_tokens, 4),
        "leave_one_out": {a: {"all_items": loo[a][0], "dropped": loo[a][1]}
                          for a in ARMS},
        "trajectory_log": stats,
    }, indent=1))
    print("wrote {}".format(out), file=sys.stderr)
    print("all {} assertions passed".format(len(checks)), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
