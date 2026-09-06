"""Integration tests for real-world enterprise datasets and demo execution."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from examples.real_data_pipeline_demo import (
    OperationalIntelligenceMockClient,
    load_real_dataset,
    run_real_data_demo,
)

from opsbrain.agents.coordinator import CoordinatorAgent
from opsbrain.agents.evaluator import EvaluatorAgent
from opsbrain.agents.monitor import MonitorAgent
from opsbrain.agents.rca import RCAAgent
from opsbrain.agents.solver import SolverAgent
from opsbrain.core.events import EventBus
from opsbrain.core.types import Incident, IncidentStatus, Severity
from opsbrain.eval.scorer import PipelineScorer
from opsbrain.orchestrator.engine import OrchestrationEngine


@pytest.fixture
def data_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "examples" / "data"


def test_real_datasets_exist_and_parse(data_dir: Path) -> None:
    """Validate all authentic domain datasets exist and conform to schemas."""
    dataset_files = [
        "real_ecommerce_checkout_outage.json",
        "real_fintech_payment_clearing_delay.json",
        "real_supply_chain_port_disruption.json",
    ]

    for filename in dataset_files:
        filepath = data_dir / filename
        assert filepath.exists(), f"Dataset missing: {filepath}"

        data = load_real_dataset(filepath)
        assert "incident_metadata" in data
        assert "metrics" in data
        assert "logs" in data
        assert "alerts" in data

        meta = data["incident_metadata"]
        assert "incident_id" in meta
        assert "title" in meta
        assert "severity" in meta
        assert len(data["metrics"]) > 0
        assert len(data["logs"]) > 0

    # Validate supply chain CSV
    csv_file = data_dir / "real_supply_chain_metrics.csv"
    assert csv_file.exists()
    with open(csv_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) >= 5
        assert "dwell_time_days" in rows[0]
        assert "backlog_teu" in rows[0]


@pytest.mark.asyncio
async def test_real_ecommerce_pipeline_execution(data_dir: Path, tmp_path: Path) -> None:
    """Validate end-to-end execution of the 5-stage pipeline on real e-commerce data."""
    dataset_path = data_dir / "real_ecommerce_checkout_outage.json"
    raw_data = load_real_dataset(dataset_path)
    metadata = raw_data["incident_metadata"]

    event_bus = EventBus()
    llm = OperationalIntelligenceMockClient(raw_data)
    engine = OrchestrationEngine(event_bus=event_bus)

    engine.register_agent(MonitorAgent(llm_client=llm, event_bus=event_bus))
    engine.register_agent(RCAAgent(llm_client=llm, event_bus=event_bus))
    engine.register_agent(SolverAgent(llm_client=llm, event_bus=event_bus))
    engine.register_agent(CoordinatorAgent(llm_client=llm, event_bus=event_bus))
    engine.register_agent(EvaluatorAgent(llm_client=llm, event_bus=event_bus))

    incident = Incident(
        title=metadata["title"],
        severity=Severity.CRITICAL,
        affected_systems=metadata.get("affected_services", ["checkout"]),
        description=metadata.get("business_impact", ""),
    )

    result = await engine.run_pipeline(
        "full_cycle_eval",
        incident=incident,
        data={
            "source": metadata.get("source_system", "checkout-api-gateway"),
            "metrics": raw_data.get("metrics", {}),
            "logs": raw_data.get("logs", []),
            "alerts": raw_data.get("alerts", []),
            "runbooks": raw_data.get("runbooks", []),
        },
    )

    assert result.success is True
    assert result.incident.status == IncidentStatus.RESOLVED
    assert len(result.step_records) == 5

    # Check each agent output was captured
    monitor_out = result.get_output("monitor")
    assert monitor_out is not None
    assert monitor_out.structured_data["anomalies_detected"] is True

    rca_out = result.get_output("rca")
    assert rca_out is not None
    assert "Postgres connection pool exhausted" in rca_out.structured_data["rca_report"]["root_cause"]

    solver_out = result.get_output("solver")
    assert solver_out is not None
    assert len(solver_out.structured_data["solutions"]) >= 2

    coord_out = result.get_output("coordinator")
    assert coord_out is not None
    assert len(coord_out.structured_data["resolution_plan"]["action_items"]) >= 3

    evaluator_out = result.get_output("evaluator")
    assert evaluator_out is not None

    # Score evaluation
    scorer = PipelineScorer()
    eval_score = scorer.score_result(
        result,
        expected_root_cause="Postgres connection pool exhausted",
        expected_systems=["checkout-service", "cart-service", "inventory-db"],
    )

    assert eval_score.overall_score >= 8.5
    assert eval_score.anomaly_detection_score >= 8.0
    assert eval_score.root_cause_accuracy >= 8.0


@pytest.mark.asyncio
async def test_run_real_data_demo_callable() -> None:
    """Validate that run_real_data_demo function runs cleanly without unhandled exceptions."""
    await run_real_data_demo()
    report_file = Path(__file__).resolve().parent.parent.parent / "reports" / "black_friday_checkout_postmortem.md"
    assert report_file.exists()
    assert len(report_file.read_text(encoding="utf-8")) > 200
