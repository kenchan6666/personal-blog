const SAFE_SRC = /^(https?:\/\/|\/\/|\/)/i;

export function isSafeMarkdownImageUrl(url: string): boolean {
  return SAFE_SRC.test(url.trim());
}

function attr(tag: string, name: string): string {
  const quoted = new RegExp(`${name}\\s*=\\s*["']([^"']*)["']`, "i").exec(tag);
  if (quoted) return quoted[1];
  const bare = new RegExp(`${name}\\s*=\\s*([^\\s>]+)`, "i").exec(tag);
  return bare?.[1] ?? "";
}

export function isBadgeImage(url: string): boolean {
  if (/\/api\/public\/media\//i.test(url)) return false;
  return /img\.shields\.io|badgen\.net|\/badge\/|shields\.io\//i.test(url);
}

export function liftReadmeHtmlImages(source: string): string {
  return source
    .replace(/<img\b[^>]*>/gi, (tag) => {
      const src = attr(tag, "src");
      if (!src || !SAFE_SRC.test(src)) return "";
      const alt = attr(tag, "alt");
      return `![${alt}](<${src}>)`;
    })
    .replace(/<\/?p\b[^>]*>/gi, "\n\n");
}
