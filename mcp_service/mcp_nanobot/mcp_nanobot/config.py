"""Configuration and rollout policy for nanobot MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


@dataclass(slots=True)
class RolloutPolicy:
    write_enabled: bool
    read_only_mode: bool

    def allow_write(self) -> bool:
        return self.write_enabled and not self.read_only_mode


@dataclass(slots=True)
class NanobotConfig:
    allowed_bearers: set[str]
    rollout: RolloutPolicy
    max_run_retries: int = 3

    @classmethod
    def from_env(cls) -> "NanobotConfig":
        allowed = {
            token.strip()
            for token in os.environ.get("NANOBOT_ALLOWED_BEARERS", "").split(",")
            if token.strip()
        }
        rollout = RolloutPolicy(
            write_enabled=_as_bool(os.environ.get("NANOBOT_WRITE_ENABLED"), default=False),
            read_only_mode=_as_bool(os.environ.get("NANOBOT_READ_ONLY_MODE"), default=True),
        )
        return cls(allowed_bearers=allowed, rollout=rollout)
