import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { ArticleToc } from "@/components/article-toc";
import { CommentThread } from "@/components/comment-thread";
import { MarkdownBody } from "@/components/markdown-body";
import { ReadingProgress } from "@/components/reading-progress";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import { articleHref, fetchPublicArticle, type PublicArticle } from "@/lib/api";
import { extractMarkdownHeadings } from "@/lib/headings";
import { formatCount, formatPostDate } from "@/lib/post-meta";

export const dynamic = "force-dynamic";

export default async function ArticlePathPage({
  params,
}: {
  params: Promise<{ locale: string; path: string[] }>;
}) {
  const { locale: raw, path } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw as Locale;

  if (path.length === 1) {
    const article = await fetchPublicArticle(locale, path[0]);
    if (!article) notFound();
    if (article.categorySlug) {
      redirect(articleHref(locale, article));
    }
    return renderArticle(locale, article);
  }

  if (path.length !== 2) notFound();

  const [category, slug] = path;
  const article = await fetchPublicArticle(locale, slug);
  if (!article) notFound();

  const canonical = article.categorySlug || "";
  if (category !== canonical) {
    redirect(articleHref(locale, article));
  }

  return renderArticle(locale, article);
}

function renderArticle(locale: Locale, article: PublicArticle) {
  const dict = getDictionary(locale);
  const headings = extractMarkdownHeadings(article.body);
  const showToc = headings.length >= 2;
  const showCategory = Boolean(article.categoryTitle);

  return (
    <article className="article-page">
      <ReadingProgress />
      <div className={`article-page-inner${showToc ? " has-toc" : ""}`}>
        <Link href={`/${locale}/articles`} className="page-back">
          ← {dict.nav.articles}
        </Link>
        <header className="article-header">
          <p className="article-kicker">
            {dict.articles.title}
            {showCategory ? (
              <span className="article-tag">{article.categoryTitle}</span>
            ) : null}
          </p>
          <h1 className="article-title display-font">{article.title}</h1>
          {article.summary ? (
            <p className="article-lede">{article.summary}</p>
          ) : null}
          <p className="article-meta">
            <time dateTime={article.publishedAt}>
              {formatPostDate(article.publishedAt, locale)}
            </time>
            <span aria-hidden>·</span>
            <span>
              {formatCount(dict.archive.minutes, article.readingMinutes)}
            </span>
            <span aria-hidden>·</span>
            <span>{formatCount(dict.archive.words, article.wordCount)}</span>
          </p>
          {article.relatedProject ? (
            <Link
              href={`/${locale}/projects/${article.relatedProject.slug}`}
              className="article-related"
            >
              {dict.articles.relatedProject}
              {" · "}
              {article.relatedProject.title}
            </Link>
          ) : null}
        </header>
        <div className="article-layout">
          <div className="article-body">
            <MarkdownBody source={article.body} />
          </div>
          {showToc ? (
            <ArticleToc headings={headings} label={dict.articles.contents} />
          ) : null}
        </div>
        <CommentThread kind="articles" slug={article.slug} dict={dict} />
      </div>
    </article>
  );
}
