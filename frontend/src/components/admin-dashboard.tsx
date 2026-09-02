"use client";

import { Suspense, useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import {
  clearSessionToken,
  fetchMe,
  getSessionToken,
} from "@/lib/api";
import { AboutEditor } from "./about-editor";
import { AgentChat } from "./agent-chat";
import { ArticleEditor } from "./article-editor";
import { CommentModerator } from "./comment-moderator";
import { GitHubConnect } from "./github-connect";
import { JournalEditor } from "./journal-editor";
import { ProjectEditor } from "./project-editor";
import { SiteEditor } from "./site-editor";

type Props = {
  locale: Locale;
  dict: Dictionary;
};

const TABS = ["site", "content", "comments", "github", "agent"] as const;
type Tab = (typeof TABS)[number];

function isTab(value: string | null): value is Tab {
  return TABS.includes(value as Tab);
}

function AdminTabs({ locale, dict, email, onLogout }: Props & { email: string; onLogout: () => void }) {
  const a = dict.admin;
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const requested = searchParams.get("tab");
  const tab: Tab = isTab(requested)
    ? requested
    : searchParams.get("github")
      ? "github"
      : "site";

  function setTab(next: Tab) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", next);
    router.replace(`${pathname}?${params.toString()}`);
  }

  const labels: Record<Tab, string> = {
    site: a.tabSite,
    content: a.tabContent,
    comments: a.tabComments,
    github: a.tabGithub,
    agent: a.tabAgent,
  };

  return (
    <div className="w-full max-w-6xl">
      <div className="glass mb-6 flex flex-wrap items-start justify-between gap-4 rounded-[var(--radius-panel)] p-6">
        <div>
          <h1 className="display-font mb-1 text-2xl font-bold">
            {a.dashboard}
          </h1>
          <p className="text-sm text-[var(--text-muted)]">
            {a.signedInAs}: {email}
          </p>
        </div>
        <button type="button" className="btn-ghost" onClick={onLogout}>
          {a.logout}
        </button>
      </div>

      <div className="segment mb-5">
        {TABS.map((item) => (
          <button
            key={item}
            type="button"
            className={tab === item ? "segment-active" : ""}
            onClick={() => setTab(item)}
          >
            {labels[item]}
          </button>
        ))}
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        {tab === "agent" ? (
          <div className="lg:col-span-2">
            <AgentChat />
          </div>
        ) : null}
        {tab === "github" ? (
          <div className="lg:col-span-2">
            <Suspense>
              <GitHubConnect locale={locale} dict={dict} />
            </Suspense>
          </div>
        ) : null}
        {tab === "site" ? (
          <>
            <div className="lg:col-span-2">
              <SiteEditor dict={dict} />
            </div>
            <div className="lg:col-span-2">
              <AboutEditor dict={dict} />
            </div>
          </>
        ) : null}
        {tab === "content" ? (
          <>
            <div className="grid gap-5">
              <ProjectEditor locale={locale} dict={dict} />
              <JournalEditor dict={dict} />
            </div>
            <ArticleEditor dict={dict} />
          </>
        ) : null}
        {tab === "comments" ? (
          <CommentModerator locale={locale} dict={dict} />
        ) : null}
      </div>
    </div>
  );
}

export function AdminDashboard({ locale, dict }: Props) {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getSessionToken();
    if (!token) {
      router.replace(`/${locale}/admin/login`);
      return;
    }
    fetchMe(token)
      .then((me) => setEmail(me.email))
      .catch(() => {
        clearSessionToken();
        router.replace(`/${locale}/admin/login`);
      })
      .finally(() => setLoading(false));
  }, [locale, router]);

  function logout() {
    clearSessionToken();
    router.replace(`/${locale}/admin/login`);
  }

  if (loading) {
    return (
      <p className="text-[var(--text-muted)]">{dict.admin.verifying}</p>
    );
  }

  if (!email) return null;

  return (
    <Suspense fallback={<p className="text-[var(--text-muted)]">{dict.admin.verifying}</p>}>
      <AdminTabs locale={locale} dict={dict} email={email} onLogout={logout} />
    </Suspense>
  );
}
