"""Violation codes carried by suite items, and the guard stage each belongs to.

The adapter raises *mechanical* errors; the guard (Phase 2) decides verdicts.
The mapping below is the orchestrator's directive of 2026-08-11 (decisions.md,
"Design directive for Phase 2"), written down here so the suite's ground truth
and the guard's stage labels cannot drift apart:

* reference existence and argument ranges -> ``G_schema``
* trade mismatch, precedence cycle, release/freeze contradiction, unfreeze of a
  non-frozen order, edits to pre-frozen orders -> ``G_feas``

Two codes are not adapter errors:

``ArgumentOutOfRange``
    ``release_shift_bh`` is deliberately unbounded in the frozen schema, so no
    adapter error exists for a 480-business-hour shift.  The suite declares the
    bound (``config.MAX_ABS_RELEASE_SHIFT_BH``) and the guard's G_schema range
    check has to adopt it; the item carries this code as its expectation.

``SchemaViolation``
    Raised by the adapter's parser, but for suite items it marks the
    decoder-absorbable sub-class of V1: an instruction whose literal translation
    would need an operation name or an enum value outside the frozen contract.
    Constrained decoding removes these before any guard sees them, which is the
    quantity the enforcement-mode axis measures.
"""

from __future__ import annotations

#: code -> guard stage
STAGE_OF_CODE: dict = {
    "SchemaViolation": "G_schema",
    "DanglingOrderID": "G_schema",
    "DanglingBuildingID": "G_schema",
    "UnknownTrade": "G_schema",
    "ArgumentOutOfRange": "G_schema",
    "TradeMismatch": "G_feas",
    "CyclicPrecedence": "G_feas",
    "FrozenWindowConflict": "G_feas",
    "NotFrozen": "G_feas",
}

#: codes the adapter raises itself, with the module that raises them.  The
#: generator asserts each of these on the item's literal operations.
ADAPTER_RAISED: dict = {
    "DanglingOrderID": "apply",
    "DanglingBuildingID": "apply",
    "UnknownTrade": "apply",
    "TradeMismatch": "apply",
    "FrozenWindowConflict": "apply",
    "NotFrozen": "apply",
    "CyclicPrecedence": "dispatch",
}

#: codes no adapter call raises; the guard owns them.
GUARD_ONLY = ("ArgumentOutOfRange",)

#: V1 sub-label: can a constrained decoder absorb this before the guard runs?
DECODER_ABSORBABLE = "decoder_absorbable"
GUARD_REQUIRING = "guard_requiring"


def stage_of(code: str | None) -> str | None:
    if code is None:
        return None
    return STAGE_OF_CODE[code]


__all__ = [
    "STAGE_OF_CODE",
    "ADAPTER_RAISED",
    "GUARD_ONLY",
    "DECODER_ABSORBABLE",
    "GUARD_REQUIRING",
    "stage_of",
]
