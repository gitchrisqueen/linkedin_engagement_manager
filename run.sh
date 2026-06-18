#!/bin/bash

# Load the .env file (optional, Docker Compose will load this automatically if the .env is in the root)
export $(grep -v '^#' .env | xargs)

NGROK_PLAN="${NGROK_PLAN:-off}"

# Step 1: Prompt the user if they want to build the latest docker image
read -p "Do you want to build the latest Docker image(s)? (y/n): " build_image
if [ "$build_image" == "y" ]; then
    echo "Building Docker images (${DOCKER_IMAGE_NAME}:latest)..."
    docker compose build
    read -p "Do you want to push the built Docker image(s) to Docker Hub? (y/n): " push_image
    if [ "$push_image" == "y" ]; then
      # Push the main app image (shared by web_app, api, celery_worker, celery_beat, flower)
      docker compose push web_app
    fi
fi

# Step 2: Run the Docker containers
echo "Starting Docker Containers..."
docker compose up -d --remove-orphans

# Step 3: Clean up old images and build cache
echo "Cleaning up old Docker images older than 7 days..."
docker image prune -a --filter "until=168h" -f

echo "Cleaning up Docker build cache older than 7 days..."
docker builder prune --filter "until=168h" -f

printf "\nExecution completed!\n\n"

# Step 4 and Step 5: Start NGrok Tunnels based on NGROK_PLAN
if [ "$NGROK_PLAN" != "off" ]; then
    if [ -z "$NGROK_AUTH_TOKEN" ]; then
        printf "Warning: NGROK_PLAN=%s but NGROK_AUTH_TOKEN is not set — skipping NGrok.\n" "$NGROK_PLAN"
        NGROK_PLAN="off"
    else
        # Generate the config for the selected plan
        ./generate-ngrok-config.sh

        printf "Starting NGrok Tunnels (plan: %s)...\n" "$NGROK_PLAN"
        mkdir -p ./logs
        touch ./logs/ngrok.log
        pkill -f ngrok || true
        sleep 3  # wait for cloud session to deregister (ERR_NGROK_108)
        ngrok start --config ./ngrok-config.yml --all --log='stdout' > ./logs/ngrok.log 2>&1 &
        NGROK_PID=$!

        # Brief wait to catch immediate startup errors
        sleep 3
        if ! kill -0 "$NGROK_PID" 2>/dev/null; then
            printf "\nWarning: NGrok exited unexpectedly. Relevant errors from ./logs/ngrok.log:\n"
            grep -E "lvl=(eror|crit)|^ERROR" ./logs/ngrok.log | tail -5 | sed 's/^/  /'
            printf "\nFalling back to local URLs.\n\n"
            NGROK_PLAN="off"
        else
            printf "NGrok running (PID %s). Tunnel URLs below or at http://localhost:%s\n\n" "$NGROK_PID" "$NGROK_UI_PORT"
        fi
    fi
fi

# Step 6: Build URL display arrays based on NGROK_PLAN
titles=("React Web App" "API Docs" "Flower Celery Monitoring" "Docker Chrome VNC")

case "$NGROK_PLAN" in
  paid)
    urls=(
      "https://${NGROK_CUSTOM_DOMAIN}"
      "https://${NGROK_CUSTOM_DOMAIN}/docs"
      "https://${NGROK_FLOWER_PREFIX}.${NGROK_FREE_DOMAIN}"
      "https://${NGROK_CHROME_PREFIX}.${NGROK_FREE_DOMAIN}"
    )
    titles+=("Ngrok Web Interface")
    urls+=("http://localhost:${NGROK_UI_PORT}")
    ;;
  free)
    # Free plan: 2 tunnels (app=static domain, flower=dynamic; chrome=local only)
    urls=(
      "https://${NGROK_CUSTOM_DOMAIN}"
      "https://${NGROK_CUSTOM_DOMAIN}/docs"
      "Dynamic — see http://localhost:${NGROK_UI_PORT}"
      "http://localhost:7900 (local only)"
    )
    titles+=("Ngrok Web Interface")
    urls+=("http://localhost:${NGROK_UI_PORT}")
    ;;
  *)
    urls=(
      "http://localhost:${API_PORT}"
      "http://localhost:${API_PORT}/docs"
      "http://localhost:${CELERY_FLOWER_PORT}"
      "http://localhost:7900"
    )
    ;;
esac

# Reference URLs (always shown)
reference_titles=("PostHog (observability)" "OpenAI (usage cost)" "RunwayML (video gen)" "Replicate (image gen)")
reference_urls=("https://us.posthog.com/" "https://platform.openai.com/usage" "https://app.runwayml.com/" "https://replicate.com/")
titles+=("${reference_titles[@]}")
urls+=("${reference_urls[@]}")

# Function to print the titles and URLs with a dynamic separator line
print_urls() {
    local -a titles=("${!1}")
    local -a urls=("${!2}")

    local max_length=0
    local print_contents=()
    local max_title_length=0

    for title in "${titles[@]}"; do
        if (( ${#title} > max_title_length )); then
            max_title_length=${#title}
        fi
    done

    for i in "${!titles[@]}"; do
        local line
        line=$(printf "%-${max_title_length}s\t%s" "${titles[$i]}" "${urls[$i]}")
        local length=${#line}
        if (( length > max_length )); then
            max_length=$length
        fi
        print_contents+=("$line")
    done

    (( max_length += 10 ))

    local separator=$(printf "%${max_length}s\n" | tr ' ' '=')

    local service_padding=$(( ((max_title_length + 4 ) / 2) - (7/2) ))
    local service_padding_right=$(( max_title_length - service_padding + 5 ))
    local url_remainder=$(( max_length - service_padding - service_padding_right - 7 ))
    local url_padding=$(( ((max_length - url_remainder ) / 2) + (3/2) ))
    local url_padding_right=$(( url_remainder - url_padding  ))

    local header
    header=$(printf "| %*s%-*s | %*s%-*s |" $service_padding " " $service_padding_right "Service" $url_padding " " $url_padding_right "URL")

    printf "\n\n%s\n%s\n%s\n%s\n%s\n\n\n" "$separator" "$header" "$separator" "$(printf "%s\n" "${print_contents[@]}")" "$separator"
}

print_urls "titles[@]" "urls[@]"

# Remove Dangling Images
docker image prune -f --filter "dangling=true"
