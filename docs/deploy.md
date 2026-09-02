# Single-VM deploy (nginx + Compose)

One host runs **nginx :80**, **Next.js**, **FastAPI/uvicorn**, **MongoDB**, and **Redis**. Browsers talk only to nginx: `/` → frontend, `/api/` → API. Owner OTP login uses the same origin, so sessions work without extra CORS.

Local Mongo/Redis on host ports (`docker compose up -d`) is unchanged. This file is the **production/demo** stack.

## Bring up

Windows PowerShell:

```powershell
.\deployment\start.ps1 --prod
```

macOS / Linux / Git Bash:

```bash
bash deployment/start.sh --prod
```

The script copies `deployment/env.example` to `deployment/.env` on first run. Edit that file (see checklist below) and run the same command again if you change secrets.

Equivalent compose:

```bash
cp deployment/env.example deployment/.env
docker compose -f docker-compose.prod.yml --env-file deployment/.env up -d --build
```

Then open `http://<host>/zh-Hant`. Health: `http://<host>/api/health`.

Logs: `docker compose -f docker-compose.prod.yml logs -f api web nginx`.

Stop: `.\deployment\stop.ps1 --prod` (or `bash deployment/stop.sh --prod`).

## Secrets checklist

| Variable | Where to get it | Required to demo OTP? | Required for SourceRepo? |
| --- | --- | --- | --- |
| `OWNER_EMAIL` | Your allowlisted mailbox | yes | yes |
| `MAIL_BACKEND=console` | — OTP appears in API logs | yes (dev/demo) | — |
| `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` | Gmail **App Password** (Google Account → Security → 2FA → App passwords) | only if `MAIL_BACKEND=smtp` | — |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub → Settings → Developer settings → OAuth Apps | no | yes |
| `GITHUB_OAUTH_CALLBACK_URL` | `{PUBLIC_ORIGIN}/api/auth/github/callback` | no | yes |
| `GITHUB_OAUTH_SUCCESS_URL` | `{PUBLIC_ORIGIN}/zh-Hant/admin` | no | yes |
| `PUBLIC_ORIGIN` | VM IP or DNS, e.g. `http://203.0.113.10` | set before GitHub OAuth | yes |

After you know `PUBLIC_ORIGIN`, set GitHub callback/success to that origin (not leftover `localhost`).

Never commit `deployment/.env`. Rotate any secret that has been pasted into chat.

## Owner login on the deployed site

1. Open `/zh-Hant/admin/login`.
2. If `MAIL_BACKEND=console`, run `docker compose -f docker-compose.prod.yml logs api` and copy the `[otp] ... code=`.
3. If SMTP is set, read the code from the Owner inbox.
4. After login, CMS and GitHub connect use `/api` on the same host.

## TLS (later)

Point DNS at the VM, put certificates on the host, and extend `deployment/nginx.conf` with `listen 443 ssl`. Until then, HTTP on port 80 is enough for a private demo.

## Layout

- `bash deployment/start.sh --prod` — one-command bring-up
- `docker-compose.prod.yml` — mongo, redis, api, web, nginx
- `deployment/nginx.conf` — reverse proxy
- `deployment/env.example` — template for `deployment/.env`
- `backend/Dockerfile`, `frontend/Dockerfile`
