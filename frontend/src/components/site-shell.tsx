"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { getDictionary } from "@/i18n/dictionaries";
import { defaultLocale, isLocale, type Locale } from "@/i18n/config";
import type { PublicSite } from "@/lib/api";
import { brandForShell, publicBrand } from "@/lib/site-content";
import { LocaleHtml } from "./locale-html";
import { PublicGuide } from "./public-guide";
import { RouteProgress } from "./route-progress";
import { Sidebar } from "./sidebar";
import { SiteChrome } from "./site-chrome";

const DESKTOP_NAV = "(min-width: 1024px)";

function localeFromPath(pathname: string): Locale {
  const segment = pathname.split("/").filter(Boolean)[0] ?? defaultLocale;
  return isLocale(segment) ? segment : defaultLocale;
}

type Props = {
  children: React.ReactNode;
};

export function SiteShell({ children }: Props) {
  const pathname = usePathname();
  const locale = localeFromPath(pathname);
  const dict = getDictionary(locale);
  const [brand, setBrand] = useState(() => publicBrand(dict.brand));
  const [open, setOpen] = useState(false);
  const [guideOpen, setGuideOpen] = useState(false);
  const closeGuide = useCallback(() => setGuideOpen(false), []);

  useEffect(() => {
    const next = getDictionary(locale);
    setBrand(publicBrand(next.brand));
    let ignore = false;
    const ctrl = new AbortController();
    fetch(`/api/public/site?locale=${encodeURIComponent(locale)}`, {
      signal: ctrl.signal,
    })
      .then((res) => (res.ok ? (res.json() as Promise<PublicSite>) : null))
      .then((site) => {
        if (!ignore && site) setBrand(brandForShell(next, site));
      })
      .catch(() => {});
    return () => {
      ignore = true;
      ctrl.abort();
    };
  }, [locale]);

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const mq = window.matchMedia(DESKTOP_NAV);
    if (mq.matches) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function onChange() {
      document.body.style.overflow = mq.matches ? previous : "hidden";
    }
    mq.addEventListener("change", onChange);
    return () => {
      mq.removeEventListener("change", onChange);
      document.body.style.overflow = previous;
    };
  }, [open]);

  const shellDict = { ...dict, brand };

  return (
    <div className="relative z-10 min-h-screen">
      <LocaleHtml locale={locale} />
      <RouteProgress />
      <Sidebar
        locale={locale}
        dict={shellDict}
        open={open}
        onToggle={() => setOpen((v) => !v)}
        onNavigate={() => setOpen(false)}
        onGuide={() => {
          setOpen(false);
          setGuideOpen(true);
        }}
      />
      <PublicGuide
        locale={locale}
        dict={shellDict.guide}
        open={guideOpen}
        onClose={closeGuide}
      />

      <SiteChrome locale={locale} dict={shellDict} />
      <main className="site-main">{children}</main>
    </div>
  );
}
