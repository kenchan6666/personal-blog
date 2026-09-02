"use client";

import { usePathname } from "next/navigation";
import { isLocale } from "@/i18n/config";
import { getDictionary } from "@/i18n/dictionaries";
import { PageLoading } from "@/components/page-loading";

export function LocalePageLoading() {
  const pathname = usePathname();
  const segment = pathname.split("/")[1] ?? "";
  const locale = isLocale(segment) ? segment : "zh-Hant";
  return <PageLoading label={getDictionary(locale).loadingPage} />;
}
