import { notFound } from "next/navigation";
import { AboutStory } from "@/components/about-story";
import { PageFrame } from "@/components/page-frame";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import type { AboutKind } from "@/lib/api";
import { fetchPublicAbout, fetchPublicSite } from "@/lib/api";
import { pageCopy } from "@/lib/site-content";

export const dynamic = "force-dynamic";

export default async function AboutPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale: raw } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw as Locale;
  const dict = getDictionary(locale);
  const [modules, site] = await Promise.all([
    fetchPublicAbout(locale),
    fetchPublicSite(locale),
  ]);

  const kindLabel: Record<AboutKind, string> = {
    summary: dict.about.kindSummary,
    education: dict.about.kindEducation,
    achievement: dict.about.kindAchievement,
    experience: dict.about.kindExperience,
    custom: dict.about.kindCustom,
  };

  const lead = pageCopy(site, "aboutLead", dict.about.lead);
  const empty = pageCopy(site, "aboutEmpty", dict.about.empty);

  return (
    <PageFrame title={dict.about.title} lead={lead} narrow>
      {modules.length === 0 ? (
        <p className="about-empty">{empty}</p>
      ) : (
        <AboutStory modules={modules} kindLabel={kindLabel} />
      )}
    </PageFrame>
  );
}
