import { notFound } from "next/navigation";
import { AdminDashboard } from "@/components/admin-dashboard";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";

export const dynamic = "force-dynamic";

export default async function AdminPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale: raw } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw as Locale;
  const dict = getDictionary(locale);

  return (
    <section className="admin-page">
      <AdminDashboard locale={locale} dict={dict} />
    </section>
  );
}
