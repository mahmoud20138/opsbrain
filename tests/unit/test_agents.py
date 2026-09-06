"""Unit tests for agent base class and specialized agents."""

from __future__ import annotations

import pytest

# Import the mock client from conftest
from conftest import MockLLMClient
from opsbrain.agents.base import Agent, AgentContext, AgentOutput
from opsbrain.agents.memory import AgentMemory, MemoryEntry
from opsbrain.agents.monitor import MonitorAgent
from opsbrain.core.events import EventBus
from opsbrain.core.types import AgentRole

# ---------------------------------------------------------------------------
# Agent Memory tests
# ---------------------------------------------------------------------------

class TestAgentMemory:
    def test_short_term_memory(self):
        mem = AgentMemory(agent_name="test")
        mem.add_turn("user", "Hello")
        mem.add_turn("assistant", "Hi there")

        turns = mem.get_conversation()
        assert len(turns) == 2
        assert turns[0]["role"] == "user"

    def test_long_term_store_and_search(self):
        mem = AgentMemory(agent_name="test")
        mem.store(MemoryEntry(
            category="incident",
            content="Database connection pool exhaustion caused outage",
            tags=["database", "pool", "outage"],
        ))
        mem.store(MemoryEntry(
            category="solution",
            content="Increase connection pool size from 50 to 200",
            tags=["database", "pool", "config"],
        ))
        mem.store(MemoryEntry(
            category="incident",
            content="Network partition between availability zones",
            tags=["network", "availability"],
        ))

        results = mem.search("database connection")
        assert len(results) >= 1
        assert "database" in results[0].content.lower()

    def test_search_with_tag_filter(self):
        mem = AgentMemory(agent_name="test")
        mem.store(MemoryEntry(
            category="incident", content="DB issue", tags=["database"],
        ))
        mem.store(MemoryEntry(
            category="incident", content="Network issue", tags=["network"],
        ))

        results = mem.search("issue", tags=["database"])
        assert all("database" in e.tags for e in results)

    def test_search_with_category_filter(self):
        mem = AgentMemory(agent_name="test")
        mem.store(MemoryEntry(category="incident", content="Problem"))
        mem.store(MemoryEntry(category="solution", content="Fix"))

        results = mem.search("", category="solution")
        # keyword search needs matches, so this might return empty
        # Let's search for the actual content
        results = mem.search("Fix", category="solution")
        assert len(results) == 1

    def test_memory_stats(self):
        mem = AgentMemory(agent_name="test")
        mem.add_turn("user", "test")
        mem.store(MemoryEntry(category="incident", content="test"))

        stats = mem.stats()
        assert stats["short_term_turns"] == 1
        assert stats["long_term_entries"] == 1


# ---------------------------------------------------------------------------
# Agent Context tests
# ---------------------------------------------------------------------------

class TestAgentContext:
    def test_context_creation(self):
        ctx = AgentContext(
            incident_id="INC-001",
            data={"source": "payment-service"},
        )
        assert ctx.incident_id == "INC-001"
        assert ctx.get("source") == "payment-service"

    def test_context_set_get(self):
        ctx = AgentContext()
        ctx.set("key", "value")
        assert ctx.get("key") == "value"
        assert ctx.get("missing", "default") == "default"


# ---------------------------------------------------------------------------
# Agent Output tests
# ---------------------------------------------------------------------------

class TestAgentOutput:
    def test_output_creation(self):
        output = AgentOutput(
            agent_role=AgentRole.MONITOR,
            content="Analysis complete",
            confidence=0.85,
        )
        assert output.agent_role == AgentRole.MONITOR
        assert output.confidence == 0.85


# ---------------------------------------------------------------------------
# Monitor Agent tests
# ---------------------------------------------------------------------------

class TestMonitorAgent:
    @pytest.mark.asyncio
    async def test_monitor_processes_data(self):
        """Monitor Agent should process data and return an output."""
        client = MockLLMClient(response_content="""{
            "anomalies_detected": true,
            "alerts": [
                {
                    "title": "High Error Rate",
                    "description": "Error rate spike detected",
                    "severity": "high",
                    "affected_systems": ["payment-service"],
                    "evidence": ["error_rate: 15%"]
                }
            ],
            "summary": "Anomaly detected"
        }""")

        agent = MonitorAgent(llm_client=client)
        ctx = AgentContext(data={
            "source": "payment-service",
            "metrics": {"error_rate": 0.15},
        })

        output = await agent.process(ctx)

        assert output.agent_role == AgentRole.MONITOR
        assert output.structured_data.get("anomalies_detected") is True
        assert len(output.structured_data.get("alerts", [])) >= 1
        assert client.call_count == 1

    @pytest.mark.asyncio
    async def test_monitor_handles_no_anomalies(self):
        """Monitor Agent should handle normal data gracefully."""
        client = MockLLMClient(response_content="""{
            "anomalies_detected": false,
            "alerts": [],
            "summary": "All systems operating normally"
        }""")

        agent = MonitorAgent(llm_client=client)
        ctx = AgentContext(data={"source": "healthy-service", "metrics": {"error_rate": 0.001}})

        output = await agent.process(ctx)
        assert output.structured_data.get("anomalies_detected") is False

    @pytest.mark.asyncio
    async def test_monitor_emits_to_event_bus(self):
        """Monitor should publish alerts to the event bus."""
        client = MockLLMClient(response_content="""{
            "anomalies_detected": true,
            "alerts": [{"title": "Test", "description": "test", "severity": "high", "affected_systems": [], "evidence": []}],
            "summary": "test"
        }""")

        bus = EventBus()
        received = []

        async def on_message(msg):
            received.append(msg)

        bus.subscribe("rca", on_message)

        agent = MonitorAgent(llm_client=client, event_bus=bus)
        ctx = AgentContext(data={"source": "test", "metrics": {}})
        await agent.process(ctx)

        assert len(received) >= 1
