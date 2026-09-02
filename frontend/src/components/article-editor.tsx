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
  type OwnerArticle,
  type OwnerProject,
} from "@/lib/api";
import { BilingualField } from "./bilingual-field";
import { CmsCard, StatusPill } from "./cms-card";
import { CmsModal } from "./cms-modal";

type Props = {
  dict: Dictionary;
};

function payloadOf(article: OwnerArticle): Omit<OwnerArticle, "id"> {
  const { id: _id, ...rest } = article;
  return rest;
}

function titleOf(article: OwnerArticle, fallback: string) {
  return article.title["zh-Hant"] || article.title.en || article.slug || fallback;
}

export function ArticleEditor({ dict }: Props) {
  const a = dict.admin;
  const [articles, setArticles] = useState<OwnerArticle[]>([]);
  const [projects, setProjects] = useState<OwnerProject[]>([]);
  const [current, setCurrent] = useState<OwnerArticle>(emptyOwnerArticle());
  const [open, setOpen] = useState(false);
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
      .catch(() => setError(a.errorGeneric))
      .finally(() => setLoading(false));
  }, [a.errorGeneric]);

  function openEditor(article: OwnerArticle) {
    setCurrent(article);
    setMessage(null);
    setError(null);
    setOpen(true);
  }

  function closeEditor() {
    setOpen(false);
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
      await reload(token);
      setOpen(false);
      setCurrent(emptyOwnerArticle());
      setMessage(a.deleted);
    } catch {
      setError(a.errorGeneric);
    } finally {
      setSaving(false);
    }
  }

  const previewProps = {
    editLabel: a.editTab,
    previewLabel: a.preview,
    emptyPreview: a.emptyPreview,
  };

  return (
    <CmsCard
      title={a.articleEditor}
      action={
        <button
          type="button"
          className="btn-ghost text-sm"
          onClick={() => openEditor(emptyOwnerArticle())}
        >
          {a.newArticle}
        </button>
      }
    >
      {error && !open ? (
        <p className="mb-3 text-sm text-[var(--danger)]">{error}</p>
      ) : null}
      {loading ? (
        <p className="text-sm text-[var(--text-muted)]">{a.loadingArticles}</p>
      ) : articles.length === 0 ? (
        <p className="text-sm text-[var(--text-muted)]">{a.emptyArticles}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {articles.map((article) => (
            <li key={article.id}>
              <button
                type="button"
                className="tile"
                onClick={() => openEditor(article)}
              >
                <span className="font-semibold">
                  {titleOf(article, a.untitledArticle)}
                </span>
                <span className="ml-3">
                  <StatusPill
                    published={article.status === "published"}
                    publishedLabel={a.statusPublished}
                    draftLabel={a.statusDraft}
                  />
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      <CmsModal
        open={open}
        title={current.id ? titleOf(current, a.untitledArticle) : a.newArticle}
        closeLabel={a.close}
        onClose={closeEditor}
        footer={
          <>
            <button
              type="submit"
              form="article-form"
              className="btn-cta"
              disabled={saving}
            >
              {saving ? a.saving : a.save}
            </button>
            {current.id ? (
              <button
                type="button"
                className="btn-ghost"
                disabled={saving}
                onClick={() => void onDelete()}
              >
                {a.deleteArticle}
              </button>
            ) : null}
            <button type="button" className="btn-ghost" onClick={closeEditor}>
              {a.close}
            </button>
            {message ? (
              <p className="text-sm text-[var(--accent-link)]">{message}</p>
            ) : null}
            {error ? (
              <p className="text-sm text-[var(--danger)]">{error}</p>
            ) : null}
          </>
        }
      >
        <form id="article-form" onSubmit={onSave}>
          <label className="mb-6 block text-sm font-semibold">
            {a.fieldSlug}
            <input
              className="field mt-2 font-normal"
              value={current.slug}
              onChange={(e) => setCurrent({ ...current, slug: e.target.value })}
              required
            />
          </label>
          <div className="mb-6 grid gap-4 sm:grid-cols-2">
            <label className="block text-sm font-semibold">
              {a.fieldStatus}
              <select
                className="field mt-2 font-normal"
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
            <label className="block text-sm font-semibold">
              {a.fieldOrder}
              <input
                type="number"
                className="field mt-2 font-normal"
                value={current.order}
                onChange={(e) =>
                  setCurrent({ ...current, order: Number(e.target.value) || 0 })
                }
              />
            </label>
          </div>
          <label className="mb-6 block text-sm font-semibold">
            {a.fieldRelatedProject}
            <select
              className="field mt-2 font-normal"
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
          <p className="mb-4 text-xs text-[var(--text-muted)]">
            {a.localeFallbackHint}
          </p>
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
            previewable
            rows={5}
            {...previewProps}
          />
          <BilingualField
            label={a.fieldArticleBody}
            value={current.body}
            onChange={(body) => setCurrent({ ...current, body })}
            multiline
            previewable
            rows={12}
            {...previewProps}
          />
        </form>
      </CmsModal>
    </CmsCard>
  );
}
