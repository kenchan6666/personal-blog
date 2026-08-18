# Personal Portfolio

Job-seeking portfolio: Next.js frontend + FastAPI backend (Mongo/Beanie + Redis).

## Quick start

### Dependencies (Mongo + Redis)

```bash
docker compose up -d
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

See [backend/README.md](backend/README.md).

### Single-VM deploy (nginx)

See [docs/deploy.md](docs/deploy.md). Compose file: `docker-compose.prod.yml`.

## Specs & tickets

- Spec: [docs/specs/0001-personal-portfolio.md](docs/specs/0001-personal-portfolio.md)
- GitHub: https://github.com/kenchan6666/personal-blog
