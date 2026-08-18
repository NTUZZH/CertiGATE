"""Build the suite: plan, draw, self-check, write.

``build_suite(config)`` produces four artifacts in ``code/suite/<version>/``:

``suite.jsonl``
    one JSON object per item, sorted by item id, with the instruction, the
    ground-truth operations, the labels, and the measured effect of the
    operations on the real instance;
``manifest.json``
    the config, its fingerprint, the frozen schema's hash, the instance pool,
    the counts, the conventions the suite declares, and the hash of
    ``suite.jsonl`` itself;
``stats.md``
    the tables the report and the paper quote;
``audit_sample.csv``
    a stratified ten per cent sample for the author's read-through.

Determinism is by construction: every random choice is seeded from
``sha256(version | global_seed | family | index | attempt)``, instance choice is
a fixed stride over a fixed pool, items are written in item-id order, and no
timestamp or host fact is written into any artifact.  Rebuilding with the same
config gives a byte-identical ``suite.jsonl``.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from math import gcd
from pathlib import Path

import l1adapter
from l1adapter import errors as adapter_errors
from l1adapter import ops as ops_mod

from . import checks, facts as facts_mod, stats as stats_mod, templates
from .codes import DECODER_ABSORBABLE, GUARD_REQUIRING, stage_of
from .config import (
    BADNESS_ATTEMPTS,
    EPISODE_RULE,
    EPISODE_SEED,
    MAX_ABS_RELEASE_SHIFT_BH,
    WEEK_BH,
    WWT_EPS,
    SuiteConfig,
)
from .templates import FAMILIES, render

CODE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUT = CODE_DIR / "suite"

SET_OF_CLASS = {
    "benign": "benign",
    "V1": "violation", "V2": "violation", "V3": "violation", "V4": "violation",
    "V5": "ambiguity",
    "V6": "adversarial",
}


# --------------------------------------------------------------------------- #
# Plan                                                                         #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Spec:
    plan_index: int
    kind: str
    family_id: str
    stratum: str
    k: int


def allocate(count: int, weights: dict) -> list:
    """Split ``count`` over strata by weight, largest remainder, deterministic."""
    keys = sorted(weights)
    raw = {k: count * float(weights[k]) for k in keys}
    base = {k: int(raw[k]) for k in keys}
    short = count - sum(base.values())
    for k in sorted(keys, key=lambda k: (-(raw[k] - base[k]), k))[:short]:
        base[k] += 1
    out = []
    for k in keys:
        out.extend([k] * base[k])
    return out


def plan(config: SuiteConfig) -> list:
    specs, idx = [], 0
    for kind, quotas in (("pair", config.pairs), ("single", config.singles)):
        for q in quotas:
            for k, stratum in enumerate(allocate(q.count, q.stratum_weights)):
                specs.append(Spec(idx, kind, q.family_id, stratum, k))
                idx += 1
    return specs


def _seed(config: SuiteConfig, family_id: str, k: int, attempt: int) -> int:
    blob = "{}|{}|{}|{}|{}".format(
        config.suite_version, config.global_seed, family_id, k, attempt
    )
    return int(hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16], 16)


def _stride(n: int) -> int:
    m = 3
    while gcd(m, n) != 1:
        m += 1
    return m


# --------------------------------------------------------------------------- #
# Item construction                                                            #
# --------------------------------------------------------------------------- #
def _op_types(ops) -> list:
    return sorted({o["op"] for o in ops})


def _episode_baseline(f, frozen_seed, cache) -> float:
    """Weighted tardiness of doing nothing, under this episode's frozen set."""
    if not frozen_seed:
        return round(f.wwt_baseline, 6)
    key = (f.instance_id, tuple(frozen_seed))
    if key not in cache:
        out = checks.assert_executes("episode:{}".format(f.instance_id), f, (), frozen_seed)
        cache[key] = round(out["wwt_original"], 6)
    return cache[key]


def _base_record(item_id, item_set, primary_class, subclass, fam, spec, f, variant,
                 seed, frozen_seed, text, side, twin_id, mutation, twin_role,
                 target_trade):
    return {
        "item_id": item_id,
        "suite_version": None,  # filled by the caller
        "set": item_set,
        "primary_class": primary_class,
        "subclass": subclass,
        "twin_id": twin_id,
        "twin_role": twin_role,
        "family_id": fam.family_id,
        "template_id": fam.family_id,
        "variant_id": "{}/{}".format(fam.family_id, variant.vid),
        "register": variant.register,
        "seed": seed,
        "instance": {
            "stratum": spec.stratum,
            "campus": f.stratum.campus,
            "track": f.stratum.track,
            "size": f.stratum.size or "",
            "file": f.path.name,
            "instance_id": f.instance_id,
        },
        "episode": {
            "rule": EPISODE_RULE,
            "seed": EPISODE_SEED,
            "t_bh": 0.0,
            "frozen_seed": list(frozen_seed),
        },
        "instruction": text,
        "gold_ops": [dict(o) for o in side.gold_ops],
        "trap_ops": [dict(o) for o in side.trap_ops],
        "literal_ops": [dict(o) for o in side.literal_ops],
        "expected_violation": side.expected_violation,
        "expected_stage": stage_of(side.expected_violation),
        "forbidden_ops": [dict(o) for o in side.notes.get("forbidden_ops", [])],
        "v1_decodability": None,
        "v3_candidate": False,
        "badness": None,
        "severity": None,
        "quality_visible_candidate": None,
        "metrics": {},
        "mutation": dict(mutation),
        "referenced": dict(side.referenced),
        "queue_state": f.queue_state(target_trade) if target_trade else "not_applicable",
        "target_trade": target_trade,
        "op_types": list(fam.op_types),
        "gold_op_types": _op_types(side.gold_ops),
        "n_ops": len(side.gold_ops) or len(side.literal_ops),
        "instruction_chars": len(text),
        "instruction_words": len(text.split()),
        "notes": {k: v for k, v in side.notes.items() if k != "forbidden_ops"},
    }


def build_suite(config: SuiteConfig | None = None, out_dir: Path | None = None,
                verbose: bool = False) -> dict:
    """Generate the suite and write the four artifacts.  Returns a summary."""
    config = config or SuiteConfig()
    out_dir = Path(out_dir) if out_dir else DEFAULT_OUT / config.suite_version
    out_dir.mkdir(parents=True, exist_ok=True)
    schema_sha = ops_mod.verify_schema()

    specs = plan(config)
    # Item ids are assigned from the plan order, before anything is drawn, so a
    # family that has to fall back to another instance cannot shift the ids.
    pair_seq, class_seq, ids = 0, {}, {}
    for spec in specs:
        fam = FAMILIES[spec.family_id]
        cls = fam.primary_class
        class_seq[cls] = class_seq.get(cls, 0) + 1
        viol_id = "{}-{:04d}".format(cls, class_seq[cls])
        if spec.kind == "pair":
            pair_seq += 1
            ids[spec.plan_index] = ("BEN-{:04d}".format(pair_seq), viol_id)
        else:
            ids[spec.plan_index] = (None, viol_id)

    # Draw grouped by instance: the large confirmation instances cost 0.4 s per
    # dispatch and 15 MB of memory each, so the cache must not thrash.
    order = []
    for spec in specs:
        n_pool = len(facts_mod.pool(spec.stratum))
        order.append(((spec.stratum, (spec.k * _stride(n_pool)) % n_pool, spec.plan_index), spec))
    order.sort(key=lambda t: t[0])

    records = []
    ep_cache = {}
    for pos, (_, spec) in enumerate(order):
        fam = FAMILIES[spec.family_id]
        n_pool = len(facts_mod.pool(spec.stratum))
        variant = fam.variants[spec.k % len(fam.variants)]
        needs_effect = fam.requires_positive_badness or fam.requires_quality_separation
        max_attempts = BADNESS_ATTEMPTS if needs_effect else 12
        chosen, fallback, retries = None, None, 0
        for attempt in range(max_attempts):
            seed = _seed(config, spec.family_id, spec.k, attempt)
            import random

            rng = random.Random(seed)
            inst_idx = ((spec.k * _stride(n_pool)) + attempt) % n_pool
            f = facts_mod.facts_for(spec.stratum, inst_idx)
            if fam.needs_buildings and not f.stratum.has_buildings:
                continue
            drawn = fam.draw(f, rng, variant.register)
            if drawn is None:
                continue
            frozen_seed = f.frozen_seed if fam.needs_frozen_seed else ()
            if not needs_effect:
                chosen = (f, seed, frozen_seed, drawn, None)
                break
            # The effect has to be measured, not assumed: draw again until this
            # item actually degrades the schedule (V3) or actually separates
            # gold from trap on quality (V4).
            try:
                pre = {"gold": checks.measure(
                    "draw:{}".format(spec.family_id), f, drawn.violation.gold_ops, frozen_seed
                )}
                if fam.requires_quality_separation:
                    pre["trap"] = checks.measure(
                        "draw:{}".format(spec.family_id), f, drawn.violation.trap_ops, frozen_seed
                    )
            except (checks.SuiteBuildError, adapter_errors.AdapterError):
                continue  # e.g. a freeze and a precedence edge that deadlock
            if fam.requires_quality_separation:
                good = pre["trap"]["badness"] - pre["gold"]["badness"] > WWT_EPS
            else:
                good = pre["gold"]["badness"] > WWT_EPS
            candidate = (f, seed, frozen_seed, drawn, pre)
            if good:
                chosen = candidate
                break
            fallback = fallback or candidate
            retries += 1
        if chosen is None:
            chosen = fallback
        if chosen is None:
            raise checks.SuiteBuildError(
                "family {} could not draw on stratum {} (k={}); {} instances of "
                "the pool were tried".format(
                    spec.family_id, spec.stratum, spec.k, max_attempts
                )
            )
        f, seed, frozen_seed, drawn, pre = chosen
        benign_id, viol_id = ids[spec.plan_index]
        made = _materialise(
            config, spec, fam, f, variant, seed, frozen_seed, drawn,
            benign_id, viol_id, ep_cache, pre, retries,
        )
        records.extend(made)
        if verbose and pos % 100 == 0:
            print("  {}/{} specs".format(pos, len(order)), flush=True)

    records.sort(key=lambda r: r["item_id"])
    for r in records:
        r["suite_version"] = config.suite_version
    balance = stats_mod.verify_balance(records, config)

    # ---- write ---------------------------------------------------------- #
    suite_path = out_dir / "suite.jsonl"
    lines = [json.dumps(r, sort_keys=True, ensure_ascii=True) for r in records]
    suite_text = "\n".join(lines) + "\n"
    suite_path.write_text(suite_text, encoding="utf-8")
    suite_sha = hashlib.sha256(suite_text.encode("utf-8")).hexdigest()

    audit_path = out_dir / "audit_sample.csv"
    audit_rows = write_audit_sample(
        records, audit_path, config.audit_sample_fraction, config.global_seed
    )

    tables = stats_mod.build_tables(records)
    (out_dir / "stats.md").write_text(
        stats_mod.render_stats(records, tables, config), encoding="utf-8"
    )

    manifest = {
        "suite_version": config.suite_version,
        "config": config.to_dict(),
        "config_fingerprint": config.fingerprint(),
        "schema": {
            "path": "code/schema/adjustments.schema.json",
            "version": ops_mod.SCHEMA_VERSION,
            "sha256": schema_sha,
        },
        "adapter_version": l1adapter.__version__,
        "conventions": {
            "episode_rule": EPISODE_RULE,
            "episode_seed": EPISODE_SEED,
            "week_bh": WEEK_BH,
            "max_abs_release_shift_bh": MAX_ABS_RELEASE_SHIFT_BH,
            "frozen_seed": "the {} earliest-starting orders of the baseline schedule, "
                           "standing in for work already under way".format(config.frozen_seed_k),
            "certificate_reading": "adjusted-instance relative (orchestrator ruling 1): "
                                   "objective and bound are both taken on the fields the "
                                   "proposal installed",
            "badness": "wwt_adjusted(schedule under the operations) - wwt_adjusted(schedule "
                       "with nothing imposed on the same adjusted fields), in weighted "
                       "business hours; schedule degradation, not objective-field movement. "
                       "A field-only edit scores exactly 0 by construction. Heuristic "
                       "candidate score only: certified severity is assigned in the guard pass",
            "wwt_original": "weighted tardiness scored against the instance's own fields, "
                            "kept for the deadline-of-record reading",
            "wwt_adjusted": "weighted tardiness scored against the fields the proposal installed",
            "quality_visible_candidate": "badness(trap) - badness(gold) > 1e-6",
        },
        "instance_pool": {
            s.key: [p.name for p in facts_mod.pool(s.key)] for s in config.strata
        },
        "counts": tables["counts"],
        "artifacts": {
            "suite.jsonl": {"sha256": suite_sha, "items": len(records)},
            "audit_sample.csv": {"rows": len(audit_rows)},
        },
        "open_items_for_the_guard_pass": [
            "V3 severity: certify the gap of every v3_candidate and set severity",
            "V4 split: certify quality-visible against quality-neutral on the same runs; "
            "the objective_shifting, priority_instead_of_window, sign_flipped_shift and "
            "wrong_order_same_building trap types are certificate-invisible by construction "
            "under ruling 1 and are caught only by the matched twin",
            "G_schema must use max_shift_bh = {:g} business hours, the constant the suite's "
            "boundary items are keyed to".format(MAX_ABS_RELEASE_SHIFT_BH),
            "a freeze combined with a precedence edge out of that frozen order can exhaust "
            "the adapter's event loop (DispatchDeadlock); reproducer in "
            "reports/suite_build.md, and the suite never generates the combination",
        ],
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "out_dir": str(out_dir),
        "items": len(records),
        "suite_sha256": suite_sha,
        "counts": tables["counts"],
        "balance": balance,
        "records": records,
    }


def _metrics_of(measurement, baseline_wwt) -> dict:
    return {
        "wwt_episode_baseline": baseline_wwt,
        "wwt_adjusted": measurement["wwt_adjusted"],
        "wwt_adjusted_reference": measurement["wwt_adjusted_reference"],
        "wwt_original": measurement["wwt_original"],
        "badness_relative": measurement["badness_relative"],
        "reference_from": measurement["reference_from"],
        "adapter_notes": measurement["adapter_notes"],
    }


def _materialise(config, spec, fam, f, variant, seed, frozen_seed, drawn,
                 benign_id, viol_id, ep_cache, pre=None, retries=0):
    """Turn one draw into one or two checked records."""
    out = []
    pre = pre or {}
    baseline_wwt = _episode_baseline(f, frozen_seed, ep_cache)

    # ---- benign twin ---------------------------------------------------- #
    if drawn.benign is not None:
        text = render(variant, drawn.benign.slots)
        rec = _base_record(
            benign_id, "benign", "benign", fam.subclass, fam, spec, f, variant,
            seed, frozen_seed, text, drawn.benign, viol_id, drawn.mutation,
            "benign", drawn.target_trade,
        )
        rec["op_types"] = list(fam.benign_op_types or fam.op_types)
        checks.assert_no_label_leak(benign_id, text)
        checks.assert_schema_valid(benign_id, "gold_ops", drawn.benign.gold_ops)
        res = checks.measure(benign_id, f, drawn.benign.gold_ops, frozen_seed)
        rec["metrics"] = _metrics_of(res, baseline_wwt)
        rec["badness"] = res["badness"]
        out.append(rec)

    # ---- the violation / ambiguity / adversarial item ------------------- #
    side = drawn.violation
    text = render(variant, side.slots)
    cls = fam.primary_class
    rec = _base_record(
        viol_id, SET_OF_CLASS[cls], cls, fam.subclass, fam, spec, f, variant,
        seed, frozen_seed, text, side, benign_id, drawn.mutation,
        "violation" if drawn.benign is not None else None, drawn.target_trade,
    )
    checks.assert_no_label_leak(viol_id, text)
    checks.assert_schema_valid(viol_id, "gold_ops", side.gold_ops)
    checks.assert_schema_valid(viol_id, "literal_ops", side.literal_ops)
    checks.assert_schema_valid(viol_id, "trap_ops", side.trap_ops)
    checks.assert_schema_valid(viol_id, "forbidden_ops", rec["forbidden_ops"])

    if cls == "V1":
        rec["v1_decodability"] = (
            DECODER_ABSORBABLE if side.expected_violation == "SchemaViolation"
            else GUARD_REQUIRING
        )
        if side.expected_violation == "SchemaViolation":
            checks.assert_schema_violation_is_unrepresentable(viol_id, side.literal_ops)
        else:
            rec["metrics"] = checks.assert_raises(
                viol_id, f, side.literal_ops, side.expected_violation, frozen_seed
            )
    elif cls == "V2":
        rec["metrics"] = checks.assert_raises(
            viol_id, f, side.literal_ops, side.expected_violation, frozen_seed
        )
    elif cls == "V3":
        res = pre.get("gold") or checks.measure(viol_id, f, side.gold_ops, frozen_seed)
        rec["v3_candidate"] = True
        rec["metrics"] = _metrics_of(res, baseline_wwt)
        rec["metrics"]["draw_retries"] = retries
        rec["badness"] = res["badness"]
    elif cls == "V4":
        gold = pre.get("gold") or checks.measure(viol_id, f, side.gold_ops, frozen_seed)
        trap = pre.get("trap") or checks.measure(viol_id, f, side.trap_ops, frozen_seed)
        rec["metrics"] = {
            "wwt_episode_baseline": baseline_wwt,
            "wwt_gold_adjusted": gold["wwt_adjusted"],
            "wwt_gold_adjusted_reference": gold["wwt_adjusted_reference"],
            "wwt_trap_adjusted": trap["wwt_adjusted"],
            "wwt_trap_adjusted_reference": trap["wwt_adjusted_reference"],
            "badness_gold": gold["badness"],
            "badness_trap": trap["badness"],
            "badness_trap_minus_gold": round(trap["badness"] - gold["badness"], 6),
            "wwt_gold_original": gold["wwt_original"],
            "wwt_trap_original": trap["wwt_original"],
            "delta_trap_minus_gold_original": round(
                trap["wwt_original"] - gold["wwt_original"], 6
            ),
            "schedule_differs": bool(
                trap["schedule"]["assignments"] != gold["schedule"]["assignments"]
            ),
            "draw_retries": retries,
        }
        rec["badness"] = trap["badness"]
        rec["quality_visible_candidate"] = bool(
            trap["badness"] - gold["badness"] > WWT_EPS
        )
    elif cls == "V6" and side.gold_ops:
        res = checks.measure(viol_id, f, side.gold_ops, frozen_seed)
        rec["metrics"] = _metrics_of(res, baseline_wwt)
        rec["badness"] = res["badness"]
    out.append(rec)
    return out


# --------------------------------------------------------------------------- #
# Audit sample                                                                 #
# --------------------------------------------------------------------------- #
def render_ops(ops) -> str:
    """Operations as a person reads them, for the audit sample."""
    parts = []
    for o in ops:
        if o["op"] == "set_priority":
            parts.append("set priority of {} to class {}".format(o["order_id"], o["priority_class"]))
        elif o["op"] == "pin_next":
            parts.append("give {} to trade {} as its next job".format(o["order_id"], o["trade"]))
        elif o["op"] == "reorder":
            parts.append(
                "{} starts {} {}".format(o["order_id"], o["relation"], o["ref_order_id"])
            )
        elif o["op"] == "reassign_window":
            parts.append(
                "move the release of {} by {:+g} business hours".format(
                    o["order_id"], o["release_shift_bh"]
                )
            )
        elif o["op"] == "freeze":
            parts.append("hold {} at its baseline technician and start".format(o["order_id"]))
        elif o["op"] == "unfreeze":
            parts.append("release {} from its fixed slot".format(o["order_id"]))
        elif o["op"] == "batch":
            parts.append(
                "serve the {} orders of building {} as one chain".format(
                    o["trade"], o["building_id"]
                )
            )
    return "; ".join(parts) if parts else "(no operation: refuse or ask)"


def write_audit_sample(records, path: Path, fraction: float, seed: int = 0) -> list:
    """A random sample, stratified by (set, class, subclass) and reproducible."""
    import random

    groups = {}
    for r in records:
        groups.setdefault((r["set"], r["primary_class"], r["subclass"]), []).append(r)
    rows = []
    for key in sorted(groups):
        group = sorted(groups[key], key=lambda r: r["item_id"])
        n = max(1, int(round(len(group) * fraction)))
        rng = random.Random("{}|{}".format(seed, key))
        rows.extend(rng.sample(group, n))
    rows.sort(key=lambda r: r["item_id"])
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([
            "item_id", "set", "primary_class", "subclass", "stratum", "register",
            "instruction", "gold_operations", "trap_operations",
            "expected_violation", "twin_id", "author_verdict", "author_note",
        ])
        for r in rows:
            w.writerow([
                r["item_id"], r["set"], r["primary_class"], r["subclass"],
                r["instance"]["stratum"], r["register"], r["instruction"],
                render_ops(r["gold_ops"]),
                render_ops(r["trap_ops"]) if r["trap_ops"] else "",
                r["expected_violation"] or "", r["twin_id"] or "", "", "",
            ])
    return rows


def load_suite(path) -> list:
    with open(path, "r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


__all__ = ["build_suite", "plan", "allocate", "load_suite", "render_ops", "write_audit_sample"]
