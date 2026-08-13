from __future__ import annotations

import secrets

from fastapi import HTTPException, status
from redis.asyncio import Redis

from app.config import Settings
from app.mailer import Mailer


def _otp_key(email: str) -> str:
    return f"otp:code:{email.lower()}"


def _rate_key(email: str) -> str:
    return f"otp:rate:{email.lower()}"


def _session_key(token: str) -> str:
    return f"session:{token}"


class AuthService:
    def __init__(self, *, redis: Redis, settings: Settings, mailer: Mailer) -> None:
        self.redis = redis
        self.settings = settings
        self.mailer = mailer

    def _normalize(self, email: str) -> str:
        return email.strip().lower()

    def _ensure_owner(self, email: str) -> str:
        normalized = self._normalize(email)
        if normalized != self.settings.owner_email.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="email_not_allowed",
            )
        return normalized

    async def request_otp(self, email: str) -> None:
        email = self._ensure_owner(email)
        rate_key = _rate_key(email)
        count = await self.redis.incr(rate_key)
        if count == 1:
            await self.redis.expire(rate_key, self.settings.otp_rate_window_seconds)
        if count > self.settings.otp_rate_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate_limited",
            )

        code = f"{secrets.randbelow(1_000_000):06d}"
        await self.redis.set(
            _otp_key(email),
            code,
            ex=self.settings.otp_ttl_seconds,
        )
        await self.mailer.send_otp(to=email, code=code)

    async def verify_otp(self, email: str, code: str) -> str:
        email = self._ensure_owner(email)
        stored = await self.redis.get(_otp_key(email))
        if stored is None or stored != code.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid_otp",
            )
        await self.redis.delete(_otp_key(email))
        token = secrets.token_urlsafe(32)
        await self.redis.set(
            _session_key(token),
            email,
            ex=self.settings.session_ttl_seconds,
        )
        return token

    async def resolve_session(self, token: str | None) -> str:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="unauthorized",
            )
        email = await self.redis.get(_session_key(token))
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="unauthorized",
            )
        return email
