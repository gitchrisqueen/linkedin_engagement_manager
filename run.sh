#!/bin/bash

# Load the .env file (optional, Docker Compose will load this automatically if the .env is in the root)
export $(grep -v '^#' .env | xargs)

# Step 1: Prompt the user if they want to build the latest docker image
read -p "Do you want to build the latest Docker image? (y/n): " build_image
if [ "$build_image" == "y" ]; then
    echo "Building Docker images (${DOCKER_IMAGE_NAME}:latest)..."
    docker-compose build
    # Push all built images
    #docker-compose push
    # Push the web app image
    docker-compose push web-app
     # Push the web the linkedin preview image
    #docker-compose push linkedin-preview
fi


# Step 2: Run the Docker containers
echo "Starting Docker Containers..."
docker-compose up -d

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
titles=("Streamlit Web App" "API Docs" "Flower Celery Monitoring" "Docker Chrome VNC" "LinkedIn Preview" "Ngrok Web Interface" "Open AI usage Cost")
#Local URLs
urls_local=("http://localhost:8501" "http://localhost:8000/docs" "http://localhost:8555" "http://localhost:4444" "http://localhost:8081" "N/A" "https://platform.openai.com/usage")
# NGrok URLs
urls_ngrok=("https://${NGROK_CUSTOM_DOMAIN}" "https://${NGROK_API_PREFIX}.${NGROK_FREE_DOMAIN}/docs" "https://${NGROK_FLOWER_PREFIX}.${NGROK_FREE_DOMAIN}" "https://${NGROK_CHROME_PREFIX}.${NGROK_FREE_DOMAIN}" "https://${NGROK_LIPREVIEW_PREFIX}.${NGROK_FREE_DOMAIN}" "http://0.0.0.0:4040" "https://platform.openai.com/usage")
# set urls variable if NGROK_AUTH_TOKEN env is not empty
urls=("${urls_local[@]}")
[ -n "$NGROK_AUTH_TOKEN" ] && urls=("${urls_ngrok[@]}")


# Function to print the separator line
# shellcheck disable=SC2120
print_separator() {
    local num_equals=${1:-60}
    printf "%${num_equals}s\n" | tr ' ' '='
}

# Step 7: Print the URLs

# Print the separator line
print_separator

# Print the titles and URLs in a tabular format
for i in "${!titles[@]}"; do
    printf "%-30s\t%s\n" "${titles[$i]}" "${urls[$i]}"
done

# Print the separator line again
print_separator

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