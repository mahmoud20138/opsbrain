"""Datadog API metrics and events connector.

Queries Datadog REST API for timeseries metrics, operational monitors,
and system events.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import structlog

from opsbrain.connectors.base import ConnectorRecord, ConnectorStatus, DataConnector
from opsbrain.core.exceptions import ConnectorError

logger = structlog.get_logger(__name__)


class DatadogConnector(DataConnector):
    """Integrates with Datadog REST API."""

    name = "datadog"

    def __init__(
        self,
        api_key: str = "",
        app_key: str = "",
        site: str = "datadoghq.com",
        *,
        timeout: float = 15.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.api_key = api_key
        self.app_key = app_key
        self.site = site
        self.timeout = timeout
        self.base_url = f"https://api.{site}"
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        headers = {
            "DD-API-KEY": self.api_key,
            "DD-APPLICATION-KEY": self.app_key,
            "Content-Type": "application/json",
        }
        self._client = httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=self.timeout)
        self.status = ConnectorStatus.CONNECTED

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self.status = ConnectorStatus.DISCONNECTED

    async def health_check(self) -> bool:
        if not self._client:
            await self.connect()
        try:
            assert self._client is not None
            resp = await self._client.get("/api/v1/validate")
            return resp.status_code == 200
        except Exception:
            return False

    async def fetch(self, query: str = "", **kwargs: Any) -> list[ConnectorRecord]:
        """Fetch timeseries metric points from Datadog.

        Args:
            query: Datadog metric query (e.g. 'avg:system.cpu.user{*}')
        """
        if not self._client:
            await self.connect()

        now = int(time.time())
        from_ts = kwargs.get("from_ts", now - 3600)
        to_ts = kwargs.get("to_ts", now)

        assert self._client is not None
        try:
            resp = await self._client.get(
                "/api/v1/query",
                params={"query": query, "from": from_ts, "to": to_ts},
            )
            resp.raise_for_status()
            data = resp.json()

            records: list[ConnectorRecord] = []
            for series in data.get("series", []):
                records.append(
                    ConnectorRecord(
                        source=f"datadog:{self.site}",
                        record_type="metric",
                        payload={
                            "metric": series.get("metric"),
                            "pointlist": series.get("pointlist", []),
                            "scope": series.get("scope"),
                        },
                    )
                )
            return records
        except Exception as exc:
            logger.error("datadog.fetch_failed", query=query, error=str(exc))
            raise ConnectorError(f"Datadog query failed: {exc}", connector="datadog") from exc
