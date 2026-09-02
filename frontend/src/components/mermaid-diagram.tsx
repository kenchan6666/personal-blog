"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { mermaidSourceFromPre } from "@/lib/mermaid-block";
import { useInView } from "@/lib/use-in-view";
import { useResolvedTheme } from "@/lib/use-resolved-theme";

type Props = {
  source: string;
};

let mermaidReady: Promise<typeof import("mermaid").default> | null = null;

function loadMermaid() {
  if (!mermaidReady) {
    mermaidReady = import("mermaid").then((mod) => mod.default);
  }
  return mermaidReady;
}

export function MermaidDiagram({ source }: Props) {
  const reactId = useId().replace(/[^a-zA-Z0-9]/g, "");
  const nonce = useRef(0);
  const { ref, inView } = useInView<HTMLDivElement>();
  const theme = useResolvedTheme();
  const [svg, setSvg] = useState("");
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!inView) return;
    let cancelled = false;
    const chart = source.trim();
    setFailed(false);
    setSvg("");
    if (!chart) return;

    const renderId = `mermaid-${reactId}-${++nonce.current}`;
    void loadMermaid()
      .then((mermaid) => {
        mermaid.initialize({
          startOnLoad: false,
          theme: theme === "dark" ? "dark" : "neutral",
          securityLevel: "strict",
          fontFamily: "inherit",
        });
        return mermaid.render(renderId, chart);
      })
      .then(({ svg: next }) => {
        if (!cancelled) setSvg(next);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
    };
  }, [inView, reactId, source, theme]);

  if (failed) {
    return (
      <pre className="mermaid-fallback">
        <code>{source}</code>
      </pre>
    );
  }

  return (
    <div
      ref={ref}
      className={`mermaid-wrap${svg ? "" : " mermaid-pending"}`}
      aria-hidden={!svg}
    >
      {svg ? (
        <div dangerouslySetInnerHTML={{ __html: svg }} />
      ) : null}
    </div>
  );
}

export function MermaidOrPre({ children }: { children?: ReactNode }) {
  const source = mermaidSourceFromPre(children);
  if (source !== null) return <MermaidDiagram source={source} />;
  return <pre>{children}</pre>;
}
