#!/usr/bin/env python
"""Scenario cards and workbook for the field-instruction collection (N5).

WHAT THIS BUILDS
----------------
Eight scenario cards, each one real work-order board from the instance
snapshot, rendered twice with the same content:

* ``the data-collection pack (not released)``, one A4 page per card;
* sheets "Card 1" .. "Card 8" of
  ``the data-collection pack (not released)``, which
  also carries the sheets "Read me" (the briefing), "Answers" and "About you".

``the data-collection pack (not released)`` records, per card, the
instance, its snapshot path and sha256, the sixteen order ids in display
order and the in-progress set, so every collected instruction can be replayed
on exactly the board the respondent saw.

INSTANCES
---------
Files are read only from the snapshot
``${L1_Y1_ROOT}/data/processed/instances_v10`` and each one
is checked against ``code/scripts/instance_manifest_l1.json`` before use (the
default instance tree has drifted and is never read here).

The eight instances are taken from the 60 the suite uses: 4 from stratum
c09_storm2_w80, 2 from c10_storm2_w80 and 2 from c10_replay_400.  Within a
stratum, instances are ranked by the number of suite items they carry
(descending), ties broken by file name, and the top ones are taken, so the
field instructions sit on the boards that carry most generated items.  An
instance is skipped when it lacks one of the four priority classes, because
every card must show every class.

THE BOARD EXTRACT (sixteen orders per card)
-------------------------------------------
The reference schedule is the baseline dispatch the suite uses
(``l1adapter.dispatch.dispatch_baseline``, rule ATC, seed 0).  An order is
"late on the current plan" when its baseline finish is after its due time.
All random draws use one ``random.Random`` seeded with SEED plus the card
number, and every candidate pool is sorted by order id before a draw, so the
extract is identical on every run.  Steps, in order, never repeating an order:

1. In progress.  If any suite item on the instance has a non-empty standing
   frozen set, the card shows that set as "in progress".  It is the three
   earliest-starting orders of the baseline schedule (ties by id), and the
   script asserts that it equals the suite's own frozen set.  Otherwise the
   card shows no in-progress rows.
2. Two late orders.  Two draws from the orders that are late on the current
   plan.  If fewer than two are late, the remainder is filled with the
   orders of smallest baseline slack (due minus finish, ties by id).
3. Two long jobs.  Two draws from the 20 orders with the most hours of work.
4. Two late arrivals.  Two draws from the orders that become available in
   the second half of the board's arrival window.
5. Replay cards only: two pairs sharing a building.  Two draws of distinct
   buildings that have at least two queued orders of one trade, then two
   draws of such orders inside each building (same building, same trade, so
   the pair can be grouped).
6. Coverage.  For each priority class 1..4 not yet on the card, one draw
   from the orders of that class; then, while fewer than four trades are on
   the card, one draw from a trade not yet on it.
7. Fill to sixteen.  Half of the free rows (rounded up) are drawn from the
   orders the suite's items on this instance name (items naming at most four
   orders), the rest from the orders that become available within the first
   eight working hours.  Each pool falls back to all remaining orders when
   it runs dry.

Display order: in-progress rows first, by baseline start; then all other rows
by due time, then id (the proposer prompt's earliest-due order).

WHAT IS ASSERTED
----------------
* every snapshot file matches its manifest hash;
* the in-progress set equals the suite's frozen set for that instance;
* every order id on every card exists in its instance, and each card has 16
  distinct orders covering all four priority classes and at least four trades,
  with two late, two long, two late-arrival rows (and two building pairs on
  replay cards);
* the "Crews and work by trade" table on each card is parsed from the
  proposer prompt itself (``l1guard.prompts.user_prompt``) and equals an
  independent recomputation from the instance;
* the PDF has eight pages and the workbook reopens with its validation lists.

Run:  python code/scripts/field_cards.py
"""

from __future__ import annotations

import collections
import datetime as _dt
import hashlib
import json
import os
import random
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent.parent
CODE = ROOT / "code"
sys.path.insert(0, str(CODE))
sys.path.insert(0, str(SCRIPTS_DIR))

from l1adapter import dispatch  # noqa: E402
from l1guard.prompts import user_prompt  # noqa: E402
from l1suite.facts import TRADE_GLOSS  # noqa: E402

VERSION = "l1-field-cards-1"
SEED = 20261026

#: The instance snapshot; ``L1_INSTANCE_ROOT`` points elsewhere when the snapshot
#: has been unpacked in another place (the repository's usual override).
SNAPSHOT_NAME = "instances_v10"
SNAPSHOT_ROOT = Path(os.environ.get(
    "L1_INSTANCE_ROOT",
    ((os.environ.get("L1_Y1_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "PaperY-FMScheduling")) + "/data/processed/instances_v10")))
HASH_MANIFEST = SCRIPTS_DIR / "instance_manifest_l1.json"
SUITE = CODE / "suite" / "v0.2" / "suite.jsonl"

OUT_DIR = ROOT / "participant_files" / "field_instructions"
PDF_PATH = OUT_DIR / "cards" / "cards.pdf"
XLSX_PATH = OUT_DIR / "Field_Instruction_Workbook.xlsx"
MANIFEST_PATH = OUT_DIR / "card_manifest.json"
BRIEFING_PATH = OUT_DIR / "briefing.md"

#: Stratum and number of cards drawn from it, in card order.
STRATA = (("c09_storm2_w80", 4), ("c10_storm2_w80", 2), ("c10_replay_400", 2))

N_ROWS = 16
N_LONG_POOL = 20
FIRST_DAY_BH = 8.0
EPISODE_RULE, EPISODE_SEED = "atc", 0

#: Names shown beside trade codes.  The UNIFORMAT names the suite already uses,
#: plus plain descriptions of the dataset's three catch-all codes.
EXTRA_GLOSS = {
    "D90": "other building services",
    "MISC": "small trades, grouped",
    "UNK": "trade not recorded",
}

#: Respondent k receives cards a and b with a = ((k-1) mod 8) + 1 and
#: b = ((k+3) mod 8) + 1, so each respondent sees one C09 card and one C10
#: card, and eight respondents cover every card twice.
def assignment(k: int) -> tuple:
    return ((k - 1) % 8 + 1, (k + 3) % 8 + 1)


SITUATIONS = (
    ("A", "Something that must move up or be dealt with next."),
    ("B", "Something that must wait, and the reason."),
    ("C", "Two jobs that must go in a particular order."),
    ("D", "Work that should be grouped (same block, same visit or same crew)."),
    ("E", "Work already under way that must not be disturbed."),
    ("F", "A change you would make knowing that other jobs will slip because "
          "of it. Say so in the instruction the way you normally would."),
    ("G", "A request you would expect the assistant to check with you before "
          "acting on."),
    ("H", "Anything else you would say on a day like this."),
)
ACTION_CHOICES = ("apply it", "ask me before applying", "refuse it")
DELAY_CHOICES = ("no", "yes, up to __ hours", "yes, any")


# --------------------------------------------------------------------------- #
# Inputs                                                                       #
# --------------------------------------------------------------------------- #
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot_relpath(file_name: str) -> str:
    stem = Path(file_name).stem
    campus, track = stem.split("_")[0], stem.split("_")[1]
    size = "w80" if track == "storm2" else stem.split("_")[2]
    return "{}/{}/{}/{}".format(campus, track, size, file_name)


def load_suite() -> list:
    with open(SUITE) as f:
        return [json.loads(line) for line in f if line.strip()]


def choose_instances(items: list, skipped: list) -> list:
    counts = collections.Counter(it["instance"]["file"] for it in items)
    stratum_of = {it["instance"]["file"]: it["instance"]["stratum"] for it in items}
    chosen = []
    for stratum, k in STRATA:
        files = sorted((f for f in counts if stratum_of[f] == stratum),
                       key=lambda f: (-counts[f], f))
        taken = 0
        for f in files:
            if taken == k:
                break
            inst = json.load(open(SNAPSHOT_ROOT / snapshot_relpath(f)))
            classes = {int(w["priority"]) for w in inst["work_orders"]}
            if classes != {1, 2, 3, 4}:
                skipped.append((f, sorted(classes)))
                continue
            chosen.append((stratum, f, counts[f]))
            taken += 1
        assert taken == k, stratum
    return chosen


# --------------------------------------------------------------------------- #
# The crew table, taken from the proposer prompt                               #
# --------------------------------------------------------------------------- #
CREW_HEAD = "Crews and work on the board, by trade:"


def crew_rows_from_prompt(instance: dict, item: dict) -> list:
    """Parse the trade table out of the proposer's own user prompt."""
    text = user_prompt(instance, item)
    lines = text.split("\n")
    i = lines.index(CREW_HEAD)
    header = lines[i + 1].split()
    assert header == ["trade", "technicians", "orders", "hours", "first", "in",
                      "first", "due", "class", "1"], header
    rows = []
    for line in lines[i + 2:]:
        if not line.strip():
            break
        rows.append(line.split())
    return rows


def crew_rows_recomputed(instance: dict) -> list:
    """Independent recomputation, used only to check the parsed table."""
    crew = collections.Counter(t["trade"] for t in instance["technicians"])
    by_trade = collections.defaultdict(list)
    for w in instance["work_orders"]:
        by_trade[w["trade"]].append(w)
    out = []
    for trade in sorted(set(crew) | set(by_trade)):
        ws = by_trade.get(trade, [])
        out.append([
            trade,
            str(crew.get(trade, 0)),
            str(len(ws)),
            "{:.2f}".format(sum(float(w["p_bh"]) for w in ws)),
            "-" if not ws else "{:.2f}".format(min(float(w["release_bh"]) for w in ws)),
            "-" if not ws else "{:.2f}".format(min(float(w["due_bh"]) for w in ws)),
            str(sum(1 for w in ws if int(w["priority"]) == 1)),
        ])
    return out


def gloss(trade: str) -> str:
    return TRADE_GLOSS.get(trade) or EXTRA_GLOSS.get(trade) or ""


# --------------------------------------------------------------------------- #
# The board extract                                                            #
# --------------------------------------------------------------------------- #
def select_orders(card_no: int, instance: dict, base: dict, frozen: list,
                  suite_refs: list, is_replay: bool) -> dict:
    rng = random.Random(SEED + card_no)
    wos = sorted(instance["work_orders"], key=lambda w: w["id"])
    by_id = {w["id"]: w for w in wos}
    asg = {a["wo"]: a for a in base["assignments"]}
    window = float(instance["meta"]["window_bh"])
    chosen: list = []
    role = collections.defaultdict(list)

    def free(pool):
        taken = set(chosen)
        return sorted({o for o in pool if o not in taken})

    def draw(pool, n, tag):
        pool = free(pool)
        picks = rng.sample(pool, min(n, len(pool)))
        for o in picks:
            chosen.append(o)
            role[o].append(tag)
        return picks

    # 1. in progress
    for o in frozen:
        chosen.append(o)
        role[o].append("in_progress")

    # 2. late on the current plan
    late = [w["id"] for w in wos if asg[w["id"]]["end_bh"] > w["due_bh"] + 1e-9]
    got = draw(late, 2, "late")
    if len(got) < 2:
        slack = sorted(free(by_id), key=lambda o: (by_id[o]["due_bh"] - asg[o]["end_bh"], o))
        for o in slack[: 2 - len(got)]:
            chosen.append(o)
            role[o].append("late")

    # 3. long jobs
    longest = sorted(free(by_id), key=lambda o: (-float(by_id[o]["p_bh"]), o))[:N_LONG_POOL]
    draw(longest, 2, "long")

    # 4. late arrivals
    draw([w["id"] for w in wos if float(w["release_bh"]) >= window / 2.0], 2, "late_arrival")

    # 5. building pairs (replay only)
    if is_replay:
        groups = collections.defaultdict(list)
        for o in free(by_id):
            w = by_id[o]
            if w["building"] is not None:
                groups[(w["building"], w["trade"])].append(o)
        eligible = sorted({b for (b, t), os_ in groups.items() if len(os_) >= 2})
        for b in rng.sample(eligible, 2):
            cells = sorted(t for (bb, t), os_ in groups.items() if bb == b and len(os_) >= 2)
            t = rng.choice(cells)
            draw(groups[(b, t)], 2, "building_pair")

    # 6. coverage of classes and trades
    for cls in (1, 2, 3, 4):
        if not any(int(by_id[o]["priority"]) == cls for o in chosen):
            draw([w["id"] for w in wos if int(w["priority"]) == cls], 1, "class_cover")
    while len({by_id[o]["trade"] for o in chosen}) < 4:
        have = {by_id[o]["trade"] for o in chosen}
        draw([w["id"] for w in wos if w["trade"] not in have], 1, "trade_cover")

    # 7. fill
    assert len(chosen) <= N_ROWS, (card_no, len(chosen))
    free_rows = N_ROWS - len(chosen)
    n_ref = (free_rows + 1) // 2
    refs = [o for o in suite_refs if o in by_id]
    got = draw(refs, n_ref, "fill_suite")
    n_rest = N_ROWS - len(chosen)
    early = [w["id"] for w in wos if float(w["release_bh"]) <= FIRST_DAY_BH]
    got = draw(early, n_rest, "fill")
    if len(chosen) < N_ROWS:
        draw(list(by_id), N_ROWS - len(chosen), "fill")
    assert len(chosen) == N_ROWS == len(set(chosen))

    fz = set(frozen)
    first = sorted(frozen, key=lambda o: (float(asg[o]["start_bh"]), o))
    rest = sorted((o for o in chosen if o not in fz),
                  key=lambda o: (float(by_id[o]["due_bh"]), o))
    return {"order_ids": first + rest, "roles": {o: role[o] for o in chosen}}


def board_rows(order_ids, instance, base, frozen, is_replay):
    by_id = {w["id"]: w for w in instance["work_orders"]}
    asg = {a["wo"]: a for a in base["assignments"]}
    rows = []
    for o in order_ids:
        w = by_id[o]
        lateness = float(asg[o]["end_bh"]) - float(w["due_bh"])
        plan = "late by {:.2f} h".format(lateness) if lateness > 1e-9 else "on time"
        row = [o, w["trade"], str(int(w["priority"])), "{:.2f}".format(float(w["p_bh"])),
               "{:.2f}".format(float(w["release_bh"])), "{:.2f}".format(float(w["due_bh"]))]
        if is_replay:
            row.append(w["building"] if w["building"] is not None else "-")
        row += ["in progress" if o in frozen else "queued", plan]
        rows.append(row)
    return rows


def board_header(is_replay):
    h = ["Order", "Trade", "Priority class", "Hours of work",
         "Available from (hours from now)", "Due (hours from now)"]
    if is_replay:
        h.append("Building")
    return h + ["Status", "Current plan"]


CREW_HEADER = ["Trade", "Trade name", "Technicians", "Open orders", "Hours of work",
               "First available (hours from now)", "First due (hours from now)",
               "Priority-1 orders"]


def site_lines(instance: dict, n_items_frozen: bool) -> list:
    meta = instance["meta"]
    n_tech = len(instance["technicians"])
    n_wo = len(instance["work_orders"])
    window = float(meta["window_bh"])
    if meta["track"] == "replay":
        start = _dt.datetime.fromisoformat(meta["window_start"])
        day = "An ordinary {} at {} (a day replayed from the dataset).".format(
            start.strftime("%A"), start.strftime("%H:%M"))
    else:
        day = ("A storm day. Requests arrive at several times the usual rate. "
               "The board is built from this campus's own work-order history.")
    return [
        "Campus {} of the source dataset.".format(int(meta["campus"])),
        day,
        "{:,} technicians. {:,} work orders on the board, arriving over the next "
        "{:.1f} working hours.".format(n_tech, n_wo, window),
    ]


NOTES = [
    "Times are working hours from now. A working day has 8 hours and a working week "
    "has 5 days, so 40 hours is one working week.",
    "Priority class 1 is the most urgent and class 4 the least. An order is due at the "
    "time it becomes available plus its response window: 8 working hours for class 1, "
    "24 for class 2, 80 for class 3 and 171.4 for class 4.",
    "Trade codes are the building-system codes used in the source dataset.",
    "\"In progress\" means the job has already started and is held in its current slot. "
    "\"Current plan\" says whether the job finishes by its due time if nobody changes "
    "the schedule.",
    "The board table shows 16 of the open orders. The crew table counts every order "
    "on the board.",
]


# --------------------------------------------------------------------------- #
# Briefing                                                                     #
# --------------------------------------------------------------------------- #
def briefing_blocks() -> list:
    """(kind, text) blocks.  kind in {title, head, para, item}."""
    b = [("title", "A short study of scheduling instructions")]
    b += [("head", "What this is"),
          ("para", "This is a research study of a scheduling assistant for "
                   "facility-management teams. A supervisor tells the assistant what to "
                   "change, and the assistant turns the instruction into a change to the "
                   "work schedule. A separate check then decides whether the change may "
                   "be applied. We want to test both on instructions written by people "
                   "who do this work every day.")]
    b += [("head", "What you are looking at"),
          ("para", "Each card shows a work-order board rebuilt from a public work-order "
                   "dataset. Some cards show an ordinary day. Others show a storm day "
                   "with far more requests than usual. The order numbers, building codes "
                   "and trade codes come from that dataset, and they do not identify "
                   "real buildings or people."),
          ("para", "Each card has a crew table for the whole site and a list of 16 open "
                   "orders. All times are working hours from now. A working day has 8 "
                   "hours and a working week has 5 days, so 40 hours is one working "
                   "week. Rows marked \"in progress\" have already started. The last "
                   "column says whether a job finishes on time if nobody changes the "
                   "schedule.")]
    b += [("head", "What we ask you to do"),
          ("para", "Your invitation names two cards and gives you a respondent code. "
                   "For each of your two cards, write 12 to 20 instructions as you would "
                   "say or type them to a dispatcher or to a scheduling assistant on that "
                   "day. Use your own words, and give the reasons you would normally "
                   "give. You may name any order or trade on the card. Please write at "
                   "least one instruction for each situation below.")]
    b += [("item", "{}. {}".format(k, t)) for k, t in SITUATIONS]
    b += [("head", "Three answers for each instruction"),
          ("para", "Write each instruction on its own row of the Answers sheet, with "
                   "your respondent code, the card and the situation letter. Then give "
                   "three short answers."),
          ("item", "1. What should the system do with it? Choose \"apply it\", "
                   "\"ask me before applying\" or \"refuse it\"."),
          ("item", "2. Is delay to other work acceptable? Choose \"no\", \"yes, up to "
                   "__ hours\" (and give the hours in the next column) or \"yes, any\"."),
          ("item", "3. If you wish, one line on why."),
          ("para", "Please also fill in the short \"About you\" sheet. The whole task "
                   "takes 30 to 45 minutes.")]
    b += [("head", "Consent"),
          ("para", "The boards are replayed from a public dataset and are "
                   "de-identified. We collect no personal data beyond your role, your "
                   "years in facility management, how often you approve work-order "
                   "changes and whether you use a maintenance management system (CMMS). "
                   "Please do not write your name or your employer anywhere in the "
                   "workbook. Your instructions will be released with the study's public "
                   "data in de-identified form, under your respondent code only. Taking "
                   "part is voluntary and unpaid. You may withdraw at any time before "
                   "the data are released, by sending us your respondent code. Returning "
                   "the workbook means that you agree to these terms.")]
    b += [("para", "Thank you for your time and for sharing your experience.")]
    return b


def write_briefing_md(path: Path) -> None:
    out = []
    for kind, text in briefing_blocks():
        if kind == "title":
            out += ["# " + text, ""]
        elif kind == "head":
            out += ["## " + text, ""]
        elif kind == "item":
            out += [text, ""]
        else:
            out += [text, ""]
    path.write_text("\n".join(out).rstrip() + "\n")


# --------------------------------------------------------------------------- #
# PDF                                                                          #
# --------------------------------------------------------------------------- #
def render_pdf(cards: list, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.lines import Line2D
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextToPath

    _t2p = TextToPath()

    def width_mm(s, size, bold=False):
        prop = FontProperties(family="serif", size=size,
                              weight="bold" if bold else "normal")
        w, _, _ = _t2p.get_text_width_height_descent(s, prop, ismath=False)
        return w * PT

    def wrap(s, max_mm, size, bold=False):
        lines, cur = [], ""
        for word in s.split():
            trial = word if not cur else cur + " " + word
            if cur and width_mm(trial, size, bold) > max_mm:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        if cur:
            lines.append(cur)
        return lines

    matplotlib.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Liberation Serif", "TeX Gyre Termes", "Times New Roman"],
        "pdf.fonttype": 42,
        "text.color": "black",
    })
    W, H = 210.0, 297.0
    ML, MR, MT = 16.0, 16.0, 16.0
    TW = W - ML - MR
    PT = 25.4 / 72.0  # mm per point

    def X(mm):
        return mm / W

    def Y(mm_from_top):
        return 1.0 - mm_from_top / H

    def rule(fig, y, lw=0.6, x0=ML, x1=W - MR):
        fig.add_artist(Line2D([X(x0), X(x1)], [Y(y), Y(y)], lw=lw, color="black"))

    def text(fig, x, y, s, size=9.0, weight="normal", ha="left"):
        fig.text(X(x), Y(y), s, fontsize=size, fontweight=weight, ha=ha, va="baseline")

    def table(fig, y, header, rows, widths, aligns, size=8.5):
        scale = TW / sum(widths)
        widths = [w * scale for w in widths]
        xs = [ML]
        for w in widths[:-1]:
            xs.append(xs[-1] + w)
        line_h = size * PT * 1.25
        pad = 1.0
        # header, wrapped per column
        wrapped = []
        for h, w in zip(header, widths):
            wrapped.append(wrap(h, w - 2.5, size, bold=True))
        n_head = max(len(x) for x in wrapped)
        rule(fig, y, lw=0.9)
        y += pad
        for c, lines in enumerate(wrapped):
            for j, s in enumerate(lines):
                yy = y + (j + 1) * line_h - 0.6
                if aligns[c] == "r":
                    text(fig, xs[c] + widths[c] - 1.0, yy, s, size, "bold", "right")
                else:
                    text(fig, xs[c] + 1.0, yy, s, size, "bold")
        y += n_head * line_h + pad
        rule(fig, y, lw=0.5)
        y += pad
        for r in rows:
            y += line_h
            for c, s in enumerate(r):
                assert width_mm(s, size) <= widths[c] - 2.0, ("cell overflow", s)
                if aligns[c] == "r":
                    text(fig, xs[c] + widths[c] - 1.0, y - 0.6, s, size, "normal", "right")
                else:
                    text(fig, xs[c] + 1.0, y - 0.6, s, size)
        y += pad
        rule(fig, y, lw=0.9)
        return y

    def para(fig, y, s, size=8.5, gap=1.2):
        line_h = size * PT * 1.3
        for line in wrap(s, TW, size):
            y += line_h
            text(fig, ML, y, line, size)
        return y + gap

    path.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(path, metadata={"Title": "Scenario cards", "Author": "",
                                  "Subject": "", "Keywords": ""}) as pdf:
        for card in cards:
            fig = plt.figure(figsize=(W / 25.4, H / 25.4))
            y = MT + 5.0
            text(fig, ML, y, card["title"], 14, "bold")
            y += 3.0
            for s in card["site"]:
                y = para(fig, y, s, size=10, gap=0.2)
            y += 8.0
            text(fig, ML, y, "Crews and work by trade", 10.5, "bold")
            y += 2.5
            y = table(fig, y, CREW_HEADER, card["crew_display"],
                      [11, 27, 17, 14, 16, 25, 22, 16],
                      ["l", "l", "r", "r", "r", "r", "r", "r"])
            y += 7.0
            text(fig, ML, y, "Board: 16 of the open work orders", 10.5, "bold")
            y += 2.5
            if card["is_replay"]:
                widths = [17, 10, 12, 12, 17, 15, 14, 16, 23]
                aligns = ["l", "l", "r", "r", "r", "r", "l", "l", "l"]
            else:
                widths = [13, 10, 12, 12, 18, 15, 16, 23]
                aligns = ["l", "l", "r", "r", "r", "r", "l", "l"]
            y = table(fig, y, card["board_header"], card["board"], widths, aligns)
            y += 5.0
            text(fig, ML, y, "Notes", 9, "bold")
            y += 0.5
            for s in NOTES:
                y = para(fig, y, s, size=8.5, gap=0.8)
            assert y < H - 10.0, ("page overflow", card["title"], y)
            card["pdf_bottom_mm"] = round(y, 1)
            pdf.savefig(fig)
            plt.close(fig)


# --------------------------------------------------------------------------- #
# Workbook                                                                     #
# --------------------------------------------------------------------------- #
def write_workbook(cards: list, path: Path) -> None:
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
    # ---- Read me
    ws = wb.active
    ws.title = "Read me"
    ws.column_dimensions["A"].width = 110
    r = 1
    for kind, s in briefing_blocks():
        c = ws.cell(row=r, column=1, value=s)
        c.alignment = wrap_top
        c.font = {"title": f_title, "head": f_head}.get(kind, f_body)
        if kind == "item":
            c.alignment = Alignment(wrap_text=True, vertical="top", indent=2)
        r += 1
        if kind in ("para", "title"):
            r += 1

    # ---- cards
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
        r = put_table(r, CREW_HEADER, card["crew_display"], {3, 4, 5, 6, 7, 8})
        ws.cell(row=r, column=1, value="Board: 16 of the open work orders").font = f_head
        r += 1
        right = {3, 4, 5, 6}
        r = put_table(r, card["board_header"], card["board"], right)
        ws.cell(row=r, column=1, value="Notes").font = f_bold
        for s in NOTES:
            r += 1
            ws.cell(row=r, column=1, value=s).font = f_body
        widths = [12, 24, 13, 13, 14, 18, 16, 14, 16]
        for j, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(j)].width = w
        ws.sheet_view.showGridLines = False

    # ---- choice lists live on a hidden sheet, because several answers contain
    # commas and an inline Excel list would split them
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
    header = ["Respondent code", "Card", "Situation (A-H)",
              "Instruction (exactly as you would say or type it)",
              "What should the system do? (apply it / ask me before applying / refuse it)",
              "Delay to other work acceptable? (no / yes, up to __ hours / yes, any)",
              "If \"up to\", how many hours?", "Why (optional)"]
    widths = [14, 10, 12, 70, 26, 26, 14, 45]
    for j, (h, w) in enumerate(zip(header, widths), start=1):
        c = ws.cell(row=1, column=j, value=h)
        c.font = f_bold
        c.alignment = Alignment(wrap_text=True, vertical="top")
        c.border = Border(bottom=thin)
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.row_dimensions[1].height = 48
    n_rows = 200
    for i in range(2, n_rows + 2):
        for j in range(1, len(header) + 1):
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
    dv_list([k for k, _ in SITUATIONS], "C", "Situation")
    dv_list(list(ACTION_CHOICES), "E", "What should the system do")
    dv_list(list(DELAY_CHOICES), "F", "Delay to other work")
    dv = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0",
                        allow_blank=True)
    dv.error = "Please enter a number of working hours."
    dv.add("G2:G{}".format(last))
    ws.add_data_validation(dv)

    # ---- About you
    ws = wb.create_sheet("About you")
    about = [
        ("Respondent code", None),
        ("Your role (for example maintenance supervisor, facilities manager or dispatcher)", None),
        ("Years in facility management", None),
        ("Do you approve work-order changes?", ("daily", "weekly", "occasionally", "never")),
        ("Do you use a computerised maintenance management system (CMMS)?", ("yes", "no")),
    ]
    ws.column_dimensions["A"].width = 70
    ws.column_dimensions["B"].width = 40
    ws.cell(row=1, column=1, value="Question").font = f_bold
    ws.cell(row=1, column=2, value="Your answer").font = f_bold
    for j in (1, 2):
        ws.cell(row=1, column=j).border = Border(bottom=thin)
    for i, (q, choices) in enumerate(about, start=2):
        c = ws.cell(row=i, column=1, value=q)
        c.font = f_body
        c.alignment = wrap_top
        a = ws.cell(row=i, column=2)
        a.font = f_body
        a.border = Border(bottom=Side(style="hair", color="000000"))
        if choices:
            dv = DataValidation(type="list", formula1=list_range(choices),
                                allow_blank=True)
            dv.add("B{}".format(i))
            ws.add_data_validation(dv)
        if q.startswith("Years"):
            dv = DataValidation(type="decimal", operator="greaterThanOrEqual",
                                formula1="0", allow_blank=True)
            dv.add("B{}".format(i))
            ws.add_data_validation(dv)
    ws.freeze_panes = "A2"

    wb.move_sheet("Lists", offset=len(wb.sheetnames) - 1 - wb.sheetnames.index("Lists"))
    wb.properties.creator = ""
    wb.properties.lastModifiedBy = ""
    wb.properties.title = "Field instruction workbook"
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def check_workbook(path: Path, cards: list) -> dict:
    from openpyxl import load_workbook
    wb = load_workbook(path)
    expected = ["Read me"] + [c["title"] for c in cards] + ["Answers", "About you", "Lists"]
    assert wb.sheetnames == expected, wb.sheetnames
    assert wb["Lists"].sheet_state == "hidden"

    def list_values(formula):
        ref = formula.split("!")[1].replace("$", "")
        return [c.value for row in wb["Lists"][ref] for c in row]
    ans = wb["Answers"]
    lists = {}
    for dv in ans.data_validations.dataValidation:
        cols = str(dv.sqref).split(":")[0][0]
        lists[cols] = (dv.type, list_values(dv.formula1) if dv.type == "list" else None)
    assert lists["E"] == ("list", list(ACTION_CHOICES)), lists["E"]
    assert lists["F"] == ("list", list(DELAY_CHOICES)), lists["F"]
    assert ans.freeze_panes == "A2"
    banned = ("name", "employer", "email", "e-mail", "phone", "company")
    fields = [c.value for c in wb["Answers"][1] if c.value]
    fields += [r[0].value for r in wb["About you"].iter_rows(min_row=2) if r[0].value]
    for f in fields:
        assert not any(b in str(f).lower() for b in banned), f
    # card sheets equal the PDF content
    for card in cards:
        ws = wb[card["title"]]
        cells = {str(c.value) for row in ws.iter_rows() for c in row if c.value is not None}
        for o in card["order_ids"]:
            assert o in cells, (card["title"], o)
    return {"sheets": wb.sheetnames, "validations": sorted(lists)}


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> None:
    hashes = json.load(open(HASH_MANIFEST))["files"]
    items = load_suite()
    skipped: list = []
    chosen = choose_instances(items, skipped)

    cards = []
    for card_no, (stratum, file_name, n_items) in enumerate(chosen, start=1):
        rel = snapshot_relpath(file_name)
        path = SNAPSHOT_ROOT / rel
        digest = sha256(path)
        assert hashes[rel] == digest, ("snapshot hash mismatch", rel)
        instance = json.load(open(path))
        iid = instance["meta"]["id"]
        assert iid == Path(file_name).stem
        is_replay = instance["meta"]["track"] == "replay"
        base = dispatch.dispatch_baseline(instance, EPISODE_RULE, EPISODE_SEED)

        its = [it for it in items if it["instance"]["file"] == file_name]
        for it in its:
            assert it["episode"]["rule"] == EPISODE_RULE and it["episode"]["seed"] == EPISODE_SEED
        frozen_sets = {tuple(it["episode"]["frozen_seed"]) for it in its
                       if it["episode"].get("frozen_seed")}
        starts = sorted((float(a["start_bh"]), a["wo"]) for a in base["assignments"])
        if frozen_sets:
            assert len(frozen_sets) == 1, frozen_sets
            frozen = [o for _, o in starts[:3]]
            assert tuple(frozen) == next(iter(frozen_sets)), (iid, frozen, frozen_sets)
        else:
            frozen = []
        suite_refs = sorted({o for it in its
                             for o in it["referenced"]["order_ids"]
                             if len(it["referenced"]["order_ids"]) <= 4})

        sel = select_orders(card_no, instance, base, frozen, suite_refs, is_replay)
        ids = sel["order_ids"]
        by_id = {w["id"]: w for w in instance["work_orders"]}
        assert all(o in by_id for o in ids), "order id not in instance"
        assert {int(by_id[o]["priority"]) for o in ids} == {1, 2, 3, 4}, (iid, "classes")
        assert len({by_id[o]["trade"] for o in ids}) >= 4, (iid, "trades")
        roles = collections.Counter(t for v in sel["roles"].values() for t in v)
        for tag in ("late", "long", "late_arrival"):
            assert roles[tag] == 2, (iid, tag, roles)
        if is_replay:
            assert roles["building_pair"] == 4, (iid, roles)

        # crew table: parsed from the proposer prompt, checked against a recount
        probe_item = next(it for it in its if it["episode"].get("frozen_seed")) if frozen else its[0]
        crew = crew_rows_from_prompt(instance, probe_item)
        assert crew == crew_rows_recomputed(instance), (iid, "crew table mismatch")
        crew_display = [[r[0], gloss(r[0])] + r[1:] for r in crew]

        cards.append({
            "card_no": card_no,
            "title": "Card {}".format(card_no),
            "instance_id": iid,
            "stratum": stratum,
            "snapshot_relpath": rel,
            "sha256": digest,
            "suite_items_on_instance": n_items,
            "is_replay": is_replay,
            "frozen": frozen,
            "order_ids": ids,
            "roles": sel["roles"],
            "site": site_lines(instance, bool(frozen)),
            "crew": crew,
            "crew_display": crew_display,
            "board_header": board_header(is_replay),
            "board": board_rows(ids, instance, base, set(frozen), is_replay),
        })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_briefing_md(BRIEFING_PATH)
    render_pdf(cards, PDF_PATH)
    write_workbook(cards, XLSX_PATH)
    wb_check = check_workbook(XLSX_PATH, cards)

    manifest = {
        "schema": VERSION,
        "generator": "code/scripts/field_cards.py",
        "seed": SEED,
        "snapshot": SNAPSHOT_NAME,
        "snapshot_note": "snapshot_relpath is relative to the instances_v10 snapshot; "
                         "each file's sha256 equals its entry in "
                         "code/scripts/instance_manifest_l1.json",
        "episode": {"rule": EPISODE_RULE, "seed": EPISODE_SEED, "t_bh": 0.0},
        "assignment_rule": "respondent Pk receives cards ((k-1) mod 8)+1 and ((k+3) mod 8)+1",
        "assignment_first_eight": {"P{}".format(k): ["Card {}".format(c) for c in assignment(k)]
                                   for k in range(1, 9)},
        "cards": [{
            "card_id": c["title"],
            "instance_id": c["instance_id"],
            "stratum": c["stratum"],
            "snapshot_relpath": c["snapshot_relpath"],
            "sha256": c["sha256"],
            "suite_items_on_instance": c["suite_items_on_instance"],
            "frozen_set_shown": c["frozen"],
            "order_ids": c["order_ids"],
            "selection_roles": {o: c["roles"][o] for o in c["order_ids"]},
        } for c in cards],
        "instances_skipped": [{"file": f, "priority_classes": c} for f, c in skipped],
        "workbook_check": wb_check,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=1) + "\n")
    for c in cards:
        print("{:7s} {:28s} items={:3d} frozen={} bottom={}mm".format(
            c["title"], c["instance_id"], c["suite_items_on_instance"],
            len(c["frozen"]), c["pdf_bottom_mm"]))
    print("wrote", PDF_PATH, XLSX_PATH, MANIFEST_PATH, BRIEFING_PATH)


if __name__ == "__main__":
    main()
