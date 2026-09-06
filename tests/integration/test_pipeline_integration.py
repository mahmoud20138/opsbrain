"""Integration tests — end-to-end multi-agent pipeline with storage and RAG."""

from __future__ import annotations

import pytest

from conftest import MockLLMClient
from opsbrain.agents.coordinator import CoordinatorAgent
from opsbrain.agents.evaluator import EvaluatorAgent
from opsbrain.agents.monitor import MonitorAgent
from opsbrain.agents.rca import RCAAgent
from opsbrain.agents.solver import SolverAgent
from opsbrain.core.events import EventBus
from opsbrain.core.types import IncidentStatus
from opsbrain.eval.scorer import PipelineScorer
from opsbrain.orchestrator.engine import OrchestrationEngine
from opsbrain.rag.indexer import DocumentIndexer
from opsbrain.rag.retriever import RAGRetriever
from opsbrain.rag.store import VectorStore
from opsbrain.storage.sqlite import SQLiteStorage


@pytest.mark.asyncio
async def test_end_to_end_full_incident_lifecycle(tmp_path):
    """Test full cycle: RAG indexing -> multi-agent response -> evaluation -> SQLite storage."""

    # 1. Populate RAG with operational runbooks
    vector_store = VectorStore()
    indexer = DocumentIndexer()
    runbook_md = """
# Database Outage Runbook
## Symptoms
High connection pool count, timeout exceptions in application logs.
## Recovery Procedure
Step 1: Increase connection pool size in Helm values.
Step 2: Perform rolling restart of consumer pods.
## Rollback
Undo Helm release to previous revision.
"""
    docs = indexer.chunk_markdown_by_headings(runbook_md, doc_id="runbook_db")
    vector_store.add_many(docs)
    assert vector_store.count() >= 2

    # 2. Setup mock LLM that reflects RAG runbook knowledge
    client = MockLLMClient(response_content="""{
        "anomalies_detected": true,
        "alerts": [
            {
                "title": "Payment DB Exhaustion",
                "description": "504 timeouts on payment API",
                "severity": "critical",
                "affected_systems": ["payment-service", "database"],
                "evidence": ["pool 100% full"]
            }
        ],
        "root_cause": "Database connection pool exhaustion caused by unclosed transactions",
        "evidence_chain": ["traffic surge", "connection pool maxed out at 50/50"],
        "solutions": [
            {
                "title": "Scale pool and rolling restart",
                "steps": ["Scale pool to 100", "kubectl rollout restart deployment/payment-service"],
                "risk_level": "low",
                "rollback_plan": "kubectl rollout undo deployment/payment-service"
            }
        ],
        "summary": "Mitigated DB connection pool outage",
        "action_items": [
            {"description": "Apply pool update", "assignee": "SRE Lead", "team": "Platform", "priority": "critical"}
        ],
        "communication_draft": "All systems: Rollback and pool scale initiated.",
        "overall_score": 9.0
    }""")

    # 3. Setup Orchestration Engine with all 5 agents
    bus = EventBus()
    engine = OrchestrationEngine(event_bus=bus)

    engine.register_agent(MonitorAgent(llm_client=client, event_bus=bus))
    engine.register_agent(RCAAgent(llm_client=client, event_bus=bus))
    engine.register_agent(SolverAgent(llm_client=client, event_bus=bus))
    engine.register_agent(CoordinatorAgent(llm_client=client, event_bus=bus))
    engine.register_agent(EvaluatorAgent(llm_client=client, event_bus=bus))

    # Retrieve relevant runbook for context injection
    retriever = RAGRetriever(vector_store)
    retrieved = retriever.retrieve("connection pool")
    rag_context = retrieved.to_context_string()

    input_data = {
        "source": "payment-service",
        "metrics": {"error_rate": 0.15, "db_pool_active": 50},
        "logs": ["ERROR Connection pool exhausted"],
        "runbook_context": rag_context,
    }

    # 4. Run pipeline
    result = await engine.run_pipeline("full_cycle_eval", data=input_data)

    assert result.success is True
    assert result.incident.status == IncidentStatus.RESOLVED
    assert len(result.step_records) == 5

    # 5. Score output
    scorer = PipelineScorer()
    score = scorer.score_result(
        result,
        expected_root_cause="Database connection pool exhaustion",
        expected_systems=["database"],
    )
    assert score.overall_score >= 8.0

    # 6. Persist to SQLite and verify audit trail
    db_file = tmp_path / "integration_opsbrain.db"
    storage = SQLiteStorage(db_file)

    storage.save_incident(result.incident)
    storage.save_audit_trail(result.incident.id, result.state_machine.get_history())

    saved_incident = storage.get_incident(result.incident.id)
    assert saved_incident is not None
    assert saved_incident.status == IncidentStatus.RESOLVED

    audit_history = storage.get_audit_trail(result.incident.id)
    assert len(audit_history) >= 4
