import { notFound } from "next/navigation";
import { SiteShell } from "@/components/site-shell";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, locales, type Locale } from "@/i18n/config";
import { fetchPublicSite } from "@/lib/api";
import { brandForShell } from "@/lib/site-content";

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
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
  const locale = raw as Locale;
  const dict = getDictionary(locale);
  const site = await fetchPublicSite(locale);
  const shellDict = { ...dict, brand: brandForShell(dict, site) };

  return (
    <SiteShell locale={locale} dict={shellDict}>
      {children}
    </SiteShell>
  );
}
