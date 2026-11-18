import Link from "next/link";
import type { LanguageShare } from "@/lib/repo-languages";

export type ProjectTileData = {
  href: string;
  title: string;
  summary: string;
  excerpt?: string;
  repo?: string;
  sourceUrl?: string;
  cover?: string;
  languages: LanguageShare[];
};

type Props = {
  project: ProjectTileData;
  variant?: "feature" | "grid";
  sourceLabel: string;
  aboutLabel?: string;
  headingLevel?: "h2" | "h3";
};

function percent(share: number) {
  return `${Math.max(1, Math.round(share * 100))}%`;
}

/**
 * Project card. With a cover image it shows the image; without one it is a
 * purely typographic card (title, description, language chips and bar) instead
 * of an empty placeholder box. Chips and bar only render when data exists.
 */
export function ProjectTile({
  project,
  variant = "grid",
  sourceLabel,
  aboutLabel,
  headingLevel = "h3",
}: Props) {
  const Heading = headingLevel;
  const chips = project.languages.filter((l) => l.share >= 0.02).slice(0, 4);
  const bar = project.languages.filter((l) => l.share >= 0.005);
  const barLabel = bar.map((l) => `${l.name} ${percent(l.share)}`).join(" · ");
  const className = [
    "card",
    "project-tile",
    `project-tile-${variant}`,
    project.cover ? "has-cover" : "is-typographic",
  ].join(" ");

  return (
    <article className={className}>
      {project.cover ? (
        <div className="project-tile-cover" aria-hidden>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={project.cover} alt="" loading="lazy" decoding="async" />
        </div>
      ) : null}
      <div className="project-tile-body">
        {project.repo ? <p className="project-repo">{project.repo}</p> : null}
        <Heading className="project-tile-title">
          <Link href={project.href} className="project-tile-link">
            {project.title}
          </Link>
        </Heading>
        {project.summary ? (
          <p className="project-summary">{project.summary}</p>
        ) : null}
        {project.excerpt ? (
          <p className="project-excerpt">{project.excerpt}</p>
        ) : null}
        {chips.length > 0 ? (
          <ul className="project-chips">
            {chips.map((lang) => (
              <li key={lang.name} className="project-chip">
                <span
                  className="project-chip-dot"
                  style={{ background: lang.color }}
                  aria-hidden
                />
                {lang.name}
              </li>
            ))}
          </ul>
        ) : null}
        {bar.length > 0 ? (
          <div
            className="project-langbar"
            role="img"
            aria-label={barLabel}
            title={barLabel}
          >
            {bar.map((lang) => (
              <span
                key={lang.name}
                style={{ flexGrow: lang.share, background: lang.color }}
              />
            ))}
          </div>
        ) : null}
        {aboutLabel || project.sourceUrl ? (
          <p className="project-links">
            {aboutLabel ? <Link href={project.href}>{aboutLabel}</Link> : null}
            {project.sourceUrl ? (
              <a href={project.sourceUrl} target="_blank" rel="noreferrer">
                {sourceLabel} <span aria-hidden>↗</span>
              </a>
            ) : null}
          </p>
        ) : null}
      </div>
    </article>
  );
}
