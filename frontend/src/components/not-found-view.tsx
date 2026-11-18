import Link from "next/link";
import { getDictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";

export function NotFoundView({ locale }: { locale: Locale }) {
  const dict = getDictionary(locale);
  return (
    <section className="not-found" aria-labelledby="not-found-title">
      {/* Decorative numeral drawn in CSS (::before) so it is not read out
          or contrast-checked as body text. */}
      <span className="not-found-code" aria-hidden data-code="404" />
      <h1 id="not-found-title" className="not-found-title display-font">
        {dict.notFound.title}
      </h1>
      <p className="not-found-body">{dict.notFound.body}</p>
      <div className="not-found-actions">
        <Link href={`/${locale}`} className="btn-cta">
          {dict.backHome}
        </Link>
        <Link href={`/${locale}/search`} className="btn-ghost">
          {dict.notFound.search}
        </Link>
      </div>
    </section>
  );
}
