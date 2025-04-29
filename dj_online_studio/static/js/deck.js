import { AudioEngine } from './audioEngine.js';
import { WaveformVisualizer } from './waveform.js';

export class DJDeck {
    constructor(deckNumber) {
        this.deckNumber = deckNumber;
        this.playing = false;
        this.startTime = 0;
        this.pauseTime = 0;

        // Initialize components
        this.audioEngine = new AudioEngine();
        this.setupDOMElements();
        this.setupVisualizers();
        this.setupEventListeners();
    }

    setupDOMElements() {
        this.deck = document.getElementById(`deck${this.deckNumber}`);
        this.fileInput = document.getElementById(`audio${this.deckNumber}`);
        this.playButton = document.getElementById(`playBtn${this.deckNumber}`);
        this.volumeSlider = document.getElementById(`volume${this.deckNumber}`);
        this.speedSlider = document.getElementById(`speed${this.deckNumber}`);
        this.volumeLevel = document.getElementById(`volumeLevel${this.deckNumber}`);
        this.timeElapsed = this.deck.querySelector('.time-elapsed');
        this.timeTotal = this.deck.querySelector('.time-total');

        // Track info elements
        this.titleElement = this.deck.querySelector('.title');
        this.artistElement = this.deck.querySelector('.artist');
        this.bpmElement = this.deck.querySelector('.bpm');

        // Initial button state
        this.playButton.disabled = true;
    }

    setupVisualizers() {
        const canvas = document.getElementById(`waveform${this.deckNumber}`);
        this.waveform = new WaveformVisualizer(canvas);
    }

    setupEventListeners() {
        this.fileInput.addEventListener('change', (e) => this.loadTrack(e));
        this.playButton.addEventListener('click', () => this.togglePlay());
        this.volumeSlider.addEventListener('input', (e) => this.setVolume(e.target.value));
        this.speedSlider.addEventListener('input', (e) => this.setSpeed(e.target.value));

        // Handle window resize for waveform
        window.addEventListener('resize', () => this.waveform.resize());
    }

    async loadTrack(event) {
        const file = event.target.files[0];
        if (!file) return;

        try {
            // Reset state
            this.stop();
            this.waveform.clear();

            // Load track through audio engine
            const { buffer, metadata, analysis } = await this.audioEngine.loadTrack(file);

            // Update UI with metadata
            this.updateTrackInfo(metadata);
            this.formatTime(metadata.duration);

            // Update visualizations
            this.waveform.setAnalysisData(analysis);

            this.playButton.disabled = false;
        } catch (error) {
            console.error('Error loading track:', error);
            this.showError('Error loading track');
        }
    }

    updateTrackInfo(metadata) {
        this.titleElement.textContent = `Title: ${metadata.title || '---'}`;
        this.artistElement.textContent = `Artist: ${metadata.artist || '---'}`;
        this.bpmElement.textContent = `BPM: ${metadata.bpm ? Math.round(metadata.bpm) : '---'}`;
        this.timeTotal.textContent = this.formatTime(metadata.duration || 0);
    }

    formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    togglePlay() {
        if (this.playing) {
            this.stop();
        } else {
            this.play();
        }
    }

    play() {
        if (!this.audioEngine.buffer) return;

        this.startTime = this.audioEngine.play(this.pauseTime);
        this.playing = true;
        this.playButton.textContent = 'Stop';
        this.deck.classList.add('playing');
        this.waveform.startScrolling();
        this.startVolumeMonitoring();
        this.updatePlaybackTime();
    }

    stop() {
        this.audioEngine.stop();
        this.pauseTime = (this.audioEngine.audioContext.currentTime - this.startTime) % this.audioEngine.buffer.duration;
        this.playing = false;
        this.playButton.textContent = 'Play';
        this.deck.classList.remove('playing');
        this.waveform.stopScrolling();
        this.stopVolumeMonitoring();
    }

    setVolume(value) {
        const volume = value / 100;
        this.audioEngine.setVolume(volume);
    }

    setSpeed(value) {
        const speed = value / 100;
        this.audioEngine.setSpeed(speed);
    }

    updatePlaybackTime() {
        if (!this.playing) return;

        const currentTime = (this.audioEngine.audioContext.currentTime - this.startTime) % this.audioEngine.buffer.duration;
        this.timeElapsed.textContent = this.formatTime(currentTime);
        requestAnimationFrame(() => this.updatePlaybackTime());
    }

    startVolumeMonitoring() {
        const updateVolumeMeter = () => {
            if (!this.playing) return;

            const frequencyData = this.audioEngine.getFrequencyData();
            const average = frequencyData.reduce((acc, val) => acc + val, 0) / frequencyData.length;
            const height = (average / 255) * 100;
            this.volumeLevel.style.height = `${height}%`;

            requestAnimationFrame(updateVolumeMeter);
        };

        updateVolumeMeter();
    }

    stopVolumeMonitoring() {
        this.volumeLevel.style.height = '0%';
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error';
        errorDiv.textContent = message;
        this.deck.insertBefore(errorDiv, this.deck.firstChild);

        setTimeout(() => {
            errorDiv.remove();
        }, 3000);
    }

    destroy() {
        this.audioEngine.disconnectAll();
        this.waveform.clear();
    }
}
