#!/bin/bash

echo "🎵 === DJ Pro Startup Script === 🎵"
echo

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python requirements
if ! command_exists python3; then
    echo "❌ Error: Python 3 is required but not installed."
    exit 1
fi

if ! command_exists pip3; then
    echo "❌ Error: pip3 is required but not installed."
    exit 1
fi

# Check for virtual environment
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

echo "📦 Installing/updating dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Setting up directories..."
mkdir -p instance uploads

# Initialize database
echo "🗄️  Initializing database..."
python setup_db.py

# Run system tests
echo "🧪 Running system tests..."
python test_system.py

if [ $? -ne 0 ]; then
    echo "❌ Error: System tests failed. Please fix the issues before starting the application."
    exit 1
else
    echo "✅ System tests passed!"
fi

# Clean up old processes
echo "🧹 Cleaning up old processes..."
pkill -f "python app.py" || true

# Start the application
echo "🚀 Starting DJ Pro..."
echo "🔑 Default login credentials:"
echo "👤 Username: admin"
echo "🔒 Password: admin"
echo
echo "🌐 Server will be available at: http://localhost:5000"
echo
python app.py

# Deactivate virtual environment on exit
deactivate
