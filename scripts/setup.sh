#!/bin/bash

# Setup script for Todo Application Development Environment
# This script sets up the complete development environment

set -e

echo "🔧 Setting up Todo Application Development Environment"
echo "====================================================="

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker and try again."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose and try again."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "✅ Prerequisites check passed!"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p data/postgres
mkdir -p data/redis

# Set proper permissions
echo "🔒 Setting permissions..."
chmod +x scripts/*.sh
chmod 600 .env.development || true

# Build Docker images
echo "🔨 Building Docker images..."
docker-compose build

# Initialize database
echo "🗄️  Initializing database..."
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
until docker-compose exec -T postgres pg_isready -U todo_user -d todo_app; do
  echo "⏳ Waiting for database connection..."
  sleep 2
done

echo "✅ Database initialization completed!"

echo ""
echo "🎉 Development environment setup completed!"
echo ""
echo "📋 Next steps:"
echo "   1. Start the development environment: ./scripts/dev-start.sh"
echo "   2. Run tests: ./scripts/test.sh"
echo "   3. Check code quality: ./scripts/lint.sh"
echo ""
echo "💡 For more information, check the README.md file"