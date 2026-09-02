from __future__ import annotations

import pytest

from mcp_nanobot.audit import AuditRecorder
from mcp_nanobot.auth import AuthorizationGuard
from mcp_nanobot.config import NanobotConfig, RolloutPolicy
from mcp_nanobot.schemas import InMemoryNanobotStore
from mcp_nanobot.tools import ReportTools, RunTools, TaskTools


@pytest.fixture
def store() -> InMemoryNanobotStore:
    return InMemoryNanobotStore()


@pytest.fixture
def config() -> NanobotConfig:
    return NanobotConfig(
        allowed_bearers={"token-ok"},
        rollout=RolloutPolicy(write_enabled=True, read_only_mode=False),
    )


@pytest.fixture
def auth(config: NanobotConfig) -> AuthorizationGuard:
    return AuthorizationGuard(config)


@pytest.fixture
def audit() -> AuditRecorder:
    return AuditRecorder()


@pytest.fixture
def task_tools(
    store: InMemoryNanobotStore,
    auth: AuthorizationGuard,
    audit: AuditRecorder,
) -> TaskTools:
    return TaskTools(store=store, auth=auth, audit=audit)


@pytest.fixture
def run_tools(
    store: InMemoryNanobotStore,
    auth: AuthorizationGuard,
    audit: AuditRecorder,
    config: NanobotConfig,
) -> RunTools:
    return RunTools(store=store, auth=auth, audit=audit, config=config)


@pytest.fixture
def report_tools(store: InMemoryNanobotStore, auth: AuthorizationGuard) -> ReportTools:
    return ReportTools(store=store, auth=auth)
