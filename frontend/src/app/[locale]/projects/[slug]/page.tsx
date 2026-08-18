import Link from "next/link";
import { notFound } from "next/navigation";
import { MarkdownBody } from "@/components/markdown-body";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import { fetchPublicProject } from "@/lib/api";

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale: raw, slug } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw as Locale;
  const dict = getDictionary(locale);
  const project = await fetchPublicProject(locale, slug);
  if (!project) notFound();

  return (
    <article className="px-6 py-24 sm:px-10 lg:px-14">
      <Link
        href={`/${locale}/projects`}
        className="text-sm text-[var(--accent-link)] hover:underline"
      >
        ← {dict.nav.projects}
      </Link>
      <h1 className="display-font mt-6 max-w-3xl text-4xl font-bold tracking-tight">
        {project.title}
      </h1>
      {project.summary ? (
        <p className="mt-4 max-w-[70ch] text-lg text-[var(--text-muted)]">
          {project.summary}
        </p>
      ) : null}
      <div className="mt-10">
        <MarkdownBody source={project.body} />
      </div>
    </article>
  );
}
