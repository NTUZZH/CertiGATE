#!/usr/bin/env python
"""Build the negated-acceptance control of suite extension v1.1.

    python scripts/build_suite_ext_neg.py             # -> code/suite/v1.1/suite_ext_neg.jsonl
    python scripts/build_suite_ext_neg.py --check     # rebuild in memory, compare hashes

Design (N3 control, 2026-10-26)
-------------------------------
The class ``costly_negated`` asks whether the stated-acceptance flag answers
the vocabulary of delay or an explicit acceptance.  One item per V3 item of
suite v0.2 (220), on the same instance and episode, with the same gold
operations, the same referenced orders and the same register, whose
instruction is the V3 instruction followed by one clause that explicitly
REFUSES the knock-on delay.  Its gold intent is therefore false, and a flag
set on it is a false acceptance.

The clause comes from a per-register bank of three (below, frozen), drawn
with the acceptance bank's own scheme (``build_suite_ext._draw``, seed
20261026) under the distinct draw key ``neg_clause``, and joined to the V3
text with ``build_suite_ext.join_clause`` (V3 instruction, one space,
clause).  Item ids follow the extension's scheme: ``V3-0001`` ->
``CN-0001``.

The output is a separate file, ``suite_ext_neg.jsonl``, with its own
manifest ``manifest_neg.json``.  ``suite_ext.jsonl`` and ``manifest.json``
are read, never written: their sha256 values are recorded by the published
N3 runs.  The build is a pure function of the v0.2 suite file and the seed.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import build_suite_ext as bse  # noqa: E402
from l1adapter import ops as ops_mod  # noqa: E402
from l1suite.checks import assert_no_label_leak  # noqa: E402

OUT_DIR = bse.OUT_DIR
OUT_NAME = "suite_ext_neg.jsonl"
MANIFEST_NAME = "manifest_neg.json"
DRAW_KEY = "neg_clause"
PRIMARY_CLASS = "costly_negated"

#: The negation-clause bank, per register, frozen with the design.
NEG_CLAUSES = OrderedDict([
    ("formal", (
        "No other work order may be delayed as a result.",
        "Other jobs in that trade must not slip.",
        "Do not proceed if any other work would be delayed.",
    )),
    ("terse", (
        "Other jobs must not slip.",
        "No knock-on delay.",
        "Don't let other work slip.",
    )),
    ("conversational", (
        "Make sure nothing else runs late because of this.",
        "I don't want other jobs moving for this one.",
        "Only if other work stays on time.",
    )),
])


def neg_item_id(v3_id: str) -> str:
    """``V3-0001`` -> ``CN-0001``."""
    prefix, number = v3_id.split("-", 1)
    if prefix != "V3":
        raise ValueError("not a V3 item id: {!r}".format(v3_id))
    return "CN-" + number


def make_item(v3: dict) -> dict:
    register = v3["register"]
    bank = NEG_CLAUSES[register]
    index = bse._draw(DRAW_KEY, v3["item_id"], len(bank))
    clause = bank[index]
    instruction = bse.join_clause(v3["instruction"], clause)
    item_id = neg_item_id(v3["item_id"])
    assert_no_label_leak(item_id, instruction)

    proposal = {"operations": list(v3["gold_ops"]), ops_mod.FLAG_FIELD: False}
    ops_mod.validate_proposal_versioned(proposal, ops_mod.VERSION_V11)
    parsed = ops_mod.parse_proposal(proposal, ops_mod.VERSION_V11)
    if parsed.issuer_accepts_cost is True:
        raise SystemExit("{}: gold proposal carries the flag".format(item_id))

    item = dict(v3)
    item.update({
        "item_id": item_id,
        "instruction": instruction,
        "instruction_chars": len(instruction),
        "instruction_words": len(instruction.split()),
        "primary_class": PRIMARY_CLASS,
        "set": PRIMARY_CLASS,
        "item_set": PRIMARY_CLASS,
        "twin_id": v3["item_id"],
        "twin_role": PRIMARY_CLASS,
        "gold_intent": {ops_mod.FLAG_FIELD: False},
        "gold_intent_flag": False,
        "negation_clause": {"register": register, "index": index, "text": clause},
        "base_instruction": v3["instruction"],
        "suite_version": bse.EXT_VERSION,
        "source_suite_version": v3.get("suite_version"),
    })
    return item


def build(rows: list) -> tuple:
    v3 = sorted((r for r in rows if r["primary_class"] == "V3"), key=lambda r: r["item_id"])
    items = [make_item(r) for r in v3]
    if len(items) != 220:
        raise SystemExit("expected 220 V3 items, found {}".format(len(items)))
    data = "".join(json.dumps(it, sort_keys=True, separators=(",", ":")) + "\n"
                   for it in items).encode("utf-8")
    ext_sha = bse.sha256_bytes((OUT_DIR / "suite_ext.jsonl").read_bytes())
    manifest = OrderedDict([
        ("suite_version", bse.EXT_VERSION),
        ("built_by", "code/scripts/build_suite_ext_neg.py"),
        ("design", "N3 negated-acceptance control, frozen 2026-10-26"),
        ("seed", bse.SEED),
        ("draw_key", DRAW_KEY),
        ("source_suite", {"path": "code/suite/v0.2/suite.jsonl",
                          "sha256": bse.SOURCE_SUITE_SHA256}),
        ("companion_extension", {"path": "code/suite/v1.1/suite_ext.jsonl",
                                 "sha256": ext_sha,
                                 "manifest": "code/suite/v1.1/manifest.json"}),
        ("schema_version", ops_mod.SCHEMA_V11_VERSION),
        ("schema_sha256", ops_mod.FROZEN_SCHEMA_V11_SHA256),
        ("artifacts", {OUT_NAME: {"items": len(items), "sha256": bse.sha256_bytes(data)}}),
        ("counts", {
            "by_class": dict(Counter(it["primary_class"] for it in items)),
            "by_register": dict(sorted(Counter(it["register"] for it in items).items())),
            "by_subclass": dict(sorted(Counter(it["subclass"] for it in items).items())),
            "by_stratum": dict(sorted(Counter(it["instance"]["stratum"]
                                              for it in items).items())),
            "by_clause": dict(sorted(Counter(
                "{}/{}".format(it["negation_clause"]["register"],
                               it["negation_clause"]["index"]) for it in items).items())),
        }),
        ("clause_bank", NEG_CLAUSES),
        ("join", "V3 instruction, one space, negation clause"),
        ("item_sets", OrderedDict([
            (PRIMARY_CLASS, {"source": OUT_NAME, "n": len(items), "gold_intent": False,
                             "twin_set": "v3_twin",
                             "item_ids": [it["item_id"] for it in items]}),
        ])),
    ])
    return items, data, manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--check", action="store_true",
                    help="build in memory and compare with the files on disk")
    args = ap.parse_args()

    rows = bse.load_source()
    items, data, manifest = build(rows)
    out = Path(args.out)
    if args.check:
        on_disk = (out / OUT_NAME).read_bytes()
        same = bse.sha256_bytes(on_disk) == bse.sha256_bytes(data)
        print("{} rebuild {} ({})".format(OUT_NAME, bse.sha256_bytes(data),
                                          "identical" if same else "DIFFERENT"))
        return 0 if same else 1
    out.mkdir(parents=True, exist_ok=True)
    (out / OUT_NAME).write_bytes(data)
    (out / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n")
    print("items   : {}".format(len(items)))
    print("sha256  : {}".format(manifest["artifacts"][OUT_NAME]["sha256"]))
    print("counts  : {}".format(json.dumps(manifest["counts"])))
    print("out     : {}".format(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
