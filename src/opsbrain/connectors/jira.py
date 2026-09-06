"""Jira ticket integration connector.

Creates and updates Jira incident tickets from Coordinator Agent resolution
plans and incident tracking.
"""

from __future__ import annotations

import base64
from typing import Any

import httpx
import structlog

from opsbrain.connectors.base import ConnectorRecord, ConnectorStatus, DataConnector
from opsbrain.core.exceptions import ConnectorError

logger = structlog.get_logger(__name__)


class JiraConnector(DataConnector):
    """Integrates with Atlassian Jira Cloud or Server REST API."""

    name = "jira"

    def __init__(
        self,
        domain: str = "",
        email: str = "",
        api_token: str = "",
        project_key: str = "OPS",
        *,
        timeout: float = 15.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.domain = domain.rstrip("/")
        if not self.domain.startswith("http"):
            self.domain = f"https://{self.domain}"
        self.email = email
        self.api_token = api_token
        self.project_key = project_key
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        auth_str = f"{self.email}:{self.api_token}".encode("ascii")
        b64_auth = base64.b64encode(auth_str).decode("ascii")
        headers = {
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self._client = httpx.AsyncClient(base_url=self.domain, headers=headers, timeout=self.timeout)
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
            resp = await self._client.get("/rest/api/3/myself")
            return resp.status_code == 200
        except Exception:
            return False

    async def fetch(self, query: str = "", **kwargs: Any) -> list[ConnectorRecord]:
        """Fetch Jira issues using JQL."""
        if not self._client:
            await self.connect()

        jql = query or f"project = {self.project_key} order by created DESC"
        assert self._client is not None
        try:
            resp = await self._client.get("/rest/api/3/search", params={"jql": jql, "maxResults": 20})
            resp.raise_for_status()
            data = resp.json()

            records: list[ConnectorRecord] = []
            for issue in data.get("issues", []):
                fields = issue.get("fields", {})
                records.append(
                    ConnectorRecord(
                        source=f"jira:{self.domain}",
                        record_type="ticket",
                        payload={
                            "key": issue.get("key"),
                            "summary": fields.get("summary"),
                            "status": fields.get("status", {}).get("name"),
                            "priority": fields.get("priority", {}).get("name"),
                        },
                    )
                )
            return records
        except Exception as exc:
            logger.error("jira.fetch_failed", error=str(exc))
            raise ConnectorError(f"Jira query failed: {exc}", connector="jira") from exc

    async def create_issue(
        self,
        *,
        summary: str,
        description: str,
        issue_type: str = "Bug",
        priority: str = "High",
    ) -> dict[str, Any]:
        """Create a new incident ticket in Jira."""
        if not self._client:
            await self.connect()

        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}],
                        }
                    ],
                },
                "issuetype": {"name": issue_type},
            }
        }

        assert self._client is not None
        try:
            resp = await self._client.post("/rest/api/3/issue", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.error("jira.create_issue_failed", error=str(exc))
            raise ConnectorError(f"Jira issue creation failed: {exc}", connector="jira") from exc
