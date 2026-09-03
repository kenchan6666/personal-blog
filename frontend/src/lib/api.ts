import { cache } from "react";

const PUBLIC_API =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const API_BASE =
  typeof window === "undefined"
    ? (process.env.API_INTERNAL_URL ?? PUBLIC_API)
    : (process.env.NEXT_PUBLIC_API_BASE_URL ?? "");

export const SESSION_KEY = "portfolio_session_token";

export type Localized = {
  "zh-Hant": string;
  "zh-Hans": string;
  en: string;
};

export type OwnerLink = {
  label: Localized;
  url: string;
  order: number;
};

export type OwnerSite = {
  brand: Localized;
  heroHeadline: Localized;
  heroSupport: Localized;
  heroCtaProjects: Localized;
  heroCtaArticles: Localized;
  bio: Localized;
  skills: Localized;
  experience: Localized;
  publicEmail: string;
  avatarUrl: string;
  heroVisualUrl: string;
  heroVisualPosX: number;
  heroVisualPosY: number;
  heroVisualScale: number;
  heroVisualBlur: number;
  articlesLead: Localized;
  aboutLead: Localized;
  aboutEmpty: Localized;
  links: OwnerLink[];
};

export type PublicLink = {
  label: string;
  url: string;
  order: number;
};

export type HeroVisual = {
  url: string;
  posX: number;
  posY: number;
  scale: number;
  blur: number;
};

export type PublicSite = {
  brand: string;
  hero: {
    headline: string;
    support: string;
    ctaProjects: string;
    ctaArticles: string;
    visual?: HeroVisual | null;
  };
  profile: {
    bio: string;
    skills: string;
    experience: string;
    publicEmail: string;
    avatarUrl: string;
    links: PublicLink[];
  };
  pages?: {
    articlesLead: string;
    aboutLead: string;
    aboutEmpty: string;
  };
};

export function emptyLocalized(): Localized {
  return { "zh-Hant": "", "zh-Hans": "", en: "" };
}

export function localizedText(value: Localized | undefined, fallback = ""): string {
  if (!value) return fallback;
  return value["zh-Hant"] || value["zh-Hans"] || value.en || fallback;
}

export function emptyOwnerSite(): OwnerSite {
  return {
    brand: emptyLocalized(),
    heroHeadline: emptyLocalized(),
    heroSupport: emptyLocalized(),
    heroCtaProjects: emptyLocalized(),
    heroCtaArticles: emptyLocalized(),
    bio: emptyLocalized(),
    skills: emptyLocalized(),
    experience: emptyLocalized(),
    publicEmail: "",
    avatarUrl: "",
    heroVisualUrl: "",
    heroVisualPosX: 50,
    heroVisualPosY: 50,
    heroVisualScale: 100,
    heroVisualBlur: 0,
    articlesLead: emptyLocalized(),
    aboutLead: emptyLocalized(),
    aboutEmpty: emptyLocalized(),
    links: [],
  };
}

export function mediaUrl(path: string): string {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return `${PUBLIC_API}${path}`;
}

export function getSessionToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(SESSION_KEY);
}

export function setSessionToken(token: string) {
  window.localStorage.setItem(SESSION_KEY, token);
}

export function clearSessionToken() {
  window.localStorage.removeItem(SESSION_KEY);
}

export class PublicApiError extends Error {
  status: number;
  constructor(status: number, message = "public_api_error") {
    super(message);
    this.status = status;
  }
}

const PUBLIC_FETCH_MS = 8_000;

function publicFetch(url: string, init?: RequestInit) {
  return fetch(url, {
    ...init,
    signal: AbortSignal.timeout(PUBLIC_FETCH_MS),
  });
}

async function publicJson<T>(url: string): Promise<T> {
  const res = await publicFetch(url, { cache: "no-store" });
  if (!res.ok) throw new PublicApiError(res.status);
  return (await res.json()) as T;
}

async function publicJsonOrNull<T>(url: string): Promise<T | null> {
  const res = await publicFetch(url, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new PublicApiError(res.status);
  return (await res.json()) as T;
}

async function publicJsonLive<T>(url: string): Promise<T> {
  const res = await publicFetch(url, { cache: "no-store" });
  if (!res.ok) throw new PublicApiError(res.status);
  return (await res.json()) as T;
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") return data.detail;
  } catch {
    /* ignore */
  }
  return `http_${res.status}`;
}

export async function requestOtp(email: string) {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/auth/otp/request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
  } catch {
    throw new Error("Failed to fetch");
  }
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function verifyOtp(email: string, code: string) {
  const res = await fetch(`${API_BASE}/api/auth/otp/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, code }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<{ session_token: string }>;
}

export async function fetchMe(token: string) {
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<{ email: string; role: string }>;
}

export const fetchPublicSite = cache(async function fetchPublicSite(
  locale: string,
): Promise<PublicSite> {
  return publicJson<PublicSite>(
    `${API_BASE}/api/public/site?locale=${encodeURIComponent(locale)}`,
  );
});

export type PublicGuideMessage = {
  role: "user" | "assistant";
  content: string;
};

const PUBLIC_GUIDE_VISITOR_KEY = "portfolio_public_guide_visitor";

function publicGuideVisitorId(): string {
  if (typeof window === "undefined") return "";
  let value = window.localStorage.getItem(PUBLIC_GUIDE_VISITOR_KEY);
  if (!value) {
    value = window.crypto.randomUUID();
    window.localStorage.setItem(PUBLIC_GUIDE_VISITOR_KEY, value);
  }
  return value;
}

export async function streamPublicGuide(
  locale: string,
  question: string,
  history: PublicGuideMessage[],
  onDelta: (text: string) => void,
): Promise<string> {
  const response = await fetch(`${API_BASE}/api/public/guide/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Visitor-ID": publicGuideVisitorId(),
    },
    body: JSON.stringify({
      locale,
      question,
      history: history.slice(-6),
    }),
  });
  if (!response.ok || !response.body) {
    throw new Error(await parseError(response));
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let complete = "";
  let streamError = "";

  function consume(block: string) {
    const lines = block.split(/\r?\n/);
    const event = lines.find((line) => line.startsWith("event:"))?.slice(6).trim();
    const data = lines
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data || data === "[DONE]") return;
    try {
      const payload = JSON.parse(data);
      if (event === "error") {
        streamError = payload.message || "public_agent_unavailable";
        return;
      }
      const delta = payload.choices?.[0]?.delta?.content;
      if (typeof delta === "string" && delta) {
        complete += delta;
        onDelta(delta);
      }
    } catch {
      /* Ignore incomplete upstream metadata. */
    }
  }

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() ?? "";
    for (const block of blocks) consume(block);
    if (done) break;
  }
  if (buffer.trim()) consume(buffer);
  if (streamError) throw new Error(streamError);
  return complete;
}

export async function fetchOwnerSite(token: string): Promise<OwnerSite> {
  const res = await fetch(`${API_BASE}/api/owner/site`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerSite;
}

export async function saveOwnerSite(
  token: string,
  body: OwnerSite,
): Promise<OwnerSite> {
  const res = await fetch(`${API_BASE}/api/owner/site`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerSite;
}

export async function uploadOwnerAvatar(
  token: string,
  file: File,
): Promise<{ avatarUrl: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/owner/avatar`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as { avatarUrl: string };
}

export async function uploadOwnerHeroVisual(
  token: string,
  file: File,
): Promise<OwnerSite> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/owner/hero-visual`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerSite;
}

export async function clearOwnerHeroVisual(token: string): Promise<OwnerSite> {
  const res = await fetch(`${API_BASE}/api/owner/hero-visual`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerSite;
}

export async function uploadOwnerMedia(
  token: string,
  file: File,
): Promise<{ url: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/owner/media`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as { url: string };
}

export type TranslateResult = Localized & {
  source: string;
  warnings: string[];
};

export async function translateOwnerLocalized(
  token: string,
  value: Localized,
): Promise<TranslateResult> {
  const res = await fetch(`${API_BASE}/api/owner/translate`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ ...value, overwrite: true }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as TranslateResult;
}

export type SourceRepo = {
  fullName: string;
  owner: string;
  name: string;
  private: boolean;
  htmlUrl: string;
  defaultBranch: string;
  description?: string;
};

export type OwnerProject = {
  id: string;
  slug: string;
  title: Localized;
  summary: Localized;
  body: Localized;
  status: "draft" | "published";
  order: number;
  sourceRepo: SourceRepo | null;
};

export type PublicProject = {
  slug: string;
  title: string;
  summary: string;
  body: string;
  order: number;
  sourceRepo: SourceRepo | null;
};

export function emptyOwnerProject(): OwnerProject {
  return {
    id: "",
    slug: "",
    title: emptyLocalized(),
    summary: emptyLocalized(),
    body: emptyLocalized(),
    status: "draft",
    order: 0,
    sourceRepo: null,
  };
}

export async function fetchPublicProjects(
  locale: string,
): Promise<PublicProject[]> {
  return publicJson<PublicProject[]>(
    `${API_BASE}/api/public/projects?locale=${encodeURIComponent(locale)}`,
  );
}

export async function fetchPublicProject(
  locale: string,
  slug: string,
): Promise<PublicProject | null> {
  return publicJsonOrNull<PublicProject>(
    `${API_BASE}/api/public/projects/${encodeURIComponent(slug)}?locale=${encodeURIComponent(locale)}`,
  );
}

export type SourceTreeEntry = {
  name: string;
  path: string;
  type: "file" | "dir";
};

export type PublicSourceOverview = {
  defaultBranch: string;
  ref: string;
  branches: string[];
  readme: { path: string; content: string };
  tree: SourceTreeEntry[];
};

export async function fetchPublicSource(
  slug: string,
  ref?: string,
): Promise<PublicSourceOverview | null> {
  const params = ref ? `?ref=${encodeURIComponent(ref)}` : "";
  try {
    const res = await fetch(
      `${API_BASE}/api/public/projects/${encodeURIComponent(slug)}/source${params}`,
      { cache: "no-store" },
    );
    if (!res.ok) return null;
    return (await res.json()) as PublicSourceOverview;
  } catch {
    return null;
  }
}

export async function fetchPublicSourceTree(
  slug: string,
  ref: string,
  path: string,
): Promise<SourceTreeEntry[]> {
  const params = new URLSearchParams({ ref, path });
  const res = await fetch(
    `${API_BASE}/api/public/projects/${encodeURIComponent(slug)}/source/tree?${params}`,
    { cache: "no-store" },
  );
  if (!res.ok) return [];
  const data = (await res.json()) as { tree: SourceTreeEntry[] };
  return data.tree;
}

export async function fetchPublicSourceBlob(
  slug: string,
  ref: string,
  path: string,
): Promise<{ path: string; content: string } | null> {
  const params = new URLSearchParams({ ref, path });
  const res = await fetch(
    `${API_BASE}/api/public/projects/${encodeURIComponent(slug)}/source/blob?${params}`,
    { cache: "no-store" },
  );
  if (!res.ok) return null;
  return (await res.json()) as { path: string; content: string };
}

export async function fetchOwnerProjects(
  token: string,
): Promise<OwnerProject[]> {
  const res = await fetch(`${API_BASE}/api/owner/projects`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerProject[];
}

export async function createOwnerProject(
  token: string,
  body: Omit<OwnerProject, "id" | "sourceRepo">,
): Promise<OwnerProject> {
  const res = await fetch(`${API_BASE}/api/owner/projects`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerProject;
}

export async function saveOwnerProject(
  token: string,
  id: string,
  body: Omit<OwnerProject, "id" | "sourceRepo">,
): Promise<OwnerProject> {
  const res = await fetch(`${API_BASE}/api/owner/projects/${id}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerProject;
}

export async function startGitHubOAuth(
  token: string,
): Promise<{ authorizationUrl: string }> {
  const res = await fetch(`${API_BASE}/api/owner/github/oauth/start`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as { authorizationUrl: string };
}

export async function fetchOwnerGitHubRepos(
  token: string,
): Promise<SourceRepo[] | null> {
  const res = await fetch(`${API_BASE}/api/owner/github/repos`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (res.status === 409) return null;
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as SourceRepo[];
}

export async function attachOwnerSourceRepo(
  token: string,
  projectId: string,
  fullName: string,
): Promise<OwnerProject> {
  const res = await fetch(
    `${API_BASE}/api/owner/projects/${projectId}/source-repo`,
    {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ fullName }),
    },
  );
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerProject;
}

export type RelatedProject = {
  slug: string;
  title: string;
};

export type OwnerArticle = {
  id: string;
  slug: string;
  title: Localized;
  summary: Localized;
  body: Localized;
  status: "draft" | "published";
  order: number;
  relatedProjectSlug: string;
  categorySlug: string;
};

export type PublicArticle = {
  slug: string;
  title: string;
  summary: string;
  body: string;
  order: number;
  relatedProject: RelatedProject | null;
  categorySlug: string;
  categoryTitle: string;
  publishedAt: string;
  wordCount: number;
  readingMinutes: number;
};

export type OwnerArticleCategory = {
  id: string;
  slug: string;
  title: Localized;
  order: number;
  protected: boolean;
};

export type PublicArticleCategory = {
  slug: string;
  title: string;
  order: number;
};

export function emptyOwnerArticle(): OwnerArticle {
  return {
    id: "",
    slug: "",
    title: emptyLocalized(),
    summary: emptyLocalized(),
    body: emptyLocalized(),
    status: "draft",
    order: 0,
    relatedProjectSlug: "",
    categorySlug: "",
  };
}

function pathSegment(value: string): string {
  return value.trim().replace(/^\/+|\/+$/g, "");
}

export function articleHref(
  locale: string,
  article: { categorySlug: string; slug: string },
): string {
  const slug = pathSegment(article.slug);
  const category = pathSegment(article.categorySlug || "");
  if (!category) return `/${locale}/articles/${slug}`;
  return `/${locale}/articles/${category}/${slug}`;
}

export async function fetchPublicArticles(
  locale: string,
): Promise<PublicArticle[]> {
  return publicJson<PublicArticle[]>(
    `${API_BASE}/api/public/articles?locale=${encodeURIComponent(locale)}`,
  );
}

export async function fetchPublicArticle(
  locale: string,
  slug: string,
): Promise<PublicArticle | null> {
  return publicJsonOrNull<PublicArticle>(
    `${API_BASE}/api/public/articles/${encodeURIComponent(slug)}?locale=${encodeURIComponent(locale)}`,
  );
}

export async function fetchPublicArticleCategories(
  locale: string,
): Promise<PublicArticleCategory[]> {
  return publicJson<PublicArticleCategory[]>(
    `${API_BASE}/api/public/article-categories?locale=${encodeURIComponent(locale)}`,
  );
}

export async function fetchOwnerArticleCategories(
  token: string,
): Promise<OwnerArticleCategory[]> {
  const res = await fetch(`${API_BASE}/api/owner/article-categories`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerArticleCategory[];
}

export async function createOwnerArticleCategory(
  token: string,
  body: { slug: string; title: Localized; order: number },
): Promise<OwnerArticleCategory> {
  const res = await fetch(`${API_BASE}/api/owner/article-categories`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerArticleCategory;
}

export async function saveOwnerArticleCategory(
  token: string,
  id: string,
  body: { slug: string; title: Localized; order: number },
): Promise<OwnerArticleCategory> {
  const res = await fetch(`${API_BASE}/api/owner/article-categories/${id}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerArticleCategory;
}

export async function deleteOwnerArticleCategory(
  token: string,
  id: string,
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/owner/article-categories/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(await parseError(res));
}

export async function fetchOwnerArticles(
  token: string,
): Promise<OwnerArticle[]> {
  const res = await fetch(`${API_BASE}/api/owner/articles`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerArticle[];
}

export async function createOwnerArticle(
  token: string,
  body: Omit<OwnerArticle, "id">,
): Promise<OwnerArticle> {
  const res = await fetch(`${API_BASE}/api/owner/articles`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerArticle;
}

export async function saveOwnerArticle(
  token: string,
  id: string,
  body: Omit<OwnerArticle, "id">,
): Promise<OwnerArticle> {
  const res = await fetch(`${API_BASE}/api/owner/articles/${id}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerArticle;
}

export async function deleteOwnerArticle(
  token: string,
  id: string,
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/owner/articles/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(await parseError(res));
}

export type OwnerJournal = {
  id: string;
  slug: string;
  title: Localized;
  summary: Localized;
  body: Localized;
  status: "draft" | "published";
  order: number;
};

export type PublicJournal = {
  slug: string;
  title: string;
  summary: string;
  body: string;
  order: number;
  publishedAt: string;
  wordCount: number;
  readingMinutes: number;
};

export function emptyOwnerJournal(): OwnerJournal {
  return {
    id: "",
    slug: "",
    title: emptyLocalized(),
    summary: emptyLocalized(),
    body: emptyLocalized(),
    status: "draft",
    order: 0,
  };
}

export async function fetchPublicJournals(
  locale: string,
): Promise<PublicJournal[]> {
  return publicJson<PublicJournal[]>(
    `${API_BASE}/api/public/journals?locale=${encodeURIComponent(locale)}`,
  );
}

export async function fetchPublicJournal(
  locale: string,
  slug: string,
): Promise<PublicJournal | null> {
  return publicJsonOrNull<PublicJournal>(
    `${API_BASE}/api/public/journals/${encodeURIComponent(slug)}?locale=${encodeURIComponent(locale)}`,
  );
}

export async function fetchOwnerJournals(
  token: string,
): Promise<OwnerJournal[]> {
  const res = await fetch(`${API_BASE}/api/owner/journals`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerJournal[];
}

export async function createOwnerJournal(
  token: string,
  body: Omit<OwnerJournal, "id">,
): Promise<OwnerJournal> {
  const res = await fetch(`${API_BASE}/api/owner/journals`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerJournal;
}

export async function saveOwnerJournal(
  token: string,
  id: string,
  body: Omit<OwnerJournal, "id">,
): Promise<OwnerJournal> {
  const res = await fetch(`${API_BASE}/api/owner/journals/${id}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerJournal;
}

export async function deleteOwnerJournal(
  token: string,
  id: string,
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/owner/journals/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(await parseError(res));
}

export type PublicComment = {
  id: string;
  displayName: string;
  body: string;
  ownerReply: string;
};

export type OwnerComment = PublicComment & {
  email: string;
  status: "pending" | "approved" | "rejected";
  targetType: "article" | "journal";
  targetSlug: string;
};

export async function fetchPublicComments(
  kind: "articles" | "journals",
  slug: string,
): Promise<PublicComment[]> {
  return publicJsonLive<PublicComment[]>(
    `${API_BASE}/api/public/${kind}/${encodeURIComponent(slug)}/comments`,
  );
}

export async function submitPublicComment(
  kind: "articles" | "journals",
  slug: string,
  body: { displayName: string; email: string; body: string },
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/public/${kind}/${encodeURIComponent(slug)}/comments`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
  if (!res.ok) throw new Error(await parseError(res));
}

export async function fetchOwnerComments(
  token: string,
): Promise<OwnerComment[]> {
  const res = await fetch(`${API_BASE}/api/owner/comments`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerComment[];
}

export async function moderateOwnerComment(
  token: string,
  id: string,
  action: "approve" | "reject",
): Promise<OwnerComment> {
  const res = await fetch(`${API_BASE}/api/owner/comments/${id}/${action}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerComment;
}

export async function replyOwnerComment(
  token: string,
  id: string,
  body: string,
): Promise<OwnerComment> {
  const res = await fetch(`${API_BASE}/api/owner/comments/${id}/reply`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ body }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerComment;
}

export type AboutKind =
  | "summary"
  | "education"
  | "achievement"
  | "experience"
  | "custom";

export type OwnerAboutModule = {
  id: string;
  slug: string;
  kind: AboutKind;
  title: Localized;
  body: Localized;
  status: "draft" | "published";
  order: number;
};

export type PublicAboutModule = {
  slug: string;
  kind: AboutKind;
  title: string;
  body: string;
  order: number;
};

export function emptyOwnerAboutModule(): OwnerAboutModule {
  return {
    id: "",
    slug: "",
    kind: "custom",
    title: emptyLocalized(),
    body: emptyLocalized(),
    status: "draft",
    order: 0,
  };
}

export async function fetchPublicAbout(
  locale: string,
): Promise<PublicAboutModule[]> {
  return publicJson<PublicAboutModule[]>(
    `${API_BASE}/api/public/about?locale=${encodeURIComponent(locale)}`,
  );
}

export async function fetchOwnerAboutModules(
  token: string,
): Promise<OwnerAboutModule[]> {
  const res = await fetch(`${API_BASE}/api/owner/about-modules`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerAboutModule[];
}

export async function createOwnerAboutModule(
  token: string,
  body: Omit<OwnerAboutModule, "id">,
): Promise<OwnerAboutModule> {
  const res = await fetch(`${API_BASE}/api/owner/about-modules`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerAboutModule;
}

export async function saveOwnerAboutModule(
  token: string,
  id: string,
  body: Omit<OwnerAboutModule, "id">,
): Promise<OwnerAboutModule> {
  const res = await fetch(`${API_BASE}/api/owner/about-modules/${id}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return (await res.json()) as OwnerAboutModule;
}

export async function deleteOwnerAboutModule(
  token: string,
  id: string,
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/owner/about-modules/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(await parseError(res));
}

export type AgentMessage = {
  role: "user" | "assistant";
  content: string;
  files: string[];
  createdAt: string;
};

export type AgentConversationSummary = {
  id: string;
  title: string;
  preview: string;
  messageCount: number;
  thinking?: boolean;
  createdAt: string;
  updatedAt: string;
};

export type AgentConversation = AgentConversationSummary & {
  messages: AgentMessage[];
};

export type AgentKnowledge = {
  id: string;
  title: string;
  category: string;
  content: string;
  tags: string[];
  order: number;
  vectorSynced: boolean;
  vectorSyncError: string;
  createdAt: string;
  updatedAt: string;
};

export type AgentKnowledgeInput = {
  title: string;
  category: string;
  content: string;
  tags: string[];
  order: number;
};

export type AgentStreamEvent =
  | {
      type: "knowledge_updated";
      changedIds: string[];
      items: AgentKnowledge[];
    }
  | {
      type: "tool_activity";
      label: string;
    };

async function ownerAgentJson<T>(
  token: string,
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) throw new Error(await parseError(response));
  return (await response.json()) as T;
}

export function listAgentConversations(token: string) {
  return ownerAgentJson<AgentConversationSummary[]>(
    token,
    "/api/owner/agent/conversations",
  );
}

export function createAgentConversation(token: string, title = "新对话") {
  return ownerAgentJson<AgentConversation>(
    token,
    "/api/owner/agent/conversations",
    { method: "POST", body: JSON.stringify({ title }) },
  );
}

export function getAgentConversation(token: string, id: string) {
  return ownerAgentJson<AgentConversation>(
    token,
    `/api/owner/agent/conversations/${id}`,
  );
}

export function renameAgentConversation(
  token: string,
  id: string,
  title: string,
) {
  return ownerAgentJson<AgentConversationSummary>(
    token,
    `/api/owner/agent/conversations/${id}`,
    { method: "PATCH", body: JSON.stringify({ title }) },
  );
}

export async function deleteAgentConversation(token: string, id: string) {
  await ownerAgentJson<{ ok: boolean }>(
    token,
    `/api/owner/agent/conversations/${id}`,
    { method: "DELETE" },
  );
}

export function listAgentKnowledge(token: string) {
  return ownerAgentJson<AgentKnowledge[]>(
    token,
    "/api/owner/agent/knowledge",
  );
}

export function createAgentKnowledge(
  token: string,
  input: AgentKnowledgeInput,
) {
  return ownerAgentJson<AgentKnowledge>(
    token,
    "/api/owner/agent/knowledge",
    { method: "POST", body: JSON.stringify(input) },
  );
}

export function updateAgentKnowledge(
  token: string,
  id: string,
  input: AgentKnowledgeInput,
) {
  return ownerAgentJson<AgentKnowledge>(
    token,
    `/api/owner/agent/knowledge/${id}`,
    { method: "PUT", body: JSON.stringify(input) },
  );
}

export async function deleteAgentKnowledge(token: string, id: string) {
  await ownerAgentJson<{ ok: boolean }>(
    token,
    `/api/owner/agent/knowledge/${id}`,
    { method: "DELETE" },
  );
}

export function syncAgentKnowledge(token: string, id: string) {
  return ownerAgentJson<AgentKnowledge>(
    token,
    `/api/owner/agent/knowledge/${id}/sync`,
    { method: "POST" },
  );
}

export function syncAllAgentKnowledge(token: string) {
  return ownerAgentJson<AgentKnowledge[]>(
    token,
    "/api/owner/agent/knowledge/sync",
    { method: "POST" },
  );
}

export async function streamOwnerAgent(
  token: string,
  conversationId: string,
  message: string,
  context: string,
  files: File[],
  onDelta: (text: string) => void,
  onEvent?: (event: AgentStreamEvent) => void,
): Promise<string> {
  let body: BodyInit;
  let headers: HeadersInit = { Authorization: `Bearer ${token}` };
  if (files.length) {
    const form = new FormData();
    form.append("message", message);
    form.append("conversation_id", conversationId);
    if (context) form.append("context", context);
    for (const file of files) form.append("files", file);
    body = form;
  } else {
    headers = { ...headers, "Content-Type": "application/json" };
    body = JSON.stringify({
      message,
      context,
      conversation_id: conversationId,
    });
  }

  const response = await fetch(`${API_BASE}/api/owner/agent/chat`, {
    method: "POST",
    headers,
    body,
  });
  if (!response.ok || !response.body) throw new Error(await parseError(response));

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let complete = "";
  let streamError = "";

  function consume(block: string) {
    const lines = block.split(/\r?\n/);
    const event = lines.find((line) => line.startsWith("event:"))?.slice(6).trim();
    const data = lines
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data || data === "[DONE]") return;
    try {
      const payload = JSON.parse(data);
      if (event === "error") {
        streamError = payload.message || "agent_error";
        return;
      }
      if (event === "knowledge_updated") {
        onEvent?.({
          type: "knowledge_updated",
          changedIds: Array.isArray(payload.changedIds)
            ? payload.changedIds.filter(
                (value: unknown): value is string => typeof value === "string",
              )
            : [],
          items: Array.isArray(payload.items)
            ? (payload.items as AgentKnowledge[])
            : [],
        });
        return;
      }
      if (event === "tool_activity") {
        const label =
          typeof payload.label === "string" ? payload.label.trim() : "";
        if (label) {
          onEvent?.({ type: "tool_activity", label });
        }
        return;
      }
      const delta = payload.choices?.[0]?.delta?.content;
      if (typeof delta === "string" && delta) {
        complete += delta;
        onDelta(delta);
      }
    } catch {
      /* Ignore incomplete or non-JSON SSE metadata. */
    }
  }

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() ?? "";
    for (const block of blocks) consume(block);
    if (done) break;
  }
  if (buffer.trim()) consume(buffer);
  if (streamError) throw new Error(streamError);
  return complete;
}
