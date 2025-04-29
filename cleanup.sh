#!/bin/bash

echo "Cleaning up duplicate and unnecessary files..."

# Remove old JavaScript files
rm -rf js/

# Remove old CSS and HTML files from root
rm -f styles.css
rm -f index.html
rm -f script.js

# Remove any Python cache files
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete

# Remove test coverage files if they exist
rm -rf htmlcov/
rm -f .coverage

echo "Cleanup completed!"
