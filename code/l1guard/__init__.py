"""l1guard - the three-stage guard, the two certificate tiers, and the log.

This is the instrument the paper measures.  It sits on the Phase 1 environment
adapter (:mod:`l1adapter`), which supplies the deterministic mechanics: parsing
a proposal against the frozen v1.0.0 schema, applying the seven operations,
re-dispatching, and scoring.  Nothing here changes the environment; everything
here decides.

    guard      - ``evaluate_proposal``: G_schema, G_feas, G_qual in one path
    config     - the three arms (UNGUARDED, G_FEAS, G_CERT) as configurations
    findings   - the closed vocabulary of deterministic observations
    verdict    - terminal states, the certificate tuple, verdict fingerprints
    lb2        - Tier 2, the release-aware admissible bound (milliseconds)
    tier1      - Tier 1, the solver-native bound (CP-SAT, per-proposal budget)
    repair     - the lenient parser, for the UNGUARDED arm only
    logging    - the append-only JSONL proposal log
    replay     - re-run any logged proposal under any guard config, offline
    models     - one OpenAI-compatible chat client (vLLM / DeepSeek / OpenAI)

The frozen schema's SHA-256 is asserted at import time: if the contract on disk
is not the one the instrument was built against, importing fails rather than
producing verdicts that cannot be compared with anything.

Typical use::

    from l1adapter import instances, dispatch
    from l1guard import evaluate_proposal, G_CERT

    inst = instances.load_instance(instances.list_instances(9, "storm2")[0])
    base = dispatch.dispatch_baseline(inst, "atc", seed=0)
    v = evaluate_proposal(inst, raw_model_output, G_CERT, baseline_schedule=base)
    print(v.terminal, v.certificate.tuple_str())
"""

from __future__ import annotations

from l1adapter.ops import SCHEMA_VERSION, verify_schema

#: SHA-256 of the frozen adjustment schema, asserted at import.
SCHEMA_HASH = verify_schema()

from . import config, findings, lb2, logging, models, repair, replay, tier1, verdict  # noqa: E402
from .config import G_CERT, G_FEAS, PRESETS, UNGUARDED, GuardConfig, preset  # noqa: E402
from .findings import Finding  # noqa: E402
from .guard import evaluate_proposal  # noqa: E402
from .lb2 import LB2_VARIANT, lb2, lb2_detail  # noqa: E402
from .logging import ProposalLog, ProposalRecord, read_log  # noqa: E402
from .replay import rerun  # noqa: E402
from .tier1 import tier1_certificate  # noqa: E402
from .verdict import Certificate, Verdict  # noqa: E402

# 0.2.0 (2026-08-16): the frozen-order-edit rule in guard._frozen_edit_findings
# is order-invariant. The 0.1.0 rule grew the frozen set operation by
# operation, so freeze-then-shift on one order was refused while
# shift-then-freeze passed; measured on suite v0.2 that order sensitivity was
# the sole blocking reason on 50 benign items and on no violation.
__version__ = "0.2.0"

__all__ = [
    "__version__",
    "SCHEMA_HASH",
    "SCHEMA_VERSION",
    "config",
    "findings",
    "lb2",
    "logging",
    "models",
    "repair",
    "replay",
    "tier1",
    "verdict",
    "GuardConfig",
    "UNGUARDED",
    "G_FEAS",
    "G_CERT",
    "PRESETS",
    "preset",
    "Finding",
    "Certificate",
    "Verdict",
    "evaluate_proposal",
    "lb2",
    "lb2_detail",
    "LB2_VARIANT",
    "tier1_certificate",
    "ProposalLog",
    "ProposalRecord",
    "read_log",
    "rerun",
]
