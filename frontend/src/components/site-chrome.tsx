"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import { localeLabels, locales, stripLocalePrefix } from "@/i18n/config";

type Props = {
  locale: Locale;
  dict: Dictionary;
};

export function SiteChrome({ locale, dict }: Props) {
  const pathname = usePathname();
  if (pathname.includes("/admin")) return null;

  return (
    <div className="site-chrome">
      <div className="site-chrome-locales">
        {locales.map((item) => {
          const href = `/${item}${stripLocalePrefix(pathname)}`;
          return (
            <Link
              key={item}
              href={href}
              className={`site-chrome-link${item === locale ? " is-active" : ""}`}
              aria-current={item === locale ? "page" : undefined}
            >
              {localeLabels[item]}
            </Link>
          );
        })}
      </div>
      <Link href={`/${locale}/search`} className="site-chrome-link">
        {dict.nav.search}
      </Link>
      <Link href={`/${locale}/about`} className="site-chrome-link">
        {dict.nav.about}
      </Link>
    </div>
  );
}
