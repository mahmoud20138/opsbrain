"""Orchestration Engine — executes multi-agent operational workflows.

Coordinates specialized agents using a supervisor pattern, managing
shared context, incident state transitions, error handling, and event publishing.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel, Field

from opsbrain.agents.base import Agent, AgentContext, AgentOutput
from opsbrain.core.events import EventBus
from opsbrain.core.exceptions import OpsBrainError
from opsbrain.core.types import AgentRole, Incident, IncidentStatus
from opsbrain.orchestrator.pipeline import Pipeline, PipelineStep
from opsbrain.orchestrator.state import IncidentStateMachine

logger = structlog.get_logger(__name__)


class StepExecutionRecord(BaseModel):
    """Execution telemetry for a single pipeline step."""

    step_name: str
    agent_role: AgentRole
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    duration_seconds: float = 0.0
    status: str = "pending"  # "success", "failed", "skipped"
    tokens_used: int = 0
    cost_usd: float = 0.0
    error_message: str | None = None


class PipelineResult:
    """Final result of an orchestration pipeline execution."""

    def __init__(
        self,
        *,
        pipeline_name: str,
        incident: Incident,
        state_machine: IncidentStateMachine,
        success: bool = True,
        step_records: list[StepExecutionRecord] | None = None,
        agent_outputs: dict[str, AgentOutput] | None = None,
        duration_seconds: float = 0.0,
        errors: list[str] | None = None,
    ) -> None:
        self.pipeline_name = pipeline_name
        self.incident = incident
        self.state_machine = state_machine
        self.success = success
        self.step_records = step_records or []
        self.agent_outputs = agent_outputs or {}
        self.duration_seconds = duration_seconds
        self.errors = errors or []

    @property
    def total_tokens(self) -> int:
        return sum(s.tokens_used for s in self.step_records)

    @property
    def total_cost(self) -> float:
        return sum(s.cost_usd for s in self.step_records)

    def get_output(self, role: AgentRole | str) -> AgentOutput | None:
        key = role.value if isinstance(role, AgentRole) else role
        return self.agent_outputs.get(key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_name": self.pipeline_name,
            "incident_id": self.incident.id,
            "incident_status": self.incident.status.value,
            "success": self.success,
            "duration_seconds": round(self.duration_seconds, 3),
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost, 6),
            "step_records": [s.model_dump(mode="json") for s in self.step_records],
            "errors": self.errors,
            "outputs": {
                k: {
                    "content": v.content,
                    "structured_data": v.structured_data,
                    "confidence": v.confidence,
                }
                for k, v in self.agent_outputs.items()
            },
        }


# Type for human-in-the-loop checkpoint handler
CheckpointCallback = Callable[[PipelineStep, AgentContext], Coroutine[Any, Any, bool]]


class OrchestrationEngine:
    """Engine executing multi-agent pipelines against operational incidents.

    Usage::

        engine = OrchestrationEngine(event_bus=bus)
        engine.register_agent(monitor_agent)
        engine.register_agent(rca_agent)
        engine.register_agent(solver_agent)

        result = await engine.run_pipeline("incident_response", data={"metrics": ...})
    """

    def __init__(
        self,
        *,
        event_bus: EventBus | None = None,
        checkpoint_handler: CheckpointCallback | None = None,
    ) -> None:
        self.event_bus = event_bus or EventBus()
        self.checkpoint_handler = checkpoint_handler
        self._agents: dict[AgentRole, Agent] = {}
        self._pipelines: dict[str, Pipeline] = {}

        # Register default pipelines
        self.register_pipeline(Pipeline.incident_response())
        self.register_pipeline(Pipeline.quick_triage())
        self.register_pipeline(Pipeline.deep_analysis())
        self.register_pipeline(Pipeline.full_cycle_eval())

    def register_agent(self, agent: Agent) -> None:
        """Register an agent instance for a given role."""
        self._agents[agent.role] = agent
        logger.info("orchestrator.registered_agent", role=agent.role.value, agent=agent.name)

    def register_pipeline(self, pipeline: Pipeline) -> None:
        """Register an executable pipeline."""
        self._pipelines[pipeline.name] = pipeline
        logger.info("orchestrator.registered_pipeline", name=pipeline.name)

    def get_pipeline(self, name: str) -> Pipeline:
        """Retrieve a pipeline by name."""
        if name not in self._pipelines:
            raise OpsBrainError(f"Pipeline '{name}' not found. Available: {list(self._pipelines.keys())}")
        return self._pipelines[name]

    async def run_pipeline(
        self,
        pipeline_name: str | Pipeline,
        *,
        data: dict[str, Any] | None = None,
        incident: Incident | None = None,
    ) -> PipelineResult:
        """Execute a pipeline from start to finish.

        Args:
            pipeline_name: Name of the pipeline or Pipeline instance.
            data: Input operational metrics, logs, context.
            incident: Optional pre-existing incident. If None, one is created.

        Returns:
            PipelineResult with agent outputs, telemetry, and audit trail.
        """
        pipeline = pipeline_name if isinstance(pipeline_name, Pipeline) else self.get_pipeline(pipeline_name)
        start_time = time.monotonic()

        data = dict(data or {})
        if incident is None:
            incident = Incident(
                title=data.get("title", f"Incident-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"),
                description=data.get("description", ""),
                source=data.get("source", "system"),
                status=IncidentStatus.DETECTED,
            )

        sm = IncidentStateMachine(incident)
        context = AgentContext(incident_id=incident.id, data=data, prior_outputs={})

        step_records: list[StepExecutionRecord] = []
        agent_outputs: dict[str, AgentOutput] = {}
        errors: list[str] = []
        overall_success = True

        logger.info("orchestrator.pipeline_started", pipeline=pipeline.name, incident_id=incident.id)

        for step in pipeline.steps:
            # Check condition
            eval_data = {**context.data, **{k: v.structured_data for k, v in agent_outputs.items()}}
            if not step.should_execute(eval_data):
                logger.info("orchestrator.step_skipped", step=step.name)
                step_records.append(
                    StepExecutionRecord(
                        step_name=step.name,
                        agent_role=step.agent_role,
                        status="skipped",
                    )
                )
                continue

            # Check if agent is registered
            agent = self._agents.get(step.agent_role)
            if agent is None:
                msg = f"Agent for role '{step.agent_role.value}' not registered in engine."
                if step.required:
                    logger.error("orchestrator.missing_agent", role=step.agent_role.value)
                    errors.append(msg)
                    overall_success = False
                    break
                else:
                    logger.warning("orchestrator.missing_optional_agent", role=step.agent_role.value)
                    continue

            # Checkpoint (human-in-the-loop)
            if self.checkpoint_handler:
                approved = await self.checkpoint_handler(step, context)
                if not approved:
                    logger.info("orchestrator.checkpoint_rejected", step=step.name)
                    step_records.append(
                        StepExecutionRecord(
                            step_name=step.name,
                            agent_role=step.agent_role,
                            status="rejected_by_checkpoint",
                        )
                    )
                    break

            # Transition incident state based on step
            self._update_incident_state(sm, step.agent_role)

            # Execute step with retries
            step_record = StepExecutionRecord(step_name=step.name, agent_role=step.agent_role)
            step_start = time.monotonic()

            try:
                # Update context with all prior outputs
                context.prior_outputs = {k: v.structured_data for k, v in agent_outputs.items()}

                # Execute with timeout
                output = await asyncio.wait_for(agent.process(context), timeout=step.timeout_seconds)

                step_record.completed_at = datetime.now(UTC)
                step_record.duration_seconds = time.monotonic() - step_start
                step_record.status = "success"
                step_record.tokens_used = output.tokens_used
                step_record.cost_usd = output.cost_usd

                agent_outputs[step.agent_role.value] = output
                step_records.append(step_record)

                # Merge any structured findings into context data for downstream steps
                if output.structured_data:
                    for k, v in output.structured_data.items():
                        context.data[k] = v

                logger.info(
                    "orchestrator.step_completed",
                    step=step.name,
                    role=step.agent_role.value,
                    duration=round(step_record.duration_seconds, 2),
                )

            except Exception as exc:
                step_record.completed_at = datetime.now(UTC)
                step_record.duration_seconds = time.monotonic() - step_start
                step_record.status = "failed"
                step_record.error_message = str(exc)
                step_records.append(step_record)

                err_msg = f"Step '{step.name}' ({step.agent_role.value}) failed: {exc}"
                logger.error("orchestrator.step_failed", step=step.name, error=str(exc))
                errors.append(err_msg)

                if step.required:
                    overall_success = False
                    break

        # Final state transition if completed successfully
        if overall_success and sm.current_state != IncidentStatus.RESOLVED and sm.can_transition(IncidentStatus.RESOLVED):
            sm.transition(IncidentStatus.RESOLVED, actor="orchestrator", reason="Pipeline completed successfully")

        duration = time.monotonic() - start_time
        return PipelineResult(
            pipeline_name=pipeline.name,
            incident=incident,
            state_machine=sm,
            success=overall_success,
            step_records=step_records,
            agent_outputs=agent_outputs,
            duration_seconds=duration,
            errors=errors,
        )

    def _update_incident_state(self, sm: IncidentStateMachine, role: AgentRole) -> None:
        """Advance incident state machine based on which agent is executing."""
        if role == AgentRole.MONITOR:
            # Usually stays at DETECTED or moves to ANALYZING
            pass
        elif role == AgentRole.RCA:
            if sm.can_transition(IncidentStatus.ANALYZING):
                sm.transition(IncidentStatus.ANALYZING, actor="rca_agent", reason="Root cause investigation begun")
        elif role == AgentRole.SOLVER:
            if sm.can_transition(IncidentStatus.DIAGNOSED):
                sm.transition(IncidentStatus.DIAGNOSED, actor="solver_agent", reason="Root cause identified, formulating solutions")
        elif role == AgentRole.COORDINATOR:
            if sm.can_transition(IncidentStatus.RESOLVING):
                sm.transition(IncidentStatus.RESOLVING, actor="coordinator_agent", reason="Dispatching cross-team action plan")
