import { notFound } from "next/navigation";
import { CommentThread } from "@/components/comment-thread";
import { MarkdownBody } from "@/components/markdown-body";
import { PageFrame } from "@/components/page-frame";
import { PostMetaLine } from "@/components/post-archive";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import { fetchPublicJournal } from "@/lib/api";

export const dynamic = "force-dynamic";

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
    <PageFrame
      title={journal.title}
      lead={journal.summary}
      back={{ href: `/${locale}/journals`, label: dict.nav.journals }}
      narrow
    >
      <PostMetaLine
        locale={locale}
        publishedAt={journal.publishedAt}
        readingMinutes={journal.readingMinutes}
        wordCount={journal.wordCount}
        labels={{
          minutes: dict.archive.minutes,
          words: dict.archive.words,
        }}
      />
      <div className="post-body">
        <MarkdownBody source={journal.body} />
      </div>
      <CommentThread kind="journals" slug={journal.slug} dict={dict} />
    </PageFrame>
  );
}
