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
import { SiteFooter } from "./site-footer";
import { TopNav } from "./top-nav";

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
  const [hasResume, setHasResume] = useState<boolean | null>(null);
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
    fetch("/api/public/resumes", { signal: ctrl.signal })
      .then((res) => (res.ok ? (res.json() as Promise<unknown[]>) : []))
      .then((rows) => {
        if (!ignore) setHasResume(Array.isArray(rows) && rows.length > 0);
      })
      .catch(() => {});
    return () => {
      ignore = true;
      ctrl.abort();
    };
  }, [locale, pathname]);

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
  const admin = pathname.includes("/admin");

  return (
    <div className="site-root">
      <LocaleHtml locale={locale} />
      <RouteProgress />
      <TopNav
        locale={locale}
        dict={shellDict}
        open={open}
        showResume={hasResume !== false}
        onToggle={() => setOpen((v) => !v)}
        onNavigate={() => setOpen(false)}
      />
      <PublicGuide
        locale={locale}
        dict={shellDict.guide}
        open={guideOpen}
        onClose={closeGuide}
      />
      {admin ? null : (
        <button
          type="button"
          className="guide-fab liquid-glass"
          onClick={() => {
            setOpen(false);
            setGuideOpen(true);
          }}
        >
          <span className="guide-orb" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
          {shellDict.guide.entry}
        </button>
      )}

      <main className="site-main">{children}</main>
      {admin ? null : (
        <SiteFooter
          locale={locale}
          dict={shellDict}
          showResume={hasResume !== false}
        />
      )}
    </div>
  );
}
