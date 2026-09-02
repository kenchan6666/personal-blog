"""Run lifecycle MCP tool implementations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from mcp_nanobot.audit import AuditRecorder
from mcp_nanobot.auth import AuthContext, AuthorizationGuard
from mcp_nanobot.config import NanobotConfig
from mcp_nanobot.errors import ErrorCode, NanobotError
from mcp_nanobot.schemas import InMemoryNanobotStore, RunRecord


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class RunTools:
    def __init__(
        self,
        *,
        store: InMemoryNanobotStore,
        auth: AuthorizationGuard,
        audit: AuditRecorder,
        config: NanobotConfig,
    ) -> None:
        self._store = store
        self._auth = auth
        self._audit = audit
        self._config = config

    def run_trigger(
        self,
        *,
        task_id: str,
        idempotency_key: str | None = None,
        bearer: str | None = None,
    ) -> dict[str, Any]:
        try:
            self._auth.require_write(AuthContext(bearer=bearer))
            task = self._store.tasks.get(task_id)
            if task is None:
                raise NanobotError(ErrorCode.INVALID_ARGUMENT, "task does not exist")
            if idempotency_key:
                existing = self._store.idempotency_index.get(idempotency_key)
                if existing:
                    run = self._store.runs[existing]
                    return {"ok": True, "run": run.as_dict(), "idempotent_replay": True}

            attempt = len(self._store.runs_by_task.get(task_id, [])) + 1
            run = self._store.create_run(task_id=task_id, attempt=attempt)
            run.status = "running"
            run.started_at = _now_iso()
            run.logs.append("accepted")
            run.logs.append("running")
            if task.status in {"pending", "blocked", "failed"}:
                task.status = "in_progress"  # type: ignore[assignment]
                self._store.update_task(task)
            if idempotency_key:
                self._store.idempotency_index[idempotency_key] = run.run_id

            self._audit.record(tool="run_trigger", status="ok", actor="nanobot", run_id=run.run_id)
            return {"ok": True, "run": run.as_dict(), "idempotent_replay": False}
        except NanobotError as exc:
            return exc.to_payload()

    def run_get(self, *, run_id: str, bearer: str | None = None) -> dict[str, Any]:
        try:
            self._auth.require_read(AuthContext(bearer=bearer))
            run = self._get_run_or_raise(run_id)
            return {"ok": True, "run": run.as_dict()}
        except NanobotError as exc:
            return exc.to_payload()

    def run_logs(
        self,
        *,
        run_id: str,
        offset: int = 0,
        limit: int = 100,
        bearer: str | None = None,
    ) -> dict[str, Any]:
        try:
            self._auth.require_read(AuthContext(bearer=bearer))
            run = self._get_run_or_raise(run_id)
            safe_offset = max(0, offset)
            safe_limit = max(1, min(limit, 500))
            logs = run.logs[safe_offset : safe_offset + safe_limit]
            return {
                "ok": True,
                "run_id": run_id,
                "offset": safe_offset,
                "limit": safe_limit,
                "items": logs,
                "next_offset": safe_offset + len(logs),
            }
        except NanobotError as exc:
            return exc.to_payload()

    def run_cancel(self, *, run_id: str, bearer: str | None = None) -> dict[str, Any]:
        try:
            self._auth.require_write(AuthContext(bearer=bearer))
            run = self._get_run_or_raise(run_id)
            if run.status not in {"queued", "running"}:
                raise NanobotError(
                    ErrorCode.STATE_CONFLICT,
                    "run cannot be cancelled in current state",
                    context={"run_id": run_id, "status": run.status},
                )
            run.status = "cancelled"
            run.ended_at = _now_iso()
            run.logs.append("cancelled")
            self._audit.record(tool="run_cancel", status="ok", actor="nanobot", run_id=run_id)
            return {"ok": True, "run": run.as_dict()}
        except NanobotError as exc:
            return exc.to_payload()

    def run_retry(self, *, run_id: str, bearer: str | None = None) -> dict[str, Any]:
        try:
            self._auth.require_write(AuthContext(bearer=bearer))
            previous = self._get_run_or_raise(run_id)
            if previous.status not in {"failed", "cancelled"}:
                raise NanobotError(
                    ErrorCode.STATE_CONFLICT,
                    "run_retry only supports failed/cancelled runs",
                    context={"run_id": run_id, "status": previous.status},
                )
            if previous.attempt >= self._config.max_run_retries:
                raise NanobotError(
                    ErrorCode.STATE_CONFLICT,
                    "retry limit reached",
                    context={"run_id": run_id, "attempt": previous.attempt},
                )
            new_run = self._store.create_run(task_id=previous.task_id, attempt=previous.attempt + 1)
            new_run.status = "queued"
            new_run.logs.append(f"retry_from:{run_id}")
            self._audit.record(tool="run_retry", status="ok", actor="nanobot", run_id=new_run.run_id)
            return {"ok": True, "run": new_run.as_dict(), "retry_of": run_id}
        except NanobotError as exc:
            return exc.to_payload()

    def _get_run_or_raise(self, run_id: str) -> RunRecord:
        run = self._store.runs.get(run_id)
        if run is None:
            raise NanobotError(
                ErrorCode.INVALID_ARGUMENT,
                "run does not exist",
                context={"run_id": run_id},
            )
        return run
