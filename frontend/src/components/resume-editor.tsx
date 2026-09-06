"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { getDictionary, type Dictionary } from "@/i18n/dictionaries";
import { isLocale, localeLabels, type Locale } from "@/i18n/config";
import {
  analyzeOwnerResumeGithubProject,
  createOwnerResume,
  createOwnerResumeTemplate,
  deleteOwnerResume,
  deleteOwnerResumeTemplate,
  emptyOwnerResume,
  emptyOwnerResumeTemplate,
  fetchOwnerGitHubRepos,
  fetchOwnerResumeTemplates,
  fetchOwnerResumes,
  generateOwnerResume,
  getSessionToken,
  importOwnerResumeFromGithub,
  localizedText,
  localizedTextFor,
  publishOwnerResume,
  pushOwnerResumeToGithub,
  saveOwnerResume,
  saveOwnerResumeTemplate,
  type OwnerResume,
  type OwnerResumeTemplate,
  type ResumeSectionId,
  type SourceRepo,
} from "@/lib/api";
import { splitResumeLines } from "@/lib/resume-lines";
import { AgentField } from "./agent-field";
import { CmsCard, StatusPill } from "./cms-card";
import { CmsConfirm } from "./cms-confirm";
import { CmsModal } from "./cms-modal";
import { ResumeLayoutStudio } from "./resume-layout-studio";
import { ResumePaper } from "./resume-paper";

type Props = {
  locale: Locale;
  dict: Dictionary;
  active?: boolean;
};

function resumePaperDict(resumeLocale: string, fallback: Dictionary) {
  return isLocale(resumeLocale)
    ? getDictionary(resumeLocale).resume
    : fallback.resume;
}

function isEmptyResume(item: OwnerResume) {
  return (
    !item.header.name.trim() &&
    !item.summary.length &&
    !item.education.length &&
    !item.internships.length &&
    !(item.workExperiences ?? []).length &&
    !item.projects.length &&
    !item.activities.length &&
    !item.skills.length &&
    !item.languages.length &&
    !(item.extras ?? []).length
  );
}

function CollapsibleBlock({
  id,
  title,
  collapsed,
  onToggle,
  action,
  children,
}: {
  id: string;
  title: string;
  collapsed: boolean;
  onToggle: (id: string) => void;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className={`resume-block${collapsed ? " is-collapsed" : ""}`}>
      <div className="resume-block-head">
        <button
          type="button"
          className="resume-block-toggle"
          aria-expanded={!collapsed}
          onClick={() => onToggle(id)}
        >
          <i />
          <p className="text-sm font-semibold">{title}</p>
        </button>
        {action}
      </div>
      <div className="resume-block-body">{children}</div>
    </section>
  );
}

function slugify(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 40);
}

function linesOf(value: string) {
  return splitResumeLines(value);
}

function formatUpdated(value: string | undefined, locale: Locale) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(locale === "en" ? "en-GB" : locale, {
    month: "short",
    day: "numeric",
  }).format(date);
}

function commasOf(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function ResumeEditor({ locale, dict, active = true }: Props) {
  const a = dict.admin;
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
  const [pickGithubOpen, setPickGithubOpen] = useState(false);
  const [githubRepos, setGithubRepos] = useState<SourceRepo[]>([]);
  const [githubReady, setGithubReady] = useState(false);
  const [repoQuery, setRepoQuery] = useState("");
  const [analyzingIndex, setAnalyzingIndex] = useState<number | null>(null);
  const [extraTitle, setExtraTitle] = useState("");
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const currentRef = useRef<OwnerResume | null>(null);
  const dirtyRef = useRef(false);
  const baselineRef = useRef("");
  const persistRef = useRef<(next: OwnerResume, silent?: boolean) => Promise<void>>(
    async () => {},
  );

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

  const paper = resumePaperDict(current?.locale ?? locale, dict);

  function sectionLabel(id: string) {
    const extra = templates
      .flatMap((item) => item.extras ?? [])
      .find((item) => item.slug === id);
    if (extra) return extra.title || extra.slug;
    const onResume = current?.extras?.find((item) => item.slug === id);
    if (onResume) return onResume.title || onResume.slug;
    const map: Record<ResumeSectionId, string> = {
      summary: paper.sectionSummary,
      education: paper.sectionEducation,
      internship: paper.sectionInternship,
      work: paper.sectionWork,
      projects: paper.sectionProjects,
      activities: paper.sectionActivities,
      skillsOthers: paper.sectionSkills,
    };
    return map[id as ResumeSectionId] || id;
  }

  function toggleBlock(id: string) {
    setCollapsed((current) => ({ ...current, [id]: !current[id] }));
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
  const filteredRepos = useMemo(() => {
    const q = repoQuery.trim().toLowerCase();
    if (!q) return githubRepos;
    return githubRepos.filter(
      (repo) =>
        repo.fullName.toLowerCase().includes(q) ||
        (repo.description ?? "").toLowerCase().includes(q),
    );
  }, [githubRepos, repoQuery]);

  async function openGithubPicker() {
    const token = getSessionToken();
    if (!token) return;
    setRepoQuery("");
    setPickGithubOpen(true);
    try {
      const repos = await fetchOwnerGitHubRepos(token);
      setGithubReady(repos !== null);
      setGithubRepos(repos ?? []);
    } catch {
      setGithubReady(false);
      setGithubRepos([]);
    }
  }

  async function typeProjectCopy(
    index: number,
    tech: string,
    description: string,
  ) {
    for (let step = 1; step <= tech.length; step += 1) {
      const next = tech.slice(0, step);
      setCurrent((prev) => {
        if (!prev || !prev.projects[index]) return prev;
        const projects = [...prev.projects];
        projects[index] = { ...projects[index], tech_stack: commasOf(next) };
        return { ...prev, projects };
      });
      await new Promise((resolve) => window.setTimeout(resolve, 8));
    }
    for (let step = 1; step <= description.length; step += 1) {
      const next = description.slice(0, step);
      setCurrent((prev) => {
        if (!prev || !prev.projects[index]) return prev;
        const projects = [...prev.projects];
        projects[index] = { ...projects[index], description: linesOf(next) };
        return { ...prev, projects };
      });
      await new Promise((resolve) => window.setTimeout(resolve, 8));
    }
  }

  async function addProjectFromRepo(repo: SourceRepo) {
    if (!current) return;
    const token = getSessionToken();
    const entry = {
      name: repo.name,
      start: "",
      end: "",
      tech_stack: [] as string[],
      description: [] as string[],
    };
    const index = current.projects.length;
    setCurrent({ ...current, projects: [...current.projects, entry] });
    setPickGithubOpen(false);
    setCollapsed((state) => ({ ...state, projects: false }));
    if (!token) return;
    setAnalyzingIndex(index);
    try {
      const analyzed = await analyzeOwnerResumeGithubProject(token, {
        fullName: repo.fullName,
        locale: current.locale,
      });
      setCurrent((prev) => {
        if (!prev || !prev.projects[index]) return prev;
        const projects = [...prev.projects];
        projects[index] = {
          ...projects[index],
          name: analyzed.name || repo.name,
        };
        return { ...prev, projects };
      });
      setAnalyzingIndex(null);
      await typeProjectCopy(
        index,
        analyzed.tech_stack.join(", "),
        analyzed.description.join("\n"),
      );
    } catch {
      setError(a.errorGeneric);
      setAnalyzingIndex(null);
    }
  }

  async function persistResume(next: OwnerResume, silent = false) {
    const token = getSessionToken();
    if (!token) return;
    if (silent && isEmptyResume(next)) return;
    if (!silent) {
      setSaving(true);
      setError(null);
    }
    try {
      const payload = {
        ...next,
        workExperiences: next.workExperiences ?? [],
        title: next.header.name.trim() || next.title.trim() || next.slug,
        slug:
          next.slug ||
          slugify(next.header.name || next.title) ||
          "resume",
      };
      const saved = next.id
        ? await saveOwnerResume(token, next.id, payload)
        : await createOwnerResume(token, payload);
      baselineRef.current = JSON.stringify(saved);
      dirtyRef.current = false;
      setCurrent(saved);
      await reload(token);
      if (!silent) setMessage(a.saved);
    } catch {
      if (!silent) setError(a.errorGeneric);
    } finally {
      if (!silent) setSaving(false);
    }
  }
  persistRef.current = persistResume;

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
    const next = {
      ...emptyOwnerResume(),
      templateSlug: templates[0]?.slug || "classic-a4",
    };
    baselineRef.current = JSON.stringify(next);
    dirtyRef.current = false;
    setCurrent(next);
    setMessage(null);
    setError(null);
  }

  function openResume(item: OwnerResume) {
    const next = {
      ...item,
      extras: item.extras ?? [],
      workExperiences: item.workExperiences ?? [],
    };
    baselineRef.current = JSON.stringify(next);
    dirtyRef.current = false;
    setCurrent(next);
    setMessage(null);
    setError(null);
  }

  useEffect(() => {
    currentRef.current = current;
    if (!current || !baselineRef.current) return;
    dirtyRef.current = JSON.stringify(current) !== baselineRef.current;
  }, [current]);

  useEffect(() => {
    async function flush() {
      const next = currentRef.current;
      if (!next || !dirtyRef.current) return;
      await persistRef.current(next, true);
    }
    function onLeave() {
      void flush();
    }
    function onHidden() {
      if (document.visibilityState === "hidden") onLeave();
    }
    window.addEventListener("pagehide", onLeave);
    document.addEventListener("visibilitychange", onHidden);
    window.addEventListener("beforeunload", onLeave);
    return () => {
      window.removeEventListener("pagehide", onLeave);
      document.removeEventListener("visibilitychange", onHidden);
      window.removeEventListener("beforeunload", onLeave);
    };
  }, []);

  useEffect(() => {
    if (active) return;
    const next = currentRef.current;
    if (!next || !dirtyRef.current) return;
    void persistRef.current(next, true);
  }, [active]);

  const extras = current?.extras ?? [];
  const extraBySlug = new Map(extras.map((item) => [item.slug, item]));
  const editorOrder = (() => {
    const seen = new Set<string>();
    return [...sections, ...extras.map((item) => item.slug)].filter((id) => {
      if (seen.has(id)) return false;
      seen.add(id);
      return true;
    });
  })();

  function renderEditorSection(id: string) {
    if (!current) return null;
    const folded = Boolean(collapsed[id]);
    if (id === "summary") {
      return (
        <CollapsibleBlock
          key={id}
          id={id}
          title={paper.sectionSummary}
          collapsed={folded}
          onToggle={toggleBlock}
        >
          <AgentField
            label={a.fieldResumeSummary}
            value={current.summary.join("\n")}
            multiline
            closeLabel={a.close}
            onChange={(value) =>
              setCurrent({ ...current, summary: linesOf(value) })
            }
          />
        </CollapsibleBlock>
      );
    }
    if (id === "education") {
      return (
        <CollapsibleBlock
          key={id}
          id={id}
          title={paper.sectionEducation}
          collapsed={folded}
          onToggle={toggleBlock}
          action={
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
          }
        >
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
                    value={item.start}
                    onChange={(event) => {
                      const education = [...current.education];
                      education[index] = { ...item, start: event.target.value };
                      setCurrent({ ...current, education });
                    }}
                  />
                </label>
                <label className="mb-3 block text-xs text-[var(--text-muted)]">
                  {a.fieldEnd}
                  <input
                    className="field"
                    value={item.end}
                    onChange={(event) => {
                      const education = [...current.education];
                      education[index] = { ...item, end: event.target.value };
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
        </CollapsibleBlock>
      );
    }
    if (id === "internship" || id === "work") {
      const items =
        id === "work"
          ? current.workExperiences ?? []
          : current.internships;
      return (
        <ExperienceList
          key={id}
          id={id}
          label={id === "work" ? paper.sectionWork : paper.sectionInternship}
          items={items}
          addLabel={id === "work" ? a.addWork : a.addInternship}
          dict={dict}
          collapsed={folded}
          onToggle={toggleBlock}
          onAdd={() => {
            const empty = {
              organization: "",
              role: "",
              start: "",
              end: "",
              city: "",
              description: [],
            };
            if (id === "work") {
              setCurrent({
                ...current,
                workExperiences: [...(current.workExperiences ?? []), empty],
              });
              return;
            }
            setCurrent({
              ...current,
              internships: [...current.internships, empty],
            });
          }}
          onChange={(next) =>
            setCurrent(
              id === "work"
                ? { ...current, workExperiences: next }
                : { ...current, internships: next },
            )
          }
        />
      );
    }
    if (id === "projects") {
      return (
        <CollapsibleBlock
          key={id}
          id={id}
          title={paper.sectionProjects}
          collapsed={folded}
          onToggle={toggleBlock}
          action={
            <div className="flex flex-wrap gap-2">
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
              <button
                type="button"
                className="btn-ghost text-sm"
                disabled={analyzingIndex !== null}
                onClick={() => void openGithubPicker()}
              >
                {a.addProjectGithub}
              </button>
            </div>
          }
        >
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
                    value={item.start}
                    onChange={(event) => {
                      const projects = [...current.projects];
                      projects[index] = { ...item, start: event.target.value };
                      setCurrent({ ...current, projects });
                    }}
                  />
                </label>
                <label className="mb-3 block text-xs text-[var(--text-muted)]">
                  {a.fieldEnd}
                  <input
                    className="field"
                    value={item.end}
                    onChange={(event) => {
                      const projects = [...current.projects];
                      projects[index] = { ...item, end: event.target.value };
                      setCurrent({ ...current, projects });
                    }}
                  />
                </label>
              </div>
              <AgentField
                label={a.fieldTech}
                value={item.tech_stack.join(", ")}
                closeLabel={a.close}
                pending={analyzingIndex === index}
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
                pending={analyzingIndex === index}
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
        </CollapsibleBlock>
      );
    }
    if (id === "activities") {
      return (
        <ExperienceList
          key={id}
          id={id}
          label={paper.sectionActivities}
          items={current.activities}
          addLabel={a.addActivity}
          dict={dict}
          collapsed={folded}
          onToggle={toggleBlock}
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
      );
    }
    if (id === "skillsOthers") {
      return (
        <CollapsibleBlock
          key={id}
          id={id}
          title={paper.sectionSkills}
          collapsed={folded}
          onToggle={toggleBlock}
          action={
            <button
              type="button"
              className="btn-ghost text-sm"
              onClick={() =>
                setCurrent({
                  ...current,
                  languages: [...current.languages, { name: "", level: "" }],
                })
              }
            >
              {a.addLanguage}
            </button>
          }
        >
          <AgentField
            label={a.fieldResumeSkills}
            value={current.skills.join(", ")}
            closeLabel={a.close}
            onChange={(value) =>
              setCurrent({ ...current, skills: commasOf(value) })
            }
          />
          {current.languages.map((item, index) => (
            <div key={`lang-${index}`} className="grid grid-cols-2 gap-2">
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
        </CollapsibleBlock>
      );
    }
    const extra = extraBySlug.get(id);
    const extraIndex = extras.findIndex((item) => item.slug === id);
    if (!extra || extraIndex < 0) return null;
    return (
      <CollapsibleBlock
        key={id}
        id={id}
        title={extra.title || id}
        collapsed={folded}
        onToggle={toggleBlock}
        action={
          <button
            type="button"
            className="btn-ghost text-sm"
            onClick={() =>
              setCurrent({
                ...current,
                extras: extras.filter((_, itemIndex) => itemIndex !== extraIndex),
              })
            }
          >
            {a.removeEntry}
          </button>
        }
      >
        <AgentField
          label={a.fieldLayoutName}
          value={extra.title}
          closeLabel={a.close}
          onChange={(title) => {
            const next = [...extras];
            next[extraIndex] = { ...extra, title };
            setCurrent({ ...current, extras: next });
          }}
        />
        <AgentField
          label={a.fieldBulletLines}
          value={extra.lines.join("\n")}
          multiline
          closeLabel={a.close}
          onChange={(value) => {
            const next = [...extras];
            next[extraIndex] = { ...extra, lines: linesOf(value) };
            setCurrent({ ...current, extras: next });
          }}
        />
        <ExperienceList
          id={`${id}-entries`}
          label={extra.title || a.addSection}
          items={extra.entries}
          addLabel={a.addActivity}
          dict={dict}
          collapsed={Boolean(collapsed[`${id}-entries`])}
          onToggle={toggleBlock}
          onAdd={() => {
            const next = [...extras];
            next[extraIndex] = {
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
            setCurrent({ ...current, extras: next });
          }}
          onChange={(entries) => {
            const next = [...extras];
            next[extraIndex] = { ...extra, entries };
            setCurrent({ ...current, extras: next });
          }}
        />
      </CollapsibleBlock>
    );
  }

  if (loading) {
    return <p className="text-[var(--text-muted)]">{a.loadingResumes}</p>;
  }

  return (
    <div className="resume-workspace">
      <div className="resume-docs">
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
                    onClick={() => openResume(item)}
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
                    <span className="resume-pick-meta">
                      {[
                        itemLayout
                          ? localizedTextFor(itemLayout.name, locale)
                          : "",
                        localeLabels[item.locale] ?? item.locale,
                        formatUpdated(item.updatedAt, locale),
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </span>
                    {item.summary[0] ? (
                      <span className="resume-pick-headline">
                        {item.summary[0]}
                      </span>
                    ) : null}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </CmsCard>
      </div>

      {current ? (
        <div className="resume-edit-grid">
          <div className="resume-form-col">
          <CmsCard title={current.title || current.header.name || a.newResume}>
            {message ? (
              <p className="mb-3 text-sm text-[var(--success)]">{message}</p>
            ) : null}
            {error ? (
              <p className="mb-3 text-sm text-[var(--danger)]">{error}</p>
            ) : null}

            <CollapsibleBlock
              id="layout"
              title={a.fieldResumeLayout}
              collapsed={Boolean(collapsed.layout)}
              onToggle={toggleBlock}
            >
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
                    <strong>
                      {localizedTextFor(item.name, locale) || item.slug}
                    </strong>
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
            </CollapsibleBlock>

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

            {editorOrder.map((id) => renderEditorSection(id))}

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

            <CollapsibleBlock
              id="import"
              title={a.importGithub}
              collapsed={Boolean(collapsed.import)}
              onToggle={toggleBlock}
            >
              <div className="resume-import">
                <label className="block text-xs text-[var(--text-muted)]">
                  {a.fieldGithubRepo}
                  <input
                    className="field"
                    value={githubRepo}
                    onChange={(event) => setGithubRepo(event.target.value)}
                  />
                </label>
                <label className="block text-xs text-[var(--text-muted)]">
                  {a.fieldGithubPath}
                  <input
                    className="field"
                    value={githubPath}
                    onChange={(event) => setGithubPath(event.target.value)}
                  />
                </label>
                <label className="block text-xs text-[var(--text-muted)]">
                  {a.fieldGithubRef}
                  <input
                    className="field"
                    value={githubRef}
                    onChange={(event) => setGithubRef(event.target.value)}
                  />
                </label>
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
            </CollapsibleBlock>
          </CmsCard>
          </div>

          <div className="resume-preview-col">
            <CmsCard
              title={a.visualCv}
              action={
                <div className="flex flex-wrap gap-2">
                  {layout && !layout.builtin ? (
                    <button
                      type="button"
                      className="btn-ghost text-sm"
                      onClick={() => openLayoutEditor(layout)}
                    >
                      {a.editLayout}
                    </button>
                  ) : null}
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
        open={pickGithubOpen}
        title={a.addProjectGithub}
        closeLabel={a.close}
        onClose={() => setPickGithubOpen(false)}
        footer={
          <button
            type="button"
            className="btn-ghost"
            onClick={() => setPickGithubOpen(false)}
          >
            {a.close}
          </button>
        }
      >
        {!githubReady ? (
          <p className="text-sm text-[var(--text-muted)]">
            {a.githubDisconnectedHint}
          </p>
        ) : (
          <>
            <label className="mb-3 block text-xs text-[var(--text-muted)]">
              {a.fieldRepos}
              <input
                className="field"
                value={repoQuery}
                onChange={(event) => setRepoQuery(event.target.value)}
              />
            </label>
            {filteredRepos.length === 0 ? (
              <p className="text-sm text-[var(--text-muted)]">
                {a.noMatchingRepos}
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {filteredRepos.map((repo) => (
                  <li key={repo.fullName}>
                    <button
                      type="button"
                      className="tile w-full text-left"
                      onClick={() => void addProjectFromRepo(repo)}
                    >
                      <strong>{repo.name}</strong>
                      <span className="ml-2 font-mono text-xs text-[var(--text-muted)]">
                        {repo.fullName}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </CmsModal>

      <CmsModal
        open={openTemplate}
        title={
          templateDraft.id
            ? localizedTextFor(templateDraft.name, locale)
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
  id,
  label,
  items,
  addLabel,
  dict,
  collapsed,
  onToggle,
  onAdd,
  onChange,
}: {
  id: string;
  label: string;
  items: OwnerResume["internships"];
  addLabel: string;
  dict: Dictionary;
  collapsed: boolean;
  onToggle: (id: string) => void;
  onAdd: () => void;
  onChange: (next: OwnerResume["internships"]) => void;
}) {
  const a = dict.admin;
  return (
    <CollapsibleBlock
      id={id}
      title={label}
      collapsed={collapsed}
      onToggle={onToggle}
      action={
        <button type="button" className="btn-ghost text-sm" onClick={onAdd}>
          {addLabel}
        </button>
      }
    >
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
    </CollapsibleBlock>
  );
}
