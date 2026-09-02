"""Tests for new-session commands (/new, start fresh, etc.)."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from viola.bus.events import InboundMessage
from viola.command.builtin import cmd_new, is_new_session_command, register_builtin_commands
from viola.command.router import CommandContext, CommandRouter
from viola.session.goal_state import GOAL_STATE_KEY
from viola.session.manager import SessionManager


@pytest.mark.parametrize(
    "raw",
    [
        "/new",
        "/NEW",
        "  /reset  ",
        "/clear",
        "start fresh",
        "Start Over",
        "state refresh",
        "Refresh State",
    ],
)
def test_is_new_session_command(raw: str) -> None:
    assert is_new_session_command(raw)


@pytest.mark.parametrize("raw", ["/help", "hello", "fresh start"])
def test_is_new_session_command_rejects_non_aliases(raw: str) -> None:
    assert not is_new_session_command(raw)


def test_router_registers_new_session_aliases() -> None:
    router = CommandRouter()
    register_builtin_commands(router)
    for command in (
        "/new",
        "/reset",
        "/clear",
        "start fresh",
        "start over",
        "state refresh",
        "refresh state",
    ):
        assert router.is_dispatchable_command(command)


@pytest.mark.asyncio
async def test_cmd_new_clears_session_messages_and_metadata(tmp_path) -> None:
    sessions = SessionManager(tmp_path)
    session = sessions.get_or_create("cli:test")
    session.add_message("user", "hello")
    session.add_message("assistant", "hi")
    session.metadata["_last_summary"] = {
        "text": "Old summary.",
        "last_active": datetime.now().isoformat(),
    }
    session.metadata[GOAL_STATE_KEY] = {
        "status": "active",
        "objective": "finish docs",
    }
    session.metadata["pending_user_turn"] = True
    sessions.save(session)

    loop = MagicMock()
    loop.sessions = sessions
    loop.consolidator = MagicMock(archive=AsyncMock(return_value=True))
    loop._cancel_active_tasks = AsyncMock(return_value=0)
    loop._schedule_background = MagicMock()
    loop.auto_compact = MagicMock(_summaries={}, _archiving=set())
    loop.bus = MagicMock(publish_outbound=AsyncMock())

    msg = InboundMessage(channel="cli", sender_id="user", chat_id="test", content="/new")
    ctx = CommandContext(msg=msg, session=None, key="cli:test", raw="/new", loop=loop)

    result = await cmd_new(ctx)

    assert "New session started" in result.content
    sessions.invalidate("cli:test")
    fresh = sessions.get_or_create("cli:test")
    assert fresh.messages == []
    assert "_last_summary" not in fresh.metadata
    assert GOAL_STATE_KEY not in fresh.metadata
    assert "pending_user_turn" not in fresh.metadata


@pytest.mark.asyncio
async def test_cmd_new_clears_auto_compact_summary_cache(tmp_path) -> None:
    sessions = SessionManager(tmp_path)
    session = sessions.get_or_create("cli:test")
    session.add_message("user", "hello")
    sessions.save(session)

    loop = MagicMock()
    loop.sessions = sessions
    loop.consolidator = MagicMock(archive=AsyncMock(return_value=True))
    loop._cancel_active_tasks = AsyncMock(return_value=0)
    loop._schedule_background = MagicMock()
    loop.auto_compact = MagicMock(
        _summaries={"cli:test": ("Summary.", datetime.now())},
        _archiving={"cli:test"},
    )
    loop.bus = MagicMock(publish_outbound=AsyncMock())

    msg = InboundMessage(
        channel="cli", sender_id="user", chat_id="test", content="start fresh",
    )
    ctx = CommandContext(
        msg=msg, session=None, key="cli:test", raw="start fresh", loop=loop,
    )

    await cmd_new(ctx)

    assert "cli:test" not in loop.auto_compact._summaries
    assert "cli:test" not in loop.auto_compact._archiving


def test_extract_body_line_strips_metadata_headers() -> None:
    """_extract_body_line returns the last non-bracket line (the actual user body)."""
    from viola.agent.loop import _extract_body_line

    whatsapp_new = (
        "[User profile name: Jing Wang]\n"
        "[Sender mobile_digits: 85212345678]\n"
        "[Backend-Bearer: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...]\n"
        "/new"
    )
    assert _extract_body_line(whatsapp_new) == "/new"
    assert _extract_body_line("[User profile name: X]\nstart fresh") == "start fresh"
    assert _extract_body_line("/new") == "/new"
    assert _extract_body_line("hello world") == "hello world"


@pytest.mark.asyncio
async def test_cmd_new_fires_with_metadata_prefix(tmp_path) -> None:
    """When the Twilio webhook prepends metadata headers, /new still clears the session."""
    sessions = SessionManager(tmp_path)
    session = sessions.get_or_create("api:+85200000000")
    session.add_message("user", "update nanoproject")
    session.add_message("assistant", "Updated.")
    sessions.save(session)

    loop = MagicMock()
    loop.sessions = sessions
    loop.consolidator = MagicMock(archive=AsyncMock(return_value=True))
    loop._cancel_active_tasks = AsyncMock(return_value=0)
    loop._schedule_background = MagicMock()
    loop.auto_compact = MagicMock(_summaries={}, _archiving=set())
    loop.bus = MagicMock(publish_outbound=AsyncMock())

    whatsapp_payload = (
        "[User profile name: Jing Wang]\n"
        "[Sender mobile_digits: 85200000000]\n"
        "[Backend-Bearer: eyJtoken]\n"
        "/new"
    )
    msg = InboundMessage(
        channel="api", sender_id="user", chat_id="+85200000000", content=whatsapp_payload,
    )
    ctx = CommandContext(
        msg=msg, session=None, key="api:+85200000000", raw=whatsapp_payload, loop=loop,
    )

    result = await cmd_new(ctx)
    assert "New session started" in result.content
    sessions.invalidate("api:+85200000000")
    fresh = sessions.get_or_create("api:+85200000000")
    assert fresh.messages == []


def test_get_history_skips_command_messages(tmp_path) -> None:
    sessions = SessionManager(tmp_path)
    session = sessions.get_or_create("cli:test")
    session.add_message("user", "real question")
    session.add_message("assistant", "real answer")
    session.add_message("user", "/help", _command=True)
    session.add_message("assistant", "help text", _command=True)

    history = session.get_history()

    assert len(history) == 2
    assert all(m["content"] != "/help" for m in history)
    assert all(m["content"] != "help text" for m in history)
