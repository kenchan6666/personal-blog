const BULLET = /^(?:[-*•●◦]|\d+[.)])\s+/;
const SENTENCE = /(?<=[。！？；;!?])\s+|(?<=\.)\s+(?=[A-Z\u4e00-\u9fff])/;

export function splitResumeLines(value: string | string[]): string[] {
  const chunks = Array.isArray(value) ? value : [value];
  const lines: string[] = [];
  for (const chunk of chunks) {
    const text = String(chunk).replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
    if (!text) continue;
    let parts = text
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);
    if (parts.length <= 1 && !text.includes("\n")) {
      const split = text
        .split(SENTENCE)
        .map((item) => item.trim())
        .filter(Boolean);
      if (split.length) parts = split;
    }
    for (const part of parts) {
      const cleaned = part.replace(BULLET, "").trim();
      if (cleaned) lines.push(cleaned);
    }
  }
  return lines;
}
