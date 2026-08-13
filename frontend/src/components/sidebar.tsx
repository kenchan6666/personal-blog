"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import { locales } from "@/i18n/config";

type Props = {
  locale: Locale;
  dict: Dictionary;
  open: boolean;
  onToggle: () => void;
  onNavigate: () => void;
};

const links = [
  { key: "home", href: "" },
  { key: "projects", href: "/projects" },
  { key: "articles", href: "/articles" },
  { key: "journals", href: "/journals" },
] as const;

export function Sidebar({
  locale,
  dict,
  open,
  onToggle,
  onNavigate,
}: Props) {
  const pathname = usePathname();

  return (
    <>
      {/* Scrim: covers page behind whenever panel is open */}
      <div
        className={`fixed inset-0 z-40 bg-black/50 transition-opacity duration-300 ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onToggle}
        aria-hidden={!open}
      />

      <aside
        className={`sidebar-panel fixed top-3 bottom-3 left-3 z-50 overflow-hidden rounded-[var(--radius-panel)] transition-[width] duration-300 ease-out ${
          open
            ? "w-[min(100%-1.5rem,var(--sidebar-width))]"
            : "w-[var(--sidebar-rail)]"
        }`}
      >
        <button
          type="button"
          className="sidebar-toggle absolute top-4 right-4 z-20 flex h-9 w-9 items-center justify-center rounded-full border border-white/15 bg-white/5 text-lg text-[var(--text-muted)] transition-[color,background] duration-300 hover:bg-white/10 hover:text-white"
          aria-label={open ? dict.closeMenu : dict.openMenu}
          aria-expanded={open}
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
                  className={`rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                    active
                      ? "bg-white/12 text-[var(--accent-link)]"
                      : "text-[var(--text-muted)] hover:bg-white/8 hover:text-white"
                  }`}
                >
                  {dict.nav[item.key]}
                </Link>
              );
            })}
          </nav>

          <div className="mt-6 flex gap-2 border-t border-white/10 pt-4">
            {locales.map((l) => {
              const rest = pathname.replace(/^\/(zh-Hant|en)/, "") || "";
              const href = `/${l}${rest}`;
              const active = l === locale;
              return (
                <Link
                  key={l}
                  href={href}
                  onClick={onNavigate}
                  tabIndex={open ? 0 : -1}
                  className={`flex-1 rounded-[var(--radius-control)] px-3 py-2 text-center text-xs font-semibold tracking-wide ${
                    active
                      ? "bg-white/15 text-white"
                      : "text-[var(--text-muted)] hover:bg-white/8"
                  }`}
                >
                  {l === "zh-Hant" ? "繁中" : "EN"}
                </Link>
              );
            })}
          </div>
        </div>
      </aside>
    </>
  );
}
