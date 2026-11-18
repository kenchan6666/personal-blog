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
  mediaUrl,
  type PublicArticle,
  type PublicJournal,
  type PublicProject,
} from "@/lib/api";
import { formatCount, formatPostDate } from "@/lib/post-meta";
import { pageMetadata } from "@/lib/seo";
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

/** First image in a markdown body, e.g. `![](</api/public/media/content/x.jpg>)`. */
function firstImage(markdown: string): string {
  const match = markdown.match(/!\[[^\]]*\]\(\s*<?([^)\s>]+)>?/);
  return match ? mediaUrl(match[1]) : "";
}

function CoverPlaceholder({ label }: { label: string }) {
  return (
    <div className="project-cover" aria-hidden>
      <span className="project-cover-icon" />
      <span>{label}</span>
    </div>
  );
}

function FeaturedProject({
  project,
  locale,
  dict,
}: {
  project: PublicProject;
  locale: Locale;
  dict: Dictionary;
}) {
  const href = `/${locale}/projects/${project.slug}`;
  const excerpt = project.body
    .replace(/[#>*_`]/g, "")
    .split(/\n\s*\n/)
    .map((part) => part.trim())
    .find(Boolean);
  return (
    <article className="card project-feature">
      <Link href={href} tabIndex={-1} aria-hidden>
        <CoverPlaceholder label={dict.projects.coverPending} />
      </Link>
      <div className="project-feature-body">
        {project.sourceRepo ? (
          <p className="project-repo">{project.sourceRepo.fullName}</p>
        ) : null}
        <h3 className="project-feature-title">
          <Link href={href}>{project.title}</Link>
        </h3>
        {project.summary ? (
          <p className="project-summary">{project.summary}</p>
        ) : null}
        {excerpt ? <p className="project-excerpt">{excerpt}</p> : null}
        <p className="project-links">
          <Link href={href}>{dict.projects.about}</Link>
          {project.sourceRepo ? (
            <a href={project.sourceRepo.htmlUrl} target="_blank" rel="noreferrer">
              {dict.projects.source}
            </a>
          ) : null}
        </p>
      </div>
    </article>
  );
}

function ProjectCard({
  project,
  locale,
  dict,
}: {
  project: PublicProject;
  locale: Locale;
  dict: Dictionary;
}) {
  return (
    <li>
      <Link href={`/${locale}/projects/${project.slug}`} className="card project-card">
        <CoverPlaceholder label={dict.projects.coverPending} />
        <div className="project-card-body">
          {project.sourceRepo ? (
            <p className="project-repo">{project.sourceRepo.fullName}</p>
          ) : null}
          <h3 className="project-card-title">{project.title}</h3>
          {project.summary ? (
            <p className="project-summary">{project.summary}</p>
          ) : null}
        </div>
      </Link>
    </li>
  );
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
      <Link href={`/${locale}/journals/${journal.slug}`} className="journal-row">
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
  const [featured, ...rest] = projects;
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
            <FeaturedProject project={featured} locale={locale} dict={dict} />
            {rest.length > 0 ? (
              <ul className="project-grid">
                {rest.map((project) => (
                  <ProjectCard
                    key={project.slug}
                    project={project}
                    locale={locale}
                    dict={dict}
                  />
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
                  <JournalRow key={journal.slug} journal={journal} locale={locale} />
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
