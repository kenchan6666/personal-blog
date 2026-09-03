import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, locales, type Locale } from "@/i18n/config";
import { fetchPublicSite } from "@/lib/api";
import { pageMetadata, siteShareImage } from "@/lib/seo";
import { brandForShell } from "@/lib/site-content";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale: raw } = await params;
  if (!isLocale(raw)) return { title: "ken" };
  const locale = raw as Locale;
  const dict = getDictionary(locale);
  const site = await fetchPublicSite(locale);
  return pageMetadata({
    locale,
    title: brandForShell(dict, site),
    description: site?.hero.support || dict.hero.support,
    path: "",
    image: siteShareImage(site),
  });
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale: raw } = await params;
  if (!isLocale(raw)) notFound();
  return children;
}
