import { notFound } from "next/navigation";
import { Hero } from "@/components/hero";
import { ProfileSection } from "@/components/profile-section";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import { fetchPublicSite } from "@/lib/api";
import { mergeHeroContent, mergeProfileContent } from "@/lib/site-content";

export default async function HomePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale: raw } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw as Locale;
  const dict = getDictionary(locale);
  const site = await fetchPublicSite(locale);

  return (
    <>
      <Hero locale={locale} content={mergeHeroContent(dict, site)} />
      <ProfileSection content={mergeProfileContent(dict, site)} />
    </>
  );
}
