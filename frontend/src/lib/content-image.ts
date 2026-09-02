const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1"]);

export function toImageSrc(url: string): string {
  if (!url.startsWith("http://") && !url.startsWith("https://")) return url;
  try {
    const parsed = new URL(url);
    const site = process.env.NEXT_PUBLIC_SITE_URL;
    if (site && parsed.origin === new URL(site).origin) {
      return `${parsed.pathname}${parsed.search}`;
    }
  } catch {
    /* keep original */
  }
  return url;
}

function pathnameOf(src: string): string {
  if (src.startsWith("/")) return src.split("?")[0] ?? src;
  try {
    return new URL(src).pathname;
  } catch {
    return src;
  }
}

export function isSiteMediaPath(src: string): boolean {
  return pathnameOf(src).startsWith("/api/public/media/");
}

export function canOptimizeImage(url: string): boolean {
  const src = toImageSrc(url);
  // FastAPI files behind the Next rewrite: `_next/image` fetches them as a
  // local path, gets HTML/JSON back in Docker, and returns 400.
  if (isSiteMediaPath(src)) return false;
  if (src.startsWith("/")) return true;
  try {
    const { protocol, hostname } = new URL(src);
    if (protocol !== "http:" && protocol !== "https:") return false;
    if (LOCAL_HOSTS.has(hostname)) return true;
    if (hostname.endsWith("githubusercontent.com")) return true;
    if (hostname === "github.com" || hostname.endsWith(".github.com")) {
      return true;
    }
    return protocol === "https:";
  } catch {
    return false;
  }
}
