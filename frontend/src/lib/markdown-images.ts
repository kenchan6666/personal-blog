export type MarkdownImage = {
  alt: string;
  src: string;
};

export function markdownImages(source: string): MarkdownImage[] {
  const found: MarkdownImage[] = [];
  const pattern = /!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?\s*\)/g;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(source))) {
    const src = match[2].trim();
    if (src) found.push({ alt: match[1], src });
  }
  return found;
}
