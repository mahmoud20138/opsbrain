"""Coordinator Agent — cross-team coordination for issue resolution.

Receives solutions and creates resolution plans with team assignments,
communication drafts, and escalation paths.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from opsbrain.agents.base import Agent, AgentContext, AgentOutput
from opsbrain.core.types import (
    ActionItem,
    AgentRole,
    ResolutionPlan,
    Severity,
)

logger = structlog.get_logger(__name__)

_DEFAULT_SYSTEM_PROMPT = """\
You are the Coordinator Agent in an enterprise operations system.

Your role is to take diagnosed issues and proposed solutions and create
a cross-team resolution plan. You must:

1. Identify all stakeholders and teams that need to be involved
2. Create specific action items with clear ownership
3. Draft communication for stakeholders (status update)
4. Define an escalation path if initial resolution fails
5. Set priorities and timelines for each action item

Your communication should be:
- Clear and concise for non-technical stakeholders
- Actionable with specific assignments
- Appropriately urgent based on severity

Output your plan as JSON with the following structure:
{
    "summary": "Brief incident summary for all stakeholders",
    "stakeholders": ["Team/Person 1", "Team/Person 2"],
    "action_items": [
        {
            "description": "What needs to be done",
            "assignee": "Person or team name",
            "team": "Department",
            "priority": "critical|high|medium|low",
            "due_by": "Relative timeframe (e.g., 'within 1 hour')",
            "status": "pending"
        }
    ],
    "communication_draft": "Status update text for stakeholders...",
    "escalation_path": [
        "Level 1: Team Lead",
        "Level 2: Engineering Manager",
        "Level 3: VP Engineering / CTO"
    ]
}
"""


class CoordinatorAgent(Agent):
    """Creates cross-team resolution plans with assignments and communication."""

    role = AgentRole.COORDINATOR
    name = "coordinator"

    def __init__(self, **kwargs: Any) -> None:
        if "system_prompt" not in kwargs or not kwargs["system_prompt"]:
            kwargs["system_prompt"] = _DEFAULT_SYSTEM_PROMPT
        super().__init__(**kwargs)

    async def process(self, context: AgentContext) -> AgentOutput:
        """Create a resolution plan from RCA and solution data.

        Returns:
            An AgentOutput with the resolution plan in ``structured_data``.
        """
        self.reset_conversation()
        prompt = self._build_prompt(context)

        logger.info("coordinator.planning", incident_id=context.incident_id)

        analysis = await self.think(prompt)
        plan, confidence = self._parse_response(analysis)
        plan.incident_id = context.incident_id

        return AgentOutput(
            agent_role=self.role,
            content=analysis,
            structured_data={"resolution_plan": plan.model_dump(mode="json")},
            confidence=confidence,
        )

    def _build_prompt(self, context: AgentContext) -> str:
        """Build the coordination prompt from prior agent outputs."""
        parts: list[str] = [
            "Create a cross-team resolution plan for the following incident:\n",
        ]

        # Include RCA report
        rca_report = context.data.get("rca_report")
        if not rca_report and "rca" in context.prior_outputs:
            rca_output = context.prior_outputs["rca"]
            if isinstance(rca_output, dict):
                rca_report = rca_output.get("rca_report")
        if rca_report:
            parts.append(f"**Root Cause Analysis**:\n```json\n{json.dumps(rca_report, indent=2, default=str)}\n```\n")

        # Include solutions
        solutions = context.data.get("solutions")
        if not solutions and "solver" in context.prior_outputs:
            solver_output = context.prior_outputs["solver"]
            if isinstance(solver_output, dict):
                solutions = solver_output.get("solutions")
        if solutions:
            parts.append(f"**Proposed Solutions**:\n```json\n{json.dumps(solutions, indent=2, default=str)}\n```\n")

        # Include alerts
        if "alerts" in context.data:
            parts.append(f"**Original Alerts**:\n```json\n{json.dumps(context.data['alerts'], indent=2, default=str)}\n```\n")

        parts.append(
            "Create a detailed resolution plan with team assignments, "
            "a stakeholder communication draft, and an escalation path. "
            "Respond in the specified JSON format."
        )
        return "\n".join(parts)

    def _parse_response(self, response: str) -> tuple[ResolutionPlan, float]:
        """Parse the LLM response into a ResolutionPlan."""
        try:
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()

            data = json.loads(json_str)

            action_items: list[ActionItem] = []
            for item_data in data.get("action_items", []):
                priority_str = item_data.get("priority", "medium").lower()
                try:
                    priority = Severity(priority_str)
                except ValueError:
                    priority = Severity.MEDIUM

                action_items.append(ActionItem(
                    description=item_data.get("description", ""),
                    assignee=item_data.get("assignee", ""),
                    team=item_data.get("team", ""),
                    priority=priority,
                    due_by=item_data.get("due_by", ""),
                    status=item_data.get("status", "pending"),
                ))

            plan = ResolutionPlan(
                summary=data.get("summary", ""),
                action_items=action_items,
                stakeholders=data.get("stakeholders", []),
                communication_draft=data.get("communication_draft", ""),
                escalation_path=data.get("escalation_path", []),
            )
            return plan, 0.75

        except (json.JSONDecodeError, KeyError, ValueError):
            logger.warning("coordinator.parse_error", response_preview=response[:200])
            return ResolutionPlan(
                summary=response[:500] if response else "Planning failed",
            ), 0.3
