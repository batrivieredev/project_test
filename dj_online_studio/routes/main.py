from flask import (
    Blueprint, render_template, request, jsonify,
    current_app, send_from_directory, abort
)
from werkzeug.utils import secure_filename
from ..models import Track, AudioAnalysis
from ..extensions import db
from ..audio_processor import AudioProcessor
import os

bp = Blueprint('main', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@bp.route('/')
def index():
    """Serve the main application page"""
    return render_template('index.html')

@bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and audio analysis"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    try:
        # Secure the filename and save the file
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Create track record
        track = Track(filename=filename)
        db.session.add(track)
        db.session.commit()

        # Process audio file
        processor = AudioProcessor(filepath)
        analysis_data = processor.analyze()

        # Update track with metadata
        track.title = os.path.splitext(filename)[0]
        track.duration = analysis_data['duration']
        track.bpm = analysis_data['bpm']

        # Create analysis record
        analysis = AudioAnalysis(track_id=track.id)
        analysis.set_waveform_data(analysis_data['waveform'])
        analysis.set_frequency_data(analysis_data['frequency_data'])
        analysis.set_beat_positions(analysis_data['beat_positions'])

        db.session.add(analysis)
        db.session.commit()

        return jsonify({
            'track': track.to_dict(),
            'analysis': analysis.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/tracks')
def list_tracks():
    """Get list of all tracks"""
    tracks = Track.query.all()
    return jsonify([track.to_dict() for track in tracks])

@bp.route('/tracks/<int:track_id>')
def get_track(track_id):
    """Get track details including analysis"""
    track = Track.query.get_or_404(track_id)
    return jsonify({
        'track': track.to_dict(),
        'analysis': track.analysis.to_dict() if track.analysis else None
    })

@bp.route('/audio/<path:filename>')
def serve_audio(filename):
    """Serve audio files"""
    try:
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        abort(404)

@bp.route('/tracks/<int:track_id>', methods=['DELETE'])
def delete_track(track_id):
    """Delete a track and its audio file"""
    track = Track.query.get_or_404(track_id)

    try:
        # Delete audio file
        os.remove(track.file_path)
    except OSError:
        pass  # File might not exist

    # Delete from database
    db.session.delete(track)
    db.session.commit()

    return '', 204

@bp.route('/tracks/<int:track_id>', methods=['PATCH'])
def update_track(track_id):
    """Update track metadata"""
    track = Track.query.get_or_404(track_id)
    data = request.get_json()

    if 'title' in data:
        track.title = data['title']
    if 'artist' in data:
        track.artist = data['artist']

    db.session.commit()
    return jsonify(track.to_dict())
