"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { Locale } from "@/i18n/config";
import {
  formatCompactDate,
  formatCount,
  formatPostDate,
  monthLabel,
  parsePostDate,
} from "@/lib/post-meta";

export type TimelinePost = {
  href: string;
  title: string;
  summary: string;
  publishedAt: string;
  wordCount: number;
  readingMinutes: number;
  project?: { slug: string; title: string };
};

type Labels = {
  search: string;
  empty: string;
  noMatch: string;
  minutes: string;
  words: string;
};

export type ArchiveChrome = {
  all: string;
  count: string;
  newest: string;
  oldest: string;
  longest: string;
  related: string;
};

type YearGroup = {
  year: number;
  count: number;
  months: {
    key: string;
    label: string;
    count: number;
    posts: TimelinePost[];
  }[];
};

type SortKey = "newest" | "oldest" | "longest";

function groupPosts(
  posts: TimelinePost[],
  locale: Locale,
  oldestFirst: boolean,
): YearGroup[] {
  const years = new Map<number, Map<string, TimelinePost[]>>();
  for (const post of posts) {
    const date = parsePostDate(post.publishedAt);
    const year = date.getFullYear();
    const month = date.getMonth();
    const key = `${year}-${month}`;
    if (!years.has(year)) years.set(year, new Map());
    const months = years.get(year)!;
    if (!months.has(key)) months.set(key, []);
    months.get(key)!.push(post);
  }
  return [...years.entries()]
    .sort(([a], [b]) => (oldestFirst ? a - b : b - a))
    .map(([year, months]) => {
      const monthGroups = [...months.entries()]
        .sort(([a], [b]) => {
          const left = Number(a.split("-")[1]);
          const right = Number(b.split("-")[1]);
          return oldestFirst ? left - right : right - left;
        })
        .map(([key, monthPosts]) => ({
          key,
          label: monthLabel(monthPosts[0].publishedAt, locale),
          count: monthPosts.length,
          posts: [...monthPosts].sort((a, b) => {
            const delta =
              parsePostDate(a.publishedAt).getTime() -
              parsePostDate(b.publishedAt).getTime();
            return oldestFirst ? delta : -delta;
          }),
        }));
      return {
        year,
        count: monthGroups.reduce((sum, item) => sum + item.count, 0),
        months: monthGroups,
      };
    });
}

type Props = {
  locale: Locale;
  posts: TimelinePost[];
  searchPlaceholder: string;
  labels: Labels;
  chrome?: ArchiveChrome;
};

export function PostArchive({
  locale,
  posts,
  searchPlaceholder,
  labels,
  chrome,
}: Props) {
  const [query, setQuery] = useState("");
  const [year, setYear] = useState("all");
  const [project, setProject] = useState("all");
  const [sort, setSort] = useState<SortKey>("newest");

  const years = useMemo(() => {
    const counts = new Map<number, number>();
    for (const post of posts) {
      const value = parsePostDate(post.publishedAt).getFullYear();
      counts.set(value, (counts.get(value) ?? 0) + 1);
    }
    return [...counts.entries()].sort(([a], [b]) => b - a);
  }, [posts]);

  const projects = useMemo(() => {
    const seen = new Map<string, { slug: string; title: string; count: number }>();
    for (const post of posts) {
      if (!post.project) continue;
      const current = seen.get(post.project.slug);
      if (current) current.count += 1;
      else seen.set(post.project.slug, { ...post.project, count: 1 });
    }
    return [...seen.values()].sort((a, b) => a.title.localeCompare(b.title, locale));
  }, [posts, locale]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return posts.filter((post) => {
      if (year !== "all" && String(parsePostDate(post.publishedAt).getFullYear()) !== year) {
        return false;
      }
      if (project !== "all" && post.project?.slug !== project) return false;
      if (!q) return true;
      return (
        post.title.toLowerCase().includes(q) ||
        post.summary.toLowerCase().includes(q) ||
        (post.project?.title.toLowerCase().includes(q) ?? false)
      );
    });
  }, [posts, query, year, project]);

  const ranked = useMemo(() => {
    const next = [...filtered];
    if (sort === "longest") {
      next.sort((a, b) => b.wordCount - a.wordCount || b.readingMinutes - a.readingMinutes);
    }
    return next;
  }, [filtered, sort]);

  const groups = useMemo(
    () => groupPosts(ranked, locale, sort === "oldest"),
    [ranked, locale, sort],
  );

  const totalWords = posts.reduce((sum, post) => sum + post.wordCount, 0);
  const browsing = Boolean(query.trim() || year !== "all" || project !== "all" || sort !== "newest");

  if (posts.length === 0) {
    return <p className="post-archive-empty">{labels.empty}</p>;
  }

  return (
    <div className="post-archive">
      {chrome ? (
        <div className="post-archive-chrome">
          <p className="post-archive-stats">
            {formatCount(chrome.count, browsing ? filtered.length : posts.length)}
            {" · "}
            {formatCount(labels.words, browsing ? ranked.reduce((sum, post) => sum + post.wordCount, 0) : totalWords)}
          </p>
          <div className="post-archive-toolbar">
            <input
              className="field field-tight post-archive-search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={searchPlaceholder}
              type="search"
              aria-label={labels.search}
            />
            <div className="segment" role="group" aria-label={chrome.newest}>
              {(
                [
                  ["newest", chrome.newest],
                  ["oldest", chrome.oldest],
                  ["longest", chrome.longest],
                ] as const
              ).map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  className={sort === key ? "segment-active" : undefined}
                  onClick={() => setSort(key)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          {years.length > 0 || projects.length > 0 ? (
            <div className="post-archive-filters">
              {years.length > 0 ? (
                <div className="post-archive-chips" role="tablist" aria-label={chrome.all}>
                  <button
                    type="button"
                    className={`post-archive-chip${year === "all" ? " is-active" : ""}`}
                    onClick={() => setYear("all")}
                  >
                    {chrome.all}
                    <span>{posts.length}</span>
                  </button>
                  {years.map(([value, count]) => (
                    <button
                      key={value}
                      type="button"
                      className={`post-archive-chip${year === String(value) ? " is-active" : ""}`}
                      onClick={() => setYear(String(value))}
                    >
                      {value}
                      <span>{count}</span>
                    </button>
                  ))}
                </div>
              ) : null}
              {projects.length > 0 ? (
                <div className="post-archive-chips" role="tablist" aria-label={chrome.related}>
                  <button
                    type="button"
                    className={`post-archive-chip${project === "all" ? " is-active" : ""}`}
                    onClick={() => setProject("all")}
                  >
                    {chrome.related}
                  </button>
                  {projects.map((item) => (
                    <button
                      key={item.slug}
                      type="button"
                      className={`post-archive-chip${project === item.slug ? " is-active" : ""}`}
                      onClick={() => setProject(item.slug)}
                    >
                      {item.title}
                      <span>{item.count}</span>
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : (
        <div className="post-archive-search-wrap">
          <input
            className="field field-tight post-archive-search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={searchPlaceholder}
            type="search"
            aria-label={labels.search}
          />
        </div>
      )}
      {ranked.length === 0 ? (
        <p className="post-archive-empty">{labels.noMatch}</p>
      ) : sort === "longest" ? (
        <ul className="post-list">
          {ranked.map((post) => (
            <PostRow key={post.href} post={post} labels={labels} />
          ))}
        </ul>
      ) : (
        groups.map((group) => (
          <section key={group.year} className="post-year">
            <h2 className="post-year-title">
              {group.year}
              <span>{group.count}</span>
            </h2>
            {group.months.map((month) => (
              <section key={month.key} className="post-month">
                <h3 className="post-month-title">
                  {month.label}
                  <span>{month.count}</span>
                </h3>
                <ul className="post-list">
                  {month.posts.map((post) => (
                    <PostRow key={post.href} post={post} labels={labels} />
                  ))}
                </ul>
              </section>
            ))}
          </section>
        ))
      )}
    </div>
  );
}

function PostRow({
  post,
  labels,
}: {
  post: TimelinePost;
  labels: Labels;
}) {
  return (
    <li>
      <Link href={post.href} className="post-item">
        <time className="post-item-date" dateTime={post.publishedAt}>
          {formatCompactDate(post.publishedAt)}
        </time>
        <div className="post-item-copy">
          <h4 className="post-item-title display-font">{post.title}</h4>
          <p className="post-item-meta">
            {formatCount(labels.minutes, post.readingMinutes)}
            {" · "}
            {formatCount(labels.words, post.wordCount)}
            {post.project ? ` · ${post.project.title}` : ""}
          </p>
          {post.summary ? <p className="post-item-summary">{post.summary}</p> : null}
        </div>
      </Link>
    </li>
  );
}

export function PostMetaLine({
  locale,
  publishedAt,
  readingMinutes,
  wordCount,
  labels,
}: {
  locale: Locale;
  publishedAt: string;
  readingMinutes: number;
  wordCount: number;
  labels: { minutes: string; words: string };
}) {
  return (
    <p className="post-item-meta">
      {formatPostDate(publishedAt, locale)}
      {" · "}
      {formatCount(labels.minutes, readingMinutes)}
      {" · "}
      {formatCount(labels.words, wordCount)}
    </p>
  );
}
