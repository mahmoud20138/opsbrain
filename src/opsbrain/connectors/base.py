"""Abstract base class for all OpsBrain data connectors.

Connectors ingest operational data (metrics, logs, traces, alerts, tickets)
from enterprise observability and workflow systems.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ConnectorStatus(StrEnum):
    """Operational status of a connector."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class ConnectorRecord(BaseModel):
    """Standardized record returned by data connectors."""

    source: str
    record_type: str = "metric"  # "metric", "log", "ticket", "alert"
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str | None = None


class DataConnector(ABC):
    """Unified interface for all enterprise data connectors.

    Usage::

        async with PrometheusConnector(url="http://prom:9090") as conn:
            records = await conn.fetch("up")
    """

    name: str = "base_connector"

    def __init__(self, **config: Any) -> None:
        self.config = config
        self.status = ConnectorStatus.DISCONNECTED

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection or validate credentials."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Tear down any open connections or sessions."""

    @abstractmethod
    async def fetch(self, query: str = "", **kwargs: Any) -> list[ConnectorRecord]:
        """Fetch operational records matching query."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Test if the upstream service is reachable and functional."""

    async def __aenter__(self) -> DataConnector:
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.disconnect()
