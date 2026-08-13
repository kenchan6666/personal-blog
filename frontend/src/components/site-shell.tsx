"use client";

import { useState } from "react";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import { Sidebar } from "./sidebar";

type Props = {
  locale: Locale;
  dict: Dictionary;
  children: React.ReactNode;
};

export function SiteShell({ locale, dict, children }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative z-10 min-h-screen">
      <Sidebar
        locale={locale}
        dict={dict}
        open={open}
        onToggle={() => setOpen((v) => !v)}
        onNavigate={() => setOpen(false)}
      />

      {/* Only the rail reserves layout space; expand overlays Hero */}
      <main className="min-h-screen pl-[calc(var(--sidebar-rail)+1.75rem)]">
        {children}
      </main>
    </div>
  );
}
