import Link from "next/link";
import { notFound } from "next/navigation";
import { Hero } from "@/components/hero";
import { ProfileSection } from "@/components/profile-section";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import { fetchPublicProjects, fetchPublicSite } from "@/lib/api";
import { mergeHeroContent, mergeProfileContent } from "@/lib/site-content";

export const dynamic = "force-dynamic";

export default async function HomePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale: raw } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw as Locale;
  const dict = getDictionary(locale);
  const [site, projects] = await Promise.all([
    fetchPublicSite(locale),
    fetchPublicProjects(locale),
  ]);

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
      {projects.length > 0 ? (
        <section className="hairline-t px-5 py-14 sm:px-10 sm:py-16 lg:px-14">
          <div className="mx-auto max-w-3xl">
            <h2 className="page-title display-font">{dict.nav.projects}</h2>
            <ul className="entry-grid">
              {projects.map((project) => (
                <li key={project.slug}>
                  <Link
                    href={`/${locale}/projects/${project.slug}`}
                    className="glass glass-hover entry-card"
                  >
                    {project.sourceRepo ? (
                      <p className="entry-card-meta">
                        {project.sourceRepo.fullName}
                      </p>
                    ) : null}
                    <h3 className="display-font entry-card-title">
                      {project.title}
                    </h3>
                    {project.summary ? (
                      <p className="entry-card-summary">{project.summary}</p>
                    ) : null}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </section>
      ) : null}
    </>
  );
}
