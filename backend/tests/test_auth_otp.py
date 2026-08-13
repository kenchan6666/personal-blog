"""
Seam: Portfolio HTTP API.
Ticket: #3 Owner email OTP login.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_otp_request_rejects_non_allowlisted_email(client):
    response = await client.post(
        "/api/auth/otp/request",
        json={"email": "stranger@example.com"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "email_not_allowed"


@pytest.mark.asyncio
async def test_otp_request_sends_code_for_owner_email(client, mailer, settings):
    response = await client.post(
        "/api/auth/otp/request",
        json={"email": settings.owner_email},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "sent"}
    assert len(mailer.sent) == 1
    assert mailer.sent[0]["to"] == settings.owner_email
    assert mailer.sent[0]["code"].isdigit()
    assert len(mailer.sent[0]["code"]) == 6


@pytest.mark.asyncio
async def test_otp_verify_rejects_expired_code(client, mailer, settings, app):
    await client.post(
        "/api/auth/otp/request",
        json={"email": settings.owner_email},
    )
    code = mailer.sent[-1]["code"]
    await app.state.redis.delete(f"otp:code:{settings.owner_email.lower()}")
    response = await client.post(
        "/api/auth/otp/verify",
        json={"email": settings.owner_email, "code": code},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_otp"


@pytest.mark.asyncio
async def test_otp_verify_issues_session_for_valid_code(client, mailer, settings):
    await client.post(
        "/api/auth/otp/request",
        json={"email": settings.owner_email},
    )
    code = mailer.sent[-1]["code"]
    response = await client.post(
        "/api/auth/otp/verify",
        json={"email": settings.owner_email, "code": code},
    )
    assert response.status_code == 200
    body = response.json()
    assert "session_token" in body
    assert len(body["session_token"]) >= 32


@pytest.mark.asyncio
async def test_owner_route_requires_session(client, mailer, settings):
    denied = await client.get("/api/auth/me")
    assert denied.status_code == 401

    await client.post(
        "/api/auth/otp/request",
        json={"email": settings.owner_email},
    )
    code = mailer.sent[-1]["code"]
    verified = await client.post(
        "/api/auth/otp/verify",
        json={"email": settings.owner_email, "code": code},
    )
    token = verified.json()["session_token"]

    allowed = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert allowed.status_code == 200
    assert allowed.json() == {"email": settings.owner_email, "role": "owner"}


@pytest.mark.asyncio
async def test_otp_request_rate_limited(client, settings):
    for _ in range(settings.otp_rate_limit):
        ok = await client.post(
            "/api/auth/otp/request",
            json={"email": settings.owner_email},
        )
        assert ok.status_code == 200

    limited = await client.post(
        "/api/auth/otp/request",
        json={"email": settings.owner_email},
    )
    assert limited.status_code == 429
    assert limited.json()["detail"] == "rate_limited"
