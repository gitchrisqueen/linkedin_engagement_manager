#!/bin/bash

# Load environment variables from .env file
export $(grep -v '^#' .env | xargs)

# Get the directory of the current script
SCRIPT_DIR=$(dirname "$0")

# Replace environment variables in the template and create ngrok-config.yml
envsubst < "$SCRIPT_DIR/ngrok-config-template.yml" > "$SCRIPT_DIR/ngrok-config.yml"

echo "Ngrok config file has been generated."