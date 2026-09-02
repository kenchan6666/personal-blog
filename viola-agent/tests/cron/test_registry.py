"""Tests for per-user cron registry routing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from viola.cron.registry import CronRegistry, create_cron_backend
from viola.cron.service import CronService
from viola.cron.types import CronSchedule
from viola.utils.helpers import safe_filename


@dataclass
class StubAgent:
    workspace: Path
    per_user_root: Path
    _per_user_workspaces: bool = True

    def _is_global_session(self, session_key: str) -> bool:
        return session_key in {"heartbeat"} or session_key.startswith("cron:")

    def workspace_for_session_key(self, session_key: str) -> Path:
        if self._is_global_session(session_key):
            return self.workspace
        return self.per_user_root / safe_filename(session_key.replace(":", "_"))


@pytest.fixture
def cron_layout(tmp_path: Path) -> tuple[CronRegistry, StubAgent]:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    users = workspace / "users"
    users.mkdir()
    registry = CronRegistry(workspace / "cron" / "jobs.json", per_user_workspaces=True)
    agent = StubAgent(workspace=workspace, per_user_root=users)
    registry.bind(agent)  # type: ignore[arg-type]
    return registry, agent


def test_create_cron_backend_single_store(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    backend = create_cron_backend(workspace, per_user_workspaces=False)
    assert isinstance(backend, CronService)


def test_create_cron_backend_registry(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    backend = create_cron_backend(workspace, per_user_workspaces=True)
    assert isinstance(backend, CronRegistry)


def test_for_session_key_uses_isolated_stores(cron_layout: tuple[CronRegistry, StubAgent]) -> None:
    registry, _agent = cron_layout
    user_a = registry.for_session_key("api:111")
    user_b = registry.for_session_key("api:222")

    assert user_a is not user_b
    assert user_a.store_path != user_b.store_path
    assert user_a.store_path == registry.default.store_path.parent.parent / "users" / "api_111" / "cron" / "jobs.json"


def test_list_and_remove_are_scoped_per_session(cron_layout: tuple[CronRegistry, StubAgent]) -> None:
    registry, _agent = cron_layout
    user_a = registry.for_session_key("api:111")
    user_b = registry.for_session_key("api:222")

    job_a = user_a.add_job(
        name="A reminder",
        schedule=CronSchedule(kind="every", every_ms=60_000),
        message="ping A",
        session_key="api:111",
    )
    user_b.add_job(
        name="B reminder",
        schedule=CronSchedule(kind="every", every_ms=60_000),
        message="ping B",
        session_key="api:222",
    )

    assert [j.id for j in user_a.list_jobs()] == [job_a.id]
    assert job_a.id not in {j.id for j in user_b.list_jobs()}

    assert user_b.remove_job(job_a.id) == "not_found"
    assert user_a.remove_job(job_a.id) == "removed"


@pytest.mark.asyncio
async def test_migrates_legacy_jobs_from_root_store(
    cron_layout: tuple[CronRegistry, StubAgent],
) -> None:
    registry, _agent = cron_layout
    await registry.start()
    legacy = registry.default.add_job(
        name="legacy",
        schedule=CronSchedule(kind="every", every_ms=60_000),
        message="old reminder",
        session_key="api:999",
    )
    user_store = registry.for_session_key("api:999")

    assert legacy.id in {j.id for j in user_store.list_jobs()}
    assert legacy.id not in {j.id for j in registry.default.list_jobs(include_disabled=True)}


@pytest.mark.asyncio
async def test_registry_starts_lazy_user_services(cron_layout: tuple[CronRegistry, StubAgent]) -> None:
    registry, _agent = cron_layout
    await registry.start()
    user_store = registry.for_session_key("api:555")
    await registry.ensure_started(user_store)
    assert user_store.running is True
