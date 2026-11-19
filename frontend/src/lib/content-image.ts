import { isOptimizedImageHost } from "./image-hosts";

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
    return isOptimizedImageHost(protocol, hostname);
  } catch {
    return false;
  }
}

/** Width ladder the API's `?w=` resizer snaps to (keep in sync with backend). */
export const MEDIA_WIDTHS = [256, 384, 640, 828, 1080, 1280, 1600, 1920] as const;

/** `?w=` WebP variant URL for site-hosted media; other URLs are returned as-is. */
export function mediaVariant(src: string, width: number): string {
  const url = toImageSrc(src);
  if (!isSiteMediaPath(url)) return url;
  const base = url.split("?")[0];
  return `${base}?w=${width}`;
}

/** `srcset` for site media, capped at the image's natural width when known. */
export function mediaSrcSet(src: string, naturalWidth?: number): string | undefined {
  const url = toImageSrc(src);
  if (!isSiteMediaPath(url)) return undefined;
  const widths = MEDIA_WIDTHS.filter(
    (w, i) => !naturalWidth || w <= naturalWidth || i === 0,
  );
  return widths.map((w) => `${mediaVariant(url, w)} ${w}w`).join(", ");
}

const FILENAME_ALT =
  /^(?:whatsapp image|img[_-]?\d|dsc[_-]?\d|screenshot|screen shot|photo|image|wechat|微信圖片|微信图片|截圖|截图)|\.(?:jpe?g|png|webp|gif|heic)$/i;

/** Alt text that is just a camera/app filename says nothing to a reader. */
export function isFilenameAlt(alt: string): boolean {
  const value = alt.trim();
  return !value || FILENAME_ALT.test(value) || /\d{4}-\d{2}-\d{2} at \d/.test(value);
}
