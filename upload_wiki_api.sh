#!/bin/bash

# Script to upload Wiki pages using GitHub API
# This script will attempt to create Wiki pages programmatically

set -e

REPO="dj-shorts/analyzer"
WIKI_DIR="wiki_pages"

echo "🚀 Attempting to upload Wiki pages to GitHub..."

# Function to upload a single page
upload_page() {
    local filename="$1"
    local pagename="$2"
    
    echo "📄 Uploading $pagename..."
    
    # Try to create/update the page
    if gh api --method PUT \
        -H "Accept: application/vnd.github.v3+json" \
        "/repos/$REPO/wiki/$pagename" \
        -f title="$pagename" \
        -f body="$(cat "$filename")" \
        --silent; then
        echo "✅ Successfully uploaded $pagename"
    else
        echo "❌ Failed to upload $pagename"
        return 1
    fi
}

# Upload pages in order
echo "📤 Starting upload process..."

# Try to upload Home page first
if upload_page "$WIKI_DIR/Home.md" "Home"; then
    echo "🎉 Home page created successfully!"
    echo "🌐 You can now view it at: https://github.com/$REPO/wiki"
    echo ""
    echo "📋 Continuing with other pages..."
    
    # Upload remaining pages
    upload_page "$WIKI_DIR/Setup-Guide.md" "Setup-Guide"
    upload_page "$WIKI_DIR/Docker-Guide.md" "Docker-Guide"
    upload_page "$WIKI_DIR/Monitoring-Setup.md" "Monitoring-Setup"
    upload_page "$WIKI_DIR/Manual-Download-Migration.md" "Manual-Download-Migration"
    upload_page "$WIKI_DIR/CI-CD-Pipeline.md" "CI-CD-Pipeline"
    upload_page "$WIKI_DIR/Testing-Guide.md" "Testing-Guide"
    upload_page "$WIKI_DIR/TestSprite-Integration.md" "TestSprite-Integration"
    upload_page "$WIKI_DIR/Epic-Reports.md" "Epic-Reports"
    
    echo ""
    echo "🎉 All Wiki pages uploaded successfully!"
    echo "🌐 View your Wiki at: https://github.com/$REPO/wiki"
else
    echo "❌ Failed to create Home page. Wiki may not be initialized."
    echo ""
    echo "🔧 Manual steps required:"
    echo "1. Go to https://github.com/$REPO/wiki"
    echo "2. Click 'Create the first page'"
    echo "3. Copy content from $WIKI_DIR/Home.md"
    echo "4. Use 'Home' as the page title"
    echo "5. Save the page"
    echo "6. Then run this script again to upload remaining pages"
fi
