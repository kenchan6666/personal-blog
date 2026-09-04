"use client";

import { useEffect, useState } from "react";
import type { Dictionary } from "@/i18n/dictionaries";
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
  pushOwnerResumeToGithub,
  localizedText,
  publishOwnerResume,
  saveOwnerResume,
  saveOwnerResumeTemplate,
  type OwnerResume,
  type OwnerResumeTemplate,
  type ResumeSectionId,
} from "@/lib/api";
import { CmsCard, StatusPill } from "./cms-card";
import { CmsConfirm } from "./cms-confirm";
import { CmsModal } from "./cms-modal";
import { ResumePaper } from "./resume-paper";

type Props = {
  dict: Dictionary;
};

const SECTION_IDS: ResumeSectionId[] = [
  "summary",
  "education",
  "internship",
  "projects",
  "activities",
  "skillsOthers",
];

function slugify(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 40);
}

export function ResumeEditor({ dict }: Props) {
  const a = dict.admin;
  const r = dict.resume;
  const [templates, setTemplates] = useState<OwnerResumeTemplate[]>([]);
  const [resumes, setResumes] = useState<OwnerResume[]>([]);
  const [current, setCurrent] = useState<OwnerResume>(emptyOwnerResume());
  const [templateDraft, setTemplateDraft] = useState<OwnerResumeTemplate>(
    emptyOwnerResumeTemplate(),
  );
  const [openResume, setOpenResume] = useState(false);
  const [openTemplate, setOpenTemplate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmResume, setConfirmResume] = useState(false);
  const [confirmTemplate, setConfirmTemplate] = useState(false);
  const [githubRepo, setGithubRepo] = useState("");
  const [githubPath, setGithubPath] = useState("cv/classic.format.json");
  const [githubRef, setGithubRef] = useState("");

  async function reload(token: string) {
    const [nextTemplates, nextResumes] = await Promise.all([
      fetchOwnerResumeTemplates(token),
      fetchOwnerResumes(token),
    ]);
    setTemplates(nextTemplates);
    setResumes(nextResumes);
  }

  useEffect(() => {
    const token = getSessionToken();
    if (!token) return;
    reload(token)
      .catch(() => setError(a.errorGeneric))
      .finally(() => setLoading(false));
  }, [a.errorGeneric]);

  function sectionLabel(id: ResumeSectionId) {
    const map = {
      summary: r.sectionSummary,
      education: r.sectionEducation,
      internship: r.sectionInternship,
      projects: r.sectionProjects,
      activities: r.sectionActivities,
      skillsOthers: r.sectionSkills,
    };
    return map[id];
  }

  async function persistResume(next: OwnerResume) {
    const token = getSessionToken();
    if (!token) return;
    setSaving(true);
    setError(null);
    try {
      const saved = next.id
        ? await saveOwnerResume(token, next.id, next)
        : await createOwnerResume(token, {
            ...next,
            slug: next.slug || slugify(next.title || next.header.name) || "resume",
          });
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
        slug: next.slug || slugify(localizedText(next.name)) || "template",
        name: next.name,
        sections: next.sections,
      };
      if (next.id) await saveOwnerResumeTemplate(token, next.id, body);
      else await createOwnerResumeTemplate(token, body);
      await reload(token);
      setOpenTemplate(false);
      setMessage(a.saved);
    } catch {
      setError(a.errorGeneric);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="text-[var(--text-muted)]">{a.loadingResumes}</p>;
  }

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <CmsCard
        title={a.resumeTemplates}
        action={
          <button
            type="button"
            className="btn-ghost"
            onClick={() => {
              setTemplateDraft(emptyOwnerResumeTemplate());
              setOpenTemplate(true);
            }}
          >
            {a.newTemplate}
          </button>
        }
      >
        {templates.length === 0 ? (
          <p className="text-sm text-[var(--text-muted)]">{a.emptyTemplates}</p>
        ) : (
          <ul className="grid gap-3">
            {templates.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className="tile w-full text-left"
                  onClick={() => {
                    setTemplateDraft(item);
                    setOpenTemplate(true);
                  }}
                >
                  <strong>{localizedText(item.name) || item.slug}</strong>
                  <span>{item.sections.map(sectionLabel).join(" · ")}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </CmsCard>

      <CmsCard
        title={a.resumeDocuments}
        action={
          <button
            type="button"
            className="btn-cta"
            onClick={() => {
              setCurrent({
                ...emptyOwnerResume(),
                templateSlug: templates[0]?.slug || "classic-a4",
              });
              setOpenResume(true);
              setMessage(null);
              setError(null);
            }}
          >
            {a.newResume}
          </button>
        }
      >
        {resumes.length === 0 ? (
          <p className="text-sm text-[var(--text-muted)]">{a.emptyResumes}</p>
        ) : (
          <ul className="grid gap-3">
            {resumes.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className="tile w-full text-left"
                  onClick={() => {
                    setCurrent(item);
                    setOpenResume(true);
                    setMessage(null);
                    setError(null);
                  }}
                >
                  <span className="flex items-center justify-between gap-3">
                    <strong>{item.title || item.header.name || a.untitledResume}</strong>
                    <StatusPill
                      published={item.status === "published"}
                      publishedLabel={a.statusPublished}
                      draftLabel={a.statusDraft}
                    />
                  </span>
                  <span>{item.slug}</span>
                  {item.githubRepo ? (
                    <span className="font-mono text-xs text-[var(--text-muted)]">
                      {item.githubRepo}
                    </span>
                  ) : null}
                </button>
              </li>
            ))}
          </ul>
        )}
      </CmsCard>

      <CmsModal
        open={openTemplate}
        title={templateDraft.id ? localizedText(templateDraft.name) : a.newTemplate}
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
                {a.deleteTemplate}
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
        <label className="mb-3 block text-xs text-[var(--text-muted)]">
          {a.fieldResumeSlug}
          <input
            className="field"
            value={templateDraft.slug}
            disabled={templateDraft.builtin}
            onChange={(event) =>
              setTemplateDraft({ ...templateDraft, slug: event.target.value })
            }
          />
        </label>
        <label className="mb-3 block text-xs text-[var(--text-muted)]">
          {a.fieldResumeTitle}
          <input
            className="field"
            value={templateDraft.name.en}
            disabled={templateDraft.builtin}
            onChange={(event) =>
              setTemplateDraft({
                ...templateDraft,
                name: {
                  ...templateDraft.name,
                  en: event.target.value,
                  "zh-Hant": event.target.value,
                  "zh-Hans": event.target.value,
                },
              })
            }
          />
        </label>
        <div className="grid gap-2">
          {SECTION_IDS.map((id) => (
            <label key={id} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                disabled={templateDraft.builtin}
                checked={templateDraft.sections.includes(id)}
                onChange={(event) => {
                  const sections = event.target.checked
                    ? [...templateDraft.sections, id]
                    : templateDraft.sections.filter((item) => item !== id);
                  setTemplateDraft({ ...templateDraft, sections });
                }}
              />
              {sectionLabel(id)}
            </label>
          ))}
        </div>
      </CmsModal>

      <CmsModal
        open={openResume}
        title={current.title || current.header.name || a.newResume}
        closeLabel={a.close}
        onClose={() => setOpenResume(false)}
        footer={
          <>
            {current.id ? (
              <button
                type="button"
                className="btn-ghost"
                onClick={() => setConfirmResume(true)}
              >
                {a.deleteResume}
              </button>
            ) : null}
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
                  const pushed = await pushOwnerResumeToGithub(token, current.id);
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
            <button
              type="button"
              className="btn-cta"
              disabled={saving}
              onClick={() => persistResume(current)}
            >
              {saving ? a.saving : a.save}
            </button>
          </>
        }
      >
        {message ? <p className="text-sm text-[var(--success)]">{message}</p> : null}
        {error ? <p className="text-sm text-[var(--danger)]">{error}</p> : null}
        <div className="grid gap-4 md:grid-cols-2">
          <div className="grid gap-3">
            <label className="mb-3 block text-xs text-[var(--text-muted)]">
              {a.fieldResumeTitle}
              <input
                className="field"
                value={current.title}
                onChange={(event) =>
                  setCurrent({ ...current, title: event.target.value })
                }
              />
            </label>
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
              {a.fieldResumeTemplate}
              <select
                className="field"
                value={current.templateSlug}
                onChange={(event) =>
                  setCurrent({ ...current, templateSlug: event.target.value })
                }
              >
                {templates.map((item) => (
                  <option key={item.id} value={item.slug}>
                    {localizedText(item.name) || item.slug}
                  </option>
                ))}
              </select>
            </label>
            <label className="mb-3 block text-xs text-[var(--text-muted)]">
              {a.fieldResumeName}
              <input
                className="field"
                value={current.header.name}
                onChange={(event) =>
                  setCurrent({
                    ...current,
                    header: { ...current.header, name: event.target.value },
                  })
                }
              />
            </label>
            <label className="mb-3 block text-xs text-[var(--text-muted)]">
              {a.fieldResumePhone}
              <input
                className="field"
                value={current.header.phone}
                onChange={(event) =>
                  setCurrent({
                    ...current,
                    header: { ...current.header, phone: event.target.value },
                  })
                }
              />
            </label>
            <label className="mb-3 block text-xs text-[var(--text-muted)]">
              {a.fieldResumeEmail}
              <input
                className="field"
                value={current.header.email}
                onChange={(event) =>
                  setCurrent({
                    ...current,
                    header: { ...current.header, email: event.target.value },
                  })
                }
              />
            </label>
            <label className="mb-3 block text-xs text-[var(--text-muted)]">
              {a.fieldResumeCity}
              <input
                className="field"
                value={current.header.city}
                onChange={(event) =>
                  setCurrent({
                    ...current,
                    header: { ...current.header, city: event.target.value },
                  })
                }
              />
            </label>
            <label className="mb-3 block text-xs text-[var(--text-muted)]">
              {a.fieldResumeSummary}
              <textarea
                className="field"
                rows={4}
                value={current.summary.join("\n")}
                onChange={(event) =>
                  setCurrent({
                    ...current,
                    summary: event.target.value.split("\n").filter(Boolean),
                  })
                }
              />
            </label>
            <label className="mb-3 block text-xs text-[var(--text-muted)]">
              {a.fieldResumeSkills}
              <input
                className="field"
                value={current.skills.join(", ")}
                onChange={(event) =>
                  setCurrent({
                    ...current,
                    skills: event.target.value
                      .split(",")
                      .map((item) => item.trim())
                      .filter(Boolean),
                  })
                }
              />
            </label>
            <button
              type="button"
              className="btn-ghost"
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
            {current.education.map((item, index) => (
              <div key={`edu-${index}`} className="grid gap-2 rounded-[var(--radius-card)] border border-[var(--hairline)] p-3">
                <input
                  className="field"
                  placeholder="Institution"
                  value={item.institution}
                  onChange={(event) => {
                    const education = [...current.education];
                    education[index] = { ...item, institution: event.target.value };
                    setCurrent({ ...current, education });
                  }}
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    className="field"
                    placeholder="YYYY-MM"
                    value={item.start}
                    onChange={(event) => {
                      const education = [...current.education];
                      education[index] = { ...item, start: event.target.value };
                      setCurrent({ ...current, education });
                    }}
                  />
                  <input
                    className="field"
                    placeholder="YYYY-MM"
                    value={item.end}
                    onChange={(event) => {
                      const education = [...current.education];
                      education[index] = { ...item, end: event.target.value };
                      setCurrent({ ...current, education });
                    }}
                  />
                </div>
              </div>
            ))}
            <button
              type="button"
              className="btn-ghost"
              onClick={() =>
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
            >
              {a.addInternship}
            </button>
            {current.internships.map((item, index) => (
              <div key={`intern-${index}`} className="grid gap-2 rounded-[var(--radius-card)] border border-[var(--hairline)] p-3">
                <input
                  className="field"
                  placeholder="Company"
                  value={item.organization}
                  onChange={(event) => {
                    const internships = [...current.internships];
                    internships[index] = { ...item, organization: event.target.value };
                    setCurrent({ ...current, internships });
                  }}
                />
                <input
                  className="field"
                  placeholder="Role"
                  value={item.role}
                  onChange={(event) => {
                    const internships = [...current.internships];
                    internships[index] = { ...item, role: event.target.value };
                    setCurrent({ ...current, internships });
                  }}
                />
                <textarea
                  className="field"
                  rows={3}
                  value={item.description.join("\n")}
                  onChange={(event) => {
                    const internships = [...current.internships];
                    internships[index] = {
                      ...item,
                      description: event.target.value.split("\n").filter(Boolean),
                    };
                    setCurrent({ ...current, internships });
                  }}
                />
              </div>
            ))}
            <button
              type="button"
              className="btn-ghost"
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
            {current.projects.map((item, index) => (
              <div key={`proj-${index}`} className="grid gap-2 rounded-[var(--radius-card)] border border-[var(--hairline)] p-3">
                <input
                  className="field"
                  placeholder="Project"
                  value={item.name}
                  onChange={(event) => {
                    const projects = [...current.projects];
                    projects[index] = { ...item, name: event.target.value };
                    setCurrent({ ...current, projects });
                  }}
                />
                <input
                  className="field"
                  placeholder="Python, Flask"
                  value={item.tech_stack.join(", ")}
                  onChange={(event) => {
                    const projects = [...current.projects];
                    projects[index] = {
                      ...item,
                      tech_stack: event.target.value
                        .split(",")
                        .map((part) => part.trim())
                        .filter(Boolean),
                    };
                    setCurrent({ ...current, projects });
                  }}
                />
                <textarea
                  className="field"
                  rows={3}
                  value={item.description.join("\n")}
                  onChange={(event) => {
                    const projects = [...current.projects];
                    projects[index] = {
                      ...item,
                      description: event.target.value.split("\n").filter(Boolean),
                    };
                    setCurrent({ ...current, projects });
                  }}
                />
              </div>
            ))}
            <div className="grid gap-2 rounded-[var(--radius-card)] border border-[var(--hairline)] p-3">
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
                      slug: current.slug || slugify(current.title) || "imported-resume",
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
            {current.id ? (
              <button
                type="button"
                className="btn-cta"
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
                {a.statusPublished}
              </button>
            ) : null}
          </div>
          <div>
            <p className="mb-2 text-sm text-[var(--text-muted)]">{a.preview}</p>
            <ResumePaper resume={current} dict={dict} />
          </div>
        </div>
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
          if (!token || !current.id) return;
          await deleteOwnerResume(token, current.id);
          setConfirmResume(false);
          setOpenResume(false);
          await reload(token);
        }}
      />
      <CmsConfirm
        open={confirmTemplate}
        title={a.deleteTemplate}
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
