"""
Seam: Portfolio HTTP API.
Owner can upload a Hero visual and place it (position / scale / blur).
"""

from __future__ import annotations

import io

import pytest
from PIL import Image


def _png_bytes(color: tuple[int, int, int] = (80, 120, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), color).save(buf, format="PNG")
    return buf.getvalue()


def _subject_png() -> bytes:
    image = Image.new("RGB", (40, 40), (250, 250, 252))
    for x in range(12, 28):
        for y in range(10, 30):
            image.putpixel((x, y), (30, 70, 190))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
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
async def test_unauthenticated_cannot_upload_hero_visual(client):
    response = await client.post(
        "/api/owner/hero-visual",
        files={"file": ("hero.png", _png_bytes(), "image/png")},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_owner_upload_and_place_hero_visual(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    uploaded = await client.post(
        "/api/owner/hero-visual",
        files={"file": ("desk.png", _subject_png(), "image/png")},
        headers=headers,
    )
    assert uploaded.status_code == 200
    url = uploaded.json()["heroVisualUrl"]
    assert url.startswith("/api/public/media/hero/")

    placed = await client.put(
        "/api/owner/site",
        json={
            "heroVisualPosX": 28,
            "heroVisualPosY": 72,
            "heroVisualScale": 130,
            "heroVisualBlur": 18,
        },
        headers=headers,
    )
    assert placed.status_code == 200
    assert placed.json()["heroVisualPosX"] == 28
    assert placed.json()["heroVisualBlur"] == 18

    public = await client.get("/api/public/site", params={"locale": "en"})
    visual = public.json()["hero"]["visual"]
    assert visual["url"] == url
    assert visual["posX"] == 28
    assert visual["posY"] == 72
    assert visual["scale"] == 130
    assert visual["blur"] == 18

    image = await client.get(url)
    assert image.status_code == 200
    assert image.content[:8] == b"\x89PNG\r\n\x1a\n"
    cutout = Image.open(io.BytesIO(image.content)).convert("RGBA")
    assert cutout.size[0] < 40 or cutout.size[1] < 40
    assert cutout.getpixel((0, 0))[3] < 30
    cx, cy = cutout.size[0] // 2, cutout.size[1] // 2
    assert cutout.getpixel((cx, cy))[3] > 200


@pytest.mark.asyncio
async def test_owner_can_clear_hero_visual(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    uploaded = await client.post(
        "/api/owner/hero-visual",
        files={"file": ("gone.png", _subject_png(), "image/png")},
        headers=headers,
    )
    url = uploaded.json()["heroVisualUrl"]

    cleared = await client.delete("/api/owner/hero-visual", headers=headers)
    assert cleared.status_code == 200
    assert cleared.json()["heroVisualUrl"] == ""

    public = await client.get("/api/public/site", params={"locale": "zh-Hant"})
    assert public.json()["hero"]["visual"] is None
    assert (await client.get(url)).status_code == 404
