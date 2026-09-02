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
