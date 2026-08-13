from __future__ import annotations

from typing import Any

from beanie import Document
from pydantic import BaseModel, Field


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

    class Settings:
        name = "site_profile"

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
            "links": [link.model_dump() for link in self.links],
        }
