#!/usr/bin/env bash
# Daily backup of the production stack:
#   - mongodump of every database (gzip archive)
#   - tarball of runtime files (data/media uploads, data/resumes PDFs)
# Written to $BACKUP_DIR (default /mnt/disks/data/backups), kept for
# $BACKUP_RETENTION_DAYS days (default 14). Run by personal-blog-backup.timer.
#
# Restore (into the running stack — overwrites matching collections):
#   docker compose -f docker-compose.prod.yml --env-file deployment/.env exec -T mongo \
#     mongorestore --archive --gzip --drop < /mnt/disks/data/backups/mongo-<ts>.archive.gz
#   tar -xzf /mnt/disks/data/backups/files-<ts>.tar.gz -C data/
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-/mnt/disks/data/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

compose_prod() {
  docker compose -f "$ROOT/docker-compose.prod.yml" --env-file "$DIR/.env" "$@"
}

umask 077
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

mongo_out="$BACKUP_DIR/mongo-$TS.archive.gz"
files_out="$BACKUP_DIR/files-$TS.tar.gz"

echo "[backup] mongodump → $mongo_out"
compose_prod exec -T mongo mongodump --archive --gzip --quiet >"$mongo_out.part"
if [ ! -s "$mongo_out.part" ]; then
  echo "[backup] mongodump produced an empty archive" >&2
  rm -f "$mongo_out.part"
  exit 1
fi
mv "$mongo_out.part" "$mongo_out"

echo "[backup] files → $files_out"
targets=()
for sub in media resumes; do
  [ -d "$ROOT/data/$sub" ] && targets+=("$sub")
done
if [ "${#targets[@]}" -gt 0 ]; then
  # -h follows the data/ symlink target so the real files are archived.
  tar -czhf "$files_out.part" -C "$ROOT/data" "${targets[@]}"
  mv "$files_out.part" "$files_out"
fi

echo "[backup] pruning archives older than $RETENTION_DAYS days"
find "$BACKUP_DIR" -maxdepth 1 -type f \
  \( -name 'mongo-*.archive.gz' -o -name 'files-*.tar.gz' -o -name '*.part' \) \
  -mtime +"$((RETENTION_DAYS - 1))" -delete

ls -lh "$mongo_out" "$files_out" 2>/dev/null || true
echo "[backup] done $TS"
