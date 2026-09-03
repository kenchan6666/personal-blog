from __future__ import annotations

import pytest

from app.github_token import persist_github_owner_token, restore_github_owner_token
from app.main import GITHUB_TOKEN_KEY


@pytest.mark.asyncio
async def test_github_token_is_restored_from_store_after_redis_loss(app) -> None:
    redis = app.state.redis
    await persist_github_owner_token("restored-github-token")
    await redis.delete(GITHUB_TOKEN_KEY)
    assert await redis.get(GITHUB_TOKEN_KEY) is None

    await restore_github_owner_token(redis, GITHUB_TOKEN_KEY)

    assert await redis.get(GITHUB_TOKEN_KEY) == "restored-github-token"
    assert await redis.ttl(GITHUB_TOKEN_KEY) == -1
