#!/bin/bash

# Script to create GitHub issues from BACKLOG_MVP_ANALYZER.json
# Usage: ./run_create_issues.sh <GITHUB_TOKEN> [PROJECT_ID]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if GITHUB_TOKEN is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: GITHUB_TOKEN is required${NC}"
    echo "Usage: $0 <GITHUB_TOKEN> [PROJECT_ID]"
    echo ""
    echo "Steps:"
    echo "1. Get GITHUB_TOKEN from GitHub Settings > Developer settings > Personal access tokens"
    echo "2. Run: node find_project_id.mjs <GITHUB_TOKEN> to get PROJECT_ID"
    echo "3. Run this script with both values"
    exit 1
fi

GITHUB_TOKEN="$1"
PROJECT_ID="${2:-}"

echo -e "${YELLOW}Setting up environment variables...${NC}"
export GITHUB_TOKEN="$GITHUB_TOKEN"

# If PROJECT_ID is not provided, try to find it
if [ -z "$PROJECT_ID" ]; then
    echo -e "${YELLOW}PROJECT_ID not provided, trying to find it...${NC}"
    PROJECT_ID=$(node find_project_id.mjs "$GITHUB_TOKEN" | grep "PROJECT_ID:" | cut -d' ' -f2)
    
    if [ -z "$PROJECT_ID" ]; then
        echo -e "${RED}Could not find PROJECT_ID for MVP Analyzer project${NC}"
        echo "Please run manually: node find_project_id.mjs $GITHUB_TOKEN"
        exit 1
    fi
    
    echo -e "${GREEN}Found PROJECT_ID: $PROJECT_ID${NC}"
fi

export PROJECT_ID="$PROJECT_ID"

echo -e "${YELLOW}Creating GitHub issues...${NC}"
echo "Repository: dj-shorts/analyzer"
echo "Project ID: $PROJECT_ID"
echo "Labels: area:analyzer, type:feature"
echo ""

# Run the main script
node create_gh_issues_from_json.mjs \
  --repo "dj-shorts/analyzer" \
  --token "$GITHUB_TOKEN" \
  --file "BACKLOG_MVP_ANALYZER.json" \
  --labels "area:analyzer,type:feature" \
  --project-id "$PROJECT_ID"

echo -e "${GREEN}Done! Issues created successfully.${NC}"
