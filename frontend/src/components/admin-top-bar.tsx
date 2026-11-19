"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import type { PublicSite } from "@/lib/api";
import { brandForShell, publicBrand } from "@/lib/site-content";
import { ThemeToggle } from "./theme-toggle";

export type AdminSection = {
  key: string;
  label: string;
  icon: React.ReactNode;
};

type Props = {
  locale: Locale;
  dict: Dictionary;
  /** Shown next to the brand; on phones it is the only section label up top. */
  title: string;
  email?: string;
  sections?: AdminSection[];
  active?: string;
  onSelect?: (key: string) => void;
  onLogout?: () => void;
};

function useBrand(locale: Locale, dict: Dictionary) {
  const [brand, setBrand] = useState(() => publicBrand(dict.brand));
  useEffect(() => {
    const ctrl = new AbortController();
    fetch(`/api/public/site?locale=${encodeURIComponent(locale)}`, {
      signal: ctrl.signal,
    })
      .then((res) => (res.ok ? (res.json() as Promise<PublicSite>) : null))
      .then((site) => {
        if (site) setBrand(brandForShell(dict, site));
      })
      .catch(() => {});
    return () => ctrl.abort();
  }, [dict, locale]);
  return brand;
}

/**
 * Compact admin chrome: brand + current section + sign out. Section tabs sit
 * in the bar on desktop and move to a bottom tab bar under 768px.
 */
export function AdminTopBar({
  locale,
  dict,
  title,
  email,
  sections,
  active,
  onSelect,
  onLogout,
}: Props) {
  const a = dict.admin;
  const brand = useBrand(locale, dict);
  const hasTabs = Boolean(sections && sections.length > 0);

  return (
    <>
      <header
        className={`admin-bar liquid-glass liquid-glass-bar${hasTabs ? " has-tabs" : ""}`}
      >
        <div className="admin-bar-inner">
          <div className="admin-bar-lead">
            <Link
              href={`/${locale}`}
              className="admin-bar-brand"
              aria-label={`${a.viewSite}: ${brand}`}
              title={a.viewSite}
            >
              {brand}
            </Link>
            <span className="admin-bar-sep" aria-hidden>
              /
            </span>
            <h1 className="admin-bar-title">{title}</h1>
          </div>

          {hasTabs && sections ? (
            <nav className="admin-bar-tabs" aria-label={a.adminSections}>
              {sections.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  className="admin-bar-tab"
                  aria-current={item.key === active ? "page" : undefined}
                  onClick={() => onSelect?.(item.key)}
                >
                  {item.label}
                </button>
              ))}
            </nav>
          ) : null}

          <div className="admin-bar-tools">
            {email ? (
              <span className="admin-bar-email" title={`${a.signedInAs}: ${email}`}>
                {email}
              </span>
            ) : null}
            <ThemeToggle dict={dict} />
            {onLogout ? (
              <button type="button" className="admin-bar-logout" onClick={onLogout}>
                {a.logout}
              </button>
            ) : (
              <Link href={`/${locale}`} className="admin-bar-logout">
                {a.viewSite}
              </Link>
            )}
          </div>
        </div>
      </header>

      {hasTabs && sections ? (
        <nav
          className="admin-tabbar liquid-glass liquid-glass-strong"
          aria-label={a.adminSections}
        >
          {sections.map((item) => (
            <button
              key={item.key}
              type="button"
              className="admin-tabbar-item"
              aria-current={item.key === active ? "page" : undefined}
              onClick={() => onSelect?.(item.key)}
            >
              <span className="admin-tabbar-icon" aria-hidden>
                {item.icon}
              </span>
              <span className="admin-tabbar-label">{item.label}</span>
            </button>
          ))}
        </nav>
      ) : null}
    </>
  );
}
