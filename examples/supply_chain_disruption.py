"""Supply Chain Disruption Scenario — Port Congestion & Raw Material Bottlenecks.

Demonstrates OpsBrain monitoring enterprise ERP/logistics telemetry,
diagnosing a critical component supply disruption, and coordinating mitigation.
"""

from __future__ import annotations

import asyncio

from opsbrain.agents.coordinator import CoordinatorAgent
from opsbrain.agents.monitor import MonitorAgent
from opsbrain.agents.rca import RCAAgent
from opsbrain.agents.solver import SolverAgent
from opsbrain.core.events import EventBus
from opsbrain.harness.mock import MockLLMClient
from opsbrain.orchestrator.engine import OrchestrationEngine


async def run_supply_chain_scenario() -> None:
    print("=========================================================")
    print("  OpsBrain Scenario: Global Supply Chain Port Congestion")
    print("=========================================================")

    client = MockLLMClient(response_content="""{
        "anomalies_detected": true,
        "alerts": [
            {
                "title": "Critical Port Dwell Time Spike",
                "description": "Port dwell time at 12.4 days vs baseline 2.1 days",
                "severity": "high",
                "affected_systems": ["global-logistics-erp", "mfg-line-assembly"],
                "evidence": ["Container dwell time: +490%", "SKU-774 buffer down to 1.5 days"]
            }
        ],
        "root_cause": "Port congestion and labor disruption delaying inbound shipping containers of micro-controller SKU-774",
        "evidence_chain": [
            "Vessel MV-Titan delayed at Port of Rotterdam",
            "Dockworker labor strike triggered severe unloading backlog",
            "Just-In-Time buffer for factory assembly line reduced from 14 days to 1.5 days"
        ],
        "solutions": [
            {
                "title": "Air-freight emergency buffer batch from secondary supplier in Taiwan",
                "steps": [
                    "Issue expedited purchase order PO-9921 for 5,000 units of SKU-774",
                    "Contract DHL Global Forwarding charter flight for delivery within 48 hours"
                ],
                "risk_level": "medium",
                "estimated_time_minutes": 120,
                "rollback_plan": "Cancel air charter if port unloading resumes within 12 hours"
            },
            {
                "title": "Reroute factory schedule to prioritize SKU-880 product lines",
                "steps": ["Reassign manufacturing line 3 to unaffected product model"],
                "risk_level": "low",
                "estimated_time_minutes": 60,
                "rollback_plan": "Switch line back when parts arrive"
            }
        ],
        "summary": "Supply chain disruption mitigated via air freight and assembly re-scheduling",
        "action_items": [
            {"description": "Authorize expedited air freight PO", "assignee": "Procurement Director", "team": "Procurement", "priority": "critical", "due_by": "2h"},
            {"description": "Adjust factory production calendar", "assignee": "Plant Operations Mgr", "team": "Manufacturing", "priority": "high", "due_by": "4h"}
        ],
        "communication_draft": "Operations Notice: Emergency supply bridge initiated for SKU-774 via air freight."
    }""")

    bus = EventBus()
    engine = OrchestrationEngine(event_bus=bus)

    engine.register_agent(MonitorAgent(llm_client=client, event_bus=bus))
    engine.register_agent(RCAAgent(llm_client=client, event_bus=bus))
    engine.register_agent(SolverAgent(llm_client=client, event_bus=bus))
    engine.register_agent(CoordinatorAgent(llm_client=client, event_bus=bus))

    data = {
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
    }

    result = await engine.run_pipeline("incident_response", data=data)
    print(f"\n[+] Pipeline: {result.pipeline_name}")
    print(f"[+] Status: {result.incident.status.value}")
    print(f"[+] Root cause: {result.get_output('rca').structured_data['rca_report']['root_cause']}")


if __name__ == "__main__":
    asyncio.run(run_supply_chain_scenario())
