"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import { localeLabels, locales, stripLocalePrefix } from "@/i18n/config";

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

export function Sidebar({
  locale,
  dict,
  open,
  onToggle,
  onNavigate,
}: Props) {
  const pathname = usePathname();

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

        <div
          className={`flex h-full flex-col p-5 pt-16 transition-opacity duration-300 ease-out ${
            open ? "opacity-100" : "pointer-events-none opacity-0"
          }`}
        >
          <Link
            href={`/${locale}`}
            className="display-font mb-8 max-w-[calc(100%-3rem)] truncate text-2xl font-extrabold tracking-tight"
            onClick={onNavigate}
            tabIndex={open ? 0 : -1}
          >
            {dict.brand}
          </Link>

          <nav className="flex flex-1 flex-col gap-1">
            {links.map((item) => {
              const href = `/${locale}${item.href}`;
              const active =
                item.href === ""
                  ? pathname === `/${locale}` || pathname === `/${locale}/`
                  : pathname.startsWith(href);
              return (
                <Link
                  key={item.key}
                  href={href}
                  onClick={onNavigate}
                  tabIndex={open ? 0 : -1}
                  className={`nav-link ${active ? "nav-link-active" : ""}`}
                >
                  {dict.nav[item.key]}
                </Link>
              );
            })}
          </nav>

          <div className="hairline-t mt-6 flex flex-wrap gap-2 pt-4">
          {locales.map((l) => {
            const rest = stripLocalePrefix(pathname);
            const href = `/${l}${rest}`;
            const active = l === locale;
            return (
              <Link
                key={l}
                href={href}
                onClick={onNavigate}
                tabIndex={open ? 0 : -1}
                className={`locale-chip ${active ? "locale-chip-active" : ""}`}
              >
                {localeLabels[l]}
              </Link>
            );
          })}
        </div>

        <Link
          href={`/${locale}/admin`}
          onClick={onNavigate}
          tabIndex={open ? 0 : -1}
          className="nav-link mt-3 text-center text-xs font-semibold"
        >
          {dict.nav.admin}
        </Link>
        </div>
      </aside>
    </div>
  );
}
