import { notFound, redirect } from "next/navigation";
import { fetchPublicArticle } from "@/lib/api";
import { isLocale } from "@/i18n/config";

export const dynamic = "force-dynamic";

export default async function ArticleSlugRedirectPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale: raw, slug } = await params;
  if (!isLocale(raw)) notFound();
  const article = await fetchPublicArticle(raw, slug);
  if (!article) notFound();
  redirect(`/${raw}/articles/${article.categorySlug || "taiko"}/${article.slug}`);
}
