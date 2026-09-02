import { notFound } from "next/navigation";
import { AdminLoginForm } from "@/components/admin-login-form";
import { getDictionary } from "@/i18n/dictionaries";
import { isLocale, type Locale } from "@/i18n/config";

export const dynamic = "force-dynamic";

export default async function AdminLoginPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale: raw } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw as Locale;
  const dict = getDictionary(locale);

  return (
    <section className="flex min-h-screen items-center justify-center px-5 py-20">
      <AdminLoginForm locale={locale} dict={dict} />
    </section>
  );
}
