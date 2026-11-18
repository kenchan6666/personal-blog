"""Public site search across articles, journals, projects and About modules.

Matching is script-insensitive: every locale value of every field is folded
to Simplified + lowercase, so 「太鼓」, 「太鼓」 typed in either script, or the
English category title all find the same posts from any locale.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from app.zh_script import to_script

MAX_QUERY = 100
_MD_NOISE = re.compile(r"!\[[^\]]*\]\([^)]*\)|\[([^\]]*)\]\([^)]*\)|[#>*_`~|]")
_SPACE = re.compile(r"\s+")


def fold(text: str) -> str:
    return to_script(text or "", "zh-Hans").lower()


def plain(text: str) -> str:
    stripped = _MD_NOISE.sub(lambda m: m.group(1) or " ", text or "")
    return _SPACE.sub(" ", stripped).strip()


def localized_values(*fields: dict[str, str] | None) -> Iterable[str]:
    for item in fields:
        for value in (item or {}).values():
            if value:
                yield str(value)


@dataclass
class SearchDoc:
    kind: str
    slug: str
    title: str
    summary: str
    body: str
    category_slug: str = ""
    category_title: str = ""
    tags: list[str] = field(default_factory=list)
    haystack_parts: list[str] = field(default_factory=list)

    def haystack(self) -> str:
        return fold("\n".join(self.haystack_parts))


def excerpt(text: str, query: str, size: int = 120) -> str:
    flat = plain(text)
    if not flat:
        return ""
    folded = fold(flat)
    index = folded.find(fold(query)) if len(folded) == len(flat) else -1
    if index < 0:
        return flat[:size] + ("…" if len(flat) > size else "")
    start = max(0, index - 32)
    chunk = flat[start : start + size]
    return f"{'…' if start > 0 else ''}{chunk}{'…' if start + size < len(flat) else ''}"


def score(doc: SearchDoc, needle: str) -> int:
    """Higher is better: exact tag/category > title > summary > body."""
    best = 0
    tags = [fold(tag) for tag in [doc.category_title, doc.category_slug, *doc.tags] if tag]
    if needle in tags:
        best = max(best, 40)
    if needle in fold(doc.title):
        best = max(best, 30)
    if any(needle in tag for tag in tags):
        best = max(best, 25)
    if needle in fold(doc.summary):
        best = max(best, 20)
    if best == 0 and needle in doc.haystack():
        best = 10
    return best


def run_search(docs: list[SearchDoc], query: str, limit: int = 30) -> list[dict[str, Any]]:
    needle = fold(query.strip()[:MAX_QUERY])
    if not needle:
        return []
    ranked: list[tuple[int, int, SearchDoc]] = []
    for position, doc in enumerate(docs):
        points = score(doc, needle)
        if points:
            ranked.append((points, -position, doc))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    out: list[dict[str, Any]] = []
    for _, _, doc in ranked[:limit]:
        source = doc.body if needle in fold(doc.body) and needle not in fold(doc.summary) else (doc.summary or doc.body)
        out.append(
            {
                "kind": doc.kind,
                "slug": doc.slug,
                "title": doc.title,
                "summary": excerpt(source, query.strip()),
                "categorySlug": doc.category_slug,
                "categoryTitle": doc.category_title,
            }
        )
    return out
