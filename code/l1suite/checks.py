"""The generator's own assertions: an item that fails one of these is a bug.

Nothing in this module is a test of a *model*.  These are the checks that make
the suite's ground truth true by construction:

* every operation list the suite ships validates against the frozen JSON schema
  (the real ``jsonschema`` validator, not the structural parser alone);
* every operation list that is supposed to be executable applies to its own
  instance, dispatches, and produces a schedule the Y1 referee accepts;
* every operation list that is supposed to be impossible raises exactly the
  typed error the item claims, from the stage the item claims;
* no instruction text names the item's own label.

They run inside :func:`l1suite.generate.build_suite`, so a family that drifts
away from the environment's semantics fails the build rather than shipping a
mislabelled item.
"""

from __future__ import annotations

import re

from l1adapter import apply as apply_mod
from l1adapter import dispatch as dispatch_mod
from l1adapter import errors as adapter_errors
from l1adapter import evaluate, ops as ops_mod

from .codes import ADAPTER_RAISED, GUARD_ONLY
from .config import EPISODE_RULE, EPISODE_SEED, MAX_ABS_RELEASE_SHIFT_BH

#: Words that would tell a reader which set an item belongs to.  An instruction
#: containing one of these is leaking its label, whatever else it says.
BANNED_TERMS = (
    "violation", "violations", "violate", "invalid", "ambiguous", "ambiguity",
    "infeasible", "unsatisfiable", "malformed", "dangling", "adversarial",
    "benign", "injection", "injected", "mistranslation", "taxonomy", "gold",
    "trap", "guard", "guardrail", "ground truth", "ground-truth", "test case",
    "testcase", "label", "class v1", "v1", "v2", "v3", "v4", "v5", "v6",
)

_BANNED_RE = re.compile(
    r"(?<![A-Za-z0-9])(" + "|".join(re.escape(t) for t in BANNED_TERMS) + r")(?![A-Za-z0-9])",
    re.IGNORECASE,
)


class SuiteBuildError(AssertionError):
    """A generated item contradicts its own label."""


def label_leaks(text: str):
    """Return the label-revealing terms found in an instruction, if any."""
    return sorted({m.group(1).lower() for m in _BANNED_RE.finditer(text)})


def assert_no_label_leak(item_id: str, text: str) -> None:
    hits = label_leaks(text)
    if hits:
        raise SuiteBuildError("{}: instruction names its own label {}".format(item_id, hits))


def assert_schema_valid(item_id: str, field: str, ops) -> None:
    """Validate an operation list against the frozen schema itself."""
    proposal = {"operations": list(ops)}
    try:
        ops_mod.validate_proposal(proposal)
        ops_mod.parse_operations(proposal)
    except adapter_errors.SchemaViolation as exc:
        raise SuiteBuildError(
            "{}: {} does not match the frozen schema: {}".format(item_id, field, exc)
        ) from exc


def run_ops(facts, ops, frozen_seed=()):
    """Apply and dispatch one operation list on the item's own instance."""
    adjusted = apply_mod.apply_proposal(
        facts.instance,
        {"operations": list(ops)},
        frozen_seed=list(frozen_seed),
        baseline_schedule=facts.baseline,
        strict_schema=True,
    )
    schedule = dispatch_mod.dispatch_adjusted(adjusted, EPISODE_RULE, EPISODE_SEED)
    return adjusted, schedule


def assert_executes(item_id: str, facts, ops, frozen_seed=()) -> dict:
    """The list applies, dispatches, and the referee accepts the schedule.

    Returns the weighted tardiness of the result under both field sets: against
    the instance as it was (``wwt_original``, the deadlines the site actually
    cares about) and against the adjusted instance (``wwt_adjusted``, the
    deadlines the proposal itself installed).  The two differ exactly when the
    proposal edits priority classes or release windows, which is the case the
    guard's certificate has to take a position on.
    """
    try:
        adjusted, schedule = run_ops(facts, ops, frozen_seed)
    except adapter_errors.AdapterError as exc:
        raise SuiteBuildError(
            "{}: operations that should execute raised {}: {}".format(
                item_id, type(exc).__name__, exc
            )
        ) from exc
    result = evaluate.validate(adjusted, schedule)
    if not result["feasible"]:
        raise SuiteBuildError(
            "{}: the referee rejected the resulting schedule: {}".format(
                item_id, result["violations"][:3]
            )
        )
    return {
        "wwt_original": round(evaluate.wwt(adjusted.original, schedule), 6),
        "wwt_adjusted": round(evaluate.wwt(adjusted, schedule), 6),
        "notes": list(adjusted.notes),
        "schedule": schedule,
    }


#: Operations that constrain the dispatcher.  An operation list containing none
#: of these only edits fields, so dispatching it and dispatching the same
#: adjusted fields with nothing imposed are the same call, and the schedule
#: cannot degrade.  That is the whole content of ruling 1 as it lands on the
#: suite: field-only edits are certificate-invisible by construction.
CONSTRAINING_OPS = frozenset({"pin_next", "reorder", "freeze", "unfreeze", "batch"})


def constrains_dispatch(ops) -> bool:
    return any(o["op"] in CONSTRAINING_OPS for o in ops)


def measure(item_id: str, facts, ops, frozen_seed=()) -> dict:
    """Execute an operation list and score the schedule degradation it causes.

    The certificate is adjusted-instance relative (orchestrator ruling 1), so
    the quantity that matters is how far the resulting schedule sits above what
    the same adjusted instance would have produced on its own:

        badness = WWT_adjusted(schedule under the operations)
                - WWT_adjusted(schedule with nothing imposed on the same fields)

    Both terms are scored against the fields the proposal installed, which is
    what G_qual will certify against.  ``wwt_original`` is kept alongside so the
    old, deadline-of-record reading stays available to the analysis.
    """
    adjusted, schedule = run_ops(facts, ops, frozen_seed)
    result = evaluate.validate(adjusted, schedule)
    if not result["feasible"]:
        raise SuiteBuildError(
            "{}: the referee rejected the resulting schedule: {}".format(
                item_id, result["violations"][:3]
            )
        )
    obj_adjusted = evaluate.wwt(adjusted, schedule)
    reference, reference_from = obj_adjusted, "identical_by_construction"
    if constrains_dispatch(ops):
        ref_adjusted = apply_mod.apply_operations(
            adjusted.instance,
            [],
            frozen_seed=list(frozen_seed),
            baseline_schedule=facts.baseline,
        )
        ref_schedule = dispatch_mod.dispatch_adjusted(
            ref_adjusted, EPISODE_RULE, EPISODE_SEED
        )
        reference = evaluate.wwt(ref_adjusted, ref_schedule)
        reference_from = "dispatched"
    return {
        "wwt_adjusted": round(obj_adjusted, 6),
        "wwt_adjusted_reference": round(reference, 6),
        "badness": round(obj_adjusted - reference, 6),
        "badness_relative": round(
            (obj_adjusted - reference) / max(reference, 1.0), 6
        ),
        "wwt_original": round(evaluate.wwt(adjusted.original, schedule), 6),
        "reference_from": reference_from,
        "adapter_notes": list(adjusted.notes),
        "schedule": schedule,
    }


def assert_raises(item_id: str, facts, ops, code: str, frozen_seed=()) -> dict:
    """The literal translation is impossible, with exactly the claimed error.

    ``ArgumentOutOfRange`` is the one code no adapter call raises: the frozen
    schema leaves ``release_shift_bh`` unbounded on purpose, so the suite
    asserts the complementary fact instead (the operations apply cleanly and the
    shift is outside the declared bound), which is what makes the item a
    guard-requiring case rather than a decoder-absorbable one.
    """
    if code in GUARD_ONLY:
        shifts = [
            abs(float(o["release_shift_bh"]))
            for o in ops
            if o["op"] == "reassign_window"
        ]
        if not shifts or max(shifts) <= MAX_ABS_RELEASE_SHIFT_BH:
            raise SuiteBuildError(
                "{}: claims {} but no shift exceeds the declared bound".format(item_id, code)
            )
        try:
            run_ops(facts, ops, frozen_seed)
        except adapter_errors.AdapterError as exc:
            raise SuiteBuildError(
                "{}: {} is a guard-only code, but the adapter raised {}".format(
                    item_id, code, type(exc).__name__
                )
            ) from exc
        return {"raised_by": None, "checked": "declared_bound"}

    expected = getattr(adapter_errors, code)
    where = ADAPTER_RAISED[code]
    try:
        adjusted = apply_mod.apply_proposal(
            facts.instance,
            {"operations": list(ops)},
            frozen_seed=list(frozen_seed),
            baseline_schedule=facts.baseline,
            strict_schema=True,
        )
    except expected:
        if where != "apply":
            raise SuiteBuildError(
                "{}: {} was expected from {}, not from apply".format(item_id, code, where)
            )
        return {"raised_by": "apply", "checked": code}
    except adapter_errors.AdapterError as exc:
        raise SuiteBuildError(
            "{}: expected {} but got {}: {}".format(item_id, code, type(exc).__name__, exc)
        ) from exc
    if where == "apply":
        raise SuiteBuildError("{}: expected {} at apply time, nothing raised".format(item_id, code))
    try:
        dispatch_mod.dispatch_adjusted(adjusted, EPISODE_RULE, EPISODE_SEED)
    except expected:
        return {"raised_by": "dispatch", "checked": code}
    except adapter_errors.AdapterError as exc:
        raise SuiteBuildError(
            "{}: expected {} at dispatch time but got {}".format(item_id, code, type(exc).__name__)
        ) from exc
    raise SuiteBuildError("{}: expected {} at dispatch time, nothing raised".format(item_id, code))


def assert_schema_violation_is_unrepresentable(item_id: str, ops) -> None:
    """A decoder-absorbable item must not ship a schema-valid literal list."""
    if ops:
        raise SuiteBuildError(
            "{}: a decoder-absorbable item cannot carry literal operations "
            "(they would have to be outside the frozen contract)".format(item_id)
        )


__all__ = [
    "BANNED_TERMS",
    "CONSTRAINING_OPS",
    "constrains_dispatch",
    "measure",
    "SuiteBuildError",
    "label_leaks",
    "assert_no_label_leak",
    "assert_schema_valid",
    "assert_executes",
    "assert_raises",
    "assert_schema_violation_is_unrepresentable",
    "run_ops",
]
