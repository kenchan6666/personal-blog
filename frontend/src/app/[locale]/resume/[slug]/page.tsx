import { notFound } from "next/navigation";
import { PageFrame } from "@/components/page-frame";
import { ResumePaper } from "@/components/resume-paper";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import { fetchPublicResume, fetchPublicResumes, publicResumePdfPath } from "@/lib/api";
import { pageMetadata } from "@/lib/seo";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale: raw, slug } = await params;
  if (!isLocale(raw)) return {};
  const locale = raw as Locale;
  try {
    const resume = await fetchPublicResume(slug);
    return pageMetadata({
      locale,
      title: resume.header.name || resume.title,
      description: resume.summary[0] || getDictionary(locale).resume.lead,
      path: `/resume/${slug}`,
    });
  } catch {
    return {};
  }
}

export default async function ResumeDetailPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale: raw, slug } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw as Locale;
  const dict = getDictionary(locale);
  let resume;
  try {
    resume = await fetchPublicResume(slug);
  } catch {
    notFound();
  }

  const resumes = await fetchPublicResumes();
  const contact = [resume.header.phone, resume.header.email, resume.header.city]
    .filter(Boolean)
    .join(" · ");
  const pdfHref = publicResumePdfPath(slug);

  return (
    <PageFrame
      title={resume.header.name || resume.title || dict.resume.title}
      lead={contact || undefined}
      back={
        resumes.length > 1
          ? { href: `/${locale}/resume`, label: dict.nav.resume }
          : undefined
      }
      narrow
    >
      <div className="mb-5 flex flex-wrap gap-3">
        <a className="btn-ghost" href={pdfHref}>
          {dict.resume.download}
        </a>
      </div>
      <ResumePaper
        resume={resume}
        dict={dict}
        sections={resume.sections}
        paged={false}
      />
    </PageFrame>
  );
}
