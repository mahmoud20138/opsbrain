"""Cross-Departmental Workflow Delay Scenario — Invoice Approval Backlog.

Demonstrates OpsBrain tracking workflow cycle times, detecting an SLA breach
in multi-level approval hierarchies, and generating policy and automation fixes.
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


async def run_workflow_delay_scenario() -> None:
    print("===============================================================")
    print("  OpsBrain Scenario: Cross-Departmental Workflow Optimization  ")
    print("===============================================================")

    client = MockLLMClient(response_content="""{
        "anomalies_detected": true,
        "alerts": [
            {
                "title": "Finance Invoice Approval SLA Breach",
                "description": "Approval cycle time increased to 18.5 days vs SLA 3.0 days",
                "severity": "high",
                "affected_systems": ["finance-procurement-system", "vendor-management"],
                "evidence": ["450 invoices stalled in queue", "$75,000 penalty risk"]
            }
        ],
        "root_cause": "Manual multi-signoff policy threshold ($1,000) created bottleneck at VP Finance desk during quarterly close",
        "evidence_chain": [
            "Recent policy lowered secondary sign-off threshold from $10,000 to $1,000",
            "VP Finance approval queue ballooned by 400%",
            "Quarterly financial close workload created 2-week backlog"
        ],
        "solutions": [
            {
                "title": "Raise auto-approval threshold to $5,000 for approved recurring vendors",
                "steps": [
                    "Update ERP workflow rule #RULE-449",
                    "Require only single-manager sign-off for contracted vendors under $5,000"
                ],
                "risk_level": "low",
                "estimated_time_minutes": 30,
                "rollback_plan": "Revert rule #RULE-449 in ERP admin console"
            },
            {
                "title": "Delegate temporary approval authority to Senior Finance Directors",
                "steps": ["Grant proxy signing rights for invoices between $5,000 and $25,000"],
                "risk_level": "low",
                "estimated_time_minutes": 15,
                "rollback_plan": "Revoke temporary delegation in Identity Manager"
            }
        ],
        "summary": "Streamlined approval workflow and cleared supplier blockages",
        "action_items": [
            {"description": "Update ERP workflow threshold", "assignee": "Finance Systems Admin", "team": "Finance IT", "priority": "high", "due_by": "today"},
            {"description": "Send vendor apologies and updated payment schedules", "assignee": "Accounts Payable Lead", "team": "Finance", "priority": "high", "due_by": "tomorrow"}
        ],
        "communication_draft": "Vendor Update: Payment processing delays resolved; all pending payments scheduled for disbursement."
    }""")

    bus = EventBus()
    engine = OrchestrationEngine(event_bus=bus)

    engine.register_agent(MonitorAgent(llm_client=client, event_bus=bus))
    engine.register_agent(RCAAgent(llm_client=client, event_bus=bus))
    engine.register_agent(SolverAgent(llm_client=client, event_bus=bus))
    engine.register_agent(CoordinatorAgent(llm_client=client, event_bus=bus))

    data = {
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
    }

    result = await engine.run_pipeline("incident_response", data=data)
    print(f"\n[+] Pipeline: {result.pipeline_name}")
    print(f"[+] Incident: {result.incident.title}")
    print(f"[+] Solution: {result.get_output('solver').structured_data['solutions'][0]['title']}")


if __name__ == "__main__":
    asyncio.run(run_workflow_delay_scenario())
