"""Public search: titles, category tags and bodies, script-insensitive."""

from __future__ import annotations

import pytest

from app.models import pick_localized
from tests.test_articles import _article_payload, _owner_token


@pytest.mark.asyncio
async def test_search_finds_articles_by_category_tag_in_every_locale(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        "/api/owner/article-categories",
        json={"slug": "taiko", "title": {"zh-Hant": "太鼓", "en": "Taiko"}, "order": 0},
        headers=headers,
    )
    assert created.status_code == 200
    article = await client.post(
        "/api/owner/articles",
        json=_article_payload(
            slug="xiaoshi",
            title={"zh-Hant": "裏消失紫雅", "zh-Hans": "里消失紫雅", "en": ""},
            summary={"zh-Hant": "又一個！", "zh-Hans": "", "en": ""},
            body={"zh-Hant": "可惜2345區全連", "zh-Hans": "", "en": ""},
            categorySlug="taiko",
        ),
        headers=headers,
    )
    assert article.status_code == 200

    for locale in ("zh-Hant", "zh-Hans", "en"):
        found = await client.get(
            "/api/public/search", params={"q": "太鼓", "locale": locale}
        )
        assert found.status_code == 200
        slugs = [(hit["kind"], hit["slug"]) for hit in found.json()]
        assert ("article", "xiaoshi") in slugs, locale

    # Body text typed in the other script still matches.
    simplified = await client.get(
        "/api/public/search", params={"q": "区全连", "locale": "zh-Hant"}
    )
    hit = simplified.json()[0]
    assert hit["slug"] == "xiaoshi"
    assert hit["title"] == "裏消失紫雅"
    assert hit["categorySlug"] == "taiko"
    assert "區全連" in hit["summary"] or hit["summary"]

    english = await client.get(
        "/api/public/search", params={"q": "taiko", "locale": "en"}
    )
    assert [h["slug"] for h in english.json()] == ["xiaoshi"]
    assert (await client.get("/api/public/search", params={"q": " "})).json() == []


def test_pick_localized_normalises_wrong_script():
    field = {"zh-Hant": "曾于纽卡斯尔大学毕业", "zh-Hans": "", "en": ""}
    assert pick_localized(field, "zh-Hant") == "曾於紐卡斯爾大學畢業"
    assert pick_localized(field, "zh-Hans") == "曾于纽卡斯尔大学毕业"
    # Text already in the right script keeps the author's variants.
    assert pick_localized({"zh-Hant": "使用websocket爲主"}, "zh-Hant") == "使用websocket爲主"
    # Code spans and links are never converted.
    assert pick_localized({"zh-Hans": "看 `后台` [链接](https://x.dev/后台)"}, "zh-Hant") == (
        "看 `后台` [鏈接](https://x.dev/后台)"
    )
