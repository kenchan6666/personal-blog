"use client";

import { useState } from "react";
import Image from "next/image";
import { mediaUrl, type HeroVisual as HeroVisualConfig } from "@/lib/api";

type Props = {
  visual?: HeroVisualConfig | null;
};

const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "").replace(/\/$/, "");

/**
 * Media paths come back relative (`/api/public/media/...`) and are served by
 * nginx, not by Next. Hand the optimizer an absolute public URL so it can fetch
 * the original; without a site URL, fall back to the unoptimized file.
 */
function heroSource(path: string): { src: string; optimize: boolean } {
  const url = mediaUrl(path);
  if (/^https?:\/\//i.test(url)) return { src: url, optimize: true };
  if (SITE_URL) return { src: `${SITE_URL}${url}`, optimize: true };
  return { src: url, optimize: false };
}

/** Mascot / photo sitting on a liquid-glass disc with a soft warm glow behind it. */
export function HeroVisual({ visual }: Props) {
  const { src, optimize } = visual?.url
    ? heroSource(visual.url)
    : { src: "", optimize: false };
  // If the optimizer cannot fetch the original, serve the file as-is.
  const [failed, setFailed] = useState(false);
  const scale = Math.max(0.8, (visual?.scale || 100) / 100);
  const blur = Math.max(0, visual?.blur || 0);
  const posX = visual?.posX ?? 50;
  const posY = visual?.posY ?? 50;

  return (
    <div className="hero-stage">
      <span className="hero-stage-glow" aria-hidden />
      <span className="hero-stage-disc liquid-glass" aria-hidden />
      {src ? (
        <div
          className="hero-stage-figure"
          style={{
            transform: `translate(${(posX - 50) * 0.4}%, ${(posY - 50) * 0.4}%) scale(${scale})`,
            filter: blur ? `blur(${blur}px)` : undefined,
          }}
        >
          <Image
            src={failed ? mediaUrl(visual?.url ?? "") : src}
            alt=""
            fill
            priority
            unoptimized={!optimize || failed}
            onError={() => setFailed(true)}
            sizes="(min-width: 1024px) 400px, (min-width: 640px) 320px, 260px"
            className="hero-stage-img"
          />
        </div>
      ) : null}
    </div>
  );
}
