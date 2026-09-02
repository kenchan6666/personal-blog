import { notFound } from "next/navigation";
import { MarkdownBody } from "@/components/markdown-body";
import { PageFrame } from "@/components/page-frame";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import { fetchPublicAbout } from "@/lib/api";

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
  const modules = await fetchPublicAbout(locale);

  const kindLabel: Record<string, string> = {
    summary: dict.about.kindSummary,
    education: dict.about.kindEducation,
    achievement: dict.about.kindAchievement,
    experience: dict.about.kindExperience,
    custom: dict.about.kindCustom,
  };

  return (
    <PageFrame title={dict.about.title} lead={dict.about.lead} narrow>
      {modules.length === 0 ? (
        <p className="text-[var(--text-muted)]">{dict.about.empty}</p>
      ) : (
        <div className="about-stack">
          {modules.map((module) => (
            <section key={module.slug} className="about-module">
              <p className="about-kicker">{kindLabel[module.kind] ?? module.kind}</p>
              {module.title ? (
                <h2 className="about-heading display-font">{module.title}</h2>
              ) : null}
              {module.body ? <MarkdownBody source={module.body} /> : null}
            </section>
          ))}
        </div>
      )}
    </PageFrame>
  );
}
