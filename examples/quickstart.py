"""OpsBrain Quickstart Example.

Demonstrates programmatic usage of OpsBrain to run an end-to-end multi-agent
pipeline against an operational incident.
"""

from __future__ import annotations

import asyncio

from opsbrain.agents.coordinator import CoordinatorAgent
from opsbrain.agents.monitor import MonitorAgent
from opsbrain.agents.rca import RCAAgent
from opsbrain.agents.solver import SolverAgent
from opsbrain.core.config import load_config
from opsbrain.core.events import EventBus
from opsbrain.harness.mock import MockLLMClient
from opsbrain.harness.registry import ProviderRegistry
from opsbrain.orchestrator.engine import OrchestrationEngine


async def main() -> None:
    print("=== OpsBrain Quickstart ===")

    # 1. Load configuration and determine provider
    cfg = load_config()
    registry = ProviderRegistry(cfg)

    # In local/test mode without API keys, fallback gracefully to MockLLMClient
    provider = cfg.routing.default_provider
    try:
        prov_config = cfg.providers.get(provider)
        if prov_config and prov_config.api_key:
            client = registry.get(provider)
            print(f"Using configured provider: {provider.value}")
        else:
            raise ValueError("No API key set")
    except Exception:
        print("Using demo MockLLMClient (no API keys required)")
        client = MockLLMClient(response_content="""{
            "anomalies_detected": true,
            "alerts": [{"title": "DB Pool Exhaustion", "severity": "critical", "affected_systems": ["db", "api"]}],
            "root_cause": "Database connection pool exhausted due to unclosed sessions in v3.2.1",
            "solutions": [{"title": "Restart pods & scale pool", "steps": ["Scale pool to 100", "Rolling restart"], "risk_level": "low", "rollback_plan": "Revert to v3.2.0"}],
            "summary": "Resolved DB pool exhaustion",
            "action_items": [{"description": "Apply pool config", "assignee": "SRE Team", "priority": "high", "due_by": "1h"}]
        }""")

    # 2. Wire agents to the orchestration engine
    bus = EventBus()
    engine = OrchestrationEngine(event_bus=bus)

    engine.register_agent(MonitorAgent(llm_client=client, event_bus=bus))
    engine.register_agent(RCAAgent(llm_client=client, event_bus=bus))
    engine.register_agent(SolverAgent(llm_client=client, event_bus=bus))
    engine.register_agent(CoordinatorAgent(llm_client=client, event_bus=bus))

    # 3. Define incident operational telemetry
    incident_data = {
        "source": "checkout-service",
        "description": "504 Gateway Timeouts during checkout surge",
        "metrics": {
            "error_rate": 0.12,
            "latency_p99_ms": 2800,
            "db_connections_active": 98,
            "db_connections_max": 100,
        },
        "logs": [
            "ERROR [checkout] PoolAcquisitionException: Timeout waiting for idle connection",
            "WARN  [db-cluster] Max connection limit approached (98/100)",
        ],
    }

    # 4. Execute the pipeline
    print("\nRunning 'incident_response' pipeline...")
    result = await engine.run_pipeline("incident_response", data=incident_data)

    print(f"\nPipeline finished: Success={result.success}")
    print(f"Total Duration: {result.duration_seconds:.2f}s")
    print(f"Incident Status: {result.incident.status.value}")

    # Inspect outputs
    if rca_out := result.get_output("rca"):
        print("\nRCA Output:")
        print(rca_out.structured_data.get("rca_report", {}).get("root_cause", "N/A"))

    if solver_out := result.get_output("solver"):
        print("\nProposed Solutions:")
        for sol in solver_out.structured_data.get("solutions", []):
            print(f"- {sol.get('title')}: {sol.get('steps')}")

    await registry.close_all()


if __name__ == "__main__":
    asyncio.run(main())
