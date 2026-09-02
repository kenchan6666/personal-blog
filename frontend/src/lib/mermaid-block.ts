import { Children, isValidElement, type ReactNode } from "react";

export function mermaidSourceFromPre(children: ReactNode): string | null {
  const items = Children.toArray(children);
  if (items.length !== 1) return null;
  const child = items[0];
  if (!isValidElement<{ className?: string; children?: ReactNode }>(child)) {
    return null;
  }
  if (!/(?:^|\s)language-mermaid(?:\s|$)/i.test(child.props.className ?? "")) {
    return null;
  }
  return Children.toArray(child.props.children)
    .filter((node): node is string => typeof node === "string")
    .join("")
    .replace(/\n$/, "");
}
