import pytest
import numpy as np
from dj_online_studio.audio_processor import AudioProcessor

def test_audio_processor_initialization(test_audio_file):
    """Test AudioProcessor initialization with test file."""
    processor = AudioProcessor(test_audio_file)
    assert processor.y is not None
    assert processor.sr == 44100

def test_get_waveform(test_audio_file):
    """Test waveform extraction."""
    processor = AudioProcessor(test_audio_file)
    waveform = processor.get_waveform()

    # Check that waveform is normalized
    assert -1.0 <= waveform.max() <= 1.0
    assert -1.0 <= waveform.min() <= 1.0

    # Check waveform shape
    assert len(waveform.shape) == 1  # 1D array
    assert waveform.shape[0] > 0

def test_get_frequency_data(test_audio_file):
    """Test frequency band analysis."""
    processor = AudioProcessor(test_audio_file)
    freq_data = processor.get_frequency_data()

    # Check required frequency bands
    assert all(band in freq_data for band in ['low', 'mid', 'high'])

    # Check data normalization
    for band in freq_data.values():
        assert -1.0 <= band.max() <= 1.0
        assert -1.0 <= band.min() <= 1.0

def test_get_beat_positions(test_audio_file):
    """Test beat detection."""
    processor = AudioProcessor(test_audio_file)
    beat_positions = processor.get_beat_positions()

    # Test file has 120 BPM = 2 beats per second
    # For 10 seconds, expect approximately 20 beats
    expected_beats = 20
    tolerance = 2  # Allow some variation in detection

    assert len(beat_positions) > 0
    assert abs(len(beat_positions) - expected_beats) <= tolerance

def test_get_bpm(test_audio_file):
    """Test BPM detection."""
    processor = AudioProcessor(test_audio_file)
    bpm = processor.get_bpm()

    # Test file is generated at 120 BPM
    expected_bpm = 120
    tolerance = 5  # Allow 5 BPM variation in detection

    assert abs(bpm - expected_bpm) <= tolerance

def test_analyze(test_audio_file):
    """Test complete audio analysis."""
    processor = AudioProcessor(test_audio_file)
    analysis = processor.analyze()

    # Check all required components are present
    assert 'waveform' in analysis
    assert 'frequency_data' in analysis
    assert 'beat_positions' in analysis
    assert 'bpm' in analysis
    assert 'duration' in analysis

    # Check duration is correct (test file is 10 seconds)
    assert abs(analysis['duration'] - 10.0) < 0.1

def test_invalid_audio_file():
    """Test handling of invalid audio file."""
    with pytest.raises(Exception):
        AudioProcessor('nonexistent.wav')

@pytest.mark.parametrize('test_file,expected_bpm', [
    ('test_120bpm.wav', 120),
    ('test_140bpm.wav', 140)
])
def test_different_bpms(test_files_dir, test_file, expected_bpm):
    """Test BPM detection with different tempos."""
    import os
    file_path = os.path.join(test_files_dir, test_file)
    processor = AudioProcessor(file_path)
    bpm = processor.get_bpm()

    tolerance = 5
    assert abs(bpm - expected_bpm) <= tolerance

def test_frequency_sweep(test_files_dir):
    """Test frequency analysis with sweep file."""
    import os
    sweep_file = os.path.join(test_files_dir, 'sweep.wav')
    processor = AudioProcessor(sweep_file)
    freq_data = processor.get_frequency_data()

    # In a frequency sweep, expect energy in all bands
    assert np.any(freq_data['low'] > 0)
    assert np.any(freq_data['mid'] > 0)
    assert np.any(freq_data['high'] > 0)
