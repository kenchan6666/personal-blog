"""
Seam: Portfolio HTTP API.
Ticket: #7 Article CMS to published public pages with optional related Project.
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


def _article_payload(**overrides):
    body = {
        "slug": "craft-notes",
        "title": {"zh-Hant": "工藝筆記", "en": "Craft notes"},
        "summary": {"zh-Hant": "摘要", "en": "Summary"},
        "body": {
            "zh-Hant": "## 正文\n用作品說話",
            "en": "## Body\nCraft first",
        },
        "status": "published",
        "order": 1,
        "relatedProjectSlug": "",
    }
    body.update(overrides)
    return body


def _project_payload(**overrides):
    body = {
        "slug": "glass-api",
        "title": {"zh-Hant": "玻璃 API", "en": "Glass API"},
        "summary": {"zh-Hant": "", "en": ""},
        "body": {"zh-Hant": "", "en": ""},
        "status": "published",
        "order": 1,
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio
async def test_unauthenticated_cannot_create_article(client):
    response = await client.post("/api/owner/articles", json=_article_payload())
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_owner_can_create_update_and_delete_article(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        "/api/owner/articles",
        json=_article_payload(),
        headers=headers,
    )
    assert created.status_code == 200
    article = created.json()
    assert article["slug"] == "craft-notes"
    assert article["title"]["zh-Hant"] == "工藝筆記"
    assert article["status"] == "published"
    article_id = article["id"]

    updated = await client.put(
        f"/api/owner/articles/{article_id}",
        json=_article_payload(
            title={"zh-Hant": "工藝筆記", "en": "Craft notes v2"},
            status="draft",
        ),
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"]["en"] == "Craft notes v2"
    assert updated.json()["status"] == "draft"

    listed = await client.get("/api/owner/articles", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == article_id for item in listed.json())

    deleted = await client.delete(
        f"/api/owner/articles/{article_id}", headers=headers
    )
    assert deleted.status_code == 200
    listed_after = await client.get("/api/owner/articles", headers=headers)
    assert listed_after.json() == []


@pytest.mark.asyncio
async def test_draft_article_is_hidden_from_visitors(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    await client.post(
        "/api/owner/articles",
        json=_article_payload(status="draft"),
        headers={"Authorization": f"Bearer {token}"},
    )

    public_list = await client.get(
        "/api/public/articles", params={"locale": "zh-Hant"}
    )
    assert public_list.status_code == 200
    assert public_list.json() == []

    detail = await client.get("/api/public/articles/craft-notes")
    assert detail.status_code == 404


@pytest.mark.asyncio
async def test_published_article_shows_related_project(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(
        "/api/owner/projects",
        json=_project_payload(),
        headers=headers,
    )
    await client.post(
        "/api/owner/articles",
        json=_article_payload(
            title={"zh-Hant": "工藝筆記", "en": ""},
            relatedProjectSlug="glass-api",
        ),
        headers=headers,
    )

    zh_list = await client.get(
        "/api/public/articles", params={"locale": "zh-Hant"}
    )
    assert zh_list.status_code == 200
    assert [item["slug"] for item in zh_list.json()] == ["craft-notes"]
    assert zh_list.json()[0]["title"] == "工藝筆記"
    assert zh_list.json()[0]["wordCount"] > 0
    assert zh_list.json()[0]["readingMinutes"] >= 1
    assert zh_list.json()[0]["publishedAt"]

    en_detail = await client.get(
        "/api/public/articles/craft-notes", params={"locale": "en"}
    )
    assert en_detail.status_code == 200
    assert en_detail.json()["title"] == "工藝筆記"
    assert en_detail.json()["body"] == "## Body\nCraft first"
    assert en_detail.json()["relatedProject"]["slug"] == "glass-api"
    assert en_detail.json()["relatedProject"]["title"] == "Glass API"

    zh_detail = await client.get(
        "/api/public/articles/craft-notes", params={"locale": "zh-Hant"}
    )
    assert zh_detail.json()["relatedProject"]["title"] == "玻璃 API"
    assert zh_detail.json()["categorySlug"] == ""
    assert zh_detail.json()["categoryTitle"] == ""


@pytest.mark.asyncio
async def test_related_draft_project_is_hidden_on_public_article(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(
        "/api/owner/projects",
        json=_project_payload(status="draft"),
        headers=headers,
    )
    await client.post(
        "/api/owner/articles",
        json=_article_payload(relatedProjectSlug="glass-api"),
        headers=headers,
    )

    detail = await client.get(
        "/api/public/articles/craft-notes", params={"locale": "zh-Hant"}
    )
    assert detail.status_code == 200
    assert detail.json()["relatedProject"] is None


@pytest.mark.asyncio
async def test_article_categories_are_optional_and_deletable(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    listed = await client.get("/api/owner/article-categories", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == []

    created = await client.post(
        "/api/owner/article-categories",
        json={
            "slug": "taiko",
            "title": {"zh-Hant": "太鼓", "en": "Taiko"},
            "order": 0,
        },
        headers=headers,
    )
    assert created.status_code == 200
    assert created.json()["slug"] == "taiko"
    assert created.json()["protected"] is False
    category_id = created.json()["id"]

    tagged = await client.post(
        "/api/owner/articles",
        json=_article_payload(slug="rip-hero", categorySlug="taiko"),
        headers=headers,
    )
    assert tagged.status_code == 200
    assert tagged.json()["categorySlug"] == "taiko"

    missing = await client.post(
        "/api/owner/articles",
        json=_article_payload(slug="ghost", categorySlug="missing"),
        headers=headers,
    )
    assert missing.status_code == 200
    assert missing.json()["categorySlug"] == ""

    deleted = await client.delete(
        f"/api/owner/article-categories/{category_id}",
        headers=headers,
    )
    assert deleted.status_code == 200

    owner_articles = await client.get("/api/owner/articles", headers=headers)
    by_slug = {item["slug"]: item for item in owner_articles.json()}
    assert by_slug["rip-hero"]["categorySlug"] == ""

    public = await client.get(
        "/api/public/articles/rip-hero", params={"locale": "zh-Hant"}
    )
    assert public.status_code == 200
    assert public.json()["categorySlug"] == ""
    assert public.json()["categoryTitle"] == ""


@pytest.mark.asyncio
async def test_owner_can_add_article_category_and_visitors_can_filter(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        "/api/owner/article-categories",
        json={
            "slug": "notes",
            "title": {"zh-Hant": "筆記", "en": "Notes"},
            "order": 1,
        },
        headers=headers,
    )
    assert created.status_code == 200
    assert created.json()["slug"] == "notes"
    assert created.json()["protected"] is False

    await client.post(
        "/api/owner/articles",
        json=_article_payload(slug="plain-piece"),
        headers=headers,
    )
    await client.post(
        "/api/owner/articles",
        json=_article_payload(slug="note-piece", categorySlug="notes"),
        headers=headers,
    )

    public_cats = await client.get(
        "/api/public/article-categories", params={"locale": "zh-Hant"}
    )
    assert public_cats.status_code == 200
    assert [item["slug"] for item in public_cats.json()] == ["notes"]
    assert public_cats.json()[0]["title"] == "筆記"

    notes = await client.get(
        "/api/public/articles",
        params={"locale": "zh-Hant", "category": "notes"},
    )
    assert [item["slug"] for item in notes.json()] == ["note-piece"]
    assert notes.json()[0]["categorySlug"] == "notes"
    assert notes.json()[0]["categoryTitle"] == "筆記"

    all_public = await client.get(
        "/api/public/articles", params={"locale": "zh-Hant"}
    )
    listed_public = {item["slug"]: item for item in all_public.json()}
    assert set(listed_public) == {"plain-piece", "note-piece"}
    assert listed_public["plain-piece"]["categorySlug"] == ""


@pytest.mark.asyncio
async def test_public_article_resolves_slug_with_leading_slash(
    client, app, mailer, settings
):
    from app.models import Article

    token = await _owner_token(client, mailer, settings)
    created = await client.post(
        "/api/owner/articles",
        json=_article_payload(slug="/rip-hero"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert created.status_code == 200
    assert created.json()["slug"] == "rip-hero"

    clean = await client.get(
        "/api/public/articles/rip-hero", params={"locale": "zh-Hant"}
    )
    assert clean.status_code == 200
    assert clean.json()["slug"] == "rip-hero"

    stored = await app.state.store.find_one(Article, slug="rip-hero")
    assert stored is not None
    stored.slug = "/rip-hero"
    await app.state.store.save(stored)

    listed = await client.get(
        "/api/public/articles", params={"locale": "zh-Hant"}
    )
    assert listed.status_code == 200
    assert [item["slug"] for item in listed.json()] == ["rip-hero"]

    recovered = await client.get(
        "/api/public/articles/rip-hero", params={"locale": "zh-Hant"}
    )
    assert recovered.status_code == 200
    assert recovered.json()["slug"] == "rip-hero"
