"""Shared task/run/report schemas and in-memory state."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from threading import RLock
from typing import Any, Literal
from uuid import uuid4


TaskStatus = Literal["pending", "in_progress", "blocked", "completed", "cancelled", "failed"]
RunStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]

TASK_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    "pending": {"in_progress", "blocked", "cancelled"},
    "in_progress": {"blocked", "completed", "failed", "cancelled"},
    "blocked": {"in_progress", "cancelled"},
    "completed": set(),
    "cancelled": set(),
    "failed": {"in_progress", "cancelled"},
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class TaskRecord:
    task_id: str
    title: str
    description: str = ""
    status: TaskStatus = "pending"
    owner: str | None = None
    priority: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RunRecord:
    run_id: str
    task_id: str
    status: RunStatus = "queued"
    attempt: int = 1
    logs: list[str] = field(default_factory=list)
    accepted_at: str = field(default_factory=_now_iso)
    started_at: str | None = None
    ended_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class InMemoryNanobotStore:
    """Thread-safe in-memory repository for first-version MCP rollout."""

    def __init__(self) -> None:
        self._lock = RLock()
        self.tasks: dict[str, TaskRecord] = {}
        self.runs: dict[str, RunRecord] = {}
        self.runs_by_task: dict[str, list[str]] = {}
        self.idempotency_index: dict[str, str] = {}

    def create_task(self, *, title: str, description: str = "", **kwargs: Any) -> TaskRecord:
        with self._lock:
            record = TaskRecord(
                task_id=f"task_{uuid4().hex[:12]}",
                title=title,
                description=description,
                owner=kwargs.get("owner"),
                priority=kwargs.get("priority"),
                tags=list(kwargs.get("tags") or []),
                metadata=dict(kwargs.get("metadata") or {}),
            )
            self.tasks[record.task_id] = record
            return record

    def update_task(self, task: TaskRecord) -> None:
        with self._lock:
            task.updated_at = _now_iso()
            self.tasks[task.task_id] = task

    def create_run(self, *, task_id: str, attempt: int = 1) -> RunRecord:
        with self._lock:
            run = RunRecord(run_id=f"run_{uuid4().hex[:12]}", task_id=task_id, attempt=attempt)
            self.runs[run.run_id] = run
            self.runs_by_task.setdefault(task_id, []).append(run.run_id)
            return run

    def reset(self) -> None:
        with self._lock:
            self.tasks.clear()
            self.runs.clear()
            self.runs_by_task.clear()
            self.idempotency_index.clear()
