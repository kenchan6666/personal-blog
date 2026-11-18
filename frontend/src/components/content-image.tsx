import type { CSSProperties } from "react";
import Image from "next/image";
import {
  canOptimizeImage,
  isSiteMediaPath,
  mediaSrcSet,
  mediaVariant,
  toImageSrc,
} from "@/lib/content-image";

type Props = {
  src: string;
  alt: string;
  className?: string;
  width?: number;
  height?: number;
  sizes?: string;
  priority?: boolean;
  style?: CSSProperties;
  /** Intrinsic size when known (site media): sets width/height to avoid layout shift. */
  natural?: { width: number; height: number };
};

export function ContentImage({
  src,
  alt,
  className,
  width = 1200,
  height = 800,
  sizes = "(max-width: 768px) 100vw, 38rem",
  priority,
  style,
  natural,
}: Props) {
  const url = toImageSrc(src);
  if (isSiteMediaPath(url)) {
    // The API serves resized WebP variants (`?w=`); let the browser pick one.
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={mediaVariant(url, 1280)}
        srcSet={mediaSrcSet(url, natural?.width)}
        sizes={sizes}
        alt={alt}
        width={natural?.width}
        height={natural?.height}
        loading={priority ? "eager" : "lazy"}
        fetchPriority={priority ? "high" : undefined}
        decoding="async"
        className={className}
        style={{ width: "100%", height: "auto", ...style }}
      />
    );
  }
  if (!canOptimizeImage(url)) {
    return (
      <img
        src={url}
        alt={alt}
        className={className}
        style={{ width: "100%", height: "auto", ...style }}
      />
    );
  }

  return (
    <Image
      src={url}
      alt={alt}
      width={width}
      height={height}
      sizes={sizes}
      priority={priority}
      className={className}
      style={{ width: "100%", height: "auto", ...style }}
    />
  );
}
