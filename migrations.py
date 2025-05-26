from app import create_app, db
from app.models import User

def initialize_database():
    """Initialize the database"""
    app = create_app()
    with app.app_context():
        # Drop and recreate all tables
        db.drop_all()
        db.create_all()
        print("✅ Tables created successfully")

        # Create admin user
        admin = User(
            username='admin',
            email='admin@local.dev',
            is_admin=True,
            can_access_mixer=True,
            can_access_converter=True,
            is_active=True
        )
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
        print("✅ Utilisateur admin créé avec succès")

        print("✅ Base de données mise à jour avec succès")

if __name__ == '__main__':
    initialize_database()
