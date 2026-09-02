"""Authorization guards for nanobot MCP tools."""

from __future__ import annotations

from dataclasses import dataclass

from mcp_nanobot.config import NanobotConfig
from mcp_nanobot.errors import ErrorCode, NanobotError


def _extract_bearer(raw: str | None) -> str:
    if not raw:
        return ""
    text = raw.strip()
    if text.lower().startswith("bearer "):
        return text[7:].strip()
    return text


@dataclass(slots=True)
class AuthContext:
    bearer: str | None = None


class AuthorizationGuard:
    def __init__(self, config: NanobotConfig):
        self._config = config

    def require_write(self, auth: AuthContext) -> None:
        if not self._config.rollout.allow_write():
            raise NanobotError(
                ErrorCode.AUTH_DENIED,
                "write operations are disabled by rollout policy",
            )
        self._require_bearer(auth)

    def require_read(self, auth: AuthContext) -> None:
        self._require_bearer(auth)

    def _require_bearer(self, auth: AuthContext) -> None:
        if not self._config.allowed_bearers:
            return
        bearer = _extract_bearer(auth.bearer)
        if not bearer or bearer not in self._config.allowed_bearers:
            raise NanobotError(
                ErrorCode.AUTH_DENIED,
                "request is not authorized",
            )
