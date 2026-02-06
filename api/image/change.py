"""
Image Change API Endpoint for Alice Display
POST /api/image/change - Select and return a different image matching current context

Expected request body:
{
    "current_image_id": "2ff41906-4d30-8103-9c99-dbe11291822d",
    "context": {
        "weather": "Sunny",
        "time_period": "Morning",
        "hour": 9,
        "exclude_recent": true
    }
}

Response:
{
    "success": true,
    "image": {
        "id": "...",
        "title": "...",
        "cloudinary_url": "...",
        "weather": "...",
        "time_period": "...",
        "activity": "...",
        "rating_score": 5
    }
}
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import random
import urllib.request
import urllib.error

# Notion configuration
NOTION_API_KEY = os.environ.get('NOTION_API_KEY', '')
NOTION_API_VERSION = '2022-06-28'  # CRITICAL: Never use 2025-09-03
GALLERY_DATABASE_ID = os.environ.get('GALLERY_DATABASE_ID', '2fc41906-4d30-8189-a748-c6b715faf485')

# Weather fallback chains
WEATHER_FALLBACKS = {
    "Sunny": ["Partly Cloudy", "Cloudy"],
    "Partly Cloudy": ["Sunny", "Cloudy"],
    "Cloudy": ["Overcast", "Partly Cloudy"],
    "Overcast": ["Cloudy", "Rainy"],
    "Rainy": ["Stormy", "Cloudy", "Overcast"],
    "Stormy": ["Rainy", "Overcast"],
    "Snowy": ["Cloudy", "Overcast", "Foggy"],
    "Foggy": ["Cloudy", "Overcast"],
    "Windy": ["Cloudy", "Partly Cloudy"],
}

# Time period fallbacks
TIME_FALLBACKS = {
    "Dawn": ["Early Morning", "Morning", "Golden Hour"],
    "Early Morning": ["Dawn", "Morning"],
    "Morning": ["Dawn", "Midday", "Early Morning"],
    "Midday": ["Afternoon", "Morning"],
    "Afternoon": ["Midday", "Evening", "Golden Hour"],
    "Golden Hour": ["Afternoon", "Evening"],
    "Evening": ["Golden Hour", "Afternoon", "Night"],
    "Night": ["Late Night", "Evening", "Dawn"],
    "Late Night": ["Night", "Dawn"],
    "Clear Night": ["Night", "Late Night", "Evening"],
}


def query_gallery_images(weather: str, time_period: str, exclude_id: str = None, page_size: int = 100) -> list:
    """
    Query the Gallery database for images matching weather and time period.
    Requires cloudinary_url to be set.
    """
    url = f"https://api.notion.com/v1/databases/{GALLERY_DATABASE_ID}/query"
    
    # Build filter - require cloudinary_url and match weather/time
    filter_conditions = [
        {
            "property": "Cloudinary URL",
            "url": {"is_not_empty": True}
        }
    ]
    
    # Add weather filter if specified
    if weather:
        filter_conditions.append({
            "property": "Weather",
            "select": {"equals": weather}
        })
    
    # Add time filter if specified
    if time_period:
        filter_conditions.append({
            "property": "Time Period",
            "select": {"equals": time_period}
        })
    
    payload = {
        "filter": {
            "and": filter_conditions
        },
        "page_size": page_size,
        "sorts": [
            {"property": "Rating Score", "direction": "descending"}
        ]
    }
    
    headers = {
        'Authorization': f'Bearer {NOTION_API_KEY}',
        'Content-Type': 'application/json',
        'Notion-Version': NOTION_API_VERSION
    }
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            return parse_gallery_results(result.get('results', []), exclude_id)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise Exception(f"Notion API error: {e.code} - {error_body}")


def parse_gallery_results(results: list, exclude_id: str = None) -> list:
    """Parse Notion query results into image objects"""
    images = []
    
    for page in results:
        page_id = page.get('id')
        
        # Skip the excluded image
        if exclude_id and page_id == exclude_id:
            continue
        
        props = page.get('properties', {})
        
        # Get cloudinary URL (required)
        cloudinary_url = None
        url_prop = props.get('Cloudinary URL', {})
        if url_prop.get('url'):
            cloudinary_url = url_prop['url']
        
        if not cloudinary_url:
            continue
        
        # Get title
        title = ''
        title_prop = props.get('Title', props.get('Name', {}))
        if title_prop.get('title') and len(title_prop['title']) > 0:
            title = title_prop['title'][0].get('text', {}).get('content', '')
        
        # Get weather
        weather = ''
        weather_prop = props.get('Weather', {})
        if weather_prop.get('select'):
            weather = weather_prop['select'].get('name', '')
        
        # Get time period
        time_period = ''
        time_prop = props.get('Time Period', {})
        if time_prop.get('select'):
            time_period = time_prop['select'].get('name', '')
        
        # Get activity
        activity = ''
        activity_prop = props.get('Activity', {})
        if activity_prop.get('rich_text') and len(activity_prop['rich_text']) > 0:
            activity = activity_prop['rich_text'][0].get('text', {}).get('content', '')
        
        # Get rating score
        rating_score = 0
        rating_prop = props.get('Rating Score', {})
        if rating_prop.get('number') is not None:
            rating_score = rating_prop['number']
        
        images.append({
            'id': page_id,
            'title': title,
            'cloudinary_url': cloudinary_url,
            'weather': weather,
            'time_period': time_period,
            'activity': activity,
            'rating_score': rating_score
        })
    
    return images


def weighted_random_choice(images: list) -> dict:
    """
    Select an image using weighted random selection based on rating score.
    Higher rated images are more likely to be selected.
    """
    if not images:
        return None
    
    if len(images) == 1:
        return images[0]
    
    # Calculate weights based on rating
    weights = []
    for img in images:
        rating = img.get('rating_score', 0)
        # Base weight of 1.0, modified by rating
        # Clamp between 0.1 and 3.0 to avoid extreme biases
        weight = max(0.1, min(3.0, 1.0 + (rating / 10.0)))
        weights.append(weight)
    
    # Normalize weights to probabilities
    total_weight = sum(weights)
    probabilities = [w / total_weight for w in weights]
    
    # Weighted random selection
    r = random.random()
    cumulative = 0
    for i, prob in enumerate(probabilities):
        cumulative += prob
        if r <= cumulative:
            return images[i]
    
    # Fallback (shouldn't reach here)
    return random.choice(images)


def find_alternative_image(weather: str, time_period: str, exclude_id: str) -> dict:
    """
    Find an alternative image matching the context.
    Uses fallback chains if no exact match found.
    """
    # Try exact match first
    images = query_gallery_images(weather, time_period, exclude_id)
    if images:
        return weighted_random_choice(images)
    
    # Try weather fallbacks
    for fallback_weather in WEATHER_FALLBACKS.get(weather, []):
        images = query_gallery_images(fallback_weather, time_period, exclude_id)
        if images:
            return weighted_random_choice(images)
    
    # Try time fallbacks
    for fallback_time in TIME_FALLBACKS.get(time_period, []):
        images = query_gallery_images(weather, fallback_time, exclude_id)
        if images:
            return weighted_random_choice(images)
    
    # Try both fallbacks combined
    for fallback_weather in WEATHER_FALLBACKS.get(weather, []):
        for fallback_time in TIME_FALLBACKS.get(time_period, []):
            images = query_gallery_images(fallback_weather, fallback_time, exclude_id)
            if images:
                return weighted_random_choice(images)
    
    # Ultimate fallback: any image with cloudinary URL
    images = query_gallery_images(None, None, exclude_id)
    if images:
        return weighted_random_choice(images)
    
    return None


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        """Handle image change request"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            self.send_error_response(400, "Invalid JSON")
            return
        
        # Check for API key
        if not NOTION_API_KEY:
            self.send_error_response(500, "Notion API key not configured")
            return
        
        # Extract context
        context = data.get('context', {})
        weather = context.get('weather', 'Sunny')
        time_period = context.get('time_period', 'Afternoon')
        current_image_id = data.get('current_image_id')
        
        try:
            # Find alternative image
            image = find_alternative_image(weather, time_period, current_image_id)
            
            if image:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "image": image
                }).encode())
            else:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": "no_alternatives_found",
                    "message": "No alternative images found matching current context"
                }).encode())
        except Exception as e:
            self.send_error_response(500, str(e))
    
    def do_GET(self):
        """Health check endpoint"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "ok",
            "service": "Alice Image Change API",
            "endpoint": "/api/image/change"
        }).encode())
    
    def send_error_response(self, status_code: int, message: str):
        """Helper to send error responses with CORS headers"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"success": False, "error": message}).encode())
