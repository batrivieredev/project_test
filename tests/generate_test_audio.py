import numpy as np
from scipy.io import wavfile
import os

def generate_sine_wave(frequency, duration, sample_rate=44100):
    """Generate a sine wave with the given frequency and duration."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    return np.sin(2 * np.pi * frequency * t)

def generate_test_audio():
    """Generate test audio files with known BPM values."""
    test_files_dir = os.path.join(os.path.dirname(__file__), 'test_files')
    os.makedirs(test_files_dir, exist_ok=True)

    # Test file parameters
    sample_rate = 44100
    durations = [10, 15]  # in seconds
    bpms = [120, 140]  # beats per minute

    for bpm, duration in zip(bpms, durations):
        # Convert BPM to frequency (beats per second)
        frequency = bpm / 60

        # Generate click track
        audio = np.zeros(int(sample_rate * duration))
        beat_samples = int(sample_rate / frequency)

        # Add clicks at beat positions
        for i in range(0, len(audio), beat_samples):
            # Generate short click sound
            click = generate_sine_wave(1000, 0.01, sample_rate)
            if i + len(click) <= len(audio):
                audio[i:i + len(click)] = click

        # Add some background sine waves for testing frequency analysis
        # Bass frequency
        bass = generate_sine_wave(100, duration, sample_rate) * 0.3
        # Mid frequency
        mid = generate_sine_wave(1000, duration, sample_rate) * 0.2
        # High frequency
        high = generate_sine_wave(5000, duration, sample_rate) * 0.1

        # Combine all sounds
        audio += bass + mid + high

        # Normalize
        audio = np.int16(audio * 32767)

        # Save file
        filename = os.path.join(test_files_dir, f'test_{bpm}bpm.wav')
        wavfile.write(filename, sample_rate, audio)
        print(f"Generated test audio file: {filename}")

def generate_sweep():
    """Generate a frequency sweep test file."""
    test_files_dir = os.path.join(os.path.dirname(__file__), 'test_files')
    os.makedirs(test_files_dir, exist_ok=True)

    sample_rate = 44100
    duration = 10
    t = np.linspace(0, duration, int(sample_rate * duration), False)

    # Generate logarithmic frequency sweep from 20Hz to 20kHz
    f0 = 20  # Start frequency
    f1 = 20000  # End frequency
    sweep = np.sin(2 * np.pi * f0 * t * (f1/f0)**(t/duration))

    # Normalize and convert to 16-bit integer
    sweep = np.int16(sweep * 32767)

    # Save file
    filename = os.path.join(test_files_dir, 'sweep.wav')
    wavfile.write(filename, sample_rate, sweep)
    print(f"Generated frequency sweep test file: {filename}")

if __name__ == '__main__':
    generate_test_audio()
    generate_sweep()
    print("Test audio files generated successfully!")
