"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import {
  clearSessionToken,
  fetchMe,
  getSessionToken,
} from "@/lib/api";
import { AboutEditor } from "./about-editor";
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
    <div className="w-full max-w-6xl">
      <div className="glass mb-6 flex flex-wrap items-start justify-between gap-4 rounded-[var(--radius-panel)] p-6">
        <div>
          <h1 className="display-font mb-1 text-2xl font-bold">
            {dict.admin.dashboard}
          </h1>
          <p className="text-sm text-[var(--text-muted)]">
            {dict.admin.signedInAs}: {email}
          </p>
        </div>
        <button type="button" className="btn-ghost" onClick={logout}>
          {dict.admin.logout}
        </button>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="lg:col-span-2">
          <Suspense>
            <GitHubConnect locale={locale} dict={dict} />
          </Suspense>
        </div>
        <div className="lg:col-span-2">
          <SiteEditor dict={dict} />
        </div>
        <div className="lg:col-span-2">
          <AboutEditor dict={dict} />
        </div>
        <ProjectEditor locale={locale} dict={dict} />
        <ArticleEditor dict={dict} />
        <JournalEditor dict={dict} />
        <CommentModerator dict={dict} />
      </div>
    </div>
  );
}
