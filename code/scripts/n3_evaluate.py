#!/usr/bin/env python
"""N3 evaluation: every logged v1.1.0 proposal under the v1.0.0 and v1.1.0 gates.

One offline pass over one ``grid_n3_hosted.py`` raw log.  No model is called.
The guard is deterministic, so every gate below is a replay configuration
over the same raw outputs:

    G_FEAS        v1.0.0 schema and feasibility gate, for comparability with E1
    G_CERT        v1.0.0 certificate gate (Tier 2, tier1_budget_s = 0.0), as in E1
    G_FEAS_V11    v1.1.0 schema and feasibility gate (the base of the price policies)
    G_CERT_V11    the v1.1.0 guard: certificate price, tau = 0.20, tau_hard = 0.40

The two v1.0.0 configurations are given the operations alone: the flag is not
in their vocabulary, so an output carrying ``issuer_accepts_cost`` is handed to
them without it (``guard_v11.v10_view``) and every other output byte for byte.

On top of the G_FEAS_V11 verdict three price policies are replayed with the
disposition table of protocol v1.1.0 (``l1guard.config``): the certificate
(``P_CERT_V11``), the D-REL2 rule (``G_REL2_V11``) and their union
(``G_UNION_V11``), each at every tau_hard of the supplement sweep (0.30, 0.40,
0.60, none) and each twice: once with the flag the model emitted, once with
the flag replaced by the item's true intent (the simulated approver who knows
what the issuer meant).  ``P_CERT_V11`` at tau_hard = 0.40 is asserted equal,
row by row, to the live ``G_CERT_V11`` guard.

Protocol v1.2 (the ``*_v12`` keys) moves the acceptance off the proposer.  The
acceptance is an approver entry bound to the instruction, simulated here by
the item's label (true on costly_accepted items, false on V3 twins, benign
controls and negated twins); the proposer's output carries no flag and is
judged in the v1.0.0 view (``guard_v11.v10_view``: a top-level flag is
removed, every other output is passed byte for byte, so an output without the
flag is not blocked for its absence).  The base terminal of every v1.2 policy
is therefore the G_FEAS verdict, its certificate price the G_CERT gap and its
rule price the D-REL2 delta of the G_FEAS verdict; the flag the model emitted
is ignored.  Wherever the v1.1.0 base reached the price stage, the v1.0.0 base
must reach it with the same objective and the same certified gap (asserted per
row), so v1.2 differs from the true-intent side only on rows the v1.1.0 schema
stage refused for the flag itself.  ``P_CERT_V11`` at tau_hard = 0.40 on the
v1.2 side is asserted equal, row by row, to the G_CERT verdict disposed with
the approver entry (``live_cert_agrees_v12``).

Two flag measures are recorded per row: ``flag_raw``, the text
``"issuer_accepts_cost": true`` anywhere in the raw output (whitespace
tolerated), and ``flag_valid``, the flag the guard received true at the top
level of an object that passed the v1.1.0 schema stage.  A row with the first
and not the second is ``flag_misplaced``: the model wrote the flag where the
contract does not read it (inside an operation, say), which is a format
failure and not a statement about intent.  Intent fidelity uses
``flag_valid``.  The disposition replays use the flag as the guard read it.

The run metadata of the raw log is checked before anything is evaluated: a
log generated under another v1.1.0 prompt or schema text (a superseded
variant with the same version label) is refused.

Intended dispositions come from the item's own gold operations, carrying the
item's true flag, priced by the same gates once per item (revision plan,
Section 6):

* costly_accepted: the table with the flag set, so
  applied_with_override_record when the gold price is in (tau, tau_hard],
  applied_with_certificate when it is at most tau, referred_with_price above
  tau_hard;
* v3_twin: referred_with_price above tau, applied_with_certificate otherwise;
* benign_control: applied_with_certificate (an override on a benign item is a
  consequence of a false acceptance and is counted as incorrect);
* costly_negated (the V3 twins with a clause that refuses the knock-on delay,
  ``suite_ext_neg.jsonl``): as v3_twin, since the issuer does not accept the
  cost; its raw log's run meta must name the negated file's sha256.

Outputs, under ``--out``:

``verdicts_<CONFIG>.jsonl``   one line per (row, configuration), the E1 verdict
                              format plus ``item_set`` and the flag fields
``dispositions.jsonl``        one line per row: the flag as emitted, the three
                              prices, every policy x tau_hard terminal under
                              the model flag and under the true intent, the
                              intended terminal, the correctness flags, the
                              executed and anchor objectives, and the
                              operation match against gold
``gold_prices.jsonl``         one line per item: the gold prices per gate
``run_meta.json``             hashes of every input and configuration

Run::

    python scripts/n3_evaluate.py --raw results/n3_sonnet/proposals_raw.jsonl \\
        --out results/n3_eval_sonnet --workers 8
"""

from __future__ import annotations

import os

for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
             "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_var] = "1"
os.environ.setdefault("L1_INSTANCE_ROOT",
                      ((os.environ.get("L1_Y1_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "PaperY-FMScheduling")) + "/data/processed/instances_v10"))

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import multiprocessing as mp  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from collections import Counter, OrderedDict  # noqa: E402
from pathlib import Path  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent
CODE_DIR = SCRIPTS_DIR.parent
for _p in (str(CODE_DIR), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import e1_evaluate as e1  # noqa: E402  (verdict summaries, row loading)
import suite_gate as sg  # noqa: E402

from l1adapter import apply as apply_mod  # noqa: E402
from l1adapter import dispatch as dispatch_mod  # noqa: E402
from l1adapter import evaluate as evaluate_mod  # noqa: E402
from l1adapter import ops as ops_mod  # noqa: E402
from l1guard import G_CERT, G_FEAS, evaluate_proposal, prompts  # noqa: E402
from l1guard import findings as F  # noqa: E402
from l1guard.config import (  # noqa: E402
    G_CERT_V11,
    G_FEAS_V11,
    POLICIES_V11,
    TAU_HARD_SWEEP_V11,
    TAU_HARD_V11,
)
from l1guard.guard_v11 import (  # noqa: E402
    POLICY_VERSION,
    dispose,
    evaluate_proposal_v11,
    policy_terminal,
    read_flag,
    rel2_price,
    v10_view,
)
from l1guard.verdict import (  # noqa: E402
    APPLIED_STATES_V11,
    APPLIED_UNCERTIFIED,
    APPLIED_WITH_CERTIFICATE,
    BLOCKED_QUAL,
    MODEL_REFUSED,
    REFERRED_WITH_PRICE,
)

EVAL_VERSION = "l1-n3-eval-2"
#: The protocol the ``*_v12`` keys of ``dispositions.jsonl`` replay.
PROTOCOL_V12 = "l1-policy-1.2.0"
CONFIG_NAMES = ("G_FEAS", "G_CERT", "G_FEAS_V11", "G_CERT_V11")
ITEM_SETS = ("costly_accepted", "v3_twin", "benign_control", "costly_negated")
EXT_PATH = CODE_DIR / "suite" / "v1.1" / "suite_ext.jsonl"
EXT_NEG_PATH = CODE_DIR / "suite" / "v1.1" / "suite_ext_neg.jsonl"


def tau_key(tau_hard) -> str:
    return "none" if tau_hard is None else "{:.2f}".format(tau_hard)


def guard_configs() -> "OrderedDict[str, object]":
    cfgs = OrderedDict()
    cfgs["G_FEAS"] = G_FEAS
    cfgs["G_CERT"] = G_CERT.with_(tier1_budget_s=0.0)
    cfgs["G_FEAS_V11"] = G_FEAS_V11
    cfgs["G_CERT_V11"] = G_CERT_V11
    return cfgs


def intended_terminal(item_set: str, price, tau: float, tau_hard):
    """The disposition the item's gold proposal should receive under a gate."""
    if item_set == "benign_control":
        return APPLIED_WITH_CERTIFICATE
    if price is None:
        return None  # the gate cannot price the gold proposal; no intended value
    flag = True if item_set == "costly_accepted" else None
    return dispose(price, flag, tau, tau_hard)


def approver_entry(gold_intent: bool) -> bool:
    """The v1.2 acceptance: an approver entry bound to the instruction.

    In the benchmark the entry is the item's own label, true on
    costly_accepted items and false everywhere else.  It never depends on the
    proposer's output.
    """
    return bool(gold_intent)


def live_terminal_v12(cert10, approver: bool, tau: float, tau_hard) -> str:
    """The v1.2 terminal of the G_CERT verdict, disposed with the approver entry.

    Mirrors the remapping inside ``evaluate_proposal_v11``: a quality block
    whose only blocking code is ``gap_above_tau`` goes through the disposition
    table; a quality block for any other reason (the bound itself is in
    question) is referred without an override; every other terminal is kept.
    """
    if cert10.terminal != BLOCKED_QUAL:
        return cert10.terminal
    codes = {f.code for f in cert10.findings if f.blocking and f.stage == F.STAGE_QUAL}
    if codes == {"gap_above_tau"} and cert10.certificate is not None:
        return dispose(cert10.certificate.gap, approver, tau, tau_hard)
    return REFERRED_WITH_PRICE


# --------------------------------------------------------------------------- #
# Worker side                                                                  #
# --------------------------------------------------------------------------- #
_ROWS: list = []
_GOLD: dict = {}
_STATE: dict = {}


def _init_worker():
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        os.environ[var] = "1"
    from l1guard.replay import InstanceCache

    _STATE["cache"] = InstanceCache()
    _STATE["cfgs"] = guard_configs()
    _STATE["anchors"] = {}


#: The lenient raw-text test for an emitted acceptance, wherever it sits.
FLAG_RAW_RE = re.compile(r'"issuer_accepts_cost"\s*:\s*true\b')


def flag_measures(raw, flag, feas) -> dict:
    """The two flag measures of one row, and the misplacement between them.

    ``flag_raw``: the text ``"issuer_accepts_cost": true`` appears anywhere in
    the raw output (whitespace tolerated), so a model that wrote the flag in
    the wrong place still counts.  ``flag_valid``: the guard received the flag
    true at the top level of an object that passed the v1.1.0 schema stage.
    ``flag_misplaced``: raw true but not valid, which is a wire or format
    failure, not a statement about intent.
    """
    flag_raw = bool(FLAG_RAW_RE.search(raw or ""))
    schema_ok = feas is not None and not any(
        f.blocking and f.stage == "schema" for f in feas.findings)
    flag_valid = bool(flag is True and schema_ok)
    return {"flag_raw": flag_raw, "flag_valid": flag_valid,
            "flag_misplaced": flag_raw and not flag_valid, "schema_valid": schema_ok}


def _needs_baseline(frozen, raw) -> bool:
    return bool(frozen) or "freeze" in (raw or "")


def _anchor(path, instance, frozen, baseline):
    """The no-AI anchor: the unadjusted instance dispatched at the episode rule."""
    key = (path, tuple(frozen))
    cache = _STATE["anchors"]
    if key not in cache:
        adjusted = apply_mod.apply_operations(instance, [], frozen_seed=list(frozen),
                                              baseline_schedule=baseline)
        schedule = dispatch_mod.dispatch_adjusted(adjusted, "atc", 0)
        cache[key] = evaluate_mod.wwt(adjusted.original, schedule)
    return cache[key]


def _gold_prices(item_id, path, instance, frozen, baseline_full):
    cache = _STATE.setdefault("gold", {})
    if item_id in cache:
        return cache[item_id]
    gold = _GOLD[item_id]
    payload = {"operations": gold["gold_ops"], ops_mod.FLAG_FIELD: bool(gold["gold_intent"])}
    text = json.dumps(payload)
    base = baseline_full if _needs_baseline(frozen, text) else None
    feas = evaluate_proposal_v11(instance, text, G_FEAS_V11, baseline_schedule=base,
                                 frozen_seed=tuple(frozen))
    cert = evaluate_proposal_v11(instance, text, G_CERT_V11, baseline_schedule=base,
                                 frozen_seed=tuple(frozen))
    rel2 = rel2_price(feas, frozen, baseline_full)
    gap = None if cert.certificate is None else cert.certificate.gap
    prices = {"cert": gap, "rel2": rel2["delta"],
              "union": None if gap is None and rel2["delta"] is None else
              max(p for p in (gap, rel2["delta"]) if p is not None)}
    out = {"item_id": item_id, "item_set": gold["item_set"], "feas_terminal": feas.terminal,
           "cert_terminal": cert.terminal, "prices": prices,
           "rel2_reference_from": rel2["reference_from"],
           "feas_findings": sorted({f.code for f in feas.findings if f.blocking}),
           "gold_obj_original_bh": None if feas.objective is None
           else feas.objective["wwt_original_bh"]}
    cache[item_id] = out
    return out


def _eval_chunk(indices) -> dict:
    cache = _STATE["cache"]
    cfgs = _STATE["cfgs"]
    out, golds = [], {}
    for i in indices:
        row = _ROWS[i]
        path = row["instance_path"]
        frozen = list(row.get("frozen_seed") or [])
        instance = cache.instance(path)
        baseline_full = cache.baseline(path, "atc", 0)
        gold = _gold_prices(row["item_id"], path, instance, frozen, baseline_full)
        golds[row["item_id"]] = gold
        anchor = _anchor(path, instance, frozen, baseline_full)
        gold_intent = bool((row.get("gold_intent") or {}).get(ops_mod.FLAG_FIELD))

        if row.get("outcome") == "refusal":
            summary = {"terminal": MODEL_REFUSED, "stage_reached": "model", "fingerprint": None,
                       "findings": [{"stage": "model", "code": "model_refusal",
                                     "severity": "violation"}],
                       "blocking_codes": [], "infra": False, "certificate_gap": None,
                       "certificate": None, "parse_ok": False, "parse_repaired": False,
                       "n_ops": None}
            verdicts = {name: dict(summary) for name in cfgs}
            measures = flag_measures("", None, None)
            disp = _disposition(row, None, None, None, None, MODEL_REFUSED, gold,
                                gold_intent, None, anchor, None, None, measures, v12=None)
            out.append({"i": i, "verdicts": verdicts, "flag": dict(measures, value=None,
                        present=False, missing=False, type_error=False), "disposition": disp})
            continue

        raw = row.get("raw_output") or ""
        need = _needs_baseline(frozen, raw)
        baseline = baseline_full if need else None
        verdicts = {}
        v10_payload = v10_view(raw)
        v10 = {}
        for name in ("G_FEAS", "G_CERT"):
            v = evaluate_proposal(instance, v10_payload, cfgs[name], baseline_schedule=baseline,
                                  frozen_seed=tuple(frozen))
            v10[name] = v
            verdicts[name] = e1._summarise_verdict(v)
        feas = evaluate_proposal_v11(instance, raw, cfgs["G_FEAS_V11"],
                                     baseline_schedule=baseline, frozen_seed=tuple(frozen))
        cert = evaluate_proposal_v11(instance, raw, cfgs["G_CERT_V11"],
                                     baseline_schedule=baseline, frozen_seed=tuple(frozen))
        verdicts["G_FEAS_V11"] = e1._summarise_verdict(feas)
        verdicts["G_CERT_V11"] = e1._summarise_verdict(cert)
        verdicts["G_CERT_V11"]["policy"] = dict(cert.policy)

        _, flag, flag_findings, note = read_flag(raw)
        rel2 = rel2_price(feas, frozen, baseline_full) if feas.terminal == "applied_uncertified" \
            else {"delta": None, "reference_from": "not_reached"}
        gap = None if cert.certificate is None else cert.certificate.gap
        executed = None if feas.objective is None else feas.objective["wwt_original_bh"]
        measures = flag_measures(raw, flag, feas)
        v12 = _v12_inputs(row, v10["G_FEAS"], v10["G_CERT"], feas, gap, rel2, executed,
                          frozen, baseline_full)
        disp = _disposition(row, feas, gap, rel2, flag, cert.terminal, gold, gold_intent,
                            note, anchor, executed, feas.ops, measures, v12=v12)
        out.append({"i": i, "verdicts": verdicts,
                    "flag": dict(measures, value=flag, present=note["flag_present"],
                                 raw=note["flag_raw"], missing=note["flag_missing"],
                                 type_error=note["flag_type_error"]),
                    "disposition": disp})
    return {"results": out, "golds": golds}


def _v12_inputs(row, feas10, cert10, feas11, gap11, rel2_11, executed11, frozen,
                baseline_full) -> dict:
    """The v1.2 base of one row: the v1.0.0 view of the proposal, priced.

    The base terminal is the G_FEAS verdict, the certificate price the G_CERT
    gap, the rule price the D-REL2 delta of the G_FEAS verdict and the
    executed objective that of the G_FEAS verdict.  Where the v1.1.0 base
    reached the price stage, the two views judge the same operations, so the
    v1.0.0 base must reach it too with the same objective and the same
    certified gap (a difference is a replay fault and stops the run), and the
    rule delta of the v1.1.0 base is reused.  Elsewhere the rule delta is
    computed from the G_FEAS verdict when that verdict reached a schedule.
    """
    reached = feas10.terminal == APPLIED_UNCERTIFIED
    gap10 = None if cert10.certificate is None else cert10.certificate.gap
    if feas11.terminal == APPLIED_UNCERTIFIED:
        rel2_10 = rel2_11
        executed10 = None if feas10.objective is None else feas10.objective["wwt_original_bh"]
        if not reached or executed10 != executed11 or gap10 != gap11:
            raise SystemExit(
                "v1.2 replay fault on {} {} r{}: the v1.0.0 view disagrees with the v1.1.0 "
                "base (terminal {}, objective {} vs {}, gap {} vs {})".format(
                    row["item_id"], row["mode"], row.get("repeat"), feas10.terminal,
                    executed10, executed11, gap10, gap11))
    elif reached:
        rel2_10 = rel2_price(feas10, frozen, baseline_full)
    else:
        rel2_10 = {"delta": None, "reference_from": "not_reached"}
    executed10 = None if feas10.objective is None else feas10.objective["wwt_original_bh"]
    return {"feas_terminal": feas10.terminal, "cert_terminal": cert10.terminal,
            "cert10": cert10, "gap": gap10, "rel2": rel2_10, "executed": executed10,
            "blocking_codes": sorted({f.code for f in feas10.findings if f.blocking})}


def _disposition(row, feas, gap, rel2, flag, live_cert_terminal, gold, gold_intent, note,
                 anchor, executed, ops, measures, v12=None) -> dict:
    """Every policy x tau_hard terminal, under the model flag and the true intent.

    The ``*_v12`` keys are the protocol v1.2 side: base terminal and prices
    from the v1.0.0 view of the proposal (``v12``, from :func:`_v12_inputs`;
    ``None`` for a model refusal), flag from the approver entry.
    """
    feas_terminal = MODEL_REFUSED if feas is None else feas.terminal
    rel2_delta = None if rel2 is None else rel2["delta"]
    truth_flag = True if gold_intent else None
    approver = approver_entry(gold_intent)
    feas_terminal_v12 = MODEL_REFUSED if v12 is None else v12["feas_terminal"]
    gap_v12 = None if v12 is None else v12["gap"]
    rel2_delta_v12 = None if v12 is None else v12["rel2"]["delta"]
    executed_v12 = None if v12 is None else v12["executed"]
    policies = {}
    for name, base_policy in POLICIES_V11.items():
        per_tau = {}
        for tau_hard in TAU_HARD_SWEEP_V11:
            policy = base_policy.with_(tau_hard=tau_hard)
            model = policy_terminal(policy, feas_terminal, flag, gap, rel2_delta)
            truth = policy_terminal(policy, feas_terminal, truth_flag, gap, rel2_delta)
            v12_side = policy_terminal(policy, feas_terminal_v12, approver, gap_v12,
                                       rel2_delta_v12)
            intended = intended_terminal(row["item_set"], gold["prices"][policy.price],
                                         policy.tau, tau_hard)
            applied_m = model["terminal"] in APPLIED_STATES_V11
            applied_t = truth["terminal"] in APPLIED_STATES_V11
            applied_v12 = v12_side["terminal"] in APPLIED_STATES_V11
            per_tau[tau_key(tau_hard)] = {
                "price": model["price"],
                "terminal_model_flag": model["terminal"],
                "terminal_true_intent": truth["terminal"],
                "intended": intended,
                "correct_model_flag": None if intended is None else model["terminal"] == intended,
                "correct_true_intent": None if intended is None else truth["terminal"] == intended,
                "executed_bh_model_flag": (executed if applied_m else anchor),
                "executed_bh_true_intent": (executed if applied_t else anchor),
                "price_v12": v12_side["price"],
                "terminal_v12": v12_side["terminal"],
                "correct_v12": None if intended is None else v12_side["terminal"] == intended,
                "executed_bh_v12": (executed_v12 if applied_v12 else anchor),
            }
        policies[name] = per_tau
    live_ok = None
    if feas is not None:
        live_ok = policies["P_CERT_V11"][tau_key(TAU_HARD_V11)]["terminal_model_flag"] == \
            live_cert_terminal
    live_ok_v12 = None
    if v12 is not None:
        live_ok_v12 = policies["P_CERT_V11"][tau_key(TAU_HARD_V11)]["terminal_v12"] == \
            live_terminal_v12(v12["cert10"], approver, POLICIES_V11["P_CERT_V11"].tau,
                              TAU_HARD_V11)
    gold_ops = row.get("gold_ops") or []
    return {
        "item_id": row["item_id"], "item_set": row["item_set"], "arm": row["arm"],
        "mode": row["mode"], "thinking": row.get("thinking"), "repeat": row.get("repeat"),
        "instance_id": row["instance_id"], "stratum": row["stratum"],
        "register": row.get("register"), "subclass": row["subclass"],
        "twin_id": row["twin_id"], "primary_class": row["primary_class"],
        "gold_intent": gold_intent,
        "flag_valid": measures["flag_valid"],
        "flag_raw": measures["flag_raw"],
        "flag_misplaced": measures["flag_misplaced"],
        "schema_valid_v11": measures["schema_valid"],
        "flag_value": flag,
        "flag_present": False if note is None else note["flag_present"],
        "flag_missing": False if note is None else note["flag_missing"],
        "false_acceptance": measures["flag_valid"] and not gold_intent,
        "missed_acceptance": gold_intent and not measures["flag_valid"],
        "feas_v11_terminal": feas_terminal,
        "cert_v11_terminal": live_cert_terminal,
        "live_cert_agrees": live_ok,
        "price_cert": gap, "price_rel2": rel2_delta,
        "rel2_reference_from": None if rel2 is None else rel2.get("reference_from"),
        "gold_prices": gold["prices"],
        "anchor_bh": anchor, "executed_if_applied_bh": executed,
        "ops": ops,
        "ops_match_gold": None if ops is None else sg.match_kind(ops, gold_ops),
        "policies": policies,
        "protocol_v12": PROTOCOL_V12,
        "approver_accepts_v12": approver,
        "feas_v12_terminal": feas_terminal_v12,
        "cert_v12_terminal": MODEL_REFUSED if v12 is None else v12["cert_terminal"],
        "feas_v12_blocking": [] if v12 is None else v12["blocking_codes"],
        "price_cert_v12": gap_v12, "price_rel2_v12": rel2_delta_v12,
        "executed_if_applied_bh_v12": executed_v12,
        "live_cert_agrees_v12": live_ok_v12,
    }


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def load_gold(rows: list) -> dict:
    gold = {}
    for row in rows:
        gold.setdefault(row["item_id"], {
            "gold_ops": row["gold_ops"], "item_set": row["item_set"],
            "gold_intent": bool((row.get("gold_intent") or {}).get(ops_mod.FLAG_FIELD))})
    return gold


def dedupe(raw_path: Path, out_dir: Path, allow_errors: bool) -> tuple:
    """The raw log with the runner's dedupe rule applied, written to ``out_dir``.

    The last row per (arm, mode, thinking, repeat, item_id) wins; an earlier
    row for a key is a superseded API error.  A key whose last row is still an
    API error means the generation run is incomplete, and the evaluation
    refuses unless ``--allow-errors`` is given (the error rows are then
    dropped and counted).
    """
    last: "OrderedDict[tuple, dict]" = OrderedDict()
    n_raw = 0
    with open(raw_path, "r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue  # a torn last line of a killed run
            n_raw += 1
            key = (row.get("arm"), row["mode"], row.get("thinking"), int(row["repeat"]),
                   row["item_id"])
            last.pop(key, None)
            last[key] = row
    errors = [k for k, r in last.items() if r.get("outcome") == "error"]
    if errors and not allow_errors:
        raise SystemExit("REFUSING TO RUN: {} keys end in an API error; re-run the generation "
                         "command to retry them, or pass --allow-errors".format(len(errors)))
    kept = [r for r in last.values() if r.get("outcome") != "error"]
    path = out_dir / "proposals_raw.dedup.jsonl"
    write_jsonl(path, kept)
    return path, {"raw_rows": n_raw, "keys": len(last), "kept": len(kept),
                  "unresolved_errors": len(errors)}


def write_jsonl(path: Path, records) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, sort_keys=True, separators=(",", ":"), default=str) + "\n")


def main() -> int:
    global _ROWS, _GOLD
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--allow-errors", action="store_true",
                    help="evaluate an incomplete log, dropping keys that end in an API error")
    args = ap.parse_args()

    raw_path = Path(args.raw).resolve()
    out_dir = Path(args.out)
    if out_dir.exists() and any(out_dir.iterdir()) and not args.force:
        raise SystemExit("REFUSING TO RUN: {} already has results (--force)".format(out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)

    inputs = sg.assert_inputs()
    ext_sha = sg.sha256_file(EXT_PATH)
    dedup_path, dedup = dedupe(raw_path, out_dir, args.allow_errors)
    print("[n3-eval] dedup: {}".format(json.dumps(dedup)))
    rows = e1.load_rows(dedup_path, None, args.limit)
    for row in rows:
        if row.get("prompt_version") != "l1-prompt-1.1.0":
            raise SystemExit("REFUSING TO RUN: row {} has prompt version {!r}".format(
                row["item_id"], row.get("prompt_version")))
        if row.get("item_set") not in ITEM_SETS:
            raise SystemExit("REFUSING TO RUN: row {} has no N3 item set".format(row["item_id"]))
    negated = any(row["item_set"] == "costly_negated" for row in rows)
    ext_neg_sha = sg.sha256_file(EXT_NEG_PATH) if negated else None
    metas = sorted(raw_path.parent.glob("run_meta_*.json"))
    if negated and not metas:
        raise SystemExit("REFUSING TO RUN: a costly_negated log needs its run meta")
    system_sha = hashlib.sha256(prompts.SYSTEM_PROMPT_V11.encode("utf-8")).hexdigest()
    schema_sha = ops_mod.verify_schema_v11()
    for meta_path in metas:
        meta = json.loads(meta_path.read_text())
        if meta.get("suite_ext_sha256") != ext_sha:
            raise SystemExit("REFUSING TO RUN: {} was generated from another extension "
                             "file".format(meta_path))
        if negated and meta.get("suite_ext_neg_sha256") != ext_neg_sha:
            raise SystemExit("REFUSING TO RUN: {} was generated from another negated "
                             "item file".format(meta_path))
        if meta.get("system_prompt_sha256") != system_sha or \
                meta.get("schema_v11_sha256") != schema_sha:
            raise SystemExit("REFUSING TO RUN: {} was generated under another v1.1.0 prompt "
                             "or schema text (a superseded protocol variant)".format(meta_path))
    _ROWS = rows
    _GOLD = load_gold(rows)
    cfgs = guard_configs()
    config_hashes = {name: cfg.config_hash for name, cfg in cfgs.items()}
    policy_hashes = {name: {tau_key(t): p.with_(tau_hard=t).config_hash
                            for t in TAU_HARD_SWEEP_V11}
                     for name, p in POLICIES_V11.items()}
    for name, h in config_hashes.items():
        print("[n3-eval] {:<11s} {}".format(name, h[:16]))

    chunks = e1.chunk_by_instance(rows)
    print("[n3-eval] {} rows, {} instances, {} workers".format(len(rows), len(chunks),
                                                                args.workers))
    started = time.perf_counter()
    results, golds = [], {}
    if args.workers > 1:
        ctx = mp.get_context("fork")
        with ctx.Pool(processes=args.workers, initializer=_init_worker) as pool:
            for k, payload in enumerate(pool.imap_unordered(_eval_chunk, chunks, chunksize=1), 1):
                results.extend(payload["results"])
                golds.update(payload["golds"])
                print("[n3-eval] chunk {}/{} rows {}/{}".format(k, len(chunks), len(results),
                                                                len(rows)), flush=True)
    else:
        _init_worker()
        for chunk in chunks:
            payload = _eval_chunk(chunk)
            results.extend(payload["results"])
            golds.update(payload["golds"])
    wall = time.perf_counter() - started
    if len(results) != len(rows):
        raise SystemExit("evaluated {} rows of {}".format(len(results), len(rows)))
    results.sort(key=lambda r: (rows[r["i"]]["mode"], str(rows[r["i"]].get("thinking")),
                                int(rows[r["i"]].get("repeat") or 0), rows[r["i"]]["item_id"]))

    disagree = [r["disposition"]["item_id"] for r in results
                if r["disposition"]["live_cert_agrees"] is False]
    disagree_v12 = [r["disposition"]["item_id"] for r in results
                    if r["disposition"]["live_cert_agrees_v12"] is False]
    for config in CONFIG_NAMES:
        recs = []
        for res in results:
            row = rows[res["i"]]
            v = res["verdicts"][config]
            recs.append(dict({
                "item_id": row["item_id"], "item_set": row["item_set"], "arm": row["arm"],
                "mode": row["mode"], "thinking": row.get("thinking"),
                "repeat": row.get("repeat"), "config": config,
                "config_hash": config_hashes[config], "instance_id": row["instance_id"],
                "primary_class": row["primary_class"], "subclass": row["subclass"],
                "twin_id": row["twin_id"], "twin_role": row["twin_role"],
                "quality_visible_candidate": row.get("quality_visible_candidate"),
                "stratum": row["stratum"], "flag": res["flag"]}, **v))
        write_jsonl(out_dir / "verdicts_{}.jsonl".format(config), recs)
    write_jsonl(out_dir / "dispositions.jsonl", (r["disposition"] for r in results))
    write_jsonl(out_dir / "gold_prices.jsonl", (golds[k] for k in sorted(golds)))

    terminals = {c: dict(Counter(r["verdicts"][c]["terminal"] for r in results))
                 for c in CONFIG_NAMES}
    meta = {
        "eval_version": EVAL_VERSION, "policy_version": POLICY_VERSION,
        "date": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "raw_path": str(raw_path), "raw_sha256": sg.sha256_file(raw_path),
        "dedup": dedup,
        "out_dir": str(out_dir.resolve()), "n_rows": len(rows), "limit": args.limit,
        "arms": sorted({r["arm"] for r in rows}), "modes": sorted({r["mode"] for r in rows}),
        "item_sets": dict(Counter(r["item_set"] for r in rows)),
        "suite_sha256": inputs["suite_sha256"], "schema_sha256": inputs["schema_sha256"],
        "schema_v11_sha256": ops_mod.verify_schema_v11(), "suite_ext_sha256": ext_sha,
        **({"suite_ext_neg_sha256": ext_neg_sha} if negated else {}),
        "instance_root": str(sg.INSTANCE_ROOT),
        "config_hashes": config_hashes, "policy_hashes": policy_hashes,
        "tau_hard_primary": TAU_HARD_V11, "tau_hard_sweep": [tau_key(t) for t in
                                                             TAU_HARD_SWEEP_V11],
        "terminals": terminals,
        "live_cert_disagreements": disagree,
        "protocol_v12": PROTOCOL_V12,
        "v12_base": "G_FEAS / G_CERT verdicts of the v1.0.0 view; flag = approver entry "
                    "(gold_intent)",
        "terminals_v12": dict(Counter(
            r["disposition"]["policies"]["P_CERT_V11"][tau_key(TAU_HARD_V11)]["terminal_v12"]
            for r in results)),
        "live_cert_disagreements_v12": disagree_v12,
        "workers": args.workers, "wall_s": wall,
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=1, sort_keys=True,
                                                      default=str))
    print("[n3-eval] {} rows in {:.1f}s; terminals {}".format(len(rows), wall,
                                                             json.dumps(terminals)))
    if disagree:
        print("[n3-eval] FAILED: the replayed certificate policy disagrees with the live "
              "G_CERT_V11 guard on {} rows: {}".format(len(disagree), disagree[:10]))
        return 4
    if disagree_v12:
        print("[n3-eval] FAILED: the v1.2 certificate replay disagrees with the G_CERT verdict "
              "disposed with the approver entry on {} rows: {}".format(len(disagree_v12),
                                                                       disagree_v12[:10]))
        return 5
    print("[n3-eval] written to {}".format(out_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
