"""Unit tests for the orchestration layer — state machine, pipelines, engine, scheduler."""

from __future__ import annotations

import asyncio

import pytest

from conftest import MockLLMClient
from opsbrain.agents.coordinator import CoordinatorAgent
from opsbrain.agents.monitor import MonitorAgent
from opsbrain.agents.rca import RCAAgent
from opsbrain.agents.solver import SolverAgent
from opsbrain.core.events import EventBus
from opsbrain.core.types import AgentRole, Incident, IncidentStatus
from opsbrain.orchestrator.engine import OrchestrationEngine, PipelineResult
from opsbrain.orchestrator.pipeline import Pipeline, PipelineDefinition, PipelineStep
from opsbrain.orchestrator.scheduler import PeriodicScheduler
from opsbrain.orchestrator.state import IncidentStateMachine, InvalidStateTransitionError

# ---------------------------------------------------------------------------
# State Machine Tests
# ---------------------------------------------------------------------------

class TestIncidentStateMachine:
    def test_state_machine_init(self):
        inc = Incident(title="Outage", status=IncidentStatus.DETECTED)
        sm = IncidentStateMachine(inc)
        assert sm.current_state == IncidentStatus.DETECTED
        assert len(sm.get_history()) == 1
        assert sm.get_history()[0].action == "incident_created"

    def test_valid_transitions(self):
        inc = Incident(title="Outage", status=IncidentStatus.DETECTED)
        sm = IncidentStateMachine(inc)

        # DETECTED -> ANALYZING
        tr = sm.transition(IncidentStatus.ANALYZING, actor="rca", reason="Investigating")
        assert tr.from_state == IncidentStatus.DETECTED
        assert tr.to_state == IncidentStatus.ANALYZING
        assert sm.current_state == IncidentStatus.ANALYZING

        # ANALYZING -> DIAGNOSED
        sm.transition(IncidentStatus.DIAGNOSED, actor="rca", reason="Found cause")
        assert sm.current_state == IncidentStatus.DIAGNOSED

        # DIAGNOSED -> RESOLVING
        sm.transition(IncidentStatus.RESOLVING, actor="solver", reason="Executing solution")
        assert sm.current_state == IncidentStatus.RESOLVING

        # RESOLVING -> RESOLVED
        sm.transition(IncidentStatus.RESOLVED, actor="coordinator", reason="All clear")
        assert sm.current_state == IncidentStatus.RESOLVED
        assert inc.resolved_at is not None

        # RESOLVED -> CLOSED
        sm.transition(IncidentStatus.CLOSED, actor="lead", reason="Postmortem complete")
        assert sm.current_state == IncidentStatus.CLOSED

    def test_invalid_transition_raises(self):
        inc = Incident(title="Outage", status=IncidentStatus.DETECTED)
        sm = IncidentStateMachine(inc)

        # Cannot jump from DETECTED directly to RESOLVED
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            sm.transition(IncidentStatus.RESOLVED)
        assert exc_info.value.from_state == IncidentStatus.DETECTED
        assert exc_info.value.to_state == IncidentStatus.RESOLVED

    def test_transition_hooks(self):
        inc = Incident(title="Outage", status=IncidentStatus.DETECTED)
        sm = IncidentStateMachine(inc)

        called = []
        sm.add_transition_hook(lambda tr: called.append(tr.to_state))
        sm.transition(IncidentStatus.ANALYZING)

        assert called == [IncidentStatus.ANALYZING]


# ---------------------------------------------------------------------------
# Pipeline Tests
# ---------------------------------------------------------------------------

class TestPipeline:
    def test_builtin_pipelines(self):
        ir = Pipeline.incident_response()
        assert ir.name == "incident_response"
        assert len(ir.steps) == 4

        qt = Pipeline.quick_triage()
        assert qt.name == "quick_triage"
        assert len(qt.steps) == 2

        fc = Pipeline.full_cycle_eval()
        assert len(fc.steps) == 5

    def test_step_conditional_execution(self):
        step_always = PipelineStep(name="always", agent_role=AgentRole.MONITOR)
        assert step_always.should_execute({}) is True

        step_conditional = PipelineStep(
            name="only_on_alerts",
            agent_role=AgentRole.RCA,
            condition=lambda d: len(d.get("alerts", [])) > 0,
        )
        assert step_conditional.should_execute({}) is False
        assert step_conditional.should_execute({"alerts": ["spike"]}) is True


# ---------------------------------------------------------------------------
# Orchestration Engine Tests
# ---------------------------------------------------------------------------

class TestOrchestrationEngine:
    @pytest.mark.asyncio
    async def test_run_incident_response_pipeline(self):
        bus = EventBus()
        engine = OrchestrationEngine(event_bus=bus)

        client = MockLLMClient(response_content="""{
            "anomalies_detected": true,
            "alerts": [{"title": "Spike", "severity": "high"}],
            "root_cause": "Memory leak",
            "solutions": [{"title": "Restart", "steps": ["kill -9"], "risk_level": "low"}],
            "summary": "Coordinated",
            "action_items": [{"description": "Restart", "assignee": "Dev"}]
        }""")

        engine.register_agent(MonitorAgent(llm_client=client, event_bus=bus))
        engine.register_agent(RCAAgent(llm_client=client, event_bus=bus))
        engine.register_agent(SolverAgent(llm_client=client, event_bus=bus))
        engine.register_agent(CoordinatorAgent(llm_client=client, event_bus=bus))

        result = await engine.run_pipeline("incident_response", data={"source": "api"})

        assert result.success is True
        assert len(result.step_records) == 4
        assert result.incident.status == IncidentStatus.RESOLVED
        assert "monitor" in result.agent_outputs
        assert "rca" in result.agent_outputs
        assert "solver" in result.agent_outputs
        assert "coordinator" in result.agent_outputs

    @pytest.mark.asyncio
    async def test_checkpoint_rejection(self):
        bus = EventBus()

        async def reject_checkpoint(step, ctx):
            if step.agent_role == AgentRole.SOLVER:
                return False
            return True

        engine = OrchestrationEngine(event_bus=bus, checkpoint_handler=reject_checkpoint)
        client = MockLLMClient(response_content="{}")

        engine.register_agent(MonitorAgent(llm_client=client, event_bus=bus))
        engine.register_agent(RCAAgent(llm_client=client, event_bus=bus))
        engine.register_agent(SolverAgent(llm_client=client, event_bus=bus))

        result = await engine.run_pipeline("incident_response", data={})
        # Should stop before solver
        statuses = [s.status for s in result.step_records]
        assert "rejected_by_checkpoint" in statuses


# ---------------------------------------------------------------------------
# Periodic Scheduler Tests
# ---------------------------------------------------------------------------

class TestPeriodicScheduler:
    @pytest.mark.asyncio
    async def test_scheduler_run_once(self):
        scheduler = PeriodicScheduler()
        counter = 0

        async def increment():
            nonlocal counter
            counter += 1

        scheduler.add_task("task_1", "Test Task", 60.0, increment)
        await scheduler.run_once("task_1")

        assert counter == 1
        tasks = scheduler.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].run_count == 1

    @pytest.mark.asyncio
    async def test_scheduler_start_and_stop(self):
        scheduler = PeriodicScheduler()
        counter = 0

        async def increment():
            nonlocal counter
            counter += 1

        scheduler.add_task("task_fast", "Fast Task", 0.05, increment)
        await scheduler.start()
        await asyncio.sleep(0.12)
        await scheduler.stop()

        assert counter >= 1
