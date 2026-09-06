"""Unit tests for evaluation rubrics, benchmarks, and reporting."""

from __future__ import annotations

import pytest

from conftest import MockLLMClient
from opsbrain.agents.coordinator import CoordinatorAgent
from opsbrain.agents.monitor import MonitorAgent
from opsbrain.agents.rca import RCAAgent
from opsbrain.agents.solver import SolverAgent
from opsbrain.core.events import EventBus
from opsbrain.core.types import Incident, IncidentStatus
from opsbrain.eval.benchmarks import BenchmarkSuite
from opsbrain.eval.reporter import generate_markdown_report
from opsbrain.eval.scorer import PipelineScorer
from opsbrain.orchestrator.engine import OrchestrationEngine, PipelineResult
from opsbrain.orchestrator.state import IncidentStateMachine


class TestPipelineScorer:
    def test_scoring_pipeline_result(self):
        inc = Incident(title="Test Incident", status=IncidentStatus.RESOLVED)
        sm = IncidentStateMachine(inc)

        mock_client = MockLLMClient()
        engine = OrchestrationEngine()

        result = PipelineResult(
            pipeline_name="incident_response",
            incident=inc,
            state_machine=sm,
            success=True,
            duration_seconds=1.2,
        )

        from opsbrain.agents.base import AgentOutput
        from opsbrain.core.types import AgentRole

        result.agent_outputs = {
            "monitor": AgentOutput(
                agent_role=AgentRole.MONITOR,
                structured_data={"alerts": [{"title": "DB Spike", "affected_systems": ["database"]}]},
            ),
            "rca": AgentOutput(
                agent_role=AgentRole.RCA,
                structured_data={"rca_report": {"root_cause": "Database connection pool exhaustion", "evidence_chain": ["pool 100%"]}},
            ),
            "solver": AgentOutput(
                agent_role=AgentRole.SOLVER,
                structured_data={"solutions": [{"title": "Scale pool", "steps": ["step 1"], "rollback_plan": "undo"}]},
            ),
            "coordinator": AgentOutput(
                agent_role=AgentRole.COORDINATOR,
                structured_data={"resolution_plan": {"action_items": [{"description": "do it"}], "communication_draft": "status msg"}},
            ),
        }

        scorer = PipelineScorer()
        score = scorer.score_result(
            result,
            expected_root_cause="Database connection pool exhaustion",
            expected_systems=["database"],
        )

        assert score.overall_score >= 8.0
        assert score.root_cause_accuracy >= 9.0
        assert score.solution_actionability >= 8.0
        assert score.risk_awareness >= 8.0


class TestBenchmarkSuite:
    def test_standard_scenarios_loaded(self):
        suite = BenchmarkSuite()
        scenarios = suite.list_scenarios()
        assert len(scenarios) >= 3

        ids = [s.id for s in scenarios]
        assert "it_payment_outage" in ids
        assert "supply_chain_port_delay" in ids
        assert "cross_dept_invoice_bottleneck" in ids

    @pytest.mark.asyncio
    async def test_run_benchmark_scenario(self):
        suite = BenchmarkSuite()
        bus = EventBus()
        engine = OrchestrationEngine(event_bus=bus)

        client = MockLLMClient(response_content="""{
            "anomalies_detected": true,
            "alerts": [{"title": "DB Alert", "affected_systems": ["payment-service", "database"]}],
            "root_cause": "Database connection pool exhaustion in production",
            "solutions": [{"title": "Restart", "steps": ["run"], "rollback_plan": "undo"}],
            "summary": "Resolved",
            "action_items": [{"description": "Action"}],
            "communication_draft": "Fixed"
        }""")

        engine.register_agent(MonitorAgent(llm_client=client, event_bus=bus))
        engine.register_agent(RCAAgent(llm_client=client, event_bus=bus))
        engine.register_agent(SolverAgent(llm_client=client, event_bus=bus))
        engine.register_agent(CoordinatorAgent(llm_client=client, event_bus=bus))

        result, score = await suite.run_scenario("it_payment_outage", engine)
        assert result.success is True
        assert score.overall_score > 7.0


class TestReporter:
    def test_markdown_report_generation(self):
        inc = Incident(title="Test Outage", status=IncidentStatus.RESOLVED)
        sm = IncidentStateMachine(inc)
        result = PipelineResult(
            pipeline_name="incident_response",
            incident=inc,
            state_machine=sm,
            success=True,
            duration_seconds=2.5,
        )

        scorer = PipelineScorer()
        score = scorer.score_result(result)

        benchmark_data = {"test_outage": (result, score)}
        md = generate_markdown_report(benchmark_data)

        assert "# OpsBrain Evaluation & Benchmark Report" in md
        assert "test_outage" in md
        assert "Operational Efficiency Metrics" in md
