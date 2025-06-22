#!/bin/bash

# Frontend Local Development Setup Script
# This script helps set up Node.js and frontend dependencies for local development

echo "🚀 Setting up Frontend for Local Development"
echo "============================================="

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "📦 Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH (for Apple Silicon Macs)
    if [[ $(uname -m) == 'arm64' ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    echo "✅ Homebrew is already installed"
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "📦 Installing Node.js..."
    brew install node
else
    echo "✅ Node.js is already installed: $(node --version)"
fi

# Check if npm is available
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not available. Please check your Node.js installation."
    exit 1
else
    echo "✅ npm is available: $(npm --version)"
fi

# Navigate to frontend directory
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
else
    echo "✅ Frontend dependencies are already installed"
fi

echo ""
echo "🎉 Frontend setup complete!"
echo ""
echo "To start the development server:"
echo "  cd frontend"
echo "  npm start"
echo ""
echo "The frontend will be available at: http://localhost:3000"
echo ""
echo "Note: The backend API should be running at: http://localhost:8000" 