import { notFound } from "next/navigation";
import { PageFrame } from "@/components/page-frame";
import { ResumePaper } from "@/components/resume-paper";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";
import { fetchPublicResume } from "@/lib/api";
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

  const api =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
  const pdfHref = resume.pdfUrl
    ? `${api}${resume.pdfUrl}`
    : `${api}/api/public/resumes/${encodeURIComponent(slug)}/pdf`;

  return (
    <PageFrame
      title={dict.resume.title}
      lead={resume.summary[0] || dict.resume.lead}
      narrow
    >
      <div className="mb-5 flex flex-wrap gap-3">
        <a className="btn-cta" href={pdfHref}>
          {dict.resume.download}
        </a>
      </div>
      <ResumePaper
        resume={resume}
        dict={dict}
        sections={resume.sections}
      />
    </PageFrame>
  );
}
