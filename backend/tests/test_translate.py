"""
Seam: Portfolio HTTP API.
Owner CMS can fill empty locales from one original; public pages still store/show that text.
"""

from __future__ import annotations

import pytest

from app.models import convert_chinese_script


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
async def test_guest_cannot_translate(client):
    response = await client.post(
        "/api/owner/translate",
        json={"zh-Hant": "玻璃", "zh-Hans": "", "en": ""},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_empty_source_is_rejected(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    response = await client.post(
        "/api/owner/translate",
        json={"zh-Hant": "  ", "zh-Hans": "", "en": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "empty_source"


@pytest.mark.asyncio
async def test_fills_empty_locales_from_traditional_chinese(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    source = "玻璃工藝"
    response = await client.post(
        "/api/owner/translate",
        json={"zh-Hant": source, "zh-Hans": "", "en": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "zh-Hant"
    assert payload["zh-Hant"] == source
    assert payload["zh-Hans"] == convert_chinese_script(source, "zh-Hans")
    assert payload["en"] == f"en:{source}"
    assert payload["warnings"] == []


@pytest.mark.asyncio
async def test_does_not_overwrite_filled_english(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    response = await client.post(
        "/api/owner/translate",
        json={
            "zh-Hant": "玻璃工藝",
            "zh-Hans": "",
            "en": "Glass craft",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["en"] == "Glass craft"
    assert payload["zh-Hans"] == convert_chinese_script("玻璃工藝", "zh-Hans")


@pytest.mark.asyncio
async def test_english_only_fills_both_chinese(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    response = await client.post(
        "/api/owner/translate",
        json={"zh-Hant": "", "zh-Hans": "", "en": "Glass craft"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "en"
    assert payload["en"] == "Glass craft"
    assert payload["zh-Hant"] == "zh-Hant:Glass craft"
    assert payload["zh-Hans"] == convert_chinese_script(
        "zh-Hant:Glass craft", "zh-Hans"
    )


@pytest.mark.asyncio
async def test_keeps_markdown_images_and_code(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    source = (
        "封面\n\n"
        "![alt](</api/public/media/content/abc.jpg>)\n\n"
        "```python\nprint('繁體')\n```\n"
    )
    response = await client.post(
        "/api/owner/translate",
        json={"zh-Hant": source, "zh-Hans": "", "en": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "/api/public/media/content/abc.jpg" in payload["zh-Hans"]
    assert "/api/public/media/content/abc.jpg" in payload["en"]
    assert "print('繁體')" in payload["zh-Hans"]
    assert "print('繁體')" in payload["en"]
