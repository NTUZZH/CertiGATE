"""Counts, coverage, balance checks, and the ``stats.md`` the report quotes.

Two jobs.  :func:`verify_balance` asserts the properties the suite claims about
itself (the twin relation is a bijection, the benign set covers all seven
operations, building-scoped operations appear only where buildings exist, every
planned coverage cell is filled, per-class counts match the config).
:func:`build_tables` and :func:`render_stats` turn the records into the tables
the build report and the paper's suite section quote.
"""

from __future__ import annotations

import collections
import statistics

from .checks import SuiteBuildError
from .config import SuiteConfig
from .templates import FAMILIES

OP_TYPES = (
    "set_priority", "pin_next", "reorder", "reassign_window",
    "freeze", "unfreeze", "batch",
)
CLASSES = ("benign", "V1", "V2", "V3", "V4", "V5", "V6")


# --------------------------------------------------------------------------- #
# Balance checks                                                               #
# --------------------------------------------------------------------------- #
def expected_cells(config: SuiteConfig) -> set:
    """(op type, class, stratum) cells the plan says must be non-empty.

    Taken from the realised allocation rather than from the weights, so the
    check reads "every cell the plan actually asked for was filled" at any
    quota scale (a one-item quota lands in exactly one stratum).
    """
    from .generate import allocate

    cells = set()
    for q in config.pairs:
        fam = FAMILIES[q.family_id]
        for stratum in set(allocate(q.count, q.stratum_weights)):
            for op in fam.op_types:
                cells.add((op, fam.primary_class, stratum))
            for op in (fam.benign_op_types or fam.op_types):
                cells.add((op, "benign", stratum))
    return cells


def verify_balance(records, config: SuiteConfig) -> dict:
    """Raise unless every structural property the suite claims actually holds."""
    problems = []
    by_id = {r["item_id"]: r for r in records}

    # 1. twin relation is a bijection over V1-V4 and the benign set
    twinned = [r for r in records if r["primary_class"] in ("V1", "V2", "V3", "V4")]
    benign = [r for r in records if r["primary_class"] == "benign"]
    if len(twinned) != len(benign):
        problems.append(
            "twin counts differ: {} violations vs {} benign".format(len(twinned), len(benign))
        )
    seen = set()
    for r in twinned:
        t = r["twin_id"]
        if t not in by_id or by_id[t]["primary_class"] != "benign":
            problems.append("{}: twin {} missing or not benign".format(r["item_id"], t))
            continue
        if by_id[t]["twin_id"] != r["item_id"]:
            problems.append("{}: twin {} points back to {}".format(
                r["item_id"], t, by_id[t]["twin_id"]))
        if t in seen:
            problems.append("{}: benign twin {} used twice".format(r["item_id"], t))
        seen.add(t)
        if by_id[t]["instance"]["instance_id"] != r["instance"]["instance_id"]:
            problems.append("{}: twin sits on a different instance".format(r["item_id"]))
        if by_id[t]["variant_id"] != r["variant_id"]:
            problems.append("{}: twin uses a different surface variant".format(r["item_id"]))
        if by_id[t]["instruction"] == r["instruction"]:
            problems.append(
                "{}: twin {} carries the identical instruction, so the pair "
                "labels one message both ways".format(r["item_id"], t)
            )
        if r["mutation"].get("from") == r["mutation"].get("to"):
            problems.append("{}: the recorded mutation changes nothing".format(r["item_id"]))
    for r in benign:
        if r["twin_id"] not in by_id:
            problems.append("{}: benign item has no violation twin".format(r["item_id"]))

    # 2. benign covers all seven operations, and batch only where buildings exist
    benign_ops = collections.Counter()
    for r in benign:
        benign_ops.update(r["gold_op_types"])
    missing = [op for op in OP_TYPES if benign_ops[op] == 0]
    if missing:
        problems.append("benign set does not cover {}".format(missing))
    for r in records:
        uses_building = any(
            o["op"] == "batch"
            for o in r["gold_ops"] + r["trap_ops"] + r["literal_ops"]
        )
        if uses_building and r["instance"]["track"] != "replay":
            problems.append("{}: batch outside the replay stratum".format(r["item_id"]))

    # 3. per-class counts match the config
    want = collections.Counter()
    for q in config.pairs:
        want[FAMILIES[q.family_id].primary_class] += q.count
        want["benign"] += q.count
    for q in config.singles:
        want[FAMILIES[q.family_id].primary_class] += q.count
    got = collections.Counter(r["primary_class"] for r in records)
    for cls in sorted(set(want) | set(got)):
        if want[cls] != got[cls]:
            problems.append("class {}: planned {}, produced {}".format(cls, want[cls], got[cls]))

    # 4. every planned coverage cell is filled
    actual = set()
    for r in records:
        for op in r["op_types"]:
            actual.add((op, r["primary_class"], r["instance"]["stratum"]))
    empty = sorted(expected_cells(config) - actual)
    if empty:
        problems.append("planned coverage cells with no item: {}".format(empty[:8]))

    # 5. label discipline and ground-truth shape
    for r in records:
        if r["primary_class"] in ("V1", "V5", "V6") and r["gold_ops"] and r["primary_class"] != "V6":
            problems.append("{}: refusal class carries gold operations".format(r["item_id"]))
        if r["primary_class"] == "V2" and not r["literal_ops"]:
            problems.append("{}: V2 item has no literal operations".format(r["item_id"]))
        if r["primary_class"] == "V4" and not r["trap_ops"]:
            problems.append("{}: V4 item has no trap operations".format(r["item_id"]))
        if r["primary_class"] in ("V1", "V2") and not r["expected_violation"]:
            problems.append("{}: no expected violation code".format(r["item_id"]))

    if problems:
        raise SuiteBuildError("balance checks failed:\n  - " + "\n  - ".join(problems[:20]))
    return {"pairs": len(twinned), "benign_op_coverage": dict(benign_ops)}


# --------------------------------------------------------------------------- #
# Tables                                                                       #
# --------------------------------------------------------------------------- #
def build_tables(records) -> dict:
    by_set = collections.Counter(r["set"] for r in records)
    by_class = collections.Counter(r["primary_class"] for r in records)
    by_subclass = collections.Counter((r["primary_class"], r["subclass"]) for r in records)
    by_stratum = collections.Counter(r["instance"]["stratum"] for r in records)
    class_stratum = collections.Counter(
        (r["primary_class"], r["instance"]["stratum"]) for r in records
    )
    register = collections.Counter(r["register"] for r in records)
    queue = collections.Counter((r["instance"]["stratum"], r["queue_state"]) for r in records)
    coverage = collections.Counter()
    for r in records:
        for op in r["op_types"]:
            coverage[(op, r["primary_class"], r["instance"]["stratum"])] += 1
    benign_ops = collections.Counter()
    for r in records:
        if r["primary_class"] == "benign":
            benign_ops.update(r["gold_op_types"])
    n_ops = collections.Counter(r["n_ops"] for r in records if r["primary_class"] == "benign")

    v3 = [r for r in records if r["primary_class"] == "V3"]
    v3_rows = {}
    for sub in sorted({r["subclass"] for r in v3}):
        vals = [r["badness"] for r in v3 if r["subclass"] == sub]
        v3_rows[sub] = {
            "n": len(vals),
            "positive": sum(1 for v in vals if v > 1e-9),
            "median": round(statistics.median(vals), 4) if vals else 0.0,
            "max": round(max(vals), 4) if vals else 0.0,
        }
    benign_badness = [r["badness"] for r in records if r["primary_class"] == "benign"]

    v4 = [r for r in records if r["primary_class"] == "V4"]
    v4_rows = {}
    for sub in sorted({r["subclass"] for r in v4}):
        rows = [r for r in v4 if r["subclass"] == sub]
        v4_rows[sub] = {
            "n": len(rows),
            "quality_visible": sum(1 for r in rows if r["quality_visible_candidate"]),
            "schedule_differs": sum(1 for r in rows if r["metrics"].get("schedule_differs")),
            "median_delta": round(
                statistics.median(
                    [r["metrics"]["badness_trap_minus_gold"] for r in rows]
                ), 4
            ) if rows else 0.0,
        }

    v1_split = collections.Counter(
        r["v1_decodability"] for r in records if r["primary_class"] == "V1"
    )
    codes = collections.Counter(
        r["expected_violation"] for r in records if r["expected_violation"]
    )
    chars = [r["instruction_chars"] for r in records]
    words = [r["instruction_words"] for r in records]
    length_by_register = {}
    for reg in sorted(register):
        vals = [r["instruction_words"] for r in records if r["register"] == reg]
        length_by_register[reg] = {
            "n": len(vals),
            "median_words": round(statistics.median(vals), 1),
            "min": min(vals),
            "max": max(vals),
        }
    return {
        "counts": {
            "total": len(records),
            "by_set": dict(by_set),
            "by_class": dict(by_class),
            "by_subclass": {"{}/{}".format(c, s): n for (c, s), n in sorted(by_subclass.items())},
            "by_stratum": dict(by_stratum),
        },
        "class_stratum": class_stratum,
        "register": register,
        "queue": queue,
        "coverage": coverage,
        "benign_ops": benign_ops,
        "benign_n_ops": n_ops,
        "v3": v3_rows,
        "benign_badness": {
            "median": round(statistics.median(benign_badness), 6) if benign_badness else 0.0,
            "positive": sum(1 for v in benign_badness if v > 1e-9),
            "n": len(benign_badness),
        },
        "v4": v4_rows,
        "v1_split": v1_split,
        "codes": codes,
        "length": {
            "chars": {"min": min(chars), "median": statistics.median(chars), "max": max(chars)},
            "words": {"min": min(words), "median": statistics.median(words), "max": max(words)},
            "by_register": length_by_register,
        },
    }


def _table(header, rows) -> str:
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join(["---"] * len(header)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def render_stats(records, t, config) -> str:
    strata = [s.key for s in config.strata]
    parts = ["# L1 violation suite {} - statistics".format(config.suite_version), ""]
    parts.append("Total items: **{}**.  Config fingerprint `{}`.".format(
        t["counts"]["total"], config.fingerprint()[:16]))
    parts.append("")

    parts.append("## Items per set and class")
    parts.append(_table(
        ["set", "class"] + strata + ["total"],
        [
            [
                {"benign": "benign", "V1": "violation", "V2": "violation", "V3": "violation",
                 "V4": "violation", "V5": "ambiguity", "V6": "adversarial"}[c],
                c,
            ]
            + [t["class_stratum"].get((c, s), 0) for s in strata]
            + [t["counts"]["by_class"].get(c, 0)]
            for c in CLASSES
        ],
    ))
    parts.append("")

    parts.append("## Items per subclass")
    parts.append(_table(
        ["class/subclass", "n"],
        [[k, v] for k, v in sorted(t["counts"]["by_subclass"].items())],
    ))
    parts.append("")

    parts.append("## Coverage matrix (operation type x class x stratum)")
    parts.append("Cells are item counts; `.` means the combination is not "
                 "generated (see the report for which combinations are impossible).")
    rows = []
    for op in OP_TYPES:
        for cls in CLASSES:
            counts = [t["coverage"].get((op, cls, s), 0) for s in strata]
            if not any(counts):
                continue
            rows.append([op, cls] + [c if c else "." for c in counts])
    parts.append(_table(["operation", "class"] + strata, rows))
    parts.append("")

    parts.append("## Benign set: operation coverage and operation count")
    parts.append(_table(
        ["operation", "items"],
        [[op, t["benign_ops"].get(op, 0)] for op in OP_TYPES],
    ))
    parts.append("")
    parts.append(_table(
        ["operations per item", "items"],
        [[k, t["benign_n_ops"][k]] for k in sorted(t["benign_n_ops"])],
    ))
    parts.append("")

    parts.append("## Expected violation codes (V1, V2)")
    parts.append(_table(
        ["code", "items"], [[k, v] for k, v in sorted(t["codes"].items())]
    ))
    parts.append("")
    parts.append("V1 decoder split: " + ", ".join(
        "{} {}".format(k, v) for k, v in sorted(t["v1_split"].items())
    ))
    parts.append("")

    v3_total = sum(v["n"] for v in t["v3"].values())
    v3_pos = sum(v["positive"] for v in t["v3"].values())
    parts.append("## V3 candidates: schedule degradation by subclass")
    parts.append("`badness` is weighted tardiness on the adjusted instance under the "
                 "item's operations, minus the same instance dispatched with nothing "
                 "imposed, in weighted business hours. It measures schedule degradation "
                 "rather than movement of the objective's own fields, which is what an "
                 "adjusted-instance certificate can see. Certified severity is assigned "
                 "in the guard pass.")
    parts.append(_table(
        ["subclass", "n", "badness > 0", "median", "max"],
        [[k, v["n"], v["positive"], v["median"], v["max"]] for k, v in sorted(t["v3"].items())],
    ))
    parts.append("")
    parts.append("**V3 positive-badness share: {}/{} = {:.1%}.**".format(
        v3_pos, v3_total, v3_pos / max(v3_total, 1)))
    parts.append("")
    parts.append("Benign twins for comparison: {} of {} degrade the schedule at all, "
                 "median {}.".format(
                     t["benign_badness"]["positive"], t["benign_badness"]["n"],
                     t["benign_badness"]["median"]))
    parts.append("")

    parts.append("## V4 traps: provisional quality separation by trap type")
    parts.append("`median delta` is badness(trap) minus badness(gold). A trap that only "
                 "moves the objective's own fields scores zero by construction and is "
                 "caught by the matched twin alone, which is a reported finding rather "
                 "than a defect.")
    parts.append(_table(
        ["trap type", "n", "quality-visible candidates", "schedule differs", "median delta"],
        [[k, v["n"], v["quality_visible"], v["schedule_differs"], v["median_delta"]]
         for k, v in sorted(t["v4"].items())],
    ))
    parts.append("")

    parts.append("## Surface form")
    parts.append(_table(
        ["register", "items", "median words", "min", "max"],
        [[k, v["n"], v["median_words"], v["min"], v["max"]]
         for k, v in sorted(t["length"]["by_register"].items())],
    ))
    parts.append("")
    parts.append("Instruction length over the whole suite: {} to {} characters "
                 "(median {}), {} to {} words (median {}).".format(
                     t["length"]["chars"]["min"], t["length"]["chars"]["max"],
                     t["length"]["chars"]["median"], t["length"]["words"]["min"],
                     t["length"]["words"]["max"], t["length"]["words"]["median"]))
    parts.append("")

    parts.append("## Queue state of the targeted trade")
    qs = sorted({q for (_, q) in t["queue"]})
    parts.append(_table(
        ["stratum"] + qs,
        [[s] + [t["queue"].get((s, q), 0) for q in qs] for s in strata],
    ))
    parts.append("")
    return "\n".join(parts)


__all__ = ["verify_balance", "build_tables", "render_stats", "expected_cells", "OP_TYPES", "CLASSES"]
