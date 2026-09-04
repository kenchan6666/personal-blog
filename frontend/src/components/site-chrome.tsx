"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import { ThemeToggle } from "./theme-toggle";

type Props = {
  locale: Locale;
  dict: Dictionary;
};

export function SiteChrome({ locale, dict }: Props) {
  const pathname = usePathname();
  const admin = pathname.includes("/admin");

  return (
    <div className="site-chrome">
      {admin ? null : (
        <>
          <Link href={`/${locale}/search`} className="site-chrome-link">
            {dict.nav.search}
          </Link>
          <Link href={`/${locale}/about`} className="site-chrome-link">
            {dict.nav.about}
          </Link>
          <Link href={`/${locale}/resume`} className="site-chrome-link">
            {dict.nav.resume}
          </Link>
        </>
      )}
      <ThemeToggle dict={dict} />
    </div>
  );
}
