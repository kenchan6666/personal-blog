"""
Seam: Portfolio HTTP API.
Ticket: #10 Public SourceRepo browser (depth B, no private leak).
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest


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


async def _connect_github(client, token: str) -> None:
    start = await client.get(
        "/api/owner/github/oauth/start",
        headers={"Authorization": f"Bearer {token}"},
    )
    state = parse_qs(urlparse(start.json()["authorizationUrl"]).query)["state"][0]
    await client.get(
        "/api/auth/github/callback",
        params={"code": "ok", "state": state},
        follow_redirects=False,
    )


async def _published_project_with_repo(client, token: str, *, full_name: str, slug: str):
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        "/api/owner/projects",
        json={
            "slug": slug,
            "title": {"zh-Hant": slug, "en": slug},
            "summary": {"zh-Hant": "", "en": ""},
            "body": {"zh-Hant": "", "en": ""},
            "status": "published",
            "order": 1,
        },
        headers=headers,
    )
    project_id = created.json()["id"]
    await client.put(
        f"/api/owner/projects/{project_id}/source-repo",
        json={"fullName": full_name},
        headers=headers,
    )
    return project_id


@pytest.mark.asyncio
async def test_public_source_readme_branches_tree_and_blob(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    await _connect_github(client, token)
    await _published_project_with_repo(
        client,
        token,
        full_name="kenchan6666/personal-blog",
        slug="glass-api",
    )

    source = await client.get("/api/public/projects/glass-api/source")
    assert source.status_code == 200
    body = source.json()
    assert body["defaultBranch"] == "master"
    assert body["branches"] == ["feature", "master"]
    assert "# Glass" in body["readme"]["content"]
    names = [item["name"] for item in body["tree"]]
    assert "README.md" in names
    assert "src" in names

    feature = await client.get(
        "/api/public/projects/glass-api/source",
        params={"ref": "feature"},
    )
    assert feature.json()["readme"]["content"].startswith("# Feature")

    nested = await client.get(
        "/api/public/projects/glass-api/source/tree",
        params={"ref": "master", "path": "src"},
    )
    assert nested.status_code == 200
    assert [item["path"] for item in nested.json()["tree"]] == ["src/app.py"]

    blob = await client.get(
        "/api/public/projects/glass-api/source/blob",
        params={"ref": "master", "path": "src/app.py"},
    )
    assert blob.status_code == 200
    assert blob.json()["content"] == "print('hi')\n"
    assert blob.json()["path"] == "src/app.py"


@pytest.mark.asyncio
async def test_private_source_repo_hides_tree_and_blob_from_visitors(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    await _connect_github(client, token)
    await _published_project_with_repo(
        client,
        token,
        full_name="kenchan6666/secret-lab",
        slug="secret-work",
    )

    source = await client.get("/api/public/projects/secret-work/source")
    assert source.status_code == 404
    tree = await client.get("/api/public/projects/secret-work/source/tree")
    assert tree.status_code == 404
    blob = await client.get(
        "/api/public/projects/secret-work/source/blob",
        params={"path": "secret.txt"},
    )
    assert blob.status_code == 404


@pytest.mark.asyncio
async def test_draft_project_source_is_not_browsable(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    await _connect_github(client, token)
    created = await client.post(
        "/api/owner/projects",
        json={
            "slug": "wip",
            "title": {"zh-Hant": "wip", "en": "wip"},
            "summary": {"zh-Hant": "", "en": ""},
            "body": {"zh-Hant": "", "en": ""},
            "status": "draft",
            "order": 1,
        },
        headers=headers,
    )
    await client.put(
        f"/api/owner/projects/{created.json()['id']}/source-repo",
        json={"fullName": "kenchan6666/personal-blog"},
        headers=headers,
    )

    source = await client.get("/api/public/projects/wip/source")
    assert source.status_code == 404


@pytest.mark.asyncio
async def test_missing_readme_still_returns_source_overview(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    await _connect_github(client, token)
    await _published_project_with_repo(
        client,
        token,
        full_name="kenchan6666/empty-box",
        slug="empty-box",
    )

    source = await client.get("/api/public/projects/empty-box/source")
    assert source.status_code == 200
    body = source.json()
    assert body["readme"] == {"path": "", "content": ""}
    assert [item["name"] for item in body["tree"]] == ["src"]


@pytest.mark.asyncio
async def test_public_source_allows_127_browser_origin(client):
    response = await client.options(
        "/api/public/projects",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin")
        == "http://127.0.0.1:3000"
    )
