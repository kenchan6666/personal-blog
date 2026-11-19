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
    return verified.cookies["portfolio_session"]


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

    owner = await client.get(
        "/api/owner/projects/secret-work/source",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert owner.status_code == 200
    assert owner.json()["private"] is True
    assert "private notes" in owner.json()["readme"]["content"]
    secret = await client.get(
        "/api/owner/projects/secret-work/source/blob",
        headers={"Authorization": f"Bearer {token}"},
        params={"path": "secret.txt"},
    )
    assert secret.status_code == 200
    assert secret.json()["content"] == "do-not-leak\n"
    assert secret.json()["private"] is True

    client.cookies.clear()
    anonymous = await client.get("/api/owner/projects/secret-work/source")
    assert anonymous.status_code == 401


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


@pytest.mark.asyncio
async def test_public_source_falls_back_to_anonymous_when_token_revoked(
    client, mailer, settings, github, app
):
    token = await _owner_token(client, mailer, settings)
    await _connect_github(client, token)
    await _published_project_with_repo(
        client, token, full_name="kenchan6666/personal-blog", slug="glass-api"
    )
    github.revoked_tokens.add("gho_test")
    client.cookies.clear()

    source = await client.get("/api/public/projects/glass-api/source")
    assert source.status_code == 200
    body = source.json()
    assert "# Glass" in body["readme"]["content"]
    assert any(item["name"] == "src" for item in body["tree"])
    assert body["languages"] == {"Python": 128, "TypeScript": 512}
    tree = await client.get(
        "/api/public/projects/glass-api/source/tree", params={"path": "src"}
    )
    assert tree.status_code == 200
    assert tree.json()["tree"][0]["path"] == "src/app.py"
    blob = await client.get(
        "/api/public/projects/glass-api/source/blob", params={"path": "src/app.py"}
    )
    assert blob.status_code == 200
    assert "print('hi')" in blob.json()["content"]
    assert ("repo", "") in github.browse_calls

    # The revoked token is remembered, and anonymous reads are cached.
    calls_before = len(github.browse_calls)
    again = await client.get("/api/public/projects/glass-api/source")
    assert again.status_code == 200
    assert len(github.browse_calls) == calls_before
    assert await app.state.redis.get("github:owner_token_invalid") == "1"
    assert await app.state.redis.ttl(
        "github:anon:kenchan6666/personal-blog:readme:master:"
    ) > 120


@pytest.mark.asyncio
async def test_public_source_reads_anonymously_without_any_token(
    client, mailer, settings, github, app
):
    token = await _owner_token(client, mailer, settings)
    await _connect_github(client, token)
    await _published_project_with_repo(
        client, token, full_name="kenchan6666/personal-blog", slug="glass-api"
    )
    await app.state.redis.delete("github:owner_token")
    source = await client.get("/api/public/projects/glass-api/source")
    assert source.status_code == 200
    assert "# Glass" in source.json()["readme"]["content"]
    assert all(token == "" for _, token in github.browse_calls[-4:])


@pytest.mark.asyncio
async def test_anonymous_fallback_never_exposes_private_repo(
    client, mailer, settings, github, app
):
    token = await _owner_token(client, mailer, settings)
    await _connect_github(client, token)
    # A private repo must stay hidden even when reads go anonymous.
    github.extra_repos.append(
        {
            "fullName": "kenchan6666/hidden-lab",
            "owner": "kenchan6666",
            "name": "hidden-lab",
            "private": True,
            "htmlUrl": "https://github.com/kenchan6666/hidden-lab",
            "defaultBranch": "main",
            "description": "",
        }
    )
    github.extra_files["kenchan6666/hidden-lab"] = {"main": {"README.md": "# nope\n"}}
    project_id = await _published_project_with_repo(
        client, token, full_name="kenchan6666/hidden-lab", slug="hidden"
    )
    github.revoked_tokens.add("gho_test")
    for path in ("source", "source/tree", "source/blob?path=README.md"):
        response = await client.get(f"/api/public/projects/hidden/{path}")
        assert response.status_code == 404, path
    assert project_id


@pytest.mark.asyncio
async def test_owner_source_reports_disconnected_when_token_revoked(
    client, mailer, settings, github
):
    token = await _owner_token(client, mailer, settings)
    await _connect_github(client, token)
    await _published_project_with_repo(
        client, token, full_name="kenchan6666/personal-blog", slug="glass-api"
    )
    github.revoked_tokens.add("gho_test")
    response = await client.get(
        "/api/owner/projects/glass-api/source",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "github_not_connected"


@pytest.mark.asyncio
async def test_reconnect_clears_revoked_marker(client, mailer, settings, github, app):
    token = await _owner_token(client, mailer, settings)
    await _connect_github(client, token)
    await app.state.redis.set("github:owner_token_invalid", "1")
    await _connect_github(client, token)
    assert await app.state.redis.get("github:owner_token_invalid") is None


@pytest.mark.asyncio
async def test_admin_account_reports_disconnected_when_token_revoked(
    client, mailer, settings, github
):
    token = await _owner_token(client, mailer, settings)
    await _connect_github(client, token)
    headers = {"Authorization": f"Bearer {token}"}
    assert (await client.get("/api/owner/github/account", headers=headers)).json()[
        "connected"
    ] is True
    github.revoked_tokens.add("gho_test")
    account = await client.get("/api/owner/github/account", headers=headers)
    assert account.json() == {"connected": False}
