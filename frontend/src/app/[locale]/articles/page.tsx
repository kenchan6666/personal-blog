import { notFound } from "next/navigation";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";

export default async function ArticlesPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale: raw } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw as Locale;
  const dict = getDictionary(locale);

  return (
    <section className="px-6 py-24 sm:px-10 lg:px-14">
      <h1 className="display-font text-3xl font-bold">{dict.nav.articles}</h1>
      <p className="mt-3 max-w-xl text-[var(--text-muted)]">
        {locale === "zh-Hant"
          ? "文章列表將接上 Portfolio API 後顯示已發布內容。"
          : "Published articles will appear here once the Portfolio API is wired."}
      </p>
    </section>
  );
}
