#!/bin/bash

IMAGE_NAME="eth-monitor"
TAG="latest"
FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"

echo "🚧 Building Docker image: $FULL_IMAGE_NAME"
docker build -t "$FULL_IMAGE_NAME" .

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

echo "✅ Build successful: $FULL_IMAGE_NAME"

echo
echo "📦 Available eth-monitor images:"
docker images | grep "$IMAGE_NAME"

echo
echo "👉 You can now run the image with:"
echo "docker run -d \\"
echo "  -v \$(pwd)/data:/data \\"
echo "  -e PUBKEYS_FILE=/data/pubkeys.txt \\"
echo "  -e BEACON_API=http://<BEACON-IP>:<BEACON-PORT> \\"
echo "  -p 8080:8080 \\"
echo "  $FULL_IMAGE_NAME"
