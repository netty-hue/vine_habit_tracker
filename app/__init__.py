from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

from app.config import Config

# Extensions déclarées ici pour pouvoir être importées ailleurs (models.py, routes.py...)
db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    """Fonction qui crée et configure l'application Flask."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialisation des extensions avec l'application
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "main.login"  # redirection si non connecté

    # Import et enregistrement des routes (blueprint)
    from app.routes import main
    app.register_blueprint(main)

    # Création des tables au démarrage si elles n'existent pas
    with app.app_context():
        db.create_all()

    return app
