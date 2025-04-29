import subprocess
import sys
import os
from pathlib import Path

def setup_environment():
    """Set up the development environment"""
    print("Setting up DJ Online Studio development environment...")

    # Create necessary directories
    directories = [
        'instance',
        'instance/uploads',
        'migrations'
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")

    # Install requirements
    print("\nInstalling requirements...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])

    # Initialize database
    print("\nInitializing database...")
    try:
        from flask.cli import FlaskGroup
        from dj_online_studio import create_app

        app = create_app()
        with app.app_context():
            from dj_online_studio.extensions import db
            db.create_all()
            print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

    print("\nSetup completed successfully!")
    print("\nYou can now run the application with:")
    print("python run.py")

    return True

if __name__ == '__main__':
    setup_environment()
