from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    """Indique à Flask-Login comment retrouver un utilisateur à partir de son id."""
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    """Table des utilisateurs."""

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mot_de_passe_hash = db.Column(db.String(255), nullable=False)

    # Un utilisateur peut avoir plusieurs tâches (relation 1-N)
    taches = db.relationship("Tache", backref="auteur", lazy=True)

    def set_password(self, mot_de_passe):
        self.mot_de_passe_hash = generate_password_hash(mot_de_passe)

    def check_password(self, mot_de_passe):
        return check_password_hash(self.mot_de_passe_hash, mot_de_passe)

    def __repr__(self):
        return f"<User {self.email}>"


class Tache(db.Model):
    """Exemple simple d'entité liée à un utilisateur (CRUD basique)."""

    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(140), nullable=False)
    terminee = db.Column(db.Boolean, default=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    # Clé étrangère vers l'utilisateur propriétaire de la tâche
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __repr__(self):
        return f"<Tache {self.titre}>"
