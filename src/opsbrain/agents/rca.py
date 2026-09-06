"""RCA Agent — Root Cause Analysis for operational bottlenecks and issues.

Receives alerts from the Monitor Agent and performs deep analysis to
trace the root cause, building an evidence chain and confidence score.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from opsbrain.agents.base import Agent, AgentContext, AgentOutput
from opsbrain.core.types import AgentRole, RCAReport

logger = structlog.get_logger(__name__)

_DEFAULT_SYSTEM_PROMPT = """\
You are the Root Cause Analysis (RCA) Agent in an enterprise operations system.

Your role is to investigate alerts and operational issues to determine their
root cause. You must:

1. Analyze the alert details, metrics, and logs
2. Form hypotheses about potential root causes
3. Evaluate each hypothesis against available evidence
4. Build an evidence chain linking symptoms to the root cause
5. Identify contributing factors and timeline of events
6. Assess confidence in your diagnosis

Your analysis should be thorough, methodical, and evidence-based.
Avoid speculation — state clearly when evidence is insufficient.

Output your analysis as JSON with the following structure:
{
    "root_cause": "Clear statement of the root cause",
    "evidence_chain": [
        "Evidence point 1: ...",
        "Evidence point 2: ...",
        "Evidence point 3 → leads to root cause"
    ],
    "affected_systems": ["system1", "system2"],
    "contributing_factors": ["factor1", "factor2"],
    "timeline": [
        "T-0: Root cause event occurred",
        "T+5min: First symptoms appeared",
        "T+10min: Alert triggered"
    ],
    "confidence": 0.85,
    "hypotheses_considered": [
        {"hypothesis": "...", "evidence_for": "...", "evidence_against": "...", "verdict": "confirmed|rejected|inconclusive"}
    ]
}
"""


class RCAAgent(Agent):
    """Investigates alerts to determine root cause with evidence chains."""

    role = AgentRole.RCA
    name = "rca"

    def __init__(self, **kwargs: Any) -> None:
        if "system_prompt" not in kwargs or not kwargs["system_prompt"]:
            kwargs["system_prompt"] = _DEFAULT_SYSTEM_PROMPT
        super().__init__(**kwargs)

    async def process(self, context: AgentContext) -> AgentOutput:
        """Perform root cause analysis on alerts from context.

        Expects ``context.data`` to contain:
        - ``"alerts"``: list of alert dicts from Monitor Agent
        - ``"metrics"``: additional metric data (optional)
        - ``"logs"``: additional log data (optional)

        Also checks ``context.prior_outputs`` for Monitor Agent output.

        Returns:
            An AgentOutput with the RCA report in ``structured_data``.
        """
        self.reset_conversation()

        prompt = self._build_prompt(context)

        logger.info("rca.analyzing", incident_id=context.incident_id)

        analysis = await self.think(prompt)
        rca_report, confidence = self._parse_response(analysis)

        # Emit findings to the Solver Agent
        await self.emit(
            f"RCA Complete: {rca_report.root_cause}",
            recipient=AgentRole.SOLVER,
            data={"rca_report": rca_report.model_dump(mode="json")},
        )

        return AgentOutput(
            agent_role=self.role,
            content=analysis,
            structured_data={"rca_report": rca_report.model_dump(mode="json")},
            confidence=confidence,
        )

    def _build_prompt(self, context: AgentContext) -> str:
        """Build the RCA analysis prompt from context."""
        parts: list[str] = [
            "Perform a root cause analysis on the following operational issue:\n",
        ]

        # Include alerts from Monitor Agent
        alerts = context.data.get("alerts", [])
        if not alerts and "monitor" in context.prior_outputs:
            monitor_output = context.prior_outputs["monitor"]
            if isinstance(monitor_output, dict):
                alerts = monitor_output.get("alerts", [])

        if alerts:
            parts.append(f"**Alerts**:\n```json\n{json.dumps(alerts, indent=2, default=str)}\n```\n")

        # Include raw data
        if "metrics" in context.data:
            parts.append(f"**Metrics**:\n```json\n{json.dumps(context.data['metrics'], indent=2, default=str)}\n```\n")

        if "logs" in context.data:
            logs = context.data["logs"]
            logs_str = "\n".join(str(e) for e in logs) if isinstance(logs, list) else str(logs)
            parts.append(f"**Logs**:\n```\n{logs_str}\n```\n")

        if "description" in context.data:
            parts.append(f"**Incident Description**: {context.data['description']}\n")

        parts.append(
            "Analyze the above data systematically. Consider multiple hypotheses, "
            "evaluate evidence for and against each, and present your findings "
            "in the specified JSON format."
        )
        return "\n".join(parts)

    def _parse_response(self, response: str) -> tuple[RCAReport, float]:
        """Parse the LLM response into an RCAReport.

        Returns:
            ``(rca_report, confidence)``
        """
        try:
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()

            data = json.loads(json_str)

            report = RCAReport(
                root_cause=data.get("root_cause", "Unable to determine root cause"),
                evidence_chain=data.get("evidence_chain", []),
                affected_systems=data.get("affected_systems", []),
                contributing_factors=data.get("contributing_factors", []),
                timeline=data.get("timeline", []),
                confidence=float(data.get("confidence", 0.5)),
            )
            return report, report.confidence

        except (json.JSONDecodeError, KeyError, ValueError):
            logger.warning("rca.parse_error", response_preview=response[:200])
            return RCAReport(
                root_cause=response[:500] if response else "Analysis failed",
                confidence=0.3,
            ), 0.3
