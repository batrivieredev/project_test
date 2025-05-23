#!/bin/bash

echo "=== DJ Pro System Verification ==="
echo

# Function to check if a command exists
check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        echo "✓ $1 found"
        return 0
    else
        echo "✗ $1 not found"
        return 1
    }
}

# Function to check Python package
check_package() {
    if python3 -c "import $1" 2>/dev/null; then
        echo "✓ Python package $1 found"
        return 0
    else
        echo "✗ Python package $1 not found"
        return 1
    }
}

# Function to check directory
check_directory() {
    if [ -d "$1" ]; then
        echo "✓ Directory $1 exists"
        return 0
    else
        echo "✗ Directory $1 not found"
        return 1
    }
}

# Function to check file
check_file() {
    if [ -f "$1" ]; then
        echo "✓ File $1 exists"
        return 0
    else
        echo "✗ File $1 not found"
        return 1
    }
}

echo "Checking system requirements..."
check_command "python3"
check_command "pip3"
check_command "ffmpeg"

echo
echo "Checking virtual environment..."
check_directory "venv"
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo
echo "Checking Python packages..."
packages=(
    "flask"
    "flask_sqlalchemy"
    "flask_login"
    "mutagen"
    "librosa"
    "numpy"
    "soundfile"
)

missing_packages=()
for package in "${packages[@]}"; do
    if ! check_package "$package"; then
        missing_packages+=("$package")
    fi
done

echo
echo "Checking directories..."
check_directory "instance"
check_directory "uploads"
check_directory "app"
check_directory "app/static"
check_directory "app/templates"

echo
echo "Checking configuration files..."
check_file "config.py"
check_file ".env"
check_file "app.py"

echo
echo "Checking database..."
if ! check_file "instance/app.db"; then
    echo "Creating database..."
    python3 setup_db.py
fi

echo
echo "Checking audio processing..."
if [ ${#missing_packages[@]} -eq 0 ]; then
    python3 -c '
import librosa
import soundfile as sf
import numpy as np

print("✓ Audio processing libraries working correctly")
'
else
    echo "✗ Missing required packages: ${missing_packages[*]}"
    echo "Please run: pip install ${missing_packages[*]}"
fi

echo
echo "Verifying test suite..."
python3 -c '
import unittest
import test_system

runner = unittest.TextTestRunner(verbosity=0)
result = runner.run(unittest.defaultTestLoader.loadTestsFromModule(test_system))

if result.wasSuccessful():
    print("✓ All tests passed")
else:
    print("✗ Some tests failed")
'

echo
echo "Verifying application startup..."
# Try to start the application
timeout 5s python3 app.py > /dev/null 2>&1 &
APP_PID=$!

# Wait a moment
sleep 2

# Check if application is running
if kill -0 $APP_PID 2>/dev/null; then
    echo "✓ Application starts successfully"
    kill $APP_PID
else
    echo "✗ Application failed to start"
fi

echo
if [ ${#missing_packages[@]} -eq 0 ] && [ -f "instance/app.db" ]; then
    echo "System verification complete. All components are ready."
else
    echo "System verification complete. Some components need attention."
    echo "Please fix the reported issues and run this script again."
fi
