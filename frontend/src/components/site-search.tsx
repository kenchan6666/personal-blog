"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { PageFrame } from "@/components/page-frame";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import { articleHref } from "@/lib/api";
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

  const results = useMemo(() => {
    if (!q) return [];
    const hits: { href: string; title: string; kind: string; summary: string }[] =
      [];
    for (const article of articles) {
      if (haystack(article.title, article.summary, article.body).includes(q)) {
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
    for (const module of about) {
      if (haystack(module.title, module.body).includes(q)) {
        hits.push({
          href: `/${locale}/about`,
          title: module.title,
          kind: dict.nav.about,
          summary: excerptAround(module.body, q),
        });
      }
    }
    return hits;
  }, [q, query, articles, journals, projects, about, dict, locale]);

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
      {!q ? (
        <p className="mt-6 text-sm text-[var(--text-muted)]">
          {dict.search.emptyQuery}
        </p>
      ) : results.length === 0 ? (
        <p className="mt-6 text-sm text-[var(--text-muted)]">
          {dict.archive.noMatch}
        </p>
      ) : (
        <ul className="mt-6 flex flex-col gap-3">
          {results.map((item, index) => (
            <li key={`${item.href}-${item.title}-${index}`}>
              <Link href={item.href} className="block rounded-xl py-2">
                <p className="text-xs font-semibold tracking-wide text-[var(--text-muted)]">
                  {item.kind}
                </p>
                <p className="display-font text-lg font-bold">{item.title}</p>
                {item.summary ? (
                  <p className="text-sm text-[var(--text-muted)]">
                    {item.summary}
                  </p>
                ) : null}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </PageFrame>
  );
}
