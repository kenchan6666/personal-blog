"use client";

import { useEffect, useState } from "react";
import type { Dictionary } from "@/i18n/dictionaries";
import {
  createOwnerJournal,
  deleteOwnerJournal,
  emptyOwnerJournal,
  fetchOwnerJournals,
  getSessionToken,
  localizedText,
  saveOwnerJournal,
  type OwnerJournal,
} from "@/lib/api";
import { BilingualField } from "./bilingual-field";
import { CmsCard, StatusPill } from "./cms-card";
import { CmsConfirm } from "./cms-confirm";
import { CmsModal } from "./cms-modal";

type Props = {
  dict: Dictionary;
};

function payloadOf(journal: OwnerJournal): Omit<OwnerJournal, "id"> {
  const { id: _id, ...rest } = journal;
  return rest;
}

function titleOf(journal: OwnerJournal, fallback: string) {
  return localizedText(journal.title, journal.slug || fallback);
}

export function JournalEditor({ dict }: Props) {
  const a = dict.admin;
  const [journals, setJournals] = useState<OwnerJournal[]>([]);
  const [current, setCurrent] = useState<OwnerJournal>(emptyOwnerJournal());
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState(false);

  async function reload(token: string) {
    const list = await fetchOwnerJournals(token);
    setJournals(list);
    return list;
  }

  useEffect(() => {
    const token = getSessionToken();
    if (!token) return;
    reload(token)
      .catch(() => setError(a.errorGeneric))
      .finally(() => setLoading(false));
  }, [a.errorGeneric]);

  function openEditor(journal: OwnerJournal) {
    setCurrent(journal);
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
        ? await saveOwnerJournal(token, current.id, payloadOf(current))
        : await createOwnerJournal(token, payloadOf(current));
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
      await deleteOwnerJournal(token, current.id);
      await reload(token);
      setOpen(false);
      setCurrent(emptyOwnerJournal());
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
      title={a.journalEditor}
      action={
        <button
          type="button"
          className="btn-ghost text-sm"
          onClick={() => openEditor(emptyOwnerJournal())}
        >
          {a.newJournal}
        </button>
      }
    >
      {error && !open ? (
        <p className="mb-3 text-sm text-[var(--danger)]">{error}</p>
      ) : null}
      {loading ? (
        <p className="text-sm text-[var(--text-muted)]">{a.loadingJournals}</p>
      ) : journals.length === 0 ? (
        <p className="text-sm text-[var(--text-muted)]">{a.emptyJournals}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {journals.map((journal) => (
            <li key={journal.id}>
              <button
                type="button"
                className="tile"
                onClick={() => openEditor(journal)}
              >
                <span className="font-semibold">
                  {titleOf(journal, a.untitledJournal)}
                </span>
                <span className="ml-3">
                  <StatusPill
                    published={journal.status === "published"}
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
        title={current.id ? titleOf(current, a.untitledJournal) : a.newJournal}
        closeLabel={a.close}
        onClose={closeEditor}
        footer={
          <>
            <button
              type="submit"
              form="journal-form"
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
                {a.deleteJournal}
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
        <form id="journal-form" onSubmit={onSave}>
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
                    status: e.target.value as OwnerJournal["status"],
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
          <BilingualField
            label={a.fieldJournalTitle}
            value={current.title}
            onChange={(title) => setCurrent({ ...current, title })}
            {...previewProps}
          />
          <BilingualField
            label={a.fieldJournalSummary}
            value={current.summary}
            onChange={(summary) => setCurrent({ ...current, summary })}
            multiline
            previewable
            rows={5}
            {...previewProps}
          />
          <BilingualField
            label={a.fieldJournalBody}
            value={current.body}
            onChange={(body) => setCurrent({ ...current, body })}
            multiline
            previewable
            rows={12}
            {...previewProps}
            {...imageProps}
          />
        </form>
      </CmsModal>
      <CmsConfirm
        open={confirm}
        title={a.confirmDelete}
        hint={a.confirmDeleteHint}
        confirmLabel={a.deleteJournal}
        closeLabel={a.close}
        busy={saving}
        onClose={() => setConfirm(false)}
        onConfirm={() => void onDelete()}
      />
    </CmsCard>
  );
}
