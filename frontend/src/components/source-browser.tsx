"use client";

import { useEffect, useRef, useState } from "react";
import type { Dictionary } from "@/i18n/dictionaries";
import type { SourceRepo } from "@/lib/api";
import {
  fetchPublicSource,
  fetchPublicSourceBlob,
  fetchPublicSourceTree,
  type PublicSourceOverview,
  type SourceTreeEntry,
} from "@/lib/api";
import { githubBlobUrl, parentPath } from "@/lib/repo-path";
import { isMarkdownPath, sourceLanguage } from "@/lib/source-lang";
import { GithubMarkdown } from "./github-markdown";
import { SoftLoader } from "./page-loading";
import { SourceCode } from "./source-code";

type Props = {
  slug: string;
  dict: Dictionary;
  sourceRepo: SourceRepo;
  initial?: PublicSourceOverview | null;
};

function FileIcon({ dir }: { dir: boolean }) {
  return dir ? (
    <svg viewBox="0 0 16 16" className="gh-icon is-dir" aria-hidden>
      <path
        fill="currentColor"
        d="M1.75 2.5A.75.75 0 0 1 2.5 1.75h4.19c.2 0 .39.08.53.22L8.72 3.5h4.78a.75.75 0 0 1 .75.75v8.5a.75.75 0 0 1-.75.75H2.5a.75.75 0 0 1-.75-.75Z"
      />
    </svg>
  ) : (
    <svg viewBox="0 0 16 16" className="gh-icon" aria-hidden>
      <path
        fill="currentColor"
        d="M2 1.75C2 .784 2.784 0 3.75 0h6.586c.199 0 .39.079.53.22l2.914 2.914c.141.14.22.331.22.53v10.586A1.75 1.75 0 0 1 12.25 16h-8.5A1.75 1.75 0 0 1 2 14.25Zm1.75-.25a.25.25 0 0 0-.25.25v12.5c0 .138.112.25.25.25h8.5a.25.25 0 0 0 .25-.25V6H9.75A1.75 1.75 0 0 1 8 4.25V1.5Zm6.906 1.442L10.5 1.646V4.25c0 .138.112.25.25.25h2.604Z"
      />
    </svg>
  );
}

export function SourceBrowser({ slug, dict, sourceRepo, initial }: Props) {
  const labels = dict.projects;
  const [overview, setOverview] = useState<PublicSourceOverview | null>(
    initial ?? null,
  );
  const [ref, setRef] = useState(initial?.ref ?? "");
  const [tree, setTree] = useState<SourceTreeEntry[]>(initial?.tree ?? []);
  const [dir, setDir] = useState("");
  const [blob, setBlob] = useState<{ path: string; content: string } | null>(
    null,
  );
  const [loadError, setLoadError] = useState(false);
  const [busy, setBusy] = useState(false);
  const skipInitialFetch = useRef(Boolean(initial));

  useEffect(() => {
    if (skipInitialFetch.current) {
      skipInitialFetch.current = false;
      return;
    }
    let cancelled = false;
    setBusy(true);
    void fetchPublicSource(slug, ref || undefined).then((data) => {
      if (cancelled) return;
      setBusy(false);
      if (!data) {
        setLoadError(true);
        return;
      }
      setLoadError(false);
      setOverview(data);
      setTree(data.tree);
      setDir("");
      setBlob(null);
      if (!ref) setRef(data.ref);
    });
    return () => {
      cancelled = true;
    };
  }, [slug, ref]);

  async function openDir(path: string) {
    if (!overview) return;
    setBusy(true);
    try {
      const next = await fetchPublicSourceTree(slug, overview.ref, path);
      setDir(path);
      setTree(next);
      setBlob(null);
    } finally {
      setBusy(false);
    }
  }

  async function openFile(path: string) {
    if (!overview) return false;
    setBusy(true);
    try {
      const file = await fetchPublicSourceBlob(slug, overview.ref, path);
      if (!file) return false;
      const parent = parentPath(path);
      if (parent !== dir) {
        setTree(await fetchPublicSourceTree(slug, overview.ref, parent));
        setDir(parent);
      }
      setBlob(file);
      return true;
    } finally {
      setBusy(false);
    }
  }

  async function openEntry(entry: SourceTreeEntry) {
    if (entry.type === "dir") {
      await openDir(entry.path);
      return;
    }
    await openFile(entry.path);
  }

  async function openRepoPath(path: string) {
    const name = path.split("/").pop() || "";
    if (name.includes(".") && (await openFile(path))) return;
    await openDir(path);
  }

  if (!overview) {
    return (
      <section className="gh-repo">
        <div className="source-loading">
          <SoftLoader label={labels.sourceLoading} />
          <p className="text-sm text-[var(--text-muted)]">
            {loadError ? labels.sourceUnavailable : labels.sourceLoading}
          </p>
        </div>
      </section>
    );
  }

  const crumbs = dir.split("/").filter(Boolean);
  const language = blob ? sourceLanguage(blob.path) : { hljs: "", label: "" };
  const githubFile = blob
    ? githubBlobUrl(sourceRepo.fullName, overview.ref, blob.path)
    : sourceRepo.htmlUrl;

  function kindLabel(entry: SourceTreeEntry) {
    if (entry.type === "dir") return labels.dir;
    return sourceLanguage(entry.name).label || labels.file;
  }

  return (
    <section className={`gh-repo${busy ? " gh-busy" : ""}`}>
      <div className="gh-repo-header">
        <div>
          <p className="gh-repo-name">
            <a href={sourceRepo.htmlUrl} rel="noreferrer" target="_blank">
              {sourceRepo.owner}
            </a>
            <span> / </span>
            <a href={sourceRepo.htmlUrl} rel="noreferrer" target="_blank">
              {sourceRepo.name}
            </a>
          </p>
          {sourceRepo.private ? (
            <span className="status-pill">{labels.privateRepo}</span>
          ) : (
            <span className="status-pill">{labels.publicRepo}</span>
          )}
        </div>
        {busy ? <SoftLoader label={labels.sourceLoading} /> : null}
        <a
          className="btn-ghost text-sm"
          href={sourceRepo.htmlUrl}
          rel="noreferrer"
          target="_blank"
        >
          GitHub
        </a>
      </div>

      <div className="gh-toolbar">
        <label className="gh-branch">
          {labels.branch}
          <select
            className="field field-tight field-inline font-mono text-sm"
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
        <nav className="gh-crumbs" aria-label="breadcrumb">
          <button type="button" onClick={() => void openDir("")}>
            {sourceRepo.name}
          </button>
          {crumbs.map((part, index) => {
            const path = crumbs.slice(0, index + 1).join("/");
            return (
              <span key={path}>
                <span className="gh-sep">/</span>
                <button type="button" onClick={() => void openDir(path)}>
                  {part}
                </button>
              </span>
            );
          })}
        </nav>
      </div>

      {!blob ? (
        <div className="gh-files">
          <table>
            <thead>
              <tr>
                <th>{labels.fileName}</th>
                <th className="gh-kind-col">{labels.fileKind}</th>
              </tr>
            </thead>
            <tbody>
              {dir ? (
                <tr>
                  <td colSpan={2}>
                    <button
                      type="button"
                      className="gh-file"
                      onClick={() => void openDir(parentPath(dir))}
                    >
                      <span className="gh-muted">..</span>
                    </button>
                  </td>
                </tr>
              ) : null}
              {tree.map((entry) => (
                <tr key={entry.path}>
                  <td>
                    <button
                      type="button"
                      className="gh-file"
                      onClick={() => void openEntry(entry)}
                    >
                      <FileIcon dir={entry.type === "dir"} />
                      <span>{entry.name}</span>
                    </button>
                  </td>
                  <td className="gh-kind-col">{kindLabel(entry)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="gh-box">
          <div className="gh-box-bar">
            <span className="font-mono text-sm">{blob.path}</span>
            <div className="gh-box-actions">
              {language.label ? (
                <span className="gh-lang">{language.label}</span>
              ) : null}
              <a
                className="text-sm text-[var(--accent-link)]"
                href={githubFile}
                rel="noreferrer"
                target="_blank"
              >
                GitHub
              </a>
              <button
                type="button"
                className="text-sm text-[var(--accent-link)]"
                onClick={() => setBlob(null)}
              >
                {labels.backToFiles}
              </button>
            </div>
          </div>
          {isMarkdownPath(blob.path) ? (
            <div className="gh-box-body">
              <GithubMarkdown
                source={blob.content}
                repoFullName={sourceRepo.fullName}
                refName={overview.ref}
                baseDir={parentPath(blob.path)}
                onRepoPath={(path) => void openRepoPath(path)}
              />
            </div>
          ) : (
            <SourceCode path={blob.path} text={blob.content} />
          )}
        </div>
      )}

      {!blob && !dir ? (
        <div className="gh-box">
          <div className="gh-box-bar">
            <button
              type="button"
              className="font-mono text-sm text-[var(--accent-link)]"
              onClick={() =>
                overview.readme.path
                  ? void openFile(overview.readme.path)
                  : undefined
              }
            >
              {overview.readme.path || labels.readme}
            </button>
          </div>
          <div className="gh-box-body">
            {overview.readme.content ? (
              <GithubMarkdown
                source={overview.readme.content}
                repoFullName={sourceRepo.fullName}
                refName={overview.ref}
                onRepoPath={(path) => void openRepoPath(path)}
              />
            ) : (
              <p className="text-[var(--text-muted)]">{labels.noReadme}</p>
            )}
          </div>
        </div>
      ) : null}
    </section>
  );
}
