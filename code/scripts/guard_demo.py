#!/usr/bin/env python
"""End-to-end demonstration on one real instance, three proposals, three arms.

Three hand-written proposals stand in for three model outputs on the same
dispatcher instruction set:

  P1 CLEAN              a sensible escalation of one overdue order
  P2 INFEASIBLE         a precedence cycle plus a trade that does not match
  P3 FEASIBLE BUT POOR  a legal reordering that parks the most urgent order
                        behind the latest-released order of its own trade

Each is run through UNGUARDED, G_FEAS and G_CERT, and every proposal is written
to a JSONL log and replayed offline to show that the replayed verdict is the
verdict.  The identifiers are picked from the instance itself and printed, so
the run is reproducible and the reader can check the choice.

Run::

    python scripts/guard_demo.py
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from l1adapter import dispatch, evaluate, instances  # noqa: E402
from l1guard import G_CERT, G_FEAS, UNGUARDED, evaluate_proposal  # noqa: E402
from l1guard.logging import ProposalLog, ProposalRecord, prompt_hash  # noqa: E402
from l1guard.replay import rerun  # noqa: E402

ARMS = (UNGUARDED, G_FEAS, G_CERT)


def pick_targets(inst) -> dict:
    """Deterministic, explainable choices from the instance's own data."""
    orders = inst["work_orders"]
    urgent = min(
        (w for w in orders if int(w["priority"]) == 1),
        key=lambda w: (float(w["due_bh"]), w["id"]),
    )
    same_trade = [w for w in orders if w["trade"] == urgent["trade"] and w["id"] != urgent["id"]]
    latest = max(same_trade, key=lambda w: (float(w["release_bh"]), w["id"]))
    other_trade = min(
        (w for w in orders if w["trade"] != urgent["trade"]),
        key=lambda w: (float(w["due_bh"]), w["id"]),
    )
    routine = max(
        (w for w in orders if int(w["priority"]) == 4),
        key=lambda w: (float(w["p_bh"]), w["id"]),
    )
    return {"urgent": urgent, "latest": latest, "other": other_trade, "routine": routine}


def proposals(t: dict):
    urgent, latest, other, routine = t["urgent"], t["latest"], t["other"], t["routine"]
    return [
        (
            "P1 CLEAN",
            "Work order {} is the most urgent job on the board; put the {} crew on it "
            "next.".format(urgent["id"], urgent["trade"]),
            {
                "operations": [
                    {"op": "set_priority", "order_id": urgent["id"], "priority_class": 1},
                    {"op": "pin_next", "order_id": urgent["id"], "trade": urgent["trade"]},
                ]
            },
        ),
        (
            "P2 INFEASIBLE",
            "Do {} before {}, and {} before {}, and send the {} crew to {}.".format(
                urgent["id"], latest["id"], latest["id"], urgent["id"],
                other["trade"], urgent["id"],
            ),
            {
                "operations": [
                    {"op": "reorder", "order_id": urgent["id"], "relation": "before",
                     "ref_order_id": latest["id"]},
                    {"op": "reorder", "order_id": latest["id"], "relation": "before",
                     "ref_order_id": urgent["id"]},
                    {"op": "pin_next", "order_id": urgent["id"], "trade": other["trade"]},
                ]
            },
        ),
        (
            "P3 FEASIBLE BUT POOR",
            "Hold {} until {} has started, and drop the big routine job {} to the "
            "lowest class.".format(urgent["id"], latest["id"], routine["id"]),
            {
                "operations": [
                    {"op": "reorder", "order_id": urgent["id"], "relation": "after",
                     "ref_order_id": latest["id"]},
                    {"op": "set_priority", "order_id": routine["id"], "priority_class": 4},
                ]
            },
        ),
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--campus", type=int, default=9)
    ap.add_argument("--track", default="storm2")
    ap.add_argument("--size", default=None)
    ap.add_argument("--index", type=int, default=0)
    ap.add_argument("--rule", default="atc")
    args = ap.parse_args()

    path = instances.list_instances(args.campus, args.track, args.size)[args.index]
    inst = instances.load_instance(path)
    baseline = dispatch.dispatch_baseline(inst, args.rule, seed=0)
    base_wwt = evaluate.wwt(inst, baseline)

    print("=" * 100)
    print("L1 GUARD DEMONSTRATION")
    print("=" * 100)
    print("instance      : {}".format(path))
    print("               {} work orders, {} technicians, {} trades".format(
        len(inst["work_orders"]), len(inst["technicians"]), len(inst["trades"])))
    print("rule / seed   : {} / 0".format(args.rule))
    print("baseline WWT  : {:.4f} weighted business hours (the as-is schedule)".format(base_wwt))
    print("guard configs : {}".format(", ".join(c.name for c in ARMS)))
    print("tau           : {} (PROVISIONAL; the published value comes from the E2 sweep)"
          .format(G_CERT.tau))
    print("schema        : {} sha256 {}".format(
        __import__("l1adapter").ops.SCHEMA_VERSION,
        __import__("l1guard").SCHEMA_HASH[:16] + "...",
    ))

    targets = pick_targets(inst)
    print("\ntargets picked from the instance")
    for name, wo in targets.items():
        print(
            "  {:<8s} {:<8s} trade {:<5s} p={:6.3f} bh  release={:8.3f}  due={:8.3f}  "
            "class {}  w={:.0f}".format(
                name, wo["id"], wo["trade"], float(wo["p_bh"]), float(wo["release_bh"]),
                float(wo["due_bh"]), wo["priority"], float(wo["weight"])
            )
        )

    log_dir = Path(tempfile.mkdtemp(prefix="l1demo-"))
    log = ProposalLog(log_dir / "demo.jsonl")
    rows = []
    for label, instruction, proposal in proposals(targets):
        # A model emits text, so the demo hands the guard text: the logged raw
        # output and the live input are then the same object, which is what
        # makes the replay comparison meaningful.
        raw = json.dumps(proposal)
        print("\n" + "-" * 100)
        print("{}".format(label))
        print('  instruction : "{}"'.format(instruction))
        print("  operations  :")
        for op in proposal["operations"]:
            print("      {}".format(op))
        for cfg in ARMS:
            verdict = evaluate_proposal(inst, raw, cfg, frozen_seed=())
            codes = ", ".join(
                "{}[{}]".format(f.code, "" if f.op_index is None else f.op_index)
                for f in verdict.findings
            ) or "none"
            print("  {:<10s} -> {:<26s} findings: {}".format(
                cfg.name, verdict.terminal, codes))
            if verdict.certificate is not None:
                print("               certificate {}".format(verdict.certificate.tuple_str()))
            if verdict.objective is not None:
                print(
                    "               executed WWT {:.4f} bh (adjusted fields), {:.4f} bh "
                    "(original fields), referee feasible={}".format(
                        verdict.objective["wwt_adjusted_bh"],
                        verdict.objective["wwt_original_bh"],
                        verdict.objective["feasible"],
                    )
                )
            print("               stage times ms: {}".format(
                {k: round(v, 3) for k, v in verdict.timings_ms.items()}))
            rows.append((label, cfg.name, verdict))
            if cfg is G_CERT:
                record = ProposalRecord(
                    instruction_id=label.split()[0],
                    instance_id=inst["meta"]["id"],
                    instance_path=str(path),
                    model="hand-written",
                    mode="M_free",
                    prompt_hash=prompt_hash("demo", instruction),
                    raw_output=raw,
                    rule=args.rule,
                    seeds={"llm": None, "dispatch": 0},
                ).attach_verdict(verdict)
                log.append(record)

    print("\n" + "=" * 100)
    print("SUMMARY  (terminal state per proposal per arm)")
    print("=" * 100)
    print("{:<24s} {:<12s} {:<26s} {:>12s} {:>10s}".format(
        "proposal", "arm", "terminal", "obj bh", "gap"))
    for label, arm, verdict in rows:
        obj = "" if verdict.objective is None else "{:.4f}".format(
            verdict.objective["wwt_adjusted_bh"])
        gap = "" if verdict.certificate is None else "{:.4f}".format(verdict.certificate.gap)
        print("{:<24s} {:<12s} {:<26s} {:>12s} {:>10s}".format(label, arm, verdict.terminal,
                                                               obj, gap))

    print("\nREPLAY  (the same three proposals, re-derived from the log with no model)")
    for cfg in ARMS:
        replayed = rerun(log.path, cfg)
        print("  {:<10s} {}".format(cfg.name, [v.terminal for v in replayed]))
    direct = [v for label, arm, v in rows if arm == "G_CERT"]
    replayed = rerun(log.path, G_CERT)
    same = all(a.fingerprint() == b.fingerprint() for a, b in zip(direct, replayed))
    print("  replayed G_CERT verdicts identical to the live ones: {}".format(same))
    print("  log written to {}".format(log.path))
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
