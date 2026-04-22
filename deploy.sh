#!/bin/bash
set -e

echo "Starting deployment..."

# 1. Sync with remote Git branch
echo "Pulling latest code from Git..."
git fetch origin
git reset --hard origin/fix-auth-cors

# 2. Restart FastAPI backend
echo "Restarting FastAPI backend..."
sudo systemctl restart fastapi

# 3. Build frontend
echo "Building frontend..."
cd ~/myapp/citation_generator/frontend
npm install --legacy-peer-deps
npm run build

# 4. Deploy frontend to Nginx
echo "Deploying frontend to /var/www/frontend..."
sudo rm -rf /var/www/frontend/*
sudo cp -r dist/* /var/www/frontend/

# 5. Update Nginx configuration
echo "Updating Nginx configuration from project..."
sudo cp ~/myapp/citation_generator/nginx/recai.estuate.com.conf /etc/nginx/sites-available/recai.estuate.com
sudo ln -sf /etc/nginx/sites-available/recai.estuate.com /etc/nginx/sites-enabled/recai.estuate.com

# 6. Reload Nginx
echo "Restarting Nginx..."
sudo nginx -t
sudo systemctl restart nginx

echo "Deployment complete! Both frontend and backend are live."
