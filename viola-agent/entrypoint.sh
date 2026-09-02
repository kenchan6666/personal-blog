#!/bin/sh
set -eu

if [ "$(id -u)" = "0" ]; then
    mkdir -p /home/viola/.viola
    chown -R viola:viola /home/viola/.viola
    exec gosu viola "$0" "$@"
fi

dir="$HOME/.viola"
if [ -d "$dir" ] && [ ! -w "$dir" ]; then
    owner_uid=$(stat -c %u "$dir" 2>/dev/null || stat -f %u "$dir" 2>/dev/null)
    cat >&2 <<EOF
Error: $dir is not writable (owned by UID $owner_uid, running as UID $(id -u)).

Fix (pick one):
  Host:   sudo chown -R 1000:1000 ~/.viola
  Docker: docker run --user \$(id -u):\$(id -g) ...
  Podman: podman run --userns=keep-id ...
EOF
    exit 1
fi

LOG_DIR="${CS_CONTAINER_LOG_DIR:-${VIOLA_CONTAINER_LOG_DIR:-}}"
if [ -n "$LOG_DIR" ]; then
    SERVICE="${VIOLA_CONTAINER_LOG_SERVICE:-viola-api}"
    mkdir -p "$LOG_DIR" 2>/dev/null || true
    STREAM="${LOG_DIR}/viola-stream.log"
    if [ -w "$LOG_DIR" ]; then
        touch "$STREAM" 2>/dev/null || true
        if [ -x /hourly-log/hourly-log-sidecar.sh ]; then
            /hourly-log/hourly-log-sidecar.sh "$SERVICE" "$LOG_DIR" viola "$STREAM" &
        fi
        viola "$@" 2>&1 | tee -a "$STREAM"
        exit 0
    fi
    cat >&2 <<EOF
Warning: container log dir not writable: $LOG_DIR (uid=$(id -u)).
Ensure backend created _container_logs with mode 2777, or: sudo chown -R 1000:1000 $LOG_DIR
EOF
fi

exec viola "$@"
