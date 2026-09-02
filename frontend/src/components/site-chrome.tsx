"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";

type Props = {
  locale: Locale;
  dict: Dictionary;
};

export function SiteChrome({ locale, dict }: Props) {
  const pathname = usePathname();
  if (pathname.includes("/admin")) return null;

  return (
    <div className="site-chrome">
      <Link href={`/${locale}/search`} className="site-chrome-link">
        {dict.nav.search}
      </Link>
      <Link href={`/${locale}/about`} className="site-chrome-link">
        {dict.nav.about}
      </Link>
    </div>
  );
}
