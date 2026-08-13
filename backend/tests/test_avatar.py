"""
Seam: Portfolio HTTP API.
Ticket: #5 Profile avatar upload.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image


def _png_bytes(color: tuple[int, int, int] = (255, 0, 0)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buf, format="PNG")
    return buf.getvalue()


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
async def test_unauthenticated_cannot_upload_avatar(client):
    response = await client.post(
        "/api/owner/avatar",
        files={"file": ("avatar.png", _png_bytes(), "image/png")},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_owner_upload_appears_on_public_site(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    uploaded = await client.post(
        "/api/owner/avatar",
        files={"file": ("me.png", _png_bytes((10, 20, 30)), "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert uploaded.status_code == 200
    avatar_url = uploaded.json()["avatarUrl"]
    assert avatar_url.startswith("/api/public/media/avatar/")

    public = await client.get("/api/public/site", params={"locale": "zh-Hant"})
    assert public.status_code == 200
    assert public.json()["profile"]["avatarUrl"] == avatar_url

    image = await client.get(avatar_url)
    assert image.status_code == 200
    assert image.headers["content-type"].startswith("image/")
    assert image.content[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.asyncio
async def test_replacing_avatar_updates_public_url(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    first = await client.post(
        "/api/owner/avatar",
        files={"file": ("a.png", _png_bytes((1, 2, 3)), "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    second = await client.post(
        "/api/owner/avatar",
        files={"file": ("b.png", _png_bytes((200, 100, 50)), "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    first_url = first.json()["avatarUrl"]
    second_url = second.json()["avatarUrl"]
    assert first_url != second_url

    public = await client.get("/api/public/site", params={"locale": "en"})
    assert public.json()["profile"]["avatarUrl"] == second_url

    old = await client.get(first_url)
    assert old.status_code == 404
    new = await client.get(second_url)
    assert new.status_code == 200
