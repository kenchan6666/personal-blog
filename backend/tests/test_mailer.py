"""
Seam: Mailer protocol.
Ticket: Owner email OTP login — SMTP fallback when outbound mail is blocked.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.mailer import RecordingMailer, ResendMailer, SmtpThenConsoleMailer


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
