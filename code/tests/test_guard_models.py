"""Model adapters.  Every test runs against an injected transport: no network."""

from __future__ import annotations

import json

import pytest

from l1adapter.ops import SCHEMA as FROZEN_SCHEMA
from l1guard.logging import (
    OUTCOME_EMPTY_CONTENT,
    OUTCOME_ERROR,
    OUTCOME_OK,
    OUTCOME_REFUSAL,
)
from l1guard.models import (
    ANTHROPIC_VERSION,
    BACKENDS,
    ENF_JSON_OBJECT,
    ENF_JSON_SCHEMA,
    ENF_XGRAMMAR,
    M_CONSTRAINED,
    M_FREE,
    WIRE_ANTHROPIC,
    WIRE_OPENAI,
    ChatClient,
    assert_xgrammar_backend,
    available_modes,
    normalize_usage,
    normalize_usage_anthropic,
    output_config_payload,
    split_user,
    strict_schema_payload,
)


class FakeTransport:
    """Records every request and returns canned responses in order."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "body": json.loads(body.decode()) if body else None,
                "timeout": timeout,
            }
        )
        status, payload = self.responses[min(len(self.calls) - 1, len(self.responses) - 1)]
        return status, json.dumps(payload).encode()


def completion(text="{}", **kw):
    payload = {
        "model": "test-model",
        "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
    }
    payload.update(kw)
    return 200, payload


# --------------------------------------------------------------------------- #
# request building                                                             #
# --------------------------------------------------------------------------- #
def test_m_free_sends_no_enforcement_of_any_kind():
    client = ChatClient("vllm", transport=FakeTransport(completion()))
    body = client.build_request("sys", "user", M_FREE)
    assert "response_format" not in body
    assert "structured_outputs" not in body
    assert body["temperature"] == 0.0 and body["stream"] is False
    assert [m["role"] for m in body["messages"]] == ["system", "user"]


def test_the_local_server_gets_the_frozen_schema_in_the_structured_outputs_field():
    client = ChatClient("vllm", transport=FakeTransport(completion()))
    body = client.build_request("sys", "user", M_CONSTRAINED)
    assert body["structured_outputs"]["json"] == FROZEN_SCHEMA
    assert "guided_json" not in body  # the pre-0.11 name is gone in vLLM 0.27


def test_openai_gets_a_strict_json_schema_response_format():
    client = ChatClient("openai", api_key="k", transport=FakeTransport(completion()))
    body = client.build_request("sys", "user", M_CONSTRAINED)
    fmt = body["response_format"]
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["strict"] is True
    schema = fmt["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["operations"]
    assert len(schema["properties"]["operations"]["items"]["anyOf"]) == 7


def test_only_json_schema_metadata_is_dropped_in_transport():
    payload = strict_schema_payload()["json_schema"]["schema"]
    assert "$schema" not in payload and "$id" not in payload
    stripped = {k: v for k, v in FROZEN_SCHEMA.items() if k not in ("$schema", "$id")}
    assert payload == stripped


def test_deepseek_uses_json_object_mode_and_needs_the_word_json():
    client = ChatClient("deepseek", api_key="k", transport=FakeTransport(completion()))
    body = client.build_request("reply in json", "do it", M_CONSTRAINED)
    assert body["response_format"] == {"type": "json_object"}
    assert "structured_outputs" not in body
    with pytest.raises(ValueError, match="json"):
        client.build_request("reply structurally", "do it", M_CONSTRAINED)


def test_the_enforcement_kind_per_backend_is_recorded_for_the_roster_table():
    assert BACKENDS["vllm"].constrained == ENF_XGRAMMAR
    assert BACKENDS["openai"].constrained == ENF_JSON_SCHEMA
    assert BACKENDS["deepseek"].constrained == ENF_JSON_OBJECT
    assert available_modes("deepseek") == (M_FREE, M_CONSTRAINED)


def test_an_unknown_mode_or_backend_is_refused():
    client = ChatClient("vllm", transport=FakeTransport(completion()))
    with pytest.raises(ValueError):
        client.build_request("s", "u", "M_whatever")
    with pytest.raises(KeyError):
        ChatClient("gemini")


def test_seed_reasoning_and_extra_body_pass_through():
    client = ChatClient("openai", api_key="k", transport=FakeTransport(completion()))
    body = client.build_request(
        "s", "u", M_FREE, seed=7, max_tokens=64, temperature=0.7,
        reasoning="high", extra_body={"top_p": 0.9},
    )
    assert body["seed"] == 7
    assert body["temperature"] == 0.7 and body["reasoning_effort"] == "high"
    assert body["top_p"] == 0.9


def test_the_output_cap_uses_each_providers_own_field_name():
    openai = ChatClient("openai", api_key="k", transport=FakeTransport(completion()))
    local = ChatClient("vllm", transport=FakeTransport(completion()))
    # OpenAI renamed the cap for reasoning-capable models; the local server and
    # DeepSeek keep the original name.
    assert openai.build_request("s", "u", M_FREE, max_tokens=64)["max_completion_tokens"] == 64
    assert "max_tokens" not in openai.build_request("s", "u", M_FREE)
    assert local.build_request("s", "u", M_FREE, max_tokens=64)["max_tokens"] == 64


def test_a_backend_can_declare_a_parameter_the_endpoint_rejects():
    from dataclasses import replace as dc_replace

    from l1guard import models as models_mod

    picky = dc_replace(models_mod.BACKENDS["openai"], drop_params=("temperature",))
    client = ChatClient("openai", api_key="k", transport=FakeTransport(completion()))
    client.backend = picky
    assert "temperature" not in client.build_request("s", "u", M_FREE)


# --------------------------------------------------------------------------- #
# keys                                                                         #
# --------------------------------------------------------------------------- #
def test_the_key_comes_from_the_environment_and_never_from_code(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    client = ChatClient("openai", transport=FakeTransport(completion()))
    assert client.api_key() == "sk-from-env"


def test_a_missing_key_fails_before_any_call(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = ChatClient("openai", transport=FakeTransport(completion()))
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        client.api_key()


def test_the_local_server_needs_no_key(monkeypatch):
    monkeypatch.delenv("L1_VLLM_API_KEY", raising=False)
    client = ChatClient("vllm", transport=FakeTransport(completion()))
    assert client.api_key() is None


# --------------------------------------------------------------------------- #
# response parsing                                                             #
# --------------------------------------------------------------------------- #
def test_a_normal_completion_is_the_ok_outcome():
    client = ChatClient("vllm", transport=FakeTransport(completion('{"operations": []}')))
    resp = client.complete("s", "u")
    assert resp.outcome == OUTCOME_OK and resp.ok
    assert resp.text == '{"operations": []}'
    assert resp.finish_reason == "stop"
    assert resp.usage["prompt_tokens"] == 100
    assert resp.latency_ms >= 0.0


def test_an_empty_completion_is_its_own_outcome_class_not_a_schema_violation():
    client = ChatClient("deepseek", api_key="k", transport=FakeTransport(completion("")))
    resp = client.complete("reply in json", "u")
    assert resp.outcome == OUTCOME_EMPTY_CONTENT
    assert resp.text == ""


def test_a_null_content_is_also_empty_content():
    payload = {"choices": [{"message": {"content": None}, "finish_reason": "stop"}]}
    client = ChatClient("vllm", transport=FakeTransport((200, payload)))
    assert client.complete("s", "u").outcome == OUTCOME_EMPTY_CONTENT


def test_a_refusal_is_its_own_outcome_class():
    payload = {
        "choices": [{"message": {"content": None, "refusal": "I will not"},
                     "finish_reason": "stop"}]
    }
    client = ChatClient("openai", api_key="k", transport=FakeTransport((200, payload)))
    resp = client.complete("s", "u")
    assert resp.outcome == OUTCOME_REFUSAL and "I will not" in resp.error


def test_an_http_error_is_reported_not_raised():
    client = ChatClient(
        "openai",
        api_key="k",
        max_retries=0,
        transport=FakeTransport((400, {"error": {"message": "bad schema"}})),
    )
    resp = client.complete("s", "u")
    assert resp.outcome == OUTCOME_ERROR and "bad schema" in resp.error
    assert resp.status == 400


def test_a_response_without_choices_is_an_error():
    client = ChatClient("vllm", transport=FakeTransport((200, {"usage": {}})))
    assert client.complete("s", "u").outcome == OUTCOME_ERROR


def test_a_rate_limit_is_retried_then_succeeds():
    transport = FakeTransport(
        (429, {"error": {"message": "slow down"}}), completion('{"operations": []}')
    )
    client = ChatClient("vllm", transport=transport, retry_sleep_s=0.0)
    resp = client.complete("s", "u")
    assert resp.ok and len(transport.calls) == 2


def test_the_request_goes_to_the_chat_completions_endpoint_with_a_bearer_key():
    transport = FakeTransport(completion())
    client = ChatClient("openai", api_key="sk-test", transport=transport)
    client.complete("s", "u")
    call = transport.calls[0]
    assert call["url"] == "https://api.openai.com/v1/chat/completions"
    assert call["headers"]["Authorization"] == "Bearer sk-test"
    assert call["body"]["model"] == "gpt-5.4-mini-2026-03-17"


# --------------------------------------------------------------------------- #
# usage normalisation                                                          #
# --------------------------------------------------------------------------- #
def test_openai_style_usage_is_normalised():
    got = normalize_usage(
        {
            "prompt_tokens": 1000,
            "completion_tokens": 200,
            "completion_tokens_details": {"reasoning_tokens": 150},
            "prompt_tokens_details": {"cached_tokens": 900},
        }
    )
    assert got["reasoning_tokens"] == 150
    assert got["cache_hit_tokens"] == 900 and got["cache_miss_tokens"] == 100
    assert got["cache_hit"] is True


def test_deepseek_style_usage_is_normalised():
    got = normalize_usage(
        {
            "prompt_tokens": 1000,
            "completion_tokens": 200,
            "prompt_cache_hit_tokens": 0,
            "prompt_cache_miss_tokens": 1000,
            "completion_tokens_details": {"reasoning_tokens": 640},
        }
    )
    assert got["cache_hit_tokens"] == 0 and got["cache_miss_tokens"] == 1000
    assert got["cache_hit"] is False and got["reasoning_tokens"] == 640


def test_missing_usage_fields_stay_none():
    got = normalize_usage(None)
    assert set(got) == {
        "prompt_tokens", "completion_tokens", "total_tokens", "reasoning_tokens",
        "cache_hit_tokens", "cache_miss_tokens", "cache_hit",
    }
    assert all(v is None for v in got.values())


# --------------------------------------------------------------------------- #
# the Anthropic wire: POST /v1/messages, not /chat/completions                 #
# --------------------------------------------------------------------------- #
#: The two halves of a cache-split user message.  Their concatenation is what
#: every other arm sends as a single string, and the tests below assert that.
PREFIX = "Site state (json):\n{\"work_orders\": []}\n\nInstruction: "
TAIL = "raise the priority of order 7"


def anthropic_message(text='{"operations": []}', **kw):
    """One /v1/messages response, shaped as the pilot recorded it."""
    payload = {
        "id": "msg_01test",
        "type": "message",
        "role": "assistant",
        "model": "claude-sonnet-5",
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 22,
            "cache_read_input_tokens": 4736,
            "cache_creation_input_tokens": 0,
            "output_tokens": 118,
        },
    }
    payload.update(kw)
    return 200, payload


def anthropic_client(*responses, **kw):
    transport = FakeTransport(*(responses or (anthropic_message(),)))
    kw.setdefault("api_key", "sk-ant-test")
    return ChatClient("anthropic", transport=transport, **kw), transport


# -- the backend record ----------------------------------------------------- #
def test_one_anthropic_backend_serves_both_claude_models():
    be = BACKENDS["anthropic"]
    assert be.wire == WIRE_ANTHROPIC
    assert be.api_key_env == "ANTHROPIC_API_KEY"
    assert be.base_url_env == "L1_ANTHROPIC_BASE_URL"
    assert be.default_base_url == "https://api.anthropic.com"
    assert be.default_model == "claude-sonnet-5"
    assert be.constrained == ENF_JSON_SCHEMA
    assert be.key_required is True
    assert available_modes("anthropic") == (M_FREE, M_CONSTRAINED)
    # The second Claude model is a client argument, not a second backend.
    opus = ChatClient("anthropic", model="claude-opus-5", api_key="k")
    assert opus.model == "claude-opus-5"


def test_the_three_older_backends_keep_the_openai_wire():
    assert {BACKENDS[n].wire for n in ("vllm", "deepseek", "openai")} == {WIRE_OPENAI}


def test_the_anthropic_key_comes_from_the_environment_like_every_other(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-from-env")
    assert ChatClient("anthropic").api_key() == "sk-ant-from-env"
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        ChatClient("anthropic").api_key()


# -- request building ------------------------------------------------------- #
def test_the_anthropic_request_goes_to_v1_messages_with_an_api_key_header(monkeypatch):
    monkeypatch.delenv("L1_ANTHROPIC_BASE_URL", raising=False)
    client, transport = anthropic_client()
    client.complete("sys", "u")
    call = transport.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == "https://api.anthropic.com/v1/messages"
    assert call["headers"]["x-api-key"] == "sk-ant-test"
    assert call["headers"]["anthropic-version"] == ANTHROPIC_VERSION == "2023-06-01"
    assert call["headers"]["Content-Type"] == "application/json"
    assert "Authorization" not in call["headers"]  # not a bearer-token wire
    assert call["body"]["model"] == "claude-sonnet-5"


def test_a_base_url_that_already_carries_v1_is_not_doubled(monkeypatch):
    monkeypatch.setenv("L1_ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")
    client, transport = anthropic_client()
    client.complete("sys", "u")
    assert transport.calls[0]["url"] == "https://api.anthropic.com/v1/messages"


def test_the_anthropic_body_never_carries_temperature_seed_or_stream(monkeypatch):
    monkeypatch.delenv("L1_ANTHROPIC_BASE_URL", raising=False)
    client, transport = anthropic_client()
    # Even when the caller passes the OpenAI-wire arguments, so that one grid
    # runner can drive either wire: the 5-series rejects temperature outright.
    _, _, body = client.build_request_anthropic(
        "sys", "u", M_FREE, seed=7, temperature=0.7, reasoning="high"
    )
    for banned in ("temperature", "seed", "stream", "reasoning_effort"):
        assert banned not in body
    assert body["max_tokens"] == 2048  # the plain name, not max_completion_tokens
    assert client.build_request_anthropic("s", "u", max_tokens=64)[2]["max_tokens"] == 64
    client.complete("sys", "u", seed=7, temperature=0.7)
    for banned in ("temperature", "seed", "stream", "reasoning_effort"):
        assert banned not in transport.calls[0]["body"]


def test_the_system_prompt_travels_as_one_text_block():
    client, _ = anthropic_client()
    _, _, body = client.build_request_anthropic("you output json only", "u")
    assert body["system"] == [{"type": "text", "text": "you output json only"}]


def test_a_tuple_user_becomes_two_blocks_with_cache_control_on_the_prefix():
    client, _ = anthropic_client()
    _, _, body = client.build_request_anthropic("sys", (PREFIX, TAIL), M_FREE)
    message = body["messages"][0]
    assert message["role"] == "user"
    blocks = message["content"]
    assert [b["type"] for b in blocks] == ["text", "text"]
    assert blocks[0]["text"] == PREFIX and blocks[1]["text"] == TAIL
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in blocks[1]  # the varying tail is never cached


def test_a_plain_string_user_becomes_one_block_with_no_cache_control():
    client, _ = anthropic_client()
    _, _, body = client.build_request_anthropic("sys", PREFIX + TAIL, M_FREE)
    blocks = body["messages"][0]["content"]
    assert blocks == [{"type": "text", "text": PREFIX + TAIL}]


def test_a_user_message_that_is_neither_a_string_nor_a_pair_is_refused():
    with pytest.raises(TypeError, match="2-tuple"):
        split_user(("a", "b", "c"))


def test_anthropic_m_constrained_sends_the_stripped_schema_in_output_config():
    client, _ = anthropic_client()
    _, _, body = client.build_request_anthropic("sys", "u", M_CONSTRAINED)
    fmt = body["output_config"]["format"]
    assert fmt["type"] == "json_schema"
    schema = fmt["schema"]
    assert "$schema" not in schema and "$id" not in schema
    assert schema == {k: v for k, v in FROZEN_SCHEMA.items() if k not in ("$schema", "$id")}
    # No OpenAI envelope: the schema sits directly under format, unnamed.
    assert "response_format" not in body and "json_schema" not in body
    assert "strict" not in json.dumps(fmt)
    # The integer enum the provider probe accepted verbatim.
    op = schema["properties"]["operations"]["items"]["anyOf"][0]
    assert op["properties"]["priority_class"]["enum"] == [1, 2, 3, 4]


def test_anthropic_m_free_sends_no_enforcement_of_any_kind():
    client, _ = anthropic_client()
    _, _, body = client.build_request_anthropic("sys", "u", M_FREE)
    assert "output_config" not in body
    assert "response_format" not in body and "structured_outputs" not in body


def test_the_output_config_payload_strips_only_schema_metadata():
    schema = output_config_payload()["format"]["schema"]
    stripped = {k: v for k, v in FROZEN_SCHEMA.items() if k not in ("$schema", "$id")}
    assert schema == stripped


def test_thinking_is_a_pass_through_never_a_hardcoded_field():
    # Opus 5 emits a thinking block by default and Sonnet 5 does not, so the
    # client states nothing and the arm decides.
    plain, _ = anthropic_client()
    assert "thinking" not in plain.build_request_anthropic("sys", "u")[2]
    off, _ = anthropic_client(extra_body={"thinking": {"type": "disabled"}})
    assert off.build_request_anthropic("sys", "u")[2]["thinking"] == {"type": "disabled"}


def test_an_unknown_mode_is_refused_on_the_anthropic_wire_too():
    client, _ = anthropic_client()
    with pytest.raises(ValueError):
        client.build_request_anthropic("s", "u", "M_whatever")


# -- the same prompt on both wires ------------------------------------------ #
def test_a_tuple_user_is_one_joined_string_on_the_openai_wire():
    """The two wires must send the same prompt, byte for byte."""
    openai = ChatClient("openai", api_key="k", transport=FakeTransport(completion()))
    local = ChatClient("vllm", transport=FakeTransport(completion()))
    joined = openai.build_request("sys", (PREFIX, TAIL), M_FREE)["messages"][1]["content"]
    assert joined == PREFIX + TAIL
    assert local.build_request("sys", (PREFIX, TAIL), M_FREE)["messages"][1]["content"] == joined

    anthropic, _ = anthropic_client()
    blocks = anthropic.build_request_anthropic("sys", (PREFIX, TAIL), M_FREE)[2]
    blocks = blocks["messages"][0]["content"]
    assert "".join(b["text"] for b in blocks) == joined


def test_the_deepseek_json_word_check_reads_the_whole_joined_prompt():
    client = ChatClient("deepseek", api_key="k", transport=FakeTransport(completion()))
    body = client.build_request("do it", ("reply in json.\n", "order 7"), M_CONSTRAINED)
    assert body["response_format"] == {"type": "json_object"}
    with pytest.raises(ValueError, match="json"):
        client.build_request("do it", ("reply structurally.\n", "order 7"), M_CONSTRAINED)


# -- response parsing ------------------------------------------------------- #
def test_a_normal_anthropic_message_is_the_ok_outcome():
    client, _ = anthropic_client(anthropic_message('{"operations": []}'))
    resp = client.complete("sys", "u")
    assert resp.outcome == OUTCOME_OK and resp.ok
    assert resp.text == '{"operations": []}'
    assert resp.finish_reason == "end_turn"
    assert resp.model == "claude-sonnet-5"
    assert resp.status == 200 and resp.latency_ms >= 0.0
    usage = resp.usage
    assert usage["prompt_tokens"] == 22 + 4736  # uncached + cache read + cache write
    assert usage["cache_hit_tokens"] == 4736
    assert usage["cache_miss_tokens"] == 22
    assert usage["completion_tokens"] == 118
    assert usage["reasoning_tokens"] is None  # thinking bills inside output_tokens
    assert usage["cache_hit"] is True
    assert usage["cache_write_tokens"] == 0


def test_anthropic_usage_counts_a_cache_write_as_a_miss():
    got = normalize_usage_anthropic(
        {
            "input_tokens": 22,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 4736,
            "output_tokens": 118,
        }
    )
    assert got["prompt_tokens"] == 4758
    assert got["cache_hit_tokens"] == 0 and got["cache_miss_tokens"] == 4758
    assert got["cache_hit"] is False and got["cache_write_tokens"] == 4736


def test_a_missing_anthropic_usage_block_stays_none():
    got = normalize_usage_anthropic(None)
    assert set(got) == set(normalize_usage(None)) | {"cache_write_tokens"}
    assert all(v is None for v in got.values())


def test_the_answer_is_the_text_block_not_the_thinking_block():
    # Opus 5 emits a thinking block first by default; block zero is not the answer.
    _, payload = anthropic_message()
    payload["content"] = [
        {"type": "thinking", "thinking": "the site needs no change", "signature": "x"},
        {"type": "text", "text": '{"operations": []}'},
    ]
    client, _ = anthropic_client((200, payload))
    resp = client.complete("sys", "u")
    assert resp.ok and resp.text == '{"operations": []}'


def test_a_refusal_stop_reason_is_its_own_outcome_class():
    _, payload = anthropic_message(text="I will not")
    payload["stop_reason"] = "refusal"
    payload["stop_details"] = {"type": "refusal", "category": "cyber"}
    client, _ = anthropic_client((200, payload))
    resp = client.complete("sys", "u")
    assert resp.outcome == OUTCOME_REFUSAL
    assert resp.finish_reason == "refusal"
    assert "refusal" in resp.error and "cyber" in resp.error


def test_an_empty_anthropic_completion_is_its_own_outcome_class():
    _, payload = anthropic_message(text="   ")
    client, _ = anthropic_client((200, payload))
    assert client.complete("sys", "u").outcome == OUTCOME_EMPTY_CONTENT


def test_a_response_with_no_text_block_is_empty_content_not_an_error():
    # max_tokens reached inside a thinking block: nothing to validate, and
    # never a schema violation.
    _, payload = anthropic_message()
    payload["content"] = [{"type": "thinking", "thinking": "..."}]
    payload["stop_reason"] = "max_tokens"
    client, _ = anthropic_client((200, payload))
    resp = client.complete("sys", "u")
    assert resp.outcome == OUTCOME_EMPTY_CONTENT
    assert resp.text == "" and resp.finish_reason == "max_tokens"


def test_an_anthropic_http_error_is_reported_not_raised():
    payload = {
        "type": "error",
        "error": {"type": "invalid_request_error", "message": "temperature: unsupported"},
    }
    client, _ = anthropic_client((400, payload), max_retries=0)
    resp = client.complete("sys", "u")
    assert resp.outcome == OUTCOME_ERROR
    assert "temperature" in resp.error and resp.status == 400


def test_an_error_envelope_is_an_error_even_at_http_200():
    payload = {"type": "error", "error": {"type": "overloaded_error", "message": "busy"}}
    client, _ = anthropic_client((200, payload), max_retries=0)
    resp = client.complete("sys", "u")
    assert resp.outcome == OUTCOME_ERROR and "busy" in resp.error


def test_an_overloaded_529_is_retried_then_succeeds():
    overloaded = (529, {"type": "error", "error": {"message": "overloaded"}})
    client, transport = anthropic_client(overloaded, anthropic_message(), retry_sleep_s=0.0)
    resp = client.complete("sys", "u")
    assert resp.ok and len(transport.calls) == 2


def test_the_openai_wire_does_not_retry_a_529():
    # 529 is Anthropic's own status; adding it changed nothing for the others.
    transport = FakeTransport((529, {"error": {"message": "overloaded"}}), completion())
    client = ChatClient("openai", api_key="k", transport=transport, retry_sleep_s=0.0)
    resp = client.complete("s", "u")
    assert resp.outcome == OUTCOME_ERROR and len(transport.calls) == 1


# --------------------------------------------------------------------------- #
# the vLLM backend read-back                                                   #
# --------------------------------------------------------------------------- #
def _server_info(backend):
    return 200, {"vllm_config": {"structured_outputs_config": {"backend": backend}}}


def test_the_resolved_structured_outputs_backend_is_read_back():
    transport = FakeTransport(_server_info("xgrammar"))
    assert assert_xgrammar_backend("http://127.0.0.1:8000/v1", transport) == "xgrammar"
    assert transport.calls[0]["url"].endswith("/server_info?config_format=json")


def test_a_backend_that_is_not_xgrammar_stops_the_run():
    transport = FakeTransport(_server_info("guidance"))
    with pytest.raises(RuntimeError, match="xgrammar"):
        assert_xgrammar_backend("http://127.0.0.1:8000/v1", transport)


def test_the_default_auto_backend_is_refused():
    transport = FakeTransport(_server_info("auto"))
    with pytest.raises(RuntimeError):
        assert_xgrammar_backend("http://127.0.0.1:8000/v1", transport)


def test_a_server_without_the_dev_endpoint_says_what_to_do():
    transport = FakeTransport((404, {"detail": "Not Found"}))
    with pytest.raises(RuntimeError, match="VLLM_SERVER_DEV_MODE"):
        assert_xgrammar_backend("http://127.0.0.1:8000/v1", transport)


def test_a_text_format_config_is_refused_rather_than_guessed():
    transport = FakeTransport((200, {"vllm_config": "VllmConfig(model=...)"}))
    with pytest.raises(RuntimeError, match="config_format=json"):
        assert_xgrammar_backend("http://127.0.0.1:8000/v1", transport)
