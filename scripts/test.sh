#!/bin/bash

# Test script for Todo Application
# This script runs tests in the Docker environment

set -e

echo "🧪 Running Todo Application Tests"
echo "================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if services are running
if ! docker-compose ps | grep -q "Up"; then
    echo "⚠️  Services are not running. Starting services first..."
    ./scripts/dev-start.sh
fi

echo "🧪 Running unit tests..."
docker-compose exec -T backend pytest tests/ -v --tb=short

echo "🧪 Running integration tests..."
docker-compose exec -T backend pytest tests/integration/ -v --tb=short

echo "🧪 Running security tests..."
docker-compose exec -T backend pytest tests/security/ -v --tb=short

echo "✅ All tests completed!"
echo ""
echo "📊 Test results available in the output above."
echo "💡 To run specific tests, use: docker-compose exec backend pytest <test_path>"