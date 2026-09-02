from __future__ import annotations

import json
import secrets
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from beanie import PydanticObjectId, init_beanie
from fastapi import Depends, FastAPI, File, Header, HTTPException, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from pymongo import AsyncMongoClient
from redis.asyncio import Redis

from app.auth import AuthService
from app.avatar import (
    ensure_avatar_dir,
    media_type_for_filename,
    resolve_avatar_path,
    save_avatar_file,
    save_hero_visual_file,
    content_public_url,
)
from app.config import Settings
from app.github import GitHubBrowseError, GitHubClient, GitHubOAuthError, HttpGitHub
from app.mailer import ConsoleMailer, Mailer, SmtpMailer, SmtpThenConsoleMailer
from app.models import (
    ABOUT_KINDS,
    LOCALES,
    STATUSES,
    AboutModule,
    Article,
    ArticleCategory,
    Comment,
    Journal,
    LinkItem,
    Project,
    SiteProfile,
    SourceRepo,
    dated,
    empty_localized,
    pick_localized,
)
from app.store import bind_store, build_store, current_store, new_document
from app.translate import (
    GoogleGtxTranslator,
    MachineTranslator,
    fill_localized,
)


async def check_mongo(mongo: AsyncMongoClient) -> bool:
    try:
        await mongo.admin.command("ping")
        return True
    except Exception:
        return False


async def close_mongo(mongo: AsyncMongoClient) -> None:
    closer = getattr(mongo, "aclose", mongo.close)
    result = closer()
    if hasattr(result, "__await__"):
        await result


async def check_redis(redis: Redis) -> bool:
    try:
        return bool(await redis.ping())
    except Exception:
        return False


class OtpRequestBody(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class OtpVerifyBody(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    code: str = Field(min_length=4, max_length=12)


class LinkInput(BaseModel):
    label: dict[str, str] = Field(default_factory=empty_localized)
    url: str = ""
    order: int = 0


class SiteUpdateBody(BaseModel):
    brand: dict[str, str] = Field(default_factory=empty_localized)
    heroHeadline: dict[str, str] = Field(default_factory=empty_localized)
    heroSupport: dict[str, str] = Field(default_factory=empty_localized)
    heroCtaProjects: dict[str, str] = Field(default_factory=empty_localized)
    heroCtaArticles: dict[str, str] = Field(default_factory=empty_localized)
    bio: dict[str, str] = Field(default_factory=empty_localized)
    skills: dict[str, str] = Field(default_factory=empty_localized)
    experience: dict[str, str] = Field(default_factory=empty_localized)
    publicEmail: str = ""
    links: list[LinkInput] = Field(default_factory=list)
    heroVisualPosX: float = 50
    heroVisualPosY: float = 50
    heroVisualScale: float = 100
    heroVisualBlur: float = 0
    articlesLead: dict[str, str] = Field(default_factory=empty_localized)
    aboutLead: dict[str, str] = Field(default_factory=empty_localized)
    aboutEmpty: dict[str, str] = Field(default_factory=empty_localized)


class ProjectBody(BaseModel):
    slug: str = Field(min_length=1, max_length=80)
    title: dict[str, str] = Field(default_factory=empty_localized)
    summary: dict[str, str] = Field(default_factory=empty_localized)
    body: dict[str, str] = Field(default_factory=empty_localized)
    status: str = "draft"
    order: int = 0


class SourceRepoBody(BaseModel):
    fullName: str = Field(min_length=1, max_length=200)


class ArticleBody(BaseModel):
    slug: str = Field(min_length=1, max_length=80)
    title: dict[str, str] = Field(default_factory=empty_localized)
    summary: dict[str, str] = Field(default_factory=empty_localized)
    body: dict[str, str] = Field(default_factory=empty_localized)
    status: str = "draft"
    order: int = 0
    relatedProjectSlug: str = ""
    categorySlug: str = ""


class ArticleCategoryBody(BaseModel):
    slug: str = Field(min_length=1, max_length=80)
    title: dict[str, str] = Field(default_factory=empty_localized)
    order: int = 0


class CommentSubmitBody(BaseModel):
    displayName: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=320)
    body: str = Field(min_length=1, max_length=4000)


class OwnerReplyBody(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class JournalBody(BaseModel):
    model_config = ConfigDict(extra="allow")
    slug: str = Field(min_length=1, max_length=80)
    title: dict[str, str] = Field(default_factory=empty_localized)
    summary: dict[str, str] = Field(default_factory=empty_localized)
    body: dict[str, str] = Field(default_factory=empty_localized)
    status: str = "draft"
    order: int = 0


class AboutModuleBody(BaseModel):
    slug: str = Field(min_length=1, max_length=80)
    kind: str = "custom"
    title: dict[str, str] = Field(default_factory=empty_localized)
    body: dict[str, str] = Field(default_factory=empty_localized)
    status: str = "draft"
    order: int = 0


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


async def get_or_create_site() -> SiteProfile:
    store = current_store()
    site = await store.find_one(SiteProfile)
    if site is None:
        site = new_document(SiteProfile)
        await store.insert(site)
    return site


GITHUB_STATE_TTL = 600
GITHUB_TOKEN_KEY = "github:owner_token"


def create_app(
    settings: Settings | None = None,
    mailer: Mailer | None = None,
    github: GitHubClient | None = None,
    translator: MachineTranslator | None = None,
) -> FastAPI:
    settings = settings or Settings()
    if mailer is not None:
        resolved_mailer: Mailer = mailer
    elif settings.mail_backend.lower() == "console":
        resolved_mailer = ConsoleMailer()
    else:
        resolved_mailer = SmtpThenConsoleMailer(
            SmtpMailer(
                host=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                from_addr=settings.smtp_from,
            ),
            ConsoleMailer(),
        )
    resolved_github: GitHubClient = github or HttpGitHub(
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        callback_url=settings.github_oauth_callback_url,
    )
    resolved_translator: MachineTranslator = translator or GoogleGtxTranslator()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        await redis.ping()
        mongo = None
        store = build_store(settings.mongo_uri, settings.local_data_dir)
        if settings.uses_mongo:
            mongo = AsyncMongoClient(settings.mongo_uri)
            await init_beanie(
                database=mongo[settings.mongo_db],
                document_models=[
                    SiteProfile,
                    Project,
                    ArticleCategory,
                    Article,
                    Journal,
                    AboutModule,
                    Comment,
                ],
            )
        bind_store(store)
        avatar_dir = ensure_avatar_dir(settings.avatar_dir)
        print(f"[media] dir={avatar_dir}", flush=True)
        app.state.mongo = mongo
        app.state.store = store
        app.state.redis = redis
        app.state.settings = settings
        app.state.mailer = resolved_mailer
        app.state.github = resolved_github
        app.state.translator = resolved_translator
        app.state.avatar_dir = avatar_dir
        app.state.auth = AuthService(
            redis=redis,
            settings=settings,
            mailer=resolved_mailer,
        )
        print(
            f"[mail] backend={settings.mail_backend} mailer={type(resolved_mailer).__name__}",
            flush=True,
        )
        if settings.mail_backend.lower() != "console":
            print(
                "[mail] SMTP from GCP Compute Engine often times out "
                "(outbound 25/465/587 blocked); OTP will print to logs on failure.",
                flush=True,
            )
        print(
            f"[store] kind={store.kind} mongo={'on' if settings.uses_mongo else 'off'}",
            flush=True,
        )
        try:
            yield
        finally:
            await redis.aclose()
            if mongo is not None:
                await close_mongo(mongo)
            bind_store(None)

    app = FastAPI(title="Portfolio API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.mailer = resolved_mailer
    app.state.translator = resolved_translator

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_auth() -> AuthService:
        return app.state.auth

    async def require_owner(
        authorization: str | None = Header(default=None),
        auth: AuthService = Depends(get_auth),
    ) -> str:
        scheme, _, token = (authorization or "").partition(" ")
        if scheme.lower() != "bearer":
            token = ""
        return await auth.resolve_session(token or None)

    @app.get("/api/health")
    async def health(response: Response) -> dict[str, str]:
        redis: Redis = app.state.redis
        redis_up = await check_redis(redis)
        if settings.uses_mongo:
            mongo_up = await check_mongo(app.state.mongo)
            storage = "up" if mongo_up else "down"
            healthy = mongo_up and redis_up
        else:
            storage = "local"
            healthy = redis_up
        payload = {
            "status": "ok" if healthy else "degraded",
            "mongo": storage,
            "redis": "up" if redis_up else "down",
        }
        if payload["status"] != "ok":
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return payload

    @app.post("/api/auth/otp/request")
    async def otp_request(
        body: OtpRequestBody,
        auth: AuthService = Depends(get_auth),
    ) -> dict[str, str]:
        print(f"[otp] request received for {body.email}", flush=True)
        try:
            await auth.request_otp(body.email)
        except HTTPException:
            raise
        except Exception as exc:
            print(f"[otp] failed: {type(exc).__name__}: {exc}", flush=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="smtp_failed",
            ) from None
        return {"status": "sent"}

    @app.post("/api/auth/otp/verify")
    async def otp_verify(
        body: OtpVerifyBody,
        auth: AuthService = Depends(get_auth),
    ) -> dict[str, str]:
        token = await auth.verify_otp(body.email, body.code)
        return {"session_token": token}

    @app.get("/api/auth/me")
    async def me(email: str = Depends(require_owner)) -> dict[str, str]:
        return {"email": email, "role": "owner"}

    @app.post("/api/owner/translate")
    async def owner_translate(
        body: dict[str, str],
        _: str = Depends(require_owner),
    ) -> dict[str, object]:
        try:
            filled, source, warnings = await fill_localized(
                body,
                translator=app.state.translator,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from None
        return {**filled, "source": source, "warnings": warnings}

    @app.get("/api/public/site")
    async def public_site(locale: str = "zh-Hant") -> dict[str, Any]:
        locale = normalize_locale(locale)
        site = await get_or_create_site()
        return site.resolve(locale)

    @app.get("/api/owner/site")
    async def owner_get_site(
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        site = await get_or_create_site()
        return site.to_owner_dict()

    @app.put("/api/owner/site")
    async def owner_put_site(
        body: SiteUpdateBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        site = await get_or_create_site()
        site.brand = body.brand
        site.hero_headline = body.heroHeadline
        site.hero_support = body.heroSupport
        site.hero_cta_projects = body.heroCtaProjects
        site.hero_cta_articles = body.heroCtaArticles
        site.bio = body.bio
        site.skills = body.skills
        site.experience = body.experience
        site.public_email = body.publicEmail
        site.links = [
            LinkItem(label=item.label, url=item.url, order=item.order)
            for item in body.links
        ]
        site.hero_visual_pos_x = clamp(body.heroVisualPosX, 0, 100)
        site.hero_visual_pos_y = clamp(body.heroVisualPosY, 0, 100)
        site.hero_visual_scale = clamp(body.heroVisualScale, 80, 180)
        site.hero_visual_blur = clamp(body.heroVisualBlur, 0, 48)
        site.articles_lead = body.articlesLead
        site.about_lead = body.aboutLead
        site.about_empty = body.aboutEmpty
        await current_store().save(site)
        return site.to_owner_dict()

    @app.post("/api/owner/avatar")
    async def owner_upload_avatar(
        file: UploadFile = File(...),
        _: str = Depends(require_owner),
    ) -> dict[str, str]:
        site = await get_or_create_site()
        settings: Settings = app.state.settings
        directory: Path = app.state.avatar_dir
        filename = await save_avatar_file(
            file,
            directory=directory,
            max_bytes=settings.avatar_max_bytes,
            previous_filename=site.avatar_filename or None,
        )
        site.avatar_filename = filename
        await current_store().save(site)
        return {"avatarUrl": site.avatar_url()}

    @app.get("/api/public/media/avatar/{filename}")
    async def public_avatar(filename: str) -> FileResponse:
        directory: Path = app.state.avatar_dir
        path = resolve_avatar_path(directory, filename)
        if path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        media_type = media_type_for_filename(path.name)
        return FileResponse(
            path,
            media_type=media_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @app.post("/api/owner/media")
    async def owner_upload_content_image(
        file: UploadFile = File(...),
        _: str = Depends(require_owner),
    ) -> dict[str, str]:
        settings: Settings = app.state.settings
        directory: Path = app.state.avatar_dir
        filename = await save_avatar_file(
            file,
            directory=directory,
            max_bytes=max(settings.avatar_max_bytes, 4 * 1024 * 1024),
            previous_filename=None,
        )
        return {"url": content_public_url(filename)}

    @app.get("/api/public/media/content/{filename}")
    async def public_content_image(filename: str) -> FileResponse:
        directory: Path = app.state.avatar_dir
        path = resolve_avatar_path(directory, filename)
        if path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        media_type = media_type_for_filename(path.name)
        return FileResponse(
            path,
            media_type=media_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @app.post("/api/owner/hero-visual")
    async def owner_upload_hero_visual(
        file: UploadFile = File(...),
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        site = await get_or_create_site()
        settings: Settings = app.state.settings
        directory: Path = app.state.avatar_dir
        filename = await save_hero_visual_file(
            file,
            directory=directory,
            max_bytes=max(settings.avatar_max_bytes, 4 * 1024 * 1024),
            previous_filename=site.hero_visual_filename or None,
        )
        site.hero_visual_filename = filename
        await current_store().save(site)
        return site.to_owner_dict()

    @app.delete("/api/owner/hero-visual")
    async def owner_clear_hero_visual(
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        site = await get_or_create_site()
        directory: Path = app.state.avatar_dir
        if site.hero_visual_filename:
            old = directory / Path(site.hero_visual_filename).name
            old.unlink(missing_ok=True)
        site.hero_visual_filename = ""
        await current_store().save(site)
        return site.to_owner_dict()

    @app.get("/api/public/media/hero/{filename}")
    async def public_hero_visual(filename: str) -> FileResponse:
        directory: Path = app.state.avatar_dir
        path = resolve_avatar_path(directory, filename)
        if path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        media_type = media_type_for_filename(path.name)
        return FileResponse(
            path,
            media_type=media_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )

    def normalize_locale(locale: str) -> str:
        return locale if locale in LOCALES else "zh-Hant"

    def apply_project_body(project: Project, body: ProjectBody) -> None:
        if body.status not in STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_status",
            )
        slug = body.slug.strip().lower()
        if not slug:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_slug",
            )
        project.slug = slug
        project.title = body.title
        project.summary = body.summary
        project.body = body.body
        project.status = body.status
        project.order = body.order

    async def ensure_unique_slug(slug: str, exclude_id: str | None = None) -> None:
        existing = await current_store().find_one(Project, slug=slug)
        if existing is not None and str(existing.id) != exclude_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="slug_taken",
            )

    @app.get("/api/public/projects")
    async def public_projects(locale: str = "zh-Hant") -> list[dict[str, Any]]:
        locale = normalize_locale(locale)
        projects = await current_store().find(Project, status="published")
        projects.sort(key=lambda item: (item.order, item.slug))
        return [item.resolve(locale) for item in projects]

    @app.get("/api/public/projects/{slug}")
    async def public_project(
        slug: str, locale: str = "zh-Hant"
    ) -> dict[str, Any]:
        locale = normalize_locale(locale)
        project = await current_store().find_one(
            Project, slug=slug, status="published"
        )
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        return project.resolve(locale)

    GITHUB_CACHE_TTL = 120

    async def published_browsable_source(slug: str) -> tuple[SourceRepo, str]:
        project = await current_store().find_one(
            Project, slug=slug, status="published"
        )
        repo = project.source_repo if project is not None else None
        if repo is None or not repo.full_name or repo.private:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        access = await github_access_token()
        if not access:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        github_client: GitHubClient = app.state.github
        try:
            if await github_client.repo_is_private(
                access_token=access,
                owner=repo.owner,
                name=repo.name,
            ):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="not_found",
                )
        except GitHubBrowseError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            ) from None
        return repo, access

    async def cached_github(
        *,
        kind: str,
        full_name: str,
        ref: str,
        path: str,
        loader,
    ):
        redis: Redis = app.state.redis
        key = f"github:src:{full_name}:{kind}:{ref}:{path}"
        raw = await redis.get(key)
        if raw:
            return json.loads(raw)
        data = await loader()
        await redis.set(key, json.dumps(data), ex=GITHUB_CACHE_TTL)
        return data

    @app.get("/api/public/projects/{slug}/source")
    async def public_project_source(
        slug: str, ref: str = ""
    ) -> dict[str, Any]:
        repo, access = await published_browsable_source(slug)
        github_client: GitHubClient = app.state.github
        branch = ref or repo.default_branch or "main"
        try:
            branches = await cached_github(
                kind="branches",
                full_name=repo.full_name,
                ref="-",
                path="",
                loader=lambda: github_client.list_branches(
                    access_token=access,
                    owner=repo.owner,
                    name=repo.name,
                ),
            )
            try:
                readme = await cached_github(
                    kind="readme",
                    full_name=repo.full_name,
                    ref=branch,
                    path="",
                    loader=lambda: github_client.get_readme(
                        access_token=access,
                        owner=repo.owner,
                        name=repo.name,
                        ref=branch,
                    ),
                )
            except GitHubBrowseError:
                readme = {"path": "", "content": ""}
            tree = await cached_github(
                kind="tree",
                full_name=repo.full_name,
                ref=branch,
                path="",
                loader=lambda: github_client.list_tree(
                    access_token=access,
                    owner=repo.owner,
                    name=repo.name,
                    ref=branch,
                    path="",
                ),
            )
        except GitHubBrowseError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            ) from None
        return {
            "defaultBranch": repo.default_branch,
            "ref": branch,
            "branches": branches,
            "readme": readme,
            "tree": tree,
        }

    @app.get("/api/public/projects/{slug}/source/tree")
    async def public_project_source_tree(
        slug: str, ref: str = "", path: str = ""
    ) -> dict[str, Any]:
        repo, access = await published_browsable_source(slug)
        github_client: GitHubClient = app.state.github
        branch = ref or repo.default_branch or "main"
        try:
            tree = await cached_github(
                kind="tree",
                full_name=repo.full_name,
                ref=branch,
                path=path,
                loader=lambda: github_client.list_tree(
                    access_token=access,
                    owner=repo.owner,
                    name=repo.name,
                    ref=branch,
                    path=path,
                ),
            )
        except GitHubBrowseError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            ) from None
        return {"ref": branch, "path": path, "tree": tree}

    @app.get("/api/public/projects/{slug}/source/blob")
    async def public_project_source_blob(
        slug: str, ref: str = "", path: str = ""
    ) -> dict[str, Any]:
        if not path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="path_required",
            )
        repo, access = await published_browsable_source(slug)
        github_client: GitHubClient = app.state.github
        branch = ref or repo.default_branch or "main"
        try:
            blob = await cached_github(
                kind="blob",
                full_name=repo.full_name,
                ref=branch,
                path=path,
                loader=lambda: github_client.get_blob(
                    access_token=access,
                    owner=repo.owner,
                    name=repo.name,
                    ref=branch,
                    path=path,
                ),
            )
        except GitHubBrowseError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            ) from None
        return blob

    @app.get("/api/owner/projects")
    async def owner_list_projects(
        _: str = Depends(require_owner),
    ) -> list[dict[str, Any]]:
        projects = await current_store().find_all(Project)
        projects.sort(key=lambda item: (item.order, item.slug))
        return [item.to_owner_dict() for item in projects]

    @app.post("/api/owner/projects")
    async def owner_create_project(
        body: ProjectBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        project = new_document(Project)
        apply_project_body(project, body)
        await ensure_unique_slug(project.slug)
        await current_store().insert(project)
        return project.to_owner_dict()

    @app.put("/api/owner/projects/{project_id}")
    async def owner_update_project(
        project_id: PydanticObjectId,
        body: ProjectBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        project = await current_store().get(Project, project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        apply_project_body(project, body)
        await ensure_unique_slug(project.slug, exclude_id=str(project.id))
        await current_store().save(project)
        return project.to_owner_dict()

    def github_redirect(*, connected: bool) -> RedirectResponse:
        dest = settings.github_oauth_success_url
        joiner = "&" if "?" in dest else "?"
        flag = "connected" if connected else "error"
        return RedirectResponse(f"{dest}{joiner}github={flag}", status_code=302)

    async def github_access_token() -> str | None:
        redis: Redis = app.state.redis
        token = await redis.get(GITHUB_TOKEN_KEY)
        return str(token) if token else None

    @app.get("/api/owner/github/oauth/start")
    async def owner_github_oauth_start(
        _: str = Depends(require_owner),
    ) -> dict[str, str]:
        if not settings.github_client_id.strip():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="github_not_configured",
            )
        redis: Redis = app.state.redis
        github_client: GitHubClient = app.state.github
        state = secrets.token_urlsafe(24)
        await redis.set(f"github:oauth:{state}", "1", ex=GITHUB_STATE_TTL)
        return {"authorizationUrl": github_client.authorization_url(state=state)}

    @app.get("/api/auth/github/callback")
    async def github_oauth_callback(
        code: str = "",
        state: str = "",
    ) -> RedirectResponse:
        redis: Redis = app.state.redis
        github_client: GitHubClient = app.state.github
        stored = await redis.get(f"github:oauth:{state}") if state else None
        if stored:
            await redis.delete(f"github:oauth:{state}")
        if not code or not stored:
            return github_redirect(connected=False)
        try:
            access = await github_client.exchange_code(code=code)
        except GitHubOAuthError:
            return github_redirect(connected=False)
        await redis.set(
            GITHUB_TOKEN_KEY,
            access,
            ex=settings.session_ttl_seconds,
        )
        return github_redirect(connected=True)

    @app.get("/api/owner/github/repos")
    async def owner_github_repos(
        _: str = Depends(require_owner),
    ) -> list[dict[str, Any]]:
        access = await github_access_token()
        if not access:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="github_not_connected",
            )
        github_client: GitHubClient = app.state.github
        try:
            return await github_client.list_repos(access_token=access)
        except GitHubOAuthError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="github_not_connected",
            ) from None

    @app.put("/api/owner/projects/{project_id}/source-repo")
    async def owner_attach_source_repo(
        project_id: PydanticObjectId,
        body: SourceRepoBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        project = await current_store().get(Project, project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        access = await github_access_token()
        if not access:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="github_not_connected",
            )
        github_client: GitHubClient = app.state.github
        repos = await github_client.list_repos(access_token=access)
        match = next(
            (item for item in repos if item.get("fullName") == body.fullName),
            None,
        )
        if match is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="unknown_repo",
            )
        project.source_repo = SourceRepo.from_github(match)
        await current_store().save(project)
        return project.to_owner_dict()

    def normalize_slug(value: str, *, detail: str = "invalid_slug") -> str:
        slug = value.strip().lower().strip("/")
        if not slug:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail,
            )
        return slug

    def slug_candidates(value: str) -> list[str]:
        raw = value.strip()
        clean = raw.lower().strip("/")
        seen: list[str] = []
        for item in (raw, clean, f"/{clean}"):
            if item and item not in seen:
                seen.append(item)
        return seen

    async def find_article_by_slug(
        slug: str, *, published_only: bool = False
    ) -> Article | None:
        store = current_store()
        extras = {"status": "published"} if published_only else {}
        for candidate in slug_candidates(slug):
            article = await store.find_one(Article, slug=candidate, **extras)
            if article is not None:
                return article
        wanted = slug.strip().lower().strip("/")
        articles = (
            await store.find(Article, **extras)
            if extras
            else await store.find_all(Article)
        )
        for article in articles:
            if (article.slug or "").strip().lower().strip("/") == wanted:
                return article
        return None

    async def heal_article_slug(article: Article) -> str:
        clean = normalize_slug(article.slug)
        if article.slug != clean:
            article.slug = clean
            await current_store().save(article)
        return clean

    async def apply_article_body(article: Article, body: ArticleBody) -> None:
        if body.status not in STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_status",
            )
        slug = normalize_slug(body.slug)
        raw_category = (body.categorySlug or "").strip()
        category_slug = ""
        if raw_category:
            wanted = normalize_slug(raw_category)
            category = await current_store().find_one(
                ArticleCategory, slug=wanted
            )
            if category is not None:
                category_slug = category.slug
        article.slug = slug
        article.title = body.title
        article.summary = body.summary
        article.body = body.body
        article.status = body.status
        article.order = body.order
        article.related_project_slug = body.relatedProjectSlug.strip().lower()
        article.category_slug = category_slug
        if body.status == "published" and article.published_at is None:
            article.published_at = datetime.now(timezone.utc)

    async def ensure_unique_article_slug(
        slug: str, exclude_id: str | None = None
    ) -> None:
        existing = await current_store().find_one(Article, slug=slug)
        if existing is not None and str(existing.id) != exclude_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="slug_taken",
            )

    async def ensure_unique_category_slug(
        slug: str, exclude_id: str | None = None
    ) -> None:
        existing = await current_store().find_one(ArticleCategory, slug=slug)
        if existing is not None and str(existing.id) != exclude_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="slug_taken",
            )

    async def public_article_payload(article: Article, locale: str) -> dict[str, Any]:
        payload = article.resolve(locale)
        payload["slug"] = await heal_article_slug(article)
        related_slug = article.related_project_slug
        if related_slug:
            project = await current_store().find_one(
                Project, slug=related_slug, status="published"
            )
            if project is not None:
                payload["relatedProject"] = {
                    "slug": project.slug,
                    "title": project.resolve(locale)["title"],
                }
        raw_category = (article.category_slug or "").strip()
        category = (
            await current_store().find_one(ArticleCategory, slug=raw_category)
            if raw_category
            else None
        )
        if category is None:
            if article.category_slug:
                article.category_slug = ""
                await current_store().save(article)
            payload["categorySlug"] = ""
            payload["categoryTitle"] = ""
        else:
            payload["categorySlug"] = category.slug
            payload["categoryTitle"] = pick_localized(category.title, locale)
        return payload

    @app.get("/api/public/article-categories")
    async def public_article_categories(
        locale: str = "zh-Hant",
    ) -> list[dict[str, Any]]:
        locale = normalize_locale(locale)
        categories = await current_store().find_all(ArticleCategory)
        categories.sort(key=lambda item: (item.order, item.slug))
        return [item.resolve(locale) for item in categories]

    @app.get("/api/public/articles")
    async def public_articles(
        locale: str = "zh-Hant",
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        locale = normalize_locale(locale)
        articles = await current_store().find(Article, status="published")
        if category:
            wanted = category.strip().lower()
            articles = [
                item
                for item in articles
                if (item.category_slug or "") == wanted
            ]
        articles.sort(key=lambda item: dated(item.published_at, item.id), reverse=True)
        return [await public_article_payload(item, locale) for item in articles]

    @app.get("/api/public/articles/{slug}")
    async def public_article(
        slug: str, locale: str = "zh-Hant"
    ) -> dict[str, Any]:
        locale = normalize_locale(locale)
        article = await find_article_by_slug(slug, published_only=True)
        if article is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        return await public_article_payload(article, locale)

    @app.get("/api/owner/article-categories")
    async def owner_list_article_categories(
        _: str = Depends(require_owner),
    ) -> list[dict[str, Any]]:
        categories = await current_store().find_all(ArticleCategory)
        categories.sort(key=lambda item: (item.order, item.slug))
        return [item.to_owner_dict() for item in categories]

    @app.post("/api/owner/article-categories")
    async def owner_create_article_category(
        body: ArticleCategoryBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        slug = normalize_slug(body.slug)
        await ensure_unique_category_slug(slug)
        category = new_document(ArticleCategory)
        category.slug = slug
        category.title = body.title
        category.order = body.order
        category.protected = False
        await current_store().insert(category)
        return category.to_owner_dict()

    @app.put("/api/owner/article-categories/{category_id}")
    async def owner_update_article_category(
        category_id: PydanticObjectId,
        body: ArticleCategoryBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        category = await current_store().get(ArticleCategory, category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        slug = normalize_slug(body.slug)
        await ensure_unique_category_slug(slug, exclude_id=str(category.id))
        old_slug = category.slug
        category.slug = slug
        category.title = body.title
        category.order = body.order
        category.protected = False
        await current_store().save(category)
        if old_slug != slug:
            store = current_store()
            for article in await store.find(Article, category_slug=old_slug):
                article.category_slug = slug
                await store.save(article)
        return category.to_owner_dict()

    @app.delete("/api/owner/article-categories/{category_id}")
    async def owner_delete_article_category(
        category_id: PydanticObjectId,
        _: str = Depends(require_owner),
    ) -> dict[str, str]:
        category = await current_store().get(ArticleCategory, category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        store = current_store()
        for article in await store.find(Article, category_slug=category.slug):
            article.category_slug = ""
            await store.save(article)
        await store.delete(category)
        return {"status": "deleted"}

    @app.get("/api/owner/articles")
    async def owner_list_articles(
        _: str = Depends(require_owner),
    ) -> list[dict[str, Any]]:
        articles = await current_store().find_all(Article)
        articles.sort(key=lambda item: (item.order, item.slug))
        return [item.to_owner_dict() for item in articles]

    @app.post("/api/owner/articles")
    async def owner_create_article(
        body: ArticleBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        article = new_document(Article)
        await apply_article_body(article, body)
        await ensure_unique_article_slug(article.slug)
        await current_store().insert(article)
        return article.to_owner_dict()

    @app.put("/api/owner/articles/{article_id}")
    async def owner_update_article(
        article_id: PydanticObjectId,
        body: ArticleBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        article = await current_store().get(Article, article_id)
        if article is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        await apply_article_body(article, body)
        await ensure_unique_article_slug(article.slug, exclude_id=str(article.id))
        await current_store().save(article)
        return article.to_owner_dict()

    @app.delete("/api/owner/articles/{article_id}")
    async def owner_delete_article(
        article_id: PydanticObjectId,
        _: str = Depends(require_owner),
    ) -> dict[str, str]:
        article = await current_store().get(Article, article_id)
        if article is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        await current_store().delete(article)
        return {"status": "deleted"}

    def reject_journal_project_link(body: JournalBody) -> None:
        extra = body.model_extra or {}
        if extra.get("relatedProjectSlug"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="journals_have_no_project",
            )

    def apply_journal_body(journal: Journal, body: JournalBody) -> None:
        reject_journal_project_link(body)
        if body.status not in STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_status",
            )
        slug = body.slug.strip().lower()
        if not slug:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_slug",
            )
        journal.slug = slug
        journal.title = body.title
        journal.summary = body.summary
        journal.body = body.body
        journal.status = body.status
        journal.order = body.order
        if body.status == "published" and journal.published_at is None:
            journal.published_at = datetime.now(timezone.utc)

    async def ensure_unique_journal_slug(
        slug: str, exclude_id: str | None = None
    ) -> None:
        existing = await current_store().find_one(Journal, slug=slug)
        if existing is not None and str(existing.id) != exclude_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="slug_taken",
            )

    @app.get("/api/public/journals")
    async def public_journals(locale: str = "zh-Hant") -> list[dict[str, Any]]:
        locale = normalize_locale(locale)
        journals = await current_store().find(Journal, status="published")
        journals.sort(key=lambda item: dated(item.published_at, item.id), reverse=True)
        return [item.resolve(locale) for item in journals]

    @app.get("/api/public/journals/{slug}")
    async def public_journal(
        slug: str, locale: str = "zh-Hant"
    ) -> dict[str, Any]:
        locale = normalize_locale(locale)
        journal = await current_store().find_one(
            Journal, slug=slug, status="published"
        )
        if journal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        return journal.resolve(locale)

    @app.get("/api/owner/journals")
    async def owner_list_journals(
        _: str = Depends(require_owner),
    ) -> list[dict[str, Any]]:
        journals = await current_store().find_all(Journal)
        journals.sort(key=lambda item: (item.order, item.slug))
        return [item.to_owner_dict() for item in journals]

    @app.post("/api/owner/journals")
    async def owner_create_journal(
        body: JournalBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        journal = new_document(Journal)
        apply_journal_body(journal, body)
        await ensure_unique_journal_slug(journal.slug)
        await current_store().insert(journal)
        return journal.to_owner_dict()

    @app.put("/api/owner/journals/{journal_id}")
    async def owner_update_journal(
        journal_id: PydanticObjectId,
        body: JournalBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        journal = await current_store().get(Journal, journal_id)
        if journal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        apply_journal_body(journal, body)
        await ensure_unique_journal_slug(journal.slug, exclude_id=str(journal.id))
        await current_store().save(journal)
        return journal.to_owner_dict()

    @app.delete("/api/owner/journals/{journal_id}")
    async def owner_delete_journal(
        journal_id: PydanticObjectId,
        _: str = Depends(require_owner),
    ) -> dict[str, str]:
        journal = await current_store().get(Journal, journal_id)
        if journal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        await current_store().delete(journal)
        return {"status": "deleted"}

    def apply_about_module_body(module: AboutModule, body: AboutModuleBody) -> None:
        if body.status not in STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_status",
            )
        kind = body.kind.strip().lower() or "custom"
        if kind not in ABOUT_KINDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_kind",
            )
        slug = body.slug.strip().lower()
        if not slug:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_slug",
            )
        module.slug = slug
        module.kind = kind
        module.title = body.title
        module.body = body.body
        module.status = body.status
        module.order = body.order

    async def ensure_unique_about_slug(
        slug: str, exclude_id: str | None = None
    ) -> None:
        existing = await current_store().find_one(AboutModule, slug=slug)
        if existing is not None and str(existing.id) != exclude_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="slug_taken",
            )

    @app.get("/api/public/about")
    async def public_about(locale: str = "zh-Hant") -> list[dict[str, Any]]:
        locale = normalize_locale(locale)
        modules = await current_store().find(AboutModule, status="published")
        modules.sort(key=lambda item: (item.order, item.slug))
        return [item.resolve(locale) for item in modules]

    @app.get("/api/owner/about-modules")
    async def owner_list_about_modules(
        _: str = Depends(require_owner),
    ) -> list[dict[str, Any]]:
        modules = await current_store().find_all(AboutModule)
        modules.sort(key=lambda item: (item.order, item.slug))
        return [item.to_owner_dict() for item in modules]

    @app.post("/api/owner/about-modules")
    async def owner_create_about_module(
        body: AboutModuleBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        module = new_document(AboutModule)
        apply_about_module_body(module, body)
        await ensure_unique_about_slug(module.slug)
        await current_store().insert(module)
        return module.to_owner_dict()

    @app.put("/api/owner/about-modules/{module_id}")
    async def owner_update_about_module(
        module_id: PydanticObjectId,
        body: AboutModuleBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        module = await current_store().get(AboutModule, module_id)
        if module is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        apply_about_module_body(module, body)
        await ensure_unique_about_slug(module.slug, exclude_id=str(module.id))
        await current_store().save(module)
        return module.to_owner_dict()

    @app.delete("/api/owner/about-modules/{module_id}")
    async def owner_delete_about_module(
        module_id: PydanticObjectId,
        _: str = Depends(require_owner),
    ) -> dict[str, str]:
        module = await current_store().get(AboutModule, module_id)
        if module is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        await current_store().delete(module)
        return {"status": "deleted"}

    def public_comment_payload(comment: Comment) -> dict[str, Any]:
        return comment.to_public_dict()

    async def published_comment_target(target_type: str, slug: str):
        if target_type == "article":
            return await find_article_by_slug(slug, published_only=True)
        if target_type == "journal":
            return await current_store().find_one(
                Journal, slug=slug, status="published"
            )
        return None

    async def submit_public_comment(
        target_type: str,
        slug: str,
        body: CommentSubmitBody,
    ) -> dict[str, Any]:
        target = await published_comment_target(target_type, slug)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        name = body.displayName.strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_name",
            )
        if "@" not in body.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_email",
            )
        comment = new_document(
            Comment,
            target_type=target_type,
            target_slug=slug,
            display_name=name,
            email=body.email.strip(),
            body=body.body.strip(),
            status="pending",
        )
        await current_store().insert(comment)
        return public_comment_payload(comment)

    async def list_public_comments(target_type: str, slug: str) -> list[dict[str, Any]]:
        target = await published_comment_target(target_type, slug)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        comments = await current_store().find(
            Comment,
            target_type=target_type,
            target_slug=slug,
            status="approved",
        )
        return [item.to_public_dict() for item in comments]

    @app.post("/api/public/articles/{slug}/comments")
    async def public_submit_article_comment(
        slug: str, body: CommentSubmitBody
    ) -> dict[str, Any]:
        return await submit_public_comment("article", slug, body)

    @app.get("/api/public/articles/{slug}/comments")
    async def public_list_article_comments(slug: str) -> list[dict[str, Any]]:
        return await list_public_comments("article", slug)

    @app.post("/api/public/journals/{slug}/comments")
    async def public_submit_journal_comment(
        slug: str, body: CommentSubmitBody
    ) -> dict[str, Any]:
        return await submit_public_comment("journal", slug, body)

    @app.get("/api/public/journals/{slug}/comments")
    async def public_list_journal_comments(slug: str) -> list[dict[str, Any]]:
        return await list_public_comments("journal", slug)

    async def load_owner_comment(comment_id: PydanticObjectId) -> Comment:
        comment = await current_store().get(Comment, comment_id)
        if comment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        return comment

    @app.get("/api/owner/comments")
    async def owner_list_comments(
        _: str = Depends(require_owner),
    ) -> list[dict[str, Any]]:
        comments = await current_store().find_all(Comment)
        comments.sort(key=lambda item: str(item.id))
        return [item.to_owner_dict() for item in comments]

    @app.post("/api/owner/comments/{comment_id}/approve")
    async def owner_approve_comment(
        comment_id: PydanticObjectId,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        comment = await load_owner_comment(comment_id)
        comment.status = "approved"
        await current_store().save(comment)
        return comment.to_owner_dict()

    @app.post("/api/owner/comments/{comment_id}/reject")
    async def owner_reject_comment(
        comment_id: PydanticObjectId,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        comment = await load_owner_comment(comment_id)
        comment.status = "rejected"
        await current_store().save(comment)
        return comment.to_owner_dict()

    @app.post("/api/owner/comments/{comment_id}/reply")
    async def owner_reply_comment(
        comment_id: PydanticObjectId,
        body: OwnerReplyBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        comment = await load_owner_comment(comment_id)
        comment.owner_reply = body.body.strip()
        await current_store().save(comment)
        return comment.to_owner_dict()

    return app


app = create_app()
