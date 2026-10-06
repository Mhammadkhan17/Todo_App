#!/bin/bash

# Linting script for Todo Application
# This script runs code quality checks in the Docker environment

set -e

echo "🔍 Running Code Quality Checks"
echo "==============================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if backend service is running
if ! docker-compose ps backend | grep -q "Up"; then
    echo "⚠️  Backend service is not running. Starting backend..."
    docker-compose up -d backend
fi

echo "🔍 Running Black formatter check..."
docker-compose exec -T backend black --check --diff src/

echo "🔍 Running Ruff linter..."
docker-compose exec -T backend ruff check src/

echo "🔍 Running MyPy type checking..."
docker-compose exec -T backend mypy src/ --ignore-missing-imports

echo "✅ Code quality checks completed!"
echo ""
echo "💡 To fix formatting issues, run: docker-compose exec backend black src/"
echo "💡 To fix linting issues, run: docker-compose exec backend ruff check --fix src/"