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

# The hash recorded when the schema was frozen (decisions.md, 2026-08-11).
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
