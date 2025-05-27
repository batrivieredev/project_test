document.addEventListener('DOMContentLoaded', function() {
    // Contexte audio pour la gestion du son
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    let analyserNodes = new Map();

    // Variables d'état
    let currentPlaylist = null; // Playlist actuellement sélectionnée
    let decksCount = 2; // Nombre de decks affichés (2 ou 4)

    // Classe Deck : gère un platine virtuel avec ses contrôles et sa visualisation
    class Deck {
        constructor(id) {
            this.id = id;
            this.audio = new Audio();
            this.isPlaying = false;
            this.gainNode = audioContext.createGain();
            this.analyserNode = audioContext.createAnalyser();
            this.gainNode.connect(this.analyserNode);
            this.analyserNode.connect(audioContext.destination);
            this.source = null;

            // Configuration de l'analyseur audio pour la visualisation
            this.analyserNode.fftSize = 2048;
            this.bufferLength = this.analyserNode.frequencyBinCount;
            this.dataArray = new Uint8Array(this.bufferLength);

            // Éléments DOM du deck
            this.element = document.getElementById(`deck-${id}`);
            if (!this.element) return;

            this.setupControls();
            this.setupAudio();
            this.setupWaveform();
            this.setupDragAndDrop();
        }

        // Configuration des contrôles (boutons et sliders)
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

        // Configuration des événements audio
        setupAudio() {
            this.audio.onended = () => {
                this.isPlaying = false;
                this.updateButtons();
            };

            this.audio.ontimeupdate = () => {
                this.updateProgress();
            };
        }

        // Création et configuration de la visualisation waveform
        setupWaveform() {
            const waveformContainer = document.createElement('div');
            waveformContainer.className = 'waveform-container';

            const waveform = document.createElement('canvas');
            waveform.className = 'waveform';
            waveformContainer.appendChild(waveform);

            const progress = document.createElement('div');
            progress.className = 'waveform-progress';
            waveformContainer.appendChild(progress);

            // Insert after controls
            const controls = this.element.querySelector('.controls');
            controls.parentNode.insertBefore(waveformContainer, controls.nextSibling);

            this.waveform = waveform;
            this.waveformProgress = progress;
            this.waveformCtx = waveform.getContext('2d');

            // Click handling for seeking
            waveformContainer.onclick = (e) => {
                const rect = waveformContainer.getBoundingClientRect();
                const clickPosition = (e.clientX - rect.left) / rect.width;
                this.audio.currentTime = this.audio.duration * clickPosition;
            };

            // Start animation
            this.drawWaveform();
        }

        // Configuration du drag & drop pour charger des morceaux
        setupDragAndDrop() {
            this.element.addEventListener('dragover', (e) => {
                e.preventDefault();
                this.element.classList.add('drag-over');
            });

            this.element.addEventListener('dragleave', () => {
                this.element.classList.remove('drag-over');
            });

            this.element.addEventListener('drop', (e) => {
                e.preventDefault();
                this.element.classList.remove('drag-over');
                const trackId = e.dataTransfer.getData('text/plain');
                if (trackId) {
                    this.loadTrack(trackId);
                }
            });
        }

        // Dessine la visualisation des fréquences en temps réel
        drawWaveform() {
            requestAnimationFrame(() => this.drawWaveform());

            const canvas = this.waveform;
            const ctx = this.waveformCtx;
            const width = canvas.width;
            const height = canvas.height;

            // Ensure canvas size matches container
            const container = canvas.parentElement;
            if (canvas.width !== container.clientWidth) {
                canvas.width = container.clientWidth;
            }
            if (canvas.height !== container.clientHeight) {
                canvas.height = container.clientHeight;
            }

            // Get frequency data
            this.analyserNode.getByteFrequencyData(this.dataArray);

            // Clear canvas
            ctx.clearRect(0, 0, width, height);

            // Draw frequency bars
            const barWidth = width / this.bufferLength;
            let x = 0;

            for(let i = 0; i < this.bufferLength; i++) {
                const barHeight = (this.dataArray[i] / 255) * height;

                // Color gradient based on frequency
                const hue = i / this.bufferLength * 360;
                ctx.fillStyle = `hsl(${hue}, 70%, 50%)`;

                ctx.fillRect(x, height - barHeight, barWidth, barHeight);
                x += barWidth;
            }
        }

        // Met à jour la barre de progression de lecture
        updateProgress() {
            if (this.audio.duration) {
                const progress = (this.audio.currentTime / this.audio.duration) * 100;
                this.waveformProgress.style.width = `${progress}%`;
            }
        }

        // Charge un morceau depuis l'API et configure l'audio
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

        // Met à jour les informations affichées du morceau
        updateTrackInfo(track) {
            const titleEl = this.element.querySelector('.track-name');
            const bpmEl = this.element.querySelector('.bpm-display');

            if (titleEl) titleEl.textContent = track.title || 'No Track';
            if (bpmEl) bpmEl.textContent = track.bpm ? `${track.bpm} BPM` : '--- BPM';
        }

        // Met à jour l'état des boutons de contrôle
        updateButtons() {
            const [playBtn, pauseBtn] = this.element.querySelectorAll('.controls button');
            playBtn.disabled = this.isPlaying;
            pauseBtn.disabled = !this.isPlaying;
        }

        // Démarre la lecture du morceau
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

    // Initialisation des 4 platines virtuelles
    const decks = {
        a: new Deck('a'),
        b: new Deck('b'),
        c: new Deck('c'),
        d: new Deck('d')
    };

    // Chargement et affichage des playlists
    async function loadPlaylists() {
        try {
            const response = await fetch('/api/playlists');
            const playlists = await response.json();
            const playlistsList = document.querySelector('.playlists-panel');

            if (playlistsList) {
                playlistsList.innerHTML = playlists.map(playlist => `
                    <div class="playlist-item" data-playlist-id="${playlist.id}">
                        <span class="material-icons">playlist_play</span>
                        ${playlist.name}
                    </div>
                `).join('');

                // Add click handlers
                playlistsList.querySelectorAll('.playlist-item').forEach(item => {
                    item.onclick = () => {
                        const playlistId = item.dataset.playlistId;
                        loadPlaylistTracks(playlistId);

                        // Update active state
                        playlistsList.querySelectorAll('.playlist-item').forEach(p =>
                            p.classList.remove('active'));
                        item.classList.add('active');
                    };
                });
            }
        } catch (error) {
            console.error('Error loading playlists:', error);
        }
    }

    // Charge les morceaux d'une playlist spécifique
    async function loadPlaylistTracks(playlistId) {
        try {
            const response = await fetch(`/api/playlists/${playlistId}/tracks`);
            const tracks = await response.json();
            const tracksList = document.getElementById('tracksList');

            if (tracksList) {
                tracksList.innerHTML = tracks.length ? tracks.map(track => `
                    <tr class="track-row" draggable="true" data-track-id="${track.id}">
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

                // Add drag handlers
                tracksList.querySelectorAll('tr[data-track-id]').forEach(row => {
                    row.ondragstart = (e) => {
                        e.dataTransfer.setData('text/plain', row.dataset.trackId);
                    };

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
            console.error('Error loading playlist tracks:', error);
        }
    }

    // Charge tous les morceaux de la bibliothèque
    async function loadTracks() {
        try {
            const response = await fetch('/api/tracks');
            const tracks = await response.json();
            const tracksList = document.getElementById('tracksList');

            if (tracksList) {
                tracksList.innerHTML = tracks.length ? tracks.map(track => `
                    <tr class="track-row" draggable="true" data-track-id="${track.id}">
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

                // Add drag handlers
                tracksList.querySelectorAll('tr[data-track-id]').forEach(row => {
                    row.ondragstart = (e) => {
                        e.dataTransfer.setData('text/plain', row.dataset.trackId);
                    };

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

    // Chargement initial des playlists et morceaux
    loadPlaylists();
    loadTracks();

    // Gestion du switch entre 2 et 4 decks
    const layout2DecksBtn = document.getElementById('layout2Decks');
    const layout4DecksBtn = document.getElementById('layout4Decks');
    const decksContainer = document.querySelector('.row.g-3');

    if (layout2DecksBtn && layout4DecksBtn && decksContainer) {
        // Cache les decks C et D au démarrage
        document.querySelectorAll('#deck-c, #deck-d').forEach(deck =>
            deck.style.display = 'none');

        layout2DecksBtn.onclick = () => {
            decksCount = 2;
            const decksContainer = document.querySelector('.row.g-3');
            decksContainer.classList.remove('four-decks');
            decksContainer.classList.add('two-decks');
            document.querySelectorAll('#deck-c, #deck-d').forEach(deck =>
                deck.style.display = 'none');
            layout2DecksBtn.classList.add('active');
            layout4DecksBtn.classList.remove('active');
        };

        layout4DecksBtn.onclick = () => {
            decksCount = 4;
            const decksContainer = document.querySelector('.row.g-3');
            decksContainer.classList.remove('two-decks');
            decksContainer.classList.add('four-decks');
            document.querySelectorAll('#deck-c, #deck-d').forEach(deck =>
                deck.style.display = 'block');
            layout4DecksBtn.classList.add('active');
            layout2DecksBtn.classList.remove('active');
        };
    }

    // Gestion du toggle du panneau des playlists
    const togglePlaylistsBtn = document.getElementById('togglePlaylists');
    const playlistsPanel = document.querySelector('.playlists-panel');

    if (togglePlaylistsBtn && playlistsPanel) {
        togglePlaylistsBtn.onclick = () => {
            playlistsPanel.classList.toggle('active');
            togglePlaylistsBtn.classList.toggle('active');
        };
    }

    // Gestion de la sélection du deck actif
    document.querySelectorAll('.library-controls button').forEach(btn => {
        btn.onclick = () => {
            document.querySelectorAll('.library-controls button').forEach(b =>
                b.classList.remove('active'));
            btn.classList.add('active');
        };
    });

    // Configuration du crossfader entre les decks
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

    // Gestion de l'upload de fichiers audio
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
                if (currentPlaylist) {
                    loadPlaylistTracks(currentPlaylist);
                } else {
                    loadTracks();
                }
            })
            .catch(error => console.error('Upload error:', error));
        });
    }

    // Scanner la bibliothèque musicale
    window.scanLibrary = async function() {
        try {
            document.body.style.cursor = 'wait';
            const response = await fetch('/api/scan-music');
            const data = await response.json();
            console.log('Scan started:', data);

            let attempts = 0;
            const maxAttempts = 5;
            const checkInterval = setInterval(async () => {
                if (currentPlaylist) {
                    await loadPlaylistTracks(currentPlaylist);
                } else {
                    await loadTracks();
                }
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

    // Analyse du BPM des morceaux
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
                if (currentPlaylist) {
                    loadPlaylistTracks(currentPlaylist);
                } else {
                    loadTracks();
                }
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
