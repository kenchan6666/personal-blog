"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ProjectTile, type ProjectTileData } from "@/components/project-tile";

export type ArchiveItem = {
  href: string;
  title: string;
  summary: string;
  meta?: string;
  tags: string[];
  /** When set, the item renders as a project card instead of a plain entry. */
  project?: ProjectTileData;
};

export type ArchiveFilter = {
  id: string;
  label: string;
};

type Labels = {
  search: string;
  all: string;
  results: string;
  empty: string;
  noMatch: string;
};

type Props = {
  items: ArchiveItem[];
  /** Label for the external source link on project cards. */
  sourceLabel?: string;
  filters: ArchiveFilter[];
  searchPlaceholder: string;
  labels: Labels;
};

function formatResults(template: string, n: number) {
  return template.replace("{n}", String(n));
}

export function ArchiveIndex({
  items,
  filters,
  searchPlaceholder,
  labels,
  sourceLabel = "",
}: Props) {
  const [query, setQuery] = useState("");
  const [active, setActive] = useState("all");

  const visibleFilters = useMemo(
    () =>
      filters.filter((filter) =>
        items.some((item) => item.tags.includes(filter.id)),
      ),
    [filters, items],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter((item) => {
      if (active !== "all" && !item.tags.includes(active)) return false;
      if (!q) return true;
      return (
        item.title.toLowerCase().includes(q) ||
        item.summary.toLowerCase().includes(q) ||
        (item.meta ?? "").toLowerCase().includes(q)
      );
    });
  }, [items, query, active]);

  if (items.length === 0) {
    return (
      <div className="archive-empty glass">
        <p>{labels.empty}</p>
      </div>
    );
  }

  return (
    <div className="archive">
      <div className="archive-toolbar">
        <input
          className="field archive-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={searchPlaceholder}
          type="search"
          aria-label={labels.search}
        />
        <p className="archive-count">
          {formatResults(labels.results, filtered.length)}
        </p>
      </div>
      {visibleFilters.length > 0 ? (
        <div className="archive-filters" role="group" aria-label={labels.all}>
          <button
            type="button"
            className={`archive-chip${active === "all" ? " is-active" : ""}`}
            aria-pressed={active === "all"}
            onClick={() => setActive("all")}
          >
            {labels.all}
          </button>
          {visibleFilters.map((filter) => (
            <button
              key={filter.id}
              type="button"
              className={`archive-chip${active === filter.id ? " is-active" : ""}`}
              aria-pressed={active === filter.id}
              onClick={() => setActive(filter.id)}
            >
              {filter.label}
            </button>
          ))}
        </div>
      ) : null}
      {filtered.length === 0 ? (
        <div className="archive-empty glass">
          <p>{labels.noMatch}</p>
        </div>
      ) : (
        <ul
          className={
            filtered.some((item) => item.project)
              ? "project-grid project-grid-archive"
              : "entry-grid"
          }
        >
          {filtered.map((item) =>
            item.project ? (
              <li key={item.href}>
                <ProjectTile
                  project={item.project}
                  sourceLabel={sourceLabel}
                  headingLevel="h2"
                />
              </li>
            ) : (
              <li key={item.href}>
                <Link href={item.href} className="glass glass-hover entry-card">
                  {item.meta ? (
                    <p className="entry-card-meta">{item.meta}</p>
                  ) : null}
                  <h2 className="display-font entry-card-title">
                    {item.title}
                  </h2>
                  {item.summary ? (
                    <p className="entry-card-summary">{item.summary}</p>
                  ) : null}
                </Link>
              </li>
            ),
          )}
        </ul>
      )}
    </div>
  );
}
