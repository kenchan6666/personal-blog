from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
NANOBOT_SRC = ROOT / "mcp_service" / "mcp_nanobot"
if str(NANOBOT_SRC) not in sys.path:
    sys.path.insert(0, str(NANOBOT_SRC))

from mcp_nanobot.audit import AuditRecorder
from mcp_nanobot.auth import AuthorizationGuard
from mcp_nanobot.config import NanobotConfig, RolloutPolicy
from mcp_nanobot.schemas import InMemoryNanobotStore
from mcp_nanobot.tools.task_tools import TaskTools


def test_rollout_rollback_disables_write() -> None:
    store = InMemoryNanobotStore()
    audit = AuditRecorder()

    writable = TaskTools(
        store=store,
        auth=AuthorizationGuard(
            NanobotConfig(
                allowed_bearers={"token-ok"},
                rollout=RolloutPolicy(write_enabled=True, read_only_mode=False),
            )
        ),
        audit=audit,
    )
    assert writable.task_create(title="stage", bearer="token-ok")["ok"] is True

    rolled_back = TaskTools(
        store=store,
        auth=AuthorizationGuard(
            NanobotConfig(
                allowed_bearers={"token-ok"},
                rollout=RolloutPolicy(write_enabled=False, read_only_mode=True),
            )
        ),
        audit=audit,
    )
    denied = rolled_back.task_create(title="blocked", bearer="token-ok")
    assert denied["ok"] is False
    assert denied["error"]["code"] == "AUTH_DENIED"
