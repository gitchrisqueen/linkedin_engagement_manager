#!/bin/bash

# Load environment variables from .env file
export $(grep -v '^#' .env | xargs)

SCRIPT_DIR=$(dirname "$0")
NGROK_PLAN="${NGROK_PLAN:-off}"

case "$NGROK_PLAN" in
  free)
    TEMPLATE="$SCRIPT_DIR/ngrok-config-template-free.yml"
    ;;
  paid)
    TEMPLATE="$SCRIPT_DIR/ngrok-config-template.yml"
    ;;
  *)
    echo "NGROK_PLAN=${NGROK_PLAN} — skipping ngrok config generation."
    exit 0
    ;;
esac

envsubst < "$TEMPLATE" > "$SCRIPT_DIR/ngrok-config.yml"
echo "Ngrok config generated from ${TEMPLATE} (plan: ${NGROK_PLAN})."
