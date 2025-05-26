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
def scan_music_folders(user=None):
    """Scanne les dossiers de musique configurés"""
    app = current_app._get_current_object()
    print("\n🎵 Starting music library scan...")

    if not user:
        print("❌ No user provided for scan")
        return

    # Ne scanne que le dossier d'upload de l'utilisateur
    upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(user.id))
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        print(f"📂 Created upload directory: {upload_dir}")
        return

    try:
        print(f"\n📁 Scanning uploads directory: {upload_dir}")
        scan_folder(upload_dir, user_id=user.id)
        db.session.commit()
        print("✅ Upload directory scan completed!")
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error scanning music folders: {str(e)}")

def scan_folder(folder_path, user_id=None, show_details=False):
    """Scan un dossier pour les fichiers musicaux"""
    try:
        # Skip system directories
        if any(x in folder_path for x in ['.lproj', 'CodeSignature', 'Resources', '.app', '__pycache__']):
            return

        if user_id is None:
            user_id = current_user.id if current_user else 1

        # Find or create playlist
        playlist = Playlist.query.filter_by(
            folder_path=folder_path,
            user_id=user_id
        ).first()

        if not playlist:
            playlist = Playlist(
                name=os.path.basename(folder_path),
                folder_path=folder_path,
                is_auto=True,
                user_id=user_id
            )
            db.session.add(playlist)
            db.session.flush()

        # Get existing files and initialize tracking sets
        existing_files = set()
        current_files = set()

        # Build set of existing track file paths
        for pt in playlist.tracks:
            if pt and pt.track and pt.track.file_path:
                existing_files.add(pt.track.file_path)

        # Get list of music files in folder
        music_files = [f for f in os.listdir(folder_path) if allowed_file(f)]

        if music_files:
            print(f"✨ Scanning playlist: {os.path.basename(folder_path)} ({len(music_files)} tracks)")

            for file in music_files:
                try:
                    file_path = os.path.join(folder_path, file)
                    current_files.add(file_path)
                    if file_path not in existing_files:
                        track = process_audio_file(file_path, playlist)
                        if track and track.id:  # Only continue if track was created successfully
                            print(f"✅ Added track: {track.title}")
                        else:
                            print(f"⚠️ Failed to process: {file}")
                except Exception as e:
                    print(f"❌ Error processing {file}: {str(e)}")
                    continue

        if music_files or any(x in folder_path.lower() for x in {'music', 'musique', 'mp3', 'audio', 'downloads', 'téléchargements', 'uploads'}):
            subfolders = [d for d in os.listdir(folder_path)
                        if os.path.isdir(os.path.join(folder_path, d))
                        and not d.startswith('.')
                        and not d.startswith('_')]

            for subfolder in subfolders:
                try:
                    subfolder_path = os.path.join(folder_path, subfolder)
                    scan_folder(subfolder_path, user_id, show_details)
                except Exception:
                    continue

    except Exception as e:
        if show_details and not any(x in folder_path for x in ['.lproj', 'CodeSignature', 'Resources']):
            print(f"❌ Error scanning folder {folder_path}: {str(e)}")
        db.session.rollback()

def process_audio_file(file_path, playlist=None, user_id=None):
    """Traite un fichier audio et l'ajoute à la base de données"""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
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
                # Extract metadata without 'easy' parameter
                audio = mutagen.File(file_path)
                title = os.path.splitext(os.path.basename(file_path))[0]
                artist = 'Unknown Artist'

                # Try to get metadata if available
                if audio and hasattr(audio, 'tags'):
                    try:
                        if isinstance(audio.tags, dict):
                            # MP3 and similar formats
                            title = audio.tags.get('title', [title])[0]
                            artist = audio.tags.get('artist', [artist])[0]
                        else:
                            # Other formats
                            title = audio.tags.get('TITLE', [title])[0]
                            artist = audio.tags.get('ARTIST', [artist])[0]
                    except (KeyError, IndexError, AttributeError):
                        pass

                # Create new track
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
                print(f"✨ Created track: {title} - {artist}")

            except Exception as e:
                print(f"❌ Error extracting metadata from {file_path}: {str(e)}")
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
                    db.session.flush()
                    print(f"✨ Added to playlist: {track.title}")
            except Exception as e:
                print(f"❌ Error adding to playlist: {str(e)}")
                # Don't raise here, still return the track

        return track

    except Exception as e:
        print(f"❌ Error processing {file_path}: {str(e)}")
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
    """Lance le scan de la bibliothèque musicale"""
    print("\n🔄 Lancement du scan de la bibliothèque...")
    user_id = current_user.id

    def scan_with_user():
        with current_app.app_context():
            # Requery user to avoid DetachedInstanceError
            user = User.query.get(user_id)
            if user:
                # Pass user object to avoid current_user issues in thread
                scan_music_folders(user=user)

    threading.Thread(target=scan_with_user).start()
    return jsonify({'message': 'Scan démarré'})

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
