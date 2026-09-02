import { useEffect, useState } from "react";
import { resolveTheme, type ThemeName } from "./theme";

export function useResolvedTheme(): ThemeName {
  const [theme, setTheme] = useState<ThemeName>("light");

  useEffect(() => {
    const read = () => {
      const attr = document.documentElement.dataset.theme;
      if (attr === "dark" || attr === "light") return attr;
      return resolveTheme();
    };
    setTheme(read());
    const onChange = () => setTheme(read());
    const observer = new MutationObserver(onChange);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    window.addEventListener("themechange", onChange);
    return () => {
      observer.disconnect();
      window.removeEventListener("themechange", onChange);
    };
  }, []);

  return theme;
}
