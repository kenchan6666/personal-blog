export type MarkdownImage = {
  alt: string;
  src: string;
};

export type MarkdownBlock =
  | { type: "text"; value: string }
  | { type: "image"; alt: string; src: string };

const IMAGE_RE = /!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?\s*\)/g;

export function markdownImages(source: string): MarkdownImage[] {
  return splitMarkdownBlocks(source)
    .filter((block): block is Extract<MarkdownBlock, { type: "image" }> => block.type === "image")
    .map(({ alt, src }) => ({ alt, src }));
}

function trimEdgeNewlines(value: string) {
  return value.replace(/^\n+/, "").replace(/\n+$/, "");
}

export function splitMarkdownBlocks(source: string): MarkdownBlock[] {
  const blocks: MarkdownBlock[] = [];
  IMAGE_RE.lastIndex = 0;
  let last = 0;
  let match: RegExpExecArray | null;
  while ((match = IMAGE_RE.exec(source))) {
    blocks.push({ type: "text", value: trimEdgeNewlines(source.slice(last, match.index)) });
    blocks.push({ type: "image", alt: match[1], src: match[2].trim() });
    last = match.index + match[0].length;
  }
  blocks.push({ type: "text", value: trimEdgeNewlines(source.slice(last)) });
  return blocks;
}

export function joinMarkdownBlocks(blocks: MarkdownBlock[]): string {
  const parts: string[] = [];
  for (const block of blocks) {
    if (block.type === "text") {
      if (block.value) parts.push(block.value);
    } else if (block.src) {
      parts.push(`![${block.alt}](<${block.src}>)`);
    }
  }
  return parts.join("\n\n");
}
