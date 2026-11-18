import { mediaUrl } from "@/lib/api";

/** First image in a markdown body, e.g. `![](</api/public/media/content/x.jpg>)`. */
export function firstMarkdownImage(markdown: string): string {
  const match = markdown.match(/!\[[^\]]*\]\(\s*<?([^)\s>]+)>?/);
  return match ? mediaUrl(match[1]) : "";
}

/** First prose paragraph of a markdown body, stripped of simple markup. */
export function firstParagraph(markdown: string): string {
  return (
    markdown
      .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
      .replace(/[#>*_`]/g, "")
      .split(/\n\s*\n/)
      .map((part) => part.trim())
      .find(Boolean) ?? ""
  );
}
