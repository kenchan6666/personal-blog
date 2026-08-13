import Link from "next/link";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import { HeroVisual } from "./hero-visual";

type Props = {
  locale: Locale;
  dict: Dictionary;
};

export function Hero({ locale, dict }: Props) {
  return (
    <section className="relative flex min-h-screen items-center px-6 py-20 sm:px-10 lg:px-14">
      <div className="mx-auto grid w-full max-w-6xl items-center gap-12 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] lg:gap-10">
        <div className="hero-copy">
          <p className="display-font mb-5 text-4xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl">
            {dict.brand}
          </p>
          <h1 className="display-font mb-5 max-w-xl text-3xl leading-[1.15] font-bold tracking-tight sm:text-4xl lg:text-[2.75rem]">
            {dict.hero.headline}
          </h1>
          <p className="mb-9 max-w-lg text-base leading-relaxed text-[var(--text-muted)] sm:text-lg">
            {dict.hero.support}
          </p>
          <div className="flex flex-wrap gap-3">
            <Link href={`/${locale}/projects`} className="btn-cta">
              {dict.hero.ctaProjects}
            </Link>
            <Link href={`/${locale}/articles`} className="btn-ghost">
              {dict.hero.ctaArticles}
            </Link>
          </div>
        </div>

        <div className="hero-visual relative min-h-[280px] sm:min-h-[340px] lg:min-h-[420px]">
          <HeroVisual />
        </div>
      </div>
    </section>
  );
}
