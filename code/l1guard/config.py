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
    lb_tier: str = "tier2"  # "tier2" | "tier1" | "best".  "tier2" is the
    # deployed certificate (admissible for the continuous objective).
    # "tier1" is proved only against the time-discretized model, so "best"
    # (the larger of the two) inherits that caveat and is a diagnostic
    # setting, not the certificate; see the paper's admissibility appendix.
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


__all__ = [
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
