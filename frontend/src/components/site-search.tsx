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
      if (
        article.title.toLowerCase().includes(q) ||
        article.summary.toLowerCase().includes(q)
      ) {
        hits.push({
          href: articleHref(locale, article),
          title: article.title,
          kind: dict.nav.articles,
          summary: article.summary,
        });
      }
    }
    for (const journal of journals) {
      if (
        journal.title.toLowerCase().includes(q) ||
        journal.summary.toLowerCase().includes(q)
      ) {
        hits.push({
          href: `/${locale}/journals/${journal.slug}`,
          title: journal.title,
          kind: dict.nav.journals,
          summary: journal.summary,
        });
      }
    }
    for (const project of projects) {
      if (
        project.title.toLowerCase().includes(q) ||
        project.summary.toLowerCase().includes(q)
      ) {
        hits.push({
          href: `/${locale}/projects/${project.slug}`,
          title: project.title,
          kind: dict.nav.projects,
          summary: project.summary,
        });
      }
    }
    for (const module of about) {
      if (
        module.title.toLowerCase().includes(q) ||
        module.body.toLowerCase().includes(q)
      ) {
        hits.push({
          href: `/${locale}/about`,
          title: module.title,
          kind: dict.nav.about,
          summary: module.body.replace(/[#>*_`]/g, "").slice(0, 120),
        });
      }
    }
    return hits;
  }, [q, articles, journals, projects, about, dict, locale]);

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
