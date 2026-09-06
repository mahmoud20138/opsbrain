"""Google Gemini provider adapter.

Translates OpsBrain's canonical request/response types to/from the
google-genai Python SDK.
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
    "vision",
    "streaming",
}


class GeminiClient(LLMClient):
    """LLM client adapter for Google's Gemini API via google-genai SDK."""

    provider = Provider.GEMINI
    display_name = "Google Gemini"

    def __init__(self, config: ProviderConfig, global_config: OpsBrainConfig) -> None:
        from google import genai

        self._config = config
        self._model = config.default_model or "gemini-2.5-flash"
        self._genai_client = genai.Client(api_key=config.api_key or None)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send a generation request to Gemini."""
        from google.genai import types as genai_types

        model = request.model or self._model
        system_prompt, contents = _build_contents(request.messages)

        config = genai_types.GenerateContentConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
            system_instruction=system_prompt or None,
        )

        try:
            response = await self._genai_client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            _raise_mapped(exc, model)

        return _from_gemini_response(response, model)

    async def complete_with_tools(
        self,
        request: LLMRequest,
        tools: list[ToolDefinition],
    ) -> LLMResponse:
        """Send a generation request with tool declarations to Gemini."""
        from google.genai import types as genai_types

        model = request.model or self._model
        system_prompt, contents = _build_contents(request.messages)

        gemini_tools = _to_gemini_tools(tools)

        config = genai_types.GenerateContentConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
            system_instruction=system_prompt or None,
            tools=gemini_tools,
        )

        try:
            response = await self._genai_client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            _raise_mapped(exc, model)

        return _from_gemini_response(response, model)

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Stream generation tokens from Gemini."""
        from google.genai import types as genai_types

        model = request.model or self._model
        system_prompt, contents = _build_contents(request.messages)

        config = genai_types.GenerateContentConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
            system_instruction=system_prompt or None,
        )

        async for chunk in self._genai_client.aio.models.generate_content_stream(
            model=model,
            contents=contents,
            config=config,
        ):
            if chunk.text:
                yield chunk.text

    def supports_feature(self, feature: str) -> bool:
        return feature in _SUPPORTED_FEATURES


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------

def _build_contents(messages: list[Message]) -> tuple[str, list[dict[str, Any]]]:
    """Separate system prompt and build Gemini-compatible content list.

    Returns:
        ``(system_prompt, contents)``
    """
    system_parts: list[str] = []
    contents: list[dict[str, Any]] = []

    for msg in messages:
        if msg.role == "system":
            system_parts.append(msg.content)
        else:
            # Gemini uses "user" and "model" roles
            role = "model" if msg.role == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

    return "\n\n".join(system_parts), contents


def _to_gemini_tools(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
    """Convert OpsBrain tool definitions to Gemini function declarations."""
    declarations = []
    for tool in tools:
        declarations.append({
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters or {"type": "object", "properties": {}},
        })
    return [{"function_declarations": declarations}]


def _from_gemini_response(response: Any, model: str) -> LLMResponse:
    """Convert a Gemini response to OpsBrain's canonical format."""
    content = ""
    tool_calls: list[ToolCall] = []

    if response.candidates:
        candidate = response.candidates[0]
        for part in candidate.content.parts:
            if hasattr(part, "text") and part.text:
                content += part.text
            elif hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                tool_calls.append(ToolCall(
                    name=fc.name,
                    arguments=dict(fc.args) if fc.args else {},
                ))

    usage = UsageStats()
    if response.usage_metadata:
        um = response.usage_metadata
        usage = UsageStats(
            prompt_tokens=getattr(um, "prompt_token_count", 0) or 0,
            completion_tokens=getattr(um, "candidates_token_count", 0) or 0,
            total_tokens=getattr(um, "total_token_count", 0) or 0,
        )

    return LLMResponse(
        content=content,
        tool_calls=tool_calls,
        model=model,
        provider=Provider.GEMINI,
        usage=usage,
        finish_reason=str(response.candidates[0].finish_reason) if response.candidates else None,
    )


def _raise_mapped(exc: Exception, model: str) -> None:
    """Map Gemini SDK exceptions to OpsBrain exceptions."""
    msg = str(exc)
    if "401" in msg or "403" in msg or "API_KEY" in msg.upper():
        raise ProviderAuthError(msg, provider="gemini", model=model) from exc
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
        raise ProviderRateLimitError(msg, provider="gemini", model=model) from exc
    if "timeout" in msg.lower() or "DEADLINE_EXCEEDED" in msg:
        raise ProviderTimeoutError(msg, provider="gemini", model=model) from exc
    raise ProviderError(msg, provider="gemini", model=model) from exc


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_client(config: ProviderConfig, global_config: OpsBrainConfig) -> LLMClient:
    """Factory function called by the ProviderRegistry."""
    return GeminiClient(config, global_config)
