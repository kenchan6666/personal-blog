from __future__ import annotations

from typing import Any

from app.models import OwnerSecret, utc_now
from app.store import current_store, new_document

GITHUB_SECRET_NAME = "github_owner_token"


async def persist_github_owner_token(token: str) -> None:
    value = (token or "").strip()
    if not value:
        return
    store = current_store()
    row = await store.find_one(OwnerSecret, name=GITHUB_SECRET_NAME)
    if row is None:
        await store.insert(new_document(OwnerSecret, name=GITHUB_SECRET_NAME, value=value))
        return
    row.value = value
    row.updated_at = utc_now()
    await store.save(row)


async def load_github_owner_token() -> str:
    row = await current_store().find_one(OwnerSecret, name=GITHUB_SECRET_NAME)
    if row is None:
        return ""
    return (row.value or "").strip()


async def restore_github_owner_token(redis: Any, redis_key: str) -> None:
    if await redis.get(redis_key):
        return
    stored = await load_github_owner_token()
    if stored:
        await redis.set(redis_key, stored)
