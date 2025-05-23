#!/bin/bash

echo "=== DJ Pro System Verification ==="
echo

# Check Python version
echo "1. Checking Python installation..."
python3 --version
if [ $? -ne 0 ]; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check pip installation
echo "2. Checking pip installation..."
python3 -m pip --version
if [ $? -ne 0 ]; then
    echo "Error: pip is not installed"
    exit 1
fi

# Check required directories
echo "3. Checking required directories..."
for dir in "instance" "uploads" "app/static/css" "app/static/js"; do
    if [ ! -d "$dir" ]; then
        echo "Creating $dir directory..."
        mkdir -p "$dir"
    fi
done

# Check required files
echo "4. Checking required files..."
required_files=(
    "requirements.txt"
    "app/__init__.py"
    "app/models.py"
    "app/routes.py"
    "app/static/css/style.css"
    "app/static/css/mixer.css"
    "app/static/js/main.js"
    "app/static/js/mixer.js"
    "app/static/js/deck-controller.js"
    "app/static/js/track-library.js"
    "app/static/js/audio-engine.js"
    "app/static/js/effect-chain.js"
    "app/templates/base.html"
    "app/templates/login.html"
    "app/templates/mixer.html"
)

missing_files=0
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "Missing required file: $file"
        missing_files=$((missing_files + 1))
    fi
done

if [ $missing_files -gt 0 ]; then
    echo "Error: Missing $missing_files required files"
    exit 1
fi

# Check permissions
echo "5. Checking file permissions..."
chmod +x launch.sh
chmod -R 755 app/static uploads instance

# Install dependencies
echo "6. Installing dependencies..."
python3 -m pip install -r requirements.txt

# Clean up old processes and files
echo "7. Cleaning up..."
pkill -f "python3 app.py" || true
rm -f instance/app.db app/app.db

# Initialize database
echo "8. Initializing database..."
python3 setup_db.py

if [ $? -eq 0 ]; then
    echo
    echo "Verification completed successfully!"
    echo
    echo "You can now run the application using:"
    echo "./launch.sh"
    echo
    echo "Default login credentials:"
    echo "Username: admin"
    echo "Password: admin"
    echo
    read -p "Would you like to start the application now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ./launch.sh
    fi
else
    echo "Error: Database initialization failed"
    exit 1
fi
