"""Unit tests for the LLM harness — types, config, events, and core."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from opsbrain.core.config import (
    OpsBrainConfig,
    generate_default_config,
    load_config,
)
from opsbrain.core.events import EventBus
from opsbrain.core.exceptions import (
    ConfigFileNotFoundError,
    OpsBrainError,
    ProviderError,
)
from opsbrain.core.types import (
    AgentMessage,
    AgentRole,
    Alert,
    Incident,
    IncidentStatus,
    LLMRequest,
    LLMResponse,
    Message,
    Provider,
    Severity,
    UsageStats,
)

# ---------------------------------------------------------------------------
# Types tests
# ---------------------------------------------------------------------------

class TestTypes:
    def test_provider_enum(self):
        assert Provider.OPENAI == "openai"
        assert Provider.GEMINI == "gemini"
        assert Provider.ANTHROPIC == "anthropic"

    def test_severity_enum(self):
        assert Severity.CRITICAL == "critical"
        assert Severity("high") == Severity.HIGH

    def test_llm_request_creation(self):
        req = LLMRequest(
            messages=[Message(role="user", content="Hello")],
            temperature=0.5,
        )
        assert len(req.messages) == 1
        assert req.temperature == 0.5
        assert req.model is None

    def test_llm_response_creation(self):
        resp = LLMResponse(
            content="Hello back",
            model="gpt-4o",
            provider=Provider.OPENAI,
            usage=UsageStats(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )
        assert resp.content == "Hello back"
        assert resp.usage.total_tokens == 15

    def test_alert_creation(self):
        alert = Alert(
            title="Test Alert",
            description="Something went wrong",
            severity=Severity.HIGH,
            affected_systems=["service-a"],
        )
        assert alert.title == "Test Alert"
        assert alert.severity == Severity.HIGH
        assert len(alert.id) == 16  # uuid hex[:16]

    def test_incident_lifecycle(self):
        inc = Incident(title="Test Incident")
        assert inc.status == IncidentStatus.DETECTED
        inc.status = IncidentStatus.ANALYZING
        assert inc.status == IncidentStatus.ANALYZING

    def test_agent_message(self):
        msg = AgentMessage(
            sender=AgentRole.MONITOR,
            recipient=AgentRole.RCA,
            content="Alert detected",
        )
        assert msg.sender == AgentRole.MONITOR
        assert msg.recipient == AgentRole.RCA


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

class TestConfig:
    def test_default_config(self):
        cfg = OpsBrainConfig()
        assert cfg.log_level == "INFO"
        assert Provider.OPENAI in cfg.providers

    def test_load_config_no_file(self):
        """Loading with no file should return defaults."""
        cfg = load_config()
        assert isinstance(cfg, OpsBrainConfig)

    def test_load_config_missing_file_raises(self):
        with pytest.raises(ConfigFileNotFoundError):
            load_config("/nonexistent/path/config.yaml")

    def test_load_config_from_yaml(self, tmp_path):
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("log_level: DEBUG\n", encoding="utf-8")

        cfg = load_config(config_file)
        assert cfg.log_level == "DEBUG"

    def test_load_config_with_overrides(self):
        cfg = load_config(overrides={"log_level": "WARNING"})
        assert cfg.log_level == "WARNING"

    def test_generate_default_config(self):
        yaml_str = generate_default_config()
        assert "log_level" in yaml_str
        assert isinstance(yaml_str, str)


# ---------------------------------------------------------------------------
# Events tests
# ---------------------------------------------------------------------------

class TestEventBus:
    @pytest.mark.asyncio
    async def test_publish_subscribe(self):
        bus = EventBus()
        received: list[AgentMessage] = []

        async def handler(msg: AgentMessage):
            received.append(msg)

        bus.subscribe("rca", handler)

        msg = AgentMessage(
            sender=AgentRole.MONITOR,
            recipient=AgentRole.RCA,
            content="Test message",
        )
        await bus.publish(msg)

        assert len(received) == 1
        assert received[0].content == "Test message"

    @pytest.mark.asyncio
    async def test_global_subscriber(self):
        bus = EventBus()
        received: list[AgentMessage] = []

        async def handler(msg: AgentMessage):
            received.append(msg)

        bus.subscribe_all(handler)

        msg = AgentMessage(
            sender=AgentRole.MONITOR,
            recipient=AgentRole.RCA,
            content="Broadcast test",
        )
        await bus.publish(msg)

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_history(self):
        bus = EventBus()

        for i in range(5):
            await bus.publish(AgentMessage(
                sender=AgentRole.MONITOR,
                content=f"Message {i}",
            ))

        history = bus.get_history(limit=3)
        assert len(history) == 3
        assert history[-1].content == "Message 4"

    @pytest.mark.asyncio
    async def test_handler_error_doesnt_break_bus(self):
        bus = EventBus()
        good_received: list[AgentMessage] = []

        async def bad_handler(msg: AgentMessage):
            raise ValueError("Boom!")

        async def good_handler(msg: AgentMessage):
            good_received.append(msg)

        bus.subscribe_all(bad_handler)
        bus.subscribe_all(good_handler)

        msg = AgentMessage(sender=AgentRole.MONITOR, content="test")
        await bus.publish(msg)

        # Good handler should still receive the message
        assert len(good_received) == 1


# ---------------------------------------------------------------------------
# Exceptions tests
# ---------------------------------------------------------------------------

class TestExceptions:
    def test_base_error(self):
        err = OpsBrainError("test error", details={"key": "value"})
        assert str(err) == "test error"
        assert err.details == {"key": "value"}

    def test_provider_error(self):
        err = ProviderError("API failed", provider="openai", model="gpt-4o")
        assert err.provider == "openai"
        assert err.model == "gpt-4o"
