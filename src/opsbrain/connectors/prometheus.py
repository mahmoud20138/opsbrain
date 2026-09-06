"""Prometheus metrics data connector.

Executes PromQL instant and range queries against Prometheus servers or
VictoriaMetrics / Cortex / Thanos compatible endpoints.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from opsbrain.connectors.base import ConnectorRecord, ConnectorStatus, DataConnector
from opsbrain.core.exceptions import ConnectorError

logger = structlog.get_logger(__name__)


class PrometheusConnector(DataConnector):
    """Queries Prometheus metrics using PromQL."""

    name = "prometheus"

    def __init__(
        self,
        url: str = "http://localhost:9090",
        *,
        auth_token: str | None = None,
        timeout: float = 15.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.url = url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        self._client = httpx.AsyncClient(base_url=self.url, headers=headers, timeout=self.timeout)
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
            resp = await self._client.get("/-/healthy")
            return resp.status_code == 200
        except Exception:
            return False

    async def fetch(self, query: str = "up", **kwargs: Any) -> list[ConnectorRecord]:
        """Execute a PromQL query.

        Args:
            query: PromQL expression string (e.g. 'sum(rate(http_requests_total[5m]))')
            **kwargs: Can pass 'time' or 'step' if needed.
        """
        if not self._client:
            await self.connect()

        assert self._client is not None
        try:
            resp = await self._client.get("/api/v1/query", params={"query": query})
            resp.raise_for_status()
            data = resp.json()

            records: list[ConnectorRecord] = []
            if data.get("status") == "success":
                result = data.get("data", {}).get("result", [])
                for item in result:
                    records.append(
                        ConnectorRecord(
                            source=self.url,
                            record_type="metric",
                            payload={
                                "metric": item.get("metric", {}),
                                "value": item.get("value", []),
                            },
                        )
                    )
            return records
        except Exception as exc:
            logger.error("prometheus.fetch_failed", query=query, error=str(exc))
            raise ConnectorError(f"Prometheus query failed: {exc}", connector="prometheus") from exc
