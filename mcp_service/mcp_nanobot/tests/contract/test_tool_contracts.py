from __future__ import annotations

from mcp_nanobot.errors import ErrorCode


def test_error_code_contract_stable() -> None:
    assert ErrorCode.AUTH_DENIED.value == "AUTH_DENIED"
    assert ErrorCode.INVALID_ARGUMENT.value == "INVALID_ARGUMENT"
    assert ErrorCode.STATE_CONFLICT.value == "STATE_CONFLICT"
    assert ErrorCode.DEPENDENCY_UNAVAILABLE.value == "DEPENDENCY_UNAVAILABLE"
    assert ErrorCode.TIMEOUT.value == "TIMEOUT"
    assert ErrorCode.INTERNAL_ERROR.value == "INTERNAL_ERROR"
