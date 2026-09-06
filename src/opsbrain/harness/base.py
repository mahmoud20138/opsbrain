"""Abstract base class for all LLM provider adapters.

Every provider (OpenAI, Gemini, Claude, Ollama, LiteLLM) implements this
interface so the rest of OpsBrain never touches provider-specific code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from opsbrain.core.types import (
    LLMRequest,
    LLMResponse,
    Provider,
    ToolDefinition,
)


class LLMClient(ABC):
    """Unified interface that every LLM provider adapter must implement.

    Subclasses handle the translation between OpsBrain's canonical
    :class:`LLMRequest` / :class:`LLMResponse` types and the provider's
    native SDK objects.
    """

    # Subclasses must set these class-level attributes
    provider: Provider
    display_name: str = ""

    # ----- core methods -----

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send a chat-completion request and return the full response.

        Args:
            request: The unified request object.

        Returns:
            A unified response object.
        """

    @abstractmethod
    async def complete_with_tools(
        self,
        request: LLMRequest,
        tools: list[ToolDefinition],
    ) -> LLMResponse:
        """Send a chat-completion request that may invoke tools.

        The provider adapter translates *tools* into the provider's native
        tool / function-calling schema and parses tool-call responses back
        into :class:`ToolCall` objects.

        Args:
            request: The unified request object.
            tools: Tool definitions the model may call.

        Returns:
            A unified response, potentially containing ``tool_calls``.
        """

    @abstractmethod
    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Stream completion tokens incrementally.

        Args:
            request: The unified request object.

        Yields:
            String chunks as they arrive from the provider.
        """

    # ----- capability introspection -----

    @abstractmethod
    def supports_feature(self, feature: str) -> bool:
        """Check whether this provider supports a given feature.

        Common feature strings:
        - ``"tool_calling"``
        - ``"structured_output"``
        - ``"vision"``
        - ``"streaming"``
        - ``"extended_thinking"``

        Args:
            feature: The feature identifier to check.

        Returns:
            ``True`` if the feature is supported.
        """

    # ----- lifecycle -----

    async def health_check(self) -> bool:
        """Verify connectivity to the provider.

        The default implementation sends a minimal completion request.
        Providers may override with a cheaper check.

        Returns:
            ``True`` if the provider is reachable and authenticated.
        """
        try:
            from opsbrain.core.types import Message

            resp = await self.complete(LLMRequest(
                messages=[Message(role="user", content="ping")],
                max_tokens=5,
            ))
            return bool(resp.content)
        except Exception:
            return False

    async def close(self) -> None:  # noqa: B027
        """Release any resources held by the client.

        Override if the provider SDK requires explicit cleanup.
        """

    # ----- metadata -----

    def get_info(self) -> dict[str, Any]:
        """Return a dict of metadata about this provider for diagnostics."""
        return {
            "provider": self.provider.value,
            "display_name": self.display_name or self.provider.value,
            "features": {
                feat: self.supports_feature(feat)
                for feat in (
                    "tool_calling",
                    "structured_output",
                    "vision",
                    "streaming",
                    "extended_thinking",
                )
            },
        }

    def __repr__(self) -> str:
        return f"<{type(self).__name__} provider={self.provider.value}>"
