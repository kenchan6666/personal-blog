from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_agent_service_token_can_use_owner_api(client, settings) -> None:
    settings.agent_service_token = "service-token-for-test"

    response = await client.get(
        "/api/owner/site",
        headers={"Authorization": "Bearer service-token-for-test"},
    )

    assert response.status_code == 200
    assert "bio" in response.json()


@pytest.mark.asyncio
async def test_wrong_agent_service_token_is_rejected(client, settings) -> None:
    settings.agent_service_token = "service-token-for-test"

    response = await client.get(
        "/api/owner/site",
        headers={"Authorization": "Bearer wrong-token"},
    )

    assert response.status_code == 401
