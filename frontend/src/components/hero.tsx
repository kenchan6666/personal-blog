import Link from "next/link";
import type { HeroVisual as HeroVisualConfig, PublicLink } from "@/lib/api";
import { HeroVisual } from "./hero-visual";
import { ProfileContacts } from "./profile-contacts";

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
  email?: string;
  links?: PublicLink[];
  visual?: HeroVisualConfig | null;
};

export function Hero({
  locale,
  content,
  email = "",
  links = [],
  visual = null,
}: Props) {
  return (
    <section className="relative flex min-h-[100svh] items-center px-5 py-16 sm:px-10 sm:py-20 lg:px-14">
      <div className="mx-auto grid w-full max-w-6xl items-center gap-10 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] lg:gap-10">
        <div className="hero-copy">
          <p className="display-font mb-4 text-[2.15rem] font-extrabold tracking-tight sm:mb-5 sm:text-5xl lg:text-6xl">
            {content.brand}
          </p>
          <h1 className="display-font mb-4 max-w-xl text-[1.65rem] leading-[1.15] font-bold tracking-tight sm:mb-5 sm:text-4xl lg:text-[2.75rem]">
            {content.headline}
          </h1>
          <p className="mb-5 max-w-lg text-base leading-relaxed text-[var(--text-muted)] sm:mb-6 sm:text-lg">
            {content.support}
          </p>
          <ProfileContacts email={email} links={links} />
          <div className="hero-cta flex flex-col gap-3 min-[400px]:flex-row min-[400px]:flex-wrap">
            <Link href={`/${locale}/projects`} className="btn-cta">
              {content.ctaProjects}
            </Link>
            <Link href={`/${locale}/articles`} className="btn-ghost">
              {content.ctaArticles}
            </Link>
          </div>
        </div>

        <div className="hero-visual relative min-h-[220px] sm:min-h-[340px] lg:min-h-[420px]">
          <HeroVisual visual={visual} />
        </div>
      </div>
    </section>
  );
}
