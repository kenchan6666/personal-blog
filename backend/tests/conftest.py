from __future__ import annotations

import os

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.mailer import RecordingMailer
from app.main import create_app
from app.models import SiteProfile


@pytest.fixture(scope="session")
def settings() -> Settings:
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
    )


@pytest_asyncio.fixture
async def mailer() -> RecordingMailer:
    return RecordingMailer()


@pytest_asyncio.fixture
async def app(settings: Settings, mailer: RecordingMailer):
    application = create_app(settings, mailer=mailer)
    async with LifespanManager(application):
        await application.state.redis.flushdb()
        await SiteProfile.delete_all()
        yield application


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
