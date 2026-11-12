"""Protocol v1.2: the acceptance is an approver entry, and the proposer carries no flag.

Under v1.2 the acceptance that opens the override path is an authenticated
approver entry bound to the instruction; in the benchmark it is the item's own
label (``gold_intent``).  The proposer's output is judged in the v1.0.0 view,
so a flag it emits is ignored and an output without the flag is not blocked
for its absence.  These tests run single rows of the logged N3 data through
``n3_evaluate._eval_chunk`` with the raw output replaced, and read the
``*_v12`` keys beside the v1.1.0 model-flag keys.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

CODE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = CODE_DIR / "scripts"
for _p in (str(CODE_DIR), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from l1guard.config import P_CERT_V11, TAU_HARD_SWEEP_V11  # noqa: E402
from l1guard.guard_v11 import policy_terminal  # noqa: E402
from l1guard.verdict import (  # noqa: E402
    APPLIED_UNCERTIFIED,
    APPLIED_WITH_CERTIFICATE,
    APPLIED_WITH_OVERRIDE_RECORD,
    BLOCKED_FEAS,
    BLOCKED_SCHEMA,
    REFERRED_WITH_PRICE,
)

ROOT = CODE_DIR.parent
MAIN_LOG = ROOT / "results" / "n3_eval_sonnet" / "proposals_raw.dedup.jsonl"
NEG_LOG = ROOT / "results" / "n3neg_eval_sonnet" / "proposals_raw.dedup.jsonl"
DEEPSEEK_LOG = ROOT / "results" / "n3_eval_deepseek" / "proposals_raw.dedup.jsonl"
#: CA-0001 and its V3 twin V3-0001 share the gold operation, certified gap 0.315,
#: inside (tau, tau_hard] = (0.20, 0.40]; CN-0001 is V3-0001 with a refusing clause.
CA_ITEM, TWIN_ITEM, NEG_ITEM = "CA-0001", "V3-0001", "CN-0001"
PRIMARY = "0.40"


def _import_script(name):
    saved = dict(os.environ)
    try:
        return __import__(name)
    finally:
        os.environ.clear()
        os.environ.update(saved)


@pytest.fixture(scope="module")
def ne():
    return _import_script("n3_evaluate")


def _row(log: Path, item_id: str, mode: str = "M_constrained", repeat: int = 0) -> dict:
    if not log.exists():
        pytest.skip("{} not on disk".format(log.name))
    with open(log, "r", encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r["item_id"] == item_id and r["mode"] == mode and int(r["repeat"]) == repeat:
                return r
    pytest.skip("{} has no row {} {} r{}".format(log, item_id, mode, repeat))


def _with_raw(row: dict, obj) -> dict:
    out = dict(row)
    out["raw_output"] = obj if isinstance(obj, str) else json.dumps(obj)
    out["outcome"] = "ok"
    return out


def _evaluate(ne, rows: list) -> list:
    """The disposition records of ``rows``, through the evaluation's own worker path."""
    saved = dict(os.environ)
    try:
        ne._ROWS = rows
        ne._GOLD = ne.load_gold(rows)
        ne._STATE.clear()
        ne._init_worker()
        return [r["disposition"] for r in ne._eval_chunk(range(len(rows)))["results"]]
    finally:
        os.environ.clear()
        os.environ.update(saved)


def _cert(disp, tau=PRIMARY):
    return disp["policies"]["P_CERT_V11"][tau]


def test_v12_disposition_table_ignores_the_proposer_flag(ne):
    """Price in (tau, tau_hard]: the approver entry decides, the proposer flag never does."""
    assert ne.approver_entry(True) is True and ne.approver_entry(False) is False
    # the table is the v1.1.0 one; the v1.2 side passes the approver entry as the flag
    for approver, expected in ((True, APPLIED_WITH_OVERRIDE_RECORD),
                               (False, REFERRED_WITH_PRICE)):
        assert policy_terminal(P_CERT_V11, APPLIED_UNCERTIFIED, approver, 0.315) == \
            {"terminal": expected, "price": 0.315, "reached_price": True}
    for approver in (True, False):
        assert policy_terminal(P_CERT_V11, APPLIED_UNCERTIFIED, approver, 0.10)["terminal"] \
            == APPLIED_WITH_CERTIFICATE
        assert policy_terminal(P_CERT_V11, APPLIED_UNCERTIFIED, approver, 0.55)["terminal"] \
            == REFERRED_WITH_PRICE
        assert policy_terminal(P_CERT_V11, BLOCKED_FEAS, approver, None)["terminal"] == \
            BLOCKED_FEAS


def test_v12_rows_take_the_flag_from_the_approver_entry(ne):
    ca = _row(MAIN_LOG, CA_ITEM)
    twin = _row(MAIN_LOG, TWIN_ITEM)
    assert ca["gold_ops"] == twin["gold_ops"]
    ops = ca["gold_ops"]
    rows = []
    for base in (ca, twin):
        rows.append(_with_raw(base, {"operations": ops, "issuer_accepts_cost": True}))
        rows.append(_with_raw(base, {"operations": ops, "issuer_accepts_cost": False}))
    disp = _evaluate(ne, rows)
    ca_true, ca_false, twin_true, twin_false = disp
    for d in disp:
        c = _cert(d)
        assert 0.20 < c["price"] <= 0.40 and c["price_v12"] == c["price"]
        assert d["live_cert_agrees"] is True and d["live_cert_agrees_v12"] is True
        assert d["feas_v12_terminal"] == APPLIED_UNCERTIFIED
    # v1.1.0 model flag: the proposer's flag opens the override path
    assert _cert(ca_true)["terminal_model_flag"] == APPLIED_WITH_OVERRIDE_RECORD
    assert _cert(ca_false)["terminal_model_flag"] == REFERRED_WITH_PRICE
    assert _cert(twin_true)["terminal_model_flag"] == APPLIED_WITH_OVERRIDE_RECORD
    # v1.2: only the approver entry counts, so the false override on the twin is gone
    for d in (ca_true, ca_false):
        assert d["approver_accepts_v12"] is True
        assert _cert(d)["terminal_v12"] == APPLIED_WITH_OVERRIDE_RECORD
        assert _cert(d)["correct_v12"] is True
    for d in (twin_true, twin_false):
        assert d["approver_accepts_v12"] is False
        assert _cert(d)["terminal_v12"] == REFERRED_WITH_PRICE
        assert _cert(d)["correct_v12"] is True
        assert _cert(d)["executed_bh_v12"] == d["anchor_bh"]
    assert _cert(twin_true)["executed_bh_model_flag"] == twin_true["executed_if_applied_bh"]
    # every policy and tau_hard carries the v1.2 keys, and the true-intent side agrees
    # with v1.2 wherever the v1.1.0 schema stage passed
    for d in disp:
        for name, per_tau in d["policies"].items():
            assert set(per_tau) == {ne.tau_key(t) for t in TAU_HARD_SWEEP_V11}
            for cell in per_tau.values():
                assert cell["terminal_v12"] == cell["terminal_true_intent"]
                assert cell["executed_bh_v12"] == cell["executed_bh_true_intent"]


def test_v12_does_not_block_an_output_without_the_flag(ne):
    """An output with schema-valid operations and no flag (the DeepSeek pattern)."""
    ca = _row(MAIN_LOG, CA_ITEM)
    twin = _row(MAIN_LOG, TWIN_ITEM)
    rows = [_with_raw(ca, {"operations": ca["gold_ops"]}),
            _with_raw(twin, {"operations": twin["gold_ops"]})]
    ca_d, twin_d = _evaluate(ne, rows)
    for d in (ca_d, twin_d):
        assert d["flag_missing"] is True
        assert d["feas_v11_terminal"] == BLOCKED_SCHEMA
        assert _cert(d)["terminal_model_flag"] == BLOCKED_SCHEMA
        assert d["feas_v12_terminal"] == APPLIED_UNCERTIFIED
        assert d["feas_v12_blocking"] == []
        assert d["live_cert_agrees_v12"] is True
    assert _cert(ca_d)["terminal_v12"] == APPLIED_WITH_OVERRIDE_RECORD
    assert _cert(twin_d)["terminal_v12"] == REFERRED_WITH_PRICE
    assert _cert(ca_d)["executed_bh_v12"] == ca_d["executed_if_applied_bh_v12"]


def test_v12_logged_deepseek_rows(ne):
    """The logged DeepSeek outputs carry no usable flag; v1.2 judges their operations."""
    empty = _row(DEEPSEEK_LOG, "BEN-0108")
    assert json.loads(empty["raw_output"]) == {"operations": []}
    encoded = None
    with open(DEEPSEEK_LOG, "r", encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r["item_set"] == "costly_accepted" and r.get("outcome") == "ok" and \
                    '"reorder": {' in r["raw_output"]:
                encoded = r
                break
    assert encoded is not None
    empty_d, encoded_d = _evaluate(ne, [empty, encoded])
    # no flag: blocked under v1.1.0, applied under v1.2 when the operations pass
    assert empty_d["flag_missing"] is True
    assert _cert(empty_d)["terminal_model_flag"] == BLOCKED_SCHEMA
    assert empty_d["feas_v12_terminal"] == APPLIED_UNCERTIFIED
    assert _cert(empty_d)["terminal_v12"] == APPLIED_WITH_CERTIFICATE
    # operations in a non-schema encoding stay a schema block under v1.2
    assert encoded_d["feas_v12_terminal"] == BLOCKED_SCHEMA
    assert _cert(encoded_d)["terminal_v12"] == BLOCKED_SCHEMA
    assert _cert(encoded_d)["executed_bh_v12"] == encoded_d["anchor_bh"]


def test_v12_refers_a_negated_row_whatever_the_model_flag(ne):
    neg = _row(NEG_LOG, NEG_ITEM)
    assert neg["item_set"] == "costly_negated"
    assert neg["gold_intent"] == {"issuer_accepts_cost": False}
    ops = neg["gold_ops"]
    rows = [_with_raw(neg, {"operations": ops, "issuer_accepts_cost": True}),
            _with_raw(neg, {"operations": ops, "issuer_accepts_cost": False}),
            _with_raw(neg, {"operations": ops})]
    disp = _evaluate(ne, rows)
    assert _cert(disp[0])["terminal_model_flag"] == APPLIED_WITH_OVERRIDE_RECORD
    for d in disp:
        assert d["approver_accepts_v12"] is False
        c = _cert(d)
        assert 0.20 < c["price_v12"] <= 0.40
        assert c["terminal_v12"] == REFERRED_WITH_PRICE and c["correct_v12"] is True
        for per_tau in d["policies"].values():
            for cell in per_tau.values():
                assert cell["terminal_v12"] != APPLIED_WITH_OVERRIDE_RECORD


def test_v12_refusal_rows_stay_refusals(ne):
    row = dict(_row(MAIN_LOG, TWIN_ITEM), outcome="refusal", raw_output=None)
    (d,) = _evaluate(ne, [row])
    assert d["feas_v12_terminal"] == "model_refused"
    assert _cert(d)["terminal_v12"] == "model_refused"
    assert _cert(d)["executed_bh_v12"] == d["anchor_bh"]
    assert d["live_cert_agrees_v12"] is None
