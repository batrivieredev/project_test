from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, current_app, make_response
from datetime import timedelta
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from .models import db, User, Track, Playlist, PlaylistTrack
from functools import wraps
import os
from pathlib import Path
import mutagen
import librosa
import numpy as np
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3, HeaderNotFoundError
import threading
import queue

from pathlib import Path
import ffmpeg
import uuid

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)
api = Blueprint('api', __name__, url_prefix='/api')
admin = Blueprint('admin', __name__, url_prefix='/admin')

@api.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response

# Constantes et variables globales
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'aiff', 'ogg', 'm4a'}
processing_queue = queue.Queue()
is_processing = False

# Décorateurs personnalisés
def admin_required(f):
    """Vérifie que l'utilisateur est administrateur"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Accès non autorisé", "error")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def mixer_access_required(f):
    """Vérifie que l'utilisateur a accès au mixer"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.can_access_mixer:
            flash("Vous n'avez pas accès au mixer", "error")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def converter_access_required(f):
    """Vérifie que l'utilisateur a accès au convertisseur"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.can_access_converter:
            flash("Vous n'avez pas accès au convertisseur", "error")
            return redirect(url_for('main.choose_mode'))
        return f(*args, **kwargs)
    return decorated_function

def requires_app_context(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_app:
            from app import create_app
            app = create_app()
            with app.app_context():
                return f(*args, **kwargs)
        return f(*args, **kwargs)
    return decorated_function

# Fonctions utilitaires
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@requires_app_context
def scan_music_folders(user=None, parent_folder=None, current_depth=0, max_depth=5):
    """
    Scanne récursivement les dossiers de musique et crée une hiérarchie de playlists.

    Args:
        user: Utilisateur pour qui scanner les dossiers
        parent_folder: Dossier parent à scanner (None = dossier racine de l'utilisateur)
        current_depth: Profondeur actuelle de la récursion
        max_depth: Profondeur maximale de scan (évite les boucles infinies)

    Returns:
        bool: True si le scan s'est bien passé
        int: Nombre de morceaux traités
    """
    if not user:
        print("❌ Aucun utilisateur fourni pour le scan")
        return False, 0

    if current_depth > max_depth:
        print(f"⚠️ Profondeur maximale atteinte ({max_depth})")
        return True, 0

    app = current_app._get_current_object()
    indent = "  " * current_depth
    folder_path = parent_folder or os.path.join(app.config['UPLOAD_FOLDER'], str(user.id))
    folder_name = os.path.basename(folder_path)
    total_tracks = 0

    try:
        print(f"\n{indent}📁 Scan du dossier : {folder_name}")

        # Vérifier si le dossier doit être ignoré
        if any(x in folder_path for x in ['.lproj', 'CodeSignature', 'Resources', '.app', '__pycache__']):
            return True, 0

        # Créer le dossier s'il n'existe pas
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"{indent}📂 Création du dossier : {folder_name}")
            return True, 0

        # Scanner le dossier actuel
        success, processed, playlist = scan_folder(folder_path, user.id, None, current_depth)
        if success:
            total_tracks += processed
        else:
            print(f"{indent}❌ Échec du scan pour {folder_name}")
            return False, 0

        # Scanner récursivement les sous-dossiers
        subdirs = [d for d in os.listdir(folder_path)
                  if os.path.isdir(os.path.join(folder_path, d))
                  and not d.startswith('.')]

        for subdir in subdirs:
            subdir_path = os.path.join(folder_path, subdir)
            sub_success, sub_tracks = scan_music_folders(
                user=user,
                parent_folder=subdir_path,
                parent_playlist=playlist,
                current_depth=current_depth + 1,
                max_depth=max_depth
            )
            if sub_success:
                total_tracks += sub_tracks

        print(f"{indent}✅ Scan terminé pour {folder_name}")
        return True, total_tracks

    except Exception as e:
        print(f"{indent}❌ Erreur lors du scan de {folder_name}: {str(e)}")
        return False, 0

def get_music_folders(base_path):
    """Retourne la liste des dossiers de musique valides"""
    music_folders = []
    for root, dirs, files in os.walk(base_path):
        # Ignorer les dossiers système
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        # Vérifier si le dossier contient des fichiers audio
        has_music = any(allowed_file(f) for f in files)
        if has_music:
            music_folders.append(root)
    return music_folders

def process_folder_files(folder_path, playlist, user_id, indent=""):
    """
    Traite tous les fichiers audio d'un dossier.

    Args:
        folder_path (str): Chemin du dossier
        playlist (Playlist): Playlist à mettre à jour
        user_id (int): ID de l'utilisateur
        indent (str): Indentation pour les logs

    Returns:
        int: Nombre de morceaux traités
    """
    current_files = set()
    processed_tracks = 0
    existing_tracks = {pt.track.file_path: pt for pt in playlist.tracks if pt.track}

    # Scanner les fichiers audio
    for file in os.listdir(folder_path):
        if not allowed_file(file):
            continue

        file_path = os.path.join(folder_path, file)
        current_files.add(file_path)

        # Traiter seulement les nouveaux fichiers
        if file_path not in existing_tracks:
            try:
                track = process_audio_file(file_path, playlist, user_id)
                if track and track.id:
                    processed_tracks += 1
                    print(f"{indent}✅ Ajout du morceau : {track.title}")
                else:
                    print(f"{indent}⚠️ Échec du traitement : {file}")
            except Exception as e:
                print(f"{indent}❌ Erreur de traitement {file}: {str(e)}")

    # Supprimer les morceaux qui n'existent plus
    for old_path, pt in existing_tracks.items():
        if old_path not in current_files:
            print(f"{indent}🗑️ Suppression du morceau manquant : {pt.track.title}")
            db.session.delete(pt)
            db.session.delete(pt.track)

    return processed_tracks


def scan_folder(folder_path, user_id, parent_playlist=None, current_depth=0):
    """
    Scanne un dossier et crée une hiérarchie de playlists.

    Args:
        folder_path (str): Chemin du dossier à scanner
        user_id (int): ID de l'utilisateur
        parent_playlist (Playlist): Playlist parente
        current_depth (int): Profondeur actuelle

    Returns:
        tuple: (success, total_tracks, playlist)
            - success: True si le scan s'est bien passé
            - total_tracks: Nombre de morceaux traités
            - playlist: Playlist créée ou mise à jour
    """
    indent = "  " * current_depth
    folder_name = os.path.basename(folder_path)
    total_tracks = 0

    try:
        # Vérifier si le dossier doit être ignoré
        if any(x in folder_path for x in ['.lproj', 'CodeSignature', 'Resources', '.app', '__pycache__']):
            return True, 0, None

        # Créer le dossier si nécessaire
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"{indent}📂 Création du dossier : {folder_name}")
            return True, 0, None

        print(f"{indent}📁 Scan du dossier : {folder_name}")

        # Chercher ou créer la playlist
        playlist = Playlist.query.filter_by(
            folder_path=folder_path,
            user_id=user_id,
            is_auto=True,
            parent_id=parent_playlist.id if parent_playlist else None
        ).first()

        if not playlist:
            playlist = Playlist(
                name=folder_name,
                folder_path=folder_path,
                is_auto=True,
                user_id=user_id,
                parent_id=parent_playlist.id if parent_playlist else None
            )
            db.session.add(playlist)
            db.session.flush()
            print(f"{indent}✨ Nouvelle playlist créée : {folder_name}")
        else:
            print(f"{indent}📝 Mise à jour de la playlist : {folder_name}")

        # Traiter les fichiers du dossier
        processed = process_folder_files(folder_path, playlist, user_id, indent)
        total_tracks += processed
        print(f"{indent}✅ {processed} morceaux traités dans {folder_name}")

        # Scanner les sous-dossiers
        subdirs = [d for d in os.listdir(folder_path)
                  if os.path.isdir(os.path.join(folder_path, d))
                  and not d.startswith('.')]

        for subdir in subdirs:
            subdir_path = os.path.join(folder_path, subdir)
            success, sub_tracks, sub_playlist = scan_folder(
                subdir_path,
                user_id,
                playlist,
                current_depth + 1
            )
            if success:
                total_tracks += sub_tracks

        return True, total_tracks, playlist

    except Exception as e:
        print(f"{indent}❌ Erreur lors du scan de {folder_name}: {str(e)}")
        db.session.rollback()
        return False, 0, None


def process_audio_file(file_path, playlist=None, user_id=None):
    """Traite un fichier audio et l'ajoute à la base de données"""
    if not os.path.exists(file_path):
        print(f"❌ Fichier non trouvé : {file_path}")
        return None

    try:
        # Get or initialize user_id
        actual_user_id = user_id if user_id else (current_user.id if current_user else 1)

        # Check if track already exists
        track = Track.query.filter_by(
            file_path=file_path,
            user_id=actual_user_id
        ).first()

        if not track:
            try:
                # Extraire les métadonnées du fichier
                audio = mutagen.File(file_path)
                title = os.path.splitext(os.path.basename(file_path))[0]
                artist = 'Artiste inconnu'

                # Récupérer les métadonnées si disponibles
                if audio and hasattr(audio, 'tags'):
                    try:
                        if isinstance(audio.tags, dict):
                            # Formats MP3 et similaires
                            title = audio.tags.get('title', [title])[0]
                            artist = audio.tags.get('artist', [artist])[0]
                        else:
                            # Autres formats
                            title = audio.tags.get('TITLE', [title])[0]
                            artist = audio.tags.get('ARTIST', [artist])[0]
                    except (KeyError, IndexError, AttributeError):
                        pass

                # Créer le nouveau morceau
                track = Track(
                    title=title,
                    artist=artist,
                    bpm=None,
                    key=audio.get('key', [None])[0] if audio else None,
                    file_path=file_path,
                    file_format=file_path.rsplit('.', 1)[1].lower(),
                    file_size=os.path.getsize(file_path),
                    user_id=actual_user_id
                )
                db.session.add(track)
                db.session.flush()
                print(f"✨ Création du morceau : {title} - {artist}")

            except Exception as e:
                print(f"❌ Erreur lors de l'extraction des métadonnées de {file_path}: {str(e)}")
                return None

        # Add to playlist if specified and not already in it
        if playlist and track and track.id:
            try:
                # Verify track not already in playlist
                if not any(pt.track_id == track.id for pt in playlist.tracks):
                    playlist_track = PlaylistTrack(
                        playlist_id=playlist.id,
                        track_id=track.id,
                        position=len(playlist.tracks)
                    )
                    db.session.add(playlist_track)
                    # Supprime les morceaux qui n'existent plus
                    for old_path, playlist_track in existing_tracks.items():
                        if old_path not in current_files:
                            print(f"🗑️ Suppression du morceau manquant : {playlist_track.track.title}")
                            db.session.delete(playlist_track.track)

                    # Sauvegarde les modifications
                    db.session.flush()
                    print(f"✨ Ajouté à la playlist : {track.title}")
            except Exception as e:
                print(f"❌ Erreur lors de l'ajout à la playlist : {str(e)}")
                # Don't raise here, still return the track

        return track

    except Exception as e:
        print(f"❌ Erreur lors du traitement de {file_path}: {str(e)}")
        return None

def detect_bpm(file_path):
    """Détecte le BPM d'un fichier audio"""
    try:
        filename = os.path.basename(file_path)
        print(f"\n🎵 Analyzing BPM for: {filename}")

        # First try ID3 tags for MP3
        if file_path.lower().endswith('.mp3'):
            try:
                print("📑 Checking ID3 tags...")
                audio = MP3(file_path)
                if audio.tags and 'TBPM' in audio.tags:
                    try:
                        bpm = float(audio.tags['TBPM'].text[0])
                        if 40 <= bpm <= 220:  # Validate BPM is in reasonable range
                            print(f"✨ Found BPM in tags: {bpm}")
                            return bpm
                    except (ValueError, IndexError, AttributeError):
                        print("⚠️ Invalid BPM value in tags")
            except Exception as e:
                print(f"⚠️ Error reading ID3 tags: {str(e)}")

        # If no valid BPM from tags, try audio analysis
        try:
            print("🔍 Analyzing audio sample (30s)...")
            y, sr = librosa.load(file_path, duration=30, sr=22050)
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
            bpm = round(tempo, 2)

            if 40 <= bpm <= 220:  # Validate detected BPM
                print(f"✅ BPM detected: {bpm}")
                return bpm
            else:
                print("⚠️ Detected BPM outside valid range")
                return None

        except Exception as e:
            print(f"❌ Error in audio analysis: {str(e)}")
            return None

    except Exception as e:
        print(f"❌ Error analyzing {filename}: {str(e)}")
        return None

# Routes principales
@main.route('/')
def index():
    """Page d'accueil - Redirige vers la page de choix ou la page de connexion"""
    if current_user.is_authenticated:
        return redirect(url_for('main.choose_mode'))
    return redirect(url_for('auth.login'))

@main.route('/choose')
@login_required
def choose_mode():
    """Page de choix entre administration et mixer"""
    return render_template('choose_mode.html')

@main.route('/loading')
@login_required
@mixer_access_required
def loading():
    """Page de chargement avant le mixer"""
    return render_template('loading.html')

@main.route('/mixer')
@login_required
@mixer_access_required
def mixer():
    """Page du mixer DJ - Nécessite l'autorisation d'accès"""
    return render_template('mixer.html')

@main.route('/converter')
@login_required
@converter_access_required
def converter():
    """Page du convertisseur audio"""
    return render_template('converter.html')

@api.route('/convert', methods=['POST', 'OPTIONS'])
@login_required
@converter_access_required
def convert_audio():
    """Convertit un fichier audio au format demandé"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    youtube_url = request.form.get('youtube_url')
    output_format = request.form.get('format', 'mp3')
    quality = request.form.get('quality', '320')

    temp_dir = Path(current_app.config['UPLOAD_FOLDER']) / 'temp'
    temp_dir.mkdir(exist_ok=True)

    try:
        input_path = None
        output_path = None
        if youtube_url:
            try:
                # Configurer pytube avec un timeout plus long
                from pytube import YouTube
                import socket
                socket.setdefaulttimeout(15)  # 15 secondes de timeout

                # Télécharger depuis YouTube avec retry
                attempts = 3
                for attempt in range(attempts):
                    try:
                        yt = YouTube(youtube_url)
                        stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
                        if not stream:
                            response = make_response('Impossible de trouver l\'audio dans la vidéo YouTube', 400)
                            response.headers['Access-Control-Allow-Origin'] = '*'
                            return response

                        input_path = temp_dir / f"{uuid.uuid4()}.mp4"
                        stream.download(filename=str(input_path))
                        filename = yt.title
                        break
                    except Exception as e:
                        if attempt == attempts - 1:  # Dernier essai
                            raise
                        continue
            except Exception as e:
                error_msg = str(e)
                if "CERTIFICATE_VERIFY_FAILED" in error_msg:
                    error_msg = "Erreur de certificat SSL lors de la connexion à YouTube"
                elif "HTTP Error 400" in error_msg:
                    error_msg = "URL YouTube invalide ou vidéo non disponible"
                response = make_response(f'Erreur YouTube: {error_msg}', 400)
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response
        else:
            # Gérer l'upload de fichier
            if 'file' not in request.files:
                response = make_response('Aucun fichier sélectionné', 400)
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response

            file = request.files['file']
            if not file or file.filename == '':
                response = make_response('Nom de fichier invalide', 400)
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response

            input_path = temp_dir / f"{uuid.uuid4()}{Path(file.filename).suffix}"
            file.save(input_path)
            filename = file.filename

        # Configurer la sortie selon le format demandé
        output_path = temp_dir / f"{uuid.uuid4()}.{output_format}"

        # Configurer ffmpeg selon le format
        ffmpeg_stream = ffmpeg.input(str(input_path))
        if output_format == 'mp3':
            ffmpeg_stream = ffmpeg.output(ffmpeg_stream, str(output_path),
                                      acodec='libmp3lame',
                                      ab=f'{quality}k',
                                      loglevel='error')
        elif output_format == 'wav':
            ffmpeg_stream = ffmpeg.output(ffmpeg_stream, str(output_path),
                                      acodec='pcm_s16le',
                                      loglevel='error')

        # Convertir le fichier
        ffmpeg.run(ffmpeg_stream, capture_stdout=True, capture_stderr=True)

        # Envoyer le fichier converti
        response = make_response(send_file(
            output_path,
            mimetype=f'audio/{output_format}',
            as_attachment=True,
            download_name=f"{Path(filename).stem}.{output_format}"
        ))
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'

        # Nettoyer les fichiers temporaires
        input_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)

        return response

    except Exception as e:
        response = make_response(f'Erreur de conversion: {str(e)}', 500)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    finally:
        # Nettoyer les fichiers temporaires
        if input_path and input_path.exists():
            input_path.unlink(missing_ok=True)
        if output_path and output_path.exists():
            output_path.unlink(missing_ok=True)

# Routes d'authentification
@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Gestion de la connexion"""
    if current_user.is_authenticated:
        return redirect(url_for('main.choose_mode'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Veuillez remplir tous les champs', 'error')
            return render_template('login.html')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash('Ce compte a été désactivé', 'error')
                return render_template('login.html')

            login_user(user)
            user.last_login = db.func.now()
            db.session.commit()
            return redirect(url_for('main.choose_mode'))

        flash('Nom d\'utilisateur ou mot de passe invalide', 'error')
    return render_template('login.html')

@auth.route('/register', methods=['POST'])
def register():
    """Inscription d'un nouvel utilisateur"""
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    # Validation des données
    if not all([username, email, password, confirm_password]):
        flash('Veuillez remplir tous les champs', 'error')
        return redirect(url_for('auth.login'))

    if password != confirm_password:
        flash('Les mots de passe ne correspondent pas', 'error')
        return redirect(url_for('auth.login'))

    if User.query.filter_by(username=username).first():
        flash('Ce nom d\'utilisateur est déjà pris', 'error')
        return redirect(url_for('auth.login'))

    if User.query.filter_by(email=email).first():
        flash('Cette adresse email est déjà utilisée', 'error')
        return redirect(url_for('auth.login'))

    # Création du nouvel utilisateur
    user = User(username=username, email=email)
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
        flash('Compte créé avec succès! Un administrateur doit approuver votre accès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erreur lors de la création du compte', 'error')

    return redirect(url_for('auth.login'))

@auth.route('/logout')
@login_required
def logout():
    """Déconnexion de l'utilisateur"""
    logout_user()
    return redirect(url_for('auth.login'))

# Routes d'administration
@admin.route('/')
@login_required
@admin_required
def dashboard():
    """Dashboard d'administration"""
    users = User.query.all()
    return render_template('admin/dashboard.html', users=users, timedelta=timedelta)

@admin.route('/users')
@login_required
@admin_required
def users_list():
    """Liste des utilisateurs"""
    users = User.query.order_by(User.username).all()
    return render_template('admin/users.html', users=users)

@admin.route('/users/create', methods=['POST'])
@login_required
@admin_required
def create_user():
    """Création d'un nouvel utilisateur"""
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    is_active = bool(request.form.get('is_active'))
    can_access_mixer = bool(request.form.get('can_access_mixer'))
    can_access_converter = bool(request.form.get('can_access_converter'))
    is_admin = bool(request.form.get('is_admin'))

    if User.query.filter_by(username=username).first():
        flash('Ce nom d\'utilisateur est déjà pris', 'error')
        return redirect(url_for('admin.users_list'))

    if User.query.filter_by(email=email).first():
        flash('Cette adresse email est déjà utilisée', 'error')
        return redirect(url_for('admin.users_list'))

    user = User(
        username=username,
        email=email,
        is_active=is_active,
        can_access_mixer=can_access_mixer,
        can_access_converter=can_access_converter,
        is_admin=is_admin
    )
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
        flash('Utilisateur créé avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erreur lors de la création de l\'utilisateur', 'error')

    return redirect(url_for('admin.users_list'))

@admin.route('/users/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def update_user(user_id):
    """Mise à jour d'un utilisateur"""
    user = User.query.get_or_404(user_id)

    if user == current_user:
        flash('Vous ne pouvez pas modifier votre propre compte', 'error')
        return redirect(url_for('admin.users_list'))

    try:
        # Mise à jour des droits
        user.is_active = bool(request.form.get('is_active'))
        user.can_access_mixer = bool(request.form.get('can_access_mixer'))
        user.can_access_converter = bool(request.form.get('can_access_converter'))
        user.is_admin = bool(request.form.get('is_admin'))

        # Mise à jour de l'email
        new_email = request.form.get('email')
        if new_email and new_email != user.email:
            if User.query.filter_by(email=new_email).first():
                flash('Cette adresse email est déjà utilisée', 'error')
                return redirect(url_for('admin.users_list'))
            user.email = new_email

        # Mise à jour du mot de passe si fourni
        new_password = request.form.get('password')
        if new_password:
            user.set_password(new_password)

        db.session.commit()
        flash('Utilisateur mis à jour avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erreur lors de la mise à jour de l\'utilisateur', 'error')

    return redirect(url_for('admin.users_list'))

@admin.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Suppression d'un utilisateur"""
    user = User.query.get_or_404(user_id)
    if user == current_user:
        flash('Vous ne pouvez pas supprimer votre propre compte', 'error')
        return redirect(url_for('admin.users_list'))

    try:
        db.session.delete(user)
        db.session.commit()
        flash('Utilisateur supprimé avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erreur lors de la suppression', 'error')

    return redirect(url_for('admin.users_list'))

# Routes API pour le mixer
@api.route('/playlists')
@login_required
@mixer_access_required
def get_playlists():
    """Retourne la liste des playlists de l'utilisateur"""
    playlists = Playlist.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'trackCount': len(p.tracks)
    } for p in playlists])

@api.route('/playlists/<int:playlist_id>/tracks')
@login_required
@mixer_access_required
def get_playlist_tracks(playlist_id):
    """Retourne les morceaux d'une playlist"""
    playlist = Playlist.query.get_or_404(playlist_id)
    if playlist.user_id != current_user.id:
        return jsonify({'error': 'Accès non autorisé'}), 403

    track_list = []
    for pt in playlist.tracks:
        if pt and pt.track:  # Only include valid tracks
            track_list.append({
                'id': pt.track.id,
                'title': pt.track.title,
                'artist': pt.track.artist,
                'bpm': pt.track.bpm,
                'key': pt.track.key,
                'duration': pt.track.duration,
                'file_path': pt.track.file_path
            })
    return jsonify(track_list)

@api.route('/tracks')
@login_required
@mixer_access_required
def get_tracks():
    """Retourne tous les morceaux de l'utilisateur"""
    try:
        tracks = Track.query.filter_by(user_id=current_user.id).all()
        return jsonify([{
            'id': t.id,
            'title': t.title,
            'artist': t.artist,
            'bpm': t.bpm,
            'key': t.key,
            'file_path': t.file_path
        } for t in tracks])
    except Exception as e:
        print(f"Error fetching tracks: {str(e)}")
        return jsonify([])  # Return empty list instead of error to avoid breaking UI

@api.route('/tracks/<int:track_id>')
@login_required
@mixer_access_required
def get_track(track_id):
    """Retourne les détails d'un morceau"""
    track = Track.query.get_or_404(track_id)
    if track.user_id != current_user.id:
        return jsonify({'error': 'Accès non autorisé'}), 403

    return jsonify({
        'id': track.id,
        'title': track.title,
        'artist': track.artist,
        'bpm': track.bpm,
        'key': track.key,
        'file_path': track.file_path,
        'filename': os.path.basename(track.file_path)
    })

@api.route('/tracks/<int:track_id>/file')
@login_required
@mixer_access_required
def get_track_file(track_id):
    """Retourne le fichier audio d'un morceau"""
    track = Track.query.get_or_404(track_id)
    if track.user_id != current_user.id:
        return jsonify({'error': 'Accès non autorisé'}), 403

    try:
        extension = os.path.splitext(track.file_path)[1].lower()
        mime_type = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
            '.m4a': 'audio/mp4'
        }.get(extension, 'audio/mpeg')

        return send_file(
            track.file_path,
            mimetype=mime_type,
            as_attachment=True,
            download_name=os.path.basename(track.file_path),
            conditional=True
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/playlists', methods=['POST'])
@login_required
@mixer_access_required
def create_playlist():
    """Crée une nouvelle playlist"""
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    is_smart = data.get('is_smart', False)
    smart_rules = data.get('smart_rules') if is_smart else None

    if not name:
        return jsonify({'error': 'Le nom est requis'}), 400

    playlist = Playlist(
        name=name,
        description=description,
        is_smart=is_smart,
        smart_rules=smart_rules,
        user_id=current_user.id
    )
    db.session.add(playlist)

    try:
        db.session.commit()
        return jsonify({
            'id': playlist.id,
            'name': playlist.name,
            'trackCount': 0
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api.route('/playlists/<int:playlist_id>/reorder', methods=['POST'])
@login_required
@mixer_access_required
def reorder_playlist(playlist_id):
    """Réorganise les morceaux d'une playlist"""
    playlist = Playlist.query.get_or_404(playlist_id)
    if playlist.user_id != current_user.id:
        return jsonify({'error': 'Accès non autorisé'}), 403

    data = request.get_json()
    track_ids = data.get('track_ids', [])

    try:
        playlist.reorder_tracks(track_ids)
        db.session.commit()
        return jsonify({'message': 'Playlist réorganisée avec succès'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api.route('/tracks/<int:track_id>/analyze-bpm', methods=['POST'])
@login_required
@mixer_access_required
def analyze_track_bpm(track_id):
    """Analyse le BPM d'un morceau"""
    track = Track.query.get_or_404(track_id)
    if track.user_id != current_user.id:
        return jsonify({'error': 'Accès non autorisé'}), 403

    try:
        bpm = detect_bpm(track.file_path)
        if bpm:
            track.bpm = bpm
            db.session.commit()
            return jsonify({'bpm': bpm})
        return jsonify({'error': 'Impossible de détecter le BPM'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api.route('/scan-music')
@login_required
@mixer_access_required
def scan_music():
    """Lance le scan de la bibliothèque musicale de l'utilisateur"""
    print("\n🔄 Lancement du scan de la bibliothèque...")
    user_id = current_user.id
    max_depth = request.args.get('max_depth', default=5, type=int)

    def scan_with_user():
        with current_app.app_context():
            user = User.query.get(user_id)  # Requery to avoid DetachedInstanceError
            if not user:
                print("❌ Utilisateur non trouvé")
                return

            try:
                # Scanner les dossiers de musique avec retour d'informations
                success, total_tracks = scan_music_folders(
                    user=user,
                    max_depth=max_depth
                )

                if success:
                    print(f"✅ Scan terminé ! {total_tracks} morceaux traités")
                else:
                    print("❌ Échec du scan de la bibliothèque")

            except Exception as e:
                print(f"❌ Erreur lors du scan : {str(e)}")

    # Démarrer le scan dans un thread séparé
    thread = threading.Thread(target=scan_with_user)
    thread.daemon = True  # Le thread s'arrêtera quand le programme principal s'arrête
    thread.start()

    return jsonify({
        'message': 'Scan démarré',
        'max_depth': max_depth
    })

@api.route('/tracks', methods=['POST'])
@login_required
@mixer_access_required
def upload_track():
    """Gère l'upload de nouveaux morceaux"""
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni'}), 400

    file = request.files['file']
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Type de fichier invalide'}), 400

    filename = secure_filename(file.filename)
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(current_user.id))

    # Crée le dossier de l'utilisateur s'il n'existe pas
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    filepath = os.path.join(upload_dir, filename)

    try:
        file.save(filepath)

        # Crée ou récupère la playlist "Uploads" de l'utilisateur
        playlist = Playlist.query.filter_by(
            name="Uploads",
            user_id=current_user.id,
            is_auto=True
        ).first()

        if not playlist:
            playlist = Playlist(
                name="Uploads",
                user_id=current_user.id,
                is_auto=True,
                folder_path=upload_dir
            )
            db.session.add(playlist)
            db.session.flush()

        # Traite le fichier
        track = process_audio_file(filepath, playlist, current_user.id)

        # Analyse le BPM si non déjà fait
        if not track.bpm:
            track.bpm = detect_bpm(filepath)

        db.session.commit()

        return jsonify({
            'id': track.id,
            'title': track.title,
            'artist': track.artist,
            'bpm': track.bpm,
            'key': track.key,
            'file_path': track.file_path
        })

    except Exception as e:
        db.session.rollback()
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': str(e)}), 500
