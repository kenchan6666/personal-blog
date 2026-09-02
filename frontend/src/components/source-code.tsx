"use client";

import { useEffect, useState } from "react";
import { sourceLanguage } from "@/lib/source-lang";

type Props = {
  path: string;
  text: string;
};

export function SourceCode({ path, text }: Props) {
  const lang = sourceLanguage(path).hljs;
  const [html, setHtml] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void import("highlight.js/lib/common").then((mod) => {
      const hljs = mod.default;
      const result =
        lang && hljs.getLanguage(lang)
          ? hljs.highlight(text, { language: lang, ignoreIllegals: true })
          : hljs.highlightAuto(text);
      if (!cancelled) setHtml(result.value);
    });
    return () => {
      cancelled = true;
    };
  }, [lang, text]);

  const lines = (html ?? escapeHtml(text)).split("\n");

  return (
    <div className="gh-code">
      {lines.map((line, index) => (
        <div key={index} className="gh-line">
          <span className="gh-ln">{index + 1}</span>
          <span
            className="gh-lc hljs"
            dangerouslySetInnerHTML={{ __html: line || " " }}
          />
        </div>
      ))}
    </div>
  );
}

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}
