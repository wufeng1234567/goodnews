"""The single OpenAI-compatible LLM gateway used by the application.

Design notes
------------
* The OpenAI SDK is used directly. No LangChain chat model, chain or agent is
  involved anywhere in the core path.
* Business code depends on :class:`LLMClientProtocol`, which keeps tests fast
  and makes the concrete provider replaceable.
* JSON mode is requested from DeepSeek, then validated by the caller's Pydantic
  model. One repair round is attempted when validation fails.

MVP temporary implementation: retries are in-process and synchronous relative
to the HTTP request. Later refactor point: move long fact-check jobs to a queue
and add per-user budget/observability.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections.abc import AsyncIterator, Sequence
from typing import Any, Literal, Protocol, TypeVar

import openai
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings

logger = logging.getLogger(__name__)

MessageRole = Literal["system", "user", "assistant"]
T = TypeVar("T", bound=BaseModel)


class LLMMessage(BaseModel):
    role: MessageRole
    content: str


class LLMResponse(BaseModel):
    """Normalized completion response returned to graph nodes."""

    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str | None = None
    latency_ms: int = 0


class LLMError(RuntimeError):
    """Base class for failures that a route can translate into an API error."""


class LLMConfigurationError(LLMError):
    """The provider is not configured (usually a missing API key)."""


class LLMResponseError(LLMError):
    """The provider responded, but the payload was unusable."""


class LLMClientProtocol(Protocol):
    """Minimal interface consumed by LangGraph nodes and the graph verifier."""

    async def chat_json(
        self,
        messages: Sequence[LLMMessage],
        schema: type[T],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> T: ...


class LLMClient:
    """Thin wrapper around ``AsyncOpenAI`` with retries, JSON parsing and streaming."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._api_key = settings.llm_api_key
        self._model = settings.llm_model
        # The SDK's built-in retry is disabled so our retry policy is explicit.
        self._client = AsyncOpenAI(
            api_key=self._api_key or "not-configured",
            base_url=settings.llm_base_url,
            timeout=settings.llm_timeout_seconds,
            max_retries=0,
        )

    @property
    def model(self) -> str:
        return self._model

    def _ensure_configured(self) -> None:
        if not self._api_key:
            raise LLMConfigurationError(
                "未配置 DEEPSEEK_API_KEY，请在仓库根目录 .env 中填写后重启后端"
            )

    async def chat(
        self,
        messages: Sequence[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Call chat completions with explicit timeout/retry and normalized usage."""
        self._ensure_configured()
        if not messages:
            raise LLMError("LLM messages cannot be empty")

        request: dict[str, Any] = {
            "model": self._model,
            "messages": [message.model_dump() for message in messages],
            "temperature": self._settings.llm_temperature if temperature is None else temperature,
            "max_tokens": self._settings.llm_max_tokens if max_tokens is None else max_tokens,
        }
        if json_mode:
            request["response_format"] = {"type": "json_object"}

        started = time.perf_counter()
        last_error: Exception | None = None
        for attempt in range(self._settings.llm_max_retries + 1):
            try:
                completion = await self._client.chat.completions.create(**request)
                choice = completion.choices[0] if completion.choices else None
                content = (choice.message.content or "") if choice else ""
                if not content.strip():
                    raise LLMResponseError("LLM 返回了空内容")
                usage = completion.usage
                return LLMResponse(
                    content=content,
                    model=completion.model or self._model,
                    prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                    completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
                    total_tokens=getattr(usage, "total_tokens", 0) or 0,
                    finish_reason=choice.finish_reason if choice else None,
                    latency_ms=int((time.perf_counter() - started) * 1000),
                )
            except LLMResponseError:
                raise
            except (openai.APITimeoutError, openai.APIConnectionError, openai.RateLimitError) as exc:
                last_error = exc
            except openai.APIStatusError as exc:
                last_error = exc
                if exc.status_code < 500 and exc.status_code != 429:
                    raise LLMError(f"LLM 请求失败: HTTP {exc.status_code}") from exc
            if attempt < self._settings.llm_max_retries:
                delay = 1.5 * (2**attempt)
                logger.warning("LLM request failed (attempt %s), retrying in %.1fs", attempt + 1, delay)
                await asyncio.sleep(delay)

        raise LLMError(f"LLM 请求重试后仍失败: {last_error}")

    async def chat_json(
        self,
        messages: Sequence[LLMMessage],
        schema: type[T],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> T:
        """Request JSON mode and validate the answer against a Pydantic model."""
        schema_hint = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        enriched_messages = [
            *messages,
            LLMMessage(
                role="system",
                content=(
                    "你必须只返回一个 JSON 对象，不要包含 Markdown 代码块或解释文字。"
                    f"输出必须符合以下 JSON Schema：{schema_hint}"
                ),
            ),
        ]
        response = await self.chat(
            enriched_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True,
        )

        try:
            return schema.model_validate(_parse_json_object(response.content))
        except (ValueError, ValidationError) as first_error:
            logger.warning("LLM JSON validation failed: %s", first_error)
            if self._settings.llm_json_repair_attempts <= 0:
                raise LLMResponseError("LLM 返回的 JSON 不符合结构要求") from first_error

            repair_messages = [
                *enriched_messages,
                LLMMessage(role="assistant", content=response.content),
                LLMMessage(
                    role="user",
                    content=(
                        "上面的 JSON 不符合 Schema。请修正并重新输出完整 JSON 对象，"
                        f"错误信息：{first_error}"
                    ),
                ),
            ]
            repaired = await self.chat(repair_messages, temperature=0, json_mode=True)
            try:
                return schema.model_validate(_parse_json_object(repaired.content))
            except (ValueError, ValidationError) as repair_error:
                raise LLMResponseError("LLM 两次返回的 JSON 均不符合结构要求") from repair_error

    async def chat_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Yield incremental text tokens.

        The current fact-check API is synchronous. This method exists because
        the gateway contract requires streaming support and is ready for the
        later SSE endpoint without changing call sites.
        """
        self._ensure_configured()
        started = time.perf_counter()
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=[message.model_dump() for message in messages],
            temperature=self._settings.llm_temperature if temperature is None else temperature,
            max_tokens=self._settings.llm_max_tokens if max_tokens is None else max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            content = chunk.choices[0].delta.content
            if content:
                yield content
        logger.debug("LLM stream finished in %sms", int((time.perf_counter() - started) * 1000))

    async def aclose(self) -> None:
        await self._client.close()


class _ParsedJSONEnvelope(BaseModel):
    """Internal-only wrapper used to type the parsed value."""

    model_config = ConfigDict(extra="ignore")
    value: dict[str, Any] = Field(default_factory=dict)


def _parse_json_object(raw: str) -> dict[str, Any]:
    """Extract one JSON object from a model response.

    Models occasionally wrap JSON in ``` fences despite JSON mode. We strip
    those first, then fall back to slicing the outermost object braces.
    """
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("response does not contain a JSON object")
        parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        # This is a malformed provider payload, not a Python API misuse.
        raise ValueError("expected a JSON object at the root")  # noqa: TRY004
    return parsed
