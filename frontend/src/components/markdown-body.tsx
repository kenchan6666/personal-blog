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
import { HighlightedPre } from "./highlighted-pre";

function headingText(children: ReactNode): string {
  return Array.isArray(children)
    ? children.map((child) => (typeof child === "string" ? child : "")).join("")
    : typeof children === "string"
      ? children
      : "";
}

export function MarkdownBody({ source }: { source: string }) {
  const markdown = liftReadmeHtmlImages(source);
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
      <div className="table-scroll">
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
      return <ContentImage src={url} alt={alt ?? ""} className="md-image" />;
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
