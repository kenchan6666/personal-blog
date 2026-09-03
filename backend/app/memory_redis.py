from __future__ import annotations

from typing import Any


class MemoryRedis:
    """In-memory Redis subset for tests when Docker Redis is unavailable."""

    def __init__(self) -> None:
        self._values: dict[str, str] = {}
        self._ttl: dict[str, int] = {}

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> str | None:
        return self._values.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool | None:
        text = str(value)
        if nx and key in self._values:
            return None
        self._values[key] = text
        if ex is None:
            self._ttl.pop(key, None)
        else:
            self._ttl[key] = ex
        return True

    async def delete(self, key: str) -> int:
        existed = int(key in self._values)
        self._values.pop(key, None)
        self._ttl.pop(key, None)
        return existed

    async def ttl(self, key: str) -> int:
        if key not in self._values:
            return -2
        return self._ttl.get(key, -1)

    async def incr(self, key: str) -> int:
        next_value = int(self._values.get(key, "0")) + 1
        self._values[key] = str(next_value)
        return next_value

    async def expire(self, key: str, ttl: int) -> bool:
        if key not in self._values:
            return False
        self._ttl[key] = ttl
        return True

    async def flushdb(self) -> bool:
        self._values.clear()
        self._ttl.clear()
        return True

    async def aclose(self) -> None:
        return None
