"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { getDictionary } from "@/i18n/dictionaries";
import { defaultLocale, isLocale } from "@/i18n/config";

export default function LocaleNotFound() {
  const pathname = usePathname();
  const segment = pathname.split("/")[1];
  const locale = isLocale(segment) ? segment : defaultLocale;
  const dict = getDictionary(locale);

  return (
    <div className="page-status">
      <p className="page-title display-font">{dict.notFoundPage}</p>
      <Link href={`/${locale}`} className="btn-cta mt-6 inline-flex">
        {dict.backHome}
      </Link>
    </div>
  );
}
