# Deploying Alice Image API to Vercel

## Quick Deploy (Recommended)

### Option 1: Vercel Dashboard
1. Go to [vercel.com/new](https://vercel.com/new)
2. Import the GitHub repo: `aliceagent/alice-image-api`
3. Configure environment variable:
   - `NOTION_API_KEY` = your Notion integration token
4. Click Deploy

### Option 2: Vercel CLI
```bash
cd alice-image-api
vercel login  # One-time authentication
vercel --prod
```

Then add the environment variable:
```bash
vercel env add NOTION_API_KEY
# Paste your Notion API key when prompted
# Select 'Production', 'Preview', and 'Development'
```

Redeploy after adding the env var:
```bash
vercel --prod
```

## Expected Endpoints

After deployment, you'll have:
- `https://alice-image-api.vercel.app/api/image/rate` - POST to rate images
- `https://alice-image-api.vercel.app/api/image/change` - POST to get different image

## Verify Deployment

Test the health check:
```bash
curl https://alice-image-api.vercel.app/api/image/rate
```

Expected response:
```json
{"status": "ok", "service": "Alice Image Rating API", "endpoint": "/api/image/rate"}
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `NOTION_API_KEY` | Notion integration token | Yes |
| `GALLERY_DATABASE_ID` | Gallery DB ID (has default) | No |

## Troubleshooting

**"Notion API key not configured"**
- Add the `NOTION_API_KEY` environment variable in Vercel dashboard
- Redeploy after adding

**CORS errors**
- The API allows all origins (`*`) for browser requests
- Should work from any domain

**"Image not found" errors**
- Check that the image ID (Notion page ID) is correct
- Verify the Gallery database has the rating properties:
  - Rating Score (Number)
  - Total Ratings (Number)
  - Like Count (Number)
  - Dislike Count (Number)

These properties were added by `scripts/add_rating_properties.py`.
