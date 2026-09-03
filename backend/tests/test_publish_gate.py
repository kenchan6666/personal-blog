from __future__ import annotations

import pytest


def _project_payload(*, status: str = "published", slug: str = "service-draft-only") -> dict:
    return {
        "slug": slug,
        "title": {"zh-Hant": "草稿", "en": "Draft"},
        "summary": {"zh-Hant": "摘要", "en": "Summary"},
        "body": {"zh-Hant": "正文", "en": "Body"},
        "status": status,
        "order": 1,
    }


def _about_payload(*, status: str = "published") -> dict:
    return {
        "slug": "service-about",
        "kind": "summary",
        "title": {"zh-Hant": "簡介", "en": "Summary"},
        "body": {"zh-Hant": "正文", "en": "Body"},
        "status": status,
        "order": 1,
    }


def _article_payload(*, status: str = "draft") -> dict:
    return {
        "slug": "service-article",
        "title": {"zh-Hant": "文章", "en": "Article"},
        "summary": {"zh-Hant": "摘要", "en": "Summary"},
        "body": {"zh-Hant": "正文", "en": "Body"},
        "status": status,
        "order": 1,
    }


@pytest.mark.asyncio
async def test_service_token_cannot_publish_project_via_put(client, settings) -> None:
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


@pytest.mark.asyncio
async def test_service_token_can_publish_via_explicit_route(client, settings) -> None:
    settings.agent_service_token = "service-publish-gate"
    headers = {"Authorization": "Bearer service-publish-gate"}

    created = await client.post(
        "/api/owner/projects",
        json=_project_payload(status="published"),
        headers=headers,
    )
    assert created.json()["status"] == "draft"
    project_id = created.json()["id"]

    published = await client.post(
        f"/api/owner/projects/{project_id}/publish",
        headers=headers,
    )
    assert published.status_code == 200
    assert published.json()["status"] == "published"

    updated = await client.put(
        f"/api/owner/projects/{project_id}",
        json=_project_payload(status="published", slug="service-draft-only"),
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "published"


@pytest.mark.asyncio
async def test_service_token_can_publish_article_and_about(client, settings) -> None:
    settings.agent_service_token = "service-publish-gate"
    headers = {"Authorization": "Bearer service-publish-gate"}

    article = await client.post(
        "/api/owner/articles",
        json=_article_payload(status="published"),
        headers=headers,
    )
    assert article.status_code == 200
    assert article.json()["status"] == "draft"
    published_article = await client.post(
        f"/api/owner/articles/{article.json()['id']}/publish",
        headers=headers,
    )
    assert published_article.status_code == 200
    assert published_article.json()["status"] == "published"
    public_article = await client.get(
        "/api/public/articles/service-article",
        params={"locale": "zh-Hant"},
    )
    assert public_article.status_code == 200
    assert public_article.json()["publishedAt"]

    about = await client.post(
        "/api/owner/about-modules",
        json=_about_payload(status="published"),
        headers=headers,
    )
    assert about.status_code == 200
    assert about.json()["status"] == "draft"
    published_about = await client.post(
        f"/api/owner/about-modules/{about.json()['id']}/publish",
        headers=headers,
    )
    assert published_about.status_code == 200
    assert published_about.json()["status"] == "published"
    public_about = await client.get(
        "/api/public/about",
        params={"locale": "zh-Hant"},
    )
    assert public_about.status_code == 200
    assert any(item["slug"] == "service-about" for item in public_about.json())
