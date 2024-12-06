#!/bin/bash

# Load the .env file (optional, Docker Compose will load this automatically if the .env is in the root)
export $(grep -v '^#' .env | xargs)

# Step 1a: Prompt the user if they want to build the latest docker image
read -p "Do you want to build the latest Docker image(s)? (y/n): " build_image
if [ "$build_image" == "y" ]; then
    echo "Building Docker images (${DOCKER_IMAGE_NAME}:latest)..."
    docker-compose build
    read -p "Do you want to push the built Docker image(s)? (y/n): " push_image
    if [ "$push_image" == "y" ]; then
      # Push all built images
      #docker-compose push
      # Push the web app image
      docker-compose push web_app
      # Push the web the linkedin preview image
      #docker-compose push linkedin-preview
    fi
fi

# Step 1b: Build the prometheus config
echo "Generating Prometheus Configs..."
./compose/local/prometheus/generate-prometheus-config.sh

# Step 2: Run the Docker containers
echo "Starting Docker Containers..."
docker-compose up -d --remove-orphans

# Step 3: (Optional) Add cleanup commands, if needed
# docker-compose down
# Remove docker dangling images
echo "Removing Dangling Docker Images..."
docker rmi $(docker images -f dangling=true -q)

printf "\nExecution completed!\n\n"

# Step 4 and Step 5: Generate NGrok Config and Start NGrok Tunnels if NGROK_AUTH_TOKEN is set
if [ -n "$NGROK_AUTH_TOKEN" ]; then
    # Step 4 (Optional): Generate NGrok Config
    ./generate-ngrok-config.sh

    # Step 5 (Optional): Start NGrok Tunnels
    printf "Starting NGrok Tunnels...\n"
    # Make sure logs/ngrok.log exists
    touch ./logs/ngrok.log
    pkill -f ngrok || true
    # Start ngrok with the generated config file and then remove it
    ngrok start --config ./ngrok-config.yml --all --log='stdout' > ./logs/ngrok.log &
fi
# Step 6: Define arrays with URLs and titles
titles=("Streamlit Web App" "API Docs" "Flower Celery Monitoring" "Docker Chrome VNC" "LinkedIn Preview" "Ngrok Web Interface" "Jaeger Error Tracing")
#Local URLs
urls_local=("http://localhost:${STREAMLIT_PORT}" "http://localhost:${API_PORT}/docs" "http://localhost:${CELERY_FLOWER_PORT}" "http://localhost:${SELENIUM_HUB_PORT}" "http://localhost:${LI_PREVIEW_PORT}" "N/A" "http://localhost:${JAEGER_UI_PORT}")
# NGrok URLs
urls_ngrok=("https://${NGROK_CUSTOM_DOMAIN}" "https://${NGROK_API_PREFIX}.${NGROK_FREE_DOMAIN}/docs" "https://${NGROK_FLOWER_PREFIX}.${NGROK_FREE_DOMAIN}" "https://${NGROK_CHROME_PREFIX}.${NGROK_FREE_DOMAIN}" "https://${NGROK_LIPREVIEW_PREFIX}.${NGROK_FREE_DOMAIN}" "http://0.0.0.0:${NGROK_UI_PORT}" "https://${NGROK_JAEGER_PREFIX}.${NGROK_FREE_DOMAIN}")
# set urls variable if NGROK_AUTH_TOKEN env is not empty
urls=("${urls_local[@]}")
[ -n "$NGROK_AUTH_TOKEN" ] && urls=("${urls_ngrok[@]}")
# Urls for reference
reference_titles=("OpenAI (usage cost)" "RunwayML (video gen)" "Replicate (image gen)")
reference_urls=("https://platform.openai.com/usage" "https://app.runwayml.com/" "https://replicate.com/")
# Append the reference titles and urls to the existing arrays
titles+=("${reference_titles[@]}")
urls+=("${reference_urls[@]}")

# Function to print the titles and URLs with a dynamic separator line
print_urls() {
    # shellcheck disable=SC2178
    #local -n titles="$1"
    # shellcheck disable=SC2178
    #local -n urls="$2"

    local -a titles=("${!1}")
    local -a urls=("${!2}")

    #echo "Array 1: ${titles[@]}"
    #echo "Array 2: ${urls[@]}"

    # Initialize variables
    local max_length=0
    local print_contents=()
    local max_title_length=0

    # Find the longest title length
    for title in "${titles[@]}"; do
        if (( ${#title} > max_title_length )); then
            max_title_length=${#title}
        fi
    done

    # Build the print contents and find the longest title-URL combination
    for i in "${!titles[@]}"; do
        local line
        line=$(printf "%-${max_title_length}s\t%s" "${titles[$i]}" "${urls[$i]}")
        local length=${#line}
        if (( length > max_length )); then
            max_length=$length
        fi
        print_contents+=("$line")
    done

    # Add padding to the max length
    (( max_length += 10 ))

    # Create the separator line
    local separator=$(printf "%${max_length}s\n" | tr ' ' '=')

    # Calculate padding for centered headers
    local service_padding=$(( ((max_title_length + 4 ) / 2) - (7/2) )) # Half the title length minus half the word "Service" length
    local service_padding_right=$(( max_title_length - service_padding + 5 )) # The rest of the padding + half the max_length padding
    local url_remainder=$(( max_length - service_padding - service_padding_right - 7 )) # The remaining space for the URL
    local url_padding=$(( ((max_length - url_remainder ) / 2) + (3/2) )) # Half the URL remainder length minus half the word "URL" length
    local url_padding_right=$(( url_remainder - url_padding  )) # The rest of the padding

    # Create the header with centered text
    local header
    header=$(printf "| %*s%-*s | %*s%-*s |" $service_padding " " $service_padding_right "Service" $url_padding " " $url_padding_right "URL")

    # Print the separator, header, separator, contents, and separator again
    printf "\n\n%s\n%s\n%s\n%s\n%s\n\n\n" "$separator" "$header" "$separator" "$(printf "%s\n" "${print_contents[@]}")" "$separator"

}

# Pass the arrays by reference
print_urls "titles[@]" "urls[@]"


# Step Final: Prompt the user if they want to open all the urls
#read -p "Do you want to Open these urls? (y/n): " open_chrome
#if [ "$open_chrome" == "y" ]; then
#    open -a "Google Chrome" "http://localhost:8501" "http://localhost:8000/docs" "http://localhost:5555" "http://localhost:4444" "http://localhost:8081"
#fi

# Step Final: Prompt the user if they want to open all the urls
read -p "Do you want to Open these urls? (y/n): " open_chrome
if [ "$open_chrome" == "y" ]; then
    osascript open_urls.scpt
fi