#!/bin/bash

# Exit on error
set -e

echo "DJ Online Studio - Quick Start Script"
echo "===================================="

# Check Python version
echo "Checking Python version..."
python3 --version

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install or upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating directories..."
mkdir -p instance/uploads
mkdir -p migrations

# Set environment variables
export FLASK_APP=run.py
export FLASK_ENV=development

# Initialize database
echo "Initializing database..."
if [ -f "instance/dj_studio.db" ]; then
    echo "Removing old database..."
    rm instance/dj_studio.db
fi

flask db init
flask db migrate -m "Initial migration"
flask db upgrade

echo ""
echo "Setup complete! Start the application with:"
echo "python run.py"
echo ""
echo "Then visit http://localhost:5000 in your browser"
