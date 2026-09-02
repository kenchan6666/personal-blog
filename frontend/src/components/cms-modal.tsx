"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

const CLOSE_MS = 220;

type Props = {
  open: boolean;
  title: string;
  closeLabel: string;
  onClose: () => void;
  children: React.ReactNode;
  footer?: React.ReactNode;
  elevated?: boolean;
};

export function CmsModal({
  open,
  title,
  closeLabel,
  onClose,
  children,
  footer,
  elevated,
}: Props) {
  const [present, setPresent] = useState(open);
  const [entered, setEntered] = useState(false);

  useEffect(() => {
    if (open) {
      setPresent(true);
      const frame = window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => setEntered(true));
      });
      return () => window.cancelAnimationFrame(frame);
    }
    setEntered(false);
    const timer = window.setTimeout(() => setPresent(false), CLOSE_MS);
    return () => window.clearTimeout(timer);
  }, [open]);

  useEffect(() => {
    if (!present) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [present, onClose]);

  if (!present || typeof document === "undefined") return null;

  return createPortal(
    <div
      className={`cms-modal-root${entered ? " is-open" : ""}${elevated ? " is-elevated" : ""}`}
      role="presentation"
    >
      <button
        type="button"
        className="cms-modal-scrim"
        aria-label={closeLabel}
        onClick={onClose}
      />
      <div
        className="cms-modal-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="cms-modal-title"
      >
        <header className="cms-modal-header">
          <h2 id="cms-modal-title" className="display-font text-xl font-bold">
            {title}
          </h2>
          <button
            type="button"
            className="icon-btn"
            aria-label={closeLabel}
            onClick={onClose}
          >
            ×
          </button>
        </header>
        <div className="cms-modal-body">{children}</div>
        {footer ? <div className="cms-modal-footer">{footer}</div> : null}
      </div>
    </div>,
    document.body,
  );
}
