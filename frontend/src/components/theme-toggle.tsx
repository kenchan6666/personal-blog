"use client";

import { useEffect, useState } from "react";
import type { Dictionary } from "@/i18n/dictionaries";
import {
  applyTheme,
  persistTheme,
  resolveTheme,
  type ThemeName,
} from "@/lib/theme";

type Props = {
  dict: Dictionary;
};

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden>
      <path
        fill="currentColor"
        d="M15.2 3.1a1 1 0 0 1 1.15 1.45A8.2 8.2 0 1 0 19.4 16a1 1 0 0 1 1.5 1.2A10.2 10.2 0 1 1 14.3 2.9c.3 0 .6.07.9.2z"
      />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden>
      <path
        fill="currentColor"
        d="M12 4.2a1 1 0 0 1 1 1V7a1 1 0 1 1-2 0V5.2a1 1 0 0 1 1-1zm0 12.3a4.5 4.5 0 1 0 0-9 4.5 4.5 0 0 0 0 9zm7.8-5.5H18a1 1 0 1 0 0 2h1.8a1 1 0 1 0 0-2zM6 12a1 1 0 0 0-1-1H3.2a1 1 0 1 0 0 2H5a1 1 0 0 0 1-1zm11.1 5.1a1 1 0 0 0-1.4 0l-1.3 1.3a1 1 0 1 0 1.4 1.4l1.3-1.3a1 1 0 0 0 0-1.4zM9.6 8.2a1 1 0 0 0 0-1.4L8.3 5.5A1 1 0 0 0 6.9 6.9l1.3 1.3a1 1 0 0 0 1.4 0zm.1 8.9-1.3 1.3A1 1 0 1 1 7 17l1.3-1.3a1 1 0 0 1 1.4 1.4zm8.4-9.6-1.3 1.3a1 1 0 1 1-1.4-1.4l1.3-1.3a1 1 0 1 1 1.4 1.4zM12 17a1 1 0 0 1 1 1v1.8a1 1 0 1 1-2 0V18a1 1 0 0 1 1-1z"
      />
    </svg>
  );
}

export function ThemeToggle({ dict }: Props) {
  const [theme, setTheme] = useState<ThemeName>("light");

  useEffect(() => {
    const next = resolveTheme();
    setTheme(next);
    applyTheme(next);
  }, []);

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    persistTheme(next);
  }

  const toDark = theme !== "dark";

  return (
    <button
      type="button"
      className="site-chrome-link theme-toggle"
      aria-label={toDark ? dict.theme.toDark : dict.theme.toLight}
      title={toDark ? dict.theme.toDark : dict.theme.toLight}
      onClick={toggle}
    >
      <span className="theme-toggle-icons" aria-hidden>
        <span className="theme-toggle-sun">
          <SunIcon />
        </span>
        <span className="theme-toggle-moon">
          <MoonIcon />
        </span>
      </span>
    </button>
  );
}
