"""Mock LLM provider for local testing, offline development, and reproducible demos."""

from __future__ import annotations

from collections.abc import AsyncIterator

from opsbrain.core.types import (
    LLMRequest,
    LLMResponse,
    Provider,
    ToolDefinition,
    UsageStats,
)
from opsbrain.harness.base import LLMClient


class MockLLMClient(LLMClient):
    """Configurable mock LLM client returning canned or dynamic responses."""

    provider = Provider.LITELLM
    display_name = "Mock Provider"

    def __init__(self, *, response_content: str = "Mock response") -> None:
        self._response_content = response_content
        self.call_count = 0
        self.last_request: LLMRequest | None = None

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.call_count += 1
        self.last_request = request
        return LLMResponse(
            content=self._response_content,
            model="mock-model",
            provider=Provider.LITELLM,
            usage=UsageStats(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                cost_usd=0.0001,
            ),
        )

    async def complete_with_tools(
        self,
        request: LLMRequest,
        tools: list[ToolDefinition],
    ) -> LLMResponse:
        return await self.complete(request)

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        yield self._response_content

    def supports_feature(self, feature: str) -> bool:
        return True
