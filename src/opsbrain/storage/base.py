"""Abstract storage backend for incidents, audit records, and agent outputs."""

from __future__ import annotations

from abc import ABC, abstractmethod

from opsbrain.core.types import Incident, IncidentStatus
from opsbrain.orchestrator.state import AuditEntry


class StorageBackend(ABC):
    """Unified interface for persisting operational incident records."""

    @abstractmethod
    def save_incident(self, incident: Incident) -> None:
        """Persist or update an incident."""

    @abstractmethod
    def get_incident(self, incident_id: str) -> Incident | None:
        """Retrieve an incident by ID."""

    @abstractmethod
    def list_incidents(
        self,
        *,
        status: IncidentStatus | None = None,
        limit: int = 50,
    ) -> list[Incident]:
        """List stored incidents, optionally filtered by status."""

    @abstractmethod
    def delete_incident(self, incident_id: str) -> bool:
        """Delete an incident by ID."""

    @abstractmethod
    def save_audit_trail(self, incident_id: str, entries: list[AuditEntry]) -> None:
        """Save audit trail entries for an incident."""

    @abstractmethod
    def get_audit_trail(self, incident_id: str) -> list[AuditEntry]:
        """Retrieve the audit trail for an incident."""

    @abstractmethod
    def close(self) -> None:
        """Close storage connections."""
