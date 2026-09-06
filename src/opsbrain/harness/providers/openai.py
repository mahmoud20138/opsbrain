"""OpenAI provider adapter.

Translates OpsBrain's canonical request/response types to/from the
OpenAI Python SDK.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import structlog

from opsbrain.core.config import OpsBrainConfig, ProviderConfig
from opsbrain.core.exceptions import (
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from opsbrain.core.types import (
    LLMRequest,
    LLMResponse,
    Message,
    Provider,
    ToolCall,
    ToolDefinition,
    UsageStats,
)
from opsbrain.harness.base import LLMClient

logger = structlog.get_logger(__name__)

_SUPPORTED_FEATURES = {
    "tool_calling",
    "structured_output",
    "vision",
    "streaming",
}


class OpenAIClient(LLMClient):
    """LLM client adapter for OpenAI's API."""

    provider = Provider.OPENAI
    display_name = "OpenAI"

    def __init__(self, config: ProviderConfig, global_config: OpsBrainConfig) -> None:
        import openai

        self._config = config
        self._model = config.default_model or "gpt-4o"
        self._client = openai.AsyncOpenAI(
            api_key=config.api_key or None,
            base_url=config.api_base or None,
            timeout=config.timeout_seconds,
            max_retries=0,  # we handle retries in the harness layer
        )

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send a chat completion request to OpenAI."""
        import openai

        model = request.model or self._model
        messages = _to_openai_messages(request.messages)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
        }
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens
        if request.stop:
            kwargs["stop"] = request.stop
        if request.response_format:
            kwargs["response_format"] = request.response_format

        try:
            response = await self._client.chat.completions.create(**kwargs)
        except openai.AuthenticationError as exc:
            raise ProviderAuthError(
                str(exc), provider="openai", model=model,
            ) from exc
        except openai.RateLimitError as exc:
            raise ProviderRateLimitError(
                str(exc), provider="openai", model=model,
            ) from exc
        except openai.APITimeoutError as exc:
            raise ProviderTimeoutError(
                str(exc), provider="openai", model=model,
            ) from exc
        except openai.APIError as exc:
            raise ProviderError(
                str(exc), provider="openai", model=model,
            ) from exc

        return _from_openai_response(response, model)

    async def complete_with_tools(
        self,
        request: LLMRequest,
        tools: list[ToolDefinition],
    ) -> LLMResponse:
        """Send a chat completion with tool definitions."""
        import openai

        model = request.model or self._model
        messages = _to_openai_messages(request.messages)
        openai_tools = _to_openai_tools(tools)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "tools": openai_tools,
            "temperature": request.temperature,
        }
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens

        try:
            response = await self._client.chat.completions.create(**kwargs)
        except openai.AuthenticationError as exc:
            raise ProviderAuthError(str(exc), provider="openai", model=model) from exc
        except openai.RateLimitError as exc:
            raise ProviderRateLimitError(str(exc), provider="openai", model=model) from exc
        except openai.APITimeoutError as exc:
            raise ProviderTimeoutError(str(exc), provider="openai", model=model) from exc
        except openai.APIError as exc:
            raise ProviderError(str(exc), provider="openai", model=model) from exc

        return _from_openai_response(response, model)

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Stream completion tokens from OpenAI."""
        model = request.model or self._model
        messages = _to_openai_messages(request.messages)

        stream = await self._client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    def supports_feature(self, feature: str) -> bool:
        return feature in _SUPPORTED_FEATURES

    async def close(self) -> None:
        await self._client.close()


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------

def _to_openai_messages(messages: list[Message]) -> list[dict[str, Any]]:
    """Convert OpsBrain messages to OpenAI message dicts."""
    result: list[dict[str, Any]] = []
    for msg in messages:
        entry: dict[str, Any] = {"role": msg.role, "content": msg.content}
        if msg.name:
            entry["name"] = msg.name
        if msg.tool_call_id:
            entry["tool_call_id"] = msg.tool_call_id
        result.append(entry)
    return result


def _to_openai_tools(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
    """Convert OpsBrain tool definitions to OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in tools
    ]


def _from_openai_response(response: Any, model: str) -> LLMResponse:
    """Convert an OpenAI response to OpsBrain's canonical format."""
    choice = response.choices[0] if response.choices else None
    content = ""
    tool_calls: list[ToolCall] = []

    if choice and choice.message:
        content = choice.message.content or ""
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments) if tc.function.arguments else {},
                ))

    usage = UsageStats()
    if response.usage:
        usage = UsageStats(
            prompt_tokens=response.usage.prompt_tokens or 0,
            completion_tokens=response.usage.completion_tokens or 0,
            total_tokens=response.usage.total_tokens or 0,
        )

    return LLMResponse(
        content=content,
        tool_calls=tool_calls,
        model=response.model or model,
        provider=Provider.OPENAI,
        usage=usage,
        finish_reason=choice.finish_reason if choice else None,
    )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_client(config: ProviderConfig, global_config: OpsBrainConfig) -> LLMClient:
    """Factory function called by the ProviderRegistry."""
    return OpenAIClient(config, global_config)
