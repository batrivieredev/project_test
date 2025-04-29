class WaveformVisualizer {
    constructor(canvasElement) {
        this.canvas = canvasElement;
        this.context = this.canvas.getContext('2d');
        this.position = 0;
        this.scrollSpeed = 1;
        this.waveformData = null;
        this.frequencyData = null;
        this.beatPositions = null;
        this.isPlaying = false;
        this.setupCanvas();
    }

    setupCanvas() {
        this.canvas.width = this.canvas.offsetWidth * 2;
        this.canvas.height = this.canvas.offsetHeight * 2;
        this.context.fillStyle = '#111';
        this.context.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }

    setAnalysisData(analysis) {
        this.waveformData = analysis.waveform_data;
        this.frequencyData = analysis.frequency_data;
        this.beatPositions = analysis.beat_positions;
        this.drawInitialView();
    }

    drawInitialView() {
        if (!this.waveformData) return;

        const width = this.canvas.width;
        const height = this.canvas.height;
        const center = height / 2;

        // Clear canvas
        this.context.fillStyle = '#111';
        this.context.fillRect(0, 0, width, height);

        // Draw frequency bands
        this.drawFrequencyBands(0, width);

        // Draw beat markers
        this.drawBeatMarkers();
    }

    drawFrequencyBands(startX, endX) {
        const height = this.canvas.height;
        const center = height / 2;

        for (let x = startX; x < endX; x++) {
            const dataIndex = (x + this.position) % this.frequencyData.low.length;

            // Draw low frequencies (red)
            this.context.fillStyle = `rgba(255, 0, 0, ${this.frequencyData.low[dataIndex]})`;
            const lowHeight = this.frequencyData.low[dataIndex] * height * 0.3;
            this.context.fillRect(x, center - lowHeight/2, 1, lowHeight);

            // Draw mid frequencies (green)
            this.context.fillStyle = `rgba(0, 255, 0, ${this.frequencyData.mid[dataIndex]})`;
            const midHeight = this.frequencyData.mid[dataIndex] * height * 0.3;
            this.context.fillRect(x, center - midHeight/2, 1, midHeight);

            // Draw high frequencies (blue)
            this.context.fillStyle = `rgba(0, 0, 255, ${this.frequencyData.high[dataIndex]})`;
            const highHeight = this.frequencyData.high[dataIndex] * height * 0.3;
            this.context.fillRect(x, center - highHeight/2, 1, highHeight);
        }
    }

    drawBeatMarkers() {
        if (!this.beatPositions) return;

        const height = this.canvas.height;
        this.context.strokeStyle = 'rgba(255, 255, 255, 0.5)';
        this.context.lineWidth = 1;

        for (const beatTime of this.beatPositions) {
            const x = (beatTime * this.scrollSpeed + this.position) % this.canvas.width;
            this.context.beginPath();
            this.context.moveTo(x, 0);
            this.context.lineTo(x, height);
            this.context.stroke();
        }
    }

    startScrolling() {
        this.isPlaying = true;
        this.animate();
    }

    stopScrolling() {
        this.isPlaying = false;
    }

    animate() {
        if (!this.isPlaying || !this.waveformData) return;

        // Update position
        this.position = (this.position + this.scrollSpeed) % this.waveformData.length;

        // Clear previous frame
        const width = this.canvas.width;
        this.context.fillStyle = '#111';
        this.context.fillRect(0, 0, this.scrollSpeed, this.canvas.height);

        // Draw new frame
        this.drawFrequencyBands(0, width);
        this.drawBeatMarkers();

        // Request next frame
        requestAnimationFrame(() => this.animate());
    }

    clear() {
        this.context.fillStyle = '#111';
        this.context.fillRect(0, 0, this.canvas.width, this.canvas.height);
        this.position = 0;
        this.waveformData = null;
        this.frequencyData = null;
        this.beatPositions = null;
    }

    resize() {
        this.canvas.width = this.canvas.offsetWidth * 2;
        this.canvas.height = this.canvas.offsetHeight * 2;
        if (this.waveformData) {
            this.drawInitialView();
        } else {
            this.clear();
        }
    }
}

export { WaveformVisualizer };
