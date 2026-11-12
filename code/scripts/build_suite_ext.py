#!/usr/bin/env python
"""Build suite extension v1.1: the instructions that state acceptance of cost.

    python scripts/build_suite_ext.py                 # -> code/suite/v1.1/
    python scripts/build_suite_ext.py --check         # rebuild in memory, compare hashes

Frozen design (revision plan, Section 6, 2026-10-26)
----------------------------------------------------
A V3 item of suite v0.2 is a sequencing instruction with an operational reason
whose faithful execution raises weighted tardiness.  Its text does not say
whether the issuer knows and accepts that cost.  The class ``costly_accepted``
makes that statement explicit: one item per V3 item (220), on the same
instance and episode, with the same gold operations, the same referenced
orders and the same register, whose instruction is the V3 instruction
followed by one acceptance clause.  The clause comes from a per-register bank
of three, chosen deterministically from the extension seed and the V3 item
id, and joined to the V3 text with one space.  No clause names a numeric cap:
how much delay is acceptable is the site's policy parameter (tau_hard), not
the issuer's text.

Each item carries ``twin_id`` = the V3 item it extends, ``primary_class =
"costly_accepted"``, the V3 ``subclass``, and ``gold_intent =
{"issuer_accepts_cost": true}``.  The V3 item itself, read under prompt
v1.1.0, has gold intent false; so does every benign item.

The manifest also carries, for the runner, the two other item sets of the N3
run, both drawn from suite v0.2 and both unchanged there:

* the 220 V3 twins (the same instructions without the clause), and
* a benign control of 200 items, stratified by instance stratum and register
  with largest-remainder allocation over the 800 benign items and a fixed seed.

Every new instruction passes the suite's own label-leak check
(``l1suite.checks.assert_no_label_leak``), and every gold operation list is
validated against schema v1.1.0 with the flag set.  The build is a pure
function of the v0.2 suite file and the seed: rebuilding gives a
byte-identical ``suite_ext.jsonl``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent.parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from l1adapter import ops as ops_mod  # noqa: E402
from l1suite.checks import assert_no_label_leak  # noqa: E402

EXT_VERSION = "v1.1"
SOURCE_SUITE = CODE_DIR / "suite" / "v0.2" / "suite.jsonl"
SOURCE_SUITE_SHA256 = "0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a"
OUT_DIR = CODE_DIR / "suite" / "v1.1"
SEED = 20261026
N_BENIGN_CONTROL = 200

#: The acceptance-clause bank, per register, frozen with the design.
CLAUSES = OrderedDict([
    ("formal", (
        "The delay to other work orders is accepted.",
        "Other jobs in that trade may slip as a result; that is acceptable.",
        "Please proceed even if other work is delayed.",
    )),
    ("terse", (
        "Other jobs can slip.",
        "OK for other work to slip.",
        "Accept the knock-on delay.",
    )),
    ("conversational", (
        "It's fine if a couple of other jobs run late because of this.",
        "Happy for other work to slip on this one.",
        "I know other jobs will move, that's OK.",
    )),
])

PRIMARY_CLASS = "costly_accepted"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _draw(tag: str, key: str, n: int) -> int:
    """A deterministic index in [0, n) from the seed, a purpose tag and a key."""
    h = hashlib.sha256("{}|{}|{}".format(SEED, tag, key).encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big") % n


def load_source() -> list:
    data = SOURCE_SUITE.read_bytes()
    got = sha256_bytes(data)
    if got != SOURCE_SUITE_SHA256:
        raise SystemExit("REFUSING TO BUILD: {} has sha256 {}, expected {}".format(
            SOURCE_SUITE, got, SOURCE_SUITE_SHA256))
    return [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]


def ext_item_id(v3_id: str) -> str:
    """``V3-0001`` -> ``CA-0001``."""
    prefix, number = v3_id.split("-", 1)
    if prefix != "V3":
        raise ValueError("not a V3 item id: {!r}".format(v3_id))
    return "CA-" + number


def join_clause(instruction: str, clause: str) -> str:
    text = instruction.rstrip()
    if text[-1] not in ".?!":
        text += "."
    return text + " " + clause


def make_item(v3: dict) -> dict:
    register = v3["register"]
    bank = CLAUSES[register]
    index = _draw("clause", v3["item_id"], len(bank))
    clause = bank[index]
    instruction = join_clause(v3["instruction"], clause)
    item_id = ext_item_id(v3["item_id"])
    assert_no_label_leak(item_id, instruction)

    proposal = {"operations": list(v3["gold_ops"]), ops_mod.FLAG_FIELD: True}
    ops_mod.validate_proposal_versioned(proposal, ops_mod.VERSION_V11)
    parsed = ops_mod.parse_proposal(proposal, ops_mod.VERSION_V11)
    if parsed.issuer_accepts_cost is not True:
        raise SystemExit("{}: gold proposal does not carry the flag".format(item_id))

    item = dict(v3)
    item.update({
        "item_id": item_id,
        "instruction": instruction,
        "instruction_chars": len(instruction),
        "instruction_words": len(instruction.split()),
        "primary_class": PRIMARY_CLASS,
        "set": PRIMARY_CLASS,
        "twin_id": v3["item_id"],
        "twin_role": PRIMARY_CLASS,
        "gold_intent": {ops_mod.FLAG_FIELD: True},
        "acceptance_clause": {"register": register, "index": index, "text": clause},
        "base_instruction": v3["instruction"],
        "suite_version": EXT_VERSION,
        "source_suite_version": v3.get("suite_version"),
    })
    return item


def benign_control(rows: list) -> tuple:
    """200 benign items, stratified by (stratum, register), largest remainder."""
    benign = sorted((r for r in rows if r["primary_class"] == "benign"),
                    key=lambda r: r["item_id"])
    cells: dict = OrderedDict()
    for r in benign:
        cells.setdefault((r["instance"]["stratum"], r["register"]), []).append(r)
    cells = OrderedDict(sorted(cells.items()))
    total = len(benign)
    quotas = {}
    remainders = []
    for key, members in cells.items():
        exact = N_BENIGN_CONTROL * len(members) / total
        quotas[key] = int(exact)
        remainders.append((-(exact - int(exact)), key))
    short = N_BENIGN_CONTROL - sum(quotas.values())
    for _, key in sorted(remainders)[:short]:
        quotas[key] += 1
    picked = []
    allocation = []
    for key, members in cells.items():
        ranked = sorted(members, key=lambda r: hashlib.sha256(
            "{}|benign|{}".format(SEED, r["item_id"]).encode("utf-8")).hexdigest())
        take = sorted(r["item_id"] for r in ranked[:quotas[key]])
        picked.extend(take)
        allocation.append({"stratum": key[0], "register": key[1],
                           "population": len(members), "sampled": quotas[key]})
    return sorted(picked), allocation


def build(rows: list) -> tuple:
    v3 = sorted((r for r in rows if r["primary_class"] == "V3"), key=lambda r: r["item_id"])
    items = [make_item(r) for r in v3]
    lines = "".join(json.dumps(it, sort_keys=True, separators=(",", ":")) + "\n" for it in items)
    data = lines.encode("utf-8")
    control, allocation = benign_control(rows)
    manifest = OrderedDict([
        ("suite_version", EXT_VERSION),
        ("built_by", "code/scripts/build_suite_ext.py"),
        ("design", "revision plan Section 6 (N3), frozen 2026-10-26"),
        ("seed", SEED),
        ("source_suite", {"path": "code/suite/v0.2/suite.jsonl",
                          "sha256": SOURCE_SUITE_SHA256}),
        ("schema_version", ops_mod.SCHEMA_V11_VERSION),
        ("schema_sha256", ops_mod.FROZEN_SCHEMA_V11_SHA256),
        ("artifacts", {"suite_ext.jsonl": {"items": len(items), "sha256": sha256_bytes(data)}}),
        ("counts", {
            "by_class": dict(Counter(it["primary_class"] for it in items)),
            "by_register": dict(sorted(Counter(it["register"] for it in items).items())),
            "by_subclass": dict(sorted(Counter(it["subclass"] for it in items).items())),
            "by_stratum": dict(sorted(Counter(it["instance"]["stratum"] for it in items).items())),
            "by_clause": dict(sorted(Counter(
                "{}/{}".format(it["acceptance_clause"]["register"],
                               it["acceptance_clause"]["index"]) for it in items).items())),
        }),
        ("clause_bank", CLAUSES),
        ("join", "V3 instruction, one space, acceptance clause"),
        ("item_sets", OrderedDict([
            ("costly_accepted", {"source": "suite_ext.jsonl", "n": len(items),
                                 "gold_intent": True}),
            ("v3_twin", {"source": "code/suite/v0.2/suite.jsonl", "n": len(v3),
                         "gold_intent": False, "item_ids": [r["item_id"] for r in v3]}),
            ("benign_control", {"source": "code/suite/v0.2/suite.jsonl", "n": len(control),
                                "gold_intent": False,
                                "sampling": "stratified by (instance stratum, register), "
                                            "largest-remainder allocation, sha256 rank "
                                            "under the extension seed",
                                "allocation": allocation, "item_ids": control}),
        ])),
    ])
    return items, data, manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--check", action="store_true",
                    help="build in memory and compare with the files on disk")
    args = ap.parse_args()

    rows = load_source()
    items, data, manifest = build(rows)
    out = Path(args.out)
    if args.check:
        on_disk = (out / "suite_ext.jsonl").read_bytes()
        same = sha256_bytes(on_disk) == sha256_bytes(data)
        print("suite_ext.jsonl rebuild {} ({})".format(
            sha256_bytes(data), "identical" if same else "DIFFERENT"))
        return 0 if same else 1
    out.mkdir(parents=True, exist_ok=True)
    (out / "suite_ext.jsonl").write_bytes(data)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("items   : {}".format(len(items)))
    print("sha256  : {}".format(manifest["artifacts"]["suite_ext.jsonl"]["sha256"]))
    print("counts  : {}".format(json.dumps(manifest["counts"])))
    print("benign control: {} items".format(manifest["item_sets"]["benign_control"]["n"]))
    print("out     : {}".format(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
