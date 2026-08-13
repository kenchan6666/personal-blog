"use client";

import { useEffect, useState } from "react";
import type { Dictionary } from "@/i18n/dictionaries";
import {
  emptyLocalized,
  emptyOwnerSite,
  fetchOwnerSite,
  getSessionToken,
  mediaUrl,
  saveOwnerSite,
  uploadOwnerAvatar,
  type Localized,
  type OwnerLink,
  type OwnerSite,
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
                rows={4}
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

export function SiteEditor({ dict }: Props) {
  const a = dict.admin;
  const [site, setSite] = useState<OwnerSite>(emptyOwnerSite());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getSessionToken();
    if (!token) return;
    fetchOwnerSite(token)
      .then((data) => setSite(data))
      .catch(() => setError(a.errorGeneric))
      .finally(() => setLoading(false));
  }, [a.errorGeneric]);

  function updateLink(index: number, patch: Partial<OwnerLink>) {
    setSite((prev) => ({
      ...prev,
      links: prev.links.map((link, i) =>
        i === index ? { ...link, ...patch } : link,
      ),
    }));
  }

  function addLink() {
    setSite((prev) => ({
      ...prev,
      links: [
        ...prev.links,
        {
          label: emptyLocalized(),
          url: "",
          order: prev.links.length,
        },
      ],
    }));
  }

  function removeLink(index: number) {
    setSite((prev) => ({
      ...prev,
      links: prev.links.filter((_, i) => i !== index),
    }));
  }

  async function onAvatarChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    const token = getSessionToken();
    if (!token) return;
    setUploading(true);
    setMessage(null);
    setError(null);
    try {
      const result = await uploadOwnerAvatar(token, file);
      setSite((prev) => ({ ...prev, avatarUrl: result.avatarUrl }));
      setMessage(a.avatarUploaded);
    } catch {
      setError(a.errorGeneric);
    } finally {
      setUploading(false);
    }
  }

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    const token = getSessionToken();
    if (!token) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const saved = await saveOwnerSite(token, site);
      setSite(saved);
      setMessage(a.saved);
    } catch {
      setError(a.errorGeneric);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="text-[var(--text-muted)]">{a.loadingSite}</p>;
  }

  return (
    <form onSubmit={onSave} className="mt-10 max-w-3xl">
      <h2 className="display-font mb-6 text-xl font-bold">{a.siteEditor}</h2>

      <div className="mb-8">
        <p className="mb-3 text-sm font-semibold">{a.fieldAvatar}</p>
        <div className="flex flex-wrap items-center gap-5">
        {site.avatarUrl ? (
          <img
            src={mediaUrl(site.avatarUrl)}
            alt=""
            width={96}
            height={96}
            className="avatar-frame h-24 w-24 object-cover"
          />
        ) : (
          <div className="avatar-frame flex h-24 w-24 items-center justify-center text-xs text-[var(--text-muted)]">
            {a.noAvatar}
          </div>
        )}
        <label className="btn-ghost cursor-pointer text-sm">
          {uploading ? a.uploadingAvatar : a.uploadAvatar}
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="sr-only"
            onChange={onAvatarChange}
            disabled={uploading}
          />
        </label>
        </div>
      </div>

      <BilingualField
        label={a.fieldBrand}
        value={site.brand}
        onChange={(brand) => setSite({ ...site, brand })}
      />
      <BilingualField
        label={a.fieldHeroHeadline}
        value={site.heroHeadline}
        onChange={(heroHeadline) => setSite({ ...site, heroHeadline })}
      />
      <BilingualField
        label={a.fieldHeroSupport}
        value={site.heroSupport}
        onChange={(heroSupport) => setSite({ ...site, heroSupport })}
        multiline
      />
      <BilingualField
        label={a.fieldCtaProjects}
        value={site.heroCtaProjects}
        onChange={(heroCtaProjects) => setSite({ ...site, heroCtaProjects })}
      />
      <BilingualField
        label={a.fieldCtaArticles}
        value={site.heroCtaArticles}
        onChange={(heroCtaArticles) => setSite({ ...site, heroCtaArticles })}
      />
      <BilingualField
        label={a.fieldBio}
        value={site.bio}
        onChange={(bio) => setSite({ ...site, bio })}
        multiline
      />
      <BilingualField
        label={a.fieldSkills}
        value={site.skills}
        onChange={(skills) => setSite({ ...site, skills })}
        multiline
      />
      <BilingualField
        label={a.fieldExperience}
        value={site.experience}
        onChange={(experience) => setSite({ ...site, experience })}
        multiline
      />

      <label className="mb-6 block text-sm font-semibold">
        {a.fieldPublicEmail}
        <input
          className="mt-2 w-full rounded-[var(--radius-card)] border border-white/15 bg-white/5 px-3 py-2 text-sm font-normal text-white"
          type="email"
          value={site.publicEmail}
          onChange={(e) => setSite({ ...site, publicEmail: e.target.value })}
        />
      </label>

      <div className="mb-6">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold">{a.fieldLinks}</h3>
          <button type="button" className="btn-ghost text-xs" onClick={addLink}>
            {a.addLink}
          </button>
        </div>
        <div className="flex flex-col gap-4">
          {site.links.map((link, index) => (
            <div
              key={index}
              className="rounded-[var(--radius-card)] border border-white/10 p-4"
            >
              <BilingualField
                label={a.linkLabel}
                value={link.label}
                onChange={(label) => updateLink(index, { label })}
              />
              <label className="mb-3 block text-xs text-[var(--text-muted)]">
                URL
                <input
                  className="mt-1 w-full rounded-[var(--radius-card)] border border-white/15 bg-white/5 px-3 py-2 text-sm text-white"
                  value={link.url}
                  onChange={(e) => updateLink(index, { url: e.target.value })}
                />
              </label>
              <label className="mb-3 block text-xs text-[var(--text-muted)]">
                {a.linkOrder}
                <input
                  type="number"
                  className="mt-1 w-28 rounded-[var(--radius-card)] border border-white/15 bg-white/5 px-3 py-2 text-sm text-white"
                  value={link.order}
                  onChange={(e) =>
                    updateLink(index, { order: Number(e.target.value) || 0 })
                  }
                />
              </label>
              <button
                type="button"
                className="text-xs text-[var(--text-muted)] hover:text-white"
                onClick={() => removeLink(index)}
              >
                {a.removeLink}
              </button>
            </div>
          ))}
        </div>
      </div>

      {message ? (
        <p className="mb-3 text-sm text-[var(--accent-link)]">{message}</p>
      ) : null}
      {error ? (
        <p className="mb-3 text-sm text-[var(--accent-cta)]">{error}</p>
      ) : null}

      <button type="submit" className="btn-cta" disabled={saving}>
        {saving ? a.saving : a.save}
      </button>
    </form>
  );
}
