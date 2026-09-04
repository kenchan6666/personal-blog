from __future__ import annotations

import asyncio
import os

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient
from redis.asyncio import Redis

from app.config import Settings
from app.github import RecordingGitHub
from app.mailer import RecordingMailer
from app.main import close_mongo, create_app
from app.memory_redis import MemoryRedis
from app.translate import ScriptedTranslator


async def _reachable_redis(url: str) -> Redis | None:
    client = Redis.from_url(url, decode_responses=True)
    try:
        await asyncio.wait_for(client.ping(), timeout=0.4)
    except Exception:
        await client.aclose()
        return None
    return client


async def _mongo_reachable(uri: str) -> bool:
    if not uri.strip():
        return False
    client = AsyncMongoClient(uri, serverSelectionTimeoutMS=400)
    try:
        await client.admin.command("ping")
    except Exception:
        return False
    finally:
        await close_mongo(client)
    return True


@pytest.fixture
def settings(tmp_path) -> Settings:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27019")
    return Settings(
        mongo_uri=mongo_uri,
        mongo_db=os.getenv("MONGO_DB", "portfolio_test"),
        redis_url=os.getenv("REDIS_URL", "redis://127.0.0.1:6380/15"),
        owner_email="ynchanhk@gmail.com",
        otp_ttl_seconds=300,
        otp_rate_limit=3,
        otp_rate_window_seconds=600,
        session_ttl_seconds=3600,
        mail_backend="console",
        smtp_host="localhost",
        smtp_port=1025,
        smtp_user="ynchanhk@gmail.com",
        smtp_password="test",
        smtp_from="ynchanhk@gmail.com",
        avatar_dir=str(tmp_path / "avatars"),
        resume_dir=str(tmp_path / "resumes"),
        local_data_dir=str(tmp_path / "local"),
        github_client_id="test-client",
        github_client_secret="test-secret",
        github_oauth_callback_url="http://test/api/auth/github/callback",
        github_oauth_success_url="http://localhost:3000/zh-Hant/admin",
        cors_origins=(
            "http://localhost:3000,http://127.0.0.1:3000"
        ),
        agent_service_token="",
    )


@pytest_asyncio.fixture
async def mailer() -> RecordingMailer:
    return RecordingMailer()


@pytest.fixture
def github() -> RecordingGitHub:
    return RecordingGitHub()


@pytest.fixture
def translator() -> ScriptedTranslator:
    return ScriptedTranslator()


@pytest_asyncio.fixture
async def app(
    settings: Settings,
    mailer: RecordingMailer,
    github: RecordingGitHub,
    translator: ScriptedTranslator,
):
    redis = await _reachable_redis(settings.redis_url)
    if redis is None:
        redis = MemoryRedis()
    if not await _mongo_reachable(settings.mongo_uri):
        settings.mongo_uri = ""
    application = create_app(
        settings,
        mailer=mailer,
        github=github,
        translator=translator,
        redis=redis,
    )
    async with LifespanManager(application):
        await application.state.redis.flushdb()
        await application.state.store.delete_all()
        yield application


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
