import { notFound } from "next/navigation";
import { MarkdownBody } from "@/components/markdown-body";
import { PageFrame, PagePanel } from "@/components/page-frame";
import { SourceBrowser } from "@/components/source-browser";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import { fetchPublicProject, fetchPublicSource } from "@/lib/api";

export const dynamic = "force-dynamic";

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
  const source =
    project.sourceRepo && !project.sourceRepo.private
      ? await fetchPublicSource(project.slug)
      : null;

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
        <PagePanel label={copy.source}>
          <SourceBrowser
            slug={project.slug}
            dict={dict}
            sourceRepo={project.sourceRepo}
            initial={source}
          />
        </PagePanel>
      ) : null}
    </PageFrame>
  );
}
