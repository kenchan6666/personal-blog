import type { Dictionary } from "@/i18n/dictionaries";
import type { PublicSite } from "@/lib/api";

const LEGACY_BRANDS = new Set(["陳逸楠", "陈逸楠", "YN Chan"]);

export function publicBrand(value: string | undefined, fallback = "ken"): string {
  const brand = value?.trim() || fallback;
  if (LEGACY_BRANDS.has(brand)) return "ken";
  return brand || "ken";
}

/** When API is unreachable, keep shell chrome. Once CMS responds, never invent copy. */
export function mergeHeroContent(dict: Dictionary, site: PublicSite | null) {
  if (!site) {
    return {
      brand: publicBrand(dict.brand),
      headline: dict.hero.headline,
      support: dict.hero.support,
      ctaProjects: dict.hero.ctaProjects,
      ctaArticles: dict.hero.ctaArticles,
    };
  }
  return {
    brand: publicBrand(site.brand, dict.brand),
    headline: site.hero.headline,
    support: site.hero.support,
    ctaProjects: site.hero.ctaProjects,
    ctaArticles: site.hero.ctaArticles,
  };
}

export function mergeProfileContent(dict: Dictionary, site: PublicSite | null) {
  return {
    title: dict.profile.title,
    bioLabel: dict.profile.bio,
    skillsLabel: dict.profile.skills,
    experienceLabel: dict.profile.experience,
    emailLabel: dict.profile.email,
    linksLabel: dict.profile.links,
    bio: site?.profile.bio ?? "",
    skills: site?.profile.skills ?? "",
    experience: site?.profile.experience ?? "",
    publicEmail: site?.profile.publicEmail ?? "",
    avatarUrl: site?.profile.avatarUrl ?? "",
    links: site?.profile.links ?? [],
  };
}

export function brandForShell(dict: Dictionary, site: PublicSite | null): string {
  return publicBrand(site?.brand, dict.brand);
}

const STOCK_PAGE_COPY = new Set([
  "技術或項目向的深度寫作。",
  "技术或项目向的深度写作。",
  "Long-form writing on engineering and projects.",
  "學歷、經歷與自我描述。",
  "学历、经历与自我描述。",
  "Education, experience, and a short self-description.",
]);

export function pageCopy(
  site: PublicSite | null,
  key: "articlesLead" | "aboutLead" | "aboutEmpty",
  fallback: string,
): string {
  const value = site?.pages?.[key]?.trim() ?? "";
  if (value && !STOCK_PAGE_COPY.has(value)) return value;
  const next = fallback.trim();
  if (next && !STOCK_PAGE_COPY.has(next)) return next;
  return "";
}
