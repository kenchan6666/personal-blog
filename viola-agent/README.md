# viola-agent (Lolanto)

Python package **viola-ai** plus **Twilio WhatsApp** webhook (`main.py`) used by this repo.

## Docker

Build **from the repository root** (Compose uses `context: ..`, `dockerfile: viola-agent/Dockerfile`):

```bash
docker build -f viola-agent/Dockerfile .
```

`README.md` must remain next to `pyproject.toml` — both are copied into the image. The Dockerfile installs **`mcp_service/mcp_nanobot`** so the nanobot MCP stdio server is available inside the image.

Production split compose: see **`deployment/README.md`** (`docker-compose.agent.yml`).

Note: **`EXPOSE 18790`** in the Dockerfile is for the standalone **gateway** port; the API service binds **`serve` on `8900`** via the container command.

## Twilio webhook (local probe)

- `GET http://127.0.0.1:8800/webhook` — health-style probe (browser)
- `POST /webhook` — Twilio inbound (form POST)
- `GET /health` — JSON health

Run `viola serve` separately (e.g. port **8900**); set **`VIOLA_API_BASE`** on the webhook service.

### Twilio Console URL **cannot** be `localhost`

Twilio runs on the public internet. A webhook like `http://localhost:8800/webhook` is **never** reachable by Twilio. Expose the service with a **public HTTPS URL** (ngrok for dev, nginx for prod).

## Deployment environment

Set in repo-root **`.env`**:

- **`BACKEND_API_BASE_URL`** — HTTP base for webhook → backend (`main.py` requires a non-empty value).
- **`INTERNAL_SECRET`** — must match the backend; used for **`POST /api/whatsapp-auth/token`** sender verification.
- **`VIOLA_CUSTOMER_SERVICE_ONLY=true`** (default) — customer Q&A only; mutation requests are blocked.
- **`VIOLA_TOOLS__PERSISTENCE_VIA_MCP_ONLY=true`** (default) — disable local workspace/shell persistence.

## Nanobot MCP

- Docker image installs `mcp_service/mcp_nanobot` by default.
- Default policy is read-only: `NANOBOT_WRITE_ENABLED=false`, `NANOBOT_READ_ONLY_MODE=true`.
- Preflight: `python viola-agent/scripts/check_mcp_nanobot_preflight.py`
- Runtime check: `GET /v1/diag` → `nanobot.configured` / `nanobot.connected`

## Viola MCP mainline migration

- `CS_VIOLA_MAINLINE_MODE=off|shadow|canary|full`
- `CS_VIOLA_MAINLINE_FALLBACK_ENABLED=true|false`
- Hard-cutover: `CS_VIOLA_MAINLINE_MODE=full`, `CS_VIOLA_MAINLINE_FALLBACK_ENABLED=false`
- Preflight: `python viola-agent/scripts/check_viola_mcp_mainline_preflight.py`
