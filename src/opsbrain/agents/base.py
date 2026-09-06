"""Abstract base class for all OpsBrain agents.

Each agent has a role, system prompt, access to tools, and an LLM client.
Agents communicate via the EventBus and share context through an
AgentContext object.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import structlog

from opsbrain.core.events import EventBus
from opsbrain.core.types import (
    AgentMessage,
    AgentRole,
    LLMRequest,
    LLMResponse,
    Message,
    ToolDefinition,
)
from opsbrain.harness.base import LLMClient

logger = structlog.get_logger(__name__)


class AgentContext:
    """Shared context passed to an agent during processing.

    Contains the incident data, prior agent outputs, and configuration
    that an agent needs to reason and take action.
    """

    def __init__(
        self,
        *,
        incident_id: str = "",
        data: dict[str, Any] | None = None,
        prior_outputs: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.incident_id = incident_id
        self.data = data or {}
        self.prior_outputs = prior_outputs or {}
        self.config = config or {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the context data."""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in the context data."""
        self.data[key] = value


class AgentOutput:
    """Structured output from an agent's processing step.

    Contains the agent's response, any structured data it produced,
    and metadata about the processing.
    """

    def __init__(
        self,
        *,
        agent_role: AgentRole,
        content: str = "",
        structured_data: dict[str, Any] | None = None,
        confidence: float = 0.0,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        self.agent_role = agent_role
        self.content = content
        self.structured_data = structured_data or {}
        self.confidence = confidence
        self.tokens_used = tokens_used
        self.cost_usd = cost_usd

    def __repr__(self) -> str:
        return (
            f"<AgentOutput role={self.agent_role.value} "
            f"confidence={self.confidence:.2f} "
            f"tokens={self.tokens_used}>"
        )


class Agent(ABC):
    """Base class for all OpsBrain agents.

    Subclasses implement :meth:`process` to perform their specialized
    task (monitoring, RCA, solution generation, coordination, evaluation).

    Usage::

        class MyAgent(Agent):
            role = AgentRole.MONITOR
            name = "my_monitor"

            async def process(self, context: AgentContext) -> AgentOutput:
                analysis = await self.think("Analyze these metrics...")
                return AgentOutput(
                    agent_role=self.role,
                    content=analysis,
                )
    """

    # Subclasses must set these
    role: AgentRole
    name: str = ""

    def __init__(
        self,
        *,
        llm_client: LLMClient,
        system_prompt: str = "",
        tools: list[ToolDefinition] | None = None,
        event_bus: EventBus | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> None:
        self.llm_client = llm_client
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.event_bus = event_bus
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._conversation: list[Message] = []

    # ----- abstract -----

    @abstractmethod
    async def process(self, context: AgentContext) -> AgentOutput:
        """Execute the agent's main task.

        Args:
            context: Shared context with incident data and prior outputs.

        Returns:
            An :class:`AgentOutput` with the agent's findings.
        """

    # ----- helper methods for subclasses -----

    async def think(self, prompt: str) -> str:
        """Make a single LLM call with the agent's system prompt.

        Appends the user prompt to the conversation history, calls the
        LLM, and returns the assistant's text response.

        Args:
            prompt: The user-role prompt to send.

        Returns:
            The assistant's text response.
        """
        messages: list[Message] = []
        if self.system_prompt:
            messages.append(Message(role="system", content=self.system_prompt))
        messages.extend(self._conversation)
        messages.append(Message(role="user", content=prompt))

        request = LLMRequest(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        response = await self.llm_client.complete(request)

        # Track conversation for multi-turn reasoning
        self._conversation.append(Message(role="user", content=prompt))
        self._conversation.append(Message(role="assistant", content=response.content))

        logger.info(
            "agent.think",
            agent=self.name or self.role.value,
            tokens=response.usage.total_tokens,
            prompt_preview=prompt[:80],
        )
        return response.content

    async def think_with_tools(self, prompt: str) -> LLMResponse:
        """Make an LLM call that may invoke tools.

        Args:
            prompt: The user-role prompt.

        Returns:
            The full :class:`LLMResponse`, which may contain tool calls.
        """
        messages: list[Message] = []
        if self.system_prompt:
            messages.append(Message(role="system", content=self.system_prompt))
        messages.extend(self._conversation)
        messages.append(Message(role="user", content=prompt))

        request = LLMRequest(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        response = await self.llm_client.complete_with_tools(request, self.tools)

        self._conversation.append(Message(role="user", content=prompt))
        self._conversation.append(Message(role="assistant", content=response.content))

        return response

    async def emit(self, content: str, *, recipient: AgentRole | None = None, data: dict[str, Any] | None = None) -> None:
        """Publish a message to the event bus.

        Args:
            content: Message content.
            recipient: Target agent role (``None`` for broadcast).
            data: Additional structured data.
        """
        if self.event_bus is None:
            return

        msg = AgentMessage(
            sender=self.role,
            recipient=recipient,
            content=content,
            data=data or {},
        )
        await self.event_bus.publish(msg)

    def reset_conversation(self) -> None:
        """Clear the conversation history for a fresh start."""
        self._conversation.clear()

    def __repr__(self) -> str:
        return f"<{type(self).__name__} role={self.role.value} name={self.name!r}>"
