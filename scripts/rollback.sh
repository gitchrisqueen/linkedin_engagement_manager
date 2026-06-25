#!/usr/bin/env bash
# Manual rollback to a previously deployed image tag.
#   ssh deploy@vps 'cd /opt/lem && ./scripts/rollback.sh v1.2.2'
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TAG="${1:?Usage: rollback.sh <image-tag>}"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

echo "[rollback] checking out ${TAG}"
git fetch --tags --quiet origin
git checkout --quiet "${TAG}" 2>/dev/null || git checkout --quiet "tags/${TAG}"

export IMAGE_TAG="${TAG}"
${COMPOSE} pull
${COMPOSE} up -d --remove-orphans
echo "${TAG}" > "${ROOT_DIR}/.last_good_tag"
echo "[rollback] now running ${TAG}"
