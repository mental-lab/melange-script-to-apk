#!/bin/bash
# Verify Docker Compose setup

set -e

echo "Checking Melange APK Packaging setup..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker not found. Install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "ERROR: Docker Compose not found. Install Docker Compose first."
    exit 1
fi

echo "Docker and Docker Compose found"

# Check files
if [ ! -f "package-config.yaml" ]; then
    echo "ERROR: package-config.yaml not found"
    exit 1
fi

if [ ! -d "tools" ] || [ -z "$(ls -A tools 2>/dev/null)" ]; then
    echo "ERROR: No scripts found in tools/ directory"
    exit 1
fi

echo "Configuration files found"

# Test Docker Compose
docker-compose config > /dev/null 2>&1
echo "Docker Compose configuration valid"

echo ""
echo "Setup complete! Run 'make build' to create your APK package."
