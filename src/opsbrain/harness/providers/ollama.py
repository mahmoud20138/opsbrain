"""Ollama provider adapter for local model inference.

Uses the Ollama HTTP API to run models like Llama, Mistral, Qwen, etc.
locally without sending data to external services.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
import structlog

from opsbrain.core.config import OpsBrainConfig, ProviderConfig
from opsbrain.core.exceptions import (
    ProviderError,
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
    "streaming",
    "tool_calling",  # Ollama supports tool calling for compatible models
}


class OllamaClient(LLMClient):
    """LLM client adapter for locally-running Ollama models."""

    provider = Provider.OLLAMA
    display_name = "Ollama (Local)"

    def __init__(self, config: ProviderConfig, global_config: OpsBrainConfig) -> None:
        self._config = config
        self._model = config.default_model or "llama3.1"
        self._base_url = (config.api_base or "http://localhost:11434").rstrip("/")
        self._timeout = config.timeout_seconds or 120
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
        )

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send a chat request to the local Ollama server."""
        model = request.model or self._model
        messages = _to_ollama_messages(request.messages)

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": request.temperature,
            },
        }
        if request.max_tokens:
            payload["options"]["num_predict"] = request.max_tokens

        try:
            resp = await self._http.post("/api/chat", json=payload)
            resp.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(str(exc), provider="ollama", model=model) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(str(exc), provider="ollama", model=model) from exc

        data = resp.json()
        return _from_ollama_response(data, model)

    async def complete_with_tools(
        self,
        request: LLMRequest,
        tools: list[ToolDefinition],
    ) -> LLMResponse:
        """Send a chat request with tools to Ollama.

        Note: Tool calling support depends on the specific model.
        """
        model = request.model or self._model
        messages = _to_ollama_messages(request.messages)
        ollama_tools = _to_ollama_tools(tools)

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "tools": ollama_tools,
            "stream": False,
            "options": {
                "temperature": request.temperature,
            },
        }
        if request.max_tokens:
            payload["options"]["num_predict"] = request.max_tokens

        try:
            resp = await self._http.post("/api/chat", json=payload)
            resp.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(str(exc), provider="ollama", model=model) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(str(exc), provider="ollama", model=model) from exc

        data = resp.json()
        return _from_ollama_response(data, model)

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Stream chat tokens from Ollama."""
        import json as json_mod

        model = request.model or self._model
        messages = _to_ollama_messages(request.messages)

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": request.temperature,
            },
        }
        if request.max_tokens:
            payload["options"]["num_predict"] = request.max_tokens

        async with self._http.stream("POST", "/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.strip():
                    chunk = json_mod.loads(line)
                    msg = chunk.get("message", {})
                    content = msg.get("content", "")
                    if content:
                        yield content

    def supports_feature(self, feature: str) -> bool:
        return feature in _SUPPORTED_FEATURES

    async def health_check(self) -> bool:
        """Check if Ollama server is running."""
        try:
            resp = await self._http.get("/api/tags")
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._http.aclose()


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------

def _to_ollama_messages(messages: list[Message]) -> list[dict[str, str]]:
    """Convert OpsBrain messages to Ollama chat format."""
    return [{"role": msg.role, "content": msg.content} for msg in messages]


def _to_ollama_tools(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
    """Convert tool definitions to Ollama's tool format."""
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


def _from_ollama_response(data: dict[str, Any], model: str) -> LLMResponse:
    """Convert an Ollama response dict to OpsBrain's canonical format."""
    message = data.get("message", {})
    content = message.get("content", "")

    tool_calls: list[ToolCall] = []
    for tc in message.get("tool_calls", []):
        func = tc.get("function", {})
        tool_calls.append(ToolCall(
            name=func.get("name", ""),
            arguments=func.get("arguments", {}),
        ))

    # Ollama reports token counts at the response level
    usage = UsageStats(
        prompt_tokens=data.get("prompt_eval_count", 0),
        completion_tokens=data.get("eval_count", 0),
        total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
        cost_usd=0.0,  # local models are free
    )

    return LLMResponse(
        content=content,
        tool_calls=tool_calls,
        model=data.get("model", model),
        provider=Provider.OLLAMA,
        usage=usage,
        finish_reason=data.get("done_reason"),
    )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_client(config: ProviderConfig, global_config: OpsBrainConfig) -> LLMClient:
    """Factory function called by the ProviderRegistry."""
    return OllamaClient(config, global_config)
