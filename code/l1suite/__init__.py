"""l1suite - the injected-violation instruction suite and its generator (D2).

The suite is a set of natural-language facility-management instructions with
ground-truth labels, generated from templates over real instance state through
:mod:`l1adapter`.  Because every item's correct translation is constructed
rather than annotated, the guard's block rate and false-block rate have known
truth by construction; this is the fault-injection design pattern, applied to a
scheduling guard rather than to software under test.

Layout::

    config     sizes, strata, quotas, seeds, and the conventions the suite declares
    codes      violation codes and the guard stage each belongs to
    facts      real instance state and the candidate pools the families select from
    phrasing   register-aware surface helpers (formal / terse / conversational)
    templates  the template families: one message shape, three registers, real slots
    checks     the generator's own assertions (schema, execution, expected errors)
    stats      balance checks and the tables the report quotes
    generate   build_suite(config) -> suite.jsonl, manifest.json, stats.md, audit_sample.csv

Typical use::

    from l1suite import SuiteConfig, build_suite
    build_suite(SuiteConfig())
"""

from __future__ import annotations

from .config import SUITE_VERSION, SuiteConfig, smoke_config
from .generate import build_suite, load_suite, plan, render_ops
from .stats import build_tables, render_stats, verify_balance
from .templates import FAMILIES

__version__ = SUITE_VERSION

__all__ = [
    "__version__",
    "SUITE_VERSION",
    "SuiteConfig",
    "smoke_config",
    "build_suite",
    "load_suite",
    "plan",
    "render_ops",
    "build_tables",
    "render_stats",
    "verify_balance",
    "FAMILIES",
]
