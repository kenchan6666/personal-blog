"""Stable error semantics for nanobot MCP tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    AUTH_DENIED = "AUTH_DENIED"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    STATE_CONFLICT = "STATE_CONFLICT"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass(slots=True)
class NanobotError(Exception):
    code: ErrorCode
    message: str
    context: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "ok": False,
            "error": {
                "code": self.code.value,
                "message": self.message,
                "context": self.context,
            },
        }


def error_payload(
    code: ErrorCode,
    message: str,
    *,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return NanobotError(code=code, message=message, context=context or {}).to_payload()
