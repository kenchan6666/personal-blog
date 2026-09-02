"""
Seam: Mailer protocol.
Ticket: Owner email OTP login — SMTP fallback when outbound mail is blocked.
"""

from __future__ import annotations

import pytest

from app.mailer import RecordingMailer, SmtpThenConsoleMailer


class _FailingMailer:
    async def send_otp(self, *, to: str, code: str) -> None:
        raise TimeoutError("timed out")


@pytest.mark.asyncio
async def test_smtp_fallback_prints_otp_when_smtp_fails():
    recorded = RecordingMailer()
    mailer = SmtpThenConsoleMailer(smtp=_FailingMailer(), console=recorded)
    await mailer.send_otp(to="ynchanhk@gmail.com", code="123456")
    assert recorded.sent == [{"to": "ynchanhk@gmail.com", "code": "123456"}]
