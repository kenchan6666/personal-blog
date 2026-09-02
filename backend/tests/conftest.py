from __future__ import annotations

import os

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.github import RecordingGitHub
from app.mailer import RecordingMailer
from app.main import create_app


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        mongo_uri=os.getenv("MONGO_URI", "mongodb://127.0.0.1:27019"),
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
        local_data_dir=str(tmp_path / "local"),
        github_client_id="test-client",
        github_client_secret="test-secret",
        github_oauth_callback_url="http://test/api/auth/github/callback",
        github_oauth_success_url="http://localhost:3000/zh-Hant/admin",
        cors_origins=(
            "http://localhost:3000,http://127.0.0.1:3000"
        ),
    )


@pytest_asyncio.fixture
async def mailer() -> RecordingMailer:
    return RecordingMailer()


@pytest.fixture
def github() -> RecordingGitHub:
    return RecordingGitHub()


@pytest_asyncio.fixture
async def app(settings: Settings, mailer: RecordingMailer, github: RecordingGitHub):
    application = create_app(settings, mailer=mailer, github=github)
    async with LifespanManager(application):
        await application.state.redis.flushdb()
        await application.state.store.delete_all()
        yield application


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
