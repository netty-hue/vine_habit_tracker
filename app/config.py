import os

# Dossier racine du projet
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    """Configuration de base de l'application."""

    # Clé secrète utilisée par Flask (sessions, formulaires CSRF...)
    SECRET_KEY = "change-moi-en-production"

    # Base de données SQLite -> fichier app.db à la racine du projet
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "app.db")

    # Désactive le tracking des modifications (non nécessaire, gain de perf)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
