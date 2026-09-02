export function parentPath(path: string) {
  const parts = path.split("/").filter(Boolean);
  parts.pop();
  return parts.join("/");
}

export function resolveRepoPath(href: string, baseDir = ""): string | null {
  if (!href || href.startsWith("#") || href.startsWith("mailto:")) return null;
  if (/^(https?:|data:|\/\/)/i.test(href)) return null;
  const stripped = href.split("#")[0]?.split("?")[0] ?? "";
  if (!stripped) return null;
  const stack = baseDir.split("/").filter(Boolean);
  for (const part of stripped.replace(/^\.\//, "").split("/")) {
    if (!part || part === ".") continue;
    if (part === "..") stack.pop();
    else stack.push(part);
  }
  return stack.join("/");
}

export function githubBlobUrl(
  repoFullName: string,
  refName: string,
  path: string,
) {
  return `https://github.com/${repoFullName}/blob/${refName}/${path}`;
}

export function githubRawUrl(
  repoFullName: string,
  refName: string,
  path: string,
) {
  return `https://raw.githubusercontent.com/${repoFullName}/${refName}/${path}`;
}
