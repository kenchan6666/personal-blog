"use client";

import { useCallback, useLayoutEffect, useRef } from "react";

const EASE = "cubic-bezier(0.32, 0.72, 0, 1)";
const OPEN_MS = 280;
const CLOSE_MS = 240;

/**
 * Drives a `.disclosure` (grid 0fr/1fr) open/close with one Web Animation on
 * its height, so the content stays laid out and visible for the whole close
 * (it only fades/slides via compositor-friendly CSS on its children).
 *
 * The animated distance is capped to what is on screen: collapsing a list
 * that runs far below the fold animates only the visible part (the rest is
 * off screen anyway), so a tall list no longer drops hundreds of pixels per
 * frame on close.
 */
export function useCollapseMotion<T extends HTMLElement>(open: boolean) {
  const ref = useRef<T>(null);
  const first = useRef(true);
  const skip = useRef(false);
  const current = useRef<Animation | null>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (first.current) {
      first.current = false;
      return;
    }
    if (!el || typeof el.animate !== "function") return;
    const running = current.current;
    const finish = () => {
      if (current.current === running) current.current = null;
    };
    if (
      skip.current ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      skip.current = false;
      running?.cancel();
      finish();
      el.classList.remove("is-animating");
      return;
    }

    const inner = el.firstElementChild as HTMLElement | null;
    const full = inner?.scrollHeight ?? 0;
    const rect = el.getBoundingClientRect();
    // Mid-animation: start from wherever it is now.
    let from = running ? rect.height : open ? 0 : full;
    let to = open ? full : 0;
    running?.cancel();

    const onScreen = Math.max(0, window.innerHeight - Math.max(rect.top, 0)) + 24;
    from = Math.min(from, onScreen);
    to = Math.min(to, onScreen);
    if (Math.abs(to - from) < 1) {
      el.classList.remove("is-animating");
      return;
    }

    el.classList.add("is-animating");
    const anim = el.animate(
      [{ height: `${from}px` }, { height: `${to}px` }],
      { duration: open ? OPEN_MS : CLOSE_MS, easing: EASE },
    );
    current.current = anim;
    const done = () => {
      if (current.current !== anim) return;
      current.current = null;
      el.classList.remove("is-animating");
    };
    anim.onfinish = done;
    anim.oncancel = done;
  }, [open]);

  /** Next open/close happens without animation (e.g. jumping to an anchor). */
  const skipNextAnimation = useCallback(() => {
    skip.current = true;
  }, []);

  return { ref, skipNextAnimation };
}
