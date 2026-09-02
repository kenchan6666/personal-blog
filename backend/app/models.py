from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from beanie import Document
from pydantic import BaseModel, Field
from zhconv import convert as zhconv_convert

from app.avatar import avatar_public_url, hero_visual_public_url

LOCALES = ("zh-Hant", "zh-Hans", "en")
DEFAULT_ARTICLE_CATEGORY_SLUG = "taiko"
DEFAULT_ARTICLE_CATEGORY_TITLE = {
    "zh-Hant": "太鼓",
    "zh-Hans": "太鼓",
    "en": "Taiko",
}
ABOUT_KINDS = ("summary", "education", "achievement", "experience", "custom")
LOCALE_FALLBACK = {
    "zh-Hans": ("zh-Hans", "zh-Hant", "en"),
    "zh-Hant": ("zh-Hant", "zh-Hans", "en"),
    "en": ("en", "zh-Hant", "zh-Hans"),
}
_SCRIPT_TARGET = {
    "zh-Hans": "zh-cn",
    "zh-Hant": "zh-hk",
}


def empty_localized() -> dict[str, str]:
    return {"zh-Hant": "", "zh-Hans": "", "en": ""}


def convert_chinese_script(text: str, locale: str) -> str:
    target = _SCRIPT_TARGET.get(locale)
    if not target:
        return text
    return zhconv_convert(text, target)


def pick_localized(field: dict[str, str] | None, locale: str) -> str:
    data = field or {}
    order = LOCALE_FALLBACK.get(locale, LOCALES)
    for key in order:
        alt = data.get(key) or ""
        if not str(alt).strip():
            continue
        if locale in _SCRIPT_TARGET and key in _SCRIPT_TARGET and key != locale:
            return convert_chinese_script(str(alt), locale)
        return str(alt)
    for value in data.values():
        if str(value).strip():
            return str(value)
    return ""


def count_chars(text: str) -> int:
    return len(re.sub(r"\s+", "", text or ""))


def reading_minutes(chars: int) -> int:
    if chars <= 0:
        return 0
    return max(1, round(chars / 400))


def dated(published_at: datetime | None, doc_id: Any) -> datetime:
    if published_at is not None:
        return published_at
    if doc_id is not None and hasattr(doc_id, "generation_time"):
        return doc_id.generation_time
    return datetime.now(timezone.utc)


class LinkItem(BaseModel):
    label: dict[str, str] = Field(default_factory=empty_localized)
    url: str = ""
    order: int = 0


class SiteProfile(Document):
    brand: dict[str, str] = Field(default_factory=empty_localized)
    hero_headline: dict[str, str] = Field(default_factory=empty_localized)
    hero_support: dict[str, str] = Field(default_factory=empty_localized)
    hero_cta_projects: dict[str, str] = Field(default_factory=empty_localized)
    hero_cta_articles: dict[str, str] = Field(default_factory=empty_localized)
    bio: dict[str, str] = Field(default_factory=empty_localized)
    skills: dict[str, str] = Field(default_factory=empty_localized)
    experience: dict[str, str] = Field(default_factory=empty_localized)
    public_email: str = ""
    links: list[LinkItem] = Field(default_factory=list)
    avatar_filename: str = ""
    hero_visual_filename: str = ""
    hero_visual_pos_x: float = 50
    hero_visual_pos_y: float = 50
    hero_visual_scale: float = 100
    hero_visual_blur: float = 0
    articles_lead: dict[str, str] = Field(default_factory=empty_localized)
    about_lead: dict[str, str] = Field(default_factory=empty_localized)
    about_empty: dict[str, str] = Field(default_factory=empty_localized)

    class Settings:
        name = "site_profile"

    def avatar_url(self) -> str:
        if not self.avatar_filename:
            return ""
        return avatar_public_url(self.avatar_filename)

    def hero_visual_url(self) -> str:
        if not self.hero_visual_filename:
            return ""
        return hero_visual_public_url(self.hero_visual_filename)

    def hero_visual_public(self) -> dict[str, Any] | None:
        url = self.hero_visual_url()
        if not url:
            return None
        return {
            "url": url,
            "posX": self.hero_visual_pos_x,
            "posY": self.hero_visual_pos_y,
            "scale": self.hero_visual_scale,
            "blur": self.hero_visual_blur,
        }

    def resolve(self, locale: str) -> dict[str, Any]:
        links = sorted(self.links, key=lambda item: item.order)
        return {
            "brand": pick_localized(self.brand, locale),
            "hero": {
                "headline": pick_localized(self.hero_headline, locale),
                "support": pick_localized(self.hero_support, locale),
                "ctaProjects": pick_localized(self.hero_cta_projects, locale),
                "ctaArticles": pick_localized(self.hero_cta_articles, locale),
                "visual": self.hero_visual_public(),
            },
            "profile": {
                "bio": pick_localized(self.bio, locale),
                "skills": pick_localized(self.skills, locale),
                "experience": pick_localized(self.experience, locale),
                "publicEmail": self.public_email,
                "avatarUrl": self.avatar_url(),
                "links": [
                    {
                        "label": pick_localized(link.label, locale),
                        "url": link.url,
                        "order": link.order,
                    }
                    for link in links
                ],
            },
            "pages": {
                "articlesLead": pick_localized(self.articles_lead, locale),
                "aboutLead": pick_localized(self.about_lead, locale),
                "aboutEmpty": pick_localized(self.about_empty, locale),
            },
        }

    def to_owner_dict(self) -> dict[str, Any]:
        return {
            "brand": self.brand,
            "heroHeadline": self.hero_headline,
            "heroSupport": self.hero_support,
            "heroCtaProjects": self.hero_cta_projects,
            "heroCtaArticles": self.hero_cta_articles,
            "bio": self.bio,
            "skills": self.skills,
            "experience": self.experience,
            "publicEmail": self.public_email,
            "avatarUrl": self.avatar_url(),
            "heroVisualUrl": self.hero_visual_url(),
            "heroVisualPosX": self.hero_visual_pos_x,
            "heroVisualPosY": self.hero_visual_pos_y,
            "heroVisualScale": self.hero_visual_scale,
            "heroVisualBlur": self.hero_visual_blur,
            "articlesLead": self.articles_lead,
            "aboutLead": self.about_lead,
            "aboutEmpty": self.about_empty,
            "links": [link.model_dump() for link in self.links],
        }


STATUSES = ("draft", "published")


class SourceRepo(BaseModel):
    full_name: str = ""
    owner: str = ""
    name: str = ""
    private: bool = False
    html_url: str = ""
    default_branch: str = ""

    @classmethod
    def from_github(cls, item: dict[str, object]) -> SourceRepo:
        return cls(
            full_name=str(item["fullName"]),
            owner=str(item["owner"]),
            name=str(item["name"]),
            private=bool(item["private"]),
            html_url=str(item["htmlUrl"]),
            default_branch=str(item["defaultBranch"]),
        )

    def to_public(self) -> dict[str, Any] | None:
        if not self.full_name:
            return None
        return {
            "fullName": self.full_name,
            "owner": self.owner,
            "name": self.name,
            "private": self.private,
            "htmlUrl": self.html_url,
            "defaultBranch": self.default_branch,
        }


class Project(Document):
    slug: str = ""
    title: dict[str, str] = Field(default_factory=empty_localized)
    summary: dict[str, str] = Field(default_factory=empty_localized)
    body: dict[str, str] = Field(default_factory=empty_localized)
    status: str = "draft"
    order: int = 0
    source_repo: SourceRepo | None = None

    class Settings:
        name = "projects"

    def to_owner_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "slug": self.slug,
            "title": self.title,
            "summary": self.summary,
            "body": self.body,
            "status": self.status,
            "order": self.order,
            "sourceRepo": self.source_repo.to_public() if self.source_repo else None,
        }

    def resolve(self, locale: str) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "title": pick_localized(self.title, locale),
            "summary": pick_localized(self.summary, locale),
            "body": pick_localized(self.body, locale),
            "order": self.order,
            "sourceRepo": self.source_repo.to_public() if self.source_repo else None,
        }


class ArticleCategory(Document):
    slug: str = ""
    title: dict[str, str] = Field(default_factory=empty_localized)
    order: int = 0
    protected: bool = False

    class Settings:
        name = "article_categories"

    def to_owner_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "slug": self.slug,
            "title": self.title,
            "order": self.order,
            "protected": self.protected,
        }

    def resolve(self, locale: str) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "title": pick_localized(self.title, locale),
            "order": self.order,
        }


class Article(Document):
    slug: str = ""
    title: dict[str, str] = Field(default_factory=empty_localized)
    summary: dict[str, str] = Field(default_factory=empty_localized)
    body: dict[str, str] = Field(default_factory=empty_localized)
    status: str = "draft"
    order: int = 0
    related_project_slug: str = ""
    category_slug: str = DEFAULT_ARTICLE_CATEGORY_SLUG
    published_at: datetime | None = None

    class Settings:
        name = "articles"

    def to_owner_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "slug": self.slug,
            "title": self.title,
            "summary": self.summary,
            "body": self.body,
            "status": self.status,
            "order": self.order,
            "relatedProjectSlug": self.related_project_slug,
            "categorySlug": self.category_slug or DEFAULT_ARTICLE_CATEGORY_SLUG,
        }

    def resolve(self, locale: str) -> dict[str, Any]:
        body_text = pick_localized(self.body, locale)
        chars = count_chars(body_text)
        when = dated(self.published_at, self.id)
        return {
            "slug": self.slug,
            "title": pick_localized(self.title, locale),
            "summary": pick_localized(self.summary, locale),
            "body": body_text,
            "order": self.order,
            "relatedProject": None,
            "categorySlug": self.category_slug or DEFAULT_ARTICLE_CATEGORY_SLUG,
            "categoryTitle": "",
            "publishedAt": when.isoformat(),
            "wordCount": chars,
            "readingMinutes": reading_minutes(chars),
        }


class Journal(Document):
    slug: str = ""
    title: dict[str, str] = Field(default_factory=empty_localized)
    summary: dict[str, str] = Field(default_factory=empty_localized)
    body: dict[str, str] = Field(default_factory=empty_localized)
    status: str = "draft"
    order: int = 0
    published_at: datetime | None = None

    class Settings:
        name = "journals"

    def to_owner_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "slug": self.slug,
            "title": self.title,
            "summary": self.summary,
            "body": self.body,
            "status": self.status,
            "order": self.order,
        }

    def resolve(self, locale: str) -> dict[str, Any]:
        body_text = pick_localized(self.body, locale)
        chars = count_chars(body_text)
        when = dated(self.published_at, self.id)
        return {
            "slug": self.slug,
            "title": pick_localized(self.title, locale),
            "summary": pick_localized(self.summary, locale),
            "body": body_text,
            "order": self.order,
            "publishedAt": when.isoformat(),
            "wordCount": chars,
            "readingMinutes": reading_minutes(chars),
        }


class AboutModule(Document):
    slug: str = ""
    kind: str = "custom"
    title: dict[str, str] = Field(default_factory=empty_localized)
    body: dict[str, str] = Field(default_factory=empty_localized)
    status: str = "draft"
    order: int = 0

    class Settings:
        name = "about_modules"

    def to_owner_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "slug": self.slug,
            "kind": self.kind,
            "title": self.title,
            "body": self.body,
            "status": self.status,
            "order": self.order,
        }

    def resolve(self, locale: str) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "kind": self.kind,
            "title": pick_localized(self.title, locale),
            "body": pick_localized(self.body, locale),
            "order": self.order,
        }


class Comment(Document):
    target_type: str = "article"
    target_slug: str = ""
    display_name: str = ""
    email: str = ""
    body: str = ""
    status: str = "pending"
    owner_reply: str = ""

    class Settings:
        name = "comments"

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "displayName": self.display_name,
            "body": self.body,
            "status": self.status,
            "ownerReply": self.owner_reply,
        }

    def to_owner_dict(self) -> dict[str, Any]:
        return {
            **self.to_public_dict(),
            "email": self.email,
            "targetType": self.target_type,
            "targetSlug": self.target_slug,
        }
