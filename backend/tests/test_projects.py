"""
Seam: Portfolio HTTP API.
Ticket: #6 Project CMS to published public list and detail.
"""

from __future__ import annotations

import pytest


async def _owner_token(client, mailer, settings) -> str:
    await client.post(
        "/api/auth/otp/request",
        json={"email": settings.owner_email},
    )
    code = mailer.sent[-1]["code"]
    verified = await client.post(
        "/api/auth/otp/verify",
        json={"email": settings.owner_email, "code": code},
    )
    return verified.json()["session_token"]


def _project_payload(**overrides):
    body = {
        "slug": "glass-api",
        "title": {"zh-Hant": "玻璃 API", "en": "Glass API"},
        "summary": {"zh-Hant": "摘要", "en": "Summary"},
        "body": {
            "zh-Hant": "## 動機\n用作品說話",
            "en": "## Motive\nCraft first",
        },
        "status": "published",
        "order": 1,
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio
async def test_unauthenticated_cannot_create_project(client):
    response = await client.post("/api/owner/projects", json=_project_payload())
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_owner_can_create_and_update_bilingual_project(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        "/api/owner/projects",
        json=_project_payload(),
        headers=headers,
    )
    assert created.status_code == 200
    project = created.json()
    assert project["slug"] == "glass-api"
    assert project["title"]["zh-Hant"] == "玻璃 API"
    assert project["title"]["en"] == "Glass API"
    assert project["status"] == "published"
    project_id = project["id"]

    updated = await client.put(
        f"/api/owner/projects/{project_id}",
        json=_project_payload(
            title={"zh-Hant": "玻璃 API", "en": "Glass API v2"},
            status="draft",
        ),
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"]["en"] == "Glass API v2"
    assert updated.json()["status"] == "draft"

    listed = await client.get("/api/owner/projects", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == project_id for item in listed.json())


@pytest.mark.asyncio
async def test_draft_project_is_hidden_from_visitors(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    await client.post(
        "/api/owner/projects",
        json=_project_payload(status="draft"),
        headers={"Authorization": f"Bearer {token}"},
    )

    public_list = await client.get(
        "/api/public/projects", params={"locale": "zh-Hant"}
    )
    assert public_list.status_code == 200
    assert public_list.json() == []

    detail = await client.get("/api/public/projects/glass-api")
    assert detail.status_code == 404


@pytest.mark.asyncio
async def test_published_project_appears_in_public_list_and_detail(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(
        "/api/owner/projects",
        json=_project_payload(
            slug="later",
            title={"zh-Hant": "後建", "en": "Later"},
            summary={"zh-Hant": "", "en": ""},
            body={"zh-Hant": "", "en": ""},
            status="published",
            order=2,
        ),
        headers=headers,
    )
    await client.post(
        "/api/owner/projects",
        json=_project_payload(
            slug="glass-api",
            title={"zh-Hant": "玻璃 API", "en": ""},
            status="published",
            order=1,
        ),
        headers=headers,
    )

    zh_list = await client.get(
        "/api/public/projects", params={"locale": "zh-Hant"}
    )
    assert zh_list.status_code == 200
    slugs = [item["slug"] for item in zh_list.json()]
    assert slugs == ["glass-api", "later"]
    assert zh_list.json()[0]["title"] == "玻璃 API"

    en_detail = await client.get(
        "/api/public/projects/glass-api", params={"locale": "en"}
    )
    assert en_detail.status_code == 200
    assert en_detail.json()["title"] == "玻璃 API"
    assert en_detail.json()["body"] == "## Motive\nCraft first"

    zh_detail = await client.get(
        "/api/public/projects/glass-api", params={"locale": "zh-Hant"}
    )
    assert zh_detail.json()["title"] == "玻璃 API"
    assert zh_detail.json()["body"] == "## 動機\n用作品說話"
