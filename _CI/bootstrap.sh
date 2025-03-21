#!/bin/bash
set -e

if [[ -d "aws" ]]; then
    cd src/cqc_lem/aws

    echo "Install AWS CDK version ${CDK_VERSION}.."

    npm i -g aws-cdk@${CDK_VERSION}
    npm ci --include=dev

    echo "Synthesize cqc_lem_aws.."

    npm run cdk bootstreap -- \
        --quiet \
        --context name=${AWS_APPLICATION_NAME} \
        --context accountId=${AWS_ACCOUNT_ID} \
        --context region=${AWS_REGION} \
        --context apiKey=${AWS_API_KEY} \
        --context applicationTag=${AWS_APPLICATION_TAG}
fi