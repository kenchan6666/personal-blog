"use client";

import { useState } from "react";
import type { Dictionary } from "@/i18n/dictionaries";
import type {
  OwnerResumeTemplate,
  ResumeExtraDef,
  ResumeSectionId,
} from "@/lib/api";

const BUILTIN: ResumeSectionId[] = [
  "summary",
  "education",
  "internship",
  "projects",
  "activities",
  "skillsOthers",
];

type Props = {
  draft: OwnerResumeTemplate;
  dict: Dictionary;
  disabled?: boolean;
  onChange: (next: OwnerResumeTemplate) => void;
};

function slugify(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 40);
}

export function ResumeLayoutStudio({ draft, dict, disabled, onChange }: Props) {
  const a = dict.admin;
  const r = dict.resume;
  const extras = draft.extras ?? [];
  const [openId, setOpenId] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState("");

  function labelOf(id: string) {
    const extra = extras.find((item) => item.slug === id);
    if (extra) return extra.title || extra.slug;
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

  function blurbOf(id: string) {
    if (!BUILTIN.includes(id as ResumeSectionId)) return a.sectionBlurbCustom;
    const map = {
      summary: a.sectionBlurbSummary,
      education: a.sectionBlurbEducation,
      internship: a.sectionBlurbInternship,
      projects: a.sectionBlurbProjects,
      activities: a.sectionBlurbActivities,
      skillsOthers: a.sectionBlurbSkills,
    };
    return map[id as ResumeSectionId];
  }

  function fieldsOf(id: string) {
    if (!BUILTIN.includes(id as ResumeSectionId)) return a.sectionFieldsCustom;
    const map = {
      summary: a.sectionFieldsSummary,
      education: a.sectionFieldsEducation,
      internship: a.sectionFieldsInternship,
      projects: a.sectionFieldsProjects,
      activities: a.sectionFieldsActivities,
      skillsOthers: a.sectionFieldsSkills,
    };
    return map[id as ResumeSectionId];
  }

  const catalog = [
    ...draft.sections,
    ...BUILTIN.filter((id) => !draft.sections.includes(id)),
    ...extras
      .map((item) => item.slug)
      .filter((slug) => !draft.sections.includes(slug)),
  ].filter((id, index, all) => all.indexOf(id) === index);

  function toggle(id: string) {
    if (disabled) return;
    const sections = draft.sections.includes(id)
      ? draft.sections.filter((item) => item !== id)
      : [...draft.sections, id];
    onChange({ ...draft, sections });
  }

  function move(id: string, direction: -1 | 1) {
    if (disabled) return;
    const index = draft.sections.indexOf(id);
    const nextIndex = index + direction;
    if (index < 0 || nextIndex < 0 || nextIndex >= draft.sections.length) return;
    const sections = [...draft.sections];
    const [item] = sections.splice(index, 1);
    sections.splice(nextIndex, 0, item);
    onChange({ ...draft, sections });
  }

  function addExtra() {
    if (disabled) return;
    const title = newTitle.trim();
    if (!title) return;
    const used = new Set([
      ...BUILTIN,
      ...extras.map((item) => item.slug),
    ]);
    let slug = slugify(title) || "extra";
    let n = 2;
    while (used.has(slug)) {
      slug = `${slugify(title) || "extra"}-${n}`;
      n += 1;
    }
    const extra: ResumeExtraDef = { slug, title };
    onChange({
      ...draft,
      extras: [...extras, extra],
      sections: [...draft.sections, slug],
    });
    setNewTitle("");
    setOpenId(slug);
  }

  function renameExtra(slug: string, title: string) {
    onChange({
      ...draft,
      extras: extras.map((item) =>
        item.slug === slug ? { ...item, title } : item,
      ),
    });
  }

  function removeExtra(slug: string) {
    onChange({
      ...draft,
      extras: extras.filter((item) => item.slug !== slug),
      sections: draft.sections.filter((item) => item !== slug),
    });
    if (openId === slug) setOpenId(null);
  }

  return (
    <div className="resume-studio">
      <label className="mb-4 block text-xs text-[var(--text-muted)]">
        {a.fieldLayoutName}
        <input
          className="field"
          value={draft.name["zh-Hant"] || draft.name.en}
          disabled={disabled}
          onChange={(event) =>
            onChange({
              ...draft,
              name: {
                ...draft.name,
                en: event.target.value,
                "zh-Hant": event.target.value,
                "zh-Hans": event.target.value,
              },
            })
          }
        />
      </label>
      <ul className="resume-studio-list">
        {catalog.map((id) => {
          const on = draft.sections.includes(id);
          const open = openId === id;
          const extra = extras.find((item) => item.slug === id);
          return (
            <li key={id}>
              <article
                className={`resume-section-card${on ? " is-on" : ""}${
                  open ? " is-open" : ""
                }`}
              >
                <button
                  type="button"
                  className="resume-section-hit"
                  onClick={() => setOpenId(open ? null : id)}
                >
                  <span className="resume-section-card-head">
                    <strong>{labelOf(id)}</strong>
                    <span className="status-pill">{on ? a.sectionOn : a.sectionOff}</span>
                  </span>
                  <span className="resume-layout-mini" aria-hidden>
                    <i />
                    <i />
                    <i />
                  </span>
                </button>
                {open ? (
                  <div className="resume-section-detail">
                    <p>{blurbOf(id)}</p>
                    <div className="resume-section-preview">
                      <strong>{labelOf(id)}</strong>
                      <span>{fieldsOf(id)}</span>
                    </div>
                    {extra && !disabled ? (
                      <input
                        className="field"
                        value={extra.title}
                        onChange={(event) =>
                          renameExtra(id, event.target.value)
                        }
                      />
                    ) : null}
                    <div className="resume-section-tools">
                      <button
                        type="button"
                        className="btn-ghost text-sm"
                        disabled={disabled}
                        onClick={() => toggle(id)}
                      >
                        {on ? a.sectionOff : a.sectionOn}
                      </button>
                      {on ? (
                        <>
                          <button
                            type="button"
                            className="btn-ghost text-sm"
                            disabled={disabled}
                            onClick={() => move(id, -1)}
                          >
                            {a.moveAboutUp}
                          </button>
                          <button
                            type="button"
                            className="btn-ghost text-sm"
                            disabled={disabled}
                            onClick={() => move(id, 1)}
                          >
                            {a.moveAboutDown}
                          </button>
                        </>
                      ) : null}
                      {extra && !disabled ? (
                        <button
                          type="button"
                          className="btn-ghost text-sm"
                          onClick={() => removeExtra(id)}
                        >
                          {a.removeEntry}
                        </button>
                      ) : null}
                    </div>
                  </div>
                ) : null}
              </article>
            </li>
          );
        })}
      </ul>
      {!disabled ? (
        <div className="resume-studio-add">
          <input
            className="field"
            placeholder={a.addSectionName}
            value={newTitle}
            onChange={(event) => setNewTitle(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                addExtra();
              }
            }}
          />
          <button type="button" className="btn-cta" onClick={addExtra}>
            {a.addSection}
          </button>
        </div>
      ) : null}
    </div>
  );
}
