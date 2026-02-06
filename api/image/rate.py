"""
Image Rating API Endpoint for Alice Display
POST /api/image/rate - Update image rating in Notion Gallery DB

Expected request body:
{
    "image_id": "2ff41906-4d30-8103-9c99-dbe11291822d",
    "rating": 1,  // 1 for like, -1 for dislike
    "context": {
        "timestamp": "2026-02-06T08:05:00.000Z",
        "weather": "Sunny",
        "time_period": "Morning",
        "user_agent": "Mozilla/5.0...",
        "session_id": "sess_abc123"
    }
}
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.error

# Notion configuration
NOTION_API_KEY = os.environ.get('NOTION_API_KEY', '')
NOTION_API_VERSION = '2022-06-28'  # CRITICAL: Never use 2025-09-03
GALLERY_DATABASE_ID = os.environ.get('GALLERY_DATABASE_ID', '2fc41906-4d30-8189-a748-c6b715faf485')


def get_image_page(image_id: str) -> dict:
    """Fetch the current image page from Notion to get existing rating values"""
    url = f"https://api.notion.com/v1/pages/{image_id}"
    headers = {
        'Authorization': f'Bearer {NOTION_API_KEY}',
        'Notion-Version': NOTION_API_VERSION
    }
    
    req = urllib.request.Request(url, headers=headers, method='GET')
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise Exception(f"Notion API error: {e.code} - {error_body}")


def update_image_rating(image_id: str, rating: int) -> dict:
    """
    Update the rating properties for an image in Notion.
    
    Rating properties:
    - Rating Score: cumulative score (likes - dislikes)
    - Total Ratings: count of all ratings
    - Like Count: number of likes
    - Dislike Count: number of dislikes
    """
    # First, get current values
    try:
        page = get_image_page(image_id)
        props = page.get('properties', {})
        
        # Get current values (default to 0 if not set)
        current_score = props.get('Rating Score', {}).get('number') or 0
        total_ratings = props.get('Total Ratings', {}).get('number') or 0
        like_count = props.get('Like Count', {}).get('number') or 0
        dislike_count = props.get('Dislike Count', {}).get('number') or 0
        
    except Exception as e:
        # If we can't get current values, start from 0
        print(f"Warning: Could not fetch current values: {e}")
        current_score = 0
        total_ratings = 0
        like_count = 0
        dislike_count = 0
    
    # Calculate new values
    new_score = current_score + rating
    new_total = total_ratings + 1
    new_like_count = like_count + (1 if rating == 1 else 0)
    new_dislike_count = dislike_count + (1 if rating == -1 else 0)
    
    # Update the page
    url = f"https://api.notion.com/v1/pages/{image_id}"
    
    payload = {
        "properties": {
            "Rating Score": {"number": new_score},
            "Total Ratings": {"number": new_total},
            "Like Count": {"number": new_like_count},
            "Dislike Count": {"number": new_dislike_count}
        }
    }
    
    headers = {
        'Authorization': f'Bearer {NOTION_API_KEY}',
        'Content-Type': 'application/json',
        'Notion-Version': NOTION_API_VERSION
    }
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='PATCH')
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            return {
                "success": True,
                "previous_score": current_score,
                "new_rating_score": new_score,
                "total_ratings": new_total,
                "like_count": new_like_count,
                "dislike_count": new_dislike_count
            }
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        return {"success": False, "error": f"Notion API error: {e.code}", "details": error_body}


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        """Handle rating submission"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            self.send_error_response(400, "Invalid JSON")
            return
        
        # Validate required fields
        image_id = data.get('image_id')
        rating = data.get('rating')
        
        if not image_id:
            self.send_error_response(400, "Missing required field: image_id")
            return
        
        if rating not in [1, -1]:
            self.send_error_response(400, "Rating must be 1 (like) or -1 (dislike)")
            return
        
        # Check for API key
        if not NOTION_API_KEY:
            self.send_error_response(500, "Notion API key not configured")
            return
        
        # Update the rating
        result = update_image_rating(image_id, rating)
        
        if result.get('success'):
            self.send_response(200)
        else:
            self.send_response(500)
        
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())
    
    def do_GET(self):
        """Health check endpoint"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "ok",
            "service": "Alice Image Rating API",
            "endpoint": "/api/image/rate"
        }).encode())
    
    def send_error_response(self, status_code: int, message: str):
        """Helper to send error responses with CORS headers"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"success": False, "error": message}).encode())
