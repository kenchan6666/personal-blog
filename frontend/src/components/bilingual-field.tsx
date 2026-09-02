"use client";

import { useState } from "react";
import type { Localized } from "@/lib/api";
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
}: Props) {
  const [mode, setMode] = useState<"edit" | "preview">("edit");
  const showPreview = previewable && multiline;

  return (
    <div className="mb-6">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-[var(--text-primary)]">{label}</p>
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
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {(["zh-Hant", "en"] as const).map((localeKey) => (
          <div key={localeKey} className="block text-xs text-[var(--text-muted)]">
            {localeKey}
            {showPreview && mode === "preview" ? (
              <div className="preview-pane mt-1">
                {value[localeKey].trim() ? (
                  <MarkdownBody source={value[localeKey]} />
                ) : (
                  <p className="text-sm text-[var(--text-muted)]">
                    {emptyPreview}
                  </p>
                )}
              </div>
            ) : multiline ? (
              <textarea
                className="field"
                value={value[localeKey]}
                onChange={(e) =>
                  onChange({ ...value, [localeKey]: e.target.value })
                }
                rows={rows}
              />
            ) : (
              <input
                className="field"
                value={value[localeKey]}
                onChange={(e) =>
                  onChange({ ...value, [localeKey]: e.target.value })
                }
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
