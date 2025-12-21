#!/bin/bash

# Setup script for Infrastructure Inquiry Bot

echo "=========================================="
echo "Infrastructure Inquiry Bot Setup"
echo "=========================================="
echo ""

# Check if Python 3.12 is available
echo "1. Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Found Python $PYTHON_VERSION"

# Create virtual environment
echo ""
echo "2. Creating virtual environment..."
python3 -m venv venv
echo "   ✓ Virtual environment created"

# Activate virtual environment
echo ""
echo "3. Activating virtual environment..."
source venv/bin/activate
echo "   ✓ Activated"

# Install dependencies
echo ""
echo "4. Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "   ✓ Dependencies installed"

# Create .env file if it doesn't exist
echo ""
echo "5. Setting up environment file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "   ✓ Created .env file"
    echo "   ⚠️  IMPORTANT: Edit .env and add your Slack tokens!"
else
    echo "   ✓ .env file already exists"
fi

# Start Docker services
echo ""
echo "6. Starting Docker services..."
if command -v docker-compose &> /dev/null; then
    docker-compose up -d
    echo "   ✓ Docker services started"
    echo "   Waiting for services to be ready..."
    sleep 10
else
    echo "   ✗ docker-compose not found"
    echo "   Please install Docker and Docker Compose"
    exit 1
fi

# Check Ollama
echo ""
echo "7. Checking Ollama..."
if command -v ollama &> /dev/null; then
    echo "   ✓ Ollama found"
    echo "   Models available:"
    ollama list | head -5
else
    echo "   ✗ Ollama not found"
    echo "   Please install Ollama from https://ollama.ai"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your Slack tokens:"
echo "   - SLACK_BOT_TOKEN"
echo "   - SLACK_APP_TOKEN"
echo ""
echo "2. Test the setup:"
echo "   python test_setup.py"
echo ""
echo "3. Start the bot:"
echo "   python src/main.py"
echo ""
echo "=========================================="
