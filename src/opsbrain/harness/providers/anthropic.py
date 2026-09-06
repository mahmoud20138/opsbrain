"""Anthropic Claude provider adapter.

Translates OpsBrain's canonical request/response types to/from the
Anthropic Python SDK.
"""

from __future__ import annotations

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
    "streaming",
    "extended_thinking",
    "vision",
}


class AnthropicClient(LLMClient):
    """LLM client adapter for Anthropic's Claude API."""

    provider = Provider.ANTHROPIC
    display_name = "Anthropic Claude"

    def __init__(self, config: ProviderConfig, global_config: OpsBrainConfig) -> None:
        import anthropic

        self._config = config
        self._model = config.default_model or "claude-sonnet-4-20250514"
        self._client = anthropic.AsyncAnthropic(
            api_key=config.api_key or None,
            base_url=config.api_base or None,
            timeout=config.timeout_seconds,
            max_retries=0,
        )

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send a message request to Claude."""
        import anthropic

        model = request.model or self._model
        system_prompt, messages = _split_system(request.messages)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": _to_anthropic_messages(messages),
            "max_tokens": request.max_tokens or 4096,
            "temperature": request.temperature,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if request.stop:
            kwargs["stop_sequences"] = request.stop

        try:
            response = await self._client.messages.create(**kwargs)
        except anthropic.AuthenticationError as exc:
            raise ProviderAuthError(str(exc), provider="anthropic", model=model) from exc
        except anthropic.RateLimitError as exc:
            raise ProviderRateLimitError(str(exc), provider="anthropic", model=model) from exc
        except anthropic.APITimeoutError as exc:
            raise ProviderTimeoutError(str(exc), provider="anthropic", model=model) from exc
        except anthropic.APIError as exc:
            raise ProviderError(str(exc), provider="anthropic", model=model) from exc

        return _from_anthropic_response(response, model)

    async def complete_with_tools(
        self,
        request: LLMRequest,
        tools: list[ToolDefinition],
    ) -> LLMResponse:
        """Send a message request with tool definitions to Claude."""
        import anthropic

        model = request.model or self._model
        system_prompt, messages = _split_system(request.messages)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": _to_anthropic_messages(messages),
            "tools": _to_anthropic_tools(tools),
            "max_tokens": request.max_tokens or 4096,
            "temperature": request.temperature,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        try:
            response = await self._client.messages.create(**kwargs)
        except anthropic.AuthenticationError as exc:
            raise ProviderAuthError(str(exc), provider="anthropic", model=model) from exc
        except anthropic.RateLimitError as exc:
            raise ProviderRateLimitError(str(exc), provider="anthropic", model=model) from exc
        except anthropic.APITimeoutError as exc:
            raise ProviderTimeoutError(str(exc), provider="anthropic", model=model) from exc
        except anthropic.APIError as exc:
            raise ProviderError(str(exc), provider="anthropic", model=model) from exc

        return _from_anthropic_response(response, model)

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Stream message tokens from Claude."""
        model = request.model or self._model
        system_prompt, messages = _split_system(request.messages)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": _to_anthropic_messages(messages),
            "max_tokens": request.max_tokens or 4096,
            "temperature": request.temperature,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text

    def supports_feature(self, feature: str) -> bool:
        return feature in _SUPPORTED_FEATURES

    async def close(self) -> None:
        await self._client.close()


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------

def _split_system(messages: list[Message]) -> tuple[str, list[Message]]:
    """Extract the system prompt from the message list.

    Claude takes the system prompt as a top-level parameter rather than
    as a message, so we separate it out.

    Returns:
        ``(system_prompt, remaining_messages)``
    """
    system_parts: list[str] = []
    remaining: list[Message] = []
    for msg in messages:
        if msg.role == "system":
            system_parts.append(msg.content)
        else:
            remaining.append(msg)
    return "\n\n".join(system_parts), remaining


def _to_anthropic_messages(messages: list[Message]) -> list[dict[str, Any]]:
    """Convert OpsBrain messages to Anthropic message dicts."""
    result: list[dict[str, Any]] = []
    for msg in messages:
        entry: dict[str, Any] = {"role": msg.role, "content": msg.content}
        result.append(entry)
    return result


def _to_anthropic_tools(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
    """Convert OpsBrain tool definitions to Anthropic's tool format."""
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.parameters,
        }
        for tool in tools
    ]


def _from_anthropic_response(response: Any, model: str) -> LLMResponse:
    """Convert an Anthropic response to OpsBrain's canonical format."""
    content_parts: list[str] = []
    tool_calls: list[ToolCall] = []

    for block in response.content:
        if block.type == "text":
            content_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append(ToolCall(
                id=block.id,
                name=block.name,
                arguments=block.input if isinstance(block.input, dict) else {},
            ))

    usage = UsageStats(
        prompt_tokens=response.usage.input_tokens,
        completion_tokens=response.usage.output_tokens,
        total_tokens=response.usage.input_tokens + response.usage.output_tokens,
    )

    return LLMResponse(
        content="\n".join(content_parts),
        tool_calls=tool_calls,
        model=response.model or model,
        provider=Provider.ANTHROPIC,
        usage=usage,
        finish_reason=response.stop_reason,
    )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_client(config: ProviderConfig, global_config: OpsBrainConfig) -> LLMClient:
    """Factory function called by the ProviderRegistry."""
    return AnthropicClient(config, global_config)
