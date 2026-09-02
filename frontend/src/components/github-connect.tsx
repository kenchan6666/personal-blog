"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import {
  fetchOwnerGitHubRepos,
  getSessionToken,
  startGitHubOAuth,
} from "@/lib/api";

type Props = {
  locale: Locale;
  dict: Dictionary;
};

export function GitHubConnect({ locale, dict }: Props) {
  const a = dict.admin;
  const router = useRouter();
  const params = useSearchParams();
  const [connected, setConnected] = useState(false);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<"ok" | "err" | null>(null);

  useEffect(() => {
    const token = getSessionToken();
    if (!token) return;
    fetchOwnerGitHubRepos(token)
      .then((repos) => {
        setConnected(repos !== null);
        setCount(repos?.length ?? 0);
      })
      .catch(() => setError(a.errorGeneric))
      .finally(() => setLoading(false));
  }, [a.errorGeneric]);

  useEffect(() => {
    const flag = params.get("github");
    if (flag === "connected") setFlash("ok");
    if (flag === "error") setFlash("err");
    if (flag) router.replace(`/${locale}/admin`);
  }, [params, locale, router]);

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

  return (
    <section className="cms-card glass rounded-[var(--radius-panel)] p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="display-font text-xl font-bold">{a.githubTitle}</h2>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            {loading
              ? a.verifying
              : connected
                ? a.githubConnectedHint.replace("{count}", String(count))
                : a.githubDisconnectedHint}
          </p>
        </div>
        {connected ? (
          <span className="status-pill status-pill-live">{a.githubConnected}</span>
        ) : (
          <button type="button" className="btn-cta" onClick={() => void onConnect()}>
            {a.connectGitHub}
          </button>
        )}
      </div>
      {flash === "ok" ? (
        <p className="mt-3 text-sm text-[var(--accent-link)]">{a.githubConnected}</p>
      ) : null}
      {flash === "err" ? (
        <p className="mt-3 text-sm text-[var(--danger)]">{a.errorGeneric}</p>
      ) : null}
      {error ? (
        <p className="mt-3 text-sm text-[var(--danger)]">{error}</p>
      ) : null}
    </section>
  );
}
