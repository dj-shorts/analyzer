#!/bin/bash

# Script to get PROJECT_ID using curl
# Usage: ./get_project_id.sh YOUR_GITHUB_TOKEN

if [ -z "$1" ]; then
    echo "Usage: $0 <GITHUB_TOKEN>"
    exit 1
fi

TOKEN="$1"

echo "Fetching projects for organization dj-shorts..."

curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { organization(login: \"dj-shorts\") { projectsV2(first: 20) { nodes { id title url } } } }"
  }' \
  https://api.github.com/graphql | jq -r '.data.organization.projectsV2.nodes[] | select(.title | test("MVP Analyzer|Analyzer"; "i")) | "Project: " + .title + "\nPROJECT_ID: " + .id + "\nURL: " + .url'

# If jq is not available, use this simpler version:
# curl -X POST \
#   -H "Authorization: Bearer $TOKEN" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "query": "query { organization(login: \"dj-shorts\") { projectsV2(first: 20) { nodes { id title url } } } }"
#   }' \
#   https://api.github.com/graphql
