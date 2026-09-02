"""MCP server entrypoint for nanobot tools."""

from __future__ import annotations

from typing import Any

from mcp_nanobot.audit import AuditRecorder
from mcp_nanobot.auth import AuthorizationGuard
from mcp_nanobot.config import NanobotConfig
from mcp_nanobot.schemas import InMemoryNanobotStore
from mcp_nanobot.tools import ReportTools, RunTools, TaskTools


def _build_services() -> tuple[TaskTools, RunTools, ReportTools, AuditRecorder]:
    config = NanobotConfig.from_env()
    store = InMemoryNanobotStore()
    audit = AuditRecorder()
    auth = AuthorizationGuard(config)
    return (
        TaskTools(store=store, auth=auth, audit=audit),
        RunTools(store=store, auth=auth, audit=audit, config=config),
        ReportTools(store=store, auth=auth),
        audit,
    )


def create_server() -> Any:
    """Create FastMCP server with task/run/report tool groups."""
    from mcp.server.fastmcp import FastMCP

    task_tools, run_tools, report_tools, audit = _build_services()
    server = FastMCP("nanobot")

    server.tool()(task_tools.task_create)
    server.tool()(task_tools.task_get)
    server.tool()(task_tools.task_list)
    server.tool()(task_tools.task_update)
    server.tool()(task_tools.task_transition)

    server.tool()(run_tools.run_trigger)
    server.tool()(run_tools.run_get)
    server.tool()(run_tools.run_logs)
    server.tool()(run_tools.run_cancel)
    server.tool()(run_tools.run_retry)

    server.tool()(report_tools.report_task_summary)
    server.tool()(report_tools.report_failure_breakdown)
    server.tool()(report_tools.report_runtime_latency)

    @server.tool()
    def nanobot_recent_audit(limit: int = 20) -> dict[str, Any]:
        """Read recent audit entries for diagnostics."""
        return {"ok": True, "items": audit.recent(limit=limit)}

    return server


def main() -> None:
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
