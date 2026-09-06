"use client";

import { useRef, useState } from "react";
import { splitResumeLines } from "@/lib/resume-lines";
import { AgentChat } from "./agent-chat";
import { CmsModal } from "./cms-modal";

type Props = {
  label: string;
  value: string;
  onChange: (next: string) => void;
  multiline?: boolean;
  rows?: number;
  placeholder?: string;
  closeLabel: string;
  pending?: boolean;
};

export function AgentField({
  label,
  value,
  onChange,
  multiline = false,
  rows = 4,
  placeholder,
  closeLabel,
  pending = false,
}: Props) {
  const [agentOpen, setAgentOpen] = useState(false);
  const insertionRun = useRef(0);

  async function insertText(text: string) {
    const run = ++insertionRun.current;
    setAgentOpen(false);
    const clean = multiline
      ? splitResumeLines(text).join("\n")
      : text.trim();
    for (let index = 1; index <= clean.length; index += 1) {
      if (insertionRun.current !== run) return;
      onChange(clean.slice(0, index));
      await new Promise((resolve) => window.setTimeout(resolve, 8));
    }
  }

  return (
    <div className="mb-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-[var(--text-primary)]">{label}</p>
        <button
          type="button"
          className="btn-ghost ai-field-button text-sm"
          disabled={pending}
          onClick={() => setAgentOpen(true)}
        >
          ✦ AI
        </button>
      </div>
      <div className={`agent-field-box${pending ? " is-pending" : ""}`}>
        {multiline ? (
          <textarea
            className="field"
            rows={rows}
            placeholder={placeholder}
            value={value}
            readOnly={pending}
            onChange={(event) => onChange(event.target.value)}
          />
        ) : (
          <input
            className="field"
            placeholder={placeholder}
            value={value}
            readOnly={pending}
            onChange={(event) => onChange(event.target.value)}
          />
        )}
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
          context={{ label, value }}
          onInsert={(_target, text) => void insertText(text)}
        />
      </CmsModal>
    </div>
  );
}
