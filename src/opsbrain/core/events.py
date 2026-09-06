"""Async event bus for inter-agent communication.

Provides a lightweight pub/sub system so agents can emit events and
subscribe to events from other agents without tight coupling.
"""

from __future__ import annotations

import contextlib
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

import structlog

from opsbrain.core.types import AgentMessage, AgentRole

logger = structlog.get_logger(__name__)

# Type alias for event handler callbacks
EventHandler = Callable[[AgentMessage], Coroutine[Any, Any, None]]


class EventBus:
    """Simple async event bus for agent-to-agent messaging.

    Agents publish messages to named channels (typically the recipient's role).
    Subscribers receive copies of all messages on their subscribed channels.

    Usage::

        bus = EventBus()

        # Subscribe
        async def on_alert(msg: AgentMessage):
            print(f"Got alert: {msg.content}")

        bus.subscribe("rca", on_alert)

        # Publish
        await bus.publish(AgentMessage(
            sender=AgentRole.MONITOR,
            recipient=AgentRole.RCA,
            content="Anomaly detected on payment-service",
        ))
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._global_subscribers: list[EventHandler] = []
        self._history: list[AgentMessage] = []
        self._max_history: int = 1000

    # ----- subscribe / unsubscribe -----

    def subscribe(self, channel: str, handler: EventHandler) -> None:
        """Subscribe *handler* to messages on *channel*."""
        self._subscribers[channel].append(handler)
        logger.debug("event_bus.subscribe", channel=channel, handler=handler.__name__)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe *handler* to **all** messages regardless of channel."""
        self._global_subscribers.append(handler)
        logger.debug("event_bus.subscribe_all", handler=handler.__name__)

    def unsubscribe(self, channel: str, handler: EventHandler) -> None:
        """Remove *handler* from *channel*."""
        with contextlib.suppress(ValueError):
            self._subscribers[channel].remove(handler)

    # ----- publish -----

    async def publish(self, message: AgentMessage) -> None:
        """Publish a message to the appropriate channel(s).

        If *message.recipient* is set, the message is delivered to that
        channel. If it is ``None`` the message is treated as a broadcast.
        Global subscribers always receive a copy.
        """
        self._history.append(message)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        logger.info(
            "event_bus.publish",
            sender=message.sender,
            recipient=message.recipient,
            content_preview=message.content[:120],
        )

        # Deliver to targeted channel
        if message.recipient is not None:
            channel = message.recipient.value
            for handler in self._subscribers.get(channel, []):
                await _safe_call(handler, message)

        # Deliver to broadcast subscribers
        for handler in self._global_subscribers:
            await _safe_call(handler, message)

    # ----- query -----

    def get_history(
        self,
        *,
        sender: AgentRole | None = None,
        recipient: AgentRole | None = None,
        limit: int = 50,
    ) -> list[AgentMessage]:
        """Return recent messages, optionally filtered by sender/recipient."""
        msgs = self._history
        if sender is not None:
            msgs = [m for m in msgs if m.sender == sender]
        if recipient is not None:
            msgs = [m for m in msgs if m.recipient == recipient]
        return msgs[-limit:]

    def clear(self) -> None:
        """Clear all subscribers and history (useful for tests)."""
        self._subscribers.clear()
        self._global_subscribers.clear()
        self._history.clear()


async def _safe_call(handler: EventHandler, message: AgentMessage) -> None:
    """Invoke *handler* and swallow exceptions so one bad subscriber
    doesn't break the bus."""
    try:
        await handler(message)
    except Exception:
        logger.exception(
            "event_bus.handler_error",
            handler=handler.__name__,
            message_id=message.id,
        )
