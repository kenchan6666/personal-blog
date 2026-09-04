"use client";

import { useRef, useState } from "react";
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
};

export function AgentField({
  label,
  value,
  onChange,
  multiline = false,
  rows = 4,
  placeholder,
  closeLabel,
}: Props) {
  const [agentOpen, setAgentOpen] = useState(false);
  const insertionRun = useRef(0);

  async function insertText(text: string) {
    const run = ++insertionRun.current;
    setAgentOpen(false);
    const clean = text.trim();
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
          onClick={() => setAgentOpen(true)}
        >
          ✦ AI
        </button>
      </div>
      {multiline ? (
        <textarea
          className="field"
          rows={rows}
          placeholder={placeholder}
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
      ) : (
        <input
          className="field"
          placeholder={placeholder}
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
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
