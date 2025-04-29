# DJ Online Studio

A Python-based web application that replicates Serato DJ Pro's functionality in the browser. Features real-time audio mixing, waveform visualization, and BPM detection.

## Features

- Serato DJ Pro-like interface
- Dual-deck mixing with real-time waveform display
- Color-coded frequency visualization (bass, mids, highs)
- Advanced BPM detection using multiple algorithms
- Track analysis and metadata handling
- Smooth crossfader with exponential curve
- Volume and pitch control for each deck
- Server-side audio processing with Librosa
- Responsive design

## Installation

### Quick Start

#### Windows
```batch
quickstart.bat
python run.py
```

#### macOS/Linux
```bash
chmod +x quickstart.sh
./quickstart.sh
python run.py
```

### Manual Installation

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize database:
```bash
python cli.py init-db
```

4. Run the application:
```bash
python run.py
```

## Development Setup

1. Install development dependencies:
```bash
pip install -r requirements.txt
pip install -r tests/requirements-test.txt
```

2. Set up pre-commit hooks:
```bash
pre-commit install
```

3. Run tests:
```bash
pytest
```

4. Run with debug mode:
```bash
export FLASK_ENV=development  # On Windows: set FLASK_ENV=development
python run.py
```

## Project Structure

```
dj_online_studio/
├── static/              # Static assets
│   ├── css/            # Stylesheets
│   └── js/             # JavaScript modules
├── templates/          # HTML templates
├── routes/            # Flask route handlers
├── models.py          # Database models
├── audio_processor.py # Audio analysis
└── config.py         # Application config
```

## Testing

Run the test suite:
```bash
pytest
```

Generate coverage report:
```bash
pytest --cov=dj_online_studio --cov-report=html
```

View the coverage report in `htmlcov/index.html`

## CLI Commands

- Initialize database:
  ```bash
  python cli.py init-db
  ```

- Clean all data:
  ```bash
  python cli.py clean
  ```

- Reset database:
  ```bash
  python cli.py reset-db
  ```

- Setup application:
  ```bash
  python cli.py setup
  ```

## Production Deployment

1. Set production environment variables:
```bash
export FLASK_ENV=production
export SECRET_KEY=your-secret-key
```

2. Run using Gunicorn:
```bash
gunicorn wsgi:app
```

## Technical Details

### Backend
- Flask web framework
- SQLAlchemy for database management
- Librosa for audio analysis
- FFmpeg for audio processing

### Frontend
- Web Audio API for real-time processing
- Canvas API for waveform visualization
- Modern JavaScript (ES6+) with modules
- CSS Grid and Flexbox for responsive layout

## Contributing

1. Fork the repository
2. Create your feature branch:
   ```bash
   git checkout -b feature/your-feature
   ```
3. Make your changes and commit:
   ```bash
   git commit -m 'Add some feature'
   ```
4. Push to the branch:
   ```bash
   git push origin feature/your-feature
   ```
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Troubleshooting

### Common Issues

1. Database initialization fails:
   ```bash
   python cli.py clean
   python cli.py init-db
   ```

2. Audio processing errors:
   - Ensure FFmpeg is installed
   - Check file permissions
   - Verify audio file format support

3. Web Audio API issues:
   - Use a modern browser
   - Enable audio playback permissions

### Getting Help

- Open an issue for bugs
- Check existing issues for solutions
- Consult the documentation in /docs

## Acknowledgments

- Inspired by Serato DJ Pro
- Uses Librosa for audio analysis
- Web Audio API for real-time processing
- FFmpeg for audio format support
