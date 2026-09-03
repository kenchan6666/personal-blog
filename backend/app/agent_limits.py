from __future__ import annotations

from typing import Any

PUBLIC_INFLIGHT_KEY = "public-agent:inflight"


def clamp_concurrency(value: int, *, default: int = 3, lo: int = 1, hi: int = 32) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(hi, max(lo, parsed))


def owner_turns_busy(turns: dict[str, Any] | None) -> int:
    running = 0
    for task in (turns or {}).values():
        if task is not None and not getattr(task, "done", lambda: True)():
            running += 1
    return running


def owner_turn_available(turns: dict[str, Any] | None, limit: int) -> bool:
    return owner_turns_busy(turns) < clamp_concurrency(limit, default=3)


async def acquire_public_inflight(
    redis: Any,
    limit: int,
    *,
    ttl: int = 300,
    key: str = PUBLIC_INFLIGHT_KEY,
) -> bool:
    cap = clamp_concurrency(limit, default=4)
    value = await redis.incr(key)
    expire = getattr(redis, "expire", None)
    if callable(expire):
        await expire(key, ttl)
    if int(value) > cap:
        await redis.decr(key)
        return False
    return True


async def release_public_inflight(
    redis: Any,
    *,
    key: str = PUBLIC_INFLIGHT_KEY,
) -> None:
    deleter = getattr(redis, "delete", None)
    try:
        value = int(await redis.decr(key))
    except Exception:
        return
    if value <= 0 and callable(deleter):
        await deleter(key)
