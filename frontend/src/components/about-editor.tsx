"use client";

import { useEffect, useState } from "react";
import type { Dictionary } from "@/i18n/dictionaries";
import {
  createOwnerAboutModule,
  deleteOwnerAboutModule,
  emptyOwnerAboutModule,
  fetchOwnerAboutModules,
  getSessionToken,
  localizedText,
  saveOwnerAboutModule,
  type AboutKind,
  type OwnerAboutModule,
} from "@/lib/api";
import {
  ABOUT_KIND_BODIES,
  ABOUT_KIND_TITLES,
  localizedIsEmpty,
} from "@/lib/about-templates";
import { BilingualField } from "./bilingual-field";
import { CmsCard, StatusPill } from "./cms-card";
import { CmsConfirm } from "./cms-confirm";
import { CmsModal } from "./cms-modal";

type Props = {
  dict: Dictionary;
};

const KINDS: AboutKind[] = [
  "summary",
  "education",
  "achievement",
  "experience",
  "custom",
];

function payloadOf(module: OwnerAboutModule): Omit<OwnerAboutModule, "id"> {
  const { id: _id, ...rest } = module;
  return rest;
}

function kindLabel(dict: Dictionary, kind: AboutKind) {
  const map = {
    summary: dict.about.kindSummary,
    education: dict.about.kindEducation,
    achievement: dict.about.kindAchievement,
    experience: dict.about.kindExperience,
    custom: dict.about.kindCustom,
  };
  return map[kind];
}

export function AboutEditor({ dict }: Props) {
  const a = dict.admin;
  const [modules, setModules] = useState<OwnerAboutModule[]>([]);
  const [current, setCurrent] = useState<OwnerAboutModule>(emptyOwnerAboutModule());
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState(false);

  async function reload(token: string) {
    const list = await fetchOwnerAboutModules(token);
    setModules(list);
    return list;
  }

  useEffect(() => {
    const token = getSessionToken();
    if (!token) return;
    reload(token)
      .catch(() => setError(a.errorGeneric))
      .finally(() => setLoading(false));
  }, [a.errorGeneric]);

  function openEditor(module: OwnerAboutModule) {
    setCurrent(module);
    setMessage(null);
    setError(null);
    setOpen(true);
  }

  function closeEditor() {
    setOpen(false);
    setMessage(null);
    setError(null);
  }

  function applyKindTemplate() {
    const kind = current.kind;
    setCurrent({
      ...current,
      title: localizedIsEmpty(current.title)
        ? ABOUT_KIND_TITLES[kind]
        : current.title,
      body: ABOUT_KIND_BODIES[kind],
    });
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
        ? await saveOwnerAboutModule(token, current.id, payloadOf(current))
        : await createOwnerAboutModule(token, payloadOf(current));
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
      await deleteOwnerAboutModule(token, current.id);
      await reload(token);
      setOpen(false);
      setCurrent(emptyOwnerAboutModule());
      setConfirm(false);
    } catch {
      setError(a.errorGeneric);
    } finally {
      setSaving(false);
    }
  }

  const previewProps = {
    editLabel: a.editTab,
    previewLabel: a.preview,
    translateLabel: a.translate,
    translatingLabel: a.translating,
    emptyPreview: a.emptyPreview,
    onTranslateError: (code: string) =>
      setError(code === "empty_source" ? a.errorTranslateEmpty : a.errorTranslate),
  };
  const imageProps = {
    allowImages: true,
    uploadImageLabel: a.uploadAboutImage,
    uploadingImageLabel: a.uploadingAboutImage,
    onImageError: () => setError(a.errorGeneric),
  };

  return (
    <CmsCard
      title={a.aboutEditor}
      action={
        <button
          type="button"
          className="btn-ghost text-sm"
          onClick={() => openEditor(emptyOwnerAboutModule())}
        >
          {a.newAbout}
        </button>
      }
    >
      {error && !open ? (
        <p className="mb-3 text-sm text-[var(--danger)]">{error}</p>
      ) : null}
      {loading ? (
        <p className="text-sm text-[var(--text-muted)]">{a.loadingAbout}</p>
      ) : modules.length === 0 ? (
        <p className="text-sm text-[var(--text-muted)]">{a.emptyAbout}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {modules.map((module) => (
            <li key={module.id}>
              <button
                type="button"
                className="tile"
                onClick={() => openEditor(module)}
              >
                <span className="font-semibold">
                  {localizedText(module.title, a.untitledAbout)}
                </span>
                <span className="ml-3 text-xs text-[var(--text-muted)]">
                  {kindLabel(dict, module.kind)}
                </span>
                <span className="ml-3">
                  <StatusPill
                    published={module.status === "published"}
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
        title={
          current.id
            ? localizedText(current.title, a.untitledAbout)
            : a.newAbout
        }
        closeLabel={a.close}
        onClose={closeEditor}
        footer={
          <>
            <button
              type="submit"
              form="about-form"
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
                onClick={() => setConfirm(true)}
              >
                {a.deleteAbout}
              </button>
            ) : null}
            <button type="button" className="btn-ghost" onClick={closeEditor}>
              {a.close}
            </button>
            {message ? (
              <p className="text-sm text-[var(--text-muted)]">{message}</p>
            ) : null}
            {error ? (
              <p className="text-sm text-[var(--danger)]">{error}</p>
            ) : null}
          </>
        }
      >
        <form id="about-form" onSubmit={onSave}>
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
              {a.fieldAboutKind}
              <select
                className="field mt-2 font-normal"
                value={current.kind}
                onChange={(e) =>
                  setCurrent({
                    ...current,
                    kind: e.target.value as AboutKind,
                  })
                }
              >
                {KINDS.map((kind) => (
                  <option key={kind} value={kind}>
                    {kindLabel(dict, kind)}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-semibold">
              {a.fieldStatus}
              <select
                className="field mt-2 font-normal"
                value={current.status}
                onChange={(e) =>
                  setCurrent({
                    ...current,
                    status: e.target.value as OwnerAboutModule["status"],
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
          <p className="mb-3 text-xs text-[var(--text-muted)]">
            {a.aboutKindHint}
          </p>
          <div className="about-image-row">
            <button
              type="button"
              className="btn-ghost text-sm"
              onClick={applyKindTemplate}
            >
              {a.applyAboutTemplate}
            </button>
          </div>
          <p className="mb-4 text-xs text-[var(--text-muted)]">
            {a.localeFallbackHint} {a.translateHint}
          </p>
          <BilingualField
            label={a.fieldAboutTitle}
            value={current.title}
            onChange={(title) => setCurrent({ ...current, title })}
            {...previewProps}
          />
          <BilingualField
            label={a.fieldAboutBody}
            value={current.body}
            onChange={(body) => setCurrent({ ...current, body })}
            multiline
            previewable
            rows={10}
            {...previewProps}
            {...imageProps}
          />
        </form>
      </CmsModal>
      <CmsConfirm
        open={confirm}
        title={a.confirmDelete}
        hint={a.confirmDeleteHint}
        confirmLabel={a.deleteAbout}
        closeLabel={a.close}
        busy={saving}
        onClose={() => setConfirm(false)}
        onConfirm={() => void onDelete()}
      />
    </CmsCard>
  );
}
