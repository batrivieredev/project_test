from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Initialize SQLAlchemy without session options
db = SQLAlchemy()
migrate = Migrate()
