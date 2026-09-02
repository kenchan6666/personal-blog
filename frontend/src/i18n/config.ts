export const locales = ["zh-Hant", "zh-Hans", "en"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "zh-Hant";

export const localeLabels: Record<Locale, string> = {
  "zh-Hant": "繁中",
  "zh-Hans": "简中",
  en: "EN",
};

export const localePrefix = /^\/(zh-Hant|zh-Hans|en)(?=\/|$)/;

export function isLocale(value: string): value is Locale {
  return (locales as readonly string[]).includes(value);
}

export function stripLocalePrefix(pathname: string): string {
  return pathname.replace(localePrefix, "") || "";
}

export function pathnameFromHref(href: string): string {
  const raw = href.split("?")[0]?.split("#")[0] ?? href;
  if (/^https?:\/\//i.test(raw)) {
    try {
      return new URL(raw).pathname;
    } catch {
      return raw;
    }
  }
  return raw.startsWith("/") ? raw : `/${raw}`;
}

/** Same page, only `/zh-Hant` ↔ `/zh-Hans` ↔ `/en`. */
export function isLocaleOnlyPathChange(fromPath: string, toPath: string): boolean {
  if (!fromPath || !toPath || fromPath === toPath) return false;
  return stripLocalePrefix(fromPath) === stripLocalePrefix(toPath);
}
