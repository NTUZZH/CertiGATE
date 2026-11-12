"""The lenient parser: what a practitioner's harness does before a guard exists.

**This module is not part of the guard.**  ``G_schema`` parses strictly and
records ``repair = None``: a guard that silently repairs its input cannot report
what the model actually produced, and the enforcement-mode analysis depends on
that record being faithful.  The lenient parser exists for exactly one arm,
UNGUARDED, whose published description is "schema-repaired only, then applied":
it is the as-is practice the paper measures against, so it has to be
implemented, named, and kept visibly separate.

Every repair that fires is recorded by name, in the order applied, so the log
says precisely how much work the harness did on the model's behalf.

Repairs, in the order attempted:

``strip_code_fence``
    Remove a surrounding markdown fence (```` ```json ... ``` ````).  This was
    the single failure mode of the unconstrained arm in the environment smoke
    test, and it is the commonest one in the wild.
``extract_first_object``
    Take the first balanced ``{...}`` block, discarding prose before and after.
``wrap_bare_array``
    Wrap a bare ``[...]`` array as ``{"operations": [...]}``: the model produced
    the operations without the envelope the frozen schema requires.
``strip_trailing_commas``
    Remove commas that sit immediately before ``}`` or ``]`` outside a string.

Nothing here rewrites operation names, invents arguments, coerces types, or
fixes enum values.  A repair that changed the *content* of a proposal would
make the measured block rate meaningless.
"""

from __future__ import annotations

import json
import re

FENCE_RE = re.compile(r"```(?:[a-zA-Z0-9_+-]*)\s*(.*?)\s*```", re.DOTALL)

REPAIR_NAMES = (
    "strip_code_fence",
    "extract_first_object",
    "wrap_bare_array",
    "strip_trailing_commas",
)


def _balanced(text: str, open_ch: str, close_ch: str) -> str | None:
    """First balanced ``open_ch ... close_ch`` block, string-aware."""
    start = text.find(open_ch)
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _strip_trailing_commas(text: str) -> str:
    out = []
    in_str = False
    esc = False
    for i, ch in enumerate(text):
        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            continue
        if ch == ",":
            rest = text[i + 1 :]
            stripped = rest.lstrip()
            if stripped[:1] in ("}", "]"):
                continue  # drop the comma
        out.append(ch)
    return "".join(out)


def lenient_parse(text) -> tuple:
    """Return ``(obj, repairs, error)``.

    ``obj`` is the parsed JSON value (``None`` if nothing parsed), ``repairs``
    the list of repair names that fired, and ``error`` the last parse error
    message when ``obj`` is ``None``.
    """
    if isinstance(text, (dict, list)):
        return text, [], None
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    if not isinstance(text, str):
        return None, [], "not text: {!r}".format(type(text))

    repairs: list[str] = []
    error = None

    def attempt(candidate: str):
        nonlocal error
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            error = str(exc)
            return None

    def done(obj):
        """A top-level array is the operations list without its envelope."""
        if isinstance(obj, list):
            if "wrap_bare_array" not in repairs:
                repairs.append("wrap_bare_array")
            return {"operations": obj}, repairs, None
        return obj, repairs, None

    obj = attempt(text)
    if obj is not None:
        return done(obj)

    working = text
    m = FENCE_RE.search(working)
    if m:
        working = m.group(1)
        repairs.append("strip_code_fence")
        obj = attempt(working)
        if obj is not None:
            return done(obj)

    block = _balanced(working, "{", "}")
    if block is not None:
        repairs.append("extract_first_object")
        obj = attempt(block)
        if obj is not None:
            return done(obj)
        cleaned = _strip_trailing_commas(block)
        if cleaned != block:
            repairs.append("strip_trailing_commas")
            obj = attempt(cleaned)
            if obj is not None:
                return done(obj)

    array = _balanced(working, "[", "]")
    if array is not None:
        obj = attempt(array)
        if obj is None:
            cleaned = _strip_trailing_commas(array)
            if cleaned != array:
                repairs.append("strip_trailing_commas")
                obj = attempt(cleaned)
        if obj is not None:
            return done(obj)

    return None, repairs, error


__all__ = ["FENCE_RE", "REPAIR_NAMES", "lenient_parse"]
