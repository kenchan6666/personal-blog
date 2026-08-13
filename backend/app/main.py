from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from beanie import init_beanie
from fastapi import FastAPI, Response, status
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis

from app.config import Settings


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


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        mongo = AsyncIOMotorClient(settings.mongo_uri)
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        await init_beanie(database=mongo[settings.mongo_db], document_models=[])
        app.state.mongo = mongo
        app.state.redis = redis
        app.state.settings = settings
        try:
            yield
        finally:
            await redis.aclose()
            mongo.close()

    app = FastAPI(title="Portfolio API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings

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

    return app


app = create_app()
