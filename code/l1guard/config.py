"""Guard configurations: one code path, three published arms.

The three arms of the experiment are *configurations of one guard*, never three
implementations:

``UNGUARDED``
    What the field ships today: repair the model's output enough to parse it,
    then apply it.  No stage gates.  Every finding the three stages would have
    produced is still computed and recorded, so the replay analysis can say
    exactly what got through.
``G_FEAS``
    Stages 1 and 2 gate (schema and feasibility).  This is the boolean guard the
    corpus's propose-and-validate systems implement.
``G_CERT``
    All three stages gate.  An accepted proposal carries a certificate.

Only the ``gate_*`` flags differ between them; the checks themselves are the
same code.  ``config_hash`` is the SHA-256 of the canonical JSON of every field,
so a logged verdict can be tied to the exact policy that produced it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace

#: Provisional quality tolerance.  The published value comes from the E2 offline
#: tau sweep (guidance Section 5.5); until then every certificate carries
#: ``tau_provisional = True`` so no result can be read as final.
TAU_PROVISIONAL = 0.2

#: The declared floor of the gap denominator, in weighted business hours.  The
#: gap convention is gap = (obj - LB) / max(LB, LB_FLOOR_BH): a large share of
#: solver-friendly instances have a zero-tardiness optimum (65.7% of C10 replay
#: under cpsat60), where (obj - LB)/LB is undefined.  One weighted business hour
#: is the smallest unit the objective is reported in, so the convention reads as
#: "excess weighted business hours per weighted business hour of unavoidable
#: tardiness, with one hour as the floor".
LB_FLOOR_BH = 1.0

#: Published legality range for a release shift, in business hours.  400 bh is
#: ten 40-bh weeks, an order of magnitude beyond the longest shipped instance
#: window (80 bh), so it refuses only shifts that are meaningless as instructions.
MAX_SHIFT_BH = 400.0


@dataclass(frozen=True)
class GuardConfig:
    """One guard policy.  Immutable; ``with_(...)`` returns a modified copy."""

    name: str = "G_CERT"

    # -- which stages gate (the only difference between the three arms) ----- #
    gate_schema: bool = True
    gate_feas: bool = True
    gate_qual: bool = True

    # -- stage 1 ------------------------------------------------------------ #
    lenient_repair: bool = False  # UNGUARDED only; the guard itself never repairs
    max_shift_bh: float = MAX_SHIFT_BH

    # -- stage 2 ------------------------------------------------------------ #
    rule: str = "atc"
    seed: int = 0
    run_validator: bool = True  # belt-and-braces referee call on the adjusted schedule

    # -- stage 3 ------------------------------------------------------------ #
    tau: float = TAU_PROVISIONAL
    tau_provisional: bool = True
    lb_floor_bh: float = LB_FLOOR_BH
    lb_tier: str = "tier2"  # "tier2" | "tier1" | "best" (max of both admissible bounds)
    tier1_budget_s: float = 5.0
    tier1_workers: int = 4
    objective_fields: str = "adjusted"  # "adjusted" | "original"
    #: Compute the certificate even when stage 3 does not gate.  Default off:
    #: the certificate for a non-gating arm is recovered for free by replaying
    #: its log under G_CERT, which is the architecture's whole point.
    certify_when_not_gating: bool = False

    # ---------------------------------------------------------------------- #
    def with_(self, **kwargs) -> "GuardConfig":
        return replace(self, **kwargs)

    def to_dict(self) -> dict:
        return asdict(self)

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @property
    def config_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    @property
    def gates(self) -> tuple[str, ...]:
        out = []
        if self.gate_schema:
            out.append("schema")
        if self.gate_feas:
            out.append("feas")
        if self.gate_qual:
            out.append("qual")
        return tuple(out)

    def __post_init__(self):
        if self.lb_tier not in ("tier2", "tier1", "best"):
            raise ValueError("lb_tier must be tier2, tier1 or best, got {!r}".format(self.lb_tier))
        if self.objective_fields not in ("adjusted", "original"):
            raise ValueError(
                "objective_fields must be adjusted or original, got {!r}".format(
                    self.objective_fields
                )
            )
        if self.lb_floor_bh <= 0.0:
            raise ValueError("lb_floor_bh must be positive")
        if self.tau < 0.0:
            raise ValueError("tau must be non-negative")


UNGUARDED = GuardConfig(
    name="UNGUARDED",
    gate_schema=False,
    gate_feas=False,
    gate_qual=False,
    lenient_repair=True,
)

G_FEAS = GuardConfig(name="G_FEAS", gate_qual=False)

G_CERT = GuardConfig(name="G_CERT")

PRESETS: dict[str, GuardConfig] = {c.name: c for c in (UNGUARDED, G_FEAS, G_CERT)}


def preset(name: str) -> GuardConfig:
    try:
        return PRESETS[name]
    except KeyError:
        raise KeyError(
            "unknown guard preset {!r}; available: {}".format(name, sorted(PRESETS))
        ) from None


# --------------------------------------------------------------------------- #
# Protocol v1.1.0: referral with a price, and the issuer's stated acceptance    #
# --------------------------------------------------------------------------- #
# Frozen 2026-10-26 before any v1.1.0 run.  Everything above is v1.0.0 and its
# objects and hashes are unchanged: v1.1.0 is a subclass with two added fields,
# so a v1.0.0 config hashes exactly as before and a v1.1.0 config carries its
# schema version and its hard ceiling inside its own hash.
#
# The disposition a gate gives a proposal whose schema and feasibility stages
# passed, with p the gate's price of the proposal (the certified gap for the
# certificate, the counterfactual delta for the rule):
#
#     p <= tau               applied_with_certificate (flag recorded, unused)
#     tau < p <= tau_hard    referred_with_price if the flag is false,
#                            applied_with_override_record if it is true
#     p > tau_hard           referred_with_price (flag recorded)
#
# ``tau_hard = None`` is the "no hard ceiling" setting of the supplement sweep:
# a flagged proposal is then applied with an override record at any price.

#: The quality tolerance, frozen for v1.1.0 at the E2-selected value.
TAU_V11 = 0.20

#: The primary hard ceiling, 2 tau; the supplement sweeps 0.30, 0.40, 0.60, None.
TAU_HARD_V11 = 0.40
TAU_HARD_SWEEP_V11 = (0.30, 0.40, 0.60, None)

#: The two schema versions a guard config can name.
SCHEMA_V10 = "l1-adjustments-1.0.0"
SCHEMA_V11 = "l1-adjustments-1.1.0"


@dataclass(frozen=True)
class GuardConfigV11(GuardConfig):
    """A v1.1.0 guard policy: the v1.0.0 fields plus the schema version and tau_hard."""

    schema_version: str = SCHEMA_V11
    tau_hard: float | None = TAU_HARD_V11

    def __post_init__(self):
        super().__post_init__()
        if self.schema_version not in (SCHEMA_V10, SCHEMA_V11):
            raise ValueError(
                "schema_version must be {} or {}, got {!r}".format(
                    SCHEMA_V10, SCHEMA_V11, self.schema_version
                )
            )
        if self.tau_hard is not None and self.tau_hard < self.tau:
            raise ValueError("tau_hard must be at least tau")


#: The feasibility guard under schema v1.1.0 (no quality stage).  It is the base
#: the rule-priced v1.1.0 policy acts on.
G_FEAS_V11 = GuardConfigV11(
    name="G_FEAS_V11", gate_qual=False, tau=TAU_V11, tau_provisional=False,
    tier1_budget_s=0.0,
)

#: The certificate-priced v1.1.0 guard.  Tier 2 bound, as in the E1 evaluation
#: (``tier1_budget_s = 0.0``), tau frozen.
G_CERT_V11 = GuardConfigV11(
    name="G_CERT_V11", tau=TAU_V11, tau_provisional=False, tier1_budget_s=0.0,
)

PRESETS_V11: dict[str, GuardConfigV11] = {c.name: c for c in (G_FEAS_V11, G_CERT_V11)}


@dataclass(frozen=True)
class PricePolicyV11:
    """The v1.1.0 disposition table bound to one price source.

    ``price`` is ``"cert"`` (the certified gap of the G_CERT_V11 certificate),
    ``"rel2"`` (the D-REL2 counterfactual delta: the proposal's weighted
    tardiness against the same adjusted fields dispatched with the proposal's
    dispatch constraints removed) or ``"union"`` (the larger of the two, which
    is "refer if either refers").  The schema and feasibility stages are those
    of ``base``; a flag never rescues a malformed or infeasible proposal.
    """

    name: str
    price: str
    tau: float = TAU_V11
    tau_hard: float | None = TAU_HARD_V11
    base: str = "G_FEAS_V11"
    floor_bh: float = LB_FLOOR_BH
    round_bh: int = 6

    def __post_init__(self):
        if self.price not in ("cert", "rel2", "union"):
            raise ValueError("price must be cert, rel2 or union, got {!r}".format(self.price))
        if self.tau_hard is not None and self.tau_hard < self.tau:
            raise ValueError("tau_hard must be at least tau")

    def with_(self, **kwargs) -> "PricePolicyV11":
        return replace(self, **kwargs)

    def to_dict(self) -> dict:
        return asdict(self)

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @property
    def config_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


P_CERT_V11 = PricePolicyV11(name="P_CERT_V11", price="cert")
G_REL2_V11 = PricePolicyV11(name="G_REL2_V11", price="rel2")
G_UNION_V11 = PricePolicyV11(name="G_UNION_V11", price="union")

POLICIES_V11: dict[str, PricePolicyV11] = {
    p.name: p for p in (P_CERT_V11, G_REL2_V11, G_UNION_V11)
}


__all__ = [
    "TAU_V11",
    "TAU_HARD_V11",
    "TAU_HARD_SWEEP_V11",
    "SCHEMA_V10",
    "SCHEMA_V11",
    "GuardConfigV11",
    "G_FEAS_V11",
    "G_CERT_V11",
    "PRESETS_V11",
    "PricePolicyV11",
    "P_CERT_V11",
    "G_REL2_V11",
    "G_UNION_V11",
    "POLICIES_V11",
    "TAU_PROVISIONAL",
    "LB_FLOOR_BH",
    "MAX_SHIFT_BH",
    "GuardConfig",
    "UNGUARDED",
    "G_FEAS",
    "G_CERT",
    "PRESETS",
    "preset",
]
