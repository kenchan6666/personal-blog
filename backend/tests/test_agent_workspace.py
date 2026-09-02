from __future__ import annotations

import pytest


def owner_headers(settings) -> dict[str, str]:
    settings.agent_service_token = "agent-workspace-test-token"
    settings.uni_api_key = ""
    return {"Authorization": "Bearer agent-workspace-test-token"}


@pytest.mark.asyncio
async def test_agent_conversation_history_is_persistent(client, settings) -> None:
    headers = owner_headers(settings)

    created = await client.post(
        "/api/owner/agent/conversations",
        headers=headers,
        json={"title": "项目构思"},
    )
    assert created.status_code == 200
    conversation_id = created.json()["id"]

    listed = await client.get(
        "/api/owner/agent/conversations",
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == conversation_id
    assert listed.json()[0]["title"] == "项目构思"

    loaded = await client.get(
        f"/api/owner/agent/conversations/{conversation_id}",
        headers=headers,
    )
    assert loaded.status_code == 200
    assert loaded.json()["messages"] == []


@pytest.mark.asyncio
async def test_about_me_knowledge_can_be_edited(client, settings) -> None:
    headers = owner_headers(settings)
    body = {
        "title": "后端开发经历",
        "category": "experience",
        "content": "我使用 Python 和 FastAPI 开发个人项目。",
        "tags": ["Python", "FastAPI"],
        "order": 10,
    }

    created = await client.post(
        "/api/owner/agent/knowledge",
        headers=headers,
        json=body,
    )
    assert created.status_code == 200
    record_id = created.json()["id"]
    assert created.json()["vectorSynced"] is False
    assert created.json()["vectorSyncError"] == "embedding_not_configured"

    body["content"] = "我使用 Python、FastAPI 和 MongoDB 开发个人项目。"
    updated = await client.put(
        f"/api/owner/agent/knowledge/{record_id}",
        headers=headers,
        json=body,
    )
    assert updated.status_code == 200
    assert "MongoDB" in updated.json()["content"]

    listed = await client.get("/api/owner/agent/knowledge", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == record_id

    retried = await client.post(
        f"/api/owner/agent/knowledge/{record_id}/sync",
        headers=headers,
    )
    assert retried.status_code == 200
    assert retried.json()["vectorSyncError"] == "embedding_not_configured"

    synced_all = await client.post(
        "/api/owner/agent/knowledge/sync",
        headers=headers,
    )
    assert synced_all.status_code == 200
    assert synced_all.json()[0]["id"] == record_id
