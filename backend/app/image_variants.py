"""Resized WebP variants and intrinsic sizes for uploaded media.

`?w=` on the public media routes snaps to a fixed width ladder (so the cache
stays bounded), never upscales, and caches the result next to the original
under `.variants/`.
"""

from __future__ import annotations

import os
import tempfile
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageOps

WIDTHS = (256, 384, 640, 828, 1080, 1280, 1600, 1920)
VARIANT_DIR = ".variants"


def snap_width(requested: int) -> int:
    for width in WIDTHS:
        if requested <= width:
            return width
    return WIDTHS[-1]


@lru_cache(maxsize=512)
def _size_cached(path: str, mtime: float) -> tuple[int, int]:
    with Image.open(path) as img:
        width, height = img.size
        orientation = img.getexif().get(0x0112, 1)
    if orientation in (5, 6, 7, 8):
        width, height = height, width
    return width, height


def intrinsic_size(path: Path) -> tuple[int, int]:
    return _size_cached(str(path), path.stat().st_mtime)


def variant_path(path: Path, requested: int) -> Path:
    """Return a cached WebP no wider than `requested` (snapped); original if smaller."""
    width = snap_width(max(1, requested))
    natural_w, _ = intrinsic_size(path)
    if natural_w <= width and path.suffix.lower() == ".webp":
        return path
    target_w = min(width, natural_w)
    cache_dir = path.parent / VARIANT_DIR
    out = cache_dir / f"{path.stem}-{target_w}.webp"
    if out.is_file() and out.stat().st_mtime >= path.stat().st_mtime:
        return out
    cache_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
        if img.width > target_w:
            ratio = target_w / img.width
            img = img.resize((target_w, max(1, round(img.height * ratio))), Image.LANCZOS)
        fd, tmp = tempfile.mkstemp(dir=cache_dir, suffix=".webp")
        os.close(fd)
        try:
            img.save(tmp, "WEBP", quality=78, method=4)
            os.replace(tmp, out)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    return out
