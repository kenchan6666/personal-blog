# Personal Portfolio

Job-seeking portfolio: Next.js frontend + FastAPI backend (Mongo/Beanie + Redis).

## Quick start

One command starts Mongo, Redis, FastAPI, and Next.js.

Windows PowerShell:

```powershell
.\deployment\start.ps1
```

macOS / Linux / Git Bash:

```bash
bash deployment/start.sh
```

Site: [http://127.0.0.1:3000/zh-Hant](http://127.0.0.1:3000/zh-Hant). API health: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health). Ctrl+C stops the app processes; Mongo/Redis keep running. Stop deps with `.\deployment\stop.ps1` (or `bash deployment/stop.sh`).

Manual steps (same as the script) are in [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md).

### Single-VM deploy (nginx)

```powershell
.\deployment\start.ps1 --prod
```

See [docs/deploy.md](docs/deploy.md). Compose file: `docker-compose.prod.yml`.

## Specs & tickets

- Spec: [docs/specs/0001-personal-portfolio.md](docs/specs/0001-personal-portfolio.md)
- GitHub: https://github.com/kenchan6666/personal-blog
