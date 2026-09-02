from __future__ import annotations

from mcp_nanobot.auth import AuthContext
from mcp_nanobot.config import NanobotConfig, RolloutPolicy
from mcp_nanobot.errors import ErrorCode, NanobotError
from mcp_nanobot.auth import AuthorizationGuard


def test_require_write_denied_when_rollout_off() -> None:
    guard = AuthorizationGuard(
        NanobotConfig(
            allowed_bearers={"token-ok"},
            rollout=RolloutPolicy(write_enabled=False, read_only_mode=True),
        )
    )
    try:
        guard.require_write(AuthContext(bearer="token-ok"))
    except NanobotError as exc:
        assert exc.code == ErrorCode.AUTH_DENIED
    else:
        raise AssertionError("expected AUTH_DENIED")


def test_require_read_rejects_unknown_bearer() -> None:
    guard = AuthorizationGuard(
        NanobotConfig(
            allowed_bearers={"token-ok"},
            rollout=RolloutPolicy(write_enabled=True, read_only_mode=False),
        )
    )
    try:
        guard.require_read(AuthContext(bearer="wrong"))
    except NanobotError as exc:
        assert exc.code == ErrorCode.AUTH_DENIED
    else:
        raise AssertionError("expected AUTH_DENIED")
