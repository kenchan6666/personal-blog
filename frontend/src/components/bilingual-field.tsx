"use client";

import { useRef, useState } from "react";
import { localeLabels } from "@/i18n/config";
import type { Localized } from "@/lib/api";
import {
  emptyLocalized,
  getSessionToken,
  mediaUrl,
  translateOwnerLocalized,
  uploadOwnerMedia,
} from "@/lib/api";
import { appendMarkdownToAll } from "@/lib/about-templates";
import {
  joinMarkdownBlocks,
  splitMarkdownBlocks,
  type MarkdownBlock,
} from "@/lib/markdown-images";
import { MarkdownBody } from "./markdown-body";
import { AgentChat } from "./agent-chat";
import { CmsModal } from "./cms-modal";

type Props = {
  label: string;
  value: Localized;
  onChange: (next: Localized) => void;
  multiline?: boolean;
  previewable?: boolean;
  rows?: number;
  editLabel?: string;
  previewLabel?: string;
  translateLabel?: string;
  translatingLabel?: string;
  emptyPreview?: string;
  allowImages?: boolean;
  uploadImageLabel?: string;
  uploadingImageLabel?: string;
  onImageError?: () => void;
  onTranslateError?: (code: string) => void;
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
  translateLabel = "Translate",
  translatingLabel = "Translating…",
  emptyPreview = "",
  allowImages = false,
  uploadImageLabel = "Upload image",
  uploadingImageLabel = "Uploading…",
  onImageError,
  onTranslateError,
}: Props) {
  const [mode, setMode] = useState<"edit" | "preview">("edit");
  const [uploading, setUploading] = useState(false);
  const [translating, setTranslating] = useState(false);
  const [agentOpen, setAgentOpen] = useState(false);
  const insertionRun = useRef(0);
  const showPreview = previewable && multiline;
  const visualImages = allowImages && multiline;

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

  async function onTranslate() {
    const token = getSessionToken();
    if (!token || translating) return;
    setTranslating(true);
    try {
      const result = await translateOwnerLocalized(token, value);
      onChange({
        "zh-Hant": result["zh-Hant"] ?? "",
        "zh-Hans": result["zh-Hans"] ?? "",
        en: result.en ?? "",
      });
      setMode("edit");
      if (result.warnings?.length) {
        onTranslateError?.(result.warnings[0] ?? "translate_failed");
      }
    } catch (error) {
      const code = error instanceof Error ? error.message : "translate_failed";
      onTranslateError?.(code);
    } finally {
      setTranslating(false);
    }
  }

  async function insertAgentText(locale: keyof Localized, text: string) {
    const run = ++insertionRun.current;
    setAgentOpen(false);
    setMode("edit");
    const clean = text.trim();
    for (let index = 1; index <= clean.length; index += 1) {
      if (insertionRun.current !== run) return;
      onChange({
        ...emptyLocalized(),
        ...value,
        [locale]: clean.slice(0, index),
      });
      await new Promise((resolve) => window.setTimeout(resolve, 8));
    }
  }

  return (
    <div className="mb-6">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-[var(--text-primary)]">{label}</p>
        <span className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            className="btn-ghost ai-field-button text-sm"
            onClick={() => setAgentOpen(true)}
          >
            ✦ AI
          </button>
          {allowImages ? (
            <label className="btn-ghost cursor-pointer text-sm">
              {uploading ? uploadingImageLabel : uploadImageLabel}
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="sr-only"
                onChange={onUpload}
                disabled={uploading || translating}
              />
            </label>
          ) : null}
          <span className="segment">
            <button
              type="button"
              className={mode === "edit" ? "segment-active" : ""}
              onClick={() => setMode("edit")}
            >
              {editLabel}
            </button>
            {showPreview ? (
              <button
                type="button"
                className={mode === "preview" ? "segment-active" : ""}
                onClick={() => setMode("preview")}
              >
                {previewLabel}
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => void onTranslate()}
              disabled={translating}
            >
              {translating ? translatingLabel : translateLabel}
            </button>
          </span>
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
            ) : visualImages ? (
              <MarkdownBlocksField
                source={value[localeKey] ?? ""}
                rows={rows}
                onChange={(next) =>
                  onChange({
                    ...emptyLocalized(),
                    ...value,
                    [localeKey]: next,
                  })
                }
              />
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
          </div>
        ))}
      </div>
      <CmsModal
        open={agentOpen}
        title={`AI · ${label}`}
        closeLabel="关闭"
        elevated
        onClose={() => {
          insertionRun.current += 1;
          setAgentOpen(false);
        }}
      >
        <AgentChat
          compact
          context={{ label, value }}
          onInsert={(locale, text) => void insertAgentText(locale, text)}
        />
      </CmsModal>
    </div>
  );
}

function MarkdownBlocksField({
  source,
  rows,
  onChange,
}: {
  source: string;
  rows: number;
  onChange: (next: string) => void;
}) {
  const blocks = splitMarkdownBlocks(source);
  const textCount = Math.max(
    1,
    blocks.filter((block) => block.type === "text").length,
  );
  const textRows = Math.max(3, Math.round(rows / textCount));

  function commit(next: MarkdownBlock[]) {
    onChange(joinMarkdownBlocks(next));
  }

  return (
    <div className="md-blocks">
      {blocks.map((block, index) =>
        block.type === "text" ? (
          <textarea
            key={`text-${index}`}
            className="field"
            value={block.value}
            rows={textRows}
            onChange={(event) => {
              const next = [...blocks];
              next[index] = { type: "text", value: event.target.value };
              commit(next);
            }}
          />
        ) : (
          <div key={`image-${block.src}-${index}`} className="md-block-image">
            <img src={mediaUrl(block.src)} alt={block.alt || ""} />
            <button
              type="button"
              className="icon-btn md-block-image-remove"
              aria-label="Remove image"
              onClick={() => {
                const next = blocks.filter((_, item) => item !== index);
                commit(next);
              }}
            >
              ×
            </button>
          </div>
        ),
      )}
    </div>
  );
}
