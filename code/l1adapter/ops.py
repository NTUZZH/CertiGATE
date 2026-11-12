"""Typed adjustment operations for the frozen v1.0.0 proposal schema.

The schema file ``code/schema/adjustments.schema.json`` (version
``l1-adjustments-1.0.0``) is frozen and is never edited from here.  Every enum
used by this module is read out of that file at import time, so the code cannot
drift from the contract: the trade vocabulary, the priority classes and the
relation names all come from the file itself.

Two levels of checking are available.

* :func:`parse_operations` always applies the structural rules of the schema
  (known op name, required fields present, no extra fields, closed enums,
  correct scalar types) and raises :class:`~l1adapter.errors.SchemaViolation`
  otherwise.  It needs no third-party package.
* :func:`validate_proposal` runs the actual JSON Schema with ``jsonschema`` when
  that package is installed, and is the reference check.

Neither level looks at an instance.  Whether the named order or building
exists, whether the trade matches, whether a shift is in range: all of that is
instance-dependent and belongs to :mod:`l1adapter.apply` (and, in Phase 2, to
the guard).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .errors import SchemaViolation

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "adjustments.schema.json"

# The hash recorded when the schema was frozen (decision record, 2026-08-11).
FROZEN_SCHEMA_SHA256 = "1115fa83d8910ed18a4fa1a421e80aaf4629f4c91fc22f83c81ba32c3fa39321"


def schema_bytes() -> bytes:
    return SCHEMA_PATH.read_bytes()


def schema_sha256() -> str:
    """SHA-256 of the schema file as it sits on disk."""
    return hashlib.sha256(schema_bytes()).hexdigest()


def load_schema() -> dict:
    return json.loads(schema_bytes())


def verify_schema() -> str:
    """Raise if the schema file no longer matches the frozen hash."""
    got = schema_sha256()
    if got != FROZEN_SCHEMA_SHA256:
        raise SchemaViolation(
            "adjustments schema hash {} does not match the frozen "
            "{}".format(got, FROZEN_SCHEMA_SHA256)
        )
    return got


SCHEMA = load_schema()
SCHEMA_VERSION = SCHEMA["$id"]


def _op_blocks() -> dict[str, dict]:
    blocks = {}
    for item in SCHEMA["properties"]["operations"]["items"]["anyOf"]:
        name = item["properties"]["op"]["enum"][0]
        blocks[name] = item
    return blocks


_BLOCKS = _op_blocks()
OP_NAMES: tuple[str, ...] = tuple(_BLOCKS)
TRADE_VOCABULARY: tuple[str, ...] = tuple(_BLOCKS["pin_next"]["properties"]["trade"]["enum"])
PRIORITY_CLASSES: tuple[int, ...] = tuple(
    _BLOCKS["set_priority"]["properties"]["priority_class"]["enum"]
)
RELATIONS: tuple[str, ...] = tuple(_BLOCKS["reorder"]["properties"]["relation"]["enum"])


# --------------------------------------------------------------------------- #
# Typed operations                                                             #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Operation:
    """Base class; every operation is an immutable dataclass with ``op``."""

    op = None

    def to_dict(self) -> dict:
        raise NotImplementedError


@dataclass(frozen=True)
class SetPriority(Operation):
    order_id: str
    priority_class: int
    op = "set_priority"

    def to_dict(self):
        return {"op": self.op, "order_id": self.order_id, "priority_class": self.priority_class}


@dataclass(frozen=True)
class PinNext(Operation):
    order_id: str
    trade: str
    op = "pin_next"

    def to_dict(self):
        return {"op": self.op, "order_id": self.order_id, "trade": self.trade}


@dataclass(frozen=True)
class Reorder(Operation):
    order_id: str
    relation: str
    ref_order_id: str
    op = "reorder"

    def to_dict(self):
        return {
            "op": self.op,
            "order_id": self.order_id,
            "relation": self.relation,
            "ref_order_id": self.ref_order_id,
        }


@dataclass(frozen=True)
class ReassignWindow(Operation):
    order_id: str
    release_shift_bh: float
    op = "reassign_window"

    def to_dict(self):
        return {
            "op": self.op,
            "order_id": self.order_id,
            "release_shift_bh": self.release_shift_bh,
        }


@dataclass(frozen=True)
class Freeze(Operation):
    order_id: str
    op = "freeze"

    def to_dict(self):
        return {"op": self.op, "order_id": self.order_id}


@dataclass(frozen=True)
class Unfreeze(Operation):
    order_id: str
    op = "unfreeze"

    def to_dict(self):
        return {"op": self.op, "order_id": self.order_id}


@dataclass(frozen=True)
class Batch(Operation):
    building_id: str
    trade: str
    op = "batch"

    def to_dict(self):
        return {"op": self.op, "building_id": self.building_id, "trade": self.trade}


_CLASSES = {
    "set_priority": SetPriority,
    "pin_next": PinNext,
    "reorder": Reorder,
    "reassign_window": ReassignWindow,
    "freeze": Freeze,
    "unfreeze": Unfreeze,
    "batch": Batch,
}


# --------------------------------------------------------------------------- #
# Parsing                                                                      #
# --------------------------------------------------------------------------- #
def _require_str(block: dict, field: str, op_name: str) -> str:
    value = block[field]
    if not isinstance(value, str):
        raise SchemaViolation(
            "{}.{} must be a string, got {!r}".format(op_name, field, value)
        )
    return value


def _require_number(block: dict, field: str, op_name: str) -> float:
    value = block[field]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SchemaViolation(
            "{}.{} must be a number, got {!r}".format(op_name, field, value)
        )
    return float(value)


def _parse_one(block) -> Operation:
    if not isinstance(block, dict):
        raise SchemaViolation("each operation must be an object, got {!r}".format(block))
    if "op" not in block:
        raise SchemaViolation("operation object has no 'op' field: {!r}".format(block))
    name = block["op"]
    if name not in _CLASSES:
        raise SchemaViolation(
            "unknown op {!r}; the frozen vocabulary is {}".format(name, list(OP_NAMES))
        )
    spec = _BLOCKS[name]
    required = set(spec["required"])
    allowed = set(spec["properties"])
    keys = set(block)
    missing = sorted(required - keys)
    if missing:
        raise SchemaViolation("{} is missing required field(s) {}".format(name, missing))
    extra = sorted(keys - allowed)
    if extra:
        raise SchemaViolation("{} has field(s) outside the schema: {}".format(name, extra))

    if name == "set_priority":
        cls = block["priority_class"]
        if cls not in PRIORITY_CLASSES or isinstance(cls, bool):
            raise SchemaViolation(
                "set_priority.priority_class must be one of {}, got {!r}".format(
                    list(PRIORITY_CLASSES), cls
                )
            )
        return SetPriority(_require_str(block, "order_id", name), int(cls))
    if name == "pin_next":
        trade = _require_str(block, "trade", name)
        if trade not in TRADE_VOCABULARY:
            raise SchemaViolation(
                "pin_next.trade {!r} is outside the frozen trade vocabulary".format(trade)
            )
        return PinNext(_require_str(block, "order_id", name), trade)
    if name == "reorder":
        rel = _require_str(block, "relation", name)
        if rel not in RELATIONS:
            raise SchemaViolation(
                "reorder.relation must be one of {}, got {!r}".format(list(RELATIONS), rel)
            )
        return Reorder(
            _require_str(block, "order_id", name),
            rel,
            _require_str(block, "ref_order_id", name),
        )
    if name == "reassign_window":
        return ReassignWindow(
            _require_str(block, "order_id", name),
            _require_number(block, "release_shift_bh", name),
        )
    if name == "freeze":
        return Freeze(_require_str(block, "order_id", name))
    if name == "unfreeze":
        return Unfreeze(_require_str(block, "order_id", name))
    # batch
    trade = _require_str(block, "trade", name)
    if trade not in TRADE_VOCABULARY:
        raise SchemaViolation(
            "batch.trade {!r} is outside the frozen trade vocabulary".format(trade)
        )
    return Batch(_require_str(block, "building_id", name), trade)


def parse_operations(proposal, strict_schema: bool = False) -> list[Operation]:
    """Parse ``{"operations": [...]}`` into typed operations.

    ``proposal`` may be the dict itself or the JSON text.  An empty operations
    array parses to an empty list: that is the refusal / no-op signal, not an
    error.  Structural problems raise
    :class:`~l1adapter.errors.SchemaViolation`.

    With ``strict_schema=True`` the real JSON Schema is run first (requires the
    ``jsonschema`` package).
    """
    if isinstance(proposal, (str, bytes)):
        try:
            proposal = json.loads(proposal)
        except json.JSONDecodeError as exc:
            raise SchemaViolation("proposal is not valid JSON: {}".format(exc)) from exc
    if strict_schema:
        validate_proposal(proposal)
    if not isinstance(proposal, dict):
        raise SchemaViolation("proposal must be a JSON object, got {!r}".format(type(proposal)))
    extra = sorted(set(proposal) - {"operations"})
    if extra:
        raise SchemaViolation("proposal has field(s) outside the schema: {}".format(extra))
    if "operations" not in proposal:
        raise SchemaViolation("proposal has no 'operations' field")
    ops = proposal["operations"]
    if not isinstance(ops, list):
        raise SchemaViolation("'operations' must be an array, got {!r}".format(type(ops)))
    return [_parse_one(b) for b in ops]


def to_proposal(ops) -> dict:
    """Serialise typed operations back to a schema-shaped proposal dict."""
    return {"operations": [o.to_dict() for o in ops]}


def validate_proposal(proposal) -> None:
    """Validate against the frozen JSON Schema (needs ``jsonschema``).

    Raises :class:`~l1adapter.errors.SchemaViolation` on any violation and
    ``ImportError`` if ``jsonschema`` is not installed.
    """
    import jsonschema  # local import: the structural parser works without it

    if isinstance(proposal, (str, bytes)):
        try:
            proposal = json.loads(proposal)
        except json.JSONDecodeError as exc:
            raise SchemaViolation("proposal is not valid JSON: {}".format(exc)) from exc
    try:
        jsonschema.validate(instance=proposal, schema=SCHEMA)
    except jsonschema.ValidationError as exc:
        raise SchemaViolation(str(exc).splitlines()[0]) from exc


__all__ = [
    "SCHEMA",
    "SCHEMA_PATH",
    "SCHEMA_VERSION",
    "FROZEN_SCHEMA_SHA256",
    "OP_NAMES",
    "TRADE_VOCABULARY",
    "PRIORITY_CLASSES",
    "RELATIONS",
    "Operation",
    "SetPriority",
    "PinNext",
    "Reorder",
    "ReassignWindow",
    "Freeze",
    "Unfreeze",
    "Batch",
    "parse_operations",
    "to_proposal",
    "validate_proposal",
    "verify_schema",
    "schema_sha256",
    "load_schema",
]


# --------------------------------------------------------------------------- #
# Protocol v1.1.0: the same operations plus one required top-level flag        #
# --------------------------------------------------------------------------- #
# Everything above this line is the frozen v1.0.0 path and is not touched by
# what follows.  Version 1.1.0 (``code/schema/adjustments_v1_1.schema.json``)
# adds one REQUIRED top-level boolean, ``issuer_accepts_cost``: true when the
# instruction explicitly accepts that other work may be delayed as a result,
# false otherwise.  The operations, their fields and their enums are those of
# v1.0.0.
#
# The field is required, not optional, because an optional field is
# wire-dependent: a strict-schema wire cannot express an optional property at
# all, and a model on such a wire fills whatever slot it is given.  A required
# boolean is the same contract on every provider and every enforcement mode.
# The consequence is that a v1.0.0 object (no field) is NOT a valid v1.1.0
# object.  A v1.0.0 output read under v1.1.0 (the relabel of the published E1
# logs) maps to ``issuer_accepts_cost = false`` (:data:`V10_FLAG`).
SCHEMA_V11_PATH = SCHEMA_PATH.parent / "adjustments_v1_1.schema.json"

#: The hash recorded when the v1.1.0 schema was frozen (2026-10-26, required flag).
FROZEN_SCHEMA_V11_SHA256 = "8b9b11a333a27462bd0c5b95e1c79f733f43a6ba9b2ff7fa0058e90b5b7ed1fb"

#: The one field v1.1.0 adds.
FLAG_FIELD = "issuer_accepts_cost"

#: The flag value a v1.0.0 output carries when it is read under v1.1.0.
V10_FLAG = False

VERSION_V10 = "1.0.0"
VERSION_V11 = "1.1.0"
SCHEMA_VERSIONS = (VERSION_V10, VERSION_V11)


def schema_v11_sha256() -> str:
    """SHA-256 of the v1.1.0 schema file as it sits on disk."""
    return hashlib.sha256(SCHEMA_V11_PATH.read_bytes()).hexdigest()


def verify_schema_v11() -> str:
    """Raise if the v1.1.0 schema file no longer matches its frozen hash."""
    got = schema_v11_sha256()
    if got != FROZEN_SCHEMA_V11_SHA256:
        raise SchemaViolation(
            "adjustments schema v1.1.0 hash {} does not match the frozen "
            "{}".format(got, FROZEN_SCHEMA_V11_SHA256)
        )
    return got


SCHEMA_V11 = json.loads(SCHEMA_V11_PATH.read_bytes())
SCHEMA_V11_VERSION = SCHEMA_V11["$id"]


def _version(version: str) -> str:
    """Accept ``"1.1.0"`` or the full ``"l1-adjustments-1.1.0"`` id."""
    v = str(version)
    if v.startswith("l1-adjustments-"):
        v = v[len("l1-adjustments-"):]
    if v not in SCHEMA_VERSIONS:
        raise ValueError(
            "schema version must be one of {}, got {!r}".format(list(SCHEMA_VERSIONS), version)
        )
    return v


def schema_for(version: str) -> dict:
    """The schema document of one version."""
    return SCHEMA if _version(version) == VERSION_V10 else SCHEMA_V11


@dataclass(frozen=True)
class Proposal:
    """A parsed proposal: typed operations plus the v1.1.0 flag.

    ``issuer_accepts_cost`` is the boolean the proposal carried under v1.1.0,
    and ``None`` under v1.0.0, where the field does not exist.
    """

    operations: tuple
    issuer_accepts_cost: bool | None = None
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict:
        out = {"operations": [o.to_dict() for o in self.operations]}
        if self.issuer_accepts_cost is not None:
            out[FLAG_FIELD] = self.issuer_accepts_cost
        return out


def validate_proposal_versioned(proposal, version: str) -> None:
    """Validate against the schema of ``version`` (needs ``jsonschema``).

    Version 1.0.0 delegates to :func:`validate_proposal` unchanged.
    """
    if _version(version) == VERSION_V10:
        validate_proposal(proposal)
        return
    import jsonschema

    if isinstance(proposal, (str, bytes)):
        try:
            proposal = json.loads(proposal)
        except json.JSONDecodeError as exc:
            raise SchemaViolation("proposal is not valid JSON: {}".format(exc)) from exc
    try:
        jsonschema.validate(instance=proposal, schema=SCHEMA_V11)
    except jsonschema.ValidationError as exc:
        raise SchemaViolation(str(exc).splitlines()[0]) from exc


def parse_proposal(proposal, version: str = VERSION_V10, strict_schema: bool = False) -> Proposal:
    """Parse a proposal under an explicit schema version.

    Under ``"1.0.0"`` this is :func:`parse_operations` exactly, wrapped in a
    :class:`Proposal` whose flag is ``None``.  Under ``"1.1.0"`` the top-level
    ``issuer_accepts_cost`` is required and must be a boolean; every other
    rule is the v1.0.0 rule.
    """
    v = _version(version)
    if v == VERSION_V10:
        return Proposal(tuple(parse_operations(proposal, strict_schema=strict_schema)),
                        None, SCHEMA_VERSION)
    if isinstance(proposal, (str, bytes)):
        try:
            proposal = json.loads(proposal)
        except json.JSONDecodeError as exc:
            raise SchemaViolation("proposal is not valid JSON: {}".format(exc)) from exc
    if strict_schema:
        validate_proposal_versioned(proposal, v)
    if not isinstance(proposal, dict):
        raise SchemaViolation("proposal must be a JSON object, got {!r}".format(type(proposal)))
    if FLAG_FIELD not in proposal:
        raise SchemaViolation("proposal is missing required field(s) ['{}']".format(FLAG_FIELD))
    flag = proposal[FLAG_FIELD]
    if not isinstance(flag, bool):
        raise SchemaViolation("{} must be a boolean, got {!r}".format(FLAG_FIELD, flag))
    rest = {k: val for k, val in proposal.items() if k != FLAG_FIELD}
    ops = parse_operations(rest, strict_schema=False)
    return Proposal(tuple(ops), flag, SCHEMA_V11_VERSION)


__all__ += [
    "SCHEMA_V11",
    "SCHEMA_V11_PATH",
    "SCHEMA_V11_VERSION",
    "FROZEN_SCHEMA_V11_SHA256",
    "FLAG_FIELD",
    "V10_FLAG",
    "VERSION_V10",
    "VERSION_V11",
    "SCHEMA_VERSIONS",
    "Proposal",
    "parse_proposal",
    "validate_proposal_versioned",
    "schema_for",
    "schema_v11_sha256",
    "verify_schema_v11",
]
