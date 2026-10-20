# shellcheck shell=bash
# The compose command for the prod stack, for scripts other than deploy.sh. Source it; do not run it.
#
# docker-compose.grid.yml defines the Selenium hub, the chrome nodes and the debug node. A compose
# command run without it treats those services as orphans, and `up --remove-orphans` then deletes
# the whole grid (2026-10-20: an `up -d cloudflared` run with base + prod only removed the hub,
# every chrome node and the debug node). deploy.sh resolves the same list inline;
# tests/unit/scripts/test_compose_files.py fails the build if the two disagree.

# Print the Selenium topology: an exported $SELENIUM_TOPOLOGY wins, then the .env value, then grid.
# Anything other than `standalone` or `grid` is named on stderr and taken as grid, as deploy.sh does.
lem_selenium_topology() {  # $1 = path to the compose .env
  local val="${SELENIUM_TOPOLOGY:-}"
  if [[ -z "${val}" && -f "$1" ]]; then
    val="$(sed -nE "s/^[[:space:]]*SELENIUM_TOPOLOGY=[\"']?([^\"'#[:space:]]*).*/\1/p" "$1" | tail -n1)"
  fi
  val="$(printf '%s' "${val:-grid}" | tr '[:upper:]' '[:lower:]')"
  case "${val}" in
    standalone|grid) ;;
    *) echo "WARN: unrecognised SELENIUM_TOPOLOGY='${val}' — using 'grid'" >&2
       val="grid" ;;
  esac
  printf '%s\n' "${val}"
}

# Print the `docker compose -f …` prefix for a topology from lem_selenium_topology.
lem_compose_cmd() {  # $1 = standalone | grid
  local cmd="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
  [[ "$1" == "standalone" ]] || cmd="${cmd} -f docker-compose.grid.yml"
  printf '%s\n' "${cmd}"
}

# Write IMAGE_TAG=<tag> into the compose .env: replace the existing line, or append one. deploy.sh
# does the same after a deploy (persist_image_tag). Without it, a later manual compose `up` or a
# reboot reads the old tag from .env and puts app services back on the release just rolled back.
lem_persist_image_tag() {  # $1 = path to the compose .env, $2 = tag
  if [[ -f "$1" ]] && grep -qE '^IMAGE_TAG=' "$1"; then
    sed -i -E "s|^IMAGE_TAG=.*|IMAGE_TAG=$2|" "$1"
  else
    echo "IMAGE_TAG=$2" >> "$1"
  fi
}
