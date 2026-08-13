# Portfolio API

FastAPI + Beanie/MongoDB + Redis. Primary test seam: **HTTP API** (`/api/...`).

## Prerequisites

- Python 3.12+ (3.14 used in development)
- Docker (for Mongo + Redis)

## Start dependencies

From the repo root:

```bash
docker compose up -d
```

Defaults:

- MongoDB: `mongodb://127.0.0.1:27017`
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

Expected when deps are up:

```json
{"status":"ok","mongo":"up","redis":"up"}
```

## Tests

With `docker compose up -d` running:

```bash
cd backend
.\.venv\Scripts\python -m pytest -v
```

Override URLs if needed:

```bash
set MONGO_URI=mongodb://127.0.0.1:27017
set REDIS_URL=redis://127.0.0.1:6380/15
pytest -v
```

## Layout

- `app/main.py` — app factory, lifespan, health route
- `app/config.py` — settings from env
- `tests/` — HTTP-seam integration tests
