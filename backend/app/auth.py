from __future__ import annotations

import hashlib
import secrets

from fastapi import HTTPException, status
from redis.asyncio import Redis

from app.config import Settings
from app.mailer import Mailer

SESSION_COOKIE = "portfolio_session"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _otp_key(email: str) -> str:
    return f"otp:code:{email.lower()}"


def _rate_key(email: str) -> str:
    return f"otp:rate:{email.lower()}"


def _fail_key(kind: str, subject: str) -> str:
    return f"otp:fail:{kind}:{subject.lower()}"


def _lock_key(kind: str, subject: str) -> str:
    return f"otp:lock:{kind}:{subject.lower()}"


def _session_key(token: str) -> str:
    # Only a hash of the token is stored, so a Redis dump cannot be replayed
    # as a browser session.
    return f"session:v2:{_digest(token)}"


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

    def _subjects(self, email: str, ip: str | None) -> list[tuple[str, str]]:
        subjects = [("email", email)]
        if ip:
            subjects.append(("ip", ip))
        return subjects

    async def _ensure_not_locked(self, email: str, ip: str | None) -> None:
        for kind, subject in self._subjects(email, ip):
            if await self.redis.get(_lock_key(kind, subject)):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="otp_locked",
                )

    async def _record_failure(self, email: str, ip: str | None) -> None:
        limit = self.settings.otp_verify_max_failures
        window = self.settings.otp_verify_lock_seconds
        locked = False
        for kind, subject in self._subjects(email, ip):
            key = _fail_key(kind, subject)
            count = await self.redis.incr(key)
            if count == 1:
                await self.redis.expire(key, window)
            if count >= limit:
                await self.redis.set(_lock_key(kind, subject), "1", ex=window)
                await self.redis.delete(key)
                locked = True
        if locked:
            # Burn the outstanding code so guessing cannot resume after the lock.
            await self.redis.delete(_otp_key(email))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="otp_locked",
            )

    async def request_otp(self, email: str, ip: str | None = None) -> None:
        email = self._ensure_owner(email)
        await self._ensure_not_locked(email, ip)
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
            _digest(code),
            ex=self.settings.otp_ttl_seconds,
        )
        await self.mailer.send_otp(to=email, code=code)

    async def verify_otp(self, email: str, code: str, ip: str | None = None) -> str:
        email = self._ensure_owner(email)
        await self._ensure_not_locked(email, ip)
        stored = await self.redis.get(_otp_key(email))
        candidate = _digest(code.strip())
        if stored is None or not secrets.compare_digest(str(stored), candidate):
            await self._record_failure(email, ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid_otp",
            )
        # One-time use: drop the code and reset failure counters.
        await self.redis.delete(_otp_key(email))
        for kind, subject in self._subjects(email, ip):
            await self.redis.delete(_fail_key(kind, subject))
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

    async def revoke_session(self, token: str | None) -> None:
        if token:
            await self.redis.delete(_session_key(token))
