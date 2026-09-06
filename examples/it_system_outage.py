"""IT System Outage Scenario — Database Connection Pool Exhaustion.

Demonstrates OpsBrain diagnosing a production degradation caused by a
database connection pool starvation following a microservice deployment.
"""

from __future__ import annotations

import asyncio

from opsbrain.agents.coordinator import CoordinatorAgent
from opsbrain.agents.evaluator import EvaluatorAgent
from opsbrain.agents.monitor import MonitorAgent
from opsbrain.agents.rca import RCAAgent
from opsbrain.agents.solver import SolverAgent
from opsbrain.core.events import EventBus
from opsbrain.harness.mock import MockLLMClient
from opsbrain.orchestrator.engine import OrchestrationEngine


async def run_it_outage_scenario() -> None:
    print("==================================================")
    print("  OpsBrain Scenario: IT System Outage Investigation")
    print("==================================================")

    client = MockLLMClient(response_content="""{
        "anomalies_detected": true,
        "alerts": [
            {
                "title": "Payment Gateway 504 Timeouts",
                "description": "Error rate 18% with connection pool starvation",
                "severity": "critical",
                "affected_systems": ["payment-service", "postgresql-master"],
                "evidence": ["pool saturation: 50/50", "latency p99: 3200ms"]
            }
        ],
        "root_cause": "Database connection pool exhaustion caused by unclosed connection leak in deployment v3.2.1",
        "evidence_chain": [
            "v3.2.1 deployed at 08:00 UTC",
            "Thread dumps reveal connection leaks in OrderConfirmationHandler",
            "PostgreSQL active connections reached pool maximum 50/50",
            "Subsequent requests timed out waiting for connection"
        ],
        "solutions": [
            {
                "title": "Roll back to v3.2.0 and restart payment pods",
                "steps": ["kubectl rollout undo deployment payment-service", "kubectl rollout status deployment payment-service"],
                "risk_level": "low",
                "estimated_time_minutes": 5,
                "rollback_plan": "Re-apply v3.2.1 container image if rollback fails"
            },
            {
                "title": "Temporarily increase pool size on RDS",
                "steps": ["ALTER SYSTEM SET max_connections = 300", "SELECT pg_reload_conf()"],
                "risk_level": "medium",
                "estimated_time_minutes": 10,
                "rollback_plan": "Revert parameter group settings"
            }
        ],
        "summary": "Critical payment outage caused by connection leak in v3.2.1",
        "action_items": [
            {"description": "Trigger Kubernetes rollback to v3.2.0", "assignee": "On-Call SRE", "team": "Platform", "priority": "critical", "due_by": "10m"},
            {"description": "Draft hotfix for OrderConfirmationHandler leak", "assignee": "Backend Lead", "team": "Payments", "priority": "high", "due_by": "4h"}
        ],
        "communication_draft": "All hands: We are executing a rollback of payment-service to v3.2.0 to restore service.",
        "overall_score": 9.2
    }""")

    bus = EventBus()
    engine = OrchestrationEngine(event_bus=bus)

    engine.register_agent(MonitorAgent(llm_client=client, event_bus=bus))
    engine.register_agent(RCAAgent(llm_client=client, event_bus=bus))
    engine.register_agent(SolverAgent(llm_client=client, event_bus=bus))
    engine.register_agent(CoordinatorAgent(llm_client=client, event_bus=bus))
    engine.register_agent(EvaluatorAgent(llm_client=client, event_bus=bus))

    input_data = {
        "source": "payment-gateway",
        "metrics": {
            "error_rate": 0.18,
            "latency_p99_ms": 3200,
            "db_pool_active": 50,
            "db_pool_max": 50,
        },
        "logs": [
            "ERROR [payment-gateway] Connection pool exhausted: timeout waiting for connection",
            "ERROR [payment-gateway] PostgreSQL connection count reached 100% capacity",
        ],
    }

    result = await engine.run_pipeline("full_cycle_eval", data=input_data)
    print(f"\n[+] Incident ID: {result.incident.id}")
    print(f"[+] Final Status: {result.incident.status.value}")
    print(f"[+] Total Duration: {result.duration_seconds:.2f}s")
    print(f"[+] Execution Records: {len(result.step_records)} steps succeeded.")


if __name__ == "__main__":
    asyncio.run(run_it_outage_scenario())
