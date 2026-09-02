import { notFound } from "next/navigation";
import { PageFrame } from "@/components/page-frame";
import { PostArchive } from "@/components/post-archive";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import { fetchPublicArticles } from "@/lib/api";

export const dynamic = "force-dynamic";

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
    <PageFrame title={dict.nav.articles} lead={dict.articles.lead} narrow>
      <PostArchive
        locale={locale}
        searchPlaceholder={dict.archive.search}
        chrome={{
          all: dict.archive.all,
          count: dict.articles.count,
          newest: dict.articles.sortNewest,
          oldest: dict.articles.sortOldest,
          longest: dict.articles.sortLongest,
          related: dict.articles.relatedProject,
        }}
        labels={{
          search: dict.archive.search,
          empty: dict.articles.empty,
          noMatch: dict.archive.noMatch,
          minutes: dict.archive.minutes,
          words: dict.archive.words,
        }}
        posts={articles.map((article) => ({
          href: `/${locale}/articles/${article.slug}`,
          title: article.title,
          summary: article.summary,
          publishedAt: article.publishedAt,
          wordCount: article.wordCount,
          readingMinutes: article.readingMinutes,
          project: article.relatedProject ?? undefined,
        }))}
      />
    </PageFrame>
  );
}
