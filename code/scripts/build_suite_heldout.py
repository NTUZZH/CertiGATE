#!/usr/bin/env python
"""N9 (B): a held-out V3 draw admitted without the badness screen.

WHY THIS EXISTS
---------------
The published V3 items (code/suite/v0.2) were admitted by a screen: a draw was
kept only when its faithful translation made the ATC dispatch worse than the
same adjusted fields dispatched with nothing imposed (``badness > 0``,
code/l1suite/generate.py).  That statistic is the one the hand-written rule
D-REL2 thresholds, so the published V3 set is selected on the rule's own
input.  This script draws a second V3 set from the same five families, with
the same quotas, on the same 60 instances, with a new seed, and with the
screen switched off.  The draw keeps every structural requirement of the
templates (a deadline-critical successor, a late-arriving predecessor, a
harmless twin predecessor, the replay-only batch family), so the items are the
same kind of instruction; only the admission on the dispatcher's own
degradation is removed.  The items are later labelled by the instruction cost
under optimal execution (code/scripts/n9_instruction_cost.py), which no gate
computes.

WHAT IS THE SAME AS THE PUBLISHED BUILD
---------------------------------------
* the families, their surface variants and their quotas (220 pairs:
  v3_reorder_block_tight 70, v3_reorder_two_successors 45,
  v3_reorder_cross_trade 45, v3_window_blocked_predecessor 45,
  v3_reorder_behind_batch_member 15, the last on the replay stratum only);
* the stratum allocation, the instance stride over each stratum's pool, and the
  60 pool instances, read from the instances_v10 snapshot and checked against
  code/scripts/instance_manifest_l1.json;
* the per-draw seed rule sha256(version | global_seed | family | k | attempt);
* the record format, the label-leak check, the schema check, and the
  measurement of badness and badness_relative (code/l1suite/checks.py).

WHAT DIFFERS
------------
* global_seed 20261103 and suite version ``v0.3_heldout`` (both enter the seed);
* no badness screen: the first structurally valid draw is kept.  A draw whose
  faithful translation does not execute (apply or dispatch raises) is drawn
  again, up to the generator's non-screened attempt cap of 12, and counted;
* item ids ``V3H-0001`` ... and ``BENH-0001`` ..., so no id collides with v0.2.

REPRODUCTION CHECK (``--check-published``)
------------------------------------------
The same drawing loop, given the published seed, version and screen, must
reproduce every published V3 item and its benign twin field for field (item id,
instance, instruction, gold operations, mutation, badness).  This shows the
held-out set differs from the published one only by the seed and the screen.

OUTPUTS (code/suite/v0.3_heldout/)
----------------------------------
``suite_heldout.jsonl``     440 records (220 V3 items, 220 benign twins)
``manifest_heldout.json``   config, pool files and digests, counts, the file's
                            sha256, the reproduction-check result

Run::

    python code/scripts/build_suite_heldout.py [--check-published]

Version: l1-n9-heldout-1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import statistics
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

SNAPSHOT_ROOT = Path(((os.environ.get("L1_Y1_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "PaperY-FMScheduling")) + "/data/processed/instances_v10"))
_env = os.environ.get("L1_INSTANCE_ROOT")
if _env and Path(_env).resolve() != SNAPSHOT_ROOT.resolve():
    raise SystemExit("REFUSING TO RUN: L1_INSTANCE_ROOT={} is not the snapshot".format(_env))
os.environ["L1_INSTANCE_ROOT"] = str(SNAPSHOT_ROOT)

SCRIPTS_DIR = Path(__file__).resolve().parent
CODE = SCRIPTS_DIR.parent
ROOT = CODE.parent
for _p in (str(CODE), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import l1adapter.instances as instances_mod  # noqa: E402

# The suite's instance pool is read through l1adapter.instances; point it at the
# snapshot, the tree every published number was computed on.
instances_mod.INSTANCE_ROOT = SNAPSHOT_ROOT

from l1adapter import errors as adapter_errors  # noqa: E402
from l1suite import checks, facts as facts_mod, generate as gen  # noqa: E402
from l1suite.config import BADNESS_ATTEMPTS, SuiteConfig  # noqa: E402
from l1suite.templates import FAMILIES  # noqa: E402

VERSION = "l1-n9-heldout-1"
HELDOUT_VERSION = "v0.3_heldout"
HELDOUT_SEED = 20261103
PUBLISHED_SEED = 20260811
UNSCREENED_ATTEMPTS = 12
OUT_DIR = CODE / "suite" / HELDOUT_VERSION
OUT_PATH = OUT_DIR / "suite_heldout.jsonl"
PUBLISHED_PATH = CODE / "suite" / "v0.2" / "suite.jsonl"
PUBLISHED_SHA256 = "0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a"
MANIFEST = SCRIPTS_DIR / "instance_manifest_l1.json"

V3_FAMILIES = ("v3_reorder_block_tight", "v3_reorder_two_successors",
               "v3_reorder_cross_trade", "v3_window_blocked_predecessor",
               "v3_reorder_behind_batch_member")
EXPECTED_QUOTAS = {"v3_reorder_block_tight": 70, "v3_reorder_two_successors": 45,
                   "v3_reorder_cross_trade": 45, "v3_window_blocked_predecessor": 45,
                   "v3_reorder_behind_batch_member": 15}


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_pool() -> dict:
    """Every pool file of the three strata is in the manifest with its digest."""
    manifest = json.loads(MANIFEST.read_text())["files"]
    out = {}
    for s in SuiteConfig().strata:
        for p in facts_mod.pool(s.key):
            rel = str(Path(p).resolve().relative_to(SNAPSHOT_ROOT.resolve()))
            if rel not in manifest:
                raise SystemExit("REFUSING TO RUN: pool file {} is not in the manifest".format(rel))
            d = sha256_file(p)
            if d != manifest[rel]:
                raise SystemExit("REFUSING TO RUN: pool file {} digest mismatch".format(rel))
            out[rel] = d
    if len(out) != 60:
        raise SystemExit("REFUSING TO RUN: pool has {} files, expected 60".format(len(out)))
    return out


def v3_config(version: str, seed: int, scale: float = 1.0) -> SuiteConfig:
    base = SuiteConfig()
    pairs = tuple(q for q in base.pair_quotas if q.family_id in V3_FAMILIES)
    got = {q.family_id: q.count for q in pairs}
    if got != EXPECTED_QUOTAS:
        raise SystemExit("V3 quotas in l1suite.config moved: {}".format(got))
    return replace(base, suite_version=version, global_seed=seed, pair_quotas=pairs,
                   single_quotas=(), quota_scale=scale)


def published_ids(scale: float = 1.0) -> dict:
    """(family, k) -> (benign id, V3 id) exactly as the published build numbers them."""
    full = SuiteConfig()
    full.quota_scale = scale
    pair_seq, class_seq, out = 0, {}, {}
    for spec in gen.plan(full):
        cls = FAMILIES[spec.family_id].primary_class
        class_seq[cls] = class_seq.get(cls, 0) + 1
        vid = "{}-{:04d}".format(cls, class_seq[cls])
        if spec.kind == "pair":
            pair_seq += 1
            out[(spec.family_id, spec.k)] = ("BEN-{:04d}".format(pair_seq), vid)
    return out


def draw(config: SuiteConfig, screen: bool, id_of) -> tuple:
    """The generator's drawing loop over the V3 plan; returns (records, draw log)."""
    specs = gen.plan(config)
    order = []
    for spec in specs:
        n_pool = len(facts_mod.pool(spec.stratum))
        order.append(((spec.stratum, (spec.k * gen._stride(n_pool)) % n_pool,
                       spec.plan_index), spec))
    order.sort(key=lambda t: t[0])
    records, log, ep_cache = [], [], {}
    for _, spec in order:
        fam = FAMILIES[spec.family_id]
        n_pool = len(facts_mod.pool(spec.stratum))
        variant = fam.variants[spec.k % len(fam.variants)]
        needs_effect = screen and fam.requires_positive_badness
        max_attempts = BADNESS_ATTEMPTS if needs_effect else UNSCREENED_ATTEMPTS
        chosen, fallback, retries, structural = None, None, 0, 0
        for attempt in range(max_attempts):
            seed = gen._seed(config, spec.family_id, spec.k, attempt)
            rng = random.Random(seed)
            inst_idx = ((spec.k * gen._stride(n_pool)) + attempt) % n_pool
            f = facts_mod.facts_for(spec.stratum, inst_idx)
            if fam.needs_buildings and not f.stratum.has_buildings:
                continue
            drawn = fam.draw(f, rng, variant.register)
            if drawn is None:
                continue
            frozen_seed = f.frozen_seed if fam.needs_frozen_seed else ()
            try:
                pre = {"gold": checks.measure("draw:{}".format(spec.family_id), f,
                                              drawn.violation.gold_ops, frozen_seed)}
            except (checks.SuiteBuildError, adapter_errors.AdapterError):
                structural += 1
                continue
            candidate = (f, seed, frozen_seed, drawn, pre, attempt)
            if not needs_effect:
                chosen = candidate
                break
            if pre["gold"]["badness"] > gen.WWT_EPS:
                chosen = candidate
                break
            fallback = fallback or candidate
            retries += 1
        if chosen is None:
            chosen = fallback
        if chosen is None:
            raise checks.SuiteBuildError("family {} could not draw on {} (k={})".format(
                spec.family_id, spec.stratum, spec.k))
        f, seed, frozen_seed, drawn, pre, attempt = chosen
        benign_id, viol_id = id_of(spec)
        made = gen._materialise(config, spec, fam, f, variant, seed, frozen_seed, drawn,
                                benign_id, viol_id, ep_cache, pre, retries)
        for r in made:
            r["suite_version"] = config.suite_version
        records.extend(made)
        log.append({"family_id": spec.family_id, "k": spec.k, "stratum": spec.stratum,
                    "attempt": attempt, "screen_retries": retries,
                    "structural_rejections": structural, "item_id": viol_id})
    records.sort(key=lambda r: r["item_id"])
    return records, log


def heldout_ids(config):
    seq = {}
    for spec in gen.plan(config):
        seq[(spec.family_id, spec.k)] = len(seq) + 1

    def id_of(spec):
        k = seq[(spec.family_id, spec.k)]
        return "BENH-{:04d}".format(k), "V3H-{:04d}".format(k)
    return id_of


def check_twins(records) -> None:
    by = {r["item_id"]: r for r in records}
    v3 = [r for r in records if r["primary_class"] == "V3"]
    ben = [r for r in records if r["primary_class"] == "benign"]
    problems = []
    if len(v3) != len(ben):
        problems.append("{} V3 vs {} benign".format(len(v3), len(ben)))
    for r in v3:
        t = by.get(r["twin_id"])
        if t is None or t["twin_id"] != r["item_id"]:
            problems.append("{}: twin relation broken".format(r["item_id"]))
            continue
        if t["instance"]["instance_id"] != r["instance"]["instance_id"]:
            problems.append("{}: twin on another instance".format(r["item_id"]))
        if t["instruction"] == r["instruction"]:
            problems.append("{}: twin carries the same instruction".format(r["item_id"]))
        if r["episode"]["frozen_seed"]:
            problems.append("{}: V3 item with a standing frozen set".format(r["item_id"]))
    if problems:
        raise checks.SuiteBuildError("held-out checks failed: " + "; ".join(problems[:10]))


def serialise(records) -> str:
    return "\n".join(json.dumps(r, sort_keys=True, ensure_ascii=True) for r in records) + "\n"


def stats(records) -> dict:
    out = {}
    v3 = [r for r in records if r["primary_class"] == "V3"]
    for fam in V3_FAMILIES + ("all",):
        rows = [r for r in v3 if fam == "all" or r["family_id"] == fam]
        twins = [r for r in records if r["primary_class"] == "benign"
                 and (fam == "all" or r["family_id"] == fam)]
        br = [r["metrics"]["badness_relative"] for r in rows]
        out[fam] = {
            "n": len(rows),
            "positive_badness": sum(1 for r in rows if r["badness"] > gen.WWT_EPS),
            "share_positive_badness": (sum(1 for r in rows if r["badness"] > gen.WWT_EPS)
                                       / len(rows)) if rows else None,
            "badness_relative_min": min(br) if br else None,
            "badness_relative_median": statistics.median(br) if br else None,
            "badness_relative_max": max(br) if br else None,
            "share_badness_relative_above_0.02": (sum(1 for x in br if x > 0.02) / len(br))
            if br else None,
            "twins_positive_badness": sum(1 for r in twins if r["badness"] > gen.WWT_EPS),
            "by_stratum": dict(Counter(r["instance"]["stratum"] for r in rows)),
        }
    return out


def build(scale: float = 1.0, out_path: Path | None = None, seed: int = HELDOUT_SEED) -> dict:
    """Draw the held-out set and write it; returns a summary with the sha256."""
    config = v3_config(HELDOUT_VERSION, seed, scale)
    records, log = draw(config, screen=False, id_of=heldout_ids(config))
    check_twins(records)
    for r in records:
        checks.assert_no_label_leak(r["item_id"], r["instruction"])
    text = serialise(records)
    out_path = Path(out_path) if out_path else OUT_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    return {"sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "n_items": len(records), "records": records, "log": log,
            "config": config, "path": str(out_path)}


COMPARE_FIELDS = ("item_id", "twin_id", "family_id", "variant_id", "instance", "episode",
                  "instruction", "gold_ops", "mutation", "badness", "metrics", "referenced",
                  "seed", "notes")


def check_published() -> dict:
    """The loop with the published seed and screen reproduces published V3 + twins."""
    if sha256_file(PUBLISHED_PATH) != PUBLISHED_SHA256:
        raise SystemExit("REFUSING TO RUN: published suite digest mismatch")
    pub = {}
    for ln in open(PUBLISHED_PATH, encoding="utf-8"):
        if ln.strip():
            r = json.loads(ln)
            pub[r["item_id"]] = r
    config = v3_config("v0.2", PUBLISHED_SEED)
    ids = published_ids()
    records, _log = draw(config, screen=True, id_of=lambda s: ids[(s.family_id, s.k)])
    mism = []
    for r in records:
        p = pub.get(r["item_id"])
        if p is None:
            mism.append((r["item_id"], "missing"))
            continue
        for k in COMPARE_FIELDS:
            if p.get(k) != r.get(k):
                mism.append((r["item_id"], k))
    n_pub = sum(1 for r in pub.values() if r["primary_class"] == "V3")
    return {"records_compared": len(records), "published_v3": n_pub,
            "mismatches": len(mism), "first_mismatches": mism[:10]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check-published", action="store_true",
                    help="also reproduce the published V3 draw (seed 20260811, screen on)")
    ap.add_argument("--cores", default=None, help="pin to these cores (e.g. 16-19)")
    args = ap.parse_args()
    if args.cores:
        cores = set()
        for part in args.cores.split(","):
            a, _, b = part.partition("-")
            cores.update(range(int(a), int(b or a) + 1))
        os.sched_setaffinity(0, cores)
    pool = verify_pool()
    repro = None
    if args.check_published:
        repro = check_published()
        print("[n9b] published reproduction: {}".format(json.dumps(repro)))
        if repro["mismatches"] or repro["records_compared"] != 2 * repro["published_v3"]:
            raise SystemExit("published V3 draw NOT reproduced; held-out set not written")
        facts_mod.clear_caches()
    res = build()
    st = stats(res["records"])
    struct = sum(x["structural_rejections"] for x in res["log"])
    attempts = Counter(x["attempt"] for x in res["log"])
    manifest = {
        "version": VERSION,
        "suite_version": HELDOUT_VERSION,
        "global_seed": HELDOUT_SEED,
        "badness_screen": False,
        "attempt_cap": UNSCREENED_ATTEMPTS,
        "config": res["config"].to_dict(),
        "config_fingerprint": res["config"].fingerprint(),
        "instance_root": "instances_v10 snapshot (code/scripts/instance_manifest_l1.json)",
        "instance_pool": pool,
        "artifacts": {"suite_heldout.jsonl": {"sha256": res["sha256"], "items": res["n_items"]}},
        "counts": dict(Counter(r["primary_class"] for r in res["records"])),
        "by_family": dict(Counter(r["family_id"] for r in res["records"]
                                  if r["primary_class"] == "V3")),
        "structural_rejections": struct,
        "draw_attempt_histogram": {str(k): v for k, v in sorted(attempts.items())},
        "stats": st,
        "published_reproduction": repro,
        "draw_log": res["log"],
    }
    (OUT_DIR / "manifest_heldout.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("[n9b] wrote {} ({} records) sha256 {}".format(
        str(Path(res["path"]).relative_to(ROOT)), res["n_items"], res["sha256"]))
    print("[n9b] structural rejections {}; attempts {}".format(struct, dict(attempts)))
    for fam, s in st.items():
        print("   {:34s} n={:3d} positive={:3d} ({:.1%}) rel min={:.4f} median={:.4f}".format(
            fam, s["n"], s["positive_badness"], s["share_positive_badness"] or 0.0,
            s["badness_relative_min"], s["badness_relative_median"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
