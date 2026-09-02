"use client";

import { CmsModal } from "./cms-modal";

type Props = {
  open: boolean;
  title: string;
  hint: string;
  confirmLabel: string;
  closeLabel: string;
  busy?: boolean;
  onClose: () => void;
  onConfirm: () => void;
};

export function CmsConfirm({
  open,
  title,
  hint,
  confirmLabel,
  closeLabel,
  busy,
  onClose,
  onConfirm,
}: Props) {
  return (
    <div className="cms-confirm">
      <CmsModal
        open={open}
        title={title}
        closeLabel={closeLabel}
        onClose={onClose}
        elevated
        footer={
          <>
            <button
              type="button"
              className="btn-cta"
              disabled={busy}
              onClick={onConfirm}
            >
              {confirmLabel}
            </button>
            <button type="button" className="btn-ghost" onClick={onClose}>
              {closeLabel}
            </button>
          </>
        }
      >
        <p className="text-sm text-[var(--text-muted)]">{hint}</p>
      </CmsModal>
    </div>
  );
}
