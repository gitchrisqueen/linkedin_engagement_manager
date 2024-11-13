#!/bin/bash

# Load environment variables from .env file
export $(grep -v '^#' .env | xargs)

# Replace environment variables in the template and create ngrok-config.yml
envsubst < ngrok-config-template.yml > ngrok-config.yml

echo "ngrok-config.yml has been generated."