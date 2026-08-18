import type { ReactNode } from "react";

function inline(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern =
    /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let key = 0;
  while ((match = pattern.exec(text))) {
    if (match.index > last) {
      nodes.push(text.slice(last, match.index));
    }
    const token = match[0];
    if (token.startsWith("**")) {
      nodes.push(<strong key={key}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("`")) {
      nodes.push(
        <code
          key={key}
          className="rounded bg-white/10 px-1 py-0.5 font-mono text-sm"
        >
          {token.slice(1, -1)}
        </code>,
      );
    } else {
      const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);
      const href = link?.[2] ?? "";
      const safe =
        href.startsWith("http://") ||
        href.startsWith("https://") ||
        href.startsWith("/");
      nodes.push(
        safe ? (
          <a
            key={key}
            href={href}
            className="text-[var(--accent-link)] underline underline-offset-4"
          >
            {link?.[1]}
          </a>
        ) : (
          token
        ),
      );
    }
    key += 1;
    last = match.index + token.length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

function isHeading(line: string): boolean {
  return /^#{1,3} /.test(line);
}

function isListItem(line: string): boolean {
  return /^[-*] /.test(line);
}

export function MarkdownBody({ source }: { source: string }) {
  if (!source.trim()) return null;
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    if (line.trim() === "") {
      i += 1;
      continue;
    }
    if (line.startsWith("### ")) {
      blocks.push(
        <h3 key={i} className="display-font text-xl font-bold">
          {inline(line.slice(4))}
        </h3>,
      );
      i += 1;
      continue;
    }
    if (line.startsWith("## ")) {
      blocks.push(
        <h2 key={i} className="display-font text-2xl font-bold">
          {inline(line.slice(3))}
        </h2>,
      );
      i += 1;
      continue;
    }
    if (line.startsWith("# ")) {
      blocks.push(
        <h1 key={i} className="display-font text-3xl font-bold">
          {inline(line.slice(2))}
        </h1>,
      );
      i += 1;
      continue;
    }
    if (isListItem(line)) {
      const items: ReactNode[] = [];
      const start = i;
      while (i < lines.length && isListItem(lines[i])) {
        items.push(
          <li key={i}>{inline(lines[i].replace(/^[-*] /, ""))}</li>,
        );
        i += 1;
      }
      blocks.push(
        <ul key={start} className="list-disc space-y-1 pl-5">
          {items}
        </ul>,
      );
      continue;
    }
    const para: string[] = [];
    const start = i;
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !isHeading(lines[i]) &&
      !isListItem(lines[i])
    ) {
      para.push(lines[i]);
      i += 1;
    }
    blocks.push(
      <p key={start} className="whitespace-pre-wrap">
        {inline(para.join("\n"))}
      </p>,
    );
  }

  return (
    <div className="markdown-body max-w-[70ch] space-y-4 text-base leading-relaxed text-[var(--text-primary)]">
      {blocks}
    </div>
  );
}
