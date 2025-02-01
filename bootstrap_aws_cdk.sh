#!/bin/bash

# Set environment variable NO_PREBUILT_LAMBDA =1
export NO_PREBUILT_LAMBDA=1

# Change Directory to the AWS CDK Project
cd src/cqc_lem/aws || { echo 'Could not find AWS/CDK directory to change to'; exit 1;}

# Remove all files and folders inside the cdk.out direcotry
echo "Removing files from cdk.out Directory..."
rm -rf cdk.out/*

echo "Removing Dangling Docker Images..."
docker rmi $(docker images -f dangling=true -q)

# Call the bootstrap command
echo "AWS CDK Bootstrapping..."
npx -p node@22 cdk bootstrap "$(aws sts get-caller-identity --query 'Account' --output text)/$(aws configure get region)" \
 --context name=CQC-LEM \
 --context accountId=103658592769 \
 --context region=us-east-1 \
 --context applicationTag=dev