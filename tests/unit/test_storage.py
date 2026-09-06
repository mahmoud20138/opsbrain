"""Unit tests for SQLite storage persistence."""

from __future__ import annotations

import pytest

from opsbrain.core.types import Incident, IncidentStatus, Severity
from opsbrain.orchestrator.state import AuditEntry
from opsbrain.storage.sqlite import SQLiteStorage


class TestSQLiteStorage:
    def test_save_and_get_incident(self, tmp_path):
        db_file = tmp_path / "test_opsbrain.db"
        storage = SQLiteStorage(db_file)

        inc = Incident(
            title="Payment Outage",
            description="High latency and 504 errors",
            severity=Severity.HIGH,
            source="payment-service",
            metadata={"cluster": "prod-us-east-1"},
        )
        storage.save_incident(inc)

        fetched = storage.get_incident(inc.id)
        assert fetched is not None
        assert fetched.id == inc.id
        assert fetched.title == "Payment Outage"
        assert fetched.severity == Severity.HIGH
        assert fetched.metadata["cluster"] == "prod-us-east-1"

    def test_list_and_filter_incidents(self, tmp_path):
        db_file = tmp_path / "test_opsbrain.db"
        storage = SQLiteStorage(db_file)

        inc1 = Incident(title="Inc 1", status=IncidentStatus.DETECTED)
        inc2 = Incident(title="Inc 2", status=IncidentStatus.RESOLVED)
        storage.save_incident(inc1)
        storage.save_incident(inc2)

        all_inc = storage.list_incidents()
        assert len(all_inc) == 2

        resolved_inc = storage.list_incidents(status=IncidentStatus.RESOLVED)
        assert len(resolved_inc) == 1
        assert resolved_inc[0].title == "Inc 2"

    def test_delete_incident(self, tmp_path):
        db_file = tmp_path / "test_opsbrain.db"
        storage = SQLiteStorage(db_file)

        inc = Incident(title="Temp Incident")
        storage.save_incident(inc)
        assert storage.get_incident(inc.id) is not None

        deleted = storage.delete_incident(inc.id)
        assert deleted is True
        assert storage.get_incident(inc.id) is None

    def test_audit_trail_persistence(self, tmp_path):
        db_file = tmp_path / "test_opsbrain.db"
        storage = SQLiteStorage(db_file)

        inc = Incident(title="Audited Incident")
        storage.save_incident(inc)

        entries = [
            AuditEntry(actor="monitor", action="alert_created", comment="Initial alert"),
            AuditEntry(actor="rca", action="diagnosed", from_state=IncidentStatus.ANALYZING, to_state=IncidentStatus.DIAGNOSED),
        ]
        storage.save_audit_trail(inc.id, entries)

        fetched_entries = storage.get_audit_trail(inc.id)
        assert len(fetched_entries) == 2
        assert fetched_entries[0].actor == "monitor"
        assert fetched_entries[1].to_state == IncidentStatus.DIAGNOSED
