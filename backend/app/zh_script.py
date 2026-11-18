"""Chinese script conversion (OpenCC) shared by rendering, translation and migrations.

zh-Hant uses Hong Kong conventions (`s2hk`); zh-Hans uses `t2s`. Code spans,
fenced code and URLs are shielded so identifiers and links never change.
"""

from __future__ import annotations

import re
from functools import lru_cache

from opencc import OpenCC

_CONFIG = {"zh-Hant": "s2hk", "zh-Hans": "t2s"}
# Detectors: s2t changes text that contains Simplified-only characters;
# t2s changes text that contains Traditional-only characters.
_DETECT = {"zh-Hant": "s2t", "zh-Hans": "t2s"}
_SHIELD = re.compile(
    r"```[\s\S]*?```"
    r"|`[^`\n]+`"
    r"|\]\(\s*<?[^)>\s]+>?\s*\)"
    r"|https?://[^\s)<>\"']+"
)


# OpenCC phrase segmentation occasionally picks a wrong compound
# (e.g. 「和面积」 → 「和麪積」, reading 和面 as "knead dough"). Patch the
# known ones for the Traditional output.
_HANT_FIXES = (
    ("麪積", "面積"),
    ("麪對", "面對"),
    ("麪向", "面向"),
    ("麪前", "面前"),
    ("麪板", "面板"),
)


@lru_cache(maxsize=4)
def _converter(name: str) -> OpenCC:
    return OpenCC(name)


def _apply(text: str, name: str) -> str:
    held: list[str] = []

    def stash(match: re.Match[str]) -> str:
        held.append(match.group(0))
        return f"\u0000{len(held) - 1}\u0000"

    shielded = _SHIELD.sub(stash, text)
    converted = _converter(name).convert(shielded)
    for index, chunk in enumerate(held):
        converted = converted.replace(f"\u0000{index}\u0000", chunk)
    return converted


def is_cjk_locale(locale: str) -> bool:
    return locale in _CONFIG


def needs_script_conversion(text: str, locale: str) -> bool:
    """True when `text` contains characters of the other Chinese script."""
    detector = _DETECT.get(locale)
    if not detector or not text:
        return False
    return _apply(text, detector) != text


@lru_cache(maxsize=4096)
def to_script(text: str, locale: str) -> str:
    """Convert to the locale's script; unchanged for non-CJK locales."""
    name = _CONFIG.get(locale)
    if not name or not text:
        return text
    converted = _apply(text, name)
    if locale == "zh-Hant":
        for wrong, right in _HANT_FIXES:
            converted = converted.replace(wrong, right)
    return converted


@lru_cache(maxsize=4096)
def normalize_script(text: str, locale: str) -> str:
    """Convert only when the text actually mixes in the other script.

    Text already written in the right script is returned untouched so the
    author's own variant choices (e.g. 爲 vs 為) are preserved.
    """
    if needs_script_conversion(text, locale):
        return to_script(text, locale)
    return text
