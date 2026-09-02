const EXT: Record<string, { hljs: string; label: string }> = {
  ts: { hljs: "typescript", label: "TypeScript" },
  tsx: { hljs: "typescript", label: "TSX" },
  js: { hljs: "javascript", label: "JavaScript" },
  jsx: { hljs: "javascript", label: "JSX" },
  mjs: { hljs: "javascript", label: "JavaScript" },
  cjs: { hljs: "javascript", label: "JavaScript" },
  py: { hljs: "python", label: "Python" },
  rs: { hljs: "rust", label: "Rust" },
  go: { hljs: "go", label: "Go" },
  java: { hljs: "java", label: "Java" },
  kt: { hljs: "kotlin", label: "Kotlin" },
  rb: { hljs: "ruby", label: "Ruby" },
  php: { hljs: "php", label: "PHP" },
  css: { hljs: "css", label: "CSS" },
  scss: { hljs: "scss", label: "SCSS" },
  less: { hljs: "less", label: "Less" },
  html: { hljs: "xml", label: "HTML" },
  xml: { hljs: "xml", label: "XML" },
  svg: { hljs: "xml", label: "SVG" },
  json: { hljs: "json", label: "JSON" },
  yml: { hljs: "yaml", label: "YAML" },
  yaml: { hljs: "yaml", label: "YAML" },
  md: { hljs: "markdown", label: "Markdown" },
  mdx: { hljs: "markdown", label: "MDX" },
  markdown: { hljs: "markdown", label: "Markdown" },
  sh: { hljs: "bash", label: "Shell" },
  bash: { hljs: "bash", label: "Shell" },
  zsh: { hljs: "bash", label: "Shell" },
  sql: { hljs: "sql", label: "SQL" },
  toml: { hljs: "ini", label: "TOML" },
  ini: { hljs: "ini", label: "INI" },
  env: { hljs: "ini", label: "ENV" },
  swift: { hljs: "swift", label: "Swift" },
  c: { hljs: "c", label: "C" },
  h: { hljs: "c", label: "C" },
  cpp: { hljs: "cpp", label: "C++" },
  cc: { hljs: "cpp", label: "C++" },
  hpp: { hljs: "cpp", label: "C++" },
  cs: { hljs: "csharp", label: "C#" },
  lua: { hljs: "lua", label: "Lua" },
  r: { hljs: "r", label: "R" },
  vue: { hljs: "xml", label: "Vue" },
  graphql: { hljs: "graphql", label: "GraphQL" },
  dockerfile: { hljs: "bash", label: "Dockerfile" },
};

export function sourceLanguage(path: string): { hljs: string; label: string } {
  const name = path.split("/").pop() || "";
  if (/^dockerfile(\.|$)/i.test(name)) return EXT.dockerfile;
  if (name === "Makefile" || name === "makefile") {
    return { hljs: "makefile", label: "Makefile" };
  }
  const ext = name.includes(".") ? name.split(".").pop()!.toLowerCase() : "";
  return EXT[ext] ?? { hljs: "", label: "" };
}

export function isMarkdownPath(path: string) {
  return /\.(md|markdown|mdx)$/i.test(path.split("/").pop() || "");
}
