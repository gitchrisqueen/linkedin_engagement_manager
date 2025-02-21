#!/bin/bash

# Load the .env file (optional, Docker Compose will load this automatically if the .env is in the root)
export $(grep -v '^#' .env | xargs)

# Set environment variable NO_PREBUILT_LAMBDA =1
export NO_PREBUILT_LAMBDA=1

# Change Directory to the AWS CDK Project
cd src/cqc_lem/aws || { echo 'Could not find AWS/CDK directory to change to'; exit 1;}

# Remove all files and folders inside the cdk.out directory
echo "Removing files from cdk.out Directory..."
rm -rf cdk.out/*

echo "Removing Dangling Docker Images..."

# Remove Dangling Images
docker image prune -f --filter "dangling=true"

# Call the bootstrap command
echo "AWS CDK Bootstrapping..."
npx -p node@22 cdk bootstrap "$(aws sts get-caller-identity --query 'Account' --output text)/$(aws configure get region)" \
 --context name=CQC-LEM \
 --context accountId=${AWS_ACCOUNT_ID} \
 --context region=us-east-1 \
 --context applicationTag=dev