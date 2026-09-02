"use client";

import type { MouseEvent } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { githubBlobUrl, githubRawUrl, resolveRepoPath } from "@/lib/repo-path";
import { isBadgeImage, liftReadmeHtmlImages } from "@/lib/readme-html";
import { ContentImage } from "./content-image";
import { HighlightedPre } from "./highlighted-pre";

type Props = {
  source: string;
  repoFullName?: string;
  refName?: string;
  baseDir?: string;
  onRepoPath?: (path: string) => void;
};

export function GithubMarkdown({
  source,
  repoFullName,
  refName,
  baseDir = "",
  onRepoPath,
}: Props) {
  const markdown = liftReadmeHtmlImages(source);
  if (!markdown.trim()) return null;

  function imageSrc(src: string) {
    const url = src.trim();
    if (!url) return "";
    if (/^(https?:|data:|\/\/)/i.test(url)) return url;
    const path = resolveRepoPath(url, baseDir);
    if (path && repoFullName && refName) {
      return githubRawUrl(repoFullName, refName, path);
    }
    return url;
  }

  return (
    <div className="gfm">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        urlTransform={(url) => url}
        components={{
          table: ({ children }) => (
            <div className="table-scroll">
              <table>{children}</table>
            </div>
          ),
          a: ({ href, children }) => {
            const raw = href ?? "";
            const repoPath = resolveRepoPath(raw, baseDir);
            if (repoPath) {
              const path = repoPath;
              const external =
                repoFullName && refName
                  ? githubBlobUrl(repoFullName, refName, path)
                  : `#${path}`;
              function openFile(event: MouseEvent<HTMLAnchorElement>) {
                if (!onRepoPath) return;
                event.preventDefault();
                onRepoPath(path);
              }
              return (
                <a
                  href={external}
                  onClick={openFile}
                  {...(onRepoPath
                    ? {}
                    : { rel: "noreferrer", target: "_blank" })}
                >
                  {children}
                </a>
              );
            }
            const external =
              raw.startsWith("http://") || raw.startsWith("https://");
            return (
              <a
                href={raw}
                {...(external ? { rel: "noreferrer", target: "_blank" } : {})}
              >
                {children}
              </a>
            );
          },
          img: ({ src, alt }) => {
            const url = typeof src === "string" ? imageSrc(src) : "";
            if (!url) return null;
            if (isBadgeImage(url)) {
              return <img src={url} alt={alt ?? ""} className="md-badge" />;
            }
            return (
              <ContentImage src={url} alt={alt ?? ""} className="md-image" />
            );
          },
          pre: HighlightedPre,
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}
