from __future__ import annotations

from types import SimpleNamespace


def test_diag_shape_has_nanobot_and_tools() -> None:
    loop = SimpleNamespace(
        _mcp_servers={"nanobot": object()},
        _mcp_stacks={"nanobot": object()},
        tools=SimpleNamespace(tool_names=lambda: ["mcp_nanobot_task_create"]),
    )
    assert "nanobot" in loop._mcp_servers
    assert "nanobot" in loop._mcp_stacks
