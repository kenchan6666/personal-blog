"use client";

import { useState } from "react";
import { localeLabels } from "@/i18n/config";
import type { Localized } from "@/lib/api";
import { emptyLocalized, getSessionToken, mediaUrl, uploadOwnerMedia } from "@/lib/api";
import { appendMarkdownToAll } from "@/lib/about-templates";
import { markdownImages } from "@/lib/markdown-images";
import { MarkdownBody } from "./markdown-body";

type Props = {
  label: string;
  value: Localized;
  onChange: (next: Localized) => void;
  multiline?: boolean;
  previewable?: boolean;
  rows?: number;
  editLabel?: string;
  previewLabel?: string;
  emptyPreview?: string;
  allowImages?: boolean;
  uploadImageLabel?: string;
  uploadingImageLabel?: string;
  onImageError?: () => void;
};

export function BilingualField({
  label,
  value,
  onChange,
  multiline = false,
  previewable = false,
  rows = 8,
  editLabel = "Edit",
  previewLabel = "Preview",
  emptyPreview = "",
  allowImages = false,
  uploadImageLabel = "Upload image",
  uploadingImageLabel = "Uploading…",
  onImageError,
}: Props) {
  const [mode, setMode] = useState<"edit" | "preview">("edit");
  const [uploading, setUploading] = useState(false);
  const showPreview = previewable && multiline;

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    const token = getSessionToken();
    if (!token) return;
    setUploading(true);
    try {
      const { url } = await uploadOwnerMedia(token, file);
      const alt = file.name.replace(/\.[^.]+$/, "");
      onChange(appendMarkdownToAll(value, `\n\n![${alt}](<${url}>)\n`));
    } catch {
      onImageError?.();
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="mb-6">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-[var(--text-primary)]">{label}</p>
        <span className="flex flex-wrap items-center gap-2">
          {allowImages ? (
            <label className="btn-ghost cursor-pointer text-sm">
              {uploading ? uploadingImageLabel : uploadImageLabel}
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="sr-only"
                onChange={onUpload}
                disabled={uploading}
              />
            </label>
          ) : null}
          {showPreview ? (
            <span className="segment">
              <button
                type="button"
                className={mode === "edit" ? "segment-active" : ""}
                onClick={() => setMode("edit")}
              >
                {editLabel}
              </button>
              <button
                type="button"
                className={mode === "preview" ? "segment-active" : ""}
                onClick={() => setMode("preview")}
              >
                {previewLabel}
              </button>
            </span>
          ) : null}
        </span>
      </div>
      <div className="grid gap-3 lg:grid-cols-3">
        {(["zh-Hant", "zh-Hans", "en"] as const).map((localeKey) => (
          <div key={localeKey} className="block text-xs text-[var(--text-muted)]">
            {localeLabels[localeKey]}
            {showPreview && mode === "preview" ? (
              <div className="preview-pane mt-1">
                {(value[localeKey] ?? "").trim() ? (
                  <MarkdownBody source={value[localeKey] ?? ""} />
                ) : (
                  <p className="text-sm text-[var(--text-muted)]">
                    {emptyPreview}
                  </p>
                )}
              </div>
            ) : multiline ? (
              <textarea
                className="field"
                value={value[localeKey] ?? ""}
                onChange={(e) =>
                  onChange({
                    ...emptyLocalized(),
                    ...value,
                    [localeKey]: e.target.value,
                  })
                }
                rows={rows}
              />
            ) : (
              <input
                className="field"
                value={value[localeKey] ?? ""}
                onChange={(e) =>
                  onChange({
                    ...emptyLocalized(),
                    ...value,
                    [localeKey]: e.target.value,
                  })
                }
              />
            )}
            {allowImages ? (
              <ImagePreviews source={value[localeKey] ?? ""} />
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function ImagePreviews({ source }: { source: string }) {
  const images = markdownImages(source);
  if (images.length === 0) return null;
  return (
    <div className="about-image-previews mt-2">
      {images.map((image, index) => (
        <img
          key={`${image.src}-${index}`}
          src={mediaUrl(image.src)}
          alt={image.alt || ""}
        />
      ))}
    </div>
  );
}
