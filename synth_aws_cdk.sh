#!/bin/bash

# Load the .env file (optional, Docker Compose will load this automatically if the .env is in the root)
export $(grep -v '^#' .env | xargs)

# Set environment variable NO_PREBUILT_LAMBDA =1
export NO_PREBUILT_LAMBDA=1

# Change Directory to the AWS CDK Project
cd src/cqc_lem/aws || { echo 'Could not find AWS/CDK directory to change to'; exit 1;}

# Call the synth command
echo "AWS CDK Synth..."
npx -p node@22 cdk synth