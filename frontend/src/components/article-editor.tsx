"use client";

import { useEffect, useState } from "react";
import type { Dictionary } from "@/i18n/dictionaries";
import {
  createOwnerArticle,
  deleteOwnerArticle,
  emptyOwnerArticle,
  fetchOwnerArticles,
  fetchOwnerProjects,
  getSessionToken,
  saveOwnerArticle,
  type Localized,
  type OwnerArticle,
  type OwnerProject,
} from "@/lib/api";

type Props = {
  dict: Dictionary;
};

function BilingualField({
  label,
  value,
  onChange,
  multiline = false,
}: {
  label: string;
  value: Localized;
  onChange: (next: Localized) => void;
  multiline?: boolean;
}) {
  return (
    <fieldset className="mb-6">
      <legend className="mb-2 text-sm font-semibold text-[var(--text-primary)]">
        {label}
      </legend>
      <div className="grid gap-3 sm:grid-cols-2">
        {(["zh-Hant", "en"] as const).map((localeKey) => (
          <label
            key={localeKey}
            className="block text-xs text-[var(--text-muted)]"
          >
            {localeKey}
            {multiline ? (
              <textarea
                className="mt-1 w-full rounded-[var(--radius-card)] border border-white/15 bg-white/5 px-3 py-2 text-sm text-white"
                value={value[localeKey]}
                onChange={(e) =>
                  onChange({ ...value, [localeKey]: e.target.value })
                }
                rows={8}
              />
            ) : (
              <input
                className="mt-1 w-full rounded-[var(--radius-card)] border border-white/15 bg-white/5 px-3 py-2 text-sm text-white"
                value={value[localeKey]}
                onChange={(e) =>
                  onChange({ ...value, [localeKey]: e.target.value })
                }
              />
            )}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function payloadOf(article: OwnerArticle): Omit<OwnerArticle, "id"> {
  const { id: _id, ...rest } = article;
  return rest;
}

export function ArticleEditor({ dict }: Props) {
  const a = dict.admin;
  const [articles, setArticles] = useState<OwnerArticle[]>([]);
  const [projects, setProjects] = useState<OwnerProject[]>([]);
  const [current, setCurrent] = useState<OwnerArticle>(emptyOwnerArticle());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function reload(token: string) {
    const [list, projectList] = await Promise.all([
      fetchOwnerArticles(token),
      fetchOwnerProjects(token),
    ]);
    setArticles(list);
    setProjects(projectList);
    return list;
  }

  useEffect(() => {
    const token = getSessionToken();
    if (!token) return;
    reload(token)
      .then((list) => {
        if (list[0]) setCurrent(list[0]);
      })
      .catch(() => setError(a.errorGeneric))
      .finally(() => setLoading(false));
  }, [a.errorGeneric]);

  function newArticle() {
    setCurrent(emptyOwnerArticle());
    setMessage(null);
    setError(null);
  }

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    const token = getSessionToken();
    if (!token) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const saved = current.id
        ? await saveOwnerArticle(token, current.id, payloadOf(current))
        : await createOwnerArticle(token, payloadOf(current));
      setCurrent(saved);
      await reload(token);
      setMessage(a.saved);
    } catch {
      setError(a.errorGeneric);
    } finally {
      setSaving(false);
    }
  }

  async function onDelete() {
    const token = getSessionToken();
    if (!token || !current.id) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      await deleteOwnerArticle(token, current.id);
      const list = await reload(token);
      setCurrent(list[0] ?? emptyOwnerArticle());
      setMessage(a.deleted);
    } catch {
      setError(a.errorGeneric);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="text-[var(--text-muted)]">{a.loadingArticles}</p>;
  }

  return (
    <section className="mt-14">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h2 className="display-font text-xl font-bold">{a.articleEditor}</h2>
        <button type="button" className="btn-ghost text-sm" onClick={newArticle}>
          {a.newArticle}
        </button>
      </div>

      <ul className="mb-8 flex flex-col gap-2">
        {articles.map((article) => (
          <li key={article.id}>
            <button
              type="button"
              className={`w-full rounded-[var(--radius-card)] border px-4 py-3 text-left text-sm ${
                current.id === article.id
                  ? "border-white/30 bg-white/10"
                  : "border-white/10 bg-white/5 hover:bg-white/10"
              }`}
              onClick={() => {
                setCurrent(article);
                setMessage(null);
                setError(null);
              }}
            >
              <span className="font-semibold">
                {article.title["zh-Hant"] ||
                  article.title.en ||
                  article.slug ||
                  a.untitledArticle}
              </span>
              <span className="ml-3 text-xs text-[var(--text-muted)]">
                {article.status === "published" ? a.statusPublished : a.statusDraft}
              </span>
            </button>
          </li>
        ))}
      </ul>

      <form onSubmit={onSave} className="max-w-3xl">
        <label className="mb-6 block text-sm font-semibold">
          {a.fieldSlug}
          <input
            className="mt-2 w-full rounded-[var(--radius-card)] border border-white/15 bg-white/5 px-3 py-2 text-sm font-normal text-white"
            value={current.slug}
            onChange={(e) => setCurrent({ ...current, slug: e.target.value })}
            required
          />
        </label>
        <label className="mb-6 block text-sm font-semibold">
          {a.fieldStatus}
          <select
            className="mt-2 w-full rounded-[var(--radius-card)] border border-white/15 bg-white/5 px-3 py-2 text-sm font-normal text-white"
            value={current.status}
            onChange={(e) =>
              setCurrent({
                ...current,
                status: e.target.value as OwnerArticle["status"],
              })
            }
          >
            <option value="draft">{a.statusDraft}</option>
            <option value="published">{a.statusPublished}</option>
          </select>
        </label>
        <label className="mb-6 block text-sm font-semibold">
          {a.fieldOrder}
          <input
            type="number"
            className="mt-2 w-28 rounded-[var(--radius-card)] border border-white/15 bg-white/5 px-3 py-2 text-sm font-normal text-white"
            value={current.order}
            onChange={(e) =>
              setCurrent({ ...current, order: Number(e.target.value) || 0 })
            }
          />
        </label>
        <label className="mb-6 block text-sm font-semibold">
          {a.fieldRelatedProject}
          <select
            className="mt-2 w-full rounded-[var(--radius-card)] border border-white/15 bg-white/5 px-3 py-2 text-sm font-normal text-white"
            value={current.relatedProjectSlug}
            onChange={(e) =>
              setCurrent({ ...current, relatedProjectSlug: e.target.value })
            }
          >
            <option value="">{a.noRelatedProject}</option>
            {projects.map((project) => (
              <option key={project.id} value={project.slug}>
                {project.title["zh-Hant"] || project.title.en || project.slug}
              </option>
            ))}
          </select>
        </label>
        <BilingualField
          label={a.fieldArticleTitle}
          value={current.title}
          onChange={(title) => setCurrent({ ...current, title })}
        />
        <BilingualField
          label={a.fieldArticleSummary}
          value={current.summary}
          onChange={(summary) => setCurrent({ ...current, summary })}
          multiline
        />
        <BilingualField
          label={a.fieldArticleBody}
          value={current.body}
          onChange={(body) => setCurrent({ ...current, body })}
          multiline
        />

        {message ? (
          <p className="mb-3 text-sm text-[var(--accent-link)]">{message}</p>
        ) : null}
        {error ? (
          <p className="mb-3 text-sm text-[var(--accent-cta)]">{error}</p>
        ) : null}

        <div className="flex flex-wrap gap-3">
          <button type="submit" className="btn-cta" disabled={saving}>
            {saving ? a.saving : a.save}
          </button>
          {current.id ? (
            <button
              type="button"
              className="btn-ghost"
              disabled={saving}
              onClick={onDelete}
            >
              {a.deleteArticle}
            </button>
          ) : null}
        </div>
      </form>
    </section>
  );
}
