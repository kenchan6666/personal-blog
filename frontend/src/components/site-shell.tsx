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

  // Focus: move into the menu sheet when it opens, hand it back on close.
  useEffect(() => {
    if (!open) return;
    const opener = document.activeElement as HTMLElement | null;
    const frame = window.requestAnimationFrame(() => {
      document
        .querySelector<HTMLElement>("#site-menu-sheet .nav-sheet-link")
        ?.focus({ preventScroll: true });
    });
    return () => {
      window.cancelAnimationFrame(frame);
      const sheet = document.getElementById("site-menu-sheet");
      const active = document.activeElement;
      if (!active || active === document.body || sheet?.contains(active)) {
        opener?.focus?.({ preventScroll: true });
      }
    };
  }, [open]);

  // The guide focuses its own input; restore focus to whatever opened it.
  useEffect(() => {
    if (!guideOpen) return;
    const opener = document.activeElement as HTMLElement | null;
    return () => {
      const panel = document.querySelector(".public-guide");
      const active = document.activeElement;
      if (!active || active === document.body || panel?.contains(active)) {
        opener?.focus?.({ preventScroll: true });
      }
    };
  }, [guideOpen]);

  useEffect(() => {
    if (!open) return;
    const mq = window.matchMedia(DESKTOP_NAV);
    if (mq.matches) return;
    // Lock via a class on <html>: overflow hidden + scrollbar-gutter stable,
    // so desktop-width scrollbars don't vanish and shift the page sideways.
    const root = document.documentElement;
    root.classList.add("is-scroll-locked");
    function onChange() {
      root.classList.toggle("is-scroll-locked", !mq.matches);
    }
    mq.addEventListener("change", onChange);
    return () => {
      mq.removeEventListener("change", onChange);
      root.classList.remove("is-scroll-locked");
    };
  }, [open]);

  const shellDict = { ...dict, brand };
  const admin = pathname.includes("/admin");

  if (admin) {
    // Admin and login pages bring their own compact AdminTopBar.
    return (
      <div className="site-root is-admin">
        <LocaleHtml locale={locale} />
        <RouteProgress />
        <main className="site-main">{children}</main>
      </div>
    );
  }

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
        onOpenGuide={
          admin
            ? undefined
            : () => {
                setOpen(false);
                setGuideOpen(true);
              }
        }
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
          aria-label={shellDict.guide.entry}
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
          <span className="guide-fab-label">{shellDict.guide.entry}</span>
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
