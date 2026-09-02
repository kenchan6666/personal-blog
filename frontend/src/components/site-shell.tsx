"use client";

import { useEffect, useState } from "react";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import { LocaleHtml } from "./locale-html";
import { RouteProgress } from "./route-progress";
import { Sidebar } from "./sidebar";
import { SiteChrome } from "./site-chrome";

const DESKTOP_NAV = "(min-width: 1024px)";

type Props = {
  locale: Locale;
  dict: Dictionary;
  children: React.ReactNode;
};

export function SiteShell({ locale, dict, children }: Props) {
  const [open, setOpen] = useState(false);

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

  return (
    <div className="relative z-10 min-h-screen">
      <LocaleHtml locale={locale} />
      <RouteProgress />
      <Sidebar
        locale={locale}
        dict={dict}
        open={open}
        onToggle={() => setOpen((v) => !v)}
        onNavigate={() => setOpen(false)}
      />

      <SiteChrome locale={locale} dict={dict} />
      <main className="site-main">{children}</main>
    </div>
  );
}
