class AudioEngine {
    constructor() {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.gainNode = this.audioContext.createGain();
        this.analyser = this.audioContext.createAnalyser();
        this.source = null;
        this.buffer = null;
    }

    async loadTrack(file) {
        // First upload the file to the server
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Upload failed');
            }

            const data = await response.json();

            // Now load the audio from the server
            const audioResponse = await fetch(`/audio/${data.track.filename}`);
            const arrayBuffer = await audioResponse.arrayBuffer();
            this.buffer = await this.audioContext.decodeAudioData(arrayBuffer);

            return {
                buffer: this.buffer,
                metadata: data.track,
                analysis: data.analysis
            };
        } catch (error) {
            console.error('Error loading track:', error);
            throw error;
        }
    }

    createSource() {
        this.source = this.audioContext.createBufferSource();
        this.source.buffer = this.buffer;
        this.source.connect(this.gainNode);
        this.gainNode.connect(this.analyser);
        this.analyser.connect(this.audioContext.destination);
        this.source.loop = true;
    }

    play(startTime = 0) {
        if (!this.buffer) return;

        this.createSource();
        this.source.start(0, startTime);
        return this.audioContext.currentTime;
    }

    stop() {
        if (this.source) {
            this.source.stop();
            this.source.disconnect();
        }
    }

    setVolume(value) {
        this.gainNode.gain.value = value;
    }

    setSpeed(value) {
        if (this.source) {
            this.source.playbackRate.value = value;
        }
    }

    getFrequencyData() {
        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        this.analyser.getByteFrequencyData(dataArray);
        return dataArray;
    }

    disconnectAll() {
        if (this.source) {
            this.source.disconnect();
        }
        this.gainNode.disconnect();
        this.analyser.disconnect();
    }
}

export { AudioEngine };
