from app import create_app, db
from app.models import User
import sqlite3

def upgrade_database():
    """Met à jour la structure de la base de données"""
    app = create_app()
    with app.app_context():
        # Vérifie les colonnes existantes
        conn = sqlite3.connect('app/app.db')
        cursor = conn.cursor()
        columns = [column[1] for column in cursor.execute("PRAGMA table_info('users')").fetchall()]

        # Ajoute les colonnes si elles n'existent pas
        if 'can_access_mixer' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN can_access_mixer BOOLEAN DEFAULT FALSE')
        if 'is_active' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE')

        conn.commit()
        conn.close()

        # Supprime l'utilisateur admin existant s'il existe
        admin = User.query.filter_by(username='admin').first()
        if admin:
            db.session.delete(admin)
            db.session.commit()

        # Crée le nouvel utilisateur admin avec les bonnes permissions
        admin = User(
            username='admin',
            email='admin@local.dev',
            is_admin=True,
            can_access_mixer=True,
            is_active=True
        )
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
        print("✅ Utilisateur admin créé avec succès")

        print("✅ Base de données mise à jour avec succès")

if __name__ == '__main__':
    upgrade_database()
