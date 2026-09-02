# Portfolio API

FastAPI + Beanie/MongoDB (or local JSON) + Redis. Primary test seam: **HTTP API** (`/api/...`).

## Prerequisites

- Python 3.12+ (3.14 used in development)
- Docker (for Redis; Mongo only if `MONGO_URI` is set)

## Start (one command)

From the repo root, Redis + API + Next.js (Mongo too if `MONGO_URI` is set):

```powershell
.\deployment\start.ps1
```

```bash
bash deployment/start.sh
```

## Start dependencies only

From the repo root:

```bash
docker compose up -d
```

Defaults:

- If `MONGO_URI` is empty or omitted, the API writes collections as JSON under `LOCAL_DATA_DIR` (default `data/local`). Health then reports `"mongo": "local"`.
- MongoDB (optional): `mongodb://127.0.0.1:27019` (host **27019** → container 27017; avoids clashes with other local Mongo on 27017)
- Redis: `redis://127.0.0.1:6380` (host port **6380** → container 6379)

## Install & run

```bash
cd backend
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Health check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

Expected when Redis is up and Mongo is configured:

```json
{"status":"ok","mongo":"up","redis":"up"}
```

Expected when `MONGO_URI` is empty (local JSON store):

```json
{"status":"ok","mongo":"local","redis":"up"}
```

## Owner OTP auth

Endpoints:

- `POST /api/auth/otp/request` `{ "email": "..." }`
- `POST /api/auth/otp/verify` `{ "email": "...", "code": "......" }` → `{ "session_token": "..." }`
- `GET /api/auth/me` with `Authorization: Bearer <token>`

Copy `.env.example` to `.env`. Local login can use `MAIL_BACKEND=console` (OTP in API stdout). Production on GCP should use `MAIL_BACKEND=resend` and `RESEND_API_KEY`. Frontend admin UI: `/zh-Hant/admin/login`.

## Site profile + avatar

- `GET /api/public/site?locale=zh-Hant|zh-Hans|en`
- `GET/PUT /api/owner/site` (Bearer)
- `POST /api/owner/avatar` multipart field `file` (png/jpeg/webp, Bearer)
- `GET /api/public/media/avatar/{filename}`

Avatars, hero, and Markdown content images are stored under `AVATAR_DIR` (local default `data/avatars`; production bind-mounts `./data/media`). The first `--prod` start copies any leftover `avatar_data` volume into that folder once.

## Projects

- `GET /api/public/projects?locale=` — Published only, ordered
- `GET /api/public/projects/{slug}?locale=` — 404 for Draft / missing
- `GET/POST /api/owner/projects` and `PUT /api/owner/projects/{id}` (Bearer)

Bilingual Markdown fields: `title`, `summary`, `body`. Status is `draft` | `published`. Locales: `zh-Hant`, `zh-Hans`, `en`.

## Articles

- `GET /api/public/articles?locale=` — Published only
- `GET /api/public/articles/{slug}?locale=` — includes `relatedProject` when that Project is Published
- `GET/POST /api/owner/articles`, `PUT/DELETE /api/owner/articles/{id}` (Bearer)

Optional `relatedProjectSlug` and `categorySlug`. A missing or deleted category leaves the Article untagged. A Draft related Project is omitted from the public payload.

## Journals

- `GET /api/public/journals?locale=` — Published only
- `GET /api/public/journals/{slug}?locale=`
- `GET/POST /api/owner/journals`, `PUT/DELETE /api/owner/journals/{id}` (Bearer)

Journals have no `relatedProject`. Sending `relatedProjectSlug` is rejected with 400.

## About modules

Owner-managed CV-like blocks on the public personal-detail page (`/about`).

- `GET /api/public/about?locale=zh-Hant|zh-Hans|en` — Published only, ordered
- `GET/POST /api/owner/about-modules` and `PUT/DELETE /api/owner/about-modules/{id}` (Bearer)
- `POST /api/owner/media` multipart field `file` (png/jpeg/webp, Bearer) — returns `{ url }` for Markdown images
- `GET /api/public/media/content/{filename}`
- `POST /api/owner/translate` (Bearer) — fills empty `zh-Hant` / `zh-Hans` / `en` from one original. Chinese uses script conversion; English uses machine translation. Filled locales are kept. Public pages still show stored text only.

Kinds: `summary`, `education`, `achievement`, `experience`, `custom`. Each kind has a distinct public template (narrative / timeline / cards). Trilingual Markdown: `title`, `body`. Status is `draft` | `published`.

## GitHub OAuth + SourceRepo

Create a GitHub OAuth App (callback `GITHUB_OAUTH_CALLBACK_URL`) and set `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET`.

- `GET /api/owner/github/oauth/start` (Bearer) → `{ authorizationUrl }`
- `GET /api/auth/github/callback?code=&state=` → redirects to admin; **never** puts the access token in the URL
- `GET /api/owner/github/repos` (Bearer) — 409 if GitHub is not connected
- `GET /api/owner/github/repos/{owner}/{name}` (+ `/tree`, `/blob`) — Owner/Agent can read authorized public and private repos without attaching a Project
- `PUT /api/owner/projects/{id}/source-repo` `{ "fullName": "owner/name" }`

Public project payloads may include `sourceRepo` metadata. Unattached GitHub repos never appear as public Projects.

Public SourceRepo browser (Published + public repo only; Redis cache ~120s, no git mirror):

- `GET /api/public/projects/{slug}/source?ref=`
- `GET /api/public/projects/{slug}/source/tree?ref=&path=`
- `GET /api/public/projects/{slug}/source/blob?ref=&path=`

Private SourceRepos and Draft Projects return 404 for these routes.

## Comments

Journal and Article only (Projects 404). Visitor `POST` with `displayName`, `email`, `body` creates a **pending** Comment. Public `GET` returns approved comments without `email`. Owner `GET /api/owner/comments` sees emails; `POST .../approve|reject|reply` to moderate.

## Production compose

See [docs/deploy.md](../docs/deploy.md). `MONGO_URI` / `REDIS_URL` inside the stack are `mongodb://mongo:27017` and `redis://redis:6379/0`.

## Tests

With `docker compose up -d` running:

```bash
cd backend
.\.venv\Scripts\python -m pytest -v
```

Override URLs if needed:

```bash
set MONGO_URI=mongodb://127.0.0.1:27019
set REDIS_URL=redis://127.0.0.1:6380/15
pytest -v
```

## Layout

- `app/main.py` — app factory, lifespan, health + auth + site routes
- `app/config.py` — settings from env
- `app/models.py` — documents (SiteProfile, Project, Article, Journal, Comment)
- `app/store.py` — Mongo or local JSON persistence
- `app/github.py` — GitHub OAuth + repo list (injected in tests)
- `tests/` — HTTP-seam integration tests
