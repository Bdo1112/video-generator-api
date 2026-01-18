# Deployment Guide - Hostinger VPS

## Prerequisites

Your VPS already has:
- ✅ Docker installed
- ✅ Ubuntu 24.04.3 LTS
- ✅ Existing apps running on port 8000

## Step 1: Upload Files to VPS

From your local machine, upload the project to your VPS:

```bash
# Option A: Using rsync (recommended)
rsync -avz --exclude 'jobs' --exclude '__pycache__' \
  /Users/brianoh/Dev/01_Personal/01_Youtube/03_video_gen/01_video_generator/ \
  root@72.62.166.107:/root/02_apis/01_video_generator/

# Option B: Using scp
scp -r /Users/brianoh/Dev/01_Personal/01_Youtube/03_video_gen/01_video_generator/ \
  root@72.62.166.107:/root/02_apis/01_video_generator/
```

## Step 2: SSH into Your VPS

```bash
ssh root@72.62.166.107
```

## Step 3: Navigate to Project Directory

```bash
cd /root/02_apis/01_video_generator
```

## Step 4: Configure Environment Variables

```bash
# Copy example config
cp config.env.example config.env

# Edit config.env and add your API keys
nano config.env
```

Add your keys:
```
ANTHROPIC_API_KEY=sk-ant-xxxxx
KIE_API_KEY=your-kie-key-here
```

Save and exit (Ctrl+X, then Y, then Enter).

## Step 5: Build and Run

```bash
# Build the Docker image
docker-compose build

# Start the container
docker-compose up -d
```

## Step 6: Verify It's Running

```bash
# Check container status
docker ps

# Should see:
# CONTAINER ID   IMAGE                    ...   PORTS                    ...
# xxxxx          video-generator-api      ...   0.0.0.0:8001->8000/tcp   ...

# Check logs
docker-compose logs -f

# Test the API
curl http://localhost:8001
```

## Step 7: Access from Outside

Your API is now available at:
- **API**: http://72.62.166.107:8001
- **Docs**: http://72.62.166.107:8001/docs

## Common Commands

```bash
# View logs
docker-compose logs -f

# Restart container
docker-compose restart

# Stop container
docker-compose down

# Rebuild and restart (after code changes)
docker-compose down
docker-compose build
docker-compose up -d

# Check container stats (CPU, memory)
docker stats video-generator-api
```

## Updating the App

When you make changes locally:

```bash
# 1. Upload changes from local machine
rsync -avz --exclude 'jobs' --exclude '__pycache__' \
  /Users/brianoh/Dev/01_Personal/01_Youtube/03_video_gen/01_video_generator/ \
  root@72.62.166.107:/root/02_apis/01_video_generator/

# 2. SSH into VPS
ssh root@72.62.166.107

# 3. Rebuild and restart
cd /root/02_apis/01_video_generator
docker-compose down
docker-compose build
docker-compose up -d
```

## Troubleshooting

### Container won't start
```bash
# Check logs for errors
docker-compose logs

# Check if port 8001 is already in use
netstat -tulpn | grep 8001
```

### Can't access from outside
```bash
# Check if firewall allows port 8001
ufw status
ufw allow 8001
```

### Out of disk space
```bash
# Check disk usage
df -h

# Clean up old Docker images
docker system prune -a
```

### Remove all job files
```bash
rm -rf /root/02_apis/01_video_generator/jobs/*
```

## Port Configuration

- **Container internal port**: 8000 (app runs on this)
- **VPS external port**: 8001 (you access via this)
- **Other apps**: 8000 (your existing fastapi-video-api)

## File Structure on VPS

```
/root/02_apis/01_video_generator/
├── api/
├── src/
├── jobs/              # Video files (persistent)
├── downloads/
├── output/
├── config.env         # Your API keys
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Security Notes

1. **Firewall**: Only open port 8001 if you need external access
2. **API Keys**: Never commit config.env to git
3. **CORS**: In production, update `allow_origins` in api/main.py to restrict access
4. **SSL**: Consider adding Nginx with Let's Encrypt for HTTPS

## Next Steps (Optional)

- Add Nginx reverse proxy for HTTPS
- Set up automatic backups of `/root/02_apis/01_video_generator/jobs/`
- Add monitoring (Datadog, Prometheus, etc.)
- Set up log rotation
