import type { Metadata } from "next";
import { locales, type Locale } from "@/i18n/config";
import { fetchPublicSite, type PublicSite } from "@/lib/api";
import { brandForShell } from "@/lib/site-content";
import { markdownImages } from "@/lib/markdown-images";
import { getDictionary } from "@/i18n/dictionaries";

const SITE_NAME = "ken";

const OG_LOCALE: Record<Locale, string> = {
  "zh-Hant": "zh_TW",
  "zh-Hans": "zh_CN",
  en: "en_US",
};

export function siteOrigin(): string {
  return (process.env.NEXT_PUBLIC_SITE_URL ?? "https://kenchan0522.blog").replace(
    /\/$/,
    "",
  );
}

export function pathWithoutLocale(locale: string, href: string): string {
  const prefix = `/${locale}`;
  if (href === prefix || href === `${prefix}/`) return "";
  return href.startsWith(`${prefix}/`) ? href.slice(prefix.length) : href;
}

export function absoluteUrl(path: string): string {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  const origin = siteOrigin();
  return path.startsWith("/") ? `${origin}${path}` : `${origin}/${path}`;
}

export function firstMarkdownImage(source?: string): string {
  if (!source?.trim()) return "";
  return markdownImages(source)[0]?.src ?? "";
}

export function siteShareImage(site: PublicSite | null | undefined): string {
  return site?.hero.visual?.url || site?.profile.avatarUrl || "/mascot.png";
}

export async function pageMetadata({
  locale,
  title,
  description,
  path,
  image,
  markdown,
}: {
  locale: Locale;
  title: string;
  description?: string;
  path: string;
  image?: string;
  markdown?: string;
}): Promise<Metadata> {
  const origin = siteOrigin();
  const suffix = !path || path.startsWith("/") ? path : `/${path}`;
  const url = `${origin}/${locale}${suffix}`;
  const languages = Object.fromEntries(
    locales.map((item) => [item, `${origin}/${item}${suffix}`]),
  );
  const siteName = await siteNameFor(locale);
  const fullTitle = title === siteName ? siteName : `${title} · ${siteName}`;
  const desc = clampDescription(
    description?.trim() || (await siteDescriptionFallback(locale)),
  );
  const ogImage = absoluteUrl(
    firstMarkdownImage(markdown) || image || (await siteImageFallback(locale)),
  );

  return {
    title: fullTitle,
    description: desc,
    alternates: {
      canonical: url,
      languages,
    },
    openGraph: {
      title: fullTitle,
      description: desc,
      url,
      siteName,
      locale: OG_LOCALE[locale],
      type: "website",
      images: [{ url: ogImage, alt: fullTitle }],
    },
    twitter: {
      card: "summary_large_image",
      title: fullTitle,
      description: desc,
      images: [ogImage],
    },
  };
}

async function siteImageFallback(locale: Locale): Promise<string> {
  try {
    return siteShareImage(await fetchPublicSite(locale));
  } catch {
    return "/mascot.png";
  }
}

function clampDescription(text: string): string {
  const flat = text.replace(/[#>*_`]/g, "").replace(/\s+/g, " ").trim();
  return flat.length > 160 ? `${flat.slice(0, 157).trimEnd()}…` : flat;
}

/** Every page gets a description: the owner's own bio, else a generic line. */
async function siteDescriptionFallback(locale: Locale): Promise<string> {
  try {
    const site = await fetchPublicSite(locale);
    const support = site?.hero.support?.trim();
    const bio = site?.profile.bio?.trim();
    if (support) return support;
    if (bio) return bio;
  } catch {
    /* fall through */
  }
  return getDictionary(locale).seoFallback;
}

/** Title suffix: the owner's brand ("Chan Yat Nam"), not a hard-coded nickname. */
async function siteNameFor(locale: Locale): Promise<string> {
  try {
    return brandForShell(getDictionary(locale), await fetchPublicSite(locale)) || SITE_NAME;
  } catch {
    return SITE_NAME;
  }
}
