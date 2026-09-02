from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.hero_visual import isolate_hero_subject

ALLOWED_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}

EXT_TO_TYPE = {ext: ctype for ctype, ext in ALLOWED_TYPES.items()}


def avatar_public_url(filename: str) -> str:
    return f"/api/public/media/avatar/{filename}"


def hero_visual_public_url(filename: str) -> str:
    return f"/api/public/media/hero/{filename}"


def content_public_url(filename: str) -> str:
    return f"/api/public/media/content/{filename}"


def media_type_for_filename(filename: str) -> str:
    return EXT_TO_TYPE.get(Path(filename).suffix.lower(), "application/octet-stream")


def ensure_avatar_dir(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


async def save_avatar_file(
    upload: UploadFile,
    *,
    directory: Path,
    max_bytes: int,
    previous_filename: str | None,
) -> str:
    content_type = (upload.content_type or "").lower()
    extension = ALLOWED_TYPES.get(content_type)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="unsupported_image_type",
        )

    data = await upload.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="empty_file",
        )
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="file_too_large",
        )

    filename = f"{uuid.uuid4().hex}{extension}"
    target = directory / filename
    target.write_bytes(data)

    if previous_filename:
        old = directory / Path(previous_filename).name
        if old.exists() and old != target:
            old.unlink(missing_ok=True)

    return filename


async def save_hero_visual_file(
    upload: UploadFile,
    *,
    directory: Path,
    max_bytes: int,
    previous_filename: str | None,
) -> str:
    content_type = (upload.content_type or "").lower()
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="unsupported_image_type",
        )

    data = await upload.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="empty_file",
        )
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="file_too_large",
        )

    try:
        processed = isolate_hero_subject(data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_image",
        ) from exc

    filename = f"{uuid.uuid4().hex}.png"
    target = directory / filename
    target.write_bytes(processed)

    if previous_filename:
        old = directory / Path(previous_filename).name
        if old.exists() and old != target:
            old.unlink(missing_ok=True)

    return filename


def resolve_avatar_path(directory: Path, filename: str) -> Path | None:
    safe_name = Path(filename).name
    if safe_name != filename or ".." in filename:
        return None
    path = directory / safe_name
    if not path.is_file():
        return None
    return path
