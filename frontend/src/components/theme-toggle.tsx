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

// A full, filled crescent and a sun with a solid core and short rays: at
// 16px both read as icons, not as a loading spinner.
function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" width="17" height="17" aria-hidden>
      <path
        fill="currentColor"
        d="M20.4 14.6A8.6 8.6 0 0 1 9.4 3.6a.6.6 0 0 0-.78-.73A9.6 9.6 0 1 0 21.13 15.4a.6.6 0 0 0-.73-.8z"
      />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" width="17" height="17" aria-hidden>
      <circle cx="12" cy="12" r="4.6" fill="currentColor" />
      <path
        d="M12 2.5v1.8M12 19.7v1.8M2.5 12h1.8M19.7 12h1.8M5.3 5.3l1.27 1.27M17.43 17.43l1.27 1.27M5.3 18.7l1.27-1.27M17.43 6.57l1.27-1.27"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
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
