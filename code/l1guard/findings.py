"""The finding vocabulary: every deterministic observation the guard can make.

A *finding* is one structured observation produced by one guard stage.  It names
the stage that produced it, a closed-vocabulary code, a human-readable message,
the index of the operation it belongs to (``None`` when it is about the proposal
as a whole), and a detail dict carrying the identifiers a downstream taxonomy
needs.

Two severities, and the distinction is what makes the guard a *gate* rather than
a linter:

``violation``
    A reason to block.  If the stage that produced it is gating in the active
    :class:`~l1guard.config.GuardConfig`, the proposal is blocked at that stage.
``info``
    Recorded, never blocking.  These are the adapter's own non-fatal notes (a
    release clipped at zero, an empty batch group) and the refusal signal (an
    empty operations array), which the benchmark needs to count but which no
    honest guard would refuse on.
``infra``
    A fault in the instrument, not a decision about the proposal: the dispatcher
    or the certification path raised.  Never blocking, and **never counted as a
    violation the guard caught**, because a grid that cannot separate instrument
    faults from guard decisions would report its own defects as recall.  The
    instruction ends in ``execution_failed``, which is an outcome, not a block.

Only ``violation`` gates.  Any analysis counting what the guard caught must use
:attr:`Finding.blocking` (or ``severity == "violation"``), never "a finding
exists".

Every code that the guard can emit is registered in :data:`CODES`, with its
stage and severity, and :func:`make` refuses to build a finding whose code is
not registered.  A typo therefore fails loudly at the call site instead of
silently inventing a category that the taxonomy analysis would then miss.
"""

from __future__ import annotations

from dataclasses import dataclass, field

STAGE_SCHEMA = "schema"
STAGE_FEAS = "feas"
STAGE_QUAL = "qual"
STAGES = (STAGE_SCHEMA, STAGE_FEAS, STAGE_QUAL)

VIOLATION = "violation"
INFO = "info"
INFRA = "infra"
SEVERITIES = (VIOLATION, INFO, INFRA)


@dataclass(frozen=True)
class CodeSpec:
    stage: str
    severity: str
    description: str


# --------------------------------------------------------------------------- #
# The closed vocabulary                                                        #
# --------------------------------------------------------------------------- #
CODES: dict[str, CodeSpec] = {
    # -- G_schema ----------------------------------------------------------- #
    "malformed_json": CodeSpec(
        STAGE_SCHEMA, VIOLATION, "the raw output is not parseable JSON"
    ),
    "schema_invalid": CodeSpec(
        STAGE_SCHEMA,
        VIOLATION,
        "the proposal does not validate against the frozen v1.0.0 JSON schema "
        "(detail.subcode names the structural class)",
    ),
    "dangling_order_id": CodeSpec(
        STAGE_SCHEMA, VIOLATION, "an operation names a work order the instance does not contain"
    ),
    "dangling_building_id": CodeSpec(
        STAGE_SCHEMA, VIOLATION, "a batch operation names a building the instance does not contain"
    ),
    "unknown_trade": CodeSpec(
        STAGE_SCHEMA, VIOLATION, "an operation names a trade this instance does not staff"
    ),
    "release_shift_out_of_range": CodeSpec(
        STAGE_SCHEMA,
        VIOLATION,
        "reassign_window asks for a release shift outside the published range",
    ),
    "duplicate_operation": CodeSpec(
        STAGE_SCHEMA,
        VIOLATION,
        "the same operation is applied to the same target twice in one proposal",
    ),
    "empty_proposal": CodeSpec(
        STAGE_SCHEMA,
        INFO,
        "the operations array is empty: the refusal / no-op signal, never a violation",
    ),
    # -- G_feas ------------------------------------------------------------- #
    "trade_mismatch": CodeSpec(
        STAGE_FEAS, VIOLATION, "pin_next names a trade that differs from the work order's trade"
    ),
    "precedence_cycle": CodeSpec(
        STAGE_FEAS, VIOLATION, "the reorder edges contain a cycle, so no start order exists"
    ),
    "frozen_window_conflict": CodeSpec(
        STAGE_FEAS,
        VIOLATION,
        "a frozen order's pinned start sits before its own shifted release",
    ),
    "frozen_precedence_conflict": CodeSpec(
        STAGE_FEAS,
        VIOLATION,
        "two frozen orders have pinned starts that contradict a precedence edge "
        "between them, so no execution satisfies both",
    ),
    "not_frozen": CodeSpec(
        STAGE_FEAS, VIOLATION, "unfreeze names an order that is not in the standing frozen set"
    ),
    "missing_baseline": CodeSpec(
        STAGE_FEAS, VIOLATION, "a freeze was requested with no usable baseline assignment"
    ),
    "frozen_order_edit": CodeSpec(
        STAGE_FEAS,
        VIOLATION,
        "an operation edits an order that is frozen at that point in the proposal",
    ),
    "validator_infeasible": CodeSpec(
        STAGE_FEAS, VIOLATION, "the referee validator rejects the adjusted schedule"
    ),
    "frozen_slot_conflict": CodeSpec(
        STAGE_FEAS, VIOLATION, "a frozen order's baseline slot is not available at its pinned start"
    ),
    "apply_error": CodeSpec(
        STAGE_FEAS, VIOLATION, "the operations could not be applied (unclassified adapter error)"
    ),
    "release_clipped_at_zero": CodeSpec(
        STAGE_FEAS, INFO, "a release shift moved a release below zero and was clipped"
    ),
    "batch_group_empty": CodeSpec(
        STAGE_FEAS, INFO, "a batch group has no eligible member"
    ),
    "batch_members_frozen": CodeSpec(
        STAGE_FEAS, INFO, "a batch group lost frozen members"
    ),
    "precedence_into_frozen_order": CodeSpec(
        STAGE_FEAS, INFO, "a precedence edge points into a frozen order, which cannot move"
    ),
    "precedence_overrides_batch_edd": CodeSpec(
        STAGE_FEAS, INFO, "a precedence edge contradicts a batch group's EDD order"
    ),
    # -- G_qual ------------------------------------------------------------- #
    "gap_above_tau": CodeSpec(
        STAGE_QUAL, VIOLATION, "the certified optimality gap exceeds the published tolerance tau"
    ),
    "lb_unavailable": CodeSpec(
        STAGE_QUAL, VIOLATION, "no usable lower bound was produced, so no certificate exists"
    ),
    "lb_exceeds_objective": CodeSpec(
        STAGE_QUAL,
        INFO,
        "the lower bound came out above the realized objective, which an admissible "
        "bound cannot do: recorded for audit, never used to block",
    ),
    # -- instrument faults, at whichever stage they occur -------------------- #
    "infra_error": CodeSpec(
        STAGE_FEAS,
        INFRA,
        "the instrument failed while dispatching or certifying (a deadlock in the "
        "dispatcher, or an unexpected exception): an instrument fault, never a "
        "guard decision and never a violation caught. The stage is set per "
        "occurrence; the registry's value is the default.",
    ),
}

#: Structural sub-classes of ``schema_invalid`` (detail["subcode"]).  The split
#: is what the enforcement-mode analysis needs: an unknown op name and an
#: out-of-enum value are absorbable by constrained decoding, a missing required
#: field is absorbable too, and none of them require the instance.
SCHEMA_SUBCODES = (
    "not_object",
    "missing_operations",
    "operations_not_array",
    "operation_not_object",
    "unknown_operation",
    "missing_field",
    "extra_field",
    "enum_violation",
    "type_error",
    "other",
)


@dataclass(frozen=True)
class Finding:
    """One structured observation of one guard stage."""

    stage: str
    code: str
    message: str
    op_index: int | None = None
    severity: str = VIOLATION
    detail: dict = field(default_factory=dict)

    @property
    def blocking(self) -> bool:
        return self.severity == VIOLATION

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "code": self.code,
            "message": self.message,
            "op_index": self.op_index,
            "severity": self.severity,
            "detail": dict(self.detail),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Finding":
        return cls(
            stage=d["stage"],
            code=d["code"],
            message=d["message"],
            op_index=d.get("op_index"),
            severity=d.get("severity", VIOLATION),
            detail=dict(d.get("detail") or {}),
        )


def make(
    code: str, message: str, op_index: int | None = None, stage: str | None = None, **detail
) -> Finding:
    """Build a registered finding; raise on an unregistered code.

    ``stage`` overrides the registry's stage, which only ``infra_error`` needs:
    an instrument fault can happen while dispatching (stage 2) or while
    certifying (stage 3), and the finding has to say which.
    """
    spec = CODES.get(code)
    if spec is None:
        raise KeyError(
            "finding code {!r} is not registered; the closed vocabulary is {}".format(
                code, sorted(CODES)
            )
        )
    if code == "schema_invalid":
        sub = detail.get("subcode")
        if sub not in SCHEMA_SUBCODES:
            raise KeyError(
                "schema_invalid needs a registered subcode, got {!r}; the vocabulary "
                "is {}".format(sub, list(SCHEMA_SUBCODES))
            )
    if stage is not None and stage not in STAGES:
        raise KeyError("stage must be one of {}, got {!r}".format(list(STAGES), stage))
    return Finding(
        stage=spec.stage if stage is None else stage,
        code=code,
        message=message,
        op_index=op_index,
        severity=spec.severity,
        detail=detail,
    )


def codes_for_stage(stage: str) -> tuple[str, ...]:
    return tuple(sorted(c for c, s in CODES.items() if s.stage == stage))


def blocking(findings) -> list[Finding]:
    """The findings that are guard decisions; the only ones a block rate counts."""
    return [f for f in findings if f.blocking]


def infra(findings) -> list[Finding]:
    """The instrument faults, which no rate over guard decisions may include."""
    return [f for f in findings if f.severity == INFRA]


__all__ = [
    "STAGE_SCHEMA",
    "STAGE_FEAS",
    "STAGE_QUAL",
    "STAGES",
    "VIOLATION",
    "INFO",
    "INFRA",
    "SEVERITIES",
    "CodeSpec",
    "CODES",
    "SCHEMA_SUBCODES",
    "Finding",
    "make",
    "codes_for_stage",
    "blocking",
    "infra",
]
