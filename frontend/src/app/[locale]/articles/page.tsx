import Link from "next/link";
import { notFound } from "next/navigation";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import { fetchPublicArticles } from "@/lib/api";

export default async function ArticlesPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale: raw } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw as Locale;
  const dict = getDictionary(locale);
  const articles = await fetchPublicArticles(locale);

  return (
    <section className="px-6 py-24 sm:px-10 lg:px-14">
      <h1 className="display-font text-3xl font-bold">{dict.nav.articles}</h1>
      {articles.length === 0 ? (
        <p className="mt-6 max-w-xl text-[var(--text-muted)]">
          {dict.articles.empty}
        </p>
      ) : (
        <ul className="mt-10 grid max-w-3xl gap-4">
          {articles.map((article) => (
            <li key={article.slug}>
              <Link
                href={`/${locale}/articles/${article.slug}`}
                className="glass glass-hover block rounded-[var(--radius-card)] p-6"
              >
                <h2 className="display-font text-xl font-bold">
                  {article.title}
                </h2>
                {article.summary ? (
                  <p className="mt-2 text-sm leading-relaxed text-[var(--text-muted)]">
                    {article.summary}
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
