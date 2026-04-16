#!/bin/bash
set -e

echo "🚀 Deploying backend and Nginx config..."

# Restart Gunicorn
sudo systemctl restart fastapi

# Copy Nginx config
sudo cp nginx/recai.estuate.com.conf /etc/nginx/sites-available/recai.estuate.com
sudo ln -sf /etc/nginx/sites-available/recai.estuate.com /etc/nginx/sites-enabled/recai.estuate.com

# Test and restart Nginx
sudo nginx -t
sudo systemctl restart nginx

echo "✅ Deployment complete!"
