"""Incident state machine and lifecycle management.

Tracks the progress of an operational incident as it moves through stages:
DETECTED -> ANALYZING -> DIAGNOSED -> RESOLVING -> RESOLVED -> CLOSED.
Maintains a full audit trail of state transitions, triggering actions,
and timestamped notes.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel, Field

from opsbrain.core.exceptions import OpsBrainError
from opsbrain.core.types import Incident, IncidentStatus

logger = structlog.get_logger(__name__)


class InvalidStateTransitionError(OpsBrainError):
    """Raised when an illegal transition between incident states is requested."""

    def __init__(self, from_state: IncidentStatus, to_state: IncidentStatus, reason: str = "") -> None:
        msg = f"Invalid transition from {from_state.value} to {to_state.value}"
        if reason:
            msg += f": {reason}"
        super().__init__(msg, details={"from_state": from_state.value, "to_state": to_state.value})
        self.from_state = from_state
        self.to_state = to_state


class AuditEntry(BaseModel):
    """An entry in the incident audit trail."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actor: str = "system"
    action: str = ""
    from_state: IncidentStatus | None = None
    to_state: IncidentStatus | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    comment: str = ""


class StateTransition(BaseModel):
    """Record of a state transition."""

    from_state: IncidentStatus
    to_state: IncidentStatus
    triggered_by: str = "orchestrator"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reason: str = ""


# Permitted state transitions graph
_VALID_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.DETECTED: {
        IncidentStatus.ANALYZING,
        IncidentStatus.CLOSED,  # False alarm / dismissed
    },
    IncidentStatus.ANALYZING: {
        IncidentStatus.DIAGNOSED,
        IncidentStatus.RESOLVING,
        IncidentStatus.CLOSED,
    },
    IncidentStatus.DIAGNOSED: {
        IncidentStatus.RESOLVING,
        IncidentStatus.ANALYZING,  # Re-evaluate
        IncidentStatus.CLOSED,
    },
    IncidentStatus.RESOLVING: {
        IncidentStatus.RESOLVED,
        IncidentStatus.ANALYZING,  # Resolution failed, re-investigate
        IncidentStatus.CLOSED,
    },
    IncidentStatus.RESOLVED: {
        IncidentStatus.CLOSED,
        IncidentStatus.ANALYZING,  # Regression
    },
    IncidentStatus.CLOSED: {
        IncidentStatus.DETECTED,  # Re-opened
    },
}


class IncidentStateMachine:
    """Manages the state lifecycle and audit trail for an incident.

    Usage::

        sm = IncidentStateMachine(incident)
        sm.transition(IncidentStatus.ANALYZING, actor="rca_agent", reason="Starting RCA")
        assert sm.current_state == IncidentStatus.ANALYZING
    """

    def __init__(self, incident: Incident) -> None:
        self.incident = incident
        self.audit_trail: list[AuditEntry] = []
        self._transition_hooks: list[Callable[[StateTransition], None]] = []

        # Record initial creation entry
        self.record_audit(
            action="incident_created",
            to_state=self.incident.status,
            details={"incident_id": self.incident.id, "title": self.incident.title},
            comment="Incident registered into state machine",
        )

    @property
    def current_state(self) -> IncidentStatus:
        """Current status of the underlying incident."""
        return self.incident.status

    def can_transition(self, to_state: IncidentStatus) -> bool:
        """Check if transition to target state is legally allowed."""
        allowed = _VALID_TRANSITIONS.get(self.current_state, set())
        return to_state in allowed

    def transition(
        self,
        to_state: IncidentStatus,
        *,
        actor: str = "system",
        reason: str = "",
        details: dict[str, Any] | None = None,
    ) -> StateTransition:
        """Transition incident to a new state if valid.

        Args:
            to_state: The target state.
            actor: Name of the agent or user initiating the change.
            reason: Explanation for the state change.
            details: Additional context data.

        Returns:
            The recorded StateTransition object.

        Raises:
            InvalidStateTransitionError: If the transition is disallowed.
        """
        from_state = self.current_state

        if not self.can_transition(to_state):
            raise InvalidStateTransitionError(
                from_state,
                to_state,
                f"Valid next states are: {[s.value for s in _VALID_TRANSITIONS.get(from_state, set())]}",
            )

        # Apply transition
        self.incident.status = to_state
        if to_state == IncidentStatus.RESOLVED and not self.incident.resolved_at:
            self.incident.resolved_at = datetime.now(UTC)

        transition_record = StateTransition(
            from_state=from_state,
            to_state=to_state,
            triggered_by=actor,
            reason=reason,
        )

        self.record_audit(
            actor=actor,
            action="state_transition",
            from_state=from_state,
            to_state=to_state,
            details=details or {},
            comment=reason,
        )

        logger.info(
            "state_machine.transition",
            incident_id=self.incident.id,
            from_state=from_state.value,
            to_state=to_state.value,
            actor=actor,
        )

        # Notify hooks
        for hook in self._transition_hooks:
            try:
                hook(transition_record)
            except Exception as exc:
                logger.warning("state_machine.hook_error", error=str(exc))

        return transition_record

    def record_audit(
        self,
        *,
        action: str,
        actor: str = "system",
        from_state: IncidentStatus | None = None,
        to_state: IncidentStatus | None = None,
        details: dict[str, Any] | None = None,
        comment: str = "",
    ) -> AuditEntry:
        """Record an audit trail event without necessarily changing state."""
        entry = AuditEntry(
            actor=actor,
            action=action,
            from_state=from_state,
            to_state=to_state,
            details=details or {},
            comment=comment,
        )
        self.audit_trail.append(entry)
        return entry

    def add_transition_hook(self, hook: Callable[[StateTransition], None]) -> None:
        """Register a callback executed on every state transition."""
        self._transition_hooks.append(hook)

    def get_history(self) -> list[AuditEntry]:
        """Return the complete audit history."""
        return list(self.audit_trail)
