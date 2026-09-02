import { notFound } from "next/navigation";
import { AdminDashboard } from "@/components/admin-dashboard";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";

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
    <section className="flex min-h-screen items-start justify-center px-4 pt-16 pb-12 sm:px-8 sm:py-12 lg:px-12">
      <AdminDashboard locale={locale} dict={dict} />
    </section>
  );
}
