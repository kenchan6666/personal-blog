from __future__ import annotations

from typing import Protocol


class Mailer(Protocol):
    async def send_otp(self, *, to: str, code: str) -> None: ...


class RecordingMailer:
    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    async def send_otp(self, *, to: str, code: str) -> None:
        self.sent.append({"to": to, "code": code})


class ConsoleMailer:
    """Local/dev mailer: prints OTP to the API process stdout."""

    async def send_otp(self, *, to: str, code: str) -> None:
        print(f"[otp] to={to} code={code}", flush=True)


class SmtpMailer:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        from_addr: str,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_addr = from_addr

    async def send_otp(self, *, to: str, code: str) -> None:
        import asyncio
        import smtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["Subject"] = "Your portfolio admin login code"
        msg["From"] = self.from_addr
        msg["To"] = to
        msg.set_content(f"Your one-time code is: {code}\n\nIt expires shortly.")

        password = self.password.replace(" ", "")

        def _send() -> None:
            with smtplib.SMTP(self.host, self.port, timeout=20) as smtp:
                smtp.starttls()
                smtp.login(self.username, password)
                smtp.send_message(msg)

        await asyncio.to_thread(_send)
