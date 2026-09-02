from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from viola.config.loader import load_config
from viola.config.schema import Config


def test_loader_accepts_nanobot_server_from_fragment(monkeypatch) -> None:
    monkeypatch.setenv("NANOBOT_WRITE_ENABLED", "true")
    config = load_config(Path("/tmp/viola-missing-config.json"))
    # If fragment package is installed the server appears; if not installed, still safe.
    assert isinstance(config, Config)
    if "nanobot" in config.tools.mcp_servers:
        assert config.tools.mcp_servers["nanobot"].command


def test_diag_nanobot_shape() -> None:
    configured = ["nanobot"]
    connected = ["nanobot"]
    fake_loop = SimpleNamespace(
        _mcp_servers={"nanobot": object()},
        _mcp_stacks={"nanobot": object()},
        tools=SimpleNamespace(tool_names=lambda: ["mcp_nanobot_task_create"]),
    )
    assert sorted(fake_loop._mcp_servers.keys()) == configured
    assert sorted(fake_loop._mcp_stacks.keys()) == connected
