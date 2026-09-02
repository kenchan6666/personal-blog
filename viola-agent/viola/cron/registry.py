"""Per-workspace cron routing for multi-user deployments."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Coroutine

from loguru import logger

from viola.cron.service import CronService
from viola.cron.types import CronJob

if TYPE_CHECKING:
    from viola.agent.loop import AgentLoop


class CronRegistry:
    """Route cron tool operations to workspace-scoped ``CronService`` instances.

    When ``per_user_workspaces`` is disabled, all operations use the default store
    (legacy single-workspace behaviour). When enabled, user sessions get an isolated
    ``<workspace>/cron/jobs.json``; system/global sessions keep using the root store.
    """

    def __init__(
        self,
        default_store_path: Path,
        *,
        per_user_workspaces: bool = False,
    ):
        self._default = CronService(default_store_path)
        self._per_user_workspaces = per_user_workspaces
        self._by_workspace: dict[str, CronService] = {}
        self._migrated_sessions: set[str] = set()
        self._started = False
        self._agent: AgentLoop | None = None
        self._on_job: Callable[[CronJob], Coroutine[Any, Any, str | None]] | None = None

    @property
    def default(self) -> CronService:
        return self._default

    @property
    def running(self) -> bool:
        return self._started

    @property
    def on_job(self) -> Callable[[CronJob], Coroutine[Any, Any, str | None]] | None:
        return self._on_job

    @on_job.setter
    def on_job(self, callback: Callable[[CronJob], Coroutine[Any, Any, str | None]] | None) -> None:
        self._on_job = callback
        self._default.on_job = callback
        for svc in self._by_workspace.values():
            svc.on_job = callback

    def bind(self, agent: AgentLoop) -> None:
        """Attach the live agent loop for workspace resolution."""
        self._agent = agent

    def _runtime_id(self, workspace: Path) -> str:
        return str(workspace.expanduser().resolve(strict=False))

    def _service_for_workspace(self, workspace: Path) -> CronService:
        rid = self._runtime_id(workspace)
        svc = self._by_workspace.get(rid)
        if svc is None:
            store_path = workspace / "cron" / "jobs.json"
            svc = CronService(store_path, on_job=self.on_job)
            self._by_workspace[rid] = svc
        return svc

    def for_session_key(self, session_key: str) -> CronService:
        """Return the cron store that owns jobs for *session_key*."""
        if not self._per_user_workspaces or not self._agent:
            return self._default
        if self._agent._is_global_session(session_key):
            return self._default

        workspace = self._agent.workspace_for_session_key(session_key)
        if workspace == self._agent.workspace:
            return self._default

        svc = self._service_for_workspace(workspace)
        self._maybe_migrate_session_jobs(session_key, svc)
        return svc

    async def ensure_started(self, svc: CronService) -> None:
        """Start a lazily-created user cron service once the registry is running."""
        if self._started and not svc.running:
            await svc.start()

    def _maybe_migrate_session_jobs(self, session_key: str, target: CronService) -> None:
        """Move legacy user jobs from the root store into a per-user store once."""
        if session_key in self._migrated_sessions:
            return
        self._migrated_sessions.add(session_key)

        default_store = self._default._load_store()
        if not default_store:
            return

        to_move = [
            job
            for job in default_store.jobs
            if job.payload.kind == "agent_turn" and job.payload.session_key == session_key
        ]
        if not to_move:
            return

        target_store = target._load_store()
        if target_store is None:
            logger.warning(
                "Skipping cron migration for session {}: target store unreadable at {}",
                session_key,
                target.store_path,
            )
            return

        existing_ids = {job.id for job in target_store.jobs}
        moved = [job for job in to_move if job.id not in existing_ids]
        if not moved:
            default_store.jobs = [
                job
                for job in default_store.jobs
                if not (job.payload.kind == "agent_turn" and job.payload.session_key == session_key)
            ]
            self._default._save_store()
            if self._default.running:
                self._default._arm_timer()
            return

        target_store.jobs.extend(moved)
        default_store.jobs = [
            job
            for job in default_store.jobs
            if not (job.payload.kind == "agent_turn" and job.payload.session_key == session_key)
        ]

        self._default._save_store()
        target._save_store()
        if self._default.running:
            self._default._arm_timer()
        if target.running:
            target._arm_timer()

        logger.info(
            "Migrated {} cron job(s) for session {} → {}",
            len(moved),
            session_key,
            target.store_path,
        )

    async def _ensure_service_started(self, svc: CronService) -> None:
        if self._started and not svc.running:
            await svc.start()

    async def start(self) -> None:
        """Start the default cron service (and any already-created user services)."""
        await self._default.start()
        self._started = True
        for svc in self._by_workspace.values():
            await svc.start()

    def stop(self) -> None:
        """Stop all cron services."""
        self._started = False
        self._default.stop()
        for svc in self._by_workspace.values():
            svc.stop()

    def register_system_job(self, job: CronJob) -> CronJob:
        """Register internal jobs (e.g. Dream) on the root store only."""
        return self._default.register_system_job(job)

    def list_jobs(self, include_disabled: bool = False) -> list[CronJob]:
        """Aggregate jobs across all stores (for startup logging)."""
        jobs = self._default.list_jobs(include_disabled=include_disabled)
        seen = {job.id for job in jobs}
        for svc in self._by_workspace.values():
            for job in svc.list_jobs(include_disabled=include_disabled):
                if job.id not in seen:
                    jobs.append(job)
                    seen.add(job.id)
        return jobs


def create_cron_backend(
    workspace_path: Path,
    *,
    per_user_workspaces: bool,
) -> CronService | CronRegistry:
    """Create the cron backend for a deployment (single store or per-user registry)."""
    store_path = workspace_path / "cron" / "jobs.json"
    if per_user_workspaces:
        return CronRegistry(store_path, per_user_workspaces=True)
    return CronService(store_path)
