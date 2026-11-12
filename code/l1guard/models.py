"""Model adapters: one chat client for every arm, over two request wires.

There is a single client.  A *backend* is a small record of where the endpoint
lives, which environment variable holds its key, what its output-enforcement
mode looks like on the wire, and which wire format it speaks: ``openai`` (the
OpenAI-compatible ``/chat/completions`` shape) or ``anthropic`` (the native
``/v1/messages`` shape).  Adding a model is adding a backend record, never a
second client, which is what keeps the enforcement-mode axis comparable across
arms.

Backends
--------
``vllm``
    The local server (``vllm serve``).  M-constrained sends the frozen schema in
    vLLM 0.27's ``structured_outputs`` request field; the pre-0.11
    ``guided_json`` / ``GuidedDecodingParams`` names no longer exist.  The
    decoding backend must be **pinned and read back**: vLLM's default is
    ``auto``, which is free to pick another backend per request, and an arm
    whose grammar engine changes mid-run is a confound.  Launch the server with

        VLLM_USE_FLASHINFER_SAMPLER=0 VLLM_SERVER_DEV_MODE=1 \\
        vllm serve <model> --structured-outputs-config '{"backend": "xgrammar"}'

    and call :func:`assert_xgrammar_backend` once at run start; it reads
    ``/server_info`` and refuses to proceed unless the engine resolved
    ``xgrammar``.  One more launch flag matters for a thinking model: Qwen3
    generations run in thinking mode by default, and structured outputs are
    disabled inside reasoning content unless the server is started with
    ``--structured-outputs-config.enable_in_reasoning=True`` alongside
    ``--reasoning-parser qwen3``.
``deepseek``
    ``deepseek-v4-pro``.  No enforced-schema mode: the only structured mode is
    JSON-object, which requires the literal word "json" in the prompt (the
    client refuses to build a request that omits it).  Its documented
    empty-content response is its own outcome class, ``empty_content``, and is
    never counted as a schema violation.
``openai``
    ``gpt-5.4-mini-2026-03-17``.  M-constrained uses strict structured outputs:
    ``response_format = {"type": "json_schema", "json_schema": {"strict": true,
    "schema": <the frozen schema>}}``.  Only JSON Schema metadata keys
    (``$schema``, ``$id``) are dropped in transport; the structure, the closed
    enums and ``additionalProperties: false`` are sent exactly as frozen, and
    :func:`strict_schema_payload` is what the provider probe should be run on.
``anthropic``
    ``claude-sonnet-5`` and ``claude-opus-5``, one backend for both (the model
    id is per-client).  Its wire is not OpenAI-compatible: the request goes to
    ``POST /v1/messages`` with an ``x-api-key`` header instead of a bearer
    token, and M-constrained sends the frozen schema in ``output_config =
    {"format": {"type": "json_schema", "schema": <the frozen schema>}}`` rather
    than the OpenAI ``json_schema``/``strict`` envelope.  Three request fields
    the other backends send are never sent here: ``temperature`` (the 5-series
    rejects it, confirmed by a live probe), ``seed`` and ``stream``.  Thinking
    is not hardcoded either, because the two models differ (Opus 5 returns a
    thinking block by default, Sonnet 5 does not); pass
    ``extra_body={"thinking": {"type": "disabled"}}`` when an arm wants it off.
    The user message travels as two text blocks so the shared prefix can carry
    ``cache_control``; the concatenation is byte-identical to the single string
    the other backends send.

No key is ever written in code: every backend names an environment variable, and
the client raises if it is unset.  Nothing here retries forever, logs a key, or
prints a prompt.

Testing
-------
The transport is injectable.  ``ChatClient(..., transport=fake)`` replaces the
HTTP call with any callable ``(method, url, headers, body, timeout) ->
(status, bytes)``, so every test in this repository runs with no network.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from l1adapter.ops import SCHEMA as FROZEN_SCHEMA

from .logging import (
    OUTCOME_EMPTY_CONTENT,
    OUTCOME_ERROR,
    OUTCOME_OK,
    OUTCOME_REFUSAL,
)

M_FREE = "M_free"
M_CONSTRAINED = "M_constrained"
MODES = (M_FREE, M_CONSTRAINED)

#: Enforcement kinds, one per wire format.
ENF_NONE = "none"
ENF_JSON_OBJECT = "json_object"  # "reply with a JSON object", no schema
ENF_JSON_SCHEMA = "json_schema"  # provider-side strict schema
ENF_XGRAMMAR = "xgrammar"  # local grammar-constrained decoding

#: Request wires.  Two endpoints shapes, one client.
WIRE_OPENAI = "openai"  # POST {base}/chat/completions, Authorization: Bearer
WIRE_ANTHROPIC = "anthropic"  # POST {base}/v1/messages, x-api-key

#: The Anthropic API version header.  Required on every request to that wire.
ANTHROPIC_VERSION = "2023-06-01"

#: HTTP statuses worth a retry.  Anthropic adds 529 ("overloaded"), which the
#: OpenAI-compatible endpoints never return; keeping the sets separate means
#: adding it changed nothing for the three older backends.
RETRY_STATUS = (429, 500, 502, 503, 504)
RETRY_STATUS_ANTHROPIC = RETRY_STATUS + (529,)


@dataclass(frozen=True)
class Backend:
    """Where an endpoint lives and what its enforcement mode looks like on the wire.

    ``wire`` selects the request/response shape: ``openai`` for the
    ``/chat/completions`` family, ``anthropic`` for the native
    ``/v1/messages`` endpoint.  ``max_tokens_field`` carries the one
    request-shape difference *within* the OpenAI wire: OpenAI renamed
    ``max_tokens`` to ``max_completion_tokens`` for reasoning-capable models,
    and ``gpt-5.4-mini`` is one.  ``drop_params`` is the recorded answer to
    "which standard field does this endpoint reject?"; it is empty for every
    backend until a live probe says otherwise, and it exists so that answer is
    a configuration line rather than an edit.
    """

    name: str
    api_key_env: str
    base_url_env: str
    default_base_url: str | None = None
    default_model: str | None = None
    constrained: str = ENF_NONE  # what M_constrained means for this backend
    free_enforcement: str = ENF_NONE  # what M_free sends (nothing, by design)
    requires_json_word: bool = False
    key_required: bool = True
    max_tokens_field: str = "max_tokens"
    drop_params: tuple = ()
    wire: str = WIRE_OPENAI


BACKENDS: dict[str, Backend] = {
    "vllm": Backend(
        name="vllm",
        api_key_env="L1_VLLM_API_KEY",
        base_url_env="L1_VLLM_BASE_URL",
        default_base_url="http://127.0.0.1:8000/v1",
        default_model="Qwen/Qwen3-14B",
        constrained=ENF_XGRAMMAR,
        key_required=False,  # a local server usually runs without a key
    ),
    "deepseek": Backend(
        name="deepseek",
        api_key_env="DEEPSEEK_API_KEY",
        base_url_env="L1_DEEPSEEK_BASE_URL",
        default_base_url="https://api.deepseek.com/v1",
        default_model="deepseek-v4-pro",
        constrained=ENF_JSON_OBJECT,
        requires_json_word=True,
    ),
    "openai": Backend(
        name="openai",
        api_key_env="OPENAI_API_KEY",
        base_url_env="L1_OPENAI_BASE_URL",
        default_base_url="https://api.openai.com/v1",
        default_model="gpt-5.4-mini-2026-03-17",
        constrained=ENF_JSON_SCHEMA,
        max_tokens_field="max_completion_tokens",
    ),
    "anthropic": Backend(
        name="anthropic",
        api_key_env="ANTHROPIC_API_KEY",
        base_url_env="L1_ANTHROPIC_BASE_URL",
        default_base_url="https://api.anthropic.com",
        default_model="claude-sonnet-5",  # per-client; claude-opus-5 shares it
        constrained=ENF_JSON_SCHEMA,
        key_required=True,
        wire=WIRE_ANTHROPIC,
    ),
}

#: Metadata keys stripped when the frozen schema travels in a request body.
#: They carry no structural meaning; every constraint is preserved.
_SCHEMA_METADATA_KEYS = ("$schema", "$id")


def strict_schema_payload(schema: dict | None = None, name: str = "l1_adjustments") -> dict:
    """The ``response_format`` payload for provider-side strict structured outputs."""
    schema = dict(FROZEN_SCHEMA if schema is None else schema)
    for key in _SCHEMA_METADATA_KEYS:
        schema.pop(key, None)
    return {
        "type": "json_schema",
        "json_schema": {"name": name, "strict": True, "schema": schema},
    }


def xgrammar_payload(schema: dict | None = None) -> dict:
    """The vLLM 0.27 ``structured_outputs`` request field for a JSON schema."""
    schema = dict(FROZEN_SCHEMA if schema is None else schema)
    return {"structured_outputs": {"json": schema}}


def output_config_payload(schema: dict | None = None) -> dict:
    """The Anthropic ``output_config`` value for provider-side strict outputs.

    Same schema, same stripping rule as :func:`strict_schema_payload`, and a
    different envelope: this wire takes the schema directly under
    ``format``, with no ``json_schema``/``strict`` wrapper and no name.
    """
    schema = dict(FROZEN_SCHEMA if schema is None else schema)
    for key in _SCHEMA_METADATA_KEYS:
        schema.pop(key, None)
    return {"format": {"type": "json_schema", "schema": schema}}


# --------------------------------------------------------------------------- #
# The user message: one string, or a (stable prefix, varying tail) pair         #
# --------------------------------------------------------------------------- #
def split_user(user) -> tuple:
    """Normalise a user message into ``(stable_prefix, tail)``.

    A plain string has no stable prefix and comes back as ``(None, user)``.  A
    2-tuple names the cache boundary: everything shared across the calls of a
    block goes in the prefix, the part that varies per call in the tail.
    """
    if isinstance(user, str):
        return None, user
    if isinstance(user, (tuple, list)) and len(user) == 2:
        return user[0], user[1]
    raise TypeError(
        "user must be a string or a (stable_prefix, tail) 2-tuple, got {!r}".format(
            type(user).__name__
        )
    )


def join_user(user) -> str:
    """The single-string form of a user message, prefix and tail concatenated.

    This is what every OpenAI-wire backend sends, and it is byte-identical to
    the concatenation of the Anthropic wire's two text blocks, so the prompt
    hash is the same across arms whichever form the caller passes.
    """
    prefix, tail = split_user(user)
    return tail if prefix is None else "{}{}".format(prefix, tail)


def user_content_blocks(user) -> list:
    """The Anthropic ``messages[0].content`` blocks for a user message.

    A 2-tuple becomes two text blocks, the first carrying ``cache_control`` so
    the shared prefix is written once and read back on every later call.  A
    plain string becomes one block with no ``cache_control``: there is no
    boundary to cache at, and marking the whole varying message would write a
    fresh cache entry per call for nothing.
    """
    prefix, tail = split_user(user)
    if prefix is None:
        return [{"type": "text", "text": tail}]
    return [
        {"type": "text", "text": prefix, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": tail},
    ]


# --------------------------------------------------------------------------- #
# Transport                                                                    #
# --------------------------------------------------------------------------- #
def urllib_transport(method: str, url: str, headers: dict, body: bytes | None, timeout: float):
    """Default transport: the standard library, so the client has no dependency."""
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except urllib.error.URLError as exc:
        raise ConnectionError("{} {}: {}".format(method, url, exc)) from exc


@dataclass
class ChatResponse:
    """One model call, normalised across providers."""

    text: str | None
    outcome: str
    model: str
    latency_ms: float
    finish_reason: str | None = None
    usage: dict = field(default_factory=dict)
    error: str | None = None
    status: int | None = None
    raw: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.outcome == OUTCOME_OK


def normalize_usage(usage: dict | None) -> dict:
    """One usage shape for every provider (missing fields stay ``None``)."""
    usage = usage or {}
    comp_details = usage.get("completion_tokens_details") or {}
    prompt_details = usage.get("prompt_tokens_details") or {}
    hit = usage.get("prompt_cache_hit_tokens")
    if hit is None:
        hit = prompt_details.get("cached_tokens")
    miss = usage.get("prompt_cache_miss_tokens")
    if miss is None and hit is not None and usage.get("prompt_tokens") is not None:
        miss = int(usage["prompt_tokens"]) - int(hit)
    return {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "reasoning_tokens": comp_details.get("reasoning_tokens"),
        "cache_hit_tokens": hit,
        "cache_miss_tokens": miss,
        "cache_hit": None if hit is None else bool(hit),
    }


def normalize_usage_anthropic(usage: dict | None) -> dict:
    """The same usage shape, from Anthropic's four token counters.

    ``input_tokens`` there means *uncached* input only, so the prompt total is
    the sum of the three input counters.  Thinking bills inside
    ``output_tokens`` and is not reported separately, so ``reasoning_tokens``
    stays ``None`` rather than being guessed at.  One key is added to the
    common shape, ``cache_write_tokens``, because a cache write costs more
    than a plain input token and the cost table needs it.
    """
    if not usage:
        return dict(normalize_usage(None), cache_write_tokens=None)
    cache_read = usage.get("cache_read_input_tokens") or 0
    cache_write = usage.get("cache_creation_input_tokens") or 0
    uncached = usage.get("input_tokens") or 0
    return {
        "prompt_tokens": uncached + cache_read + cache_write,
        "completion_tokens": usage.get("output_tokens"),
        "total_tokens": None,
        "reasoning_tokens": None,
        "cache_hit_tokens": cache_read,
        "cache_miss_tokens": uncached + cache_write,
        "cache_hit": bool(cache_read),
        "cache_write_tokens": cache_write,
    }


class ChatClient:
    """One chat client, two request wires, and a pluggable transport.

    ``complete`` routes on ``self.backend.wire``; everything else about a call
    (retries, key handling, outcome classes, usage shape) is shared, which is
    what lets the same grid runner drive a local vLLM server and a Claude
    model without a second code path.
    """

    def __init__(
        self,
        backend: str = "vllm",
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_s: float = 180.0,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        transport=None,
        max_retries: int = 2,
        retry_sleep_s: float = 2.0,
        extra_body: dict | None = None,
    ):
        if backend not in BACKENDS:
            raise KeyError(
                "unknown backend {!r}; available: {}".format(backend, sorted(BACKENDS))
            )
        self.backend = BACKENDS[backend]
        self.model = model or self.backend.default_model
        self.base_url = (
            base_url
            or os.environ.get(self.backend.base_url_env)
            or self.backend.default_base_url
        ).rstrip("/")
        self._api_key = api_key
        self.timeout_s = float(timeout_s)
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)
        self.transport = transport or urllib_transport
        self.max_retries = int(max_retries)
        self.retry_sleep_s = float(retry_sleep_s)
        self.extra_body = dict(extra_body or {})

    # -- key handling -------------------------------------------------------- #
    def api_key(self) -> str | None:
        if self._api_key is not None:
            return self._api_key
        key = os.environ.get(self.backend.api_key_env)
        if not key and self.backend.key_required:
            raise RuntimeError(
                "environment variable {} is not set; no key is ever stored in "
                "code".format(self.backend.api_key_env)
            )
        return key

    # -- request building (pure, and therefore testable) --------------------- #
    def build_request(
        self,
        system: str,
        user,
        mode: str = M_FREE,
        schema: dict | None = None,
        seed: int | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        reasoning: str | None = None,
        extra_body: dict | None = None,
    ) -> dict:
        """The OpenAI-wire request body.

        ``user`` is a string, or a ``(stable_prefix, tail)`` pair naming a
        cache boundary.  These endpoints cache prefixes automatically, so the
        pair is simply concatenated: the prompt they see is the same string
        either way.
        """
        if mode not in MODES:
            raise ValueError("mode must be one of {}, got {!r}".format(list(MODES), mode))
        user = join_user(user)
        body: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature if temperature is None else float(temperature),
            self.backend.max_tokens_field: (
                self.max_tokens if max_tokens is None else int(max_tokens)
            ),
            "stream": False,
        }
        if seed is not None:
            body["seed"] = int(seed)

        enforcement = ENF_NONE
        if mode == M_CONSTRAINED:
            enforcement = self.backend.constrained
            if enforcement == ENF_NONE:
                raise ValueError(
                    "backend {!r} has no constrained mode; run it in M_free and say "
                    "so in the roster table".format(self.backend.name)
                )
            if enforcement == ENF_JSON_SCHEMA:
                body["response_format"] = strict_schema_payload(schema)
            elif enforcement == ENF_XGRAMMAR:
                body.update(xgrammar_payload(schema))
            elif enforcement == ENF_JSON_OBJECT:
                body["response_format"] = {"type": "json_object"}

        if enforcement == ENF_JSON_OBJECT or (
            self.backend.requires_json_word and body.get("response_format")
        ):
            blob = "{} {}".format(system or "", user or "").lower()
            if "json" not in blob:
                raise ValueError(
                    "{} JSON-object mode requires the word 'json' in the prompt; the "
                    "provider returns an empty completion otherwise".format(
                        self.backend.name
                    )
                )
        if reasoning is not None:
            body["reasoning_effort"] = reasoning
        body.update(self.extra_body)
        body.update(extra_body or {})
        for field_name in self.backend.drop_params:
            body.pop(field_name, None)
        return body

    def build_request_anthropic(
        self,
        system: str,
        user,
        mode: str = M_FREE,
        schema: dict | None = None,
        seed: int | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        reasoning: str | None = None,
        extra_body: dict | None = None,
    ) -> tuple:
        """The native ``/v1/messages`` request, as ``(path, headers, body)``.

        The signature matches :meth:`build_request` so one runner can drive
        either wire, but three of its arguments are deliberately dropped
        rather than translated: ``temperature`` (the 5-series rejects it, and
        the pilot confirmed the rejection on the wire), ``seed`` and
        ``reasoning`` (no equivalent field here).  Thinking is left to
        ``extra_body`` because the two Claude models differ in their default.
        """
        if mode not in MODES:
            raise ValueError("mode must be one of {}, got {!r}".format(list(MODES), mode))
        body: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens if max_tokens is None else int(max_tokens),
            "messages": [{"role": "user", "content": user_content_blocks(user)}],
        }
        if system:
            body["system"] = [{"type": "text", "text": system}]

        if mode == M_CONSTRAINED:
            enforcement = self.backend.constrained
            if enforcement == ENF_NONE:
                raise ValueError(
                    "backend {!r} has no constrained mode; run it in M_free and say "
                    "so in the roster table".format(self.backend.name)
                )
            if enforcement != ENF_JSON_SCHEMA:
                raise ValueError(
                    "the anthropic wire only implements {!r} enforcement, not "
                    "{!r}".format(ENF_JSON_SCHEMA, enforcement)
                )
            body["output_config"] = output_config_payload(schema)

        body.update(self.extra_body)
        body.update(extra_body or {})
        for field_name in self.backend.drop_params:
            body.pop(field_name, None)
        headers = {"anthropic-version": ANTHROPIC_VERSION}
        return "/v1/messages", headers, body

    # -- response parsing (pure, and therefore testable) --------------------- #
    def parse_response(self, status: int, payload: dict, latency_ms: float) -> ChatResponse:
        model = payload.get("model") or self.model
        usage = normalize_usage(payload.get("usage"))
        if status >= 400 or "error" in payload:
            err = payload.get("error")
            message = err.get("message") if isinstance(err, dict) else str(err)
            return ChatResponse(
                text=None,
                outcome=OUTCOME_ERROR,
                model=model,
                latency_ms=latency_ms,
                usage=usage,
                error="HTTP {}: {}".format(status, message),
                status=status,
                raw=payload,
            )
        choices = payload.get("choices") or []
        if not choices:
            return ChatResponse(
                text=None,
                outcome=OUTCOME_ERROR,
                model=model,
                latency_ms=latency_ms,
                usage=usage,
                error="response carried no choices",
                status=status,
                raw=payload,
            )
        choice = choices[0]
        message = choice.get("message") or {}
        text = message.get("content")
        finish = choice.get("finish_reason")
        if message.get("refusal"):
            return ChatResponse(
                text=None,
                outcome=OUTCOME_REFUSAL,
                model=model,
                latency_ms=latency_ms,
                finish_reason=finish,
                usage=usage,
                error=str(message.get("refusal")),
                status=status,
                raw=payload,
            )
        if text is None or text.strip() == "":
            # Documented DeepSeek behaviour, and possible anywhere: an empty
            # completion is its own outcome, never a schema violation.
            return ChatResponse(
                text="" if text is None else text,
                outcome=OUTCOME_EMPTY_CONTENT,
                model=model,
                latency_ms=latency_ms,
                finish_reason=finish,
                usage=usage,
                status=status,
                raw=payload,
            )
        return ChatResponse(
            text=text,
            outcome=OUTCOME_OK,
            model=model,
            latency_ms=latency_ms,
            finish_reason=finish,
            usage=usage,
            status=status,
            raw=payload,
        )

    def parse_response_anthropic(
        self, status: int, payload: dict, latency_ms: float
    ) -> ChatResponse:
        """One ``/v1/messages`` response, in the same normalised shape.

        ``content`` is a list of blocks and the answer is the first ``text``
        one: Opus 5 puts a ``thinking`` block in front of it by default, and
        reading block zero would return the reasoning instead of the answer.
        """
        model = payload.get("model") or self.model
        usage = normalize_usage_anthropic(payload.get("usage"))
        if status >= 400 or payload.get("type") == "error" or "error" in payload:
            err = payload.get("error")
            message = err.get("message") if isinstance(err, dict) else str(err)
            return ChatResponse(
                text=None,
                outcome=OUTCOME_ERROR,
                model=model,
                latency_ms=latency_ms,
                usage=usage,
                error="HTTP {}: {}".format(status, message),
                status=status,
                raw=payload,
            )
        content = payload.get("content") or []
        text = next(
            (
                block.get("text")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ),
            None,
        )
        finish = payload.get("stop_reason")
        if finish == "refusal":
            details = payload.get("stop_details") or {}
            category = details.get("category") if isinstance(details, dict) else None
            return ChatResponse(
                text=text,
                outcome=OUTCOME_REFUSAL,
                model=model,
                latency_ms=latency_ms,
                finish_reason=finish,
                usage=usage,
                error=(
                    "stop_reason=refusal"
                    if not category
                    else "stop_reason=refusal ({})".format(category)
                ),
                status=status,
                raw=payload,
            )
        if text is None or text.strip() == "":
            # Same outcome class as an empty OpenAI completion, and never a
            # schema violation: there is nothing to validate.
            return ChatResponse(
                text="" if text is None else text,
                outcome=OUTCOME_EMPTY_CONTENT,
                model=model,
                latency_ms=latency_ms,
                finish_reason=finish,
                usage=usage,
                status=status,
                raw=payload,
            )
        return ChatResponse(
            text=text,
            outcome=OUTCOME_OK,
            model=model,
            latency_ms=latency_ms,
            finish_reason=finish,
            usage=usage,
            status=status,
            raw=payload,
        )

    # -- the call ------------------------------------------------------------ #
    def complete(self, system: str, user, mode: str = M_FREE, **kwargs) -> ChatResponse:
        """One call, on whichever wire this backend speaks.

        ``user`` is a string or a ``(stable_prefix, tail)`` pair; see
        :func:`split_user`.
        """
        headers = {"Content-Type": "application/json"}
        key = self.api_key()
        if self.backend.wire == WIRE_ANTHROPIC:
            path, wire_headers, body = self.build_request_anthropic(
                system, user, mode, **kwargs
            )
            root = self.base_url
            if root.endswith("/v1"):  # the path already carries the version
                root = root[: -len("/v1")]
            url = "{}{}".format(root, path)
            headers.update(wire_headers)
            if key:
                headers["x-api-key"] = key  # never a bearer token on this wire
            parse = self.parse_response_anthropic
            retry_status = RETRY_STATUS_ANTHROPIC
        else:
            body = self.build_request(system, user, mode, **kwargs)
            url = "{}/chat/completions".format(self.base_url)
            if key:
                headers["Authorization"] = "Bearer {}".format(key)
            parse = self.parse_response
            retry_status = RETRY_STATUS
        blob = json.dumps(body).encode("utf-8")

        attempt = 0
        while True:
            started = time.perf_counter()
            try:
                status, raw = self.transport("POST", url, headers, blob, self.timeout_s)
            except ConnectionError as exc:
                latency_ms = (time.perf_counter() - started) * 1000.0
                if attempt < self.max_retries:
                    attempt += 1
                    time.sleep(self.retry_sleep_s * attempt)
                    continue
                return ChatResponse(
                    text=None,
                    outcome=OUTCOME_ERROR,
                    model=self.model,
                    latency_ms=latency_ms,
                    error=str(exc),
                )
            latency_ms = (time.perf_counter() - started) * 1000.0
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                payload = {"error": {"message": "unparseable response body: {}".format(exc)}}
            if status in retry_status and attempt < self.max_retries:
                attempt += 1
                time.sleep(self.retry_sleep_s * attempt)
                continue
            return parse(status, payload, latency_ms)


# --------------------------------------------------------------------------- #
# vLLM backend read-back                                                       #
# --------------------------------------------------------------------------- #
def read_server_info(base_url: str, transport=None, timeout_s: float = 30.0) -> dict:
    """Fetch ``/server_info`` from a vLLM server (needs ``VLLM_SERVER_DEV_MODE=1``)."""
    transport = transport or urllib_transport
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        root = root[: -len("/v1")]
    status, raw = transport(
        "GET", "{}/server_info?config_format=json".format(root), {}, None, timeout_s
    )
    if status >= 400:
        raise RuntimeError(
            "vLLM /server_info returned HTTP {}. Start the server with "
            "VLLM_SERVER_DEV_MODE=1 so the resolved config can be read back.".format(status)
        )
    return json.loads(raw.decode("utf-8"))


def assert_xgrammar_backend(base_url: str, transport=None) -> str:
    """Assert the live engine resolved the ``xgrammar`` structured-outputs backend.

    vLLM's default backend is ``auto`` and may switch per request; an arm whose
    grammar engine is not fixed cannot carry an enforcement-mode claim.  Returns
    the resolved backend name and raises when it is anything but ``xgrammar``.
    """
    info = read_server_info(base_url, transport)
    cfg = info.get("vllm_config")
    if isinstance(cfg, str):
        raise RuntimeError(
            "/server_info returned the text config; request config_format=json"
        )
    resolved = ((cfg or {}).get("structured_outputs_config") or {}).get("backend")
    if resolved != "xgrammar":
        raise RuntimeError(
            "vLLM resolved structured-outputs backend {!r}, not 'xgrammar'. Launch "
            "with --structured-outputs-config '{{\"backend\": \"xgrammar\"}}'.".format(
                resolved
            )
        )
    return resolved


def available_modes(backend: str) -> tuple:
    """The enforcement modes a backend can actually run (for the roster table)."""
    be = BACKENDS[backend]
    return (M_FREE,) if be.constrained == ENF_NONE else (M_FREE, M_CONSTRAINED)


__all__ = [
    "M_FREE",
    "M_CONSTRAINED",
    "MODES",
    "ENF_NONE",
    "ENF_JSON_OBJECT",
    "ENF_JSON_SCHEMA",
    "ENF_XGRAMMAR",
    "WIRE_OPENAI",
    "WIRE_ANTHROPIC",
    "ANTHROPIC_VERSION",
    "RETRY_STATUS",
    "RETRY_STATUS_ANTHROPIC",
    "Backend",
    "BACKENDS",
    "strict_schema_payload",
    "xgrammar_payload",
    "output_config_payload",
    "split_user",
    "join_user",
    "user_content_blocks",
    "urllib_transport",
    "ChatResponse",
    "normalize_usage",
    "normalize_usage_anthropic",
    "ChatClient",
    "read_server_info",
    "assert_xgrammar_backend",
    "available_modes",
]


if __name__ == "__main__":  # pragma: no cover - a one-call live smoke, never in tests
    import argparse

    ap = argparse.ArgumentParser(description="one live chat call (no test uses this)")
    ap.add_argument("--live", action="store_true", required=True)
    ap.add_argument("--backend", default="vllm", choices=sorted(BACKENDS))
    ap.add_argument("--model", default=None)
    ap.add_argument("--mode", default=M_FREE, choices=list(MODES))
    ap.add_argument("--max-tokens", type=int, default=256)
    args = ap.parse_args()

    client = ChatClient(args.backend, model=args.model, max_tokens=args.max_tokens)
    if args.backend == "vllm" and args.mode == M_CONSTRAINED:
        print("structured-outputs backend:", assert_xgrammar_backend(client.base_url))
    resp = client.complete(
        "You output json only, matching the operations schema.",
        'Return the json {"operations": []}.',
        mode=args.mode,
    )
    print(resp.outcome, resp.finish_reason, resp.usage)
    print(resp.text)
