#!/usr/bin/env python
"""The frozen E3 item slice: E3-300, its 60-item calibration subsample, and E3-240.

E3 runs one item slice, unchanged, for every arm, every budget level and every
pipeline (decisions.md, 2026-08-12, "E3 DESIGN FREEZE"): instruction noise is
held constant by construction rather than modelled away, and every E3 metric is
additionally reported by register.  This script is where that slice is defined,
and it is a pure function of the suite file: no model, no network, no state.

The draw, verbatim from the freeze
----------------------------------
*Violations first, then twin closure.*  The four operational violation classes
are drawn in proportion to the suite's own composition, ``V1 24 / V2 30 /
V3 33 / V4 33`` (= 120 of the 800 violations, and 160/200/220/220 x 3/20 is
exactly those four numbers).  Each drawn violation brings its matched benign
twin along, which is what makes the 120 McNemar pairs exact.  ``V5 30`` and
``V6 30`` are drawn on top; no twin exists for either by suite design, because
their metric is refusal rather than block-versus-false-block.  Total 300.

*Register-proportional within every cell.*  Each class's target is split over
``formal / terse / conversational`` in proportion to that class's own register
counts, by the largest-remainder rule with ties broken in that fixed register
order.  So the slice's noise profile is the suite's noise profile, per class.

*Deterministic, at seed 0.*  Within a ``(class, register)`` cell the items are
ordered by ``sha256("l1-e3-sample|seed=0|class=...|register=...|<item_id>")`` and
the target count is taken from the front.  A keyed sort rather than
``random.shuffle`` because it is a property of the inputs alone: it cannot drift
with a Python release, and any reader can recompute it in three lines.

The two smaller slices are PREFIXES of the same per-cell orders, so
``E3-CAL-60`` is a subset of ``E3-240`` is a subset of ``E3-300``.  This is what
makes the pre-declared fallback safe: if the launch-gate projection busts the
cost envelope and the run shrinks to E3-240, every trajectory already logged for
those items stays valid instead of being thrown away.

*E3-240*, the pre-declared fallback (never an ad-hoc trim): 96 violations, split
over V1-V4 in the same suite proportion, their 96 twins, V5 24, V6 24.

*E3-CAL-60*, the calibration subsample the budget levels are derived from: 24
violations in the same proportion, their 24 twins, V5 6, V6 6.

Run::

    conda run -n fjsp python scripts/e3_sample.py                 # write the file
    conda run -n fjsp python scripts/e3_sample.py --print E3-300  # ids on stdout

The output file carries the SHA-256 of each emitted id list, so a later run (or
another machine) proves it drew the same slice rather than asserting it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))  # scripts/: suite_gate
sys.path.insert(0, str(_HERE.parent))  # code/

import suite_gate as sg  # noqa: E402  (suite sha assertion, suite loading)

SAMPLE_VERSION = "l1-e3-sample-1"
SEED = 0

#: The fixed register order.  It is the tie-break of the largest-remainder rule
#: and the order cells are reported in; nothing else depends on it.
REGISTERS = ("formal", "terse", "conversational")

#: The four operational violation classes, in the order the freeze names them.
V_CLASSES = ("V1", "V2", "V3", "V4")

#: The refusal classes: drawn on top of the violations, no twins by suite design.
R_CLASSES = ("V5", "V6")

#: The frozen E3-300 targets (decisions.md, 2026-08-12).  They are asserted
#: against the proportional computation rather than derived from it, so a change
#: in either the suite or the freeze shows up as a failure here.
FROZEN_300 = {"V1": 24, "V2": 30, "V3": 33, "V4": 33, "V5": 30, "V6": 30}

#: The pre-declared fallback and the calibration subsample, as (violation total,
#: per-refusal-class count).  The violation total is split over V1-V4 in the
#: suite's own proportion by the same largest-remainder rule.
FALLBACK_240 = (96, 24)
CALIBRATION_60 = (24, 6)

SLICE_E3_300 = "E3-300"
SLICE_E3_240 = "E3-240"
SLICE_CAL_60 = "E3-CAL-60"
SLICE_NAMES = (SLICE_E3_300, SLICE_E3_240, SLICE_CAL_60)

#: The frozen size of each slice, so a runner can print its grid before it reads
#: the suite.  ``build_slices`` asserts these are what the draw produces.
SLICE_SIZES = {SLICE_E3_300: 300, SLICE_E3_240: 240, SLICE_CAL_60: 60}


# --------------------------------------------------------------------------- #
# The two deterministic primitives                                             #
# --------------------------------------------------------------------------- #
def largest_remainder(total: int, weights: list) -> list:
    """Split ``total`` over ``weights`` proportionally, by largest remainder.

    Ties on the remainder go to the earlier position, which is why both callers
    fix their order (V1..V4 for classes, formal/terse/conversational for
    registers) instead of sorting by size.
    """
    mass = float(sum(weights))
    if mass <= 0.0:
        return [0] * len(weights)
    exact = [total * w / mass for w in weights]
    out = [int(x) for x in exact]
    remainder = total - sum(out)
    order = sorted(range(len(weights)), key=lambda i: (-(exact[i] - out[i]), i))
    for i in order[:remainder]:
        out[i] += 1
    return out


def draw_order(item_ids: list, cls: str, register: str, seed: int = SEED) -> list:
    """The frozen order of one ``(class, register)`` cell: a keyed sort, not an RNG."""
    salt = "l1-e3-sample|seed={}|class={}|register={}".format(seed, cls, register)

    def key(item_id):
        blob = "{}|{}".format(salt, item_id).encode("utf-8")
        return (hashlib.sha256(blob).hexdigest(), item_id)

    return sorted(item_ids, key=key)


# --------------------------------------------------------------------------- #
# The draw                                                                     #
# --------------------------------------------------------------------------- #
def class_targets(v_total: int, per_refusal: int, sizes: dict) -> dict:
    """Per-class targets for one slice size, proportional to the suite."""
    split = largest_remainder(v_total, [sizes[c] for c in V_CLASSES])
    out = dict(zip(V_CLASSES, split))
    for cls in R_CLASSES:
        out[cls] = per_refusal
    return out


def cell_targets(targets: dict, register_sizes: dict) -> dict:
    """``(class, register) -> count``, register-proportional within each class."""
    out = {}
    for cls, target in targets.items():
        weights = [register_sizes[cls][reg] for reg in REGISTERS]
        for reg, n in zip(REGISTERS, largest_remainder(target, weights)):
            out[(cls, reg)] = n
    return out


def build_slices(rows: list, seed: int = SEED) -> dict:
    """Draw all three slices from the suite rows; everything else reads this."""
    by_id = {r["item_id"]: r for r in rows}
    pools: dict = {}
    sizes: dict = {}
    register_sizes: dict = {}
    for cls in V_CLASSES + R_CLASSES:
        members = [r for r in rows if r["primary_class"] == cls]
        sizes[cls] = len(members)
        register_sizes[cls] = {
            reg: sum(1 for r in members if r["register"] == reg) for reg in REGISTERS
        }
        for reg in REGISTERS:
            ids = [r["item_id"] for r in members if r["register"] == reg]
            pools[(cls, reg)] = draw_order(ids, cls, reg, seed)

    proportional_300 = class_targets(120, 30, sizes)
    if proportional_300 != FROZEN_300:
        raise SystemExit(
            "REFUSING TO EMIT: the frozen E3-300 targets {} are not the suite's own "
            "proportional split {}; the freeze and the suite disagree.".format(
                FROZEN_300, proportional_300
            )
        )

    plans = {
        SLICE_E3_300: FROZEN_300,
        SLICE_E3_240: class_targets(FALLBACK_240[0], FALLBACK_240[1], sizes),
        SLICE_CAL_60: class_targets(CALIBRATION_60[0], CALIBRATION_60[1], sizes),
    }
    cells = {name: cell_targets(plan, register_sizes) for name, plan in plans.items()}

    # The prefix property is what makes the fallback safe; assert it rather than
    # trust the arithmetic, because it is the arithmetic that could change.
    for smaller, bigger in ((SLICE_E3_240, SLICE_E3_300), (SLICE_CAL_60, SLICE_E3_240)):
        for key, n in cells[smaller].items():
            if n > cells[bigger][key]:
                raise SystemExit(
                    "REFUSING TO EMIT: cell {} asks for {} items in {} but only {} in "
                    "{}; the smaller slice would not be a subset.".format(
                        key, n, smaller, cells[bigger][key], bigger
                    )
                )

    out = {"cells": cells, "targets": plans, "sizes": sizes,
           "register_sizes": register_sizes, "slices": {}, "detail": {}}
    for name in SLICE_NAMES:
        violations, twins, refusals, detail = [], [], [], []
        for cls in V_CLASSES:
            for reg in REGISTERS:
                take = pools[(cls, reg)][: cells[name][(cls, reg)]]
                for item_id in take:
                    twin_id = by_id[item_id]["twin_id"]
                    if not twin_id or twin_id not in by_id:
                        raise SystemExit(
                            "REFUSING TO EMIT: violation {} has no matched benign twin "
                            "in the suite; the McNemar pairs would not be exact.".format(
                                item_id
                            )
                        )
                    violations.append(item_id)
                    twins.append(twin_id)
                detail.append({"slice": name, "class": cls, "register": reg,
                               "drawn": len(take), "pool": len(pools[(cls, reg)])})
        for cls in R_CLASSES:
            for reg in REGISTERS:
                take = pools[(cls, reg)][: cells[name][(cls, reg)]]
                refusals.extend(take)
                detail.append({"slice": name, "class": cls, "register": reg,
                               "drawn": len(take), "pool": len(pools[(cls, reg)])})
        item_ids = violations + twins + refusals
        if len(set(item_ids)) != len(item_ids):
            raise SystemExit(
                "REFUSING TO EMIT: slice {} draws an item twice; a twin was also drawn "
                "as a violation, which no suite composition should allow.".format(name)
            )
        if len(item_ids) != SLICE_SIZES[name]:
            raise SystemExit(
                "REFUSING TO EMIT: slice {} came out at {} items, not the frozen "
                "{}".format(name, len(item_ids), SLICE_SIZES[name])
            )
        out["slices"][name] = {
            "n": len(item_ids),
            "n_violations": len(violations),
            "n_twins": len(twins),
            "n_refusal": len(refusals),
            "sha256": list_sha256(item_ids),
            "item_ids": item_ids,
        }
        out["detail"][name] = detail
    return out


def list_sha256(item_ids) -> str:
    """SHA-256 over the canonical JSON of an id list: the slice's identity."""
    blob = json.dumps(list(item_ids), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


# --------------------------------------------------------------------------- #
# Reading the emitted file back                                                #
# --------------------------------------------------------------------------- #
DEFAULT_OUT = sg.CODE_DIR.parent / "results" / "e3_sample" / "e3_slice.json"


def load_slice(name: str = SLICE_E3_300, path=None, rows=None) -> list:
    """The item ids of one slice, recomputed and checked against the file.

    The draw is a pure function of the suite, so the ids are always recomputed
    here; the file, when present, is used as an independent witness and a
    mismatch is fatal.  A runner therefore cannot silently drift from the slice
    that was reviewed.
    """
    if name not in SLICE_NAMES:
        raise KeyError("unknown slice {!r}; available: {}".format(name, list(SLICE_NAMES)))
    rows = sg.load_suite() if rows is None else rows
    built = build_slices(rows)["slices"][name]
    path = Path(DEFAULT_OUT if path is None else path)
    if path.exists():
        with open(path, "r", encoding="utf-8") as fh:
            emitted = json.load(fh)
        recorded = (emitted.get("slices") or {}).get(name)
        if recorded is None:
            raise SystemExit(
                "REFUSING TO RUN: {} holds no slice {!r}; re-run scripts/e3_sample.py"
                .format(path, name)
            )
        if recorded["sha256"] != built["sha256"]:
            raise SystemExit(
                "REFUSING TO RUN: slice {} on disk has sha256 {} but the suite draws "
                "{}; the emitted slice and the suite no longer agree.".format(
                    name, recorded["sha256"], built["sha256"]
                )
            )
    return list(built["item_ids"])


# --------------------------------------------------------------------------- #
# Reporting                                                                    #
# --------------------------------------------------------------------------- #
def report(built: dict, inputs: dict) -> str:
    lines = []
    add = lines.append
    add("E3 ITEM SLICE  (seed {}, {}, suite sha256 {})".format(
        SEED, SAMPLE_VERSION, inputs["suite_sha256"][:16]))
    add("")
    add("  {:<10s} {:>6s} {:>11s} {:>7s} {:>9s}  {}".format(
        "slice", "items", "violations", "twins", "refusal", "sha256 of the id list"))
    for name in SLICE_NAMES:
        s = built["slices"][name]
        add("  {:<10s} {:>6d} {:>11d} {:>7d} {:>9d}  {}".format(
            name, s["n"], s["n_violations"], s["n_twins"], s["n_refusal"], s["sha256"]))
    add("")
    add("  per-cell draw (class x register), register-proportional within each class")
    add("  {:<6s} {:>7s} {:>7s} {:>7s} {:>16s} {:>9s} {:>9s} {:>9s}".format(
        "class", "E3-300", "E3-240", "CAL-60", "suite (F/T/C)", "F", "T", "C"))
    for cls in V_CLASSES + R_CLASSES:
        reg = built["register_sizes"][cls]
        add("  {:<6s} {:>7d} {:>7d} {:>7d} {:>16s} {:>9d} {:>9d} {:>9d}".format(
            cls,
            built["targets"][SLICE_E3_300][cls],
            built["targets"][SLICE_E3_240][cls],
            built["targets"][SLICE_CAL_60][cls],
            "{}/{}/{}".format(*[reg[r] for r in REGISTERS]),
            *[built["cells"][SLICE_E3_300][(cls, r)] for r in REGISTERS],
        ))
    add("")
    add("  the three slices nest: E3-CAL-60 subset of E3-240 subset of E3-300, because")
    add("  each is a prefix of the same per-cell draw order (asserted, not assumed).")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--print", dest="print_slice", default=None, choices=list(SLICE_NAMES),
                    help="print that slice's item ids, one per line, and write nothing")
    args = ap.parse_args()

    inputs = sg.assert_inputs()
    rows = sg.load_suite()
    built = build_slices(rows)

    if args.print_slice:
        for item_id in built["slices"][args.print_slice]["item_ids"]:
            print(item_id)
        return 0

    payload = {
        "version": SAMPLE_VERSION,
        "date": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "seed": SEED,
        "suite_path": str(sg.SUITE_PATH),
        "suite_sha256": inputs["suite_sha256"],
        "schema_sha256": inputs["schema_sha256"],
        "registers": list(REGISTERS),
        "draw": "violations first, twin closure, register-proportional within class; "
                "cell order is sha256('l1-e3-sample|seed=0|class=..|register=..|<id>')",
        "frozen_targets_E3_300": FROZEN_300,
        "suite_class_sizes": built["sizes"],
        "suite_register_sizes": {c: built["register_sizes"][c] for c in built["register_sizes"]},
        "cell_targets": {
            name: {"{}|{}".format(c, r): n for (c, r), n in cells.items()}
            for name, cells in built["cells"].items()
        },
        "cell_detail": built["detail"],
        "slices": {name: built["slices"][name] for name in SLICE_NAMES},
        "nesting": {
            "E3-240 subset of E3-300": set(built["slices"][SLICE_E3_240]["item_ids"])
            <= set(built["slices"][SLICE_E3_300]["item_ids"]),
            "E3-CAL-60 subset of E3-240": set(built["slices"][SLICE_CAL_60]["item_ids"])
            <= set(built["slices"][SLICE_E3_240]["item_ids"]),
        },
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=1, sort_keys=True))

    print(report(built, inputs))
    print("\n[e3s] written to {}".format(out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
