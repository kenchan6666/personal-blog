"""Audit logging primitives for nanobot MCP tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class AuditEntry:
    request_id: str
    tool: str
    status: str
    actor: str
    created_at: str
    task_id: str | None = None
    run_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


class AuditRecorder:
    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def record(
        self,
        *,
        tool: str,
        status: str,
        actor: str,
        task_id: str | None = None,
        run_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            request_id=uuid4().hex,
            tool=tool,
            status=status,
            actor=actor,
            created_at=_now_iso(),
            task_id=task_id,
            run_id=run_id,
            details=details or {},
        )
        self._entries.append(entry)
        return entry

    def recent(self, *, limit: int = 20) -> list[dict[str, Any]]:
        return [entry.__dict__.copy() for entry in self._entries[-limit:]]
