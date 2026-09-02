from __future__ import annotations

from typing import Protocol

import httpx


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


class ResendMailer:
    """HTTPS mail. Works from GCP because it uses 443, not SMTP 587."""

    def __init__(
        self,
        *,
        api_key: str,
        from_addr: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key
        self.from_addr = from_addr
        self.client = client

    async def send_otp(self, *, to: str, code: str) -> None:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "from": self.from_addr,
            "to": [to],
            "subject": "Your portfolio admin login code",
            "text": f"Your one-time code is: {code}\n\nIt expires shortly.",
        }
        if self.client is not None:
            response = await self.client.post(
                "https://api.resend.com/emails",
                headers=headers,
                json=payload,
            )
        else:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers=headers,
                    json=payload,
                )
        if response.status_code >= 400:
            raise RuntimeError(f"resend_{response.status_code}: {response.text}")


class SmtpThenConsoleMailer:
    """Try the primary mailer, then print OTP so Owner can still sign in."""

    def __init__(self, smtp: Mailer, console: Mailer | None = None) -> None:
        self.smtp = smtp
        self.console = console or ConsoleMailer()

    async def send_otp(self, *, to: str, code: str) -> None:
        try:
            await self.smtp.send_otp(to=to, code=code)
        except Exception as exc:
            print(
                "[mail] send failed "
                f"({type(exc).__name__}: {exc}). "
                "OTP is printed below so Owner can still sign in.",
                flush=True,
            )
            await self.console.send_otp(to=to, code=code)
