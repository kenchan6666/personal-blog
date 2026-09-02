"""Reporting MCP tool implementations."""

from __future__ import annotations

from collections import Counter
from statistics import quantiles
from typing import Any

from mcp_nanobot.auth import AuthContext, AuthorizationGuard
from mcp_nanobot.errors import NanobotError
from mcp_nanobot.schemas import InMemoryNanobotStore


class ReportTools:
    def __init__(self, *, store: InMemoryNanobotStore, auth: AuthorizationGuard) -> None:
        self._store = store
        self._auth = auth

    def report_task_summary(self, *, bearer: str | None = None) -> dict[str, Any]:
        try:
            self._auth.require_read(AuthContext(bearer=bearer))
            by_status = Counter(task.status for task in self._store.tasks.values())
            return {
                "ok": True,
                "total_tasks": len(self._store.tasks),
                "by_status": dict(by_status),
            }
        except NanobotError as exc:
            return exc.to_payload()

    def report_failure_breakdown(self, *, bearer: str | None = None) -> dict[str, Any]:
        try:
            self._auth.require_read(AuthContext(bearer=bearer))
            failures = Counter(
                run.error_code or "UNKNOWN"
                for run in self._store.runs.values()
                if run.status == "failed"
            )
            return {"ok": True, "failures": dict(failures), "total_failed_runs": sum(failures.values())}
        except NanobotError as exc:
            return exc.to_payload()

    def report_runtime_latency(self, *, bearer: str | None = None) -> dict[str, Any]:
        try:
            self._auth.require_read(AuthContext(bearer=bearer))
            durations = [len(run.logs) * 10 for run in self._store.runs.values()]
            if not durations:
                return {"ok": True, "count": 0, "p50_ms": 0, "p95_ms": 0}
            if len(durations) == 1:
                p50 = durations[0]
                p95 = durations[0]
            else:
                q = quantiles(durations, n=100)
                p50 = q[49]
                p95 = q[94]
            return {"ok": True, "count": len(durations), "p50_ms": p50, "p95_ms": p95}
        except NanobotError as exc:
            return exc.to_payload()
