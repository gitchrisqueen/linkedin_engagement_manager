#!/usr/bin/env bash
# Generate a few AI image/video variants for review and print their public URLs.
# Does NOT mutate any post. Mirrors regen_approved_assets.sh (reads creds from the
# deployed env, curls the admin endpoint on the running container).
#
# Usage (run as root on the VPS):
#   sudo bash scripts/generate_media_variants.sh --text "AI in healthcare" --user-id 1
#   sudo bash scripts/generate_media_variants.sh --post-id 42
#   sudo bash scripts/generate_media_variants.sh --topic "supply chain resilience"
set -euo pipefail

ENV=${LEM_ENV_FILE:-/opt/lem/.env}
BASE=${LEM_BASE_URL:-https://lem.christopherqueenconsulting.com}

POST_ID="" TEXT="" TOPIC="" USER_ID=""
while [ $# -gt 0 ]; do
  case "$1" in
    --post-id) POST_ID="$2"; shift 2 ;;
    --text)    TEXT="$2";    shift 2 ;;
    --topic)   TOPIC="$2";   shift 2 ;;
    --user-id) USER_ID="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$POST_ID" ] && [ -z "$TEXT" ] && [ -z "$TOPIC" ]; then
  echo "✗ Provide one of: --post-id N | --text \"...\" | --topic \"...\"" >&2
  exit 2
fi

TOKEN=$(grep '^API_ACCESS_TOKENS=' "$ENV" | cut -d= -f2- | cut -d, -f1)
ADMIN=$(grep '^ADMIN_SECRET=' "$ENV" | cut -d= -f2-)

# --- Guard: endpoint must exist (deploy this feature first) -----------------
PROBE=$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$BASE/api/admin/generate-media-variants" \
  -H "Authorization: Bearer $TOKEN" -H "x-admin-secret: $ADMIN" \
  -H 'Content-Type: application/json' -d '{}' 2>/dev/null || echo 000)
# 404 = no route; 405 = the SPA catch-all GET swallowed the path (endpoint not built).
# A deployed endpoint returns 422 (bad body) / 401 / 403 for this probe.
if [ "$PROBE" = "404" ] || [ "$PROBE" = "405" ]; then
  echo "✗ /api/admin/generate-media-variants not available (HTTP $PROBE) — this feature" >&2
  echo "  isn't deployed yet. Merge + deploy the media-variants PR, then re-run." >&2
  exit 1
fi

# --- Build JSON body (python for safe escaping) -----------------------------
BODY=$(POST_ID="$POST_ID" TEXT="$TEXT" TOPIC="$TOPIC" USER_ID="$USER_ID" python3 - <<'PY'
import json, os
body = {}
if os.environ.get("POST_ID"): body["post_id"] = int(os.environ["POST_ID"])
if os.environ.get("TEXT"):    body["text"] = os.environ["TEXT"]
if os.environ.get("TOPIC"):   body["topic"] = os.environ["TOPIC"]
if os.environ.get("USER_ID"): body["user_id"] = int(os.environ["USER_ID"])
print(json.dumps(body))
PY
)

echo "→ Generating variants (this runs image + Gen-4 Turbo video, ~1-2 min each)…"
RESP=$(curl -sS -w $'\n%{http_code}' -X POST "$BASE/api/admin/generate-media-variants" \
  -H "Authorization: Bearer $TOKEN" -H "x-admin-secret: $ADMIN" \
  -H 'Content-Type: application/json' -d "$BODY")
CODE=$(printf '%s' "$RESP" | tail -n1)
RESP=$(printf '%s' "$RESP" | sed '$d')

# --- Error responses: print the raw body so failures are never hidden -------
if [ "$CODE" != "200" ]; then
  echo "✗ HTTP $CODE — request failed:" >&2
  echo "$RESP" | python3 -m json.tool 2>/dev/null || echo "$RESP"
  exit 1
fi

# --- Pretty-print URLs + cost (success: detail is the payload object) -------
if command -v jq >/dev/null 2>&1; then
  echo "$RESP" | jq -r '
    .detail as $d
    | "Batch: \($d.batch_id)   Est. cost: $\($d.total_estimated_cost_usd)",
      ($d.variants[] | "  variant: image=\(.image_url // "—")  video=\(.video_url // "—")  \(if .error then "ERROR: \(.error)" else "" end)"),
      "Metadata: \($d.metadata_url)"'
else
  echo "$RESP" | python3 -m json.tool
fi
