export const THEME_STORAGE_KEY = "site-theme";
export const THEME_SWITCH_MS = 420;

export type ThemeName = "light" | "dark";

let switchTimer = 0;

export function readStoredTheme(): ThemeName | null {
  try {
    const value = window.localStorage.getItem(THEME_STORAGE_KEY);
    return value === "dark" || value === "light" ? value : null;
  } catch {
    return null;
  }
}

export function resolveTheme(): ThemeName {
  return readStoredTheme() ?? "light";
}

export function applyTheme(theme: ThemeName) {
  const root = document.documentElement;
  root.dataset.theme = theme;
  root.style.colorScheme = theme;
}

export function persistTheme(theme: ThemeName) {
  const root = document.documentElement;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!reduce) {
    root.classList.add("theme-switching");
    window.clearTimeout(switchTimer);
    switchTimer = window.setTimeout(() => {
      root.classList.remove("theme-switching");
    }, THEME_SWITCH_MS);
  }
  applyTheme(theme);
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    /* ignore quota / private mode */
  }
  window.dispatchEvent(new Event("themechange"));
}
