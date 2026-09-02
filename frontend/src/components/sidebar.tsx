"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import { localeLabels, locales, stripLocalePrefix } from "@/i18n/config";
import { getSessionToken } from "@/lib/api";

type Props = {
  locale: Locale;
  dict: Dictionary;
  open: boolean;
  onToggle: () => void;
  onNavigate: () => void;
};

const links = [
  { key: "home", href: "" },
  { key: "about", href: "/about" },
  { key: "projects", href: "/projects" },
  { key: "articles", href: "/articles" },
  { key: "journals", href: "/journals" },
  { key: "search", href: "/search" },
] as const;

function MenuIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden>
      <path
        fill="currentColor"
        d="M4 6.4h16v1.7H4zm0 4.75h16v1.7H4zm0 4.75h16v1.7H4z"
      />
    </svg>
  );
}

function NavIcon({ name }: { name: (typeof links)[number]["key"] }) {
  const paths: Record<(typeof links)[number]["key"], string> = {
    home: "M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1z",
    about: "M12 12.5a3.25 3.25 0 1 0-3.25-3.25A3.25 3.25 0 0 0 12 12.5Zm-7 7.25c0-3.1 3.13-5 7-5s7 1.9 7 5v1.25H5z",
    projects:
      "M4 7.5A2.5 2.5 0 0 1 6.5 5h3.2L11 7h6.5A2.5 2.5 0 0 1 20 9.5v7A2.5 2.5 0 0 1 17.5 19h-11A2.5 2.5 0 0 1 4 16.5z",
    articles:
      "M6 4.75h9.5A2.5 2.5 0 0 1 18 7.25v12H7.5A1.5 1.5 0 0 1 6 17.75zm2 4.5h6.5v1.4H8zm0 3h6.5v1.4H8z",
    journals:
      "M7 4.5h10.5A1.5 1.5 0 0 1 19 6v13.2l-3.4-1.8-3.1 1.8-3.1-1.8L6 19.2V6a1.5 1.5 0 0 1 1-1.5z",
    search:
      "M11 5.25a5.75 5.75 0 1 1 0 11.5 5.75 5.75 0 0 1 0-11.5Zm6.7 10.4 2.4 2.4",
  };
  return (
    <svg viewBox="0 0 24 24" className="nav-link-icon" aria-hidden>
      <path fill="currentColor" d={paths[name]} />
    </svg>
  );
}

export function Sidebar({
  locale,
  dict,
  open,
  onToggle,
  onNavigate,
}: Props) {
  const pathname = usePathname();
  const [showAdmin, setShowAdmin] = useState(false);

  useEffect(() => {
    setShowAdmin(Boolean(getSessionToken()));
  }, [pathname]);

  return (
    <div className={`site-nav${open ? " is-open" : ""}`}>
      <button
        type="button"
        className="icon-btn sidebar-fab"
        aria-label={dict.openMenu}
        aria-expanded={open}
        aria-controls="site-sidebar"
        onClick={onToggle}
      >
        <MenuIcon />
      </button>

      <div
        className="scrim site-nav-scrim"
        onClick={onToggle}
        aria-hidden={!open}
      />

      <aside id="site-sidebar" className="sidebar-panel">
        <button
          type="button"
          className="icon-btn sidebar-toggle"
          aria-label={open ? dict.closeMenu : dict.openMenu}
          aria-expanded={open}
          aria-controls="site-sidebar"
          onClick={onToggle}
        >
          <span
            className={`inline-block leading-none transition-transform duration-300 ease-out ${
              open ? "rotate-0" : "rotate-180"
            }`}
            aria-hidden
          >
            ‹
          </span>
        </button>

        <div className="sidebar-inner">
          <Link
            href={`/${locale}`}
            className="sidebar-brand display-font"
            onClick={onNavigate}
            title={dict.brand}
          >
            <span className="sidebar-brand-full">{dict.brand}</span>
            <span className="sidebar-brand-mark" aria-hidden>
              k
            </span>
          </Link>

          <nav className="flex flex-1 flex-col gap-1">
            {links.map((item) => {
              const href = `/${locale}${item.href}`;
              const label = dict.nav[item.key];
              const active =
                item.href === ""
                  ? pathname === `/${locale}` || pathname === `/${locale}/`
                  : pathname.startsWith(href);
              return (
                <Link
                  key={item.key}
                  href={href}
                  onClick={onNavigate}
                  title={label}
                  aria-label={label}
                  className={`nav-link ${active ? "nav-link-active" : ""}`}
                >
                  <NavIcon name={item.key} />
                  <span className="nav-link-label">{label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="sidebar-locales hairline-t mt-6 flex flex-wrap gap-2 pt-4">
            {locales.map((item) => {
              const rest = stripLocalePrefix(pathname);
              const href = `/${item}${rest}`;
              const active = item === locale;
              return (
                <Link
                  key={item}
                  href={href}
                  onClick={onNavigate}
                  className={`locale-chip ${active ? "locale-chip-active" : ""}`}
                >
                  {localeLabels[item]}
                </Link>
              );
            })}
          </div>

          {showAdmin ? (
            <Link
              href={`/${locale}/admin`}
              onClick={onNavigate}
              className="nav-link sidebar-admin mt-3 text-center text-xs font-semibold"
            >
              {dict.nav.admin}
            </Link>
          ) : null}
        </div>
      </aside>
    </div>
  );
}
