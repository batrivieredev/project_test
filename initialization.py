"""
Script d'initialisation rapide du système:
- Crée les tables de la base de données
- Crée l'utilisateur admin par défaut
- Scanne un dossier de musique personnalisé
"""
import os
from pathlib import Path
from mutagen.mp3 import MP3
import librosa
import numpy as np
import sys
import time
from datetime import datetime, timedelta

# Ajoute le dossier parent au PYTHONPATH pour pouvoir importer app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Track, Playlist, PlaylistTrack

def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█', print_end="\r"):
    """
    Affiche une barre de progression dans le terminal
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=print_end)
    if iteration == total:
        print()

def format_time(seconds):
    """
    Formate un temps en secondes en format lisible
    """
    return str(timedelta(seconds=int(seconds)))

def process_audio_file(file_path, playlist, user_id, current_file, total_files, start_time):
    """
    Traite un fichier audio MP3:
    - Extrait les métadonnées (titre, artiste, BPM)
    - Crée un objet Track dans la base de données
    """
    try:
        track = Track.query.filter_by(file_path=file_path, user_id=user_id).first()
        if not track:
            audio = MP3(file_path)
            title = os.path.splitext(os.path.basename(file_path))[0]
            artist = 'Unknown Artist'
            if audio.tags:
                try:
                    title = audio.tags.get('TIT2', [title])[0].text[0]
                    artist = audio.tags.get('TPE1', [artist])[0].text[0]
                except (KeyError, IndexError, AttributeError):
                    pass

            elapsed_time = time.time() - start_time
            files_per_second = current_file / elapsed_time if elapsed_time > 0 else 0
            remaining_files = total_files - current_file
            eta = remaining_files / files_per_second if files_per_second > 0 else 0

            print_progress_bar(
                current_file,
                total_files,
                prefix=f'Processing: {title[:30]}...',
                suffix=f'ETA: {format_time(eta)}',
                length=30
            )

            print("\n🎵 Analyzing BPM...")
            bpm = None
            try:
                y, sr = librosa.load(file_path, duration=30, sr=22050)
                onset_env = librosa.onset.onset_strength(y=y, sr=sr)
                tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
                bpm = float(tempo)
                if 40 <= bpm <= 220:
                    bpm = round(bpm, 2)
                else:
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
            db.session.commit()

            position = len(playlist.tracks)
            playlist_track = PlaylistTrack(
                playlist_id=playlist.id,
                track_id=track.id,
                position=position
            )
            db.session.add(playlist_track)
            db.session.commit()
        return track
    except Exception as e:
        print(f"\n❌ Error processing {file_path}: {str(e)}")
        db.session.rollback()
        return None

def count_mp3_files(directory):
    """
    Compte le nombre total de fichiers MP3 dans un répertoire et ses sous-répertoires
    """
    count = 0
    for root, _, files in os.walk(directory):
        count += sum(1 for f in files if f.lower().endswith('.mp3'))
    return count

def scan_music_folders(main_dir, user_id):
    """
    Scanne le dossier musique et ses sous-dossiers:
    - Crée une playlist pour chaque sous-dossier
    - Analyse les fichiers MP3 de chaque sous-dossier
    """
    print(f"\n📂 Processing main music directory: {main_dir}")

    try:
        # Liste tous les sous-dossiers directs
        subdirs = [d for d in os.listdir(main_dir)
                  if os.path.isdir(os.path.join(main_dir, d)) and not d.startswith('.')]

        if not subdirs:
            print("⚠️ No subdirectories found in music folder")
            return

        print(f"📁 Found {len(subdirs)} music folders to process")

        # Compte le nombre total de fichiers MP3
        total_files = sum(count_mp3_files(os.path.join(main_dir, subdir)) for subdir in subdirs)
        print(f"\n📊 Total MP3 files to process: {total_files}")

        current_file = 0
        start_time = time.time()

        # Traite chaque sous-dossier
        for subdir in subdirs:
            folder_path = os.path.join(main_dir, subdir)
            print(f"\n🎵 Processing folder: {subdir}")

            # Trouve tous les MP3 dans ce dossier
            music_files = []
            for root, _, files in os.walk(folder_path):
                for f in files:
                    if f.lower().endswith('.mp3'):
                        music_files.append(os.path.join(root, f))

            if music_files:
                print(f"📀 Found {len(music_files)} MP3 files")

                # Crée ou récupère la playlist pour ce dossier
                playlist = Playlist.query.filter_by(folder_path=folder_path, user_id=user_id).first()
                if not playlist:
                    print(f"📋 Creating playlist: {subdir}")
                    playlist = Playlist(
                        name=subdir,
                        folder_path=folder_path,
                        is_auto=True,
                        user_id=user_id
                    )
                    db.session.add(playlist)
                    db.session.commit()

                # Traite les fichiers
                for file_path in music_files:
                    current_file += 1
                    process_audio_file(file_path, playlist, user_id, current_file, total_files, start_time)

                print(f"\n✅ Finished processing {subdir}")
            else:
                print(f"⚠️ No MP3 files in {subdir}")

    except Exception as e:
        print(f"❌ Error scanning music folders: {str(e)}")
        db.session.rollback()

def initialize_system():
    """
    Initialise le système rapidement:
    - Crée/réinitialise la base de données
    - Crée l'utilisateur admin
    - Scanne un dossier de musique spécifique
    """
    start_time = time.time()
    total_steps = 4
    current_step = 0

    # S'assure que le dossier app existe
    app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app')
    if not os.path.exists(app_dir):
        os.makedirs(app_dir)

    # Crée l'application avec le bon chemin de base de données
    current_step += 1
    print_progress_bar(current_step, total_steps, prefix='Initialization Progress:', suffix='Creating App')

    app = create_app()
    db_path = os.path.join(app_dir, 'app.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

    with app.app_context():
        # Initialize database
        current_step += 1
        print_progress_bar(current_step, total_steps, prefix='Initialization Progress:', suffix='Creating Database')

        try:
            db.session.execute('SELECT 1 FROM playlists')
            print("\n✓ Database tables exist, clearing data...")
        except Exception:
            print("\n⚠️ Database tables not found, creating schema...")
        db.drop_all()
        db.create_all()
        db.session.commit()

        # Create admin user
        current_step += 1
        print_progress_bar(current_step, total_steps, prefix='Initialization Progress:', suffix='Creating Admin')

        print("\n👤 Creating admin user...")
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
        print("✅ Admin user created")

        # Scan music folders
        current_step += 1
        print_progress_bar(current_step, total_steps, prefix='Initialization Progress:', suffix='Scanning Music')

        print("\n🔍 Scanning music folders...")
        music_dir = "/Users/batriviere/Music"  # <-- adapte ce chemin à ton environnement

        if os.path.exists(music_dir) and os.path.isdir(music_dir):
            print(f"✓ Starting scan of: {music_dir}")
            scan_music_folders(music_dir, admin.id)
        else:
            print(f"⚠️ Music directory not found: {music_dir}")

        total_time = time.time() - start_time
        print(f"\n✅ System initialization complete! ({format_time(total_time)})")
        print("🔑 Login with admin/admin")

if __name__ == '__main__':
    initialize_system()
