import { headers } from "next/headers";
import { NotFoundView } from "@/components/not-found-view";
import { defaultLocale, isLocale } from "@/i18n/config";

export default async function RootNotFound() {
  const raw = (await headers()).get("x-locale") ?? defaultLocale;
  return <NotFoundView locale={isLocale(raw) ? raw : defaultLocale} />;
}
