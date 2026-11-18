"""
Seam: Mailer protocol.
Ticket: Owner email OTP login — SMTP fallback when outbound mail is blocked.
"""

from __future__ import annotations

import json
import os
import stat

import httpx
import pytest

from app.mailer import (
    FallbackMailer,
    FileDropMailer,
    RecordingMailer,
    ResendMailer,
    SmtpMailer,
    SmtpThenConsoleMailer,
)


class _FailingMailer:
    async def send_otp(self, *, to: str, code: str) -> None:
        raise TimeoutError("timed out")


@pytest.mark.asyncio
async def test_smtp_fallback_prints_otp_when_smtp_fails():
    recorded = RecordingMailer()
    mailer = SmtpThenConsoleMailer(smtp=_FailingMailer(), console=recorded)
    await mailer.send_otp(to="ynchanhk@gmail.com", code="123456")
    assert recorded.sent == [{"to": "ynchanhk@gmail.com", "code": "123456"}]


@pytest.mark.asyncio
async def test_resend_posts_otp_over_https():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "re_1"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        mailer = ResendMailer(
            api_key="re_test",
            from_addr="ken@kenchan0522.blog",
            client=client,
        )
        await mailer.send_otp(to="ynchanhk@gmail.com", code="123456")

    assert seen["url"] == "https://api.resend.com/emails"
    assert seen["auth"] == "Bearer re_test"
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["from"] == "ken@kenchan0522.blog"
    assert body["to"] == ["ynchanhk@gmail.com"]
    assert "123456" in str(body["text"])


class _OkMailer:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_otp(self, *, to: str, code: str) -> None:
        self.sent.append(to)


@pytest.mark.asyncio
async def test_fallback_uses_next_route_when_first_fails(capsys):
    second = _OkMailer()
    last = RecordingMailer()
    mailer = FallbackMailer(
        [("resend", _FailingMailer()), ("smtp", second)],
        last_resort=last,
    )
    await mailer.send_otp(to="ynchanhk@gmail.com", code="654321")
    assert second.sent == ["ynchanhk@gmail.com"]
    assert last.sent == []
    out = capsys.readouterr().out
    assert "resend failed" in out
    assert "654321" not in out


@pytest.mark.asyncio
async def test_all_routes_failing_writes_owner_only_file(tmp_path, capsys):
    target = tmp_path / "otp" / "latest.txt"
    mailer = FallbackMailer(
        [("resend", _FailingMailer()), ("smtp", _FailingMailer())],
        last_resort=FileDropMailer(str(target)),
    )
    await mailer.send_otp(to="ynchanhk@gmail.com", code="246810")
    assert "code=246810" in target.read_text()
    assert stat.S_IMODE(os.stat(target).st_mode) == 0o600
    assert "246810" not in capsys.readouterr().out


def test_resend_backend_chains_gmail_smtp_when_password_set():
    from app.config import Settings
    from app.main import _build_mail_chain

    settings = Settings(
        mail_backend="resend",
        resend_api_key="re_test",
        resend_from="ken@kenchan0522.blog",
        smtp_user="ynchanhk@gmail.com",
        smtp_from="ynchanhk@gmail.com",
        smtp_password="app password",
    )
    chain = _build_mail_chain(settings, "resend")
    assert isinstance(chain, FallbackMailer)
    assert [name for name, _ in chain.routes] == ["resend", "smtp"]
    resend = chain.routes[0][1]
    smtp = chain.routes[1][1]
    assert isinstance(resend, ResendMailer) and resend.from_addr == "ken@kenchan0522.blog"
    assert isinstance(smtp, SmtpMailer) and smtp.from_addr == "ynchanhk@gmail.com"

    settings.smtp_password = ""
    chain = _build_mail_chain(settings, "resend")
    assert [name for name, _ in chain.routes] == ["resend"]
