import { notFound } from "next/navigation";
import { PageFrame } from "@/components/page-frame";
import { PostArchive } from "@/components/post-archive";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import { fetchPublicJournals } from "@/lib/api";
import { pageMetadata } from "@/lib/seo";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale: raw } = await params;
  if (!isLocale(raw)) return {};
  const locale = raw as Locale;
  const dict = getDictionary(locale);
  return pageMetadata({
    locale,
    title: dict.nav.journals,
    path: "/journals",
  });
}

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
    <PageFrame title={dict.nav.journals} narrow>
      <PostArchive
        locale={locale}
        searchPlaceholder={dict.archive.search}
        labels={{
          search: dict.archive.search,
          empty: dict.journals.empty,
          noMatch: dict.archive.noMatch,
          minutes: dict.archive.minutes,
          words: dict.archive.words,
        }}
        posts={journals.map((journal) => ({
          href: `/${locale}/journals/${journal.slug}`,
          title: journal.title,
          summary: journal.summary,
          publishedAt: journal.publishedAt,
          wordCount: journal.wordCount,
          readingMinutes: journal.readingMinutes,
        }))}
      />
    </PageFrame>
  );
}
