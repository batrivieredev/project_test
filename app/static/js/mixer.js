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

                // Clean up old URL if exists
                if (this.audio.src) {
                    URL.revokeObjectURL(this.audio.src);
                }

                this.audio.src = url;

                // Reset audio nodes
                if (this.source) {
                    this.source.disconnect();
                }
                this.source = audioContext.createMediaElementSource(this.audio);
                this.source.connect(this.gainNode);

                // Get track info
                const trackInfo = await fetch(`/api/tracks/${trackId}`).then(r => r.json());
                this.updateTrackInfo(trackInfo);

            } catch (error) {
                console.error('Error loading track:', error);
            }
        }

        updateTrackInfo(track) {
            const titleEl = this.element.querySelector('.track-name');
            const bpmEl = this.element.querySelector('.bpm-display');

            if (titleEl) titleEl.textContent = track.title || 'No Track';
            if (bpmEl) bpmEl.textContent = track.bpm ? `${track.bpm} BPM` : '--- BPM';
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

    // Load and display tracks
    async function loadTracks() {
        try {
            const response = await fetch('/api/tracks');
            const tracks = await response.json();
            const tracksList = document.getElementById('tracksList');

            if (tracksList) {
                tracksList.innerHTML = tracks.length ? tracks.map(track => `
                    <tr data-track-id="${track.id}">
                        <td>${track.title || 'Unknown Title'}</td>
                        <td>${track.artist || 'Unknown Artist'}</td>
                        <td>${track.bpm || '---'}</td>
                        <td>
                            <button class="btn btn-sm btn-outline-secondary" onclick="analyzeBPM(${track.id})">
                                <span class="material-icons">speed</span>
                            </button>
                        </td>
                    </tr>
                `).join('') : '<tr><td colspan="4" class="text-center">No tracks found</td></tr>';

                // Add click handlers
                tracksList.querySelectorAll('tr[data-track-id]').forEach(row => {
                    row.onclick = () => {
                        const trackId = row.dataset.trackId;
                        const activeDeck = document.querySelector('.library-controls button.active');
                        if (activeDeck) {
                            const deckId = activeDeck.dataset.deck.toLowerCase();
                            decks[deckId]?.loadTrack(trackId);
                        }
                    };
                });
            }
        } catch (error) {
            console.error('Error loading tracks:', error);
        }
    }

    // Initial tracks load
    loadTracks();

    // Deck selection handlers
    document.querySelectorAll('.library-controls button').forEach(btn => {
        btn.onclick = () => {
            document.querySelectorAll('.library-controls button').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
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
                loadTracks(); // Refresh tracks list instead of page reload
            })
            .catch(error => console.error('Upload error:', error));
        });
    }

    // Scanner handler
    window.scanLibrary = async function() {
        try {
            // Show loading state
            document.body.style.cursor = 'wait';
            const response = await fetch('/api/scan-music');
            const data = await response.json();
            console.log('Scan started:', data);

            // Refresh tracks list a few times to catch newly scanned files
            let attempts = 0;
            const maxAttempts = 5;
            const checkInterval = setInterval(async () => {
                await loadTracks();
                attempts++;
                if (attempts >= maxAttempts) {
                    clearInterval(checkInterval);
                    document.body.style.cursor = 'default';
                }
            }, 2000);
        } catch (error) {
            console.error('Scan error:', error);
            document.body.style.cursor = 'default';
        }
    };

    // BPM Analysis
    window.analyzeBPM = async function(trackId) {
        try {
            const btn = document.querySelector(`tr[data-track-id="${trackId}"] button`);
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="material-icons spin">refresh</span>';
            }

            const response = await fetch(`/api/tracks/${trackId}/analyze-bpm`, {
                method: 'POST'
            });
            const data = await response.json();

            if (data.bpm) {
                console.log('BPM detected:', data.bpm);
                loadTracks(); // Refresh tracks
            } else {
                console.error('BPM detection failed');
                if (btn) {
                    btn.innerHTML = '<span class="material-icons">error</span>';
                    setTimeout(() => {
                        btn.disabled = false;
                        btn.innerHTML = '<span class="material-icons">speed</span>';
                    }, 2000);
                }
            }
        } catch (error) {
            console.error('BPM analysis error:', error);
            const btn = document.querySelector(`tr[data-track-id="${trackId}"] button`);
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<span class="material-icons">speed</span>';
            }
        }
    };
});
