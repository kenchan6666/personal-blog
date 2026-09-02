"""Task management MCP tool implementations."""

from __future__ import annotations

from typing import Any

from mcp_nanobot.audit import AuditRecorder
from mcp_nanobot.auth import AuthContext, AuthorizationGuard
from mcp_nanobot.errors import ErrorCode, NanobotError, error_payload
from mcp_nanobot.schemas import InMemoryNanobotStore, TASK_TRANSITIONS


class TaskTools:
    def __init__(
        self,
        *,
        store: InMemoryNanobotStore,
        auth: AuthorizationGuard,
        audit: AuditRecorder,
    ) -> None:
        self._store = store
        self._auth = auth
        self._audit = audit

    def task_create(
        self,
        *,
        title: str,
        description: str = "",
        owner: str | None = None,
        priority: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        bearer: str | None = None,
    ) -> dict[str, Any]:
        try:
            if not title.strip():
                raise NanobotError(ErrorCode.INVALID_ARGUMENT, "title is required")
            self._auth.require_write(AuthContext(bearer=bearer))
            task = self._store.create_task(
                title=title.strip(),
                description=description,
                owner=owner,
                priority=priority,
                tags=tags or [],
                metadata=metadata or {},
            )
            self._audit.record(tool="task_create", status="ok", actor="nanobot", task_id=task.task_id)
            return {"ok": True, "task": task.as_dict()}
        except NanobotError as exc:
            return exc.to_payload()

    def task_get(self, *, task_id: str, bearer: str | None = None) -> dict[str, Any]:
        try:
            self._auth.require_read(AuthContext(bearer=bearer))
            task = self._store.tasks.get(task_id)
            if task is None:
                raise NanobotError(
                    ErrorCode.INVALID_ARGUMENT,
                    "task does not exist",
                    context={"task_id": task_id},
                )
            return {"ok": True, "task": task.as_dict()}
        except NanobotError as exc:
            return exc.to_payload()

    def task_list(
        self,
        *,
        status: str | None = None,
        owner: str | None = None,
        page: int = 1,
        page_size: int = 20,
        bearer: str | None = None,
    ) -> dict[str, Any]:
        try:
            self._auth.require_read(AuthContext(bearer=bearer))
            tasks = list(self._store.tasks.values())
            if status:
                tasks = [task for task in tasks if task.status == status]
            if owner:
                tasks = [task for task in tasks if task.owner == owner]
            page = max(1, page)
            page_size = min(max(1, page_size), 200)
            start = (page - 1) * page_size
            end = start + page_size
            return {
                "ok": True,
                "items": [task.as_dict() for task in tasks[start:end]],
                "pagination": {"page": page, "page_size": page_size, "total": len(tasks)},
            }
        except NanobotError as exc:
            return exc.to_payload()

    def task_update(
        self,
        *,
        task_id: str,
        updates: dict[str, Any],
        bearer: str | None = None,
    ) -> dict[str, Any]:
        try:
            self._auth.require_write(AuthContext(bearer=bearer))
            task = self._store.tasks.get(task_id)
            if task is None:
                raise NanobotError(ErrorCode.INVALID_ARGUMENT, "task does not exist")
            mutable_fields = {"title", "description", "owner", "priority", "tags", "metadata"}
            unknown = sorted(set(updates) - mutable_fields)
            if unknown:
                return error_payload(
                    ErrorCode.INVALID_ARGUMENT,
                    "unsupported update fields",
                    context={"fields": unknown},
                )
            for key, value in updates.items():
                setattr(task, key, value)
            self._store.update_task(task)
            self._audit.record(tool="task_update", status="ok", actor="nanobot", task_id=task_id)
            return {"ok": True, "task": task.as_dict()}
        except NanobotError as exc:
            return exc.to_payload()

    def task_transition(
        self,
        *,
        task_id: str,
        to_status: str,
        bearer: str | None = None,
    ) -> dict[str, Any]:
        try:
            self._auth.require_write(AuthContext(bearer=bearer))
            task = self._store.tasks.get(task_id)
            if task is None:
                raise NanobotError(ErrorCode.INVALID_ARGUMENT, "task does not exist")
            from_status = task.status
            allowed = TASK_TRANSITIONS.get(task.status, set())
            if to_status not in allowed:
                raise NanobotError(
                    ErrorCode.STATE_CONFLICT,
                    f"invalid transition: {task.status} -> {to_status}",
                    context={"task_id": task_id, "from": task.status, "to": to_status},
                )
            task.status = to_status  # type: ignore[assignment]
            self._store.update_task(task)
            self._audit.record(
                tool="task_transition",
                status="ok",
                actor="nanobot",
                task_id=task_id,
                details={"from": from_status, "to": to_status},
            )
            return {"ok": True, "task": task.as_dict()}
        except NanobotError as exc:
            return exc.to_payload()
