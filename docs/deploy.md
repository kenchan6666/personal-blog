# Single-VM deploy (nginx + Compose)

One host runs **nginx :80**, **Next.js**, **FastAPI/uvicorn**, the internal
**Portfolio Agent**, **MongoDB**, **Qdrant**, and **Redis**. Browsers talk only to nginx:
`/` → frontend, `/api/` → API. The Agent has no public port; Owner login and
the API proxy protect every chat and upload. A chat turn may run up to 600s
(Viola `--timeout 600`); nginx and the API proxy match that window. The stream
sends SSE keepalives so a silent Gemini thinking pass is not cut as a network
error.

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

Logs: `docker compose -f docker-compose.prod.yml logs -f api agent web nginx`.

Stop: `.\deployment\stop.ps1 --prod` (or `bash deployment/stop.sh --prod`).

## Secrets checklist

| Variable | Where to get it | Required to demo OTP? | Required for SourceRepo? |
| --- | --- | --- | --- |
| `OWNER_EMAIL` | Your allowlisted mailbox | yes | yes |
| `MAIL_BACKEND=console` | — OTP appears in API logs | yes (dev/demo) | — |
| `MAIL_BACKEND=resend` + `RESEND_API_KEY` + `SMTP_FROM` | [Resend](https://resend.com) API key; verify `kenchan0522.blog` and send from e.g. `ken@kenchan0522.blog` | yes, if you want the OTP in the inbox | — |
| `SMTP_USER` / `SMTP_PASSWORD` | Gmail **App Password** | optional; consumer Gmail SMTP from this VM usually fails. OTP still prints to API logs. | — |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub → Settings → Developer settings → OAuth Apps | no | yes |
| `GITHUB_OAUTH_CALLBACK_URL` | `{PUBLIC_ORIGIN}/api/auth/github/callback` | no | yes |
| `GITHUB_OAUTH_SUCCESS_URL` | `{PUBLIC_ORIGIN}/zh-Hant/admin` | no | yes |
| `PUBLIC_ORIGIN` | VM IP or DNS, e.g. `http://203.0.113.10` | set before GitHub OAuth | yes |

After you know `PUBLIC_ORIGIN`, set GitHub callback/success to that origin (not leftover `localhost`).

Never commit `deployment/.env`. Rotate any secret that has been pasted into chat.

## Portfolio Agent

Set these values in `deployment/.env` before using the Agent tab:

- `UNI_API_KEY`: your UniAPI key.
- `UNI_API_BASE=https://api.uniapi.io`.
- `VIOLA_AGENT_MODEL=gemini-2.5-flash` (change this only when UniAPI uses a
  different exact model slug).
- `AGENT_INTERNAL_TOKEN`: a random secret used by FastAPI when calling Viola.
- `AGENT_SERVICE_TOKEN`: a different random secret used by the Portfolio MCP
  when calling Owner APIs.
- `AGENT_EMBEDDING_MODEL=text-embedding-3-small`: UniAPI 中已验证可用的 Embedding 模型。`gemini-embedding-001` 在部分账号无渠道，同步时会自动回退。
- `QDRANT_URL=http://qdrant:6333`: Compose 内部向量数据库地址。

Generate the two tokens with `python deployment/ensure_agent_tokens.py deployment/.env`
(no `openssl` or GitHub CLI). They must be different and
must never use a `NEXT_PUBLIC_` name. The Agent reads all Owner-visible content,
including drafts and comment email addresses. It can create/update content
through MCP, but new records are always Draft and no delete tool is exposed.

后台 Agent 页面会持久保存多组会话与消息。右侧“关于我”用于查看、添加和修改
模块化个人资料；资料正文保存在 MongoDB，并同步向量到 Qdrant。若 Embedding
服务暂时不可用，资料仍会保存，Agent 自动降级为关键词检索。站点事实仍应保留
在 CMS 中，Agent 会通过 MCP 实时读取。

新增或编辑资料时会立即自动尝试向量同步；失败不会阻止 MongoDB 保存。后台
“关于我”可对单条资料点“同步”，也可点“同步全部”重试。批量同步检测到旧
Embedding 模型造成的向量维度不兼容时，会仅重建 Qdrant collection，再从
MongoDB 全量恢复向量，不会删除资料正文。

公开站点侧栏另有一个只读 Portfolio Guide。它不复用 Owner Agent 权限，只读取
Published 的 Profile、About、Project、Article、Journal，以及已绑定公开仓库的
README。访客不能上传、写入内容或访问私有 RAG / 私有 GitHub 源码。后台 Owner
Agent 经同一套 GitHub OAuth 读取已绑定仓库，包括 private；GitHub token 不离开
FastAPI。
标识限制每分钟 4 次、每小时 20 次、每天 40 次，并以
`PUBLIC_AGENT_DAILY_BUDGET` 设置全站每日模型调用上限。可在
`deployment/.env` 中调整所有 `PUBLIC_AGENT_*` 值；设
`PUBLIC_AGENT_ENABLED=false` 可立即关闭公开导览。

## Owner login on the deployed site

1. Open `/zh-Hant/admin/login`.
2. If `MAIL_BACKEND=resend` and the domain is verified, the code arrives in `OWNER_EMAIL`.
3. If `MAIL_BACKEND=console`, or Resend/SMTP fails, run `docker compose -f docker-compose.prod.yml logs api` and copy the `[otp] ... code=`.
4. After login, CMS and GitHub connect use `/api` on the same host.

## TLS

`bash deployment/start.sh --prod` requests a Let's Encrypt certificate for the host in `PUBLIC_ORIGIN` (must be a domain, not a raw IP). HTTP-01 is served at `/.well-known/acme-challenge/`. After issuance, nginx listens on **443** and redirects HTTP to HTTPS.

Open GCP firewall **tcp:80** and **tcp:443**. Turn off GoDaddy HTTPS forwarding/parking first, or certbot cannot prove the domain. Set `TLS_EMAIL` (or `OWNER_EMAIL`) in `deployment/.env`. GitHub OAuth callback must use `https://`.

## Layout

- `bash deployment/start.sh --prod` — one-command bring-up
- `docker-compose.prod.yml` — mongo, redis, qdrant, api, agent, web, nginx
- `deployment/nginx.conf` — reverse proxy
- `deployment/env.example` — template for `deployment/.env`
- `backend/Dockerfile`, `frontend/Dockerfile`
