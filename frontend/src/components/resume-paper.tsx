import type { Dictionary } from "@/i18n/dictionaries";
import type { OwnerResume, PublicResume, ResumeSectionId } from "@/lib/api";

type Props = {
  resume: PublicResume | OwnerResume;
  dict: Dictionary;
  sections?: ResumeSectionId[];
  showEmpty?: boolean;
};

function range(start: string, end: string) {
  return [start, end].filter(Boolean).join(" – ");
}

export function ResumePaper({ resume, dict, sections, showEmpty }: Props) {
  const r = dict.resume;
  const header = resume.header;
  const visible = (id: ResumeSectionId, filled: boolean) =>
    showEmpty ? !sections || sections.includes(id) : filled;
  return (
    <article className="resume-paper">
      <header className="resume-paper-head">
        <h2>{header.name || resume.title || " "}</h2>
        <p>{[header.phone, header.email].filter(Boolean).join(" · ")}</p>
        {header.city ? <p>{header.city}</p> : null}
      </header>
      {visible("summary", resume.summary.length > 0) ? (
        <section>
          <h3>{r.sectionSummary}</h3>
          {resume.summary.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </section>
      ) : null}
      {visible("education", resume.education.length > 0) ? (
        <section>
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
      ) : null}
      {visible("internship", resume.internships.length > 0) ? (
        <section>
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
      ) : null}
      {visible("projects", resume.projects.length > 0) ? (
        <section>
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
      ) : null}
      {visible("activities", resume.activities.length > 0) ? (
        <section>
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
      ) : null}
      {visible(
        "skillsOthers",
        resume.skills.length > 0 || resume.languages.length > 0,
      ) ? (
        <section>
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
      ) : null}
    </article>
  );
}
