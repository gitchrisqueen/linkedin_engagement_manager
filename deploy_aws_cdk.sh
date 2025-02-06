#!/bin/bash

# Load the .env file (optional, Docker Compose will load this automatically if the .env is in the root)
export $(grep -v '^#' .env | xargs)

# Set environment variable NO_PREBUILT_LAMBDA =1
export NO_PREBUILT_LAMBDA=1

# Prompt user to deply sequentially or all and run different commands based on user input. Start wiht a defautl so user can just hit enter
echo "Would you like to deploy sequentially or all at once? (s/a)"
read -r deploy_choice
if [ "$deploy_choice" = "s" ]; then
    echo "Deploying sequentially..."
    poetry run python -m cqc_lem.aws.deploy
else
    echo "Deploying all at once..."
    poetry run python -m cqc_lem.aws.deploy --all
fi
