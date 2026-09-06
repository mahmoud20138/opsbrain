"""LiteLLM fallback provider adapter.

Provides a catch-all adapter that can route to 100+ providers via LiteLLM's
unified completion interface. Used as the last resort in the fallback chain
when native adapters are not available.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import structlog

from opsbrain.core.config import OpsBrainConfig, ProviderConfig
from opsbrain.core.exceptions import ProviderError
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


class LiteLLMClient(LLMClient):
    """Catch-all LLM client using LiteLLM for broad provider coverage.

    LiteLLM normalizes the interface across 100+ providers so this
    adapter can serve as a universal fallback.
    """

    provider = Provider.LITELLM
    display_name = "LiteLLM (Universal)"

    def __init__(self, config: ProviderConfig, global_config: OpsBrainConfig) -> None:
        self._config = config
        self._model = config.default_model or "gpt-4o"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send a completion request via LiteLLM."""
        import litellm

        model = request.model or self._model
        messages = _to_litellm_messages(request.messages)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
        }
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens
        if request.stop:
            kwargs["stop"] = request.stop

        try:
            response = await litellm.acompletion(**kwargs)
        except Exception as exc:
            raise ProviderError(
                str(exc), provider="litellm", model=model,
            ) from exc

        return _from_litellm_response(response, model)

    async def complete_with_tools(
        self,
        request: LLMRequest,
        tools: list[ToolDefinition],
    ) -> LLMResponse:
        """Send a completion request with tools via LiteLLM."""
        import litellm

        model = request.model or self._model
        messages = _to_litellm_messages(request.messages)
        litellm_tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

        try:
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                tools=litellm_tools,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
        except Exception as exc:
            raise ProviderError(str(exc), provider="litellm", model=model) from exc

        return _from_litellm_response(response, model)

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Stream completion tokens via LiteLLM."""
        import litellm

        model = request.model or self._model
        messages = _to_litellm_messages(request.messages)

        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True,
        )

        async for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    def supports_feature(self, feature: str) -> bool:
        # LiteLLM supports most features depending on the underlying model
        return feature in {"tool_calling", "streaming", "structured_output", "vision"}


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------

def _to_litellm_messages(messages: list[Message]) -> list[dict[str, str]]:
    """Convert OpsBrain messages to LiteLLM-compatible dicts."""
    return [{"role": msg.role, "content": msg.content} for msg in messages]


def _from_litellm_response(response: Any, model: str) -> LLMResponse:
    """Convert a LiteLLM response to OpsBrain's canonical format."""
    import json

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
            prompt_tokens=getattr(response.usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(response.usage, "completion_tokens", 0) or 0,
            total_tokens=getattr(response.usage, "total_tokens", 0) or 0,
        )

    return LLMResponse(
        content=content,
        tool_calls=tool_calls,
        model=getattr(response, "model", model) or model,
        provider=Provider.LITELLM,
        usage=usage,
        finish_reason=choice.finish_reason if choice else None,
    )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_client(config: ProviderConfig, global_config: OpsBrainConfig) -> LLMClient:
    """Factory function called by the ProviderRegistry."""
    return LiteLLMClient(config, global_config)
