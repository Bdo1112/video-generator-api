#!/bin/bash
set -e
echo "🚀 Deploying video-generator-api to VPS..."
echo ""
# Step 1: Commit and push changes
echo "📝 Committing changes..."
git add .
if git commit -m "Deploy $(date '+%Y-%m-%d %H:%M:%S')"; then
    echo "✅ Changes committed"
else
    echo "ℹ️  No changes to commit"
fi
echo "📤 Pushing to GitHub..."
git push origin main
echo "✅ Pushed to GitHub"
echo ""
# Step 2: Deploy on VPS
echo "🌐 Deploying on VPS..."
ssh root@72.62.166.107 << 'ENDSSH'
set -e
cd /root/02_apis/01_video_generator
echo "📥 Pulling latest code..."
git pull origin main
echo "🔄 Restarting Docker containers..."
docker-compose down
docker-compose up -d --build
echo "✅ Containers restarted"
echo ""
echo "📋 Recent logs:"
docker-compose logs --tail 20 video-generator
ENDSSH
echo ""
echo "✅ Deployment complete!"
echo "🌍 API available at: http://srv1239785.hstgr.cloud:8001"
