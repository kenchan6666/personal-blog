from __future__ import annotations

from typing import Any

from beanie import Document
from pydantic import BaseModel, Field

from app.avatar import avatar_public_url


def empty_localized() -> dict[str, str]:
    return {"zh-Hant": "", "en": ""}


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

    class Settings:
        name = "site_profile"

    def avatar_url(self) -> str:
        if not self.avatar_filename:
            return ""
        return avatar_public_url(self.avatar_filename)

    def resolve(self, locale: str) -> dict[str, Any]:
        def pick(field: dict[str, str]) -> str:
            return (field or {}).get(locale, "") or ""

        links = sorted(self.links, key=lambda item: item.order)
        return {
            "brand": pick(self.brand),
            "hero": {
                "headline": pick(self.hero_headline),
                "support": pick(self.hero_support),
                "ctaProjects": pick(self.hero_cta_projects),
                "ctaArticles": pick(self.hero_cta_articles),
            },
            "profile": {
                "bio": pick(self.bio),
                "skills": pick(self.skills),
                "experience": pick(self.experience),
                "publicEmail": self.public_email,
                "avatarUrl": self.avatar_url(),
                "links": [
                    {
                        "label": pick(link.label),
                        "url": link.url,
                        "order": link.order,
                    }
                    for link in links
                ],
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
        def pick(field: dict[str, str]) -> str:
            return (field or {}).get(locale, "") or ""

        return {
            "slug": self.slug,
            "title": pick(self.title),
            "summary": pick(self.summary),
            "body": pick(self.body),
            "order": self.order,
            "sourceRepo": self.source_repo.to_public() if self.source_repo else None,
        }


class Article(Document):
    slug: str = ""
    title: dict[str, str] = Field(default_factory=empty_localized)
    summary: dict[str, str] = Field(default_factory=empty_localized)
    body: dict[str, str] = Field(default_factory=empty_localized)
    status: str = "draft"
    order: int = 0
    related_project_slug: str = ""

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
        }

    def resolve(self, locale: str) -> dict[str, Any]:
        def pick(field: dict[str, str]) -> str:
            return (field or {}).get(locale, "") or ""

        return {
            "slug": self.slug,
            "title": pick(self.title),
            "summary": pick(self.summary),
            "body": pick(self.body),
            "order": self.order,
            "relatedProject": None,
        }


class Journal(Document):
    slug: str = ""
    title: dict[str, str] = Field(default_factory=empty_localized)
    summary: dict[str, str] = Field(default_factory=empty_localized)
    body: dict[str, str] = Field(default_factory=empty_localized)
    status: str = "draft"
    order: int = 0

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
        def pick(field: dict[str, str]) -> str:
            return (field or {}).get(locale, "") or ""

        return {
            "slug": self.slug,
            "title": pick(self.title),
            "summary": pick(self.summary),
            "body": pick(self.body),
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
