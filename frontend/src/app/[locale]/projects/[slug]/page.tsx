import { Suspense } from "react";
import { notFound } from "next/navigation";
import { MarkdownBody } from "@/components/markdown-body";
import { PageFrame, PagePanel } from "@/components/page-frame";
import { SoftLoader } from "@/components/page-loading";
import { SourceBrowser } from "@/components/source-browser";
import { getDictionary, type Dictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import {
  fetchPublicProject,
  fetchPublicSource,
  type SourceRepo,
} from "@/lib/api";
import { pageMetadata } from "@/lib/seo";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale: raw, slug } = await params;
  if (!isLocale(raw)) return {};
  const locale = raw as Locale;
  const project = await fetchPublicProject(locale, slug);
  if (!project) return {};
  return pageMetadata({
    locale,
    title: project.title,
    description: project.summary,
    path: `/projects/${project.slug}`,
    markdown: project.body,
  });
}

function SourceFallback({ label }: { label: string }) {
  return (
    <div className="source-loading">
      <SoftLoader label={label} />
      <p>{label}</p>
    </div>
  );
}

async function ProjectSource({
  slug,
  dict,
  sourceRepo,
}: {
  slug: string;
  dict: Dictionary;
  sourceRepo: SourceRepo;
}) {
  const source = await fetchPublicSource(slug);
  return (
    <PagePanel label={dict.projects.source}>
      <SourceBrowser
        slug={slug}
        dict={dict}
        sourceRepo={sourceRepo}
        initial={source}
      />
    </PagePanel>
  );
}

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale: raw, slug } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw as Locale;
  const dict = getDictionary(locale);
  const copy = dict.projects;
  const project = await fetchPublicProject(locale, slug);
  if (!project) notFound();

  return (
    <PageFrame
      title={project.title}
      lead={project.summary}
      back={{ href: `/${locale}/projects`, label: dict.nav.projects }}
    >
      {project.body ? (
        <PagePanel label={copy.about}>
          <MarkdownBody source={project.body} />
        </PagePanel>
      ) : null}
      {project.sourceRepo?.private ? (
        <PagePanel label={copy.source}>
          <p className="text-[var(--text-muted)]">{copy.privateHint}</p>
          <p className="mt-3">
            <a
              href={project.sourceRepo.htmlUrl}
              className="text-[var(--accent-link)] hover:underline"
              rel="noreferrer"
              target="_blank"
            >
              {project.sourceRepo.fullName}
            </a>
          </p>
        </PagePanel>
      ) : null}
      {project.sourceRepo && !project.sourceRepo.private ? (
        <Suspense
          fallback={
            <PagePanel label={copy.source}>
              <SourceFallback label={copy.sourceLoading} />
            </PagePanel>
          }
        >
          <ProjectSource
            slug={project.slug}
            dict={dict}
            sourceRepo={project.sourceRepo}
          />
        </Suspense>
      ) : null}
    </PageFrame>
  );
}
