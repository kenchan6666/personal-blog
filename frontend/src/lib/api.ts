const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export const SESSION_KEY = "portfolio_session_token";

export type Localized = {
  "zh-Hant": string;
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
  links: OwnerLink[];
};

export type PublicLink = {
  label: string;
  url: string;
  order: number;
};

export type PublicSite = {
  brand: string;
  hero: {
    headline: string;
    support: string;
    ctaProjects: string;
    ctaArticles: string;
  };
  profile: {
    bio: string;
    skills: string;
    experience: string;
    publicEmail: string;
    avatarUrl: string;
    links: PublicLink[];
  };
};

export function emptyLocalized(): Localized {
  return { "zh-Hant": "", en: "" };
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
    links: [],
  };
}

export function mediaUrl(path: string): string {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return `${API_BASE}${path}`;
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

export async function fetchPublicSite(locale: string): Promise<PublicSite | null> {
  try {
    const res = await fetch(
      `${API_BASE}/api/public/site?locale=${encodeURIComponent(locale)}`,
      { next: { revalidate: 30 } },
    );
    if (!res.ok) return null;
    return (await res.json()) as PublicSite;
  } catch {
    return null;
  }
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

export type SourceRepo = {
  fullName: string;
  owner: string;
  name: string;
  private: boolean;
  htmlUrl: string;
  defaultBranch: string;
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
  try {
    const res = await fetch(
      `${API_BASE}/api/public/projects?locale=${encodeURIComponent(locale)}`,
      { next: { revalidate: 30 } },
    );
    if (!res.ok) return [];
    return (await res.json()) as PublicProject[];
  } catch {
    return [];
  }
}

export async function fetchPublicProject(
  locale: string,
  slug: string,
): Promise<PublicProject | null> {
  try {
    const res = await fetch(
      `${API_BASE}/api/public/projects/${encodeURIComponent(slug)}?locale=${encodeURIComponent(locale)}`,
      { next: { revalidate: 30 } },
    );
    if (!res.ok) return null;
    return (await res.json()) as PublicProject;
  } catch {
    return null;
  }
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
};

export type PublicArticle = {
  slug: string;
  title: string;
  summary: string;
  body: string;
  order: number;
  relatedProject: RelatedProject | null;
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
  };
}

export async function fetchPublicArticles(
  locale: string,
): Promise<PublicArticle[]> {
  try {
    const res = await fetch(
      `${API_BASE}/api/public/articles?locale=${encodeURIComponent(locale)}`,
      { next: { revalidate: 30 } },
    );
    if (!res.ok) return [];
    return (await res.json()) as PublicArticle[];
  } catch {
    return [];
  }
}

export async function fetchPublicArticle(
  locale: string,
  slug: string,
): Promise<PublicArticle | null> {
  try {
    const res = await fetch(
      `${API_BASE}/api/public/articles/${encodeURIComponent(slug)}?locale=${encodeURIComponent(locale)}`,
      { next: { revalidate: 30 } },
    );
    if (!res.ok) return null;
    return (await res.json()) as PublicArticle;
  } catch {
    return null;
  }
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
  try {
    const res = await fetch(
      `${API_BASE}/api/public/journals?locale=${encodeURIComponent(locale)}`,
      { next: { revalidate: 30 } },
    );
    if (!res.ok) return [];
    return (await res.json()) as PublicJournal[];
  } catch {
    return [];
  }
}

export async function fetchPublicJournal(
  locale: string,
  slug: string,
): Promise<PublicJournal | null> {
  try {
    const res = await fetch(
      `${API_BASE}/api/public/journals/${encodeURIComponent(slug)}?locale=${encodeURIComponent(locale)}`,
      { next: { revalidate: 30 } },
    );
    if (!res.ok) return null;
    return (await res.json()) as PublicJournal;
  } catch {
    return null;
  }
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
