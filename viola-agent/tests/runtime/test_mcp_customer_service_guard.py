from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
for name in list(sys.modules.keys()):
    if name == "viola" or name.startswith("viola."):
        sys.modules.pop(name, None)

mcp_tools = importlib.import_module("viola.agent.tools.mcp")


def test_mutating_mcp_tool_detection() -> None:
    assert mcp_tools._is_mutating_mcp_tool("projects_create") is True
    assert mcp_tools._is_mutating_mcp_tool("projects_update") is True
    assert mcp_tools._is_mutating_mcp_tool("projects_delete") is True
    assert mcp_tools._is_mutating_mcp_tool("projects_search") is False
    assert mcp_tools._is_mutating_mcp_tool("projects_get") is False


def test_customer_service_only_defaults_to_on(monkeypatch) -> None:
    monkeypatch.delenv("VIOLA_CUSTOMER_SERVICE_ONLY", raising=False)
    assert mcp_tools._customer_service_only_enabled() is True


def test_customer_service_only_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("VIOLA_CUSTOMER_SERVICE_ONLY", "0")
    assert mcp_tools._customer_service_only_enabled() is False
