#!/usr/bin/env bash
# One-command start for the portfolio stack (Git Bash / macOS / Linux).
# Windows PowerShell: use .\deployment\start.ps1 — `bash` on Windows is WSL, not Git Bash.
#   bash deployment/start.sh          local: Redis + FastAPI + Next.js (Mongo if MONGO_URI is set)
#   bash deployment/start.sh --prod   single-VM compose (nginx :80)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
PROD=0
DOWN=0

usage() {
  cat <<'EOF'
Usage: bash deployment/start.sh [--prod] [--down]

  (default)  Start Redis, FastAPI, and Next.js. Mongo starts only if MONGO_URI is set.
  --prod     Build and start the nginx + containers stack on :80.
  --down     Stop the stack that matches the other flags (dev deps or prod).
EOF
}

die() {
  echo "error: $*" >&2
  exit 1
}

need() {
  command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --prod) PROD=1 ;;
    --down) DOWN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1 (try --help)" ;;
  esac
  shift
done

if [ "$PROD" -eq 1 ] && [ "$DOWN" -eq 1 ]; then
  MODE="prod-down"
elif [ "$PROD" -eq 1 ]; then
  MODE="prod"
elif [ "$DOWN" -eq 1 ]; then
  MODE="dev-down"
else
  MODE="dev"
fi

need docker
docker compose version >/dev/null 2>&1 || die "docker compose plugin is required"

ensure_prod_env() {
  if [ ! -f "$DIR/.env" ]; then
    cp "$DIR/env.example" "$DIR/.env"
    echo "created $DIR/.env from env.example — edit secrets if you need SMTP or GitHub OAuth"
  fi
}

compose_prod() {
  docker compose -f "$ROOT/docker-compose.prod.yml" --env-file "$DIR/.env" "$@"
}

compose_deps() {
  docker compose -f "$ROOT/docker-compose.yml" "$@"
}

read_dotenv_value() {
  local file="$1"
  local key="$2"
  [ -f "$file" ] || return 0
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      ''|\#*) continue ;;
    esac
    if [ "${line%%=*}" = "$key" ]; then
      local value="${line#*=}"
      value="${value%\"}"
      value="${value#\"}"
      value="${value%\'}"
      value="${value#\'}"
      printf '%s' "$value"
      return 0
    fi
  done < "$file"
}

venv_python() {
  if [ -x "$ROOT/backend/.venv/Scripts/python.exe" ]; then
    echo "$ROOT/backend/.venv/Scripts/python.exe"
  elif [ -x "$ROOT/backend/.venv/bin/python" ]; then
    echo "$ROOT/backend/.venv/bin/python"
  else
    return 1
  fi
}

host_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo python3
  elif command -v python >/dev/null 2>&1; then
    echo python
  else
    die "Python 3.12+ is required (python3 or python)"
  fi
}

wait_http() {
  local url="$1"
  local tries="${2:-60}"
  local i=0
  while [ "$i" -lt "$tries" ]; do
    if command -v curl >/dev/null 2>&1; then
      curl -sf "$url" >/dev/null 2>&1 && return 0
    fi
    i=$((i + 1))
    sleep 2
  done
  return 1
}

ensure_media_dir() {
  mkdir -p "$ROOT/data/media"
  local marker="$ROOT/data/media/.migrated-from-avatar-volume"
  if [ -f "$marker" ]; then
    return 0
  fi
  local vol
  vol="$(docker volume ls -q | grep 'avatar_data$' | head -n 1 || true)"
  if [ -n "$vol" ]; then
    echo "one-time copy $vol → data/media"
    docker run --rm -v "$vol:/from:ro" -v "$ROOT/data/media:/to" alpine:3.20 \
      sh -c 'cp -an /from/. /to/'
  fi
  touch "$marker"
}

start_prod() {
  ensure_prod_env
  ensure_media_dir
  mkdir -p "$DIR/nginx-runtime"
  cp "$DIR/nginx/http.conf" "$DIR/nginx-runtime/default.conf"

  echo "starting production stack (nginx :80/:443)…"
  compose_prod up -d --build
  if wait_http "http://127.0.0.1/api/health" 45; then
    echo "health: http://127.0.0.1/api/health"
    issue_letsencrypt || echo "TLS skipped — site is on http until certbot succeeds (open GCP tcp:80 and tcp:443, turn off GoDaddy HTTPS forwarding)."
    echo "ready: http://127.0.0.1/zh-Hant"
  else
    echo "containers are up; health check timed out. logs:"
    compose_prod logs --tail 40 api web nginx
  fi
}

host_from_origin() {
  local origin="$1"
  origin="${origin#http://}"
  origin="${origin#https://}"
  origin="${origin%/}"
  printf '%s' "$origin"
}

issue_letsencrypt() {
  local origin domain email
  origin="$(read_dotenv_value "$DIR/.env" "PUBLIC_ORIGIN")"
  domain="$(host_from_origin "$origin")"
  email="$(read_dotenv_value "$DIR/.env" "TLS_EMAIL")"
  if [ -z "$email" ]; then
    email="$(read_dotenv_value "$DIR/.env" "OWNER_EMAIL")"
  fi
  case "$domain" in
    ""|YOUR_PUBLIC_IP|*localhost*|*[0-9].*[0-9].*[0-9].*[0-9]*)
      echo "PUBLIC_ORIGIN=$origin is not a domain — skipping Let's Encrypt"
      return 1
      ;;
  esac
  if [ -z "$email" ]; then
    echo "TLS_EMAIL / OWNER_EMAIL empty — skipping Let's Encrypt"
    return 1
  fi
  echo "requesting Let's Encrypt cert for $domain …"
  if compose_prod run --rm --no-deps --entrypoint certbot certbot certonly \
    --webroot -w /var/www/certbot \
    --cert-name site \
    --agree-tos --non-interactive \
    --email "$email" \
    -d "$domain" -d "www.$domain"
  then
    :
  elif compose_prod run --rm --no-deps --entrypoint certbot certbot certonly \
    --webroot -w /var/www/certbot \
    --cert-name site \
    --agree-tos --non-interactive \
    --email "$email" \
    -d "$domain"
  then
    :
  else
    return 1
  fi
  cp "$DIR/nginx/ssl.conf" "$DIR/nginx-runtime/default.conf"
  compose_prod exec -T nginx nginx -s reload
  echo "TLS ready: https://$domain"
  return 0
}

stop_prod() {
  ensure_prod_env
  compose_prod down
  echo "production stack stopped"
}

start_dev() {
  need npm
  if [ ! -f "$ROOT/backend/.env" ]; then
    cp "$ROOT/backend/.env.example" "$ROOT/backend/.env"
    echo "created backend/.env from .env.example"
  fi

  MONGO_URI_VALUE="${MONGO_URI:-}"
  if [ -z "$MONGO_URI_VALUE" ]; then
    MONGO_URI_VALUE="$(read_dotenv_value "$ROOT/backend/.env" "MONGO_URI")"
  fi
  if [ -n "$MONGO_URI_VALUE" ]; then
    echo "starting Mongo + Redis…"
    compose_deps up -d
  else
    echo "MONGO_URI empty — starting Redis only; API stores data in backend/data/local"
    compose_deps up -d redis
  fi

  if ! PY="$(venv_python)"; then
    echo "creating backend virtualenv…"
    "$(host_python)" -m venv "$ROOT/backend/.venv"
    PY="$(venv_python)" || die "failed to create backend/.venv"
    "$PY" -m pip install -r "$ROOT/backend/requirements.txt"
  fi

  if [ ! -d "$ROOT/frontend/node_modules" ]; then
    echo "installing frontend dependencies…"
    (cd "$ROOT/frontend" && npm install)
  fi

  echo "API:  http://127.0.0.1:8000/api/health"
  echo "site: http://127.0.0.1:3000/zh-Hant"
  echo "Ctrl+C stops FastAPI and Next.js (Mongo/Redis keep running)."

  cleanup() {
    trap - INT TERM EXIT
    if [ -n "${API_PID:-}" ]; then kill "$API_PID" 2>/dev/null || true; fi
    if [ -n "${WEB_PID:-}" ]; then kill "$WEB_PID" 2>/dev/null || true; fi
    wait 2>/dev/null || true
  }
  trap cleanup INT TERM EXIT

  (
    cd "$ROOT/backend"
    "$PY" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
  ) &
  API_PID=$!

  (
    cd "$ROOT/frontend"
    npm run dev
  ) &
  WEB_PID=$!

  wait
}

stop_dev() {
  compose_deps stop
  echo "Mongo + Redis stopped (data volume kept)"
}

case "$MODE" in
  prod) start_prod ;;
  prod-down) stop_prod ;;
  dev-down) stop_dev ;;
  dev) start_dev ;;
  *) die "invalid mode: $MODE" ;;
esac
