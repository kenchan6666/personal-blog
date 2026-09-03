"""
Seam: Portfolio HTTP API — JSON files when MONGO_URI is empty.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.github import RecordingGitHub
from app.mailer import RecordingMailer
from app.main import create_app
from app.memory_redis import MemoryRedis


def _local_settings(tmp_path: Path) -> Settings:
    return Settings(
        mongo_uri="",
        mongo_db="portfolio_test",
        redis_url=os.getenv("REDIS_URL", "redis://127.0.0.1:6380/15"),
        local_data_dir=str(tmp_path / "local"),
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
        github_client_id="test-client",
        github_client_secret="test-secret",
        github_oauth_callback_url="http://test/api/auth/github/callback",
        github_oauth_success_url="http://localhost:3000/zh-Hant/admin",
        cors_origins="http://localhost:3000",
    )


async def _owner_token(client: AsyncClient, mailer: RecordingMailer, settings: Settings) -> str:
    await client.post(
        "/api/auth/otp/request",
        json={"email": settings.owner_email},
    )
    code = mailer.sent[-1]["code"]
    verified = await client.post(
        "/api/auth/otp/verify",
        json={"email": settings.owner_email, "code": code},
    )
    return verified.json()["session_token"]


@pytest.mark.asyncio
async def test_health_reports_local_store_when_mongo_uri_is_empty(tmp_path):
    settings = _local_settings(tmp_path)
    mailer = RecordingMailer()
    application = create_app(
        settings,
        mailer=mailer,
        github=RecordingGitHub(),
        redis=MemoryRedis(),
    )
    async with LifespanManager(application):
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mongo"] == "local"
    assert body["redis"] == "up"


@pytest.mark.asyncio
async def test_empty_mongo_uri_persists_site_and_project_to_json(tmp_path):
    settings = _local_settings(tmp_path)
    mailer = RecordingMailer()
    data_dir = Path(settings.local_data_dir)

    application = create_app(
        settings,
        mailer=mailer,
        github=RecordingGitHub(),
        redis=MemoryRedis(),
    )
    async with LifespanManager(application):
        await application.state.redis.flushdb()
        await application.state.store.delete_all()
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            token = await _owner_token(client, mailer, settings)
            headers = {"Authorization": f"Bearer {token}"}
            saved = await client.put(
                "/api/owner/site",
                json={
                    "brand": {"zh-Hant": "本地站", "en": "Local site"},
                    "heroHeadline": {"zh-Hant": "標題", "en": ""},
                },
                headers=headers,
            )
            created = await client.post(
                "/api/owner/projects",
                json={
                    "slug": "local-demo",
                    "title": {"zh-Hant": "本地項目", "en": "Local project"},
                    "status": "published",
                },
                headers=headers,
            )

    assert saved.status_code == 200
    assert created.status_code == 200
    site_rows = json.loads((data_dir / "site_profile.json").read_text(encoding="utf-8"))
    project_rows = json.loads((data_dir / "projects.json").read_text(encoding="utf-8"))
    assert site_rows[0]["brand"]["zh-Hant"] == "本地站"
    assert project_rows[0]["slug"] == "local-demo"

    restarted = create_app(
        settings,
        mailer=RecordingMailer(),
        github=RecordingGitHub(),
        redis=MemoryRedis(),
    )
    async with LifespanManager(restarted):
        transport = ASGITransport(app=restarted)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            site = await client.get("/api/public/site", params={"locale": "zh-Hant"})
            projects = await client.get(
                "/api/public/projects", params={"locale": "zh-Hant"}
            )

    assert site.status_code == 200
    assert site.json()["brand"] == "本地站"
    assert [item["slug"] for item in projects.json()] == ["local-demo"]
