"use client";

import { useEffect, useState, type ReactNode } from "react";
import { fenceFromPre } from "@/lib/code-fence";
import { mermaidSourceFromPre } from "@/lib/mermaid-block";
import { useInView } from "@/lib/use-in-view";
import { MermaidDiagram } from "./mermaid-diagram";

function LazyCodeBlock({ lang, text }: { lang: string; text: string }) {
  const { ref, inView } = useInView<HTMLPreElement>();
  const [html, setHtml] = useState<string | null>(null);

  useEffect(() => {
    if (!inView) return;
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
  }, [inView, lang, text]);

  return (
    <pre ref={ref} className="code-block">
      {html ? (
        <code
          className={`hljs${lang ? ` language-${lang}` : ""}`}
          dangerouslySetInnerHTML={{ __html: html }}
        />
      ) : (
        <code className={lang ? `language-${lang}` : undefined}>{text}</code>
      )}
    </pre>
  );
}

export function HighlightedPre({ children }: { children?: ReactNode }) {
  const mermaid = mermaidSourceFromPre(children);
  if (mermaid !== null) return <MermaidDiagram source={mermaid} />;
  const fence = fenceFromPre(children);
  if (!fence) return <pre>{children}</pre>;
  return <LazyCodeBlock lang={fence.lang} text={fence.text} />;
}
