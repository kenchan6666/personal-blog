import Link from "next/link";
import { notFound } from "next/navigation";
import { CommentThread } from "@/components/comment-thread";
import { MarkdownBody } from "@/components/markdown-body";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import { fetchPublicArticle } from "@/lib/api";

export default async function ArticleDetailPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale: raw, slug } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw as Locale;
  const dict = getDictionary(locale);
  const article = await fetchPublicArticle(locale, slug);
  if (!article) notFound();

  return (
    <article className="px-6 py-24 sm:px-10 lg:px-14">
      <Link
        href={`/${locale}/articles`}
        className="text-sm text-[var(--accent-link)] hover:underline"
      >
        ← {dict.nav.articles}
      </Link>
      <h1 className="display-font mt-6 max-w-3xl text-4xl font-bold tracking-tight">
        {article.title}
      </h1>
      {article.summary ? (
        <p className="mt-4 max-w-[70ch] text-lg text-[var(--text-muted)]">
          {article.summary}
        </p>
      ) : null}
      {article.relatedProject ? (
        <p className="mt-4 text-sm text-[var(--text-muted)]">
          {dict.articles.relatedProject}:{" "}
          <Link
            href={`/${locale}/projects/${article.relatedProject.slug}`}
            className="text-[var(--accent-link)] hover:underline"
          >
            {article.relatedProject.title}
          </Link>
        </p>
      ) : null}
      <div className="mt-10">
        <MarkdownBody source={article.body} />
      </div>
      <CommentThread kind="articles" slug={article.slug} dict={dict} />
    </article>
  );
}
