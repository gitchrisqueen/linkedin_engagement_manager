#!/bin/bash

# Load the .env file (optional, Docker Compose will load this automatically if the .env is in the root)
export $(grep -v '^#' .env | xargs)

# Step 1: Build and run the Docker containers
echo "Building and starting Docker containers..."
docker-compose up --build -d

# Step 2: Wait for MySQL container to be ready (optional, useful for slow startups)
echo "Waiting for MySQL to be ready..."
sleep 10  # Adjust the sleep time if needed

# Step 3: Run the Selenium automation script inside the container
echo "Executing the Selenium automation script..."
docker exec -it selenium-app python run_automation.py

# Step 4: (Optional) Add cleanup commands, if needed
# docker-compose down

echo "Execution completed!"
