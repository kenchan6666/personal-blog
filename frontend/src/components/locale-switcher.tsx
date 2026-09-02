"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  localeLabels,
  locales,
  stripLocalePrefix,
  type Locale,
} from "@/i18n/config";

type Props = {
  locale: Locale;
  tabIndex?: number;
};

export function LocaleSwitcher({ locale, tabIndex }: Props) {
  const pathname = usePathname();
  const router = useRouter();
  const rest = stripLocalePrefix(pathname);
  const [pending, setPending] = useState<Locale | null>(null);

  useEffect(() => {
    setPending(null);
  }, [locale, pathname]);

  useEffect(() => {
    for (const item of locales) {
      if (item === locale) continue;
      router.prefetch(`/${item}${rest}`);
    }
  }, [locale, rest, router]);

  return (
    <div className="hairline-t mt-6 flex flex-wrap gap-2 pt-4" role="group">
      {locales.map((item) => {
        const href = `/${item}${rest}`;
        const active = (pending ?? locale) === item;
        return (
          <Link
            key={item}
            href={href}
            prefetch
            scroll={false}
            tabIndex={tabIndex}
            className={`locale-chip ${active ? "locale-chip-active" : ""}`}
            aria-current={item === locale ? "page" : undefined}
            onClick={() => {
              if (item !== locale) setPending(item);
            }}
          >
            {localeLabels[item]}
          </Link>
        );
      })}
    </div>
  );
}
