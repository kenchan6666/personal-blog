import asyncio

from aiohttp.client_exceptions import ClientConnectionResetError

from viola.api.server import (
    _is_sse_disconnect,
    _timeout_notice,
    _write_sse,
)
from viola.providers.openai_compat_provider import (
    _openai_compat_idle_timeout_s,
    _openai_compat_timeout_s,
)


def test_timeout_notice_tells_the_owner_the_turn_stopped() -> None:
    text = _timeout_notice(120)
    assert "120" in text
    assert "已停止" in text


def test_openai_compat_timeouts_cover_long_tool_turns() -> None:
    assert _openai_compat_timeout_s() >= 300
    assert _openai_compat_idle_timeout_s() >= 180


def test_sse_disconnect_includes_aiohttp_reset() -> None:
    assert _is_sse_disconnect(ClientConnectionResetError("Cannot write to closing transport"))
    assert _is_sse_disconnect(ConnectionResetError())
    assert not _is_sse_disconnect(ValueError("nope"))


def test_write_sse_returns_false_when_the_browser_is_gone() -> None:
    class ClosingResponse:
        async def write(self, _data: bytes) -> None:
            raise ClientConnectionResetError("Cannot write to closing transport")

    assert asyncio.run(_write_sse(ClosingResponse(), b": keepalive\n\n")) is False
