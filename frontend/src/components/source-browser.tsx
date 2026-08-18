"use client";

import { useEffect, useState } from "react";
import type { Dictionary } from "@/i18n/dictionaries";
import {
  fetchPublicSource,
  fetchPublicSourceBlob,
  fetchPublicSourceTree,
  type PublicSourceOverview,
  type SourceTreeEntry,
} from "@/lib/api";
import { MarkdownBody } from "./markdown-body";

type Props = {
  slug: string;
  dict: Dictionary;
};

export function SourceBrowser({ slug, dict }: Props) {
  const labels = dict.projects;
  const [overview, setOverview] = useState<PublicSourceOverview | null>(null);
  const [ref, setRef] = useState("");
  const [tree, setTree] = useState<SourceTreeEntry[]>([]);
  const [dir, setDir] = useState("");
  const [blob, setBlob] = useState<{ path: string; content: string } | null>(
    null,
  );

  useEffect(() => {
    void fetchPublicSource(slug, ref || undefined).then((data) => {
      if (!data) {
        setOverview(null);
        return;
      }
      setOverview(data);
      setTree(data.tree);
      setDir("");
      setBlob(null);
      if (!ref) setRef(data.ref);
    });
  }, [slug, ref]);

  async function openEntry(entry: SourceTreeEntry) {
    if (!overview) return;
    if (entry.type === "dir") {
      const next = await fetchPublicSourceTree(slug, overview.ref, entry.path);
      setDir(entry.path);
      setTree(next);
      setBlob(null);
      return;
    }
    const file = await fetchPublicSourceBlob(slug, overview.ref, entry.path);
    setBlob(file);
  }

  async function goRoot() {
    if (!overview) return;
    const data = await fetchPublicSource(slug, overview.ref);
    if (!data) return;
    setDir("");
    setTree(data.tree);
    setBlob(null);
  }

  if (!overview) return null;

  return (
    <section className="glass mt-12 rounded-[var(--radius-panel)] p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="display-font text-lg font-bold">{labels.sourceBrowser}</h2>
        <label className="text-xs text-[var(--text-muted)]">
          {labels.branch}
          <select
            className="ml-2 rounded-[var(--radius-card)] border border-white/15 bg-white/5 px-2 py-1 font-mono text-sm text-white"
            value={overview.ref}
            onChange={(e) => setRef(e.target.value)}
          >
            {overview.branches.map((branch) => (
              <option key={branch} value={branch}>
                {branch}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="mb-3 text-xs text-[var(--text-muted)]">
        <button type="button" className="hover:text-white" onClick={goRoot}>
          /
        </button>
        {dir ? <span className="font-mono"> {dir}</span> : null}
      </div>

      <ul className="mb-6 divide-y divide-white/10 font-mono text-sm">
        {tree.map((entry) => (
          <li key={entry.path}>
            <button
              type="button"
              className="w-full px-1 py-2 text-left hover:text-[var(--accent-link)]"
              onClick={() => void openEntry(entry)}
            >
              {entry.type === "dir" ? `${labels.dir} ` : `${labels.file} `}
              {entry.name}
            </button>
          </li>
        ))}
      </ul>

      {blob ? (
        <pre className="overflow-x-auto rounded-[var(--radius-card)] bg-black/30 p-4 font-mono text-sm leading-relaxed">
          {blob.content}
        </pre>
      ) : overview.readme.content ? (
        <div>
          <p className="mb-2 font-mono text-xs text-[var(--text-muted)]">
            {overview.readme.path}
          </p>
          <MarkdownBody source={overview.readme.content} />
        </div>
      ) : null}
    </section>
  );
}
