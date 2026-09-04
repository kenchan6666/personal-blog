import { notFound } from "next/navigation";
import Link from "next/link";
import { PageFrame } from "@/components/page-frame";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import { fetchPublicResumes } from "@/lib/api";
import { pageMetadata } from "@/lib/seo";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale: raw } = await params;
  if (!isLocale(raw)) return {};
  const locale = raw as Locale;
  const dict = getDictionary(locale);
  return pageMetadata({
    locale,
    title: dict.resume.title,
    description: dict.resume.lead,
    path: "/resume",
  });
}

export default async function ResumeIndexPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale: raw } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw as Locale;
  const dict = getDictionary(locale);
  const resumes = await fetchPublicResumes();

  return (
    <PageFrame title={dict.resume.title} lead={dict.resume.lead} narrow>
      {resumes.length === 0 ? (
        <p className="about-empty">{dict.resume.empty}</p>
      ) : (
        <ul className="grid gap-4">
          {resumes.map((item) => (
            <li key={item.slug}>
              <Link
                href={`/${locale}/resume/${item.slug}`}
                className="tile block"
              >
                <strong>{item.title}</strong>
                <span className="ml-3 text-[var(--text-muted)]">{item.locale}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </PageFrame>
  );
}
