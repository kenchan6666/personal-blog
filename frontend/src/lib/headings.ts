export type ArticleHeading = {
  id: string;
  text: string;
  level: 2 | 3;
};

function cleanHeadingText(raw: string): string {
  return raw
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .trim();
}

export function slugifyHeading(
  text: string,
  used: Map<string, number> = new Map(),
): string {
  const base =
    text
      .toLowerCase()
      .replace(/[^\p{L}\p{N}]+/gu, "-")
      .replace(/^-+|-+$/g, "") || "section";
  const count = used.get(base) ?? 0;
  used.set(base, count + 1);
  return count ? `${base}-${count}` : base;
}

export function extractMarkdownHeadings(source: string): ArticleHeading[] {
  const used = new Map<string, number>();
  const headings: ArticleHeading[] = [];
  let inFence = false;

  for (const line of source.replace(/\r\n/g, "\n").split("\n")) {
    if (/^```/.test(line)) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;
    const match = /^(#{2,3})\s+(.+)$/.exec(line);
    if (!match) continue;
    const text = cleanHeadingText(match[2]);
    if (!text) continue;
    headings.push({
      id: slugifyHeading(text, used),
      text,
      level: match[1].length === 3 ? 3 : 2,
    });
  }

  return headings;
}
