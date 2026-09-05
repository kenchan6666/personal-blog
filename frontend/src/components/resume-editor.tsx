"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import {
  createOwnerResume,
  createOwnerResumeTemplate,
  deleteOwnerResume,
  deleteOwnerResumeTemplate,
  emptyOwnerResume,
  emptyOwnerResumeTemplate,
  fetchOwnerResumeTemplates,
  fetchOwnerResumes,
  generateOwnerResume,
  getSessionToken,
  importOwnerResumeFromGithub,
  localizedText,
  publishOwnerResume,
  pushOwnerResumeToGithub,
  saveOwnerResume,
  saveOwnerResumeTemplate,
  type OwnerResume,
  type OwnerResumeTemplate,
  type ResumeSectionId,
} from "@/lib/api";
import { AgentField } from "./agent-field";
import { CmsCard, StatusPill } from "./cms-card";
import { CmsConfirm } from "./cms-confirm";
import { CmsModal } from "./cms-modal";
import { ResumeLayoutStudio } from "./resume-layout-studio";
import { ResumePaper } from "./resume-paper";

type Props = {
  locale: Locale;
  dict: Dictionary;
};

function slugify(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 40);
}

function linesOf(value: string) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function commasOf(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function ResumeEditor({ locale, dict }: Props) {
  const a = dict.admin;
  const r = dict.resume;
  const [templates, setTemplates] = useState<OwnerResumeTemplate[]>([]);
  const [resumes, setResumes] = useState<OwnerResume[]>([]);
  const [current, setCurrent] = useState<OwnerResume | null>(null);
  const [templateDraft, setTemplateDraft] = useState<OwnerResumeTemplate>(
    emptyOwnerResumeTemplate(),
  );
  const [openTemplate, setOpenTemplate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmResume, setConfirmResume] = useState(false);
  const [confirmTemplate, setConfirmTemplate] = useState(false);
  const [githubRepo, setGithubRepo] = useState("");
  const [githubPath, setGithubPath] = useState("");
  const [githubRef, setGithubRef] = useState("");
  const [extraTitle, setExtraTitle] = useState("");

  async function reload(token: string) {
    const [nextTemplates, nextResumes] = await Promise.all([
      fetchOwnerResumeTemplates(token),
      fetchOwnerResumes(token),
    ]);
    setTemplates(nextTemplates);
    setResumes(nextResumes);
    return { nextTemplates, nextResumes };
  }

  useEffect(() => {
    const token = getSessionToken();
    if (!token) return;
    reload(token)
      .catch(() => setError(a.errorGeneric))
      .finally(() => setLoading(false));
  }, [a.errorGeneric]);

  function openLayoutEditor(item: OwnerResumeTemplate) {
    setTemplateDraft({
      ...item,
      extras: item.extras ?? [],
    });
    setOpenTemplate(true);
  }

  function sectionLabel(id: string) {
    const extra = templates
      .flatMap((item) => item.extras ?? [])
      .find((item) => item.slug === id);
    if (extra) return extra.title || extra.slug;
    const onResume = current?.extras?.find((item) => item.slug === id);
    if (onResume) return onResume.title || onResume.slug;
    const map: Record<ResumeSectionId, string> = {
      summary: r.sectionSummary,
      education: r.sectionEducation,
      internship: r.sectionInternship,
      projects: r.sectionProjects,
      activities: r.sectionActivities,
      skillsOthers: r.sectionSkills,
    };
    return map[id as ResumeSectionId] || id;
  }

  function sectionBlurb(id: string) {
    if (layout?.extras?.some((item) => item.slug === id)) return a.sectionBlurbCustom;
    const map = {
      summary: a.sectionBlurbSummary,
      education: a.sectionBlurbEducation,
      internship: a.sectionBlurbInternship,
      projects: a.sectionBlurbProjects,
      activities: a.sectionBlurbActivities,
      skillsOthers: a.sectionBlurbSkills,
    };
    return map[id as ResumeSectionId] || a.sectionBlurbCustom;
  }

  const layout = useMemo(
    () =>
      templates.find((item) => item.slug === current?.templateSlug) ??
      templates[0],
    [templates, current?.templateSlug],
  );
  const sections = layout?.sections ?? [
    "summary",
    "education",
    "projects",
    "skillsOthers",
  ];

  async function persistResume(next: OwnerResume) {
    const token = getSessionToken();
    if (!token) return;
    setSaving(true);
    setError(null);
    try {
      const payload = {
        ...next,
        title: next.header.name.trim() || next.title.trim() || next.slug,
        slug:
          next.slug ||
          slugify(next.header.name || next.title) ||
          "resume",
      };
      const saved = next.id
        ? await saveOwnerResume(token, next.id, payload)
        : await createOwnerResume(token, payload);
      setCurrent(saved);
      await reload(token);
      setMessage(a.saved);
    } catch {
      setError(a.errorGeneric);
    } finally {
      setSaving(false);
    }
  }

  async function persistTemplate(next: OwnerResumeTemplate) {
    const token = getSessionToken();
    if (!token) return;
    setSaving(true);
    setError(null);
    try {
      const body = {
        slug: next.slug || slugify(localizedText(next.name)) || "layout",
        name: next.name,
        sections: next.sections,
        extras: next.extras,
      };
      const saved = next.id
        ? await saveOwnerResumeTemplate(token, next.id, body)
        : await createOwnerResumeTemplate(token, body);
      await reload(token);
      if (current) setCurrent({ ...current, templateSlug: saved.slug });
      setOpenTemplate(false);
      setMessage(a.saved);
    } catch {
      setError(a.errorGeneric);
    } finally {
      setSaving(false);
    }
  }

  function startNew() {
    setCurrent({
      ...emptyOwnerResume(),
      templateSlug: templates[0]?.slug || "classic-a4",
    });
    setMessage(null);
    setError(null);
  }

  if (loading) {
    return <p className="text-[var(--text-muted)]">{a.loadingResumes}</p>;
  }

  return (
    <div className="resume-workspace">
      <CmsCard
        title={a.resumeDocuments}
        action={
          <button type="button" className="btn-cta" onClick={startNew}>
            {a.newResume}
          </button>
        }
      >
        {resumes.length === 0 ? (
          <p className="text-sm text-[var(--text-muted)]">{a.emptyResumes}</p>
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {resumes.map((item) => {
              const itemLayout = templates.find(
                (template) => template.slug === item.templateSlug,
              );
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    className={`tile resume-pick w-full text-left${
                      current?.id === item.id ? " tile-active" : ""
                    }`}
                    onClick={() => {
                      setCurrent({ ...item, extras: item.extras ?? [] });
                      setMessage(null);
                      setError(null);
                    }}
                  >
                    <span className="flex items-center justify-between gap-3">
                      <strong>
                        {item.title || item.header.name || a.untitledResume}
                      </strong>
                      <StatusPill
                        published={item.status === "published"}
                        publishedLabel={a.statusPublished}
                        draftLabel={a.statusDraft}
                      />
                    </span>
                    <span className="resume-layout-mini">
                      {(itemLayout?.sections ?? sections).map((id) => (
                        <i key={id} title={sectionLabel(id)} />
                      ))}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </CmsCard>

      {current ? (
        <div className="resume-edit-grid">
          <CmsCard title={current.title || current.header.name || a.newResume}>
            {message ? (
              <p className="mb-3 text-sm text-[var(--success)]">{message}</p>
            ) : null}
            {error ? (
              <p className="mb-3 text-sm text-[var(--danger)]">{error}</p>
            ) : null}

            <p className="mb-2 text-sm font-semibold">{a.fieldResumeLayout}</p>
            <div className="resume-layout-split mb-4">
              <div className="resume-layout-row">
                {templates.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={`resume-layout-card${
                      current.templateSlug === item.slug ? " is-active" : ""
                    }`}
                    onClick={() => {
                      setCurrent({
                        ...current,
                        templateSlug: item.slug,
                        extras: [
                          ...(item.extras ?? []).map((def) => {
                            const existing = current.extras.find(
                              (extra) => extra.slug === def.slug,
                            );
                            return (
                              existing ?? {
                                slug: def.slug,
                                title: def.title,
                                lines: [],
                                entries: [],
                              }
                            );
                          }),
                          ...current.extras.filter(
                            (extra) =>
                              !(item.extras ?? []).some(
                                (def) => def.slug === extra.slug,
                              ),
                          ),
                        ],
                      });
                    }}
                  >
                    <strong>{localizedText(item.name) || item.slug}</strong>
                    <span className="resume-layout-bars">
                      {item.sections.map((id) => (
                        <span key={id}>{sectionLabel(id)}</span>
                      ))}
                    </span>
                  </button>
                ))}
                <button
                  type="button"
                  className="resume-layout-card is-new"
                  onClick={() => {
                    setTemplateDraft(emptyOwnerResumeTemplate());
                    setOpenTemplate(true);
                  }}
                >
                  {a.newLayout}
                </button>
              </div>
              {layout ? (
                <aside key={layout.slug} className="resume-layout-detail">
                  <div className="resume-layout-detail-head">
                    <div>
                      <strong>{localizedText(layout.name) || layout.slug}</strong>
                      {layout.githubPath ? (
                        <p className="resume-layout-path">{layout.githubPath}</p>
                      ) : null}
                    </div>
                    {!layout.builtin ? (
                      <button
                        type="button"
                        className="btn-cta"
                        onClick={() => openLayoutEditor(layout)}
                      >
                        {a.editLayout}
                      </button>
                    ) : (
                      <span className="resume-layout-locked">{a.layoutLocked}</span>
                    )}
                  </div>
                  <ul>
                    {layout.sections.map((id) => (
                      <li key={id}>
                        <b>{sectionLabel(id)}</b>
                        <span>{sectionBlurb(id)}</span>
                      </li>
                    ))}
                  </ul>
                </aside>
              ) : null}
            </div>

            <label className="mb-3 block text-xs text-[var(--text-muted)]">
              {a.fieldResumeSlug}
              <input
                className="field"
                value={current.slug}
                onChange={(event) =>
                  setCurrent({ ...current, slug: event.target.value })
                }
              />
            </label>
            <label className="mb-3 block text-xs text-[var(--text-muted)]">
              {a.fieldResumeLocale}
              <select
                className="field"
                value={current.locale}
                onChange={(event) =>
                  setCurrent({
                    ...current,
                    locale: event.target.value as OwnerResume["locale"],
                  })
                }
              >
                <option value="zh-Hant">繁中</option>
                <option value="zh-Hans">简中</option>
                <option value="en">English</option>
              </select>
            </label>
            <AgentField
              label={a.fieldResumeName}
              value={current.header.name}
              closeLabel={a.close}
              onChange={(name) =>
                setCurrent({
                  ...current,
                  title: name,
                  header: { ...current.header, name },
                })
              }
            />
            <AgentField
              label={a.fieldResumePhone}
              value={current.header.phone}
              closeLabel={a.close}
              onChange={(phone) =>
                setCurrent({
                  ...current,
                  header: { ...current.header, phone },
                })
              }
            />
            <AgentField
              label={a.fieldResumeEmail}
              value={current.header.email}
              closeLabel={a.close}
              onChange={(email) =>
                setCurrent({
                  ...current,
                  header: { ...current.header, email },
                })
              }
            />
            <AgentField
              label={a.fieldResumeCity}
              value={current.header.city}
              closeLabel={a.close}
              onChange={(city) =>
                setCurrent({
                  ...current,
                  header: { ...current.header, city },
                })
              }
            />

            {sections.includes("summary") ? (
              <AgentField
                label={a.fieldResumeSummary}
                value={current.summary.join("\n")}
                multiline
                closeLabel={a.close}
                onChange={(value) =>
                  setCurrent({ ...current, summary: linesOf(value) })
                }
              />
            ) : null}

            {sections.includes("education") ? (
              <section className="resume-block">
                <div className="resume-block-head">
                  <p className="text-sm font-semibold">{r.sectionEducation}</p>
                  <button
                    type="button"
                    className="btn-ghost text-sm"
                    onClick={() =>
                      setCurrent({
                        ...current,
                        education: [
                          ...current.education,
                          {
                            institution: "",
                            field: "",
                            degree: "",
                            start: "",
                            end: "",
                            city: "",
                            honor: "",
                            related_courses: [],
                          },
                        ],
                      })
                    }
                  >
                    {a.addEducation}
                  </button>
                </div>
                {current.education.map((item, index) => (
                  <div key={`edu-${index}`} className="resume-entry-form">
                    <AgentField
                      label={a.fieldInstitution}
                      value={item.institution}
                      closeLabel={a.close}
                      onChange={(institution) => {
                        const education = [...current.education];
                        education[index] = { ...item, institution };
                        setCurrent({ ...current, education });
                      }}
                    />
                    <AgentField
                      label={a.fieldMajor}
                      value={item.field}
                      closeLabel={a.close}
                      onChange={(field) => {
                        const education = [...current.education];
                        education[index] = { ...item, field };
                        setCurrent({ ...current, education });
                      }}
                    />
                    <AgentField
                      label={a.fieldDegree}
                      value={item.degree}
                      closeLabel={a.close}
                      onChange={(degree) => {
                        const education = [...current.education];
                        education[index] = { ...item, degree };
                        setCurrent({ ...current, education });
                      }}
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <label className="mb-3 block text-xs text-[var(--text-muted)]">
                        {a.fieldStart}
                        <input
                          className="field"
                          placeholder="YYYY-MM"
                          value={item.start}
                          onChange={(event) => {
                            const education = [...current.education];
                            education[index] = {
                              ...item,
                              start: event.target.value,
                            };
                            setCurrent({ ...current, education });
                          }}
                        />
                      </label>
                      <label className="mb-3 block text-xs text-[var(--text-muted)]">
                        {a.fieldEnd}
                        <input
                          className="field"
                          placeholder="YYYY-MM"
                          value={item.end}
                          onChange={(event) => {
                            const education = [...current.education];
                            education[index] = {
                              ...item,
                              end: event.target.value,
                            };
                            setCurrent({ ...current, education });
                          }}
                        />
                      </label>
                    </div>
                    <AgentField
                      label={a.fieldResumeCity}
                      value={item.city}
                      closeLabel={a.close}
                      onChange={(city) => {
                        const education = [...current.education];
                        education[index] = { ...item, city };
                        setCurrent({ ...current, education });
                      }}
                    />
                    <AgentField
                      label={a.fieldHonor}
                      value={item.honor}
                      closeLabel={a.close}
                      onChange={(honor) => {
                        const education = [...current.education];
                        education[index] = { ...item, honor };
                        setCurrent({ ...current, education });
                      }}
                    />
                    <AgentField
                      label={a.fieldCourses}
                      value={item.related_courses.join(", ")}
                      closeLabel={a.close}
                      onChange={(value) => {
                        const education = [...current.education];
                        education[index] = {
                          ...item,
                          related_courses: commasOf(value),
                        };
                        setCurrent({ ...current, education });
                      }}
                    />
                    <button
                      type="button"
                      className="btn-ghost text-sm"
                      onClick={() =>
                        setCurrent({
                          ...current,
                          education: current.education.filter(
                            (_, itemIndex) => itemIndex !== index,
                          ),
                        })
                      }
                    >
                      {a.removeEntry}
                    </button>
                  </div>
                ))}
              </section>
            ) : null}

            {sections.includes("internship") ? (
              <ExperienceList
                label={r.sectionInternship}
                items={current.internships}
                addLabel={a.addInternship}
                dict={dict}
                onAdd={() =>
                  setCurrent({
                    ...current,
                    internships: [
                      ...current.internships,
                      {
                        organization: "",
                        role: "",
                        start: "",
                        end: "",
                        city: "",
                        description: [],
                      },
                    ],
                  })
                }
                onChange={(internships) => setCurrent({ ...current, internships })}
              />
            ) : null}

            {sections.includes("projects") ? (
              <section className="resume-block">
                <div className="resume-block-head">
                  <p className="text-sm font-semibold">{r.sectionProjects}</p>
                  <button
                    type="button"
                    className="btn-ghost text-sm"
                    onClick={() =>
                      setCurrent({
                        ...current,
                        projects: [
                          ...current.projects,
                          {
                            name: "",
                            start: "",
                            end: "",
                            tech_stack: [],
                            description: [],
                          },
                        ],
                      })
                    }
                  >
                    {a.addProject}
                  </button>
                </div>
                {current.projects.map((item, index) => (
                  <div key={`proj-${index}`} className="resume-entry-form">
                    <AgentField
                      label={a.fieldProjectName}
                      value={item.name}
                      closeLabel={a.close}
                      onChange={(name) => {
                        const projects = [...current.projects];
                        projects[index] = { ...item, name };
                        setCurrent({ ...current, projects });
                      }}
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <label className="mb-3 block text-xs text-[var(--text-muted)]">
                        {a.fieldStart}
                        <input
                          className="field"
                          placeholder="YYYY-MM"
                          value={item.start}
                          onChange={(event) => {
                            const projects = [...current.projects];
                            projects[index] = {
                              ...item,
                              start: event.target.value,
                            };
                            setCurrent({ ...current, projects });
                          }}
                        />
                      </label>
                      <label className="mb-3 block text-xs text-[var(--text-muted)]">
                        {a.fieldEnd}
                        <input
                          className="field"
                          placeholder="YYYY-MM"
                          value={item.end}
                          onChange={(event) => {
                            const projects = [...current.projects];
                            projects[index] = {
                              ...item,
                              end: event.target.value,
                            };
                            setCurrent({ ...current, projects });
                          }}
                        />
                      </label>
                    </div>
                    <AgentField
                      label={a.fieldTech}
                      value={item.tech_stack.join(", ")}
                      closeLabel={a.close}
                      onChange={(value) => {
                        const projects = [...current.projects];
                        projects[index] = {
                          ...item,
                          tech_stack: commasOf(value),
                        };
                        setCurrent({ ...current, projects });
                      }}
                    />
                    <AgentField
                      label={a.fieldBulletLines}
                      value={item.description.join("\n")}
                      multiline
                      closeLabel={a.close}
                      onChange={(value) => {
                        const projects = [...current.projects];
                        projects[index] = {
                          ...item,
                          description: linesOf(value),
                        };
                        setCurrent({ ...current, projects });
                      }}
                    />
                    <button
                      type="button"
                      className="btn-ghost text-sm"
                      onClick={() =>
                        setCurrent({
                          ...current,
                          projects: current.projects.filter(
                            (_, itemIndex) => itemIndex !== index,
                          ),
                        })
                      }
                    >
                      {a.removeEntry}
                    </button>
                  </div>
                ))}
              </section>
            ) : null}

            {sections.includes("activities") ? (
              <ExperienceList
                label={r.sectionActivities}
                items={current.activities}
                addLabel={a.addActivity}
                dict={dict}
                onAdd={() =>
                  setCurrent({
                    ...current,
                    activities: [
                      ...current.activities,
                      {
                        organization: "",
                        role: "",
                        start: "",
                        end: "",
                        city: "",
                        description: [],
                      },
                    ],
                  })
                }
                onChange={(activities) => setCurrent({ ...current, activities })}
              />
            ) : null}

            {sections.includes("skillsOthers") ? (
              <section className="resume-block">
                <AgentField
                  label={a.fieldResumeSkills}
                  value={current.skills.join(", ")}
                  closeLabel={a.close}
                  onChange={(value) =>
                    setCurrent({ ...current, skills: commasOf(value) })
                  }
                />
                <div className="resume-block-head">
                  <p className="text-sm font-semibold">{a.fieldLanguages}</p>
                  <button
                    type="button"
                    className="btn-ghost text-sm"
                    onClick={() =>
                      setCurrent({
                        ...current,
                        languages: [
                          ...current.languages,
                          { name: "", level: "" },
                        ],
                      })
                    }
                  >
                    {a.addLanguage}
                  </button>
                </div>
                {current.languages.map((item, index) => (
                  <div
                    key={`lang-${index}`}
                    className="grid grid-cols-2 gap-2"
                  >
                    <AgentField
                      label={a.fieldLanguageName}
                      value={item.name}
                      closeLabel={a.close}
                      onChange={(name) => {
                        const languages = [...current.languages];
                        languages[index] = { ...item, name };
                        setCurrent({ ...current, languages });
                      }}
                    />
                    <AgentField
                      label={a.fieldLanguageLevel}
                      value={item.level}
                      closeLabel={a.close}
                      onChange={(level) => {
                        const languages = [...current.languages];
                        languages[index] = { ...item, level };
                        setCurrent({ ...current, languages });
                      }}
                    />
                  </div>
                ))}
              </section>
            ) : null}

            {(current.extras ?? []).map((extra, index) => (
              <section key={extra.slug} className="resume-block">
                <AgentField
                  label={a.fieldLayoutName}
                  value={extra.title}
                  closeLabel={a.close}
                  onChange={(title) => {
                    const extras = [...(current.extras ?? [])];
                    extras[index] = { ...extra, title };
                    setCurrent({ ...current, extras });
                  }}
                />
                <AgentField
                  label={a.fieldBulletLines}
                  value={extra.lines.join("\n")}
                  multiline
                  closeLabel={a.close}
                  onChange={(value) => {
                    const extras = [...(current.extras ?? [])];
                    extras[index] = { ...extra, lines: linesOf(value) };
                    setCurrent({ ...current, extras });
                  }}
                />
                <ExperienceList
                  label={extra.title || a.addSection}
                  items={extra.entries}
                  addLabel={a.addActivity}
                  dict={dict}
                  onAdd={() => {
                    const extras = [...(current.extras ?? [])];
                    extras[index] = {
                      ...extra,
                      entries: [
                        ...extra.entries,
                        {
                          organization: "",
                          role: "",
                          start: "",
                          end: "",
                          city: "",
                          description: [],
                        },
                      ],
                    };
                    setCurrent({ ...current, extras });
                  }}
                  onChange={(entries) => {
                    const extras = [...(current.extras ?? [])];
                    extras[index] = { ...extra, entries };
                    setCurrent({ ...current, extras });
                  }}
                />
                <button
                  type="button"
                  className="btn-ghost text-sm"
                  onClick={() =>
                    setCurrent({
                      ...current,
                      extras: (current.extras ?? []).filter(
                        (_, itemIndex) => itemIndex !== index,
                      ),
                    })
                  }
                >
                  {a.removeEntry}
                </button>
              </section>
            ))}

            <div className="resume-studio-add">
              <input
                className="field"
                placeholder={a.addSectionName}
                value={extraTitle}
                onChange={(event) => setExtraTitle(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key !== "Enter" || !current) return;
                  event.preventDefault();
                  const title = extraTitle.trim();
                  if (!title) return;
                  const used = new Set((current.extras ?? []).map((item) => item.slug));
                  let slug = slugify(title) || "extra";
                  let n = 2;
                  while (used.has(slug)) {
                    slug = `${slugify(title) || "extra"}-${n}`;
                    n += 1;
                  }
                  setCurrent({
                    ...current,
                    extras: [
                      ...(current.extras ?? []),
                      { slug, title, lines: [], entries: [] },
                    ],
                  });
                  setExtraTitle("");
                }}
              />
              <button
                type="button"
                className="btn-cta"
                onClick={() => {
                  const title = extraTitle.trim();
                  if (!title || !current) return;
                  const used = new Set((current.extras ?? []).map((item) => item.slug));
                  let slug = slugify(title) || "extra";
                  let n = 2;
                  while (used.has(slug)) {
                    slug = `${slugify(title) || "extra"}-${n}`;
                    n += 1;
                  }
                  setCurrent({
                    ...current,
                    extras: [
                      ...(current.extras ?? []),
                      { slug, title, lines: [], entries: [] },
                    ],
                  });
                  setExtraTitle("");
                }}
              >
                {a.addSection}
              </button>
            </div>

            <div className="resume-import">
              <p className="text-sm font-semibold">{a.importGithub}</p>
              <input
                className="field"
                placeholder={a.fieldGithubRepo}
                value={githubRepo}
                onChange={(event) => setGithubRepo(event.target.value)}
              />
              <input
                className="field"
                placeholder={a.fieldGithubPath}
                value={githubPath}
                onChange={(event) => setGithubPath(event.target.value)}
              />
              <input
                className="field"
                placeholder={a.fieldGithubRef}
                value={githubRef}
                onChange={(event) => setGithubRef(event.target.value)}
              />
              <button
                type="button"
                className="btn-ghost"
                disabled={saving}
                onClick={async () => {
                  const token = getSessionToken();
                  if (!token) return;
                  setSaving(true);
                  try {
                    const imported = await importOwnerResumeFromGithub(token, {
                      fullName: githubRepo,
                      path: githubPath,
                      ref: githubRef,
                      slug:
                        current.slug ||
                        slugify(current.header.name || current.title) ||
                        "imported-resume",
                    });
                    setCurrent(imported);
                    await reload(token);
                    setMessage(a.saved);
                  } catch {
                    setError(a.errorGeneric);
                  } finally {
                    setSaving(false);
                  }
                }}
              >
                {saving ? a.importing : a.importNow}
              </button>
            </div>
          </CmsCard>

          <div className="resume-preview-col">
            <CmsCard
              title={a.visualCv}
              action={
                <div className="flex flex-wrap gap-2">
                  {current.id ? (
                    <button
                      type="button"
                      className="btn-ghost text-sm"
                      onClick={() => setConfirmResume(true)}
                    >
                      {a.deleteResume}
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="btn-cta"
                    disabled={saving}
                    onClick={() => void persistResume(current)}
                  >
                    {saving ? a.saving : a.save}
                  </button>
                </div>
              }
            >
              <ResumePaper
                resume={current}
                dict={dict}
                sections={sections}
                showEmpty
              />
              <div className="resume-actions">
                <button
                  type="button"
                  className="btn-ghost"
                  disabled={saving || !current.id}
                  onClick={async () => {
                    const token = getSessionToken();
                    if (!token || !current.id) return;
                    setSaving(true);
                    try {
                      const next = await generateOwnerResume(token, current.id);
                      setCurrent(next);
                      setMessage(a.generatedPdf);
                    } catch {
                      setError(a.errorGeneric);
                    } finally {
                      setSaving(false);
                    }
                  }}
                >
                  {saving ? a.generatingPdf : a.generatePdf}
                </button>
                <button
                  type="button"
                  className="btn-ghost"
                  disabled={saving || !current.id}
                  onClick={async () => {
                    const token = getSessionToken();
                    if (!token || !current.id) return;
                    setSaving(true);
                    try {
                      const pushed = await pushOwnerResumeToGithub(
                        token,
                        current.id,
                      );
                      setCurrent(pushed.resume);
                      await reload(token);
                      setMessage(
                        a.pushedCv.replace("{repo}", pushed.repo.fullName),
                      );
                    } catch (err) {
                      const text = err instanceof Error ? err.message : "";
                      setError(
                        text === "github_not_connected"
                          ? a.githubNotConnected
                          : a.errorGeneric,
                      );
                    } finally {
                      setSaving(false);
                    }
                  }}
                >
                  {saving ? a.pushingCv : a.pushCv}
                </button>
                {current.id ? (
                  <button
                    type="button"
                    className="btn-ghost"
                    disabled={saving}
                    onClick={async () => {
                      const token = getSessionToken();
                      if (!token) return;
                      setSaving(true);
                      try {
                        const next = await publishOwnerResume(token, current.id);
                        setCurrent(next);
                        await reload(token);
                        setMessage(a.saved);
                      } catch {
                        setError(a.errorGeneric);
                      } finally {
                        setSaving(false);
                      }
                    }}
                  >
                    {a.publishToSite}
                  </button>
                ) : null}
                {current.status === "published" && current.slug ? (
                  <Link
                    href={`/${locale}/resume/${current.slug}`}
                    className="btn-ghost"
                  >
                    {a.viewPublic}
                  </Link>
                ) : null}
              </div>
            </CmsCard>
          </div>
        </div>
      ) : null}

      <CmsModal
        open={openTemplate}
        title={
          templateDraft.id
            ? localizedText(templateDraft.name)
            : a.newLayout
        }
        closeLabel={a.close}
        onClose={() => setOpenTemplate(false)}
        footer={
          <>
            {templateDraft.id && !templateDraft.builtin ? (
              <button
                type="button"
                className="btn-ghost"
                onClick={() => setConfirmTemplate(true)}
              >
                {a.deleteLayout}
              </button>
            ) : null}
            <button
              type="button"
              className="btn-cta"
              disabled={saving || templateDraft.builtin}
              onClick={() => persistTemplate(templateDraft)}
            >
              {saving ? a.saving : a.save}
            </button>
          </>
        }
      >
        <ResumeLayoutStudio
          draft={templateDraft}
          dict={dict}
          disabled={templateDraft.builtin}
          onChange={setTemplateDraft}
        />
      </CmsModal>

      <CmsConfirm
        open={confirmResume}
        title={a.deleteResume}
        hint={a.confirmDeleteHint}
        confirmLabel={a.confirmDelete}
        closeLabel={a.close}
        onClose={() => setConfirmResume(false)}
        onConfirm={async () => {
          const token = getSessionToken();
          if (!token || !current?.id) return;
          await deleteOwnerResume(token, current.id);
          setConfirmResume(false);
          setCurrent(null);
          await reload(token);
        }}
      />
      <CmsConfirm
        open={confirmTemplate}
        title={a.deleteLayout}
        hint={a.confirmDeleteHint}
        confirmLabel={a.confirmDelete}
        closeLabel={a.close}
        onClose={() => setConfirmTemplate(false)}
        onConfirm={async () => {
          const token = getSessionToken();
          if (!token || !templateDraft.id) return;
          await deleteOwnerResumeTemplate(token, templateDraft.id);
          setConfirmTemplate(false);
          setOpenTemplate(false);
          await reload(token);
        }}
      />
    </div>
  );
}

function ExperienceList({
  label,
  items,
  addLabel,
  dict,
  onAdd,
  onChange,
}: {
  label: string;
  items: OwnerResume["internships"];
  addLabel: string;
  dict: Dictionary;
  onAdd: () => void;
  onChange: (next: OwnerResume["internships"]) => void;
}) {
  const a = dict.admin;
  return (
    <section className="resume-block">
      <div className="resume-block-head">
        <p className="text-sm font-semibold">{label}</p>
        <button type="button" className="btn-ghost text-sm" onClick={onAdd}>
          {addLabel}
        </button>
      </div>
      {items.map((item, index) => (
        <div key={`${label}-${index}`} className="resume-entry-form">
          <AgentField
            label={a.fieldOrganization}
            value={item.organization}
            closeLabel={a.close}
            onChange={(organization) => {
              const next = [...items];
              next[index] = { ...item, organization };
              onChange(next);
            }}
          />
          <AgentField
            label={a.fieldRole}
            value={item.role}
            closeLabel={a.close}
            onChange={(role) => {
              const next = [...items];
              next[index] = { ...item, role };
              onChange(next);
            }}
          />
          <div className="grid grid-cols-2 gap-2">
            <label className="mb-3 block text-xs text-[var(--text-muted)]">
              {a.fieldStart}
              <input
                className="field"
                placeholder="YYYY-MM"
                value={item.start}
                onChange={(event) => {
                  const next = [...items];
                  next[index] = { ...item, start: event.target.value };
                  onChange(next);
                }}
              />
            </label>
            <label className="mb-3 block text-xs text-[var(--text-muted)]">
              {a.fieldEnd}
              <input
                className="field"
                placeholder="YYYY-MM"
                value={item.end}
                onChange={(event) => {
                  const next = [...items];
                  next[index] = { ...item, end: event.target.value };
                  onChange(next);
                }}
              />
            </label>
          </div>
          <AgentField
            label={a.fieldResumeCity}
            value={item.city}
            closeLabel={a.close}
            onChange={(city) => {
              const next = [...items];
              next[index] = { ...item, city };
              onChange(next);
            }}
          />
          <AgentField
            label={a.fieldBulletLines}
            value={item.description.join("\n")}
            multiline
            closeLabel={a.close}
            onChange={(value) => {
              const next = [...items];
              next[index] = { ...item, description: linesOf(value) };
              onChange(next);
            }}
          />
          <button
            type="button"
            className="btn-ghost text-sm"
            onClick={() =>
              onChange(items.filter((_, itemIndex) => itemIndex !== index))
            }
          >
            {a.removeEntry}
          </button>
        </div>
      ))}
    </section>
  );
}
