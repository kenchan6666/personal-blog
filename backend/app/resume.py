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
from reportlab.pdfbase.ttfonts import TTFError, TTFont
from reportlab.pdfgen import canvas

from app.github import (
    CV_TEMPLATE_DIR,
    GitHubBrowseError,
    GitHubClient,
    cv_template_path,
    ensure_owned_cv_repo,
)
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
    utc_now,
)
from app.owner_actor import force_draft_if_service
from app.store import current_store, new_document

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_BULLET_PREFIX_RE = re.compile(r"^(?:[-*•●◦]|\d+[.)])\s+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？；;!?])\s+|(?<=\.)\s+(?=[A-Z\u4e00-\u9fff])")


def split_resume_lines(values: Any) -> list[str]:
    if values is None:
        return []
    chunks = [values] if isinstance(values, str) else list(values)
    lines: list[str] = []
    for chunk in chunks:
        text = str(chunk).replace("\r\n", "\n").replace("\r", "\n").strip()
        if not text:
            continue
        parts = [part.strip() for part in text.split("\n") if part.strip()]
        if len(parts) <= 1 and "\n" not in text:
            parts = [
                part.strip()
                for part in _SENTENCE_SPLIT_RE.split(text)
                if part.strip()
            ] or [text]
        for part in parts:
            cleaned = _BULLET_PREFIX_RE.sub("", part).strip()
            if cleaned:
                lines.append(cleaned)
    return lines


def _experience_rows(raw: list[Any]) -> list[ResumeExperience]:
    rows: list[ResumeExperience] = []
    for item in raw:
        data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
        data["description"] = split_resume_lines(data.get("description") or [])
        rows.append(ResumeExperience.model_validate(data))
    return rows


def _paragraph_lines(values: Any) -> list[str]:
    chunks = [values] if isinstance(values, str) else list(values or [])
    text = "\n".join(str(chunk) for chunk in chunks)
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []
    return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]


def _explicit_lines(values: Any) -> list[str]:
    chunks = [values] if isinstance(values, str) else list(values or [])
    lines: list[str] = []
    for chunk in chunks:
        text = str(chunk).replace("\r\n", "\n").replace("\r", "\n")
        for part in text.split("\n"):
            cleaned = _BULLET_PREFIX_RE.sub("", part).strip()
            if cleaned:
                lines.append(cleaned)
    return lines


def _project_rows(raw: list[Any]) -> list[ResumeProject]:
    rows: list[ResumeProject] = []
    for item in raw:
        data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
        style = str(
            data.get("description_style") or data.get("descriptionStyle") or "bullets"
        )
        data.pop("descriptionStyle", None)
        data["description_style"] = (
            "paragraph" if style == "paragraph" else "bullets"
        )
        if data["description_style"] == "paragraph":
            data["description"] = _paragraph_lines(data.get("description") or [])
        else:
            data["description"] = _explicit_lines(data.get("description") or [])
        data["tech_stack"] = [
            str(part).strip()
            for part in (data.get("tech_stack") or [])
            if str(part).strip()
        ]
        rows.append(ResumeProject.model_validate(data))
    return rows


_CJK_FONT_CANDIDATES = (
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\msyh.ttf"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
)

_PAGE_WIDTH, _PAGE_HEIGHT = A4
_MARGIN = 50
_LEFT = _MARGIN
_RIGHT = _PAGE_WIDTH - _MARGIN
_NAME_SIZE = 18
_TITLE_SIZE = 10
_SECTION_TITLES = {
    "en": {
        "summary": "SUMMARY",
        "education": "EDUCATION",
        "internship": "INTERNSHIP",
        "work": "WORK EXPERIENCE",
        "projects": "PROJECTS",
        "activities": "ACTIVITIES",
        "skillsOthers": "SKILLS",
    },
    "zh-Hant": {
        "summary": "個人總結",
        "education": "教育經歷",
        "internship": "實習經歷",
        "work": "工作經驗",
        "projects": "項目經歷",
        "activities": "活動經歷",
        "skillsOthers": "技能",
    },
    "zh-Hans": {
        "summary": "个人总结",
        "education": "教育经历",
        "internship": "实习经历",
        "work": "工作经验",
        "projects": "项目经历",
        "activities": "活动经历",
        "skillsOthers": "技能",
    },
}


def _section_titles(locale: str) -> dict[str, str]:
    return _SECTION_TITLES.get(locale, _SECTION_TITLES["en"])


_FIELD_LABELS = {
    "en": {"languages": "Languages", "courses": "Coursework"},
    "zh-Hant": {"languages": "語言", "courses": "相關課程"},
    "zh-Hans": {"languages": "语言", "courses": "相关课程"},
}
_BODY_SIZE = 10
_LEADING = 13
_PAGE_BOTTOM = _MARGIN
_INK = (0.12, 0.12, 0.12)
_MUTED = (0.32, 0.32, 0.32)
_RULE = (0.22, 0.22, 0.22)

_REGISTERED_FONT = ""
_REGISTERED_BOLD = ""


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


def builtin_classic_template() -> dict[str, Any]:
    return {
        "slug": CLASSIC_RESUME_TEMPLATE_SLUG,
        "name": {
            "zh-Hant": "學生項目向",
            "zh-Hans": "学生项目向",
            "en": "Student projects",
        },
        "sections": ["summary", "education", "projects", "skillsOthers"],
        "extras": [],
        "builtin": True,
    }


def vault_seed_templates() -> list[dict[str, Any]]:
    return [
        {
            "slug": "campus-a4",
            "name": {
                "zh-Hant": "學歷先行",
                "zh-Hans": "学历先行",
                "en": "Education first",
            },
            "sections": ["education", "internship", "projects", "skillsOthers"],
            "extras": [],
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
        },
        {
            "slug": "job-a4",
            "name": {
                "zh-Hant": "工作",
                "zh-Hans": "工作",
                "en": "Work",
            },
            "sections": [
                "summary",
                "education",
                "work",
                "projects",
                "skillsOthers",
            ],
            "extras": [],
        },
    ]


def builtin_resume_templates() -> list[dict[str, Any]]:
    return [builtin_classic_template()]


def builtin_template_slugs() -> set[str]:
    return {CLASSIC_RESUME_TEMPLATE_SLUG}


def _layout_signature(template: ResumeTemplate) -> tuple[Any, ...]:
    extras = tuple((item.slug, item.title) for item in template.extras)
    return (tuple(template.sections), extras)


def _spec_signature(spec: dict[str, Any]) -> tuple[Any, ...]:
    extras = tuple(
        (str(item.get("slug") or ""), str(item.get("title") or ""))
        for item in spec.get("extras") or []
    )
    return (tuple(spec["sections"]), extras)


def _apply_template_spec(
    template: ResumeTemplate, spec: dict[str, Any], *, builtin: bool
) -> None:
    template.slug = spec["slug"]
    template.name = spec["name"]
    template.extras = parse_extra_defs(spec.get("extras") or [])
    template.sections = list(spec["sections"])
    template.builtin = builtin
    if not builtin:
        template.github_path = spec.get("github_path") or cv_template_path(
            template.slug
        )


def template_vault_bytes(template: ResumeTemplate) -> bytes:
    return json.dumps(
        {
            "slug": template.slug,
            "name": template.name,
            "sections": list(template.sections),
            "extras": [item.model_dump() for item in template.extras],
        },
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")


def parse_vault_template_file(path: str, raw: str) -> dict[str, Any] | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    stem = Path(path).stem
    try:
        slug = validate_slug(str(data.get("slug") or stem))
    except HTTPException:
        return None
    if slug == CLASSIC_RESUME_TEMPLATE_SLUG:
        return None
    name = data.get("name") if isinstance(data.get("name"), dict) else {}
    extras = parse_extra_defs(data.get("extras") or [])
    extra_slugs = {item.slug for item in extras}
    try:
        sections = validate_sections(
            list(data.get("sections") or []), extra_slugs
        )
    except HTTPException:
        return None
    return {
        "slug": slug,
        "name": {
            **empty_localized(),
            **{key: str(name.get(key) or "") for key in LOCALES},
        },
        "sections": sections,
        "extras": [item.model_dump() for item in extras],
        "github_path": path,
    }


async def _prune_duplicate_custom_templates() -> None:
    store = current_store()
    rows = await store.find_all(ResumeTemplate)
    target_by_sig = {_spec_signature(builtin_classic_template()): CLASSIC_RESUME_TEMPLATE_SLUG}
    for item in rows:
        if item.builtin or item.slug == CLASSIC_RESUME_TEMPLATE_SLUG:
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
    spec = builtin_classic_template()
    existing = await store.find_one(ResumeTemplate, slug=spec["slug"])
    if existing is None:
        template = new_document(ResumeTemplate)
        _apply_template_spec(template, spec, builtin=True)
        template.github_path = ""
        await store.insert(template)
    else:
        _apply_template_spec(existing, spec, builtin=True)
        existing.github_path = ""
        await store.save(existing)
    for item in await store.find_all(ResumeTemplate):
        if item.builtin and item.slug != CLASSIC_RESUME_TEMPLATE_SLUG:
            item.builtin = False
            item.github_path = item.github_path or cv_template_path(item.slug)
            await store.save(item)
    for vault in vault_seed_templates():
        current = await store.find_one(ResumeTemplate, slug=vault["slug"])
        if current is not None:
            continue
        template = new_document(ResumeTemplate)
        _apply_template_spec(template, vault, builtin=False)
        await store.insert(template)


async def fold_duplicate_custom_templates() -> None:
    await ensure_builtin_templates()
    await _prune_duplicate_custom_templates()


async def write_cv_template_file(
    github: GitHubClient,
    *,
    access_token: str,
    template: ResumeTemplate,
    previous_path: str = "",
) -> str:
    repo, _ = await ensure_owned_cv_repo(github, access_token=access_token)
    branch = str(repo.get("defaultBranch") or "main")
    path = cv_template_path(template.slug)
    await github.put_file(
        access_token=access_token,
        owner=str(repo["owner"]),
        name=str(repo["name"]),
        path=path,
        content=template_vault_bytes(template),
        message=f"Update template {template.slug}",
        branch=branch,
    )
    if previous_path and previous_path != path:
        await github.delete_file(
            access_token=access_token,
            owner=str(repo["owner"]),
            name=str(repo["name"]),
            path=previous_path,
            message=f"Remove renamed template {previous_path}",
            branch=branch,
        )
    template.github_path = path
    return path


async def delete_cv_template_file(
    github: GitHubClient,
    *,
    access_token: str,
    path: str,
) -> None:
    if not path:
        return
    repo, _ = await ensure_owned_cv_repo(github, access_token=access_token)
    await github.delete_file(
        access_token=access_token,
        owner=str(repo["owner"]),
        name=str(repo["name"]),
        path=path,
        message=f"Remove template {path}",
        branch=str(repo.get("defaultBranch") or "main"),
    )


async def sync_cv_templates(
    github: GitHubClient,
    *,
    access_token: str,
) -> None:
    await ensure_builtin_templates()
    store = current_store()
    repo, _ = await ensure_owned_cv_repo(github, access_token=access_token)
    branch = str(repo.get("defaultBranch") or "main")
    owner = str(repo["owner"])
    name = str(repo["name"])
    try:
        entries = await github.list_tree(
            access_token=access_token,
            owner=owner,
            name=name,
            ref=branch,
            path=CV_TEMPLATE_DIR,
        )
    except GitHubBrowseError:
        entries = []
    remote_paths = {
        item["path"]
        for item in entries
        if item.get("type") == "file" and str(item.get("name") or "").endswith(".json")
    }
    for item in await store.find_all(ResumeTemplate):
        if item.builtin:
            continue
        path = item.github_path or cv_template_path(item.slug)
        if path in remote_paths:
            continue
        await write_cv_template_file(
            github, access_token=access_token, template=item
        )
        await store.save(item)
        remote_paths.add(path)
    for path in sorted(remote_paths):
        try:
            blob = await github.get_blob(
                access_token=access_token,
                owner=owner,
                name=name,
                ref=branch,
                path=path,
            )
        except GitHubBrowseError:
            continue
        spec = parse_vault_template_file(path, blob.get("content") or "")
        if spec is None:
            continue
        current = await store.find_one(ResumeTemplate, slug=spec["slug"])
        if current is None:
            template = new_document(ResumeTemplate)
            _apply_template_spec(template, spec, builtin=False)
            await store.insert(template)
            continue
        if current.builtin:
            continue
        _apply_template_spec(current, spec, builtin=False)
        await store.save(current)


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
    resume.summary = split_resume_lines(
        body["summary"] if "summary" in body else resume.summary
    )
    resume.education = [
        ResumeEducation.model_validate(item)
        for item in (
            body["education"]
            if "education" in body
            else [item.model_dump() for item in resume.education]
        )
    ]
    resume.internships = _experience_rows(
        body["internships"]
        if "internships" in body
        else [item.model_dump() for item in resume.internships]
    )
    resume.work_experiences = _experience_rows(
        body["workExperiences"]
        if "workExperiences" in body
        else [item.model_dump() for item in resume.work_experiences]
    )
    resume.projects = _project_rows(
        body["projects"]
        if "projects" in body
        else [item.model_dump() for item in resume.projects]
    )
    resume.activities = _experience_rows(
        body["activities"]
        if "activities" in body
        else [item.model_dump() for item in resume.activities]
    )
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
    extras: list[ResumeExtra] = []
    for item in (
        body["extras"]
        if "extras" in body
        else [item.model_dump() for item in resume.extras]
    ):
        data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
        data["lines"] = split_resume_lines(data.get("lines") or [])
        data["entries"] = [
            row.model_dump()
            for row in _experience_rows(data.get("entries") or [])
        ]
        extras.append(ResumeExtra.model_validate(data))
    resume.extras = extras
    resume.updated_at = utc_now()


def resume_vault_json(resume: Resume) -> bytes:
    payload = resume.to_owner_dict()
    for key in (
        "id",
        "pdfUrl",
        "githubRepo",
        "githubJsonPath",
        "githubPdfPath",
        "updatedAt",
    ):
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
        "workExperiences": source.get("workExperiences") or [],
        "projects": source.get("projects") or [],
        "activities": source.get("activities") or [],
        "skills": source.get("skills") or skills_block.get("skills") or [],
        "languages": source.get("languages") or skills_block.get("languages") or [],
        "extras": source.get("extras") or [],
    }


def format_range(start: str, end: str) -> str:
    left = (start or "").strip()
    right = (end or "").strip()
    if left and right:
        return f"{left} – {right}"
    return left or right


def _field_labels(locale: str) -> dict[str, str]:
    return _FIELD_LABELS.get(locale, _FIELD_LABELS["en"])


def _body_font() -> str:
    global _REGISTERED_FONT, _REGISTERED_BOLD
    if _REGISTERED_FONT:
        return _REGISTERED_FONT
    for path in _CJK_FONT_CANDIDATES:
        if not path.is_file():
            continue
        try:
            pdfmetrics.registerFont(TTFont("ResumeBody", str(path), subfontIndex=0))
            bold_name = "ResumeBody"
            try:
                pdfmetrics.registerFont(
                    TTFont("ResumeBold", str(path), subfontIndex=1)
                )
                bold_name = "ResumeBold"
            except (OSError, TTFError, ValueError):
                bold_name = "ResumeBody"
            _REGISTERED_FONT = "ResumeBody"
            _REGISTERED_BOLD = bold_name
            return _REGISTERED_FONT
        except (OSError, TTFError, ValueError):
            continue
    _REGISTERED_FONT = "Helvetica"
    _REGISTERED_BOLD = "Helvetica-Bold"
    return _REGISTERED_FONT


def _bold_font() -> str:
    _body_font()
    return _REGISTERED_BOLD or _REGISTERED_FONT


def render_resume_pdf(resume: Resume, template: ResumeTemplate) -> bytes:
    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=A4)
    font = _body_font()
    bold = _bold_font()
    content_width = _RIGHT - _LEFT
    y = _PAGE_HEIGHT - _MARGIN - 14
    page.setFillColorRGB(*_INK)

    def new_page() -> None:
        nonlocal y
        page.showPage()
        page.setFillColorRGB(*_INK)
        y = _PAGE_HEIGHT - _MARGIN - 14

    def ensure_space(needed: float) -> None:
        if y - needed < _PAGE_BOTTOM:
            new_page()

    def text_width(value: str, size: float, face: str | None = None) -> float:
        return pdfmetrics.stringWidth(value, face or font, size)

    def wrap(value: str, width: float, size: float, face: str | None = None) -> list[str]:
        use = face or font

        def measure(token: str) -> float:
            return pdfmetrics.stringWidth(token, use, size)

        def fit_token(token: str) -> list[str]:
            if measure(token) <= width:
                return [token]
            rows: list[str] = []
            current = ""
            for char in token:
                trial = current + char
                if current and measure(trial) > width:
                    rows.append(current)
                    current = char
                else:
                    current = trial
            if current:
                rows.append(current)
            return rows or [token]

        words = value.split()
        if not words:
            return []
        lines = fit_token(words[0])
        for word in words[1:]:
            pieces = fit_token(word)
            trial = f"{lines[-1]} {pieces[0]}"
            if measure(trial) <= width:
                lines[-1] = trial
                lines.extend(pieces[1:])
            else:
                lines.extend(pieces)
        return lines

    def draw_centered(value: str, size: float, *, face: str | None = None) -> None:
        nonlocal y
        use = face or font
        for line in wrap(value, content_width, size, use) or [value]:
            ensure_space(_LEADING)
            page.setFillColorRGB(*_INK)
            page.setFont(use, size)
            page.drawString((_PAGE_WIDTH - text_width(line, size, use)) / 2, y, line)
            y -= size + 2

    def draw_wrapped(
        value: str,
        x: float,
        size: float,
        width: float,
        *,
        muted: bool = False,
    ) -> None:
        nonlocal y
        page.setFillColorRGB(*(_MUTED if muted else _INK))
        page.setFont(font, size)
        for line in wrap(value, width, size) or [value]:
            ensure_space(_LEADING)
            page.drawString(x, y, line)
            y -= _LEADING

    def draw_bullet(value: str) -> None:
        nonlocal y
        indent = 11
        lines = wrap(value, content_width - indent, _BODY_SIZE) or [value]
        for index, line in enumerate(lines):
            ensure_space(_LEADING)
            page.setFillColorRGB(*_INK)
            page.setFont(font, _BODY_SIZE)
            if index == 0:
                page.drawString(_LEFT, y, "•")
            page.drawString(_LEFT + indent, y, line)
            y -= _LEADING

    def section_title(title: str) -> None:
        nonlocal y
        ensure_space(_TITLE_SIZE + 20)
        y -= 8
        page.setFillColorRGB(*_INK)
        page.setFont(bold, _TITLE_SIZE)
        page.drawString(_LEFT, y, title)
        y -= 3
        page.setStrokeColorRGB(*_RULE)
        page.setLineWidth(0.45)
        page.line(_LEFT, y, _RIGHT, y)
        y -= 8

    def column_line(left: str, right: str, *, emphasize: bool = False) -> None:
        nonlocal y
        if not left and not right:
            return
        face = bold if emphasize else font
        right_text = right.strip()
        right_w = text_width(right_text, _BODY_SIZE) + 12 if right_text else 0
        first_width = max(72, content_width - right_w)
        lines = wrap(left, first_width, _BODY_SIZE, face) or ([left] if left else [""])
        ensure_space(_LEADING)
        page.setFillColorRGB(*_INK)
        page.setFont(face, _BODY_SIZE)
        if lines[0]:
            page.drawString(_LEFT, y, lines[0])
        if right_text:
            page.setFillColorRGB(*_MUTED)
            page.setFont(font, _BODY_SIZE)
            page.drawRightString(_RIGHT, y, right_text)
        y -= _LEADING
        for extra in lines[1:]:
            ensure_space(_LEADING)
            page.setFillColorRGB(*_INK)
            page.setFont(face, _BODY_SIZE)
            page.drawString(_LEFT, y, extra)
            y -= _LEADING

    def project_head(name: str, stack: str, dates: str) -> None:
        nonlocal y
        date_w = text_width(dates, _BODY_SIZE) + 12 if dates else 0
        first_width = max(72, content_width - date_w)
        name_lines = wrap(name, first_width, _BODY_SIZE, bold) if name else []
        first = name_lines[0] if name_lines else ""
        first_w = text_width(first, _BODY_SIZE, bold) if first else 0
        inline = f"  |  {stack}" if name and stack else ""
        room = _LEFT + first_width
        inline_fits = bool(
            inline
            and _LEFT + first_w + text_width(inline, _BODY_SIZE) <= room
        )
        ensure_space(_LEADING)
        if first:
            page.setFillColorRGB(*_INK)
            page.setFont(bold, _BODY_SIZE)
            page.drawString(_LEFT, y, first)
        if inline_fits:
            page.setFillColorRGB(*_MUTED)
            page.setFont(font, _BODY_SIZE)
            page.drawString(_LEFT + first_w, y, inline)
        elif stack and not name:
            fitted = wrap(stack, first_width, _BODY_SIZE) or [stack]
            page.setFillColorRGB(*_MUTED)
            page.setFont(font, _BODY_SIZE)
            page.drawString(_LEFT, y, fitted[0])
            stack = " ".join(fitted[1:])
        if dates:
            page.setFillColorRGB(*_MUTED)
            page.setFont(font, _BODY_SIZE)
            page.drawRightString(_RIGHT, y, dates)
        y -= _LEADING
        for extra in name_lines[1:]:
            ensure_space(_LEADING)
            page.setFillColorRGB(*_INK)
            page.setFont(bold, _BODY_SIZE)
            page.drawString(_LEFT, y, extra)
            y -= _LEADING
        if stack and not inline_fits:
            draw_wrapped(stack, _LEFT, _BODY_SIZE, content_width, muted=True)

    def labeled(label: str, value: str) -> None:
        nonlocal y
        if not value:
            return
        ensure_space(_LEADING)
        page.setFillColorRGB(*_INK)
        page.setFont(bold, _BODY_SIZE)
        page.drawString(_LEFT, y, label)
        gap = text_width(label, _BODY_SIZE, bold) + 8
        page.setFont(font, _BODY_SIZE)
        lines = wrap(value, content_width - gap, _BODY_SIZE) or [value]
        page.drawString(_LEFT + gap, y, lines[0])
        y -= _LEADING
        for extra in lines[1:]:
            ensure_space(_LEADING)
            page.setFont(font, _BODY_SIZE)
            page.drawString(_LEFT + gap, y, extra)
            y -= _LEADING

    header = resume.header
    draw_centered(header.name or resume.title or "Resume", _NAME_SIZE, face=bold)
    y -= 2
    contact = "  ·  ".join(
        part for part in (header.phone, header.email, header.city) if part
    )
    if contact:
        draw_centered(contact, 9)

    titles = _section_titles(resume.locale)
    labels = _field_labels(resume.locale)

    def draw_extra(extra: ResumeExtra) -> None:
        section_title((extra.title or extra.slug).upper())
        for line in extra.lines:
            draw_bullet(line)
        for item in extra.entries:
            column_line(
                item.organization or item.role,
                format_range(item.start, item.end),
                emphasize=True,
            )
            if item.organization and item.role:
                column_line(item.role, item.city)
            elif item.city and not item.organization:
                column_line("", item.city)
            for line in item.description:
                draw_bullet(line)

    for section in template.sections:
        if section == "summary" and resume.summary:
            section_title(titles[section])
            for line in resume.summary:
                draw_wrapped(line, _LEFT, _BODY_SIZE, content_width)
        elif section == "education" and resume.education:
            section_title(titles[section])
            for item in resume.education:
                column_line(
                    item.institution,
                    format_range(item.start, item.end),
                    emphasize=True,
                )
                subtitle = ", ".join(part for part in (item.field, item.degree) if part)
                column_line(subtitle, item.city)
                if item.honor:
                    draw_wrapped(item.honor, _LEFT, _BODY_SIZE, content_width)
                if item.related_courses:
                    labeled(labels["courses"], ", ".join(item.related_courses))
                y -= 2
        elif section == "internship" and resume.internships:
            section_title(titles[section])
            for item in resume.internships:
                column_line(
                    item.organization,
                    format_range(item.start, item.end),
                    emphasize=True,
                )
                column_line(item.role, item.city)
                for line in item.description:
                    draw_bullet(line)
                y -= 2
        elif section == "work" and resume.work_experiences:
            section_title(titles[section])
            for item in resume.work_experiences:
                column_line(
                    item.organization,
                    format_range(item.start, item.end),
                    emphasize=True,
                )
                column_line(item.role, item.city)
                for line in item.description:
                    draw_bullet(line)
                y -= 2
        elif section == "projects" and resume.projects:
            section_title(titles[section])
            for item in resume.projects:
                project_head(
                    item.name,
                    ", ".join(item.tech_stack),
                    format_range(item.start, item.end),
                )
                if item.description_style == "paragraph":
                    for para in item.description:
                        for piece in para.split("\n"):
                            draw_wrapped(piece, _LEFT, _BODY_SIZE, content_width)
                else:
                    for line in item.description:
                        draw_bullet(line)
                y -= 2
        elif section == "activities" and resume.activities:
            section_title(titles[section])
            for item in resume.activities:
                column_line(
                    item.organization,
                    format_range(item.start, item.end),
                    emphasize=True,
                )
                column_line(item.role, item.city)
                for line in item.description:
                    draw_bullet(line)
                y -= 2
        elif section == "skillsOthers" and (resume.skills or resume.languages):
            section_title(titles[section])
            if resume.skills:
                draw_wrapped(", ".join(resume.skills), _LEFT, _BODY_SIZE, content_width)
            if resume.languages:
                langs = ", ".join(
                    f"{item.name} ({item.level})" if item.level else item.name
                    for item in resume.languages
                )
                labeled(labels["languages"], langs)
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
