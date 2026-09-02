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


def test_task_flow_closed_loop() -> None:
    tools = TaskTools(
        store=InMemoryNanobotStore(),
        auth=AuthorizationGuard(
            NanobotConfig(
                allowed_bearers={"token-ok"},
                rollout=RolloutPolicy(write_enabled=True, read_only_mode=False),
            )
        ),
        audit=AuditRecorder(),
    )
    created = tools.task_create(title="A", bearer="token-ok")
    task_id = created["task"]["task_id"]
    fetched = tools.task_get(task_id=task_id, bearer="token-ok")
    updated = tools.task_update(task_id=task_id, updates={"description": "B"}, bearer="token-ok")
    transitioned = tools.task_transition(task_id=task_id, to_status="in_progress", bearer="token-ok")

    assert created["ok"] and fetched["ok"] and updated["ok"] and transitioned["ok"]
