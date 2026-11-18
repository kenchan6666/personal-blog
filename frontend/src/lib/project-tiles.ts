import type { PublicProject } from "@/lib/api";
import { firstMarkdownImage, firstParagraph } from "@/lib/markdown-preview";
import { fetchRepoLanguages } from "@/lib/repo-languages";
import type { ProjectTileData } from "@/components/project-tile";

/** Card data for public projects: cover = first image in the body, if any. */
export async function toProjectTiles(
  projects: PublicProject[],
  locale: string,
  { excerptFor }: { excerptFor?: string } = {},
): Promise<ProjectTileData[]> {
  return Promise.all(
    projects.map(async (project) => ({
      href: `/${locale}/projects/${project.slug}`,
      title: project.title,
      summary: project.summary,
      excerpt:
        excerptFor === project.slug ? firstParagraph(project.body) : undefined,
      repo: project.sourceRepo?.fullName,
      sourceUrl: project.sourceRepo?.htmlUrl,
      cover: firstMarkdownImage(project.body) || undefined,
      languages: await fetchRepoLanguages(project.sourceRepo),
    })),
  );
}
