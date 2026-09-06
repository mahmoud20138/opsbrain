"""Built-in enterprise operations benchmark suite.

Includes ground-truth operational scenarios across IT outages, supply chain
disruptions, and cross-departmental workflow delays.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from opsbrain.eval.scorer import EvaluationScore, PipelineScorer
from opsbrain.orchestrator.engine import OrchestrationEngine, PipelineResult


class BenchmarkScenario(BaseModel):
    """Specification of a reproducible benchmark operational incident."""

    id: str
    name: str
    category: str  # "it_ops", "supply_chain", "business_workflow"
    description: str
    input_data: dict[str, Any]
    expected_root_cause: str
    expected_affected_systems: list[str]
    minimum_passing_score: float = 7.0


class BenchmarkSuite:
    """Manages and executes standard operational benchmark scenarios."""

    def __init__(self) -> None:
        self._scenarios: dict[str, BenchmarkScenario] = {}
        self._load_standard_scenarios()

    def add_scenario(self, scenario: BenchmarkScenario) -> None:
        self._scenarios[scenario.id] = scenario

    def get_scenario(self, scenario_id: str) -> BenchmarkScenario:
        return self._scenarios[scenario_id]

    def list_scenarios(self) -> list[BenchmarkScenario]:
        return list(self._scenarios.values())

    async def run_scenario(
        self,
        scenario_id: str,
        engine: OrchestrationEngine,
        *,
        pipeline_name: str = "incident_response",
    ) -> tuple[PipelineResult, EvaluationScore]:
        """Run a single benchmark scenario through the engine and score it."""
        scenario = self.get_scenario(scenario_id)
        result = await engine.run_pipeline(pipeline_name, data=scenario.input_data)

        scorer = PipelineScorer()
        score = scorer.score_result(
            result,
            expected_root_cause=scenario.expected_root_cause,
            expected_systems=scenario.expected_affected_systems,
        )
        return result, score

    async def run_all(
        self,
        engine: OrchestrationEngine,
        *,
        pipeline_name: str = "incident_response",
    ) -> dict[str, tuple[PipelineResult, EvaluationScore]]:
        """Run all benchmark scenarios."""
        results = {}
        for sc_id in self._scenarios:
            results[sc_id] = await self.run_scenario(sc_id, engine, pipeline_name=pipeline_name)
        return results

    def _load_standard_scenarios(self) -> None:
        # 1. IT Operations: Payment Outage
        self.add_scenario(
            BenchmarkScenario(
                id="it_payment_outage",
                name="Payment Processing Database Pool Exhaustion",
                category="it_ops",
                description="Elevated latency and connection pool starvation on payment gateway following deployment.",
                input_data={
                    "source": "payment-service",
                    "metrics": {
                        "error_rate": 0.18,
                        "latency_p99_ms": 3200,
                        "db_pool_active": 50,
                        "db_pool_max": 50,
                    },
                    "logs": [
                        "ERROR [payment-service] Connection pool exhausted: timeout waiting for connection",
                        "ERROR [payment-service] PostgreSQL connection count reached 100% capacity",
                    ],
                },
                expected_root_cause="Database connection pool exhaustion",
                expected_affected_systems=["payment-service", "database"],
                minimum_passing_score=7.5,
            )
        )

        # 2. Supply Chain: Port Congestion & Component Shortage
        self.add_scenario(
            BenchmarkScenario(
                id="supply_chain_port_delay",
                name="Logistics Hub Port Congestion",
                category="supply_chain",
                description="Shipment delays causing inventory starvation for manufacturing assembly lines.",
                input_data={
                    "source": "global-logistics-erp",
                    "metrics": {
                        "port_dwell_time_days": 12.4,
                        "port_dwell_baseline_days": 2.1,
                        "critical_sku_inventory_days": 1.5,
                        "factory_line_stoppage_risk": 0.92,
                    },
                    "logs": [
                        "WARN [logistics-tracker] Vessel MV-Titan delayed at Port of Rotterdam due to dockworker strike",
                        "ERROR [mfg-erp] Critical micro-controller SKU-774 stock depleted below safety threshold",
                    ],
                },
                expected_root_cause="Port congestion and shipping delays",
                expected_affected_systems=["global-logistics-erp", "mfg-erp"],
                minimum_passing_score=7.0,
            )
        )

        # 3. Cross-Departmental Workflow: Invoice Approval Backlog
        self.add_scenario(
            BenchmarkScenario(
                id="cross_dept_invoice_bottleneck",
                name="Finance Invoice Approval Bottleneck",
                category="business_workflow",
                description="Cross-department approval SLA breach causing vendor relations escalation and late payment penalties.",
                input_data={
                    "source": "finance-procurement-system",
                    "metrics": {
                        "pending_approvals_count": 450,
                        "avg_approval_cycle_days": 18.5,
                        "sla_target_days": 3.0,
                        "penalty_risk_usd": 75000,
                    },
                    "logs": [
                        "WARN [finance-wf] 240 invoices awaiting VP approval exceed 14 days aging",
                        "ERROR [vendor-management] 12 key suppliers placed accounts on credit hold due to unpaid invoices",
                    ],
                },
                expected_root_cause="Manual invoice review backlog in finance approval workflow",
                expected_affected_systems=["finance-procurement-system", "vendor-management"],
                minimum_passing_score=7.0,
            )
        )
