"""
Seam: Portfolio HTTP API.
Ticket: #11 Moderated Comments on Journal and Article.
"""

from __future__ import annotations

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


async def _publish_article(client, token: str) -> None:
    await client.post(
        "/api/owner/articles",
        json={
            "slug": "craft-notes",
            "title": {"zh-Hant": "工藝筆記", "en": "Craft notes"},
            "summary": {"zh-Hant": "", "en": ""},
            "body": {"zh-Hant": "正文", "en": "Body"},
            "status": "published",
            "order": 1,
            "relatedProjectSlug": "",
        },
        headers={"Authorization": f"Bearer {token}"},
    )


async def _publish_journal(client, token: str) -> None:
    await client.post(
        "/api/owner/journals",
        json={
            "slug": "monday-notes",
            "title": {"zh-Hant": "週一", "en": "Monday"},
            "summary": {"zh-Hant": "", "en": ""},
            "body": {"zh-Hant": "日誌", "en": "Journal"},
            "status": "published",
            "order": 1,
        },
        headers={"Authorization": f"Bearer {token}"},
    )


def _comment_payload(**overrides):
    body = {
        "displayName": "Ada",
        "email": "ada@example.com",
        "body": "Loved this write-up.",
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio
async def test_visitor_comment_on_article_is_pending_and_hides_email(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    await _publish_article(client, token)

    submitted = await client.post(
        "/api/public/articles/craft-notes/comments",
        json=_comment_payload(),
    )
    assert submitted.status_code == 200
    payload = submitted.json()
    assert payload["status"] == "pending"
    assert "email" not in payload
    assert payload["displayName"] == "Ada"

    public = await client.get("/api/public/articles/craft-notes/comments")
    assert public.status_code == 200
    assert public.json() == []


@pytest.mark.asyncio
async def test_owner_can_approve_reject_and_reply(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    await _publish_article(client, token)
    await _publish_journal(client, token)

    first = await client.post(
        "/api/public/articles/craft-notes/comments",
        json=_comment_payload(),
    )
    second = await client.post(
        "/api/public/journals/monday-notes/comments",
        json=_comment_payload(displayName="Lin", body="Nice day."),
    )
    first_id = first.json()["id"]
    second_id = second.json()["id"]

    inbox = await client.get("/api/owner/comments", headers=headers)
    assert inbox.status_code == 200
    emails = {item["email"] for item in inbox.json()}
    assert "ada@example.com" in emails

    approved = await client.post(
        f"/api/owner/comments/{first_id}/approve",
        headers=headers,
    )
    assert approved.status_code == 200
    replied = await client.post(
        f"/api/owner/comments/{first_id}/reply",
        json={"body": "Thanks for reading."},
        headers=headers,
    )
    assert replied.status_code == 200
    rejected = await client.post(
        f"/api/owner/comments/{second_id}/reject",
        headers=headers,
    )
    assert rejected.status_code == 200

    article_comments = await client.get(
        "/api/public/articles/craft-notes/comments"
    )
    assert article_comments.status_code == 200
    visible = article_comments.json()
    assert len(visible) == 1
    assert visible[0]["displayName"] == "Ada"
    assert visible[0]["ownerReply"] == "Thanks for reading."
    assert "email" not in visible[0]
    assert "ada@example.com" not in str(visible)

    journal_comments = await client.get(
        "/api/public/journals/monday-notes/comments"
    )
    assert journal_comments.json() == []


@pytest.mark.asyncio
async def test_projects_do_not_accept_comments(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    await client.post(
        "/api/owner/projects",
        json={
            "slug": "glass-api",
            "title": {"zh-Hant": "玻璃", "en": "Glass"},
            "summary": {"zh-Hant": "", "en": ""},
            "body": {"zh-Hant": "", "en": ""},
            "status": "published",
            "order": 1,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    posted = await client.post(
        "/api/public/projects/glass-api/comments",
        json=_comment_payload(),
    )
    assert posted.status_code == 404

    listed = await client.get("/api/public/projects/glass-api/comments")
    assert listed.status_code == 404


@pytest.mark.asyncio
async def test_owner_can_delete_comment(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    await _publish_article(client, token)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        "/api/public/articles/craft-notes/comments", json=_comment_payload()
    )
    comment_id = created.json()["id"]
    await client.post(f"/api/owner/comments/{comment_id}/approve", headers=headers)
    assert len((await client.get("/api/public/articles/craft-notes/comments")).json()) == 1

    deleted = await client.delete(f"/api/owner/comments/{comment_id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json() == {"status": "deleted"}
    owner_list = await client.get("/api/owner/comments", headers=headers)
    assert all(item["id"] != comment_id for item in owner_list.json())
    assert (await client.get("/api/public/articles/craft-notes/comments")).json() == []
    missing = await client.delete(f"/api/owner/comments/{comment_id}", headers=headers)
    assert missing.status_code == 404

    client.cookies.clear()
    created = await client.post(
        "/api/public/articles/craft-notes/comments", json=_comment_payload()
    )
    anon = await client.delete(f"/api/owner/comments/{created.json()['id']}")
    assert anon.status_code == 401


@pytest.mark.asyncio
async def test_comment_submission_is_rate_limited_per_ip(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    await _publish_article(client, token)
    client.cookies.clear()
    url = "/api/public/articles/craft-notes/comments"
    alice = {"X-Real-IP": "203.0.113.7"}
    for _ in range(settings.comment_rate_minute):
        ok = await client.post(url, json=_comment_payload(), headers=alice)
        assert ok.status_code == 200
    blocked = await client.post(url, json=_comment_payload(), headers=alice)
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "comment_rate_limited"
    assert int(blocked.headers["Retry-After"]) >= 1

    # Another visitor is unaffected; rejected attempts on unknown targets count too.
    bob = {"X-Real-IP": "198.51.100.9"}
    assert (await client.post(url, json=_comment_payload(), headers=bob)).status_code == 200
    for _ in range(2):
        missing = await client.post(
            "/api/public/articles/nope/comments", json=_comment_payload(), headers=bob
        )
        assert missing.status_code == 404
    assert (
        await client.post(url, json=_comment_payload(), headers=bob)
    ).status_code == 429


@pytest.mark.asyncio
async def test_comment_daily_limit(client, mailer, settings, app):
    token = await _owner_token(client, mailer, settings)
    await _publish_journal(client, token)
    client.cookies.clear()
    settings.comment_rate_minute = 100
    url = "/api/public/journals/monday-notes/comments"
    carol = {"X-Real-IP": "192.0.2.44"}
    for _ in range(settings.comment_rate_day):
        assert (await client.post(url, json=_comment_payload(), headers=carol)).status_code == 200
    assert (await client.post(url, json=_comment_payload(), headers=carol)).status_code == 429
