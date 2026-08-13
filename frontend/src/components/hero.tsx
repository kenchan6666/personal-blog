import Link from "next/link";
import { HeroVisual } from "./hero-visual";

export type HeroContent = {
  brand: string;
  headline: string;
  support: string;
  ctaProjects: string;
  ctaArticles: string;
};

type Props = {
  locale: string;
  content: HeroContent;
};

export function Hero({ locale, content }: Props) {
  return (
    <section className="relative flex min-h-screen items-center px-6 py-20 sm:px-10 lg:px-14">
      <div className="mx-auto grid w-full max-w-6xl items-center gap-12 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] lg:gap-10">
        <div className="hero-copy">
          <p className="display-font mb-5 text-4xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl">
            {content.brand}
          </p>
          <h1 className="display-font mb-5 max-w-xl text-3xl leading-[1.15] font-bold tracking-tight sm:text-4xl lg:text-[2.75rem]">
            {content.headline}
          </h1>
          <p className="mb-9 max-w-lg text-base leading-relaxed text-[var(--text-muted)] sm:text-lg">
            {content.support}
          </p>
          <div className="flex flex-wrap gap-3">
            <Link href={`/${locale}/projects`} className="btn-cta">
              {content.ctaProjects}
            </Link>
            <Link href={`/${locale}/articles`} className="btn-ghost">
              {content.ctaArticles}
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
