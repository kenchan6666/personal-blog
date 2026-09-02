"use client";

import { useEffect, useState } from "react";
import type { ArticleHeading } from "@/lib/headings";

type Props = {
  headings: ArticleHeading[];
  label: string;
};

export function ArticleToc({ headings, label }: Props) {
  const [active, setActive] = useState(headings[0]?.id ?? "");

  useEffect(() => {
    const nodes = headings
      .map((heading) => document.getElementById(heading.id))
      .filter((node): node is HTMLElement => Boolean(node));
    if (nodes.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        const id = visible[0]?.target.id;
        if (id) setActive(id);
      },
      { rootMargin: "0px 0px -68% 0px", threshold: [0, 1] },
    );

    for (const node of nodes) observer.observe(node);
    return () => observer.disconnect();
  }, [headings]);

  return (
    <nav className="article-toc" aria-label={label}>
      <p className="article-toc-label">{label}</p>
      <ol>
        {headings.map((heading) => (
          <li
            key={heading.id}
            className={heading.level === 3 ? "is-sub" : undefined}
          >
            <a
              href={`#${heading.id}`}
              className={active === heading.id ? "is-active" : undefined}
            >
              {heading.text}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}
