from __future__ import annotations

import json
import secrets
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from beanie import PydanticObjectId, init_beanie
from fastapi import Depends, FastAPI, File, Header, HTTPException, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, Field
from redis.asyncio import Redis

from app.auth import AuthService
from app.avatar import (
    ensure_avatar_dir,
    media_type_for_filename,
    resolve_avatar_path,
    save_avatar_file,
)
from app.config import Settings
from app.github import GitHubBrowseError, GitHubClient, GitHubOAuthError, HttpGitHub
from app.mailer import ConsoleMailer, Mailer, SmtpMailer
from app.models import (
    STATUSES,
    Article,
    Journal,
    LinkItem,
    Project,
    SiteProfile,
    SourceRepo,
    empty_localized,
)


async def check_mongo(mongo: AsyncIOMotorClient) -> bool:
    try:
        await mongo.admin.command("ping")
        return True
    except Exception:
        return False


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


class JournalBody(BaseModel):
    model_config = ConfigDict(extra="allow")
    slug: str = Field(min_length=1, max_length=80)
    title: dict[str, str] = Field(default_factory=empty_localized)
    summary: dict[str, str] = Field(default_factory=empty_localized)
    body: dict[str, str] = Field(default_factory=empty_localized)
    status: str = "draft"
    order: int = 0


async def get_or_create_site() -> SiteProfile:
    site = await SiteProfile.find_one()
    if site is None:
        site = SiteProfile()
        await site.insert()
    return site


GITHUB_STATE_TTL = 600
GITHUB_TOKEN_KEY = "github:owner_token"


def create_app(
    settings: Settings | None = None,
    mailer: Mailer | None = None,
    github: GitHubClient | None = None,
) -> FastAPI:
    settings = settings or Settings()
    if mailer is not None:
        resolved_mailer: Mailer = mailer
    elif settings.mail_backend.lower() == "console":
        resolved_mailer = ConsoleMailer()
    else:
        resolved_mailer = SmtpMailer(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            from_addr=settings.smtp_from,
        )
    resolved_github: GitHubClient = github or HttpGitHub(
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        callback_url=settings.github_oauth_callback_url,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        mongo = AsyncIOMotorClient(settings.mongo_uri)
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        await init_beanie(
            database=mongo[settings.mongo_db],
            document_models=[SiteProfile, Project, Article, Journal],
        )
        await redis.ping()
        avatar_dir = ensure_avatar_dir(settings.avatar_dir)
        app.state.mongo = mongo
        app.state.redis = redis
        app.state.settings = settings
        app.state.mailer = resolved_mailer
        app.state.github = resolved_github
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
        try:
            yield
        finally:
            await redis.aclose()
            mongo.close()

    app = FastAPI(title="Portfolio API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.mailer = resolved_mailer

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
        mongo: AsyncIOMotorClient = app.state.mongo
        redis: Redis = app.state.redis
        mongo_up = await check_mongo(mongo)
        redis_up = await check_redis(redis)
        payload = {
            "status": "ok" if mongo_up and redis_up else "degraded",
            "mongo": "up" if mongo_up else "down",
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

    @app.get("/api/public/site")
    async def public_site(locale: str = "zh-Hant") -> dict[str, Any]:
        if locale not in ("zh-Hant", "en"):
            locale = "zh-Hant"
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
        await site.save()
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
        await site.save()
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
        return FileResponse(path, media_type=media_type)

    def normalize_locale(locale: str) -> str:
        return locale if locale in ("zh-Hant", "en") else "zh-Hant"

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
        existing = await Project.find_one(Project.slug == slug)
        if existing is not None and str(existing.id) != exclude_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="slug_taken",
            )

    @app.get("/api/public/projects")
    async def public_projects(locale: str = "zh-Hant") -> list[dict[str, Any]]:
        locale = normalize_locale(locale)
        projects = await Project.find(Project.status == "published").to_list()
        projects.sort(key=lambda item: (item.order, item.slug))
        return [item.resolve(locale) for item in projects]

    @app.get("/api/public/projects/{slug}")
    async def public_project(
        slug: str, locale: str = "zh-Hant"
    ) -> dict[str, Any]:
        locale = normalize_locale(locale)
        project = await Project.find_one(
            Project.slug == slug,
            Project.status == "published",
        )
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        return project.resolve(locale)

    GITHUB_CACHE_TTL = 120

    async def published_browsable_source(slug: str) -> tuple[SourceRepo, str]:
        project = await Project.find_one(
            Project.slug == slug,
            Project.status == "published",
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
        projects = await Project.find_all().to_list()
        projects.sort(key=lambda item: (item.order, item.slug))
        return [item.to_owner_dict() for item in projects]

    @app.post("/api/owner/projects")
    async def owner_create_project(
        body: ProjectBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        project = Project()
        apply_project_body(project, body)
        await ensure_unique_slug(project.slug)
        await project.insert()
        return project.to_owner_dict()

    @app.put("/api/owner/projects/{project_id}")
    async def owner_update_project(
        project_id: PydanticObjectId,
        body: ProjectBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        project = await Project.get(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        apply_project_body(project, body)
        await ensure_unique_slug(project.slug, exclude_id=str(project.id))
        await project.save()
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
        project = await Project.get(project_id)
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
        await project.save()
        return project.to_owner_dict()

    def apply_article_body(article: Article, body: ArticleBody) -> None:
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
        article.slug = slug
        article.title = body.title
        article.summary = body.summary
        article.body = body.body
        article.status = body.status
        article.order = body.order
        article.related_project_slug = body.relatedProjectSlug.strip().lower()

    async def ensure_unique_article_slug(
        slug: str, exclude_id: str | None = None
    ) -> None:
        existing = await Article.find_one(Article.slug == slug)
        if existing is not None and str(existing.id) != exclude_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="slug_taken",
            )

    async def public_article_payload(article: Article, locale: str) -> dict[str, Any]:
        payload = article.resolve(locale)
        related_slug = article.related_project_slug
        if related_slug:
            project = await Project.find_one(
                Project.slug == related_slug,
                Project.status == "published",
            )
            if project is not None:
                payload["relatedProject"] = {
                    "slug": project.slug,
                    "title": project.resolve(locale)["title"],
                }
        return payload

    @app.get("/api/public/articles")
    async def public_articles(locale: str = "zh-Hant") -> list[dict[str, Any]]:
        locale = normalize_locale(locale)
        articles = await Article.find(Article.status == "published").to_list()
        articles.sort(key=lambda item: (item.order, item.slug))
        return [await public_article_payload(item, locale) for item in articles]

    @app.get("/api/public/articles/{slug}")
    async def public_article(
        slug: str, locale: str = "zh-Hant"
    ) -> dict[str, Any]:
        locale = normalize_locale(locale)
        article = await Article.find_one(
            Article.slug == slug,
            Article.status == "published",
        )
        if article is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        return await public_article_payload(article, locale)

    @app.get("/api/owner/articles")
    async def owner_list_articles(
        _: str = Depends(require_owner),
    ) -> list[dict[str, Any]]:
        articles = await Article.find_all().to_list()
        articles.sort(key=lambda item: (item.order, item.slug))
        return [item.to_owner_dict() for item in articles]

    @app.post("/api/owner/articles")
    async def owner_create_article(
        body: ArticleBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        article = Article()
        apply_article_body(article, body)
        await ensure_unique_article_slug(article.slug)
        await article.insert()
        return article.to_owner_dict()

    @app.put("/api/owner/articles/{article_id}")
    async def owner_update_article(
        article_id: PydanticObjectId,
        body: ArticleBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        article = await Article.get(article_id)
        if article is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        apply_article_body(article, body)
        await ensure_unique_article_slug(article.slug, exclude_id=str(article.id))
        await article.save()
        return article.to_owner_dict()

    @app.delete("/api/owner/articles/{article_id}")
    async def owner_delete_article(
        article_id: PydanticObjectId,
        _: str = Depends(require_owner),
    ) -> dict[str, str]:
        article = await Article.get(article_id)
        if article is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        await article.delete()
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

    async def ensure_unique_journal_slug(
        slug: str, exclude_id: str | None = None
    ) -> None:
        existing = await Journal.find_one(Journal.slug == slug)
        if existing is not None and str(existing.id) != exclude_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="slug_taken",
            )

    @app.get("/api/public/journals")
    async def public_journals(locale: str = "zh-Hant") -> list[dict[str, Any]]:
        locale = normalize_locale(locale)
        journals = await Journal.find(Journal.status == "published").to_list()
        journals.sort(key=lambda item: (item.order, item.slug))
        return [item.resolve(locale) for item in journals]

    @app.get("/api/public/journals/{slug}")
    async def public_journal(
        slug: str, locale: str = "zh-Hant"
    ) -> dict[str, Any]:
        locale = normalize_locale(locale)
        journal = await Journal.find_one(
            Journal.slug == slug,
            Journal.status == "published",
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
        journals = await Journal.find_all().to_list()
        journals.sort(key=lambda item: (item.order, item.slug))
        return [item.to_owner_dict() for item in journals]

    @app.post("/api/owner/journals")
    async def owner_create_journal(
        body: JournalBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        journal = Journal()
        apply_journal_body(journal, body)
        await ensure_unique_journal_slug(journal.slug)
        await journal.insert()
        return journal.to_owner_dict()

    @app.put("/api/owner/journals/{journal_id}")
    async def owner_update_journal(
        journal_id: PydanticObjectId,
        body: JournalBody,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        journal = await Journal.get(journal_id)
        if journal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        apply_journal_body(journal, body)
        await ensure_unique_journal_slug(journal.slug, exclude_id=str(journal.id))
        await journal.save()
        return journal.to_owner_dict()

    @app.delete("/api/owner/journals/{journal_id}")
    async def owner_delete_journal(
        journal_id: PydanticObjectId,
        _: str = Depends(require_owner),
    ) -> dict[str, str]:
        journal = await Journal.get(journal_id)
        if journal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="not_found",
            )
        await journal.delete()
        return {"status": "deleted"}

    return app


app = create_app()
