# Alice Image Control API

Vercel serverless API for the Alice Display image control panel.

## Endpoints

### POST /api/image/rate
Update the rating for an image in the Notion Gallery database.

**Request:**
```json
{
    "image_id": "2ff41906-4d30-8103-9c99-dbe11291822d",
    "rating": 1,
    "context": {
        "timestamp": "2026-02-06T08:05:00.000Z",
        "weather": "Sunny",
        "time_period": "Morning",
        "session_id": "sess_abc123"
    }
}
```

**Response:**
```json
{
    "success": true,
    "previous_score": 5,
    "new_rating_score": 6,
    "total_ratings": 12,
    "like_count": 9,
    "dislike_count": 3
}
```

### POST /api/image/change
Get a different image matching the current context.

**Request:**
```json
{
    "current_image_id": "2ff41906-4d30-8103-9c99-dbe11291822d",
    "context": {
        "weather": "Sunny",
        "time_period": "Morning",
        "hour": 9
    }
}
```

**Response:**
```json
{
    "success": true,
    "image": {
        "id": "...",
        "title": "Alice Morning Coffee",
        "cloudinary_url": "https://res.cloudinary.com/...",
        "weather": "Sunny",
        "time_period": "Morning",
        "activity": "Breakfast",
        "rating_score": 5
    }
}
```

## Environment Variables

- `NOTION_API_KEY` - Notion integration token
- `GALLERY_DATABASE_ID` - ID of the Notion Gallery database (default: 2fc41906-4d30-8189-a748-c6b715faf485)

## Deployment

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Set environment variable
vercel env add NOTION_API_KEY
```

## Gallery Database Properties Required

The following properties must exist in the Notion Gallery database:

- **Rating Score** (Number) - Cumulative rating (likes - dislikes)
- **Total Ratings** (Number) - Total number of ratings
- **Like Count** (Number) - Number of likes
- **Dislike Count** (Number) - Number of dislikes
- **Cloudinary URL** (URL) - Required for image selection
- **Weather** (Select) - Weather condition
- **Time Period** (Select) - Time of day
- **Activity** (Text) - Current activity
- **Title** or **Name** (Title) - Image title

## Local Development

```bash
vercel dev
```

Then test with:
```bash
curl -X POST http://localhost:3000/api/image/rate \
  -H "Content-Type: application/json" \
  -d '{"image_id": "test-id", "rating": 1}'
```
