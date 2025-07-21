swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "🎧 DJ Pro Studio API 🎶",
        "description": """
Bienvenue dans l'API REST officielle de **DJ Pro Studio** - ta plateforme web 🔥 fullstack pour mixer, gérer ta musique et tes playlists comme un pro !

✨ **Fonctionnalités clés** :
- 🎵 Gestion complète des utilisateurs avec rôles (admin & DJ)
- 📂 Création, édition et suppression de playlists personnalisées
- 🎼 Upload et analyse avancée des pistes audio (MP3, WAV, AIFF, OGG, M4A)
- 🎚️ Accès en temps réel à un mixer DJ puissant via Web Audio API
- 🔐 Authentification sécurisée avec gestion des droits d'accès
- 🖥️ Interface responsive et intuitive pensée pour les passionnés de musique
- ⚙️ Administration complète avec contrôle d’accès aux fonctions sensibles

💻 **Technologies** :
- Backend : Python 🐍, Flask, SQLAlchemy, Flask-Login
- Frontend : HTML5, CSS3, JS ES6, Web Audio API
- Documentation interactive et moderne avec Swagger / Flasgger

📚 **À propos du projet** :
Ce projet est une réalisation personnelle de **Baptiste RIVIERE**, développée dans le cadre de la formation **Holberton School Rennes**.  
L’objectif : proposer une expérience DJ en ligne complète, accessible, et performante, avec une architecture robuste et un code propre.

📞 **Contact & Support** :  
- Site web : [https://mixer.fusikabdj.fr](https://mixer.fusikabdj.fr)  
- Email : baptiste@fusikabdj.fr  
- LinkedIn : [https://linkedin.com/in/baptisteriviere](https://linkedin.com/in/baptisteriviere)

🚀 **Rejoins la révolution DJ Pro Studio et commence à mixer dès aujourd’hui !**
        """,
        "termsOfService": "https://mixer.fusikabdj.fr/terms",
        "contact": {
            "responsibleOrganization": "DJ Pro Studio",
            "responsibleDeveloper": "Baptiste RIVIERE 🎧",
            "email": "baptiste@fusikabdj.fr",
            "url": "https://mixer.fusikabdj.fr",
        },
        "license": {
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        },
        "version": "1.0.0"
    },
    "host": "mixer.fusikabdj.fr",
    "basePath": "/api",
    "schemes": [
        "https",
        "http"
    ],
    "securityDefinitions": {
        "ApiKeyAuth": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "🔑 Utilisez un token JWT Bearer ou une clé API dans l’en-tête Authorization"
        }
    },
    "security": [
        {
            "ApiKeyAuth": []
        }
    ],
    "tags": [
        {"name": "auth", "description": "🔐 Authentification & gestion des utilisateurs"},
        {"name": "playlists", "description": "🎶 Gestion des playlists et organisation musicale"},
        {"name": "tracks", "description": "🎧 Gestion des pistes audio et métadonnées"},
        {"name": "mixer", "description": "🎚️ Contrôle du mixer DJ en temps réel"},
        {"name": "admin", "description": "⚙️ Fonctions d’administration & gestion des droits"}
    ]
}

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec_1",
            "route": "/apispec_1.json",
            "rule_filter": lambda rule: True,  # expose toutes les routes
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/"
}

def init_swagger(app):
    from flasgger import Swagger
    Swagger(app, template=swagger_template, config=swagger_config)
