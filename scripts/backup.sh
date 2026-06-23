#!/usr/bin/env bash
# Nightly backup of the MySQL database + Chrome profile volume.
# Run from cron on the VPS, e.g.:
#   0 3 * * * cd /opt/lem && ./scripts/backup.sh >> logs/backup.log 2>&1
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Load env for DB creds (MYSQL_*).
set -a; [[ -f .env ]] && . ./.env; set +a

BACKUP_DIR="${BACKUP_DIR:-${ROOT_DIR}/backups}"
RETAIN_DAYS="${RETAIN_DAYS:-7}"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "[backup ${STAMP}] dumping MySQL ${MYSQL_DATABASE}"
docker exec "${MYSQL_HOST:-mysql_db}" \
  mysqldump --single-transaction --quick --routines --triggers \
  -u root -p"${MYSQL_ROOT_PASSWORD}" "${MYSQL_DATABASE}" \
  | gzip > "${BACKUP_DIR}/db-${STAMP}.sql.gz"

echo "[backup ${STAMP}] archiving chrome-profile volume"
docker run --rm \
  -v linkedin_engagement_manager_chrome-profile:/data:ro \
  -v "${BACKUP_DIR}:/backup" \
  alpine tar czf "/backup/chrome-profile-${STAMP}.tar.gz" -C /data . 2>/dev/null || \
  echo "[backup] chrome-profile volume not found (named differently?) — skipping"

echo "[backup ${STAMP}] pruning backups older than ${RETAIN_DAYS} days"
find "$BACKUP_DIR" -name '*.gz' -mtime "+${RETAIN_DAYS}" -delete

# Optional: push to Cloudflare R2 / S3 if rclone is configured.
if command -v rclone >/dev/null 2>&1 && [[ -n "${BACKUP_REMOTE:-}" ]]; then
  echo "[backup ${STAMP}] syncing to ${BACKUP_REMOTE}"
  rclone copy "$BACKUP_DIR" "$BACKUP_REMOTE" --max-age "${RETAIN_DAYS}d"
fi
echo "[backup ${STAMP}] done"
