"""
Seam under test: Portfolio HTTP API (FastAPI) — agreed in to-spec.
Ticket: #2 Portfolio API foundation.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_returns_ok_when_mongo_and_redis_are_up(client):
    response = await client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mongo"] in {"up", "local"}
    assert body["redis"] == "up"
