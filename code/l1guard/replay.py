"""Offline replay: any logged proposal, under any guard configuration.

This is the paper's cost saver, and the reason the log carries the raw model
output.  One paid (or GPU-bound) generation pass produces the log; every
comparison that follows is a deterministic recomputation over that log with no
model in the loop:

* the UNGUARDED / G-FEAS / G-CERT ladder (the same proposals, three policies);
* the tau sweep (the same certificates, a moving threshold);
* the Tier 1 vs Tier 2 certificate comparison (the same schedules, two bounds);
* any later re-scoring after a finding-vocabulary extension.

``rerun(log_path, guard_config)`` returns one :class:`~l1guard.verdict.Verdict`
per record, in log order.  Instances are loaded from the path recorded with each
call and cached, and a baseline schedule is dispatched only when the proposal
can need one (it carries a freeze, or the episode has a standing frozen set),
because a baseline costs a full dispatch on the largest instances.

Replay is exact.  A verdict produced here is identical to the verdict the live
run produced under the same configuration, wall-clock excepted; the equivalence
is asserted by ``tests/test_guard_replay.py`` on
:meth:`~l1guard.verdict.Verdict.fingerprint`, which is the verdict with its
timing measurements removed.
"""

from __future__ import annotations

from pathlib import Path

from l1adapter import dispatch as dispatch_mod
from l1adapter import instances as instances_mod

from .config import GuardConfig, preset
from .guard import evaluate_proposal
from .logging import read_log


class InstanceCache:
    """Loads instances and baseline schedules once each."""

    def __init__(self, loader=None, dispatcher=None):
        self._loader = loader or instances_mod.load_instance
        self._dispatch = dispatcher or dispatch_mod.dispatch_baseline
        self._instances: dict = {}
        self._baselines: dict = {}
        self.n_instance_loads = 0
        self.n_baseline_dispatches = 0

    def instance(self, path):
        key = str(path)
        if key not in self._instances:
            self._instances[key] = self._loader(path)
            self.n_instance_loads += 1
        return self._instances[key]

    def baseline(self, path, rule: str, seed: int):
        key = (str(path), rule, int(seed))
        if key not in self._baselines:
            self._baselines[key] = self._dispatch(self.instance(path), rule, seed=seed)
            self.n_baseline_dispatches += 1
        return self._baselines[key]


def _needs_baseline(record) -> bool:
    """Conservative: any standing frozen set, or 'freeze' anywhere in the output.

    ``unfreeze`` contains ``freeze``, so the test over-computes rather than
    under-computes; a missing baseline would turn into a spurious
    ``missing_baseline`` finding, which is exactly the error worth avoiding.
    """
    if record.frozen_seed:
        return True
    raw = record.raw_output or ""
    return "freeze" in raw


def _resolve_path(record, instance_root=None):
    if record.instance_path:
        p = Path(record.instance_path)
        if p.exists():
            return p
        if instance_root is not None:
            candidate = Path(instance_root) / p.name
            if candidate.exists():
                return candidate
    raise FileNotFoundError(
        "cannot resolve the instance for instruction {!r}: instance_path={!r}. "
        "Log every call with an instance_path, or pass instance_root.".format(
            record.instruction_id, record.instance_path
        )
    )


def rerun_pairs(
    log_path,
    guard_config,
    instance_root=None,
    cache: InstanceCache | None = None,
    records=None,
) -> list:
    """Replay a log and return ``(record, verdict)`` pairs, in log order."""
    if isinstance(guard_config, str):
        guard_config = preset(guard_config)
    if not isinstance(guard_config, GuardConfig):
        raise TypeError("guard_config must be a GuardConfig or a preset name")

    if records is None:
        records = read_log(log_path)
    cache = cache or InstanceCache()

    out = []
    for record in records:
        path = _resolve_path(record, instance_root)
        instance = cache.instance(path)
        rule = record.rule or guard_config.rule
        cfg = guard_config if rule == guard_config.rule else guard_config.with_(rule=rule)
        baseline = None
        if _needs_baseline(record):
            baseline = cache.baseline(path, cfg.rule, cfg.seed)
        verdict = evaluate_proposal(
            instance,
            record.raw_output if record.raw_output is not None else "",
            cfg,
            baseline_schedule=baseline,
            frozen_seed=tuple(record.frozen_seed or ()),
        )
        out.append((record, verdict))
    return out


def rerun(
    log_path,
    guard_config,
    instance_root=None,
    cache: InstanceCache | None = None,
    records=None,
) -> list:
    """Replay a log under one guard configuration; verdicts in log order."""
    return [v for _rec, v in rerun_pairs(log_path, guard_config, instance_root, cache, records)]


def terminal_counts(verdicts) -> dict:
    """``terminal state -> count``, the trustworthiness profile's first column."""
    out: dict = {}
    for v in verdicts:
        out[v.terminal] = out.get(v.terminal, 0) + 1
    return dict(sorted(out.items()))


def finding_counts(verdicts, stage: str | None = None) -> dict:
    """``finding code -> count`` over a set of verdicts."""
    out: dict = {}
    for v in verdicts:
        for f in v.findings:
            if stage is not None and f.stage != stage:
                continue
            out[f.code] = out.get(f.code, 0) + 1
    return dict(sorted(out.items()))


__all__ = [
    "InstanceCache",
    "rerun",
    "rerun_pairs",
    "terminal_counts",
    "finding_counts",
]
