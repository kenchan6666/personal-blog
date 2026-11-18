"""One-off content migration: fill missing locale fields, fix wrong-script text.

Usage (inside the api container):
    python -m app.scripts.fill_locales            # dry run, prints a diff summary
    python -m app.scripts.fill_locales --apply    # writes changes

Rules for every localized field ({"zh-Hant", "zh-Hans", "en"}):
  * zh-Hant holding Simplified characters is converted with OpenCC s2hk;
    an empty zh-Hant is filled from zh-Hans the same way.
  * zh-Hans holding Traditional characters is converted with OpenCC t2s;
    an empty zh-Hans is filled from zh-Hant.
  * An empty `en` is filled only from EN_TRANSLATIONS (faithful human
    translations of the owner's text); existing English is never touched.
  * OVERRIDES are explicit owner-approved renames (applied to every locale).
Text already in the right script is never rewritten.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from copy import deepcopy
from typing import Any

from app.zh_script import needs_script_conversion, to_script

COLLECTIONS = (
    "site_profile",
    "projects",
    "article_categories",
    "articles",
    "journals",
    "about_modules",
)
LOCALE_KEYS = {"zh-Hant", "zh-Hans", "en"}

# (collection, slug or "*" for the singleton profile, dotted field) -> English
EN_TRANSLATIONS: dict[tuple[str, str, str], str] = {
    ("about_modules", "about-me", "title"): "About me",
    ("about_modules", "about-me", "body"): (
        "I graduated from Newcastle University in the UK in 2025 with a Bachelor's "
        "degree in Computer Science, awarded First-Class Honours. At university I "
        "didn't just focus on studying computer science; I was also an active member "
        "of the table tennis team and once represented the university's second team "
        "at the British Universities championships.\n\n"
        "After graduating, I worked at Virpluz as a Full-stack Developer from "
        "28 December 2025 to 3 September 2026. That experience gave me an in-depth "
        "command of the whole stack, from front end to back end and from databases to "
        "deployment, including FastAPI, React, Next.js, Docker Compose, Nginx and more. "
        "I have also explored the AI/LLM field and am familiar with MCP, LangChain, "
        "RAG and Prompt Engineering."
    ),
    ("about_modules", "taiko-no-tatsujin", "title"): "Taiko no Tatsujin",
    ("about_modules", "taiko-no-tatsujin", "body"): (
        "I first got into Taiko no Tatsujin in July 2024 and played it with friends "
        "until August. Then I went to study in the UK; after coming home in December I "
        "played for another month. After that I didn't pick it up again until I was "
        "working in June 2026. At first I was drawn in by the Compass collaboration and "
        "its unique gameplay; now I'm more into taking on high-difficulty songs."
    ),
    # Keeps the glossary the owner already uses in the English posts.
    ("articles", "rip-hero", "title"): "Ura RIP Ziya!!",
    ("articles", "rip-hero", "summary"): "s brings Ziya +1",
    ("site_profile", "*", "brand"): "Chan Yat Nam",
}

# Owner-approved renames: (collection, slug, field) -> value for every locale.
OVERRIDES: dict[tuple[str, str, str], str] = {
    ("site_profile", "*", "brand"): "Chan Yat Nam",
    ("projects", "quantium-repo", "title"): "Quantium Repo",
}


def _is_localized(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and bool(value)
        and set(value.keys()) <= LOCALE_KEYS
        and all(isinstance(v, str) for v in value.values())
    )


def fix_field(
    field: dict[str, str], en_fill: str | None, override: str | None
) -> tuple[dict[str, str], list[str]]:
    out = {key: field.get(key, "") or "" for key in ("zh-Hant", "zh-Hans", "en")}
    notes: list[str] = []
    if override is not None:
        for key in out:
            if out[key] != override:
                out[key] = override
                notes.append(f"override:{key}")
        return out, notes

    hant, hans = out["zh-Hant"], out["zh-Hans"]
    if hant.strip() and needs_script_conversion(hant, "zh-Hant"):
        out["zh-Hant"] = to_script(hant, "zh-Hant")
        notes.append("script-fix:zh-Hant")
    elif not hant.strip() and hans.strip():
        out["zh-Hant"] = to_script(hans, "zh-Hant")
        notes.append("fill:zh-Hant")

    if hans.strip() and needs_script_conversion(hans, "zh-Hans"):
        out["zh-Hans"] = to_script(hans, "zh-Hans")
        notes.append("script-fix:zh-Hans")
    elif not hans.strip() and out["zh-Hant"].strip():
        out["zh-Hans"] = to_script(out["zh-Hant"], "zh-Hans")
        notes.append("fill:zh-Hans")

    if not out["en"].strip() and en_fill:
        out["en"] = en_fill
        notes.append("fill:en")
    elif not out["en"].strip() and (out["zh-Hant"].strip() or out["zh-Hans"].strip()):
        notes.append("missing:en")
    return out, notes


def plan_document(collection: str, doc: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    slug = "*" if collection == "site_profile" else str(doc.get("slug", ""))
    new = deepcopy(doc)
    changes: list[str] = []

    def walk(node: Any, path: str) -> Any:
        if _is_localized(node):
            key = (collection, slug, path)
            fixed, notes = fix_field(node, EN_TRANSLATIONS.get(key), OVERRIDES.get(key))
            for note in notes:
                changes.append(f"{collection}/{slug}/{path} {note}")
            return fixed
        if isinstance(node, dict):
            return {
                k: (v if k == "_id" else walk(v, f"{path}.{k}" if path else k))
                for k, v in node.items()
            }
        if isinstance(node, list):
            return [walk(v, f"{path}[{i}]") for i, v in enumerate(node)]
        return node

    new = walk(new, "")
    return new, changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    from pymongo import MongoClient

    client = MongoClient(os.environ.get("MONGO_URI", "mongodb://mongo:27017"))
    db = client[os.environ.get("MONGO_DB", "portfolio")]
    totals: Counter[str] = Counter()
    docs_changed = 0
    for collection in COLLECTIONS:
        for doc in db[collection].find():
            new, changes = plan_document(collection, doc)
            for change in changes:
                print(change)
                totals[change.rsplit(" ", 1)[1].split(":")[0]] += 1
            real = [c for c in changes if not c.endswith("missing:en")]
            if real:
                docs_changed += 1
                if args.apply:
                    update = {k: v for k, v in new.items() if k != "_id" and v != doc.get(k)}
                    db[collection].update_one({"_id": doc["_id"]}, {"$set": update})
    print(json.dumps({"applied": args.apply, "documents_changed": docs_changed, **totals}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
