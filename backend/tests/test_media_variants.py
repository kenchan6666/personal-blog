"""Responsive WebP variants and intrinsic sizes for content images."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from tests.test_avatar import _owner_token


def _jpeg(width: int, height: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (200, 40, 40)).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_content_image_meta_and_resized_variant(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    uploaded = await client.post(
        "/api/owner/media",
        files={"file": ("photo.jpg", _jpeg(2000, 1000), "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert uploaded.status_code == 200
    url = uploaded.json()["url"]

    meta = await client.get(f"{url}/meta")
    assert meta.json() == {"width": 2000, "height": 1000}

    small = await client.get(url, params={"w": 600})
    assert small.status_code == 200
    assert small.headers["content-type"] == "image/webp"
    with Image.open(io.BytesIO(small.content)) as img:
        assert img.size == (640, 320)

    # Never upscale: a huge request is capped at the natural width.
    big = await client.get(url, params={"w": 5000})
    with Image.open(io.BytesIO(big.content)) as img:
        assert img.width == 1920

    original = await client.get(url)
    assert original.headers["content-type"] == "image/jpeg"
    assert (await client.get("/api/public/media/content/missing.jpg/meta")).status_code == 404
