from __future__ import annotations

import re
from typing import Protocol

import httpx

from app.models import LOCALES, convert_chinese_script

MAX_CHARS = 20_000
_CJK = {"zh-Hant", "zh-Hans"}
_GTX_LANG = {"zh-Hant": "zh-TW", "zh-Hans": "zh-CN", "en": "en"}
_SHIELD = re.compile(
    r"```[\s\S]*?```"
    r"|`[^`]+`"
    r"|!\[[^\]]*\]\(\s*<?[^)>\s]+>?\s*\)"
    r"|https?://[^\s)<]+"
    r"|/api/public/media/[^\s)<]+"
)
_CHUNK = 1500


class MachineTranslator(Protocol):
    async def translate(self, text: str, *, source: str, target: str) -> str: ...


class GoogleGtxTranslator:
    async def translate(self, text: str, *, source: str, target: str) -> str:
        if not text.strip():
            return text
        sl = _GTX_LANG[source]
        tl = _GTX_LANG[target]
        parts: list[str] = []
        async with httpx.AsyncClient(timeout=20.0) as client:
            for chunk in _chunks(text):
                response = await client.get(
                    "https://translate.googleapis.com/translate_a/single",
                    params={
                        "client": "gtx",
                        "sl": sl,
                        "tl": tl,
                        "dt": "t",
                        "q": chunk,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                parts.append(
                    "".join(
                        piece[0]
                        for piece in (payload[0] or [])
                        if piece and piece[0]
                    )
                )
        return "".join(parts)


class ScriptedTranslator:
    """Test double: prefix with `{target}:` so HTTP tests never hit the network."""

    async def translate(self, text: str, *, source: str, target: str) -> str:
        return f"{target}:{text}"


def _chunks(text: str) -> list[str]:
    if len(text) <= _CHUNK:
        return [text]
    pieces: list[str] = []
    rest = text
    while rest:
        if len(rest) <= _CHUNK:
            pieces.append(rest)
            break
        cut = rest.rfind("\n", 0, _CHUNK)
        if cut < _CHUNK // 2:
            cut = _CHUNK
        pieces.append(rest[:cut])
        rest = rest[cut:]
    return pieces


def _shield(text: str) -> tuple[str, list[str]]:
    held: list[str] = []

    def stash(match: re.Match[str]) -> str:
        held.append(match.group(0))
        return f"@@{len(held) - 1}@@"

    return _SHIELD.sub(stash, text), held


def _restore(text: str, held: list[str]) -> str:
    for index, chunk in enumerate(held):
        text = text.replace(f"@@{index}@@", chunk)
    return text


def _plain_len(text: str) -> int:
    shielded, _ = _shield(text)
    return len(re.sub(r"\s+", "", shielded))


def _pick_source(fields: dict[str, str]) -> str | None:
    best: str | None = None
    best_len = -1
    for locale in LOCALES:
        length = _plain_len(fields.get(locale) or "")
        if length > best_len:
            best_len = length
            best = locale
    return best if best_len > 0 else None


def _normalize(fields: dict[str, str]) -> dict[str, str]:
    return {locale: str(fields.get(locale) or "") for locale in LOCALES}


async def fill_localized(
    fields: dict[str, str],
    *,
    translator: MachineTranslator,
    overwrite: bool = True,
) -> tuple[dict[str, str], str, list[str]]:
    current = _normalize(fields)
    total = sum(len(value) for value in current.values())
    if total > MAX_CHARS:
        raise ValueError("too_long")
    source = _pick_source(current)
    if source is None:
        raise ValueError("empty_source")

    filled = dict(current)
    warnings: list[str] = []

    async def write(target: str, origin: str) -> None:
        if target == origin:
            return
        existing = filled[target]
        origin_text = filled[origin]
        if not origin_text.strip():
            return
        if (
            not overwrite
            and _plain_len(existing)
            and existing.strip() != origin_text.strip()
        ):
            return
        try:
            filled[target] = await _render(
                origin_text,
                source=origin,
                target=target,
                translator=translator,
            )
        except Exception as exc:
            print(
                f"[translate] {origin}->{target} failed: {type(exc).__name__}: {exc}",
                flush=True,
            )
            warnings.append(f"{target}_failed")

    if source == "en":
        await write("zh-Hant", "en")
        await write("zh-Hans", "zh-Hant" if filled["zh-Hant"].strip() else "en")
    elif source == "zh-Hant":
        await write("zh-Hans", "zh-Hant")
        await write("en", "zh-Hant")
    else:
        await write("zh-Hant", "zh-Hans")
        await write("en", "zh-Hans")

    return filled, source, warnings


async def _render(
    text: str,
    *,
    source: str,
    target: str,
    translator: MachineTranslator,
) -> str:
    shielded, held = _shield(text)
    if source in _CJK and target in _CJK:
        converted = convert_chinese_script(shielded, target)
    else:
        converted = await translator.translate(
            shielded, source=source, target=target
        )
    return _restore(converted, held)
