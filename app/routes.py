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
def scan_music_folders(user=None, parent_folder=None, parent_playlist=None, current_depth=0, max_depth=5):
    """
    Scanne récursivement les dossiers de musique et crée une hiérarchie de playlists.
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

# Routes principales
@main.route('/')
@main.route('/landing')
@main.route('/landingpage')
def index():
    """Page d'accueil - Redirige vers la landing page si non connecté"""
    if current_user.is_authenticated:
        return redirect(url_for('main.choose_mode'))
    return render_template('landing_page.html')

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

@auth.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['POST'])
def register():
    """Handle new user registration"""
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    # Basic validation
    if not username or not email or not password or not confirm_password:
        flash('Veuillez remplir tous les champs', 'error')
        return redirect(url_for('auth.login'))

    if password != confirm_password:
        flash('Les mots de passe ne correspondent pas', 'error')
        return redirect(url_for('auth.login'))

    # Check if username or email already exists
    if User.query.filter_by(username=username).first():
        flash('Ce nom d\'utilisateur est déjà pris', 'error')
        return redirect(url_for('auth.login'))

    if User.query.filter_by(email=email).first():
        flash('Cette adresse email est déjà utilisée', 'error')
        return redirect(url_for('auth.login'))

    # Create new user
    user = User(
        username=username,
        email=email,
        is_active=True,
        can_access_mixer=False,
        is_admin=False
    )
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
        flash('Compte créé avec succès. Vous pouvez maintenant vous connecter.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erreur lors de la création du compte', 'error')

    return redirect(url_for('auth.login'))

# Routes API
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

# Routes d'administration
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
        action = request.form.get('action')
        if action == 'toggle_mixer_access':
            user.can_access_mixer = not user.can_access_mixer
            flash('Accès au mixer modifié avec succès', 'success')
        else:
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

            flash('Utilisateur mis à jour avec succès', 'success')

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('Erreur lors de la mise à jour de l\'utilisateur', 'error')

    return redirect(url_for('admin.users_list'))

@admin.route('/')
@login_required
@admin_required
def dashboard():
    """Admin dashboard showing user statistics"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/dashboard.html', users=users, timedelta=timedelta)

@admin.route('/users')
@login_required
@admin_required
def users_list():
    """List all users for administration"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users, timedelta=timedelta)

@admin.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user account"""
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
        flash('Erreur lors de la suppression de l\'utilisateur', 'error')

    return redirect(url_for('admin.users_list'))
