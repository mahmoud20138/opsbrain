"""Solver Agent — generates tailored solutions for identified problems.

Receives RCA reports and produces actionable remediation plans with
step-by-step instructions, risk assessments, and rollback plans.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from opsbrain.agents.base import Agent, AgentContext, AgentOutput
from opsbrain.core.types import AgentRole, Severity, Solution

logger = structlog.get_logger(__name__)

_DEFAULT_SYSTEM_PROMPT = """\
You are the Solver Agent in an enterprise operations system.

Your role is to generate actionable solutions for operational issues based
on root cause analysis. For each solution you propose:

1. Provide a clear title
2. List step-by-step remediation instructions
3. Assess the risk level of the solution
4. Estimate time to implement
5. List prerequisites
6. Include a rollback plan
7. Rate your confidence in the solution

Prioritize solutions that are:
- Safe: minimize risk of making things worse
- Fast: reduce time-to-resolution
- Thorough: address root cause, not just symptoms
- Reversible: include rollback plans

Output your solutions as JSON with the following structure:
{
    "solutions": [
        {
            "title": "...",
            "steps": ["Step 1: ...", "Step 2: ..."],
            "risk_level": "critical|high|medium|low",
            "estimated_time_minutes": 30,
            "prerequisites": ["..."],
            "rollback_plan": "How to undo this if it fails",
            "confidence": 0.85
        }
    ],
    "recommended_solution_index": 0,
    "reasoning": "Why this solution is recommended over alternatives"
}
"""


class SolverAgent(Agent):
    """Generates actionable solutions based on RCA findings."""

    role = AgentRole.SOLVER
    name = "solver"

    def __init__(self, **kwargs: Any) -> None:
        if "system_prompt" not in kwargs or not kwargs["system_prompt"]:
            kwargs["system_prompt"] = _DEFAULT_SYSTEM_PROMPT
        super().__init__(**kwargs)

    async def process(self, context: AgentContext) -> AgentOutput:
        """Generate solutions based on RCA report.

        Expects ``context.data`` or ``context.prior_outputs`` to contain
        an RCA report.

        Returns:
            An AgentOutput with solutions in ``structured_data``.
        """
        self.reset_conversation()
        prompt = self._build_prompt(context)

        logger.info("solver.generating", incident_id=context.incident_id)

        analysis = await self.think(prompt)
        solutions, confidence = self._parse_response(analysis)

        # Emit solutions to the Coordinator
        await self.emit(
            f"Solutions generated: {len(solutions)} option(s)",
            recipient=AgentRole.COORDINATOR,
            data={"solutions": [s.model_dump(mode="json") for s in solutions]},
        )

        return AgentOutput(
            agent_role=self.role,
            content=analysis,
            structured_data={
                "solutions": [s.model_dump(mode="json") for s in solutions],
            },
            confidence=confidence,
        )

    def _build_prompt(self, context: AgentContext) -> str:
        """Build the solution generation prompt."""
        parts: list[str] = [
            "Generate solutions for the following operational issue:\n",
        ]

        # Include RCA report
        rca_report = context.data.get("rca_report")
        if not rca_report and "rca" in context.prior_outputs:
            rca_output = context.prior_outputs["rca"]
            if isinstance(rca_output, dict):
                rca_report = rca_output.get("rca_report")

        if rca_report:
            parts.append(f"**Root Cause Analysis**:\n```json\n{json.dumps(rca_report, indent=2, default=str)}\n```\n")

        # Include any additional context
        if "alerts" in context.data:
            parts.append(f"**Original Alerts**:\n```json\n{json.dumps(context.data['alerts'], indent=2, default=str)}\n```\n")

        if "constraints" in context.data:
            parts.append(f"**Constraints**: {context.data['constraints']}\n")

        parts.append(
            "Propose at least 2 solutions, ranked by safety and effectiveness. "
            "Include step-by-step instructions, risk assessment, and rollback plans. "
            "Respond in the specified JSON format."
        )
        return "\n".join(parts)

    def _parse_response(self, response: str) -> tuple[list[Solution], float]:
        """Parse the LLM response into Solution objects."""
        try:
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()

            data = json.loads(json_str)
            solutions: list[Solution] = []

            for sol_data in data.get("solutions", []):
                risk_str = sol_data.get("risk_level", "medium").lower()
                try:
                    risk = Severity(risk_str)
                except ValueError:
                    risk = Severity.MEDIUM

                solutions.append(Solution(
                    title=sol_data.get("title", "Untitled Solution"),
                    steps=sol_data.get("steps", []),
                    risk_level=risk,
                    estimated_time_minutes=sol_data.get("estimated_time_minutes"),
                    prerequisites=sol_data.get("prerequisites", []),
                    rollback_plan=sol_data.get("rollback_plan", ""),
                    confidence=float(sol_data.get("confidence", 0.5)),
                ))

            avg_confidence = (
                sum(s.confidence for s in solutions) / len(solutions)
                if solutions
                else 0.3
            )
            return solutions, avg_confidence

        except (json.JSONDecodeError, KeyError, ValueError):
            logger.warning("solver.parse_error", response_preview=response[:200])
            return [Solution(
                title="Solution (unparsed)",
                steps=[response[:500] if response else "Analysis failed"],
                confidence=0.3,
            )], 0.3
