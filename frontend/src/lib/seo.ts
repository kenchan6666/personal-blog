import type { Metadata } from "next";
import { locales, type Locale } from "@/i18n/config";

const SITE_NAME = "ken";

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

export function pageMetadata({
  locale,
  title,
  description,
  path,
}: {
  locale: Locale;
  title: string;
  description?: string;
  path: string;
}): Metadata {
  const origin = siteOrigin();
  const suffix = !path || path.startsWith("/") ? path : `/${path}`;
  const url = `${origin}/${locale}${suffix}`;
  const languages = Object.fromEntries(
    locales.map((item) => [item, `${origin}/${item}${suffix}`]),
  );
  const fullTitle = title === SITE_NAME ? SITE_NAME : `${title} · ${SITE_NAME}`;
  const desc = description?.trim() || undefined;

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
      siteName: SITE_NAME,
      locale,
      type: "website",
    },
    twitter: {
      card: "summary",
      title: fullTitle,
      description: desc,
    },
  };
}
