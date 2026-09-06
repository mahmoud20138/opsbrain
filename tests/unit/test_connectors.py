"""Unit tests for enterprise data connectors."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from opsbrain.connectors.base import ConnectorStatus
from opsbrain.connectors.csv_connector import CSVConnector
from opsbrain.connectors.datadog import DatadogConnector
from opsbrain.connectors.elasticsearch import ElasticsearchConnector
from opsbrain.connectors.jira import JiraConnector
from opsbrain.connectors.prometheus import PrometheusConnector
from opsbrain.connectors.webhook import WebhookConnector

# ---------------------------------------------------------------------------
# CSV / JSON Connector Tests
# ---------------------------------------------------------------------------

class TestCSVConnector:
    @pytest.mark.asyncio
    async def test_csv_file_reading(self, tmp_path):
        csv_file = tmp_path / "metrics.csv"
        csv_file.write_text("timestamp,cpu,mem\n2026-09-06T00:00:00Z,45,70\n2026-09-06T00:01:00Z,50,72\n", encoding="utf-8")

        connector = CSVConnector(csv_file)
        await connector.connect()
        assert connector.status == ConnectorStatus.CONNECTED

        records = await connector.fetch()
        assert len(records) == 2
        assert records[0].payload["cpu"] == "45"
        assert records[1].payload["mem"] == "72"

        await connector.disconnect()
        assert connector.status == ConnectorStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_json_file_reading(self, tmp_path):
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps([{"service": "auth", "errors": 5}, {"service": "pay", "errors": 12}]), encoding="utf-8")

        connector = CSVConnector(json_file)
        await connector.connect()
        records = await connector.fetch()
        assert len(records) == 2
        assert records[0].payload["service"] == "auth"


# ---------------------------------------------------------------------------
# Webhook Connector Tests
# ---------------------------------------------------------------------------

class TestWebhookConnector:
    @pytest.mark.asyncio
    async def test_webhook_receive_and_drain(self):
        wh = WebhookConnector()
        await wh.connect()
        assert await wh.health_check() is True

        wh.receive_payload("grafana", {"rule": "HighCPU", "value": 95})
        wh.receive_payload("alertmanager", {"alertname": "PodCrashLoop"})

        records = await wh.fetch(clear=True)
        assert len(records) == 2
        assert records[0].source == "grafana"
        assert records[1].source == "alertmanager"

        # Drained
        records_after = await wh.fetch()
        assert len(records_after) == 0


# ---------------------------------------------------------------------------
# Mocked Remote Connectors Tests
# ---------------------------------------------------------------------------

class TestPrometheusConnector:
    @pytest.mark.asyncio
    async def test_prometheus_fetch(self):
        prom = PrometheusConnector(url="http://prom-test:9090")
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = {
                "status": "success",
                "data": {
                    "resultType": "vector",
                    "result": [
                        {"metric": {"instance": "srv1"}, "value": [1600000000, "1"]}
                    ],
                },
            }
            mock_get.return_value = mock_resp

            await prom.connect()
            records = await prom.fetch("up")
            assert len(records) == 1
            assert records[0].record_type == "metric"
            await prom.disconnect()


class TestDatadogConnector:
    @pytest.mark.asyncio
    async def test_datadog_fetch(self):
        dd = DatadogConnector(api_key="mock-api", app_key="mock-app")
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = {
                "status": "ok",
                "series": [
                    {"metric": "system.cpu.user", "pointlist": [[1600000000, 42.5]]}
                ],
            }
            mock_get.return_value = mock_resp

            await dd.connect()
            records = await dd.fetch("system.cpu.user{*}")
            assert len(records) == 1
            assert records[0].payload["metric"] == "system.cpu.user"
            await dd.disconnect()


class TestElasticsearchConnector:
    @pytest.mark.asyncio
    async def test_elasticsearch_fetch(self):
        es = ElasticsearchConnector(url="http://es-test:9200", index="app-logs")
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = {
                "hits": {
                    "hits": [
                        {"_source": {"message": "NullPointerException in payment handler", "@timestamp": "2026-09-06T08:00:00Z"}}
                    ]
                }
            }
            mock_post.return_value = mock_resp

            await es.connect()
            records = await es.fetch("NullPointerException")
            assert len(records) == 1
            assert "NullPointerException" in records[0].payload["message"]
            await es.disconnect()


class TestJiraConnector:
    @pytest.mark.asyncio
    async def test_jira_fetch_and_create(self):
        jira = JiraConnector(domain="test.atlassian.net", email="a@b.com", api_token="tok")

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_resp_get = MagicMock()
            mock_resp_get.status_code = 200
            mock_resp_get.raise_for_status.return_value = None
            mock_resp_get.json.return_value = {
                "issues": [{"key": "OPS-101", "fields": {"summary": "Payment Outage", "status": {"name": "Open"}}}]
            }
            mock_get.return_value = mock_resp_get

            mock_resp_post = MagicMock()
            mock_resp_post.status_code = 201
            mock_resp_post.raise_for_status.return_value = None
            mock_resp_post.json.return_value = {"id": "10001", "key": "OPS-102"}
            mock_post.return_value = mock_resp_post

            await jira.connect()
            issues = await jira.fetch()
            assert len(issues) == 1
            assert issues[0].payload["key"] == "OPS-101"

            created = await jira.create_issue(summary="Outage", description="Critical bug")
            assert created["key"] == "OPS-102"
            await jira.disconnect()
