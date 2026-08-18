import Link from "next/link";
import { notFound } from "next/navigation";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import { fetchPublicJournals } from "@/lib/api";

export default async function JournalsPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale: raw } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw as Locale;
  const dict = getDictionary(locale);
  const journals = await fetchPublicJournals(locale);

  return (
    <section className="px-6 py-24 sm:px-10 lg:px-14">
      <h1 className="display-font text-3xl font-bold">{dict.nav.journals}</h1>
      {journals.length === 0 ? (
        <p className="mt-6 max-w-xl text-[var(--text-muted)]">
          {dict.journals.empty}
        </p>
      ) : (
        <ul className="mt-10 grid max-w-3xl gap-4">
          {journals.map((journal) => (
            <li key={journal.slug}>
              <Link
                href={`/${locale}/journals/${journal.slug}`}
                className="glass glass-hover block rounded-[var(--radius-card)] p-6"
              >
                <h2 className="display-font text-xl font-bold">
                  {journal.title}
                </h2>
                {journal.summary ? (
                  <p className="mt-2 text-sm leading-relaxed text-[var(--text-muted)]">
                    {journal.summary}
                  </p>
                ) : null}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
