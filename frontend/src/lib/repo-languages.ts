import type { SourceRepo } from "@/lib/api";

export type LanguageShare = {
  name: string;
  share: number;
  color: string;
};

/** GitHub linguist colours for the languages that show up in these repos. */
const LANGUAGE_COLORS: Record<string, string> = {
  Python: "#3572A5",
  TypeScript: "#3178c6",
  JavaScript: "#f1e05a",
  CSS: "#663399",
  SCSS: "#c6538c",
  HTML: "#e34c26",
  Shell: "#89e051",
  PowerShell: "#012456",
  Dockerfile: "#384d54",
  "Jupyter Notebook": "#DA5B0B",
  GLSL: "#5686a5",
  Cuda: "#3A4E3A",
  Java: "#b07219",
  Kotlin: "#A97BFF",
  Go: "#00ADD8",
  Rust: "#dea584",
  C: "#555555",
  "C++": "#f34b7d",
  "C#": "#178600",
  Vue: "#41b883",
  Svelte: "#ff3e00",
  Swift: "#F05138",
  Dart: "#00B4AB",
  PHP: "#4F5D95",
  Ruby: "#701516",
  Solidity: "#AA6746",
  Makefile: "#427819",
  Batchfile: "#C1F12E",
};

const FALLBACK_COLOR = "#8e8e93";
const TTL_MS = 6 * 60 * 60 * 1000;
const cache = new Map<string, { at: number; value: LanguageShare[] }>();

/**
 * Language breakdown for a public GitHub repo (anonymous API, cached for a few
 * hours). Returns [] for private repos or on any failure, so callers simply
 * omit the chips and bar.
 */
export async function fetchRepoLanguages(
  repo: SourceRepo | null,
): Promise<LanguageShare[]> {
  if (!repo || repo.private || !repo.fullName) return [];
  const key = repo.fullName.toLowerCase();
  const hit = cache.get(key);
  if (hit && Date.now() - hit.at < TTL_MS) return hit.value;
  try {
    const res = await fetch(
      `https://api.github.com/repos/${repo.fullName}/languages`,
      {
        headers: { Accept: "application/vnd.github+json" },
        next: { revalidate: 21600 },
        signal: AbortSignal.timeout(3000),
      },
    );
    if (!res.ok) return hit?.value ?? [];
    const data = (await res.json()) as Record<string, number>;
    const total = Object.values(data).reduce((sum, n) => sum + n, 0);
    const value = total
      ? Object.entries(data)
          .map(([name, bytes]) => ({
            name,
            share: bytes / total,
            color: LANGUAGE_COLORS[name] ?? FALLBACK_COLOR,
          }))
          .sort((a, b) => b.share - a.share)
      : [];
    cache.set(key, { at: Date.now(), value });
    return value;
  } catch {
    return hit?.value ?? [];
  }
}
