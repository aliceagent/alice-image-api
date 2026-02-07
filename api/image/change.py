"""
Image Change API Endpoint for Alice Display
POST /api/image/change - Select and return a different image matching current context
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import random
import urllib.request
import urllib.error

# GitHub-hosted image database (same data as select_image.py uses)
IMAGE_DATABASE_URL = "https://raw.githubusercontent.com/aliceagent/alice-display/main/data/image-database.json"

# Weather fallback chains
WEATHER_FALLBACKS = {
    "Sunny": ["Partly Cloudy", "Cloudy", "Clear"],
    "Partly Cloudy": ["Sunny", "Cloudy"],
    "Cloudy": ["Overcast", "Partly Cloudy"],
    "Overcast": ["Cloudy", "Foggy"],
    "Rainy": ["Stormy", "Cloudy", "Overcast"],
    "Stormy": ["Rainy", "Overcast"],
    "Snowy": ["Cloudy", "Overcast", "Foggy"],
    "Foggy": ["Cloudy", "Overcast"],
    "Windy": ["Cloudy", "Partly Cloudy"],
    "Clear": ["Sunny", "Partly Cloudy"],
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


def fetch_image_database() -> list:
    """Fetch the image database from GitHub"""
    try:
        req = urllib.request.Request(IMAGE_DATABASE_URL, headers={'User-Agent': 'AliceImageAPI/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data if isinstance(data, list) else data.get('images', [])
    except Exception as e:
        raise Exception(f"Failed to fetch image database: {str(e)}")


def find_matching_images(images: list, weather: str, time_period: str, exclude_id: str = None) -> list:
    """Find images matching weather and time period with CDN URLs"""
    matches = []
    
    for img in images:
        # Must have cloudinary URL
        if not img.get('cloudinary_url') or not img.get('cloudinary_url').strip():
            continue
        
        # Must be verified
        if not img.get('verified'):
            continue
        
        # Skip excluded image
        if exclude_id and img.get('id') == exclude_id:
            continue
        
        # SKIP HOLIDAY IMAGES - they should only appear on their actual holiday
        # The main display handles holiday logic; change should only return regular images
        holiday = img.get('holiday', '')
        if holiday and holiday.strip():
            continue
        
        # Check weather match
        if weather and img.get('weather', '').lower() != weather.lower():
            continue
        
        # Check time period match
        if time_period and img.get('time_period', '').lower() != time_period.lower():
            continue
        
        matches.append(img)
    
    return matches


def weighted_random_choice(candidates: list) -> dict:
    """Select image using rating-weighted random choice"""
    if not candidates:
        return None
    
    # Calculate weights based on rating
    weighted = []
    for img in candidates:
        rating_score = img.get('rating_score', 0) or 0
        total_ratings = img.get('total_ratings', 0) or 0
        
        if total_ratings >= 5:
            weight = max(0.1, min(3.0, 1.0 + rating_score / 10))
        else:
            weight = 1.0
        
        weighted.append((img, weight))
    
    # Weighted random selection
    total_weight = sum(w for _, w in weighted)
    r = random.uniform(0, total_weight)
    
    cumulative = 0
    for img, weight in weighted:
        cumulative += weight
        if r <= cumulative:
            return img
    
    return weighted[-1][0] if weighted else None


def select_different_image(images: list, context: dict, exclude_id: str = None) -> dict:
    """Select a different image matching context, with fallbacks.
    
    IMPORTANT: Time period is prioritized over weather to prevent showing
    daytime images at night (or vice versa).
    """
    weather = context.get('weather', '')
    time_period = context.get('time_period', '')
    
    # Define time period groups for consistency
    NIGHT_PERIODS = ['Night', 'Late Night', 'Clear Night']
    DAY_PERIODS = ['Morning', 'Midday', 'Afternoon', 'Dawn', 'Early Morning']
    TRANSITION_PERIODS = ['Evening', 'Golden Hour']
    
    def get_compatible_periods(period):
        """Get time periods that are visually compatible"""
        if period in NIGHT_PERIODS:
            return NIGHT_PERIODS + ['Evening']  # Night can show evening
        elif period in DAY_PERIODS:
            return DAY_PERIODS + TRANSITION_PERIODS
        elif period in TRANSITION_PERIODS:
            return TRANSITION_PERIODS + DAY_PERIODS  # Evening prefers day over night
        return [period]
    
    compatible_times = get_compatible_periods(time_period)
    
    # Try exact match first
    matches = find_matching_images(images, weather, time_period, exclude_id)
    if matches:
        return weighted_random_choice(matches)
    
    # Try weather fallbacks with SAME time period
    for fallback_weather in WEATHER_FALLBACKS.get(weather, []):
        matches = find_matching_images(images, fallback_weather, time_period, exclude_id)
        if matches:
            return weighted_random_choice(matches)
    
    # Try any weather with SAME time period
    matches = find_matching_images(images, None, time_period, exclude_id)
    if matches:
        return weighted_random_choice(matches)
    
    # Try compatible time periods (e.g., Night can use Late Night)
    for alt_time in compatible_times:
        if alt_time != time_period:
            # Try with original weather
            matches = find_matching_images(images, weather, alt_time, exclude_id)
            if matches:
                return weighted_random_choice(matches)
            # Try any weather
            matches = find_matching_images(images, None, alt_time, exclude_id)
            if matches:
                return weighted_random_choice(matches)
    
    # STRICT: Only return images within compatible time groups
    # This prevents showing daytime images at night
    compatible_images = [
        img for img in images 
        if img.get('cloudinary_url') and img.get('verified') 
        and img.get('id') != exclude_id
        and not (img.get('holiday') and img.get('holiday').strip())
        and img.get('time_period', '') in compatible_times
    ]
    if compatible_images:
        return weighted_random_choice(compatible_images)
    
    # Ultimate fallback: NO images rather than wrong time period
    # User sees "no alternatives found" which is better than wrong images
    return None


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else '{}'
            data = json.loads(body) if body else {}
            
            current_image_id = data.get('current_image_id')
            context = data.get('context', {})
            
            # Fetch image database
            images = fetch_image_database()
            
            # Find a different image
            selected = select_different_image(images, context, current_image_id)
            
            if not selected:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'error': 'no_alternatives_found',
                    'message': 'No alternative images found for current conditions'
                }).encode())
                return
            
            # Return the selected image
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'image': {
                    'id': selected.get('id'),
                    'title': selected.get('name', ''),
                    'cloudinary_url': selected.get('cloudinary_url'),
                    'weather': selected.get('weather', ''),
                    'time_period': selected.get('time_period', ''),
                    'activity': selected.get('activity', ''),
                    'rating_score': selected.get('rating_score', 0)
                }
            }).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'error': str(e)
            }).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
