#!/bin/bash
set -e

echo "🚀 Deploying backend and frontend..."

# 1. Restart FastAPI backend
sudo systemctl restart fastapi

# 2. Build frontend (make sure Node is installed on the server)
cd ~/myapp/citation_generator/frontend
npm install --legacy-peer-deps
npm run build

# 3. Copy frontend build to Nginx directory
sudo rm -rf /var/www/frontend/*
sudo cp -r dist/* /var/www/frontend/

# 4. Reload Nginx
sudo nginx -t
sudo systemctl restart nginx

echo "✅ Deployment complete!"
