import Link from "next/link";
import { notFound } from "next/navigation";
import { Hero } from "@/components/hero";
import { ProfileSection } from "@/components/profile-section";
import { getDictionary, type Dictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import {
  articleHref,
  fetchPublicArticles,
  fetchPublicJournals,
  fetchPublicProjects,
  fetchPublicSite,
  type PublicArticle,
  type PublicJournal,
} from "@/lib/api";
import { formatCount, formatPostDate } from "@/lib/post-meta";
import { pageMetadata } from "@/lib/seo";
import { firstMarkdownImage } from "@/lib/markdown-preview";
import { toProjectTiles } from "@/lib/project-tiles";
import { ProjectTile } from "@/components/project-tile";
import {
  mergeHeroContent,
  mergeProfileContent,
  pageCopy,
} from "@/lib/site-content";

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
  const site = await fetchPublicSite(locale);
  return pageMetadata({
    locale,
    title: mergeHeroContent(dict, site).brand,
    description: mergeHeroContent(dict, site).support,
    path: "",
  });
}

async function settle<T>(promise: Promise<T[]>): Promise<T[]> {
  try {
    return await promise;
  } catch {
    return [];
  }
}

function firstImage(markdown: string): string {
  return firstMarkdownImage(markdown);
}

function ArticleRow({
  article,
  locale,
  dict,
}: {
  article: PublicArticle;
  locale: Locale;
  dict: Dictionary;
}) {
  const image = firstImage(article.body);
  return (
    <li>
      <Link href={articleHref(locale, article)} className="post-row">
        <div className="post-row-text">
          {article.categoryTitle ? (
            <span className="post-tag">{article.categoryTitle}</span>
          ) : null}
          <h3 className="post-row-title">{article.title}</h3>
          {article.summary ? (
            <p className="post-row-summary">{article.summary}</p>
          ) : null}
          <p className="post-row-meta">
            {formatPostDate(article.publishedAt, locale)} ·{" "}
            {formatCount(dict.archive.minutes, article.readingMinutes)} ·{" "}
            {formatCount(dict.archive.words, article.wordCount)}
          </p>
        </div>
        {image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={image}
            alt=""
            width={168}
            height={96}
            loading="lazy"
            decoding="async"
            className="post-row-image"
          />
        ) : null}
      </Link>
    </li>
  );
}

function JournalRow({
  journal,
  locale,
}: {
  journal: PublicJournal;
  locale: Locale;
}) {
  return (
    <li>
      <Link
        href={`/${locale}/journals/${journal.slug}`}
        className="journal-row"
      >
        <span className="post-row-title">{journal.title}</span>
        <span className="post-row-meta">
          {formatPostDate(journal.publishedAt, locale)}
        </span>
      </Link>
    </li>
  );
}

export default async function HomePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale: raw } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw as Locale;
  const dict = getDictionary(locale);
  const [site, projects, articles, journals] = await Promise.all([
    fetchPublicSite(locale),
    settle(fetchPublicProjects(locale)),
    settle(fetchPublicArticles(locale)),
    settle(fetchPublicJournals(locale)),
  ]);
  const [featured, ...rest] = await toProjectTiles(projects, locale, {
    excerptFor: projects[0]?.slug,
  });
  const latestArticles = [...articles]
    .sort((a, b) => b.publishedAt.localeCompare(a.publishedAt))
    .slice(0, 4);
  const latestJournals = [...journals]
    .sort((a, b) => b.publishedAt.localeCompare(a.publishedAt))
    .slice(0, 5);

  return (
    <>
      <Hero
        locale={locale}
        content={mergeHeroContent(dict, site)}
        email={site?.profile.publicEmail ?? ""}
        links={site?.profile.links ?? []}
        visual={site?.hero.visual ?? null}
      />
      <ProfileSection content={mergeProfileContent(dict, site)} />
      {featured ? (
        <section className="home-section">
          <div className="home-wrap">
            <div className="home-section-head">
              <h2>{dict.nav.projects}</h2>
              <Link href={`/${locale}/projects`} className="home-section-link">
                {dict.hero.ctaProjects}
              </Link>
            </div>
            <ProjectTile
              project={featured}
              variant="feature"
              sourceLabel={dict.projects.source}
              aboutLabel={dict.projects.about}
            />
            {rest.length > 0 ? (
              <ul className="project-grid">
                {rest.map((project) => (
                  <li key={project.href}>
                    <ProjectTile
                      project={project}
                      sourceLabel={dict.projects.source}
                    />
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </section>
      ) : null}
      <section className="home-section">
        <div className="home-wrap home-writing">
          <div>
            <div className="home-section-head">
              <h2>{dict.articles.title}</h2>
              <p className="home-section-lead">
                {pageCopy(site, "articlesLead", dict.articles.lead)}
              </p>
            </div>
            {latestArticles.length > 0 ? (
              <ul className="post-list">
                {latestArticles.map((article) => (
                  <ArticleRow
                    key={article.slug}
                    article={article}
                    locale={locale}
                    dict={dict}
                  />
                ))}
              </ul>
            ) : (
              <p className="card home-empty">{dict.articles.empty}</p>
            )}
          </div>
          <div>
            <div className="home-section-head">
              <h2>{dict.journals.title}</h2>
            </div>
            {latestJournals.length > 0 ? (
              <ul className="card journal-list">
                {latestJournals.map((journal) => (
                  <JournalRow
                    key={journal.slug}
                    journal={journal}
                    locale={locale}
                  />
                ))}
              </ul>
            ) : (
              <p className="card home-empty">{dict.journals.empty}</p>
            )}
          </div>
        </div>
      </section>
    </>
  );
}
