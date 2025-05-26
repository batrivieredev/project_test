document.addEventListener('DOMContentLoaded', function() {
    // Audio Context
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();

    // Deck initialization
    class Deck {
        constructor(id) {
            this.id = id;
            this.audio = new Audio();
            this.isPlaying = false;
            this.gainNode = audioContext.createGain();
            this.gainNode.connect(audioContext.destination);
            this.source = null;

            // DOM elements
            this.element = document.getElementById(`deck-${id}`);
            if (!this.element) return;

            this.setupControls();
            this.setupAudio();
        }

        setupControls() {
            const controls = this.element.querySelector('.controls');
            const [playBtn, pauseBtn, cueBtn, loopBtn] = controls.querySelectorAll('button');
            const volumeSlider = document.getElementById(`volume-${this.id}`);
            const pitchSlider = document.getElementById(`pitch-${this.id}`);

            playBtn.onclick = () => this.play();
            pauseBtn.onclick = () => this.pause();
            cueBtn.onclick = () => this.cue();
            loopBtn.onclick = () => this.toggleLoop();

            if (volumeSlider) {
                volumeSlider.oninput = (e) => {
                    if (this.gainNode) {
                        this.gainNode.gain.value = e.target.value / 100;
                    }
                };
            }

            if (pitchSlider) {
                pitchSlider.oninput = (e) => {
                    const value = 1 + (parseFloat(e.target.value) / 100);
                    this.audio.playbackRate = value;
                };
            }
        }

        setupAudio() {
            this.audio.onended = () => {
                this.isPlaying = false;
                this.updateButtons();
            };
        }

        async loadTrack(trackId) {
            try {
                const response = await fetch(`/api/tracks/${trackId}/file`);
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);

                this.audio.src = url;

                // Reset audio nodes
                if (this.source) {
                    this.source.disconnect();
                }
                this.source = audioContext.createMediaElementSource(this.audio);
                this.source.connect(this.gainNode);

            } catch (error) {
                console.error('Error loading track:', error);
            }
        }

        updateButtons() {
            const [playBtn, pauseBtn] = this.element.querySelectorAll('.controls button');
            playBtn.disabled = this.isPlaying;
            pauseBtn.disabled = !this.isPlaying;
        }

        async play() {
            if (!this.audio.src) return;
            try {
                await audioContext.resume();
                await this.audio.play();
                this.isPlaying = true;
                this.updateButtons();
            } catch (error) {
                console.error('Error playing:', error);
            }
        }

        pause() {
            this.audio.pause();
            this.isPlaying = false;
            this.updateButtons();
        }

        cue() {
            this.audio.currentTime = 0;
        }

        toggleLoop() {
            this.audio.loop = !this.audio.loop;
            this.element.querySelector('.controls button:last-child').classList.toggle('active');
        }
    }

    // Initialize decks
    const decks = {
        a: new Deck('a'),
        b: new Deck('b')
    };

    // Track loading
    document.querySelectorAll('tr[data-track-id]').forEach(row => {
        row.onclick = () => {
            const trackId = row.dataset.trackId;
            const activeDeck = document.querySelector('.library-controls button.active');
            if (activeDeck) {
                const deckId = activeDeck.dataset.deck.toLowerCase();
                decks[deckId]?.loadTrack(trackId);
            }
        };
    });

    // Crossfader
    const crossfader = document.querySelector('.crossfader');
    if (crossfader) {
        crossfader.oninput = (e) => {
            const value = parseInt(e.target.value);
            const gainA = Math.cos((value + 100) * (Math.PI / 400));
            const gainB = Math.cos((100 - value) * (Math.PI / 400));

            if (decks.a?.gainNode) decks.a.gainNode.gain.value = gainA;
            if (decks.b?.gainNode) decks.b.gainNode.gain.value = gainB;
        };
    }

    // File upload
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');

    if (uploadZone && fileInput) {
        uploadZone.ondragover = (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        };

        uploadZone.ondragleave = () => {
            uploadZone.classList.remove('dragover');
        };

        uploadZone.ondrop = (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            handleFiles(e.dataTransfer.files);
        };

        uploadZone.onclick = () => fileInput.click();
        fileInput.onchange = () => handleFiles(fileInput.files);
    }

    function handleFiles(files) {
        Array.from(files).forEach(file => {
            const formData = new FormData();
            formData.append('file', file);

            fetch('/api/tracks', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                console.log('Upload successful:', data);
                location.reload(); // Refresh to show new tracks
            })
            .catch(error => console.error('Upload error:', error));
        });
    }

    // BPM Analysis
    window.analyzeBPM = function(trackId) {
        fetch(`/api/tracks/${trackId}/analyze-bpm`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.bpm) {
                console.log('BPM detected:', data.bpm);
                location.reload(); // Refresh to show updated BPM
            }
        })
        .catch(error => console.error('BPM analysis error:', error));
    };
});
