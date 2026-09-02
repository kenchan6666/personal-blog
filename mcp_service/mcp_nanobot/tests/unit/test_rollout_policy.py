from __future__ import annotations

from mcp_nanobot.config import NanobotConfig, RolloutPolicy
from mcp_nanobot.auth import AuthorizationGuard
from mcp_nanobot.audit import AuditRecorder
from mcp_nanobot.schemas import InMemoryNanobotStore
from mcp_nanobot.tools.task_tools import TaskTools


def test_rollout_read_only_blocks_writes() -> None:
    tools = TaskTools(
        store=InMemoryNanobotStore(),
        auth=AuthorizationGuard(
            NanobotConfig(
                allowed_bearers={"token-ok"},
                rollout=RolloutPolicy(write_enabled=True, read_only_mode=True),
            )
        ),
        audit=AuditRecorder(),
    )
    response = tools.task_create(title="x", bearer="token-ok")
    assert response["ok"] is False
    assert response["error"]["code"] == "AUTH_DENIED"
