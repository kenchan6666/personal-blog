from __future__ import annotations

import os

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(
        mongo_uri=os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017"),
        mongo_db=os.getenv("MONGO_DB", "portfolio_test"),
        redis_url=os.getenv("REDIS_URL", "redis://127.0.0.1:6380/15"),
    )


@pytest_asyncio.fixture
async def app(settings: Settings):
    application = create_app(settings)
    async with LifespanManager(application):
        yield application


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
