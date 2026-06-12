# Deployment Information

## Public URL
https://YOUR_URL.up.railway.app

## Platform
Railway

## Test Commands

### Health Check
curl https://YOUR_URL.up.railway.app/health

### API Test
curl -X POST https://YOUR_URL.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Docker?"}'

## Screenshots
- screenshots/dashboard.png
- screenshots/running.png
