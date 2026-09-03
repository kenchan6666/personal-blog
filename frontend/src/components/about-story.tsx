import { MarkdownBody } from "@/components/markdown-body";
import type { AboutKind, PublicAboutModule } from "@/lib/api";

type Props = {
  modules: PublicAboutModule[];
  kindLabel: Record<AboutKind, string>;
  tocLabel: string;
};

export function AboutStory({ modules, kindLabel, tocLabel }: Props) {
  return (
    <>
      {modules.length > 1 ? (
        <nav className="about-toc" aria-label={tocLabel}>
          {modules.map((module) => (
            <a key={module.slug} href={`#${module.slug}`}>
              {module.title || kindLabel[module.kind] || module.kind}
            </a>
          ))}
        </nav>
      ) : null}
      <div className="about-stack">
        {modules.map((module) => (
          <section
            key={module.slug}
            id={module.slug}
            className={`about-module about-module-${module.kind}`}
          >
            {module.kind === "summary" ? null : (
              <p className="about-kicker">
                {kindLabel[module.kind] ?? module.kind}
              </p>
            )}
            {module.title ? (
              <h2 className="about-heading display-font">{module.title}</h2>
            ) : null}
            {module.body ? <MarkdownBody source={module.body} /> : null}
          </section>
        ))}
      </div>
    </>
  );
}
