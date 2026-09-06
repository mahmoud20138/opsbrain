"""Monitor Agent — real-time anomaly detection across processes and systems.

Analyzes metrics, logs, and operational data to detect anomalies,
threshold breaches, and unusual patterns. Produces Alert objects
with severity, affected systems, and supporting evidence.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from opsbrain.agents.base import Agent, AgentContext, AgentOutput
from opsbrain.core.types import AgentRole, Alert, Severity

logger = structlog.get_logger(__name__)

_DEFAULT_SYSTEM_PROMPT = """\
You are the Monitor Agent in an enterprise operations monitoring system.

Your role is to analyze operational metrics, logs, and system data to detect:
- Anomalies: unexpected deviations from normal behavior
- Threshold breaches: values exceeding defined limits
- Trend anomalies: gradual degradation or unusual growth patterns
- Correlation anomalies: unexpected relationships between metrics

For each anomaly you detect, provide:
1. A clear, concise title
2. A detailed description of what was observed
3. Severity level (critical, high, medium, low, info)
4. Which systems are affected
5. Supporting evidence (specific metrics, log entries, timestamps)

Be precise and avoid false positives. Only flag genuine anomalies that
warrant investigation. If the data looks normal, say so clearly.

Output your analysis as JSON with the following structure:
{
    "anomalies_detected": true/false,
    "alerts": [
        {
            "title": "...",
            "description": "...",
            "severity": "critical|high|medium|low|info",
            "affected_systems": ["..."],
            "evidence": ["..."]
        }
    ],
    "summary": "Brief overall assessment"
}
"""


class MonitorAgent(Agent):
    """Analyzes operational data to detect anomalies and generate alerts."""

    role = AgentRole.MONITOR
    name = "monitor"

    def __init__(self, **kwargs: Any) -> None:
        if "system_prompt" not in kwargs or not kwargs["system_prompt"]:
            kwargs["system_prompt"] = _DEFAULT_SYSTEM_PROMPT
        super().__init__(**kwargs)

    async def process(self, context: AgentContext) -> AgentOutput:
        """Analyze the provided data for anomalies.

        Expects ``context.data`` to contain some combination of:
        - ``"metrics"``: list of metric dicts or raw metric data
        - ``"logs"``: list of log entries or raw log text
        - ``"source"``: name of the system being monitored
        - ``"thresholds"``: optional threshold definitions

        Returns:
            An AgentOutput with detected alerts in ``structured_data``.
        """
        self.reset_conversation()

        # Build the analysis prompt from context data
        prompt = self._build_prompt(context)

        logger.info("monitor.analyzing", source=context.data.get("source", "unknown"))

        # Call the LLM for analysis
        analysis = await self.think(prompt)

        # Parse the response
        alerts, confidence = self._parse_response(analysis)

        # Emit alerts to the event bus
        for alert in alerts:
            await self.emit(
                f"Alert: {alert.title} [{alert.severity.value}]",
                recipient=AgentRole.RCA,
                data={"alert": alert.model_dump(mode="json")},
            )

        return AgentOutput(
            agent_role=self.role,
            content=analysis,
            structured_data={
                "alerts": [a.model_dump(mode="json") for a in alerts],
                "anomalies_detected": len(alerts) > 0,
            },
            confidence=confidence,
        )

    def _build_prompt(self, context: AgentContext) -> str:
        """Construct the analysis prompt from context data."""
        parts: list[str] = ["Analyze the following operational data for anomalies:\n"]

        source = context.data.get("source", "unknown system")
        parts.append(f"**Source System**: {source}\n")

        if "metrics" in context.data:
            metrics = context.data["metrics"]
            if isinstance(metrics, (dict, list)):
                metrics_str = json.dumps(metrics, indent=2, default=str)
            else:
                metrics_str = str(metrics)
            parts.append(f"**Metrics**:\n```json\n{metrics_str}\n```\n")

        if "logs" in context.data:
            logs = context.data["logs"]
            if isinstance(logs, list):
                logs_str = "\n".join(str(entry) for entry in logs)
            else:
                logs_str = str(logs)
            parts.append(f"**Logs**:\n```\n{logs_str}\n```\n")

        if "thresholds" in context.data:
            thresholds = json.dumps(context.data["thresholds"], indent=2)
            parts.append(f"**Thresholds**:\n```json\n{thresholds}\n```\n")

        if "description" in context.data:
            parts.append(f"**Additional Context**: {context.data['description']}\n")

        parts.append("Respond with your analysis in the specified JSON format.")
        return "\n".join(parts)

    def _parse_response(self, response: str) -> tuple[list[Alert], float]:
        """Parse the LLM response into Alert objects.

        Returns:
            ``(alerts, confidence)``
        """
        alerts: list[Alert] = []
        confidence = 0.5

        try:
            # Try to extract JSON from the response
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()

            data = json.loads(json_str)

            for alert_data in data.get("alerts", []):
                severity_str = alert_data.get("severity", "medium").lower()
                try:
                    severity = Severity(severity_str)
                except ValueError:
                    severity = Severity.MEDIUM

                alerts.append(Alert(
                    title=alert_data.get("title", "Unnamed Alert"),
                    description=alert_data.get("description", ""),
                    severity=severity,
                    affected_systems=alert_data.get("affected_systems", []),
                    evidence=alert_data.get("evidence", []),
                    source=alert_data.get("source", ""),
                ))

            if data.get("anomalies_detected"):
                confidence = 0.8 if alerts else 0.3

        except (json.JSONDecodeError, KeyError, IndexError):
            logger.warning("monitor.parse_error", response_preview=response[:200])
            # If we can't parse JSON, treat the whole response as a single alert
            if any(word in response.lower() for word in ("anomaly", "alert", "critical", "error", "spike")):
                alerts.append(Alert(
                    title="Anomaly Detected (unparsed)",
                    description=response,
                    severity=Severity.MEDIUM,
                ))
                confidence = 0.4

        return alerts, confidence
