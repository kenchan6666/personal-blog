"use client";

import { useEffect, useState } from "react";
import type { Dictionary } from "@/i18n/dictionaries";
import {
  createOwnerArticle,
  createOwnerArticleCategory,
  deleteOwnerArticle,
  deleteOwnerArticleCategory,
  emptyOwnerArticle,
  fetchOwnerArticleCategories,
  fetchOwnerArticles,
  fetchOwnerProjects,
  getSessionToken,
  saveOwnerArticle,
  type OwnerArticle,
  type OwnerArticleCategory,
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

function categoryLabel(category: OwnerArticleCategory) {
  return category.title["zh-Hant"] || category.title.en || category.slug;
}

export function ArticleEditor({ dict }: Props) {
  const a = dict.admin;
  const [articles, setArticles] = useState<OwnerArticle[]>([]);
  const [projects, setProjects] = useState<OwnerProject[]>([]);
  const [categories, setCategories] = useState<OwnerArticleCategory[]>([]);
  const [current, setCurrent] = useState<OwnerArticle>(emptyOwnerArticle());
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [newSlug, setNewSlug] = useState("");
  const [newTitleZh, setNewTitleZh] = useState("");
  const [newTitleEn, setNewTitleEn] = useState("");
  const [addingCategory, setAddingCategory] = useState(false);

  async function reload(token: string) {
    const [list, projectList, categoryList] = await Promise.all([
      fetchOwnerArticles(token),
      fetchOwnerProjects(token),
      fetchOwnerArticleCategories(token),
    ]);
    setArticles(list);
    setProjects(projectList);
    setCategories(categoryList);
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

  async function onAddCategory(e: React.FormEvent) {
    e.preventDefault();
    const token = getSessionToken();
    if (!token) return;
    const slug = newSlug.trim().toLowerCase();
    if (!slug) return;
    setAddingCategory(true);
    setError(null);
    try {
      await createOwnerArticleCategory(token, {
        slug,
        title: { "zh-Hant": newTitleZh, en: newTitleEn },
        order: categories.length,
      });
      setNewSlug("");
      setNewTitleZh("");
      setNewTitleEn("");
      await reload(token);
      setMessage(a.saved);
    } catch {
      setError(a.errorGeneric);
    } finally {
      setAddingCategory(false);
    }
  }

  async function onDeleteCategory(id: string) {
    const token = getSessionToken();
    if (!token) return;
    setError(null);
    try {
      await deleteOwnerArticleCategory(token, id);
      const list = await reload(token);
      if (current.categorySlug) {
        const still = list.some((item) => item.categorySlug === current.categorySlug);
        if (!still) {
          setCurrent({ ...current, categorySlug: "taiko" });
        }
      }
    } catch {
      setError(a.errorGeneric);
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
      <div className="cms-categories">
        <p className="cms-categories-label">{a.articleCategories}</p>
        <ul className="cms-category-list">
          {categories.map((category) => (
            <li key={category.id} className="cms-category-item">
              <span>{categoryLabel(category)}</span>
              {category.protected ? (
                <em>{a.protectedCategory}</em>
              ) : (
                <button
                  type="button"
                  className="btn-ghost text-xs"
                  onClick={() => void onDeleteCategory(category.id)}
                >
                  {a.deleteCategory}
                </button>
              )}
            </li>
          ))}
        </ul>
        <form className="cms-category-add" onSubmit={onAddCategory}>
          <input
            className="field field-tight"
            value={newSlug}
            onChange={(e) => setNewSlug(e.target.value)}
            placeholder={a.categorySlug}
            required
          />
          <input
            className="field field-tight"
            value={newTitleZh}
            onChange={(e) => setNewTitleZh(e.target.value)}
            placeholder={a.categoryTitleZh}
            required
          />
          <input
            className="field field-tight"
            value={newTitleEn}
            onChange={(e) => setNewTitleEn(e.target.value)}
            placeholder={a.categoryTitleEn}
          />
          <button
            type="submit"
            className="btn-ghost text-sm"
            disabled={addingCategory}
          >
            {a.newCategory}
          </button>
        </form>
      </div>
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
              {a.fieldCategory}
              <select
                className="field mt-2 font-normal"
                value={current.categorySlug || "taiko"}
                onChange={(e) =>
                  setCurrent({ ...current, categorySlug: e.target.value })
                }
              >
                {categories.map((category) => (
                  <option key={category.id} value={category.slug}>
                    {categoryLabel(category)}
                  </option>
                ))}
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
