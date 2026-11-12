"""Protocol v1.1.0: the guard that prices, refers, and records stated acceptance.

The v1.0.0 guard (:mod:`l1guard.guard`) refuses a proposal whose certified
gap exceeds tau.  A deterministic gate cannot know whether a cost is a mistake
or a trade-off the issuer meant, so under v1.1.0 a quality refusal is a
*referral with a price*: the proposal goes to a person with the gate's price
attached, and the baseline stands until that person decides.  The proposer
carries one extra signal, the required top-level boolean
``issuer_accepts_cost`` of schema ``l1-adjustments-1.1.0``, which says whether
the instruction explicitly accepted that other work may be delayed.

Frozen design (revision plan, Section 6, 2026-10-26)
----------------------------------------------------
With p the gate's price of a proposal that passed schema and feasibility:

======================  ==========================  ===============================
price                   flag false                  flag true
======================  ==========================  ===============================
p <= tau                applied_with_certificate    applied_with_certificate
                                                    (flag recorded, unused)
tau < p <= tau_hard     referred_with_price         applied_with_override_record
p > tau_hard            referred_with_price         referred_with_price
                                                    (flag recorded)
======================  ==========================  ===============================

The schema and feasibility stages are the v1.0.0 stages, unchanged: a flag
never rescues a malformed or infeasible proposal.  For the certificate the
price is the certified gap; for the rule (D-REL2) it is the counterfactual
delta, the proposal's weighted tardiness against the same adjusted fields
dispatched with the proposal's dispatch constraints removed; the union prices
at the larger of the two.

How the stages are reused
-------------------------
:func:`evaluate_proposal_v11` reads the flag off the parsed object and hands
the remaining object to the v1.0.0 :func:`~l1guard.guard.evaluate_proposal`,
whose stage 1 then checks exactly the v1.1.0 schema (v1.1.0 adds nothing
else).  The flag is required: an object without it is a ``schema_invalid``
finding with subcode ``missing_field`` and ``check = "flag_missing"``, and a
flag that is not a boolean (null included) is a ``schema_invalid`` finding with
subcode ``type_error``.  A flag written inside an operation object is not a
top-level flag: the operation carries a field outside the schema
(``extra_field``) and the top level misses the flag, so both are reported.
The terminal state is then remapped through the table above, and the
certificate and the verdict carry the flag as received, the price, tau and
tau_hard.

Replays of v1.0.0 logs
----------------------
A v1.0.0 output carries no flag, and under v1.1.0 it is read with the flag
false (``ops.V10_FLAG``).  Replaying it is therefore a relabel, not a new
evaluation (a v1.0.0 object would fail the v1.1.0 schema for the missing
field, which is a property of the protocol change, not of the proposal):
``blocked_qual`` becomes ``referred_with_price`` and every other terminal is
unchanged.  :func:`relabel_v10_terminal` is that mapping.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from l1adapter import apply as apply_mod
from l1adapter import dispatch as dispatch_mod
from l1adapter import evaluate as evaluate_mod
from l1adapter import ops as ops_mod

from . import findings as F
from .config import G_CERT_V11, GuardConfigV11, PricePolicyV11
from .guard import evaluate_proposal
from .verdict import (
    APPLIED_STATES_V11,
    APPLIED_UNCERTIFIED,
    EXECUTION_FAILED,
    APPLIED_WITH_CERTIFICATE,
    APPLIED_WITH_OVERRIDE_RECORD,
    BLOCKED_QUAL,
    BLOCKED_SCHEMA,
    BLOCKED_STATES_V11,
    REFERRED_WITH_PRICE,
    Certificate,
    Verdict,
)

SCHEMA_V11_HASH = ops_mod.verify_schema_v11()  # refuses to import against a drifted file
POLICY_VERSION = "l1-policy-1.1.0"
FLAG = ops_mod.FLAG_FIELD

#: The operations that constrain the dispatcher rather than edit fields.  The
#: D-REL2 counterfactual removes exactly these (``l1suite/checks.py::measure``).
CONSTRAINING_OPS = frozenset({"pin_next", "reorder", "freeze", "unfreeze", "batch"})


# --------------------------------------------------------------------------- #
# The disposition table                                                        #
# --------------------------------------------------------------------------- #
def dispose(price: float, flag, tau: float, tau_hard) -> str:
    """The v1.1.0 terminal of a proposal priced at ``price``.

    Only ``flag is True`` counts as stated acceptance; ``False`` (and ``None``,
    used where no flag could be read) is "not accepted".  ``tau_hard = None`` means no hard ceiling.
    """
    if price <= tau:
        return APPLIED_WITH_CERTIFICATE
    if flag is True and (tau_hard is None or price <= tau_hard):
        return APPLIED_WITH_OVERRIDE_RECORD
    return REFERRED_WITH_PRICE


def relabel_v10_terminal(terminal: str) -> str:
    """A v1.0.0 terminal read under v1.1.0 (no flag exists in v1.0.0 output)."""
    return REFERRED_WITH_PRICE if terminal == BLOCKED_QUAL else terminal


# --------------------------------------------------------------------------- #
# Records                                                                      #
# --------------------------------------------------------------------------- #
@dataclass
class CertificateV11(Certificate):
    """The v1.0.0 certificate plus the flag as received and tau_hard."""

    issuer_accepts_cost: bool | None = None
    tau_hard: float | None = None
    policy_version: str = POLICY_VERSION

    def to_dict(self) -> dict:
        out = super().to_dict()
        out["issuer_accepts_cost"] = self.issuer_accepts_cost
        out["tau_hard"] = self.tau_hard
        out["policy_version"] = self.policy_version
        return out

    @classmethod
    def from_v10(cls, cert: Certificate, flag, tau_hard) -> "CertificateV11":
        return cls(**cert.to_dict(), issuer_accepts_cost=flag, tau_hard=tau_hard)


@dataclass
class VerdictV11(Verdict):
    """A verdict under protocol v1.1.0; ``policy`` records the disposition."""

    policy: dict = field(default_factory=dict)

    @property
    def applied(self) -> bool:
        return self.terminal in APPLIED_STATES_V11

    @property
    def blocked(self) -> bool:
        return self.terminal in BLOCKED_STATES_V11

    @property
    def referred(self) -> bool:
        return self.terminal == REFERRED_WITH_PRICE

    @property
    def overridden(self) -> bool:
        return self.terminal == APPLIED_WITH_OVERRIDE_RECORD

    def to_dict(self) -> dict:
        out = super().to_dict()
        out["policy"] = dict(self.policy)
        return out

    @classmethod
    def from_dict(cls, d: dict) -> "VerdictV11":
        cert = d.get("certificate")
        base = Verdict.from_dict(dict(d, certificate=None))
        kwargs = {k: getattr(base, k) for k in (
            "terminal", "config_name", "config_hash", "schema_hash", "schema_version",
            "instance_id", "findings", "timings_ms", "parse", "ops", "objective",
            "notes", "stage_reached", "rule", "seed", "schedule_digest")}
        kwargs["certificate"] = None if cert is None else CertificateV11.from_dict(cert)
        return cls(policy=dict(d.get("policy") or {}), **kwargs)


# --------------------------------------------------------------------------- #
# Reading the flag                                                             #
# --------------------------------------------------------------------------- #
def read_flag(raw):
    """Split a raw proposal into what the v1.0.0 stages see and the flag.

    Returns ``(payload, flag, findings, parse_note)``.  ``payload`` is the raw
    output unchanged when it does not parse to a JSON object or carries no
    top-level flag (stage 1 then judges it exactly as v1.0.0 does), otherwise
    the object with the flag removed.  ``flag`` is ``True`` / ``False``, or
    ``None`` when no boolean flag was read.  ``findings`` holds the stage-1
    findings the flag itself produces: ``missing_field`` (``check =
    "flag_missing"``) for a JSON object without the top-level flag, and
    ``type_error`` for a flag that is not a boolean.
    """
    note = {"flag_present": False, "flag_raw": None, "flag_missing": False,
            "flag_type_error": False, "source": None}
    if isinstance(raw, (dict, list)):
        obj = raw
        note["source"] = "object"
    else:
        text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
        note["source"] = "text"
        try:
            obj = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return raw, None, [], note
    if not isinstance(obj, dict):
        return raw, None, [], note
    if FLAG not in obj:
        note["flag_missing"] = True
        finding = F.make(
            "schema_invalid",
            "proposal is missing required field(s) ['{}']".format(FLAG),
            subcode="missing_field",
            field=FLAG,
            check="flag_missing",
        )
        return raw, None, [finding], note

    note["flag_present"] = True
    note["flag_raw"] = obj[FLAG]
    value = obj[FLAG]
    payload = {k: v for k, v in obj.items() if k != FLAG}
    if isinstance(value, bool):
        return payload, value, [], note
    note["flag_type_error"] = True
    finding = F.make(
        "schema_invalid",
        "{} must be a boolean, got {!r}".format(FLAG, value),
        subcode="type_error",
        field=FLAG,
    )
    return payload, None, [finding], note


def v10_view(raw):
    """What a v1.0.0 guard is given when a v1.1.0 output is replayed under it.

    The flag is not part of the v1.0.0 vocabulary, so for comparability the
    v1.0.0 configurations judge the operations alone: an output that parses
    to an object carrying ``issuer_accepts_cost`` (any value) is handed over
    as that object without the field; every other output is passed through
    unchanged, byte for byte.
    """
    if isinstance(raw, (dict, list)):
        obj = raw
    else:
        text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
        try:
            obj = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return raw
    if isinstance(obj, dict) and FLAG in obj:
        return {k: v for k, v in obj.items() if k != FLAG}
    return raw


# --------------------------------------------------------------------------- #
# The v1.1.0 guard                                                             #
# --------------------------------------------------------------------------- #
def evaluate_proposal_v11(
    instance: dict,
    raw_text_or_obj,
    config: GuardConfigV11 = G_CERT_V11,
    baseline_schedule: dict | None = None,
    frozen_seed=(),
) -> VerdictV11:
    """Run one proposal through the v1.1.0 guard and return its verdict."""
    if not isinstance(config, GuardConfigV11):
        raise TypeError("evaluate_proposal_v11 needs a GuardConfigV11, got {!r}".format(
            type(config).__name__))
    payload, flag, flag_findings, note = read_flag(raw_text_or_obj)
    base = evaluate_proposal(instance, payload, config, baseline_schedule=baseline_schedule,
                             frozen_seed=frozen_seed)
    kwargs = {k: getattr(base, k) for k in (
        "terminal", "config_name", "config_hash", "instance_id", "certificate",
        "timings_ms", "parse", "ops", "objective", "notes", "stage_reached", "rule",
        "seed", "schedule_digest", "artifacts")}
    verdict = VerdictV11(schema_hash=SCHEMA_V11_HASH, schema_version=ops_mod.SCHEMA_V11_VERSION,
                         findings=list(flag_findings) + list(base.findings), **kwargs)
    parse = dict(verdict.parse or {})
    if note["source"] is not None:
        parse["source"] = note["source"]
    parse["flag_present"] = note["flag_present"]
    parse["flag_missing"] = note["flag_missing"]
    parse["flag_type_error"] = note["flag_type_error"]
    verdict.parse = parse

    if config.gate_schema and any(f.blocking for f in flag_findings):
        # A missing or malformed flag is a stage-1 violation: the verdict stops
        # there and reports every stage-1 finding, as v1.0.0 does for any other
        # required field.
        verdict.findings = list(flag_findings) + [
            f for f in base.findings if f.stage == F.STAGE_SCHEMA]
        verdict.terminal = BLOCKED_SCHEMA
        verdict.stage_reached = "schema"
        verdict.certificate = None
        verdict.objective = None
        verdict.notes = []
        verdict.schedule_digest = None
        verdict.artifacts = {}

    price = None
    if verdict.certificate is not None:
        price = verdict.certificate.gap
        verdict.certificate = CertificateV11.from_v10(verdict.certificate, flag, config.tau_hard)

    if config.gate_qual and verdict.terminal == BLOCKED_QUAL:
        qual_codes = {f.code for f in verdict.findings
                      if f.blocking and f.stage == F.STAGE_QUAL}
        if qual_codes == {"gap_above_tau"} and price is not None:
            verdict.terminal = dispose(price, flag, config.tau, config.tau_hard)
        else:
            # The bound itself is in question (an inadmissible LB): the gate
            # cannot price the proposal, so it refers it without an override.
            verdict.terminal = REFERRED_WITH_PRICE

    verdict.policy = {
        "policy_version": POLICY_VERSION,
        "price_source": "cert" if config.gate_qual else None,
        "price": price,
        "tau": config.tau,
        "tau_hard": config.tau_hard,
        "issuer_accepts_cost": flag,
        "flag_present": note["flag_present"],
        "flag_raw": note["flag_raw"],
        "override": verdict.terminal == APPLIED_WITH_OVERRIDE_RECORD,
    }
    return verdict


# --------------------------------------------------------------------------- #
# The rule-priced policy, as a replay over a feasibility verdict               #
# --------------------------------------------------------------------------- #
def rel2_price(feas_verdict, frozen_seed=(), baseline_schedule=None,
               floor_bh: float = 1.0, round_bh: int = 6) -> dict:
    """The D-REL2 delta of one proposal, from its feasibility-stage verdict.

    ``feas_verdict`` must carry the live ``adjusted`` and ``schedule``
    artifacts (any verdict that reached a dispatched schedule does).  The
    arithmetic is ``delta_baselines._compute_delta`` and
    ``e1_delta_guard_replay.compute_delta`` exactly: the reference is the same
    adjusted fields dispatched with no operation (which removes the
    proposal's dispatch constraints), the difference is rounded to
    ``round_bh`` decimals and divided by ``max(reference, floor_bh)``.  A
    proposal with no constraining operation has the reference equal to its
    own objective by construction.  When the counterfactual does not exist
    (reinstating a standing freeze contradicts a shifted release), the rule
    has nothing to threshold and the delta is ``None``.
    """
    adjusted = feas_verdict.artifacts.get("adjusted")
    schedule = feas_verdict.artifacts.get("schedule")
    if adjusted is None or schedule is None:
        return {"delta": None, "obj_bh": None, "ref_bh": None, "reference_from": "no_schedule"}
    obj = evaluate_mod.wwt(adjusted, schedule)
    ops = feas_verdict.ops or []
    if any(o.get("op") in CONSTRAINING_OPS for o in ops):
        try:
            ref_adjusted = apply_mod.apply_operations(
                adjusted.instance, [], frozen_seed=list(frozen_seed or ()),
                baseline_schedule=baseline_schedule)
            ref_schedule = dispatch_mod.dispatch_adjusted(
                ref_adjusted, feas_verdict.rule, feas_verdict.seed)
            ref = evaluate_mod.wwt(ref_adjusted, ref_schedule)
            source = "dispatched"
        except Exception as exc:  # noqa: BLE001 - a missing counterfactual is data
            return {"delta": None, "obj_bh": obj, "ref_bh": None,
                    "reference_from": "unavailable:" + type(exc).__name__}
    else:
        ref = obj
        source = "identical_by_construction"
    delta = round(obj - ref, round_bh) / max(ref, floor_bh)
    return {"delta": delta, "obj_bh": obj, "ref_bh": ref, "reference_from": source}


def policy_terminal(policy: PricePolicyV11, feas_terminal: str, flag, cert_gap=None,
                    rel2_delta=None) -> dict:
    """The disposition of one proposal under a price policy.

    ``feas_terminal`` is the terminal of the policy's base (``G_FEAS_V11``):
    anything other than ``applied_uncertified`` (a schema or feasibility
    block, an execution failure, a model refusal) is returned unchanged,
    because the price stage is never reached.  Otherwise the price is the
    certified gap, the D-REL2 delta, or the larger of the two.  Two prices can
    be missing, and they mean different things.  A missing certificate is an
    instrument fault, so the certificate policy ends in ``execution_failed``,
    as the live guard does.  A missing rule delta (the counterfactual does not
    exist) is a rule that cannot fire, so the rule policy applies the proposal
    without a price (``applied_uncertified``), exactly as in the DG17 replay;
    the union then prices at the certificate alone.  The terminal names of the
    table are used for every price source, so ``applied_with_certificate``
    under the rule means "priced at or below tau", not "a bound was issued".
    """
    if feas_terminal != APPLIED_UNCERTIFIED:
        return {"terminal": feas_terminal, "price": None, "reached_price": False}
    if policy.price == "cert":
        price = cert_gap
    elif policy.price == "rel2":
        price = rel2_delta
    else:
        price = cert_gap if rel2_delta is None else (
            rel2_delta if cert_gap is None else max(cert_gap, rel2_delta))
    if price is None:
        missing = EXECUTION_FAILED if policy.price in ("cert", "union") and cert_gap is None \
            and (policy.price == "cert" or rel2_delta is None) else APPLIED_UNCERTIFIED
        return {"terminal": missing, "price": None, "reached_price": True}
    return {"terminal": dispose(price, flag, policy.tau, policy.tau_hard),
            "price": price, "reached_price": True}


__all__ = [
    "POLICY_VERSION",
    "SCHEMA_V11_HASH",
    "CONSTRAINING_OPS",
    "CertificateV11",
    "VerdictV11",
    "dispose",
    "relabel_v10_terminal",
    "read_flag",
    "v10_view",
    "evaluate_proposal_v11",
    "rel2_price",
    "policy_terminal",
]
