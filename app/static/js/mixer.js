// Theme handling
let isDarkMode = true;

function toggleTheme() {
    isDarkMode = !isDarkMode;
    document.body.classList.toggle('light-mode');
    const themeIcon = document.querySelector('#themeToggle .material-icons');
    themeIcon.textContent = isDarkMode ? 'dark_mode' : 'light_mode';

    // Update UI elements
    document.querySelectorAll('.card, .btn-outline-secondary, .table').forEach(el => {
        el.classList.toggle('light-mode');
    });

    // Update background and text colors
    if (isDarkMode) {
        document.body.style.backgroundColor = '#121212';
        document.body.style.color = '#fff';
    } else {
        document.body.style.backgroundColor = '#f8f9fa';
        document.body.style.color = '#212529';
    }
}

// Initialisation du mixer
document.addEventListener('DOMContentLoaded', () => {
    // Theme toggle initialization
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);
    // Initialise la bibliothèque
    const library = new TrackLibrary();

    // Initialise les decks principaux et leurs effets
    const deckA = new DeckController('A');
    const deckB = new DeckController('B');
    const effectsA = new EffectChain(deckA.audioEngine);
    const effectsB = new EffectChain(deckB.audioEngine);

    // Gestion du crossfader
    const crossfader = document.getElementById('crossfader');
    if (crossfader) {
        crossfader.addEventListener('input', () => {
            // Convert crossfader range [-1, 1] to [0, 1] for volume
            const value = (parseFloat(crossfader.value) + 1) / 2;

            // Apply smooth crossfade curve
            const gainA = Math.cos(value * Math.PI / 2);
            const gainB = Math.cos((1 - value) * Math.PI / 2);

            deckA.audioEngine.setVolume(gainA);
            deckB.audioEngine.setVolume(gainB);
        });
    }

    // Gestion des volumes individuels
    setupVolumeControl('A', deckA);
    setupVolumeControl('B', deckB);

    // Initialise les decks supplémentaires (désactivés par défaut)
    let deckC = null;
    let deckD = null;
    let effectsC = null;
    let effectsD = null;

    // Layout switching
    const layout2DecksBtn = document.getElementById('layout2Decks');
    const layout4DecksBtn = document.getElementById('layout4Decks');
    const decksContainer = document.querySelector('.decks-container');
    const deckCElement = document.querySelector('.deck-c');
    const deckDElement = document.querySelector('.deck-d');

    if (layout2DecksBtn && layout4DecksBtn && decksContainer) {
        // Set initial state (2-deck layout)
        layout2DecksBtn.classList.add('btn-primary');
        layout2DecksBtn.classList.remove('btn-outline-secondary');

        layout2DecksBtn.addEventListener('click', () => {
            // Switch to 2-deck layout
            decksContainer.classList.remove('layout-4-decks');
            layout2DecksBtn.classList.add('btn-primary');
            layout2DecksBtn.classList.remove('btn-outline-secondary');
            layout4DecksBtn.classList.remove('btn-primary');
            layout4DecksBtn.classList.add('btn-outline-secondary');

            // Hide and cleanup decks C and D
            deckCElement.classList.add('d-none');
            deckDElement.classList.add('d-none');
            if (deckC) {
                deckC.audioEngine.stop();
                deckD.audioEngine.stop();
            }
        });

        layout4DecksBtn.addEventListener('click', () => {
            // Switch to 4-deck layout
            decksContainer.classList.add('layout-4-decks');
            layout4DecksBtn.classList.add('btn-primary');
            layout4DecksBtn.classList.remove('btn-outline-secondary');
            layout2DecksBtn.classList.remove('btn-primary');
            layout2DecksBtn.classList.add('btn-outline-secondary');

            // Initialize and show decks C and D
            deckCElement.classList.remove('d-none');
            deckDElement.classList.remove('d-none');

            if (!deckC) {
                deckC = new DeckController('C');
                deckD = new DeckController('D');
                effectsC = new EffectChain(deckC.audioEngine);
                effectsD = new EffectChain(deckD.audioEngine);

                // Setup volume controls for new decks
                setupVolumeControl('C', deckC);
                setupVolumeControl('D', deckD);
            }
        });
    }
    // Setup EQ controls for each deck
    setupEQControls('A', deckA);
    setupEQControls('B', deckB);

    // Handle track loading for all decks
    document.addEventListener('loadTrack', (e) => {
        const { track, deckId } = e.detail;

        // Verify track object and ID exist
        if (!track || !track.id) {
            console.error('Invalid track data:', track);
            return;
        }

        let targetDeck;
        switch(deckId) {
            case 'A':
                targetDeck = deckA;
                break;
            case 'B':
                targetDeck = deckB;
                break;
            case 'C':
                if (deckC) targetDeck = deckC;
                break;
            case 'D':
                if (deckD) targetDeck = deckD;
                break;
        }

        if (targetDeck) {
            targetDeck.loadTrack(track);
        } else {
            console.error('Invalid deck ID:', deckId);
        }
    });

    // EQ controls setup when switching to 4 decks
    layout4DecksBtn.addEventListener('click', () => {
        if (!deckC) {
            deckC = new DeckController('C');
            deckD = new DeckController('D');
            effectsC = new EffectChain(deckC.audioEngine);
            effectsD = new EffectChain(deckD.audioEngine);

            setupVolumeControl('C', deckC);
            setupVolumeControl('D', deckD);
            setupEQControls('C', deckC);
            setupEQControls('D', deckD);
        }
    });

    // Synchronisation des BPM entre tous les decks actifs
    setupBPMSync(deckA, deckB);

    // Raccourcis clavier
    setupKeyboardShortcuts(deckA, deckB, deckC, deckD);
});

function setupVolumeControl(deckId, deck) {
    const volumeControl = document.getElementById(`volume${deckId}`);
    if (volumeControl) {
        volumeControl.addEventListener('input', () => {
            const value = parseFloat(volumeControl.value);
            deck.audioEngine.setVolume(value);
        });
    }
}

function setupDeckSelection() {
    const decks = document.querySelectorAll('.deck');
    decks.forEach(deck => {
        deck.addEventListener('click', () => {
            decks.forEach(d => d.classList.remove('selected'));
            deck.classList.add('selected');
        });
    });
}

function setupBPMSync(deckA, deckB) {
    const syncButton = document.getElementById('syncDecks');
    if (!syncButton) return;

    syncButton.addEventListener('click', () => {
        if (!deckA.currentTrack || !deckB.currentTrack) return;

        // Récupère les BPM des deux morceaux
        const bpmA = deckA.currentTrack.bpm;
        const bpmB = deckB.currentTrack.bpm;
        if (!bpmA || !bpmB) return;

        // Calcule le ratio pour la synchronisation
        const ratio = bpmA / bpmB;

        // Ajuste la vitesse du deck B
        deckB.audioEngine.source.playbackRate.value = ratio;

        // Met à jour l'interface
        const pitchControl = document.querySelector(`[data-pitch="B"]`);
        if (pitchControl) {
            pitchControl.value = (ratio - 1) * 100;
        }
    });
}

function setupKeyboardShortcuts(deckA, deckB, deckC, deckD) {
    document.addEventListener('keydown', (e) => {
        // Empêche les raccourcis si on est dans un champ de texte
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        switch(e.code) {
            // Deck A
            case 'KeyQ':
                deckA.togglePlay();
                break;
            case 'KeyW':
                deckA.pressCue();
                break;
            case 'KeyE':
                // Load to deck A
                document.querySelector('#loadDeckA').click();
                break;
            case 'KeyR':
                // Eject from deck A
                document.querySelector('#ejectDeckA').click();
                break;

            // Deck B
            case 'KeyP':
                deckB.togglePlay();
                break;
            case 'KeyO':
                deckB.pressCue();
                break;
            case 'KeyI':
                // Load to deck B
                document.querySelector('#loadDeckB').click();
                break;
            case 'KeyU':
                // Eject from deck B
                document.querySelector('#ejectDeckB').click();
                break;

            // Deck C
            case 'KeyZ':
                if (deckC) deckC.togglePlay();
                break;
            case 'KeyX':
                if (deckC) deckC.pressCue();
                break;
            case 'KeyC':
                if (deckC) document.querySelector('#loadDeckC').click();
                break;
            case 'KeyV':
                if (deckC) document.querySelector('#ejectDeckC').click();
                break;

            // Deck D
            case 'KeyM':
                if (deckD) deckD.togglePlay();
                break;
            case 'KeyN':
                if (deckD) deckD.pressCue();
                break;
            case 'KeyB':
                if (deckD) document.querySelector('#loadDeckD').click();
                break;
            case 'KeyG':
                if (deckD) document.querySelector('#ejectDeckD').click();
                break;

            // Global controls
            case 'Space':
                e.preventDefault(); // Empêche le défilement de la page
                // Joue/Pause le deck sélectionné
                const selectedDeck = document.querySelector('.deck.selected');
                if (selectedDeck) {
                    let deck;
                    if (selectedDeck.classList.contains('deck-left')) deck = deckA;
                    else if (selectedDeck.classList.contains('deck-right')) deck = deckB;
                    else if (selectedDeck.classList.contains('deck-c')) deck = deckC;
                    else if (selectedDeck.classList.contains('deck-d')) deck = deckD;

                    if (deck) deck.togglePlay();
                }
                break;
        }
    });

    document.addEventListener('keyup', (e) => {
        // Empêche les raccourcis si on est dans un champ de texte
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        switch(e.code) {
            case 'KeyW':
                deckA.releaseCue();
                break;
            case 'KeyO':
                deckB.releaseCue();
                break;
            case 'KeyX':
                if (deckC) deckC.releaseCue();
                break;
            case 'KeyN':
                if (deckD) deckD.releaseCue();
                break;
        }
    });
}

// Setup EQ and effects controls for a deck
function setupEQControls(deckId, deck) {
    // EQ Controls
    ['low', 'mid', 'high'].forEach(band => {
        const slider = document.querySelector(`input[data-eq="${deckId}"][data-band="${band}"]`);
        if (slider) {
            slider.addEventListener('input', (e) => {
                const value = parseFloat(e.target.value);
                if (deck.audioEngine.setEQ) {
                    deck.audioEngine.setEQ(band, value);
                }
            });
        }
    });

    // Filter control
    const filterSlider = document.querySelector(`input[data-fx="${deckId}"][data-effect="filter"]`);
    if (filterSlider) {
        filterSlider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            if (deck.audioEngine.setFilter) {
                deck.audioEngine.setFilter(value);
            }
        });
    }

    // Effect controls
    ['delay', 'reverb'].forEach(effect => {
        const slider = document.querySelector(`input[data-fx="${deckId}"][data-effect="${effect}"]`);
        if (slider) {
            slider.addEventListener('input', (e) => {
                const value = parseFloat(e.target.value) / 100; // Normalize to 0-1
                if (deck.audioEngine.setEffectParam) {
                    deck.audioEngine.setEffectParam(effect, value);
                }
            });
        }
    });
}

// Fonctions utilitaires pour l'interface
function showTooltip(element, message) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = message;

    element.appendChild(tooltip);
    setTimeout(() => tooltip.remove(), 2000);
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Gestion des erreurs
window.onerror = function(msg, url, lineNo, columnNo, error) {
    console.error('Error: ' + msg + '\nURL: ' + url + '\nLine: ' + lineNo);
    return false;
};

window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
});
