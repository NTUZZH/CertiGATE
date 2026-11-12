#!/usr/bin/env python
"""Screening, scenario cards and workbook for the second field-instruction collection.

WHAT THIS BUILDS
----------------
The first collection (``code/scripts/field_cards.py``) put eight practitioners on
eight real boards of the benchmark.  Their instructions were small changes, and
none of the priced proposals cost more than the 0.20 class.  The second
collection puts practitioners on boards and orders on which a simple change has
a price.  The practitioners still choose the orders and the words, and nothing
on a card says which orders carry a price; that information is kept in the
manifest only.

Outputs, all under ``the data-collection pack (not released)``:

* ``screening_candidates.csv``  every screened candidate change and its realised
  cost (also the cache: a rerun reads it instead of recomputing);
* ``screening_selftest.csv``    the self-test against the published labels;
* ``screening_report.md``       the screening per stratum and per instance, the
  ranking and the card allocation;
* ``cards/Scenario_Cards_R2.pdf`` eight cards, one A4 page each;
* ``Field_Instruction_Workbook_R2.xlsx`` sheets "Read me" (the text of
  ``briefing_r2.md``), "Card 1" .. "Card 8", "Answers", "About you" and a hidden
  "Lists" sheet holding the dropdown values;
* ``card_manifest_r2.json``     per card the instance, its snapshot hash, the
  sixteen orders, the in-progress set, the allocation rule, the instance's
  screening numbers and, per displayed order, its extract step and its prices;
* ``README.md``.

PART 1. SCREENING
-----------------
Every candidate is a one-operation proposal in the form of a logged proposal
(``{"operations": [op]}`` as JSON text), with the operation and argument names
of the frozen schema (``code/schema/adjustments.schema.json``).  It is priced by
the code path of ``n21_field_instructions.py evaluate`` and nothing else: the
decision instant by the benchmark's rule (``n11_decision_time.issuability`` and
``decision_instant_of``, reading "primary": the instant at which every order the
candidate names is first known), the site at that instant (``n21.Site``) and
``n21.unit_record``, which runs the schema check, the feasibility check, the
certificate, the realised run to the end of the window on the original values,
the cost bracket ``cost_lo`` / ``cost_hi`` and the cost classes at 0.20 and 0.10
(costly when the whole bracket lies above the level).  n21 is loaded from its
source with its core allowance set in memory to this script's core, as n21 loads
n16 and n20 loads n16 and n18; the file on disk is untouched, and the run first
asserts that n21's verification report is a pass on the same replay code.

The episode is the one the cards show: rule ATC, seed 0, and the instance's
standing frozen set where the suite uses one (the card's "in progress" rows).
Orders in that set are left out of every candidate pool.

Candidates per instance.  Every pool is sorted by order id, and every draw that
a cap forces uses one ``random.Random(SEED + index)``, index being the
instance's position in the full screening order (stratum order, then suite
items descending, then id), in the order HOLD, PROMOTE, PRECEDENCE (a),
PRECEDENCE (b), DOWNGRADE, BATCH.

* HOLD: ``reassign_window`` with ``release_shift_bh`` +16 and +40 on each of the
  16 class-1 or class-2 orders with the earliest due time (ties by id).
* PROMOTE: ``pin_next`` (with the order's own trade) on each class-3 or class-4
  order among the 20 orders with the most hours of work; at most 12, drawn.
* PRECEDENCE: ``reorder`` that makes an urgent order of the HOLD pool wait for
  another order, written as the suite's cost-bearing items write it:
  ``{"op": "reorder", "order_id": <other>, "relation": "before",
  "ref_order_id": <urgent>}`` ("sequence <other> before <urgent>"; the urgent
  order may start only once the other has started).  The other order is drawn
  from (a) the orders that become available in the second half of the arrival
  window and (b) the PROMOTE orders: 24 pairs from each source at most.
* DOWNGRADE: ``set_priority`` to class 4 on each class-1 order of the HOLD pool;
  at most 8, drawn.
* BATCH (instances with building codes only): ``batch`` for up to 8 drawn
  (building, trade) pairs that hold at least two orders outside the frozen set;
  the candidate names every order of the pair, as the suite's batch items do.

A candidate whose decision instant falls after one of its orders has started is
not issuable: it is counted and not priced.  A candidate that the schema or
feasibility check refuses is recorded with the check's outcome.  Only issuable,
accepted candidates enter the shares.  The cost level in weighted business
hours is 0.20 times the upper end of the instance's full-window bracket (floor
1 bh); it is the realised damage above which a candidate is costly whenever the
no-change run lies at or above that end, and the script asserts this on every
row where that holds.

Self-test (run before the screening is trusted, fatal on any mismatch): 60 suite
reference proposals of the screened instances that carry a published class in
``analysis/N18_fig_price_k_fi.csv`` (10 costly and 10 low-cost per stratum,
drawn with ``random.Random(SEED)``) are priced by the same function, and both
the decision instant and the class at 0.20 and at 0.10 must equal the published
values.

PART 2. CARDS
-------------
Within each stratum the screened instances that carry all four priority classes
are ranked by the share of issuable, accepted candidates that are costly at
0.20 (descending, ties by id).  A board with no lateness without a change (the
upper end of its full-window bracket below 1 bh, so that the 1 bh floor sets its
cost level at 0.2 bh) and an ordinary-day board whose arrival window is longer
than one working week (MAX_ORDINARY_WINDOW_BH = 40 bh) are left out of the
ranking and kept in the screening tables.  Default allocation: 4 cards from c09_storm2_w80 (Primary, Cards 1 to
4), 1 from c10_storm2_w80 (Confirmation, Card 5), 3 from c10_replay_400
(ordinary days, Cards 6 to 8), because a hold of 16 bh is not costly on the
campus 10 storm boards and often is on the ordinary-day boards with lateness,
whose load is the dataset's own (the report gives the counts).  A stratum in
which no instance reaches a costly share of 5 per cent contributes no card, and
its cards go to the other strata in the proportion 2:1 (Primary : the other
stratum), by largest remainder.  ``--cards-per-stratum a,b,c`` overrides the
allocation.

The sixteen orders of a card, in this order, never repeating an order, with
``random.Random(SEED + card number)`` and every pool sorted by id:

1. In progress: the suite's standing frozen set where one exists (the three
   earliest-starting orders of the baseline schedule, asserted equal to it).
2. Four urgent orders: class-1 or class-2 orders whose +16 bh HOLD is costly at
   0.20 (drawn); if fewer than four, the rest by the largest +16 bh HOLD damage.
3. Three long jobs: PROMOTE orders that are costly at 0.20 (drawn); if fewer
   than three, the rest by the largest PROMOTE damage.
4. Two late arrivals from the second half of the arrival window: first the
   orders that form a costly PRECEDENCE (a) with an urgent order of step 2
   (drawn), then drawn from all late arrivals.
5. Cards on instances with building codes: two pairs sharing a building, as in
   field_cards.py.
6. Coverage of the four priority classes and of at least four trades, as in
   field_cards.py.
7. Fill to sixteen, as in field_cards.py.

Display order, columns, crew table, site lines, notes, the PDF page and the card
sheet are those of field_cards.py, whose functions are imported.

WHAT IS ASSERTED
----------------
Snapshot hashes; n21's verification is a pass on the current replay code; the
self-test; the cost level on every qualifying row; every displayed order exists
in its instance; 16 distinct orders per card with all four classes and at least
four trades and the step counts above; the in-progress set equals the suite's
frozen set; every ordinary-day card shows at least 8 orders available within
16 working hours of the card's instant; the crew table parsed from the proposer
prompt equals a recount;
the workbook reopens with its validation lists on the right columns; the PDF
has eight pages; the briefing's card-mix sentence ("Five cards show a storm
day, ..., and three show an ordinary weekday.") is on the "Read me" sheet and its
two number words equal the storm and ordinary cards of the allocation used; the
manifest built twice from the screening rows is byte-identical; no card page,
card sheet or card string contains "lever", "costly", "screen" or "threshold".

Run from the repository root, on the project's one core, one thread:
  OMP_NUM_THREADS=1 python code/scripts/field_cards_r2.py
Options: --plan (count candidates, time one evaluation, no screening),
--screen-per-stratum a,b,c, --cards-per-stratum a,b,c.
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_v] = "1"

import sys  # noqa: E402

sys.dont_write_bytecode = True  # importing the reused scripts leaves no cache files behind

import argparse  # noqa: E402
import collections  # noqa: E402
import datetime as _dt  # noqa: E402
import csv  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import time  # noqa: E402
import types  # noqa: E402
from pathlib import Path  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent
CODE = SCRIPTS_DIR.parent
ROOT = CODE.parent
for _p in (str(CODE), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

#: The project's core on this machine (one core, shared with nothing timed).
ALLOWED_CORES = {3}
_aff = set(os.sched_getaffinity(0))
if not _aff <= ALLOWED_CORES and not os.environ.get("CERTIGATE_ANY_CORES"):
    raise SystemExit("REFUSING TO RUN: affinity {} is not inside cores {}".format(
        sorted(_aff), sorted(ALLOWED_CORES)))


def load_n21():
    """n21_field_instructions as a module, with its core allowance (its own guard and the
    allowance it writes into n16's source) set to this script's cores in memory."""
    path = SCRIPTS_DIR / "n21_field_instructions.py"
    src = path.read_text(encoding="utf-8")
    old = "ALLOWED_CORES = {10, 11}"
    new = "ALLOWED_CORES = {" + ", ".join(str(c) for c in sorted(ALLOWED_CORES)) + "}"
    if src.count(old) != 2:
        raise SystemExit("n21_field_instructions.py: '{}' found {} times, expected 2".format(
            old, src.count(old)))
    mod = types.ModuleType("n21_field_instructions")
    mod.__file__ = str(path)
    sys.modules["n21_field_instructions"] = mod
    exec(compile(src.replace(old, new), str(path), "exec"), mod.__dict__)  # noqa: S102
    return mod


n21 = load_n21()
import field_cards as FC1  # noqa: E402  (layout, crew table, board rows, PDF)

VERSION = "l1-field-cards-r2-1"
SEED = 20261112
SNAPSHOT_NAME = FC1.SNAPSHOT_NAME
OUT_DIR = ROOT / "participant_files" / "field_instructions_r2"
CACHE_CSV = OUT_DIR / "screening_candidates.csv"
SELFTEST_CSV = OUT_DIR / "screening_selftest.csv"
REPORT_MD = OUT_DIR / "screening_report.md"
PDF_PATH = OUT_DIR / "cards" / "Scenario_Cards_R2.pdf"
XLSX_PATH = OUT_DIR / "Field_Instruction_Workbook_R2.xlsx"
MANIFEST_PATH = OUT_DIR / "card_manifest_r2.json"
BRIEFING_PATH = OUT_DIR / "briefing_r2.md"
README_PATH = OUT_DIR / "README.md"
N18_CSV = ROOT / "analysis" / "N18_fig_price_k_fi.csv"

STRATA = tuple(s for s, _k in FC1.STRATA)
#: Default cards per stratum: 4 campus 9 storm boards (Cards 1 to 4), 1 campus 10 storm board
#: (Card 5) and 3 ordinary days of campus 10 (Cards 6 to 8).
DEFAULT_CARDS = collections.OrderedDict([("c09_storm2_w80", 4), ("c10_storm2_w80", 1),
                                         ("c10_replay_400", 3)])
STRATUM_NAME = {"c09_storm2_w80": "Primary", "c10_storm2_w80": "Confirmation",
                "c10_replay_400": "Buildings"}
#: Weights of the 2:1 rule that moves the cards of a stratum without costly candidates.
REALLOC_WEIGHT = {"c09_storm2_w80": 2, "c10_storm2_w80": 1, "c10_replay_400": 1}
#: Instances screened per stratum (the most suite items first).  Measured on this core
#: (2026-11-12): about 15 s per instance on c09_storm2_w80 (0.15 to 0.3 s per evaluation),
#: 185 to 255 s on c10_storm2_w80 (9,350 orders, 1 to 4 s per evaluation) and about 2 s on
#: c10_replay_400.  All 60 would take about 50 minutes on one core, over the budget of
#: about 40, so c10_storm2_w80 is screened on its 8 instances with the most suite items.
SCREEN_PER_STRATUM = collections.OrderedDict([("c09_storm2_w80", 24), ("c10_storm2_w80", 8),
                                              ("c10_replay_400", 24)])
BUDGET_S = 40 * 60

HOLD_SHIFTS = (16.0, 40.0)
N_HOLD = 16
N_LONG_POOL = 20
N_PROMOTE = 12
N_PREC_HALF = 24
N_DOWNGRADE = 8
N_BATCH = 8
DELTA, DELTA_LOW = 0.20, 0.10
MIN_SHARE = 0.05
N_ROWS = FC1.N_ROWS
FIRST_DAY_BH = FC1.FIRST_DAY_BH
EPISODE_RULE, EPISODE_SEED = FC1.EPISODE_RULE, FC1.EPISODE_SEED
SELFTEST_PER_CLASS = 10

TYPES = ("HOLD", "PROMOTE", "PRECEDENCE", "DOWNGRADE", "BATCH")
#: (type, variant) columns of the report, in order, with their labels.
KINDS = collections.OrderedDict([
    (("HOLD", "shift_16"), "HOLD +16 bh"), (("HOLD", "shift_40"), "HOLD +40 bh"),
    (("PROMOTE", ""), "PROMOTE"), (("PRECEDENCE", "late_arrival"), "PRECEDENCE (a)"),
    (("PRECEDENCE", "long_job"), "PRECEDENCE (b)"), (("DOWNGRADE", ""), "DOWNGRADE"),
    (("BATCH", ""), "BATCH")])
BANNED_ON_CARDS = ("lever", "costly", "screen", "threshold")

CAND_FIELDS = ["instance_id", "stratum", "instance_index", "frozen_key", "cand_no",
               "candidate_type", "variant", "operation", "orders_named", "focus_order",
               "partner_order", "decision_instant", "issuable", "check_outcome", "term_cert",
               "codes", "damage_bh", "cost_lo", "cost_hi", "costly_020", "costly_010",
               "threshold_bh_020", "eval_s"]

LATER_CHOICES = ("none", "up to half a day", "half a day to two days", "more than two days")
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                "eight": 8}
#: The briefing's sentence that states the card mix ("Five cards show a storm day, ... and
#: three show an ordinary weekday.").
CARD_MIX_RE = re.compile(r"\b([A-Za-z]+) cards show a storm day\b[^.]*?\band ([A-Za-z]+) show "
                         r"an ordinary ([A-Za-z]+)\.")
STORM_STRATA = ("c09_storm2_w80", "c10_storm2_w80")
ORDINARY_STRATA = ("c10_replay_400",)
#: An ordinary-day board whose orders arrive over more than one working week leaves the
#: card ranking (its displayed orders would become available days or weeks from now).
MAX_ORDINARY_WINDOW_BH = 40.0
#: Every ordinary-day card shows at least MIN_NEAR_ROWS orders available within NEAR_BH
#: working hours of the card's instant (t = 0).
NEAR_BH = 16.0
MIN_NEAR_ROWS = 8
#: Respondent code letter of the second set (Q1 to Q8), distinct from the first set's P codes.
RESPONDENT_LETTER = "Q"
YES_NO = ("yes", "no")
APPROVAL_CHOICES = ("daily", "weekly", "occasionally", "never")


# --------------------------------------------------------------------------- #
# Small utilities                                                              #
# --------------------------------------------------------------------------- #
def fnum(x):
    """A float written so that reading it back gives the same number."""
    return "" if x is None else repr(float(x))


def fbool(x):
    return "" if x is None else ("1" if x else "0")


def fcls(x):
    return "" if x is None else str(int(x))


def pnum(s):
    return None if s in ("", None) else float(s)


def pint(s):
    return None if s in ("", None) else int(s)


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def op_json(op: dict) -> str:
    return json.dumps(op, separators=(", ", ": "))


def pct(x):
    return "-" if x is None else "{:.1f}%".format(100.0 * x)


def share(num, den):
    return None if not den else num / den


def parse_triple(text, what):
    vals = [int(v) for v in text.split(",")]
    if len(vals) != len(STRATA) or any(v < 0 for v in vals):
        raise SystemExit("{}: give {} non-negative integers, e.g. 4,2,2".format(what, len(STRATA)))
    return collections.OrderedDict(zip(STRATA, vals))


# --------------------------------------------------------------------------- #
# Inputs: suite, instances, standing frozen set                                #
# --------------------------------------------------------------------------- #
class Inputs:
    def __init__(self):
        self.items = FC1.load_suite()
        self.hashes = json.load(open(FC1.HASH_MANIFEST))["files"]
        self.by_inst = collections.defaultdict(list)
        for it in self.items:
            assert it["episode"]["rule"] == EPISODE_RULE and it["episode"]["seed"] == EPISODE_SEED
            self.by_inst[it["instance"]["instance_id"]].append(it)
        self.meta = {iid: its[0]["instance"] for iid, its in self.by_inst.items()}
        self.n_items = {iid: len(its) for iid, its in self.by_inst.items()}
        assert len(self.meta) == 60, len(self.meta)

    def screening_order(self):
        """Every suite instance: stratum order, then suite items descending, then id."""
        out = []
        for s in STRATA:
            ids = sorted((i for i, m in self.meta.items() if m["stratum"] == s),
                         key=lambda i: (-self.n_items[i], i))
            out += [(s, i) for i in ids]
        return out

    def checked_path(self, iid):
        """field_cards' own check: the snapshot file and its manifest hash."""
        rel = FC1.snapshot_relpath(self.meta[iid]["file"])
        path = FC1.SNAPSHOT_ROOT / rel
        digest = FC1.sha256(path)
        assert self.hashes[rel] == digest, ("snapshot hash mismatch", rel)
        return rel, path, digest

    def standing_frozen(self, iid, base):
        """The card's in-progress set: the suite's standing frozen set where one exists."""
        its = self.by_inst[iid]
        sets = {tuple(it["episode"]["frozen_seed"]) for it in its
                if it["episode"].get("frozen_seed")}
        if not sets:
            return []
        assert len(sets) == 1, (iid, sets)
        starts = sorted((float(a["start_bh"]), a["wo"]) for a in base["assignments"])
        frozen = [o for _, o in starts[:3]]
        assert tuple(frozen) == next(iter(sets)), (iid, frozen, sets)
        return frozen

    def suite_refs(self, iid):
        return sorted({o for it in self.by_inst[iid] for o in it["referenced"]["order_ids"]
                       if len(it["referenced"]["order_ids"]) <= 4})


# --------------------------------------------------------------------------- #
# The pricing path of n21 evaluate                                             #
# --------------------------------------------------------------------------- #
class Pricer:
    """n21's Instances, Labels and SiteCache; one call prices one proposal."""

    def __init__(self, inputs):
        self.inputs = inputs
        self.I = n21.Instances()
        self.L = n21.Labels()
        self.D = self.I.D
        self.sc = n21.SiteCache(self.I)
        self._starts = {}
        self._checked = set()

    def instance(self, iid):
        c = self.I.get(iid)
        if iid not in self._checked:
            rel, path, digest = self.inputs.checked_path(iid)
            assert Path(c["path"]).resolve() == Path(path).resolve(), (c["path"], path)
            self._checked.add(iid)
        return c

    def starts(self, iid, seed):
        key = (iid, n21.frozen_key(seed))
        if key not in self._starts:
            traj = self.I.traj(iid, list(seed))
            self._starts[key] = {a["wo"]: float(a["start_bh"]) for a in traj["assignments"]}
        return self._starts[key]

    def decision(self, iid, seed, refs):
        """The benchmark's rule, as n21 items applies it to a field instruction."""
        c = self.instance(iid)
        stub = {"referenced": {"order_ids": list(refs)}}
        iss = self.D.issuability(stub, c["by_id"], self.starts(iid, seed))
        return iss, float(self.D.decision_instant_of(iss, "primary"))

    def price(self, iid, seed, refs, ops, t_d):
        site = self.sc.get(iid, list(seed), t_d)
        raw = json.dumps({"operations": list(ops)})
        return n21.unit_record(site, self.L, raw, list(refs))

    def threshold(self, iid):
        b = self.L.full_br.get((iid, self.D.BASE_FP))
        assert b is not None, ("no full-window bracket", iid)
        lo_e, up_e, _p = self.D.ends(b)
        return DELTA * max(up_e, n21.FLOOR_BH), lo_e, up_e

    def drop_sites(self):
        self.sc.sites.clear()

    def drop_instance(self, iid):
        self.drop_sites()
        self.I.cache.pop(iid, None)
        for k in [k for k in self._starts if k[0] == iid]:
            del self._starts[k]


def assert_verified():
    """n21's verification passed on exactly the replay code this script calls."""
    vr = json.loads(Path(n21.VERIFY_REPORT).read_text())
    assert vr["status"] == "PASS", ("n21 verify report", vr["status"])
    now = n21.replay_code_hashes()
    assert vr["code_hashes"] == now, "replay code changed since n21's verification"
    return sha_text(json.dumps(now, sort_keys=True))


# --------------------------------------------------------------------------- #
# Candidates                                                                   #
# --------------------------------------------------------------------------- #
def candidates_for(inst, frozen, rng):
    wos = sorted(inst["work_orders"], key=lambda w: w["id"])
    by_id = {w["id"]: w for w in wos}
    fz = set(frozen)
    free = [w for w in wos if w["id"] not in fz]
    window = float(inst["meta"]["window_bh"])
    urgent = sorted((w for w in free if int(w["priority"]) in (1, 2)),
                    key=lambda w: (float(w["due_bh"]), w["id"]))[:N_HOLD]
    hold_pool = sorted(w["id"] for w in urgent)
    longest = sorted(free, key=lambda w: (-float(w["p_bh"]), w["id"]))[:N_LONG_POOL]
    promote_pool = sorted(w["id"] for w in longest if int(w["priority"]) in (3, 4))
    promote = (sorted(rng.sample(promote_pool, N_PROMOTE)) if len(promote_pool) > N_PROMOTE
               else promote_pool)
    late = sorted(w["id"] for w in free if float(w["release_bh"]) >= window / 2.0)
    pairs_a = [(u, o) for u in hold_pool for o in late if o != u]
    pick_a = sorted(rng.sample(pairs_a, min(N_PREC_HALF, len(pairs_a))))
    pairs_b = [(u, o) for u in hold_pool for o in promote if o != u]
    pick_b = sorted(rng.sample(pairs_b, min(N_PREC_HALF, len(pairs_b))))
    class1 = [o for o in hold_pool if int(by_id[o]["priority"]) == 1]
    down = sorted(rng.sample(class1, N_DOWNGRADE)) if len(class1) > N_DOWNGRADE else class1
    pick_bt, members = [], {}
    if any(w["building"] is not None for w in wos):
        groups = collections.defaultdict(list)
        for w in free:
            if w["building"] is not None:
                groups[(w["building"], w["trade"])].append(w["id"])
        eligible = sorted(k for k, v in groups.items() if len(v) >= 2)
        pick_bt = sorted(rng.sample(eligible, min(N_BATCH, len(eligible))))
        for b, t in pick_bt:
            members[(b, t)] = sorted(w["id"] for w in wos
                                     if w["building"] == b and w["trade"] == t)

    out = []

    def add(ctype, variant, op, refs, focus, partner=""):
        out.append({"candidate_type": ctype, "variant": variant, "op": op,
                    "refs": sorted(set(refs)), "focus_order": focus, "partner_order": partner})

    for u in hold_pool:
        for sh in HOLD_SHIFTS:
            add("HOLD", "shift_{:d}".format(int(sh)),
                {"op": "reassign_window", "order_id": u, "release_shift_bh": sh}, [u], u)
    for o in promote:
        add("PROMOTE", "", {"op": "pin_next", "order_id": o, "trade": by_id[o]["trade"]}, [o], o)
    for variant, picks in (("late_arrival", pick_a), ("long_job", pick_b)):
        for u, o in picks:
            add("PRECEDENCE", variant, {"op": "reorder", "order_id": o, "relation": "before",
                                        "ref_order_id": u}, [u, o], u, o)
    for u in down:
        add("DOWNGRADE", "", {"op": "set_priority", "order_id": u, "priority_class": 4}, [u], u)
    for b, t in pick_bt:
        add("BATCH", "", {"op": "batch", "building_id": b, "trade": t}, members[(b, t)],
            "{}/{}".format(b, t))
    seen, uniq = set(), []
    for c in out:
        k = op_json(c["op"])
        if k in seen:
            continue
        seen.add(k)
        c["cand_no"] = len(uniq) + 1
        uniq.append(c)
    pools = {"hold_pool": hold_pool, "promote_pool": promote_pool, "promote": promote,
             "late_arrivals": len(late), "pairs_a": len(pairs_a), "pairs_b": len(pairs_b),
             "downgrade": down, "batch_pairs": ["{}/{}".format(b, t) for b, t in pick_bt]}
    return uniq, pools


# --------------------------------------------------------------------------- #
# The screening cache                                                          #
# --------------------------------------------------------------------------- #
def cache_header(code_sha):
    return ["screening candidates ({}); priced by the n21 evaluate path; replay code sha256 "
            "{}; seed {}".format(VERSION, code_sha, SEED)]


def read_cache(code_sha):
    if not CACHE_CSV.is_file():
        return {}, "absent"
    with open(CACHE_CSV, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    head = [ln[2:] for ln in lines if ln.startswith("# ")]
    if head != cache_header(code_sha):
        print("[r2] screening cache written by other code; recomputing", flush=True)
        return {}, "stale"
    rows = list(csv.DictReader(ln for ln in lines if not ln.startswith("#")))
    return {(r["instance_id"], r["frozen_key"], r["operation"]): r for r in rows}, "read"


def write_cache(rows_in_order, code_sha):
    tmp = CACHE_CSV.with_suffix(".csv.tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        for c in cache_header(code_sha):
            fh.write("# " + c + "\n")
        w = csv.DictWriter(fh, fieldnames=CAND_FIELDS, extrasaction="raise")
        w.writeheader()
        for r in rows_in_order:
            w.writerow({k: r.get(k, "") for k in CAND_FIELDS})
    os.replace(tmp, CACHE_CSV)


def typed_row(r):
    """A cache row with its numbers as numbers."""
    return dict(r, instance_index=int(r["instance_index"]), cand_no=int(r["cand_no"]),
                decision_instant=pnum(r["decision_instant"]), issuable=r["issuable"] == "1",
                damage_bh=pnum(r["damage_bh"]), cost_lo=pnum(r["cost_lo"]),
                cost_hi=pnum(r["cost_hi"]), costly_020=pint(r["costly_020"]),
                costly_010=pint(r["costly_010"]), threshold_bh_020=pnum(r["threshold_bh_020"]),
                eval_s=pnum(r["eval_s"]),
                orders_named=[o for o in r["orders_named"].split("|") if o],
                accepted=(r["issuable"] == "1" and r["check_outcome"] == "priced"))


# --------------------------------------------------------------------------- #
# Timing probe and plan                                                        #
# --------------------------------------------------------------------------- #
def plan(inputs, P, screen):
    """Candidates and decision instants per instance, and one timed evaluation per stratum."""
    out = {}
    probe = {}
    for idx, (s, iid) in enumerate(inputs.screening_order()):
        if iid not in screen:
            continue
        c = P.instance(iid)
        frozen = inputs.standing_frozen(iid, c["baseline"])
        cands, _pools = candidates_for(c["inst"], frozen, random.Random(SEED + idx))
        tds, n_iss = set(), 0
        for cd in cands:
            iss, t_d = P.decision(iid, frozen, cd["refs"])
            if iss["issuable"]:
                n_iss += 1
                tds.add(t_d)
        out[iid] = (s, len(cands), n_iss, len(tds))
        if s not in probe:
            cd = cands[0]
            _iss, t_d = P.decision(iid, frozen, cd["refs"])
            t0 = time.time()
            P.sc.get(iid, frozen, t_d)
            t1 = time.time()
            P.price(iid, frozen, cd["refs"], [cd["op"]], t_d)
            t2 = time.time()
            probe[s] = (t1 - t0, t2 - t1)
            print("[r2] timing {}: site {:.2f} s, one realised-cost evaluation {:.2f} s".format(
                iid, t1 - t0, t2 - t1), flush=True)
        P.drop_instance(iid)
    total = 0.0
    for iid, (s, n, n_iss, n_td) in out.items():
        t_site, t_unit = probe[s]
        total += n_td * t_site + n_iss * t_unit
    return out, probe, total


# --------------------------------------------------------------------------- #
# Part 1: screening                                                            #
# --------------------------------------------------------------------------- #
def screen_instances(inputs, P, screen, code_sha):
    cache, cache_state = read_cache(code_sha)
    rows_out, instances = [], collections.OrderedDict()
    order = [(idx, s, iid) for idx, (s, iid) in enumerate(inputs.screening_order())
             if iid in screen]
    t_start = time.time()
    n_new = 0
    for k, (idx, s, iid) in enumerate(order, start=1):
        t0 = time.time()
        c = P.instance(iid)
        inst = c["inst"]
        frozen = inputs.standing_frozen(iid, c["baseline"])
        fk = n21.frozen_key(frozen)
        cands, pools = candidates_for(inst, frozen, random.Random(SEED + idx))
        thr, lo_e, up_e = P.threshold(iid)
        anchor = P.L.anchor_wwt(iid, fk)
        recs = []
        pending = []
        for cd in cands:
            key = (iid, fk, op_json(cd["op"]))
            iss, t_d = P.decision(iid, frozen, cd["refs"])
            base = {"instance_id": iid, "stratum": s, "instance_index": str(idx),
                    "frozen_key": fk, "cand_no": str(cd["cand_no"]),
                    "candidate_type": cd["candidate_type"], "variant": cd["variant"],
                    "operation": op_json(cd["op"]), "orders_named": "|".join(cd["refs"]),
                    "focus_order": cd["focus_order"], "partner_order": cd["partner_order"],
                    "decision_instant": fnum(t_d), "issuable": fbool(iss["issuable"]),
                    "threshold_bh_020": fnum(thr)}
            if key in cache:
                hit = cache[key]
                for f in ("candidate_type", "variant", "orders_named", "decision_instant",
                          "issuable", "threshold_bh_020"):
                    assert hit[f] == base[f], ("cache row disagrees", key, f, hit[f], base[f])
                recs.append(dict(hit, cand_no=base["cand_no"], instance_index=base["instance_index"],
                                 focus_order=base["focus_order"],
                                 partner_order=base["partner_order"]))
                continue
            if not iss["issuable"]:
                base.update(check_outcome="not_issuable", term_cert="", codes="",
                            damage_bh="", cost_lo="", cost_hi="", costly_020="",
                            costly_010="", eval_s="")
                recs.append(base)
                continue
            pending.append((t_d, cd["cand_no"], cd, base))
            recs.append(base)
        # evaluate grouped by decision instant, one site in memory at a time
        last_td = None
        for t_d, _no, cd, base in sorted(pending, key=lambda x: (x[0], x[1])):
            if last_td is not None and t_d != last_td:
                P.drop_sites()
            last_td = t_d
            e0 = time.time()
            u = P.price(iid, frozen, cd["refs"], [cd["op"]], t_d)
            base.update(check_outcome=u["class"], term_cert=u["term_cert"] or "",
                        codes="|".join(u["codes"]), damage_bh=fnum(u["damage_bh"]),
                        cost_lo=fnum(u["cost_lo"]), cost_hi=fnum(u["cost_hi"]),
                        costly_020=fcls(u["costTwenty"]), costly_010=fcls(u["costTen"]),
                        eval_s="{:.4f}".format(time.time() - e0))
            assert u["anchor_wwt"] == anchor, (iid, u["anchor_wwt"], anchor)
            n_new += 1
        P.drop_instance(iid)
        rows_out += recs
        typed = [typed_row(r) for r in recs]
        # the cost level in weighted bh, asserted where the no-change run is at or above it
        if anchor >= up_e:
            for r in typed:
                if r["accepted"] and r["damage_bh"] is not None and r["cost_lo"] is not None:
                    want = 1 if r["damage_bh"] > thr + 1e-9 else 0
                    if abs(r["damage_bh"] - thr) > 1e-6:
                        assert (r["costly_020"] or 0) == want, ("cost level", iid, r["operation"],
                                                                r["damage_bh"], thr)
        acc = [r for r in typed if r["accepted"]]
        n20 = sum(1 for r in acc if r["costly_020"] == 1)
        instances[iid] = {"stratum": s, "index": idx, "frozen": frozen, "pools": pools,
                          "threshold_bh": thr, "bracket_lo": lo_e, "bracket_up": up_e,
                          "anchor_wwt": anchor, "rows": typed,
                          "classes": sorted({int(w["priority"]) for w in inst["work_orders"]}),
                          "window_bh": float(inst["meta"]["window_bh"]),
                          "n_orders": len(inst["work_orders"])}
        # keep the cache current after every instance
        done = {(r["instance_id"], r["frozen_key"], r["operation"]) for r in rows_out}
        rest = [r for kk, r in cache.items() if kk not in done and kk[0] not in instances]
        write_cache(rows_out + rest, code_sha)
        print("[r2] screen {:2d}/{} {:28s} {:3d} candidates, {:3d} accepted, costly at 0.20 "
              "{:3d} ({}), level {:.1f} bh, {:.1f} s".format(
                  k, len(order), iid, len(typed), len(acc), n20, pct(share(n20, len(acc))), thr,
                  time.time() - t0), flush=True)
    return instances, {"cache": cache_state, "evaluated_now": n_new,
                       "wall_s": time.time() - t_start}


# --------------------------------------------------------------------------- #
# Self-test against the published labels                                       #
# --------------------------------------------------------------------------- #
def self_test(inputs, P, screened_ids):
    rows = n21.read_csv_comments(N18_CSV)
    suite = {it["item_id"]: it for it in inputs.items}
    rng = random.Random(SEED)
    chosen = []
    for s in STRATA:
        pool = sorted((r for r in rows if r["instance_id"] in screened_ids
                       and r["stratum"] == s and r["costly_delta020"] in ("0", "1")),
                      key=lambda r: r["item_id"])
        for cls in ("1", "0"):
            sub = [r for r in pool if r["costly_delta020"] == cls]
            chosen += rng.sample(sub, min(SELFTEST_PER_CLASS, len(sub)))
    assert len(chosen) >= 40, len(chosen)
    chosen.sort(key=lambda r: (r["instance_id"], r["item_id"]))
    out = []
    t0 = time.time()
    last = None
    for r in chosen:
        it = suite[r["item_id"]]
        iid = it["instance"]["instance_id"]
        if last is not None and iid != last:
            P.drop_instance(last)
        last = iid
        seed = list(it["episode"]["frozen_seed"] or [])
        refs = list(it["referenced"]["order_ids"])
        ops = P.D.canonical_ops(it)
        iss, t_d = P.decision(iid, seed, refs)
        u = P.price(iid, seed, refs, ops, t_d)
        P.drop_sites()
        rec = {"item_id": r["item_id"], "instance_id": iid, "stratum": r["stratum"],
               "primary_class": it["primary_class"], "n_ops": len(ops),
               "op_types": "|".join(sorted({o["op"] for o in ops})),
               "t_d_published": r["t_d"], "t_d": "{:.4f}".format(t_d),
               "costly_020_published": r["costly_delta020"], "costly_020": fcls(u["costTwenty"]),
               "costly_010_published": r["costly_delta010"], "costly_010": fcls(u["costTen"]),
               "damage_bh": fnum(u["damage_bh"]), "cost_lo": fnum(u["cost_lo"]),
               "cost_hi": fnum(u["cost_hi"]), "check_outcome": u["class"]}
        rec["match"] = int(iss["issuable"] and abs(t_d - float(r["t_d"])) < 5e-5
                           and rec["costly_020"] == rec["costly_020_published"]
                           and rec["costly_010"] == rec["costly_010_published"])
        out.append(rec)
    if last is not None:
        P.drop_instance(last)
    fields = list(out[0].keys())
    with open(SELFTEST_CSV, "w", encoding="utf-8", newline="") as fh:
        fh.write("# self-test ({}): suite reference proposals priced by the screening function "
                 "against analysis/N18_fig_price_k_fi.csv\n".format(VERSION))
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    bad = [r for r in out if not r["match"]]
    summary = {"n": len(out), "n_match": len(out) - len(bad),
               "by_published_class": dict(sorted(collections.Counter(
                   r["costly_020_published"] for r in out).items())),
               "by_stratum": dict(sorted(collections.Counter(r["stratum"] for r in out).items())),
               "single_operation": sum(1 for r in out if r["n_ops"] == 1),
               "op_types": dict(sorted(collections.Counter(r["op_types"] for r in out).items())),
               "wall_s": time.time() - t0}
    if bad:
        for r in bad[:20]:
            print("SELF-TEST MISMATCH", r, file=sys.stderr)
        raise SystemExit("self-test failed: {} of {} suite reference proposals disagree".format(
            len(bad), len(out)))
    print("[r2] self-test: {} suite reference proposals, every decision instant and class "
          "equal to N18 ({:.1f} s)".format(len(out), summary["wall_s"]), flush=True)
    return summary


# --------------------------------------------------------------------------- #
# Screening numbers                                                            #
# --------------------------------------------------------------------------- #
def kind_stats(rows):
    acc = [r for r in rows if r["accepted"]]
    dmg = [r["damage_bh"] for r in acc if r["damage_bh"] is not None]
    n20 = sum(1 for r in acc if r["costly_020"] == 1)
    n10 = sum(1 for r in acc if r["costly_010"] == 1)
    return collections.OrderedDict(
        generated=len(rows), not_issuable=sum(1 for r in rows if not r["issuable"]),
        refused=sum(1 for r in rows if r["issuable"] and not r["accepted"]),
        accepted=len(acc), costly_020=n20, costly_010=n10,
        share_020=share(n20, len(acc)), share_010=share(n10, len(acc)),
        max_damage_bh=max(dmg) if dmg else None)


def instance_stats(rec):
    rows = rec["rows"]
    out = collections.OrderedDict(all=kind_stats(rows))
    for (t, v), _lab in KINDS.items():
        out["{}{}".format(t, ("/" + v) if v else "")] = kind_stats(
            [r for r in rows if r["candidate_type"] == t and r["variant"] == v])
    return out


def rnd(x, n=6):
    return None if x is None else round(float(x), n)


def stats_json(st):
    return collections.OrderedDict((k, rnd(v) if isinstance(v, float) else v)
                                   for k, v in st.items())


# --------------------------------------------------------------------------- #
# Part 2: ranking and allocation                                               #
# --------------------------------------------------------------------------- #
def hold16_counts(instances, stratum, lateness_only):
    """Costly at 0.20 / accepted for the +16 bh HOLD on the stratum's screened boards."""
    rs = [r for rec in instances.values() if rec["stratum"] == stratum
          and (not lateness_only or rec["bracket_up"] >= n21.FLOOR_BH)
          for r in rec["rows"] if r["candidate_type"] == "HOLD" and r["variant"] == "shift_16"
          and r["accepted"]]
    return sum(1 for r in rs if r["costly_020"] == 1), len(rs)


def default_reason(instances):
    a, b = hold16_counts(instances, "c10_storm2_w80", False)
    c, d = hold16_counts(instances, "c10_replay_400", True)
    return ("default allocation 4 / 1 / 3: on the campus 10 storm boards a hold of 16 bh is "
            "costly at 0.20 in {} of {} screened holds, while on the ordinary-day boards with "
            "lateness it is costly in {} of {} ({}), and the ordinary days carry the dataset's "
            "own load".format(a, b, c, d, pct(share(c, d))))


def card_mix(texts, alloc, cards):
    """The briefing's card-mix sentence: its two number words must equal the allocation."""
    joined = " ".join(str(t) for t in texts)
    m = CARD_MIX_RE.search(joined)
    if m is None:
        raise SystemExit("the briefing has no sentence of the form '<n> cards show a storm day, "
                         "..., and <m> show an ordinary <day>.'")
    words = (m.group(1).lower(), m.group(2).lower())
    if any(w not in NUMBER_WORDS for w in words):
        raise SystemExit("card-mix sentence: cannot read the number words {}".format(words))
    n_storm, n_ordinary = (NUMBER_WORDS[w] for w in words)
    want_storm = sum(alloc[s] for s in STORM_STRATA)
    want_ordinary = sum(alloc[s] for s in ORDINARY_STRATA)
    if (n_storm, n_ordinary) != (want_storm, want_ordinary):
        raise SystemExit("card-mix sentence disagrees with the allocation: the briefing says {} "
                         "storm and {} ordinary cards ('{}'), the allocation gives {} storm "
                         "({}) and {} ordinary ({})".format(
                             n_storm, n_ordinary, m.group(0), want_storm,
                             " + ".join("{} {}".format(s, alloc[s]) for s in STORM_STRATA),
                             want_ordinary,
                             " + ".join("{} {}".format(s, alloc[s]) for s in ORDINARY_STRATA)))
    day = m.group(3)
    days = [(c["title"], c["weekday"]) for c in cards if c["stratum"] in ORDINARY_STRATA]
    weekdays = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
    other = [(t, d) for t, d in days
             if d != day and not (day == "weekday" and d in weekdays)]
    return collections.OrderedDict(sentence=m.group(0), storm=n_storm, ordinary=n_ordinary,
                                   weekday_in_sentence=day, weekdays_on_cards=days,
                                   weekday_mismatch=other)


def rank_and_allocate(instances, override):
    ranking, skipped = collections.OrderedDict(), []
    for s in STRATA:
        recs = [(iid, r) for iid, r in instances.items() if r["stratum"] == s]
        ok = []
        for iid, r in recs:
            reasons = []
            if r["classes"] != [1, 2, 3, 4]:
                reasons.append("missing a priority class")
            if r["bracket_up"] < n21.FLOOR_BH:
                reasons.append("no lateness without a change")
            if s in ORDINARY_STRATA and r["window_bh"] > MAX_ORDINARY_WINDOW_BH:
                reasons.append("arrival window longer than one working week")
            if reasons:
                skipped.append(collections.OrderedDict(
                    file=iid + ".json", instance_id=iid, priority_classes=r["classes"],
                    bracket_upper_bh=rnd(r["bracket_up"]), window_bh=rnd(r["window_bh"]),
                    reasons=reasons))
                continue
            ok.append((iid, kind_stats(r["rows"])["share_020"] or 0.0))
        ranking[s] = sorted(ok, key=lambda x: (-x[1], x[0]))
    best = {s: (ranking[s][0][1] if ranking[s] else 0.0) for s in STRATA}
    if override is not None:
        alloc = collections.OrderedDict(override)
        reason = "set by --cards-per-stratum"
        rule = "override"
    else:
        alloc = collections.OrderedDict(DEFAULT_CARDS)
        dropped = [s for s in STRATA if alloc[s] > 0 and best[s] < MIN_SHARE]
        if not dropped:
            reason = ("{}; every stratum has an instance with a costly share of at least 5% "
                      "({})".format(default_reason(instances), ", ".join(
                          "{} {}".format(STRATUM_NAME[s], pct(best[s])) for s in STRATA)))
            rule = "default"
        else:
            freed = sum(alloc[s] for s in dropped)
            keep = [s for s in STRATA if s not in dropped]
            if not keep:
                raise SystemExit("no stratum has an instance with a costly share of 5%")
            total = sum(alloc.values())
            wsum = sum(REALLOC_WEIGHT[s] for s in keep)
            quota = {s: freed * REALLOC_WEIGHT[s] / wsum for s in keep}
            add = {s: int(quota[s]) for s in keep}
            left = freed - sum(add.values())
            for s in sorted(keep, key=lambda s: (-(quota[s] - add[s]), STRATA.index(s)))[:left]:
                add[s] += 1
            for s in dropped:
                alloc[s] = 0
            for s in keep:
                alloc[s] += add[s]
            assert sum(alloc.values()) == total
            reason = ("{} reached no costly share of 5% (best {}); its {} card(s) went to {} "
                      "by the 2:1 rule".format(", ".join(STRATUM_NAME[s] for s in dropped),
                                               ", ".join(pct(best[s]) for s in dropped), freed,
                                               ", ".join("{} +{}".format(STRATUM_NAME[s], add[s])
                                                         for s in keep)))
            rule = "reallocated"
    assert sum(alloc.values()) == 8, alloc
    for s in STRATA:
        if len(ranking[s]) < alloc[s]:
            raise SystemExit("stratum {} has {} screened four-class instances for {} cards".format(
                s, len(ranking[s]), alloc[s]))
    chosen = []
    for s in STRATA:
        for iid, sh in ranking[s][:alloc[s]]:
            chosen.append((s, iid, sh))
    return {"ranking": ranking, "best": best, "alloc": alloc, "rule": rule, "reason": reason,
            "skipped": skipped, "chosen": chosen}


# --------------------------------------------------------------------------- #
# Part 2: the sixteen orders of a card                                         #
# --------------------------------------------------------------------------- #
def select_orders_r2(card_no, inst, base, frozen, suite_refs, rows):
    rng = random.Random(SEED + card_no)
    wos = sorted(inst["work_orders"], key=lambda w: w["id"])
    by_id = {w["id"]: w for w in wos}
    asg = {a["wo"]: a for a in base["assignments"]}
    window = float(inst["meta"]["window_bh"])
    chosen: list = []
    role = collections.defaultdict(list)
    pick = {}
    step = {}

    def free(pool):
        taken = set(chosen)
        return sorted({o for o in pool if o not in taken})

    def put(o, tag, how, st):
        chosen.append(o)
        role[o].append(tag)
        pick.setdefault(o, how)
        step.setdefault(o, st)

    def draw(pool, n, tag, how, st):
        pool = free(pool)
        picks = rng.sample(pool, min(n, len(pool)))
        for o in picks:
            put(o, tag, how, st)
        return picks

    def take(ordered, n, tag, how, st):
        got = []
        taken = set(chosen)
        for o in ordered:
            if len(got) == n:
                break
            if o not in taken:
                put(o, tag, how, st)
                got.append(o)
        return got

    def of(t, v=""):
        return [r for r in rows if r["candidate_type"] == t and r["variant"] == v]

    # 1. in progress
    for o in frozen:
        put(o, "in_progress", "suite_frozen_set", 1)

    # 2. four urgent orders
    h16 = {r["focus_order"]: r for r in of("HOLD", "shift_16")}
    costly = [o for o, r in h16.items() if r["accepted"] and r["costly_020"] == 1]
    got = draw(costly, 4, "urgent", "hold16_costly", 2)
    if len(got) < 4:
        rest = sorted((o for o, r in h16.items() if r["accepted"] and r["damage_bh"] is not None),
                      key=lambda o: (-h16[o]["damage_bh"], o))
        got += take(rest, 4 - len(got), "urgent", "hold16_largest_damage", 2)
    assert len(got) == 4, ("urgent", card_no, got)
    urgent = list(got)

    # 3. three long jobs
    pr = {r["focus_order"]: r for r in of("PROMOTE")}
    costly = [o for o, r in pr.items() if r["accepted"] and r["costly_020"] == 1]
    got = draw(costly, 3, "long", "promote_costly", 3)
    if len(got) < 3:
        rest = sorted((o for o, r in pr.items() if r["accepted"] and r["damage_bh"] is not None),
                      key=lambda o: (-pr[o]["damage_bh"], o))
        got += take(rest, 3 - len(got), "long", "promote_largest_damage", 3)
    assert len(got) == 3, ("long", card_no, got)

    # 4. two late arrivals
    us = set(urgent)
    partners = sorted({r["partner_order"] for r in of("PRECEDENCE", "late_arrival")
                       if r["accepted"] and r["costly_020"] == 1 and r["focus_order"] in us})
    got = draw(partners, 2, "late_arrival", "precedence_costly_with_urgent", 4)
    if len(got) < 2:
        late = [w["id"] for w in wos if float(w["release_bh"]) >= window / 2.0]
        got += draw(late, 2 - len(got), "late_arrival", "draw", 4)
    assert len(got) == 2, ("late arrivals", card_no, got)

    # 5. building pairs (field_cards' rule), on instances with building codes
    has_buildings = any(w["building"] is not None for w in wos)
    if has_buildings:
        groups = collections.defaultdict(list)
        for o in free(by_id):
            w = by_id[o]
            if w["building"] is not None:
                groups[(w["building"], w["trade"])].append(o)
        eligible = sorted({b for (b, t), os_ in groups.items() if len(os_) >= 2})
        for b in rng.sample(eligible, 2):
            cells = sorted(t for (bb, t), os_ in groups.items() if bb == b and len(os_) >= 2)
            t = rng.choice(cells)
            draw(groups[(b, t)], 2, "building_pair", "draw", 5)

    # 6. coverage of classes and trades (field_cards' rule)
    for cls in (1, 2, 3, 4):
        if not any(int(by_id[o]["priority"]) == cls for o in chosen):
            draw([w["id"] for w in wos if int(w["priority"]) == cls], 1, "class_cover", "draw", 6)
    while len({by_id[o]["trade"] for o in chosen}) < 4:
        have = {by_id[o]["trade"] for o in chosen}
        draw([w["id"] for w in wos if w["trade"] not in have], 1, "trade_cover", "draw", 6)

    # 7. fill (field_cards' rule)
    assert len(chosen) <= N_ROWS, (card_no, len(chosen))
    free_rows = N_ROWS - len(chosen)
    n_ref = (free_rows + 1) // 2
    refs = [o for o in suite_refs if o in by_id]
    draw(refs, n_ref, "fill_suite", "draw", 7)
    early = [w["id"] for w in wos if float(w["release_bh"]) <= FIRST_DAY_BH]
    draw(early, N_ROWS - len(chosen), "fill", "draw", 7)
    if len(chosen) < N_ROWS:
        draw(list(by_id), N_ROWS - len(chosen), "fill", "draw", 7)
    assert len(chosen) == N_ROWS == len(set(chosen))

    fz = set(frozen)
    first = sorted(frozen, key=lambda o: (float(asg[o]["start_bh"]), o))
    rest = sorted((o for o in chosen if o not in fz), key=lambda o: (float(by_id[o]["due_bh"]), o))
    return {"order_ids": first + rest, "roles": {o: role[o] for o in chosen},
            "pick": pick, "step": step, "has_buildings": has_buildings}


def order_prices(o, rows):
    """Every screened candidate that names order ``o``, with its numbers."""
    out = []
    for r in rows:
        if o in r["orders_named"]:
            out.append(collections.OrderedDict(
                type=r["candidate_type"], variant=r["variant"], operation=json.loads(r["operation"]),
                decision_instant=rnd(r["decision_instant"]), issuable=r["issuable"],
                check_outcome=r["check_outcome"], damage_bh=rnd(r["damage_bh"]),
                cost_lo=rnd(r["cost_lo"]), cost_hi=rnd(r["cost_hi"]),
                costly_020=r["costly_020"], costly_010=r["costly_010"]))
    return out


def card_levers(order_ids, rows):
    """Per kind: displayed orders named by a candidate of that kind that is costly at 0.20."""
    on = set(order_ids)
    out = collections.OrderedDict()
    for (t, v), lab in KINDS.items():
        rs = [r for r in rows if r["candidate_type"] == t and r["variant"] == v
              and r["accepted"] and r["costly_020"] == 1]
        if t == "PRECEDENCE":
            both = [r for r in rs if r["focus_order"] in on and r["partner_order"] in on]
            out[lab] = {"orders": len({o for r in rs for o in r["orders_named"] if o in on}),
                        "pairs_on_card": len(both)}
        else:
            out[lab] = {"orders": len({o for r in rs for o in r["orders_named"] if o in on})}
    n_any = len({o for r in rows if r["accepted"] and r["costly_020"] == 1
                 for o in r["orders_named"] if o in on})
    out["any kind"] = {"orders": n_any}
    return out


def build_cards(inputs, instances, alloc):
    cards = []
    for card_no, (stratum, iid, sh) in enumerate(alloc["chosen"], start=1):
        rel, path, digest = inputs.checked_path(iid)
        instance = json.load(open(path))
        assert instance["meta"]["id"] == iid
        is_replay = instance["meta"]["track"] == "replay"
        base = FC1.dispatch.dispatch_baseline(instance, EPISODE_RULE, EPISODE_SEED)
        frozen = inputs.standing_frozen(iid, base)
        rec = instances[iid]
        assert frozen == rec["frozen"], (iid, frozen, rec["frozen"])
        sel = select_orders_r2(card_no, instance, base, frozen, inputs.suite_refs(iid),
                               rec["rows"])
        ids = sel["order_ids"]
        by_id = {w["id"]: w for w in instance["work_orders"]}
        assert all(o in by_id for o in ids), "order id not in instance"
        assert len(ids) == N_ROWS == len(set(ids)), (iid, "sixteen distinct orders")
        assert {int(by_id[o]["priority"]) for o in ids} == {1, 2, 3, 4}, (iid, "classes")
        assert len({by_id[o]["trade"] for o in ids}) >= 4, (iid, "trades")
        assert ids[:len(frozen)] == sorted(frozen, key=lambda o: (
            float({a["wo"]: a for a in base["assignments"]}[o]["start_bh"]), o)), iid
        roles = collections.Counter(t for v in sel["roles"].values() for t in v)
        for tag, n in (("urgent", 4), ("long", 3), ("late_arrival", 2),
                       ("in_progress", len(frozen))):
            assert roles[tag] == n, (iid, tag, roles)
        if sel["has_buildings"]:
            assert roles["building_pair"] == 4, (iid, roles)
        its = inputs.by_inst[iid]
        probe_item = (next(it for it in its if it["episode"].get("frozen_seed")) if frozen
                      else its[0])
        crew = FC1.crew_rows_from_prompt(instance, probe_item)
        assert crew == FC1.crew_rows_recomputed(instance), (iid, "crew table mismatch")
        cards.append({
            "card_no": card_no, "title": "Card {}".format(card_no), "instance_id": iid,
            "stratum": stratum, "snapshot_relpath": rel, "sha256": digest,
            "suite_items_on_instance": inputs.n_items[iid], "is_replay": is_replay,
            "frozen": frozen, "order_ids": ids, "roles": sel["roles"], "pick": sel["pick"],
            "step": sel["step"], "share_020": sh,
            "site": FC1.site_lines(instance, bool(frozen)), "crew": crew,
            "crew_display": [[r[0], FC1.gloss(r[0])] + r[1:] for r in crew],
            "board_header": FC1.board_header(is_replay),
            "board": FC1.board_rows(ids, instance, base, set(frozen), is_replay),
            "levers": card_levers(ids, rec["rows"]),
            "weekday": (_dt.datetime.fromisoformat(instance["meta"]["window_start"]).strftime("%A")
                        if is_replay else None),
        })
        b = cards[-1]["board"]
        near = sum(1 for o in ids if float(by_id[o]["release_bh"]) <= NEAR_BH + 1e-9)
        cards[-1]["board_counts"] = collections.OrderedDict(
            late_on_plan=sum(1 for r in b if r[-1].startswith("late")),
            available_at_hour_0=sum(1 for r in b if r[4] == "0.00"),
            available_within_16_bh=near,
            class_1_or_2=sum(1 for r in b if r[2] in ("1", "2")))
        if stratum in ORDINARY_STRATA and near < MIN_NEAR_ROWS:
            raise SystemExit("{} ({}): only {} of the 16 displayed orders are available within "
                             "{:g} working hours of the card's instant; at least {} are required "
                             "on an ordinary-day card".format(
                                 cards[-1]["title"], iid, near, NEAR_BH, MIN_NEAR_ROWS))
    return cards


def card_strings(card):
    out = [card["title"]] + list(card["site"]) + ["Crews and work by trade",
                                                  "Board: 16 of the open work orders", "Notes"]
    out += list(FC1.CREW_HEADER) + list(card["board_header"]) + list(FC1.NOTES)
    for r in card["crew_display"] + card["board"]:
        out += [str(x) for x in r]
    return out


def assert_no_hint(texts, where):
    for t in texts:
        low = str(t).lower()
        for w in BANNED_ON_CARDS:
            assert w not in low, ("card text contains '{}'".format(w), where, t)


# --------------------------------------------------------------------------- #
# Read me: the briefing, verbatim                                              #
# --------------------------------------------------------------------------- #
ITEM_RE = re.compile(r"^(?:[A-H]|\d+)\. ")


def briefing_blocks_r2():
    blocks = []
    for line in BRIEFING_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if line.startswith("# "):
            blocks.append(("title", line[2:]))
        elif line.startswith("## "):
            blocks.append(("head", line[3:]))
        elif ITEM_RE.match(line):
            blocks.append(("item", line))
        else:
            blocks.append(("para", line))
    return blocks


# --------------------------------------------------------------------------- #
# Workbook                                                                     #
# --------------------------------------------------------------------------- #
ANSWER_HEADER = ["Respondent code", "Card", "Situation (A-H)",
                 "Instruction (exactly as you would say or type it)",
                 "What should the system do?", "Is the delay it causes acceptable?",
                 "Hours (if you chose up to __ hours)", "How much delay do you expect it to cause?",
                 "Why (optional)"]
ANSWER_WIDTHS = [14, 10, 12, 70, 26, 26, 16, 26, 45]
ABOUT = [
    ("Respondent code", None),
    ("Your role (for example maintenance supervisor, facilities manager or dispatcher)", None),
    ("Years in facility management", "years"),
    ("How often do you approve work-order changes?", APPROVAL_CHOICES),
    ("Do you use a computerised maintenance management system (CMMS)?", YES_NO),
    ("Did you take part in the first set of this study?", YES_NO),
]


def write_workbook_r2(cards, path):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    FONT = "Times New Roman"
    f_body = Font(name=FONT, size=11)
    f_bold = Font(name=FONT, size=11, bold=True)
    f_title = Font(name=FONT, size=14, bold=True)
    f_head = Font(name=FONT, size=12, bold=True)
    thin = Side(style="thin", color="000000")
    wrap_top = Alignment(wrap_text=True, vertical="top")

    wb = Workbook()
    # ---- Read me (briefing_r2.md, verbatim)
    ws = wb.active
    ws.title = "Read me"
    ws.column_dimensions["A"].width = 110
    r = 1
    for kind, s in briefing_blocks_r2():
        c = ws.cell(row=r, column=1, value=s)
        c.alignment = wrap_top
        c.font = {"title": f_title, "head": f_head}.get(kind, f_body)
        if kind == "item":
            c.alignment = Alignment(wrap_text=True, vertical="top", indent=2)
        r += 1
        if kind in ("para", "title"):
            r += 1

    # ---- cards (the layout of the first workbook)
    for card in cards:
        ws = wb.create_sheet(card["title"])
        ws.cell(row=1, column=1, value=card["title"]).font = f_title
        r = 2
        for s in card["site"]:
            ws.cell(row=r, column=1, value=s).font = f_body
            r += 1
        r += 1

        def put_table(r, header, rows, right_cols):
            for j, h in enumerate(header, start=1):
                c = ws.cell(row=r, column=j, value=h)
                c.font = f_bold
                c.alignment = Alignment(wrap_text=True, vertical="bottom",
                                        horizontal="right" if j in right_cols else "left")
                c.border = Border(top=thin, bottom=thin)
            for row in rows:
                r += 1
                for j, v in enumerate(row, start=1):
                    c = ws.cell(row=r, column=j, value=v)
                    c.font = f_body
                    if j in right_cols:
                        c.alignment = Alignment(horizontal="right")
                        if v != "-":
                            c.value = float(v) if "." in v else int(v)
                            c.number_format = "0.00" if "." in v else "0"
            for j in range(1, len(header) + 1):
                ws.cell(row=r, column=j).border = Border(bottom=thin)
            return r + 2

        ws.cell(row=r, column=1, value="Crews and work by trade").font = f_head
        r += 1
        r = put_table(r, FC1.CREW_HEADER, card["crew_display"], {3, 4, 5, 6, 7, 8})
        ws.cell(row=r, column=1, value="Board: 16 of the open work orders").font = f_head
        r += 1
        r = put_table(r, card["board_header"], card["board"], {3, 4, 5, 6})
        ws.cell(row=r, column=1, value="Notes").font = f_bold
        for s in FC1.NOTES:
            r += 1
            ws.cell(row=r, column=1, value=s).font = f_body
        for j, w in enumerate([12, 24, 13, 13, 14, 18, 16, 14, 16], start=1):
            ws.column_dimensions[get_column_letter(j)].width = w
        ws.sheet_view.showGridLines = False

    # ---- dropdown values on a hidden sheet (several answers contain commas)
    lists_ws = wb.create_sheet("Lists")
    lists_ws.sheet_state = "hidden"
    list_cols = []

    def list_range(values):
        col = get_column_letter(len(list_cols) + 1)
        list_cols.append(col)
        for i, v in enumerate(values, start=1):
            lists_ws["{}{}".format(col, i)] = v
        return "Lists!${0}$1:${0}${1}".format(col, len(values))

    # ---- Answers
    ws = wb.create_sheet("Answers")
    for j, (h, w) in enumerate(zip(ANSWER_HEADER, ANSWER_WIDTHS), start=1):
        c = ws.cell(row=1, column=j, value=h)
        c.font = f_bold
        c.alignment = Alignment(wrap_text=True, vertical="top")
        c.border = Border(bottom=thin)
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.row_dimensions[1].height = 48
    n_rows = 200
    for i in range(2, n_rows + 2):
        for j in range(1, len(ANSWER_HEADER) + 1):
            c = ws.cell(row=i, column=j)
            c.font = f_body
            c.alignment = wrap_top
            if j == 7:
                c.number_format = "0.0"
    ws.freeze_panes = "A2"
    last = n_rows + 1

    def dv_list(values, col, title):
        dv = DataValidation(type="list", formula1=list_range(values),
                            allow_blank=True, showDropDown=False)
        dv.errorTitle = title
        dv.error = "Please choose one of the listed answers."
        dv.add("{0}2:{0}{1}".format(col, last))
        ws.add_data_validation(dv)

    dv_list(["Card {}".format(c["card_no"]) for c in cards], "B", "Card")
    dv_list([k for k, _ in FC1.SITUATIONS], "C", "Situation")
    dv_list(list(FC1.ACTION_CHOICES), "E", "What should the system do")
    dv_list(list(FC1.DELAY_CHOICES), "F", "Is the delay it causes acceptable")
    dv = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0",
                        allow_blank=True)
    dv.error = "Please enter a number of working hours."
    dv.add("G2:G{}".format(last))
    ws.add_data_validation(dv)
    dv_list(list(LATER_CHOICES), "H", "How much delay do you expect it to cause")

    # ---- About you
    ws = wb.create_sheet("About you")
    ws.column_dimensions["A"].width = 70
    ws.column_dimensions["B"].width = 40
    ws.cell(row=1, column=1, value="Question").font = f_bold
    ws.cell(row=1, column=2, value="Your answer").font = f_bold
    for j in (1, 2):
        ws.cell(row=1, column=j).border = Border(bottom=thin)
    for i, (q, choices) in enumerate(ABOUT, start=2):
        c = ws.cell(row=i, column=1, value=q)
        c.font = f_body
        c.alignment = wrap_top
        a = ws.cell(row=i, column=2)
        a.font = f_body
        a.border = Border(bottom=Side(style="hair", color="000000"))
        if choices == "years":
            dv = DataValidation(type="decimal", operator="greaterThanOrEqual",
                                formula1="0", allow_blank=True)
            dv.add("B{}".format(i))
            ws.add_data_validation(dv)
        elif choices:
            dv = DataValidation(type="list", formula1=list_range(choices), allow_blank=True)
            dv.add("B{}".format(i))
            ws.add_data_validation(dv)
    ws.freeze_panes = "A2"

    wb.move_sheet("Lists", offset=len(wb.sheetnames) - 1 - wb.sheetnames.index("Lists"))
    wb.properties.creator = ""
    wb.properties.lastModifiedBy = ""
    wb.properties.title = "Field instruction workbook, second set"
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def check_workbook_r2(path, cards, alloc):
    from openpyxl import load_workbook
    wb = load_workbook(path)
    expected = ["Read me"] + [c["title"] for c in cards] + ["Answers", "About you", "Lists"]
    assert wb.sheetnames == expected, wb.sheetnames
    assert wb["Lists"].sheet_state == "hidden"

    def list_values(formula):
        ref = formula.split("!")[1].replace("$", "")
        return [c.value for row in wb["Lists"][ref] for c in row]

    def validations(ws):
        out = {}
        for dv in ws.data_validations.dataValidation:
            ref = str(dv.sqref)
            out[ref] = (dv.type, list_values(dv.formula1) if dv.type == "list" else None)
        return out

    ans = validations(wb["Answers"])
    want = {"B2:B201": ("list", ["Card {}".format(c["card_no"]) for c in cards]),
            "C2:C201": ("list", [k for k, _ in FC1.SITUATIONS]),
            "E2:E201": ("list", list(FC1.ACTION_CHOICES)),
            "F2:F201": ("list", list(FC1.DELAY_CHOICES)),
            "G2:G201": ("decimal", None),
            "H2:H201": ("list", list(LATER_CHOICES))}
    assert ans == want, ans
    header = [c.value for c in wb["Answers"][1]]
    assert header == ANSWER_HEADER, header
    assert wb["Answers"].freeze_panes == "A2"
    assert wb["Answers"].max_row == 201, wb["Answers"].max_row
    about = validations(wb["About you"])
    want_about = {"B4": ("decimal", None), "B5": ("list", list(APPROVAL_CHOICES)),
                  "B6": ("list", list(YES_NO)), "B7": ("list", list(YES_NO))}
    assert about == want_about, about
    qs = [r[0].value for r in wb["About you"].iter_rows(min_row=2) if r[0].value]
    assert qs == [q for q, _ in ABOUT], qs
    banned = ("name", "employer", "email", "e-mail", "phone", "company")
    for f in [h for h in header if h] + qs:
        assert not any(b in str(f).lower() for b in banned), f
    readme = [c.value for row in wb["Read me"].iter_rows() for c in row if c.value is not None]
    assert readme == [t for _k, t in briefing_blocks_r2()], "Read me differs from the briefing"
    mix = card_mix(readme, alloc, cards)
    for card in cards:
        ws = wb[card["title"]]
        cells = [str(c.value) for row in ws.iter_rows() for c in row if c.value is not None]
        for o in card["order_ids"]:
            assert o in cells, (card["title"], o)
        assert_no_hint(cells, card["title"] + " sheet")
    return {"sheets": wb.sheetnames, "answers_validations": sorted(ans),
            "about_validations": sorted(about), "answer_rows": wb["Answers"].max_row - 1,
            "card_mix": mix}


def check_pdf(path, cards):
    raw = path.read_bytes()
    n_pages = len(re.findall(rb"/Type\s*/Page[^s]", raw))
    info = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=True)
    m = re.search(r"^Pages:\s+(\d+)", info.stdout, re.M)
    assert m and int(m.group(1)) == len(cards) == n_pages == 8, (n_pages, info.stdout)
    txt = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True,
                         text=True, check=True).stdout
    pages = txt.split("\f")
    pages = [p for p in pages if p.strip()]
    assert len(pages) == 8, len(pages)
    for card, page in zip(cards, pages):
        assert card["title"] in page, card["title"]
        for o in card["order_ids"]:
            assert o in page, (card["title"], o)
        assert_no_hint([page], card["title"] + " page")
    return {"pages": len(pages)}


# --------------------------------------------------------------------------- #
# Manifest                                                                     #
# --------------------------------------------------------------------------- #
def build_manifest(cards, instances, alloc, screen_meta, selftest, wb_check, pdf_check):
    def inst_screen(iid):
        rec = instances[iid]
        st = instance_stats(rec)
        rank = [i for i, _ in alloc["ranking"][rec["stratum"]]].index(iid) + 1
        return collections.OrderedDict(
            rank_in_stratum=rank, threshold_bh_020=rnd(rec["threshold_bh"]),
            bracket_upper_bh=rnd(rec["bracket_up"]), anchor_wwt_bh=rnd(rec["anchor_wwt"]),
            by_kind=collections.OrderedDict((k, stats_json(v)) for k, v in st.items()),
            pools=rec["pools"])

    m = collections.OrderedDict()
    m["schema"] = VERSION
    m["generator"] = "code/scripts/field_cards_r2.py"
    m["seed"] = SEED
    m["snapshot"] = SNAPSHOT_NAME
    m["snapshot_note"] = ("snapshot_relpath is relative to the instances_v10 snapshot; each "
                          "file's sha256 equals its entry in code/scripts/instance_manifest_l1.json")
    m["episode"] = {"rule": EPISODE_RULE, "seed": EPISODE_SEED, "t_bh": 0.0}
    m["assignment_rule"] = ("respondent {}k receives cards ((k-1) mod 8)+1 and ((k+3) mod 8)+1"
                            .format(RESPONDENT_LETTER))
    strat = {c["title"]: c["stratum"] for c in cards}
    pairs = collections.OrderedDict()
    for k in range(1, 9):
        a, b = ["Card {}".format(x) for x in FC1.assignment(k)]
        pairs["{}{}".format(RESPONDENT_LETTER, k)] = [a, b]
    m["assignment_first_eight"] = pairs
    m["assignment_strata"] = collections.OrderedDict(
        (p, [strat[c] for c in cs]) for p, cs in pairs.items())
    m["assignment_same_stratum_pairs"] = [p for p, cs in pairs.items()
                                          if strat[cs[0]] == strat[cs[1]]]
    m["assignment_note"] = assignment_note(alloc)
    m["screening"] = collections.OrderedDict(
        version=VERSION, candidates_file="participant_files/field_instructions_r2/screening_candidates.csv",
        priced_by="n21_field_instructions.py evaluate path (Site, unit_record) at the decision "
                  "instant of n11_decision_time.issuability / decision_instant_of (primary)",
        classes="costly when cost_lo > level; low-cost when cost_hi <= level; levels 0.20 and 0.10",
        threshold_bh_020="0.20 x max(upper end of the full-window bracket, 1 bh)",
        draw_seed="random.Random(SEED + instance index in the screening order)",
        instances_screened=[iid for iid in instances],
        instances_per_stratum=collections.OrderedDict(
            (s, sum(1 for r in instances.values() if r["stratum"] == s)) for s in STRATA),
        candidates=sum(len(r["rows"]) for r in instances.values()),
        self_test=collections.OrderedDict((k, v) for k, v in selftest.items() if k != "wall_s"))
    m["allocation"] = collections.OrderedDict(
        default=collections.OrderedDict(DEFAULT_CARDS), used=alloc["alloc"], rule=alloc["rule"],
        reason=alloc["reason"], min_share=MIN_SHARE,
        best_share_by_stratum=collections.OrderedDict((s, rnd(alloc["best"][s])) for s in STRATA),
        ranking=collections.OrderedDict((s, [[iid, rnd(sh)] for iid, sh in alloc["ranking"][s]])
                                        for s in STRATA))
    m["cards"] = []
    for c in cards:
        rows = instances[c["instance_id"]]["rows"]
        m["cards"].append(collections.OrderedDict(
            card_id=c["title"], instance_id=c["instance_id"], stratum=c["stratum"],
            snapshot_relpath=c["snapshot_relpath"], sha256=c["sha256"],
            suite_items_on_instance=c["suite_items_on_instance"],
            frozen_set_shown=c["frozen"], order_ids=c["order_ids"],
            selection_roles={o: c["roles"][o] for o in c["order_ids"]},
            allocation_rule=collections.OrderedDict(
                rule=alloc["rule"], stratum_cards=alloc["alloc"][c["stratum"]],
                choice="rank {} of {} in {} by the share of issuable, accepted candidates that "
                       "are costly at 0.20".format(
                           [i for i, _ in alloc["ranking"][c["stratum"]]].index(c["instance_id"]) + 1,
                           len(alloc["ranking"][c["stratum"]]), c["stratum"])),
            screening=inst_screen(c["instance_id"]),
            levers_on_card=c["levers"],
            board_counts=c["board_counts"],
            orders=collections.OrderedDict(
                (o, collections.OrderedDict(step=c["step"][o], roles=c["roles"][o],
                                            pick=c["pick"][o], prices=order_prices(o, rows)))
                for o in c["order_ids"])))
    m["instances_skipped"] = alloc["skipped"]
    m["workbook_check"] = wb_check
    m["pdf_check"] = pdf_check
    return json.dumps(m, indent=1) + "\n"


# --------------------------------------------------------------------------- #
# Report and README                                                            #
# --------------------------------------------------------------------------- #
def fmt_dmg(x):
    return "-" if x is None else "{:.1f}".format(x)


def assignment_note(alloc):
    strat = [s for s in STRATA for _ in range(alloc["alloc"][s])]
    same = [k for k in range(1, 9)
            if strat[FC1.assignment(k)[0] - 1] == strat[FC1.assignment(k)[1] - 1]]
    campus = [s[:3] for s in strat]
    mixed = all(campus[FC1.assignment(k)[0] - 1] != campus[FC1.assignment(k)[1] - 1]
                for k in range(1, 9))
    if alloc["alloc"]["c09_storm2_w80"] == 4 and mixed:
        out = ("Each respondent receives one campus 9 card (Cards 1 to 4) and one campus 10 card "
               "(Cards 5 to 8), and eight respondents cover every card twice.")
    else:
        out = "Eight respondents cover every card twice; the campus mix differs by respondent."
    if same:
        out += " Respondents {} receive two cards of one stratum.".format(
            ", ".join("{}{}".format(RESPONDENT_LETTER, k) for k in same))
    return out


def write_report(instances, alloc, cards, selftest, screen_meta, timing, inputs, screen,
                 wb_mix):
    L = []
    L.append("# Screening for the second field-instruction collection")
    L.append("")
    L.append("Generated by `code/scripts/field_cards_r2.py` ({}). Every number below is a "
             "deterministic dispatch priced by the evaluation path of "
             "`n21_field_instructions.py`; no solver, no model.".format(VERSION))
    L.append("")
    L.append("## What was screened")
    L.append("")
    n_all = len(inputs.meta)
    per = collections.Counter(r["stratum"] for r in instances.values())
    n_of = {s: sum(1 for m in inputs.meta.values() if m["stratum"] == s) for s in STRATA}
    part = [s for s in STRATA if per[s] < n_of[s]]
    L.append("{} of the suite's {} instances were screened: {}.{}".format(
        len(instances), n_all, ", ".join("{} {} of {}".format(s, per[s], n_of[s])
                                         for s in STRATA),
        "" if not part else " To keep the screening within about 40 minutes on one core, "
        "{} was screened in part, on its instances with the most suite items (one "
        "c10_storm2_w80 instance takes 3 to 4 minutes; all 60 instances would take about "
        "50).".format(", ".join(part))))
    L.append("")
    L.append("The episode is the one the cards show (rule ATC, seed 0, the instance's standing "
             "frozen set where the suite uses one). Each candidate is one operation, priced at "
             "its decision instant. \"Accepted\" means issuable and passed by the schema and "
             "feasibility checks; shares are taken over accepted candidates. The cost level is "
             "0.20 times the upper end of the instance's full-window bracket, in weighted "
             "business hours (bh).")
    L.append("")
    L.append("Candidates per instance (each pool sorted by order id, draws seeded per instance):")
    L.append("")
    L.append("- HOLD: `reassign_window` with `release_shift_bh` +16 and +40 on each of the 16 "
             "class-1 or class-2 orders with the earliest due time, orders in progress excluded. "
             "On the storm boards no corrective order is open at the window start (every order "
             "known at t = 0 is planned maintenance of class 4), so each HOLD is priced at the "
             "instant its order becomes known, which is the benchmark's rule. The operation moves "
             "the release and restarts the response clock (due = new release + response window), "
             "while the realised cost is measured on the original due times.")
    L.append("- PROMOTE: `pin_next` on each class-3 or class-4 order among the 20 orders with "
             "the most hours of work (at most 12, drawn).")
    L.append("- PRECEDENCE: `reorder` with `relation` \"before\", `order_id` the other order and "
             "`ref_order_id` the urgent order, as the suite's cost-bearing items write it: the "
             "urgent order may start only once the other has started. The other order is a late "
             "arrival (released in the second half of the arrival window), source (a), or a "
             "PROMOTE order, source (b); at most 24 pairs from each.")
    L.append("- DOWNGRADE: `set_priority` to class 4 on each class-1 order of the HOLD pool "
             "(at most 8, drawn).")
    L.append("- BATCH (boards with building codes): `batch` for up to 8 drawn (building, trade) "
             "pairs with at least two orders not in progress; the candidate names every order "
             "of the pair, as the suite's batch items do.")
    L.append("")
    L.append("## Self-test")
    L.append("")
    L.append("{} suite reference proposals of the screened instances ({}; published class at "
             "0.20: {}) were priced by the screening function. The decision instant and the "
             "class at 0.20 and at 0.10 equal `analysis/N18_fig_price_k_fi.csv` for all {} "
             "(file `screening_selftest.csv`). {} of them are one-operation proposals; operation "
             "types: {}.".format(
                 selftest["n"], ", ".join("{} {}".format(k, v)
                                          for k, v in selftest["by_stratum"].items()),
                 ", ".join("{} x{}".format({"1": "costly", "0": "low-cost"}[k], v)
                           for k, v in selftest["by_published_class"].items()),
                 selftest["n_match"], selftest["single_operation"],
                 ", ".join("{} {}".format(k or "no operation", v)
                           for k, v in selftest["op_types"].items())))
    L.append("")
    L.append("## Timing")
    L.append("")
    evs = [r["eval_s"] for rec in instances.values() for r in rec["rows"]
           if r["eval_s"] is not None]
    for s in STRATA:
        e = [r["eval_s"] for rec in instances.values() if rec["stratum"] == s
             for r in rec["rows"] if r["eval_s"] is not None]
        if e:
            L.append("- {}: {} evaluations, mean {:.2f} s, longest {:.2f} s per evaluation "
                     "(site construction included).".format(s, len(e), sum(e) / len(e), max(e)))
    L.append("- Probe before the run: {}.".format("; ".join(
        "{} site {:.2f} s, evaluation {:.2f} s".format(s, a, b) for s, (a, b) in timing.items())))
    L.append("- This run: {} evaluations computed, cache {}; screening wall time {:.0f} s; "
             "{} evaluations recorded in total.".format(
                 screen_meta["evaluated_now"], screen_meta["cache"], screen_meta["wall_s"],
                 len(evs)))
    L.append("")
    L.append("## Per stratum, by candidate type")
    L.append("")
    for s in STRATA:
        recs = [r for r in instances.values() if r["stratum"] == s]
        if not recs:
            continue
        rows = [r for rec in recs for r in rec["rows"]]
        thr = [rec["threshold_bh"] for rec in recs]
        L.append("### {} ({}), {} instances, cost level {:.1f} to {:.1f} bh".format(
            s, STRATUM_NAME[s], len(recs), min(thr), max(thr)))
        L.append("")
        L.append("| Candidate type | Generated | Not issuable | Refused | Accepted | Costly at "
                 "0.20 | Costly at 0.10 | Largest damage (bh) |")
        L.append("|---|---:|---:|---:|---:|---:|---:|---:|")
        for (t, v), lab in list(KINDS.items()) + [(("ALL", ""), "All")]:
            sub = rows if t == "ALL" else [r for r in rows if r["candidate_type"] == t
                                           and r["variant"] == v]
            if not sub:
                continue
            k = kind_stats(sub)
            L.append("| {} | {} | {} | {} | {} | {} ({}) | {} ({}) | {} |".format(
                lab, k["generated"], k["not_issuable"], k["refused"], k["accepted"],
                k["costly_020"], pct(k["share_020"]), k["costly_010"], pct(k["share_010"]),
                fmt_dmg(k["max_damage_bh"])))
        L.append("")
    L.append("## Per instance")
    L.append("")
    L.append("Columns per type give costly at 0.20 / accepted. Shares are over all accepted "
             "candidates of the instance.")
    L.append("")
    short = ["H16", "H40", "PRO", "PRE(a)", "PRE(b)", "DOWN", "BAT"]
    L.append("| Instance | Items | Classes | Level (bh) | Generated | Not issuable | Refused | "
             "Accepted | Costly 0.20 | Costly 0.10 | Largest damage (bh) | " + " | ".join(short) + " |")
    L.append("|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|" + "---:|" * len(short))
    for iid, rec in instances.items():
        st = instance_stats(rec)
        a = st["all"]
        cells = []
        for (t, v) in KINDS:
            k = st["{}{}".format(t, ("/" + v) if v else "")]
            cells.append("-" if not k["generated"] else "{}/{}".format(k["costly_020"],
                                                                       k["accepted"]))
        L.append("| {} | {} | {} | {:.1f} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            iid, inputs.n_items[iid], "".join(str(c) for c in rec["classes"]),
            rec["threshold_bh"], a["generated"], a["not_issuable"], a["refused"], a["accepted"],
            pct(a["share_020"]), pct(a["share_010"]), fmt_dmg(a["max_damage_bh"]),
            " | ".join(cells)))
    L.append("")
    L.append("## Ranking used for the cards")
    L.append("")
    L.append("Instances that carry all four priority classes, ranked within each stratum by the "
             "share of accepted candidates that are costly at 0.20 (ties by id).")
    L.append("")
    for s in STRATA:
        rk = alloc["ranking"][s]
        L.append("- {} ({}): {}".format(s, STRATUM_NAME[s], ", ".join(
            "{} {}".format(iid, pct(sh)) for iid, sh in rk) or "none screened"))
    for why in ("missing a priority class", "no lateness without a change",
                "arrival window longer than one working week"):
        xs = [x for x in alloc["skipped"] if why in x["reasons"]]
        if xs:
            L.append("- Left out, {}: {}".format(why, ", ".join(
                "{} (classes {}, bracket upper end {} bh, arrival window {} bh)".format(
                    x["instance_id"], "".join(str(c) for c in x["priority_classes"]),
                    "{:.1f}".format(x["bracket_upper_bh"]), "{:.1f}".format(x["window_bh"]))
                for x in xs)))
    L.append("")
    L.append("A board has no lateness without a change when the upper end of its full-window "
             "bracket is below 1 bh, so that the floor of 1 bh sets its cost level (0.2 bh). "
             "An ordinary-day board whose orders arrive over more than {:g} working hours (one "
             "working week) is also left out, because its displayed orders would become "
             "available days or weeks from now. These boards stay in the screening tables "
             "above.".format(MAX_ORDINARY_WINDOW_BH))
    L.append("")
    L.append("## Allocation")
    L.append("")
    L.append("Cards per stratum: {}. Rule: {}. Reason: {}.".format(", ".join(
        "{} {}".format(s, alloc["alloc"][s]) for s in STRATA), alloc["rule"], alloc["reason"]))
    L.append("")
    L.append("## The eight cards")
    L.append("")
    L.append("Lever columns: displayed orders named by a candidate of that type that is costly "
             "at 0.20 (for PRECEDENCE also the costly pairs with both orders on the card).")
    L.append("")
    L.append("The last four columns count the 16 displayed rows: late on the current plan, "
             "available at hour 0, available within {:g} working hours, and of class 1 or 2. "
             "Every ordinary-day card must have at least {} rows available within {:g} working "
             "hours.".format(NEAR_BH, MIN_NEAR_ROWS, NEAR_BH))
    L.append("")
    L.append("| Card | Instance | Stratum | Level (bh) | Accepted | Costly 0.20 | H16 | H40 | "
             "PRO | PRE(a) | PRE(b) | DOWN | BAT | Any | Late | Hour 0 | Within 16 bh | "
             "Class 1-2 |")
    L.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
             "---:|")
    for c in cards:
        rec = instances[c["instance_id"]]
        a = kind_stats(rec["rows"])
        lv = c["levers"]
        cols = []
        for lab in KINDS.values():
            x = lv[lab]
            cols.append(str(x["orders"]) + (" (pairs {})".format(x["pairs_on_card"])
                                            if "pairs_on_card" in x else ""))
        bc = c["board_counts"]
        L.append("| {} | {} | {} | {:.1f} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            c["title"], c["instance_id"], STRATUM_NAME[c["stratum"]], rec["threshold_bh"],
            a["accepted"], pct(a["share_020"]), " | ".join(cols), lv["any kind"]["orders"],
            bc["late_on_plan"], bc["available_at_hour_0"], bc["available_within_16_bh"],
            bc["class_1_or_2"]))
    L.append("")
    mix = wb_mix
    L.append("Card mix: the briefing's sentence \"{}\" agrees with the allocation ({} storm, {} "
             "ordinary).".format(mix["sentence"], mix["storm"], mix["ordinary"]))
    if mix["weekday_mismatch"]:
        L.append("")
        L.append("Weekday: the sentence names {}, but {} {} another day ({}).".format(
            mix["weekday_in_sentence"], ", ".join(t for t, _d in mix["weekday_mismatch"]),
            "shows" if len(mix["weekday_mismatch"]) == 1 else "show",
            ", ".join("{} {}".format(t, d) for t, d in mix["weekday_mismatch"])))
    L.append("")
    L.append("Assignment: respondent {}k receives cards ((k-1) mod 8)+1 and ((k+3) mod 8)+1 "
             "(codes {}1 to {}8). ".format(RESPONDENT_LETTER, RESPONDENT_LETTER,
                                         RESPONDENT_LETTER) + assignment_note(alloc))
    REPORT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")


def write_readme(alloc, instances):
    per = collections.Counter(r["stratum"] for r in instances.values())
    text = """# Field-instruction collection, second set

| File | What it is |
|---|---|
| `briefing_r2.md` | One-page briefing for respondents. The same text is the "Read me" sheet of the workbook. |
| `cards/Scenario_Cards_R2.pdf` | The eight scenario cards, one A4 page each. |
| `Field_Instruction_Workbook_R2.xlsx` | Sheets "Read me", "Card 1" to "Card 8" (same content as the PDF), "Answers" (200 rows; dropdowns for card, situation, what the system should do, whether the delay it causes is acceptable and how much delay it is expected to cause), "About you" (role, years, how often you approve work-order changes, CMMS use, part in the first set). A hidden sheet "Lists" holds the dropdown values, because some answers contain commas. |
| `card_manifest_r2.json` | Per card: instance id, snapshot path and sha256, stratum, the 16 order ids in display order, the in-progress set, the allocation rule, the instance's screening numbers and, per displayed order, the extract step that placed it and the price of every screened change that names it. Also the card assignment rule. Not for respondents. |
| `screening_candidates.csv` | One row per screened candidate change: instance, type, the operation, the orders it names, decision instant, issuable, check outcome, realised damage, cost bracket, class at 0.20 and 0.10, the cost level in weighted business hours. The script reads it as a cache. |
| `screening_selftest.csv` | The suite reference proposals used to check the screening against the published classes. |
| `screening_report.md` | The screening per stratum and per instance, the ranking, the allocation and the eight cards. |

## Regenerate

```
OMP_NUM_THREADS=1 python code/scripts/field_cards_r2.py
```

Run from the repository root, on the project's core, one thread. The script reads
instances only from the `instances_v10` snapshot and checks every file against
`code/scripts/instance_manifest_l1.json`. It prices every candidate with the
evaluation code of `code/scripts/n21_field_instructions.py` and first asserts
that this code is the one n21's verification passed on. When
`screening_candidates.csv` is present and was written by the same code, the
screening is read from it; delete the file to recompute (about 40 minutes).
Two runs give a byte-identical `card_manifest_r2.json`. The full rules are in the
script's header.

## Screening

The aim is to find boards and orders on which a simple change has a price. On
each screened board the script tries a fixed set of one-operation changes, each
at the moment the orders it names are first known (the benchmark's own rule):

- hold an urgent order (class 1 or 2) for 16 and for 40 working hours, on the 16
  urgent orders with the earliest due time;
- put a long low-priority job (class 3 or 4, among the 20 longest) first in its
  trade's queue;
- make an urgent order wait until another order has started, the other order
  being a late arrival or one of the long jobs;
- lower an urgent class-1 order to class 4;
- on boards with building codes, group one trade's orders in one building.

Each change goes through the schema and feasibility checks and is then run to
the end of the window. Its realised cost is the extra weighted tardiness on the
original due times, relative to the instance's full-window bracket. A change is
costly at 0.20 when the whole cost bracket lies above 0.20; the matching cost
level in weighted business hours is in the report. A change that names an order
which has already started at that moment is not issuable and is not priced.
Screened: {screened}.

## Card selection

Within each stratum, boards that carry all four priority classes are ranked by
the share of accepted changes that are costly at 0.20. Ordinary-day boards
without lateness (the upper end of the full-window bracket below 1 bh, so that
the 1 bh floor sets the cost level) or with an arrival window above one working
week (40 working hours) are left out of the ranking; they stay in the screening
tables. Every ordinary-day card shows at least 8 orders that are available
within 16 working hours. The cards go to the top-ranked boards: by default 4
storm boards of campus 9 (Cards 1 to 4), 1 storm board of campus 10 (Card 5) and
3 ordinary days of campus 10 with building codes (Cards 6 to 8). The reason for
this default: {reason}. A stratum with no board above a 5% costly share gives
its cards to the others (2:1 in favour of campus 9). Allocation used: {alloc}.

Each card shows 16 orders: the work in progress, four urgent orders, three long
jobs, two late arrivals (on the building cards also two pairs of orders in one
building), then orders that complete the four priority classes and four trades,
then a fill as on the first cards. The urgent orders, long jobs and late
arrivals are drawn first from those whose simple change is costly. The card
itself shows only what the first cards showed; which orders carry a price is
recorded in `card_manifest_r2.json` only.

## Card assignment

Respondent {q}k receives cards ((k-1) mod 8)+1 and ((k+3) mod 8)+1. The
second-set codes are {q}1 to {q}8, so that they cannot be confused with the
first set's P codes. {pairs} Name the two cards and the respondent code in the
invitation. Each respondent can receive the same workbook.
""".format(screened=", ".join("{} {} instances".format(s, per[s]) for s in STRATA),
           alloc=", ".join("{} {}".format(s, alloc["alloc"][s]) for s in STRATA),
           reason=(default_reason(instances) if alloc["rule"] == "default"
                   else alloc["reason"]), pairs=assignment_note(alloc), q=RESPONDENT_LETTER)
    README_PATH.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", action="store_true",
                    help="count candidates and time one evaluation per stratum; no screening")
    ap.add_argument("--screen-per-stratum", default=None,
                    help="instances screened per stratum, e.g. 24,5,24")
    ap.add_argument("--cards-per-stratum", default=None,
                    help="cards per stratum, overriding the allocation rule, e.g. 4,2,2")
    args = ap.parse_args(argv)
    t_run = time.time()
    assert Path(FC1.SNAPSHOT_ROOT).resolve() == Path(n21.SNAPSHOT_ROOT).resolve()
    assert BRIEFING_PATH.is_file(), BRIEFING_PATH
    briefing_sha = FC1.sha256(BRIEFING_PATH)
    code_sha = assert_verified()
    inputs = Inputs()
    per = (parse_triple(args.screen_per_stratum, "--screen-per-stratum")
           if args.screen_per_stratum else SCREEN_PER_STRATUM)
    override = (parse_triple(args.cards_per_stratum, "--cards-per-stratum")
                if args.cards_per_stratum else None)
    screen = []
    for s in STRATA:
        ids = [iid for ss, iid in inputs.screening_order() if ss == s]
        screen += ids[:per[s]]
    screen = set(screen)
    P = Pricer(inputs)

    print("[r2] timing probe", flush=True)
    counts, timing, projected = plan(inputs, P, screen)
    print("[r2] {} instances, {} candidates ({} issuable), {} decision instants; projected "
          "{:.0f} s without the cache".format(
              len(counts), sum(v[1] for v in counts.values()), sum(v[2] for v in counts.values()),
              sum(v[3] for v in counts.values()), projected), flush=True)
    if args.plan:
        for iid, (s, n, n_iss, n_td) in counts.items():
            print("  {:28s} {:15s} candidates {:3d} issuable {:3d} instants {:3d}".format(
                iid, s, n, n_iss, n_td))
        return 0
    if projected > 1.5 * BUDGET_S and not CACHE_CSV.is_file():
        print("[r2] warning: projected time {:.0f} s exceeds the budget".format(projected),
              flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    selftest = self_test(inputs, P, screen)
    instances, screen_meta = screen_instances(inputs, P, screen, code_sha)
    alloc = rank_and_allocate(instances, override)
    cards = build_cards(inputs, instances, alloc)
    card_mix([t for _k, t in briefing_blocks_r2()], alloc["alloc"], cards)
    for c in cards:
        assert_no_hint(card_strings(c), c["title"])
    FC1.render_pdf(cards, PDF_PATH)
    pdf_check = check_pdf(PDF_PATH, cards)
    write_workbook_r2(cards, XLSX_PATH)
    wb_check = check_workbook_r2(XLSX_PATH, cards, alloc["alloc"])
    text = build_manifest(cards, instances, alloc, screen_meta, selftest, wb_check, pdf_check)
    # the manifest again, from the cached rows and a fresh selection: byte-identical
    cache, state = read_cache(code_sha)
    assert state == "read"
    again = collections.OrderedDict()
    for iid, rec in instances.items():
        rows = [typed_row(cache[(iid, n21.frozen_key(rec["frozen"]), r["operation"])])
                for r in rec["rows"]]
        again[iid] = dict(rec, rows=rows)
    alloc2 = rank_and_allocate(again, override)
    cards2 = build_cards(inputs, again, alloc2)
    for c in cards2:
        c["pdf_bottom_mm"] = None
    text2 = build_manifest(cards2, again, alloc2, screen_meta, selftest, wb_check, pdf_check)
    assert text == text2, "manifest differs between two builds"
    MANIFEST_PATH.write_text(text, encoding="utf-8")
    write_report(instances, alloc, cards, selftest, screen_meta, timing, inputs, screen,
                 wb_check["card_mix"])
    if wb_check["card_mix"]["weekday_mismatch"]:
        print("[r2] note: the card-mix sentence names {} but {}".format(
            wb_check["card_mix"]["weekday_in_sentence"], ", ".join(
                "{} is a {}".format(t, d) for t, d in wb_check["card_mix"]["weekday_mismatch"])),
            flush=True)
    write_readme(alloc, instances)
    assert FC1.sha256(BRIEFING_PATH) == briefing_sha, "the briefing changed"
    for c in cards:
        lv = c["levers"]
        print("{:7s} {:28s} {:15s} level {:6.1f} bh share {:>6s} levers {}".format(
            c["title"], c["instance_id"], c["stratum"], instances[c["instance_id"]]["threshold_bh"],
            pct(c["share_020"]), lv["any kind"]["orders"]), flush=True)
    print("[r2] allocation {} ({})".format(dict(alloc["alloc"]), alloc["reason"]))
    print("[r2] manifest sha256 {}".format(FC1.sha256(MANIFEST_PATH)))
    print("[r2] wrote {}, {}, {}, {}, {}, {}, {}; {:.0f} s".format(
        CACHE_CSV, SELFTEST_CSV, REPORT_MD, PDF_PATH, XLSX_PATH, MANIFEST_PATH, README_PATH,
        time.time() - t_run), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
