import click
from flask.cli import FlaskGroup
from dj_online_studio import create_app
import os
import shutil

app = create_app()
cli = FlaskGroup(create_app=lambda: app)

@cli.command('init-db')
def init_db():
    """Initialize the database."""
    from dj_online_studio.extensions import db
    from dj_online_studio.models import Track, AudioAnalysis

    click.echo('Initializing the database...')
    db.create_all()
    click.echo('Database initialized!')

@cli.command('clean')
def clean():
    """Remove all database and uploaded files."""
    if click.confirm('This will delete all data. Continue?', abort=True):
        # Remove database file
        try:
            os.remove('instance/dj_studio.db')
            click.echo('Database removed.')
        except OSError:
            click.echo('No database file found.')

        # Remove uploaded files
        uploads_dir = os.path.join('instance', 'uploads')
        try:
            shutil.rmtree(uploads_dir)
            os.makedirs(uploads_dir)
            click.echo('Uploads directory cleaned.')
        except OSError:
            click.echo('No uploads directory found.')

@cli.command('setup')
def setup():
    """Set up the application."""
    # Create necessary directories
    click.echo('Creating directories...')
    for directory in ['instance', 'instance/uploads', 'migrations']:
        os.makedirs(directory, exist_ok=True)
        click.echo(f'Created {directory}/')

    # Initialize database
    click.echo('Initializing database...')
    from dj_online_studio.extensions import db
    db.create_all()

    click.echo('Setup complete! You can now run the application:')
    click.echo('  python run.py')

@cli.command('reset-db')
def reset_db():
    """Reset the database."""
    if click.confirm('This will delete all database data. Continue?', abort=True):
        from dj_online_studio.extensions import db
        db.drop_all()
        db.create_all()
        click.echo('Database has been reset.')

if __name__ == '__main__':
    cli()
