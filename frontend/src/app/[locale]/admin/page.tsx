import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { AdminDashboard } from "@/components/admin-dashboard";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import { fetchPublicSite } from "@/lib/api";
import { brandForShell } from "@/lib/site-content";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale: raw } = await params;
  const locale = (isLocale(raw) ? raw : "zh-Hant") as Locale;
  const dict = getDictionary(locale);
  return {
    title: `${dict.admin.dashboard} · ${brandForShell(dict, await fetchPublicSite(locale))}`,
    robots: { index: false, follow: false, nocache: true },
  };
}

export default async function AdminPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale: raw } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw as Locale;
  const dict = getDictionary(locale);

  return (
    <section className="admin-page">
      <AdminDashboard locale={locale} dict={dict} />
    </section>
  );
}
