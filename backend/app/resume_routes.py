from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from beanie import PydanticObjectId
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.github import (
    GitHubBrowseError,
    GitHubOAuthError,
    GitHubWriteError,
    cv_repo_payload,
    cv_template_path,
    ensure_owned_cv_repo,
    match_authorized_repo,
)
from app.models import (
    CLASSIC_RESUME_TEMPLATE_SLUG,
    Resume,
    ResumeTemplate,
    empty_localized,
)
from app.resume import (
    apply_resume_body,
    apply_template_body,
    builtin_template_slugs,
    delete_cv_template_file,
    ensure_builtin_templates,
    fold_duplicate_custom_templates,
    ensure_resume_dir,
    parse_resume_import,
    render_resume_pdf,
    resume_vault_json,
    save_resume_pdf_bytes,
    sync_cv_templates,
    validate_slug,
    vault_seed_templates,
    write_cv_template_file,
)
from app.store import current_store, new_document

GITHUB_TOKEN_KEY = "github:owner_token"


class ResumeTemplateBody(BaseModel):
    slug: str = Field(min_length=1, max_length=80)
    name: dict[str, str] = Field(default_factory=empty_localized)
    sections: list[str] = Field(
        default_factory=lambda: ["summary", "education", "projects", "skillsOthers"]
    )
    extras: list[dict[str, Any]] = Field(default_factory=list)


class ResumeBody(BaseModel):
    slug: str = Field(min_length=1, max_length=80)
    title: str = ""
    templateSlug: str = "classic-a4"
    locale: str = "en"
    status: str = "draft"
    header: dict[str, Any] = Field(default_factory=dict)
    summary: list[str] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    internships: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    activities: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    languages: list[dict[str, Any]] = Field(default_factory=list)
    extras: list[dict[str, Any]] = Field(default_factory=list)


class ResumeGithubImportBody(BaseModel):
    fullName: str
    path: str
    ref: str = ""
    slug: str = ""
    title: str = ""
    templateSlug: str = ""


def register_resume_routes(app: FastAPI, require_owner: Callable) -> None:
    async def unique_template_slug(slug: str, exclude_id: str | None = None) -> None:
        existing = await current_store().find_one(ResumeTemplate, slug=slug)
        if existing is not None and str(existing.id) != exclude_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="slug_taken"
            )

    async def unique_resume_slug(slug: str, exclude_id: str | None = None) -> None:
        existing = await current_store().find_one(Resume, slug=slug)
        if existing is not None and str(existing.id) != exclude_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="slug_taken"
            )

    async def load_template(slug: str) -> ResumeTemplate:
        await ensure_builtin_templates()
        template = await current_store().find_one(ResumeTemplate, slug=slug)
        if template is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="template_not_found"
            )
        return template

    async def owner_token() -> str | None:
        token = await app.state.redis.get(GITHUB_TOKEN_KEY)
        return str(token) if token else None

    async def refresh_templates() -> None:
        access = await owner_token()
        if access:
            try:
                await sync_cv_templates(
                    app.state.github, access_token=access
                )
            except (GitHubOAuthError, GitHubWriteError, GitHubBrowseError):
                pass
        await fold_duplicate_custom_templates()

    async def push_template(
        template: ResumeTemplate, *, previous_path: str = ""
    ) -> None:
        access = await owner_token()
        if not access:
            return
        try:
            await write_cv_template_file(
                app.state.github,
                access_token=access,
                template=template,
                previous_path=previous_path,
            )
        except (GitHubOAuthError, GitHubWriteError):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="github_write_failed",
            ) from None

    @app.get("/api/public/resumes")
    async def public_list_resumes() -> list[dict[str, Any]]:
        rows = await current_store().find(Resume, status="published")
        rows.sort(key=lambda item: item.slug)
        return [
            {
                "slug": item.slug,
                "title": item.header.name or item.title or item.slug,
                "locale": item.locale,
                "pdfUrl": item.pdf_url() if item.pdf_filename else "",
            }
            for item in rows
        ]

    @app.get("/api/public/resumes/{slug}")
    async def public_get_resume(slug: str) -> dict[str, Any]:
        row = await current_store().find_one(
            Resume, slug=validate_slug(slug), status="published"
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        return row.to_public_dict()

    @app.get("/api/public/resumes/{slug}/pdf")
    async def public_resume_pdf(slug: str) -> Response:
        row = await current_store().find_one(
            Resume, slug=validate_slug(slug), status="published"
        )
        if row is None or not row.pdf_filename:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        path = ensure_resume_dir(app.state.settings.resume_dir) / Path(row.pdf_filename).name
        if not path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        return Response(
            content=path.read_bytes(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{row.slug}.pdf"'},
        )

    @app.get("/api/owner/resume-templates")
    async def owner_list_templates(_: str = Depends(require_owner)) -> list[dict[str, Any]]:
        await refresh_templates()
        rows = await current_store().find_all(ResumeTemplate)
        order = {CLASSIC_RESUME_TEMPLATE_SLUG: 0}
        for index, spec in enumerate(vault_seed_templates(), start=1):
            order[spec["slug"]] = index
        rows.sort(key=lambda item: (order.get(item.slug, 100), item.slug))
        return [item.to_owner_dict() for item in rows]

    @app.post("/api/owner/resume-templates")
    async def owner_create_template(
        body: ResumeTemplateBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        template = new_document(ResumeTemplate)
        apply_template_body(template, body.model_dump())
        if template.slug in builtin_template_slugs():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="reserved_template",
            )
        await unique_template_slug(template.slug)
        template.github_path = cv_template_path(template.slug)
        await push_template(template)
        await current_store().insert(template)
        return template.to_owner_dict()

    @app.put("/api/owner/resume-templates/{template_id}")
    async def owner_update_template(
        template_id: PydanticObjectId,
        body: ResumeTemplateBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        template = await current_store().get(ResumeTemplate, template_id)
        if template is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        if template.builtin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="builtin_template"
            )
        previous_path = template.github_path
        apply_template_body(template, body.model_dump())
        await unique_template_slug(template.slug, exclude_id=str(template.id))
        template.github_path = cv_template_path(template.slug)
        await push_template(template, previous_path=previous_path)
        await current_store().save(template)
        return template.to_owner_dict()

    @app.delete("/api/owner/resume-templates/{template_id}")
    async def owner_delete_template(
        template_id: PydanticObjectId,
        _: str = Depends(require_owner),
    ) -> dict[str, str]:
        template = await current_store().get(ResumeTemplate, template_id)
        if template is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        if template.builtin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="builtin_template"
            )
        access = await owner_token()
        if access and (template.github_path or template.slug):
            try:
                await delete_cv_template_file(
                    app.state.github,
                    access_token=access,
                    path=template.github_path
                    or cv_template_path(template.slug),
                )
            except (GitHubOAuthError, GitHubWriteError):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="github_write_failed",
                ) from None
        await current_store().delete(template)
        return {"status": "deleted"}

    @app.get("/api/owner/resumes")
    async def owner_list_resumes(_: str = Depends(require_owner)) -> list[dict[str, Any]]:
        await ensure_builtin_templates()
        rows = await current_store().find_all(Resume)
        rows.sort(key=lambda item: item.slug)
        return [item.to_owner_dict() for item in rows]

    @app.post("/api/owner/resumes")
    async def owner_create_resume(
        body: ResumeBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        await load_template(body.templateSlug)
        resume = new_document(Resume)
        apply_resume_body(resume, body.model_dump())
        await unique_resume_slug(resume.slug)
        await current_store().insert(resume)
        return resume.to_owner_dict()

    @app.put("/api/owner/resumes/{resume_id}")
    async def owner_update_resume(
        resume_id: PydanticObjectId,
        body: ResumeBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        resume = await current_store().get(Resume, resume_id)
        if resume is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        await load_template(body.templateSlug or resume.template_slug)
        apply_resume_body(resume, body.model_dump())
        await unique_resume_slug(resume.slug, exclude_id=str(resume.id))
        await current_store().save(resume)
        return resume.to_owner_dict()

    @app.delete("/api/owner/resumes/{resume_id}")
    async def owner_delete_resume(
        resume_id: PydanticObjectId,
        _: str = Depends(require_owner),
    ) -> dict[str, str]:
        resume = await current_store().get(Resume, resume_id)
        if resume is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        directory = ensure_resume_dir(app.state.settings.resume_dir)
        if resume.pdf_filename:
            old = directory / Path(resume.pdf_filename).name
            if old.exists():
                old.unlink(missing_ok=True)
        await current_store().delete(resume)
        return {"status": "deleted"}

    async def generate_pdf(resume: Resume) -> Resume:
        template = await load_template(resume.template_slug)
        data = render_resume_pdf(resume, template)
        directory = ensure_resume_dir(app.state.settings.resume_dir)
        resume.pdf_filename = save_resume_pdf_bytes(
            data, directory=directory, previous_filename=resume.pdf_filename
        )
        await current_store().save(resume)
        return resume

    @app.post("/api/owner/resumes/{resume_id}/generate")
    async def owner_generate_resume(
        resume_id: PydanticObjectId,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        resume = await current_store().get(Resume, resume_id)
        if resume is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        resume = await generate_pdf(resume)
        return resume.to_owner_dict()

    @app.post("/api/owner/resumes/{resume_id}/publish")
    async def owner_publish_resume(
        resume_id: PydanticObjectId,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        resume = await current_store().get(Resume, resume_id)
        if resume is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        if not resume.pdf_filename:
            resume = await generate_pdf(resume)
        resume.status = "published"
        await current_store().save(resume)
        return resume.to_owner_dict()

    @app.post("/api/owner/resumes/{resume_id}/push-github")
    async def owner_push_resume_github(
        resume_id: PydanticObjectId,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        access = await owner_token()
        if not access:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="github_not_connected"
            )
        resume = await current_store().get(Resume, resume_id)
        if resume is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        if not resume.pdf_filename:
            resume = await generate_pdf(resume)
        directory = ensure_resume_dir(app.state.settings.resume_dir)
        pdf_path = directory / Path(resume.pdf_filename).name
        if not pdf_path.is_file():
            resume = await generate_pdf(resume)
            pdf_path = directory / Path(resume.pdf_filename).name
        try:
            repo, created = await ensure_owned_cv_repo(
                app.state.github, access_token=access
            )
            json_name = f"{resume.slug}.json"
            pdf_name = f"{resume.slug}.pdf"
            branch = str(repo.get("defaultBranch") or "main")
            json_put = await app.state.github.put_file(
                access_token=access,
                owner=str(repo["owner"]),
                name=str(repo["name"]),
                path=json_name,
                content=resume_vault_json(resume),
                message=f"Update {resume.slug} resume JSON",
                branch=branch,
            )
            pdf_put = await app.state.github.put_file(
                access_token=access,
                owner=str(repo["owner"]),
                name=str(repo["name"]),
                path=pdf_name,
                content=pdf_path.read_bytes(),
                message=f"Update {resume.slug} resume PDF",
                branch=branch,
            )
        except GitHubOAuthError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="github_not_connected"
            ) from None
        except GitHubWriteError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail="github_write_failed"
            ) from None
        resume.github_repo = str(repo["fullName"])
        resume.github_json_path = json_name
        resume.github_pdf_path = pdf_name
        await current_store().save(resume)
        return {
            "created": created,
            "repo": cv_repo_payload(repo, [], created=created),
            "files": [json_put, pdf_put],
            "resume": resume.to_owner_dict(),
        }

    @app.get("/api/owner/resumes/{resume_id}/pdf")
    async def owner_resume_pdf(
        resume_id: PydanticObjectId,
        _: str = Depends(require_owner),
    ) -> Response:
        resume = await current_store().get(Resume, resume_id)
        if resume is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        if not resume.pdf_filename:
            resume = await generate_pdf(resume)
        path = ensure_resume_dir(app.state.settings.resume_dir) / Path(resume.pdf_filename).name
        return Response(
            content=path.read_bytes(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{resume.slug}.pdf"'},
        )

    @app.post("/api/owner/resumes/import-github")
    async def owner_import_resume_github(
        body: ResumeGithubImportBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        access = await owner_token()
        if not access:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="github_not_connected"
            )
        try:
            repos = await app.state.github.list_repos(access_token=access)
            repo = match_authorized_repo(repos, body.fullName)
            if repo is None:
                raise GitHubBrowseError("not_found")
            blob = await app.state.github.get_blob(
                access_token=access,
                owner=str(repo["owner"]),
                name=str(repo["name"]),
                ref=body.ref or str(repo.get("defaultBranch") or "main"),
                path=body.path,
            )
        except (GitHubBrowseError, KeyError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="github_file_not_found"
            ) from exc
        imported = parse_resume_import(blob.get("content"))
        slug = validate_slug(body.slug or imported.get("title") or "imported-resume")
        imported["slug"] = slug
        if body.title:
            imported["title"] = body.title
        if body.templateSlug:
            imported["templateSlug"] = body.templateSlug
        await load_template(str(imported.get("templateSlug") or "classic-a4"))
        existing = await current_store().find_one(Resume, slug=slug)
        resume = existing or new_document(Resume)
        apply_resume_body(resume, imported)
        if existing is None:
            await current_store().insert(resume)
        else:
            await current_store().save(resume)
        return resume.to_owner_dict()
