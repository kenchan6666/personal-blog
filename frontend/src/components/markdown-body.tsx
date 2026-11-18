import type { ReactNode } from "react";
import type { Components } from "react-markdown";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { mediaUrl } from "@/lib/api";
import { extractMarkdownHeadings } from "@/lib/headings";
import {
  isBadgeImage,
  isSafeMarkdownImageUrl,
  liftReadmeHtmlImages,
} from "@/lib/readme-html";
import { ContentImage } from "./content-image";
import { isFilenameAlt } from "@/lib/content-image";
import { markdownImages } from "@/lib/markdown-images";
import { HighlightedPre } from "./highlighted-pre";

function headingText(children: ReactNode): string {
  return Array.isArray(children)
    ? children.map((child) => (typeof child === "string" ? child : "")).join("")
    : typeof children === "string"
      ? children
      : "";
}

type Props = {
  source: string;
  /** Intrinsic sizes of site images, keyed by the markdown src. */
  imageMeta?: Record<string, { width: number; height: number }>;
  /** Builds an alt when the author's alt is just a filename (n is 1-based). */
  fallbackAlt?: (n: number) => string;
  /** Load the first content image eagerly (it is usually the LCP element). */
  eagerFirstImage?: boolean;
};

export function MarkdownBody({
  source,
  imageMeta,
  fallbackAlt,
  eagerFirstImage = false,
}: Props) {
  const markdown = liftReadmeHtmlImages(source);
  // 1-based position of each image src, for fallback alts and eager loading.
  const imageOrder = new Map<string, number>();
  for (const image of markdownImages(markdown)) {
    if (!imageOrder.has(image.src)) imageOrder.set(image.src, imageOrder.size + 1);
  }
  if (!markdown.trim()) return null;

  const ids = extractMarkdownHeadings(markdown).map((heading) => heading.id);
  let next = 0;
  const takeId = (children: ReactNode) =>
    ids[next++] ?? headingText(children);

  const components: Components = {
    h1: ({ children }) => <h1>{children}</h1>,
    h2: ({ children }) => <h2 id={takeId(children)}>{children}</h2>,
    h3: ({ children }) => <h3 id={takeId(children)}>{children}</h3>,
    table: ({ children }) => (
      <div className="table-scroll" tabIndex={0}>
        <table>{children}</table>
      </div>
    ),
    a: ({ href, children }) => {
      const url = href ?? "";
      const safe =
        !url ||
        url.startsWith("http://") ||
        url.startsWith("https://") ||
        url.startsWith("/") ||
        url.startsWith("#") ||
        url.startsWith("mailto:");
      if (!safe) return <>{children}</>;
      const external = url.startsWith("http://") || url.startsWith("https://");
      return (
        <a
          href={url}
          {...(external ? { target: "_blank", rel: "noreferrer" } : {})}
        >
          {children}
        </a>
      );
    },
    img: ({ src, alt }) => {
      const raw = typeof src === "string" ? src.trim() : "";
      const url = raw ? mediaUrl(raw) : "";
      if (!isSafeMarkdownImageUrl(url || raw)) return null;
      if (isBadgeImage(url)) {
        return <img src={url} alt={alt ?? ""} className="md-badge" />;
      }
      const imageIndex = imageOrder.get(raw) ?? imageOrder.size + 1;
      const rawAlt = alt ?? "";
      const text =
        fallbackAlt && isFilenameAlt(rawAlt) ? fallbackAlt(imageIndex) : rawAlt;
      return (
        <ContentImage
          src={url}
          alt={text}
          className="md-image"
          natural={imageMeta?.[raw] ?? imageMeta?.[url]}
          priority={eagerFirstImage && imageIndex === 1}
        />
      );
    },
    pre: HighlightedPre,
  };

  return (
    <div className="markdown-body typeset-reading">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        urlTransform={(url) => (isSafeMarkdownImageUrl(url) || url.startsWith("#") || url.startsWith("mailto:") ? url : "")}
        components={components}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}
