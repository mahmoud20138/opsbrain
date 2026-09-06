"""Pipeline definitions and step configuration for multi-agent workflows.

Pipelines define the order, conditional gates, and error handling of agents
operating on operational problems.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import structlog
from pydantic import BaseModel, Field

from opsbrain.core.types import AgentRole

logger = structlog.get_logger(__name__)


class PipelineStep(BaseModel):
    """A single stage in an orchestration pipeline."""

    name: str
    agent_role: AgentRole
    required: bool = True
    condition: Callable[[dict[str, Any]], bool] | None = Field(default=None, exclude=True)
    description: str = ""
    timeout_seconds: float = 120.0
    retry_count: int = 1

    def should_execute(self, context_data: dict[str, Any]) -> bool:
        """Evaluate whether this step should run given the current context."""
        if self.condition is None:
            return True
        try:
            return bool(self.condition(context_data))
        except Exception as exc:
            logger.warning("pipeline_step.condition_eval_failed", step=self.name, error=str(exc))
            return False


class PipelineDefinition(BaseModel):
    """Declarative specification of an operations pipeline."""

    name: str
    description: str = ""
    steps: list[PipelineStep] = Field(default_factory=list)
    version: str = "1.0.0"
    tags: list[str] = Field(default_factory=list)


class Pipeline:
    """Executable pipeline instance with built-in standard pipelines."""

    def __init__(self, definition: PipelineDefinition) -> None:
        self.definition = definition

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def steps(self) -> list[PipelineStep]:
        return self.definition.steps

    # -----------------------------------------------------------------------
    # Built-in Standard Pipelines
    # -----------------------------------------------------------------------

    @classmethod
    def incident_response(cls) -> Pipeline:
        """Full incident response pipeline: Monitor -> RCA -> Solver -> Coordinator."""
        return cls(
            PipelineDefinition(
                name="incident_response",
                description="Comprehensive 4-agent incident detection, root-cause investigation, solution generation, and coordination.",
                steps=[
                    PipelineStep(
                        name="anomaly_detection",
                        agent_role=AgentRole.MONITOR,
                        description="Inspect metrics and logs to detect anomalies and generate alerts.",
                        required=True,
                    ),
                    PipelineStep(
                        name="root_cause_analysis",
                        agent_role=AgentRole.RCA,
                        description="Hypothesis-driven root cause analysis on detected alerts.",
                        required=True,
                        condition=lambda data: bool(data.get("alerts") or data.get("anomalies_detected", True)),
                    ),
                    PipelineStep(
                        name="solution_generation",
                        agent_role=AgentRole.SOLVER,
                        description="Produce ranked remediation solutions with rollback instructions.",
                        required=True,
                    ),
                    PipelineStep(
                        name="cross_team_coordination",
                        agent_role=AgentRole.COORDINATOR,
                        description="Assign action items, communication drafts, and escalation paths.",
                        required=False,
                    ),
                ],
                tags=["incident", "end-to-end", "production"],
            )
        )

    @classmethod
    def quick_triage(cls) -> Pipeline:
        """Fast triage pipeline: Monitor -> RCA."""
        return cls(
            PipelineDefinition(
                name="quick_triage",
                description="Rapid triage: anomaly detection and immediate root cause hypothesis without generating full resolution plans.",
                steps=[
                    PipelineStep(
                        name="anomaly_detection",
                        agent_role=AgentRole.MONITOR,
                        required=True,
                    ),
                    PipelineStep(
                        name="root_cause_analysis",
                        agent_role=AgentRole.RCA,
                        required=True,
                    ),
                ],
                tags=["triage", "fast"],
            )
        )

    @classmethod
    def deep_analysis(cls) -> Pipeline:
        """Deep analysis pipeline: RCA -> Solver."""
        return cls(
            PipelineDefinition(
                name="deep_analysis",
                description="In-depth analysis and solution generation for already-known incidents.",
                steps=[
                    PipelineStep(
                        name="root_cause_analysis",
                        agent_role=AgentRole.RCA,
                        required=True,
                    ),
                    PipelineStep(
                        name="solution_generation",
                        agent_role=AgentRole.SOLVER,
                        required=True,
                    ),
                ],
                tags=["rca", "deep", "solver"],
            )
        )

    @classmethod
    def full_cycle_eval(cls) -> Pipeline:
        """Full 5-agent pipeline including automated evaluation."""
        return cls(
            PipelineDefinition(
                name="full_cycle_eval",
                description="Complete cycle including quality evaluation by the Evaluator agent.",
                steps=[
                    PipelineStep(name="anomaly_detection", agent_role=AgentRole.MONITOR, required=True),
                    PipelineStep(name="root_cause_analysis", agent_role=AgentRole.RCA, required=True),
                    PipelineStep(name="solution_generation", agent_role=AgentRole.SOLVER, required=True),
                    PipelineStep(name="cross_team_coordination", agent_role=AgentRole.COORDINATOR, required=True),
                    PipelineStep(name="quality_evaluation", agent_role=AgentRole.EVALUATOR, required=True),
                ],
                tags=["benchmark", "eval", "full"],
            )
        )
