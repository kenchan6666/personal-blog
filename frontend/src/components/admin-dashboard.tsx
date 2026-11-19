"use client";

import { Suspense, useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import {
  clearSessionToken,
  logoutOwner,
  fetchMe,
  fetchOwnerGitHubAccount,
  getSessionToken,
} from "@/lib/api";
import { AdminTopBar, type AdminSection } from "./admin-top-bar";
import { AboutEditor } from "./about-editor";
import { AgentChat } from "./agent-chat";
import { ArticleEditor } from "./article-editor";
import { CommentModerator } from "./comment-moderator";
import { GitHubConnect } from "./github-connect";
import { JournalEditor } from "./journal-editor";
import { ProjectEditor } from "./project-editor";
import { ResumeEditor } from "./resume-editor";
import { SiteEditor } from "./site-editor";

type Props = {
  locale: Locale;
  dict: Dictionary;
};

const TABS = ["site", "content", "comments", "github", "resume", "agent"] as const;
type Tab = (typeof TABS)[number];

function isTab(value: string | null): value is Tab {
  return TABS.includes(value as Tab);
}

const ICON_PATHS: Record<Tab, string> = {
  site: "M3 10.5 12 4l9 6.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z",
  content: "M6 3h9l4 4v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zm2 8h8M8 15h8M8 7h5",
  comments: "M4 5h16v11H9l-5 4z",
  github: "M9 19c-4 1.3-4-2-6-2.5m12 4.5v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.3 4.3 0 0 0-.1-3.2s-1-.3-3.4 1.3a11.6 11.6 0 0 0-6.2 0C6.6 2.8 5.6 3.1 5.6 3.1a4.3 4.3 0 0 0-.1 3.2A4.6 4.6 0 0 0 4.2 9.5c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21",
  resume: "M7 3h10a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zm5 5a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm-3 9a3 3 0 0 1 6 0",
  agent: "M12 3l1.8 4.7L18.5 9l-4.7 1.8L12 15.5l-1.8-4.7L5.5 9l4.7-1.3zM18 15l.9 2.1L21 18l-2.1.9L18 21l-.9-2.1L15 18l2.1-.9z",
};

function TabIcon({ tab }: { tab: Tab }) {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden>
      <path
        d={ICON_PATHS[tab]}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function GitHubBanner({ dict, onReconnect }: { dict: Dictionary; onReconnect: () => void }) {
  const a = dict.admin;
  return (
    <div className="admin-banner" role="status">
      <p>{a.githubDisconnectedBanner}</p>
      <button type="button" className="btn-cta text-sm" onClick={onReconnect}>
        {a.githubReconnectCta}
      </button>
    </div>
  );
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

  const [githubConnected, setGithubConnected] = useState<boolean | null>(null);
  const githubParam = searchParams.get("github");

  useEffect(() => {
    const token = getSessionToken();
    if (!token) return;
    let ignore = false;
    fetchOwnerGitHubAccount(token)
      .then((account) => {
        if (!ignore) setGithubConnected(Boolean(account.connected));
      })
      .catch(() => {});
    return () => {
      ignore = true;
    };
  }, [githubParam]);

  const labels: Record<Tab, string> = {
    site: a.tabSite,
    content: a.tabContent,
    comments: a.tabComments,
    github: a.tabGithub,
    resume: a.tabResume,
    agent: a.tabAgent,
  };

  const pageTitle = `${labels[tab]} · ${a.dashboard}`;
  useEffect(() => {
    document.title = pageTitle;
  }, [pageTitle]);

  const sections: AdminSection[] = TABS.map((item) => ({
    key: item,
    label: labels[item],
    icon: <TabIcon tab={item} />,
  }));

  return (
    <div
      className={`admin-dashboard-shell${tab === "agent" ? " is-agent" : ""}`}
    >
      <AdminTopBar
        locale={locale}
        dict={dict}
        title={labels[tab]}
        email={email}
        sections={sections}
        active={tab}
        onSelect={(key) => {
          if (isTab(key)) setTab(key);
        }}
        onLogout={onLogout}
      />
      {githubConnected === false && tab !== "agent" && tab !== "github" ? (
        <GitHubBanner dict={dict} onReconnect={() => setTab("github")} />
      ) : null}

      <div
        key={tab}
        className={
          tab === "agent"
            ? "admin-tab-panel"
            : "admin-tab-panel grid gap-5 lg:grid-cols-2"
        }
      >
        {tab === "agent" ? (
          <div>
            <AgentChat preview={{ locale, dict }} />
          </div>
        ) : null}
        {tab === "github" ? (
          <div className="lg:col-span-2">
            <Suspense>
              <GitHubConnect locale={locale} dict={dict} />
            </Suspense>
          </div>
        ) : null}
        {tab === "resume" ? (
          <div className="lg:col-span-2">
            <ResumeEditor locale={locale} dict={dict} active={tab === "resume"} />
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
    void logoutOwner().finally(() => router.replace(`/${locale}/admin/login`));
  }

  if (loading) {
    return (
      <div className="admin-dashboard-shell">
        <AdminTopBar locale={locale} dict={dict} title={dict.admin.dashboard} />
        <p className="text-[var(--text-muted)]">{dict.admin.verifying}</p>
      </div>
    );
  }

  if (!email) return null;

  return (
    <Suspense fallback={<p className="text-[var(--text-muted)]">{dict.admin.verifying}</p>}>
      <AdminTabs locale={locale} dict={dict} email={email} onLogout={logout} />
    </Suspense>
  );
}
