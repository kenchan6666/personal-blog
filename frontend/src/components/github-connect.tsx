"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import {
  ensureOwnerCvRepo,
  fetchOwnerGitHubAccount,
  fetchOwnerGitHubRepos,
  getSessionToken,
  startGitHubOAuth,
  type GitHubAccount,
  type SourceRepo,
} from "@/lib/api";
import { CmsCard } from "./cms-card";

type Props = {
  locale: Locale;
  dict: Dictionary;
};

export function GitHubConnect({ locale, dict }: Props) {
  const a = dict.admin;
  const router = useRouter();
  const params = useSearchParams();
  const [account, setAccount] = useState<GitHubAccount>({ connected: false });
  const [repos, setRepos] = useState<SourceRepo[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<"ok" | "err" | "vault" | null>(null);

  async function reload(token: string) {
    const nextAccount = await fetchOwnerGitHubAccount(token);
    setAccount(nextAccount);
    if (!nextAccount.connected) {
      setRepos([]);
      return nextAccount;
    }
    const nextRepos = await fetchOwnerGitHubRepos(token);
    setRepos(nextRepos ?? []);
    return nextAccount;
  }

  useEffect(() => {
    const token = getSessionToken();
    if (!token) return;
    reload(token)
      .catch(() => setError(a.errorGeneric))
      .finally(() => setLoading(false));
  }, [a.errorGeneric]);

  useEffect(() => {
    const flag = params.get("github");
    if (flag === "connected") setFlash("ok");
    if (flag === "error") setFlash("err");
    if (flag) router.replace(`/${locale}/admin?tab=github`);
  }, [params, locale, router]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return repos;
    return repos.filter(
      (repo) =>
        repo.fullName.toLowerCase().includes(q) ||
        (repo.description ?? "").toLowerCase().includes(q),
    );
  }, [query, repos]);

  async function onConnect() {
    const token = getSessionToken();
    if (!token) return;
    setError(null);
    try {
      const { authorizationUrl } = await startGitHubOAuth(token);
      window.location.href = authorizationUrl;
    } catch (err) {
      const text = err instanceof Error ? err.message : "";
      setError(
        text === "github_not_configured"
          ? a.errorGithubNotConfigured
          : a.errorGeneric,
      );
    }
  }

  async function onCreateVault() {
    const token = getSessionToken();
    if (!token) return;
    setWorking(true);
    setError(null);
    try {
      await ensureOwnerCvRepo(token);
      await reload(token);
      setFlash("vault");
    } catch {
      setError(a.errorGeneric);
    } finally {
      setWorking(false);
    }
  }

  const connected = account.connected;
  const login = account.login || "";
  const hint = loading
    ? a.verifying
    : connected
      ? a.githubConnectedHint
          .replace("{login}", login)
          .replace("{count}", String(account.repoCount ?? repos.length))
      : a.githubDisconnectedHint;

  return (
    <div className="grid gap-5">
      <CmsCard
        title={a.githubTitle}
        action={
          connected ? (
            <span className="status-pill status-pill-live">{a.githubConnected}</span>
          ) : (
            <button type="button" className="btn-cta" onClick={() => void onConnect()}>
              {a.connectGitHub}
            </button>
          )
        }
      >
        <p className="text-sm text-[var(--text-muted)]">{hint}</p>
        <p className="mt-2 text-sm text-[var(--text-muted)]">{a.githubWorkspaceHint}</p>
        {flash === "ok" ? (
          <p className="mt-3 text-sm text-[var(--text-muted)]">{a.githubConnected}</p>
        ) : null}
        {flash === "err" ? (
          <p className="mt-3 text-sm text-[var(--danger)]">{a.errorGeneric}</p>
        ) : null}
        {error ? <p className="mt-3 text-sm text-[var(--danger)]">{error}</p> : null}
      </CmsCard>

      {connected ? (
        <CmsCard
          title={a.githubAccount}
          action={
            <button type="button" className="btn-ghost text-sm" onClick={() => void onConnect()}>
              {a.githubReconnect}
            </button>
          }
        >
          <div className="flex flex-wrap items-center gap-4">
            {account.avatarUrl ? (
              <img
                src={account.avatarUrl}
                alt={login}
                width={48}
                height={48}
                className="h-12 w-12 rounded-full border border-[var(--hairline)]"
              />
            ) : null}
            <div>
              <p className="font-semibold">{account.name || login}</p>
              <p className="font-mono text-sm text-[var(--text-muted)]">{login}</p>
            </div>
            {account.htmlUrl ? (
              <a
                href={account.htmlUrl}
                target="_blank"
                rel="noreferrer"
                className="btn-ghost text-sm"
              >
                {a.githubOpenProfile}
              </a>
            ) : null}
          </div>
        </CmsCard>
      ) : null}

      {connected ? (
        <CmsCard
          title={a.githubCvVault}
          action={
            account.cvRepo ? (
              <span className="status-pill status-pill-live">
                {account.cvRepo.private ? a.githubCvPrivate : a.githubCvPublic}
              </span>
            ) : (
              <button
                type="button"
                className="btn-cta"
                disabled={working}
                onClick={() => void onCreateVault()}
              >
                {working ? a.githubCvCreating : a.githubCvCreate}
              </button>
            )
          }
        >
          {account.cvRepo ? (
            <div className="grid gap-3">
              {flash === "vault" ? (
                <p className="text-sm text-[var(--text-muted)]">{a.githubCvReady}</p>
              ) : null}
              <p className="font-mono text-sm">{account.cvRepo.fullName}</p>
              <div className="flex flex-wrap gap-2">
                <a
                  href={account.cvRepo.htmlUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-ghost text-sm"
                >
                  {a.githubOpenRepo}
                </a>
              </div>
              {account.cvRepo.files.length > 0 ? (
                <ul className="grid gap-1">
                  {account.cvRepo.files.map((file) => (
                    <li
                      key={file.path}
                      className="font-mono text-xs text-[var(--text-muted)]"
                    >
                      {file.path}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : (
            <p className="text-sm text-[var(--text-muted)]">{a.githubCvMissing}</p>
          )}
        </CmsCard>
      ) : null}

      {connected ? (
        <CmsCard title={a.githubReposHeading}>
          <input
            className="field mb-4"
            placeholder={a.searchRepos}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          {filtered.length === 0 ? (
            <p className="text-sm text-[var(--text-muted)]">{a.noMatchingRepos}</p>
          ) : (
            <ul className="grid gap-2">
              {filtered.map((repo) => (
                <li key={repo.fullName} className="tile flex flex-wrap items-center gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="font-mono text-sm font-semibold">{repo.fullName}</p>
                    {repo.description ? (
                      <p className="mt-1 text-sm text-[var(--text-muted)]">
                        {repo.description}
                      </p>
                    ) : null}
                    <p className="mt-1 text-xs text-[var(--text-muted)]">
                      {repo.private ? a.githubRepoPrivate : a.githubRepoPublic}
                      {repo.defaultBranch ? ` · ${repo.defaultBranch}` : ""}
                    </p>
                  </div>
                  <a
                    href={repo.htmlUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-ghost text-sm"
                  >
                    {a.githubOpenRepo}
                  </a>
                  <button
                    type="button"
                    className="btn-ghost text-sm"
                    onClick={() =>
                      router.push(
                        `/${locale}/admin?tab=content&attach=${encodeURIComponent(repo.fullName)}`,
                      )
                    }
                  >
                    {a.githubAttachProject}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </CmsCard>
      ) : null}
    </div>
  );
}
