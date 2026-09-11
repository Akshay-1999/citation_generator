# Ubuntu 22.04 LTS Deployment Guide for RecAI (Citation Generator)

This guide provides a complete, step-by-step procedure to deploy the application (**FastAPI Backend + React/Vite Frontend + PostgreSQL + Nginx**) on a fresh **Ubuntu 22.04.5 LTS (Jammy Jellyfish)** virtual machine.

---

## 🏗️ Architecture Overview

- **Host OS:** Ubuntu 22.04.5 LTS (x86_64)
- **Backend:** FastAPI (Python 3.10) managed via `systemd` service (`fastapi.service`) using Gunicorn with Uvicorn workers (`127.0.0.1:8000`).
- **Frontend:** React + Vite Single Page Application (SPA), compiled into static assets and served by Nginx from `/var/www/frontend`.
- **Reverse Proxy:** Nginx (listening on port 80/443), serving frontend static assets and reverse-proxying API calls (`/auth`, `/user`, `/main`, `/file`, `/chat`, `/folder`, `/conversion`) to FastAPI.
- **External Binaries:**
  - `libreoffice` (Headless mode for DOCX to PDF conversion)
  - `tesseract-ocr` & `tesseract-ocr-eng` (OCR text extraction from images/PDFs)
  - `ffmpeg` (Audio/video processing)

---

## Step 1: System Update & Package Installation

Connect to your fresh Ubuntu 22.04 server via SSH and install the system dependencies:

```bash
# 1. Update package lists and upgrade existing software
sudo apt update && sudo apt upgrade -y

# 2. Install essential build tools, python environment, and Nginx
sudo apt install -y git curl wget build-essential software-properties-common \
    python3 python3-pip python3-venv python3-dev libpq-dev nginx

# 3. Install LibreOffice, Tesseract OCR, and FFmpeg (CRITICAL for resume processing & OCR)
sudo apt install -y libreoffice tesseract-ocr tesseract-ocr-eng ffmpeg
```

Verify binary installations:
```bash
libreoffice --version
tesseract --version
ffmpeg -version
```

---

## Step 2: Install Node.js 20 LTS

Ubuntu 22.04 default repositories contain an older Node.js version. Install Node.js 20 LTS using the official NodeSource repository:

```bash
# 1. Download and run NodeSource setup script
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -

# 2. Install Node.js (includes npm)
sudo apt install -y nodejs

# 3. Verify installations
node -v   # Should output v20.x.x
npm -v    # Should output 10.x.x
```

---

## Step 3: Database Setup (PostgreSQL)

> [!NOTE]
> If you are using a managed cloud database (e.g., Supabase, Neon, AWS RDS), skip to **Step 4** and configure your connection strings in the `.env` file.

If installing PostgreSQL locally on the VM:

```bash
# 1. Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# 2. Start and enable service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 3. Create database and user (Replace 'your_secure_password' with your desired password)
sudo -u postgres psql -c "CREATE USER dbuser WITH PASSWORD 'your_secure_password';"
sudo -u postgres psql -c "CREATE DATABASE citation_db OWNER dbuser;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE citation_db TO dbuser;"
```

---

## Step 4: Clone the Repository & Configure Permissions

Create the application directory under your home folder:

```bash
mkdir -p ~/myapp
cd ~/myapp

# 1. Clone your repository
git clone https://github.com/Akshay-1999/citation_generator.git
cd citation_generator

# 2. Checkout your active working branch
git checkout option/claude-llm
git pull origin option/claude-llm

# 3. Create required runtime directories
mkdir -p logs static uploaded_files converted_resumes temp_jd_processing screening_reports

# 4. Set appropriate read/write permissions
chmod -R 775 uploaded_files converted_resumes temp_jd_processing screening_reports logs static
```

---

## Step 5: Backend Setup (Python Virtual Environment)

Inside `~/myapp/citation_generator`:

```bash
# 1. Create a virtual environment
python3 -m venv venv

# 2. Activate virtual environment
source venv/bin/activate

# 3. Upgrade pip, setuptools, and wheel
pip install --upgrade pip setuptools wheel

# 4. Install backend dependencies (legacy resolver flag prevents resolver hangs)
pip install -r requirements.txt --use-deprecated=legacy-resolver
```

---

## Step 6: Configure Environment Variables (`.env`)

Create the root `.env` file for FastAPI:

```bash
nano ~/myapp/citation_generator/.env
```

Populate the `.env` file with your production values:

```ini
# Server Environment
ENV=production

# Database Credentials
db_user=dbuser
db_password=your_secure_password
db_host=localhost
db_port=5432
db_name=citation_db

# Security & JWT Authentication
secret_key=YOUR_SUPER_SECRET_RANDOM_STRING_KEY_HERE
ALLOWED_ORIGINS=https://recai.estuate.com,http://recai.estuate.com

# LLM & AI API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
COHERE_API_KEY=...
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=...
TAVILY_API_KEY=...

# OCR Command Path (Optional, Ubuntu auto-detects /usr/bin/tesseract)
TESSERACT_CMD=/usr/bin/tesseract
```

Save and exit: `Ctrl + O`, `Enter`, `Ctrl + X`.

### Execute Database Migrations / Schema
If using local PostgreSQL, load the database schema:

```bash
PGPASSWORD='your_secure_password' psql -h localhost -U dbuser -d citation_db -f "db/table files/table.sql"
PGPASSWORD='your_secure_password' psql -h localhost -U dbuser -d citation_db -f "db/table files/create_converted_resumes.sql"
PGPASSWORD='your_secure_password' psql -h localhost -U dbuser -d citation_db -f "db/table files/video feature tables.sql"
```

---

## Step 7: Configure `systemd` Service for FastAPI

Create a systemd service to keep the FastAPI server running persistently in the background.

```bash
sudo nano /etc/systemd/system/fastapi.service
```

Paste the following configuration:
*(Replace `<YOUR_UBUNTU_USERNAME>` with your actual VM user, e.g., `ubuntu` or `akshay`)*

```ini
[Unit]
Description=FastAPI Service for Citation Generator / RecAI
After=network.target

[Service]
User=<YOUR_UBUNTU_USERNAME>
Group=<YOUR_UBUNTU_USERNAME>
WorkingDirectory=/home/<YOUR_UBUNTU_USERNAME>/myapp/citation_generator
Environment="PATH=/home/<YOUR_UBUNTU_USERNAME>/myapp/citation_generator/venv/bin:/usr/bin:/bin"
ExecStart=/home/<YOUR_UBUNTU_USERNAME>/myapp/citation_generator/venv/bin/gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000 --timeout 300
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Reload daemon, enable service on boot, and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable fastapi
sudo systemctl start fastapi

# Check service status
sudo systemctl status fastapi
```

Test backend locally on the server:
```bash
curl http://127.0.0.1:8000/
# Response: {"message":"Backend is running"}
```

---

## Step 8: Build and Deploy the Frontend

1. Navigate to the frontend directory:
   ```bash
   cd ~/myapp/citation_generator/frontend
   ```

2. Configure `frontend/.env`:
   ```bash
   nano .env
   ```
   Set `VITE_API_URL` to an empty string so the browser issues requests to the same origin (Nginx will proxy `/auth`, `/user`, etc., to backend port 8000):
   ```ini
   VITE_API_URL=
   ```

3. Install dependencies and compile production build:
   ```bash
   npm install --legacy-peer-deps
   npm run build
   ```

4. Deploy the compiled files to `/var/www/frontend`:
   ```bash
   sudo mkdir -p /var/www/frontend
   sudo rm -rf /var/www/frontend/*
   sudo cp -r dist/* /var/www/frontend/
   sudo chown -R www-data:www-data /var/www/frontend
   sudo chmod -R 755 /var/www/frontend
   ```

---

## Step 9: Configure Nginx & SSL

### 1. Create Nginx Site Configuration
```bash
sudo nano /etc/nginx/sites-available/recai.conf
```

Paste the following:
*(Replace `<YOUR_UBUNTU_USERNAME>` and `recai.estuate.com` with your actual username and domain or IP)*

```nginx
server {
    listen 80;
    server_name recai.estuate.com; # Replace with your domain name or VM IP

    client_max_body_size 100M;

    # Frontend Single Page App
    root /var/www/frontend;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Reverse Proxy for FastAPI Endpoints
    location ~ ^/(auth|user|main|file|chat|folder|conversion) {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Extended timeouts for AI processing
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }

    # Static assets served directly
    location /static/ {
        alias /home/<YOUR_UBUNTU_USERNAME>/myapp/citation_generator/static/;
        expires 30d;
        access_log off;
    }
}
```

### 2. Enable Site and Reload Nginx
```bash
# Disable default nginx configuration
sudo rm -f /etc/nginx/sites-enabled/default

# Enable our application site
sudo ln -sf /etc/nginx/sites-available/recai.conf /etc/nginx/sites-enabled/recai.conf

# Test syntax
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### 3. Setup SSL with Let's Encrypt (Certbot)
If you have a domain mapped to this VM's public IP:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d recai.estuate.com
```
*Certbot will automatically install the certificate, update Nginx with SSL blocks, and configure HTTP-to-HTTPS redirect.*

---

## Step 10: Configure UFW Firewall

Allow SSH and web traffic:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
sudo ufw status
```

---

## Step 11: Setup One-Command Deployment (`deploy.sh`)

Ensure your `deploy.sh` script is up-to-date for future git pull and deployments:

```bash
nano ~/myapp/citation_generator/deploy.sh
```

Ensure it looks like this:

```bash
#!/bin/bash
set -e

APP_DIR="$HOME/myapp/citation_generator"
BRANCH="option/claude-llm"

echo "=== Pulling latest changes from $BRANCH ==="
cd "$APP_DIR"
git fetch origin
git reset --hard "origin/$BRANCH"

echo "=== Updating Python dependencies ==="
source "$APP_DIR/venv/bin/activate"
pip install -r "$APP_DIR/requirements.txt" --use-deprecated=legacy-resolver

echo "=== Restarting FastAPI service ==="
sudo systemctl restart fastapi

echo "=== Building Frontend ==="
cd "$APP_DIR/frontend"
npm install --legacy-peer-deps
npm run build

echo "=== Syncing frontend build to /var/www/frontend ==="
sudo rm -rf /var/www/frontend/*
sudo cp -r dist/* /var/www/frontend/
sudo chown -R www-data:www-data /var/www/frontend

echo "=== Reloading Nginx ==="
sudo nginx -t
sudo systemctl reload nginx

echo "=== Deployment complete! ==="
```

Make it executable:
```bash
chmod +x ~/myapp/citation_generator/deploy.sh
```

Whenever you push new changes to GitHub, deploy on the VM simply by running:
```bash
./deploy.sh
```

---

## 🛠️ Operations & Troubleshooting Cheat Sheet

### View Logs
- **FastAPI Real-Time Logs:**
  ```bash
  journalctl -u fastapi -f
  ```
- **Nginx Error Logs:**
  ```bash
  sudo tail -f /var/log/nginx/error.log
  ```
- **Nginx Access Logs:**
  ```bash
  sudo tail -f /var/log/nginx/access.log
  ```

### Manage Services
- **Restart Backend:**
  ```bash
  sudo systemctl restart fastapi
  ```
- **Check Backend Status:**
  ```bash
  sudo systemctl status fastapi
  ```
- **Restart Nginx:**
  ```bash
  sudo systemctl restart nginx
  ```
- **Restart PostgreSQL:**
  ```bash
  sudo systemctl restart postgresql
  ```

### Common Gotchas & Fixes
1. **Resume PDF conversion error (`LibreOffice conversion failed`):**
   Ensure `libreoffice` is installed on Ubuntu: `sudo apt install -y libreoffice`.
2. **OCR extraction error (`Tesseract executable not found`):**
   Ensure `tesseract-ocr` is installed: `sudo apt install -y tesseract-ocr tesseract-ocr-eng`.
3. **Frontend API calls failing with `ERR_CONNECTION_REFUSED` to `localhost:8000`:**
   Check `frontend/.env`. It must have `VITE_API_URL=` (empty), and the frontend must be rebuilt (`npm run build`).
4. **File upload 413 Payload Too Large:**
   Check `client_max_body_size 100M;` inside your Nginx server block.
