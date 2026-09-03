from __future__ import annotations

from typing import Any

_RETRYABLE = frozenset(
    {
        "APIConnectionError",
        "ConnectError",
        "ConnectTimeout",
        "ReadTimeout",
        "WriteTimeout",
        "PoolTimeout",
        "RemoteProtocolError",
        "ConnectionError",
        "ConnectionResetError",
        "ConnectionAbortedError",
        "BrokenPipeError",
        "TimeoutException",
    }
)


def is_retryable_transport_error(exc: BaseException) -> bool:
    name = type(exc).__name__
    if name in _RETRYABLE:
        return True
    lowered = name.lower()
    if "timeout" in lowered and name != "TimeoutError":
        return "connect" in lowered or "read" in lowered or lowered.endswith("timeoutexception")
    return "connection" in lowered
