import { DJDeck } from './deck.js';

class DJMixer {
    constructor() {
        // Initialize decks
        this.deck1 = new DJDeck(1);
        this.deck2 = new DJDeck(2);

        // Get crossfader element
        this.crossfader = document.getElementById('crossfader');

        this.setupEventListeners();
    }

    setupEventListeners() {
        // Crossfader control with smooth curve
        this.crossfader.addEventListener('input', (e) => this.handleCrossfade(e.target.value));

        // Handle window events
        window.addEventListener('beforeunload', () => this.cleanup());
    }

    handleCrossfade(value) {
        // Convert linear slider value to exponential curve for smoother transitions
        const normalizedValue = value / 100;

        // Apply exponential curve to create smoother crossfading
        const deck1Volume = Math.cos(normalizedValue * Math.PI / 2);
        const deck2Volume = Math.sin(normalizedValue * Math.PI / 2);

        // Apply volume changes to decks, considering their individual volume settings
        this.deck1.setVolume(deck1Volume * this.deck1.volumeSlider.value);
        this.deck2.setVolume(deck2Volume * this.deck2.volumeSlider.value);
    }

    cleanup() {
        // Clean up resources
        this.deck1.destroy();
        this.deck2.destroy();
    }
}

// Initialize the mixer when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const mixer = new DJMixer();
});

export { DJMixer };
