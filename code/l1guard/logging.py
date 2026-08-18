"""The proposal log: one JSON line per language-model call.

The log is the architecture the whole experiment rests on.  Every LLM call is
expensive and non-reproducible; every guard verdict over it is cheap and exactly
reproducible.  So the run writes down the *raw model output* together with
everything needed to re-derive a verdict from it, and every later question
(what would G-FEAS have passed?  what does tau = 0.15 change?  how do the two
certificate tiers compare?) is answered by :mod:`l1guard.replay` at zero API
cost and zero new sampling variance.

One record per call, appended, never rewritten.  The fields fall into four
groups:

*What was asked*: ``instruction_id``, ``instance_id``, ``instance_path``,
``model``, ``mode``, ``prompt_hash``, ``seeds``.

*What came back*: ``raw_output``, ``finish_reason``, ``outcome`` (``ok``,
``empty_content``, ``refusal``, ``error``: an empty completion is its own
outcome class and is never counted as a schema violation), token usage
(``prompt_tokens``, ``completion_tokens``, ``reasoning_tokens``,
``cache_hit_tokens``, ``cache_miss_tokens``, ``cache_hit``), and ``latency_ms``.

*What the guard made of it*: ``parsed_ops`` or ``parse_error``, ``findings``,
``verdict``, ``certificate``, ``timings_ms``.

*What makes it re-derivable*: ``schema_hash``, ``config_hash``, ``config_name``,
``guard_version``, ``timestamp``.

Token fields are placeholders when no provider filled them in (``None``), so a
record written by a local vLLM run has the same shape as a DeepSeek one and the
cost accounting never has to special-case a source.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

LOG_VERSION = "l1-proposal-log-1"

#: Outcome classes of one model call, before the guard sees anything.
OUTCOME_OK = "ok"
OUTCOME_EMPTY_CONTENT = "empty_content"
OUTCOME_REFUSAL = "refusal"
OUTCOME_ERROR = "error"
OUTCOMES = (OUTCOME_OK, OUTCOME_EMPTY_CONTENT, OUTCOME_REFUSAL, OUTCOME_ERROR)


def prompt_hash(*parts) -> str:
    """Stable hash of the prompt pieces, so identical prompts are detectable."""
    h = hashlib.sha256()
    for p in parts:
        if p is None:
            continue
        if not isinstance(p, str):
            p = json.dumps(p, sort_keys=True, separators=(",", ":"))
        h.update(p.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass
class ProposalRecord:
    """One LLM call and everything derived from it."""

    # -- what was asked ------------------------------------------------------ #
    instruction_id: str
    instance_id: str
    model: str
    mode: str  # "M_free" | "M_constrained" | "replay"
    instance_path: str | None = None
    prompt_hash: str | None = None
    system_prompt: str | None = None
    user_prompt: str | None = None
    temperature: float | None = None
    seeds: dict = field(default_factory=dict)  # {"llm": ..., "dispatch": ...}
    frozen_seed: list = field(default_factory=list)
    rule: str = "atc"

    # -- what came back ------------------------------------------------------ #
    raw_output: str | None = None
    outcome: str = OUTCOME_OK
    finish_reason: str | None = None
    latency_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    reasoning_tokens: int | None = None
    cache_hit_tokens: int | None = None
    cache_miss_tokens: int | None = None
    cache_hit: bool | None = None
    api_error: str | None = None

    # -- what the guard made of it ------------------------------------------- #
    parsed_ops: list | None = None
    parse_error: str | None = None
    findings: list = field(default_factory=list)
    verdict: dict | None = None
    certificate: dict | None = None
    timings_ms: dict = field(default_factory=dict)

    # -- what makes it re-derivable ------------------------------------------ #
    schema_hash: str | None = None
    config_hash: str | None = None
    config_name: str | None = None
    guard_version: str | None = None
    log_version: str = LOG_VERSION
    timestamp: str = field(default_factory=utc_now)
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ProposalRecord":
        known = {f for f in cls.__dataclass_fields__}  # noqa: SLF001
        extra = {k: v for k, v in d.items() if k not in known}
        base = {k: v for k, v in d.items() if k in known}
        rec = cls(**base)
        if extra:
            rec.extra.update(extra)
        return rec

    def attach_verdict(self, verdict) -> "ProposalRecord":
        """Fill the guard-derived fields from a :class:`~l1guard.verdict.Verdict`."""
        d = verdict.to_dict()
        self.parsed_ops = d.get("ops")
        self.parse_error = (d.get("parse") or {}).get("error")
        self.findings = d.get("findings", [])
        self.certificate = d.get("certificate")
        self.timings_ms = d.get("timings_ms", {})
        self.schema_hash = d.get("schema_hash")
        self.config_hash = d.get("config_hash")
        self.config_name = d.get("config_name")
        self.verdict = {
            "terminal": d["terminal"],
            "stage_reached": d["stage_reached"],
            "objective": d.get("objective"),
            "schedule_digest": d.get("schedule_digest"),
            "notes": d.get("notes", []),
            "parse": d.get("parse"),
        }
        return self


class ProposalLog:
    """Append-only JSONL writer/reader.

    ``ProposalLog(path).append(record)`` opens, writes one line, flushes and
    closes, so a crashed run still leaves every completed call on disk.
    """

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record) -> "ProposalLog":
        payload = record.to_dict() if hasattr(record, "to_dict") else dict(record)
        line = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return self

    def extend(self, records) -> "ProposalLog":
        for r in records:
            self.append(r)
        return self

    def read(self) -> list:
        return read_log(self.path)

    def __len__(self) -> int:
        if not self.path.exists():
            return 0
        with open(self.path, "r", encoding="utf-8") as fh:
            return sum(1 for line in fh if line.strip())


def read_log(path) -> list:
    """Read a JSONL log into :class:`ProposalRecord` objects."""
    out = []
    p = Path(path)
    if not p.exists():
        return out
    with open(p, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(ProposalRecord.from_dict(json.loads(line)))
            except (json.JSONDecodeError, TypeError) as exc:
                raise ValueError("log {} line {} is not a record: {}".format(p, i, exc)) from exc
    return out


def read_raw(path) -> list:
    """Read a JSONL log into plain dicts (no field validation)."""
    p = Path(path)
    if not p.exists():
        return []
    with open(p, "r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


__all__ = [
    "LOG_VERSION",
    "OUTCOME_OK",
    "OUTCOME_EMPTY_CONTENT",
    "OUTCOME_REFUSAL",
    "OUTCOME_ERROR",
    "OUTCOMES",
    "prompt_hash",
    "utc_now",
    "ProposalRecord",
    "ProposalLog",
    "read_log",
    "read_raw",
]
