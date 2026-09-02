import Script from "next/script";
import { THEME_STORAGE_KEY } from "@/lib/theme";

const boot = `(function(){try{var k=${JSON.stringify(THEME_STORAGE_KEY)};var s=localStorage.getItem(k);var t=s==="dark"||s==="light"?s:(window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light");document.documentElement.dataset.theme=t;document.documentElement.style.colorScheme=t;}catch(e){document.documentElement.dataset.theme="light";}})();`;

export function ThemeScript() {
  return (
    <Script id="theme-boot" strategy="beforeInteractive">
      {boot}
    </Script>
  );
}
