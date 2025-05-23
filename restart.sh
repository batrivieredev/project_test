#!/bin/bash

echo "=== DJ Pro Restart Script ==="

# Function to check if a process is running
is_running() {
    pgrep -f "$1" >/dev/null
}

# Function to gracefully stop the application
stop_app() {
    echo "Stopping DJ Pro..."
    pkill -f "python app.py"

    # Wait for process to stop
    while is_running "python app.py"; do
        echo "Waiting for application to stop..."
        sleep 1
    done
}

# Function to start the application
start_app() {
    echo "Starting DJ Pro..."

    # Activate virtual environment if it exists
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi

    # Check dependencies
    echo "Checking dependencies..."
    pip install -r requirements.txt > /dev/null

    # Scan for new music
    echo "Scanning music library..."
    curl -s "http://localhost:5000/api/scan-music" || true

    # Start application
    echo "Server will be available at: http://localhost:5000"
    python app.py &

    # Wait for application to start
    sleep 2
    if is_running "python app.py"; then
        echo "DJ Pro successfully restarted!"
    else
        echo "Error: Failed to start DJ Pro"
        exit 1
    fi
}

# Main restart logic
if is_running "python app.py"; then
    stop_app
fi

start_app

# Trap Ctrl+C and cleanup
trap 'stop_app; exit 0' INT

# Keep script running to handle Ctrl+C gracefully
while true; do
    sleep 1
    if ! is_running "python app.py"; then
        echo "Application stopped unexpectedly!"
        exit 1
    fi
done
