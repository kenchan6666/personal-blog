"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { mermaidSourceFromPre } from "@/lib/mermaid-block";

type Props = {
  source: string;
};

let mermaidReady: Promise<typeof import("mermaid").default> | null = null;

function loadMermaid() {
  if (!mermaidReady) {
    mermaidReady = import("mermaid").then((mod) => {
      const mermaid = mod.default;
      mermaid.initialize({
        startOnLoad: false,
        theme: "neutral",
        securityLevel: "strict",
        fontFamily: "inherit",
      });
      return mermaid;
    });
  }
  return mermaidReady;
}

export function MermaidDiagram({ source }: Props) {
  const reactId = useId().replace(/[^a-zA-Z0-9]/g, "");
  const nonce = useRef(0);
  const [svg, setSvg] = useState("");
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const chart = source.trim();
    setFailed(false);
    setSvg("");
    if (!chart) return;

    const renderId = `mermaid-${reactId}-${++nonce.current}`;
    void loadMermaid()
      .then((mermaid) => mermaid.render(renderId, chart))
      .then(({ svg: next }) => {
        if (!cancelled) setSvg(next);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
    };
  }, [source, reactId]);

  if (failed) {
    return (
      <pre className="mermaid-fallback">
        <code>{source}</code>
      </pre>
    );
  }

  if (!svg) {
    return <div className="mermaid-wrap mermaid-pending" aria-hidden />;
  }

  return (
    <div className="mermaid-wrap" dangerouslySetInnerHTML={{ __html: svg }} />
  );
}

export function MermaidOrPre({ children }: { children?: ReactNode }) {
  const source = mermaidSourceFromPre(children);
  if (source !== null) return <MermaidDiagram source={source} />;
  return <pre>{children}</pre>;
}
