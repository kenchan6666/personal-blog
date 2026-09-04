"""
Seam: Portfolio HTTP API.
Resume templates, filled documents, PDF generation, GitHub import.
"""

from __future__ import annotations

from pypdf import PdfReader

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


def _resume_payload(**overrides):
    body = {
        "slug": "intern-en",
        "title": "Internship CV",
        "templateSlug": "classic-a4",
        "locale": "en",
        "status": "draft",
        "header": {
            "name": "Chan YatNam",
            "phone": "+852 63058683",
            "email": "ynchanhk@gmail.com",
            "city": "Newcastle upon Tyne",
        },
        "summary": ["Seeking a programming internship."],
        "education": [
            {
                "institution": "Newcastle University",
                "field": "Computer Science",
                "degree": "Bachelor",
                "start": "2022-06",
                "end": "2026-06",
                "city": "Newcastle",
                "honor": "First Honor Degree",
                "related_courses": ["Web Development"],
            }
        ],
        "internships": [],
        "projects": [
            {
                "name": "Pantry pal",
                "start": "2024-05",
                "end": "2024-06",
                "tech_stack": ["Python", "Flask"],
                "description": ["Track food items and expiry dates."],
            }
        ],
        "activities": [],
        "skills": ["Python", "Flask"],
        "languages": [{"name": "English", "level": "Fluent"}],
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio
async def test_builtin_template_is_seeded_and_cannot_be_deleted(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    listed = await client.get("/api/owner/resume-templates", headers=headers)
    assert listed.status_code == 200
    slugs = [item["slug"] for item in listed.json()]
    assert slugs[:6] == [
        "classic-a4",
        "campus-a4",
        "intern-a4",
        "full-a4",
        "work-a4",
        "certs-a4",
    ]
    classic = next(item for item in listed.json() if item["slug"] == "classic-a4")
    intern = next(item for item in listed.json() if item["slug"] == "intern-a4")
    assert classic["name"]["en"] == "Student projects"
    assert intern["sections"] == [
        "summary",
        "education",
        "internship",
        "projects",
        "skillsOthers",
    ]
    deleted = await client.delete(
        f"/api/owner/resume-templates/{classic['id']}",
        headers=headers,
    )
    assert deleted.status_code == 400
    edited = await client.put(
        f"/api/owner/resume-templates/{classic['id']}",
        json={"slug": "classic-a4", "name": classic["name"], "sections": ["summary"]},
        headers=headers,
    )
    assert edited.status_code == 400


@pytest.mark.asyncio
async def test_duplicate_custom_layout_is_folded_into_builtin(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    clone = await client.post(
        "/api/owner/resume-templates",
        json={
            "slug": "clone-classic",
            "name": {"zh-Hant": "複本", "zh-Hans": "复本", "en": "Clone"},
            "sections": ["summary", "education", "projects", "skillsOthers"],
        },
        headers=headers,
    )
    assert clone.status_code == 200
    created = await client.post(
        "/api/owner/resumes",
        json=_resume_payload(slug="clone-en", templateSlug="clone-classic"),
        headers=headers,
    )
    assert created.status_code == 200
    listed = await client.get("/api/owner/resume-templates", headers=headers)
    slugs = [item["slug"] for item in listed.json()]
    assert "clone-classic" not in slugs
    assert slugs.count("classic-a4") == 1
    resumes = await client.get("/api/owner/resumes", headers=headers)
    row = next(item for item in resumes.json() if item["id"] == created.json()["id"])
    assert row["templateSlug"] == "classic-a4"


@pytest.mark.asyncio
async def test_custom_resume_section_renders_in_pdf(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    layout = await client.post(
        "/api/owner/resume-templates",
        json={
            "slug": "with-certs",
            "name": {"zh-Hant": "證書版", "zh-Hans": "证书版", "en": "Certs"},
            "sections": ["summary", "certs"],
            "extras": [{"slug": "certs", "title": "Certifications"}],
        },
        headers=headers,
    )
    assert layout.status_code == 200
    assert layout.json()["extras"][0]["slug"] == "certs"
    created = await client.post(
        "/api/owner/resumes",
        json=_resume_payload(
            slug="certs-en",
            templateSlug="with-certs",
            extras=[
                {
                    "slug": "certs",
                    "title": "Certifications",
                    "lines": ["AWS Cloud Practitioner"],
                    "entries": [],
                }
            ],
        ),
        headers=headers,
    )
    assert created.status_code == 200
    assert created.json()["extras"][0]["lines"] == ["AWS Cloud Practitioner"]
    pdf = await client.get(
        f"/api/owner/resumes/{created.json()['id']}/pdf",
        headers=headers,
    )
    assert pdf.status_code == 200
    text = PdfReader(io_bytes(pdf.content)).pages[0].extract_text() or ""
    assert "AWS Cloud Practitioner" in text
    assert "CERTIFICATIONS" in text


@pytest.mark.asyncio
async def test_draft_resume_is_hidden_until_published_and_pdf_matches_a4(
    client, mailer, settings
):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        "/api/owner/resumes",
        json=_resume_payload(),
        headers=headers,
    )
    assert created.status_code == 200
    resume_id = created.json()["id"]

    public = await client.get("/api/public/resumes")
    assert public.status_code == 200
    assert public.json() == []

    generated = await client.post(
        f"/api/owner/resumes/{resume_id}/generate",
        headers=headers,
    )
    assert generated.status_code == 200
    assert generated.json()["pdfUrl"].endswith("/intern-en/pdf")
    hidden_pdf = await client.get("/api/public/resumes/intern-en/pdf")
    assert hidden_pdf.status_code == 404

    pdf = await client.get(f"/api/owner/resumes/{resume_id}/pdf", headers=headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    reader = PdfReader(io_bytes(pdf.content))
    assert len(reader.pages) == 1
    box = reader.pages[0].mediabox
    assert abs(float(box.width) - 595) < 1
    assert abs(float(box.height) - 842) < 1
    text = reader.pages[0].extract_text() or ""
    assert "Chan YatNam" in text
    assert "EDUCATION" in text
    assert "Pantry pal" in text

    published = await client.post(
        f"/api/owner/resumes/{resume_id}/publish",
        headers=headers,
    )
    assert published.status_code == 200
    assert published.json()["status"] == "published"

    listed = await client.get("/api/public/resumes")
    assert [item["slug"] for item in listed.json()] == ["intern-en"]
    detail = await client.get("/api/public/resumes/intern-en")
    assert detail.status_code == 200
    assert detail.json()["header"]["name"] == "Chan YatNam"
    public_pdf = await client.get("/api/public/resumes/intern-en/pdf")
    assert public_pdf.status_code == 200


@pytest.mark.asyncio
async def test_resume_title_follows_header_name(client, mailer, settings):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        "/api/owner/resumes",
        json=_resume_payload(title="Internship CV"),
        headers=headers,
    )
    assert created.status_code == 200
    assert created.json()["title"] == "Chan YatNam"

    body = _resume_payload()
    body["header"] = {**body["header"], "name": "Ken Chan"}
    updated = await client.put(
        f"/api/owner/resumes/{created.json()['id']}",
        json=body,
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Ken Chan"


@pytest.mark.asyncio
async def test_import_resume_from_github_uses_authorized_file(
    client, mailer, settings, app
):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    await app.state.redis.set("github:owner_token", "gho_test")
    imported = await client.post(
        "/api/owner/resumes/import-github",
        json={
            "fullName": "kenchan6666/personal-blog",
            "path": "cv/classic.format.json",
            "slug": "from-github",
        },
        headers=headers,
    )
    assert imported.status_code == 200
    body = imported.json()
    assert body["slug"] == "from-github"
    assert body["header"]["name"] == "Chan YatNam"
    assert body["projects"][0]["name"] == "Pantry pal"


@pytest.mark.asyncio
async def test_push_resume_creates_cv_repo_then_updates(
    client, mailer, settings, github, app
):
    token = await _owner_token(client, mailer, settings)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        "/api/owner/resumes",
        json=_resume_payload(),
        headers=headers,
    )
    resume_id = created.json()["id"]

    blocked = await client.post(
        f"/api/owner/resumes/{resume_id}/push-github",
        headers=headers,
    )
    assert blocked.status_code == 409

    await app.state.redis.set("github:owner_token", "gho_test")
    account = await client.get("/api/owner/github/account", headers=headers)
    assert account.status_code == 200
    assert account.json()["connected"] is True
    assert account.json()["login"] == "kenchan6666"
    assert account.json()["cvRepo"] is None

    first = await client.post(
        f"/api/owner/resumes/{resume_id}/push-github",
        headers=headers,
    )
    assert first.status_code == 200
    body = first.json()
    assert body["created"] is True
    assert body["repo"]["fullName"] == "kenchan6666/cv"
    assert body["repo"]["private"] is True
    assert body["resume"]["githubRepo"] == "kenchan6666/cv"
    assert body["resume"]["githubJsonPath"] == "intern-en.json"
    assert body["resume"]["githubPdfPath"] == "intern-en.pdf"
    assert github.created_repos == ["kenchan6666/cv"]
    assert "kenchan6666/cv:intern-en.json" in github.puts
    assert "kenchan6666/cv:intern-en.pdf" in github.puts

    vault = await client.post("/api/owner/github/cv-repo", headers=headers)
    assert vault.status_code == 200
    assert vault.json()["created"] is False
    names = [item["name"] for item in vault.json()["files"]]
    assert "intern-en.json" in names
    assert "intern-en.pdf" in names

    second = await client.post(
        f"/api/owner/resumes/{resume_id}/push-github",
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["created"] is False
    assert github.created_repos == ["kenchan6666/cv"]


def io_bytes(data: bytes):
    from io import BytesIO

    return BytesIO(data)
