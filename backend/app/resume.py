from __future__ import annotations

import io
import json
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.models import (
    CLASSIC_RESUME_TEMPLATE_SLUG,
    LOCALES,
    RESUME_SECTIONS,
    Resume,
    ResumeEducation,
    ResumeExperience,
    ResumeExtra,
    ResumeExtraDef,
    ResumeHeader,
    ResumeLanguage,
    ResumeProject,
    ResumeTemplate,
    empty_localized,
)
from app.owner_actor import force_draft_if_service
from app.store import current_store, new_document

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)
_CJK_FONT_CANDIDATES = (
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\msyh.ttf"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
)

_PAGE_WIDTH, _PAGE_HEIGHT = A4
_LEFT = 35
_BODY = 50
_DATE_RIGHT = 521
_NAME_SIZE = 14
_TITLE_SIZE = 10
_BODY_SIZE = 9

_REGISTERED_FONT = ""


def ensure_resume_dir(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def save_resume_pdf_bytes(
    data: bytes,
    *,
    directory: Path,
    previous_filename: str | None,
) -> str:
    filename = f"{uuid.uuid4().hex}.pdf"
    target = directory / filename
    target.write_bytes(data)
    if previous_filename:
        old = directory / Path(previous_filename).name
        if old.exists() and old != target:
            old.unlink(missing_ok=True)
    return filename


def builtin_resume_templates() -> list[dict[str, Any]]:
    return [
        {
            "slug": CLASSIC_RESUME_TEMPLATE_SLUG,
            "name": {
                "zh-Hant": "學生項目向",
                "zh-Hans": "学生项目向",
                "en": "Student projects",
            },
            "sections": ["summary", "education", "projects", "skillsOthers"],
            "extras": [],
            "builtin": True,
        },
        {
            "slug": "campus-a4",
            "name": {
                "zh-Hant": "學歷先行",
                "zh-Hans": "学历先行",
                "en": "Education first",
            },
            "sections": ["education", "internship", "projects", "skillsOthers"],
            "extras": [],
            "builtin": True,
        },
        {
            "slug": "intern-a4",
            "name": {
                "zh-Hant": "實習投遞",
                "zh-Hans": "实习投递",
                "en": "Internship application",
            },
            "sections": [
                "summary",
                "education",
                "internship",
                "projects",
                "skillsOthers",
            ],
            "extras": [],
            "builtin": True,
        },
        {
            "slug": "full-a4",
            "name": {
                "zh-Hant": "校園完整",
                "zh-Hans": "校园完整",
                "en": "Full campus",
            },
            "sections": [
                "summary",
                "education",
                "internship",
                "projects",
                "activities",
                "skillsOthers",
            ],
            "extras": [],
            "builtin": True,
        },
        {
            "slug": "work-a4",
            "name": {
                "zh-Hant": "經歷優先",
                "zh-Hans": "经历优先",
                "en": "Experience first",
            },
            "sections": [
                "summary",
                "internship",
                "projects",
                "education",
                "skillsOthers",
            ],
            "extras": [],
            "builtin": True,
        },
        {
            "slug": "certs-a4",
            "name": {
                "zh-Hant": "證書加持",
                "zh-Hans": "证书加持",
                "en": "With certifications",
            },
            "sections": [
                "summary",
                "education",
                "internship",
                "projects",
                "skillsOthers",
                "certs",
            ],
            "extras": [{"slug": "certs", "title": "Certifications"}],
            "builtin": True,
        },
    ]


def builtin_classic_template() -> dict[str, Any]:
    return builtin_resume_templates()[0]


def builtin_template_slugs() -> set[str]:
    return {item["slug"] for item in builtin_resume_templates()}


def _layout_signature(template: ResumeTemplate) -> tuple[Any, ...]:
    extras = tuple((item.slug, item.title) for item in template.extras)
    return (tuple(template.sections), extras)


def _spec_signature(spec: dict[str, Any]) -> tuple[Any, ...]:
    extras = tuple(
        (str(item.get("slug") or ""), str(item.get("title") or ""))
        for item in spec.get("extras") or []
    )
    return (tuple(spec["sections"]), extras)


def _apply_builtin_spec(template: ResumeTemplate, spec: dict[str, Any]) -> None:
    template.slug = spec["slug"]
    template.name = spec["name"]
    template.extras = parse_extra_defs(spec.get("extras") or [])
    template.sections = list(spec["sections"])
    template.builtin = True


async def _prune_duplicate_custom_templates() -> None:
    store = current_store()
    rows = await store.find_all(ResumeTemplate)
    target_by_sig = {
        _spec_signature(spec): spec["slug"] for spec in builtin_resume_templates()
    }
    for item in rows:
        if item.builtin:
            continue
        target = target_by_sig.get(_layout_signature(item))
        if not target or target == item.slug:
            continue
        for resume in await store.find(Resume, template_slug=item.slug):
            resume.template_slug = target
            await store.save(resume)
        await store.delete(item)


async def ensure_builtin_templates() -> None:
    store = current_store()
    for spec in builtin_resume_templates():
        existing = await store.find_one(ResumeTemplate, slug=spec["slug"])
        if existing is None:
            template = new_document(ResumeTemplate)
            _apply_builtin_spec(template, spec)
            await store.insert(template)
            continue
        _apply_builtin_spec(existing, spec)
        await store.save(existing)


async def fold_duplicate_custom_templates() -> None:
    await ensure_builtin_templates()
    await _prune_duplicate_custom_templates()


def validate_slug(slug: str) -> str:
    cleaned = slug.strip().lower()
    if not _SLUG_RE.match(cleaned):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_slug",
        )
    return cleaned


def parse_extra_defs(raw: Any) -> list[ResumeExtraDef]:
    extras: list[ResumeExtraDef] = []
    used: set[str] = set()
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        slug_raw = str(item.get("slug") or "").strip()
        if slug_raw:
            slug = validate_slug(slug_raw)
        elif title:
            ascii_slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            slug = validate_slug(ascii_slug or "extra")
        else:
            continue
        base = slug
        n = 2
        while slug in used:
            slug = f"{base}-{n}"
            n += 1
        used.add(slug)
        extras.append(ResumeExtraDef(slug=slug, title=title or slug))
    return extras


def validate_sections(sections: list[str], extra_slugs: set[str] | None = None) -> list[str]:
    allowed = set(RESUME_SECTIONS) | (extra_slugs or set())
    cleaned: list[str] = []
    for item in sections:
        key = str(item).strip()
        if key not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_section",
            )
        if key not in cleaned:
            cleaned.append(key)
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_section",
        )
    return cleaned


def apply_template_body(template: ResumeTemplate, body: dict[str, Any]) -> None:
    template.slug = validate_slug(str(body.get("slug") or template.slug))
    name = body.get("name") or template.name
    if not isinstance(name, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_name",
        )
    merged = empty_localized()
    merged.update({key: str(name.get(key) or "") for key in LOCALES})
    template.name = merged
    extras = (
        parse_extra_defs(body["extras"])
        if "extras" in body
        else list(template.extras)
    )
    template.extras = extras
    template.sections = validate_sections(
        list(body.get("sections") or template.sections),
        {item.slug for item in extras},
    )
    if body.get("builtin") is True:
        template.builtin = True


def apply_resume_body(resume: Resume, body: dict[str, Any]) -> None:
    resume.slug = validate_slug(str(body.get("slug") or resume.slug))
    resume.template_slug = str(
        body.get("templateSlug") or resume.template_slug or CLASSIC_RESUME_TEMPLATE_SLUG
    ).strip()
    locale = str(body.get("locale") or resume.locale or "en")
    if locale not in LOCALES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_locale",
        )
    resume.locale = locale
    incoming_status = str(body.get("status") or resume.status or "draft")
    if incoming_status not in {"draft", "published"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_status",
        )
    resume.status = force_draft_if_service(incoming_status, resume.status)
    header = body["header"] if "header" in body else resume.header
    resume.header = ResumeHeader.model_validate(header)
    incoming_title = str(body.get("title") or "").strip()
    resume.title = resume.header.name.strip() or incoming_title or resume.title or resume.slug
    resume.summary = [
        str(line).strip()
        for line in (body["summary"] if "summary" in body else resume.summary)
        if str(line).strip()
    ]
    resume.education = [
        ResumeEducation.model_validate(item)
        for item in (
            body["education"]
            if "education" in body
            else [item.model_dump() for item in resume.education]
        )
    ]
    resume.internships = [
        ResumeExperience.model_validate(item)
        for item in (
            body["internships"]
            if "internships" in body
            else [item.model_dump() for item in resume.internships]
        )
    ]
    resume.projects = [
        ResumeProject.model_validate(item)
        for item in (
            body["projects"]
            if "projects" in body
            else [item.model_dump() for item in resume.projects]
        )
    ]
    resume.activities = [
        ResumeExperience.model_validate(item)
        for item in (
            body["activities"]
            if "activities" in body
            else [item.model_dump() for item in resume.activities]
        )
    ]
    resume.skills = [
        str(item).strip()
        for item in (body["skills"] if "skills" in body else resume.skills)
        if str(item).strip()
    ]
    resume.languages = [
        ResumeLanguage.model_validate(item)
        for item in (
            body["languages"]
            if "languages" in body
            else [item.model_dump() for item in resume.languages]
        )
    ]
    resume.extras = [
        ResumeExtra.model_validate(item)
        for item in (
            body["extras"]
            if "extras" in body
            else [item.model_dump() for item in resume.extras]
        )
    ]


def resume_vault_json(resume: Resume) -> bytes:
    payload = resume.to_owner_dict()
    for key in ("id", "pdfUrl", "githubRepo", "githubJsonPath", "githubPdfPath"):
        payload.pop(key, None)
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def parse_resume_import(payload: Any) -> dict[str, Any]:
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_resume_json",
        )
    source = payload.get("instance") if isinstance(payload.get("instance"), dict) else payload
    header = source.get("header") or {}
    if not header and any(key in source for key in ("name", "phone", "email", "city")):
        header = {
            "name": source.get("name") or "",
            "phone": source.get("phone") or "",
            "email": source.get("email") or "",
            "city": source.get("city") or "",
        }
    skills_block = source.get("skillsOthers") or {}
    return {
        "title": source.get("title") or header.get("name") or "",
        "templateSlug": source.get("templateSlug") or CLASSIC_RESUME_TEMPLATE_SLUG,
        "locale": source.get("locale") or "en",
        "header": header,
        "summary": source.get("summary") or [],
        "education": source.get("education") or [],
        "internships": source.get("internships") or [],
        "projects": source.get("projects") or [],
        "activities": source.get("activities") or [],
        "skills": source.get("skills") or skills_block.get("skills") or [],
        "languages": source.get("languages") or skills_block.get("languages") or [],
        "extras": source.get("extras") or [],
    }


def format_month(value: str) -> str:
    text = (value or "").strip()
    match = re.match(r"^(\d{4})-(\d{1,2})", text)
    if not match:
        return text
    year = match.group(1)
    month = int(match.group(2))
    if 1 <= month <= 12:
        return f"{_MONTHS[month - 1]} {year}"
    return text


def format_range(start: str, end: str) -> str:
    left = format_month(start)
    right = format_month(end) or "Present"
    if left and right:
        return f"{left} - {right}"
    return left or right


def _body_font() -> str:
    global _REGISTERED_FONT
    if _REGISTERED_FONT:
        return _REGISTERED_FONT
    for path in _CJK_FONT_CANDIDATES:
        if not path.is_file():
            continue
        try:
            pdfmetrics.registerFont(TTFont("ResumeBody", str(path), subfontIndex=0))
            _REGISTERED_FONT = "ResumeBody"
            return _REGISTERED_FONT
        except Exception:
            continue
    _REGISTERED_FONT = "Helvetica"
    return _REGISTERED_FONT


def render_resume_pdf(resume: Resume, template: ResumeTemplate) -> bytes:
    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=A4)
    font = _body_font()
    y = _PAGE_HEIGHT - 36
    page.setFillColorRGB(0.10, 0.09, 0.19)

    def text_width(value: str, size: float) -> float:
        return pdfmetrics.stringWidth(value, font, size)

    def draw_centered(value: str, size: float) -> None:
        nonlocal y
        page.setFont(font, size)
        page.drawString((_PAGE_WIDTH - text_width(value, size)) / 2, y, value)
        y -= size + 4

    def wrap(value: str, width: float, size: float) -> list[str]:
        words = value.split()
        if not words:
            return []
        lines = [words[0]]
        for word in words[1:]:
            trial = f"{lines[-1]} {word}"
            if text_width(trial, size) <= width:
                lines[-1] = trial
            else:
                lines.append(word)
        return lines

    def draw_wrapped(value: str, x: float, size: float, width: float) -> None:
        nonlocal y
        page.setFont(font, size)
        for line in wrap(value, width, size) or [value]:
            page.drawString(x, y, line)
            y -= size + 4

    def section_title(title: str) -> None:
        nonlocal y
        y -= 8
        page.setFont(font, _TITLE_SIZE)
        page.drawString(_LEFT, y, title)
        y -= 6
        page.setStrokeColorRGB(0.35, 0.27, 0.55)
        page.setLineWidth(0.6)
        page.line(_LEFT, y, _PAGE_WIDTH - 36, y)
        y -= 14

    def entry_row(left: str, right: str) -> None:
        nonlocal y
        page.setFont(font, _BODY_SIZE)
        page.drawString(_LEFT, y, left)
        if right:
            page.drawRightString(_DATE_RIGHT + 36, y, right)
        y -= _BODY_SIZE + 5

    header = resume.header
    draw_centered(header.name or resume.title or "Resume", _NAME_SIZE)
    contact = "  |  ".join(part for part in (header.phone, header.email) if part)
    if contact:
        draw_centered(contact, _BODY_SIZE)
    if header.city:
        draw_centered(header.city, _BODY_SIZE)
    for link in header.links:
        if link:
            draw_centered(link, _BODY_SIZE)

    titles = {
        "summary": "SUMMARY",
        "education": "EDUCATION",
        "internship": "INTERNSHIP",
        "projects": "PROJECT EXPERIENCE",
        "activities": "ACTIVITIES",
        "skillsOthers": "SKILLS, CERTIFICATIONS & OTHERS",
    }
    width = _PAGE_WIDTH - _BODY - 40

    def draw_extra(extra: ResumeExtra) -> None:
        section_title((extra.title or extra.slug).upper())
        for line in extra.lines:
            draw_wrapped(line, _BODY, _BODY_SIZE, width)
        for item in extra.entries:
            entry_row(item.organization or item.role, format_range(item.start, item.end))
            if item.role and item.organization:
                entry_row(item.role, item.city)
            for line in item.description:
                draw_wrapped(line, _BODY, _BODY_SIZE, width)

    for section in template.sections:
        if section == "summary" and resume.summary:
            section_title(titles[section])
            for line in resume.summary:
                draw_wrapped(line, _BODY, _BODY_SIZE, width)
        elif section == "education" and resume.education:
            section_title(titles[section])
            for item in resume.education:
                entry_row(item.institution, format_range(item.start, item.end))
                subtitle = " ".join(part for part in (item.field, item.degree) if part)
                entry_row(subtitle, item.city)
                if item.honor:
                    draw_wrapped(item.honor, _LEFT, _BODY_SIZE, width)
                if item.related_courses:
                    draw_wrapped(
                        "Related course: " + ", ".join(item.related_courses),
                        _LEFT,
                        _BODY_SIZE,
                        width,
                    )
        elif section == "internship" and resume.internships:
            section_title(titles[section])
            for item in resume.internships:
                entry_row(item.organization, format_range(item.start, item.end))
                entry_row(item.role, item.city)
                for line in item.description:
                    draw_wrapped(line, _BODY, _BODY_SIZE, width)
        elif section == "projects" and resume.projects:
            section_title(titles[section])
            for item in resume.projects:
                entry_row(item.name, format_range(item.start, item.end))
                if item.tech_stack:
                    draw_wrapped(
                        "(" + ", ".join(item.tech_stack) + ")",
                        _LEFT,
                        _BODY_SIZE,
                        width,
                    )
                for line in item.description:
                    draw_wrapped(line, _BODY, _BODY_SIZE, width)
        elif section == "activities" and resume.activities:
            section_title(titles[section])
            for item in resume.activities:
                entry_row(item.organization, format_range(item.start, item.end))
                entry_row(item.role, item.city)
                for line in item.description:
                    draw_wrapped(line, _BODY, _BODY_SIZE, width)
        elif section == "skillsOthers" and (resume.skills or resume.languages):
            section_title(titles[section])
            if resume.skills:
                draw_wrapped("Skills: " + ", ".join(resume.skills), _LEFT, _BODY_SIZE, width)
            if resume.languages:
                langs = ", ".join(
                    f"{item.name} ({item.level})" if item.level else item.name
                    for item in resume.languages
                )
                draw_wrapped("Languages: " + langs, _LEFT, _BODY_SIZE, width)
        else:
            extra = next(
                (item for item in resume.extras if item.slug == section),
                None,
            )
            if extra is None:
                extra = next(
                    (
                        ResumeExtra(slug=item.slug, title=item.title)
                        for item in template.extras
                        if item.slug == section
                    ),
                    None,
                )
            if extra is not None and (extra.lines or extra.entries):
                draw_extra(extra)

    drawn = set(template.sections)
    for extra in resume.extras:
        if extra.slug in drawn or not (extra.lines or extra.entries):
            continue
        draw_extra(extra)

    page.showPage()
    page.save()
    return buffer.getvalue()
