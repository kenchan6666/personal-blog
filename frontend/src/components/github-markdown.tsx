"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Props = {
  source: string;
  repoFullName?: string;
  refName?: string;
};

function rewriteUrl(url: string, repoFullName?: string, refName?: string) {
  if (!url || url.startsWith("#") || url.startsWith("mailto:")) return url;
  if (/^(https?:|data:|\/\/)/i.test(url)) return url;
  if (!repoFullName || !refName) return url;
  const clean = url.replace(/^\.\//, "").replace(/^\//, "");
  return `https://raw.githubusercontent.com/${repoFullName}/${refName}/${clean}`;
}

export function GithubMarkdown({ source, repoFullName, refName }: Props) {
  if (!source.trim()) return null;
  return (
    <div className="gfm">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        urlTransform={(url) => rewriteUrl(url, repoFullName, refName)}
        components={{
          table: ({ children }) => (
            <div className="table-scroll">
              <table>{children}</table>
            </div>
          ),
          a: ({ href, children }) => (
            <a href={href} rel="noreferrer" target="_blank">
              {children}
            </a>
          ),
        }}
      >
        {source}
      </ReactMarkdown>
    </div>
  );
}
