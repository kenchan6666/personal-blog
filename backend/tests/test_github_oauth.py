"""
Seam: Portfolio HTTP API.
Ticket: #9 GitHub OAuth and attach SourceRepo to a Project.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from app.github import RecordingGitHub


async def _owner_token(client, mailer, settings) -> str:
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


def _project_payload(**overrides):
    body = {
        "slug": "glass-api",
        "title": {"zh-Hant": "玻璃 API", "en": "Glass API"},
        "summary": {"zh-Hant": "", "en": ""},
        "body": {"zh-Hant": "", "en": ""},
        "status": "published",
        "order": 1,
    }
    body.update(overrides)
    return body


async def _connect_github(client, token: str, *, code: str = "ok") -> None:
    start = await client.get(
        "/api/owner/github/oauth/start",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert start.status_code == 200
    state = parse_qs(urlparse(start.json()["authorizationUrl"]).query)["state"][0]
    await client.get(
        "/api/auth/github/callback",
        params={"code": code, "state": state},
        follow_redirects=False,
    )


@pytest.mark.asyncio
async def test_oauth_start_without_client_id_fails_closed(
    client, app, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    app.state.settings.github_client_id = ""
    response = await client.get(
        "/api/owner/github/oauth/start",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "github_not_configured"
    assert "authorizationUrl" not in response.json()


@pytest.mark.asyncio
async def test_unauthenticated_cannot_start_github_oauth(client):
    response = await client.get("/api/owner/github/oauth/start")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_owner_oauth_lists_repos_without_leaking_token(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    start = await client.get("/api/owner/github/oauth/start", headers=headers)
    assert start.status_code == 200
    url = start.json()["authorizationUrl"]
    assert "github.com/login/oauth/authorize" in url
    state = parse_qs(urlparse(url).query)["state"][0]

    callback = await client.get(
        "/api/auth/github/callback",
        params={"code": "ok", "state": state},
        follow_redirects=False,
    )
    assert callback.status_code in (302, 303, 307)
    location = callback.headers["location"]
    assert "access_token" not in location
    assert "gho_" not in location
    assert "tab=github" in location
    assert "github=connected" in location

    repos = await client.get("/api/owner/github/repos", headers=headers)
    assert repos.status_code == 200
    names = [item["fullName"] for item in repos.json()]
    assert names == [
        "kenchan6666/personal-blog",
        "kenchan6666/secret-lab",
        "kenchan6666/empty-box",
    ]
    assert repos.json()[1]["private"] is True
    assert repos.json()[0]["description"] == "Job-seeking portfolio"
    assert "accessToken" not in repos.json()[0]


@pytest.mark.asyncio
async def test_oauth_failure_fails_closed(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    await _connect_github(client, token, code="bad")

    repos = await client.get("/api/owner/github/repos", headers=headers)
    assert repos.status_code == 409


@pytest.mark.asyncio
async def test_owner_attaches_source_repo_public_inventory_stays_projects_only(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    await _connect_github(client, token)

    created = await client.post(
        "/api/owner/projects",
        json=_project_payload(),
        headers=headers,
    )
    project_id = created.json()["id"]

    attached = await client.put(
        f"/api/owner/projects/{project_id}/source-repo",
        json={"fullName": "kenchan6666/personal-blog"},
        headers=headers,
    )
    assert attached.status_code == 200
    repo = attached.json()["sourceRepo"]
    assert repo["fullName"] == "kenchan6666/personal-blog"
    assert repo["private"] is False
    assert repo["htmlUrl"] == "https://github.com/kenchan6666/personal-blog"

    public = await client.get(
        "/api/public/projects", params={"locale": "zh-Hant"}
    )
    assert public.status_code == 200
    slugs = [item["slug"] for item in public.json()]
    assert slugs == ["glass-api"]
    assert "secret-lab" not in slugs
    assert public.json()[0]["sourceRepo"]["fullName"] == "kenchan6666/personal-blog"
    assert "accessToken" not in str(public.json())

    missing = await client.get("/api/public/github/repos")
    assert missing.status_code == 404
