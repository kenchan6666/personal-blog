"use client";

import { useEffect, useRef, useState } from "react";
import {
  applyWordListEnter,
  descriptionStyle,
  fromBulletEditorValue,
  parseParagraphs,
  splitResumeLines,
  toBulletEditorValue,
  type ResumeDescriptionStyle,
} from "@/lib/resume-lines";
import { AgentChat } from "./agent-chat";
import { CmsModal } from "./cms-modal";

type Props = {
  label: string;
  proseLabel: string;
  listLabel: string;
  lines: string[];
  style?: string;
  closeLabel: string;
  pending?: boolean;
  onChange: (lines: string[], style: ResumeDescriptionStyle) => void;
};

function editorValue(lines: string[], style: ResumeDescriptionStyle) {
  return style === "bullets"
    ? toBulletEditorValue(lines)
    : lines.join("\n\n");
}

export function ResumeDescriptionField({
  label,
  proseLabel,
  listLabel,
  lines,
  style: styleProp,
  closeLabel,
  pending = false,
  onChange,
}: Props) {
  const style = descriptionStyle(styleProp);
  const [agentOpen, setAgentOpen] = useState(false);
  const [draft, setDraft] = useState(() => editorValue(lines, style));
  const focused = useRef(false);
  const insertionRun = useRef(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const serialized = editorValue(lines, style);

  useEffect(() => {
    if (pending || !focused.current) setDraft(serialized);
  }, [serialized, pending]);

  function emit(nextDraft: string, nextStyle: ResumeDescriptionStyle) {
    setDraft(nextDraft);
    onChange(
      nextStyle === "bullets"
        ? fromBulletEditorValue(nextDraft)
        : parseParagraphs(nextDraft),
      nextStyle,
    );
  }

  function switchStyle(next: ResumeDescriptionStyle) {
    if (next === style) return;
    const currentLines =
      style === "bullets"
        ? fromBulletEditorValue(draft)
        : parseParagraphs(draft);
    const converted =
      next === "paragraph"
        ? currentLines.length
          ? [currentLines.join(" ")]
          : []
        : currentLines.flatMap((part) =>
            part
              .split("\n")
              .map((item) => item.trim())
              .filter(Boolean),
          );
    onChange(converted, next);
    setDraft(editorValue(converted, next));
  }

  async function insertText(text: string) {
    const run = ++insertionRun.current;
    setAgentOpen(false);
    const clean =
      style === "paragraph"
        ? parseParagraphs(text).join("\n\n")
        : toBulletEditorValue(splitResumeLines(text));
    for (let index = 1; index <= clean.length; index += 1) {
      if (insertionRun.current !== run) return;
      emit(clean.slice(0, index), style);
      await new Promise((resolve) => window.setTimeout(resolve, 8));
    }
  }

  return (
    <div className="mb-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-[var(--text-primary)]">{label}</p>
        <span className="flex flex-wrap items-center gap-2">
          <span className="segment" role="group">
            <button
              type="button"
              className={style === "paragraph" ? "segment-active" : ""}
              disabled={pending}
              onClick={() => switchStyle("paragraph")}
            >
              {proseLabel}
            </button>
            <button
              type="button"
              className={style === "bullets" ? "segment-active" : ""}
              disabled={pending}
              onClick={() => switchStyle("bullets")}
            >
              {listLabel}
            </button>
          </span>
          <button
            type="button"
            className="btn-ghost ai-field-button text-sm"
            disabled={pending}
            onClick={() => setAgentOpen(true)}
          >
            ✦ AI
          </button>
        </span>
      </div>
      <div className={`agent-field-box${pending ? " is-pending" : ""}`}>
        <textarea
          ref={textareaRef}
          className="field"
          rows={5}
          value={draft}
          readOnly={pending}
          onFocus={() => {
            focused.current = true;
          }}
          onBlur={() => {
            focused.current = false;
          }}
          onChange={(event) => emit(event.target.value, style)}
          onKeyDown={(event) => {
            if (
              style !== "bullets" ||
              event.key !== "Enter" ||
              event.shiftKey ||
              event.nativeEvent.isComposing
            ) {
              return;
            }
            event.preventDefault();
            const node = event.currentTarget;
            const next = applyWordListEnter(
              node.value,
              node.selectionStart ?? 0,
              node.selectionEnd ?? 0,
            );
            emit(next.value, "bullets");
            requestAnimationFrame(() => {
              const el = textareaRef.current;
              if (!el) return;
              el.selectionStart = next.cursor;
              el.selectionEnd = next.cursor;
            });
          }}
        />
        {pending ? (
          <span className="agent-thinking" aria-label="等待模型">
            <i />
            <i />
            <i />
            <i />
          </span>
        ) : null}
      </div>
      <CmsModal
        open={agentOpen}
        title={`AI · ${label}`}
        closeLabel={closeLabel}
        elevated
        onClose={() => {
          insertionRun.current += 1;
          setAgentOpen(false);
        }}
      >
        <AgentChat
          compact
          context={{ label, value: draft }}
          onInsert={(_target, text) => void insertText(text)}
        />
      </CmsModal>
    </div>
  );
}
