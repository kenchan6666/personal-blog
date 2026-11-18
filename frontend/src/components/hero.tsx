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
  visualAlt?: string;
};

export function Hero({
  locale,
  content,
  email = "",
  links = [],
  visual = null,
  visualAlt = "",
}: Props) {
  return (
    <section className="home-hero">
      <div className="home-wrap home-hero-grid">
        <div className="hero-copy">
          <p className="home-hero-name">{content.brand}</p>
          {content.headline ? (
            <h1 className="home-hero-headline">{content.headline}</h1>
          ) : null}
          {content.support ? (
            <p className="home-hero-support">{content.support}</p>
          ) : null}
          <ProfileContacts email={email} links={links} />
          <div className="hero-cta">
            <Link href={`/${locale}/projects`} className="btn-cta">
              {content.ctaProjects}
            </Link>
            <Link href={`/${locale}/articles`} className="btn-ghost">
              {content.ctaArticles}
            </Link>
          </div>
        </div>

        <div className="hero-visual">
          <HeroVisual visual={visual} alt={visualAlt} />
        </div>
      </div>
    </section>
  );
}
