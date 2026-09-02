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
from mcp_nanobot.tools.run_tools import RunTools
from mcp_nanobot.tools.task_tools import TaskTools


def test_run_trigger_get_cancel_retry() -> None:
    store = InMemoryNanobotStore()
    auth = AuthorizationGuard(
        NanobotConfig(
            allowed_bearers={"token-ok"},
            rollout=RolloutPolicy(write_enabled=True, read_only_mode=False),
        )
    )
    audit = AuditRecorder()
    task_tools = TaskTools(store=store, auth=auth, audit=audit)
    run_tools = RunTools(
        store=store,
        auth=auth,
        audit=audit,
        config=NanobotConfig(
            allowed_bearers={"token-ok"},
            rollout=RolloutPolicy(write_enabled=True, read_only_mode=False),
            max_run_retries=3,
        ),
    )

    task_id = task_tools.task_create(title="X", bearer="token-ok")["task"]["task_id"]
    run_id = run_tools.run_trigger(task_id=task_id, bearer="token-ok")["run"]["run_id"]
    assert run_tools.run_get(run_id=run_id, bearer="token-ok")["ok"] is True
    run_tools.run_cancel(run_id=run_id, bearer="token-ok")
    retried = run_tools.run_retry(run_id=run_id, bearer="token-ok")
    assert retried["ok"] is True
