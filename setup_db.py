"""
Script principal d'initialisation de la base de données et du scan de la bibliothèque musicale.
Ce script:
- Crée les tables de la base de données
- Crée l'utilisateur admin par défaut
- Scanne les dossiers de musique pour créer les playlists
- N'analyse pas les BPM au démarrage pour être plus rapide
"""

from app import create_app, db
from app.models import User, Track, Playlist, PlaylistTrack
import os
from pathlib import Path
import mutagen
from mutagen.mp3 import MP3
import librosa
import numpy as np

# Vérifie si librosa est installé pour l'analyse BPM
try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    print("⚠️ Attention: librosa n'est pas installé. La détection BPM sera désactivée.")
    HAS_LIBROSA = False

def process_audio_file(file_path, playlist, user_id):
    """
    Traite un fichier audio:
    - Extrait les métadonnées (titre, artiste)
    - Crée un objet Track dans la base de données
    - Ajoute le morceau à la playlist si nécessaire
    - Ne fait pas l'analyse BPM (sera fait lors du chargement dans un deck)
    """
    """Process a single audio file"""
    try:
        # Check if track exists
        track = Track.query.filter_by(file_path=file_path, user_id=user_id).first()

        if not track:
            # Extract metadata
            audio = mutagen.File(file_path, easy=True)
            if audio:
                title = audio.get('title', [os.path.splitext(os.path.basename(file_path))[0]])[0]
                artist = audio.get('artist', ['Unknown Artist'])[0]
                print(f"📝 Adding track: {title} - {artist}")

                track = Track(
                    title=title,
                    artist=artist,
                    bpm=None,  # ⏳ BPM will be analyzed when loaded in a deck
                    key=audio.get('key', [None])[0],
                    file_path=file_path,
                    file_format=file_path.rsplit('.', 1)[1].lower(),
                    file_size=os.path.getsize(file_path),
                    user_id=user_id
                )
                db.session.add(track)
                db.session.flush()

        # Add to playlist if not already there
        if not any(pt.track_id == track.id for pt in playlist.tracks):
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
    Scanne un dossier pour trouver les fichiers musicaux:
    - Recherche tous les fichiers audio supportés
    - Crée une playlist pour le dossier s'il n'existe pas
    - Traite chaque fichier trouvé
    - Scanne récursivement les sous-dossiers
    - Affiche la progression avec des emojis
    """
    allowed_extensions = {'mp3', 'wav', 'aiff', 'ogg', 'm4a'}
    folder_name = os.path.basename(folder_path)

    print(f"\n📂 Scanning folder: {folder_name}")

    try:
        # Find music files
        music_files = [f for f in os.listdir(folder_path)
                      if os.path.isfile(os.path.join(folder_path, f))
                      and f.split('.')[-1].lower() in allowed_extensions]

        if music_files:
            print(f"🎵 Found {len(music_files)} music files")

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
            else:
                print(f"ℹ️  Using existing playlist: {folder_name}")

            # Process files
            for i, filename in enumerate(music_files, 1):
                file_path = os.path.join(folder_path, filename)
                print(f"  ({i}/{len(music_files)}) Processing {filename}")
                process_audio_file(file_path, playlist, user_id)

            db.session.commit()
            print(f"✅ Finished processing {folder_name}")

        # Recursively scan subfolders
        subfolders = [d for d in os.listdir(folder_path)
                     if os.path.isdir(os.path.join(folder_path, d))]

        if subfolders:
            print(f"📂 Found {len(subfolders)} subfolders in {folder_name}")
            for subfolder in subfolders:
                scan_music_folder(os.path.join(folder_path, subfolder), user_id)

    except Exception as e:
        print(f"❌ Error scanning {folder_name}: {str(e)}")
        db.session.rollback()

def init_db():
    """
    Initialise la base de données:
    - Supprime les tables existantes
    - Crée les nouvelles tables
    - Crée l'utilisateur admin par défaut
    - Lance le scan des dossiers de musique
    - Affiche les logs avec des emojis pour suivre la progression
    """
    app = create_app()

    with app.app_context():
        print("🗄️  Initializing database...")
        try:
            # Vérifie si les tables existent
            db.session.execute('SELECT 1 FROM playlists')
            print("✓ Database tables exist, clearing data...")
        except Exception:
            print("⚠️  Database tables not found, creating schema...")

        # Recrée toutes les tables
        db.drop_all()
        db.create_all()
        db.session.commit()

        print("\n👤 Creating admin user...")
        admin = User(
            username='admin',
            email='admin@example.com',
            is_admin=True
        )
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()

        print("\n🔍 Scanning music folders...")
        print("📂 Looking for music in default locations:")
        music_dirs = []
        home = str(Path.home())

        potential_dirs = [
            os.path.join(home, 'Music'),
            os.path.join(home, 'Downloads'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
        ]

        for directory in potential_dirs:
            if os.path.exists(directory) and os.path.isdir(directory):
                print(f"✓ Found music directory: {directory}")
                music_dirs.append(directory)
                try:
                    scan_music_folder(directory, admin.id)
                except Exception as e:
                    print(f"❌ Error scanning {directory}: {str(e)}")
                    db.session.rollback()

        print("\n✅ Database initialization complete!")
        print("🔑 Default admin user credentials:")
        print("👤 Username: admin")
        print("🔒 Password: admin")

if __name__ == '__main__':
    init_db()
