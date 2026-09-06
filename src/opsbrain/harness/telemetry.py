"""Telemetry — token usage, cost, and latency tracking for LLM calls.

Collects per-request metrics and aggregates them by provider, model,
and agent role for reporting and cost governance.
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import structlog

from opsbrain.core.types import LLMResponse

logger = structlog.get_logger(__name__)

# Approximate per-token costs in USD (input / output)
# These are rough estimates — update as pricing changes.
_COST_PER_1K_TOKENS: dict[str, tuple[float, float]] = {
    # (input_cost_per_1k, output_cost_per_1k)
    "gpt-4o": (0.0025, 0.01),
    "gpt-4o-mini": (0.00015, 0.0006),
    "o3": (0.01, 0.04),
    "o4-mini": (0.0011, 0.0044),
    "claude-sonnet-4-20250514": (0.003, 0.015),
    "claude-opus-4-20250514": (0.015, 0.075),
    "gemini-2.5-pro": (0.00125, 0.01),
    "gemini-2.5-flash": (0.00015, 0.001),
    # Local models are free
    "llama3.1": (0.0, 0.0),
    "mistral": (0.0, 0.0),
}


@dataclass
class RequestMetrics:
    """Metrics captured for a single LLM request."""

    provider: str = ""
    model: str = ""
    agent_role: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    success: bool = True
    error: str = ""
    timestamp: float = field(default_factory=time.time)


class TelemetryCollector:
    """Collects and aggregates LLM usage telemetry.

    Usage::

        telemetry = TelemetryCollector()

        async with telemetry.track("openai", "gpt-4o", agent_role="rca") as tracker:
            response = await client.complete(request)
            tracker.record_response(response)

        print(telemetry.get_summary())
    """

    def __init__(self) -> None:
        self._records: list[RequestMetrics] = []
        self._cost_by_provider: dict[str, float] = defaultdict(float)
        self._cost_by_agent: dict[str, float] = defaultdict(float)
        self._total_tokens: int = 0
        self._total_cost: float = 0.0
        self._request_count: int = 0

    @asynccontextmanager
    async def track(
        self,
        provider: str,
        model: str,
        *,
        agent_role: str = "",
    ) -> AsyncIterator[RequestTracker]:
        """Context manager that times a request and records its metrics.

        Args:
            provider: Provider name (e.g., ``"openai"``).
            model: Model name (e.g., ``"gpt-4o"``).
            agent_role: The agent role making the request.

        Yields:
            A :class:`RequestTracker` to record the response.
        """
        tracker = RequestTracker(provider=provider, model=model, agent_role=agent_role)
        start = time.perf_counter()
        try:
            yield tracker
        except Exception as exc:
            tracker.metrics.success = False
            tracker.metrics.error = str(exc)
            raise
        finally:
            tracker.metrics.latency_ms = (time.perf_counter() - start) * 1000
            self._ingest(tracker.metrics)

    def _ingest(self, metrics: RequestMetrics) -> None:
        """Record a completed request's metrics."""
        self._records.append(metrics)
        self._request_count += 1
        self._total_tokens += metrics.total_tokens
        self._total_cost += metrics.cost_usd
        self._cost_by_provider[metrics.provider] += metrics.cost_usd
        if metrics.agent_role:
            self._cost_by_agent[metrics.agent_role] += metrics.cost_usd

        logger.info(
            "telemetry.request",
            provider=metrics.provider,
            model=metrics.model,
            agent=metrics.agent_role,
            tokens=metrics.total_tokens,
            cost=f"${metrics.cost_usd:.6f}",
            latency=f"{metrics.latency_ms:.0f}ms",
            success=metrics.success,
        )

    def get_summary(self) -> dict[str, Any]:
        """Return an aggregate summary of all collected telemetry."""
        return {
            "total_requests": self._request_count,
            "total_tokens": self._total_tokens,
            "total_cost_usd": round(self._total_cost, 6),
            "cost_by_provider": dict(self._cost_by_provider),
            "cost_by_agent": dict(self._cost_by_agent),
            "average_latency_ms": (
                sum(r.latency_ms for r in self._records) / len(self._records)
                if self._records
                else 0.0
            ),
            "error_rate": (
                sum(1 for r in self._records if not r.success) / len(self._records)
                if self._records
                else 0.0
            ),
        }

    def get_records(self, *, limit: int = 100) -> list[RequestMetrics]:
        """Return the most recent request records."""
        return self._records[-limit:]

    def reset(self) -> None:
        """Clear all collected telemetry."""
        self._records.clear()
        self._cost_by_provider.clear()
        self._cost_by_agent.clear()
        self._total_tokens = 0
        self._total_cost = 0.0
        self._request_count = 0


class RequestTracker:
    """Companion object yielded by :meth:`TelemetryCollector.track`.

    Call :meth:`record_response` after the LLM call completes to capture
    token usage and cost.
    """

    def __init__(self, provider: str, model: str, agent_role: str = "") -> None:
        self.metrics = RequestMetrics(
            provider=provider,
            model=model,
            agent_role=agent_role,
        )

    def record_response(self, response: LLMResponse) -> None:
        """Extract usage stats from the response and estimate cost."""
        self.metrics.prompt_tokens = response.usage.prompt_tokens
        self.metrics.completion_tokens = response.usage.completion_tokens
        self.metrics.total_tokens = response.usage.total_tokens

        # Use provider-reported cost if available, else estimate
        if response.usage.cost_usd is not None:
            self.metrics.cost_usd = response.usage.cost_usd
        else:
            self.metrics.cost_usd = estimate_cost(
                model=response.model or self.metrics.model,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
            )


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate the USD cost of a request based on known per-token prices.

    Args:
        model: Model name.
        prompt_tokens: Number of input tokens.
        completion_tokens: Number of output tokens.

    Returns:
        Estimated cost in USD.
    """
    # Try exact match, then prefix match
    costs = _COST_PER_1K_TOKENS.get(model)
    if costs is None:
        for key, val in _COST_PER_1K_TOKENS.items():
            if model.startswith(key):
                costs = val
                break
    if costs is None:
        return 0.0

    input_cost, output_cost = costs
    return (prompt_tokens / 1000 * input_cost) + (completion_tokens / 1000 * output_cost)
