import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { AdminLoginForm } from "@/components/admin-login-form";
import { AdminTopBar } from "@/components/admin-top-bar";
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
    title: `${dict.admin.title} · ${brandForShell(dict, await fetchPublicSite(locale))}`,
    robots: { index: false, follow: false, nocache: true },
  };
}

export default async function AdminLoginPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale: raw } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw as Locale;
  const dict = getDictionary(locale);

  return (
    <>
      <AdminTopBar locale={locale} dict={dict} title={dict.admin.dashboard} />
      <section className="flex min-h-screen items-center justify-center px-5 py-20">
        <AdminLoginForm locale={locale} dict={dict} />
      </section>
    </>
  );
}
