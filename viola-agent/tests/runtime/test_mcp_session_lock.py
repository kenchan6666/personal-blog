from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from viola.agent.tools.mcp import MCPToolWrapper, mcp_session_lock
from viola.utils.transport import await_with_one_retry, is_retryable_transport_error


class FakeSession:
    def __init__(self) -> None:
        self.in_flight = 0
        self.max_in_flight = 0
        self.calls = 0

    async def call_tool(self, name: str, arguments=None):
        self.calls += 1
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        await asyncio.sleep(0.05)
        self.in_flight -= 1
        return SimpleNamespace(content=[])


def test_transport_retry_skips_idle_timeout_and_http_errors() -> None:
    class APIConnectionError(Exception):
        pass

    assert is_retryable_transport_error(APIConnectionError("down"))
    assert not is_retryable_transport_error(asyncio.TimeoutError())
    assert not is_retryable_transport_error(ValueError("no"))


@pytest.mark.asyncio
async def test_await_with_one_retry_retries_connection_once() -> None:
    class APIConnectionError(Exception):
        pass

    calls = {"n": 0}

    async def flaky() -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            raise APIConnectionError("once")
        return "ok"

    assert await await_with_one_retry(flaky) == "ok"
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_mcp_tools_on_one_session_do_not_overlap() -> None:
    session = FakeSession()
    tool_def = SimpleNamespace(
        name="list_content",
        description="list",
        inputSchema={"type": "object", "properties": {}},
    )
    first = MCPToolWrapper(session, "portfolio", tool_def)
    second = MCPToolWrapper(session, "portfolio", tool_def)
    await asyncio.gather(first.execute(), second.execute())
    assert session.calls == 2
    assert session.max_in_flight == 1
    assert mcp_session_lock(session) is mcp_session_lock(session)
