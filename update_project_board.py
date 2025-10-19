#!/usr/bin/env python3
"""
Update GitHub Project board to move Epic B and Epic C issues to Done status.
"""

import os
import requests
import json
from typing import Dict, List, Any

# GitHub API configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OWNER = "dj-shorts"
REPO = "analyzer"
PROJECT_NUMBER = 1  # MVP Analyzer project

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "MVP-Analyzer-Project-Updater"
}

def get_project_info():
    """Get project information."""
    url = f"https://api.github.com/orgs/{OWNER}/projects"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"❌ Error getting projects: {response.status_code}")
        print(response.text)
        return None
    
    projects = response.json()
    project = next((p for p in projects if p["name"] == "MVP Analyzer"), None)
    
    if not project:
        print("❌ MVP Analyzer project not found")
        return None
    
    print(f"✅ Found project: {project['name']} (ID: {project['id']})")
    return project

def get_project_columns(project_id: int) -> List[Dict[str, Any]]:
    """Get project columns."""
    url = f"https://api.github.com/projects/{project_id}/columns"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"❌ Error getting columns: {response.status_code}")
        return []
    
    columns = response.json()
    print("📋 Project columns:")
    for col in columns:
        print(f"  - {col['name']} (ID: {col['id']})")
    
    return columns

def get_column_cards(column_id: int) -> List[Dict[str, Any]]:
    """Get cards in a column."""
    url = f"https://api.github.com/projects/columns/{column_id}/cards"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"❌ Error getting cards: {response.status_code}")
        return []
    
    return response.json()

def move_card_to_column(card_id: int, column_id: int) -> bool:
    """Move a card to a different column."""
    url = f"https://api.github.com/projects/columns/cards/{card_id}/moves"
    data = {
        "position": "top",
        "column_id": column_id
    }
    
    response = requests.post(url, headers=HEADERS, json=data)
    
    if response.status_code == 201:
        print(f"✅ Card {card_id} moved successfully")
        return True
    else:
        print(f"❌ Error moving card {card_id}: {response.status_code}")
        print(response.text)
        return False

def get_issue_from_card(card: Dict[str, Any]) -> Dict[str, Any]:
    """Get issue information from a project card."""
    if not card.get("content_url"):
        return None
    
    response = requests.get(card["content_url"], headers=HEADERS)
    
    if response.status_code != 200:
        print(f"❌ Error getting issue: {response.status_code}")
        return None
    
    return response.json()

def main():
    """Main function to update project board."""
    print("🚀 Starting GitHub Project board update...")
    
    # Get project info
    project = get_project_info()
    if not project:
        return
    
    # Get columns
    columns = get_project_columns(project["id"])
    if not columns:
        return
    
    # Find "Done" column
    done_column = next((col for col in columns if col["name"].lower() == "done"), None)
    if not done_column:
        print("❌ 'Done' column not found")
        return
    
    print(f"✅ Found 'Done' column: {done_column['name']} (ID: {done_column['id']})")
    
    # Find "No Status" column
    no_status_column = next((col for col in columns if col["name"].lower() == "no status"), None)
    if not no_status_column:
        print("❌ 'No Status' column not found")
        return
    
    print(f"✅ Found 'No Status' column: {no_status_column['name']} (ID: {no_status_column['id']})")
    
    # Get cards from "No Status" column
    no_status_cards = get_column_cards(no_status_column["id"])
    print(f"📝 Found {len(no_status_cards)} cards in 'No Status' column")
    
    # Epic B and Epic C issue numbers
    epic_issues = [8, 9, 10]  # Epic B1, B2, C1
    
    moved_count = 0
    
    for card in no_status_cards:
        issue = get_issue_from_card(card)
        if not issue:
            continue
        
        issue_number = issue.get("number")
        if issue_number in epic_issues:
            print(f"🎯 Found Epic issue #{issue_number}: {issue['title']}")
            
            # Move card to "Done" column
            if move_card_to_column(card["id"], done_column["id"]):
                moved_count += 1
                print(f"✅ Moved Epic issue #{issue_number} to Done")
    
    print(f"\n🎉 Project board update completed!")
    print(f"📊 Moved {moved_count} Epic issues to Done status")
    
    if moved_count == len(epic_issues):
        print("✅ All Epic B and Epic C issues moved to Done!")
    else:
        print(f"⚠️  Expected to move {len(epic_issues)} issues, but moved {moved_count}")

if __name__ == "__main__":
    main()
