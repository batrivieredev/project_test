"""
Script d'initialisation rapide du système:
- Crée les tables de la base de données
- Crée l'utilisateur admin par défaut
- Scanne uniquement les dossiers de musique principaux
"""

from app import create_app, db
from app.models import User, Track, Playlist, PlaylistTrack
import os
from pathlib import Path
import mutagen
from mutagen.mp3 import MP3
import librosa
import numpy as np

def process_audio_file(file_path, playlist, user_id):
    """
    Traite un fichier audio MP3:
    - Extrait les métadonnées (titre, artiste, BPM)
    - Crée un objet Track dans la base de données
    """
    try:
        # Check if track exists
        track = Track.query.filter_by(file_path=file_path, user_id=user_id).first()

        if not track:
            # Extract metadata
            audio = MP3(file_path)
            title = os.path.splitext(os.path.basename(file_path))[0]
            artist = 'Unknown Artist'

            if audio.tags:
                try:
                    title = audio.tags.get('TIT2', [title])[0].text[0]
                    artist = audio.tags.get('TPE1', [artist])[0].text[0]
                except (KeyError, IndexError, AttributeError):
                    pass
                print(f"📝 Adding track: {title} - {artist}")

                # Detect BPM
                bpm = None
                if file_path.lower().endswith('.mp3'):
                    print("📊 Analyzing BPM...")
                    try:
                        audio_mp3 = MP3(file_path)
                        if audio_mp3.tags and 'TBPM' in audio_mp3.tags:
                            try:
                                bpm = float(audio_mp3.tags['TBPM'].text[0])
                                if not (40 <= bpm <= 220):  # Validate BPM range
                                    bpm = None
                            except (ValueError, IndexError, AttributeError):
                                bpm = None
                    except Exception as e:
                        print(f"⚠️ Error reading ID3 BPM: {str(e)}")

                if bpm is None:
                    try:
                        y, sr = librosa.load(file_path, duration=30, sr=22050)
                        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
                        tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
                        bpm = round(tempo, 2)
                        if not (40 <= bpm <= 220):  # Validate BPM range
                            bpm = None
                    except Exception as e:
                        print(f"⚠️ Error analyzing BPM: {str(e)}")
                        bpm = None

                track = Track(
                    title=title,
                    artist=artist,
                    bpm=bpm,
                    key=audio.get('key', [None])[0],
                    file_path=file_path,
                    file_format='mp3',
                    file_size=os.path.getsize(file_path),
                    user_id=user_id
                )
                db.session.add(track)
                db.session.flush()

                # Add to playlist
                position = len(playlist.tracks)
                playlist_track = PlaylistTrack(
                    playlist_id=playlist.id,
                    track_id=track.id,
                    position=position
                )
                db.session.add(playlist_track)
                db.session.flush()

        return track

    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        db.session.rollback()
        return None

def scan_music_folder(folder_path, user_id):
    """
    Scanne un dossier de musique:
    - Recherche uniquement les fichiers MP3
    - Pas de scan récursif des sous-dossiers
    """
    folder_name = os.path.basename(folder_path)
    print(f"\n📂 Scanning folder: {folder_name}")

    try:
        # Find MP3 files only
        music_files = [f for f in os.listdir(folder_path)
                      if os.path.isfile(os.path.join(folder_path, f))
                      and f.lower().endswith('.mp3')]

        if music_files:
            print(f"🎵 Found {len(music_files)} MP3 files")

            # Get or create playlist
            playlist = Playlist.query.filter_by(folder_path=folder_path, user_id=user_id).first()

            if not playlist:
                print(f"📝 Creating playlist: {folder_name}")
                playlist = Playlist(
                    name=folder_name,
                    folder_path=folder_path,
                    is_auto=True,
                    user_id=user_id
                )
                db.session.add(playlist)
                db.session.flush()

            # Process files
            for filename in music_files:
                file_path = os.path.join(folder_path, filename)
                process_audio_file(file_path, playlist, user_id)

            db.session.commit()
            print(f"✅ Finished processing {folder_name}")

    except Exception as e:
        print(f"❌ Error scanning {folder_name}: {str(e)}")
        db.session.rollback()

def initialize_system():
    """
    Initialise le système rapidement:
    - Crée/réinitialise la base de données
    - Crée l'utilisateur admin
    - Scanne uniquement les dossiers principaux
    """
    app = create_app()

    with app.app_context():
        print("\n🗄️  Initializing database...")
        try:
            db.session.execute('SELECT 1 FROM playlists')
            print("✓ Database tables exist, clearing data...")
        except Exception:
            print("⚠️  Database tables not found, creating schema...")

        # Recrée toutes les tables
        db.drop_all()
        db.create_all()
        db.session.commit()

        print("\n👤 Creating admin user...")
        # Create admin user with full permissions
        admin = User(
            username='admin',
            email='admin@example.com',
            is_admin=True,
            is_active=True,
            can_access_mixer=True,
            can_access_converter=True
        )
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin user created")

        print("\n🔍 Scanning music folders...")
        # Scan only main music folders
        main_dirs = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads'),
            os.path.join(str(Path.home()), 'Music')
        ]

        for directory in main_dirs:
            if os.path.exists(directory) and os.path.isdir(directory):
                print(f"✓ Scanning music directory: {directory}")
                scan_music_folder(directory, admin.id)

        print("\n✅ System initialization complete!")
        print("🔑 Login with admin/admin")

if __name__ == '__main__':
    initialize_system()
