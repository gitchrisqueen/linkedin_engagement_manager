#!/bin/bash
set -e

if [[ -d "aws" ]]; then
     cd src/cqc_lem/aws

    npm run cdk deploy -- \
        --context name=${AWS_APPLICATION_NAME} \
        --context accountId=${AWS_ACCOUNT_ID} \
        --context region=${AWS_REGION} \
        --context apiKey=${AWS_API_KEY} \
        --context applicationTag=${AWS_APPLICATION_TAG} \
        --all \
        --require-approval never
fi