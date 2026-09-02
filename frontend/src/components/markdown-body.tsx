import type { ReactNode } from "react";
import type { Components } from "react-markdown";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { extractMarkdownHeadings } from "@/lib/headings";

function headingText(children: ReactNode): string {
  return Array.isArray(children)
    ? children.map((child) => (typeof child === "string" ? child : "")).join("")
    : typeof children === "string"
      ? children
      : "";
}

export function MarkdownBody({ source }: { source: string }) {
  if (!source.trim()) return null;

  const ids = extractMarkdownHeadings(source).map((heading) => heading.id);
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
  };

  return (
    <div className="markdown-body typeset-reading">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {source}
      </ReactMarkdown>
    </div>
  );
}
