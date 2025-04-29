# Installation and Development Guide

## Prerequisites

1. Python 3.8 or higher
2. FFmpeg installed on your system
3. pip (Python package installer)
4. virtualenv or venv module

## Quick Installation

### Unix/macOS
```bash
# Make scripts executable
chmod +x make_executable.sh
./make_executable.sh

# Run quickstart script
./quickstart.sh
```

### Windows
```batch
quickstart.bat
```

## Manual Installation

1. Create and activate virtual environment:
```bash
# Unix/macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
.\venv\Scripts\activate
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

2. Install pre-commit hooks:
```bash
pre-commit install
```

## Running Tests

### Quick Run
```bash
# Unix/macOS
./run_tests.py

# Windows
python run_tests.py
```

### Manual Test Running

1. Generate test audio files:
```bash
python -m tests.generate_test_audio
```

2. Run specific test modules:
```bash
pytest tests/test_models.py -v
pytest tests/test_routes.py -v
pytest tests/test_audio_processor.py -v
pytest tests/test_cli.py -v
```

3. Run with coverage:
```bash
pytest --cov=dj_online_studio --cov-report=html
```

4. View coverage report:
```bash
# Unix/macOS
open htmlcov/index.html

# Windows
start htmlcov/index.html
```

## Test Suite Structure

```
tests/
├── __init__.py          # Test package initialization
├── conftest.py          # Test fixtures and configuration
├── test_audio_processor.py  # Audio processing tests
├── test_cli.py          # CLI command tests
├── test_models.py       # Database model tests
├── test_routes.py       # API endpoint tests
├── generate_test_audio.py  # Test audio file generator
└── test_files/         # Directory for test audio files
    ├── .gitkeep
    └── .gitignore
```

## Configuration Files

- `setup.cfg`: Test and code quality settings
- `pytest.ini`: PyTest configuration
- `pyproject.toml`: Project metadata and tool settings
- `.pre-commit-config.yaml`: Pre-commit hook configuration

## Troubleshooting

### Common Test Issues

1. Test database errors:
```bash
python cli.py reset-db
pytest
```

2. Missing test audio files:
```bash
python -m tests.generate_test_audio
pytest
```

3. Coverage report not generating:
```bash
pytest --cov=dj_online_studio --cov-report=term-missing --cov-report=html
```

### Environment Issues

1. SQLite errors:
- Check database file permissions
- Verify SQLite is installed
- Try deleting and reinitializing the database

2. Audio processing errors:
- Verify FFmpeg is installed and in PATH
- Check audio file permissions
- Ensure test audio files are generated

3. Pre-commit hook failures:
- Update hooks: `pre-commit autoupdate`
- Clean repo: `pre-commit clean`
- Run manually: `pre-commit run --all-files`

## Getting Help

- Check the test output for specific error messages
- Review the coverage report for untested code
- Consult the documentation in /docs
- Open an issue on the project repository
