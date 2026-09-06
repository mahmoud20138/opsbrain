"""Elasticsearch / OpenSearch data connector for log exploration.

Queries ELK/OpenSearch clusters for operational logs, error messages,
and stacktraces.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from opsbrain.connectors.base import ConnectorRecord, ConnectorStatus, DataConnector
from opsbrain.core.exceptions import ConnectorError

logger = structlog.get_logger(__name__)


class ElasticsearchConnector(DataConnector):
    """Integrates with Elasticsearch and OpenSearch clusters."""

    name = "elasticsearch"

    def __init__(
        self,
        url: str = "http://localhost:9200",
        *,
        index: str = "logs-*",
        api_key: str | None = None,
        timeout: float = 15.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.url = url.rstrip("/")
        self.index = index
        self.api_key = api_key
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"ApiKey {self.api_key}"
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
            resp = await self._client.get("/_cluster/health")
            return resp.status_code == 200
        except Exception:
            return False

    async def fetch(self, query: str = "*", **kwargs: Any) -> list[ConnectorRecord]:
        """Search logs using query string syntax or structured query DSL.

        Args:
            query: Lucene query string (e.g., 'level:ERROR AND service:payment')
            **kwargs: 'size' (default 50), 'sort'
        """
        if not self._client:
            await self.connect()

        size = kwargs.get("size", 50)
        body = {
            "size": size,
            "query": {
                "query_string": {
                    "query": query,
                }
            },
            "sort": [{"@timestamp": {"order": "desc", "unmapped_type": "boolean"}}],
        }

        assert self._client is not None
        try:
            resp = await self._client.post(f"/{self.index}/_search", json=body)
            resp.raise_for_status()
            data = resp.json()

            records: list[ConnectorRecord] = []
            for hit in data.get("hits", {}).get("hits", []):
                records.append(
                    ConnectorRecord(
                        source=f"elasticsearch:{self.index}",
                        record_type="log",
                        payload=hit.get("_source", {}),
                        timestamp=hit.get("_source", {}).get("@timestamp"),
                    )
                )
            return records
        except Exception as exc:
            logger.error("elasticsearch.fetch_failed", query=query, error=str(exc))
            raise ConnectorError(f"Elasticsearch query failed: {exc}", connector="elasticsearch") from exc
