"""Quick smoke for nanobot MCP lifecycle."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
NANOBOT_SRC = ROOT / "mcp_service" / "mcp_nanobot"
if str(NANOBOT_SRC) not in sys.path:
    sys.path.insert(0, str(NANOBOT_SRC))

from mcp_nanobot.audit import AuditRecorder
from mcp_nanobot.auth import AuthorizationGuard
from mcp_nanobot.config import NanobotConfig, RolloutPolicy
from mcp_nanobot.schemas import InMemoryNanobotStore
from mcp_nanobot.tools.report_tools import ReportTools
from mcp_nanobot.tools.run_tools import RunTools
from mcp_nanobot.tools.task_tools import TaskTools


def main() -> int:
    config = NanobotConfig(
        allowed_bearers={"token-ok"},
        rollout=RolloutPolicy(write_enabled=True, read_only_mode=False),
    )
    store = InMemoryNanobotStore()
    auth = AuthorizationGuard(config)
    audit = AuditRecorder()
    task_tools = TaskTools(store=store, auth=auth, audit=audit)
    run_tools = RunTools(store=store, auth=auth, audit=audit, config=config)
    report_tools = ReportTools(store=store, auth=auth)

    task = task_tools.task_create(title="smoke", bearer="token-ok")
    task_id = task["task"]["task_id"]
    run = run_tools.run_trigger(task_id=task_id, bearer="token-ok")
    summary = report_tools.report_task_summary(bearer="token-ok")
    print(json.dumps({"task": task, "run": run, "summary": summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
