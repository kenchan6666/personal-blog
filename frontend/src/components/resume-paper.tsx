import type { Dictionary } from "@/i18n/dictionaries";
import type {
  OwnerResume,
  PublicResume,
  ResumeExtra,
  ResumeSectionId,
} from "@/lib/api";

type Props = {
  resume: PublicResume | OwnerResume;
  dict: Dictionary;
  sections?: string[];
  showEmpty?: boolean;
};

const BUILTIN: ResumeSectionId[] = [
  "summary",
  "education",
  "internship",
  "projects",
  "activities",
  "skillsOthers",
];

function range(start: string, end: string) {
  return [start, end].filter(Boolean).join(" – ");
}

function filled(id: string, resume: PublicResume | OwnerResume) {
  if (id === "summary") return resume.summary.length > 0;
  if (id === "education") return resume.education.length > 0;
  if (id === "internship") return resume.internships.length > 0;
  if (id === "projects") return resume.projects.length > 0;
  if (id === "activities") return resume.activities.length > 0;
  if (id === "skillsOthers") {
    return resume.skills.length > 0 || resume.languages.length > 0;
  }
  const extra = (resume.extras ?? []).find((item) => item.slug === id);
  return Boolean(extra && (extra.lines.length > 0 || extra.entries.length > 0));
}

export function ResumePaper({ resume, dict, sections, showEmpty }: Props) {
  const r = dict.resume;
  const header = resume.header;
  const extras = resume.extras ?? [];
  const seen = new Set<string>();
  const order = [
    ...(sections ?? BUILTIN),
    ...extras.map((item) => item.slug),
  ].filter((id) => {
    if (seen.has(id)) return false;
    seen.add(id);
    return true;
  });

  return (
    <article className="resume-paper">
      <header className="resume-paper-head">
        <h2>{header.name || resume.title || " "}</h2>
        <p>{[header.phone, header.email].filter(Boolean).join(" · ")}</p>
        {header.city ? <p>{header.city}</p> : null}
      </header>
      {order.map((id) => {
        if (!showEmpty && !filled(id, resume)) return null;
        if (showEmpty && sections && !sections.includes(id) && filled(id, resume) === false && BUILTIN.includes(id as ResumeSectionId)) {
          return null;
        }
        if (id === "summary") {
          return (
            <section key={id}>
              <h3>{r.sectionSummary}</h3>
              {resume.summary.map((line) => (
                <p key={line}>{line}</p>
              ))}
            </section>
          );
        }
        if (id === "education") {
          return (
            <section key={id}>
              <h3>{r.sectionEducation}</h3>
              {resume.education.map((item) => (
                <div key={`${item.institution}-${item.start}`} className="resume-entry">
                  <div className="resume-entry-row">
                    <strong>{item.institution}</strong>
                    <span>{range(item.start, item.end)}</span>
                  </div>
                  <div className="resume-entry-row">
                    <span>
                      {[item.field, item.degree].filter(Boolean).join(" ")}
                    </span>
                    <span>{item.city}</span>
                  </div>
                  {item.honor ? <p>{item.honor}</p> : null}
                  {item.related_courses.length > 0 ? (
                    <p>{item.related_courses.join(", ")}</p>
                  ) : null}
                </div>
              ))}
            </section>
          );
        }
        if (id === "internship") {
          return (
            <section key={id}>
              <h3>{r.sectionInternship}</h3>
              {resume.internships.map((item) => (
                <div key={`${item.organization}-${item.start}`} className="resume-entry">
                  <div className="resume-entry-row">
                    <strong>{item.organization}</strong>
                    <span>{range(item.start, item.end)}</span>
                  </div>
                  <div className="resume-entry-row">
                    <span>{item.role}</span>
                    <span>{item.city}</span>
                  </div>
                  {item.description.map((line) => (
                    <p key={line}>{line}</p>
                  ))}
                </div>
              ))}
            </section>
          );
        }
        if (id === "projects") {
          return (
            <section key={id}>
              <h3>{r.sectionProjects}</h3>
              {resume.projects.map((item) => (
                <div key={`${item.name}-${item.start}`} className="resume-entry">
                  <div className="resume-entry-row">
                    <strong>{item.name}</strong>
                    <span>{range(item.start, item.end)}</span>
                  </div>
                  {item.tech_stack.length > 0 ? (
                    <p>({item.tech_stack.join(", ")})</p>
                  ) : null}
                  {item.description.map((line) => (
                    <p key={line}>{line}</p>
                  ))}
                </div>
              ))}
            </section>
          );
        }
        if (id === "activities") {
          return (
            <section key={id}>
              <h3>{r.sectionActivities}</h3>
              {resume.activities.map((item) => (
                <div key={`${item.organization}-${item.role}`} className="resume-entry">
                  <div className="resume-entry-row">
                    <strong>{item.organization}</strong>
                    <span>{range(item.start, item.end)}</span>
                  </div>
                  {item.description.map((line) => (
                    <p key={line}>{line}</p>
                  ))}
                </div>
              ))}
            </section>
          );
        }
        if (id === "skillsOthers") {
          return (
            <section key={id}>
              <h3>{r.sectionSkills}</h3>
              {resume.skills.length > 0 ? (
                <p>Skills: {resume.skills.join(", ")}</p>
              ) : null}
              {resume.languages.length > 0 ? (
                <p>
                  Languages:{" "}
                  {resume.languages
                    .map((item) =>
                      item.level ? `${item.name} (${item.level})` : item.name,
                    )
                    .join(", ")}
                </p>
              ) : null}
            </section>
          );
        }
        const extra = extras.find((item) => item.slug === id);
        if (!extra) return null;
        if (!showEmpty && extra.lines.length === 0 && extra.entries.length === 0) {
          return null;
        }
        return <ExtraBlock key={id} extra={extra} />;
      })}
    </article>
  );
}

function ExtraBlock({ extra }: { extra: ResumeExtra }) {
  return (
    <section>
      <h3>{extra.title || extra.slug}</h3>
      {extra.lines.map((line) => (
        <p key={line}>{line}</p>
      ))}
      {extra.entries.map((item) => (
        <div key={`${item.organization}-${item.start}`} className="resume-entry">
          <div className="resume-entry-row">
            <strong>{item.organization}</strong>
            <span>{range(item.start, item.end)}</span>
          </div>
          <div className="resume-entry-row">
            <span>{item.role}</span>
            <span>{item.city}</span>
          </div>
          {item.description.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </div>
      ))}
    </section>
  );
}
