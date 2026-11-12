"""Property fuzz: random valid proposals on real instances, invariants asserted.

For each instance a random proposal (1-6 operations, drawn from all seven) is
applied and dispatched, then the result is checked against the referee and
against the semantics of every constraint the proposal contains:

  * the schedule is feasible (fmwos.validator) and covers every order once;
  * every frozen order sits on its baseline technician at its baseline start;
  * every precedence edge holds (start_a <= start_b), except where the
    successor is frozen, which the adapter documents as freeze-wins;
  * every batch group runs on one technician, consecutively, and in EDD order
    among the members that were available at each hand-off.

Usage: python scripts/fuzz_ops.py [n_instances] [seed]
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from l1adapter import apply_operations, dispatch, evaluate, instances, ops  # noqa: E402
from l1adapter.errors import CyclicPrecedence, FrozenWindowConflict  # noqa: E402

CELLS = [(9, "storm2", None), (10, "replay", 150), (5, "replay", 150), (10, "storm2", None)]
_TOL = 1e-9


def dense_pool(inst, rng, size=25):
    """A small pool of orders from one busy trade, so operations interact."""
    wos = inst["work_orders"]
    by_trade = {}
    for w in wos:
        by_trade.setdefault(w["trade"], []).append(w)
    trade = max(by_trade, key=lambda t: len(by_trade[t]))
    pool = sorted(by_trade[trade], key=lambda w: (w["release_bh"], w["due_bh"], w["id"]))[:size]
    return [w["id"] for w in pool]


def random_proposal(inst, rng, n_ops, pool=None):
    wos = inst["work_orders"]
    ids = [w["id"] for w in wos] if pool is None else list(pool)
    trade_of = {w["id"]: w["trade"] for w in wos}
    keep = set(ids)
    pairs = sorted(
        {(w["building"], w["trade"]) for w in wos
         if w["building"] is not None and (pool is None or w["id"] in keep)}
    )
    frozen: set[str] = set()
    out = []
    for _ in range(n_ops):
        kind = rng.choice(
            ["set_priority", "pin_next", "reorder", "reassign_window", "freeze", "unfreeze", "batch"]
        )
        if kind == "set_priority":
            out.append({"op": kind, "order_id": rng.choice(ids), "priority_class": rng.choice([1, 2, 3, 4])})
        elif kind == "pin_next":
            oid = rng.choice(ids)
            out.append({"op": kind, "order_id": oid, "trade": trade_of[oid]})
        elif kind == "reorder":
            a, b = rng.sample(ids, 2)
            out.append({"op": kind, "order_id": a, "relation": rng.choice(["before", "after"]),
                        "ref_order_id": b})
        elif kind == "reassign_window":
            out.append({"op": kind, "order_id": rng.choice(ids),
                        "release_shift_bh": round(rng.uniform(-20, 20), 3)})
        elif kind == "freeze":
            oid = rng.choice(ids)
            frozen.add(oid)
            out.append({"op": kind, "order_id": oid})
        elif kind == "unfreeze":
            if not frozen:
                continue
            oid = rng.choice(sorted(frozen))
            frozen.discard(oid)
            out.append({"op": kind, "order_id": oid})
        else:
            if not pairs:
                continue
            b, t = pairs[rng.randrange(len(pairs))]
            out.append({"op": kind, "building_id": b, "trade": t})
    return {"operations": out}


def check(adj, schedule, baseline):
    by_wo = {a["wo"]: a for a in schedule["assignments"]}
    problems = []

    result = evaluate.validate(adj, schedule)
    if not result["feasible"]:
        problems.append("validator: " + "; ".join(result["violations"][:3]))
    if len(by_wo) != len(adj.instance["work_orders"]):
        problems.append("coverage: {} assignments for {} orders".format(
            len(by_wo), len(adj.instance["work_orders"])))

    base_by_wo = {a["wo"]: a for a in baseline["assignments"]}
    for oid, slot in adj.frozen.items():
        got = by_wo.get(oid)
        ref = base_by_wo[oid]
        if got is None or got["tech"] != slot["tech"] or abs(got["start_bh"] - slot["start_bh"]) > _TOL:
            problems.append("freeze {} moved from {} to {}".format(oid, ref, got))

    for a, b in adj.precedence:
        if b in adj.frozen:
            continue  # documented: a freeze wins over a precedence edge
        if by_wo[a]["start_bh"] > by_wo[b]["start_bh"] + _TOL:
            problems.append("precedence {}<={} violated ({} > {})".format(
                a, b, by_wo[a]["start_bh"], by_wo[b]["start_bh"]))

    for g in adj.batches:
        rows = [by_wo[m] for m in g.members]
        techs = {r["tech"] for r in rows}
        if len(techs) != 1:
            problems.append("batch {}/{} split across {}".format(g.building_id, g.trade, techs))
            continue
        tech = techs.pop()
        served = sorted(rows, key=lambda r: r["start_bh"])
        seq = [r["wo"] for r in served]
        on_tech = sorted(
            (a for a in schedule["assignments"] if a["tech"] == tech), key=lambda a: a["start_bh"]
        )
        window = [a["wo"] for a in on_tech
                  if served[0]["start_bh"] - _TOL <= a["start_bh"] <= served[-1]["start_bh"] + _TOL]
        intruders = [w for w in window if w not in set(seq) and w not in adj.frozen]
        if intruders:
            problems.append("batch {}/{} interrupted by {}".format(g.building_id, g.trade, intruders))
        rel = {w["id"]: float(w["release_bh"]) for w in adj.instance["work_orders"]}
        due = {w["id"]: float(w["due_bh"]) for w in adj.instance["work_orders"]}
        constrained_members = {b for _, b in adj.precedence}
        for cur, nxt in zip(seq, seq[1:]):
            if nxt in constrained_members:
                continue  # precedence legitimately moves a member down the chain
            if due[cur] > due[nxt] + _TOL and rel[nxt] <= by_wo[cur]["start_bh"] + _TOL:
                problems.append("batch {}/{} out of EDD order at {}->{}".format(
                    g.building_id, g.trade, cur, nxt))
    return problems


def main(n_instances=60, seed=11, dense=False):
    rng = random.Random(seed)
    paths = []
    for campus, track, size in CELLS:
        paths.extend(instances.list_instances(campus, track, size)[:40])
    rng.shuffle(paths)
    paths = paths[:n_instances]

    n_ok = n_cyclic = n_refused = 0
    n_ops_total = 0
    failures = []
    for path in paths:
        inst = instances.load_instance(path)
        rule = rng.choice(["atc", "edd"])
        baseline = dispatch.dispatch_baseline(inst, rule, 0)
        pool = dense_pool(inst, rng) if dense else None
        proposal = random_proposal(inst, rng, rng.randint(4, 14) if dense else rng.randint(1, 6), pool)
        n_ops_total += len(proposal["operations"])
        try:
            adj = apply_operations(
                inst, ops.parse_operations(proposal, strict_schema=True),
                baseline_schedule=baseline,
            )
            schedule = dispatch.dispatch_adjusted(adj, rule, 0)
        except FrozenWindowConflict:
            n_refused += 1
            continue
        except CyclicPrecedence:
            assert adj.find_cycles(), "CyclicPrecedence raised without a cycle"
            n_cyclic += 1
            continue
        problems = check(adj, schedule, baseline)
        if problems:
            failures.append((path.name, rule, proposal, problems))
        else:
            n_ok += 1

    print("fuzz{}: {} instances, {} operations, {} clean, {} cyclic, {} frozen-window conflict, "
          "{} failures".format(" (dense)" if dense else "", len(paths), n_ops_total, n_ok,
                               n_cyclic, n_refused, len(failures)))
    for name, rule, proposal, problems in failures[:5]:
        print("--", name, rule)
        print("   ops:", proposal["operations"])
        for p in problems:
            print("   !", p)
    return 1 if failures else 0


if __name__ == "__main__":
    argv = [a for a in sys.argv[1:] if a != "--dense"]
    n = int(argv[0]) if len(argv) > 0 else 60
    s = int(argv[1]) if len(argv) > 1 else 11
    sys.exit(main(n, s, dense="--dense" in sys.argv))
