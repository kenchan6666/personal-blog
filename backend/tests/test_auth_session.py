"""
Seam: Portfolio HTTP API.
OTP verify lockout, cookie sessions, server-side logout, CSRF origin checks.
"""

from __future__ import annotations

import pytest

ORIGIN = {"Origin": "http://localhost:3000"}


async def _request(client, settings, ip="203.0.113.7"):
    return await client.post(
        "/api/auth/otp/request",
        json={"email": settings.owner_email},
        headers={"X-Real-IP": ip},
    )


async def _verify(client, settings, code, ip="203.0.113.7"):
    return await client.post(
        "/api/auth/otp/verify",
        json={"email": settings.owner_email, "code": code},
        headers={"X-Real-IP": ip, **ORIGIN},
    )


async def _login(client, mailer, settings):
    await _request(client, settings)
    response = await _verify(client, settings, mailer.sent[-1]["code"])
    assert response.status_code == 200
    return response


def _wrong(code: str) -> str:
    return "000000" if code != "000000" else "111111"


@pytest.mark.asyncio
async def test_five_wrong_codes_lock_and_burn_the_code(client, mailer, settings):
    await _request(client, settings)
    code = mailer.sent[-1]["code"]
    for _ in range(4):
        response = await _verify(client, settings, _wrong(code))
        assert response.status_code == 401
    fifth = await _verify(client, settings, _wrong(code))
    assert fifth.status_code == 429
    assert fifth.json()["detail"] == "otp_locked"
    # Even the right code is refused while locked.
    right = await _verify(client, settings, code)
    assert right.status_code == 429
    assert "portfolio_session" not in client.cookies
    # Requesting a new code is also refused during the lock.
    again = await _request(client, settings)
    assert again.status_code == 429


@pytest.mark.asyncio
async def test_lock_expiry_does_not_revive_burned_code(client, mailer, settings, app):
    await _request(client, settings)
    code = mailer.sent[-1]["code"]
    for _ in range(5):
        await _verify(client, settings, _wrong(code))
    email = settings.owner_email.lower()
    await app.state.redis.delete(f"otp:lock:email:{email}")
    await app.state.redis.delete("otp:lock:ip:203.0.113.7")
    response = await _verify(client, settings, code)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ip_lock_applies_across_attempts_from_same_ip(client, mailer, settings, app):
    await _request(client, settings, ip="198.51.100.9")
    code = mailer.sent[-1]["code"]
    for _ in range(5):
        await _verify(client, settings, _wrong(code), ip="198.51.100.9")
    assert await app.state.redis.get("otp:lock:ip:198.51.100.9")


@pytest.mark.asyncio
async def test_code_is_single_use(client, mailer, settings):
    await _request(client, settings)
    code = mailer.sent[-1]["code"]
    first = await _verify(client, settings, code)
    assert first.status_code == 200
    second = await _verify(client, settings, code)
    assert second.status_code == 401


@pytest.mark.asyncio
async def test_success_resets_failure_counter(client, mailer, settings, app):
    await _request(client, settings)
    code = mailer.sent[-1]["code"]
    for _ in range(3):
        await _verify(client, settings, _wrong(code))
    assert (await _verify(client, settings, code)).status_code == 200
    email = settings.owner_email.lower()
    assert await app.state.redis.get(f"otp:fail:email:{email}") is None


@pytest.mark.asyncio
async def test_otp_is_not_stored_in_plaintext(client, mailer, settings, app):
    await _request(client, settings)
    code = mailer.sent[-1]["code"]
    stored = await app.state.redis.get(f"otp:code:{settings.owner_email.lower()}")
    assert stored and stored != code


@pytest.mark.asyncio
async def test_cookie_session_authorizes_owner_routes(client, mailer, settings):
    await _login(client, mailer, settings)
    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == settings.owner_email


@pytest.mark.asyncio
async def test_logout_revokes_session_server_side(client, mailer, settings):
    response = await _login(client, mailer, settings)
    token = response.cookies["portfolio_session"]
    out = await client.post("/api/auth/logout", headers=ORIGIN)
    assert out.status_code == 200
    assert "portfolio_session" not in client.cookies
    # A copied cookie no longer works after logout.
    replay = await client.get(
        "/api/auth/me", cookies={"portfolio_session": token}
    )
    assert replay.status_code == 401


@pytest.mark.asyncio
async def test_cross_site_write_with_cookie_is_rejected(client, mailer, settings):
    await _login(client, mailer, settings)
    evil = await client.put(
        "/api/owner/site",
        json={},
        headers={"Origin": "https://evil.example"},
    )
    assert evil.status_code == 403
    assert evil.json()["detail"] == "bad_origin"
    cross = await client.post(
        "/api/auth/logout", headers={"Sec-Fetch-Site": "cross-site"}
    )
    assert cross.status_code == 403
    # Cross-site reads are not blocked by the origin check (CORS covers reads).
    me = await client.get("/api/auth/me", headers={"Origin": "https://evil.example"})
    assert me.status_code == 200


@pytest.mark.asyncio
async def test_same_origin_write_from_forwarded_host_is_allowed(client, mailer, settings):
    await _login(client, mailer, settings)
    response = await client.post(
        "/api/auth/logout",
        headers={
            "Origin": "https://blog.example",
            "Host": "blog.example",
            "X-Forwarded-Proto": "https",
        },
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_old_plain_session_keys_are_ignored(client, app, settings):
    await app.state.redis.set("session:legacy-token", settings.owner_email)
    response = await client.get(
        "/api/auth/me", cookies={"portfolio_session": "legacy-token"}
    )
    assert response.status_code == 401
