import Link from "next/link";
import { notFound } from "next/navigation";
import { MarkdownBody } from "@/components/markdown-body";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import { fetchPublicJournal } from "@/lib/api";

export default async function JournalDetailPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale: raw, slug } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw as Locale;
  const dict = getDictionary(locale);
  const journal = await fetchPublicJournal(locale, slug);
  if (!journal) notFound();

  return (
    <article className="px-6 py-24 sm:px-10 lg:px-14">
      <Link
        href={`/${locale}/journals`}
        className="text-sm text-[var(--accent-link)] hover:underline"
      >
        ← {dict.nav.journals}
      </Link>
      <h1 className="display-font mt-6 max-w-3xl text-4xl font-bold tracking-tight">
        {journal.title}
      </h1>
      {journal.summary ? (
        <p className="mt-4 max-w-[70ch] text-lg text-[var(--text-muted)]">
          {journal.summary}
        </p>
      ) : null}
      <div className="mt-10">
        <MarkdownBody source={journal.body} />
      </div>
    </article>
  );
}
