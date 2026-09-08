const BULLET = /^(?:[-*•●◦]|\d+[.)])\s+/;
const SENTENCE = /(?<=[。！？；;!?])\s+|(?<=\.)\s+(?=[A-Z\u4e00-\u9fff])/;

export const BULLET_MARK = "• ";

export type ResumeDescriptionStyle = "bullets" | "paragraph";

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

export function descriptionStyle(
  value: string | undefined,
): ResumeDescriptionStyle {
  return value === "paragraph" ? "paragraph" : "bullets";
}

export function parseParagraphs(value: string | string[]): string[] {
  const text = (Array.isArray(value) ? value.join("\n\n") : value)
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .trim();
  if (!text) return [];
  return text
    .split(/\n\s*\n/)
    .map((part) => part.trim())
    .filter(Boolean);
}

export function toBulletEditorValue(lines: string[]): string {
  if (!lines.length) return BULLET_MARK;
  return lines.map((line) => `${BULLET_MARK}${line}`).join("\n");
}

export function fromBulletEditorValue(value: string): string[] {
  return value
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map((line) => line.replace(BULLET, "").trim())
    .filter(Boolean);
}

export function applyWordListEnter(
  value: string,
  start: number,
  end: number,
): { value: string; cursor: number } {
  const before = value.slice(0, start);
  const after = value.slice(end);
  const lineStart = before.lastIndexOf("\n") + 1;
  const currentPrefix = before.slice(lineStart);
  const restOfLine = after.split("\n")[0] ?? "";
  const lineBody = `${currentPrefix}${restOfLine}`.replace(BULLET, "").trim();

  if (!lineBody) {
    const stripped = currentPrefix.replace(BULLET, "");
    const next = `${before.slice(0, lineStart)}${stripped}${after}`;
    return { value: next, cursor: lineStart + stripped.length };
  }

  if (BULLET.test(`${currentPrefix}${restOfLine}`)) {
    const next = `${before}\n${BULLET_MARK}${after}`;
    return { value: next, cursor: before.length + 1 + BULLET_MARK.length };
  }

  const next = `${before}\n${after}`;
  return { value: next, cursor: before.length + 1 };
}
