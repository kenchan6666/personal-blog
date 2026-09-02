#!/usr/bin/env bash
# Stop the stack started by deployment/start.sh.
#   bash deployment/stop.sh          stop local Mongo + Redis
#   bash deployment/stop.sh --prod   stop the nginx compose stack
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
exec bash "$DIR/start.sh" --down "$@"
