#!/bin/bash

# Development shutdown script for Todo Application
# This script stops and cleans up the development environment

set -e

echo "🛑 Stopping Todo Application Development Environment"
echo "=================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running."
    exit 1
fi

# Stop all services
echo "🛑 Stopping all services..."
docker-compose down

echo "🧹 Cleaning up unused Docker resources..."
docker system prune -f --volumes

echo "✅ Development environment stopped and cleaned!"
echo ""
echo "💡 To start again, run: ./scripts/dev-start.sh"