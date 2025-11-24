#!/bin/bash
# Deploy BRMesh Bridge to us001.buckleup.cc Docker container

set -e

echo "🚀 Deploying BRMesh Bridge to us001.buckleup.cc..."

# Variables
SERVER="us001"
CONTAINER_NAME="buckleup"
DEPLOY_PATH="/usr/share/nginx/html/brmesh-bridge"
LOCAL_PATH="."

# Check if we can reach the server
echo "📡 Checking connection to $SERVER..."
if ! ssh -q $SERVER exit; then
    echo "❌ Cannot connect to $SERVER. Please check your SSH connection."
    exit 1
fi

echo "✅ Connected to $SERVER"

# Create deployment directory in container
echo "📁 Creating deployment directory..."
ssh $SERVER "docker exec $CONTAINER_NAME mkdir -p $DEPLOY_PATH"

# Copy files to server
echo "📦 Copying files to server..."
scp -r \
    config.yaml \
    Dockerfile \
    run.sh \
    brmesh_bridge.py \
    effects.py \
    web_ui.py \
    esphome_generator.py \
    ble_discovery.py \
    app_importer.py \
    nspanel_ui.py \
    repository.json \
    hacs.json \
    README.md \
    QUICK_START.md \
    GUI_CONFIGURATION.md \
    NEW_FEATURES.md \
    SETUP_GUIDE.md \
    DEPLOYMENT.md \
    CHANGELOG.md \
    static \
    templates \
    $SERVER:/tmp/brmesh-bridge/

# Move files into container
echo "🐳 Moving files into Docker container..."
ssh $SERVER "docker cp /tmp/brmesh-bridge/. $CONTAINER_NAME:$DEPLOY_PATH/"

# Set permissions
echo "🔒 Setting permissions..."
ssh $SERVER "docker exec $CONTAINER_NAME chmod -R 755 $DEPLOY_PATH"
ssh $SERVER "docker exec $CONTAINER_NAME chown -R nginx:nginx $DEPLOY_PATH"

# Cleanup temp files on server
ssh $SERVER "rm -rf /tmp/brmesh-bridge"

# Verify deployment
echo "✅ Verifying deployment..."
if ssh $SERVER "docker exec $CONTAINER_NAME test -f $DEPLOY_PATH/repository.json"; then
    echo "✅ Deployment successful!"
    echo ""
    echo "📍 Repository is now available at:"
    echo "   http://www.buckleup.cc/brmesh-bridge"
    echo ""
    echo "🔗 Add to Home Assistant:"
    echo "   HACS → Custom Repositories → http://www.buckleup.cc/brmesh-bridge"
else
    echo "❌ Deployment verification failed"
    exit 1
fi

echo ""
echo "🎉 Deployment complete!"
