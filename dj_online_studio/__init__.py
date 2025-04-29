import os
from flask import Flask
from flask_cors import CORS
from .config import Config

def create_app(config_class=Config):
    # Initialize Flask app
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Create uploads directory
    uploads_dir = os.path.join(app.instance_path, 'uploads')
    try:
        os.makedirs(uploads_dir)
    except OSError:
        pass

    app.config['UPLOAD_FOLDER'] = uploads_dir

    # Initialize CORS
    CORS(app)

    # Initialize extensions
    from .extensions import db, migrate
    db.init_app(app)
    migrate.init_app(app, db)

    # Import models to ensure they're registered with SQLAlchemy
    from . import models

    # Register blueprints
    from .routes import main
    app.register_blueprint(main.bp)

    # Create database tables
    with app.app_context():
        db.create_all()

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
        return response

    return app
