"""The three-stage deterministic guard.

``evaluate_proposal(instance, raw, config, baseline_schedule, frozen_seed)``
runs one proposal through

1. **G_schema** - is this a well-formed proposal about *this* instance?
   Strict JSON parse (no repair; the guard records what the model produced),
   validation against the frozen v1.0.0 schema, then the instance-dependent
   checks the schema deliberately does not carry: order and building ids exist,
   the named trade is staffed here, the release shift is inside the published
   range, and no operation is applied to the same target twice.
2. **G_feas** - can the operations be executed together?  Applying them is the
   check (the adapter's typed errors are the mechanism), plus the constraint
   consistency the adapter records rather than judges: precedence cycles,
   edits to frozen orders, freeze/window contradictions.  Where the operations
   apply, the adjusted instance is dispatched and the schedule is handed to the
   Y1 referee, which is the belt-and-braces feasibility check.
3. **G_qual** - is the resulting schedule any good?  The realized objective is
   certified against an admissible lower bound on the adjusted instance, and the
   proposal is accepted only if the certified gap is at or below tau.

The pipeline short-circuits *by stage*: it stops at the first gating stage that
found a violation, and reports everything that stage found, not just the first
thing.  Which stages gate is the only difference between UNGUARDED, G_FEAS and
G_CERT (see :mod:`l1guard.config`); the checks themselves are this one code
path, so no arm can drift from another.

The gap convention is fixed and published:

    gap = (obj - LB) / max(LB, 1.0)

with 1.0 weighted business hour the declared floor.  A large share of
solver-friendly instances have a zero-tardiness optimum, where a plain
``(obj - LB)/LB`` is undefined; the floor turns the ratio into "excess weighted
business hours per weighted business hour of unavoidable tardiness, with one
hour as the floor" and leaves the ratio unchanged wherever ``LB >= 1``.
"""

from __future__ import annotations

import hashlib
import json
from time import perf_counter

from l1adapter import apply as apply_mod
from l1adapter import dispatch as dispatch_mod
from l1adapter import evaluate as evaluate_mod
from l1adapter import ops as ops_mod
from l1adapter.errors import (
    AdapterError,
    CyclicPrecedence,
    DanglingBuildingID,
    DanglingOrderID,
    DispatchDeadlock,
    FrozenPrecedenceConflict,
    FrozenSlotConflict,
    FrozenWindowConflict,
    MissingBaseline,
    NotFrozen,
    SchemaViolation,
    TradeMismatch,
    UnknownTrade,
)

from . import findings as F
from .config import G_CERT, GuardConfig
from .lb2 import LB2_VARIANT, lb2_detail
from .repair import lenient_parse
from .tier1 import TIER1_VARIANT, tier1_certificate
from .verdict import (
    APPLIED_UNCERTIFIED,
    APPLIED_WITH_CERTIFICATE,
    BLOCKED_FEAS,
    BLOCKED_QUAL,
    BLOCKED_SCHEMA,
    EXECUTION_FAILED,
    Certificate,
    Verdict,
    certified_gap,
)

SCHEMA_HASH = ops_mod.verify_schema()  # refuses to import against a drifted schema


# --------------------------------------------------------------------------- #
# Stage 1: G_schema                                                            #
# --------------------------------------------------------------------------- #
_SUBCODE_RULES = (
    # (substring of the structural parser's message, subcode)
    ("each operation must be an object", "operation_not_object"),
    ("has no 'op' field", "missing_field"),
    ("unknown op", "unknown_operation"),
    ("is missing required field", "missing_field"),
    ("field(s) outside the schema", "extra_field"),
    ("outside the frozen trade vocabulary", "enum_violation"),
    ("must be one of", "enum_violation"),
    ("must be a string", "type_error"),
    ("must be a number", "type_error"),
)


def _schema_subcode(message: str) -> str:
    """Deterministic structural class of one schema violation message."""
    for needle, subcode in _SUBCODE_RULES:
        if needle in message:
            return subcode
    return "other"


def _op_target(op) -> tuple:
    """The (op name, target) key used for duplicate detection."""
    name = op.op
    if name == "reorder":
        edge = (
            (op.order_id, op.ref_order_id)
            if op.relation == "before"
            else (op.ref_order_id, op.order_id)
        )
        return (name, edge)
    if name == "batch":
        return (name, (op.building_id, op.trade))
    return (name, (op.order_id,))


def _known_trades(instance: dict) -> set:
    known = set(instance.get("trades", []) or [])
    known.update(t["trade"] for t in instance.get("technicians", []) or [])
    known.update(w["trade"] for w in instance["work_orders"])
    return known


def _stage_schema(instance: dict, raw, config: GuardConfig):
    """Return ``(findings, typed_ops, parse_info)``.

    ``typed_ops`` is ``None`` when nothing parsed, otherwise the list of typed
    operations that survived structural parsing (bad operations are reported and
    dropped, so the later stages see only executable ones).
    """
    out: list = []
    parse = {"ok": False, "repair": None, "error": None, "source": None}

    # -- (a) JSON parse, strictly ------------------------------------------- #
    if isinstance(raw, (dict, list)):
        obj = raw
        parse["ok"] = True
        parse["source"] = "object"
    else:
        text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
        parse["source"] = "text"
        try:
            obj = json.loads(text)
            parse["ok"] = True
        except (json.JSONDecodeError, TypeError) as exc:
            obj = None
            parse["error"] = str(exc)
            out.append(
                F.make("malformed_json", "raw output is not parseable JSON: {}".format(exc))
            )
            if config.lenient_repair:
                repaired, repairs, err = lenient_parse(text)
                parse["repair"] = repairs
                if repaired is not None:
                    obj = repaired
                    parse["ok"] = True
                    parse["repaired"] = True
                else:
                    parse["error"] = err or parse["error"]
    if obj is None:
        return out, None, parse

    # -- (b) the frozen schema ---------------------------------------------- #
    if not isinstance(obj, dict):
        out.append(
            F.make(
                "schema_invalid",
                "proposal must be a JSON object, got {}".format(type(obj).__name__),
                subcode="not_object",
            )
        )
        return out, None, parse

    extra = sorted(set(obj) - {"operations"})
    if extra:
        out.append(
            F.make(
                "schema_invalid",
                "proposal has field(s) outside the schema: {}".format(extra),
                subcode="extra_field",
                fields=extra,
            )
        )
    if "operations" not in obj:
        out.append(
            F.make(
                "schema_invalid",
                "proposal has no 'operations' field",
                subcode="missing_operations",
            )
        )
        return out, None, parse
    blocks = obj["operations"]
    if not isinstance(blocks, list):
        out.append(
            F.make(
                "schema_invalid",
                "'operations' must be an array, got {}".format(type(blocks).__name__),
                subcode="operations_not_array",
            )
        )
        return out, None, parse
    if not blocks:
        out.append(
            F.make("empty_proposal", "the operations array is empty (refusal / no-op signal)")
        )

    typed: list = []
    indices: list = []
    for i, block in enumerate(blocks):
        try:
            parsed = ops_mod.parse_operations({"operations": [block]})
        except SchemaViolation as exc:
            msg = str(exc)
            out.append(
                F.make(
                    "schema_invalid",
                    msg,
                    op_index=i,
                    subcode=_schema_subcode(msg),
                    op=block.get("op") if isinstance(block, dict) else None,
                )
            )
            continue
        typed.append(parsed[0])
        indices.append(i)

    # The frozen JSON Schema is the contract; the per-operation scan above is
    # what makes the report precise.  Run the real validator too, so a proposal
    # that the schema rejects for a reason the scan does not model can never
    # pass silently.
    try:
        ops_mod.validate_proposal(obj)
    except SchemaViolation as exc:
        if not any(f.code == "schema_invalid" for f in out):
            out.append(
                F.make(
                    "schema_invalid",
                    "frozen JSON Schema rejects the proposal: {}".format(exc),
                    subcode="other",
                )
            )
    except ImportError:  # pragma: no cover - jsonschema is a hard dependency here
        pass

    # -- (c) instance-dependent legality ------------------------------------ #
    by_id = {w["id"]: w for w in instance["work_orders"]}
    buildings = {w["building"] for w in instance["work_orders"] if w["building"] is not None}
    trades = _known_trades(instance)

    def _check_order(order_id, i, op_name, field_name="order_id"):
        if order_id not in by_id:
            out.append(
                F.make(
                    "dangling_order_id",
                    "{} names work order {!r}, which is not in instance {}".format(
                        op_name, order_id, instance["meta"]["id"]
                    ),
                    op_index=i,
                    op=op_name,
                    order_id=order_id,
                    field=field_name,
                )
            )

    seen: dict = {}
    for op, i in zip(typed, indices):
        name = op.op
        if name in ("set_priority", "pin_next", "reassign_window", "freeze", "unfreeze"):
            _check_order(op.order_id, i, name)
        elif name == "reorder":
            _check_order(op.order_id, i, name)
            _check_order(op.ref_order_id, i, name, "ref_order_id")
        elif name == "batch":
            if op.building_id not in buildings:
                out.append(
                    F.make(
                        "dangling_building_id",
                        "batch names building {!r}, which is not in instance {}".format(
                            op.building_id, instance["meta"]["id"]
                        ),
                        op_index=i,
                        op=name,
                        building_id=op.building_id,
                    )
                )
        if name in ("pin_next", "batch") and op.trade not in trades:
            out.append(
                F.make(
                    "unknown_trade",
                    "{} names trade {!r}, which instance {} does not staff".format(
                        name, op.trade, instance["meta"]["id"]
                    ),
                    op_index=i,
                    op=name,
                    trade=op.trade,
                )
            )
        if name == "reassign_window":
            shift = float(op.release_shift_bh)
            if abs(shift) > config.max_shift_bh:
                out.append(
                    F.make(
                        "release_shift_out_of_range",
                        "reassign_window asks for {:+.4f} bh; the published range is "
                        "|shift| <= {:.1f} bh".format(shift, config.max_shift_bh),
                        op_index=i,
                        op=name,
                        order_id=op.order_id,
                        release_shift_bh=shift,
                        max_shift_bh=config.max_shift_bh,
                    )
                )
        key = _op_target(op)
        if key in seen:
            out.append(
                F.make(
                    "duplicate_operation",
                    "{} is applied to the same target twice (first at operation "
                    "{})".format(name, seen[key]),
                    op_index=i,
                    op=name,
                    first_op_index=seen[key],
                    target=list(key[1]),
                )
            )
        else:
            seen[key] = i

    return out, typed, parse


# --------------------------------------------------------------------------- #
# Stage 2: G_feas                                                              #
# --------------------------------------------------------------------------- #
#: The adapter's own non-fatal notes, mapped onto recorded findings.  Cycles are
#: deliberately absent: they are detected by the guard's own pre-scan below, so
#: they are still reported when ``apply_operations`` raises on something else
#: first and never produces its notes at all.
_NOTE_CODES = {
    "release_clipped_at_zero": "release_clipped_at_zero",
    "batch_group_empty": "batch_group_empty",
    "batch_members_frozen": "batch_members_frozen",
    "precedence_into_frozen_order": "precedence_into_frozen_order",
    "precedence_overrides_batch_edd": "precedence_overrides_batch_edd",
}


def _cycle_findings(typed_ops) -> list:
    """Precedence cycles, detected before the operations are applied.

    ``apply_operations`` is fail-fast: the first mechanical impossibility it
    meets raises, and everything it would have recorded afterwards is lost.  A
    cycle is cheap to find from the operations alone, so the guard finds it
    itself and a proposal that is both cyclic and (say) trade-mismatched
    reports both.
    """
    edges = []
    for op in typed_ops:
        if op.op != "reorder":
            continue
        edge = (
            (op.order_id, op.ref_order_id)
            if op.relation == "before"
            else (op.ref_order_id, op.order_id)
        )
        if edge not in edges:
            edges.append(edge)
    if not edges:
        return []
    probe = apply_mod.Adjusted(instance={}, original={}, precedence=tuple(edges))
    return [
        F.make(
            "precedence_cycle",
            "the reorder edges cannot all hold: {}".format(" -> ".join(group)),
            cycle=list(group),
        )
        for group in probe.find_cycles()
    ]


def _frozen_edit_findings(instance: dict, typed_ops, frozen_seed) -> list:
    """Operations that edit an order in the episode's standing frozen set.

    Order-invariant since guard v1.1 (2026-08-16): the proposal's operation
    list is one atomic adjustment, so the order in which its own ``freeze``
    and its other operations are written carries no meaning. Only the
    episode's standing frozen set is protected here, and an order the
    proposal ``unfreeze``s anywhere in the list counts as released, because
    unfreezing before editing is the legitimate way to edit committed work.
    A freeze the proposal itself introduces never blocks the proposal's own
    other operations; a genuine contradiction with the frozen slot is caught
    by the adapter's typed errors when the adjustment is applied. The v1.0
    rule instead grew the frozen set operation by operation, which made the
    verdict depend on the listing order: freeze-then-shift on the same order
    was refused while shift-then-freeze passed. Measured on the released
    suite's canonical proposals, that order sensitivity was the sole blocking
    reason on 50 benign items and on no violation, because the adapter flags
    every real conflict on its own; on logged model output it also blocked
    unfaithful translations of freeze-and-shift instructions whose emitted
    operations carried no actual conflict, which inflated the apparent catch
    rate on that violation family. Removing the rule therefore costs no true
    block on any proposal that actually contains its violation.
    """
    out: list = []
    released = {op.order_id for op in typed_ops if op.op == "unfreeze"}
    live = set(frozen_seed or ()) - released
    members_of = {}
    for wo in instance["work_orders"]:
        if wo["building"] is not None:
            members_of.setdefault((wo["building"], wo["trade"]), []).append(wo["id"])

    def flag(i, name, order_id):
        out.append(
            F.make(
                "frozen_order_edit",
                "{} edits work order {!r}, which is frozen at this point in the "
                "proposal".format(name, order_id),
                op_index=i,
                op=name,
                order_id=order_id,
            )
        )

    for i, op in enumerate(typed_ops):
        name = op.op
        if name in ("unfreeze", "freeze"):
            continue
        if name == "batch":
            hit = [o for o in members_of.get((op.building_id, op.trade), []) if o in live]
            for order_id in sorted(hit):
                flag(i, name, order_id)
            continue
        if name == "reorder":
            for order_id in (op.order_id, op.ref_order_id):
                if order_id in live:
                    flag(i, name, order_id)
            continue
        if op.order_id in live:
            flag(i, name, op.order_id)
    return out


#: Every typed error the adapter can raise, mapped onto a finding code.  The
#: mapping is explicit rather than defaulted so that a new adapter error shows
#: up under its own label instead of silently joining ``apply_error``.
#: ``DispatchDeadlock`` is the exception: it is a defensive error of the
#: dispatcher itself, so it is an instrument fault, not a verdict about the
#: proposal (see :func:`_infra_finding`).
_ERROR_CODES = {
    TradeMismatch: "trade_mismatch",
    NotFrozen: "not_frozen",
    MissingBaseline: "missing_baseline",
    FrozenWindowConflict: "frozen_window_conflict",
    FrozenPrecedenceConflict: "frozen_precedence_conflict",
    CyclicPrecedence: "precedence_cycle",
    FrozenSlotConflict: "frozen_slot_conflict",
    DanglingOrderID: "dangling_order_id",
    DanglingBuildingID: "dangling_building_id",
    UnknownTrade: "unknown_trade",
}

_DETAIL_ATTRS = (
    "order_id",
    "ref_order_id",
    "building_id",
    "trade",
    "cycles",
    "start_bh",
    "ref_start_bh",
    "release_bh",
)


def _error_finding(exc: AdapterError):
    code = _ERROR_CODES.get(type(exc), "apply_error")
    detail = {"error": type(exc).__name__}
    for attr in _DETAIL_ATTRS:
        if hasattr(exc, attr):
            detail[attr] = getattr(exc, attr)
    return F.make(code, str(exc), **detail)


def _infra_finding(exc: BaseException, stage: str):
    """An instrument fault: recorded with its exception text, never a violation."""
    detail = {"error": type(exc).__name__}
    if isinstance(exc, DispatchDeadlock):
        detail["unassigned"] = list(exc.unassigned)[:10]
        detail["n_unassigned"] = len(exc.unassigned)
    return F.make(
        "infra_error",
        "{} raised while {}: {}".format(
            type(exc).__name__,
            "dispatching the adjusted instance" if stage == F.STAGE_FEAS
            else "computing the certificate",
            exc,
        ),
        stage=stage,
        **detail,
    )


def _stage_feas(instance: dict, typed_ops, config: GuardConfig, baseline_schedule, frozen_seed):
    """Return ``(findings, adjusted, schedule, validation)``."""
    out = _cycle_findings(typed_ops)
    out.extend(_frozen_edit_findings(instance, typed_ops, frozen_seed))

    try:
        adjusted = apply_mod.apply_operations(
            instance,
            typed_ops,
            frozen_seed=frozen_seed,
            baseline_schedule=baseline_schedule,
        )
    except AdapterError as exc:
        out.append(_error_finding(exc))
        return out, None, None, None

    for note in adjusted.notes:
        head = note.split(":", 1)[0]
        code = _NOTE_CODES.get(head)
        if code is None:  # pragma: no cover - the adapter's note set is closed
            continue
        out.append(F.make(code, "adapter note: {}".format(note), note=note))

    # A cyclic precedence set has no start order, so no execution of the
    # proposal exists at all; dispatching it would only raise.  Every other
    # violation still gets dispatched when the stage does not gate, because the
    # UNGUARDED arm has to execute what it was given.
    if any(f.code == "precedence_cycle" for f in out):
        return out, adjusted, None, None
    if config.gate_feas and any(f.blocking for f in out):
        return out, adjusted, None, None

    # From here on the guard is running the instrument, not judging the
    # proposal.  A dispatcher deadlock or any unexpected exception is an
    # instrument fault: it is recorded with its text, it never counts as a
    # violation the guard caught, and the instruction ends in execution_failed.
    try:
        schedule = dispatch_mod.dispatch_adjusted(adjusted, rule=config.rule, seed=config.seed)
    except DispatchDeadlock as exc:
        out.append(_infra_finding(exc, F.STAGE_FEAS))
        return out, adjusted, None, None
    except AdapterError as exc:
        out.append(_error_finding(exc))
        return out, adjusted, None, None
    except Exception as exc:  # noqa: BLE001 - an instrument fault must be data
        out.append(_infra_finding(exc, F.STAGE_FEAS))
        return out, adjusted, None, None

    validation = None
    if config.run_validator:
        try:
            validation = evaluate_mod.validate(adjusted, schedule)
        except Exception as exc:  # noqa: BLE001 - the referee is instrument too
            out.append(_infra_finding(exc, F.STAGE_FEAS))
            return out, adjusted, None, None
        if not validation["feasible"]:
            out.append(
                F.make(
                    "validator_infeasible",
                    "the referee rejects the adjusted schedule: {}".format(
                        validation["violations"][:3]
                    ),
                    n_violations=len(validation["violations"]),
                    violations=validation["violations"][:5],
                )
            )
    return out, adjusted, schedule, validation


# --------------------------------------------------------------------------- #
# Stage 3: G_qual                                                              #
# --------------------------------------------------------------------------- #
def _stage_qual(adjusted, schedule, config: GuardConfig):
    """Return ``(findings, certificate)``, turning any instrument fault into data."""
    try:
        return _certify(adjusted, schedule, config)
    except Exception as exc:  # noqa: BLE001 - a failed bound is not a verdict
        return [_infra_finding(exc, F.STAGE_QUAL)], None


def _certify(adjusted, schedule, config: GuardConfig):
    out: list = []
    fields = adjusted.instance if config.objective_fields == "adjusted" else adjusted.original
    obj = evaluate_mod.wwt(fields, schedule)
    other = evaluate_mod.wwt(
        adjusted.original if config.objective_fields == "adjusted" else adjusted.instance,
        schedule,
    )

    lb2_bh = None
    lb2_wall = 0.0
    lb1_bh = None
    solve_wall = 0.0
    budget_s = 0.0
    status = None
    incumbent = None

    if config.lb_tier in ("tier2", "best"):
        detail = lb2_detail(fields)
        lb2_bh = detail["lb_bh"]
        lb2_wall = detail["wall_ms"]
    if config.lb_tier in ("tier1", "best"):
        rec = tier1_certificate(
            fields, budget_s=config.tier1_budget_s, workers=config.tier1_workers
        )
        lb1_bh = rec["lb_bh"]
        solve_wall = rec["wall_ms"]
        budget_s = rec["budget_s"]
        status = rec["status"]
        incumbent = rec["objective_bh"]

    candidates = [(v, t) for v, t in ((lb2_bh, "tier2"), (lb1_bh, "tier1")) if v is not None]
    if not candidates:
        out.append(F.make("lb_unavailable", "no lower bound was computed for this proposal"))
        return out, None
    lb_bh, tier = max(candidates, key=lambda pair: pair[0])
    if config.lb_tier == "best":
        tier = "best:" + tier
    variant = LB2_VARIANT if tier.endswith("tier2") else TIER1_VARIANT

    if lb_bh > obj + 1e-6:
        out.append(
            F.make(
                "lb_exceeds_objective",
                "lower bound {:.6f} exceeds the realized objective {:.6f}; an "
                "admissible bound cannot do this".format(lb_bh, obj),
                lb_bh=lb_bh,
                obj_bh=obj,
                tier=tier,
            )
        )

    gap = certified_gap(obj, lb_bh, config.lb_floor_bh)
    accepted = gap <= config.tau
    if not accepted:
        out.append(
            F.make(
                "gap_above_tau",
                "certified gap {:.4f} exceeds tau = {:.4f} (obj {:.4f} bh, LB {:.4f} bh, "
                "tier {})".format(gap, config.tau, obj, lb_bh, tier),
                gap=gap,
                tau=config.tau,
                obj_bh=obj,
                lb_bh=lb_bh,
                tier=tier,
            )
        )

    cert = Certificate(
        obj_bh=obj,
        lb_bh=lb_bh,
        gap=gap,
        tier=tier,
        lb_wall_ms=lb2_wall,
        solve_wall_ms=solve_wall,
        budget_s=budget_s,
        lb_variant=variant,
        tau=config.tau,
        tau_provisional=config.tau_provisional,
        accepted=accepted,
        lb_floor_bh=config.lb_floor_bh,
        objective_fields=config.objective_fields,
        obj_original_bh=other if config.objective_fields == "adjusted" else obj,
        lb_tier2_bh=lb2_bh,
        lb_tier1_bh=lb1_bh,
        tier1_status=status,
        tier1_incumbent_bh=incumbent,
    )
    return out, cert


# --------------------------------------------------------------------------- #
# The pipeline                                                                 #
# --------------------------------------------------------------------------- #
def evaluate_proposal(
    instance: dict,
    raw_text_or_obj,
    config: GuardConfig = G_CERT,
    baseline_schedule: dict | None = None,
    frozen_seed=(),
) -> Verdict:
    """Run one proposal through the guard and return its :class:`Verdict`."""
    t_start = perf_counter()
    timings = {}
    findings: list = []

    verdict = Verdict(
        terminal=EXECUTION_FAILED,
        config_name=config.name,
        config_hash=config.config_hash,
        schema_hash=SCHEMA_HASH,
        schema_version=ops_mod.SCHEMA_VERSION,
        instance_id=instance["meta"]["id"],
        rule=config.rule,
        seed=config.seed,
    )

    def finish(terminal: str, stage_reached: str) -> Verdict:
        verdict.terminal = terminal
        verdict.stage_reached = stage_reached
        verdict.findings = findings
        timings["total"] = (perf_counter() - t_start) * 1000.0
        verdict.timings_ms = timings
        return verdict

    # -- stage 1 ------------------------------------------------------------- #
    t0 = perf_counter()
    schema_findings, typed_ops, parse = _stage_schema(instance, raw_text_or_obj, config)
    timings["schema"] = (perf_counter() - t0) * 1000.0
    findings.extend(schema_findings)
    verdict.parse = parse
    verdict.ops = None if typed_ops is None else [op.to_dict() for op in typed_ops]

    if config.gate_schema and any(f.blocking for f in schema_findings):
        return finish(BLOCKED_SCHEMA, "schema")
    if typed_ops is None:
        # Nothing executable came out of stage 1 and no stage gated it: the
        # UNGUARDED arm simply cannot apply anything.
        return finish(EXECUTION_FAILED, "schema")

    # -- stage 2 ------------------------------------------------------------- #
    t0 = perf_counter()
    feas_findings, adjusted, schedule, validation = _stage_feas(
        instance, typed_ops, config, baseline_schedule, frozen_seed
    )
    timings["feas"] = (perf_counter() - t0) * 1000.0
    findings.extend(feas_findings)
    if adjusted is not None:
        verdict.notes = list(adjusted.notes)
        verdict.artifacts["adjusted"] = adjusted
    if schedule is not None:
        verdict.artifacts["schedule"] = schedule
        verdict.schedule_digest = hashlib.sha256(
            dispatch_mod.canonical_schedule_json(schedule).encode("utf-8")
        ).hexdigest()
        verdict.objective = {
            "wwt_adjusted_bh": evaluate_mod.wwt(adjusted.instance, schedule),
            "wwt_original_bh": evaluate_mod.wwt(adjusted.original, schedule),
            "n_assignments": len(schedule.get("assignments", []) or []),
            "feasible": None if validation is None else bool(validation["feasible"]),
        }
    if validation is not None:
        verdict.artifacts["validation"] = validation

    if config.gate_feas and any(f.blocking for f in feas_findings):
        return finish(BLOCKED_FEAS, "feas")
    if schedule is None:
        # Either an instrument fault (an infra_error is in the findings) or a
        # proposal with no execution in a non-gating arm.  Both end here, and
        # neither is a block.
        return finish(EXECUTION_FAILED, "feas")

    # -- stage 3 ------------------------------------------------------------- #
    if not (config.gate_qual or config.certify_when_not_gating):
        return finish(APPLIED_UNCERTIFIED, "feas")

    t0 = perf_counter()
    qual_findings, certificate = _stage_qual(adjusted, schedule, config)
    timings["qual"] = (perf_counter() - t0) * 1000.0
    findings.extend(qual_findings)
    verdict.certificate = certificate

    if any(f.severity == F.INFRA for f in qual_findings):
        # The certificate could not be computed because the instrument failed.
        # That is not a refusal, and it must never be counted as one.  When the
        # stage gates, the arm could not reach its own outcome, so the
        # instruction ends in execution_failed.  When the certificate is only a
        # shadow (certify_when_not_gating on a non-gating arm), the arm DID
        # reach its outcome and shipped the schedule; relabelling it would
        # corrupt that arm's terminal-state profile, so the fault is recorded
        # and the arm keeps its own terminal.
        if config.gate_qual:
            return finish(EXECUTION_FAILED, "qual")
        return finish(APPLIED_UNCERTIFIED, "qual")
    if config.gate_qual and any(f.blocking for f in qual_findings):
        return finish(BLOCKED_QUAL, "qual")
    if config.gate_qual and certificate is not None and certificate.accepted:
        return finish(APPLIED_WITH_CERTIFICATE, "qual")
    return finish(APPLIED_UNCERTIFIED, "qual")


__all__ = ["SCHEMA_HASH", "evaluate_proposal"]
