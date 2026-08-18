"use client";

import { useEffect, useState } from "react";
import type { Dictionary } from "@/i18n/dictionaries";
import {
  createOwnerJournal,
  deleteOwnerJournal,
  emptyOwnerJournal,
  fetchOwnerJournals,
  getSessionToken,
  saveOwnerJournal,
  type Localized,
  type OwnerJournal,
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

function payloadOf(journal: OwnerJournal): Omit<OwnerJournal, "id"> {
  const { id: _id, ...rest } = journal;
  return rest;
}

export function JournalEditor({ dict }: Props) {
  const a = dict.admin;
  const [journals, setJournals] = useState<OwnerJournal[]>([]);
  const [current, setCurrent] = useState<OwnerJournal>(emptyOwnerJournal());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function reload(token: string) {
    const list = await fetchOwnerJournals(token);
    setJournals(list);
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

  function newJournal() {
    setCurrent(emptyOwnerJournal());
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
      const list = await reload(token);
      setCurrent(list[0] ?? emptyOwnerJournal());
      setMessage(a.deleted);
    } catch {
      setError(a.errorGeneric);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="text-[var(--text-muted)]">{a.loadingJournals}</p>;
  }

  return (
    <section className="mt-14">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h2 className="display-font text-xl font-bold">{a.journalEditor}</h2>
        <button type="button" className="btn-ghost text-sm" onClick={newJournal}>
          {a.newJournal}
        </button>
      </div>

      <ul className="mb-8 flex flex-col gap-2">
        {journals.map((journal) => (
          <li key={journal.id}>
            <button
              type="button"
              className={`w-full rounded-[var(--radius-card)] border px-4 py-3 text-left text-sm ${
                current.id === journal.id
                  ? "border-white/30 bg-white/10"
                  : "border-white/10 bg-white/5 hover:bg-white/10"
              }`}
              onClick={() => {
                setCurrent(journal);
                setMessage(null);
                setError(null);
              }}
            >
              <span className="font-semibold">
                {journal.title["zh-Hant"] ||
                  journal.title.en ||
                  journal.slug ||
                  a.untitledJournal}
              </span>
              <span className="ml-3 text-xs text-[var(--text-muted)]">
                {journal.status === "published" ? a.statusPublished : a.statusDraft}
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
                status: e.target.value as OwnerJournal["status"],
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
        <BilingualField
          label={a.fieldJournalTitle}
          value={current.title}
          onChange={(title) => setCurrent({ ...current, title })}
        />
        <BilingualField
          label={a.fieldJournalSummary}
          value={current.summary}
          onChange={(summary) => setCurrent({ ...current, summary })}
          multiline
        />
        <BilingualField
          label={a.fieldJournalBody}
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
              {a.deleteJournal}
            </button>
          ) : null}
        </div>
      </form>
    </section>
  );
}
