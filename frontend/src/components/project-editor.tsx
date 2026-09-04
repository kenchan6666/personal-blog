"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import {
  attachOwnerSourceRepo,
  createOwnerProject,
  emptyOwnerProject,
  fetchOwnerGitHubRepos,
  fetchOwnerProjects,
  getSessionToken,
  localizedText,
  saveOwnerProject,
  type OwnerProject,
  type SourceRepo,
} from "@/lib/api";
import { BilingualField } from "./bilingual-field";
import { CmsCard, StatusPill } from "./cms-card";
import { CmsModal } from "./cms-modal";

type Props = {
  locale: Locale;
  dict: Dictionary;
};

function payloadOf(
  project: OwnerProject,
): Omit<OwnerProject, "id" | "sourceRepo"> {
  const { id: _id, sourceRepo: _repo, ...rest } = project;
  return rest;
}

function titleOf(project: OwnerProject, fallback: string) {
  return localizedText(project.title, project.slug || fallback);
}

function slugFromName(name: string, taken: string[]) {
  const base =
    name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "project";
  let slug = base;
  let n = 2;
  while (taken.includes(slug)) {
    slug = `${base}-${n}`;
    n += 1;
  }
  return slug;
}

function projectFromRepo(
  repo: SourceRepo,
  taken: string[],
  order: number,
): OwnerProject {
  const slug = slugFromName(repo.name, taken);
  const summary = repo.description ?? "";
  return {
    ...emptyOwnerProject(),
    slug,
    order,
    status: "published",
    title: { "zh-Hant": repo.name, "zh-Hans": repo.name, en: repo.name },
    summary: { "zh-Hant": summary, "zh-Hans": summary, en: summary },
  };
}

export function ProjectEditor({ locale, dict }: Props) {
  const a = dict.admin;
  const router = useRouter();
  const params = useSearchParams();
  const [projects, setProjects] = useState<OwnerProject[]>([]);
  const [current, setCurrent] = useState<OwnerProject>(emptyOwnerProject());
  const [pickedRepo, setPickedRepo] = useState<SourceRepo | null>(null);
  const [step, setStep] = useState<"pick" | "form">("form");
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [repos, setRepos] = useState<SourceRepo[]>([]);
  const [githubReady, setGithubReady] = useState(false);

  async function reload(token: string) {
    const list = await fetchOwnerProjects(token);
    setProjects(list);
    const githubRepos = await fetchOwnerGitHubRepos(token);
    setGithubReady(githubRepos !== null);
    setRepos(githubRepos ?? []);
    return { projects: list, repos: githubRepos ?? [] };
  }

  function startFromRepo(repo: SourceRepo, existing: OwnerProject[]) {
    const taken = existing.map((item) => item.slug);
    const nextOrder =
      existing.reduce((max, item) => Math.max(max, item.order), 0) + 1;
    setPickedRepo(repo);
    setCurrent(projectFromRepo(repo, taken, nextOrder));
    setStep("form");
    setMessage(null);
    setError(null);
    setOpen(true);
  }

  const attach = params.get("attach");

  useEffect(() => {
    const token = getSessionToken();
    if (!token) return;
    reload(token)
      .then(({ projects: nextProjects, repos: nextRepos }) => {
        if (!attach) return;
        const repo = nextRepos.find((item) => item.fullName === attach);
        if (repo) startFromRepo(repo, nextProjects);
        const next = new URLSearchParams(params.toString());
        next.delete("attach");
        router.replace(`/${locale}/admin?${next.toString()}`);
      })
      .catch(() => setError(a.errorGeneric))
      .finally(() => setLoading(false));
  }, [a.errorGeneric, attach, locale, params, router]);

  const filteredRepos = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return repos;
    return repos.filter(
      (repo) =>
        repo.fullName.toLowerCase().includes(q) ||
        (repo.description ?? "").toLowerCase().includes(q),
    );
  }, [query, repos]);

  function openNew() {
    setCurrent(emptyOwnerProject());
    setPickedRepo(null);
    setQuery("");
    setMessage(null);
    setError(null);
    setStep(githubReady ? "pick" : "form");
    setOpen(true);
  }

  function openEditor(project: OwnerProject) {
    setCurrent(project);
    setPickedRepo(project.sourceRepo);
    setMessage(null);
    setError(null);
    setStep("form");
    setOpen(true);
  }

  function closeEditor() {
    setOpen(false);
    setMessage(null);
    setError(null);
    setStep("form");
  }

  function chooseRepo(repo: SourceRepo) {
    startFromRepo(repo, projects);
  }

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    const token = getSessionToken();
    if (!token) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      let saved = current.id
        ? await saveOwnerProject(token, current.id, payloadOf(current))
        : await createOwnerProject(token, payloadOf(current));
      const fullName = pickedRepo?.fullName;
      if (fullName && saved.sourceRepo?.fullName !== fullName) {
        saved = await attachOwnerSourceRepo(token, saved.id, fullName);
      }
      setCurrent(saved);
      setPickedRepo(saved.sourceRepo);
      await reload(token);
      setMessage(a.saved);
    } catch {
      setError(a.errorGeneric);
    } finally {
      setSaving(false);
    }
  }

  const previewProps = {
    editLabel: a.editTab,
    previewLabel: a.preview,
    translateLabel: a.translate,
    translatingLabel: a.translating,
    emptyPreview: a.emptyPreview,
    onTranslateError: (code: string) =>
      setError(code === "empty_source" ? a.errorTranslateEmpty : a.errorTranslate),
  };
  const imageProps = {
    allowImages: true,
    uploadImageLabel: a.uploadAboutImage,
    uploadingImageLabel: a.uploadingAboutImage,
    onImageError: () => setError(a.errorGeneric),
  };

  const modalTitle =
    step === "pick"
      ? a.pickRepo
      : current.id
        ? titleOf(current, a.untitledProject)
        : a.newProject;

  return (
    <CmsCard
      title={a.projectEditor}
      action={
        <button type="button" className="btn-ghost text-sm" onClick={openNew}>
          {a.newProject}
        </button>
      }
    >
      {error && !open ? (
        <p className="mb-3 text-sm text-[var(--danger)]">{error}</p>
      ) : null}
      {loading ? (
        <p className="text-sm text-[var(--text-muted)]">{a.loadingProjects}</p>
      ) : projects.length === 0 ? (
        <p className="text-sm text-[var(--text-muted)]">
          {githubReady ? a.emptyProjectsFromGithub : a.emptyProjects}
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {projects.map((project) => (
            <li key={project.id} className="flex items-stretch gap-2">
              <button
                type="button"
                className="tile flex-1"
                onClick={() => openEditor(project)}
              >
                <span className="font-semibold">
                  {titleOf(project, a.untitledProject)}
                </span>
                <span className="ml-3">
                  <StatusPill
                    published={project.status === "published"}
                    publishedLabel={a.statusPublished}
                    draftLabel={a.statusDraft}
                  />
                </span>
                {project.sourceRepo ? (
                  <span className="ml-3 font-mono text-xs text-[var(--text-muted)]">
                    {project.sourceRepo.fullName}
                  </span>
                ) : null}
              </button>
              {project.status === "published" ? (
                <Link
                  href={`/${locale}/projects/${project.slug}`}
                  className="btn-ghost self-center text-sm whitespace-nowrap"
                >
                  {a.viewPublic}
                </Link>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      <CmsModal
        open={open}
        title={modalTitle}
        closeLabel={a.close}
        onClose={closeEditor}
        footer={
          step === "pick" ? (
            <button type="button" className="btn-ghost" onClick={closeEditor}>
              {a.close}
            </button>
          ) : (
            <>
              {githubReady && !current.id ? (
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => setStep("pick")}
                >
                  {a.pickRepo}
                </button>
              ) : null}
              <button
                type="submit"
                form="project-form"
                className="btn-cta"
                disabled={saving}
              >
                {saving ? a.saving : a.save}
              </button>
              <button type="button" className="btn-ghost" onClick={closeEditor}>
                {a.close}
              </button>
              {message ? (
                <p className="text-sm text-[var(--text-muted)]">{message}</p>
              ) : null}
              {current.id && current.status === "published" ? (
                <Link
                  href={`/${locale}/projects/${current.slug}`}
                  className="btn-ghost text-sm"
                >
                  {a.viewPublic}
                </Link>
              ) : null}
              {error ? (
                <p className="text-sm text-[var(--danger)]">{error}</p>
              ) : null}
            </>
          )
        }
      >
        {step === "pick" ? (
          <div>
            {!githubReady ? (
              <p className="text-sm text-[var(--text-muted)]">
                {a.githubDisconnectedHint}
              </p>
            ) : (
              <>
                <input
                  className="field field-tight mb-4"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={a.searchRepos}
                />
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
                          className="tile"
                          onClick={() => chooseRepo(repo)}
                        >
                          <span className="font-mono text-sm font-semibold">
                            {repo.fullName}
                          </span>
                          {repo.private ? (
                            <span className="ml-2 text-xs text-[var(--text-muted)]">
                              private
                            </span>
                          ) : null}
                          {repo.description ? (
                            <p className="mt-1 text-sm text-[var(--text-muted)]">
                              {repo.description}
                            </p>
                          ) : null}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </div>
        ) : (
          <form id="project-form" onSubmit={onSave}>
            {pickedRepo ? (
              <p className="mb-6 rounded-[var(--radius-card)] border border-[var(--hairline)] bg-[#f7f5fb] px-3 py-2 text-sm">
                {a.addingRepo}:{" "}
                <span className="font-mono">{pickedRepo.fullName}</span>
              </p>
            ) : null}
            <label className="mb-6 block text-sm font-semibold">
              {a.fieldSlug}
              <input
                className="field mt-2 font-normal"
                value={current.slug}
                onChange={(e) =>
                  setCurrent({ ...current, slug: e.target.value })
                }
                required
              />
            </label>
            <div className="mb-6 grid gap-4 sm:grid-cols-2">
              <label className="block text-sm font-semibold">
                {a.fieldStatus}
                <select
                  className="field mt-2 font-normal"
                  value={current.status}
                  onChange={(e) =>
                    setCurrent({
                      ...current,
                      status: e.target.value as OwnerProject["status"],
                    })
                  }
                >
                  <option value="draft">{a.statusDraft}</option>
                  <option value="published">{a.statusPublished}</option>
                </select>
              </label>
              <label className="block text-sm font-semibold">
                {a.fieldOrder}
                <input
                  type="number"
                  className="field mt-2 font-normal"
                  value={current.order}
                  onChange={(e) =>
                    setCurrent({
                      ...current,
                      order: Number(e.target.value) || 0,
                    })
                  }
                />
              </label>
            </div>
            <BilingualField
              label={a.fieldProjectTitle}
              value={current.title}
              onChange={(title) => setCurrent({ ...current, title })}
              {...previewProps}
            />
            <BilingualField
              label={a.fieldProjectSummary}
              value={current.summary}
              onChange={(summary) => setCurrent({ ...current, summary })}
              multiline
              previewable
              rows={5}
              {...previewProps}
            />
            <BilingualField
              label={a.fieldProjectBody}
              value={current.body}
              onChange={(body) => setCurrent({ ...current, body })}
              multiline
              previewable
              rows={8}
              {...previewProps}
              {...imageProps}
            />
          </form>
        )}
      </CmsModal>
    </CmsCard>
  );
}
