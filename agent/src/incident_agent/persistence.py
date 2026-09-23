from __future__ import annotations

import json
from typing import Any, Protocol

from .models import Incident, InvestigationResult


class InvestigationRepository(Protocol):
    def save(
        self,
        incident: Incident,
        result: InvestigationResult,
        audit_events: list[dict[str, Any]],
    ) -> None: ...

    def list_reports(self) -> list[dict[str, Any]]: ...

    def get_trace(self, investigation_id: int) -> list[dict[str, Any]]: ...


class InMemoryRepository:
    def __init__(self) -> None:
        self.reports: list[dict[str, Any]] = []
        self.traces: dict[int, list[dict[str, Any]]] = {}

    def save(
        self,
        incident: Incident,
        result: InvestigationResult,
        audit_events: list[dict[str, Any]],
    ) -> None:
        report = result.as_dict()
        report["investigationId"] = len(self.reports) + 1
        self.reports.append(report)
        self.traces[report["investigationId"]] = list(result.trace)

    def list_reports(self) -> list[dict[str, Any]]:
        return list(self.reports)

    def get_trace(self, investigation_id: int) -> list[dict[str, Any]]:
        return list(self.traces.get(investigation_id, []))


class PostgresRepository:
    def __init__(self, database_url: str) -> None:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("PostgreSQL persistence requires psycopg") from exc
        self.psycopg = psycopg
        self.database_url = database_url

    def save(
        self,
        incident: Incident,
        result: InvestigationResult,
        audit_events: list[dict[str, Any]],
    ) -> None:
        with self.psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO incidents (service, description, status)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (incident.service, incident.description, "DIAGNOSED"),
                )
                incident_id = cursor.fetchone()[0]
                cursor.execute(
                    """
                    INSERT INTO investigations (incident_id, root_cause, confidence)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (incident_id, result.root_cause, result.confidence),
                )
                investigation_id = cursor.fetchone()[0]
                cursor.executemany(
                    """
                    INSERT INTO evidence (investigation_id, source, finding, tool_name, collected_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            investigation_id,
                            item.source,
                            item.finding,
                            item.tool,
                            item.collected_at,
                        )
                        for item in result.evidence
                    ],
                )
                cursor.executemany(
                    """
                    INSERT INTO model_turns (investigation_id, turn_number, direction, payload)
                    VALUES (%s, %s, %s, %s::jsonb)
                    """,
                    [
                        (
                            investigation_id,
                            turn.get("turn", 0),
                            turn.get("direction", "unknown"),
                            json.dumps(turn),
                        )
                        for turn in result.trace
                    ],
                )
                cursor.executemany(
                    """
                    INSERT INTO recommendations (investigation_id, action, reason, requires_approval)
                    VALUES (%s, %s, %s, %s)
                    """,
                    [
                        (
                            investigation_id,
                            item.action,
                            item.reason,
                            item.requires_approval,
                        )
                        for item in result.recommendations
                    ],
                )
                cursor.executemany(
                    """
                    INSERT INTO tool_calls (investigation_id, event, tool_name, arguments, details)
                    VALUES (%s, %s, %s, %s::jsonb, %s::jsonb)
                    """,
                    [
                        (
                            investigation_id,
                            event.get("event", "unknown"),
                            event.get("tool"),
                            json.dumps(event.get("arguments", {})),
                            json.dumps(event),
                        )
                        for event in audit_events
                    ],
                )

    def list_reports(self) -> list[dict[str, Any]]:
        with self.psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT i.description, i.service, inv.root_cause, inv.confidence,
                           inv.id
                    FROM investigations inv
                    JOIN incidents i ON i.id = inv.incident_id
                    ORDER BY inv.created_at DESC
                    """
                )
                return [
                    {
                        "incident": row[0],
                        "service": row[1],
                        "rootCause": row[2],
                        "confidence": float(row[3]),
                        "investigationId": row[4],
                    }
                    for row in cursor.fetchall()
                ]

    def get_trace(self, investigation_id: int) -> list[dict[str, Any]]:
        with self.psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT turn_number, direction, payload, created_at
                    FROM model_turns
                    WHERE investigation_id = %s
                    ORDER BY turn_number, id
                    """,
                    (investigation_id,),
                )
                return [
                    {
                        "turn": row[0],
                        "direction": row[1],
                        "payload": row[2],
                        "createdAt": row[3].isoformat(),
                    }
                    for row in cursor.fetchall()
                ]


def build_repository(database_url: str | None) -> InvestigationRepository:
    return PostgresRepository(database_url) if database_url else InMemoryRepository()
