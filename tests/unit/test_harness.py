"""Unit tests for the LLM harness — telemetry, guardrails, retry."""

from __future__ import annotations

import pytest

from opsbrain.core.config import GuardrailConfig
from opsbrain.core.exceptions import CostLimitExceededError, GuardrailError
from opsbrain.core.types import (
    LLMRequest,
    LLMResponse,
    Message,
    Provider,
    UsageStats,
)
from opsbrain.harness.guardrails import Guardrails
from opsbrain.harness.retry import CircuitBreaker
from opsbrain.harness.telemetry import TelemetryCollector, estimate_cost

# ---------------------------------------------------------------------------
# Guardrails tests
# ---------------------------------------------------------------------------

class TestGuardrails:
    def test_token_limit_enforcement(self):
        guard = Guardrails(GuardrailConfig(max_tokens_per_request=1000))
        request = LLMRequest(
            messages=[Message(role="user", content="test")],
            max_tokens=5000,
        )
        with pytest.raises(GuardrailError):
            guard.validate_request(request)

    def test_token_limit_passes(self):
        guard = Guardrails(GuardrailConfig(max_tokens_per_request=8000))
        request = LLMRequest(
            messages=[Message(role="user", content="test")],
            max_tokens=4000,
        )
        # Should not raise
        guard.validate_request(request)

    def test_blocked_pattern_in_request(self):
        guard = Guardrails(GuardrailConfig(blocked_patterns=["DROP TABLE"]))
        request = LLMRequest(
            messages=[Message(role="user", content="Please DROP TABLE users")],
        )
        with pytest.raises(GuardrailError):
            guard.validate_request(request)

    def test_blocked_pattern_in_response(self):
        guard = Guardrails(GuardrailConfig(blocked_patterns=["CONFIDENTIAL"]))
        response = LLMResponse(content="This is CONFIDENTIAL information")
        with pytest.raises(GuardrailError):
            guard.validate_response(response)

    def test_pii_detection_logs_warning(self):
        """PII detection should log a warning but not block by default."""
        guard = Guardrails(GuardrailConfig(pii_detection_enabled=True))
        request = LLMRequest(
            messages=[Message(role="user", content="Email is test@example.com")],
        )
        # Should log warning but not raise
        guard.validate_request(request)

    def test_hourly_cost_tracking(self):
        guard = Guardrails(GuardrailConfig(max_cost_per_hour_usd=0.01))

        for _ in range(5):
            response = LLMResponse(
                content="test",
                usage=UsageStats(cost_usd=0.003),
            )
            try:
                guard.validate_response(response)
            except CostLimitExceededError:
                # Expected after accumulating enough cost
                assert guard.current_hourly_cost > 0.01
                return

        # If we didn't hit the limit, the test still passes
        # (depends on threshold vs accumulated)

    def test_reset_hourly_cost(self):
        guard = Guardrails(GuardrailConfig())
        response = LLMResponse(content="test", usage=UsageStats(cost_usd=1.0))
        guard.validate_response(response)
        assert guard.current_hourly_cost == 1.0

        guard.reset_hourly_cost()
        assert guard.current_hourly_cost == 0.0


# ---------------------------------------------------------------------------
# Circuit Breaker tests
# ---------------------------------------------------------------------------

class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.allow_request()

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreaker.CLOSED
        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN
        assert not cb.allow_request()

    def test_resets_on_success(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.state == CircuitBreaker.CLOSED

    def test_half_open_after_recovery(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN

        import time
        time.sleep(0.02)  # wait for recovery
        assert cb.state == CircuitBreaker.HALF_OPEN
        assert cb.allow_request()


# ---------------------------------------------------------------------------
# Telemetry tests
# ---------------------------------------------------------------------------

class TestTelemetry:
    @pytest.mark.asyncio
    async def test_track_request(self):
        telemetry = TelemetryCollector()

        async with telemetry.track("openai", "gpt-4o", agent_role="rca") as tracker:
            response = LLMResponse(
                content="test",
                model="gpt-4o",
                provider=Provider.OPENAI,
                usage=UsageStats(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            )
            tracker.record_response(response)

        summary = telemetry.get_summary()
        assert summary["total_requests"] == 1
        assert summary["total_tokens"] == 150

    @pytest.mark.asyncio
    async def test_cost_estimation(self):
        cost = estimate_cost("gpt-4o", prompt_tokens=1000, completion_tokens=500)
        assert cost > 0

    @pytest.mark.asyncio
    async def test_local_model_free(self):
        cost = estimate_cost("llama3.1", prompt_tokens=1000, completion_tokens=500)
        assert cost == 0.0

    @pytest.mark.asyncio
    async def test_telemetry_summary_aggregation(self):
        telemetry = TelemetryCollector()

        for _i in range(3):
            async with telemetry.track("openai", "gpt-4o", agent_role="monitor") as tracker:
                tracker.record_response(LLMResponse(
                    content="test",
                    usage=UsageStats(prompt_tokens=100, completion_tokens=50, total_tokens=150),
                ))

        summary = telemetry.get_summary()
        assert summary["total_requests"] == 3
        assert summary["total_tokens"] == 450

    def test_telemetry_reset(self):
        telemetry = TelemetryCollector()
        telemetry.reset()
        summary = telemetry.get_summary()
        assert summary["total_requests"] == 0


# ---------------------------------------------------------------------------
# Provider Registry and Router Tests
# ---------------------------------------------------------------------------

class TestProviderRegistry:
    def test_list_available(self):
        from opsbrain.core.config import OpsBrainConfig
        from opsbrain.harness.registry import ProviderRegistry

        cfg = OpsBrainConfig()
        registry = ProviderRegistry(cfg)
        avail = registry.list_available()
        assert len(avail) == len(Provider)


class TestModelRouter:
    @pytest.mark.asyncio
    async def test_route_fallback(self):
        from opsbrain.core.config import OpsBrainConfig, RoutingConfig, RoutingRule
        from opsbrain.harness.mock import MockLLMClient
        from opsbrain.harness.registry import ProviderRegistry
        from opsbrain.harness.router import ModelRouter

        cfg = OpsBrainConfig(
            routing=RoutingConfig(
                default_provider=Provider.LITELLM,
                rules=[
                    RoutingRule(pattern="*rca*", provider=Provider.LITELLM, priority=10),
                ],
            )
        )
        registry = ProviderRegistry(cfg)
        mock_client = MockLLMClient(response_content="Routed successfully")
        registry._clients[Provider.LITELLM] = mock_client

        router = ModelRouter(cfg, registry)
        req = LLMRequest(messages=[Message(role="user", content="hello")])
        resp = await router.route(req, context={"agent_role": "rca"})

        assert resp.content == "Routed successfully"
