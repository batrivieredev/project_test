import os
import tempfile
import pytest
from dj_online_studio import create_app
from dj_online_studio.extensions import db

@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'UPLOAD_FOLDER': tempfile.mkdtemp()
    })

    with app.app_context():
        db.create_all()

    yield app

    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200

def test_upload_no_file(client):
    response = client.post('/upload')
    assert response.status_code == 400
    assert b'No file part' in response.data

def test_upload_empty_file(client):
    response = client.post('/upload', data={'file': (None, '')})
    assert response.status_code == 400
    assert b'No selected file' in response.data

def test_tracks_list_empty(client):
    response = client.get('/tracks')
    assert response.status_code == 200
    assert response.json == []

def test_track_not_found(client):
    response = client.get('/tracks/1')
    assert response.status_code == 404

def test_track_delete_not_found(client):
    response = client.delete('/tracks/1')
    assert response.status_code == 404

def test_upload_invalid_file(client):
    data = {
        'file': (tempfile.NamedTemporaryFile(suffix='.txt').name, 'test.txt')
    }
    response = client.post('/upload', data=data)
    assert response.status_code == 400
    assert b'File type not allowed' in response.data

def test_audio_file_not_found(client):
    response = client.get('/audio/nonexistent.mp3')
    assert response.status_code == 404
