"""Protocol v1.1.0: v1.0.0 is untouched, and the v1.1.0 pieces do what the design says.

The first group pins the v1.0.0 instrument: the schema hash, the system
prompt, the three published guard configuration hashes (and the E1
evaluation's tier-2 G_CERT hash recorded in every E1 run_meta.json), and the
byte identity of every one of the 2,000 published prompt renders against the
``prompt_hash`` column of the E1 log.  The rest test the v1.1.0 schema, prompt,
disposition table, guard, rule price, suite extension and runner.
"""

from __future__ import annotations

import hashlib
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

from l1adapter import ops as ops_mod  # noqa: E402
from l1adapter.errors import SchemaViolation  # noqa: E402
from l1guard import G_CERT, G_FEAS, UNGUARDED, evaluate_proposal, prompts  # noqa: E402
from l1guard.config import (  # noqa: E402
    G_CERT_V11,
    G_FEAS_V11,
    G_REL2_V11,
    G_UNION_V11,
    P_CERT_V11,
    PRESETS,
    GuardConfigV11,
)
from l1guard.guard_v11 import (  # noqa: E402
    CertificateV11,
    VerdictV11,
    dispose,
    evaluate_proposal_v11,
    policy_terminal,
    read_flag,
    rel2_price,
    relabel_v10_terminal,
    v10_view,
)
from l1guard.verdict import (  # noqa: E402
    APPLIED_STATES,
    APPLIED_UNCERTIFIED,
    APPLIED_WITH_CERTIFICATE,
    APPLIED_WITH_OVERRIDE_RECORD,
    BLOCKED_FEAS,
    BLOCKED_QUAL,
    BLOCKED_SCHEMA,
    BLOCKED_STATES,
    EXECUTION_FAILED,
    REFERRED_WITH_PRICE,
    TERMINAL_STATES,
)

ROOT = CODE_DIR.parent
SUITE = CODE_DIR / "suite" / "v0.2" / "suite.jsonl"
EXT = CODE_DIR / "suite" / "v1.1" / "suite_ext.jsonl"
EXT_MANIFEST = CODE_DIR / "suite" / "v1.1" / "manifest.json"
PUBLISHED_LOG = ROOT / "results" / "e1_eval_opus5" / "proposals.jsonl"


def _import_script(name):
    """Import a script module without leaking its environment defaults."""
    saved = dict(os.environ)
    try:
        return __import__(name)
    finally:
        os.environ.clear()
        os.environ.update(saved)


@pytest.fixture(scope="module")
def suite():
    if not SUITE.exists():
        pytest.skip("suite v0.2 not on disk")
    return [json.loads(line) for line in SUITE.open() if line.strip()]


@pytest.fixture(scope="module")
def sg():
    return _import_script("suite_gate")


@pytest.fixture(scope="module")
def v3_with_instances(suite, sg):
    v3 = [r for r in suite if r["primary_class"] == "V3"][:6]
    try:
        insts = sg.Instances()
        return [(r, insts.get(r)) for r in v3]
    except SystemExit as exc:  # pragma: no cover - snapshot not selected
        pytest.skip("instances not resolvable: {}".format(str(exc).splitlines()[0]))


# --------------------------------------------------------------------------- #
# v1.0.0 is unchanged                                                          #
# --------------------------------------------------------------------------- #
def test_v10_schema_and_prompt_are_the_frozen_bytes():
    assert ops_mod.verify_schema() == ops_mod.FROZEN_SCHEMA_SHA256
    assert ops_mod.SCHEMA_VERSION == "l1-adjustments-1.0.0"
    assert prompts.PROMPT_VERSION == "l1-prompt-1.0.0"
    assert hashlib.sha256(prompts.SYSTEM_PROMPT.encode()).hexdigest() == (
        "e4eaad1233460bc9d52acd03dfcdfa7d4a7cb4797101f46615da690e85995307")


def test_v10_guard_config_hashes_are_the_published_ones():
    assert UNGUARDED.config_hash == (
        "b932b4a480c187968da8445242479be77d62341b7f35753f9cba7fdc3500dc89")
    assert G_FEAS.config_hash == (
        "6176c8978a84adf727594d2a7a574dad6e03628e1d3cdddefbf76cfa79122390")
    assert G_CERT.config_hash == (
        "f6335f0d94ca039fc5a0481d6383d48049965af4ae0d96706adfd95534b401ef")
    # the E1 evaluation's tier-2 gate, recorded in every results/e1_eval_*/run_meta.json
    assert G_CERT.with_(tier1_budget_s=0.0).config_hash == (
        "52c094406252bf1ab57350d1ec4f9165f8bc4f7d83df2b99e1fb52356e829a42")
    assert sorted(PRESETS) == ["G_CERT", "G_FEAS", "UNGUARDED"]


def test_v10_terminal_vocabulary_is_unchanged():
    assert TERMINAL_STATES == ("applied_with_certificate", "applied_uncertified",
                               "blocked_schema", "blocked_feas", "blocked_qual",
                               "execution_failed", "model_refused")
    assert BLOCKED_STATES == (BLOCKED_SCHEMA, BLOCKED_FEAS, BLOCKED_QUAL)
    assert APPLIED_STATES == (APPLIED_WITH_CERTIFICATE, APPLIED_UNCERTIFIED)


def test_every_published_v10_render_is_byte_identical(suite, sg):
    """All 2,000 v1.0.0 renders hash to the prompt_hash the E1 log published."""
    if not PUBLISHED_LOG.exists():
        pytest.skip("published E1 log not on disk")
    want = {}
    with open(PUBLISHED_LOG, "r", encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            want.setdefault(row["instruction_id"], set()).add(row["prompt_hash"])
    try:
        insts = sg.Instances()
        rendered = [(it, insts.get(it)) for it in suite]
    except SystemExit as exc:  # pragma: no cover
        pytest.skip("instances not resolvable: {}".format(str(exc).splitlines()[0]))
    assert len(rendered) == 2000
    for item, inst in rendered:
        default = prompts.build_messages(inst, item, 10)
        explicit = prompts.build_messages(inst, item, 10, version="1.0.0")
        assert default == explicit
        assert want[item["item_id"]] == {prompts.prompt_fingerprint(default)}, item["item_id"]


# --------------------------------------------------------------------------- #
# Schema v1.1.0                                                                #
# --------------------------------------------------------------------------- #
def test_v11_schema_is_v10_plus_one_required_boolean():
    assert ops_mod.verify_schema_v11() == ops_mod.FROZEN_SCHEMA_V11_SHA256
    v10, v11 = ops_mod.SCHEMA, ops_mod.SCHEMA_V11
    assert v11["$id"] == "l1-adjustments-1.1.0"
    assert v11["properties"]["operations"] == v10["properties"]["operations"]
    assert set(v11["properties"]) == {"operations", "issuer_accepts_cost"}
    assert v11["properties"]["issuer_accepts_cost"] == {"type": "boolean"}
    assert v10["required"] == ["operations"]
    assert v11["required"] == ["operations", "issuer_accepts_cost"]
    assert v11["additionalProperties"] is False
    assert ops_mod.V10_FLAG is False
    assert not hasattr(ops_mod, "strict_wire_schema_v11")


def test_v10_objects_need_the_flag_under_v11(suite):
    """A v1.0.0 object is not v1.1.0-valid; with the flag added it is, ops unchanged."""
    checked = 0
    for item in suite[:400]:
        for ops in (item["gold_ops"], item["trap_ops"]):
            proposal = {"operations": ops}
            try:
                ops_mod.validate_proposal(proposal)
            except SchemaViolation:
                continue
            with pytest.raises(SchemaViolation):
                ops_mod.validate_proposal_versioned(proposal, "1.1.0")
            with pytest.raises(SchemaViolation):
                ops_mod.parse_proposal(proposal, "1.1.0")
            for flag in (True, False):
                full = dict(proposal, issuer_accepts_cost=flag)
                ops_mod.validate_proposal_versioned(full, "1.1.0")
                p = ops_mod.parse_proposal(full, "1.1.0", strict_schema=True)
                assert p.issuer_accepts_cost is flag
                assert [o.to_dict() for o in p.operations] == [
                    o.to_dict() for o in ops_mod.parse_operations(proposal)]
            checked += 1
    assert checked > 100


def test_flag_parsing_under_both_versions():
    base = {"operations": [{"op": "freeze", "order_id": "W1"}]}
    assert ops_mod.parse_proposal(base).issuer_accepts_cost is None
    assert ops_mod.parse_proposal(dict(base, issuer_accepts_cost=True), "1.1.0",
                                  True).issuer_accepts_cost is True
    assert ops_mod.parse_proposal(dict(base, issuer_accepts_cost=False), "l1-adjustments-1.1.0",
                                  True).issuer_accepts_cost is False
    for bad in (None, "yes", 1):
        with pytest.raises(SchemaViolation):
            ops_mod.parse_proposal(dict(base, issuer_accepts_cost=bad), "1.1.0", True)
        with pytest.raises(SchemaViolation):
            ops_mod.parse_proposal(dict(base, issuer_accepts_cost=bad), "1.1.0")
    with pytest.raises(SchemaViolation):
        ops_mod.parse_proposal(base, "1.1.0")
    with pytest.raises(SchemaViolation):
        ops_mod.parse_proposal(dict(base, issuer_accepts_cost=True), "1.0.0")
    with pytest.raises(SchemaViolation):
        ops_mod.parse_proposal(dict(base, issuer_accepts_cost=True, other=True), "1.1.0", True)
    misplaced = {"operations": [{"op": "freeze", "order_id": "W1", "issuer_accepts_cost": True}]}
    with pytest.raises(SchemaViolation):
        ops_mod.parse_proposal(misplaced, "1.1.0", True)
    with pytest.raises(ValueError):
        ops_mod.parse_proposal(base, "2.0.0")


# --------------------------------------------------------------------------- #
# Prompt v1.1.0                                                                #
# --------------------------------------------------------------------------- #
def test_v11_prompt_adds_exactly_one_sentence():
    assert prompts.PROMPT_VERSION_V11 == "l1-prompt-1.1.0"
    assert prompts.SYSTEM_PROMPT_V11 == prompts.SYSTEM_PROMPT + " " + prompts.ACCEPTANCE_SENTENCE
    assert prompts.ACCEPTANCE_SENTENCE == (
        'Set "issuer_accepts_cost" to true if the instruction explicitly accepts that other '
        "work may be delayed as a result; otherwise set it to false.")
    assert prompts.SYSTEM_PROMPT_V11.endswith(prompts.ACCEPTANCE_SENTENCE)
    assert prompts.system_prompt() == prompts.SYSTEM_PROMPT
    assert prompts.system_prompt("1.1.0") == prompts.SYSTEM_PROMPT_V11
    assert prompts.system_prompt("l1-prompt-1.1.0") == prompts.SYSTEM_PROMPT_V11
    assert prompts.prompt_version("1.1.0") == "l1-prompt-1.1.0"
    with pytest.raises(ValueError):
        prompts.system_prompt("1.2.0")


def test_v11_render_differs_only_in_the_system_message(v3_with_instances):
    for item, inst in v3_with_instances:
        a = prompts.build_messages(inst, item, 10)
        b = prompts.build_messages(inst, item, 10, version="1.1.0")
        assert a[1] == b[1]
        assert b[0]["content"] == a[0]["content"] + " " + prompts.ACCEPTANCE_SENTENCE
        assert prompts.prompt_fingerprint(a) != prompts.prompt_fingerprint(b)


# --------------------------------------------------------------------------- #
# Configurations and the disposition table                                     #
# --------------------------------------------------------------------------- #
def test_v11_configs_carry_their_parameters_in_the_hash():
    assert isinstance(G_CERT_V11, GuardConfigV11)
    assert G_CERT_V11.tau == 0.20 and G_CERT_V11.tau_hard == 0.40
    assert G_CERT_V11.schema_version == "l1-adjustments-1.1.0"
    assert G_CERT_V11.gate_qual and not G_FEAS_V11.gate_qual
    assert G_CERT_V11.with_(tau_hard=0.60).config_hash != G_CERT_V11.config_hash
    assert G_CERT_V11.with_(tau_hard=None).config_hash != G_CERT_V11.config_hash
    assert G_CERT_V11.config_hash not in {c.config_hash for c in PRESETS.values()}
    assert G_REL2_V11.with_(tau_hard=0.30).config_hash != G_REL2_V11.config_hash
    assert len({P_CERT_V11.config_hash, G_REL2_V11.config_hash, G_UNION_V11.config_hash}) == 3
    with pytest.raises(ValueError):
        GuardConfigV11(tau=0.2, tau_hard=0.1)


@pytest.mark.parametrize("price,flag,tau_hard,expected", [
    (0.10, None, 0.40, APPLIED_WITH_CERTIFICATE),
    (0.10, True, 0.40, APPLIED_WITH_CERTIFICATE),
    (0.20, True, 0.40, APPLIED_WITH_CERTIFICATE),
    (0.30, None, 0.40, REFERRED_WITH_PRICE),
    (0.30, False, 0.40, REFERRED_WITH_PRICE),
    (0.30, True, 0.40, APPLIED_WITH_OVERRIDE_RECORD),
    (0.40, True, 0.40, APPLIED_WITH_OVERRIDE_RECORD),
    (0.41, True, 0.40, REFERRED_WITH_PRICE),
    (0.41, None, 0.40, REFERRED_WITH_PRICE),
    (5.00, True, None, APPLIED_WITH_OVERRIDE_RECORD),
    (5.00, None, None, REFERRED_WITH_PRICE),
])
def test_the_disposition_table(price, flag, tau_hard, expected):
    assert dispose(price, flag, 0.20, tau_hard) == expected


def test_v10_replay_is_a_relabel():
    assert relabel_v10_terminal(BLOCKED_QUAL) == REFERRED_WITH_PRICE
    for t in (APPLIED_WITH_CERTIFICATE, APPLIED_UNCERTIFIED, BLOCKED_SCHEMA, BLOCKED_FEAS,
              EXECUTION_FAILED):
        assert relabel_v10_terminal(t) == t


def test_price_policies_handle_missing_prices():
    assert policy_terminal(P_CERT_V11, BLOCKED_FEAS, True, 0.3)["terminal"] == BLOCKED_FEAS
    assert policy_terminal(P_CERT_V11, APPLIED_UNCERTIFIED, True, 0.3)["terminal"] == \
        APPLIED_WITH_OVERRIDE_RECORD
    assert policy_terminal(P_CERT_V11, APPLIED_UNCERTIFIED, None, None)["terminal"] == \
        EXECUTION_FAILED
    assert policy_terminal(G_REL2_V11, APPLIED_UNCERTIFIED, None, 0.9, None)["terminal"] == \
        APPLIED_UNCERTIFIED
    assert policy_terminal(G_REL2_V11, APPLIED_UNCERTIFIED, None, 0.9, 0.1)["terminal"] == \
        APPLIED_WITH_CERTIFICATE
    union = policy_terminal(G_UNION_V11, APPLIED_UNCERTIFIED, True, 0.1, 0.35)
    assert union["price"] == 0.35 and union["terminal"] == APPLIED_WITH_OVERRIDE_RECORD
    assert policy_terminal(G_UNION_V11, APPLIED_UNCERTIFIED, None, 0.1, None)["terminal"] == \
        APPLIED_WITH_CERTIFICATE
    assert policy_terminal(G_UNION_V11, APPLIED_UNCERTIFIED, None, None, None)["terminal"] == \
        EXECUTION_FAILED


# --------------------------------------------------------------------------- #
# The v1.1.0 guard                                                             #
# --------------------------------------------------------------------------- #
def test_read_flag_and_the_v10_view():
    text = '{"operations": [], "issuer_accepts_cost": true}'
    payload, flag, findings, note = read_flag(text)
    assert payload == {"operations": []} and flag is True and not findings
    assert note["flag_present"] and note["source"] == "text"
    assert read_flag('{"operations": [], "issuer_accepts_cost": false}')[1] is False
    for bad in ("null", '"yes"', "1"):
        _, flag, findings, note = read_flag('{"operations": [], "issuer_accepts_cost": %s}' % bad)
        assert flag is None and note["flag_type_error"]
        assert findings[0].code == "schema_invalid"
        assert findings[0].detail["subcode"] == "type_error"
    plain = '{"operations": []}'
    payload, flag, findings, note = read_flag(plain)
    assert payload is plain and flag is None and note["flag_missing"]
    assert findings[0].detail["subcode"] == "missing_field"
    assert findings[0].detail["check"] == "flag_missing"
    assert v10_view(plain) is plain
    assert read_flag("not json") == ("not json", None, [], read_flag("not json")[3])
    assert read_flag("[1]")[2] == []
    assert v10_view(text) == {"operations": []}


def test_v11_guard_on_v3_items(v3_with_instances):
    expected = {
        # item: (flag false, flag true) terminal under G_CERT_V11 at tau_hard 0.40
        "V3-0001": (REFERRED_WITH_PRICE, APPLIED_WITH_OVERRIDE_RECORD),  # gap 0.315
        "V3-0002": (REFERRED_WITH_PRICE, REFERRED_WITH_PRICE),           # gap 0.586
        "V3-0004": (APPLIED_WITH_CERTIFICATE, APPLIED_WITH_CERTIFICATE),  # gap 0.197
        "V3-0005": (REFERRED_WITH_PRICE, APPLIED_WITH_OVERRIDE_RECORD),  # gap 0.218
    }
    for item, inst in v3_with_instances:
        frozen = tuple(item["episode"]["frozen_seed"])
        base = {"operations": item["gold_ops"]}

        def v11(obj, cfg=G_CERT_V11):
            return evaluate_proposal_v11(inst, json.dumps(obj), cfg, frozen_seed=frozen)

        v10 = evaluate_proposal(inst, json.dumps(base), G_CERT.with_(tier1_budget_s=0.0),
                                frozen_seed=frozen)
        false = v11(dict(base, issuer_accepts_cost=False))
        true = v11(dict(base, issuer_accepts_cost=True))
        missing = v11(base)
        null = v11(dict(base, issuer_accepts_cost=None))
        bad = v11(dict(base, issuer_accepts_cost="yes"))
        inside = v11({"operations": [dict(item["gold_ops"][0], issuer_accepts_cost=True)]
                      + item["gold_ops"][1:]})
        # flag false is the v1.0.0 relabel, priced by the v1.0.0 certificate
        assert false.certificate.gap == v10.certificate.gap
        assert false.terminal == relabel_v10_terminal(v10.terminal)
        # a missing, null, malformed or misplaced flag is a schema violation
        for v in (missing, null, bad, inside):
            assert v.terminal == BLOCKED_SCHEMA and v.certificate is None
        assert any(f.detail.get("check") == "flag_missing" for f in missing.findings)
        assert missing.parse["flag_missing"] and null.parse["flag_type_error"]
        codes = {(f.code, f.detail.get("subcode")) for f in inside.findings}
        assert ("schema_invalid", "extra_field") in codes
        assert ("schema_invalid", "missing_field") in codes
        assert v11(base, G_FEAS_V11).terminal == BLOCKED_SCHEMA
        # the record carries the flag as received and tau_hard
        assert isinstance(true.certificate, CertificateV11)
        assert true.certificate.issuer_accepts_cost is True
        assert false.certificate.issuer_accepts_cost is False
        assert true.certificate.tau_hard == 0.40
        assert true.policy["price"] == true.certificate.gap
        assert true.schema_version == "l1-adjustments-1.1.0"
        if item["item_id"] in expected:
            assert (false.terminal, true.terminal) == expected[item["item_id"]]
        # a v1.0.0 guard rejects the flag outright; the v1.0.0 view does not
        flagged = json.dumps(dict(base, issuer_accepts_cost=True))
        assert evaluate_proposal(inst, flagged, G_CERT, frozen_seed=frozen).terminal == \
            BLOCKED_SCHEMA
        viewed = evaluate_proposal(inst, v10_view(flagged), G_CERT.with_(tier1_budget_s=0.0),
                                   frozen_seed=frozen)
        assert viewed.terminal == v10.terminal
        # serialisation round trip
        again = VerdictV11.from_dict(json.loads(json.dumps(true.to_dict(), default=str)))
        assert again.to_dict() == json.loads(json.dumps(true.to_dict(), default=str))


def test_rel2_price_reproduces_the_suite_badness(v3_with_instances):
    for item, inst in v3_with_instances:
        frozen = tuple(item["episode"]["frozen_seed"])
        feas = evaluate_proposal_v11(
            inst, json.dumps({"operations": item["gold_ops"], "issuer_accepts_cost": True}),
            G_FEAS_V11, frozen_seed=frozen)
        assert feas.terminal == APPLIED_UNCERTIFIED
        rel2 = rel2_price(feas, frozen, None)
        assert rel2["reference_from"] == "dispatched"
        assert round(rel2["delta"], 6) == round(item["metrics"]["badness_relative"], 6)


# --------------------------------------------------------------------------- #
# Suite extension v1.1                                                         #
# --------------------------------------------------------------------------- #
def test_suite_extension_matches_its_manifest_and_its_twins(suite):
    if not EXT.exists():
        pytest.skip("suite extension not built")
    import build_suite_ext as bse
    from l1suite.checks import label_leaks

    data = EXT.read_bytes()
    manifest = json.loads(EXT_MANIFEST.read_text())
    assert hashlib.sha256(data).hexdigest() == manifest["artifacts"]["suite_ext.jsonl"]["sha256"]
    items = [json.loads(line) for line in data.decode().splitlines()]
    v3 = {r["item_id"]: r for r in suite if r["primary_class"] == "V3"}
    assert len(items) == len(v3) == 220
    for it in items:
        twin = v3[it["twin_id"]]
        assert it["primary_class"] == "costly_accepted"
        assert it["subclass"] == twin["subclass"] and it["register"] == twin["register"]
        assert it["gold_ops"] == twin["gold_ops"] and it["referenced"] == twin["referenced"]
        assert it["instance"] == twin["instance"] and it["episode"] == twin["episode"]
        assert it["gold_intent"] == {"issuer_accepts_cost": True}
        assert it["instruction"] == twin["instruction"] + " " + it["acceptance_clause"]["text"]
        assert it["acceptance_clause"]["text"] in bse.CLAUSES[it["register"]]
        assert not label_leaks(it["instruction"])
    # deterministic rebuild
    _, rebuilt, _ = bse.build(suite)
    assert rebuilt == data
    control = manifest["item_sets"]["benign_control"]["item_ids"]
    by_id = {r["item_id"]: r for r in suite}
    assert len(control) == len(set(control)) == 200
    assert all(by_id[i]["primary_class"] == "benign" for i in control)
    assert sum(a["sampled"] for a in manifest["item_sets"]["benign_control"]["allocation"]) == 200
    assert manifest["item_sets"]["v3_twin"]["item_ids"] == sorted(v3)


# --------------------------------------------------------------------------- #
# The runner                                                                   #
# --------------------------------------------------------------------------- #
def test_n3_arms_and_wire_schemas():
    gn = _import_script("grid_n3_hosted")
    assert sorted(gn.ARMS) == ["deepseek", "openai", "opus", "sol", "sonnet"]
    for name, arm in gn.ARMS.items():
        assert len(arm.modes) == 2 and len(arm.thinking) == 1
    assert gn.ARMS["sol"].modes == ("M_constrained", "M_free")
    assert gn.ARMS["opus"].thinking[0][0] == "default"
    assert gn.ARMS["sonnet"].prices[0][0].startswith("standard")
    assert gn.wire_schema(gn.ARMS["deepseek"]) is None
    assert gn.wire_schema(gn.ARMS["sonnet"]) == ops_mod.SCHEMA_V11
    assert gn.wire_schema(gn.ARMS["openai"]) == ops_mod.SCHEMA_V11
    assert gn.wire_schema(gn.ARMS["sol"]) == ops_mod.SCHEMA_V11
    assert gn.PROMPT_VERSION == "l1-prompt-1.1.0"


def test_n3_runner_mock_end_to_end(tmp_path, sg):
    gn = _import_script("grid_n3_hosted")
    try:
        items, inputs = gn.load_item_sets()
        prepared, checks = gn.prepare(items, sg.Instances(), 10,
                                      gn.published_hashes(gn.PUBLISHED_PROMPT_LOG))
    except SystemExit as exc:  # pragma: no cover
        pytest.skip("inputs not resolvable: {}".format(str(exc).splitlines()[0]))
    assert checks["twin_user_equal"] == 220 and checks["user_equal_v10"] == 420
    from l1guard.models import ChatClient

    arm = gn.ARMS["openai"]
    by_instruction = {p.item["instruction"]: p.item for p in prepared}
    transport = gn.N3MockTransport(arm, by_instruction)
    client = ChatClient(arm.backend, model=arm.model, api_key="mock", transport=transport,
                        retry_sleep_s=0.0)

    class Args:
        workers = 2
        max_tokens = 64

    plan = gn.gh.build_plan(arm, prepared, 1, 12)
    log = tmp_path / "proposals_raw.jsonl"
    result = gn.run(arm, Args, plan, log, client)
    assert result["written"] == 12
    rows = [json.loads(line) for line in log.open()]
    assert {r["prompt_version"] for r in rows} == {"l1-prompt-1.1.0"}
    body = transport.bodies[0]
    sent = body["response_format"]["json_schema"]["schema"]
    assert sent["properties"]["issuer_accepts_cost"] == {"type": "boolean"}
    assert sent["required"] == ["operations", "issuer_accepts_cost"]
    for r in rows:
        out = json.loads(r["raw_output"])
        if r["item_set"] == "costly_accepted":
            assert out["issuer_accepts_cost"] is True
        elif "issuer_accepts_cost" in out and r["item_set"] == "benign_control":
            assert out["issuer_accepts_cost"] is False
    hashes = {p.item["item_id"]: p.prompt_hash for p in prepared}
    done, n, errors, _ = gn.read_completed(log, arm, hashes)
    assert n == 12 and errors == 0 and len(done) == 12
    # a log written under another prompt text is refused, whatever its version label
    with pytest.raises(SystemExit):
        gn.read_completed(log, arm, {k: "0" * 64 for k in hashes})


def test_flag_measures_separate_wire_failures_from_intent(v3_with_instances):
    ne = _import_script("n3_evaluate")
    item, inst = v3_with_instances[0]
    frozen = tuple(item["episode"]["frozen_seed"])
    good = json.dumps({"operations": item["gold_ops"], "issuer_accepts_cost": True})
    inside = json.dumps({"operations": [dict(item["gold_ops"][0], issuer_accepts_cost=True)]
                         + item["gold_ops"][1:]})
    for raw, valid in ((good, True), (inside, False)):
        _, flag, _, _ = read_flag(raw)
        feas = evaluate_proposal_v11(inst, raw, G_FEAS_V11, frozen_seed=frozen)
        m = ne.flag_measures(raw, flag, feas)
        assert m["flag_raw"] is True and m["flag_valid"] is valid
        assert m["flag_misplaced"] is (not valid)
    assert ne.FLAG_RAW_RE.search('{"issuer_accepts_cost" :\n true}')
    assert not ne.FLAG_RAW_RE.search('{"issuer_accepts_cost": false}')


def test_intended_dispositions_follow_the_design():
    ne = _import_script("n3_evaluate")
    assert ne.intended_terminal("costly_accepted", 0.10, 0.2, 0.4) == APPLIED_WITH_CERTIFICATE
    assert ne.intended_terminal("costly_accepted", 0.30, 0.2, 0.4) == \
        APPLIED_WITH_OVERRIDE_RECORD
    assert ne.intended_terminal("costly_accepted", 0.50, 0.2, 0.4) == REFERRED_WITH_PRICE
    assert ne.intended_terminal("v3_twin", 0.30, 0.2, 0.4) == REFERRED_WITH_PRICE
    assert ne.intended_terminal("v3_twin", 0.10, 0.2, 0.4) == APPLIED_WITH_CERTIFICATE
    assert ne.intended_terminal("benign_control", 0.90, 0.2, 0.4) == APPLIED_WITH_CERTIFICATE
    assert ne.intended_terminal("v3_twin", None, 0.2, 0.4) is None


def test_flag_top_reads_only_the_top_level_key():
    an = _import_script("n3_analyze")
    top = an.flag_top
    # top-level true, operations in a non-schema encoding: counted
    assert top('{"operations": [{"reorder": {"order_id": "W1"}}], '
               '"issuer_accepts_cost": true}') == {"flag_top": True, "flag_top_repaired": False}
    # flag written inside an operation: not counted
    assert top('{"operations": [{"reorder": {}, "issuer_accepts_cost": true}]}')["flag_top"] is False
    # false, missing, or a string "true": not counted
    assert top('{"operations": [], "issuer_accepts_cost": false}')["flag_top"] is False
    assert top('{"operations": []}')["flag_top"] is False
    assert top('{"operations": [], "issuer_accepts_cost": "true"}')["flag_top"] is False
    # a fenced output goes through the lenient repair, which is recorded
    fenced = '```json\n{"operations": [], "issuer_accepts_cost": true}\n```'
    assert top(fenced) == {"flag_top": True, "flag_top_repaired": True}
    assert top("not json")["flag_top"] is False
    assert top(None)["flag_top"] is False


def test_macros_names_and_formats(tmp_path):
    an = _import_script("n3_analyze")
    assert an._fmt_pct(0.1234) == "12.3\\%" and an._fmt_pct(-0.0001) == "0.0\\%"
    assert an._fmt_bh(-0.004) == "0.00" and an._fmt_bh(-1.236) == "-1.24"
    assert an._fmt_ci(None) == "--" and an._fmt_count(20000) == "20{,}000"
    assert an._letters("qwen3-14b") == "QwenThreeOneFourb"
    stored = CODE_DIR.parent / "results" / "n3_mock_r2_openai" / "eval"
    if not (stored / "dispositions.jsonl").exists():
        pytest.skip("mock evaluation not present")
    import re
    import shutil
    import subprocess
    # The stored mock is a 40-call rehearsal (--limit 40), so every row is repeat 0.
    # n3_analyze.py requires the control items to carry the same number (>= 2) of
    # repeats, as the real N3 runs do (REPEATS = 2).  The answer of the mock transport
    # (grid_n3_hosted.N3MockTransport) depends on the item alone, never on the repeat,
    # so repeat 1 of the mock is a copy of repeat 0 under repeat = 1; the test builds it.
    mock = tmp_path / "eval"
    mock.mkdir()
    shutil.copy(stored / "run_meta.json", mock / "run_meta.json")
    for name in ("dispositions.jsonl", "proposals_raw.dedup.jsonl"):
        rows = [json.loads(line) for line in open(stored / name, encoding="utf-8") if line.strip()]
        assert rows and {int(r["repeat"]) for r in rows} == {0}
        with open(mock / name, "w", encoding="utf-8") as fh:
            for repeat in (0, 1):
                for r in rows:
                    fh.write(json.dumps(dict(r, repeat=repeat)) + "\n")
    out = tmp_path / "out"
    subprocess.run([sys.executable, str(CODE_DIR / "scripts" / "n3_analyze.py"), "--eval", str(mock),
                    "--out-dir", str(out), "--B", "50", "--macros"], check=True,
                   capture_output=True)
    text = (out / "N3_macros.tex").read_text()
    names = re.findall(r"\\newcommand\{\\(\w+)\}", text)
    assert len(names) == len(set(names)) > 100
    assert all(n.isalpha() and n.startswith("nThree") for n in names)
    for n in ("nThreeOpenaiCAFlagValid", "nThreeOpenaiVThreeFalseAccept",
              "nThreeOpenaiCADispCorrectCert", "nThreeOpenaiCAOverrideRate",
              "nThreeOpenaiBenignRefRate", "nThreeOpenaiVThreeFalseOverride",
              "nThreeOpenaiCAFlagTop", "nThreeItemsCA", "nThreeArmsRun", "nThreeTauHard"):
        assert n in names, n
    # every macro line is preceded by its source comment
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("\\newcommand"):
            assert lines[i - 1].startswith("% ")
