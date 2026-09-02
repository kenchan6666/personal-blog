"use client";

import { useEffect, useState } from "react";
import type { Dictionary } from "@/i18n/dictionaries";
import {
  emptyLocalized,
  emptyOwnerSite,
  fetchOwnerSite,
  getSessionToken,
  localizedText,
  mediaUrl,
  saveOwnerSite,
  uploadOwnerAvatar,
  uploadOwnerHeroVisual,
  clearOwnerHeroVisual,
  type OwnerLink,
  type OwnerSite,
} from "@/lib/api";
import { CONTACT_PRESETS, type ContactPreset } from "@/lib/contact-link";
import { BilingualField } from "./bilingual-field";
import { CmsCard } from "./cms-card";
import { CmsModal } from "./cms-modal";
import { HeroVisualEditor } from "./hero-visual-editor";

type Props = {
  dict: Dictionary;
};

export function SiteEditor({ dict }: Props) {
  const a = dict.admin;
  const [site, setSite] = useState<OwnerSite>(emptyOwnerSite());
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadingHero, setUploadingHero] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getSessionToken();
    if (!token) return;
    fetchOwnerSite(token)
      .then((data) => setSite({ ...emptyOwnerSite(), ...data }))
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

  function addLink(preset?: ContactPreset) {
    setSite((prev) => ({
      ...prev,
      links: [
        ...prev.links,
        {
          label: preset
            ? {
                "zh-Hant": preset.labelZh,
                "zh-Hans": preset.labelHans,
                en: preset.labelEn,
              }
            : emptyLocalized(),
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

  async function onHeroVisualChange(file: File) {
    const token = getSessionToken();
    if (!token) return;
    setUploadingHero(true);
    setMessage(null);
    setError(null);
    try {
      const saved = await uploadOwnerHeroVisual(token, file);
      setSite((prev) => ({
        ...prev,
        ...saved,
        heroVisualPosX: prev.heroVisualPosX,
        heroVisualPosY: prev.heroVisualPosY,
        heroVisualScale: prev.heroVisualScale,
        heroVisualBlur: prev.heroVisualBlur,
      }));
      setMessage(a.heroVisualUploaded);
    } catch {
      setError(a.errorGeneric);
    } finally {
      setUploadingHero(false);
    }
  }

  async function onHeroVisualClear() {
    const token = getSessionToken();
    if (!token) return;
    setUploadingHero(true);
    setMessage(null);
    setError(null);
    try {
      const saved = await clearOwnerHeroVisual(token);
      setSite(saved);
      setMessage(a.heroVisualCleared);
    } catch {
      setError(a.errorGeneric);
    } finally {
      setUploadingHero(false);
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

  const brand = localizedText(site.brand);
  const previewProps = {
    editLabel: a.editTab,
    previewLabel: a.preview,
    translateLabel: a.translate,
    translatingLabel: a.translating,
    emptyPreview: a.emptyPreview,
    onTranslateError: (code: string) =>
      setError(code === "empty_source" ? a.errorTranslateEmpty : a.errorTranslate),
  };

  return (
    <CmsCard
      title={a.siteEditor}
      action={
        <button
          type="button"
          className="btn-ghost text-sm"
          onClick={() => {
            setMessage(null);
            setError(null);
            setOpen(true);
          }}
        >
          {a.editSite}
        </button>
      }
    >
      {loading ? (
        <p className="text-sm text-[var(--text-muted)]">{a.loadingSite}</p>
      ) : (
        <div className="flex flex-wrap items-center gap-4">
          {site.avatarUrl ? (
            <img
              src={mediaUrl(site.avatarUrl)}
              alt=""
              width={64}
              height={64}
              className="avatar-frame h-16 w-16 object-cover"
            />
          ) : (
            <div className="avatar-frame flex h-16 w-16 items-center justify-center text-xs text-[var(--text-muted)]">
              {a.noAvatar}
            </div>
          )}
          <div>
            <p className="display-font text-lg font-bold">
              {brand || a.fieldBrand}
            </p>
            <p className="text-sm text-[var(--text-muted)]">
              {site.publicEmail || a.fieldPublicEmail}
            </p>
          </div>
        </div>
      )}
      {error && !open ? (
        <p className="mt-3 text-sm text-[var(--danger)]">{error}</p>
      ) : null}

      <CmsModal
        open={open}
        title={a.siteEditor}
        closeLabel={a.close}
        onClose={() => setOpen(false)}
        footer={
          <>
            <button
              type="submit"
              form="site-form"
              className="btn-cta"
              disabled={saving}
            >
              {saving ? a.saving : a.save}
            </button>
            <button
              type="button"
              className="btn-ghost"
              onClick={() => setOpen(false)}
            >
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
        <form id="site-form" onSubmit={onSave}>
          <p className="mb-6 text-xs text-[var(--text-muted)]">
            {a.localeFallbackHint} {a.translateHint}
          </p>
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

          <HeroVisualEditor
            site={site}
            uploading={uploadingHero}
            onUpload={onHeroVisualChange}
            onClear={onHeroVisualClear}
            onChange={(patch) => setSite((prev) => ({ ...prev, ...patch }))}
            labels={{
              fieldHeroVisual: a.fieldHeroVisual,
              uploadHeroVisual: a.uploadHeroVisual,
              uploadingHeroVisual: a.uploadingHeroVisual,
              clearHeroVisual: a.clearHeroVisual,
              heroVisualHint: a.heroVisualHint,
              heroVisualPosX: a.heroVisualPosX,
              heroVisualPosY: a.heroVisualPosY,
              heroVisualScale: a.heroVisualScale,
              heroVisualBlur: a.heroVisualBlur,
              noHeroVisual: a.noHeroVisual,
            }}
          />

          <BilingualField
            label={a.fieldBrand}
            value={site.brand}
            onChange={(brand) => setSite({ ...site, brand })}
            {...previewProps}
          />
          <BilingualField
            label={a.fieldHeroHeadline}
            value={site.heroHeadline}
            onChange={(heroHeadline) => setSite({ ...site, heroHeadline })}
            {...previewProps}
          />
          <BilingualField
            label={a.fieldHeroSupport}
            value={site.heroSupport}
            onChange={(heroSupport) => setSite({ ...site, heroSupport })}
            multiline
            previewable
            rows={4}
            {...previewProps}
          />
          <BilingualField
            label={a.fieldCtaProjects}
            value={site.heroCtaProjects}
            onChange={(heroCtaProjects) =>
              setSite({ ...site, heroCtaProjects })
            }
            {...previewProps}
          />
          <BilingualField
            label={a.fieldCtaArticles}
            value={site.heroCtaArticles}
            onChange={(heroCtaArticles) =>
              setSite({ ...site, heroCtaArticles })
            }
            {...previewProps}
          />
          <BilingualField
            label={a.fieldArticlesLead}
            value={site.articlesLead}
            onChange={(articlesLead) => setSite({ ...site, articlesLead })}
            multiline
            rows={3}
            {...previewProps}
          />
          <BilingualField
            label={a.fieldAboutLead}
            value={site.aboutLead}
            onChange={(aboutLead) => setSite({ ...site, aboutLead })}
            multiline
            rows={3}
            {...previewProps}
          />
          <BilingualField
            label={a.fieldAboutEmpty}
            value={site.aboutEmpty}
            onChange={(aboutEmpty) => setSite({ ...site, aboutEmpty })}
            multiline
            rows={2}
            {...previewProps}
          />
          <BilingualField
            label={a.fieldBio}
            value={site.bio}
            onChange={(bio) => setSite({ ...site, bio })}
            multiline
            previewable
            rows={5}
            {...previewProps}
          />
          <BilingualField
            label={a.fieldSkills}
            value={site.skills}
            onChange={(skills) => setSite({ ...site, skills })}
            multiline
            previewable
            rows={4}
            {...previewProps}
          />
          <BilingualField
            label={a.fieldExperience}
            value={site.experience}
            onChange={(experience) => setSite({ ...site, experience })}
            multiline
            previewable
            rows={5}
            {...previewProps}
          />

          <label className="mb-6 block text-sm font-semibold">
            {a.fieldPublicEmail}
            <input
              className="field mt-2 font-normal"
              type="email"
              value={site.publicEmail}
              onChange={(e) =>
                setSite({ ...site, publicEmail: e.target.value })
              }
            />
          </label>

          <div className="mb-2">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <h3 className="text-sm font-semibold">{a.fieldLinks}</h3>
              <button
                type="button"
                className="btn-ghost text-xs"
                onClick={() => addLink()}
              >
                {a.addLink}
              </button>
            </div>
            <p className="mb-3 text-xs text-[var(--text-muted)]">
              {a.linkPresetsHint}
            </p>
            <div className="mb-4 flex flex-wrap gap-2">
              {CONTACT_PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  className="archive-chip"
                  onClick={() => addLink(preset)}
                >
                  {preset.labelZh}
                </button>
              ))}
            </div>
            <div className="flex flex-col gap-4">
              {site.links.map((link, index) => (
                <div
                  key={index}
                  className="rounded-[var(--radius-card)] border border-[var(--hairline)] p-4"
                >
                  <BilingualField
                    label={a.linkLabel}
                    value={link.label}
                    onChange={(label) => updateLink(index, { label })}
                    {...previewProps}
                  />
                  <label className="mb-3 block text-xs text-[var(--text-muted)]">
                    {a.linkUrl}
                    <input
                      className="field"
                      value={link.url}
                      placeholder={
                        CONTACT_PRESETS.find(
                          (preset) =>
                            preset.labelZh === link.label["zh-Hant"] ||
                            preset.labelHans === link.label["zh-Hans"] ||
                            preset.labelEn === link.label.en,
                        )?.placeholder ?? "https://、電話或 @帳號"
                      }
                      onChange={(e) =>
                        updateLink(index, { url: e.target.value })
                      }
                    />
                  </label>
                  <label className="mb-3 block text-xs text-[var(--text-muted)]">
                    {a.linkOrder}
                    <input
                      type="number"
                      className="field field-narrow"
                      value={link.order}
                      onChange={(e) =>
                        updateLink(index, {
                          order: Number(e.target.value) || 0,
                        })
                      }
                    />
                  </label>
                  <button
                    type="button"
                    className="text-xs text-[var(--text-muted)] hover:text-[var(--danger)]"
                    onClick={() => removeLink(index)}
                  >
                    {a.removeLink}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </form>
      </CmsModal>
    </CmsCard>
  );
}
