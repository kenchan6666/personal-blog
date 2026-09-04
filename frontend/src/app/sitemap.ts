import type { MetadataRoute } from "next";
import { locales } from "@/i18n/config";
import {
  articleHref,
  fetchPublicArticles,
  fetchPublicJournals,
  fetchPublicProjects,
  fetchPublicResumes,
} from "@/lib/api";
import { pathWithoutLocale, siteOrigin } from "@/lib/seo";

export const dynamic = "force-dynamic";

const STATIC_PATHS = [
  "",
  "/about",
  "/resume",
  "/articles",
  "/journals",
  "/projects",
  "/search",
];

async function safeList<T>(load: () => Promise<T[]>): Promise<T[]> {
  try {
    return await load();
  } catch {
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const origin = siteOrigin();
  const [articles, journals, projects, resumes] = await Promise.all([
    safeList(() => fetchPublicArticles("zh-Hant")),
    safeList(() => fetchPublicJournals("zh-Hant")),
    safeList(() => fetchPublicProjects("zh-Hant")),
    safeList(() => fetchPublicResumes()),
  ]);

  const paths = [
    ...STATIC_PATHS,
    ...articles.map((article) =>
      pathWithoutLocale("zh-Hant", articleHref("zh-Hant", article)),
    ),
    ...journals.map((journal) => `/journals/${journal.slug}`),
    ...projects.map((project) => `/projects/${project.slug}`),
    ...resumes.map((resume) => `/resume/${resume.slug}`),
  ];

  return paths.flatMap((path) =>
    locales.map((locale) => ({
      url: `${origin}/${locale}${path}`,
      alternates: {
        languages: Object.fromEntries(
          locales.map((item) => [item, `${origin}/${item}${path}`]),
        ),
      },
    })),
  );
}
