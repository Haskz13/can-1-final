#!/bin/bash

echo "=== Canadian Procurement Scanner - Docker Startup ==="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Creating .env file from env.example..."
    cp env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  Please edit .env file to add your MERX credentials if you have them:"
    echo "   MERX_USERNAME=your_username"
    echo "   MERX_PASSWORD=your_password"
    echo ""
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "Starting the procurement scanner with Docker Compose..."
echo ""

# Start the services
docker-compose up -d

echo ""
echo "✓ Services starting up..."
echo ""
echo "Waiting for services to be ready..."

# Wait for backend to be healthy
echo -n "Waiting for backend API..."
for i in {1..30}; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo " ✓ Ready!"
        break
    fi
    echo -n "."
    sleep 2
done

# Wait for frontend to be ready
echo -n "Waiting for frontend..."
for i in {1..30}; do
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        echo " ✓ Ready!"
        break
    fi
    echo -n "."
    sleep 2
done

echo ""
echo "=== Application is ready! ==="
echo ""
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📊 API Documentation: http://localhost:8000/docs"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"
echo ""
echo "The application will now scan ALL 26 procurement portals:"
echo "- MERX (requires login credentials in .env)"
echo "- CanadaBuys"
echo "- All Provincial portals (BC, Alberta, Saskatchewan, Manitoba, Ontario, Quebec, Nova Scotia)"
echo "- Major Municipal portals (Calgary, Edmonton, Vancouver, Ottawa, etc.)"
echo "- Specialized portals (NBON, PEI, NL)"
echo "- Health/Education portals"
echo ""
echo "To trigger a manual scan: curl -X POST http://localhost:8000/api/scan"