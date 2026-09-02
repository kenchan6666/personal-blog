"""
Seam: Portfolio HTTP API.
Ticket: #8 Journal CMS to published public pages (no Project link).
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
    return verified.json()["session_token"]


def _journal_payload(**overrides):
    body = {
        "slug": "monday-notes",
        "title": {"zh-Hant": "週一隨筆", "en": "Monday notes"},
        "summary": {"zh-Hant": "摘要", "en": "Summary"},
        "body": {
            "zh-Hant": "## 今天\n寫一點生活",
            "en": "## Today\nA little life",
        },
        "status": "published",
        "order": 1,
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio
async def test_unauthenticated_cannot_create_journal(client):
    response = await client.post("/api/owner/journals", json=_journal_payload())
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_owner_can_create_update_and_delete_journal(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        "/api/owner/journals",
        json=_journal_payload(),
        headers=headers,
    )
    assert created.status_code == 200
    journal = created.json()
    assert journal["slug"] == "monday-notes"
    assert journal["title"]["zh-Hant"] == "週一隨筆"
    assert "relatedProjectSlug" not in journal
    journal_id = journal["id"]

    updated = await client.put(
        f"/api/owner/journals/{journal_id}",
        json=_journal_payload(
            title={"zh-Hant": "週一隨筆", "en": "Monday notes v2"},
            status="draft",
        ),
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"]["en"] == "Monday notes v2"
    assert updated.json()["status"] == "draft"

    listed = await client.get("/api/owner/journals", headers=headers)
    assert any(item["id"] == journal_id for item in listed.json())

    deleted = await client.delete(
        f"/api/owner/journals/{journal_id}", headers=headers
    )
    assert deleted.status_code == 200
    after = await client.get("/api/owner/journals", headers=headers)
    assert after.json() == []


@pytest.mark.asyncio
async def test_journal_cannot_be_attached_to_a_project(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    response = await client.post(
        "/api/owner/journals",
        json=_journal_payload(relatedProjectSlug="glass-api"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_draft_journal_is_hidden_from_visitors(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    await client.post(
        "/api/owner/journals",
        json=_journal_payload(status="draft"),
        headers={"Authorization": f"Bearer {token}"},
    )

    public_list = await client.get(
        "/api/public/journals", params={"locale": "zh-Hant"}
    )
    assert public_list.status_code == 200
    assert public_list.json() == []

    detail = await client.get("/api/public/journals/monday-notes")
    assert detail.status_code == 404


@pytest.mark.asyncio
async def test_published_journal_appears_in_public_list_and_detail(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    await client.post(
        "/api/owner/journals",
        json=_journal_payload(title={"zh-Hant": "週一隨筆", "en": ""}),
        headers={"Authorization": f"Bearer {token}"},
    )

    zh_list = await client.get(
        "/api/public/journals", params={"locale": "zh-Hant"}
    )
    assert zh_list.status_code == 200
    assert [item["slug"] for item in zh_list.json()] == ["monday-notes"]
    assert zh_list.json()[0]["title"] == "週一隨筆"
    assert "relatedProject" not in zh_list.json()[0]
    assert zh_list.json()[0]["wordCount"] > 0
    assert zh_list.json()[0]["publishedAt"]

    en_detail = await client.get(
        "/api/public/journals/monday-notes", params={"locale": "en"}
    )
    assert en_detail.status_code == 200
    assert en_detail.json()["title"] == "週一隨筆"
    assert en_detail.json()["body"] == "## Today\nA little life"
    assert "relatedProject" not in en_detail.json()
