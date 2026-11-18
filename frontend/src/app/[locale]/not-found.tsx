"use client";

import { usePathname } from "next/navigation";
import { NotFoundView } from "@/components/not-found-view";
import { defaultLocale, isLocale } from "@/i18n/config";

export default function LocaleNotFound() {
  const pathname = usePathname();
  const segment = pathname.split("/")[1];
  const locale = isLocale(segment) ? segment : defaultLocale;
  return <NotFoundView locale={locale} />;
}
