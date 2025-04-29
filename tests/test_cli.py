import os
import pytest
from click.testing import CliRunner
from dj_online_studio.extensions import db
from cli import setup, init_db, clean, reset_db

def test_setup_command(app):
    """Test setup command creates necessary directories and database."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(setup)
        assert result.exit_code == 0

        # Check directories were created
        assert os.path.exists('instance')
        assert os.path.exists('instance/uploads')
        assert os.path.exists('migrations')

def test_init_db_command(app):
    """Test database initialization command."""
    runner = CliRunner()
    with app.app_context():
        result = runner.invoke(init_db)
        assert result.exit_code == 0

        # Verify tables exist
        tables = db.metadata.tables.keys()
        assert 'tracks' in tables
        assert 'audio_analyses' in tables

def test_clean_command_abort(app):
    """Test clean command with abort."""
    runner = CliRunner()
    result = runner.invoke(clean, input='n\n')  # Answer no to confirmation
    assert result.exit_code == 1
    assert 'Aborted!' in result.output

def test_clean_command_confirm(app, test_track_with_analysis):
    """Test clean command with confirmation."""
    runner = CliRunner()
    with app.app_context():
        # Create test file in uploads
        test_file = os.path.join(app.config['UPLOAD_FOLDER'], 'test.wav')
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, 'w') as f:
            f.write('test')

        result = runner.invoke(clean, input='y\n')  # Answer yes to confirmation
        assert result.exit_code == 0

        # Check database is empty
        assert db.session.query(db.metadata.tables['tracks']).count() == 0
        assert db.session.query(db.metadata.tables['audio_analyses']).count() == 0

        # Check uploads directory is empty
        assert not os.path.exists(test_file)
        assert os.path.exists(app.config['UPLOAD_FOLDER'])  # Directory should still exist but be empty

def test_reset_db_command_abort(app):
    """Test reset database command with abort."""
    runner = CliRunner()
    result = runner.invoke(reset_db, input='n\n')  # Answer no to confirmation
    assert result.exit_code == 1
    assert 'Aborted!' in result.output

def test_reset_db_command_confirm(app, test_track_with_analysis):
    """Test reset database command with confirmation."""
    runner = CliRunner()
    with app.app_context():
        # Verify data exists before reset
        assert db.session.query(db.metadata.tables['tracks']).count() > 0

        result = runner.invoke(reset_db, input='y\n')  # Answer yes to confirmation
        assert result.exit_code == 0

        # Verify database is empty
        assert db.session.query(db.metadata.tables['tracks']).count() == 0
        assert db.session.query(db.metadata.tables['audio_analyses']).count() == 0
