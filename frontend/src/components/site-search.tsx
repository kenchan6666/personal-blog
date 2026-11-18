"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { PageFrame } from "@/components/page-frame";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import { articleHref, searchPublic, type PublicSearchHit } from "@/lib/api";
import type { PublicAboutModule, PublicArticle, PublicJournal, PublicProject } from "@/lib/api";

type Props = {
  locale: Locale;
  dict: Dictionary;
  articles: PublicArticle[];
  journals: PublicJournal[];
  projects: PublicProject[];
  about: PublicAboutModule[];
};

function excerptAround(text: string, query: string, size = 120): string {
  const plain = text.replace(/[#>*_`[\]]/g, " ").replace(/\s+/g, " ").trim();
  const lower = plain.toLowerCase();
  const index = lower.indexOf(query);
  if (index < 0) return plain.slice(0, size);
  const start = Math.max(0, index - 32);
  const chunk = plain.slice(start, start + size);
  return `${start > 0 ? "…" : ""}${chunk}${start + size < plain.length ? "…" : ""}`;
}

function haystack(...parts: Array<string | undefined>) {
  return parts.filter(Boolean).join("\n").toLowerCase();
}

export function SiteSearch({
  locale,
  dict,
  articles,
  journals,
  projects,
  about,
}: Props) {
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();
  // Server search matches every locale and both Chinese scripts; the local
  // filter below is only a fallback if the API is unreachable.
  const [remote, setRemote] = useState<{ q: string; hits: PublicSearchHit[] } | null>(null);
  const [remoteFailed, setRemoteFailed] = useState(false);

  useEffect(() => {
    const term = query.trim();
    if (!term) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      searchPublic(locale, term, controller.signal)
        .then((hits) => {
          setRemote({ q: term, hits });
          setRemoteFailed(false);
        })
        .catch((error: unknown) => {
          if ((error as Error)?.name !== "AbortError") setRemoteFailed(true);
        });
    }, 160);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [query, locale]);

  const kindLabel: Record<PublicSearchHit["kind"], string> = {
    article: dict.nav.articles,
    journal: dict.nav.journals,
    project: dict.nav.projects,
    about: dict.nav.about,
  };
  const remoteHits =
    remote && remote.q.toLowerCase() === q
      ? remote.hits.map((hit) => ({
          href:
            hit.kind === "article"
              ? articleHref(locale, hit)
              : hit.kind === "journal"
                ? `/${locale}/journals/${hit.slug}`
                : hit.kind === "project"
                  ? `/${locale}/projects/${hit.slug}`
                  : `/${locale}/about#${hit.slug}`,
          title: hit.title,
          kind: hit.categoryTitle
            ? `${kindLabel[hit.kind]} · ${hit.categoryTitle}`
            : kindLabel[hit.kind],
          summary: hit.summary,
        }))
      : null;

  const localResults = useMemo(() => {
    if (!q) return [];
    const hits: { href: string; title: string; kind: string; summary: string }[] =
      [];
    for (const article of articles) {
      if (haystack(article.title, article.summary, article.body, article.categoryTitle, article.categorySlug).includes(q)) {
        hits.push({
          href: articleHref(locale, article),
          title: article.title,
          kind: dict.nav.articles,
          summary: excerptAround(
            article.summary.includes(query.trim()) || article.title.toLowerCase().includes(q)
              ? article.summary || article.body
              : article.body || article.summary,
            q,
          ),
        });
      }
    }
    for (const journal of journals) {
      if (haystack(journal.title, journal.summary, journal.body).includes(q)) {
        hits.push({
          href: `/${locale}/journals/${journal.slug}`,
          title: journal.title,
          kind: dict.nav.journals,
          summary: excerptAround(
            journal.summary.toLowerCase().includes(q) || journal.title.toLowerCase().includes(q)
              ? journal.summary || journal.body
              : journal.body || journal.summary,
            q,
          ),
        });
      }
    }
    for (const project of projects) {
      if (haystack(project.title, project.summary, project.body).includes(q)) {
        hits.push({
          href: `/${locale}/projects/${project.slug}`,
          title: project.title,
          kind: dict.nav.projects,
          summary: excerptAround(
            project.summary.toLowerCase().includes(q) || project.title.toLowerCase().includes(q)
              ? project.summary || project.body
              : project.body || project.summary,
            q,
          ),
        });
      }
    }
    for (const entry of about) {
      if (haystack(entry.title, entry.body).includes(q)) {
        hits.push({
          href: `/${locale}/about#${entry.slug}`,
          title: entry.title,
          kind: dict.nav.about,
          summary: excerptAround(entry.body, q),
        });
      }
    }
    return hits;
  }, [q, query, articles, journals, projects, about, dict, locale]);
  const results = remoteHits ?? (remoteFailed || !remote ? localResults : []);

  return (
    <PageFrame title={dict.search.title} narrow>
      <input
        className="field"
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={dict.search.placeholder}
        aria-label={dict.nav.search}
        autoFocus
      />
      <p className="sr-only" aria-live="polite">
        {q ? `${results.length}` : ""}
      </p>
      {!q ? (
        <p className="mt-6 text-sm text-[var(--text-muted)]">
          {dict.search.emptyQuery}
        </p>
      ) : results.length === 0 ? (
        <p className="mt-6 text-sm text-[var(--text-muted)]">
          {dict.archive.noMatch}
        </p>
      ) : (
        <ul className="search-results">
          {results.map((item, index) => (
            <li key={`${item.href}-${item.title}-${index}`}>
              <Link href={item.href} className="search-hit">
                <p className="search-hit-kind">{item.kind}</p>
                <p className="search-hit-title display-font">{item.title}</p>
                {item.summary ? (
                  <p className="search-hit-summary">{item.summary}</p>
                ) : null}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </PageFrame>
  );
}
