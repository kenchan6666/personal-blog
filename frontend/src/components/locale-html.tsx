"use client";

import { useEffect } from "react";
import type { Locale } from "@/i18n/config";

export function LocaleHtml({ locale }: { locale: Locale }) {
  useEffect(() => {
    const root = document.documentElement;
    root.lang = locale;
    root.classList.remove("locale-zh-Hant", "locale-zh-Hans", "locale-en");
    root.classList.add(`locale-${locale}`);
  }, [locale]);
  return null;
}
