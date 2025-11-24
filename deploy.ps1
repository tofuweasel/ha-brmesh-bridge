# Deploy BRMesh Bridge to us001.buckleup.cc Docker container
# PowerShell version

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying BRMesh Bridge to us001.buckleup.cc..." -ForegroundColor Green

# Variables
$SERVER = "us001"
$CONTAINER_NAME = "buckleup"
$DEPLOY_PATH = "/usr/share/nginx/html/brmesh-bridge"
$LOCAL_PATH = "."

# Files to deploy
$FILES = @(
    "config.yaml",
    "Dockerfile",
    "run.sh",
    "brmesh_bridge.py",
    "effects.py",
    "web_ui.py",
    "esphome_generator.py",
    "ble_discovery.py",
    "app_importer.py",
    "nspanel_ui.py",
    "repository.json",
    "hacs.json",
    "README.md",
    "QUICK_START.md",
    "GUI_CONFIGURATION.md",
    "NEW_FEATURES.md",
    "SETUP_GUIDE.md",
    "DEPLOYMENT.md",
    "CHANGELOG.md"
)

$FOLDERS = @("static", "templates")

# Check SSH connection
Write-Host "📡 Checking connection to $SERVER..." -ForegroundColor Cyan
try {
    ssh -q $SERVER "exit"
    Write-Host "✅ Connected to $SERVER" -ForegroundColor Green
} catch {
    Write-Host "❌ Cannot connect to $SERVER. Please check your SSH connection." -ForegroundColor Red
    exit 1
}

# Create deployment directory in container
Write-Host "📁 Creating deployment directory..." -ForegroundColor Cyan
ssh $SERVER "docker exec $CONTAINER_NAME mkdir -p $DEPLOY_PATH"

# Create temp directory on server
Write-Host "📦 Creating temporary directory on server..." -ForegroundColor Cyan
ssh $SERVER "mkdir -p /tmp/brmesh-bridge"

# Copy files to server
Write-Host "📤 Copying files to server..." -ForegroundColor Cyan
foreach ($file in $FILES) {
    if (Test-Path $file) {
        scp $file "${SERVER}:/tmp/brmesh-bridge/"
        Write-Host "  ✓ $file" -ForegroundColor Gray
    } else {
        Write-Host "  ⚠ Skipping $file (not found)" -ForegroundColor Yellow
    }
}

# Copy folders to server
Write-Host "📤 Copying folders to server..." -ForegroundColor Cyan
foreach ($folder in $FOLDERS) {
    if (Test-Path $folder) {
        scp -r $folder "${SERVER}:/tmp/brmesh-bridge/"
        Write-Host "  ✓ $folder/" -ForegroundColor Gray
    } else {
        Write-Host "  ⚠ Skipping $folder (not found)" -ForegroundColor Yellow
    }
}

# Move files into container
Write-Host "🐳 Moving files into Docker container..." -ForegroundColor Cyan
ssh $SERVER "docker cp /tmp/brmesh-bridge/. $CONTAINER_NAME`:$DEPLOY_PATH/"

# Set permissions
Write-Host "🔒 Setting permissions..." -ForegroundColor Cyan
ssh $SERVER "docker exec $CONTAINER_NAME chmod -R 755 $DEPLOY_PATH"
ssh $SERVER "docker exec $CONTAINER_NAME chown -R nginx:nginx $DEPLOY_PATH"

# Cleanup temp files on server
Write-Host "🧹 Cleaning up temporary files..." -ForegroundColor Cyan
ssh $SERVER "rm -rf /tmp/brmesh-bridge"

# Verify deployment
Write-Host "✅ Verifying deployment..." -ForegroundColor Cyan
try {
    ssh $SERVER "docker exec $CONTAINER_NAME test -f $DEPLOY_PATH/repository.json"
    Write-Host ""
    Write-Host "✅ Deployment successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📍 Repository is now available at:" -ForegroundColor Cyan
    Write-Host "   http://www.buckleup.cc/brmesh-bridge" -ForegroundColor White
    Write-Host ""
    Write-Host "🔗 Add to Home Assistant:" -ForegroundColor Cyan
    Write-Host "   HACS → Custom Repositories → http://www.buckleup.cc/brmesh-bridge" -ForegroundColor White
} catch {
    Write-Host "❌ Deployment verification failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🎉 Deployment complete!" -ForegroundColor Green
