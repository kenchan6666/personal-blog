import { NextRequest, NextResponse } from "next/server";
import { defaultLocale, isLocale } from "@/i18n/config";

/**
 * Per-request nonce CSP for every HTML route. Next.js reads the nonce from the
 * request's Content-Security-Policy header and stamps it on its own inline
 * scripts and on <Script> tags; 'strict-dynamic' lets those trusted scripts
 * load the rest of the bundle (chunks, mermaid, …). Pages are already
 * rendered per request (the root layout reads headers()), so nonces cost no
 * caching. Styles keep 'unsafe-inline' because React style={} attributes and
 * mermaid's SVG <style> cannot carry a nonce. nginx adds a static fallback
 * policy for responses that don't come through here (/api, static files).
 */
function contentSecurityPolicy(nonce: string): string {
  const dev = process.env.NODE_ENV === "development";
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${dev ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https:",
    "font-src 'self' data:",
    "connect-src 'self'",
    "media-src 'self' data: blob:",
    "worker-src 'self' blob:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'self'",
    ...(dev ? [] : ["upgrade-insecure-requests"]),
  ].join("; ");
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/_next") || pathname.startsWith("/api")) {
    return NextResponse.next();
  }

  const nonce = btoa(crypto.randomUUID());
  const csp = contentSecurityPolicy(nonce);
  const headers = new Headers(request.headers);
  headers.set("x-nonce", nonce);
  headers.set("Content-Security-Policy", csp);

  const segment = pathname.split("/")[1];
  if (pathname.includes(".") || isLocale(segment)) {
    if (isLocale(segment)) headers.set("x-locale", segment);
    const response = NextResponse.next({ request: { headers } });
    response.headers.set("Content-Security-Policy", csp);
    if (isLocale(segment) && pathname.split("/")[2] === "admin") {
      response.headers.set("X-Robots-Tag", "noindex, nofollow, noarchive");
    }
    return response;
  }

  const url = request.nextUrl.clone();
  url.pathname = `/${defaultLocale}${pathname === "/" ? "" : pathname}`;
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
