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
    assert loaded.json()["thinking"] is False


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


@pytest.mark.asyncio
async def test_agent_stop_and_rewind(client, settings) -> None:
    from app.models import AgentConversation, AgentMessage
    from app.store import current_store

    headers = owner_headers(settings)
    created = await client.post(
        "/api/owner/agent/conversations",
        headers=headers,
        json={"title": "改写"},
    )
    assert created.status_code == 200
    conversation_id = created.json()["id"]
    stopped = await client.post(
        f"/api/owner/agent/conversations/{conversation_id}/stop",
        headers=headers,
    )
    assert stopped.status_code == 200
    assert stopped.json()["thinking"] is False

    from beanie import PydanticObjectId

    row = await current_store().get(
        AgentConversation, PydanticObjectId(conversation_id)
    )
    assert row is not None
    row.messages = [
        AgentMessage(role="user", content="第一句"),
        AgentMessage(role="assistant", content="答一"),
        AgentMessage(role="user", content="第二句"),
        AgentMessage(role="assistant", content="答二"),
    ]
    await current_store().save(row)

    rewound = await client.post(
        f"/api/owner/agent/conversations/{conversation_id}/rewind",
        headers=headers,
        json={"index": 2, "content": "第二句改写"},
    )
    assert rewound.status_code == 200
    assert [item["content"] for item in rewound.json()["messages"]] == [
        "第一句",
        "答一",
    ]

    bad = await client.post(
        f"/api/owner/agent/conversations/{conversation_id}/rewind",
        headers=headers,
        json={"index": 1, "content": "不是用户"},
    )
    assert bad.status_code == 400


def test_live_thinking_expires_after_the_stale_window() -> None:
    from datetime import timedelta

    from app.models import conversation_is_thinking, utc_now

    now = utc_now()
    assert conversation_is_thinking(True, now, now=now) is True
    assert (
        conversation_is_thinking(True, now - timedelta(seconds=800), now=now)
        is False
    )
    assert conversation_is_thinking(False, now, now=now) is False
    assert conversation_is_thinking(True, None, now=now) is True
