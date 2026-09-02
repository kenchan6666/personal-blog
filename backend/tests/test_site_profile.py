"""
Seam: Portfolio HTTP API.
Ticket: #4 Bilingual Profile and Hero CMS.
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


@pytest.mark.asyncio
async def test_unauthenticated_cannot_update_site(client):
    response = await client.put(
        "/api/owner/site",
        json={"brand": {"zh-Hant": "測試", "en": "Test"}},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_owner_can_save_bilingual_site_fields(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    payload = {
        "brand": {"zh-Hant": "陳逸楠", "en": "YN Chan"},
        "heroHeadline": {
            "zh-Hant": "用作品說話",
            "en": "Craft first",
        },
        "heroSupport": {
            "zh-Hant": "支援句",
            "en": "Support line",
        },
        "heroCtaProjects": {"zh-Hant": "查看項目", "en": "Projects"},
        "heroCtaArticles": {"zh-Hant": "閱讀文章", "en": "Articles"},
        "bio": {"zh-Hant": "簡介", "en": "Bio"},
        "skills": {"zh-Hant": "技能", "en": "Skills"},
        "experience": {"zh-Hant": "經歷", "en": "Experience"},
        "publicEmail": "ynchanhk@gmail.com",
        "links": [
            {
                "label": {"zh-Hant": "GitHub", "en": "GitHub"},
                "url": "https://github.com/kenchan6666",
                "order": 1,
            },
            {
                "label": {"zh-Hant": "履歷", "en": "Resume"},
                "url": "https://example.com/cv.pdf",
                "order": 0,
            },
        ],
    }
    saved = await client.put(
        "/api/owner/site",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert saved.status_code == 200
    body = saved.json()
    assert body["brand"]["zh-Hant"] == "陳逸楠"
    assert body["brand"]["en"] == "YN Chan"

    fetched = await client.get(
        "/api/owner/site",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fetched.status_code == 200
    assert fetched.json()["heroHeadline"]["en"] == "Craft first"


@pytest.mark.asyncio
async def test_public_site_falls_back_to_filled_locale(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    await client.put(
        "/api/owner/site",
        json={
            "brand": {"zh-Hant": "陳逸楠", "en": ""},
            "heroHeadline": {"zh-Hant": "標題", "en": ""},
            "heroSupport": {"zh-Hant": "副文", "en": ""},
            "heroCtaProjects": {"zh-Hant": "項目", "en": ""},
            "heroCtaArticles": {"zh-Hant": "文章", "en": ""},
            "bio": {"zh-Hant": "簡介", "en": ""},
            "skills": {"zh-Hant": "", "en": ""},
            "experience": {"zh-Hant": "", "en": ""},
            "publicEmail": "hello@example.com",
            "links": [
                {
                    "label": {"zh-Hant": "履歷", "en": "Resume"},
                    "url": "https://example.com/cv.pdf",
                    "order": 2,
                },
                {
                    "label": {"zh-Hant": "GitHub", "en": "GitHub"},
                    "url": "https://github.com/kenchan6666",
                    "order": 1,
                },
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    zh = await client.get("/api/public/site", params={"locale": "zh-Hant"})
    assert zh.status_code == 200
    zh_body = zh.json()
    assert zh_body["brand"] == "陳逸楠"
    assert zh_body["hero"]["headline"] == "標題"
    assert zh_body["profile"]["publicEmail"] == "hello@example.com"
    assert [link["label"] for link in zh_body["profile"]["links"]] == [
        "GitHub",
        "履歷",
    ]

    en = await client.get("/api/public/site", params={"locale": "en"})
    assert en.status_code == 200
    en_body = en.json()
    assert en_body["brand"] == "陳逸楠"
    assert en_body["hero"]["headline"] == "標題"
    assert en_body["hero"]["support"] == "副文"
    assert en_body["profile"]["bio"] == "簡介"
    assert en_body["profile"]["links"][0]["label"] == "GitHub"
    assert en_body["hero"]["visual"] is None


@pytest.mark.asyncio
async def test_owner_can_save_public_page_copy(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    saved = await client.put(
        "/api/owner/site",
        json={
            "articlesLead": {
                "zh-Hant": "太鼓與工程筆記。",
                "zh-Hans": "太鼓与工程笔记。",
                "en": "Notes on taiko and engineering.",
            },
            "aboutLead": {
                "zh-Hant": "學歷與經歷。",
                "zh-Hans": "学历与经历。",
                "en": "Education and experience.",
            },
            "aboutEmpty": {
                "zh-Hant": "內容稍後補上。",
                "zh-Hans": "内容稍后补上。",
                "en": "More coming soon.",
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert saved.status_code == 200
    body = saved.json()
    assert body["articlesLead"]["zh-Hant"] == "太鼓與工程筆記。"
    assert body["aboutLead"]["en"] == "Education and experience."
    assert body["aboutEmpty"]["zh-Hans"] == "内容稍后补上。"

    public = await client.get("/api/public/site", params={"locale": "zh-Hant"})
    assert public.status_code == 200
    pages = public.json()["pages"]
    assert pages["articlesLead"] == "太鼓與工程筆記。"
    assert pages["aboutLead"] == "學歷與經歷。"
    assert pages["aboutEmpty"] == "內容稍後補上。"

    english = await client.get("/api/public/site", params={"locale": "en"})
    assert english.json()["pages"]["articlesLead"] == "Notes on taiko and engineering."
