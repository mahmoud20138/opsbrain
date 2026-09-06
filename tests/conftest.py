"""Shared test fixtures for OpsBrain."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opsbrain.core.config import OpsBrainConfig, ProviderConfig, load_config
from opsbrain.core.events import EventBus
from opsbrain.core.types import (
    LLMRequest,
    LLMResponse,
    Message,
    Provider,
    UsageStats,
)
from opsbrain.harness.base import LLMClient

# ---------------------------------------------------------------------------
# Mock LLM Client
# ---------------------------------------------------------------------------

class MockLLMClient(LLMClient):
    """A mock LLM client that returns configurable canned responses."""

    provider = Provider.LITELLM
    display_name = "Mock Provider"

    def __init__(self, *, response_content: str = "Mock response") -> None:
        self._response_content = response_content
        self.call_count = 0
        self.last_request: LLMRequest | None = None

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.call_count += 1
        self.last_request = request
        return LLMResponse(
            content=self._response_content,
            model="mock-model",
            provider=Provider.LITELLM,
            usage=UsageStats(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
            ),
        )

    async def complete_with_tools(self, request, tools):
        return await self.complete(request)

    async def stream(self, request):
        yield self._response_content

    def supports_feature(self, feature: str) -> bool:
        return True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_client() -> MockLLMClient:
    """A mock LLM client for testing agents without real API calls."""
    return MockLLMClient()


@pytest.fixture
def mock_client_with_json() -> MockLLMClient:
    """A mock client that returns JSON-formatted monitor output."""
    return MockLLMClient(response_content="""{
    "anomalies_detected": true,
    "alerts": [
        {
            "title": "High Error Rate on Payment Service",
            "description": "Error rate at 15% exceeds critical threshold of 5%",
            "severity": "critical",
            "affected_systems": ["payment-service", "database"],
            "evidence": ["error_rate: 0.15 vs baseline 0.002", "DB pool 96% utilized"]
        }
    ],
    "summary": "Critical anomalies detected in payment service"
}""")


@pytest.fixture
def event_bus() -> EventBus:
    """A fresh EventBus for testing."""
    return EventBus()


@pytest.fixture
def sample_config() -> OpsBrainConfig:
    """A default OpsBrainConfig for testing."""
    return OpsBrainConfig()


@pytest.fixture
def sample_incident_data() -> dict:
    """Sample incident data for testing."""
    return {
        "source": "payment-service",
        "metrics": {
            "error_rate": 0.15,
            "latency_p99_ms": 2500,
            "cpu_usage_percent": 78,
            "memory_usage_percent": 92,
        },
        "logs": [
            "ERROR Connection pool exhausted",
            "WARN Slow query detected: 2340ms",
            "ERROR Request timeout for order #ORD-29481",
        ],
    }
