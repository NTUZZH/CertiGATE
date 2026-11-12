"""Surface-form helpers: how an FM supervisor names things in a message.

Three registers are used throughout the template families, and every family
carries variants in all three:

``formal``
    the work-order register of a CMMS note or a planner's email;
``terse``
    the shift-handover line a supervisor types on a phone;
``conversational``
    what the same person says on the radio, with the reason attached.

Two rules hold for every string produced here.  First, an instruction never
names its own label: no class name, no word such as "invalid" or "ambiguous",
nothing that tells a reader which set the item belongs to (``checks.py``
enforces this on every generated item).  Second, a benign instruction states
everything the reader needs to translate it: the work-order number, the trade
when the operation needs one, and the shift in business hours.
"""

from __future__ import annotations

from .facts import TRADE_GLOSS

# --------------------------------------------------------------------------- #
# Work orders and trades                                                       #
# --------------------------------------------------------------------------- #
def order_ref(oid: str, style: str = "formal") -> str:
    if style == "formal":
        return "work order {}".format(oid)
    if style == "terse":
        return "WO {}".format(oid)
    return oid


def trade_ref(trade: str, style: str = "formal") -> str:
    """``the D50 (electrical) crew`` / ``the electrical crew`` / ``D50``.

    ``MISC``, ``UNK`` and ``D90`` have no craft name (they are the corpus's
    merge and unknown buckets), so they are named by their code alone.
    """
    gloss = TRADE_GLOSS.get(trade)
    if style == "terse":
        return trade
    if gloss is None:
        return "the {} crew".format(trade)
    if style == "conversational":
        return "the {} crew".format(gloss)
    return "the {} ({}) crew".format(trade, gloss)


def trade_work(trade: str) -> str:
    """``the electrical work`` / ``the D90 work`` for scope phrases."""
    return "the {}".format(trade_work_bare(trade))


def trade_work_bare(trade: str) -> str:
    """``electrical work``: no article, for "the outstanding X" contexts."""
    gloss = TRADE_GLOSS.get(trade)
    return "{} work".format(gloss) if gloss else "{} work".format(trade)


def job_noun(order: dict, style: str = "formal") -> str:
    """A short noun for one order: ``the HVAC job``, ``the D90 job``."""
    gloss = TRADE_GLOSS.get(order["trade"])
    base = "{} job".format(gloss) if gloss else "{} job".format(order["trade"])
    if style == "formal" and order.get("is_pm"):
        return "the planned {}".format(base)
    return "the {}".format(base)


# --------------------------------------------------------------------------- #
# Time                                                                         #
# --------------------------------------------------------------------------- #
#: Business-hour magnitudes with the phrasings a supervisor actually uses.
#: 8 bh is one working day and 40 bh is one working week on this time axis.
_MAGNITUDE = {
    4.0: ("half a working day", "4 business hours"),
    8.0: ("one working day", "8 business hours"),
    16.0: ("two working days", "16 business hours"),
    24.0: ("three working days", "24 business hours"),
    40.0: ("one working week", "40 business hours"),
    80.0: ("two working weeks", "80 business hours"),
    120.0: ("three working weeks", "120 business hours"),
    480.0: ("three months", "480 business hours"),
    600.0: ("four months", "600 business hours"),
}

NATURAL_SHIFTS = (4.0, 8.0, 16.0, 24.0, 40.0, 80.0, 120.0)
OUT_OF_RANGE_SHIFTS = (480.0, 600.0)


def magnitude(bh: float, style: str = "formal") -> str:
    """``two working days (16 business hours)`` / ``16 bh`` / ``two working days``."""
    words, hours = _MAGNITUDE.get(
        abs(float(bh)), ("{:g} business hours".format(abs(bh)), "{:g} business hours".format(abs(bh)))
    )
    if style == "terse":
        return "{:g} bh".format(abs(bh))
    if style == "conversational":
        return words
    if words == hours:
        return hours
    return "{} ({})".format(words, hours)


def duration(bh: float, style: str = "formal") -> str:
    """A bare length of time, for "for a further X" contexts: ``40 business hours``."""
    if style == "terse":
        return "{:g} bh".format(abs(bh))
    return "{:g} business hours".format(abs(bh))


def snap_shift(minimum: float) -> float:
    """Smallest natural shift strictly above ``minimum`` business hours."""
    for v in NATURAL_SHIFTS:
        if v > minimum:
            return v
    step = 40.0
    v = NATURAL_SHIFTS[-1]
    while v <= minimum:
        v += step
    return v


# --------------------------------------------------------------------------- #
# Priority classes                                                             #
# --------------------------------------------------------------------------- #
#: Response windows are the environment's own SLA constants (8 / 24 / 80 / 171.4
#: business hours for classes 1-4); the words are how a CMMS labels them.
PRIORITY_WORD = {1: "emergency", 2: "urgent", 3: "routine", 4: "deferrable"}


def priority_ref(cls: int, style: str = "formal") -> str:
    if style == "terse":
        return "P{}".format(cls)
    if style == "conversational":
        return "{}".format(PRIORITY_WORD[cls])
    return "priority class {} ({})".format(cls, PRIORITY_WORD[cls])


# --------------------------------------------------------------------------- #
# Reasons: what makes an instruction read like a real message                  #
# --------------------------------------------------------------------------- #
DELAY_REASONS = (
    "the tenant cannot give us access before then",
    "the replacement part is still on back order",
    "the area is handed over to the fit-out contractor until then",
    "the block is closed for the exam period",
    "we are waiting on the permit to work",
)

ADVANCE_REASONS = (
    "the part came in early",
    "the tenant has moved the shutdown forward",
    "we have the riser access earlier than planned",
    "the contractor finished ahead of schedule",
)

#: Kept trade-neutral on purpose: a reason clause is drawn independently of the
#: work order, so anything craft-specific ("no cooling") would end up attached
#: to the wrong kind of job.
URGENCY_REASONS = (
    "the tenant has escalated it to the estates manager",
    "it has already breached the response window",
    "we have had three calls about it this morning",
    "the department head has been on the phone about it",
    "it has been outstanding for a fortnight",
)

BATCH_REASONS = (
    "one trip to that block is enough",
    "access is only worth arranging once",
    "the lift booking covers the whole visit",
    "the crew loses half a day travelling otherwise",
)

FREEZE_REASONS = (
    "the crew is already on site",
    "the isolation is booked around it",
    "the tenant has been told that time",
    "it is part of tomorrow's shutdown",
)


def pick(seq, rng):
    return seq[rng.randrange(len(seq))]


def sentence_case(text: str) -> str:
    text = text.strip()
    if not text:
        return text
    return text[0].upper() + text[1:]


def clean(text: str) -> str:
    """Normalise whitespace and punctuation left by empty optional slots."""
    out = " ".join(text.split())
    out = out.replace(" ,", ",").replace(" .", ".").replace(" ;", ";")
    out = out.replace("..", ".").replace(",,", ",")
    return out.strip()


__all__ = [
    "order_ref",
    "trade_ref",
    "trade_work",
    "trade_work_bare",
    "duration",
    "job_noun",
    "magnitude",
    "snap_shift",
    "priority_ref",
    "PRIORITY_WORD",
    "NATURAL_SHIFTS",
    "OUT_OF_RANGE_SHIFTS",
    "DELAY_REASONS",
    "ADVANCE_REASONS",
    "URGENCY_REASONS",
    "BATCH_REASONS",
    "FREEZE_REASONS",
    "pick",
    "sentence_case",
    "clean",
]
