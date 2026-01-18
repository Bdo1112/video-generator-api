# Docker Deployment Guide

## 🚀 Quick Deploy

### 1. Build and Start
```bash
docker-compose up -d --build
```

### 2. Check Status
```bash
docker-compose ps
docker-compose logs -f
```

### 3. Test
```bash
# Health check
curl http://srv1239785.hstgr.cloud:8001/

# Should return: {"service":"Video Generator API","version":"1.0.0","status":"running"}
```

---

## 📁 What's Running

**Two containers:**
1. **video-generator-api** - FastAPI application (internal port 8000)
2. **video-generator-nginx** - Nginx reverse proxy + static files (public port 8001)

**Nginx handles:**
- `/api/*` → Proxy to FastAPI
- `/jobs/*` → Serve static files (frames, videos) directly
- `/` → Health check

---

## 🔧 Useful Commands

### View Logs
```bash
# All logs
docker-compose logs -f

# Just API logs
docker-compose logs -f video-generator

# Just Nginx logs
docker-compose logs -f nginx
```

### Restart
```bash
docker-compose restart
```

### Stop
```bash
docker-compose down
```

### Rebuild After Code Changes
```bash
docker-compose down
docker-compose up -d --build
```

### Clean Everything
```bash
docker-compose down -v  # Removes volumes too
```

---

## 🧪 Test Image-to-Video

### 1. Generate Prompts
```bash
curl -X POST http://srv1239785.hstgr.cloud:8001/api/prompts/sync \
  -H "Content-Type: application/json" \
  -d '{
    "article_text": "Test article...",
    "title": "test_continuity",
    "num_shots": 2,
    "clip_duration": 10
  }'
```

### 2. Generate Videos
```bash
curl -X POST http://srv1239785.hstgr.cloud:8001/api/create_videos \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test_continuity",
    "prompts_file": "./jobs/test_continuity/prompts/..."
  }'
```

### 3. Check Frame Was Created
```bash
# After Shot 1 completes, check frame exists:
curl -I http://srv1239785.hstgr.cloud:8001/jobs/test_continuity/frames/shot_01_last.png

# Should return: 200 OK
```

### 4. Watch Logs for Image-to-Video
```bash
docker-compose logs -f video-generator | grep "IMAGE-TO-VIDEO"

# You should see:
# [video] Mode: IMAGE-TO-VIDEO
# [video] Image URL: http://srv1239785.hstgr.cloud:8001/jobs/.../frames/shot_01_last.png
```

---

## 🐛 Troubleshooting

### Container won't start
```bash
docker-compose logs video-generator
```

### Can't access API
```bash
# Check nginx is running
docker-compose ps

# Test nginx directly
docker exec video-generator-nginx nginx -t
```

### Frames not accessible
```bash
# Check files exist
ls -la jobs/*/frames/

# Check nginx permissions
docker exec video-generator-nginx ls -la /var/www/jobs
```

### Update config
```bash
# Edit config.env, then:
docker-compose down
docker-compose up -d
```

---

## 📊 File Structure on Server

```
/app/  (inside container)
├── api/
├── src/
├── config.env
├── jobs/           → /var/www/jobs/ (nginx serves this)
│   └── {job_id}/
│       ├── videos/
│       ├── frames/  ← Accessible at http://srv.../jobs/{job_id}/frames/
│       └── audio/
└── ...
```

---

## 🔒 Security Notes

- All files in `/jobs` are publicly accessible
- Consider adding authentication for production
- Use HTTPS in production (add SSL to nginx)

---

## 🎯 Next Steps

1. Deploy: `docker-compose up -d --build`
2. Test health: `curl http://srv1239785.hstgr.cloud:8001/`
3. Generate 2 videos to test continuity
4. Check if KIE can download frames
5. Verify Shot 2 uses image-to-video mode
