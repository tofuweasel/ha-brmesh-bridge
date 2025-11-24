# Publishing BRMesh Bridge to buckleup.cc

This guide covers publishing the BRMesh Bridge add-on repository to your web server at http://www.buckleup.cc/ for easy HACS installation.

## Prerequisites

- SSH access to server "us001" at buckleup.cc
- Git installed on the server
- Web server (Apache/Nginx) configured to serve static content
- Docker Hub or GitHub Container Registry account (for images)

---

## Step 1: Prepare Repository Structure

The add-on repository should have this structure:

```
brmesh-bridge/
├── README.md
├── config.yaml
├── Dockerfile
├── run.sh
├── brmesh_bridge.py
├── effects.py
├── web_ui.py
├── esphome_generator.py
├── ble_discovery.py
├── app_importer.py
├── nspanel_ui.py
├── repository.json      # HACS repository manifest
├── hacs.json           # HACS integration metadata
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
└── templates/
    └── index.html
```

---

## Step 2: Create GitHub Repository

For HACS to work properly, the add-on needs to be in a Git repository:

```bash
# On your local machine
cd c:\Profiles\crval\Nextcloud\Projects\HomeAssistant\addons\brmesh-bridge

# Initialize git if not already done
git init
git add .
git commit -m "Initial commit: BRMesh Bridge v2.0.0 with GUI configuration"

# Create repository on GitHub
# Go to https://github.com/new
# Repository name: ha-brmesh-bridge
# Description: Home Assistant add-on for BRMesh/Fastcon BLE lights with GUI configuration

# Add remote and push
git remote add origin https://github.com/YOUR_USERNAME/ha-brmesh-bridge.git
git branch -M main
git push -u origin main
```

---

## Step 3: Update repository.json

Edit `repository.json` to point to your actual GitHub repository:

```json
{
  "name": "BRMesh Bridge Pro",
  "url": "https://github.com/YOUR_USERNAME/ha-brmesh-bridge",
  "version": "2.0.0",
  "image": "ghcr.io/YOUR_USERNAME/{arch}-brmesh-bridge"
}
```

---

## Step 4: Build and Publish Docker Images

### Option A: GitHub Container Registry (Recommended)

1. **Enable GitHub Container Registry**:
   - Go to your GitHub repository
   - Settings → Packages → Improved container support

2. **Create GitHub Actions workflow**:

Create `.github/workflows/publish.yml`:

```yaml
name: Publish Add-on Images

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        arch: [aarch64, amd64, armhf, armv7, i386]
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up QEMU
        uses: docker/setup-qemu-action@v2
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Login to GitHub Container Registry
        uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          platforms: linux/${{ matrix.arch }}
          push: true
          tags: ghcr.io/${{ github.repository_owner }}/${{ matrix.arch }}-brmesh-bridge:latest
```

3. **Trigger build**:
```bash
git tag v2.0.0
git push origin v2.0.0
```

### Option B: Manual Docker Build

```bash
# Build for your architecture
docker build -t ghcr.io/YOUR_USERNAME/amd64-brmesh-bridge:latest .

# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# Push image
docker push ghcr.io/YOUR_USERNAME/amd64-brmesh-bridge:latest
```

---

## Step 5: Deploy Repository to buckleup.cc

### SSH into your server

```bash
ssh user@us001.buckleup.cc
```

### Clone the repository

```bash
cd /var/www/buckleup.cc/
sudo mkdir -p brmesh-bridge
cd brmesh-bridge

# Clone your GitHub repository
sudo git clone https://github.com/YOUR_USERNAME/ha-brmesh-bridge.git .
```

### Configure web server

**For Nginx** (create `/etc/nginx/sites-available/brmesh-bridge`):

```nginx
server {
    listen 80;
    server_name www.buckleup.cc buckleup.cc;
    
    location /brmesh-bridge {
        alias /var/www/buckleup.cc/brmesh-bridge;
        autoindex on;
        
        # Enable CORS for HACS
        add_header 'Access-Control-Allow-Origin' '*';
        add_header 'Access-Control-Allow-Methods' 'GET, OPTIONS';
        
        # Serve JSON with correct content type
        location ~ \.json$ {
            add_header Content-Type application/json;
        }
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/brmesh-bridge /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**For Apache** (add to your virtual host):

```apache
<Directory /var/www/buckleup.cc/brmesh-bridge>
    Options +Indexes +FollowSymLinks
    AllowOverride None
    Require all granted
    
    # Enable CORS for HACS
    Header set Access-Control-Allow-Origin "*"
    Header set Access-Control-Allow-Methods "GET, OPTIONS"
</Directory>

Alias /brmesh-bridge /var/www/buckleup.cc/brmesh-bridge
```

Reload Apache:
```bash
sudo systemctl reload apache2
```

---

## Step 6: Create Repository Manifest

Create a repository manifest at the root of your buckleup.cc site:

`/var/www/buckleup.cc/repositories.json`:

```json
{
  "repositories": [
    {
      "name": "BRMesh Bridge",
      "description": "Bridge BRMesh/Fastcon BLE lights to Home Assistant",
      "url": "http://www.buckleup.cc/brmesh-bridge",
      "category": "integration",
      "maintainer": "YOUR_NAME"
    }
  ]
}
```

---

## Step 7: Verify Deployment

Test that your repository is accessible:

```bash
# Test repository.json
curl http://www.buckleup.cc/brmesh-bridge/repository.json

# Test README
curl http://www.buckleup.cc/brmesh-bridge/README.md

# Test config
curl http://www.buckleup.cc/brmesh-bridge/config.yaml
```

All files should be accessible and return proper content.

---

## Step 8: Add to Home Assistant via HACS

### Method 1: Custom Repository

1. Open Home Assistant
2. Go to **HACS** → **Integrations**
3. Click ⋮ (three dots) → **Custom repositories**
4. Add:
   - **Repository**: `http://www.buckleup.cc/brmesh-bridge`
   - **Category**: Add-on
5. Click **Add**
6. Search for "BRMesh Bridge"
7. Click **Download**

### Method 2: Direct Add-on Installation

1. Go to **Settings** → **Add-ons**
2. Click **Add-on Store** → ⋮ → **Repositories**
3. Add: `http://www.buckleup.cc/brmesh-bridge`
4. The add-on appears in the store
5. Click **Install**

---

## Step 9: Set Up Auto-Updates

Create a cron job to automatically pull updates:

```bash
sudo crontab -e
```

Add:
```cron
# Update BRMesh Bridge repository hourly
0 * * * * cd /var/www/buckleup.cc/brmesh-bridge && git pull origin main
```

Or use a webhook for instant updates:

```bash
# Install webhook listener
sudo apt-get install webhook

# Create webhook configuration
cat > /etc/webhook/brmesh-bridge.json << 'EOF'
[
  {
    "id": "brmesh-bridge-update",
    "execute-command": "/usr/local/bin/update-brmesh-bridge.sh",
    "command-working-directory": "/var/www/buckleup.cc/brmesh-bridge",
    "trigger-rule": {
      "match": {
        "type": "payload-hash-sha1",
        "secret": "YOUR_SECRET_HERE",
        "parameter": {
          "source": "header",
          "name": "X-Hub-Signature"
        }
      }
    }
  }
]
EOF

# Create update script
sudo tee /usr/local/bin/update-brmesh-bridge.sh << 'EOF'
#!/bin/bash
cd /var/www/buckleup.cc/brmesh-bridge
git pull origin main
EOF

sudo chmod +x /usr/local/bin/update-brmesh-bridge.sh

# Start webhook service
sudo systemctl enable webhook
sudo systemctl start webhook
```

Configure GitHub webhook:
- URL: `http://www.buckleup.cc:9000/hooks/brmesh-bridge-update`
- Content type: `application/json`
- Secret: Your secret from above
- Events: Just the push event

---

## Step 10: Create Release Documentation

Create a `CHANGELOG.md`:

```markdown
# Changelog

## v2.0.0 - November 2025

### 🎉 Major Release: GUI Configuration

**New Features:**
- ✅ Complete web-based GUI configuration - no more manual file editing!
- ✅ Auto-detect Home Assistant location for map view
- ✅ Settings tab with all configuration options
- ✅ BLE discovery for phone-free light addition
- ✅ Import/export configuration
- ✅ ESPHome config generator
- ✅ 8 built-in lighting effects
- ✅ Scene management
- ✅ NSPanel integration
- ✅ Multi-controller support with signal strength monitoring

**Credits:**
- Huge thanks to [@scross01](https://github.com/scross01) for the esphome-fastcon component!

### Installation

```
Add custom repository: http://www.buckleup.cc/brmesh-bridge
```

See [QUICK_START.md](QUICK_START.md) for 5-minute setup guide.
```

---

## Maintenance

### Update the Add-on

When you make changes:

```bash
# Local machine
cd c:\Profiles\crval\Nextcloud\Projects\HomeAssistant\addons\brmesh-bridge
git add .
git commit -m "Update: description of changes"
git tag v2.0.1
git push origin main
git push origin v2.0.1

# Server will auto-update via cron/webhook
```

### Monitor Access Logs

```bash
# Nginx
sudo tail -f /var/log/nginx/access.log | grep brmesh-bridge

# Apache
sudo tail -f /var/log/apache2/access.log | grep brmesh-bridge
```

---

## Troubleshooting

### Repository Not Found

- Check web server configuration
- Verify files are accessible via browser: `http://www.buckleup.cc/brmesh-bridge/`
- Check file permissions: `sudo chown -R www-data:www-data /var/www/buckleup.cc/brmesh-bridge`

### Docker Images Not Pulling

- Verify images are public: Go to ghcr.io packages settings
- Check image tags match repository.json
- Test manually: `docker pull ghcr.io/YOUR_USERNAME/amd64-brmesh-bridge:latest`

### HACS Installation Fails

- Verify repository.json is valid JSON: `cat repository.json | jq`
- Check HACS logs in Home Assistant
- Ensure CORS headers are set correctly

---

## Alternative: Use GitHub Pages

If you prefer hosting on GitHub instead of buckleup.cc:

1. Push to GitHub
2. Enable GitHub Pages: Settings → Pages → Source: main branch
3. Repository URL becomes: `https://YOUR_USERNAME.github.io/ha-brmesh-bridge/`
4. Add to HACS using that URL

---

## Support

**Add-on Issues**: Create issue at your GitHub repository
**ESPHome Component**: Visit https://github.com/scross01/esphome-fastcon
**Server Issues**: Check buckleup.cc server logs

---

## Quick Reference

**Repository URL**: http://www.buckleup.cc/brmesh-bridge
**GitHub Repository**: https://github.com/YOUR_USERNAME/ha-brmesh-bridge
**Container Registry**: ghcr.io/YOUR_USERNAME/brmesh-bridge
**Web UI Port**: 8099
**HACS Category**: Add-on

**Files to Keep Updated**:
- README.md - User documentation
- config.yaml - Add-on configuration
- repository.json - HACS manifest
- CHANGELOG.md - Version history

Good luck with your deployment! 🚀
