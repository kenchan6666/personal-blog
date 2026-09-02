"use client";

import { useParams } from "next/navigation";
import { getDictionary } from "@/i18n/dictionaries";
import { defaultLocale, isLocale } from "@/i18n/config";

export default function LocaleError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const params = useParams<{ locale?: string }>();
  const raw = params.locale ?? "";
  const locale = isLocale(raw) ? raw : defaultLocale;
  const dict = getDictionary(locale);

  return (
    <div className="page-status">
      <p className="page-title display-font">{dict.errorPage}</p>
      <button type="button" className="btn-cta mt-6" onClick={() => reset()}>
        {dict.retry}
      </button>
    </div>
  );
}
