"""
Script for system initialization:
- Creates database tables
- Creates admin user
- Creates test data
"""
import os
from pathlib import Path
import sys
import time
from datetime import datetime, timedelta

# Add parent directory to PYTHONPATH to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Track, Playlist, PlaylistTrack

def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=50, print_end="\r"):
    """
    Display progress bar in terminal using ASCII characters
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = '#' * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=print_end, flush=True)
    if iteration == total:
        print(flush=True)

def format_time(seconds):
    """
    Format time in seconds to readable format
    """
    return str(timedelta(seconds=int(seconds)))

def initialize_system():
    """
    Quick system initialization:
    - Creates/resets database
    - Creates admin user
    - Creates test data
    """
    start_time = time.time()
    total_steps = 4
    current_step = 0

    # Ensure app directory exists
    app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app')
    if not os.path.exists(app_dir):
        os.makedirs(app_dir)

    # Create application with correct database path
    current_step += 1
    print_progress_bar(current_step, total_steps, prefix='Progress:', suffix='Creating App')

    app = create_app()

    # Database configuration will be handled by Config class
    from config import Config
    app.config.from_object(Config)

    # Set application folders
    app.config['MUSIC_FOLDER'] = os.getenv('MUSIC_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'musiques'))
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads'))

    # Ensure folders exist
    for folder in [app.config['MUSIC_FOLDER'], app.config['UPLOAD_FOLDER']]:
        if not os.path.exists(folder):
            os.makedirs(folder)

    with app.app_context():
        # Initialize database
        current_step += 1
        print_progress_bar(current_step, total_steps, prefix='Progress:', suffix='Creating Database')

        try:
            db.session.execute('SELECT 1 FROM playlists')
            print("\n[*] Database tables exist, clearing data...")
        except Exception:
            print("\n[*] Database tables not found, creating schema...")
        db.drop_all()
        db.create_all()
        db.session.commit()

        # Create admin user
        current_step += 1
        print_progress_bar(current_step, total_steps, prefix='Progress:', suffix='Creating Admin')

        print("\n[*] Creating admin user...")
        admin = User(
            username='admin',
            email='admin@example.com',
            is_admin=True,
            is_active=True,
            can_access_mixer=True,
        )
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
        print("[+] Admin user created")

        # Create test data
        current_step += 1
        print_progress_bar(current_step, total_steps, prefix='Progress:', suffix='Creating Test Data')

        print("\n[*] Creating test playlist...")
        # Create test playlist
        test_playlist = Playlist(
            name="Test Playlist",
            description="A test playlist for migration",
            is_auto=False,
            is_smart=False,
            user_id=admin.id
        )
        db.session.add(test_playlist)

        # Create test track
        music_folder = app.config['MUSIC_FOLDER']
        test_file_path = os.path.join(music_folder, "test.mp3")

        test_track = Track(
            title="Test Track",
            artist="Test Artist",
            album="Test Album",
            genre="Test Genre",
            bpm=120.0,
            key="C",
            duration=180.0,
            file_path=test_file_path,
            file_format="mp3",
            file_size=1024,
            user_id=admin.id
        )
        db.session.add(test_track)
        db.session.commit()

        # Add track to playlist
        playlist_track = PlaylistTrack(
            playlist_id=test_playlist.id,
            track_id=test_track.id,
            position=0
        )
        db.session.add(playlist_track)
        db.session.commit()

        print("[+] Test data created successfully")

        total_time = time.time() - start_time
        print(f"\n[+] System initialization complete! ({format_time(total_time)})")
        print("[*] Login with admin/admin")

if __name__ == '__main__':
    initialize_system()
