import Link from "next/link";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";

type Props = {
  locale: Locale;
  dict: Dictionary;
  showResume?: boolean;
};

export function SiteFooter({ locale, dict, showResume = true }: Props) {
  return (
    <footer className="site-footer">
      <div className="home-wrap site-footer-inner">
        <span>© {new Date().getFullYear()} {dict.brand}</span>
        <nav className="site-footer-links">
          <Link href={`/${locale}/about`}>{dict.nav.about}</Link>
          {showResume ? (
            <Link href={`/${locale}/resume`}>{dict.nav.resume}</Link>
          ) : null}
          <Link href={`/${locale}/search`}>{dict.nav.search}</Link>
        </nav>
      </div>
    </footer>
  );
}
