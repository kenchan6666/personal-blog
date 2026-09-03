from __future__ import annotations

import asyncio

import httpx
import pytest

from app.agent_limits import (
    acquire_public_inflight,
    clamp_concurrency,
    owner_turn_available,
    owner_turns_busy,
    release_public_inflight,
)
from app.transport import is_retryable_transport_error


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    async def decr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) - 1
        return self.values[key]

    async def expire(self, key: str, ttl: int) -> None:
        self.expirations[key] = ttl

    async def delete(self, key: str) -> None:
        self.values.pop(key, None)
        self.expirations.pop(key, None)


class FakeTask:
    def __init__(self, done: bool) -> None:
        self._done = done

    def done(self) -> bool:
        return self._done


def test_clamp_concurrency_stays_in_range() -> None:
    assert clamp_concurrency(0) == 1
    assert clamp_concurrency(3) == 3
    assert clamp_concurrency(99) == 32
    assert clamp_concurrency("nope") == 3  # type: ignore[arg-type]


def test_owner_turn_gate_counts_only_running_tasks() -> None:
    turns = {
        "a": FakeTask(False),
        "b": FakeTask(True),
        "c": FakeTask(False),
        "d": None,
    }
    assert owner_turns_busy(turns) == 2
    assert owner_turn_available(turns, 3) is True
    assert owner_turn_available(turns, 2) is False


@pytest.mark.asyncio
async def test_public_inflight_rejects_over_cap_and_releases() -> None:
    redis = FakeRedis()
    assert await acquire_public_inflight(redis, 2) is True
    assert await acquire_public_inflight(redis, 2) is True
    assert await acquire_public_inflight(redis, 2) is False
    assert redis.values["public-agent:inflight"] == 2
    await release_public_inflight(redis)
    await release_public_inflight(redis)
    assert "public-agent:inflight" not in redis.values


def test_transport_retry_only_for_connection_failures() -> None:
    class APIConnectionError(Exception):
        pass

    assert is_retryable_transport_error(httpx.ConnectError("down"))
    assert is_retryable_transport_error(httpx.RemoteProtocolError("cut"))
    assert is_retryable_transport_error(APIConnectionError("upstream"))
    assert not is_retryable_transport_error(
        httpx.HTTPStatusError(
            "nope",
            request=httpx.Request("POST", "https://example.com"),
            response=httpx.Response(429),
        )
    )
    assert not is_retryable_transport_error(ValueError("bad json"))
    assert not is_retryable_transport_error(asyncio.TimeoutError())
