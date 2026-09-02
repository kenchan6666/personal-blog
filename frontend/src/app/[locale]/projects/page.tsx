import { notFound } from "next/navigation";
import { ArchiveIndex } from "@/components/archive-index";
import { PageFrame } from "@/components/page-frame";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import { fetchPublicProjects } from "@/lib/api";
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
    title: dict.nav.projects,
    path: "/projects",
  });
}

export default async function ProjectsPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale: raw } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw as Locale;
  const dict = getDictionary(locale);
  const projects = await fetchPublicProjects(locale);

  return (
    <PageFrame title={dict.nav.projects}>
      <ArchiveIndex
        searchPlaceholder={`${dict.archive.search} ${dict.nav.projects}`}
        labels={{
          search: dict.archive.search,
          all: dict.archive.all,
          results: dict.archive.results,
          empty: dict.projects.empty,
          noMatch: dict.archive.noMatch,
        }}
        filters={[
          { id: "source", label: dict.archive.withSource },
          { id: "public", label: dict.archive.publicRepo },
          { id: "private", label: dict.archive.privateRepo },
        ]}
        items={projects.map((project) => {
          const tags: string[] = [];
          if (project.sourceRepo) {
            tags.push("source");
            tags.push(project.sourceRepo.private ? "private" : "public");
          }
          return {
            href: `/${locale}/projects/${project.slug}`,
            title: project.title,
            summary: project.summary,
            meta: project.sourceRepo?.fullName,
            tags,
          };
        })}
      />
    </PageFrame>
  );
}
