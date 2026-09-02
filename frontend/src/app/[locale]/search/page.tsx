import { notFound } from "next/navigation";
import { SiteSearch } from "@/components/site-search";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import {
  fetchPublicArticles,
  fetchPublicJournals,
  fetchPublicProjects,
  fetchPublicAbout,
} from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function SearchPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale: raw } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw as Locale;
  const dict = getDictionary(locale);
  const [articles, journals, projects, about] = await Promise.all([
    fetchPublicArticles(locale),
    fetchPublicJournals(locale),
    fetchPublicProjects(locale),
    fetchPublicAbout(locale),
  ]);

  return (
    <SiteSearch
      locale={locale}
      dict={dict}
      articles={articles}
      journals={journals}
      projects={projects}
      about={about}
    />
  );
}
