import { Children, isValidElement, type ReactNode } from "react";

export function fenceFromPre(
  children: ReactNode,
): { lang: string; text: string } | null {
  const items = Children.toArray(children);
  if (items.length !== 1) return null;
  const child = items[0];
  if (!isValidElement<{ className?: string; children?: ReactNode }>(child)) {
    return null;
  }
  const lang =
    (child.props.className ?? "").match(
      /(?:^|\s)language-([a-z0-9_+-]+)/i,
    )?.[1] ?? "";
  const text = Children.toArray(child.props.children)
    .filter((node): node is string => typeof node === "string")
    .join("")
    .replace(/\n$/, "");
  return { lang, text };
}
