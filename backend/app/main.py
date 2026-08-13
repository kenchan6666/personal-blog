from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from beanie import init_beanie
from fastapi import Depends, FastAPI, File, Header, HTTPException, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.auth import AuthService
from app.avatar import (
    ensure_avatar_dir,
    media_type_for_filename,
    resolve_avatar_path,
    save_avatar_file,
)
from app.config import Settings
from app.mailer import ConsoleMailer, Mailer, SmtpMailer
from app.models import LinkItem, SiteProfile, empty_localized


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


async def get_or_create_site() -> SiteProfile:
    site = await SiteProfile.find_one()
    if site is None:
        site = SiteProfile()
        await site.insert()
    return site


def create_app(
    settings: Settings | None = None,
    mailer: Mailer | None = None,
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

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        mongo = AsyncIOMotorClient(settings.mongo_uri)
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        await init_beanie(
            database=mongo[settings.mongo_db],
            document_models=[SiteProfile],
        )
        await redis.ping()
        avatar_dir = ensure_avatar_dir(settings.avatar_dir)
        app.state.mongo = mongo
        app.state.redis = redis
        app.state.settings = settings
        app.state.mailer = resolved_mailer
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

    return app


app = create_app()
