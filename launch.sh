#!/bin/bash

echo "=== DJ Pro Installation ==="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to display progress
show_progress() {
    echo
    echo "=== $1 ==="
}

# Check system requirements
show_progress "Checking system requirements"

if ! command_exists python3; then
    echo "Error: Python 3 is required but not installed."
    echo "Please install Python 3 and try again."
    exit 1
fi

if ! command_exists pip3; then
    echo "Error: pip3 is required but not installed."
    echo "Please install pip3 and try again."
    exit 1
fi

if ! command_exists git; then
    echo "Error: git is required but not installed."
    echo "Please install git and try again."
    exit 1
fi

# Set up virtual environment
show_progress "Setting up virtual environment"

if [ -d "venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf venv
fi

python3 -m venv venv
source venv/bin/activate

# Install dependencies
show_progress "Installing dependencies"
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
show_progress "Creating directories"
mkdir -p instance uploads

# Set up database
show_progress "Setting up database"

# Remove old database if it exists
if [ -f "instance/app.db" ]; then
    rm instance/app.db
fi

# Initialize database and create admin user
python setup_db.py

if [ $? -ne 0 ]; then
    echo "Error: Database initialization failed."
    exit 1
fi

# Run system tests
show_progress "Running system tests"
python test_system.py

if [ $? -ne 0 ]; then
    echo "Warning: Some tests failed. The application may not work correctly."
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Set file permissions
show_progress "Setting file permissions"
chmod +x start.sh restart.sh verify_components.sh

# Create default configuration
show_progress "Creating configuration"
cat > config.py << EOL
import os

class Config:
    SECRET_KEY = os.urandom(24).hex()
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # 64MB max file size
EOL

# Final setup
show_progress "Completing installation"

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    cat > .gitignore << EOL
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
instance/
.env
*.db
uploads/
.DS_Store
EOL
fi

echo
echo "Installation complete!"
echo
echo "You can now start the application using:"
echo "./start.sh"
echo
echo "Default login credentials:"
echo "Username: admin"
echo "Password: admin"
echo
echo "Would you like to start the application now?"
read -p "(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ./start.sh
fi
