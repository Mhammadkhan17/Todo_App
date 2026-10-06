#!/bin/bash

# Development startup script for Todo Application
# This script sets up and starts the development environment

set -e

echo "🚀 Starting Todo Application Development Environment"
echo "=================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install it and try again."
    exit 1
fi

# Load environment variables
ENV_FILE=".env.development"
if [ -f "$ENV_FILE" ]; then
    echo "✅ Loading environment from $ENV_FILE"
    export $(cat $ENV_FILE | grep -v '^#' | xargs)
else
    echo "⚠️  Warning: $ENV_FILE not found, using default environment"
fi

# Build and start services
echo "🔨 Building Docker images..."
docker-compose build --no-cache backend

echo "🐳 Starting services..."
docker-compose up -d postgres redis

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
until docker-compose exec -T postgres pg_isready -U todo_user -d todo_app; do
  echo "⏳ Waiting for database connection..."
  sleep 2
done

echo "✅ PostgreSQL is ready!"

# Start the backend service
echo "🚀 Starting backend service..."
docker-compose up -d backend

# Wait for backend to be ready
echo "⏳ Waiting for backend to be ready..."
until curl -f http://localhost:8000/health > /dev/null 2>&1; do
  echo "⏳ Waiting for backend..."
  sleep 2
done

echo "✅ Backend is ready!"

# Start Adminer for database management (optional)
if [ "${ADMINER_ENABLED:-true}" = "true" ]; then
    echo "🌐 Starting Adminer for database management..."
    docker-compose up -d adminer
    echo "✅ Adminer is available at http://localhost:8080"
fi

echo ""
echo "🎉 Development environment is ready!"
echo ""
echo "📋 Services:"
echo "   - Backend API: http://localhost:8000"
echo "   - API Documentation: http://localhost:8000/api/docs"
echo "   - Adminer: http://localhost:8080 (optional)"
echo ""
echo "🔧 Useful commands:"
echo "   - View logs: docker-compose logs -f backend"
echo "   - Stop services: docker-compose down"
echo "   - Restart backend: docker-compose restart backend"
echo "   - Run tests: docker-compose exec backend pytest"
echo ""
echo "💡 For development with hot reload, use: docker-compose up backend"