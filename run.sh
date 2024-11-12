#!/bin/bash

# Load the .env file (optional, Docker Compose will load this automatically if the .env is in the root)
export $(grep -v '^#' .env | xargs)

# Prompt the user if they want to build the latest docker image
read -p "Do you want to build the latest Docker image? (y/n): " build_image
if [ "$build_image" == "y" ]; then
    echo "Building Docker images (${DOCKER_IMAGE_NAME}:latest)..."
    docker-compose build
fi


# Step 1: Run the Docker containers
echo "Starting Docker Containers..."
docker-compose up -d

# Step 3: (Optional) Add cleanup commands, if needed
# docker-compose down
# Remove docker dangling images
echo "Removing Dangling Docker Images..."
docker rmi $(docker images -f dangling=true -q)

printf "\nExecution completed!\n\n"

# Define arrays with URLs and titles
titles=("Streamlit Web App" "API Docs" "Flower Celery Monitoring" "Docker Chrome VNC" "LinkedIn Preview" "Open AI usage Cost")
urls=("http://localhost:8501" "http://localhost:8000/docs" "http://localhost:8555" "http://localhost:4444" "http://localhost:8081" "https://platform.openai.com/usage")


# Function to print the separator line
# shellcheck disable=SC2120
print_separator() {
    local num_equals=${1:-60}
    printf "%${num_equals}s\n" | tr ' ' '='
}

# Print the separator line
print_separator

# Print the titles and URLs in a tabular format
for i in "${!titles[@]}"; do
    printf "%-30s\t%s\n" "${titles[$i]}" "${urls[$i]}"
done

# Print the separator line again
print_separator

# Prompt the user if they want to open all the urls
#read -p "Do you want to Open these urls? (y/n): " open_chrome
#if [ "$open_chrome" == "y" ]; then
#    open -a "Google Chrome" "http://localhost:8501" "http://localhost:8000/docs" "http://localhost:5555" "http://localhost:4444" "http://localhost:8081"
#fi

# Prompt the user if they want to open all the urls
read -p "Do you want to Open these urls? (y/n): " open_chrome
if [ "$open_chrome" == "y" ]; then
    osascript open_urls.scpt
fi