import os
import io
import json
from dj_online_studio.models import Track, AudioAnalysis

def test_index_route(client):
    """Test the main page route."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'DJ Online Studio' in response.data

def test_upload_no_file(client):
    """Test upload endpoint with no file."""
    response = client.post('/upload')
    assert response.status_code == 400
    assert b'No file part' in response.data

def test_upload_empty_filename(client):
    """Test upload endpoint with empty filename."""
    response = client.post('/upload', data={
        'file': (io.BytesIO(b''), '')
    })
    assert response.status_code == 400
    assert b'No selected file' in response.data

def test_upload_invalid_extension(client):
    """Test upload endpoint with invalid file type."""
    response = client.post('/upload', data={
        'file': (io.BytesIO(b'test data'), 'test.txt')
    })
    assert response.status_code == 400
    assert b'File type not allowed' in response.data

def test_upload_success(client, test_audio_file):
    """Test successful file upload and processing."""
    with open(test_audio_file, 'rb') as f:
        data = {
            'file': (f, 'test_120bpm.wav')
        }
        response = client.post('/upload', data=data)

    assert response.status_code == 200
    json_data = json.loads(response.data)

    assert 'track' in json_data
    assert 'analysis' in json_data
    assert json_data['track']['bpm'] is not None
    assert json_data['analysis']['waveform_data'] is not None

def test_get_tracks_empty(client):
    """Test get tracks endpoint with empty database."""
    response = client.get('/tracks')
    assert response.status_code == 200
    assert json.loads(response.data) == []

def test_get_tracks(client, test_track_with_analysis):
    """Test get tracks endpoint with existing track."""
    response = client.get('/tracks')
    assert response.status_code == 200

    tracks = json.loads(response.data)
    assert len(tracks) == 1
    assert tracks[0]['id'] == test_track_with_analysis.id
    assert tracks[0]['title'] == test_track_with_analysis.title

def test_get_track_not_found(client):
    """Test getting a non-existent track."""
    response = client.get('/tracks/999')
    assert response.status_code == 404

def test_get_track(client, test_track_with_analysis):
    """Test getting a specific track with analysis."""
    response = client.get(f'/tracks/{test_track_with_analysis.id}')
    assert response.status_code == 200

    data = json.loads(response.data)
    assert 'track' in data
    assert 'analysis' in data
    assert data['track']['id'] == test_track_with_analysis.id

def test_delete_track_not_found(client):
    """Test deleting a non-existent track."""
    response = client.delete('/tracks/999')
    assert response.status_code == 404

def test_delete_track(client, test_track_with_analysis, app):
    """Test deleting a track."""
    track_id = test_track_with_analysis.id

    response = client.delete(f'/tracks/{track_id}')
    assert response.status_code == 204

    # Verify track is deleted from database
    with app.app_context():
        assert Track.query.get(track_id) is None

def test_update_track_not_found(client):
    """Test updating a non-existent track."""
    response = client.patch('/tracks/999', json={
        'title': 'New Title'
    })
    assert response.status_code == 404

def test_update_track(client, test_track):
    """Test updating track metadata."""
    new_data = {
        'title': 'Updated Title',
        'artist': 'Updated Artist'
    }

    response = client.patch(f'/tracks/{test_track.id}',
                          json=new_data)
    assert response.status_code == 200

    data = json.loads(response.data)
    assert data['title'] == new_data['title']
    assert data['artist'] == new_data['artist']

def test_serve_audio_not_found(client):
    """Test serving non-existent audio file."""
    response = client.get('/audio/nonexistent.wav')
    assert response.status_code == 404

def test_serve_audio(client, app, test_track):
    """Test serving audio file."""
    # Create test file in uploads directory
    test_content = b'test audio data'
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], test_track.filename)

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'wb') as f:
        f.write(test_content)

    response = client.get(f'/audio/{test_track.filename}')
    assert response.status_code == 200
    assert response.data == test_content
