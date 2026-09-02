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

export function canOptimizeImage(url: string): boolean {
  const src = toImageSrc(url);
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
