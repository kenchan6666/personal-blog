from __future__ import annotations

import pytest

def _project_payload(*, status: str = "published") -> dict:
    return {
        "slug": "service-draft-only",
        "title": {"zh-Hant": "草稿", "en": "Draft"},
        "summary": {"zh-Hant": "摘要", "en": "Summary"},
        "body": {"zh-Hant": "正文", "en": "Body"},
        "status": status,
        "order": 1,
    }


@pytest.mark.asyncio
async def test_service_token_cannot_publish_project(client, settings) -> None:
    settings.agent_service_token = "service-publish-gate"
    headers = {"Authorization": "Bearer service-publish-gate"}

    created = await client.post(
        "/api/owner/projects",
        json=_project_payload(status="published"),
        headers=headers,
    )

    assert created.status_code == 200
    assert created.json()["status"] == "draft"

    updated = await client.put(
        f"/api/owner/projects/{created.json()['id']}",
        json=_project_payload(status="published"),
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "draft"
