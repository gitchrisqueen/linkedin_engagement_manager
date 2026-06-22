#!/bin/bash

REPO="christopherqueenconsulting/linkedin_engagement_manager"

# Fetch open alert numbers 100 at a time and mass-dismiss them using parallel workers
while true; do
  echo "Fetching next batch of open alerts..."
  ALERTS=$(gh api "repos/$REPO/code-scanning/alerts?state=open&per_page=100" --jq '.[].number')
  
  # If no open alerts are left, break the loop
  if [ -z "$ALERTS" ]; then
    echo "All alerts successfully cleared!"
    break
  fi

  # Dismiss the current batch of 100 in parallel
  echo "$ALERTS" | xargs -I {} -P 10 gh api \
    --method PATCH \
    -H "Accept: application/vnd.github+json" \
    "/repos/$REPO/code-scanning/alerts/{}" \
    -f state="dismissed" \
    -f dismissed_reason="false positive" \
    --silent
done