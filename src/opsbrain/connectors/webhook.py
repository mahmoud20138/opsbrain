"""Generic webhook connector for push-based alert ingestion.

Processes incoming JSON webhook alerts from Alertmanager, Grafana, PagerDuty,
or custom monitoring webhooks.
"""

from __future__ import annotations

from typing import Any

import structlog

from opsbrain.connectors.base import ConnectorRecord, ConnectorStatus, DataConnector

logger = structlog.get_logger(__name__)


class WebhookConnector(DataConnector):
    """Parses and ingests push alerts received via HTTP webhooks."""

    name = "webhook"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._buffer: list[ConnectorRecord] = []

    async def connect(self) -> None:
        self.status = ConnectorStatus.CONNECTED

    async def disconnect(self) -> None:
        self.status = ConnectorStatus.DISCONNECTED

    async def health_check(self) -> bool:
        return self.status == ConnectorStatus.CONNECTED

    def receive_payload(self, source: str, payload: dict[str, Any]) -> ConnectorRecord:
        """Receive and normalize an incoming webhook payload into a ConnectorRecord."""
        record = ConnectorRecord(
            source=source,
            record_type="webhook_alert",
            payload=payload,
        )
        self._buffer.append(record)
        logger.info("webhook.received_alert", source=source, buffer_size=len(self._buffer))
        return record

    async def fetch(self, query: str = "", **kwargs: Any) -> list[ConnectorRecord]:
        """Drain buffered webhook records."""
        items = list(self._buffer)
        if kwargs.get("clear", True):
            self._buffer.clear()
        return items
