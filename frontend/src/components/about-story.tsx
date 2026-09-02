import { MarkdownBody } from "@/components/markdown-body";
import type { AboutKind, PublicAboutModule } from "@/lib/api";

type Props = {
  modules: PublicAboutModule[];
  kindLabel: Record<AboutKind, string>;
};

export function AboutStory({ modules, kindLabel }: Props) {
  return (
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
  );
}
