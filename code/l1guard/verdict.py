"""The guard's output: a certificate, a terminal state, and everything found.

Terminal states
---------------
Four are produced by a gating guard, and they are the ones the paper reports:

``applied_with_certificate``
    Every gating stage passed and stage 3 produced a certificate whose gap is at
    or below tau.
``blocked_schema`` / ``blocked_feas`` / ``blocked_qual``
    The proposal was refused at that stage; the findings say why, and a block at
    stage 3 still carries its certificate, so the proposal can be returned for
    revision or referral with evidence attached.

Two more exist because two arms of the experiment do not gate at every stage,
and a terminal state must describe what actually happened to the instruction:

``applied_uncertified``
    Applied and executed with no quality certificate.  This is the terminal
    state of the G_FEAS arm on a proposal it passes, and of UNGUARDED on a
    proposal that happens to be executable.  The name is the guidance's own
    (Section 5.4's trustworthiness profile lists *applied-uncertified* as a
    terminal state available to UNGUARDED and G-FEAS).
``execution_failed``
    UNGUARDED only: nothing gated the proposal, and applying it raised, so no
    adjusted schedule exists and the baseline stands.  Recording it as its own
    outcome keeps the "what the field ships today" arm honest: its failures are
    crashes, not refusals.

The certificate tuple
---------------------
The published tuple is ``(obj, lb, gap, tier, lb_wall_ms, solve_wall_ms,
budget_s, lb_variant)``.  Everything else on :class:`Certificate` is auxiliary
recording (both tiers when both were computed, the solver status, the objective
scored against the original fields) and is there so the tier-comparison table
and the E2 analysis need no extra runs.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .findings import Finding

APPLIED_WITH_CERTIFICATE = "applied_with_certificate"
APPLIED_UNCERTIFIED = "applied_uncertified"
BLOCKED_SCHEMA = "blocked_schema"
BLOCKED_FEAS = "blocked_feas"
BLOCKED_QUAL = "blocked_qual"
EXECUTION_FAILED = "execution_failed"
# The proposer's own safety layer ended the request before any document
# existed (hosted stop_reason "refusal").  It is a disposition of the MODEL,
# never of the guard: it stays in every denominator, and it is neither a
# blocked nor an applied state.
MODEL_REFUSED = "model_refused"

TERMINAL_STATES = (
    APPLIED_WITH_CERTIFICATE,
    APPLIED_UNCERTIFIED,
    BLOCKED_SCHEMA,
    BLOCKED_FEAS,
    BLOCKED_QUAL,
    EXECUTION_FAILED,
    MODEL_REFUSED,
)

BLOCKED_STATES = (BLOCKED_SCHEMA, BLOCKED_FEAS, BLOCKED_QUAL)
APPLIED_STATES = (APPLIED_WITH_CERTIFICATE, APPLIED_UNCERTIFIED)


def certified_gap(obj_bh: float, lb_bh: float, floor_bh: float) -> float:
    """gap = (obj - LB) / max(LB, floor), clamped at zero.

    The floor is the declared LB = 0 convention (``config.LB_FLOOR_BH``): a
    zero-tardiness lower bound would otherwise make the ratio undefined.  The
    clamp at zero only ever fires on floating-point noise; a bound genuinely
    above the objective is recorded as an ``lb_exceeds_objective`` finding,
    because an admissible bound cannot do that.
    """
    denom = lb_bh if lb_bh > floor_bh else floor_bh
    gap = (float(obj_bh) - float(lb_bh)) / float(denom)
    return gap if gap > 0.0 else 0.0


@dataclass
class Certificate:
    """The evidence that ships with an accepted (or refused) proposal."""

    # -- the published tuple ------------------------------------------------ #
    obj_bh: float
    lb_bh: float
    gap: float
    tier: str  # "tier1" | "tier2" | "best"
    lb_wall_ms: float  # wall time of the analytic bound (Tier 2)
    solve_wall_ms: float  # wall time of the solver call (Tier 1); 0.0 if not run
    budget_s: float  # solver budget offered (Tier 1); 0.0 if not run
    lb_variant: str  # which bound implementation produced lb_bh

    # -- auxiliary recording ------------------------------------------------ #
    tau: float = 0.0
    tau_provisional: bool = True
    accepted: bool = False
    lb_floor_bh: float = 1.0
    objective_fields: str = "adjusted"
    obj_original_bh: float | None = None
    lb_tier2_bh: float | None = None
    lb_tier1_bh: float | None = None
    tier1_status: str | None = None
    tier1_incumbent_bh: float | None = None
    tier1_relaxation: str = "fields_only"

    def to_dict(self) -> dict:
        return {
            "obj_bh": self.obj_bh,
            "lb_bh": self.lb_bh,
            "gap": self.gap,
            "tier": self.tier,
            "lb_wall_ms": self.lb_wall_ms,
            "solve_wall_ms": self.solve_wall_ms,
            "budget_s": self.budget_s,
            "lb_variant": self.lb_variant,
            "tau": self.tau,
            "tau_provisional": self.tau_provisional,
            "accepted": self.accepted,
            "lb_floor_bh": self.lb_floor_bh,
            "objective_fields": self.objective_fields,
            "obj_original_bh": self.obj_original_bh,
            "lb_tier2_bh": self.lb_tier2_bh,
            "lb_tier1_bh": self.lb_tier1_bh,
            "tier1_status": self.tier1_status,
            "tier1_incumbent_bh": self.tier1_incumbent_bh,
            "tier1_relaxation": self.tier1_relaxation,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Certificate":
        return cls(**d)

    def tuple_str(self) -> str:
        """The published tuple, one line, for the system-output table."""
        return (
            "(obj={:.4f} bh, LB={:.4f} bh, gap={:.4f}, tier={}, lb_wall={:.3f} ms, "
            "solve_wall={:.1f} ms, budget={:.1f} s, variant={})".format(
                self.obj_bh,
                self.lb_bh,
                self.gap,
                self.tier,
                self.lb_wall_ms,
                self.solve_wall_ms,
                self.budget_s,
                self.lb_variant,
            )
        )


@dataclass
class Verdict:
    """Everything one guard evaluation produced."""

    terminal: str
    config_name: str
    config_hash: str
    schema_hash: str
    schema_version: str
    instance_id: str
    findings: list = field(default_factory=list)
    certificate: Certificate | None = None
    timings_ms: dict = field(default_factory=dict)
    parse: dict = field(default_factory=dict)
    ops: list | None = None
    objective: dict | None = None
    notes: list = field(default_factory=list)
    stage_reached: str = "schema"
    rule: str = "atc"
    seed: int = 0
    schedule_digest: str | None = None
    #: Live objects (Adjusted, schedule, validator result).  Never serialised,
    #: never compared: they exist so a demo or a test can look at the schedule
    #: the verdict describes.
    artifacts: dict = field(default_factory=dict, repr=False, compare=False)

    # -- convenience --------------------------------------------------------- #
    @property
    def accepted(self) -> bool:
        return self.terminal == APPLIED_WITH_CERTIFICATE

    @property
    def applied(self) -> bool:
        return self.terminal in APPLIED_STATES

    @property
    def blocked(self) -> bool:
        return self.terminal in BLOCKED_STATES

    def codes(self, stage: str | None = None) -> list:
        return [f.code for f in self.findings if stage is None or f.stage == stage]

    def violations(self) -> list:
        return [f for f in self.findings if f.blocking]

    def to_dict(self) -> dict:
        return {
            "terminal": self.terminal,
            "config_name": self.config_name,
            "config_hash": self.config_hash,
            "schema_hash": self.schema_hash,
            "schema_version": self.schema_version,
            "instance_id": self.instance_id,
            "findings": [f.to_dict() for f in self.findings],
            "certificate": None if self.certificate is None else self.certificate.to_dict(),
            "timings_ms": dict(self.timings_ms),
            "parse": dict(self.parse),
            "ops": None if self.ops is None else [dict(o) for o in self.ops],
            "objective": None if self.objective is None else dict(self.objective),
            "notes": list(self.notes),
            "stage_reached": self.stage_reached,
            "rule": self.rule,
            "seed": self.seed,
            "schedule_digest": self.schedule_digest,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Verdict":
        cert = d.get("certificate")
        return cls(
            terminal=d["terminal"],
            config_name=d["config_name"],
            config_hash=d["config_hash"],
            schema_hash=d["schema_hash"],
            schema_version=d["schema_version"],
            instance_id=d["instance_id"],
            findings=[Finding.from_dict(f) for f in d.get("findings", [])],
            certificate=None if cert is None else Certificate.from_dict(cert),
            timings_ms=dict(d.get("timings_ms") or {}),
            parse=dict(d.get("parse") or {}),
            ops=d.get("ops"),
            objective=d.get("objective"),
            notes=list(d.get("notes") or []),
            stage_reached=d.get("stage_reached", "schema"),
            rule=d.get("rule", "atc"),
            seed=d.get("seed", 0),
            schedule_digest=d.get("schedule_digest"),
        )

    # -- comparison ---------------------------------------------------------- #
    def fingerprint(self) -> str:
        """Canonical JSON of everything except measured wall-clock.

        Two verdicts are *the same verdict* when their fingerprints match.
        Timings are dropped for the same reason the adapter's
        ``canonical_schedule`` drops ``wall_seconds``: a measurement is not
        content, and no two runs of a timer agree.
        """
        d = self.to_dict()
        d.pop("timings_ms", None)
        cert = d.get("certificate")
        if cert is not None:
            for k in ("lb_wall_ms", "solve_wall_ms"):
                cert.pop(k, None)
        return json.dumps(d, sort_keys=True, separators=(",", ":"), default=str)

    def digest(self) -> str:
        return hashlib.sha256(self.fingerprint().encode("utf-8")).hexdigest()

    def summary_line(self) -> str:
        cert = "" if self.certificate is None else "  " + self.certificate.tuple_str()
        codes = ",".join(sorted({f.code for f in self.violations()})) or "-"
        return "{:<24s} {:<26s} violations={}{}".format(
            self.config_name, self.terminal, codes, cert
        )


__all__ = [
    "APPLIED_WITH_CERTIFICATE",
    "APPLIED_UNCERTIFIED",
    "BLOCKED_SCHEMA",
    "BLOCKED_FEAS",
    "BLOCKED_QUAL",
    "EXECUTION_FAILED",
    "MODEL_REFUSED",
    "TERMINAL_STATES",
    "BLOCKED_STATES",
    "APPLIED_STATES",
    "certified_gap",
    "Certificate",
    "Verdict",
]
