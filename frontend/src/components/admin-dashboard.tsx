"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import {
  clearSessionToken,
  fetchMe,
  getSessionToken,
} from "@/lib/api";
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
    <div className="sidebar-panel max-w-4xl rounded-[var(--radius-panel)] p-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="display-font mb-2 text-2xl font-bold">
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

      <SiteEditor dict={dict} />
      <ProjectEditor dict={dict} />
    </div>
  );
}
