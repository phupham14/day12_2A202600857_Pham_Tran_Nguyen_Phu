# Deployment Information

## Public URL
https://ai-agent-0nyx.onrender.com/

## Platform
Render (Free tier, region: Singapore)

## Deployment Method
- Connected GitHub repo to Render Dashboard → New → Web Service
- Root Directory: `03-cloud-deployment/render`
- Runtime: Python, Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`

## Verified Endpoints

### Root
```
GET https://ai-agent-0nyx.onrender.com/
→ {"message":"AI Agent running on Railway!","docs":"/docs","health":"/health"}
```

### Health Check
```
GET https://ai-agent-0nyx.onrender.com/health
→ {"status":"ok","uptime_seconds":...,"platform":"Railway"}
```

### Docs
```
GET https://ai-agent-0nyx.onrender.com/docs
→ Swagger UI (interactive API docs)
```

## Test Commands

```bash
# Root
curl https://ai-agent-0nyx.onrender.com/

# Health
curl https://ai-agent-0nyx.onrender.com/health

# Docs (open in browser)
# https://ai-agent-0nyx.onrender.com/docs
```

## Notes
- App code copied from `03-cloud-deployment/railway/` — response messages reference "Railway" but the deployment platform is Render
- Free tier may spin down after inactivity (~30s cold start on first request)
