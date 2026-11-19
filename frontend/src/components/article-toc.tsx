"use client";

import { useEffect, useState } from "react";
import type { ArticleHeading } from "@/lib/headings";
import { useCollapseMotion } from "@/lib/use-collapse-motion";

type Props = {
  headings: ArticleHeading[];
  label: string;
};

type ListProps = {
  headings: ArticleHeading[];
  active: string;
  onPick?: () => void;
};

// Top level (not declared inside ArticleToc): a component defined during
// render is a new type every render, so React remounted both lists on each
// open/close and the items lost their fade-out mid-transition.
function HeadingList({ headings, active, onPick }: ListProps) {
  return (
    <ol>
      {headings.map((heading) => (
        <li key={heading.id} className={heading.level === 3 ? "is-sub" : undefined}>
          <a
            href={`#${heading.id}`}
            className={active === heading.id ? "is-active" : undefined}
            onClick={onPick}
          >
            {heading.text}
          </a>
        </li>
      ))}
    </ol>
  );
}

export function ArticleToc({ headings, label }: Props) {
  const [active, setActive] = useState(headings[0]?.id ?? "");
  const [open, setOpen] = useState(false);
  const { ref, skipNextAnimation } = useCollapseMotion<HTMLDivElement>(open);

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

  // Picking a heading jumps below the list: fold it at once so the page
  // above the target doesn't shrink during the jump and land it off-target.
  function pick() {
    skipNextAnimation();
    setOpen(false);
  }

  return (
    <div className="article-toc-slot">
      <nav className="article-toc-mobile" aria-label={label}>
        <button
          type="button"
          className="article-toc-mobile-toggle"
          aria-expanded={open}
          aria-controls="article-toc-mobile-list"
          onClick={() => setOpen((value) => !value)}
        >
          <span>{label}</span>
          <span className="chevron" aria-hidden />
        </button>
        <div
          id="article-toc-mobile-list"
          ref={ref}
          data-motion=""
          className={`disclosure${open ? " is-open" : ""}`}
          inert={!open}
        >
          <div className="disclosure-inner">
            <HeadingList headings={headings} active={active} onPick={pick} />
          </div>
        </div>
      </nav>
      <nav className="article-toc" aria-label={label}>
        <p className="article-toc-label">{label}</p>
        <HeadingList headings={headings} active={active} />
      </nav>
    </div>
  );
}
