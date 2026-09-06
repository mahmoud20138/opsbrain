"""Evaluator Agent — assesses the quality of agent outputs.

Scores the combined pipeline output (alerts, RCA, solutions, coordination)
for accuracy, completeness, actionability, and overall quality.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from opsbrain.agents.base import Agent, AgentContext, AgentOutput
from opsbrain.core.types import AgentRole

logger = structlog.get_logger(__name__)

_DEFAULT_SYSTEM_PROMPT = """\
You are the Evaluator Agent in an enterprise operations system.

Your role is to critically assess the quality of the entire analysis
pipeline — from anomaly detection through root cause analysis to
solution proposals and coordination plans.

Evaluate each stage on the following criteria (1-10 scale):

1. **Accuracy**: Are the findings factually correct and well-supported?
2. **Completeness**: Are all relevant factors considered?
3. **Actionability**: Can the solutions be immediately executed?
4. **Clarity**: Is the communication clear for all stakeholders?
5. **Risk Awareness**: Are risks and rollback plans adequate?

Also identify:
- Gaps: What important aspects were missed?
- Contradictions: Are there inconsistencies between stages?
- Improvements: Specific suggestions to improve the analysis

Output your evaluation as JSON:
{
    "overall_score": 7.5,
    "stage_scores": {
        "monitoring": {"score": 8, "feedback": "..."},
        "rca": {"score": 7, "feedback": "..."},
        "solution": {"score": 8, "feedback": "..."},
        "coordination": {"score": 7, "feedback": "..."}
    },
    "criteria_scores": {
        "accuracy": 8,
        "completeness": 7,
        "actionability": 8,
        "clarity": 7,
        "risk_awareness": 7
    },
    "gaps": ["..."],
    "contradictions": ["..."],
    "improvements": ["..."],
    "summary": "Overall assessment..."
}
"""


class EvaluatorAgent(Agent):
    """Assesses the quality of the entire pipeline output."""

    role = AgentRole.EVALUATOR
    name = "evaluator"

    def __init__(self, **kwargs: Any) -> None:
        if "system_prompt" not in kwargs or not kwargs["system_prompt"]:
            kwargs["system_prompt"] = _DEFAULT_SYSTEM_PROMPT
        super().__init__(**kwargs)

    async def process(self, context: AgentContext) -> AgentOutput:
        """Evaluate the combined outputs from all prior agents.

        Expects ``context.prior_outputs`` to contain outputs from
        monitor, rca, solver, and coordinator agents.

        Returns:
            An AgentOutput with evaluation scores in ``structured_data``.
        """
        self.reset_conversation()
        prompt = self._build_prompt(context)

        logger.info("evaluator.assessing", incident_id=context.incident_id)

        evaluation = await self.think(prompt)
        scores, confidence = self._parse_response(evaluation)

        return AgentOutput(
            agent_role=self.role,
            content=evaluation,
            structured_data={"evaluation": scores},
            confidence=confidence,
        )

    def _build_prompt(self, context: AgentContext) -> str:
        """Build the evaluation prompt from all prior outputs."""
        parts: list[str] = [
            "Evaluate the quality of the following incident analysis pipeline:\n",
        ]

        for stage, output in context.prior_outputs.items():
            parts.append(f"**{stage.upper()} Output**:")
            parts.append(f"```json\n{json.dumps(output, indent=2, default=str)}\n```\n")

        if "original_data" in context.data:
            parts.append(f"**Original Input Data**:\n```json\n{json.dumps(context.data['original_data'], indent=2, default=str)}\n```\n")

        parts.append(
            "Critically evaluate each stage for accuracy, completeness, "
            "actionability, clarity, and risk awareness. "
            "Respond in the specified JSON format."
        )
        return "\n".join(parts)

    def _parse_response(self, response: str) -> tuple[dict[str, Any], float]:
        """Parse the evaluation response."""
        try:
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()

            data = json.loads(json_str)
            overall = float(data.get("overall_score", 5.0)) / 10.0
            return data, overall

        except (json.JSONDecodeError, KeyError, ValueError):
            logger.warning("evaluator.parse_error", response_preview=response[:200])
            return {"summary": response[:500], "overall_score": 5.0}, 0.5
