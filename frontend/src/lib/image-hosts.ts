/**
 * Remote hosts `next/image` may optimize. Shared by next.config (remotePatterns)
 * and the components that decide whether to hand a URL to the optimizer, so an
 * image on any other host falls back to a plain <img> instead of a 400.
 */
export const OPTIMIZED_IMAGE_HOSTS = [
  "kenchan0522.blog",
  "www.kenchan0522.blog",
  "raw.githubusercontent.com",
  "avatars.githubusercontent.com",
  "user-images.githubusercontent.com",
  "private-user-images.githubusercontent.com",
  "github.com",
] as const;

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1"]);

export function isOptimizedImageHost(protocol: string, hostname: string): boolean {
  if (LOCAL_HOSTS.has(hostname)) return protocol === "http:" || protocol === "https:";
  return (
    protocol === "https:" &&
    (OPTIMIZED_IMAGE_HOSTS as readonly string[]).includes(hostname)
  );
}
