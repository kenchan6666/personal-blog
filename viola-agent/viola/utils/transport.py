from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from loguru import logger

T = TypeVar("T")

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
    if isinstance(exc, asyncio.TimeoutError):
        return False
    lowered = name.lower()
    if "timeout" in lowered:
        return "connect" in lowered or "read" in lowered or lowered.endswith(
            "timeoutexception"
        )
    return "connection" in lowered


async def await_with_one_retry(operation: Callable[[], Awaitable[T]]) -> T:
    try:
        return await operation()
    except Exception as exc:
        if not is_retryable_transport_error(exc):
            raise
        logger.warning("Transport error ({}), retrying once", type(exc).__name__)
        return await operation()
