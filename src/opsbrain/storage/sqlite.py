"""SQLite storage backend for incidents and audit trails.

Zero-configuration persistence suitable for single-node deployments,
CLI workflows, and automated tests.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import structlog

from opsbrain.core.types import Incident, IncidentStatus, Severity
from opsbrain.orchestrator.state import AuditEntry
from opsbrain.storage.base import StorageBackend

logger = structlog.get_logger(__name__)


class SQLiteStorage(StorageBackend):
    """SQLite implementation of StorageBackend."""

    def __init__(self, db_path: str | Path = "opsbrain.db") -> None:
        self.db_path = str(db_path)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    severity TEXT,
                    status TEXT NOT NULL,
                    source TEXT,
                    created_at TEXT,
                    resolved_at TEXT,
                    metadata_json TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_trail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    from_state TEXT,
                    to_state TEXT,
                    details_json TEXT,
                    comment TEXT,
                    FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    def save_incident(self, incident: Incident) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO incidents (
                    id, title, description, severity, status, source,
                    created_at, resolved_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    incident.id,
                    incident.title,
                    incident.description,
                    incident.severity.value,
                    incident.status.value,
                    incident.source,
                    incident.created_at.isoformat(),
                    incident.resolved_at.isoformat() if incident.resolved_at else None,
                    json.dumps(incident.metadata),
                ),
            )
            conn.commit()

    def get_incident(self, incident_id: str) -> Incident | None:
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
            row = cursor.fetchone()
            if not row:
                return None

            return Incident(
                id=row["id"],
                title=row["title"],
                description=row["description"] or "",
                severity=Severity(row["severity"]),
                status=IncidentStatus(row["status"]),
                source=row["source"] or "",
                created_at=datetime.fromisoformat(row["created_at"]),
                resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
                metadata=json.loads(row["metadata_json"] or "{}"),
            )

    def list_incidents(
        self,
        *,
        status: IncidentStatus | None = None,
        limit: int = 50,
    ) -> list[Incident]:
        with self._get_conn() as conn:
            if status:
                cursor = conn.execute(
                    "SELECT * FROM incidents WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status.value, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM incidents ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                )

            incidents: list[Incident] = []
            for row in cursor.fetchall():
                incidents.append(
                    Incident(
                        id=row["id"],
                        title=row["title"],
                        description=row["description"] or "",
                        severity=Severity(row["severity"]),
                        status=IncidentStatus(row["status"]),
                        source=row["source"] or "",
                        created_at=datetime.fromisoformat(row["created_at"]),
                        resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
                        metadata=json.loads(row["metadata_json"] or "{}"),
                    )
                )
            return incidents

    def delete_incident(self, incident_id: str) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM incidents WHERE id = ?", (incident_id,))
            conn.execute("DELETE FROM audit_trail WHERE incident_id = ?", (incident_id,))
            conn.commit()
            return cursor.rowcount > 0

    def save_audit_trail(self, incident_id: str, entries: list[AuditEntry]) -> None:
        with self._get_conn() as conn:
            for entry in entries:
                conn.execute(
                    """
                    INSERT INTO audit_trail (
                        incident_id, timestamp, actor, action,
                        from_state, to_state, details_json, comment
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        incident_id,
                        entry.timestamp.isoformat(),
                        entry.actor,
                        entry.action,
                        entry.from_state.value if entry.from_state else None,
                        entry.to_state.value if entry.to_state else None,
                        json.dumps(entry.details),
                        entry.comment,
                    ),
                )
            conn.commit()

    def get_audit_trail(self, incident_id: str) -> list[AuditEntry]:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM audit_trail WHERE incident_id = ? ORDER BY timestamp ASC",
                (incident_id,),
            )
            entries: list[AuditEntry] = []
            for row in cursor.fetchall():
                entries.append(
                    AuditEntry(
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                        actor=row["actor"],
                        action=row["action"],
                        from_state=IncidentStatus(row["from_state"]) if row["from_state"] else None,
                        to_state=IncidentStatus(row["to_state"]) if row["to_state"] else None,
                        details=json.loads(row["details_json"] or "{}"),
                        comment=row["comment"] or "",
                    )
                )
            return entries

    def close(self) -> None:
        pass
