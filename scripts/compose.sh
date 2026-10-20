#!/usr/bin/env bash
# Run `docker compose` against the prod stack with the same files deploy.sh uses.
#   cd /opt/lem && ./scripts/compose.sh up -d cloudflared
#   cd /opt/lem && ./scripts/compose.sh ps
#
# Use this instead of typing the -f list by hand. A hand-typed list that leaves out
# docker-compose.grid.yml makes compose treat the Selenium grid as orphans, and any
# `--remove-orphans` then deletes it (see scripts/lib/compose_files.sh). It does not set IMAGE_TAG:
# to move the stack to a release, run scripts/deploy.sh <tag>.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
. "${ROOT_DIR}/scripts/lib/compose_files.sh"

# Word splitting is intended: the prefix is a command plus its -f flags.
# shellcheck disable=SC2046
exec $(lem_compose_cmd "$(lem_selenium_topology "${ROOT_DIR}/.env")") "$@"
