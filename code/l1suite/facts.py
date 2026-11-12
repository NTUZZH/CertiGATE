"""Real instance state, in the shapes the template families select from.

Every slot value in every instruction comes from here: real work-order ids,
real trades, real buildings, real release and due dates, and the real baseline
schedule the Y1 dispatcher produces for that instance.  Nothing is invented
except the ids that V1 items deliberately break, and those are checked against
the instance so they are genuinely dangling.

Three facts about this environment drive the selection helpers, and all three
were measured on the shipped instances before the families were written (see
reports/suite_build.md, "What actually moves the objective"):

1. Weighted tardiness is carried by a handful of priority-1 and priority-2
   orders.  In ``c09_storm2_w80_u100_0000`` only 14 of 2,269 orders are late at
   all.  An operation that does not touch a late or nearly late order usually
   leaves the objective unchanged to the decimal.
2. Many late orders are late because their own processing time exceeds their
   response window, not because they queued.  Resequencing cannot help those,
   so the "hot" list is ranked by weighted tardiness but selection for
   sequencing families additionally requires positive baseline queueing time.
3. ``batch`` and ``pin_next`` are weak levers on these instances (one displaced
   pick, or a chain the technicians can absorb), while ``reassign_window`` and
   ``reorder`` move the objective reliably.  The families use all seven
   operations anyway, because the suite has to cover the vocabulary, and the
   generator records the measured effect of each item rather than assuming one.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
from pathlib import Path

from l1adapter import dispatch, evaluate, instances, ops

from .config import EPISODE_RULE, EPISODE_SEED, FROZEN_SEED_K, STRATA_BY_KEY, Stratum

#: UNIFORMAT II group-element names for the trade codes that carry one.  Y1's
#: ``io.py`` rule R6 defines trade as the top-level UNIFORMAT system code and
#: names "D20 Plumbing" itself; the rest are that standard's own group names.
#: ``D90``, ``MISC`` and ``UNK`` are left without a gloss on purpose: ``MISC``
#: is Y1's merge bucket for trades under 1,000 orders in a campus and ``UNK`` is
#: its missing-code bucket, so neither has a craft name a supervisor would use.
TRADE_GLOSS = {
    "B20": "facade",
    "B30": "roofing",
    "C10": "interior construction",
    "C30": "interior finishes",
    "D10": "lift",
    "D20": "plumbing",
    "D30": "HVAC",
    "D40": "fire protection",
    "D50": "electrical",
    "E10": "equipment",
    "E20": "furnishings",
}

#: Trades that read naturally in an instruction (used for the "the instance does
#: not staff this trade" family, which has to name a craft a supervisor would).
NAMEABLE_TRADES = tuple(sorted(TRADE_GLOSS))

#: Codes that look like a plausible UNIFORMAT craft code but are outside the
#: frozen 14-code enum, for the decoder-absorbable V1 sub-class.  C20 (stairs)
#: and D80 (integrated automation) are real UNIFORMAT group elements that this
#: corpus never contains; B10 and D60 are the same shape.
OFF_VOCABULARY_TRADES = ("B10", "C20", "D60", "D80")


@dataclass
class InstanceFacts:
    """One instance, its baseline schedule, and everything the families need."""

    stratum: Stratum
    path: Path
    instance: dict
    baseline: dict
    instance_id: str = ""
    wwt_baseline: float = 0.0
    by_id: dict = field(default_factory=dict)
    assign: dict = field(default_factory=dict)
    trades: tuple = ()
    n_tech: dict = field(default_factory=dict)
    n_orders: dict = field(default_factory=dict)
    frozen_seed: tuple = ()

    # ---- construction ----------------------------------------------------- #
    @classmethod
    def build(cls, stratum: Stratum, path: Path) -> "InstanceFacts":
        inst = instances.load_instance(path)
        base = dispatch.dispatch_baseline(inst, EPISODE_RULE, EPISODE_SEED)
        f = cls(stratum=stratum, path=Path(path), instance=inst, baseline=base)
        f.instance_id = inst["meta"]["id"]
        f.wwt_baseline = evaluate.wwt(inst, base)
        f.by_id = {w["id"]: w for w in inst["work_orders"]}
        f.assign = {a["wo"]: a for a in base["assignments"]}
        f.n_tech = collections.Counter(t["trade"] for t in inst["technicians"])
        f.n_orders = collections.Counter(w["trade"] for w in inst["work_orders"])
        f.trades = tuple(sorted(set(inst["trades"]) | set(f.n_orders)))
        # The episode's standing frozen set: the work that is already under way
        # when the supervisor speaks, mirroring Y1's rolling replanner.  Earliest
        # baseline starts, ties by id, so it is the same set on every rebuild.
        starts = sorted(
            (float(a["start_bh"]), a["wo"]) for a in base["assignments"]
        )
        f.frozen_seed = tuple(wo for _, wo in starts[:FROZEN_SEED_K])
        return f

    # ---- per-order quantities --------------------------------------------- #
    def queueing_bh(self, oid: str) -> float:
        """Business hours the order waited in queue in the baseline schedule."""
        return float(self.assign[oid]["start_bh"]) - float(self.by_id[oid]["release_bh"])

    def lateness_bh(self, oid: str) -> float:
        """``end - due`` in the baseline schedule (negative when it finishes early)."""
        return float(self.assign[oid]["end_bh"]) - float(self.by_id[oid]["due_bh"])

    def weighted_tardiness(self, oid: str) -> float:
        return float(self.by_id[oid]["weight"]) * max(0.0, self.lateness_bh(oid))

    def queue_state(self, trade: str) -> str:
        """Congestion of a trade: orders per technician over the whole window."""
        load = self.n_orders.get(trade, 0) / max(1, self.n_tech.get(trade, 0))
        if load >= 20.0:
            return "deep"
        if load >= 5.0:
            return "moderate"
        return "shallow"

    # ---- candidate pools (all deterministic, all sorted) ------------------- #
    def orders_of(self, trade: str) -> list:
        return sorted(
            (w for w in self.instance["work_orders"] if w["trade"] == trade),
            key=lambda w: w["id"],
        )

    def hot_orders(self, k: int = 40, require_queueing: bool = False) -> list:
        """Orders whose deadline is under most pressure in the baseline.

        Ranked by baseline weighted tardiness, then by how close the finish is
        to the due date, then by id.  ``require_queueing`` keeps only orders
        that actually waited, which are the only ones a sequencing operation can
        move.
        """
        pool = [w for w in self.instance["work_orders"] if w["id"] in self.assign]
        if require_queueing:
            pool = [w for w in pool if self.queueing_bh(w["id"]) >= 1.0]
        pool.sort(
            key=lambda w: (
                -self.weighted_tardiness(w["id"]),
                -self.lateness_bh(w["id"]),
                w["id"],
            )
        )
        return pool[:k]

    def urgent_orders(self, k: int = 40) -> list:
        """Priority 1-2 orders with the earliest due dates (the SLA-critical work)."""
        pool = [w for w in self.instance["work_orders"] if int(w["priority"]) <= 2]
        if not pool:  # replay slices can hold none; fall back to the tightest dues
            pool = list(self.instance["work_orders"])
        pool.sort(key=lambda w: (float(w["due_bh"]), w["id"]))
        return pool[:k]

    def slack_orders(self, k: int = 40) -> list:
        """Routine work with room to move: low priority, finishing well before due."""
        pool = [
            w
            for w in self.instance["work_orders"]
            if int(w["priority"]) >= 3
            and w["id"] in self.assign
            and self.lateness_bh(w["id"]) < -8.0
        ]
        pool.sort(key=lambda w: (self.lateness_bh(w["id"]), w["id"]))
        return pool[:k]

    def long_orders(self, trade: str | None = None, k: int = 20, low_priority=True) -> list:
        """The longest jobs (optionally within one trade), longest first."""
        pool = [
            w
            for w in self.instance["work_orders"]
            if (trade is None or w["trade"] == trade)
            and (not low_priority or int(w["priority"]) >= 3)
        ]
        pool.sort(key=lambda w: (-float(w["p_bh"]), w["id"]))
        return pool[:k]

    def late_releasing_orders(self, k: int = 30) -> list:
        """Orders that arrive late in the window: strong precedence predecessors."""
        pool = [w for w in self.instance["work_orders"] if int(w["priority"]) >= 3]
        pool.sort(key=lambda w: (-float(w["release_bh"]), w["id"]))
        return pool[:k]

    def thin_trades(self, max_tech: int = 3) -> list:
        return sorted(t for t, n in self.n_tech.items() if 0 < n <= max_tech)

    def deep_trades(self) -> list:
        return sorted(
            (t for t in self.n_orders if self.n_tech.get(t, 0) > 0),
            key=lambda t: (-self.n_orders[t] / max(1, self.n_tech[t]), t),
        )

    def absent_nameable_trades(self) -> list:
        """Enum trades this instance does not staff and a supervisor could name."""
        present = set(self.trades)
        return [t for t in NAMEABLE_TRADES if t not in present]

    def building_groups(self, min_members: int = 2) -> list:
        """``(building, trade, member_ids)`` groups, largest first (replay only)."""
        groups = collections.defaultdict(list)
        for w in self.instance["work_orders"]:
            if w["building"]:
                groups[(w["building"], w["trade"])].append(w["id"])
        out = []
        for (b, t), members in groups.items():
            if len(members) >= min_members:
                out.append((b, t, tuple(sorted(members))))
        out.sort(key=lambda g: (-len(g[2]), g[0], g[1]))
        return out

    def buildings(self) -> list:
        return sorted({w["building"] for w in self.instance["work_orders"] if w["building"]})

    # ---- broken references, verified against the instance ------------------ #
    def dangling_order_id(self, seed_id: str) -> str:
        """A work-order number of the same shape that this instance does not have."""
        prefix = "".join(ch for ch in seed_id if not ch.isdigit())
        digits = "".join(ch for ch in seed_id if ch.isdigit()) or "0"
        n = int(digits)
        # Keep the shape of the real numbers: pad only if the source was padded.
        width = len(digits) if digits.startswith("0") else 0
        fallback = None
        for step in range(1, 2000):
            for cand_n in (n + step * 7, n - step * 7):
                if cand_n < 0:
                    continue
                cand = "{}{:0{w}d}".format(prefix, cand_n, w=width)
                if cand in self.by_id or cand == seed_id:
                    continue
                if len(cand) == len(seed_id):
                    return cand
                fallback = fallback or cand
        if fallback:
            return fallback
        raise RuntimeError("no dangling id found for {!r}".format(seed_id))

    def dangling_building_id(self, seed_building: str) -> str:
        have = set(self.buildings())
        digits = "".join(ch for ch in seed_building if ch.isdigit()) or "0"
        n, width = int(digits), len(digits)
        for step in range(1, 900):
            for cand_n in (n + step, n - step):
                if cand_n < 0:
                    continue
                cand = "{:0{w}d}".format(cand_n, w=width)
                if cand not in have:
                    return cand
        raise RuntimeError("no dangling building found for {!r}".format(seed_building))

    def other_trade(self, trade: str) -> str | None:
        """A different trade this instance does staff (for the mismatch family)."""
        cands = [t for t in self.trades if t != trade and self.n_tech.get(t, 0) > 0]
        return cands[0] if cands else None


# --------------------------------------------------------------------------- #
# Instance pools                                                               #
# --------------------------------------------------------------------------- #
_POOL_CACHE: dict = {}
_FACTS_CACHE: "collections.OrderedDict" = collections.OrderedDict()
_FACTS_CACHE_MAX = 3


def pool(stratum_key: str) -> list:
    """The stratum's instance files, first ``n_instances`` in sorted order."""
    if stratum_key not in _POOL_CACHE:
        s = STRATA_BY_KEY[stratum_key]
        paths = instances.list_instances(s.campus, s.track, s.size)
        if len(paths) < s.n_instances:
            raise RuntimeError(
                "stratum {} has {} files, needs {}".format(
                    stratum_key, len(paths), s.n_instances
                )
            )
        _POOL_CACHE[stratum_key] = paths[: s.n_instances]
    return _POOL_CACHE[stratum_key]


def facts_for(stratum_key: str, index: int) -> InstanceFacts:
    """Facts for one pool member, with a small cache (instances are big)."""
    key = (stratum_key, index)
    hit = _FACTS_CACHE.get(key)
    if hit is not None:
        _FACTS_CACHE.move_to_end(key)
        return hit
    f = InstanceFacts.build(STRATA_BY_KEY[stratum_key], pool(stratum_key)[index])
    _FACTS_CACHE[key] = f
    while len(_FACTS_CACHE) > _FACTS_CACHE_MAX:
        _FACTS_CACHE.popitem(last=False)
    return f


def clear_caches() -> None:
    _FACTS_CACHE.clear()


__all__ = [
    "InstanceFacts",
    "TRADE_GLOSS",
    "NAMEABLE_TRADES",
    "OFF_VOCABULARY_TRADES",
    "pool",
    "facts_for",
    "clear_caches",
]
