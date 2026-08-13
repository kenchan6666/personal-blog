from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from beanie import init_beanie
from fastapi import Depends, FastAPI, Header, Response, status
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.auth import AuthService
from app.config import Settings
from app.mailer import Mailer, SmtpMailer


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


def create_app(
    settings: Settings | None = None,
    mailer: Mailer | None = None,
) -> FastAPI:
    settings = settings or Settings()
    resolved_mailer: Mailer = mailer or SmtpMailer(
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
        await init_beanie(database=mongo[settings.mongo_db], document_models=[])
        await redis.ping()
        app.state.mongo = mongo
        app.state.redis = redis
        app.state.settings = settings
        app.state.mailer = resolved_mailer
        app.state.auth = AuthService(
            redis=redis,
            settings=settings,
            mailer=resolved_mailer,
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
        await auth.request_otp(body.email)
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

    return app


app = create_app()
