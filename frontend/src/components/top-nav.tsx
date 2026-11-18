"use client";

import { useSyncExternalStore } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import { getSessionToken } from "@/lib/api";
import { LocaleSwitcher } from "./locale-switcher";
import { ThemeToggle } from "./theme-toggle";

type Props = {
  locale: Locale;
  dict: Dictionary;
  open: boolean;
  onToggle: () => void;
  onNavigate: () => void;
  /** Opens the AI guide; shown as a nav button on phones instead of a floating launcher. */
  onOpenGuide?: () => void;
  showResume?: boolean;
};

const links = [
  { key: "home", href: "" },
  { key: "projects", href: "/projects" },
  { key: "articles", href: "/articles" },
  { key: "journals", href: "/journals" },
  { key: "about", href: "/about" },
  { key: "resume", href: "/resume" },
  { key: "search", href: "/search" },
] as const;

function subscribeToStorage(onChange: () => void) {
  window.addEventListener("storage", onChange);
  return () => window.removeEventListener("storage", onChange);
}

function MenuIcon({ open }: { open: boolean }) {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden>
      {open ? (
        <path
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          d="M6 6l12 12M18 6L6 18"
        />
      ) : (
        <path
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          d="M4 7h16M4 12h16M4 17h16"
        />
      )}
    </svg>
  );
}

export function TopNav({
  locale,
  dict,
  open,
  onToggle,
  onNavigate,
  onOpenGuide,
  showResume = true,
}: Props) {
  const pathname = usePathname();
  const showAdmin = useSyncExternalStore(
    subscribeToStorage,
    () => Boolean(getSessionToken()),
    () => false,
  );

  const items = links
    .filter((item) => item.key !== "resume" || showResume)
    .map((item) => {
      const href = `/${locale}${item.href}`;
      const active =
        item.href === ""
          ? pathname === `/${locale}` || pathname === `/${locale}/`
          : pathname.startsWith(href);
      return { key: item.key, href, active, label: dict.nav[item.key] };
    });

  return (
    <>
      <header className="top-nav liquid-glass liquid-glass-bar">
        <div className="top-nav-inner">
          <Link href={`/${locale}`} className="top-nav-brand" onClick={onNavigate}>
            {dict.brand}
          </Link>

          <nav className="top-nav-links" aria-label={dict.brand}>
            {items.map((item) => (
              <Link
                key={item.key}
                href={item.href}
                className="top-nav-link"
                aria-current={item.active ? "page" : undefined}
              >
                {item.label}
                {item.active ? (
                  <span className="top-nav-indicator" aria-hidden />
                ) : null}
              </Link>
            ))}
            {showAdmin ? (
              <Link href={`/${locale}/admin`} className="top-nav-link">
                {dict.nav.admin}
              </Link>
            ) : null}
          </nav>

          <div className="top-nav-tools">
            <div className="top-nav-locale">
              <LocaleSwitcher locale={locale} />
            </div>
            {onOpenGuide ? (
              <button
                type="button"
                className="top-nav-guide"
                aria-label={dict.guide.entry}
                onClick={onOpenGuide}
              >
                <span className="guide-orb" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                </span>
              </button>
            ) : null}
            <ThemeToggle dict={dict} />
            <button
              type="button"
              className="top-nav-menu"
              aria-label={open ? dict.closeMenu : dict.openMenu}
              aria-expanded={open}
              aria-controls="site-menu-sheet"
              onClick={onToggle}
            >
              <MenuIcon open={open} />
            </button>
          </div>
        </div>
      </header>

      <div
        className={`nav-sheet-scrim${open ? " is-open" : ""}`}
        onClick={onToggle}
        aria-hidden
      />
      <div
        id="site-menu-sheet"
        className={`nav-sheet liquid-glass liquid-glass-strong${open ? " is-open" : ""}`}
        aria-hidden={!open}
        inert={!open}
      >
        <nav className="nav-sheet-links">
          {items.map((item) => (
            <Link
              key={item.key}
              href={item.href}
              onClick={onNavigate}
              tabIndex={open ? 0 : -1}
              className="nav-sheet-link"
              aria-current={item.active ? "page" : undefined}
            >
              {item.label}
            </Link>
          ))}
          {showAdmin ? (
            <Link
              href={`/${locale}/admin`}
              onClick={onNavigate}
              tabIndex={open ? 0 : -1}
              className="nav-sheet-link"
            >
              {dict.nav.admin}
            </Link>
          ) : null}
        </nav>
        <LocaleSwitcher locale={locale} tabIndex={open ? 0 : -1} />
      </div>
    </>
  );
}
