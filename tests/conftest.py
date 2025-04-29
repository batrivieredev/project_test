import os
import tempfile
import shutil
import pytest
from dj_online_studio import create_app
from dj_online_studio.extensions import db
from dj_online_studio.models import Track, AudioAnalysis

@pytest.fixture(scope='session')
def test_audio_files():
    """Generate test audio files for testing."""
    from .generate_test_audio import generate_test_audio, generate_sweep
    generate_test_audio()
    generate_sweep()
    yield
    # Cleanup test files after tests
    test_files_dir = os.path.join(os.path.dirname(__file__), 'test_files')
    if os.path.exists(test_files_dir):
        shutil.rmtree(test_files_dir)

@pytest.fixture
def app(test_audio_files):
    """Create application for testing."""
    db_fd, db_path = tempfile.mkstemp()
    upload_dir = tempfile.mkdtemp()

    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'UPLOAD_FOLDER': upload_dir,
        'WTF_CSRF_ENABLED': False
    })

    with app.app_context():
        db.create_all()
        yield app

    # Cleanup after tests
    os.close(db_fd)
    os.unlink(db_path)
    shutil.rmtree(upload_dir)

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create test CLI runner."""
    return app.test_cli_runner()

@pytest.fixture
def test_track(app):
    """Create a test track in the database."""
    track = Track(
        filename='test_120bpm.wav',
        title='Test Track',
        artist='Test Artist',
        duration=10.0,
        bpm=120.0
    )
    db.session.add(track)
    db.session.commit()
    return track

@pytest.fixture
def test_track_with_analysis(test_track):
    """Create a test track with analysis data."""
    analysis = AudioAnalysis(
        track_id=test_track.id,
        waveform_data='[]',
        frequency_data='{"low":[],"mid":[],"high":[]}',
        beat_positions='[]'
    )
    db.session.add(analysis)
    db.session.commit()
    return test_track

@pytest.fixture
def test_audio_file():
    """Get path to a test audio file."""
    return os.path.join(os.path.dirname(__file__), 'test_files', 'test_120bpm.wav')

@pytest.fixture
def mock_upload_file(test_audio_file):
    """Create a mock file upload."""
    class MockUpload:
        def __init__(self, filename):
            self.filename = filename
            self.audio_file = open(test_audio_file, 'rb')

        def save(self, path):
            with open(path, 'wb') as f:
                f.write(self.audio_file.read())
            self.audio_file.seek(0)

    yield MockUpload('test_track.wav')
