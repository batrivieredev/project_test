import pytest
import json
import numpy as np
from dj_online_studio.models import Track, AudioAnalysis
from dj_online_studio.extensions import db

def test_create_track(app):
    """Test track creation and default values."""
    with app.app_context():
        track = Track(filename='test.wav')
        db.session.add(track)
        db.session.commit()

        assert track.id is not None
        assert track.filename == 'test.wav'
        assert track.title is None
        assert track.artist is None
        assert track.duration is None
        assert track.bpm is None
        assert track.upload_date is not None

def test_track_file_path(app):
    """Test track file path property."""
    with app.app_context():
        track = Track(filename='test.wav')
        expected_path = f"{app.config['UPLOAD_FOLDER']}/test.wav"
        assert track.file_path == expected_path

def test_track_to_dict(app):
    """Test track serialization to dictionary."""
    with app.app_context():
        track = Track(
            filename='test.wav',
            title='Test Track',
            artist='Test Artist',
            duration=180.5,
            bpm=120.0
        )
        db.session.add(track)
        db.session.commit()

        data = track.to_dict()
        assert data['id'] == track.id
        assert data['filename'] == 'test.wav'
        assert data['title'] == 'Test Track'
        assert data['artist'] == 'Test Artist'
        assert data['duration'] == 180.5
        assert data['bpm'] == 120.0
        assert 'upload_date' in data

def test_create_audio_analysis(app, test_track):
    """Test audio analysis creation and relationship."""
    with app.app_context():
        analysis = AudioAnalysis(track_id=test_track.id)
        db.session.add(analysis)
        db.session.commit()

        assert analysis.id is not None
        assert analysis.track_id == test_track.id
        assert analysis.created_at is not None
        assert test_track.analysis is analysis

def test_audio_analysis_waveform_data(app, test_track):
    """Test waveform data serialization."""
    with app.app_context():
        analysis = AudioAnalysis(track_id=test_track.id)

        # Test numpy array serialization
        test_data = np.array([0.1, -0.2, 0.3, -0.4])
        analysis.set_waveform_data(test_data)

        # Verify data is stored as JSON string
        assert isinstance(analysis.waveform_data, str)

        # Verify data can be retrieved correctly
        retrieved_data = analysis.get_waveform_data()
        assert isinstance(retrieved_data, np.ndarray)
        assert np.array_equal(retrieved_data, test_data)

def test_audio_analysis_frequency_data(app, test_track):
    """Test frequency data serialization."""
    with app.app_context():
        analysis = AudioAnalysis(track_id=test_track.id)

        # Test frequency band data serialization
        test_data = {
            'low': np.array([0.1, 0.2]),
            'mid': np.array([0.3, 0.4]),
            'high': np.array([0.5, 0.6])
        }
        analysis.set_frequency_data(test_data)

        # Verify data is stored as JSON string
        assert isinstance(analysis.frequency_data, str)

        # Verify data can be retrieved correctly
        retrieved_data = analysis.get_frequency_data()
        for band in ['low', 'mid', 'high']:
            assert band in retrieved_data
            assert isinstance(retrieved_data[band], np.ndarray)
            assert np.array_equal(retrieved_data[band], test_data[band])

def test_audio_analysis_beat_positions(app, test_track):
    """Test beat positions serialization."""
    with app.app_context():
        analysis = AudioAnalysis(track_id=test_track.id)

        # Test beat positions serialization
        test_data = np.array([1.0, 1.5, 2.0, 2.5])
        analysis.set_beat_positions(test_data)

        # Verify data is stored as JSON string
        assert isinstance(analysis.beat_positions, str)

        # Verify data can be retrieved correctly
        retrieved_data = analysis.get_beat_positions()
        assert isinstance(retrieved_data, np.ndarray)
        assert np.array_equal(retrieved_data, test_data)

def test_audio_analysis_to_dict(app, test_track):
    """Test audio analysis serialization to dictionary."""
    with app.app_context():
        analysis = AudioAnalysis(track_id=test_track.id)

        # Set test data
        analysis.set_waveform_data(np.array([0.1, 0.2]))
        analysis.set_frequency_data({
            'low': np.array([0.1]),
            'mid': np.array([0.2]),
            'high': np.array([0.3])
        })
        analysis.set_beat_positions(np.array([1.0, 2.0]))

        db.session.add(analysis)
        db.session.commit()

        data = analysis.to_dict()
        assert data['id'] == analysis.id
        assert data['track_id'] == test_track.id
        assert isinstance(data['waveform_data'], list)
        assert isinstance(data['frequency_data'], dict)
        assert isinstance(data['beat_positions'], list)
        assert 'created_at' in data

def test_cascade_delete(app):
    """Test that deleting a track also deletes its analysis."""
    with app.app_context():
        # Create track and analysis
        track = Track(filename='test.wav')
        db.session.add(track)
        db.session.commit()

        analysis = AudioAnalysis(track_id=track.id)
        db.session.add(analysis)
        db.session.commit()

        analysis_id = analysis.id

        # Delete track
        db.session.delete(track)
        db.session.commit()

        # Verify analysis is also deleted
        assert AudioAnalysis.query.get(analysis_id) is None
