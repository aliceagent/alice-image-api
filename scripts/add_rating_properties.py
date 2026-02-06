#!/usr/bin/env python3
"""
Add rating properties to the Notion Gallery database.
Run once to set up the database schema for image ratings.

Properties added:
- Rating Score (Number) - Cumulative score (likes - dislikes)
- Total Ratings (Number) - Count of all ratings
- Like Count (Number) - Number of likes
- Dislike Count (Number) - Number of dislikes
"""

import json
import os
import urllib.request
import urllib.error

# Configuration
NOTION_API_KEY = os.environ.get('NOTION_API_KEY', '')
NOTION_API_VERSION = '2022-06-28'  # CRITICAL: Never use 2025-09-03
GALLERY_DATABASE_ID = '2fc41906-4d30-8189-a748-c6b715faf485'


def update_database_schema():
    """Add rating properties to the Gallery database"""
    url = f"https://api.notion.com/v1/databases/{GALLERY_DATABASE_ID}"
    
    # Properties to add
    payload = {
        "properties": {
            "Rating Score": {
                "number": {
                    "format": "number"
                }
            },
            "Total Ratings": {
                "number": {
                    "format": "number"
                }
            },
            "Like Count": {
                "number": {
                    "format": "number"
                }
            },
            "Dislike Count": {
                "number": {
                    "format": "number"
                }
            }
        }
    }
    
    headers = {
        'Authorization': f'Bearer {NOTION_API_KEY}',
        'Content-Type': 'application/json',
        'Notion-Version': NOTION_API_VERSION
    }
    
    req = urllib.request.Request(
        url, 
        data=json.dumps(payload).encode('utf-8'), 
        headers=headers, 
        method='PATCH'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            print("✅ Successfully added rating properties to Gallery database!")
            print(f"   Database: {result.get('title', [{}])[0].get('text', {}).get('content', 'N/A')}")
            print(f"   ID: {GALLERY_DATABASE_ID}")
            print("\n   Properties added:")
            print("   - Rating Score (Number)")
            print("   - Total Ratings (Number)")
            print("   - Like Count (Number)")
            print("   - Dislike Count (Number)")
            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"❌ Failed to update database: HTTP {e.code}")
        print(f"   Error: {error_body}")
        return False


def check_database_schema():
    """Check current database schema"""
    url = f"https://api.notion.com/v1/databases/{GALLERY_DATABASE_ID}"
    
    headers = {
        'Authorization': f'Bearer {NOTION_API_KEY}',
        'Notion-Version': NOTION_API_VERSION
    }
    
    req = urllib.request.Request(url, headers=headers, method='GET')
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            props = result.get('properties', {})
            
            print("📊 Current Gallery Database Properties:")
            for name, prop in props.items():
                prop_type = prop.get('type', 'unknown')
                print(f"   - {name}: {prop_type}")
            
            # Check if rating properties exist
            rating_props = ['Rating Score', 'Total Ratings', 'Like Count', 'Dislike Count']
            existing = [p for p in rating_props if p in props]
            missing = [p for p in rating_props if p not in props]
            
            print(f"\n✅ Rating properties exist: {existing}")
            if missing:
                print(f"❌ Rating properties missing: {missing}")
            
            return len(missing) == 0
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"❌ Failed to check database: HTTP {e.code}")
        print(f"   Error: {error_body}")
        return False


if __name__ == '__main__':
    if not NOTION_API_KEY:
        print("❌ NOTION_API_KEY environment variable not set!")
        print("   Run: export NOTION_API_KEY='your-api-key'")
        exit(1)
    
    print("🔍 Checking Gallery database schema...\n")
    has_all_props = check_database_schema()
    
    if not has_all_props:
        print("\n🔧 Adding missing rating properties...")
        success = update_database_schema()
        if success:
            print("\n✅ Database schema updated successfully!")
        else:
            print("\n❌ Failed to update database schema")
            exit(1)
    else:
        print("\n✅ All rating properties already exist!")
