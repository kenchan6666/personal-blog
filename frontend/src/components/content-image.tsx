import type { CSSProperties } from "react";
import Image from "next/image";
import { canOptimizeImage, toImageSrc } from "@/lib/content-image";

type Props = {
  src: string;
  alt: string;
  className?: string;
  width?: number;
  height?: number;
  sizes?: string;
  priority?: boolean;
  style?: CSSProperties;
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
}: Props) {
  const url = toImageSrc(src);
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
