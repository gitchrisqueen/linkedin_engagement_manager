#!/usr/bin/env bash
# Manual rollback to a previously deployed image tag.
#   ssh deploy@vps 'cd /opt/lem && ./scripts/rollback.sh v1.2.2'
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TAG="${1:?Usage: rollback.sh <image-tag>}"
# Same file list as deploy.sh: without docker-compose.grid.yml, the `--remove-orphans` below would
# delete the Selenium grid (scripts/lib/compose_files.sh).
. "${ROOT_DIR}/scripts/lib/compose_files.sh"
COMPOSE="$(lem_compose_cmd "$(lem_selenium_topology "${ROOT_DIR}/.env")")"

echo "[rollback] checking out ${TAG}"
git fetch --tags --quiet origin
git checkout --quiet "${TAG}" 2>/dev/null || git checkout --quiet "tags/${TAG}"

export IMAGE_TAG="${TAG}"
${COMPOSE} pull
${COMPOSE} up -d --remove-orphans
echo "${TAG}" > "${ROOT_DIR}/.last_good_tag"
echo "[rollback] now running ${TAG}"
