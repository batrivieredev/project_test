import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Security settings
    SECRET_KEY = os.urandom(24).hex()

    # Database settings
    # PostgreSQL Database settings
    DB_USER = os.getenv('DB_USER', 'project_user')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'secure_password')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'project_test')

    SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_pre_ping': True,
        'pool_recycle': 300
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File storage settings
    MUSIC_FOLDER = os.getenv('MUSIC_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'musiques'))
    UPLOAD_FOLDER = os.getenv('UPLOAD_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads'))
    MAX_CONTENT_LENGTH = 256 * 1024 * 1024  # 256MB max file size
