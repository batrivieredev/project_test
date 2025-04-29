import librosa
import numpy as np
from flask import current_app
from pydub import AudioSegment
import tempfile
import os

class AudioProcessor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.y = None
        self.sr = None
        self._load_audio()

    def _load_audio(self):
        """Load and preprocess audio file"""
        # Convert mp3 to wav if necessary
        if self.file_path.endswith('.mp3'):
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                audio = AudioSegment.from_mp3(self.file_path)
                audio.export(temp_wav.name, format='wav')
                self.y, self.sr = librosa.load(temp_wav.name,
                                             sr=current_app.config['SAMPLE_RATE'])
                os.unlink(temp_wav.name)
        else:
            self.y, self.sr = librosa.load(self.file_path,
                                         sr=current_app.config['SAMPLE_RATE'])

    def analyze(self):
        """Perform complete audio analysis"""
        return {
            'waveform': self.get_waveform(),
            'frequency_data': self.get_frequency_data(),
            'beat_positions': self.get_beat_positions(),
            'bpm': self.get_bpm(),
            'duration': librosa.get_duration(y=self.y, sr=self.sr)
        }

    def get_waveform(self):
        """Extract waveform data"""
        # Resample to reduce data size while maintaining shape
        hop_length = current_app.config['HOP_LENGTH']
        waveform = librosa.resample(self.y, orig_sr=self.sr,
                                  target_sr=self.sr//hop_length)
        return librosa.util.normalize(waveform)

    def get_frequency_data(self):
        """Analyze frequency content"""
        # Compute STFT
        D = librosa.stft(self.y, n_fft=current_app.config['CHUNK_SIZE'])

        # Convert to magnitude spectrogram
        S = np.abs(D)

        # Split frequencies into bands
        freqs = librosa.fft_frequencies(sr=self.sr,
                                      n_fft=current_app.config['CHUNK_SIZE'])

        # Define frequency bands (in Hz)
        low_band = (freqs <= 250)
        mid_band = (freqs > 250) & (freqs <= 2000)
        high_band = (freqs > 2000)

        # Calculate average energy in each band
        low = np.mean(S[low_band], axis=0)
        mid = np.mean(S[mid_band], axis=0)
        high = np.mean(S[high_band], axis=0)

        # Normalize
        return {
            'low': librosa.util.normalize(low),
            'mid': librosa.util.normalize(mid),
            'high': librosa.util.normalize(high)
        }

    def get_beat_positions(self):
        """Detect beat positions"""
        tempo, beats = librosa.beat.beat_track(y=self.y, sr=self.sr)
        self.tempo = tempo  # Store for BPM calculation
        return librosa.frames_to_time(beats, sr=self.sr)

    def get_bpm(self):
        """Calculate BPM using multiple methods and return most confident result"""
        # Method 1: Basic beat tracking
        if not hasattr(self, 'tempo'):
            self.tempo, _ = librosa.beat.beat_track(y=self.y, sr=self.sr)

        # Method 2: Onset strength
        onset_env = librosa.onset.onset_strength(y=self.y, sr=self.sr)
        tempo_onset = librosa.beat.tempo(onset_envelope=onset_env, sr=self.sr)

        # Method 3: Tempogram
        tempogram = librosa.feature.tempogram(y=self.y, sr=self.sr)
        tempo_tempogram = librosa.beat.tempo(tempogram=tempogram)

        # Combine results (weighted average)
        tempos = np.array([self.tempo, tempo_onset, tempo_tempogram[0]])
        weights = np.array([0.4, 0.3, 0.3])  # Adjust weights based on confidence

        return float(np.average(tempos, weights=weights))
