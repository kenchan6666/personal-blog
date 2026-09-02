"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

function isInternalNav(anchor: HTMLAnchorElement, pathname: string) {
  if (anchor.target && anchor.target !== "_self") return false;
  if (anchor.hasAttribute("download")) return false;
  const href = anchor.getAttribute("href");
  if (!href || href.startsWith("#") || href.startsWith("mailto:") || href.startsWith("tel:")) {
    return false;
  }
  if (/^https?:/i.test(href)) {
    try {
      const url = new URL(href);
      if (url.origin !== window.location.origin) return false;
      return url.pathname !== pathname;
    } catch {
      return false;
    }
  }
  const path = href.split("?")[0]?.split("#")[0] ?? href;
  return path !== pathname;
}

export function RouteProgress() {
  const pathname = usePathname();
  const [phase, setPhase] = useState<"idle" | "pending" | "done">("idle");

  useEffect(() => {
    setPhase((current) => (current === "pending" ? "done" : current));
  }, [pathname]);

  useEffect(() => {
    function onClick(event: MouseEvent) {
      if (event.defaultPrevented || event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const anchor = (event.target as HTMLElement | null)?.closest("a");
      if (!anchor || !isInternalNav(anchor, pathname)) return;
      setPhase("pending");
    }
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, [pathname]);

  useEffect(() => {
    document.documentElement.classList.toggle(
      "is-route-pending",
      phase === "pending",
    );
    return () => document.documentElement.classList.remove("is-route-pending");
  }, [phase]);

  useEffect(() => {
    if (phase !== "done") return;
    const timer = window.setTimeout(() => setPhase("idle"), 340);
    return () => window.clearTimeout(timer);
  }, [phase]);

  useEffect(() => {
    if (phase !== "pending") return;
    const timer = window.setTimeout(() => setPhase("idle"), 12000);
    return () => window.clearTimeout(timer);
  }, [phase]);

  if (phase === "idle") return null;
  return (
    <div
      className={`route-progress${phase === "done" ? " is-done" : ""}`}
      role="progressbar"
      aria-hidden
    >
      <span />
    </div>
  );
}
