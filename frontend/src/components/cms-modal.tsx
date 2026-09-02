"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

const CLOSE_MS = 220;
const FOCUSABLE =
  'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

type Props = {
  open: boolean;
  title: string;
  closeLabel: string;
  onClose: () => void;
  children: React.ReactNode;
  footer?: React.ReactNode;
  elevated?: boolean;
};

function focusablesIn(root: HTMLElement) {
  return [...root.querySelectorAll<HTMLElement>(FOCUSABLE)].filter(
    (el) => !el.hasAttribute("disabled") && el.tabIndex !== -1,
  );
}

function isTopmostModal(root: HTMLElement) {
  const roots = document.querySelectorAll(".cms-modal-root");
  return roots[roots.length - 1] === root;
}

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
  const panelRef = useRef<HTMLDivElement>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const lastFocus = useRef<HTMLElement | null>(null);

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
    lastFocus.current = document.activeElement as HTMLElement | null;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const panel = panelRef.current;
    const first = panel ? focusablesIn(panel)[0] : null;
    (first ?? panel)?.focus();

    function onKey(event: KeyboardEvent) {
      const root = rootRef.current;
      if (root && !isTopmostModal(root)) return;
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) return;
      const items = focusablesIn(panelRef.current);
      if (items.length === 0) {
        event.preventDefault();
        panelRef.current.focus();
        return;
      }
      const firstItem = items[0];
      const lastItem = items[items.length - 1];
      if (event.shiftKey && document.activeElement === firstItem) {
        event.preventDefault();
        lastItem.focus();
      } else if (!event.shiftKey && document.activeElement === lastItem) {
        event.preventDefault();
        firstItem.focus();
      }
    }

    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
      lastFocus.current?.focus?.();
    };
  }, [onClose, present]);

  if (!present || typeof document === "undefined") return null;

  return createPortal(
    <div
      ref={rootRef}
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
        ref={panelRef}
        className="cms-modal-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="cms-modal-title"
        tabIndex={-1}
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
