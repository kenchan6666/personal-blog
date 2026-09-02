"""
Seam: Portfolio HTTP API.
About modules on the public personal-detail page.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image


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


def _png_bytes(color: tuple[int, int, int] = (255, 0, 0)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buf, format="PNG")
    return buf.getvalue()


def _about_payload(**overrides):
    body = {
        "slug": "education",
        "kind": "education",
        "title": {
            "zh-Hant": "學歷",
            "zh-Hans": "学历",
            "en": "Education",
        },
        "body": {
            "zh-Hant": "香港大學",
            "zh-Hans": "香港大学",
            "en": "The University of Hong Kong",
        },
        "status": "published",
        "order": 1,
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio
async def test_draft_about_module_is_hidden_from_visitors(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    await client.post(
        "/api/owner/about-modules",
        json=_about_payload(status="draft"),
        headers={"Authorization": f"Bearer {token}"},
    )
    public = await client.get("/api/public/about", params={"locale": "zh-Hans"})
    assert public.status_code == 200
    assert public.json() == []


@pytest.mark.asyncio
async def test_published_about_module_uses_simplified_or_falls_back(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        "/api/owner/about-modules",
        json=_about_payload(),
        headers=headers,
    )
    assert created.status_code == 200
    assert created.json()["kind"] == "education"

    hans = await client.get("/api/public/about", params={"locale": "zh-Hans"})
    assert hans.status_code == 200
    assert hans.json()[0]["title"] == "学历"
    assert hans.json()[0]["body"] == "香港大学"

    await client.put(
        f"/api/owner/about-modules/{created.json()['id']}",
        json=_about_payload(title={"zh-Hant": "學歷", "zh-Hans": "", "en": ""}),
        headers=headers,
    )
    hans_fallback = await client.get(
        "/api/public/about", params={"locale": "zh-Hans"}
    )
    assert hans_fallback.json()[0]["title"] == "学历"

    await client.put(
        f"/api/owner/about-modules/{created.json()['id']}",
        json=_about_payload(
            title={"zh-Hant": "", "zh-Hans": "学历", "en": ""},
            body={"zh-Hant": "", "zh-Hans": "香港大学", "en": ""},
        ),
        headers=headers,
    )
    hant_fallback = await client.get(
        "/api/public/about", params={"locale": "zh-Hant"}
    )
    assert hant_fallback.json()[0]["title"] == "學歷"


@pytest.mark.asyncio
async def test_unauthenticated_cannot_upload_content_image(client):
    response = await client.post(
        "/api/owner/media",
        files={"file": ("note.png", _png_bytes(), "image/png")},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_owner_can_upload_content_image_for_markdown(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    uploaded = await client.post(
        "/api/owner/media",
        files={"file": ("campus.png", _png_bytes((40, 80, 120)), "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert uploaded.status_code == 200
    url = uploaded.json()["url"]
    assert url.startswith("/api/public/media/content/")

    image = await client.get(url)
    assert image.status_code == 200
    assert image.headers["content-type"].startswith("image/")
    assert image.content[:8] == b"\x89PNG\r\n\x1a\n"
