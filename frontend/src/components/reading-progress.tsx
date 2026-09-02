"use client";

import { useEffect, useState } from "react";

export function ReadingProgress() {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const update = () => {
      const article = document.querySelector<HTMLElement>(".article-body");
      if (!article) return;
      const top = article.getBoundingClientRect().top + window.scrollY;
      const height = article.offsetHeight;
      const readable = Math.max(height - window.innerHeight * 0.45, 1);
      const next = (window.scrollY - top + 80) / readable;
      setProgress(Math.min(1, Math.max(0, next)));
    };

    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, []);

  return (
    <div
      className="reading-progress"
      style={{ transform: `scaleX(${progress})` }}
      aria-hidden
    />
  );
}
