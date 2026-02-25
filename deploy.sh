#!/bin/bash

# Q&ACE Deployment Script

echo "🚀 Starting Q&ACE deployment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
mkdir -p outputs
mkdir -p models

echo "📦 Building Docker images..."
docker-compose build

echo "🔧 Starting services..."
docker-compose up -d

echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Q&ACE services are running!"
    echo "🌐 Frontend: http://localhost:3000"
    echo "🔌 Backend API: http://localhost:8001"
    echo "📊 API Docs: http://localhost:8001/docs"
else
    echo "❌ Failed to start services. Check logs:"
    docker-compose logs
    exit 1
fi

echo "🎯 Deployment complete! Access your application at http://localhost:3000"