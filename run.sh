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
echo "Starting Docker containers..."
docker-compose up -d

# Step 3: (Optional) Add cleanup commands, if needed
# docker-compose down

# Print pertinent information
echo "=============================="
echo "Streamlit Web App: http://localhost:8501/"
echo "API Docs: http://localhost:8000/docs"
echo "Flower Celery Monitoring: http://localhost:5555"
echo "Docker Chrome VNC: http://localhost:7900/?autoconnect=1&resize=scale&password=secret"
echo "=============================="


echo "Execution completed!"
