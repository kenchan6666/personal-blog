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


def _first_filled(fields: dict[str, str], order: tuple[str, ...] = LOCALES) -> str | None:
    for locale in order:
        if (fields.get(locale) or "").strip():
            return locale
    return None


def _normalize(fields: dict[str, str]) -> dict[str, str]:
    return {locale: str(fields.get(locale) or "") for locale in LOCALES}


async def fill_localized(
    fields: dict[str, str],
    *,
    translator: MachineTranslator,
) -> tuple[dict[str, str], str, list[str]]:
    current = _normalize(fields)
    total = sum(len(value) for value in current.values())
    if total > MAX_CHARS:
        raise ValueError("too_long")
    source = _first_filled(current)
    if source is None:
        raise ValueError("empty_source")

    filled = dict(current)
    warnings: list[str] = []

    async def write(target: str, origin: str) -> None:
        if filled[target].strip():
            return
        try:
            filled[target] = await _render(
                filled[origin],
                source=origin,
                target=target,
                translator=translator,
            )
        except Exception:
            warnings.append(f"{target}_failed")

    if filled["zh-Hant"].strip() and not filled["zh-Hans"].strip():
        await write("zh-Hans", "zh-Hant")
    elif filled["zh-Hans"].strip() and not filled["zh-Hant"].strip():
        await write("zh-Hant", "zh-Hans")
    elif not filled["zh-Hant"].strip() and not filled["zh-Hans"].strip():
        await write("zh-Hant", "en")
        if filled["zh-Hant"].strip():
            await write("zh-Hans", "zh-Hant")

    if not filled["en"].strip():
        origin = _first_filled(filled, ("zh-Hant", "zh-Hans"))
        if origin:
            await write("en", origin)

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
